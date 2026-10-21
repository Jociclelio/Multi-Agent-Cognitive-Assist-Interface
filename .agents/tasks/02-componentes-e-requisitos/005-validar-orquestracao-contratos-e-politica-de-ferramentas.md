# Task 005: Validar especificação da camada transversal I — orquestração, contratos e política de ferramentas — C13, C14 e C15

Estado: aguardando revisão
Depende de: 004
Origem: nenhuma

## Prompt
Conferir que a especificação abaixo dos componentes C13–C15 reproduz **fielmente** as características exigidas e os critérios verificáveis de `fase2/documentos/02_componentes_e_requisitos.md` (documento-fonte normativo, que permanece intocado). Registrar em Evidências a conferência item a item. Desvio de fidelidade: corrija apenas o texto desta task em dif mínimo e registre em Evidências.

Especificação a validar (extraída da tabela do documento-fonte):
- **C13 — Orquestração:** LangGraph com rotas fixas, checkpoints, pausa humana, dependências e terminais; ausência de ciclos não limitados; política para divergências; mesmas ferramentas no baseline
- **C14 — Comunicação e contratos:** JSON Schema/Pydantic, envelope com task/trace/version, referência em vez de cópia integral, leitura de snapshot; erros tipados; MCP nas fronteiras de ferramentas; A2A somente como extensão de serviços *(Ambiguidade pendente 5: A2A não é requisito para comunicação interna — acrescentar serviços remotos ao MVP ampliaria os pontos de falha sem benefício demonstrado.)*
- **C15 — Política de ferramentas:** allowlist por papel, argumentos validados, tool result como dados, rede opcional, escrita mediada; JSON correto não basta: validar também intenção e efeito

Além da fidelidade, conferir que: os IDs são permanentes/estáveis; nada acrescenta requisito, número ou métrica além do fonte; C13–C17/C20 estão registrados como camada que **sustenta o núcleo desde o início** (não como fase posterior); a ambiguidade 5 aparece apenas como decisão pendente.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver ambiguidades; prosa em português; commit de registro separado, sem amend/force-push/commits vazios.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e ambiguidades.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; "Abordagem" (camada transversal sustentando o núcleo desde o início) e "Critérios de conclusão".
- `fase2/documentos/04_mapa_completo_do_sistema.md` — apoio para checar alinhamento de terminologia (orquestrador, contratos verificáveis, validação determinística), sem importar conteúdo.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [x] C1 — Características e critérios de C13, C14 e C15 correspondem item a item ao documento-fonte; conferência registrada em Evidências.
- [x] C2 — IDs permanentes/estáveis; ambiguidade 5 (A2A fora do MVP) registrada apenas como decisão pendente; C13–C15 caracterizados como sustentação do núcleo desde o início.
- [x] C3 — Nenhum requisito, número ou métrica além do fonte; nada apresentado como resultado medido.
- [x] C4 — Documento-fonte intocado (`git diff` vazio para ele em relação à base); correções limitadas ao arquivo desta task em dif mínimo.
- [x] C5 — Commit de registro com evidências separado de qualquer commit de entrega; sem commits vazios, amend ou force-push.

