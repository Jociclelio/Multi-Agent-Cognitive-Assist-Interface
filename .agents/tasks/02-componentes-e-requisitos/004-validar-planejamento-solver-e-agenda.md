# Task 004: Validar especificação de planejamento/solver e agenda — C11 e C12

Estado: pendente
Depende de: 003
Origem: nenhuma

## Prompt
Conferir que a especificação abaixo dos componentes C11 e C12 reproduz **fielmente** as características exigidas e os critérios verificáveis de `fase2/documentos/02_componentes_e_requisitos.md` (documento-fonte normativo, que permanece intocado). Registrar em Evidências a conferência item a item. Desvio de fidelidade: corrija apenas o texto desta task em dif mínimo e registre em Evidências.

Especificação a validar (extraída da tabela do documento-fonte):
- **C11 — Planejamento e solver:** slots, timezone, prazos, disponibilidade, compromissos imutáveis, duração e prioridade; solver verificável; mínimo de alterações no replanejamento; distinguir inviável de timeout. *(Ambiguidades pendentes 3 e 4 relacionadas: tempo insuficiente não deve ser resolvido silenciosamente removendo compromissos ou reduzindo duração obrigatória; documento externo mais recente não substitui automaticamente prazo confirmado — reconciliação.)*
- **C12 — Exportação e agenda:** ICS válido, UID estável, timezone, preview e confirmação; integração MCP opcional; idempotência, concorrência, reconciliação após timeout e nenhuma duplicação em retry. *(Nota de prioridade do fonte: o ICS local de C12 é obrigatório no núcleo; a sincronização remota de C12 é conector opcional avaliado separadamente — especificada na task 008.)*

Além da fidelidade, conferir que: os IDs são permanentes/estáveis; nada acrescenta requisito, número ou métrica além do fonte; C11 ocupa o fim da cadeia do núcleo (C01 → C02/C03 → C04/C09 → C06/C07/C08 → **C11**); as ambiguidades 3 e 4 aparecem apenas como decisões pendentes.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver ambiguidades; prosa em português; commit de registro separado, sem amend/force-push/commits vazios.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e ambiguidades.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; "Abordagem" (cadeia do núcleo, ICS local obrigatório) e "Critérios de conclusão".
- `fase2/documentos/04_mapa_completo_do_sistema.md` — apoio para checar alinhamento de terminologia (solver, planejador de rotina), sem importar conteúdo.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [ ] C1 — Características e critérios de C11 e C12 correspondem item a item ao documento-fonte; conferência registrada em Evidências.
- [ ] C2 — IDs permanentes/estáveis; ambiguidades 3 e 4 registradas apenas como decisões pendentes; ICS local marcado como obrigatório no núcleo e sincronização remota de C12 marcada como opcional (remetida à task 008).
- [ ] C3 — Nenhum requisito, número ou métrica além do fonte; posição de C11 na cadeia do núcleo registrada corretamente.
- [ ] C4 — Documento-fonte intocado (`git diff` vazio para ele em relação à base); correções limitadas ao arquivo desta task em dif mínimo.
- [ ] C5 — Commit de registro com evidências separado de qualquer commit de entrega; sem commits vazios, amend ou force-push.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
2/10 — Conferência textual de duas linhas de tabela; risco baixo, com atenção à fronteira núcleo/opcional de C12.

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
