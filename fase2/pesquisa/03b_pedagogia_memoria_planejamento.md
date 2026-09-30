# 03b — Pedagogia, memória longitudinal e planejamento verificável

## 1. Escopo, método de pesquisa e estatuto das recomendações

**Resolução posterior:** mapa4 §§8/9/15 é normativo. DTSTAMP sem METHOD é por revisão (CREATED preserva criação); estado favorável, avaliação por tópico/omissão, política evidência→demanda e precedência de atividades estão fechados ali. As regras percentuais de contexto desta pesquisa são alternativas históricas: vale a reserva única reconciliada no mapa4. Mapa8 contém oráculos correspondentes. Pendências abaixo são o registro do momento de pesquisa, não substituem essas decisões.

Pesquisa dirigida por requisitos C06–C12 de `fase2/documentos/02_componentes_e_requisitos.md`, em conformidade com as fronteiras de agentes de `01_esqueleto_conceitual.md`. Consulta realizada em **30/09/2026**. A proposta foi lida no PDF `fase1/fase1_proposta.pdf`, especialmente §§4.1–4.3 e §5; conversão temporária em `/tmp/opencode/markitdown/fase1_proposta_pedagogia.md`. Não se utilizou `fase1/references.bib` como fonte bibliográfica.

O método foi uma **revisão técnica dirigida, não sistemática**: (1) extrair requisitos e afirmações da proposta; (2) localizar trabalhos originais por título/DOI/identificador e documentação dos mantenedores; (3) consultar com webfetch; (4) aprofundar método e avaliação quando texto acessível; (5) distinguir mecanismo publicado, adaptação proposta e obrigação normativa; (6) especificar contratos, procedimento, alternativas e teste de seleção. Consultas independentes foram feitas em paralelo; a síntese integrou dependências Tutor → Monitor → estado/memória → Planejador → agenda. Não houve busca exaustiva em bases nem contagem PRISMA.

Foram incluídos **18 itens bibliográficos**: 15 com conteúdo substantivo em artigo/documentação, um com resumo experimental depositado pelo editor (Chi) e dois apenas com metadados acessíveis (Wood e Corbett). As equações e detalhes operacionais de BKT foram conferidos no texto de pyBKT. O registro da §10 explicita essas diferenças: consultar metadados não equivale a ler um artigo. HTMLs extensos foram usados nos trechos de método/resultados efetivamente retornados; não se presume leitura de todos os apêndices. PDFs retornados como bytes por webfetch foram baixados da mesma URL e convertidos com markitdown em `/tmp`, quando necessários à análise.

**Legenda:** **[E]** evidência empírica no contexto da fonte; **[N]** especificação normativa/documentação técnica; **[P]** escolha ou parâmetro proposto para o EduAgent-OS, ainda não calibrado. Todos os limites, pesos, escalas locais e regras de seleção abaixo são **[P]**, salvo identificação explícita de [E]/[N]. Resultados de outros modelos não estabelecem qualidade do Bonsai 2, da língua portuguesa ou desta integração.

## 2. Decisões por componente

| ID | Método recomendado [P] | Fontes e natureza | Alternativa a comparar | Critério de seleção |
|---|---|---|---|---|
| C06 | Máquina de estados de tutoria, apoio graduado, autoexplicação e recuperação ativa; skills versionadas por tarefa | Chi/Roediger [E]; MultiTutor/Voyager/MetaGPT, transferência arquitetural | Explicação direta; prompt único com todas as skills | Qualidade por rubrica, participação solicitada, vazamento de solução, tokens e terminação |
| C07 | Avaliação por critério com gabarito, evidência textual e abstinência | Prometheus [E] em avaliação de LLMs; entropia semântica [E] em QA | Verificador determinístico; juiz único; amostragem semântica | Acordo humano, erro entre avaliações aceitas, cobertura e custo |
| C08 | Estado observado auditável no cold-start; BKT como estimador comparável somente após ajuste | Corbett, identidade bibliográfica; pyBKT [E] e equações | Contadores; modelo logístico; BKT com esquecimento | Brier/log loss de resposta futura, calibração e estabilidade por tópico |
| C09 | Eventos preservados, projeções versionadas, fatos com tempo de validade e origem | MemGPT/LongMemEval [E], engenharia própria | Últimos turnos; resumo único; busca sem filtro temporal | Recall de evidências, resposta temporal, atualização e exclusão |
| C10 | Recuperar primeiro, montar contexto com tokenizer real, compactar seletivamente | MemGPT/LongMemEval [E], engenharia própria | Contexto amplo; resumo recursivo; recuperação sem resumo | Retenção de fatos críticos e qualidade sob igual orçamento |
| C11 | CP-SAT local sobre candidatos de blocos; validação independente e mínima alteração | OR-Tools [N]; ToRA como analogia de ferramentas | Earliest-deadline-first; MILP; intervalos CP-SAT | Viabilidade, demanda atendida, alterações e latência |
| C12 | ICS por biblioteca, UID persistente; sincronização com outbox, versão e reconciliação | RFC 5545/4791 [N]; Google Calendar [N] | Exportação manual; CalDAV; API via MCP opcional | Round-trip, timezone, ausência de duplicação e concorrência |

## 3. C06 — Tutor ativo e biblioteca de skills

### 3.1 Fundamento, evidência e limites

Chi et al. (`chi1994selfexplanation`) contrastam 14 alunos da oitava série solicitados a se autoexplicar sobre circulação humana com dez que leram o texto duas vezes; o resumo editorial relata maior ganho pré–pós e diferenças de compreensão entre níveis de autoexplicação. **[E]** Trata-se de domínio/população específicos; não prova que qualquer paráfrase, fala longa ou diálogo socrático gere entendimento. A referência popular à “Técnica de Feynman” na proposta deve ser operacionalizada como **autoexplicação elicitada e avaliada**, sem atribuir eficácia científica ao rótulo.

Roediger e Karpicke (`roediger2006testing`) usam passagens em prosa, recuperação livre sem feedback e releitura. **[E]** No experimento 1, 120 universitários, passagens com 30 unidades de ideia e testes após cinco minutos, dois dias ou uma semana; releitura favoreceu a medida imediata, recuperação favoreceu retenção tardia. Portanto, desempenho imediatamente após explicação e confiança declarada não são medidas suficientes de retenção. A fonte sustenta recuperação ativa, **não uma sequência universal de intervalos de flashcards**, nem o benefício específico do feedback automático aqui proposto.

