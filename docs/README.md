# docs — índice do conhecimento

> Ponto de entrada para agentes de IA e humanos localizarem slides e notebooks da disciplina MO810/MC959.
> Convenção de nomes: **kebab-case, minúsculas, sem acento, sem números, sem espaços**.
> A ordem didática e o pareamento slide ↔ notebook **não estão nos nomes dos arquivos** — estão neste índice (e no `INDEX.yml` espelho-máquina).

## Como navegar

- **Slides:** `disciplina/slides/*.pdf` — teoria do professor (12 aulas).
- **Notebooks:** `notebooks/*.ipynb` — prática correspondente (10 notebooks; nem toda aula teórica tem notebook).
- **Mapa máquina:** [`INDEX.yml`](INDEX.yml) — mesma informação em YAML para agentes.
- **Outros:** `disciplina/PDD-MO810-MC959-1.pdf` (plano da disciplina) e `playground-llmagenticsystem/` (submódulo com sistema multiagente de exemplo, não faz parte da sequência didática).

## Sequência didática (tema como chave)

| Aula | Tema | Slide | Notebook(s) | Sobre |
|------|------|-------|-------------|-------|
| 1 | Introdução a agentes LLM | [introducao.pdf](disciplina/slides/introducao.pdf) | — | Conceitos, definições e panorama de agentes baseados em LLM. |
| 2 | Componentes de agentes | [componentes.pdf](disciplina/slides/componentes.pdf) | — | Percepção, decisão, ação; anatomia de um agente. |
| 3 | Especificando agentes | [especificando-agentes.pdf](disciplina/slides/especificando-agentes.pdf) | — | Como especificar comportamento, papéis e tarefas de agentes. |
| — | Base: LangChain | — | [introducao-langchain.ipynb](notebooks/introducao-langchain.ipynb) | Fundamentos de LangChain (N0); pré-requisito prático, sem slide dedicado. |
| 4 | Introdução ao LangGraph | [introducao-langgraph.pdf](disciplina/slides/introducao-langgraph.pdf) | [introducao-langgraph.ipynb](notebooks/introducao-langgraph.ipynb) | Grafos, estados e primeiros fluxos em LangGraph (N1). |
| 5 | Workflows e orquestração agêntica | [workflows-orquestracao-agentica-langgraph.pdf](disciplina/slides/workflows-orquestracao-agentica-langgraph.pdf) | [langgraph-com-llms.ipynb](notebooks/langgraph-com-llms.ipynb) | LangGraph com LLMs e padrões de orquestração (N2). |
| 6 | Ferramentas e integrações | [ferramentas-integracoes-agentes.pdf](disciplina/slides/ferramentas-integracoes-agentes.pdf) | [ferramentas-integracoes-agentes.ipynb](notebooks/ferramentas-integracoes-agentes.ipynb) | Tools/function-calling e integração de agentes com sistemas externos (N3). |
| 7 | Model Context Protocol (MCP) | [model-context-protocol-mcp.pdf](disciplina/slides/model-context-protocol-mcp.pdf) | [model-context-protocol-mcp.ipynb](notebooks/model-context-protocol-mcp.ipynb) | Protocolo de contexto para conectar modelos a dados e ferramentas (N4). |
| 8 | Skills | [skills.pdf](disciplina/slides/skills.pdf) | [skills.ipynb](notebooks/skills.ipynb) | Empacotamento de capacidades reutilizáveis como skills (N6). |
| 9 | Raciocínio em agentes | [raciocinio-agentes-llm.pdf](disciplina/slides/raciocinio-agentes-llm.pdf) | [raciocinio-agentes-llm.ipynb](notebooks/raciocinio-agentes-llm.ipynb) | Padrões de raciocínio: ReAct, CoT, reflexão (N7). |
| 10 | Planejamento em agentes | [planejamento-agentes-llm.pdf](disciplina/slides/planejamento-agentes-llm.pdf) | [planejamento-agentes-llm.ipynb](notebooks/planejamento-agentes-llm.ipynb) | Decomposição de tarefas e plan-execute (N8). |
| 11 | Memória em agentes | [memoria-agentes-llm.pdf](disciplina/slides/memoria-agentes-llm.pdf) | [memoria-agentes-llm.ipynb](notebooks/memoria-agentes-llm.ipynb) | Memória curta/longa, checkpointers e persistência em LangGraph (N10). |
| 12 | Memória reflexiva | [memoria-reflexiva-agentes-llm.pdf](disciplina/slides/memoria-reflexiva-agentes-llm.pdf) | [memoria-reflexiva-agentes-llm.ipynb](notebooks/memoria-reflexiva-agentes-llm.ipynb) | Memória reflexiva e autoaperfeiçoamento do agente (N11). |

Notas:
- Os códigos N0–N11 nos "Sobre" são os cabeçalhos originais dentro dos notebooks; os nomes de arquivo não os repetem por decisão de normalização.
- Não há notebooks para as aulas 1–3 (teoria introdutória) nem notebook N5/N9 — a lacuna é original do material, não um arquivo faltando.

## Arquivos de apoio

- [PDD-MO810-MC959-1.pdf](disciplina/PDD-MO810-MC959-1.pdf) — plano de desenvolvimento da disciplina.
- `playground-llmagenticsystem/` — submódulo: sistema multiagente de viagens (ReAct vs. plan-execute) usado como playground; ver README próprio.

## Para agentes de IA

1. Leia [`INDEX.yml`](INDEX.yml) para o mapa completo e inequívoco (aula, tema, descrição, paths).
2. Prefira os paths declarados no `INDEX.yml` — nunca infira nomes por número.
3. Futuro `AGENTS.md` (raiz do repo) é a fonte de regras de contribuição; este README é só o índice de conhecimento.
