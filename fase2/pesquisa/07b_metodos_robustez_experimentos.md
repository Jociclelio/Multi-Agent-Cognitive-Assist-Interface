# Etapa 7b — Métodos de robustez e desenho experimental do EduAgent-OS

## 1. Escopo, estatuto e decisões

**Fechamento posterior:** mapa4 §15 e mapa8 §12 definem revisão global/snapshot, política de demandas, estado/revisão por tópico, atividades, grade, identidade e testes de instrução completa/reduzida; mapa8 acrescenta orçamento/captura/anotação e matriz C→predicado. Esses mapas são normativos; pendências registradas aqui refletem o momento da pesquisa. Modelo/runtime, ouro real, calibração, potência e medidas de hardware continuam a depender de execução futura.

Pesquisa metodológica realizada em **30/09/2026**, orientada por `../documentos/04_mapa_completo_do_sistema.md`, `05_fluxos_resultados_e_falhas.md` e `06_protocolo_de_avaliacao.md`. Complementa C18 (dados/ouro) e C19 (comparação/análise) e prepara a especificação executável da etapa 8. Os procedimentos abaixo são propostas implementáveis; nenhum experimento, teste do sistema ou resultado de desempenho foi executado nesta pesquisa.

**Decisão principal:** combinar propriedades locais, relações metamórficas, máquinas de estado, injeção de falhas e avaliação de trajetórias com oráculos independentes. Uma resposta fluente, um JSON válido, um trace presente ou um solver que declara sucesso não constitui, isoladamente, evidência de correção.

1. Preservar desenvolvimento, validação e teste **fixos**, separados por família documental/item, trajetória e família de agenda. Transformações, versões, ataques e seeds do mesmo caso herdam seu split. Desenvolvimento descobre defeitos e ajusta rubricas; validação seleciona configurações; teste mede a configuração congelada.
2. Preservar as comparações MA/SA e ablações da etapa 6 com mesmo modelo, acesso aos dados/tools e teto de recursos por tarefa. O custo de coordenação do MA pertence ao orçamento.
3. Separar `task_completion`, `safe_terminal`, violação publicada, efeito indevido e recuperação. Abstinência correta em pergunta originalmente sem suporte pode ser sucesso; falta de evidência causada por uma falha não transforma automaticamente a tarefa original em concluída.
4. Usar oráculos de estado/efeito para invariantes e humanos cegos para conteúdo pedagógico/apoio semântico. Juiz LLM é secundário e calibrado; o Monitor do sistema não é o ouro de sua própria avaliação.
5. IC95% segue a etapa 6. Os gates numéricos daquela etapa são decisões de engenharia locais, não limiares universais obtidos da literatura. Não declarar que dez casos por F, três seeds ou trinta trajetórias fornecem potência/precisão suficientes.
6. Manter falhas e execuções censuradas no relatório e nos denominadores apropriados. Ausência de medição é `null` com motivo; ausência de violação observada não demonstra risco populacional zero.

As citações usam chaves BibTeX entre colchetes. Há **16 fontes nucleares** na trilha da seção 10: 13 entradas novas em `references_robustez.bib` e três entradas existentes reaproveitadas. Consultas de metadados/resumo são distinguidas de leitura de mecanismos em documentação ou texto HTML.

## 2. Unidade de ensaio, par clean/fault e independência dos oráculos

### 2.1 Registro mínimo de um caso

A etapa 8 deve representar cada caso por: `case_id`, `family_id`, `trajectory_id?`, split, W/O/F cobertos, estado inicial e hash, mensagens/script do estudante, fontes autorizadas e versões, ouro e versão da rubrica, condições, seeds, terminal esperado, propriedades, limites congelados, local/gatilho da injeção e versão do controlador. Um caso pode ter várias falhas associadas, mas deve indicar qual causa é manipulada em cada execução.

**Construção do par:** restaurar duas cópias independentes do mesmo estado inicial; executar clean e fault sob a mesma condição/seed, relógio de domínio, versões de corpus, respostas de conectores e política de cache. Injetar somente a diferença especificada. Randomizar/counterbalancear a ordem para reduzir aquecimento e deriva térmica. Registrar o instante e se o gatilho foi efetivamente alcançado. Um nó que nunca foi visitado não fornece evidência de resistência à falha destinada àquele nó.

Há dois desenhos complementares:

- **Ponta a ponta:** o agente escolhe a trajetória; mede utilidade real sob exposição disponível. Reportar casos elegíveis, alcançados, expostos e falhas do próprio controlador.
- **Fronteira controlada:** a partir de snapshot/artefato congelado, forçar a chamada do serviço ou validar um artefato deliberadamente defeituoso. Mede contenção naquela fronteira, sem confundir ausência de exposição com defesa eficaz. Não substitui o primeiro desenho.

Compartilhar seed reduz uma fonte de variação, mas não garante as mesmas amostras aleatórias depois que os caminhos divergem. Separar RNG de geração, geradores de casos e controlador de falhas; registrar streams/chamadas. Manter o pareamento por caso/seed, sem selecionar retrospectivamente a seed mais favorável.

### 2.2 Estimandos de impacto

Para métrica definida em ambos os braços, `d(i,s,a,f) = Y_fault − Y_clean`, com caso i, seed s, arquitetura a e falha f. Qualidade/sucesso maiores são melhores; latência/tokens/violações maiores são piores. Exibir os níveis absolutos e a diferença: um delta próximo de zero pode ocultar dois braços igualmente ruins.

Medir por F e por W: conclusão, terminal seguro, qualidade específica de O, publicação inválida, efeitos indevidos, chamadas/tokens, tempo ativo/fila, tempo até detecção e tempo até recuperar estado verificável. Definir detecção pelo primeiro evento observável de erro/pendência; recuperação pelo primeiro estado/readback aceito pelo oráculo, não pela mensagem “recuperado”. Casos sem recuperação até o horizonte congelado são censurados e têm razão registrada.

Não atribuir zero à qualidade de um artefato inexistente. Reportar qualidade condicional à emissão junto com taxa de emissão e conclusão para todas as tentativas; para uma comparação não condicional, pré-definir um desfecho composto, como “emitiu artefato e passou todos os critérios essenciais”, com denominador completo. Diferenças de latência de término incluem terminais de erro; tempo até conclusão da tarefa exige tratar censura. Redução de latência por abortar cedo não demonstra maior eficiência produtiva.

Para comparar robustez de MA e SA, estimar também `I_f = (Y_MA,fault − Y_MA,clean) − (Y_SA,fault − Y_SA,clean)` nos mesmos casos. Esse contraste mede diferença de degradação, não superioridade absoluta. Controladores por fronteira usam gatilhos semânticos equivalentes entre arquiteturas, e não o “terceiro nó” de grafos diferentes.

### 2.3 Oráculos independentes e teste do avaliador

