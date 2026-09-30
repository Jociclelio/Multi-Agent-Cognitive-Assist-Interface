"""Compila o relatório, publica PDFs e empacota os documentos com SHA-256."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

from verificar_documentos import ROOT, verify


def run(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True,
                            errors="replace", timeout=180)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)


def build() -> None:
    verify()
    approved_parent = Path("/tmp/opencode")
    if not approved_parent.is_dir():
        raise RuntimeError("Diretório temporário /tmp/opencode ausente")
    with tempfile.TemporaryDirectory(prefix="eduagent-entrega-", dir=approved_parent) as temp:
        out = Path(temp)
        env = os.environ.copy()
        env["BIBINPUTS"] = str(ROOT) + os.pathsep + env.get("BIBINPUTS", "")
        command = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                   f"-output-directory={out}", "fase2_metodologia.tex"]
        run(command, ROOT, env)
        run(["bibtex", "fase2_metodologia"], out, env)
        run(command, ROOT, env)
        run(command, ROOT, env)
        log = (out / "fase2_metodologia.log").read_text(errors="replace")
        bad = ["undefined citations", "undefined references", "There were undefined",
               "Overfull \\hbox", "Overfull \\vbox"]
        if any(term in log for term in bad):
            raise RuntimeError("Compilação com referências/layout pendentes; consultar log: " + log)
        shutil.copy2(out / "fase2_metodologia.pdf", ROOT / "fase2_metodologia.pdf")
    submission = ROOT / "fase2_metodologia_rafael-attilio-agricola_jociclelio-castro-macedo-junior.pdf"
    shutil.copy2(ROOT / "fase2_metodologia.pdf", submission)
    verification = verify()
    verification["compilation"] = "pdflatex + bibtex + pdflatex ×2; sem referência indefinida ou overfull"
    verification["bibliography_style"] = "aasjournal se disponível, plainnat no ambiente verificado"
    (ROOT / "verificacao_documental.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload = [ROOT / "fase2_metodologia.tex", ROOT / "references.bib", ROOT / "fase2_metodologia.pdf",
               submission, ROOT / "README-entrega.md", ROOT / "verificacao_documental.json",
               *sorted((ROOT / "documentos").glob("*.md")),
               *sorted((ROOT / "pesquisa").glob("*.md")),
               *sorted((ROOT / "pesquisa").glob("*.bib")),
               *sorted((ROOT / "scripts").glob("*.py"))]
    # Contexto fornecido pelo usuário: arquivos explícitos, sem percorrer o repo.
    context = {"fase2/template-fase2.tex": ROOT / "template-fase2.tex",
               "fase2/MO810_2026-fase2.pdf": ROOT / "MO810_2026-fase2.pdf",
               "fase1/fase1_proposta.pdf": ROOT.parent / "fase1/fase1_proposta.pdf"}
    files = {"fase2/" + str(p.relative_to(ROOT)): p for p in payload}
    files.update(context)
    digests = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}
    sums = "".join(f"{digest}  {name}\n" for name, digest in sorted(digests.items()))
    (ROOT / "SHA256SUMS.txt").write_text(sums, encoding="utf-8")
    target = ROOT / "eduagent_fase2_entrega.zip"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            archive.write(path, name)
        archive.writestr("SHA256SUMS.txt", sums)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None, "CRC incorreto no ZIP"
        for name, digest in digests.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
    verified = verify(check_delivery=True)
    print(json.dumps({"status": "passed", "pdf": str(ROOT / "fase2_metodologia.pdf"),
                      "zip": str(target), "archive_files": len(files) + 1,
                      "sha256_verified": len(digests), "documentation": verified},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    build()
