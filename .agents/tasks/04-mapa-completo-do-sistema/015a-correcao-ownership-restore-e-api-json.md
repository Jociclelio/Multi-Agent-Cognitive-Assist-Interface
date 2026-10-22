# Task 015a: Correção da 015 — ownership de sessão, tombstones no restore, confinamento de caminhos e JSON da API

Estado: aguardando subtasks (decisão `corrigir` — subtask 015b pendente de criação)
Depende de: 015
Origem: task mãe 015 — correção (decisão `corrigir`, revisão com quórum GLM 8/10, qwen3-27b 7/10, gpt-6-luna 7/10)

## Prompt
Corrigir pontualmente a entrega da task 015 (commit `429a5cd`, preservado sem reversão; design aprovado). Itens obrigatórios, com as sondas da revisão como prova antes/depois:

1. **Ownership usuário↔sessão (achado alto, GLM-A1, sonda reproduzida em `/tmp/opencode/rev015/p1`)** — `resume` (CLI `eduagent/cli.py:453-482` e API `eduagent/api.py:223-236`) e `cancel`/`approve` aplicam efeitos de sessão de outro usuário: usuário B autenticado resuma a sessão de A (gate `waiting`) e aplica a deleção de A. Antes de retomar/cancelar/aprovar, verificar que a sessão (thread do checkpoint) pertence ao usuário autenticado — o estado do grafo tem `user_id`; recusar com erro tipado de permissão (sem aplicar efeito) na API e na CLI. Cobrir o precedente A1 da 014a (mesma classe de falha).
2. **Tombstone antes de liberar restore cobre backup pré-deleção (achado médio, qwen-A1, sonda reproduzida em `/tmp/opencode/reviewer-015/probe_a_tombstone.py`)** — `eduagent/services/backup.py:452-455` confronta tombstones apenas com o manifesto do próprio backup; backup que **antecede** a deleção é restaurado com o payload tombstonado vivo. No restore, confrontar os refs do conjunto restaurado com os tombstones do domínio **corrente** (ou recusar entradas do catálogo pendentes por deleção de usuário), de modo que nenhum ref tombstonado resolva vivo no conjunto liberado; recusa tipada com diretório descartado.
3. **Confinamento de caminhos no restore (achado alto, luna-A1, leitura de código — reproduzir sonda)** — `eduagent/services/backup.py:406-412` usa `relative` do manifesto diretamente em `directory / relative` e `target_root / relative`, sem recusar caminhos absolutos ou componentes `..`. Validar cada caminho do manifesto como relativo e confinado à raiz esperada antes de verificar ou copiar; recusar manifesto malicioso com erro tipado e descartar o diretório. Reproduzir a sonda do achado antes da correção (manifesto adulterado com `../` e caminho absoluto) e fixar com testes de traversal e caminho absoluto.
4. **API responde JSON em falha interna (achado médio, qwen-A2, sonda reproduzida em `/tmp/opencode/reviewer-015/probe_b_api.py`)** — exceção fora do contrato (`ValueError` de UUID malformado em `POST /turns`) escapa dos handlers (`eduagent/api.py:174-201`, só capturam `EduAgentError`) e encerra a conexão sem corpo. Envolver o dispatch em captura genérica respondendo `{"status": "failed", "error": {"code": "INTERNAL_FAILURE", ...}}` com status HTTP 500, espelhando o mapeamento existente; teste com payload que provoque exceção fora do contrato.
5. **Exit code 3 para recurso configurado ausente (GLM-A2 médio + qwen-A5 baixo)** — sem embedder/modelo, a rota sai `INTERNAL_FAILURE`/exit 4 (`eduagent/graph.py:1372-1375` e `_require_service`, herdado da 014). Mapear ausência de recurso configurado para a classe 3 do §12 (código que saia em exit 3, ex. `MODEL_NOT_ADMITTED`/`SERVICE_UNAVAILABLE`) **ou** registrar explicitamente como escolha local de mapeamento §12 com justificativa; alinhar o teste CLI-3 conforme a escolha.
6. **Teste negativo do verificador de tombstones (GLM-A3 médio)** — `test_tombstone_antes_do_restore` só valida restore legítimo; acrescentar o teste de recusa (ref tombstonado vivo → recusa com `INTERNAL_FAILURE` e diretório descartado), que é o caminho que a evidência do C3 da 015 alega.