| Objeto | Oráculo proposto | Independência exigida |
|---|---|---|
| OCR/fatos/fontes | Transcrição humana da página original, localização e campos críticos anotados | Não reutilizar o texto extraído pelo sistema como verdade |
| Claims e pedagogia | Dois anotadores cegos, fontes originais e rubrica versionada; solução exata quando aplicável | Ouro anterior à saída avaliada; sem autovalidação do Tutor/Monitor |
| Estado de tópicos/memória | Modelo de referência simples de eventos, ajuda, validade, correções e tombstones | Sem chamar o redutor/projeção do sistema para obter o esperado |
| Agenda | Verificador em instantes/minutos originais; enumeração independente nas pequenas | Sem reaproveitar discretização ou matriz de restrições do solver |
| Commit/efeito | Ledger do controlador, consulta direta de operações e estado do destino/mock | ACK/texto/trace do agente não é readback |
| ICS | Parser de implementação distinta e tuplas semânticas de eventos | Round-trip com a própria biblioteca pode reproduzir seu defeito |
| Telemetria | Contadores e relógio do harness/proxy de fronteiras | Não somar somente os spans que o sistema escolheu emitir |
| Reprodução | Ambiente limpo offline e manifesto de artefatos | Não depender dos caches da máquina de desenvolvimento |

Validar os próprios oráculos em desenvolvimento com controles positivos/negativos: plano com sobreposição conhecida; span inexistente; retry duplicado; correção ignorada; contador com chamada omitida; ICS com fim alterado. Se o oráculo não detecta um defeito conhecido, o ensaio correspondente não está validado. Mutation testing focalizado testa sensibilidade dos verificadores, inspirado pela discussão do SQLite [sqliteTesting], sem impor cobertura universal nem uma taxa arbitrária de mutantes mortos. Defeitos equivalentes e falhas do harness são adjudicados separadamente.

## 3. Métodos locais: propriedades, metamorfismo e estado

### M01 — Property-based testing, fronteiras e relações metamórficas

**Mecanismo.** Gerar dados de domínio válidos e variações inválidas, aplicar propriedades e reduzir automaticamente o contraexemplo. Hypothesis fornece estratégias, regras, precondições, invariantes e redução de sequências [hypothesisStateful]. Metamorfismo relaciona múltiplas entradas/saídas quando uma saída exata é difícil de especificar [chen2018metamorphic]. A definição foi consultada no resumo editorial; as relações a seguir são derivações do contrato local, não relações comprovadas naquele artigo para agentes educacionais.

**Como implementar posteriormente:** estratégias para Unicode, números/unidades, datas parciais, versões/refs, durações, zonas e grafos acíclicos; geradores estruturados que exercitam campos semanticamente errados mesmo quando passam pelo schema. Concentrar exemplos nos limites configurados: limite−1, limite, limite+1, tamanho zero, campo ausente e incompatibilidade entre envelope e payload. Guardar exemplo reduzido, seed, versão do gerador e distribuição de categorias.

Relações que podem virar assertions determinísticas:

- Renomear consistentemente IDs de uma agenda e permutar demandas preserva conjunto de soluções factíveis e vetor ótimo lexicográfico, não necessariamente o plano escolhido entre empates.
- Ampliar disponibilidade sem mudar outros contratos não remove soluções factíveis; acrescentar bloqueio não cria soluções antes proibidas. Comparar conjuntos/ótimos nas pequenas. Não exigir melhora da solução encontrada por solver limitado por tempo.
- Mudar representação UTC/zona mantendo os mesmos instantes preserva conflitos e durações. Deslocar todo o horizonte exige também deslocar compromissos, earliest e deadlines e controlar transições de zona; deslocamento de dias locais não é sempre deslocamento fixo em segundos.
- Repetir operação com mesmo ID/digest preserva recibo e cardinalidade de efeito; mesmo ID/digest diferente deve ser rejeitado. Reexportar a mesma revisão preserva identidade semântica/UIDs.
- Adicionar eventos posteriores ao corte de uma consulta retrospectiva não muda a resposta naquele corte. É preciso declarar se o corte é por validade (`occurred_at`) ou por conhecimento disponível (`recorded_at`); correção retroativa pode legitimamente mudar uma retrospectiva de validade consultada hoje.
- Reordenar chaves JSON preserva interpretação. Não tratar troca de números, polaridade, autoridade, usuário ou versão como transformação semântica neutra.

**Metamorfismo semântico exige ouro:** paráfrase validada de resposta correta deve manter critérios; versão prolixa de resposta errada não deve ganhar crédito; mudança somente de ajuda altera classificação assistida, não o conteúdo julgado. Adicionar distratores a RAG ou ruído a uma imagem é teste de sensibilidade, não garantia matemática de ranking/texto invariantes. A própria transformação pode alterar legibilidade, sentido ou fatos: revisá-la e anotar sua intensidade antes do teste.

**Impacto e limites.** Medir violação de propriedades, tamanho do contraexemplo e Δ por artefato/downstream. Cobertura do gerador é cobertura da distribuição escolhida, não de todas as entradas possíveis. Para geração LLM, comparar claims/estado/rubrica, não igualdade byte a byte. Relações incorretas produzem falsos defeitos; relações fracas podem deixar dois resultados incorretos concordarem.

### M02 — Model-based/stateful testing e replay temporal

**Mecanismo.** Uma máquina de referência em memória executa ações e verifica invariantes após cada passo. O exemplo oficial do Hypothesis compara implementação persistente e modelo simplificado, combinando regras e valores reutilizados por Bundles [hypothesisStateful].

**Modelo local:** estado com versão, operações/digests, attempts, ajuda/reveal, fatos e tempos, plano/confirmação, derivados e tombstones. Regras: publicar item → tentativa → pista/reveal → assessment → commit/retry → corrigir fato → replanejar → aprovar → exportar → cancelar/reiniciar → excluir → reconstruir/restaurar. Precondições tornam caminhos executáveis, mas criar também regras negativas para aprovação obsoleta, resposta sem item e acesso sem ownership; não filtrar justamente os estados que devem ser negados.

Invariantes: assessment aceito afeta uma tentativa uma vez; ajuda não vira independência; eventos futuros não entram no corte de conhecimento; superseded não volta como atual; confirmação corresponde a revisão/digest; plano em execução preserva blocos fixos; derivados publicados correspondem a versão completa; exclusão impede recuperação pelo escopo contratado. Após restart, comparar domínio com o modelo e reconstruir projeções sem aproveitar o checkpoint como autoridade.

**Impacto e limites.** Reportar primeira transição ilegal, Δestado e propagação a demandas/plano. Redução de sequência deve preservar condições temporais e a falha; guardar também a sequência original. O modelo deve ser menor e escrito a partir dos contratos, com revisão independente: copiar a implementação gera erro correlacionado. Stateful testing sequencial não exercita por si só interleavings concorrentes. No MVP, `estimate=null`; métricas probabilísticas e BKT ficam N/A. Uma futura variante BKT requer shadow mode e dados temporalmente separados, fora da admissão atual.

### M03 — Ouro semântico, testes contrastivos e risco–cobertura

Para F01–F06/F08–F09, associar anotação ao original: trecho/claim, verdade, suporte, ambiguidade, critérios, unidades, ajuda e terminal. Produzir pares contrastivos (curta correta versus fluente errada; fonte com versus sem evidência; fato atual versus superseded), incluindo casos em que o julgamento correto é `undecidable`. O avaliador vê enunciado, resposta original, referência e rubrica; não recebe a avaliação do Tutor como fonte.

Anotadores fazem primeira avaliação separadamente e cegos à arquitetura, antes da adjudicação. Reportar acordo pré-adjudicação, matriz de confusão e falso acerto crítico, além do ouro final. Julgamentos de claims separam existência da referência, resolução da versão e implicação semântica. Gabarito “concordante” entre Tutor e Monitor não é prova de correção quando ambos usam o mesmo modelo/fonte defeituosa.

