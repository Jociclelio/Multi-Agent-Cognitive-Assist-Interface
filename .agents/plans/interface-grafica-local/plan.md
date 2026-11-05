# Plano: Interface gráfica local para o EduAgent-OS v0.1

Estado: rascunho

## Objetivo
Fornecer uma interface gráfica local (desktop, loopback) para o EduAgent-OS v0.1, na qual o aluno interage com os cinco agentes sem usar a CLI, com aparência semelhante ao WhatsApp Web: **matérias como âncoras estáveis** na lista lateral e **sessões de tutoria efêmeras** (um novo chat a cada turno do Tutor). A interface é consumidora dos contratos existentes (JSON Schemas de `schemas/`) e não altera os 11 artefatos obrigatórios do mapa §4 nem a filosofia fail-closed do sistema.

## Abordagem
O princípio de design: **cada elemento da UI é a projeção visual de um agente ou serviço já implementado** — a interface consome contratos, não inventa domínio. A metáfora é o WhatsApp Web, mas com a hierarquia do domínio: o ChatGPT é chat-cêntrico; o EduAgent-OS é matéria-cêntrico (`TopicState`, `StudyDemand`), e a UI espelha isso.

Layout de três colunas:

1. **Trilho de ícones** (esquerda; análogo aos ícones de status/canais do WhatsApp Web) — as áreas transversais, cada uma a projeção de um agente/serviço:
   - **Operações** — fila de aprovações pendentes (`Operation`/`OperationState`) com Aprovar/Rejeitar e contador no ícone.
   - **Calendário** — blocos do Planejador (`ScheduleProposal`, `PlanBlock`), replanejamento com `PlanDiff` e aceitar/rejeitar, orçamento de tempo semanal (`StudyDemand`/`DurationStatus`) e exportar ICS (`exports/`).
   - **Biblioteca** — histórico de material curado (Curador + Bibliotecário): itens com `LearningItem.ItemKind`, proveniência via `SourceRef`/`AcademicFact`, progresso do pipeline de ingestão (Docling → OCR → indexação → fatos); upload por drag-and-drop para `originals/`.
   - **Revisão** — flashcards apenas (skill `flashcard`), sem streak, sem gamificação. Quiz (skill `quiz`) permanece dentro do chat; não tem superfície própria.
   - **Progresso** — `TopicState` por tópico e resumo do que está sendo deixado de lado, alimentado pelo orçamento de tempo do calendário.
   - **Configurações** — estados honestos do sistema: gate do modelo (`MODEL_NOT_ADMITTED`), timezone `null`, conector web `CONNECTOR_DISABLED`, reranker não adotado; ausência declarada, nunca disfarçada.
2. **Lista de matérias** (coluna central) — as âncoras estáveis. Cada card exibe: ícone/nome da matéria, prévia do último turno, timestamp e **badge de "material pronto"** (a materialização do Inbox dentro da lista: "Pronto para estudar — Cinética Química ✓ [Iniciar]"). A ordenação é dinâmica e **legível**: curadoria nova sobe a matéria, bloco agendado próximo sobe mais, tempo sem interação desce — e o card mostra o **porquê** da posição ("bloco agendado 14h", "material novo curado hoje", "12 dias sem estudo"). Ordenação opaca não: o aluno entende por que sua matéria afundou.
3. **Painel de conversa** (direita) — o turno atual do Tutor com objetivo e `TutorState`; resumo/retomada/cancelamento via `POST /turns`, `resume`, `cancel`; **evidence drawer** expansível por mensagem exibindo `EvidencePack` (chunks, cobertura) e `SourceRef`.

Comportamentos acordados:
- **Sessões efêmeras**: não há chat longo por matéria; cada interação inicia uma nova sessão curta. A continuidade vem do sistema (`MemoryPack`, checkpoints, retomada longitudinal W05), não do histórico da conversa. Dentro da matéria, uma **gaveta de conversas anteriores** (buscável) preserva o passado — efemeridade não pode virar perda.
- **Proatividade**: o agente prepara e sinaliza (badge no card da matéria), o aluno inicia via botão "Iniciar"; nenhum turno é criado sem ação do usuário (modelo requisição/resposta do §12 preservado).
- **Pomodoro acoplado à sessão**: timer visível no painel de conversa e ao clicar "Iniciar", com duração sincronizada ao `PlanBlock` quando houver (fallback 25/5 em sessão livre). Tempo é estado da UI — sem gamificação. Ao terminar, a UI **pergunta** se o bloco foi concluído; só com confirmação explícita o fechamento é sinalizado ao sistema (fail-closed: o cronômetro nunca marca cumprimento sozinho).

