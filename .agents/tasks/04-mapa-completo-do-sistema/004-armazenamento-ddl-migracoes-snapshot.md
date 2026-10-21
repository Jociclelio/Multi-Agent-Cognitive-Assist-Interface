# Task 004: Armazenamento — DDL, migrações, snapshot e domain_revision (mapa §5, §15.1)

Estado: aguardando revisão
Depende de: 003
Origem: nenhuma

## Prompt
Implementar a camada de dados do mapa §5 e §15.1 em `eduagent/storage/`: DDL lógico completo (todas as tabelas do bloco §5: `users`, `courses`, `topics`, `topic_edges`, `documents`, `doc_versions`, `blocks`, `chunks`, `facts`, `events`, `items`, `attempts`, `assessments`, `topic_states`, `summaries`, `demands`, `plans`, `logical_blocks`, `operations`, `outbox`, `confirmations`, `schema_migrations`), com `user_id` em toda tabela de domínio, FK e constraints habilitados, e `artifact_dependencies(user_id, child_ref, parent_ref, relation)` com relações `derived_from/corrects/supersedes` indexadas nos dois sentidos (§15.1). Migrações versionadas em `schema_migrations`; SQLite WAL/FULL, escritor serializado, transações curtas. `users.domain_revision` monotônica: toda operação nova que muda domínio incrementa o contador na mesma transação (retries não incrementam); `expected_version`/`snapshot_version` são esse contador (§15.1). Snapshot materializado em transação de leitura curta (fatos/agenda/projeções/versões ativas/ref hashes → artefato imutável); agentes não mantêm conexão aberta nem hidratam versão atual silenciosamente; controle conservador por usuário no MVP. Ownership: FK composto `(user_id,id)` onde aplicável; arestas de tópicos exigem mesmo dono/curso. Eventos brutos preservados para auditoria com exclusão explícita de payloads pessoais possível; proibido hash reversível de texto excluído.

Nota do master (da revisão da task 001, achado A1): `data/<user_id>/` foi criado como diretório literal com colchetes angulares. Nesta task, decida explicitamente o destino do placeholder (manter como documentação, substituir por `data/_template/` ou criar diretórios por usuário em runtime) e registre a escolha em Evidências — sem alterar o mapa.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §5 (DDL, WAL, deleção, backup inicial) e §15.1 (snapshot, ownership, invalidação).
- `eduagent/storage/{repository,migrations,checkpoints}.py` (stubs da 001); contratos da 003.

## Corretude
- [x] C1 — Migração do zero cria todas as tabelas com colunas/FK/UNIQUE conforme §5 (+ `artifact_dependencies`); segunda aplicação é no-op.
- [x] C2 — WAL/FULL ativo; escrita concorrente serializada; toda escrita mutável valida revisão esperada e `domain_revision` incrementa uma única vez por operação nova (testado).
- [x] C3 — Snapshot materializado como artefato imutável em leitura curta; leitura posterior a escrita exige reload (controle por usuário testado).
- [x] C4 — Mapa intocado; commits separados; submódulo não tocado.

