# Task 008: Validar dependência externa — avaliação experimental (C18/C19)

Estado: aguardando revisão
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
- [x] C1 — A decisão de método para C18/C19 nesta task corresponde item a item à linha 28 do fonte (método selecionado, referências/chaves e limite); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task. *(Sem desvio de fidelidade: nenhuma correção foi necessária.)*
- [x] C2 — Nada acrescido além do fonte; a dependência externa (etapas 6–7) permanece registrada como pendência, sem antecipação de experimentos, splits, métricas ou valores; IDs permanentes; nada apresentado como resultado medido.
- [x] C3 — O documento-fonte permanece intocado (`git diff` vazio em relação à base); correções limitadas ao arquivo desta task em dif mínimo; commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo não tocado.

## Execução
- Modelo: GLM-5.3-Flash (via `~/sd2-llm.sh`; provider `sd2`, model ID `GLM-5.3-Flash`)
- Base: `c442af31484c45c23fca4d440bed6b450b4d48f5`
- Entrega: sem alteração de artefatos — conferência de fidelidade confirmou correspondência integral; não houve commit de entrega.
- Arquivos da entrega: — (apenas este arquivo de task no commit de registro)
- Evidências:
  - Conferência item a item contra `fase2/documentos/03_metodologias_de_implementacao.md`, linha 28 (lida direto do fonte, intocado):
    - **C18/C19 (linha 28 do fonte):** método "Ouro independente, splits por família, avaliação pareada, ablações e falhas injetadas" = task linha 11 "ouro independente, splits por família, avaliação pareada, ablações e falhas injetadas" ✓; referências/chaves "Pesquisa específica na etapa 7" = task "pesquisa específica na etapa 7" ✓; por quê e limite "Seleção de parâmetros em validação, nunca no teste final" = task "seleção de parâmetros em validação, nunca no teste final" ✓.
    - Únicas diferenças: caixa da letra inicial ("Ouro"→"ouro", "Pesquisa"→"pesquisa", "Seleção"→"seleção"), ajuste tipográfico decorrente da inserção no fluxo da frase, sem alteração de sentido — não configuram desvio de fidelidade, portanto nenhuma correção foi aplicada.
  - Dependência externa verificada: linha 10 do fonte ("C18–C19 são completados pela pesquisa específica das etapas 6–7") e questão aberta do plano (`plan.md`, "C18–C19 dependem da pesquisa específica das etapas 6–7 (ainda não contemplada por este plano)"); a task linha 13 registra a dependência como pendência, sem antecipar a pesquisa nem decisões dos mapas normativos (`04_mapa_completo_do_sistema.md` e `08_mapa_completo_da_testagem.md`, não consultados para decisão).
  - IDs C18 e C19 tratados como permanentes (rótulos da tabela fonte); nenhum experimento, split, métrica ou valor acrescido além do fonte; a regra "seleção de parâmetros em validação, nunca no teste final" citada apenas como limite, sem valores definidos; nada apresentado como resultado medido.
  - `git diff c442af3 -- fase2/documentos/03_metodologias_de_implementacao.md docs/playground-llmagenticsystem`: vazio — documento-fonte e submódulo intocados.
  - `python3 fase2/scripts/verificar_documentos.py`: `status: passed` (escopo: documentação; não experimentos do sistema).
- Dificuldade sentida: registrada abaixo.

## Notas

### Dificuldade esperada
2/10 — Conferência textual de uma linha de tabela; o risco é antecipar design experimental: a task registra a decisão e a pendência, nada mais.

### Dificuldade sentida
1/10 — Conferência textual direta de uma linha de tabela contra o texto já extraído na task; correspondência integral, sem necessidade de correção. Único cuidado: distinguir ajuste de caixa tipográfica de desvio de fidelidade e registrar a pendência das etapas 6–7 sem antecipar design experimental.

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