Itens baixos (corrigir quando triviais, senão documentar a escolha): (a) falha de geração não publica evento ao observador do trace — `_notify(None, exc)` é no-op (`eduagent/policy.py:339,343` vs `:352-356`; construir evento de erro nos ramos de exceção, como `_notify_queue_refusal`); (b) categoria `queue` nunca emite span (`eduagent/telemetry.py:80-88`) — emitir span de fila por evento de geração a partir do observador **ou** documentar a escolha "fila como métrica por geração" no registro da 015; (c) docstring de `eduagent/api.py:10` promete 401 e a implementação devolve 400 — alinhar; (d) `from __future__ import annotations` duplicado em `eduagent/cli.py:27-29`.

Restrições: preservar o design e a entrega da 015; tocar apenas `eduagent/` e `tests/`; mapa, `config/`, `docs/` e submódulo intocados; sem dependência nova (`uv.lock` inalterado); nada apresentado como resultado medido; temporários em `/tmp/opencode`. Commits SEPARADOS: entrega (código) e registro (task.md com SHAs/evidências). Suíte integral deve permanecer verde (521 passed no momento, mais regressões novas) sem quebrar os 490 testes anteriores; sondas dos achados reproduzidas antes e depois da correção.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §12 (exit codes, JSON com status, contexto autenticado); §15.1 (tombstones antes de liberar restore); §15 prevalece quando mais preciso. INTOCADO.
- `.agents/tasks/04-mapa-completo-do-sistema/015-cli-e-api-loopback.md` — task mãe com a Revisão completa (achados e sondas) e a entrega original.
- `.agents/tasks/04-mapa-completo-do-sistema/014a-correcao-seguranca-paths-fetch-e-limites.md` — precedente de ownership de paths (classe A1).
- `eduagent/services/backup.py`, `eduagent/api.py`, `eduagent/cli.py`, `eduagent/graph.py`, `eduagent/policy.py`, `eduagent/telemetry.py`, `tests/test_task015_cli_api.py` — alvos da correção.

## Corretude
- [x] C1 — Sonda de ownership reproduzida antes/depois: usuário B autenticado não consegue `resume`/`cancel`/`approve` em sessão de A (recusa tipada, sem efeito aplicado); regressões novas na suíte da 015 cobrindo os três comandos pela API e pela CLI.
- [x] C2 — Sondas de restore reproduzidas antes/depois: (a) backup pré-deleção + delete + restore → recusa tipada com diretório descartado, payload tombstonado não ressuscita; (b) manifesto adulterado com `../` e caminho absoluto → recusa tipada; testes de regressão para os dois caminhos negativos e para o teste de recusa do verificador de tombstones (item 6).
- [x] C3 — API responde JSON com `status: failed` e `INTERNAL_FAILURE` em exceção fora do contrato (teste com payload que provoque `ValueError` fora dos handlers); item de exit code 3 resolvido com teste alinhado ou escolha documentada no registro; itens baixos corrigidos com teste ou documentados.
- [x] C4 — Suíte integral verde (521 anteriores + regressões novas, sem quebrar 490+31); entrega em commit de código separado do registro; mapa, `config/`, `docs/` e submódulo intocados; `uv.lock` inalterado.

## Execução
- Modelo: GLM-5.3-Flash (provider `sd2`, model id `GLM-5.3-Flash`, via `~/sd2-llm.sh`) — identidade informada pelo runtime da sessão.
- Base: `95c21af6ae93b360ab4ef945ada779946c10390d` (árvore limpa, pós-criação da subtask; entrega da 015 `429a5cd` preservada sem reversão).
- Entrega: `e17cbf05e8b9e8de70ee372c842e41e926924372` (commit de código; commit de registro é este, encontrado por `git log -- <task.md>`).
- Arquivos da entrega: `eduagent/graph.py` (ownership usuário↔sessão `_session_owner`/`_require_session_owner` aplicado em `run_turn` e `resume_turn(user_id=...)`; `_require_service` e check de embedder → classe 3 `SOURCE_UNRESOLVED`), `eduagent/cli.py` (resume/approve/delete passam o usuário autenticado ao `resume_turn`; import futuro duplicado removido; nota de mapeamento §12 no `EXIT_CODE_BY_ERROR`), `eduagent/api.py` (resume com ownership; captura genérica do dispatch respondendo JSON `failed`/`INTERNAL_FAILURE` com HTTP 500; docstring 401→400), `eduagent/services/backup.py` (`_validate_manifest_relative` no verificador/cópia/`_relative_domain_name`; `_current_domain_tombstones` confrontado no restore), `eduagent/policy.py` (`_notify` publica evento de erro de geração ao observador), `eduagent/telemetry.py` (span `queue` por evento de geração em `observe_llm`), `tests/test_task015_cli_api.py` (CLI-3 realinhada à escolha §12), `tests/test_task015a_correcoes.py` (novo; 12 regressões OWN-1..4, TOM-1..2, PTH-1..3, API-6, TEL-5..6).

