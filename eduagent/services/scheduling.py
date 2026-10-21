"""Serviço de agendamento — parte de demandas: política evidência→demanda
v1 determinística (mapa normativo §15.3; ``StudyDemand`` §4; contratos da
task 003, armazenamento da 004, commit idempotente da 005, redutor da 009).

A política é aplicada **por serviço, não pelo LLM** (§15.3: "o serviço
aplica política determinística e exige confirmação para mudança de dura";
o Planejador pode explicar ou propor alteração, mas nunca decide).
``eduagent/agents/planner.py`` (atividades, §15.4) consome estas demandas.

Contratos implementados (task 011, §15.3):

- **Política ``assessment_review_policy_v1``** sempre registrada na demanda
  (``policy_version``) e em ``review_due`` (``TopicState.review_due`` = data
  do primeiro candidato pendente, nunca probabilidade de esquecimento):
  - Tentativa aceita incorreta/parcial ou erro crítico → uma revisão
    sugerida no próximo dia local com disponibilidade; se não existir no
    horizonte, primeira data do horizonte.
  - Acerto independente → candidatos de recuperação em 1/3/7 dias a partir
    da ocorrência local (offsets do §8/§15.3; política configurável).
  - No máximo uma demanda pendente por
    ``(user, topic, activity_kind, due_local_date, policy_version)``
    (índice único parcial da migração 0006); retry do mesmo
    ``operation_id`` devolve o recibo original sem gerar novas (§11).
  - Referência a avaliação confirmada vem da relação ``assessment_topics``
    (migração 0006); prazo pedagógico de revisão = menor entre due sugerido
    e início confirmado da avaliação. Avaliação com dia sem hora → sugerir
    antes do dia **sem promover datetime duro** (o prazo permanece data;
    §6.3: prazo só de dia não ganha horário automático).
  - Revisão vencida mantém due original e é exposta com ``overdue=True``
    (o solver busca primeiro bloco futuro indicando atraso — §15.4/§9); o
    serviço nunca altera o due de revisão vencida. Revisão sem data
    agendável no horizonte fica ``pending_next_horizon=True`` (pendente
    para o próximo horizonte).
  - Prioridades (política de ensaio, NÃO inferência de retenção ótima):
    classe1 = avaliação confirmada em até 48h ou erro crítico; classe2 =
    avaliação em até 7 dias, revisão vencida, ou dois erros aceitos em
    famílias distintas entre as últimas 5 tentativas no tópico; classe3 =
    demais. **Ausência de avaliação não inventa urgência**: sem avaliação
    confirmada nenhuma classe 1/2 surge por proximidade de prova.
  - Duração: valor informado/confirmado prevalece (``confirmed``); na
    ausência, catálogo inicial estimado ``practice=30min``, ``review=15min``,
    ``flashcard=15min`` com rótulo ``estimated`` e ``mandatory=false``;
    usuário pode editar e confirmar para obrigatória (validador do contrato
    §4: mandatory exige ``duration_status='confirmed'``). **Não converter
    percentual de domínio em duração**: o redutor mantém ``estimate=null``
    no MVP (mapa §8) e nenhum caminho aqui lê estimativa de competência.
  - Demanda duplicada é consolidada com **todas** as ``evidence_ids`` e a
    regra de prioridade **mais alta** (classe1 > classe2 > classe3).

Defaults de horizonte (7 dias, §15.5) e offsets 1/3/7 são valores do mapa;
a disponibilidade por dia é injetável (o solver da task 012 é quem conhece
a grade): default de ensaio considera todos os dias disponíveis. Fuso local
só é aplicado quando explicitamente confirmado (plano: timezone
``America/Sao_Paulo`` apenas após confirmação) — sem confirmação, o dia
local é o dia UTC, escolha conservadora documentada.

Nada aqui apresenta resultados medidos: prioridades, janelas e catálogo são
política de ensaio a calibrar.
"""

from __future__ import annotations

import hashlib
import json
import time as _time
import uuid as _uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time as _dt_time, timedelta, timezone, tzinfo
from enum import Enum
from pathlib import Path
from typing import Any

from ortools.sat.python import cp_model

from eduagent.contracts import (
    Assessment,
    EduAgentError,
    ErrorCode,
    ScheduleProposal,
    SenderRole,
    StudyDemand,
    ToolName,
    TopicState,
    validate_tool_request,
)
from eduagent.services.effects import CommitRequest, EffectsService, EventSpec
from eduagent.storage.repository import DomainStore, Receipt

_DIAGNOSTIC = "eduagent/services/scheduling.py"

#: Versão da política determinística (§15.3) — registrada em demanda e
#: review_due. Mudanças de regra exigem nova versão.
POLICY_VERSION = "assessment_review_policy_v1"

#: Ação de commit idempotente (mapa §4 ``OperationAction.DEMAND_UPSERT``).
ACTION_DEMAND_UPSERT = "demand.upsert"

#: Kinds de evento (catálogo default de ensaio, como em MemoryPack.EventKind).
EVENT_DEMAND_GENERATED = "demand_generated"
EVENT_DEMAND_DURATION_CONFIRMED = "demand_duration_confirmed"

#: Catálogo inicial de duração estimada (§15.3 — escolhas de ensaio).
DURATION_CATALOG_MINUTES: dict[str, int] = {
    "practice": 30,
    "review": 15,
    "flashcard": 15,
}

#: Horizonte de planejamento (§15.5: sete datas) — valor do mapa.
HORIZON_DAYS = 7

#: Janelas de prioridade por proximidade de avaliação confirmada (§15.3).
EXAM_URGENT_HOURS = 48
EXAM_NEAR_DAYS = 7

#: Offsets de recuperação após acerto independente (§15.3/§8).
RECOVERY_OFFSETS_DAYS = (1, 3, 7)

#: Fator de conversão do prazo só de dia: sugestão anterior ao dia da
#: avaliação (§15.3: "sugerir antes desse dia").
_ONE_DAY = timedelta(days=1)


class PolicyOutcome(str, Enum):
    """Gatilho da política v1 (§15.3)."""

    #: Tentativa aceita incorreta/parcial ou erro crítico → revisão.
    REVIEW_AFTER_ERROR = "review_after_error"
    #: Acerto independente → candidatos de recuperação 1/3/7 dias.
    RECOVERY_AFTER_CORRECT = "recovery_after_correct"


#: Namespace determinístico para IDs de demanda derivados da chave de
#: unicidade (§15.3): retry recomputa o mesmo ID e o mesmo digest — a
#: dedup do §11 não depende de aleatoriedade.
_DEMAND_NAMESPACE = _uuid.uuid5(_uuid.NAMESPACE_URL, "eduagent:demand:v1")


def demand_key_id(
    user_id: str, topic_id: str, activity_kind: str, due: str, policy: str
) -> _uuid.UUID:
    """ID determinístico da demanda para a chave de unicidade da política."""
    return _uuid.uuid5(
        _DEMAND_NAMESPACE, "|".join([user_id, topic_id, activity_kind, due, policy])
    )


@dataclass(frozen=True)
class ConfirmedExam:
    """Avaliação confirmada (fato acadêmico ``status='confirmed'`` ligado ao
    tópico por ``assessment_topics``, §15.3). ``start`` é datetime com zona
    quando a avaliação tem hora; dia puro (``has_time=False``) nunca é
    promovido a datetime (§6.3/§15.3)."""

    fact_id: _uuid.UUID
    topic_id: _uuid.UUID
    start: datetime | date
    has_time: bool

    @property
    def day(self) -> date:
        if self.has_time:
            return self.start.date()  # type: ignore[union-attr]
        return self.start  # type: ignore[return-value]


@dataclass(frozen=True)
class DemandCandidate:
    """Candidato de demanda produzido pela política (§15.3) — entrada do
    ``StudyDemand`` persistido."""

    topic_id: _uuid.UUID
    activity_kind: str
    due_local_date: date
    priority_class: int  # 1..3
    duration_minutes: int
    duration_status: str  # 'confirmed' | 'estimated'
    mandatory: bool
    evidence_ids: tuple[_uuid.UUID, ...]
    deadline: datetime | date  # PartialDate (§4): dia puro ou datetime
    earliest: datetime
    origin: str  # 'review_after_error' | 'recovery_after_correct'
    policy_version: str = POLICY_VERSION
    #: Nenhum dia disponível no horizonte → pendente para o próximo
    #: horizonte (§15.3); o due registrado é a primeira data do horizonte.
    pending_next_horizon: bool = False
    #: Sugestão limitada pelo dia de avaliação só de data (sem datetime duro).
    before_exam_day: bool = False


@dataclass(frozen=True)
class DemandRecord:
    """Demanda projetada (linha ``demands``)."""

    demand_id: _uuid.UUID
    user_id: str
    topic_id: _uuid.UUID
    activity_kind: str
    due_local_date: date
    policy_version: str
    status: str
    demand: StudyDemand
    pending_next_horizon: bool = False
    before_exam_day: bool = False
    overdue: bool = False
    splittable_declaration: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class DemandGeneration:
    """Resultado de uma geração: recibo, demandas afetadas (novas ou
    consolidadas) e ``review_due`` vigente do tópico. ``demand`` é a
    primeira demanda gerada (conveniência para gerações de candidato único;
    recuperação gera as três em ``demands``)."""

    receipt: Receipt
    created: bool
    consolidated: bool
    demands: tuple[DemandRecord, ...]
    review_due: date | None

    @property
    def demand(self) -> DemandRecord:
        return self.demands[0]


def _digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _utc_iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat()


def _local_day(moment: datetime, tz: tzinfo | None) -> date:
    """Dia local da ocorrência; sem fuso confirmado, dia UTC (documentado)."""
    if tz is None:
        return moment.astimezone(timezone.utc).date()
    return moment.astimezone(tz).date()


# ---------------------------------------------------------------------------
# Política pura (§15.3) — determinística, testável sem banco
# ---------------------------------------------------------------------------


def next_available_day(
    start: date,
    *,
    availability: Callable[[date], bool],
    horizon_end: date,
) -> date | None:
    """Primeiro dia em ``[start, horizon_end]`` com disponibilidade."""
    day = start
    while day <= horizon_end:
        if availability(day):
            return day
        day += _ONE_DAY
    return None


def exam_priority_class(
    confirmed_exams: Sequence[ConfirmedExam], *, now_utc: datetime
) -> int | None:
    """Classe de urgência pela avaliação confirmada mais próxima (§15.3):
    até 48h → 1; até 7 dias → 2; sem avaliação válida → ``None`` (ausência
    de avaliação NÃO inventa urgência). Avaliação no passado não gera
    urgência. Avaliação só de dia: ≤ amanhã conta como ≤48h (escolha
    conservadora — só sobe para classe1 quando certamente possível),
    ≤ 7 dias conta como classe2."""
    if not confirmed_exams:
        return None
    now = now_utc.astimezone(timezone.utc)
    today = now.date()
    best: int | None = None
    for exam in confirmed_exams:
        if exam.has_time:
            delta = exam.start - now  # type: ignore[operator]
            if timedelta(0) < delta <= timedelta(hours=EXAM_URGENT_HOURS):
                return 1
            if timedelta(0) < delta <= timedelta(days=EXAM_NEAR_DAYS):
                best = 2 if best is None else best
        else:
            days_ahead = (exam.day - today).days
            if 0 <= days_ahead <= 1:
                return 1
            if 0 < days_ahead <= EXAM_NEAR_DAYS:
                best = 2 if best is None else best
    return best


def _pedagogical_deadline(
    due: date, confirmed_exams: Sequence[ConfirmedExam]
) -> datetime | date:
    """Prazo pedagógico (§15.3): menor entre due sugerido e início
    confirmado da avaliação. Avaliação com dia sem hora nunca promove
    datetime duro — o prazo permanece data (§6.3/§15.3)."""
    deadline: datetime | date = due
    for exam in confirmed_exams:
        if exam.has_time:
            exam_start = exam.start
            assert isinstance(exam_start, datetime)
            # Avaliação COM hora: o instante confirmado é o prazo quando
            # cai no dia do due ou antes (menor entre os dois).
            if exam_start.date() <= due and (
                not isinstance(deadline, datetime) or exam_start < deadline
            ):
                deadline = exam_start
        else:
            exam_day = exam.day
            current_day = (
                deadline.date() if isinstance(deadline, datetime) else deadline
            )
            if exam_day < current_day:
                deadline = exam_day
    return deadline


