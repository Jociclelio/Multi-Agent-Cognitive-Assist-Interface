# Task 005: Validar decisões de método — memória/contexto e planejamento (C09/C10 e C11)

Estado: fechada
Depende de: 004
Origem: nenhuma

## Prompt
Conferir que as duas decisões abaixo reproduzem **fielmente** as linhas C09/C10 e C11 da tabela "Decisões reconciliadas" de `fase2/documentos/03_metodologias_de_implementacao.md` (documento-fonte normativo, que permanece intocado; linhas 22 e 23). Registrar em Evidências a conferência item a item de cada linha (método selecionado, referências/chaves, por quê e limite). Se encontrar desvio de fidelidade, corrija **apenas o texto desta task** em dif mínimo, preservando o sentido do fonte, e registre a correção em Evidências.

Decisões a validar (extraídas da tabela do documento-fonte):
- **C09/C10 — Memória e gestão do contexto:** eventos originais, fatos temporais, projeções versionadas, recuperação antes de síntese *(referências/chaves: `packer2023memgpt`, `wu2025longmemeval`)* *(por quê e limite: preserva correções e ajuda recebida; compressão não é presumida sem perdas)*
- **C11 — Planejamento:** blocos candidatos e CP-SAT; verificador independente *(referências/chaves: `google2024cpsat`, `googleEmployeeScheduling`, `gou2024tora`)* *(por quê e limite: viabilidade verificável; prazo/duração mal interpretados continuam sendo erro upstream)*

Além da fidelidade, conferir que: os IDs C09, C10 e C11 são tratados como permanentes; nada acrescenta requisito, número ou métrica não presente no fonte; a regra "recuperação antes de síntese" (C10) é a decisão de método reconciliada e não altera a pendência de posicionamento de C10 na cadeia do núcleo registrada na etapa 2 (o fonte da etapa 2 não posiciona C10; a decisão de onde ele entra permanece externa); a ambiguidade 3 da etapa 2 (não resolver falta de tempo removendo compromissos silenciosamente, C11) permanece pendente; a fronteira da etapa 2 (prazo/duração mal interpretados = erro upstream) permanece coerente.

