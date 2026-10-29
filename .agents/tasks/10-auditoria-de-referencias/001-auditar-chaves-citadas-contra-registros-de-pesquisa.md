# Task 001: Auditar as 44 chaves citadas contra os registros de pesquisa

Estado: pendente
Depende de: nenhuma
Origem: nenhuma

## Prompt
Auditar as citações de `fase2/fase2_metodologia.tex` contra os registros verificáveis de consulta das pesquisas (acessos remotos válidos = os documentados em 30/09/2026; NÃO é nova leitura remota dos artigos): (1) extrair todas as chaves citadas no `.tex`; (2) para cada chave citada (44 no inventário do documento-fonte), confrontar a entrada bibliográfica e o registro de consulta na pesquisa correspondente (`fase2/pesquisa/03a_arquitetura_rag.md` §5, `03b_pedagogia_memoria_planejamento.md` §10, `07a_metodos_qualidade.md` §11, `07b_metodos_robustez_experimentos.md` §10.2) — autoria, título, ano, DOI quando registrado, URL, versão e o alcance do trecho que cita; (3) classificar cada chave: **Correto** (identidade e atribuição compatíveis com o conteúdo registrado como lido) ou **Limitado** (identidade correta, fundamentação só por metadados/resumo/leitura restrita, com ressalva); (4) conferir que o relatório `fase2/documentos/10_auditoria_de_referencias.md` registra o parecer por chave, o inventário (56 fontes únicas; 44 citadas; 12 preservadas sem citação; 15 com `s.d.`), a síntese (8 limitadas, 36 corretas) e as limitações de leitura explícitas. Exceção pontual autorizada: recuperação direta do prefácio primário de Lakens para confirmação. Correção no relatório 10 somente em dif mínimo com justificativa; as classificações não afirmam eficácia do EduAgent-OS nem reprodução de benchmarks.

Restrições: `.tex`, pesquisas e documentos das etapas 1–9 INTOCADOS nesta task (a auditoria confere, não edita o auditado); nenhuma leitura remota nova além da exceção Lakens; nada apresentado como resultado medido; prosa em português; `python3 fase2/scripts/verificar_documentos.py` deve passar ao final; commits entrega/registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/10_auditoria_de_referencias.md` — relatório da auditoria (inventário, tabela das 44 chaves, correções, fechamento).
- `fase2/fase2_metodologia.tex` — objeto auditado (chaves citadas, `\cite`/`\citeonline`).
- `fase2/pesquisa/03a_arquitetura_rag.md`, `03b_pedagogia_memoria_planejamento.md`, `07a_metodos_qualidade.md`, `07b_metodos_robustez_experimentos.md` — registros verificáveis de consulta (fontes, tentativas, limitações).
- `fase2/scripts/verificar_documentos.py` — verificação de chaves e links.

## Corretude
- [ ] C1 — Todas as chaves citadas no `.tex` extraídas e confrontadas com entrada + registro de pesquisa; zero chaves citadas sem entrada.
- [ ] C2 — Parecer por chave (Correto/Limitado) conferido no relatório 10 e consistente com os registros de consulta; contagens do inventário (56/44/12/15; 8/36) corretas ou divergência justificada em dif mínimo.
- [ ] C3 — Limitações de leitura permanecem explícitas (não convertidas em resultado do sistema); nenhuma leitura remota nova além da exceção Lakens; verificador passa.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
5/10 — Conferência chave a chave (44) contra quatro registros de pesquisa; o risco é validar identidade bibliográfica sem conferir o alcance do trecho que cita (a parte "Limitado").

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
