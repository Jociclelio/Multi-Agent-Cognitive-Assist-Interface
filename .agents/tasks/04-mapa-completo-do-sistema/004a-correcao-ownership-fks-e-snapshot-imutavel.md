# Task 004a: Correção da 004 — ownership em FKs simples e snapshot imutável efetivo (mapa §5, §15.1)

Estado: pendente
Depende de: 004
Origem: 004 — correção (revisão com decisão "corrigir"; entrega `519c32e` preservada, sem reversão)

## Prompt
Corrigir na camada de dados existente (`eduagent/storage/`) os gaps corroborados por pelo menos dois revisores da task 004, preservando a entrega anterior e sem alterar o mapa:

1. **Ownership no nível do banco (§15.1):** referências cruzadas entre donos diferentes são aceitas hoje por FKs simples, confirmadas por probes de dois revisores independentes:
   - `documents.course_id` aceita curso de outro `user_id` (`migrations.py` ~linha 132);
   - `facts.supersedes` (~213), `attempts.response_event_id` (~267) e `assessments.supersedes` aceitam referência a registro de outro dono.
   Correção esperada: criar `UNIQUE(user_id,id)` em `courses` (e onde a tabela pai exigir índice único para FK composto) e converter essas FKs para compostas `(user_id, id)` — ou, onde o FK composto não se aplicar, trigger que recuse referência entre donos, no padrão do trigger já existente em `topic_edges`. Teste obrigatório: tentativa de vincular documento a curso de outro dono (e os pares acima) é recusada no nível do banco, com teste cobrindo cada padrão.
2. **Imutabilidade efetiva do snapshot (C3 da 004):** `Snapshot` é dataclass com `content` dict mutável; mutar o dict após materialização altera o digest silenciosamente (probe de dois revisores). Correção esperada: `frozen=True` + cópia profunda/canonização do `content` no momento da materialização e digest calculado uma única vez e armazenado (não recalculado sob demanda); mutação externa do dict original não altera o artefato. Teste obrigatório: obter snapshot, mutar estruturas internas e/ou o objeto retornado, verificar que digest, `to_json()` e conteúdo do artefato permanecem estáveis.
3. **Contrato de erros:** `materialize_snapshot` de usuário inexistente levanta `TypeError: 'NoneType' object is not subscriptable` (`repository.py` ~452-457); corrigir para `EduAgentError` com código `SOURCE_UNRESOLVED`, no padrão de `write_transaction`/`commit_operation`/`domain_revision`. Teste obrigatório do caso.
4. **Decisões explícitas registradas em Evidências (sem mudança silenciosa):**
   - purge × revisão: manter `purge_event_payloads` com `bump_domain_revision=False` é aceitável, mas registre a decisão e a ressalva de que um snapshot materializado antes do purge pode hidratar payload já excluído (avaliar na 005/006 quando eventos entrarem em replay);
   - `expected_version` opcional (`None` pula validação) em `execute_write`/`write_transaction` e `add_artifact_dependency`: ou torne obrigatório para escritas de domínio ou registre a exceção como escolha de ensaio com justificativa.

Restrições: fonte normativa única `fase2/documentos/04_mapa_completo_do_sistema.md` INTOCADO; **não adicionar coluna `user_id` a `topics`/`topic_edges`** — o bloco DDL do §5 não as contém; ownership de tópicos/arestas permanece via cadeia `courses.user_id` + trigger de mesmo curso já existente; registre essa resolução em Evidências. Migração nova versionada em `schema_migrations` (não reescrever a `0001` já aplicada); garantir que banco migrado do zero e banco que aplica a migração nova sobre a `0001` cheguem ao mesmo estado. Suíte existente (94 testes) deve permanecer verde. Commits separados: entrega (código/testes) e registro (task.md com SHAs/evidências), sem amend/force-push/commits vazios. Mapa, submodule `docs/playground-llmagenticsystem`, `config/`, `pyproject.toml` e `uv.lock` intocados; nada apresentado como resultado medido; temporários em `/tmp/opencode`.

## Contexto
- `.agents/tasks/04-mapa-completo-do-sistema/004-armazenamento-ddl-migracoes-snapshot.md` — task mãe; seção Revisão com os achados A1–A4 por revisor que motivam esta correção.
- `eduagent/storage/migrations.py` — DDL das 23 tabelas, migração `0001`, triggers existentes (padrão do trigger de `topic_edges`).
- `eduagent/storage/repository.py` — `Snapshot`, `materialize_snapshot`, `write_transaction`, `commit_operation`, `purge_event_payloads`.
- `tests/test_task004_storage.py` — suíte da 004 a estender.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §5 (DDL, ownership) e §15.1 (FK composto onde aplicável, snapshot imutável); §15 prevalece quando mais preciso.

## Corretude
- [ ] C1 — Migração nova versionada aplica sobre a `0001` e do zero chega ao mesmo estado; `UNIQUE(user_id,id)` em `courses` e FKs compostos/triggers de ownership ativos; probes de referência cruzada entre donos (`documents.course_id`, `facts.supersedes`, `attempts.response_event_id`, `assessments.supersedes`) são todos recusados no nível do banco (testado por padrão).
- [ ] C2 — Snapshot imutável efetivo: `frozen=True`, `content` canonizado/copiado na materialização, digest calculado uma vez; mutação pós-materialização não altera digest/`to_json()`/conteúdo (testado); suíte completa (94 + novos) verde.
- [ ] C3 — `materialize_snapshot` de usuário inexistente levanta `EduAgentError(SOURCE_UNRESOLVED)` (testado); decisões de purge × revisão e `expected_version` opcional registradas explicitamente em Evidências.
- [ ] C4 — Mapa intocado (sem coluna nova em `topics`/`topic_edges`); commits de entrega e registro separados; submodule, `config/`, `pyproject.toml` e `uv.lock` intocados.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
4/10 — Escopo delimitado e padrões já estabelecidos na 004 (trigger de mesmo curso, índice único para FK composto); risco moderado em migração incremental idempotente e em congelar estruturas aninhadas do snapshot.

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
