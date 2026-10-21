# Task 002: Validar decisão de método — ingestão e ontologia (C02/C03)

Estado: fechada
Depende de: 001
Origem: nenhuma

## Prompt
Conferir que a decisão abaixo reproduz **fielmente** a linha C02/C03 da tabela "Decisões reconciliadas" de `fase2/documentos/03_metodologias_de_implementacao.md` (documento-fonte normativo, que permanece intocado; linha 17). Registrar em Evidências a conferência item a item (método selecionado, referências/chaves, por quê e limite). Se encontrar desvio de fidelidade, corrija **apenas o texto desta task** em dif mínimo, preservando o sentido do fonte, e registre a correção em Evidências.

Decisão a validar (extraída da tabela do documento-fonte):
- **C02/C03 — Ingestão e ontologia:** Docling, OCR seletivo, blocos com página/origem, ontologia relacional e fatos candidatos *(referências/chaves: `docling`, `ocrpdf`, `pydstrict`)* *(por quê e limite: permite conferir números, datas e citações; confirmação prevalece sobre confiança verbal)*

Além da fidelidade, conferir que: os IDs C02 e C03 são tratados como permanentes; nada acrescenta requisito, número ou métrica não presente no fonte; a regra "confirmação prevalece sobre confiança verbal" aparece como limite do método (reconciliada na etapa 3), sem reabrir a ambiguidade 4 da etapa 2 (documento externo mais recente não substitui prazo confirmado; reconciliação) — que permanece pendente; a posição de C02/C03 na cadeia do núcleo (segundo passo, após C01) permanece a da etapa 2.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver ambiguidades nem a política de reconciliação de prazos; nada apresentado como resultado medido; IDs C01–C20 permanentes; prosa em português; commit de entrega (correção de fidelidade, se houver) e commit de registro separados, sem amend/force-push/commits vazios; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/03_metodologias_de_implementacao.md` — documento-fonte: tabela "Decisões reconciliadas", linha C02/C03 (linha 17).
- `fase2/pesquisa/03a_arquitetura_rag.md` — relatório integral da frente de arquitetura, referência de embasamento, sem reabrir alternativas.
- `.agents/tasks/02-componentes-e-requisitos/001-validar-fundacao-inferencia-ingestao-ontologia.md` — etapa 2: características exigidas de C02 e C03, incluindo a ambiguidade 4 como pendente.
- `.agents/plans/03-metodologias-de-implementacao/plan.md` — plano aprovado.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [x] C1 — A decisão de método para C02/C03 nesta task corresponde item a item à linha 17 do fonte (método selecionado, referências/chaves e limite); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task.
- [x] C2 — Nada acrescido além do fonte; a regra de confirmação sobre confiança verbal é registrada como limite reconciliado, sem resolver a ambiguidade 4 (pendência preservada); IDs permanentes; nada apresentado como resultado medido.
- [x] C3 — O documento-fonte permanece intocado (`git diff` vazio em relação à base); correções limitadas ao arquivo desta task em dif mínimo; commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo não tocado.

## Execução
- Modelo: GLM-5.3-Flash (provider `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime
- Base: 0581795ca7b4e5a0cb83ec15f869d6fe6c0d0bf7
- Entrega: sem alteração de artefatos — a conferência não encontrou desvio de fidelidade; nenhuma correção no arquivo desta task nem em qualquer outro arquivo (task apenas de verificação; commit documental de registro único)
- Arquivos da entrega: nenhum
- Evidências:
  - **C1 (fidelidade item a item, linha 17 do fonte)** — Conferência textual automatizada (script isolado em `/tmp/opencode/check_003_002.py`, extração da linha `| C02/C03 |` de `fase2/documentos/03_metodologias_de_implementacao.md` — confirmada na linha 17 — e do bullet da decisão desta task, comparação após normalização NFC/minúsculas/espaços): `método FIEL: True`, `refs FIEL: True`, `porquê FIEL (normalizado): True`. Campo a campo: (1) método selecionado — "Docling, OCR seletivo, blocos com página/origem, ontologia relacional e fatos candidatos", idêntico ao fonte; (2) referências/chaves — `docling`, `ocrpdf`, `pydstrict`, mesmas três chaves, mesma ordem, todas presentes em `fase2/pesquisa/references_arquitetura.bib` (linhas 34, 43 e 135 do `.bib`); (3) por quê e limite — "Permite conferir números, datas e citações; confirmação prevalece sobre confiança verbal", idêntico ao fonte após normalização. Única diferença literal: inicial minúscula em "permite" na task (posição na frase, dentro do parêntese "por quê e limite:") contra maiúscula no início da célula do fonte — adaptação tipográfica de prosa sem alteração de sentido, classificada como não-desvio e mantida sem correção. O rótulo do bullet, "Ingestão e ontologia", é rótulo de agrupamento dos dois componentes, pré-existente no prompt da task na base, e não acrescenta requisito nem renomeia os IDs.
  - **C2 (nada acrescido além do fonte; nada como resultado medido; regra como limite reconciliado)** — Varredura de números no bullet da decisão: apenas `02`/`03` (IDs C02/C03) — ambos presentes no fonte (script: `todos presentes no fonte: True`); nenhum orçamento, parâmetro, métrica ou requisito novo. A regra "confirmação prevalece sobre confiança verbal" aparece no bullet apenas como limite do método, na coluna "por quê e sob qual limite" do fonte, reconciliada na etapa 3; o texto adicional da task referencia a ambiguidade 4 da etapa 2 exclusivamente como pendente ("permanece pendente"; script: `ambiguidade 4 registrada como pendente: True`), sem propor política de reconciliação nem apresentar a regra como sua resolução. Nenhuma frase apresenta a decisão como resultado medido.
  - **C2 (IDs permanentes; posição na cadeia do núcleo)** — A decisão refere-se aos componentes apenas pelos IDs permanentes C02/C03, sem renomeação. A posição na cadeia do núcleo permanece a da etapa 2: fonte `fase2/documentos/02_componentes_e_requisitos.md`, seção "Dependências e prioridades": "Núcleo implementável: C01 → C02/C03 → C04/C09 → …" — C02/C03 como segundo passo, após C01; a ordem da família 001→002 do plano segue a mesma cadeia e nenhuma alteração de posicionamento é proposta. O posicionamento de C10 na cadeia do núcleo (pendência da etapa 2) não é tocado.
  - **C3 (fonte intocado; commits separados)** — Árvore limpa na base `0581795` antes da execução (estado confirmado por `git status`); após o registro, `git diff` vazio para `fase2/documentos/03_metodologias_de_implementacao.md` e para o submódulo `docs/playground-llmagenticsystem` (não tocado); único arquivo alterado é esta task (registro). Sem commit de entrega (não houve correção); único commit documental de registro, sem amend/force-push/commits vazios. Tentativa anterior da task interrompida sem artefato: confirmado que não há commit anterior (`git log -- <task.md>` vazio antes deste registro) e árvore limpa na base.
  - **Verificador do repositório (apoio)** — `python3 fase2/scripts/verificar_documentos.py` a partir da raiz: `status: "passed"`, `components: 20`, `missing_citations: []`, `local_links_checked: 39`, `delivery_pending: []` — integridade documental da fase 2 confirmada na base trabalhada. Limitação anotada: verificação documental (stdlib only), não constitui resultado medido nem validação experimental.
