# Plano: Execução do sistema de testagem do EduAgent-OS v0.1 (mapa etapa 8)

Estado: tasks criadas (001–011) — execução pendente de início do ciclo; sequência implementação (001–008) → piloto/orçamento (009) → freeze/campanha (010) → relatório (011)

## Objetivo

Implementar o testbed local especificado em `fase2/documentos/08_mapa_completo_da_testagem.md`
(abaixo, "mapa §N"): harness completo com registro de casos, runner pareado, oráculos
determinísticos independentes para O01–O18, FaultController cobrindo F01–F24, anotação
cega, métricas, estatística por cluster e relatório com gates — para então executar a
campanha de testes do EduAgent-OS (especificação futura; o mapa não registra resultados
medidos e este plano não os apresenta).

## Abordagem

Sequência de alto nível, ancorada nas seções do mapa (execução futura deve ler o mapa
integralmente; o plano não o reproduz):

1. **Estrutura e interface do SUT** — criar o pacote `eval/` conforme mapa §2
   (`cli.py`, `runner.py`, `adapters.py`, `oracles/`, `faults/`, `metrics/`,
   `statistics/`, etc.), implementando o `SUTAdapter` obrigatório (mapa §1) para MA,
   SA e ablações, com `TurnResult`, inspeção autoritativa restrita ao harness e
   `MockLLM` apenas para lógica determinística. Stack: Python 3.11+, pytest,
   Hypothesis, JiWER, pytrec_eval, scikit-learn/SciPy, parser ICS independente
   candidato `ics.py` (pinado após smoke de conformidade, mapa §2).
2. **Registro e dataset** — schemas JSON estritos `CaseRecord`/`GoldRecord`/
   `RunRecord`/`MetricRecord`/`AnnotationRecord` (mapa §3); captura do dataset com
   metas e targets do mapa §4 e §12.1 (famílias documentais, queries, trajetórias,
   agendas), auditor de parentesco/duplicatas, splits sem repartir parentes, clusters
   = componentes de parentesco, anotação com dois especialistas + adjudicação.
3. **Runner e condições** — condições `MA_FULL`, `SA_EQUIVALENT`, ablações e
   `MA_REDUCED_SKILL` com recursos compartilhados do mapa §5 (orçamentos de
   chamadas/turno/solver marcados como ensaio a congelar após piloto); algoritmo
   counterbalanced por bloco, seeds principais 0–4, seeds de falha 0–2, RNGs
   separados, relógio virtual + watchdog externo (overshoot após 120 s é overshoot).
4. **Oráculos O01–O18** — implementação independente de cada oráculo com checks/gates
   conforme tabela do mapa §6 (valores ali são thresholds propostos, não resultados);
   CP/CR de claims, abstinência vs. recall, `value=null` com razão em denominador zero.
5. **FaultController** — contrato `FaultPlan`, cobertura F01–F24 e efeitos a medir
   (mapa §7), crashpoints CP0–CP6 com `SIGKILL`, `UNKNOWN_EFFECT` sem destino
   consultável, concorrência/linearizabilidade local, falhas compostas com design
   clean/A/B/A+B, priorização por severidade.
6. **Meta-avaliação dos oráculos** — máquina de estados Hypothesis independente,
   metamorfismos e controles positivos/negativos do avaliador (mapa §8); oráculo que
   falha é corrigido em `development` antes de avaliar o teste.
7. **Anotação e estatística** — export cego, juiz LLM secundário calibrado, TSR de rota
   e longitudinal, bootstrap pareado por cluster (B=10.000, seed 2026, IC95% percentil
   a validar em piloto), regra conjunta primária, margem de compactação proposta .03 a
   confirmar antes do congelamento, bound com zero eventos `1−.05^(1/G)` (mapa §9).
8. **CLI, freeze, gates e relatório** — comandos do mapa §10 (`validate`,
   `oracle-controls`, `pilot`, `freeze`, `run`, `faults`, `annotate-export/import`,
   `analyze`, `report`); manifesto imutável no `freeze` (sem flag de retuning); gates
   de release conforme mapa §10; relatório final só com resultados da execução real.
9. **Detalhes complementares** — regras de snapshot/demanda v1/atividade/grade/
   approval reproduzidas no mapa §12 para implementação dos oráculos sem depender de
   outro arquivo; matriz requisito→predicado C01–C20 (mapa §12.2) com case_ids
   concretos gerados após a captura; métrica de delegação
   `valid_consumed_artifacts/eligible_handoffs_attempted`.

## Escopo

- Entrega: pacote `eval/` + fixtures/manifests/runs conforme layout do mapa §2,
  execução do piloto (20 casos, dev) e do teste principal conforme orçamento do mapa
  §12.1 (ex.: 6000 runs principais; 6000 sessões; reduced 600 runs; falhas ≤2880
  runs — números de planejamento, não contagens executadas).
- Fora do escopo: simulador LLM de estudante (estudo separado, mapa §3.1); export
  Porcupine (extensão opcional); exigir Go; energia sem medidor (N/A, mapa §9);
  apagamento físico de dados (testes verificam status lógico, mapa §12).
- Custo humano: aprovação de orçamento e revisão de N ou rotulagem exploratória pelos
  autores **antes** do teste (mapa §12.1); anotação por dois especialistas + juiz.
- O PDF/LaTeX experimental não preenche resultados antes da execução (mapa §10).

## Contexto

- `fase2/documentos/08_mapa_completo_da_testagem.md` — fonte normativa autocontida
  deste plano; toda execução deve se apoiar nele seção a seção.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — define o SUT (regras de snapshot,
  rubrica, demanda, grade etc., referenciadas no mapa §12).
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — origem dos IDs W/O/F usados nas
  matrizes do mapa (§12.2) e no relatório de cobertura.
