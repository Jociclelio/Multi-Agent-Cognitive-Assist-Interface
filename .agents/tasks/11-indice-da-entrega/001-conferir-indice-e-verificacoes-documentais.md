# Task 001: Conferir o índice da entrega e rodar as verificações

Estado: pendente
Depende de: nenhuma
Origem: nenhuma

## Prompt
Conferir a sincronização do pacote de entrega: (1) Validar `fase2/documentos/11_indice_da_entrega.md` contra o conteúdo real de `fase2/` — as 11 etapas listadas com links relativos válidos (`fase2/documentos/`, `fase2/pesquisa/`, relatório LaTeX/PDF, `references.bib`, `README-entrega.md`), ordem de leitura recomendada preservada (mapas 4 e 8 como entradas normativas) e instruções de acesso/reprodução (ZIP + `SHA256SUMS.txt`, sem credenciais/dados privados). (2) Rodar `python3 fase2/scripts/verificar_documentos.py` a partir da raiz. (3) Rodar `python3 fase2/scripts/verificar_documentos.py --check-delivery` (confirma apenas existência dos arquivos de entrega linkados — os dois PDFs e o ZIP; NÃO checa `verificacao_documental.json` nem checksums). (4) Conferir checksums: `sha256sum -c fase2/SHA256SUMS.txt` a partir da raiz (o arquivo cobre o conteúdo extraído, não o ZIP — integridade do ZIP por CRC; opcionalmente comparar o `SHA256SUMS.txt` embutido no ZIP com a cópia em `fase2/`). Ajuste no índice somente se a conferência revelar desvio, em dif mínimo com justificativa, preservando a prosa acadêmica em português.

Restrições: nenhum conteúdo científico de mapas/pesquisas alterado; nada em `docs/` (regra de kebab-case vale só para materiais de curso); integração com Google Drive inexistente por decisão registrada (não criar); nada apresentado como resultado medido; commits entrega/registro separados; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/11_indice_da_entrega.md` — índice das etapas 1–11 (objeto da conferência).
- `fase2/scripts/verificar_documentos.py` — verificação documental; `--check-delivery` adiciona existência de PDFs e ZIP.
- `fase2/SHA256SUMS.txt` — checksums do conteúdo extraído da entrega.
- `fase2/README-entrega.md` — guia da entrega.

## Corretude
- [ ] C1 — Índice lista as 11 etapas com links relativos funcionais, alinhado ao conteúdo real de `fase2/` (arquivos existentes, nomes corretos); desvios corrigidos em dif mínimo ou justificados.
- [ ] C2 — `verificar_documentos.py` passa sem erros e `--check-delivery` confirma a existência dos arquivos de entrega linkados (com a limitação da flag corretamente entendida).
- [ ] C3 — `sha256sum -c fase2/SHA256SUMS.txt` executa sem falhas a partir da raiz; ordem de leitura e instruções de reprodução preservadas no índice.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
2/10 — Conferência mecânica de índice, links e checksums; o risco é confundir o alcance da flag `--check-delivery` (não checa JSON nem checksums) com uma falha.

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

Plano: [plan.md](../../plans/11-indice-da-entrega/plan.md)
