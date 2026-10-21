# Task 009: Monitor, redutor determinístico e estado de tópico (mapa §8, §15.2, §13.5 parte 2)

Estado: aguardando subtasks (009a)
Depende de: 008
Origem: nenhuma

## Prompt
Implementar o Monitor e o redutor (mapa §8 e §15.2) em `eduagent/agents/monitor.py` e `eduagent/services/assessment.py` com `assessment.check`: Monitor recebe enunciado, resposta original, referência, critérios, ajuda e fonte — nunca a autovalidação do Tutor. Itens determinísticos: exatidão/tolerância explícita e unidades; texto com rubrica por critério 0/1/2, span de resposta e `misconception_code`. `RubricCriterion` (§15.2): id, topic_ids não vazio, níveis 0/1/2, critical, accepted_equivalences, evidence_refs; `evidence_kind=present` requer offsets válidos; `missing` exige span=null e descrição; `undecidable` não atualiza competência; span inventado, item ambíguo, ausência de fonte ou divergência formal → abstinência (`reliability=abstain`). Agregação por tópico: todos 2=correct; todos 0=incorrect; mistura=partial; qualquer indecidível essencial=undecidable; erro crítico se critério critical com nível 0. Redutor determinístico: aceita só Assessment válido, uma vez por `attempt_id`; tentativa com `occurred_at` e `attempt_ordinal` no commit (assessment tardio não muda ordem); independente = hint_level 0, sem reveal nem acesso prévio à solução da família na sessão corrente; assessment vigente = maior `assessment_revision` explicitamente aceito, com supersedes e recálculo da projeção desde eventos (não atualização cumulativa); unicidade `(attempt_id, assessment_revision)`. `TopicState`: `estimate=null` no MVP; zero evidência=`insufficient`; demais=`mixed`; `favorable` provisório exige exatamente a regra do §8: três tentativas mais recentes independentes/aceitas/decidíveis no tópico, todas corretas, de famílias distintas, posteriores ao último erro crítico aceito; novo erro crítico volta a mixed; tentativa independente parcial/incorreta interrompe a sequência; assistidas não removem erro crítico nem compõem sequência; "recentes" é ordem cronológica; idade informada à parte. BKT: NÃO implementar (shadow futuro); não inventar priors.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §8 (monitor/redutor) e §15.2 integral; `Assessment`/`TopicState` (§4).
- Tutor/items (008), storage (004), contratos (003).

## Corretude
- [x] C1 — Monitor com rubrica por critério e abstinência nos quatro gatilhos do mapa (span inventado, ambiguidade, sem fonte, divergência formal); `evidence_kind` com invariantes de span.
- [x] C2 — Redutor: uma avaliação por attempt_id (por revision), ordem por ordinal, supersedes recalcula projeção desde eventos — testado com assessment tardio/corrigido.
- [x] C3 — Regra `favorable` aplicada exatamente como §8/§15.2 — testada com casos positivos e cada quebra (erro crítico, tentativa parcial, assistida, famílias repetidas, indecidível).
- [x] C4 — `estimate=null` no MVP; BKT ausente; mapa intocado; commits separados.

## Notas

### Dificuldade esperada
6/10 — A regra favorable e o recálculo pós-supersedes têm muitos casos de borda; exigir tabela de testes.

### Dificuldade sentida
6/10 — A regra `favorable` e o recálculo pós-supersedes de fato concentram os
casos de borda (âncora do último erro crítico, desempate por ordinal,
exclusão de tópicos por critério multicomponente, abstinência como não-vigente);
o contrato fechado da task 003 não representa indecidibilidade por critério,
o que exigiu escolhas de codificação (critério indecidível omitido dos
resultados; marcadores não inferenciais na abstinência) que precisam passar
pela revisão.

### Execução
- Identidade real do modelo: GLM-5.3-Flash, provider `sd2`
  (`~/sd2-llm.sh`) — identidade informada pelo runtime do OpenCode.
- SHA base: `b8dac576a8f5c917b004dc0da62b9fd72ea363bd`
- SHA da entrega: `db57f68785da24bfe88c96ef752fbc08d5c49981`
- SHA do registro: _preenchido no commit de registro (ver
  `git log -- <este arquivo>`)_
