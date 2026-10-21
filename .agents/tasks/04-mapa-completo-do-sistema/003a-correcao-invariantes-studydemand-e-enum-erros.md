# Task 003a: Correção dos invariantes de `StudyDemand` e enum de `error_codes` (mapa §4)

Estado: aguardando revisão
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
- [x] C1 — Regra de `StudyDemand` verificada contra §4/§15.3/§8 com citação exata no task.md: validador implementado com testes de rejeição/aceitação OU leitura normativa contrária documentada com evidência; probe do revisor (mandatory=True + estimated) reproduz o comportamento corrigido/justificado.
- [x] C2 — `error_codes` restrito ao enum tipado, com teste e JSON Schema contendo `enum`; suíte completa verde (`pytest tests/ -q`).
- [x] C3 — Schemas regenerados e byte a byte (`--check`); itens A3–A6 aproveitados registrados item a item (feito/não aplicável com motivo) no task.md.
- [x] C4 — Mapa, plano e submodule intocados; commits de entrega e registro separados; entrega da 003 preservada (sem reversão).

## Execução
- Modelo: GLM-5.3-Flash (via ~/sd2-llm.sh; provider `sd2`, model `GLM-5.3-Flash`)
- Base: 860942f3bc3f05396098cf2cb5d5d3a2252709dd (árvore limpa; entrega da 003 `82bac2dd3600967358f1db42154913a3c7375834` preservada)
- Entrega: b0de70c40cfc73bb1554763d845c4e6d2e98aeb8
- Arquivos da entrega: `eduagent/contracts.py`, `tests/test_task003_contracts.py`, `pyproject.toml`, `uv.lock`, `schemas/{AcademicFact,Envelope,MemoryPack,TopicState}.schema.json` (diff do commit de entrega)
- Evidências:
  - **A1 (obrigatório) — leitura normativa e validador implementado.** Mapa §4, tabela (linha 87 de `04_mapa_completo_do_sistema.md`): "`StudyDemand` | … duration_status `confirmed/estimated`; **restrição dura exige confirmação**". §15.3 (linha 266): "**rótulo estimated e mandatory=false**. Usuário pode editar e confirmar para obrigatória. Não converter percentual de domínio em duração." §8 (linha 158, replanejamento): "a duração recomendada é explicitamente estimada e **confirmada quando virar obrigatória** … **não converter incerteza em obrigação**." A regra se aplica: `mandatory=True ⇒ duration_status="confirmed"`. Implementado `model_validator` `_mandatory_requires_confirmed` em `StudyDemand` (`eduagent/contracts.py`); teste `test_mandatory_study_demand_requires_confirmed_duration` (aceitação: estimada+opcional e confirmada+obrigatória; rejeição: obrigatória+estimated). Probe do revisor reproduzido fora da suíte: payload com `mandatory=True, duration_status="estimated"` é rejeitado com "demanda obrigatória (mandatory=true) exige duration_status='confirmed'".
  - **A2 (obrigatório).** `TopicState.error_codes` mudou de `list[_ShortId]` para `list[ErrorCode]` (12 códigos canônicos do §4, já deduplicados na 003). Teste `test_topic_state_error_codes_restricted_to_typed_enum`: aceita `["TIMEOUT","NO_EVIDENCE"]`, rejeita `["ERRO_INVENTADO"]` e verifica `enum` fechado no JSON Schema (`$defs.ErrorCode.enum == {os 12 valores}`). Schema `TopicState.schema.json` (e `MemoryPack.schema.json`, que inclui `TopicState`) agora sai com `"$ref": "#/$defs/ErrorCode"` + `enum`.
  - **A3 — aproveitado (opção teste ajustado).** `test_payload_external_sender_role_does_not_grant_permission` reescrito: payload externo com papel ALEGADO privilegiado (`monitor`, permitido para `assessment.check`) é aceito como dado (`ToolRequest`), e a decisão é avaliada contra o papel atribuído pelo dispatcher (`TUTOR`) → negado com `TOOL_DENIED`; papel legítimo (`MONITOR`) passa. Garantia definitiva do descarte do papel alegado na fronteira documentada como responsabilidade do dispatcher na task 014 (docstring de `validate_tool_request` e do teste).
  - **A4 — aproveitado.** `max_length=100` (default de ensaio, não resultado medido) no campo `timezone` de `AcademicFact`; refletido como `maxLength` no schema.
  - **A5 — aproveitado.** `EnvelopeStatus` e `MemoryPack.EventKind` rotulados como catálogo default de ensaio nos docstrings (padrão de `OperationAction`); apareceram como `description` nos schemas.
  - **A6 — aproveitado.** `jsonschema>=4,<5` declarado no grupo `dev` do `pyproject.toml`; `uv lock` real executado (`uv.lock` atualizado, 170 packages resolvidos).
  - **Schemas:** `.venv/bin/python -m eduagent.contracts --export schemas` regenerado e `--check` confirmou byte a byte ("schemas/ atualizado: schemas"). Diff dos schemas conferido manualmente: apenas as mudanças esperadas (maxLength/enum/ref/descriptions).
  - **Suíte:** `.venv/bin/python -m pytest tests/ -q` → **63 passed** (61 da 003 + 2 novos), 0.27s.
  - **Intocados:** `fase2/documentos/04_mapa_completo_do_sistema.md`, `.agents/plans/04-mapa-completo-do-sistema/plan.md` e submodule `docs/playground-llmagenticsystem` sem alteração (`git status` limpo fora dos arquivos da entrega).
  - Limitações: verificação contratual local; nenhum experimento executado, nada medido. Defaults numéricos (max_length=100 etc.) são escolhas de ensaio.

## Notas

### Dificuldade esperada
2/10 — Correção pontual com verificação normativa; o único cuidado real é a leitura exata de §4/§15.3/§8 para A1 e a regeneração determinística dos schemas.

### Dificuldade sentida
2/10 — Correção delimitada e bem especificada; o único cuidado extra foi conferir a seção exata de cada citação normativa (§4 linha 87, §8 linha 158, §15.3 linha 266) antes de fixar o validador, e validar que a mudança de `error_codes` para o enum produziu `enum` no JSON Schema sem efeitos colaterais (MemoryPack inclui TopicState e mudou junto, como esperado).

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
