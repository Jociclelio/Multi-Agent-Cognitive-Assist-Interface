# Plano: Entrega de Resultados Práticos da Fase 3 (MO810A/MC959A)

Estado: concluído (artefatos de código/LaTeX/verificador prontos; aguardando compilação TeX e vídeo demo pelo usuário)

## Objetivo
Consolidar e produzir todos os artefatos documentais, de reprodutibilidade e de verificação exigidos pela **Fase 3 — Resultado Prático** (`fase3/MO810_2026-Fase3-Instruções.pdf` e `fase3/template-fase3.tex`) sobre o MVP implementado e congelado do **EduAgent-OS v0.1** (`eduagent/`, `ui/`, `schemas/`, `manifest.json`), incluindo: (1) atualização de `README.md` e `.env.example` para reprodutibilidade completa da release `fase3` com exemplo de entrada e saída; (2) roteiro cronometrado de demonstração de até 3 minutos (`fase3/roteiro_demo_3min.md`); (3) relatório técnico LaTeX (`fase3/fase3_resultado_pratico.tex` e `fase3/references.bib`) com no máximo 3 páginas fora a capa; e (4) scripts determinísticos de verificação e compilação (`fase3/scripts/verificar_documentos.py` e `fase3/scripts/gerar_entrega.py`).

## Abordagem
1. Preservar intocados o núcleo implementado (`eduagent/`, `ui/`, `schemas/`, `eduagent/skills/`), o manifesto congelado (`manifest.json`) e o lockfile (`uv.lock`), extraindo todos os dados técnicos diretamente dessas fontes autoritativas e de `eval/relatorio-testes-mvp.md`.
2. Atualizar `README.md` e `.env.example` na raiz para atender integralmente ao requisito (3) das instruções da Fase 3: pré-requisitos, instalação via `uv sync --frozen`, instruções para obtenção dos modelos não versionados (`Ternary-Bonsai-2-27B-PTQ1_0.gguf`, `BAAI/bge-m3`, `Docling`), configuração de parâmetros, comandos de execução (CLI e Web UI) e um exemplo concreto de entrada e saída ponta a ponta.
3. Redigir `fase3/fase3_resultado_pratico.tex` a partir de `fase3/template-fase3.tex` com página de capa separada (`\newpage` + `\setcounter{page}{1}`) seguida de no máximo 3 páginas de conteúdo cobrindo as 7 seções obrigatórias (`\ref{sec:visao-geral}` a `\ref{sec:resultados-praticos}`), a seção não numerada de Declaração de uso de IA generativa (PDD §7.2) e `\bibliography{references}` (`plainnat`), sem caixas `\dica{...}` e usando exclusivamente `\cite{...}` e `\citeonline{...}`.
4. Implementar `fase3/scripts/verificar_documentos.py` (stdlib-only) e `fase3/scripts/gerar_entrega.py` (build isolado em `/tmp/opencode/`), validando zero referências indefinidas, zero `Overfull \hbox`/`\vbox`, contagem de páginas ($\le 3$ páginas fora a capa), checksums `SHA256SUMS.txt` e pacote `eduagent_fase3_entrega.zip`.

## Escopo
- **Incluído:** `README.md`, `.env.example`, `fase3/roteiro_demo_3min.md`, `fase3/fase3_resultado_pratico.tex`, `fase3/references.bib`, `fase3/README-entrega.md`, `fase3/scripts/verificar_documentos.py`, `fase3/scripts/gerar_entrega.py`, `fase3/verificacao_documental.json` (e geração de `fase3_resultado_pratico.pdf`, `fase3_resultado_pratico_rafael-attilio-agricola_jociclelio-castro-macedo-junior.pdf` e `SHA256SUMS.txt` via `gerar_entrega.py`).
- **Excluído:** alterações funcionais no código de `eduagent/` ou `ui/`, modificação de `manifest.json` ou `uv.lock`, e execução de experimentos comparativos/ablações da Fase 4 (Mapa 08).

## Contexto
- `fase3/MO810_2026-Fase3-Instruções.pdf` — instruções oficiais da Fase 3.
- `fase3/template-fase3.tex` — template LaTeX oficial com as 7 seções numeradas obrigatórias.
- `manifest.json` — registro congelado de versões, hashes SHA-256 do modelo Bonsai 2, runtime PrismML `llama.cpp`, `BGE-M3`, `Docling`, `skills` e pacotes Python.
- `eval/relatorio-testes-mvp.md` e `eval/ensaio_longitudinal.py` — evidências executáveis do ensaio longitudinal de 15 passos, correções realizadas e aceite funcional (§13.235).
- `eduagent/config.py`, `eduagent/api.py`, `eduagent/cli.py`, `eduagent/graph.py` — implementação real da resolução automática de timezone, API/UI loopback e orquestração em grafo.

## Critérios de conclusão
- `README.md` e `.env.example` documentam a arquitetura implementada, instalação (`uv sync --frozen`), obtenção dos modelos locais, execução CLI/UI e exemplo completo de entrada e saída.
- `fase3/roteiro_demo_3min.md` descreve o roteiro cronometrado de até 3 minutos cobrindo os 5 agentes em operação.
- `python3 fase3/scripts/verificar_documentos.py` retorna `"status": "passed"` (14 referências únicas, 14 citadas, 7 seções obrigatórias, declaração de IA presente).
- `fase3/scripts/gerar_entrega.py` está pronto para compilar `fase3_resultado_pratico.pdf` e `fase3_resultado_pratico_rafael-attilio-agricola_jociclelio-castro-macedo-junior.pdf` na máquina com TeX Live (`pdflatex` + `bibtex`) ou Tectonic instalado.

## Questões abertas
Nenhuma pendência de código ou redação; restam apenas a compilação TeX na máquina local da dupla (o container atual não possui `pdflatex`/`tectonic` instalado no PATH) e a gravação do vídeo demo ($\le 3$ min).

## Tasks
1. [001-readme-reprodutibilidade-env-e-roteiro-demo.md](../../tasks/12-fase3-resultados-praticos/001-readme-reprodutibilidade-env-e-roteiro-demo.md) — depende de: nenhuma — estado: concluída
2. [002-relatorio-fase3-secoes-1-a-4.md](../../tasks/12-fase3-resultados-praticos/002-relatorio-fase3-secoes-1-a-4.md) — depende de: 001 — estado: concluída
3. [003-relatorio-fase3-secoes-5-a-7-ajustes-e-declaracao-ia.md](../../tasks/12-fase3-resultados-praticos/003-relatorio-fase3-secoes-5-a-7-ajustes-e-declaracao-ia.md) — depende de: 002 — estado: concluída
4. [004-verificador-build-pdf-3paginas-e-validacao-final.md](../../tasks/12-fase3-resultados-praticos/004-verificador-build-pdf-3paginas-e-validacao-final.md) — depende de: 003 — estado: concluída (verificador aprovado; compilação PDF pendente de TeX Live na máquina do usuário)