Wood, Bruner e Ross (`wood1976tutoring`) é referência histórica de scaffolding, mas nesta consulta somente sua identidade bibliográfica ficou acessível; detalhes empíricos e funções de apoio exigem leitura integral antes de serem usados como evidência. O procedimento abaixo é uma adaptação [P], apoiada operacionalmente no MultiTutor e nas fontes pedagógicas acessíveis.

MultiTutor (`sun2025multitutor`) distribui explicação, scaffolding, pesquisa, recursos e visualização; seu scaffolding reorganiza conteúdo em progressão de dificuldade. Avalia 25 perguntas simuladas de cinco áreas, com GPT-4o como juiz e métricas de texto, não trajetórias reais de aprendizagem. O MVP pode aproveitar especialização e artefatos; não importar geração multimodal nem presumir benefício causal de seis agentes.

### 3.2 Procedimento implementável [P]

1. Receber intenção, tópico, objetivo, pacote documental com origem e snapshot de evidências. Se a solicitação for definição, consulta pontual ou resposta direta explícita, explicar diretamente; se for prática, iniciar tentativa. Se não houver material suficiente, pedir contexto antes de inventar exercício/gabarito.
2. Selecionar uma skill por tarefa e verificar suas pré-condições. Emitir **uma atividade principal por turno** e terminar em `waiting_student`; esperar não dispara novos turnos do modelo.
3. Em `attempt`, pedir resposta sem mostrar solução. Em `assess`, encaminhar resposta ao Monitor com item/rubrica e histórico de ajuda. Em `hint`, oferecer apoio localizado: orientação conceitual → próximo passo → exemplo análogo → solução comentada. Ajustar apoio ao erro efetivamente observado.
4. Após solução comentada, pedir autoexplicação de uma relação causal, condição de validade ou contraste: “Por que este passo é válido? Em que caso falha?”. Avaliar conteúdo conceitual e relações, não coincidência lexical com o texto-fonte.
5. Em `transfer`, apresentar novo item isomorfo, sem pistas iniciais, com `item_family_id` para distinguir variação de repetição. Flashcard exige tentativa antes de revelar verso; registrar `answer_revealed`, atraso e ajuda.
6. Em `close`, fornecer síntese curta, evidência produzida e recomendação de revisão. Recusa, cancelamento, pedido de solução e limite de tentativas são terminais legítimos. Uma resposta copiada após revelação não conta como desempenho independente.

**Contrato da skill:** `skill_id, version, task_types, input_schema, preconditions, steps, allowed_tools, output_schema, postconditions, stop_conditions, budget, evaluation_cases`. Catálogo inicial [P]: `explain`, `graduated_hint`, `quiz`, `flashcard`, `self_explain`. Pós-condições verificam fonte, objetivo, existência de gabarito/rubrica, separação pergunta/solução e terminal. Mudança de prompt gera versão; registrar hash usado em cada turno. Melhorias de skills passam por avaliação offline antes de publicação; um acerto isolado do LLM não autoriza modificação automática da biblioteca.

**Transferência de Voyager:** sua skill é programa executável indexado por descrição, refinado com feedback e reutilizado em Minecraft. Aqui é procedimento pedagógico com validadores, não habilidade cognitiva do aluno nem compressão comprovadamente sem perdas. MetaGPT contribui SOPs e artefatos intermediários; não define método de ensino.

**Alternativas e teste:** comparar explicação direta com tutoria ativa em casos que exigem cada modalidade; comparar prompt monolítico com seleção de skills, preservando modelo, fontes, ferramentas e orçamento. Avaliar por anotadores se houve apoio adequado, pistas sem solução antecipada, exercício válido e término. Simulações verificam fluxo; ganho de aprendizagem requer alunos reais, pré-teste, pós-teste tardio e itens de transferência, com controle de tempo de estudo.

## 4. C07 — Monitor com rubricas e incerteza separada do domínio

### 4.1 Método e procedimento [P]

**Entrada:** `attempt_id, user_id, topic_ids, item_id/family/version, response_text, reference_answer, rubric_id/version, source_ids, help_level, reveal_status, occurred_at`. Rubrica deve anteceder avaliação: critérios, descritores por nível, equivalências aceitáveis, erros conceituais críticos e trechos de origem. Um gabarito gerado pelo mesmo LLM precisa de validação documental ou especialista; não é ouro independente.

1. Verificar se item, resposta e fonte são avaliáveis. Resposta vazia, ambiguidade de enunciado, imagem não disponível, referência conflitante ou critério sem apoio geram `insufficient_evidence`/`abstain` com motivo.
2. Usar comparador exato, tolerância numérica com unidades, equivalência simbólica ou testes executáveis quando o item permitir. Essas ferramentas verificam a propriedade formalizada, não toda a justificativa pedagógica; uma ferramenta incapaz de decidir não transforma resposta em errada.
3. Para texto aberto, fornecer ao Monitor enunciado, referência e rubrica, sem a autodeclaração de sucesso do Tutor. Produzir por critério `level, response_span, justification, misconception_code, uncertainty_reason`. Checar que o span existe na resposta; não inventar evidência.
4. Registrar **separadamente** corretude, apoio recebido, cobertura de critérios e confiabilidade da avaliação. `correctness=partial` não é automaticamente probabilidade de domínio. O Monitor produz observação e recomendação; a atualização de estado cabe a um redutor determinístico.
5. Onde houver divergência com ferramenta, falta de critérios essenciais ou baixa confiabilidade, suspender atualização inferencial e pedir esclarecimento/revisão. Comunicar feedback útil mesmo quando o resultado não pode ser agregado.

Exemplo de rubrica [P] para justificar um algoritmo: **condições de aplicação**, **invariante/argumento**, **conclusão com limites**; níveis locais `0=ausente/incorreto`, `1=parcial`, `2=adequado`. Avaliar cada dimensão; um argumento incorreto com linguagem fluente não recebe nível adequado. A escala é proposta do projeto, não a escala 1–5 publicada pelo Prometheus.

### 4.2 Incerteza e validação

Prometheus (`kim2024prometheus`) usa instrução, resposta, rubrica e referência como entradas; reporta correlação humana de 0,897 em 45 instâncias/rubricas de benchmarks de respostas de LLMs. **[E]** É um modelo treinado em feedback sintético, não valida um juiz local genérico, respostas de estudantes ou rubricas em português. Correlação global também não mede taxa de falsos “domínios”. Adotar seu desenho de entrada, e calibrar o Monitor no domínio do projeto.

