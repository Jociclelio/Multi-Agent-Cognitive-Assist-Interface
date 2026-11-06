# Plano: Interface Gráfica Local do EduAgent-OS v0.1

Estado: concluído

## Objetivo

Projetar, implementar e testar de ponta a ponta a **interface gráfica local (Web UI loopback)** do EduAgent-OS v0.1 sobre o núcleo multiagente existente (`eduagent/`), unificando o fluxo conversacional por disciplina/sessão (inspirado no layout de três colunas do WhatsApp Web) com os artefatos estruturados, portas *fail-closed* e contratos tipados dos cinco agentes (**Curador**, **Bibliotecário**, **Tutor**, **Monitor** e **Planejador**), acompanhada de uma suíte completa de testes automatizados de backend, frontend e integração E2E.

## Fontes de verdade

- `fase2/documentos/04_mapa_completo_do_sistema.md` — contrato normativo da arquitetura, grafo LangGraph, armazenamento SQLite/WAL, ingestão, retrieval híbrido, tutoria socrática/Feynman, avaliação rubricada, planejamento de calendário, CLI/API loopback (§12) e congelamento (§16).
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — fluxos operacionais `W01–W12`, saídas `O01–O18` e modos de falha `F01–F24`.
- `fase2/documentos/08_mapa_completo_da_testagem.md` — invariantes de verificação e separação estrita entre validação funcional/estrutural e avaliação experimental.
- `eduagent/api.py`, `eduagent/cli.py`, `eduagent/runtime.py`, `eduagent/graph.py` e `eduagent/storage/migrations.py` — implementação real da API HTTP loopback (`127.0.0.1`), CLI, `RuntimeContext` e tabelas SQLite.
- `schemas/*.schema.json` — 15 contratos JSON Schema Draft 2020-12 congelados na task 001 do plano 04.
- `RELATORIO_ESTADO_E_PROXIMOS_PASSOS.md` — diagnóstico consolidado do estado atual e roteiro das Fases A–E.

## Esboço visual

Arquivo: `.agents/plans/interface-grafica-local/esboco-interface.svg`

O esboço mostra a janela desktop local dividida em **4 zonas coordenadas** (3 colunas principais sempre visíveis + 1 gaveta de evidências retrátil):

1. **Trilho Global Esquerdo (`64px`)**: navegação rápida entre os modos do sistema:
   - `Disciplinas / Chat` (visão principal de estudo e tutoria);
   - `Calendário & Demandas` (blocos planejados, demandas, conflitos, diff e exportação `.ics`);
   - `Biblioteca & Ingestão` (documentos por curso, status de indexação/versão ativa, upload confinado e citações);
   - `Revisão & Flashcards` (itens vencidos de repetição espaçada, frente/verso sob demanda sem gamificação);
   - `Progresso & Domínio` (`TopicState` qualitativo `insufficient | mixed | favorable`, erros críticos e tópicos negligenciados);
   - `Fila de Aprovações / Operações` (badge numérico de interrupções `waiting_approval`, fatos ambíguos e planos pendentes);
   - `Diagnóstico / Configurações` (`doctor`, admissão do modelo Bonsai 2, fuso horário, conectores, backup/restore/delete).
2. **Coluna de Disciplinas e Sessões (`320px`, estilo lista de conversas do WhatsApp Web)**:
   - Busca global/filtro (`Ctrl+K`) por disciplina, tópico, sessão ou trecho citado;
   - Botão `+ Nova Disciplina / Ingerir Material`;
   - Chips de filtro: `Todas`, `Prontas p/ Estudar`, `Na Agenda Hoje`, `Aprovação Pendente`;
   - Cards de disciplinas ordenados deterministicamente por prioridade pedagógica (4 níveis) com sinal verde **"Pronta para estudar"** quando há versão documental ativa ou item/revisão pendente.