## Execução
- Modelo: GLM-5.3-Flash (via ~/sd2-llm.sh; provider `sd2`, model `GLM-5.3-Flash`)
- Base: 1e3f042bd81d6a193f061641d0f95c7b92ff42d2 (árvore limpa; dependência 003/003a fechada)
- Entrega: 519c32efc34441cc4cd1737e2b869c91c9fb479a
- Arquivos da entrega: `eduagent/storage/migrations.py`, `eduagent/storage/repository.py`, `tests/test_task004_storage.py`, `README-eduagent.md` (linha `data/<user_id>/` → `data/_template/`), renomeação `data/<user_id>/{originals,derived,indexes,exports}/.gitkeep` → `data/_template/...` (diff do commit de entrega)
- Evidências:
  - **Placeholder `data/<user_id>/` (nota do master, achado A1 da 001) — decisão: substituir por `data/_template/`.** Motivo: diretório literal com colchetes angulares é um placeholder inválido como nome de usuário real e ambíguo para código; `data/_template/` preserva a documentação da estrutura (`{originals,derived,indexes,exports}` com `.gitkeep`) sem nome inválido. Executado com `git mv 'data/<user_id>' data/_template` (renomeação rastreada, 4 `.gitkeep` preservados). Criação de diretórios por usuário em runtime fica para a task 006 (ingestão), que é a primeira consumidora dos diretórios — nesta task não há código de ingestão para ancorar a criação. Linha correspondente do `README-eduagent.md` atualizada; `fase2/documentos/04_mapa_completo_do_sistema.md` INTOCADO. Nenhuma referência a `data/<user_id>` permanece fora do mapa e dos registros históricos de tasks (verificado por grep).
  - **C1 — DDL completo e migração idempotente.** Migração `0001` em `eduagent/storage/migrations.py` contém as 21 tabelas do bloco §5 + `artifact_dependencies` (23 tabelas totais, incluindo `schema_migrations`). Verificação independente: script que parseia o bloco ```text do §5 do mapa (linhas 100–122) e cruza cada `tabela.coluna` com `PRAGMA table_xinfo` no banco recém-migrado → zero colunas faltantes; os únicos "ausentes" do parser eram artefatos de parse de constraints inline `UNIQUE(parent_id,child_id)` e `UNIQUE(attempt_id,assessor_version)`, conferidos manualmente como presentes/refinados (ver abaixo). Testes: `test_all_tables_created_from_scratch` (23 tabelas), `test_second_application_is_noop` (segunda aplicação retorna `[]` e não altera `sqlite_master`), `test_migration_is_atomic_on_failure` (script quebrado → rollback, sem `ok1` nem registro de versão).
  - **Refinamento normativo UNIQUE de assessments:** o DDL §5 (linha 114) escreve `UNIQUE(attempt_id,assessor_version)`, mas §15.2 define "Unicidade lógica `(attempt_id,assessment_revision)`, não apenas versão do modelo" (linha 257). Implementado `uq_assessments_attempt_revision ON assessments(attempt_id, assessment_revision)` (refinamento de §15.2, que prevalece); `assessor_version` permanece como coluna no payload. UNIQUE(parent_id,child_id) de topic_edges implementado inline.
  - **C2 — WAL/FULL, escritor serializado, revisão esperada, incremento único.** `DomainStore.open` aplica `journal_mode=WAL`, `synchronous=FULL` (2), `foreign_keys=ON`, `busy_timeout=5000` (default de ensaio); teste `test_wal_pragmas` verifica os três PRAGMAs e `test_wal_persists_in_file` confirma WAL persistente no arquivo reaberto por conexão nova. Piso SQLite 3.51.3 (mapa §3) verificado por `require_wal_capable_sqlite` — runtime do projeto embarga SQLite 3.53.1 (posterior à série corrigida; verificação de configuração, não backport necessário). `commit_operation` idempotente: mesmo `operation_id`+`digest` devolve o recibo original sem incrementar (testado: `test_domain_revision_increments_once_per_new_operation` — revision 1→2, retry mantém 2); `digest` diferente com mesmo ID → `SCHEMA_INVALID` (§4); falha de statement faz ROLLBACK completo sem incremento (`test_operation_failure_does_not_bump_revision`); metadados operacionais (receipt/lease) com `bump_domain_revision=False` não incrementam (§15.1 linha 247).
  - **C3 — snapshot imutável em leitura curta, reload obrigatório.** `materialize_snapshot` copia fatos/topic_states/demandas/planos/versões ativas/ref hashes em transação `BEGIN DEFERRED` fechada no fim (nenhuma conexão retida); artefato `Snapshot` com `snapshot_version = users.domain_revision`, `digest` SHA-256 do JSON canônico e `to_json()` imutável. Testes: `test_snapshot_immutable_and_versioned` (digest estável, version = domain_revision, escrita → version+1 e digest diferente), `test_stale_snapshot_write_requires_reload` (escrita com `expected_version` do snapshot velho → VERSION_CONFLICT; `require_fresh` recusa e reload resolve), `test_snapshot_reads_do_not_bump_revision` (3 materializações, revisão constante), `test_snapshot_isolated_per_user` (conteúdo de UID2 não vaza no snapshot de UID).
  - **Ownership adicional testado:** `test_valid_topic_edge_accepted` (aresta válida aceita) e `test_topic_edges_require_same_course` (aresta entre cursos de donos diferentes recusada pelo trigger "parent e child devem pertencer ao mesmo curso"); `test_dependencies_are_user_scoped` e `test_purge_scoped_to_owner` (percurso de dependências e purge confinados ao dono).
  - **Suíte:** `.venv/bin/python -m pytest tests/ -q` → **94 passed** (63 da 003/003a + 31 novos), 0,37s. Comando executado no venv do projeto (CPython 3.12.13, SQLite 3.53.1).
  - **Intocados:** `fase2/documentos/04_mapa_completo_do_sistema.md` (git diff vazio), `.agents/plans/04-mapa-completo-do-sistema/plan.md`, submodule `docs/playground-llmagenticsystem` (git status vazio), `config/default.yaml`, `pyproject.toml`, `uv.lock` (nenhuma dependência nova — apenas stdlib + `eduagent.contracts` já existente). Commits: entrega `519c32e` e registro (este) separados.
  - **Limitações:** verificação contratual local; nenhum experimento executado, nada medido. `busy_timeout=5000` é default de ensaio. `commit_operation` pré-implementa o caminho idempotente do §11 na camada de dados; outbox/dispatcher/recuperação de crash/replay completos são da task 005. Diretórios por usuário em runtime ficam para a task 006 (primeira consumidora dos diretórios).

## Notas

### Dificuldade esperada
5/10 — Muitas tabelas e invariantes de ownership/revision; risco de constraint faltante.

### Dificuldade sentida
5/10 — Alinhada à expectativa. O volume de tabelas/invariantes foi mecânico; o esforço real concentrou-se em armadilhas de runtime do SQLite: `executescript` faz COMMIT implícito e roda em autocommit (quebrava a atomicidade da migração — corrigido com BEGIN/COMMIT dentro do próprio script), CHECK de coluna comparada não pode ser satisfeito por trigger `AFTER UPDATE` (corrigido com coluna gerada), FK composta exige índice único `(user_id,id)` explícito na tabela pai, e `PRAGMA table_info` omite colunas geradas. O bug do no-op (`SELECT` em `schema_migrations` antes de ela existir) foi pego pelo próprio teste C1.

### Revisão
- Orquestrador: —
- Alvo: —
- Avaliações: —
- Nota final: —
- Parecer: —
- Decisão: pendente
- Reversão: —
- Próximo passo: —

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
