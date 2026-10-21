# Plano: Metodologias de implementação — decisões reconciliadas da etapa 3

Estado: aprovado — aguardando escrita de tasks pelo task-master (ao iniciar este plano, o task-master deve derivar as tasks antes de executar)

## Objetivo
Consolidar, em plano acionável, a implementação da primeira versão do EduAgent-OS segundo as decisões metodológicas reconciliadas no documento-fonte (síntese da etapa 3, requisitos C01–C20), sem reabrir a pesquisa: os métodos já foram selecionados e os conflitos de parâmetros já foram resolvidos para a etapa 4.

## Abordagem
- O documento-fonte é uma síntese de revisão técnica dirigida pelos vinte requisitos (não é revisão sistemática nem prova de ótimo global). O plano não repete a pesquisa; apenas executa o que ela decidiu.
- Implementar cada componente (C01–C20) pelo método selecionado na tabela "Decisões reconciliadas", usando as referências/chaves indicadas como embasamento, respeitando os "por quês e limites" de cada linha (ex.: confirmação documental prevalece sobre confiança verbal; checkpoint não é commit de domínio; seleção de parâmetros em validação, nunca no teste final).
- Tratar todos os números da seção "Conflitos de parâmetros resolvidos para a etapa 4" como escolhas iniciais configuráveis, não como resultados medidos: janela operacional 32.768 (reservas: saída 16.384, ferramentas 2.048, margem 1.024; entrada máx. 13.312), evidências ≤ 4.096 tokens, memória ≤ 8 unidades / 2.048 tokens, solver de 7 dias com slots de 15 min e 10 s totais entre etapas lexicográficas, estimativa de aprendizagem `null` no MVP (rótulo provisório só com 3 respostas independentes de famílias distintas; intervalos 1/3/7 dias são política de ensaio), grafo com 6 chamadas LLM / 8 ferramentas / 16 transições / 2 reparos globais + 1 por artefato / 120 s de computação ativa por turno. O limite de entrada total prevalece sobre limites locais; não combinar a regra percentual da frente pedagógica com as reservas.
- Congelar a configuração antes do teste final; o teste de desenvolvimento determina viabilidade. Se o hardware não comportar a janela, revalidar o perfil.
- Manter a extensão de agenda remota atrás de feature flag até que a documentação específica e os ensaios de concorrência sejam concluídos.
- Onde o documento aponta para etapas posteriores (C18–C19 completados pela pesquisa das etapas 6–7), não antecipar decisões: seguir os mapas normativos.
- Nos textos entregues, preservar os limites da base bibliográfica (Wood, Corbett e RRF sem texto integral; Chi pelo resumo; BKT via pyBKT; MetaGPT via arXiv consultado; sem reaproveitar a bibliografia preliminar da fase 1) — não afirmar verificações que não ocorreram.

## Escopo
- Entrega: registro do plano de implementação das decisões da etapa 3, cobrindo C01–C20 conforme a tabela de decisões reconciliadas e os orçamentos de parâmetros da etapa 4.
- Limites: o documento integra os relatórios 03a/03b; a síntese não deve ser distribuída sem os relatórios integrantes (o pacote final inclui todos). C18–C19 ficam dependentes da pesquisa específica das etapas 6–7. Nada aqui estabelece resultado experimental: especificação ≠ resultado medido.
- Fora do escopo: reabrir alternativas de método já descartadas (registradas nos relatórios 03a/03b), alterar o documento-fonte ou reescrever decisões já reconciliadas.

## Contexto
- `fase2/documentos/03_metodologias_de_implementacao.md` — documento-fonte: tabela de decisões reconciliadas (C01–C20), conflitos de parâmetros resolvidos para a etapa 4 e limites da base bibliográfica.
- `fase2/pesquisa/03a_arquitetura_rag.md` — relatório integral da frente de arquitetura RAG (C01–C05, C13–C17, C20; 18 núcleos bibliográficos).
- `fase2/pesquisa/03b_pedagogia_memoria_planejamento.md` — relatório integral da frente de pedagogia/memória/planejamento (C06–C12; 18 itens com alcance de leitura discriminado).
- `fase2/pesquisa/references_arquitetura.bib` e `fase2/pesquisa/references_pedagogia.bib` — bibliografias das duas frentes.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — mapa normativo de implementação; prevalece para decisões de implementação.
- `fase2/documentos/08_mapa_completo_da_testagem.md` — mapa normativo de avaliação; prevalece para critérios de teste.

