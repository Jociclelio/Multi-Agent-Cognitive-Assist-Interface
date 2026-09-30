# Pesquisa 03a — Arquitetura local, ingestão, RAG e infraestrutura

**Data da consulta:** 30/09/2026. **Escopo:** C01–C05, C13–C17 e C20 do documento `02_componentes_e_requisitos.md`, interpretados em conjunto com `01_esqueleto_conceitual.md`. Esta é uma especificação metodológica para seleção e implementação futura; não representa benchmark executado nem eficácia educacional demonstrada.

**Resolução posterior:** mapa4 §§11/15 é normativo. No commit, após ownership/permissão, deduplicar operation_id+digest antes de checar expected_version de operação nova. Snapshot é materializado com domain_revision por usuário. Referências a decisões ainda abertas abaixo descrevem o momento desta pesquisa; stack/contratos concretos estão no mapa4, testes no mapa8.

## 1. Método, evidência e critérios de seleção

A pesquisa foi coordenada em quatro frentes dependentes: (1) identidade/runtime do modelo; (2) representação documental e recuperação; (3) contratos, grafo e fronteiras de ferramentas; (4) durabilidade, observabilidade e reprodução. Os resultados foram reconciliados pelos IDs permanentes, sobretudo onde uma escolha altera outra: tokenizer afeta chunking; runtime afeta JSON; retomada afeta idempotência; armazenamento afeta isolamento e filtros.

Foram lidos os dois documentos locais solicitados e consultadas fontes remotas efetivamente por `webfetch`: documentação dos mantenedores, model cards do publicador, página primária de artigo e metadados Crossref. Foram explorados **18 núcleos bibliográficos**, com consultas auxiliares identificadas na seção 5. Não houve execução de modelos, extração de PDFs do estudante, instalação de dependências ou medição de hardware.

### Convenções de evidência

- **Publicado (P):** a fonte consultada declara o comportamento, recurso ou resultado. Em documentação de software é um contrato documentado; em model card é declaração do fornecedor, não reprodução independente.
- **Proposto (H):** escolha de engenharia ou hipótese a testar neste projeto. Todos os budgets, gates, tamanhos de amostra e parâmetros experimentais abaixo, salvo atribuição explícita, são H.
- **Pendente (L):** não foi verificado ou depende de execução local, acesso adicional ou validação humana.
- **Verificada** significa que conteúdo legível da página ou metadado foi recuperado e inspecionado. Não significa que binários/pesos foram baixados, que resultados foram reproduzidos ou que links internos foram todos abertos.

Seleção: priorizar fonte primária e comportamento operacional verificável; exigir alternativa, custo, limite e teste de seleção; evitar transportar resultados de inglês/outro hardware para português/local. Documentação sem data editorial explícita recebe `s.d.` e data de acesso, inclusive no BibTeX; o ano de consulta não é inventado como ano de publicação. A versão móvel `main/latest` consultada exige snapshot no futuro manifesto. Ajustes usam desenvolvimento/validação separados por família documental, antes de congelar a configuração; teste final não escolhe parâmetros.

## 2. Decisão arquitetural integrada

Núcleo proposto: cinco papéis lógicos em um `StateGraph`, servidor local único de geração, ingestão estruturada com originais preservados, índice lexical e índice denso independentes, fusão por ranks seguida de reranking opcional, serviço determinístico de autorização/efeitos e SQLite como autoridade transacional. Índices e resumos são derivados reconstruíveis. MCP adapta fronteiras de ferramentas; comunicação interna usa contratos tipados e referências a snapshots. Traces ficam locais.

```text
arquivo original → hash/manifesto → extração/OCR → blocos com proveniência
                → fatos candidatos → validação/confirmação → ontologia versionada
pergunta + snapshot → filtros → lexical ∪ denso → RRF → reranker → pacote de fontes
                   → Tutor → validação de citações → resposta ou abstinência
grafo → proposta de ferramenta → política → efeito idempotente → reconciliação
      ↘ checkpoint / eventos de domínio / outbox / trace local
```

Essa composição é H, não uma arquitetura prescrita por um artigo. A recuperação documental não deve misturar perfil do estudante com documentos por simples similaridade; as duas recuperações devolvem pacotes distintos, com origem e orçamento separados.

## 3. Metodologia por requisito

### C01 — Inferência local identificável

**P — identidade encontrada.** O publicador Prism ML disponibiliza `prism-ml/Ternary-Bonsai-2-27B-gguf`, denominado **Bonsai 2 27B — GGUF** no model card (`bonsai2`). A API do Hub retornou revisão `b072e1d3b35a0a630cece372c2127528e0994386`, criação em 16/09/2026 e última modificação em 25/09/2026. O card declara Apache 2.0, derivação de Qwen3.8-27B, janela de 262.144 tokens e packings ternários com transformações Hadamard. Esses dados identificam um candidato concreto; a proposta original não tinha identificador suficiente para provar que era exatamente esse artefato que pretendia usar.

| Arquivo publicado | Bytes pela API | SHA-256 LFS publicado |
|---|---:|---|
| `Ternary-Bonsai-2-27B-PTQ1_0.gguf` | 5.946.648.928 | `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3` |
| `Ternary-Bonsai-2-27B-PQ2_0.gguf` | 7.206.168.928 | `3907dc1658db1f78a9826bf8d5bcb8dc65db0d466388937af57f2294fae62ec1` |

São hashes **publicados**, ainda não recalculados sobre download local. Tamanho do arquivo não equivale a RSS/VRAM necessária. O card declara 27,36B parâmetros totais incluindo visão; a API agrega aproximadamente 26,896B para GGUF textual e mostra `architecture=qwen35`. Registrar ambos, com escopo, sem converter a tag interna em afirmação de que o modelo-base é outro. O tokenizer e o template devem ser extraídos do próprio GGUF selecionado: a API expõe template, BOS `<|endoftext|>` e EOS `<|im_end|>`, mas isso não é auditoria completa do vocabulário/tokenizer.

