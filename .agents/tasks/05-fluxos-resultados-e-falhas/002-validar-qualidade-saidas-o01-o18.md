# Task 002: Validar a qualidade por saída O01–O18

Estado: aguardando revisão
Depende de: 001
Origem: nenhuma

## Prompt
Conferir a seção 2 ("O que constitui qualidade de cada saída") de `fase2/documentos/05_fluxos_resultados_e_falhas.md` — a tabela O01–O18 — quanto a: (a) cobertura — as 18 saídas cobrem artefatos internos (O01–O02, O12–O13, O16–O18), saídas ao estudante (O03–O11) e operacionais, sem lacuna de artefato previsto no contrato §4 da etapa 4; (b) fidelidade — "conteúdo necessário" e "perda de qualidade típica" de cada saída são coerentes com o contrato Pydantic/tabela §4 do mapa e com os artefatos reais do sistema implementado (ex.: O14 exige ICS RFC5545 com UID/versão/recibo — ver `eduagent/services/`; O17 traces com falhas incluídas; O18 manifesto com hashes e `uv.lock`); (c) consistência interna — cada saída citada na matriz W01–W12 existe na tabela e vice-versa (todas as O são alcançáveis por algum fluxo). Se encontrar desvio, corrija **apenas o documento 05** em dif mínimo, preservando o sentido normativo, e registre em Evidências.

Restrições: `fase2/documentos/04_mapa_completo_do_sistema.md` é INTOCADO ("deve" é contrato; §15 prevalece); correções no documento 05 somente em dif mínimo com justificativa; nada apresentado como resultado medido (perdas típicas são riscos potenciais, não ocorrências observadas); IDs O01–O18 permanentes; prosa em português; `python3 fase2/scripts/verificar_documentos.py` deve passar; commit de entrega e registro separados, sem amend/force-push/commits vazios; submódulo intocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — documento a materializar (entregável): seção 2, tabela O01–O18 (linhas 22–43).
- `fase2/documentos/04_mapa_completo_do_sistema.md` — contrato de artefatos da tabela §4 e saídas por rota (fonte normativo, intocado).
- `eduagent/`, `manifest.json`, `eval/relatorio-testes-mvp.md` — artefatos reais da v0.1 para coerência (planos 04, tasks 001–017).
- `fase2/scripts/verificar_documentos.py` — verificação documental.

## Corretude
- [x] C1 — As 18 saídas conferidas item a item contra o contrato §4 e os artefatos reais (conteúdo necessário e perdas típicas), com registro em Evidências; desvios corrigidos em dif mínimo ou justificados. **Sem desvio: dif zero justificado.**
- [x] C2 — Consistência interna matriz×tabela confirmada: todo O citado em W01–W12 existe; toda O é alcançável por algum fluxo; nenhuma perda típica descrita como ocorrência medida.
- [x] C3 — `python3 fase2/scripts/verificar_documentos.py` passa; mapa intocado; commits entrega/registro separados (entrega: sem alteração de artefatos; só commit de registro).

