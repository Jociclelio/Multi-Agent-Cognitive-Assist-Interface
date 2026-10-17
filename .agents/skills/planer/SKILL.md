---
name: planer
description: Use com o agente plan para discutir uma implementação com o usuário e escrever seu plan.md antes de decompor o trabalho em tasks.
---

# Planer

## Fluxo

1. Converse sobre objetivo, resultado esperado e restrições. Leia apenas as
   fontes necessárias para embasar as decisões; não carregue todo o projeto.
2. Discuta alternativas quando afetarem a implementação. Resolva dúvidas
   essenciais com o usuário; registre decisões e dúvidas ainda abertas.
3. Escreva `.agents/plans/<slug>/plan.md` usando o formato abaixo. Atualize-o
   conforme a conversa, sem confundir uma proposta com uma decisão acordada.
4. Peça confirmação do plano. Marque `aprovado` somente após confirmação;
   então encaminhe à próxima etapa com a skill `task-writer`.

```markdown
# Plano: <título>

Estado: rascunho | aprovado | em execução | concluído

## Objetivo
<Resultado desejado.>

## Abordagem
<Decisões acordadas e sequência de alto nível.>

## Escopo
<Entregas e limites relevantes.>

## Contexto
- `arquivo` — relevância.

## Critérios de conclusão
- <Condição verificável para concluir o plano.>

## Questões abertas
<Dúvidas essenciais ou “Nenhuma”.>

## Tasks
<Índice preenchido pelo task-writer e mantido pelo task-master.>
```

Seja breve: o plano deve permitir uma nova sessão sem recuperar a conversa.
Não implemente nem crie tasks nesta etapa. Se o modo Plan impedir escrita,
entregue o texto e informe o impedimento; não contorne a restrição via shell.
