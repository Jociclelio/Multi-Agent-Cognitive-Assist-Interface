# Task 006: Validar decisões de método — agenda e orquestração (C12 e C13/C14)

Estado: pendente
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
- [ ] C1 — As decisões de método para C12 e C13/C14 nesta task correspondem item a item às linhas 24 e 25 do fonte (método selecionado, referências/chaves e limite de cada linha); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task.
- [ ] C2 — Nada acrescido além do fonte; ICS local permanece núcleo e a extensão remota permanece opcional/feature flag; a ambiguidade 5 (A2A) e a pendência de reconciliação de prazos permanecem abertas; IDs permanentes; nada apresentado como resultado medido.
- [ ] C3 — O documento-fonte permanece intocado (`git diff` vazio em relação à base); correções limitadas ao arquivo desta task em dif mínimo; commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo não tocado.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
2/10 — Conferência textual de duas linhas de tabela; cuidado em manter as fronteiras núcleo/opcional de C12 e A2A fora do MVP.

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

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
