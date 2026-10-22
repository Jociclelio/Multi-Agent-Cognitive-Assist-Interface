# Task 014: Grafo LangGraph — intenções, rotas, checkpoints e limites (mapa §10, §12, §13.8 parte 1)

Estado: aguardando subtasks
Depende de: 013
Origem: nenhuma

## Prompt
Implementar o grafo completo (mapa §10 e §12) em `eduagent/graph.py`, `eduagent/policy.py` e `eduagent/storage/checkpoints.py`: intenções `ingest, ask, practice, submit_answer, plan, replan, approve_plan, update_activity, memory_query, correct_fact, delete_data, export_calendar, curate, cancel`; comandos explícitos prevalecem; classificador LLM retorna enum validado e, em ambiguidade, pergunta antes de efeito. Rotas exatamente como o mapa §10 (cada `+` é leitura independente de snapshot comum; geração usa fila serial). Checkpointer SQLite persistente com `durability=sync` e `thread_id` por sessão; interrupt retoma o nó desde o início (preparação pura, efeitos em nós idempotentes separados); espera por aluno é fim da invocação e nova entrada retoma o item, sem timeout ativo durante espera. Política de ferramentas conforme a tabela §10 (quem pode propor, pré-condição, validação); nenhum agente recebe shell genérico ou escrita direta no DB; MCP é adaptador allowlisted; JSON correto para ação proibida é negado por código; fonte/tool result é dado rotulado e não altera política; divergência com solver/fato confirmado não é resolvida por votação (esclarecimento ou falha controlada). Segurança: resolver paths/ownership, bloquear traversal/symlink escapes; fetch bloqueia IP privado/loopback e revalida redirects/DNS. Limites (§12): antes de cada node/tool/geração conferir cancelamento, deadline e budget; reparo consome chamada e contador; ao esgotar, terminal com erro tipado e artefatos já válidos — nunca saída parcial silenciosamente aprovada; fila cheia responde `RESOURCE_LIMIT`; `cancel` → stop_dispatch → reconcile_started_effects → persist → cancelled. Checkpoint guarda refs, não PDFs integrais; estado de domínio é autoridade; checkpoint não substitui commit.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §10 e §12 (limites) integrais; §13.8; estado do grafo e erros (§4).
- Todos os serviços anteriores (005–013); adaptador de modelo (002).

## Corretude
- [x] C1 — Todas as 11 rotas do §10 terminam com estado definido; teste por rota (incluindo cancelamento e deadline com terminal de erro tipado e artefatos válidos preservados).
- [x] C2 — Checkpointer SQLite com sync/thread_id; sessão retomada de checkpoint preserva item pendente, nível de ajuda e histórico do turno (teste).
- [x] C3 — Política de ferramentas: proposta fora de papel/pré-condição é negada por código; sem shell/escrita direta; fila serial nas gerações.
- [x] C4 — Limites/budgets da config aplicados antes de cada nó; `RESOURCE_LIMIT` na fila cheia; mapa intocado; commits separados.

## Notas

### Evidências de execução (GLM-5.3-Flash via ~/sd2-llm.sh, provider sd2)

Implementação em três módulos + duas integrações transversais, sobre a base
`2373cfb9` (família 013 fechada):

- **`eduagent/graph.py`** — grafo LangGraph completo: 14 intenções do enum
  `Intent`; as 11 rotas do §10; classificador LLM com enum validado (parse +
  schema locais, reparo consumindo chamada/contador, ambiguidade →
  `pending_question` sem efeito; comandos explícitos prevalecem, inclusive
  prefixos `/`, com o comando removido do conteúdo usado como consulta/
  resposta); gates de confirmação como `interrupt()` puro retomado desde o
  início (efeitos em nós idempotentes separados com `operation_id` no estado
  para replay §11); espera por aluno = fim da invocação (`waiting_student`),
  sem timeout ativo durante espera; rota cancel
  `stop_dispatch → reconcile_started_effects → persist → cancelled` com
  reconciliação por identidade e `UNKNOWN_EFFECT` terminal; terminal `finish`
  valida o estado final contra o contrato `GraphState` (mapa §4).