def _clamp_due_before_exam_day(
    due: date, confirmed_exams: Sequence[ConfirmedExam], occ_local: date
) -> tuple[date, bool]:
    """Avaliação com dia sem hora: sugerir ANTES desse dia (§15.3), sem
    sugerir dia anterior à própria ocorrência. Retorna (due ajustado,
    ajustado_para_antes_do_dia)."""
    adjusted = due
    clamped = False
    for exam in confirmed_exams:
        if exam.has_time:
            continue
        latest_ok = exam.day - _ONE_DAY
        if adjusted > latest_ok:
            adjusted = max(latest_ok, occ_local + _ONE_DAY)
            clamped = adjusted <= latest_ok
    return adjusted, clamped


def compute_demand_candidates(
    *,
    occurrence_utc: datetime,
    outcome: PolicyOutcome,
    now_utc: datetime,
    confirmed_exams: Sequence[ConfirmedExam] = (),
    critical_error: bool = False,
    recurrent_difficulty: bool = False,
    overdue_review: bool = False,
    availability: Callable[[date], bool] | None = None,
    local_timezone: Any = None,
    activity_kind: str = "review",
    confirmed_duration_minutes: int | None = None,
    user_confirms_mandatory: bool = False,
    evidence_ids: Sequence[_uuid.UUID] = (),
    horizon_days: int = HORIZON_DAYS,
) -> list[DemandCandidate]:
    """Política ``assessment_review_policy_v1`` (§15.3) — função pura.

    - ``REVIEW_AFTER_ERROR``: um candidato no próximo dia local com
      disponibilidade; sem dia disponível no horizonte, primeira data do
      horizonte com ``pending_next_horizon=True``.
    - ``RECOVERY_AFTER_CORRECT``: candidatos em +1/+3/+7 dias da ocorrência
      local.
    - Prazo pedagógico e limitação por dia de avaliação só de data,
      conforme ``_pedagogical_deadline``.
    - Prioridade: erro crítico → 1; avaliação ≤48h → 1; avaliação ≤7 dias,
      revisão vencida ou dificuldade recorrente → 2; demais → 3. Ausência
      de avaliação não inventa urgência.
    - Duração: confirmada prevalece; senão catálogo estimado com
      ``mandatory=False``. Nenhuma conversão de domínio em duração.
    """
    if occurrence_utc.tzinfo is None or occurrence_utc.utcoffset() is None:
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            "occurrence_utc exige zona (UTC/offset)",
            diagnostic=_DIAGNOSTIC,
        )
    if now_utc.tzinfo is None or now_utc.utcoffset() is None:
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            "now_utc exige zona (UTC/offset)",
            diagnostic=_DIAGNOSTIC,
        )
    if availability is None:
        # Default de ensaio: todos os dias disponíveis (a grade é do solver,
        # task 012). Nunca interpretado como disponibilidade medida.
        availability = lambda day: True  # noqa: E731
    occ_local = _local_day(occurrence_utc, local_timezone)
    horizon_end = occ_local + timedelta(days=horizon_days)
    if confirmed_duration_minutes is not None:
        # Valor informado/confirmado prevalece (§15.3). Obrigatoriedade é
        # decisão explícita do usuário, não efeito colateral da confirmação.
        duration = confirmed_duration_minutes
        duration_status = StudyDemand.DurationStatus.CONFIRMED.value
        mandatory = bool(user_confirms_mandatory)
    else:
        duration = DURATION_CATALOG_MINUTES.get(activity_kind)
        if duration is None:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"activity_kind {activity_kind!r} fora do catálogo de "
                "duração da política v1 (§15.3)",
                diagnostic=_DIAGNOSTIC,
            )
        duration_status = StudyDemand.DurationStatus.ESTIMATED.value
        mandatory = False  # estimated nunca é obrigatória (§15.3/§4)

    exam_class = exam_priority_class(confirmed_exams, now_utc=now_utc)
    if critical_error:
        priority = 1
    elif exam_class == 1:
        priority = 1
    elif exam_class == 2 or overdue_review or recurrent_difficulty:
        priority = 2
    else:
        priority = 3

    def _candidate(raw_due: date, *, pending: bool = False) -> DemandCandidate:
        due, clamped = _clamp_due_before_exam_day(
            raw_due, confirmed_exams, occ_local
        )
        deadline = _pedagogical_deadline(due, confirmed_exams)
        return DemandCandidate(
            topic_id=_uuid.UUID(int=0),  # preenchido pelo serviço
            activity_kind=activity_kind,
            due_local_date=due,
            priority_class=priority,
            duration_minutes=duration,
            duration_status=duration_status,
            mandatory=mandatory,
            evidence_ids=tuple(evidence_ids),
            deadline=deadline,
            earliest=occurrence_utc.astimezone(timezone.utc),
            origin=outcome.value,
            pending_next_horizon=pending,
            before_exam_day=clamped,
        )

    if outcome is PolicyOutcome.REVIEW_AFTER_ERROR:
        due = next_available_day(
            occ_local + _ONE_DAY,
            availability=availability,
            horizon_end=horizon_end,
        )
        if due is None:
            return [_candidate(occ_local + _ONE_DAY, pending=True)]
        return [_candidate(due)]

    # RECOVERY_AFTER_CORRECT: candidatos 1/3/7 dias a partir da ocorrência
    # local (§15.3). Candidato além do horizonte fica pendente para o
    # próximo horizonte (§15.3: "Revisão além de sete dias fica pendente
    # para próximo horizonte").
    candidates: list[DemandCandidate] = []
    for offset in RECOVERY_OFFSETS_DAYS:
        day = occ_local + timedelta(days=offset)
        if day > horizon_end or not availability(day):
            candidates.append(_candidate(day, pending=True))
            continue
        candidates.append(_candidate(day))
    return candidates


def has_recurrent_difficulty(
    attempts: Sequence[Any],
    assessments: Sequence[Any],
    topic_id: _uuid.UUID,
) -> bool:
    """Dificuldade recorrente (§15.3): dois erros aceitos em **famílias
    distintas** entre as últimas 5 tentativas no tópico.

    Opera sobre os fatos de projeção do redutor (``AttemptFact``/
    ``AssessmentFact``, task 009): entradas decidíveis no tópico (§15.2),
    avaliação vigente aceita, erro = incorreta/parcial no tópico ou erro
    crítico por critério. Tentativas sem avaliação aceita não contam como
    erro (ausência de julgamento não é dificuldade).
    """
    from eduagent.services.assessment import (  # import tardio evita ciclo
        _critical_error,
        _topic_correctness,
        _topic_undecidable,
    )

    by_attempt: dict[_uuid.UUID, list[Any]] = {}
    for fact in assessments:
        by_attempt.setdefault(fact.attempt_id, []).append(fact)
    entries: list[tuple[Any, Any]] = []
    for attempt in attempts:
        accepted = [
            fact
            for fact in by_attempt.get(attempt.attempt_id, [])
            if fact.reliability is Assessment.Reliability.ACCEPTED
        ]
        if not accepted:
            continue
        vigente = max(accepted, key=lambda fact: fact.assessment_revision)
        results = [
            result
            for result in vigente.results
            if len(result.topic_ids) == 1 and result.topic_ids[0] == topic_id
        ]
        if not results or _topic_undecidable(vigente, topic_id):
            continue
        entries.append((attempt, vigente))
    recent = sorted(entries, key=lambda entry: entry[0].order_key)[-5:]
    error_families: set[_uuid.UUID] = set()
    for attempt, vigente in recent:
        correctness = _topic_correctness(vigente, topic_id)
        errored = correctness in (
            Assessment.Correctness.INCORRECT,
            Assessment.Correctness.PARTIAL,
        ) or _critical_error(vigente, topic_id)
        if errored:
            error_families.add(attempt.family_id)
    return len(error_families) >= 2


# ---------------------------------------------------------------------------
# Serviço de demandas (persistência via commit idempotente, §11/§15.3)
# ---------------------------------------------------------------------------


