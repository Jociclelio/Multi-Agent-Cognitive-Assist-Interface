# Task 014a: Correção da 014 — segurança de paths/fetch e limites sob fan-out

Estado: aguardando revisão
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
- Base: `8985b45de8e7b493a2098827048c54d245607fd5` (criação da subtask; árvore limpa, entrega `6968403` e registro `121a0e7` da 014 preservados sem reversão)
- Entrega: `3b7bce8916d5fd81767c3ead0f326f238140a4c2`
- Arquivos da entrega: `eduagent/policy.py`, `eduagent/graph.py`, `eduagent/storage/checkpoints.py`, `tests/test_task014_graph.py`
- Evidências:
  - **C1** — Sondas reproduzidas ANTES da correção (`/tmp/opencode/sonda_014a_antes.py`; saída "antes" com S-1 `.`/`""` aceitos resolvendo para o próprio root, S-2 `//10.0.0.1/evil` aceito como `http://93.184.216.34//10.0.0.1/evil` sem revalidar): após a correção, `.`/`""`/`..` recusados com `TOOL_DENIED` e redirect protocol-relative recusado com `TOOL_DENIED` (saída em `/tmp/opencode/sonda_014a_depois.txt`). Regressões: `test_user_id_ponto_vazio_e_traversal_recusados`, `test_redirect_protocol_relative_revalidado` (IPs literais; sem rede real).
  - **C2** — `test_turn_limits_contagem_exata_sob_concorrencia`: 8 threads × 200 consumos com janela de preempção forçada por subclassificação que só instrumenta o escalonamento (`time.sleep(0)` na leitura do contador; semântica de produção executada integralmente) — contagem exata (1000 sucessos, 600 recusas, restantes 0) prova o RLock; a mesma técnica reproduziu atualizações perdidas ANTES do fix na sonda (S-5: 1600 sucessos vs 522 decrementos). `test_checkpointer_list_sob_lock`: proxy de conexão prende o INSERT do `put` segurando o lock e `list()` aguarda (pré-fix lia a conexão em paralelo). `test_begin_step_precedencia_deadline_antes_de_passos`: deadline e limite de passos esgotados simultaneamente → terminal `TIMEOUT`; cancelamento continua com prioridade (`CANCELLED`).
  - **C3** — `test_fila_cheia_preserva_orcamento_de_llm`: fila cheia recusa com `RESOURCE_LIMIT` e `llm_calls_remaining` preservado (`GenerationGate` reembolsa via `TurnLimits.refund_llm`; recusa de enqueue não consome o turno). `test_web_fetch_revalida_destino_final_sempre` (DNS rebinding simulado por `getaddrinfo` substituído: destino final revalidado mesmo com URL original) e `test_web_fetch_revalida_cada_hop_da_cadeia` (`redirect_chain` com hop público passa; hop privado recusado por código; pré-condição contratual registrada no nó para o conector real da 016).
  - **C4** — Suíte integral reexecutada: `python -m pytest tests/ -q` → **490 passed** (482 da base + 8 regressões novas) em ~24 s, sem regressões. `git status` limpo após a entrega; mapa (`fase2/documentos/04_mapa_completo_do_sistema.md`), config e submódulo `docs/playground-llmagenticsystem` intocados (diff confinado aos 4 arquivos listados); commits de entrega e registro separados, sem amend/force-push.
  - Limitações declaradas: a sonda S-5 sem instrumentação de escalonamento não manifesta a corrida de forma confiável (janela estreita do GIL) — a prova determinística usa a subclassificação documentada no teste; A5 é verificado pelo teste de exclusão mútua acima (comportamento observável), não por varredura de corrida.

## Notas

### Dificuldade esperada
3/10 — Correções pontuais e delimitadas com sondas já descritas pela revisão; risco baixo de regressão além da suíte existente.

### Dificuldade sentida
3/10 — Correções pontuais e delimitadas conforme previsto, com sondas descritas pela revisão. As duas sutilezas foram: (1) a corrida de contadores (A3) não se manifesta de forma confiável sem instrumentar o escalonamento — a prova determinística exigiu subclassificação com pontos de preempção documentados no teste, preservando a semântica de produção; (2) "revalidar sempre o destino final" (A4) só é distinguível da validação anterior simulando DNS rebinding (substituição de `getaddrinfo`), já que com URL final idêntica não há sinal observável sem controlar a resolução. Precedência em `begin_step` e reembolso de orçamento foram diretos; nenhuma regressão na suíte existente.

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
