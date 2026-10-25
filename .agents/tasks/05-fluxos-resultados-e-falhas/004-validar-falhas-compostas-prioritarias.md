# Task 004: Validar as seis falhas compostas prioritárias e suas exigências

Estado: aguardando revisão
Depende de: 003
Origem: nenhuma

## Prompt
Conferir a seção 4 ("Falhas compostas prioritárias") de `fase2/documentos/05_fluxos_resultados_e_falhas.md` — os 6 cenários compostos — quanto a: (a) fidelidade — cada cenário encadeia falhas do catálogo F01–F24 de forma coerente (OCR→prazo errado envolve F01/F02; erro correlacionado Tutor/Monitor envolve F06/F09; retry pós-timeout sobrescrevendo mudança externa envolve F14/F15; invalidação transitiva de resumo envolve F21; reexecução sem `operation_id` envolve F15 e o contrato §11; falhas fora do denominador de p95 envolve F22/F23); (b) exigências — cada cenário registra a exigência de mitigação correspondente (validação independente de fontes/julgamento; snapshot/ETag e reconciliação; invalidação transitiva; idempotência por `operation_id`; falhas permanentes no denominador) sem contradizer §11 (commit idempotente), §15.1 (snapshot/`domain_revision`) e §15.5 (verificador independente) do mapa; (c) honestidade — a ressalva de que o solver/verificador não elimina as falhas de montante (cenário 1) e que checkpoint sozinho não garante idempotência (cenário 5) permanece no texto. Se encontrar desvio, corrija **apenas o documento 05** em dif mínimo, preservando o sentido normativo, e registre em Evidências.

Restrições: `fase2/documentos/04_mapa_completo_do_sistema.md` é INTOCADO ("deve" é contrato; §15 prevalece); correções no documento 05 somente em dif mínimo com justificativa; cenários compostos são riscos potenciais — nada apresentado como ocorrência observada; IDs F permanentes; prosa em português; `python3 fase2/scripts/verificar_documentos.py` deve passar; commit de entrega e registro separados, sem amend/force-push/commits vazios; submódulo intocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — documento a materializar (entregável): seção 4, cenários 1–6 (linhas 76–83).
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §11 idempotência, §12 checkpoint/limites, §15.1 snapshot, §15.5 verificador (fonte normativo, intocado).
- Registros das tasks 005/010a/013a/015b/016/016a do plano 04 — implementação real de idempotência, reconciliação com ETag, invalidação e fail-closed para coerência.
- `fase2/scripts/verificar_documentos.py` — verificação documental.

## Corretude
- [x] C1 — Os 6 cenários conferidos item a item: encadeamento de falhas coerente com o catálogo e exigências de mitigação registradas, sem contradição com §11/§15.1/§15.5 do mapa; desvios corrigidos em dif mínimo ou justificados.
- [x] C2 — Ressalvas de honestidade preservadas (solver não elimina falha de montante; checkpoint não garante idempotência; falhas no denominador); nada como ocorrência medida.
- [x] C3 — `python3 fase2/scripts/verificar_documentos.py` passa; mapa intocado; commits entrega/registro separados.

