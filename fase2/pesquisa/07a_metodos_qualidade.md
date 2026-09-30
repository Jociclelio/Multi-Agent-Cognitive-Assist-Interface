# Etapa 7a — Métodos de avaliação da qualidade de O01–O18

## 1. Escopo, método de pesquisa e estatuto

**Resoluções incorporadas depois desta pesquisa:** mapa4 §§8/9/11/15 define favorable, omissão sem span, avaliação por tópico/revisão, snapshot e retries; DTSTAMP sem METHOD agora é persistido por revisão. Mapa8 §§6/12 replica estas regras nos oráculos e fixa parser independente candidato, margem de ensaio e cobertura C. As divergências/pendências de O09/O14 abaixo são preservadas como histórico **resolvido**, não instruções atuais concorrentes.

**Consulta: 30/09/2026.** Base normativa local: `fase2/documentos/04_mapa_completo_do_sistema.md` (contratos), `05_fluxos_resultados_e_falhas.md` (W01–W12, O01–O18, F01–F24) e `06_protocolo_de_avaliacao.md` (desenho, métricas e gates). Foram lidos também os dois textos e os dois BibTeX da pesquisa 3, para reaproveitar métodos e identidades bibliográficas. Este documento seleciona e operacionaliza métodos para a etapa 8; não contém resultados do EduAgent-OS nem implementação já executada.

Foi realizada **pesquisa técnica dirigida, não revisão sistemática**. Procedimento: extrair as necessidades de cada O; localizar artigos originais por títulos/identificadores e documentação dos mantenedores; consultar por `webfetch`; aprofundar definições em HTML/código primário disponível; confrontar métodos com contratos locais; escolher procedimento, oráculo, custo e limitações. Não houve consultas a buscador geral, busca exaustiva em bases, PRISMA, avaliação formal de todos os trabalhos concorrentes ou reprodução dos experimentos publicados. A trilha da §11 registra as **14 fontes/núcleos efetivamente consultados**, contando páginas auxiliares do mesmo trabalho como um núcleo. Nenhum PDF foi necessário nesta rodada.

Convenções: **[E]** resultado/método empírico da fonte, no seu domínio; **[N]** especificação ou API documentada; **[P]** adaptação/decisão proposta para o projeto. Fórmulas locais, regras de correspondência, rubricas e orçamento de anotação são [P], salvo atribuição expressa. Os thresholds da etapa 6 permanecem **gates propostos de engenharia**, não recomendações universais da literatura. Bonsai 2, português e corpus educacional precisam de validação própria.

Bibliografia: `references_avaliacao_qualidade.bib` contém apenas **oito entradas novas**. As seis fontes já cadastradas e reconsultadas mantêm suas keys em `references_pedagogia.bib` ou `references_arquitetura.bib`. Para compilar citações desta pesquisa, carregar os três arquivos; não copiar entradas antigas para o novo BibTeX. Outras referências da pesquisa 3 são mencionadas como antecedentes, com leitura anterior explicitamente indicada, e não entram na contagem de 14 consultas desta rodada.

## 2. Decisões gerais: independência, denominadores e eficiência

### 2.1 O que será considerado oráculo

1. **Contratos verificáveis:** comparador independente sobre entrada original, versões e efeitos observados. Não reutilizar a mesma função de produção para calcular o esperado. Schema é um primeiro check, não um oráculo semântico.
2. **Texto e pedagogia:** dois avaliadores humanos com especialidade nas disciplinas, cegos à condição, referência e critérios prévios; acordo calculado **antes** da adjudicação. Ouro adjudicado conserva as anotações originais e razões de discordância.
3. **LLM/NLI:** instrumento de triagem e análise secundária, validado contra humanos; seu diagnóstico não substitui ouro. Tutor e Monitor usam o mesmo modelo no sistema: a separação de papéis não torna seus erros independentes.
4. **Efeitos:** ledger de teste e leitura do destino/DB. ACK, trace e checkpoint isoladamente não provam que o efeito ocorreu.

Registro mínimo de avaliação [P]: `case_id, family_id/trajectory_id, split, output_id, condition, seed, snapshot_hash, input_ref, output_ref, oracle_version, metric_name, numerator, denominator, value, eligible, missing_reason, critical_error_ids, annotations, evaluator_manifest`. Não guardar apenas o escalar final. Quando houver auditoria humana amostral, preservar probabilidade de seleção e estrato.

### 2.2 Regras para agregação

- Medir por saída e por W antes do TSR. Para uma rota, sucesso exige todos os invariantes essenciais e terminal adequado; média de rubrica alta não compensa violação crítica.
- Separar `artifact_quality` condicionado a artefato disponível, `artifact_availability` em todas as tentativas elegíveis e sucesso end-to-end. Timeout/ausência de saída não recebe citação perfeita nem é retirado do TSR. Não inventar CER ou kappa para uma saída inexistente: registrar ausência e falha da rota.
- Macro por consulta/item/instância e micro por unidades elementares, com nomes distintos. Para O01, agregar erros sobre caracteres/palavras (micro) e reportar distribuição por página/família (macro). Para O08, critérios da mesma tentativa são dependentes.
- `N/A` exige causa: pergunta sem evidência para recall, referência vazia para taxa clássica, estimativa `null` para Brier. Denominador zero não vira acerto 1 por conveniência. Sempre apresentar frequência desses casos.
- **Exceção necessária à convenção [0,1] da etapa 6:** CER/WER não têm teto 1; kappa pertence a [-1,1]; log loss não tem teto finito. Contagens de falhas e inversões também não são taxas até terem denominador. Não truncar essas métricas para adequá-las à tabela.
- Comparar condições pareadas; preservar os splits por família e trajetória da etapa 6. IC95% por bootstrap de famílias/trajetórias, reamostrando o mesmo caso em todas as condições e mantendo suas seeds juntas. Seeds não aumentam artificialmente N. Pré-especificar primárias e correção de hipóteses secundárias.

### 2.3 Estratégia de custo [P]

Executar primeiro todos os checks determinísticos baratos; cachear resultados por hashes de artefato, oráculo e configuração. Ouro documental e rubricas são reutilizáveis entre condições, mas respostas geradas novas precisam de julgamento próprio. Fazer julgamento humano nas unidades semânticas previstas pela etapa 6; se o orçamento impedir cobertura integral, declarar subconjunto estratificado e seu alcance, sem generalizar o gate ao restante. Revisar todos os candidatos a erro crítico e uma amostra aleatória dos casos aparentemente bons: revisar somente alertas do LLM impede estimar seus falsos negativos.

Uma decisão sobre apoio pode ser feita em lote de claims por contexto, desde que IDs/decisões individuais sejam preservados. Medir custo de avaliação separadamente do custo do sistema. Uma variante que amostra três juízos ou NLI em cada citação deve contabilizar essas chamadas; não adotar automaticamente as gerações múltiplas caras da pesquisa 3.

## 3. Extração e estrutura documental

### O01 — Manifesto, texto, blocos e proveniência (W01; F01/F10/F12/F24)

**Definição operacional.** Texto fiel à página física, estrutura e ordem recuperáveis, números/sinais preservados, fontes resolvíveis à versão correta. Fonte principal de implementação: `jiwerQuality` [N], biblioteca de avaliação de ASR adaptada a OCR [P]. Representação Docling/OCRmyPDF permanece como antecedente da pesquisa 3 (`docling`, `ocrpdf`), não como prova de qualidade.

**Métricas e fórmulas.** Alinhar referência humana R e hipótese H por distância mínima de Levenshtein. `CER=(S_char+D_char+I_char)/|R_char|`; `WER=(S_word+D_word+I_word)/|R_word|`. CER/WER podem ultrapassar 1 por inserções. Micro corpus é soma dos numeradores dividida pela soma dos comprimentos de referência, não média de porcentagens arredondadas. Informar separadamente S/D/I e caracteres de substituição.

Normalização congelada: Unicode NFC, finais de linha padronizados e regra explícita de espaços; preservar acentos, sinais, expoentes, vírgula decimal, unidades e caixa em códigos. Publicar resultado estrito e, se útil, diagnóstico com normalização tipográfica adicional. Não remover pontuação/números para melhorar CER. WER usa segmentação declarada; equações/tabelas requerem avaliações próprias, não apenas tokens separados por espaço.

