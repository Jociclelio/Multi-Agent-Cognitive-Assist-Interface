# Repository guidance

## Scope and sources of truth
- This is currently an academic documentation/notebook repository. EduAgent-OS and its testbed are specifications for future implementation, not a runnable application; document checks do not establish experimental results.
- For implementation decisions, read `fase2/documentos/04_mapa_completo_do_sistema.md`; for evaluation, read `fase2/documentos/08_mapa_completo_da_testagem.md`. These maps are normative; `fase2/pesquisa/` records rationale and historical alternatives. `fase2/documentos/11_indice_da_entrega.md` indexes the deliverables.
- Use `docs/INDEX.yml` (paths relative to `docs/`) for course materials and slide/notebook pairings. The root README's numbered notebook paths are stale. New course-material filenames follow lowercase, accent-free kebab-case without numeric prefixes; keep the index and `docs/README.md` synchronized.
- `docs/playground-llmagenticsystem/` is a separate Git submodule containing a travel-agent example, not the EduAgent-OS implementation. Its `pyproject.toml`, `uv.lock`, and tests belong to that submodule, not the root project.

## Document verification and delivery
Run from the repository root:
- Focused documentation check: `python3 fase2/scripts/verificar_documentos.py`. Uses only the Python standard library; checks citations, required sections, IDs, stage files, and local links.
- Include delivery-file existence checks: `python3 fase2/scripts/verificar_documentos.py --check-delivery`. This does not check PDF freshness or checksums.
- Rebuild/publish a changed phase-2 delivery: `python3 fase2/scripts/gerar_entrega.py`. It validates first, runs `pdflatex -> bibtex -> pdflatex -> pdflatex`, rejects undefined citations/references and overfull boxes, then validates ZIP CRCs and SHA-256 digests.
- The delivery build requires existing `/tmp/opencode/`, `pdflatex`, `bibtex`, and the TeX packages listed in `fase2/README-entrega.md`; no LangChain installation is needed. It builds in a temporary directory but overwrites both phase-2 PDFs, `verificacao_documental.json`, `SHA256SUMS.txt`, and the ZIP. ZIPs are Git-ignored.
- In `fase2/fase2_metodologia.tex`, use `\cite{...}` or `\citeonline{...}`, not `\citep`/`\citet` in the body; keep exactly one `\bibliography{references}` and unique, case-sensitive keys in `fase2/references.bib`. The source selects `aasjournal.bst` if available, otherwise `plainnat`.
- No root test/lint/typecheck runner is configured; the document verifier is not a system-test suite.

## Notebook setup and conventions
- Base notebook environment: `python3 -m venv .venv`, `source .venv/bin/activate`, `python -m pip install -r requirements.txt`; launch, e.g., `jupyter notebook docs/notebooks/introducao-langchain.ipynb`.
- Check each notebook's setup cells for extra dependencies: the memory notebooks require `langgraph-checkpoint-sqlite` (and reflective memory uses `numpy`), absent from root requirements; the MCP notebook specifies `mcp>=1.29,<2`, stricter than root requirements.
- Inspect the notebook's `PROVEDOR`/model-selection cell before execution. Local llama-cpp examples use `LLAMA_CPP_BASE_URL=http://localhost:8079/v1` and `LLAMA_CPP_MODEL=bonsai2-pq2-0`; memory/reasoning/planning examples also have cloud-provider configurations. Notebooks call `load_dotenv()`; a local `docs/notebooks/.env` may override the expected root-file discovery.
- Preserve Portuguese academic prose; commit messages follow concise, action-oriented Portuguese per the root README. Do not present proposed thresholds/budgets or future experiments as measured results.
