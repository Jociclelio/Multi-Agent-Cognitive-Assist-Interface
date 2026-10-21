# Task 001: Validar decisão de método — inferência local (C01/C20)

Estado: pendente
Depende de: nenhuma
Origem: nenhuma

## Prompt
Conferir que a decisão abaixo reproduz **fielmente** a linha C01/C20 da tabela "Decisões reconciliadas" de `fase2/documentos/03_metodologias_de_implementacao.md` (documento-fonte normativo, que permanece intocado; linha 16). Registrar em Evidências a conferência item a item (método selecionado, referências/chaves, por quê e limite). Se encontrar desvio de fidelidade entre esta decisão e o fonte, corrija **apenas o texto desta task** em dif mínimo, preservando o sentido do fonte, e registre a correção em Evidências.

Decisão a validar (extraída da tabela do documento-fonte):
- **C01/C20 — Inferência local:** GGUF Bonsai 2 27B, fork Prism de llama.cpp, servidor único e manifesto completo *(referências/chaves: `bonsai2`, `bonsaidemo`, `llamasrv`, `uvlock`)* *(por quê e limite: identidade rastreável; dados do fornecedor não substituem teste local. PTQ1_0 é ensaio inicial, PQ2_0 alternativa)*

Além da fidelidade, conferir que: os IDs C01 e C20 são tratados como permanentes; nada nesta decisão acrescenta requisito, número ou alternativa não presente no fonte (PTQ1_0/PQ2_0 são exatamente ensaio inicial e alternativa, sem selecionar entre elas); a pendência do teste local (dados do fornecedor não substituem teste) permanece registrada como limite, não como resultado; a característica exigida de C01 (benchmark de português e ferramentas antes da adoção, registrada na task 001 da etapa 2) não é contraditada.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver a escolha concreta do artefato Bonsai 2 (decisão externa, questão aberta 1 da etapa 2) nem selecionar PTQ1_0 ou PQ2_0; nada pode ser apresentado como resultado medido; IDs C01–C20 permanentes; prosa em português; commit de entrega (correção de fidelidade, se houver) e commit de registro separados, sem amend/force-push/commits vazios; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/03_metodologias_de_implementacao.md` — documento-fonte: tabela "Decisões reconciliadas", linha C01/C20 (linha 16); fonte normativo da conferência.
- `fase2/pesquisa/03a_arquitetura_rag.md` — relatório integral da frente de arquitetura (C01–C05, C13–C17, C20), referência de embasamento, sem reabrir alternativas.
- `.agents/tasks/02-componentes-e-requisitos/001-validar-fundacao-inferencia-ingestao-ontologia.md` — etapa 2: características exigidas e critério verificável de C01, registradas na task anterior da família.
- `.agents/plans/03-metodologias-de-implementacao/plan.md` — plano aprovado; seções "Abordagem", "Escopo" e "Critérios de conclusão" definem o esperado.
- `AGENTS.md` (raiz) — convenções do repositório (não apresentar propostas como resultados medidos).

## Corretude
- [ ] C1 — A decisão de método para C01/C20 nesta task corresponde item a item à linha 16 do fonte (método selecionado, referências/chaves e "por quê e sob qual limite"); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task.
- [ ] C2 — Nada acrescido além do fonte: nenhuma alternativa selecionada (PTQ1_0 permanece ensaio inicial e PQ2_0 alternativa), nenhum número ou requisito novo, nada apresentado como resultado medido; IDs permanentes.
- [ ] C3 — O documento-fonte permanece intocado (`git diff` vazio para ele em relação à base); correções, se houver, limitam-se ao arquivo desta task em dif mínimo; commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo não tocado.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
2/10 — Conferência textual de uma linha de tabela com três campos; o cuidado está em não selecionar entre PTQ1_0 e PQ2_0 nem apresentar a escolha como decidida.

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