### Evidências (Corretude)

- **Sondas antes/depois (reprodução obrigatória)**:
  - Ownership (GLM-A1, `/tmp/opencode/rev015/probe1.py`, artefatos em `/tmp/opencode/rev015/p1`): ANTES — `resume B (gate de A): 0 {"status": "completed", ... "change_applied": true ...}` (B aplicou a deleção de A); DEPOIS — `resume B (gate de A): 3 {"status": "failed", "error": {"code": "TOOL_DENIED", "message": "sessão de outro usuário: ..."}}`, sem efeito aplicado.
  - Tombstone pré-deleção (qwen-A1, `/tmp/opencode/reviewer-015/probe_a_tombstone.py`): ANTES — `RESTORE PRE-DELECAO: restored; payload vivo no conjunto restaurado? True; CONTEUDO: PAGODO-SECRETO-DELETA-ME`; DEPOIS — recusa `INTERNAL_FAILURE`: "tombstone do domínio corrente violado no restore: event:...@1 (backup anterior à deleção não é restaurável)".
  - API sem JSON (qwen-A2, `/tmp/opencode/reviewer-015/probe_b_api.py`): ANTES — `SEM RESPOSTA JSON — RemoteDisconnected`; DEPOIS — `HTTPError 500 {"status": "failed", "error": {"code": "INTERNAL_FAILURE", "message": "falha interna da API: ValueError: badly formed hexadecimal UUID string", ...}}`.
  - Traversal (luna-A1, sonda criada em `/tmp/opencode/015a/probe_traversal.py` — não existia; manifesto adulterado com SHA-256 REAL): ANTES — `../vazou.txt` restaurado com arquivo escrito FORA da raiz de restore (`traversal/vazou.txt`, fora de `alvo-traversal/`); caminho absoluto resolvia fora do diretório (SameFileError mostrando `directory / relative` == caminho absoluto); DEPOIS — `[traversal] recusa tipada: SCHEMA_INVALID (componente '..')`, `[absoluto] recusa tipada: SCHEMA_INVALID (caminho ABSOLUTO)`, diretório alvo descartado nos dois casos.
- **C1 (ownership)**: coberto pelos três comandos na CLI e na API — OWN-1 (B não resume gate de A via API, 403 TOOL_DENIED; A retoma), OWN-2 (B não cancela sessão de A; A cancela depois, estado intacto), OWN-3 (B não confirma deleção de A via CLI `resume --data`, exit 3; A confirma e o efeito é aplicado pelo dono), OWN-4 (B não aprova sessão de A, exit 3). Verificação no grafo (`run_turn` e `resume_turn`) cobre CLI e API de uma vez, ANTES de qualquer escrita no thread.
- **C2 (restore/tombstones/traversal)**: TOM-1 (backup pré-deleção + delete + restore → `INTERNAL_FAILURE` com "domínio corrente" e diretório descartado), TOM-2 (teste negativo do verificador: ref tombstonado vivo no manifesto → `INTERNAL_FAILURE`, diretório descartado — item 6), PTH-1/PTH-2 (manifesto com `..` e caminho absoluto, com hash real → `SCHEMA_INVALID`, diretório descartado), PTH-3 (o verificador `verify_backup` recusa por código antes de qualquer cópia).
- **C3 (API JSON + exit 3 + baixos)**: API-6 (exceção fora do contrato → JSON `status: failed`, `INTERNAL_FAILURE`, HTTP 500); item 5 resolvido por MAPEAMENTO (escolha local §12 documentada em `_require_service`, `EXIT_CODE_BY_ERROR` e no teste CLI-3 realinhado: recurso configurado ausente → `SOURCE_UNRESOLVED` → exit 3, classe "recurso/conector indisponível"; justificativa: o mapa §4 não tem código `SERVICE_UNAVAILABLE`, e ausência de recurso declarada não é falha interna); baixo (a) TEL-5 (falha de geração publica evento com `error` ao observador, mesma forma da recusa de fila); baixo (b) TEL-6 (span `queue` emitido por evento de geração com `active_s` medido e atributo com a razão dos instantes absolutos); baixo (c) docstring da API alinhada a 400 (recusa por código `SCHEMA_INVALID`; o mapa §4 não define status HTTP — escolha mantida, documentação corrigida); baixo (d) import futuro duplicado removido.
- **C4 (intocabilidade e commits)**: `git status`/`git diff --stat` confirmando alteração somente em `eduagent/` e `tests/`; `fase2/` (mapa), `config/`, `docs/` e `uv.lock` sem diff; submódulo `docs/playground-llmagenticsystem` intocado; commit de entrega separado do registro.

