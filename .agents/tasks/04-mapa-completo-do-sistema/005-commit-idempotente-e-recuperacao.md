# Task 005: Commit idempotente, recibo e recuperação (mapa §11, §13.2)

Estado: pendente
Depende de: 004
Origem: nenhuma

## Prompt
Implementar o commit idempotente do mapa §11 em `eduagent/services/effects.py`/`eduagent/storage/repository.py`: `commit(operation_id, digest, expected_version)` abre transação curta, confere identidade/permissão e **primeiro verifica `operation_id`**: mesmo ID+digest+usuário devolve o recibo anterior mesmo que `expected_version` agora seja antiga; digest/usuário diferente para o mesmo ID falha. Operação nova: confere revisão esperada, insere evento/operação/outbox e atualiza projeção, atomicamente. Não manter transação durante LLM/rede. Checkpoint (DB separado, task 014) não é atômico: replay consulta a operação autoritativa e reutiliza o recibo. Implementar dispatcher com lease para o outbox: crash antes do commit não promove estado; após commit recupera pendente; após efeito antes do ACK reconcilia destino por identidade; efeito desconhecido sem consulta possível permanece `UNKNOWN_EFFECT` sem retry automático. Entrega ao menos uma vez; sem promessa de exactly-once distribuído. Validar crash/replay com testes que matam o processo em pontos definidos (antes/depois do commit, antes/depois do efeito) e demonstram: sem duplicação, sem perda de efeito reconhecido, recibo estável.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §11 integral; §15.1 (receipt/lease/trace não incrementam domain_revision).
- Storage da task 004; contrato `Operation` da 003.

## Corretude
- [ ] C1 — Semântica exata do §11: dedup por `operation_id` antes de `expected_version`; conflito de digest/usuário falha; commit atômico com evento+operação+outbox+projeção.
- [ ] C2 — Testes de crash/replay reproduzem os três cenários (pré-commit, pós-commit, pós-efeito sem ACK) sem duplicação nem perda; recibo reutilizado no replay.
- [ ] C3 — Dispatcher com lease; `UNKNOWN_EFFECT` sem retry automático; lease/recibo não incrementam `domain_revision`.
- [ ] C4 — Mapa intocado; commits separados; submódulo não tocado.

## Notas

### Dificuldade esperada
6/10 — Semântica idempotente com simulação de crash; fácil errar a ordem dedup→version.

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
