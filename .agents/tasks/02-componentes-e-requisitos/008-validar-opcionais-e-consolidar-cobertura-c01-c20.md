# Task 008: Validar opcionais (C05 e sincronização remota de C12) e consolidar cobertura C01–C20

Estado: aguardando revisão
Depende de: 007
Origem: nenhuma

## Prompt
Duas partes:

**Parte 1 — Opcionais.** Conferir que a especificação abaixo reproduz **fielmente** o que `fase2/documentos/02_componentes_e_requisitos.md` estabelece para os conectores opcionais (documento-fonte normativo, que permanece intocado):
- **C05 — Curadoria conectada (opcional):** busca/fetch controlados, metadados de texto/vídeo, idioma, acessibilidade e nível; distinguir leitura de metadados de leitura de transcrição; funcionamento offline sem URLs inventadas *(Conector opcional avaliado separadamente; não é necessário para fechar o núcleo.)*
- **Sincronização remota de C12 (opcional):** apenas o aspecto de integração remota/agenda conectada é opcional; o ICS local de C12 permanece obrigatório no núcleo (especificado na task 004). A especificação do aspecto opcional deve citar C12 pelo ID permanente e não pode reclassificar o ICS local como opcional.

**Parte 2 — Consolidação.** Conferir e registrar em Evidências que: (a) todos os componentes C01–C20 estão representados nas tasks desta família (001–008), cada um com características exigidas e critério verificável extraídos fielmente do documento-fonte; (b) a ordem de implementação futura está registrada conforme a seção de dependências do fonte: núcleo C01 → C02/C03 → C04/C09 → C06/C07/C08 → C11, sustentado desde o início por C13–C17/C20; C18/C19 começam antes da otimização; C05 e sincronização remota de C12 avaliados separadamente; (c) as seis ambiguidades do documento-fonte estão registradas como decisões pendentes, distribuídas pelas tasks onde são relevantes, sem que nenhuma tenha sido resolvida arbitrariamente.

Desvio de fidelidade: corrija apenas o texto desta task em dif mínimo e registre em Evidências. Se a consolidação revelar lacuna de cobertura (componente sem task), registre o impedimento em Evidências e no campo Notas — não crie task nem edite tasks de outras sessões.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver ambiguidades; não apresentar especificação como resultado medido; prosa em português; commit de registro separado, sem amend/force-push/commits vazios.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e as seis ambiguidades.
- `.agents/tasks/02-componentes-e-requisitos/` — tasks 001–007 desta família, objeto da conferência de cobertura.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; "Critérios de conclusão" define o que a consolidação deve comprovar.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [x] C1 — Características e critérios de C05 e do aspecto opcional de C12 correspondem item a item ao documento-fonte; ICS local permanece obrigatório no núcleo, sem reclassificação.
- [ ] C2 — Cobertura completa comprovada: cada componente C01–C20 mapeado à task onde está especificado (lista explícita em Evidências); nenhum componente órfão. **(NÃO comprovado integralmente: C10 — Gestão do contexto não é mencionado em nenhuma task da família nem no plano; impedimento registrado em Evidências e Notas — 19/20 componentes mapeados.)**
- [x] C3 — Cadeia do núcleo, camada transversal desde o início, C18/C19 antes da otimização e opcionais separados registrados conforme a seção de dependências do fonte.
- [x] C4 — As seis ambiguidades estão listadas como decisões pendentes e nenhuma foi resolvida nesta etapa.
- [x] C5 — Documento-fonte intocado (`git diff` vazio para ele em relação à base); correções limitadas ao arquivo desta task em dif mínimo; commit de registro com evidências separado de qualquer commit de entrega; sem commits vazios, amend ou force-push.

