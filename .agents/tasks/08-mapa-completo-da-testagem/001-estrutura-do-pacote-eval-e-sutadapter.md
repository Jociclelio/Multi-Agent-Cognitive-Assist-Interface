# Task 001: Estrutura do pacote eval/ e SUTAdapter

Estado: pendente
Depende de: nenhuma
Origem: nenhuma

## Prompt
Criar a estrutura do pacote `eval/` conforme mapa §2 (`cli.py`, `runner.py`, `adapters.py`, `oracles/`, `faults/`, `metrics/`, `statistics/`, diretórios de fixtures/manifests/runs) e implementar o `SUTAdapter` obrigatório (mapa §1) para as condições MA, SA e ablações, com `TurnResult`, inspeção autoritativa restrita ao harness e `MockLLM` apenas para lógica determinística. Fixar a stack: Python 3.11+, pytest, Hypothesis, JiWER, pytrec_eval, scikit-learn/SciPy; parser ICS independente candidato `ics.py`, pinado APÓS smoke de conformidade RFC (se a fixture RFC falhar, registrar interoperabilidade inconclusiva, não falha automática — mapa §2). O adapter opera o EduAgent-OS real (`eduagent/`, `uv run`) como SUT; `eval/ensaio_longitudinal.py` e `eval/relatorio-testes-mvp.md` existentes são preservados e não são reescritos. Dependências novas entram no grupo `dev` do `pyproject.toml` com `uv sync` regenerando `uv.lock`.

Restrições: código do sistema `eduagent/` e o manifesto congelado (`manifest.json`) INTOCADOS; `fase2/documentos/08_mapa_completo_da_testagem.md` é a fonte normativa — ler integralmente as seções §1–§2 antes de implementar; thresholds do mapa são propostos, não resultados; nada apresentado como resultado medido; submódulo `docs/playground-llmagenticsystem` não tocado; suíte raiz `uv run pytest tests/` (591) deve continuar passando; commits de entrega e registro separados; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/08_mapa_completo_da_testagem.md` — fonte normativa autocontida: §1 (interface SUT), §2 (estrutura do pacote, stack, parser ICS).
- `eduagent/` — SUT a adaptar (CLI e API loopback em `eduagent/cli.py`, `eduagent/api.py`).
- `eval/ensaio_longitudinal.py`, `eval/relatorio-testes-mvp.md` — artefatos existentes do ensaio do plano 04 (preservar).
- `pyproject.toml`, `uv.lock` — ambiente uv (deps de avaliação no grupo `dev`).

## Corretude
- [ ] C1 — Estrutura de diretórios/arquivos do `eval/` conforme mapa §2, com `SUTAdapter` implementando a interface do mapa §1 para MA, SA e ablações (mesmo modelo/corpus/memória/tools/envelope no SA), `TurnResult` e `MockLLM` restrito a lógica determinística.
- [ ] C2 — Smoke do parser ICS candidato executado contra fixture RFC com resultado registrado (pinado ou interoperabilidade inconclusiva documentada); stack instalada no grupo `dev` com `uv.lock` regenerado e uv.lock raiz do sistema sem mudança de dependências de runtime.
- [ ] C3 — Suíte raiz `uv run pytest tests/` integral passando (piso 591); artefatos do ensaio do plano 04 preservados; código de `eduagent/` e `manifest.json` intocados.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
6/10 — Scaffold com contrato de adapter correto desde o início (condições e inspeção autoritativa) sem contaminar o SUT; dependências pesadas (torch já presente no embedder) podem tensionar limites de memória documentados no parágrafo 3 do mapa 4.

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

### Revisão
- Orquestrador: —
- Alvo: —
- Avaliações: <modelo A: _/10; modelo B: _/10; modelo C: _/10>
- Nota final: _/10
- Parecer: —
- Decisão: —
- Reversão: —
- Próximo passo: —

Plano: [plan.md](../../plans/08-mapa-completo-da-testagem/plan.md)