**P — runtime e limites.** `bonsai2` e `bonsaidemo` exigem o fork `PrismML-Eng/llama.cpp`; stock llama.cpp não executa corretamente os packings. O demo documenta release fixada `prism-b10743-adfffbe`; isso é uma candidata a investigar, não uma release testada aqui. O servidor upstream (`llamasrv`) documenta JSON condicionado por schema, API de chat, slots e métricas, mas **não comprova** paridade desses recursos na release do fork. O template do Hub contém chamadas de ferramenta em marcação XML-like; a conversão em `tool_calls` JSON é responsabilidade do parser/runtime, não prova de geração JSON nativa perfeita.

O card relata BFCL v3 de 74,92 e média de 84,78 em 14 benchmarks, em thinking mode. Não são evidência de desempenho em tutoria portuguesa. `KNOWN_ISSUES.md`, consultado com data de checagem 23/09/2026, registra tool calls malformadas/loops, erros com argumentos vazios, restrições de mensagem system e problemas de CPU/backend. O README do demo atualizado em 25/09 diverge das notas de 23/09 quanto à disponibilidade de MLX/visão: não consolidar as duas versões como se fossem o mesmo estado testado.

**H — configuração inicial.** Um processo textual, loopback, um slot, fila externa de até quatro requisições, sem visão no núcleo. Comparar PTQ1_0/PQ2_0 no hardware real; contexto inicial de 32.768, reserva máxima de saída de 16.384 e `reasoning_effort=medium`. Esses limites são candidatos: se memória/latência não comportarem a reserva, medir non-thinking e contextos menores; não cortar saída para 256 tokens e classificar pensamento incompleto como resposta ruim sem diagnóstico. Separar tokens de entrada, raciocínio quando exposto e resposta final. Partir dos samplers publicados: thinking `temperature=1.0`, `top_p=.95`, `top_k=20`, `min_p=.05`; non-thinking `.7/.80/20/0`, com penalidades do card. Avaliar temperatura baixa para contratos como ablação, não como recomendação do publicador.

**Seleção e alternativa.** Rodar conjunto de desenvolvimento em português com perguntas com/sem fontes, ambiguidade, ferramentas válidas/inválidas e interrupções; registrar JSON parseável, schema, intenção correta, efeito correto, truncamento, p50/p95, prefill/decode, RSS/VRAM e seeds. Rejeitar qualquer efeito não autorizado mesmo com JSON válido. Comparar com outro modelo local de card/licença identificados apenas em rodada futura; Bonsai 8B antigo não pode ser renomeado “Bonsai 2”. CPU é alternativa de backend documentada, com latência a medir; MLX só tem pertinência se houver Apple Silicon. **L:** hardware, licença integral/NOTICE, tokenizer integral, commit/binário do fork e suporte real a schema permanecem gates de adoção.

### C02 — Ingestão, OCR e proveniência

**P.** `docling` define `DoclingDocument` tipado em Pydantic com textos, tabelas, figuras, hierarquia, ordem no `body`, furniture, bounding boxes quando disponíveis e proveniência. Isso sustenta uma representação intermediária, não fidelidade garantida da extração. `ocrpdf` documenta seleção explícita de idioma, rotação, deskew e sidecar; sidecar **omite páginas que já tinham texto e páginas não OCRizadas**. Tesseract não detecta automaticamente idioma nessa configuração. Processamento pode rasterizar/perder qualidade; assinaturas digitais não são preservadas ao acrescentar OCR.

**H — pipeline.** (1) arquivar bytes originais; (2) calcular SHA-256, MIME real e tamanho; (3) extrair por página com Docling; (4) diagnosticar páginas vazias, caracteres substitutos, colunas/tabelas fora de ordem e discrepância entre imagem e texto; (5) OCR apenas páginas diagnosticadas, idioma `por` ou `por+eng` quando confirmado, mantendo derivado separado; (6) reextrair o documento completo, não somente sidecar; (7) persistir blocos com `doc_id`, `version_id`, página física 1-based, rótulo impresso separado, seção, bbox, ordem, texto, método, versões e diagnóstico; (8) construir chunks referenciando todos os blocos de origem.

Propor renderização a 300 DPI como ponto experimental, não garantia do OCRmyPDF. Não inferir legibilidade só de “há texto”: OCR prévio pode estar errado. Equações e tabelas mantêm estrutura/imagem original; tabela linearizada repete cabeçalhos e mapeia células. Datas/números críticos exigem cotejo humano quando OCR incerto. Ilegível vira pendência localizada, nunca texto completado pelo LLM.

**Alternativas/custo/seleção.** Extração simples com Poppler `pdftotext` é alternativa indicada no cookbook para texto completo e pode bastar para PDFs digitais simples, mas esta pesquisa não auditou sua documentação/API. OCR integrado ao Docling reduz etapas, mas motores, pesos e idioma precisam de lock próprio; OCRmyPDF fornece derivado PDF pesquisável e diagnóstico operacional com custo adicional. Comparar páginas digitais, scans portugueses/ingleses, duas colunas e tabelas com ouro humano: CER/WER quando aplicáveis, exatidão de números/datas, ordem e associação página/bloco. Aprovar somente se todas as citações do conjunto de integração resolvem à versão e página; falhas de extração podem existir, desde que declaradas.

### C03 — Ontologia acadêmica e autoridade

