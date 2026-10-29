# Task 003: Anotação, ouro e congelamento do teste

Estado: aguardando subtasks (001-1 — emenda da D4, pendente)
Depende de: 002, 001-1
Origem: nenhuma

## Prompt
Executar a anotação e o congelamento (seção 2 do protocolo): (1) Preparar rubricas por tipo de saída (rubricas 0–4 para saídas seméricas) e testá-las em piloto no split de desenvolvimento, ajustando antes do uso no teste. (2) Anotar com dois avaliadores independentes cegos à arquitetura e à condição, com adjudicação nos desacordos; registrar kappa. (3) Construir o ouro com IDs de fonte/claim, critérios/erros, fatos temporais e restrições originais — o ouro NUNCA contém respostas do sistema avaliado. (4) Congelar o split de teste antes de qualquer ajuste do sistema sobre ele: registrar hashes dos arquivos congelados, acessos e data; a partir do congelamento, nenhum item de teste pode ser alterado. Registrar desvios em relação às metas com as justificativas herdadas da task 001.

Restrições: anotadores cegos à arquitetura e à condição; o ouro nunca deriva de saída do sistema; nada apresentado como resultado medido (contagens de anotação são insumo, não resultado experimental); prosa em português; commits de entrega e registro separados; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/06_protocolo_de_avaliacao.md` — seção 2 (anotação e congelamento): dois avaliadores cegos, rubricas com piloto, adjudicação, ouro com IDs de fonte/claim, hashes e acessos.
- `.agents/tasks/06-protocolo-de-avaliacao/002-montar-corpus-e-conjuntos-por-split.md` — conjuntos por split produzidos (insumo).
- `fase2/documentos/07_metodologias_de_testagem.md` — famílias de métodos que definem que tipo de anotação cada métrica exige (consultar; a implementação dos mecanismos é da etapa 8).
- `fase2/documentos/08_mapa_completo_da_testagem.md` — §3 schema `AnnotationRecord` e §4 auditoria de parentesco (consultar para alinhar formato de anotação).

## Corretude
- [ ] C1 — Rubricas testadas em piloto no split de desenvolvimento antes do uso; ajustes de rubrica registrados.
- [ ] C2 — Anotação com dois avaliadores independentes cegos à arquitetura/condição, com adjudicação e kappa registrados; ouro com IDs de fonte/claim, critérios/erros, fatos temporais e restrições originais, sem nenhuma resposta do sistema avaliado.
- [ ] C3 — Split de teste congelado antes de qualquer ajuste sobre ele: hashes registrados, acessos e data registrados; desvios de quantidade documentados com as justificativas da 001.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Bloqueio registrado (2026-10-29)

A task não foi executada: o impedimento é a **precondition pré-fixada na decisão
D4 da task 001** — "abaixo dos mínimos: não iniciar anotação; registrar
indisponibilidade". Conferido nesta sessão:

- **Corpus depositado:** apenas 2 materiais, ambos PDFs digitais (um por
  disciplina) — `mat-redes-001` (programa MC832-A) e `mat-ans-001` (PDD MC847),
  depositados em 2026-10-29 na sessão da task 002
  (`eval/corpus/registro-materiais.json`); **nenhum novo depósito** desde então
  (diretórios `eval/corpus/originais/` inalterados, conferidos por timestamp).
- **Mínimos da D4 não atingidos:** famílias documentais 0 derivadas (mínimo ≥18
  no total; dev ≥6, val ≥3, test ≥9; ≥5 por disciplina); scans 0 (mínimo ≥2),
  tabelas 0 (mínimo ≥2), versões conflitantes 0 — ver
  `eval/datasets/contagens-vs-metas.md`.
- **Consequência pela regra da D4:** a anotação (rubricas com piloto, dois
  avaliadores cegos, adjudicação, kappa) **não inicia**, pois não há split de
  desenvolvimento povoado para o piloto nem corpus para derivar itens; o
  congelamento do split de teste (C3) também não ocorre, pois não há itens de
  teste para congelar. Critérios C1–C3 permanecem desmarcados, sem evidência.
- **Dependência de usuário:** a coleta completa exige o depósito de scans,
  tabelas, versões conflitantes e material didático das duas disciplinas em
  `eval/corpus/originais/` (fora do Git), conforme registrado na task 002 e em
  `contagens-vs-metas.md`. A pendência de autorização de redistribuição (D2)
  permanece condicional e registrada.
- **Nada foi fabricado** para contornar o bloqueio: nenhuma rubrica "preparada"
  sem piloto, nenhuma anotação simulada, nenhum hash de congelamento fictício.
  A ausência é declarada como ausência; nada aqui é resultado medido.

As sucessoras da família (004, 005 e 006) declaram dependência da 003 e
permanecem pendentes até o desbloqueio pelo depósito do corpus.

### Dificuldade esperada
6/10 — Coordenar anotação cega com adjudicação e congelamento auditável; o risco é vazamento de condição para os anotadores ou congelamento incompleto (hash faltante).

### Dificuldade sentida
não se aplica — task não executada (bloqueio anterior à execução).

### Revisão
- Orquestrador: GLM-5.3-Flash (provedor `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime; master do ciclo opt-in.
- Alvo: nenhum — não houve execução nem entrega desta task; bloqueio registrado antes da delegação, sem commit de entrega e sem commit de registro de execução.
- Avaliações: nenhuma — sem entrega, não há alvo para rodada de revisão; quórum não se aplica.
- Nota final: n/a — bloqueio, não fechamento (estado `bloqueada`, não `fechada`).
- Parecer: a precondition da D4 (regra pré-fixada antes de qualquer coleta na task 001) não é atendida pelos depósitos atuais: 0 famílias derivadas, 0 scans, 0 tabelas, 0 versões conflitantes contra mínimos ≥18 famílias/dev ≥6/val ≥3/test ≥9/≥5 por disciplina/≥2 scans/≥2 tabelas. Sem split de desenvolvimento povoado, C1 (piloto de rubricas) não é executável; sem corpus, C2 (anotação cega com ouro por IDs) e C3 (congelamento com hashes) não são executáveis. O encaminhamento correto é o bloqueio documentável, sem inventar solução nem fabricar insumos.
- Decisão: **bloqueada** — impedimento documentável dependente de usuário (depósito de corpus até os mínimos da D4); sem sucessora; o ciclo encerra com o estado preservado para retomada.
- Reversão: não se aplica — sem artefatos a reverter (nenhum commit de entrega desta task).
- Próximo passo: usuário deposita os materiais restantes em `eval/corpus/originais/` com registro por material; retomar a task 003 (nova execução pela task 001 da família `001-definir-corpus-autorizacoes-e-desvios-aceitaveis.md`, que permanece raiz da família), atualizando `contagens-vs-metas.md` antes de iniciar a anotação.

