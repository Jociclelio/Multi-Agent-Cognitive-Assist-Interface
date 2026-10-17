# Plano: Auditoria de consistência entre os documentos da fase 2

Estado: rascunho

## Objetivo
Reproduzir, como processo verificável, a auditoria independente de consistência registrada em `fase2/documentos/auditoria_de_consistencia.md`: confrontar os documentos da fase 2, com verificação item a item delimitada conforme o Escopo, verificar a cobertura nominal C01–C20/W01–W12/O01–O18/F01–F24 e confirmar que as quinze decisões de correção listadas na tabela de achados estão incorporadas nos locais indicados ("Local vigente").

## Abordagem
Auditoria somente leitura dos documentos; nenhuma verificação de implementação/execução é escopo (o documento-fonte registra explicitamente que o modelo/runtime, OCR/RAG, pipeline educacional e testbed não foram executados).

1. Ler o documento-fonte e extrair a tabela de 15 achados (Achado → Decisão incorporada → Local vigente).
2. Verificar cobertura nominal dos requisitos C01–C20, W01–W12, O01–O18 e F01–F24 nos mapas normativos.
3. Para cada achado, conferir no "Local vigente" se a decisão está presente e coerente, por exemplo:
   - autoridade de snapshot/expected_version → mapa4 §15.1 e mapa8 §12;
   - rubrica (critério→tópico, omissão sem span) → mapa4 §15.2 e mapa8 §12;
   - ordem/revisão/independência de tentativas → mapa4 §§8/15.2 e mapa8 O09/§12;
   - política do elo evidência→agenda → mapa4 §15.3 e mapa8 §12;
   - dependência de atividade tipada → mapa4 §15.4 e mapa8 §12;
   - grade/limite diário/INFEASIBLE e identidade de bloco/UID/revisão ICS → mapa4 §15.5, mapa8 §12 e relatório;
   - incumbent perdido em UNKNOWN → mapa4 §15.5 e mapa8 §12;
   - rota approve_plan/ActivityUpdate → mapa4 §§10/15.4 e relatório;
   - ownership/dependências em esquema → mapa4 §15.1 e mapa8 §12;
   - orçamento de execução das metas → mapa8 §12.1 e relatório;
   - contraste full/reduced e handoff → mapa4 §15.6, mapa8 §§5/12 e relatório;
   - requisitos emCaseRecord e matrizC→predicado → mapa8 §12.2;
   - hierarquia normativa e notas de resolução nas pesquisas 3a/3b/7a/7b → mapa4 §1;
   - referência a Lakens (livro/capítulo consultado, DOI, entrada misc) → mapa8 §11, `fase2/references.bib` e auditoria 10.
4. Registrar divergências encontradas entre documentos como lacunas a corrigir nos mapas normativos, no relatório e nas notas de resolução das pesquisas — sem alterar o documento-fonte da auditoria.
5. Não apresentar metas nem constatações como resultados medidos; preservar as limitações declaradas (pin final de dependências, corpus/ouro/calibração por coleta, N/potência por piloto, exclusão lógica, etc.).

## Escopo
- Entrega: registro da auditoria de consistência reproduzida (constatações por achado e eventuais correções impostas nos documentos da fase 2).
- Limites: somente leitura na etapa de auditoria; correções, quando impostas, recaem sobre os mapas normativos, relatório e notas de resolução — nunca sobre o documento-fonte da auditoria. Não inclui execução de código, testes de implementação nem novos experimentos.
- Delimitação da verificação (decisão explícita deste plano): a conferência item a item cobre os "Locais vigentes" da tabela de achados — mapas normativos, relatório, pesquisas 3a/3b/7a/7b, `references.bib` e auditoria 10. A proposta da fase 1, as instruções e os demais documentos metodológicos entram como leitura de apoio para contextualizar os achados, sem verificação item a item.

## Contexto
- `fase2/documentos/auditoria_de_consistencia.md` — documento-fonte: tabela dos 15 achados/decisões e limitações declaradas.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — mapa4 normativo (§§1, 8, 10, 15.1–15.6): principal alvo de verificação.
- `fase2/documentos/08_mapa_completo_da_testagem.md` — mapa8 normativo (§§5, 11, 12, 12.1, 12.2, O09): principal alvo de verificação.
- `fase2/documentos/09_relatorio_tecnico.md` — relatório citado como "Local vigente" de vários achados.
- `fase2/pesquisa/03a_arquitetura_rag.md`, `fase2/pesquisa/03b_pedagogia_memoria_planejamento.md`, `fase2/pesquisa/07a_metodos_qualidade.md`, `fase2/pesquisa/07b_metodos_robustez_experimentos.md` — pesquisas com notas de resolução no início.
- `fase2/references.bib` — entrada de Lakens (livro/capítulo, DOI, misc).
- `fase2/documentos/10_auditoria_de_referencias.md` — auditoria de referências (achado Lakens).

## Critérios de conclusão
- Os 15 achados do documento-fonte foram conferidos um a um nos seus "Locais vigentes", com registro por achado (confirmado/divergente).
- Cobertura nominal C01–C20/W01–W12/O01–O18/F01–F24 verificada nos mapas.
- Divergências encontradas estão registradas com o local e a correção imposta, sem alterar o documento-fonte.
- O registro não apresenta pendências metodológicas como resultados medidos e preserva as limitações do documento-fonte.

## Questões abertas
- Se algum achado divergir do "Local vigente", aplicar a correção diretamente ou apenas registrá-la para decisão do master? (padrão proposto: registrar e deixar a decisão de fechar/corrigir com o master).
- Verificação de PDF/entrega (`fase2/fase2_metodologia.pdf`, SHA-256, ZIP) está fora do escopo desta auditoria documental; confirmar se deve permanecer fora.

## Tasks
<A preencher pelo task-writer.>
