# Task 012: Solver CP-SAT lexicográfico e verificador independente (mapa §9, §15.5, §13.7 parte 1)

Estado: aguardando subtasks
Depende de: 011
Origem: nenhuma

## Prompt
Implementar o solver e o verificador (mapa §9 e §15.5) em `eduagent/services/scheduling.py` com a ferramenta `schedule.solve`: horizonte de 7 dias da meia-noite local da data inicial confirmada até a meia-noite local após 7 datas, convertidas individualmente para UTC; grade por dia local a partir de 00:00; rejeitar instantes locais ambíguos/inexistentes até confirmação; candidatos não atravessam meia-noite no MVP. Slots de 15 min: arredondar disponibilidade para dentro e bloqueios para fora; duração ocupa `ceil(duration/15)` slots sem reduzir minutos; capacidade diária mede minutos efetivamente reservados (inclusive arredondamento e blocos fixos de estudo), não duração nominal; compromissos pessoais bloqueiam tempo mas não contam como estudo; inviabilidade apresentada como "inviável na grade conservadora de 15 min; viabilidade contínua não determinada". Modelo: `x_b∈{0,1}`; obrigatória `Σ=1`; opcional `≤1`; por slot `Σ x_b≤1`; limites diários confirmados; precedência `end_i≤start_j`; `presence_j≤presence_i` para pré-requisito obrigatório; dependência cíclica é erro explícito. Objetivos lexicográficos: maximizar opcionais classe1, depois 2, depois 3; minimizar alterações de blocos futuros; minimizar deslocamento em slots; preferências (§15.5: overlap em minutos com janelas preferidas; nenhuma=0) como desempate. Tempo: dividir os 10 s totais entre solves com `remaining_seconds/remaining_stages`, incumbent validado salvo após cada etapa, tempo restante reaproveitado; fixar valor anterior só com OPTIMAL; FEASIBLE numa fase interrompe lexicografia e conserva solução válida com vetor de provas por etapa; primeira fase sem solução→UNKNOWN; UNKNOWN posterior→publicar incumbent anterior como FEASIBLE; INFEASIBLE é conflito provado; MODEL_INVALID é defeito; nunca publicar relaxação diagnóstica como aprovado. Verificador **separado** reaplica restrições em minutos/instantes originais (não só a matriz de slots), valida demanda, conflitos, precedência, imutabilidade e snapshot; `ScheduleProposal` com status, blocks, unmet_demands, diff (identidade de ocorrência, §15.5: `activity_occurrence_id` persistido; block_id/UID estáveis; alterações/remoções/adições conforme §15.5), validation, objective/bound e explanation; sem validação não há aprovação.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §9 (planejamento) e §15.5 integrais; §13.7; `ScheduleProposal` (§4).
- Demandas/atividades (011), storage (004), contratos (003).

## Corretude
- [x] C1 — Modelo CP-SAT com todas as restrições do §9; grade/UTC/horizonte conforme §15.5; dependência cíclica → erro explícito (teste).
- [x] C2 — Lexicografia com orçamento de 10 s: testes cobrem OPTIMAL fixado, FEASIBLE interrompendo com provas por etapa, UNKNOWN→incumbent anterior, INFEASIBLE provado; nunca publicar relaxação.
- [x] C3 — Verificador separado valida em minutos/instantes originais e rejeita proposta inválida (teste com violação só visível fora da matriz); preview com diff por identidade de ocorrência.
- [x] C4 — `solver_budget_s=10`, `slot_minutes=15`, `horizon_days=7`, `seed=0`, `num_workers=1` da config; mapa intocado; commits separados.

## Notas

### Execução (registro do executor)

- **Identidade real do modelo**: GLM-5.3-Flash (provider `sd2`, via `~/sd2-llm.sh`) — informada pelo runtime do agente.
- **SHA base**: `a0b29c4` (`a0b29c4415407c52d166de2d865329e6c5590a8e`, revisão da 011 liberando a 012).
- **SHA da entrega**: `34fe505` (`34fe5058d362e1b225a07cb20e7810b839d8d447`) — código em `eduagent/services/scheduling.py` (seção nova do solver/verificador após o `DemandService`) e `tests/test_task012_solver_verifier.py`.
- **Arquivos da entrega**: `eduagent/services/scheduling.py`; `tests/test_task012_solver_verifier.py`. Mapa normativo, `docs/playground-llmagenticsystem` (submódulo) e `config/default.yaml` intocados (`git status` limpo após commits; ortools já pinado em `pyproject.toml`/`uv.lock` da task 001).

#### Evidências por critério