- `fase2/pesquisa/` (pesquisas 7a/7b) — referências verificadas e limitações de acesso
  citadas no mapa §11; escolhas locais não são resultados publicados dessas fontes.
- Nota do repositório: EduAgent-OS é especificação futura, não aplicação executável;
  checagens de documento não estabelecem resultados experimentais.

## Critérios de conclusão

- Todos os comandos do mapa §10 implementados e passando em `--split development`.
- Oráculos O01–O18 e FaultController F01–F24 implementados; controles positivos/negativos
  do mapa §8 passam (mutantes conhecidos detectados, controles válidos aprovados).
- Piloto executado (20 casos, dev) com wall time, calls e minutos de anotação medidos
  para o cálculo de `horas_exec`/`horas_humanas` (mapa §12.1); orçamento aprovado
  antes do `freeze`.
- `freeze` gera manifesto imutável (datasets, configs, margins, budgets, seeds,
  versões de oráculo/parser, hashes); teste principal executado com runs completas
  preservadas (falha de harness ≠ falha SUT, sem substituição silenciosa, mapa §3.3).
- Relatório final com inventário/cobertura W/O/F, N planejado/executado/elegível/
  exposto, ICs por cluster, violações críticas, limitações — contendo apenas valores
  medidos na execução.

## Questões abertas

- Congelamento dos orçamentos/limites do mapa §5 (chamadas, tempo de turno, solver):
  valores são ensaio e dependem do piloto; decisão dos autores pendente.
- Margem de não inferioridade para compactação (.03) e default de IC (percentil):
  propostos no mapa §9, exigem confirmação (especialistas / simulação de piloto).
- Viabilidade de N (30 trajetórias; clusters independentes): a definir no piloto —
  ampliar antes do congelar ou rotular exploratório (mapa §9, §12.1).
- Interoperabilidade do parser ICS candidato (`ics.py`): se fixture RFC falhar,
  resultado é interoperabilidade inconclusiva, não falha automática (mapa §2).

## Tasks

| Ordem | Task | Cobertura (plano) | Depende de | Estado |
|---|---|---|---|---|
| 1 | [001-estrutura-do-pacote-eval-e-sutadapter.md](../../tasks/08-mapa-completo-da-testagem/001-estrutura-do-pacote-eval-e-sutadapter.md) | Abordagem 1 (estrutura §2, SUTAdapter §1, stack, parser ICS) | nenhuma | pendente |
| 2 | [002-schemas-de-registro-e-captura-de-dataset.md](../../tasks/08-mapa-completo-da-testagem/002-schemas-de-registro-e-captura-de-dataset.md) | Abordagem 2 (schemas §3, dataset §4/§12.1) | 001 | pendente |
| 3 | [003-runner-condicoes-e-recursos-compartilhados.md](../../tasks/08-mapa-completo-da-testagem/003-runner-condicoes-e-recursos-compartilhados.md) | Abordagem 3 (condições §5, seeds, relógio virtual) | 002 | pendente |
| 4 | [004-oraculos-independentes-o01-o18.md](../../tasks/08-mapa-completo-da-testagem/004-oraculos-independentes-o01-o18.md) | Abordagem 4 (oráculos §6) | 003 | pendente |
| 5 | [005-faultcontroller-f01-f24.md](../../tasks/08-mapa-completo-da-testagem/005-faultcontroller-f01-f24.md) | Abordagem 5 (FaultController §7, CP0–CP6) | 004 | pendente |
| 6 | [006-meta-avaliacao-dos-oraculos.md](../../tasks/08-mapa-completo-da-testagem/006-meta-avaliacao-dos-oraculos.md) | Abordagem 6 (meta-avaliação §8) | 004 | pendente |
| 7 | [007-anotacao-cega-e-estatistica-por-cluster.md](../../tasks/08-mapa-completo-da-testagem/007-anotacao-cega-e-estatistica-por-cluster.md) | Abordagem 7 (anotação e estatística §9) | 003, 006 | pendente |
| 8 | [008-cli-do-harness-freeze-e-gates.md](../../tasks/08-mapa-completo-da-testagem/008-cli-do-harness-freeze-e-gates.md) | Abordagem 8 (CLI, freeze e gates §10) | 004, 005, 007 | pendente |
| 9 | [009-piloto-e-aprovacao-de-orcamento.md](../../tasks/08-mapa-completo-da-testagem/009-piloto-e-aprovacao-de-orcamento.md) | Escopo (piloto 20 casos) + questões abertas (§12.1) | 008 | pendente |
| 10 | [010-freeze-e-campanha-principal.md](../../tasks/08-mapa-completo-da-testagem/010-freeze-e-campanha-principal.md) | Escopo (execução da campanha, §12.1) | 009 | pendente |
| 11 | [011-relatorio-final-e-consolidacao.md](../../tasks/08-mapa-completo-da-testagem/011-relatorio-final-e-consolidacao.md) | Abordagem 9 (detalhes §12) + critérios de conclusão | 010 | pendente |

Notas: implementação do harness em `eval/` com o EduAgent-OS real (`eduagent/`, `uv run`) como SUT — `eduagent/` e `manifest.json` intocados em todas as tasks; bug de SUT descoberto na campanha é achado para decisão do master, nunca correção silenciosa. Orçamentos/margens/N são ensaios até o piloto (009) e imutáveis após o `freeze` (010). Valores do mapa são propostos, não resultados; o relatório (011) só contém valores medidos na execução. `eval/ensaio_longitudinal.py` e `eval/relatorio-testes-mvp.md` do plano 04 preservados.