3. **Painel Central da Disciplina / Sessão de Estudo (`flex: 1`)**:
   - **Cabeçalho da Disciplina**: título, código, estado de domínio qualitativo (`insufficient` / `mixed` / `favorable`), versão ativa do corpus, seletor de modo (`Perguntar (/ask)`, `Praticar (/practice)`, `Submeter (/submit)`, `Revisar`) e **Timer Pomodoro sincronizado** ao `PlanBlock` ativo (ou `25:00 / 05:00` em estudo livre);
   - **Timeline Conversacional e de Artefatos**: mensagens do estudante, respostas do Tutor com escada de ajuda `L0 -> L1 -> L2 -> L3` e badges clicáveis de `SourceRef`, cards interativos de `LearningItem` (sem jamais vazar `answer_ref` antes de `revealed=true`), cards de `Assessment` + `TopicState` pós-submissão e cards de gate/aprovação (`Confirmation` para plano/deleção/fato ambíguo) e de erro tipado (`TypedError`);
   - **Composer Inferior Contextual**: seletor de intenção explícita (`/ask`, `/practice`, `/submit`, `/ingest`, `/plan`), anexo de arquivo e botão `Cancelar Turno` (`POST /turns/{id}/cancel`).
4. **Gaveta Direita de Evidências, Plano e Invariantes (`340px`, retrátil)**:
   - `EvidencePack` do turno selecionado (`coverage`, chunks citados, `SourceRef` com `doc_id`, `version_id`, página e bbox);
   - Checklist de rubrica (somente critérios públicos antes da revelação) e `TopicState` qualitativo (`estimate = null`);
   - Proposta de agenda (`ScheduleProposal`), `PlanDiff` e botão `Exportar .ics`.

## Decisões arquiteturais aprovadas (D1 a D8)

| # | Decisão | Escolha Aprovada | Justificativa Técnica |
|---|---|---|---|
| **D1** | Stack de Frontend | **TypeScript + HTML5 Semântico + CSS Grid Nativo (`ui/src/*.ts` $\rightarrow$ `ui/dist/`)** | Zero dependências externas pesadas, tipagem estrita 1:1 com os 15 JSON Schemas, execução instantânea de testes via `deno test` em sandbox offline e entrega direta pelo servidor Python loopback. |
| **D2** | Versionamento da API | **Estender `eduagent/api.py` *in-place* sem prefixo `/v1`** | Preserva 100% de compatibilidade com `fase2/documentos/04_mapa_completo_do_sistema.md` (§12) e com `tests/test_task015_cli_api.py` (`TestAPILoopback`). |
| **D3** | Ordenação da Lista de Disciplinas | **Ordenação determinística em 4 faixas no backend (`GET /courses`)** | `(1)` bloco planejado ativo/próximo (`logical_blocks`), `(2)` demanda crítica/alta vencendo (`demands`), `(3)` material recém-indexado não praticado (`doc_versions` vs `attempts`), `(4)` dias de inatividade (`events.occurred_at`). Retorna `sort_tier`, `sort_reason_label`, `ready_to_study` e `recommended_intent`. |
| **D4** | Sinal "Pronta para Estudar" | **Derivado em tempo real no `GET /courses` (sem alterar DDL SQLite)** | Mantém `eduagent/storage/migrations.py` intacto; calcula prontidão a partir de `documents.active_version`, `demands` abertas e `items` disponíveis. |
| **D5** | Timer Pomodoro e `update_activity` | **Sincronizado ao `PlanBlock` (fallback 25/5 min) + Persistência `localStorage` + *Fail-Closed*** | Ao chegar a `00:00`, abre `<dialog>` modal nativo perguntando ao estudante se concluiu o bloco, se precisa de mais tempo ou se deseja pausar. Nunca dispara `update_activity` (`completed`) sem clique explícito. |
| **D6** | Hospedagem e Comando de Inicialização | **`LoopbackAPI` serve `ui/dist/` em `GET /` e `/ui/*` + flag `--serve-ui` / `python -m eduagent.api`** | Único processo em `127.0.0.1` (zero problemas de CORS), preservando intocado o conjunto exato dos 14 subcomandos normativos da CLI (`TestParser.test_quatorze_comandos_do_mapa`). |
| **D7** | Upload de Arquivos (`POST /library/upload`) | **Estágio confinado em `data/<user_id>/originals/` via `resolve_owned_path` + limite de 50 MiB** | Recebe nome do arquivo e conteúdo em base64/bytes, valida tamanho $\le 50\text{ MiB}$ (`ErrorCode.RESOURCE_LIMIT`) e confinamento de path antes de acionar `/ingest`. |
| **D8** | Concorrência do Servidor Loopback | **`ThreadingHTTPServer` em `eduagent/api.py`** | Permite que `POST /turns/{id}/cancel` e `GET /health` respondam imediatamente enquanto um turno longo está em execução, com acesso ao SQLite serializado pelo `RLock` de `DomainStore`. |

