# Task 001: Validar a tabela de métodos por família do documento 07

Estado: pendente
Depende de: nenhuma
Origem: nenhuma

## Prompt
Conferir item a item a tabela de métodos por família de `fase2/documentos/07_metodologias_de_testagem.md` contra os relatórios de pesquisa completos: (1) cada família de saída O01–O18 está coberta por método(s) com fórmulas/denominadores, procedimentos e oráculos fiéis a `fase2/pesquisa/07a_metodos_qualidade.md` (quatorze fontes); (2) cada família de falha F01–F24 e as capabilities C18/C19 estão cobertas conforme `fase2/pesquisa/07b_metodos_robustez_experimentos.md` (dezesseis fontes) — injeção de falhas, propriedade/estado, comparação e inferência; (3) as referências/bibliotecas citadas (ex.: JiWER, BEIR, ALCE, RAGAs, Prometheus, LongMemEval, AgentDojo, Hypothesis, SciPy) correspondem às usadas nos relatórios; (4) nenhum método presente no documento sem lastro nos relatórios e nenhum método dos relatórios essencial omitido sem registro. Se encontrar desvio de fidelidade, corrigir apenas o documento 07 em dif mínimo com justificativa (os relatórios 07a/07b são fontes, não entregáveis a editar).

Restrições: `fase2/documentos/04_mapa_completo_do_sistema.md`, `05_fluxos_resultados_e_falhas.md`, `06_protocolo_de_avaliacao.md` e os relatórios `07a`/`07b` INTOCADOS; nada apresentado como resultado medido (a síntese é especificação, não revisão sistemática nem experimento); IDs O01–O18, F01–F24 permanentes; prosa em português; `python3 fase2/scripts/verificar_documentos.py` deve passar ao final; commits de entrega e registro separados; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/07_metodologias_de_testagem.md` — documento a validar: tabela de métodos por família (O01–O18, F01–F24, C18/C19).
- `fase2/pesquisa/07a_metodos_qualidade.md` — relatório completo de métodos de qualidade por saída (fonte).
- `fase2/pesquisa/07b_metodos_robustez_experimentos.md` — relatório completo de robustez e experimentos (fonte).
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — IDs O/F de origem, para conferência de correspondência.

## Corretude
- [ ] C1 — Cobertura completa: todas as famílias de O01–O18 e de F01–F24 mais C18/C19 têm método com lastro em 07a/07b; nenhum ID citado fora dos intervalos permanentes.
- [ ] C2 — Fidelidade: fórmulas/denominadores, procedimentos e oráculos do documento 07 correspondem aos relatórios; bibliotecas citadas corretas; omissões ou acréscimos sem lastro registrados (ou corrigidos em dif mínimo).
- [ ] C3 — Caráter de especificação preservado (não revisão sistemática, não resultado medido); verificador passa ao final; documentos-fonte intocados.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
4/10 — Conferência cruzada densa entre síntese e dois relatórios longos; o risco é validar por amostragem e deixar passar família sem método ou biblioteca trocada.

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

Plano: [plan.md](../../plans/07-metodologias-de-testagem/plan.md)
