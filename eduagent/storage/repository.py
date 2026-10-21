"""Repositório SQLite de domínio: DDL, WAL/FULL, escritor serializado e
transações curtas (mapa §5); ``domain_revision`` monotônica, snapshot
materializado e ownership por FK composto (mapa §15.1).

Contratos implementados (task 004):

- **WAL/FULL e escritor serializado** (§5, linha 125): toda conexão recebe
  ``journal_mode=WAL``, ``synchronous=FULL``, ``foreign_keys=ON`` e
  ``busy_timeout``. Toda escrita passa por ``write_transaction``, que abre
  ``BEGIN IMMEDIATE`` — um único escritor por vez; leituras concurrentes
  continuam permitidas pelo WAL. Transações são curtas: nunca permanecem
  abertas durante LLM/rede (§11).
- **domain_revision monotônica** (§15.1): ``DomainStore.commit_operation``
  incrementa ``users.domain_revision`` uma única vez por operação nova, na
  mesma transação do efeito; retries da mesma ``operation_id`` devolvem o
  recibo original sem incrementar (idempotência do §11, pré-implementada
  aqui na camada de dados para a task 005 reutilizar).
- **Validação de revisão esperada** (§5: "todo estado mutável valida revisão
  esperada"): escritas recebem ``expected_version``; divergência gera
  ``EduAgentError(VERSION_CONFLICT)`` (retentável, mapa §4).
- **Snapshot materializado** (§15.1, linha 245): ``materialize_snapshot`` copia
  fatos/agenda/projeções/versões ativas/ref hashes para um artefato imutável
  (JSON + SHA-256 + ``snapshot_version``) em transação de leitura curta; a
  leitura não mantém conexão aberta e registra o usuário (ownership). Escrita
  nova após leitura exige reload — ``require_fresh`` compara a revisão vista
  com a atual e recusa commit com revisão velha.
- **Ownership** (§15.1, linha 249): consultas de leitura são sempre
  parametrizadas por ``user_id``; FKs compostas ``(user_id,id)`` no DDL
  (migrations.py) recusam cruzar donos no nível do banco; ``topic_edges``
  exige mesmo curso via trigger.
- **Eventos brutos e exclusão explícita** (§5, linha 125): ``purge_event_
  payloads`` zera ``payload_json`` e registra ``purged_at``/``purge_reason``
  — sem hash reversível do texto excluído (§5: "não manter hash reversível de
  texto excluído"; o gatilho ``events_no_undrop_payload`` impede restauração).

Nada aqui apresenta resultados medidos: contadores, tempos e versões são
estado do banco, não benchmarks.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eduagent.contracts import ErrorCode, EduAgentError
from eduagent.storage.migrations import apply_migrations, migrate_database

#: Piso de SQLite exigido pelo mapa §3 ("correções WAL documentadas em 3.51.3
#: ou backport"): 3.51.3 é o primeiro release da série corrigida.
SQLITE_WAL_FLOOR = (3, 51, 3)

#: ``busy_timeout`` default de ensaio (ms) — escolha operacional local, não
#: resultado medido (mapa §1/§3).
DEFAULT_BUSY_TIMEOUT_MS = 5_000


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sqlite_version_tuple() -> tuple[int, ...]:
    return tuple(int(p) for p in sqlite3.sqlite_version.split(".")[:3])


def require_wal_capable_sqlite() -> str:
    """Recusa SQLite anterior à série corrigida do WAL (mapa §3).

    Retorna a versão em uso; levanta ``EduAgentError(INTERNAL_FAILURE)`` se o
    runtime embutido é anterior a 3.51.3 e não há backport verificado.
    """
    version = _sqlite_version_tuple()
    if version < SQLITE_WAL_FLOOR:
        raise EduAgentError(
            ErrorCode.INTERNAL_FAILURE,
            f"SQLite {sqlite3.sqlite_version} anterior ao piso WAL 3.51.3 "
            "(mapa §3); use runtime corrigido ou backport verificado",
            diagnostic="eduagent/storage/repository.py",
        )
    return sqlite3.sqlite_version


@dataclass(frozen=True)
class Receipt:
    """Recibo do commit idempotente (mapa §11 — pré-implementação da 004).

    ``domain_revision`` é a revisão após o commit; ``was_retry`` indica que a
    operação já tinha sido aplicada (mesmo ``operation_id``+``digest``) e o
    recibo original foi devolvido **sem** novo incremento (§15.1: retries não
    incrementam).
    """

    operation_id: str
    domain_revision: int
    was_retry: bool
    applied_at: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "operation_id": self.operation_id,
                "domain_revision": self.domain_revision,
                "was_retry": self.was_retry,
                "applied_at": self.applied_at,
            },
            sort_keys=True,
        )


@dataclass
class Snapshot:
    """Artefato imutável de snapshot (mapa §15.1, linha 245).

    ``version`` é a ``users.domain_revision`` congelada na materialização;
    ``content`` é um dict serializável (fatos, topic_states, planos ativos,
    versões ativas de documentos, ref hashes de dependências). ``digest`` é o
    SHA-256 do JSON canônico — imutabilidade verificável.
    """

    user_id: str
    version: int
    materialized_at: str
    content: dict[str, Any] = field(default_factory=dict)

    @property
    def digest(self) -> str:
        canonical = json.dumps(self.content, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_json(self) -> str:
        return json.dumps(
            {
                "user_id": self.user_id,
                "snapshot_version": self.version,
                "materialized_at": self.materialized_at,
                "digest": self.digest,
                "content": self.content,
            },
            sort_keys=True,
        )


class DomainStore:
    """Repositório SQLite do domínio (um banco por instância).

    Uso típico:

        store = DomainStore.open("data/domain.sqlite")
        with store.write(user_id, expected_version=12) as tx:
            tx.execute("INSERT INTO facts ...")
        # tx.domain_revision == 13 após o commit
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Abertura e configuração
    # ------------------------------------------------------------------

    @classmethod
    def open(
        cls,
        path: str | Path,
        *,
        apply_schema: bool = True,
        busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
    ) -> "DomainStore":
        """Abre (criando se preciso) o banco de domínio com o perfil do §5.

        - ``journal_mode=WAL`` e ``synchronous=FULL`` — persistência exigida
          pelo mapa §5; WAL é persistente no arquivo, ``synchronous`` é por
          conexão e é reaplicado aqui.
        - ``foreign_keys=ON`` e ``busy_timeout`` — por conexão.
        - Escritor serializado: as escritas passam por ``write_transaction``
          (``BEGIN IMMEDIATE``), nunca por ``conn.execute`` solto.
        """
        require_wal_capable_sqlite()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), timeout=busy_timeout_ms / 1000)
        conn.row_factory = sqlite3.Row
        conn.isolation_level = None  # transações explícitas (autocommit off)
        conn.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA foreign_keys=ON")
        if apply_schema:
            apply_migrations(conn)
        return cls(conn)

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Transações curtas — escritor serializado (§5, §11)
    # ------------------------------------------------------------------

    @contextmanager
    def write_transaction(
        self,
        user_id: str,
        *,
        expected_version: int | None = None,
        bump_domain_revision: bool = True,
    ) -> Iterator[sqlite3.Connection]:
        """Transação curta de escrita com revisão validada (§5/§15.1).

        - Abre ``BEGIN IMMEDIATE`` (escritor serializado) e valida a revisão
          esperada do usuário **antes** de executar os efeitos; divergência
          levanta ``VERSION_CONFLICT`` sem aplicar nada.
        - No commit, incrementa ``users.domain_revision`` **uma vez**, na
          mesma transação dos efeitos (§15.1). Operações que não mudam domínio
          (metadados operacionais — receipt/lease/trace, §15.1 linha 247)
          passam ``bump_domain_revision=False`` e não incrementam.
        - Qualquer exceção faz ``ROLLBACK`` completo — efeito parcial nunca
          persiste junto do incremento.
        """
        conn = self._conn
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT domain_revision FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if row is None:
                raise EduAgentError(
                    ErrorCode.SOURCE_UNRESOLVED,
                    f"usuário {user_id} não existe no domínio",
                    diagnostic="eduagent/storage/repository.py",
                )
            current = int(row["domain_revision"])
            if expected_version is not None and expected_version != current:
                raise EduAgentError(
                    ErrorCode.VERSION_CONFLICT,
                    f"revisão esperada {expected_version} difere da atual "
                    f"{current} (usuário {user_id})",
                    diagnostic="eduagent/storage/repository.py",
                )
            yield conn
            if bump_domain_revision:
                conn.execute(
                    "UPDATE users SET domain_revision = domain_revision + 1 "
                    "WHERE id = ?",
                    (user_id,),
                )
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise

    @contextmanager
    def read_transaction(self) -> Iterator[sqlite3.Connection]:
        """Leitura curta em snapshot do WAL (mapa §15.1).

        Leituras no WAL não bloqueiam escritas, mas a transação é fechada
        imediatamente após o yield — agentes nunca mantêm conexão aberta
        (§15.1: "os agentes não mantêm uma conexão aberta").
        """
        self._conn.execute("BEGIN DEFERRED")
        try:
            yield self._conn
        finally:
            self._conn.execute("COMMIT")

    # ------------------------------------------------------------------
    # Escritas de domínio de alto nível
    # ------------------------------------------------------------------

    def execute_write(
        self,
        user_id: str,
        statements: list[tuple[str, tuple[Any, ...]]],
        *,
        expected_version: int | None = None,
        bump_domain_revision: bool = True,
    ) -> int:
        """Executa statements de escrita numa transação única e retorna a
        ``domain_revision`` pós-commit.

        Conveniência sobre ``write_transaction`` para chamadores que já
        materializaram os efeitos; o caminho preferido é ``commit_operation``
        (idempotente) ou transações compostas.
        """
        with self.write_transaction(
            user_id,
            expected_version=expected_version,
            bump_domain_revision=bump_domain_revision,
        ) as tx:
            for sql, params in statements:
                tx.execute(sql, params)
        return self.domain_revision(user_id)

    def commit_operation(
        self,
        user_id: str,
        operation_id: str,
        digest: str,
        statements: list[tuple[str, tuple[Any, ...]]],
        *,
        expected_version: int,
    ) -> Receipt:
        """Commit de operação de domínio com idempotência (§11 + §15.1).

        Semântica (na mesma transação, escritor serializado):

        1. Se ``(operation_id)`` já existe com o mesmo ``digest``: devolve o
           recibo original **sem** incrementar ``domain_revision`` (retry).
           Com ``digest`` diferente: erro ``SCHEMA_INVALID`` (§4: "mesmo ID
           com digest diferente é erro").
        2. Operação nova: valida ``expected_version``, aplica os statements e
           incrementa ``domain_revision`` uma única vez, registra a operação
           em ``operations`` (estado ``committed`` + recibo) e confirma.

        A task 005 (commit idempotente e recuperação §11) estende este caminho
        com outbox/dispatcher; a garantia de dados já vive aqui.
        """
        conn = self._conn
        conn.execute("BEGIN IMMEDIATE")
        try:
            existing = conn.execute(
                "SELECT digest, receipt_json FROM operations "
                "WHERE id = ? AND user_id = ?",
                (operation_id, user_id),
            ).fetchone()
            if existing is not None:
                if existing["digest"] != digest:
                    raise EduAgentError(
                        ErrorCode.SCHEMA_INVALID,
                        "mesmo operation_id com digest diferente (mapa §4)",
                        diagnostic="eduagent/storage/repository.py",
                    )
                receipt = _decode_receipt(existing["receipt_json"], operation_id)
                conn.execute("COMMIT")
                return receipt  # retry: nada incrementa (§15.1)

            row = conn.execute(
                "SELECT domain_revision FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if row is None:
                raise EduAgentError(
                    ErrorCode.SOURCE_UNRESOLVED,
                    f"usuário {user_id} não existe no domínio",
                    diagnostic="eduagent/storage/repository.py",
                )
            current = int(row["domain_revision"])
            if expected_version != current:
                raise EduAgentError(
                    ErrorCode.VERSION_CONFLICT,
                    f"revisão esperada {expected_version} difere da atual "
                    f"{current} (usuário {user_id})",
                    diagnostic="eduagent/storage/repository.py",
                )

            for sql, params in statements:
                conn.execute(sql, params)

            new_revision = current + 1
            conn.execute(
                "UPDATE users SET domain_revision = domain_revision + 1 "
                "WHERE id = ?",
                (user_id,),
            )
            applied_at = _utc_now_iso()
            receipt = Receipt(
                operation_id=operation_id,
                domain_revision=new_revision,
                was_retry=False,
                applied_at=applied_at,
            )
            conn.execute(
                "INSERT INTO operations(id, user_id, digest, state, "
                "expected_version, receipt_json) VALUES (?,?,?,?,?,?)",
                (
                    operation_id,
                    user_id,
                    digest,
                    "committed",
                    expected_version,
                    receipt.to_json(),
                ),
            )
            conn.execute("COMMIT")
            return receipt
        except BaseException:
            conn.execute("ROLLBACK")
            raise

    # ------------------------------------------------------------------
    # Leituras de domínio (ownership por user_id — §15.1)
    # ------------------------------------------------------------------

    def domain_revision(self, user_id: str) -> int:
        """Revisão atual do domínio do usuário (``expected_version``)."""
        row = self._conn.execute(
            "SELECT domain_revision FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row is None:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"usuário {user_id} não existe no domínio",
                diagnostic="eduagent/storage/repository.py",
            )
        return int(row["domain_revision"])

    def ensure_user(self, user_id: str, *, timezone: str | None = None) -> None:
        """Cria o usuário se ausente (idempotente; não incrementa revisão)."""
        conn = self._conn
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "INSERT INTO users(id, timezone) VALUES (?, ?) "
                "ON CONFLICT(id) DO NOTHING",
                (user_id, timezone),
            )
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise

    def fetch_user_rows(
        self, sql: str, params: tuple[Any, ...] = ()
    ) -> list[sqlite3.Row]:
        """Leitura parametrizada em transação curta (uso interno/serviços).

        O chamador é responsável por incluir ``user_id`` no filtro — as FKs
        compostas do DDL protegem a escrita; a leitura é controlada aqui.
        """
        with self.read_transaction() as tx:
            return list(tx.execute(sql, params).fetchall())

    # ------------------------------------------------------------------
    # Snapshot materializado (§15.1, linha 245)
    # ------------------------------------------------------------------

    def materialize_snapshot(self, user_id: str) -> Snapshot:
        """Materializa o snapshot do usuário em leitura curta.

        Copia para um artefato imutável: fatos ativos, projeções de estado de
        tópico, demandas pendentes, planos com revisão, versões ativas de
        documentos e os ref hashes das dependências de artefatos (§15.1). A
        transação é aberta e fechada aqui — nada de conexão retida.

        Escritas novas após esta leitura exigem reload (``require_fresh`` /
        ``expected_version``) — o controle conservador no MVP é por usuário.
        """
        with self.read_transaction() as tx:
            revision = int(
                tx.execute(
                    "SELECT domain_revision FROM users WHERE id = ?", (user_id,)
                ).fetchone()["domain_revision"]
            )
            facts = [
                dict(r)
                for r in tx.execute(
                    "SELECT id, kind, value_json, status, valid_from, "
                    "valid_to, recorded_at, supersedes FROM facts "
                    "WHERE user_id = ? AND status IN ('confirmed','candidate')",
                    (user_id,),
                ).fetchall()
            ]
            topic_states = [
                dict(r)
                for r in tx.execute(
                    "SELECT topic_id, revision, payload_json FROM topic_states "
                    "WHERE user_id = ?",
                    (user_id,),
                ).fetchall()
            ]
            demands = [
                dict(r)
                for r in tx.execute(
                    "SELECT id, payload_json, status FROM demands "
                    "WHERE user_id = ?",
                    (user_id,),
                ).fetchall()
            ]
            plans = [
                dict(r)
                for r in tx.execute(
                    "SELECT id, revision, snapshot_version, approval_ref "
                    "FROM plans WHERE user_id = ?",
                    (user_id,),
                ).fetchall()
            ]
            active_versions = [
                dict(r)
                for r in tx.execute(
                    "SELECT d.id AS doc_id, d.active_version, "
                    "v.sha256 FROM documents d LEFT JOIN doc_versions v "
                    "ON v.id = d.active_version "
                    "WHERE d.user_id = ?",
                    (user_id,),
                ).fetchall()
            ]
            ref_hashes = {
                r["ref"]: r["digest"]
                for r in tx.execute(
                    "SELECT artifact_id AS ref, digest FROM confirmations "
                    "WHERE user_id = ?",
                    (user_id,),
                ).fetchall()
            }
        content = {
            "facts": facts,
            "topic_states": topic_states,
            "demands": demands,
            "plans": plans,
            "active_versions": active_versions,
            "ref_hashes": ref_hashes,
        }
        return Snapshot(
            user_id=user_id,
            version=revision,
            materialized_at=_utc_now_iso(),
            content=content,
        )

    def require_fresh(self, user_id: str, seen_version: int) -> None:
        """Exige reload após escrita de terceiros (§15.1).

        Levanta ``VERSION_CONFLICT`` se a revisão atual difere da versão vista
        pelo snapshot — escrita nova com visão velha é recusada; o chamador
        materializa novo snapshot e refaz a proposta.
        """
        current = self.domain_revision(user_id)
        if current != seen_version:
            raise EduAgentError(
                ErrorCode.VERSION_CONFLICT,
                f"snapshot v{seen_version} está velho: domínio está em "
                f"v{current}; materialize novo snapshot antes de escrever",
                diagnostic="eduagent/storage/repository.py",
            )

    # ------------------------------------------------------------------
    # Auditoria e exclusão explícita de payloads pessoais (§5)
    # ------------------------------------------------------------------

    def purge_event_payloads(
        self,
        user_id: str,
        *,
        event_ids: list[str] | None = None,
        reason: str,
    ) -> int:
        """Exclusão explícita de payloads pessoais de eventos (§5, linha 125).

        Zera ``payload_json`` dos eventos do usuário (todos ou os
        ``event_ids`` listados) e registra ``purged_at``/``purge_reason``.
        **Não** se mantém hash reversível do texto excluído: nenhuma coluna
        guarda derivada do payload; o gatilho ``events_no_undrop_payload``
        impede restauração. Retorna o número de eventos purgados.
        """
        with self.write_transaction(
            user_id, bump_domain_revision=False
        ) as tx:  # purge é efeito de privacidade; não é escrita de domínio
            if event_ids is None:
                cursor = tx.execute(
                    "UPDATE events SET payload_json = NULL, purged_at = ?, "
                    "purge_reason = ? WHERE user_id = ? "
                    "AND payload_json IS NOT NULL",
                    (_utc_now_iso(), reason, user_id),
                )
            else:
                purged = 0
                for event_id in event_ids:
                    cursor = tx.execute(
                        "UPDATE events SET payload_json = NULL, purged_at = ?, "
                        "purge_reason = ? WHERE id = ? AND user_id = ? "
                        "AND payload_json IS NOT NULL",
                        (_utc_now_iso(), reason, event_id, user_id),
                    )
                    purged += cursor.rowcount
                return purged
            return int(cursor.rowcount)

    def add_artifact_dependency(
        self,
        user_id: str,
        *,
        child_ref: str,
        parent_ref: str,
        relation: str,
    ) -> None:
        """Registra dependência de artefato (§15.1) numa transação própria.

        Relações válidas: ``derived_from``/``corrects``/``supersedes`` —
        validadas pelo CHECK do DDL; índices cobrem os dois sentidos.
        """
        if relation not in ("derived_from", "corrects", "supersedes"):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"relação inválida {relation!r} (§15.1)",
                diagnostic="eduagent/storage/repository.py",
            )
        self.execute_write(
            user_id,
            [
                (
                    "INSERT INTO artifact_dependencies(user_id, child_ref, "
                    "parent_ref, relation) VALUES (?,?,?,?)",
                    (user_id, child_ref, parent_ref, relation),
                )
            ],
        )

    def dependents_of(
        self, user_id: str, parent_ref: str
    ) -> list[dict[str, str]]:
        """Dependentes (filhos) de um artefato — percurso de invalidação."""
        rows = self.fetch_user_rows(
            "SELECT child_ref, relation FROM artifact_dependencies "
            "WHERE user_id = ? AND parent_ref = ?",
            (user_id, parent_ref),
        )
        return [{"child_ref": r["child_ref"], "relation": r["relation"]} for r in rows]

    def dependencies_of(
        self, user_id: str, child_ref: str
    ) -> list[dict[str, str]]:
        """Fontes (pais) de um artefato — percurso de correção."""
        rows = self.fetch_user_rows(
            "SELECT parent_ref, relation FROM artifact_dependencies "
            "WHERE user_id = ? AND child_ref = ?",
            (user_id, child_ref),
        )
        return [{"parent_ref": r["parent_ref"], "relation": r["relation"]} for r in rows]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _decode_receipt(receipt_json: str | None, operation_id: str) -> Receipt:
    if not receipt_json:
        raise EduAgentError(
            ErrorCode.INTERNAL_FAILURE,
            f"operação {operation_id} committed sem recibo armazenado",
            diagnostic="eduagent/storage/repository.py",
        )
    data = json.loads(receipt_json)
    return Receipt(
        operation_id=str(data["operation_id"]),
        domain_revision=int(data["domain_revision"]),
        was_retry=True,  # recibo reutilizado em retry
        applied_at=str(data["applied_at"]),
    )


__all__ = [
    "DEFAULT_BUSY_TIMEOUT_MS",
    "DomainStore",
    "Receipt",
    "Snapshot",
    "SQLITE_WAL_FLOOR",
    "migrate_database",
    "require_wal_capable_sqlite",
]
