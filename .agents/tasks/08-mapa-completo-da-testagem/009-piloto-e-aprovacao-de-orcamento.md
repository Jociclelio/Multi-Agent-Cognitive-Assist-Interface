# Task 009: Piloto (20 casos, development) e aprovação de orçamento

Estado: pendente
Depende de: 008
Origem: nenhuma

## Prompt
Executar o piloto do mapa §12.1: 20 casos no split `development` com o harness da task 008, medindo wall time, chamadas e minutos de anotação para calcular `horas_exec`/`horas_humanas` do orçamento. Usar o piloto para validar/decidir as questões abertas do plano: (1) congelamento dos orçamentos/limites do mapa §5 (chamadas, tempo de turno, solver — valores são ensaio); (2) margem de não-inferioridade da compactação (.03 proposta) e default de IC (percentil); (3) viabilidade de N (30 trajetórias; clusters independentes) — ampliar antes do congelar ou rotular exploratório. Aprovação de orçamento pelos autores ANTES do `freeze` (custo humano do mapa §12.1: revisão de N ou rotulagem exploratória pelos autores). Registrar todas as medições do piloto como medições de piloto (insumo de planejamento), rotulando-as como tais — não como resultados da campanha.

Restrições: execução restrita ao split `development`; `eduagent/` INTOCADO; modelo Bonsai 2 offline e gate `MODEL_NOT_ADMITTED` vigentes (admitir o modelo do harness conforme procedimento da task 002 do plano 04); nada apresentado como resultado da campanha principal; suíte raiz passando; commits entrega/registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/08_mapa_completo_da_testagem.md` — §12.1 (orçamento, custo humano, metas) e §5 (orçamentos ensaio).
- `eval/cli.py` — comandos `pilot`, `freeze` (task 008).
- `.agents/plans/08-mapa-completo-da-testagem/plan.md` — questões abertas (orçamentos, margem .03, viabilidade de N) que o piloto deve informar.
- `eval/relatorio-testes-mvp.md` — precedentes de ensaio da v0.1 (runtime pinado, Docling em subprocesso spawn).

## Corretude
- [ ] C1 — Piloto executado em 20 casos de `development` com wall time, calls e minutos de anotação medidos e `horas_exec`/`horas_humanas` calculados.
- [ ] C2 — Decisões registradas para orçamentos do §5, margem de compactação, default de IC e viabilidade de N — cada uma com evidência do piloto, marcadas para entrada no `freeze`.
- [ ] C3 — Orçamento aprovado pelos autores antes do `freeze`; medições rotuladas como piloto; suíte raiz passando; sistema intocado.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
7/10 — Primeira execução real do harness completo: bugs de integração são esperados (como no ensaio do plano 04, que revelou quatro); exige paciência para corrigir em `eval/` sem tocar o SUT e disciplina para não rotular medições de piloto como resultados.

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
