# Task 015: CLI mínima, API loopback e observabilidade (mapa §12, §13.8 parte 2)

Estado: aguardando revisão
Depende de: 014
Origem: nenhuma

## Prompt
Implementar a interface e a observabilidade (mapa §12) em `eduagent/cli.py`, `eduagent/api.py` e `eduagent/telemetry.py`: CLI mínima com `doctor, ingest, ask, practice, submit, plan, approve, export, resume, cancel, trace, backup, restore, delete`; API loopback com POST `/turns`, POST `/turns/{id}/resume`, POST `/turns/{id}/cancel`, GET `/artifacts/{id}`, GET `/health`; escrita exige contexto de usuário autenticado localmente. Exit codes: 0 sucesso/espera legítima, 2 entrada ambígua/inválida, 3 recurso/conector indisponível, 4 falha interna; JSON sempre contém status. Trace local por turno com spans de fila/LLM/retrieval/context/solver/commit/tools; registrar versões, seed/sampling, counts entrada/raciocínio/saída quando disponíveis, status/truncamento, tempo ativo/fila/total, RSS/VRAM e erros; não logar payload pessoal completo por padrão; métricas desconhecidas ficam `null` com razão, nunca zero; custo local: tokens/segundos/energia quando medidos, com amortização documentada; custo API apenas se conector pago usado. Backup: fechar escritores/checkpointer, consolidar e copiar conjunto consistente com originais/manifesto; restore em diretório novo com verificador de integridade/replay; exclusão ativa imediata com backups pendentes até expiração (30 dias propostos), tombstone sem payload aplicado **antes** de liberar restore, remoção de backup com apenas usuário excluído já na solicitação; CLI mostra escopo/prazo, sem alegar sanitização forense; expiração verificada por job/doctor com relógio e catálogo (§15.1). `doctor` reporta saúde do modelo/DB/índices/config.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §12 integral; §15.1 (backup/tombstones); §13.8.
- Grafo (014), storage (004/005).

## Corretude
- [x] C1 — Todos os comandos CLI e endpoints funcionam contra o grafo; exit codes e JSON com status conforme mapa (tabela de testes por comando).
- [x] C2 — Traces por turno com spans listados; payload pessoal não logado por padrão; métrica desconhecida = null com razão (teste).
- [x] C3 — Backup consistente + restore em diretório novo com verificação; tombstone antes do restore; expiração com catálogo (testes).
- [x] C4 — Mapa intocado; commits separados; submódulo não tocado.

## Execução

- Identidade real do modelo: GLM-5.3-Flash (provider `sd2`, model id `GLM-5.3-Flash`, via `~/sd2-llm.sh`) — identidade informada pelo runtime da sessão.
- Base: `3f31a473a85b09def07673301bcce3bb075b466c` (árvore limpa, pós-revisão da 014a).
- SHA de entrega: `429a5cd` (commit de código; commit de registro é este, encontrado por `git log -- <task.md>`, sem SHA próprio em si).
- Artefatos da entrega: `eduagent/cli.py`, `eduagent/api.py`, `eduagent/telemetry.py`, `eduagent/runtime.py` (novo), `eduagent/services/backup.py` (novo), `eduagent/graph.py` (spans por nó + trace no TurnResult), `eduagent/policy.py` (observador do GenerationGate), `eduagent/services/model_adapter.py` (instrumentação de fila/tempo do servidor loopback), `eduagent/storage/repository.py` e `eduagent/storage/checkpoints.py` (`path` público + `checkpoint_wal()` para o backup), `tests/test_task015_cli_api.py` (novo).

### Evidências (Corretude)

