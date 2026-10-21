# Task 006: Validar decisões de método — agenda e orquestração (C12 e C13/C14)

Estado: aguardando revisão
Depende de: 005
Origem: nenhuma

## Prompt
Conferir que as duas decisões abaixo reproduzem **fielmente** as linhas C12 e C13/C14 da tabela "Decisões reconciliadas" de `fase2/documentos/03_metodologias_de_implementacao.md` (documento-fonte normativo, que permanece intocado; linhas 24 e 25). Registrar em Evidências a conferência item a item de cada linha (método selecionado, referências/chaves, por quê e limite). Se encontrar desvio de fidelidade, corrija **apenas o texto desta task** em dif mínimo, preservando o sentido do fonte, e registre a correção em Evidências.

Decisões a validar (extraídas da tabela do documento-fonte):
- **C12 — Agenda:** ICS UTC, UID persistente; conector remoto com outbox/reconciliação *(referências/chaves: `desruisseaux2009icalendar`, `daboo2007caldav`, `google2026calendarcreate`)* *(por quê e limite: offline fecha o núcleo; UID não garante deduplicação em todo importador manual)*
- **C13/C14 — Orquestração e política de ferramentas:** LangGraph, snapshots, Pydantic/JSON Schema, MCP nas fronteiras *(referências/chaves: `hong2024metagpt`, `lgstate`, `lginterrupt`, `mcparch`, `pydstrict`)* *(por quê e limite: roteamento explícito, pausa e retomada; A2A não é dependência interna)*

Além da fidelidade, conferir que: os IDs C12, C13 e C14 são tratados como permanentes; nada acrescenta requisito, número ou métrica não presente no fonte; a fronteira da etapa 2 permanece coerente (ICS local de C12 obrigatório no núcleo; sincronização remota de C12 e C05 são opcionais avaliados separadamente) e a extensão de agenda remota permanece atrás de feature flag conforme o plano; a ambiguidade 5 da etapa 2 (A2A fora do MVP) permanece pendente e coerente com "A2A não é dependência interna"; a ambiguidade de reconciliação de prazos ligada a C12 permanece pendente.

