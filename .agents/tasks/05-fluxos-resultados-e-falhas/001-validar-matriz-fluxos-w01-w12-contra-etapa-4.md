# Task 001: Validar a matriz de fluxos W01–W12 contra a etapa 4 e a v0.1 implementada

Estado: fechada (decisão: fechar — revisão 9/10, quórum aprovado)
Depende de: nenhuma
Origem: nenhuma

## Prompt
Conferir a seção 1 ("Universo de tarefas") de `fase2/documentos/05_fluxos_resultados_e_falhas.md` — a matriz de fluxos W01–W12 — contra a especificação v0.1 (`fase2/documentos/04_mapa_completo_do_sistema.md`, seções de intenções/rotas/estados, em especial §10) e contra o MVP já implementado (tasks 001–017 do plano 04-mapa-completo-do-sistema, código em `eduagent/`). Para cada fluxo, registrar em Evidências a conferência item a item: gatilho/sequência corresponde a rotas existentes da etapa 4 (e do grafo implementado); saídas esperadas citam apenas IDs O existentes (O01–O18); variações/término incluem sucesso, espera, conflito, abstinência, cancelamento e falha controlada. Conferir que pedidos compostos são decompostos em rotas existentes, sem criar capacidades ilimitadas, e que a regra "novos conectores/skills exigem revisão desta matriz" está presente. Se encontrar desvio de fidelidade ou contradição com a etapa 4, corrija **apenas o documento 05** em dif mínimo, preservando o sentido normativo do fonte (etapa 4), e registre a correção em Evidências.

Alinhamentos obrigatórios com a v0.1 implementada (nada no documento pode contradizer o sistema entregue): curadoria sem conector de busca configurado é `CONNECTOR_DISABLED` (W09 mantém o fluxo com gate de rede/cache); sync de calendário é opcional com `[→outbox→sync]` entre colchetes (W08); timezone permanece pendente de confirmação (nenhum fluxo presume `America/Sao_Paulo` fixado); reranker não adotado; `MODEL_NOT_ADMITTED` bloqueia tutoria; não-admitidos (busca, Google) não aparecem como capacidades garantidas.

Restrições: `fase2/documentos/04_mapa_completo_do_sistema.md` é INTOCADO ("deve" é contrato; §15 prevalece quando especifica regra mais precisa); `05_fluxos_resultados_e_falhas.md` é o entregável — manutenção/revisão permitida somente em dif mínimo com justificativa; nada apresentado como resultado medido; IDs W01–W12 e O01–O18 permanentes; prosa em português; `python3 fase2/scripts/verificar_documentos.py` deve passar após as alterações; commit de entrega (documento, se houver correção) e commit de registro (task.md) separados, sem amend/force-push/commits vazios; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — documento a materializar (entregável): seção 1, tabela W01–W12 (linhas 3–20).
- `fase2/documentos/04_mapa_completo_do_sistema.md` — especificação v0.1 (fonte normativo, intocado): intenções/estados, §10 rotas do grafo, §6/§9 módulos opcionais.
- `eduagent/` e `eval/relatorio-testes-mvp.md` — sistema implementado (planos 04, tasks 001–017): rotas reais, questões abertas preservadas.
- `fase2/scripts/verificar_documentos.py` — verificação documental (exige presença de W01–W12, O01–O18, F01–F24).

## Corretude
- [x] C1 — Cada um dos 12 fluxos conferido item a item contra a etapa 4 e a implementação (gatilho/sequência, saídas citadas, variações/término), com registro em Evidências; desvios corrigidos no documento 05 em dif mínimo ou justificados.
- [x] C2 — Decomposição de pedidos compostos sem capacidades ilimitadas e a regra de revisão da matriz por novos conectores/skills confirmadas no texto; nenhum fluxo contraria a v0.1 (CONNECTOR_DISABLED, sync opcional, timezone pendente, não-admitidos).
- [x] C3 — `python3 fase2/scripts/verificar_documentos.py` passa; mapa intocado; commits entrega/registro separados; nada como resultado medido.

