# Plano: Implementação do EduAgent-OS v0.1 (núcleo textual local)

Estado: aprovado — tasks derivadas (001–017, ordem da sequência do mapa §13); execução pendente de início do ciclo

## Objetivo

Implementar o núcleo textual local do EduAgent-OS v0.1 conforme a especificação
implementável do mapa (mapa §1): cinco agentes lógicos (Curador, Bibliotecário,
Tutor, Monitor, Planejador) em LangGraph, com ingestão PDF/texto, RAG com
citações resolvíveis, tutoria/quiz/flashcards/autoexplicação, evidências
formativas, memória temporal e agenda semanal com exportação ICS. Web e
sincronização de calendário são módulos opcionais com contrato definido; sua
ausência não bloqueia o núcleo. Este plano cobre especificação, não aplicação
executável pronta: o mapa de testes (etapa 8) é quem define critérios
quantitativos e dados de teste.

## Abordagem

Ordem de construção em alto nível conforme mapa §13, cada etapa com gate de
aceite próprio antes da seguinte:

1. Manifesto/hardware e gate de modelo: carregar o candidato Bonsai 2 offline
   (mapa §3.1), validar tokenizer/JSON/tools negadas; se falhar, marcar
   `MODEL_NOT_ADMITTED` sem substituição silenciosa.
2. Contratos Pydantic estritos, DDL/migrações SQLite e commit idempotente
   (mapa §4–5, §11); validar crash/replay.
3. Ingestão (Docling + OCR seletivo), proveniência e confirmação de fatos
   pelo usuário (mapa §6).
4. RAG lexical (BM25) + denso (BGE-M3) + RRF, citação resolvível e abstinência
   documental (mapa §6); reranker decidido em validação.
5. Skills YAML, estados do Tutor, Monitor com rubrica por critério e redutor
   determinístico observado (mapa §8, §15.2).
6. Memória temporal, montagem de contexto com checagem de síntese, correção e
   deleção com propagação (mapa §7, §5).
7. Solver CP-SAT com objetivo lexicográfico + verificador independente
   separado, preview/confirmação e ICS RFC5545 (mapa §9, §15.5).
8. Grafo completo com intenções/rotas, checkpoints, pausas, limites e traces
   (mapa §10, §12); ensaio longitudinal offline.
9. Conectores opcionais (web, sync de calendário) admitidos individualmente
   após contratos e falhas de rede (mapa §6, §9).
10. Congelar manifesto e emitir relatório de testes conforme etapa 8 (mapa
    §13.10).

Invariantes transversais que condicionam tudo: snapshot/ownership com
`domain_revision` monotônica (mapa §15.1), commit idempotente com recibo
(mapa §11), erros tipados com retryability (mapa §4), e nenhuma saída parcial
silenciosamente aprovada (mapa §12).

## Escopo

- MVP: cinco agentes, ingestão, RAG, tutoria/avaliação, memória, agenda/ICS,
  CLI mínima e API loopback (mapa §12, §1).
- Fora do MVP: notas oficiais, treinamento fundacional, voz, vídeos gerados,
  sistemas acadêmicos fechados, multiusuário concorrente em rede (segurança de
  dados por usuário existe desde o esquema), BKT (só shadow mode futuro),
  ANN/Qdrant (extensão), A2A distribuído (adiado) (mapa §1, §8, §14, §15.6).
- Módulos opcionais com contrato: curadoria web, sync via MCP/CalDAV/Google
  (mapa §6, §9). Sem credenciais/conector, não bloqueiam o núcleo.
- Defaults numéricos (janelas de contexto, budgets, limites de ingestão,
  parâmetros BM25/RRF/solver) são defaults de ensaio a calibrar no hardware
  registrado antes do congelamento — não resultados medidos (mapa §1, §3).

## Contexto

