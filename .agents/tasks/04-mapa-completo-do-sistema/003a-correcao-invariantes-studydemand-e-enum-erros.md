# Task 003a: Correção dos invariantes de `StudyDemand` e enum de `error_codes` (mapa §4)

Estado: pendente
Depende de: 003
Origem: 003 — correção

## Prompt
Correção delimitada da entrega da task 003 (preservada; base atual = HEAD com entrega `82bac2dd3600967358f1db42154913a3c7375834`). Fonte normativa única: `fase2/documentos/04_mapa_completo_do_sistema.md` — INTOCADO; "deve" é contrato; §15 prevalece quando especifica regra mais precisa. Resolver:

1. **A1 (obrigatório)** — O revisor `opencode/mimo-v2.6-flash-free` verificou por probe que `StudyDemand` aceita `mandatory=True` com `duration_status="estimated"` (`eduagent/contracts.py`, região ~820–846). Verifique contra o mapa §4 (tabela, linha de `StudyDemand`: "restrição dura exige confirmação"), §15.3 ("rótulo estimated e mandatory=false … confirmar para obrigatória") e §8 ("não converter incerteza em obrigação"): se a leitura normativa confirmar a regra, implemente o validador `mandatory=True ⇒ duration_status="confirmed"` (mais teste de rejeição e de aceitação); se concluir que a regra NÃO se aplica à tabela §4, registre a leitura com citação exata do mapa no task.md e não altere o contrato — em ambos os casos C1 fica resolvido com evidência.
2. **A2 (obrigatório)** — `error_codes` (~contracts.py:807) aceita strings arbitrárias; restrinja aos códigos tipados do contrato (enum `ErrorCode` dos 12 do §4, já canônico após a dedupe da 003) e adicione teste de rejeição/aceitação; o JSON Schema correspondente deve sair com `enum`.
3. **A3–A6 (aproveite se de baixo custo, sem expandir escopo)** — A3: garantir que a decisão de permissão não leia papel alegado no payload (ou ajustar o teste `test_payload_external_sender_role_does_not_grant_permission` para papel ALEGADO privilegiado, ex. `monitor`, e documentar a garantia definitiva como responsabilidade do dispatcher na task 014); A4: `max_length` em `timezone`; A5: rotular `EnvelopeStatus` e `MemoryPack.EventKind` como defaults de ensaio nos docstrings (como em `OperationAction`); A6: declarar `jsonschema` no grupo `dev` do `pyproject.toml` com `uv lock` real.
4. Regenerar schemas (`python -m eduagent.contracts --export schemas`) e confirmar byte a byte; suíte verde completa.

Restrições: preservar a entrega da 003 (sem reverter); commits SEPARADOS — (1) entrega (código + schemas + testes + lock), (2) registro (task.md com SHAs e evidências); sem amend/force-push/commits vazios; mapa, plano e submodule `docs/playground-llmagenticsystem` intocados; temporários em `/tmp/opencode`; sem push; nada apresentado como resultado medido.

## Contexto
- `eduagent/contracts.py` — entrega da 003 a corrigir (procurar `StudyDemand`, `error_codes`, `TOOL_PERMISSIONS`, `EnvelopeStatus`, `EventKind`).
- `tests/test_task003_contracts.py` — suíte existente (61 testes) a estender.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §4 (tabela), §8, §15.3; NÃO modificar.
- `schemas/` — regenerar após alterações (`--export`/`--check`).

## Corretude
- [ ] C1 — Regra de `StudyDemand` verificada contra §4/§15.3/§8 com citação exata no task.md: validador implementado com testes de rejeição/aceitação OU leitura normativa contrária documentada com evidência; probe do revisor (mandatory=True + estimated) reproduz o comportamento corrigido/justificado.
- [ ] C2 — `error_codes` restrito ao enum tipado, com teste e JSON Schema contendo `enum`; suíte completa verde (`pytest tests/ -q`).
- [ ] C3 — Schemas regenerados e byte a byte (`--check`); itens A3–A6 aproveitados registrados item a item (feito/não aplicável com motivo) no task.md.
- [ ] C4 — Mapa, plano e submodule intocados; commits de entrega e registro separados; entrega da 003 preservada (sem reversão).

## Execução
- Modelo: <identificador real do executor>
- Base: <SHA completo antes da implementação>
- Entrega: <SHA(s) completos, sem commits de registro, ou sem alteração de artefatos>
- Arquivos da entrega: <paths ou referência ao diff dos commits>
- Evidências: <comandos/procedimentos, resultados e limitações>

## Notas

### Dificuldade esperada
2/10 — Correção pontual com verificação normativa; o único cuidado real é a leitura exata de §4/§15.3/§8 para A1 e a regeneração determinística dos schemas.

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