**P versus H.** `docling` sustenta estrutura/proveniência e `pydstrict` sustenta validação de tipos. Nenhuma das fontes consultadas valida uma ontologia educacional ou uma regra universal de autoridade de prazos. A autoridade do PDD confirmado vem dos documentos locais de requisitos; o esquema a seguir é H.

Entidades: `Disciplina`, `Topico`, `PreRequisito`, `Avaliacao`, `Recurso`, `FatoCandidato`, `Confirmacao` e `Conflito`. Usar IDs imutáveis; rótulos e aliases português/inglês são campos corrigíveis. Relações de pré-requisito são orientadas e passam por detecção de ciclo; ambiguidade não é resolvida por fusão automática de títulos parecidos. Identidade documental é diferente de hash: versões diferentes da mesma disciplina mantêm vínculo, bytes iguais deduplicam armazenamento.

Datas guardam expressão original, data ou datetime normalizado, timezone IANA quando aplicável, precisão, `source_ref`, status e justificativa. Prazo só com dia não recebe horário 23:59 silenciosamente. Timezone inicial `America/Sao_Paulo` depende de confirmação, não do idioma. Confiança começa categórica (`extraido`, `ambiguo`, `confirmado`, `rejeitado`), sem probabilidades calibradas inventadas. Separar data da avaliação, entrega e publicação. Fonte mais recente gera candidato de mudança; conflito preserva duas afirmações e exige reconciliação. Correção cria nova versão e evento, mantendo origem consultável.

**Alternativas e seleção.** Tabelas relacionais + JSON validado são preferidas pela simplicidade local; RDF/OWL e grafo de conhecimento são extensões com custo de vocabulário/consulta, sem vantagem demonstrada aqui. Validar gold de tópicos/aliases, ciclo, datas relativas, mudança de versão e PDD versus sugestão externa. Gates: nenhuma restrição oficial sem origem/confirmação; nenhum conflito apagado por overwrite. A granularidade de tópico deve ser decidida com anotadores e usada igualmente no baseline.

### C04 — Recuperação híbrida, RRF, reranking e abstinência

**P.** `m3` (página arXiv/abstract, não leitura integral) descreve dense/sparse/multi-vector, mais de 100 idiomas e entradas até 8.192 tokens. Isso motiva candidato multilingual, não comprova qualidade de português no corpus. `bgerank` documenta `BAAI/bge-reranker-v2-m3` multilingual, query+passage, logits e sigmoid opcional, Apache 2.0; o exemplo Transformers trunca em 512 tokens. Sigmoid não é probabilidade calibrada de sustentação. `qdranthyb` documenta prefetch/fusão e DBSF: RRF padrão `k=2`, ranks zero-based, parametrização desde v1.16 e pesos desde v1.17. Não confundir defaults do banco com parâmetro universal da literatura. `rrf09` teve metadados confirmados no Crossref, mas o PDF devolveu bytes não legíveis nesta consulta; fórmula e implementação usadas aqui são sustentadas pela documentação Qdrant, não por leitura integral do artigo.

**H — estratégia reproduzível.**

1. Fixar snapshot de corpus e filtros `user_id`, disciplina, versão ativa e permissões **antes** de cada busca; revalidar na hidratação. Versões antigas só entram quando pedidas ou para explicar conflito. Bibliotecário faz memória pessoal em consulta separada.
2. Chunking por seção/bloco, com alvo de 384 tokens e overlap até 64 apenas quando necessário para continuidade, comparando 256/384/512. Usar tokenizer do embedding para indexação; depois contar pacote com tokenizer Bonsai. Guardar offsets e cabeçalhos como contexto derivado, sem atribuí-los à página errada.
3. Lexical BM25 local e denso BGE-M3, cada um top-40; união/deduplicação por chunk_id. Preservar símbolos, códigos de disciplinas, termos técnicos e aliases. BM25 não equivale ao sparse aprendido BGE-M3: tratá-los como alternativas distintas.
4. Fusor explícito `score(d)=Σ 1/(60+rank_i(d))`, rank começando em **1**, ausente contribuindo zero, pesos iguais, empate por ID. `60` é H nesta pesquisa, sem alegar confirmação no PDF. Se usar implementação Qdrant zero-based, implementar conversão/offset equivalente e conferir fixture; passar `k=60` cegamente não produz a mesma fórmula 1-based. Ranks e limites ficam no trace.
5. Rerank dos 40 primeiros com `bge-reranker-v2-m3`, inicialmente pares até 512 tokens contados com tokenizer do reranker; registrar truncamentos. Tabelas/chunks longos podem exigir janelas, cujo agregado também precisa de validação. Selecionar até seis chunks, expandindo vizinhos somente se couberem e mantendo origem distinta.
6. Budget inicial de 4.096 tokens de evidências Bonsai, sujeito à reserva C01; não preencher à força com fontes irrelevantes. Pacote leva citação `[doc_id@version:página:bloco]`, trecho e diagnóstico. URI local resolve original e página; fragmento `#page` de leitor PDF é conveniência, não prova de existência.
7. Resposta separa afirmações apoiadas de explicação adicional; validador verifica existência, versão, página e trecho. Apoio semântico requer ouro humano/amostragem; não se reduz a checar sintaxe. Sem fonte suficiente, abster da afirmação documental e pedir material/esclarecimento. Limiar de reranker só será escolhido com curva precisão–cobertura em validação.

**Alternativas/custos.** BM25-only custa pouco e recupera identificadores; dense-only ajuda paráfrases e tradução, mas pode perder literais. BGE-M3 sparse+dense evita outro encoder, porém acrescenta índice aprendido; multi-vector aumenta armazenamento/custo. RRF não requer normalização de scores, mas descarta suas magnitudes. DBSF é alternativa documentada, sensível à amostra top-k/outliers. Reranker pode melhorar ordenação, mas não recupera item ausente da união; LLM reranking usa geração compartilhada e pode aumentar custo/variância. Comparar sem reranking antes de comprometer memória GPU com ele.

