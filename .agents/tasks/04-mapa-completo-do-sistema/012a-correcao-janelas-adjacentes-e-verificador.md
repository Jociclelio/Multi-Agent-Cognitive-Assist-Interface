# Task 012a: Correção — semântica de janelas adjacentes/sobrepostas alinhada entre enumerador e verificador (mapa §9, §15.5)

Estado: aguardando revisão
Depende de: 012
Origem: 012 — correção (entrega `34fe505` preservada; decisão `corrigir` da revisão da 012)

## Prompt
Corrigir na entrega da 012 (`eduagent/services/scheduling.py`) a inconsistência entre a enumeração de candidatos e o verificador quando há janelas de disponibilidade **adjacentes ou sobrepostas no mesmo dia**: o enumerador constrói runs contíguos sobre a **união** das janelas (região ~`scheduling.py:1793-1848`), mas o verificador exige contenção em **uma única** janela (região ~`scheduling.py:2286-2296`), fazendo `schedule.solve` devolver `INTERNAL_FAILURE` para entrada confirmada legítima (ex.: janelas 8:15–9:15 e 9:15–10:15 com demanda obrigatória de 90 min — reproduzido pela sonda da revisão). Escolha **uma** semântica, alinhe os dois lados e registre a escolha como decisão de codificação: (a) verificador valida cobertura pela união das janelas do dia, ou (b) enumerador restringe candidatos a janela única. A semântica deve preservar o contrato do §15.5: disponibilidade arredondada para dentro por janela, bloqueios para fora, capacidade em minutos efetivamente reservados e nenhuma saída inválida publicada — `INTERNAL_FAILURE` continua reservado a contradição interna genuína, não a entrada confirmada válida. No mesmo commit de teste, acrescente um teste que **fixe a identidade do diff** preservada entre preview e proposta (movida mantém `block_id`/`uid`; duas ocorrências distintas nunca colidem na mesma identidade), respondendo com prova ao ponto retirado na revisão da 012. Não altere `fase2/documentos/04_mapa_completo_do_sistema.md` (INTOCADO), `config/default.yaml` nem `docs/playground-llmagenticsystem`. Commits de entrega e registro separados, sem amend/force-push/commits vazios, sem push. Defaults numéricos da config são escolhas de ensaio — nada é resultado medido. Suite integral deve terminar verde.

## Contexto
- `eduagent/services/scheduling.py` — enumerador de candidatos (runs sobre união de janelas), `_verify_placement`/`verify_schedule` (contenção em janela única) e `_expected_diff`/`_mint_identity` (identidade do diff).
- `tests/test_task012_solver_verifier.py` — G1–G15, L1–L12, V1–V8, K1–K2, R1; acrescente regressões aqui.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §9 e §15.5 (arquivo INTOCADO; "deve" é contrato; §15 prevalece).
- Task mãe `.agents/tasks/04-mapa-completo-do-sistema/012-solver-cpsat-lexicografico-e-verificador.md` — decisão da revisão, achado A1 (médio, com sonda) e residuais A2/A3 documentados (NÃO reabertos nesta correção).

## Corretude
- [x] C1 — Com janelas adjacentes (ex.: 8:15–9:15 e 9:15–10:15) e demanda obrigatória de 90 min, `schedule.solve` retorna solução válida publicável (ou INFEASIBLE provado se a capacidade não permitir), nunca `INTERNAL_FAILURE` para entrada confirmada legítima; teste de regressão cobre também janelas sobrepostas. — **Comprovado**: sonda `/tmp/opencode/012a_sonda_adjacentes.py` reproduziu `INTERNAL_FAILURE` antes da correção e `OPTIMAL` + validação passed depois; regressões J1 (adjacentes) e J2 (sobrepostas, sem janela única que caiba a demanda, solução cruza a emenda) verdes.
- [x] C2 — A semântica escolhida está aplicada dos dois lados (enumerador e verificador) sem divergência; decisão de codificação registrada na task com justificativa contra §15.5; bloqueios e arredondamento por janela preservados. — **Comprovado**: decisão (a) abaixo; enumerador já construía runs sobre a união (inalterado), verificador alinhado via `_merged_availability`; J3 prova que vão entre janelas disjuntas continua rejeitado ("bloqueios para fora", §9).
- [x] C3 — Teste novo prova que a identidade do diff é preservada: movida mantém `block_id`/`uid` entre preview e proposta, e duas ocorrências distintas não colidem na mesma identidade. — **Comprovado**: J4 — `diff.moved == [block_id 201]` com `uid 301` preservado na proposta; adições disjuntas das movidas; identidades `(block_id, uid)` todas distintas; `_mint_identity` com `block|occ ≠ uid|occ` e ocorrências distintas gerando identidades distintas.
- [x] C4 — Suite integral verde (≥ 412 testes); mapa normativo, `config/default.yaml` e submodule intocados; commits de entrega e registro separados. — **Comprovado**: 414 passed (18,75 s, `pytest -q --ignore=runner-llm --ignore=docs`; coleção interrompida pelos testes de terceiros do runner de llama.cpp, fora do projeto — mesmo critério das rodadas anteriores); `git status` sem alteração em `fase2/`, `config/` e no submodule; entrega `f82a626` e registro separados.

