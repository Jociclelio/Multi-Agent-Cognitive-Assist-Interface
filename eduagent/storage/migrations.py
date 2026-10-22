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
  Resolução da 004a: o bloco DDL do §5 não contém ``user_id`` em
  ``topics``/``topic_edges`` — a coluna **não** é adicionada; ownership de
  tópicos/arestas permanece via cadeia ``courses.user_id`` + trigger de mesmo
  curso (mapa intocado).
- Ownership no nível do banco em FKs simples (§15.1, correção da 004 —
  migração ``0002``): ``courses`` ganha ``UNIQUE(user_id,id)`` (alvo de FK
  composto) e ``documents.course_id`` vira FK composto
  ``(user_id, course_id)``; ``facts.supersedes``, ``attempts.response_event_id``
  e ``assessments.supersedes`` recusam referência entre donos por trigger no
  padrão ``topic_edges`` — FK composto não se aplica aí sem trocar a semântica
  ``ON DELETE SET NULL`` do DDL §5 (SET NULL em FK composto nularia também a
  coluna do dono, ``NOT NULL``).
- ``blocks.block_id`` determinístico persistido (§6.7, correção da 006a —
  migração ``0003``): coluna aditiva com UNIQUE ``(version_id, block_id)`` e
  backfill pela fórmula ``p{page}b{order%10⁴+1}``; a PK UUID do DDL §5
  permanece e a citação fecha pela coluna armazenada.
- ``tombstones`` (§5/§15.1, task 010 — migração ``0005``): catálogo de
  tombstones **sem payload** para impedir ressurreição de artefatos
  excluídos, com ``backup_pending_until`` (backup identificado como
  pendente até expiração) e **nenhum hash reversível** do texto excluído.

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

#: Migrações versionadas: ``(versão, descrição, SQL script)`` ou, quando a
#: migração exige reconstrução de tabela (alterar FK de tabela existente),
#: 4-tupla ``(versão, descrição, SQL script, requires_foreign_keys_off)`` —
#: ``PRAGMA foreign_keys`` é no-op dentro de transação, então o framework
#: desativa/restaura o pragma fora do ``BEGIN IMMEDIATE`` do script. Cada
#: script roda dentro de uma única transação (``BEGIN IMMEDIATE``), com FKs
#: habilitadas (restauradas ao final quando desativadas). A ordem da lista é a
#: ordem de aplicação; versões são monotônicas.
MIGRATIONS: list[tuple[int, str, str] | tuple[int, str, str, bool]] = []


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


