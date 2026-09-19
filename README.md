# MO810A / MC959A — Sistemas Multiagentes com Modelos de Linguagem

**IC/UNICAMP — 2026 — Prof. Dr. Julio Cesar dos Reis**

## Dupla

- Rafael Attilio Agricola — RA 249245
- Jociclelio Castro Macedo Junior — RA 231722

## Estrutura

```
.
├── docs/
│   ├── disciplina/               # ementa e PDD oficiais (MO810_2026.pdf, PDD-MO810-MC959-1.pdf)
│   └── notebooks/                # notebooks de referência da disciplina (não avaliativos)
│       ├── 00-introducao-langchain.ipynb
│       ├── 01-langgraph-com-llms.ipynb
│       ├── 03-ferramentas.ipynb
│       ├── 04-model-context-protocol.ipynb
│       └── 05-skills.ipynb
├── proposta/fase1/               # proposta inicial (LaTeX: template + rascunhos + references.bib)
│   ├── template-fase1.tex
│   ├── fase1_rascunho_agricola.tex
│   └── fase1_rascunho_jociclelio.tex
├── requirements.txt
└── .env.example
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # preencher chaves
```

Rodar notebooks:

```bash
jupyter notebook docs/notebooks/00-introducao-langchain.ipynb
```

## Proposta

Proposta em `proposta/fase1/` (LaTeX). Compilar:

```bash
cd proposta/fase1 && pdflatex fase1_rascunho_jociclelio.tex
```

### Slides da fase 1

- Fonte Beamer: `proposta/fase1/fase1_slides.tex`.
- Apresentação: `proposta/fase1/fase1_slides.pdf` (16:9; 9 slides principais e 1 de referências).
- Roteiro previsto para aproximadamente 4min50s, com tempos sugeridos nos comentários do `.tex`.

Compilar a partir da raiz do repositório com Tectonic:

```bash
tectonic proposta/fase1/fase1_slides.tex
```

Para a entrega, usar os nomes exigidos pela disciplina:

- Slides: `fase1_slides_rafael-attilio-agricola_jociclelio-castro-macedo-junior.pdf`.
- Relatório: `fase1_relatorio_rafael-attilio-agricola_jociclelio-castro-macedo-junior.pdf`.

## Convenções

- Não versionar `.env` — ver `.env.example`
- Commits em português, mensagens curtas e objetivas
