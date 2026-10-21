# Task 006: Validar especificação da camada transversal II — persistência, observabilidade e empacotamento — C16, C17 e C20

Estado: aguardando revisão
Depende de: 005
Origem: nenhuma

## Prompt
Conferir que a especificação abaixo dos componentes C16, C17 e C20 reproduz **fielmente** as características exigidas e os critérios verificáveis de `fase2/documentos/02_componentes_e_requisitos.md` (documento-fonte normativo, que permanece intocado). Registrar em Evidências a conferência item a item. Desvio de fidelidade: corrija apenas o texto desta task em dif mínimo e registre em Evidências.

Especificação a validar (extraída da tabela do documento-fonte):
- **C16 — Persistência e recuperação:** transações, outbox, controle otimista de versão, migrações, backup, retomada e deduplicação; teste de crash antes/depois de efeitos
- **C17 — Observabilidade e limites:** trace por turno, tokens, tempo, RSS/VRAM, hashes de modelo/prompt, solver status; orçamento de chamadas, tempo e reparos; cancelamento e resposta controlada *(Questão aberta do plano: as definições dos orçamentos de C17 não constam do documento-fonte e não devem ser inventadas nesta etapa.)*
- **C20 — Empacotamento e execução:** manifesto/lock de versões e hashes, configuração documentada, instalação offline possível, smoke test e CLI; hardware real registrado; extensões não obrigatórias para fechar o núcleo

Além da fidelidade, conferir que: os IDs são permanentes/estáveis; nada acrescenta requisito, número ou métrica além do fonte (em especial, nenhum valor de orçamento para C17); C16/C17/C20 estão registrados como camada que sustenta o núcleo desde o início.

Restrições: não alterar o documento-fonte nem criar documento novo; não definir orçamentos nem inventar parâmetros; prosa em português; commit de registro separado, sem amend/force-push/commits vazios.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e ambiguidades.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; "Abordagem" (camada transversal) e "Questões abertas" (item 4: orçamentos de C17 não constam do documento).
- `fase2/documentos/04_mapa_completo_do_sistema.md` — apoio para checar alinhamento de terminologia, sem importar conteúdo.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [x] C1 — Características e critérios de C16, C17 e C20 correspondem item a item ao documento-fonte; conferência registrada em Evidências.
- [x] C2 — IDs permanentes/estáveis; nenhum valor de orçamento (chamadas, tempo, reparos) ou outro parâmetro inventado para C17; a ausência de definições registrada como questão aberta.
- [x] C3 — Nenhum requisito, número ou métrica além do fonte; C16/C17/C20 caracterizados como sustentação do núcleo desde o início.
- [x] C4 — Documento-fonte intocado (`git diff` vazio para ele em relação à base); correções limitadas ao arquivo desta task em dif mínimo.
- [x] C5 — Commit de registro com evidências separado de qualquer commit de entrega; sem commits vazios, amend ou force-push.

