# Task 003: Contratos Pydantic, envelope e erros tipados (mapa §4)

Estado: pendente
Depende de: 002
Origem: nenhuma

## Prompt
Implementar em `eduagent/contracts.py` (e módulos afins) todos os contratos do mapa §4 com Pydantic estrito (`extra='forbid'`, enums, IDs UUID, datetimes ISO-8601 com zona/UTC, tamanhos limitados, datas parciais com tipo específico — sem coerção para datetime; campos `*_ref` com ID+versão, nunca caminho produzido por LLM): `SourceRef`, `AcademicFact`, `EvidencePack`, `MemoryPack`, `LearningItem`, `TutorTurn`, `Assessment`, `TopicState`, `StudyDemand`, `ScheduleProposal`, `Operation` — campos e invariantes exatamente como a tabela do §4. Implementar o envelope comum (`schema_version`, `task_id`, `trace_id`, `parent_task_id`, `sender_role`, `artifact_type`, `snapshot_version`, `source_refs`, `payload_ref`, `status`, `error`), o estado do grafo (campos do §4) e os erros tipados (`SCHEMA_INVALID`, `SOURCE_UNRESOLVED`, `AMBIGUOUS_INPUT`, `VERSION_CONFLICT`, `TOOL_DENIED`, `MODEL_NOT_ADMITTED`, `NO_EVIDENCE`, `RESOURCE_LIMIT`, `TIMEOUT`, `UNKNOWN_EFFECT`, `CANCELLED`, `INTERNAL_FAILURE`), cada um com mensagem ao usuário, retryability e referência de diagnóstico local. Payload externo não muda papel/permissões. Exportar os JSON Schemas para `schemas/` como parte do build.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §4 integral (tabela de artefatos, envelope, estado, erros).
- `eduagent/contracts.py` (stub da task 001).

## Corretude
- [ ] C1 — Todos os 11 tipos da tabela §4 implementados com os campos/invariantes listados; validação rejeita extra fields, datas ingênuas e `*_ref` com caminho.
- [ ] C2 — Envelope e estado do grafo conforme §4; os 12 erros tipados existem com retryability e mensagem.
- [ ] C3 — JSON Schemas exportados em `schemas/` e regeneráveis pelo build; teste mínimo de round-trip (instância válida → schema → valida).
- [ ] C4 — Mapa intocado; commits separados; submódulo não tocado.

## Notas

### Dificuldade esperada
4/10 — Muitos contratos com invariantes finos (spans, confirmações, supersedes); risco de omissão de campo.

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
