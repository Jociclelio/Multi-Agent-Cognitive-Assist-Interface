# Task 004: Validar decisões de método — pedagogia e avaliação do aluno (C06 e C07/C08)

Estado: aguardando revisão
Depende de: 003
Origem: nenhuma

## Prompt
Conferir que as duas decisões abaixo reproduzem **fielmente** as linhas C06 e C07/C08 da tabela "Decisões reconciliadas" de `fase2/documentos/03_metodologias_de_implementacao.md` (documento-fonte normativo, que permanece intocado; linhas 20 e 21). Registrar em Evidências a conferência item a item de cada linha (método selecionado, referências/chaves, por quê e limite). Se encontrar desvio de fidelidade, corrija **apenas o texto desta task** em dif mínimo, preservando o sentido do fonte, e registre a correção em Evidências.

Decisões a validar (extraídas da tabela do documento-fonte):
- **C06 — Pedagogia:** skills versionadas, estados de tentativa/pista/autoexplicação/transferência *(referências/chaves: `chi1994selfexplanation`, `roediger2006testing`, `sun2025multitutor`, `wang2023voyager`)* *(por quê e limite: apoio contingente e recuperação ativa; não importar eficácia de outro domínio/população)*
- **C07/C08 — Avaliação e estado do aluno:** gabarito/rubrica antes da avaliação, verificação formal quando possível, estado observado; BKT em modo experimental *(referências/chaves: `kim2024prometheus`, `farquhar2024semanticentropy`, `badrinath2021pybkt`)* *(por quê e limite: evita transformar erro do juiz em domínio do aluno; estimador exige logs/calibração)*

