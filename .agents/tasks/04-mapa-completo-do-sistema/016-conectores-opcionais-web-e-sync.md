# Task 016: Conectores opcionais — curadoria web e sync de calendário (mapa §6/§9, §13.9)

Estado: pendente
Depende de: 015
Origem: nenhuma

## Prompt
Implementar e admitir individualmente os conectores opcionais (mapa §6 curadoria web, §9 sync, §13.9): curadoria web — interface `search(query, language, max_results)->candidates` e `fetch(url)->resource`; até 5 candidatos/3 fetches, 10 s/5 MiB, dois redirects com revalidação; estados `metadata_only/text_read/transcript_read/unavailable`, URL final, data/hash e fonte; vídeo sem transcrição só recomendado por metadados, nunca resumido; conector de busca escolhido/configurado na implementação — sem ele, `CONNECTOR_DISABLED` (rota `curate` com `network_gate`); cache offline marcado com data, nunca fingido como consulta atual; `web.search/fetch` respeitam `network_enabled=false` e a política de rede da task 014. Sync de calendário — MCP expõe `read/create/update/delete` com IDs/precondições; CalDAV com href estável, criação `If-None-Match: *`, atualização `If-Match` ETag; Google: ID próprio de criação conforme backend, update/delete condicional **só depois de verificar documentação específica** (se não verificada, declarar não admitido — não inventar comportamento); timeout→`UNKNOWN_EFFECT`→read/reconcile sem repetição cega; alteração externa→conflito e novo preview; se o conector não preservar leitura, IDs e versão, manter ICS/preview e declarar não admitido. Cada conector é admitido individualmente após contratos e testes de falha de rede (timeout, redirect malicioso, resposta inválida); sem credenciais, não bloqueiam o núcleo.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §6 (curadoria web), §9 (sync), §13.9; tabela `web.search/fetch`/`calendar.apply` (§10).
- Task 013 (contratos de sync/outbox), 014 (network_gate/política), 015 (CLI/API).

## Corretude
- [ ] C1 — Curadoria web com limites/estados/hash conforme §6; sem conector configurado, `CONNECTOR_DISABLED` com comportamento testado; cache offline datado.
- [ ] C2 — Falhas de rede testadas (timeout/redirect/5 MiB); fetch bloqueia IP privado/loopback (herdado da 014, retestado na rota curate).
- [ ] C3 — Sync: MCP/CalDAV conforme contrato; Google condicional apenas com verificação documental registrada, senão não admitido; reconciliação por identidade com UNKNOWN_EFFECT sem retry cego.
- [ ] C4 — Conectores admitidos individualmente com registro em Evidências; sem credenciais o núcleo segue funcional; mapa intocado; commits separados.

## Notas

### Dificuldade esperada
5/10 — Contratos claros, mas testes de falha de rede exigem fixtures; risco de prometer dedup/comportamento não verificado.

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
