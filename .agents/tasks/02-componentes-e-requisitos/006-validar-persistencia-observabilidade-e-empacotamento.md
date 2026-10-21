# Task 006: Validar especificação da camada transversal II — persistência, observabilidade e empacotamento — C16, C17 e C20

Estado: pendente
Depende de: 005
Origem: nenhuma

## Prompt
Conferir que a especificação abaixo dos componentes C16, C17 e C20 reproduz **fielmente** as características exigidas e os critérios verificáveis de `fase2/documentos/02_componentes_e_requisitos.md` (documento-fonte normativo, que permanece intocado). Registrar em Evidências a conferência item a item. Desvio de fidelidade: corrija apenas o texto desta task em dif mínimo e registre em Evidências.

Especificação a validar (extraída da tabela do documento-fonte):
- **C16 — Persistência e recuperação:** transações, outbox, controle otimista de versão, migrações, backup, retomada e deduplicação; teste de crash antes/depois de efeitos
- **C17 — Observabilidade e limites:** trace por turno, tokens, tempo, RSS/VRAM, hashes de modelo/prompt, solver status; orçamento de chamadas, tempo e reparos; cancelamento e resposta controlada *(Questão aberta do plano: as definições dos orçamentos de C17 não constam do documento-fonte e não devem ser inventadas nesta etapa.)*
- **C20 — Empacotamento e execução:** manifesto/lock de versões e hashes, configuração documentada, instalação offline possível, smoke test e CLI; hardware real registrado; extensões não obrigatórias para fechar o núcleo

Além da fidelidade, conferir que: os IDs são permanentes/estáveis; nada acrescenta requisito, número ou métrica além do fonte (em especial, nenhum valor de orçamento para C17); C16/C17/C20 estão registrados como camada que sustenta o núcleo desde o início.

Restrições: não alterar o documento-fonte nem criar documento novo; não definir orçamentos nem inventar parâmetros; prosa em português; commit de registro separado, sem amend/force-push/commits vazios.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e ambiguidades.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; "Abordagem" (camada transversal) e "Questões abertas" (item 4: orçamentos de C17 não constam do documento).
- `fase2/documentos/04_mapa_completo_do_sistema.md` — apoio para checar alinhamento de terminologia, sem importar conteúdo.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [ ] C1 — Características e critérios de C16, C17 e C20 correspondem item a item ao documento-fonte; conferência registrada em Evidências.
- [ ] C2 — IDs permanentes/estáveis; nenhum valor de orçamento (chamadas, tempo, reparos) ou outro parâmetro inventado para C17; a ausência de definições registrada como questão aberta.
- [ ] C3 — Nenhum requisito, número ou métrica além do fonte; C16/C17/C20 caracterizados como sustentação do núcleo desde o início.
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
2/10 — Conferência textual de três linhas de tabela; risco baixo, com atenção para não inventar orçamentos de C17.

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