Farquhar et al. (`farquhar2024semanticentropy`) amostram respostas, agrupam por equivalência semântica via implicação bidirecional e calculam entropia; para QA de sentenças usam dez gerações. **[E]** Detectam confabulações, mas não erros sistemáticos consistentemente reproduzidos. Entropia baixa não garante gabarito correto; variabilidade do **juiz** não é incerteza cognitiva do **aluno**.

Aplicação opcional [P]: reavaliar a mesma resposta sob seeds diferentes, agrupar **decisões por critério**, medir desacordo e usá-lo como sinal de abstinência. Isso é proxy de estabilidade, **não reprodução literal da entropia semântica do artigo**. Entropia semântica propriamente dita exigiria amostragem de afirmações, verificação de equivalência e implementação/calibração próprias. Começar com motivos categóricos; não expor `confidence=0.9` verbal do modelo como probabilidade calibrada.

Validação [P]: duas anotações humanas independentes, adjudicação, exemplos curtos/longos, paráfrases, erros plausíveis, respostas parcialmente corretas e ajuda graduada. Separar famílias de itens entre ajuste e teste. Medir kappa ponderado por critério, F1 de erros, evidências inventadas, curvas risco–cobertura e custo. Se houver probabilidade de avaliação correta aprendida no conjunto de calibração, medir Brier e diagrama de confiabilidade. Preservar conjunto final intocado e estratificar por disciplina e ajuda.

## 5. C08 — Estado de aprendizagem, cold-start e knowledge tracing

### 5.1 Decisão de cold-start [P]

No primeiro contato: `status=insufficient_evidence`, `observed_attempts=0`, estimativa inferencial `null`. Preferência, autorrelato, texto do Tutor e material lido são eventos de contexto, não prova de competência. Oferecer diagnóstico curto sobre tópicos prioritários com itens identificados; nunca extrapolar uma resposta para a disciplina inteira.

Persistir por tópico: tentativas independentes/assistidas, erros por critério, datas, famílias distintas, exposição à solução, última recuperação tardia e próximo objetivo. O MVP usa esse **estado observado**, sem “percentual de domínio” fabricado. Uma regra de interface pode mostrar “evidência recente favorável”, mas não substituir incerteza por um selo definitivo.

### 5.2 BKT como estimador auditável, depois do ajuste

Corbett e Anderson (`corbett1995knowledgetracing`) identificam o trabalho fundador. O ano conferido no registro editorial/Crossref é **1995**, embora pyBKT o cite como 1994; manter essa divergência explícita. O método abaixo foi conferido nas equações do texto de `badrinath2021pybkt`.

Para um componente de conhecimento, BKT tem estado binário latente, prior `p0`, transição de aprendizado `T`, guess `G` e slip `S`. Dado `p=P(L_t)`:

```text
P(correct_next) = p*(1-S) + (1-p)*G
q_correct       = p*(1-S) / (p*(1-S) + (1-p)*G)
q_incorrect     = p*S     / (p*S     + (1-p)*(1-G))
p_next          = q + (1-q)*T                       # BKT sem esquecimento
p_next_forget   = q*(1-F) + (1-q)*T                 # extensão por oportunidade
```

Um `F` por oportunidade não é taxa por dia. **Não aplicar exponencial temporal escolhida arbitrariamente** nem converter esse parâmetro em curva cognitiva sem estimação. BKT básico assume ausência de esquecimento e não modela todos os pré-requisitos, dificuldade ou múltiplos conceitos de uma resposta aberta.

Procedimento [P]: definir componentes menores que disciplinas; mapear item a componente validado; binarizar apenas resultados decidíveis e independentes segundo regra predefinida, mantendo parciais/ajuda no registro; ajustar parâmetros por componente ou agrupamento usando logs autorizados, com múltiplas inicializações; salvar parâmetros e dataset/versão; fazer atualização cronológica idempotente por `attempt_id`; comparar previsão da próxima resposta com baseline observado/logístico. Para itens multicomponente, usar critérios separáveis ou não atualizar o BKT simples, evitando atribuir o mesmo erro indiscriminadamente a todos os tópicos.

pyBKT oferece EM, previsão, validação cruzada e extensões de dificuldade/esquecimento. Sua análise de suficiência é principalmente sintética sob parâmetros específicos; referências a 50 alunos ou 15 respostas **não são mínimos universais** para este projeto. Para aluno novo com modelo ajustado, usar prior populacional do componente, indicado como inferido; para tópico novo sem modelo, manter `null`. Parâmetros de outras disciplinas não se tornam calibrados por importação.

### 5.3 Revisão temporal e alternativas

Separar estimativa e atualidade: `estimated_at`, `last_independent_attempt_at`, `last_delayed_retrieval_at`, `evidence_ids`, `model_version`, `review_due`. Ausência de prática torna evidência antiga, **não é observação de erro**. Gerar revisão por política explícita e deixar o desempenho tardio corrigir o estado.

Comparar [P] contadores transparentes, regressão logística de acertos/erros e BKT, depois BKT+Forget se houver dados temporais. Modelos profundos/IRT são alternativas futuras por exigirem logs e itens mais estáveis; esta pesquisa não os verificou como superiores. Selecionar por previsão prospectiva, log loss/Brier, calibração por tópico/cold-start e custo; não apenas AUC. Split por aluno e corte temporal evitam futuro no passado. Sem dados suficientes, o estado observado é a decisão operacional, e BKT fica em avaliação paralela.

## 6. C09 — Memória longitudinal com origem e temporalidade

### 6.1 Método e esquema [P]

MemGPT (`packer2023memgpt`) demonstra contexto ativo/externo e movimentação por ferramentas em conversa e análise documental; sua qualidade depende da capacidade de ferramentas do modelo e os baselines incluem resumos com perda. LongMemEval (`wu2025longmemeval`) distingue indexação, recuperação e leitura; avalia extração, múltiplas sessões, raciocínio temporal, atualização e abstinência. Seu texto mostra que rounds podem funcionar melhor que sessões inteiras e que comprimir valores apenas em fatos pode perder detalhes. **[E]** Nenhuma das fontes define um perfil pedagógico validado ou transações deste projeto.

Modelo local proposto:

