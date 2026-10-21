# Task 001: Scaffold do projeto e configuração (mapa §3)

Estado: fechada
Depende de: nenhuma
Origem: nenhuma

## Prompt
Criar o esqueleto do EduAgent-OS v0.1 conforme o mapa normativo `fase2/documentos/04_mapa_completo_do_sistema.md` §3: estrutura de diretórios (`eduagent/{api,cli,config,contracts,graph,context,policy,telemetry}.py`, `eduagent/agents/`, `eduagent/services/`, `eduagent/storage/`, `eduagent/skills/{explain,graduated_hint,quiz,flashcard,self_explain}/skill.yaml` como stubs declarativos, `config/default.yaml`, `schemas/`, `data/<user_id>/{originals,derived,indexes,exports}/`, `tests/ fixtures/ eval/`), `pyproject.toml` com Python 3.11+ e dependências pinadas via `uv` (LangGraph, Pydantic v2, Docling, motor OCR, SentenceTransformers/FlagEmbedding, OR-Tools, icalendar, rank_bm25), `uv.lock` gerado, e `config/default.yaml` com TODOS os defaults do mapa §3: `window=32768`, `max_output_tokens=16384`, `tool_reserve=2048`, `margin=1024`, `doc_tokens=4096`, `memory_tokens=2048`, `max_llm_calls=6`, `max_tool_calls=8`, `max_graph_steps=16`, `max_repairs_total=2`, `max_repair_artifact=1`, `active_deadline_s=120`, `llm_timeout_s=90`, `retrieval_top_k=40`, `rrf_k=60`, `rerank_candidates=40`, `evidence_chunks=6`, `solver_budget_s=10`, `slot_minutes=15`, `horizon_days=7`, `seed=0`, `num_workers=1`; ingestão `50 MiB/500 páginas/timeout 600 s/subprocesso 4 GiB`; `network_enabled=false`, `calendar_sync_enabled=false`; `timezone` NÃO fixado (`America/Sao_Paulo` só após confirmação — registrar como pendente). Registrar em Evidências as versões reais resolvidas.

Restrições: mapa intocado; defaults são escolhas de ensaio, não resultados medidos; sem implementar lógica de agentes nesta task (stubs); temporários em `/tmp/opencode`; commits de entrega e de registro separados.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — fonte normativa: §3 (stack, diretórios, configuração). Ler integralmente; "deve" é contrato.
- `.agents/plans/04-mapa-completo-do-sistema/plan.md` — plano aprovado: Escopo e Questões abertas.

## Corretude
- [x] C1 — Estrutura de diretórios e módulos existe conforme mapa §3; `uv sync` (ou equivalente com lock) instala o ambiente; `python -c "import eduagent"` funciona.
- [x] C2 — `config/default.yaml` reproduz todos os defaults numéricos e flags do §3, conferidos item a item; timezone não fixado e pendência registrada.
- [x] C3 — `uv.lock` com pin real das dependências; versões registradas em Evidências (pin é resultado do smoke test, não `latest` presumido).
- [x] C4 — Mapa e plano intocados (`git diff`); commit de entrega (código/config) e de registro (task.md) separados; submódulo não tocado.

## Execução
- Modelo: GLM-5.3-Flash (via ~/sd2-llm.sh; provider `sd2`, model id `GLM-5.3-Flash`)
- Base: 8e5c56b7b0fed5641208b7607e5b5816ef4e9aa1 (árvore limpa)
- Entrega: bf5b81203b547aec82a7e45b80ae2db7e1460dac (commit de entrega único; código/config)
- Arquivos da entrega: `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`, `README-eduagent.md`, `config/default.yaml`, `eduagent/` (8 módulos raiz + `agents/` 5 + `services/` 7 + `storage/` 3 + `skills/` 5 × `skill.yaml`), `schemas/`, `data/<user_id>/{originals,derived,indexes,exports}/` (`.gitkeep`), `tests/`, `fixtures/`, `eval/`
- Evidências:
  - Estrutura: verificação programática dos 38 caminhos do mapa §3 — "faltando: nada — estrutura completa (38/38)". `data/domain.sqlite` e `data/checkpoints.sqlite` são artefatos de runtime (mapa §3), ignorados via `.gitignore` (`data/*.sqlite*`).
  - `uv lock`: "Resolved 168 packages in 1.76s"; `uv sync` concluído em `.venv` (Python 3.12.13 via `.python-version`; interpretador de wheel-availability, não decisão normativa).
  - `uv run python -c "import eduagent"` → `eduagent 0.1.0`. Smoke test de versões reais (importlib.metadata): `langgraph==1.2.16`, `langgraph-checkpoint==4.3.0`, `pydantic==2.14.1`, `docling==2.141.0`, `easyocr==1.7.2`, `sentence-transformers==5.7.0`, `FlagEmbedding==1.4.2`, `ortools==9.15.6755`, `icalendar==6.3.2`, `rank-bm25==0.2.2`, `torch==2.14.1+cpu`, `torchvision==0.29.1+cpu`, `rapidocr==3.10.0` (transitiva do docling); `sqlite3` stdlib 3.53.1.
  - `config/default.yaml`: 25 defaults do §3 transcritos e conferidos dígito a dígito (window 32768; max_output_tokens 16384; tool_reserve 2048; margin 1024; doc_tokens 4096; memory_tokens 2048; max_llm_calls 6; max_tool_calls 8; max_graph_steps 16; max_repairs_total 2; max_repair_artifact 1; active_deadline_s 120; llm_timeout_s 90; retrieval_top_k 40; rrf_k 60; rerank_candidates 40; evidence_chunks 6; solver_budget_s 10; slot_minutes 15; horizon_days 7; seed 0; num_workers 1; network_enabled false; calendar_sync_enabled false; ingestão 50 MiB/500 págs/600 s/4 GiB). Todos rotulados como defaults de ensaio no arquivo.
  - Pendências registradas no YAML: `timezone: null` (America/Sao_Paulo só após confirmação); `reranker_enabled: false` (seleção em validação, mapa §6.6); `search_connector: null` (CONNECTOR_DISABLED, mapa §6); `model_mode: non-thinking` (mapa §3.1; perfil congelado no manifesto em 002/017).
  - Intocabilidade: 0 alterações em `fase2/documentos/04_mapa_completo_do_sistema.md` e `.agents/plans/04-mapa-completo-do-sistema/plan.md`; 0 alterações no submodule `docs/playground-llmagenticsystem`.
  - Correção WAL SQLite (mapa §3): stdlib 3.53.1 > 3.51.3 no interpretador de ensaio; decisão de runtime fica com a task 004 (storage).

