# Task 003: Validar especificação de tutor, monitor formativo e estado de aprendizagem — C06, C07 e C08

Estado: pendente
Depende de: 002
Origem: nenhuma

## Prompt
Conferir que a especificação abaixo dos componentes C06–C08 reproduz **fielmente** as características exigidas e os critérios verificáveis de `fase2/documentos/02_componentes_e_requisitos.md` (documento-fonte normativo, que permanece intocado). Registrar em Evidências a conferência item a item. Desvio de fidelidade: corrija apenas o texto desta task em dif mínimo e registre em Evidências.

Especificação a validar (extraída da tabela do documento-fonte):
- **C06 — Tutor e skills:** socrático, explicação e prática graduada; habilidades versionadas para explicar, pistas, quiz, flashcards, autoexplicação; pré/pós-condições; resposta direta quando apropriada; não interrogar indefinidamente
- **C07 — Monitor formativo:** gabarito ou rubrica explícita, evidência de resposta, erros por tópico, incerteza e opção de abster; separar corretude, ajuda recebida e domínio; validação contra anotação humana *(Ambiguidade pendente 2: um único episódio correto não basta para estimar domínio — o monitor precisa dos estados "evidência insuficiente" e "avaliável"; como operacionalizá-los ainda não está definido.)*
- **C08 — Estado de aprendizagem:** modelo atualizável e auditável por tópico, distinção entre observado e inferido; cold-start; revisão temporal; evitar parâmetros cognitivos arbitrários tratados como calibrados

Além da fidelidade, conferir que: os IDs são permanentes/estáveis; nada acrescenta requisito, número ou métrica além do fonte; C06/C07/C08 ocupam a posição correta da cadeia do núcleo (C01 → C02/C03 → C04/C09 → **C06/C07/C08** → C11); a ambiguidade 2 aparece apenas como decisão pendente.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver ambiguidades; não apresentar especificação como resultado medido; prosa em português; commit de registro separado, sem amend/force-push/commits vazios.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e ambiguidades.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; "Abordagem" (cadeia do núcleo) e "Critérios de conclusão".
- `fase2/documentos/04_mapa_completo_do_sistema.md` — apoio para checar alinhamento de terminologia (tutor, monitor, estado), sem importar conteúdo.
- `fase2/documentos/08_mapa_completo_da_testagem.md` — referência de avaliação (validação contra anotação humana em C07), sem importar conteúdo.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [ ] C1 — Características e critérios de C06, C07 e C08 correspondem item a item ao documento-fonte; conferência registrada em Evidências.
- [ ] C2 — IDs permanentes/estáveis; ambiguidade 2 ("evidência insuficiente"/"avaliável") registrada apenas como decisão pendente, sem proposta de operacionalização nesta etapa.
- [ ] C3 — Nenhum requisito, número ou métrica além do fonte; posição de C06–C08 na cadeia do núcleo registrada corretamente; nada apresentado como resultado medido.
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
