# Task 007: Validar especificação de dados e avaliação experimental — C18 e C19

Estado: pendente
Depende de: 006
Origem: nenhuma

## Prompt
Conferir que a especificação abaixo dos componentes C18 e C19 reproduz **fielmente** as características exigidas e os critérios verificáveis de `fase2/documentos/02_componentes_e_requisitos.md` (documento-fonte normativo, que permanece intocado). Registrar em Evidências a conferência item a item. Desvio de fidelidade: corrija apenas o texto desta task em dif mínimo e registre em Evidências.

Especificação a validar (extraída da tabela do documento-fonte):
- **C18 — Dados de avaliação:** corpus autorizado, casos com ouro de fontes, tópicos, respostas e agenda; trajetórias longitudinais; splits por famílias de documentos; prevenir contaminação e registrar anotação
- **C19 — Avaliação experimental:** comparação pareada com agente único, orçamento controlado, ablações, métricas por saída/falha, oráculos independentes, IC e análise de custo; juízes humanos e LLM calibrados

Além da fidelidade, conferir que: os IDs são permanentes/estáveis; nada acrescenta requisito, número ou métrica além do fonte; C18/C19 estão registrados conforme a prioridade do fonte — **devem começar antes da otimização** para impedir que o conjunto de teste oriente escolhas; "comparação pareada com agente único" é registrada como desenho experimental futuro, não como resultado obtido (a hipótese da etapa 1 permanece condicionada a essa avaliação futura).

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver ambiguidades (inclui a ambiguidade 6: toda recomendação de pesquisa deve declarar hipótese, alternativa, custo, limitação e teste de seleção — registrar como pendência, não aplicá-la); prosa em português; commit de registro separado, sem amend/force-push/commits vazios.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e ambiguidades.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; "Abordagem" (C18/C19 antes da otimização) e "Escopo" (especificação ≠ resultado).
- `fase2/documentos/08_mapa_completo_da_testagem.md` — mapa normativo de avaliação, referência para C18/C19, sem importar conteúdo.
- `fase2/documentos/01_esqueleto_conceitual.md` — hipótese da etapa 1, que permanece condicionada à comparação pareada futura.
- `AGENTS.md` (raiz) — convenções do repositório (não apresentar propostas como resultados medidos).

## Corretude
- [ ] C1 — Características e critérios de C18 e C19 correspondem item a item ao documento-fonte; conferência registrada em Evidências.
- [ ] C2 — IDs permanentes/estáveis; prioridade "C18/C19 antes da otimização" registrada conforme o fonte; ambiguidade 6 mantida como pendência, sem aplicação ou resolução.
- [ ] C3 — Nenhum requisito, número ou métrica além do fonte; a comparação pareada aparece exclusivamente como desenho experimental futuro, nunca como resultado obtido.
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
2/10 — Conferência textual de duas linhas de tabela; risco baixo, com atenção ao enquadramento "desenho futuro ≠ resultado".

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