Restrições: não alterar o documento-fonte nem criar documento novo; não reclassificar opcionais nem resolver ambiguidades; nada apresentado como resultado medido; IDs C01–C20 permanentes; prosa em português; commit de entrega (correção de fidelidade, se houver) e commit de registro separados, sem amend/force-push/commits vazios; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/03_metodologias_de_implementacao.md` — documento-fonte: tabela "Decisões reconciliadas", linhas C12 (linha 24) e C13/C14 (linha 25).
- `fase2/pesquisa/03b_pedagogia_memoria_planejamento.md` (C06–C12) e `fase2/pesquisa/03a_arquitetura_rag.md` (C13–C17, C20) — relatórios integrais das frentes, referência de embasamento, sem reabrir alternativas.
- `.agents/tasks/02-componentes-e-requisitos/004-validar-planejamento-solver-e-agenda.md`, `005-validar-orquestracao-contratos-e-politica-de-ferramentas.md` e `008-validar-opcionais-e-consolidar-cobertura-c01-c20.md` — etapa 2: características de C12/C13/C14 e o caráter opcional da sincronização remota de C12.
- `.agents/plans/03-metodologias-de-implementacao/plan.md` — plano aprovado.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [x] C1 — As decisões de método para C12 e C13/C14 nesta task correspondem item a item às linhas 24 e 25 do fonte (método selecionado, referências/chaves e limite de cada linha); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task.
- [x] C2 — Nada acrescido além do fonte; ICS local permanece núcleo e a extensão remota permanece opcional/feature flag; a ambiguidade 5 (A2A) e a pendência de reconciliação de prazos permanecem abertas; IDs permanentes; nada apresentado como resultado medido.
- [x] C3 — O documento-fonte permanece intocado (`git diff` vazio em relação à base); correções limitadas ao arquivo desta task em dif mínimo; commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo não tocado.

## Execução
- Modelo: sd2/GLM-5.3-Flash
- Base: `775054cdb5497bcf50d2c2609ef464aadc094552`
- Entrega: sem alteração de artefatos — conferência textual não encontrou desvio de fidelidade; nenhuma correção no arquivo desta task foi necessária, portanto não há commit de entrega (apenas o commit de registro).
- Arquivos da entrega: nenhum (registro somente neste `.md`).
- Evidências:
  - **C12 (linha 24 do fonte)** — conferência item a item: método selecionado "ICS UTC, UID persistente; conector remoto com outbox/reconciliação" idêntico ao texto da task; referências/chaves `desruisseaux2009icalendar`, `daboo2007caldav` e `google2026calendarcreate` idênticas e presentes em `fase2/references.bib` (uma ocorrência cada); "por quê e limite" "Offline fecha o núcleo; UID não garante deduplicação em todo importador manual" reproduzido sem alteração.
  - **C13/C14 (linha 25 do fonte)** — conferência item a item: método selecionado "LangGraph, snapshots, Pydantic/JSON Schema, MCP nas fronteiras" idêntico ao texto da task; referências/chaves `hong2024metagpt`, `lgstate`, `lginterrupt`, `mcparch` e `pydstrict` idênticas e presentes em `fase2/references.bib` (uma ocorrência cada); "por quê e limite" "Roteamento explícito, pausa e retomada; A2A não é dependência interna" reproduzido sem alteração.
  - **Conferência automatizada** — script isolado em `/tmp/opencode/check_006.py` (extração das células das linhas 24 e 25 do fonte e dos bullets da task, comparação após normalização NFC/aspas/travessões/espaços/minúsculas): resultado `C12 FIEL`, `C13/C14 FIEL`; as 8 chaves de referência conferidas verbatim; nenhum termo, critério ou cláusula divergente; nenhuma correção necessária.
  - **IDs e escopo**: C12, C13 e C14 tratados como IDs permanentes do conjunto C01–C20; varredura de números no corpo dos bullets fora das chaves de referência retorna apenas os dígitos dos próprios identificadores ("C12", "C13", "C14", "A2A"); nenhum requisito, número ou métrica acrescido além do fonte; nada apresentado como resultado medido; nenhuma alternativa do fonte selecionada ou fechada.
  - **Fronteiras da etapa 2 preservadas**: a task registra explicitamente ICS local de C12 como obrigatório no núcleo e sincronização remota de C12 e C05 como opcionais avaliados separadamente, coerente com a etapa 2 (task `008-validar-opcionais-e-consolidar-cobertura-c01-c20.md`); a extensão de agenda remota permanece atrás de feature flag conforme o plano e o fonte (linha 38); a ambiguidade 5 da etapa 2 (A2A fora do MVP, registrada na task `005-validar-orquestracao-contratos-e-politica-de-ferramentas.md`) permanece pendente e coerente com o limite "A2A não é dependência interna" da linha C13/C14; a ambiguidade de reconciliação de prazos ligada a C12 permanece pendente conforme a task `004-validar-planejamento-solver-e-agenda.md` (ambiguidade 4 do fonte).
  - **Documento-fonte intocado**: `git diff -- fase2/documentos/03_metodologias_de_implementacao.md` vazio em relação à base `775054c`; `git status --porcelain fase2/` vazio; submódulo `docs/playground-llmagenticsystem` não tocado; nenhum documento novo criado. Verificador de documentos (`python3 fase2/scripts/verificar_documentos.py`): `status: passed` (os 24 "failures" são contagem de categorias monitoradas, não falhas de verificação; estado pré-existente, sem alteração nesta task).
- Pendências/bloqueios: nenhum bloqueio. Pendências herdadas, apenas registradas e não resolvidas aqui: ambiguidade 5 da etapa 2 (A2A fora do MVP) e ambiguidade de reconciliação de prazos ligada a C12; feature flag da agenda remota segue condicionada à documentação específica e aos ensaios de concorrência.

## Notas

### Dificuldade esperada
2/10 — Conferência textual de duas linhas de tabela; cuidado em manter as fronteiras núcleo/opcional de C12 e A2A fora do MVP.

### Dificuldade sentida
1/10 — Conferência textual de duas linhas de tabela já cobertas por tarefas análogas (001–005); nenhuma correção foi necessária e as fronteiras núcleo/opcional de C12 e A2A fora do MVP estavam coerentes no texto da task.

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