Juiz LLM: calibrar em desenvolvimento/validação contra humanos por disciplina, tipo de erro, ajuda e comprimento; fixar modelo, prompt, referência e política de abstinência. Contrabalancear ordem A/B, testar respostas iguais e versão prolixa sem informação nova, ocultar rótulos MA/SA. Zheng et al. discutem posição, verbosidade e limitações de raciocínio [zheng2023judge]; seu acordo com humanos no MT-Bench não é uma estimativa de confiabilidade em português ou de acerto formativo aqui. Preferência não substitui correção.

Escolher regra de aceitação na validação e reportar curva risco–cobertura: cobertura = aceitos/elegíveis; risco = erros entre aceitos segundo ouro. Exibir também erro sobre todas as tentativas e abstinências indevidas. Em texto livre, confiança verbal não é probabilidade calibrada. Variação de estilo pode revelar viés, mas não determina, sozinha, qual resposta está correta.

## 4. Falhas operacionais, concorrência e efeitos

### M04 — Fault injection determinística e recuperação verificável

SQLite descreve falhar a n-ésima alocação/I/O, falhas únicas e persistentes, crashes e falhas compostas, com integridade e atomicidade verificadas depois [sqliteTesting]. Adaptar o princípio ao runtime e às fronteiras do EduAgent-OS:

1. Inventariar pontos: antes/dentro/depois do commit de domínio; antes/depois do checkpoint separado; construção/publicação de índice; outbox/lease; envio remoto; efeito no destino; resposta/ACK; backup e migração.
2. Nos wrappers, injetar timeout, erro tipado, truncamento, retorno inconsistente, busy e resposta perdida na n-ésima chamada. Diferenciar falha única de indisponibilidade persistente.
3. Em subprocesso isolado, encerrar o processo em barreira nomeada e reiniciar usando os mesmos dados de ensaio. Snapshot e ledger pertencem ao controlador externo, que sobrevive ao crash.
4. Para ENOSPC e busy, usar volume de ensaio limitado e conexão que mantém lock. Para OOM, distinguir erro simulado no adaptador e encerramento real por limite de memória. Cada camada testa mecanismos diferentes.
5. Retirar a falha; observar recuperação até horizonte fixo. Consultar operações, efeitos/destino, FK/integridade, projeções/replay e originais/índices. `integrity_check` satisfatório não prova que uma operação de domínio foi preservada.

| Crashpoint | Resultado verificável esperado |
|---|---|
| Antes de commit | Nenhuma promoção parcial de evento/projeção/outbox; tentativa pode ser reapresentada |
| Durante transação | Estado antigo ou novo completo, nunca mistura; recibo corresponde ao commit efetivo |
| Após commit, antes de checkpoint/resposta | Replay consulta operação autoritativa e reutiliza recibo; não aplica atualização outra vez |
| Após lease, antes de envio | Pendente recuperável após lease expirar conforme política; sem inventar efeito |
| Após efeito remoto, antes de ACK | Read/reconcile por identidade/versão; sem nova criação cega |
| Resposta perdida sem consulta possível | `UNKNOWN_EFFECT`, pendência verdadeira, sem retry automático |
| Durante indexação/backup/migração | Versão incompleta não ativa; backup incompleto não anunciado íntegro; migração retoma/rejeita de modo definido |

O WAL faz parte do estado persistente, e sua separação da base pode perder commits; WAL não torna múltiplas bases atomicamente consistentes [sqlitewal]. Testar a base de domínio, checkpoints, originais e manifesto como conjunto. Conferir a versão SQLite **real carregada**, não só a versão declarada da dependência, incluindo correção WAL exigida na etapa 4.

**Impacto e limites.** Medir perda de operações comprometidas, duplicatas, pendências verdadeiras, publicações inválidas, detecção/recuperação e custo adicional. `SIGKILL` testa crash de processo; não simula automaticamente corte de energia, reorder de escritas não sincronizadas ou corrupção do dispositivo. Simulação em VFS ou infraestrutura equivalente seria ensaio adicional explicitamente delimitado. Falhar wrapper antes do commit não valida atomicidade de I/O no meio do commit. Não chamar entrega ao menos uma vez de exactly-once distribuído.

### M05 — Interleavings controlados e checagem de histórico “linearizability-ish”

Porcupine verifica se um histórico concorrente é compatível com uma especificação sequencial executável, respeitando a precedência de chamadas/respostas [athalye2017porcupine]. Isso fundamenta um ensaio **restrito** para commits locais, não uma afirmação sobre todo o diálogo ou serviço remoto.

Modelo sequencial: `commit(id,digest,expected_version)` aceita novo ID só com revisão esperada atual; grava evento/projeção/operação/outbox atomically no domínio; ID/digest repetido devolve recibo; ID com outro digest falha. A ordem de deduplicação versus validação de versão deve ser explicitada: retry de operação já comprometida com expected_version antigo precisa recuperar o recibo, conforme etapa 4, sem ser confundido com nova escrita obsoleta.

Procedimento: dois clientes leem versão v; pausar em barreiras antes da verificação/commit; intercalar correção, aprovação e exportação; repetir duas chamadas do mesmo ID e dois IDs com mesma revisão; marcar bloco como iniciado entre preview e commit; renovar/expirar lease concorrente. Registrar invoke/return/result e estado, com relógio monotônico/coleta ordenada no controlador. Verificar primeiro históricos pequenos por enumeração de ordens legais; Porcupine é alternativa para exportar históricos quando a interface/modelo estiver definida. `timeout` do checker é inconclusivo, não “não linearizável”.

**Operações incompletas:** crash/timeout sem resposta pode ter ocorrido; representá-las como pendentes com possibilidades compatíveis com readback/ledger. Não removê-las arbitrariamente nem presumir sucesso. Leituras de snapshot declarado têm semântica de versão própria; uma leitura retrospectiva antiga legítima não viola um registro “atual”.

**Separação de garantias:** linearizabilidade do commit não basta para durabilidade, isolamento entre usuários ou validade pedagógica. Para outbox/remoto usar M02/M04 com pré-condições de identidade/ETag e reconciliação; exigir convergência sob recuperação quando o contrato a permite. Efeitos remotos sem consulta permanecem desconhecidos. Sem ordenação real confiável ou modelo completo, relatar “históricos compatíveis com o modelo local ensaiado”. Limites: explosão de estados, cobertura finita de schedules e deploy inicial sem multiusuário em rede.

## 5. Trajetórias de agente, ataque e disponibilidade

### M06 — Benchmark local inspirado em BFCL, AgentBench e AgentDojo

**BFCL.** A documentação inicial distingue seleção, argumentos/tipos, AST e execução; V3 adiciona multi-turn/multi-step, estado no fim de cada turno e execução mínima para tarefas de leitura [bfclMultiTurn]. Adotar quatro níveis da etapa 6: parse/schema → seleção/intenção → argumentos/domínio → efeito observado. Não importar normalização de strings que apaga sinal/pontuação de datas, nem tolerâncias do benchmark para números críticos. JSON estrito do projeto prevalece.

