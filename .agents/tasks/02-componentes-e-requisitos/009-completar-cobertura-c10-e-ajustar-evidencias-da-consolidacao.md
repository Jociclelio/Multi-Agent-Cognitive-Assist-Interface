# Task 009: Completar cobertura de C10 (Gestão do contexto) e ajustar evidências da consolidação

Estado: aguardando revisão
Depende de: 008
Origem: task 008 — correção (decisão de revisão "corrigir": lacuna de cobertura C10, achado convergente dos três revisores, e imprecisões de evidência F2/F3 da MiMo)

## Prompt
Duas partes:

**Parte 1 — Especificação de C10.** Conferir que a especificação abaixo reproduz **fielmente** a célula C10 da tabela de `fase2/documentos/02_componentes_e_requisitos.md` (documento-fonte normativo, que permanece intocado; célula na linha 16):
- **C10 — Gestão do contexto:** medir tokens com tokenizer real, reservar saída e ferramentas; recuperar antes de resumir; sumarização com checagem de fatos críticos; preservar prazos e evidências; medir perda de informação

**Parte 2 — Consolidação da cobertura e ajustes de evidência.** Com C10 registrado nesta task, registrar em Evidências a lista explícita completa componente → task (20/20), incluindo C10 → task 009 (esta), complementando a lista 19/20 da task 008. Registrar ainda que a seção "Dependências e prioridades" do fonte não posiciona C10 na cadeia do núcleo — como **pendência de posicionamento** (não decidir onde C10 entra; não reclassificá-lo como opcional; o ID C10 é permanente e o componente integra o conjunto C01–C20). Corrigir na task 008, em **difs mínimos limitados a duas frases**, as imprecisões de evidência apontadas pela revisão:
- (i) na Evidência C2 da task 008, a frase "não aparece em nenhuma task da família (001–008) nem no `plan.md`" deve ser reformulada para refletir o que a varredura constatou no momento da consolidação: ausência de especificação e de menção nas tasks 001–007 e no plano, sendo a menção na própria 008 o registro do impedimento (a evidência não pode afirmar algo que não reproduz no histórico);
- (ii) na Evidência C4 da task 008, a frase "Distribuição confirmada por varredura nos oito arquivos" deve ser ajustada para atribuir à varredura automatizada apenas o que ela confirmou (ambiguidades 1, 2, 3 e 5) e à conferência manual o restante (ambiguidades 4 e 6, cujo padrão do script não capturou integralmente).

Desvio de fidelidade na Parte 1: corrija apenas o texto desta task em dif mínimo e registre em Evidências. Na task 008, altere somente as duas frases indicadas — nenhum outro trecho de 008 (contrato, execução, revisão, notas) pode ser modificado.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver ambiguidades nem a pendência de posicionamento de C10; não apresentar especificação como resultado medido; não inventar orçamentos/parâmetros; IDs C01–C20 permanentes; prosa em português; commit de entrega (correções de fidelidade, se houver) e commit de registro separados, sem amend/force-push/commits vazios.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: célula C10 (linha 16) e seção "Dependências e prioridades" (linha 30, que omite C10 da cadeia).
- `.agents/tasks/02-componentes-e-requisitos/008-validar-opcionais-e-consolidar-cobertura-c01-c20.md` — task de origem: seção Revisão com a decisão "corrigir", impedimento C10 e as duas frases de evidência a ajustar.
- `.agents/tasks/02-componentes-e-requisitos/` — tasks 001–008, objeto da consolidação de cobertura.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; "Critérios de conclusão" exige cada componente C01–C20 representado nas tasks.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [x] C1 — A especificação de C10 nesta task corresponde item a item à célula da linha 16 do fonte (medir tokens com tokenizer real; reservar saída e ferramentas; recuperar antes de resumir; sumarização com checagem de fatos críticos; preservar prazos e evidências; medir perda de informação); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task.
- [x] C2 — Cobertura C01–C20 completa comprovada: lista explícita em Evidências com os 20 componentes mapeados a tasks (incluindo C10 → task 009); as duas frases de evidência da task 008 ajustadas em difs mínimos limitados a elas, sem tocar nenhum outro trecho de 008.
- [x] C3 — Pendência de posicionamento de C10 registrada conforme o fonte: a cadeia do núcleo não é alterada, C10 não é reclassificado como opcional nem inserido arbitrariamente na cadeia, e nenhuma ambiguidade é resolvida.
- [x] C4 — Documento-fonte intocado (`git diff` vazio para ele em relação à base); commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo `docs/playground-llmagenticsystem` não tocado.

