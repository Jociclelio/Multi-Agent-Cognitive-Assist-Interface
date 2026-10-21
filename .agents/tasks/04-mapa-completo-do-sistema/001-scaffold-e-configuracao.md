# Task 001: Scaffold do projeto e configuração (mapa §3)

Estado: pendente
Depende de: nenhuma
Origem: nenhuma

## Prompt
Criar o esqueleto do EduAgent-OS v0.1 conforme o mapa normativo `fase2/documentos/04_mapa_completo_do_sistema.md` §3: estrutura de diretórios (`eduagent/{api,cli,config,contracts,graph,context,policy,telemetry}.py`, `eduagent/agents/`, `eduagent/services/`, `eduagent/storage/`, `eduagent/skills/{explain,graduated_hint,quiz,flashcard,self_explain}/skill.yaml` como stubs declarativos, `config/default.yaml`, `schemas/`, `data/<user_id>/{originals,derived,indexes,exports}/`, `tests/ fixtures/ eval/`), `pyproject.toml` com Python 3.11+ e dependências pinadas via `uv` (LangGraph, Pydantic v2, Docling, motor OCR, SentenceTransformers/FlagEmbedding, OR-Tools, icalendar, rank_bm25), `uv.lock` gerado, e `config/default.yaml` com TODOS os defaults do mapa §3: `window=32768`, `max_output_tokens=16384`, `tool_reserve=2048`, `margin=1024`, `doc_tokens=4096`, `memory_tokens=2048`, `max_llm_calls=6`, `max_tool_calls=8`, `max_graph_steps=16`, `max_repairs_total=2`, `max_repair_artifact=1`, `active_deadline_s=120`, `llm_timeout_s=90`, `retrieval_top_k=40`, `rrf_k=60`, `rerank_candidates=40`, `evidence_chunks=6`, `solver_budget_s=10`, `slot_minutes=15`, `horizon_days=7`, `seed=0`, `num_workers=1`; ingestão `50 MiB/500 páginas/timeout 600 s/subprocesso 4 GiB`; `network_enabled=false`, `calendar_sync_enabled=false`; `timezone` NÃO fixado (`America/Sao_Paulo` só após confirmação — registrar como pendente). Registrar em Evidências as versões reais resolvidas.

Restrições: mapa intocado; defaults são escolhas de ensaio, não resultados medidos; sem implementar lógica de agentes nesta task (stubs); temporários em `/tmp/opencode`; commits de entrega e de registro separados.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — fonte normativa: §3 (stack, diretórios, configuração). Ler integralmente; "deve" é contrato.
- `.agents/plans/04-mapa-completo-do-sistema/plan.md` — plano aprovado: Escopo e Questões abertas.

## Corretude
- [ ] C1 — Estrutura de diretórios e módulos existe conforme mapa §3; `uv sync` (ou equivalente com lock) instala o ambiente; `python -c "import eduagent"` funciona.
- [ ] C2 — `config/default.yaml` reproduz todos os defaults numéricos e flags do §3, conferidos item a item; timezone não fixado e pendência registrada.
- [ ] C3 — `uv.lock` com pin real das dependências; versões registradas em Evidências (pin é resultado do smoke test, não `latest` presumido).
- [ ] C4 — Mapa e plano intocados (`git diff`); commit de entrega (código/config) e de registro (task.md) separados; submódulo não tocado.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
2/10 — Scaffold e transcrição de defaults com conferência dígito a dígito; risco baixo.

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
