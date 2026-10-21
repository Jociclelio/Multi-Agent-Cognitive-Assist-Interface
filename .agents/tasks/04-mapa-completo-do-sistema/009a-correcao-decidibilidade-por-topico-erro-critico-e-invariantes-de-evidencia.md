# Task 009a: Correção — decidibilidade por tópico, erro crítico e invariantes de evidência (mapa §8, §15.2, §11)

Estado: aguardando revisão
Depende de: 009
Origem: 009 — correção

## Prompt
Corrigir na entrega da 009 (preservada, sem reversão; base `db57f68785da24bfe88c96ef752fbc08d5c49981`) os achados confirmados na revisão, em `eduagent/services/assessment.py`, `eduagent/agents/monitor.py`, `eduagent/contracts.py`, schemas e testes:

- **F1 (obrigatório)** — `_critical_error` gated por `correctness` global: o erro crítico é julgado POR CRITÉRIO (critério `critical=true` com nível 0 presente nos resultados, §15.2), não pelo `correctness` global do assessment. Critério critical nível 0 presente + outro critério indecidível NÃO pode manter `favorable`; novo erro crítico aceito volta a `mixed` mesmo com o assessment globalmente `undecidable` (§8: "mesmo assistido" permanece).
- **F2 (obrigatório)** — decidibilidade/elegibilidade POR TÓPICO (§8: "decidíveis **no tópico**"; §15.2: "avaliação por tópico usa somente seus critérios"): os probes do revisor (mimo) mostraram desvio nas duas direções — tópico A correta + critério de B indecidível → A permanece `favorable` onde a regra exige interromper, e o inverso suprime `favorable` indevidamente. O contrato da 003 só tem `evidence_kind` present/missing; o mapa §15.2 cita `undecidable` no mesmo rol ("`undecidable` não atualiza competência"), de modo que o caminho recomendado é alinhar o contrato: `evidence_kind=undecidable` como valor válido por critério (span não inventado; motivo descritivo; NÃO atualiza competência), o Monitor emite `undecidable` por critério em vez de omiti-lo, e a agregação por tópico (§15.2: "qualquer indecidível essencial=undecidable") e a elegibilidade do redutor passam a operar por tópico. Tópicos decididos do mesmo assessment continuam a atualizar estado; tópicos com critério essencial indecidível não recebem `last_attempt_at` nem entram em `independent_attempt_ids` (também resolve o A1 do revisor gpt-6-luna). Se optar por outro mecanismo map-conform, documente a escolha e justifique contra §8/§15.2/§4 — sem inventar valores fora do mapa e sem tocar a fonte normativa.
- **F4 (obrigatório)** — proposta com `level>0` e `span_text=None` vira `evidence_kind=missing` aceita como `correct`: invariantes de §15.2 — `missing` significa critério ausente (nível não pode ser >0); veredito com nível>0 exige span válido da resposta. `level>0` sem span é divergência formal → abstinência (`reliability=abstain`), não aceitação.
- **A2 de gpt-6-luna (obrigatório)** — `critical_criterion_ids` recebido livre em `check()`: validar contra a rubrica publicada do item (IDs pertencem à rubrica; criticidade coerente). Assessment formalmente coerente mas incompatível com a rubrica → recusa tipada ou abstinência documentada, nunca projeção de estado a partir de rubrica não conferida.
- **F3** — `check()` valida unicidade/revision antes de consultar o recibo: consultar `effects.receipt_for(user_id, operation_id, digest)` ANTES das validações (§11: "primeiro verifica `operation_id`"); retry idempotente pós-sucesso recupera o recibo. Mesmo tratamento para `record_attempt` com `attempt_id` repetido.
- **F5** — tabela M8 promete critério duplicado mas o `parametrize` não cobre; ramo determinístico `len(rubric)!=1` (`monitor.py`) sem teste: completar casos e ajustar a tabela.
- **F6** — tópico com tentativa sem avaliação aceita não populado em `last_attempt_at`: popular a partir das tentativas (mantendo `status=insufficient`), para a "idade informada à parte" de §8 não se perder.
- **A2 de GLM-5.3-Flash** — no reason da abstinência, citar a descrição do critério (`RubricCriterion.description` disponível), não apenas o motivo genérico.

