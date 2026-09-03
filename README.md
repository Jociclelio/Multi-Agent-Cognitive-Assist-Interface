# MO810A / MC959A — Sistemas Multiagentes com Modelos de Linguagem

**IC/UNICAMP — 2026 — Prof. Dr. Julio Cesar dos Reis**

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

## Convenções

- Não versionar `.env` — ver `.env.example`
- Commits em português, mensagens curtas e objetivas
