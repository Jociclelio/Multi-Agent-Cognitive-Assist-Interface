# Plano: Relatório técnico da fase 2 — manutenção, compilação e entrega

Estado: rascunho

## Objetivo
Manter, compilar e entregar o relatório científico da fase 2 (`fase2/fase2_metodologia.tex` → `fase2_metodologia.pdf`), garantindo que o texto siga o template, as convenções de citação e que a entrega publicada (PDFs, verificação documental, SHA256, ZIP) esteja íntegra e sincronizada com o fonte.

## Abordagem
1. Editar `fase2/fase2_metodologia.tex` conforme necessário, preservando a estrutura do template: capa, geometria, corpo 12pt, rodapé e as seções mapeadas (Visão Geral da Metodologia; Conjunto de Dados para a Avaliação; Arquitetura Multiagente; Orquestração e Uso de Ferramentas; Procedimentos de Avaliação; Apêndice; Referências). A figura permanece TikZ, sem imagens externas.
2. Regras de citação/bibliografia: usar `\cite{...}` ou `\citeonline{...}` no corpo (nunca `\citep`/`\citet`), manter exatamente um `\bibliography{references}` e chaves únicas, case-sensitive, em `fase2/references.bib`. O estilo é `aasjournal` se disponível, senão `plainnat` (autor–ano).
3. Validação documental focada: `python3 fase2/scripts/verificar_documentos.py` e, quando pertinente, `--check-delivery`.
4. Compilação/publicação: `python3 fase2/scripts/gerar_entrega.py` (valida, roda pdflatex → bibtex → pdflatex → pdflatex, rejeita citações/referências indefinidas e overfull boxes, valida CRCs de ZIP e SHA-256, e sobrescreve os PDFs da fase 2, `verificacao_documental.json`, `SHA256SUMS.txt` e o ZIP).
5. Manter a fidelidade do conteúdo: parâmetros e gates do relatório são propostas metodológicas, não resultados de execução do EduAgent-OS; seleção de hardware/runtime, autorização/anotação de dados e piloto de calibração ainda não foram realizados. Não apresentar metas como resultados medidos.
6. Manter prose acadêmica em português; commit com mensagem concisa e orientada a ação.

## Escopo
- Entrega: fonte `.tex` atualizado (se houver mudança) e relatório compilado/publicado via `gerar_entrega.py`, com PDFs, `verificacao_documental.json`, `SHA256SUMS.txt` e ZIP regenerados.
- Limites: a compilação e a integridade documental são verificações desta entrega, distintas dos experimentos futuros do sistema; não executar experimentos nem instalar LangChain (a entrega só exige `/tmp/opencode/`, `pdflatex`, `bibtex` e os pacotes TeX listados em `fase2/README-entrega.md`).
- O documento de auditoria da etapa 10 registra o alcance de verificação das referências; não duplicar essa auditoria aqui.

## Contexto
- `fase2/documentos/09_relatorio_tecnico.md` — documento-fonte desta etapa; índice do relatório.
- `fase2/fase2_metodologia.tex` — fonte LaTeX do relatório (objeto da manutenção).
- `fase2/references.bib` — bibliografia (chaves únicas, case-sensitive).
- `fase2/template-fase2.tex` — referência de capa, geometria, corpo 12pt, rodapé e seções.
- `fase2/scripts/gerar_entrega.py` — script de compilação/publicação da entrega.
- `fase2/scripts/verificar_documentos.py` — verificação documental focada.
- `fase2/README-entrega.md` — pré-requisitos do build (pdflatex, bibtex, pacotes TeX).
- `fase2/documentos/11_indice_da_entrega.md` — índice dos entregáveis da fase 2.

## Critérios de conclusão
- `python3 fase2/scripts/verificar_documentos.py` passa sem erros.
- `python3 fase2/scripts/gerar_entrega.py` conclui: sem citações/referências indefinidas, sem overfull boxes, CRCs de ZIP e SHA-256 válidos, artefatos de entrega regenerados.
- `fase2_metodologia.tex` usa apenas `\cite`/`\citeonline`, com exatamente um `\bibliography{references}` e chaves únicas em `references.bib`.
- O texto não apresenta parâmetros/gates propostos como resultados medidos.

## Questões abertas
Nenhuma essencial. Observação: o estilo `aasjournal` pode não estar disponível no ambiente; nesse caso o fallback documentado é `plainnat` (autor–ano).

## Tasks
<A preencher pelo task-writer.>
