# Plano: Protocolo de avaliação de saídas e fragilidades (Etapa 6)

Estado: tasks criadas (001–006) — 001 fechada; 002 revisada (decisão: corrigir via subtask 002-1; entrega preservada); próxima: 002-1 (correção do oráculo da borda F13) e depois 003 (anotação e congelamento, bloqueada pelos mínimos de famílias da D4 até novo depósito de corpus)

## Objetivo
Materializar o protocolo de avaliação definido em `fase2/documentos/06_protocolo_de_avaliacao.md`: preparar dados e desenho experimental, construir a matriz de avaliação por saída (O01–O18), o catálogo de testes de falha (F01–F24) e os produtos de avaliação (manifesto congelado, datasets/anotações, logs, métricas com denominadores, relatório de limitações), respondendo às questões Q1–Q3 (integração MA vs. agente único; custo/qualidade da compactação e seleção de skills; contenção de falhas por contratos/validação/limites).

## Abordagem
O documento é normativo: define o que a avaliação futura deve executar. A execução segue as seções do protocolo, nesta ordem de alto nível:

1. **Dados e desenho (seção 2).** Montar corpus autorizado de duas disciplinas (uma técnico-formal, outra conceitual; PDFs digitais, scans, tabelas, versões conflitantes), registrando licença/autorização. Construir os conjuntos propostos: 24 famílias documentais (8 desenvolvimento / 4 validação / 12 teste), 120 consultas e 120 tentativas por conjunto (itens distintos por split, sem vazamento), 30 trajetórias longitudinais com 8 sessões cada (scripts fixos simulados), 100 instâncias de agenda pequenas com ótimo/viabilidade conhecidos + 100 realistas e casos de borda (split 40/20/40%), e no mínimo 10 casos base por falha F01–F24 (3 seeds quando houver geração, mais crashpoints determinísticos). **As quantidades são metas propostas, a conferir por disponibilidade/autorização — não requisitos fechados.**
2. **Anotação e congelamento.** Dois avaliadores independentes, cegos à arquitetura, com rubricas testadas em piloto de desenvolvimento e adjudicação; ouro com IDs de fonte/claim, critérios/erros, fatos temporais e restrições originais (nunca respostas do sistema avaliado). Congelar teste antes de qualquer ajuste; splits por família/trajetória; registrar hashes e acessos.
3. **Condições.** MA completo; SA único com mesmo modelo/corpus/memória/tools/envelope; ablações (sem memória longitudinal, sem compactação, todas as skills carregadas). Comparação principal com teto comum de chamadas/tokens/tempo; análise adicional iguala orçamento real consumido. Seeds 0–4, uma execução por condição/seed, state reset e cache policy registrados; offline como condição separada; connected com mocks/snapshots e depois smoke real de conector.
4. **Matriz por saída (seção 3).** Para cada saída O01–O18, medir conforme "Como medir" (CER/WER, recall@40/nDCG@6/MRR, rubricas 0–4, kappa, replay, leak count etc.), usando os critérios iniciais propostos como **gates de engenharia para o corpus escolhido, não mínimos universais**. Respeitar domínios das métricas (taxas em [0,1]; CER/WER podem exceder 1; kappa em [-1,1]; log loss sem teto); `N/A` exige motivo; se a amostra não sustentar estimativa, reportar IC e resultado inconclusivo, sem baixar limite após olhar teste. Medir artefatos antes de sucesso agregado; turnos de uma mesma trajetória não são amostras independentes.
5. **Testes de falha (seção 4).** Para cada F01–F24, executar par limpo/perturbado com mesmo caso/seed e medir Δqualidade, Δsucesso, Δlatência, Δtokens, efeitos indevidos e tempo até detectar/recuperar; avaliar se a redução de conclusão é explicada e contida.
6. **Sucesso e eficiência (seção 5).** Sucesso de tarefa = todos os critérios essenciais da rota satisfeitos + terminal correto; abstinência correta e diagnóstico correto contam como sucesso nos casos próprios. Na fault-injection, separar task_completion de safe_terminal. Reportar TSR por W, macro e micro; tool-use correctness em quatro níveis separados; tokens/latência com p50/p95, timeout rate, RSS/VRAM, custo por tarefa/trajectory; p95 nunca só de sucessos (indicar censura).
7. **Validade e análise (seção 6).** Comparações pareadas por caso, reamostragem por trajetória/família, IC95%; primárias pré-definidas (TSR longitudinal e taxa de violação crítica publicada); correção para múltiplas hipóteses secundárias; tamanhos de efeito, não só p-values; tamanho amostral estimado após piloto. Juiz LLM apenas para triagem/secundária após calibração contra humanos; anotadores cegos à condição. Declarar limites de generalização (aluno simulado, duas disciplinas, hardware único); qualidade operacional não comprova ganho de aprendizagem.
8. **Produtos (seção 7).** Manifesto congelado, datasets autorizados/anotações ou referências de acesso, logs estruturados, métricas com denominadores, catálogo de falhas, ICs/tabelas por condição, artefatos julgados e relatório de limitações. Os mecanismos por célula são definidos na etapa 7 e os módulos/schemas/execução na etapa 8.

## Escopo
- **Entregas:** datasets/anotações por split, catálogo de falhas F01–F24 com casos base, execução da matriz O01–O18 e F01–F24 conforme protocolo, métricas/ICs/tabelas, manifesto congelado, logs e relatório de limitações.
- **Limites:** não inventar nem ampliar thresholds (os da seção 3 são propostas/gates do corpus escolhido); não apresentar metas de quantidade (24 famílias, 120 consultas, 30 trajetórias, 100 instâncias etc.) como resultados medidos; não estimar ganho humano (scripts simulados apenas testam consistência); estudo humano de aprendizagem fica fora (protocolo próprio futuro); mecanismos por célula e implementação pertencem às etapas 7 e 8, respectivamente; não redistribuir materiais sem permissão.