def _migration_0002() -> tuple[str, bool]:
    """Ownership no nível do banco em FKs simples (§15.1 — correção da 004).

    Gaps corroborados por probes de dois revisores independentes: FKs simples
    aceitavam referência cruzada entre donos diferentes. Correção:

    - ``courses`` ganha ``UNIQUE(user_id, id)`` — índice único é pré-requisito
      de FK composto em SQLite (§15.1, linha 249).
    - ``documents.course_id`` vira FK composto ``(user_id, course_id)`` →
      ``courses(user_id, id)``. SQLite não altera a definição de FK de uma
      tabela existente, então a tabela é reconstruída pelo procedimento
      documentado (sqlite.org/lang_altertable.html): criar tabela nova, copiar,
      descartar a antiga e renomear — com ``foreign_keys=OFF`` durante a
      reconstrução (``DROP TABLE`` com FKs ativas dispararia a cascata de
      deleção sobre as tabelas filhas). O framework desativa/restaura o pragma
      fora da transação do script.
    - ``facts.supersedes``, ``attempts.response_event_id`` e
      ``assessments.supersedes``: FK composto **não se aplica** sem trocar a
      semântica ``ON DELETE SET NULL`` do DDL §5 — em FK composto, SET NULL
      nularia também a coluna do dono (``user_id``/``attempt_user_id``,
      ``NOT NULL``). Ownership garantido por trigger no padrão ``topic_edges``
      já existente (§15.1: "arestas de tópicos exigem mesmo dono/curso").
    - ``topics``/``topic_edges`` permanecem sem coluna ``user_id`` (o bloco DDL
      do §5 não as contém): ownership via cadeia ``courses.user_id`` + trigger
      de mesmo curso já existentes.

    Banco migrado do zero e banco que aplica esta migração sobre a ``0001``
    chegam ao mesmo estado (verificado por teste de equivalência de schema).
    Dados pré-existentes que cruzem donos ficam fora do escopo do MVP (não há
    base legada; a FK composto não é retroativa) — violações remanescentes
    seriam reportadas por ``PRAGMA foreign_key_check`` em verificação manual.
    """
    return (
        """
-- ---------------------------------------------------------------------------
-- (a) courses: chave única (user_id, id) — alvo da FK composto de documents
-- ---------------------------------------------------------------------------
CREATE UNIQUE INDEX uq_courses_user_id ON courses(user_id, id);

-- ---------------------------------------------------------------------------
-- (b) documents.course_id → FK composto (user_id, course_id) →
--     courses(user_id, id) — reconstrução documentada da tabela
-- ---------------------------------------------------------------------------
CREATE TABLE documents_new (
    id             TEXT PRIMARY KEY,                -- UUID
    user_id        TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id      TEXT NOT NULL,
    active_version TEXT,                            -- doc_versions.id; null = sem versão ativa
    FOREIGN KEY (user_id, course_id)
        REFERENCES courses(user_id, id) ON DELETE CASCADE
);
INSERT INTO documents_new(id, user_id, course_id, active_version)
    SELECT id, user_id, course_id, active_version FROM documents;
DROP TABLE documents;
ALTER TABLE documents_new RENAME TO documents;
CREATE INDEX idx_documents_user ON documents(user_id);
CREATE INDEX idx_documents_course ON documents(course_id);
-- Triggers de versão ativa recriados (descartados junto da tabela antiga).
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

-- ---------------------------------------------------------------------------
-- (c) facts.supersedes: mesmo dono (trigger, padrão topic_edges)
-- ---------------------------------------------------------------------------
CREATE TRIGGER facts_supersedes_same_owner_insert
BEFORE INSERT ON facts
WHEN NEW.supersedes IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'facts: supersedes deve referenciar fato do mesmo dono')
    WHERE (SELECT user_id FROM facts WHERE id = NEW.supersedes)
       <> NEW.user_id;
END;
CREATE TRIGGER facts_supersedes_same_owner_update
BEFORE UPDATE OF supersedes ON facts
WHEN NEW.supersedes IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'facts: supersedes deve referenciar fato do mesmo dono')
    WHERE (SELECT user_id FROM facts WHERE id = NEW.supersedes)
       <> NEW.user_id;
END;

-- ---------------------------------------------------------------------------
-- (d) attempts.response_event_id: mesmo dono (trigger, padrão topic_edges)
-- ---------------------------------------------------------------------------
CREATE TRIGGER attempts_response_event_same_owner_insert
BEFORE INSERT ON attempts
WHEN NEW.response_event_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'attempts: response_event_id deve referenciar evento do mesmo dono')
    WHERE (SELECT user_id FROM events WHERE id = NEW.response_event_id)
       <> NEW.user_id;
END;
CREATE TRIGGER attempts_response_event_same_owner_update
BEFORE UPDATE OF response_event_id ON attempts
WHEN NEW.response_event_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'attempts: response_event_id deve referenciar evento do mesmo dono')
    WHERE (SELECT user_id FROM events WHERE id = NEW.response_event_id)
       <> NEW.user_id;
END;

-- ---------------------------------------------------------------------------
-- (e) assessments.supersedes: mesmo dono (dono é attempt_user_id, §15.1)
-- ---------------------------------------------------------------------------
CREATE TRIGGER assessments_supersedes_same_owner_insert
BEFORE INSERT ON assessments
WHEN NEW.supersedes IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'assessments: supersedes deve referenciar avaliação do mesmo dono')
    WHERE (SELECT attempt_user_id FROM assessments WHERE id = NEW.supersedes)
       <> NEW.attempt_user_id;
END;
CREATE TRIGGER assessments_supersedes_same_owner_update
BEFORE UPDATE OF supersedes ON assessments
WHEN NEW.supersedes IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'assessments: supersedes deve referenciar avaliação do mesmo dono')
    WHERE (SELECT attempt_user_id FROM assessments WHERE id = NEW.supersedes)
       <> NEW.attempt_user_id;
END;
""",
        # Reconstrução de ``documents`` exige FKs desativadas fora da transação.
        True,
    )