Restrições: não alterar o documento-fonte nem criar documento novo; não posicionar C10 na cadeia nem resolver a ambiguidade 3; nada apresentado como resultado medido; IDs C01–C20 permanentes; prosa em português; commit de entrega (correção de fidelidade, se houver) e commit de registro separados, sem amend/force-push/commits vazios; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/03_metodologias_de_implementacao.md` — documento-fonte: tabela "Decisões reconciliadas", linhas C09/C10 (linha 22) e C11 (linha 23).
- `fase2/pesquisa/03b_pedagogia_memoria_planejamento.md` — relatório integral da frente de pedagogia/memória/planejamento (C06–C12), referência de embasamento, sem reabrir alternativas.
- `.agents/tasks/02-componentes-e-requisitos/002-validar-rag-e-memoria-persistente.md`, `004-validar-planejamento-solver-e-agenda.md` e `009-completar-cobertura-c10-e-ajustar-evidencias-da-consolidacao.md` — etapa 2: características de C09/C11 e a pendência de posicionamento de C10.
- `.agents/plans/03-metodologias-de-implementacao/plan.md` — plano aprovado.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [x] C1 — As decisões de método para C09/C10 e C11 nesta task correspondem item a item às linhas 22 e 23 do fonte (método selecionado, referências/chaves e limite de cada linha); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task.
- [x] C2 — Nada acrescido além do fonte; a pendência de posicionamento de C10 e a ambiguidade 3 (C11) permanecem pendentes, não resolvidas nem reclassificadas; IDs permanentes; nada apresentado como resultado medido.
- [x] C3 — O documento-fonte permanece intocado (`git diff` vazio em relação à base); correções limitadas ao arquivo desta task em dif mínimo; commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo não tocado.

## Execução
- Modelo: sd2/GLM-5.3-Flash
- Base: `0322e4006ef75d00fa426875074e05cd8d94b68a`
- Entrega: sem alteração de artefatos — conferência textual não encontrou desvio de fidelidade; nenhuma correção no arquivo desta task foi necessária, portanto não há commit de entrega (apenas o commit de registro).
- Arquivos da entrega: nenhum (registro somente neste `.md`).
- Evidências:
  - **C09/C10 (linha 22 do fonte)** — conferência item a item: método selecionado "Eventos originais, fatos temporais, projeções versionadas, recuperação antes de síntese" idêntico ao texto da task; referências/chaves `packer2023memgpt` e `wu2025longmemeval` idênticas e presentes em `fase2/references.bib` (linhas 225 e 296); "por quê e limite" "Preserva correções e ajuda recebida; compressão não é presumida sem perdas" reproduzido sem alteração.
  - **C11 (linha 23 do fonte)** — conferência item a item: método selecionado "Blocos candidatos e CP-SAT; verificador independente" idêntico ao texto da task; referências/chaves `google2024cpsat`, `googleEmployeeScheduling` e `gou2024tora` idênticas e presentes em `fase2/references.bib` (linhas 305, 313 e 252); "por quê e limite" "Viabilidade verificável; prazo/duração mal interpretados continuam sendo erro upstream" reproduzido sem alteração.
  - **IDs e escopo**: C09, C10 e C11 tratados como IDs permanentes do conjunto C01–C20; nenhum requisito, número ou métrica acrescido além do fonte; nada apresentado como resultado medido; nenhuma alternativa do fonte selecionada ou fechada.
  - **Pendências preservadas**: a decisão de método "recuperação antes de síntese" (C10) não foi interpretada como posicionamento de C10 na cadeia do núcleo — confirmado na etapa 2 (task `009-completar-cobertura-c10-e-ajustar-evidencias-da-consolidacao.md`: o fonte da etapa 2 não posiciona C10; cadeia "C01 → C02/C03 → C04/C09 → C06/C07/C08 → C11"; pendência de posicionamento registrada, não resolvida). A ambiguidade 3 da etapa 2 (não resolver falta de tempo removendo compromissos silenciosamente, ligada a C11) permanece pendente conforme a task `004-validar-planejamento-solver-e-agenda.md`; a fronteira "prazo/duração mal interpretados = erro upstream" permanece coerente com o limite da linha C11.
  - **Documento-fonte intocado**: `git diff -- fase2/documentos/03_metodologias_de_implementacao.md` vazio em relação à base `0322e40`; submódulo `docs/playground-llmagenticsystem` não tocado; nenhum documento novo criado.
- Pendências/bloqueios: nenhum bloqueio. Pendências herdadas do fonte, apenas registradas e não resolvidas aqui: posicionamento de C10 na cadeia do núcleo e ambiguidade 3 da etapa 2.

## Notas

### Dificuldade esperada
2/10 — Conferência textual de duas linhas de tabela; cuidado em não interpretar a decisão de método de C10 como posicionamento dele na cadeia do núcleo.

### Dificuldade sentida
1/10 — Conferência textual direta de duas linhas de tabela, com correspondência exata em método, chaves e limite; o único cuidado foi separar a decisão de método de C10 ("recuperação antes de síntese") do posicionamento dele na cadeia do núcleo, que permanece pendente da etapa 2.

### Revisão
- Orquestrador: sd2/GLM-5.3-Flash (task-master, ciclo opt-in)
- Alvo: esta task; base `0322e40`; commit de entrega: nenhum ("não se aplica — sem artefatos", não houve desvio de fidelidade); commit de registro `2906d51` (único commit base→HEAD, somente este arquivo); árvore limpa; fonte normativo e submódulo intocados.
- Modo da rodada: paralelo — conferência textual sem recursos compartilhados do sistema; três revisores independentes do pool fixo do ciclo, sessões novas.
- Avaliações: sd2/GLM-5.3-Flash — 9/10, aprovada; openai/gpt-6-luna — 9/10, aprovada; opencode/mimo-v2.6-flash-free — 9/10, aprovada. Nenhum revisor falhou; sem substituições.
- Nota final: 9/10 — fidelidade das linhas 22 e 23 do fonte confirmada por comparação textual independente (um revisor com script de normalização em `/tmp/opencode`); chaves confirmadas em `fase2/references.bib` (225, 296, 305, 313, 252); pendências de C10 e ambiguidade 3 preservadas; `verificar_documentos.py` passed; desconto pela natureza de registro documental da entrega.
- Parecer: achados apenas baixos/informativos, pré-existentes na base e não imputáveis ao executor — (A1) a frase do Prompt "fronteira da etapa 2 (prazo/duração mal interpretados = erro upstream)" atribui à etapa 2 um limite que é texto da linha 23 da etapa 3; (A2) rótulos "Memória e gestão do contexto" e "Planejamento" abreviam nomes canônicos da etapa 2, coerente com as tasks 001–004 da família. Nenhum bloqueia; sem correção exigida.
- Decisão: fechar — todos os critérios C1–C3 comprovados por evidência independente; pendências registradas, não resolvidas.
- Reversão: não se aplica — sem artefatos a reverter.
- Próximo passo: liberar task 006 (C12/C13/C14 — agenda/orquestração), dependência cumprida.

<!-- task-cycle: {"decision":"fechar","next_task":".agents/tasks/03-metodologias-de-implementacao/006-validar-decisoes-agenda-orquestracao-c12-c13-c14.md","family":".agents/tasks/03-metodologias-de-implementacao/002-validar-decisao-ingestao-ontologia-c02-c03.md","plan":".agents/plans/03-metodologias-de-implementacao/plan.md"} -->
Plano: [plan.md](../../plans/03-metodologias-de-implementacao/plan.md)
