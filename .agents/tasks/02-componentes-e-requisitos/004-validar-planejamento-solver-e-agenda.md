# Task 004: Validar especificação de planejamento/solver e agenda — C11 e C12

Estado: fechada
Depende de: 003
Origem: nenhuma

## Prompt
Conferir que a especificação abaixo dos componentes C11 e C12 reproduz **fielmente** as características exigidas e os critérios verificáveis de `fase2/documentos/02_componentes_e_requisitos.md` (documento-fonte normativo, que permanece intocado). Registrar em Evidências a conferência item a item. Desvio de fidelidade: corrija apenas o texto desta task em dif mínimo e registre em Evidências.

Especificação a validar (extraída da tabela do documento-fonte):
- **C11 — Planejamento e solver:** slots, timezone, prazos, disponibilidade, compromissos imutáveis, duração e prioridade; solver verificável; mínimo de alterações no replanejamento; distinguir inviável de timeout *(Ambiguidades pendentes 3 e 4 relacionadas: tempo insuficiente não deve ser resolvido silenciosamente removendo compromissos ou reduzindo duração obrigatória; documento externo mais recente não substitui automaticamente prazo confirmado — reconciliação.)*
- **C12 — Exportação e agenda:** ICS válido, UID estável, timezone, preview e confirmação; integração MCP opcional; idempotência, concorrência, reconciliação após timeout e nenhuma duplicação em retry *(Nota de prioridade do fonte: o ICS local de C12 é obrigatório no núcleo; a sincronização remota de C12 é conector opcional avaliado separadamente — especificada na task 008.)*

Além da fidelidade, conferir que: os IDs são permanentes/estáveis; nada acrescenta requisito, número ou métrica além do fonte; C11 ocupa o fim da cadeia do núcleo (C01 → C02/C03 → C04/C09 → C06/C07/C08 → **C11**); as ambiguidades 3 e 4 aparecem apenas como decisões pendentes.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver ambiguidades; prosa em português; commit de registro separado, sem amend/force-push/commits vazios.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e ambiguidades.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; "Abordagem" (cadeia do núcleo, ICS local obrigatório) e "Critérios de conclusão".
- `fase2/documentos/04_mapa_completo_do_sistema.md` — apoio para checar alinhamento de terminologia (solver, planejador de rotina), sem importar conteúdo.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [x] C1 — Características e critérios de C11 e C12 correspondem item a item ao documento-fonte; conferência registrada em Evidências.
- [x] C2 — IDs permanentes/estáveis; ambiguidades 3 e 4 registradas apenas como decisões pendentes; ICS local marcado como obrigatório no núcleo e sincronização remota de C12 marcada como opcional (remetida à task 008).
- [x] C3 — Nenhum requisito, número ou métrica além do fonte; posição de C11 na cadeia do núcleo registrada corretamente.
- [x] C4 — Documento-fonte intocado (`git diff` vazio para ele em relação à base); correções limitadas ao arquivo desta task em dif mínimo.
- [x] C5 — Commit de registro com evidências separado de qualquer commit de entrega; sem commits vazios, amend ou force-push.