- **C1** — Testes G1–G15: obrigatória `Σ=1`/opcional `≤1` (G1), earliest (G2), deadline datetime (G3) e só de dia valendo até a meia-noite seguinte (G4), precedência `end_i≤start_j` (G5), `presence_j≤presence_i` com pré-requisito obrigatório (G6), ciclo/auto-dependência → `SCHEMA_INVALID` explícito, não INFEASIBLE (G7), exclusividade por slot com INFEASIBLE provado (G8), candidatos não atravessam meia-noite (G9), horizonte de 7 datas com dia 7 fora (G10), capacidade em minutos reservados `ceil(duração/15)*15` (G11), compromisso arredondado para fora sem contar como estudo (G12), bloco fixo de estudo contando na capacidade (G13), instantes locais inexistentes (04/11/2018, America/Sao_Paulo — zona explícita do teste, não default) e ambíguos (16/02/2019) rejeitados com `AMBIGUOUS_INPUT` (G14), settings inválidos tipados (G15).
- **C2** — Testes L1–L8: 6 etapas lexicográficas (`max_class1/2/3`, `min_changes`, `min_displacement_min`, `max_preferences`) todas OPTIMAL com defaults da config (L1), classe1 vence classe2 no mesmo slot (L2), FEASIBLE interrompendo a lexicografia com provas por etapa e solução válida (L3), primeira fase UNKNOWN → UNKNOWN sem publicar nada (L4), UNKNOWN posterior → incumbent anterior publicado como FEASIBLE com provas (L5), INFEASIBLE provado com a mensagem obrigatória "inviável na grade conservadora de 15 min; viabilidade contínua não determinada" (L6, G8), MODEL_INVALID como defeito sem blocos (L7), orçamento dividido por `remaining_seconds/remaining_stages` com tempo não consumido reaproveitado e recortes crescentes dentro do teto (L8). Fixação do valor anterior somente com OPTIMAL implementada em `_LexicographicDriver.run`/`_fix`; incumbent é validado pelo verificador independente após cada etapa e solução que falhar na validação levanta `INTERNAL_FAILURE` (nada é publicado). Testes de protocolo (L3/L4/L5/L7) sobrescrevem apenas o **status** reportado por etapa via monkeypatch de `_LexicographicDriver._solve_stage`, mantendo a seleção real do CP-SAT.
- **C3** — Testes V1–V8: verificador separado (`_verify_placement`/`verify_schedule`) que não consulta a matriz de slots nem o modelo do solver; V2 é a violação **só visível fora da matriz** (duração original de 20 min com instantes cobrindo 15 min — uma checagem que só conta slots livres veria 2 slots disponíveis e aprovaria); V3 conflito, V4 snapshot divergente, V5 obrigatória ausente, V6 diff inconsistente com a identidade, V7 status sem solução publicando blocos; V8 preview com diff por identidade (movida mantém `block_id`/`uid`, adicionada nova ocorrência, déficit 0).
- **C4** — `SolverSettings`/`load_solver_settings` leem `config/default.yaml` (`solver_budget_s=10`, `slot_minutes=15`, `horizon_days=7`, `seed=0`, `num_workers=1`) com fallback tipado para defaults de ensaio espelhando o yaml (K1); `slot_minutes` e `horizon_days` da config governam o solve (K2); `num_workers`/`seed` vão direto aos parâmetros do CP-SAT. Ferramenta `schedule.solve` negada a papéis que não o Planejador (R1). Mapa e submódulo intocados verificados por `git status`/`git diff`.

#### Decisões de codificação registradas

1. **Identidade de diff por `block_id`** (§15.5 usa block_id como identidade de alteração): ocorrência aprovada reagenda com o **mesmo** `block_id`/`uid`; ocorrência nova recebe `occurrence_id`/`block_id`/`uid` determinísticos (uuid5). A persistência definitiva da identidade fica para a confirmação (task 013).
2. **Deadline só de dia** vale até a meia-noite local seguinte (a fronteira do dia é a própria regra; nenhum horário é inventado, §6.3/§15.3).
3. **Sem zona confirmada** (`local_timezone=None`) o dia local é o dia UTC — escolha conservadora já documentada na task 011; UTC não tem transição, então os testes de ambiguidade passam zona IANA explícita (não é default).
4. **Round-trip antes de fold** na resolução de instante local: lacuna → "não existe"; repetição com round-trip ok → "ambíguo" (ambos `AMBIGUOUS_INPUT`, rejeitados até confirmação).
5. **INFEASIBLE em etapa posterior a incumbent válido** é tratado como contradição interna (`INTERNAL_FAILURE`), pois as restrições fixadas por OPTIMAL mantêm o modelo satisfatível — não é conflito novo de dados.
6. **`verify_schedule` público** reusa a grade default para a regra de arredondamento e aceita `settings` explícito; a checagem de capacidade/duração usa a duração original da demanda.
7. **Nenhuma medida de tempo publicada no artefato**: a proposta registra apenas status por etapa e valores de objetivo; os segundos do orçamento são operacionais e não entram em `explanation`.

