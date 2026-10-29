# Task 002: Validar bibliografias novas, reutilização de chaves e deduplicação

Estado: pendente
Depende de: 001
Origem: nenhuma

## Prompt
Conferir o estado bibliográfico da etapa 7: (1) as referências novas da pesquisa estão em `fase2/pesquisa/references_avaliacao_qualidade.bib` e `fase2/pesquisa/references_robustez.bib` e toda citação do documento 07 tem entrada rastreável; (2) chaves reutilizadas de bibliografias anteriores (`references_arquitetura.bib`, `references_pedagogia.bib`) não são contadas como evidência independente nos relatórios/documento (registro de reuso presente); (3) a duplicata `zheng2023judge` está removida da bibliografia consolidada `fase2/references.bib`, prevalecendo a entrada de `references_avaliacao_qualidade.bib` (com DOI e `primaryClass`); (4) chaves únicas e case-sensitive em todos os `.bib` envolvidos, sem entradas órfãs citadas sem entrada no `.tex` (a auditoria fina de identidade é da etapa 10 — aqui confere-se deduplicação e unicidade, não o parecer por chave). Correção (se necessária) em dif mínimo no arquivo afetado, com justificativa.

Restrições: relatórios `07a`/`07b` e documentos das etapas 1–6 INTOCADOS; edição restrita aos `.bib` e, se indispensável, ao documento 07 em dif mínimo; prosa em português; `python3 fase2/scripts/verificar_documentos.py` deve passar ao final (inclui unicidade case-sensitive de chaves); commits de entrega e registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/pesquisa/references_avaliacao_qualidade.bib` e `fase2/pesquisa/references_robustez.bib` — bibliografias novas da pesquisa 7 (entradas de origem).
- `fase2/pesquisa/references_arquitetura.bib` e `fase2/pesquisa/references_pedagogia.bib` — bibliografias anteriores (chaves reutilizadas).
- `fase2/references.bib` — bibliografia consolidada do relatório (duplicata `zheng2023judge` removida).
- `fase2/documentos/07_metodologias_de_testagem.md` — citações do documento 07 (cobertura de entrada).
- `fase2/scripts/verificar_documentos.py` — verificação de chaves únicas case-sensitive.

## Corretude
- [ ] C1 — Toda citação do documento 07 tem entrada rastreável nos `.bib` de origem; referências novas presentes nos dois arquivos dedicados.
- [ ] C2 — `zheng2023judge` aparece uma única vez na consolidada, com a entrada de `references_avaliacao_qualidade.bib` (DOI e `primaryClass`); reuso de chaves antigas registrado como não-evidência-independente.
- [ ] C3 — Chaves únicas e case-sensitive em todos os `.bib`; verificador passa ao final; correções em dif mínimo com justificativa.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
3/10 — Conferência bibliográfica mecânica; o risco é confundir duplicata de chave com entrada legítima de obra distinta com chave parecida.

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

Plano: [plan.md](../../plans/07-metodologias-de-testagem/plan.md)
