# Task 006a: Correção da 006 — adaptador Docling sem saída parcial e semântica de ciclos/PDD (mapa §6.1–3, §12, §13.3)

Estado: pendente
Depende de: 006
Origem: 006 — correção (revisão com decisão "corrigir"; entrega `4ca4b50` preservada, sem reversão)

## Prompt
Corrigir na entrega existente (`eduagent/services/ingestion.py`, `eduagent/agents/curator.py`) os gaps corroborados pela revisão da task 006 (probes independentes; detalhes e linhas na seção Revisão da 006), preservando a fronteira `BlockExtractor` injetável, o ciclo de versão `pending→indexed→active` e a suíte existente (163 testes verdes antes das mudanças):

1. **Truncamento silencioso no adaptador real (§3, §12; C1 da 006):** em `DoclingExtractor`/`_docling_convert`, um PDF com mais páginas que `max_pages` é descartado página a página e a versão fica `indexed` como completa. Correção esperada: exceder o limite no adaptador real produz erro tipado (`RESOURCE_LIMIT`) ou versão com falha/diagnóstico explícito de recusa — nunca indexação parcial aprovada como integral. Teste obrigatório: adaptador real (ou simulacro fiel do fluxo `_docling_convert`) com mais páginas que o limite não termina em versão `indexed` completa.
2. **OCR seletivo inerte no adaptador real (§6.2; C2 da 006):** o parâmetro `languages` de `DoclingExtractor.extract` nunca configura o `DocumentConverter` (idiomas só aparecem no manifesto; `ocr_source` é gravado `None` incondicionalmente). Correção esperada: plumbear `languages` às opções do pipeline do Docling (ex.: `PdfPipelineOptions` com OCR/idiomas) — ou, se a API instalada não o permitir sem o smoke real, falhar tipado quando OCR for solicitado e o adaptador não puder honrá-lo, com a limitação registrada em Evidências (manifesto nunca deve descrever intenção não executada como feita).
3. **Cancelamento/progresso pós-fato no adaptador real (§12; C2 da 006):** `on_page`/`cancelled` só são percorridos depois que o subprocesso termina. Correção aceitável (uma das duas, registrada): (a) plumbear cancelamento/progresso para dentro do subprocesso (arquivo de estado/pipe observado pelo filho); ou (b) registrar como contrato explícito do adaptador que o cancelamento é cooperativo-pós-conversão com o timeout de §3 como teto, cobrindo o caso por teste.
4. **Ciclos de pré-requisito só dentro do lote (§6.3/§9; C3 da 006):** `register_topics` valida apenas as arestas fornecidas na chamada; arestas persistidas de chamadas anteriores podem fechar ciclo (probe: `[(a,b)]` depois `[(b,a)]` → ciclo persistido sem detecção). Correção esperada: incluir as arestas existentes do curso (`topic_edges`) no grafo de detecção antes de qualquer escrita, mantendo a garantia "erro antes de qualquer efeito". Teste obrigatório do ciclo entre chamadas.
5. **Conflito PDD invisível entre versões (§6.3; C3 da 006):** `entity_id = uuid5(ns, f"{version_id}:{expression}")` namespacia a entidade pela versão, então a revisão real do mesmo fato numa versão nova do mesmo documento não confronta o PDD confirmado (probe: 0 conflitos). Correção esperada: derivar identidade da entidade de estábulo por documento/âncora de conteúdo (não pela versão) — ou, se o vínculo entre versões exigir decisão de modelagem maior, registrar o limite como comportamento explícito declarado e deixar a reconciliação entre versões/documentos para a memória (§7), com teste que documente o comportamento escolhido. Nada silencioso.
6. **Dedup de versões falhas (C1 da 006):** `_find_exact_duplicate` devolve qualquer versão com o mesmo SHA, inclusive `failed`/`pending`, sem caminho de retry acionável. Correção esperada: dedup considerar apenas versões reutilizáveis (`indexed`/ativa) — ou devolver diagnóstico acionável que indique como reprocessar; registrar a escolha.
7. **`block_id` inconsistente (§6.7; impacto na task 007):** o ID determinístico `p{n}b{n}` é calculado e descartado; `source_refs_for_version` devolve um ID que não fecha pela PK de `blocks`. Correção esperada: persistir o ID determinístico como PK/coluna UNIQUE de `blocks` (ou remover o cálculo morto e documentar que a citação fecha por página/ordem/`text_hash`), deixando a citação resolvível de forma inequívoca para a 007.
8. **Lambda não picklável (latente):** a lambda passada a `run_in_subprocess` só funciona com start method `fork`. Correção esperada: alvo module-level picklável (ou contexto `fork` explícito com justificativa registrada), com teste que não dependa do start method default.