class DemandService:
    """Aplica a política v1 e persiste demandas com unicidade por chave
    (mapa §15.3; commit idempotente §11)."""

    def __init__(
        self,
        store: DomainStore,
        effects: EffectsService,
        *,
        clock: Callable[[], datetime] | None = None,
        local_timezone: Any = None,
        availability: Callable[[date], bool] | None = None,
    ) -> None:
        self._store = store
        self._effects = effects
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._local_timezone = local_timezone
        self._availability = availability

    # -- relação assessment_topics (§15.3) -----------------------------------

    def link_assessment_topics(
        self,
        user_id: str,
        *,
        fact_id: _uuid.UUID | str,
        topic_ids: Sequence[_uuid.UUID | str],
    ) -> int:
        """Registra a relação avaliação confirmada → tópicos (§15.3).

        A avaliação é um fato acadêmico confirmado do usuário (ownership);
        tópicos devem existir. Idempotente por PK. Retorna arestas criadas.
        """
        fact_key = str(_uuid.UUID(str(fact_id)))
        with self._store.read_transaction() as conn:
            fact = conn.execute(
                "SELECT status FROM facts WHERE user_id = ? AND id = ?",
                (user_id, fact_key),
            ).fetchone()
            known = {
                str(row["id"])
                for row in conn.execute(
                    "SELECT id FROM topics WHERE id IN "
                    f"({','.join('?' * len(topic_ids))})",
                    [str(_uuid.UUID(str(t))) for t in topic_ids],
                ).fetchall()
            }
        if fact is None:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"fato {fact_key} não resolve para o usuário",
                diagnostic=_DIAGNOSTIC,
            )
        if fact["status"] != "confirmed":
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "assessment_topics exige avaliação confirmada "
                f"(fato {fact_key} está '{fact['status']}')",
                diagnostic=_DIAGNOSTIC,
            )
        missing = [
            str(_uuid.UUID(str(t)))
            for t in topic_ids
            if str(_uuid.UUID(str(t))) not in known
        ]
        if missing:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"tópicos não resolvem: {missing}",
                diagnostic=_DIAGNOSTIC,
            )
        created = 0
        with self._store.write_transaction(user_id) as tx:
            for topic in topic_ids:
                cursor = tx.execute(
                    "INSERT INTO assessment_topics(user_id, fact_id, "
                    "topic_id) VALUES (?,?,?) ON CONFLICT DO NOTHING",
                    (user_id, fact_key, str(_uuid.UUID(str(topic)))),
                )
                created += max(cursor.rowcount, 0)
        return created

    def confirmed_exams(
        self,
        user_id: str,
        topic_id: _uuid.UUID | str,
        *,
        kind: str = "exam",
    ) -> list[ConfirmedExam]:
        """Avaliações confirmadas do tópico via ``assessment_topics`` (§15.3).

        O valor do fato define o início: valor com hora (ISO datetime com
        zona) vira datetime; dia puro (``YYYY-MM-DD``) permanece data —
        nunca promovido a datetime (§6.3/§15.3)."""
        topic_key = str(_uuid.UUID(str(topic_id)))
        rows = self._store.fetch_user_rows(
            "SELECT f.id AS fact_id, f.kind AS kind, f.value_json AS "
            "value_json FROM assessment_topics at "
            "JOIN facts f ON f.id = at.fact_id AND f.user_id = at.user_id "
            "WHERE at.user_id = ? AND at.topic_id = ? "
            "AND f.status = 'confirmed'",
            (user_id, topic_key),
        )
        exams: list[ConfirmedExam] = []
        for row in rows:
            try:
                value = json.loads(row["value_json"])
            except (json.JSONDecodeError, TypeError):
                continue
            normalized = (
                value.get("normalized_value")
                if isinstance(value, dict)
                else None
            )
            if not isinstance(normalized, str) or not normalized:
                continue
            fact_id = _uuid.UUID(str(row["fact_id"]))
            if "T" in normalized or "t" in normalized:
                start = datetime.fromisoformat(
                    normalized.replace("Z", "+00:00")
                )
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                exams.append(
                    ConfirmedExam(
                        fact_id=fact_id,
                        topic_id=_uuid.UUID(topic_key),
                        start=start,
                        has_time=True,
                    )
                )
            else:
                try:
                    day = date.fromisoformat(normalized)
                except ValueError:
                    continue
                exams.append(
                    ConfirmedExam(
                        fact_id=fact_id,
                        topic_id=_uuid.UUID(topic_key),
                        start=day,
                        has_time=False,
                    )
                )
        return exams

    # -- geração de demandas (§15.3) ------------------------------------------

    def generate_review_demand(
        self,
        user_id: str,
        *,
        topic_id: _uuid.UUID | str,
        occurrence_utc: datetime,
        outcome: PolicyOutcome | str,
        critical_error: bool = False,
        recurrent_difficulty: bool | None = None,
        evidence_ids: Sequence[_uuid.UUID | str] = (),
        activity_kind: str = "review",
        confirmed_duration_minutes: int | None = None,
        mandatory: bool = False,
        confirmed_exams: Sequence[ConfirmedExam] | None = None,
        operation_id: str | None = None,
    ) -> DemandGeneration:
        """Aplica a política v1 e persiste a demanda (nova ou consolidada).

        ``recurrent_difficulty=None`` calcula a dificuldade recorrente do
        tópico a partir das tentativas/avaliações registradas (§15.3);
        informar ``False``/``True`` sobrepõe (testes/caminhos sem histórico).
        Retry com o mesmo ``operation_id`` devolve o resultado anterior sem
        gerar novas demandas (§11).
        """
        outcome_enum = PolicyOutcome(outcome)
        topic_key = _uuid.UUID(str(topic_id))
        evidence = [_uuid.UUID(str(e)) for e in evidence_ids]
        if confirmed_exams is None:
            exams = self.confirmed_exams(user_id, topic_key)
        else:
            exams = list(confirmed_exams)
        if recurrent_difficulty is None:
            recurrent_difficulty = self._topic_recurrent_difficulty(
                user_id, topic_key
            )
        now_utc = self._clock()
        candidates = compute_demand_candidates(
            occurrence_utc=occurrence_utc,
            outcome=outcome_enum,
            now_utc=now_utc,
            confirmed_exams=exams,
            critical_error=critical_error,
            recurrent_difficulty=recurrent_difficulty,
            overdue_review=self._has_overdue_review(user_id, topic_key),
            availability=self._availability,
            local_timezone=self._local_timezone,
            activity_kind=activity_kind,
            confirmed_duration_minutes=confirmed_duration_minutes,
            user_confirms_mandatory=mandatory,
            evidence_ids=evidence,
        )
        if not candidates:  # pragma: no cover — política sempre gera ≥1
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                "política v1 sem candidatos (invariante violada)",
                diagnostic=_DIAGNOSTIC,
            )
        return self._persist_candidates(
            user_id,
            topic_key,
            candidates,
            operation_id=operation_id,
        )

    def _persist_candidates(
        self,
        user_id: str,
        topic_id: _uuid.UUID,
        candidates: Sequence[DemandCandidate],
        *,
        operation_id: str | None,
    ) -> DemandGeneration:
        """Persiste os candidatos num único commit idempotente (§11/§15.3):
        cada candidato é inserido novo ou **consolidado** na pendente com a
        mesma chave (todas as ``evidence_ids`` e prioridade mais alta)."""
        statements: list[tuple[str, tuple[Any, ...]]] = []
        entries: list[dict[str, Any]] = []
        digest_items: list[dict[str, Any]] = []
        seen_keys: set[tuple[str, str, str, str]] = set()
        for candidate in candidates:
            key = (
                user_id,
                str(topic_id),
                candidate.activity_kind,
                candidate.due_local_date.isoformat(),
                candidate.policy_version,
            )
            if key in seen_keys:
                # Candidatos distintos que colapsaram para a mesma chave
                # (ex.: limites para antes do dia da prova) consolidam na
                # mesma pendente — nunca duas INSERTs da mesma chave.
                continue
            seen_keys.add(key)
            existing = self._pending_by_key(*key)
            demand_id = (
                _uuid.UUID(existing["id"])
                if existing is not None
                else demand_key_id(*key)
            )
            consolidated = existing is not None
            if consolidated:
                assert existing is not None
                stored_payload = json.loads(existing["payload_json"])
                old = StudyDemand.model_validate(stored_payload["demand"])
                merged_evidence = list(
                    dict.fromkeys([*old.evidence_ids, *candidate.evidence_ids])
                )
                # Regra de prioridade mais alta (classe1 > classe2 > classe3).
                priority = min(old.priority_class, candidate.priority_class)
                # Valor informado/confirmado prevalece (§15.3).
                if (
                    candidate.duration_status
                    == StudyDemand.DurationStatus.CONFIRMED.value
                    or old.duration_status
                    == StudyDemand.DurationStatus.CONFIRMED.value
                ):
                    duration_status = (
                        StudyDemand.DurationStatus.CONFIRMED.value
                    )
                    duration = (
                        candidate.duration_minutes
                        if candidate.duration_status
                        == StudyDemand.DurationStatus.CONFIRMED.value
                        else old.duration_minutes
                    )
                else:
                    duration_status = (
                        StudyDemand.DurationStatus.ESTIMATED.value
                    )
                    duration = old.duration_minutes
                mandatory = old.mandatory or candidate.mandatory
                demand = StudyDemand(
                    demand_id=demand_id,
                    topic_ids=[topic_id],
                    kind=StudyDemand.DemandKind(candidate.activity_kind),
                    duration_minutes=duration,
                    earliest=candidate.earliest,
                    deadline=candidate.deadline,
                    mandatory=mandatory,
                    dependencies=[],
                    priority_class=priority,
                    evidence_ids=merged_evidence,
                    duration_status=StudyDemand.DurationStatus(
                        duration_status
                    ),
                )
                statements.append(
                    (
                        "UPDATE demands SET payload_json = ?, revision = "
                        "revision + 1 WHERE id = ? AND user_id = ? AND "
                        "status = 'pending'",
                        (
                            self._payload_json(demand, candidate),
                            str(demand_id),
                            user_id,
                        ),
                    )
                )
            else:
                demand = StudyDemand(
                    demand_id=demand_id,
                    topic_ids=[topic_id],
                    kind=StudyDemand.DemandKind(candidate.activity_kind),
                    duration_minutes=candidate.duration_minutes,
                    earliest=candidate.earliest,
                    deadline=candidate.deadline,
                    mandatory=candidate.mandatory,
                    dependencies=[],
                    priority_class=candidate.priority_class,
                    evidence_ids=list(candidate.evidence_ids),
                    duration_status=StudyDemand.DurationStatus(
                        candidate.duration_status
                    ),
                )
                statements.append(
                    (
                        "INSERT INTO demands(id, user_id, payload_json, "
                        "status, revision, topic_id, activity_kind, "
                        "due_local_date, policy_version) VALUES "
                        "(?,?,?,'pending',0,?,?,?,?)",
                        (
                            str(demand_id),
                            user_id,
                            self._payload_json(demand, candidate),
                            str(topic_id),
                            candidate.activity_kind,
                            candidate.due_local_date.isoformat(),
                            candidate.policy_version,
                        ),
                    )
                )
            entries.append(
                {
                    "demand_id": str(demand_id),
                    "activity_kind": candidate.activity_kind,
                    "due_local_date": candidate.due_local_date.isoformat(),
                    "priority_class": demand.priority_class,
                    "origin": candidate.origin,
                    "consolidated": consolidated,
                }
            )
            # Digest determinístico: chave + payload consolidado (merge é
            # idempotente) — o retry da mesma operação recomputa o mesmo
            # digest e a dedup do §11 devolve o recibo original.
            digest_items.append(
                {
                    "key": list(key[1:]),
                    "payload": json.loads(
                        self._payload_json(demand, candidate)
                    ),
                }
            )
        digest = _digest({"topic_id": str(topic_id), "items": digest_items})
        request = CommitRequest(
            operation_id=operation_id or str(_uuid.uuid4()),
            user_id=user_id,
            action=ACTION_DEMAND_UPSERT,
            digest=digest,
            expected_version=self._store.domain_revision(user_id),
            event=EventSpec(
                id=str(_uuid.uuid4()),
                kind=EVENT_DEMAND_GENERATED,
                occurred_at=_utc_iso(self._clock()),
                recorded_at=_utc_iso(self._clock()),
                payload={
                    "topic_id": str(topic_id),
                    "policy_version": candidates[0].policy_version,
                    "origin": candidates[0].origin,
                    "demands": entries,
                },
            ),
            projection=tuple(statements),
        )
        receipt = self._effects.commit(request)
        records = [
            record
            for record in (
                self.get_demand(user_id, entry["demand_id"])
                for entry in entries
            )
            if record is not None
        ]
        if len(records) != len(entries):  # pragma: no cover
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                "demandas não encontradas após commit confirmado",
                diagnostic=_DIAGNOSTIC,
            )
        review_due = self.refresh_review_due(user_id, topic_id)
        return DemandGeneration(
            receipt=receipt,
            created=any(not entry["consolidated"] for entry in entries),
            consolidated=any(entry["consolidated"] for entry in entries),
            demands=records,
            review_due=review_due,
        )

    @staticmethod
    def _payload_json(
        demand: StudyDemand, candidate: DemandCandidate
    ) -> str:
        payload = {
            "demand": demand.model_dump(mode="json"),
            "policy_version": candidate.policy_version,
            "origin": candidate.origin,
            "pending_next_horizon": candidate.pending_next_horizon,
            "before_exam_day": candidate.before_exam_day,
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    # -- leituras e consolidação ----------------------------------------------

    def _pending_by_key(
        self, user_id: str, topic_id: str, kind: str, due: str, policy: str
    ) -> Any | None:
        rows = self._store.fetch_user_rows(
            "SELECT id, payload_json, status FROM demands WHERE user_id = ? "
            "AND topic_id = ? AND activity_kind = ? AND due_local_date = ? "
            "AND policy_version = ? AND status = 'pending' ORDER BY rowid "
            "LIMIT 1",
            (user_id, topic_id, kind, due, policy),
        )
        return rows[0] if rows else None

    def get_demand(
        self, user_id: str, demand_id: _uuid.UUID | str
    ) -> DemandRecord | None:
        """Demanda projetada por ID (dono exigido)."""
        key = str(_uuid.UUID(str(demand_id)))
        rows = self._store.fetch_user_rows(
            "SELECT id, user_id, payload_json, status, topic_id, "
            "activity_kind, due_local_date, policy_version FROM demands "
            "WHERE user_id = ? AND id = ?",
            (user_id, key),
        )
        if not rows:
            return None
        return self._record_from_row(rows[0])

    def _record_from_row(self, row: Any) -> DemandRecord:
        payload = json.loads(row["payload_json"])
        demand = StudyDemand.model_validate(payload["demand"])
        today = _local_day(self._clock(), self._local_timezone)
        due = date.fromisoformat(str(row["due_local_date"]))
        return DemandRecord(
            demand_id=_uuid.UUID(str(row["id"])),
            user_id=str(row["user_id"]),
            topic_id=_uuid.UUID(str(row["topic_id"])),
            activity_kind=str(row["activity_kind"]),
            due_local_date=due,
            policy_version=str(row["policy_version"]),
            status=str(row["status"]),
            demand=demand,
            pending_next_horizon=bool(payload.get("pending_next_horizon")),
            before_exam_day=bool(payload.get("before_exam_day")),
            overdue=due < today,
            splittable_declaration=payload.get("splittable_declaration"),
        )

    def pending_demands(
        self,
        user_id: str,
        *,
        topic_id: _uuid.UUID | str | None = None,
    ) -> list[DemandRecord]:
        """Demandas pendentes do usuário (do tópico, se informado), em ordem
        de due; revisão vencida mantém due original e vem com
        ``overdue=True`` (§15.3)."""
        if topic_id is None:
            rows = self._store.fetch_user_rows(
                "SELECT id, user_id, payload_json, status, topic_id, "
                "activity_kind, due_local_date, policy_version FROM demands "
                "WHERE user_id = ? AND status = 'pending' "
                "ORDER BY due_local_date, rowid",
                (user_id,),
            )
        else:
            rows = self._store.fetch_user_rows(
                "SELECT id, user_id, payload_json, status, topic_id, "
                "activity_kind, due_local_date, policy_version FROM demands "
                "WHERE user_id = ? AND status = 'pending' AND topic_id = ? "
                "ORDER BY due_local_date, rowid",
                (user_id, str(_uuid.UUID(str(topic_id)))),
            )
        return [self._record_from_row(row) for row in rows]

    def _has_overdue_review(self, user_id: str, topic_id: _uuid.UUID) -> bool:
        """Existe revisão pendente vencida no tópico (§15.3: classe2)?"""
        return any(
            record.overdue for record in self.pending_demands(
                user_id, topic_id=topic_id
            )
        )

    def _topic_recurrent_difficulty(
        self, user_id: str, topic_id: _uuid.UUID
    ) -> bool:
        """Dificuldade recorrente calculada dos fatos registrados (§15.3);
        sem histórico, False (ausência de avaliação não inventa urgência)."""
        from eduagent.services.assessment import AssessmentService

        attempts, assessments = AssessmentService(
            self._store, self._effects, clock=self._clock
        ).load_facts(user_id)
        return has_recurrent_difficulty(attempts, assessments, topic_id)

    # -- duração confirmada (§15.3) -------------------------------------------

    def confirm_duration(
        self,
        user_id: str,
        demand_id: _uuid.UUID | str,
        *,
        minutes: int | None = None,
        mandatory: bool = True,
        operation_id: str | None = None,
    ) -> DemandRecord:
        """Usuário edita e confirma a duração (§15.3: "valor informado/
        confirmado prevalece … Usuário pode editar e confirmar para
        obrigatória"). Demanda obrigatória só com duração confirmada
        (validador do contrato §4)."""
        key = str(_uuid.UUID(str(demand_id)))
        record = self.get_demand(user_id, key)
        if record is None:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"demanda {key} não resolve para o usuário",
                diagnostic=_DIAGNOSTIC,
            )
        demand = record.demand
        duration = minutes if minutes is not None else demand.duration_minutes
        if duration <= 0:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "duração confirmada deve ser positiva",
                diagnostic=_DIAGNOSTIC,
            )
        confirmed = demand.model_copy(
            update={
                "duration_minutes": duration,
                "duration_status": StudyDemand.DurationStatus.CONFIRMED,
                "mandatory": bool(mandatory),
            }
        )
        payload = {
            "demand": confirmed.model_dump(mode="json"),
            "policy_version": record.policy_version,
            "origin": "duration_confirmed",
            "pending_next_horizon": record.pending_next_horizon,
        }
        digest = _digest(
            {
                "demand_id": key,
                "payload": payload,
            }
        )
        request = CommitRequest(
            operation_id=operation_id or str(_uuid.uuid4()),
            user_id=user_id,
            action=ACTION_DEMAND_UPSERT,
            digest=digest,
            expected_version=self._store.domain_revision(user_id),
            event=EventSpec(
                id=str(_uuid.uuid4()),
                kind=EVENT_DEMAND_DURATION_CONFIRMED,
                occurred_at=_utc_iso(self._clock()),
                recorded_at=_utc_iso(self._clock()),
                payload={
                    "demand_id": key,
                    "duration_minutes": duration,
                    "mandatory": bool(mandatory),
                },
            ),
            projection=(
                (
                    "UPDATE demands SET payload_json = ?, revision = "
                    "revision + 1 WHERE id = ? AND user_id = ?",
                    (
                        json.dumps(
                            payload, sort_keys=True, ensure_ascii=False
                        ),
                        key,
                        user_id,
                    ),
                ),
            ),
        )
        self._effects.commit(request)
        updated = self.get_demand(user_id, key)
        assert updated is not None
        return updated

    # -- review_due do tópico (§15.3) ------------------------------------------

    def refresh_review_due(
        self, user_id: str, topic_id: _uuid.UUID | str
    ) -> date | None:
        """``review_due`` = data do primeiro candidato pendente (§15.3),
        registrada na projeção do tópico quando existir (o redutor da 009 é
        quem cria a linha; a política só atualiza ``review_due``)."""
        topic_key = str(_uuid.UUID(str(topic_id)))
        pendings = self.pending_demands(user_id, topic_id=topic_key)
        first_due = min(
            (record.due_local_date for record in pendings), default=None
        )
        with self._store.read_transaction() as conn:
            row = conn.execute(
                "SELECT revision, payload_json FROM topic_states "
                "WHERE user_id = ? AND topic_id = ?",
                (user_id, topic_key),
            ).fetchone()
        if row is None:
            # Sem projeção de competência (nenhuma tentativa avaliada): a
            # política registra o due apenas na demanda — nada é inventado.
            return first_due
        state = TopicState.model_validate_json(row["payload_json"])
        if state.review_due == first_due:
            return first_due
        updated = state.model_copy(update={"review_due": first_due})
        with self._store.write_transaction(
            user_id, bump_domain_revision=False
        ) as tx:
            # Ajuste de projeção pela política (não é escrita nova de
            # domínio do aluno); a revisão do estado acompanha a mudança.
            tx.execute(
                "UPDATE topic_states SET revision = revision + 1, "
                "payload_json = ? WHERE user_id = ? AND topic_id = ?",
                (updated.model_dump_json(), user_id, topic_key),
            )
        return first_due


