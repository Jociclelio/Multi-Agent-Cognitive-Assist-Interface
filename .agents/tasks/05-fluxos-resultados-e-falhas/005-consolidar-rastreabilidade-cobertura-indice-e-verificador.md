# Task 005: Consolidar rastreabilidade e cobertura, índice da entrega e verificador

Estado: aguardando revisão
Depende de: 004
Origem: nenhuma

## Prompt
Fechar a etapa 5 (consolidação final do plano): (1) Conferir a seção 5 ("Rastreabilidade e cobertura") de `fase2/documentos/05_fluxos_resultados_e_falhas.md` — as afirmações de cobertura são consistentes com a etapa 4: W01–W12 cobrem as intenções/estados da v0.1 (conferir contra as rotas do §10 do mapa, corrigindo o texto do documento 05 se houver lacuna ou superafetação — a etapa 4 é a autoridade do universo de tarefas); O01–O18 cobrem artefatos internos, saídas ao estudante e operacionais; F01–F24 cobrem fronteiras de transformação/persistência/efeito e validade da avaliação. Confirmar que as remissões à etapa 6 (define métricas para os IDs W/O/F) e à etapa 7 (seleciona métodos) não contradizem `fase2/documentos/06_protocolo_de_avaliacao.md` e `fase2/documentos/07_metodologias_de_testagem.md`, e que a nota "mudanças de capability exigem novo fluxo, saída, falha e teste" permanece. (2) Conferir que o documento permanece corretamente registrado no índice da entrega `fase2/documentos/11_indice_da_entrega.md` (entrada da etapa 5 apontando `05_fluxos_resultados_e_falhas.md`), ajustando o índice apenas se necessário. (3) Rodar `python3 fase2/scripts/verificar_documentos.py` (e, se a entrega da fase 2 exigir reconstrução, seguir o procedimento do README de entrega — apenas se houver alteração documental pendente de publicação; sem reconstrução desnecessária). (4) Registrar na task o resumo consolidado: estado final das quatro conferências anteriores (001–004), correções feitas no documento 05 (se houver) e pendências herdadas (nada medido; severidades potenciais; catálogo não exaustivo).

Restrições: `fase2/documentos/04_mapa_completo_do_sistema.md` é INTOCADO ("deve" é contrato; §15 prevalece); correções no documento 05 e no índice somente em dif mínimo com justificativa; nada apresentado como resultado medido; IDs W/O/F permanentes; prosa em português; `python3 fase2/scripts/verificar_documentos.py` deve passar ao final; commit de entrega (documento/índice, se houver alteração) e commit de registro separados, sem amend/force-push/commits vazios; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — documento consolidado (entregável): seção 5 (linhas 85–87) e o documento integral após as tasks 001–004.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — fonte do universo de tarefas da v0.1 (intocado).
- `fase2/documentos/06_protocolo_de_avaliacao.md` e `fase2/documentos/07_metodologias_de_testagem.md` — etapas 6/7, para conferência de não-contradição (intocados).
- `fase2/documentos/11_indice_da_entrega.md` — índice da entrega (entrada da etapa 5).
- `fase2/scripts/verificar_documentos.py` — verificação documental (citações, seções, IDs W/O/F, links); `fase2/README-entrega.md` — procedimento de reconstrução, se aplicável.

## Corretude
- [x] C1 — Afirmações de cobertura da seção 5 conferidas contra a etapa 4 e sem contradição com etapas 6/7; correções em dif mínimo ou justificativas registradas. **Sem correção necessária: dif zero no documento 05.**
- [x] C2 — Documento registrado no índice da entrega; verificador `python3 fase2/scripts/verificar_documentos.py` passa ao final. **Entrada da etapa 5 correta no índice (linha 11); verificador passed com 12 fluxos, 18 saídas, 24 falhas e 39 links.**
- [x] C3 — Resumo consolidado registrado na task (estado das conferências 001–004, correções, pendências herdadas); nada como resultado medido; mapa/docs-fonte intocados; commits entrega/registro separados. **Sem commit de entrega (não houve alteração de artefatos); só commit de registro.**

