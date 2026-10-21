# Task 014: Grafo LangGraph — intenções, rotas, checkpoints e limites (mapa §10, §12, §13.8 parte 1)

Estado: pendente
Depende de: 013
Origem: nenhuma

## Prompt
Implementar o grafo completo (mapa §10 e §12) em `eduagent/graph.py`, `eduagent/policy.py` e `eduagent/storage/checkpoints.py`: intenções `ingest, ask, practice, submit_answer, plan, replan, approve_plan, update_activity, memory_query, correct_fact, delete_data, export_calendar, curate, cancel`; comandos explícitos prevalecem; classificador LLM retorna enum validado e, em ambiguidade, pergunta antes de efeito. Rotas exatamente como o mapa §10 (cada `+` é leitura independente de snapshot comum; geração usa fila serial). Checkpointer SQLite persistente com `durability=sync` e `thread_id` por sessão; interrupt retoma o nó desde o início (preparação pura, efeitos em nós idempotentes separados); espera por aluno é fim da invocação e nova entrada retoma o item, sem timeout ativo durante espera. Política de ferramentas conforme a tabela §10 (quem pode propor, pré-condição, validação); nenhum agente recebe shell genérico ou escrita direta no DB; MCP é adaptador allowlisted; JSON correto para ação proibida é negado por código; fonte/tool result é dado rotulado e não altera política; divergência com solver/fato confirmado não é resolvida por votação (esclarecimento ou falha controlada). Segurança: resolver paths/ownership, bloquear traversal/symlink escapes; fetch bloqueia IP privado/loopback e revalida redirects/DNS. Limites (§12): antes de cada node/tool/geração conferir cancelamento, deadline e budget; reparo consome chamada e contador; ao esgotar, terminal com erro tipado e artefatos já válidos — nunca saída parcial silenciosamente aprovada; fila cheia responde `RESOURCE_LIMIT`; `cancel` → stop_dispatch → reconcile_started_effects → persist → cancelled. Checkpoint guarda refs, não PDFs integrais; estado de domínio é autoridade; checkpoint não substitui commit.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §10 e §12 (limites) integrais; §13.8; estado do grafo e erros (§4).
- Todos os serviços anteriores (005–013); adaptador de modelo (002).

## Corretude
- [ ] C1 — Todas as 11 rotas do §10 terminam com estado definido; teste por rota (incluindo cancelamento e deadline com terminal de erro tipado e artefatos válidos preservados).
- [ ] C2 — Checkpointer SQLite com sync/thread_id; sessão retomada de checkpoint preserva item pendente, nível de ajuda e histórico do turno (teste).
- [ ] C3 — Política de ferramentas: proposta fora de papel/pré-condição é negada por código; sem shell/escrita direta; fila serial nas gerações.
- [ ] C4 — Limites/budgets da config aplicados antes de cada nó; `RESOURCE_LIMIT` na fila cheia; mapa intocado; commits separados.

## Notas

### Dificuldade esperada
7/10 — Integrar tudo no grafo com interrupções/idempotência; maior superfície de regressão do plano.

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

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
