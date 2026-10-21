# Task 009: Monitor, redutor determinístico e estado de tópico (mapa §8, §15.2, §13.5 parte 2)

Estado: pendente
Depende de: 008
Origem: nenhuma

## Prompt
Implementar o Monitor e o redutor (mapa §8 e §15.2) em `eduagent/agents/monitor.py` e `eduagent/services/assessment.py` com `assessment.check`: Monitor recebe enunciado, resposta original, referência, critérios, ajuda e fonte — nunca a autovalidação do Tutor. Itens determinísticos: exatidão/tolerância explícita e unidades; texto com rubrica por critério 0/1/2, span de resposta e `misconception_code`. `RubricCriterion` (§15.2): id, topic_ids não vazio, níveis 0/1/2, critical, accepted_equivalences, evidence_refs; `evidence_kind=present` requer offsets válidos; `missing` exige span=null e descrição; `undecidable` não atualiza competência; span inventado, item ambíguo, ausência de fonte ou divergência formal → abstinência (`reliability=abstain`). Agregação por tópico: todos 2=correct; todos 0=incorrect; mistura=partial; qualquer indecidível essencial=undecidable; erro crítico se critério critical com nível 0. Redutor determinístico: aceita só Assessment válido, uma vez por `attempt_id`; tentativa com `occurred_at` e `attempt_ordinal` no commit (assessment tardio não muda ordem); independente = hint_level 0, sem reveal nem acesso prévio à solução da família na sessão corrente; assessment vigente = maior `assessment_revision` explicitamente aceito, com supersedes e recálculo da projeção desde eventos (não atualização cumulativa); unicidade `(attempt_id, assessment_revision)`. `TopicState`: `estimate=null` no MVP; zero evidência=`insufficient`; demais=`mixed`; `favorable` provisório exige exatamente a regra do §8: três tentativas mais recentes independentes/aceitas/decidíveis no tópico, todas corretas, de famílias distintas, posteriores ao último erro crítico aceito; novo erro crítico volta a mixed; tentativa independente parcial/incorreta interrompe a sequência; assistidas não removem erro crítico nem compõem sequência; "recentes" é ordem cronológica; idade informada à parte. BKT: NÃO implementar (shadow futuro); não inventar priors.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §8 (monitor/redutor) e §15.2 integral; `Assessment`/`TopicState` (§4).
- Tutor/items (008), storage (004), contratos (003).

## Corretude
- [ ] C1 — Monitor com rubrica por critério e abstinência nos quatro gatilhos do mapa (span inventado, ambiguidade, sem fonte, divergência formal); `evidence_kind` com invariantes de span.
- [ ] C2 — Redutor: uma avaliação por attempt_id (por revision), ordem por ordinal, supersedes recalcula projeção desde eventos — testado com assessment tardio/corrigido.
- [ ] C3 — Regra `favorable` aplicada exatamente como §8/§15.2 — testada com casos positivos e cada quebra (erro crítico, tentativa parcial, assistida, famílias repetidas, indecidível).
- [ ] C4 — `estimate=null` no MVP; BKT ausente; mapa intocado; commits separados.

## Notas

### Dificuldade esperada
6/10 — A regra favorable e o recálculo pós-supersedes têm muitos casos de borda; exigir tabela de testes.

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
