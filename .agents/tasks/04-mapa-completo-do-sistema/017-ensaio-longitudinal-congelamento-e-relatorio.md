# Task 017: Ensaio longitudinal offline, congelamento e relatório de testes (mapa §13.8/10, §13.235)

Estado: aguardando revisão
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
- Orquestrador: —
- Alvo: —
- Avaliações: —
- Nota final: —
- Parecer: —
- Decisão: pendente
- Reversão: —
- Próximo passo: —

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
