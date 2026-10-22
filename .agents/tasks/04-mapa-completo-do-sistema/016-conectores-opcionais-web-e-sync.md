# Task 016: Conectores opcionais — curadoria web e sync de calendário (mapa §6/§9, §13.9)

Estado: aguardando revisão
Depende de: 015
Origem: nenhuma

## Prompt
Implementar e admitir individualmente os conectores opcionais (mapa §6 curadoria web, §9 sync, §13.9): curadoria web — interface `search(query, language, max_results)->candidates` e `fetch(url)->resource`; até 5 candidatos/3 fetches, 10 s/5 MiB, dois redirects com revalidação; estados `metadata_only/text_read/transcript_read/unavailable`, URL final, data/hash e fonte; vídeo sem transcrição só recomendado por metadados, nunca resumido; conector de busca escolhido/configurado na implementação — sem ele, `CONNECTOR_DISABLED` (rota `curate` com `network_gate`); cache offline marcado com data, nunca fingido como consulta atual; `web.search/fetch` respeitam `network_enabled=false` e a política de rede da task 014. Sync de calendário — MCP expõe `read/create/update/delete` com IDs/precondições; CalDAV com href estável, criação `If-None-Match: *`, atualização `If-Match` ETag; Google: ID próprio de criação conforme backend, update/delete condicional **só depois de verificar documentação específica** (se não verificada, declarar não admitido — não inventar comportamento); timeout→`UNKNOWN_EFFECT`→read/reconcile sem repetição cega; alteração externa→conflito e novo preview; se o conector não preservar leitura, IDs e versão, manter ICS/preview e declarar não admitido. Cada conector é admitido individualmente após contratos e testes de falha de rede (timeout, redirect malicioso, resposta inválida); sem credenciais, não bloqueiam o núcleo.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §6 (curadoria web), §9 (sync), §13.9; tabela `web.search/fetch`/`calendar.apply` (§10).
- Task 013 (contratos de sync/outbox), 014 (network_gate/política), 015 (CLI/API).

## Corretude
- [x] C1 — Curadoria web com limites/estados/hash conforme §6; sem conector configurado, `CONNECTOR_DISABLED` com comportamento testado; cache offline datado.
- [x] C2 — Falhas de rede testadas (timeout/redirect/5 MiB); fetch bloqueia IP privado/loopback (herdado da 014, retestado na rota curate).
- [x] C3 — Sync: MCP/CalDAV conforme contrato; Google condicional apenas com verificação documental registrada, senão não admitido; reconciliação por identidade com UNKNOWN_EFFECT sem retry cego.
- [x] C4 — Conectores admitidos individualmente com registro em Evidências; sem credenciais o núcleo segue funcional; mapa intocado; commits separados.

## Execução

- Identidade real do modelo: GLM-5.3-Flash (provider `sd2`, model id `GLM-5.3-Flash`, via `~/sd2-llm.sh`) — identidade informada pelo runtime da sessão.
- Base: `5f56f8ea710a20d13c4a0c489d30bb29a046425c` (árvore limpa, pós-revisão da 015b; suíte 535 passed reproduzida na base antes de iniciar).
- SHA de entrega: `7db9267075e6c54bc794cdc65173f66a7434f2aa` (commit de código; commit de registro é este, encontrado por `git log -- <task.md>`, sem SHA próprio em si).
- Artefatos da entrega: `eduagent/services/web.py` (novo), `eduagent/services/sync_connectors.py` (novo), `eduagent/graph.py` (cap de 5 candidatos na rota curate + parâmetro `calendar_connector` no `_node_publish_ics`), `eduagent/policy.py` (dívida da 014a: reembolso no `TIMEOUT` pós-`consume_llm`), `eduagent/services/calendar.py` (docstring do `apply_plan` atualizada para a admissão da 016 — sem mudança de comportamento), `tests/test_task016_conectores.py` (novo, 29 testes).

### Registro de admissão individual dos conectores (§9, critério C4)