## Execução
- Modelo: GLM-5.3-Flash (via ~/sd2-llm.sh; provider sd2, model GLM-5.3-Flash)
- Base: `dd7ca8a55e4e7d037cb0da102966180a94ccc10c` (HEAD, árvore limpa)
- Entrega: `dd8134c00464feb2c0e0313c8bb6ba92808224f3` (correção de fidelidade no próprio arquivo da task; commit de registro separado, sem SHA próprio neste arquivo)
- Arquivos da entrega: `.agents/tasks/02-componentes-e-requisitos/008-validar-opcionais-e-consolidar-cobertura-c01-c20.md` (1 linha, remoção do ponto final acrescido na célula C05; nenhum outro arquivo alterado)
- Evidências:
  - **C1 (fidelidade item a item, célula C05 da tabela do fonte)** — Conferência textual automatizada (script isolado em `/tmp/opencode/check_008.py`, extração por regex da célula C05 do fonte e do bullet da especificação da task, comparação após normalização NFC/minúsculas/espaços) da célula C05 (linha 11) de `fase2/documentos/02_componentes_e_requisitos.md`: antes da correção, o único desvio era tipográfico — ponto final acrescido ao final da célula copiada (o fonte não pontua as células), mesmo desvio corrigido nas tasks 001–007; nenhum termo, critério ou cláusula divergia. Item a item: C05 = busca/fetch controlados ✓, metadados de texto/vídeo ✓, idioma ✓, acessibilidade ✓, nível ✓, distinguir leitura de metadados de leitura de transcrição ✓, funcionamento offline sem URLs inventadas ✓. Após a remoção do ponto final (commit de entrega `dd8134c`, dif de 1 caractere): `C05 FIEL`. Diferença legítima mantida: inicial minúscula em "busca" na task (posição na frase, como "artefato" na task 001).
  - **C1 (aspecto opcional de C12; ICS local não reclassificado)** — A seção "Dependências e prioridades" do fonte (linha 30) estabelece: "C05 e a **sincronização remota de C12** são conectores opcionais avaliados separadamente; ICS local de C12 é obrigatório no núcleo." Conferência automatizada: a task 008 declara "apenas o aspecto de integração remota/agenda conectada é opcional" ✓; "o ICS local de C12 permanece obrigatório no núcleo" ✓; cita o componente pelo ID permanente C12 ✓; e proíbe explicitamente reclassificar o ICS local como opcional ✓. A task 004 (célula C12, nota de prioridade) mantém a fronteira coerente ("o ICS local de C12 é obrigatório no núcleo; a sincronização remota de C12 é conector opcional avaliado separadamente — especificada na task 008") ✓. A glosa descritiva "integração remota/agenda conectada" da task mapeia o nome canônico do fonte ("sincronização remota de C12") e o aspecto correspondente na célula C12 do fonte (linha 18: "integração MCP opcional"), sem contradizer o fonte nem reclassificar o ICS local; nenhum desvio de fidelidade a corrigir nesse bullet.
  - **C2 (cobertura C01–C20 pelas tasks 001–008; IMPEDIMENTO: C10)** — Lista explícita componente → task (extraída da tabela do plano e confirmada por varredura automatizada de IDs nos oito arquivos, regex `\bC\d\d\b`): C01, C02, C03 → task 001; C04, C09 → task 002; C06, C07, C08 → task 003; C11, C12 (ICS local) → task 004; C13, C14, C15 → task 005; C16, C17, C20 → task 006; C18, C19 → task 007; C05 e sincronização remota de C12 → task 008 (esta). Resultado da varredura: 19 dos 20 componentes do fonte têm ao menos uma menção; **C10 — Gestão do contexto (célula da linha 16 do fonte: "Medir tokens com tokenizer real, reservar saída e ferramentas; recuperar antes de resumir; sumarização com checagem de fatos críticos; preservar prazos e evidências; medir perda de informação") não aparece em nenhuma task da família (001–008) nem no `plan.md`** (script: `SEM NENHUMA MENÇÃO EM NENHUMA TASK: ['C10']`; `faltando no plano: ['C10']`). Conforme o Prompt, registrado como impedimento em Evidências e Notas — nenhuma task criada, nenhuma task de outra sessão editada, documento-fonte intocado. O critério C2 fica marcado como não comprovado integralmente (19/20); a decisão sobre como fechar a lacuna (criar task dedicada a C10, repartir o plano ou registrar exceção) é do master.
  - **C3 (ordem de implementação conforme a seção de dependências do fonte)** — Conferência automatizada contra a linha 30 do fonte: a task 008 registra a cadeia do núcleo "C01 → C02/C03 → C04/C09 → C06/C07/C08 → C11" (trecho idêntico ao fonte, script: `cadeia no fonte == cadeia na task: True`), sustentada desde o início por C13–C17/C20 ✓; "C18/C19 começam antes da otimização" ✓; "C05 e sincronização remota de C12 avaliados separadamente" ✓. Coerente com os Prompts das tasks 002–007 (cada uma cita sua posição na cadeia, verificada nas execuções 001–007) e com o `plan.md` (linha de cobertura do fonte).
  - **C4 (seis ambiguidades registradas como pendentes, distribuídas, nenhuma resolvida)** — Distribuição confirmada por varredura nos oito arquivos: ambiguidade 1 (Bonsai 2 sem identificador/precisão/hardware) → task 001 (nota anexa a C01); ambiguidade 2 (estados "evidência insuficiente"/"avaliável" no monitor) → task 003 (nota anexa a C07); ambiguidade 3 (não resolver falta de tempo removendo compromissos silenciosamente) → task 004 (nota anexa a C11); ambiguidade 4 (documento externo mais recente não substitui prazo confirmado; reconciliação) → tasks 001 (C03) e 004 (C11); ambiguidade 5 (A2A fora do MVP) → task 005 (nota anexa a C14); ambiguidade 6 (toda recomendação de pesquisa deve declarar hipótese, alternativa, custo, limitação e teste de seleção) → task 007 (Restrições: "registrar como pendência, não aplicá-la"). Todas aparecem apenas como decisões pendentes; varredura de marcadores de resolução na task 008 ("decidimos", "resolvemos", "definimos que", "fica definido"): nenhum; nenhuma das seis foi resolvida em 001–008.
  - **C5 (fonte intocado; correção mínima; commits separados)** — `git diff dd7ca8a -- fase2/documentos/02_componentes_e_requisitos.md`: vazio (0 linhas); `git diff --stat` da entrega: somente o arquivo desta task, 1 inserção/1 remoção (o ponto final da célula C05). Nenhum documento novo criado; `docs/playground-llmagenticsystem` (submódulo) não tocado. Commit de entrega `dd8134c` separado do commit de registro; sem amend, force-push ou commits vazios (histórico linear verificado).
  - **Verificador do repositório (apoio)** — `python3 fase2/scripts/verificar_documentos.py` a partir da raiz: `status: "passed"`, `components: 20`, `missing_citations: []`, `local_links_checked: 39`, `delivery_pending: []` — confirma a integridade documental da fase 2 (incluindo a tabela C01–C20 do fonte) na base trabalhada. Limitação anotada: o verificador é checagem documental (stdlib only) e não valida experimentalmente nada; não constitui resultado medido. As duas partes desta task são conferências de especificação, não experimentos: nada aqui é resultado medido, e nenhum orçamento/parâmetro de C17 foi definido.