**Seleção.** Ouro de consulta→bloco/página em português, inglês técnico e consultas cruzadas; incluir códigos, OCR ruidoso, versões conflitantes e perguntas sem resposta. Medir recall@40 antes de rerank, MRR/nDCG@6 após, precisão de citação, sustentação por afirmação, abstinência precisão/cobertura e p95/RSS/VRAM. Medir também recall ANN contra busca exata se houver índice aproximado. Escolher a menor configuração que preserve qualidade em validação; manter ablações lexical, dense, RRF e RRF+rerank com mesmos dados/budget. Não declarar superioridade antes desse ensaio.

### C05 — Curadoria conectada e acesso real ao conteúdo

**P.** `ytcaptions` distingue obtenção de uma faixa de legenda de mera consulta a um vídeo: download exige autorização e permissão para editar o vídeo, custa 200 unidades e pode responder 403/404. Portanto, a API oficial não é um mecanismo geral de leitura de transcrições de qualquer vídeo público. Tradução via `tlang` é tradução automática, não legenda original. `mcpsec` fundamenta riscos de SSRF/redirects; transpor proteção de URL para fetch de recursos é H.

**H.** Conector opcional retorna `ResourceCandidate` com URL realmente encontrada, URL final, título, autor/canal quando disponível, idioma, tipo, licença se identificada, data de acesso, evidência de nível e estados `metadata_only`, `text_read`, `transcript_read`, `unavailable`. “Acessível” distingue fetch HTTP, conteúdo legível e acessibilidade pedagógica/legendas. Não concluir nível universitário apenas pelo título; sinalizar inferência. Snapshot do conteúdo lido recebe hash; transcrição tem origem e timestamps, e tradução fica marcada.

Buscar em fontes institucionais/editoriais selecionadas, conferir fetch controlado e só então recomendar. Metadados podem justificar um link para explorar, mas não resumo/conclusão sobre conteúdo não lido. Proposta operacional: até cinco candidatos por solicitação, fetch de três, 10 s e 5 MiB por recurso, no máximo dois redirects com revalidação de destino. Rede desligada consulta cache identificado; sem cache, dizer indisponível e continuar tutoria local.

**Alternativas/seleção.** Transcrição fornecida pelo estudante ou publicada pelo autor é alternativa à API de captions; ASR local exigiria arquivo autorizado, novo modelo e validação, fora do núcleo desta rodada. Provedor de busca web ainda não foi escolhido/verificado. Testar metadados sem transcrição, link morto, mudança de conteúdo, tradução, limite de quota e offline. Gate: nenhum resumo atribuído a vídeo sem conteúdo lido e nenhuma URL inventada.

### C13 — Grafo, checkpoint, pausa e divergência

**P.** `lgstate` distingue checkpoint por thread de store entre threads; checkpointers persistem em super-steps e pending writes permitem aproveitar nós já concluídos. Modos documentados: `exit`, `async`, `sync`, com durabilidade/custo diferentes. `lginterrupt` exige checkpointer e mesmo `thread_id` para `Command(resume=...)`; o nó **reinicia desde o começo**, inclusive código anterior ao interrupt. Não é uma continuação exatamente na linha suspensa. A URL antiga durable-execution devolveu a página Persistence; detalhes foram obtidos na página Checkpointers, não atribuídos a uma página inexistente.

**H — desenho.** Rotas fixas por intenção enum: ingestão, tutoria, resposta ao exercício, planejamento e curadoria opcional. Curador/Bibliotecário produzem evidências e snapshot; Tutor/Monitor/Planejador consomem somente seus contratos; validador/solver determinísticos fecham fluxo. Um único escritor de estado de domínio. Paralelizar somente leitura independente, preservando snapshot comum; chamadas ao único LLM entram na fila C01.

Estado carrega IDs, status, snapshot_version, fontes, pending_question, orçamento restante e cancelamento; documentos integrais ficam fora do checkpoint. Pausas por ambiguidade/confirmação/resposta do aluno são terminais de invocação, retomados por nova entrada autorizada. Efeitos ficam em nó separado e idempotente. Propor `durability=sync` e checkpointer SQLite local; não usar `InMemorySaver` para continuidade após reinício.

Divergências: sintaxe inválida permite um reparo; incompatibilidade com origem/PDD/solver volta a esclarecer ou falha controlada, sem votação entre agentes. Somente arestas declaradas; limite de 16 transições e budgets C17; todo ciclo tem contador/saída. Baseline agente único recebe mesmas ferramentas/dados/reservas. **Alternativa:** máquina de estados própria é mais simples se o grafo for pequeno, mas exigiria implementar retomada; serviços A2A só após necessidade real de distribuição. **Seleção:** roteamento, pausa sem geração continuada, retomada após reinício, cancelamento e falha de ramo; conferir que nenhum efeito duplica.

### C14 — Comunicação, schemas e MCP

**P.** `pydstrict` explica coerção padrão e modo estrito, mas admite strings para datas em JSON mesmo no strict mode. `mcparch` descreve host-client-server, JSON-RPC, negociação de capacidades e isolamento de contexto. Não define comunicação pedagógica entre agentes nem atomicidade de efeitos.

