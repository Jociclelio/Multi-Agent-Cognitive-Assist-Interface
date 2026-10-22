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
| 8 | [008-skills-yaml-e-tutor.md](../../tasks/04-mapa-completo-do-sistema/008-skills-yaml-e-tutor.md) | §8 tutor/skills, §13.5 | 007 | resolvida por subtasks (6/10, corrigir → 008a fechada; F1 pistas por sessão em vez de por item, F2 item publicado antes da validação do LearningItem/TutorTurn e F3 coerção de rubrica/validação de schema local confirmados com reprodução; correção integral na 008a) |
| 8a | [008a-correcao-pistas-por-item-e-validacoes-do-tutor.md](../../tasks/04-mapa-completo-do-sistema/008a-correcao-pistas-por-item-e-validacoes-do-tutor.md) | §8, §4, §3.1, §12 | 008 | fechada (9/10, fechar; F1–F4 e A1/A2 corrigidos e provados por 7 testes de regressão, suíte 259 passed; C1–C4 comprovados por quórum de três modelos distintos; handoff para 009: nível de ajuda da tentativa vem dos turnos/eventos de pista, `exposure.help_level` do item publicado é 0) |
| 9 | [009-monitor-e-redutor-deterministico.md](../../tasks/04-mapa-completo-do-sistema/009-monitor-e-redutor-deterministico.md) | §8 monitor/redutor, §15.2 | 008 | resolvida por subtasks (009a + 009b fechadas; decisão original corrigir, 7/10, preservada: F1 erro crítico gated por indecidibilidade global, F2 decidibilidade global vs. por tópico nas duas direções, F4 nível>0 sem span aceito como correct, A2 `critical_criterion_ids` sem validar contra rubrica) |
| 9a | [009a-correcao-decidibilidade-por-topico-erro-critico-e-invariantes-de-evidencia.md](../../tasks/04-mapa-completo-do-sistema/009a-correcao-decidibilidade-por-topico-erro-critico-e-invariantes-de-evidencia.md) | §8, §15.2, §11, §4 | 009 | resolvida por subtasks (009b fechada; decisão original corrigir, 7,5/10, preservada: F1/F2/F3/F5/F6 e A2 luna/GLM provados por 13 regressões novas, suíte 310 passed; F4 obrigatório fechado na 009b — A-01 invariante `level==0` estendida a `missing` e A-02 `kind` conferido em `_published_critical_ids`) |
| 9b | [009b-correcao-invariante-missing-e-rubrica-publicada.md](../../tasks/04-mapa-completo-do-sistema/009b-correcao-invariante-missing-e-rubrica-publicada.md) | §8, §15.2, §4 | 009a | fechada (fechar, 9,5/10: A-01 provado nos dois eixos por sondas de dois revisores — construção recusada e `check()` recusa assessment externo com `SCHEMA_INVALID` sem commit, replay idempotente precedente intacto; A-02 `kind=='item_published'` conferido com recusa tipada; suíte 313 passed; entrega `33d60f6`) |
| 10 | [010-memoria-temporal-e-contexto.md](../../tasks/04-mapa-completo-do-sistema/010-memoria-temporal-e-contexto.md) | §7, §13.6 | 009 | resolvida por subtasks (decisão original `corrigir`, 7/10, entrega `e106baf` preservada; corrigida pela 010a — entrega `fd3e359`, fechada com 9/10: verificação exata de números/datas, corte de fontes sem pressuposto de prefixo e percurso de correção-substituição com recusa tipada da segunda correção, suíte 345 passed) |
| 10a | [010a-correcao-verificacao-exata-corte-de-fontes-e-correcao-sucessiva.md](../../tasks/04-mapa-completo-do-sistema/010a-correcao-verificacao-exata-corte-de-fontes-e-correcao-sucessiva.md) | §7, §5, §15.1 | 010 | fechada (9/10, decisão `fechar`: entrega `fd3e359`, registro `7bd320e`, base `c3f4c70`; R1–R9, suíte 345 passed, quórum GLM 9/10, Luna 7/10 inconclusiva por ambiente — rank_bm25 fora do .venv, resolvida por reprodução de Beam — e Beam 9/10; resíduos de baixa severidade A-01/A-02/A-03 documentados na task) |
| 11 | [011-demandas-atividades-e-politica-evidencia.md](../../tasks/04-mapa-completo-do-sistema/011-demandas-atividades-e-politica-evidencia.md) | §15.3, §15.4 | 010 | fechada (9/10, `fechar`; entrega `2dded12`, registro `f45a29a`, base `dccaf64`; política `assessment_review_policy_v1` determinística por serviço, demandas com unicidade/consolidação/prioridades e ciclo de atividades §15.4 com transições e dependências, suíte 372 passed reproduzida pelos três revisores; residuais A1 payload de política descartado em reescrita, F1–F3 casos-limite de dependência/conflito/ownership — correção pontual futura sem reabrir a família) |
| 12 | [012-solver-cpsat-lexicografico-e-verificador.md](../../tasks/04-mapa-completo-do-sistema/012-solver-cpsat-lexicografico-e-verificador.md) | §9 solver, §15.5, §13.7 | 011 | resolvida por subtasks (tentativa original 8/10, corrigir; entrega `34fe505` e registro `0df7c37` preservados; achado A1 médio — enumerador por união de janelas adjacentes/sobrepostas vs verificador por janela única → `INTERNAL_FAILURE` — corrigido pela 012a; residuais A2/A3 de baixa severidade documentados para correção pontual futura, família fechada sem reabertura) |
| 12a | [012a-correcao-janelas-adjacentes-e-verificador.md](../../tasks/04-mapa-completo-do-sistema/012a-correcao-janelas-adjacentes-e-verificador.md) | §9, §15.5 | 012 | fechada (9/10, fechar; entrega `f82a626`, registro `2bbc562`, base `3e99e33`; semântica (a) — verificador valida cobertura pela união das janelas do dia — alinhada aos dois lados com decisão registrada contra §15.5; C1–C4 provados: sonda reproduzida antes/depois, J1–J4 incluem identidade do diff, suite integral 414 passed reproduzida por GLM 9/10 e beam 9/10, luna 8/10 provisória inconclusiva sem executar a suíte — pendência coberta pela reprodução independente dos demais; residuais baixos: superconjunto não arredondado em `_merged_availability` e validação de intervalo invertido) |
| 13 | [013-ics-preview-confirmacao-outbox.md](../../tasks/04-mapa-completo-do-sistema/013-ics-preview-confirmacao-outbox.md) | §9 ICS/confirmação | 012 | resolvida por subtasks (tentativa original: 7/10, `corrigir`; entrega `f72440c`, registro `d1ecc58`, base `f85c95f` preservados sem reversão; fechada com a subtask 13a; achados A-01 alto, A-02, L-A1, L-A2, G-A1/G-A2 corrigidos na 13a) |
| 13a | [013a-correcao-precisao-temporal-e-sync.md](../../tasks/04-mapa-completo-do-sistema/013a-correcao-precisao-temporal-e-sync.md) | §9, §15.1, §15.5 | 013 | fechada (9/10, `fechar`; entrega `8ddbaea`, registro `4c13c45`, base real `dc00d795` preservada sem reversão; seis correções implementadas e cobertas por R1–R7; quórum sequencial por venv compartilhado — GLM 9/10 com suíte 446 passed reproduzida, luna 8/10 provisória sem executar a suíte por ambiente, coberta pela reprodução independente de GLM e beam, beam 9/10 com suíte 446 passed e sondas reproduzidas; residuais baixos F-2 guarda de hash vazio legado e DTSTART/DTEND com micros documentados para correção pontual futura; família 013 resolvida, libera 014) |
| 14 | [014-grafo-langgraph-intencoes-rotas-checkpoints.md](../../tasks/04-mapa-completo-do-sistema/014-grafo-langgraph-intencoes-rotas-checkpoints.md) | §10, §12 limites, §13.8 | 013 | resolvida por subtasks (tentativa original: 7/10, `corrigir`; entrega `6968403`, registro `121a0e7`, base `2373cfb` preservados sem reversão; C1/C2/C4 comprovados com suíte 482 reproduzida por dois revisores; C3 incompleto — achados altos probe-confirmados de bypass de ownership em `resolve_owned_path` e redirect protocol-relative não revalidado, mais corrida em `TurnLimits` no fan-out e precedência em `begin_step`; fechada pela subtask 14a com 9/10) |
| 14a | [014a-correcao-seguranca-paths-fetch-e-limites.md](../../tasks/04-mapa-completo-do-sistema/014a-correcao-seguranca-paths-fetch-e-limites.md) | §10, §12 | 014 | fechada (9/10, `fechar`; entrega `3b7bce8`, registro `b8fb4bb`, base `8985b45`; 7 itens corrigidos e provados por sondas antes/depois independentes e 8 regressões discriminantes — sensibilidade provada por mutação; suíte 490 passed sem regressões; quórum GLM-5.3-Flash 9/10 e qwen3-27b 9/10 aprovando, gpt-6-luna 8/10 pedindo correção por residual baixo fora do escopo do item 7 — reembolso de débito LLM no caminho `TIMEOUT` pós-`consume_llm` — registrado como dívida para micro-correção futura junto à 016; falha sistemática de seleção de modelo no `task_review` neste turno registrada, quórum completado pela `task` nativa após `config reviewers=""`) |
| 15 | [015-cli-e-api-loopback.md](../../tasks/04-mapa-completo-do-sistema/015-cli-e-api-loopback.md) | §12 CLI/API/traces | 014 | resolvida por subtasks (tentativa original: 7/10, `corrigir`; entrega `429a5cd`, registro `522e997`, base `3f31a47` preservados sem reversão; C1/C2/C4 comprovados por quórum GLM 8/10, qwen3-27b 7/10, gpt-6-luna 7/10 em rodada sequencial por venv compartilhado, suíte 521 passed reproduzida (luna: 520+1 skip ambiental em árvore isolada); C3 incompleto — restore de backup pré-deleção ressuscita payload tombstonado (sonda), caminhos do manifesto sem confinamento contra traversal (achado alto), e C1 com achado alto de escrita cross-user em resume/approve/cancel (sonda) e API sem JSON em falha interna; família fechada pela subtask 15b) |
| 15a | [015a-correcao-ownership-restore-e-api-json.md](../../tasks/04-mapa-completo-do-sistema/015a-correcao-ownership-restore-e-api-json.md) | §12, §15.1 | 015 | resolvida por subtasks (tentativa: 8/10, `corrigir`; entrega `e17cbf0`, registro `6f4b385`, base `95c21af` preservados sem reversão; C1–C4 provados por quórum GLM 9/10, qwen3-27b 9/10, gpt-6-luna 8/10 em rodada sequencial por venv compartilhado, suíte 533 passed reproduzida pelos três (luna por execução da suíte, sondas adversariais não reproduzidas); seis itens obrigatórios e quatro baixos implementados com sondas antes/depois e 12 regressões; ressalva obrigatória: fail-open em `_current_domain_tombstones` (`backup.py` — banco corrente presente porém ilegível faz o restore prosseguir sem confrontar tombstones; luna achado alto, GLM/qwen baixo com recomendação de recusa); família fechada pela subtask 15b) |
| 15b | [015b-correcao-fail-closed-tombstones-correntes.md](../../tasks/04-mapa-completo-do-sistema/015b-correcao-fail-closed-tombstones-correntes.md) | §15.1 | 015a | fechada (9/10, `fechar`; entrega `a9fb8aa`, registro `8955787`, base `23eb88f`; fail-closed do confronto com tombstones do domínio corrente no restore — `domain.sqlite` presente porém ilegível/corrompido/sem tabela recusa com `INTERNAL_FAILURE` e descarte do diretório alvo, lista vazia apenas para ausência documentada do banco; C1–C3 provados por quórum GLM-5.3-Flash 9/10, qwen3-27b 10/10, gpt-6-luna 9/10 em rodada sequencial por venv compartilhado, suíte 535 passed reproduzida por dois revisores, sondas independentes antes/depois incluindo modos de falha extras; observações residuais baixas: TOCTOU conservador entre `exists()` e `connect`, teórico mascaramento por `close()` e acoplamento do teste à redação — dívida opcional de robustez, sem impacto de segurança) |
| 16 | [016-conectores-opcionais-web-e-sync.md](../../tasks/04-mapa-completo-do-sistema/016-conectores-opcionais-web-e-sync.md) | §6 web, §9 sync, §13.9 | 015 | aguardando subtasks (tentativa: 8/10, `corrigir`; entrega `7db9267`, registro `a365ea5`, base `5f56f8e` preservados sem reversão; C1–C4 provados por quórum GLM 9/10, qwen3-27b 9/10, gpt-6-luna 7/10 em rodada sequencial por venv compartilhado, suíte 564 passed reproduzida pelos três com sondas independentes de GLM e qwen; dívida da 014a — reembolso de débito LLM no `TIMEOUT` pós-`consume_llm` — resolvida nesta entrega com discriminação provada por mutação; busca NÃO admitida — questão aberta permanece; Google NÃO admitido sem verificação documental; divergência de severidade resolvida pela posição mais rigorosa: lacuna de admissão do CalDAV sem teste de redirect malicioso no transporte real, que segue redirects automáticos com credencial Basic, e limite de 5 MiB do §6 não imposto na leitura do transporte web; subtask 016a pendente de criação) |
| 17 | [017-ensaio-longitudinal-congelamento-e-relatorio.md](../../tasks/04-mapa-completo-do-sistema/017-ensaio-longitudinal-congelamento-e-relatorio.md) | §13.8, §13.10, §13.235 | 016 | pendente |

Sequência segue o mapa §13 com gates de aceite por etapa (plano, Abordagem); etapas grandes de §13 foram divididas (13.1→001/002; 13.2→003/004/005; 13.5→008/009; 13.7→012/013; 13.8→014/015) mantendo a ordem. Pendências que nenhuma task decide: reranker (007 registra; seleção em validação, mapa §6.6); conector de busca (016: sem ele `CONNECTOR_DISABLED`); modo non-thinking vs thinking (002: perfil congelado no manifesto); timezone `America/Sao_Paulo` (001/017: só após confirmação); suporte a JSON schema do fork (002: verificar por hash). BKT fora do MVP (009 não implementa). Defaults numéricos são escolhas de ensaio, nunca resultados medidos.