def _migration_0003() -> str:
    """``blocks.block_id`` determinístico persistido (§6.7 — correção da
    006a).

    Gap corroborado pela revisão da 006 (probe P4): o ID determinístico
    ``p{n}b{n}`` era calculado e descartado, e ``source_refs_for_version``
    devolvia um ID que não fechava pela PK de ``blocks`` — citação §6.7 não
    resolvível de forma inequívoca. Correção: coluna ``block_id`` persistida
    com UNIQUE ``(version_id, block_id)``; linhas pré-existentes recebem
    backfill pela mesma fórmula determinística (``p{page}b{order%10⁴+1}``),
    então banco migrado e banco criado do zero chegam ao mesmo estado. O DDL
    lógico do §5 (``blocks(id PK, version_id, page, ...)``) não é alterado:
    a PK ``id`` (UUID) permanece e a coluna é aditiva.
    """
    return """
-- ---------------------------------------------------------------------------
-- blocks.block_id determinístico persistido (§6.7 — citação resolvível)
-- ---------------------------------------------------------------------------
ALTER TABLE blocks ADD COLUMN block_id TEXT;
UPDATE blocks
   SET block_id = 'p' || page || 'b' || (order_index % 10000 + 1)
 WHERE block_id IS NULL;
CREATE UNIQUE INDEX uq_blocks_version_block ON blocks(version_id, block_id);
"""


def _migration_0004() -> str:
    """Colunas de redução em ``attempts`` (§15.2 — task 009).

    O redutor determinístico precisa, por tentativa, da família do item
    (regra ``favorable``: famílias distintas) e do julgamento de
    independência (hint_level 0, sem reveal, sem acesso prévio à solução da
    família na sessão corrente — §15.2). ``family_id`` é derivável por JOIN
    com ``items``, mas ``independent`` é julgamento do commit (exposição da
    sessão) que precisa sobreviver ao purge de payloads de eventos (§5):
    coluna aditiva, default conservador 1 para linhas pré-existentes (nenhuma
    no MVP — tabela escrita a partir desta task).
    """
    return """
-- ---------------------------------------------------------------------------
-- attempts: família e independência para o redutor (§15.2, task 009)
-- ---------------------------------------------------------------------------
ALTER TABLE attempts ADD COLUMN family_id TEXT;
ALTER TABLE attempts ADD COLUMN independent INTEGER NOT NULL DEFAULT 1
    CHECK (independent IN (0,1));
CREATE INDEX idx_attempts_family ON attempts(user_id, family_id);
"""


def _migration_0005() -> str:
    """Catálogo de tombstones sem payload (§5/§15.1 — task 010).

    A deleção explícita precisa de catálogo para impedir ressurreição do
    artefato excluído (§5: "catálogo de tombstones sem payload") e para
    identificar o backup como **pendente até expiração** (§15.1: "backups
    identificados como pendentes até expiração"). Regras:

    - Nenhum payload: a tabela guarda apenas a referência (ID+versão), o
      motivo e o instante — **nenhum hash reversível do texto excluído**
      (§5: "não manter hash reversível de texto excluído"; o motivo é texto
      de política, não conteúdo do artefato).
    - ``backup_pending_until``: retenção de backup proposta de 30 dias
      (default de ensaio, §5/§15.1) para escopos parciais; deleção que
      remove todos os dados do usuário (backup conteria apenas esse
      usuário) registra ``NULL`` — remoção já na solicitação.
    """
    return """
-- ---------------------------------------------------------------------------
-- tombstones (§5 linha 125 / §15.1): catálogo sem payload
-- ---------------------------------------------------------------------------
CREATE TABLE tombstones (
    id                   TEXT PRIMARY KEY,         -- UUID
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    artifact_ref         TEXT NOT NULL,            -- '<prefixo>:<uuid>@<versão>'
    kind                 TEXT NOT NULL
        CHECK (kind IN ('fact','event','summary','data')),
    reason               TEXT NOT NULL,
    tombstoned_at        TEXT NOT NULL,
    backup_pending_until TEXT                       -- NULL = remoção na solicitação
);
CREATE INDEX idx_tombstones_user ON tombstones(user_id);
CREATE INDEX idx_tombstones_ref ON tombstones(user_id, artifact_ref);
"""


