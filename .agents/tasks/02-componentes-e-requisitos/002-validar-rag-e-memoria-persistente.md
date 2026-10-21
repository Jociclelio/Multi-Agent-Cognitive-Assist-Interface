# Task 002: Validar especificação de RAG documental e memória persistente — C04 e C09

Estado: pendente
Depende de: 001
Origem: nenhuma

## Prompt
Conferir que a especificação abaixo dos componentes C04 e C09 reproduz **fielmente** as características exigidas e os critérios verificáveis de `fase2/documentos/02_componentes_e_requisitos.md` (documento-fonte normativo, que permanece intocado). Registrar em Evidências a conferência item a item contra o fonte. Desvio de fidelidade: corrija apenas o texto desta task em dif mínimo e registre em Evidências.

Especificação a validar (extraída da tabela do documento-fonte):
- **C04 — RAG documental:** busca lexical e semântica local, filtros por disciplina/versão, reranking, budget e abstinência; citações resolvíveis para documento e página; medição de recall e sustentação.
- **C09 — Memória persistente:** eventos originais imutáveis, perfil corrigível, estado derivado versionado e sínteses com IDs de origem; recuperação temporal; correção, exclusão e isolamento por usuário.

Além da fidelidade, conferir que: os IDs são permanentes/estáveis; nada acrescenta requisito, número ou métrica além do fonte; C04 e C09 ocupam a posição correta da cadeia do núcleo (C01 → C02/C03 → **C04/C09** → C06/C07/C08 → C11); "medição de recall" em C04 é registrada como critério verificável de avaliação futura, não como resultado medido.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver ambiguidades; prosa em português; commit de registro separado, sem amend/force-push/commits vazios.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e ambiguidades.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; "Abordagem" (cadeia do núcleo) e "Critérios de conclusão".
- `fase2/documentos/08_mapa_completo_da_testagem.md` — referência de avaliação para critérios verificáveis de C04 (recall/sustentação), sem importar conteúdo.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [ ] C1 — Características e critérios de C04 e C09 correspondem item a item ao documento-fonte; conferência registrada em Evidências.
- [ ] C2 — IDs permanentes/estáveis; "medição de recall" apresentada exclusivamente como critério verificável de avaliação futura, nunca como resultado medido.
- [ ] C3 — Nenhum requisito, número ou métrica além do fonte; posição de C04/C09 na cadeia do núcleo registrada corretamente.
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
2/10 — Conferência textual de duas linhas de tabela; risco baixo, com atenção apenas ao enquadramento de "medição de recall" como critério e não como resultado.

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
