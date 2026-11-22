"""Regressão do parser de datas do Curador (§6.3).

Origem: W01 observado em 21/11/2026 — a ementa do MC832 ("Datas: 10/09/26,
15/10/26 e 26/11/26") gerava gates espúrios porque ``_DATE_SLASH_SHORT``
casava o rabo de datas DD/MM/AA ("09/26" dentro de "10/09/26") e a taxonomia
não tinha a forma DD/MM/AA. Estas travas valem PARA SEMPRE:

1. Forma curta (DD/MM) nunca casa dentro de data longa;
2. DD/MM/AA vira data completa (pivô 2000+aa), não gate ambíguo;
3. Formas ISO e DD/MM/YYYY continuam intactas;
4. Máscara de datas remove TODAS as formas antes da extração numérica.
"""

from __future__ import annotations

from eduagent.agents.curator import CuratorAgent
from eduagent.agents.curator import validate_date

# Texto real do ProgramaMC8322s26-1.pdf (bloco p1#10024) — o caso do bug.
EMENTA_MC8322 = (
    "Avaliação: listas semanais, projetos e provas. "
    "Três provas (pesos iguais). Datas: 10/09/26, 15/10/26 e 26/11/26. "
    "Avaliação de Curso: 20/10/26."
)


def _dates(text: str) -> dict[str, tuple[str, str]]:
    """{expressão: (normalizado, validation)} dos candidatos de data."""
    return {
        expr: (normalized, validation)
        for expr, _kind, _precision, normalized, validation in (
            CuratorAgent._date_candidates(text)
        )
    }


# ============================================================================
# 1. O caso do bug: DD/MM/AA é data completa, nunca rabo ambíguo
# ============================================================================
def test_dd_mm_yy_dates_are_complete_not_ambiguous() -> None:
    dates = _dates(EMENTA_MC8322)
    assert "10/09/26" in dates
    assert "15/10/26" in dates
    assert "26/11/26" in dates
    assert "20/10/26" in dates
    for expr in ("10/09/26", "15/10/26", "26/11/26", "20/10/26"):
        normalized, validation = dates[expr]
        assert validation == "ok", f"{expr}: {validation}"
    assert dates["10/09/26"][0] == "2026-09-10"
    assert dates["15/10/26"][0] == "2026-10-15"
    assert dates["26/11/26"][0] == "2026-11-26"
    assert dates["20/10/26"][0] == "2026-10-20"


def test_no_tail_of_long_date_becomes_short_candidate() -> None:
    """'09/26', '10/26', '11/26' (rabos de 10/09/26, 15/10/26, 26/11/26)
    NUNCA aparecem como candidatos — era o gate espúrio do W01."""
    dates = _dates(EMENTA_MC8322)
    for tail in ("09/26", "10/26", "11/26"):
        assert tail not in dates, f"rabo de data vazou: {tail}"


# ============================================================================
# 2. Fronteiras: formas curtas legítimas continuam ambiguas (sem ano inventado)
# ============================================================================
def test_genuine_short_date_stays_ambiguous() -> None:
    dates = _dates("Avaliação em 20/10, sem ano definido.")
    assert "20/10" in dates
    normalized, validation = dates["20/10"]
    assert normalized == "--10-20"
    assert validation == "year_missing"


def test_short_date_inside_long_date_is_never_matched() -> None:
    # "15/10" (curta) está contida em "15/10/26" (longa) — só a longa sai.
    dates = _dates("Prova em 15/10/26 e entrega em 15/10.")
    assert "15/10/26" in dates
    assert "15/10" in dates  # a segunda ocorrência é genuinamente curta
    assert dates["15/10/26"][1] == "ok"
    assert dates["15/10"][1] == "year_missing"


def test_iso_and_full_dates_unaffected_by_boundary_guards() -> None:
    dates = _dates("ISO 2026-03-15 e completa 12/05/2026.")
    assert dates["2026-03-15"] == ("2026-03-15", "ok")
    assert dates["12/05/2026"] == ("2026-05-12", "ok")
    # rabos da ISO ("03-15") e da completa ("05/2026") não vazam
    assert "03-15" not in dates
    assert "05/2026" not in dates


# ============================================================================
# 3. validate_date: contrato da forma DD/MM/AA
# ============================================================================
def test_validate_date_yy_form() -> None:
    assert validate_date("10/09/26", "2026-09-10") == "ok"
    assert validate_date("10/09/26", "2026-09-11") == "value_mismatch"
    # Formato DD/MM/AA reconhecido: derivação divergente → value_mismatch
    # (validade de calendário é recusada em _date_candidates, antes daqui).
    assert validate_date("13/13/26", "2013-13-13") == "value_mismatch"
    # Forma que não é data → não derivável
    assert validate_date("banana", "2026-09-10") == "expression_not_a_date"


# ============================================================================
# 4. Máscara: número dentro de data não vira fato numérico
# ============================================================================
def test_mask_dates_covers_yy_form() -> None:
    masked = CuratorAgent._mask_dates("P1 em 10/09/26 com nota 8.5 e ISO 2026-03-15.")
    assert "10/09/26" not in masked
    assert "2026-03-15" not in masked
    assert "8.5" in masked


# ============================================================================
# 5. Invariante de sanidade: nenhum candidato de data colide com outro
# ============================================================================
def test_no_overlapping_candidates() -> None:
    dates = _dates(EMENTA_MC8322)
    expressions = list(dates)
    for expr in expressions:
        for other in expressions:
            if expr != other and expr in other:
                raise AssertionError(
                    f"candidato sobreposto: {expr!r} está dentro de {other!r}"
                )