## Contratos de API Loopback (`127.0.0.1`)

### Endpoints Existentes Preservados (§12)
- `GET /health` — retorna `status: "ok"`, `service: "eduagent-loopback"`, `mode` e objeto estendido `gates` (`model_admitted`, `timezone`, `network_enabled`, `web_connector`, `calendar_sync_enabled`, `reranker_enabled`, `sqlite_version`, `domain_revision`).
- `POST /turns` — executa turno contra `EduAgentGraph.run_turn` (exige `X-EduAgent-User`).
- `POST /turns/{session_id}/resume` — retoma gate com payload de confirmação (exige `X-EduAgent-User`).
- `POST /turns/{session_id}/cancel` — cancela turno ativo e grava evento de cancelamento (exige `X-EduAgent-User`).
- `GET /artifacts/{artifact_id}` — retorna artefato `.ics` confinado a `data/<user_id>/exports/` (exige `X-EduAgent-User`).

### Novos Endpoints de Leitura e Staging para a UI (Todos exigem `X-EduAgent-User`)
- `GET /courses` — lista disciplinas do usuário ordenadas pelas 4 faixas determinísticas, incluindo tópicos, `active_doc_count`, `ready_to_study`, `sort_tier`, `sort_reason_label`, `recommended_intent`, `last_turn_preview`, `last_activity_at`, `pending_demands_count`, `active_plan_block` e resumo de `topic_states`.
- `POST /courses` — cria ou atualiza disciplina (`title`, `course_id` opcional, `topics` opcionais) de forma idempotente no `DomainStore`.
- `GET /courses/{course_id}/sessions` — lista sessões associadas à disciplina com contagem de eventos, último status e timestamp.
- `GET /sessions/{session_id}` — reconstrói a timeline da sessão (`events`, `EvidencePack` mais recente, itens praticados sem vazar `answer_ref` quando `revealed=false`, `assessments` e estado de interrupção no checkpointer).
- `GET /operations` — lista operações pendentes (`operations`), fatos `candidate`/`ambiguous` aguardando confirmação, planos sem `approval_ref` e sessões pausadas em gate (`pending_count`).
- `GET /calendar` — retorna demandas (`demands`), proposta de plano mais recente (`plans`), blocos lógicos (`logical_blocks`), conflitos e artefatos `.ics` disponíveis em `exports/`.
- `GET /progress` — retorna `topic_states` por disciplina e tópico (`status: insufficient | mixed | favorable`, `estimate: null`, contagens de tentativas independentes vs. assistidas, erros críticos recorrentes e tópicos negligenciados).
- `GET /library` — retorna documentos (`documents`), versões (`doc_versions` com estágios de pipeline), blocos/chunks indexados, fatos (`facts`) e itens (`items`) com `SourceRef`.
- `POST /library/upload` — grava arquivo enviado pela UI dentro de `data/<user_id>/originals/<filename>` usando `resolve_owned_path` e limite de 50 MiB, podendo opcionalmente disparar a ingestão na sequência.
- `GET /review/flashcards` — retorna itens e cartões de revisão devidos para estudo espaçado com separação estrita frente/verso e sem métricas punitivas/streaks.
- `GET /search?q=<termo>` — busca unificada para o modal `Ctrl+K` em disciplinas, tópicos, eventos de sessão, fatos confirmados e chunks indexados.
- `GET /` e `GET /ui/*` — serve os ativos estáticos de `ui/dist/` (`index.html`, `styles.css`, `app.js`).

## Plano de Testes Automatizados da Interface Gráfica Local

