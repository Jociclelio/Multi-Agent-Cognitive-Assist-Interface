# Task 002: Validar a consolidação do references.bib

Estado: pendente
Depende de: 001
Origem: nenhuma

## Prompt
Validar `fase2/references.bib` consolidado contra as regras do plano: (1) **Deduplicação** — mesma obra em arquivos distintos vira uma única chave, mantendo a entrada mais completa (`zheng2023judge`: prevalece a de `references_avaliacao_qualidade.bib`, com DOI e `primaryClass`); sem entradas para páginas auxiliares, APIs, HTML do mesmo artigo ou documentação reconsultada. (2) **Datas** — `year = {s.d.}` com `note = {Acesso em 30/09/2026}` e `urldate` ISO onde não há data editorial verificada (15 entradas); não converter `s.d.` em publicação de 2026; anos de documentação com data explícita preservados (CP-SAT 2024, SQLite WAL 2026, MCP 2025 = especificação 2025-11-25); ano de publicação/preprint vs. revisão arXiv consultada distinguidos em nota (MemGPT 2023/v2 2024; M3 2024/v5 2025; MetaGPT v7 2024; LongMemEval ICLR 2025; AgentBench ICLR 2024; RAGAs EACL 2024). (3) **Estrutura BibTeX** — adequações ao estilo efetivo (`lakens2022inferences` como `@misc` com `howpublished`, pois `plainnat` exige `publisher` em `@book`; sem fabricar editora). (4) **Notas e escaping** — sem notas extensas de auditoria/bloqueios; URLs exclusivamente no campo `url` com underscores literais (sem `\_`); escape de underscore só em texto TeX de título; DOI em campo `doi`; grafia original conservada ("Heterogenous" de BEIR). (5) **Cobertura** — 56 fontes únicas, incluindo as 12 não citadas preservadas sem geração de citação nem `\nocite{*}`; zero citações sem entrada. Correção em dif mínimo com justificativa.

Restrições: edição restrita a `fase2/references.bib` e, se indispensável, ao relatório 10 em dif mínimo; `.tex` e pesquisas intocados; chaves únicas e case-sensitive; prosa em português; `python3 fase2/scripts/verificar_documentos.py` deve passar ao final; commits entrega/registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/references.bib` — bibliografia consolidada (objeto da validação).
- `fase2/pesquisa/references_arquitetura.bib`, `references_pedagogia.bib`, `references_avaliacao_qualidade.bib`, `references_robustez.bib` — bibliografias de origem da consolidação.
- `fase2/documentos/10_auditoria_de_referencias.md` — regras de consolidação e inventário (documento-fonte).
- `fase2/scripts/verificar_documentos.py` — verificação de unicidade case-sensitive de chaves.

## Corretude
- [ ] C1 — Deduplicação correta (uma obra = uma chave; `zheng2023judge` única com a entrada completa); sem entradas auxiliares/APIs/HTML.
- [ ] C2 — Datas conforme regras (15 `s.d.` com note/urldate; distinções de versão em nota; nenhum `s.d.` convertido em 2026); estrutura BibTeX adequada ao estilo efetivo.
- [ ] C3 — URLs em campo `url` com underscores literais, DOI em `doi`, grafia original conservada; cobertura 56 fontes (12 não citadas preservadas, sem `\nocite{*}`); chaves únicas case-sensitive e verificador passando.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
4/10 — Conferência mecânica contra regras explícitas; o risco é "corrigir" a grafia original de um título ou converter `s.d.` em ano editorial.

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

### Revisão
- Orquestrador: —
- Alvo: —
- Avaliações: <modelo A: _/10; modelo B: _/10; modelo C: _/10>
- Nota final: _/10
- Parecer: —
- Decisão: —
- Reversão: —
- Próximo passo: —

Plano: [plan.md](../../plans/10-auditoria-de-referencias/plan.md)