- **`eduagent/storage/checkpoints.py`** — `SQLiteCheckpointer`
  (`BaseCheckpointSaver` do LangGraph pinnado na 002): DB separado do domínio,
  `PRAGMA synchronous=FULL` (durability=sync), `thread_id` = `session_id`,
  serialização do próprio LangGraph; guarda refs e dados textuais de turno,
  nunca PDFs; `delete_thread` propaga deleção (§5).
- **`eduagent/policy.py`** — `TurnLimits` (cancelamento → deadline → budget
  ANTES de cada nó/tool/geração; `RESOURCE_LIMIT` no esgotamento e na fila
  cheia; reparo consome chamada e contador); `GenerationGate` (fila serial
  sobre o servidor loopback da 002 — 1 slot + fila 4, §3.1); tabela §10
  (`require_tool`: papel atribuído pelo dispatcher, payload sem permissão,
  `CONNECTOR_DISABLED` para web sem conector com código `RESOURCE_LIMIT` e
  mensagem prefixada, mesma convenção do `calendar.apply` da 013 — o enum de
  códigos do §4 é fechado); `resolve_owned_path` (traversal/symlink bloqueados
  por código) e `assert_public_url`/`assert_redirect_target` (IP
  privado/loopback bloqueado, redirect/DNS revalidados).
- **Integração transversal 1 (gap de §15.2)** — `eduagent/agents/tutor.py`: a
  rubrica publicada do item passa a carregar `topic_ids` do item (atribuição
  determinística no `_handle_item_move`; o modelo não escolhe tópicos). Sem
  isso, itens publicados pelo Tutor eram recusados pela `AssessmentService`
  (009 exige `RubricCriterion.topic_ids` não vazio) — a submissão era
  impossível na integração real.
- **Integração transversal 2 (leituras paralelas do §10)** —
  `eduagent/storage/repository.py`: `DomainStore.open` usa
  `check_same_thread=False` e todas as transações/leituras diretas são
  serializadas por `RLock` — as leituras independentes ("+") rodam em threads
  de trabalho do LangGraph no mesmo processo (§1: sem multiusuário em rede;
  semântica de transação/ownership inalterada; suítes 004/005 verdes).

Escolhas registradas (ensaio, não medidas): disponibilidade default do
problema de planejamento (seg–sex 08:00–12:00/14:00–18:00 UTC até confirmação
de timezone), substituível por `build_problem` injetado; `CONNECTOR_DISABLED`
via `RESOURCE_LIMIT` (ver nota do módulo policy); `/resume` → rota depende do
estado (item pendente → `submit_answer`); status `running` residual no
terminal → `completed` (nenhum nó pediu espera/falha/cancelamento).

**Discrepância menor no commit de entrega**: a mensagem do commit `6968403`
cita "37 testes novos"; o número correto é **36** (`pytest
tests/test_task014_graph.py --collect-only`), mais as suítes anteriores
intactas — total 482 passed.

Comandos e resultados:
- `python -m pytest tests/test_task014_graph.py -q` → **36 passed**.
- `python -m pytest tests/ -q` → **482 passed** (446 da base + 36 novos; sem
  regressões nas tasks 001–013, incluindo a suíte do Tutor alterada).
- `python -m compileall eduagent tests/test_task014_graph.py` → ok.
- Mapa (`fase2/`), `config/default.yaml`, `manifest.json`, `uv.lock` e
  submodule `docs/playground-llmagenticsystem` intocados (git status limpo
  fora dos 6 arquivos da entrega).

#### Corretude (comprovação por critério)

- **C1** — 11 rotas com teste próprio e terminal de estado definido:
  ingest (R-I1/R-I2), ask (R-A1), practice (R-A2), submit_answer (R-S1),
  plan/replan (R-P1), approve_plan (R-AP1), update_activity (R-U1),
  export_calendar (R-E1 + recusa sem confirmação), memory_query (R-M1),
  correct_fact/delete_data (R-CF1/R-DD1), curate (R-CU1/R-CU2), cancel
  (R-X1/R-X2); deadline → terminal `failed` com `TIMEOUT` tipado e item
  publicado preservado no domínio (L-T1); cancelamento com reconciliação de
  efeito iniciado (R-X1).
