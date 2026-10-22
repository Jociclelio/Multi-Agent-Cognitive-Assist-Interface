# Relatório de testes do MVP — EduAgent-OS v0.1 (task 017, mapa §13.10/§13.235)

**Data:** 2026-10-22 · **Executor:** task-executor (GLM-5.3-Flash via `~/sd2-llm.sh`)
**Fonte normativa:** `fase2/documentos/04_mapa_completo_do_sistema.md` (INTOCADO)
**Formato de referência:** `fase2/documentos/08_mapa_completo_da_testagem.md` (etapa 8)

## 1. Estatuto deste relatório

Este relatório cobre o **aceite funcional** do mapa §13.235 (último parágrafo
do §13) e o ensaio longitudinal offline do §13.8, com evidência executável ou
de inspeção. Ele **não** é o relatório da etapa 8: a suíte quantitativa do
mapa de testagem (oráculos O01–O18, condições `MA_FULL`/`SA_EQUIVALENT`/
ablações, seeds 0..4, splits e clusters, bootstrap pareado, gates com IC) **não
foi implementada nem executada** nesta task — isso é a etapa 8 do mapa §13.10.
**Ausência de resultado é declarada como ausência**: nenhuma métrica de
qualidade, recall, precisão, TSR ou custo é alegada aqui. Todos os valores
numéricos citados são defaults de ensaio do mapa §3, nunca resultados medidos.

## 2. O que foi executado (ensaio longitudinal offline)

Protocolo mecânico em dados de teste locais (`eval/ensaio_longitudinal.py`),
cada passo uma invocação separada (pausa/retomada do próprio protocolo; toda
execução local ficou muito abaixo de 10 min). Ambiente: CPU i5-9400F/32 GiB +
runtime do modelo fixado da task 002 (imagem `llama.cpp-prismml:latest`, id
`d88136167019…`, build `b1-8444536`, candidato Bonsai 2 PTQ1_0, SHA
`53107f…ee3` conferido — **modelo inalterado, não substituído**), GPU RTX 3060
livre nesta data; embedder denso **BGE-M3 real** (revisão
`5617a9f61b028005a4858fdac845db406aefb181`); extrator **Docling real**
(2.141.0, pin do `uv.lock`). Sem rede externa: `network_enabled=false`,
busca `CONNECTOR_DISABLED`.

