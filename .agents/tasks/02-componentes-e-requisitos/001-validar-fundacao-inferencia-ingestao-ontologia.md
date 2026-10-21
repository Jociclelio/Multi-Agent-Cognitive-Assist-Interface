# Task 001: Validar especificação dos componentes fundação — C01, C02 e C03

Estado: fechada
Depende de: nenhuma
Origem: nenhuma

## Prompt
Conferir que a especificação abaixo dos componentes C01–C03 reproduz **fielmente** as características exigidas e os critérios verificáveis de `fase2/documentos/02_componentes_e_requisitos.md` (documento-fonte normativo, que permanece intocado). Registrar em Evidências a conferência item a item contra o fonte. Se encontrar desvio de fidelidade entre esta especificação e o fonte, corrija **apenas o texto desta task** em dif mínimo, preservando o sentido do fonte, e registre a correção em Evidências.

Especificação a validar (extraída da tabela do documento-fonte):
- **C01 — Inferência local:** artefato Bonsai 2 identificável, licença, revisão/hash, runtime, quantização, tokenizer, janela e suporte a JSON; execução offline; um servidor compartilhado com fila limitada; benchmark de português e ferramentas antes da adoção *(Ambiguidade pendente 1: Bonsai 2 é nomeado sem identificador, precisão ou hardware — não se pode derivar qualidade e latência dessa designação; a escolha do artefato exige decisão externa.)*
- **C02 — Ingestão e proveniência:** PDF/texto, página/seção, hash, versão, ordem, diagnóstico de OCR e tabelas; nenhum prazo promovido sem origem; material ilegível resulta em pendência explícita
- **C03 — Ontologia acadêmica:** disciplina/tópico/pré-requisito/avaliação/recurso com IDs; datas com timezone e confiança; autoridade do PDD confirmado superior a sugestões; conflitos rastreáveis *(Ambiguidade pendente 4 relacionada: documento externo mais recente não substitui automaticamente prazo confirmado; mudanças exigem reconciliação.)*

Além da fidelidade, conferir que: os IDs são tratados como permanentes e estáveis (referências futuras citam IDs, não nomes alternativos); nada nesta especificação acrescenta requisito, número ou métrica não presente no fonte; os componentes aparecem na posição correta da cadeia do núcleo (C01 → C02/C03).

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver as ambiguidades — apenas registrá-las como pendentes; não apresentar especificação como resultado medido; prosa em português; commits de registro em português, sem amend/force-push.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e ambiguidades; fonte normativo da conferência.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; seções "Abordagem", "Escopo" e "Critérios de conclusão" definem o esperado.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — mapa normativo de implementação, apoio para checar alinhamento de terminologia, sem importar conteúdo.
- `AGENTS.md` (raiz) — convenções do repositório (não apresentar propostas como resultados medidos).

## Corretude
- [x] C1 — As características exigidas e critérios verificáveis de C01, C02 e C03 nesta task correspondem item a item ao documento-fonte (tabela da seção de componentes); conferência registrada em Evidências.
- [x] C2 — Os IDs C01–C03 são tratados como permanentes/estáveis e as ambiguidades 1 e 4 aparecem apenas como decisões pendentes, sem resolução arbitrária.
- [x] C3 — Nenhum requisito, número ou métrica foi acrescido além do fonte; nenhuma formulação apresenta especificação como resultado medido.
- [x] C4 — O documento-fonte `fase2/documentos/02_componentes_e_requisitos.md` permanece intocado (`git diff` vazio para ele em relação à base); correções, se houver, limitam-se ao arquivo desta task em dif mínimo.
- [x] C5 — Commit de registro com evidências separado de qualquer commit de entrega; sem commits vazios, amend ou force-push.

