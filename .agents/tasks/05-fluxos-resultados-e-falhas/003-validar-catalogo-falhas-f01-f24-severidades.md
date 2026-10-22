# Task 003: Validar o catálogo de falhas F01–F24 e as severidades S1–S4

Estado: pendente
Depende de: 002
Origem: nenhuma

## Prompt
Conferir a seção 3 ("Catálogo de falhas") de `fase2/documentos/05_fluxos_resultados_e_falhas.md` — a tabela F01–F24 — quanto a: (a) fidelidade — cada falha descreve ponto/causa, propagação/impacto e saídas/fluxos afetados coerentes com a etapa 4 (erros tipados com retryability, estados terminais, §12 limites) e com o sistema implementado (ex.: F15 timeout/ACK/`UNKNOWN_EFFECT` — ver reconciliação do conector CalDAV na 016a; F21 invalidação de índice/resumo — ver correção/substituição da 010a; F24 empacotamento com pin/hash — ver manifesto congelado da 017); (b) severidades — S1–S4 atribuídas conforme a escala do próprio documento (S1 qualidade localizada; S2 perda pedagógica/continuidade; S3 restrição, dado ou efeito comprometido; S4 indisponibilidade/corrupção generalizada) e rotuladas como **potenciais, não frequência observada**; (c) cobertura — as fronteiras de transformação (ingestão, extração, geração), persistência (memória, snapshot, backup) e efeito (agenda, sync) e a validade da avaliação têm ao menos uma falha. Se encontrar desvio, corrija **apenas o documento 05** em dif mínimo, preservando o sentido normativo, e registre em Evidências.

Restrições: `fase2/documentos/04_mapa_completo_do_sistema.md` é INTOCADO ("deve" é contrato; §15 prevalece); correções no documento 05 somente em dif mínimo com justificativa; severidades permanecem potenciais — nada pode ser apresentado como falha observada/frequência medida; IDs F01–F24 e S1–S4 permanentes; prosa em português; `python3 fase2/scripts/verificar_documentos.py` deve passar; commit de entrega e registro separados, sem amend/force-push/commits vazios; submódulo intocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — documento a materializar (entregável): seção 3, tabela F01–F24 e escala de severidade (linhas 45–74).
- `fase2/documentos/04_mapa_completo_do_sistema.md` — erros tipados/estados (§4, §12), limites (§3, §6, §9), §15 (fonte normativo, intocado).
- `eduagent/` e registros das tasks 010a/015b/016/016a/017 do plano 04 — comportamento real de reconciliação, fail-closed, invalidação e congelamento para coerência.
- `fase2/scripts/verificar_documentos.py` — verificação documental.

## Corretude
- [ ] C1 — As 24 falhas conferidas item a item (ponto/causa, propagação, saídas/fluxos citados existentes em W e O), com registro em Evidências; desvios corrigidos em dif mínimo ou justificados.
- [ ] C2 — Severidades S1–S4 coerentes com a escala do documento e rotuladas como potenciais; nenhuma falha descrita como observada; cobertura de fronteiras (transformação, persistência, efeito) e validade da avaliação confirmada.
- [ ] C3 — `python3 fase2/scripts/verificar_documentos.py` passa; mapa intocado; commits entrega/registro separados.

## Execução
- Modelo: <identificador real do executor>
- Base: <SHA completo antes da implementação>
- Entrega: <SHA(s) completos, sem commits de registro, ou sem alteração de artefatos>
- Arquivos da entrega: <paths ou referência ao diff dos commits>
- Evidências: <comandos/procedimentos, resultados e limitações>

## Notas

### Dificuldade esperada
4/10 — Cruzar 24 falhas com erros tipados/estados da etapa 4 e com o comportamento real implementado; o risco é inflar severidade ou descrever como observado o que é potencial.

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

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