- **C1 (comandos/endpoints, exit codes, JSON com status)**: 31 testes de aceite novos (`tests/test_task015_cli_api.py`), tabela de casos no cabeçalho do arquivo (CLI-1…CLI-13, TEL-1…TEL-4, API-1…API-5, BKP-1…BKP-6). Os 14 comandos do §12 existem no parser (`test_quatorze_comandos_do_mapa`); ingest → exit 0 com `version_status=indexed`; practice → exit 0 waiting (espera legítima); submit → exit 0 com feedback; export sem plano → exit 3; cancel → exit 0 `cancelled`; sem `--user` → exit 2; usuário inexistente → exit 3; erro fora do contrato do §4 → exit 4 com `INTERNAL_FAILURE`; JSON de toda saída contém `status`. API loopback: `/health` 200; `POST /turns` sem `X-EduAgent-User` → 400 com erro tipado (escrita exige contexto autenticado, §12); `/turns`, `/turns/{id}/resume`, `/turns/{id}/cancel` executam contra o grafo; `/artifacts/{id}` serve ICS do próprio usuário via `resolve_owned_path` e 404 para id desconhecido. Smoke real do `doctor` executado fora da suíte (data-root temporário em `/tmp/opencode/task015-smoke`, exit 0, config real de `config/default.yaml` carregada com `timezone: null` preservado).
- **C2 (traces, redação, null com razão)**: spans por nó nas 7 categorias do §12 com mapeamento nó→categoria explícito (não listado vai a `tools` com o nó no span, sem alegar categoria); span de fila medido no `LoopbackGenerationServer` (enqueue→execução) publicado ao recorder via observador do `GenerationGate` (falha de telemetria isolada do turno); contagens de entrada/saída registradas quando o backend as reporta (`test_contagens_llm_quando_disponiveis`), raciocínio sempre `null` com razão (runtime não reporta contagem); mensagem registrada apenas como SHA-256 + tamanho — conteúdo nunca entra no trace (`test_payload_pessoal_nao_logado`); VRAM/energia/custo de API sempre `null` com razão, nunca zero (`test_metrica_desconhecida_null_com_razao`); trace gravado como JSON por `trace_id` fora do estado do grafo e do checkpoint; comando `trace` lista/mostra os traces gravados.
- **C3 (backup/restore/tombstones/expiração)**: backup fecha checkpointer e escritor do domínio com `wal_checkpoint(TRUNCATE)` antes da cópia (§5), copia bancos + árvore de dados com manifesto SHA-256 e catálogo; verificação recalcula hashes e roda `integrity_check`; restore é recusado em diretório com conteúdo, copia para diretório NOVO e roda verificador de integridade + replay idempotente das migrações, descartando o diretório em qualquer falha; tombstone vale ANTES de liberar o restore — ref tombstonado vivo (evento com payload não-purgado, fato/resumo presentes) recusa o restore com `INTERNAL_FAILURE` (`test_tombstone_antes_do_restore`); exclusão ativa imediata: backup que contém apenas o usuário excluído é removido já na solicitação e demais ficam pendentes até expiração com retenção PROPOSTA de 30 dias rotulada como default de ensaio; expiração verificada por relógio + catálogo no `expire_due` e via `doctor` (`test_expiracao_via_doctor`); relatórios mostram escopo/prazo e declaram não alegar sanitização forense.
- **C4 (intocabilidade e commits)**: `git status`/`git diff` confirmando `fase2/` (mapa), `config/` e `docs/` sem alteração; submódulo `docs/playground-llmagenticsystem` intocado; `uv.lock` inalterado (nenhuma dependência nova — API/backup/telemetria usam só biblioteca padrão + pyyaml já pinado); commit de entrega separado do commit de registro.

### Verificações executadas

- Suíte integral: `.venv/bin/python -m pytest tests/ -q` → **521 passed** (490 da entrega anterior + 31 novos), 2 warnings pré-existentes (fork em subprocesso da 006), sem regressões.
- Compilação dos módulos alterados: OK.

### Limitações e pendências registradas (não são resultado medido)

- O `doctor` do MVP não executa o gate de modelo (§13.1) — reporta apenas o verificável localmente e diz o que não foi validado; o congelamento do perfil no manifesto é da task 017.
- Sem embedder configurado (`--embedder-dir`), a rota ask/practice recusa com erro tipado; sem `--model-url`, a tutoria é bloqueada com erro tipado (tutoria exige modelo admitido, §3.1).
- Contagem de raciocínio e energia/VRAM/custo ficam `null` com razão — nenhum medidor no processo local; nada aqui é apresentado como resultado medido.
- Exit code 3 cobre `VERSION_CONFLICT`/`TIMEOUT` por mapeamento local documentado (o mapa fixa as quatro classes, não o destino de cada código).

## Notas

### Dificuldade esperada
4/10 — Superfície ampla mas mecânica; risco em backup/restore consistente.

### Dificuldade sentida
5/10 — Superfície ampla mesmo sendo mecânica: o ponto de maior atrito foi alinhar backup/restore ao comportamento real da deleção da 010 (evento purgado permanece como linha com payload `NULL`, então "tombstone violado" precisa distinguir linha purgada de ressurreição — primeira versão do verificador recusava restore legítimo) e integrar o trace ao grafo sem tocar o estado/checkpoint (spans exigiram mapear `_node_*` para nomes de rota e instrumentar a fila do servidor loopback trocando o segundo elemento do Future de `"ok"` por metadados de tempo — compatível com os usos da 002/014). Ajustes de integração CLI↔grafo (course/topic obrigatórios nas rotas, gates de confirmação por resume) consumiram iterações de teste, mas sem dúvida de design.