- `fase2/documentos/04_mapa_completo_do_sistema.md` — fonte normativa única e
  autocontida; o executor deve lê-lo integralmente e tratar "deve" como
  contrato. As seções §15 fecham decisões da auditoria e prevalecem quando
  especificam regra mais precisa.
- `fase2/documentos/08_mapa_completo_da_testagem.md` — critérios quantitativos,
  dados e aceites de teste (referenciado, fora do escopo deste plano).
- `fase2/documentos/11_indice_da_entrega.md` — índice dos entregáveis.
- `fase2/pesquisa/` — fundamentos e registro histórico (pesquisas 3/7); não
  normativo.

## Critérios de conclusão

Aceite funcional do mapa §13.235, verificável por inspeção/execução:

- Cada rota do grafo (mapa §10) termina com estado definido; cancelamento e
  deadline produzem terminais com erro tipado e artefatos já válidos.
- Cada artefato cumpre o contrato Pydantic da tabela do mapa §4 (inclusive
  invariantes de `*_ref`, spans e confirmações).
- Toda citação `[doc_id@version:página:bloco]` resolve ao original armazenado.
- Toda escrita passa pelo commit idempotente com recibo e versionamento
  (`expected_version`/`domain_revision`); crash/replay não duplica nem perde
  efeito reconhecido.
- Nenhum plano sem validação do verificador independente é publicado como
  aprovado; nenhum ICS é gerado sem plano confirmado.
- Uma sessão retomada de checkpoint preserva item pendente, nível de ajuda e
  histórico do turno.
- Uso de evidências: zero evidência → `insufficient`; sequência `favorable`
  exige as três tentativas mais recentes, independentes/aceitas/decidíveis e
  no tópico, de famílias distintas, todas corretas e posteriores ao último
  erro crítico aceito (mapa §8, §15.2) — regra aplicada exatamente como
  especificada.
- Ingestão acima dos limites é recusada ou dividida; versão incompleta nunca
  vira ativa (mapa §3, §12).
- Manifesto congelado com versões reais (pacotes, modelo, tokenizer, skills)
  em `manifest.json` e `uv.lock`; `MODEL_NOT_ADMITTED` bloqueia tutoria.
- Relatório de testes emitido conforme etapa 8, sem preencher ausência de
  resultados experimentais com estimativas inventadas (mapa §13.235).

## Questões abertas

- Reranker (`BAAI/bge-reranker-v2-m3`): decisão de adotar ou não depende de
  co-residência e validação; o mapa define seleção em validação (mapa §6.6).
- Conector de busca web: deve ser escolhido/configurado na implementação;
  sem ele, `CONNECTOR_DISABLED` (mapa §6).
- Modo do modelo (non-thinking vs thinking): mapa §3.1 manda testar
  non-thinking primeiro e comparar thinking em desenvolvimento; perfil final é
  congelado no manifesto — decisão pendente de validação.
- Timezone default `America/Sao_Paulo` requer confirmação antes de fixar
  (mapa §3).
- Suporte a JSON schema no fork do runtime (`prism-b10743-adfffbe`): capacidade
  a verificar e fixar por hash; parse/schema/política permanecem obrigatórios
  independentemente (mapa §3.1).