**Oráculo e procedimento.** Dois anotadores transcrevem/cotejam páginas contra imagem original; regiões ilegíveis são marcadas, não completadas por LLM. Separar ouro de texto por região e ouro de ordem. Usar `jiwer.process_characters`/`process_words` com transformações explícitas, persistindo alinhamentos. Para página realmente vazia, medir inserções espúrias e acerto de diagnóstico; JiWER >=4 define convenções para referências vazias, mas não misturar seus valores convencionais com taxa clássica sem explicação.

- Fatos críticos: `EM_crit=#campos críticos exatos/#campos críticos legíveis anotados`. Comparar tuplas valor/sinal/unidade/posição; distinguir fidelidade literal de normalização semântica em O02. Número trocado vale erro mesmo com CER excelente.
- Ordem: parear blocos ao ouro por bbox/spans revisados; taxa de inversão `I_order/#pares comparáveis`. Apenas pares com ordem definida entram; blocos ausentes e extras têm recall/precisão próprios, para evitar ordem perfeita por omissão.
- Tabelas: exatidão por célula e associação célula→linha/coluna/cabeçalho; símbolos/equações: cotejo especialista ou equivalência formal autorizada. São checks locais, sem alegar adoção de benchmark de tabelas não consultado.
- Proveniência: resolver cada ref emitida no snapshot e comparar original/hash/página física/bloco/offset ou bbox. Reportar taxa de refs resolvidas **e corretas**, além de integridade do original; uma página existente mas errada falha.

**Recomendação/limite.** Manter gate ≥.98 nos fatos críticos e 100% nas refs conforme etapa 6; CER/WER servem a diagnóstico estratificado digital/scan/colunas/tabelas, sem threshold universal. Extração ilegível declarada pode ser terminal seguro, mas não documento corretamente extraído. Não deixar texto omitido desaparecer do denominador.

### O02 — Tópicos, fatos acadêmicos, prazos e pendências (W01; F02/F10/F16)

**Método [P].** Ouro humano de entidades e relações com span, ID canônico, aliases autorizados, versão, precisão, autoridade, timezone e status. Separar três tarefas: detecção de menção, ligação ontológica e normalização temporal. Pareamento um-a-um evita contar duas previsões do mesmo prazo como dois TP.

`P=TP/(TP+FP)`, `R=TP/(TP+FN)`, `F1=2PR/(P+R)`; reportar micro e macro por tipo. Correspondência principal é exata para tipo/span/entidade; overlap de span é diagnóstico secundário. Relação correta exige dois endpoints corretos e tipo/direção. Para datas, `EM_norm` compara tupla `(kind,value,precision,timezone,status,authority,source_version)`; não equiparar DATE a datetime 23:59. Datas relativas usam data da fala e zona confirmada no ouro.

**Oráculo.** Comparador de tuplas e grafo de aliases anotado independentemente; parser de datas determinístico apenas nos casos inequívocos. Ciclos de pré-requisitos verificados por algoritmo de grafo. Contar `silent_promotions` e taxa sobre candidatos ambíguos; contar também conflitos omitidos sobre conflitos anotados. Confirmação precisa apontar evento de usuário, não apenas `status=confirmed`.

**Recomendação/limite.** F1≥.90 e zero promoção silenciosa da etapa 6; auditar autoridade separadamente de F1. Dois avaliadores devem resolver granularidade de tópicos antes do teste. Sinônimos não tornam disciplinas distintas equivalentes; fonte mais recente não determina autoridade automaticamente. Não há evidência nas 14 fontes de que esta ontologia local seja universal: método é adaptação verificável.

## 4. Recuperação e geração fundamentada

### O03 — EvidencePack, ranking, cobertura e citações (W02; F03/F04/F10)

**Base.** BEIR (`thakur2021beir`) [E] fornece benchmark heterogêneo e interface de qrels; código oficial consultado [N] usa `pytrec_eval` para nDCG/recall e função específica para MRR. Resultados em seus datasets não substituem consultas educacionais locais. ALCE (`gao2023alce`) [E] separa corretude e qualidade de citações; RAGAs (`es2024ragas`) [E] mede fidelidade ao contexto, relevância da resposta e do contexto.

**Ouro [P].** Para cada consulta: `answerability`, disciplina/usuário/snapshot, unidades de evidência necessárias, IDs de blocos relevantes e qrels 0=irrelevante, 1=útil parcial, 2=suficiente para aspecto requerido. Anotar unidades de evidência no original e depois mapear para chunks, para poder comparar chunkings sem inflar recall por duplicação de overlap. Fazer pooling dos candidatos das configurações em desenvolvimento e revisão adicional no teste; documentos não julgados são desconhecidos, não prova de irrelevância. Em corpus pequeno, procurar exaustivamente o suporte de cada pergunta.

**Fórmulas.** Seja G_q o conjunto de IDs relevantes no ouro e T_q,k o top-k deduplicado:

```text
Recall@k(q) = |G_q ∩ T_q,k| / |G_q|
RR@k(q) = 1/r_primeiro_relevante se r <= k; caso contrário 0
MRR@k = média_q RR@k(q)
DCG@k = Σ_(r=1..k) gain(rel_r)/log2(r+1)
nDCG@k = DCG@k / IDCG@k
```

**Convenção principal [P]: ganho linear `gain(rel)=rel` compatível com `trec_eval/ndcg_cut`; não trocar silenciosamente por `2^rel−1`.** Confirmar com fixture de relevância graduada na versão fixada do avaliador. IDCG vem da ordenação ideal de todos os julgados relevantes elegíveis no snapshot. Empates recebem ordem estável por ID e scores de avaliação sem empate, ou política de empate explicitamente documentada. Recall@40 é medido na lista de 40 que chega ao reranker; medir também recall da união lexical+densa separadamente. nDCG@6/MRR@6 na ordenação final; recall do pacote realmente serializado após budget é outra medida.

MRR valoriza só o primeiro relevante; para pergunta multiaspecto, acrescentar `coverage_evidence=#unidades necessárias presentes/#unidades necessárias`. Duplicatas de uma unidade não aumentam cobertura. Queries sem G_q não entram em recall/nDCG tradicionais: avaliar abstinência e retorno indevido no estrato sem suporte; reportar seu N.

**Implementação/oráculo.** Exportar qrels/run por consulta; configurar k=[6,40], filtros e namespace de IDs. O código BEIR consultado remove por default doc_id igual a query_id, modifica `results` e agrega somente queries devolvidas por `pytrec_eval`; usar cópia, configurar essa opção e reconciliar a lista completa de consultas esperadas, atribuindo zero a ranking vazio de consulta respondível. Não permitir perda silenciosa de consultas na média. Guardar valores por consulta antes de arredondamento, conferir manualmente uma fixture pequena.

#### Sustentação: quatro medidas separadas [P]

Para claims documentais atômicas s_i, contexto K e citações C_i, usar decisão humana `entails(premise,claim)` com valores apoiada/contradita/insuficiente/indecidível. Excluir cumprimentos e instruções sem conteúdo factual segundo regra anterior ao julgamento, não porque foram difíceis de avaliar.

1. **Resolução:** refs corretas e autorizadas/refs emitidas, como O01; ref não resolvida não sustenta claim.
2. **Corretude factual:** claims corretas/claims factuais julgáveis, contra fonte autoritativa e especialista; listar indecidíveis e erros críticos.
3. **Faithfulness ao contexto:** `F_K=Σ 1[entails(K,s_i)]/m`, adaptação da decomposição e verificação de RAGAs. Texto pode ser fiel a fonte errada; F_K não comprova verdade nem citações adequadas.
4. **Citation recall ALCE adaptado:** `CR=Σ 1[C_i≠∅ e entails(concat(C_i),s_i)]/m`. Aqui a unidade é claim atômica; ALCE usa principalmente sentença. Reportar essa adaptação, sem declarar resultado diretamente comparável ao paper.