# ---------------------------------------------------------------------------
# Solver CP-SAT lexicográfico e verificador independente (§9/§15.5) — task 012
# ---------------------------------------------------------------------------

#: Namespace determinístico para identidades derivadas pelo solver (§15.5):
#: ocorrência nova recebe ID novo e determinístico; ``block_id``/``uid``
#: permanecem em mudança de horário.
_SOLVER_NAMESPACE = _uuid.uuid5(_uuid.NAMESPACE_URL, "eduagent:schedule:v1")

#: Identidade do verificador independente (mapa §9: verificador **separado**).
VERIFIER_ID = "schedule_verifier_v1"

#: Teto de texto da explicação (contrato §4: _MAX_TEXT = 4000).
_MAX_SOLVER_TEXT = 4000

#: Mensagem obrigatória de inviabilidade na grade conservadora (§15.5).
_CONSERVATIVE_GRID_MESSAGE = (
    "inviável na grade conservadora de {slot} min; "
    "viabilidade contínua não determinada"
)

#: Caminho default da configuração (mapa §3); relativo à raiz do repositório.
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default.yaml"


@dataclass(frozen=True)
class SolverSettings:
    """Parâmetros do solver vindos da configuração (mapa §3/§9):

    ``solver_budget_s=10``, ``slot_minutes=15``, ``horizon_days=7``,
    ``seed=0``, ``num_workers=1`` em ``config/default.yaml``. São **escolhas
    de ensaio** a calibrar no hardware registrado — NUNCA resultados medidos
    (mapa §1/§3).
    """

    solver_budget_s: float = 10.0
    slot_minutes: int = 15
    horizon_days: int = 7
    seed: int = 0
    num_workers: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.solver_budget_s, bool) or not isinstance(
            self.solver_budget_s, (int, float)
        ) or self.solver_budget_s <= 0:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "solver_budget_s deve ser número positivo (config §3)",
                diagnostic=_DIAGNOSTIC,
            )
        if (
            isinstance(self.slot_minutes, bool)
            or not isinstance(self.slot_minutes, int)
            or self.slot_minutes <= 0
            or 1440 % self.slot_minutes != 0
        ):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "slot_minutes deve ser inteiro positivo que divide 1440 "
                f"(recebido {self.slot_minutes!r})",
                diagnostic=_DIAGNOSTIC,
            )
        if (
            isinstance(self.horizon_days, bool)
            or not isinstance(self.horizon_days, int)
            or self.horizon_days < 1
        ):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "horizon_days deve ser inteiro ≥ 1 (config §3/§15.5)",
                diagnostic=_DIAGNOSTIC,
            )
        if (
            isinstance(self.seed, bool)
            or not isinstance(self.seed, int)
            or self.seed < 0
        ):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "seed deve ser inteiro ≥ 0 (config §3)",
                diagnostic=_DIAGNOSTIC,
            )
        if (
            isinstance(self.num_workers, bool)
            or not isinstance(self.num_workers, int)
            or self.num_workers < 1
        ):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "num_workers deve ser inteiro ≥ 1 (config §3)",
                diagnostic=_DIAGNOSTIC,
            )

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any] | None) -> "SolverSettings":
        """Constrói a partir do mapeamento de configuração (chaves do mapa
        §3); chaves ausentes mantêm os defaults de ensaio."""
        section = config or {}
        return cls(
            solver_budget_s=section.get("solver_budget_s", 10.0),
            slot_minutes=section.get("slot_minutes", 15),
            horizon_days=section.get("horizon_days", 7),
            seed=section.get("seed", 0),
            num_workers=section.get("num_workers", 1),
        )


def load_solver_settings(path: Path | str | None = None) -> SolverSettings:
    """Carrega as configurações do solver de ``config/default.yaml`` (mapa
    §3). Arquivo ausente → defaults de ensaio espelhando o yaml (escolha
    documentada; nunca apresentados como valores medidos)."""
    import yaml  # import tardio: só necessário no carregamento

    target = Path(path) if path is not None else _DEFAULT_CONFIG_PATH
    if not target.exists():
        return SolverSettings()
    with open(target, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            f"configuração {target} inválida: mapeamento esperado",
            diagnostic=_DIAGNOSTIC,
        )
    return SolverSettings.from_mapping(data)


# -- Entradas do solver (dados confirmados; §9: "Interpretar demandas,
#    confirmar durations/prazos/compromissos") -------------------------------


@dataclass(frozen=True)
class TimeWindow:
    """Janela no dia local, em minutos desde a meia-noite local (§15.5:
    grade por dia local a partir de 00:00). ``end_minute`` é exclusivo e
    pode ser 1440 (meia-noite seguinte)."""

    day: date
    start_minute: int  # 0 <= start < end <= 1440
    end_minute: int


@dataclass(frozen=True)
class FixedBlock:
    """Bloco fixo em instantes UTC (§9: "Compromissos, blocos iniciados e
    concluídos são fixos"; §15.4: "Fixos inseridos uma vez no conjunto de
    ocupação, sem candidatos móveis"). Compromisso pessoal bloqueia tempo
    mas NÃO conta como estudo diário (§15.5); bloco fixo de estudo conta
    (``counts_as_study=True``)."""

    start_utc: datetime
    end_utc: datetime
    counts_as_study: bool = False


@dataclass(frozen=True)
class DailyStudyLimit:
    """Limite diário confirmado de estudo (§9: "limites diários
    confirmados"), medido em minutos efetivamente reservados (§15.5)."""

    day: date
    study_minutes: int


@dataclass(frozen=True)
class SolverDemand:
    """Demanda de estudo confirmada para o solver (``StudyDemand`` §4 com
    os dados já confirmados pelo serviço da task 011/§15.3)."""

    demand_id: _uuid.UUID
    duration_minutes: int  # duração original; nunca reduzida (§9/§15.5)
    mandatory: bool
    priority_class: int  # 1..3
    earliest_utc: datetime
    deadline: datetime | date  # PartialDate (§4): dia puro ou instante
    dependencies: tuple[_uuid.UUID, ...] = ()  # demandas predecessoras (§15.4)
    #: Identidade de ocorrência persistida ao criar a demanda (§15.5);
    #: ``None`` → demanda nunca agendada (occurrence nova no primeiro plano).
    occurrence_id: _uuid.UUID | None = None


@dataclass(frozen=True)
class ExistingOccurrence:
    """Bloco de ocorrência previamente aprovado (identidade §15.5:
    ``block_id``/``uid`` permanecem em mudança de horário; nova ocorrência
    recebe novo ID)."""

    occurrence_id: _uuid.UUID
    block_id: _uuid.UUID
    demand_id: _uuid.UUID
    start_utc: datetime
    end_utc: datetime
    uid: _uuid.UUID | None = None


@dataclass(frozen=True)
class SchedulingProblem:
    """Problema de agendamento confirmado (§9/§15.5). ``local_timezone``
    é a zona IANA **confirmada**; ``None`` → dia local = dia UTC (escolha
    conservadora documentada na task 011; timezone default só após
    confirmação explícita, mapa §3)."""

    user_id: str
    horizon_start: date  # data inicial confirmada (§15.5)
    local_timezone: tzinfo | None
    snapshot_version: int
    demands: tuple[SolverDemand, ...] = ()
    availability: tuple[TimeWindow, ...] = ()
    preferred: tuple[TimeWindow, ...] = ()
    fixed_blocks: tuple[FixedBlock, ...] = ()
    daily_limits: tuple[DailyStudyLimit, ...] = ()
    existing: tuple[ExistingOccurrence, ...] = ()


