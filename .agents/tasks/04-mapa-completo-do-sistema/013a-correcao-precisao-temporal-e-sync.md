# Task 013a: Correção — precisão temporal do ICS, fuso all-day no sync e robustez de confirmação/outbox

Estado: fechada (9/10, fechar)
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
- [x] C1 — Com relógio/instantes de microssegundos ≠ 0: `render_plan` publica ICS válido e estável (mesma revisão → bytes idênticos), `verify_calendar` não diverge e `build_sync_ops` não marca bloco atual como desatualizado (A-01 corrigido, com teste de regressão).
- [x] C2 — All-day em `build_sync_ops` para serviço com `local_timezone` ≠ UTC gera DATE com fim exclusivo no dia local correto, sem dupla conversão (A-02, com teste).
- [x] C3 — `apply_plan` revalida a confirmação antes de cada efeito remoto: mutação de domínio/dependência entre checagem e envio interrompe o lote com recusa tipada, sem aplicar efeitos restantes, sem retry cego; status agregado coerente com reconciliação (L-A1 e L-A2, com testes).
- [x] C4 — Parser de `dependencies_json` tolerante ao default da migração 0007 e igualdade de UPDATE incluindo DTSTART/DTEND (G-A1/G-A2, com testes); suíte integral verde (≥ 439 + novos), mapa/config/submódulo intocados, commits de entrega e registro separados.