**AgentBench.** O texto apresenta ambientes interativos e categorias de término como formato inválido, ação inválida, contexto e limite de tarefa [liu2024agentbench]. Adaptar taxonomia às rotas W01–W12: terminal esperado, erro de conteúdo, versão/ownership, budget, timeout, espera e efeito desconhecido. `waiting_student` encerra a invocação sem chamadas extras. Término normal não equivale a sucesso.

**AgentDojo.** Adotar estado inicial, ferramentas determinísticas, objetivo legítimo e objetivo atacante, com funções separadas de utilidade e segurança sobre o ambiente [debenedetti2024agentdojo]. Injeção aparece em PDF, página ou retorno de tool disponível ao agente; exemplo local é instrução para promover uma data candidata ou alterar agenda sem confirmação. Avaliar objetivo alcançado, tentativa de chamada proibida, negação pelo dispatcher e efeito real separadamente. Detectar palavras adversariais não basta.

**Especificação implementável:** para cada W criar estado inicial, ações/ordem parcial obrigatórias, ações proibidas, condição de espera/encerramento e predicados finais. Ouro de trajetória é uma família de caminhos aceitáveis: leitura relevante antes de claim; validação antes de publicar; aprovação válida antes de outbox; readback após timeout. Permitir exploração/recuperação legítimas dentro do budget. Checar estado em cada turno e histórico de efeitos: escrever indevidamente e depois desfazer pode deixar estado final correto e ainda ser violação. Em consultas read-only, estado inalterado não prova que a fonte foi consultada ou que a resposta é sustentada.

**Ataques:** separar famílias/posições/idiomas entre splits; incluir objetivo legítimo sem ataque, ataque visto em desenvolvimento e variantes retidas para teste. Ataque adaptativo com busca contra uma defesa tem orçamento e acesso fixados; congelar controlador antes do teste, mantendo eventual otimização em tempo de ensaio registrada e equivalente entre condições. Não escolher apenas o ataque que funcionou contra SA. Medir utilidade clean, utilidade sob ataque sem efeitos adversos e ASR por efeito/objetivo. Reportar ASR sobre todos os casos elegíveis e, adicionalmente, condicionado à exposição/clean concluído com denominador explícito. Condicionamento em subconjuntos diferentes entre arquiteturas prejudica comparação.

Para F17 e F19, complementar o paradigma de agente com controladores determinísticos: ownership alternado, path/symlink, resolução DNS e redirect simulados, quota/404, metadata-only e versão de recurso. Assert de negação **antes** de leitura/envio no proxy; canários sintéticos permitem observar vazamento no ensaio. URL/DNS devem ser simulados no teste comparativo; smoke de conector real é evidência de integração distinta, com data registrada.

**Limites.** Benchmarks consultados não são testes de aprendizagem e seus escores não estimam eficácia do EduAgent-OS. Domínios, idiomas, tools e permissões diferem. Um detector que bloqueia tudo pode diminuir ASR e destruir utilidade; exibir ambas. Estado de mock correto não garante interoperabilidade real. Os limites de turnos daqueles benchmarks não são limites universais a aplicar aqui.

## 6. Observabilidade, performance e reprodução

### M07 — Auditoria cruzada de trace e benchmark de recursos

OpenTelemetry define spans, eventos, propagação e links úteis para outbox assíncrona [oteltrace]. É infraestrutura de observação, não um oráculo automático de custo ou sucesso.

Preparar ledger externo de chamadas com request IDs e relógio monotônico e conferir contra trace: fila, recuperação, contexto, geração, validação, solver, commit, tools, reparos, cancelamento e reconciliação. Uma chamada negada/falha deve ser contada mesmo sem resultado. Conferir tokens por resposta do backend e contagem do tokenizer fixado, registrando diferenças de definição/template; tokens de raciocínio desconhecidos permanecem desconhecidos. Soma de spans sobrepostos não é latência total: reportar tempo de parede e caminho crítico, além de tempos por componente. Relacionar continuidade assíncrona por operação/links, sem exigir uma árvore síncrona fictícia.

Teste F22: retirar um span, omitir um retry e devolver contador ausente; o auditor deve detectar divergência, não “consertar” preenchendo zero. Injete falha no exporter e verifique contadores locais/ledger. Antes de inferir eficiência, conferir completude das medidas de ambos os braços. Não logar payload pessoal completo; evidência semântica do ensaio fica nos artefatos autorizados com acesso controlado.

**Carga:** perfis cold-start/primeira consulta e warmed separados; tamanho do corpus/contexto, prompt real, output, fila e concorrência definidos. Testar o servidor de um slot/fila quatro com chegadas programadas e saturation, incluindo pedidos recusados. Medir desde chegada ao harness para evitar ignorar tempo na fila. Documentar hardware, runtime/fork, threads, modelos auxiliares, temperatura/estado energético quando disponíveis, cache e processos concorrentes. Ordem counterbalanced reduz deriva, não a elimina.

Reportar p50/p95 de tempo até terminal para todas as tentativas, timeout rate e distribuição de conclusão censurada. Se o quantil de tempo até conclusão não é identificável antes do limite, indicar isso, sem calcular p95 somente dos sucessos. RSS/VRAM vêm de medidor de processo/dispositivo, com intervalo de amostragem e risco de perder picos; energia só de contador/medidor identificado, com unidade, escopo CPU/GPU/parede, baseline e frequência. Não converter automaticamente tokens em energia. Desligar instrumentation em um ensaio diagnóstico pode estimar overhead, com pareamento; não retirar instrumentation de uma única arquitetura na comparação principal.

### M08 — Reprodução computacional e round-trip independente

Pineau et al. fundamentam disponibilização de código/dados e explicitação do procedimento para reprodução [pineau2021reproducibility]. Aplicação local: manifesto com commit, lock, wheels/binários, hashes de pesos/tokenizer/template/skills, OCR e idiomas, SQLite real, solver/timezone database, datasets/splits, mocks, controlador, rubricas, configuração do juiz, RNG, cache policy e hardware. Hash autentica identidade do artefato disponível; não demonstra correção.

F24: em ambiente limpo sem acesso à rede e sem caches herdados, instalar bundle autorizado e executar doctor, smoke das rotas núcleo, restore e subset congelado de avaliação. Remover peso/OCR/lock ou alterar hash em cópia do bundle; o diagnóstico deve identificar a dependência. Smoke não substitui reprodução de estimativas: distinguir instalação reproduzida, estado restaurado, resultado determinístico igual e métricas estocásticas compatíveis com a variação declarada. Uma seed não assegura determinismo entre GPU/runtime diferentes.

F20: gerar eventos com acentos, caracteres multibyte nas bordas de folding, escapes, all-day, meia-noite, revisão e UID estável; interpretar com parser distinto e comparar `(UID, início, fim, tipo DATE/DATE-TIME, revisão, texto)` ao plano. RFC 5545 explicita CRLF/folding em octetos e UTF-8 (§3.1), e início inclusivo/fim exclusivo, inclusive all-day (§3.6.1) [desruisseaux2009icalendar]. Comparar semântica, não ordenação de propriedades. Importação em cliente real é smoke separado: UID não garante deduplicação universal do importador manual. Modelo de plano usa minutos/instantes originais e não a serialização como verdade.