### Dificuldade esperada
7/10 — CP-SAT + lexicografia com orçamento e verificador independente; muitos casos de status e de grade local.

### Dificuldade sentida
6/10 — A modelagem CP-SAT e o protocolo de status do §15.5 foram diretos após ler §9/§15.5; a dificuldade concentrou-se em (a) acertar a semântica de identidade do diff (block_id vs occurrence_id) sem campo de ocorrência no contrato `PlanBlock`, resolvida com identidade estável derivada de ocorrência; (b) a ordem round-trip×fold na detecção de instante inexistente vs ambíguo (bug encontrado pelo próprio teste G14 e corrigido); e (c) desenhar testes de protocolo determinísticos para FEASIBLE/UNKNOWN/MODEL_INVALID sem depender de timing do CP-SAT (resolvido sobrescrevendo apenas o status reportado por etapa). Dois testes tiveram matemática de janela errada no primeiro corte (G7 sem ciclo real, L10/L11 com empates de solução) — corrigidos antes da entrega.

### Revisão
- Orquestrador: GLM-5.3-Flash (provider `sd2`), master do ciclo opt-in.
- Alvo: base `a0b29c4`; entrega (código) `34fe505`; registro `0df7c37`; árvore limpa; mapa normativo e submodule intocados confirmados por inspeção Git.
- Modo da rodada: **sequencial** — os três revisores reproduzem a suite integral no mesmo `.venv` (recurso compartilhado; mesmo critério da rodada da 011).
- Avaliações:
  - GLM-5.3-Flash — 8/10, aprovada. A1 **médio**: enumerador constrói runs sobre a **união** de janelas adjacentes/sobrepostas (`scheduling.py:1793-1848`) enquanto o verificador exige contenção em **janela única** (`2286-2296`); sonda reproduzida em `/tmp/opencode` mostra `INTERNAL_FAILURE` para entrada confirmada legítima (janelas 8:15–9:15 e 9:15–10:15, demanda obrigatória de 90 min) — fail-safe, mas atingível pela ferramenta pública. A2 baixo: deslocamento em minutos (teto) vs slots de §15.5. A3 informativo: `bound` recebe valor da etapa 1. C1–C4 verificados com evidência de linha; suite 410 passed reproduzida.
  - gpt-6-luna — 8/10 provisória, inconclusiva; achado alto A1 sobre identidade de ocorrências sem evidência de linha. **Esclarecimento solicitado e achado RETIRADO**: reinspeção própria de `_mint_identity` (`1374-1391`) e `_expected_diff` (`2363-2393`) contra §15.5 (linhas 279–281) não encontrou colisão nem perda de identidade; persistência definitiva na confirmação é da task 013.
  - beam-free — 9/10, aprovada; residuais baixos (teto de deslocamento `horizon_days*1440`; `verify_schedule` exige settings coerentes do chamador). C1–C4 verificados; suite 410 passed reproduzida.
- Quórum: três modelos distintos, sem falha de transporte; suite integral 410 passed reproduzida pelos três.
- Nota final: **8/10** — critérios obrigatórios C1–C4 provados com reprodução por três modelos e protocolo lexicográfico fiel ao §15.5; desconto pelo defeito médio A1 (janelas adjacentes/sobrepostas rejeitadas como falha interna) e pela nota provisória/inconclusiva inicial de luna, retirada após esclarecimento.
- Parecer: entrega coesa e provada, mas o A1 do GLM é atingível por entrada confirmada legítima pela ferramenta pública e classifica erro de dados legítimo como defeito interno — não deve ser apenas residual; divergência essencial de luna foi resolvida por esclarecimento (retirada).
- Decisão: **corrigir** — entrega preservada; subtask 012a delimitada ao alinhamento enumerador×verificador da semântica de janelas adjacentes/sobrepostas com teste de regressão (e teste que fixe a identidade do diff, respondendo ao ponto retirado de luna com prova). A2/A3 do GLM e residuais do beam ficam documentados como correção pontual futura, sem reabrir a família.
- Reversão: não se aplica — entrega preservada.
- Próximo passo: subtask `012a-correcao-janelas-adjacentes-e-verificador.md` criada; após seu fechamento, liberar a 013.

<!-- task-cycle: {"decision":"corrigir","next_task":".agents/tasks/04-mapa-completo-do-sistema/012a-correcao-janelas-adjacentes-e-verificador.md","family":".agents/tasks/04-mapa-completo-do-sistema/011-demandas-atividades-e-politica-evidencia.md","plan":".agents/plans/04-mapa-completo-do-sistema/plan.md"} -->

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
