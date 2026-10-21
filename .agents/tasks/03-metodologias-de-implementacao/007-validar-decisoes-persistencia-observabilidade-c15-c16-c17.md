# Task 007: Validar decisões de método — persistência e observabilidade (C15/C16 e C17)

Estado: fechada
Depende de: 006
Origem: nenhuma

## Prompt
Conferir que as duas decisões abaixo reproduzem **fielmente** as linhas C15/C16 e C17 da tabela "Decisões reconciliadas" de `fase2/documentos/03_metodologias_de_implementacao.md` (documento-fonte normativo, que permanece intocado; linhas 26 e 27). Registrar em Evidências a conferência item a item de cada linha (método selecionado, referências/chaves, por quê e limite). Se encontrar desvio de fidelidade, corrija **apenas o texto desta task** em dif mínimo, preservando o sentido do fonte, e registre a correção em Evidências.

Decisões a validar (extraídas da tabela do documento-fonte):
- **C15/C16 — Política de ferramentas e persistência:** autorização por código, escritor único, SQLite/WAL, idempotência e outbox *(referências/chaves: `mcpsec`, `sqlitewal`, `lginterrupt`)* *(por quê e limite: checkpoint não é commit de domínio; timeout externo requer reconciliação)*
- **C17 — Observabilidade:** traces locais, métricas e limites ativos *(referências/chaves: `oteltrace`, `llamasrv`)* *(por quê e limite: identifica custo e loops; traces não são provas de correção)*

Além da fidelidade, conferir que: os IDs C15, C16 e C17 são tratados como permanentes; nada acrescenta requisito, número ou métrica não presente no fonte — em particular, nenhum orçamento de C17 é inventado aqui (os limites ativos são mencionados como método, não como valores; os números da etapa 4 cabem à task 009 desta família); a fronteira da etapa 2 (checkpoint ≠ commit de domínio; traces ≠ prova de correção) permanece coerente.

