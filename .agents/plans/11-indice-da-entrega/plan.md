# Plano: Manutenção do índice e pacote de entrega da fase 2

Estado: rascunho

## Objetivo
Manter o pacote de entrega da fase 2 íntegro e sincronizado: o índice (`11_indice_da_entrega.md`) refletindo os documentos atuais, a entrega regenerável/empacotável de forma reprodutível e os checksums conferíveis.

## Abordagem
1. Conferir se o índice lista corretamente os documentos das etapas 1–11, com links relativos válidos (`fase2/documentos/`, `fase2/pesquisa/`, relatório LaTeX/PDF, `references.bib`, `README-entrega.md`).
2. Rodar a verificação documental focada: `python3 fase2/scripts/verificar_documentos.py`.
3. Para confirmar a existência dos arquivos de entrega linkados (os dois PDFs e o ZIP — é isso que a flag faz; ela não checa `verificacao_documental.json` nem checksums): `python3 fase2/scripts/verificar_documentos.py --check-delivery`.
4. Conferir checksums da entrega já existente em disco: `sha256sum -c fase2/SHA256SUMS.txt` a partir da raiz (opcionalmente, comparar também o `SHA256SUMS.txt` embutido no ZIP com a cópia em `fase2/`).
5. Se documentos ou a entrega mudarem, regenerar/publicar com `python3 fase2/scripts/gerar_entrega.py` (valida antes; roda `pdflatex -> bibtex -> pdflatex -> pdflatex`; rejeita citações/referências indefinidas e overfull boxes; valida CRCs de ZIP e SHA-256). O script sobrescreve ambos os PDFs da fase 2, `verificacao_documental.json`, `SHA256SUMS.txt` e o ZIP.
6. Atualizar o índice apenas se a lista de arquivos ou a estrutura do pacote mudar, preservando a prosa acadêmica em português.

## Escopo
- Inclui: sincronização do índice `11_indice_da_entrega.md`; execução da verificação documental; regeneração/empacotamento da entrega quando necessário; conferência de checksums.
- Não inclui: alteração de conteúdo científico dos mapas/pesquisas; verificação de frescor de PDFs além do que o script faz; integração com Google Drive (inexistente por decisão registrada); nada em `docs/` (a regra de kebab-case sem prefixos numéricos vale só para materiais de curso em `docs/`, não para os documentos numerados de `fase2/documentos/`).

## Contexto
- `fase2/documentos/11_indice_da_entrega.md` — documento-fonte: índice das etapas 1–11, ordem de leitura recomendada (mapas 4 e 8 como entradas normativas), e instruções de acesso/reprodução (ZIP + `SHA256SUMS.txt`, sem credenciais/dados privados).
- `fase2/scripts/verificar_documentos.py` — verificação documental focada (citations, seções obrigatórias, IDs, arquivos de etapa, links locais); `--check-delivery` adiciona apenas a checagem de existência dos arquivos de entrega linkados (PDFs e ZIP).
- `fase2/scripts/gerar_entrega.py` — rebuild/publicação da entrega; requer `/tmp/opencode/`, `pdflatex`, `bibtex` e os pacotes TeX listados em `fase2/README-entrega.md`; sobrescreve PDFs, `verificacao_documental.json`, `SHA256SUMS.txt` e o ZIP (ZIPs são Git-ignorados).
- `fase2/README-entrega.md` — guia da entrega e requisitos do ambiente de compilação.

## Critérios de conclusão
- `python3 fase2/scripts/verificar_documentos.py` executa sem erros a partir da raiz.
- `python3 fase2/scripts/verificar_documentos.py --check-delivery` confirma a existência dos arquivos de entrega linkados (não checa `verificacao_documental.json`, checksums nem frescor de PDFs).
- `sha256sum -c fase2/SHA256SUMS.txt` executa sem falhas a partir da raiz.
- Se houve regeneração: `gerar_entrega.py` conclui sem citações/referências indefinidas nem overfull boxes, e `SHA256SUMS.txt`/ZIP resultantes passam na validação do próprio script.
- O índice lista as 11 etapas com links relativos funcionais, alinhado ao conteúdo real de `fase2/`.

## Questões abertas
- Nenhuma essencial. Observação: a verificação mecânica (`verificacao_documental.json`) não substitui leitura científica, já realizada na elaboração/auditoria; pendências de conteúdo científico estariam fora do escopo deste plano.

## Tasks
<A preencher pelo task-writer.>
