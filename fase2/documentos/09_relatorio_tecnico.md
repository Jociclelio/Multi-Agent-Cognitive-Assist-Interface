# Etapa 9 — Relatório de desenvolvimento e avaliação

O relatório científico completo desta etapa é [`../fase2_metodologia.tex`](../fase2_metodologia.tex), com bibliografia [`../references.bib`](../references.bib). A versão PDF de leitura é [`../fase2_metodologia.pdf`](../fase2_metodologia.pdf).

O texto segue a capa, geometria, corpo12pt, rodapé e seções de `template-fase2.tex`: Visão Geral da Metodologia; Conjunto de Dados para a Avaliação; Arquitetura Multiagente; Orquestração e Uso de Ferramentas; Procedimentos de Avaliação; Apêndice; Referências. A figura é TikZ e não depende de imagem externa. `natbib` usa `\cite` e disponibiliza `\citeonline`; a chamada final é `\bibliography{references}`. O estilo `aasjournal` do template é escolhido se disponível; neste ambiente foi usado `plainnat`, autor–ano, porque aquele estilo não estava disponível.

O relatório descreve captura/preparação de dados, cinco agentes, modelo local e gate de admissão, contratos, skills, memória/contexto, política pedagógica→demanda, solver, ferramentas, transações/efeitos e sequência de implementação. A avaliação apresenta dados/ouro/splits, baselines/ablações, métricas e gates propostos, falhas, estatística/validade e matrizes completas W/O/F.

Os parâmetros não representam resultados de execução do EduAgent-OS. A seleção/configuração final de hardware/runtime, autorização/anotação dos dados e piloto de calibração/potência são passos metodológicos definidos, ainda não realizados. O documento de auditoria da etapa10 registra o alcance de verificação das referências. Compilação e integridade documental são verificações desta entrega, distintas dos experimentos futuros do sistema.
