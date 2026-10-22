# Task 016a: Correção — limites no transporte real, redirect malicioso do CalDAV e complementos da 016

Estado: aguardando revisão
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
- [x] C1 — Limite de 5 MiB e timeout de 10 s do §6 impostos no transporte real da web: leitura limitada a `MAX_BODY_BYTES + 1` (incluindo caminho `HTTPError`), excesso → `unavailable` tipado; teste discriminante contra servidor HTTP local real chamando o transporte diretamente, com sensibilidade à mutação provada; sem leitura integral antes do cheque.
- [x] C2 — CalDAV sem redirect automático: redirect para host/esquema distinto do `base_url` recusado com erro tipado, sem contato com o segundo host e sem reenvio da credencial Basic (prova por captura/afirmação no teste); teste de redirect malicioso do CalDAV presente e a admissão do CalDAV revalidada e registrada (histórico da admissão anterior preservado).
- [x] C3 — Complementos baixos provados: `parse_multistatus` rejeita DTD/entidades e limita bytes pré-parse; REPORT com teto de corpo; clamp de `max_results` na rota curate com regressão; wiring do `calendar_connector` no runtime com teste dos dois caminhos (config presente/ausente); defaults rotulados como escolhas de ensaio.
- [x] C4 — Suíte integral ≥ 564 passed sem regressões (564 + regressões novas dos itens acima); mapa, config de docs, docs/, submodule e `uv.lock` intocados; commits de entrega e de registro separados; questão aberta da busca e não-admissão do Google preservadas sem invenção.

## Execução

- Modelo: GLM-5.3-Flash (provider `sd2`, model id `GLM-5.3-Flash`, via `~/sd2-llm.sh`) — identidade informada pelo runtime da sessão.
- Base: `85d4badc8384b8a0cb3d8913a9764e4d1726cd7c` (árvore limpa; suíte 564 passed reproduzida na base antes de iniciar).
- Entrega: `33a75712be1c3a94148ac170a30df3da90239fc7` (commit de código; commit de registro é este, encontrado por `git log -- <task.md>`; entrega da 016 `7db9267` e registro `a365ea5` preservados, sem amend/rebase/reversão).
- Arquivos da entrega: `eduagent/services/web.py` (transporte real com leitura limitada a `MAX_BODY_BYTES + 1` incluindo `exc.read(limit)`, timeout default 10 s e `URLError` de timeout normalizado a `TimeoutError`), `eduagent/services/sync_connectors.py` (auto-follow de redirect desabilitado com validação de origem por esquema+autoridade, `ConnectorError` sem contato com o segundo host e sem reenvio da credencial, `parse_multistatus` recusando DTD/entidades e limitando bytes pré-parse a 1 MiB, teto de 5 MiB no corpo do REPORT, `CONNECTOR_ADMISSION["caldav"]` revalidado com histórico da 016), `eduagent/graph.py` (clamp `min(max_results, _MAX_CANDIDATES)` antes de `search`), `eduagent/runtime.py` (`calendar_connector=build_calendar_connector(effective_config)` no montagem do grafo), `tests/test_task016_conectores.py` (17 testes novos: W9a–d, W10, S9b, S10–S10d, S11–S11e, S12a–b; tabela do cabeçalho atualizada).
- Evidências:
  - **C1 (LUNA-A1)**: W9 — servidor HTTP local real (`_HttpServerLocal`, 127.0.0.1 porta efêmera, sem rede externa) respondendo 5 MiB+4096 bytes; `urllib_transport` chamado DIRETAMENTE (fora da barreira de IP privado da rota — camadas distintas) devolve exatamente `MAX_BODY_BYTES + 1` bytes, e o excesso alimenta `_build_resource` → estado tipado `unavailable` ("corpo excede"). W9b: caminho `HTTPError` (404 com corpo grande) também limitado a `MAX+1`. W9c: timeout imposto (servidor dorme 1,5 s, cliente 0,25 s → `TimeoutError`). W9d: default do parâmetro é `DEFAULT_TIMEOUT_S = 10.0` (§6). **Sensibilidade à mutação provada** (sondas em `/tmp/opencode/016a/`): (1) `read(limit)` → `read()` sem limite → W9 e W9b falham (2 failed); restaurado → 4 passed; (2) `timeout=timeout_s` → `timeout=None` → W9c falha; restaurado → 4 passed.
  - **C2 (LUNA-A2)**: S10 — transporte real (`make_urllib_transport` com credencial Basic) contra DOIS servidores locais reais; o primeiro responde 302 → `http://127.0.0.1:<porta B>/roubo`: `read_all` levanta `ConnectorError` ("origem distinta… credencial"), captura prova exatamente 1 requisição no host A (com `Authorization: Basic …` confinado à origem configurada) e ZERO requisições no host B (sem contato, sem reenvio da credencial). S10b: redirect https (esquema distinto, mesmo host:porta) recusado. S10c: `Location` protocol-relative (`//evil.exemplo.invalid/roubo`) recusado. S10d: redirect mesmo-origem é segido (dois REPORTs, leitura OK) — redirect legítimo preservado. S9b: `CONNECTOR_ADMISSION["caldav"]` revalidado com "ADMITIDO (revalidado na 016a)" + histórico da admissão da 016 preservado. **Mutação provada**: `_same_origin` → `True` → S10/S10b/S10c falham (3 failed); restaurado → 4 passed.
  - **C3 (GLM-A1/QW-A2/GLM-A2/QW-A1)**: S11: multistatus com `<!DOCTYPE … <!ENTITY …>` e com `<!ENTITY` órfã recusados com `ConnectorError`; bytes pré-parse limitados a `MAX_MULTISTATUS_BYTES = 1 MiB` (default de ensaio rotulado, parâmetro `max_bytes` honrado); multistatus legítimo sem DTD continua parseando (S11e). S11d: REPORT 207 com corpo > `MAX_REPORT_BODY_BYTES = 5 MiB` (default de ensaio rotulado — o §9 NÃO prescreve valor; nunca apresentado como resultado medido) → `ConnectorError`. W10: rota curate com payload `max_results=50` faz `search` receber exatamente 5 (`min(50, _MAX_CANDIDATES)`); sem payload recebe o default 5; **mutação provada** (clamp removido → 1 failed; restaurado → passed). S12: `RuntimeContext.open` com config CalDAV → `graph._calendar_connector` é `CaldavConnector`; sem config → `None` com `apply` reportando `CONNECTOR_DISABLED` mantendo ICS/preview (S7 preservado). **Mutação da defesa DTD provada**: cheque removido → S11 falha; restaurado → 5 passed.
  - **C4**: suíte integral `.venv/bin/python -m pytest tests/ -q` → **581 passed** (564 do piso + 17 novos), 2 warnings pré-existentes, sem regressões; `git status`/`git diff` confirmando mapa (`fase2/`), `config/`, `docs/`, submodule `docs/playground-llmagenticsystem` e `uv.lock` intocados (nenhuma dependência nova — só biblioteca padrão); commits de entrega (`33a7571`) e de registro (este) separados; questão aberta do conector de busca permanece ABERTA (`CONNECTOR_DISABLED`, nada de dedup/promessa) e Google permanece NÃO ADMITIDO — nada inventado.

