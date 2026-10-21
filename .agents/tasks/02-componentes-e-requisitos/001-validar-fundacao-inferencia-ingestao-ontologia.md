# Task 001: Validar especificação dos componentes fundação — C01, C02 e C03

Estado: pendente
Depende de: nenhuma
Origem: nenhuma

## Prompt
Conferir que a especificação abaixo dos componentes C01–C03 reproduz **fielmente** as características exigidas e os critérios verificáveis de `fase2/documentos/02_componentes_e_requisitos.md` (documento-fonte normativo, que permanece intocado). Registrar em Evidências a conferência item a item contra o fonte. Se encontrar desvio de fidelidade entre esta especificação e o fonte, corrija **apenas o texto desta task** em dif mínimo, preservando o sentido do fonte, e registre a correção em Evidências.

Especificação a validar (extraída da tabela do documento-fonte):
- **C01 — Inferência local:** artefato Bonsai 2 identificável, licença, revisão/hash, runtime, quantização, tokenizer, janela e suporte a JSON; execução offline; um servidor compartilhado com fila limitada; benchmark de português e ferramentas antes da adoção. *(Ambiguidade pendente 1: Bonsai 2 é nomeado sem identificador, precisão ou hardware — não se pode derivar qualidade e latência dessa designação; a escolha do artefato exige decisão externa.)*
- **C02 — Ingestão e proveniência:** PDF/texto, página/seção, hash, versão, ordem, diagnóstico de OCR e tabelas; nenhum prazo promovido sem origem; material ilegível resulta em pendência explícita.
- **C03 — Ontologia acadêmica:** disciplina/tópico/pré-requisito/avaliação/recurso com IDs; datas com timezone e confiança; autoridade do PDD confirmado superior a sugestões; conflitos rastreáveis. *(Ambiguidade pendente 4 relacionada: documento externo mais recente não substitui automaticamente prazo confirmado; mudanças exigem reconciliação.)*

Além da fidelidade, conferir que: os IDs são tratados como permanentes e estáveis (referências futuras citam IDs, não nomes alternativos); nada nesta especificação acrescenta requisito, número ou métrica não presente no fonte; os componentes aparecem na posição correta da cadeia do núcleo (C01 → C02/C03).

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver as ambiguidades — apenas registrá-las como pendentes; não apresentar especificação como resultado medido; prosa em português; commits de registro em português, sem amend/force-push.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e ambiguidades; fonte normativo da conferência.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; seções "Abordagem", "Escopo" e "Critérios de conclusão" definem o esperado.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — mapa normativo de implementação, apoio para checar alinhamento de terminologia, sem importar conteúdo.
- `AGENTS.md` (raiz) — convenções do repositório (não apresentar propostas como resultados medidos).

## Corretude
- [ ] C1 — As características exigidas e critérios verificáveis de C01, C02 e C03 nesta task correspondem item a item ao documento-fonte (tabela da seção de componentes); conferência registrada em Evidências.
- [ ] C2 — Os IDs C01–C03 são tratados como permanentes/estáveis e as ambiguidades 1 e 4 aparecem apenas como decisões pendentes, sem resolução arbitrária.
- [ ] C3 — Nenhum requisito, número ou métrica foi acrescido além do fonte; nenhuma formulação apresenta especificação como resultado medido.
- [ ] C4 — O documento-fonte `fase2/documentos/02_componentes_e_requisitos.md` permanece intocado (`git diff` vazio para ele em relação à base); correções, se houver, limitam-se ao arquivo desta task em dif mínimo.
- [ ] C5 — Commit de registro com evidências separado de qualquer commit de entrega; sem commits vazios, amend ou force-push.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
2/10 — Conferência textual de três linhas de tabela contra o próprio documento-fonte; risco baixo, exigindo apenas disciplina de não parafrasear além do fonte.

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
