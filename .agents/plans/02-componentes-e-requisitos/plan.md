# Plano: Componentes faltantes e requisitos (Etapa 2)

Estado: aprovado — aguardando escrita de tasks pelo task-master (ao iniciar este plano, o task-master deve derivar as tasks antes de executar)

## Objetivo
Registrar e organizar os 20 componentes do EduAgent-OS que estão "faltantes" no sentido técnico do documento-fonte (não especificados na proposta, não ausência comprovada em implementação), com IDs permanentes (C01–C20) que ligam pesquisa, arquitetura e testes, suas características exigidas, critérios verificáveis, dependências/prioridades e as ambiguidades que exigem decisão antes da implementação.

## Abordagem
- Usar o documento-fonte como especificação normativa do que cada componente (C01–C20) precisa garantir, sem adicionar requisitos ou números não presentes nele.
- Tratar cada ID como permanente e estável: referências futuras de pesquisa, arquitetura e testes devem citar os IDs C01–C20, não nomes alternativos.
- Ordenar o trabalho de implementação futura pela cadeia de dependências do documento:
  - Núcleo: C01 → C02/C03 → C04/C09 → C06/C07/C08 → C11, sustentado desde o início por C13–C17/C20.
  - C18/C19 começam antes da otimização, para impedir que o conjunto de teste oriente escolhas.
  - Opcionais avaliados separadamente: C05 e a sincronização remota de C12; o ICS local de C12 permanece obrigatório no núcleo.
- Registrar as seis ambiguidades do documento como decisões pendentes que bloqueiam ou condicionam os componentes afetados (Bonsai 2 sem identificador/precisão/hardware; estados "evidência insuficiente" e "avaliável" no monitor; não resolver falta de tempo removendo compromissos silenciosamente; reconciliação em vez de substituição automática de prazos; A2A fora do MVP; toda recomendação de pesquisa deve declarar hipótese, alternativa, custo, limitação e teste de seleção).

## Escopo
- Entrega: especificação estruturada dos requisitos de C01–C20 com critérios verificáveis, mapa de dependências e prioridades, e lista de ambiguidades a decidir — materializada em tasks derivadas deste plano, sem criar documento novo nem alterar o documento-fonte (que já contém a tabela, as dependências e as ambiguidades e permanece intocado como fonte normativa).
- Limites: nada aqui estabelece resultado experimental medido — especificação ≠ resultado; valores de qualidade/latência não podem ser derivados da designação "Bonsai 2" conforme o próprio documento; extensões opcionais (C05, sincronização remota de C12, A2A) não são necessárias para fechar o núcleo.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e ambiguidades a decidir.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — mapa normativo de implementação, referência para onde os requisitos dos componentes se concretizam (consultar conforme necessário).
- `fase2/documentos/08_mapa_completo_da_testagem.md` — mapa normativo de avaliação, referência para os critérios verificáveis e para C18/C19 (consultar conforme necessário).

## Critérios de conclusão
- Cada componente C01–C20 está representado nas tasks derivadas deste plano, com suas características exigidas e critério verificável extraídos fielmente do documento-fonte.
- A ordem de implementação (núcleo, C18/C19 antes da otimização, opcionais) está registrada conforme a seção de dependências.
- As seis ambiguidades estão listadas como decisões pendentes, sem resolver nenhuma delas arbitrariamente.

## Questões abertas
1. Bonsai 2 carece de identificador, precisão e hardware-alvo: a escolha concreta do artefato (e o benchmark de português/ferramentas antes da adoção, exigido por C01) precisa de decisão externa.
2. Como operacionalizar os estados "evidência insuficiente" e "avaliável" do monitor formativo (C07) ainda não está definido.
3. Política de reconciliação entre prazos confirmados e documentos externos mais recentes (ligada a C03/C11/C12) pendente de decisão.
4. Definições de orçamentos (chamadas, tempo, reparos — C17) e demais parâmetros não constam do documento e não devem ser inventados aqui.

## Tasks
| Ordem | Task | Componentes | Depende de | Estado |
|---|---|---|---|---|
| 1 | [001-validar-fundacao-inferencia-ingestao-ontologia.md](../../tasks/02-componentes-e-requisitos/001-validar-fundacao-inferencia-ingestao-ontologia.md) | C01, C02, C03 | nenhuma | fechada |
| 2 | [002-validar-rag-e-memoria-persistente.md](../../tasks/02-componentes-e-requisitos/002-validar-rag-e-memoria-persistente.md) | C04, C09 | 001 | fechada |
| 3 | [003-validar-tutor-monitor-e-estado-de-aprendizagem.md](../../tasks/02-componentes-e-requisitos/003-validar-tutor-monitor-e-estado-de-aprendizagem.md) | C06, C07, C08 | 002 | fechada |
| 4 | [004-validar-planejamento-solver-e-agenda.md](../../tasks/02-componentes-e-requisitos/004-validar-planejamento-solver-e-agenda.md) | C11, C12 (ICS local) | 003 | fechada |
| 5 | [005-validar-orquestracao-contratos-e-politica-de-ferramentas.md](../../tasks/02-componentes-e-requisitos/005-validar-orquestracao-contratos-e-politica-de-ferramentas.md) | C13, C14, C15 | 004 | fechada |
| 6 | [006-validar-persistencia-observabilidade-e-empacotamento.md](../../tasks/02-componentes-e-requisitos/006-validar-persistencia-observabilidade-e-empacotamento.md) | C16, C17, C20 | 005 | fechada |
| 7 | [007-validar-dados-e-avaliacao-experimental.md](../../tasks/02-componentes-e-requisitos/007-validar-dados-e-avaliacao-experimental.md) | C18, C19 | 006 | fechada |
| 8 | [008-validar-opcionais-e-consolidar-cobertura-c01-c20.md](../../tasks/02-componentes-e-requisitos/008-validar-opcionais-e-consolidar-cobertura-c01-c20.md) | C05, sinc. remota de C12 + consolidação | 007 | aguardando subtasks (revisão: corrigir — lacuna C10) |
| 9 | _subtask 009 (completar cobertura de C10 e ajustar evidências da consolidação) — criação pendente_ | C10 | 008 | pendente de criação |

Cobertura da cadeia do fonte: núcleo C01 → C02/C03 → C04/C09 → C06/C07/C08 → C11 (tasks 001–004), sustentado por C13–C17/C20 (tasks 005–006), C18/C19 antes da otimização (task 007), opcionais C05 e sincronização remota de C12 (task 008). Todas as especificações são extraídas fielmente de `fase2/documentos/02_componentes_e_requisitos.md`, que permanece intocado como fonte normativo; as seis ambiguidades permanecem decisões pendentes.
