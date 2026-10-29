# Task 002: Montar o corpus autorizado e os conjuntos por split

Estado: aguardando subtasks (correção delimitada 002a)
Depende de: 001
Origem: nenhuma

## Prompt
Montar o corpus autorizado das duas disciplinas definidas na task 001 e construir os conjuntos do desenho (seção 2 do protocolo), respeitando os desvios aceitáveis definidos na 001: (1) famílias documentais cobrindo a variedade do protocolo (PDFs digitais, scans, tabelas, versões conflitantes), divididas em desenvolvimento/validação/teste (meta: 8/4/12); (2) consultas e tentativas por conjunto (meta: 120 consultas e 120 tentativas por split, itens distintos por split, sem vazamento); (3) trajetórias longitudinais com 8 sessões cada, roteirizadas com scripts fixos de aluno simulado (meta: 30); (4) instâncias de agenda pequenas com ótimo/viabilidade conhecidos e instâncias realistas, mais casos de borda (split meta 40/20/40%); (5) no mínimo 10 casos base por falha F01–F24, com 3 seeds quando houver geração e crashpoints determinísticos. Splits por família/trajetória (nunca repartir parentes entre splits); registrar estrutura, contagens reais versus metas e os desvios com justificativa; nada redistribuído sem permissão.

Restrições: as metas de quantidade são propostas — registrar contagens reais e desvios, nunca apresentar metas como resultados medidos; IDs F01–F24 e O01–O18 permanentes; prosa em português; commit de entrega (datasets/estrutura) e commit de registro separados; submódulo `docs/playground-llmagenticsystem` não tocado; materiais autorizados não vão para o Git sem permissão explícita (registrar referências de acesso quando o material não puder ser commitado); temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/06_protocolo_de_avaliacao.md` — seção 2: composição dos conjuntos, variedade documental e regras de split.
- `.agents/tasks/06-protocolo-de-avaliacao/001-definir-corpus-autorizacoes-e-desvios-aceitaveis.md` — disciplinas escolhidas, autorizações e desvios aceitáveis (insumo desta task).
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — catálogo F01–F24 (casos base por falha) e O01–O18.
- `fase2/documentos/08_mapa_completo_da_testagem.md` — §4 e §12.1: metas e targets de captura do dataset que os conjuntos devem atender (consultar, não implementar aqui).

## Corretude
- [ ] C1 — Corpus montado com as duas disciplinas e variedade documental do protocolo; fonte e autorização de cada material registradas (ou referência de acesso quando o material não puder ser versionado). **Parcial:** os dois materiais depositados (1 PDF digital por disciplina) têm fonte, tipo, SHA-256, vínculo de versão, modelo de uso e referência de acesso registrados em `eval/corpus/registro-materiais.json`; a variedade documental completa do protocolo (scans, tabelas como material, versões conflitantes) está **ausente** e a ausência foi registrada como ausência com procedimento de coleta (`eval/datasets/familias/manifesto.json`, `contagens-vs-metas.md`) — nada foi fabricado para preenchê-la.
- [ ] C2 — Conjuntos construídos por split (famílias, consultas/tentativas, trajetórias, agenda, ≥10 casos por F01–F24) sem vazamento entre splits e sem repartir parentes; contagens reais versus metas registradas com os desvios justificados pelos limites definidos na 001. **Parcial:** a regra de split por parentesco está documentada e aplicada (`splits.json`; famílias inteiras de agenda por split, sem duplicatas; verificação embutida no gerador); contagens reais versus metas registradas com desvios justificados pelos limites da D4 (`contagens-vs-metas.md`); os conjuntos dependentes de corpus (famílias derivadas, consultas, tentativas, trajetórias, casos de falha) estão em 0 com ausência e procedimento registrados — e, abaixo dos mínimos da D4, a anotação não foi iniciada, conforme a regra pré-fixada na 001.
- [x] C3 — Estrutura dos conjuntos documentada de forma reproduzível (localização, formato, procedimento de geração com seeds quando aplicável); nada apresentado como resultado medido. Estrutura em `eval/datasets/` (README, manifestos por conjunto com localização/formato/estado); gerador determinístico com seed mestre 0 e verificação EDF reproduz byte a byte os conjuntos sintéticos de agenda (hashes SHA-256 registrados no manifesto); nada é apresentado como resultado medido — as quantidades permanecem rotuladas como metas propostas.

## Execução
- Modelo: GLM-5.3-Flash (provedor `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime.
- Base: 680834d
- Entrega: 76b8c7a6895bd5afc00577ed5bd846c1da11bb8a e 73723cfebe1e54ad83a8178bcea732f68cac5a31 (correção cosmica de acentuação em `contagens-vs-metas.md`; `eval/corpus/` + `eval/datasets/`; documento 06, documento 04 e submódulo sem dif)
- Arquivos da entrega: `eval/corpus/README.md`, `eval/corpus/registro-materiais.json`, `eval/datasets/README.md`, `eval/datasets/contagens-vs-metas.md`, `eval/datasets/splits.json`, `eval/datasets/familias/manifesto.json`, `eval/datasets/consultas/manifesto.json`, `eval/datasets/tentativas/manifesto.json`, `eval/datasets/trajetorias/manifesto.json`, `eval/datasets/agenda/manifesto.json`, `eval/datasets/agenda/pequenas.jsonl`, `eval/datasets/agenda/borda.jsonl`, `eval/datasets/falhas/manifesto.json`, `eval/datasets/scripts/gerar_agenda.py`
- Evidências: ver seção Evidências de verificação abaixo e `eval/datasets/contagens-vs-metas.md` para o consolidado de contagens reais versus metas.