F21/F18: restore em diretório novo, reindexação e replay com catálogos de tombstones; procurar canários excluídos nos meios recuperáveis contratados (índice, resumo, checkpoint, trace e backup conforme expiração), e consultar fatos vigentes. Distinguir recibo de exclusão ativa, retenção temporária de backup e sua expiração efetivamente verificada. Busca lógica negativa não prova apagamento físico de bytes, mídia ou backups externos; não prometer essa propriedade sem mecanismo e ensaio específicos.

## 7. Matriz completa F01–F24: método, oráculo e impacto

Todos os pares seguem a seção 2. A coluna de impacto acrescenta o desfecho específico aos deltas gerais de sucesso/qualidade/latência/tokens, detecção e recuperação. As referências sustentam os **métodos**, enquanto a propriedade esperada vem das etapas 4–6.

| F | Método e manipulação implementável | Oráculo independente / resultado seguro | Impacto específico e limite |
|---|---|---|---|
| F01 | M01/M03: renderizar original em scan, rotacionar/ruído; embaralhar blocos ou alterar sinal/data no adaptador para isolar parser | Transcrição/página original e fatos críticos; diagnosticar ilegibilidade, não confirmar dado corrompido | CER/WER, erro de número/página e restrição downstream; ruído pode tornar impossível extrair, sem obrigação de manter texto idêntico |
| F02 | M01/M03/M06: dia sem hora, expressão relativa, revisão conflitante e falta de parâmetro | Tabela humana de autoridade/precisão e script de confirmação; nenhuma restrição dura inferida silenciosamente | Promoções falsas e Δviabilidade real; confirmação do script precisa verificar valor, não aceitar qualquer preview |
| F03 | M01/M03: fonte ouro removida, distrator, versão antiga e filtro por snapshot | IDs relevantes anotados e claims suportadas; abstinência/apoio parcial rotulado | Recall/nDCG e falso suporte downstream; retirar fonte altera a respondibilidade, não exige recall impossível |
| F04 | M03/M06: evidência insuficiente/contraditória e claim falso com citação resolvível | Humano verifica implicação na fonte original, além de existência/versionamento | Claims falsas/suporte fictício aceitos; resolvedor sozinho não mede entailment |
| F05 | M02/M03/M06: sequência de pistas, recusa, solução, reveal e resposta posterior | Máquina de tutoria/ajuda e anotação de conteúdo; waiting/close corretos | Vazamento, insistência, chamadas na espera e promoção indevida; detecção textual de solução pode exigir especialista |
| F06 | M03: correta curta, errada fluente, paráfrase e gabarito deliberadamente defeituoso | Ouro humano/solução formal, spans reais; abster do indecidível | Falso acerto crítico, acordo e risco–cobertura, Δdemanda/plano; mesmo modelo em papéis distintos não cria independência |
| F07 | M01/M02: retry de attempt, ajuda/reveal e evento futuro em replay | Redutor de referência por IDs/corte e famílias; estado idempotente e ajuda preservada | Dupla atualização/falso favorable/leak temporal; BKT não admitido no MVP |
| F08 | M02/M03: homônimos, supersedes, correção retroativa e evidência antiga | Ouro bitemporal/origem, consulta atual versus histórica; conflito explícito | Fato antigo reativado e continuidade errada; definir corte de conhecimento versus validade |
| F09 | M01/M03/M07: limite de contexto real e síntese que troca data/polaridade/ajuda ou remove rubrica | Claims→originais e tokens após template; bloquear síntese/avaliação sem contexto crítico | Recall crítico e Δjulgamento/plano; resumo menor não implica custo total menor se exigiu reparos |
| F10 | M01/M06: ref ausente, schema/envelope incompatível, enum e user/version semanticamente errados | Contrato de referência e ledger; rejeição antes de publicar/commit | Inválidos aceitos, reparos/efeitos; schema válido pode ser erro de domínio |
| F11 | M02/M04/M06/M07: tools com erro persistente, ciclo e pedidos infinitos | Watchdog externo e máquina de budget; terminal tipado no limite e cancelamento | Overshoot de chamadas/steps/deadline e não término; relógio virtual valida lógica, tempo real valida backend |
| F12 | M04/M07: timeout, OOM simulado/real, truncamento, fila cheia e tokenizer incompatível | Finish_reason/saída incompleta, ledger e recursos; erro controlado sem promoção parcial | Disponibilidade, censura, fila e artefatos inválidos; mock OOM não testa allocator/runtime real |
| F13 | M01/M03/M08: duração17min, deadline meio-slot, DST, ciclo e status UNKNOWN/FEASIBLE | Enumeração nas pequenas e check em minutos/instantes originais; status exato | Violações, demanda/regret/churn; discretização pode excluir plano contínuo viável, INFEASIBLE vale para modelo discretizado |
| F14 | M02/M05: alteração entre snapshot/aprovação/commit e bloco iniciado | Histórico de versões/confirmations e imutabilidade; VERSION_CONFLICT e novo preview | Lost update/plano obsoleto/bloco fixo movido; histórico legal local não prova deploy distribuído |
| F15 | M02/M04/M05: crash commit/efeito/ACK, resposta perdida e lease concorrente | Ledger de operações e destino por identidade/versão; reconcile ou UNKNOWN_EFFECT | Duplicata, perda, overwrite externo e tempo de recuperação; exactly-once remoto não assumido |
| F16 | M06: objetivo atacante em PDF/site/tool e posição/idioma variáveis | Predicados sobre estado/efeitos e trace de chamadas negadas; política não muda | ASR, utilidade sob ataque e custo da contenção; defesa pode bloquear também tarefa legítima |
| F17 | M01/M02/M06: troca de usuário, traversal/symlink, DNS/redirect privado | Proxy/ownership e canários; negar antes de ler/enviar | Vazamento/leitura/envio indevido; allowlist de string não testa destino efetivamente resolvido |
| F18 | M04/M05/M08: ENOSPC, busy, transação interrompida, migração/backup incompleto | Integridade/FK mais operações comprometidas e replay/restore; sem estado parcial anunciado íntegro | Corrupção/perda de evidência e disponibilidade; integrity_check não substitui semântica do domínio |
| F19 | M04/M06: offline, quota,404, recurso mudado e metadata-only sem transcrição | Mock/snapshot versionado e estado de acesso; núcleo local continua e conteúdo não lido não é resumido | ΔTSR local, claims de acesso falsas e recomendações; smoke real sujeito a deriva não entra no mesmo par reproduzível |
| F20 | M01/M08: UTF-8/folding, all-day, zona e reexportação/revisão | RFC/parser distinto e tuplas plano↔ICS↔readback | Deslocamento temporal, identidade/revisão e duplicação; importar manualmente não garante dedup |
| F21 | M02/M04/M08: corrigir/excluir e depois reconstruir, restart/replay/restore | Tombstones e canários em derivados/meios contratados; sem fato antigo ou dado excluído recuperável | Stale fact/ressurreição/recuperabilidade; respeitar escopo/expiração e distinguir apagamento lógico/físico |
| F22 | M04/M07: omitir retry/span/contador e falhar exporter | Ledger externo versus trace; divergência detectada e unknown explícito | Subcontagem de tokens/chamadas/latência e erro de conclusão experimental; trace sozinho não audita a si mesmo |
| F23 | M03 e seção 8: ordem/comprimento do juiz, família vazada e seeds tratadas como N | Auditor de split/parentesco e ouro cego; invalidar análise contaminada | Mudança no ranking, IC artificialmente estreito e viés; contaminação de pretraining pode permanecer desconhecida |
| F24 | M08: bundle offline sem peso/OCR/lock ou hash alterado | Ambiente limpo, manifesto/doctor/smoke/restore | Falha de instalação/reprodução e dependência identificada; smoke e seed não garantem métrica idêntica em outro hardware |