- Pendências/bloqueios: **lacuna de cobertura — C10 (Gestão do contexto) sem task na família 001–008 nem menção no plano**; registrado como impedimento e elevado ao master para decisão (criar task dedicada, repartir o plano ou registrar exceção justificada), fora do escopo desta task. As seis ambiguidades do fonte permanecem decisões pendentes, nenhuma resolvida.

## Notas

### Dificuldade esperada
4/10 — A parte 1 é conferência textual simples; a parte 2 exige verificação cruzada de cobertura sobre oito tasks e as seis ambiguidades, com risco moderado de lacuna sutil de mapeamento.

### Dificuldade sentida
4/10 — A conferência textual da Parte 1 foi direta (dois bullets contra o fonte, único desvio o ponto final já previsto pelo precedente da família). A Parte 2 exigiu varredura cruzada sistemática sobre oito arquivos e o plano (regex de IDs, distribuição das seis ambiguidades, cadeia de dependências); a descoberta da lacuna de C10 — que nenhuma menção textual isolada teria revelado — elevou a dificuldade ao nível previsto (4/10) e introduziu a decisão de registro de impedimento sem ampliar escopo: não criar task, não editar tasks alheias, marcar o critério C2 como não comprovado em vez de aprová-lo por aproximação.

### Impedimento registrado (lacuna de cobertura C10)
- **C10 — Gestão do contexto** (célula da linha 16 do documento-fonte) não é especificado em nenhuma task da família 001–008 e não é mencionado no `plan.md` (a tabela do plano e a linha de cobertura do fonte omitem C10 inteiramente). A lacuna origina-se na derivação das tasks a partir do plano, não de desvio de fidelidade das especificações existentes (as 19 demais células validadas foram fiel às suas tasks).
- Conforme o Prompt desta task, não foi criada task e nenhuma task de outra sessão foi editada; o impedimento fica registrado aqui para decisão do master (por exemplo: criar task dedicada a C10, repartir o plano ou registrar exceção justificada — note-se que a seção "Dependências e prioridades" do próprio fonte também não posiciona C10 na cadeia do núcleo, o que pode explicar a omissão, mas não a elimina do critério "todos os componentes C01–C20").

### Revisão
- Orquestrador: —
- Alvo: —
- Avaliações: —
- Nota final: —
- Parecer: —
- Decisão: pendente
- Reversão: —
- Próximo passo: —

Plano: [plan.md](../../plans/02-componentes-e-requisitos/plan.md)
