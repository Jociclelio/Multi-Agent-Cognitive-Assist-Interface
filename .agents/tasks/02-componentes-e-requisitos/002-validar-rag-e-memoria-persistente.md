# Task 002: Validar especificação de RAG documental e memória persistente — C04 e C09

Estado: fechada
Depende de: 001
Origem: nenhuma

## Prompt
Conferir que a especificação abaixo dos componentes C04 e C09 reproduz **fielmente** as características exigidas e os critérios verificáveis de `fase2/documentos/02_componentes_e_requisitos.md` (documento-fonte normativo, que permanece intocado). Registrar em Evidências a conferência item a item contra o fonte. Desvio de fidelidade: corrija apenas o texto desta task em dif mínimo e registre em Evidências.

Especificação a validar (extraída da tabela do documento-fonte):
- **C04 — RAG documental:** busca lexical e semântica local, filtros por disciplina/versão, reranking, budget e abstinência; citações resolvíveis para documento e página; medição de recall e sustentação
- **C09 — Memória persistente:** eventos originais imutáveis, perfil corrigível, estado derivado versionado e sínteses com IDs de origem; recuperação temporal; correção, exclusão e isolamento por usuário

Além da fidelidade, conferir que: os IDs são permanentes/estáveis; nada acrescenta requisito, número ou métrica além do fonte; C04 e C09 ocupam a posição correta da cadeia do núcleo (C01 → C02/C03 → **C04/C09** → C06/C07/C08 → C11); "medição de recall" em C04 é registrada como critério verificável de avaliação futura, não como resultado medido.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver ambiguidades; prosa em português; commit de registro separado, sem amend/force-push/commits vazios.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e ambiguidades.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; "Abordagem" (cadeia do núcleo) e "Critérios de conclusão".
- `fase2/documentos/08_mapa_completo_da_testagem.md` — referência de avaliação para critérios verificáveis de C04 (recall/sustentação), sem importar conteúdo.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [x] C1 — Características e critérios de C04 e C09 correspondem item a item ao documento-fonte; conferência registrada em Evidências.
- [x] C2 — IDs permanentes/estáveis; "medição de recall" apresentada exclusivamente como critério verificável de avaliação futura, nunca como resultado medido.
- [x] C3 — Nenhum requisito, número ou métrica além do fonte; posição de C04/C09 na cadeia do núcleo registrada corretamente.
- [x] C4 — Documento-fonte intocado (`git diff` vazio para ele em relação à base); correções limitadas ao arquivo desta task em dif mínimo.
- [x] C5 — Commit de registro com evidências separado de qualquer commit de entrega; sem commits vazios, amend ou force-push.