Restrições: não alterar o documento-fonte nem criar documento novo; não definir orçamentos ou parâmetros de C17; nada apresentado como resultado medido; IDs C01–C20 permanentes; prosa em português; commit de entrega (correção de fidelidade, se houver) e commit de registro separados, sem amend/force-push/commits vazios; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/03_metodologias_de_implementacao.md` — documento-fonte: tabela "Decisões reconciliadas", linhas C15/C16 (linha 26) e C17 (linha 27).
- `fase2/pesquisa/03a_arquitetura_rag.md` — relatório integral da frente de arquitetura (C13–C17, C20), referência de embasamento, sem reabrir alternativas.
- `.agents/tasks/02-componentes-e-requisitos/005-validar-orquestracao-contratos-e-politica-de-ferramentas.md` e `006-validar-persistencia-observabilidade-e-empacotamento.md` — etapa 2: características de C15, C16 e C17 (incluindo a ambiguidade de orçamentos, pendente).
- `.agents/plans/03-metodologias-de-implementacao/plan.md` — plano aprovado.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [x] C1 — As decisões de método para C15/C16 e C17 nesta task correspondem item a item às linhas 26 e 27 do fonte (método selecionado, referências/chaves e limite de cada linha); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task. *(Sem desvio de fidelidade: nenhuma correção foi necessária.)*
- [x] C2 — Nada acrescido além do fonte; nenhum orçamento/parâmetro de C17 definido nesta task (números da etapa 4 cabem à task 009); IDs permanentes; nada apresentado como resultado medido.
- [x] C3 — O documento-fonte permanece intocado (`git diff` vazio em relação à base); correções limitadas ao arquivo desta task em dif mínimo; commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo não tocado.

## Execução
- Modelo: GLM-5.3-Flash (via `~/sd2-llm.sh`; provider `sd2`, model ID `GLM-5.3-Flash`)
- Base: `cf6c5982f5565739decf6017fc9ab6cfd159c03b`
- Entrega: sem alteração de artefatos — conferência de fidelidade confirmou correspondência integral; não houve commit de entrega.
- Arquivos da entrega: — (apenas este arquivo de task no commit de registro)
- Evidências:
  - Conferência item a item contra `fase2/documentos/03_metodologias_de_implementacao.md`, linhas 26 e 27 (lidas direto do fonte, intocado):
    - **C15/C16 (linha 26 do fonte):** método "Autorização por código, escritor único, SQLite/WAL, idempotência e outbox" = task linha 11 "autorização por código, escritor único, SQLite/WAL, idempotência e outbox" ✓; chaves `mcpsec`, `sqlitewal`, `lginterrupt` = task ✓; por quê e limite "Checkpoint não é commit de domínio; timeout externo requer reconciliação" = task "checkpoint não é commit de domínio; timeout externo requer reconciliação" ✓.
    - **C17 (linha 27 do fonte):** método "Traces locais, métricas e limites ativos" = task linha 12 "traces locais, métricas e limites ativos" ✓; chaves `oteltrace`, `llamasrv` = task ✓; por quê e limite "Identifica custo e loops; traces não são provas de correção" = task "identifica custo e loops; traces não são provas de correção" ✓.
    - Únicas diferenças: caixa da letra inicial ("Autorização"→"autorização", "Traces"→"traces", "Checkpoint"→"checkpoint", "Identifica"→"identifica"), ajuste tipográfico decorrente da inserção no fluxo da frase, sem alteração de sentido — não configuram desvio de fidelidade, portanto nenhuma correção foi aplicada.
  - IDs C15, C16 e C17 tratados como permanentes (rótulos da tabela fonte); limite ativo de C17 citado apenas como método, sem qualquer número de orçamento nesta task; nada apresentado como resultado medido.
  - `git diff cf6c598 -- fase2/documentos/03_metodologias_de_implementacao.md`: vazio — documento-fonte intocado; submódulo `docs/playground-llmagenticsystem` não tocado.
  - `python3 fase2/scripts/verificar_documentos.py`: `status: passed` (escopo: documentação; não experimentos do sistema).
- Dificuldade sentida: registrada abaixo.

## Notas

### Dificuldade esperada
2/10 — Conferência textual de duas linhas de tabela; cuidado em não citar números de orçamento aqui (pertencem à task 009).

### Dificuldade sentida
1/10 — Conferência textual direta de duas linhas de tabela contra o texto já extraído na task; correspondência integral, sem necessidade de correção. Único cuidado: distinguir ajuste de caixa tipográfica de desvio de fidelidade e não tocar nos números da etapa 4 (task 009).

### Revisão
- Orquestrador: GLM-5.3-Flash (via `~/sd2-llm.sh`; provider `sd2`, model ID `GLM-5.3-Flash`) — master do ciclo opt-in.
- Alvo: task `.agents/tasks/03-metodologias-de-implementacao/007-validar-decisoes-persistencia-observabilidade-c15-c16-c17.md`; base `cf6c5982f5565739decf6017fc9ab6cfd159c03b`; commit de entrega: nenhum (fidelidade confirmada, sem correção); commit de registro `e0f5c41f0f794099051f3ed343710b2393a7eed0` (única alteração: o arquivo desta task).
- Modo da rodada: paralelo — conferência textual somente leitura, sem recursos compartilhados do sistema; três revisores em sessões novas, sem acesso aos pareceres entre si.
- Avaliações:
  - `sd2/GLM-5.3-Flash` (ses_ea17f05bcffei35K4B9Togqk0L) — **10/10**; C1, C2 e C3 verificados; nenhum achado.
  - `openai/gpt-6-luna` (ses_ea17f057fffeINXJWOSbwRkjYG) — **10/10**; C1, C2 e C3 verificados por cotejo direto com as linhas 26–27 do fonte e por `git diff`; nenhum achado.
  - `opencode/mimo-v2.6-flash-free` (ses_ea17f0548ffepV6sB6DW31vpPJ) — **9/10**; C1, C2 e C3 verificados com comparação programática; único achado F1 (impacto baixo, informativo): as Evidências citam apenas diferenças de caixa, não mencionando os rótulos descritivos "C15/C16 — Política de ferramentas e persistência" e "C17 — Observabilidade"; o revisor confirmou que esses rótulos já existiam na base `cf6c598` (o diff de registro não tocou as linhas 10–16) e derivam da nomenclatura da etapa 2 — sem impacto na fidelidade e sem correção obrigatória.
- Nota final: **10/10** — os três revisores confirmaram independente e integralmente a fidelidade item a item das linhas 26 e 27 do fonte (método, chaves e por quê/limite de C15/C16 e C17), a ausência de qualquer orçamento/parâmetro de C17 nesta task (cabem à task 009), a preservação dos IDs permanentes e a higiene de commits (fonte e submódulo intocados, commit de registro único e não vazio). O único ponto residual (F1 do MiMo) é informativo, pré-existente à execução e não afeta critério algum; a nota não o oculta, mas não o justifica rebaixar a entrega, que atende todos os critérios obrigatórios.
- Parecer: entrega de validação cumprida com fidelidade integral e escopo respeitado; pendências do plano permanecem apenas registradas (ambiguidade de orçamentos de C17 segue para a task 009).
- Decisão: **fechar**.
- Reversão: não se aplica — sem artefatos a desfazer.
- Próximo passo: liberar a task 008 (`008-validar-dependencia-externa-avaliacao-c18-c19.md`), que depende desta.

<!-- task-cycle: {"decision":"fechar","next_task":".agents/tasks/03-metodologias-de-implementacao/008-validar-dependencia-externa-avaliacao-c18-c19.md","family":".agents/tasks/03-metodologias-de-implementacao/002-validar-decisao-ingestao-ontologia-c02-c03.md","plan":".agents/plans/03-metodologias-de-implementacao/plan.md"} -->

Plano: [plan.md](../../plans/03-metodologias-de-implementacao/plan.md)