## Notas

### Dificuldade esperada
2/10 — Scaffold e transcrição de defaults com conferência dígito a dígito; risco baixo.

### Dificuldade sentida
3/10 — Transcrição dos defaults foi mecânica, mas a resolução do lock exigiu depuração: `[tool.uv.sources]` para o índice CPU do PyTorch foi ignorado enquanto `torch` era dependência apenas transitiva (lock saía com stack CUDA do PyPI); foi necessário declarar `torch`/`torchvision` como dependências diretas e regerar `uv.lock`. Cancelamento e repetição do `uv sync` por mudança de lock consumiram tempo. Nenhuma lógica implementada (stubs), conforme escopo.

### Revisão
- Orquestrador: GLM-5.3-Flash (provider `sd2`) — task-master do ciclo opt-in. Rodada **paralela** (padrão): verificação de leitura/config, sem uso exclusivo de recursos compartilhados; revisores instruídos a não escrever na árvore.
- Alvo: entrega `bf5b812` (43 arquivos: scaffold, config, uv.lock, stubs) e registro `f90f2de` (apenas task.md); base `8e5c56b`; HEAD `f90f2de`, árvore limpa.
- Avaliações (quórum de três modelos distintos, sem falhas nem substituições):
  - `sd2/GLM-5.3-Flash` — 9,5/10, aprovada. Defaults 25/25 conferidos por parser YAML, zero divergências; pins do lock idênticos às Evidências. Achado A1 (baixo): `data/<user_id>/` criado como diretório literal com colchetes angulares (placeholder) — decidir destino na task 004; A2 informativo: `cli.py` stub levanta NotImplementedError (escopo).
  - `openai/gpt-6-luna` — 9/10, aprovada. Sem achado relevante; ressalva: instalação/smoke test aceitos com base nas evidências registradas, sem repetição independente.
  - `opencode/mimo-v2.6-flash-free` — 9,5/10, aprovada. Versões do venv conferidas via importlib.metadata — idênticas ao lock e ao relato; 25/25 defaults corretos; observações sem impacto (contagem "38/38" não reproduzível como número exato, porém nenhum item do §3 ausente; .python-version 3.12 dentro de "3.11+").
- Nota final: 9/10 — scaffold fiel ao mapa §3 com defaults verificados por dois revisores de forma independente (parser YAML e importlib.metadata), pins reais, commits separados, mapa/plano/submódulo intocados. Deduções: placeholder literal `data/<user_id>/` (A1, sem efeito nesta task) e verificação de runtime apoiada no ambiente do executor (nenhum revisor reexecutou uv sync, por restrição).
- Parecer: C1–C4 comprovados por evidência direta e independente. Registro de incidente de processo: a primeira execução do ciclo retornou antes de commitar (aguardava `uv sync` em background); uma retomada manual via subagente e a continuação da sessão original se sobreporam sem duplicação — os commits existentes são únicos e íntegros (verificado pelo master e pelo revisor GLM); nenhuma reexecução de trabalho ocorreu. Divergências entre revisores: nenhuma essencial.
- Decisão: fechar — todos os critérios obrigatórios comprovados; libera a task 002.
- Reversão: não se aplica.
- Próximo passo: task 002 (manifesto/hardware e gate de modelo). A task 004 deve decidir o destino do placeholder `data/<user_id>/` (achado A1) — anotado no prompt da 004.

<!-- task-cycle: {"decision":"fechar","next_task":".agents/tasks/04-mapa-completo-do-sistema/002-manifesto-hardware-e-gate-de-modelo.md","family":".agents/tasks/04-mapa-completo-do-sistema/001-scaffold-e-configuracao.md","plan":".agents/plans/04-mapa-completo-do-sistema/plan.md"} -->

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