## Notas

### Resumo da execução (herda D1–D7 da task 001)

1. **Registro por material (herança de C1 da 001):** dois materiais depositados
   nesta sessão foram registrados em `eval/corpus/registro-materiais.json` com
   fonte, tipo (PDF digital, texto extraível; verificação por `pdftotext`),
   SHA-256, vínculo de versão, datas, modelo de uso (privado, sem
   redistribuição, D2) e referência de acesso. Originais permanecem em
   `eval/corpus/originais/`, fora do Git (regra `.gitignore:46` confirmada).
2. **Contagens reais versus metas (todas as metas permanecem propostas):**
   famílias documentais 2 materiais / 0 famílias derivadas (meta 24; mínimos da
   D4 não atendidos → anotação não iniciada por regra pré-fixada); consultas 0
   por split (meta 120); tentativas 0 por split (meta 120); trajetórias 0
   (meta 30+6+4 com 8 sessões; template de roteiro documentado); agenda:
   100 pequenas **sintéticas** (meta 100; split 40/20/40 exato por família
   inteira), 6 bordas estruturais (2 por split; F13), 0 realistas (meta 100);
   casos de falha 0 em cada F01–F24 (meta ≥10; nenhuma falha declarada
   `N/A`). Consolidado com justificativas em
   `eval/datasets/contagens-vs-metas.md`.
3. **Conjunto sintético de agenda:** gerado por
   `eval/datasets/scripts/gerar_agenda.py` com seed mestre 0 (somente
   biblioteca padrão), viabilidade exata por verificador EDF para tarefas
   unitárias e ótimo afirmado apenas por força de construção na família
   `f05-demanda-total`; reexecução reproduz os arquivos byte a byte (SHA-256
   registrados no manifesto). As instâncias são dados de entrada construídos —
   não dados coletados e não execuções do sistema.
4. **Nenhum material fabricado:** onde a coleta real não foi possível
   (corpus completo, consultas, tentativas, trajetórias, casos de falha,
   instâncias realistas), a ausência foi registrada como ausência com
   procedimento de coleta documentado em cada manifesto.

### Evidências de verificação

- `python3 fase2/scripts/verificar_documentos.py` (da raiz, após as
  alterações): `"status": "passed"` — 11 etapas, 20 componentes, 18 saídas,
  24 falhas, 39 links locais, `delivery_pending` vazio (documento 06 sem dif).
