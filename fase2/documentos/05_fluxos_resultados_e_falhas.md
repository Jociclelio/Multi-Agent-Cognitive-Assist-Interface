# Etapa 5 — Fluxos, saídas esperadas e pontos de falha

## 1. Universo de tarefas

O universo é o conjunto de intenções e estados da especificação v0.1 (etapa4). Pedidos compostos são decompostos em rotas existentes, sem criar capacidades ilimitadas. Os fluxos abaixo cobrem sucesso, espera, conflito, abstinência, cancelamento e falha controlada. Novos conectores/skills exigem revisão desta matriz.

| Fluxo | Gatilho e sequência | Saídas esperadas (IDs O) | Variações e término |
|---|---|---|---|
| W01 Ingestão | PDF/texto→extração→fatos→confirmação→índice | O01 manifesto/blocos; O02 tópicos/prazos/pendências | Digital, scan, tabela, duplicata, revisão; ilegível ou oversized são explícitos |
| W02 Consulta fundamentada | pergunta→fontes+memória→tutor→validação | O03 pacote/citações; O04 explicação | Resposta apoiada, parcial, geral rotulada ou abstinência; termina em resposta/esclarecimento |
| W03 Prática | objetivo→skill→item/gabarito→tentativa/pistas | O05 exercício/quiz; O06 flashcard; O07 turno/pista/autoexplicação | Separar solução; pedido de solução/recusa interrompe pistas; espera não gera chamadas |
| W04 Avaliação formativa | resposta pendente→monitor→commit→feedback | O08 avaliação/evidência; O09 estado/revisão | Correta/parcial/incorreta/indecidível, com/sem ajuda; não produz nota oficial |
| W05 Retomada longitudinal | sessão nova→snapshot→eventos relevantes | O10 memória atual/temporal; O11 síntese/contexto | Fato corrigido, dificuldade recorrente, evidência antiga ou ausente; não inventar continuidade |
| W06 Planejamento | disponibilidade/prazos→demandas→solver→check→preview | O12 demandas; O13 plano/conflito | Viável, ótimo, inviável provado, inconclusivo ou entrada ambígua; espera confirmação |
| W07 Replanejamento | erro/tarefa perdida/mudança→novo snapshot→W06 | O13 diff e déficit; O09 revisão | Preservar blocos fixos; duração estimada é transparente; nenhum overwrite silencioso |
| W08 Agenda | plano aprovado→ICS→parser [→outbox→sync] | O14 ICS/recibo de efeito | Sem rede exporta local; timeout remoto gera reconciliação, não duplicata |
| W09 Curadoria | tópico→gate rede/cache→search/fetch→rank | O15 recursos/estado de acesso | Vídeo metadata-only, transcrição real, link morto, offline; sem resumo fictício |
| W10 Memória explícita | pergunta/correção/exclusão→escopo→preview→commit | O10 resposta/correção; O16 recibo de alteração/exclusão | Propagação a derivados e backup policy; conflito pede esclarecimento |
| W11 Recuperação operacional | crash/restart/cancel/fila cheia→replay/reconcile | O16 recibo/status; O17 trace/métricas | Retomada idempotente, cancelamento, resource_limit/unknown_effect |
| W12 Instalação/manutenção | doctor/bundle/backup/restore→smoke/integridade | O18 manifesto/diagnóstico/backup | Sem rede, versão incompatível, DB busy/disco cheio; não anunciar sucesso sem check |

## 2. O que constitui qualidade de cada saída

