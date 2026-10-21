# Task 003: Validar especificação de tutor, monitor formativo e estado de aprendizagem — C06, C07 e C08

Estado: fechada
Depende de: 002
Origem: nenhuma

## Prompt
Conferir que a especificação abaixo dos componentes C06–C08 reproduz **fielmente** as características exigidas e os critérios verificáveis de `fase2/documentos/02_componentes_e_requisitos.md` (documento-fonte normativo, que permanece intocado). Registrar em Evidências a conferência item a item. Desvio de fidelidade: corrija apenas o texto desta task em dif mínimo e registre em Evidências.

Especificação a validar (extraída da tabela do documento-fonte):
- **C06 — Tutor e skills:** socrático, explicação e prática graduada; habilidades versionadas para explicar, pistas, quiz, flashcards, autoexplicação; pré/pós-condições; resposta direta quando apropriada; não interrogar indefinidamente
- **C07 — Monitor formativo:** gabarito ou rubrica explícita, evidência de resposta, erros por tópico, incerteza e opção de abster; separar corretude, ajuda recebida e domínio; validação contra anotação humana *(Ambiguidade pendente 2: um único episódio correto não basta para estimar domínio — o monitor precisa dos estados "evidência insuficiente" e "avaliável"; como operacionalizá-los ainda não está definido.)*
- **C08 — Estado de aprendizagem:** modelo atualizável e auditável por tópico, distinção entre observado e inferido; cold-start; revisão temporal; evitar parâmetros cognitivos arbitrários tratados como calibrados

Além da fidelidade, conferir que: os IDs são permanentes/estáveis; nada acrescenta requisito, número ou métrica além do fonte; C06/C07/C08 ocupam a posição correta da cadeia do núcleo (C01 → C02/C03 → C04/C09 → **C06/C07/C08** → C11); a ambiguidade 2 aparece apenas como decisão pendente.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver ambiguidades; não apresentar especificação como resultado medido; prosa em português; commit de registro separado, sem amend/force-push/commits vazios.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e ambiguidades.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; "Abordagem" (cadeia do núcleo) e "Critérios de conclusão".
- `fase2/documentos/04_mapa_completo_do_sistema.md` — apoio para checar alinhamento de terminologia (tutor, monitor, estado), sem importar conteúdo.
- `fase2/documentos/08_mapa_completo_da_testagem.md` — referência de avaliação (validação contra anotação humana em C07), sem importar conteúdo.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [x] C1 — Características e critérios de C06, C07 e C08 correspondem item a item ao documento-fonte; conferência registrada em Evidências.
- [x] C2 — IDs permanentes/estáveis; ambiguidade 2 ("evidência insuficiente"/"avaliável") registrada apenas como decisão pendente, sem proposta de operacionalização nesta etapa.
- [x] C3 — Nenhum requisito, número ou métrica além do fonte; posição de C06–C08 na cadeia do núcleo registrada corretamente; nada apresentado como resultado medido.
- [x] C4 — Documento-fonte intocado (`git diff` vazio para ele em relação à base); correções limitadas ao arquivo desta task em dif mínimo.
- [x] C5 — Commit de registro com evidências separado de qualquer commit de entrega; sem commits vazios, amend ou force-push.

