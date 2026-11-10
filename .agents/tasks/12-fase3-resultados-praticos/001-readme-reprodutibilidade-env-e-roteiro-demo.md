# Task 001: Atualização de README.md, .env.example e Roteiro de Demonstração (3 min)

Estado: concluída
Depende de: nenhuma
Origem: nenhuma

## Prompt
Atualizar `README.md` e `.env.example` na raiz do repositório para cumprir integralmente os requisitos de reprodutibilidade da release `fase3` (`fase3/MO810_2026-Fase3-Instruções.pdf`, item 3), e criar `fase3/roteiro_demo_3min.md` com o roteiro técnico cronometrado (máximo de 3 minutos) para a gravação do vídeo de demonstração da execução ponta a ponta.

## Contexto
- `fase3/MO810_2026-Fase3-Instruções.pdf` — exige README com requisitos, instalação, configuração, comando de execução, instruções para obtenção de dados/modelos não versionados e exemplo de entrada e saída.
- `README.md` e `.env.example` — arquivos da raiz atualizados.
- `manifest.json` e `config/default.yaml` — hashes, revisões e parâmetros congelados do MVP.
- `eduagent/cli.py`, `eduagent/api.py`, `eduagent/config.py` e `eval/ensaio_longitudinal.py` — superfície executável real do sistema.

## Corretude
- [x] C1 — `README.md` contém seções explícitas de requisitos, instalação com `uv sync --frozen`, instruções para obter os modelos não versionados (`Bonsai 2`, `BGE-M3`, `Docling`), configuração (`.env.example` e `config/default.yaml`), comandos de execução (CLI 14 subcomandos + Web UI `--serve-ui`) e exemplo concreto de entrada e saída.
- [x] C2 — `.env.example` documenta as variáveis locais (`LLAMA_CPP_BASE_URL`, `LLAMA_CPP_MODEL`, `EDUAGENT_TIMEZONE`, `EDUAGENT_DATA_ROOT`, `EDUAGENT_API_PORT`) sem conter chaves reais.
- [x] C3 — `fase3/roteiro_demo_3min.md` existe e detalha o roteiro cronometrado de até 3 minutos cobrindo os 5 agentes (Curador, Bibliotecário, Tutor, Monitor e Planejador) na CLI e na Web UI.

## Execução
- Modelo: Gemini 4 Argon (Low)
- Base: `47204e8d77cf30df571415ee6ed55db22a29918f`
- Entrega: artefatos gravados no workspace (`README.md`, `.env.example`, `fase3/roteiro_demo_3min.md`)
- Arquivos da entrega: `README.md`, `.env.example`, `fase3/roteiro_demo_3min.md`
- Evidências: `python3 fase3/scripts/verificar_documentos.py` validou todos os marcadores obrigatórios em `README.md`, `.env.example` e os links em `fase3/roteiro_demo_3min.md`.

## Notas

### Dificuldade esperada
3/10 — Consolidação documental extensa, mas todos os comandos, portas e contratos já existem e estão verificados no código.

### Dificuldade sentida
3/10 — Atualização direta a partir das fontes congeladas do repositório.

Plano: [plan.md](../../plans/12-fase3-resultados-praticos/plan.md)