## Execução
- Modelo: GLM-5.3-Flash (via ~/sd2-llm.sh; provider sd2, model GLM-5.3-Flash)
- Base: `2b757cd49ae83ecbad8f05c1f3c670a3707f9d57` (árvore limpa)
- Entrega: `c94cbd64e0e44ee6dec2c0c326f869a67d47a55a` (commit de entrega; commit de registro separado, sem SHA próprio neste arquivo)
- Arquivos da entrega: `.agents/tasks/02-componentes-e-requisitos/006-validar-persistencia-observabilidade-e-empacotamento.md` (3 linhas, remoção do ponto final acrescido nas células C16, C17 e C20 — no C17, entre a célula e a nota de questão aberta; nenhum outro arquivo alterado)
- Evidências:
  - **C1 (fidelidade item a item, células C16/C17/C20 da tabela do fonte)** — Conferência textual automatizada (script isolado em `/tmp/opencode/check_006.py`, extração por regex das células da tabela do fonte e dos bullets da especificação da task, comparação após normalização NFC/aspas/travessões/espaços/minúsculas) das células C16 (linha 22), C17 (linha 23) e C20 (linha 26) de `fase2/documentos/02_componentes_e_requisitos.md`: resultado `C16 FIEL`, `C17 FIEL`, `C20 FIEL` após a correção descrita abaixo. Antes da correção, o único desvio era tipográfico: ponto final acrescido ao final de cada célula copiada — no C17, entre a célula e a nota de questão aberta (o fonte não pontua as células), mesmo desvio corrigido nas tasks 001–005; nenhum termo, critério ou cláusula divergia e a cobertura termo a termo era completa já antes. Item a item: C16 = transações ✓, outbox ✓, controle otimista de versão ✓, migrações ✓, backup ✓, retomada ✓, deduplicação ✓, "teste de crash antes/depois de efeitos" ✓; C17 = trace por turno ✓, tokens ✓, tempo ✓, RSS/VRAM ✓, hashes de modelo/prompt ✓, solver status ✓, "orçamento de chamadas, tempo e reparos" ✓, "cancelamento e resposta controlada" ✓; C20 = manifesto/lock de versões e hashes ✓, configuração documentada ✓, instalação offline possível ✓, smoke test e CLI ✓, hardware real registrado ✓, "extensões não obrigatórias para fechar o núcleo" ✓. Diferenças legítimas mantidas: inicial minúscula em "transações", "trace" e "manifesto" na task (posição na frase, como "allowlist" na task 005); capitalização de "RSS/VRAM", "solver status", "CLI" e "smoke test" preservada.
  - **C2 (IDs permanentes/estáveis; nenhum orçamento/parâmetro inventado; questão aberta registrada)** — O fonte declara na abertura (linha 3): "Os IDs abaixo são permanentes e ligam pesquisa, arquitetura e testes"; a task referencia os componentes apenas pelos IDs C16/C17/C20 com seus nomes canônicos do fonte ("Persistência e recuperação", "Observabilidade e limites", "Empacotamento e execução"), sem nome alternativo. Sobre C17: a nota "*(Questão aberta do plano: as definições dos orçamentos de C17 não constam do documento-fonte e não devem ser inventadas nesta etapa.)*" registra a questão aberta 4 do plano (linha 35: "Definições de orçamentos (chamadas, tempo, reparos — C17) e demais parâmetros não constam do documento e não devem ser inventados aqui."); o corpo da célula C17 na task contém exatamente os mesmos termos do fonte — "orçamento de chamadas, tempo e reparos" — sem nenhum valor numérico, limite ou parâmetro acrescido (varredura de dígitos no corpo: nenhuma ocorrência, idêntica ao fonte).
  - **C3 (nada acrescido; sustentação do núcleo desde o início; nada medido)** — Varredura de números na especificação C16/C17/C20: zero dígitos no corpo das três células, tanto na task quanto no fonte (saída do script: `numeros C16/C17/C20 task=[] fonte=[]`); nenhum requisito, métrica ou critério além do fonte. A caracterização no Prompt da task ("C16/C17/C20 estão registrados como camada que sustenta o núcleo desde o início") coincide com a seção "Dependências e prioridades" do fonte (linha 30: "sustentado desde o início por C13–C17/C20"), que cobre C16, C17 e C20 (script confirma a presença da caracterização). Nenhuma frase da task afirma ter medido, executado ou validado qualquer comportamento de persistência, observabilidade ou empacotamento; a especificação é apresentada como requisito de implementação/avaliação futura.
  - **C4 (fonte intocado; correção mínima)** — `git diff 2b757cd -- fase2/documentos/02_componentes_e_requisitos.md`: vazio (0 linhas); `git diff --stat` pós-correção: somente o arquivo desta task, 3 inserções/3 remoções (os três pontos finais). Nenhum documento novo criado; `docs/playground-llmagenticsystem` (submódulo) não tocado.
  - **Verificador do repositório (apoio)** — `python3 fase2/scripts/verificar_documentos.py` a partir da raiz: `status: "passed"`, `components: 20`, `missing_citations: []`, `local_links_checked: 39`, `delivery_pending: []` — confirma a integridade documental da fase 2 (incluindo a tabela C01–C20 do fonte) na base trabalhada. Limitação anotada: o verificador é checagem documental (stdlib only) e não valida experimentalmente nada; não constitui resultado medido. Referência auxiliar consultada sem importar conteúdo: `fase2/documentos/04_mapa_completo_do_sistema.md` (alinhamento de terminologia de persistência/observabilidade/empacotamento, sem acrescentar requisitos).
