# Task 001: Conferir o fonte LaTeX do relatório e a verificação documental

Estado: pendente
Depende de: nenhuma
Origem: nenhuma

## Prompt
Conferir/manter `fase2/fase2_metodologia.tex` conforme o plano: (1) estrutura do template preservada (capa, geometria, corpo 12pt, rodapé; seções Visão Geral da Metodologia, Conjunto de Dados para a Avaliação, Arquitetura Multiagente, Orquestração e Uso de Ferramentas, Procedimentos de Avaliação, Apêndice, Referências) contra `fase2/template-fase2.tex`; figura permanece TikZ, sem imagens externas. (2) Regras de citação: apenas `\cite{...}`/`\citeonline{...}` no corpo (nunca `\citep`/`\citet`), exatamente um `\bibliography{references}`, chaves únicas e case-sensitive em `fase2/references.bib`, estilo condicional (`aasjournal` se disponível, senão `plainnat`). (3) Fidelidade de conteúdo: parâmetros e gates são propostas metodológicas, não resultados de execução do EduAgent-OS; seleção de hardware/runtime, autorização/anotação de dados e piloto de calibração declarados como não realizados; nada apresentado como resultado medido. (4) Rodar `python3 fase2/scripts/verificar_documentos.py` (e `--check-delivery` quando pertinente). Correções apenas em dif mínimo com justificativa; a auditoria fina das referências é da etapa 10 (não duplicar).

Restrições: documentos das etapas 1–8 e `fase2/references.bib` fora do escopo de reescrita (correção de chave faltante só em conjunto com a etapa 10/problema mecânico, com justificativa); prosa acadêmica em português preservada; commit de entrega (se houver alteração do `.tex`) e commit de registro separados; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/fase2_metodologia.tex` — fonte LaTeX do relatório (objeto da manutenção).
- `fase2/template-fase2.tex` — referência de estrutura do template.
- `fase2/references.bib` — bibliografia (chaves únicas, case-sensitive).
- `fase2/scripts/verificar_documentos.py` — verificação documental focada.
- `fase2/documentos/09_relatorio_tecnico.md` — índice do relatório (documento-fonte da etapa).

## Corretude
- [ ] C1 — Estrutura do template preservada e alinhada a `template-fase2.tex`; figura em TikZ; prosa acadêmica em português.
- [ ] C2 — Apenas `\cite`/`\citeonline`, exatamente um `\bibliography{references}`, chaves únicas case-sensitive; estilo condicional declarado.
- [ ] C3 — Nenhum parâmetro/gate apresentado como resultado medido; pendências (hardware, dados, piloto) declaradas como não realizadas; `python3 fase2/scripts/verificar_documentos.py` passa.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
3/10 — Manutenção/conferência de LaTeX existente; o risco é "melhorar" texto normativo em dif extenso ou deixar um `\citep` remanescente.

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

Plano: [plan.md](../../plans/09-relatorio-tecnico/plan.md)