Além da fidelidade, conferir que: os IDs C06, C07 e C08 são tratados como permanentes; nada acrescenta requisito, número ou métrica não presente no fonte; BKT permanece "em modo experimental", sem promoção a método confirmado; a ambiguidade 2 da etapa 2 (estados "evidência insuficiente" e "avaliável" no monitor formativo, C07) permanece pendente, não resolvida por esta decisão; a fronteira da etapa 2 (erro do juiz ≠ domínio do aluno) permanece coerente.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver a ambiguidade 2 nem promover BKT a confirmado; nada apresentado como resultado medido; IDs C01–C20 permanentes; prosa em português; commit de entrega (correção de fidelidade, se houver) e commit de registro separados, sem amend/force-push/commits vazios; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/03_metodologias_de_implementacao.md` — documento-fonte: tabela "Decisões reconciliadas", linhas C06 (linha 20) e C07/C08 (linha 21).
- `fase2/pesquisa/03b_pedagogia_memoria_planejamento.md` — relatório integral da frente de pedagogia/memória/planejamento (C06–C12), referência de embasamento, sem reabrir alternativas.
- `.agents/tasks/02-componentes-e-requisitos/003-validar-tutor-monitor-e-estado-de-aprendizagem.md` — etapa 2: características de C06, C07 e C08, incluindo a ambiguidade 2 como pendente.
- `.agents/plans/03-metodologias-de-implementacao/plan.md` — plano aprovado.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [x] C1 — As decisões de método para C06 e C07/C08 nesta task correspondem item a item às linhas 20 e 21 do fonte (método selecionado, referências/chaves e limite de cada linha); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task.
- [x] C2 — Nada acrescido além do fonte; BKT permanece experimental; a ambiguidade 2 (C07) permanece pendente, não resolvida; IDs permanentes; nada apresentado como resultado medido.
- [x] C3 — O documento-fonte permanece intocado (`git diff` vazio em relação à base); correções limitadas ao arquivo desta task em dif mínimo; commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo não tocado.

## Execução
- Modelo: GLM-5.3-Flash (provider sd2, via `~/sd2-llm.sh`)
- Base: `main` em `fd9c8ca` (`fd9c8caecf62e28380ce2ea1180f2b887a24115e`), árvore limpa; dependência 003 fechada na revisão (`fd9c8ca`)
- Entrega: sem alteração de artefatos — a conferência não encontrou desvio de fidelidade; o documento-fonte permaneceu intocado e nenhuma correção na task foi necessária. Commit único de registro.
- Arquivos da entrega: `.agents/tasks/03-metodologias-de-implementacao/004-validar-decisoes-pedagogia-avaliacao-c06-c07-c08.md` (somente este registro)
- Evidências:
  - **C1 (fidelidade item a item, linhas 20 e 21 do fonte)** — Conferência textual automatizada (script isolado em `/tmp/opencode/verif_004b.py`, extração por regex das células da tabela do fonte e dos bullets da task, comparação após normalização de aspas/travessões e de capitalização inicial):
    - **C06 (linha 20)**: método selecionado `FIEL` ("Skills versionadas, estados de tentativa/pista/autoexplicação/transferência" ✓); chaves `FIEL` e na ordem do fonte (`chi1994selfexplanation` ✓, `roediger2006testing` ✓, `sun2025multitutor` ✓, `wang2023voyager` ✓); por que e limite `FIEL` ("Apoio contingente e recuperação ativa; não importar eficácia de outro domínio/população" ✓). As sete chaves existem em `fase2/pesquisa/references_pedagogia.bib` (entradas nas linhas 15, 25, 34, 52, 79, 88, 106).
    - **C07/C08 (linha 21)**: método selecionado `FIEL` ("Gabarito/rubrica antes da avaliação, verificação formal quando possível, estado observado; BKT em modo experimental" ✓); chaves `FIEL` e na ordem do fonte (`kim2024prometheus` ✓, `farquhar2024semanticentropy` ✓, `badrinath2021pybkt` ✓); por que e limite `FIEL` ("Evita transformar erro do juiz em domínio do aluno; estimador exige logs/calibração" ✓).
    - Diferenças legítimas mantidas, sem correção: capitalização inicial minúscula nos bullets da task ("skills", "gabarito", "apoio", "evita" — posição na frase após o rótulo do bullet) e chaves sem backticks na task. Nenhum desvio de fidelidade; a primeira tentativa de script (`/tmp/opencode/verif_004.py`) falhou apenas na extração (padrões de regex sem "quê" acentuado e sem o formato `- **C06 — Pedagogia:**`), corrigida no segundo script; o resultado do teste não dependeu da falha de extração.
  - **C2 (nada acrescido; BKT experimental; ambiguidade 2 pendente; IDs permanentes; nada medido)** — Script confirma `BKT em modo experimental` presente de forma idêntica no bullet da task e na linha 21 do fonte, sem promoção a confirmado; a task cita explicitamente "linhas 20 e 21" (corretas no arquivo). A ambiguidade 2 da etapa 2 (estados "evidência insuficiente" e "avaliável" no monitor formativo, C07) aparece na task apenas como pendente ("permanece pendente, não resolvida por esta decisão"), coerente com a task da etapa 2 (`.agents/tasks/02-componentes-e-requisitos/003-validar-tutor-monitor-e-estado-de-aprendizagem.md`, onde figura como "Ambiguidade pendente 2" anexada a C07); a fronteira etapa 2 (erro do juiz ≠ domínio do aluno) reproduz literalmente o limite da linha 21. Os IDs C06, C07 e C08 são usados apenas como identificadores permanentes. Varredura dos bullets: nenhum número, métrica, orçamento ou parâmetro além do fonte; nenhuma alternativa fechada pelo fonte foi selecionada e nenhum opcional reclassificado; nenhuma frase afirma resultado medido ou verificação experimental.
  - **C3 (fonte intocado; escopo de commits)** — `git status --porcelain` vazio na base `fd9c8ca` antes da edição; o único arquivo modificado nesta execução é esta task; nenhuma alteração em `fase2/` (fonte normativo intacto), no submódulo `docs/playground-llmagenticsystem` ou em qualquer outro arquivo. Sem commit de entrega (não houve correção de fidelidade) e sem commits vazios, amend ou force-push; commit de registro separado, contendo apenas esta task.
  - **Verificador do repositório (apoio)** — `python3 fase2/scripts/verificar_documentos.py` a partir da raiz: `status: "passed"`, `components: 20`, `missing_citations: []`, `local_links_checked: 39`, `delivery_pending: []`. Limitação anotada: checagem documental (stdlib only), não constitui resultado experimental nem validação de eficácia pedagógica.

## Notas

### Dificuldade esperada
2/10 — Conferência textual de duas linhas de tabela; cuidado em manter BKT experimental e a ambiguidade 2 pendente.

### Dificuldade sentida
2/10 — Conferência textual direta de duas linhas de tabela contra os próprios bullets da task, com checagem automatizada por script isolado; a única fricção foi técnica e sem impacto no resultado (dois padrões de regex do primeiro script de extração não casaram com "por quê" acentuado e com o formato do rótulo do bullet, corrigidos em um segundo script antes de qualquer conclusão). Os critérios de julgamento já tinham precedente nas tasks 001–003: capitalização inicial e backticks são diferenças tipográficas legítimas, não desvios de fidelidade; manteve-se BKT estritamente "em modo experimental" e a ambiguidade 2 estritamente como pendente, sem nenhuma operacionalização proposta.

### Revisão
- Orquestrador: —
- Alvo: —
- Avaliações: —
- Nota final: —
- Parecer: —
- Decisão: pendente
- Reversão: —
- Próximo passo: —

Plano: [plan.md](../../plans/03-metodologias-de-implementacao/plan.md)
