# Task 001: Extensão da API Loopback, Ordenação em 4 Faixas e Servidor UI

Estado: concluída
Plano: `.agents/plans/interface-grafica-local/plan.md`

## Objetivo

Estender `eduagent/api.py` (preservando 100% da retrocompatibilidade com os endpoints do §12) para usar `ThreadingHTTPServer`, expor os endpoints de leitura e staging necessários à Interface Gráfica Local (`/courses`, `/courses/{id}/sessions`, `/sessions/{id}`, `/operations`, `/calendar`, `/progress`, `/library`, `/library/upload`, `/review/flashcards`, `/search`), servir os ativos estáticos de `ui/dist/` e oferecer inicialização via `eduagent --serve-ui` ou `python -m eduagent.api`.

## Arquivos tocados

- `eduagent/api.py`
- `eduagent/cli.py`

## Critérios de corretude

- [x] Todos os testes existentes de `TestParser` e `TestAPILoopback` em `tests/test_task015_cli_api.py` continuam passando sem alteração.
- [x] `GET /courses` retorna disciplinas ordenadas deterministicamente nas 4 faixas (`1: scheduled_block`, `2: critical_demand`, `3: new_curation`, `4: inactivity_days`) com `ready_to_study`, `sort_reason_label` e `recommended_intent`.
- [x] `POST /library/upload` confina escritas em `data/<user_id>/originals/` via `resolve_owned_path` e impõe o teto de 50 MiB (`RESOURCE_LIMIT`).
- [x] `GET /sessions/{id}` e `GET /review/flashcards` jamais vazam `expected_answer` quando `revealed=false`.