## Execução
- Modelo: GLM-5.3-Flash (provider `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime
- Base: 05b213a26c2dea1257e6b2072a7e8fe935ee061c (HEAD, árvore limpa)
- Entrega: d980d80b0d7294995cad5b1f5c49280205f9c323 (correção de fidelidade tipográfica no próprio arquivo da task)
- Arquivos da entrega: `.agents/tasks/02-componentes-e-requisitos/002-validar-rag-e-memoria-persistente.md` (2 linhas, remoção do ponto final acrescido nas células C04 e C09; nenhum outro arquivo alterado)
- Evidências:
  - **C1 (fidelidade item a item, células C04 e C09 da tabela do fonte)** — Conferência textual automatizada (script isolado em `/tmp/opencode/check_002.py`, extração por regex das células da tabela do fonte e dos bullets da especificação da task, comparação após normalização NFC/minúsculas/espaços) das células C04 (linha 10) e C09 (linha 15) de `fase2/documentos/02_componentes_e_requisitos.md`: resultado `C04 FIEL`, `C09 FIEL` após a correção descrita abaixo. Antes da correção, o único desvio era tipográfico: ponto final acrescido ao final de cada célula copiada (o fonte não pontua as células), mesmo desvio corrigido na task 001; nenhum termo, critério ou cláusula divergia. Item a item: C04 = busca lexical ✓, busca semântica local ✓, filtros por disciplina/versão ✓, reranking ✓, budget ✓, abstinência ✓, citações resolvíveis para documento e página ✓, medição de recall ✓, sustentação ✓; C09 = eventos originais imutáveis ✓, perfil corrigível ✓, estado derivado versionado ✓, sínteses com IDs de origem ✓, recuperação temporal ✓, correção ✓, exclusão ✓, isolamento por usuário ✓. Diferença legítima mantida: inicial minúscula em "busca/eventos" na task (posição na frase); capitalização de "IDs" e "RAG" preservada.
  - **C1 (correção aplicada)** — Remoção do ponto final nas duas células da especificação (dif de 2 linhas, commit de entrega `d980d80`), preservando integralmente o sentido do fonte; nenhuma outra alteração no arquivo da task.
  - **C2 (IDs permanentes/estáveis; "medição de recall" como critério futuro)** — O fonte declara na abertura (linha 3): "Os IDs abaixo são permanentes e ligam pesquisa, arquitetura e testes"; a task referencia os componentes apenas pelos IDs C04/C09 com seus nomes canônicos do fonte ("RAG documental", "Memória persistente"), sem nome alternativo. A expressão "medição de recall e sustentação" aparece na especificação como cláusula do critério verificável da célula C04 e no Prompt como critério de conferência ("é registrada como critério verificável de avaliação futura, não como resultado medido"); nenhuma frase da task afirma ter medido recall ou sustentação. Referência auxiliar conferida sem importar conteúdo: `fase2/documentos/08_mapa_completo_da_testagem.md` trata recall como métrica de avaliação futura (linha 245: `| C04 | W02/O03/F03,F04 | recall/claim/citação |`), coerente com o enquadramento adotado.
  - **C3 (nada acrescido; posição na cadeia do núcleo)** — Varredura de números na especificação C04+C09: nenhum (saída do script: `numeros na especificacao C04+C09: nenhum`); nenhum valor de qualidade, latência, orçamento ou parâmetro acrescido (respeita C17/questão aberta 4 do plano). A cadeia do núcleo citada no Prompt da task ("C01 → C02/C03 → **C04/C09** → C06/C07/C08 → C11", com C04/C09 em negrito na terceira posição) coincide literalmente com a seção "Dependências e prioridades" do fonte (linha 30: "Núcleo implementável: C01 → C02/C03 → C04/C09 → C06/C07/C08 → C11, sustentado desde o início por C13–C17/C20") — script confirma (`cadeia citada na task: True`).
  - **C4 (fonte intocado)** — `git diff 05b213a -- fase2/documentos/02_componentes_e_requisitos.md` vazio (exit 0, sem saída); diff total da entrega limitado ao arquivo desta task (2 linhas); as seis ambiguidades do fonte permanecem decisões pendentes, nenhuma resolvida.
  - **Verificador do repositório (apoio)** — `python3 fase2/scripts/verificar_documentos.py` a partir da raiz: `status: "passed"`, `components: 20`, `missing_citations: []`, `local_links_checked: 39`, `delivery_pending: []` — confirma a integridade documental da fase 2 (incluindo a tabela C01–C20 do fonte) na base trabalhada. Limitação anotada: o verificador é checagem documental (stdlib only) e não valida experimentalmente nada; não constitui resultado medido.
- Pendências/bloqueios: nenhum. As seis ambiguidades do fonte permanecem decisões pendentes (nenhuma é específica de C04/C09 nesta task); a "medição de recall e sustentação" de C04 segue como critério verificável de avaliação futura, dependente de C18/C19.

## Notas

### Dificuldade esperada
2/10 — Conferência textual de duas linhas de tabela; risco baixo, com atenção apenas ao enquadramento de "medição de recall" como critério e não como resultado.

### Dificuldade sentida
2/10 — Conferência textual direta de duas células contra a tabela do próprio documento-fonte, com checagem automatizada por script isolado; a única decisão de julgamento foi classificar o ponto final acrescido como desvio tipográfico de fidelidade (corrigido em dif mínimo, seguindo o precedente da task 001) e não como reescrita legítima, além de manter o enquadramento de "medição de recall e sustentação" como critério verificável de avaliação futura, sem apresentá-lo como resultado medido.

### Revisão
- Orquestrador: sd2/GLM-5.3-Flash (master do ciclo opt-in; sessão própria)
- Alvo: base `05b213a26c2dea1257e6b2072a7e8fe935ee061c`; entrega `d980d80b0d7294995cad5b1f5c49280205f9c323`; registro `69d038ef0dbfebb61f1923d60b9186e78d087b21`; árvore limpa na rodada.
- Modo da rodada: paralelo (revisão textual somente leitura, sem recursos compartilhados do sistema); três sessões novas, modelos distintos.
- Avaliações: sd2/GLM-5.3-Flash — 9,5/10, aprovada; openai/gpt-6-luna — 9/10, aprovada; opencode/mimo-v2.6-flash-free — 9/10, aprovada. Sem revisores substituídos; nenhum falhou.
- Nota final: 9/10 — Os três revisores reproduziram independentemente a conferência item a item de C04 e C09 contra `fase2/documentos/02_componentes_e_requisitos.md` (linhas 10 e 15), confirmando fidelidade literal após o dif mínimo da entrega (remoção de ponto final nas duas células); cadeia do núcleo conferida contra a linha 30 do fonte; documento-fonte intocado (`git diff` vazio contra a base); commits de entrega e registro separados e não vazios; verificar_documentos.py `passed` (checagem documental, não resultado medido). Divergência irrelevante entre revisores restringe-se à nota (9–9,5); achados menores convergentes: a evidência C1 cita script efêmero em `/tmp/opencode/check_002.py` não versionado (mitigado pela reprodução independente idêntica de dois revisores; impacto baixo, sem ação).
- Parecer: todos os critérios C1–C5 comprovados por evidência independente dos três revisores; entrega fiel, mínima e corretamente registrada.
- Decisão: fechar
- Reversão: não se aplica — sem artefatos a reverter (entrega de validação sem desvios).
- Próximo passo: liberar a task 003 (`003-validar-tutor-monitor-e-estado-de-aprendizagem.md`, critérios C06/C07/C08).

<!-- task-cycle: {"decision":"fechar","next_task":".agents/tasks/02-componentes-e-requisitos/003-validar-tutor-monitor-e-estado-de-aprendizagem.md","family":".agents/tasks/02-componentes-e-requisitos/001-validar-fundacao-inferencia-ingestao-ontologia.md","plan":".agents/plans/02-componentes-e-requisitos/plan.md"} -->

Plano: [plan.md](../../plans/02-componentes-e-requisitos/plan.md)

Plano: [plan.md](../../plans/02-componentes-e-requisitos/plan.md)