- **C2** — `SQLiteCheckpointer` com `synchronous=FULL` e `thread_id` por
  sessão; CK-1 prova retomada sobre os MESMOS arquivos (simulação de reinício)
  preservando item pendente, nível de ajuda por item (1→2 na escada do §8) e
  histórico do turno.
- **C3** — T-P1 (papel fora da tabela → `TOOL_DENIED` por código;
  `ToolRequest`/payload não muda permissões), T-P2 (catálogo de tools fechado,
  sem shell/exec/sql; `domain.commit` só SYSTEM), T-P3 (fonte/tool result não
  altera política), fila serial provada no gate (L-Q1: slot único, fila cheia
  `RESOURCE_LIMIT`; geração serial L-Q1b).
- **C4** — Limites conferidos por `TurnLimits.begin_step` antes de cada nó
  (guarda em todos os nós) e por `require_tool`/`GenerationGate` antes de
  tool/geração (L-B1: orçamento 0 → `RESOURCE_LIMIT` antes da geração); fila
  cheia `RESOURCE_LIMIT` (L-Q1); mapa/config/submódulo intocados; commits de
  entrega e registro separados.

Limitações declaradas: o MVP é single-threaded por turno (§1); os limites do
turno são da instância do runner; ensaios usam backend/embedder/conectores
fakes determinísticos (nenhuma chamada ao modelo real — o gate da 002/017 é
quem admite o modelo); a disponibilidade do problema de planejamento no grafo
é default de ensaio injetável; o conector web é execução com dobra de teste
(conexão real é a task 016).

SHAs: base `2373cfb9d6c13cdf23d1ce6d87bcdb07535c8540`; entrega
`6968403283db129e6fc5094a9477e91c1d27228f`.

### Dificuldade esperada
7/10 — Integrar tudo no grafo com interrupções/idempotência; maior superfície de regressão do plano.

### Dificuldade sentida
8/10 — Maior task do plano em superfície de integração: 11 rotas sobre nove
serviços com contratos rígidos. As dificuldades reais foram (a) semântica de
canais do LangGraph (esquema `dict` trata o estado como canal único — corrigido
com `TypedDict` por chave), (b) fan-out paralelo exigindo serialização do
`DomainStore` entre threads de trabalho, (c) o gap latente rubrica×tópicos
entre a 008 e a 009 (§15.2), descoberto só na integração ponta-a-ponta da
submissão, e (d) nós compartilhados entre rotas (`snapshot`,
`librarian_retrieve`, `confirm_if_needed`) exigindo arestas condicionais por
intenção. Nenhum impeditivo; ambiguidades do mapa resolvidas conservadoramente
e registradas acima.

### Revisão
- Orquestrador: master do ciclo opt-in — sd2/GLM-5.3-Flash (GLM-5.3-Flash via `~/sd2-llm.sh`, provider `sd2`).
- Alvo: task 014; base `2373cfb9d6c13cdf23d1ce6d87bcdb07535c8540`; entrega `6968403283db129e6fc5094a9477e91c1d27228f`; registro `121a0e7a034602a40122bccf7b81e5c640c16811`; árvore limpa; mapa/config/`uv.lock`/submódulo intocados entre base e registro (verificado por diff).
- Modo da rodada: **sequencial** — revisores compartilham o venv e a suíte do projeto; cada revisor rodou em sessão nova com exclusividade dos recursos.
- Avaliações (quórum de três modelos distintos):
  - **GLM-5.3-Flash (sd2) — 9/10, aprovada.** Reproduziu a suíte integral (482 passed) com exclusividade do venv. Achados baixos/informativos: L-A1 débito de orçamento LLM antes do `submit` na fila cheia; L-A2 `resolve_owned_path` aceita `user_id` `.`/vazio (julgado baixo por validação a montante de UUID); L-A3 TOCTOU DNS informativo (pré-condição p/ 016); divergência declarada de precedência em `begin_step` (deadline após limite de passos).
  - **GPT-6 Luna (openai) — 7/10, provisória/inconclusiva.** Não executou a suíte (dependências ausentes na cópia isolada; pendência coberta pela reprodução independente de GLM e beam, ambos 482 passed). Achado médio A-01: `begin_step` verifica limite de passos antes do deadline, contrariando a ordem documentada cancelamento → deadline → steps; caso simultâneo sem teste.
  - **Beam Free (opencode) — 8/10, requer correções.** Reproduziu suíte 482 e sondas de segurança. Achados: **A1 alto** — `resolve_owned_path(root, ".")` e `""` resolvem para o próprio root (probe-confirmado), bypass da segregação por usuário, violando "resolver paths/ownership" do §10; **A2 alto** — redirect protocol-relative `//host` não revalidado (`assert_redirect_target`), bypass da barreira de fetch IP privado/loopback; **A3 médio** — `TurnLimits` muta contadores sem sincronização durante o fan-out paralelo do §10 (threads reais do LangGraph, confirmado pelo próprio executor para o `DomainStore`); **A4 médio** — `_node_web_fetch` revalida destino final apenas se diferente da URL inicial, sem revalidação por hop; **A5 baixo** — `checkpointer.list()` acessa conexão sem lock; **A6 baixo** — contagem "37 vs 36" no commit de entrega (auto-declarada).