| Armazenamento | Campos mínimos | Regra |
|---|---|---|
| Evento original | `event_id, user_id, session_id, kind, payload, occurred_at, recorded_at, source_ids, schema_version` | Append-only no uso ordinário; conteúdo original consultável |
| Fato de perfil | `fact_id, key, value, valid_from/to, asserted_at, authority, source_event_ids, supersedes, version` | Corrigível por nova versão; preferências declaradas não são domínio |
| Estado por tópico | `topic_id, evidence_ids, observed_state, estimate, model_version, computed_at, revision` | Projeção reproduzível a partir de evidências |
| Síntese | `summary_id, topic_ids, covered_event_ids, coverage_interval, claims_with_sources, generator_version, verification_status` | Derivado; não substitui originais |
| Vínculos | `corrects, supersedes, derived_from, deleted_by` | Proveniência e invalidação transitiva |

Usar **tempo do fato** (`valid_from/to`, ou intervalo do acontecimento) e **tempo de registro** (`recorded_at`) separadamente. Uma mudança informada hoje pode valer desde ontem; “semana passada” é resolvida relativamente à data/timezone da fala, com pendência se ambígua. Datas acadêmicas confirmadas têm autoridade superior a sugestões; não usar simplesmente “o documento mais recente vence”.

### 6.2 Procedimento de escrita, recuperação e correção [P]

1. Transação grava evento, chave única e projeção/outbox; retry do mesmo `event_id/attempt_id` não atualiza domínio duas vezes. Agentes leem snapshot versionado; concorrência verifica revisão esperada.
2. Extrair fatos candidatos com spans/IDs e estatuto `observed/asserted/inferred`. Hipóteses como “dificuldade recorrente” carregam evidências, não passam a fato declarado.
3. Indexar rounds/eventos por usuário, disciplina, tópico, tipo e datas; fatos e sínteses ampliam chaves de busca, mas retorno pode incluir valor original. Isolamento por usuário deve ocorrer **antes** de similaridade/ranking.
4. Recuperar com query de tópico/intenção e intervalo temporal. Para “estado atual”, trazer projeção vigente e evidências relevantes; para “como mudou”, trazer versões anteriores e correções em ordem temporal. Similaridade ou recência não podem suprimir correção autoritativa.
5. Contexto contém IDs, tempos, fonte e status. Se houver contradição não reconciliada, retornar os dois registros e pedir esclarecimento, em vez de inventar conciliação.
6. Correção adiciona evento e invalida/recalcula projeções e sínteses dependentes. **Exclusão é exceção explícita ao append-only:** remover ou tornar irrecuperável o payload e propagar a remoção a índices, resumos, caches e política de backups; tombstone mínimo, sem conteúdo excluído, evita ressurreição por replay. Hash de texto curto pode revelar conteúdo e não deve ser preservado automaticamente.

Alternativas: últimos N turnos (barato, esquece longo prazo); resumo único (compacto, mistura versões); busca vetorial pura (perde autoridade e tempo); banco de eventos com filtros e busca híbrida (mais engenharia, auditável). Comparar perguntas atuais, retrospectivas, agregação de erros, mudança de preferência, correção retroativa e perguntas sem resposta; medir recall de IDs, fidelidade, temporalidade, abstinência e ausência de vazamento entre usuários. LongMemEval orienta **tipos de teste**, não fornece ouro educacional em português.

## 7. C10 — Orçamento e compactação de contexto

### 7.1 Procedimento [P]

Definir `W` como janela operacional verificada do runtime e contar a serialização real com tokenizer/template do modelo. Antes de cada chamada:

```text
input_tokens + reserved_output + reserved_tool_result + safety_margin <= W
```

Reservas são limites locais [P], não a janela anunciada sem verificação. Incluir instruções, schema de ferramentas, delimitadores e histórico serializado na contagem; ferramentas têm resultado truncável/paginável com IDs e sinalização de corte.

1. Fixar âncoras: intenção atual, item/rubrica, tentativa aguardada, fatos temporais confirmados relevantes, evidências e status. Não descartar rubrica para caber uma explicação longa.
2. Recuperar histórico por tópico e tempo; deduplicar por ID. Carregar skill específica em vez de todas as instruções. Ordenar evidências temporalmente e separar fonte documental de memória pessoal.
3. Se exceder budget, reduzir candidatos menos relevantes e buscar segmentos menores. Somente então sintetizar trechos antigos: objetivos, erros com evidência, ajuda, resultados, decisões, datas e pendências. Conteúdo numérico e prazos vêm de campos estruturados protegidos, não de reconstrução livre.
4. Sumarizar de originais referenciados; evitar cadeias indefinidas resumo → resumo. Checar datas, IDs, polaridade, corretude e ajuda contra originais. Afirmação sem origem é removida ou marcada pendente. Checagem por LLM é auxiliar, não oráculo independente.
5. Publicar síntese validada com versão e manifesto de cobertura. Em falha, manter seleção de originais, reduzir a tarefa ou pedir divisão. Recontar **depois** da montagem e antes da geração; compactação ocorre entre chamadas, não durante geração.

### 7.2 Evidência, alternativas e avaliação

MemGPT usa FIFO, armazenamento de recall e resumo recursivo; exemplos de limiares no artigo não são configuração validada do EduAgent-OS. LongMemEval sugere preservar rounds e usar fatos no índice, evitando confundir índice enriquecido com valor resumido. Escolher recuperação + síntese com proveniência [P] como núcleo; gerenciamento totalmente autônomo pelo LLM aumenta chamadas e depende de capacidade local ainda desconhecida.

Comparar [P] recuperação de originais, recuperação+síntese, resumo recursivo e contexto amplo em trajetórias idênticas, orçamento total contado. Medir retenção exata de fatos críticos, omissões, contradições, recuperabilidade por ID, desempenho downstream e tokens/latência. Uma síntese menor que altera “acertou com pista” para “domina” falha independentemente de ROUGE. Tolerância zero para prazo confirmado alterado e atribuição de evidência inexistente é **critério de engenharia [P]**, não resultado da literatura.

## 8. C11 — Demanda pedagógica, CP-SAT e replanejamento

### 8.1 Fronteira entre linguagem e solver

O LLM interpreta necessidades e produz demanda estruturada `task_id, topic_ids, activity_type, duration_minutes, release, deadline, mandatory, dependencies, priority_reason, evidence_ids`. Duração é estimativa ou entrada confirmada, nunca inferida de `1 - mastery` por uma fórmula cognitiva arbitrária. Preferências têm pesos/regras locais explícitos. Só restrições confirmadas entram como duras; prazo ambíguo permanece pendente.

