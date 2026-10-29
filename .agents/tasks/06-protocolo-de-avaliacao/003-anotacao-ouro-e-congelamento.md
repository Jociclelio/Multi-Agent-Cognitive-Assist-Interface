# Task 003: Anotação, ouro e congelamento do teste

Estado: pendente
Depende de: 002
Origem: nenhuma

## Prompt
Executar a anotação e o congelamento (seção 2 do protocolo): (1) Preparar rubricas por tipo de saída (rubricas 0–4 para saídas seméricas) e testá-las em piloto no split de desenvolvimento, ajustando antes do uso no teste. (2) Anotar com dois avaliadores independentes cegos à arquitetura e à condição, com adjudicação nos desacordos; registrar kappa. (3) Construir o ouro com IDs de fonte/claim, critérios/erros, fatos temporais e restrições originais — o ouro NUNCA contém respostas do sistema avaliado. (4) Congelar o split de teste antes de qualquer ajuste do sistema sobre ele: registrar hashes dos arquivos congelados, acessos e data; a partir do congelamento, nenhum item de teste pode ser alterado. Registrar desvios em relação às metas com as justificativas herdadas da task 001.

Restrições: anotadores cegos à arquitetura e à condição; o ouro nunca deriva de saída do sistema; nada apresentado como resultado medido (contagens de anotação são insumo, não resultado experimental); prosa em português; commits de entrega e registro separados; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/06_protocolo_de_avaliacao.md` — seção 2 (anotação e congelamento): dois avaliadores cegos, rubricas com piloto, adjudicação, ouro com IDs de fonte/claim, hashes e acessos.
- `.agents/tasks/06-protocolo-de-avaliacao/002-montar-corpus-e-conjuntos-por-split.md` — conjuntos por split produzidos (insumo).
- `fase2/documentos/07_metodologias_de_testagem.md` — famílias de métodos que definem que tipo de anotação cada métrica exige (consultar; a implementação dos mecanismos é da etapa 8).
- `fase2/documentos/08_mapa_completo_da_testagem.md` — §3 schema `AnnotationRecord` e §4 auditoria de parentesco (consultar para alinhar formato de anotação).

## Corretude
- [ ] C1 — Rubricas testadas em piloto no split de desenvolvimento antes do uso; ajustes de rubrica registrados.
- [ ] C2 — Anotação com dois avaliadores independentes cegos à arquitetura/condição, com adjudicação e kappa registrados; ouro com IDs de fonte/claim, critérios/erros, fatos temporais e restrições originais, sem nenhuma resposta do sistema avaliado.
- [ ] C3 — Split de teste congelado antes de qualquer ajuste sobre ele: hashes registrados, acessos e data registrados; desvios de quantidade documentados com as justificativas da 001.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
6/10 — Coordenar anotação cega com adjudicação e congelamento auditável; o risco é vazamento de condição para os anotadores ou congelamento incompleto (hash faltante).

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