**H — contrato interno.** Envelope: `schema_version`, `task_id`, `trace_id`, `parent_task_id`, `sender_role`, `artifact_type`, `snapshot_version`, `source_refs`, `payload_ref`, `status`, `error`. `trace_id` correlaciona execução, `task_id` identifica trabalho e `operation_id` C16 identifica efeito; nenhum deles é credencial. Artefatos específicos: manifesto, evidence pack, turno pedagógico, evidência formativa e proposta temporal. Validar Pydantic estrito, campos extras proibidos, enum, comprimentos e regras cruzadas; exportar JSON Schema e conferir o subconjunto aceito pelo runtime. Em erro devolver código tipado (`SCHEMA_INVALID`, `SOURCE_UNRESOLVED`, `VERSION_CONFLICT`, `TOOL_DENIED`, `TIMEOUT`, `CANCELLED`) e possibilidade de retry, sem stack/secrets no prompt.

Referências transportam ID+versão/hash; consumidor hidrata sob permissão e snapshot, nunca “último estado” implícito. Resultados concorrentes só entram se compatíveis com versão lida. O grafo invoca funções tipadas no mesmo processo; não há mailbox livre. MCP é adaptador na fronteira, com versão negociada/fixada, servidor e schemas em allowlist. Não habilitar sampling/prompts de servidor externo automaticamente.

**Alternativas/seleção.** JSON Schema puro é portável, Pydantic reduz duplicação no ecossistema Python; transporte HTTP/serviços acrescenta autenticação e falhas, sem necessidade no MVP. A2A não é requisito interno e não teve especificação auditada nesta rodada. Testar round-trip, datas JSON, versão antiga incompatível, payload_ref inexistente, acesso cruzado e retorno malformado; schema válido ainda passa pelas regras de intenção/efeito C15.

### C15 — Ferramentas como capacidades controladas

**P.** `mcpsec` trata execução de servidores locais com privilégios do cliente, SSRF, token passthrough, confused deputy e autenticação que não pode depender apenas de session ID. `llamasrv` também explicita privilégios de subprocessos/ferramentas. MCP não substitui sandbox, autorização ou validação semântica.

**H — matriz mínima.** Curador: ler documentos autorizados, extrair e recuperar; fetch só em modo conectado. Tutor: recuperar evidências e propor atividades, sem escrita direta em agenda/perfil. Monitor: propor evidência formativa. Planejador: solicitar solver e produzir preview. Bibliotecário: propor atualização versionada. Orquestrador/serviço determinístico: validar e executar commits; confirmação externa segue o requisito já existente no esqueleto. O papel é atribuído pelo código, não por argumento produzido pelo LLM.

Toda chamada passa por: ferramenta permitida → schema → ownership/path/URL → compatibilidade com tarefa/snapshot → budget → confirmação quando exigida → execução restrita → conferência do efeito. Conteúdo de PDF, site e tool result entra como dados rotulados; nunca registra novas ferramentas nem muda permissões. Paths canônicos ficam em raízes autorizadas, com symlink/traversal verificados; fetch externo bloqueia destinos privados/loopback e revalida redirects/DNS. Inferência loopback é uma capacidade distinta do fetch externo. Não expor shell genérico. Escritas usam ações de domínio pequenas e idempotentes. Timeout não é comprovante de que efeito não ocorreu.

**Alternativas/limites/seleção.** Sandbox por subprocesso/container reduz impacto com custo de empacotamento; uma função local restrita pode bastar para operações puras, mas parser de arquivo também precisa de limites. Prompt defensivo sozinho não aplica autorização. Testar PDF instruindo a mudar prazo, resultado pedindo exfiltração, ferramenta não permitida, path escape, redirect interno e chamada JSON válida para usuário errado. Gate de integração: zero efeitos não autorizados nos casos preparados, sem extrapolar isso como prova absoluta de segurança.

### C16 — Persistência, outbox e recuperação

**P.** `sqlitewal` documenta leitores com snapshot, um escritor por vez, WAL no mesmo host, `SQLITE_BUSY`, diferenças FULL/NORMAL e risco de perder estado ao copiar DB sem WAL ativo. Checkpoint WAL é consolidação de páginas, diferente do checkpoint do grafo. A página atualizada em 25/08/2026 registra correção do WAL-reset bug em 3.51.3 e backports 3.44.6/3.50.7: o manifesto deve identificar a biblioteca SQLite efetivamente carregada, não somente a versão de Python. `lgstate` não garante uma transação comum entre banco de domínio, checkpointer e efeitos externos.

**H — protocolo de domínio.** SQLite local com WAL, `synchronous=FULL`, transações curtas e escritor serializado. Eventos originais, fatos confirmados, operações/outbox e versões em um DB de domínio. Checkpointer pode usar DB separado, mas sua atualização não é atômica com domínio: reexecutar nó consulta operação/evento já comprometido e devolve o mesmo resultado. Não manter transação aberta durante geração/fetch.

1. Receber `operation_id` estável e digest da ação, escopo de usuário e `expected_version`.
2. Em uma transação: verificar permissão/versão, inserir operação com unicidade, evento e outbox, atualizar projeção; conflito não sobrescreve.
3. Dispatcher pega item pendente com lease; efeito externo recebe chave idempotente quando suportada. Resultado confirmado vira recibo e evento em transação local.
4. Crash antes de commit deixa nada promovido; crash após commit permite recuperar item pendente. Crash após efeito e antes do recibo exige consulta/reconciliação por UID/operation_id. Se o destino não permite saber se ocorreu, marcar `UNKNOWN_EFFECT` e suspender retry automático.
5. Retomada do grafo reidrata snapshot/recibo; deduplica por operação, não pelo texto do LLM. Índice recebe versão publicada somente após indexação completa; recuperação filtra versão ativa e hidratação confere autoridade no DB.

