# Task 003: Validar regras LaTeX, compilação e fechar a etapa 10

Estado: pendente
Depende de: 002
Origem: nenhuma

## Prompt
Fechar a etapa 10: (1) Validar as regras LaTeX em `fase2/fase2_metodologia.tex`: `natbib` com `[authoryear,round]`; `\cite` = `citep` (parentética) e `\citeonline` = `citet` (narrativa); chaves preservadas exatamente, inclusive maiúsculas (`jiwerQuality`, `bfclMultiTurn`, `hypothesisStateful`, `scipyBootstrap`); exatamente um `\bibliography{references}`; estilo condicional (`aasjournal` se disponível, `plainnat` como fallback — ausência do `.bst` no ambiente é questão aberta registrada, não erro). (2) Conferir que a compilação via `python3 fase2/scripts/gerar_entrega.py` não produz citações/referências indefinidas nem overfull boxes (executar somente se houver alteração pendente de publicação; caso contrário, registrar a dispensa com evidência). (3) Consolidar a etapa na task: resultado das conferências 001–002, questões abertas herdadas (fallback `plainnat` vs. providenciar `aasjournal.bst`; SHA-256 do modelo Bonsai e setups/demos citados permanecem pendências fora do escopo). (4) Rodar `python3 fase2/scripts/verificar_documentos.py` (e `--check-delivery` quando pertinente).

Restrições: `.tex` INTOCADO nesta task (regras são conferidas, não editadas — correção só se a conferência revelar violação, em dif mínimo com justificativa); pesquisas e documentos 1–9 intocados; nada apresentado como resultado medido; prosa em português; commits entrega/registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/fase2_metodologia.tex` — regras de citação/estilo a conferir (auditado, não editado por padrão).
- `fase2/references.bib` — consolidado validado na task 002.
- `fase2/scripts/gerar_entrega.py` — compilação com rejeição de indefinidas/overfull.
- `fase2/documentos/10_auditoria_de_referencias.md` — fechamento da auditoria e questões abertas.
- `fase2/scripts/verificar_documentos.py` — verificação documental.

## Corretude
- [ ] C1 — Regras LaTeX conferidas (natbib authoryear/round, `\cite`/`\citeonline`, chaves case-sensitive preservadas, um `\bibliography{references}`, estilo condicional); violação (se houver) corrigida em dif mínimo com justificativa.
- [ ] C2 — Compilação sem citações/referências indefinidas nem overfull boxes, ou dispensa registrada com evidência (sem alteração pendente).
- [ ] C3 — Consolidação da etapa registrada com questões abertas herdadas; `python3 fase2/scripts/verificar_documentos.py` passa; commits entrega/registro separados.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
3/10 — Conferência de regras declaradas com build existente; o risco é editar o `.tex` sem necessidade ou reconstruir a entrega sem alteração pendente.

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
