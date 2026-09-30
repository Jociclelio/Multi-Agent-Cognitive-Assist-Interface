# Etapa 7 — Síntese da pesquisa metodológica de testes

## Documentos integrantes e alcance

A pesquisa foi orquestrada depois do protocolo da etapa6, em duas frentes, com leitura de fontes primárias e documentação oficial em30/09/2026:

- [`../pesquisa/07a_metodos_qualidade.md`](../pesquisa/07a_metodos_qualidade.md): todos O01–O18, quatorze fontes consultadas, fórmulas/denominadores, procedimentos e oráculos.
- [`../pesquisa/07b_metodos_robustez_experimentos.md`](../pesquisa/07b_metodos_robustez_experimentos.md): todos F01–F24 e C18/C19, dezesseis fontes consultadas, injeção de falhas, propriedade/estado, comparação e inferência.

Esses relatórios completos fazem parte da entrega desta etapa. Referências novas: `references_avaliacao_qualidade.bib` e `references_robustez.bib`; chaves já existentes são reutilizadas, não fontes contadas como evidência independente. A bibliografia consolidada remove a duplicata `zheng2023judge`. Pesquisa dirigida não equivale a revisão sistemática ou reprodução dos experimentos publicados.

## Métodos selecionados e referências

| Família de saída/falha | Métodos de implementação do teste | Referências |
|---|---|---|
| O01/O02; F01/F02 | Edit distance CER/WER com normalização preservando sinais; EM crítico; F1 de entidades/relações; autoridade/confirmação por ledger | JiWER, Docling, OCRmyPDF; ontologia e checks são adaptação local |
| O03/O04; F03/F04 | Qrels por evidência original; recall/MRR/nDCG linear; claims atômicas e sustentação conjunta/individual; humanos e NLI auxiliar | BEIR (`thakur2021beir`), ALCE (`gao2023alce`), RAGAs (`es2024ragas`) |
| O05–O08; F05/F06/F23 | Gabarito independente, rubricagem cega, verificação numérica/simbólica, sequência/reveal, kappa linear, risco–cobertura e auditoria de ordem/comprimento | Prometheus, Zheng (`zheng2023judge`), docs scikit-learn |
| O09–O11; F07–F09/F21 | Replay por prefixos, corte bitemporal, tuples de fatos críticos, teste downstream após compactação; Brier/log loss apenas para probabilidade real | LongMemEval, MemGPT, Guo (`guo2017calibration`), pyBKT opcional |
| O12/O13; F13/F14 | Restrições em minutos originais, enumeração independente pequena, vetor objetivo e diff; metamorfismo de disponibilidade e IDs | OR-Tools; Chen (`chen2018metamorphic`); propriedade local |
| O14/O16; F15/F18/F20/F21 | Parser ICS distinto, tuplas canônicas, ledger externo, barreiras/crashpoints, readback e reconciliação | RFC5545/RFC4791, SQLite Testing/WAL, Hypothesis |
| O15; F16/F17/F19 | Ambiente com objetivo legítimo/adversarial, autorização por efeito, proxy de fetch e states de acesso | AgentDojo (`debenedetti2024agentdojo`), MCP; YouTube captions |
| O17/O18; F11/F12/F22/F24 | Watchdog, ledger externo, contadores/tokenizer, censura de latência, ambiente limpo offline e manifesto | AgentBench, BFCL multi-turn, OpenTelemetry, Pineau |
| Todas; F10/F14/F15 | Property-based/stateful, referências inválidas semanticamente, históricos de commits com modelo sequencial | Hypothesis; Porcupine; SQLite Testing |
| C18/C19; F23 | Split por parentesco, pares clean/fault, cluster bootstrap pareado, piloto potência/precisão, margem de não inferioridade | Dror, Field/Welsh, SciPy, Lakens |

## Correções exigidas pela pesquisa

1. CER/WER não estão restritos a[0,1], kappa pode ser negativo e log loss é não limitada. Etapa6 corrigida.
2. DTSTAMP em exportação sem METHOD corresponde à revisão, não necessariamente à criação. Etapa4 corrigida: CREATED preserva criação; DTSTAMP/LAST-MODIFIED são persistidos por revisão e não mudam em retry.
3. “Contradição recente” não tinha definição implementável. Etapa4 agora define a sequência de três tentativas independentes decidíveis mais recentes após erro crítico, com critério crítico marcado na rubrica.
4. Retry idempotente deve conferir operation_id antes de rejeitar expected_version antiga. Etapa4 explicita essa ordem.
5. INFEASIBLE da grade prova inviabilidade do modelo discretizado, não de todo tempo contínuo; diagnóstico precisa informar a limitação.
6. Qualidade condicional a saída não pode ocultar ausência de artefato: disponibilidade e TSR têm denominadores completos. Contenção segura não é conclusão original após falha induzida.

## Decisões para a implementação do testbed

Começar com verificadores determinísticos e fixtures positivas/negativas; só depois usar avaliações semânticas. Validar o avaliador com mutações conhecidas. Instrumentar tanto o sistema quanto o controlador para detectar subcontagem. Separar teste de fronteira, E2E, mock conectado e smoke real. Congelar estimandos, clusters, thresholds/margens e seeds antes do teste final; não inferioridade requer IC compatível com a margem, não apenas p>.05. A etapa8 fixa contratos, registro, comandos e plano de execução.
