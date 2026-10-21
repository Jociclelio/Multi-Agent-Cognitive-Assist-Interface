"""Testes de aceite da task 011 — demandas (política evidência→demanda v1,
mapa §15.3) e atividades/dependências (mapa §15.4); ``StudyDemand`` §4,
Storage (004), contratos (003), commit idempotente (005), redutor (009).

Não é a suíte quantitativa da etapa 8 (mapa de testes): testes locais de
curta duração, sem chamada ao modelo real. C4 (mapa intocado, commits
separados, submódulo intocado) é verificado por inspeção de git e
registrado no task.md.

Tabela de testes (código → caso):

| Código | Caso |
|---|---|
| P1 | erro crítico → revisão no próximo dia local com disponibilidade, classe1 |
| P2 | acerto independente → candidatos de recuperação 1/3/7 dias da ocorrência local |
| P3 | unicidade por chave: segunda geração consolida (uma pendente por chave) |
| P4 | retry com mesmo operation_id devolve recibo original, sem nova demanda |
| P5 | prioridades 1–3: prova ≤48h→1, ≤7d→2, vencida→2, recorrente→2, demais→3 |
| P6 | ausência de avaliação não inventa urgência (sem prova → nada de classe 1/2) |
| P7 | prazo pedagógico com dia sem hora: sugerir antes do dia, sem datetime duro |
| P8 | prazo pedagógico com avaliação datada: menor entre due e início confirmado |
| P9 | revisão vencida mantém due original e expõe overdue=True |
| P10 | sem disponibilidade no horizonte → pendente para o próximo horizonte |
| P11 | review_due registrado na projeção do tópico (primeiro pendente) |
| P12 | dificuldade recorrente: 2 erros aceitos em famílias distintas nas últimas 5 |
| D1 | catálogo de duração (practice=30, review=15, flashcard=15) estimated, mandatory=false |
| D2 | duração confirmada prevalece; confirmação habilita mandatory (contrato §4) |
| D3 | nenhuma conversão de domínio em duração (estimate=null nunca vira minutos) |
| A1 | planned→started→completed; started bloqueia intervalo aprovado (fixo, uma vez) |
| A2 | complete direto de planned aceita início/fim reais informados; sem eles, recusa |
| A3 | sair de completed: transição ordinária recusada; correção explícita funciona |
| A4 | scheduler não presume falta por relógio: relógio avançado não marca missed |
| A5 | sessão além do fim previsto: conflito registrado até término esclarecer |
| A6 | transição fora do conjunto (started→missed) é recusa tipada |
| A7 | replan uma vez por evento: retry do mesmo operation_id não duplica evento |
| A8 | expected_version divergente → VERSION_CONFLICT (§15.1/§11) |
| A9 | dependência referencia demanda (não tópico); ciclo é erro tipado |
| A10 | semântica de dependência: satisfied / waits_confirmed_end / blocked / ready |
| A11 | splittable: sem confirmação ou soma < duração → recusa; confirmado → subdemandas |
| M1 | migração 0006: índice único parcial impede segunda pendente da mesma chave |
"""

from __future__ import annotations

import sqlite3
import uuid as _uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from eduagent.agents.planner import (
    ActivityUpdate,
    PlannerAgent,
)
from eduagent.contracts import (
    Assessment,
    EduAgentError,
    ErrorCode,
    StudyDemand,
    TopicState,
)
from eduagent.services.effects import EffectsService
from eduagent.services.scheduling import (
    ConfirmedExam,
    DemandService,
    PolicyOutcome,
    has_recurrent_difficulty,
)
from eduagent.storage.repository import DomainStore

UID = "123e4567-e89b-12d3-a456-426614174000"
COURSE = "c0000000-0000-0000-0000-000000000001"
TOPIC_A = "aaaaaaaa-0000-0000-0000-000000000001"
TOPIC_B = "aaaaaaaa-0000-0000-0000-000000000002"
EXAM_FACT = "bbbbbbbb-0000-0000-0000-000000000001"

T0 = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)  # terça-feira


def _uid(n: int) -> _uuid.UUID:
    return _uuid.UUID(f"00000000-0000-0000-0000-{n:012d}")


class FakeClock:
    """Relógio injetável que avança um minuto por leitura."""

    def __init__(self, start: datetime = T0) -> None:
        self._moment = start

    def __call__(self) -> datetime:
        self._moment += timedelta(minutes=1)
        return self._moment


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
        ],
    )
    clock = FakeClock()
    effects = EffectsService(store)
    demands = DemandService(store, effects, clock=clock)
    planner = PlannerAgent(store, effects, clock=clock)
    yield store, effects, demands, planner, clock
    store.close()


