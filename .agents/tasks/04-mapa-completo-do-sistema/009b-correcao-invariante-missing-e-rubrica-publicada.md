# Task 009b: Correção — invariante `level==0` para `evidence_kind='missing'` e conferência do kind da rubrica publicada (mapa §8, §15.2, §4)

Estado: pendente
Depende de: 009a
Origem: 009a — correção

## Prompt
Corrigir na entrega da 009a (PRESERVADA, sem reversão; base `d4bb28db53bad0fede8249b97f9f1cea91f53bd7`, entrega `563acd6e26a4f1adf53a1a1a2f701edafafa8e38`) o achado A-01 (obrigatório) e o A-02 (recomendado) confirmados na revisão:

- **A-01 (obrigatório)** — invariante do F4 aplicada só a `undecidable`: em `Assessment.CriterionResult` (`eduagent/contracts.py`, `_span_invariants`), `CriterionResult(level>0, evidence_kind='missing', response_span=None)` constrói sem erro, e um assessment assim submetido a `check()` (`eduagent/services/assessment.py`, consistência formal) é ACEITO, compondo competência (`mixed` + tentativa em `independent_attempt_ids`). O F4 obrigatório da 009a e §15.2 exigem: "`missing` significa critério ausente (nível não pode ser >0)". Corrigir: (i) `_span_invariants` passa a exigir `level == 0` também para `MISSING` (o Monitor e o caminho determinístico já emitem só nível 0 em `missing` — sem mudança de emissão); (ii) a consistência formal de `check()` recusa o caso com erro tipado (divergência formal de assessment deserializado/externo é recusa, não abstinência), mantendo o replay idempotente do F3 como primeira operação; (iii) regenerar schemas (`python -m eduagent.contracts --export schemas`; `schemas_are_current('schemas')` → True) se o docstring/contrato mudar. Sonda de referência do revisor: `/tmp/opencode/reviewer-mimo-009a/probe/p1.py` e `p2.py` (se ainda existirem; caso contrário, reproduzir conforme a descrição).
- **A-02 (recomendado)** — `_published_critical_ids` (`eduagent/services/assessment.py`) resolve `items.rubric_ref` validando ref, usuário e payload com lista `rubric`, mas não confere o `kind` do evento: conferir `kind == 'item_published'` na resolução, recusando evento homônimo com outra kind.

Não alterar a semântica já aprovada na 009a (F1, F2, F3, F5, F6, A2 luna/GLM): todas as regressões M1–M16, R1–R11, S1–S4 e o caso de contrato `test_assessment_undecidable_evidence_invariants` devem permanecer verdes.

Restrições: fonte normativa `fase2/documentos/04_mapa_completo_do_sistema.md` INTOCADA ("deve" é contrato; §15 prevalece quando especificar regra mais precisa); coerência com §4/§15.2 (a exceção de span nulo de §4 estendida a `undecidable` permanece como divergência textual conhecida, documentada — não retocar); BKT ausente; `estimate=null`; sem defaults apresentados como resultados medidos; commits SEPARADOS (entrega e registro), sem amend/force-push/commits vazios; temporários em `/tmp/opencode`; submodule `docs/playground-llmagenticsystem` intocado; sem push.

## Contexto
- `eduagent/contracts.py` — `_span_invariants` em `Assessment.CriterionResult` (~linhas 770-790): invariante a estender para `missing`; docstring da exceção não inferencial.
- `eduagent/services/assessment.py` — consistência formal de `check()` (~609-640; replay idempotente ~694-703 vem ANTES das validações); `_published_critical_ids` (~718-798, resolução de `items.rubric_ref`).
- `schemas/Assessment.schema.json` — regenerar se o contrato mudar.
- `tests/test_task003_contracts.py` — `test_assessment_undecidable_evidence_invariants` (~:523) e testes de invariante de span: adicionar casos `missing` com `level>0` (construção recusada) e assessment aceito→recusado por `check()`.
- `tests/test_task009_monitor_reducer.py` — tabela M1–M16/R1–R11/S1–S4: não deve quebrar; se um caso existente emitir `missing` com nível>0, o caso está violando o mapa e deve ser corrigido (não enfraquecer a invariante).
- Task mãe: `009a-correcao-decidibilidade-por-topico-erro-critico-e-invariantes-de-evidencia.md` (seção Revisão com o A-01/A-02 e as sondas do revisor mimo).
- `eduagent/agents/tutor.py` (~316-377) — sink real de `item_published` para conferir a forma do evento no A-02.

## Corretude
- [ ] C1 — A-01: `CriterionResult(level>0, evidence_kind='missing', response_span=None)` é recusado na construção (erro tipado do contrato); teste de contrato cobre o caso.
- [ ] C2 — A-01: assessment deserializado com critério `missing` nível>0 submetido a `check()` é recusado com erro tipado (não aceito, não abstinência), sem commit de estado/evento; replay idempotente por `operation_id` continua precedendo as validações (regressão S3 verde).
- [ ] C3 — A-01: caminho do Monitor inalterado — `missing` continua emitido com nível 0; M13 (nível>0 sem span → abstinência) e a tabela completa da 009a permanecem verdes.
- [ ] C4 — A-02: `_published_critical_ids` confere `kind='item_published'`; teste cobre evento com payload homônimo e kind diversa → recusa tipada.
- [ ] C5 — Schemas sincronizados (`schemas_are_current('schemas')` → True); suíte integral verde (310 + casos novos); `estimate=null` e BKT ausentes; mapa e submodule intocados; commits entrega/registro separados.

## Execução
- Modelo: _
- Base: _
- Entrega: _
- Arquivos da entrega: _
- Evidências: _

## Notas

### Dificuldade esperada
3/10 — Correção pequena e cirúrgica: uma invariante a mais em `_span_invariants`, uma recusa na consistência formal de `check()` e a conferência de `kind`. O risco está em quebrar regressões existentes que eventualmente emitam `missing` com nível>0 (o que indicaria violação do mapa a corrigir, não a invariante a enfraquecer).

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
