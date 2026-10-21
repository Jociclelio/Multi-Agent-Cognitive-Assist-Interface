# Task 010: Memória temporal, contexto com checagem e correção/deleção (mapa §7, §13.6)

Estado: pendente
Depende de: 009
Origem: nenhuma

## Prompt
Implementar o Bibliotecário (mapa §7) em `eduagent/agents/librarian.py`, `eduagent/services/memory.py` e `eduagent/context.py`: eventos com `occurred_at`/`recorded_at`; fatos com validade e `supersedes`; origem `observed/asserted/inferred`; preferência declarada não é evidência de aprendizagem; "atual" recupera projeção vigente e correções; "como mudou" recupera versões em ordem temporal; contradição não conciliada devolve ambos os registros e pendência. Recuperação: filtros usuário/disciplina/tópico/tempo → busca lexical+densa de rounds/eventos → até 8 originais em 2.048 tokens + fatos atuais obrigatórios; correções relevantes podem substituir candidatos; similaridade não pode reativar fato superseded como atual; consulta de evidências antigas pode trazer versões anteriores explicitamente. Contexto contado após template/serialização: `input + 16384 + 2048 + 1024 ≤ 32768`, entrada máxima 13.312; ordem de montagem: instrução/schema → skill → tarefa/item/rubrica → âncoras/fatos confirmados → fontes → memória → turnos recentes; reduzir fontes periféricas/segmentar antes de resumir; jamais remover rubrica necessária e continuar avaliando. Síntese nasce de originais com claim→event_ids, cobertura temporal e verificação; checar exatamente datas, números, polaridade, ajuda e estado; falha mantém originais ou pede divisão; não encadear resumo de resumo; publicar síntese derivada, nunca apagar evento por compactação. Correção e deleção (`correct_fact`/`delete_data`): percorrem `artifact_dependencies`, invalidam versões publicadas, reconstituem projeções, propagam a derivados/checkpoints/traces; tombstone sem payload; backup identificado como pendente até expiração; sem hash reversível de texto excluído (§5, §15.1).

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §7 integral; §5 (deleção/backup); §15.1 (dependencies/invalidação/tombstones); §13.6.
- Storage (004), retrieval (007), redutor (009).

## Corretude
- [ ] C1 — Recuperação temporal: "atual" vs "como mudou" corretos; fato superseded nunca reativado por similaridade (teste); contradição devolve ambos + pendência.
- [ ] C2 — Montagem de contexto na ordem do mapa com contagem pós-serialização e entrada ≤ 13.312; rubrica jamais removida; síntese verificada (datas/números/polaridade/ajuda/estado) com falha preservando originais.
- [ ] C3 — Correção/deleção propaga por `artifact_dependencies` e invalida derivados/checkpoints/traces; tombstone sem payload; sem hash reversível (testes).
- [ ] C4 — Mapa intocado; commits separados; submódulo não tocado.

## Notas

### Dificuldade esperada
6/10 — Semântica temporal (supersedes/projeções) + checagem de síntese; risco de esconder recorte como "resumo".

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
