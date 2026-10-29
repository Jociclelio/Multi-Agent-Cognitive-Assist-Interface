# Task 005: Validar testes de falha, sucesso/eficiência e validade do protocolo

Estado: pendente
Depende de: 004
Origem: nenhuma

## Prompt
Conferir item a item as seções 4, 5 e 6 de `fase2/documentos/06_protocolo_de_avaliacao.md`: (1) **Testes de falha (seção 4):** cada F01–F24 prevê par limpo/perturbado com mesmo caso/seed e as medidas de impacto (Δqualidade, Δsucesso, Δlatência, Δtokens, efeitos indevidos, tempo até detectar/recuperar), com o critério de redução de conclusão explicada e contida; correspondência de IDs com o catálogo da etapa 5. (2) **Sucesso e eficiência (seção 5):** sucesso de tarefa = todos os critérios essenciais da rota + terminal correto, com abstinência correta e diagnóstico correto contando como sucesso nos casos próprios; na fault-injection, task_completion separado de safe_terminal; TSR reportado por W, macro e micro; tool-use correctness em quatro níveis separados; eficiência com p50/p95, timeout rate, RSS/VRAM, custo por tarefa/trajectory; p95 nunca só de sucessos (censura indicada). (3) **Validade e análise (seção 6):** comparações pareadas por caso, reamostragem por trajetória/família, IC95%; primárias pré-definidas (TSR longitudinal e taxa de violação crítica publicada); correção para múltiplas hipóteses secundárias; tamanhos de efeito; tamanho amostral estimado após piloto; juiz LLM apenas para triagem/secundária após calibração; anotadores cegos à condição; limites de generalização declarados (aluno simulado, duas disciplinas, hardware único) e a nota de que qualidade operacional não comprova ganho de aprendizagem. Confirmar coerência com a v0.1 implementada (ex.: `MODEL_NOT_ADMITTED` bloqueia tutoria; `CONNECTOR_DISABLED` sem conector; sync opcional entre colchetes). Desvio de fidelidade: corrigir apenas o documento 06 em dif mínimo.

Restrições: `04_mapa_completo_do_sistema.md`, `05_fluxos_resultados_e_falhas.md` e `07_metodologias_de_testagem.md` INTOCADOS; nada apresentado como resultado medido; IDs W/O/F permanentes; prosa em português; verificador deve passar ao final; commits de entrega e registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/06_protocolo_de_avaliacao.md` — documento a validar: seções 4 (testes de falha), 5 (sucesso e eficiência) e 6 (validade e análise).
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — catálogo F01–F24 e matriz W01–W12 (TSR por W).
- `fase2/pesquisa/07b_metodos_robustez_experimentos.md` — injeção de falhas, comparação e inferência (fonte dos métodos das seções 4–6).
- `eval/relatorio-testes-mvp.md` — estado da v0.1 (ensaio longitudinal do plano 04) para conferência de coerência com o sistema implementado.

## Corretude
- [ ] C1 — Seção 4: par limpo/perturbado por F01–F24 com medidas de impacto e critério de contenção presentes; IDs coerentes com a etapa 5.
- [ ] C2 — Seção 5: definições de sucesso (critérios essenciais + terminal correto; abstinência/diagnóstico nos casos próprios), task_completion vs. safe_terminal, TSR por W/macro/micro, quatro níveis de tool-use e p95 com denominador completo presentes.
- [ ] C3 — Seção 6: primárias pré-definidas, IC95% por cluster, correção de múltiplas hipóteses, efeitos, calibração do juiz LLM, cegamento e limites de generalização presentes; alinhamentos v0.1 sem contradição; correções em dif mínimo com verificador passando.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
4/10 — Conferência documental densa em três seções; o risco é confundir especificação de análise com resultado e deixar passar contradição com o comportamento fail-closed da v0.1.

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

### Revisão
- Orquestrador: —
- Alvo: —
- Avaliações: <modelo A: _/10; modelo B: _/10; modelo C: _/10>
- Nota final: _/10
- Parecer: —
- Decisão: —
- Reversão: —
- Próximo passo: —

Plano: [plan.md](../../plans/06-protocolo-de-avaliacao/plan.md)
