# Task 003: Validar as seis correções exigidas em etapas anteriores

Estado: pendente
Depende de: 002
Origem: nenhuma

## Prompt
Conferir que as seis correções que a pesquisa metodológica exige em etapas anteriores estão corretamente registradas no documento 07, com conteúdo fiel aos relatórios 07a/07b: (1) faixas de CER/WER/kappa/log loss (domínios e interpretação); (2) semântica de DTSTAMP vs. CREATED na etapa 4; (3) definição implementável de "contradição recente"; (4) ordem de conferência de `operation_id` no retry idempotente; (5) alcance do diagnóstico INFEASIBLE da grade; (6) denominadores completos de disponibilidade/TSR e a regra de que "contenção segura não é conclusão original". Para cada correção: (a) confirmar que o documento 07 registra a correção e a etapa afetada; (b) confirmar que a redação não contradiz o texto atual do documento da etapa afetada (`04_mapa_completo_do_sistema.md`, `05_fluxos_resultados_e_falhas.md`, `06_protocolo_de_avaliacao.md`) — a correção é exigência registrada para evolução/reexecução, não edição silenciosa destes documentos neste plano; (c) confirmar coerência com o código da v0.1 quando a correção toca comportamento implementado (ex.: `operation_id` conferido antes de `expected_version` em `eduagent/services/`), registrando na task qualquer divergência encontrada como achado, sem alterar código neste plano.

Restrições: documentos das etapas 1–6, relatórios 07a/07b e código `eduagent/` INTOCADOS; edição restrita ao documento 07 em dif mínimo com justificativa; nada apresentado como resultado medido; prosa em português; verificador deve passar ao final; commits de entrega e registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/07_metodologias_de_testagem.md` — registro das seis correções exigidas (objeto da conferência).
- `fase2/pesquisa/07a_metodos_qualidade.md` (§ de correções) e `fase2/pesquisa/07b_metodos_robustez_experimentos.md` (§ de correções) — fonte de cada exigência.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — etapa 4 (DTSTAMP/CREATED, operation_id, INFEASIBLE), intocado.
- `eduagent/services/` — comportamento implementado citável como evidência (idempotência, efeitos), sem alteração.

## Corretude
- [ ] C1 — As seis correções estão presentes no documento 07, cada uma identificando a etapa afetada, fiéis aos relatórios 07a/07b.
- [ ] C2 — Nenhuma correção contradiz o texto vigente das etapas 1–6; divergências com o código da v0.1 (quando aplicável) registradas como achado, sem alteração de código.
- [ ] C3 — Verificador passa ao final; correções no documento 07 em dif mínimo com justificativa; nada como resultado medido.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
5/10 — Exige leitura cruzada de especificação, pesquisa e código; o risco é marcar correção como "aplicada" quando ela é apenas "registrada como exigência".

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

Plano: [plan.md](../../plans/07-metodologias-de-testagem/plan.md)
