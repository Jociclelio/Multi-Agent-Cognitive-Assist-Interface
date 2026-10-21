# Task 004: Armazenamento — DDL, migrações, snapshot e domain_revision (mapa §5, §15.1)

Estado: pendente
Depende de: 003
Origem: nenhuma

## Prompt
Implementar a camada de dados do mapa §5 e §15.1 em `eduagent/storage/`: DDL lógico completo (todas as tabelas do bloco §5: `users`, `courses`, `topics`, `topic_edges`, `documents`, `doc_versions`, `blocks`, `chunks`, `facts`, `events`, `items`, `attempts`, `assessments`, `topic_states`, `summaries`, `demands`, `plans`, `logical_blocks`, `operations`, `outbox`, `confirmations`, `schema_migrations`), com `user_id` em toda tabela de domínio, FK e constraints habilitados, e `artifact_dependencies(user_id, child_ref, parent_ref, relation)` com relações `derived_from/corrects/supersedes` indexadas nos dois sentidos (§15.1). Migrações versionadas em `schema_migrations`; SQLite WAL/FULL, escritor serializado, transações curtas. `users.domain_revision` monotônica: toda operação nova que muda domínio incrementa o contador na mesma transação (retries não incrementam); `expected_version`/`snapshot_version` são esse contador (§15.1). Snapshot materializado em transação de leitura curta (fatos/agenda/projeções/versões ativas/ref hashes → artefato imutável); agentes não mantêm conexão aberta nem hidratam versão atual silenciosamente; controle conservador por usuário no MVP. Ownership: FK composto `(user_id,id)` onde aplicável; arestas de tópicos exigem mesmo dono/curso. Eventos brutos preservados para auditoria com exclusão explícita de payloads pessoais possível; proibido hash reversível de texto excluído.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §5 (DDL, WAL, deleção, backup inicial) e §15.1 (snapshot, ownership, invalidação).
- `eduagent/storage/{repository,migrations,checkpoints}.py` (stubs da 001); contratos da 003.

## Corretude
- [ ] C1 — Migração do zero cria todas as tabelas com colunas/FK/UNIQUE conforme §5 (+ `artifact_dependencies`); segunda aplicação é no-op.
- [ ] C2 — WAL/FULL ativo; escrita concorrente serializada; toda escrita mutável valida revisão esperada e `domain_revision` incrementa uma única vez por operação nova (testado).
- [ ] C3 — Snapshot materializado como artefato imutável em leitura curta; leitura posterior a escrita exige reload (controle por usuário testado).
- [ ] C4 — Mapa intocado; commits separados; submódulo não tocado.

## Notas

### Dificuldade esperada
5/10 — Muitas tabelas e invariantes de ownership/revision; risco de constraint faltante.

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

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
