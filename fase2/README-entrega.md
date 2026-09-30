# EduAgent-OS — Entrega metodológica da fase 2

**Dupla:** Rafael Attilio Agricola (RA249245) e Jociclelio Castro Macedo Junior (RA231722). **Disciplina:** MO810A/MC959A, IC/UNICAMP,2026.

## Arquivos principais

- [Pacote íntegro ZIP](eduagent_fase2_entrega.zip).
- [Relatório PDF](fase2_metodologia.pdf),31páginas na compilação verificada.
- [PDF com nome de submissão](fase2_metodologia_rafael-attilio-agricola_jociclelio-castro-macedo-junior.pdf).
- [Fonte LaTeX](fase2_metodologia.tex) e [bibliografia](references.bib).
- [Índice de todas as onze etapas](documentos/11_indice_da_entrega.md).
- [Mapa de produção](documentos/04_mapa_completo_do_sistema.md) e [mapa de testes](documentos/08_mapa_completo_da_testagem.md).
- [Auditoria bibliográfica](documentos/10_auditoria_de_referencias.md).

## Conteúdo e estatuto

Vinte componentes, cinco agentes, doze famílias de fluxo, dezoito saídas e vinte e quatro falhas. Pesquisa dirigida em quatro relatórios integrais, com artigos, documentação oficial, métodos, alternativas e registro de limitações de acesso. Bibliografia consolidada:56fontes únicas,44citadas no relatório. As etapas3/7 têm síntese e pesquisas integrantes; todas são incluídas no ZIP.

Os mapas são especificações para implementação futura. Hardware/runtime, corpus autorizado, anotação, calibração e experimentos ainda devem ser executados conforme os protocolos; não se afirmam desempenho, superioridade multiagente ou ganho de aprendizagem já demonstrados. Thresholds/budgets são propostas congeláveis. Modelo local candidato identificado, estado observado sem probabilidade de domínio, ICS obrigatório e sync/web opcionais.

## Compilação e integridade

Requisitos do relatório: Python3, pdflatex/BibTeX e TeX Live com babel português, natbib, amsmath, TikZ, booktabs, longtable, xurl e hyperref. Não é necessário instalar o stack do sistema multiagente para ler/compilar esta entrega.

Da raiz do projeto:

```bash
python3 fase2/scripts/verificar_documentos.py
python3 fase2/scripts/gerar_entrega.py
```

O build usa diretório temporário, resolve bibliografia, repete LaTeX para fechar referências, confere warnings relevantes e publica PDF+ZIP/checksums. No ambiente atual `aasjournal.bst` não está instalado; o fonte usa fallback `plainnat`, mantendo autor–ano. Não há necessidade de `--shell-escape`. Arquivos de build não poluem o projeto.

Os diagramas Markdown são Mermaid; o PDF tem figura TikZ. Um leitor sem Mermaid continua tendo descrição textual completa. `verificacao_documental.json` contém chaves/contagens, cobertura IDs, links locais e status de integridade. O ZIP inclui `SHA256SUMS.txt`; `python3 fase2/scripts/gerar_entrega.py` valida o conteúdo do arquivo após gravá-lo.

## Hierarquia e decisões auditadas

Mapas4/8 são normativos; pesquisas registram fundamentos/histórico. A auditoria independente fechou snapshots/revisão, omissões nas rubricas, avaliação por tópico/correção, política evidência→demanda, atividades/dependências, discretização/incumbent, identidade de eventos, exclusão e cobertura experimental. Veja mapa4 §15 e mapa8 §12. Os métodos e cifras não são transportados da literatura como prova de eficácia do EduAgent-OS.

Todos os documentos estão no workspace. Google Drive não está conectado; o ZIP está pronto para upload manual.