ToRA (`gou2024tora`) intercala raciocínio e ferramentas e envolve treinamento de modelos matemáticos. **[E]** É inspiração de divisão entre interpretação e operação formal, não prova de que um prompt com OR-Tools herdará seu desempenho. OR-Tools (`google2024cpsat`, `googleEmployeeScheduling`) fornece mecanismo [N] de variáveis inteiras, restrições e objetivos; não determina prioridades pedagógicas.

### 8.2 Formalização implementável por candidatos de blocos [P]

Para horizonte semanal, gerar candidatos `b` de **blocos contíguos**, por tarefa `i`, com começo `s_b`, fim `e_b`, duração `d_i` e slots ocupados `O_b`. Variável `x_b ∈ {0,1}`. Candidatos já devem respeitar janela da tarefa, disponibilidade e compromissos; conservar IDs e fonte de cada filtro.

```text
Para tarefa obrigatória i: sum(x_b para b de i) = 1
Para tarefa opcional i:    sum(x_b para b de i) <= 1
Para todo slot t:         sum(x_b com t em O_b) <= 1
Para dependência i -> j:  e_i <= s_j quando ambas presentes
Para todo dia:            sum(d_i * presença_i) <= limite diário confirmado
```

Disponibilidade pode conter limites no meio de slots: arredondar abertura para cima, fechamento/prazo para baixo e bloqueios para fora, registrando conservadorismo; nunca permitir sobreposição criada por arredondamento. Tarefas longas só são decompostas em blocos se divisibilidade estiver declarada e soma preservar duração. Duração não múltipla do slot ocupa capacidade arredondada para cima, sem reduzir minutos exigidos.

Guardar instantes UTC para comparar intervalos e timezone IANA para disponibilidade/apresentação. Converter janelas locais por dia usando regras da zona, não somar dias UTC cegamente. Horas ambíguas/inexistentes exigem política explícita ou confirmação. Um prazo só de data precisa de semântica confirmada (não presumir 23:59). Blocos iniciados/concluídos e compromissos externos são imutáveis no replanejamento.

**Objetivos [P]:** primeiro maximizar atendimento de tarefas opcionais por classe de prioridade documentada; depois minimizar número de blocos futuros movidos/removidos; depois minimizar deslocamento em slots; finalmente atender preferências/espalhamento. Otimização lexicográfica por solves sucessivos só fixa o ótimo de uma etapa se houver prova `OPTIMAL`; se houver apenas `FEASIBLE`, reportar incumbent/bound, sem alegar mínimo de alterações. Um único objetivo ponderado é alternativa, mas requer limites que impeçam pesos de trocar prioridade por conveniência silenciosamente.

### 8.3 Procedimento e falhas

1. Ler snapshot de agenda e demandas, validar timezone/durações/IDs, detectar ciclos de dependência e candidatos vazios.
2. Construir modelo, validar estrutura e resolver sob limite registrado. Guardar versão OR-Tools, parâmetros, seed, workers, tempo, objetivo/bound e snapshot hash.
3. **[N]** `OPTIMAL`: ótima viável; `FEASIBLE`: viável sem prova de ótimo; `INFEASIBLE`: inviabilidade provada para o modelo; `UNKNOWN`: interrupção sem solução/prova, podendo incluir timeout; `MODEL_INVALID`: erro de construção. Não chamar `UNKNOWN` de inviável.
4. Validar solução fora do solver: reaplicar disponibilidade, sobreposição, duração, precedência, prazo e imutabilidade sobre instantes reais. Revalidar snapshot antes de publicar.
5. Em inviabilidade, apresentar restrições responsáveis. Um diagnóstico pode usar literais de assumptions e núcleo suficiente de conflito, quando a versão/encoding suportar; núcleo suficiente **não é necessariamente mínimo**. Alternativa implementável: retirar grupos em cópias diagnósticas e verificar viabilidade. Nunca publicar cópia relaxada como plano confirmado.
6. Comparar plano novo ao aprovado, preview com adições/movimentos/remoções e razões de evidência. Plano sem tempo para toda demanda mostra déficit; não remove compromissos nem encurta tarefa obrigatória silenciosamente.

Alternativas [P]: greedy por prazo é baseline simples e explicável, sem garantia de encontrar plano existente; MILP é adequado à formulação binária; intervalos opcionais/`NoOverlap` em CP-SAT evitam matriz grande para durações variadas. Escolher candidatos no MVP pela facilidade de auditoria; comparar intervalos se crescer o número de candidatos. Verificação: instâncias pequenas com enumeração independente, conflitos deliberados, bordas de horário, prazo no meio de slot, replanejamento com blocos fixos e timeout. Medir violações, demanda atendida, churn e latência; agenda formalmente ótima não implica aprendizagem ótima.

## 9. C12 — ICS, calendário idempotente e concorrência

### 9.1 Exportação [N] e decisões [P]

RFC 5545 (`desruisseaux2009icalendar`) define representação, não entrega exatamente uma vez. Gerar por biblioteca: `VCALENDAR`, `VERSION:2.0`, `PRODID`, `VEVENT`, `UID`, `DTSTAMP`, `DTSTART`, `DTEND`, `SUMMARY`. Fim é exclusivo; não incluir simultaneamente `DTEND` e `DURATION`. Texto deve escapar separadores/quebras e serializar UTF-8/CRLF, com folding recomendado a 75 octetos preservando caracteres multibyte. Se usar hora local com `TZID`, incluir `VTIMEZONE` correspondente; alternativa inicial [P] usa UTC `Z` no evento e mantém zona na interface/manifesto. Eventos all-day usam `DATE`, com fim no dia seguinte ao último dia incluído.

Persistir UID opaco na criação do **bloco lógico**; mudanças de horário mantêm UID e atualizam `SEQUENCE`/`LAST-MODIFIED` conforme revisão. Não derivar UID do horário, texto ou versão do plano. Exportar novamente o mesmo snapshot deve manter UIDs e metadados de revisão; não recriar `DTSTAMP` arbitrariamente em cada retry. Plano adaptativo começa com eventos individuais [P]; compromissos recorrentes importados são expandidos no horizonte com exceções antes do solver.

**Limite:** importar o mesmo arquivo ICS duas vezes pode duplicar eventos dependendo do cliente; UID estável é condição de interoperabilidade, **não garantia universal de deduplicação de importação manual**. Exportação local idempotente e sincronização remota idempotente são contratos diferentes. Preview e confirmação referenciam hash/revisão do plano; confirmação vencida por alteração exige novo preview.

### 9.2 Sincronização implementável [P]

