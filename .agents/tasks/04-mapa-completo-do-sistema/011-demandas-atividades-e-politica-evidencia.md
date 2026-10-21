# Task 011: Demandas, atividades e política evidência→demanda v1 (mapa §15.3, §15.4)

Estado: pendente
Depende de: 010
Origem: nenhuma

## Prompt
Implementar a geração de demandas e o ciclo de atividades (mapa §15.3 e §15.4) em `eduagent/services/scheduling.py` (parte de demandas) e `eduagent/agents/planner.py`: política `assessment_review_policy_v1` sempre registrada em demanda/review_due — tentativa aceita incorreta/parcial ou erro crítico → revisão sugerida no próximo dia local com disponibilidade (senão primeira data do horizonte); acerto independente → candidatos de recuperação em 1/3/7 dias a partir da ocorrência local; no máximo uma demanda pendente por `(user,topic,activity_kind,due_local_date,policy_version)`; retry não gera novas. Referência a avaliação confirmada via relação `assessment_topics`; prazo pedagógico = menor entre due sugerido e início confirmado; avaliação com dia sem hora → sugerir antes do dia sem promover datetime duro; revisão vencida mantém due original e busca primeiro bloco futuro indicando atraso; revisão além de 7 dias fica pendente para o próximo horizonte. Prioridades: classe1 (avaliação ≤48h ou erro crítico), classe2 (≤7 dias, revisão vencida ou dois erros aceitos em famílias distintas entre as últimas 5 tentativas no tópico), classe3 (demais); ausência de avaliação não inventa urgência; prioridade é política de ensaio. Duração: valor informado/confirmado prevalece; senão catálogo `practice=30min`, `review=15min`, `flashcard=15min` com rótulo estimated e mandatory=false; usuário pode confirmar para obrigatória; não converter percentual de domínio em duração; demanda duplicada consolidada com todas evidence_ids e prioridade mais alta. `StudyDemand` conforme §4. Atividades (§15.4): `ActivityUpdate(block_id,status,occurred_at,expected_version,operation_id)` com transições `planned→started→completed` ou `planned→missed/cancelled`; complete direto de planned aceita início/fim reais; sair de completed exige correção explícita; missed é declaração do aluno ou atraso confirmado (scheduler não presume falta por relógio); started bloqueia intervalo aprovado; sessão além do fim previsto pede atualização antes do solver e registra conflito; approve_plan valida preview atual; ambos retornam recibo e podem disparar replan uma vez por evento. Dependência temporal referencia demanda/atividade (não ID de tópico); pré-requisito pedagógico só vira dependência quando explicitado/confirmado; predecessor concluído satisfaz presença com término real; tarefa indivisível por default, decomposição só com demanda pai `splittable` confirmada (número/duração/subtarefas, soma ≥ original).

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §15.3 e §15.4 integrais; `StudyDemand` (§4); redutor/TopicState (009).
- Storage (004), contratos (003), commit idempotente (005).

## Corretude
- [ ] C1 — Política v1 determinística aplicada por serviço (não pelo LLM): testes cobrem erro crítico, acerto independente 1/3/7, unicidade por chave, consolidação de duplicadas, prioridades 1–3 e prazo pedagógico com dia sem hora.
- [ ] C2 — Durações: confirmado prevalece; catálogo com estimated/mandatory=false; nenhuma conversão de domínio em duração.
- [ ] C3 — Transições de atividade e semântica de dependência conforme §15.4 (testes: complete direto, sair de completed, started bloqueia, replan uma vez por evento, splittable confirmado).
- [ ] C4 — Mapa intocado; commits separados; submódulo não tocado.

## Notas

### Dificuldade esperada
5/10 — Política longa e determinística; risco de converter sugestão em obrigação.

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
