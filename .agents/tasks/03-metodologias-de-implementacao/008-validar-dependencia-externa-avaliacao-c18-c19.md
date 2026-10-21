# Task 008: Validar dependência externa — avaliação experimental (C18/C19)

Estado: pendente
Depende de: 007
Origem: nenhuma

## Prompt
Conferir que a decisão abaixo reproduz **fielmente** a linha C18/C19 da tabela "Decisões reconciliadas" de `fase2/documentos/03_metodologias_de_implementacao.md` (documento-fonte normativo, que permanece intocado; linha 28). Registrar em Evidências a conferência item a item (método selecionado, referências/chaves, por quê e limite). Se encontrar desvio de fidelidade, corrija **apenas o texto desta task** em dif mínimo, preservando o sentido do fonte, e registre a correção em Evidências.

Decisão a validar (extraída da tabela do documento-fonte):
- **C18/C19 — Dados e avaliação experimental:** ouro independente, splits por família, avaliação pareada, ablações e falhas injetadas *(referências/chaves: pesquisa específica na etapa 7)* *(por quê e limite: seleção de parâmetros em validação, nunca no teste final)*

Além da fidelidade, conferir que: os IDs C18 e C19 são tratados como permanentes; nada acrescenta requisito, número, métrica ou design de experimento não presente no fonte; a dependência externa permanece registrada como pendência — a pesquisa específica das etapas 6–7 completa C18–C19 e não faz parte desta etapa (questão aberta do plano), sem antecipar decisões dos mapas normativos (`04_mapa_completo_do_sistema.md` e `08_mapa_completo_da_testagem.md`); a regra "seleção de parâmetros em validação, nunca no teste final" permanece como limite, sem valores definidos.

Restrições: não alterar o documento-fonte nem criar documento novo; não antecipar a pesquisa das etapas 6–7 nem desenhar experimentos, splits ou métricas; nada apresentado como resultado medido; IDs C01–C20 permanentes; prosa em português; commit de entrega (correção de fidelidade, se houver) e commit de registro separados, sem amend/force-push/commits vazios; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/03_metodologias_de_implementacao.md` — documento-fonte: tabela "Decisões reconciliadas", linha C18/C19 (linha 28); abertura (linhas 5–10) declara C18–C19 completados pelas etapas 6–7.
- `.agents/tasks/02-componentes-e-requisitos/007-validar-dados-e-avaliacao-experimental.md` — etapa 2: características exigidas de C18/C19 registradas na etapa anterior.
- `fase2/documentos/08_mapa_completo_da_testagem.md` — mapa normativo de avaliação; prevalece para critérios de teste; referência apenas, sem antecipar decisões.
- `.agents/plans/03-metodologias-de-implementacao/plan.md` — plano aprovado; "Questões abertas" registra a dependência das etapas 6–7.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [ ] C1 — A decisão de método para C18/C19 nesta task corresponde item a item à linha 28 do fonte (método selecionado, referências/chaves e limite); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task.
- [ ] C2 — Nada acrescido além do fonte; a dependência externa (etapas 6–7) permanece registrada como pendência, sem antecipação de experimentos, splits, métricas ou valores; IDs permanentes; nada apresentado como resultado medido.
- [ ] C3 — O documento-fonte permanece intocado (`git diff` vazio em relação à base); correções limitadas ao arquivo desta task em dif mínimo; commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo não tocado.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
2/10 — Conferência textual de uma linha de tabela; o risco é antecipar design experimental: a task registra a decisão e a pendência, nada mais.

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

### Revisão
- Orquestrador: —
- Alvo: —
- Avaliações: —
- Nota final: —
- Parecer: —
- Decisão: pendente
- Reversão: —
- Próximo passo: —

Plano: [plan.md](../../plans/03-metodologias-de-implementacao/plan.md)