Outbox é padrão proposto aqui, não função nativa demonstrada pela página WAL. “Exactly once” externo não é prometido: buscar entrega ao menos uma vez com efeito idempotente/reconciliação. Hash de ação diferente com mesmo operation_id é erro. Migrações numeradas com backup anterior e verificação de schemas; índice reconstruível por manifesto. Backup inicial proposto: parar escritores/conexões, efetuar fechamento/checkpoint consistente e copiar conjunto fechado com originais e manifesto; alternativa online exige auditar e testar API de backup em rodada posterior, não copiar apenas `.db` aberto.

**Alternativas/seleção.** PostgreSQL local atende mais escritores e operação multiusuário com maior custo; SQLite rollback journal simplifica cenários de baixa concorrência. Gates por injeção de crash nos cinco pontos, duas propostas concorrentes, disco cheio/DB busy, migração e restauração: zero duplicação de efeito confirmado, zero evento comprometido desaparecido no teste, derivação reproduzível e pendência explícita quando efeito desconhecido. Exclusão por usuário precisa alcançar originais autorizados, projeções, índices, checkpoints e traces relacionados; um tombstone sozinho não realiza exclusão dos bytes.

### C17 — Traces, custos, limites e cancelamento

**P.** `oteltrace` define traces/spans, parentesco, atributos, eventos, status, links e exporters inclusive locais. Não fornece instrumentação automática de tokens/VRAM deste sistema. `llamasrv` documenta métricas opcionais; não substituem trace de domínio. Trace observacional não é registro autoritativo de commit.

**H.** Raiz por turno; spans para fila, ingestão, retrieval lexical/denso, fusão, rerank, LLM, validação, solver, commit e ferramenta. Guardar IDs/hash/versões, input/output token counts, backend, prompt/template hash, sampler, seed, tempo de fila/prefill/decode/total, status e erro tipado. Registrar razões de abstinência, repair count, hits/citações e solver status sem reinventar saída do solver. RSS e VRAM são séries/métricas correlacionadas; instrumentação depende de processo/backend. Payloads completos ficam fora dos spans por padrão; anexos de diagnóstico são locais, limitados e vinculados por hash. Não usar cadeia de pensamento como prova de correção.

Budgets iniciais: até seis chamadas LLM por turno, um reparo por artefato e dois no total, oito chamadas de ferramenta e 16 transições de grafo; deadline interativo de 120 s ativo, geração individual até 90 s. Ingestão roda como job separado com limite por documento e progresso, não consome indefinidamente turno interativo. Valores são H e podem ser inviáveis em CPU: calibrar SLO no hardware real, sem abandonar o limite. Tempo aguardando aluno não conta como computação ativa. Cancelamento impede novos despachos, tenta interromper geração/subprocesso, persiste estado e reconcilia efeito já iniciado. Resposta deve distinguir cancelado, timeout, insuficiência de fonte e efeito desconhecido.

**Alternativas/seleção.** JSONL local com correlação é início barato; OpenTelemetry + collector/backend local facilita árvore/consulta com consumo adicional. LangSmith hospedado não é necessário para núcleo offline. Testar export sem rede, span ausente, fila cheia, timeout, orçamento esgotado e cancelamento durante efeito. Medir overhead da observabilidade e incluir falhas/truncamentos na análise de latência, sem reportar somente execuções bem-sucedidas.

### C20 — Empacotamento e execução reproduzível

**P.** `uvlock` documenta lock e sync, `--locked` verifica desatualização, enquanto `--frozen` ignora essa verificação; extras não são instalados automaticamente. Lock não contém por si só pesos, binários GPU, pacotes de idioma OCR ou dados. `bonsaidemo` mostra release pinada, mas setup baixa componentes e extras: isso não demonstra instalação offline.

**H.** Manifesto de execução inclui SO/kernel, CPU/RAM, GPU/VRAM/driver/backend, Python/uv, SQLite carregado, pacotes Python, fork/commit/release/hash do binário, pesos e tokenizer/template, OCR/idiomas, embedding/reranker, prompts/skills/schemas, versão do corpus e seed/configuração. Instalação em duas fases: preparar bundle com artefatos e wheels compatíveis na máquina conectada; instalar/reconstruir em ambiente sem rede com hashes conferidos. Propor lock Python com `uv sync --locked`, cache/bundle previamente abastecido e bloqueio de rede; `--offline` precisa ser conferido na versão/CLI adotada, pois a página consultada não especifica todo o processo offline.

CLI futura: `doctor`, `ingest`, `ask`, `resume`, `trace`, `backup`, com outputs e exit codes documentados. Smoke test futuro: PDF digital e página OCR conhecida → índices → pergunta com citação → pausa/restart/resume → efeito simulado deduplicado → trace local. Provar instalação offline em ambiente limpo/cache declarado, não apenas executar modelo já baixado. Núcleo textual dispensa web, visão, code interpreter e serviços remotos; conectores têm extras/configurações próprios.

**Alternativas/seleção.** Container fixado por digest facilita dependências nativas, porém compatibilidade GPU/driver e tamanho continuam custos; venv+binário empacotado simplifica CLI local. Não congelar números de versão não consultados como se fossem testados. Gate: bundle verificável, smoke offline, restauração e manifesto completo em hardware real. A escolha final depende conjuntamente de C01, C02 e C16.

## 4. Sequência de validação e decisões condicionais

| Ordem | Ensaio/artefato futuro | Decisão que resolve |
|---|---|---|
| 1 | Manifesto de hardware, download com hashes, carga/tokenizer/schema/tools em português | Admitir Bonsai 2 e packing/runtime ou manter seleção aberta (C01/C20) |
| 2 | Páginas anotadas com datas, tabelas, colunas e OCR | Motor/diagnóstico, ontologia e chunking (C02/C03) |
| 3 | Queries com ouro e sem resposta; ablações de retrieval | BM25/dense, RRF/DBSF, reranking e abstinência (C04) |
| 4 | Contratos, rotas, pausas e efeitos simulados | Comunicação/grafo/política (C13–C15) |
| 5 | Crashes, concorrência, timeout e restauração | Outbox, idempotência e durabilidade (C16) |
| 6 | Carga limitada, cancelamento, traces e bundle sem rede | Budgets/SLO e fechamento do núcleo (C17/C20) |
| 7 | Cache, links e vídeo sem transcrição com rede opcional | Admissão do conector C05 separadamente |