## Execução
- Modelo: GLM-5.3-Flash (via ~/sd2-llm.sh; provider sd2, model GLM-5.3-Flash)
- Base: `381e5065920e04bc8d69614d09249156b5402781` (árvore limpa)
- Entrega: `1cf8eab4cae7ba3d8946badd72f614e6a79f1996` (commit de entrega; commit de registro separado, sem SHA próprio neste arquivo)
- Arquivos da entrega: `.agents/tasks/02-componentes-e-requisitos/005-validar-orquestracao-contratos-e-politica-de-ferramentas.md` (3 linhas, remoção do ponto final acrescido nas células C13, C14 e C15; nenhum outro arquivo alterado)
- Evidências:
  - **C1 (fidelidade item a item, células C13–C15 da tabela do fonte)** — Conferência textual automatizada (script isolado em `/tmp/opencode/check_005.py`, extração por regex das células da tabela do fonte e dos bullets da especificação da task, comparação após normalização NFC/aspas/travessões/espaços/minúsculas) das células C13 (linha 19), C14 (linha 20) e C15 (linha 21) de `fase2/documentos/02_componentes_e_requisitos.md`: resultado `C13 FIEL`, `C14 FIEL`, `C15 FIEL` após a correção descrita abaixo. Antes da correção, o único desvio era tipográfico: ponto final acrescido ao final de cada célula copiada — no C14, entre a célula e a nota de ambiguidade (o fonte não pontua as células), mesmo desvio corrigido nas tasks 001–004; nenhum termo, critério ou cláusula divergia. Item a item: C13 = LangGraph ✓, rotas fixas ✓, checkpoints ✓, pausa humana ✓, dependências ✓, terminais ✓, ausência de ciclos não limitados ✓, política para divergências ✓, mesmas ferramentas no baseline ✓; C14 = JSON Schema/Pydantic ✓, envelope com task/trace/version ✓, referência em vez de cópia integral ✓, leitura de snapshot ✓, erros tipados ✓, MCP nas fronteiras de ferramentas ✓, A2A somente como extensão de serviços ✓; C15 = allowlist por papel ✓, argumentos validados ✓, tool result como dados ✓, rede opcional ✓, escrita mediada ✓, "JSON correto não basta: validar também intenção e efeito" ✓. Diferenças legítimas mantidas: inicial minúscula em "allowlist" na task (posição na frase, como "artefato" na task 001); capitalização de "LangGraph", "JSON Schema/Pydantic", "MCP" e "A2A" preservada.
  - **C2 (IDs permanentes/estáveis; ambiguidade 5 pendente; sustentação do núcleo desde o início)** — O fonte declara na abertura (linha 3): "Os IDs abaixo são permanentes e ligam pesquisa, arquitetura e testes"; a task referencia os componentes apenas pelos IDs C13/C14/C15 com seus nomes canônicos do fonte ("Orquestração", "Comunicação e contratos", "Política de ferramentas"), sem nome alternativo. A ambiguidade 5 do fonte (linha 38: "A2A não é requisito para comunicação interna: acrescentar serviços remotos ao MVP ampliaria os pontos de falha sem benefício demonstrado.") aparece apenas como nota anexa — "*(Ambiguidade pendente 5: …)*" — sem qualquer proposta de resolução; a nota substitui os dois-pontos do fonte por travessão e os demais termos são idênticos (conferência de cobertura termo a termo no script). A caracterização da camada transversal no Prompt da task ("C13–C17/C20 estão registrados como camada que **sustenta o núcleo desde o início** (não como fase posterior)") coincide com a seção "Dependências e prioridades" do fonte (linha 30: "sustentado desde o início por C13–C17/C20"), que cobre C13–C15 (script confirma presença da caracterização).
  - **C3 (nada acrescido; nada medido)** — Varredura de números na especificação C13–C15 (corpo das células): o único dígito é o "2" do nome próprio "A2A", presente verbatim na célula C14 do fonte (saída do script: `numeros na especificacao C13-C15 (corpo): ['2']`, originado de "A2A"); nenhum valor de qualidade, latência, orçamento ou parâmetro acrescido (respeita C17/questão aberta 4 do plano). Nenhuma frase da task afirma ter medido, executado ou validado qualquer comportamento de orquestração, contratos ou política de ferramentas; a especificação é apresentada como requisito de implementação/avaliação futura.
  - **C4 (fonte intocado; correção mínima)** — `git diff 381e506 -- fase2/documentos/02_componentes_e_requisitos.md`: vazio (0 linhas); `git diff --stat` pós-correção: somente o arquivo desta task, 3 inserções/3 remoções (os três pontos finais). Nenhum documento novo criado.
  - **Verificador do repositório (apoio)** — `python3 fase2/scripts/verificar_documentos.py` a partir da raiz: `status: "passed"`, `components: 20`, `missing_citations: []`, `local_links_checked: 39`, `delivery_pending: []` — confirma a integridade documental da fase 2 (incluindo a tabela C01–C20 do fonte) na base trabalhada. Limitação anotada: o verificador é checagem documental (stdlib only) e não valida experimentalmente nada; não constitui resultado medido. Referência auxiliar consultada sem importar conteúdo: `fase2/documentos/04_mapa_completo_do_sistema.md` (terminologia orquestrador/contratos verificáveis/validação determinística, alinhada às células C13–C15 do fonte).