## Execução
- Modelo: GLM-5.3-Flash (via `~/sd2-llm.sh`, provider `sd2`) — identidade informada pelo runtime
- Base: cd4e91129ce99ab13bd6abe66973039e4fa03c94
- Entrega: sem alteração de artefatos (conferência item a item sem desvio; dif zero no documento 05)
- Arquivos da entrega: nenhum (somente este registro)
- Evidências:
  - Procedimento: leitura integral da seção 2 (tabela O01–O18, linhas 24–43) de `fase2/documentos/05_fluxos_resultados_e_falhas.md` e conferência linha a linha contra a tabela de artefatos do §4 do mapa (SourceRef, AcademicFact, EvidencePack, MemoryPack, LearningItem, TutorTurn, Assessment, TopicState, StudyDemand, ScheduleProposal, Operation), os parágrafos de detalhe (§5–§12, §15.1–15.5) e os artefatos reais da v0.1.
  - (a) Cobertura: O01–O02/O12–O13/O16–O18 cobrem artefatos internos e operacionais (manifesto/blocos, fatos, demandas, planos, operações, traces, empacotamento); O03–O11 cobrem as saídas ao estudante (pacote, explicação, item, flashcard, turno, avaliação, estado, memória, síntese); nenhuma lacuna encontrada — cada artefato obrigatório do §4 tem linha correspondente (SourceRef→O01/O03; AcademicFact→O02; EvidencePack→O03; LearningItem→O05; TutorTurn→O07; Assessment→O08; TopicState→O09; StudyDemand→O12; ScheduleProposal→O13; Operation→O16; MemoryPack→O10/O11).
  - (b) Fidelidade, exemplos verificados no código: O14 (ICS) — `eduagent/services/calendar.py` produz UID (UUID estável por bloco lógico), DTSTAMP/CREATED/LAST-MODIFIED/SEQUENCE (versão) e outbox/recibo (`EVENT_CALENDAR_OUTBOX`, `receipt⇔committed`), coerente com "UID/versão/recibo" e RFC5545; O16 — `eduagent/services/effects.py` verifica operation_id primeiro e reutiliza recibo (idempotência), coerente com "operação identificável/efeito conferido"; O17 — traces/spans do mapa §12 com falhas no denominador, sem alegação de medição; O18 — `manifest.json` com SHA-256 de modelo/runtime/skills e `eduagent/services/backup.py` com `wal_checkpoint(TRUNCATE)`, manifesto SHA-256 por arquivo e restore verificado, coerente com "hashes/instalação/restore verificáveis" e perda "DB copiado sem WAL".
  - Alinhamentos v0.1 obrigatórios: zero ocorrências de "America/Sao_Paulo", de reranker adotado e de resultado medido no documento 05 (grep); O15/W09 coerentes com `CONNECTOR_DISABLED` em `eduagent/services/web.py` (sem conector de busca, rota `curate` desabilitada via network_gate) — busca/Google não aparecem como capacidade garantida; W08 mantém sync opcional entre colchetes; severidade rotulada como potencial (linha 47), perdas típicas formuladas como riscos.
  - (c) Consistência matriz×tabela: extração de todos os IDs O citados em W01–W12 (linhas 9–20) e da tabela O01–O18 via grep — ambos os conjuntos são exatamente {O01..O18}; toda saída é alcançável por algum fluxo.
  - Verificador: `python3 fase2/scripts/verificar_documentos.py` → status "passed" (flows 12, outputs 18, failures 24, local_links_checked 39, exit 0); `git status` limpo antes e depois; mapa 04 intocado (nenhuma alteração em árvore limpa sobre a base); submódulo intocado.
  - Limitações: conferência documental/estática de fidelidade (leitura de contratos e código), sem execução do sistema; nenhuma métrica de qualidade foi medida nem inferida — ausência de resultado quantitativo permanece declarada como ausência (etapas 6/7 e mapa de testagem fora do escopo).

## Notas

### Dificuldade esperada
3/10 — Conferência de tabela de qualidade contra contratos e artefatos reais; exige cruzar 18 linhas com o mapa §4 e o código entregue.

### Dificuldade sentida
3/10 — Conferência de tabela contra contratos e artefatos reais foi direta: a tabela O01–O18 do documento 05 está alinhada ao contrato §4 e ao código entregue, sem desvios; o esforço principal foi cruzar 18 linhas com o mapa §4, os parágrafos de detalhe e os serviços implementados (calendar/effects/backup/web/manifesto).

### Revisão
- Orquestrador: —
- Alvo: <SHAs da entrega e versão do registro revisado>
- Avaliações: <modelo A: _/10; modelo B: _/10; modelo C: _/10>
- Nota final: _/10
- Parecer: <síntese dos achados, evidências, divergências e Corretude pendente>
- Decisão: <fechar | corrigir | reiniciar | repartir; pendente se bloqueada>
- Reversão: <SHA ou não se aplica>
- Próximo passo: <subtasks em ordem ou próxima task liberada>

Plano: [plan.md](../../plans/05-fluxos-resultados-e-falhas/plan.md)