### Verificações executadas

- Suíte integral ANTES: `.venv/bin/python -m pytest tests/ -q` → **521 passed** (baseline reproduzida).
- Suíte integral DEPOIS: → **533 passed** (521 anteriores + 12 regressões da 015a), 2 warnings pré-existentes (fork em subprocesso da 006), sem regressões nas 490+31 anteriores.
- Compilação dos módulos alterados: `py_compile` OK.

### Escolhas documentadas (não são resultados medidos)

- Recurso configurado ausente (serviço/embedder/modelo não configurado) é **classe 3 do §12** via `SOURCE_UNRESOLVED` (exit 3; HTTP 404 no mapa local da API): o conjunto de códigos do §4 é fechado e não possui `SERVICE_UNAVAILABLE`; ausência de recurso configurado é indisponibilidade declarada, não falha interna. Teste CLI-3 realinhado conforme a escolha (permitido pelo item 5 da task).
- Recusa de ownership usa `TOOL_DENIED` (§4/§10: "ação proibida é negada por código, nunca interpretada"; mesmo precedente de ownership de paths da 014a) → exit 3 na CLI, HTTP 403 na API.
- Confinamento do manifesto usa `SCHEMA_INVALID` (manifesto malicioso é entrada inválida) → exit 2 na CLI, HTTP 400.
- Span de fila: emitido por evento de geração a partir do observador (opção "emitir" do item baixo b); instantes absolutos da janela de fila não são conhecidos no recorder — registrado como atributo com a razão, duração `active_s` medida pelo servidor loopback.

### Limitações e pendências registradas

- O confronto com tombstones do domínio corrente lê `data_root/domain.sqlite` somente-leitura no restore; sem banco corrente (raiz isolada), não há tombstones a confrontar (registrado no docstring).
- `resume_turn` aceita `user_id=None` (chamadas internas/testes da 014 sem contexto); CLI e API sempre passam o usuário autenticado — a lacuna não é alcançável pelas interfaces do §12.

### Dificuldade sentida
3/10 — Correções pontuais com sondas que reproduziram de primeira; os únicos atritos foram calibrar a sonda de traversal (o manifesto precisa do SHA-256 REAL do arquivo plantado, senão a recusa vem do verificador de hash e não do confinamento) e construir o gate de espera para o teste de approve (practice exige tópico e evidência). A escolha do código de erro para ausência de recurso exigiu decisão explícita dentro do conjunto fechado do §4, documentada acima.

## Notas

### Dificuldade esperada
3/10 — Correções pontuais e locais com sondas já descritas pela revisão; maior cuidado no confronto de tombstones com o domínio corrente sem quebrar o restore legítimo da 015.

### Dificuldade sentida
3/10 — Registrada pelo executor na seção Execução (calibração da sonda de traversal com SHA-256 real e construção do gate de approve).

