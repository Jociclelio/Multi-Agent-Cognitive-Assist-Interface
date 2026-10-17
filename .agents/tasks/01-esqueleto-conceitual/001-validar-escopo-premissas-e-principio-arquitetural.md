# Task 001: Validar escopo, premissas, hipótese e princípio arquitetural (seções 1–2)

Estado: aguardando revisão
Depende de: nenhuma
Origem: nenhuma

## Prompt
Validar e, se necessário, corrigir as seções 1 ("Escopo e premissas") e 2 ("Princípio arquitetural") de `fase2/documentos/01_esqueleto_conceitual.md` contra o plano aprovado. A entrega do plano já existe e está commitada: **não reescreva o documento do zero**; faça conferência item a item e correções mínimas e pontuais apenas onde encontrar lacunas ou desvios.

Procedimento:
1. Conferir o recorte de escopo da seção 1 contra o fonte normativo: graduação, interação textual em português, documentos e PDFs do estudante, recursos complementares, exercícios, flashcards, memória entre sessões e planejamento semanal; ODS principal 4; infraestrutura local (inferência, recuperação e armazenamento) com rede opcional para curadoria e agenda; exclusões (sem notas oficiais, geração de vídeos, treinamento fundacional, integração acadêmica fechada). Usar `fase1/fase1_proposta.tex` (fonte LaTeX, preferencial para citação textual) e `fase1/fase1_proposta.pdf` como referência de conferência. Em divergência entre o plano aprovado e a fase 1, prevalece o plano; registre a divergência em Evidências.
2. Conferir que a hipótese (separação de responsabilidades, contratos verificáveis e memória seletiva melhorando continuidade e consistência sob orçamento local) e a comparação com agente único (mesmas ferramentas, dados e limites de recursos) estão registradas **como hipótese/proposta condicionada a avaliação futura**, nunca como resultado medido ou demonstração de superioridade.
3. Conferir a seção 2: cinco agentes lógicos compartilhando um modelo local com instruções, dados e permissões distintos; coordenação por grafo explícito (não conversa irrestrita); componentes determinísticos validando decisões do LLM; agentes não escrevem livremente nos armazenamentos.
4. Validar o diagrama Mermaid da seção 2: sintaxe válida (renderizável) e consistente com os cinco agentes, o orquestrador, a base documental, a memória e o solver — cada agente da tabela da seção 3 deve aparecer no grafo, e as arestas devem refletir o fluxo do ciclo da seção 4.
5. Registrar em Evidências o que foi conferido, divergências encontradas e correções aplicadas (ou a ausência delas).

Restrições: preservar a prosa acadêmica em português; difs mínimos; não introduzir números, métricas ou comparações como resultados medidos; não resolver as questões abertas nesta etapa; só alterar `fase2/documentos/01_esqueleto_conceitual.md` (e, no commit de registro, o arquivo desta task).

## Contexto
- `fase2/documentos/01_esqueleto_conceitual.md` — documento-fonte da etapa 1, objeto da validação (seções 1 e 2).
- `.agents/plans/01-esqueleto-conceitual/plan.md` — plano aprovado; seções "Abordagem" (bullets 1–2), "Escopo" e "Critérios de conclusão" definem o esperado.
- `fase1/fase1_proposta.tex` e `fase1/fase1_proposta.pdf` — fonte normativo do escopo, citado pelo documento; o `.tex` permite conferir o texto sem depender de extração de PDF.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — leitura de apoio para checar alinhamento de terminologia (cinco agentes, orquestrador, contratos), sem importar conteúdo desta etapa; a checagem obrigatória de nomenclatura é critério da Task 002 (C5).
- `AGENTS.md` (raiz) — convenções do repositório (prosa acadêmica em português, não apresentar propostas como resultados medidos).

## Corretude
- [x] C1 — Cada item do recorte de escopo listado no plano (itens incluídos, ODS 4, infraestrutura local/rede opcional e as quatro exclusões) está presente na seção 1 do documento; conferência registrada em Evidências contra `fase1/fase1_proposta.tex`/`.pdf`.
- [x] C2 — A hipótese e a comparação com agente único aparecem na seção 1 exclusivamente como proposição condicionada a avaliação futura, sem qualquer formulação que as apresente como resultado medido, demonstrado ou validado.
- [x] C3 — A seção 2 contém explicitamente: modelo local compartilhado, instruções/dados/permissões distintos por agente, coordenação por grafo explícito, validação determinística de decisões do LLM e restrição de escrita dos agentes aos armazenamentos.
- [x] C4 — O bloco Mermaid da seção 2 é sintaticamente válido (renderizável; preferir verificação determinística, ex.: renderizador Mermaid executado em `/tmp/opencode` com a ferramenta registrada em Evidências, sendo a leitura manual o fallback registrado) e menciona os cinco agentes nomeados na tabela da seção 3, sem agente órfão ou aresta contraditória com o ciclo da seção 4.
- [x] C5 — Correções (se houver) limitam-se às seções 1–2, em difs mínimos que preservam a prosa; se nenhuma lacuna for encontrada, a entrega é o commit de registro documentando a conformidade, sem alteração de artefatos. *(Nenhuma lacuna ou desvio encontrado: sem alteração de artefatos.)*