Para cada alternativa, registrar tabela de configuração, qualidade/cobertura, falhas, latência e memória. Os mesmos contratos/ferramentas ficam disponíveis no baseline. Estes ensaios alimentam C18/C19, mas não substituem pesquisa específica de desenho experimental, pedagogia ou solver.

## 5. Fontes consultadas: identidade, alcance e limites

As chaves abaixo correspondem aos registros em `references_arquitetura.bib`. Datas `s.d.` indicam ausência de ano editorial explícito na página recuperada. URLs auxiliares efetivamente abertas constam aqui e nas notas dos registros quando cabível.

| Chave | Título, autores/responsável, ano | URL verificada e o que sustenta |
|---|---|---|
| `bonsai2` | **Bonsai 2 27B — GGUF**; Prism ML; 2026 | https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/raw/main/README.md — identidade, licença declarada, packings, janela, sampling e resultados do fornecedor. Auxiliar: https://huggingface.co/api/models/prism-ml/Ternary-Bonsai-2-27B-gguf?blobs=true — revisão, bytes e SHA-256 LFS. Auxiliar: https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/raw/main/KNOWN_ISSUES.md — limites de runtime, structured output e relatos não reproduzidos. Card/notas não são benchmark independente. |
| `bonsaidemo` | **Bonsai Demo**; Prism ML / PrismML-Eng; 2026 | https://raw.githubusercontent.com/PrismML-Eng/Bonsai-demo/main/README.md — fork obrigatório, release pinada, parâmetros e setup. Estado upstream declarado em 25/09/2026; binários não baixados nem release auditada. |
| `llamasrv` | **LLaMA.cpp HTTP Server**; contribuidores de llama.cpp / ggml-org; s.d. | https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/README.md — API, schema, slots, métricas e privilégios das ferramentas. Saída truncada: recursos utilizados estavam no trecho legível; não foram auditadas todas as rotas nem paridade com o fork. |
| `docling` | **Docling document**; Docling Project; s.d. | https://docling-project.github.io/docling/concepts/docling_document/ — representação tipada, hierarquia, ordem, proveniência, tabelas e bbox quando disponíveis. Não prova exatidão de OCR. |
| `ocrpdf` | **Cookbook**; OCRmyPDF contributors; s.d. | https://ocrmypdf.readthedocs.io/en/latest/cookbook.html — idiomas, rotação/deskew, sidecar parcial, rasterização e assinaturas. Contém opções v17: só usar após pin/checagem da versão escolhida. |
| `m3` | **M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation**; Jianlv Chen, Shitao Xiao, Peitian Zhang, Kun Luo, Defu Lian, Zheng Liu; 2024 (v5 em 2025) | https://arxiv.org/abs/2402.03216 — autores/data/DOI e abstract sobre funcionalidades, idiomas e comprimento. Texto integral/resultados específicos em português não lidos. |
| `bgerank` | **Reranker: bge-reranker-v2-m3**; Beijing Academy of Artificial Intelligence (BAAI); s.d. | https://huggingface.co/BAAI/bge-reranker-v2-m3/raw/main/README.md — modalidade multilingual, licença, pares query/passagem, scores e exemplo de truncamento. Gráficos de avaliação não foram lidos quantitativamente; não atribuir benchmark do paper M3 a este reranker. |
| `rrf09` | **Reciprocal rank fusion outperforms condorcet and individual rank learning methods**; Gordon V. Cormack, Charles L. A. Clarke, Stefan Buettcher; 2009 | https://api.crossref.org/works/10.1145/1571941.1572114 — título/autores/ano/SIGIR/páginas/DOI verificados **como metadados**. PDF primário não ficou legível; não se afirma verificação do experimento/fórmula no artigo. |
| `qdranthyb` | **Hybrid and Multi-Stage Queries**; Qdrant; s.d. | https://qdrant.tech/documentation/concepts/hybrid-queries/ — conteúdo com links canônicos em `/documentation/search/hybrid-queries/`, prefetch, RRF e DBSF; diferenças de ranks/defaults/versões. Saída truncada após trechos usados; não auditoria de todo o banco. |
| `lgstate` | **Checkpointers**; LangChain; s.d. | https://docs.langchain.com/oss/python/langgraph/checkpointers — StateSnapshot, thread/super-step, pending writes, replay, durability e backends. Auxiliar: https://docs.langchain.com/oss/python/langgraph/persistence — checkpoint versus store e volatilidade InMemorySaver. Recursos beta (DeltaChannel) excluídos do núcleo. |
| `lginterrupt` | **Interrupts**; LangChain; s.d. | https://docs.langchain.com/oss/python/langgraph/interrupts — pause/resume, reinício do nó e necessidade de idempotência. Exemplos online de traces não foram abertos. |
| `mcparch` | **Architecture**, especificação 2025-11-25; Model Context Protocol contributors; 2025 | https://modelcontextprotocol.io/specification/2025-11-25/architecture — host/client/server, JSON-RPC, capabilities e contexto isolado. Não sustenta detalhes não consultados de transportes/tools. |
| `mcpsec` | **Security Best Practices**, especificação 2025-11-25; Model Context Protocol contributors; 2025 | https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices — SSRF, redirects, permissões locais, sessão/autenticação, token audience e scopes. Não demonstra resistência a qualquer prompt injection. |
| `pydstrict` | **Strict Mode**; Pydantic contributors; s.d. | https://docs.pydantic.dev/latest/concepts/strict_mode/ — coerção versus strict, exceções para JSON/data. Validação de domínio/efeito é camada própria. |
| `sqlitewal` | **Write-Ahead Logging**; SQLite developers; 2026 (atualização explícita 25/08) | https://sqlite.org/wal.html — concurrency, sync, WAL, snapshots, limites de backup/cópia e correção WAL-reset. Não fornece protocolo outbox. |
| `oteltrace` | **Traces**; OpenTelemetry Authors; s.d. | https://opentelemetry.io/docs/concepts/signals/traces/ — spans, IDs, attributes/events/links/status e export. JSON ilustrativo explicitamente não é formato OTLP/JSON. |
| `ytcaptions` | **Captions: download**; Google; 2026 (atualização explícita 15/09) | https://developers.google.com/youtube/v3/docs/captions/download — autorização/edição, quota 200, formatos, tradução e erros. Não valida provedor de busca nem acesso universal a legendas públicas. |
| `uvlock` | **Locking and syncing**; Astral; 2026 (data explícita 05/08) | https://docs.astral.sh/uv/concepts/projects/sync/ — lock/check/sync, frozen versus locked e extras. Bundle offline completo é proposta, não funcionalidade comprovada por esta página. |

