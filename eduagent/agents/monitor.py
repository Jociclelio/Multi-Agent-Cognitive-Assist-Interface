"""Agente Monitor: gabarito, rubrica por critério, evidências (mapa §8, §15.2).

O Monitor recebe enunciado, resposta original, referência (gabarito),
critérios da rubrica, ajuda da tentativa e fonte — **nunca** a autovalidação
do Tutor (mapa §8): a entrada ``MonitorInput`` não possui campo para
validação própria do Tutor e a avaliação é produzida aqui, do zero, sobre a
resposta original do estudante.

Regras do mapa implementadas neste módulo:

- Itens determinísticos usam exatidão com **tolerância explícita** e
  **unidades** (§8); comparação numérica exata quando não há tolerância.
- Itens de texto usam rubrica por critério 0=incorreto/ausente, 1=parcial,
  2=adequado, com **span de resposta** (offsets reais na resposta original)
  e ``misconception_code`` (§8/§15.2).
- Abstinência (``reliability='abstain'``) nos quatro gatilhos do mapa §8:
  span inventado, item ambíguo, ausência de fonte e divergência formal.
  Em abstinência nenhum nível é atribuído inferencialmente: os resultados
  por critério usam ``evidence_kind='missing'`` com ``response_span=null``,
  nível 0 **marcador não inferencial** e a descrição do motivo (§15.2:
  ``missing`` exige span=null e descrição; nunca inventar span para
  silêncio). O redutor (``eduagent/services/assessment.py``) nunca usa
  assessment em abstinência para atualizar competência — feedback pode ser
  útil sem atualização inferencial (§8).
- Critério essencial indecidível (nível não atribuído pelo julgamento) torna
  a avaliação ``correctness='undecidable'`` (§15.2: indecidível não atualiza
  competência); o critério indecidível é **omitido** de ``criterion_results``
  em vez de receber nível fabricado.

BKT não é implementado aqui nem em qualquer ponto do redutor (mapa §8:
módulo futuro em shadow mode; não inventar priors).
"""

from __future__ import annotations

import re
import uuid as _uuid
from dataclasses import dataclass, fields
from enum import Enum
from typing import Protocol, Sequence

from eduagent.contracts import (
    Assessment,
    EduAgentError,
    ErrorCode,
    Ref,
    RubricCriterion,
    SourceRef,
)

_DIAGNOSTIC = "eduagent/agents/monitor.py"

#: Nível marcador não inferencial usado **apenas** em assessments em
#: abstinência (§15.2); o redutor ignora assessments abstidos por completo.
_ABSTAIN_MARKER_LEVEL = 0

#: Normalização numérica de ensaio (§1/§3): vírgula decimal quando não há
#: ponto; não é resultado medido e pode ser recalibrada.
_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


class MonitorMode(str, Enum):
    """Modo de avaliação do item (mapa §8)."""

    DETERMINISTIC = "deterministic"
    TEXT = "text"


class AbstentionTrigger(str, Enum):
    """Os quatro gatilhos de abstinência do mapa §8."""

    INVENTED_SPAN = "invented_span"
    AMBIGUOUS_ITEM = "ambiguous_item"
    MISSING_SOURCE = "missing_source"
    FORMAL_DIVERGENCE = "formal_divergence"