Restrições: fonte normativa `fase2/documentos/04_mapa_completo_do_sistema.md` INTOCADA ("deve" é contrato; §15 prevalece quando especificar regra mais precisa); qualquer mudança de contrato mantém coerência com §4/§15.2, com schemas regenerados e verificados (`schemas_are_current`); BKT continua ausente; `estimate=null`; sem defaults apresentados como resultados medidos; commits SEPARADOS (entrega e registro), sem amend/force-push; temporários em `/tmp/opencode`; submodule `docs/playground-llmagenticsystem` intocado; sem push.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §8 (regra favorable e erro crítico, linhas sobre "decidíveis no tópico" e "mesmo assistido"), §15.2 (linha 255: agregação por tópico e `undecidable`), §4 linha 85 (`Assessment`, invariante "span existe salvo evidence_kind=missing"), §11 (operação idempotente/recibo).
- `eduagent/services/assessment.py` — redutor e projeção (linhas citadas na revisão: `:182-265`, `:464-477`, `:529-546`).
- `eduagent/agents/monitor.py` — rubrica e abstinência (`:418-546`, `:379-387`, `:264-272`).
- `eduagent/contracts.py`, `schemas/` — contrato `RubricCriterion` e enum de `evidence_kind`.
- `tests/test_task009_monitor_reducer.py` — tabela M1–M12/R1–R10/S1–S2 a estender com as regressões.
- Task mãe: `009-monitor-e-redutor-deterministico.md` (execução, escolhas 1–7 e Revisão com os achados).

## Corretude
- [x] C1 — F2: sondas do revisor viram testes de regressão nas duas direções — (i) tópico A correta + critério de B indecidível: A segue a regra exata de §8 conforme o caso (interrompe/compõe por decisão no tópico A, não pelo `correctness` global); (ii) critério de A indecidível: tópico A `undecidable`, não elegível e sem atualização de competência (sem `last_attempt_at`/`independent_attempt_ids`); tópicos integralmente decididos do mesmo assessment continuam a atualizar estado.
- [x] C2 — F1: critério `critical` nível 0 presente + outro critério indecidível → estado volta a `mixed` (erro crítico aceito), teste ponta a ponta serviço+persistência; erro crítico assistido também volta a `mixed` (§8), regressão R3i continua verde.
- [x] C3 — F4: `level>0` sem span → abstinência/divergência formal (nunca `missing` com nível>0 nem `correct` sem evidência); invariantes de `evidence_kind` re-verificadas nos testes de contrato.
- [x] C4 — A2 (luna): `critical_criterion_ids` fora da rubrica publicada → recusa tipada ou abstinência documentada, sem commit de projeção; teste cobre o caso incompatível.
- [x] C5 — F3: retry de `check` com mesmo `operation_id`+digest após sucesso devolve o recibo anterior (não `SCHEMA_INVALID`); idem para `record_attempt` com `attempt_id` repetido; §11 respeitado.
- [x] C6 — F5/F6/A2 (GLM): tabela M8 cobre critério duplicado; ramo `len(rubric)!=1` testado; `last_attempt_at` populado a partir das tentativas mesmo sem avaliação aceita (`insufficient` mantido); reason da abstinência cita a descrição do critério.
- [x] C7 — Suíte integral verde (297 + regressões novas); `estimate=null` e BKT ausentes; mapa e submodule intocados; schemas sincronizados; commits entrega/registro separados.

## Execução
- Modelo: GLM-5.3-Flash, provider `sd2` (`~/sd2-llm.sh`) — identidade informada pelo runtime do OpenCode.
- Base: `db57f68785da24bfe88c96ef752fbc08d5c49981` (entrega da 009, PRESERVADA — sem reversão; HEAD de partida `2ff1bff35fdf16f9eaf958461a0a51c691d0b819`, árvore limpa).
- Entrega: `563acd6e26a4f1adf53a1a1a2f701edafafa8e38`
- Arquivos da entrega:
  - `eduagent/contracts.py` — `Assessment.EvidenceKind.UNDECIDABLE` (§15.2 cita `undecidable` no rol de evidência) com invariantes: marcador não inferencial exige `level=0` e `response_span=null` (nunca inventar span para silêncio; fecha o caminho "nível>0 sem evidência" por construção — F4);
  - `schemas/Assessment.schema.json` — schema regenerado (`python -m eduagent.contracts --export schemas`; `schemas_are_current('schemas')` → True);
  - `eduagent/agents/monitor.py` — critério essencial indecidível EMITIDO como `evidence_kind='undecidable'` (nível 0 marcador, span nulo, motivo descritivo) em vez de omitido (F2); `level>0` sem span e proposta indecidível com span → divergência formal/abstinência (F4); reason da abstinência cita `RubricCriterion.description` (A2 GLM); ramo morto "nenhum critério decidível" removido;
  - `eduagent/services/assessment.py` — erro crítico julgado POR CRITÉRIO (`_critical_error` sem gate pelo `correctness` global; marcador `undecidable` não conta — F1); decidibilidade/elegibilidade POR TÓPICO (`_topic_results`/`_topic_undecidable`/`_topic_correctness`; tópico com critério essencial indecidível não compõe/interrompe nem atualiza `last_attempt_at`/ids; tópicos decididos do mesmo assessment continuam — F2); `last_attempt_at` populado a partir das tentativas sem avaliação aceita, `insufficient` mantido (F6); retry idempotente de `check` por `operation_id` consultado ANTES das validações com reconstrução do resultado anterior (`_replay_check`) e de `record_attempt` por `operation_id` (`_replay_attempt`) ou `attempt_id` repetido (`_existing_attempt` + digest; payload diferente → `SCHEMA_INVALID`) — F3; validação de `critical_criterion_ids` contra a rubrica PUBLICADA do item (`_published_critical_ids`: resolve `items.rubric_ref` → evento `item_published` → `RubricCriterion`; exige igualdade com o conjunto `critical` publicado — recusa tipada, sem commit — A2 luna); consistência formal atualizada (qualquer `undecidable` por critério exige `correctness='undecidable'`);
  - `eduagent/storage/repository.py` — `DomainStore.receipt_by_digest` para recuperar o recibo da operação committed pelo digest do payload (§11);
  - `tests/test_task009_monitor_reducer.py` — tabela ampliada de 36 para 48 casos (M1–M16, R1–R11 incluindo R3a–R3m, S1–S4); fixture `World` publica itens com rubrica resolvível em evento `item_published` (como no sink da 008) e `assess` emite marcadores `undecidable`/abstinência fiéis ao Monitor;
  - `tests/test_task003_contracts.py` — `test_assessment_undecidable_evidence_invariants` (C3).
