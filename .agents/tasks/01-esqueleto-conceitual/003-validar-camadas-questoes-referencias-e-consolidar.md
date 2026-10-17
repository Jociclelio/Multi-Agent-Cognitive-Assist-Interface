# Task 003: Validar camadas transversais, questões abertas, referências de partida e consolidação final (seções 5–7)

Estado: aguardando revisão
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
- [x] C1 — As oito camadas transversais do plano estão representadas na seção 5, cada uma com conferência registrada em Evidências; nenhuma camada do plano ficou de fora.
- [x] C2 — As onze questões abertas do plano estão enumeradas na seção 6 e o texto as remete explicitamente à etapa 2 e às etapas 3–4 (formulações equivalentes, como "remetidas às etapas 2–4" ou "resolvidas metodologicamente nas etapas 3–4", são aceitas desde que nenhuma questão apareça como resolvida nesta etapa), sem resolver ou decidir nenhuma delas.
- [x] C3 — A seção 7 lista as cinco referências de partida com enquadramento explícito de "verificação na etapa 3 e na auditoria final", e nenhuma frase do documento atribui a elas validação, eficácia ou suporte a este projeto.
- [x] C4 — Os três critérios de conclusão do plano foram reavaliados sobre o documento completo e o resultado (conforme/ajustado) está registrado em Evidências, citando trechos verificados.
- [x] C5 — `python3 fase2/scripts/verificar_documentos.py` roda sem erro fatal e sem apontamentos referentes a `01_esqueleto_conceitual.md` (saída registrada; limitações do verificador anotadas); correções (se houver) em difs mínimos; se nada precisar mudar além do registro, a entrega é o commit de registro sem alteração de artefatos.