- **Web/fetch HTTP — ADMITIDO**: interface `fetch(url)->resource` com limites normativos (≤5 candidatos, ≤3 fetches, 10 s, 5 MiB, dois redirects com revalidação de cada hop); estados `metadata_only/text_read/transcript_read/unavailable` com URL final, data, hash SHA-256 e fonte; vídeo/áudio sempre `metadata_only` (nunca resumido, §6); cache offline marcado com `cached=True`, `source="cache"` e a data ORIGINAL da captura. Testes de falha de rede (transporte injetado, sem rede real): timeout, conexão recusada, resposta 404/503, corpo > 5 MiB, terceiro redirect, redirect malicioso para IP privado (negado por código).
- **Web/busca — NÃO ADMITIDO (questão aberta NÃO decidida)**: nenhum conector de busca é implementado nem escolhido; `search` recusa `CONNECTOR_DISABLED` e a rota `curate` permanece desabilitada (testada nos dois níveis: sem conector no `network_gate` e com conector de fetch no nó `web_search`). A decisão do backend de busca fica para decisão própria posterior; nada de dedup/comportamento de busca é prometido.
- **CalDAV (RFC 4791) — ADMITIDO**: href estável por UID; criação `PUT` com `If-None-Match: *` (obrigatório — recusa `SCHEMA_INVALID` sem ele); atualização/remoção SEMPRE condicionais com `If-Match` ETag do read anterior (escrita incondicional recusada); `412` → `CONFLICT` (alteração externa → conflito e novo preview); `404` em delete → `APPLIED` (escolha local documentada: estado já igual ao desejado, evita reenvio inútil); `TimeoutError` → `ConnectorTimeout` → reconcile por leitura, sem retry cego; leitura inacessível pós-timeout → `UNKNOWN_EFFECT` terminal. Testes com servidor CalDAV falso (transporte injetado) incluindo timeout com efeito possível/sem efeito e contador de PUTs provando ausência de retry cego.
- **Google Calendar — NÃO ADMITIDO**: update/delete condicional exige verificação documental específica (§9) NÃO realizada nesta entrega, e não há credenciais para testes de falha de rede; conector não implementado — `GoogleCalendarConnector` recusa por código e `CONNECTOR_ADMISSION["google"]` registra o motivo; ICS/preview mantidos. Nenhum comportamento inventado.
- **Sem credenciais/conector o núcleo segue funcional**: `build_calendar_connector` devolve `None` sem config e `calendar.apply` reporta `CONNECTOR_DISABLED` mantendo ICS/preview (comportamento da 013 preservado; o conector admitido entra por `calendar_connector` no grafo quando configurado).

### Evidências (Corretude)

- **C1 (curadoria web §6)**: 29 testes novos (`tests/test_task016_conectores.py`, tabela W1–W8/S1–S9/D1 no cabeçalho). W1: `search` sem conector → `RESOURCE_LIMIT` com prefixo `CONNECTOR_DISABLED`. W2: rota curate com `network_enabled=true` e sem conector → `CONNECTOR_DISABLED` no `network_gate`; W3: com `WebFetchConnector` (busca desabilitada) → `CONNECTOR_DISABLED` no nó `web_search`. W4: estados `text_read`/`metadata_only`/`unavailable` com URL final, `captured_at`, hash SHA-256 de 64 hex e fonte; vídeo/mp4 nunca vira `text_read`; W4b: claims do grafo marcam vídeo como `metadata_only` com nota de metadados. W8: cache offline devolve `cached=True`, `source="cache"`, `captured_at` ORIGINAL (T+0 mesmo com relógio em T+30) e razão "cache offline" — nunca fingido como consulta atual; cache vazio não vira conteúdo. Cap de candidatos em duas camadas (conector valida 1..5; grafo corta em 5) — W7c/W7b.
- **C2 (falhas de rede e barreira §10)**: W7: corpo de 5 MiB+1 → `unavailable` com razão; timeout (`TimeoutError`) e conexão recusada → `unavailable` tipado, não exceção crua. W5: dois redirects com revalidação de cada hop (URL final = terceiro hop, `redirect_chain` completo); terceiro redirect recusado; redirect para `http://10.0.0.1/` → `TOOL_DENIED` (código). W6: `fetch` bloqueia `127.0.0.1`, `localhost`, `192.168.0.1`, `[::1]` e esquema não-http com resolução REAL de nomes (transporte nunca chamado); W6b: rota curate revalida o destino de cada candidato com IP privado → `TOOL_DENIED` (reteste do comportamento herdado da 014 na rota, defesa em profundidade).
- **C3 (sync §9)**: S1–S3: precondições CalDAV provadas por captura de requisições (`If-None-Match: *` na criação; `If-Match` ETag no update/delete; href do read reutilizado; 412 → `CONFLICT`). S4: parse de `207 Multi-Status` com uid/etag/ics; `read_one` ausente → `None`; REPORT ≠ 207 → `ConnectorError` (falha definida, sem mascarar leitura). S5: timeout no PUT → exatamente UM PUT (contador prova ausência de retry cego) → leitura também inacessível → `UNKNOWN_EFFECT` terminal; S5b: timeout com leitura OK → reconciliado `NOT_APPLIED` por leitura. S6: end-to-end `apply_plan` com CalDAV (cria eventos; reaplicação sem mudança não gera ops; alteração externa → `CONFLICT` com "novo preview" no detalhe). S8: adaptador MCP com allowlist exata de `read/create/update/delete` com IDs/precondições; ferramenta fora da lista → `TOOL_DENIED`; `create` com `if_none_match_star=false` → `TOOL_DENIED`; IDs/precondições ausentes → `SCHEMA_INVALID`. S9: registro de admissão com Google NÃO ADMITIDO e construção recusada por código.
- **C4 (intocabilidade, commits, admissão individual)**: `git status`/`git diff` confirmando `fase2/` (mapa), `config/` e `docs/` sem alteração; submódulo `docs/playground-llmagenticsystem` intocado; `uv.lock` inalterado (nenhuma dependência nova — conectores usam só biblioteca padrão: `urllib`, `xml.etree`, `hashlib`, `base64`); commit de entrega (`7db9267`) separado do commit de registro (este); admissão individual registrada na seção própria acima.
- **Dívida herdada da 014a (D1)**: `GenerationGate.generate` reembolsa o débito LLM quando `check_deadline` levanta `TIMEOUT` após `consume_llm` e antes do enqueue — teste discriminante `test_d1_timeout_antes_do_enqueue_reembolsa_debito` (orçamento preservado em 2) com **sensibilidade à mutação provada**: com o reembolso removido, o teste falha (1 failed reproduzido); `test_d1b` garante que TIMEOUT APÓS enqueue aceito continua consumindo a chamada (comportamento anterior preservado).

