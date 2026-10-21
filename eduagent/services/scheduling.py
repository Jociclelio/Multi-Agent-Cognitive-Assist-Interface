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
import uuid as _uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, tzinfo
from enum import Enum
from typing import Any

from eduagent.contracts import (
    Assessment,
    EduAgentError,
    ErrorCode,
    StudyDemand,
    TopicState,
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


__all__ = [
    "ACTION_DEMAND_UPSERT",
    "ConfirmedExam",
    "DURATION_CATALOG_MINUTES",
    "DemandCandidate",
    "DemandGeneration",
    "DemandRecord",
    "DemandService",
    "EXAM_NEAR_DAYS",
    "EXAM_URGENT_HOURS",
    "HORIZON_DAYS",
    "PolicyOutcome",
    "POLICY_VERSION",
    "RECOVERY_OFFSETS_DAYS",
    "compute_demand_candidates",
    "exam_priority_class",
    "has_recurrent_difficulty",
    "next_available_day",
]