**Citation precision ALCE:** para claim já totalmente apoiada pelo conjunto citado, c∈C_i é relevante se apoia sozinha s_i **ou** se removê-la faz o restante deixar de apoiar s_i. `CP=Σ_(i,c) 1[claim apoiada ∧ c relevante]/Σ_i |C_i|`. Isso admite fontes redundantes que sustentam a claim sozinhas e fontes conjuntamente necessárias; não exige conjunto mínimo. Ref inválida entra no denominador com crédito zero. Sem citações: CP=N/A e CR=0 quando havia claims documentais; resposta vazia/abstinência correta é avaliada pelo estrato de answerability e disponibilidade, não recebe CP=1.

**Custo/limite/recomendação.** Resolução determinística em todas as refs; humanos para semântica e números; NLI/LLM para triagem após meta-avaliação. ALCE usa TRUE/T5-11B, cuja qualidade/custo em português não foram estabelecidos aqui. Testar premissa→claim, não direção inversa; citação de página inteira ou truncamento pode esconder falta de apoio. Preservar conclusões condicionais e apoios conjuntos. Gate recall≥.90 e CP≥.95 é local; acrescentar CR, completude e answerability, para impedir ganhar abstendo de tudo ou emitindo só uma frase trivial.

### O04 — Explicação (W02; F03/F04/F09/F12)

**Método.** Auditoria de claims de O03 + rubrica humana por dimensão (corretude conceitual, pertinência/completude, clareza, limites/apoio), com contexto e objetivo do estudante. Usar gabarito validado; não exigir coincidência de palavras. Prometheus (`kim2024prometheus`) sustenta entradas instrução/resposta/rubrica/referência, mas sua escala publicada 1–5 e avaliação de respostas de LLM não validam a escala pedagógica local 0–4.

**Âncoras [P], por dimensão:** 0=ausente ou gravemente inadequado; 1=defeito central que impede uso; 2=parcial, exige correção substantiva; 3=adequado, pequeno defeito localizado; 4=adequado e completo para o objetivo, sem defeito relevante. Para corretude: erro crítico recebe flag própria e nível 0/1 conforme impacto; para clareza: texto conciso e compreensível pode receber 4, sem premiar comprimento. Para limites: 4 exige explicitar condições pertinentes e insuficiência de evidência quando houver; não exigir ressalvas genéricas sem necessidade.

**Oráculo/medida.** Anotadores marcam trechos e justificativas por dimensão; medianas/distribuições e acordo ordinal, nunca só nota média global. Checklist de claims necessárias mede completude independentemente da quantidade gerada. Comparação principal humana; juiz secundário conforme §6. Gate mediana≥3 por dimensão e sem erro crítico em caso aceito. Similaridade semântica/cosseno não decide causalidade, sinal ou condição matemática; fluência não absolve erro factual.

## 5. Artefatos e interação pedagógica

### O05 — Exercício, quiz, gabarito e rubrica (W03; F04/F05/F06)

**Definição [P].** Item válido se contém objetivo/tópico/família, informação suficiente, solução decidível ou conjunto de soluções aceitas, nível compatível com tarefa, gabarito/rubrica prévia com origem e separação da solução. Dois especialistas tentam resolver sem ver gabarito; depois cotejam soluções, equivalências e pressupostos. Gabarito produzido pelo Tutor não pode validar a si próprio.

**Oráculo.** Para resposta numérica, aceitar `|a−a*|≤atol+rtol·|a*|` depois de conversão de unidades, tolerâncias fixadas por item; comparar unidade e dimensões. Para expressão simbólica, simplificação/equivalência sob domínio e hipóteses explícitos; exemplos numéricos aleatórios ajudam a achar contraexemplo, não provam equivalência. Ferramenta incapaz de decidir devolve indecidível, encaminhando especialista. Código só se extensão sandbox admitida, com testes de propriedades do problema e casos ocultos próprios, não tests inventados pelo gerador.

`item_validity=#itens com todos os checks essenciais/#itens publicados`; disponibilidade sobre solicitações de item também é reportada. Medir gabaritos incorretos, ambiguidade e rubricas insuficientes individualmente. Nível é julgamento de adequação **pretendida**: dificuldade empírica requer respostas de alunos. Gate ≥.95 válidos; origem ausente bloqueia publicação. Custo especialista concentra-se em famílias novas, mas variações precisam de check de constantes/domínio.

### O06 — Flashcard (W03; F04/F05)

**Checklist/oráculo [P].** Frente testável sem revelar verso; uma unidade conceitual/relacional recuperável; verso correto, suficiente e breve para essa unidade; fonte pertinente; família/versão; política de reveal. Atomicidade é avaliada por especialista: lista com vários objetivos independentes falha, mas uma relação causal não precisa ser quebrada em palavras isoladas.

`valid_card_rate=#cards com todos os essenciais/#cards publicados`; duplicação por frente+objetivo e equivalência humana, com duplicatas deliberadas de revisão identificadas à parte. `early_reveal=#episódios com verso acessível antes de reveal/#episódios elegíveis`. Check de campos/renderização e sequência de eventos automatizados; vazamento semântico requer inspeção da frente e pistas.

**Limite/recomendação.** ≥.95 válidos e zero reveal antecipado no ensaio. “Retenção potencial” da etapa 6 é qualidade de desenho, não estimativa de retenção. O antecedente `roediger2006testing`, lido na pesquisa 3, motiva recuperação e teste tardio, não valida intervalos 1/3/7 nem mede efeito destes cards. Retenção humana exigiria teste tardio sem pistas e transferência com controle de exposição.

### O07 — Turno, pistas, autoexplicação e término (W03; F05/F11/F12)

**Método [P].** Julgar sequência com enunciado, tentativa original, erro conhecido, ajuda anterior e intenção atual, não pista isolada. Rubrica 0–4 com âncoras da O04 para: contingência ao erro, graduação do apoio, oportunidade de participação e adequação ao objetivo. Exemplo: nota 3 em contingência exige pista ligada ao erro observado que permite próximo passo; nota 1 é pergunta genérica incapaz de orientar; nota 0 contradiz o conceito ou expõe solução quando prática independente era exigida. Autoexplicação deve pedir relação/condição/justificativa, não mera cópia.

**Oráculo.** Máquina de estados de teste independente a partir do roteiro e eventos: `waiting_student` termina invocação sem chamadas até nova entrada; pedido explícito de solução/recusa/cancelamento encerra insistência; após reveal, ajuda fica registrada. Definir semanticamente antes do teste o que é solução antecipada em cada família; nem todo símbolo comum é vazamento, e paráfrase da solução pode ser.

Taxas: vazamento/episódios elegíveis de prática; insistência/terminais pedidos; espera correta/episódios que exigem resposta; cobertura das transições e motivo de término. Mediana≥3 e 100% terminais respeitados. Roteiros simulados avaliam observância e qualidade de apoio, não participação espontânea ou aprendizagem humana. Antecedentes Chi/Wood na pesquisa 3 têm alcances de leitura distintos; as âncoras aqui são proposta local, não rubrica empírica extraída daqueles trabalhos.

## 6. Avaliação formativa e confiabilidade do juiz

### O08 — Assessment, feedback e evidências (W04; F06/F10/F23)

**Oráculo.** Entrada contém item/rubrica/gabarito validado, resposta original, fontes, ajuda e reveal. Humanos dão nível 0–2 por critério: 0=ausente/incorreto; 1=parcial; 2=adequado. Anotam misconception codes e spans por offsets, verificando substring no original. `undecidable` e abstinência são decisões separadas dos níveis ordinais; não converter abstain em nota 0 para calcular acordo.

**Concordância.** Usar `sklearnKappaQuality` [N], com `labels=[0,1,2]`, pesos lineares, por critério. Para matriz de proporções O_ab e esperado E_ab pelo produto das marginais: `κ_w=1−Σ d_ab·O_ab/Σ d_ab·E_ab`, `d_ab=|a−b|/(K−1)`. Equivalente a kappa ponderado; declarar pesos lineares como escolha, não trocar para quadráticos para elevar resultado. Reportar também acordo exato, diferença absoluta, matriz de confusão, marginais, N e IC por família. Se todas as notas forem a mesma e o denominador esperado zero, kappa é indefinido, não acordo comprovado por κ=1.

