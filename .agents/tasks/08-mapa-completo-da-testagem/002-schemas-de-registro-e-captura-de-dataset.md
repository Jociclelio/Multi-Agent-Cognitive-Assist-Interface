# Task 002: Schemas de registro e captura de dataset

Estado: pendente
Depende de: 001
Origem: nenhuma

## Prompt
Implementar os schemas JSON estritos do mapa §3 — `CaseRecord`, `GoldRecord`, `RunRecord`, `MetricRecord`, `AnnotationRecord` — e a captura do dataset conforme metas e targets do mapa §4 e §12.1 (famílias documentais, queries, trajetórias, agendas), incluindo: auditor de parentesco/duplicatas; splits que nunca repartem parentes; clusters = componentes de parentesco; e o fluxo de anotação com dois especialistas + adjudicação (formato dos registros alinhado ao protocolo da etapa 6, task 003 do plano 06). Validação dos schemas com fixtures positivas e negativas (documento inválido rejeitado com erro claro). A captura usa os conjuntos preparados no plano 06 (ou reconstrói equivalentes se o split ainda não estiver materializado em formato consumível — registrar o que foi usado).

Restrições: mapa §3/§4/§12.1 como fonte; schemas estritos (sem campos soltos); nada apresentado como resultado medido; dados autorizados não commitados sem permissão (registrar referências de acesso); suíte raiz passando; commits entrega/registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/08_mapa_completo_da_testagem.md` — §3 (schemas e regra "falha de harness ≠ falha SUT, sem substituição silenciosa"), §4 (dataset), §12.1 (metas/targets e custo humano).
- `.agents/tasks/06-protocolo-de-avaliacao/002-montar-corpus-e-conjuntos-por-split.md` e `003-anotacao-ouro-e-congelamento.md` — conjuntos e anotação produzidos na etapa 6 (insumo/contrato de formato).
- `eval/adapters.py` e estrutura da task 001 — onde a captura se apoia.

## Corretude
- [ ] C1 — Cinco schemas implementados e validados com fixtures positivas e negativas; registros rejeitam campos inválidos com erro claro.
- [ ] C2 — Captura do dataset conforme §4/§12.1 com auditor de parentesco/duplicatas, splits sem repartir parentes e clusters = componentes de parentesco, com relatório de contagens versus metas e desvios justificados.
- [ ] C3 — Formato de anotação compatível com o protocolo da etapa 6 (dois especialistas + adjudicação); suíte raiz passando; nenhum dado não-autorizado commitado.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
6/10 — Schemas estritos com auditoria de parentesco correta (grafo de componentes); o risco é split com vazamento silencioso.

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

Plano: [plan.md](../../plans/08-mapa-completo-da-testagem/plan.md)
