# Task 008: CLI do harness, freeze e gates de release

Estado: pendente
Depende de: 004, 005, 007
Origem: nenhuma

## Prompt
Implementar os comandos do `eval/cli.py` conforme mapa §10: `validate`, `oracle-controls`, `pilot`, `freeze`, `run`, `faults`, `annotate-export`, `annotate-import`, `analyze`, `report`. O `freeze` gera manifesto IMUTÁVEL (datasets, configs, margins, budgets, seeds, versões de oráculo/parser, hashes) sem flag de retuning — alterar parâmetros exige novo freeze explícito com registro. Gates de release conforme mapa §10 (release bloqueada quando gate falha, sem flag de contorno). `run`/`faults` preservam runs completas (falha de harness ≠ falha SUT; sem substituição silenciosa). `report` só emite relatório a partir de runs existentes — nunca preenche resultados antes da execução. Mensagens de erro fail-closed quando pré-condição faltar (ex.: `analyze` sem runs, `report` sem `analyze`).

Restrições: `eduagent/` e `manifest.json` do sistema INTOCADOS (o freeze do harness é artefato próprio em `eval/`); mapa §10 como fonte; nada apresentado como resultado medido; suíte raiz passando; commits entrega/registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/08_mapa_completo_da_testagem.md` — §10 (comandos, freeze imutável, gates de release) e §3.3 (runs preservadas).
- `eval/cli.py` e módulos das tasks 001–007 — superfície a expor.
- `eduagent/cli.py` — referência de estilo de CLI do projeto (leitura apenas).

## Corretude
- [ ] C1 — Dez comandos implementados com comportamento do mapa §10 e encadeamento de pré-condições fail-closed (validate → oracle-controls → pilot → freeze → run/faults → annotate → analyze → report).
- [ ] C2 — `freeze` gera manifesto imutável com todos os campos do mapa e sem flag de retuning; gates de release bloqueiam sem contorno.
- [ ] C3 — Runs completas preservadas com distinção harness/SUT; `report` recusa-se a emitir sem runs reais; suíte raiz passando.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
5/10 — Integração dos módulos anteriores numa CLI coesa; o risco é gate frouxo (flag de contorno) que compromete o congelamento.

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
