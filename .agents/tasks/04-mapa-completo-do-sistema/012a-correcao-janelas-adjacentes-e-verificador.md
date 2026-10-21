# Task 012a: Correção — semântica de janelas adjacentes/sobrepostas alinhada entre enumerador e verificador (mapa §9, §15.5)

Estado: pendente
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
- [ ] C1 — Com janelas adjacentes (ex.: 8:15–9:15 e 9:15–10:15) e demanda obrigatória de 90 min, `schedule.solve` retorna solução válida publicável (ou INFEASIBLE provado se a capacidade não permitir), nunca `INTERNAL_FAILURE` para entrada confirmada legítima; teste de regressão cobre também janelas sobrepostas.
- [ ] C2 — A semântica escolhida está aplicada dos dois lados (enumerador e verificador) sem divergência; decisão de codificação registrada na task com justificativa contra §15.5; bloqueios e arredondamento por janela preservados.
- [ ] C3 — Teste novo prova que a identidade do diff é preservada: movida mantém `block_id`/`uid` entre preview e proposta, e duas ocorrências distintas não colidem na mesma identidade.
- [ ] C4 — Suite integral verde (≥ 412 testes); mapa normativo, `config/default.yaml` e submodule intocados; commits de entrega e registro separados.

## Execução
- Modelo: _preencher pelo executor_
- Base: _SHA antes da implementação_
- Entrega: _SHA(s) completos, sem commits de registro_
- Arquivos da entrega: _paths_
- Evidências: _comandos, resultados e limitações_

## Notas

### Dificuldade esperada
4/10 — correção delimitada com decisão de semântica e regressões; o risco está em escolher a semântica sem quebrar V1–V8 e G9–G12 existentes.

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
