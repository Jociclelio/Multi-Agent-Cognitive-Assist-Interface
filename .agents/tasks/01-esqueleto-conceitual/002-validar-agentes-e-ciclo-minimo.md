# Task 002: Validar responsabilidades/fronteiras dos cinco agentes e ciclo mínimo com terminais (seções 3–4)

Estado: pendente
Depende de: 001
Origem: nenhuma

## Prompt
Validar e, se necessário, corrigir as seções 3 ("Responsabilidades e fronteiras") e 4 ("Ciclo mínimo") de `fase2/documentos/01_esqueleto_conceitual.md` contra o plano aprovado. A entrega já existe e está commitada: **não reescreva o documento**; confira item a item e aplique apenas correções pontuais onde houver lacunas. A Task 001 já terá garantido a conformidade das seções 1–2; não retrabalhe essas seções.

Procedimento:
1. Conferir a tabela da seção 3: para cada um dos cinco agentes (Curador de Conhecimento, Tutor Adaptativo, Monitor de Aprendizagem, Planejador de Rotina, Bibliotecário de Memória) deve haver responsabilidade, artefato produzido e fronteira. Conferir que as fronteiras exemplificadas no plano estão presentes: conteúdo recuperado não é instrução executável; viabilidade de agenda decidida por solver/verificador, não pelo texto do LLM; resumos são derivados e originais permanecem consultáveis.
2. Conferir alinhamento terminológico com o mapa normativo `fase2/documentos/04_mapa_completo_do_sistema.md` (nomes dos agentes, orquestrador, contratos): divergências de nomenclatura entre o esqueleto e o mapa devem ser corrigidas no esqueleto apenas se caracterizarem inconsistência factual (por exemplo, agente com nome divergente); diferenças de granularidade esperadas entre esqueleto e mapa não são defeito.
3. Conferir o ciclo mínimo da seção 4: exatamente os 7 passos do plano, na ordem — captura → extração/validação de fatos → recuperação sob orçamento de contexto → atividade/resposta/avaliação por critérios explícitos → persistência de evidência e estimativa → solver de agenda → continuidade entre sessões (ferramentas externas só recebem ações confirmadas).
4. Conferir os terminais explícitos: resposta, pedido de esclarecimento, espera pelo aluno, conflito de agenda, falha controlada e cancelamento; e a assertiva de que esperar o aluno não é continuar gerando chamadas.
5. Registrar em Evidências o resultado da conferência por agente e por passo, divergências encontradas e correções aplicadas (ou a ausência delas).

Restrições: preservar a prosa acadêmica em português e o formato de tabela/lista existente; difs mínimos; não introduzir números ou métricas como resultados medidos; não expandir o escopo para além das seções 3–4; só alterar `fase2/documentos/01_esqueleto_conceitual.md` (e, no commit de registro, o arquivo desta task).

## Contexto
- `fase2/documentos/01_esqueleto_conceitual.md` — documento-fonte; seções 3 (tabela de responsabilidades e fronteiras) e 4 (ciclo em 7 passos e terminais) são o objeto desta task.
- `.agents/plans/01-esqueleto-conceitual/plan.md` — plano aprovado; bullets 3–4 da "Abordagem" e "Critérios de conclusão" definem o esperado para estas seções.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — mapa normativo de implementação; ler as seções de agentes/arquitetura para checar consistência de nomes e fronteiras (é leitura de apoio, não fonte a copiar).
- `.agents/tasks/01-esqueleto-conceitual/001-validar-escopo-premissas-e-principio-arquitetural.md` — task anterior; ler seu registro (Execução/Evidências) para herdar o estado das seções 1–2 sem refazer o trabalho.

## Corretude
- [ ] C1 — A tabela da seção 3 cobre os cinco agentes nomeados no plano, cada um com responsabilidade, artefato produzido e fronteira não vazios; conferência registrada em Evidências item a item.
- [ ] C2 — As três fronteiras exemplificadas no plano (conteúdo recuperado não é instrução; viabilidade decidida por solver/verificador; resumos derivados com originais consultáveis) estão expressas na tabela ou no texto da seção 3.
- [ ] C3 — A seção 4 contém exatamente os 7 itens numerados do plano, na ordem especificada e sem itens numerados extras (o parágrafo de terminais é verificado em C4 e não conta como passo), incluindo orçamento de contexto no passo de recuperação, critérios explícitos na avaliação e ações confirmadas para ferramentas externas.
- [ ] C4 — Os seis terminais do plano (resposta, pedido de esclarecimento, espera pelo aluno, conflito de agenda, falha controlada, cancelamento) estão enumerados na seção 4, acompanhados da assertiva de que esperar o aluno não equivale a continuar gerando chamadas.
- [ ] C5 — Nomenclatura dos agentes no documento é consistente com `fase2/documentos/04_mapa_completo_do_sistema.md` (ou divergências detectadas foram corrigidas/justificadas em Evidências); correções (se houver) limitam-se às seções 3–4, em difs mínimos; se nada precisar mudar, a entrega é o commit de registro sem alteração de artefatos.

## Execução
- Modelo: <identificador real do executor>
- Base: <SHA completo antes da implementação>
- Entrega: <SHA(s) completos, sem commits de registro, ou sem alteração de artefatos>
- Arquivos da entrega: <paths ou referência ao diff dos commits>
- Evidências: <comandos/procedimentos, resultados e limitações>

## Notas

### Dificuldade esperada
3/10 — Tabela e lista curtas com correspondência quase literal no plano; a dificuldade está no julgamento fino do item de alinhamento com o mapa normativo (distinguir inconsistência factual de diferença legítima de granularidade) e em resistir à tentação de expandir o texto além da validação.

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