Calcular humano–humano antes de adjudicar e Monitor–ouro depois. κ alto é consistência, não verdade; depende das marginais e pode ocultar erros raros. Correlação Pearson/Spearman de notas é auxiliar, não substitui acordo nem falso acerto. `macroF1_errors` calcula F1 por código de erro predefinido e média sobre códigos; reportar suporte e FP/FN, mantendo classes raras e N/A explícitos.

**Erro crítico e seleção [P].** Publicar dois denominadores:

```text
critical_false_credit = #avaliações aceitas que dão crédito indevido crítico / #aceitas
critical_miss_rate = #respostas com erro crítico aceitas como corretas / #respostas com erro crítico
coverage(t) = #aceitas sob política/limiar t / #tentativas elegíveis
risk(t) = #avaliações incorretas entre aceitas / #aceitas
```

Mostrar pontos risco–cobertura, precisão de abstinência (`abstinências necessárias/abstinências emitidas`) e recall de abstinência (`abstinências necessárias detectadas/necessárias`), além de taxa de abstinência em respostas decidíveis. Sem score ordinal de confiabilidade, mostrar políticas categóricas (schema/fonte/spans/discordância) em vez de fingir curva contínua. Se aceitas=0, risco=N/A; cobertura=0. Escolher política em validação e congelar; testar uma vez.

**Recomendação.** Gate κ≥.70 e falso crédito crítico≤.05 entre aceitos conforme etapa 6, com IC e cobertura; não aceitar juiz que satisfaz risco abstendo quase sempre. Feedback é auditado separadamente: identifica erro real, aponta próximo passo realizável, preserva ajuda e não inventa span. Falha formal resulta em abstinência e nenhuma atualização inferencial, mesmo que a prosa pareça útil.

### 6.1 Humano versus LLM judge: procedimento de meta-avaliação

Prometheus [E] mostra utilidade de rubrica/referência e correlação humana em 45 instâncias com rubricas distintas; não valida respostas de alunos em português. Zheng et al. (`zheng2023judge`) [E] examinam posição, verbosidade, capacidade de raciocínio e possível auto-favorecimento. O próprio texto não estabelece conclusivamente self-enhancement em todos os modelos; tratar como risco a testar, não fato universal. Seus acordos >80% dependem da inclusão/exclusão de empates e contexto de preferências, não são gate transportável de corretude pedagógica.

**Meta-avaliação [P]:**

1. Preparar conjunto de desenvolvimento/validação estratificado em correta curta, correta longa, fluente errada, parcialmente correta, ajuda/reveal, paráfrase, erro formal, item ambíguo e fonte contraditória. Manter famílias de teste inéditas.
2. Dois humanos avaliam cegos e independentemente; só depois adjudicam. Não mostrar avaliação LLM antes da anotação, para evitar ancoragem.
3. Fixar judge_id/revisão, prompt/hash, rubrica, reference_hash, sampler, seed, parser, idioma e contexto. Juiz recebe fonte/rubrica, não nome MA/SA nem autoelogio do Tutor. Um modelo diferente reduz circularidade de identidade, mas não elimina erro correlacionado de dados/gabarito.
4. Avaliação por dimensão e critério é preferida a preferência global. Quando houver comparação pareada, executar A/B e B/A; mapear vencedor à identidade real e medir `order_flip=#decisões incompatíveis/#pares`. Inconsistência é registrada; empate conservador não é acerto factual e empates não somem do denominador.
5. Testar metamorfismos controlados por humanos: acrescentar repetição sem informação, encurtar sem perder conteúdo, paráfrase e renomeação de candidatos. Medir Δnota e crédito em erro crítico; não truncar respostas reais para igualar comprimentos, pois isso muda sua qualidade.
6. Medir acordo, erros por disciplina/ajuda/comprimento, spans inventados e custo. Amostragem de seeds mede estabilidade, não certeza; erro consistente pode ser repetido em todas.
7. Admitir LLM somente para triagem/medida secundária após análise contra ouro. Discordâncias críticas são revisadas. Se avaliação humana final for amostral, declarar amostragem e incerteza; nenhum consenso de LLM substitui ouro na violação crítica publicada.

**Eficiência.** Começar com uma avaliação de referência por critério/artefato; usar ordem dupla só em comparações pareadas e amostragem adicional na variante de estabilidade. RAGAs pode acelerar iteração, mas suas métricas originalmente usam modelos/API próprios e WikiEval pequeno em inglês; não ligar pacote `latest` e chamar seu escalar de mesma métrica do paper. Fixar versão/função/prompt e registrar adaptação.

## 7. Estado, memória e contexto

### O09 — TopicState e revisão (W04/W07; F07/F18)

**MVP [P].** `estimate=null`: avaliar regras, não calibração probabilística. Implementar redutor-oráculo simples separado que lê somente Assessments válidos/aceitos, deduplica attempt_id, conserva família/ajuda/reveal e aplica regras da etapa 4. Congelar operacionalização de **“contradição recente”** e **“erro crítico”** antes do teste: o documento ainda não define janela/escopo suficientemente para um oráculo único.

Comparar projeção após cada prefixo temporal: IDs independentes/assistidos, erros, datas, revisão e estado. `replay_agreement=#prefixos com projeção semanticamente idêntica/#prefixos`; revisar campos voláteis fora da projeção sem ocultar revisão de domínio. Tentar retries, eventos inválidos e fatos de autorrelato/leitura: não podem alterar competência. `false_favorable` conta estados favoráveis sem os três acertos independentes de famílias distintas ou com contradição vigente; separar isso de falso sinal pedagógico contra desempenho futuro real. Zero ajuda promovida e replay 100% são gates locais.

**BKT futuro/calibração.** Antecedente `badrinath2021pybkt` já lido na pesquisa 3; não reconsultado nesta rodada. Para prever próxima resposta independente, avaliar `p_correct=p_L(1−S)+(1−p_L)G`, não p_L contra resposta observada. O alvo é resposta futura decidível, não “domínio verdadeiro”. Ajuste por aluno/componente e tempo deve impedir acesso ao futuro; ajuda/parciais não são binarizados silenciosamente.

Guo (`guo2017calibration`) [E] e `sklearnCalibrationQuality` [N] sustentam separação entre confiança e calibração. Havendo probabilidades genuínas:

```text
Brier = média_i (p_i−y_i)^2                         # convenção binária, sem fator 2
LogLoss = −média_i [y_i ln(p_i)+(1−y_i) ln(1−p_i)]
ECE = Σ_b (n_b/N) · |média_b(y)−média_b(p)|
```

Reportar bins, limites, n_b, média prevista, frequência observada e IC, estratos cold-start/tópico/ajuda, além de discriminação. O ECE acima é calibração da probabilidade do evento binário; Guo também descreve confiança da classe prevista contra acurácia, que não deve ser misturada com p de acerto futuro. Brier/log loss medem qualidade probabilística com resolução e incerteza, não calibração isolada. ECE varia com binning e N; zero com poucos bins não prova confiabilidade. Clipping numérico de p para log deve ter ε registrado; p extremo errado implica perda teórica infinita.

**Recomendação/limite.** Permanecer no estado observado até dados prospectivos. Se necessário calibrar score de avaliação/reranker, aprender sigmoid/isotônico em validação separada, com famílias fora do treino; isotônico pode sobreajustar amostra pequena. Temperature scaling requer logits/classes adequados, não é a temperatura de sampling do LLM nem calibrador de “confidence=0.9” verbal. Não recomendar probabilidade de domínio como resultado do MVP.

### O10 — Memória atual, temporal e correções (W05/W10; F08/F17/F21)

**Base.** `wu2025longmemeval` [E] separa extração, raciocínio multisessão, temporalidade, atualização e abstinência; avalia retrieval e QA. Reutilizar tipos de pergunta, não copiar ouro inglês nem assumir que seu juiz GPT-4o permanece calibrado localmente.

**Ouro/oráculo [P].** Cada trajetória tem ledger humano/roteirizado: evento, autor/origem, usuário, tópico, occurred_at, recorded_at, valid_from/to, supersedes, correções e conjunto de fatos conhecido em cada corte. Formular perguntas atuais, retrospectivas, agregação e sem resposta; inserir homônimos, versões conflitantes e correção retroativa. Uma pergunta “o que era válido em t?” difere de “o que o sistema sabia em t?”: a segunda filtra recorded_at, não só validade.