- `python3 eval/datasets/scripts/gerar_agenda.py` (executado duas vezes):
  `OK: 100 pequenas + 6 borda; split = {'desenvolvimento': 40, 'validacao': 20,
  'teste': 40}` com SHA-256 idênticos entre execuções —
  `pequenas.jsonl` `ba15a8677a9d63198643954c7ff7264af22907a8c2f40000462edf5e94abda35`,
  `borda.jsonl` `3a59d4a2612d33afdd7046437d71668128cb7dce776b0be71cb4e9d1f396c478`.
- Validações embutidas no gerador (executadas a cada geração): 100 instâncias;
  40/20/40 exato; nenhuma família repartida entre splits; IDs e conteúdos
  únicos; verificador EDF re-executado sobre cada instância serializada
  confirmando `esperado.viavel`; 2 bordas por split.
- Caracterização dos PDFs: `pdfinfo`/`pdftotext` — MC832 (PDF 1.3, 2 páginas,
  Quartz, criado 2026-07-30) e MC847 (PDF 1.5, 2 páginas, pdfTeX, criado
  2026-08-05); ambos com texto extraível (não são scans).
- `sha256sum` dos originais: MC832
  `d9c2355f7b125c06499e8ccfcca85e95cf0c9320f82779c0496396718ec1d14c`; MC847
  `e3cd8d6a5a8e7e2adfab7d685dca8d70c8396b95d62aa7ba244fede5e729e4f7`.
- `git check-ignore -v`: regra `.gitignore:46` mantém
  `eval/corpus/originais/` fora do Git; `eval/datasets/` e
  `registro-materiais.json` não são ignorados.
- Todos os JSONs validados por `python3 -m json.tool` (8 arquivos OK).
- Submódulo `docs/playground-llmagenticsystem` e
  `fase2/documentos/04_mapa_completo_do_sistema.md` sem dif; documento 06 sem
  dif (nenhuma decisão desta task exigiu ajuste normativo — análogo ao D7 da
  001: as ausências cabem nas metas rotuladas como propostas).

### Pendências de usuário

1. Completar o depósito em `eval/corpus/originais/` com scans, tabelas,
   versões conflitantes e material didático das duas disciplinas até superar
   os mínimos da D4 — precondição para a derivação de famílias, consultas,
   tentativas, trajetórias, instâncias realistas de agenda e casos de falha.
2. Pendência condicional mantida (D2): autorização escrita antes de qualquer
   redistribuição de originais ou anotações verbatim.

### Dificuldade esperada
6/10 — Coleta real de materiais autorizados com controle de vazamento e cobertura das 24 famílias de falha; volume alto de trabalho manual e dependência de autorizações.

### Dificuldade sentida
6/10 — A parte manual foi dominada pela disciplina de honestidade das ausências: distinguir, conjunto a conjunto, o que é meta proposta, o que é dado sintético publicável e o que é ausência registrada, sem nunca apresentar uns pelos outros. O desenho do verificador EDF exato exigiu cuidado com o argumento de troca (limitado a chunks unitários sem dependências, com ótimo restrito à força de construção) e dois defeitos de geração foram pegos pelas validações embutidas (sobreposição de janelas inflando capacidade; teto de prazo referenciando dia sem janela). A dependência externa de coleta (depósito dos materiais pelo usuário) permanece como bloqueio estrutural dos conjuntos dependentes de corpus — tratada como pendência documentada, não contornada.

