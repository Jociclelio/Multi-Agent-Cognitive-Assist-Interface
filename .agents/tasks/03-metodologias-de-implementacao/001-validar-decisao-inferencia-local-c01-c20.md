# Task 001: Validar decisão de método — inferência local (C01/C20)

Estado: aguardando revisão
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
- [x] C1 — A decisão de método para C01/C20 nesta task corresponde item a item à linha 16 do fonte (método selecionado, referências/chaves e "por quê e sob qual limite"); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task.
- [x] C2 — Nada acrescido além do fonte: nenhuma alternativa selecionada (PTQ1_0 permanece ensaio inicial e PQ2_0 alternativa), nenhum número ou requisito novo, nada apresentado como resultado medido; IDs permanentes.
- [x] C3 — O documento-fonte permanece intocado (`git diff` vazio para ele em relação à base); correções, se houver, limitam-se ao arquivo desta task em dif mínimo; commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo não tocado.

## Execução
- Modelo: GLM-5.3-Flash (provider `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime
- Base: a2590b54372a2cc4058643ccca99e4f3f1feb8bd
- Entrega: sem alteração de artefatos — a conferência não encontrou desvio de fidelidade; nenhuma correção no arquivo desta task nem em qualquer outro arquivo (task apenas de verificação; commit documental de registro único)
- Arquivos da entrega: nenhum
- Evidências:
  - **C1 (fidelidade item a item, linha 16 do fonte)** — Conferência textual automatizada (script isolado em `/tmp/opencode/check_003_001.py`, extração da linha `| C01/C20 |` de `fase2/documentos/03_metodologias_de_implementacao.md` — confirmada na linha 16 — e do bullet da decisão desta task, comparação após normalização NFC/minúsculas/espaços): `método FIEL: True`, `refs FIEL: True`, `porquê FIEL (normalizado): True`. Campo a campo: (1) método selecionado — "GGUF Bonsai 2 27B, fork Prism de llama.cpp, servidor único e manifesto completo", idêntico ao fonte; (2) referências/chaves — `bonsai2`, `bonsaidemo`, `llamasrv`, `uvlock`, mesmas quatro chaves, mesma ordem, todas presentes em `fase2/pesquisa/references_arquitetura.bib` (linhas 5, 15, 25 e 173 do `.bib`); (3) por quê e limite — "identidade rastreável; dados do fornecedor não substituem teste local. PTQ1_0 é ensaio inicial, PQ2_0 alternativa", idêntico ao fonte após normalização. Única diferença literal: inicial minúscula em "identidade" na task (posição na frase, dentro do parêntese "por quê e limite:") contra maiúscula no início da célula do fonte — adaptação tipográfica de prosa sem alteração de sentido, classificada como não-desvio e mantida sem correção.
  - **C2 (nada acrescido além do fonte; nada como resultado medido)** — Varredura de números no bullet da decisão: apenas `27` (Bonsai 2 27B), `2` (Bonsai 2/quantizações), `0`/`1` (sufixos PTQ1_0/PQ2_0), `01`/`20` (IDs C01/C20) — todos presentes no fonte (script: `todos presentes no fonte: True`); nenhum orçamento, parâmetro ou métrica novo. PTQ1_0 permanece rotulado exatamente como "ensaio inicial" e PQ2_0 como "alternativa", sem seleção entre elas e sem fixar o artefato concreto (questão aberta 1 da etapa 2 permanece decisão externa). O limite "dados do fornecedor não substituem teste local" permanece registrado como limite, não como resultado — nada na decisão é apresentado como resultado medido.
  - **C2 (IDs permanentes; característica de C01 da etapa 2 não contraditada)** — A decisão refere-se aos componentes apenas pelos IDs permanentes C01/C20, sem renomeação. A característica exigida de C01 registrada na task 001 da etapa 2 ("benchmark de português e ferramentas antes da adoção", com Ambiguidade pendente 1) não é contraditada: o limite do fonte ("dados do fornecedor não substituem teste local") reforça, e não dispensa, a exigência de teste/benchmark local antes da adoção; a decisão desta task não posiciona Bonsai 2 como adotado por dados de fornecedor. Os dados do model card citados no relatório 03a (revisão `b072e1d…`, hashes dos GGUF) permanecem no relatório de embasamento, não são incorporados à decisão como verificação local.
  - **C3 (fonte intocado; commits separados)** — Árvore limpa na base `a2590b5` antes da execução; após o registro, `git diff` vazio para `fase2/documentos/03_metodologias_de_implementacao.md` e para o submódulo `docs/playground-llmagenticsystem` (permanece em `3504c4b`); único arquivo alterado é esta task (registro). Sem commit de entrega (não houve correção); único commit documental de registro, sem amend/force-push/commits vazios.
  - **Verificador do repositório (apoio)** — `python3 fase2/scripts/verificar_documentos.py` a partir da raiz: `status: "passed"`, `components: 20`, `missing_citations: []`, `local_links_checked: 39`, `delivery_pending: []` — integridade documental da fase 2 confirmada na base trabalhada. Limitação anotada: verificação documental (stdlib only), não constitui resultado medido nem validação experimental.
- Pendências/bloqueios: nenhum bloqueio. Permanecem pendentes, sem resolução nesta task: escolha concreta do artefato Bonsai 2 (questão aberta 1 da etapa 2, decisão externa); seleção entre PTQ1_0 (ensaio inicial) e PQ2_0 (alternativa) permanece aberta no fonte; teste local de português e ferramentas antes da adoção segue como exigência futura, não realizada.

## Notas

### Dificuldade esperada
2/10 — Conferência textual de uma linha de tabela com três campos; o cuidado está em não selecionar entre PTQ1_0 e PQ2_0 nem apresentar a escolha como decidida.

### Dificuldade sentida
2/10 — Conferência textual de um único bullet contra uma linha de tabela, com checagem automatizada por script isolado; a decisão de julgamento foi classificar a inicial minúscula em "identidade" como adaptação tipográfica de prosa (não-desvio) e resistir à tentação de resolver a escolha entre PTQ1_0/PQ2_0 ou do artefato Bonsai 2, que permanecem abertos no fonte.

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
