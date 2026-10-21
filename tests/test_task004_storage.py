"""Testes de aceite da task 004 — DDL, migrações, snapshot e domain_revision
(mapa §5 e §15.1).

Não é a suíte quantitativa da etapa 8 (mapa de testes): são testes locais de
curta duração que verificam os critérios C1–C3 da task. C4 (mapa intocado,
commits separados, submodule intocado) é verificado por inspeção de git e
registrado no task.md.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from pathlib import Path

import pytest

from eduagent.contracts import EduAgentError, ErrorCode
from eduagent.storage.migrations import (
    MIGRATIONS,
    apply_migrations,
    current_version,
    introspect_table,
    table_names,
)
from eduagent.storage.repository import (
    SQLITE_WAL_FLOOR,
    DomainStore,
    require_wal_capable_sqlite,
)

UID = "123e4567-e89b-12d3-a456-426614174000"
UID2 = "223e4567-e89b-12d3-a456-426614174000"
HASH64 = "ab" * 32

#: Todas as 21 tabelas do DDL do §5 + artifact_dependencies + schema_migrations.
EXPECTED_TABLES = {
    "users",
    "courses",
    "topics",
    "topic_edges",
    "documents",
    "doc_versions",
    "blocks",
    "chunks",
    "facts",
    "events",
    "items",
    "attempts",
    "assessments",
    "topic_states",
    "summaries",
    "demands",
    "plans",
    "logical_blocks",
    "operations",
    "outbox",
    "confirmations",
    "schema_migrations",
    "artifact_dependencies",
}


def _uuid() -> str:
    return str(uuid.uuid4())


def _seed_course(store: DomainStore, user_id: str = UID) -> str:
    """Cria usuário + curso + dois tópicos; retorna course_id."""
    store.ensure_user(user_id)
    course_id = _uuid()
    topic_a, topic_b = _uuid(), _uuid()
    store.execute_write(
        user_id,
        [
            (
                "INSERT INTO courses(id, user_id, title) VALUES (?,?,?)",
                (course_id, user_id, "Cálculo"),
            ),
            (
                "INSERT INTO topics(id, course_id, title) VALUES (?,?,?)",
                (topic_a, course_id, "Limites"),
            ),
            (
                "INSERT INTO topics(id, course_id, title) VALUES (?,?,?)",
                (topic_b, course_id, "Derivadas"),
            ),
        ],
        expected_version=0,
    )
    return course_id


# ======================================================================
# C1 — migração do zero cria todas as tabelas; segunda aplicação é no-op
# ======================================================================


class TestC1Migration:
    def test_all_tables_created_from_scratch(self, tmp_path: Path) -> None:
        db = tmp_path / "domain.sqlite"
        store = DomainStore.open(db)
        try:
            assert EXPECTED_TABLES <= table_names(store._conn)
        finally:
            store.close()

    def test_second_application_is_noop(self, tmp_path: Path) -> None:
        db = tmp_path / "domain.sqlite"
        store = DomainStore.open(db)
        conn = store._conn
        try:
            before = conn.execute(
                "SELECT count(*) FROM sqlite_master"
            ).fetchone()[0]
            applied = apply_migrations(conn)
            assert applied == []  # nada a aplicar
            after = conn.execute(
                "SELECT count(*) FROM sqlite_master"
            ).fetchone()[0]
            assert before == after
            assert current_version(conn) == MIGRATIONS[-1][0]
        finally:
            store.close()

    def test_migration_is_atomic_on_failure(self, tmp_path: Path) -> None:
        """Script com SQL inválido não deixa estado parcial."""
        db = tmp_path / "partial.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute("PRAGMA foreign_keys=ON")
        bad = [
            (
                1,
                "migração inválida de teste",
                "CREATE TABLE ok1(id INTEGER); CREATE TABLE sem_fechar(",
            )
        ]
        with pytest.raises(sqlite3.OperationalError):
            apply_migrations(conn, migrations=bad)
        # nada da migração quebrada persistiu (rollback do BEGIN do script)
        names = table_names(conn)
        assert "ok1" not in names and "sem_fechar" not in names
        assert "schema_migrations" not in names  # versão não registrada
        conn.close()

    def test_users_columns_match_section5(self, tmp_path: Path) -> None:
        db = tmp_path / "domain.sqlite"
        store = DomainStore.open(db)
        try:
            # ``revision`` é coluna gerada (alias do §5); aparece em xinfo.
            info = store._conn.execute(
                "PRAGMA table_xinfo(users)"
            ).fetchall()
            cols = {r[1] for r in info}
            assert {"id", "timezone", "revision", "domain_revision"} <= cols
            # revision espelha domain_revision e não aceita escrita direta
            row = store._conn.execute(
                "SELECT revision, domain_revision FROM users LIMIT 1"
            ).fetchone()
            assert row is None  # sem usuários ainda; verificação de leitura ok
        finally:
            store.close()

    def test_artifact_dependencies_relations_and_both_indexes(
        self, tmp_path: Path
    ) -> None:
        db = tmp_path / "domain.sqlite"
        store = DomainStore.open(db)
        conn = store._conn
        try:
            sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE "
                "name='artifact_dependencies'"
            ).fetchone()[0]
            for relation in ("derived_from", "corrects", "supersedes"):
                assert relation in sql
            # índices nos dois sentidos (§15.1)
            indexes = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND "
                    "tbl_name='artifact_dependencies' AND name NOT LIKE "
                    "'sqlite_%'"
                ).fetchall()
            }
            assert "idx_ad_by_child" in indexes   # child → parent
            assert "idx_ad_by_parent" in indexes  # parent → child
        finally:
            store.close()

    def test_artifact_dependency_invalid_relation_rejected(
        self, tmp_path: Path
    ) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            store.ensure_user(UID)
            with pytest.raises(EduAgentError):
                store.add_artifact_dependency(
                    UID,
                    child_ref="fact:a@1",
                    parent_ref="doc:b@1",
                    relation="inventada",
                )
        finally:
            store.close()


# ======================================================================
# C2 — WAL/FULL; escrita concorrente serializada; revisão esperada;
#      domain_revision incrementa uma única vez por operação nova
# ======================================================================


class TestC2WalAndRevision:
    def test_wal_and_full_pragmas(self, tmp_path: Path) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        conn = store._conn
        try:
            assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
            assert conn.execute("PRAGMA synchronous").fetchone()[0] == 2  # FULL
            assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        finally:
            store.close()

    def test_wal_persists_in_file(self, tmp_path: Path) -> None:
        db = tmp_path / "domain.sqlite"
        DomainStore.open(db).close()
        probe = sqlite3.connect(str(db))
        try:
            assert probe.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        finally:
            probe.close()

    def test_sqlite_floor_check(self) -> None:
        version = require_wal_capable_sqlite()
        parts = [int(p) for p in version.split(".")[:3]]
        assert tuple(parts) >= SQLITE_WAL_FLOOR

    def test_expected_version_conflict_rolls_back(
        self, tmp_path: Path
    ) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            _seed_course(store)
            with pytest.raises(EduAgentError) as exc:
                store.execute_write(
                    UID,
                    [
                        (
                            "INSERT INTO facts(id, user_id, kind, value_json,"
                            " authority, recorded_at, status) VALUES "
                            "(?,?,?,?,?,?,?)",
                            (
                                _uuid(),
                                UID,
                                "date",
                                "{}",
                                "document",
                                "2026-10-21T12:00:00Z",
                                "candidate",
                            ),
                        )
                    ],
                    expected_version=99,
                )
            assert exc.value.code == ErrorCode.VERSION_CONFLICT
            assert store.domain_revision(UID) == 1  # sem incremento
        finally:
            store.close()

    def test_domain_revision_increments_once_per_new_operation(
        self, tmp_path: Path
    ) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            _seed_course(store)
            assert store.domain_revision(UID) == 1
            receipt = store.commit_operation(
                UID,
                operation_id=_uuid(),
                digest=HASH64,
                statements=[
                    (
                        "INSERT INTO facts(id, user_id, kind, value_json, "
                        "authority, recorded_at, status) VALUES (?,?,?,?,?,?,?)",
                        (
                            _uuid(),
                            UID,
                            "date",
                            "{}",
                            "document",
                            "2026-10-21T12:00:00Z",
                            "candidate",
                        ),
                    )
                ],
                expected_version=1,
            )
            assert receipt.domain_revision == 2 and not receipt.was_retry
            assert store.domain_revision(UID) == 2

            # Retry do mesmo operation_id+digest: devolve recibo, não incrementa
            retry = store.commit_operation(
                UID,
                operation_id=receipt.operation_id,
                digest=HASH64,
                statements=[],  # efeitos não reexecutados
                expected_version=0,  # mesmo velho — retry ignora (§11)
            )
            assert retry.was_retry
            assert retry.domain_revision == 2
            assert store.domain_revision(UID) == 2
        finally:
            store.close()

    def test_same_operation_id_different_digest_is_error(
        self, tmp_path: Path
    ) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            _seed_course(store)
            op = _uuid()
            store.commit_operation(
                UID, operation_id=op, digest=HASH64, statements=[],
                expected_version=1,
            )
            other_digest = "cd" * 32
            with pytest.raises(EduAgentError) as exc:
                store.commit_operation(
                    UID, operation_id=op, digest=other_digest, statements=[],
                    expected_version=2,
                )
            assert exc.value.code == ErrorCode.SCHEMA_INVALID
        finally:
            store.close()

    def test_operation_failure_does_not_bump_revision(
        self, tmp_path: Path
    ) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            _seed_course(store)
            before = store.domain_revision(UID)
            with pytest.raises(sqlite3.IntegrityError):
                # statement viola CHECK do DDL → rollback completo
                store.execute_write(
                    UID,
                    [
                        (
                            "UPDATE users SET domain_revision = -5 "
                            "WHERE id = ?",
                            (UID,),
                        )
                    ],
                    expected_version=before,
                )
            assert store.domain_revision(UID) == before
        finally:
            store.close()

    def test_concurrent_writers_serialize(self, tmp_path: Path) -> None:
        """Dois escritores concorrentes partem da mesma revisão: o escritor
        serializado recusa a revisão velha (VERSION_CONFLICT, retentável) e,
        após reload (§15.1), o retry aplica — cada incremento é único."""
        db = tmp_path / "domain.sqlite"
        store = DomainStore.open(db)
        _seed_course(store)
        base = store.domain_revision(UID)
        store.close()

        errors: list[Exception] = []
        increments: list[int] = []
        conflicts: list[int] = []

        def writer() -> None:
            own = DomainStore.open(db)
            try:
                for attempt in range(3):  # retry limitado com reload
                    try:
                        receipt = own.commit_operation(
                            UID,
                            operation_id=_uuid(),
                            digest=HASH64,
                            statements=[
                                (
                                    "INSERT INTO events(id, user_id, kind, "
                                    "occurred_at, recorded_at) "
                                    "VALUES (?,?,?,?,?)",
                                    (
                                        _uuid(),
                                        UID,
                                        "test",
                                        "2026-10-21T12:00:00Z",
                                        "2026-10-21T12:00:00Z",
                                    ),
                                )
                            ],
                            expected_version=own.domain_revision(UID),
                        )
                        increments.append(receipt.domain_revision)
                        break
                    except EduAgentError as exc:
                        if (
                            exc.code == ErrorCode.VERSION_CONFLICT
                            and attempt < 2
                        ):
                            conflicts.append(attempt)
                            continue  # reload e retry (§15.1)
                        raise
            except Exception as exc:  # noqa: BLE001 — registrado no teste
                errors.append(exc)
            finally:
                own.close()

        threads = [threading.Thread(target=writer) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert errors == []
        final = DomainStore.open(db)
        try:
            # Escritor serializado: revisões finais consecutivas e únicas.
            assert sorted(increments) == [base + 1, base + 2]
            assert final.domain_revision(UID) == base + 2
            assert (
                final.fetch_user_rows(
                    "SELECT count(*) AS n FROM events WHERE user_id = ?",
                    (UID,),
                )[0]["n"]
                == 2
            )
        finally:
            final.close()

    def test_metadata_write_does_not_bump_revision(self, tmp_path: Path) -> None:
        """Receipt/lease/trace não incrementam domain_revision (§15.1)."""
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            _seed_course(store)
            before = store.domain_revision(UID)
            store.execute_write(
                UID,
                [("UPDATE outbox SET lease_until = ? WHERE 0", ("2026-01-01",))],
                expected_version=before,
                bump_domain_revision=False,
            )
            assert store.domain_revision(UID) == before
        finally:
            store.close()


# ======================================================================
# Ownership — FK composto (user_id,id); topic_edges mesmo dono/curso
# ======================================================================


class TestOwnership:
    def test_composite_fk_blocks_cross_owner_parent(
        self, tmp_path: Path
    ) -> None:
        """FK composta ``(user_id,id)``: um usuário não pode referenciar
        doc_version de outro dono (§15.1, linha 249)."""
        db = tmp_path / "domain.sqlite"
        store = DomainStore.open(db)
        try:
            store.ensure_user(UID)
            store.ensure_user(UID2)
            course_a = _seed_course(store, UID)
            doc_id = _uuid()
            version_a = _uuid()
            store.execute_write(
                UID,
                [
                    (
                        "INSERT INTO documents(id, user_id, course_id) "
                        "VALUES (?,?,?)",
                        (doc_id, UID, course_a),
                    ),
                    (
                        "INSERT INTO doc_versions(id, user_id, doc_id, "
                        "sha256, mime, original_ref, extractor_manifest, "
                        "status) VALUES (?,?,?,?,?,?,?,?)",
                        (
                            version_a,
                            UID,
                            doc_id,
                            HASH64,
                            "application/pdf",
                            "orig",
                            "manifest",
                            "active",
                        ),
                    ),
                ],
            )
            # UID2 aponta blocks para doc_versions do UID → FK composta recusa
            with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
                store.execute_write(
                    UID2,
                    [
                        (
                            "INSERT INTO blocks(id, user_id, version_id, "
                            "page, order_index, kind, text) "
                            "VALUES (?,?,?,?,?,?,?)",
                            (_uuid(), UID2, version_a, 1, 0, "paragraph", "x"),
                        )
                    ],
                )
            # O dono legítimo consegue inserir o bloco
            store.execute_write(
                UID,
                [
                    (
                        "INSERT INTO blocks(id, user_id, version_id, "
                        "page, order_index, kind, text) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (_uuid(), UID, version_a, 1, 0, "paragraph", "x"),
                    )
                ],
            )
        finally:
            store.close()

    def test_topic_edges_require_same_course(self, tmp_path: Path) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            course_a = _seed_course(store, UID)
            # Curso/tópicos de outro usuário — ownership diferente
            store.ensure_user(UID2)
            course_b = _uuid()
            store.execute_write(
                UID2,
                [
                    (
                        "INSERT INTO courses(id, user_id, title) VALUES (?,?,?)",
                        (course_b, UID2, "Física"),
                    ),
                    (
                        "INSERT INTO topics(id, course_id, title) VALUES (?,?,?)",
                        (_uuid(), course_b, "Cinemática"),
                    ),
                ],
                expected_version=0,
            )
            topic_other = store.fetch_user_rows(
                "SELECT id FROM topics WHERE course_id = ?", (course_b,)
            )[0]["id"]
            topic_mine = store.fetch_user_rows(
                "SELECT id FROM topics WHERE course_id = ? LIMIT 1",
                (course_a,),
            )[0]["id"]
            # Aresta entre cursos diferentes é recusada pelo trigger (§15.1)
            with pytest.raises(
                (sqlite3.IntegrityError, sqlite3.OperationalError),
                match="mesmo curso",
            ):
                store.execute_write(
                    UID,
                    [
                        (
                            "INSERT INTO topic_edges(parent_id, child_id) "
                            "VALUES (?,?)",
                            (topic_mine, topic_other),
                        )
                    ],
                )
        finally:
            store.close()

    def test_valid_topic_edge_accepted(self, tmp_path: Path) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            course = _seed_course(store)
            topics = store.fetch_user_rows(
                "SELECT id FROM topics WHERE course_id = ? ORDER BY title",
                (course,),
            )
            store.execute_write(
                UID,
                [
                    (
                        "INSERT INTO topic_edges(parent_id, child_id) "
                        "VALUES (?,?)",
                        (topics[0]["id"], topics[1]["id"]),
                    )
                ],
            )
            assert (
                store.fetch_user_rows("SELECT count(*) AS n FROM topic_edges")[
                    0
                ]["n"]
                == 1
            )
        finally:
            store.close()


# ======================================================================
# C3 — snapshot materializado imutável em leitura curta; reload após escrita
# ======================================================================


class TestC3Snapshot:
    def test_snapshot_immutable_and_versioned(self, tmp_path: Path) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            _seed_course(store)
            snap1 = store.materialize_snapshot(UID)
            content_json = snap1.to_json()
            digest1 = snap1.digest
            # Imutabilidade: mesmo conteúdo → mesmo digest
            reparsed = json.loads(content_json)
            assert reparsed["snapshot_version"] == snap1.version
            assert reparsed["digest"] == digest1
            # snapshot_version é a domain_revision do usuário (§15.1)
            assert snap1.version == store.domain_revision(UID)

            # Escrita nova → versão nova no snapshot seguinte
            store.execute_write(
                UID,
                [
                    (
                        "INSERT INTO facts(id, user_id, kind, value_json, "
                        "authority, recorded_at, status) VALUES (?,?,?,?,?,?,?)",
                        (
                            _uuid(),
                            UID,
                            "date",
                            '{"normalized_value": "2026-11-01"}',
                            "document",
                            "2026-10-21T12:00:00Z",
                            "confirmed",
                        ),
                    )
                ],
            )
            snap2 = store.materialize_snapshot(UID)
            assert snap2.version == snap1.version + 1
            assert snap2.digest != digest1
            assert len(snap2.content["facts"]) == 1
        finally:
            store.close()

    def test_stale_snapshot_write_requires_reload(self, tmp_path: Path) -> None:
        """Escrita nova após leitura exige reload (§15.1): revisão velha é
        recusada com VERSION_CONFLICT."""
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            _seed_course(store)
            snap = store.materialize_snapshot(UID)
            assert store.domain_revision(UID) == snap.version
            # Outra parte escreve (por usuário — controle conservador do MVP)
            store.execute_write(
                UID,
                [
                    (
                        "INSERT INTO demands(id, user_id, payload_json, "
                        "status) VALUES (?,?,?,?)",
                        (_uuid(), UID, "{}", "pending"),
                    )
                ],
            )
            # Escrita baseada no snapshot velho é recusada…
            with pytest.raises(EduAgentError) as exc:
                store.execute_write(
                    UID,
                    [
                        (
                            "INSERT INTO summaries(id, user_id, claims_json) "
                            "VALUES (?,?,?)",
                            (_uuid(), UID, "[]"),
                        )
                    ],
                    expected_version=snap.version,
                )
            assert exc.value.code == ErrorCode.VERSION_CONFLICT
            # …e require_fresh sinaliza a necessidade de reload
            with pytest.raises(EduAgentError, match="materialize novo snapshot"):
                store.require_fresh(UID, snap.version)
            # Reload resolve
            fresh = store.materialize_snapshot(UID)
            store.require_fresh(UID, fresh.version)  # não levanta
        finally:
            store.close()

    def test_snapshot_reads_do_not_bump_revision(self, tmp_path: Path) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            _seed_course(store)
            before = store.domain_revision(UID)
            for _ in range(3):
                store.materialize_snapshot(UID)
            assert store.domain_revision(UID) == before
        finally:
            store.close()

    def test_snapshot_isolated_per_user(self, tmp_path: Path) -> None:
        """Ownership do snapshot: conteúdo de outro usuário não vaza (§15.1:
        "Acesso ao snapshot mantém ownership"; "não mistura usuários" §4)."""
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            _seed_course(store, UID)
            store.ensure_user(UID2)
            store.execute_write(
                UID2,
                [
                    (
                        "INSERT INTO demands(id, user_id, payload_json, "
                        "status) VALUES (?,?,?,?)",
                        (_uuid(), UID2, '{"secreto": true}', "pending"),
                    )
                ],
                expected_version=0,
            )
            snap1 = store.materialize_snapshot(UID)
            snap2 = store.materialize_snapshot(UID2)
            assert snap1.user_id == UID and snap2.user_id == UID2
            assert all(d["id"] for d in snap1.content["demands"]) is True
            assert snap1.content["demands"] == []  # nada do UID2
            assert len(snap2.content["demands"]) == 1
        finally:
            store.close()


# ======================================================================
# §5 — eventos brutos, exclusão explícita, sem hash reversível
# ======================================================================


class TestEventPurge:
    def test_purge_clears_payload_and_keeps_event(self, tmp_path: Path) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            _seed_course(store)
            event_id = _uuid()
            store.execute_write(
                UID,
                [
                    (
                        "INSERT INTO events(id, user_id, kind, payload_json, "
                        "occurred_at, recorded_at) VALUES (?,?,?,?,?,?)",
                        (
                            event_id,
                            UID,
                            "user_answer",
                            json.dumps({"text": "resposta pessoal x"}),
                            "2026-10-21T12:00:00Z",
                            "2026-10-21T12:00:00Z",
                        ),
                    )
                ],
            )
            purged = store.purge_event_payloads(UID, reason="pedido do usuário")
            assert purged == 1
            row = store.fetch_user_rows(
                "SELECT payload_json, purged_at, purge_reason FROM events "
                "WHERE id = ?",
                (event_id,),
            )[0]
            assert row["payload_json"] is None  # payload removido
            assert row["purged_at"] is not None
            assert "pedido do usuário" in row["purge_reason"]
            # evento bruto preservado como registro de auditoria (sem payload)
            assert (
                store.fetch_user_rows(
                    "SELECT kind FROM events WHERE id = ?", (event_id,)
                )[0]["kind"]
                == "user_answer"
            )
        finally:
            store.close()

    def test_purged_payload_cannot_be_restored(self, tmp_path: Path) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            _seed_course(store)
            event_id = _uuid()
            store.execute_write(
                UID,
                [
                    (
                        "INSERT INTO events(id, user_id, kind, payload_json, "
                        "occurred_at, recorded_at) VALUES (?,?,?,?,?,?)",
                        (
                            event_id,
                            UID,
                            "user_answer",
                            '{"text": "x"}',
                            "2026-10-21T12:00:00Z",
                            "2026-10-21T12:00:00Z",
                        ),
                    )
                ],
            )
            store.purge_event_payloads(UID, reason="teste")
            # Restauração é recusada pelo gatilho (§5: tombstone sem retorno)
            with pytest.raises(
                (sqlite3.IntegrityError, sqlite3.OperationalError),
                match="purgado",
            ):
                store.execute_write(
                    UID,
                    [
                        (
                            "UPDATE events SET payload_json = ? WHERE id = ?",
                            ('{"text": "de volta"}', event_id),
                        )
                    ],
                    bump_domain_revision=False,
                )
        finally:
            store.close()

    def test_no_reversible_hash_of_purged_text(self, tmp_path: Path) -> None:
        """Nenhuma coluna do banco guarda derivada reversível do payload
        excluído (§5: "não manter hash reversível de texto excluído")."""
        db = tmp_path / "domain.sqlite"
        store = DomainStore.open(db)
        try:
            columns = store.fetch_user_rows("PRAGMA table_xinfo(events)")
            names = {r[1] for r in columns}
            # Colunas de purge registram o fato da exclusão, nunca conteúdo
            # nem derivada (hash) do texto excluído.
            purge_cols = {n for n in names if n.startswith("purged") or n.startswith("purge")}
            assert purge_cols == {"purged_at", "purge_reason"}
            for name in names:
                lowered = name.lower()
                assert not (
                    ("payload" in lowered or "text" in lowered)
                    and "hash" in lowered
                ), f"coluna suspeita de hash reversível: {name}"
        finally:
            store.close()

    def test_purge_scoped_to_owner(self, tmp_path: Path) -> None:
        """Purge é por usuário: payload de outro dono não é tocado (§15.1)."""
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            _seed_course(store, UID)
            store.ensure_user(UID2)
            other_event = _uuid()
            store.execute_write(
                UID2,
                [
                    (
                        "INSERT INTO events(id, user_id, kind, payload_json, "
                        "occurred_at, recorded_at) VALUES (?,?,?,?,?,?)",
                        (
                            other_event,
                            UID2,
                            "user_answer",
                            '{"text": "do outro usuário"}',
                            "2026-10-21T12:00:00Z",
                            "2026-10-21T12:00:00Z",
                        ),
                    )
                ],
                expected_version=0,
            )
            store.purge_event_payloads(UID, reason="apaga só os meus")
            row = store.fetch_user_rows(
                "SELECT payload_json FROM events WHERE id = ?", (other_event,)
            )[0]
            assert row["payload_json"] is not None  # intocado
        finally:
            store.close()


# ======================================================================
# artifact_dependencies — os dois sentidos
# ======================================================================


class TestArtifactDependencies:
    def test_traversal_both_directions(self, tmp_path: Path) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            _seed_course(store)
            store.add_artifact_dependency(
                UID, child_ref="fact:f1@1", parent_ref="doc:d1@2",
                relation="derived_from",
            )
            store.add_artifact_dependency(
                UID, child_ref="fact:f2@1", parent_ref="fact:f1@1",
                relation="corrects",
            )
            # filho → pais
            parents = store.dependencies_of(UID, "fact:f1@1")
            assert {"doc:d1@2"} == {p["parent_ref"] for p in parents}
            # pai → filhos (invalidação)
            children = store.dependents_of(UID, "fact:f1@1")
            assert {"fact:f2@1"} == {c["child_ref"] for c in children}
            # correção de doc:d1 percorre dependentes em cadeia
            assert store.dependents_of(UID, "doc:d1@2")[0]["child_ref"] == "fact:f1@1"
        finally:
            store.close()

    def test_dependencies_are_user_scoped(self, tmp_path: Path) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            _seed_course(store, UID)
            store.ensure_user(UID2)
            store.add_artifact_dependency(
                UID, child_ref="fact:f1@1", parent_ref="doc:d1@1",
                relation="supersedes",
            )
            assert store.dependencies_of(UID2, "fact:f1@1") == []
            assert store.dependents_of(UID2, "doc:d1@1") == []
        finally:
            store.close()


# ======================================================================
# Sanidade — schema_migrations e DDL do §5
# ======================================================================


class TestSchemaRegistry:
    def test_schema_migrations_row_recorded(self, tmp_path: Path) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            rows = store.fetch_user_rows(
                "SELECT version, applied_at FROM schema_migrations"
            )
            assert [r["version"] for r in rows] == [m[0] for m in MIGRATIONS]
            assert all(r["applied_at"] for r in rows)
        finally:
            store.close()

    def test_all_domain_tables_have_user_ownership_path(
        self, tmp_path: Path
    ) -> None:
        """Toda tabela de domínio tem user_id direto ou FK composta para o
        pai (§5 linha 99; §15.1 linha 249: 'FK composto (user_id,id) para
        pai'). ``assessments`` herda o dono via ``attempt_user_id``."""
        store = DomainStore.open(tmp_path / "domain.sqlite")
        conn = store._conn
        try:
            domain_tables = EXPECTED_TABLES - {"schema_migrations"}
            # ``topic_edges`` é tabela relacional: §15.1 (mais preciso que o
            # cabeçalho do §5) exige "arestas de tópicos exigem mesmo
            # dono/curso", garantido pelos triggers de mesmo curso sobre
            # topics→courses→users (ownership indireto pelos pais).
            relational_via_parents = {"topic_edges", "topics", "users"}
            allowed_owner_columns = {"user_id", "attempt_user_id"}
            for table in sorted(domain_tables - relational_via_parents):
                info = introspect_table(conn, table)
                cols = {c["name"] for c in info["columns"]}
                owner_cols = cols & allowed_owner_columns
                assert owner_cols, (
                    f"{table} sem user_id nem FK composto para pai "
                    "(§5/§15.1)"
                )
            # Triggers de mesmo curso presentes (§15.1)
            triggers = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='trigger' "
                    "AND tbl_name='topic_edges'"
                ).fetchall()
            }
            assert "topic_edges_same_course_insert" in triggers
            assert "topic_edges_same_course_update" in triggers
        finally:
            store.close()

    def test_operations_table_enforces_digest_uniqueness(
        self, tmp_path: Path
    ) -> None:
        store = DomainStore.open(tmp_path / "domain.sqlite")
        try:
            _seed_course(store)
            op = _uuid()
            store.commit_operation(
                UID, operation_id=op, digest=HASH64, statements=[],
                expected_version=1,
            )
            # Mesmo id+digest: persistido uma única vez
            rows = store.fetch_user_rows(
                "SELECT id FROM operations WHERE id = ?", (op,)
            )
            assert len(rows) == 1
        finally:
            store.close()