- Pendências/bloqueios: nenhum. A ambiguidade 5 (A2A fora do MVP) permanece decisão pendente, sem resolução proposta nesta etapa; as demais cinco ambiguidades do fonte seguem pendentes no plano.

## Notas

### Dificuldade esperada
2/10 — Conferência textual de três linhas de tabela; risco baixo.

### Dificuldade sentida
2/10 — Conferência textual de três células de tabela com script de comparação normalizada; a caracterização de sustentação do núcleo exigiu confronto com a seção "Dependências e prioridades" do fonte, mas o desvio encontrado foi apenas o mesmo ponto final tipográfico já corrigido nas tasks 001–004 (aqui em três pontos, incluindo o C14 antes da nota de ambiguidade).

### Revisão
- Orquestrador: GLM-5.3-Flash (sd2/GLM-5.3-Flash, via ~/sd2-llm.sh)
- Alvo: task 005; base `381e506`, entrega `1cf8eab` (correção de fidelidade, só o arquivo da task, 3+/3−), registro `68a771f` (HEAD, árvore limpa conferida antes da rodada). Modo da rodada: **paralelo** — revisão somente leitura, sem recursos compartilhados do sistema; os três revisores rodaram simultaneamente, cada um em sessão nova.
- Avaliações:
  - GLM-5.3-Flash (sd2) — 9,5/10 — aprovada; conferência normalizada independente das células C13–C15; achado A1 (baixo): travessão no lugar dos dois-pontos na nota da ambiguidade 5, divulgado e sem efeito de conteúdo.
  - GPT-6 Luna (openai/gpt-6-luna) — 10/10 — aprovada; sem achados; todos os critérios verificados, diff da entrega limitado aos três pontos finais.
  - MiMo v2.6 Flash (opencode/mimo-v2.6-flash-free) — 9/10 — aprovada; achados A1 (baixo): "allowlist" minúsculo vs "Allowlist" do fonte (posição na frase, convenção aceita em 001–004) e A2 (baixo): dois-pontos→travessão na nota da ambiguidade, ambos tipográficos e documentados.
- Nota final: 9,5/10 — consenso dos três revisores de que C1–C5 estão comprovados com verificação independente (cada revisor rodou sua própria comparação normalizada e o verificador documental, `status: passed`); os únicos achados residuais são adaptações tipográficas conscientes, divulgadas em Evidências e coerentes com o padrão já fechado nas tasks 001–004, sem qualquer efeito sobre requisitos, números ou decisões pendentes.
- Parecer: a especificação C13–C15 reproduz fielmente a tabela do fonte após a remoção dos três pontos finais acrescidos (correção mínima, commit de entrega isolado); IDs permanentes preservados, ambiguidade 5 permanece apenas como decisão pendente, caracterização de sustentação do núcleo desde o início coerente com "Dependências e prioridades" do fonte, documento-fonte intocado e commits de entrega/registro separados e íntegros.
- Decisão: fechar
- Reversão: não se aplica — entrega aprovada, sem reversão.
- Próximo passo: liberar a task 006 (validar persistência, observabilidade e empacotamento — C16, C17 e C20), que depende desta.

<!-- task-cycle: {"decision":"fechar","next_task":".agents/tasks/02-componentes-e-requisitos/006-validar-persistencia-observabilidade-e-empacotamento.md","family":".agents/tasks/02-componentes-e-requisitos/001-validar-fundacao-inferencia-ingestao-ontologia.md","plan":".agents/plans/02-componentes-e-requisitos/plan.md"} -->

Plano: [plan.md](../../plans/02-componentes-e-requisitos/plan.md)
