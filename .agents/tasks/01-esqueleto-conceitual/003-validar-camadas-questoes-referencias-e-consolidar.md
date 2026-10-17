# Task 003: Validar camadas transversais, questões abertas, referências de partida e consolidação final (seções 5–7)

Estado: pendente
Depende de: 002
Origem: nenhuma

## Prompt
Validar e, se necessário, corrigir as seções 5 ("Camadas transversais necessárias"), 6 ("Questões ainda abertas nesta etapa") e 7 ("Referências de partida") de `fase2/documentos/01_esqueleto_conceitual.md` contra o plano aprovado e, em seguida, fazer a **consolidação final** da etapa 1: revalidar o documento inteiro contra os critérios de conclusão do plano e rodar o verificador de documentos do repositório. A entrega já existe e está commitada: **não reescreva o documento**; aplique apenas correções pontuais onde houver lacunas. Tasks 001 e 002 já cobriram as seções 1–4; não retrabalhe essas seções além da checagem final de consistência.

Procedimento:
1. Conferir a seção 5 contra o bullet de camadas transversais do plano: contratos tipados e IDs estáveis; separação de dados brutos, fatos confirmados, inferências e artefatos publicados; recuperação documental distinta da memória do estudante, ambas com proveniência; skills versionadas com pré-condições e critérios de término; validação estrutural, de domínio e conferência independente de efeitos externos; checkpoints, transações, idempotência, timeout, limites de chamadas e cancelamento; registro de custo, latência, erros, delegações e versões; avaliação em camadas. Cada camada do plano deve estar representada na seção.
2. Conferir a seção 6: as questões abertas enumeradas correspondem às do plano (configuração do Bonsai 2, extração/OCR, granularidade de tópicos, busca híbrida/reranking, datas, rubricas e estimador de domínio, memória, formalização do solver, ferramentas e permissões, limites operacionais, dataset e métricas) e estão **explicitamente remetidas à etapa 2 e às etapas 3–4**, sem que nenhuma seja resolvida ou decidida nesta etapa (formulações equivalentes, como "remetidas às etapas 2–4" ou "resolvidas metodologicamente nas etapas 3–4", são aceitas desde que nenhuma questão apareça como resolvida nesta etapa).
3. Conferir a seção 7: as cinco referências de partida (MetaGPT, MultiTutor, MemGPT, Voyager, ToRA) constam como **referências por verificar** na etapa 3 e na auditoria final, sem o texto atribuir a elas validação deste projeto; conferir que os links são os do documento atual (não acessar a rede para "corrigir" referências — a verificação das referências é trabalho das etapas 3 e 10).
4. Consolidação final: percorrer os três critérios de conclusão do plano (cobertura das seções do esqueleto; nenhuma proposta como resultado medido, com hipótese e comparação condicionadas; questões abertas enumeradas e remetidas às etapas 2–4) sobre o documento como um todo, corrigindo eventuais resíduos.
5. Rodar `python3 fase2/scripts/verificar_documentos.py` a partir da raiz do repositório (usa só a biblioteca padrão; não requer LangChain) e registrar a saída em Evidências; se houver apontamentos referentes a este documento, corrigi-los e reexecutar até passagem limpa (limites conhecidos: o verificador não checa PDF freshness nem checksums — registrar essa limitação).

Restrições: preservar a prosa acadêmica em português; difs mínimos; não introduzir números ou métricas como resultados medidos; não resolver questões abertas nem validar referências nesta etapa; só alterar `fase2/documentos/01_esqueleto_conceitual.md` (e, no commit de registro, o arquivo desta task).

## Contexto
- `fase2/documentos/01_esqueleto_conceitual.md` — documento-fonte; seções 5, 6 e 7 são o objeto principal e o documento inteiro é o objeto da consolidação.
- `.agents/plans/01-esqueleto-conceitual/plan.md` — plano aprovado; bullets 5–6 da "Abordagem" e a seção "Critérios de conclusão" (três critérios) guiam esta task.
- `fase2/scripts/verificar_documentos.py` — verificador de documentos do repositório (citações, seções obrigatórias, IDs, arquivos de etapa, links locais); executável com `python3` a partir da raiz.
- `.agents/tasks/01-esqueleto-conceitual/001-validar-escopo-premissas-e-principio-arquitetural.md` e `.agents/tasks/01-esqueleto-conceitual/002-validar-agentes-e-ciclo-minimo.md` — tasks anteriores; ler seus registros (Execução/Evidências) para conhecer o estado já verificado das seções 1–4.
- `fase2/documentos/11_indice_da_entrega.md` — índice da entrega; consultar apenas para confirmar que a etapa 1 mantém o enquadramento de "especificação/proposta", não para editar.

## Corretude
- [ ] C1 — As oito camadas transversais do plano estão representadas na seção 5, cada uma com conferência registrada em Evidências; nenhuma camada do plano ficou de fora.
- [ ] C2 — As onze questões abertas do plano estão enumeradas na seção 6 e o texto as remete explicitamente à etapa 2 e às etapas 3–4 (formulações equivalentes, como "remetidas às etapas 2–4" ou "resolvidas metodologicamente nas etapas 3–4", são aceitas desde que nenhuma questão apareça como resolvida nesta etapa), sem resolver ou decidir nenhuma delas.
- [ ] C3 — A seção 7 lista as cinco referências de partida com enquadramento explícito de "verificação na etapa 3 e na auditoria final", e nenhuma frase do documento atribui a elas validação, eficácia ou suporte a este projeto.
- [ ] C4 — Os três critérios de conclusão do plano foram reavaliados sobre o documento completo e o resultado (conforme/ajustado) está registrado em Evidências, citando trechos verificados.
- [ ] C5 — `python3 fase2/scripts/verificar_documentos.py` roda sem erro fatal e sem apontamentos referentes a `01_esqueleto_conceitual.md` (saída registrada; limitações do verificador anotadas); correções (se houver) em difs mínimos; se nada precisar mudar além do registro, a entrega é o commit de registro sem alteração de artefatos.

## Execução
- Modelo: <identificador real do executor>
- Base: <SHA completo antes da implementação>
- Entrega: <SHA(s) completos, sem commits de registro, ou sem alteração de artefatos>
- Arquivos da entrega: <paths ou referência ao diff dos commits>
- Evidências: <comandos/procedimentos, resultados e limitações>

## Notas

### Dificuldade esperada
4/10 — Seções curtas e com correspondência próxima ao plano, mas a task acumula a consolidação final de todo o documento e a execução do verificador; exige julgamento para distinguir resíduo real de estilo legítimo e para interpretar a saída do script (que cobre todos os documentos da fase 2, não só este).

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

### Revisão
- Orquestrador: —
- Alvo: <SHAs da entrega e versão do registro revisado>
- Avaliações: <modelo A: _/10; modelo B: _/10; modelo C: _/10>
- Nota final: _/10
- Parecer: <síntese dos achados, evidências, divergências e Corretude pendente>
- Decisão: <fechar | corrigir | reiniciar | repartir; pendente se bloqueada>
- Reversão: <SHA ou não se aplica>
- Próximo passo: <subtasks em ordem ou próxima task liberada>

Plano: [plan.md](../../plans/01-esqueleto-conceitual/plan.md)
