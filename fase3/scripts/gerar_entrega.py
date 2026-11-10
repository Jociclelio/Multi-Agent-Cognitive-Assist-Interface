"""Compila o relatório da Fase 3, valida o limite de 3 páginas fora a capa e gera SHA-256 + ZIP."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

from verificar_documentos import ROOT, verify


MAX_TOTAL_PAGES = 4  # 1 página de capa + no máximo 3 páginas de conteúdo


def run(command: list[str], cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=180,
    )
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout + result.stderr


def build() -> None:
    verification = verify(check_delivery=False)
    (ROOT / "verificacao_documental.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    pdflatex_bin = shutil.which("pdflatex")
    bibtex_bin = shutil.which("bibtex")
    tectonic_bin = shutil.which("tectonic")

    if not ((pdflatex_bin and bibtex_bin) or tectonic_bin):
        raise RuntimeError(
            "Compilador LaTeX (pdflatex+bibtex ou tectonic) não encontrado no PATH deste "
            "ambiente. Execute `python3 fase3/scripts/gerar_entrega.py` no ambiente com "
            "TeX Live (pdflatex + bibtex) ou Tectonic instalado para gerar os PDFs e o ZIP."
        )

    approved_parent = Path("/tmp/opencode")
    approved_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="eduagent-fase3-", dir=approved_parent) as temp:
        out = Path(temp)
        env = os.environ.copy()
        env["BIBINPUTS"] = str(ROOT) + os.pathsep + env.get("BIBINPUTS", "")

        if pdflatex_bin and bibtex_bin:
            command = [
                pdflatex_bin,
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={out}",
                "fase3_resultado_pratico.tex",
            ]
            run(command, ROOT, env)
            run([bibtex_bin, "fase3_resultado_pratico"], out, env)
            run(command, ROOT, env)
            run(command, ROOT, env)
            log = (out / "fase3_resultado_pratico.log").read_text(errors="replace")
        else:
            assert tectonic_bin is not None
            shutil.copy2(ROOT / "fase3_resultado_pratico.tex", out / "fase3_resultado_pratico.tex")
            shutil.copy2(ROOT / "references.bib", out / "references.bib")
            log = run(
                [tectonic_bin, "--keep-logs", str(out / "fase3_resultado_pratico.tex")],
                out,
                env,
            )
            log_file = out / "fase3_resultado_pratico.log"
            if log_file.exists():
                log = log_file.read_text(errors="replace")

        bad = [
            "undefined citations",
            "undefined references",
            "There were undefined",
            "Overfull \\hbox",
            "Overfull \\vbox",
        ]
        if any(term in log for term in bad):
            raise RuntimeError(
                "Compilação com referências/layout pendentes; consultar log:\n" + log
            )
        page_match = re.search(r"Output written on .*?\((\d+)\s+pages?", log, re.DOTALL)
        total_pages = int(page_match.group(1)) if page_match else 0
        if total_pages == 0 or total_pages > MAX_TOTAL_PAGES:
            raise RuntimeError(
                f"Limite de páginas violado: total={total_pages} (máximo permitido: "
                f"{MAX_TOTAL_PAGES} páginas totais = 1 capa + 3 páginas de conteúdo)."
            )
        shutil.copy2(
            out / "fase3_resultado_pratico.pdf",
            ROOT / "fase3_resultado_pratico.pdf",
        )

    submission = (
        ROOT
        / "fase3_resultado_pratico_rafael-attilio-agricola_jociclelio-castro-macedo-junior.pdf"
    )
    shutil.copy2(ROOT / "fase3_resultado_pratico.pdf", submission)

    verification = verify(check_delivery=False)
    verification["compilation"] = (
        "pdflatex + bibtex + pdflatex ×2; sem referência indefinida ou overfull"
    )
    verification["total_pages"] = total_pages
    verification["content_pages_excluding_cover"] = total_pages - 1
    verification["max_content_pages_allowed"] = 3
    (ROOT / "verificacao_documental.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    payload = [
        ROOT / "fase3_resultado_pratico.tex",
        ROOT / "references.bib",
        ROOT / "fase3_resultado_pratico.pdf",
        submission,
        ROOT / "roteiro_demo_3min.md",
        ROOT / "README-entrega.md",
        ROOT / "verificacao_documental.json",
        ROOT / "template-fase3.tex",
        ROOT / "MO810_2026-Fase3-Instruções.pdf",
        *sorted((ROOT / "scripts").glob("*.py")),
    ]
    files = {"fase3/" + str(p.relative_to(ROOT)): p for p in payload}
    digests = {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in files.items()
    }
    sums = "".join(f"{digest}  {name}\n" for name, digest in sorted(digests.items()))
    (ROOT / "SHA256SUMS.txt").write_text(sums, encoding="utf-8")

    target = ROOT / "eduagent_fase3_entrega.zip"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            archive.write(path, name)
        archive.writestr("fase3/SHA256SUMS.txt", sums)

    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None, "CRC incorreto no ZIP"
        for name, digest in digests.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name

    verified = verify(check_delivery=True)
    print(
        json.dumps(
            {
                "status": "passed",
                "pdf": str(submission),
                "total_pages": total_pages,
                "content_pages_excluding_cover": total_pages - 1,
                "zip": str(target),
                "archive_files": len(files) + 1,
                "sha256_verified": len(digests),
                "documentation": verified,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    build()
