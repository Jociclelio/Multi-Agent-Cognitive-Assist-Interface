# Task 003: Runner, condições e recursos compartilhados

Estado: pendente
Depende de: 002
Origem: nenhuma

## Prompt
Implementar o runner e as condições do mapa §5: condições `MA_FULL`, `SA_EQUIVALENT` (SA único com mesmo modelo/corpus/memória/tools/envelope), ablações (sem memória longitudinal, sem compactação, todas as skills carregadas) e `MA_REDUCED_SKILL`, com recursos compartilhados definidos no mapa; orçamentos de chamadas/turno/solver implementados como ENSAIO, marcados para congelamento após piloto (não são limites finais). Algoritmo counterbalanced por bloco; seeds principais 0–4 (uma execução por condição/seed); seeds de falha 0–2; RNGs separados por propósito; relógio virtual para tempos do SUT + watchdog externo (overshoot após 120 s é overshoot, não tempo do SUT). State reset e cache policy registrados por execução; offline como condição separada; conectado com mocks/snapshots (smoke real de conector é fase posterior). Comparação principal sob teto comum de chamadas/tokens/tempo; análise adicional iguala orçamento real consumido.

Restrições: `eduagent/` INTOCADO (condições via adapter da task 001); mapa §5 como fonte; orçamentos rotulados como ensaio a congelar; nada apresentado como resultado medido; suíte raiz passando; commits entrega/registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/08_mapa_completo_da_testagem.md` — §5 (condições, recursos, seeds, relógio virtual/watchdog).
- `eval/runner.py`, `eval/adapters.py` — infraestrutura das tasks 001–002.
- `fase2/documentos/06_protocolo_de_avaliacao.md` — seção 3 (condições e teto comum), para coerência.

## Corretude
- [ ] C1 — Cinco condições implementadas com recursos compartilhados do mapa; SA_EQUIVALENT de fato equivalente em modelo/corpus/memória/tools/envelope.
- [ ] C2 — Counterbalancing por bloco, seeds principais 0–4 e de falha 0–2, RNGs separados, state reset e cache policy registrados por execução.
- [ ] C3 — Relógio virtual + watchdog externo com semântica de overshoot correta; orçamentos marcados como ensaio a congelar; suíte raiz passando.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
6/10 — Orquestração de condições com equivalência real entre MA e SA e separação correta de relógios; o risco é vazamento de estado entre condições (state reset incompleto).

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