`Recall_ID@k=|IDs necessários ∩ recuperados|/|necessários|`; quando há suportes alternativos, definir conjuntos suficientes e medir cobertura por unidade de fato para não exigir todos os caminhos redundantes. QA: acurácia por tipo contra tuplas/valores e equivalências anotadas; texto aberto recebe avaliação humana, EM é reservado a campos fechados. Reportar acurácia atual e retrospectiva separadas e macro entre os cinco tipos. Contar superseded apresentado como atual, conflito ocultado, correção ignorada e vazamentos (zero é gate, não média).

**Diagnóstico/custo.** Comparar contexto recuperado com contexto-oráculo que contém só evidências necessárias: diferença em QA localiza recuperação versus leitura, sem chamar contexto-oráculo de baseline realista de custo. Escrever/ler em ordem cronológica, mantendo recuperação de originais; cache por corte/snapshot. Abstinência tem precisão/recall conforme O08; não premiar resposta vaga que evita fato desconhecido mas inventa outro. LongMemEval não ensaia exclusão transacional ou isolamento deste DB: O16 faz esses checks adicionais.

### O11 — Síntese e contexto compactado (W05; F09/F12/F21)

**Método [P].** Ouro de fatos críticos como tuplas `(sujeito,predicado,valor,polaridade,tempo,origem,help_level,reveal,evidence_ids)` e âncoras de rubrica/item. Comparador estruturado confere datas/números/ajuda/versão; especialista confere claims livres. `critical_recall=#fatos críticos preservados corretamente/#fatos críticos necessários`; `unsupported_claim_rate=#claims sem apoio/#claims emitidas`; contradições em contagem e taxa. Omissão de “com pista” falha mesmo que ROUGE seja alto. Refs existentes não bastam: verificar claim contra eventos referenciados.

**Oráculo/custo.** Tokenizar a mensagem final com template/schema/tools e tokenizer real do manifesto: `input+16384+2048+1024≤32768` na configuração da etapa 4. Comparar contador local e contagem backend disponível; desconhecido=null, nunca 0. Registrar tokens por segmento antes/depois, compressão `1−tokens_síntese/tokens_originais` apenas para o mesmo conteúdo-alvo, e tamanho total efetivo. Se âncora/rubrica não couber, saída segura é dividir/esclarecer, não avaliar sem ela.

Comparar originais selecionados versus síntese nos mesmos casos/seeds e budgets: ΔO04/O08/O10/O13 e custo total, incluindo geração/verificação de síntese. `wu2025longmemeval` indica que comprimir valores em fatos pode perder detalhes [E]; não estabelece taxa de compressão sem perdas. Gate 100% fatos críticos e budget cumprido; qualidade downstream impede passar só copiando tuplas enquanto perde justificativa essencial. Estresse com polaridade, prazo, ajuda, correção e rubrica na fronteira da janela.

## 8. Demanda, solver e calendário

### O12 — Demandas e estimativas (W06; F02/F07/F13)

**Oráculo [P].** Tabela independente produzida de entrada confirmada, evidência aceita e política de prioridade congelada. Cada demanda traz duração positiva, status confirmed/estimated, earliest/deadline com precisão/zona, mandatory, dependencies, prioridade e motivo/evidence_ids. Comparar restrições duras por tuplas; qualquer valor essencial diferente torna a demanda não fiel.

`hard_fidelity=#restrições duras exatas/#restrições duras confirmadas esperadas`; contar também duras extras inventadas, demandas esperadas ausentes e estimativas sem rótulo. Gate exige ausência de extras indevidos, não só recall=1. Especialista avalia pertinência/adequação de prioridade e da recomendação de revisão com rubrica 0–4; política determinística é conferida por regra, sem exigir concordância com preferências arbitrárias do juiz.

**Limite/recomendação.** Duração estimada não tem EM humano universal. Quando houver duração observada, reportar erro absoluto em minutos e distribuição por tipo; tempo de estudo observado não é medida direta de competência. 100% duras fiéis e estimativas rotuladas. Fonte/confirm status deve ser conferido no evento de origem; um solver perfeito não corrige demanda errada.

### O13 — Plano, status, conflito, déficit e diff (W06/W07; F13/F14)

**Base [N].** `google2024cpsat` define inteiros e cinco status. **[P]** Oráculo de qualidade tem três camadas independentes:

1. **Validador em tempo original:** ler demandas/compromissos confirmados do snapshot; conferir intervalos UTC `[start,end)`, zona IANA/tzdata, duração real ≥ requerida, janelas, prazos, limites diários, não sobreposição, unicidade, presença obrigatória, dependências e blocos fixos. Para conflito entre a e b: `max(start_a,start_b)<min(end_a,end_b)`. Eventos adjacentes são permitidos. Não reaproveitar a matriz de slots nem o gerador de candidatos da produção.
2. **Enumeração exaustiva pequena:** gerar independentemente todos os inícios na grade declarada, filtrar com regras em instantes originais, enumerar uma escolha por obrigatória e zero/uma por opcional; descartar combinações inválidas; calcular objetivo lexicográfico. Guardar certificado de melhor vetor e número de possibilidades exploradas. **Não usar `enumerate_all_solutions` do mesmo CP-SAT como único oráculo independente.** Limitar tamanho antes do teste; enumeração interrompida não certifica inviabilidade.
3. **Instâncias realistas:** validar incumbent e status relatado, objetivo/bound de cada etapa e duração total. Sem ótimo independente, reportar gap/certificado do solver como declarado, não regret verdadeiro. Timeout forçado pode ocorrer em fases diferentes; usar fixture de status e ensaio real sem presumir que toda seed produz UNKNOWN.

**Métricas [P].** Violações por regra e `invalid_published/#planos publicados`; cobertura de demandas por classe (número e minutos, sem misturar); déficit é expected_demands−atendidas, conferido por conjuntos e motivos. Objetivo como vetor de maximização `v=(n_classe1,n_classe2,n_classe3,−alterações,−deslocamento,preferências)`. Nas pequenas, comparar ao vetor ótimo v*: igualdade e primeiro componente divergente com diferença orientada; não colapsar prioridade lexicográfica em soma arbitrária denominada regret. Métrica escalar por estágio só tem sentido quando os estágios anteriores estão iguais.

Churn: `#blocos futuros aprovados movidos ou removidos/#blocos futuros aprovados elegíveis`; novas adições reportadas separadamente. Deslocamento em minutos sobre IDs preservados; informar removidos para não premiar remoção de tudo. Diff-oráculo calcula conjuntos added/removed/moved/unchanged por block_id e compara ao preview, incluindo razões/versões. Snapshot obsoleto invalida aprovação mesmo com plano viável.

**Status/limites.** OPTIMAL exige prova para cada fase lexicográfica anunciada; FEASIBLE é viável sem essa prova; UNKNOWN é inconclusivo, não inviável; MODEL_INVALID é defeito de modelagem. INFEASIBLE prova ausência **no modelo discretizado**, não necessariamente em tempo contínuo. Acrescentar fixture em minutos com solução que grade conservadora exclui, para verificar se diagnóstico informa esse limite. Ciclo/entrada ambígua é erro de entrada, não conflito misterioso. Núcleo suficiente de conflito não deve ser chamado mínimo; redução diagnóstica não é plano publicável.

**Recomendação.** Gate zero violações publicadas, status correto e diff completo; tolerar inferioridade de objetivo explicitamente como FEASIBLE dentro do budget. Mutation testing do oráculo na etapa 8: plano com sobreposição de um minuto, duração 17→15, omissão de prerequisite, movimento de fixo e troca de snapshot deve falhar. Isso testa o próprio verificador, não só soluções do solver.

### O14 — ICS e recibo de efeito (W08; F15/F20)

**Base [N].** `desruisseaux2009icalendar`, RFC 5545, §§3.1/3.6.1/3.8.7.2–4. Método [P]: serializador `icalendar` e parser de outra implementação a selecionar/pinar na etapa 8; usar a mesma biblioteca nos dois lados é round-trip útil, mas insuficiente como independência.