def _migration_0006() -> str:
    """Política evidência→demanda v1 e atividades (§15.3/§15.4 — task 011).

    - ``assessment_topics``: relação avaliação confirmada → tópicos (§15.3:
      "Referência a avaliação confirmada vem de relação
      ``assessment_topics``"). A avaliação (prova) é um fato acadêmico
      confirmado; a relação é por usuário (ownership §15.1).
    - ``demands``: colunas da chave de unicidade da política
      ``(user, topic, activity_kind, due_local_date, policy_version)`` —
      no máximo uma demanda pendente por chave (§15.3). Índice único
      parcial em ``status='pending'``: demandas consolidadas atualizam a
      linha pendente; subdemandas de decomposição (``status='split'``) e
      linhas fora da política (colunas NULL — NULL é distinto em índice
      único no SQLite) não colidem.
    - ``logical_blocks``: campos de atividade (§15.4/§15.5) — status de
      transição, instantes planejados/reais, demanda de origem,
      ``event_sequence`` (começa 0 e incrementa só quando campos de evento
      mudam, §15.5), conflito de término pendente de esclarecimento e o
      evento que disparou replan (uma vez por evento, §15.4).
    """
    return """
-- ---------------------------------------------------------------------------
-- assessment_topics (§15.3): relação avaliação confirmada → tópicos
-- ---------------------------------------------------------------------------
CREATE TABLE assessment_topics (
    user_id  TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fact_id  TEXT NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, fact_id, topic_id)
);
CREATE INDEX idx_assessment_topics_topic ON assessment_topics(user_id, topic_id);

-- ---------------------------------------------------------------------------
-- demands: chave de unicidade da política v1 (§15.3) — colunas aditivas
-- ---------------------------------------------------------------------------
ALTER TABLE demands ADD COLUMN topic_id TEXT;
ALTER TABLE demands ADD COLUMN activity_kind TEXT;
ALTER TABLE demands ADD COLUMN due_local_date TEXT;
ALTER TABLE demands ADD COLUMN policy_version TEXT;
CREATE UNIQUE INDEX uq_demands_pending_policy_key ON demands(
    user_id, topic_id, activity_kind, due_local_date, policy_version
) WHERE status = 'pending';
CREATE INDEX idx_demands_topic ON demands(user_id, topic_id, status);

-- ---------------------------------------------------------------------------
-- logical_blocks: campos de atividade (§15.4/§15.5)
-- ---------------------------------------------------------------------------
ALTER TABLE logical_blocks ADD COLUMN status TEXT NOT NULL DEFAULT 'planned'
    CHECK (status IN ('planned','started','completed','missed','cancelled'));
ALTER TABLE logical_blocks ADD COLUMN planned_start_utc TEXT;
ALTER TABLE logical_blocks ADD COLUMN planned_end_utc TEXT;
ALTER TABLE logical_blocks ADD COLUMN actual_start_utc TEXT;
ALTER TABLE logical_blocks ADD COLUMN actual_end_utc TEXT;
ALTER TABLE logical_blocks ADD COLUMN source_demand_id TEXT;
ALTER TABLE logical_blocks ADD COLUMN event_sequence INTEGER NOT NULL DEFAULT 0;
ALTER TABLE logical_blocks ADD COLUMN end_conflict INTEGER NOT NULL DEFAULT 0
    CHECK (end_conflict IN (0,1));
ALTER TABLE logical_blocks ADD COLUMN last_replan_event TEXT;
CREATE INDEX idx_logical_blocks_demand ON logical_blocks(user_id, source_demand_id);
"""


