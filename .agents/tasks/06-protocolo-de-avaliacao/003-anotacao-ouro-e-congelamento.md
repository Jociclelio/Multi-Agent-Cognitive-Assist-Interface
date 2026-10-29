# Task 003: Anotação, ouro e congelamento do teste

Estado: aguardando revisão (execução parcial honesta de 2026-10-29 — ver seção Execução e notas; anotação e congelamento pendentes de avaliadores humanos)
Depende de: 002, 001-1 (ambas resolvidas)
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
- [ ] C1 — **Não atendido integralmente.** Rubricas 0–4 para saídas semênticas foram preparadas como rascunho versionado (`eval/annotation/rubricas-v0.1-rascunho.md`: RUB-O04 com quatro dimensões, RUB-O07 contingência, RUB-O08 julgamento formativo, anotação categórica de níveis de ajuda em tentativas). O **piloto no split de desenvolvimento não foi executado** — exige dois avaliadores humanos independentes cegos, indisponíveis nesta sessão (ausência registrada em `eval/annotation/README.md`); nenhum ajuste de rubrica foi registrado porque nenhum piloto ocorreu, e as rubricas estão marcadas como não utilizáveis no teste antes do piloto.
- [ ] C2 — **Não executado.** A anotação com dois avaliadores independentes cegos à arquitetura/condição, a adjudicação e o kappa dependem de avaliadores humanos, inexistentes nesta sessão — anotadores cegos inexistentes **não foram simulados**: nenhum kappa, nenhuma adjudicação e nenhum número de acordo foi inventado. O ouro humano (IDs de fonte/claim, critérios/erros, fatos temporais, restrições originais, nunca respostas do sistema) **não foi produzido** — nenhum `GoldRecord` existe (decisão D5: humanos são ouro de conteúdo; juiz LLM nunca gera ouro). A estrutura/forma do registro está especificada em `eval/annotation/README.md` (mapa 08, §3.2) como insumo para a retomada.
- [ ] C3 — **Não executado.** O congelamento do split de teste não ocorreu: a auditoria de duplicatas/parentesco que o precede (mapa 08, §4) foi executada com resultado `passed` sobre as 19 famílias documentais, mas o split de teste está incompleto (consultas, tentativas, trajetórias e casos de falha pendentes); congelar conjunto parcial forçaria reabertura do manifesto. O congelamento ocorrerá com o conjunto completo, antes de qualquer ajuste da etapa 8, com hashes, acessos e data. Os desvios de quantidade foram atualizados em `eval/datasets/contagens-vs-metas.md` com as justificativas herdadas da task 001 (D4 com emenda E1): famílias 19 ≥ mínimo 18 (meta 24 não alcançada, desvio registrado); consultas/tentativas/trajetórias/falhas 0 com ausência declarada como ausência.

