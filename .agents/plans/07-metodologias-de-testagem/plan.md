# Plano: Síntese da pesquisa metodológica de testes (Etapa 7)

Estado: aprovado — aguardando escrita de tasks pelo task-master (ao iniciar este plano, o task-master deve derivar as tasks antes de executar)

## Objetivo
Consolidar a pesquisa metodológica de testagem (documentos 07a/07b) em um documento de síntese (`fase2/documentos/07_metodologias_de_testagem.md`) que registre os métodos selecionados para cada família de saída/falha (O01–O18, F01–F24, C18/C19), as correções que a pesquisa exige em etapas anteriores e as decisões de implementação do testbed — mantendo o caráter de especificação (pesquisa dirigida), sem apresentá-lo como revisão sistemática ou resultado experimental medido.

## Abordagem
Os itens abaixo descrevem o conteúdo já existente nos artefatos acordados, a ser validado nesta etapa, não produzido por ela.

- Partir do relatório `07a` (métodos de qualidade, O01–O18) e do relatório `07b` (robustez e experimentos, F01–F24, C18/C19) e sintetizá-los em uma tabela única de métodos por família, com as referências/bibliotecas associadas (ex.: JiWER, BEIR, ALCE, RAGAs, Prometheus, LongMemEval, AgentDojo, Hypothesis, SciPy).
- Registrar as referências bibliográficas novas em `references_avaliacao_qualidade.bib` e `references_robustez.bib`; reutilizar chaves existentes (não contá-las como evidência independente) e remover a duplicata `zheng2023judge` da bibliografia consolidada.
- Documentar as seis correções exigidas pela pesquisa em etapas anteriores (faixas de CER/WER/kappa/log loss; semântica de DTSTAMP vs. CREATED na etapa4; definição implementável de "contradição recente"; ordem de conferência de `operation_id` no retry idempotente; alcance do diagnóstico INFEASIBLE da grade; denominadores completos de disponibilidade/TSR e regra de "contenção segura não é conclusão original").
- Registrar as decisões para a implementação do testbed: verificadores determinísticos e fixtures positivas/negativas primeiro, avaliações semânticas depois; validar avaliadores com mutações conhecidas; instrumentar sistema e controlador; separar teste de fronteira, E2E, mock conectado e smoke real; congelar estimandos, clusters, thresholds/margens e seeds antes do teste final; não inferioridade exigida por IC compatível com a margem (não apenas p>.05).
- Apontar que a etapa 8 (mapa normativo de testagem) fixa contratos, registro, comandos e plano de execução.

## Escopo
- Entregas desta etapa: este plano registra e valida o que já está acordado no documento de síntese `fase2/documentos/07_metodologias_de_testagem.md` e nos dois relatórios de pesquisa completos (`07a`, `07b`) com as bibliografias novas — esses artefatos já existem no repositório, fazem parte da entrega e não devem ser reescritos (ver Contexto).
- Limites: pesquisa dirigida com leitura de fontes primárias e documentação oficial (30/09/2026); não equivale a revisão sistemática nem à reprodução de experimentos publicados. Nenhum limiar/resultado proposto deve ser apresentado como medido.
- Fora do escopo desta etapa: fixação de contratos, registro, comandos e plano de execução do testbed (pertencem ao mapa normativo 08).

## Contexto
- `fase2/documentos/07_metodologias_de_testagem.md` — documento-fonte da síntese (não modificar; serve de referência do que está acordado).
- `fase2/pesquisa/07a_metodos_qualidade.md` — relatório completo O01–O18: fórmulas/denominadores, procedimentos e oráculos (quatorze fontes).
- `fase2/pesquisa/07b_metodos_robustez_experimentos.md` — relatório completo F01–F24 e C18/C19: injeção de falhas, propriedade/estado, comparação e inferência (dezesseis fontes).
- `fase2/documentos/08_mapa_completo_da_testagem.md` — mapa normativo de testagem; a etapa 8 fixa contratos, registro, comandos e plano de execução (consultar, não alterar).

## Critérios de conclusão
- O documento 07 contém a tabela de métodos por família com referências, as seis correções exigidas e as decisões de implementação do testbed, fiel aos relatórios 07a/07b.
- As referências novas estão nas bibliografias dedicadas e a duplicata `zheng2023judge` está removida da bibliografia consolidada, com chaves únicas e case-sensitive.
- O texto preserva a prosa acadêmica em português e não afirma resultados medidos (especificação ≠ resultado).
- `python3 fase2/scripts/verificar_documentos.py` passa sem erros.

## Questões abertas
- Nenhuma essencial no documento-fonte. Nota: o documento indica que decisões operacionais (contratos, registro, comandos, execução) pertencem à etapa 8 — não reproduzi-las aqui.

## Tasks
<A preencher pelo task-writer.>
