# Task 005: Commit idempotente, recibo e recuperação (mapa §11, §13.2)

Estado: aguardando revisão
Depende de: 004
Origem: nenhuma

## Prompt
Implementar o commit idempotente do mapa §11 em `eduagent/services/effects.py`/`eduagent/storage/repository.py`: `commit(operation_id, digest, expected_version)` abre transação curta, confere identidade/permissão e **primeiro verifica `operation_id`**: mesmo ID+digest+usuário devolve o recibo anterior mesmo que `expected_version` agora seja antiga; digest/usuário diferente para o mesmo ID falha. Operação nova: confere revisão esperada, insere evento/operação/outbox e atualiza projeção, atomicamente. Não manter transação durante LLM/rede. Checkpoint (DB separado, task 014) não é atômico: replay consulta a operação autoritativa e reutiliza o recibo. Implementar dispatcher com lease para o outbox: crash antes do commit não promove estado; após commit recupera pendente; após efeito antes do ACK reconcilia destino por identidade; efeito desconhecido sem consulta possível permanece `UNKNOWN_EFFECT` sem retry automático. Entrega ao menos uma vez; sem promessa de exactly-once distribuído. Validar crash/replay com testes que matam o processo em pontos definidos (antes/depois do commit, antes/depois do efeito) e demonstram: sem duplicação, sem perda de efeito reconhecido, recibo estável.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §11 integral; §15.1 (receipt/lease/trace não incrementam domain_revision).
- Storage da task 004; contrato `Operation` da 003.

## Corretude
- [x] C1 — Semântica exata do §11: dedup por `operation_id` antes de `expected_version`; conflito de digest/usuário falha; commit atômico com evento+operação+outbox+projeção.
- [x] C2 — Testes de crash/replay reproduzem os três cenários (pré-commit, pós-commit, pós-efeito sem ACK) sem duplicação nem perda; recibo reutilizado no replay.
- [x] C3 — Dispatcher com lease; `UNKNOWN_EFFECT` sem retry automático; lease/recibo não incrementam `domain_revision`.
- [x] C4 — Mapa intocado; commits separados; submódulo não tocado.