### Verificações executadas

- Suíte da base reproduzida antes de iniciar: 564 passed.
- Suíte integral após a entrega: **581 passed** em ~34 s, sem regressões.
- Cinco sondas de sensibilidade à mutação em `/tmp/opencode/016a/` (cap de leitura web, timeout do transporte web, `_same_origin` do CalDAV, clamp do `max_results`, defesa DTD) — todas com falha sob mutação e passed restaurado; backups restaurados e árvore conferida por `git status`/`git diff` ao final.

### Limitações e pendências registradas (não são resultado medido)

- A validação de redirect do CalDAV compara esquema E autoridade completa (host:porta) do `base_url` — escolha local documentada, mais estrita que "mesmo host" a miolo: porta distinta é outro serviço/origem e é recusada (servidores CalDAV legítimos com redirect de mudança de porta/esquema precisariam ajustar o `base_url` configurado).
- O teto de corpo do REPORT (5 MiB) e o limite pré-parse do multistatus (1 MiB) são defaults de ensaio rotulados — o §9 não prescreve valores; nunca apresentados como resultados medidos.
- O transporte real do CalDAV lê o corpo do hop (2xx/3xx) sem cap de bytes no transporte; o teto normativo do REPORT é imposto no conector (leitura) — alinhado ao item 3 da task, que pede teto no REPORT, não no transporte.
- Nenhum conector de busca é admitido (questão aberta permanece); Google permanece NÃO ADMITIDO; `transcript_read` segue sem conector admitido no MVP.
- Testes de rede usam apenas servidores HTTP locais reais (127.0.0.1, portas efêmeras) — sem rede externa, sem credenciais reais.

## Notas

### Dificuldade esperada
4/10 — Correções delimitadas em código recém-escrito e bem testado; o ponto de maior cuidado é testar o transporte real sem rede externa (servidor local chamado diretamente, fora da barreira da rota) e provar a não-reenvio de credencial no redirect, além de manter o piso de 564 passed.

### Dificuldade sentida
4/10 — Correções delimitadas em código recém-escrito e bem testado, como previsto. Pontos de atrito: (1) provar o cap de leitura e o timeout no transporte real sem rede externa exigiu um servidor HTTP local real (127.0.0.1, porta efêmera) chamado diretamente — fora da barreira de IP privado da rota, mantendo as camadas distintas; (2) provar "sem contato com o segundo host e sem reenvio de credencial" no redirect do CalDAV exigiu a captura em DOIS servidores locais simultâneos (contador de requisições por host) e a decisão documentada de comparar a autoridade completa (host:porta), não só o hostname; (3) o auto-follow do urllib só se desativa via handler próprio, e a resposta 3xx chega pelo caminho `HTTPError` — o laço de redirect precisou unificar os dois caminhos de resposta; (4) as cinco sondas de mutação (incluindo uma com guarda `timeout 30` contra hang potencial) consumiram a maior parte do tempo, mas deram a discriminação exigida pelo padrão D1. Piso de 564 preservado sem esforço extra: as mudanças são aditivas nos caminhos reais e os testes antigos usam transporte injetado.

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