## Execução
- Modelo: GLM-5.3-Flash (provedor `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime.
- Base: 5629b23 (árvore limpa)
- Entrega: c8a926c59fb1d36d1e79bfa20be43a8e6d05e94c (derivação de famílias, auditoria, rubricas-rascunho, registro de ausências)
- Arquivos da entrega: `eval/datasets/familias/registro-familias.json` (novo), `eval/annotation/README.md` (novo), `eval/annotation/rubricas-v0.1-rascunho.md` (novo), `eval/datasets/splits.json`, `eval/datasets/familias/manifesto.json`, `eval/datasets/contagens-vs-metas.md`, `eval/datasets/README.md`
- Evidências: ver seção Evidências de verificação abaixo.

### Evidências de verificação
- `python3 fase2/scripts/verificar_documentos.py` (da raiz, após as alterações): `"status": "passed"` — 11 etapas, 20 componentes, 18 saídas, 24 falhas, 39 links locais, `delivery_pending` vazio; fase2 sem dif (`git diff --numstat -- fase2/ docs/` vazio), submódulo intocado.
- Conferência material do corpus: script JSON↔disco reproduz 19/19 SHA-256 idênticos aos arquivos em `eval/corpus/originais/`, nenhum hash duplicado (identidade com `mat-redes-001` já registrada; não há segundo arquivo no depósito).
- Conferência cruzada da entrega (script): 19 famílias com IDs únicos, mapeamento 1:1 com os materiais do registro, hashes idênticos ao registro e ao disco, splits coerentes entre `registro-familias.json` e `splits.json`, família inteira em um único split, mínimos da D4+E1 atendidos (total 19 ≥ 18; dev 6 ≥ 6; val 3 ≥ 3; test 10 ≥ 9; por disciplina 9 e 10 ≥ 5) e manifesto coerente com as contagens — `CONFERENCIA COMPLETA: passed`.
- JSON válidos: `splits.json`, `familias/manifesto.json`, `familias/registro-familias.json`, `registro-materiais.json`.
- Originais fora do Git: `git check-ignore -v` confirma a regra `.gitignore:46` (`eval/corpus/originais/`); nenhum arquivo de `originais/` adicionado.
- Nada medido do EduAgent-OS: contagens de famílias/materiais são insumo de disponibilidade de dados; kappa, adjudicação, piloto e congelamento não existem e não foram simulados.

## Notas

### Execução parcial (2026-10-29, sessão do executor)

A precondition material da D4 foi verificada como **atendida**: os 19 materiais
depositados (registro conferido, 19/19 hashes idênticos ao disco, nenhum
duplicado) sustentam a derivação de 19 famílias documentais, acima do mínimo de
18 e dos mínimos por split/disciplina da D4 com a emenda E1. A execução
proceedeu então pelo que é genuinamente executável sem avaliadores humanos,
registrando como ausência tudo o que depende deles — nada foi fabricado:

- **Executado (insumo):**
  1. **Derivação de famílias documentais** — 19 famílias, uma por material,
     tipo documento-base (`eval/datasets/familias/registro-familias.json`); itens
     derivados futuros (paráfrases, variantes de ataque, perturbações) devem
     ingressar na família de origem, no mesmo split. Scans 0, tabelas 0 e
     versões conflitantes 0 são suplementos opcionais pela emenda E1 — ausência
     registrada como ausência, sem bloqueio.
  2. **Atribuição de splits por parentesco** — 6 desenvolvimento / 3 validação /
     10 teste (redes 9, aprendizado não supervisionado 10), regra determinística
     por posição curricular fixada por escrito **antes de qualquer anotação e
     sem observação de escores**; registrada em `eval/datasets/splits.json`.
  3. **Auditoria de duplicatas/parentesco** (mapa 08, §4), precondition do
     congelamento — resultado `passed`: hashes todos distintos, sem candidato a
     duplicata, sem referência de ouro no corpus, sem parentes entre famílias
     (nenhum item derivado existe ainda).
  4. **Rubricas 0–4 preparadas como rascunho** (`eval/annotation/rubricas-v0.1-rascunho.md`,
     versão `v0.1-rascunho`): RUB-O04 (corretude/pertinência/clareza/limites),
     RUB-O07 (contingência), RUB-O08 (julgamento formativo) e anotação
     categórica de níveis de ajuda em tentativas — alinhadas à forma de item de
     rubrica do mapa 08 (§3.2) e marcadas como **não pilotadas**.
- **Ausências registradas (não simuladas), documentadas em
  `eval/annotation/README.md`:**
  1. **Piloto de rubricas no split de desenvolvimento** — não executado; exige
     dois avaliadores humanos independentes cegos à arquitetura/condição,
     indisponíveis nesta sessão. Consequentemente, nenhum ajuste de rubrica foi
     registrado (nada a ajustar sem piloto) e as rubricas não podem ser usadas
     no teste antes do piloto (C1 não atendido integralmente).
  2. **Dois avaliadores cegos, adjudicação e kappa** — não produzidos; qualquer
     número de acordo seria invenção (C2 não executado).
  3. **Ouro humano** — nenhum `GoldRecord` criado: por D5, humanos são ouro de
     conteúdo e o juiz LLM nunca gera ouro; sem avaliadores, não há ouro. A
     forma do registro (mapa 08, §3.2) ficou especificada como insumo.
  4. **Congelamento do teste** — não realizado: a auditoria que o precede está
     `passed`, mas o split de teste está incompleto (consultas, tentativas,
     trajetórias e casos de falha pendentes); congelar conjunto parcial forçaria
     reabertura do manifesto. O congelamento ocorrerá com o conjunto completo,
     **antes de qualquer ajuste da etapa 8**, com hashes, acessos e data (C3 não
     executado).
- **Desvios de quantidade** atualizados em `eval/datasets/contagens-vs-metas.md`
  com as justificativas herdadas da task 001: famílias 19 contra meta 24 (dentro
  da faixa aceitável; mínimos atendidos), demais conjuntos 0 com ausência
  declarada como ausência. Nada é resultado medido.
- **Pendência de retomada:** a sessão de retomada precisa de dois avaliadores
  humanos independentes cegos (pseudônimos, mapa blind→run oculto), execuções do
  piloto em dev, adjudicação/kappa, autoria do ouro e dos itens pendentes e, por
  fim, o congelamento — a lista completa está em `eval/annotation/README.md`.
- **Pendência cosmética encerrada:** o título de `contagens-vs-metas.md` citava
  apenas a task 002 (achado informativo da revisão da 001-1); estendido às tasks
  002 e 003, que de fato produziram contagens ali.

O bloqueio e o encaminhamento anteriores permanecem preservados no histórico
desta seção, sem reescrita.

### Bloqueio registrado (2026-10-29, sessão anterior — histórico preservado)

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
7/10 — A execução parcial exigiu calibrar continuamente o que é genuinamente
executável sem avaliadores humanos: a derivação de famílias, a regra de split e
a auditoria de parentesco são mecânicas e verificáveis, mas cada passo da
anotação (piloto, kappa, adjudicação, ouro) dependia de pessoas indisponíveis, e
a tentação estrutural de "preencher" com simulação precisou ser explicitamente
recusada e documentada como ausência em três lugares (task, README de anotação e
contagens). O maior cuidado foi não deixar a entrega parecer mais completa do
que é: critérios C1–C3 permanecem desmarcados mesmo com insumos reais entregues
(rubricas-rascunho, auditoria passed), e o congelamento foi adiado com
justificativa em vez de executado de forma vazia sobre um conjunto parcial.

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