## Execução
- Modelo: GLM-5.3-Flash (provider `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime.
- Base: `5d8df51cb7c9670122d39fb881d3da3acee147c6` (árvore limpa; dependência 004 fechada pela 004a).
- Entrega: `17c1392a2978e8d430ec23c6b2ab6897232c5a02` (código/testes: `eduagent/services/effects.py`, `eduagent/storage/repository.py`, `tests/test_task005_effects.py`, `tests/_task005_crash_runner.py`).
- Arquivos da entrega: `eduagent/services/effects.py` (implementação completa do stub: `EffectsService.commit` com validação pelo contrato `Operation` da 003 FORA da transação e dedup por `operation_id` ANTES de `expected_version`; `EffectsService.receipt_for` como consulta autoritativa para replay de checkpoint; `OutboxDispatcher` com lease — efeito aplicado fora de qualquer transação, probe de reconciliação por identidade, `EffectOutcome` APPLIED/NOT_APPLIED/UNKNOWN, `DispatchReport` com erro tipado `UNKNOWN_EFFECT`); `eduagent/storage/repository.py` (`commit_operation` com dedup consultando por ID global e comparando usuário+digest — §11 "digest/usuário diferente para o mesmo ID falha" — e outbox inserido por último, após `operations`, por causa da FK; novos métodos `receipt_for`/`get_operation` (replay autoritativo) e `claim_outbox`/`ack_outbox`/`requeue_outbox`/`fail_outbox`/`outbox_row` com transações curtas próprias que não incrementam `domain_revision` (§15.1); dataclass `OutboxRow` com `state_before`/`recovered`); `tests/test_task005_effects.py` (23 testes: C1 semântica do §11, replay autoritativo, dispatcher/lease/UNKNOWN_EFFECT, metadados operacionais sem bump); `tests/_task005_crash_runner.py` (runner de crash em subprocesso com `os._exit(137)` em três pontos: pré-commit via trace callback do sqlite3 antes do statement `COMMIT`, pós-commit, pós-efeito sem ACK).
- Evidências:
  - Suíte: `python -m pytest tests/ -q` → **130 passed** (107 pré-existentes verdes + 23 novos), base `5d8df51` → 107 passed antes das mudanças. Não é resultado medido de desempenho: são asserções funcionais locais de curta duração.
  - C2 — crash/replay com processo morto (`os._exit(137)`, sem unwind/rollback/finally): **pré-commit** (`returncode 137` provado) → nada promovido (revisão 0; 0 linhas em operations/events/facts/outbox) e o replay com a mesma identidade aplica exatamente uma vez, com recibo reutilizado no segundo replay mesmo com `expected_version=0` já antiga; **pós-commit** → operação committed + outbox `pending` persistem e o dispatcher recupera o pendente entregando uma única vez; **pós-efeito sem ACK** → marcador do destino registra `apply_calls == 1`, e o dispatcher seguinte (lease expirado, `now` futuro) reconcilia por identidade (`probe` → APPLIED) e confirma com ACK sem reentrega — `apply_calls` permanece 1 (sem duplicação, sem perda de efeito reconhecido, recibo/estado estáveis).
  - C1 — dedup antes da versão testado (`test_retry_returns_previous_receipt_even_with_stale_version`): mesmo ID+digest+usuário com `expected_version=0` após revisão já em 1 devolve o recibo anterior (`applied_at`/`domain_revision` idênticos, `was_retry=True`) sem incrementar nem duplicar; digest diferente → `SCHEMA_INVALID`; usuário diferente para o mesmo ID → `SCHEMA_INVALID` (dedup consulta por ID global); commit atômico verificado por contagens pós-commit (1 evento, 1 fato, 1 outbox `pending`, 1 operação, revisão +1 exatamente).
  - C3 — lease testado (`claim_outbox` não apropria linha `in_flight` com lease válido; recupera após expiração com `state_before='in_flight'`); `UNKNOWN_EFFECT`: apply desconhecido + probe indisponível → outbox `failed` terminal, erro tipado `ErrorCode.UNKNOWN_EFFECT` no relatório, e ciclo seguinte com handler novo registra zero chamadas a apply/probe (sem retry automático); `apply` com exceção (rede) é tratado como desconhecido → com probe `NOT_APPLIED` volta a `pending` (entrega ao menos uma vez, §11); lease/ACK/requeue/fail e recibo de retry não alteram `domain_revision` (§15.1) — testado ponta a ponta.
  - Probe manual independente (fora do pytest, descartado em `/tmp/opencode`): replay de recibo com campos de identidade estáveis (`operation_id`/`domain_revision`/`applied_at` idênticos, `was_retry=True` no reuso), `UNKNOWN_EFFECT` terminal e revisão intacta pós lease/fail; `py_compile` OK nos três arquivos alterados/criados.
  - **Decisão explícita — marcação persistente de `UNKNOWN_EFFECT`:** a linha do outbox vai ao estado terminal `failed` do DDL §5 (CHECK `pending/in_flight/done/failed`) e o motivo tipado vai ao `DispatchReport.errors` (trace/§12 nas tasks 014/015); NÃO foi criada migração para colunas extras (`attempts`/`last_error`) porque qualquer migração nova quebraria a equivalência de schema registrada pela 004a (`test_0002_stepwise_equals_full_run` aplica explicitamente `MIGRATIONS[0]`+`[1]` no caminho incremental) — escolha de ensaio registrada, mapa intocado.
  - **Decisão explícita — validação do contrato `Operation` no estado `PENDING` apenas:** a validação cobre identidade (UUIDs), ação, `payload_hash` (SHA-256 hex) e `expected_version ≥ 0` antes de abrir transação; o acoplamento receipt⇔committed do contrato não é exercido com `Ref` porque o recibo não é artefato com linha própria no DDL §5 — é armazenado em `operations.receipt_json` (§5/§11). O `probe` do handler é o mecanismo de reconciliação por identidade exigido pelo §11.
  - **Decisão explícita — dedup consulta por ID global:** `commit_operation` passou a consultar `operations` por `id` (PK global) e comparar `user_id` e `digest`, corrigindo a consulta anterior (`WHERE id = ? AND user_id = ?`), que tratava mesmo ID sob outro usuário como operação nova e explodia em `IntegrityError` em vez de `SCHEMA_INVALID` (§11: "digest/usuário diferente para o mesmo ID falha").
  - **Achados latentes A1/A2 da 004a (framework de migrações):** considerados e NÃO tratados nesta task — não há migração nova nesta entrega e nenhum caminho desta task chama `apply_migrations` com transação implícita pendente; ficam registrados para robustez futura do framework.
  - Intocabilidade verificada por `git status --porcelain` entre base e entrega: apenas os 4 arquivos da task; `fase2/documentos/04_mapa_completo_do_sistema.md` sem diff; submodule `docs/playground-llmagenticsystem` em `3504c4b` sem alteração; `config/`, `pyproject.toml` e `uv.lock` intocados.

## Notas

### Dificuldade esperada
6/10 — Semântica idempotente com simulação de crash; fácil errar a ordem dedup→version.

### Dificuldade sentida
5/10 — A ordem dedup→version e a máquina de estados do lease foram diretas porque a 004 já pré-implementou a dedup na camada de dados; o peso extra veio de três pontos: (i) a FK do outbox referencia `operations(id)`, forçando o outbox a ser inserido por último na transação (a primeira versão falhava com `FOREIGN KEY constraint failed`); (ii) simular crash real exigiu subprocesso com `os._exit` — `sqlite3.Connection` é imutável, e o crash pré-commit precisou de trace callback (invocado antes do statement); o cenário pós-efeito deu falso negativo na primeira tentativa porque um claim manual criava lease que o próprio dispatcher via como recuperado; (iii) a tentativa de colunas extras no outbox para persistir o motivo de `UNKNOWN_EFFECT` esbarrou na equivalência de schema registrada pela 004a — decisão documentada de usar o estado terminal `failed` sem migração.

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