@dataclass(frozen=True)
class PlacedBlock:
    """Bloco colocado pelo solver (entrada do verificador)."""

    occurrence_id: _uuid.UUID
    block_id: _uuid.UUID
    uid: _uuid.UUID
    demand_id: _uuid.UUID
    start_utc: datetime
    end_utc: datetime


@dataclass(frozen=True)
class StageProof:
    """Prova de uma etapa da lexicografia (§15.5: "vetor de provas por
    etapa"). ``status`` é o status do CP-SAT na etapa; ``value`` o valor do
    objetivo quando há solução."""

    stage: str
    status: str
    value: int | None


@dataclass(frozen=True)
class ScheduleSolveResult:
    """Resultado da ferramenta ``schedule.solve``: proposta (contrato §4)
    mais o vetor de provas lexicográficas (§15.5). A proposta só é
    publicável como aprovada com ``status`` OPTIMAL/FEASIBLE **e**
    ``validation.passed=True`` (mapa §9/§4)."""

    proposal: ScheduleProposal
    proofs: tuple[StageProof, ...]


# -- Validação do problema (erros explícitos; §9) ----------------------------


def _require_aware(moment: datetime, name: str) -> None:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            f"{name} exige datetime com zona (mapa §4)",
            diagnostic=_DIAGNOSTIC,
        )


def _resolve_wall_instant(
    day: date, wall_minute: int, tz: tzinfo | None
) -> datetime:
    """Instante UTC do minuto ``wall_minute`` do dia local ``day`` (§15.5:
    "convertidas individualmente para UTC"), rejeitando instantes locais
    ambíguos/inexistentes até confirmação (§15.5/§9)."""

    naive = datetime.combine(day, _dt_time(0, 0)) + timedelta(
        minutes=wall_minute
    )
    if tz is None:
        # Sem zona confirmada, o dia local é o dia UTC (conservador,
        # documentado na task 011; UTC não tem transição).
        return naive.replace(tzinfo=timezone.utc)
    fold0 = naive.replace(tzinfo=tz, fold=0)
    fold1 = naive.replace(tzinfo=tz, fold=1)
    roundtrip = fold0.astimezone(timezone.utc).astimezone(tz)
    if roundtrip.replace(tzinfo=None) != naive:
        # Na "lacuna" da transição o instante de parede não existe.
        raise EduAgentError(
            ErrorCode.AMBIGUOUS_INPUT,
            f"instante local {naive} não existe na zona informada "
            "(transição de horário); esclarecer antes de planejar (§15.5)",
            diagnostic=_DIAGNOSTIC,
        )
    if fold0.utcoffset() != fold1.utcoffset():
        # Na "repetição" da transição o instante ocorre duas vezes.
        raise EduAgentError(
            ErrorCode.AMBIGUOUS_INPUT,
            f"instante local {naive} é ambíguo na zona informada; "
            "esclarecer antes de planejar (§15.5)",
            diagnostic=_DIAGNOSTIC,
        )
    return fold0.astimezone(timezone.utc)


def _deadline_instant(deadline: datetime | date, tz: tzinfo | None) -> datetime:
    """Instante-limite do prazo: datetime é usado como está; dia puro vale
    até a meia-noite local seguinte (o prazo permanece no dia, §6.3/§15.3;
    nenhum horário é inventado — a fronteira do dia é a própria regra)."""
    if isinstance(deadline, datetime):
        _require_aware(deadline, "deadline")
        return deadline
    return _resolve_wall_instant(deadline + timedelta(days=1), 0, tz)


def _demand_deadline_instant(
    demand: SolverDemand, tz: tzinfo | None
) -> datetime:
    return _deadline_instant(demand.deadline, tz)


def _check_acyclic(demands: Sequence[SolverDemand]) -> None:
    """Dependência cíclica é erro explícito, não inviabilidade misteriosa
    (mapa §9)."""
    by_id = {d.demand_id: d for d in demands}
    state: dict[_uuid.UUID, int] = {}

    def visit(node: _uuid.UUID) -> None:
        mark = state.get(node, 0)
        if mark == 1:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "dependência cíclica é erro, não inviabilidade misteriosa "
                f"(mapa §9; ciclo em {node})",
                diagnostic=_DIAGNOSTIC,
            )
        if mark == 2:
            return
        state[node] = 1
        for dep in by_id[node].dependencies:
            if dep not in by_id:
                raise EduAgentError(
                    ErrorCode.SOURCE_UNRESOLVED,
                    f"dependência {dep} não resolve para demanda conhecida "
                    "(§15.4: dependência referencia demanda)",
                    diagnostic=_DIAGNOSTIC,
                )
            visit(dep)
        state[node] = 2

    for demand in demands:
        if demand.demand_id in demand.dependencies:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "dependência circular: demanda não depende de si (§9)",
                diagnostic=_DIAGNOSTIC,
            )
        visit(demand.demand_id)


def _fixed_block_wall_minutes(
    block: FixedBlock, day: date, tz: tzinfo | None
) -> tuple[int, int] | None:
    """Sobreposição do bloco fixo com o dia local, em minutos de parede
    [0, 1440]; ``None`` se não sobrepõe. Instantes UTC são inequívocos;
    conversão por ``astimezone`` (§15.5)."""
    zone = tz if tz is not None else timezone.utc
    start_local = block.start_utc.astimezone(zone)
    end_local = block.end_utc.astimezone(zone)
    day_start = datetime.combine(day, _dt_time(0, 0), tzinfo=zone)
    if end_local <= day_start or start_local >= day_start + timedelta(days=1):
        return None
    if start_local.date() == day:
        start_minute = start_local.hour * 60 + start_local.minute
    else:
        start_minute = 0
    if end_local.date() == day:
        end_minute = end_local.hour * 60 + end_local.minute
        if end_local.second or end_local.microsecond:
            end_minute += 1  # teto conservador (bloqueios para fora, §9)
    else:
        end_minute = 1440
    if end_minute <= start_minute:
        return None
    return start_minute, end_minute


def _fixed_study_minutes(day: date, problem: SchedulingProblem) -> int:
    """Minutos fixos de estudo reservados no dia (§15.5: capacidade diária
    inclui blocos fixos de estudo), arredondados para fora (§9). Sobreposição
    entre fixos é somada (conservador, MVP)."""
    total = 0
    for block in problem.fixed_blocks:
        if not block.counts_as_study:
            continue
        overlap = _fixed_block_wall_minutes(block, day, problem.local_timezone)
        if overlap is None:
            continue
        total += overlap[1] - overlap[0]
    return total


def _validate_problem(
    problem: SchedulingProblem, settings: SolverSettings
) -> dict[_uuid.UUID, int]:
    """Validação explícita das entradas confirmadas (erros tipados; §9)."""
    if not problem.user_id:
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            "user_id obrigatório",
            diagnostic=_DIAGNOSTIC,
        )
    if problem.snapshot_version < 0:
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            "snapshot_version deve ser ≥ 0 (§15.1)",
            diagnostic=_DIAGNOSTIC,
        )
    seen: dict[_uuid.UUID, int] = {}
    for index, demand in enumerate(problem.demands):
        if demand.demand_id in seen:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"demanda duplicada no problema: {demand.demand_id}",
                diagnostic=_DIAGNOSTIC,
            )
        seen[demand.demand_id] = index
        if demand.duration_minutes <= 0:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"demanda {demand.demand_id} exige duração positiva (§4)",
                diagnostic=_DIAGNOSTIC,
            )
        if demand.priority_class not in (1, 2, 3):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"demanda {demand.demand_id} com priority_class inválida "
                "(§4: 1..3)",
                diagnostic=_DIAGNOSTIC,
            )
        _require_aware(demand.earliest_utc, f"earliest da demanda {demand.demand_id}")
    _check_acyclic(problem.demands)

    existing_by_demand: dict[_uuid.UUID, ExistingOccurrence] = {}
    occurrence_ids: set[_uuid.UUID] = set()
    block_ids: set[_uuid.UUID] = set()
    for occurrence in problem.existing:
        if occurrence.demand_id not in seen:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"ocorrência existente referencia demanda desconhecida "
                f"{occurrence.demand_id}",
                diagnostic=_DIAGNOSTIC,
            )
        if occurrence.occurrence_id in occurrence_ids:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "ocorrência existente duplicada (§15.5: uma ocorrência por "
                "demanda no MVP)",
                diagnostic=_DIAGNOSTIC,
            )
        if occurrence.block_id in block_ids:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "block_id existente duplicado (§15.5)",
                diagnostic=_DIAGNOSTIC,
            )
        demand = problem.demands[seen[occurrence.demand_id]]
        if (
            demand.occurrence_id is not None
            and demand.occurrence_id != occurrence.occurrence_id
        ):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "occurrence_id da demanda diverge da ocorrência aprovada "
                "(§15.5: identidade persistida)",
                diagnostic=_DIAGNOSTIC,
            )
        if occurrence.start_utc >= occurrence.end_utc:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "ocorrência existente exige start < end (§4)",
                diagnostic=_DIAGNOSTIC,
            )
        _require_aware(
            occurrence.start_utc, f"start da ocorrência {occurrence.block_id}"
        )
        _require_aware(
            occurrence.end_utc, f"end da ocorrência {occurrence.block_id}"
        )
        occurrence_ids.add(occurrence.occurrence_id)
        block_ids.add(occurrence.block_id)
        existing_by_demand[occurrence.demand_id] = occurrence

    for window in (*problem.availability, *problem.preferred):
        if not 0 <= window.start_minute < window.end_minute <= 1440:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"janela inválida no dia {window.day}: "
                f"[{window.start_minute}, {window.end_minute})",
                diagnostic=_DIAGNOSTIC,
            )
    for block in problem.fixed_blocks:
        if block.start_utc >= block.end_utc:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "bloco fixo exige start < end (§9)",
                diagnostic=_DIAGNOSTIC,
            )
        _require_aware(block.start_utc, "start de bloco fixo")
        _require_aware(block.end_utc, "end de bloco fixo")
    for limit in problem.daily_limits:
        if limit.study_minutes < 0:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"limite diário negativo no dia {limit.day}",
                diagnostic=_DIAGNOSTIC,
            )
        fixed = _fixed_study_minutes(limit.day, problem)
        if fixed > limit.study_minutes:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"limite diário confirmado do dia {limit.day} "
                f"({limit.study_minutes} min) já é excedido por "
                f"{fixed} min de blocos fixos de estudo (§15.5)",
                diagnostic=_DIAGNOSTIC,
            )
    return seen


# -- Grade e candidatos (§9/§15.5) -------------------------------------------


@dataclass(frozen=True)
class _Candidate:
    """Candidato contíguo de demanda: dia local + faixa de slots (§9:
    "candidatos contíguos"; §15.5: candidatos não atravessam meia-noite)."""

    demand_index: int
    day_index: int
    start_slot: int
    n_slots: int
    start_utc: datetime
    end_utc: datetime
    reserved_minutes: int
    preferred_minutes: int
    same_instants_block_id: _uuid.UUID | None  # ocorrência aprovada igual
    displacement_minutes: int  # |novo_start − antigo_start| (§15.5)


@dataclass
class _Grid:
    days: list[date]
    usable: list[list[bool]]  # por dia, lista de slots utilizáveis
    fixed_study: list[int]  # minutos fixos de estudo por dia


def _horizon_days(start: date, count: int) -> list[date]:
    """Horizonte: da meia-noite local da data inicial confirmada até a
    meia-noite local após ``count`` datas (§15.5) — dias locais
    ``start..start+count-1``."""
    return [start + timedelta(days=offset) for offset in range(count)]


