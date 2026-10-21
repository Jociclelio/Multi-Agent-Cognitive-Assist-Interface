# Task 010: Memória temporal, contexto com checagem e correção/deleção (mapa §7, §13.6)

Estado: aguardando revisão
Depende de: 009
Origem: nenhuma

## Prompt
Implementar o Bibliotecário (mapa §7) em `eduagent/agents/librarian.py`, `eduagent/services/memory.py` e `eduagent/context.py`: eventos com `occurred_at`/`recorded_at`; fatos com validade e `supersedes`; origem `observed/asserted/inferred`; preferência declarada não é evidência de aprendizagem; "atual" recupera projeção vigente e correções; "como mudou" recupera versões em ordem temporal; contradição não conciliada devolve ambos os registros e pendência. Recuperação: filtros usuário/disciplina/tópico/tempo → busca lexical+densa de rounds/eventos → até 8 originais em 2.048 tokens + fatos atuais obrigatórios; correções relevantes podem substituir candidatos; similaridade não pode reativar fato superseded como atual; consulta de evidências antigas pode trazer versões anteriores explicitamente. Contexto contado após template/serialização: `input + 16384 + 2048 + 1024 ≤ 32768`, entrada máxima 13.312; ordem de montagem: instrução/schema → skill → tarefa/item/rubrica → âncoras/fatos confirmados → fontes → memória → turnos recentes; reduzir fontes periféricas/segmentar antes de resumir; jamais remover rubrica necessária e continuar avaliando. Síntese nasce de originais com claim→event_ids, cobertura temporal e verificação; checar exatamente datas, números, polaridade, ajuda e estado; falha mantém originais ou pede divisão; não encadear resumo de resumo; publicar síntese derivada, nunca apagar evento por compactação. Correção e deleção (`correct_fact`/`delete_data`): percorrem `artifact_dependencies`, invalidam versões publicadas, reconstituem projeções, propagam a derivados/checkpoints/traces; tombstone sem payload; backup identificado como pendente até expiração; sem hash reversível de texto excluído (§5, §15.1).

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §7 integral; §5 (deleção/backup); §15.1 (dependencies/invalidação/tombstones); §13.6.
- Storage (004), retrieval (007), redutor (009).

## Corretude
- [x] C1 — Recuperação temporal: "atual" vs "como mudou" corretos; fato superseded nunca reativado por similaridade (teste); contradição devolve ambos + pendência. — B1 (atual/history em ordem temporal), B2 (consulta textualmente igual ao valor antigo não reativa; `include_superseded` traz versão anterior explicitamente marcada, nunca como atual), B3 (ambos os registros + `pending=True`), B4 (preferência não atualiza competência), B5–B7 (filtros, teto 8/2048, correções substituem candidatos, pacote MemoryPack com origem).
- [x] C2 — Montagem de contexto na ordem do mapa com contagem pós-serialização e entrada ≤ 13.312; rubrica jamais removida; síntese verificada (datas/números/polaridade/ajuda/estado) com falha preservando originais. — X1 (ordem das seções do §7 e total ≤ 13312), X2 (contagem por seção sobre o texto renderizado — contador de caracteres), X3 (fontes periféricas → memória → turnos antigos; rubrica permanece), X4 (obrigatórias que não cabem → `RESOURCE_LIMIT` pedindo divisão, nunca avaliar sem rubrica), X5/S2 (claim sem suporte → falha, originais mantidos, publicação recusada), S1/S3 (claims verificados e publicados com `claim→event_ids`, cobertura temporal, arestas `derived_from`, nenhum evento apagado), S4 (resumo de resumo recusado), X6 (entrada > 13312 → `RESOURCE_LIMIT`).
- [x] C3 — Correção/deleção propaga por `artifact_dependencies` e invalida derivados/checkpoints/traces; tombstone sem payload; sem hash reversível (testes). — D1 (`correct_fact`: supersedes + `valid_to` + evento de correção + dependente invalidado via percurso BFS com `verification='failed'` e evento `artifact_invalidated`), D2 (tombstone sem payload e sem digest reversível do texto excluído — varredura de células por SHA-256 de variações do texto), D3 (purge de payload com gatilho `events_no_undrop_payload` provado, resumo derivado REMOVIDO — §5 propaga a derivados —, projeção reconstituída), D4 (backup pendente ~30 dias em escopo parcial; escopo `all` sem backup pendente), D5 (preview → confirm; sem confirmação é recusa tipada sem efeito). Propagação a checkpoints/traces: camadas ainda não existem (014/015) — a propagação fica registrada em tombstones/eventos de invalidação para consumo pelo replay delas; registrado como limite, não como feito.
- [x] C4 — Mapa intocado; commits separados; submódulo não tocado. — `git status`/`git diff` limpos em `fase2/` e `docs/playground-llmagenticsystem`; commits de entrega e registro separados (`e106baf` entrega, registro em commit próprio).