- Pendências/bloqueios: nenhum bloqueio. Permanecem pendentes, sem resolução nesta task: posicionamento de C10 na cadeia do núcleo; validação de C04 em português; ambiguidades 1–6 da etapa 2 — em particular a ambiguidade 4 (documento externo mais recente não substitui prazo confirmado; mudanças exigem reconciliação), que a regra "confirmação prevalece sobre confiança verbal" não resolve; pesquisa específica das etapas 6–7 para C18–C19; feature flag da agenda remota.

## Notas

### Dificuldade esperada
2/10 — Conferência textual de uma linha de tabela; cuidado único em não transformar o limite reconciliado em resolução da ambiguidade 4.

### Dificuldade sentida
2/10 — Conferência textual de um único bullet contra uma linha de tabela, com checagem automatizada por script isolado; a decisão de julgamento foi classificar a inicial minúscula em "permite" como adaptação tipográfica de prosa (não-desvio) e resistir à tentação de tratar a regra "confirmação prevalece sobre confiança verbal" como resolução da ambiguidade 4, que permanece pendente.

### Revisão
- Orquestrador: GLM-5.3-Flash (provider `sd2`) — task-master do ciclo opt-in.
- Alvo: base `0581795ca7b4e5a0cb83ec15f869d6fe6c0d0bf7`; commit de entrega inexistente (task de validação sem desvio — "sem alteração de artefatos"); commit de registro `bc058f8631f1d687498bd775e1ea20431e5eeb6b` (versão `bc058f8`), único arquivo tocado: o `.md` desta task; executor GLM-5.3-Flash (provider `sd2`).
- Avaliações (rodada paralela — conferência textual sem recursos compartilhados do sistema; modo e motivo registrados conforme protocolo): **sd2/GLM-5.3-Flash — 10/10, aprovada** (fidelidade confirmada por leitura direta da linha 17 do fonte; chaves conferidas no `.bib`; diff do registro não altera o Prompt nem o bullet); **openai/gpt-6-luna — 9/10, aprovada** (nota reduzida apenas porque a identidade do executor é relato do runtime, não verificável pelo diff; critérios C1–C3 atendidos); **opencode/mimo-v2.6-flash-free — 9/10, aprovada** (comparação textual independente com script próprio em `/tmp/opencode/revisor-002/`; resultado do verificador documental reproduzido; submódulo com mesmo ponteiro na base e no registro). Nenhum revisor falhou; não houve substituição. Quórum de três modelos distintos completo.
- Síntese dos achados: nenhum achado bloqueante. F1 (baixo, informativo — GLM-5.3-Flash e MiMo): a inicial minúscula em "permite" e o rótulo "Ingestão e ontologia" divergem literalmente da célula do fonte, mas já existiam no prompt da task na base (`git diff 0581795 bc058f8` não toca a linha 11) e foram classificados como adaptação tipográfica/rótulo de agrupamento, sem alteração de sentido e sem exigência de correção. Divergência entre revisores: apenas na justificativa das notas (10 vs. 9), sem contradição essencial sobre os critérios; Luna e MiMo apontam limitações de observabilidade (identidade do executor via relato do runtime; ausência de force-push remoto não demonstrável pelo reflog local) sem impactar a Corretude.
- Nota final: 9,5/10 — conferência textual rigorosa e independente confirmada pelos três revisores; entrega e registro conformes ao contrato; as únicas ressalvas são limitações de observabilidade inerentes a uma task documental, não falhas da entrega.
- Parecer: todos os critérios obrigatórios (C1–C3) comprovados com evidência própria dos revisores; pendências preservadas (em particular a ambiguidade 4, não resolvida pela regra de confirmação sobre confiança verbal); nada apresentado como resultado medido.
- Decisão: fechar
- Reversão: não se aplica — sem artefatos (nenhum commit de entrega a reverter).
- Próximo passo: liberar a task 003 (`003-validar-decisoes-recuperacao-curadoria-c04-c05.md`), dependência resolvida.

<!-- task-cycle: {"decision":"fechar","next_task":".agents/tasks/03-metodologias-de-implementacao/003-validar-decisoes-recuperacao-curadoria-c04-c05.md","family":".agents/tasks/03-metodologias-de-implementacao/002-validar-decisao-ingestao-ontologia-c02-c03.md","plan":".agents/plans/03-metodologias-de-implementacao/plan.md"} -->

Plano: [plan.md](../../plans/03-metodologias-de-implementacao/plan.md)
