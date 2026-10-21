# EduAgent-OS v0.1 — núcleo textual local

Scaffold do EduAgent-OS v0.1 conforme o mapa normativo
[`fase2/documentos/04_mapa_completo_do_sistema.md`](fase2/documentos/04_mapa_completo_do_sistema.md)
(§3: stack, diretórios e configuração). Estado atual: **scaffold e configuração
apenas** (task 001 do plano `.agents/plans/04-mapa-completo-do-sistema/plan.md`);
módulos são stubs sem lógica de agentes/serviços.

## Estrutura (mapa §3)

```text
eduagent/
  api.py cli.py config.py contracts.py graph.py context.py policy.py
  agents/{curator,tutor,monitor,planner,librarian}.py
  services/{ingestion,retrieval,memory,assessment,scheduling,calendar,effects}.py
  storage/{repository,migrations,checkpoints}.py
  skills/{explain,graduated_hint,quiz,flashcard,self_explain}/skill.yaml
  telemetry.py
config/default.yaml
schemas/                         # JSON Schemas exportados dos contratos
data/<user_id>/{originals,derived,indexes,exports}/
tests/ fixtures/ eval/           # especificação de testes: etapa 8 (mapa de testes)
```

`data/domain.sqlite` e `data/checkpoints.sqlite` são artefatos de runtime
(criados pelas tasks de armazenamento) e não são versionados.

## Ambiente

- Python 3.11+ (arquivo `.python-version` fixa o interpretador do venv em 3.12;
  wheel availability é prioridade de ambiente, não decisão normativa).
- Dependências pinadas por `uv.lock` (pin real resolvido, não presumido).
  Torch usa o índice CPU do PyTorch para o MVP textual local.
- Setup: `uv sync` (cria `.venv` e instala do lock).

## Configuração

`config/default.yaml` reproduz os defaults do mapa §3. Todos os valores
numéricos são **defaults de ensaio** a calibrar no hardware registrado antes do
congelamento — não são resultados medidos. `timezone` não está fixado
(`America/Sao_Paulo` somente após confirmação explícita).