- Pendências/bloqueios: nenhum. A questão aberta 4 do plano (definições dos orçamentos de C17) permanece pendente, sem resolução proposta nesta etapa; as seis ambiguidades do fonte seguem pendentes no plano.

## Notas

### Dificuldade esperada
2/10 — Conferência textual de três linhas de tabela; risco baixo, com atenção para não inventar orçamentos de C17.

### Dificuldade sentida
2/10 — Conferência textual de três células de tabela com script de comparação normalizada; a caracterização de sustentação do núcleo exigiu confronto com a seção "Dependências e prioridades" do fonte, mas o desvio encontrado foi apenas o mesmo ponto final tipográfico já corrigido nas tasks 001–005 (aqui em três pontos, incluindo o C17 antes da nota de questão aberta).

### Revisão
- Orquestrador: GLM-5.3-Flash (sd2), master do ciclo opt-in; modo da rodada: paralelo (conferência textual de arquivos Markdown, sem disputa de recursos compartilhados).
- Alvo: base `2b757cd49ae83ecbad8f05c1f3c670a3707f9d57`; entrega `c94cbd64e0e44ee6dec2c0c326f869a67d47a55a`; registro `d6aace2410da855e0165070d8c45463635f0e6e8` (HEAD). Árvore limpa e inalterada durante a rodada; documento-fonte e submódulo intocados.
- Avaliações: (1) GLM-5.3-Flash (sd2) — 9,5/10, aprovada; fidelidade C16/C17/C20 reconfirmada por comparação normalizada independente; achado baixo A1 (evidência de C1 cita script efêmero em `/tmp/opencode`, não auditável a posteriori — recomendação opcional para futuras tasks) e achado informativo A2 (nota de questão aberta demarcada no bullet C17, sem desvio). (2) openai/gpt-6-luna — 10/10, aprovada; sem achados; C1–C5 verificados via diffs e cadeia de pais. (3) opencode/mimo-v2.6-flash-free — 9,5/10, aprovada; sem achados; reimplementou a comparação das células (fiel ×3) e varredura de dígitos (zero); desconto apenas por não poder verificar estado remoto (fora de escopo). Revisores falhos: nenhum.
- Nota final: 9,5/10 — consenso de que a especificação C16/C17/C20 reproduz fielmente o documento-fonte, a correção de fidelidade foi mínima (3+/3−, só o arquivo da task), nenhum orçamento/parâmetro foi inventado para C17 e a questão aberta permanece apenas registrada, como exigido.
- Parecer: Síntese dos três pareceres (modelos distintos, sem divergência essencial): fidelidade item a item comprovada independentemente por pelo menos dois revisores com comparação normalizada própria; `git diff` do documento-fonte vazio em relação à base; submódulo intacto; commits de entrega e registro separados, lineares, sem vazios/amend/force-push; pendências mantidas por design (questão aberta 4 do plano sobre orçamentos de C17; seis ambiguidades do fonte). O único achado material é de processo (A1, script de evidência efêmero), não invalida a entrega.
- Decisão: fechar
- Reversão: não se aplica — sem reversão (entrega aprovada)
- Próximo passo: liberar task 007 (.agents/tasks/02-componentes-e-requisitos/007-validar-dados-e-avaliacao-experimental.md, C18/C19, depende de 006) no ciclo opt-in.

<!-- task-cycle: {"decision":"fechar","next_task":".agents/tasks/02-componentes-e-requisitos/007-validar-dados-e-avaliacao-experimental.md","family":".agents/tasks/02-componentes-e-requisitos/001-validar-fundacao-inferencia-ingestao-ontologia.md","plan":".agents/plans/02-componentes-e-requisitos/plan.md"} -->
Plano: [plan.md](../../plans/02-componentes-e-requisitos/plan.md)