## Execução
- Modelo: GLM-5.3-Flash (provider `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime
- Base: 815a474f73f253b524df49f79edd367efa4684da
- Entrega: sem alteração de artefatos (validação conforme C1–C5; nenhuma lacuna, desvio ou resíduo encontrado nas seções 5–7 nem na consolidação final)
- Arquivos da entrega: nenhum (somente este registro; `git diff 815a474 -- fase2/documentos/01_esqueleto_conceitual.md` permanece vazio)
- Evidências:
  - **C1 (seção 5, oito camadas)** — Conferência item a item da lista (linhas 56–63 do documento) contra o bullet de camadas do plano: (1) contratos tipados e IDs estáveis de disciplina/tópico/documento/evento/tarefa; (2) separação de dados brutos, fatos confirmados, inferências e artefatos publicados; (3) recuperação documental distinta da memória do estudante, ambas com proveniência; (4) skills versionadas, selecionadas por tarefa, com pré-condições e critérios de término; (5) validação estrutural, validação de domínio e conferência independente de efeitos externos; (6) checkpoints, transações, idempotência, timeout, limites de chamadas e cancelamento; (7) registro de custo, latência, erros, delegações e versão de cada componente; (8) avaliação em camadas: artefatos, fluxos completos, continuidade e injeção de falhas. Correspondência 1:1 com o plano — oitava camada com desdobramento exemplificativo ("artefatos, fluxos completos, continuidade e injeção de falhas"), consistente com "avaliação em camadas" do plano; nenhuma camada de fora, nenhum item extra que conflite.
  - **C2 (seção 6, onze questões)** — Contagem e conferência do parágrafo único (linha 67): escolha verificável e configuração do Bonsai 2 (1); extração/OCR (2); granularidade dos tópicos (3); busca híbrida e reranking (4); tratamento de datas (5); rubricas e estimador de domínio (6); recuperação/compactação da memória (7); formalização do solver (8); ferramentas e suas permissões (9); limites operacionais (10); dataset e métricas (11) — as onze do plano, nenhuma a mais ou a menos. Remissão explícita presente: "Essas lacunas são enumeradas na etapa 2 e resolvidas metodologicamente nas etapas 3–4" — formulação aceita pelo critério; nenhuma questão aparece como resolvida ou decidida nesta etapa.
  - **C3 (seção 7, cinco referências)** — Conferência das cinco entradas (linhas 71–77): MetaGPT (Hong et al., ICLR 2024, arXiv:2308.00352), MultiTutor (Sun e Tai, PMLR 273, 2025), MemGPT (Packer et al., 2023, arXiv:2310.08560), Voyager (Wang et al., 2023, arXiv:2305.16291), ToRA (Gou et al., ICLR 2024, arXiv:2309.17452). Enquadramento explícito de verificação futura: "sua verificação e análise de adequação serão registradas na etapa 3 e na auditoria final, antes de entrarem no relatório". Cada entrada traz qualificador que impede atribuição de validação a este projeto ("transferência para educação é uma adaptação"; "sem estabelecer eficácia deste projeto"; "não validação de um modelo pedagógico"; "não prova benefício de compactar prompts"; "solver de agenda é uma escolha de engenharia própria"). Links conferidos como os do documento atual (arXiv/PMLR), sem acesso à rede — verificação de referências permanece para as etapas 3 e 10.
  - **C4 (consolidação final, três critérios do plano) — resultado: conforme**, sem resíduos:
    1. *Cobertura das seções do esqueleto* — percurso completo do documento (linhas 1–77): §1 escopo/premissas com hipótese como hipótese; §2 princípio arquitetural com diagrama Mermaid (`flowchart TD`, linhas 13–30, cobrindo os cinco agentes, orquestrador e camada de contratos/observabilidade); §3 tabela de responsabilidades e fronteiras dos cinco agentes (linhas 34–40); §4 ciclo mínimo em 7 passos com terminais explícitos (linha 52: "resposta, pedido de esclarecimento, espera por resposta do aluno, conflito de agenda, falha controlada e cancelamento"); §5 camadas transversais; §6 questões abertas; §7 referências de partida. Todas as seções exigidas presentes; consistência entre seções mantida (ex.: terminais de §4 alinhados com cancelamento/limites de §5; nomes dos agentes no grafo, na tabela e no ciclo coincidem).
    2. *Nenhuma proposta como resultado medido* — varredura por números/métricas/resultados: não há valores medidos no documento; §1 mantém "A hipótese é que separação de responsabilidades, contratos verificáveis e memória seletiva melhorem continuidade e consistência sob orçamento local" e condiciona a comparação: "A comparação com um agente único deve usar as mesmas ferramentas, dados e limites de recursos"; "dataset e métricas" consta apenas como questão aberta (§6). Conforme.
    3. *Questões abertas enumeradas e remetidas às etapas 2–4* — conforme evidência de C2 (remissão explícita no fechamento da seção 6). Conforme.
    - **Divergência plano × fase 1** — nenhuma divergência nova relevante identificada nas seções 5–7; as registradas em 001/002 (exclusões do escopo; nomenclatura abreviada dos agentes) permanecem resolvidas com prevalência do plano, sem alteração.
  - **C5 (verificador)** — `python3 fase2/scripts/verificar_documentos.py` a partir da raiz: saída `status: "passed"`, `bibliography_unique: 56`, `cited_unique: 44`, `missing_citations: []`, `steps: 11`, `components: 20`, `flows: 12`, `outputs: 18`, `failures: 24`, `local_links_checked: 39`, `delivery_pending: []` — passagem limpa, sem apontamentos referentes a `01_esqueleto_conceitual.md` (o verificador cobre todos os documentos da fase 2 e não reporta nenhum). **Limitações anotadas:** o verificador usa só a biblioteca padrão e não checa freshness de PDFs nem checksums; `delivery_pending: []` indica apenas ausência de entrega pendente declarada, não validação de PDF/ZIP. Verificação de rede/referências fora do escopo desta etapa (etapas 3 e 10).
  - **Decisão de não alteração** — todas as conferências (C1–C4) e o verificador (C5) conformes; nenhuma correção necessária, portanto nenhum dif aplicado ao documento, preservando a prosa acadêmica intacta. Entrega consolidada como "sem alteração de artefatos".

## Notas

### Dificuldade esperada
4/10 — Seções curtas e com correspondência próxima ao plano, mas a task acumula a consolidação final de todo o documento e a execução do verificador; exige julgamento para distinguir resíduo real de estilo legítimo e para interpretar a saída do script (que cobre todos os documentos da fase 2, não só este).

### Dificuldade sentida
3/10 — Correspondência 1:1 entre seções 5–7 e os bullets do plano tornou as conferências diretas; o verificador passou limpo na primeira execução. A única exigência de julgamento foi a consolidação final sobre o documento inteiro (C4), distinguir estilo legítimo de resíduo (nenhum encontrado) e anotar as limitações do verificador (sem checagem de PDF/checksums) sem apresentar `delivery_pending: []` como validação experimental.

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
