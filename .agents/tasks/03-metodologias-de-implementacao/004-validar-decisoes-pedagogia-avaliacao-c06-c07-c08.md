# Task 004: Validar decisões de método — pedagogia e avaliação do aluno (C06 e C07/C08)

Estado: pendente
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
- [ ] C1 — As decisões de método para C06 e C07/C08 nesta task correspondem item a item às linhas 20 e 21 do fonte (método selecionado, referências/chaves e limite de cada linha); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task.
- [ ] C2 — Nada acrescido além do fonte; BKT permanece experimental; a ambiguidade 2 (C07) permanece pendente, não resolvida; IDs permanentes; nada apresentado como resultado medido.
- [ ] C3 — O documento-fonte permanece intocado (`git diff` vazio em relação à base); correções limitadas ao arquivo desta task em dif mínimo; commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo não tocado.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
2/10 — Conferência textual de duas linhas de tabela; cuidado em manter BKT experimental e a ambiguidade 2 pendente.

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

Plano: [plan.md](../../plans/03-metodologias-de-implementacao/plan.md)
