# Task 017: Ensaio longitudinal offline, congelamento e relatório de testes (mapa §13.8/10, §13.235)

Estado: fechada (9/10, `concluido` — última task do plano; plano 04 concluído)
Depende de: 016
Origem: nenhuma

## Prompt
Fechar o MVP (mapa §13.8 e §13.10, aceite §13.235): (1) ensaio longitudinal offline da rota completa (ingestão → pergunta/prática com pausas e retomadas → avaliação → replanejamento → exportação ICS → crash/recuperação), em dados de teste locais, dentro de limites de tempo razoáveis — se o ensaio exigir execução inviável no hardware, registrar o impedimento documentado em vez de encurtar silenciosamente o protocolo. (2) Congelar o manifesto: `manifest.json` e `uv.lock` com versões reais de pacotes, modelo, tokenizer, skills (hash) e perfil de sampling selecionado; a configuração é congelada antes do teste final; timezone só fixado após confirmação explícita (sem confirmação, registrar pendência e manter padrão neutro). (3) Verificar o aceite funcional do mapa §13.235 item a item, com evidência executável ou de inspeção: cada rota termina com estado definido; cada artefato cumpre o contrato §4; toda citação resolve; toda escrita tem recibo/versionamento; nenhum plano sem validação do verificador é publicado como aprovado; nenhum ICS sem plano confirmado; sessão retomada preserva item/ajuda/histórico; regra de evidências `insufficient/mixed/favorable` exata; ingestão acima dos limites recusada ou dividida; `MODEL_NOT_ADMITTED` bloqueia tutoria. (4) Emitir o relatório de testes conforme a etapa 8 (`fase2/documentos/08_mapa_completo_da_testagem.md` — referência; critérios quantitativos e dados são do mapa8), sem preencher ausência de resultados experimentais com estimativas inventadas: ausência de resultado é declarada como ausência. Baselines/ablações do mapa §13.10 pertencem à etapa 8: registrar o que fica para o mapa8, sem executar aqui.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §13.8, §13.10, §13.235.
- `fase2/documentos/08_mapa_completo_da_testagem.md` — referência para o formato do relatório (fora do escopo implementar sua suite quantitativa).
- Sistema completo (001–016).

## Corretude
- [x] C1 — Ensaio longitudinal offline executado (não apenas impedimento): rotas completas reais com pausas/retomadas, crash SIGKILL/recuperação na mesma sessão e backup/restore verificado; cada passo < 10 min (execuções separadas do próprio protocolo).
- [x] C2 — Manifesto congelado ANTES do ensaio final (`congelamento` em `manifest.json`): perfil non-thinking selecionado (comparativo thinking PENDENTE), hashes reais das skills/catálogo/BGE-M3/modelos de layout Docling, `uv.lock` inalterado com SHA registrado; timezone NÃO confirmada → `null` com pendência registrada; verificado por testes G-1…G-4.
- [x] C3 — Aceite §13.235 verificado item a item com evidência executável ou de inspeção (tabela no relatório, §3); abstinências fail-closed observadas no ensaio (multi-critério → `FORMAL_DIVERGENCE`) registradas, nada parcial aprovado.
- [x] C4 — Relatório `eval/relatorio-testes-mvp.md` conforme formato da etapa 8, sem resultados inventados (ausência declarada); baselines/ablações registrados como escopo do mapa8; mapa/fase2, docs, config e submodule intocados (`git diff` vazio); commits separados.

## Execução