## Execução
- Modelo: GLM-5.3-Flash (provider `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime
- Base: 27aed9e71816a2095d4d9d33e6b0d35ac4b2851b (HEAD, árvore limpa)
- Entrega: e41aa1ae2b3d8ca38c1480db17e0815e58cf8c51 (correção de fidelidade tipográfica no próprio arquivo da task)
- Arquivos da entrega: `.agents/tasks/02-componentes-e-requisitos/003-validar-tutor-monitor-e-estado-de-aprendizagem.md` (3 linhas, remoção do ponto final acrescido nas células C06, C07 e C08; nenhum outro arquivo alterado)
- Evidências:
  - **C1 (fidelidade item a item, células C06–C08 da tabela do fonte)** — Conferência textual automatizada (script isolado em `/tmp/opencode` via heredoc, extração por regex das células da tabela do fonte e dos bullets da especificação da task, comparação após normalização de aspas/travessões e de capitalização inicial) das células C06 (linha 12), C07 (linha 13) e C08 (linha 14) de `fase2/documentos/02_componentes_e_requisitos.md`: resultado `C06 FIEL`, `C07 FIEL`, `C08 FIEL` após a correção descrita abaixo. Antes da correção, o único desvio era tipográfico: ponto final acrescido ao final de cada célula copiada (o fonte não pontua as células), mesmo desvio corrigido nas tasks 001 e 002; nenhum termo, critério ou cláusula divergia. Item a item: C06 = socrático ✓, explicação e prática graduada ✓, habilidades versionadas (explicar, pistas, quiz, flashcards, autoexplicação) ✓, pré/pós-condições ✓, resposta direta quando apropriada ✓, não interrogar indefinidamente ✓; C07 = gabarito ou rubrica explícita ✓, evidência de resposta ✓, erros por tópico ✓, incerteza ✓, opção de abster ✓, separar corretude/ajuda recebida/domínio ✓, validação contra anotação humana ✓; C08 = modelo atualizável e auditável por tópico ✓, distinção observado/inferido ✓, cold-start ✓, revisão temporal ✓, evitar parâmetros cognitivos arbitrários tratados como calibrados ✓. Diferença legítima mantida: inicial minúscula em "socrático/gabarito/modelo" na task (posição na frase); acentos e termos técnicos ("cold-start", "pré/pós-condições") preservados.
  - **C1 (correção aplicada)** — Remoção do ponto final nas três células da especificação (dif de 3 linhas, commit de entrega `e41aa1a`), preservando integralmente o sentido do fonte; nenhuma outra alteração no arquivo da task.
  - **C2 (IDs permanentes/estáveis; ambiguidade 2 como pendente)** — O fonte declara na abertura (linha 3): "Os IDs abaixo são permanentes e ligam pesquisa, arquitetura e testes"; a task referencia os componentes apenas pelos IDs C06/C07/C08 com seus nomes canônicos do fonte ("Tutor e skills", "Monitor formativo", "Estado de aprendizagem"), sem nome alternativo. A ambiguidade 2 do fonte (linha 35: "Um único episódio correto não basta para estimar domínio: o monitor precisa de estados “evidência insuficiente” e “avaliável”.") aparece na task apenas como nota anexada a C07 — "*(Ambiguidade pendente 2: … como operacionalizá-los ainda não está definido.)*" — sem qualquer proposta de operacionalização, enquadramento ou decisão; a formulação reproduz a asserção do fonte e registra a indefinição como pendente (coerente com a questão aberta 2 do plano).
  - **C3 (nada acrescido; posição na cadeia do núcleo; nada medido)** — Varredura de números na especificação C06–C08: nenhum (saída do script: `numeros na especificacao C06-C08: nenhum`); nenhum valor de qualidade, latência, orçamento ou parâmetro acrescido (respeita C17/questão aberta 4 do plano). A cadeia do núcleo citada no Prompt da task ("C01 → C02/C03 → C04/C09 → **C06/C07/C08** → C11", com C06/C07/C08 em negrito na quarta posição) coincide literalmente com a seção "Dependências e prioridades" do fonte (linha 30: "Núcleo implementável: C01 → C02/C03 → C04/C09 → C06/C07/C08 → C11, sustentado desde o início por C13–C17/C20") — script confirma (`cadeia citada na task: True`). Nenhuma frase da task afirma ter medido ou validado qualquer comportamento do tutor, do monitor ou do estado; a especificação é apresentada como requisito de implementação/avaliação futura.
  - **C4 (fonte intocado)** — `git diff 27aed9e -- fase2/documentos/02_componentes_e_requisitos.md` vazio (0 linhas); diff total da entrega limitado ao arquivo desta task (3 linhas); as seis ambiguidades do fonte permanecem decisões pendentes, nenhuma resolvida.
  - **Verificador do repositório (apoio)** — `python3 fase2/scripts/verificar_documentos.py` a partir da raiz: `status: "passed"`, `components: 20`, `missing_citations: []`, `local_links_checked: 39`, `delivery_pending: []` — confirma a integridade documental da fase 2 (incluindo a tabela C01–C20 do fonte) na base trabalhada. Limitação anotada: o verificador é checagem documental (stdlib only) e não valida experimentalmente nada; não constitui resultado medido. Referências auxiliares consultadas sem importar conteúdo: `fase2/documentos/04_mapa_completo_do_sistema.md` e `fase2/documentos/08_mapa_completo_da_testagem.md` (validação contra anotação humana de C07 é critério de avaliação futura, não executada nesta task).
- Pendências/bloqueios: nenhum. A ambiguidade 2 (estados "evidência insuficiente" e "avaliável" do monitor, C07) permanece decisão pendente, sem operacionalização proposta nesta etapa; as demais cinco ambiguidades do fonte seguem pendentes no plano.

## Notas

### Dificuldade esperada
2/10 — Conferência textual de três linhas de tabela; risco baixo.

### Dificuldade sentida
2/10 — Conferência textual direta de três células contra a tabela do próprio documento-fonte, com checagem automatizada por script isolado; a única decisão de julgamento foi classificar o ponto final acrescido como desvio tipográfico de fidelidade (corrigido em dif mínimo, seguindo o precedente das tasks 001 e 002) e não como reescrita legítima, além de manter a nota da ambiguidade 2 estritamente como decisão pendente, sem sugerir operacionalização para os estados "evidência insuficiente" e "avaliável".

### Revisão
- Orquestrador: GLM-5.3-Flash (provider `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime; sessão master do ciclo task-cycle
- Modo da rodada: **paralelo** — a revisão é somente leitura (fontes, diffs git e verificador documental stdlib), sem disputa de recursos compartilhados do sistema; os três revisores rodaram em sessões novas, com o mesmo pedido e sem acesso aos pareceres entre si. Observação: a primeira tentativa da rodada foi interrompida por reinício do servidor, sem pareceres retornados; a rodada foi relançada do zero sobre o mesmo alvo imutável (base/entrega/registro conferidos antes do relançamento).
- Alvo: task 003; base `27aed9e71816a2095d4d9d33e6b0d35ac4b2851b`; entrega `e41aa1ae2b3d8ca38c1480db17e0815e58cf8c51`; registro `fbfe325012bba08be658563db7e4cb3512015946` (HEAD, árvore limpa). Identidade e alvo confirmados pelos três revisores.
- Avaliações:
  - GLM-5.3-Flash (`sd2`) — **10/10** — aprovada; C1–C5 verificados independentemente (leitura direta das células, `git show`/`git log --format='%H %P'`, verificador `passed`). Sessão `ses_ea3a35d14ffeWcyXCmBKr6IYHQ`.
  - GPT-6 Luna (`openai/gpt-6-luna`) — **9/10** — aprovada; C1–C5 verificados por conferência própria, sem falha concreta encontrada. Sessão `ses_ea3a35cdeffeeIGoFqgDLNLg7e`.
  - MiMo 2.6 Flash (`opencode/mimo-v2.6-flash-free`) — **9/10** — aprovada; C1–C5 verificados com script de fidelidade independente reproduzido e reflog linear sem amend/reset. Sessão `ses_ea3a35cacffe06PO8RxWIxY1rI`.
- Síntese: consenso unânime de aprovação, sem achado bloqueante. Achados menores (impacto baixo, sem correção necessária): (i) nota da ambiguidade usa aspas retas onde o fonte usa curvas — diferença tipográfica já normalizada como legítima na própria evidência (apontado pelo revisor GLM); (ii) evidência C4 cita a base por SHA abreviado, cuja forma completa confere com o alvo (apontado pelo revisor GLM); (iii) evidência C3 relata "nenhum número" na especificação, imprecisão literal pois os IDs C06–C08 e o índice da ambiguidade 2 contêm dígitos originários do próprio fonte — nenhum número/métrica/parâmetro *novo* foi acrescido (apontado pelo revisor MiMo). O revisor GLM registrou ainda, como observação de processo, que sua identidade coincide com a do executor; o quórum se sustenta: são três modelos distintos entre si, conforme contrato. Divergência essencial: nenhuma; limitações declaradas (verificador documental ≠ resultado experimental; impossibilidade local de provar ausência de force-push remoto) não afetam os critérios.
- Nota final: **9,5/10** — fidelidade item a item confirmada por três modelos independentes com procedimentos próprios; entrega mínima (dif de 3 linhas) e registro completo. Dedução pela imprecisão literal do relato C3 e detalhes tipográficos menores, sem efeito sobre fidelidade, isolamento ou contratos.
- Decisão: **fechar** — todos os critérios obrigatórios (C1–C5) comprovados; libera a sucessora 004.
- Reversão: não se aplica — entrega aprovada.
- Próximo passo: task `.agents/tasks/02-componentes-e-requisitos/004-validar-planejamento-solver-e-agenda.md` (executor sd2/GLM-5.3-Flash; alternativo não configurado).

<!-- task-cycle: {"decision":"fechar","next_task":".agents/tasks/02-componentes-e-requisitos/004-validar-planejamento-solver-e-agenda.md","family":".agents/tasks/02-componentes-e-requisitos/001-validar-fundacao-inferencia-ingestao-ontologia.md","plan":".agents/plans/02-componentes-e-requisitos/plan.md"} -->

Plano: [plan.md](../../plans/02-componentes-e-requisitos/plan.md)
