# Etapa 11 — Índice dos documentos íntegros

Todos os arquivos foram salvos em `fase2/`. O pacote [`../eduagent_fase2_entrega.zip`](../eduagent_fase2_entrega.zip) reúne documentos, pesquisas, bibliografias, relatório LaTeX/PDF, template/proposta de contexto e scripts de validação/compilação. `SHA256SUMS.txt` no pacote permite conferir os bytes. Não contém `.env`, credenciais, pesos de modelos ou dados privados de estudantes.

| Etapa | Documento |
|---|---|
| 1 | [Esqueleto conceitual](01_esqueleto_conceitual.md) |
| 2 | [Componentes e requisitos](02_componentes_e_requisitos.md) |
| 3 | [Metodologias de implementação](03_metodologias_de_implementacao.md), com [pesquisa arquitetural/RAG](../pesquisa/03a_arquitetura_rag.md) e [pedagogia/memória/agenda](../pesquisa/03b_pedagogia_memoria_planejamento.md) |
| 4 | [Mapa completo do sistema](04_mapa_completo_do_sistema.md) |
| 5 | [Fluxos, resultados e falhas](05_fluxos_resultados_e_falhas.md) |
| 6 | [Protocolo de avaliação](06_protocolo_de_avaliacao.md) |
| 7 | [Metodologias de testagem](07_metodologias_de_testagem.md), com [qualidade das saídas](../pesquisa/07a_metodos_qualidade.md) e [robustez/experimentos](../pesquisa/07b_metodos_robustez_experimentos.md) |
| 8 | [Mapa completo da testagem](08_mapa_completo_da_testagem.md) |
| 9 | [Índice do relatório](09_relatorio_tecnico.md), [fonte LaTeX](../fase2_metodologia.tex) e [PDF](../fase2_metodologia.pdf) |
| 10 | [Auditoria de referências](10_auditoria_de_referencias.md) e [references.bib](../references.bib) |
| 11 | Este índice, [guia da entrega](../README-entrega.md), arquivo ZIP e checksums |

## Ordem recomendada de leitura

Para implementar produção, começar pelo mapa4, que é autocontido e normativo. Para implementar avaliação, começar pelo mapa8, também autocontido. O relatório oferece a apresentação acadêmica integrada. Pesquisas3a/3b/7a/7b fundamentam decisões, alternativas e limitações; trechos históricos resolvidos têm aviso no início e não substituem os mapas atuais.

## Acesso e reprodução

Arquivos disponíveis diretamente no workspace, com links relativos neste índice e no chat. Não há integração autenticada com Google Drive nesta sessão; nenhum upload foi realizado. O ZIP pode ser enviado ao Drive pelo usuário sem perder os fontes e anexos.

Compilar/empacotar: `python3 fase2/scripts/gerar_entrega.py`. Verificar documentação sem executar o sistema: `python3 fase2/scripts/verificar_documentos.py`. O arquivo `verificacao_documental.json` registra contagens e verificações mecânicas; essas não substituem leitura científica, que foi realizada durante elaboração/auditoria.
