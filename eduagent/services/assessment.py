"""Serviço de avaliação: validador de assessments e redutor determinístico
(mapa §8, §15.2; contratos ``Assessment``/``TopicState``/``RubricCriterion``
da task 003 + §15.2).

Responsabilidades (mapa §8/§15.2):

- ``AssessmentService.check``: aceita **apenas** Assessment válido —
  unicidade lógica ``(attempt_id, assessment_revision)`` (§15.2), revisão
  monotônica, correção (revision > 1) exige ``supersedes`` apontando para a
  avaliação vigente do attempt e consistência formal entre
  ``correctness`` e a agregação dos critérios (§15.2). Assessment em
  abstinência é registrado (feedback sem atualização inferencial, §8), mas
  nunca entra na projeção.
- ``record_attempt``: tentativa com ``occurred_at`` informado e
  ``attempt_ordinal`` atribuído no commit (subconsulta atômica na inserção);
  independência julgada no commit: hint_level 0, sem reveal e sem acesso
  prévio à solução da família na sessão corrente (§15.2).
- ``compute_topic_states``: projeção **recalculada desde eventos** a cada
  novo assessment (não atualização cumulativa): para cada tópico, avaliação
  vigente por tentativa = maior ``assessment_revision`` explicitamente
  aceito; regra ``favorable`` aplicada exatamente como §8/§15.2 — três
  tentativas mais recentes independentes, aceitas e decidíveis no tópico,
  todas corretas, de famílias distintas, posteriores ao último erro crítico
  aceito; erro crítico novo volta a mixed mesmo assistido; tentativa
  independente parcial/incorreta interrompe; assistidas não removem erro
  crítico nem compõem a sequência; "recentes" é ordem cronológica
  (``occurred_at``, desempate por ``attempt_ordinal``); idade é informada à
  parte (``last_attempt_at``), nunca como janela de dias.

BKT NÃO é implementado: ``TopicState.estimate=None`` no MVP (mapa §8) e
nenhum prior cognitivo é inventado. ``review_due`` fica ``None`` aqui — a
política ``assessment_review_policy_v1`` (§15.3) é da task 011.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid as _uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from eduagent.contracts import (
    Assessment,
    EduAgentError,
    ErrorCode,
    TopicState,
)
from eduagent.services.effects import CommitRequest, EffectsService, EventSpec
from eduagent.storage.repository import DomainStore, Receipt

_DIAGNOSTIC = "eduagent/services/assessment.py"

#: Identificação do modelo de regras do redutor (``TopicState.model_version``,
#: mapa §4). Versão de ensaio das regras determinísticas — não modelo de ML.
MODEL_VERSION = "monitor-rules-mvp"

#: Tipos de evento e ações do commit idempotente (mapa §5/§11). Tentativa é
#: apêndice de evento com projeção (``event.append``); avaliação tem ação
#: própria no enum ``OperationAction`` (mapa §4).
EVENT_ATTEMPT = "attempt_recorded"
EVENT_ASSESSMENT = "assessment_recorded"
ACTION_ATTEMPT = "event.append"
ACTION_ASSESSMENT = "assessment.record"


# ---------------------------------------------------------------------------
# Fatos de projeção (interface pura entre banco e regras)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AttemptRecord:
    """Resultado de ``record_attempt``: IDs e ordem atribuídos no commit."""

    attempt_id: _uuid.UUID
    attempt_ordinal: int
    occurred_at: datetime
    independent: bool
    receipt: Receipt


@dataclass(frozen=True)
class AttemptFact:
    """Tentativa projetada (mapa §8/§15.2)."""

    attempt_id: _uuid.UUID
    item_id: _uuid.UUID
    family_id: _uuid.UUID
    occurred_at: datetime
    attempt_ordinal: int
    help_level: int
    revealed: bool
    independent: bool

    @property
    def order_key(self) -> tuple[datetime, int]:
        # "Recentes" é ordem cronológica; desempate por ordinal (§15.2).
        return (self.occurred_at, self.attempt_ordinal)


@dataclass(frozen=True)
class AssessmentFact:
    """Avaliação projetada com os critérios críticos da rubrica no momento
    do commit (os resultados por critério não carregam ``critical``, que é
    propriedade da rubrica — §15.2)."""

    assessment_id: _uuid.UUID
    attempt_id: _uuid.UUID
    assessment_revision: int
    results: tuple[Assessment.CriterionResult, ...]
    correctness: Assessment.Correctness
    reliability: Assessment.Reliability
    critical_criterion_ids: frozenset[str]


@dataclass(frozen=True)
class AssessmentCheckResult:
    """Resultado de ``check``: recibo, aceitação e estados recalculados."""

    assessment_id: _uuid.UUID
    receipt: Receipt
    accepted: bool
    topic_states: dict[_uuid.UUID, TopicState]


def _digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _aggregate(levels: Sequence[int]) -> Assessment.Correctness:
    """Agregação do §15.2 sobre níveis decididos: todos 2=correct; todos
    0=incorrect; mistura=partial."""
    if levels and all(level == 2 for level in levels):
        return Assessment.Correctness.CORRECT
    if levels and all(level == 0 for level in levels):
        return Assessment.Correctness.INCORRECT
    return Assessment.Correctness.PARTIAL


def _topic_correctness(
    assessment: AssessmentFact, topic_id: _uuid.UUID
) -> Assessment.Correctness | None:
    """Avaliação por tópico usa SOMENTE os critérios do tópico (§15.2)."""
    levels = [
        result.level
        for result in assessment.results
        if len(result.topic_ids) == 1 and result.topic_ids[0] == topic_id
    ]
    if not levels:
        return None
    return _aggregate(levels)


# ---------------------------------------------------------------------------
# Redutor puro: projeção de TopicState desde eventos (§8/§15.2)
# ---------------------------------------------------------------------------


def compute_topic_states(
    attempts: Sequence[AttemptFact],
    assessments: Sequence[AssessmentFact],
    *,
    model_version: str = MODEL_VERSION,
    revision_by_topic: Mapping[_uuid.UUID, int] | None = None,
) -> dict[_uuid.UUID, TopicState]:
    """Recalcula os ``TopicState`` desde a história completa de tentativas e
    avaliações (não cumulativo).

    Devolve estados apenas para tópicos com evidência (tentativa com
    avaliação vigente aceita tocando o tópico por critério de tópico único);
    tópicos sem evidência ficam ``insufficient`` na camada de serviço, que
    conhece o conjunto de tópicos nomeados pelos assessments.

    Escolhas de implementação registradas (detalhes na task 009):

    - Decidibilidade da tentativa para o tópico segue o ``correctness``
      global do assessment vigente: ``undecidable`` não compõe nem interrompe
      a sequência (§8 interrompe apenas parcial/incorreta independente).
    - Erro crítico conta apenas em assessment aceito e decidível, por
      critério de tópico único marcado ``critical`` com nível 0 (§8/§15.2).
    - Critério de múltiplos tópicos não decomposto: a tentativa não atualiza
      o estado desses tópicos (§15.2).
    - ``error_codes`` fica vazio no MVP: os códigos de sistema (mapa §4) não
      descrevem misconceptions pedagógicas, que permanecem nos assessments.
    """
    by_attempt: dict[_uuid.UUID, list[AssessmentFact]] = {}
    for fact in assessments:
        by_attempt.setdefault(fact.attempt_id, []).append(fact)
    # Avaliação vigente = maior assessment_revision explicitamente aceito
    # (§15.2); assessments em abstinência nunca são vigentes.
    current: dict[_uuid.UUID, AssessmentFact] = {}
    for attempt_id, facts in by_attempt.items():
        accepted = [
            fact
            for fact in facts
            if fact.reliability is Assessment.Reliability.ACCEPTED
        ]
        if accepted:
            current[attempt_id] = max(
                accepted, key=lambda fact: fact.assessment_revision
            )
    touched: dict[_uuid.UUID, list[tuple[AttemptFact, AssessmentFact]]] = {}
    for attempt in attempts:
        vigente = current.get(attempt.attempt_id)
        if vigente is None:
            continue
        # §15.2: critério de múltiplos tópicos não decomposto — a tentativa
        # não atualiza o estado desses tópicos.
        excluded = {
            topic
            for result in vigente.results
            for topic in result.topic_ids
            if len(result.topic_ids) > 1
        }
        topics_touched: set[_uuid.UUID] = set()
        for result in vigente.results:
            if len(result.topic_ids) != 1:
                continue
            topic_id = result.topic_ids[0]
            if topic_id in excluded:
                continue
            topics_touched.add(topic_id)
        for topic_id in sorted(topics_touched, key=str):
            touched.setdefault(topic_id, []).append((attempt, vigente))

    previous = dict(revision_by_topic or {})
    states: dict[_uuid.UUID, TopicState] = {}
    for topic_id, entries in touched.items():
        entries = sorted(entries, key=lambda entry: entry[0].order_key)

        def _critical_error(
            entry: tuple[AttemptFact, AssessmentFact]
        ) -> bool:
            _, vigente = entry
            if vigente.correctness is Assessment.Correctness.UNDECIDABLE:
                return False
            return any(
                result.level == 0
                and result.criterion_id in vigente.critical_criterion_ids
                for result in vigente.results
                if len(result.topic_ids) == 1
                and result.topic_ids[0] == topic_id
            )

        # Elegíveis: independentes, aceitas e decidíveis no tópico (§8).
        eligible = [
            entry
            for entry in entries
            if entry[0].independent
            and entry[1].correctness is not Assessment.Correctness.UNDECIDABLE
        ]
        last_critical = next(
            (entry for entry in reversed(entries) if _critical_error(entry)),
            None,
        )
        recent_three = eligible[-3:]
        favorable = (
            len(recent_three) == 3
            and all(
                _topic_correctness(vigente, topic_id)
                is Assessment.Correctness.CORRECT
                for _, vigente in recent_three
            )
            and len({attempt.family_id for attempt, _ in recent_three}) == 3
            and (
                last_critical is None
                or all(
                    attempt.order_key > last_critical[0].order_key
                    for attempt, _ in recent_three
                )
            )
        )
        independent_ids = [
            attempt.attempt_id for attempt, _ in entries if attempt.independent
        ]
        assisted_ids = [
            attempt.attempt_id
            for attempt, _ in entries
            if not attempt.independent
        ]
        states[topic_id] = TopicState(
            topic_id=topic_id,
            independent_attempt_ids=independent_ids,
            assisted_attempt_ids=assisted_ids,
            error_codes=[],
            last_attempt_at=max(
                attempt.occurred_at for attempt, _ in entries
            ),
            status=(
                TopicState.TopicStatus.FAVORABLE
                if favorable
                else TopicState.TopicStatus.MIXED
            ),
            estimate=None,  # MVP (mapa §8): sem BKT, sem priors
            review_due=None,  # política §15.3 é da task 011
            model_version=model_version,
            revision=previous.get(topic_id, 0) + 1,
        )
    return states


# ---------------------------------------------------------------------------
# Serviço de avaliação (commit idempotente + projeção)
# ---------------------------------------------------------------------------


class AssessmentService:
    """Valida assessments, registra tentativas/avaliações via commit
    idempotente e projeta ``TopicState`` desde eventos (mapa §8, §15.2)."""

    def __init__(
        self,
        store: DomainStore,
        effects: EffectsService,
        *,
        clock: Any = None,
    ) -> None:
        self._store = store
        self._effects = effects
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    # -- tentativas ----------------------------------------------------------

    def record_attempt(
        self,
        *,
        user_id: str,
        session_id: str | None,
        item_id: _uuid.UUID,
        family_id: _uuid.UUID,
        response_text: str,
        help_level: int,
        revealed: bool,
        family_solution_seen_in_session: bool,
        occurred_at: datetime,
        attempt_id: _uuid.UUID | None = None,
    ) -> AttemptRecord:
        """Registra a tentativa: evento + projeção com ordinal atribuído no
        commit e independência julgada no commit (§15.2)."""
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "occurred_at da tentativa exige zona (UTC/offset)",
                diagnostic=_DIAGNOSTIC,
            )
        if help_level not in (0, 1, 2, 3):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "help_level da tentativa deve estar em 0..3",
                diagnostic=_DIAGNOSTIC,
            )
        with self._store.read_transaction() as conn:
            item = conn.execute(
                "SELECT family_id FROM items WHERE user_id = ? AND id = ?",
                (user_id, str(item_id)),
            ).fetchone()
        if item is None:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"item {item_id} não resolve para o usuário",
                diagnostic=_DIAGNOSTIC,
            )
        if str(item["family_id"]) != str(family_id):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "family_id informado não confere com o item publicado",
                diagnostic=_DIAGNOSTIC,
            )
        independent = (
            help_level == 0
            and not revealed
            and not family_solution_seen_in_session
        )
        attempt_id = attempt_id or _uuid.uuid4()
        event_id = str(_uuid.uuid4())
        occurred_iso = occurred_at.astimezone(timezone.utc).isoformat()
        now_iso = self._clock().astimezone(timezone.utc).isoformat()
        payload = {
            "attempt_id": str(attempt_id),
            "item_id": str(item_id),
            "family_id": str(family_id),
            "response": response_text,
            "help_level": help_level,
            "revealed": bool(revealed),
            "family_solution_seen_in_session": bool(
                family_solution_seen_in_session
            ),
            "independent": independent,
            "occurred_at": occurred_iso,
        }
        request = CommitRequest(
            operation_id=str(_uuid.uuid4()),
            user_id=user_id,
            action=ACTION_ATTEMPT,
            digest=_digest(payload),
            expected_version=self._store.domain_revision(user_id),
            event=EventSpec(
                id=event_id,
                kind=EVENT_ATTEMPT,
                occurred_at=occurred_iso,
                recorded_at=now_iso,
                payload=payload,
                session_id=session_id,
            ),
            projection=(
                # Ordinal atribuído no commit, atomicamente (§15.2).
                (
                    "INSERT INTO attempts(id, user_id, item_id, "
                    "response_event_id, help_level, revealed, "
                    "attempt_ordinal, family_id, independent) VALUES "
                    "(?,?,?,?,?,?,"
                    "(SELECT COALESCE(MAX(attempt_ordinal),0)+1 FROM "
                    "attempts WHERE user_id = ?),?,?)",
                    (
                        str(attempt_id),
                        user_id,
                        str(item_id),
                        event_id,
                        help_level,
                        int(bool(revealed)),
                        user_id,
                        str(family_id),
                        int(independent),
                    ),
                ),
            ),
        )
        try:
            receipt = self._effects.commit(request)
        except sqlite3.IntegrityError as exc:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"tentativa não registrada: violação de integridade ({exc})",
                diagnostic=_DIAGNOSTIC,
            ) from exc
        with self._store.read_transaction() as conn:
            row = conn.execute(
                "SELECT attempt_ordinal FROM attempts WHERE user_id = ? "
                "AND id = ?",
                (user_id, str(attempt_id)),
            ).fetchone()
        if row is None:  # pragma: no cover — commit confirmou a inserção
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                "tentativa não encontrada após commit",
                diagnostic=_DIAGNOSTIC,
            )
        return AttemptRecord(
            attempt_id=attempt_id,
            attempt_ordinal=int(row["attempt_ordinal"]),
            occurred_at=occurred_at.astimezone(timezone.utc),
            independent=independent,
            receipt=receipt,
        )

    # -- avaliação (assessment.check) ---------------------------------------

    def check(
        self,
        *,
        user_id: str,
        session_id: str | None,
        assessment: Assessment,
        critical_criterion_ids: Sequence[str] = (),
        operation_id: str | None = None,
        assessment_id: _uuid.UUID | None = None,
    ) -> AssessmentCheckResult:
        """Valida e registra o Assessment (uma vez por attempt_id por
        revision) e recalcula a projeção de ``TopicState`` desde eventos
        (mapa §8/§15.2)."""
        critical = frozenset(critical_criterion_ids)
        attempt_id = assessment.attempt_id
        with self._store.read_transaction() as conn:
            attempt = conn.execute(
                "SELECT a.id AS id, a.item_id AS item_id, "
                "a.attempt_ordinal AS attempt_ordinal, e.occurred_at AS "
                "occurred_at, a.independent AS independent FROM attempts a "
                "JOIN events e ON e.id = a.response_event_id "
                "WHERE a.user_id = ? AND a.id = ?",
                (user_id, str(attempt_id)),
            ).fetchone()
            existing = conn.execute(
                "SELECT id, assessment_revision FROM assessments "
                "WHERE attempt_user_id = ? AND attempt_id = ? "
                "ORDER BY assessment_revision",
                (user_id, str(attempt_id)),
            ).fetchall()
            topic_revisions = {
                _uuid.UUID(row["topic_id"]): int(row["revision"])
                for row in conn.execute(
                    "SELECT topic_id, revision FROM topic_states "
                    "WHERE user_id = ?",
                    (user_id,),
                ).fetchall()
            }
            attempt_rows = conn.execute(
                "SELECT a.id AS id, a.item_id AS item_id, i.family_id AS "
                "family_id, e.occurred_at AS occurred_at, "
                "a.attempt_ordinal AS attempt_ordinal, a.help_level AS "
                "help_level, a.revealed AS revealed, a.independent AS "
                "independent FROM attempts a JOIN items i ON i.user_id = "
                "a.user_id AND i.id = a.item_id JOIN events e ON e.id = "
                "a.response_event_id WHERE a.user_id = ?",
                (user_id,),
            ).fetchall()
            assessment_rows = conn.execute(
                "SELECT id, attempt_id, assessment_revision, payload_json "
                "FROM assessments WHERE attempt_user_id = ?",
                (user_id,),
            ).fetchall()
        if attempt is None:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"tentativa {attempt_id} não resolve para o usuário",
                diagnostic=_DIAGNOSTIC,
            )
        if _uuid.UUID(str(attempt["item_id"])) != assessment.item_ref.id:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "item_ref do assessment não confere com a tentativa",
                diagnostic=_DIAGNOSTIC,
            )
        existing_revisions = [int(row["assessment_revision"]) for row in existing]
        if assessment.assessment_revision in existing_revisions:
            # Unicidade lógica (attempt_id, assessment_revision) — §15.2.
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "unicidade lógica violada: já existe assessment para "
                f"(attempt_id={attempt_id}, "
                f"assessment_revision={assessment.assessment_revision})",
                diagnostic=_DIAGNOSTIC,
            )
        max_revision = max(existing_revisions, default=0)
        if assessment.assessment_revision <= max_revision:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "assessment_revision deve ser estritamente maior que a "
                f"maior revision registrada ({max_revision})",
                diagnostic=_DIAGNOSTIC,
            )
        if assessment.assessment_revision == 1:
            if assessment.supersedes is not None:
                raise EduAgentError(
                    ErrorCode.SCHEMA_INVALID,
                    "revision 1 não pode supersedar avaliação (§15.2)",
                    diagnostic=_DIAGNOSTIC,
                )
        else:
            # Correção: supersedes obrigatório apontando para a avaliação
            # vigente (maior revision registrada) — §15.2.
            if assessment.supersedes is None:
                raise EduAgentError(
                    ErrorCode.SCHEMA_INVALID,
                    "correção (revision > 1) exige supersedes (§15.2)",
                    diagnostic=_DIAGNOSTIC,
                )
            if max_revision == 0:
                raise EduAgentError(
                    ErrorCode.SCHEMA_INVALID,
                    "correção sem avaliação prévia registrada",
                    diagnostic=_DIAGNOSTIC,
                )
            vigente = existing[-1]
            if (
                assessment.supersedes.id != _uuid.UUID(str(vigente["id"]))
                or assessment.supersedes.version != int(
                    vigente["assessment_revision"]
                )
            ):
                raise EduAgentError(
                    ErrorCode.SCHEMA_INVALID,
                    "supersedes deve apontar para a avaliação vigente "
                    "(maior assessment_revision) do attempt (§15.2)",
                    diagnostic=_DIAGNOSTIC,
                )
        # Consistência formal (§15.2): a agregação dos critérios decididos
        # tem de coincidir com o rótulo global — divergência formal é
        # recusada, não abstida (o Monitor abstém, o redutor recusa).
        if (
            assessment.reliability is Assessment.Reliability.ACCEPTED
            and assessment.correctness is not Assessment.Correctness.UNDECIDABLE
        ):
            levels = [result.level for result in assessment.criterion_results]
            if _aggregate(levels) is not assessment.correctness:
                raise EduAgentError(
                    ErrorCode.SCHEMA_INVALID,
                    "correctness diverge da agregação dos critérios "
                    "(todos 2=correct; todos 0=incorrect; mistura=partial)",
                    diagnostic=_DIAGNOSTIC,
                )

        assessment_id = assessment_id or _uuid.uuid4()
        new_fact = AssessmentFact(
            assessment_id=assessment_id,
            attempt_id=attempt_id,
            assessment_revision=assessment.assessment_revision,
            results=tuple(assessment.criterion_results),
            correctness=assessment.correctness,
            reliability=assessment.reliability,
            critical_criterion_ids=critical,
        )
        attempts_facts, assessments_facts = _facts_from_rows(
            attempt_rows, assessment_rows
        )
        states = compute_topic_states(
            attempts_facts,
            [*assessments_facts, new_fact],
            revision_by_topic=topic_revisions,
        )
        # Tópicos afetados: os nomeados por ESTE assessment (mesmo abstido —
        # evidência zero é ``insufficient``, §8) e os já projetados.
        affected = set(topic_revisions)
        for result in assessment.criterion_results:
            affected.update(result.topic_ids)
        for topic_id in affected - set(states):
            states[topic_id] = TopicState(
                topic_id=topic_id,
                independent_attempt_ids=[],
                assisted_attempt_ids=[],
                error_codes=[],
                last_attempt_at=None,
                status=TopicState.TopicStatus.INSUFFICIENT,
                estimate=None,
                review_due=None,
                model_version=MODEL_VERSION,
                revision=topic_revisions.get(topic_id, 0) + 1,
            )

        extended = {
            "assessment": assessment.model_dump(mode="json"),
            "critical_criterion_ids": sorted(critical),
        }
        event_payload = dict(extended)
        event_payload["accepted"] = (
            assessment.reliability is Assessment.Reliability.ACCEPTED
        )
        statements: list[tuple[str, tuple[Any, ...]]] = [
            (
                "INSERT INTO assessments(id, attempt_id, attempt_user_id, "
                "assessor_version, payload_json, assessment_revision, "
                "supersedes) VALUES (?,?,?,?,?,?,?)",
                (
                    str(assessment_id),
                    str(attempt_id),
                    user_id,
                    MODEL_VERSION,
                    json.dumps(extended, sort_keys=True, ensure_ascii=False),
                    assessment.assessment_revision,
                    str(assessment.supersedes.id)
                    if assessment.supersedes is not None
                    else None,
                ),
            )
        ]
        for topic_id, state in states.items():
            statements.append(
                (
                    "INSERT INTO topic_states(user_id, topic_id, revision, "
                    "payload_json) VALUES (?,?,?,?) ON CONFLICT(user_id, "
                    "topic_id) DO UPDATE SET revision = excluded.revision, "
                    "payload_json = excluded.payload_json",
                    (
                        user_id,
                        str(topic_id),
                        state.revision,
                        state.model_dump_json(),
                    ),
                )
            )
        now_iso = self._clock().astimezone(timezone.utc).isoformat()
        request = CommitRequest(
            operation_id=operation_id or str(_uuid.uuid4()),
            user_id=user_id,
            action=ACTION_ASSESSMENT,
            digest=_digest(extended),
            expected_version=self._store.domain_revision(user_id),
            event=EventSpec(
                id=str(_uuid.uuid4()),
                kind=EVENT_ASSESSMENT,
                occurred_at=now_iso,
                recorded_at=now_iso,
                payload=event_payload,
                session_id=session_id,
            ),
            projection=tuple(statements),
        )
        try:
            receipt = self._effects.commit(request)
        except sqlite3.IntegrityError as exc:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"assessment não registrado: violação de integridade ({exc})",
                diagnostic=_DIAGNOSTIC,
            ) from exc
        return AssessmentCheckResult(
            assessment_id=assessment_id,
            receipt=receipt,
            accepted=(
                assessment.reliability is Assessment.Reliability.ACCEPTED
            ),
            topic_states=states,
        )

    # -- leitura da projeção --------------------------------------------------

    def load_facts(
        self, user_id: str
    ) -> tuple[list[AttemptFact], list[AssessmentFact]]:
        """Fatos projetados do usuário (tentativas + assessments)."""
        with self._store.read_transaction() as conn:
            attempt_rows = conn.execute(
                "SELECT a.id AS id, a.item_id AS item_id, i.family_id AS "
                "family_id, e.occurred_at AS occurred_at, "
                "a.attempt_ordinal AS attempt_ordinal, a.help_level AS "
                "help_level, a.revealed AS revealed, a.independent AS "
                "independent FROM attempts a JOIN items i ON i.user_id = "
                "a.user_id AND i.id = a.item_id JOIN events e ON e.id = "
                "a.response_event_id WHERE a.user_id = ?",
                (user_id,),
            ).fetchall()
            assessment_rows = conn.execute(
                "SELECT id, attempt_id, assessment_revision, payload_json "
                "FROM assessments WHERE attempt_user_id = ?",
                (user_id,),
            ).fetchall()
        return _facts_from_rows(attempt_rows, assessment_rows)

    def topic_state(
        self, user_id: str, topic_id: _uuid.UUID
    ) -> TopicState | None:
        """Estado de tópico projetado (linha ``topic_states``), se houver."""
        with self._store.read_transaction() as conn:
            row = conn.execute(
                "SELECT payload_json FROM topic_states WHERE user_id = ? "
                "AND topic_id = ?",
                (user_id, str(topic_id)),
            ).fetchone()
        if row is None:
            return None
        return TopicState.model_validate_json(row["payload_json"])


def _facts_from_rows(
    attempt_rows: Sequence[Any], assessment_rows: Sequence[Any]
) -> tuple[list[AttemptFact], list[AssessmentFact]]:
    attempts: list[AttemptFact] = []
    for row in attempt_rows:
        occurred = datetime.fromisoformat(str(row["occurred_at"]))
        if occurred.tzinfo is None:  # pragma: no cover — escrita normaliza
            occurred = occurred.replace(tzinfo=timezone.utc)
        attempts.append(
            AttemptFact(
                attempt_id=_uuid.UUID(str(row["id"])),
                item_id=_uuid.UUID(str(row["item_id"])),
                family_id=_uuid.UUID(str(row["family_id"]))
                if row["family_id"] is not None
                else _uuid.UUID(int=0),
                occurred_at=occurred.astimezone(timezone.utc),
                attempt_ordinal=int(row["attempt_ordinal"]),
                help_level=int(row["help_level"]),
                revealed=bool(row["revealed"]),
                independent=bool(row["independent"]),
            )
        )
    assessments: list[AssessmentFact] = []
    for row in assessment_rows:
        try:
            data = json.loads(row["payload_json"])
        except (json.JSONDecodeError, TypeError) as exc:
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                f"payload de assessment ilegível: {exc}",
                diagnostic=_DIAGNOSTIC,
            ) from exc
        payload = data.get("assessment", data)
        assessment = Assessment.model_validate(payload)
        assessments.append(
            AssessmentFact(
                assessment_id=_uuid.UUID(str(row["id"])),
                attempt_id=_uuid.UUID(str(row["attempt_id"])),
                assessment_revision=int(row["assessment_revision"]),
                results=tuple(assessment.criterion_results),
                correctness=assessment.correctness,
                reliability=assessment.reliability,
                critical_criterion_ids=frozenset(
                    data.get("critical_criterion_ids", [])
                ),
            )
        )
    return attempts, assessments


__all__ = [
    "ACTION_ASSESSMENT",
    "ACTION_ATTEMPT",
    "AssessmentCheckResult",
    "AssessmentFact",
    "AssessmentService",
    "AttemptFact",
    "AttemptRecord",
    "EVENT_ASSESSMENT",
    "EVENT_ATTEMPT",
    "MODEL_VERSION",
    "compute_topic_states",
]