### Atualização do encaminhamento (2026-10-29, sessão master posterior)

O impedimento registrado acima evoluiu por decisão do usuário; nenhum novo
parecer técnico é emitido aqui (não houve entrega desta task) e a decisão de
bloqueio original permanece preservada no histórico desta seção:

- **Decisão do usuário (2026-10-29):** scans, tabelas, versões conflitantes,
  resoluções de exercícios e notas de monitoria são suplementares opcionais,
  fornecidos pelo aluno quando existirem — professores não costumam fornecê-los
  e o sistema não pode depender deles; o corpus autorizado é construído com o
  que os professores de fato disponibilizam. Isso emenda a regra da D4 que
  bloqueava esta task.
- **Depósito novo:** 17 materiais adicionais registrados em 2026-10-29 (tarde) —
  8 PDFs de Redes do Google Classroom (G_MC832A_2026S2) e 9 notas de aula em
  HTML de MC847 (fonte pública do docente) — totalizando 19 materiais das duas
  disciplinas, fora do Git; o registro por material é escopo da subtask 001-1.
- **Subtask criada:** `001-1-corrigir-variedade-documental-opcional-aluno.md`
  (commit `d964597`) — emenda da D4 na task 001, dif mínimo na linha 11 do
  documento 06 e registro por material; origem 001, mesma família.
- **Encaminhamento atualizado:** de `bloqueada` para `corrigir`, com próxima
  task 001-1 (subtask da família 001 tem prioridade sobre esta task); a 003
  volta a ser retomável após 001-1 fechar. O contrato desta task (prompt,
  contexto e critérios C1–C3) permanece inalterado.

<!-- task-cycle: {"decision":"corrigir","next_task":".agents/tasks/06-protocolo-de-avaliacao/001-1-corrigir-variedade-documental-opcional-aluno.md","family":".agents/tasks/06-protocolo-de-avaliacao/001-definir-corpus-autorizacoes-e-desvios-aceitaveis.md","plan":".agents/plans/06-protocolo-de-avaliacao/plan.md"} -->

Plano: [plan.md](../../plans/06-protocolo-de-avaliacao/plan.md)