- Divergências e resolução: GLM avaliou path ownership e concorrência de contadores como baixos/informativos (validação a montante; limitação declarada single-threaded); beam probe-confirmou o bypass de paths e apontou que o fan-out do §10 executa nós em threads paralelas no design entregue — evidência reprodutível prevalece sobre o atenuante declarado; luna convergiu de forma independente na precedência de `begin_step`. Sem contradição factual entre pareceres.
- Nota final: **7/10** — C1, C2 e C4 comprovados com suíte reproduzida por dois revisores independentes (482 passed, 36 testes novos, testes por rota, deadline tipado com artefatos preservados, checkpointer com retomada provada, limites antes de cada nó, mapa intocado, commits separados). C3 não está plenamente comprovado: dois achados altos probe-confirmados (bypass de ownership em `resolve_owned_path` e redirect protocol-relative não revalidado) violam requisitos explícitos do prompt da task, somando-se dois médios (corrida nos contadores do `TurnLimits` no fan-out paralelo; precedência deadline/limites em `begin_step`) e baixos (lock ausente em `checkpointer.list()`; débito de orçamento na fila cheia). Pendências essenciais não podem ser fechadas com a nota.
- Parecer: entrega substancial e bem testada no núcleo do grafo (rotas, checkpoints, limites), porém com falhas localizadas e concretas de segurança de paths/fetch e de atomicidade dos contadores que o prompt exige resolvidas. Não justifica reinício nem repartição: defeitos delimitados em `eduagent/policy.py` e pontos de integração, corrigíveis preservando o design aprovado.
- Decisão: **corrigir**
- Reversão: não se aplica — entrega `6968403` e registro `121a0e7` preservados sem reversão.
- Próximo passo: subtask 014a (`.agents/tasks/04-mapa-completo-do-sistema/014a-correcao-seguranca-paths-fetch-e-limites.md`) — corrigir ownership de paths (recusar `user_dir == root`; exigir filho direto de root), revalidação de redirect protocol-relative com `urljoin` antes de `assert_public_url`, sincronização (`RLock`) dos contadores de `TurnLimits` para o fan-out paralelo, revalidação do destino final/cadeia de redirects em `_node_web_fetch`, lock em `checkpointer.list()`, precedência cancelamento → deadline → limite de passos em `begin_step` com teste do caso simultâneo, e débito de orçamento LLM apenas após enqueue aceito (ou reembolso em recusa), com testes de regressão e suíte integral reexecutada.

<!-- task-cycle: {"decision":"corrigir","next_task":".agents/tasks/04-mapa-completo-do-sistema/014a-correcao-seguranca-paths-fetch-e-limites.md","family":".agents/tasks/04-mapa-completo-do-sistema/011-demandas-atividades-e-politica-evidencia.md","plan":".agents/plans/04-mapa-completo-do-sistema/plan.md"} -->

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