## Decisão de codificação — semântica de janelas adjacentes/sobrepostas

**Escolha: (a) — o verificador valida cobertura pela união das janelas do dia** (`_merged_availability`, nova, usada em `_verify_placement`); o enumerador permanece como está, pois já constrói runs contíguos sobre a união dos slots utilizáveis.

Justificativa contra §15.5/§9:
1. A grade (`_usable_slots`) marca como utilizáveis os slots da **união** das janelas do dia (arredondamento para dentro **por janela**), e o enumerador gera "candidatos contíguos" (§9) sobre esses slots — runs cruzam emendas de janelas adjacentes por construção. O verificador deve **reaplicar a mesma restrição** nos minutos/instantes originais (§9: "Verificador separado reaplica restrições em minutos/instantes originais"); exigir contenção em janela única aplicava ao verificador uma restrição mais forte do que a que gerou os candidatos, divergência que se manifestava como `INTERNAL_FAILURE` (contradição interna, §15.5) para entrada confirmada legítima — exatamente o que §15.5/§12 reservam a defeito genuíno, não a resultado.
2. Os contratos de §15.5 permanecem: disponibilidade segue arredondada para dentro **por janela** na grade; bloqueios (compromissos/fixos) seguem para fora, por slot; capacidade diária continua em minutos efetivamente reservados; nenhuma saída inválida é publicada. A união no verificador é calculada sobre as janelas **originais**, sem arredondamento — superconjunto da união arredondada da grade, logo todo candidato do solver passa e blocos fabricados que mergulhem em vão entre janelas disjuntas continuam rejeitados (J3).
3. A alternativa (b) — restringir o enumerador a janela única — reduziria candidatos legítimos (um bloco contíguo sobre a emenda é tempo disponível em cada minuto) e fragilizaria o objetivo de deslocamento mínimo no replanejamento; exigiria também mudança na grade, que hoje é união por slots. Menos fiel ao §9 ("arredondar disponibilidade para dentro e bloqueios para fora" fala de janelas como conjunto de tempo disponível, não de contenção por janela individual).

## Execução
- Modelo: GLM-5.3-Flash (via ~/sd2-llm.sh; provider `sd2`, model `GLM-5.3-Flash`)
- Base: `3e99e33cfa5f7f2fe71817dd5a0bac5f793c9cc9`
- Entrega: `f82a626c46d8a8d2494fc387e1f0083a97ffbacf`
- Arquivos da entrega: `eduagent/services/scheduling.py`; `tests/test_task012_solver_verifier.py`
- Evidências:
  - Sonda da revisão reproduzida antes da correção: `.venv/bin/python /tmp/opencode/012a_sonda_adjacentes.py` → `EduAgentError code=INTERNAL_FAILURE — solução do solver falhou no verificador independente: bloco …: fora das janelas de disponibilidade originais` (achado A1 confirmado). Após a correção: `STATUS: OPTIMAL; BLOCO 08:45→10:15 UTC; VALIDACAO: True []`.
  - Regressões: `.venv/bin/python -m pytest tests/test_task012_solver_verifier.py -q` → **42 passed** (38 anteriores + J1–J4).
  - Suíte integral: `.venv/bin/python -m pytest -q --ignore=runner-llm --ignore=docs` → **414 passed, 2 warnings in 18.75 s** (≥ 412; os 2 erros de coleção sem os ignores vêm de `runner-llm/third_party/llama.cpp/tools/server/tests`, ambiente de terceiros do runner de llama.cpp, fora do escopo do projeto e das rodadas anteriores da 012).
  - Intocados verificados: `git status --porcelain` antes do commit listava apenas os dois arquivos da entrega; `fase2/documentos/04_mapa_completo_do_sistema.md`, `config/default.yaml` e `docs/playground-llmagenticsystem` sem alteração.
  - Limitações: verificação por testes locais de curta duração; nenhum ensaio de tempo publicado (defaults de `solver_budget_s`/`slot_minutes` são escolhas de ensaio da config, não resultados medidos). Residuais A2 (deslocamento em minutos vs slots) e A3 (bound da etapa 1) da revisão da 012 permanecem documentados na task mãe, não reabertos aqui.

## Notas

### Dificuldade esperada
4/10 — correção delimitada com decisão de semântica e regressões; o risco está em escolher a semântica sem quebrar V1–V8 e G9–G12 existentes.

### Dificuldade sentida
3/10 — Correção delimitada e bem caracterizada pela sonda da revisão: a decisão de semântica (a) foi direta porque a grade e o enumerador já operavam sobre a união das janelas, restando alinhar o verificador; o cuidado principal foi preservar V1–V8 e G9–G12 (todos verdes sem alteração) e provar, no J3, que a união não afrouxa bloqueios para fora. O único ajuste de teste foi o tipo de `diff.moved` (UUID, não string).

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
