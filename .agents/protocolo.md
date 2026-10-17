# Protocolo: plano → tasks → execução → revisão

Fluxo de trabalho com agentes de IA, neutro de ferramenta. Foi desenhado para
rodar igual no OpenCode e no Google Antigravity: o que vale são os **arquivos**
e os **invariantes** abaixo, não a mecânica de cada ferramenta.

- `.agents/skills/` — skills canônicas (`planer`, `task-writer`, `task-executor`)
  no formato aberto SKILL.md, carregadas nativamente pelo Antigravity
  (`.agents/skills/`) e reaproveitáveis pelo OpenCode. Mudanças aqui devem ser
  espelhadas nas cópias locais de cada ferramenta.
- `.agents/plans/<slug>/plan.md` — planos.
- `.agents/tasks/<slug>/<NNN-descrição>.md` — tasks e subtasks.
- `.agents/contrato-revisor.md` — contrato comum dos revisores.

**Atenção**: dentro de `.agents/`, os nomes `rules/` e `AGENTS.md` têm
significado especial para o Antigravity; não use esses nomes para outra coisa.

## Papéis

Quatro papéis, independentes de ferramenta. Uma sessão nova por etapa/task
para manter o contexto pequeno; os arquivos são a memória do fluxo e o Git
guarda entregas, decisões e tentativas rejeitadas.

- **Planejador** (`planer`): discute a implementação com o usuário e escreve
  `plan.md`. Não implementa nem cria tasks.
- **Escritor** (`task-writer`): decompõe o plano aprovado em tasks sequenciais
  pequenas; também escreve subtasks de correção, reinício ou divisão.
- **Executor** (`task-executor`): implementa **uma única task**, verifica a
  Corretude e commita a entrega. Nunca revisa a si mesmo, nunca delega outra
  execução e não inicia a próxima task.
- **Master**: orquestra o ciclo e consolida a revisão. Único responsável por
  decisão, reversão, criação de subtasks e liberação da sequência.

No OpenCode, os papéis correspondem aos agentes/subagentes globais do usuário.
No Antigravity, execute os papéis em sessões separadas do Agent Manager (ou
subagents nativos), sempre a partir de uma sessão limpa por papel.

## Fluxo

1. **Plano:** use a skill `planer` e escreva `.agents/plans/<slug>/plan.md`.
   Confirme o plano com o usuário antes de prosseguir.
2. **Tasks:** em sessão nova, use `task-writer` para decompor o plano aprovado
   em `.agents/tasks/<slug>/<NNN-...>.md`, seguindo o template da skill.
3. **Versione a base documental** (plano + tasks) antes das entregas, em commit
   separado da implementação.
4. **Execução:** em sessão nova, use `task-executor` para a task atual,
   incluindo os commits do fluxo (entrega separada do registro).
5. **Revisão:** em sessão nova, o master consolida **três revisões
   independentes** conforme `.agents/contrato-revisor.md` e decide.
6. Repita a partir do passo 4 na próxima task indicada, até concluir o plano.
   Correções, reinícios e divisões entram antes da próxima task principal.

## Invariantes (vale para qualquer ferramenta)

- Uma task por sessão de execução; não carregue a fila inteira.
- O executor não revisa a própria entrega; quem revisa não edita nem commita.
- Quórum de revisão: **três modelos distintos**, pareceres independentes, nota
  0–10 cada. Nunca reduza a rodada a dois; sem quórum, pause sem decidir.
- Decisões do master: `fechar`, `corrigir` (subtask pontual), `reiniciar`
  (reversão + subtask com **outro modelo** de executor) ou `repartir`
  (reversão + sequência de tasks menores).
- Reversões são commits novos feitos pelo master; task original e commits
  antigos permanecem como histórico — não reescreva contratos nem evidências.
- Subtasks entram antes da próxima task principal e registram o aprendizado da
  tentativa anterior; a mãe só se resolve quando toda a família fecha.
- Commits do executor: **entrega** (só artefatos) e **registro** (task.md com
  SHAs e evidências) separados. Sem amend, force-push ou commit vazio.
- Verificações usam temporários isolados; sem jobs remotos/benchmarks longos
  sem autorização explícita. Falta de ambiente não é aprovação.
- Dificuldade esperada/sentida (0–10) mede esforço; notas de revisão medem
  qualidade. Não invente avaliações.

## Notas por ferramenta

- **OpenCode:** o motor (agentes, pool de revisores e o ciclo opt-in
  `task_cycle`) é global, em `~/.config/opencode/`; os paths dos documentos
  passam a ser `.agents/plans/` e `.agents/tasks/`. O marcador
  `<!-- task-cycle: ... -->` e as regras de handoff seguem descritos no
  `WORKFLOW.md` global.
- **Antigravity:** este arquivo e `AGENTS.md` na raiz já são descobertos
  automaticamente. Rode cada papel numa sessão própria e aplique os invariantes
  literalmente: três revisões em sessões separadas, decisão documentada na
  seção Revisão da task, commits nos mesmos moldes. Não há equivalente do ciclo
  automático; a progressão é manual, task a task.
