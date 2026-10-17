# Plano: Correções documentais pendentes da revisão externa (fase2)

Estado: rascunho

## Objetivo
Executar a decisão **"corrigir"** da revisão externa de 2026-10-13 (registrada em `fase2/documentos/revisao_externa.md`): aplicar as cinco correções documentais delimitadas (itens 1–5 da seção "Decisão e encaminhamento") na árvore `fase2/`, preservando a entrega já avaliada (nota consolidada 8,3/10), sem reverter nada e sem reabrir decisões de arquitetura.

## Abordagem
- Tratar os itens 1–5 do encaminhamento como uma lista delimitada de correções documentais, executadas por subtask(s) únicas de revisão documental (como o documento propõe), nesta ordem sugerida de dependência:
  1. **Republicar o DDL do mapa4 §5** consolidado com §15 aplicada: `user_id`/ownership em `items`, `domain_revision`, `artifact_dependencies`, `assessment_topics`, unicidade `(attempt_id, assessment_revision)` (em vez de `(attempt_id, assessor_version)`), campos de revisão/ocorrência em `logical_blocks`.
  2. **Resolver a contagem de consultas** ("120 por partição" em etapa6/tex vs. "80 por disciplina por split" no mapa8 §12.1): adotar uma única contagem e recalcular runs (6.000 foram calculadas sobre 120 totais), estratos, custo e potência nos documentos afetados.
  3. **Tornar gates/contratos mensuráveis**: declarar casos/thresholds para `MODEL_NOT_ADMITTED`; definir rota/contrato de aceitação de revisão de assessment (caminho exercitado pelo oráculo O09, hoje não coberto por W04/W10); schema do `CanonicalSnapshot`; incluir `topic_ids` no schema resumido do GoldRecord.
  4. **Reprodutibilidade de RAG/OCR**: nomear candidatos/pin para motor OCR, embeddings (BGE-M3) e reranker — ou declará-los explicitamente como gate de manifesto; definir a regra de dupla contagem de tokens (embedding vs. Bonsai); tratar o orçamento do verificador fora dos 10 s.
  5. **Pré-registros no freeze e reescritas P2**: esforço/orçamento de tuning do baseline SA; margem própria do contraste reduced; regra conjunta operacional no mapa8 §9; reescrever os menores P2 ("inclusive assistido" no mapa8, DTSTAMP vs. RFC, autenticação local, RSS/VRAM como cota inferior).
- Cada item deve ser aplicado mantendo a honestidade documental: propostas/pinagens futuras ficam como pré-registro ou gate declarado, jamais como resultado medido.
- Após as edições: rodar `python3 fase2/scripts/verificar_documentos.py` (e `--check-delivery` se fizer sentido para os arquivos tocados); se a entrega do LaTeX mudar, regenerar via `python3 fase2/scripts/gerar_entrega.py` conforme regras de `fase2/README-entrega.md`.
- Encaminhar a entrega corrigida a nova rodada de revisão com quórum de três modelos distintos, conforme `.agents/contrato-revisor.md` (pareceres anteriores: GLM-5.3-Flash, muse-spark-1.3, gpt-5.6-terra; sessões originais registradas no documento-fonte).
- Commits de entrega e de registro separados, conforme o protocolo de `.agents/protocolo.md`.

## Escopo
- **Dentro:** os cinco itens delimitados acima nos documentos de `fase2/` (mapa4, mapa8, tex/etapa6 e documentos diretamente afetados); re-verificação documental; eventual regeneração da entrega; re-revisão externa com quórum.
- **Fora:** reabrir decisões de arquitetura; implementação de código; alterar o parecer da rodada ou o próprio `revisao_externa.md`; os "critérios pendentes legítimos" (hardware/pins do Bonsai 2, corpus autorizado, calibração via piloto, conteúdo de prompts/skills, conector web/sync, BKT shadow, exclusão lógica) permanecem pendentes por design.

## Contexto
- `fase2/documentos/revisao_externa.md` — documento-fonte: registro da rodada de revisão com três modelos, decisão "corrigir" e a lista delimitada de correções (itens 1–5).
- `fase2/documentos/04_mapa_completo_do_sistema.md` — mapa normativo com o DDL da §5 (e §15) a consolidar (item 1).
- `fase2/documentos/08_mapa_completo_da_testagem.md` — mapa normativo com metas de consultas (§12.1), regra conjunta (§9) e oráculos/W-numbers citados nas correções (itens 2, 3 e 5).
- `fase2/fase2_metodologia.tex` (e documento de etapas correspondente, ex.: etapa6) — fontes das contagens contraditórias de consultas e regras concorrentes (item 2).
- `.agents/contrato-revisor.md` — contrato do quórum de revisão de três modelos distintos.
- `.agents/protocolo.md` — protocolo do fluxo (commits de entrega/registro separados, invariantes).
- `fase2/scripts/verificar_documentos.py` — verificação documental obrigatória após as edições.
- `fase2/README-entrega.md` — requisitos da regeneração da entrega (pdflatex/bibtex, pacotes), se aplicável.

## Critérios de conclusão
- Os cinco itens 1–5 do encaminhamento aplicados nos arquivos correspondentes, sem alterar decisões de arquitetura.
- `python3 fase2/scripts/verificar_documentos.py` passa sem erros (incluindo `--check-delivery`, se a entrega for tocada); entrega LaTeX regenerada com sucesso quando necessário.
- Nenhum texto apresenta proposta/limiar futuro como resultado medido.
- Nova rodada de revisão externa lançada com três modelos distintos (quórum do contrato) e decisão subsequente registrada pelo master (fechar/corrigir/reiniciar/repartir).

## Questões abertas
- Contagem de consultas: 120 total vs. 80 por disciplina por split — qual adotar não está decidido no documento-fonte; requer decisão do master/plano antes de recalcular runs e orçamento.
- Itens 3 e 4 admitem alternativa "declarar como gate de manifesto" em vez de pinar candidatos — escolher por item ou uniformizar.
- Se a nova rodada de revisão deve reavaliar a árvore inteira ou apenas o delta das correções (o contrato de revisão não especifica escopo de re-revisão).

## Tasks
<A preencher pelo task-writer.>
