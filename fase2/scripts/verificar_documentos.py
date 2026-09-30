"""Verifica os artefatos documentais; não executa testes do EduAgent-OS."""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def verify(check_delivery: bool = False) -> dict:
    tex = (ROOT / "fase2_metodologia.tex").read_text(encoding="utf-8")
    bib = (ROOT / "references.bib").read_text(encoding="utf-8")
    keys = re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", bib)
    counts = collections.Counter(keys)
    assert all(v == 1 for v in counts.values()), "Chave BibTeX duplicada"
    cited = {key.strip() for group in re.findall(r"\\cite(?:online)?(?:\[[^]]*\])?\{([^}]+)\}", tex)
             for key in group.split(",")}
    assert cited <= set(keys), f"Citações ausentes: {cited - set(keys)}"
    assert tex.count(r"\bibliography{references}") == 1
    assert not re.search(r"\\(?:citep|citet)\{", tex), "Usar cite/citeonline no corpo"
    assert "<Título do projeto>" not in tex and "<Aluno" not in tex
    sections = ["Visão Geral da Metodologia", "Conjunto de Dados para a Avaliação",
                "Arquitetura Multiagente", "Orquestração e Uso de Ferramentas", "Procedimentos de Avaliação"]
    assert all(r"\section{" + s + "}" in tex for s in sections)
    docs = ROOT / "documentos"
    for n in range(1, 12):
        assert len(list(docs.glob(f"{n:02d}_*.md"))) == 1, f"Etapa {n} ausente/duplicada"
    requirements = (docs / "02_componentes_e_requisitos.md").read_text(encoding="utf-8")
    catalog = (docs / "05_fluxos_resultados_e_falhas.md").read_text(encoding="utf-8")
    testmap = (docs / "08_mapa_completo_da_testagem.md").read_text(encoding="utf-8")
    for prefix, n, text in [("C", 20, requirements), ("W", 12, catalog),
                            ("O", 18, catalog), ("F", 24, catalog)]:
        ids = {f"{prefix}{i:02d}" for i in range(1, n + 1)}
        present = set(re.findall(rf"\b{prefix}\d{{2}}\b", text))
        assert ids <= present, f"IDs ausentes: {ids - present}"
    assert all(f"| C{i:02d}" in testmap for i in range(1, 21))
    # Cada F e O deve ter linha própria nos relatórios integrantes, não apenas faixa.
    research = ROOT / "pesquisa"
    quality = (research / "07a_metodos_qualidade.md").read_text(encoding="utf-8")
    robustness = (research / "07b_metodos_robustez_experimentos.md").read_text(encoding="utf-8")
    assert all(re.search(rf"### O{i:02d}\b", quality) for i in range(1, 19))
    assert all(f"| F{i:02d} |" in robustness for i in range(1, 25))
    checked_links, pending = 0, []
    delivery_names = {"fase2_metodologia.pdf", "eduagent_fase2_entrega.zip",
                      "fase2_metodologia_rafael-attilio-agricola_jociclelio-castro-macedo-junior.pdf"}
    for path in [*docs.glob("*.md"), ROOT / "README-entrega.md"]:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (path.parent / target.split("#", 1)[0]).resolve()
            if not resolved.exists() and resolved.name in delivery_names and not check_delivery:
                pending.append(resolved.name)
                continue
            assert resolved.exists(), f"Link ausente em {path.name}: {target}"
            checked_links += 1
    result = {"status": "passed", "scope": "documentação; não experimentos do sistema",
              "bibliography_unique": len(keys), "cited_unique": len(cited),
              "uncited_unique": len(set(keys) - cited), "missing_citations": [],
              "steps": 11, "components": 20, "flows": 12, "outputs": 18, "failures": 24,
              "local_links_checked": checked_links, "delivery_pending": sorted(set(pending))}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-delivery", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.check_delivery), ensure_ascii=False, indent=2))
