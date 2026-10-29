# Task 007: Anotação cega e estatística por cluster

Estado: pendente
Depende de: 003, 006
Origem: nenhuma

## Prompt
Implementar anotação e estatística do mapa §9: (1) export cego para anotadores (sem condição/arquitetura visível) e import de anotações com adjudicação; juiz LLM apenas como secundário/triagem, com calibração contra humanos registrada antes do uso. (2) Métricas agregadas: TSR de rota e TSR longitudinal (por W, macro e micro); bootstrap pareado por cluster (B=10.000, seed 2026, IC95% percentil — default a validar em piloto); regra conjunta da primária (TSR longitudinal e taxa de violação crítica publicada); margem de não-inferioridade da compactação proposta (.03) marcada como a confirmar antes do congelamento; bound com zero eventos `1−.05^(1/G)`; tool-use correctness em quatro níveis separados; p50/p95 com denominador completo (falhas no denominador, censura indicada). (3) Regra: se a amostra não sustentar estimativa, reportar IC e resultado inconclusivo; turnos de uma mesma trajetória nunca são amostras independentes (cluster é a unidade de reamostragem).

Restrições: `eduagent/` INTOCADO; mapa §9 como fonte (valores B/seed/margem são propostas a confirmar em piloto, não constantes sagradas nem resultados); nada apresentado como resultado medido nesta task (implementação do cálculo, sem execução da campanha); suíte raiz passando; commits entrega/registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/08_mapa_completo_da_testagem.md` — §9 (estatística, bootstrap, regra conjunta, margem, bound) e §3 (`AnnotationRecord`).
- `eval/statistics/`, `eval/metrics/` — diretórios da task 001.
- `fase2/documentos/06_protocolo_de_avaliacao.md` — seções 5–6 (sucesso/eficiência e validade), para coerência das definições.
- `fase2/pesquisa/07b_metodos_robustez_experimentos.md` — inferência estatística (bootstrap pareado, IC, não-inferioridade).

## Corretude
- [ ] C1 — Export/import cego com adjudicação implementados; juiz LLM restrito a secundário com calibração contra humanos exigida antes do uso.
- [ ] C2 — TSR por rota/longitudinal (W, macro, micro), bootstrap pareado por cluster (unidade = trajetória/família), regra conjunta, bound com zero eventos e p50/p95 com denominador completo implementados conforme mapa §9.
- [ ] C3 — Margem e IC default marcados como a confirmar em piloto; regra de IC/inconclusivo implementada; suíte raiz passando.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
6/10 — Estatística pareada por cluster com regras de denominador e censura corretas; o risco é bootstrap por caso em vez de por cluster (violando a não-independência) ou p95 só de sucessos.

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
