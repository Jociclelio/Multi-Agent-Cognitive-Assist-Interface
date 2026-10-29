# Task 006: Meta-avaliação dos oráculos (controles e Hypothesis)

Estado: pendente
Depende de: 004
Origem: nenhuma

## Prompt
Implementar a meta-avaliação dos oráculos do mapa §8: máquina de estados Hypothesis independente exercitando os oráculos; metamorfismos (transformações que NÃO devem mudar o veredito — ex.: reformatação preservando semântica — e transformações que DEVEM mudar); controles positivos e negativos do avaliador (casos que o oráculo deve aprovar e casos que deve rejeitar, incluindo mutantes conhecidos). Regra do mapa: oráculo que falha no controle é corrigido antes de avaliar o split de teste (ciclo restrito ao split `development`). Cobertura: todos os oráculos O01–O18 com controles próprios; registrar por oráculo os mutantes detectados e os não detectados com justificativa.

Restrições: `eduagent/` INTOCADO; mapa §8 como fonte; correção de oráculo restrita a `eval/oracles/`; nada apresentado como resultado medido (meta-avaliação é validação do instrumento, não avaliação do SUT); suíte raiz passando; commits entrega/registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/08_mapa_completo_da_testagem.md` — §8 (máquina de estados, metamorfismos, controles, regra de correção em development).
- `eval/oracles/` — oráculos da task 004 (objeto da meta-avaliação).
- `fase2/pesquisa/07b_metodos_robustez_experimentos.md` — fundamentos de testes de propriedade e mutação.

## Corretude
- [ ] C1 — Máquina de estados Hypothesis independente exercitando os oráculos; metamorfismos definidos com direção explícita (deve manter / deve mudar veredito).
- [ ] C2 — Controles positivos e negativos por oráculo O01–O18 passando; mutantes conhecidos detectados; oráculos com falha de controle corrigidos em `eval/oracles/` antes de qualquer uso no teste.
- [ ] C3 — Registro por oráculo (mutantes detectados/não detectados com justificativa); suíte raiz passando; `eduagent/` intocado.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
7/10 — Desenhar metamorfismos e mutantes que realmente discriminem oráculos fracos exige entender cada métrica a fundo; Hypothesis stateful tem armadilhas de redução/flakiness.

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