## Execução
- Modelo: GLM-5.3-Flash (via ~/sd2-llm.sh; provider sd2, model GLM-5.3-Flash)
- Base: `cb08a7e48ca839c3e3a93bb001a2f1108b94c1de` (árvore limpa)
- Entrega: `3ef06cab8edf321eb3873eb2a6f52fce3dcd341f` (commit de entrega; commit de registro separado, sem SHA próprio neste arquivo)
- Arquivos da entrega: `.agents/tasks/02-componentes-e-requisitos/004-validar-planejamento-solver-e-agenda.md` (2 linhas, remoção do ponto final acrescido nas células C11 e C12; nenhum outro arquivo alterado)
- Evidências:
  - **C1 (fidelidade item a item, células C11 e C12 da tabela do fonte)** — Conferência textual automatizada (script isolado em `/tmp/opencode/check_004.py`, extração por regex das células da tabela do fonte e dos bullets da especificação da task, comparação após normalização NFC/aspas/travessões/espaços/minúsculas) das células C11 (linha 17) e C12 (linha 18) de `fase2/documentos/02_componentes_e_requisitos.md`: resultado `C11 FIEL`, `C12 FIEL` após a correção descrita abaixo. Antes da correção, o único desvio era tipográfico: ponto final acrescido ao final de cada célula copiada (o fonte não pontua as células), mesmo desvio corrigido nas tasks 001–003; nenhum termo, critério ou cláusula divergia. Item a item: C11 = slots ✓, timezone ✓, prazos ✓, disponibilidade ✓, compromissos imutáveis ✓, duração ✓, prioridade ✓, solver verificável ✓, mínimo de alterações no replanejamento ✓, distinguir inviável de timeout ✓; C12 = ICS válido ✓, UID estável ✓, timezone ✓, preview e confirmação ✓, integração MCP opcional ✓, idempotência ✓, concorrência ✓, reconciliação após timeout ✓, nenhuma duplicação em retry ✓. Diferenças legítimas mantidas: inicial minúscula em "slots" na task (posição na frase); capitalização de "ICS", "UID" e "MCP" preservada.
  - **C2 (IDs permanentes/estáveis; ambiguidades 3 e 4 pendentes; fronteira núcleo/opcional de C12)** — O fonte declara na abertura (linha 3): "Os IDs abaixo são permanentes e ligam pesquisa, arquitetura e testes"; a task referencia os componentes apenas pelos IDs C11/C12 com seus nomes canônicos do fonte ("Planejamento e solver", "Exportação e agenda"), sem nome alternativo. As ambiguidades 3 e 4 do fonte (linhas 36–37: "Tempo insuficiente não deve ser resolvido silenciosamente removendo compromissos ou reduzindo duração obrigatória." / "O documento externo mais recente não deve substituir automaticamente um prazo confirmado; mudanças precisam de reconciliação.") aparecem apenas como notas anexas — "*(Ambiguidades pendentes 3 e 4 relacionadas: …)*" — sem qualquer proposta de resolução, política ou decisão; a formulação condensada reproduz as asserções do fonte e registra a pendência (coerente com a questão aberta 3 do plano). A nota de prioridade reproduz a seção "Dependências e prioridades" do fonte (linha 30): "ICS local de C12 é obrigatório no núcleo" e "a **sincronização remota de C12** [são] conectores opcionais avaliados separadamente"; a remissão "especificada na task 008" coincide com a tabela do plano (task 008: "C05, sinc. remota de C12 + consolidação"), sem antecipar especificação.
  - **C3 (nada acrescido; posição na cadeia do núcleo; nada medido)** — Varredura de números na especificação C11+C12 (corpo das células): nenhum (saída do script: `numeros na especificacao C11+C12 (corpo): nenhum`); nenhum valor de qualidade, latência, orçamento ou parâmetro acrescido (respeita C17/questão aberta 4 do plano). A cadeia do núcleo citada no Prompt da task ("C01 → C02/C03 → C04/C09 → C06/C07/C08 → **C11**", com C11 em negrito na quinta e última posição do núcleo) coincide com a seção "Dependências e prioridades" do fonte (linha 30: "Núcleo implementável: C01 → C02/C03 → C04/C09 → C06/C07/C08 → C11, sustentado desde o início por C13–C17/C20") — script confirma (`cadeia citada na task: True | igual ao fonte: True`). Nenhuma frase da task afirma ter medido, executado ou validado qualquer comportamento do solver ou da exportação; a especificação é apresentada como requisito de implementação/avaliação futura.
  - **C4 (fonte intocado; correção mínima)** — `git diff cb08a7e -- fase2/documentos/02_componentes_e_requisitos.md`: vazio (0 linhas); `git diff --stat` pós-correção: somente o arquivo desta task, 2 inserções/2 remoções (os dois pontos finais). Nenhum documento novo criado.
  - **Verificador do repositório (apoio)** — `python3 fase2/scripts/verificar_documentos.py` a partir da raiz: `status: "passed"`, `components: 20`, `missing_citations: []`, `local_links_checked: 39`, `delivery_pending: []` — confirma a integridade documental da fase 2 (incluindo a tabela C01–C20 do fonte) na base trabalhada. Limitação anotada: o verificador é checagem documental (stdlib only) e não valida experimentalmente nada; não constitui resultado medido. Referência auxiliar consultada sem importar conteúdo: `fase2/documentos/04_mapa_completo_do_sistema.md` (terminologia solver/planejador de rotina, alinhada à célula C11 do fonte).