- Identidade real do modelo: GLM-5.3-Flash (provider `sd2`, model id `GLM-5.3-Flash`, via `~/sd2-llm.sh`) — identidade informada pelo runtime da sessão.
- Base: `cfe025fc470b953caf2270df4f1e0e683151f205` (árvore limpa, pós-revisão da 016a; suíte 581 passed reproduzida na base antes de iniciar).
- SHA de entrega: `9c4538a3288c85b7b60bdc113a681c0b8eadf7ac` (commit de código/manifesto/ensaio/relatório; commit de registro é este, encontrado por `git log -- <task.md>`).
- Artefatos da entrega: `eval/ensaio_longitudinal.py` (novo — protocolo por passos), `eval/relatorio-testes-mvp.md` (novo — relatório), `manifest.json` (seção `congelamento`), `tests/test_task017_congelamento.py` (novo, 10 testes), e correções dos achados do ensaio em `eduagent/services/ingestion.py`, `eduagent/runtime.py`, `eduagent/cli.py`, `eduagent/services/memory.py`, `eduagent/graph.py`, `eduagent/agents/tutor.py`.

### Ensaio longitudinal (resumo; detalhe no relatório)

Componentes reais, sem dobras: Docling 2.141 (pin do lock) em subprocesso spawn/RLIMIT 4 GiB, BGE-M3 real (revisão `5617a9f…`), modelo Bonsai 2 PTQ1_0 **inalterado** via runtime fixado da task 002 (imagem `d88136167019`, build `b1-8444536`), GPU RTX 3060. Fluxo executado (evidências JSON em `/tmp/opencode/017/evidencias/`, temporário): setup → doctor (modelo `configured`, WAL ok, timezone null) → ingest com gate de confirmação (2 fatos ambíguos → pausa/retomada confirmada) + índice denso BGE-M3 + ativação pós-indexação → ask (explain completado, 0 citações — observado) → practice (quiz, waiting) → pistas 1→2 com item/ajuda preservados entre invocações → submit com abstinência fail-closed do monitor → 2º practice com rubrica convergida (1 critério) → submit-known correto (gabarito do domínio, privilégio de harness registrado) → topic `mixed` → plan (3 demandas) → confirmação → solver OPTIMAL (5 etapas) → preview → approve com digest → ICS RFC5545 (3 VEVENTs) → sonda de cancelamento (`cancelled`, stop_dispatch) → crash SIGKILL em turno em voo (integridade ok, retomada na mesma sessão completou) → backup/restore verificado (integrity/migrations/tombstones ok) → 30 traces com spans.

### Achados do ensaio corrigidos na entrega

1. Adaptador Docling × API 2.141 (`DocumentStream`, `iterate_items` em tuplas, `page_no`) — fecha o smoke pendente da 006/006a.
2. `fork`→`spawn` na extração: o fork herdava o torch do embedder e estourava o RLIMIT_AS de §3 (reproduzido: hang; corrigido e testado).
3. Fiação do extrator default no `RuntimeContext` (superfície real CLI/API agora ingere PDF; `ingestion.extractor: none` desliga).
4. CLI lê o manifesto congelado para capacidades (sem manifesto, não presume — §3.1).
5. `MemoryPack.Origin` × evento `demand_generated` (`origin='review_after_error'` quebrava TODO turno posterior com memória) — mapeamento para a origem do §7.
6. `operation_id` reusado entre turnos da mesma sessão (2º submit/plan → "digest do replay difere", §11) — IDs derivados do `turn_id`, estáveis no turno, distintos entre turnos.
7. Tutor publica item determinístico com rubrica multi-critério que o Monitor sempre abstém — agora exige 1 critério (ciclo de reparo).

### Impedimentos e pendências registradas (não são resultado medido)

- **OCR seletivo (§6.2) impedido no limite de §3**: código `por` não servido pelo EasyOCR (usa `pt`; tesseract fora do stack) — mapeamento é decisão pendente; com `pt`, o reconhecedor de página inteira nega alocação de ~1,14 GB dentro dos 4 GiB do subprocesso (fail-closed tipado observado). Texto nativo exercitado no smoke (ocr_source=None). Registrado como impedimento, sem encurtar protocolo.
- Comparativo thinking não executado (§3.1: só desenvolvimento); timezone permanece `null` sem confirmação explícita; reranker NÃO adotado e busca `CONNECTOR_DISABLED` (questões abertas preservadas); modelo real não emitiu citações nos turnos explain do ensaio (validador proíbe citação fictícia; maquinaria provada nas suítes 007/014).
- Suíte quantitativa do mapa8 (O01–O18, condições, seeds, splits), baselines/ablações e testbed: NÃO executados — etapa 8; ausência declarada como ausência no relatório.