**Oráculo/medidas.** Validar bytes UTF-8, CRLF, escaping, folding recomendado em 75 octetos (não caracteres), VCALENDAR VERSION/PRODID e cardinalidades/valores de VEVENT. Comparar multiconjuntos canônicos `(UID,start_utc,end_utc,SUMMARY,SEQUENCE,DTSTAMP)` entre plano aprovado, ICS parseado e readback remoto quando sync existe. DATE all-day permanece DATE com fim exclusivo; não converter a meia-noite UTC. Canonicalização ignora ordenação/folding, não hora/identidade/revisão. `event_equivalence=#eventos equivalentes/#eventos esperados`; extras/duplicatas contados separadamente. Gate não passa com eventos faltantes ou extras mesmo que campos presentes tenham 100%.

Testar acentos/multibyte, vírgula/semicolon/backslash/quebra, fim exclusivo, fronteira de dia, DST em zona que efetivamente tenha transição, reexportação da mesma revisão e mudança de horário com UID constante. UID identifica bloco lógico, não hora/plano; SEQUENCE não aumenta num retry sem revisão. Exportação manual em cliente externo tem comportamento próprio: não generalizar ausência de duplicata no adaptador a todos os importadores.

**Divergência a resolver:** etapa 4 §9 fixa DTSTAMP na criação. RFC 5545 §3.8.7.2 distingue objetos com METHOD (criação da instância) de objetos **sem METHOD** (última revisão no calendar store, equivalente a LAST-MODIFIED). Para exportação simples sem METHOD, recomendar persistir DTSTAMP por revisão e preservá-lo em retries da mesma revisão; CREATED pode guardar criação. Registrar a divergência contratual e decidir antes do congelamento; não implementar oráculo que aprove criação imutável em todas as revisões como “conforme RFC”. Nenhum documento anterior foi alterado nesta pesquisa.

**Sync [P].** Só recibo confirmado após efeito consultável e equivalente. Backend-mock independente mantém contador de recursos e versões; ensaiar criação/update/delete, timeout pós-efeito, ACK perdido e revisão externa. Backend real necessita smoke/readback próprio. Sem sync habilitado, checks remotos=N/A com motivo; exportação local continua elegível. Sem consulta após timeout, UNKNOWN_EFFECT é resultado correto, não sucesso de escrita. Antecedentes `daboo2007caldav`/`google2026calendarcreate` são da pesquisa 3; update/delete específicos do Google permanecem não auditados nesta rodada.

## 9. Saídas de curadoria e operação

### O15 — Recursos, URLs e estado de acesso (W09; F19/F17)

**Método/oráculo [P].** Fixtures de páginas/transcrições e fetch real/cache identificado; comparar resource_id, URL encontrada/final, data/hash, idioma, tipo e estados `metadata_only/text_read/transcript_read/unavailable` ao log do conector e conteúdo de fato disponível. `access_status_accuracy=#estados corretos/#recursos ensaiados`; matriz de confusão destaca metadata_only incorretamente promovido a lido. URL 200 não implica conteúdo legível nem pertinência.

Especialistas avaliam alinhamento ao tópico, nível e idioma com evidência; `relevance_rate=#recomendações pertinentes/#recomendações julgadas`, com N, rubrica e IC. Testar link morto, redirect, paywall, conteúdo mudado, cache offline, vídeo sem transcrição e transcrição fornecida. Para cada resumo, exigir spans/trechos no snapshot lido e auditoria de apoio de O03; contar resumos de conteúdo não lido (gate zero). Recursos indisponíveis declarados corretamente podem passar estado de acesso, mas não contam como conteúdo lido.

**Limite/recomendação.** ≥.90 pertinência, precisão do estado e continuidade offline. Mocks servem a reprodução, fetch real a acesso no instante registrado; nenhum comprova disponibilidade futura. Antecedente `ytcaptions` da pesquisa 3 descreve limites de acesso a legendas; não transforma título/thumbnail em leitura de vídeo.

### O16 — Recibo, alteração, exclusão e recuperação (W10/W11; F15/F18/F21)

**Base.** `sqlitewal` [N] documenta commits/WAL, concorrência e limites de cópia; idempotência/outbox é contrato local [P], não propriedade automaticamente fornecida pelo WAL. **Oráculo:** ledger de operações do controlador de teste fora do DB sob ensaio, snapshots lógicos antes/depois, inspeção de tabelas e backend de efeito independente.

Após cada crashpoint (antes commit, depois commit, antes efeito, depois efeito/antes ACK, depois recibo), reiniciar e conferir: mesmo operation_id+digest retorna recibo semanticamente idêntico; digest diferente falha; evento/projeção/outbox são tudo ou nada; revisão esperada impede lost update; não há segundo efeito lógico. Medir `duplicate_effects=Σ_op max(0,#efeitos_lógicos_observados−1)` e `committed_losses=#operações comprometidas cujo efeito local durável esperado desapareceu`. Pendente/desconhecido é estado próprio, não perda presumida de efeito remoto. Não contar retries de leitura como duplicação de efeito.

**Exclusão.** Inserir marcadores sintéticos únicos em originais, eventos, índices, vetores associados, resumos, caches, checkpoints e traces; pedir exclusão confirmada e consultar todos os caminhos autorizados por ID/termos/paráfrase, reconstruir índices, replay e restaurar backup conforme política. Verificar ausência de payload e refs recuperáveis indevidas e aplicação de tombstones sem payload no restore. Busca textual isolada não detecta derivados sem o marcador; auditar dependências e ownership. Distinguir irrecuperabilidade pela aplicação de apagamento forense de bytes: este ensaio não prova sanitização física de SSD/WAL/backups.

**Recomendação/limite.** Zero duplicata/perda comprometida e exclusão propagada no escopo ensaiado; contagem por operação/falha. Retenção de backups tem prazo e política explícitos; não anunciar exclusão instantânea de cópias cuja expiração é futura. ACK só passa se estado verdadeiro após recuperação; checkpoint em DB distinto não garante atomicidade com domínio.

### O17 — Trace, medidas, budgets e diagnóstico (W11/todos; F11/F12/F22)

**Base [N].** `oteltrace` define trace/span, timestamps, status e links, não contagem automática de tokens. **Oráculo [P]:** controlador emite lista esperada de eventos/chamadas e timestamps monotônicos, runtime-mock devolve counts conhecidos; comparar trace coletado após flush com execução esperada por IDs. Evitar usar o próprio trace como único esperado.

`span_completeness=#spans obrigatórios presentes e válidos/#esperados`; confira parent/links, ordem causal, uma raiz por turno, status/truncamento, retries e terminais. `token_error=reported_total−Σ_counts_backend_todas_chamadas` quando conhecidos; separar input/reasoning/output segundo API para não contar raciocínio duas vezes se já incluso em completion. Total desconhecido é null com razão e cobertura de medição; OTel attributes não aceitam null, portanto guardar razão/ausência no atributo e null no registro de métricas de domínio.

Latência ativa mede início→terminal excluindo espera humana, inclui fila/tools/reparos. Não somar duração de spans sobrepostos: usar intervalo raiz, união de períodos ativos ou caminho crítico para decomposição. p50/p95 sobre tentativas, com timeout/censura e proporção explícita; se quantil de conclusão não identificável pelos casos censurados, informar limite/inconclusivo em vez de tratá-los como duração concluída. Registrar limite realmente aplicado e tempo de cancelamento, além de segundos até detectar/recuperar.

**Recomendação.** 100% etapas obrigatórias no teste e falhas no denominador; medir overhead instrumentado versus sem exportação nos casos de desenvolvimento. RSS/VRAM precisam de amostragem declarada e pico pode ser perdido entre amostras. Energia só com contador/medidor identificado; ausência não é zero. Trace estruturalmente perfeito não comprova tarefa correta nem efeito comprometido.

### O18 — Manifesto, instalação, diagnóstico e backup/restore (W12; F18/F24)

**Método/oráculo [P].** Inventário independente compara arquivos/hashes esperados com bundle: lock Python, binário/fork, pesos, tokenizer/template, OCR/idiomas, embedding/reranker, skills/prompts/schemas, corpus, configurações, SO/hardware/drivers e SQLite realmente carregado. Hash publicado é esperado; recomputar SHA local sobre bytes para verificação. Manifesto autodeclarado não substitui essa inspeção.

