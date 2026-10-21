# Task 007: Validar especificação de dados e avaliação experimental — C18 e C19

Estado: aguardando revisão
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
- [x] C1 — Características e critérios de C18 e C19 correspondem item a item ao documento-fonte; conferência registrada em Evidências.
- [x] C2 — IDs permanentes/estáveis; prioridade "C18/C19 antes da otimização" registrada conforme o fonte; ambiguidade 6 mantida como pendência, sem aplicação ou resolução.
- [x] C3 — Nenhum requisito, número ou métrica além do fonte; a comparação pareada aparece exclusivamente como desenho experimental futuro, nunca como resultado obtido.
- [x] C4 — Documento-fonte intocado (`git diff` vazio para ele em relação à base); correções limitadas ao arquivo desta task em dif mínimo.
- [x] C5 — Commit de registro com evidências separado de qualquer commit de entrega; sem commits vazios, amend ou force-push.

## Execução
- Modelo: GLM-5.3-Flash (via ~/sd2-llm.sh; provider sd2, model GLM-5.3-Flash)
- Base: `aca357645b9f2832b0184daaa736fd77ddfdd305` (árvore limpa)
- Entrega: `3d0b787614e55295f658993293dbba36b2bb7a12` (commit de entrega; commit de registro separado, sem SHA próprio neste arquivo)
- Arquivos da entrega: `.agents/tasks/02-componentes-e-requisitos/007-validar-dados-e-avaliacao-experimental.md` (3 linhas: remoção do ponto final acrescido nas células C18 e C19 e da vírgula acrescida após "**devem começar antes da otimização**" no parágrafo de prioridade — o fonte pontua "antes da otimização para impedir..."; nenhum outro arquivo alterado)
- Evidências:
  - **C1 (fidelidade item a item, células C18/C19 da tabela do fonte)** — Conferência textual automatizada (script isolado em `/tmp/opencode/check_007.py`, extração por regex das células da tabela do fonte e dos bullets da especificação da task, comparação após normalização NFC/aspas/travessões/espaços/minúsculas) das células C18 (linha 24) e C19 (linha 25) de `fase2/documentos/02_componentes_e_requisitos.md`: resultado `C18 FIEL`, `C19 FIEL` após a correção descrita acima. Antes da correção, os únicos desvios eram tipográficos: ponto final acrescido ao final de cada célula copiada (o fonte não pontua as células), mesmo desvio corrigido nas tasks 001–006; nenhum termo, critério ou cláusula divergia e a cobertura termo a termo era completa já antes. Item a item: C18 = corpus autorizado ✓, casos com ouro de fontes ✓, tópicos ✓, respostas e agenda ✓, trajetórias longitudinais ✓, splits por famílias de documentos ✓, prevenir contaminação ✓, registrar anotação ✓; C19 = comparação pareada com agente único ✓, orçamento controlado ✓, ablações ✓, métricas por saída/falha ✓, oráculos independentes ✓, IC e análise de custo ✓, juízes humanos e LLM calibrados ✓. Diferenças legítimas mantidas: inicial minúscula em "corpus" e "comparação" na task (posição na frase, como "transações" na task 006).
  - **C2 (IDs permanentes/estáveis; prioridade conforme o fonte; ambiguidade 6 pendente)** — O fonte declara na abertura (linha 3): "Os IDs abaixo são permanentes e ligam pesquisa, arquitetura e testes"; a task referencia os componentes apenas pelos IDs C18/C19 com seus nomes canônicos do fonte ("Dados de avaliação", "Avaliação experimental"), sem nome alternativo. A prioridade reproduz a seção "Dependências e prioridades" do fonte (linha 30): "C18/C19 devem começar antes da otimização para impedir que o conjunto de teste oriente escolhas" — a vírgula acrescida pela task foi removida na entrega. A ambiguidade 6 do fonte (linha 39: "Não existe um método universalmente ótimo: cada recomendação de pesquisa deve indicar hipótese, alternativa, custo, limitação e teste de seleção.") permanece apenas registrada como pendência no parágrafo de Restrições da task ("registrar como pendência, não aplicá-la"), sem aplicação ou resolução.
  - **C3 (nada acrescido; desenho futuro ≠ resultado)** — Varredura de números na especificação C18/C19: zero dígitos no corpo das duas células, tanto na task quanto no fonte (saída do script: `numeros C18 fonte=[] task=[]`, `numeros C19 fonte=[] task=[]`); nenhum requisito, métrica, orçamento ou parâmetro além do fonte. A "comparação pareada com agente único" aparece na task exclusivamente como critério do componente C19 e como "desenho experimental futuro, não como resultado obtido", com a hipótese da etapa 1 explicitamente condicionada a essa avaliação futura — coerente com `fase2/documentos/01_esqueleto_conceitual.md` (linha 7: "Este desenho é uma proposta de implementação, não uma demonstração de superioridade. A hipótese é que separação de responsabilidades, contratos verificáveis e memória seletiva melhorem continuidade e consistência sob orçamento local. A comparação com um agente único deve usar as mesmas ferramentas, dados e limites de recursos."). Nenhuma frase da task afirma ter medido, executado ou validado qualquer comportamento.
  - **C4 (fonte intocado; correção mínima)** — `git diff aca3576 -- fase2/documentos/02_componentes_e_requisitos.md`: vazio (0 linhas); `git diff --stat` pós-correção: somente o arquivo desta task, 3 inserções/3 remoções (os dois pontos finais e a vírgula da prioridade). Nenhum documento novo criado; `docs/playground-llmagenticsystem` (submódulo) não tocado (`git diff aca3576 -- docs/playground-llmagenticsystem`: vazio).
  - **Verificador do repositório (apoio)** — `python3 fase2/scripts/verificar_documentos.py` a partir da raiz: `status: "passed"`, `components: 20`, `missing_citations: []`, `local_links_checked: 39`, `delivery_pending: []` — confirma a integridade documental da fase 2 (incluindo a tabela C01–C20 do fonte) na base trabalhada. Limitação anotada: o verificador é checagem documental (stdlib only) e não valida experimentalmente nada; não constitui resultado medido. Referência auxiliar consultada sem importar conteúdo: `fase2/documentos/08_mapa_completo_da_testagem.md` (linhas 260–261 mapeiam C18 e C19 para saídas/falhas e critérios de testagem, alinhamento de terminologia sem acrescentar requisitos).
- Pendências/bloqueios: nenhum. A ambiguidade 6 do fonte permanece registrada como pendência, sem aplicação; a comparação pareada segue como desenho experimental futuro, e a hipótese da etapa 1 permanece condicionada a essa avaliação futura.

## Notas

### Dificuldade esperada
2/10 — Conferência textual de duas linhas de tabela; risco baixo, com atenção ao enquadramento "desenho futuro ≠ resultado".

### Dificuldade sentida
2/10 — Conferência textual de duas células de tabela com script de comparação normalizada; o enquadramento "desenho futuro ≠ resultado" exigiu confronto com `01_esqueleto_conceitual.md`, mas os desvios encontrados foram apenas os mesmos pontos finais tipográficos já corrigidos nas tasks 001–006, mais uma vírgula na menção à prioridade.

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