### Verificações executadas

- Suíte integral: `.venv/bin/python -m pytest tests/ -q` → **591 passed** (581 da base + 10 novos), sem regressões; suíte da base reproduzida antes de iniciar.
- Verificador documental: `python3 fase2/scripts/verificar_documentos.py` → `status: passed` (mapa/fase2 intocados; `git diff --name-only fase2/ docs/ config/ uv.lock` vazio; submodule intocado).
- Manifesto: JSON válido; hashes de skills conferidos contra arquivos e catálogo (teste G-1); `uv.lock` SHA confere (G-2).

### Limitações

- As evidências do ensaio vivem em `/tmp/opencode/017/` (temporário por design); o relatório registra os resultados observados e o driver é versionado para reprodução.
- O ensaio é aceito funcional mecânico (1 usuário, dados sintéticos, 1 documento): não mede qualidade, disponibilidade nem eficácia pedagógica — etapas do mapa8.

## Notas

### Dificuldade esperada
6/10 — Consolidação de aceite com execução real; risco de inflar resultados ou encurtar o ensaio.

### Dificuldade sentida
7/10 — A consolidação em si foi tranquila, mas o ensaio com componentes REAIS (Docling + BGE-M3 + modelo 27B) revelou quatro bugs de integração que as suítes com dobras não pegavam (API do Docling 2.141, fork×RLIMIT_AS com torch no pai, `MemoryPack.Origin` com eventos de demanda, reuso de `operation_id` entre turnos) — cada um exigiu diagnóstico honesto, correção mínima e regressão discriminante, com risco constante de inflar resultado ou fingir sucesso (ex.: índice "publicado" sem embedder real; OCR registrado como impedimento após duas tentativas calibradas, não encurtado silenciosamente). Coordenação do protocolo por passos com o servidor do modelo em container e o gate de confirmação do grafo adicionou atrito operacional (sessões UUID, pausas/retomadas corretas).

### Revisão
- Orquestrador: GLM-5.3-Flash (provider `sd2`, model id `GLM-5.3-Flash`, via `~/sd2-llm.sh`) — master do ciclo opt-in, sessão dedicada.
- Alvo: base `cfe025fc470b953caf2270df4f1e0e683151f205`; entrega `9c4538a3288c85b7b60bdc113a681c0b8eadf7ac` (código/manifesto/ensaio/relatório); registro `ffdbffa9b3ee7d29895ae003cfe32e8f658f8033`. SHAs e separação de commits conferidos por `git log/show`; árvore limpa durante toda a rodada; submodule intocado.
- Modo da rodada: **sequencial** (GLM → qwen3-27b → luna) — a revisão exige rodar a suíte no venv compartilhado e inspecionar artefatos do ensaio no mesmo host; precedente do repositório (14a/15/15a/15b/16/16a). Motivo registrado conforme contrato.
- Avaliações (três modelos distintos, retorno completo):
  - `sd2/GLM-5.3-Flash` — 9/10, aprovado. C1–C4 verificados com evidência própria: evidências JSON por passo em `/tmp/opencode/017/evidencias/` com timestamps coerentes, domínio SQLite inspecionado read-only (abstinência `formal_divergence`, pistas 1→2, `mixed`, digest `626fb8ef…`, crash SIGKILL com `integrity_check=ok` e retomada na mesma sessão), hashes recompute (uv.lock/catálogo/5 skills conferem), suíte **591 passed** reproduzida (G-5 real, sem skip). Achados baixos: R017-A1 evidência de passo sobrescrita em invocações repetidas do driver (`practice.json`/`ask.json`) — abstinência provada no domínio autoritativo; R017-A2 nomenclatura `ask-crash-recovery` inexistente no `crash.json`; R017-A3 narrativa "quatro bugs" no commit de registro vs. sete corrigidos; R017-A4 (escopo, para o master) tensão textual §13.10 item 10 × transferência de baselines/ablações ao mapa8 — ratificada como coerente com §13.235 e com o contrato da task.
  - `sorgan-qwen/qwen3-27b` — 9/10, aprovado. Sondas próprias: hashes recompute (uv.lock, skills, catálogo, 6 arquivos BGE-M3, 2 modelos de layout, GGUF Bonsai 2 conferem), domínio/checkpoints read-only, suíte 591 passed reproduzida, 5 sondas de mutação discriminantes (P1/P2, M-1/M-2, O-1/O-2 — reverter `operation_id` reproduz o bug real), smoke Docling real reproduzido em cópia isolada. Achados baixos: QW-01 janela de crash heurística (kill não auditável a posteriori; integridade+retomada provadas); QW-02 `crash.json` lista `session_id None` (cosmético); QW-03 precedência do congelamento sem timestamp próprio (consistente com todas as evidências).
  - `openai/gpt-6-luna` — 9/10, aprovado. Verificação por inspeção (manifesto, SHA do `uv.lock` conferido, evidências JSON, relatório, diff de isolamento) e suíte **591 passed** reproduzida; sem achados corretivos. Limitação registrada: não repetiu o ensaio nem sondas de mutação — coberta pela reprodução independente de GLM e qwen.
