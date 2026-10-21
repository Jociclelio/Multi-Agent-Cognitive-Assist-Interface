# Task 015: CLI mínima, API loopback e observabilidade (mapa §12, §13.8 parte 2)

Estado: pendente
Depende de: 014
Origem: nenhuma

## Prompt
Implementar a interface e a observabilidade (mapa §12) em `eduagent/cli.py`, `eduagent/api.py` e `eduagent/telemetry.py`: CLI mínima com `doctor, ingest, ask, practice, submit, plan, approve, export, resume, cancel, trace, backup, restore, delete`; API loopback com POST `/turns`, POST `/turns/{id}/resume`, POST `/turns/{id}/cancel`, GET `/artifacts/{id}`, GET `/health`; escrita exige contexto de usuário autenticado localmente. Exit codes: 0 sucesso/espera legítima, 2 entrada ambígua/inválida, 3 recurso/conector indisponível, 4 falha interna; JSON sempre contém status. Trace local por turno com spans de fila/LLM/retrieval/context/solver/commit/tools; registrar versões, seed/sampling, counts entrada/raciocínio/saída quando disponíveis, status/truncamento, tempo ativo/fila/total, RSS/VRAM e erros; não logar payload pessoal completo por padrão; métricas desconhecidas ficam `null` com razão, nunca zero; custo local: tokens/segundos/energia quando medidos, com amortização documentada; custo API apenas se conector pago usado. Backup: fechar escritores/checkpointer, consolidar e copiar conjunto consistente com originais/manifesto; restore em diretório novo com verificador de integridade/replay; exclusão ativa imediata com backups pendentes até expiração (30 dias propostos), tombstone sem payload aplicado **antes** de liberar restore, remoção de backup com apenas usuário excluído já na solicitação; CLI mostra escopo/prazo, sem alegar sanitização forense; expiração verificada por job/doctor com relógio e catálogo (§15.1). `doctor` reporta saúde do modelo/DB/índices/config.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §12 integral; §15.1 (backup/tombstones); §13.8.
- Grafo (014), storage (004/005).

## Corretude
- [ ] C1 — Todos os comandos CLI e endpoints funcionam contra o grafo; exit codes e JSON com status conforme mapa (tabela de testes por comando).
- [ ] C2 — Traces por turno com spans listados; payload pessoal não logado por padrão; métrica desconhecida = null com razão (teste).
- [ ] C3 — Backup consistente + restore em diretório novo com verificação; tombstone antes do restore; expiração com catálogo (testes).
- [ ] C4 — Mapa intocado; commits separados; submódulo não tocado.

## Notas

### Dificuldade esperada
4/10 — Superfície ampla mas mecânica; risco em backup/restore consistente.

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

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