### Revisão
- Orquestrador: GLM-5.3-Flash (provider `sd2`) — master do ciclo opt-in, sessão dedicada.
- Alvo: entrega `e17cbf05e8b9e8de70ee372c842e41e926924372` sobre base `95c21af6ae93b360ab4ef945ada779946c10390d`, registro `6f4b385`; árvore limpa e inalterada durante a rodada (confirmado por `git status`/`git log` antes, entre e após os pareceres).
- Avaliações (quórum completo, três modelos distintos, rodada **sequencial** — motivo: os revisores precisam rodar a suíte integral no venv compartilhado do repositório, uso concorrente que se interferiria em paralelo):
  - GLM-5.3-Flash — 9/10, recomenda **fechar**. C1–C4 provados (sondas próprias de ownership/traversal/tombstone/API em `/tmp/opencode/rev-015a-glm/`, suíte 533 passed reproduzida em 28,4 s, isolamento do diff confirmado). Residuais baixos: guard ausente para `user_id=None` em `run_turn` (latente), janela do span `queue` compensada por atributo com a razão, mensagem de exceção interna exposta ao cliente (aceitável no MVP local).
  - qwen3-27b — 9/10, recomenda **fechar**. Sondas da própria revisão da 015 re-executadas (`probe_a_tombstone.py`, `probe_b_api.py`) mais sonda independente de ownership; suíte 533 passed reproduzida (28,7 s); divergência factual nenhuma. Residuais: F1 (baixo) `except sqlite3.Error: return []` em `_current_domain_tombstones` degrada silenciosamente o confronto se o banco corrente existir mas estiver corrompido — recomenda mesmo assim "registrar a anomalia ou recusar, em vez de `[]` mudo"; F2 (baixo) `resume_turn(user_id=None)` documentado e não alcançável pelas interfaces do §12.
  - gpt-6-luna — 8/10, recomenda **corrigir**. C1 e C2 classificados provisórios (não reproduziu sondas adversariais; C3 e C4 provados por leitura e suíte 533 passed). Achado A1 (**alto**): o mesmo fail-open de `backup.py:544-545` — banco corrente presente porém ilegível faz o restore prosseguir sem confrontar tombstones, podendo restaurar payload excluído; exige recusa tipada com descarte do destino, reservando lista vazia apenas para ausência documentada do banco.
- Síntese: convergência factual total — os três confirmam os seis itens obrigatórios e os quatro baixos implementados, a suíte 533 passed (521 + 12 regressões), o isolamento do diff (apenas `eduagent/` e `tests/`; mapa, `config/`, `docs/`, submódulo e `uv.lock` intocados) e a separação entrega/registro. Nenhuma divergência factual. A única divergência é de severidade no fail-open de `_current_domain_tombstones`: GLM e qwen classificam baixo (caso de borda, sem regressão em fluxo normal), luna alto. A decisão acolhe a posição mais rigorosa: o critério C2 desta task estabelece garantia absoluta ("nenhum ref tombstonado resolva vivo no conjunto liberado"), §15.1 prevalece quando mais preciso, o restore é precisamente o caminho de recuperação em que corrupção do banco vivo é plausível, e até o revisor que classificou baixo recomenda a recusa — a pendência não pode ser escondida atrás da nota.
- Nota final: 8/10 — entrega sólida e provada em quase sua totalidade, com um fail-open residual num controle de privacidade do caminho de recuperação que exige correção delimitada antes do fechamento da família.
- Parecer: aprovada com ressalva obrigatória — todos os itens do prompt implementados e provados por sondas antes/depois e regressões; falha de fail-closed no confronto com tombstones do domínio corrente quando o `domain.sqlite` corrente existe mas não pode ser consultado.
- Decisão: `corrigir` — entrega `e17cbf0` preservada sem reversão (design aprovado; correção é pequena e local).
- Reversão: não se aplica — entrega preservada.
- Próximo passo: criar a subtask 015b (fail-closed do confronto com tombstones do domínio corrente em `eduagent/services/backup.py`: recusa tipada com diretório descartado quando o banco corrente existe mas não pode ser consultado; lista vazia apenas para ausência documentada; teste de regressão com banco corrente corrompido/ilegível provando a recusa). Família: 011-demandas-atividades-e-politica-evidencia.md.

<!-- task-cycle: {"decision":"corrigir","next_task":".agents/tasks/04-mapa-completo-do-sistema/015b-correcao-fail-closed-tombstones-correntes.md","family":".agents/tasks/04-mapa-completo-do-sistema/011-demandas-atividades-e-politica-evidencia.md","plan":".agents/plans/04-mapa-completo-do-sistema/plan.md"} -->

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