Para garantir que nenhuma funcionalidade ou invariante *fail-closed* regrida, a verificação automatizada da Interface Gráfica Local é dividida em **3 camadas complementares**:

### Camada 1 — Testes Automatizados de Backend e Contratos HTTP (`tests/test_interface_grafica_local.py`)
Executados sobre `LoopbackAPI` real (`ThreadingHTTPServer` em porta efêmera `127.0.0.1:0`) com `DomainStore` real:
1. **`UI-API-01` (`GET /health` e Gates de Runtime)**: verifica presença de `status == "ok"` e do dicionário `gates` (`model_admitted`, `timezone`, `network_enabled`, `web_connector`, `domain_revision`).
2. **`UI-API-02` (Isolamento de Usuário `X-EduAgent-User`)**: verifica que todos os novos endpoints (`/courses`, `/sessions/{id}`, `/operations`, `/calendar`, `/progress`, `/library`, `/review/flashcards`, `/search`) recusam requisições sem `X-EduAgent-User` com HTTP 400 (`INVALID_INPUT`) e isolam dados entre usuários distintos.
3. **`UI-API-03` (Ordenação Determinística em 4 Faixas em `GET /courses`)**: cria disciplinas em cada uma das 4 condições (bloco ativo na agenda, demanda crítica vencendo, documento recém-indexado sem tentativa, inatividade) e verifica que `GET /courses` retorna a ordem exata `tier 1 -> tier 2 -> tier 3 -> tier 4`, com `ready_to_study`, `sort_reason_label` e `recommended_intent` corretos.
4. **`UI-API-04` (Segurança *Fail-Closed* de `POST /library/upload`)**: verifica que upload válido grava em `data/<user_id>/originals/`, que tentativa de *path traversal* (`../fora.pdf`) é bloqueada, e que payload acima do limite retorna `RESOURCE_LIMIT` (HTTP 413/400).
5. **`UI-API-05` (Não-Vazamento de Gabarito em `GET /sessions/{id}` e `GET /review/flashcards`)**: verifica que itens não revelados (`revealed == 0`) jamais expõem `expected_answer` no payload de sessão antes de `revealed=True`.
6. **`UI-API-06` (Visões de Operações, Calendário, Progresso, Biblioteca e Busca `Ctrl+K`)**: verifica a consistência dos payloads retornados por `/operations`, `/calendar`, `/progress` (`estimate is None`), `/library` e `/search?q=...`.
7. **`UI-API-07` (Entrega de Ativos Estáticos e Concorrência)**: verifica que `GET /`, `GET /ui/styles.css` e `GET /ui/app.js` respondem HTTP 200 com MIME types corretos e que `GET /health` responde concorrentemente.

### Camada 2 — Testes Automatizados de Frontend: Estado, Contratos e Invariantes (`ui/tests/ui_automated_test.ts`)
Executados via `deno test` em TypeScript estrito (tempo $< 1\text{s}$, zero rede):
1. **`UI-FE-01` (Ordenação de Disciplinas e Filtros da Coluna Esquerda)**: testa o comparador de 4 faixas, desempate determinístico e filtros (`all`, `ready`, `scheduled`, `pending_approval`).
2. **`UI-FE-02` (Máquina de Estados do Timer Pomodoro *Fail-Closed*)**: verifica sincronização com `PlanBlock` (ex.: 45 min) e fallback `25:00 / 05:00`, transição para `awaiting_confirmation` ao atingir `00:00`, garantia de que **nenhum** payload `update_activity` (`completed`) é emitido automaticamente no zero, e emissão apenas após confirmação explícita (`confirmPomodoroCompletion()`).
3. **`UI-FE-03` (Escada de Ajuda Socrática `L0 -> L3` e Proteção contra Vazamento de Gabarito)**: verifica que o estado de `LearningItem` oculta resposta esperada em `L0`, `L1` e `L2` e só exibe gabarito quando `help_level === "L3"` ou `revealed === true`.
4. **`UI-FE-04` (Flashcards Frente/Verso e Zero Gamificação)**: verifica que o cartão inicia com `backVisible = false`, exige ação explícita de virar (`flipCard`) antes de registrar autoavaliação e não contém campos proibidos (`streak`, `points`, `xp`, `leaderboard`, `ranking`).
5. **`UI-FE-05` (Renderização de `TypedError`, Gates de Modelo/Timezone e Gaveta de Evidências)**: verifica mapeamento dos 15 `ErrorCode` para mensagens acionáveis em português, banner de `MODEL_NOT_ADMITTED` / `timezone: null`, e abertura de `SourceRef` na gaveta lateral (`EvidencePack`).
6. **`UI-FE-06` (Inspeção Estrutural do DOM/HTML e CSS Grid)**: verifica que `ui/dist/index.html` e `ui/dist/styles.css` contêm o grid de 3 colunas + gaveta de evidências, os `<dialog>` modais nativos sem atributos ARIA redundantes (`role="dialog"` / `aria-modal` ausentes em `<dialog>`), `aria-labelledby`, `100dvh` e `overscroll-behavior: contain`.

