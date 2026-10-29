# Task 010: Freeze e execução da campanha principal

Estado: pendente
Depende de: 009
Origem: nenhuma

## Prompt
Executar o congelamento e a campanha principal: (1) `freeze` com os parâmetros decididos na task 009 (orçamentos, margem, IC default, N, seeds, versões de oráculo/parser, hashes de datasets) — manifesto imutável, sem retuning; após o freeze, NENHUM parâmetro muda. (2) Executar `run` para a campanha principal (números de planejamento do mapa §12.1: ~6000 runs principais, ~6000 sessões; reduced ~600; falhas ≤2880 — contagens reais são as executadas, registradas como tais) com runs completas preservadas. (3) Executar `faults` para os pares limpo/perturbado F01–F24 priorizados por severidade. (4) Smoke real de conector quando aplicável (condição connected separada, após mocks/snapshots). (5) `annotate-export`/`annotate-import` com adjudicação; (6) `analyze` produzindo métricas com denominadores, ICs por cluster, violações críticas. Monitorar armadilhas conhecidas da v0.1: limite de subprocesso do Docling (spawn, RLIMIT_AS), memória do embedder, operação em `/tmp/opencode` para artefatos voláteis.

Restrições: nenhum parâmetro alterado após o freeze (qualquer necessidade = parar, registrar e decidir reinício/repartição com o master); `eduagent/` INTOCADO — bug de SUT descoberto na campanha é registrado como achado para decisão, não corrigido em silíncio; nada apresentado como resultado antes do relatório da task 011; suíte raiz passando; commits entrega/registro separados; submódulo não tocado.

## Contexto
- `fase2/documentos/08_mapa_completo_da_testagem.md` — §12.1 (orçamento da campanha), §10 (freeze/run/faults), §3.3 (runs preservadas).
- `eval/cli.py` — comandos implementados (task 008).
- `.agents/tasks/08-mapa-completo-da-testagem/009-piloto-e-aprovacao-de-orcamento.md` — parâmetros aprovados para o freeze.
- `eval/ensaio_longitudinal.py` — precedentes operacionais (spawn, limites de memória) do plano 04.

## Corretude
- [ ] C1 — Manifesto de freeze gerado e imutável, contendo datasets, configs, margins, budgets, seeds e hashes; nenhum parâmetro alterado depois.
- [ ] C2 — Campanha principal e fault-injection executadas com runs completas preservadas (falha de harness ≠ falha SUT, sem substituição silenciosa); contagens reais registradas versus números de planejamento.
- [ ] C3 — `analyze` concluído com métricas com denominadores, ICs por cluster e violações críticas calculadas a partir das runs reais; achados de SUT registrados como achados, sem correção silenciosa.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
8/10 — Campanha longa e cara (milhares de runs) com disciplina de imutabilidade pós-freeze; qualquer bug de SUT cria a tentação proibida de corrigir e reexecutar silenciosamente.

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