## Critérios de conclusão
- O plano registra, por componente (C01–C20), o método selecionado e seus limites, sem alterar decisões do documento-fonte.
- Os orçamentos de parâmetros da etapa 4 estão reproduzidos como escolhas iniciais configuráveis, com as regras de prevalência e de não combinação explicitadas.
- Os dependentes externos estão identificados: C18–C19 (etapas 6–7), feature flag da agenda remota, congelamento de configuração antes do teste final.
- Nenhum número é apresentado como resultado medido; nenhum texto afirma verificação bibliográfica que não ocorreu.

## Questões abertas
- C18–C19 dependem da pesquisa específica das etapas 6–7 (ainda não contemplada por este plano).
- A documentação específica e os ensaios de concorrência da agenda remota (condição de saída da feature flag) não fazem parte desta etapa.
- Validação dos parâmetros de recuperação (C04) em português ainda pendente, conforme apontado no documento.

## Tasks
| Ordem | Task | Componentes | Depende de | Estado |
|---|---|---|---|---|
| 1 | [001-validar-decisao-inferencia-local-c01-c20.md](../../tasks/03-metodologias-de-implementacao/001-validar-decisao-inferencia-local-c01-c20.md) | C01, C20 | nenhuma | fechada |
| 2 | [002-validar-decisao-ingestao-ontologia-c02-c03.md](../../tasks/03-metodologias-de-implementacao/002-validar-decisao-ingestao-ontologia-c02-c03.md) | C02, C03 | 001 | liberada |
| 3 | [003-validar-decisoes-recuperacao-curadoria-c04-c05.md](../../tasks/03-metodologias-de-implementacao/003-validar-decisoes-recuperacao-curadoria-c04-c05.md) | C04, C05 | 002 | pendente |
| 4 | [004-validar-decisoes-pedagogia-avaliacao-c06-c07-c08.md](../../tasks/03-metodologias-de-implementacao/004-validar-decisoes-pedagogia-avaliacao-c06-c07-c08.md) | C06, C07, C08 | 003 | pendente |
| 5 | [005-validar-decisoes-memoria-planejamento-c09-c10-c11.md](../../tasks/03-metodologias-de-implementacao/005-validar-decisoes-memoria-planejamento-c09-c10-c11.md) | C09, C10, C11 | 004 | pendente |
| 6 | [006-validar-decisoes-agenda-orquestracao-c12-c13-c14.md](../../tasks/03-metodologias-de-implementacao/006-validar-decisoes-agenda-orquestracao-c12-c13-c14.md) | C12, C13, C14 | 005 | pendente |
| 7 | [007-validar-decisoes-persistencia-observabilidade-c15-c16-c17.md](../../tasks/03-metodologias-de-implementacao/007-validar-decisoes-persistencia-observabilidade-c15-c16-c17.md) | C15, C16, C17 | 006 | pendente |
| 8 | [008-validar-dependencia-externa-avaliacao-c18-c19.md](../../tasks/03-metodologias-de-implementacao/008-validar-dependencia-externa-avaliacao-c18-c19.md) | C18, C19 | 007 | pendente |
| 9 | [009-consolidar-parametros-etapa-4-limites-bibliograficos-e-cobertura.md](../../tasks/03-metodologias-de-implementacao/009-consolidar-parametros-etapa-4-limites-bibliograficos-e-cobertura.md) | orçamentos da etapa 4 + limites bibliográficos + consolidação 20/20 | 008 | pendente |

Partição segue as 13 linhas da tabela "Decisões reconciliadas" do documento-fonte, agrupadas em 8 tasks de decisão (001–008) mais a consolidação de orçamentos, limites bibliográficos e cobertura (task 009). Pendências preservadas e não resolvidas por esta família: posicionamento de C10 na cadeia do núcleo; validação de C04 em português; ambiguidades 1–6 da etapa 2; pesquisa específica das etapas 6–7 (C18–C19); feature flag da agenda remota; orçamentos tratados como escolhas iniciais configuráveis, nunca como resultados medidos.
