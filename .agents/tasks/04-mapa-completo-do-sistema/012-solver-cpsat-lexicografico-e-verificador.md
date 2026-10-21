# Task 012: Solver CP-SAT lexicográfico e verificador independente (mapa §9, §15.5, §13.7 parte 1)

Estado: pendente
Depende de: 011
Origem: nenhuma

## Prompt
Implementar o solver e o verificador (mapa §9 e §15.5) em `eduagent/services/scheduling.py` com a ferramenta `schedule.solve`: horizonte de 7 dias da meia-noite local da data inicial confirmada até a meia-noite local após 7 datas, convertidas individualmente para UTC; grade por dia local a partir de 00:00; rejeitar instantes locais ambíguos/inexistentes até confirmação; candidatos não atravessam meia-noite no MVP. Slots de 15 min: arredondar disponibilidade para dentro e bloqueios para fora; duração ocupa `ceil(duration/15)` slots sem reduzir minutos; capacidade diária mede minutos efetivamente reservados (inclusive arredondamento e blocos fixos de estudo), não duração nominal; compromissos pessoais bloqueiam tempo mas não contam como estudo; inviabilidade apresentada como "inviável na grade conservadora de 15 min; viabilidade contínua não determinada". Modelo: `x_b∈{0,1}`; obrigatória `Σ=1`; opcional `≤1`; por slot `Σ x_b≤1`; limites diários confirmados; precedência `end_i≤start_j`; `presence_j≤presence_i` para pré-requisito obrigatório; dependência cíclica é erro explícito. Objetivos lexicográficos: maximizar opcionais classe1, depois 2, depois 3; minimizar alterações de blocos futuros; minimizar deslocamento em slots; preferências (§15.5: overlap em minutos com janelas preferidas; nenhuma=0) como desempate. Tempo: dividir os 10 s totais entre solves com `remaining_seconds/remaining_stages`, incumbent validado salvo após cada etapa, tempo restante reaproveitado; fixar valor anterior só com OPTIMAL; FEASIBLE numa fase interrompe lexicografia e conserva solução válida com vetor de provas por etapa; primeira fase sem solução→UNKNOWN; UNKNOWN posterior→publicar incumbent anterior como FEASIBLE; INFEASIBLE é conflito provado; MODEL_INVALID é defeito; nunca publicar relaxação diagnóstica como aprovado. Verificador **separado** reaplica restrições em minutos/instantes originais (não só a matriz de slots), valida demanda, conflitos, precedência, imutabilidade e snapshot; `ScheduleProposal` com status, blocks, unmet_demands, diff (identidade de ocorrência, §15.5: `activity_occurrence_id` persistido; block_id/UID estáveis; alterações/remoções/adições conforme §15.5), validation, objective/bound e explanation; sem validação não há aprovação.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §9 (planejamento) e §15.5 integrais; §13.7; `ScheduleProposal` (§4).
- Demandas/atividades (011), storage (004), contratos (003).

## Corretude
- [ ] C1 — Modelo CP-SAT com todas as restrições do §9; grade/UTC/horizonte conforme §15.5; dependência cíclica → erro explícito (teste).
- [ ] C2 — Lexicografia com orçamento de 10 s: testes cobrem OPTIMAL fixado, FEASIBLE interrompendo com provas por etapa, UNKNOWN→incumbent anterior, INFEASIBLE provado; nunca publicar relaxação.
- [ ] C3 — Verificador separado valida em minutos/instantes originais e rejeita proposta inválida (teste com violação só visível fora da matriz); preview com diff por identidade de ocorrência.
- [ ] C4 — `solver_budget_s=10`, `slot_minutes=15`, `horizon_days=7`, `seed=0`, `num_workers=1` da config; mapa intocado; commits separados.

## Notas

### Dificuldade esperada
7/10 — CP-SAT + lexicografia com orçamento e verificador independente; muitos casos de status e de grade local.

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
