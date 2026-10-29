# Task 004: Validar decisões do testbed, remissão à etapa 8 e consolidar

Estado: pendente
Depende de: 003
Origem: nenhuma

## Prompt
Fechar a etapa 7 (consolidação final do plano): (1) Conferir que as decisões para a implementação do testbed estão presentes e fiéis aos relatórios no documento 07: verificadores determinísticos e fixtures positivas/negativas primeiro, avaliações semânticas depois; validação de avaliadores com mutações conhecidas; instrumentação de sistema e controlador; separação de teste de fronteira, E2E, mock conectado e smoke real; congelamento de estimandos, clusters, thresholds/margens e seeds antes do teste final; não-inferioridade exigida por IC compatível com a margem (não apenas p>.05). (2) Conferir que a remissão "a etapa 8 (mapa normativo de testagem) fixa contratos, registro, comandos e plano de execução" é coerente com `fase2/documentos/08_mapa_completo_da_testagem.md` e que o documento 07 NÃO reproduz decisões que pertencem à etapa 8. (3) Registrar na task o resumo consolidado das conferências 001–003 e as pendências herdadas (decisões operacionais na etapa 8; nenhum limiar apresentado como medido). (4) Conferir o registro do documento 07 no índice da entrega `fase2/documentos/11_indice_da_entrega.md`, ajustando apenas se necessário. (5) Rodar `python3 fase2/scripts/verificar_documentos.py` (e `--check-delivery` apenas se houver alteração documental pendente de publicação).

Restrições: documentos das etapas 1–6, relatórios 07a/07b e `08_mapa_completo_da_testagem.md` INTOCADOS; correções no documento 07 e no índice somente em dif mínimo com justificativa; nada apresentado como resultado medido; prosa em português; verificador deve passar ao final; commits de entrega e registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/07_metodologias_de_testagem.md` — documento consolidado (entregável): decisões do testbed e remissão à etapa 8.
- `fase2/pesquisa/07a_metodos_qualidade.md` e `fase2/pesquisa/07b_metodos_robustez_experimentos.md` — fontes das decisões (intocados).
- `fase2/documentos/08_mapa_completo_da_testagem.md` — etapa 8, para conferência de não-duplicação e não-contradição (intocado).
- `fase2/documentos/11_indice_da_entrega.md` — índice da entrega (entrada da etapa 7).
- `fase2/scripts/verificar_documentos.py` — verificação documental.

## Corretude
- [ ] C1 — Decisões do testbed presentes e fiéis aos relatórios (ordem determinístico→semântico, mutações, instrumentação, níveis de teste, congelamento pré-teste, não-inferioridade por IC).
- [ ] C2 — Remissão à etapa 8 coerente e sem duplicação de conteúdo normativo do mapa; índice da entrega correto.
- [ ] C3 — Resumo consolidado das conferências 001–003 registrado com pendências como ausência; verificador passa; commits entrega/registro separados; documentos-fonte intocados.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
3/10 — Consolidação sobre conferências anteriores; o risco é deixar passar fronteira difusa entre decisão de método (etapa 7) e contrato de execução (etapa 8).

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
