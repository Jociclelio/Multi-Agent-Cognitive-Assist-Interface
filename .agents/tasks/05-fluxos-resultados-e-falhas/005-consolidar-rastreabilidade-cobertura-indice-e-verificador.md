# Task 005: Consolidar rastreabilidade e cobertura, índice da entrega e verificador

Estado: pendente
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
- [ ] C1 — Afirmações de cobertura da seção 5 conferidas contra a etapa 4 e sem contradição com etapas 6/7; correções em dif mínimo ou justificativas registradas.
- [ ] C2 — Documento registrado no índice da entrega; verificador `python3 fase2/scripts/verificar_documentos.py` passa ao final.
- [ ] C3 — Resumo consolidado registrado na task (estado das conferências 001–004, correções, pendências herdadas); nada como resultado medido; mapa/docs-fonte intocados; commits entrega/registro separados.

## Execução
- Modelo: <identificador real do executor>
- Base: <SHA completo antes da implementação>
- Entrega: <SHA(s) completos, sem commits de registro, ou sem alteração de artefatos>
- Arquivos da entrega: <paths ou referência ao diff dos commits>
- Evidências: <comandos/procedimentos, resultados e limitações>

## Notas

### Dificuldade esperada
3/10 — Consolidação sobre conferências anteriores; risco principal é presumir cobertura sem conferir a seção 5 contra §10 da etapa 4.

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
