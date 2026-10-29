# Task 004: Validar a matriz por saída O01–O18 do protocolo

Estado: pendente
Depende de: 003
Origem: nenhuma

## Prompt
Conferir item a item a seção 3 ("Matriz por saída") de `fase2/documentos/06_protocolo_de_avaliacao.md`: (1) cada saída O01–O18 tem métrica "Como medir" coerente com a etapa 7 (fórmulas/denominadores de `fase2/pesquisa/07a_metodos_qualidade.md`) e com o conteúdo definido para a saída na etapa 5 (`fase2/documentos/05_fluxos_resultados_e_falhas.md`, tabela O01–O18); (2) os domínios das métricas estão corretos e preservados (taxas em [0,1]; CER/WER podem exceder 1; kappa em [-1,1]; log loss sem teto); (3) `N/A` exige motivo e a regra de IC/inconclusivo quando a amostra não sustentar estimativa está presente, com a proibição de baixar limite após olhar o teste; (4) os critérios iniciais estão rotulados como gates de engenharia para o corpus escolhido, não mínimos universais; (5) as notas "medir artefatos antes de sucesso agregado" e "turnos de uma mesma trajetória não são amostras independentes" permanecem. Confirmar a correspondência de IDs O01–O18 entre etapas 5, 6 e 7 (nenhum ID citado fora do intervalo permanente). Se encontrar desvio de fidelidade ou contradição, corrigir apenas o documento 06 em dif mínimo, preservando o sentido normativo.

Restrições: `fase2/documentos/04_mapa_completo_do_sistema.md`, `05_fluxos_resultados_e_falhas.md` e `07_metodologias_de_testagem.md` INTOCADOS; nada apresentado como resultado medido (a matriz é especificação de métricas, não resultado); IDs O01–O18 permanentes; prosa em português; `python3 fase2/scripts/verificar_documentos.py` deve passar ao final; commits de entrega e registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/06_protocolo_de_avaliacao.md` — documento a validar: seção 3 (matriz O01–O18).
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — tabela de qualidade por saída O01–O18 (conteúdo esperado por artefato).
- `fase2/pesquisa/07a_metodos_qualidade.md` — fórmulas, denominadores e oráculos por saída (fonte das métricas "Como medir").
- `fase2/documentos/07_metodologias_de_testagem.md` — tabela de métodos por família para conferência de correspondência.

## Corretude
- [ ] C1 — Cada linha O01–O18 da seção 3 é coerente com a etapa 5 (conteúdo da saída) e com a etapa 7/07a (métrica, fórmula, denominador); correspondência de IDs confirmada sem ID fora de O01–O18.
- [ ] C2 — Domínios de métrica corretos, `N/A` condicionado a motivo, regra de IC/inconclusivo e proibição de baixar limite pós-teste presentes; gates rotulados como propostas do corpus, não mínimos universais.
- [ ] C3 — Notas de "artefatos antes de sucesso agregado" e de não-independência de turnos preservadas; correções (se houver) em dif mínimo no documento 06 com verificador passando; nada como resultado medido.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
4/10 — Conferência documental cruzada entre três etapas; o risco é deixar passar domínio de métrica errado (ex.: kappa tratado como não-negativo) ou gate lido como mínimo universal.

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

Plano: [plan.md](../../plans/06-protocolo-de-avaliacao/plan.md)