## Execução
- Modelo: GLM-5.3-Flash (provider `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime
- Base: 19a57f3be92528b4acd13f7e59fd231a29e51572
- Entrega: 728cfd0642d71458b3e837bb010fee6daf23f0e0 (correção de fidelidade pontual no próprio arquivo da task)
- Arquivos da entrega: `.agents/tasks/02-componentes-e-requisitos/001-validar-fundacao-inferencia-ingestao-ontologia.md` (3 linhas, remoção do ponto final acrescido nas células C01–C03; nenhum outro arquivo alterado)
- Evidências:
  - **C1 (fidelidade item a item, células C01–C03 da tabela do fonte)** — Conferência textual automatizada (script isolado em `/tmp/opencode/check_001.py`, extração por regex das células da tabela do fonte e dos bullets da especificação da task, comparação após normalização NFC/minúsculas/espaços) das células C01 (linha 7), C02 (linha 8) e C03 (linha 9) de `fase2/documentos/02_componentes_e_requisitos.md`: resultado `C01 FIEL`, `C02 FIEL`, `C03 FIEL` após a correção descrita abaixo. Antes da correção, o único desvio era tipográfico: ponto final acrescido ao final de cada célula copiada (o fonte não pontua as células); nenhum termo, critério ou cláusula divergia. Diferenças legítimas mantidas: inicial minúscula em "artefato/disciplina" na task (posição na frase) e capitalização de "Bonsai 2", "OCR", "JSON", "IDs", "PDD" preservada.
  - **C1 (correção aplicada)** — Remoção do ponto final nas três células da especificação (dif de 3 caracteres, commit de entrega `728cfd0`), preservando integralmente o sentido do fonte; nenhuma outra alteração no arquivo da task.
  - **C2 (IDs permanentes/estáveis; ambiguidades 1 e 4 como pendentes)** — O fonte declara na abertura (linha 3): "Os IDs abaixo são permanentes e ligam pesquisa, arquitetura e testes"; a task referencia os componentes apenas pelos IDs C01/C02/C03 com seus nomes canônicos do fonte ("Inferência local", "Ingestão e proveniência", "Ontologia acadêmica"), sem nome alternativo. A ambiguidade 1 do fonte (linha 34: "A proposta nomeia Bonsai 2 sem identificador, precisão ou hardware: não se pode derivar qualidade e latência dessa designação") aparece na task como parêntese de "Ambiguidade pendente 1", com a nota adicional "a escolha do artefato exige decisão externa" — eco da questão aberta 1 do plano, sem fixar artefato, precisão ou hardware. A ambiguidade 4 (linha 37: "O documento externo mais recente não deve substituir automaticamente um prazo confirmado; mudanças precisam de reconciliação") aparece como "Ambiguidade pendente 4 relacionada", sem política de reconciliação proposta. Nenhuma das duas é resolvida; script confirma (`amb1 como pendente: True | amb4 como pendente: True`).
  - **C3 (nada acrescido além do fonte; nada como resultado medido)** — Varredura de números na especificação C01–C03: apenas "2" (de "Bonsai 2") e "1"/"4" (numeração das ambiguidades do próprio fonte, seção "Ambiguidades que precisam de decisão"); nenhum valor de qualidade, latência, orçamento ou parâmetro acrescido. A especificação é rotulada como "Especificação a validar (extraída da tabela do documento-fonte)" e nenhuma frase a apresenta como resultado medido. O parêntese da ambiguidade 1 acrescenta somente a consequência de pendência já registrada no plano (questão aberta 1), não requisito novo.
  - **C1/C2 (posição na cadeia do núcleo)** — Fonte, seção "Dependências e prioridades" (linha 30): "Núcleo implementável: C01 → C02/C03 → …" — a task coloca C01 como fundação e C02/C03 como passo seguinte, na ordem correta (primeira task da família 001→008 do plano, que segue a cadeia).
  - **C4 (fonte intocado)** — `git diff --quiet -- fase2/documentos/02_componentes_e_requisitos.md` vazio em relação à base `19a57f3`; `git status` limpo após os commits; diff total da entrega limitado ao arquivo da task (3 linhas).
  - **Verificador do repositório (apoio)** — `python3 fase2/scripts/verificar_documentos.py` a partir da raiz: `status: "passed"`, `components: 20`, `missing_citations: []`, `local_links_checked: 39`, `delivery_pending: []` — confirma a integridade documental da fase 2 (incluindo a tabela C01–C20 do fonte) na base trabalhada. Limitação anotada: o verificador é checagem documental (stdlib only, sem checagem de PDF/checksum) e não valida experimentalmente nada; não constitui resultado medido.
- Pendências/bloqueios: nenhum. As seis ambiguidades do fonte permanecem decisões pendentes (desta task, somente as de números 1 e 4 são pertinentes e seguem pendentes); a escolha concreta do artefato Bonsai 2 exige decisão externa (questão aberta 1 do plano).

## Notas

### Dificuldade esperada
2/10 — Conferência textual de três linhas de tabela contra o próprio documento-fonte; risco baixo, exigindo apenas disciplina de não parafrasear além do fonte.

### Dificuldade sentida
2/10 — Conferência textual direta de três células contra a tabela do próprio documento-fonte, com checagem automatizada por script isolado; a única decisão de julgamento foi classificar o ponto final acrescido como desvio tipográfico de fidelidade (corrigido em dif mínimo) e não como reescrita legítima, além de manter as ambiguidades 1 e 4 apenas como pendências sem lhes atribuir resolução.

### Revisão
- Orquestrador: GLM-5.3-Flash (provider `sd2`), master do ciclo opt-in do plano 02. Rodada **paralela** (três revisores em sessões independentes): revisão documental de leitura com scripts stdlib isolados em `/tmp/opencode`, sem disputa de recursos compartilhados do sistema.
- Alvo: base `19a57f3` (19a57f3be92528b4acd13f7e59fd231a29e51572); entrega `728cfd0` (728cfd0642d71458b3e837bb010fee6daf23f0e0 — correção de fidelidade: remoção do ponto final acrescido nas células C01–C03, 3+/3−); commit de registro revisado `718862c` (718862c47773ca5727c5ee7d7dd75f53fc5a0b15), árvore limpa em `main`.
- Avaliações: sd2/GLM-5.3-Flash: 9/10 (ses_ea3b0f301ffeJUJ902W814Wr79); openai/gpt-6-luna: 9/10 (ses_ea3b0f2c8ffeSAp8CQbWYt4wzC); opencode/mimo-v2.6-flash-free: 9/10 (ses_ea3b0f28fffeiZwntYOht3bcnO). Quórum de três modelos distintos cumprido; nenhum revisor falhou; nenhuma substituição necessária. Os três verificaram fidelidade C01–C03 contra o fonte por verificação própria (scripts de extração/comparação independentes), confirmaram o documento-fonte intocado, a separação entrega/registro e as ambiguidades 1 e 4 pendentes; GLM e MiMo reexecutaram `verificar_documentos.py` → passed (components: 20).
- Nota final: 9/10 — todos os critérios C1–C5 comprovados por verificação independente dos três revisores; correção de fidelidade mínima e autorizada pelo Prompt; evidências reproduzíveis e honestas quanto às limitações (identidade via runtime, verificador documental ≠ resultado experimental). Divergências essenciais entre pareceres: nenhuma.
- Parecer: nenhum achado bloqueante. (1) GLM A1 / severidade baixa: após a correção, em C01 e C03 o corpo da célula cola no parêntese de ambiguidade sem separador — apenas estética/legibilidade, fidelidade preservada; opcional em tarefa futura. (2) GLM A2 e MiMo F2 (baixo): identidade do modelo registrada como informada pelo runtime, não verificável pelo Git — limitação inerente deste tipo de evidência. (3) MiMo F1 (baixo): ausência de bullet de evidência dedicado ao C5 no registro — os três revisores, porém, verificaram C5 diretamente (SHAs, pais, reflog linear, sem amend/force-push), e Luna confirmou C5 sem restrição; não exige reabertura. Divergência essencial entre pareceres: nenhuma.
- Decisão: fechar
- Reversão: não se aplica
- Próximo passo: liberar a task 002 (`.agents/tasks/02-componentes-e-requisitos/002-validar-rag-e-memoria-persistente.md`). Sugestão a absorver no fluxo: adicionar espaço/separador entre célula e nota de ambiguidade quando editar especificações futuras desta família, e incluir bullet de evidência para o critério de separação de commits.

<!-- task-cycle: {"decision":"fechar","next_task":".agents/tasks/02-componentes-e-requisitos/002-validar-rag-e-memoria-persistente.md","family":".agents/tasks/02-componentes-e-requisitos/001-validar-fundacao-inferencia-ingestao-ontologia.md","plan":".agents/plans/02-componentes-e-requisitos/plan.md"} -->

Plano: [plan.md](../../plans/02-componentes-e-requisitos/plan.md)