@dataclass(frozen=True)
class MonitorInput:
    """Entrada do Monitor (mapa §8): enunciado, resposta original,
    referência, critérios, ajuda e fonte.

    Não existe campo para autovalidação do Tutor — a garantia é estrutural:
    qualquer tentativa de passar ``tutor_self_validation`` (ou similar) falha
    em ``__post_init__`` (``dataclass`` sem esse campo + recusa explícita de
    chaves estranhas em ``extras``).
    """

    attempt_id: _uuid.UUID
    item_ref: Ref
    assessment_revision: int
    supersedes: Ref | None
    prompt: str
    response: str
    expected_answer: str
    rubric: tuple[RubricCriterion, ...]
    source_refs: tuple[SourceRef, ...]
    mode: MonitorMode
    help_level: int
    revealed: bool
    family_solution_seen_in_session: bool
    # Itens determinísticos: tolerância e unidade EXPLÍCITAS (mapa §8).
    tolerance: float | None = None
    unit: str | None = None
    item_ambiguous: bool = False
    extras: dict[str, object] | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.help_level <= 3:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "help_level da tentativa deve estar em 0..3",
                diagnostic=_DIAGNOSTIC,
            )
        if not self.rubric:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "Monitor exige rubrica com pelo menos um critério",
                diagnostic=_DIAGNOSTIC,
            )
        ids = [c.criterion_id for c in self.rubric]
        if len(set(ids)) != len(ids):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "criterion_id duplicado na rubrica do item",
                diagnostic=_DIAGNOSTIC,
            )
        if self.extras:
            # Barreira estrutural contra vazamento da autovalidação do Tutor
            # (mapa §8): payload estranho não entra na avaliação.
            forbidden = {"self_validation", "tutor_self_validation",
                         "tutor_validation"}
            leaked = forbidden & set(self.extras)
            if leaked:
                raise EduAgentError(
                    ErrorCode.SCHEMA_INVALID,
                    "Monitor não aceita autovalidação do Tutor (mapa §8): "
                    f"campos proibidos {sorted(leaked)}",
                    diagnostic=_DIAGNOSTIC,
                )

    @property
    def criterion_ids(self) -> frozenset[str]:
        return frozenset(c.criterion_id for c in self.rubric)


@dataclass(frozen=True)
class GradingRequest:
    """Pedido de julgamento por rubrica (itens de texto)."""

    prompt: str
    response: str
    expected_answer: str
    rubric: tuple[RubricCriterion, ...]


@dataclass(frozen=True)
class CriterionProposal:
    """Proposta de julgamento de UM critério pelo backend de julgamento.

    ``level=None`` significa critério essencial indecidível (§15.2).
    ``span_text`` deve ser trecho literal da resposta original — o Monitor
    converte em offsets e recusa span inventado.
    """

    criterion_id: str
    level: int | None
    span_text: str | None
    reason: str
    misconception_code: str | None = None


class RubricGrader(Protocol):
    """Backend de julgamento por rubrica (injetável; sem rede nos testes)."""

    def grade(self, request: GradingRequest) -> Sequence[CriterionProposal]:
        ...


@dataclass(frozen=True)
class MonitorAbstention:
    """Registro de abstinência (mapa §8) com gatilho e código tipado."""

    trigger: AbstentionTrigger
    error_code: ErrorCode
    detail: str


@dataclass(frozen=True)
class MonitorOutcome:
    """Resultado do Monitor: assessment contrato-tipo + abstinência opcional.

    ``accepted=False`` (reliability='abstain') nunca atualiza competência no
    redutor; o feedback segue útil para exibição (§8).
    """

    assessment: Assessment
    abstention: MonitorAbstention | None

    @property
    def accepted(self) -> bool:
        return (
            self.assessment.reliability is Assessment.Reliability.ACCEPTED
        )


def _short(text: str) -> str:
    return text if len(text) <= 1000 else text[:997] + "..."


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def _numeric_value(text: str) -> float | None:
    """Valor numérico de ensaio: vírgula decimal quando não há ponto."""
    stripped = text.strip().replace(" ", "")
    if "," in stripped and "." not in stripped:
        stripped = stripped.replace(",", ".")
    match = _NUMBER_RE.fullmatch(stripped)
    if match is not None:
        return float(match.group())
    fallback = _NUMBER_RE.search(stripped)
    return float(fallback.group()) if fallback is not None else None


def _strip_unit(text: str, unit: str | None) -> str:
    if not unit:
        return text
    return re.sub(re.escape(unit.strip()), " ", text, flags=re.IGNORECASE)


