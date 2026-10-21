# Task 010a: Correção da 010 — verificação exata, corte de fontes e correção sucessiva

Estado: fechada
Depende de: 010
Origem: 010 (correção — decisão `corrigir`, 7/10, entrega `e106baf` preservada)

## Prompt
Corrigir na entrega da 010 os achados confirmados por três revisores, sem reescrever o desenho já aprovado (semântica temporal estrutural, tombstones, orçamento pós-serialização e propagação por `artifact_dependencies` permanecem):

1. **Verificação exata de números e datas (§7) — `eduagent/context.py`**: remover o pré-check por substring em `_has_number`/`verify_claim_against_sources` que faz `"12"` casar com `"120"` (sonda do revisor: `verify_claim_against_sources("resultado 12", ["a nota foi 120 pontos"])` devolve `True` — deve ser `False`). Exigir igualdade numérica contra os tokens extraídos por `_NUMBER_RE` das fontes (atentar a decimais como "7"/"7,0" e a não criar falso negativo para números presentes); aplicar o mesmo rigor às datas (extrair datas das fontes em vez de substring). Incluir regressão com o par da sonda e com número genuinamente presente.
2. **Polaridade/ajuda/estado com negação — `eduagent/context.py`**: a presença literal de token de polaridade não prova claims opostos (achado Luna A3); cobrir no verificador o caso em que a fonte contradiz o claim (negação/inversão) com teste de par contraditório — pode ser conservador (falhar fechado), desde que a falha preserve originais.
3. **Corte de fontes sem pressuposto de prefixo — `_fit_sources` (context.py)**: `rest = ordered[len(kept):]` assume que `kept` é prefixo de `ordered`; o laço guloso pode pular uma fonte grande e aceitar uma menor posterior, e o resto passa a incluir fonte já mantida (reproduzido pelo revisor: fonte mantida reaparece segmentada/sintetizada em duplicidade). Calcular as rejeitadas explicitamente (ex.: `rest = [f for f in ordered if f not in kept]`) e testar a sequência "grande, pequena" sob orçamento limitado.
4. **Correção-substituição coerente — `_apply_corrections`/`correct_fact` (`eduagent/services/memory.py`)**: (a) alinhar as referências consumidas por `_apply_corrections` com as de fato emitidas pelos eventos (`artifact_invalidated` aponta para fato; `EVENT_FACT_CORRECTED` traz `old_fact_ref`) de modo que a substituição de candidatos por correção relevante seja demonstrada por teste de consulta antes/depois da correção (achado Luna A1); (b) deduplicar por `event_id`/fato para não reemitir original cuja correção já foi emitida quando ambos coexistem na seleção (achado Beam A2, regressão obrigatória); (c) recusar com erro tipado (ou fechar a validade do sucessor intermediário, documentando a escolha) a correção de um fato que já possui sucessor ativo — hoje a segunda correção deixa dois fatos ativos como contradição pendente (achado GLM A-03, sonda: f3 e f4 ativos após duas correções).
5. **Menores**: (a) `preview_delete` com ID de fato inexistente deve levantar recusa tipada (`SOURCE_UNRESOLVED`), não `TypeError` (GLM A-05); (b) corrigir a docstring de invalidação que alega BFS "pelos dois sentidos" (GLM A-02); (c) mover a reconstituição de projeções para dentro do commit idempotente da deleção (ou registrar operação idempotente própria) — hoje um crash entre deleção e `reconstitute_topic_states` deixa projeção obsoleta sem retry (GLM A-04); (d) alinhar `projections_reconstituted` entre escopos (`facts` hoje devolve `False`) ou documentar por que o escopo `facts` não reconstitui (Beam A3).

Manter commits SEPARADOS (entrega e registro), mapa `fase2/documentos/04_mapa_completo_do_sistema.md` INTOCADO, submodule intocado, defaults como escolhas de ensaio (nada apresentado como resultado medido).

## Contexto
- `.agents/tasks/04-mapa-completo-do-sistema/010-memoria-temporal-e-contexto.md` — task mãe: contrato, evidências (B/X/S/D/P) e decisão da revisão.
- `eduagent/context.py` — verificador de claims (`verify_claim_against_sources`, `_has_number`, `_NUMBER_RE`) e montador (`_fit_sources`).
- `eduagent/services/memory.py` — `correct_fact`, `_apply_corrections`, `preview_delete`, `reconstitute_topic_states`, percurso de `artifact_dependencies`.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §7 (checagem exata; redução), §5, §15.1, §13.6.
- `tests/test_task010_memory_context.py` — tabela B1–B7/X1–X6/S1–S4/D1–D5/P1; adicionar regressões sem quebrar as existentes (suíte atual 336 passed).