## Execução
- Modelo: GLM-5.3-Flash (provider sd2, via ~/sd2-llm.sh)
- Base: 92e3e2ccd87c3a8a3b80c94a254039dd9abb0f85
- Entrega: sem alteração de artefatos — conferência item a item não revelou desvio que exigisse correção no documento 05 (dif zero em `fase2/documentos/05_fluxos_resultados_e_falhas.md` entre base e HEAD); único commit é o registro desta task.
- Arquivos da entrega: nenhum (apenas o registro `.agents/tasks/05-fluxos-resultados-e-falhas/004-validar-falhas-compostas-prioritarias.md` neste commit documental; ver o diff do commit para o conteúdo).
- Evidências:
  - **Leitura integral** da seção 4 do documento 05 (linhas 76–83, cenários 1–6) e das âncoras normativas do mapa: §11 (linhas 208–212 — commit idempotente por `operation_id`, checkpoint não atômico, `UNKNOWN_EFFECT` sem retry automático), §15.1 (linhas 243–251 — `domain_revision`, snapshot materializado, `artifact_dependencies` com `derived_from/corrects/supersedes` e invalidação de dependentes), §15.5 (linha 283 — "Verificação independente ainda obrigatória"), §9 (linha 172 — If-None-Match:*/If-Match ETag, timeout→unknown_effect→read/reconcile, não repetir cegamente) e tabela §10 (linha 204 — `calendar.apply` com ID/ETag/reconciliação).
  - **Cenário 1 (linha 78) — OCR→prazo, F01/F02:** "OCR troca data" = F01 (linha 51: "OCR/parser erra ordem/número/página"); "Curador confirma indevidamente" = F02 (linha 52: extração resolve ambiguidade sem confirmação; propagação "restrição falsa altera cronograma" corresponde a "solver produz plano ótimo para prazo errado" — o solver é correto sobre entrada errada, sem criar nova falha). Ressalva "O solver não elimina F01/F02" presente e coerente com §15.5: a verificação independente exige validade, não elimina falhas de montante.
  - **Cenário 2 (linha 79) — erro correlacionado, F06/F09:** "Tutor e Monitor compartilham modelo/gabarito→erro consistente" = F06 (linha 56); "memória compactada vira 'domina'" = F09 (linha 59: compactação perde polaridade); "Planejador reduz prática" corresponde à propagação de F06 ("falso progresso orienta prática e agenda"). Exigência "Validar fontes e julgamento independentemente" coerente com §15.2 (rubrica/julgamento) e §15.5 (verificação independente); formulada como exigência, sem afirmar capacidade implementada.
  - **Cenário 3 (linha 80) — retry pós-timeout, F14/F15:** "agenda externa muda" sob replan aprovado = F14 (linha 64: concorrência usa snapshot obsoleto); "retry pós-timeout sobrescreve mudança" = F15 (linha 65). Exigência "snapshot/ETag e reconciliação, não apenas UID" coerente com §15.1 (snapshot/versionamento) e §9/§11 (If-Match ETag, read/reconcile, `UNKNOWN_EFFECT` sem retry cego); "não apenas UID" é reconhecimento de insuficiência, não contradição — §15.5 garante que UID permanece em mudança de horário (identidade), mas identidade sozinha não reconcilia estado remoto.
  - **Cenário 4 (linha 81) — invalidação transitiva, F21:** "Correção registrada→resumo antigo permanece no índice→sessão retoma a versão errada" = F21 (linha 71); exigência "invalidação transitiva" = §15.1 (`artifact_dependencies`; "Correção/exclusão percorre dependentes, invalida versões publicadas e reconstitui projeções").
  - **Cenário 5 (linha 82) — reexecução sem `operation_id`, F15 + §11:** "Interrupção do grafo reexecuta nó→efeito já ocorreu" = F15 (timeout/ACK/crash); "sem operation_id duplica" = §11 (commit **primeiro verifica** `operation_id`; mesmo ID+digest+usuário devolve recibo anterior — sem esse ID não há como reutilizar o recibo). Ressalva "Checkpoint sozinho não garante idempotência" reproduz §11: "Checkpoint em DB separado não é atômico: replay consulta operação autoritativa e reutiliza recibo".
  - **Cenário 6 (linha 83) — falhas fora do denominador, F22/F23:** "sistema avalia só casos concluídos" = F22 (linha 72: trace/métrica omite retries/falhas) encadeado com F23 (linha 73: conclusão de superioridade sem validade — viés de sobrevivência); exigência "Falhas devem permanecer no denominador" coerente com §15.6 ("falhas ficam no denominador") e §12 (métricas desconhecidas ficam null, nunca zero; esgotar→terminal com erro, nunca saída parcial aprovada).
  - **Alinhamentos v0.1 (grep/leitura):** `eduagent/storage/repository.py` implementa exatamente o §11 (verificação de `operation_id` antes de `expected_version`, reuso de recibo, `UNKNOWN_EFFECT` sem retry automático) — cenário 5 coerente com o entregue; `eduagent/services/calendar.py` implementa precondições `if_match_etag` e reconciliação por leitura sem retry cego (família 016/016a) — cenário 3 coerente com o entregue; a seção 4 não menciona timezone, busca, Google nem reranker — nenhum conflito com as questões abertas (CONNECTOR_DISABLED, sync opcional `[→outbox→sync]`, timezone pendente, MODEL_NOT_ADMITTED). Nenhum cenário apresentado como ocorrência observada ou resultado medido: os seis são cadeias hipotéticas de risco e o rótulo "Severidade é potencial, não frequência observada" (linha 47) cobre o catálogo.
  - **Verificador:** `python3 fase2/scripts/verificar_documentos.py` (da raiz) → `status: passed`, 12 fluxos, 18 saídas, 24 falhas, 39 links, `delivery_pending: []`.
  - **Integridade:** `git status` limpo antes e depois; `git diff 92e3e2c` vazio (árvore idêntica à base); `fase2/documentos/04_mapa_completo_do_sistema.md` intocado; submódulo `docs/playground-llmagenticsystem` intocado.
  - Limitações: verificação documental/estática (leitura do código e dos registros das tasks 010a/016/016a/017); nenhum teste do sistema foi reexecutado (fora do escopo); a correspondência dos cenários 3 e 5 com a implementação é com o comportamento entregue da v0.1 (código), não com execução reproduzida dos cenários de falha — que seriam experimentos, fora do escopo da etapa 5.

## Notas

### Dificuldade esperada
4/10 — Seis cenários de encadeamento exigem rastrear cadeias entre falhas e exigências de mitigação até §11/§15; risco de reinterpretar exigência como solução implementada.

### Dificuldade sentida
3/10 — A conferência foi facilitada pelo padrão já consolidado nas tasks 001–003 e pela estrutura enxuta da seção 4 (seis enunciados de uma linha cada, todos ancorados no catálogo recém-validado pela 003): cada cenário exigiu apenas rastrear a cadeia até as linhas do catálogo F01–F24 e até as âncoras §9/§11/§15.1/§15.5/§15.6 do mapa, sem desvio encontrado. O único ponto que exigiu julgamento foi distinguir "confirma indevidamente" (cenário 1) da redação exata de F02 ("resolve ambiguidade sem confirmação") — mesma família de falha, redação diferente — e o mapeamento do cenário 6 simultaneamente a F22 (omissão de falhas na métrica) e F23 (conclusão inválida), resolvido pela leitura da propagação de cada linha do catálogo.

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