def _attempt(attempt_id, family_id, occurred, ordinal):
    from eduagent.services.assessment import AttemptFact

    return AttemptFact(
        attempt_id=attempt_id,
        item_id=_uid(900),
        family_id=family_id,
        occurred_at=occurred,
        attempt_ordinal=ordinal,
        help_level=0,
        revealed=False,
        independent=True,
    )


def _assessment(attempt_id, revision, level, *, topic=TOPIC_A):
    from eduagent.services.assessment import AssessmentFact

    return AssessmentFact(
        assessment_id=_uuid.uuid4(),
        attempt_id=attempt_id,
        assessment_revision=revision,
        results=(
            Assessment.CriterionResult(
                criterion_id="c1",
                topic_ids=[_uuid.UUID(topic)],
                level=level,
                evidence_kind=Assessment.EvidenceKind.PRESENT,
                response_span=(0, 3),
                reason="julgamento de teste",
            ),
        ),
        correctness=(
            Assessment.Correctness.CORRECT
            if level == 2
            else (
                Assessment.Correctness.INCORRECT
                if level == 0
                else Assessment.Correctness.PARTIAL
            )
        ),
        reliability=Assessment.Reliability.ACCEPTED,
        critical_criterion_ids=frozenset(),
    )


# ---------------------------------------------------------------------------
# C1 — política evidência→demanda v1 (§15.3)
# ---------------------------------------------------------------------------


def test_p1_erro_critico_gera_revisao_proximo_dia_classe1(env):
    _, _, demands, _, _ = env
    generation = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        critical_error=True,
        operation_id=str(_uid(1)),
    )
    assert generation.created and not generation.consolidated
    record = generation.demand
    # Próximo dia local com disponibilidade (ocorrência terça → quarta).
    assert record.due_local_date == date(2026, 10, 21)
    assert record.demand.priority_class == 1
    assert record.policy_version == "assessment_review_policy_v1"
    assert record.activity_kind == "review"
    assert record.demand.kind.value == "review"


def test_p2_acerto_independente_candidatos_1_3_7(env):
    _, _, demands, _, _ = env
    generation = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.RECOVERY_AFTER_CORRECT,
        operation_id=str(_uid(10)),
    )
    # Três candidatos de recuperação a partir da ocorrência local (§15.3).
    dues = sorted(record.due_local_date for record in generation.demands)
    assert dues == [date(2026, 10, 21), date(2026, 10, 23), date(2026, 10, 27)]
    assert all(record.demand.priority_class == 3 for record in generation.demands)
    pendings = demands.pending_demands(UID, topic_id=TOPIC_A)
    assert sorted(r.due_local_date for r in pendings) == dues


def test_p3_unicidade_por_chave_consolidacao(env):
    _, _, demands, _, _ = env
    evidence_1 = [_uid(71)]
    evidence_2 = [_uid(72)]
    first = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        evidence_ids=evidence_1,
        operation_id=str(_uid(20)),
    )
    assert first.created
    # Mesma chave (user, topic, kind, due, policy), outra operação:
    # consolida — todas as evidence_ids e prioridade mais alta.
    second = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        critical_error=True,  # classe1 > classe3 da primeira
        evidence_ids=evidence_2,
        operation_id=str(_uid(21)),
    )
    assert second.consolidated and not second.created
    assert second.demand.demand_id == first.demand.demand_id
    assert set(second.demand.demand.evidence_ids) == {*evidence_1, *evidence_2}
    assert second.demand.demand.priority_class == 1
    pendings = demands.pending_demands(UID, topic_id=TOPIC_A)
    assert len(pendings) == 1  # no máximo uma pendente por chave


def test_p4_retry_mesmo_operation_id_nao_gera_nova(env):
    store, _, demands, _, _ = env
    revision_before = store.domain_revision(UID)
    first = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        operation_id=str(_uid(30)),
    )
    retry = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        operation_id=str(_uid(30)),
    )
    assert retry.receipt.operation_id == first.receipt.operation_id
    assert retry.receipt.was_retry
    assert retry.receipt.domain_revision == first.receipt.domain_revision
    # Retry não incrementa (§15.1) e não gera novas demandas.
    assert store.domain_revision(UID) == revision_before + 1
    assert len(demands.pending_demands(UID, topic_id=TOPIC_A)) == 1