Restrições: fonte normativa única `fase2/documentos/04_mapa_completo_do_sistema.md` INTOCADO (§6.1–3, §12, §15 prevalece quando mais preciso); não decidir questões abertas do plano (reranker, conector, timezone — manter `AMBIGUOUS_INPUT` sem zona confirmada); smoke real do pipeline de PDF do Docling continua pendente para a validação (task 017 ou autorização explícita de download de modelos de layout) — não fingir smoke; se a correção 2 exigir download não autorizado, registrar impedimento documentado e adotar a alternativa tipada. Suíte existente (163 testes) deve permanecer verde. Commits separados: entrega (código/testes) e registro (task.md com SHAs/evidências), sem amend/force-push/commits vazios. Mapa, submodule `docs/playground-llmagenticsystem`, `config/`, `pyproject.toml` e `uv.lock` intocados; nada apresentado como resultado medido; temporários em `/tmp/opencode`.

## Contexto
- `.agents/tasks/04-mapa-completo-do-sistema/006-ingestao-docling-ocr-proveniencia-fatos.md` — task mãe; seção Revisão com os achados A1–A7 por revisor que motivam esta correção.
- `eduagent/services/ingestion.py` — `DoclingExtractor`/`_docling_convert` (~1122–1220), `_find_exact_duplicate` (~599–611), `_persist_blocks` (~874–933), `run_in_subprocess`.
- `eduagent/agents/curator.py` — `entity_id`/reconciliação PDD (~387, ~581–618), `register_topics` (~857–929), `persist_fact_candidates` (~622–670).
- `tests/test_task006_ingestion.py` — suíte da 006 a estender (os probes da revisão descrevem os casos a cobrir).
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §6.1–3, §12, §15; §10 (`document.extract`).
- Contratos da 003 (`eduagent/contracts.py`) — `AcademicFact` e barreiras de confirmação; não alterar contratos sem necessidade.

## Corretude
- [ ] C1 — Adaptador real/simulacro fiel com PDF de mais páginas que `max_pages` não produz versão `indexed` completa (erro tipado ou falha/diagnóstico explícito); dedup não devolve versão `failed`/`pending` como reutilizável sem caminho acionável documentado.
- [ ] C2 — `languages` é aplicado ao conversor ou a solicitação de OCR não honrável falha tipada com limitação registrada; cancelamento/progresso plumbados ao subprocesso ou contratados explicitamente com teste; citação por bloco fecha de forma inequívoca (PK/UNIQUE do `block_id` determinístico ou regra documentada); alvo de subprocesso picklável ou `fork` explícito justificado.
- [ ] C3 — Ciclo fechado por arestas de chamadas anteriores é detectado antes de qualquer escrita (teste entre chamadas); comportamento do PDD confirmado entre versões é corrigido (identidade estável) ou declarado explicitamente com teste documentando o limite.
- [ ] C4 — Mapa intocado; suíte existente (163) verde; commits de entrega e registro separados; submodule, `config/`, `pyproject.toml` e `uv.lock` intocados; temporários em `/tmp/opencode`; smoke real do Docling não simulado.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
4/10 — Correções cirúrgicas e localizadas sobre padrões já estabelecidos na 006; risco moderado no item 5 (identidade de entidade entre versões) e no plumbing de cancelamento (item 3).

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