### Camada 3 — Testes de Integração Ponta a Ponta (E2E Fluxos Críticos)
Integrados na suíte automatizada (`tests/test_interface_grafica_local.py`):
- **Fluxo E2E 1**: Criar disciplina $\rightarrow$ Fazer upload de material via `/library/upload` $\rightarrow$ Ingerir e indexar via `/turns` (`/ingest`) $\rightarrow$ Verificar que a disciplina fica `ready_to_study: true` em `/courses` e o documento aparece em `/library`.
- **Fluxo E2E 2**: Iniciar prática (`/practice`) via `/turns` $\rightarrow$ Verificar estado `waiting_student` em `/sessions/{id}` e `/operations` $\rightarrow$ Submeter resposta (`/submit`) $\rightarrow$ Verificar atualização qualitativa em `/progress` (`estimate == null`).
- **Fluxo E2E 3**: Cancelar sessão ativa via `/turns/{id}/cancel` e verificar status `cancelled`.

## Invariantes que não podem ser violados

1. **Proibição de execução silenciosa**: nenhum botão ou timer dispara escrita irreversível sem passar por `POST /turns` ou `POST /turns/{session_id}/resume`.
2. **Proibição de vazamento de gabarito**: `answer_ref` nunca é enviado ou exibido antes de `L3` ou `revealed=true`.
3. **Ausência de nota numérica opaca**: `TopicState.estimate` permanece `null`; a UI apresenta apenas `insufficient`, `mixed` ou `favorable` com justificativa auditável.
4. **Ausência de gamificação punitiva**: sem streaks, pontos, rankings ou cronômetros regressivos de pressão em exercícios.
5. **Transparência de estado degradado**: `MODEL_NOT_ADMITTED`, `timezone: null` e `CONNECTOR_DISABLED` são exibidos com clareza no topo e no painel de diagnóstico.
6. **Confinamento local**: servidor restrito a `127.0.0.1` e arquivos confinados a `data/<user_id>/`.

## Índice de tasks

- `001-api-loopback-endpoints-e-ordenacao.md` — Extensão de `eduagent/api.py` (`ThreadingHTTPServer`, endpoints de leitura/staging, ordenação em 4 faixas, entrega estática de `ui/dist/`) e flag `--serve-ui` em `eduagent/cli.py`.
- `002-shell-spa-design-system-e-sessao-tutoria.md` — Contratos TypeScript (`ui/src/contracts.ts`), máquina de estados (`ui/src/state.ts`), shell CSS Grid de 3 colunas + gaveta de evidências e timeline conversacional de tutoria/prática.
- `003-visoes-auxiliares-pomodoro-e-gates.md` — Timer Pomodoro *fail-closed* com `<dialog>` nativo, visões de Operações, Calendário (`.ics`), Biblioteca (upload confinado), Revisão (Flashcards), Progresso, Configurações e busca `Ctrl+K`.
- `004-suite-testes-automatizados-backend-frontend-e2e.md` — Suíte de testes automatizados em `ui/tests/ui_automated_test.ts` (`deno test`) e `tests/test_interface_grafica_local.py`, mais atualização de `RELATORIO_ESTADO_E_PROXIMOS_PASSOS.md`.