Instalar em ambiente limpo com rede bloqueada e cache/bundle declarado, executar doctor e smoke completo de ingestão→RAG→prática/pausa/restart→assessment/estado→solver/ICS→trace. Remover individualmente peso/OCR/lock ou alterar hash para testar diagnóstico e não-sucesso. `reproduction_success=#ambientes que passam todos os checks/#ambientes elegíveis ensaiados`; hardware único limita generalização.

**Restore.** Com escritores fechados/conjunto consistente, comparar snapshots lógicos e originais antes/apos restore em diretório novo, integridade/FKs, replay, fontes/citações, projeções, agenda/UIDs e recibos. Não exigir arquivo SQLite byte a byte igual após checkpoint; exigir conteúdo/versionamento esperado e hashes de artefatos imutáveis. `sqlitewal` afirma que WAL integra estado persistente: DB aberto copiado sem WAL é fixture negativa, não backup aceito. `uvlock` da pesquisa 3 é antecedente; lock sozinho não inclui pesos/binários/OCR nem prova bundle offline.

**Recomendação/limite.** Todos os artefatos requeridos, restore íntegro e smoke offline; reportar tempo/espaço e diagnóstico. Sucesso no mesmo hardware não demonstra portabilidade GPU/SO, e kill de processo não simula integralmente queda elétrica. Checksum/integridade não revela omissão sem inventário ou ledger externo.

## 10. Integração, falhas e entrega para a etapa 8

### 10.1 Matriz de cobertura e método prioritário

| IDs | Método principal | Oráculo prioritário | Validação de limite/falha |
|---|---|---|---|
| O01/O02 | Alinhamento edit distance; EM; F1 e autoridade | Página original + anotações/tuplas | F01/F02/F10: sinais, datas, ambiguidade, refs erradas |
| O03/O04 | qrels/ranking; claims/ALCE/RAGAs; rubrica | Ouro documental e humanos | F03/F04: falta suporte, fonte antiga, distração, contradição |
| O05/O06/O07 | Solução/checklist; rubricagem; sequência/reveal | Especialista + comparador + estados | F05/F06/F11: gabarito ruim, reveal, recusa, espera/loop |
| O08/O09 | Kappa/erro seletivo; replay; previsão futura opcional | Humanos + redutor independente | F06/F07/F23: length/order bias, ajuda, retries, futuro |
| O10/O11 | QA temporal/recall IDs; fatos críticos/budget/Δdownstream | Ledger por corte + fontes + tokenizer | F08/F09/F12/F17/F21: correção, compressão, isolamento |
| O12/O13 | EM duras; enumeração; viabilidade/status/diff | Demandas confirmadas + tempo original | F13/F14: slots, DST, snapshot, fixos, UNKNOWN |
| O14/O15 | Parser/readback; acesso real e apoio | RFC + parser distinto/backend + conteúdo | F15/F19/F20: timeout, UID, all-day, metadata-only |
| O16/O17/O18 | Ledger/crashpoints; trace esperado; clean install/restore | Controlador externo + inventário | F18/F21/F22/F24: atomicidade, ressurreição, counters, bundle |

F16/F17 (injection/isolamento) atravessam vários O: executar os pares limpo/perturbado da etapa 6 e verificar efeito/alteração de autoridade em O02/O12/O14/O16, leak em O10/O15 e terminal em O17. JSON válido não conta como resistência: `attack_success=#casos com efeito não autorizado/#ataques executados`; tentativas e efeitos são medidas distintas. Esta pesquisa não introduz novo benchmark de segurança nem declara revisão dessa literatura.

### 10.2 Protocolo implementável [P]

1. Congelar política de normalização, qrels/unidades, tolerâncias, rubricas, critérios críticos, timezone/tzdata, redutor, semântica de calendário e versões dos avaliadores em desenvolvimento/validação.
2. Construir adaptadores de avaliação independentes por artefato: `extract_eval`, `fact_eval`, `retrieval_eval`, `claim_eval`, `pedagogy_eval`, `assessment_eval`, `state_replay_eval`, `temporal_memory_eval`, `context_eval`, `demand_eval`, `schedule_oracle`, `calendar_eval`, `resource_eval`, `operation_audit`, `trace_audit`, `reproduction_audit`. São nomes sugeridos para etapa 8, não arquivos criados.
3. Validar os avaliadores com casos conhecidos e mutações significativas: sinal/data/ajuda alterados, citation irrelevante/resolvida, ranking vazio, resposta longa errada, estado atualizado duas vezes, plano com um minuto de conflito, UID trocado, span ausente. Oráculo que não rejeita a mutação deve ser corrigido antes da execução final.
4. Rodar condições/baselines/ablações e seeds da etapa 6 com resets e controle de cache. Para falhas, par limpo/perturbado conserva caso/seed e mede Δqualidade/TSR/custo e contenção, sem retirar timeout.
5. Emitir tabelas por O e W com N, numerator/denominator, IC, disponibilidade, cobertura, falhas críticas e custo. Agregar TSR somente após gates essenciais, distinguindo conclusão de terminal seguro. Zero falhas observadas em N finito não prova risco populacional zero; com unidades independentes, limite superior unilateral binomial de 95% é `1−0.05^(1/N)`; com dependência, não usar número de turnos como N dessa fórmula.
6. Qualidade operacional/pedagógica de artefato é resultado deste ensaio. Ganho de aprendizagem requer protocolo humano prospectivo com pré-teste, pós-teste tardio e transferência; roteiros simulados não o estimam.

## 11. Fontes efetivamente consultadas e trilha transparente

Data comum: **30/09/2026**. Identidades completas das oito novas fontes constam no novo BibTeX; autores de referências reutilizadas permanecem nos BibTeX da pesquisa 3. “s.d.” indica ausência de data editorial verificável na documentação, não publicação em 2026. URLs abaixo foram efetivamente abertas; URLs com versão explícita que resultaram de redirecionamento/conteúdo são registradas como tal. HTML truncado não autoriza presumir leitura de apêndices ausentes.

