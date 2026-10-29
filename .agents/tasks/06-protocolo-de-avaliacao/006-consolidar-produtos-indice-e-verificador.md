# Task 006: Consolidar produtos do protocolo, índice e verificador

Estado: pendente
Depende de: 005
Origem: nenhuma

## Prompt
Fechar a etapa 6 (consolidação final do plano): (1) Conferir a seção 7 ("Produtos") de `fase2/documentos/06_protocolo_de_avaliacao.md` contra os critérios de conclusão do plano: manifesto congelado, datasets/anotações ou referências de acesso, logs estruturados, métricas com denominadores, catálogo de falhas, ICs/tabelas por condição, artefatos julgados e relatório de limitações; verificar que a remissão "os mecanismos por célula são definidos na etapa 7 e os módulos/schemas/execução na etapa 8" não contradiz `fase2/documentos/07_metodologias_de_testagem.md` e `fase2/documentos/08_mapa_completo_da_testagem.md`. (2) Registrar na task o resumo consolidado do estado da etapa: decisões da 001, contagens/desvios da 002, congelamento da 003, resultado das validações 004–005, e as pendências que permanecem como ausência (execução experimental pertence à etapa 8/plano 08; nada medido nesta etapa até a execução). (3) Conferir que o documento 06 permanece corretamente registrado no índice da entrega `fase2/documentos/11_indice_da_entrega.md`, ajustando apenas se necessário. (4) Rodar `python3 fase2/scripts/verificar_documentos.py` (e `--check-delivery` se a entrega exigir reconstrução — apenas se houver alteração documental pendente de publicação).

Restrições: `04_mapa_completo_do_sistema.md`, `05_fluxos_resultados_e_falhas.md`, `07_metodologias_de_testagem.md` e `08_mapa_completo_da_testagem.md` INTOCADOS; correções no documento 06 e no índice somente em dif mínimo com justificativa; nada apresentado como resultado medido; IDs W/O/F permanentes; prosa em português; verificador deve passar ao final; commits de entrega e registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/06_protocolo_de_avaliacao.md` — seção 7 (produtos) e o documento integral após as tasks 001–005.
- `fase2/documentos/07_metodologias_de_testagem.md` e `fase2/documentos/08_mapa_completo_da_testagem.md` — etapas 7/8, para conferência de não-contradição (intocados).
- `fase2/documentos/11_indice_da_entrega.md` — índice da entrega (entrada da etapa 6).
- `fase2/scripts/verificar_documentos.py` — verificação documental (citações, seções, IDs W/O/F, links).

## Corretude
- [ ] C1 — Seção 7 coerente com os critérios de conclusão do plano e sem contradição com as etapas 7/8; correções em dif mínimo ou justificativa de dif zero registrada.
- [ ] C2 — Resumo consolidado registrado na task (decisões, contagens/desvios, congelamento, validações 004–005, pendências como ausência); nada como resultado medido.
- [ ] C3 — Documento registrado no índice da entrega; `python3 fase2/scripts/verificar_documentos.py` passa ao final; commits entrega/registro separados; documentos-fonte intocados.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
3/10 — Consolidação sobre conferências anteriores; o risco é presumir produtos entregues que na verdade pertencem à execução da etapa 8 (deve permanecer registrado como pendência, não como produto).

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
