# Plano: Interface gráfica local para o EduAgent-OS v0.1

Estado: rascunho

## Objetivo
Fornecer uma interface gráfica local (desktop, loopback) para o EduAgent-OS v0.1, na qual o aluno interage com os cinco agentes sem usar a CLI: chats de tutoria, gestão do calendário planejado, histórico de material curado, prática com flashcards e acompanhamento do progresso por tópico. A interface é consumidora dos contratos existentes (JSON Schemas de `schemas/`) e não altera os 11 artefatos obrigatórios do mapa §4 nem a filosofia fail-closed do sistema.

## Abordagem
O princípio de design: **cada área da UI é a projeção visual de um agente ou serviço já implementado** — a interface consome contratos, não inventa domínio. Sete áreas:

1. **Home** — Inbox de sessões prontas (proatividade do Planejador: o agente prepara e sinaliza, o aluno inicia via botão "Iniciar"; nenhum turno é criado sem ação do usuário, preservando o modelo requisição/resposta do §12) + fila de Operações pendentes (`Operation`/`OperationState`) com Aprovar/Rejeitar.
2. **Chats** — múltiplas sessões de estudo estilo ChatGPT, cada uma com objetivo e `TutorState`; resumo/retomada/cancelamento via `POST /turns`, `resume`, `cancel`; **evidence drawer** expansível por mensagem exibindo `EvidencePack` (chunks, cobertura) e `SourceRef`.
3. **Calendário** — blocos do Planejador (`ScheduleProposal`, `PlanBlock`), propostas de replanejamento com `PlanDiff` e aceitar/rejeitar, orçamento de tempo semanal por tópico (`StudyDemand`/`DurationStatus`) e botão de exportar ICS (`exports/`).
4. **Biblioteca** — histórico de material curado (Curador + Bibliotecário): itens com `LearningItem.ItemKind`, proveniência via `SourceRef`/`AcademicFact`, e progresso do pipeline de ingestão (Docling → OCR → indexação → fatos) exposto por item; upload por drag-and-drop para `originals/`.
5. **Revisão** — flashcards apenas (skill `flashcard`), sem streak, sem gamificação. Quiz (skill `quiz`) permanece dentro do chat quando o Tutor decide avaliar; não tem aba própria.
6. **Progresso** — `TopicState` por tópico (domínio/status) e resumo do que está sendo deixado de lado, alimentado pelo orçamento de tempo do calendário.
7. **Configurações** — página honesta dos estados reais do sistema: gate do modelo (`MODEL_NOT_ADMITTED`), timezone `null`, conector web `CONNECTOR_DISABLED`, reranker não adotado; ausência declarada, nunca disfarçada.

Transversais:
- **Pomodoro acoplado à sessão de estudo**: timer visível durante o chat (e no Inbox ao clicar "Iniciar"), com duração sincronizada ao `PlanBlock` correspondente quando houver (fallback: ciclo padrão 25/5 quando a sessão é livre, sem bloco). O tempo é estado da UI — sem gamificação, sem streak. Ao terminar, a UI **pergunta** ao aluno se o bloco foi concluído; só com confirmação explícita o fechamento é sinalizado ao sistema (fail-closed: o cronômetro nunca marca cumprimento sozinho).
- **Busca global** (Ctrl+K) sobre chats, fatos curados, tópicos e materiais, reaproveitando os serviços de retrieval (BM25 + BGE-M3).
- **Erros de primeira classe**: os 12 `TypedError` renderizados como estados claros (mensagem ao usuário + retentabilidade), com indicador de status no topo lendo `/health`; nada de chat quebrado.
- A UI fala HTTP JSON com `eduagent/api.py` (loopback, `X-EduAgent-User`), nunca acessa o SQLite diretamente.

Sequência de alto nível: (a) estender `eduagent/api.py` com endpoints de **leitura** derivados dos contratos existentes (sessões, calendário, biblioteca, tópicos, operações, health detalhado); (b) escolher e montar o frontend; (c) implementar as sete áreas em ordem de valor: Chats → Inbox/Operações → Calendário → Progresso → Biblioteca → Revisão → Configurações; busca global por último.

## Escopo
- Entrega: frontend local + endpoints de leitura adicionais em `eduagent/api.py`, ambos versionados no repositório raiz.
- Frontend comunica-se exclusivamente com a API loopback; continua sem rede externa, single-threaded no servidor.
- Fora de escopo: streak/gamificação, onboarding de primeira execução, notificações push, rede/multiusuário, mobile, editor de materiais (o Curador é quem curar; a UI consome), alteração dos contratos do mapa §4, IQ dos agentes.

## Contexto
- `eduagent/api.py` — API loopback atual (`/turns`, `resume`, `cancel`, `/artifacts/{id}`, `/health`); base a estender com endpoints de leitura.
- `eduagent/contracts.py` e `schemas/` — contratos e JSON Schemas que a UI consome (Envelope, TutorTurn, ScheduleProposal, LearningItem, Operation, TopicState, TypedError etc.).
- `eduagent/agents/` e `eduagent/services/` — origem dos dados de cada área (planner/scheduling/calendar, curator/librarian/ingestion, monitor/assessment).
- `eduagent/skills/{flashcard,quiz}` — suporte da aba Revisão e do quiz intrachat.
- `fase2/documentos/04_mapa_completo_do_sistema.md` (§12 API, §3 estrutura, §4 contratos) — normativo; a UI não contradiz o loopback single-threaded nem o fail-closed.
- `README-eduagent.md` — estado do MVP e convenções de ambiente (`uv sync`).
- `.agents/protocolo.md` — fluxo plano → tasks → execução → revisão.

## Critérios de conclusão
- As sete áreas implementadas e navegáveis, consumindo apenas a API loopback (nenhum acesso direto a `data/` ou SQLite pelo frontend).
- Nenhum turno criado sem ação explícita do usuário; proatividade restrita ao Inbox (preparar + sinalizar).
- Erros tipados renderizados com mensagem ao usuário e indicador de retentabilidade; `/health` refletido no indicador de status.
- Nenhum streak/gamificação, onboarding ou notificação push (escopo negativo respeitado).
- Testes dos novos endpoints de leitura no suíte `uv run pytest tests/`, mantendo os 591 testes existentes verdes.
- `python3 fase2/scripts/verificar_documentos.py` permanece passando (a entrega da fase 2 não é regredida).

## Questões abertas
- **Stack do frontend**: Streamlit/Gradio (protótipo rápido, Python puro) vs. SPA (React/Vite, controle total para calendário e inbox). Decidir antes da primeira task de frontend.
- **Versionamento da API**: estender `eduagent/api.py` in place (mesma versão, endpoints novos de leitura) vs. prefixar `/v1` desde já. Impacta clientes futuros.
- **Estado do Inbox**: onde persiste a sinalização "sessão pronta" (derivar em tempo real do `ScheduleProposal` + estado de curadoria, ou tabela própria). Preferência inicial: derivar em tempo real, sem estado novo.
- **Pomodoro**: apenas duração sincronizada ao `PlanBlock` com fallback 25/5, ou ciclos configuráveis na aba Configurações? Preferência inicial: sincronizado + fallback fixo, sem configuração no MVP.

## Tasks
<Índice preenchido pelo task-writer e mantido pelo task-master.>