def test_p5_prioridades_por_proximidade_de_avaliacao(env):
    _, _, demands, _, _ = env
    # Prova confirmada dentro de 48h → classe1 (sem erro crítico).
    exam_48h = ConfirmedExam(
        fact_id=_uuid.UUID(EXAM_FACT),
        topic_id=_uuid.UUID(TOPIC_A),
        start=T0 + timedelta(hours=40),
        has_time=True,
    )
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        confirmed_exams=[exam_48h],
        operation_id=str(_uid(40)),
    )
    assert gen.demand.demand.priority_class == 1
    # Prova em 6 dias → classe2 (topico B, sem outras fontes de urgência).
    exam_6d = ConfirmedExam(
        fact_id=_uuid.UUID(EXAM_FACT),
        topic_id=_uuid.UUID(TOPIC_B),
        start=T0 + timedelta(days=6),
        has_time=True,
    )
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_B,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        confirmed_exams=[exam_6d],
        operation_id=str(_uid(41)),
    )
    assert gen.demand.demand.priority_class == 2
    # Dificuldade recorrente → classe2 (novo due, nova chave).
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_B,
        occurrence_utc=T0 + timedelta(days=2),
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        recurrent_difficulty=True,
        operation_id=str(_uid(42)),
    )
    assert gen.demand.demand.priority_class == 2
    # Revisão vencida → classe2: pendente de A vence após 3 dias.
    demands._clock = lambda: T0 + timedelta(days=3)
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0 + timedelta(days=2),  # due 23/10, chave nova
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        operation_id=str(_uid(43)),
    )
    assert gen.demand.demand.priority_class == 2
    # Demais revisões → classe3 (sem prova, sem vencida, sem recorrência).
    demands._clock = lambda: T0
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_B,
        occurrence_utc=T0 + timedelta(days=30),
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        operation_id=str(_uid(44)),
    )
    assert gen.demand.demand.priority_class == 3


def test_p6_ausencia_de_avaliacao_nao_inventa_urgencia(env):
    _, _, demands, _, _ = env
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        operation_id=str(_uid(50)),
    )
    # Sem prova confirmada e sem erro crítico → classe3, nunca 1/2.
    assert gen.demand.demand.priority_class == 3


def test_p7_prazo_pedagogico_dia_sem_hora(env):
    _, _, demands, _, _ = env
    # Avaliação confirmada só de dia (22/10): prazo permanece DATA (§6.3),
    # due já é anterior ao dia — nada promovido a datetime.
    exam_day = ConfirmedExam(
        fact_id=_uuid.UUID(EXAM_FACT),
        topic_id=_uuid.UUID(TOPIC_A),
        start=date(2026, 10, 22),
        has_time=False,
    )
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        confirmed_exams=[exam_day],
        operation_id=str(_uid(60)),
    )
    record = gen.demand
    assert record.due_local_date == date(2026, 10, 21)
    assert isinstance(record.demand.deadline, date)
    assert not isinstance(record.demand.deadline, datetime)
    assert record.demand.deadline == date(2026, 10, 21)
    # due que cairia no dia (ou depois) da prova é sugerido ANTES do dia:
    # ocorrência 20/10, candidato de recuperação +3 cairia em 23/10, prova
    # dia 23 → candidato limitado para 22/10 (antes do dia).
    exam_23 = ConfirmedExam(
        fact_id=_uuid.UUID(EXAM_FACT),
        topic_id=_uuid.UUID(TOPIC_B),
        start=date(2026, 10, 23),
        has_time=False,
    )
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_B,
        occurrence_utc=T0,
        outcome=PolicyOutcome.RECOVERY_AFTER_CORRECT,
        confirmed_exams=[exam_23],
        operation_id=str(_uid(61)),
    )
    clamped = [
        record
        for record in gen.demands
        if record.pending_next_horizon is False and record.before_exam_day
    ]
    assert len(clamped) >= 1
    assert clamped[0].due_local_date == date(2026, 10, 22)
    assert clamped[0].due_local_date < date(2026, 10, 23)
    assert isinstance(clamped[0].demand.deadline, date)


def test_p8_prazo_pedagogico_com_avaliacao_datada(env):
    _, _, demands, _, _ = env
    exam = ConfirmedExam(
        fact_id=_uuid.UUID(EXAM_FACT),
        topic_id=_uuid.UUID(TOPIC_A),
        start=T0 + timedelta(hours=20),  # 21/10 08:00 — antes do due 21/10
        has_time=True,
    )
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        confirmed_exams=[exam],
        operation_id=str(_uid(70)),
    )
    # Prazo pedagógico = menor entre due sugerido e início confirmado.
    assert gen.demand.demand.deadline == exam.start


def test_p9_revisao_vencida_mantem_due_original(env):
    _, _, demands, _, _ = env
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        operation_id=str(_uid(80)),
    )
    original_due = gen.demand.due_local_date
    # Relógio avança além do due: due NÃO muda; overdue indicado (§15.3 —
    # o solver busca primeiro bloco futuro indicando atraso).
    demands._clock = lambda: T0 + timedelta(days=3)
    pendings = demands.pending_demands(UID, topic_id=TOPIC_A)
    assert len(pendings) == 1
    assert pendings[0].due_local_date == original_due
    assert pendings[0].overdue is True


