# Task 014a: Correção da 014 — segurança de paths/fetch e limites sob fan-out

Estado: pendente
Depende de: 014
Origem: 014 (correção — decisão `corrigir` da revisão, nota 7/10)

## Prompt
Corrigir pontualmente a entrega da 014 (`6968403283db129e6fc5094a9477e91c1d27228f`, registro `121a0e7a034602a40122bccf7b81e5c640c16811`, base `2373cfb9d6c13cdf23d1ce6d87bcdb07535c8540`), preservando o design aprovado. Correções exigidas pelos achados da revisão (task 014, seção Revisão):

1. **A1 alto — ownership de paths** (`eduagent/policy.py`, `resolve_owned_path`): sondas confirmaram `resolve_owned_path(root, ".")` e `resolve_owned_path(root, "")` resolvendo para o próprio `root`, escapando da guarda `user_dir != root and user_dir.parent != root`. Exigir que o diretório do usuário seja **subdiretório direto de `root`** (recusar `user_dir == root` e qualquer resolução fora do filho direto); manter traversal/symlink bloqueados. Teste de regressão com `.` e `""` recusados por código.
2. **A2 alto — redirect protocol-relative** (`eduagent/policy.py`, `assert_redirect_target`): `assert_redirect_target("http://example.com/a", "//127.0.0.1/evil")` retornava `http://example.com//127.0.0.1/evil` sem revalidar o host. Resolver o alvo com `urllib.parse.urljoin` (trata `//host` como host absoluto) antes de `assert_public_url`, ou tratar explicitamente `location` iniciando com `//`. Sonda da revisão deve passar após a correção.
3. **A3 médio — corrida nos contadores de `TurnLimits`** (`eduagent/policy.py`): o fan-out do §10 (`["curator_retrieve","librarian_retrieve"]`) executa nós em threads do LangGraph e `begin_step`/`consume_tool`/`consume_llm` mutam contadores sem sincronização. Serializar as mutações com `threading.RLock` (ou consumo fora do fan-out) sem mudar a semântica dos limites; teste com consumos concorrentes provando contagem exata.
4. **A4 médio — revalidação de redirect em `_node_web_fetch`** (`eduagent/graph.py`): revalidar sempre o destino final (não apenas se `final_url != url`) e, se o conector expuser cadeia de hops, revalidar cada hop com `assert_redirect_target`; registrar como pré-condição contratual para o conector real da 016.
5. **A5 baixo — lock no `checkpointer.list()`** (`eduagent/storage/checkpoints.py`): envolver o acesso a `self._conn` em `list()` com o mesmo lock de `get_tuple`/`put`.
6. **Precedência em `begin_step`** (achado médio da luna): alinhar a ordem de verificação à documentada cancelamento → deadline → limite de passos; cobrir em teste o caso com deadline e limite de passos esgotados simultaneamente (terminal `TIMEOUT`).
7. **Débito de orçamento na fila cheia** (L-A1 do GLM, baixo): `GenerationGate.generate` debita `limits.consume_llm()` antes do `submit`; na recusa `RESOURCE_LIMIT` o orçamento é consumido sem geração. Debitar somente após enqueue aceito ou reembolsar em recusa, com teste da contagem de orçamento na fila cheia.

Restrições vigentes do ciclo: mapa (`fase2/documentos/04_mapa_completo_do_sistema.md`) INTOCADO; §15 prevalece; defaults numéricos são escolhas de ensaio; commits de entrega e registro SEPARADOS, sem amend/force-push/commits vazios; submodule `docs/playground-llmagenticsystem` intocado; temporários em `/tmp/opencode`. Nada pode ser apresentado como resultado medido.

## Contexto
- `.agents/tasks/04-mapa-completo-do-sistema/014-grafo-langgraph-intencoes-rotas-checkpoints.md` — task mãe com a Revisão (achados A1–A6, L-A1–L-A3, A-01) e evidências.
- `eduagent/policy.py` — `resolve_owned_path`, `assert_public_url`/`assert_redirect_target`, `TurnLimits`, `GenerationGate`.
- `eduagent/graph.py` — `_node_web_fetch`, fan-out do §10, `_guarded`.
- `eduagent/storage/checkpoints.py` — lock do `SQLiteCheckpointer`.
- `tests/test_task014_graph.py` — suíte existente (36 testes) onde as regressões novas entram.

## Corretude
- [ ] C1 — Sondas da revisão reproduzidas ANTES da correção e recusadas/devidas DEPOIS: `resolve_owned_path` com `.`/`""` recusado por código; redirect protocol-relative `//host` bloqueado contra IP privado/loopback (teste).
- [ ] C2 — `TurnLimits` com contagem exata sob consumos concorrentes (teste com threads); `checkpointer.list()` sob lock; precedência cancelamento → deadline → limite de passos provada no caso simultâneo (terminal `TIMEOUT`).
- [ ] C3 — Débito de orçamento LLM somente com geração real/enqueue aceito (fila cheia preserva orçamento — teste); revalidação do destino final de fetch sempre aplicada.
- [ ] C4 — Suíte integral reexecutada sem regressões (482 + regressões novas); mapa/config/submódulo intocados; commits de entrega e registro separados.

## Execução
- Modelo: sd2/GLM-5.3-Flash (executor do ciclo; correção pontual, sem exigência de troca de modelo — decisão foi `corrigir`, não `reiniciar`)
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
3/10 — Correções pontuais e delimitadas com sondas já descritas pela revisão; risco baixo de regressão além da suíte existente.

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