## Corretude
- [x] C1 — Verificação exata: sonda do revisor vira regressão (número substring → `False`); número/data genuinamente presente continua verificando; par contraditório de polaridade falha fechado mantendo originais; nenhum evento apagado.
- [x] C2 — Corte de fontes: com sequência "grande, pequena" sob orçamento limitado, nenhuma fonte mantida reaparece no resto; segmentação/síntese sem duplicidade; rubrica jamais removida e orçamento pós-serialização preservados (X1–X6 continuam verdes).
- [x] C3 — Correção sucessiva: substituição por correção demonstrada por consulta antes/depois (refs alinhadas); original não reemitido quando sua correção já foi emitida; segunda correção de fato com sucessor ativo recusada com erro tipado (ou sucessor intermediário fechado com escolha documentada); `preview_delete` inexistente recusa tipada; suíte integral verde.
- [x] C4 — Mapa e submodule intocados; commits de entrega e registro separados; docstring/flags menores ajustados.

## Execução
- Modelo: GLM-5.3-Flash (via ~/sd2-llm.sh; provider `sd2`, model `GLM-5.3-Flash` — identidade informada pelo runtime)
- Base: `c3f4c70960b59690b61c5071b63171b466d033f6` (entrega da 010 `e106baf` preservada)
- Entrega: `fd3e35986a2ae50d13ce6419132bae97183cb2a8`
- Arquivos da entrega: `eduagent/context.py`, `eduagent/services/memory.py`, `tests/test_task010_memory_context.py`
- Evidências:
  - Sondas de reprodução pré-correção (registradas em sessão): `verify_claim_against_sources("resultado 12", ["a nota foi 120 pontos"])` → `True` (bug); `("ajuda nível 2", ["ajuda nível 23"])` → `True` (bug); negação na fonte (`"o resultado não foi correct"`) → `True` (bug); segunda `correct_fact` do mesmo fato deixava dois fatos ativos ("valor 51" e "valor 52"); após `correct_fact` com evento dependente, o original continuava na seleção (refs desalinhadas); `preview_delete` com ID inexistente era no-op silencioso em todos os escopos.
  - Pós-correção: sonda do revisor → `False`; número presente → `True`; decimal "7" vs "7,0" → `True` (igualdade numérica); data divergente → `False`, mesma data em formato distinto (`21/10/2026` vs `2026-10-21`) → `True`; pares contraditórios por inversão/negação → `False` mantendo pares coerentes → `True`.
  - Regressões novas R1–R9 em `tests/test_task010_memory_context.py` (tabela no docstring do módulo): R1 números exatos, R2 datas exatas, R3 negação/inversão com falha fechado e originais preservados, R4 corte "grande, pequena" sem pressuposto de prefixo (mantida aparece uma única vez; segmento vem da fonte grande), R5 substituição por consulta antes/depois com `artifact_ref`/`old_fact_ref`, R6 dedupe por `event_id` nas duas ordens, R7 recusa tipada (`SCHEMA_INVALID`) da segunda correção com estado preservado (um único fato ativo), R8 `SOURCE_UNRESOLVED` para ID inexistente em preview e delete, R9 reconstituição dentro do commit idempotente (falha na reconstituição reverte a deleção inteira — rollback total com payload não purgado e sem tombstones; incremento único de revisão) com escopo `facts` documentado como não reconstituinte (`topic_states` deriva de attempts/assessments, não da tabela `facts`).
  - Suíte integral: `python -m pytest tests/ -q` → **345 passed** (336 anteriores + 9 regressões; B1–B7/X1–X6/S1–S4/D1–D5/P1 todos verdes, nenhum quebrado ou reemitido).
  - Inspeção de git: `fase2/documentos/04_mapa_completo_do_sistema.md` e `docs/playground-llmagenticsystem` sem diff; diff confinado aos 3 arquivos da entrega. `ruff` não instalado no ambiente (sem runner de lint no projeto — registro, não aprovação).
  - Limitações: `reconstitute_topic_states` mantido como método público (escrita própria) para outros chamadores; `delete_data` não o usa mais. A escolha por recusa tipada (em vez de fechar a validade do sucessor intermediário) está documentada no docstring de `correct_fact` e no docstring do módulo.

## Notas

### Dificuldade esperada
4/10 — Correções localizadas com regressões dedicadas; o cuidado é não introduzir falso negativo no verificador exato nem quebrar X1–X6/D1–D5 existentes.