def _migration_0007() -> str:
    """Exportação ICS, confirmação e outbox (§9/§15.1/§15.5 — task 013).

    - ``logical_blocks``: campos de evento do ICS (§9/§15.5) —
      ``created_at`` alimenta CREATED; ``modified_at`` (última revisão
      persistida) alimenta DTSTAMP/LAST-MODIFIED; ``summary`` alimenta
      SUMMARY; ``value_type`` distingue all-day (``DATE``, fim exclusivo no
      dia seguinte) de DATE-TIME (UTC Z). ``event_sequence`` (migração 0006)
      alimenta SEQUENCE — começa em 0 e incrementa apenas se campos de
      evento mudam; retries/reexportações da mesma revisão não alteram
      timestamps (§9/§15.5).
    - ``confirmations``: conjunto/hash das dependências da aprovação
      (§15.1: "Confirmação guarda ``base_revision``, ``approval_revision``
      pós-commit e conjunto/hash das dependências") — a alteração posterior
      de dependência invalida a aprovação ainda não aplicada.
    """
    return """
-- ---------------------------------------------------------------------------
-- logical_blocks: campos de evento do ICS (§9/§15.5)
-- ---------------------------------------------------------------------------
ALTER TABLE logical_blocks ADD COLUMN created_at TEXT;
ALTER TABLE logical_blocks ADD COLUMN modified_at TEXT;
ALTER TABLE logical_blocks ADD COLUMN summary TEXT;
ALTER TABLE logical_blocks ADD COLUMN value_type TEXT NOT NULL
    DEFAULT 'DATE-TIME' CHECK (value_type IN ('DATE','DATE-TIME'));

-- ---------------------------------------------------------------------------
-- confirmations: dependências da aprovação (§15.1)
-- ---------------------------------------------------------------------------
ALTER TABLE confirmations ADD COLUMN dependencies_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE confirmations ADD COLUMN dependencies_hash TEXT
    CHECK (dependencies_hash IS NULL OR length(dependencies_hash) = 64);
CREATE INDEX idx_confirmations_artifact
    ON confirmations(user_id, artifact_id, artifact_revision);
"""


def _load_builtin() -> None:
    script_0002, fk_off_0002 = _migration_0002()
    MIGRATIONS.append(
        (1, "DDL completo do mapa §5 + artifact_dependencies (§15.1)", _migration_0001())
    )
    MIGRATIONS.append(
        (
            2,
            "Ownership no nível do banco: UNIQUE(user_id,id) em courses, "
            "FK composto em documents.course_id e triggers de mesmo dono "
            "(facts.supersedes, attempts.response_event_id, "
            "assessments.supersedes) — §15.1",
            script_0002,
            fk_off_0002,
        )
    )
    MIGRATIONS.append(
        (
            3,
            "blocks.block_id determinístico persistido com UNIQUE "
            "(version_id, block_id) e backfill — §6.7, correção da 006a",
            _migration_0003(),
        )
    )
    MIGRATIONS.append(
        (
            4,
            "attempts.family_id e attempts.independent para o redutor "
            "determinístico (famílias distintas e independência da "
            "tentativa) — §15.2, task 009",
            _migration_0004(),
        )
    )
    MIGRATIONS.append(
        (
            5,
            "catálogo de tombstones sem payload com backup pendente até "
            "expiração — §5/§15.1, task 010",
            _migration_0005(),
        )
    )
    MIGRATIONS.append(
        (
            6,
            "política evidência→demanda v1 e atividades: assessment_topics, "
            "chave de unicidade de demandas pendentes e campos de atividade "
            "em logical_blocks — §15.3/§15.4, task 011",
            _migration_0006(),
        )
    )
    MIGRATIONS.append(
        (
            7,
            "exportação ICS e confirmação: campos de evento do ICS em "
            "logical_blocks (created_at/modified_at/summary/value_type — "
            "§9/§15.5) e conjunto/hash das dependências da confirmação em "
            "confirmations (§15.1) — task 013",
            _migration_0007(),
        )
    )


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
    for entry in plan:
        version, description, script, *rest = entry
        requires_fk_off = bool(rest) and bool(rest[0])
        if _migration_applied(conn, version):
            continue
        if requires_fk_off:
            # ``PRAGMA foreign_keys`` é no-op dentro de transação: desativa
            # fora do BEGIN do script (reconstrução de tabela, migração 0002)
            # e restaura após o COMMIT — o perfil do §5 é FK sempre ativa.
            conn.execute("PRAGMA foreign_keys=OFF")
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
        finally:
            if requires_fk_off:
                conn.execute("PRAGMA foreign_keys=ON")
        applied_now.append(version)
        if log is not None:
            log(f"migração {version} aplicada ({description})")
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