## Tasks
| Ordem | Task | Cobertura (mapa) | Depende de | Estado |
|---|---|---|---|---|
| 1 | [001-scaffold-e-configuracao.md](../../tasks/04-mapa-completo-do-sistema/001-scaffold-e-configuracao.md) | §3 stack/diretórios/config | nenhuma | fechada |
| 2 | [002-manifesto-hardware-e-gate-de-modelo.md](../../tasks/04-mapa-completo-do-sistema/002-manifesto-hardware-e-gate-de-modelo.md) | §3.1, §13.1 | 001 | fechada (8,7/10, fechar; gate MODEL_ADMITTED non-thinking; runtime em descendente da tag e política de tool_calls em papéis permitidos encaminhados a 003/017) |
| 3 | [003-contratos-pydantic-e-erros-tipados.md](../../tasks/04-mapa-completo-do-sistema/003-contratos-pydantic-e-erros-tipados.md) | §4 | 002 | resolvida por subtasks (8/10, corrigir; invariantes de `StudyDemand` e enum de `error_codes` verificados/corrigidos na 003a) |
| 3a | [003a-correcao-invariantes-studydemand-e-enum-erros.md](../../tasks/04-mapa-completo-do-sistema/003a-correcao-invariantes-studydemand-e-enum-erros.md) | §4, §8, §15.3 | 003 | fechada (9/10, fechar; validador mandatory⇒confirmed, error_codes no enum tipado, A3–A6 aproveitados, suíte 63 verde) |
| 4 | [004-armazenamento-ddl-migracoes-snapshot.md](../../tasks/04-mapa-completo-do-sistema/004-armazenamento-ddl-migracoes-snapshot.md) | §5, §15.1 | 003 | resolvida por subtasks (8/10, corrigir; ownership de FKs simples e imutabilidade efetiva do snapshot corrigidos e verificados na 004a) |
| 4a | [004a-correcao-ownership-fks-e-snapshot-imutavel.md](../../tasks/04-mapa-completo-do-sistema/004a-correcao-ownership-fks-e-snapshot-imutavel.md) | §5, §15.1 | 004 | fechada (9/10, fechar; migração `0002` com `UNIQUE(user_id,id)` em courses, FK composto em `documents.course_id`, triggers de mesmo dono, snapshot frozen com digest armazenado, `SOURCE_UNRESOLVED`; suíte 107 verde; achados latentes A1/A2 do framework de migrações registrados para 005/006) |
| 5 | [005-commit-idempotente-e-recuperacao.md](../../tasks/04-mapa-completo-do-sistema/005-commit-idempotente-e-recuperacao.md) | §11, §13.2 | 004 | fechada (9/10, fechar; commit idempotente com dedup por `operation_id` antes de `expected_version`, transação atômica evento+operação+outbox+projeção, dispatcher com lease, `UNKNOWN_EFFECT` terminal sem retry, crash/replay provado com `os._exit(137)`; suíte 130 verde; divergência da revisão — posse de lease sob despacho concorrente — resolvida pelo contrato: schema §11 não tem token de lease e §11 promete apenas ao-menos-uma-vez; melhoria registrada para 014/015) |
| 6 | [006-ingestao-docling-ocr-proveniencia-fatos.md](../../tasks/04-mapa-completo-do-sistema/006-ingestao-docling-ocr-proveniencia-fatos.md) | §6.1–3, §13.3 | 005 | resolvida por subtasks (7,5/10, corrigir → 006a fechada; MIME por bytes, dedup, ciclo de versão, OCR seletivo com derivado separado e confirmações verificados com suíte 163; os gaps do adaptador real corrigidos na 006a; smoke do Docling pendente para 017) |
| 6a | [006a-correcao-adaptador-docling-e-ciclos-pdd.md](../../tasks/04-mapa-completo-do-sistema/006a-correcao-adaptador-docling-e-ciclos-pdd.md) | §6.1–3, §12, §13.3 | 006 | fechada (9/10; 8 gaps corrigidos com escolhas registradas, suíte 177 passed, probes da 006 verdes; smoke real do Docling e distinção nativo×OCR por bloco pendentes para 017) |
| 7 | [007-rag-bm25-denso-rrf-citacao-abstinencia.md](../../tasks/04-mapa-completo-do-sistema/007-rag-bm25-denso-rrf-citacao-abstinencia.md) | §6.4–8, §13.4 | 006 | fechada (9/10, fechar; chunking 384/64 com tabelas/páginas preservadas, BM25+denso BGE-M3 pinado com publicação atômica do índice, RRF determinística com desempate por ID, filtros pré-ranking com isolamento provado, citação resolvível e abstinência sem citação fictícia; suíte 212 verde; achados menores — teto de chars em janelas densas, hash de 1 arquivo fora do manifesto, página da citação não conferida, filtro de scores ≤ 0 — e pendências de validação, incl. reranker, encaminhados a 017) |
| 8 | [008-skills-yaml-e-tutor.md](../../tasks/04-mapa-completo-do-sistema/008-skills-yaml-e-tutor.md) | §8 tutor/skills, §13.5 | 007 | aguardando subtasks (6/10, corrigir; F1 pistas por sessão em vez de por item, F2 item publicado antes da validação do LearningItem/TutorTurn e F3 coerção de rubrica/validação de schema local confirmados com reprodução; correção na 008a) |
| 8a | [008a-correcao-pistas-por-item-e-validacoes-do-tutor.md](../../tasks/04-mapa-completo-do-sistema/008a-correcao-pistas-por-item-e-validacoes-do-tutor.md) | §8, §4, §3.1, §12 | 008 | pendente |
| 9 | [009-monitor-e-redutor-deterministico.md](../../tasks/04-mapa-completo-do-sistema/009-monitor-e-redutor-deterministico.md) | §8 monitor/redutor, §15.2 | 008 | pendente |
| 10 | [010-memoria-temporal-e-contexto.md](../../tasks/04-mapa-completo-do-sistema/010-memoria-temporal-e-contexto.md) | §7, §13.6 | 009 | pendente |
| 11 | [011-demandas-atividades-e-politica-evidencia.md](../../tasks/04-mapa-completo-do-sistema/011-demandas-atividades-e-politica-evidencia.md) | §15.3, §15.4 | 010 | pendente |
| 12 | [012-solver-cpsat-lexicografico-e-verificador.md](../../tasks/04-mapa-completo-do-sistema/012-solver-cpsat-lexicografico-e-verificador.md) | §9 solver, §15.5, §13.7 | 011 | pendente |
| 13 | [013-ics-preview-confirmacao-outbox.md](../../tasks/04-mapa-completo-do-sistema/013-ics-preview-confirmacao-outbox.md) | §9 ICS/confirmação | 012 | pendente |
| 14 | [014-grafo-langgraph-intencoes-rotas-checkpoints.md](../../tasks/04-mapa-completo-do-sistema/014-grafo-langgraph-intencoes-rotas-checkpoints.md) | §10, §12 limites, §13.8 | 013 | pendente |
| 15 | [015-cli-e-api-loopback.md](../../tasks/04-mapa-completo-do-sistema/015-cli-e-api-loopback.md) | §12 CLI/API/traces | 014 | pendente |
| 16 | [016-conectores-opcionais-web-e-sync.md](../../tasks/04-mapa-completo-do-sistema/016-conectores-opcionais-web-e-sync.md) | §6 web, §9 sync, §13.9 | 015 | pendente |
| 17 | [017-ensaio-longitudinal-congelamento-e-relatorio.md](../../tasks/04-mapa-completo-do-sistema/017-ensaio-longitudinal-congelamento-e-relatorio.md) | §13.8, §13.10, §13.235 | 016 | pendente |

Sequência segue o mapa §13 com gates de aceite por etapa (plano, Abordagem); etapas grandes de §13 foram divididas (13.1→001/002; 13.2→003/004/005; 13.5→008/009; 13.7→012/013; 13.8→014/015) mantendo a ordem. Pendências que nenhuma task decide: reranker (007 registra; seleção em validação, mapa §6.6); conector de busca (016: sem ele `CONNECTOR_DISABLED`); modo non-thinking vs thinking (002: perfil congelado no manifesto); timezone `America/Sao_Paulo` (001/017: só após confirmação); suporte a JSON schema do fork (002: verificar por hash). BKT fora do MVP (009 não implementa). Defaults numéricos são escolhas de ensaio, nunca resultados medidos.