def test_p10_sem_disponibilidade_pendente_proximo_horizonte(env):
    _, _, demands, _, _ = env
    demands._availability = lambda day: False
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        operation_id=str(_uid(90)),
    )
    # Primeira data do horizonte, pendente para o próximo horizonte (§15.3).
    assert gen.demand.due_local_date == date(2026, 10, 21)
    assert gen.demand.pending_next_horizon is True


def test_p11_review_due_registrado_no_topico(env):
    store, _, demands, _, _ = env
    # Projeção do redutor (task 009) existe para o tópico.
    state = TopicState(
        topic_id=_uuid.UUID(TOPIC_A),
        independent_attempt_ids=[],
        assisted_attempt_ids=[],
        error_codes=[],
        last_attempt_at=None,
        status=TopicState.TopicStatus.MIXED,
        estimate=None,
        review_due=None,
        model_version="monitor-rules-mvp",
        revision=1,
    )
    store.execute_write(
        UID,
        [
            (
                "INSERT INTO topic_states(user_id, topic_id, revision, "
                "payload_json) VALUES (?,?,?,?)",
                (UID, TOPIC_A, 1, state.model_dump_json()),
            ),
        ],
    )
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        operation_id=str(_uid(100)),
    )
    assert gen.review_due == gen.demand.due_local_date
    stored = store.fetch_user_rows(
        "SELECT payload_json FROM topic_states WHERE user_id = ? AND "
        "topic_id = ?",
        (UID, TOPIC_A),
    )[0]
    projected = TopicState.model_validate_json(stored["payload_json"])
    assert projected.review_due == gen.demand.due_local_date
    # Tópico sem projeção: review_due fica só na demanda (nada inventado).
    gen_b = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_B,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        operation_id=str(_uid(101)),
    )
    assert gen_b.review_due == gen_b.demand.due_local_date


def test_p12_dificuldade_recorrente_familias_distintas(env):
    family_1, family_2 = _uid(201), _uid(202)
    base = T0 - timedelta(days=6)
    # 5 tentativas no tópico; erros aceitos em DUAS famílias distintas.
    attempts = [
        _attempt(_uid(210 + i), family, base + timedelta(days=i), i + 1)
        for i, family in enumerate([family_1, family_1, family_2, family_1, family_2])
    ]
    assessments = [
        _assessment(_uid(210), 1, 2),  # acerto família 1
        _assessment(_uid(211), 1, 0),  # erro família 1
        _assessment(_uid(212), 1, 0),  # erro família 2
        _assessment(_uid(213), 1, 2),  # acerto família 1
        _assessment(_uid(214), 1, 2),  # acerto família 2
    ]
    assert (
        has_recurrent_difficulty(attempts, assessments, _uuid.UUID(TOPIC_A))
        is True
    )
    # Erros em família única entre as últimas 5 → não é recorrente.
    attempts_same = [
        _attempt(_uid(220 + i), family, base + timedelta(days=i), i + 1)
        for i, family in enumerate([family_1, family_1, family_1, family_1, family_2])
    ]
    assessments_same = [
        _assessment(_uid(220), 1, 2),
        _assessment(_uid(221), 1, 0),  # erro família 1
        _assessment(_uid(222), 1, 2),
        _assessment(_uid(223), 1, 0),  # erro família 1 (mesma família)
        _assessment(_uid(224), 1, 2),
    ]
    assert (
        has_recurrent_difficulty(
            attempts_same, assessments_same, _uuid.UUID(TOPIC_A)
        )
        is False
    )
    # Menos de dois erros → False.
    assert (
        has_recurrent_difficulty(
            attempts_same,
            [
                _assessment(_uid(220), 1, 2),
                _assessment(_uid(221), 1, 0),
                _assessment(_uid(222), 1, 2),
                _assessment(_uid(223), 1, 2),
                _assessment(_uid(224), 1, 2),
            ],
            _uuid.UUID(TOPIC_A),
        )
        is False
    )
    # Tentativa sem avaliação aceita não conta como erro.
    assert (
        has_recurrent_difficulty(
            attempts_same,
            [
                _assessment(
                    _uid(221),
                    1,
                    0,
                ),
                _assessment(_uid(223), 1, 2),
            ],
            _uuid.UUID(TOPIC_A),
        )
        is False
    )


# ---------------------------------------------------------------------------
# C2 — durações (§15.3)
# ---------------------------------------------------------------------------