Outbox transacional contém `operation_id, calendar_id, logical_block_id, target_revision, operation_kind, payload_hash, confirmation_id, remote_id/href, etag, state`. Chave única para operação lógica/revisão; UID/remote ID são estáveis entre revisões, enquanto chave da operação distingue mudanças. Estados: `pending → sending → confirmed`, ou `unknown_effect → reconcile`, ou `conflict/failed`.

1. Worker obtém operação confirmada e revisão esperada; processa com lock/controle otimista por bloco e impede que revisão antiga sobrescreva nova.
2. **CalDAV [N]:** RFC 4791 (`daboo2007caldav`) define UID único na coleção, recurso persistente e ETags; criação usa PUT no href estável com `If-None-Match: *`, atualização usa `If-Match` com ETag corrente. Conflito de precondição exige leitura/reconciliação, não escrita incondicional.
3. **Google [N]:** `google2026calendarcreate` documenta ID fornecido pelo cliente para impedir duplicação após criação com falha de resposta. Adaptador deve codificar ID no formato aceito; UID ICS e `event.id` não são intercambiáveis automaticamente. A consulta desta rodada verificou criação; atualização condicional e sincronização incremental do Google precisam de documentação adicional antes da implementação.
4. Timeout deixa efeito desconhecido. Ler por remote ID/href (ou UID quando necessário), comparar campos geridos/payload normalizado e versão. Se efeito desejado existe, concluir outbox; se ausente, repetir com mesma identidade; se mudou externamente, registrar conflito e produzir novo preview. Resultado normalizado evita interpretar reformatação do servidor como mudança semântica.
5. Confirmar após leitura do efeito, persistindo remote ID/ETag. Deleção remota também usa identidade/versionamento; ausência após retry só conclui remoção se houver prova de que se consulta o alvo correto. Não recriar eventos apagados pelo usuário durante reconciliação automática.
6. MCP opcional transporta chamada, mas não cria idempotência. O conector precisa preservar IDs, precondições, motivos de erro e capacidade de leitura pós-timeout. Se a ferramenta não oferece essas capacidades, ficar em preview/exportação ou registrar efeito desconhecido, sem retry cego.

Alternativas: ICS manual é offline e simples, mas sem controle do importador; CalDAV tem semântica explícita de recursos/concorrência; API Google integra destino específico com contrato próprio. Testes [P]: round-trip por parser independente, caracteres portugueses, timezone/horário de verão, evento all-day, retry antes/depois do efeito, crash depois da escrita antes do ACK, atualização concorrente, deleção externa e duas revisões em ordem invertida. Critérios: zero duplicação no adaptador testado, conflitos visíveis, correspondência entre plano aprovado e efeito observado. Não prometer exactly-once distribuído sem hipóteses do backend.

## 10. Registro das fontes efetivamente consultadas

Todos os itens: acesso em 30/09/2026. Autoria completa consta no BibTeX; abreviação “et al.” abaixo remete à lista integral verificada no registro arXiv. URLs auxiliares são consultas ao mesmo trabalho, não novas evidências independentes.

