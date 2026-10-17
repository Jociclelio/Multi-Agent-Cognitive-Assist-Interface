# Plano: Materializar a Etapa 5 — fluxos, saídas esperadas e pontos de falha do EduAgent-OS

Estado: rascunho

## Objetivo
Consolidar `05_fluxos_resultados_e_falhas.md` como a referência de fluxos operacionais, qualidade de saídas e catálogo de falhas do EduAgent-OS, garantindo que o material esteja coerente com a especificação v0.1 (etapa 4), registrado no índice da entrega e rastreável (IDs W, O e F), sem apresentar nada como resultado medido.

## Abordagem
O documento é normativo (especificação), portanto o plano descreve a implementação/documentação futura que ele define — não executa experimentos:

1. **Matriz de fluxos W01–W12**: manter/validar a tabela de 12 fluxos (Ingestão, Consulta fundamentada, Prática, Avaliação formativa, Retomada longitudinal, Planejamento, Replanejamento, Agenda, Curadoria, Memória explícita, Recuperação operacional, Instalação/manutenção), cada um com gatilho/sequência, saídas esperadas (IDs O) e variações/término. Pedidos compostos devem decompor em rotas existentes, sem criar capacidades ilimitadas.
2. **Qualidade por saída O01–O18**: preservar a tabela de conteúdo necessário e perdas de qualidade típicas de cada saída, como critério de qualidade por artefato.
3. **Catálogo de falhas F01–F24**: manter a tabela de pontos/causas, propagação/impacto, saídas/fluxos afetados e severidade (S1 qualidade localizada; S2 perda pedagógica/continuidade; S3 restrição, dado ou efeito comprometido; S4 indisponibilidade/corrupção generalizada). Severidade é potencial, não frequência observada.
4. **Falhas compostas prioritárias**: registrar os 6 cenários compostos (OCR→prazo errado; Tutor/Monitor com erro correlacionado; retry pós-timeout sobrescrevendo mudança externa; invalidação transitiva de resumo; reexecução sem operation_id; falhas fora do denominador de p95) com suas exigências (validação independente, snapshot/ETag, idempotência, etc.).
5. **Rastreabilidade e cobertura**: verificar as afirmações de cobertura — W01–W12 cobrem as intenções da etapa 4; O01–O18 cobrem artefatos internos, saídas ao estudante e operacionais; F01–F24 cobrem fronteiras de transformação/persistência/efeito e validade da avaliação. A etapa 6 define métricas para esses IDs e a etapa 7 seleciona métodos; mudanças de capability exigem novo fluxo, saída, falha e teste.

## Escopo
- Entrega: manutenção/revisão do documento `05_fluxos_resultados_e_falhas.md` (matriz de fluxos, qualidade de saídas, catálogo de falhas, falhas compostas, rastreabilidade), integrado ao fluxo de entrega da fase 2.
- Regras de consistência: novos conectores/skills exigem revisão da matriz; nenhum resumo fictício, nota oficial a partir de avaliação formativa, overwrite silencioso ou anúncio de sucesso sem verificação.
- Fora de escopo: definição de métricas (etapa 6), seleção de métodos de teste (etapa 7), implementação executável do sistema e qualquer medição real.

## Contexto
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — documento-fonte (normativo) a materializar.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — especificação de referência; o universo de tarefas é o conjunto de intenções/estados da v0.1 definida ali (etapa 4).
- `fase2/documentos/06_protocolo_de_avaliacao.md` — etapa 6, que define as métricas para os IDs W/O/F.
- `fase2/documentos/07_metodologias_de_testagem.md` — etapa 7, que seleciona os métodos de teste.
- `fase2/documentos/11_indice_da_entrega.md` — índice da entrega onde o documento deve permanecer registrado.
- `fase2/scripts/verificar_documentos.py` — verificação documental (citações, seções obrigatórias, IDs, links) a rodar na entrega.

## Critérios de conclusão
- O documento mantém as tabelas completas: 12 fluxos (W01–W12), 18 saídas (O01–O18) e 24 falhas (F01–F24) com severidades atribuídas e 6 falhas compostas prioritárias.
- As afirmações de rastreabilidade da seção 5 são consistentes com a etapa 4 (intenções cobertas por W01–W12) e sem contradição com etapas 6/7.
- Nada no documento é apresentado como resultado medido; severidades permanecem rotuladas como potenciais.
- `python3 fase2/scripts/verificar_documentos.py` passa após as alterações.

## Questões abertas
- Nenhuma essencial. Nota do próprio documento: o catálogo não presume enumerar todos os defeitos futuros; mudanças de capability exigirão novos fluxos, saídas, falhas e testes.

## Tasks
<A preencher pelo task-writer.>