def test_d1_catalogo_estimado_mandatory_false(env):
    _, _, demands, _, _ = env
    gen_review = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        operation_id=str(_uid(120)),
    )
    assert gen_review.demand.demand.duration_minutes == 15
    assert (
        gen_review.demand.demand.duration_status
        == gen_review.demand.demand.DurationStatus.ESTIMATED
    )
    assert gen_review.demand.demand.mandatory is False
    gen_practice = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_B,
        occurrence_utc=T0,
        outcome=PolicyOutcome.RECOVERY_AFTER_CORRECT,
        activity_kind="practice",
        operation_id=str(_uid(121)),
    )
    assert gen_practice.demand.demand.duration_minutes == 30
    gen_flash = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_B,
        occurrence_utc=T0,
        outcome=PolicyOutcome.RECOVERY_AFTER_CORRECT,
        activity_kind="flashcard",
        operation_id=str(_uid(122)),
    )
    assert gen_flash.demand.demand.duration_minutes == 15


def test_d2_confirmado_prevalece_e_habilita_mandatory(env):
    _, _, demands, _, _ = env
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        operation_id=str(_uid(130)),
    )
    demand_id = gen.demand.demand_id
    confirmed = demands.confirm_duration(
        UID, demand_id, minutes=45, mandatory=True, operation_id=str(_uid(131))
    )
    assert confirmed.demand.duration_minutes == 45
    assert (
        confirmed.demand.duration_status
        == confirmed.demand.DurationStatus.CONFIRMED
    )
    assert confirmed.demand.mandatory is True
    # mandatory com estimated é recusado pelo contrato (§4/§15.3) —
    # reconstrução (validadores rodam) com mandatory=True e estimated falha.
    data = gen.demand.demand.model_dump()
    data["mandatory"] = True
    with pytest.raises(ValueError):
        StudyDemand(**data)


def test_d3_nenhuma_conversao_de_dominio_em_duracao(env):
    store, _, demands, _, _ = env
    # Estado favorável (estimate=null no MVP) não altera duração estimada.
    state = TopicState(
        topic_id=_uuid.UUID(TOPIC_A),
        independent_attempt_ids=[_uid(1)],
        assisted_attempt_ids=[],
        error_codes=[],
        last_attempt_at=T0,
        status=TopicState.TopicStatus.FAVORABLE,
        estimate=None,
        review_due=None,
        model_version="monitor-rules-mvp",
        revision=1,
    )
    assert state.estimate is None
    store.execute_write(
        UID,
        [
            (
                "INSERT INTO topic_states(user_id, topic_id, revision, "
                "payload_json) VALUES (?,?,?,?)",
                (UID, TOPIC_A, 1, state.model_dump_json()),
            ),
        ],
    )
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.RECOVERY_AFTER_CORRECT,
        operation_id=str(_uid(140)),
    )
    # Domínio favorável NÃO reduz nem amplia duração: catálogo segue.
    assert gen.demand.demand.duration_minutes == 15
    assert (
        gen.demand.demand.duration_status
        == gen.demand.demand.DurationStatus.ESTIMATED
    )


# ---------------------------------------------------------------------------
# C3 — atividades e dependências (§15.4)
# ---------------------------------------------------------------------------


def _register_block(planner: PlannerAgent, **kwargs):
    defaults = dict(
        planned_start_utc=T0 + timedelta(hours=24),
        planned_end_utc=T0 + timedelta(hours=25),
        source_demand_id=None,
    )
    defaults.update(kwargs)
    return planner.register_block(UID, **defaults)


def _update(planner, store, block, status, occurred, operation, **extra):
    return planner.update_activity(
        UID,
        ActivityUpdate(
            block_id=block.block_id,
            status=status,
            occurred_at=occurred,
            expected_version=store.domain_revision(UID),
            operation_id=operation,
            **extra,
        ),
    )


def test_a1_started_bloca_intervalo_aprovado_uma_vez(env):
    store, _, _, planner, _ = env
    block = _register_block(planner)
    assert block.status == "planned"
    assert planner.fixed_occupation(UID) == []  # planned não ocupa
    result = _update(
        planner,
        store,
        block,
        "started",
        block.planned_start_utc + timedelta(minutes=15),
        str(_uid(150)),
    )
    assert result.receipt.was_retry is False
    assert result.block.status == "started"
    assert result.replan_requested and result.replan_event_id
    occupation = planner.fixed_occupation(UID)
    assert len(occupation) == 1  # fixo inserido uma vez
    assert occupation[0][0] == block.block_id
    assert occupation[0][1] == block.planned_start_utc + timedelta(minutes=15)
    assert occupation[0][2] == block.planned_end_utc  # intervalo aprovado
    # Complete com término real: ocupa [início real, fim real].
    end_real = block.planned_end_utc + timedelta(minutes=30)
    done = _update(
        planner,
        store,
        block,
        "completed",
        end_real,
        str(_uid(151)),
        actual_end=end_real,
    )
    assert done.block.status == "completed"
    occupation = planner.fixed_occupation(UID)
    assert len(occupation) == 1
    assert occupation[0][2] == end_real