### Revisão
- Orquestrador: GLM-5.3-Flash (provider `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime do master.
- Alvo: base `680834d`; entrega `76b8c7a` (esqueleto `eval/datasets` + registro por material em `eval/corpus`) e `73723cf` (correção cosmética de acentuação); registro `4f6dfa5` (task.md + índice do plano). Isolamento confirmado: `git diff --stat 680834d..HEAD -- fase2/ docs/` vazio (documento 04, documento 06 e submódulo intocados), commits de entrega e registro separados, árvore limpa durante toda a rodada.
- Modo da rodada: **sequencial** — os três revisores rodam verificador documental, checagens Git e reexecução do gerador na mesma árvore de trabalho compartilhada (mesmo motivo das rodadas anteriores do repositório); um revisor por vez, cada um em sessão nova, sem acesso aos pareceres dos demais.
- Avaliações: GLM-5.3-Flash (sd2): 9/10 — aprovado; Qwen3.8 27B (sorgan-qwen/qwen3-27b): 8/10 — aprovado; GPT-6 Luna (openai/gpt-6-luna): 7/10 — requer correção. Quórum de três modelos distintos cumprido, sem falhas nem substituições.
- Síntese: convergência factual total nos pontos reproduzíveis — os três recomputaram os SHA-256 dos dois originais (idênticos a `registro-materiais.json`), confirmaram os originais fora do Git (`.gitignore:46`), reproduziram byte a byte a geração de agenda (hashes `ba15a867…` e `3a59d4a2…` conferindo com o manifesto e o registro), confirmaram o split 40/20/40 sem família repartida e a ausência de vazamento, e o verificador documental `passed` com dif zero em `fase2/` e `docs/`. GLM reimplementou o EDF do zero e Qwen confirmou a exatidão do verificador por fluxo máximo independente (100/100 de concordância) — o verificador é exato no escopo declarado (chunks unitários, liberação 0, sem dependências). A honestidade das ausências foi confirmada pelos três: contagens reais em zero para conjuntos dependentes de corpus declaradas como ausência, metas preservadas como propostas, nada fabricado, nada apresentado como medido, e anotação não iniciada em estrita observância à regra pré-fixada D4 da task 001. Achados: (i) **baixo** (GLM A1; convergente com Qwen R002-REV-QW-01): bloco de template `### Dificuldade sentida` duplicado com placeholder no registro — removido nesta consolidação, sem efeito sobre dados; (ii) **informativo** (Qwen R002-REV-QW-02): bloqueio de depósito do usuário já propagado ao índice para a 003; (iii) **médio** (Luna A1, divergência de juízo com GLM/Qwen que recomendaram fechar): `eval/datasets/agenda/borda.jsonl:2` — o caso de duração não múltipla (17 min) cita `reserva_min: 30` sem codificar a reserva nem um `esperado` que a aplique, deixando a borda como declaração textual com oráculo ambíguo. A divergência não é factual (GLM e Qwen verificaram as bordas como especificações estruturais coerentes com o escopo declarado no manifesto; Luna aponta defeito concreto neste caso específico) e não exigiu esclarecimento adicional: prevalece o tratamento conservador — oráculo ambíguo em dataset commitado não pode ser congelado pela task 003.
- Nota final: 8/10 — a parte executável da entrega é excelente e verificada por reprodução independente dos três revisores (hashes, determinismo, exatidão do EDF, integridade Git e documental), com honestidade de ausências impecável; a nota desconta o achado médio de oráculo ambíguo na borda F13 e a parcialidade estrutural de C1/C2 (governada pela regra D4 e por dependência externa legítima, não por omissão do executor).
- Parecer: C1 e C2 parciais por natureza, com parcialidade declarada e correta; C3 atendida na parte executável. A pendência material (depósito do corpus completo pelo usuário) é dependência legítima já registrada e não contornada.
- Decisão: **corrigir** — preserva a entrega (`76b8c7a` + `73723cf` + `4f6dfa5`); cria correção delimitada na subtask `002a` para codificar o `esperado` do caso de borda F13 de duração não múltipla (aplicando a regra de `reserva_min` citada ou justificando sua não aplicação) e sanar a ambiguidade de oráculo antes do congelamento; o placeholder de template duplicado já foi removido nesta consolidação.
- Reversão: não se aplica — entrega preservada.
- Próximo passo: subtask pendente `002a-corrigir-oraculo-borda-f13` (a criar); task 003 segue bloqueada pelos mínimos da D4 até novo depósito do usuário.

<!-- task-cycle: {"decision":"corrigir","next_task":".agents/tasks/06-protocolo-de-avaliacao/002a-corrigir-oraculo-borda-f13.md","family":".agents/tasks/06-protocolo-de-avaliacao/001-definir-corpus-autorizacoes-e-desvios-aceitaveis.md","plan":".agents/plans/06-protocolo-de-avaliacao/plan.md"} -->

Plano: [plan.md](../../plans/06-protocolo-de-avaliacao/plan.md)