| # / bib key | Título, autores, ano e URL consultada | Conteúdo acessado e contexto de uso |
|---|---|---|
| 1 `wood1976tutoring` | **The Role of Tutoring in Problem Solving** — David Wood, Jerome S. Bruner, Gail Ross, 1976. https://doi.org/10.1111/j.1469-7610.1976.tb00381.x ; https://api.crossref.org/works/10.1111/j.1469-7610.1976.tb00381.x | DOI retornou citação; Crossref confirmou autores, periódico, 17(2):89–100. Texto editorial bloqueado. Referência histórica identificada, sem extrair resultados não lidos. |
| 2 `chi1994selfexplanation` | **Eliciting Self-Explanations Improves Understanding** — Michelene T. H. Chi, Nicholas de Leeuw, Mei-Hung Chiu, Christian Lavancher, 1994. https://doi.org/10.1207/s15516709cog1803_3 ; https://api.crossref.org/works/10.1207/s15516709cog1803_3 | Metadados e resumo experimental depositado pelo editor; texto completo bloqueado. Autoexplicação, tamanho dos grupos, domínio e avaliação pré–pós; não estimar efeito além do resumo. Ano original 1994, não disponibilização online em 2010. |
| 3 `roediger2006testing` | **Test-Enhanced Learning: Taking Memory Tests Improves Long-Term Retention** — Henry L. Roediger III, Jeffrey D. Karpicke, 2006. https://api.crossref.org/works/10.1111/j.1467-9280.2006.01693.x ; https://learninglab.psych.purdue.edu/downloads/2006/2006_Roediger_Karpicke_PsychSci.pdf | Registro com resumo e PDF original no laboratório do coautor, convertido/lido: resumo, introdução e método/avaliação do experimento 1. Recuperação versus releitura e medidas tardias; feedback proposto não foi testado nessa condição. |
| 4 `sun2025multitutor` | **MultiTutor: Collaborative LLM Agents for Multimodal Student Support** — Edward Sun, LeAnn Tai, 2025. https://proceedings.mlr.press/v273/sun25a.html ; https://raw.githubusercontent.com/mlresearch/v273/main/assets/sun25a/sun25a.pdf | Página PMLR com BibTeX; PDF convertido/lido §§2–3: papéis, estado estruturado, 25 perguntas simuladas, juiz e métricas de texto. C06 e auditoria da proposta. |
| 5 `packer2023memgpt` | **MemGPT: Towards LLMs as Operating Systems** — Charles Packer, Sarah Wooders, Kevin Lin, Vivian Fang, Shishir G. Patil, Ion Stoica, Joseph E. Gonzalez, 2023; revisão v2/2024. https://arxiv.org/abs/2310.08560 ; https://arxiv.org/html/2310.08560v2 | Identidade e texto §§2–3: contexto, FIFO, ferramentas, resumo, recall, benchmarks e influência do modelo. C09/C10. Bib usa ano do preprint original e nota da versão lida. |
| 6 `wang2023voyager` | **Voyager: An Open-Ended Embodied Agent with Large Language Models** — Guanzhi Wang, Yuqi Xie, Yunfan Jiang, Ajay Mandlekar, Chaowei Xiao, Yuke Zhu, Linxi Fan, Anima Anandkumar, 2023. https://arxiv.org/abs/2305.16291 ; https://arxiv.org/html/2305.16291v2 | Texto §§2–4: biblioteca de programas, recuperação, feedback, comparação e limites. Transferência para skills pedagógicas; não evidência de compressão de prompts. |
| 7 `hong2024metagpt` | **MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework** — Sirui Hong et al., 2024 (v7). https://arxiv.org/abs/2308.00352 ; https://arxiv.org/html/2308.00352v7 | Identidade e lista de autores; texto §§3–4: SOPs, comunicação estruturada, feedback executável e resultados de engenharia de software. Adaptação arquitetural, sem evidência educacional. Bib cita a versão arXiv consultada; tentativa de conferência editorial em OpenReview bloqueada. |
| 8 `gou2024tora` | **ToRA: A Tool-Integrated Reasoning Agent for Mathematical Problem Solving** — Zhibin Gou, Zhihong Shao, Yeyun Gong, Yelong Shen, Yujiu Yang, Minlie Huang, Nan Duan, Weizhu Chen, 2024. https://arxiv.org/abs/2309.17452 ; https://arxiv.org/html/2309.17452v4 | Registro confirma ICLR 2024; texto §§2–3: treinamento, interação com ferramentas e falhas de formalização/raciocínio. Analogia para C11, sem importar ganhos matemáticos. |
| 9 `kim2024prometheus` | **Prometheus: Inducing Fine-grained Evaluation Capability in Language Models** — Seungone Kim et al., 2024. https://arxiv.org/abs/2310.08491 ; https://arxiv.org/html/2310.08491v2 | Registro confirma ICLR 2024; texto de construção, entradas, avaliação humana e ablação. C07: rubrica/referência; correlação não é calibração educacional. |
| 10 `farquhar2024semanticentropy` | **Detecting hallucinations in large language models using semantic entropy** — Sebastian Farquhar, Jannik Kossen, Lorenz Kuhn, Yarin Gal, 2024. https://www.nature.com/articles/s41586-024-07421-0 | Texto principal e método: agrupamento semântico, dez gerações em QA, métricas de rejeição e limitação para erro sistemático. C07 e custo da incerteza. |
| 11 `corbett1995knowledgetracing` | **Knowledge tracing: Modeling the acquisition of procedural knowledge** — Albert T. Corbett, John R. Anderson, 1995 no registro editorial. https://doi.org/10.1007/BF01099821 ; https://api.crossref.org/works/10.1007/BF01099821 | Identidade e 4(4):253–278 verificados; página Springer com challenge. Equações não atribuídas a leitura integral deste artigo; conferidas no item 12. Divergência 1994/1995 documentada. |
| 12 `badrinath2021pybkt` | **pyBKT: An Accessible Python Library of Bayesian Knowledge Tracing Models** — Anirudhan Badrinath, Frederic Wang, Zachary Pardos, 2021. https://arxiv.org/abs/2105.00385 ; https://arxiv.org/html/2105.00385v2 | Texto com equações, EM, extensões, suficiência sintética e avaliações de previsão. Registro diz aceito EDM 2021; Bib cita versão arXiv consultada, sem inventar paginação. |
| 13 `wu2025longmemeval` | **LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory** — Di Wu, Hongwei Wang, Wenhao Yu, Yuwei Zhang, Kai-Wei Chang, Dong Yu, 2025. https://arxiv.org/abs/2410.10813 ; https://arxiv.org/html/2410.10813v2 | Registro confirma ICLR 2025; texto §§3–5: tipos de pergunta, indexação/recuperação/leitura, granularidade, tempo e protocolo de avaliação. C09/C10. |
| 14 `google2024cpsat` | **CP-SAT Solver** — Google, atualização 28/08/2024. https://developers.google.com/optimization/cp/cp_solver | Documentação dos mantenedores, tipos inteiros, código e significados dos cinco status. C11. |
| 15 `googleEmployeeScheduling` | **Employee Scheduling** — Google, **s.d.** na parte inspecionada. https://developers.google.com/optimization/scheduling/employee_scheduling | Exemplo dos mantenedores: variáveis booleanas, exatamente/ao máximo um, cobertura e preferências. Transferência para blocos; ano não inferido da data de acesso. |
| 16 `desruisseaux2009icalendar` | **Internet Calendaring and Scheduling Core Object Specification (iCalendar)** — Bernard Desruisseaux (editor), 2009. https://www.rfc-editor.org/rfc/rfc5545.html | RFC primária: gramática, linhas/UTF-8 e componentes; consulta direcionada a VEVENT, TZID/VTIMEZONE, UID, fim e revisão (§§3.1, 3.3, 3.6, 3.8). C12. |
| 17 `daboo2007caldav` | **Calendaring Extensions to WebDAV (CalDAV)** — Cyrus Daboo, Bernard Desruisseaux, Lisa Dusseault, 2007. https://www.rfc-editor.org/rfc/rfc4791.html | RFC primária: modelo de recursos, UID único, precondições de PUT/ETags (§§4.1, 5.3.2–5.3.4), consulta por UID e sincronização. C12. |
| 18 `google2026calendarcreate` | **Create events** — Google, atualização 11/09/2026. https://developers.google.com/workspace/calendar/api/guides/create-events | Documentação primária: campos de início/fim e ID fornecido pelo cliente para impedir duplicação após criação. C12; não verificar atualização/incremental por mera presença de links. |

**Versão bibliográfica de MetaGPT:** o corpo do artigo consultado identifica os 15 autores reproduzidos no BibTeX. A tentativa em OpenReview não passou do challenge; portanto a entrada é da versão arXiv v7/2024, sem declarar conferência do registro editorial. O primeiro preprint é de 2023; ICLR 2024, indicado na proposta, permanece com verificação editorial pendente nesta rodada. Essa pendência não afeta a identidade nem a leitura do método na versão arXiv.

## 11. Trilha de localização, tentativas e exclusões