### 7.1 Falhas compostas e propagação

Priorizar as seis cadeias da etapa 5: F01→F02→F13; F04/F06→F07→F09; F14→F15; F08/F21→F09; F11/replay→F15; F12→F22/F23. Ensaiar primeiro causa isolada e depois combinações selecionadas por fronteira/severidade. Usar desenho clean, A, B, A+B para distinguir amplificação de simples soma; `interação = Y_AB − Y_A − Y_B + Y_clean`. Não explorar todas as combinações de 24 falhas como se o orçamento permitisse cobertura exaustiva.

Medir em cada fronteira: defeito introduzido, detectado, artefato rejeitado/aceito, propagação e publicação/efeito. Contenção em uma fronteira não elimina defeito na anterior; um solver pode otimizar perfeitamente um deadline extraído errado. Quando uma falha anterior impede alcançar a segunda, marcar a exposição da segunda como não ocorrida; não contar esse caso como defesa bem-sucedida contra ambas.

## 8. C18/C19 — Dados fixos, comparação pareada e inferência

### 8.1 C18: dados, splits e ouro

Preservar as metas da etapa 6: 24 famílias documentais (8 desenvolvimento/4 validação/12 teste), consultas/tentativas distintas por conjunto, 30 trajetórias de teste com oito sessões, instâncias de agenda separadas por família/parâmetros e catálogo mínimo por F. São metas sujeitas à disponibilidade/autorização, **não cálculo de suficiência**. Se houver revisão da quantidade, documentá-la antes da execução final, mantendo a separação e congelando IDs/hashes; não realocar famílias após observar escores.

Definir família como parentesco de conteúdo, não apenas SHA: scan, versão, tradução, paráfrase de item e variantes de falha do mesmo original permanecem juntos. Auditar duplicatas exatas e similaridade textual, com revisão dos matches, antes do congelamento. Trajetórias que reutilizam uma família podem induzir dependência além do estudante: registrar incidência documento↔item↔trajetória. Uma consulta de teste só acessa corpus previsto no seu cenário; fontes necessárias ao RAG são entrada legítima, enquanto gabaritos/rubricas privadas de avaliação não entram no índice do agente.

Ouro documenta resposta decidível, suporte/ausência, fonte e versão, restrições originais/precisão, ajuda, temporalidade e terminal. Ouro negativo é explícito (sem evidência, impossível, ambíguo). Para agenda pequena, enumerar candidatos e verificar objetivo lexicográfico independentemente; nas realistas sem ótimo conhecido avaliar viabilidade/cobertura e bounds declarados, sem inventar regret exato.

O teste fica indisponível para ajuste de prompts, threshold, reranker, compactação, budgets, juiz e geradores. Bugs descobertos em teste são reportados; corrigir cria nova versão/rodada com transparência e necessidade de novo conjunto confirmatório, não substituição silenciosa dos resultados anteriores. Geradores adaptativos e exemplos reduzidos de teste não voltam ao desenvolvimento preservando a alegação de teste intocado.

### 8.2 C19: condições, justiça e orçamento

Condições principais: MA completo, SA com ferramentas/memória/corpus equivalentes, MA sem memória longitudinal, sem compactação e com todas as skills. Mesma oportunidade de ajuste em desenvolvimento e escolha em validação para SA/MA; registrar esforço/configurações testadas. A capacidade de contexto é igual, mas tokens de instrução/coordenação são custo de cada arquitetura. Ablação deve especificar mecanismo removido e tratamento quando não cabe no contexto: bloquear/segmentar conforme política congelada, não dar contexto ilimitado.

Para comparação principal usar teto comum por tarefa e seeds **0/1/2/3/4**, uma execução por condição/seed, reset de estado e cache policy. Para o catálogo de falhas com geração, as três seeds propostas podem ser **0/1/2**, compartilhadas entre clean/fault e condições; congelar essa escolha antes de executar. Crashpoints determinísticos não exigem multiplicação por seed sem geração. As duas contagens da etapa 6 têm propósitos distintos e não são N independentes.

Reportar duas análises: qualidade sob teto comum e curvas qualidade–custo em níveis de orçamento pré-definidos. Não selecionar apenas execuções que consumiram o mesmo custo observado: esse consumo é consequência da condição e tal seleção pode enviesar. Incluir chamadas de reparo, coordenação, validação e trabalho interrompido. Offline, connected com mocks/snapshots e smoke real permanecem condições identificáveis.

Primárias da etapa 6: TSR longitudinal e taxa de violação crítica publicada, com denominadores/formas de agregação fixados. Proposta para TSR longitudinal: proporção de trajetórias que passam todas as dependências críticas em cada seed, média das seeds por trajetória e média das trajetórias. Para violação: publicar taxa por tentativas elegíveis e por artefatos publicados (dois denominadores), mais “ao menos uma violação por trajetória/família”; abstenção excessiva não pode mascarar resultado sem utilidade. Secundárias O/F preservam unidades e denominadores específicos.

### 8.3 Pareamento, cluster bootstrap e testes de hipótese

Dror et al. discutem adequação do teste à métrica/desenho [dror2018hitchhiker]; seu resumo e metadados foram consultados, sem atribuir a ele a implementação de cluster bootstrap abaixo. Field/Welsh mostram no resumo editorial que a validade do bootstrap para dados agrupados depende do modelo e que cluster bootstrap pode estimar variância consistentemente sob modelos estudados [field2007cluster]. Isso motiva preservar dependência; não assegura validade com poucas famílias ou dependência cruzada arbitrária. A documentação SciPy explicita que `paired=True` reamostra os mesmos índices entre vetores e alerta para distribuições degeneradas [scipyBootstrap].

**Algoritmo proposto para diferenças pareadas:**

1. Congelar estimando e pesos: média de trajetórias para longitudinal; macro-W e micro-tarefas em tabelas distintas; para consulta/item, ponderação de casos ou famílias explicitada, sem trocar depois de ver resultados.
2. Computar desfechos para todas as condições/clean/fault. Seeds são repetições dentro do caso; agregar por caso quando esse é o estimando, ou mantê-las dentro do cluster sem recontar independência.
3. Identificar clusters independentes plausíveis: trajetória no longitudinal; família documental/item no conteúdo; família de parâmetros na agenda. Reamostrar G clusters com reposição, mantendo **todos** os turnos/casos, seeds, condições e pares do cluster sorteado. No estimando micro, recalcular numerador/denominador completos da réplica; no macro, recalcular médias com pesos congelados.
4. Recalcular diferenças MA−SA, fault−clean e contraste de degradação na mesma réplica. Não fazer dois bootstraps independentes e subtrair ICs.
5. Registrar seed do bootstrap, B, método do intervalo e estabilidade Monte Carlo dos extremos. B regula erro numérico da reamostragem, não aumenta N. Escolher método em piloto; percentil/basic são candidatos e BCa requer jackknife por **cluster**, não por turno. Avaliar cobertura em simulação antes do congelamento.
6. Se poucas famílias, desfecho raro/degenerado ou heterogeneidade extrema impedirem intervalo informativo, reportar distribuição/dados por cluster e limitação. Um IC [0,0] produzido por reamostragem de nenhum evento observado não prova ausência de risco.