## Notas

### Dificuldade esperada
6/10 — Semântica temporal (supersedes/projeções) + checagem de síntese; risco de esconder recorte como "resumo".

### Dificuldade sentida
7/10 — A semântica temporal foi direta graças ao grafo `supersedes`/`valid_to` já previsto no DDL da 004; a parte mais delicada foi o orçamento do contexto: a primeira versão da redução criava retroalimentação (linha de ações crescia e consumia orçamento) e a redução gulosa de fontes deixava o turno mais recente sem espaço — resolvido com metadados de observabilidade fora do prompt e reserva do turno recente antes do ajuste de fontes. O verificador exato de claims (datas/números/polaridade/ajuda/estado) exigiu decisões conservadoras (claim sem elemento verificável falha) que foram documentadas como escolha de ensaio. Risco de "resumo esconder recorte" foi tratado com verificação literal por claim e proibição de síntese sobre resumo.

### Evidências de execução
- Suíte integral: `python -m pytest tests -q` → **336 passed** (313 anteriores + 23 novos; 21,7 s locais, sem rede/modelo real).
- Tabela de testes nova (código → caso) no cabeçalho de `tests/test_task010_memory_context.py`: B1–B7 (memória temporal/recuperação), X1–X6 (contexto), S1–S4 (síntese), D1–D5 (correção/deleção/backup), P1 (permissão da ferramenta `memory.query`).
- Verificação de documentos não se aplica (nenhum documento alterado); mapa conferido byte a byte por `git diff` vazio em `fase2/`.

### Decisões de codificação registradas
- `MemoryService` em `eduagent/services/memory.py`: recuperação reutiliza `tokenize`/`rrf_merge`/`HeuristicTokenCounter` da 007; ranking lexical de memória mantém scores ≤ 0 (IDF negativo com termo comum a todos os eventos não pode esvaziar a recuperação — diferente da busca documental, aqui não há abstinência).
- Projeção "atual" é estrutural (`valid_to IS NULL` + sem sucessor ativo), nunca de ranking — similaridade não reativa superseded (B2).
- Correção (§15.1) invalida dependentes (resumo vai a `verification='failed'`); deleção (§5) REMOVE derivados com tombstone — propagar deleção a claims derivados de payload excluído.
- Refs de fato usam versão `revision + 1` (Ref do contrato exige versão ≥ 1; `facts.revision` começa em 0).
- Migração 0005: `tombstones(artifact_ref, kind, reason, tombstoned_at, backup_pending_until)` — sem payload e sem hash do conteúdo.
- Contexto: reduções registradas em `ContextAssembly.actions` (observabilidade, §12) fora do prompt serializado; turno mais recente reservado; síntese só via `Summarizer` injetado com verificação exata por claim; falha mantém originais que couberem, e divisão (`RESOURCE_LIMIT`) só quando nada couber ou obrigatórias excederem o orçamento.
- Defaults de ensaio (não medidos): retenção de backup 30 dias (proposta do §5), teto 8 originais/2048 tokens (normativo do §7), k1/b do BM25 herdados da 007.

### Entrega
- SHA da entrega: `e106baf326698eb8f83c81e6572d07fbae7aafbd`
- SHA da base: `17881ff782a8295cae0ca23d27a21af7c40e609f`
- Arquivos: `eduagent/services/memory.py`, `eduagent/context.py`, `eduagent/agents/librarian.py`, `eduagent/storage/migrations.py`, `tests/test_task010_memory_context.py`

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