| Saída | Conteúdo necessário | Perda de qualidade típica |
|---|---|---|
| O01 | Original identificável, texto/blocos/ordem e página, versão, diagnóstico | OCR troca data/sinal, tabela perde cabeçalho, página errada |
| O02 | Tópico/granularidade, prazos com autoridade/precisão/zona, conflitos | Alias fundido, deadline inferido, revisão substitui confirmado |
| O03 | Relevância/cobertura, fonte resolvível e que sustenta afirmação | Recall baixo, trecho fora de contexto, citação existente mas irrelevante |
| O04 | Corretude conceitual, pertinência, clareza, limites e apoio | Fluência mascara erro, fonte não sustenta, explica outro tópico |
| O05 | Enunciado decidível, nível adequado, resposta/rubrica válida, fonte | Exercício impossível, gabarito circular, múltiplas respostas não previstas |
| O06 | Conceito atômico, frente/verso separados, precisão e fonte | Verso na pergunta, lista longa, erro reforçado por repetição |
| O07 | Apoio adequado ao erro, participação, nenhuma solução antecipada, término | Perguntas genéricas, excesso de pistas, insiste quando aluno pede solução |
| O08 | Julgamento por critério, span real, feedback acionável e abstinência | Texto longo recebe crédito injusto, erro formal ignorado, evidência inventada |
| O09 | Estado reproduzível, ajuda preservada, atualidade e revisão | Copiou solução vira domínio, erro é atualizado duas vezes, inferência sem dados |
| O10 | Fatos atuais e históricos temporalmente corretos, origem/isolamento | Perfil antigo reativado, outro usuário vazado, ausência preenchida |
| O11 | Fatos críticos preservados, cobertura e refs, budget real | “Com pista” vira “sem pista”, prazo muda, rubrica removida |
| O12 | Demanda ligada à evidência, duração/prioridade justificadas | Duração arbitrária obrigatória, pré-requisito ignorado, urgência inventada |
| O13 | Viabilidade, completude, déficit, status exato, diff e churn controlado | Sobreposição, prazo perdido, UNKNOWN chamado inviável, plano obsoleto |
| O14 | Validade ICS, correspondência ao plano, UID/versão/recibo | Zona desloca horário, retry duplica, remoto diverge do aprovado |
| O15 | URL real, pertinência, nível/idioma/acesso justificados | Link inventado, vídeo não lido resumido, fonte muda sem aviso |
| O16 | Estado verdadeiro, operação identificável, efeito/exclusão conferidos | ACK sem efeito, efeito duplicado, exclusão deixa dados em índice |
| O17 | Trace completo e counts/status corretos, falhas incluídas | Não mede fila, truncamento desaparece, custo mede só última chamada |
| O18 | Artefatos/versionamento/hashes, hardware, instalação/restore verificáveis | Lock sem pesos, DB copiado sem WAL, manifesto irreproduzível |

## 3. Catálogo de falhas

Severidade: S1=qualidade localizada; S2=perda pedagógica/continuidade; S3=restrição, dado ou efeito comprometido; S4=indisponibilidade/corrupção generalizada. Severidade é potencial, não frequência observada.

