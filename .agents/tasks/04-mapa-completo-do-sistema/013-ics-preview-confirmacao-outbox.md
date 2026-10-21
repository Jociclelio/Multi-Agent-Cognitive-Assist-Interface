# Task 013: ICS RFC5545, confirmação e outbox (mapa §9, §13.7 parte 2)

Estado: pendente
Depende de: 012
Origem: nenhuma

## Prompt
Implementar a exportação ICS e o fluxo de confirmação (mapa §9) em `eduagent/services/calendar.py` com `calendar.render`: ICS por `icalendar` — VCALENDAR `VERSION:2.0`/PRODID; VEVENT UID/DTSTAMP/DTSTART/DTEND/SUMMARY; UTF-8/CRLF/folding; UTC `Z` para início/fim com fim exclusivo; exportação simples **sem METHOD**; UID UUID estável por bloco lógico; CREATED da criação; DTSTAMP/LAST-MODIFIED da última revisão persistida e SEQUENCE da revisão — retries/reexportações da mesma revisão não alteram timestamps; SEQUENCE começa em 0 e incrementa apenas se campos de evento mudam (§15.5); all-day usa DATE com fim exclusivo no dia seguinte; parser independente valida round-trip; importador manual pode duplicar apesar de UID — não prometer dedup universal. Persistir em `logical_blocks`: created_at, modified_at, event_sequence, summary, value_type, source_demand_id, actual_start/end (§15.5). Remoção no ICS é ausência na exportação, não comando remoto de delete; remoto só remove com operação confirmada. Confirmação (`approve_plan`): vincula `plan_id/revision/digest`; guarda `base_revision`, `approval_revision` pós-commit e conjunto/hash das dependências; alteração posterior invalida confirmação; nova outbox exige domínio igual à `approval_revision` (§15.1); confirmação/outbox conjuntas podem ocorrer no mesmo commit. `calendar.apply` (dispatcher determinístico, §10) exige confirmação atual; outbox somente após confirmação. Sync MCP/CalDAV/Google: nesta task, apenas os contratos e estados (`read/create/update/delete` com IDs/precondições; href estável; `If-None-Match: *`; `If-Match` ETag; update/delete condicional do Google só após verificação de documentação específica) — conexão real é admitida na task 016; timeout→`UNKNOWN_EFFECT`→read/reconcile, sem retry cego; alteração externa→conflito e novo preview; se o conector não preservar leitura/IDs/versão, manter ICS/preview e declarar não admitido.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §9 (ICS/sync), §15.1 (confirmação/outbox), §15.5 (identidade de blocos), §13.7; tabela `calendar.render`/`calendar.apply` (§10).
- Solver/preview (012), commit idempotente (005), contratos (003).

## Corretude
- [ ] C1 — ICS conforme RFC5545/§9: sem METHOD, UID estável, timestamps estáveis por revisão, SEQUENCE só em mudança de evento (testes com reexportação idêntica e com revisão).
- [ ] C2 — Parser independente valida round-trip; all-day com DATE e fim exclusivo; CRLF/folding verificados.
- [ ] C3 — Confirmação vincula plan/revision/digest; outbox exige `approval_revision` atual; alteração posterior invalida confirmação (testes); `calendar.apply` sem confirmação atual é recusado.
- [ ] C4 — Sync implementado só como contrato/estados (sem conexão real nesta task); mapa intocado; commits separados.

## Notas

### Dificuldade esperada
4/10 — ICS bem especificado; risco em estabilidade de timestamps e invalidação de confirmação.

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