Transversais:
- **Busca global** (Ctrl+K) sobre matérias, turnos anteriores, fatos curados, tópicos e materiais, reaproveitando os serviços de retrieval (BM25 + BGE-M3).
- **Erros de primeira classe**: os 12 `TypedError` renderizados como estados claros (mensagem ao usuário + retentabilidade), com indicador de status no topo lendo `/health`; nada de conversa quebrada.
- A UI fala HTTP JSON com `eduagent/api.py` (loopback, `X-EduAgent-User`), nunca acessa o SQLite diretamente.

Sequência de alto nível: (a) estender `eduagent/api.py` com endpoints de **leitura** derivados dos contratos existentes (matérias/tópicos com sinal de ordenação, sessões, calendário, biblioteca, operações, health detalhado); (b) escolher e montar o frontend com o esqueleto de três colunas; (c) implementar em ordem de valor: Painel de conversa + lista de matérias → badge "material pronto"/Iniciar → Operações → Calendário → Progresso → Biblioteca → Revisão → Configurações; busca global e gaveta de histórico por último.

## Escopo
- Entrega: frontend local + endpoints de leitura adicionais em `eduagent/api.py`, ambos versionados no repositório raiz.
- Frontend comunica-se exclusivamente com a API loopback; continua sem rede externa, single-threaded no servidor.
- Fora de escopo: streak/gamificação, onboarding de primeira execução, notificações push, rede/multiusuário, mobile, editor de materiais (o Curador é quem curar; a UI consome), alteração dos contratos do mapa §4, IQ dos agentes.

## Contexto
- `eduagent/api.py` — API loopback atual (`/turns`, `resume`, `cancel`, `/artifacts/{id}`, `/health`); base a estender com endpoints de leitura.
- `eduagent/contracts.py` e `schemas/` — contratos e JSON Schemas que a UI consome (Envelope, TutorTurn, ScheduleProposal, LearningItem, Operation, TopicState, TypedError etc.).
- `eduagent/agents/` e `eduagent/services/` — origem dos dados de cada área (planner/scheduling/calendar, curator/librarian/ingestion, monitor/assessment).
- `eduagent/skills/{flashcard,quiz}` — suporte da Revisão e do quiz intrachat.
- `fase2/documentos/04_mapa_completo_do_sistema.md` (§12 API, §3 estrutura, §4 contratos) — normativo; a UI não contradiz o loopback single-threaded nem o fail-closed.
- `README-eduagent.md` — estado do MVP e convenções de ambiente (`uv sync`).
- `.agents/protocolo.md` — fluxo plano → tasks → execução → revisão.

## Critérios de conclusão
- Esqueleto de três colunas (trilho, lista de matérias, painel de conversa) implementado e navegável, consumindo apenas a API loopback (nenhum acesso direto a `data/` ou SQLite pelo frontend).
- Matérias como âncoras estáveis com sessões efêmeras; gaveta de conversas anteriores acessível e buscável dentro da matéria.
- A ordenação da lista é dinâmica e legível: cada card exibe o motivo da posição; nenhum turno criado sem ação explícita do usuário.
- Erros tipados renderizados com mensagem ao usuário e indicador de retentabilidade; `/health` refletido no indicador de status.
- Pomodoro acoplado à sessão, com sincronização ao `PlanBlock` e confirmação explícita para fechar bloco.
- Nenhum streak/gamificação, onboarding ou notificação push (escopo negativo respeitado).
- Testes dos novos endpoints de leitura no suíte `uv run pytest tests/`, mantendo os 591 testes existentes verdes.
- `python3 fase2/scripts/verificar_documentos.py` permanece passando (a entrega da fase 2 não é regredida).

## Questões abertas
- **Stack do frontend**: Streamlit/Gradio (protótipo rápido, Python puro) vs. SPA (React/Vite, controle total para o esqueleto de três colunas, badges em tempo quase real e calendário). Decidir antes da primeira task de frontend. Nota: a metáfora WhatsApp Web com três colunas e reordenamento dinâmico favorece a SPA.
- **Versionamento da API**: estender `eduagent/api.py` in place (mesma versão, endpoints novos de leitura) vs. prefixar `/v1` desde já. Impacta clientes futuros.
- **Fórmula de ordenação da lista**: composição acordada (curadoria nova ↑, bloco agendado ↑↑, tempo sem interação ↓, motivo visível), mas os pesos exatos e o empate entre sinais ficam a definir na implementação — devem ser explícitos no código, nunca mágicos.
- **Sinal "sessão pronta"**: derivar em tempo real do `ScheduleProposal` + estado de curadoria, ou tabela própria. Preferência inicial: derivar em tempo real, sem estado novo.
- **Pomodoro**: apenas duração sincronizada ao `PlanBlock` com fallback 25/5, ou ciclos configuráveis na aba Configurações? Preferência inicial: sincronizado + fallback fixo, sem configuração no MVP.

## Tasks
<Índice preenchido pelo task-writer e mantido pelo task-master.>