### Trilha de busca e exclusões

| Etapa/consulta efetiva | Resultado e tratamento |
|---|---|
| API de descoberta `https://huggingface.co/api/models?search=Bonsai&limit=20` | Identificou publicador `prism-ml`, Bonsai 2 e derivados; seguir card/API do publicador. Não usar likes/downloads como prova de qualidade. API de busca é trilha auxiliar, não artigo adicional. |
| Card → API `?blobs=true` → README do demo → KNOWN_ISSUES | Identidade resolvida como candidato; comparação de datas revelou informação operacional móvel/divergente. Excluídos forks comunitários “abliterated/uncensored”, speculative builds e Bonsai 8B/Bonsai 1 como substitutos automáticos do Bonsai 2. |
| `https://docling-project.github.io/docling/concepts/document/` | **404**; não verificada. URL corrigida para `concepts/docling_document/`, com conteúdo legível. Falha não vira referência bibliográfica. |
| OCRmyPDF cookbook, Docling, arXiv 2402.03216 e model card BAAI | Separação de representação/OCR/embedding/reranker. Excluídas afirmações de que “multilingual” ou OCR ativo garantem qualidade em português. Não foram auditados todos os motores/alternativas citados nos menus. |
| `https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf` | HTTP bem-sucedido, mas webfetch entregou conteúdo binário/truncado; **texto do paper não verificado**. Crossref confirmou apenas bibliografia; Qdrant forneceu explicação operacional legível. Não atribuir `k=60` ao artigo como fato lido. |
| Qdrant hybrid queries e servidor llama.cpp | Conteúdo recuperado parcialmente por limite da ferramenta; usar somente seções legíveis registradas. Sem leitura de restante truncado ou teste de compatibilidade. Excluída fusão linear de BM25/cosseno brutos sem normalização. |
| LangGraph persistence e `https://docs.langchain.com/oss/python/langgraph/durable-execution` | A segunda URL devolveu **Persistence**, não documentação específica de durable execution; limitação registrada. Seguir páginas Checkpointers e Interrupts, efetivamente lidas. Não usar agente remoto/Agent Server como requisito local. |
| URLs conhecidas MCP 2025-11-25, Pydantic strict, SQLite WAL, OpenTelemetry traces, YouTube captions e uv sync | Fontes oficiais legíveis. Excluídos MCP como sandbox/garantia transacional, JSON válido como autorização, InMemorySaver como persistência de reinício e API captions como transcrição universal. |
| Referências de partida MetaGPT/MultiTutor/MemGPT/Voyager/ToRA | Não consultadas nesta rodada: não entram no `.bib` nem são apresentadas como evidência de RAG/runtime/transações. A2A, modelos alternativos e API online de backup aguardam pesquisa específica. |

Não foi realizada busca sistemática em todos os motores ou bases bibliográficas; foi uma pesquisa dirigida pelos requisitos com URLs oficiais conhecidas e expansão por links pertinentes. Não há registro fictício de consulta a motores de busca, Crossref em massa ou leitura de PDF integral.

## 6. Pendências explícitas

1. Confirmar que o Bonsai 2 identificado é o pretendido; baixar revisão/pesos e conferir hashes, LICENSE/NOTICE, tokenizer e runtime no hardware disponível. Benchmarks do publicador não encerram esse gate.
2. Fixar e testar release/commit do fork com schema, tool parser, português e budgets; reconciliar known issues de 23/09 com demo de 25/09 por release concreta.
3. Escolher motor OCR/idiomas e granularidade de tópicos com ouro humano; não fixar confidence probabilística sem calibração.
4. Medir seleção de embedding/reranker, custo de co-residência, formulação RRF/ranks e limiar de abstinência. Revisions/hashes BAAI ainda não foram coletados.
5. Auditar provedor de busca e estratégia de transcrição para C05; curadoria permanece opcional e metadados não equivalem a conteúdo lido.
6. Implementar e testar semântica de snapshot/outbox/checkpoint e backup, incluindo efeitos desconhecidos; não presumir atomicidade entre serviços.
7. Fixar versões, limites/SLO e pacote offline completo, export local de traces e exclusão por usuário. Reprodutibilidade exige artefatos além do lock Python.
8. Obter leitura integral legível do artigo RRF se forem usados seus resultados/parâmetros históricos no relatório; nesta pesquisa a referência é bibliograficamente verificada e metodologicamente limitada.
