# Etapa 2 — Componentes faltantes e requisitos

“Faltante” significa não especificado tecnicamente na proposta, e não ausência comprovada em uma implementação. Os IDs abaixo são permanentes e ligam pesquisa, arquitetura e testes.

| ID | Componente | Características exigidas e critério verificável |
|---|---|---|
| C01 | Inferência local | Artefato Bonsai 2 identificável, licença, revisão/hash, runtime, quantização, tokenizer, janela e suporte a JSON; execução offline; um servidor compartilhado com fila limitada; benchmark de português e ferramentas antes da adoção |
| C02 | Ingestão e proveniência | PDF/texto, página/seção, hash, versão, ordem, diagnóstico de OCR e tabelas; nenhum prazo promovido sem origem; material ilegível resulta em pendência explícita |
| C03 | Ontologia acadêmica | Disciplina/tópico/pré-requisito/avaliação/recurso com IDs; datas com timezone e confiança; autoridade do PDD confirmado superior a sugestões; conflitos rastreáveis |
| C04 | RAG documental | Busca lexical e semântica local, filtros por disciplina/versão, reranking, budget e abstinência; citações resolvíveis para documento e página; medição de recall e sustentação |
| C05 | Curadoria conectada | Busca/fetch controlados, metadados de texto/vídeo, idioma, acessibilidade e nível; distinguir leitura de metadados de leitura de transcrição; funcionamento offline sem URLs inventadas |
| C06 | Tutor e skills | Socrático, explicação e prática graduada; habilidades versionadas para explicar, pistas, quiz, flashcards, autoexplicação; pré/pós-condições; resposta direta quando apropriada; não interrogar indefinidamente |
| C07 | Monitor formativo | Gabarito ou rubrica explícita, evidência de resposta, erros por tópico, incerteza e opção de abster; separar corretude, ajuda recebida e domínio; validação contra anotação humana |
| C08 | Estado de aprendizagem | Modelo atualizável e auditável por tópico, distinção entre observado e inferido; cold-start; revisão temporal; evitar parâmetros cognitivos arbitrários tratados como calibrados |
| C09 | Memória persistente | Eventos originais imutáveis, perfil corrigível, estado derivado versionado e sínteses com IDs de origem; recuperação temporal; correção, exclusão e isolamento por usuário |
| C10 | Gestão do contexto | Medir tokens com tokenizer real, reservar saída e ferramentas; recuperar antes de resumir; sumarização com checagem de fatos críticos; preservar prazos e evidências; medir perda de informação |
| C11 | Planejamento e solver | Slots, timezone, prazos, disponibilidade, compromissos imutáveis, duração e prioridade; solver verificável; mínimo de alterações no replanejamento; distinguir inviável de timeout |
| C12 | Exportação e agenda | ICS válido, UID estável, timezone, preview e confirmação; integração MCP opcional; idempotência, concorrência, reconciliação após timeout e nenhuma duplicação em retry |
| C13 | Orquestração | LangGraph com rotas fixas, checkpoints, pausa humana, dependências e terminais; ausência de ciclos não limitados; política para divergências; mesmas ferramentas no baseline |
| C14 | Comunicação e contratos | JSON Schema/Pydantic, envelope com task/trace/version, referência em vez de cópia integral, leitura de snapshot; erros tipados; MCP nas fronteiras de ferramentas; A2A somente como extensão de serviços |
| C15 | Política de ferramentas | Allowlist por papel, argumentos validados, tool result como dados, rede opcional, escrita mediada; JSON correto não basta: validar também intenção e efeito |
| C16 | Persistência e recuperação | Transações, outbox, controle otimista de versão, migrações, backup, retomada e deduplicação; teste de crash antes/depois de efeitos |
| C17 | Observabilidade e limites | Trace por turno, tokens, tempo, RSS/VRAM, hashes de modelo/prompt, solver status; orçamento de chamadas, tempo e reparos; cancelamento e resposta controlada |
| C18 | Dados de avaliação | Corpus autorizado, casos com ouro de fontes, tópicos, respostas e agenda; trajetórias longitudinais; splits por famílias de documentos; prevenir contaminação e registrar anotação |
| C19 | Avaliação experimental | Comparação pareada com agente único, orçamento controlado, ablações, métricas por saída/falha, oráculos independentes, IC e análise de custo; juízes humanos e LLM calibrados |
| C20 | Empacotamento e execução | Manifesto/lock de versões e hashes, configuração documentada, instalação offline possível, smoke test e CLI; hardware real registrado; extensões não obrigatórias para fechar o núcleo |

## Dependências e prioridades

Núcleo implementável: C01 → C02/C03 → C04/C09 → C06/C07/C08 → C11, sustentado desde o início por C13–C17/C20. C18/C19 devem começar antes da otimização para impedir que o conjunto de teste oriente escolhas. C05 e a **sincronização remota de C12** são conectores opcionais avaliados separadamente; ICS local de C12 é obrigatório no núcleo.

## Ambiguidades que precisam de decisão

1. A proposta nomeia Bonsai 2 sem identificador, precisão ou hardware: não se pode derivar qualidade e latência dessa designação.
2. Um único episódio correto não basta para estimar domínio: o monitor precisa de estados “evidência insuficiente” e “avaliável”.
3. Tempo insuficiente não deve ser resolvido silenciosamente removendo compromissos ou reduzindo duração obrigatória.
4. O documento externo mais recente não deve substituir automaticamente um prazo confirmado; mudanças precisam de reconciliação.
5. A2A não é requisito para comunicação interna: acrescentar serviços remotos ao MVP ampliaria os pontos de falha sem benefício demonstrado.
6. Não existe um método universalmente ótimo: cada recomendação de pesquisa deve indicar hipótese, alternativa, custo, limitação e teste de seleção.