| ID | Ponto e causa | Propagação/impacto | Saídas/fluxos | Severidade |
|---|---|---|---|---|
| F01 | OCR/parser erra ordem/número/página | Fonte ruim→gabarito ou deadline incorreto | O01–05/O13; W01–06 | S3 |
| F02 | Extração ontológica resolve ambiguidade sem confirmação | Restrição falsa altera cronograma | O02/O12/O13; W01/W06 | S3 |
| F03 | Recuperação omite trecho ou escolhe versão errada | Resposta parcialmente correta com falsa segurança | O03/O04/O05; W02/W03 | S2 |
| F04 | Geração/citação alucina ou fonte não implica claim | Explicação e aprendizado reforçam erro | O03–08; W02–04 | S2 |
| F05 | Tutor vaza solução, ignora ajuda/recusa ou insiste | Tentativa deixa de medir entendimento; loop pedagógico | O05–09; W03/W04 | S2 |
| F06 | Monitor/gabarito tem viés ou erro correlacionado com Tutor | Falso progresso orienta prática e agenda | O08/O09/O12; W04/W07 | S3 |
| F07 | Redutor/BKT usa ajuda como acerto independente ou dado futuro | Estado fictício e revisão inadequada | O09/O10/O13; W04–07 | S3 |
| F08 | Memória omite correção/tempo e mistura origem | Continuidade incoerente ou dado antigo atual | O10/O11; W05/W10 | S2 |
| F09 | Compactação perde polaridade, prazo, rubrica ou ajuda | Erro atravessa agentes sem parecer erro | O08–13; W02–07 | S3 |
| F10 | Schema válido mas errado; envelope/ref/versão incompatível | Agente interpreta artefato indevido | Todas; todas rotas | S3 |
| F11 | Grafo roteia mal ou repete chamadas sem limite | Latência, custo e ausência de resposta | O07/O16/O17; W02–11 | S4 |
| F12 | Modelo/local backend trunca, OOM, fila ou tokenizer diverge | Saída incompleta promovida ou indisponibilidade | O04–13/O18; W02–12 | S4 |
| F13 | Demanda/slots/zona/solver status incorretos | Plano formalmente “válido” viola tempo real | O12/O13/O14; W06–08 | S3 |
| F14 | Concorrência usa snapshot obsoleto ou replan move fixo | Plano aprovado contradiz agenda atual | O13/O14/O16; W07/W08 | S3 |
| F15 | Timeout/ACK/crash causa efeito duplicado ou desconhecido | Agenda diverge ou operação perde rastreabilidade | O14/O16; W08/W11 | S3 |
| F16 | Prompt injection em PDF/site/tool result induz ação | Fonte vira comando e altera dado/agenda/acesso | O02/O14/O16; W01/W09 | S3 |
| F17 | Isolamento/path/URL falha | Dados cruzados, exfiltração ou destino indevido | O10/O15/O16; W09/W10 | S3 |
| F18 | Disco cheio/DB busy/crash/migração/backup incompleto | Estado parcial, evidência perdida, replay incoerente | O09–18; W04–12 | S4 |
| F19 | Web indisponível, metadata-only, quota ou recurso mudou | Recomendação sem conteúdo e núcleo bloqueado | O15/O04; W09/W02 | S2 |
| F20 | ICS serializa mal UTF-8/zone/UID/all-day | Horário errado ou importação divergente | O14; W08 | S3 |
| F21 | Correção/exclusão não invalida índice/resumo/backup | Fato reaparece ou dado permanece recuperável | O10/O11/O16; W10/W12 | S3 |
| F22 | Trace/métrica omite retries/falhas/energia indisponível | Experimento subestima custo e explica mal falha | O17/O18; todas | S2 |
| F23 | Dataset contaminado, juiz enviesado, repetição pseudoindependente | Conclusão de superioridade sem validade | Relatório experimental; todas | S3 |
| F24 | Empacotamento sem pin/hash/dependência offline | Outro agente não reproduz instalação/resultados | O18; W12 | S4 |

## 4. Falhas compostas prioritárias

1. OCR troca data→Curador confirma indevidamente→solver produz plano ótimo para prazo errado. O solver não elimina F01/F02.
2. Tutor e Monitor compartilham modelo/gabarito→erro consistente→memória compactada vira “domina”→Planejador reduz prática. Validar fontes e julgamento independentemente.
3. Replanejamento aprovado→agenda externa muda→retry pós-timeout sobrescreve mudança. Exige snapshot/ETag e reconciliação, não apenas UID.
4. Correção registrada→resumo antigo permanece no índice→sessão retoma a versão errada. Exige invalidação transitiva.
5. Interrupção do grafo reexecuta nó→efeito já ocorreu→sem operation_id duplica. Checkpoint sozinho não garante idempotência.
6. Falha de geração consome deadline→sistema avalia só casos concluídos→p95 e sucesso parecem melhores. Falhas devem permanecer no denominador.

## 5. Rastreabilidade e cobertura

W01–W12 cobrem todas as intenções da etapa4; O01–O18 cobrem artefatos internos, saídas ao estudante e operacionais; F01–F24 cobrem cada fronteira de transformação/persistência/efeito e a validade da avaliação. A etapa6 define métricas para todos esses IDs e a etapa7 seleciona métodos. O catálogo não presume enumerar todos os defeitos futuros: mudanças de capability exigem novo fluxo, saída, falha e teste.