## Contexto
- `fase2/documentos/06_protocolo_de_avaliacao.md` — documento-fonte normativo: questões Q1–Q3, dados/desenho, matrizes O01–O18 e F01–F24, sucesso global, validade e produtos.
- `fase2/documentos/07_metodologias_de_testagem.md` — define os mecanismos confiáveis para cada célula das matrizes (referenciado na seção 7 do protocolo).
- `fase2/documentos/08_mapa_completo_da_testagem.md` — define módulos, schemas e execução para implementar os mecanismos (referenciado na seção 7 do protocolo).
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — origem das saídas O01–O18 e falhas F01–F24 avaliadas (se houver dúvida de correspondência de IDs).

## Critérios de conclusão
- Corpus autorizado montado com licenças/autorizações registradas e splits congelados (desenvolvimento/validação/teste) antes de ajustes, com hashes e acessos registrados.
- Datasets por split construídos conforme desenho (famílias documentais, consultas, tentativas, trajetórias, instâncias de agenda, casos de falha por F01–F24), com desvios de quantidade documentados por disponibilidade/autorização.
- Cada saída O01–O18 avaliada com as métricas especificadas, unidades preservadas, `N/A` justificado e IC/inconclusivo quando a amostra não sustentar estimativa.
- Cada falha F01–F24 testada em par limpo/perturbado com as medidas de impacto e resultado seguro do protocolo.
- Relatório com TSR (W/macro/micro), task_completion vs. safe_terminal, eficiência (p50/p95, timeouts, custo), análise de validade (IC95%, efeitos, correção de múltiplas hipóteses) e limitações declaradas.
- Produtos da seção 7 completos: manifesto congelado, datasets/anotações ou referências de acesso, logs estruturados, métricas com denominadores, catálogo de falhas, tabelas por condição, artefatos julgados e relatório de limitações.

## Questões abertas
- Disponibilidade real do corpus: as quantidades propostas (24 famílias, 120 consultas/tentativas por conjunto, 30 trajetórias, 100 instâncias de agenda, ≥10 casos por falha) dependem de autorização e devem ser confirmadas — definir desvios aceitáveis antes da coleta.
- Escolha concreta das duas disciplinas/materiais e do juiz LLM (com calibração contra humanos) ainda não está definida no protocolo.
- Meio de medição de energia: só reportar se houver medidor/contador identificado; decidir se haverá.
- Mapeamento fino de cada célula O/F para mecanismos e implementação depende das etapas 7 e 8 — verificar correspondência de IDs antes de executar.

## Tasks
| Ordem | Task | Cobertura (plano) | Depende de | Estado |
|---|---|---|---|---|
| 1 | [001-definir-corpus-autorizacoes-e-desvios-aceitaveis.md](../../tasks/06-protocolo-de-avaliacao/001-definir-corpus-autorizacoes-e-desvios-aceitaveis.md) | Questões abertas (disciplinas, autorizações, desvios, juiz LLM, energia) | nenhuma | fechada (9/10) |
| 2 | [002-montar-corpus-e-conjuntos-por-split.md](../../tasks/06-protocolo-de-avaliacao/002-montar-corpus-e-conjuntos-por-split.md) | Abordagem 1 (dados e desenho, seção 2) | 001 | aguardando subtasks (8/10; registro por material executado: 2 PDFs; agenda sintética completa; demais conjuntos em ausência registrada; correção delimitada 002-1 para o oráculo da borda F13) |
| 2a | [002-1-corrigir-oraculo-borda-f13.md](../../tasks/06-protocolo-de-avaliacao/002-1-corrigir-oraculo-borda-f13.md) | Correção da abordagem 1 (oráculo ambíguo na borda F13 apontado na revisão) | 002 | pendente (subtask de correção; entrega 76b8c7a/73723cf preservada) |
| 3 | [003-anotacao-ouro-e-congelamento.md](../../tasks/06-protocolo-de-avaliacao/003-anotacao-ouro-e-congelamento.md) | Abordagem 2 (anotação e congelamento) | 002 | pendente |
| 4 | [004-validar-matriz-o01-o18-do-protocolo.md](../../tasks/06-protocolo-de-avaliacao/004-validar-matriz-o01-o18-do-protocolo.md) | Abordagem 4 (matriz por saída, seção 3) | 003 | pendente |
| 5 | [005-validar-testes-de-falha-sucesso-eficiencia-e-validade.md](../../tasks/06-protocolo-de-avaliacao/005-validar-testes-de-falha-sucesso-eficiencia-e-validade.md) | Abordagens 5–7 (seções 4, 5 e 6) | 004 | pendente |
| 6 | [006-consolidar-produtos-indice-e-verificador.md](../../tasks/06-protocolo-de-avaliacao/006-consolidar-produtos-indice-e-verificador.md) | Abordagem 3 (condições) + 8 (produtos, seção 7) + critérios de conclusão | 005 | pendente |

Notas: o documento `fase2/documentos/06_protocolo_de_avaliacao.md` já está materializado e registrado no índice da entrega — as tasks 004–006 são de conferência de fidelidade contra as etapas 5/7 e a v0.1 implementada, com correção apenas em dif mínimo no próprio documento 06; as tasks 001–003 executam o preparo real (decisões, corpus/datasets, anotação/congelamento). As condições da abordagem 3 (MA/SA/ablações, seeds, orçamentos) são materializadas na implementação do testbed da etapa 8 (plano 08, task 003) — aqui permanecem como especificação validada. Nada é apresentado como resultado medido; a execução experimental pertence à etapa 8.