| # | Passo | Resultado observado (evidência executável) |
|---|---|---|
| 0 | `setup` | fixture mecânica: usuário/disciplina/tópico no domínio (registrada como privilégio de harness) |
| 1 | `doctor` | `configured` p/ modelo; SQLite 3.53.1 WAL ok; integridade domínio+checkpoints ok; `timezone: null` |
| 2 | `ingest` | PDF de teste real extraído pelo **Docling em subprocesso** (spawn, RLIMIT_AS 4 GiB); 3 fatos candidatos, **2 ambíguos → gate de confirmação (§6.3)**; retomada `{"confirmed": true}` → completado; índice denso **BGE-M3** publicado (28 s) e versão ativada após indexação completa (§6.1) |
| 3 | `ask` | turno `explain` com o modelo real: completado, resposta ancorada no documento; **0 citações emitidas** (observado; validador não permite citação fictícia — §6.8) |
| 4 | `practice` | item quiz publicado com gabarito/rubrica separados, terminal `waiting_student` (espera = fim da invocação, §10) |
| 5 | `hint` ×2 | pistas graduadas com o modelo real: `help_level` 1 → 2, item pendente preservado entre turnos (checkpoint) |
| 6 | `submit` | resposta real do "aluno" → monitor **absteve** (`FORMAL_DIVERGENCE`: rubrica multi-critério em item determinístico — fail-closed, nada aprovado parcialmente); `correctness=undecidable` não atualizou competência (§15.2) |
| 7 | `practice` 2º ciclo | com a correção do tutor (item determinístico exige 1 critério), o ciclo de reparo convergiu para rubrica de 1 critério |
| 8 | `submit-known` | gabarito lido do domínio (privilégio de harness registrado) → `correct`, `help_level=0` (independente), tópico → `mixed` (1 tentativa independente correta; `favorable` exige 3 de famílias distintas — não atingido, e não seria com 1 família) |
| 9 | `plan` | 3 demandas pendentes (política v1, duração `estimated` 15 min) → **interrupt de confirmação (§9/§15.3)** → retomada confirmada → solver **OPTIMAL** nas 5 etapas lexicográficas → preview (3 blocos, déficit 0) → espera de aprovação |
| 10 | `approve` | confirmação commitada com digest (`626fb8ef…`), recibo, `outbox_created=false` (sem conector — §9) |
| 11 | `export` | ICS RFC5545 publicado (3 VEVENTs, UTC Z, UID estáveis, SEQUENCE 0, CREATED/LAST-MODIFIED, sem METHOD — §9) |
| 12 | `cancel` | sonda: prática em espera → `/cancel` → terminal **`cancelled`** com `stop_dispatch` e reconciliação de efeitos iniciados (§10) |
| 13 | `crash` | processo do SUT morto com **SIGKILL durante turno em voo** → reabertura: `PRAGMA integrity_check=ok`, domínio autoritativo íntegro → **novo turno na MESMA sessão completou** (checkpoint persistido; commit não duplicado) |
| 14 | `backup`/`restore` | backup consistente (escritores fechados) → restore em diretório NOVO: `integrity=ok`, `migrations_replay=ok`, tombstones conferidos (`0`), tombstone aplicado antes de liberar (§15.1) |
| 15 | `trace`/`state` | 30 traces locais com spans (classify/snapshot/retrieval/context/LLM/commit), sampler e versões registrados (§12); estado final: 16 operações `committed`, `domain_revision=22` |

Evidências JSON por passo: `/tmp/opencode/017/evidencias/` (temporário, não
versionado); o driver do protocolo é entregue em `eval/ensaio_longitudinal.py`.

### 2.1 Correções motivadas pelo ensaio (achados → corrigidos nesta entrega)

1. **Adaptador Docling × API real (2.141)**: `convert` exige `DocumentStream`;
   `iterate_items` devolve tuplas `(item, nível)`; proveniência é
   `page_no`. Corrigido em `eduagent/services/ingestion.py` — fecha a
   pendência "smoke real do Docling" herdada da 006/006a.
2. **`fork` × RLIMIT_AS**: com o embedder denso carregado no mesmo processo,
   o filho `fork` herdava o estado pesado (torch) e estourava o limite de
   4 GiB de §3. A extração passa a usar `spawn` (filho limpo).
3. **Fiação do extrator**: `RuntimeContext.open` agora usa `DoclingExtractor`
   por default na superfície CLI/API (sem extrator, a versão permanece
   `pending` com impedimento explícito — §6.1/§12). `ingestion.extractor:
   none` desliga.
4. **CLI × manifesto**: a CLI lê o manifesto congelado (`--manifest`, default
   `manifest.json`) e só habilita `json_schema` com a capacidade verificada
   registrada; sem manifesto, capacidade NÃO presumida (mapa §3.1).
5. **`MemoryPack.Origin` × eventos de demanda**: o evento `demand_generated`
   carrega `origin='review_after_error'` e o enum do §4 não o aceita — sem
   correção, TODO turno posterior com recuperação de memória falhava
   (INTERNAL_FAILURE). Mapeamento explícito para a origem do §7
   (`INFERRED`/`ASSERTED`), desconhecido → `observed` (default já usado).
6. **Reuso de `operation_id` entre turnos**: `operation_ids` persistem no
   estado da sessão; o `setdefault` reusava o ID do turno anterior na mesma
   sessão e o segundo submit/plan falhava com "digest do replay difere"
   (§11). IDs de operação passam a ser derivados do `turn_id` (estáveis
   dentro do turno para retomada de interrupt, distintos entre turnos).
