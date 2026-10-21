# Plano: Auditoria de referências da metodologia (fase 2)

Estado: aprovado — aguardando escrita de tasks pelo task-master (ao iniciar este plano, o task-master deve derivar as tasks antes de executar)

## Objetivo
Auditar as citações de `fase2/fase2_metodologia.tex` contra as fontes registradas nas pesquisas, produzindo `fase2/references.bib` consolidado e o relatório `fase2/documentos/10_auditoria_de_referencias.md`, com zero chaves citadas sem entrada e zero divergências de identidade bibliográfica (autor/título/ano/DOI/URL).

## Abordagem
Processo de auditoria definido no documento-fonte (não é nova leitura remota dos artigos; os acessos remotos válidos são os documentados nas pesquisas de 30/09/2026):

1. Ler integralmente o `.tex` da metodologia, os quatro `fase2/pesquisa/references_*.bib` e os quatro relatórios de pesquisa (tabelas de fontes, tentativas e limitações).
2. Confrontar cada chave citada com a entrada bibliográfica e com o registro verificável de consulta da pesquisa correspondente (autoria, título, ano, DOI quando registrado, URL, versão e alcance do trecho que cita). Exceção pontual autorizada: recuperação direta do prefácio primário de Lakens para confirmação.
3. Classificar cada chave citada: **Correto** (identidade e atribuição compatíveis com o conteúdo registrado como lido) ou **Limitado** (identidade correta, mas fundamentação só por metadados/resumo/leitura restrita, com ressalva). Essas classificações não afirmam eficácia do EduAgent-OS nem reprodução de benchmarks.
4. Consolidar as bibliografias das pesquisas aplicando as regras abaixo (deduplicação, datas, estrutura, escaping).

Regras de consolidação do `references.bib`:
- **Deduplicação:** a mesma obra em arquivos distintos vira uma única chave, mantendo a entrada mais completa (caso `zheng2023judge`: prevalece a de `references_avaliacao_qualidade.bib`, com DOI e `primaryClass`; registro de leitura complementar não gera segunda chave). Não criar entradas para páginas auxiliares, APIs, HTML do mesmo artigo ou documentação reconsultada.
- **Datas:** ausência de data editorial verificada → `year = {s.d.}` com `note = {Acesso em 30/09/2026}` e `urldate` ISO; **não** converter em publicação de 2026. Anos de documentação com data explícita permanecem (ex.: CP-SAT 2024, SQLite WAL 2026); MCP 2025 (especificação 2025-11-25); distinguir ano de publicação/preprint original de revisão arXiv consultada (MemGPT 2023/v2 2024; M3 2024/v5 2025; MetaGPT v7 2024; LongMemEval ICLR 2025; AgentBench ICLR 2024; RAGAs EACL 2024), mantendo as diferenças explícitas em nota.
- **Estrutura BibTeX:** corrigir inadequações para o estilo efetivo (caso `lakens2022inferences`: `@misc` com `howpublished`, pois `plainnat` exige `publisher` em `@book`; não fabricar editora).
- **Notas e escaping:** retirar notas extensas de auditoria/bloqueios/tentativas, mantendo só notas curtas essenciais de versão/acesso; URLs exclusivamente no campo `url`, com underscores literais (sem `\_` em URLs); escape de underscore só em texto TeX de título; DOI em campo `doi`; grafia original de títulos conservada (ex.: "Heterogenous" de BEIR).
- **Cobertura:** preservar também as fontes únicas não citadas (12 no inventário do documento-fonte) — a consolidação abrange todas; isso não gera citação nem exige `\nocite{*}`.

Regras do LaTeX (`fase2_metodologia.tex`):
- `natbib` com `[authoryear,round]`; `\cite` = `citep` (parentética) e `\citeonline` = `citet` (narrativa); chaves preservadas exatamente, inclusive maiúsculas (`jiwerQuality`, `bfclMultiTurn`, `hypothesisStateful`, `scipyBootstrap`).
- Exatamente um `\bibliography{references}` e estilo condicional (`aasjournal` se disponível, `plainnat` como fallback); chaves únicas e case-sensitive no `.bib`.

## Escopo
- Entregas: `fase2/references.bib` consolidado (56 fontes únicas; 44 citadas; 12 preservadas sem citação; 15 com `s.d.`; 0 citações sem entrada) e o relatório `fase2/documentos/10_auditoria_de_referencias.md` com inventário, tabela individual das 44 chaves citadas (pesquisa/fonte primária, alcance de acesso, parecer), síntese (8 limitadas, 36 corretas) e fechamento.
- Edição restrita a esses dois arquivos; o `.tex`, as pesquisas e os demais documentos não são editados.
- A auditoria confere registros de pesquisa e sua utilização no texto; **não** é nova leitura remota dos artigos, não é verificação de desempenho do EduAgent-OS, e limitações de leitura (metadados/resumo/truncamento) não são erros de identidade.

## Contexto
- `fase2/documentos/10_auditoria_de_referencias.md` — documento-fonte: método, inventário, tabela das 44 chaves, correções e fechamento.
- `fase2/fase2_metodologia.tex` — objeto auditado (citações, definição `\cite`/`\citeonline`, `\bibliography{references}`).
- `fase2/references.bib` — bibliografia consolidada a produzir/manter.
- `fase2/pesquisa/references_arquitetura.bib`, `fase2/pesquisa/references_pedagogia.bib`, `fase2/pesquisa/references_avaliacao_qualidade.bib`, `fase2/pesquisa/references_robustez.bib` — bibliografias de origem da consolidação.
- `fase2/pesquisa/03a_arquitetura_rag.md` (§5), `fase2/pesquisa/03b_pedagogia_memoria_planejamento.md` (§10), `fase2/pesquisa/07a_metodos_qualidade.md` (§11), `fase2/pesquisa/07b_metodos_robustez_experimentos.md` (§10.2) — registros verificáveis de consulta (fontes, tentativas, limitações) usados no confronto.
- `fase2/scripts/verificar_documentos.py` — verificação de chaves únicas, cobertura de etapas, seções e links locais (`--check-delivery` inclui existência de arquivos de entrega).

## Critérios de conclusão
- `python3 fase2/scripts/verificar_documentos.py` passa (inclui unicidade case-sensitive de chaves e links locais).
- Toda chave citada no `.tex` tem entrada única no `references.bib` e toda entrada é rastreável a um registro das pesquisas (identidade: autor/título/ano/DOI/URL).
- Regras de formatação atendidas: `\cite`/`\citeonline` no `.tex`, um único `\bibliography{references}`, URLs em `url`, `s.d.` apenas onde não há data editorial verificada, sem duplicatas.
- Relatório registra parecer por chave citada (Correto/Limitado) e as limitações de leitura permanecem explícitas, sem convertê-las em resultados do sistema.
- Compilação BibTeX/LaTeX (quando executada, via `gerar_entrega.py`) sem citações/referências indefinidas nem caixas overfull.

## Questões abertas
- O documento-fonte registra `aasjournal.bst` ausente no ambiente atual; manter o fallback `plainnat` declarado no fonte ou providenciar o `.bst` é decisão pendente.
- O recálculo do SHA-256 do modelo Bonsai (publicado, não recalculado na auditoria) e a execução de setups/demos citados permanecem pendências fora do escopo desta auditoria.

## Tasks
<A preencher pelo task-writer.>
