# Task 004: Oráculos independentes O01–O18

Estado: pendente
Depende de: 003
Origem: nenhuma

## Prompt
Implementar cada oráculo de saída O01–O18 de forma INDEPENDENTE do SUT (implementação própria no harness, sem importar a lógica avaliada do `eduagent/`), com checks/gates conforme a tabela do mapa §6 — valores do mapa são thresholds propostos, não resultados. Incluir: CP/CR de claims (cobertura e precisão contra IDs de fonte/claim do ouro); abstinência versus recall (abstinência correta não pune recall indevidamente); regra `value=null` com razão registrada quando o denominador é zero; métricas com unidades e domínios preservados (taxas em [0,1]; CER/WER podem exceder 1; kappa em [-1,1]; log loss sem teto); `N/A` somente com motivo. Medição de artefatos ANTES de qualquer sucesso agregado. Cada oráculo com teste unitário próprio e controles positivos/negativos mínimos (a meta-avaliação completa é da task 006).

Restrições: oráculos independentes (reimplementação a partir da especificação do mapa/etapa 7, não chamada de código do SUT); `eduagent/` INTOCADO; nada apresentado como resultado medido (gates são propostas); IDs O01–O18 permanentes; suíte raiz passando; commits entrega/registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/08_mapa_completo_da_testagem.md` — §6 (tabela de oráculos, checks/gates por saída) e §12 (regras de snapshot/demanda/grade/approval para implementação sem depender de outro arquivo).
- `fase2/pesquisa/07a_metodos_qualidade.md` — fórmulas/denominadores e oráculos por saída.
- `eval/oracles/` — diretório criado na task 001.
- `eduagent/` — especificação do comportamento a partir da qual os oráculos são reescritos (leitura apenas).

## Corretude
- [ ] C1 — Dezoito oráculos implementados de forma independente, cobrindo a tabela do mapa §6, com domínios/unidades corretos e `N/A` condicionado a motivo.
- [ ] C2 — CP/CR de claims contra IDs de fonte/claim, abstinência vs. recall e `value=null` com razão em denominador zero implementados conforme mapa.
- [ ] C3 — Cada oráculo com teste unitário e controles mínimos; nenhuma dependência de código interno do SUT na lógica de julgamento; suíte raiz passando.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
7/10 — Volume alto (18 oráculos) com exigência de independência real da implementação avaliada; o risco é reimplementar por delegação ao código do SUT, invalidando o oráculo.

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