| # / key / localização | Identidade verificada e URL consultada | Alcance real da leitura e uso |
|---|---|---|
| 1 `jiwerQuality` — nova | **JiWER** / **Usage**, Jitsi/JiWER contributors, s.d. https://jitsi.github.io/jiwer/ ; https://jitsi.github.io/jiwer/usage/ | Documentação primária: distância mínima, CER/WER, API/alinhamentos/transformações, referências vazias >=4.0. Transferência ASR→OCR proposta; não benchmark OCR executado. |
| 2 `thakur2021beir` — nova | **BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models**, Nandan Thakur, Nils Reimers, Andreas Rücklé, Abhishek Srivastava, Iryna Gurevych, 2021. https://arxiv.org/abs/2104.08663 ; https://raw.githubusercontent.com/beir-cellar/beir/main/beir/retrieval/evaluation.py | Registro v4/abstract e código oficial `EvaluateRetrieval`, pytrec_eval/k_values/remoção de IDs/média. Artigo integral não lido; fórmula/ganho escolhidos e fixture de compatibilidade são especificação local, não resultado extraído de leitura integral do BEIR. DOI arXiv e comentário de aceitação conferidos no registro. |
| 3 `gao2023alce` — nova | **Enabling Large Language Models to Generate Text with Citations**, Tianyu Gao, Howard Yen, Jiatong Yu, Danqi Chen, EMNLP 2023. https://aclanthology.org/2023.emnlp-main.398/ ; https://arxiv.org/html/2305.14627 (retornou v2) | ACL confirma autores/ano/páginas/DOI. HTML: tarefa e §§2–3, recall/precision de citações, apoio conjunto e limites; leitura direcionada, saída truncada antes de aprofundar avaliação humana/apêndices. Não declarar leitura integral nem revalidar correlações do paper. |
| 4 `es2024ragas` — nova | **RAGAs: Automated Evaluation of Retrieval Augmented Generation**, Shahul Es, Jithin James, Luis Espinosa Anke, Steven Schockaert, EACL 2024. https://aclanthology.org/2024.eacl-demo.16/ ; https://arxiv.org/html/2309.15217 (retornou v2, 28/04/2025) | Metadados editoriais 2024; método lido na revisão arXiv 2025, §§3–5: decomposição/verificação, relevâncias, WikiEval/limites. Distinguir publicação e revisão; não conferir API atual do pacote por inferência do artigo. |
| 5 `zheng2023judge` — nova | **Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena**, Lianmin Zheng, Wei-Lin Chiang, Ying Sheng, Siyuan Zhuang, Zhanghao Wu, Yonghao Zhuang, Zi Lin, Zhuohan Li, Dacheng Li, Eric P. Xing, Hao Zhang, Joseph E. Gonzalez, Ion Stoica, 2023. https://arxiv.org/html/2306.05685 (v4) ; https://arxiv.org/abs/2306.05685v4 | Autores/ano/DOI arXiv conferidos; HTML §§3–4: vieses, ordem dupla, referência e definição de acordo/empates. Saída truncada; não revisão dos apêndices completos. Venue NeurIPS consta no comentário, entrada cita versão arXiv sem paginação inventada. |
| 6 `kim2024prometheus` — reutilizada, pedagogia | **Prometheus: Inducing Fine-grained Evaluation Capability in Language Models**, Seungone Kim et al., 2024, v2 de 09/03/2024. https://arxiv.org/html/2310.08491v2 | Reconsulta de autoria, §§3–5: entradas/rubricas, avaliação/correlação humana e ranking iterativo; saída truncada nos resultados, apêndices não revistos. Não copiar key nem transportar sua correlação ao Monitor. |
| 7 `wu2025longmemeval` — reutilizada, pedagogia | **LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory**, Di Wu, Hongwei Wang, Wenhao Yu, Yuwei Zhang, Kai-Wei Chang, Dong Yu, 2025, v2 de 04/03/2025. https://arxiv.org/html/2410.10813v2 | Reconsulta §§3–4 e início de §5: cinco capacidades, tipos de pergunta, QA/recall, decomposição de valores e contexto-oráculo. HTML truncado; não auditar apêndice da meta-avaliação nem importar seu >97% ao juiz local. |
| 8 `guo2017calibration` — nova | **On Calibration of Modern Neural Networks**, Chuan Guo, Geoff Pleiss, Yu Sun, Kilian Q. Weinberger, ICML/PMLR 70, 2017. https://proceedings.mlr.press/v70/guo17a.html ; https://arxiv.org/html/1706.04599 (v2) | PMLR verifica identidade/páginas/ano. HTML tem título renderizado “Supplementary Materials for…”, mas expõe texto principal §§2/4: confiabilidade/ECE/NLL, calibradores e logits. Leitura desses trechos, saída truncada; não assumir inspeção de todos suplementos/gráficos. URL primária usada, sem DOI editorial inventado. |
| 9 `sklearnKappaQuality` — nova | **cohen_kappa_score**, scikit-learn developers, s.d. https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html | Documentação 1.9.1 retornada: fórmula, marginais, pesos lineares/quadráticos, labels e indefinição. Fonte primária de API; Cohen/Artstein citados na página não foram consultados separadamente. |
| 10 `sklearnCalibrationQuality` — nova | **Probability calibration**, scikit-learn developers, s.d. https://scikit-learn.org/stable/modules/calibration.html | Guia 1.9.1: curvas, Brier/log loss versus calibração isolada, dados separados, sigmoid/isotônico/temperature. Exemplos gráficos e referências internas não reproduzidos nem abertos como novos estudos. |
| 11 `google2024cpsat` — reutilizada, pedagogia | **CP-SAT Solver**, Google, atualização 28/08/2024. https://developers.google.com/optimization/cp/cp_solver | Documentação primária reconsultada: inteiros, cinco status e enumeração do próprio solver. Oráculo de enumeração independente é adaptação local, não exemplo pronto dessa página. |
| 12 `desruisseaux2009icalendar` — reutilizada, pedagogia | **Internet Calendaring and Scheduling Core Object Specification (iCalendar)**, Bernard Desruisseaux (editor), RFC 5545, 2009. https://www.rfc-editor.org/rfc/rfc5545.html | Retorno extenso truncado; §§3.1 e gramática no trecho inicial, §§3.6.1 e 3.8.7.2–4 recuperados por leitura direcionada da resposta completa da ferramenta. Fim exclusivo/DATE, DTSTAMP e SEQUENCE efetivamente lidos; não leitura integral das 175 páginas. |
| 13 `sqlitewal` — reutilizada, arquitetura | **Write-Ahead Logging**, SQLite developers, atualização 25/08/2026. https://sqlite.org/wal.html | Página reconsultada: snapshots/escritor/commit, FULL/NORMAL, arquivo WAL e cópia, busy/correção WAL-reset. Outbox, apagamento e oráculo de crash são projeto local, não garantias ensaiadas dessa documentação. |
| 14 `oteltrace` — reutilizada, arquitetura | **Traces**, OpenTelemetry Authors, s.d. https://opentelemetry.io/docs/concepts/signals/traces/ | Página primária: spans/IDs/status/links/attributes, exporters e JSON ilustrativo não OTLP. Não auditar semconv de LLM nem inferir suporte automático a tokens/energia. |

**Localização e exclusões.** Âncoras solicitadas BEIR/ALCE/RAGAs/LongMemEval levaram a registros arXiv/ACL e código oficial BEIR; rubricas e juiz levaram a Prometheus/Zheng; calibração a PMLR/Guo e documentação scikit-learn; CER/WER a documentação JiWER; operações às fontes oficiais já usadas na pesquisa 3. Não houve falha HTTP nessas consultas. Restrições encontradas foram truncamento de HTML longo, leitura apenas de metadados/abstract do artigo BEIR e diferença de versões RAGAs/Guo. Não contar listas de referências internas como artigos consultados. Blogs comerciais, rankings móveis, BLEU/ROUGE como prova de corretude, votação de agentes como ouro e confiança verbal como probabilidade foram excluídos como métodos principais; não alegar busca exaustiva por alternativas.

## 12. Pendências e decisões finais

1. **Ouro/rubricas:** autorizar corpus, definir granularidade de tópico/claim/família, equivalências e erros críticos; pilotar acordo humano em português. Congelar antes do teste e manter anotação pré-adjudicação.
2. **Avaliadores:** pin de JiWER/pytrec_eval/scikit-learn e teste de convenções (normalização, vazios, ganho linear, empates, kappa indefinido); versões web consultadas não são lock de runtime.
3. **O03/O08:** validar juiz/NLI no domínio com dados independentes e auditar falsos negativos; definir política de abstinência e custo. Não impor API paga ou TRUE/T5-11B no núcleo offline por mera presença nos artigos.
4. **O09:** especificar “contradição recente” e janela/escopo de erro crítico, regras de ordenação/revisão e delayed retrieval. Probabilidades/BKT continuam módulo futuro até logs prospectivos suficientes.
5. **O13:** construir enumeração pequena separada e validador em instantes originais; certificar limites de instância; distinguir prova na grade de viabilidade contínua e definir como expor déficit causado pela discretização.
6. **O14:** resolver conflito DTSTAMP criação versus última revisão sem METHOD; selecionar parser independente/pinar tzdata; backend remoto e update/delete condicionais necessitam documentação/teste específico.
7. **O16–O18:** explicitar exclusão lógica/retensão de backup, inventário de derivados, crashpoints, ledger externo, counts reais do fork e instalação/restore em ambiente limpo. Medir hardware, não herdar números de documentação.
8. **Inferência experimental:** conferir suficiência de N por famílias/trajectórias após piloto; gates e IC inconclusivos permanecem inconclusivos. Nenhum dado experimental foi fabricado, nenhum gate foi recalibrado olhando teste.

**Decisão central:** usar verificadores independentes onde há contrato formal; qrels e claims com ouro para retrieval/citações; humanos com rubricas e meta-avaliação para pedagogia; memória e estado avaliados por prefixos temporais; solver por tempo original e enumeração pequena; calendário por norma, parser distinto e readback; operação por ledger/restore. Métricas automáticas aceleram diagnóstico, mas não substituem o oráculo de cada transformação.