## Execução
- Modelo: GLM-5.3-Flash (via ~/sd2-llm.sh; provider sd2, model GLM-5.3-Flash)
- Base: 41cf3db6e79be934f410280335a5818510841b79
- Entrega: sem alteração de artefatos (dif zero no documento 05 e no índice; nenhum commit de entrega)
- Arquivos da entrega: nenhum (referência: `git diff 41cf3db..HEAD -- fase2/documentos/05_fluxos_resultados_e_falhas.md fase2/documentos/11_indice_da_entrega.md` vazio)
- Evidências:
  1. **Seção 5 contra §10 da etapa 4 (universo de tarefas):** as 14 intenções e 11 rotas do parágrafo 10 do mapa foram mapeadas rota a rota para W01–W12 sem lacuna nem superafetação: `ingest`→W01; `ask`/`practice`→W02/W03; `submit_answer`→W04; `plan`/`replan`→W06/W07; `approve_plan`→transição W06→W08; `update_activity`/`export_calendar`→W08; `memory_query`/retomada de sessão (checkpointer, §10)→W05/W10; `correct_fact`/`delete_data`→W10; `curate`→W09 (gate rede/cache do W09 corresponde ao `network_gate` da rota); `cancel`/crash/fila cheia→W11; `doctor`/`backup`/`restore` (CLI do §12)→W12. Script próprio expandiu todos os IDs citados no documento: exatamente 12 W, 18 O e 24 F, nenhum fora dos intervalos permanentes.
  2. **Não-contradição com etapas 6/7:** a remissão "a etapa6 define métricas para todos esses IDs" é coerente com o protocolo: §3 da etapa 6 define métricas para O01–O18, §4 cobre F01–F24 ("no mínimo dez casos base por F01–F24") e §5 define TSR reportado por W. A remissão "a etapa7 seleciona métodos" é coerente com as linhas 7–8 e a tabela da etapa 7 (todos O01–O18 e F01–F24 mapeados em famílias de métodos). A nota "mudanças de capability exigem novo fluxo, saída, falha e teste" permanece (linha 87) e não contradiz nenhum dos dois documentos.
  3. **Alinhamentos v0.1 por grep no documento 05:** zero ocorrências de "America/Sao_Paulo"/"São Paulo", "reranker" e "medido" — timezone segue pendente, reranker não adotado e nada apresentado como resultado medido; W08 preserva `[→outbox→sync]` (sync opcional) e W09 preserva o gate de rede/cache (CONNECTOR_DISABLED), sem apresentar busca ou Google como capacidade garantida.
  4. **Índice da entrega:** entrada da etapa 5 em `fase2/documentos/11_indice_da_entrega.md` linha 11 aponta corretamente `05_fluxos_resultados_e_falhas.md`; nenhum ajuste necessário.
  5. **Verificador:** `python3 fase2/scripts/verificar_documentos.py` da raiz → `status: passed`, 11 etapas, 20 componentes, 12 fluxos, 18 saídas, 24 falhas, 39 links locais, `delivery_pending: []`, exit 0. Como não houve alteração documental, nenhuma reconstrução da entrega foi necessária (conforme fase2/README-entrega.md: reconstruir apenas com mudança pendente de publicação).
  6. **Estado das conferências 001–004 (resumo consolidado):** todas fechadas em revisão com decisão "fechar" e nota final 9/10 cada (registros ac4222c, 8144943, e96c4af, 2d25eeb; revisões cd4e911, 5d3818d, 92e3e2c, 41cf3db), todas com dif zero no documento 05, mapa da etapa 4 intocado e verificador passed. Achados não corretivos herdados para juízo desta task: R004-REV-01 ("confirmação indevida" do cenário composto 1 versus redação de F02, que descreve resolver ambiguidade sem confirmação) e R004-REV-02 (exigência implícita no cenário 1). Juízo do executor: **não corretivo** — a seção 4 descreve composições de falhas, não novos IDs; ancorar o cenário 1 em F01/F02 é legítimo pois a família de F02 (decisão de extração/contorno da confirmação, com remédio "esclarecer antes de restrição" na etapa 6) cobre a confirmação indevida como variante do mesmo limite, e a exigência de validação independente antes de confirmar está implícita em "Curador confirma indevidamente" e explícita no cenário 2 análogo; corrigir introduziria dif sem ganho de fidelidade, contra a regra de dif mínimo.
  7. **Pendências herdadas (registradas como ausência, não como resultado):** nada no documento é resultado medido — métricas dos IDs W/O/F são da etapa 6 e métodos da etapa 7, fora do escopo; severidades S1–S4 permanecem potenciais, nunca frequência observada; o catálogo declara-se não exaustivo (linha 87); baselines/ablações e execução experimental permanecem pendentes (etapa 8, plano 06+); reranker, timezone e conector de busca seguem como questões abertas da v0.1, não decididos no documento 05.
- Limitações: conferência é documental e de leitura dirigida ao código já auditado nas tasks 001–004; nenhum experimento foi executado e nenhuma métrica foi produzida nesta task.

## Notas

### Dificuldade esperada
3/10 — Consolidação sobre conferências anteriores; risco principal é presumir cobertura sem conferir a seção 5 contra §10 da etapa 4.

### Dificuldade sentida
2/10 — Consolidação final sobre quatro conferências fechadas com convergência factual total e dif zero acumulado; o universo de tarefas do §10 foi re-mapeado rota a rota e os IDs re-expandidos por script, sem desvio encontrado. O único ponto de juízo foi o destino dos achados não corretivos R004-REV-01/02 herdados da revisão da 004, resolvido como não corretivo com justificativa registrada.

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