def test_a2_complete_direto_de_planned_exige_reais(env):
    store, _, _, planner, _ = env
    block = _register_block(planner)
    # Sem início/fim reais informados: recusa tipada (§15.4).
    with pytest.raises(EduAgentError) as exc:
        _update(
            planner,
            store,
            block,
            "completed",
            block.planned_end_utc,
            str(_uid(160)),
        )
    assert exc.value.code is ErrorCode.SCHEMA_INVALID
    # Com início/fim reais informados: aceito direto de planned.
    result = _update(
        planner,
        store,
        block,
        "completed",
        block.planned_end_utc + timedelta(minutes=5),
        str(_uid(161)),
        actual_start=block.planned_start_utc,
        actual_end=block.planned_end_utc,
    )
    assert result.block.status == "completed"
    assert result.block.actual_start_utc == block.planned_start_utc
    assert result.block.actual_end_utc == block.planned_end_utc


def test_a3_sair_de_completed_exige_correcao_explicita(env):
    store, _, _, planner, _ = env
    block = _register_block(planner)
    _update(
        planner,
        store,
        block,
        "completed",
        block.planned_end_utc,
        str(_uid(170)),
        actual_start=block.planned_start_utc,
        actual_end=block.planned_end_utc,
    )
    # Transição ordinária saindo de completed: recusa tipada (§15.4).
    with pytest.raises(EduAgentError) as exc:
        _update(
            planner,
            store,
            block,
            "missed",
            block.planned_end_utc + timedelta(hours=1),
            str(_uid(171)),
        )
    assert exc.value.code is ErrorCode.SCHEMA_INVALID
    assert "correção explícita" in exc.value.message
    # Correção explícita: único caminho que altera completed.
    corrected = planner.correct_activity(
        UID,
        ActivityUpdate(
            block_id=block.block_id,
            status="started",
            occurred_at=block.planned_start_utc,
            expected_version=store.domain_revision(UID),
            operation_id=str(_uid(172)),
        ),
    )
    assert corrected.block.status == "started"
    # correct_activity fora de completed: recusa.
    with pytest.raises(EduAgentError):
        planner.correct_activity(
            UID,
            ActivityUpdate(
                block_id=block.block_id,
                status="completed",
                occurred_at=block.planned_end_utc,
                expected_version=store.domain_revision(UID),
                operation_id=str(_uid(173)),
            ),
        )


def test_a4_scheduler_nao_presume_falta_por_relogio(env):
    store, _, _, planner, _ = env
    block = _register_block(planner)
    # Relógio avança muito além do fim previsto: nada muda sozinho (§15.4:
    # missed é declaração do aluno ou atraso confirmado — nunca relógio).
    planner._clock = lambda: T0 + timedelta(days=5)
    record = planner.get_block(UID, block.block_id)
    assert record.status == "planned"
    assert planner.fixed_occupation(UID) == []
    # Falta só por declaração explícita.
    declared = _update(
        planner,
        store,
        block,
        "missed",
        T0 + timedelta(days=5),
        str(_uid(180)),
    )
    assert declared.block.status == "missed"
    assert planner.fixed_occupation(UID) == []  # liberou o intervalo


def test_a5_sessao_alem_do_fim_previsto_registra_conflito(env):
    store, _, _, planner, _ = env
    block = _register_block(planner)
    # Sessão declarada iniciada ALÉM do fim previsto (sessão continua além
    # do intervalo aprovado): conflito registrado até esclarecimento; a
    # atualização de término é pedida antes do solver (§15.4).
    late_start = block.planned_end_utc + timedelta(minutes=45)
    conflict = _update(
        planner,
        store,
        block,
        "started",
        late_start,
        str(_uid(190)),
    )
    assert conflict.end_conflict is True
    assert "término" in conflict.message
    # Ocupação continua (intervalo aprovado bloqueado até esclarecer).
    assert len(planner.fixed_occupation(UID)) == 1
    # Término real informado esclarece o conflito.
    resolved = _update(
        planner,
        store,
        block,
        "completed",
        late_start + timedelta(minutes=30),
        str(_uid(191)),
        actual_end=late_start + timedelta(minutes=30),
    )
    assert resolved.end_conflict is False
    assert resolved.block.actual_end_utc == late_start + timedelta(minutes=30)
    # Início dentro do previsto não registra conflito.
    other = _register_block(planner)
    normal = _update(
        planner,
        store,
        other,
        "started",
        other.planned_start_utc,
        str(_uid(192)),
    )
    assert normal.end_conflict is False


