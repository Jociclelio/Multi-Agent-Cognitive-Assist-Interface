# Task 011: Relatório final da campanha e consolidação do plano

Estado: pendente
Depende de: 010
Origem: nenhuma

## Prompt
Fechar a etapa 8: (1) `report` emitindo o relatório final da campanha conforme mapa §10 — SOMENTE com valores medidos na execução: inventário e cobertura W/O/F; N planejado/executado/elegível/exposto; ICs por cluster; violações críticas; task_completion vs. safe_terminal na fault-injection; eficiência (p50/p95 com censura, timeouts, custo); limitações declaradas (aluno simulado, duas disciplinas, hardware único; qualidade operacional não comprova ganho de aprendizagem). Nenhum resultado inventado, extrapolado ou preenchido: se uma célula não tem dados suficientes, IC e inconclusivo. (2) Consolidar o estado do plano: critérios de conclusão do `plan.md` verificados um a um com evidência; questões abertas resolvidas ou explicitamente pendentes. (3) Conferir registro dos artefatos da campanha no índice da entrega quando pertinente e rodar `python3 fase2/scripts/verificar_documentos.py` (mapa 08 INTOCADO; se o relatório final for integrado à entrega LaTeX, seguir o plano 09).

Restrições: `eduagent/` e `fase2/documentos/08_mapa_completo_da_testagem.md` INTOCADOS; relatório só com valores medidos; runs preservadas como fonte de verdade (todo número do relatório rastreável a run IDs); prosa em português; commits entrega/registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/08_mapa_completo_da_testagem.md` — §10 (formato do relatório e gates) e §12.2 (matriz requisito→predicado, métrica de delegação `valid_consumed_artifacts/eligible_handoffs_attempted`).
- `eval/` — runs, métricas e artefatos da task 010 (fonte única de números).
- `.agents/plans/08-mapa-completo-da-testagem/plan.md` — critérios de conclusão e questões abertas a consolidar.
- `eval/relatorio-testes-mvp.md` — formato de relatório com ausências declaradas usado no plano 04 (referência de honestidade, não de conteúdo).

## Corretude
- [ ] C1 — Relatório final emitido apenas com valores medidos, com inventário/cobertura W/O/F, N planejado/executado/elegível/exposto, ICs por cluster e violações críticas; todo número rastreável a runs; inconclusivos declarados como tais.
- [ ] C2 — Limitações declaradas (aluno simulado, duas disciplinas, hardware único, operacional ≠ aprendizagem); nenhuma métrica inventada ou extrapolada.
- [ ] C3 — Critérios de conclusão do plano verificados com evidência e questões abertas consolidadas na task; verificador documental passa; mapa 08 e `eduagent/` intocados.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
5/10 — Consolidação de números já produzidos; o risco é pressão por "completar" células sem dados — o critério é declarar inconclusivo, nunca estimar.

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

### Revisão
- Orquestrador: —
- Alvo: —
- Avaliações: <modelo A: _/10; modelo B: _/10; modelo C: _/10>
- Nota final: _/10
- Parecer: —
- Decisão: —
- Reversão: —
- Próximo passo: —

Plano: [plan.md](../../plans/08-mapa-completo-da-testagem/plan.md)
