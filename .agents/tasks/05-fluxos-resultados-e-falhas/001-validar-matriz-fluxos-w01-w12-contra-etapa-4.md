# Task 001: Validar a matriz de fluxos W01–W12 contra a etapa 4 e a v0.1 implementada

Estado: pendente
Depende de: nenhuma
Origem: nenhuma

## Prompt
Conferir a seção 1 ("Universo de tarefas") de `fase2/documentos/05_fluxos_resultados_e_falhas.md` — a matriz de fluxos W01–W12 — contra a especificação v0.1 (`fase2/documentos/04_mapa_completo_do_sistema.md`, seções de intenções/rotas/estados, em especial §10) e contra o MVP já implementado (tasks 001–017 do plano 04-mapa-completo-do-sistema, código em `eduagent/`). Para cada fluxo, registrar em Evidências a conferência item a item: gatilho/sequência corresponde a rotas existentes da etapa 4 (e do grafo implementado); saídas esperadas citam apenas IDs O existentes (O01–O18); variações/término incluem sucesso, espera, conflito, abstinência, cancelamento e falha controlada. Conferir que pedidos compostos são decompostos em rotas existentes, sem criar capacidades ilimitadas, e que a regra "novos conectores/skills exigem revisão desta matriz" está presente. Se encontrar desvio de fidelidade ou contradição com a etapa 4, corrija **apenas o documento 05** em dif mínimo, preservando o sentido normativo do fonte (etapa 4), e registre a correção em Evidências.

Alinhamentos obrigatórios com a v0.1 implementada (nada no documento pode contradizer o sistema entregue): curadoria sem conector de busca configurado é `CONNECTOR_DISABLED` (W09 mantém o fluxo com gate de rede/cache); sync de calendário é opcional com `[→outbox→sync]` entre colchetes (W08); timezone permanece pendente de confirmação (nenhum fluxo presume `America/Sao_Paulo` fixado); reranker não adotado; `MODEL_NOT_ADMITTED` bloqueia tutoria; não-admitidos (busca, Google) não aparecem como capacidades garantidas.

Restrições: `fase2/documentos/04_mapa_completo_do_sistema.md` é INTOCADO ("deve" é contrato; §15 prevalece quando especifica regra mais precisa); `05_fluxos_resultados_e_falhas.md` é o entregável — manutenção/revisão permitida somente em dif mínimo com justificativa; nada apresentado como resultado medido; IDs W01–W12 e O01–O18 permanentes; prosa em português; `python3 fase2/scripts/verificar_documentos.py` deve passar após as alterações; commit de entrega (documento, se houver correção) e commit de registro (task.md) separados, sem amend/force-push/commits vazios; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — documento a materializar (entregável): seção 1, tabela W01–W12 (linhas 3–20).
- `fase2/documentos/04_mapa_completo_do_sistema.md` — especificação v0.1 (fonte normativo, intocado): intenções/estados, §10 rotas do grafo, §6/§9 módulos opcionais.
- `eduagent/` e `eval/relatorio-testes-mvp.md` — sistema implementado (planos 04, tasks 001–017): rotas reais, questões abertas preservadas.
- `fase2/scripts/verificar_documentos.py` — verificação documental (exige presença de W01–W12, O01–O18, F01–F24).

## Corretude
- [ ] C1 — Cada um dos 12 fluxos conferido item a item contra a etapa 4 e a implementação (gatilho/sequência, saídas citadas, variações/término), com registro em Evidências; desvios corrigidos no documento 05 em dif mínimo ou justificados.
- [ ] C2 — Decomposição de pedidos compostos sem capacidades ilimitadas e a regra de revisão da matriz por novos conectores/skills confirmadas no texto; nenhum fluxo contraria a v0.1 (CONNECTOR_DISABLED, sync opcional, timezone pendente, não-admitidos).
- [ ] C3 — `python3 fase2/scripts/verificar_documentos.py` passa; mapa intocado; commits entrega/registro separados; nada como resultado medido.

## Execução
- Modelo: <identificador real do executor>
- Base: <SHA completo antes da implementação>
- Entrega: <SHA(s) completos, sem commits de registro, ou sem alteração de artefatos>
- Arquivos da entrega: <paths ou referência ao diff dos commits>
- Evidências: <comandos/procedimentos, resultados e limitações>

## Notas

### Dificuldade esperada
3/10 — Conferência de fidelidade tabela-a-especificação com documento já materializado; risco baixo de inflar resultado, mas exige leitura atenta do mapa §10 e do sistema implementado.

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
