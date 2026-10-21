# Task 009: Completar cobertura de C10 (Gestão do contexto) e ajustar evidências da consolidação

Estado: pendente
Depende de: 008
Origem: task 008 — correção (decisão de revisão "corrigir": lacuna de cobertura C10, achado convergente dos três revisores, e imprecisões de evidência F2/F3 da MiMo)

## Prompt
Duas partes:

**Parte 1 — Especificação de C10.** Conferir que a especificação abaixo reproduz **fielmente** a célula C10 da tabela de `fase2/documentos/02_componentes_e_requisitos.md` (documento-fonte normativo, que permanece intocado; célula na linha 16):
- **C10 — Gestão do contexto:** medir tokens com tokenizer real, reservar saída e ferramentas; recuperar antes de resumir; sumarização com checagem de fatos críticos; preservar prazos e evidências; medir perda de informação.

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
- [ ] C1 — A especificação de C10 nesta task corresponde item a item à célula da linha 16 do fonte (medir tokens com tokenizer real; reservar saída e ferramentas; recuperar antes de resumir; sumarização com checagem de fatos críticos; preservar prazos e evidências; medir perda de informação); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task.
- [ ] C2 — Cobertura C01–C20 completa comprovada: lista explícita em Evidências com os 20 componentes mapeados a tasks (incluindo C10 → task 009); as duas frases de evidência da task 008 ajustadas em difs mínimos limitados a elas, sem tocar nenhum outro trecho de 008.
- [ ] C3 — Pendência de posicionamento de C10 registrada conforme o fonte: a cadeia do núcleo não é alterada, C10 não é reclassificado como opcional nem inserido arbitrariamente na cadeia, e nenhuma ambiguidade é resolvida.
- [ ] C4 — Documento-fonte intocado (`git diff` vazio para ele em relação à base); commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo `docs/playground-llmagenticsystem` não tocado.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
3/10 — A Parte 1 é conferência textual de uma célula; a Parte 2 exige atualizar a consolidação com difs mínimos e precisos em outra task (008), sem tocar trechos além das duas frases indicadas.

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

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