## Execução
- Modelo: GLM-5.3-Flash (provider `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime
- Base: e7f3f9c765887df62eca2edbfb2f4a1a505e9b97
- Entrega: sem alteração de artefatos (validação conforme C5; nenhuma lacuna ou desvio encontrado em seções 1–2)
- Arquivos da entrega: nenhum (somente este registro; diff de `fase2/documentos/01_esqueleto_conceitual.md` permanece vazio em relação à base)
- Evidências:
  - **C1 (escopo)** — Conferência item a item da seção 1 contra `fase1/fase1_proposta.tex` (linhas 51, 60, 84, 86) e contra o PDF extraído com `pdftotext` (`/tmp/opencode/fase1_p1-6.txt`; texto do PDF idêntico ao `.tex` no trecho da delimitação). Todos os itens presentes no documento: graduação; interação textual em português; documentos e PDFs do estudante; recursos complementares existentes; exercícios; flashcards; memória entre sessões; planejamento semanal; ODS principal 4; inferência/recuperação/armazenamento locais; rede opcional para curadoria e agenda; exclusões de notas oficiais, geração de vídeos, treinamento fundacional e integração acadêmica fechada. **Divergência plano × fase 1 registrada (prevalece o plano, sem alteração):** a fase 1 exclui também "a substituição do PDD oficial" e adia "síntese de voz e gamificação" para extensões posteriores; o plano aprovado e a task listam exatamente quatro exclusões, e o documento segue o plano.
  - **C2 (hipótese)** — Seção 1, 2º parágrafo: "Este desenho é uma proposta de implementação, não uma demonstração de superioridade. A hipótese é que…" e "A comparação com um agente único **deve** usar as mesmas ferramentas, dados e limites de recursos" — formulação condicional, sem qualquer número, métrica ou afirmação de resultado medido/demonstrado. Nenhuma ocorrência problemática encontrada (grep por termos de resultado nas seções 1–2: limpo).
  - **C3 (princípio arquitetural)** — Seção 2, 1º parágrafo contém explicitamente: cinco agentes lógicos compartilhando um modelo local; "recebem instruções, dados e permissões diferentes"; "A coordenação é um grafo explícito, não uma conversa irrestrita"; "Componentes determinísticos validam decisões produzidas pelo LLM"; "Agentes não escrevem diretamente em todos os armazenamentos nem escolhem livremente seus destinatários".
  - **C4 (Mermaid)** — Renderizador Mermaid **indisponível** no ambiente: `mmdc` ausente, `mermaid` não resolvível via Node e `npx` exigiria instalação (proibida pela task). Fallback aplicado conforme C4: (a) leitura manual linha a linha — cabeçalho `flowchart TD`, 11 nós com rótulos entre colchetes sem caracteres reservados problemáticos (aspas, colchetes ou pipes internos), 15 arestas `-->` bem formadas; (b) verificação estrutural determinística complementar em `/tmp/opencode/check_mermaid_001.py` (script Python stdlib, sem renderização): todos os nós referenciados por arestas estão declarados, e os cinco agentes da tabela da seção 3 (Curador de Conhecimento, Tutor Adaptativo, Monitor de Aprendizagem, Planejador de Rotina, Bibliotecário de Memória) aparecem no grafo, além de Orquestrador, base documental, memória (Eventos, perfil e estado por tópico) e Solver — sem agente órfão. Coerência das arestas com o ciclo da seção 4 (análise manual): captura (U→O→C/B), recuperação (C→R→T), tutoria (T→U), avaliação (U→A), persistência (A→B→M), replanejamento (A→P, M→P), solver (P→S→U) e camada transversal (O→V) — nenhuma aresta contraditória com o ciclo. Observação (não é contradição nem lacuna obrigatória): o grafo não desenha aresta Curador→Bibliotecário para fatos confirmados; o passo 2 do ciclo não exige essa aresta no diagrama e a fase 1 também não a declara explicitamente — registrado para consideração na revisão, sem alteração nesta etapa.
  - **Verificador de documentos** — `python3 fase2/scripts/verificar_documentos.py`: status "passed", 39 links locais verificados, sem citações pendentes (executado como evidência geral; checagem final completa é critério da task 003).
  - Limitações: sem renderização efetiva do Mermaid (limitação registrada); validade sintática confirmada por leitura manual + checagem estrutural, não por renderizador.

## Notas

### Dificuldade esperada
3/10 — Conferência textual de duas seções curtas contra um plano que as descreve quase literalmente; a única parte com risco moderado é julgar validade sintática e coerência do diagrama Mermaid sem ambiente de renderização garantido, o que pode exigir verificação manual linha a linha.

### Dificuldade sentida
3/10 — Conferência textual direta, conforme o esperado. A única fricção real foi a ausência de renderizador Mermaid no ambiente (exigiu fallback de leitura manual + script estrutural próprio, com dois ajustes no script até refletir os rótulos do grafo), e a decisão de não tratar a ausência da aresta Curador→Bibliotecário como lacuna corretiva, por não haver contradição com o ciclo nem exigência do plano/fase 1.

### Revisão
- Orquestrador: —
- Alvo: <SHAs da entrega e versão do registro revisado>
- Avaliações: <modelo A: _/10; modelo B: _/10; modelo C: _/10>
- Nota final: _/10
- Parecer: <síntese dos achados, evidências, divergências e Corretude pendente>
- Decisão: <fechar | corrigir | reiniciar | repartir; pendente se bloqueada>
- Reversão: <SHA ou não se aplica>
- Próximo passo: <subtasks em ordem ou próxima task liberada>

Plano: [plan.md](../../plans/01-esqueleto-conceitual/plan.md)
