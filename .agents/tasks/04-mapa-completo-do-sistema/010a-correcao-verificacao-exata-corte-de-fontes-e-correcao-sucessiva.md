# Task 010a: Correção da 010 — verificação exata, corte de fontes e correção sucessiva

Estado: pendente
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
- [ ] C1 — Verificação exata: sonda do revisor vira regressão (número substring → `False`); número/data genuinamente presente continua verificando; par contraditório de polaridade falha fechado mantendo originais; nenhum evento apagado.
- [ ] C2 — Corte de fontes: com sequência "grande, pequena" sob orçamento limitado, nenhuma fonte mantida reaparece no resto; segmentação/síntese sem duplicidade; rubrica jamais removida e orçamento pós-serialização preservados (X1–X6 continuam verdes).
- [ ] C3 — Correção sucessiva: substituição por correção demonstrada por consulta antes/depois (refs alinhadas); original não reemitido quando sua correção já foi emitida; segunda correção de fato com sucessor ativo recusada com erro tipado (ou sucessor intermediário fechado com escolha documentada); `preview_delete` inexistente recusa tipada; suíte integral verde.
- [ ] C4 — Mapa e submodule intocados; commits de entrega e registro separados; docstring/flags menores ajustados.

## Execução
- Modelo: _a preencher pelo executor_
- Base: _SHA antes da implementação_
- Entrega: _SHA(s) da entrega_
- Arquivos da entrega: _paths_
- Evidências: _suíte, sondas, limitações_

## Notas

### Dificuldade esperada
4/10 — Correções localizadas com regressões dedicadas; o cuidado é não introduzir falso negativo no verificador exato nem quebrar X1–X6/D1–D5 existentes.

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