## Execução
- Modelo: GLM-5.3-Flash (provider `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime
- Base: `dc00d7993586298299e6a452e5722ce8680706cb` (criação da subtask; entrega `f72440c` e registro `d1ecc58` da 013 preservados, sem reversão)
- Entrega: `8ddbaea` (commit único de código — `eduagent/services/calendar.py` + `tests/test_task013_calendar_confirmation.py`)
- Arquivos da entrega: `eduagent/services/calendar.py`, `tests/test_task013_calendar_confirmation.py`
- Evidências:
  - Sonda pré-correção (base) reproduziu o achado A-01: `build_calendar` com `created_at`/`modified_at` em microssegundos serializa em segundos (icalendar trunca), mas `verify_calendar` comparava com micros → `['CREATED divergente…', 'DTSTAMP/LAST-MODIFIED divergentes…']` → `render_plan` falharia com INTERNAL_FAILURE; `build_sync_ops` comparava `event.dtstamp` (segundos) contra `_utc(modified_at)` (micros) → todo bloco desatualizado. Sonda pós-correção: `verify_calendar` → `[]`.
  - Correções: helper `_ics_moment` (trunca para segundos) aplicado em `build_calendar` (DTSTAMP/CREATED/LAST-MODIFIED), `verify_calendar` e `build_sync_ops` (comparação de DTSTAMP), preservando §15.5 (persistidos mantêm precisão original; reexportação byte-idêntica; SEQUENCE só em mudança de evento — I2/I3/I4/P1 verdes); pré-conversão all-day removida de `build_sync_ops` (fronteira única em `_all_day_bounds`/`build_calendar`); `apply_plan` revalida via `check_confirmation_current` imediatamente antes de cada op remoto (recusa tipada VERSION_CONFLICT propaga; efeitos já enviados ficam para reconciliação por leitura; sem retry); status agregado propaga `NOT_APPLIED` total/parcial reconciliado; `_confirmation_from_row` tolerante a `'[]'` (linha legada com hash vazio valida só revisão de domínio em `check_confirmation_current`); igualdade de UPDATE inclui DTSTART/DTEND (também na reconciliação de update, mesma classe do achado).
  - Testes: 7 regressões novas R1–R7 (relógio `MicroClock` com microssegundos ≠ 0 cobrindo render sucesso + estabilidade + verify + `build_sync_ops`; all-day com offset fixo −3 — fuso America/Sao_Paulo permanece questão aberta, não decidido aqui; duplo `DomainMutatingConnector` mutando domínio e dependência entre checagem e envio; duplo `TimeoutLostConnector` para reconciliação NOT_APPLIED total e parcial; linha legada da 0007; remoto mutante DATE-TIME e DATE).
  - Comandos: `python3 -m pytest tests/test_task013_calendar_confirmation.py -q` → 32 passed (25 da 013 + 7 novas, sem quebra); `python3 -m pytest tests/ -q` → **446 passed** (439 + 7) em ~20 s; `git status` confirma apenas os dois arquivos da entrega alterados (mapa, config e submodule `docs/playground-llmagenticsystem` intocados).
  - Limitações: sem conexão real de sync (permanece na 016 — duplos de teste apenas); nenhum resultado medido apresentado; a escolha de interromper o lote propagando a `EduAgentError` tipada (sem `ApplyReport` intermediário) segue o idioma de recusas tipadas já registrado na 013; a reconciliação `UNKNOWN_EFFECT` de update continua comparando corpo parsed, agora também com DTSTART/DTEND (mais conservador).

## Notas

### Dificuldade esperada
3/10 — correções pontuais e bem localizadas; cuidado principal é não quebrar a estabilidade byte-idêntica de reexportação e a semântica §15.5 de timestamps por revisão.

### Dificuldade sentida
3/10 — correções pontuais e bem localizadas conforme previsto; a sonda reproduziu o achado A-01 de imediato e os critérios tinham caminho de teste direto. Único ajuste de rota: no caso "total" do R5 o lote continua após `NOT_APPLIED` reconciliado (decisão da 013 preservada — só CONFLICT/UNKNOWN interrompem), então o teste total precisou de dois updates perdidos para não aplicar efeito residual; a guarda de linha legada em `check_confirmation_current` (hash vazio) foi acrescentada para o caminho do parser G-A1 ficar coeso sem enfraquecer a invalidação por revisão de domínio.

### Revisão
- Orquestrador: master do ciclo (sd2/GLM-5.3-Flash, via `~/sd2-llm.sh`); rodada **sequencial** (suíte roda no venv compartilhado — mesmo motivo registrado nas rodadas da família 011/012/013).
- Alvo: base real `dc00d79500015005641134789aa54003dacc21fa` (conferida por `git rev-parse`; o SHA completo `dc00d7993586…` registrado na Execução era erro de transcrição — corrigido aqui pelo master, sem alterar commits), entrega `8ddbaea` (calendar.py + testes), registro `4c13c45`. Árvore limpa; entrega e registro separados; mapa/config/submódulo intocados (confirmado por diff e pelos três revisores).
- Avaliações (três modelos distintos, mesmas evidências alvo, sem compartilhamento de pareceres):
  - GLM-5.3-Flash (`task_review`, sessão própria): 9/10, aprovado. Suíte integral 446 passed reproduzida no `.venv`. C1–C4 verificados por leitura de diff + execução. Achado F-1 (baixo, do alvo recebido, não da entrega): SHA de base transcrito errado — corrigido na ata. F-2 (baixo): linha legada com `dependencies_hash` vazio pula validação por dependência em `check_confirmation_current` (janela restrita a linhas pré-0007; invalidação por domínio preservada; documentado e testado em R6).
  - GPT-6 Luna (`task_review`, sessão própria): 8/10, provisória/inconclusiva — não executou a suíte (python do sistema sem `rank_bm25`/`ortools`/`icalendar` em vez do `.venv`); sem correção de código identificada; pendência de execução coberta pela reprodução independente de GLM e Beam, conforme precedência já usada na família.
  - Beam Free (`task_review`, sessão própria): 9/10, aprovado definitivo. Suíte integral 446 passed reproduzida no `.venv` (~20 s); sondas MicroClock reproduzidas. Residual baixo: comparações de DTSTART/DTEND em `verify_calendar` e `build_sync_ops` usam precisão original; ICS serializa em segundos — divergência só ocorreria com blocos construídos diretamente com microssegundos ≠ 0, não atingível pelo solver (instantes alinhados a minuto); hardening opcional, fora do escopo do A-01.
- Síntese: as seis correções (A-01/A-02/L-A1/L-A2/G-A1/G-A2) implementadas e cobertas por R1–R7, confirmadas por dois revisores com execução independente (GLM e Beam, ambos 446 passed); §15.5 preservado (persistidos com micros, reexportação byte-idêntica R1, SEQUENCE intocada); revalidação §15.1 por efeito remoto com recusa tipada sem retry cego e efeitos enviados em reconciliação (R4/R5); divergência única entre revisores era de ambiente (Luna), não de mérito. Residuais baixos (F-2, DTSTART/DTEND com micros) documentados para correção pontual futura, sem reabrir a família.
- Nota final: 9/10 — correção pontual completa e bem isolada, com regressão específica por achado e reprodução independente; dedução apenas pelos residuais baixos documentados.
- Parecer: todos os critérios obrigatórios (C1–C4) comprovados com evidência de execução; sem achado alto/médio de mérito pendente.
- Decisão: fechar
- Reversão: não se aplica — entrega preservada (correção da 013 mantida; nenhum commit revertido).
- Próximo passo: família 013 resolvida por subtasks (013 fechada com nota 7/10 pela revisão original + 013a fechada com 9/10); liberar a task 014 (grafo LangGraph — intenções, rotas e checkpoints), dependente de 013.

<!-- task-cycle: {"decision":"fechar","next_task":".agents/tasks/04-mapa-completo-do-sistema/014-grafo-langgraph-intencoes-rotas-checkpoints.md","family":".agents/tasks/04-mapa-completo-do-sistema/011-demandas-atividades-e-politica-evidencia.md","plan":".agents/plans/04-mapa-completo-do-sistema/plan.md"} -->

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
