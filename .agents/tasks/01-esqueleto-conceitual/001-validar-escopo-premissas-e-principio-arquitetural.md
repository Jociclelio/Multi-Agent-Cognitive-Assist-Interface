# Task 001: Validar escopo, premissas, hipótese e princípio arquitetural (seções 1–2)

Estado: pendente
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
- [ ] C1 — Cada item do recorte de escopo listado no plano (itens incluídos, ODS 4, infraestrutura local/rede opcional e as quatro exclusões) está presente na seção 1 do documento; conferência registrada em Evidências contra `fase1/fase1_proposta.tex`/`.pdf`.
- [ ] C2 — A hipótese e a comparação com agente único aparecem na seção 1 exclusivamente como proposição condicionada a avaliação futura, sem qualquer formulação que as apresente como resultado medido, demonstrado ou validado.
- [ ] C3 — A seção 2 contém explicitamente: modelo local compartilhado, instruções/dados/permissões distintos por agente, coordenação por grafo explícito, validação determinística de decisões do LLM e restrição de escrita dos agentes aos armazenamentos.
- [ ] C4 — O bloco Mermaid da seção 2 é sintaticamente válido (renderizável; preferir verificação determinística, ex.: renderizador Mermaid executado em `/tmp/opencode` com a ferramenta registrada em Evidências, sendo a leitura manual o fallback registrado) e menciona os cinco agentes nomeados na tabela da seção 3, sem agente órfão ou aresta contraditória com o ciclo da seção 4.
- [ ] C5 — Correções (se houver) limitam-se às seções 1–2, em difs mínimos que preservam a prosa; se nenhuma lacuna for encontrada, a entrega é o commit de registro documentando a conformidade, sem alteração de artefatos.

## Execução
- Modelo: <identificador real do executor>
- Base: <SHA completo antes da implementação>
- Entrega: <SHA(s) completos, sem commits de registro, ou sem alteração de artefatos>
- Arquivos da entrega: <paths ou referência ao diff dos commits>
- Evidências: <comandos/procedimentos, resultados e limitações>

## Notas

### Dificuldade esperada
3/10 — Conferência textual de duas seções curtas contra um plano que as descreve quase literalmente; a única parte com risco moderado é julgar validade sintática e coerência do diagrama Mermaid sem ambiente de renderização garantido, o que pode exigir verificação manual linha a linha.

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

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