- Artefatos da entrega:
  - `eduagent/agents/monitor.py` — Monitor (rubrica por critério 0/1/2,
    spans como offsets reais, `misconception_code`, itens determinísticos com
    tolerância/unidades explícitas, abstinência nos quatro gatilhos de §8;
    `MonitorInput` sem campo para autovalidação do Tutor — garantia
    estrutural, testada);
  - `eduagent/services/assessment.py` — `AssessmentService.check` (validade,
    unicidade `(attempt_id, assessment_revision)`, revisão monotônica,
    correção com `supersedes` apontando para a vigente, consistência formal
    da agregação), `record_attempt` (ordinal atribuído no commit,
    independência julgada no commit) e `compute_topic_states` (projeção
    recalculada desde eventos, não cumulativa; regra `favorable` exata de
    §8/§15.2);
  - `eduagent/contracts.py` — `RubricCriterion` (§15.2) e atualização de
    `__all__`/`ALL_CONTRACT_MODELS`;
  - `eduagent/storage/migrations.py` — migração `0004`
    (`attempts.family_id`, `attempts.independent` com CHECK);
  - `schemas/RubricCriterion.schema.json` + `schemas/index.json` — schemas
    regenerados (byte a byte verificado por `schemas_are_current`);
  - `tests/test_task009_monitor_reducer.py` — 36 testes; fixture do novo
    contrato acrescida em `tests/test_task003_contracts.py`.
- Evidências de Corretude (comandos e resultados):
  - `python -m pytest tests/test_task009_monitor_reducer.py -q` → 36 passed
    (tabela de testes no cabeçalho do arquivo: M1–M12 monitor, R1–R10
    redutor — incluindo cada quebra da regra favorable e o recálculo
    pós-supersedes de assessment tardio/corrigido —, S1–S2 migração/serviço);
  - `python -m pytest tests/ -q` → 297 passed (suíte integral do repositório
    após a entrega);
  - `schemas_are_current('schemas')` → True (exportação do build
    sincronizada);
  - `git status` pós-entrega sem alteração em
    `fase2/documentos/04_mapa_completo_do_sistema.md` (mapa intocado) e sem
    alteração no submodule `docs/playground-llmagenticsystem`.
- Escolhas de implementação registradas (para a revisão):
  1. Abstinência contrato-conforme: assessment abstido leva
     `correctness='undecidable'`, `reliability='abstain'` e resultados por
     critério com `evidence_kind='missing'`, `span=null` e nível 0 como
     MARCADOR não inferencial (§15.2 exige span=null + descrição; nível não
     é atribuído inferencialmente) — o redutor ignora assessments abstidos
     por completo (R4/R8 provam que nem erro crítico marcador atualiza
     estado).
  2. Critério essencial indecidível: o contrato (task 003) não tem
     evidência `undecidable` por critério; o Monitor omite o critério dos
     `criterion_results` (não fabrica nível) e rotula o assessment
     `undecidable` (M9). Decidibilidade por tópico segue o `correctness`
     global do assessment vigente — indecidível não compõe nem interrompe a
     sequência (§8 interrompe só parcial/incorreta independente; R3h).
  3. Critério multicomponente (múltiplos tópicos) não decomposto: a tentativa
     não atualiza o estado desses tópicos (§15.2; R9).
  4. `error_codes` do `TopicState` fica vazio no MVP: o enum tipado do mapa
     §4 é de erros de sistema, não de misconceptions pedagógicas (que
     permanecem nos assessments); `review_due=None` — política §15.3 é da
     task 011.
  5. `record_attempt` usa ação `event.append` (enum fechado de
     `OperationAction` da task 003 não tem `attempt.record`; nova ação
     exigiria revisão de contrato).
  6. Janela de corrida MVP: pré-leitura para cálculo de projeção e
     `expected_version` antes do commit idempotente; sob escrita concorrente
     o commit falha com `VERSION_CONFLICT` retentável (controle conservador
     por usuário do §15.1; multiusuário concorrente em rede está fora do
     MVP).
  7. Normalização numérica de ensaio (vírgula decimal quando não há ponto) e
     checagem de unidade por substring case-insensitive — escolhas de ensaio
     declaradas no docstring, não resultados medidos.
- Pendências/bloqueios: nenhum bloqueio. Fora do escopo desta task (mantidos
  para 011/014/017): política de `review_due` (§15.3), conexão do Monitor ao
  grafo/turnos do Tutor e backend de julgamento real (os testes usam grader
  injetado determinístico); BKT não implementado por contrato (§8).