### Dificuldade sentida
5/10 — As correções em si são localizadas, mas três pontos exigiram cuidado: (1) o rigor numérico sem criar falso negativo (datas normalizadas por valor para não rejeitar data presente em formato distinto; igualdade numérica preserva "7" vs "7,0"); (2) alinhar `_apply_corrections` sem quebrar B6, que depende de `trigger_ref` — a solução consumiu as três refs emitidas (`trigger_ref`, `artifact_ref`, `old_fact_ref`) em vez de trocar uma pela outra; (3) provar a reconstituição dentro do commit idempotente: a sonda direta com `compute_topic_states` vazio não discriminava (statements vazios também não escrevem), então a regressão R9 usa falha injetada na projeção para provar atomicidade (rollback total) e incremento único de revisão. Descoberta de execução: `preview_delete` com ID inexistente não reproduzia `TypeError` na versão atual — reproduzia no-op silencioso; a recusa tipada `SOURCE_UNRESOLVED` cobre ambos (e também `delete_data`, que antes aplicava nada e devolvia sucesso).

### Revisão
- Orquestrador: GLM-5.3-Flash (provider `sd2`) — master do ciclo; rodada **paralela** (leitura de código/testes sem disputa de recursos compartilhados: sem build concorrente, GPU ou portas; cada revisor em sessão nova).
- Alvo: base `c3f4c70` (entrega da 010 `e106baf` preservada); entrega `fd3e359` (context.py, services/memory.py, test_task010_memory_context.py); registro `7bd320e`; HEAD em `7bd320e` com árvore limpa; mapa e submodule sem diff em `c3f4c70..7bd320e` (confirmado pelos três revisores).
- Avaliações: **sd2/GLM-5.3-Flash 9/10 — aprovada** (sondas próprias em /tmp/opencode + suíte integral 345 passed reproduzida); **openai/gpt-6-luna 7/10 — inconclusiva** (não executou a suíte: rodou pytest com interpretador sem `.venv` e falhou a coleta por `rank_bm25` ausente — limitação ambiental, não defeito da entrega; nenhuma sonda de código contradita, C1/C2 parcialmente provados por sondas próprias, C4 verificado por Git); **opencode/beam-free 9/10 — aprovada** (suíte focada 32 passed e integral 345 passed via `.venv/bin/python`, sondas de C1 reproduzidas, R4–R8 verdes). Quórum de três modelos distintos cumprido; nenhum substituto necessário.
- Síntese: os achados médios da revisão da 010 (substring numérico, prefixo em `_fit_sources`, percurso de correção-substituição) estão corrigidos com regressões reais R1–R9, provadas por três execuções independentes da suíte (executor, GLM e Beam — 345 passed) e por sondas convergentes de dois revisores. O achado A1 de Luna ("rank_bm25 ausente") foi resolvido como alarme ambiental: Beam reproduziu a suíte no `.venv` e registrou explicitamente que a execução exige esse interpretador, não sendo defeito da entrega. Resíduos de baixa severidade registrados por GLM, sem violar o prompt nem o §7: A-01 mapa de opostos de polaridade/estado cobre só `correct`↔`incorrect` (negação cobre o caso testado em R3); A-02 números dentro de datas podem servir de suporte numérico (resíduo herdado do desenho, coerente com o pedido); A-03 janela de negação heurística (2 palavras/32 caracteres), conservadora e documentada. Divergência Luna × GLM/Beam era só de ambiente de execução, não de fundo.
- Nota final: **9/10** — todos os critérios obrigatórios C1–C4 provados com evidência reproduzível e confirmação independente; resíduos documentados como dívida de baixa severidade, não bloqueantes.
- Parecer: fechada — os cinco itens do prompt implementados, suíte integral verde (345 passed, B/X/S/D/P intactos), mapa e submodule intocados, commits de entrega e registro separados, nada apresentado como resultado medido.
- Decisão: **fechar**
- Reversão: não se aplica — entrega aprovada.
- Próximo passo: task 011 (`.agents/tasks/04-mapa-completo-do-sistema/011-demandas-atividades-e-politica-evidencia.md`); família 010 resolvida por subtasks.

<!-- task-cycle: {"decision":"fechar","next_task":".agents/tasks/04-mapa-completo-do-sistema/011-demandas-atividades-e-politica-evidencia.md","family":".agents/tasks/04-mapa-completo-do-sistema/011-demandas-atividades-e-politica-evidencia.md","plan":".agents/plans/04-mapa-completo-do-sistema/plan.md"} -->

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
