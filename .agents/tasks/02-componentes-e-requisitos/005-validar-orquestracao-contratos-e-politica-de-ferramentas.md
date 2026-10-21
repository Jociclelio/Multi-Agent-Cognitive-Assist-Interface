# Task 005: Validar especificação da camada transversal I — orquestração, contratos e política de ferramentas — C13, C14 e C15

Estado: pendente
Depende de: 004
Origem: nenhuma

## Prompt
Conferir que a especificação abaixo dos componentes C13–C15 reproduz **fielmente** as características exigidas e os critérios verificáveis de `fase2/documentos/02_componentes_e_requisitos.md` (documento-fonte normativo, que permanece intocado). Registrar em Evidências a conferência item a item. Desvio de fidelidade: corrija apenas o texto desta task em dif mínimo e registre em Evidências.

Especificação a validar (extraída da tabela do documento-fonte):
- **C13 — Orquestração:** LangGraph com rotas fixas, checkpoints, pausa humana, dependências e terminais; ausência de ciclos não limitados; política para divergências; mesmas ferramentas no baseline.
- **C14 — Comunicação e contratos:** JSON Schema/Pydantic, envelope com task/trace/version, referência em vez de cópia integral, leitura de snapshot; erros tipados; MCP nas fronteiras de ferramentas; A2A somente como extensão de serviços. *(Ambiguidade pendente 5: A2A não é requisito para comunicação interna — acrescentar serviços remotos ao MVP ampliaria os pontos de falha sem benefício demonstrado.)*
- **C15 — Política de ferramentas:** allowlist por papel, argumentos validados, tool result como dados, rede opcional, escrita mediada; JSON correto não basta: validar também intenção e efeito.

Além da fidelidade, conferir que: os IDs são permanentes/estáveis; nada acrescenta requisito, número ou métrica além do fonte; C13–C17/C20 estão registrados como camada que **sustenta o núcleo desde o início** (não como fase posterior); a ambiguidade 5 aparece apenas como decisão pendente.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver ambiguidades; prosa em português; commit de registro separado, sem amend/force-push/commits vazios.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e ambiguidades.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; "Abordagem" (camada transversal sustentando o núcleo desde o início) e "Critérios de conclusão".
- `fase2/documentos/04_mapa_completo_do_sistema.md` — apoio para checar alinhamento de terminologia (orquestrador, contratos verificáveis, validação determinística), sem importar conteúdo.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [ ] C1 — Características e critérios de C13, C14 e C15 correspondem item a item ao documento-fonte; conferência registrada em Evidências.
- [ ] C2 — IDs permanentes/estáveis; ambiguidade 5 (A2A fora do MVP) registrada apenas como decisão pendente; C13–C15 caracterizados como sustentação do núcleo desde o início.
- [ ] C3 — Nenhum requisito, número ou métrica além do fonte; nada apresentado como resultado medido.
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
2/10 — Conferência textual de três linhas de tabela; risco baixo.

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
