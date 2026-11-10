# EduAgent-OS — Entrega de Resultados Práticos da Fase 3

**Dupla:** Rafael Attilio Agricola (`RA 249245`) e Jociclelio Castro Macedo Junior (`RA 231722`)  
**Disciplina:** MO810A/MC959A — Sistemas Multiagentes com Modelos de Linguagem (IC/UNICAMP, 2026)

## Arquivos principais da pasta `fase3/`

- [Relatório PDF (nome oficial de submissão)](fase3_resultado_pratico_rafael-attilio-agricola_jociclelio-castro-macedo-junior.pdf) — capa + até 3 páginas de conteúdo técnico.
- [Relatório PDF (cópia local)](fase3_resultado_pratico.pdf).
- [Fonte LaTeX](fase3_resultado_pratico.tex) e [Bibliografia BibTeX](references.bib).
- [Roteiro de Demonstração de 3 Minutos](roteiro_demo_3min.md).
- [Template Oficial da Fase 3](template-fase3.tex) e [Enunciado Oficial](MO810_2026-Fase3-Instruções.pdf).
- [Metadados de Verificação Documental](verificacao_documental.json) e [Checksums SHA-256](SHA256SUMS.txt).
- Scripts de verificação e empacotamento: [verificar_documentos.py](scripts/verificar_documentos.py) e [gerar_entrega.py](scripts/gerar_entrega.py).

## Compilação e Verificação Mecânica

A partir da raiz do repositório:

```bash
python3 fase3/scripts/verificar_documentos.py
python3 fase3/scripts/gerar_entrega.py
```

O script `gerar_entrega.py` valida as 7 seções obrigatórias do template, a declaração de uso de IA generativa, a higiene de citações (`\cite`/`\citeonline`), a ausência de caixas `\dica{...}`, a compilação `pdflatex -> bibtex -> pdflatex -> pdflatex` sem referências indefinidas ou *overfull boxes*, o limite estrito de **no máximo 3 páginas fora a capa** (total $\le 4$ páginas incluindo a capa), os digests em `SHA256SUMS.txt` e o pacote `eduagent_fase3_entrega.zip`.