- Evidências de Corretude (comandos e resultados):
  - `python -m pytest tests/test_task009_monitor_reducer.py -q` → 48 passed;
  - `python -m pytest tests/ -q -p no:cacheprovider` → 310 passed (suíte integral; 297 da 009 + 13 novos: 12 na tabela da task + 1 de contrato);
  - suíte em cópia isolada (`/tmp/opencode/009a-check` via `git archive HEAD` + `eduagent/`/`schemas/`/`tests/` da árvore de trabalho) → 309 passed, 1 skipped (smoke BGE-M3 sem pesos na cópia — declarado);
  - `python -m eduagent.contracts --check` e `schemas_are_current('schemas')` → True;
  - `git status` pós-entrega limpo; `fase2/documentos/04_mapa_completo_do_sistema.md` sem diff e submodule `docs/playground-llmagenticsystem` em `3504c4b` (intocados);
  - `estimate=None` mantido em todos os `TopicState` emitidos (MVP §8, sem BKT — nada de priors); nenhum default apresentado como resultado medido.
- Mapeamento achado → regressão: F1→R3m (+R3i verde); F2→R3j/R3k/R3l (+M9/M14, R3h); F4→M13 (+invariante de contrato); A2 luna→S4; F3→S3; F5→caso duplicado no `parametrize` de M8 + M15; F6→R4 (atualizado)/R11/projeção pura; A2 GLM→M16.
- Pendências/bloqueios: nenhum bloqueio. Escolha documentada (F2): alinhamento do contrato com `evidence_kind='undecidable'` por critério — §15.2 (linha 255) cita `undecidable` no mesmo rol de `evidence_kind` ("`undecidable` não atualiza competência") e prevalece como regra mais precisa; span nulo para `undecidable` justificado pelo princípio de §15.2 "não inventar span para silêncio" (o marcador não assevera evidência; a regra de §4 "span existe salvo missing" governa evidência julgada — exceção não inferencial fechada no docstring do contrato, com nível 0 obrigatório para impedir veredito sem evidência). Validação de A2 exige IGUALDADE entre `critical_criterion_ids` e o conjunto `critical` da rubrica publicada (IDs pertencem à rubrica E criticidade é propriedade da rubrica — subconjunto permitiria subdetecção silenciosa de erro crítico).

## Notas

### Dificuldade esperada
6/10 — A passagem de decidibilidade global para por tópico toca o contrato, o monitor e o redutor ao mesmo tempo; o risco está em manter as regressões R1–R10 verdes enquanto a semântica muda, e em não inventar valores fora dos enums de §4/§15.2.

### Dificuldade sentida
7/10 — O F2 exigiu mudança simultânea de contrato (novo valor de enum), Monitor (emissão do marcador) e redutor (decidibilidade/elegibilidade por tópico), com interação sutil entre F1 e F2 (erro crítico detectado em tentativa topicamente indecidível deve contar para `last_critical` sem atualizar ids/idade — resolvido separando `entries` (detecção) de `decided` (composição/estado)). O F3 exigiu desenhar a reconstrução do resultado de retry (`_replay_check`/`_existing_attempt` por digest) sem quebrar a unicidade lógica, e o A2 (luna) dependeu de descobrir que a rubrica publicada só existe no payload do evento `item_published` (ref `items.rubric_ref`), o que forçou atualização da fixture de teste. Nenhuma dificuldade ficou sem resolução.

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