### Verificações executadas

- Suíte integral: `.venv/bin/python -m pytest tests/ -q` → **564 passed** (535 da base + 29 novos), 2 warnings pré-existentes, sem regressões; suíte da base (535 passed) reproduzida antes de iniciar.
- Compilação/imports dos módulos novos e alterados: OK.
- Mutação da correção D1 removida e restaurada com árvore conferida por `git diff` ao final.

### Limitações e pendências registradas (não são resultado medido)

- Nenhum conector de busca é admitido — questão aberta do plano permanece ABERTA; a rota `curate` só opera quando um backend de busca for escolhido/configurado em decisão própria (sem ele, `CONNECTOR_DISABLED`, §6).
- O conector Google permanece NÃO ADMITIDO: verificação documental de update/delete condicional não foi realizada e não há credenciais para testes; se uma futura verificação documental ocorrer, a admissão exige além disso testes de falha de rede contra backend real.
- O transporte real (`urllib`) dos dois conectores não é exercitado contra rede externa nos testes (sem rede real permitida); a validação de destino e a construção de precondições estão FORA do seam de transporte e são testadas; um smoke com servidor local de verdade não faz parte do aceite.
- `read_one` do CalDAV usa o mesmo REPORT de coleção (MVP, coleções locais pequenas) — nenhuma suposição de mapeamento filename→UID além do fallback documentado é inventada; `transcript_read` existe no contrato de estados mas nenhum conector de transcrição é admitido no MVP.
- Todos os limites numéricos (10 s, 5 MiB, 2 redirects, 5 candidatos, 3 fetches) são defaults de ensaio do §6 — nunca apresentados como resultados medidos.

## Notas

### Dificuldade esperada
5/10 — Contratos claros, mas testes de falha de rede exigem fixtures; risco de prometer dedup/comportamento não verificado.

### Dificuldade sentida
4/10 — Contratos da 013/014 bem preparados (o dispatcher de `calendar.apply` já tinha todos os estados), o que reduziu o risco principal. Pontos de atrito: (1) desenhar o seam de transporte de forma que os testes de falha de rede sejam honestos sem rede real — a invalidação de destino e as precondições tiveram que ficar FORA do transporte injetado para que o seam não burlasse a segurança; (2) a barreira de IP privado/loopback bloqueia localhost, então os testes usam resolução real de nomes literais/IPs públicos (93.184.216.34) e transporte falso para o laço de redirects; (3) o parsing de multistatus exigiu escapar CRLF como entidades XML para não corromper o ICS na reconciliação por leitura; (4) o teste de candidatos (W7b) revelou que o limite efetivo da rota é o de FETCHES (3), não o de candidatos — a asserção foi alinhada ao comportamento normativo real em vez de prometer 5 leituras. A dívida da 014a foi de execução simples com mutação para provar discriminação.

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
