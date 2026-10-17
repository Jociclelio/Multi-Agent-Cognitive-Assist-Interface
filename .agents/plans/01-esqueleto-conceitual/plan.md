# Plano: Esqueleto conceitual do EduAgent-OS

Estado: aprovado

## Objetivo
Documentar a etapa 1 (esqueleto conceitual) do EduAgent-OS como proposta de implementação: recorte de escopo, princípio arquitetural multiagente com modelo local, responsabilidades e fronteiras dos cinco agentes lógicos, ciclo mínimo de funcionário, camadas transversais e questões abertas remetidas às etapas seguintes.

## Abordagem
- Fixar o escopo a partir da fonte normativa (`fase1/fase1_proposta.pdf` conferida com seu fonte LaTeX): graduação, interação textual em português, documentos e PDFs do estudante, recursos complementares, exercícios, flashcards, memória entre sessões e planejamento semanal; ODS principal 4. Infraestrutura local (inferência, recuperação e armazenamento), rede opcional para curadoria e agenda. Sem notas oficiais, geração de vídeos, treinamento fundacional ou integração acadêmica fechada.
- Registrar a hipótese como hipótese (não como resultado medido): separação de responsabilidades, contratos verificáveis e memória seletiva devem melhorar continuidade e consistência sob orçamento local; a comparação com um agente único usa as mesmas ferramentas, dados e limites de recursos.
- Definir cinco agentes lógicos (Curador de Conhecimento, Tutor Adaptativo, Monitor de Aprendizagem, Planejador de Rotina, Bibliotecário de Memória) compartilhando um modelo local, com instruções, dados e permissões distintos; coordenação por grafo explícito; componentes determinísticos validando decisões do LLM; agentes não escrevem livremente nos armazenamentos.
- Especificar, por agente, responsabilidade, artefato produzido e fronteira (ex.: conteúdo recuperado não é instrução executável; viabilidade de agenda decidida por solver/verificador, não pelo texto do LLM; resumos são derivados e originais permanecem consultáveis).
- Descrever o ciclo mínimo em 7 passos (captura → extração/validação de fatos → recuperação sob orçamento de contexto → atividade/resposta/avaliação por critérios explícitos → persistência de evidência e estimativa → solver de agenda → continuidade entre sessões), com terminais explícitos (resposta, pedido de esclarecimento, espera pelo aluno, conflito de agenda, falha controlada, cancelamento); esperar o aluno não é continuar gerando chamadas.
- Listar as camadas transversais: contratos tipados e IDs estáveis; separação de dados brutos, fatos confirmados, inferências e artefatos publicados; recuperação documental distinta da memória do estudante, ambas com proveniência; skills versionadas com pré-condições e critérios de término; validação estrutural, de domínio e conferência independente de efeitos externos; checkpoints, transações, idempotência, timeout, limites de chamadas e cancelamento; registro de custo, latência, erros, delegações e versões; avaliação em camadas.
- Enumerar as questões abertas (configuração do Bonsai 2, extração/OCR, granularidade de tópicos, busca híbrida/reranking, datas, rubricas e estimador de domínio, memória, formalização do solver, ferramentas e permissões, limites operacionais, dataset e métricas), remetendo-as à etapa 2 e às etapas 3–4.
- Manter as referências de partida (MetaGPT, MultiTutor, MemGPT, Voyager, ToRA) como referências por verificar na etapa 3 e na auditoria final, sem atribuir a elas validação deste projeto.

## Escopo
- Entrega: documento da etapa 1 (esqueleto conceitual) contendo escopo/premissas, diagrama de arquitetura (Mermaid), tabela de responsabilidades e fronteiras, ciclo mínimo, camadas transversais, questões abertas e referências de partida.
- Limites: é especificação/proposta de implementação, não demonstração de superioridade e não resultado experimental; nenhuma métrica ou comparação é medida nesta etapa; lacunas metodológicas ficam para as etapas 2–4.

## Contexto
- `fase2/documentos/01_esqueleto_conceitual.md` — documento-fonte desta etapa (conteúdo a documentar).
- `fase1/fase1_proposta.pdf` — fonte normativa do escopo, citada pelo documento-fonte.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — mapa normativo de implementação (sistema), para alinhamento de decisões.

## Critérios de conclusão
- O documento da etapa 1 cobre todas as seções do esqueleto: escopo/premissas, princípio arquitetural com diagrama, responsabilidades e fronteiras dos cinco agentes, ciclo mínimo com terminais explícitos, camadas transversais, questões abertas e referências de partida.
- Nenhuma proposta de design é apresentada como resultado medido; hipótese e comparação com agente único estão condicionadas a avaliação futura com mesmas ferramentas, dados e limites de recursos.
- Questões abertas estão enumeradas e remetidas explicitamente às etapas 2–4.

## Questões abertas
As próprias questões abertas do documento (configuração verificável do Bonsai 2; extração/OCR; granularidade dos tópicos; busca híbrida e reranking; tratamento de datas; rubricas e estimador de domínio; recuperação/compactação da memória; formalização do solver; ferramentas e permissões; limites operacionais; dataset e métricas) — todas pendentes de resolução nas etapas 2–4, não nesta etapa.

## Tasks
1. [001-validar-escopo-premissas-e-principio-arquitetural](../../tasks/01-esqueleto-conceitual/001-validar-escopo-premissas-e-principio-arquitetural.md) — valida e consolida as seções 1 (escopo/premissas, hipótese como hipótese) e 2 (princípio arquitetural e diagrama Mermaid). Depende de: nenhuma. Estado: fechada (quórum 3/3 modelos distintos, nota final 9/10, decisão fechar; sem alteração de artefatos, registro `ba4e283`).
2. [002-validar-agentes-e-ciclo-minimo](../../tasks/01-esqueleto-conceitual/002-validar-agentes-e-ciclo-minimo.md) — valida e consolida a tabela de responsabilidades/fronteiras dos cinco agentes (seção 3) e o ciclo mínimo com terminais explícitos (seção 4). Depende de: 001 (resolvida). Estado: fechada (quórum 3/3 modelos distintos, nota final 9/10, decisão fechar; sem alteração de artefatos, registro `1ae71ae`).
3. [003-validar-camadas-questoes-referencias-e-consolidar](../../tasks/01-esqueleto-conceitual/003-validar-camadas-questoes-referencias-e-consolidar.md) — valida camadas transversais (seção 5), questões abertas remetidas às etapas 2–4 (seção 6) e referências de partida por verificar (seção 7); faz a consolidação final contra os critérios de conclusão e roda `fase2/scripts/verificar_documentos.py`. Depende de: 002 (resolvida). Estado: liberada.

Cobertura: as três tasks cobrem todas as seções do esqueleto exigidas pelos critérios de conclusão (escopo/premissas, princípio arquitetural com diagrama, responsabilidades e fronteiras dos cinco agentes, ciclo mínimo com terminais, camadas transversais, questões abertas e referências de partida), além da restrição de nenhuma proposta como resultado medido. O documento da etapa 1 já existe commitado; as tasks validam/consolidam, não reescrevem do zero.