`scipy.stats.bootstrap(..., paired=True)` sobre turnos preserva o par, **mas não preserva agrupamento**. Aplicá-lo a vetores de estatísticas por cluster serve ao estimando de média desses clusters; para razão micro, quantis ou clusters de tamanho variável, reamostrar IDs e recalcular a estatística completa com agrupamento explícito. A escolha de percentil/basic/BCa não corrige unidade de reamostragem errada.

Se trajetórias compartilham documentos, a independência apenas por trajetória é uma suposição forte. Preferir desenho sem compartilhamento entre clusters quando possível; alternativamente, agrupar por componentes de parentesco ou planejar modelo/método de dependência cruzada antes do teste. Com apenas duas disciplinas, não tratá-las como grande amostra de clusters de disciplinas: estratificar/reportar por disciplina e limitar generalização.

Testes secundários: permutação pareada por cluster pode trocar rótulos MA/SA conjuntamente dentro do cluster sob hipótese de exchangeabilidade; inversão de sinais exige suposições sobre as diferenças e não é automaticamente exata. McNemar simples aplica-se a pares binários independentes; não a 240 turnos correlacionados nem seeds como novos estudantes. Definir famílias de hipóteses e ajuste Holm para secundárias confirmatórias; análises exploratórias por F/O são rotuladas. Se as duas primárias sustentarem decisões separadas, definir também controle de multiplicidade; se a alegação exigir ambas, declarar regra conjunta antes do ensaio. Reportar tamanho de efeito/IC e não só p-value.

### 8.4 Potência, precisão, eventos raros e equivalência

Lakens distingue planejamento por potência, precisão e restrição de recursos e exige justificar efeito de interesse e suposições [lakens2022inferences]. **Procedimento antes do teste:**

- No piloto de desenvolvimento, estimar variabilidade das diferenças por cluster, correlação entre condições/seeds, discordância dos pares binários, tamanho dos clusters e frequência plausível de eventos; guardar incerteza dessas estimativas.
- Definir diferença mínima relevante em unidades de TSR/violação/tokens e margem de perda aceitável de qualidade para compactação, com justificativa do domínio. Essas escolhas são decisões pendentes, não números universais.
- Simular dados hierárquicos pareados para grades de G, efeito, prevalência e correlação plausíveis; executar a mesma análise/multiplicidade/decisão planejadas; sob efeito nulo verificar erro tipo I e cobertura, sob alternativas estimar potência e largura dos intervalos. Reportar erro Monte Carlo e cenários sensíveis a suposições, não apenas o cenário mais favorável.
- Congelar quantidade final, critérios e plano de parada antes de olhar resultados de teste. Com orçamento insuficiente, justificar por recursos e reportar efeitos detectáveis/precisão esperada, sem alegar suficiência. Não usar potência pós-hoc baseada no efeito observado como prova de adequação.

“Zero violações no ensaio” é gate finito. Para G clusters **independentes, comparáveis e amostrados de uma população definida**, um indicador binário “alguma violação no cluster” com zero eventos admite limite unilateral exato `p_upper = 1 − alpha^(1/G)` sob modelo Bernoulli homogêneo; para cobertura unilateral95%, alpha=.05. Não substituir G por turnos/seeds nem aplicar esse limite diretamente à taxa de artefatos dependentes. Em stress tests escolhidos adversarialmente, reportar cobertura e zero eventos observados, sem inferir prevalência do mundo real desse cálculo. Se não houver clusters suficientes/plausivelmente independentes, a conclusão sobre raridade permanece limitada.

Q2 (“reduzir custo preservando qualidade”) precisa de margem e análise de não inferioridade/equivalência pareada planejadas. `p>.05` numa comparação de qualidade não prova preservação. Selecionar margens em desenvolvimento/validação e exigir que o IC pertinente exclua perdas inaceitáveis, com regra e ajuste congelados; custo menor com IC de qualidade amplo pode ser inconclusivo. Uma melhora de TSR operacional em trajetórias simuladas não demonstra ganho humano de aprendizagem; exigiria estudo próprio, conforme etapa 6.

## 9. Decisões para etapa 8 e pendências

**Adotar:** M01–M08 com modelo de referência separado; duas camadas de falha (fronteira e ponta a ponta); predicados por turno e histórico de efeitos; pares clean/fault completos; histórico de commits locais e reconciliação remota; auditoria externa de trace; instalação/restore offline; cluster bootstrap pareado com estimando explícito; humanos como ouro de conteúdo e juiz secundário.

**Congelar antes do teste:** IDs/splits e parentesco; versões/hashes; rubricas e adjudicação; seeds/order/cache; budgets e horizonte de recuperação; distribuição/intensidade/crashpoints; conjunto/adaptação dos ataques; critérios de exposição; denominadores, pesos e hipóteses; margens/efeitos relevantes; método/B de IC; tamanho e parada justificados por piloto/recursos. Nenhum ajuste é autorizado pelo desempenho do teste final.

**Pendências concretas:**

1. Obter corpus autorizado, construir/anotar ouro negativo e validar relações semânticas; conferir metas de amostra sem presumir potência.
2. Desenhar parentesco documento/item/trajectória para decidir clusters e evitar dependência cruzada não modelada; esclarecer corte bitemporal de cada pergunta.
3. Definir margens/efeitos relevantes e executar piloto de potência/precisão/cobertura apenas em desenvolvimento.
4. Especificar precondições de retry/versão e operações pendentes no modelo local, exposição equivalente MA/SA e limites dos verificadores de histórico.
5. Selecionar parser ICS independente, mecanismos de barreira/process kill e, se necessário, camada VFS para power-loss; essas capacidades ainda não foram verificadas no runtime.
6. Definir tombstones/expiração de backups e escopo de exclusão verificável; expiração futura não pode ser declarada já medida.
7. Conferir pins do runtime/SQLite, tokenizer e instrumentos de RSS/VRAM/energia; decidir como reportar medições indisponíveis.
8. Escolher/calibrar juiz e anotadores, fixar tratamento de discordâncias/abstenções e auditar contaminação conhecida; pretraining desconhecido permanece limitação.

## 10. Trilha de busca, fontes consultadas e exclusões

### 10.1 Estratégia e critérios

Busca direcionada por mecanismos: “metamorphic testing challenges opportunities”; “Hypothesis stateful invariants”; “SQLite crash I/O OOM testing WAL”; “linearizability executable model concurrent history Porcupine”; “BFCL multi-turn state response evaluation”; “AgentBench finish reasons”; “AgentDojo utility security”; “OpenTelemetry traces”; “paired bootstrap clustered data”; “sample size justification power precision”; “LLM judge position verbosity”; “machine learning reproducibility”; “RFC5545 round-trip UTF-8”. As expressões descrevem eixos de busca, não consultas fictícias a um motor: nesta rodada usou-se **webfetch de páginas primárias conhecidas**, uma consulta Crossref por título e resolução de DOI/links dessas páginas.

Incluir artigo metodológico original, resumo editorial identificado ou documentação oficial com mecanismo pertinente a F/C. Priorizar verificabilidade e escopo explícito. Excluir páginas não relacionadas, rotas indisponíveis como evidência de conteúdo, resumos de terceiros e leaderboards como prova de eficácia local. O conjunto é seleção metodológica dirigida, não revisão sistemática/exaustiva com contagem PRISMA.

