# Task 006: Ingestão, OCR seletivo, proveniência e fatos candidatos (mapa §6.1–3, §13.3)

Estado: pendente
Depende de: 005
Origem: nenhuma

## Prompt
Implementar a ingestão do Curador (mapa §6 itens 1–3) em `eduagent/services/ingestion.py` e `eduagent/agents/curator.py` com a ferramenta `document.extract`: (1) validar ownership, MIME por bytes, limites (50 MiB/500 páginas/600 s/subprocesso 4 GiB) e path canônico; arquivar original e SHA; duplicata exata reaproveita bytes preservando vínculos por disciplina; nova versão não ativa antes da indexação completa. (2) Docling produz blocos ordenados, tabelas e proveniência; páginas vazias/ruidosas diagnosticadas; OCR seletivo `por`/`por+eng` com derivado separado e reextração do documento inteiro; equações/tabelas não legíveis ficam pendentes; nunca usar apenas sidecar OCR como texto total; progresso por página; job cancelável; versão incompleta nunca vira ativa. (3) Curador extrai tópicos e fatos candidatos por schema (contratos da 003); validar datas/números com texto de origem; datas relativas usam data da fala e zona confirmada; PDD confirmado tem prioridade, mas revisão gera conflito a reconciliar; prazo só de dia não ganha horário automático; detectar ciclos de pré-requisito; o usuário confirma ou corrige a tabela extraída (`status candidate/ambiguous/confirmed/rejected`; confirmado exige confirmação ou entrada direta inequívoca do usuário).

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §6.1–3; §13.3; tabela de ferramentas §10 (`document.extract`).
- Storage (004), contratos (003), config de limites (001).

## Corretude
- [ ] C1 — Ingestão valida MIME por bytes e limites; oversized é recusado ou dividido pelo usuário; duplicata reaproveita bytes; versão só ativa após indexação completa.
- [ ] C2 — Blocos/tabelas com proveniência e diagnóstico de páginas; OCR seletivo gera derivado separado; sidecar nunca é texto total.
- [ ] C3 — Fatos candidatos seguem `AcademicFact`; datas/números validados contra origem; ciclos de pré-requisito detectados; confirmação do usuário registrada em `confirmations`.
- [ ] C4 — Mapa intocado; commits separados; temporários em `/tmp/opencode`; submódulo não tocado.

## Notas

### Dificuldade esperada
5/10 — Integração Docling/OCR com proveniência; risco em edge cases de datas relativas e duplicatas.

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
