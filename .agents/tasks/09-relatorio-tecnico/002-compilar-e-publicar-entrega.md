# Task 002: Compilar e publicar a entrega do relatório

Estado: pendente
Depende de: 001
Origem: nenhuma

## Prompt
Compilar e publicar a entrega da fase 2 com `python3 fase2/scripts/gerar_entrega.py`: o script valida os documentos, roda `pdflatex → bibtex → pdflatex → pdflatex`, rejeita citações/referências indefinidas e overfull boxes, valida CRCs de ZIP e SHA-256, e sobrescreve ambos os PDFs da fase 2, `verificacao_documental.json`, `SHA256SUMS.txt` e o ZIP. Pré-requisitos: `/tmp/opencode/` existente, `pdflatex`, `bibtex` e os pacotes TeX listados em `fase2/README-entrega.md` (conferir antes; sem instalar LangChain). Após o build: conferir que os artefatos regenerados estão íntegros (SHA-256 válidos, ZIP com CRCs ok) e que o PDF não contém "??"/referências indefinidas. Se não houver alteração pendente de publicação desde a última entrega íntegra, registrar isso e NÃO reconstruir desnecessariamente (decisão explícita com `git status` e comparação de hashes como evidência).

Restrições: compilação/integridade documental são verificações desta entrega, distintas dos experimentos futuros; não executar experimentos nem apresentar metas como resultados; `fase2_metodologia.tex` só muda se a task 001 o alterou; prosa em português; commit de entrega (artefatos regenerados, quando houver) e commit de registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/scripts/gerar_entrega.py` — script de compilação/publicação (valida antes de compilar).
- `fase2/README-entrega.md` — pré-requisitos do build (pdflatex, bibtex, pacotes TeX).
- `fase2/fase2_metodologia.tex` — fonte (saída da task 001).
- `fase2/SHA256SUMS.txt` e `fase2/eduagent_fase2_entrega.zip` — artefatos de integridade regenerados/validados.

## Corretude
- [ ] C1 — `python3 fase2/scripts/gerar_entrega.py` conclui sem citações/referências indefinidas e sem overfull boxes (ou reconstrução dispensada com evidência de que nada mudou).
- [ ] C2 — Artefatos de entrega regenerados íntegros: PDFs, `verificacao_documental.json`, `SHA256SUMS.txt` e ZIP com CRCs/SHA-256 válidos; PDF sem referências indefinidas visíveis.
- [ ] C3 — Commits entrega/registro separados; nenhum experimento executado nem resultado apresentado como medido; ambiente conforme `README-entrega.md`.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
4/10 — Build mecânico quando o ambiente está completo; o risco é falta de pacote TeX ou `/tmp/opencode/` ausente, e a tentação de "consertar" erros de compilação mexendo no conteúdo normativo.

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
