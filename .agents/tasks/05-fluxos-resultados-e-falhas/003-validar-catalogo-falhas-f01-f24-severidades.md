# Task 003: Validar o catálogo de falhas F01–F24 e as severidades S1–S4

Estado: aguardando revisão
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
- [x] C1 — As 24 falhas conferidas item a item (ponto/causa, propagação, saídas/fluxos citados existentes em W e O), com registro em Evidências; desvios corrigidos em dif mínimo ou justificados.
- [x] C2 — Severidades S1–S4 coerentes com a escala do documento e rotuladas como potenciais; nenhuma falha descrita como observada; cobertura de fronteiras (transformação, persistência, efeito) e validade da avaliação confirmada.
- [x] C3 — `python3 fase2/scripts/verificar_documentos.py` passa; mapa intocado; commits entrega/registro separados.

## Execução
- Modelo: GLM-5.3-Flash (via ~/sd2-llm.sh; provider sd2, model GLM-5.3-Flash — identidade informada pelo runtime)
- Base: 5d3818de23609d405665b1b4c444bf82531f03f6
- Entrega: sem alteração de artefatos — dif zero no `fase2/documentos/05_fluxos_resultados_e_falhas.md` (nenhum desvio encontrado; conferência abaixo)
- Arquivos da entrega: nenhum (somente este registro em `.agents/tasks/05-fluxos-resultados-e-falhas/003-validar-catalogo-falhas-f01-f24-severidades.md`)
- Evidências:
  - **C1 — fidelidade item a item (24/24):** script próprio em `/tmp/opencode/task003/check_ids.py` analisou as 24 linhas da tabela da seção 3 (regex `^\| F\d\d \| … \| S\d \|$`): 24 linhas extraídas; **nenhum ID O ou W citado fora de O01–O18 / W01–W12** (intervalos como O01–05, O03–08, W02–12 expandidos e validados; células "Todas"/"todas rotas"/"Relatório experimental" tratadas como totais). Fidelidade semântica conferida por leitura contra o mapa §4 (erros tipados com retryability, envelope/artefatos, `Operation` com operation_id/digest), §11 (dispatcher/lease/`UNKNOWN_EFFECT`/reconciliação), §12 (limites/observabilidade) e §15.1 (snapshot/invalidação): F01/F02↔§6.2–6.3 (OCR/confirmação de fatos); F03/F04↔§6.5–6.8 (recuperação/abstinência/citação não garante sustentação); F05↔§8 (recusa encerra sem insistência); F06/F07↔§8/§15.2 (monitor independente; independente = hint_level 0; BKT shadow); F08/F09↔§7 (origem/validade/supersedes; checagem de polaridade/prazo/rubrica/ajuda); F10↔§4 (Pydantic estrito); F11↔§10/§12 (max_calls, budgets); F12↔§3.1/§12 (RESOURCE_LIMIT); F13/F14↔§9/§15.1/§15.5 (slots 15min, UTC/zona, fixos, snapshot); F15↔§9/§11 (timeout→unknown_effect→read/reconcile, sem retry cego) — coerente com o implementado em `eduagent/services/calendar.py` (linhas 44, 606–662, 1586–1627: `UNKNOWN_EFFECT`, reconciliação por leitura, sem retry cego; família 016/016a); F16/F17↔§10 (fonte é dado rotulado; path traversal/fetch bloqueado); F18↔§5/§12 (backup consistente, fila cheia, DB busy — ecoa W12); F19↔§6 (estados `metadata_only/text_read/transcript_read/unavailable`, quota 10s/5MiB, cache marcado com data) — não apresenta busca como capacidade garantida; F20↔§9 (ICS UTF-8/CRLF/UID/SEQUENCE/All-day DATE); F21↔§5/§15.1 (correção/exclusão percorre dependentes, invalida publicados, tombstones) — coerente com a 010a (`_apply_corrections`/`correct_fact` em `eduagent/services/memory.py`, `artifact_invalidated`, reconstituição no commit idempotente); F22↔§12 (métricas desconhecidas null com razão, nunca zero); F23↔validade da avaliação (etapa 8/mapa8); F24↔§13.10 e manifesto congelado da 017 (`manifest.json` com `congelamento`, hashes de skills/BGE-M3/Docling, `uv.lock` SHA). Seções 4 e 5 do documento 05 coerentes (exigências normativas, não resultados).
  - **C2 — severidades:** escala da linha 47 do documento idêntica à do plano (S1 qualidade localizada; S2 perda pedagógica/continuidade; S3 restrição, dado ou efeito comprometido; S4 indisponibilidade/corrupção generalizada) e rótulo explícito "Severidade é potencial, não frequência observada" presente. Distribuição conferida por script: S2×6 (F03,F04,F05,F08,F19,F22), S3×14 (F01,F02,F06,F07,F09,F10,F13,F14,F15,F16,F17,F20,F21,F23), S4×4 (F11,F12,F18,F24) — todas defensíveis pela escala (S3 para dado/restrição/efeito comprometido; S4 reservada a ausência de resposta, corrupção de estado, replay incoerente e não-reprodutibilidade). Nenhuma linha descreve falha como observada; nenhuma frequência/percentual no documento. Observação registrada sem caráter corretivo: S1 é definido na escala mas não ocorre na tabela — coerente com um catálogo de falhas de fronteira (falha meramente local de qualidade não é enumerada como ponto de falha); ausência de uso não é contradição. Cobertura de fronteiras confirmada por script: transformação (F01–F04, F09, F10), persistência (F08, F18, F21), efeito (F13–F15, F20), validade da avaliação (F22, F23) — nenhuma fronteira sem falha.
  - **Alinhamentos v0.1 (greps):** zero ocorrências de "América/São Paulo"/`sao_paulo` no documento 05 (timezone permanece pendente; F13 cita "zona" genérica); zero "Google"; "reranker" ausente; `CONNECTOR_DISABLED` implícito no W09 (gate rede/cache) e F19 não transforma busca em capacidade garantida; W08 preserva `[→outbox→sync]` opcional com "Sem rede exporta local"; `MODEL_NOT_ADMITTED` não é contradito por nenhuma falha; "observada/observado/medido/frequência" ocorre apenas no rótulo negativo da linha 47. Verificador: `python3 fase2/scripts/verificar_documentos.py` → `status: passed`, 12 fluxos, 18 saídas, 24 falhas, 39 links, exit 0. Árvore limpa antes e depois; submódulo `docs/playground-llmagenticsystem` intocado; `fase2/documentos/04_mapa_completo_do_sistema.md` intocado (`git status` sem modificação nele).
  - Limitações: verificação é documental/estática (leitura do código e registros das tasks 010a/016/016a/017); nenhum teste do sistema foi reexecutado (fora do escopo desta task); a correspondência F15↔016a é com o comportamento implementado do conector CalDAV (reconciliação em `eduagent/services/calendar.py`), pois o registro da 016a trata dos limites de transporte/redirect sem citar literalmente "reconciliação".

## Notas

### Dificuldade esperada
4/10 — Cruzar 24 falhas com erros tipados/estados da etapa 4 e com o comportamento real implementado; o risco é inflar severidade ou descrever como observado o que é potencial.

### Dificuldade sentida
3/10 — A conferência foi facilitada pelo padrão já estabelecido nas tasks 001/002 (mesmos universos de IDs, mesmo verificador) e pelo fato de o documento 05 já estar materializado com alta fidelidade: os scripts de expansão de IDs e o cruzamento com §4/§11/§15.1 e com o código (`calendar.py`, `memory.py`, `manifest.json`) não revelaram desvio. O único ponto que exigiu julgamento foi a ausência de uso do nível S1 na tabela (registrado como observação, sem correção) e a atribuição fina entre S2/S3 nas falhas de validade da avaliação (F22/F23), resolvida pela ordenação interna da própria escala.

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
