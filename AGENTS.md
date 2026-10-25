# Repository guidance

## Scope and sources of truth
- This is an academic repository combining course notebooks, phase-2 specification documents, and the implemented EduAgent-OS v0.1 MVP: the five-agent textual core (Curador, Bibliotecário, Tutor, Monitor, Planejador) lives in `eduagent/`, built per `.agents/plans/04-mapa-completo-do-sistema/plan.md` (concluded). Document checks do not establish experimental results; quantitative evaluation (mapa 08: baselines, ablations, metrics) is still pending and its absence must be declared as absence, never filled with estimates.
- For implementation decisions, read `fase2/documentos/04_mapa_completo_do_sistema.md`; for evaluation, read `fase2/documentos/08_mapa_completo_da_testagem.md`. These maps are normative; `fase2/pesquisa/` records rationale and historical alternatives. `fase2/documentos/11_indice_da_entrega.md` indexes the deliverables.
- Use `docs/INDEX.yml` (paths relative to `docs/`) for course materials and slide/notebook pairings. The root README's numbered notebook paths are stale. New course-material filenames follow lowercase, accent-free kebab-case without numeric prefixes; keep the index and `docs/README.md` synchronized.
- `docs/playground-llmagenticsystem/` is a separate Git submodule containing a travel-agent example, not the EduAgent-OS implementation. Its `pyproject.toml`, `uv.lock`, and tests belong to that submodule, not the root project.

## EduAgent-OS v0.1 (implemented MVP)
- Environment is uv-managed: `uv sync` creates `.venv` from `pyproject.toml`/`uv.lock` (Python >= 3.11). Dev tools (pytest, jsonschema) are in the `dev` dependency group, not runtime dependencies.
- Test suite: `uv run pytest tests/` (591 tests as of the task 017 freeze). Per-task test files map to plan-04 tasks (`test_task0NN_*`); gates live in `tests/gates/`. The model gate (task 002) must admit the offline model (Bonsai 2) before tutoring works; `MODEL_NOT_ADMITTED` blocks the tutor by design.
- CLI entry point: `eduagent` (`eduagent.cli:main`); API loopback in `eduagent/api.py`. `manifest.json` is frozen (task 017) with real hashes of skills, BGE-M3 and Docling layout models; treat it as an artifact, not a config file to edit casually.
- Open questions intentionally left pending (do not silently decide): reranker adoption, web search connector (`CONNECTOR_DISABLED` without config), thinking vs non-thinking profile, timezone (`null` pending confirmation of `America/Sao_Paulo`).
- Known debts are documented in the plan-04 task files as optional robustness fixes; check the task records before "fixing" behavior that looks wrong — it may be a deliberate fail-closed choice.

## Document verification and delivery
Run from the repository root:
- Focused documentation check: `python3 fase2/scripts/verificar_documentos.py`. Uses only the Python standard library; checks citations, required sections, IDs, stage files, and local links.
- Include delivery-file existence checks: `python3 fase2/scripts/verificar_documentos.py --check-delivery`. This does not check PDF freshness or checksums.
- Rebuild/publish a changed phase-2 delivery: `python3 fase2/scripts/gerar_entrega.py`. It validates first, runs `pdflatex -> bibtex -> pdflatex -> pdflatex`, rejects undefined citations/references and overfull boxes, then validates ZIP CRCs and SHA-256 digests.
- The delivery build requires existing `/tmp/opencode/`, `pdflatex`, `bibtex`, and the TeX packages listed in `fase2/README-entrega.md`; no LangChain installation is needed. It builds in a temporary directory but overwrites both phase-2 PDFs, `verificacao_documental.json`, `SHA256SUMS.txt`, and the ZIP. ZIPs are Git-ignored.
- In `fase2/fase2_metodologia.tex`, use `\cite{...}` or `\citeonline{...}`, not `\citep`/`\citet` in the body; keep exactly one `\bibliography{references}` and unique, case-sensitive keys in `fase2/references.bib`. The source selects `aasjournal.bst` if available, otherwise `plainnat`.
- The pytest suite under `tests/` is the system-test suite for EduAgent-OS (requires `uv sync` and the pinned offline model/runtime); it is separate from the document verifier, which remains a stdlib-only check.

## Notebook setup and conventions
- Base notebook environment: `python3 -m venv .venv`, `source .venv/bin/activate`, `python -m pip install -r requirements.txt`; launch, e.g., `jupyter notebook docs/notebooks/introducao-langchain.ipynb`. The EduAgent-OS environment is separate: use `uv sync` as above, not the root `requirements.txt`.
- Check each notebook's setup cells for extra dependencies: the memory notebooks require `langgraph-checkpoint-sqlite` (and reflective memory uses `numpy`), absent from root requirements; the MCP notebook specifies `mcp>=1.29,<2`, stricter than root requirements.
- Inspect the notebook's `PROVEDOR`/model-selection cell before execution. Local llama-cpp examples use `LLAMA_CPP_BASE_URL=http://localhost:8079/v1` and `LLAMA_CPP_MODEL=bonsai2-pq2-0`; memory/reasoning/planning examples also have cloud-provider configurations. Notebooks call `load_dotenv()`; a local `docs/notebooks/.env` may override the expected root-file discovery.
- Preserve Portuguese academic prose; commit messages follow concise, action-oriented Portuguese per the root README. Do not present proposed thresholds/budgets or future experiments as measured results.

## Agent workflow (plan → tasks → execution → review)
Multi-agent work in this repository follows the tool-agnostic protocol in `.agents/protocolo.md`; both OpenCode and Google Antigravity read this file, so start there. Skills (`planer`, `task-writer`, `task-executor`) live in `.agents/skills/` in the open SKILL.md format; plans go to `.agents/plans/<slug>/plan.md` and tasks to `.agents/tasks/<slug>/<NNN-descrição>.md`. Key invariants: one task per session, the executor never reviews its own delivery, review quorum of three distinct independent models (contract in `.agents/contrato-revisor.md`), delivery and record commits kept separate, and master decisions limited to fechar/corrigir/reiniciar/repartir. Version plan and tasks before any implementation commits. Note: inside `.agents/`, the names `rules/` and `AGENTS.md` are reserved by Antigravity — do not use them for other purposes.
- Current progress: plan 04 (implementation) is concluded; plan 05 (fluxos/resultados/falhas W01–W12, O01–O18, F01–F24) has tasks 001–005 created and pending execution; plans 06–11 have plans but no tasks yet.
