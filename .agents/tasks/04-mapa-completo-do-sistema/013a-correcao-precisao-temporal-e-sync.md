# Task 013a: Correção — precisão temporal do ICS, fuso all-day no sync e robustez de confirmação/outbox

Estado: pendente
Depende de: 013
Origem: 013 (correção — decisão do master `e177547`; entrega `f72440c` e registro `d1ecc58` preservados, sem reversão)

## Prompt
Corrigir pontualmente a entrega da 013 em `eduagent/services/calendar.py` (e testes), preservando o design aprovado e sem reabrir decisões de codificação registradas. Itens, por prioridade:

1. **A-01 (alto, obrigatório — precisão temporal de segundos):** o formato ICS RFC5545 tem precisão de segundos, mas `build_calendar` (DTSTAMP/CREATED/LAST-MODIFIED), `verify_calendar` (comparação com `created_at`/`modified_at` persistidos) e `build_sync_ops` (comparação `event.dtstamp`/modified_at) usam microssegundos. Com relógio real (microssegundos ≠ 0), `render_plan` falha com divergência CREATED/DTSTAMP e o sync considera todo bloco desatualizado. Truncar para segundos a representação usada em ICS e nas comparações de igualdade (renderização, verificação e construção de ops), mantendo a regra §15.5: timestamps derivados da revisão persistida, reexportação da mesma revisão byte-idêntica, SEQUENCE só em mudança de evento. Adicionar teste de regressão com relógio/instantes de microssegundos ≠ 0 cobrindo render (sucesso e estabilidade), verify e build_sync_ops.
2. **A-02 (médio):** em `build_sync_ops`, o ramo all-day pré-converte start/end para meia-noite UTC antes de chamar `build_calendar(..., local_timezone=...)`, causando dupla conversão de fuso quando o serviço tem `local_timezone` ≠ UTC. Remover a pré-conversão e deixar a fronteira de dia ser aplicada uma única vez pela lógica existente (`_all_day_bounds`/`build_calendar`), com teste para serviço com fuso não-UTC.
3. **L-A1 (médio):** `apply_plan` valida a confirmação apenas no início do despacho; definir e implementar a revalidação imediatamente antes de cada efeito remoto (§15.1): se a confirmação ficar obsoleta (domínio/dependência alterada) entre a checagem inicial e o envio, interromper o lote com recusa tipada (sem aplicar efeitos restantes) e estado coerente com o protocolo §11 (efeitos já enviados entram em reconciliação por leitura; nada de retry cego). Teste com mutação de domínio entre checagem e envio (duplo de conector).
4. **L-A2 (baixo):** após timeout reconciliado como `NOT_APPLIED`, o status agregado pode permanecer `APPLIED`. Propagar o resultado não aplicado (ou parcial) no status final, coerente com os detalhes individuais; ajustar teste de timeout/reconciliação.
5. **G-A1 (baixo):** `_confirmation_from_row` faz `json.loads(dependencies_json)` assumindo objeto enquanto a migração 0007 usa `DEFAULT '[]'`; tornar o parser tolerante (lista vazia → conjunto vazio) ou alinhar o default da migração, sem migração destrutiva; teste do caminho.
6. **G-A2 (baixo):** igualdade de UPDATE remoto compara só SUMMARY/SEQUENCE/DTSTAMP; incluir DTSTART/DTEND na comparação para que remoto mutante com SEQUENCE/DTSTAMP intactos seja detectado; teste.

Restrições: `fase2/documentos/04_mapa_completo_do_sistema.md` INTOCADO ("deve" é contrato; §15 prevalece quando mais preciso); sem decisões de questões abertas do plano; nada apresentado como resultado medido; sem conexão real de sync (permanece na 016); sem amend/force-push/commits vazios; mapa, config e submodule intocados; commits de entrega e registro SEPARADOS; temporários em /tmp/opencode; suíte integral deve permanecer verde.

## Contexto
- `.agents/tasks/04-mapa-completo-do-sistema/013-ics-preview-confirmacao-outbox.md` — task mãe, contrato original, evidências e registro da revisão (seção Revisão com os seis achados).
- `eduagent/services/calendar.py` — alvo das correções (`build_calendar` ~:207-249 e :237-239; parser/`verify_calendar` ~:288-545; `approve_plan`/`_confirmation_from_row` ~:897-1259; `build_sync_ops` ~:1448-1712; `apply_plan` ~:1528-1582).
- `eduagent/storage/migrations.py` — migração 0007 (default de `dependencies_json`).
- `tests/test_task013_calendar_confirmation.py` — suíte existente (I1–I5, P1–P3, F1, A1–A6, B1–B3, S1–S6, M1) a estender, sem quebrar.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §9, §10, §11, §15.1, §15.5 (normativo).

## Corretude
- [ ] C1 — Com relógio/instantes de microssegundos ≠ 0: `render_plan` publica ICS válido e estável (mesma revisão → bytes idênticos), `verify_calendar` não diverge e `build_sync_ops` não marca bloco atual como desatualizado (A-01 corrigido, com teste de regressão).
- [ ] C2 — All-day em `build_sync_ops` para serviço com `local_timezone` ≠ UTC gera DATE com fim exclusivo no dia local correto, sem dupla conversão (A-02, com teste).
- [ ] C3 — `apply_plan` revalida a confirmação antes de cada efeito remoto: mutação de domínio/dependência entre checagem e envio interrompe o lote com recusa tipada, sem aplicar efeitos restantes, sem retry cego; status agregado coerente com reconciliação (L-A1 e L-A2, com testes).
- [ ] C4 — Parser de `dependencies_json` tolerante ao default da migração 0007 e igualdade de UPDATE incluindo DTSTART/DTEND (G-A1/G-A2, com testes); suíte integral verde (≥ 439 + novos), mapa/config/submódulo intocados, commits de entrega e registro separados.

## Execução
- Modelo: _preencher pelo executor_
- Base: _SHA completo antes da implementação_
- Entrega: _SHA(s) completos, sem commits de registro_
- Arquivos da entrega: _paths_
- Evidências: _comandos, resultados e limitações_

## Notas

### Dificuldade esperada
3/10 — correções pontuais e bem localizadas; cuidado principal é não quebrar a estabilidade byte-idêntica de reexportação e a semântica §15.5 de timestamps por revisão.

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

<!-- task-cycle: {"decision":"corrigir","next_task":".agents/tasks/04-mapa-completo-do-sistema/013a-correcao-precisao-temporal-e-sync.md","family":".agents/tasks/04-mapa-completo-do-sistema/011-demandas-atividades-e-politica-evidencia.md","plan":".agents/plans/04-mapa-completo-do-sistema/plan.md"} -->

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
