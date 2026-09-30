# Etapa 6 — Protocolo de avaliação de saídas e fragilidades

## 1. Objetivos e unidades

Q1: a arquitetura integra tutoria, memória e replanejamento melhor que um agente único com recursos equivalentes? Q2: a compactação/seleção de skills reduz custo preservando qualidade? Q3: contratos/validação/limites impedem falhas de se tornarem efeitos ou ausência de resposta?

Unidades: documento/página (extração), consulta (RAG), item/tentativa (pedagogia), trajetória de estudante (continuidade), instância de agenda (solver) e execução com falha (robustez). Turnos de uma mesma trajetória não são amostras independentes. Medir artefatos antes de medir sucesso agregado.

## 2. Dados e desenho experimental proposto

- Corpus autorizado de duas disciplinas de graduação, uma técnico-formal e outra com respostas conceituais abertas; português com termos técnicos ingleses. Incluir PDFs digitais, scans, tabelas e versões conflitantes. Registrar licença/autorização e não redistribuir materiais sem permissão.
- Plano inicial: 24 famílias documentais (8 desenvolvimento/4 validação/12 teste), 120 consultas por conjunto com suporte/sem suporte/códigos/temporalidade, 120 tentativas por conjunto com níveis de ajuda e erros anotados; construir itens distintos por split, não variações vazadas do mesmo enunciado. Quantidades são metas propostas e devem ser conferidas por disponibilidade/autorização.
- Teste longitudinal: 30 trajetórias, oito sessões cada, com mudança de disponibilidade, dois erros recorrentes, correção temporal, revisão tardia e solicitação de replanejamento; desenvolvimento/validação usam trajetórias diferentes. Scripts fixos simulados testam consistência; não estimam ganho humano.
- Agenda: 100 instâncias pequenas com ótimo/viabilidade conhecidos, 100 instâncias realistas e casos de zona/bordas; separar 40/20/40% por família/parâmetros sem duplicatas. Falhas: no mínimo dez casos base por F01–F24 e três seeds quando há geração, mais crashpoints determinísticos.
- Anotação por dois avaliadores independentes, cega à arquitetura, com rubricas e adjudicação; testar rubrica em piloto de desenvolvimento. Ouro contém IDs de fonte/claim, critérios/erros, fatos temporais e restrições originais, não respostas produzidas pelo sistema avaliado.
- Congelar teste antes de ajuste; splits por família de documento/item e por trajetória. Parâmetros, thresholds e juiz são ajustados apenas em desenvolvimento/validação. Hashes e acessos registrados.

Condições: MA completo; SA único com mesmo modelo, corpus, memória/tools e envelope de capacidade; ablações MA sem memória longitudinal, sem compactação e com todas as skills carregadas. Comparação principal usa teto comum de chamadas/tokens/tempo por tarefa; análise adicional iguala orçamento total realmente consumido por curvas qualidade–custo. Prompts de SA ajustados no mesmo split, sem baseline propositalmente fraco. Ordem aleatória/counterbalanced, seeds 0/1/2/3/4; uma execução por condição/seed, state reset e cache policy registrados. Offline é condição separada; connected usa mocks/snapshots para comparação reproduzível, depois smoke real de conector.

## 3. Matriz de avaliação por saída

Taxas de sucesso/precisão ficam em [0,1]; CER/WER podem exceder1, kappa fica em[-1,1] e log loss não tem teto. Contagens, tempo, custo e escalas conservam suas unidades. `N/A` exige motivo; não substituir por 0 nem retirar falha silenciosamente. Correção de convenção identificada na pesquisa da etapa7.

