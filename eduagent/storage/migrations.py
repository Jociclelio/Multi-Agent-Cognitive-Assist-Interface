"""Migrações de schema versionadas (tabela ``schema_migrations``, mapa §5).

O DDL lógico do mapa §5 (linhas 100–122) é aplicado na migração ``0001`` como
uma única transação, com ``PRAGMA foreign_keys=ON`` e ``BEGIN IMMEDIATE``;
aplicar uma migração já registrada é no-op idempotente (C1 da task 004). O
esquema é todo textual/SQLite (mapa §1): nenhum motor adicional.

Contratos do mapa §5 implementados aqui:

- ``users`` tem a ``domain_revision`` monotônica de §15.1 (o ``revision`` do
  DDL §5 é essa coluna no runtime — toda escrita nova de domínio incrementa
  ``users.domain_revision`` na mesma transação do efeito, e ``expected_version``/
  ``snapshot_version`` são esse contador; receipts/leases/traces não incrementam).
- Todas as tabelas de domínio têm ``user_id`` com ownership direto ou FK
  composto ``(user_id, id)`` para o pai (§15.1, linha 249).
- ``artifact_dependencies(user_id, child_ref, parent_ref, relation)`` com as
  relações ``derived_from/corrects/supersedes`` e índices nos dois sentidos
  (child→parent e parent→child) para percurso de correção/exclusão.
- ``events`` preserva payload bruto para auditoria; a exclusão explícita de
  payloads pessoais é registrada sem hash reversível do texto excluído — a
  coluna ``payload_json`` vira NULL e ``purged_at``/``purge_reason`` marcam o
  evento; nenhum digest do conteúdo é mantido.
- Arestas de tópicos exigem mesmo dono/curso (§15.1) — ``topics`` carrega
  ``course_id`` e ``topic_edges`` valida por triggers que ambos os nós são do
  mesmo curso; ownership direto vem da disciplina via ``courses.user_id``.

Nota de runtime: o mapa §3 pede SQLite com as correções WAL documentadas
(3.51.3 ou backport). O interpretador do projeto (CPython 3.12, ``uv``)
embarca SQLite 3.53.1, posterior à série corrigida — versão verificada por
``_require_sqlite_floor`` em ``repository.py``; nenhum backport é necessário
nesta configuração. Nada aqui é resultado medido: são verificações de
configuração.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Any

#: Migrações versionadas: ``(versão, descrição, SQL script)``. Cada script roda
#: dentro de uma única transação (``BEGIN IMMEDIATE``), com FKs habilitadas.
#: A ordem da lista é a ordem de aplicação; versões são monotônicas.
MIGRATIONS: list[tuple[int, str, str]] = []


def _migration_0001() -> str:
    """DDL completo do bloco §5 + ``artifact_dependencies`` (§15.1).

    Observações de projeto (escolhas de ensaio do MVP, não resultados medidos):

    - ``user_id`` é ``TEXT`` (UUID) e toda tabela de domínio o traz, direto ou
      via FK composto do pai — §15.1, linha 249 ("eventos/items de usuário
      incluem user_id"). ``items`` recebe ``user_id`` e ``attempts`` referencia
      itens por FK composto ``(user_id, item_id)`` — tentativa e item do mesmo
      dono. FKs compostas exigem índice único ``(user_id, id)`` na tabela pai
      (``doc_versions``, ``items``, ``attempts``).
    - ``assessments`` herda o dono via FK composto ``attempt_user_id``; a
      unicidade lógica de §15.2 é ``(attempt_id, assessment_revision)``.
    - FKs são compostas ``(user_id, id)`` onde §15.1 pede; FKs simples de
      catálogo (``course_id`` → ``courses.id``) ficam com índice próprio.
    - ``ON DELETE CASCADE`` propaga deleção a derivados (mapa §5, "deleção
      propaga a todos os derivados"); ``ON DELETE RESTRICT`` protege o pai
      onde o derivado é evidência (mapa §6: proveniência).
    - Índices nos dois sentidos de ``artifact_dependencies`` permitem percorrer
      a árvore de dependências na correção/exclusão (§15.1) sem varredura.
    """
    return """
-- ---------------------------------------------------------------------------
-- users (mapa §5 linha 100 + §15.1 domain_revision)
-- ---------------------------------------------------------------------------
CREATE TABLE users (
    id              TEXT PRIMARY KEY,               -- UUID
    timezone        TEXT,                           -- null até confirmação (§3)
    domain_revision INTEGER NOT NULL DEFAULT 0 CHECK (domain_revision >= 0),
    -- Alias de leitura do DDL §5 ("users(id PK, timezone, revision)"); §15.1
    -- renomeia o conceito para domain_revision. Coluna gerada: sempre espelha
    -- domain_revision, sem escrita direta.
    revision        INTEGER GENERATED ALWAYS AS (domain_revision) VIRTUAL
);

-- ---------------------------------------------------------------------------
-- courses / topics / topic_edges (§5 linhas 101–103, §15.1 mesmo dono/curso)
-- ---------------------------------------------------------------------------
CREATE TABLE courses (
    id           TEXT PRIMARY KEY,                  -- UUID
    user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    aliases_json TEXT NOT NULL DEFAULT '[]',
    revision     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_courses_user ON courses(user_id);

CREATE TABLE topics (
    id           TEXT PRIMARY KEY,                  -- UUID
    course_id    TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    aliases_json TEXT NOT NULL DEFAULT '[]',
    revision     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_topics_course ON topics(course_id);

-- Arestas exigem mesmo dono/curso (§15.1): triggers recusam aresta entre
-- tópicos de cursos diferentes; ownership do curso é o do usuário.
CREATE TABLE topic_edges (
    parent_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    child_id  TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    UNIQUE(parent_id, child_id)
);
CREATE INDEX idx_topic_edges_child ON topic_edges(child_id);
CREATE TRIGGER topic_edges_same_course_insert
BEFORE INSERT ON topic_edges
BEGIN
    SELECT RAISE(ABORT, 'topic_edges: parent e child devem pertencer ao mesmo curso')
    WHERE (SELECT course_id FROM topics WHERE id = NEW.parent_id)
       <> (SELECT course_id FROM topics WHERE id = NEW.child_id);
END;
CREATE TRIGGER topic_edges_same_course_update
BEFORE UPDATE OF parent_id, child_id ON topic_edges
BEGIN
    SELECT RAISE(ABORT, 'topic_edges: parent e child devem pertencer ao mesmo curso')
    WHERE (SELECT course_id FROM topics WHERE id = NEW.parent_id)
       <> (SELECT course_id FROM topics WHERE id = NEW.child_id);
END;

-- ---------------------------------------------------------------------------
-- documents / doc_versions / blocks / chunks (§5 linhas 104–108)
-- ---------------------------------------------------------------------------
CREATE TABLE documents (
    id             TEXT PRIMARY KEY,                -- UUID
    user_id        TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id      TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    active_version TEXT                             -- doc_versions.id; null = sem versão ativa
);
CREATE INDEX idx_documents_user ON documents(user_id);
CREATE INDEX idx_documents_course ON documents(course_id);
-- A versão ativa, quando existe, pertence ao documento (FK composto).
CREATE TRIGGER documents_active_version_check
BEFORE INSERT ON documents WHEN NEW.active_version IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'documents: active_version deve pertencer ao documento')
    WHERE NOT EXISTS (
        SELECT 1 FROM doc_versions
        WHERE id = NEW.active_version AND doc_id = NEW.id
    );
END;
CREATE TRIGGER documents_active_version_check_update
BEFORE UPDATE OF active_version ON documents
BEGIN
    SELECT RAISE(ABORT, 'documents: active_version deve pertencer ao documento')
    WHERE NEW.active_version IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM doc_versions
        WHERE id = NEW.active_version AND doc_id = NEW.id
    );
END;

CREATE TABLE doc_versions (
    id                  TEXT PRIMARY KEY,           -- UUID
    user_id             TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    doc_id              TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    sha256              TEXT NOT NULL CHECK (length(sha256) = 64),
    mime                TEXT NOT NULL,
    original_ref        TEXT NOT NULL,
    extractor_manifest  TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN ('pending','indexed','active','failed'))
);
CREATE INDEX idx_doc_versions_doc ON doc_versions(doc_id);
CREATE INDEX idx_doc_versions_user ON doc_versions(user_id);
-- Chave única (user_id, id): alvo da FK composta de blocks/chunks (§15.1).
CREATE UNIQUE INDEX uq_doc_versions_user_id ON doc_versions(user_id, id);

CREATE TABLE blocks (
    id             TEXT PRIMARY KEY,                -- UUID
    user_id        TEXT NOT NULL,                   -- FK composto → doc_versions
    version_id     TEXT NOT NULL,
    page           INTEGER NOT NULL CHECK (page >= 1),
    order_index    INTEGER NOT NULL,
    kind           TEXT NOT NULL,
    text           TEXT NOT NULL DEFAULT '',
    bbox_json      TEXT,
    diagnosis_json TEXT,
    FOREIGN KEY (user_id, version_id)
        REFERENCES doc_versions(user_id, id) ON DELETE CASCADE
);
CREATE INDEX idx_blocks_version ON blocks(version_id);
CREATE INDEX idx_blocks_page ON blocks(version_id, page, order_index);

CREATE TABLE chunks (
    id                  TEXT PRIMARY KEY,           -- UUID
    user_id             TEXT NOT NULL,              -- FK composto → doc_versions
    version_id          TEXT NOT NULL,
    block_refs_json     TEXT NOT NULL DEFAULT '[]',
    text                TEXT NOT NULL,
    embedding_manifest  TEXT,
    FOREIGN KEY (user_id, version_id)
        REFERENCES doc_versions(user_id, id) ON DELETE CASCADE
);
CREATE INDEX idx_chunks_version ON chunks(version_id);

-- ---------------------------------------------------------------------------
-- facts (§5 linha 109–110; status enum do §4 AcademicFact)
-- ---------------------------------------------------------------------------
CREATE TABLE facts (
    id                TEXT PRIMARY KEY,             -- UUID
    user_id           TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind              TEXT NOT NULL,
    value_json        TEXT NOT NULL,
    authority         TEXT NOT NULL,
    valid_from        TEXT,                         -- ISO-8601; null = aberto
    valid_to          TEXT,
    recorded_at       TEXT NOT NULL,
    source_refs_json  TEXT NOT NULL DEFAULT '[]',
    supersedes        TEXT REFERENCES facts(id) ON DELETE SET NULL,
    status            TEXT NOT NULL
        CHECK (status IN ('candidate','ambiguous','confirmed','rejected')),
    revision          INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_facts_user ON facts(user_id);
CREATE INDEX idx_facts_status ON facts(user_id, status);

-- ---------------------------------------------------------------------------
-- events (§5 linha 111; payload bruto auditável + exclusão explícita)
-- ---------------------------------------------------------------------------
CREATE TABLE events (
    id           TEXT PRIMARY KEY,                  -- UUID
    user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id   TEXT,
    kind         TEXT NOT NULL,
    payload_json TEXT,                              -- NULL após purge explícito
    occurred_at  TEXT NOT NULL,
    recorded_at  TEXT NOT NULL,
    purged_at    TEXT,                              -- exclusão explícita (§5)
    purge_reason TEXT
);
CREATE INDEX idx_events_user ON events(user_id);
CREATE INDEX idx_events_session ON events(user_id, session_id);
-- Após purge, o payload não volta: UPDATE que repõe payload é recusado.
CREATE TRIGGER events_no_undrop_payload
BEFORE UPDATE OF payload_json ON events
WHEN NEW.payload_json IS NOT NULL AND OLD.payload_json IS NULL
BEGIN
    SELECT RAISE(ABORT, 'events: payload purgado não pode ser restaurado (§5)');
END;

-- ---------------------------------------------------------------------------
-- items / attempts / assessments (§5 linhas 112–114; §15.1: "eventos/items
-- de usuário incluem user_id"; §15.2 unicidade lógica)
-- ---------------------------------------------------------------------------
CREATE TABLE items (
    id                TEXT PRIMARY KEY,             -- UUID
    user_id           TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    family_id         TEXT NOT NULL,
    version           INTEGER NOT NULL CHECK (version >= 1),
    prompt            TEXT NOT NULL,
    answer_ref        TEXT NOT NULL,
    rubric_ref        TEXT NOT NULL,
    source_refs_json  TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX idx_items_family ON items(family_id, version);
-- Chave única (user_id, id): alvo da FK composta de attempts (§15.1).
CREATE UNIQUE INDEX uq_items_user_id ON items(user_id, id);

CREATE TABLE attempts (
    id                TEXT PRIMARY KEY,             -- UUID
    user_id           TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item_id           TEXT NOT NULL,
    response_event_id TEXT REFERENCES events(id) ON DELETE SET NULL,
    help_level        INTEGER NOT NULL CHECK (help_level BETWEEN 0 AND 3),
    revealed          INTEGER NOT NULL CHECK (revealed IN (0,1)),
    attempt_ordinal   INTEGER NOT NULL DEFAULT 0,
    -- Tentativa referencia item do mesmo dono (FK composto, §15.1).
    FOREIGN KEY (user_id, item_id)
        REFERENCES items(user_id, id) ON DELETE RESTRICT
);
CREATE INDEX idx_attempts_user ON attempts(user_id);
CREATE INDEX idx_attempts_item ON attempts(item_id);
-- Chave única (user_id, id): alvo da FK composta de assessments (§15.1).
CREATE UNIQUE INDEX uq_attempts_user_id ON attempts(user_id, id);

CREATE TABLE assessments (
    id                  TEXT PRIMARY KEY,           -- UUID
    attempt_id          TEXT NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    attempt_user_id     TEXT NOT NULL,              -- FK composto → attempts (§15.1)
    assessor_version    TEXT NOT NULL,
    payload_json        TEXT NOT NULL,
    assessment_revision INTEGER NOT NULL DEFAULT 1 CHECK (assessment_revision >= 1),
    supersedes          TEXT REFERENCES assessments(id) ON DELETE SET NULL,
    FOREIGN KEY (attempt_user_id, attempt_id)
        REFERENCES attempts(user_id, id) ON DELETE CASCADE
);
CREATE INDEX idx_assessments_attempt ON assessments(attempt_id);
-- Unicidade lógica (§15.2): (attempt_id, assessment_revision), não versão do
-- modelo; a coluna assessor_version fica no payload.
CREATE UNIQUE INDEX uq_assessments_attempt_revision
    ON assessments(attempt_id, assessment_revision);

-- ---------------------------------------------------------------------------
-- topic_states (§5 linha 114; PK composta por usuário/tópico)
-- ---------------------------------------------------------------------------
CREATE TABLE topic_states (
    user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_id     TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    revision     INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (user_id, topic_id)
);

-- ---------------------------------------------------------------------------
-- summaries / demands / plans (§5 linhas 115–117)
-- ---------------------------------------------------------------------------
CREATE TABLE summaries (
    id                    TEXT PRIMARY KEY,         -- UUID
    user_id               TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_event_ids_json TEXT NOT NULL DEFAULT '[]',
    claims_json           TEXT NOT NULL,
    verification          TEXT,
    revision              INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_summaries_user ON summaries(user_id);

CREATE TABLE demands (
    id           TEXT PRIMARY KEY,                  -- UUID
    user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    payload_json TEXT NOT NULL,
    status       TEXT NOT NULL,
    revision     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_demands_user ON demands(user_id);

CREATE TABLE plans (
    id               TEXT PRIMARY KEY,              -- UUID
    user_id          TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    revision         INTEGER NOT NULL DEFAULT 0,
    snapshot_version INTEGER NOT NULL DEFAULT 0,    -- = users.domain_revision (§15.1)
    payload_json     TEXT NOT NULL,
    approval_ref     TEXT
);
CREATE INDEX idx_plans_user ON plans(user_id);

-- ---------------------------------------------------------------------------
-- logical_blocks / operations / outbox / confirmations (§5 linhas 118–121)
-- ---------------------------------------------------------------------------
CREATE TABLE logical_blocks (
    id          TEXT PRIMARY KEY,                   -- UUID
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    uid         TEXT NOT NULL UNIQUE,               -- UID ICS estável (§15.5)
    revision    INTEGER NOT NULL DEFAULT 0,
    remote_id   TEXT,
    etag        TEXT
);
CREATE INDEX idx_logical_blocks_user ON logical_blocks(user_id);

CREATE TABLE operations (
    id               TEXT PRIMARY KEY,              -- operation_id UUID (§11)
    user_id          TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    digest           TEXT NOT NULL CHECK (length(digest) = 64),
    state            TEXT NOT NULL
        CHECK (state IN ('pending','committed','failed')),
    expected_version INTEGER NOT NULL,              -- domain_revision esperada
    receipt_json     TEXT
);
CREATE INDEX idx_operations_user ON operations(user_id);
-- Mesmo ID com digest diferente é erro (§4/§11) — índice único impede
-- sobrescrever sem verificação explícita na camada de repositório.
CREATE UNIQUE INDEX uq_operations_id_digest ON operations(id, digest);

CREATE TABLE outbox (
    id            TEXT PRIMARY KEY,                 -- UUID
    user_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    operation_id  TEXT NOT NULL UNIQUE REFERENCES operations(id) ON DELETE CASCADE,
    target        TEXT NOT NULL,
    payload_json  TEXT NOT NULL,
    lease_until   TEXT,
    state         TEXT NOT NULL DEFAULT 'pending'
        CHECK (state IN ('pending','in_flight','done','failed'))
);
CREATE INDEX idx_outbox_state ON outbox(state);
CREATE INDEX idx_outbox_user ON outbox(user_id);

CREATE TABLE confirmations (
    id                TEXT PRIMARY KEY,             -- UUID
    user_id           TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    artifact_id       TEXT NOT NULL,
    artifact_revision INTEGER NOT NULL,
    digest            TEXT NOT NULL CHECK (length(digest) = 64),
    occurred_at       TEXT NOT NULL,
    base_revision     INTEGER,                      -- §15.1
    approval_revision INTEGER                       -- §15.1
);
CREATE INDEX idx_confirmations_user ON confirmations(user_id);

-- ---------------------------------------------------------------------------
-- artifact_dependencies (§15.1, linha 249): relações nos dois sentidos
-- ---------------------------------------------------------------------------
CREATE TABLE artifact_dependencies (
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    child_ref  TEXT NOT NULL,                       -- 'doc:uuid@v' / 'fact:uuid@v' ...
    parent_ref TEXT NOT NULL,
    relation   TEXT NOT NULL
        CHECK (relation IN ('derived_from','corrects','supersedes')),
    PRIMARY KEY (user_id, child_ref, parent_ref, relation)
);
-- Sentido 1: dependências de um artefato (correção parte do filho).
CREATE INDEX idx_ad_by_child ON artifact_dependencies(user_id, child_ref, relation);
-- Sentido 2: dependentes de um pai (invalidação parte do pai).
CREATE INDEX idx_ad_by_parent ON artifact_dependencies(user_id, parent_ref, relation);

-- ---------------------------------------------------------------------------
-- schema_migrations (§5 linha 122)
-- ---------------------------------------------------------------------------
CREATE TABLE schema_migrations (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
"""


def _load_builtin() -> None:
    MIGRATIONS.append((1, "DDL completo do mapa §5 + artifact_dependencies (§15.1)", _migration_0001()))


_load_builtin()


def _connect(path: str) -> sqlite3.Connection:
    """Conexão de migração: FKs habilitadas, journal persistente na base."""
    conn = sqlite3.connect(path, isolation_level=None)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _current_version(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
    ).fetchone()
    return int(row[0])


def _migration_applied(conn: sqlite3.Connection, version: int) -> bool:
    """Verifica se a versão já foi aplicada (tolera banco ainda sem a tabela).

    Numa base do zero, ``schema_migrations`` não existe antes da primeira
    migração — a checagem vai de ``sqlite_master`` primeiro.
    """
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND "
        "name = 'schema_migrations'"
    ).fetchone()
    if not exists:
        return False
    return (
        conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version = ?", (version,)
        ).fetchone()
        is not None
    )


def apply_migrations(
    conn: sqlite3.Connection,
    *,
    migrations: list[tuple[int, str, str]] | None = None,
    log: Callable[[str], None] | None = None,
) -> list[int]:
    """Aplica migrações pendentes e retorna as versões aplicadas nesta chamada.

    Idempotente: se a versão já está em ``schema_migrations``, é no-op (C1 —
    segunda aplicação não altera o schema). Cada migração roda em transação
    única (``BEGIN IMMEDIATE``) — ou aplica tudo, ou nada.
    """
    plan = migrations if migrations is not None else MIGRATIONS
    applied_now: list[int] = []
    for version, _description, script in plan:
        if _migration_applied(conn, version):
            continue
        # ``executescript`` emite COMMIT implícito de transações pendentes e
        # roda em autocommit — por isso a transação única do §5 é aberta
        # dentro do próprio script (BEGIN IMMEDIATE ... COMMIT), garantindo
        # atomicidade: ou a migração inteira aplica, ou nada persiste.
        script_sql = (
            "BEGIN IMMEDIATE;\n"
            f"{script}\n"
            "INSERT INTO schema_migrations(version, applied_at) VALUES "
            f"({int(version)}, strftime('%Y-%m-%dT%H:%M:%fZ','now'));\n"
            "COMMIT;"
        )
        try:
            conn.executescript(script_sql)
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        applied_now.append(version)
        if log is not None:
            log(f"migração {version} aplicada ({_description})")
    return applied_now


def migrate_database(
    path: str,
    *,
    migrations: list[tuple[int, str, str]] | None = None,
    log: Callable[[str], None] | None = None,
) -> list[int]:
    """Cria/abre o banco em ``path`` e aplica migrações pendentes.

    Mantém WAL persistente (mapa §5) e rehabilita FKs (``PRAGMA`` não é
    persistente em conexões novas). Retorna as versões aplicadas.
    """
    conn = _connect(path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        return apply_migrations(conn, migrations=migrations, log=log)
    finally:
        conn.close()


def current_version(conn: sqlite3.Connection) -> int:
    """Última versão aplicada (0 se o banco está vazio)."""
    return _current_version(conn)


def table_names(conn: sqlite3.Connection) -> set[str]:
    """Nomes de tabelas de usuário presentes (utilitário de verificação)."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {str(r[0]) for r in rows}


def introspect_table(conn: sqlite3.Connection, table: str) -> dict[str, Any]:
    """Introspecção básica: colunas, PK e FKs de uma tabela (verificação C1)."""
    columns = [
        {
            "name": r[1],
            "type": r[2],
            "notnull": bool(r[3]),
            "pk": bool(r[5]),
        }
        for r in conn.execute(f"PRAGMA table_info({table})").fetchall()
    ]
    fks = [
        {
            "table": r[2],
            "from": r[3],
            "to": r[4],
        }
        for r in conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
    ]
    return {"columns": columns, "foreign_keys": fks}
