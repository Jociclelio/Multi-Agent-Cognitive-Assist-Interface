---
name: task-executor
description: Use com o subagente task-executor ou o agente build para implementar uma única task Markdown, verificar a Corretude, registrar dificuldade sentida e commitar a entrega para revisão.
---

# Task Executor

## Executar uma task

1. Leia a task inteira, as instruções do projeto e os arquivos de Contexto.
   Consulte o plano e o índice para confirmar a ordem. Só execute quando as
   dependências e suas subtasks estiverem resolvidas. Não carregue toda a fila.
2. Confira `git status`, diff e último commit; registre o SHA base. Identifique
   alterações preexistentes. Não misture outra entrega no commit da task.
3. Em reinício, confirme a reversão registrada e use outro modelo. Se estiver
   no mesmo modelo rejeitado, pare e solicite a troca; não finja trocar modelo.
4. Implemente apenas o Prompt. Registre impedimentos, sem ampliar o escopo.
5. Execute Corretude. Marque apenas critérios comprovados; registre comandos,
   resultados e limitações de forma compacta. Use `correct == 1` em I/O quando
   aplicável. Falta de ambiente não é aprovação. Use artefatos temporários
   isolados e não dispare jobs remotos/benchmarks longos sem autorização.
6. Preencha Execução com identidade real do modelo, base, evidências e arquivos
   da entrega; preencha dificuldade sentida (0–10 + justificativa).

## Entrega e commits

Ao receber autorização para executar este fluxo, faça os commits da task;
uma restrição explícita de “sem commit” prevalece e deve constar como pendência.
Antes de cada commit, confira `git status`, `git diff`, `git diff --cached` e
`git log --oneline -10`; siga o estilo local e adicione somente paths da task.
Se houver arquivos alheios no índice, não os commite nem os retire sem acordo.
O repositório pode ignorar `.agents/`: confira `git check-ignore -v <task.md>`
e use `git add -f -- <task.md>` somente para o registro documental autorizado.
Nunca force a inclusão da pasta inteira nem de arquivos de estado/segredos.

1. **Entrega:** commite somente os artefatos da implementação (incluindo docs
   que sejam a entrega), separadamente do registro da task e do índice do plano.
   Essa separação permite ao master reverter a entrega sem perder o histórico.
2. **Registro:** escreva o SHA completo da entrega no `.md`, marque
   `aguardando revisão` e commite o registro da task. O commit de registro é
   encontrado por `git log -- <task.md>`; não tente guardar seu SHA em si mesmo.

Não use amend, force-push ou commit vazio. Para tasks apenas de verificação,
registre `sem alteração de artefatos` no campo de entrega e faça só o commit
documental. Se a execução estiver bloqueada, registre esse estado e a causa;
não declare entrega pronta. Registre todos os SHAs caso mais de um commit de
entrega seja necessário, sem incluir commits de registro nessa lista.

Finalize com caminho da task, commits, resultado das verificações e pendências.
Não preencha Revisão, não inicie a próxima task e não faça a revisão de si
mesmo. Não delegue outra execução nem chame master/revisores. Como subagente,
retorne ao chamador (o master retoma a revisão); no build manual, indique a
revisão pelo master numa sessão focada na entrega.
