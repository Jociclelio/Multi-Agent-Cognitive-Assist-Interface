# Task 001: Definir corpus, autorizações e desvios aceitáveis das metas

Estado: pendente
Depende de: nenhuma
Origem: nenhuma

## Prompt
Fechar as questões abertas do plano 06 e do protocolo (seção "Questões abertas" de ambos) ANTES de qualquer coleta de dados: (1) Confirmar a disponibilidade real do corpus candidata e as autorizações/licenças de uso das duas disciplinas (uma técnico-formal, outra conceitual), registrando a fonte de cada material e a autorização correspondente — sem redistribuir materiais sem permissão. (2) Escolher e justificar as duas disciplinas concretas. (3) Definir, por escrito e antes da coleta, os desvios aceitáveis das metas de quantidade propostas (24 famílias documentais, 120 consultas e 120 tentativas por conjunto, 30 trajetórias com 8 sessões, 100+100 instâncias de agenda, ≥10 casos base por falha F01–F24) — as quantidades são metas propostas a conferir por disponibilidade/autorização, não requisitos fechados, e o desvio aceitável precisa existir antes de se olhar qualquer resultado. (4) Decidir o juiz LLM (qual modelo, para triagem/secundária apenas) com plano de calibração contra humanos, e decidir se haverá medição de energia (só reportar se houver medidor/contador identificado; senão `N/A` com motivo). Registrar todas as decisões com justificativa na task; se alguma decisão exigir ajuste no texto normativo de `fase2/documentos/06_protocolo_de_avaliacao.md`, corrigir apenas em dif mínimo com justificativa.

Restrições: nada apresentado como resultado medido; as metas de quantidade nunca são apresentadas como resultados; prosa em português; `python3 fase2/scripts/verificar_documentos.py` deve passar se o documento 06 for alterado; commit de entrega (se houver alteração de artefatos) e commit de registro separados, sem amend/force-push/commits vazios; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/06_protocolo_de_avaliacao.md` — protocolo normativo (etapa 6): seção 2 (dados e desenho, metas de quantidade) e questões abertas do próprio documento.
- `.agents/plans/06-protocolo-de-avaliacao/plan.md` — seção "Questões abertas" com as quatro pendências que esta task fecha.
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — origem dos IDs F01–F24 (casos base por falha) e O01–O18.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — contexto da v0.1 implementada (conectores opcionais, gates) para avaliar o que o corpus precisa exercitar.

## Corretude
- [ ] C1 — As duas disciplinas estão escolhidas com justificativa e cada material do corpus tem fonte e autorização/licença registradas; nada é redistribuído sem permissão.
- [ ] C2 — Desvios aceitáveis das metas de quantidade definidos por escrito ANTES da coleta, para cada conjunto (famílias, consultas/tentativas, trajetórias, agenda, casos de falha); as metas permanecem rotuladas como propostas.
- [ ] C3 — Juiz LLM decidido com plano de calibração contra humanos (uso restrito a triagem/secundária) e decisão sobre energia registrada (medidor identificado ou `N/A` com motivo); decisões registradas na task e, se aplicável, ajuste em dif mínimo no documento 06 com verificador passando.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
4/10 — Decisões pré-experimentais com dependência externa (autorização de materiais); o risco é deixar uma questão aberta implícita e descobrir depois da coleta.

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