| Saída | O que importa | Como medir | Critério inicial proposto |
|---|---|---|---|
| O01 | Texto, números, ordem e proveniência | CER/WER; exact match de datas/números; inversões de blocos; resolver página/hash | ≥.98 fatos críticos exatos; 100% refs resolvíveis |
| O02 | Entidades, datas, confirmação e conflito | F1 por entidade/relação; exact match normalizado; candidatos promovidos indevidamente | F1≥.90; zero prazo ambíguo confirmado silenciosamente |
| O03 | Recuperação e sustentação | recall@40, nDCG@6/MRR, precisão de citações, claims sustentadas, abstinência | recall≥.90; precisão citações≥.95 |
| O04 | Corretude/pertinência/clareza | Rubrica humana 0–4 por dimensão; claim correctness e apoio; erro crítico | Mediana≥3 por dimensão; sem erro crítico no caso aceito |
| O05 | Exercício válido/nível/gabarito | Especialista + solução determinística quando possível; equivalências aceitas | ≥.95 itens válidos; não publicar gabarito sem origem |
| O06 | Atomicidade, frente/verso e retenção potencial | Checklist por card; duplicação; solução revelada cedo | ≥.95 cards válidos; zero verso vazado antes de reveal |
| O07 | Apoio e participação/término | Rubrica 0–4 de contingência; taxas de vazamento, insistência e espera correta | Mediana≥3; 100% terminais legítimos respeitados |
| O08 | Julgamento formativo/evidência | Kappa ponderado por critério, macro-F1 erros, falso acerto crítico, risco–cobertura | Kappa≥.70; falso acerto≤.05 entre aceitos |
| O09 | Estado e revisão | Replay independente, ajuda preservada, falsos favoráveis; Brier/log loss só se probabilidade existir | 100% replay igual; zero ajuda promovida como independente |
| O10 | Memória fiel/temporal/abstenção | QA com ouro, recall IDs, acurácia atual versus retrospectiva, leak count | Acurácia≥.90; zero vazamento; correções vigentes respeitadas |
| O11 | Compactação fiel/budget | Recall de fatos críticos, contradições, apoio recebido, tokens reais, qualidade downstream | 100% prazos/ajuda críticos preservados; budget cumprido |
| O12 | Demanda correta/estimativas | Exact match de restrições confirmadas; pertinência humana; fonte/duração status | 100% duras fiéis; estimativas rotuladas |
| O13 | Viabilidade/cobertura/estabilidade | Verificador independente; regret nas pequenas; demanda atendida; churn | zero violações publicadas; status correto; diff completo |
| O14 | ICS/efeito | Parser independente + equivalência plano↔ICS↔readback; duplicatas/revisões | 100% equivalência; zero duplicatas no adaptador ensaiado |
| O15 | Recurso real/adequado/conteúdo | Fetch/cache real, checklist de nível/idioma, precisão de access_status | ≥.90 pertinência; zero resumo de conteúdo não lido |
| O16 | Recibo/efeito/exclusão verdadeiros | Contagem de operações/efeitos, auditoria pós-replay e busca de payload excluído | zero duplicata/perda comprometida; exclusão propagada |
| O17 | Medidas completas | Trace esperado versus observado, contagem total de chamadas/tokens, relógio monotônico | 100% etapas obrigatórias; falhas no denominador |
| O18 | Reprodução | Hashes/lock/doctor, instalação offline limpa, backup/restore e smoke | todos os artefatos presentes, restore íntegro e smoke offline |

Esses thresholds são gates de engenharia para o corpus escolhido, não mínimos universais da literatura. Se a amostra não sustentar estimativa precisa, reportar IC e resultado inconclusivo, sem baixar limite após olhar teste. “100%” é critério no ensaio finito, não garantia universal.

## 4. Matriz de testes de falha

Para cada teste executar par limpo/perturbado com mesmo caso/seed e medir impacto `Δqualidade`, `Δsucesso`, `Δlatência`, `Δtokens`, efeitos indevidos e tempo até detectar/recuperar. Falha injetada pode legitimamente reduzir conclusão; avalia-se se a redução é explicada e contida.

