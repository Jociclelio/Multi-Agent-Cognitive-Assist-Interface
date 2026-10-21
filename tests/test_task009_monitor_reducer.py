"""Testes de aceite da task 009 — Monitor, redutor determinístico e estado de
tópico (mapa §8, §15.2; contratos Assessment/TopicState/RubricCriterion da
task 003 + §15.2, armazenamento da 004, commit idempotente da 005).

Não é a suíte quantitativa da etapa 8 (mapa de testes): são testes locais de
curta duração com backend de julgamento injetado (``FakeGrader``
determinístico; nenhuma chamada ao modelo real). C4 (mapa intocado, commits
separados, submodule intocado) é verificado por inspeção de git e registrado
no task.md.

Tabela de testes (código → caso):

| Código | Caso |
|---|---|
| M1 | determinístico correto com tolerância e unidade explícitas |
| M2 | determinístico fora da tolerância → incorrect |
| M3 | unidade declarada ausente → level 0 com misconception |
| M11 | equivalência aceita da rubrica conta como adequado |
| M4 | texto: rubrica 2 critérios (2 e 1) → partial, spans = offsets reais |
| M5 | span inventado → abstinência (missing, span=null) |
| M6 | ausência de fonte → abstinência |
| M7 | item ambíguo → abstinência |
| M8 | divergência formal (critério desconhecido/duplicado/nível inválido/cobertura/sem razão) → abstinência |
| M9 | critério essencial indecidível → undecidable, critério omitido |
| M10 | Monitor não recebe autovalidação do Tutor (garantia estrutural) |
| M12 | resposta vazia → critério ausente (missing, span=null), incorrect |
| R1 | primeira tentativa correta independente → mixed |
| R2 | positivo: erro crítico + 3 corretas independentes distintas → favorable |
| R3a | menos de três elegíveis → mixed |
| R3b | famílias repetidas → mixed |
| R3c | independente parcial mais recente interrompe → mixed |
| R3d | independente incorreta mais recente interrompe → mixed |
| R3e | novo erro crítico volta a mixed |
| R3f | assistida não compõe sequência → mixed |
| R3g | assistida não remove erro crítico (e não bloqueia recuperação) |
| R3h | indecidível não compõe nem interrompe |
| R3i | erro crítico assistido volta a mixed (mesmo assistido) |
| R4 | zero evidência → insufficient |
| R5 | ordem cronológica: assessment tardio não muda a ordem |
| R6 | supersedes: correção recalcula projeção desde eventos (mixed→favorable) |
| R7 | unicidade (attempt_id, revision), revision monotônica e supersedes estrito |
| R8 | abstinência não atualiza estado (nem erro crítico marcador) |
| R9 | critério multicomponente não atualiza tópicos (§15.2) |
| R10 | desempate por attempt_ordinal no mesmo occurred_at |
| S1 | migration 0004: colunas family_id/independent + CHECK |
| S2 | record_attempt: ordinal no commit e independência julgada no commit |
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from eduagent.agents.monitor import (
    MONITOR_INPUT_FIELDS,
    AbstentionTrigger,
    CriterionProposal,
    Monitor,
    MonitorInput,
    MonitorMode,
)
from eduagent.contracts import (
    Assessment,
    EduAgentError,
    ErrorCode,
    Ref,
    RubricCriterion,
    SourceRef,
    TopicState,
)
from eduagent.services.assessment import (
    AssessmentFact,
    AssessmentService,
    AttemptFact,
    compute_topic_states,
)
from eduagent.services.effects import EffectsService
from eduagent.storage.repository import DomainStore

UID = "123e4567-e89b-12d3-a456-426614174000"
SESSION = "7c9e6679-7425-40de-944b-e07fc1f90ae7"
COURSE = "c0000000-0000-0000-0000-000000000001"
TOPIC_A = "aaaaaaaa-0000-0000-0000-000000000001"
TOPIC_B = "bbbbbbbb-0000-0000-0000-000000000002"
TOPIC_C = "cccccccc-0000-0000-0000-000000000003"
DOC = "3ea0f0e2-0c1e-4d9a-9b1f-0a2b3c4d5e6f"
VERSION = "4ea0f0e2-0c1e-4d9a-9b1f-0a2b3c4d5e6f"
HASH = "ab" * 32

T0 = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
FIXED_NOW = T0 + timedelta(hours=9)


def _uid(n: int) -> _uuid.UUID:
    return _uuid.UUID(f"00000000-0000-0000-0000-{n:012d}")


def _source() -> SourceRef:
    return SourceRef(
        doc_id=_uuid.UUID(DOC),
        version_id=_uuid.UUID(VERSION),
        physical_page=1,
        block_id="p1b1",
        text_hash=HASH,
    )


def _rubric(
    *specs: tuple[str, list[_uuid.UUID], bool]
) -> tuple[RubricCriterion, ...]:
    return tuple(
        RubricCriterion(
            criterion_id=cid,
            topic_ids=topics,
            description=f"critério {cid}",
            critical=critical,
        )
        for cid, topics, critical in specs
    )


# ---------------------------------------------------------------------------
# Backend de julgamento de texto determinístico (injetável)
# ---------------------------------------------------------------------------


class FakeGrader:
    def __init__(self, proposals: list[CriterionProposal]) -> None:
        self.proposals = list(proposals)
        self.calls: list[object] = []

    def grade(self, request):
        self.calls.append(request)
        return list(self.proposals)


def _monitor_input(**overrides) -> MonitorInput:
    item_id = _uid(101)
    defaults: dict = {
        "attempt_id": _uid(201),
        "item_ref": Ref(kind="item", id=item_id, version=1),
        "assessment_revision": 1,
        "supersedes": None,
        "prompt": "Quantos segundos tem 1,5 minuto? Responda com unidade.",
        "response": "90 s",
        "expected_answer": "90 s",
        "rubric": _rubric(
            ("c1", [_uuid.UUID(TOPIC_A)], False),
        ),
        "source_refs": (_source(),),
        "mode": MonitorMode.DETERMINISTIC,
        "help_level": 0,
        "revealed": False,
        "family_solution_seen_in_session": False,
        "tolerance": 0.0,
        "unit": "s",
    }
    defaults.update(overrides)
    return MonitorInput(**defaults)


# ---------------------------------------------------------------------------
# Monitor (M1–M12)
# ---------------------------------------------------------------------------


class TestMonitor:
    def setup_method(self) -> None:
        self.monitor = Monitor()

    def test_m1_deterministic_correct_with_tolerance_and_unit(self):
        outcome = self.monitor.evaluate(
            _monitor_input(response="90,5 s", tolerance=0.5, unit="s",
                           expected_answer="90 s")
        )
        assert outcome.accepted
        result = outcome.assessment.criterion_results[0]
        assert result.level == 2
        assert result.response_span == (0, len("90,5 s"))
        assert outcome.assessment.correctness is (
            Assessment.Correctness.CORRECT
        )
        assert outcome.assessment.reliability is (
            Assessment.Reliability.ACCEPTED
        )

    def test_m2_deterministic_out_of_tolerance(self):
        outcome = self.monitor.evaluate(
            _monitor_input(response="95 s", tolerance=0.5, unit="s",
                           expected_answer="90 s")
        )
        assert outcome.accepted
        assert outcome.assessment.correctness is (
            Assessment.Correctness.INCORRECT
        )
        assert outcome.assessment.criterion_results[0].level == 0
        assert "tolerância" in outcome.assessment.criterion_results[0].reason

    def test_m3_missing_unit_is_incorrect_with_misconception(self):
        outcome = self.monitor.evaluate(
            _monitor_input(response="90", tolerance=0.5, unit="s",
                           expected_answer="90 s")
        )
        result = outcome.assessment.criterion_results[0]
        assert result.level == 0
        assert result.misconception_code == "missing_unit"
        assert "unidade" in result.reason

    def test_m11_accepted_equivalence_counts_as_correct(self):
        rubric = (
            RubricCriterion(
                criterion_id="c1",
                topic_ids=[_uuid.UUID(TOPIC_A)],
                description="d",
                critical=False,
                accepted_equivalences=["um minuto e meio"],
            ),
        )
        outcome = self.monitor.evaluate(
            _monitor_input(
                response="Um  minuto e meio",
                rubric=rubric,
                expected_answer="90 s",
                unit=None,
            )
        )
        assert outcome.accepted
        assert outcome.assessment.correctness is (
            Assessment.Correctness.CORRECT
        )

    def test_m4_text_partial_with_real_spans(self):
        response = "A dedup vem primeiro, mas falta citar o recibo."
        grader = FakeGrader([
            CriterionProposal(
                criterion_id="c1",
                level=2,
                span_text="A dedup vem primeiro",
                reason="identifica a dedup",
            ),
            CriterionProposal(
                criterion_id="c2",
                level=1,
                span_text="falta citar o recibo",
                reason="menciona o recibo sem detalhar",
                misconception_code="incomplete_receipt",
            ),
        ])
        outcome = self.monitor.evaluate(
            _monitor_input(
                mode=MonitorMode.TEXT,
                response=response,
                rubric=_rubric(
                    ("c1", [_uuid.UUID(TOPIC_A)], False),
                    ("c2", [_uuid.UUID(TOPIC_A)], False),
                ),
            ),
            grader=grader,
        )
        assert outcome.accepted
        assert outcome.assessment.correctness is Assessment.Correctness.PARTIAL
        first, second = outcome.assessment.criterion_results
        assert first.response_span == (0, len("A dedup vem primeiro"))
        assert second.response_span == (
            response.find("falta citar o recibo"),
            response.find("falta citar o recibo") + len("falta citar o recibo"),
        )
        assert second.misconception_code == "incomplete_receipt"

    def test_m5_invented_span_abstains(self):
        grader = FakeGrader([
            CriterionProposal(
                criterion_id="c1",
                level=2,
                span_text="trecho que não existe na resposta",
                reason="span fabricado",
            ),
        ])
        outcome = self.monitor.evaluate(
            _monitor_input(
                mode=MonitorMode.TEXT,
                response="resposta real do estudante",
                rubric=_rubric(("c1", [_uuid.UUID(TOPIC_A)], False)),
            ),
            grader=grader,
        )
        assert not outcome.accepted
        assert outcome.abstention.trigger is AbstentionTrigger.INVENTED_SPAN
        assessment = outcome.assessment
        assert assessment.reliability is Assessment.Reliability.ABSTAIN
        assert assessment.correctness is Assessment.Correctness.UNDECIDABLE
        for result in assessment.criterion_results:
            assert result.evidence_kind is Assessment.EvidenceKind.MISSING
            assert result.response_span is None
            assert "abstida" in result.reason

    def test_m6_missing_source_abstains(self):
        outcome = self.monitor.evaluate(_monitor_input(source_refs=()))
        assert not outcome.accepted
        assert outcome.abstention.trigger is AbstentionTrigger.MISSING_SOURCE
        assert outcome.abstention.error_code is ErrorCode.NO_EVIDENCE
        assert outcome.assessment.reliability is Assessment.Reliability.ABSTAIN

    def test_m7_ambiguous_item_abstains(self):
        outcome = self.monitor.evaluate(_monitor_input(item_ambiguous=True))
        assert not outcome.accepted
        assert outcome.abstention.trigger is AbstentionTrigger.AMBIGUOUS_ITEM
        assert outcome.abstention.error_code is ErrorCode.AMBIGUOUS_INPUT

    @pytest.mark.parametrize(
        "proposals",
        [
            # critério desconhecido
            [CriterionProposal("fantasma", 2, "s", "r")],
            # nível inválido
            [CriterionProposal("c1", 3, "s", "r")],
            # cobertura incompleta
            [],
            # sem razão
            [CriterionProposal("c1", 2, "s", "  ")],
        ],
    )
    def test_m8_formal_divergence_abstains(self, proposals):
        grader = FakeGrader(proposals)
        outcome = self.monitor.evaluate(
            _monitor_input(
                mode=MonitorMode.TEXT,
                response="resposta",
                rubric=_rubric(("c1", [_uuid.UUID(TOPIC_A)], False)),
            ),
            grader=grader,
        )
        assert not outcome.accepted
        assert (
            outcome.abstention.trigger is AbstentionTrigger.FORMAL_DIVERGENCE
        )
        assert outcome.assessment.reliability is Assessment.Reliability.ABSTAIN

    def test_m9_essential_undecidable_is_omitted_not_fabricated(self):
        grader = FakeGrader([
            CriterionProposal("c1", None, None, "não foi possível decidir"),
            CriterionProposal("c2", 2, "resposta real", "ok"),
        ])
        outcome = self.monitor.evaluate(
            _monitor_input(
                mode=MonitorMode.TEXT,
                response="resposta real do estudante",
                rubric=_rubric(
                    ("c1", [_uuid.UUID(TOPIC_A)], True),
                    ("c2", [_uuid.UUID(TOPIC_A)], False),
                ),
            ),
            grader=grader,
        )
        assert outcome.accepted
        assert outcome.assessment.correctness is (
            Assessment.Correctness.UNDECIDABLE
        )
        ids = [r.criterion_id for r in outcome.assessment.criterion_results]
        # Critério indecidível omitido — nível nunca é fabricado.
        assert ids == ["c2"]

    def test_m10_monitor_never_receives_tutor_selfvalidation(self):
        # Garantia estrutural (mapa §8): a interface do Monitor não tem campo
        # para autovalidação do Tutor e payload estranho é recusado.
        assert "self_validation" not in MONITOR_INPUT_FIELDS
        assert "tutor_self_validation" not in MONITOR_INPUT_FIELDS
        with pytest.raises(EduAgentError) as excinfo:
            _monitor_input(
                extras={"tutor_self_validation": {"valid": True}}
            )
        assert excinfo.value.code is ErrorCode.SCHEMA_INVALID

    def test_m12_empty_response_is_missing_evidence_incorrect(self):
        outcome = self.monitor.evaluate(_monitor_input(response="   "))
        result = outcome.assessment.criterion_results[0]
        assert result.evidence_kind is Assessment.EvidenceKind.MISSING
        assert result.response_span is None
        assert result.level == 0
        assert outcome.assessment.correctness is (
            Assessment.Correctness.INCORRECT
        )


# ---------------------------------------------------------------------------
# Redutor — infraestrutura de teste
# ---------------------------------------------------------------------------


@pytest.fixture()
def env(tmp_path: Path):
    store = DomainStore.open(tmp_path / "domain.sqlite")
    store.ensure_user(UID)
    store.execute_write(
        UID,
        [
            (
                "INSERT INTO courses(id, user_id, title) VALUES (?,?,?)",
                (COURSE, UID, "Curso"),
            ),
            (
                "INSERT INTO topics(id, course_id, title) VALUES (?,?,?)",
                (TOPIC_A, COURSE, "Tópico A"),
            ),
            (
                "INSERT INTO topics(id, course_id, title) VALUES (?,?,?)",
                (TOPIC_B, COURSE, "Tópico B"),
            ),
            (
                "INSERT INTO topics(id, course_id, title) VALUES (?,?,?)",
                (TOPIC_C, COURSE, "Tópico C"),
            ),
        ],
    )
    service = AssessmentService(
        store, EffectsService(store), clock=lambda: FIXED_NOW
    )
    yield service, store
    store.close()


class World:
    """Auxiliar: publica itens (famílias), registra tentativas e submete
    assessments via serviço."""

    def __init__(self, service: AssessmentService, store: DomainStore):
        self.service = service
        self.store = store
        self.counter = 0

    def item(self, family: int) -> _uuid.UUID:
        self.counter += 1
        item_id = _uid(1000 + self.counter)
        self.store.execute_write(
            UID,
            [
                (
                    "INSERT INTO items(id, user_id, family_id, version, "
                    "prompt, answer_ref, rubric_ref, source_refs_json) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (
                        str(item_id),
                        UID,
                        str(_uid(family)),
                        1,
                        "enunciado",
                        "event:00000000-0000-0000-0000-00000000000f@1",
                        "event:00000000-0000-0000-0000-00000000000f@1",
                        "[]",
                    ),
                )
            ],
        )
        return item_id

    def attempt(
        self,
        item_id: _uuid.UUID,
        family: int,
        *,
        occurred: datetime,
        help_level: int = 0,
        revealed: bool = False,
        seen: bool = False,
    ):
        return self.service.record_attempt(
            user_id=UID,
            session_id=SESSION,
            item_id=item_id,
            family_id=_uid(family),
            response_text="resposta do estudante",
            help_level=help_level,
            revealed=revealed,
            family_solution_seen_in_session=seen,
            occurred_at=occurred,
        )

    def assess(
        self,
        record,
        item_id: _uuid.UUID,
        *,
        levels: list[int],
        critical: tuple[str, ...] = ("c1",),
        revision: int = 1,
        supersedes: Ref | None = None,
        correctness: Assessment.Correctness | None = None,
        reliability: Assessment.Reliability = Assessment.Reliability.ACCEPTED,
    ) -> AssessmentCheckResult:
        results = [
            Assessment.CriterionResult(
                criterion_id=f"c{i + 1}",
                topic_ids=[_uuid.UUID(TOPIC_A)],
                level=level,
                evidence_kind=Assessment.EvidenceKind.PRESENT,
                response_span=(0, 10),
                reason=f"critério c{i + 1} avaliado",
            )
            for i, level in enumerate(levels)
        ]
        if correctness is None:
            if reliability is Assessment.Reliability.ABSTAIN:
                correctness = Assessment.Correctness.UNDECIDABLE
            else:
                correctness = _aggregate(levels)
        assessment = Assessment(
            attempt_id=record.attempt_id,
            item_ref=Ref(kind="item", id=item_id, version=1),
            assessment_revision=revision,
            supersedes=supersedes,
            criterion_results=results,
            correctness=correctness,
            help_level=0,
            revealed=False,
            evidence_ids=[],
            reliability=reliability,
            reason="avaliação de teste",
        )
        return self.service.check(
            user_id=UID,
            session_id=SESSION,
            assessment=assessment,
            critical_criterion_ids=list(critical),
        )


def _aggregate(levels: list[int]) -> Assessment.Correctness:
    if levels and all(level == 2 for level in levels):
        return Assessment.Correctness.CORRECT
    if levels and all(level == 0 for level in levels):
        return Assessment.Correctness.INCORRECT
    return Assessment.Correctness.PARTIAL


def _state(env, topic: str = TOPIC_A) -> TopicState:
    service, _ = env
    state = service.topic_state(UID, _uuid.UUID(topic))
    assert state is not None
    return state


def _favorable_setup(world: World):
    """Erro crítico em A1 (12:00) + três corretas independentes de famílias
    distintas (12:01, 12:02, 12:03) → favorable (caso positivo R2)."""
    item1 = world.item(1)
    item2 = world.item(2)
    item3 = world.item(3)
    item4 = world.item(4)
    a1 = world.attempt(item1, 1, occurred=T0)
    world.assess(a1, item1, levels=[0, 2], correctness=Assessment.Correctness.PARTIAL)
    a2 = world.attempt(item2, 2, occurred=T0 + timedelta(minutes=1))
    world.assess(a2, item2, levels=[2, 2])
    a3 = world.attempt(item3, 3, occurred=T0 + timedelta(minutes=2))
    world.assess(a3, item3, levels=[2, 2])
    a4 = world.attempt(item4, 4, occurred=T0 + timedelta(minutes=3))
    world.assess(a4, item4, levels=[2, 2])
    return a1, (a2, a3, a4)


# ---------------------------------------------------------------------------
# Redutor (R1–R10)
# ---------------------------------------------------------------------------


class TestReducer:
    def test_r1_first_correct_attempt_is_mixed(self, env):
        service, _ = env
        world = World(service, env[1])
        item = world.item(1)
        record = world.attempt(item, 1, occurred=T0)
        world.assess(record, item, levels=[2, 2])
        state = _state(env)
        assert state.status is TopicState.TopicStatus.MIXED
        assert state.estimate is None
        assert state.independent_attempt_ids == [record.attempt_id]
        assert state.assisted_attempt_ids == []
        assert state.last_attempt_at == T0
        assert state.model_version == "monitor-rules-mvp"

    def test_r2_favorable_after_critical_error(self, env):
        service, store = env
        world = World(service, store)
        _favorable_setup(world)
        state = _state(env)
        assert state.status is TopicState.TopicStatus.FAVORABLE
        assert len(state.independent_attempt_ids) == 4

    def test_r3a_fewer_than_three_is_mixed(self, env):
        service, store = env
        world = World(service, store)
        item1 = world.item(1)
        a1 = world.attempt(item1, 1, occurred=T0)
        world.assess(a1, item1, levels=[0, 2],
                     correctness=Assessment.Correctness.PARTIAL)
        item2 = world.item(2)
        a2 = world.attempt(item2, 2, occurred=T0 + timedelta(minutes=1))
        world.assess(a2, item2, levels=[2, 2])
        assert _state(env).status is TopicState.TopicStatus.MIXED

    def test_r3b_repeated_families_block_favorable(self, env):
        service, store = env
        world = World(service, store)
        item1 = world.item(1)
        a1 = world.attempt(item1, 1, occurred=T0)
        world.assess(a1, item1, levels=[0, 2],
                     correctness=Assessment.Correctness.PARTIAL)
        item2 = world.item(2)
        a2 = world.attempt(item2, 2, occurred=T0 + timedelta(minutes=1))
        world.assess(a2, item2, levels=[2, 2])
        item3 = world.item(2)  # mesma família do anterior
        a3 = world.attempt(item3, 2, occurred=T0 + timedelta(minutes=2))
        world.assess(a3, item3, levels=[2, 2])
        item4 = world.item(4)
        a4 = world.attempt(item4, 4, occurred=T0 + timedelta(minutes=3))
        world.assess(a4, item4, levels=[2, 2])
        # Três corretas, mas duas da mesma família → mixed.
        assert _state(env).status is TopicState.TopicStatus.MIXED

    def test_r3c_independent_partial_interrupts(self, env):
        service, store = env
        world = World(service, store)
        item1 = world.item(1)
        a1 = world.attempt(item1, 1, occurred=T0)
        world.assess(a1, item1, levels=[0, 2],
                     correctness=Assessment.Correctness.PARTIAL)
        for i, family in enumerate((2, 3, 4)):
            item = world.item(family)
            record = world.attempt(
                item, family, occurred=T0 + timedelta(minutes=i + 1)
            )
            world.assess(record, item, levels=[2, 2])
        item5 = world.item(5)
        a5 = world.attempt(item5, 5, occurred=T0 + timedelta(minutes=4))
        world.assess(a5, item5, levels=[1, 2],
                     correctness=Assessment.Correctness.PARTIAL)
        assert _state(env).status is TopicState.TopicStatus.MIXED

    def test_r3d_independent_incorrect_interrupts(self, env):
        service, store = env
        world = World(service, store)
        item1 = world.item(1)
        a1 = world.attempt(item1, 1, occurred=T0)
        world.assess(a1, item1, levels=[0, 2],
                     correctness=Assessment.Correctness.PARTIAL)
        for i, family in enumerate((2, 3, 4)):
            item = world.item(family)
            record = world.attempt(
                item, family, occurred=T0 + timedelta(minutes=i + 1)
            )
            world.assess(record, item, levels=[2, 2])
        item5 = world.item(5)
        a5 = world.attempt(item5, 5, occurred=T0 + timedelta(minutes=4))
        world.assess(a5, item5, levels=[0, 0],
                     correctness=Assessment.Correctness.INCORRECT)
        assert _state(env).status is TopicState.TopicStatus.MIXED

    def test_r3e_new_critical_error_returns_to_mixed(self, env):
        service, store = env
        world = World(service, store)
        _favorable_setup(world)
        assert _state(env).status is TopicState.TopicStatus.FAVORABLE
        item5 = world.item(5)
        a5 = world.attempt(item5, 5, occurred=T0 + timedelta(minutes=4))
        world.assess(a5, item5, levels=[0, 2],
                     correctness=Assessment.Correctness.PARTIAL)
        state = _state(env)
        assert state.status is TopicState.TopicStatus.MIXED

    def test_r3f_assisted_does_not_compose(self, env):
        service, store = env
        world = World(service, store)
        item1 = world.item(1)
        a1 = world.attempt(item1, 1, occurred=T0)
        world.assess(a1, item1, levels=[0, 2],
                     correctness=Assessment.Correctness.PARTIAL)
        item2 = world.item(2)
        a2 = world.attempt(item2, 2, occurred=T0 + timedelta(minutes=1))
        world.assess(a2, item2, levels=[2, 2])
        item3 = world.item(3)
        a3 = world.attempt(item3, 3, occurred=T0 + timedelta(minutes=2))
        world.assess(a3, item3, levels=[2, 2])
        # Terceira "correta" é ASSISTIDA: não compõe a sequência.
        item4 = world.item(4)
        a4 = world.attempt(
            item4, 4, occurred=T0 + timedelta(minutes=3), help_level=2
        )
        world.assess(a4, item4, levels=[2, 2])
        state = _state(env)
        assert state.status is TopicState.TopicStatus.MIXED
        assert a4.attempt_id in state.assisted_attempt_ids
        assert a4.attempt_id not in state.independent_attempt_ids

    def test_r3g_assisted_neither_removes_nor_blocks(self, env):
        service, store = env
        world = World(service, store)
        item1 = world.item(1)
        a1 = world.attempt(item1, 1, occurred=T0)
        world.assess(a1, item1, levels=[0, 2],
                     correctness=Assessment.Correctness.PARTIAL)
        # Assistida correta NÃO remove o erro crítico.
        item2 = world.item(2)
        a2 = world.attempt(
            item2, 2, occurred=T0 + timedelta(minutes=1), help_level=1
        )
        world.assess(a2, item2, levels=[2, 2])
        state = _state(env)
        assert state.status is TopicState.TopicStatus.MIXED
        # Duas independentes corretas depois do erro ainda não bastam.
        for i, family in enumerate((3, 4)):
            item = world.item(family)
            record = world.attempt(
                item, family, occurred=T0 + timedelta(minutes=i + 2)
            )
            world.assess(record, item, levels=[2, 2])
        assert _state(env).status is TopicState.TopicStatus.MIXED
        # Terceira independente correta: três elegíveis após o erro crítico
        # → favorable; a assistida não bloqueou a recuperação.
        item5 = world.item(5)
        a5 = world.attempt(item5, 5, occurred=T0 + timedelta(minutes=4))
        world.assess(a5, item5, levels=[2, 2])
        assert _state(env).status is TopicState.TopicStatus.FAVORABLE

    def test_r3h_undecidable_neither_composes_nor_interrupts(self, env):
        service, store = env
        world = World(service, store)
        item1 = world.item(1)
        a1 = world.attempt(item1, 1, occurred=T0)
        world.assess(a1, item1, levels=[0, 2],
                     correctness=Assessment.Correctness.PARTIAL)
        for i, family in enumerate((2, 3, 4)):
            item = world.item(family)
            record = world.attempt(
                item, family, occurred=T0 + timedelta(minutes=i + 1)
            )
            world.assess(record, item, levels=[2, 2])
        # Tentativa independente indecidível mais recente: não interrompe.
        item5 = world.item(5)
        a5 = world.attempt(item5, 5, occurred=T0 + timedelta(minutes=4))
        world.assess(
            a5, item5, levels=[2], correctness=Assessment.Correctness.UNDECIDABLE
        )
        assert _state(env).status is TopicState.TopicStatus.FAVORABLE

    def test_r3i_assisted_critical_error_returns_to_mixed(self, env):
        service, store = env
        world = World(service, store)
        _favorable_setup(world)
        assert _state(env).status is TopicState.TopicStatus.FAVORABLE
        item5 = world.item(5)
        a5 = world.attempt(
            item5, 5, occurred=T0 + timedelta(minutes=4), help_level=1
        )
        world.assess(a5, item5, levels=[0, 2],
                     correctness=Assessment.Correctness.PARTIAL)
        # §8: novo erro crítico volta a mixed MESMO ASSISTIDO.
        assert _state(env).status is TopicState.TopicStatus.MIXED

    def test_r4_no_evidence_is_insufficient(self, env):
        service, store = env
        world = World(service, store)
        item = world.item(1)
        record = world.attempt(item, 1, occurred=T0)
        # Única avaliação é em abstinência → zero evidência inferencial.
        world.assess(
            record, item, levels=[0],
            reliability=Assessment.Reliability.ABSTAIN,
        )
        state = _state(env)
        assert state.status is TopicState.TopicStatus.INSUFFICIENT
        assert state.independent_attempt_ids == []
        assert state.last_attempt_at is None

    def test_r5_late_assessment_does_not_change_order(self, env):
        service, store = env
        world = World(service, store)
        items = [world.item(f) for f in (1, 2, 3)]
        records = [
            world.attempt(item, family, occurred=T0 + timedelta(minutes=i))
            for i, (item, family) in enumerate(zip(items, (1, 2, 3)))
        ]
        # Avaliações submetidas em ordem DIFERENTE da cronológica: A2, A3, A1.
        world.assess(records[1], items[1], levels=[2, 2])
        world.assess(records[2], items[2], levels=[2, 2])
        world.assess(records[0], items[0], levels=[2, 2])
        state = _state(env)
        assert state.status is TopicState.TopicStatus.FAVORABLE
        assert state.last_attempt_at == T0 + timedelta(minutes=2)
        # Ordem cronológica (occurred_at), não de submissão.
        assert state.independent_attempt_ids == [
            records[0].attempt_id,
            records[1].attempt_id,
            records[2].attempt_id,
        ]

    def test_r6_supersedes_recalculates_projection(self, env):
        service, store = env
        world = World(service, store)
        item1 = world.item(1)
        a1 = world.attempt(item1, 1, occurred=T0)
        world.assess(a1, item1, levels=[0, 2],
                     correctness=Assessment.Correctness.PARTIAL)
        item2 = world.item(2)
        a2 = world.attempt(item2, 2, occurred=T0 + timedelta(minutes=1))
        world.assess(a2, item2, levels=[2, 2])
        item3 = world.item(3)
        a3 = world.attempt(item3, 3, occurred=T0 + timedelta(minutes=2))
        world.assess(a3, item3, levels=[2, 2])
        # Avaliação tardia/corrigida da tentativa antiga: erro crítico era
        # falso positivo → projeção recalculada desde eventos.
        first = service.load_facts(UID)[1]
        first_id = next(
            f.assessment_id
            for f in first
            if f.attempt_id == a1.attempt_id
            and f.assessment_revision == 1
        )
        result = world.assess(
            a1, item1, levels=[2, 2], revision=2,
            supersedes=Ref(kind="assessment", id=first_id, version=1),
        )
        assert result.accepted
        state = _state(env)
        assert state.status is TopicState.TopicStatus.FAVORABLE

    def test_r7_revision_uniqueness_and_supersedes_strictness(self, env):
        service, store = env
        world = World(service, store)
        item = world.item(1)
        record = world.attempt(item, 1, occurred=T0)
        world.assess(record, item, levels=[2, 2])
        # Mesma revision → unicidade lógica (§15.2).
        with pytest.raises(EduAgentError) as excinfo:
            world.assess(record, item, levels=[2, 2])
        assert excinfo.value.code is ErrorCode.SCHEMA_INVALID
        # revision 2 sem supersedes → recusada.
        with pytest.raises(EduAgentError) as excinfo:
            world.assess(record, item, levels=[2, 2], revision=2)
        assert excinfo.value.code is ErrorCode.SCHEMA_INVALID
        # revision 1 com supersedes → recusada.
        other = _uid(999)
        with pytest.raises(EduAgentError):
            world.assess(
                record, item, levels=[2, 2], revision=1,
                supersedes=Ref(kind="assessment", id=other, version=1),
            )
        # supersedes que não aponta para a vigente → recusada.
        with pytest.raises(EduAgentError):
            world.assess(
                record, item, levels=[2, 2], revision=2,
                supersedes=Ref(kind="assessment", id=other, version=1),
            )

    def test_r8_abstain_never_updates_state(self, env):
        service, store = env
        world = World(service, store)
        item = world.item(1)
        record = world.attempt(item, 1, occurred=T0)
        # Abstinência com marcador de nível 0 em critério CRÍTICO: não pode
        # registrar erro crítico nem evidência.
        world.assess(
            record, item, levels=[0, 0],
            reliability=Assessment.Reliability.ABSTAIN,
        )
        state = _state(env)
        assert state.status is TopicState.TopicStatus.INSUFFICIENT
        # Tentativa seguinte correta: só ela compõe o estado.
        item2 = world.item(2)
        a2 = world.attempt(item2, 2, occurred=T0 + timedelta(minutes=1))
        world.assess(a2, item2, levels=[2, 2])
        state = _state(env)
        assert state.status is TopicState.TopicStatus.MIXED
        assert state.independent_attempt_ids == [a2.attempt_id]

    def test_r9_multitopic_criterion_does_not_update_topics(self, env):
        service, store = env
        world = World(service, store)
        item = world.item(1)
        record = world.attempt(item, 1, occurred=T0)
        results = [
            Assessment.CriterionResult(
                criterion_id="c1",
                topic_ids=[_uuid.UUID(TOPIC_A), _uuid.UUID(TOPIC_B)],
                level=2,
                evidence_kind=Assessment.EvidenceKind.PRESENT,
                response_span=(0, 10),
                reason="multicomponente não decomposto",
            ),
        ]
        assessment = Assessment(
            attempt_id=record.attempt_id,
            item_ref=Ref(kind="item", id=item, version=1),
            assessment_revision=1,
            supersedes=None,
            criterion_results=results,
            correctness=Assessment.Correctness.CORRECT,
            help_level=0,
            revealed=False,
            evidence_ids=[],
            reliability=Assessment.Reliability.ACCEPTED,
            reason="avaliação de teste",
        )
        service.check(
            user_id=UID, session_id=SESSION, assessment=assessment,
            critical_criterion_ids=[],
        )
        # §15.2: tentativa multicomponente não atualiza estado desses tópicos.
        for topic in (TOPIC_A, TOPIC_B):
            state = service.topic_state(UID, _uuid.UUID(topic))
            assert state is not None
            assert state.status is TopicState.TopicStatus.INSUFFICIENT
        # Critério de tópico único atualiza normalmente.
        item2 = world.item(2)
        a2 = world.attempt(item2, 2, occurred=T0 + timedelta(minutes=1))
        world.assess(a2, item2, levels=[2, 2])
        state = service.topic_state(UID, _uuid.UUID(TOPIC_A))
        assert state.status is TopicState.TopicStatus.MIXED

    def test_r10_ordinal_tiebreak_on_same_timestamp(self, env):
        service, store = env
        world = World(service, store)
        item1 = world.item(1)
        a1 = world.attempt(item1, 1, occurred=T0)  # ordinal 1, erro crítico
        world.assess(a1, item1, levels=[0, 2],
                     correctness=Assessment.Correctness.PARTIAL)
        item2 = world.item(2)
        a2 = world.attempt(item2, 2, occurred=T0)  # ordinal 2, correta
        world.assess(a2, item2, levels=[2, 2])
        item3 = world.item(3)
        a3 = world.attempt(item3, 3, occurred=T0 + timedelta(minutes=1))
        world.assess(a3, item3, levels=[2, 2])
        item4 = world.item(4)
        a4 = world.attempt(item4, 4, occurred=T0 + timedelta(minutes=2))
        world.assess(a4, item4, levels=[2, 2])
        # Com desempate por ordinal, as três mais recentes são A2, A3, A4 —
        # todas corretas e posteriores ao erro crítico (A1) → favorable.
        assert _state(env).status is TopicState.TopicStatus.FAVORABLE


# ---------------------------------------------------------------------------
# Serviço / migração (S1, S2) e projeção pura
# ---------------------------------------------------------------------------


class TestStorageAndService:
    def test_s1_migration_0004_columns(self, env):
        _, store = env
        columns = {
            row["name"]
            for row in store._conn.execute("PRAGMA table_info(attempts)")
        }
        assert {"family_id", "independent"} <= columns
        with pytest.raises(Exception):
            store._conn.execute(
                "INSERT INTO attempts(id, user_id, item_id, help_level, "
                "revealed, attempt_ordinal, independent) VALUES "
                "('x', ?, 'y', 0, 0, 1, 2)",
                (UID,),
            )

    def test_s2_ordinal_and_independence_at_commit(self, env):
        service, store = env
        world = World(service, store)
        item1 = world.item(1)
        item2 = world.item(2)
        first = world.attempt(item1, 1, occurred=T0)
        second = world.attempt(
            item2, 2, occurred=T0, help_level=2
        )
        assert first.attempt_ordinal == 1
        assert second.attempt_ordinal == 2
        assert first.independent is True
        assert second.independent is False
        # Independência também é julgada por reveal/exposição da família.
        third = world.attempt(
            world.item(3), 3, occurred=T0, revealed=True
        )
        assert third.independent is False
        fourth = world.attempt(
            world.item(4), 4, occurred=T0, seen=True
        )
        assert fourth.independent is False

    def test_pure_projection_ignores_abstain_as_current(self, env):
        service, store = env
        attempt = AttemptFact(
            attempt_id=_uid(5001),
            item_id=_uid(6001),
            family_id=_uid(1),
            occurred_at=T0,
            attempt_ordinal=1,
            help_level=0,
            revealed=False,
            independent=True,
        )
        def _fact(revision, reliability, correctness):
            result = Assessment.CriterionResult(
                criterion_id="c1",
                topic_ids=[_uuid.UUID(TOPIC_A)],
                level=2,
                evidence_kind=Assessment.EvidenceKind.PRESENT,
                response_span=(0, 5),
                reason="ok",
            )
            return AssessmentFact(
                assessment_id=_uid(7000 + revision),
                attempt_id=attempt.attempt_id,
                assessment_revision=revision,
                results=(result,),
                correctness=correctness,
                reliability=reliability,
                critical_criterion_ids=frozenset({"c1"}),
            )
        abstain = _fact(
            1, Assessment.Reliability.ABSTAIN,
            Assessment.Correctness.UNDECIDABLE,
        )
        accepted = _fact(
            2, Assessment.Reliability.ACCEPTED,
            Assessment.Correctness.CORRECT,
        )
        states = compute_topic_states([attempt], [abstain, accepted])
        topic = _uuid.UUID(TOPIC_A)
        assert topic in states
        assert states[topic].status is TopicState.TopicStatus.MIXED
        # Abstain nunca é vigente: a vigente é a maior revision aceita.
        only_abstain = compute_topic_states([attempt], [abstain])
        assert topic not in only_abstain