## Execução
- Modelo: GLM-5.3-Flash (via ~/sd2-llm.sh; provider `sd2`, model `GLM-5.3-Flash`) — identidade informada pelo runtime
- Base: 8bed49a50bb0f93fc444504970770ae9d6e4c79a
- Entrega: sem alteração de artefatos — conferência de fidelidade não revelou desvio que exigisse correção no documento 05; nenhum diff necessário
- Arquivos da entrega: nenhum modificado; conferência sobre `fase2/documentos/05_fluxos_resultados_e_falhas.md` (seção 1, linhas 3–20), `fase2/documentos/04_mapa_completo_do_sistema.md` (§§1–15), grafo implementado (`eduagent/graph.py`) e `eval/relatorio-testes-mvp.md`
- Evidências: conferência item a item dos 12 fluxos contra o §10 do mapa e o grafo implementado (`eduagent/graph.py`, nós e arestas `classify`→rotas):
  - **W01** = rota `ingest → extract → curator_facts → validate → confirm_if_needed → commit/index` (nós `ingest_extract, curator_facts, ingest_validate, confirm_if_needed, commit_index`); saídas O01/O02 existem; variações (digital, scan, tabela, duplicata, revisão; ilegível/oversized explícitos) batem com §6 itens 1–3. ✓
  - **W02** = rota `ask/practice → snapshot → curator_retrieve + librarian_retrieve → context → tutor → validate → publish/wait`; O03/O04; abstinência e "geral rotulada" batem com §6 itens 7–8. ✓
  - **W03** = mesma rota de `practice` com skills (`eduagent/skills/{explain,graduated_hint,quiz,flashcard,self_explain}`); O05–O07; "separar solução", recusa interrompe pistas e "espera não gera chamadas" batem com §8 e §10 (espera = fim da invocação). ✓
  - **W04** = rota `submit_answer → resolve_pending_item → monitor → validate → commit → feedback → optional_review_request` (nós `resolve_pending_item, monitor_node, answer_validate, commit_assessment, feedback, optional_review_request`); O08/O09; corretude `correct/partial/incorrect/undecidable` e "não produz nota oficial" batem com §4/§8/§15.2. ✓
  - **W05** = recuperação de memória (§7) via snapshot + `librarian_retrieve`; O10/O11; "não inventar continuidade" bate com §8 ("ausência de prática torna evidência antiga"). ✓
  - **W06** = rota `plan/replan → snapshot → planner_demands → confirm_if_needed → solver → independent_check → preview → wait` (nós presentes); O12/O13; statuses viável/ótimo/inviável provado/inconclusivo/ambíguo batem com §9 (OPTIMAL/FEASIBLE/INFEASIBLE/UNKNOWN/MODEL_INVALID). ✓
  - **W07** = replan com novo snapshot reusando W06; O13 (diff e déficit) e O09 (revisão); blocos fixos (§9), duração estimada transparente (§8/§15.3) e "nenhum overwrite silencioso" (§15.1) batem. ✓
  - **W08** = rota `export_calendar → resolve_approved_plan → render_ics → validate → publish [→ confirmed_outbox]` (nós `resolve_approved_plan, render_ics, ics_validate, publish_ics`); sync fica **entre colchetes** `[→outbox→sync]`, opcional, coerente com §9 e com `calendar_sync_enabled=false`/`calendar.apply → CONNECTOR_DISABLED` na v0.1; O14; "sem rede exporta local; timeout→reconciliação, não duplicata" bate com §9/§11. ✓
  - **W09** = rota `curate → network_gate → search/fetch → curator_rank → validate_access_claims` (nós presentes); mantém o fluxo **com gate de rede/cache** (mecanismo que produz `CONNECTOR_DISABLED` sem conector configurado — `eduagent/graph.py` nó `network_gate`; relatório de testes linha 30); O15; metadata-only sem resumo e "sem resumo fictício" batem com §6; busca não é apresentada como capacidade garantida. ✓
  - **W10** = rotas `memory_query` e `correct_fact/delete_data → validate_scope → preview → confirm → commit/invalidate` (nós presentes); O10/O16; propagação a derivados e conflito→esclarecimento batem com §5/§15.1. ✓
  - **W11** = rota `cancel → stop_dispatch → reconcile_started_effects → persist → cancelled` (nós presentes) + recuperação §11; O16/O17; retomada idempotente, `RESOURCE_LIMIT` e `UNKNOWN_EFFECT` presentes nos erros tipados (§4). ✓
  - **W12** = CLI `doctor/backup/restore` (§12, `eduagent/cli.py`) + verificador de integridade/replay (§5); O18; "não anunciar sucesso sem check" explícito. ✓
  - **Saídas citadas**: todos os IDs citados na matriz (O01–O18) existem na tabela da seção 2; nenhum ID fora da faixa ou inexistente. ✓
  - **Variações/término**: sucesso, espera (W02/W03/W06), conflito (W06/W08/W10), abstinência (W02/W04), cancelamento (W11) e falha controlada (W01/W12) estão cobertos na coluna "Variações e término". ✓
  - **Pedidos compostos e regra de revisão**: o parágrafo de abertura da seção 1 mantém "Pedidos compostos são decompostos em rotas existentes, sem criar capacidades ilimitadas" e "Novos conectores/skills exigem revisão desta matriz". ✓ (C2)
  - **Alinhamentos obrigatórios com a v0.1**: nenhuma ocorrência de `America/Sao_Paulo` fixado, reranker adotado ou resultado medido no documento 05 (grep sem ocorrências); sync permanece opcional entre colchetes; `MODEL_NOT_ADMITTED` não é contradito (nenhum fluxo garante tutoria sem modelo validado); busca e Google não aparecem como capacidades garantidas. ✓ (C2)
  - **Verificador**: `python3 fase2/scripts/verificar_documentos.py` → `status: passed`, 12 fluxos, 18 saídas, 24 falhas, 39 links locais. ✓ (C3)
  - **Mapa intocado**: `git status` limpo antes e depois; nenhum diff em `fase2/documentos/04_mapa_completo_do_sistema.md`; submódulo não tocado. ✓ (C3)
  - Limitação: conferência é documental/estática (leitura do grafo e das seções do mapa + grep); não reexecutei a suíte pytest (fora do escopo desta task documental), e o grafo implementado foi conferido por leitura de `eduagent/graph.py`, não por execução de rotas.