def test_a6_transicao_fora_do_conjunto_recusada(env):
    store, _, _, planner, _ = env
    block = _register_block(planner)
    _update(
        planner, store, block, "started", block.planned_start_utc, str(_uid(200))
    )
    with pytest.raises(EduAgentError) as exc:
        _update(
            planner,
            store,
            block,
            "missed",
            block.planned_end_utc,
            str(_uid(201)),
        )
    assert exc.value.code is ErrorCode.SCHEMA_INVALID


def test_a7_replan_uma_vez_por_evento(env):
    store, _, _, planner, _ = env
    block = _register_block(planner)
    operations_before = store.fetch_user_rows(
        "SELECT count(*) AS n FROM operations WHERE user_id = ?", (UID,)
    )[0]["n"]
    result = _update(
        planner,
        store,
        block,
        "started",
        block.planned_start_utc,
        str(_uid(210)),
    )
    assert result.replan_requested is True
    operations_after = store.fetch_user_rows(
        "SELECT count(*) AS n FROM operations WHERE user_id = ?", (UID,)
    )[0]["n"]
    assert operations_after == operations_before + 1
    # Retry do MESMO evento: recibo original, sem segundo evento/replan.
    retry = _update(
        planner,
        store,
        block,
        "started",
        block.planned_start_utc,
        str(_uid(210)),
    )
    assert retry.receipt.was_retry is True
    assert retry.replan_event_id == result.replan_event_id
    operations_retry = store.fetch_user_rows(
        "SELECT count(*) AS n FROM operations WHERE user_id = ?", (UID,)
    )[0]["n"]
    assert operations_retry == operations_after
    assert planner.get_block(UID, block.block_id).event_sequence == 1


def test_a8_expected_version_divergente(env):
    _, _, _, planner, _ = env
    block = _register_block(planner)
    with pytest.raises(EduAgentError) as exc:
        planner.update_activity(
            UID,
            ActivityUpdate(
                block_id=block.block_id,
                status="started",
                occurred_at=block.planned_start_utc,
                expected_version=99,
                operation_id=str(_uid(220)),
            ),
        )
    assert exc.value.code is ErrorCode.VERSION_CONFLICT


def test_a9_dependencia_referencia_demanda_e_ciclo_erro(env):
    _, _, demands, planner, _ = env
    d1 = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        operation_id=str(_uid(230)),
    )
    d2 = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_B,
        occurrence_utc=T0,
        outcome=PolicyOutcome.RECOVERY_AFTER_CORRECT,
        operation_id=str(_uid(231)),
    )
    planner.declare_dependency(
        UID,
        dependent_demand_id=d2.demand.demand_id,
        predecessor_demand_id=d1.demand.demand_id,
        operation_id=str(_uid(232)),
    )
    # Ciclo: d1 depender de d2 (que já depende de d1) é erro tipado (§9).
    with pytest.raises(EduAgentError) as exc:
        planner.declare_dependency(
            UID,
            dependent_demand_id=d1.demand.demand_id,
            predecessor_demand_id=d2.demand.demand_id,
            operation_id=str(_uid(233)),
        )
    assert exc.value.code is ErrorCode.SCHEMA_INVALID
    assert "cíclica" in exc.value.message
    # Dependência referenciada no payload da demanda (não ID de tópico).
    stored = demands.get_demand(UID, d2.demand.demand_id)
    assert [ref.id for ref in stored.demand.dependencies] == [
        d1.demand.demand_id
    ]


def test_a10_semantica_de_dependencia(env):
    store, _, demands, planner, _ = env
    dep = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        operation_id=str(_uid(240)),
    )
    pred = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_B,
        occurrence_utc=T0,
        outcome=PolicyOutcome.RECOVERY_AFTER_CORRECT,
        operation_id=str(_uid(241)),
    )
    planner.declare_dependency(
        UID,
        dependent_demand_id=dep.demand.demand_id,
        predecessor_demand_id=pred.demand.demand_id,
        operation_id=str(_uid(242)),
    )
    horizon_end = T0 + timedelta(days=7)
    # Pendente dentro do horizonte: pronto para o solver.
    state = planner.dependency_state(
        UID,
        dependent_demand_id=dep.demand.demand_id,
        predecessor_demand_id=pred.demand.demand_id,
        horizon_end_utc=horizon_end,
    )
    assert state.state == "ready"
    # Bloco pendente planejado além do horizonte: bloqueia com razão.
    far_block = planner.register_block(
        UID,
        planned_start_utc=T0 + timedelta(days=30),
        planned_end_utc=T0 + timedelta(days=30, hours=1),
        source_demand_id=pred.demand.demand_id,
    )
    state = planner.dependency_state(
        UID,
        dependent_demand_id=dep.demand.demand_id,
        predecessor_demand_id=pred.demand.demand_id,
        horizon_end_utc=horizon_end,
    )
    assert state.state == "blocked_outside_horizon"
    assert "horizonte" in state.reason
    # Iniciado: ocupa fixo, dependente espera término confirmado.
    planner.update_activity(
        UID,
        ActivityUpdate(
            block_id=far_block.block_id,
            status="started",
            occurred_at=T0 + timedelta(days=30),
            expected_version=store.domain_revision(UID),
            operation_id=str(_uid(243)),
        ),
    )
    state = planner.dependency_state(
        UID,
        dependent_demand_id=dep.demand.demand_id,
        predecessor_demand_id=pred.demand.demand_id,
        horizon_end_utc=horizon_end,
    )
    assert state.state == "waits_confirmed_end"
    # Concluído: presença satisfeita com término real.
    planner.update_activity(
        UID,
        ActivityUpdate(
            block_id=far_block.block_id,
            status="completed",
            occurred_at=T0 + timedelta(days=30, hours=2),
            expected_version=store.domain_revision(UID),
            operation_id=str(_uid(244)),
            actual_end=T0 + timedelta(days=30, hours=2),
        ),
    )
    state = planner.dependency_state(
        UID,
        dependent_demand_id=dep.demand.demand_id,
        predecessor_demand_id=pred.demand.demand_id,
        horizon_end_utc=horizon_end,
    )
    assert state.state == "satisfied"