class Monitor:
    """Avaliador por gabarito/rubrica com abstinência (mapa §8, §15.2)."""

    def evaluate(
        self, data: MonitorInput, grader: RubricGrader | None = None
    ) -> MonitorOutcome:
        # Ausência de fonte: abstinência (mapa §8).
        if not data.source_refs:
            return self._abstain(
                data,
                AbstentionTrigger.MISSING_SOURCE,
                ErrorCode.NO_EVIDENCE,
                "avaliação sem fonte: o item não tem referência "
                "resolvível (mapa §8)",
            )
        # Item ambíguo: abstinência (mapa §8) — sinalizado pelo chamador
        # (grafo/orquestrador) a partir de critérios do enunciado.
        if data.item_ambiguous:
            return self._abstain(
                data,
                AbstentionTrigger.AMBIGUOUS_ITEM,
                ErrorCode.AMBIGUOUS_INPUT,
                "item ambíguo: enunciado/rubrica não permitem julgamento "
                "não ambíguo (mapa §8)",
            )
        if data.mode is MonitorMode.DETERMINISTIC:
            return self._evaluate_deterministic(data)
        return self._evaluate_text(data, grader)

    # -- itens determinísticos ---------------------------------------------

    def _evaluate_deterministic(self, data: MonitorInput) -> MonitorOutcome:
        if len(data.rubric) != 1:
            return self._abstain(
                data,
                AbstentionTrigger.FORMAL_DIVERGENCE,
                ErrorCode.SCHEMA_INVALID,
                "item determinístico exige rubrica com exatamente um "
                "critério (exatidão/tolerância/unidades, mapa §8)",
            )
        criterion = data.rubric[0]
        response = data.response
        if response.strip():
            level, reason, misconception = self._grade_deterministic(
                data, criterion
            )
            span: tuple[int, int] | None = (0, len(response))
            kind = Assessment.EvidenceKind.PRESENT
        else:
            # Resposta vazia: critério ausente — missing com span=null e
            # descrição (§15.2); nível 0 = ausente (§8), não é invenção.
            level, reason, misconception = (
                _ABSTAIN_MARKER_LEVEL,
                "critério ausente: resposta vazia",
                None,
            )
            span, kind = None, Assessment.EvidenceKind.MISSING
        result = Assessment.CriterionResult(
            criterion_id=criterion.criterion_id,
            topic_ids=list(criterion.topic_ids),
            level=level,
            evidence_kind=kind,
            response_span=span,
            reason=reason,
            misconception_code=misconception,
        )
        correctness = (
            Assessment.Correctness.CORRECT
            if level == 2
            else (
                Assessment.Correctness.INCORRECT
                if level == 0
                else Assessment.Correctness.PARTIAL
            )
        )
        return self._accepted(data, [result], correctness)

    def _grade_deterministic(
        self, data: MonitorInput, criterion: RubricCriterion
    ) -> tuple[int, str, str | None]:
        equivalences = {_normalize(e) for e in criterion.accepted_equivalences}
        if _normalize(data.response) in equivalences:
            return 2, "resposta igual a equivalência aceita pela rubrica", None
        if data.unit and data.unit.strip().casefold() not in (
            data.response.casefold()
        ):
            return (
                0,
                f"unidade declarada ({data.unit}) ausente na resposta "
                "(mapa §8: unidades explícitas)",
                "missing_unit",
            )
        expected = _numeric_value(_strip_unit(data.expected_answer, data.unit))
        if expected is None:
            # Referência não numérica: comparação exata normalizada.
            if _normalize(data.response) == _normalize(data.expected_answer):
                return 2, "resposta igual à referência", None
            return 0, "resposta difere da referência", None
        value = _numeric_value(_strip_unit(data.response, data.unit))
        if value is None:
            return 0, "resposta não é um valor numérico interpretável", None
        tolerance = data.tolerance if data.tolerance is not None else 0.0
        if abs(value - expected) <= tolerance:
            return (
                2,
                f"valor dentro da tolerância explícita (±{tolerance})",
                None,
            )
        return (
            0,
            f"valor fora da tolerância explícita (±{tolerance})",
            None,
        )

    # -- itens de texto (rubrica por critério) ------------------------------

    def _evaluate_text(
        self, data: MonitorInput, grader: RubricGrader | None
    ) -> MonitorOutcome:
        if grader is None:
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                "avaliação de texto exige backend de julgamento injetado",
                diagnostic=_DIAGNOSTIC,
            )
        proposals = list(
            grader.grade(
                GradingRequest(
                    prompt=data.prompt,
                    response=data.response,
                    expected_answer=data.expected_answer,
                    rubric=data.rubric,
                )
            )
        )
        # Cobertura exata da rubrica — divergência formal vira abstinência.
        seen: set[str] = set()
        for proposal in proposals:
            if proposal.criterion_id not in data.criterion_ids:
                return self._abstain(
                    data,
                    AbstentionTrigger.FORMAL_DIVERGENCE,
                    ErrorCode.SCHEMA_INVALID,
                    "proposta cita critério desconhecido "
                    f"({proposal.criterion_id!r})",
                )
            if proposal.criterion_id in seen:
                return self._abstain(
                    data,
                    AbstentionTrigger.FORMAL_DIVERGENCE,
                    ErrorCode.SCHEMA_INVALID,
                    "proposta duplicada para critério "
                    f"({proposal.criterion_id!r})",
                )
            seen.add(proposal.criterion_id)
            if proposal.level not in (0, 1, 2, None):
                return self._abstain(
                    data,
                    AbstentionTrigger.FORMAL_DIVERGENCE,
                    ErrorCode.SCHEMA_INVALID,
                    f"nível fora de 0/1/2 para critério "
                    f"{proposal.criterion_id!r}: {proposal.level!r}",
                )
            if not proposal.reason.strip():
                return self._abstain(
                    data,
                    AbstentionTrigger.FORMAL_DIVERGENCE,
                    ErrorCode.SCHEMA_INVALID,
                    f"proposta sem razão para critério "
                    f"{proposal.criterion_id!r}",
                )
        if seen != data.criterion_ids:
            missing = sorted(data.criterion_ids - seen)
            return self._abstain(
                data,
                AbstentionTrigger.FORMAL_DIVERGENCE,
                ErrorCode.SCHEMA_INVALID,
                "proposta não cobre a rubrica; critérios ausentes: "
                + ", ".join(missing),
            )
        results: list[Assessment.CriterionResult] = []
        undecided = False
        by_id = {c.criterion_id: c for c in data.rubric}
        for proposal in proposals:
            criterion = by_id[proposal.criterion_id]
            if proposal.level is None:
                # §15.2: indecidível essencial não atualiza competência —
                # critério omitido dos resultados (nível nunca é fabricado).
                undecided = True
                continue
            if proposal.span_text:
                index = data.response.find(proposal.span_text)
                if index < 0 or not data.response:
                    # Span inventado: abstinência (mapa §8).
                    return self._abstain(
                        data,
                        AbstentionTrigger.INVENTED_SPAN,
                        ErrorCode.SCHEMA_INVALID,
                        "span proposto não aparece na resposta original "
                        f"(critério {proposal.criterion_id!r}); nunca "
                        "inventar span para silêncio (§15.2)",
                    )
                span = (index, index + len(proposal.span_text))
                kind = Assessment.EvidenceKind.PRESENT
                reason = proposal.reason
            else:
                # Sem span: critério ausente na resposta — missing com
                # descrição (§15.2).
                span = None
                kind = Assessment.EvidenceKind.MISSING
                reason = f"critério ausente na resposta: {proposal.reason}"
            results.append(
                Assessment.CriterionResult(
                    criterion_id=criterion.criterion_id,
                    topic_ids=list(criterion.topic_ids),
                    level=proposal.level,
                    evidence_kind=kind,
                    response_span=span,
                    reason=reason,
                    misconception_code=proposal.misconception_code,
                )
            )
        if not results:
            # Nenhum critério decidível: sem resultado contrato-válido, a
            # avaliação inteira abstém por ambiguidade de julgamento.
            return self._abstain(
                data,
                AbstentionTrigger.AMBIGUOUS_ITEM,
                ErrorCode.AMBIGUOUS_INPUT,
                "nenhum critério decidível na proposta de julgamento",
            )
        correctness = self._aggregate(levels=[r.level for r in results],
                                      undecided=undecided)
        return self._accepted(data, results, correctness, undecided=undecided)

    @staticmethod
    def _aggregate(
        levels: Sequence[int], *, undecided: bool
    ) -> Assessment.Correctness:
        # Agregação §15.2: todos 2=correct; todos 0=incorrect; mistura=
        # partial; indecidível essencial=undecidable.
        if undecided:
            return Assessment.Correctness.UNDECIDABLE
        if levels and all(level == 2 for level in levels):
            return Assessment.Correctness.CORRECT
        if levels and all(level == 0 for level in levels):
            return Assessment.Correctness.INCORRECT
        return Assessment.Correctness.PARTIAL

    # -- construção dos assessments -----------------------------------------

    def _evidence_ids(self, data: MonitorInput) -> list[_uuid.UUID]:
        evidence: list[_uuid.UUID] = []
        for source in data.source_refs:
            if source.doc_id not in evidence:
                evidence.append(source.doc_id)
        return evidence

    def _accepted(
        self,
        data: MonitorInput,
        results: list[Assessment.CriterionResult],
        correctness: Assessment.Correctness,
        *,
        undecided: bool = False,
    ) -> MonitorOutcome:
        summary = ", ".join(
            f"{result.criterion_id}={result.level}" for result in results
        )
        reason = f"rubrica por critério: {summary}"
        if undecided:
            reason += "; critério essencial indecidível não atualiza " \
                      "competência (§15.2)"
        assessment = Assessment(
            attempt_id=data.attempt_id,
            item_ref=data.item_ref,
            assessment_revision=data.assessment_revision,
            supersedes=data.supersedes,
            criterion_results=results,
            correctness=correctness,
            help_level=data.help_level,
            revealed=data.revealed,
            evidence_ids=self._evidence_ids(data),
            reliability=Assessment.Reliability.ACCEPTED,
            reason=_short(reason),
        )
        return MonitorOutcome(assessment=assessment, abstention=None)

    def _abstain(
        self,
        data: MonitorInput,
        trigger: AbstentionTrigger,
        error_code: ErrorCode,
        detail: str,
    ) -> MonitorOutcome:
        # Abstinência contrato-conforme (§4/§15.2): cada critério como
        # missing (span=null, descrição do motivo), nível 0 é MARCADOR não
        # inferencial — o redutor ignora assessments abstidos por completo.
        marker_reason = _short(
            f"avaliação abstida ({trigger.value}): {detail} — nível não "
            "atribuído; feedback sem atualização inferencial (§8)"
        )
        results = [
            Assessment.CriterionResult(
                criterion_id=criterion.criterion_id,
                topic_ids=list(criterion.topic_ids),
                level=_ABSTAIN_MARKER_LEVEL,
                evidence_kind=Assessment.EvidenceKind.MISSING,
                response_span=None,
                reason=marker_reason,
                misconception_code=None,
            )
            for criterion in data.rubric
        ]
        assessment = Assessment(
            attempt_id=data.attempt_id,
            item_ref=data.item_ref,
            assessment_revision=data.assessment_revision,
            supersedes=data.supersedes,
            criterion_results=results,
            correctness=Assessment.Correctness.UNDECIDABLE,
            help_level=data.help_level,
            revealed=data.revealed,
            evidence_ids=self._evidence_ids(data),
            reliability=Assessment.Reliability.ABSTAIN,
            reason=_short(f"abstinência ({trigger.value}): {detail}"),
        )
        abstention = MonitorAbstention(
            trigger=trigger, error_code=error_code, detail=detail
        )
        return MonitorOutcome(assessment=assessment, abstention=abstention)


__all__ = [
    "AbstentionTrigger",
    "Assessment",
    "CriterionProposal",
    "GradingRequest",
    "Monitor",
    "MonitorAbstention",
    "MonitorInput",
    "MonitorMode",
    "MonitorOutcome",
    "RubricCriterion",
    "RubricGrader",
]

#: Campos de ``MonitorInput`` — verificação estrutural de que a autovalidação
#: do Tutor não faz parte da interface do Monitor (mapa §8).
MONITOR_INPUT_FIELDS = frozenset(f.name for f in fields(MonitorInput))