## Notas

### Dificuldade esperada
3/10 — Conferência de fidelidade tabela-a-especificação com documento já materializado; risco baixo de inflar resultado, mas exige leitura atenta do mapa §10 e do sistema implementado.

### Dificuldade sentida
4/10 — A conferência em si é de baixo risco, mas exige leitura atenta e cruzada de três fontes (tabela do documento 05, §10/§15 do mapa e nós/arestas reais em `eduagent/graph.py`); o maior cuidado foi resistir à tentação de "melhorar" redações do documento 05 sem desvio de fidelidade que as justificasse, mantendo o dif zero.

### Revisão
- Orquestrador: GLM-5.3-Flash (provider `sd2`) — master do ciclo opt-in, sessão dedicada
- Alvo: base `8bed49a50bb0f93fc444504970770ae9d6e4c79a`; entrega **sem commit de artefatos** (conferência sem desvio → dif zero no documento 05); registro `ac4222c0be065d2ff8d12c558482c8c74b7b486e` (commit único documental, apenas este task.md)
- Modo da rodada: sequencial — reproduz o padrão dos ciclos anteriores do plano 04 (revisores executam o verificador documental e sondagens de leitura sobre o mesmo ambiente/venv compartilhado da raiz, evitando disputa de recursos); três sessões novas, um modelo por sessão
- Avaliações: GLM-5.3-Flash (sd2): 9/10 — aprovada; qwen3-27b (sorgan-qwen): 9/10 — aprovada; gpt-6-luna (openai): 9/10 — aprovada
- Nota final: 9/10
- Parecer: convergência factual total entre os três revisores nos critérios C1–C3, cada um com sondagens independentes. C1: matriz W01–W12 confere rota a rota com o §10 do mapa e com `eduagent/graph.py` (nós/arestas citados presentes); saídas citadas restringem-se a O01–O18 existentes; variações cobrem sucesso, espera (W02/W03/W06), conflito (W06/W08/W10), abstinência (W02/W04), cancelamento (W11) e falha controlada (W01/W12); dif zero justificado — as sondagens negativas dos três revisores não encontraram desvio de fidelidade. C2: decomposição de pedidos compostos e regra de revisão da matriz presentes no parágrafo de abertura (linha 5); `[→outbox→sync]` no W08; gate de rede/cache no W09; zero ocorrências de `America/Sao_Paulo`, reranker adotado, resultado medido ou busca/Google como capacidade garantida; `MODEL_NOT_ADMITTED` não contradito (confirmado em `eduagent/contracts.py:302`, `CONNECTOR_DISABLED` em `graph.py:508,2429` e relatório linha 30). C3: verificador documental `passed` (12 fluxos, 18 saídas, 24 falhas, 39 links) reproduzido pelos três; `git diff 8bed49a..HEAD` afeta apenas o task.md — mapa 04, documento 05 e submódulo intocados; árvore limpa; commits entrega/registro trivialmente separados (não há commit de entrega). Divergências: apenas de profundidade de reprodução (GLM e qwen inspecionaram o grafo linha a linha; luna com sondagens mais enxutas), sem contradição essencial. Achados relevantes: dois de impacto baixo, do qwen (R1: `task.md:34` cita "§4/§8/§15.2" para "não produz nota oficial", expressão literal ausente do mapa — paráfrase fiel no documento 05 linha 12; R2: `task.md:37` cita "§15.1" para "overwrite silencioso", quando o §15.1 diz "nunca undo silencioso" — paráfrase fiel no documento 05 linha 15): imprecisões de citação de seção SOMENTE no registro, sem efeito no entregável; registradas como observação editorial, sem reabrir a task. GLM registrou observação menor análoga (abstinência em W04 apoiada em O08/indecidível, não no texto literal da linha) — leitura justificável. Limitações declaradas: conferência estática (sem execução de rotas nem suíte pytest), coerente com escopo documental da task e corretamente registrada em Evidências. Nenhum critério obrigatório pendente.
- Decisão: fechar
- Reversão: não se aplica — sem artefatos
- Próximo passo: task liberada — `.agents/tasks/05-fluxos-resultados-e-falhas/002-validar-qualidade-saidas-o01-o18.md` (dependência 001 resolvida)

<!-- task-cycle: {"decision":"fechar","next_task":".agents/tasks/05-fluxos-resultados-e-falhas/002-validar-qualidade-saidas-o01-o18.md","family":".agents/tasks/05-fluxos-resultados-e-falhas/001-validar-matriz-fluxos-w01-w12-contra-etapa-4.md","plan":".agents/plans/05-fluxos-resultados-e-falhas/plan.md"} -->

Plano: [plan.md](../../plans/05-fluxos-resultados-e-falhas/plan.md)