7. **Item determinístico não avaliável**: o modelo real gerava rubricas
   multi-critério para itens quiz; o Monitor determinístico absteve sempre
   (`FORMAL_DIVERGENCE`) — publicação de item sistematicamente não avaliável
   era saída parcial disfarçada. O tutor agora exige **exatamente 1 critério**
   na rubrica do item determinístico (violação entra no ciclo de reparo, §12).

### 2.2 Impedimentos registrados (não encurtados silenciosamente)

- **OCR seletivo (§6.2) — não executável no limite de §3 neste ambiente**:
  (a) o código `por` prescrito pelo mapa não é servido pelo motor OCR
  instalado (EasyOCR usa `pt`; tesseract não está no stack do MVP) — o
  mapeamento de código é decisão pendente, não tomada aqui; (b) com `pt`, o
  reconhecedor de página inteira tenta alocar ~1,14 GB e o subprocesso de
  4 GiB (§3) recusa (`DefaultCPUAllocator … Cannot allocate memory`) — o
  adaptador falha tipado (`INTERNAL_FAILURE`), versão nunca fica `indexed`
  parcial. Texto **nativo** foi exercitado no smoke real (ocr_source=None por
  bloco). A viabilidade do OCR de página inteira (DPI/pipeline/motor/memória)
  fica para calibração em validação — **registrada como impedimento, não
  como sucesso**.
- **Citações no turno `explain`**: com o perfil congelado, o modelo não emitiu
  citações documentais nos turnos de pergunta do ensaio (0 citações). O
  validador recusa citação não resolúvel (provas nas suítes 007/014) e a
  abstinência de citação não gera citação fictícia (§6.8). A qualidade de
  citação/ancoragem é medida da etapa 8 (O03/O04) — não alegada aqui.
- **Comparativo thinking**: não executado (orçamento de tokens de pensamento;
  mapa §3.1 o restringe a desenvolvimento). Non-thinking congelado.
- **Timezone**: sem confirmação explícita — permanece `null`; horizonte e
  disponibilidade operam em UTC (escolha de ensaio).

## 3. Aceite funcional do mapa §13.235 — item a item

| Item do aceite | Evidência |
|---|---|
| Cada rota termina com estado definido | Ensaio: ingest (waiting→confirmed→completed), ask/practice (waiting_student), submit (completed/abstain), plan (waiting→completed), export, cancel (`cancelled`), crash (failed→recuperação). Suíte: `tests/test_task014_graph.py` (rotas R-I1…R-X2), limites L-T1/L-B1/L-Q1 (terminais tipados com artefatos válidos) |
| Cada artefato cumpre o contrato §4 | `tests/test_task003_contracts.py` + `003a`; export dos JSON Schemas verificado; estado final de cada turno validado por `_contract_state` (falha = `INTERNAL_FAILURE`, nunca terminal fora do contrato — observado no ensaio ao recusar sessão não-UUID) |
| Toda citação `[doc_id@version:página:bloco]` resolve | `tests/test_task007_retrieval.py` (citação resolvível; citação fora do pack recusada) + `test_task014_graph.py` R-A1; no ensaio nenhuma citação foi emitida (registrado em §2.2) |
| Toda escrita tem recibo/versionamento | `tests/test_task005_effects.py` (commit idempotente, crash/replay com `os._exit(137)`); ensaio: 16 operações `committed`, recibo de aprovação com digest; achado 6 corrigido (IDs por turno) com regressão `test_o2` |
| Nenhum plano sem validação do verificador é publicado como aprovado | `tests/test_task012_solver_verifier.py` + `012a` (verificador independente separado); rota approve recusa plano sem `validation.passed` (R-AP1); ensaio: preview OPTIMAL com provas por etapa antes da aprovação |
| Nenhum ICS sem plano confirmado | `tests/test_task013_calendar_confirmation.py` (R-E1 recusa sem plano confirmado); ensaio: ICS só após aprovação commitada |
| Sessão retomada preserva item/ajuda/histórico | `tests/test_task014_graph.py` CK-1/CK-2; ensaio: pistas 1→2 entre invocações separadas com item pendente preservado; recuperação pós-SIGKILL na mesma sessão |
| Regra de evidências `insufficient/mixed/favorable` exata | `tests/test_task009_monitor_reducer.py` + `009a`/`009b` (§8/§15.2: 3 independentes/aceitas/decidíveis, corretas, famílias distintas, pós-último erro crítico); ensaio: 1 correta independente → `mixed` (não favorable) |
| Ingestão acima dos limites recusada ou dividida | `tests/test_task006_ingestion.py` + `006a` (páginas além do limite → `RESOURCE_LIMIT`; versão incompleta nunca ativa); ensaio: PDF dentro dos limites, ativação só após indexação completa |
| `MODEL_NOT_ADMITTED` bloqueia tutoria | `tests/test_task015_cli_api.py` (rotas com geração sem backend → erro tipado) + `tests/test_task002*` gate `MODEL_ADMITTED`; ensaio: modelo da task 002 reutilizado, SHA conferido, sem substituição |