### Revisão
- Orquestrador: GLM-5.3-Flash (provider `sd2`) — sessão master do ciclo 04-mapa-completo-do-sistema.
- Alvo: base `b8dac576a8f5c917b004dc0da62b9fd72ea363bd`; entrega `db57f68785da24bfe88c96ef752fbc08d5c49981` (8 arquivos, +2634/−3); registro `65554c688231fac7cb42aca8c34955fe48e9bfbc`; árvore limpa em HEAD, commits entrega/registro separados conferidos; mapa e submodule sem diff. Rodada em modo **paralelo** (padrão — revisão por leitura de código e testes de CPU com temporários isolados em `/tmp/opencode`; sem GPU, portas, diretórios de build ou benchmarks em disputa), três revisores de modelos distintos, mesmos paths/SHAs, sem compartilhar pareceres entre si.
- Avaliações:
  - `sd2/GLM-5.3-Flash` — 9/10, aprovada; reproduziu a suíte da task (36 passed) e a integral (297 passed); C1–C4 verificados com referências de linha; classificou o desvio de decidibilidade (global vs. por tópico) como conservador e não bloqueante (A1), com A2 (reason genérico por critério na abstinência) e A3 (`insufficient` para tópico multicomponente) baixos.
  - `openai/gpt-6-luna` — 7/10, corrigir; suíte da task 36 passed (`-p no:cacheprovider`, suíte integral não repetida — limitação declarada); A1 alto — assessment globalmente indecidível ainda atualiza `last_attempt_at`/`independent_attempt_ids` dos tópicos tocados (`assessment.py:182-220,252-265`), contra "undecidable não atualiza competência" (§15.2); A2 médio — `critical_criterion_ids` recebido livre, sem validação contra a rubrica publicada do item (`assessment.py:464-477,224-235`).
  - `opencode/mimo-v2.6-flash-free` — 7/10, corrigir; suíte integral em cópia isolada (`/tmp/opencode/rev009-a` via `git archive`): 296 passed, 1 skipped (smoke BGE-M3 sem pesos na cópia — declarado); sondas ponta a ponta reproduzindo: F1 — `_critical_error` gated por `correctness` global: critério critical nível 0 presente + outro omitido (formato M9) mantém `favorable` após erro crítico aceito (esperado `mixed`); F2 — elegibilidade/interrupção usa o `correctness` global em vez de decidibilidade **no tópico** (§8), com desvio reproduzido nas DUAS direções (favorable mantido indevidamente e favorable suprimido indevidamente); F3 — `check()` valida unicidade/revision antes de consultar o recibo por `operation_id` (§11: retry idempotente pós-sucesso não recupera recibo); F4 — proposta com `level>0` e `span_text=None` vira `evidence_kind=missing` aceita como `correct` (veredito correto sem evidência); F5 — tabela M8 promete critério duplicado mas `parametrize` não cobre, e ramo `len(rubric)!=1` sem teste; F6 — tópico com tentativa sem avaliação aceita não populado em `last_attempt_at` (idade de §8 perdida).
- Nota final: 7/10 — não é média automática: o R1 subestimou o desvio de decidibilidade porque o tratou como unicamente conservador, mas a sonda reproduzida do R3 mostra desvio nas duas direções e o F1 produz falso `favorable` após erro crítico — quebra direta de C3 e da segurança da regra favorable; o F4 aceita veredito `correct` sem evidência, violando os invariantes de `evidence_kind` de §15.2. Os pontos fortes (estrutura do monitor/redutor, suíte de 36 casos, recálculo desde eventos, isolamento, sem invenções) são reais e preservados; a base é sólida, porém C3 não pode ser aprovado como "regra exata" enquanto F1/F2 persistirem.
- Parecer: Divergência essencial resolvida por evidência: R1 disse conservador, R3 demonstrou com sonda reproduzida em ambas as direções + F1 — prevalece R3/R2 (dois de três) com evidência concreta; sem necessidade de esclarecimento adicional. Correções obrigatórias na subtask: F1 (erro crítico julgado por critério, não gated por indecidibilidade global), F2 (decidibilidade/elegibilidade por tópico, em mecanismo que respeite os enums de §4/§15.2 — o executor documentou que o contrato 003 só tem `evidence_kind` present/missing; a solução NÃO pode inventar valores fora do mapa), F4 (nível>0 sem span não pode virar `missing` aceito como correct) e A2 do R2 (validar `critical_criterion_ids` contra a rubrica publicada). Também delimitadas: F3 (recibo por `operation_id` antes das validações, §11), F5 (completar tabela M8 e ramo `len(rubric)!=1`), F6 (`last_attempt_at` populado das tentativas), A2 do R1 (descrição do critério no reason da abstinência). A3 do R1 e escolha 6 (janela de corrida MVP) ficam como observações registradas, não bloqueantes. Nenhuma pendência essencial escondida.
- Decisão: **corrigir** — entrega preservada (sem reversão); subtask 009a criada para os achados acima.
- Reversão: não se aplica — entrega preservada.
- Próximo passo: subtask [009a-correcao-decidibilidade-por-topico-erro-critico-e-invariantes-de-evidencia.md](009a-correcao-decidibilidade-por-topico-erro-critico-e-invariantes-de-evidencia.md). Após 009a fechada, família 009 resolve e libera 010.

<!-- task-cycle: {"decision":"corrigir","next_task":".agents/tasks/04-mapa-completo-do-sistema/009a-correcao-decidibilidade-por-topico-erro-critico-e-invariantes-de-evidencia.md","family":".agents/tasks/04-mapa-completo-do-sistema/001-scaffold-e-configuracao.md","plan":".agents/plans/04-mapa-completo-do-sistema/plan.md"} -->

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
