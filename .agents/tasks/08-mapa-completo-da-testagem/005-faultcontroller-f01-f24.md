# Task 005: FaultController F01–F24

Estado: pendente
Depende de: 004
Origem: nenhuma

## Prompt
Implementar o FaultController do mapa §7: contrato `FaultPlan` (injeção declarativa por caso/seed), cobertura completa F01–F24, e coleta dos efeitos a medir por par limpo/perturbado (Δqualidade, Δsucesso, Δlatência, Δtokens, efeitos indevidos, tempo até detectar/recuperar). Incluir: crashpoints CP0–CP6 com `SIGKILL` real; `UNKNOWN_EFFECT` sem destino consultável (sem retry cego); testes de concorrência/linearizabilidade local; falhas compostas com design clean/A/B/A+B (as seis compostas prioritárias da etapa 5); priorização por severidade (S2–S4 primeiro). Falha de harness ≠ falha de SUT: distinguir e registrar; sem substituição silenciosa de execução falha.

Restrições: `eduagent/` INTOCADO (injeção via adapter/ambiente controlado); mapa §7 como fonte; `SIGKILL` real nos crashpoints (não simulado por exceção); nada apresentado como resultado medido (execução de campanha é task posterior); IDs F01–F24 permanentes; suíte raiz passando; commits entrega/registro separados; submódulo não tocado; temporários em `/tmp/opencode` (execuções de teste de falha isoladas do domínio raiz).

## Contexto
- `fase2/documentos/08_mapa_completo_da_testagem.md` — §7 (contrato FaultPlan, cobertura F01–F24, efeitos a medir, crashpoints).
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — catálogo F01–F24, severidades e as seis falhas compostas prioritárias.
- `fase2/pesquisa/07b_metodos_robustez_experimentos.md` — métodos de injeção e propriedade/estado.
- `eval/faults/` — diretório criado na task 001.

## Corretude
- [ ] C1 — `FaultPlan` implementado com injeção declarativa e cobertura das 24 famílias F01–F24, com priorização por severidade.
- [ ] C2 — Crashpoints CP0–CP6 com `SIGKILL` real, `UNKNOWN_EFFECT` sem retry cego, concorrência/linearizabilidade local e compostas clean/A/B/A+B implementados.
- [ ] C3 — Efeitos a medir coletados por par limpo/perturbado com mesmo caso/seed; falha de harness distinguida de falha de SUT e registrada; suíte raiz passando.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
7/10 — Injeção real de falhas (SIGKILL, UNKNOWN_EFFECT, concorrência) sem corromper o domínio do SUT nem o repositório; o risco é injetar de dentro do SUT (contamina a independência).

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