def test_a11_splittable_confirmado(env):
    _, _, demands, planner, _ = env
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        confirmed_duration_minutes=60,
        operation_id=str(_uid(250)),
    )
    demand_id = gen.demand.demand_id
    # Sem confirmação do usuário: recusa tipada (§15.4).
    with pytest.raises(EduAgentError) as exc:
        planner.declare_splittable(
            UID,
            demand_id,
            subtask_count=2,
            subtask_minutes=30,
            confirmed_by_user=False,
            operation_id=str(_uid(251)),
        )
    assert exc.value.code is ErrorCode.SCHEMA_INVALID
    # Soma < duração original: recusa.
    with pytest.raises(EduAgentError) as exc:
        planner.declare_splittable(
            UID,
            demand_id,
            subtask_count=2,
            subtask_minutes=20,  # 40 < 60
            confirmed_by_user=True,
            operation_id=str(_uid(252)),
        )
    assert "duração original" in exc.value.message
    # Sem declaração, split é recusado (indivisível por default).
    with pytest.raises(EduAgentError):
        planner.split_demand(UID, demand_id, operation_id=str(_uid(253)))
    # Declaração confirmada e soma ≥ duração: subdemandas criadas.
    planner.declare_splittable(
        UID,
        demand_id,
        subtask_count=2,
        subtask_minutes=30,
        confirmed_by_user=True,
        operation_id=str(_uid(254)),
    )
    subtasks = planner.split_demand(UID, demand_id, operation_id=str(_uid(255)))
    assert len(subtasks) == 2
    for sub in subtasks:
        record = demands.get_demand(UID, sub)
        assert record.status == "split"
        assert record.demand.duration_minutes == 30
        assert record.demand.mandatory is False
        assert [ref.id for ref in record.demand.dependencies] == [demand_id]
    # Subdemandas não colidem com a chave de pendentes (status 'split').
    assert len(demands.pending_demands(UID, topic_id=TOPIC_A)) == 1


# ---------------------------------------------------------------------------
# Migração 0006 — índice único parcial (§15.3)
# ---------------------------------------------------------------------------


def test_m1_indice_unico_parcial_impede_duplicata(env):
    store, _, demands, _, _ = env
    gen = demands.generate_review_demand(
        UID,
        topic_id=TOPIC_A,
        occurrence_utc=T0,
        outcome=PolicyOutcome.REVIEW_AFTER_ERROR,
        operation_id=str(_uid(260)),
    )
    with pytest.raises(sqlite3.IntegrityError):
        # Inserção direta de segunda pendente com a mesma chave é recusada
        # pelo índice único parcial (migração 0006) — a consolidação do
        # serviço é o caminho previsto (§15.3).
        store.execute_write(
            UID,
            [
                (
                    "INSERT INTO demands(id, user_id, payload_json, status, "
                    "revision, topic_id, activity_kind, due_local_date, "
                    "policy_version) VALUES (?,?,?,'pending',0,?,?,?,?)",
                    (
                        str(_uid(261)),
                        UID,
                        gen.demand.demand.model_dump_json(),
                        TOPIC_A,
                        "review",
                        gen.demand.due_local_date.isoformat(),
                        "assessment_review_policy_v1",
                    ),
                ),
            ],
        )
    # Demanda fora da política (colunas NULL) não colide.
    store.execute_write(
        UID,
        [
            (
                "INSERT INTO demands(id, user_id, payload_json, status, "
                "revision) VALUES (?,?,?,'pending',0)",
                (str(_uid(262)), UID, "{}"),
            ),
        ],
    )