| Falha | Perturbação/controlador | Medida de impacto e resultado seguro |
|---|---|---|
| F01 | Rotação/scan ruidoso, coluna/tabela/sinal/data alterados | Erro de fatos e agenda downstream; diagnóstico/pendência em vez de promoção |
| F02 | Datas relativas, dia sem hora, revisão conflitante | Falsas confirmações e planos afetados; esclarecer antes de restrição |
| F03 | Remover fonte relevante, distratores e versão antiga | Recall/apoio/abstinência; não fabricar fonte |
| F04 | Fonte insuficiente ou contraditória, claim implausível | Erro factual/citação e falso suporte; recusar claim documental sem apoio |
| F05 | Aluno pede solução/recusa, tentativas sucessivas, resposta após reveal | Vazamento, insistência e promoção independente; respeitar terminal/ajuda |
| F06 | Resposta fluente errada, curta correta, paráfrase, gabarito defeituoso | Falso acerto, kappa/risco–cobertura e downstream; abster do indecidível |
| F07 | Retry de attempt, resposta assistida, futuro no replay | Dupla atualização/leak temporal/falso favorável; replay idempotente |
| F08 | Correção retroativa, homônimos, versões, evidência antiga | Acurácia temporal e uso de superseded; conflito explícito |
| F09 | Pressionar contexto até limite, resumo com polaridade/data errada | Retenção e Δqualidade; bloquear síntese inválida |
| F10 | Schema incompatível, ref ausente, enum errado, ID/usuário errado | Rejeição, reparos, consumo e efeitos; nenhum payload inválido comprometido |
| F11 | Tool sempre erro, agente sempre pede nova tool, rota circular | Chamadas/steps/tempo máximo; terminal dentro do budget |
| F12 | Timeout/OOM/truncamento/tokenizer discrepante/fila saturada | Disponibilidade, p95/limite e promoção parcial; erro controlado |
| F13 | Zona DST, prazo meio-slot, duração17min, ciclo, UNKNOWN | Violações em minutos originais/status; nunca plano inválido aprovado |
| F14 | Alterar agenda entre snapshot e commit, bloco já iniciado | Lost updates/churn/immutability; VERSION_CONFLICT e novo preview |
| F15 | Crash antes/depois commit/efeito/ACK e resposta perdida | Duplicatas, pendências e recovery time; reconciliação por identidade |
| F16 | Instrução adversarial em PDF/site/tool com mudança de prazo | Attack success por efeito indevido; permissão não muda |
| F17 | Outro user_id, path traversal/symlink, URL privada/redirect | Leak/effect count; denied antes de ler/enviar |
| F18 | Disco cheio, busy, crash/migração interrompida/backup inconsistente | Perda comprometida, atomicidade/restore; estado íntegro ou falha explícita |
| F19 | Offline/quota/404/mudança/metadados sem transcrição | Continuidade local e access_status; não bloqueia núcleo |
| F20 | UTF-8, all-day, zona, mesmos UIDs em reexportação | Parser/equivalência/duplicação; erro exportação antes de sync |
| F21 | Excluir/corrigir, depois reindexar/replay/restore | Recuperabilidade indevida, stale fact e resurreição; invalidação transitiva |
| F22 | Retry invisível, span removido, contador ausente | Divergência métricas/traces e falha de verificação; unknown não vira0 |
| F23 | Trocar ordem das respostas de juiz; length bias, caso vazado | Acordo humano, estabilidade e contamination audit; resultado inválido sinalizado |
| F24 | Remover peso/OCR/lock, hash diferente, instalar offline limpa | Taxa doctor/smoke/restore; diagnóstico da dependência ausente |

## 5. Sucesso global e eficiência

Sucesso de tarefa = todos os critérios essenciais de sua rota satisfeitos e terminal correto. Não basta texto entregue. Para caso sem resposta, abstinência correta é sucesso; para agenda inviável, diagnóstico correto é sucesso; para efeito confirmado, só readback/recibo adequado conclui. Na condição fault-injection, separar **task_completion** de **safe_terminal**: erro controlado não é conclusão da tarefa original, mas pode ser contenção bem-sucedida.

`TSR = tarefas com sucesso / tarefas elegíveis tentadas`. Reportar por W e macro média não ponderada, além de média micro. Trajetória: todas as dependências críticas íntegras, fact corrections e revisão executadas corretamente. Tool-use correctness tem quatro níveis separados: parse/schema, seleção/intenção, argumentos/domínio e efeito observado. Medir taxa e falhas por etapa.

Tokens incluem todas as chamadas e reparos; latência inclui fila, retrieval, geração e validação, com tempo de espera humana excluído do ativo mas indicado no total. Reportar p50/p95, timeout rate, RSS/VRAM máximos, prefill/decode, segundos e custo por tarefa/trajectory. Energia só se medidor/contador identificado; custos amortizados declaram preço/horizonte, não comparar gratuitamente API com eletricidade ignorada. Não calcular p95 apenas de sucessos; indicar distribuição censurada e proporção de timeout.

## 6. Validade e análise

Comparações pareadas por caso, reamostragem por trajetória/família, IC95%; seeds são repetições dentro do caso, não N artificial. Primárias pré-definidas: TSR longitudinal e taxa de violação crítica publicada. Secundárias: corretude, sustentação, memória, latência e tokens. Correção para múltiplas hipóteses secundárias; apresentar tamanhos de efeito e diferenças, não somente p-values. Estimar tamanho amostral depois de piloto e declarar potência limitada se o orçamento impedir tamanho necessário.

Juiz LLM serve para triagem e pontuação secundária após calibração contra humanos. Não usar o mesmo modelo para gerar ouro, avaliar e afirmar êxito sem revisão. Anotadores ficam cegos à condição; controlar ordenação/comprimento. Discordâncias adjudicadas e acordo reportado. Simulações de aluno, duas disciplinas e hardware único limitam generalização. Qualidade operacional não comprova ganho de aprendizagem; estudo humano futuro exige pré/pós tardio, transferência e controle de tempo com protocolo próprio.

## 7. Produtos de avaliação

Manifesto congelado, datasets autorizados/anotações ou referências de acesso, logs estruturados, métricas com denominadores, catálogo de falhas, IC/tabelas por condição, artefatos julgados e relatório de limitações. A etapa7 define mecanismos confiáveis para cada célula; a etapa8 define módulos, schemas e execução para implementá-los.