- Síntese: convergência factual total nos três revisores sobre C1–C4; divergência apenas de profundidade de reprodução (luna mais provisória, como no precedente 12a/13a/14a). Todos os achados são baixos, de higiene de evidência/robustez do driver de ensaio ou narrativos — nenhum impacto no aceite funcional, na integridade do domínio ou na honestidade do relatório. Nada parcial aprovado silenciosamente; ausências e impedimento do OCR declarados como tais.
- Nota final: 9/10 — execução real com componentes reais provada por evidência independente de dois revisores com sondas; não 10 pelos resíduos de higiene do driver (R017-A1/A2, QW-01/02), registrados como dívida opcional de robustez para micro-correção futura, sem reabrir a task.
- Parecer: aceite funcional §13.235 item a item com evidência executável/inspeção (tabela §3 do relatório, confirmada independentemente); manifesto congelado antes do teste final com hashes reais e timezone `null` pendente; relatório honesto conforme formato da etapa 8, sem métricas inventadas; questões abertas do plano preservadas (reranker não adotado, busca `CONNECTOR_DISABLED`, thinking pendente, timezone pendente); mapa/fase2, docs, config, submodule e `uv.lock` intocados; commits entrega/registro separados.
- Decisão: `concluido` — última task da sequência 001→017; todas as famílias do plano fechadas/resolvidas; critérios de conclusão do plano com evidência (aceite §13.235, manifesto congelado, relatório emitido). Nenhuma subtask criada: resíduos são dívida opcional registrada; etapa 8 (mapa8) e questões abertas permanecem fora do MVP por design, não são lacuna deste plano.
- Reversão: não se aplica — sem artefatos a reverter.
- Próximo passo: plano 04-mapa-completo-do-sistema concluído; ciclo encerrado com `advance` `concluido`. Pendências vivas registradas (não bloqueiam o MVP): comparativo thinking, timezone (só com confirmação explícita), seleção de reranker em validação, conector de busca, suite quantitativa/baselines/ablações do mapa8, dívidas opcionais de robustez (R017-A1/A2, QW-01/02/03 e resíduos de tasks anteriores documentados no índice).

<!-- task-cycle: {"decision":"concluido","next_task":null,"family":".agents/tasks/04-mapa-completo-do-sistema/011-demandas-atividades-e-politica-evidencia.md","plan":".agents/plans/04-mapa-completo-do-sistema/plan.md"} -->

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
