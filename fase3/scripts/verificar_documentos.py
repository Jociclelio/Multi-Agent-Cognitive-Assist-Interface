"""Verifica os artefatos documentais da Fase 3; usa apenas a biblioteca padrão."""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent

REQUIRED_SECTIONS = [
    "Visão Geral da Implementação e Arquitetura em Operação",
    "Tecnologias, Frameworks e Infraestrutura de Execução",
    "Especificação Técnica dos Agentes",
    "Padrão de Orquestração, Protocolo de Mensagens e Uso de Ferramentas",
    "Mecanismos de Memória, Limites de Execução, Custo e Tratamento de Falhas",
    "Ajustes Realizados em Relação à Proposta Original e Justificativas",
    "Execução Ponta a Ponta e Resultados Práticos Obtidos",
]

AI_DECLARATION_TITLE = "Declaração de uso de IA generativa no processo de elaboração"


def verify(check_delivery: bool = False) -> dict:
    tex_path = ROOT / "fase3_resultado_pratico.tex"
    bib_path = ROOT / "references.bib"
    demo_path = ROOT / "roteiro_demo_3min.md"
    readme_entrega_path = ROOT / "README-entrega.md"
    root_readme_path = REPO_ROOT / "README.md"
    env_example_path = REPO_ROOT / ".env.example"

    assert tex_path.exists(), "fase3_resultado_pratico.tex ausente"
    assert bib_path.exists(), "fase3/references.bib ausente"
    assert demo_path.exists(), "fase3/roteiro_demo_3min.md ausente"
    assert readme_entrega_path.exists(), "fase3/README-entrega.md ausente"
    assert root_readme_path.exists(), "README.md da raiz ausente"
    assert env_example_path.exists(), ".env.example ausente"

    tex = tex_path.read_text(encoding="utf-8")
    bib = bib_path.read_text(encoding="utf-8")
    root_readme = root_readme_path.read_text(encoding="utf-8")

    # 1. Chaves BibTeX únicas e citações resolvidas no corpo do documento
    body = tex.split(r"\begin{document}", 1)[-1]
    keys = re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", bib)
    counts = collections.Counter(keys)
    assert all(v == 1 for v in counts.values()), f"Chave BibTeX duplicada: {counts}"
    cited = {
        key.strip()
        for group in re.findall(r"\\cite(?:online)?(?:\[[^]]*\])?\{([^}]+)\}", body)
        for key in group.split(",")
    }
    assert cited <= set(keys), f"Citações ausentes no .bib: {cited - set(keys)}"
    assert body.count(r"\bibliography{references}") == 1, "Deve haver exatamente um \\bibliography{references}"
    assert not re.search(r"\\(?:citep|citet)\{", body), "Usar apenas \\cite ou \\citeonline no corpo"

    # 2. Ausência de placeholders e caixas \dica{...} do template
    for forbidden in ("[Título do Projeto]", "Nome Completo", "RA XXXXXX", r"\dica{"):
        assert forbidden not in tex, f"Placeholder/instrução do template remanescente: {forbidden}"

    # 3. Presença das 7 seções numeradas obrigatórias e da declaração de IA
    for section in REQUIRED_SECTIONS:
        assert r"\section{" + section + "}" in tex, f"Seção obrigatória ausente: {section}"
    assert r"\section*{" + AI_DECLARATION_TITLE + "}" in tex, "Declaração de uso de IA generativa ausente"

    # 4. Verificação de reprodutibilidade no README.md da raiz
    for required_readme_marker in (
        "uv sync --frozen",
        "Ternary-Bonsai-2-27B-PTQ1_0.gguf",
        "Exemplo de Entrada e Saída Ponta a Ponta",
        "--serve-ui",
    ):
        assert required_readme_marker in root_readme, (
            f"Marcador de reprodutibilidade ausente no README.md: {required_readme_marker}"
        )

    # 5. Verificação de links locais em fase3/*.md
    checked_links = 0
    pending: list[str] = []
    delivery_names = {
        "fase3_resultado_pratico.pdf",
        "fase3_resultado_pratico_rafael-attilio-agricola_jociclelio-castro-macedo-junior.pdf",
        "eduagent_fase3_entrega.zip",
        "SHA256SUMS.txt",
        "verificacao_documental.json",
    }
    for md_path in (demo_path, readme_entrega_path):
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", md_path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (md_path.parent / target.split("#", 1)[0]).resolve()
            if not resolved.exists() and resolved.name in delivery_names and not check_delivery:
                pending.append(resolved.name)
                continue
            assert resolved.exists(), f"Link local ausente em {md_path.name}: {target}"
            checked_links += 1

    if check_delivery:
        for fname in (
            "fase3_resultado_pratico.pdf",
            "fase3_resultado_pratico_rafael-attilio-agricola_jociclelio-castro-macedo-junior.pdf",
            "SHA256SUMS.txt",
            "verificacao_documental.json",
        ):
            assert (ROOT / fname).exists(), f"Artefato de entrega ausente: {fname}"

    return {
        "status": "passed",
        "scope": "documentação e relatório prático da Fase 3",
        "bibliography_unique": len(keys),
        "cited_unique": len(cited),
        "uncited_unique": len(set(keys) - cited),
        "missing_citations": [],
        "required_sections": len(REQUIRED_SECTIONS),
        "ai_declaration_present": True,
        "local_links_checked": checked_links,
        "delivery_pending": sorted(set(pending)),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-delivery", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.check_delivery), ensure_ascii=False, indent=2))