- Pendências/bloqueios: nenhum. As ambiguidades 3 e 4 (política de reconciliação de prazos ligada a C03/C11/C12; não resolver falta de tempo removendo compromissos silenciosamente) permanecem decisões pendentes, sem resolução proposta nesta etapa; as demais quatro ambiguidades do fonte seguem pendentes no plano.

## Notas

### Dificuldade esperada
2/10 — Conferência textual de duas linhas de tabela; risco baixo, com atenção à fronteira núcleo/opcional de C12.

### Dificuldade sentida
2/10 — Conferência textual de duas células de tabela com script de comparação normalizada; a fronteira núcleo/opcional de C12 exigiu confronto com a seção "Dependências e prioridades" do fonte e com a tabela do plano, mas o desvio encontrado foi apenas o mesmo ponto final tipográfico já corrigido nas tasks 001–003.

### Revisão
- Orquestrador: GLM-5.3-Flash (provider sd2, via ~/sd2-llm.sh) — task-master do ciclo opt-in.
- Alvo: task 004; base `cb08a7e`, entrega `3ef06ca` (correção de fidelidade, 2+/2−, só o arquivo da task), registro `4a07576`; árvore limpa e alvo confirmado antes da rodada; fonte intocado.
- Modo da rodada: paralelo — revisão puramente textual/leitura, sem disputa de recursos compartilhados do sistema; três revisores de modelos distintos, sem falhas nem substituições (pool do ciclo fixado conforme restrição do usuário).
- Avaliações:
  - GLM-5.3-Flash (sd2) — 9/10, aprovada; replicou a comparação de fidelidade de forma independente (`C11 fiel: True`, `C12 fiel: True`), confirmou cadeia do núcleo, ausência de métricas acrescidas, commits separados e fonte intocado. Observação menor (informativa, sem ação): script de conferência do executor em `/tmp/opencode/` não versionado, reduz rastreabilidade sem impactar corretude — contornado pela replicação independente do revisor.
  - GPT-6 Luna (openai) — 9/10, aprovada; verificou diretamente fidelidade contra linhas 17–18 e 30 do fonte, ambiguidades 3 e 4 como pendências, fronteira núcleo/opcional de C12, diff do fonte vazio e commits distintos de entrega/registro. Sem achados.
  - MiMo v2.6 Flash (opencode) — 9,5/10, aprovada; reproduziu a conferência programática com normalização própria (`C11 igual_ci: True`, `C12 igual_ci: True`), confirmou ancestralidade direta dos commits via `git log --format='%H %P'` e ausência de docs novos. Duas observações informativas sem exigência de correção (condensação semântica preservada da ambiguidade 4; cadeia citada omite o suporte "C13–C17/C20" por delimitar explicitamente "cadeia do núcleo", forma igual à do plano).
- Nota final: 9/10 — consenso dos três pareceres sem achado bloqueante; a nota reflete fidelidade plena confirmada independentemente por dois revisores, com desconto único pela não-versionação do script de conferência do executor (rastreabilidade marginal, sem impacto na corretude dos critérios C1–C5).
- Parecer: todos os critérios obrigatórios (C1–C5) verificados e comprovados; divergências nulas entre revisores; nenhuma pendência essencial. As ambiguidades 3 e 4 permanecem apenas como decisões pendentes, conforme restrição.
- Decisão: fechar
- Reversão: não se aplica — sem artefatos a desfazer (correção de fidelidade aprovada; nenhum commit de implementação).
- Próximo passo: avançar para a task 005 (`.agents/tasks/02-componentes-e-requisitos/005-validar-orquestracao-contratos-e-politica-de-ferramentas.md` — C13, C14, C15), única pendente elegível da família.

<!-- task-cycle: {"decision":"fechar","next_task":".agents/tasks/02-componentes-e-requisitos/005-validar-orquestracao-contratos-e-politica-de-ferramentas.md","family":".agents/tasks/02-componentes-e-requisitos/001-validar-fundacao-inferencia-ingestao-ontologia.md","plan":".agents/plans/02-componentes-e-requisitos/plan.md"} -->

Plano: [plan.md](../../plans/02-componentes-e-requisitos/plan.md)
