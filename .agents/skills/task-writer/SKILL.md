---
name: task-writer
description: Use com o agente build para transformar um plan.md aprovado em tasks sequenciais pequenas, ou com task-master para escrever subtasks de correção, reinício ou divisão.
---

# Task Writer

1. Leia o plano aprovado e o template abaixo. Resolva dúvidas
   essenciais antes de transformar suposições em requisitos.
2. Divida o plano do começo ao fim em entregas coesas, pequenas e verificáveis.
   Use `.agents/tasks/<slug-do-plano>/<NNN-descrição>.md` e ordem explícita.
   Cada task deve caber em uma sessão focada e ter uma entrega isolável no Git.
3. Preencha Prompt (entrega e limites), Contexto (paths reais e relevância),
   Corretude (procedimento e resultado esperado) e dificuldade esperada, 0–10
   com justificativa. Numere os critérios C1, C2 etc. para referência na revisão.
4. Deixe Execução, dificuldade sentida e Revisão por preencher. Há uma única
   seção de revisão, pertencente ao task-master. Não invente avaliações.
5. Coloque dependências e, na **última linha**, o link relativo para o `plan.md`.
   Arquivos que só existirão após uma dependência devem ser identificados assim.
6. Atualize o índice do plano: ordem, link, dependências e estado de cada task.
   Confira que todas as entregas e critérios do plano estão cobertos.

## Template da task

```markdown
# Task <NNN>: <título>

Estado: pendente
Depende de: <IDs ou nenhuma>
Origem: <task mãe e tipo: correção/reinício/divisão, ou nenhuma>

## Prompt
<O que fazer, resultado esperado e restrições.>

## Contexto
- `caminho/arquivo` — por que ler.

## Corretude
- [ ] C1 — <Procedimento de verificação e resultado esperado.>

## Execução
- Modelo: <identificador real do executor>
- Base: <SHA completo antes da implementação>
- Entrega: <SHA(s) completos, sem commits de registro, ou sem alteração de artefatos>
- Arquivos da entrega: <paths ou referência ao diff dos commits>
- Evidências: <comandos/procedimentos, resultados e limitações>

## Notas

### Dificuldade esperada
_/10 — <Justificativa do autor: 0 trivial, 10 muito difícil.>

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

Plano: [plan.md](../../plans/<slug>/plan.md)
```

## Subtasks

- Correção da 002: `002-1-<slug>.md`, depois `002-2-<slug>.md`; escolha o próximo
  sufixo livre da família, sem sobrescrever arquivos ou proliferar níveis.
- Referencie a task de origem no Contexto. Transforme o parecer em instruções
  executáveis e critérios objetivos; não copie relatórios extensos.
- Correção preserva a entrega anterior. Reinício e divisão partem da base já
  restaurada pelo task-master: inclua o SHA da reversão e o que fazer diferente.
- Reinício exige modelo diferente do executor rejeitado; registre essa
  restrição no Prompt, sem inventar um identificador de modelo disponível.
- Divisão cobre toda a entrega original em passos menores, com dependências.
- Insira as subtasks antes da próxima task principal. Ela depende da resolução
  de toda a família anterior, mesmo quando seu campo original cita só a mãe.
- A task original permanece como histórico. O master registra nela a decisão;
  não reescreva seu contrato, evidências ou dificuldade para simular sucesso.

## Conferência

O documento deve ser suficiente para um executor novo, sem carregar outras
conversas. Prefira referências a transcrições. Confira links, sequência,
escopo, critérios observáveis e a referência ao plano na última linha.