### Revisão
- Orquestrador: GLM-5.3-Flash (provider `sd2`) — master do ciclo opt-in; três rodadas de revisão sequencial (um revisor por vez) porque a revisão executa a suíte pytest no `.venv` compartilhado e grava temporários comuns — recursos compartilhados que se interferem; motivo registrado conforme contrato.
- Alvo: entrega `429a5cd` sobre base `3f31a473a85b09def07673301bcce3bb075b466c`; registro `522e997`; árvore confirmada limpa e inalterada durante a rodada.
- Avaliações (quórum completo, três modelos distintos):
  - GLM-5.3-Flash (`sd2`) — **8/10**, requer correções. Suíte 521 passed reproduzida. **A1 alto (sonda reproduzida)**: `resume`/`approve`/`cancel` sem vínculo usuário↔sessão — usuário B autenticado resume sessão de A e aplica a deleção de A sob contexto de B (`api.py:223-236`, `cli.py:453-482`, `graph.py:984`; precedente A1 da 014a). A2 médio: recurso local ausente (sem embedder) sai exit 4 em vez de 3. A3 médio: caminho negativo do verificador de tombstones sem teste (evidência do C3 superestimada; comportamento em si correto por sonda). Baixos: span `queue` nunca emitido; erro de geração não publica evento LLM; docstring 401 vs 400.
  - Qwen3.8 27B (`sorgan-qwen`) — **7/10**, requer correções. Suíte 521 passed reproduzida. **A1 médio (sonda reproduzida)**: restore de backup **pré-deleção** ressuscita payload tombstonado — verificação de tombstones cobre só o manifesto do próprio backup, não o domínio corrente (`backup.py:452-455`). **A2 médio (sonda reproduzida)**: exceção fora do contrato na API (`ValueError` de UUID) encerra a conexão sem JSON, quebrando "JSON sempre contém status" em falha interna (`api.py:174-201`). A5 baixo: modelo não configurado → exit 4 em vez de 3 (código herdado da 014, cristalizado por teste novo). Baixos: mesmo span `queue` ausente; erro de geração não chega ao observador.
  - GPT-6 Luna (`openai`) — **7/10** (provisória quanto a comportamento sem teste adversarial), requer correções. Suíte em árvore isolada: 520 passed, 1 skipped. **A1 alto**: caminhos `relative` do manifesto usados diretamente em `directory / relative` e `target_root / relative` sem recusar absolutos ou `..` — manifesto malicioso permite leitura/escrita fora da raiz de restore (`backup.py:406-412`); sonda end-to-end não executada, risco concreto por leitura de código.
- Síntese: convergência dos três vereditos em **corrigir**, sem divergência factual. Achados altos/médios que fundamentam a decisão, todos com evidência: (1) escrita cross-user em resume/approve/cancel (GLM-A1, sonda); (2) restore de backup pré-deleção ressuscita dado tombstonado (qwen-A1, sonda); (3) path traversal via manifesto no restore (luna-A1, leitura de código — verificar por sonda na correção); (4) API sem JSON em falha interna (qwen-A2, sonda); (5) exit 4 para recurso ausente em vez de 3 (GLM-A2 + qwen-A5); (6) teste negativo ausente para o verificador de tombstones (GLM-A3). Baixos a incluir quando triviais: evento de erro de geração não publicado ao observador (qwen-A3/GLM-A5), span `queue` ausente ou documentado (GLM-A4/qwen-A4), docstring 401 vs 400 e `from __future__` duplicado (GLM-A6). Suíte integral verde nos três (521/521/521+1 skip ambiental); C4 (intocabilidade, commits separados) provado por unanimidade.
- Nota final: **7/10** — entrega ampla, bem documentada e com suíte robusta (31 testes novos, 521 passed reproduzido por dois revisores independentes e 520+1 skip no terceiro), C1/C2/C4 atendidos; C3 incompleto: o invariante "tombstone antes de liberar restore" (§15.1) não cobre backups anteriores à deleção e o restore confia em caminhos do manifesto sem confinamento, além do achado alto de ownership no resume. Pendências essenciais não são escondidas pela nota: os achados 1–4 acima são obrigatórios na correção.
- Decisão: **corrigir** — entrega e design preservados (sem reversão); correção delimitada na subtask 015a.
- Reversão: não se aplica — entrega preservada; nenhum commit revertido.
- Próximo passo: criar subtask 015a (`.agents/tasks/04-mapa-completo-do-sistema/015a-correcao-ownership-restore-e-api-json.md`) cobrindo os achados obrigatórios 1–6 e os baixos triviais; família 011 permanece aberta; task 016 segue bloqueada até resolução.

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