def _usable_slots(
    day: date,
    problem: SchedulingProblem,
    settings: SolverSettings,
) -> tuple[list[bool], int]:
    """Slots utilizáveis do dia: disponibilidade arredondada **para dentro**
    e bloqueios **para fora** (mapa §9)."""
    slot = settings.slot_minutes
    total = 1440 // slot
    usable = [False] * total
    for window in problem.availability:
        if window.day != day:
            continue
        first = -(-window.start_minute // slot)  # teto: para dentro
        last = window.end_minute // slot  # piso: para dentro
        for slot_index in range(first, last):
            usable[slot_index] = True
    for block in problem.fixed_blocks:
        overlap = _fixed_block_wall_minutes(
            block, day, problem.local_timezone
        )
        if overlap is None:
            continue
        start_minute, end_minute = overlap
        first = start_minute // slot  # piso: para fora
        last = -(-end_minute // slot)  # teto: para fora
        for slot_index in range(first, min(last, total)):
            usable[slot_index] = False
    fixed_study = _fixed_study_minutes(day, problem)
    return usable, fixed_study


def _merged_availability(
    problem: SchedulingProblem, day: date
) -> list[tuple[int, int]]:
    """União das janelas de disponibilidade do dia (decisão de codificação
    da 012a, §9/§15.5): janelas adjacentes ou sobrepostas do mesmo dia
    colapsam em intervalos contíguos. É a mesma semântica da grade
    (``_usable_slots`` constrói os slots utilizáveis como união das janelas)
    e do enumerador (runs contíguos sobre esses slots); o verificador
    reaplica a restrição nos minutos originais sem arredondamento —
    arredondamento para dentro **por janela** e bloqueios para fora
    permanecem na grade. Vão entre janelas disjuntas não é cobertura."""
    intervals = sorted(
        (window.start_minute, window.end_minute)
        for window in problem.availability
        if window.day == day
    )
    merged: list[list[int]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def _build_grid(
    problem: SchedulingProblem, settings: SolverSettings
) -> _Grid:
    days = _horizon_days(problem.horizon_start, settings.horizon_days)
    usable: list[list[bool]] = []
    fixed_study: list[int] = []
    for day in days:
        day_usable, day_fixed = _usable_slots(day, problem, settings)
        usable.append(day_usable)
        fixed_study.append(day_fixed)
    return _Grid(days=days, usable=usable, fixed_study=fixed_study)


def _enumerate_candidates(
    problem: SchedulingProblem,
    grid: _Grid,
    settings: SolverSettings,
    demand_index_by_id: dict[_uuid.UUID, int],
) -> list[_Candidate]:
    """Candidatos contíguos por demanda (§9): runs de slots utilizáveis
    dentro do dia, respeitando earliest/deadline/janelas e capacidade diária
    (o limite é restrição do modelo, não do candidato)."""
    slot = settings.slot_minutes
    slot_per_day = 1440 // slot
    existing_by_demand: dict[int, ExistingOccurrence] = {}
    for occurrence in problem.existing:
        existing_by_demand[demand_index_by_id[occurrence.demand_id]] = occurrence
    preferred_by_day: dict[int, list[TimeWindow]] = {}
    day_index: dict[date, int] = {day: i for i, day in enumerate(grid.days)}
    for window in problem.preferred:
        if window.day in day_index:
            preferred_by_day.setdefault(day_index[window.day], []).append(window)

    candidates: list[_Candidate] = []
    for demand_index, demand in enumerate(problem.demands):
        n_slots = -(-demand.duration_minutes // slot)  # ceil (§9)
        reserved = n_slots * slot
        earliest = demand.earliest_utc.astimezone(timezone.utc)
        deadline = _demand_deadline_instant(demand, problem.local_timezone)
        occurrence = existing_by_demand.get(demand_index)
        for day_index_value, day in enumerate(grid.days):
            usable = grid.usable[day_index_value]
            run_start: int | None = None
            for position in range(slot_per_day + 1):
                open_run = position < slot_per_day and usable[position]
                if open_run and run_start is None:
                    run_start = position
                if (not open_run) and (run_start is not None):
                    run_end = position
                    for start_slot in range(run_start, run_end - n_slots + 1):
                        start_minute = start_slot * slot
                        end_minute = start_minute + reserved
                        start_utc = _resolve_wall_instant(
                            day, start_minute, problem.local_timezone
                        )
                        end_utc = _resolve_wall_instant(
                            day, end_minute, problem.local_timezone
                        )
                        if start_utc < earliest or end_utc > deadline:
                            continue
                        preferred_minutes = sum(
                            max(
                                0,
                                min(end_minute, w.end_minute)
                                - max(start_minute, w.start_minute),
                            )
                            for w in preferred_by_day.get(
                                day_index_value, ()
                            )
                        )
                        same_block: _uuid.UUID | None = None
                        displacement = 0
                        if occurrence is not None:
                            if (
                                start_utc == occurrence.start_utc
                                and end_utc == occurrence.end_utc
                            ):
                                same_block = occurrence.block_id
                            delta = start_utc - occurrence.start_utc
                            displacement = abs(
                                int(delta.total_seconds()) // 60
                            )
                            if delta.total_seconds() % 60:
                                displacement += 1  # teto conservador
                        candidates.append(
                            _Candidate(
                                demand_index=demand_index,
                                day_index=day_index_value,
                                start_slot=start_slot,
                                n_slots=n_slots,
                                start_utc=start_utc,
                                end_utc=end_utc,
                                reserved_minutes=reserved,
                                preferred_minutes=preferred_minutes,
                                same_instants_block_id=same_block,
                                displacement_minutes=displacement,
                            )
                        )
                    run_start = None
    return candidates


# -- Modelo CP-SAT e lexicografia (§9/§15.5) ---------------------------------


@dataclass(frozen=True)
class _Stage:
    """Etapa lexicográfica (§9: objetivos lexicográficos; §15.5)."""

    name: str
    expression: Any  # LinearExpr | int
    maximize: bool


class _LexicographicDriver:
    """Protocolo de lexicografia com orçamento (§15.5):

    - divide ``solver_budget_s`` entre solves com
      ``remaining_seconds/remaining_stages`` e reaproveita o tempo restante;
    - guarda incumbent **validado** após cada etapa;
    - fixa o valor anterior só com OPTIMAL;
    - FEASIBLE numa fase interrompe a lexicografia e conserva solução
      válida com vetor de provas por etapa;
    - primeira fase sem solução → UNKNOWN; UNKNOWN posterior → publica o
      incumbent anterior como FEASIBLE;
    - INFEASIBLE é conflito provado; MODEL_INVALID é defeito;
    - nunca publica relaxação diagnóstica como aprovado.
    """

    def __init__(
        self,
        *,
        model: cp_model.CpModel,
        stages: Sequence[_Stage],
        variables: Sequence[Any],
        settings: SolverSettings,
        extract: Callable[[Sequence[int]], list[PlacedBlock]],
        verify: Callable[[list[PlacedBlock]], list[str]],
    ) -> None:
        self._model = model
        self._stages = list(stages)
        self._variables = list(variables)
        self._settings = settings
        self._extract = extract
        self._verify = verify

    def run(
        self,
    ) -> tuple[
        "ScheduleProposal.SolverStatus",
        list[PlacedBlock] | None,
        tuple[StageProof, ...],
    ]:
        total = len(self._stages)
        remaining = self._settings.solver_budget_s
        proofs: list[StageProof] = []
        incumbent: list[PlacedBlock] | None = None
        for index, stage in enumerate(self._stages):
            seconds = remaining / (total - index)
            started = _time.monotonic()
            status, value, selected = self._solve_stage(stage, seconds)
            elapsed = _time.monotonic() - started
            remaining = max(remaining - elapsed, 0.0)
            proofs.append(StageProof(stage.name, status, value))
            if status == "INFEASIBLE":
                if incumbent is None:
                    return (
                        ScheduleProposal.SolverStatus.INFEASIBLE,
                        None,
                        tuple(proofs),
                    )
                # Com incumbent válido e restrições fixadas, INFEASIBLE
                # posterior é contradição interna (defeito), não resultado.
                raise EduAgentError(
                    ErrorCode.INTERNAL_FAILURE,
                    "INFEASIBLE em etapa posterior a incumbent válido "
                    "(contradição interna; §15.5)",
                    diagnostic=_DIAGNOSTIC,
                )
            if status == "MODEL_INVALID":
                return (
                    ScheduleProposal.SolverStatus.MODEL_INVALID,
                    None,
                    tuple(proofs),
                )
            if status == "UNKNOWN":
                if incumbent is None:
                    return (
                        ScheduleProposal.SolverStatus.UNKNOWN,
                        None,
                        tuple(proofs),
                    )
                # §15.5: UNKNOWN posterior → publicar incumbent anterior
                # como FEASIBLE com provas das etapas concluídas.
                return (
                    ScheduleProposal.SolverStatus.FEASIBLE,
                    incumbent,
                    tuple(proofs),
                )
            # OPTIMAL ou FEASIBLE: há solução — validar antes de guardar.
            assert selected is not None
            placed = self._extract(selected)
            issues = self._verify(placed)
            if issues:
                raise EduAgentError(
                    ErrorCode.INTERNAL_FAILURE,
                    "solução do solver falhou no verificador independente "
                    f"(defeito, nada publicado): {'; '.join(issues[:3])}",
                    diagnostic=_DIAGNOSTIC,
                )
            incumbent = placed
            if status == "FEASIBLE":
                # §15.5: FEASIBLE numa fase interrompe a lexicografia e
                # conserva a solução válida com provas por etapa.
                return (
                    ScheduleProposal.SolverStatus.FEASIBLE,
                    incumbent,
                    tuple(proofs),
                )
            # OPTIMAL: só agora o valor anterior é fixado (§15.5).
            self._fix(stage, value)
        assert incumbent is not None
        return (
            ScheduleProposal.SolverStatus.OPTIMAL,
            incumbent,
            tuple(proofs),
        )

    def _solve_stage(
        self, stage: _Stage, seconds: float
    ) -> tuple[str, int | None, list[int] | None]:
        """Resolve uma etapa dentro do recorte de tempo; retorna
        (status, valor, seleção). Método isolado para observabilidade
        (testes de protocolo) — o orçamento total nunca é excedido."""
        if stage.maximize:
            self._model.Maximize(stage.expression)
        else:
            self._model.Minimize(stage.expression)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(seconds, 0.001)
        solver.parameters.random_seed = self._settings.seed
        solver.parameters.num_workers = self._settings.num_workers
        status = solver.Solve(self._model)
        name = solver.StatusName(status)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            value = int(round(solver.ObjectiveValue()))
            selected = [
                index
                for index, variable in enumerate(self._variables)
                if solver.Value(variable)
            ]
            return name, value, selected
        return name, None, None

    def _fix(self, stage: _Stage, value: int) -> None:
        """Fixa o valor da etapa concluída com OPTIMAL (§15.5: "fixar valor
        anterior só se OPTIMAL"). Constante trivial não gera restrição."""
        expression = stage.expression
        if isinstance(expression, int):
            if expression != value:  # pragma: no cover — contrato violado
                raise EduAgentError(
                    ErrorCode.INTERNAL_FAILURE,
                    "valor fixado diverge de objetivo constante (defeito)",
                    diagnostic=_DIAGNOSTIC,
                )
            return
        self._model.Add(expression == value)


def _build_stages_and_model(
    problem: SchedulingProblem,
    grid: _Grid,
    candidates: list[_Candidate],
    settings: SolverSettings,
    demand_index_by_id: dict[_uuid.UUID, int],
) -> tuple[cp_model.CpModel, list[Any], list[_Stage], dict[int, list[int]]]:
    """Modelo do §9: ``x_b∈{0,1}``; obrigatória ``Σ=1``; opcional ``≤1``;
    por slot ``Σ x_b≤1``; limites diários confirmados; precedência
    ``end_i≤start_j``; ``presence_j≤presence_i`` para pré-requisito
    obrigatório."""
    model = cp_model.CpModel()
    variables: list[Any] = [model.NewBoolVar(f"x_{i}") for i in range(len(candidates))]
    by_demand: dict[int, list[int]] = {}
    by_slot: dict[tuple[int, int], list[int]] = {}
    by_day: dict[int, list[int]] = {}
    for index, candidate in enumerate(candidates):
        by_demand.setdefault(candidate.demand_index, []).append(index)
        for offset in range(candidate.n_slots):
            key = (
                candidate.day_index,
                candidate.start_slot + offset,
            )
            by_slot.setdefault(key, []).append(index)
        by_day.setdefault(candidate.day_index, []).append(index)

    presence: dict[int, Any] = {}
    for demand_index, demand in enumerate(problem.demands):
        presence_var = model.NewIntVar(0, 1, f"presence_{demand_index}")
        terms = [variables[i] for i in by_demand.get(demand_index, [])]
        if terms:
            model.Add(presence_var == cp_model.LinearExpr.Sum(terms))
        else:
            model.Add(presence_var == 0)
        presence[demand_index] = presence_var
        if demand.mandatory:
            model.Add(presence_var == 1)  # obrigatória Σ=1 (§9)
        else:
            model.Add(presence_var <= 1)  # opcional ≤1 (§9)

    for covering in by_slot.values():
        if len(covering) > 1:
            model.Add(
                cp_model.LinearExpr.Sum([variables[i] for i in covering]) <= 1
            )

    for limit in problem.daily_limits:
        if limit.day not in grid.days:
            continue  # fora do horizonte: irrelevante para este plano
        day_index_value = grid.days.index(limit.day)
        terms = [
            (variables[i], candidates[i].reserved_minutes)
            for i in by_day.get(day_index_value, [])
        ]
        expr = cp_model.LinearExpr.WeightedSum(
            [term[0] for term in terms], [term[1] for term in terms]
        ) if terms else 0
        model.Add(
            expr + grid.fixed_study[day_index_value] <= limit.study_minutes
        )

    for demand in problem.demands:
        dependent_index = demand_index_by_id[demand.demand_id]
        for predecessor_id in demand.dependencies:
            predecessor_index = demand_index_by_id[predecessor_id]
            predecessor = problem.demands[predecessor_index]
            # Precedência end_i ≤ start_j quando ambos presentes (§9).
            for i in by_demand.get(predecessor_index, []):
                for j in by_demand.get(dependent_index, []):
                    if candidates[i].end_utc > candidates[j].start_utc:
                        model.Add(variables[i] + variables[j] <= 1)
            # Pré-requisito obrigatório não pode ser omitido enquanto o
            # dependente está selecionado (§9: presence_j ≤ presence_i).
            if predecessor.mandatory:
                model.Add(presence[dependent_index] <= presence[predecessor_index])

    # Objetivos lexicográficos (§9/§15.5): classe1 → classe2 → classe3 →
    # alterações de blocos futuros → deslocamento → preferências.
    stages: list[_Stage] = []
    for klass in (1, 2, 3):
        terms = [
            presence[i]
            for i, demand in enumerate(problem.demands)
            if not demand.mandatory and demand.priority_class == klass
        ]
        stages.append(
            _Stage(
                name=f"max_class{klass}",
                expression=cp_model.LinearExpr.Sum(terms) if terms else 0,
                maximize=True,
            )
        )

    existing_by_demand_index: dict[int, ExistingOccurrence] = {}
    for occurrence in problem.existing:
        existing_by_demand_index[
            demand_index_by_id[occurrence.demand_id]
        ] = occurrence

    same_terms: list[Any] = []
    displacement_vars: list[Any] = []
    horizon_minutes = settings.horizon_days * 1440
    for demand_index, occurrence in existing_by_demand_index.items():
        same = [
            variables[i]
            for i in by_demand.get(demand_index, [])
            if candidates[i].same_instants_block_id == occurrence.block_id
        ]
        same_terms.extend(same)
        displacement = model.NewIntVar(
            0, horizon_minutes, f"disp_{occurrence.block_id}"
        )
        for i in by_demand.get(demand_index, []):
            cost = candidates[i].displacement_minutes
            if cost > 0:
                model.Add(displacement >= cost * variables[i])
        displacement_vars.append(displacement)
    total_changes = len(existing_by_demand_index)
    stages.append(
        _Stage(
            name="min_changes",
            expression=total_changes - cp_model.LinearExpr.Sum(same_terms)
            if same_terms
            else total_changes,
            maximize=False,
        )
    )
    stages.append(
        _Stage(
            name="min_displacement_min",
            expression=cp_model.LinearExpr.Sum(displacement_vars)
            if displacement_vars
            else 0,
            maximize=False,
        )
    )
    preference_terms = [
        (variables[i], candidates[i].preferred_minutes)
        for i, candidate in enumerate(candidates)
        if candidate.preferred_minutes > 0
    ]
    stages.append(
        _Stage(
            name="max_preferences",
            expression=cp_model.LinearExpr.WeightedSum(
                [term[0] for term in preference_terms],
                [term[1] for term in preference_terms],
            )
            if preference_terms
            else 0,
            maximize=True,
        )
    )
    return model, variables, stages, by_demand


# -- Verificador independente (§9: separado; reaplica restrições nos
#    minutos/instantes originais, não só na matriz de slots) ------------------


def _wall_minutes_of(
    moment: datetime, day: date, tz: tzinfo | None
) -> int:
    zone = tz if tz is not None else timezone.utc
    local = moment.astimezone(zone)
    if local.date() != day:  # pragma: no cover — chamadores garantem
        raise ValueError("instante fora do dia local informado")
    return local.hour * 60 + local.minute


def _verify_placement(
    problem: SchedulingProblem,
    settings: SolverSettings,
    placed: Sequence[PlacedBlock],
) -> list[str]:
    """Verificador independente (§9): reaplica as restrições nos minutos e
    instantes **originais** — não consulta a matriz de slots nem o modelo do
    solver. Valida demanda, conflitos, precedência, imutabilidade e
    snapshot. Retorna a lista de problemas (vazia = válida)."""
    issues: list[str] = []
    demands_by_id = {d.demand_id: d for d in problem.demands}
    per_demand: dict[_uuid.UUID, list[PlacedBlock]] = {}
    for block in placed:
        per_demand.setdefault(block.demand_id, []).append(block)
        if block.demand_id not in demands_by_id:
            issues.append(f"bloco {block.block_id} sem demanda conhecida")
            continue
        demand = demands_by_id[block.demand_id]
        span = (block.end_utc - block.start_utc).total_seconds() / 60
        if span < demand.duration_minutes:
            issues.append(
                f"bloco {block.block_id}: duração reduzida "
                f"({span:g} min < {demand.duration_minutes} min originais)"
            )
        elif span > -(-demand.duration_minutes // settings.slot_minutes) * settings.slot_minutes:
            issues.append(
                f"bloco {block.block_id}: reserva excede o arredondamento "
                f"de {settings.slot_minutes} min (§9)"
            )
        if block.start_utc < demand.earliest_utc:
            issues.append(f"bloco {block.block_id}: antes de earliest")
        deadline = _demand_deadline_instant(demand, problem.local_timezone)
        if block.end_utc > deadline:
            issues.append(f"bloco {block.block_id}: após deadline confirmado")

    for demand in problem.demands:
        count = len(per_demand.get(demand.demand_id, []))
        if demand.mandatory and count != 1:
            issues.append(
                f"demanda obrigatória {demand.demand_id} sem bloco único "
                f"({count})"
            )
        if count > 1:
            issues.append(
                f"demanda {demand.demand_id} com mais de um bloco (Σ≤1, §9)"
            )

    # Conflitos entre blocos e com fixos (imutabilidade, §9).
    sorted_blocks = sorted(placed, key=lambda b: (b.start_utc, b.end_utc))
    for first, second in zip(sorted_blocks, sorted_blocks[1:]):
        if second.start_utc < first.end_utc:
            issues.append(
                f"conflito: blocos {first.block_id} e {second.block_id} "
                "se sobrepõem"
            )
    for block in placed:
        for fixed in problem.fixed_blocks:
            if block.start_utc < fixed.end_utc and fixed.start_utc < block.end_utc:
                issues.append(
                    f"bloco {block.block_id} sobrepõe bloco fixo imutável "
                    f"({fixed.start_utc.isoformat()}..{fixed.end_utc.isoformat()})"
                )

    days = _horizon_days(problem.horizon_start, settings.horizon_days)
    if days:
        horizon_start_utc = _resolve_wall_instant(
            days[0], 0, problem.local_timezone
        )
        horizon_end_utc = _resolve_wall_instant(
            days[-1] + timedelta(days=1), 0, problem.local_timezone
        )
    else:  # pragma: no cover — horizon_days ≥ 1 validado
        horizon_start_utc = horizon_end_utc = None
    for block in placed:
        if horizon_start_utc is not None and (
            block.start_utc < horizon_start_utc or block.end_utc > horizon_end_utc
        ):
            issues.append(f"bloco {block.block_id}: fora do horizonte")
        # Candidatos não atravessam meia-noite (§15.5); fim exatamente na
        # meia-noite é permitido (fim exclusivo).
        zone = problem.local_timezone or timezone.utc
        start_local = block.start_utc.astimezone(zone)
        end_local = block.end_utc.astimezone(zone)
        crosses = end_local.date() != start_local.date() and not (
            end_local.time() == _dt_time(0, 0)
            and end_local.date() == start_local.date() + timedelta(days=1)
        )
        if crosses:
            issues.append(
                f"bloco {block.block_id} atravessa meia-noite local (§15.5)"
            )
        # Disponibilidade nos instantes originais, sem arredondamento,
        # pela união das janelas do dia (decisão da 012a): mesma semântica
        # da grade/enumerador, cujos candidatos contíguos cobrem runs sobre
        # janelas adjacentes/sobrepostas (§9); contenção em janela única
        # rejeitaria entrada confirmada legítima como INTERNAL_FAILURE.
        day = start_local.date()
        start_minute = _wall_minutes_of(block.start_utc, day, problem.local_timezone)
        end_minute = start_minute + int(
            (block.end_utc - block.start_utc).total_seconds() // 60
        )
        covered = any(
            start_minute >= window_start and end_minute <= window_end
            for window_start, window_end in _merged_availability(problem, day)
        )
        if not covered:
            issues.append(
                f"bloco {block.block_id}: fora das janelas de disponibilidade "
                "originais"
            )

    # Precedência e presença (§9) nos instantes originais.
    for demand in problem.demands:
        dependent_blocks = per_demand.get(demand.demand_id, [])
        if not dependent_blocks:
            continue
        for predecessor_id in demand.dependencies:
            predecessor = demands_by_id.get(predecessor_id)
            if predecessor is None:
                issues.append(
                    f"dependência {predecessor_id} não resolve (§15.4)"
                )
                continue
            predecessor_blocks = per_demand.get(predecessor_id, [])
            if not predecessor_blocks:
                if predecessor.mandatory:
                    issues.append(
                        f"pré-requisito obrigatório {predecessor_id} omitido "
                        f"com dependente {demand.demand_id} selecionado "
                        "(§9: presence_j ≤ presence_i)"
                    )
                continue
            if any(
                pred.end_utc > dep.start_utc
                for pred in predecessor_blocks
                for dep in dependent_blocks
            ):
                issues.append(
                    f"precedência violada: {predecessor_id} termina após "
                    f"início de {demand.demand_id} (§9)"
                )

    # Capacidade diária em minutos efetivamente reservados (§15.5),
    # incluindo arredondamento e blocos fixos de estudo; compromissos
    # pessoais não contam como estudo (§15.5).
    reserved_by_day: dict[date, int] = {}
    for block in placed:
        demand = demands_by_id.get(block.demand_id)
        if demand is None:
            continue
        zone = problem.local_timezone or timezone.utc
        day = block.start_utc.astimezone(zone).date()
        reserved = -(-demand.duration_minutes // settings.slot_minutes) * settings.slot_minutes
        reserved_by_day[day] = reserved_by_day.get(day, 0) + reserved
    for limit in problem.daily_limits:
        if limit.day not in days:
            continue
        total = reserved_by_day.get(limit.day, 0) + _fixed_study_minutes(
            limit.day, problem
        )
        if total > limit.study_minutes:
            issues.append(
                f"capacidade diária do dia {limit.day} excedida: "
                f"{total} > {limit.study_minutes} min reservados (§15.5)"
            )

    # Identidade: block_id/uid únicos e estáveis (§15.5).
    block_ids = [b.block_id for b in placed]
    uids = [b.uid for b in placed]
    if len(set(block_ids)) != len(block_ids):
        issues.append("block_id repetido na proposta (§15.5)")
    if len(set(uids)) != len(uids):
        issues.append("uid repetido na proposta (§15.5)")
    return issues


def _expected_diff(
    problem: SchedulingProblem,
    placed: Sequence[PlacedBlock],
) -> "ScheduleProposal.PlanDiff":
    """Diff por identidade de ocorrência/bloco (§15.5): adições, movimentos
    (mesma identidade, instantes diferentes), remoções; déficit em minutos
    da duração demandada não agendada."""
    existing_by_block = {o.block_id: o for o in problem.existing}
    placed_by_block = {b.block_id: b for b in placed}
    added = sorted(
        str(b.block_id) for b in placed if b.block_id not in existing_by_block
    )
    moved = sorted(
        str(b.block_id)
        for b in placed
        if b.block_id in existing_by_block
        and (
            existing_by_block[b.block_id].start_utc != b.start_utc
            or existing_by_block[b.block_id].end_utc != b.end_utc
        )
    )
    removed = sorted(
        str(o.block_id) for o in problem.existing if o.block_id not in placed_by_block
    )
    scheduled = {b.demand_id for b in placed}
    deficit = sum(
        d.duration_minutes for d in problem.demands if d.demand_id not in scheduled
    )
    return ScheduleProposal.PlanDiff(
        added=added, moved=moved, removed=removed, deficit_minutes=deficit
    )


def verify_schedule(
    problem: SchedulingProblem,
    proposal: ScheduleProposal,
    *,
    settings: SolverSettings | None = None,
    clock: Callable[[], datetime] | None = None,
) -> "ScheduleProposal.PlanValidation":
    """Verificador independente público (mapa §9): revalida a proposta
    contra o problema confirmado — minutos/instantes originais, demandas,
    conflitos, precedência, imutabilidade, snapshot e diff por identidade.
    Usado pelo solver após cada etapa e reutilizável no preview/confirmação
    (task 013)."""
    now = (clock or (lambda: datetime.now(timezone.utc)))().astimezone(
        timezone.utc
    )
    active_settings = settings or load_solver_settings()
    issues: list[str] = []
    if proposal.snapshot_version != problem.snapshot_version:
        issues.append(
            f"snapshot divergente: proposta {proposal.snapshot_version} != "
            f"problema {problem.snapshot_version} (§15.1)"
        )
    solution_status = proposal.status in (
        ScheduleProposal.SolverStatus.OPTIMAL,
        ScheduleProposal.SolverStatus.FEASIBLE,
    )
    issues.extend(
        _verify_placement(
            problem,
            active_settings,
            [
                PlacedBlock(
                    occurrence_id=_occurrence_for_block(problem, block),
                    block_id=block.block_id,
                    uid=block.uid,
                    demand_id=block.demand_id,
                    start_utc=block.start_utc,
                    end_utc=block.end_utc,
                )
                for block in proposal.blocks
            ],
        )
    )
    if not solution_status and proposal.blocks:
        issues.append(
            "status sem solução não publica blocos (§9: nunca publicar "
            "relaxação diagnóstica como aprovado)"
        )
    if solution_status:
        expected = _expected_diff(problem, list(proposal.blocks))
        actual = proposal.diff
        if (
            sorted(expected.added) != sorted(actual.added)
            or sorted(expected.moved) != sorted(actual.moved)
            or sorted(expected.removed) != sorted(actual.removed)
            or expected.deficit_minutes != actual.deficit_minutes
        ):
            issues.append("diff não confere com blocos e identidades (§15.5)")
        scheduled = {block.demand_id for block in proposal.blocks}
        expected_unmet = sorted(
            str(d.demand_id)
            for d in problem.demands
            if d.demand_id not in scheduled
        )
        if sorted(str(u) for u in proposal.unmet_demands) != expected_unmet:
            issues.append("unmet_demands não confere com os blocos (§9)")
    return ScheduleProposal.PlanValidation(
        passed=not issues,
        verifier_id=VERIFIER_ID,
        checked_at=now,
        issues=issues[:64],
    )


def _occurrence_for_block(
    problem: SchedulingProblem, block: "ScheduleProposal.PlanBlock"
) -> _uuid.UUID:
    """Recupera a identidade de ocorrência do bloco (§15.5): da ocorrência
    aprovada com o mesmo block_id, do occurrence_id da demanda, ou da
    derivação determinística do solver."""
    for occurrence in problem.existing:
        if occurrence.block_id == block.block_id:
            return occurrence.occurrence_id
    for demand in problem.demands:
        if demand.demand_id == block.demand_id:
            if demand.occurrence_id is not None:
                return demand.occurrence_id
            return _uuid.uuid5(
                _SOLVER_NAMESPACE, f"occurrence|{demand.demand_id}"
            )
    return block.block_id  # pragma: no cover — demanda desconhecida já gera issue


# -- Ferramenta schedule.solve (mapa §10: Planejador; §9/§15.5) ---------------


def _mint_identity(
    demand: SolverDemand, occurrence: ExistingOccurrence | None
) -> tuple[_uuid.UUID, _uuid.UUID, _uuid.UUID]:
    """Identidade do bloco colocado (§15.5): ocorrência aprovada mantém
    ``block_id``/``uid`` em mudança de horário; ocorrência nova recebe ID
    determinístico (persistência é da confirmação, task 013)."""
    if occurrence is not None:
        occurrence_id = occurrence.occurrence_id
        block_id = occurrence.block_id
        uid = occurrence.uid or _uuid.uuid5(
            _SOLVER_NAMESPACE, f"uid|{occurrence_id}"
        )
        return occurrence_id, block_id, uid
    occurrence_id = demand.occurrence_id or _uuid.uuid5(
        _SOLVER_NAMESPACE, f"occurrence|{demand.demand_id}"
    )
    block_id = _uuid.uuid5(_SOLVER_NAMESPACE, f"block|{occurrence_id}")
    uid = _uuid.uuid5(_SOLVER_NAMESPACE, f"uid|{occurrence_id}")
    return occurrence_id, block_id, uid


def _blocks_to_proposal_blocks(
    placed: Sequence[PlacedBlock],
) -> list["ScheduleProposal.PlanBlock"]:
    return [
        ScheduleProposal.PlanBlock(
            block_id=block.block_id,
            demand_id=block.demand_id,
            start_utc=block.start_utc,
            end_utc=block.end_utc,
            uid=block.uid,
        )
        for block in sorted(
            placed, key=lambda b: (b.start_utc, b.demand_id)
        )
    ]


def solve_schedule(
    problem: SchedulingProblem,
    *,
    sender_role: SenderRole,
    plan_id: _uuid.UUID | None = None,
    revision: int = 1,
    settings: SolverSettings | None = None,
    clock: Callable[[], datetime] | None = None,
) -> ScheduleSolveResult:
    """Ferramenta ``schedule.solve`` (mapa §10): proposta de grade com
    objetivos lexicográficos (§9) e protocolo de orçamento (§15.5), seguida
    da validação do verificador independente.

    Pré-condição da tabela de ferramentas (§10): demandas/agenda
    confirmadas — o problema carrega somente dados confirmados. Erros de
    entrada são tipados e explícitos; inviabilidade é apresentada como
    "inviável na grade conservadora de 15 min; viabilidade contínua não
    determinada" (§15.5).
    """
    validate_tool_request(ToolName.SCHEDULE_SOLVE, sender_role)
    active_settings = settings or load_solver_settings()
    now = (clock or (lambda: datetime.now(timezone.utc)))().astimezone(
        timezone.utc
    )
    demand_index_by_id = _validate_problem(problem, active_settings)
    grid = _build_grid(problem, active_settings)
    candidates = _enumerate_candidates(
        problem, grid, active_settings, demand_index_by_id
    )
    model, variables, stages, by_demand = _build_stages_and_model(
        problem, grid, candidates, active_settings, demand_index_by_id
    )
    existing_by_demand: dict[int, ExistingOccurrence] = {}
    for occurrence in problem.existing:
        existing_by_demand[demand_index_by_id[occurrence.demand_id]] = occurrence

    def extract(selected: Sequence[int]) -> list[PlacedBlock]:
        placed: list[PlacedBlock] = []
        for index in selected:
            candidate = candidates[index]
            demand = problem.demands[candidate.demand_index]
            occurrence = existing_by_demand.get(candidate.demand_index)
            occurrence_id, block_id, uid = _mint_identity(demand, occurrence)
            placed.append(
                PlacedBlock(
                    occurrence_id=occurrence_id,
                    block_id=block_id,
                    uid=uid,
                    demand_id=demand.demand_id,
                    start_utc=candidate.start_utc,
                    end_utc=candidate.end_utc,
                )
            )
        placed.sort(key=lambda b: (b.start_utc, b.demand_id))
        return placed

    def verify(placed: list[PlacedBlock]) -> list[str]:
        return _verify_placement(problem, active_settings, placed)

    driver = _LexicographicDriver(
        model=model,
        stages=stages,
        variables=variables,
        settings=active_settings,
        extract=extract,
        verify=verify,
    )
    status, placed, proofs = driver.run()

    final_plan_id = plan_id or _uuid.uuid5(
        _SOLVER_NAMESPACE,
        f"plan|{problem.user_id}|{problem.snapshot_version}|{revision}",
    )
    objective_text = "lexicografico: " + " > ".join(
        f"{proof.stage}={proof.value if proof.value is not None else proof.status}"
        for proof in proofs
    )
    explanation_parts = [
        f"status={status.value}; etapas="
        + ",".join(f"{p.stage}:{p.status}" for p in proofs)
    ]
    if status is ScheduleProposal.SolverStatus.INFEASIBLE:
        explanation_parts.append(
            _CONSERVATIVE_GRID_MESSAGE.format(
                slot=active_settings.slot_minutes
            )
        )
    elif status is ScheduleProposal.SolverStatus.UNKNOWN:
        explanation_parts.append(
            "inconclusivo dentro do orçamento de tempo; nada é publicado "
            "como aprovado (§9)"
        )
    elif status is ScheduleProposal.SolverStatus.MODEL_INVALID:
        explanation_parts.append(
            "defeito do modelo (§9); nada é publicado como aprovado"
        )

    if placed is None:
        # Sem solução: nada publicado como aprovado (mapa §9/§12).
        deficit = sum(d.duration_minutes for d in problem.demands)
        proposal = ScheduleProposal(
            plan_id=final_plan_id,
            revision=revision,
            snapshot_version=problem.snapshot_version,
            status=status,
            blocks=[],
            unmet_demands=[d.demand_id for d in problem.demands],
            diff=ScheduleProposal.PlanDiff(
                added=[], moved=[], removed=[], deficit_minutes=deficit
            ),
            validation=ScheduleProposal.PlanValidation(
                passed=False,
                verifier_id=VERIFIER_ID,
                checked_at=now,
                issues=explanation_parts[:1],
            ),
            objective=objective_text[:512],
            bound=None,
            explanation="; ".join(explanation_parts)[:_MAX_SOLVER_TEXT],
        )
        return ScheduleSolveResult(proposal=proposal, proofs=tuple(proofs))

    assert placed is not None
    placement_issues = _verify_placement(problem, active_settings, placed)
    if placement_issues:  # pragma: no cover — driver já valida cada etapa
        raise EduAgentError(
            ErrorCode.INTERNAL_FAILURE,
            "incumbent final falhou no verificador independente",
            diagnostic=_DIAGNOSTIC,
        )
    scheduled = {block.demand_id for block in placed}
    unmet = [d.demand_id for d in problem.demands if d.demand_id not in scheduled]
    diff = _expected_diff(problem, placed)
    proposal = ScheduleProposal(
        plan_id=final_plan_id,
        revision=revision,
        snapshot_version=problem.snapshot_version,
        status=status,
        blocks=_blocks_to_proposal_blocks(placed),
        unmet_demands=unmet,
        diff=diff,
        validation=ScheduleProposal.PlanValidation(
            passed=True,
            verifier_id=VERIFIER_ID,
            checked_at=now,
            issues=[],
        ),
        objective=objective_text[:512],
        bound=float(proofs[0].value) if proofs and proofs[0].value is not None else None,
        explanation="; ".join(explanation_parts)[:_MAX_SOLVER_TEXT],
    )
    return ScheduleSolveResult(proposal=proposal, proofs=tuple(proofs))


__all__ = [
    "ACTION_DEMAND_UPSERT",
    "ConfirmedExam",
    "DURATION_CATALOG_MINUTES",
    "DailyStudyLimit",
    "DemandCandidate",
    "DemandGeneration",
    "DemandRecord",
    "DemandService",
    "EXAM_NEAR_DAYS",
    "EXAM_URGENT_HOURS",
    "ExistingOccurrence",
    "FixedBlock",
    "HORIZON_DAYS",
    "PlacedBlock",
    "PolicyOutcome",
    "POLICY_VERSION",
    "RECOVERY_OFFSETS_DAYS",
    "SchedulingProblem",
    "ScheduleSolveResult",
    "SolverDemand",
    "SolverSettings",
    "StageProof",
    "TimeWindow",
    "VERIFIER_ID",
    "compute_demand_candidates",
    "exam_priority_class",
    "has_recurrent_difficulty",
    "load_solver_settings",
    "next_available_day",
    "solve_schedule",
    "verify_schedule",
]