| Etapa / alvo | Caminho efetivamente usado | Resultado e decisão |
|---|---|---|
| Âncoras da proposta | PMLR `sun25a` e arXiv `2310.08560`, `2305.16291`, `2308.00352`, `2309.17452` | Cinco trabalhos identificados; aprofundamento em HTMLs e PDF MultiTutor. Não copiar BibTeX de fase1. |
| Scaffolding | DOI Wood → Crossref → `https://acamh.onlinelibrary.wiley.com/doi/10.1111/j.1469-7610.1976.tb00381.x` | Citação/metadados acessíveis; Wiley 403. Excluir detalhes empíricos desta síntese, manter referência histórica e pendência. |
| Autoexplicação | DOI Chi → `https://onlinelibrary.wiley.com/doi/10.1207/s15516709cog1803_3` → Crossref | Wiley 403; resumo original depositado acessível. Usar apenas afirmações desse resumo. |
| Recuperação ativa | `https://pubmed.ncbi.nlm.nih.gov/16507066/` ; SAGE DOI `10.1111/j.1467-9280.2006.01693.x` ; Crossref | PubMed exigiu cookies; SAGE 403; Crossref forneceu resumo/metadados. Não tratar bloqueios como leitura. |
| PDF recuperação | URL inicialmente tentada `https://learninglab.psych.purdue.edu/downloads/2006_Roediger_Karpicke_PsychSci.pdf` | 404; não citar como fonte. Página consultada `https://learninglab.psych.purdue.edu/publications/` revelou subdiretório `2006/`; PDF corrigido acessado e convertido. Lista do laboratório é trilha de localização, não uma 19ª evidência. |
| Rubricas e uncertainty | arXiv Prometheus e HTML v2; artigo Nature | Ambos primários; excluir interpretação de autoconfiança verbal como calibração e de entropia como prova de corretude. |
| Knowledge tracing | DOI/Crossref Corbett; `https://link.springer.com/article/10.1007/BF01099821` ; arXiv/HTML pyBKT | Springer challenge; pyBKT supriu método acessível e expôs divergência de ano. Não adotar limiares de suficiência sintética como universais. |
| Memória temporal | MemGPT v2 e LongMemEval v2 | Preferir evidência sobre preservar originais/tempo; excluir “resumo sem perdas” e “mais contexto sempre resolve”. |
| MetaGPT venue | `https://openreview.net/forum?id=VtmBAGCN7o` | Browser verification; registro não lido. Bib da versão arXiv; venue editorial pendente. |
| Planejamento | Docs Google CP-SAT e Employee Scheduling | Exemplos executáveis e status consultados; formulação de estudo e prioridades são adaptações. Não supor solver corrige interpretação errada. |
| Calendário | RFC 5545, RFC 4791, guia Google Create events | Fontes normativas/técnicas; excluir promessa de idempotência por UID em todo importador ou por MCP sozinho. |

Critérios de inclusão: origem verificável, utilidade para pelo menos um requisito, acesso a método/resultado ou identidade explicitamente limitada. Exclusões de método, não resultados de busca inexistentes: blogs agregadores como prova de eficácia, referências internas de papers sem consulta própria, reprodução de números sem contexto, “Feynman” como método empiricamente validado, treinamento de modelo fundacional, geração de vídeos e calendário sem leitura pós-timeout. Não foram executadas consultas de buscador geral; os termos de localização foram os títulos/DOIs e conceitos dos requisitos. Não se declara saturação da literatura.

## 12. Parâmetros iniciais propostos e plano de decisão

**Todos os valores nesta tabela são [P], configuráveis e não calibrados pela literatura.** Um número de ensaio não deve aparecer depois como parâmetro cognitivo validado.

| Área | Configuração inicial de ensaio [P] | Sensibilidade/decisão |
|---|---|---|
| Tutor | Uma atividade por turno; até três níveis de pista antes de oferecer solução comentada; diagnóstico com três itens por tópico prioritário | Variar limite de pistas; avaliar apoio adequado e carga, sem impor questionamento infinito |
| Monitor | Rubrica local 0–2 por critério; uma avaliação inicial; três amostras apenas na variante de estabilidade | Comparar erro–cobertura/custo; sem cutoff numérico de confiança antes de calibração |
| Estado | Sem prior cognitivo numérico no MVP; `null` no tópico novo; três respostas independentes de famílias distintas para rótulo provisório “evidência favorável” | Rótulo não é domínio; exigir verificação tardia e avaliar falsos favoráveis |
| Revisão | Candidatos após 1, 3 e 7 dias, ajustáveis a prazo/disponibilidade; erro antecipa nova prática, não reduz duração obrigatória | Comparar com política uniforme; intervalos não derivam do experimento de Roediger |
| Memória | Recuperar até oito unidades originais relevantes + projeção; incluir correções mesmo que desloquem candidatos | Variar 4/8/16 sob orçamento comum; medir recall e tokens, preservando isolamento |
| Contexto | Reservar 20% de W para saída, 10% para resultado de ferramenta, 5% de margem; resto para entrada | Verificar limites reais de runtime; variar reservas e contar template; se impossível, dividir tarefa |
| Solver | Horizonte de sete dias, slots de 15 minutos, orçamento total de dez segundos, seed 0 e um worker no ensaio reprodutível | Comparar slots 5/15/30 e latência; limite compartilhado entre etapas lexicográficas, sem dez segundos por etapa silenciosamente |
| Calendário | Eventos individuais; um worker por calendário; retries limitados a três após reconciliação, com backoff 1/2/4 segundos | Três retries não resolvem efeito desconhecido; medir comportamento de crash e conflitos no backend escolhido |

### Pendências que condicionam implementação e relatório

1. Ler texto integral autorizado de Wood e Chi para aprofundar contingência do apoio, controles e tamanhos de efeito; obter Corbett integral para auditoria histórica. As recomendações operacionais já distinguem esses limites.
2. Conferir venue MetaGPT em registro de conferência acessível antes de substituir sua entrada arXiv por entrada de conferência; evitar misturar metadados de versões diferentes. As cinco identidades da proposta estão localizadas.
3. Definir tópicos/componentes, famílias de itens e rubricas humanas em português antes de calibrar Monitor/BKT; validar separadamente alunos novos e tópicos novos.
4. Verificar tokenizer, template, janela e qualidade local de C01; resultados com GPT-4/Prometheus não substituem esse ensaio.
5. Estimar duração de atividades e política de prioridade com casos reais/confirmados; escolher regras de revisão por comparação, sem supor agenda otimizada para retenção.
6. Fixar versão OR-Tools e biblioteca ICS; conferir APIs de assumptions/intervalos e suportes de timezone; produzir oráculos independentes e testes de falha.
7. Selecionar backend de agenda e consultar atualização condicional, formato de ID, deleção e sincronização incremental específicos. Avaliar conector MCP somente se preservar o contrato; ICS local fecha a exportação offline.
8. Protocolo de exclusão/backup e invalidação de derivados precisa integrar C16. Comparações de memória/skills usam as mesmas ferramentas e limites no baseline único de C19.

**Conclusão:** adotar primeiro mecanismos verificáveis: participação ativa com término, critérios de avaliação com origem, estado observado, memória temporal recuperável, contexto contado, solver validado e efeitos de agenda reconciliados. Superioridade multiagente, estimativa de domínio e ganho de aprendizagem permanecem hipóteses a avaliar, não conclusões herdadas dessas fontes.
