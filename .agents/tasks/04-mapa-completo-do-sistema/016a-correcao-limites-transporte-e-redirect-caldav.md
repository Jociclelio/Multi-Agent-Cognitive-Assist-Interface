# Task 016a: Correção — limites no transporte real, redirect malicioso do CalDAV e complementos da 016

Estado: pendente
Depende de: 016
Origem: 016 — correção (preserva a entrega `7db9267075e6c54bc794cdc65173f66a7434f2aa`; sem reversão)

## Prompt
Corrigir pontualmente a entrega da 016 preservando design e admissões já registrados, contra os achados da revisão (nota 8/10, decisão `corrigir`):

1. **Obrigatório (LUNA-A1)** — Impor o limite de 5 MiB do mapa §6 no transporte real da web (`urllib_transport` em `eduagent/services/web.py`): a leitura (incluindo o caminho `HTTPError` via `exc.read()`) deve ser limitada a `MAX_BODY_BYTES + 1` bytes, com excesso mapeado ao estado tipado `unavailable` (mesma forma do teste W7), e não mais lido integralmente antes do cheque em `_build_resource`. O timeout de 10 s do §6 também deve valer no transporte real. Provar por teste discriminante contra servidor HTTP local real (o teste chama o transporte diretamente, fora da barreira de IP privado da rota — camadas distintas), com sensibilidade à mutação provada (falha sob mutação, passed restaurado), mesmo padrão da dívida D1.
2. **Obrigatório (LUNA-A2)** — CalDAV (`eduagent/services/sync_connectors.py`): desabilitar o redirect automático do `urllib` e validar cada destino de redirect antes de seguir — mesmo host e esquema do `base_url` configurado; redirect para host/esquema distinto é recusado com erro tipado, sem contatar o segundo host e **sem reenviar a credencial Basic** a ele. Adicionar o teste de falha de rede **redirect malicioso do CalDAV** (exigido pela task 016 para admissão individual de cada conector e ausente na entrega), junto aos já existentes de timeout e resposta inválida. Revalidar e registrar a admissão do CalDAV em `CONNECTOR_ADMISSION`/Evidências após a correção (a admissão anterior fica como histórico; nada de comportamento inventado).
3. **Complementar baixo (GLM-A1/QW-A2)** — Endurecer `parse_multistatus`: rejeitar XML com DTD/declaração de entidades no preâmbulo e limitar os bytes antes do parse (default de ensaio, ex.: 1 MiB, rotulado); impor teto de corpo no REPORT do CalDAV (default de ensaio, ex.: 5 MiB, rotulado — o §9 não prescreve valor; nunca apresentar como resultado medido).
4. **Complementar baixo (GLM-A2)** — Rota curate (`eduagent/graph.py`): cortar `max_results` com `min(max_results, _MAX_CANDIDATES)` antes de chamar `search`, na mesma linha do corte defensivo existente, com regressão discriminante.
5. **Complementar baixo (QW-A1)** — Wiring: `eduagent/runtime.py` deve construir `calendar_connector=build_calendar_connector(effective_config)` ao montar `EduAgentGraph`, tornando o conector CalDAV admitido alcançável pela superfície CLI/API; teste de wiring provando que config CalDAV presente chega ao grafo e ausente mantém `CONNECTOR_DISABLED` com ICS/preview (comportamento S7 preservado).

Restrições: preservar a entrega da 016 e seus registros (commits `7db9267`/`a365ea5` intocados, sem amend/rebase); suíte integral **564 passed** é o piso — sem regressões; nenhum comportamento inventado; questão aberta do conector de busca permanece ABERTA (`CONNECTOR_DISABLED`, nada de dedup/promessa); Google permanece NÃO ADMITIDO; mapa, config de docs, docs/ e submodule intocados; `uv.lock` inalterado salvo dependência nova estritamente necessária (pinada); defaults numéricos são escolhas de ensaio rotuladas; commits SEPARADOS (entrega e registro) sem vazios; temporários/sondas em `/tmp/opencode`; sem push, sem rede externa real, sem benchmarks >10 min.

## Contexto
- `.agents/tasks/04-mapa-completo-do-sistema/016-conectores-opcionais-web-e-sync.md` — task mãe: contrato, admissões individuais, evidências W1–W8/S1–S9/D1 e limitações registradas (ler antes).
- `eduagent/services/web.py` — transporte real `urllib_transport` (linhas ~157-160), `_build_resource`, limites.
- `eduagent/services/sync_connectors.py` — transporte CalDAV (`urllib`, linhas ~94-111), `parse_multistatus` (~175), `CONNECTOR_ADMISSION`.
- `eduagent/graph.py` — rota curate (~2667) e `calendar_connector` no grafo.
- `eduagent/runtime.py` — montagem do `EduAgentGraph` na superfície CLI/API (~126).
- `tests/test_task016_conectores.py` — testes existentes W1–W8, S1–S9, D1 (padrão de transporte injetado e servidor falso a estender).
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §6 (limites da curadoria), §9 (sync), §10 (tabela de ferramentas) — INTOCADO; "deve" é contrato.

## Corretude
- [ ] C1 — Limite de 5 MiB e timeout de 10 s do §6 impostos no transporte real da web: leitura limitada a `MAX_BODY_BYTES + 1` (incluindo caminho `HTTPError`), excesso → `unavailable` tipado; teste discriminante contra servidor HTTP local real chamando o transporte diretamente, com sensibilidade à mutação provada; sem leitura integral antes do cheque.
- [ ] C2 — CalDAV sem redirect automático: redirect para host/esquema distinto do `base_url` recusado com erro tipado, sem contato com o segundo host e sem reenvio da credencial Basic (prova por captura/afirmação no teste); teste de redirect malicioso do CalDAV presente e a admissão do CalDAV revalidada e registrada (histórico da admissão anterior preservado).
- [ ] C3 — Complementos baixos provados: `parse_multistatus` rejeita DTD/entidades e limita bytes pré-parse; REPORT com teto de corpo; clamp de `max_results` na rota curate com regressão; wiring do `calendar_connector` no runtime com teste dos dois caminhos (config presente/ausente); defaults rotulados como escolhas de ensaio.
- [ ] C4 — Suíte integral ≥ 564 passed sem regressões (564 + regressões novas dos itens acima); mapa, config de docs, docs/, submodule e `uv.lock` intocados; commits de entrega e de registro separados; questão aberta da busca e não-admissão do Google preservadas sem invenção.

## Execução
- Modelo: _
- Base: _
- Entrega: _
- Arquivos da entrega: _
- Evidências: _

## Notas

### Dificuldade esperada
4/10 — Correções delimitadas em código recém-escrito e bem testado; o ponto de maior cuidado é testar o transporte real sem rede externa (servidor local chamado diretamente, fora da barreira da rota) e provar a não-reenvio de credencial no redirect, além de manter o piso de 564 passed.

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