## Execução
- Modelo: GLM-5.3-Flash (via ~/sd2-llm.sh; provider sd2, model GLM-5.3-Flash)
- Base: `e1f39b425c7980e84f35f8dbcc51cc4932093079` (HEAD, árvore limpa)
- Entrega: `8bf5c30de72b4a471ee7272bf5f1ad031e23b5f5` (correção de fidelidade no bullet C10 desta task + ajuste das duas frases de evidência na task 008; commit de registro separado, sem SHA próprio neste arquivo)
- Arquivos da entrega: `.agents/tasks/02-componentes-e-requisitos/009-completar-cobertura-c10-e-ajustar-evidencias-da-consolidacao.md` (remoção do ponto final do bullet C10, 1 caractere) e `.agents/tasks/02-componentes-e-requisitos/008-validar-opcionais-e-consolidar-cobertura-c01-c20.md` (duas linhas alteradas — exatamente as duas frases indicadas; nenhum outro trecho de 008, nenhum terceiro arquivo)
- Evidências:
  - **C1 (fidelidade item a item, célula C10 da linha 16 do fonte)** — Conferência textual automatizada (script isolado em `/tmp/opencode/check_009.py`, extração por regex da célula C10 do fonte e do bullet da especificação desta task, comparação após normalização NFC/minúsculas/espaços). Antes da correção, o único desvio era tipográfico — ponto final acrescido ao final da célula copiada (o fonte não pontua as células), mesmo desvio já corrigido nas tasks 001–008; nenhum termo, critério ou cláusula divergia. Item a item: C10 = medir tokens com tokenizer real ✓, reservar saída e ferramentas ✓, recuperar antes de resumir ✓, sumarização com checagem de fatos críticos ✓, preservar prazos e evidências ✓, medir perda de informação ✓. Após a remoção do ponto final (commit de entrega `8bf5c30`, dif de 1 caractere): `iguais normalizados: True` (C10 FIEL). Diferença legítima mantida: inicial minúscula em "medir" na task (posição na frase, como "artefato" na task 001 e "busca" na task 008).
  - **C2 (cobertura C01–C20 completa, 20/20)** — Lista explícita componente → task, complementando a lista 19/20 da task 008: C01, C02, C03 → task 001; C04, C09 → task 002; C06, C07, C08 → task 003; C11, C12 (ICS local) → task 004; C13, C14, C15 → task 005; C16, C17, C20 → task 006; C18, C19 → task 007; C05 e sincronização remota de C12 → task 008; **C10 — Gestão do contexto → task 009 (esta)**. Varredura automatizada de confirmação (script `/tmp/opencode/coverage_009.py`, regex `\bC\d\d\b` por arquivo mapeado): os 20 IDs distintos têm ao menos uma menção na task correspondente (`Distintos cobertos: 20 / 20; ok = True`; C10 → 18 menções na task 009) e C10 consta do `plan.md`. Ajustes na task 008, ambos no commit de entrega `8bf5c30` e limitados às duas frases indicadas: (i) Evidência C2 — "não aparece em nenhuma task da família (001–008) nem no `plan.md`" reformulada para "não tinha especificação nem menção nas tasks 001–007 nem no `plan.md` no momento da consolidação; a menção na própria 008 é o registro do impedimento", reproduzindo o que a varredura constatou no momento da consolidação; (ii) Evidência C4 — "Distribuição confirmada por varredura nos oito arquivos" ajustada para "Distribuição confirmada por varredura automatizada nos oito arquivos (ambiguidades 1, 2, 3 e 5), completada por conferência manual para as ambiguidades 4 e 6, cujo padrão do script não capturou integralmente", atribuindo a cada método apenas o que ele confirmou. `git diff` da entrega na 008: exatamente 2 linhas (as duas frases); contrato, execução, revisão e notas de 008 intocados.
  - **C3 (pendência de posicionamento de C10, sem decisão)** — Conferência automatizada da seção "Dependências e prioridades" do fonte (linha 30): `C10 em Dependências e prioridades? False` — o fonte não posiciona C10 na cadeia do núcleo (cadeia presente e idêntica: "C01 → C02/C03 → C04/C09 → C06/C07/C08 → C11", sustentada por C13–C17/C20, com C18/C19 antes da otimização e C05/sincronização remota de C12 opcionais). Registrado como **pendência de posicionamento**: C10 não foi inserido arbitrariamente na cadeia, não foi reclassificado como opcional, o ID C10 permanece permanente e o componente integra o conjunto C01–C20 (o `plan.md`, já atualizado pelo master na linha de cobertura, registra a mesma pendência). Nenhuma das seis ambiguidades do fonte foi resolvida nesta task.
  - **C4 (fonte intocado; commits separados)** — `git diff e1f39b4 -- fase2/documentos/02_componentes_e_requisitos.md`: vazio (0 linhas); `git diff --stat` da entrega: somente os dois arquivos de task (3 inserções/3 remoções no total). Nenhum documento novo criado; `docs/playground-llmagenticsystem` (submódulo) não tocado. Commit de entrega `8bf5c30` separado do commit de registro; sem amend, force-push ou commits vazios (histórico linear verificado).
  - **Verificador do repositório (apoio)** — `python3 fase2/scripts/verificar_documentos.py` a partir da raiz: `status: "passed"`, `components: 20`, `missing_citations: []`, `local_links_checked: 39`, `delivery_pending: []`. Limitação anotada: o verificador é checagem documental (stdlib only) e não valida experimentalmente nada; não constitui resultado medido. As duas partes desta task são conferências de especificação, não experimentos: nada aqui é resultado medido, e nenhum orçamento/parâmetro de C17 foi definido.
- Pendências/bloqueios: **pendência de posicionamento de C10** — a seção "Dependências e prioridades" do fonte não o posiciona na cadeia do núcleo; a decisão de onde C10 entra é do master, fora do escopo desta task (não decidida, não reclassificada). A atualização do campo Estado e do critério C2 da task 008 (ainda marcados para a iteração anterior) está fora do escopo autorizado desta task (somente as duas frases de evidência podiam ser alteradas em 008) e cabe ao master/revisão. As seis ambiguidades do fonte permanecem decisões pendentes, nenhuma resolvida.

## Notas

### Dificuldade esperada
3/10 — A Parte 1 é conferência textual de uma célula; a Parte 2 exige atualizar a consolidação com difs mínimos e precisos em outra task (008), sem tocar trechos além das duas frases indicadas.

### Dificuldade sentida
3/10 — A Parte 1 foi conferência textual direta de uma célula (único desvio, o ponto final já previsto pelo precedente da família). A Parte 2 exigiu reconstruir a lista de cobertura 20/20 com varredura automatizada por arquivo mapeado e editar outra task (008) sob restrição estrita de tocar somente duas frases, o que demandou conferência linha a linha do diff; nenhuma ambiguidade foi resolvida e a pendência de posicionamento de C10 foi apenas registrada, conforme o contrato.

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