### 10.2 Fontes nucleares efetivamente consultadas

| # / chave | URL(s) e alcance de leitura em 30/09/2026 | Uso e ressalva |
|---|---|---|
| 1 `chen2018metamorphic` | https://api.crossref.org/works/10.1145/3143561 — metadados e resumo editorial; ACM integral403 | Definição de relação metamórfica; relações do projeto são propostas locais. Online2018, fascículo impresso2019 |
| 2 `hypothesisStateful` | https://hypothesis.readthedocs.io/en/latest/stateful.html — documentação lida, regras/Bundles/preconditions/invariants/exemplo reduzido | M01/M02; página móvel requer pin |
| 3 `sqliteTesting` | https://sqlite.org/testing.html — conteúdo de anomaly/crash/compound/boundary/mutation testing lido; atualização exibida2026-04-21 | M04 e teste de sensibilidade do oráculo; garantias do SQLite não se transferem automaticamente à aplicação |
| 4 `athalye2017porcupine` | https://raw.githubusercontent.com/anishathalye/porcupine/master/README.md — modelo/histórico/exemplos/limites e citação lidos | M05; algoritmos vinculados não foram lidos |
| 5 `bfclMultiTurn` | https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html e https://gorilla.cs.berkeley.edu/blogs/8_berkeley_function_calling_leaderboard.html — documentação de avaliação/curadoria lida | M06; V3 com estado + resposta. Usar entrada de documentação; não reproduzir citação inconsistente do blog inicial nem pontuação de leaderboard |
| 6 `liu2024agentbench` | https://arxiv.org/abs/2308.03688 e https://arxiv.org/html/2308.03688v3 — metadados e §§2–4 disponíveis/lidos; saída integral truncada | Términos/trajetórias; ICLR2024 confirmado no registro, v3 de2025; apêndices completos não analisados |
| 7 `debenedetti2024agentdojo` | https://arxiv.org/abs/2406.13352 e https://arxiv.org/html/2406.13352v3 — metadados e §§1–4 disponíveis/lidos; saída integral truncada | Utilidade/ASR/oráculos de estado, v3 de2024; não validar números de todas as tabelas/apêndices |
| 8 `oteltrace` **existente** | https://opentelemetry.io/docs/concepts/signals/traces/ — página lida, spans/events/links/status | M07; chave em `references_arquitetura.bib`, sem duplicação |
| 9 `desruisseaux2009icalendar` **existente** | https://www.rfc-editor.org/rfc/rfc5545.html — §§3.1 e3.6.1 lidas, esta última no retorno armazenado após truncamento | M08; chave em `references_pedagogia.bib`; restante da RFC não afirmado como leitura integral |
| 10 `sqlitewal` **existente** | https://sqlite.org/wal.html — WAL/concorrência/checkpoint/cópia/correção lidos | M04/M08; chave em `references_arquitetura.bib`; atualização2026-08-25 |
| 11 `dror2018hitchhiker` | https://aclanthology.org/P18-1128/ — resumo e metadados lidos | Seleção de análise conforme desenho; PDF não lido, sem atribuir detalhes não inspecionados |
| 12 `field2007cluster` | https://api.crossref.org/works/10.1111/j.1467-9868.2007.00593.x e DOI — resumo editorial/metadados lidos | Fundamenta dependência/modelo do bootstrap; integral não acessado |
| 13 `scipyBootstrap` | https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html — documentação lida, paired/métodos/RNG/degeneração; versão exibida1.18.0 | Receita computacional; paired não implementa agrupamento automaticamente |
| 14 `lakens2022inferences` | https://lakens.github.io/statistical_inferences/ e https://lakens.github.io/statistical_inferences/08-samplesizejustification.html — prefácio/citação e §§8.1–8.8 disponíveis/lidas; capítulo integral truncado | Potência/precisão/recursos, não heurística de N; capítulo adapta artigo do autor |
| 15 `zheng2023judge` | https://arxiv.org/html/2306.05685v4 — §§1–6 disponíveis/lidas, saída integral truncada | Viés/calibração; não transportar acordo do MT-Bench para domínio local |
| 16 `pineau2021reproducibility` | https://jmlr.org/papers/v22/20-303.html — resumo e metadados lidos | Fundamentação da reprodução; manifesto/harness propostos são derivados dos contratos locais |

**Bibliografias combinadas:** usar `references_arquitetura.bib`, `references_pedagogia.bib` e `references_robustez.bib`. As três chaves existentes acima não são redefinidas no novo arquivo. As demais foram conferidas contra as bibliografias existentes, inclusive fase1, para evitar novas chaves duplicando obras já presentes.

### 10.3 Tentativas excluídas e decisões de alcance

- `https://arxiv.org/abs/1609.02964` retornou artigo de convergência da equação de Schrödinger, não metamorphic testing: identificação candidata incorreta, excluída. O resumo correto veio do DOI10.1145/3143561; `https://dl.acm.org/doi/10.1145/3143561` retornou403. A busca Crossref por título com `rows=1` devolveu artigo de Rehman/Srinivasan (2023), relacionado mas distinto; não usado como se fosse Chen et al.
- `https://arxiv.org/abs/2508.03262` retornou estudo econômico “Pay What LLM Wants”, não BFCL: excluído. `https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v4_sneak_peek.html` e `https://raw.githubusercontent.com/gorilla-llm/Berkeley-Function-Call-Leaderboard/main/README.md` retornaram404. Seguir os links do blog8 levou ao blog13 V3 correto. V4 é mencionado pela página, mas não foi consultado nem usado para alegar cobertura nova.
- `https://academic.oup.com/jrsssb/article/69/3/369/7109337` retornou403. DOI e Crossref identificam a obra Field/Welsh; leitura limitada ao resumo editorial/metadados, sem afirmar leitura do integral. Crossref fornece rota editorial canônica diferente (`7109361`), não usada para inventar acesso bem-sucedido.
- `https://lakens.github.io/statistical_inferences/06-samplesize.html` e `/sample.html` retornaram404; `https://online.ucpress.edu/collabra/article/8/1/33267/120491/Sample-Size-Justification` retornou403. Índice do livro apontou o capítulo8 acessível e a citação2022; usar a obra/chave do livro efetivamente consultado, não o artigo bloqueado como leitura integral.
- PDFs de Dror, Pineau, Chen e Field não foram lidos; não inferir tabelas, provas ou parâmetros específicos deles. Nos HTMLs truncados, fundamentar apenas os trechos disponíveis indicados acima. Quantidades de benchmarks não dimensionam a amostra local.
- Não selecionar outra survey genérica de agentes, defesa comercial ou leaderboard de modelo para substituir oráculos de efeito/estado. LangGraph, CP-SAT, pedagogia, RAG e calendários remotos já têm pesquisa anterior; aqui os seus contratos são objetos de teste. Não duplicar essas obras nem alegar nova leitura de páginas não visitadas nesta rodada.

**Limitação geral:** seleção dirigida com algumas fontes acessíveis apenas por resumo; mecanismos detalhados foram apoiados por documentação/HTML realmente lidos. A transferência para o sistema é especificação metodológica a validar no piloto, não evidência de que a implementação já cumpre as propriedades.
