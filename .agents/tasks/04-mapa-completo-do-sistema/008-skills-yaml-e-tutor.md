# Task 008: Skills YAML e Tutor (mapa §8 tutor/skills, §13.5 parte 1)

Estado: pendente
Depende de: 007
Origem: nenhuma

## Prompt
Implementar o Tutor e o catálogo de skills (mapa §8) em `eduagent/agents/tutor.py` e `eduagent/skills/`: estados `explain`, `attempt`, `hint`, `self_explain`, `transfer`, `close`; um turno principal por chamada, terminal `waiting_student` quando pede resposta; intenção direta recebe explicação direta; para prática, criar item com fonte e gabarito/rubrica prévia, separando solução; revelação explícita é registrada; pistas 1=conceito, 2=próximo passo, 3=exemplo análogo; após três, oferecer solução comentada ou encerramento; pedido de solução, recusa e cancelamento encerram sem insistência; transferência usa família identificada e não conta cópia como aprendizagem independente. Skills YAML com `id, version, tasks, input_schema, preconditions, steps, allowed_tools, output_schema, postconditions, stop_conditions, max_calls, cases`; catálogo obrigatório: explicar, pistas, quiz, flashcard, autoexplicação; hash/version registrados; alterações só por revisão offline (sem autoedição ao vivo); flashcard com pergunta/verso separados, conceito atômico e fonte; revisão inicial 1/3/7 dias é política configurável. Saídas conforme `TutorTurn`/`LearningItem` (003) e geradas pelo adaptador da 002 (JSON válido com schema/parse/política).

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §8 (parágrafos de Tutor e Skills); §13.5; `TutorTurn`/`LearningItem` (§4).
- Adaptador de modelo (002), retrieval (007), storage (004).

## Corretude
- [ ] C1 — Máquina de estados do Tutor conforme mapa, com terminal `waiting_student` e encerramento sem insistência em recusa/cancelamento.
- [ ] C2 — Cinco skills YAML no schema do mapa, com hash/version registrados; nenhum caminho de autoedição em runtime.
- [ ] C3 — Item de prática tem gabarito/rubrica prévia separado da solução; flashcard separa pergunta/verso com fonte; transferência exige família identificada.
- [ ] C4 — Mapa intocado; commits separados; submódulo não tocado.

## Notas

### Dificuldade esperada
5/10 — Estados e skills bem especificados; risco em JSON estrito com o modelo local.

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