## 4. O que fica para a etapa 8 (mapa de testagem) — registrado como ausência

Nada disto foi executado ou implementado nesta task, e nenhum número abaixo
existe neste relatório: suíte quantitativa (O01–O18) e seus oráculos
independentes; testbed (`SUTAdapter`, runner pareado, FaultController,
F01–F24); condições e baselines/ablações do mapa §13.10 (`MA_FULL`,
`SA_EQUIVALENT`, `MA_NO_LONG_MEMORY`, `MA_NO_COMPACTION`, `MA_ALL_SKILLS`,
`MA_REDUCED_SKILL`); seeds 0..4, splits dev/val/test, clusters e auditoria de
parentesco; anotação humana cega e acordo; métricas (TSR, violações, ASR,
custo) com IC/bootstrap; gates e `freeze` do experimento; smoke offline e
restore por snapshot lógico do bundle O18. O ensaio desta task é evidência de
**aceite funcional** (rotas terminam, contratos honrados), não medição de
qualidade, disponibilidade ou eficácia pedagógica.

## 5. Congelamento (mapa §13.10)

`manifest.json` congelado ANTES do ensaio final (seção `congelamento`): perfil
selecionado **non-thinking** `.7/.8/20/min_p=0/presence=1.5` (perfil do gate
G4; comparativo thinking PENDENTE); hashes reais das 5 skills e do catálogo
(§8, conferidos por `sha256sum` e por teste de regressão G-1); hashes do
BGE-M3 (revisão pinada) e dos modelos de layout do Docling usados no smoke
(revisões registradas); `uv.lock` inalterado (SHA `40c5156c…`); modelo Bonsai
2 **inalterado** (SHA `53107f…ee3`); `timezone: null` PENDENTE de confirmação
explícita; reranker NÃO adotado (questão aberta); busca `CONNECTOR_DISABLED`
(questão aberta). Versões de pacotes reconferidas por `importlib.metadata` na
data do congelamento. Defaults numéricos continuam sendo escolhas de ensaio.

## 6. Cobertura de testes automatizados da entrega

Suíte integral: **591 passed** (581 do piso + 10 novos em
`tests/test_task017_congelamento.py`), sem regressões. Testes novos:
G-1…G-4 (congelamento), G-5 (smoke real do Docling, pulado sem modelos em
cache — sem download em ambiente de revisão), M-1/M-2 (origem de política no
pacote de memória), O-1/O-2 (ID de operação por turno; dois submits na mesma
sessão) e o teste do subprocesso com `spawn`.
