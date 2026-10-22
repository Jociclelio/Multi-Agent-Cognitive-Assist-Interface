# Task 015a: Correção da 015 — ownership de sessão, tombstones no restore, confinamento de caminhos e JSON da API

Estado: pendente
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
- [ ] C1 — Sonda de ownership reproduzida antes/depois: usuário B autenticado não consegue `resume`/`cancel`/`approve` em sessão de A (recusa tipada, sem efeito aplicado); regressões novas na suíte da 015 cobrindo os três comandos pela API e pela CLI.
- [ ] C2 — Sondas de restore reproduzidas antes/depois: (a) backup pré-deleção + delete + restore → recusa tipada com diretório descartado, payload tombstonado não ressuscita; (b) manifesto adulterado com `../` e caminho absoluto → recusa tipada; testes de regressão para os dois caminhos negativos e para o teste de recusa do verificador de tombstones (item 6).
- [ ] C3 — API responde JSON com `status: failed` e `INTERNAL_FAILURE` em exceção fora do contrato (teste com payload que provoque `ValueError` fora dos handlers); item de exit code 3 resolvido com teste alinhado ou escolha documentada no registro; itens baixos corrigidos com teste ou documentados.
- [ ] C4 — Suíte integral verde (521 anteriores + regressões novas, sem quebrar 490+31); entrega em commit de código separado do registro; mapa, `config/`, `docs/` e submódulo intocados; `uv.lock` inalterado.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
3/10 — Correções pontuais e locais com sondas já descritas pela revisão; maior cuidado no confronto de tombstones com o domínio corrente sem quebrar o restore legítimo da 015.

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
