"""Agente Planejador — atividades e dependências (mapa normativo §15.4;
contratos da task 003, armazenamento da 004, commit idempotente da 005).

A política evidência→demanda v1 (§15.3) vive em
``eduagent/services/scheduling.py`` (task 011); este módulo cobre a parte
de **atividades** do §15.4 que cabe à task 011 (o solver CP-SAT e o
verificador independente são da task 012; preview/confirmação/ICS da 013).

Contratos implementados (task 011, §15.4):

- **``ActivityUpdate(block_id, status, occurred_at, expected_version,
  operation_id)``** com transições ``planned→started→completed`` ou
  ``planned→missed/cancelled``:
  - Complete direto de ``planned`` aceita início/fim **reais informados**
    (campos ``actual_start``/``actual_end`` — extensão necessária para
    "início/fim reais informados"; os cinco campos do mapa continuam
    obrigatórios).
  - Sair de ``completed`` exige **correção explícita** — transição comum é
    recusada com erro tipado; ``correct_activity`` é o caminho explícito.
  - ``missed`` é declaração do aluno (a própria atualização é a declaração)
    ou sugestão de atraso confirmada; o **scheduler não presume falta por
    relógio** — nenhum caminho aqui marca ``missed`` automaticamente.
  - ``started`` bloqueia o intervalo aprovado (``fixed_occupation``):
    blocos iniciados/concluídos entram uma única vez no conjunto de
    ocupação, sem candidatos móveis (§15.4/§9).
  - Sessão além do fim previsto: registrar conflito (``end_conflict``) e
    pedir atualização de término antes de solver, até esclarecimento; o
    término real confirmado em ``completed`` esclarece o conflito.
- **Recibo e replan uma vez por evento**: toda transição passa pelo commit
  idempotente (§11) e retorna recibo; transições que mudam ocupação futura
  retornam ``replan_requested=True`` com ``replan_event_id=operation_id`` —
  o mesmo evento nunca dispara dois replans (dedup por evento a jusante;
  retry devolve o recibo original sem novo evento).
- **Dependência temporal referencia demanda/atividade, não ID de tópico**
  (§15.4): ``declare_dependency`` liga demandas (pré-requisito pedagógico
  de tópico é só informação de recomendação; só vira dependência de
  atividade quando explicitada/confirmada aqui). Ciclo de dependência é
  **erro**, não inviabilidade misteriosa (§9). Estado da dependência:
  predecessor concluído satisfaz presença com término real; iniciado ocupa
  fixo e o dependente espera término confirmado; pendente fora do horizonte
  bloqueia o dependente com razão.
- **Indivisível por default** (§15.4): decomposição só após a demanda pai
  declarar ``splittable`` com número/duração de subtarefas e soma ≥ duração
  original, **confirmados pelo usuário** — sem declaração confirmada, a
  divisão é recusada com erro tipado.

``expected_version`` é a ``domain_revision`` do usuário (§15.1) validada
pelo commit idempotente; ``event_sequence`` do bloco começa em 0 e
incrementa apenas quando campos de evento mudam (§15.5).

Nada aqui presume falta por relógio nem converte sugestão em obrigação.
"""

from __future__ import annotations

import hashlib
import json
import uuid as _uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from eduagent.contracts import (
    EduAgentError,
    ErrorCode,
    Ref,
    StudyDemand,
)
from eduagent.services.effects import CommitRequest, EffectsService, EventSpec
from eduagent.services.scheduling import _DEMAND_NAMESPACE
from eduagent.storage.repository import DomainStore, Receipt

_DIAGNOSTIC = "eduagent/agents/planner.py"

#: Ação de commit idempotente (mapa §4 ``OperationAction.ACTIVITY_UPDATE``).
ACTION_ACTIVITY_UPDATE = "activity.update"

#: Kinds de evento (catálogo default de ensaio).
EVENT_ACTIVITY_UPDATED = "activity_updated"
EVENT_DEPENDENCY_DECLARED = "dependency_declared"
EVENT_DEMAND_SPLIT = "demand_split"

#: Status de atividade (§15.4) — coluna de logical_blocks (migração 0006).
STATUS_PLANNED = "planned"
STATUS_STARTED = "started"
STATUS_COMPLETED = "completed"
STATUS_MISSED = "missed"
STATUS_CANCELLED = "cancelled"

#: Transições ordinárias (§15.4: ``planned→started→completed`` ou
#: ``planned→missed/cancelled``). Sair de ``completed`` é correção
#: explícita, nunca transição ordinária.
ALLOWED_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        (STATUS_PLANNED, STATUS_STARTED),
        (STATUS_PLANNED, STATUS_COMPLETED),
        (STATUS_STARTED, STATUS_COMPLETED),
        (STATUS_PLANNED, STATUS_MISSED),
        (STATUS_PLANNED, STATUS_CANCELLED),
    }
)

#: Transições que mudam ocupação futura → replan uma vez por evento (§15.4).
REPLAN_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        (STATUS_PLANNED, STATUS_STARTED),
        (STATUS_PLANNED, STATUS_COMPLETED),
        (STATUS_STARTED, STATUS_COMPLETED),
        (STATUS_PLANNED, STATUS_MISSED),
        (STATUS_PLANNED, STATUS_CANCELLED),
    }
)


class ActivityStatus(str, Enum):
    """Status de atividade (§15.4)."""

    PLANNED = STATUS_PLANNED
    STARTED = STATUS_STARTED
    COMPLETED = STATUS_COMPLETED
    MISSED = STATUS_MISSED
    CANCELLED = STATUS_CANCELLED


class ActivityUpdate(BaseModel):
    """``ActivityUpdate`` (mapa §15.4). Campos do mapa obrigatórios;
    ``actual_start``/``actual_end`` carregam os instantes reais informados
    (complete direto de planned e término real — §15.4). Modelo estrito:
    campo desconhecido é rejeitado (mesma política do mapa §4)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    block_id: _uuid.UUID
    status: ActivityStatus
    occurred_at: datetime  # com zona (validado no serviço, §4)
    expected_version: int = Field(ge=0)
    operation_id: str
    actual_start: datetime | None = None
    actual_end: datetime | None = None


@dataclass(frozen=True)
class BlockRecord:
    """Bloco lógico projetado com campos de atividade (§15.4/§15.5)."""

    block_id: _uuid.UUID
    uid: str
    status: str
    planned_start_utc: datetime | None
    planned_end_utc: datetime | None
    actual_start_utc: datetime | None
    actual_end_utc: datetime | None
    source_demand_id: _uuid.UUID | None
    event_sequence: int
    end_conflict: bool
    last_replan_event: str | None


@dataclass(frozen=True)
class ActivityResult:
    """Resultado de ``update_activity``/``correct_activity`` (§15.4): recibo
    e replan uma vez por evento."""

    receipt: Receipt
    block: BlockRecord
    #: Transição mudou ocupação futura — replan disparável uma vez por
    #: evento (dedup a jusante por ``replan_event_id``).
    replan_requested: bool
    replan_event_id: str | None
    #: Sessão além do fim previsto — conflito registrado até esclarecimento;
    #: solver (task 012) não usa o bloco enquanto pendente.
    end_conflict: bool
    message: str


@dataclass(frozen=True)
class DependencyState:
    """Semântica de dependência temporal (§15.4) entre demandas."""

    dependent_demand_id: _uuid.UUID
    predecessor_demand_id: _uuid.UUID
    state: str  # satisfied | waits_confirmed_end | blocked_outside_horizon | ready
    reason: str


def _aware(moment: datetime, field_name: str) -> datetime:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            f"{field_name} exige zona (UTC/offset) — datetime ingênuo é "
            "rejeitado (mapa §4)",
            diagnostic=_DIAGNOSTIC,
        )
    return moment.astimezone(timezone.utc)


def _digest(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _intent_digest(update: "ActivityUpdate", *, correction: bool) -> str:
    """Digest de intenção da atualização (§11): estável entre retries —
    independe do estado vigente do bloco, então o mesmo ``operation_id``
    recomputa o mesmo digest e devolve o recibo original."""
    return _digest(
        {
            "block_id": str(update.block_id),
            "status": update.status.value,
            "occurred_at": _aware(update.occurred_at, "occurred_at")
            .isoformat(),
            "actual_start": (
                _aware(update.actual_start, "actual_start").isoformat()
                if update.actual_start is not None
                else None
            ),
            "actual_end": (
                _aware(update.actual_end, "actual_end").isoformat()
                if update.actual_end is not None
                else None
            ),
            "correction": correction,
        }
    )


def _parse_utc_text(text: str | None) -> datetime | None:
    if text is None:
        return None
    value = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


class PlannerAgent:
    """Atividades e dependências do Planejador (mapa §9/§15.4)."""

    def __init__(
        self,
        store: DomainStore,
        effects: EffectsService,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._effects = effects
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    # -- registro de bloco (MVP; preview/confirmação do plano é a 013) -------

    def register_block(
        self,
        user_id: str,
        *,
        planned_start_utc: datetime,
        planned_end_utc: datetime,
        block_id: _uuid.UUID | str | None = None,
        uid: _uuid.UUID | str | None = None,
        source_demand_id: _uuid.UUID | str | None = None,
    ) -> BlockRecord:
        """Cria o bloco lógico no status ``planned`` (§15.5: identidade de
        ocorrência persistida; UID estável).

        Caminho de MVP para testes e para o fluxo da task 012/013: a criação
        por preview/confirmation de plano chega na 013 — nada aqui aprova
        plano nem gera ICS.
        """
        start = _aware(planned_start_utc, "planned_start_utc")
        end = _aware(planned_end_utc, "planned_end_utc")
        if start >= end:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "bloco exige planned_start_utc < planned_end_utc",
                diagnostic=_DIAGNOSTIC,
            )
        block_key = str(_uuid.UUID(str(block_id))) if block_id else str(
            _uuid.uuid4()
        )
        uid_key = str(_uuid.UUID(str(uid))) if uid else str(_uuid.uuid4())
        demand_key = (
            str(_uuid.UUID(str(source_demand_id)))
            if source_demand_id
            else None
        )
        with self._store.write_transaction(user_id) as tx:
            tx.execute(
                "INSERT INTO logical_blocks(id, user_id, uid, status, "
                "planned_start_utc, planned_end_utc, source_demand_id) "
                "VALUES (?,?,?,'planned',?,?,?)",
                (
                    block_key,
                    user_id,
                    uid_key,
                    start.isoformat(),
                    end.isoformat(),
                    demand_key,
                ),
            )
        record = self.get_block(user_id, block_key)
        assert record is not None
        return record

    # -- transições de atividade (§15.4) ---------------------------------------

    def _load_block(self, user_id: str, block_id: str) -> tuple[Any, BlockRecord]:
        rows = self._store.fetch_user_rows(
            "SELECT id, user_id, uid, status, planned_start_utc, "
            "planned_end_utc, actual_start_utc, actual_end_utc, "
            "source_demand_id, event_sequence, end_conflict, "
            "last_replan_event FROM logical_blocks WHERE user_id = ? AND "
            "id = ?",
            (user_id, block_id),
        )
        if not rows:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"bloco {block_id} não resolve para o usuário",
                diagnostic=_DIAGNOSTIC,
            )
        return rows[0], self._record_from_row(rows[0])

    def _record_from_row(self, row: Any) -> BlockRecord:
        return BlockRecord(
            block_id=_uuid.UUID(str(row["id"])),
            uid=str(row["uid"]),
            status=str(row["status"]),
            planned_start_utc=_parse_utc_text(row["planned_start_utc"]),
            planned_end_utc=_parse_utc_text(row["planned_end_utc"]),
            actual_start_utc=_parse_utc_text(row["actual_start_utc"]),
            actual_end_utc=_parse_utc_text(row["actual_end_utc"]),
            source_demand_id=(
                _uuid.UUID(str(row["source_demand_id"]))
                if row["source_demand_id"]
                else None
            ),
            event_sequence=int(row["event_sequence"]),
            end_conflict=bool(row["end_conflict"]),
            last_replan_event=row["last_replan_event"],
        )

    def get_block(
        self, user_id: str, block_id: _uuid.UUID | str
    ) -> BlockRecord | None:
        try:
            _, record = self._load_block(
                user_id, str(_uuid.UUID(str(block_id)))
            )
        except EduAgentError as exc:
            if exc.code is ErrorCode.SOURCE_UNRESOLVED:
                return None
            raise
        return record

    def update_activity(
        self, user_id: str, update: ActivityUpdate
    ) -> ActivityResult:
        """Transição ordinária de atividade (§15.4).

        Regras: transições válidas apenas no conjunto
        ``planned→started→completed`` / ``planned→missed→cancelled``;
        sair de ``completed`` é recusa tipada (correção explícita é caminho
        separado); complete direto de ``planned`` exige início/fim reais
        informados; ``started`` além do fim previsto registra conflito de
        término; scheduler nunca presume falta por relógio.

        §11: o mesmo ``operation_id``+digest devolve o recibo original
        ANTES de qualquer validação de transição (retry não gera novas).
        """
        occurred = _aware(update.occurred_at, "occurred_at")
        operation_key = update.operation_id
        if not operation_key:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "operation_id é obrigatório (§15.4/§11)",
                diagnostic=_DIAGNOSTIC,
            )
        digest = _intent_digest(update, correction=False)
        if operation_key:
            receipt = self._effects.receipt_for(user_id, operation_key, digest)
            if receipt is not None:
                _, current = self._load_block(
                    user_id, str(_uuid.UUID(str(update.block_id)))
                )
                return self._retry_result(receipt, current, operation_key)
        _, current = self._load_block(
            user_id, str(_uuid.UUID(str(update.block_id)))
        )
        target = update.status.value
        if current.status == STATUS_COMPLETED:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "bloco completed: sair de completed exige correção "
                "explícita (§15.4), não transição ordinária — use "
                "correct_activity",
                diagnostic=_DIAGNOSTIC,
            )
        transition = (current.status, target)
        if transition not in ALLOWED_TRANSITIONS:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"transição {current.status}→{target} fora do conjunto "
                "planned→started→completed / planned→missed/cancelled (§15.4)",
                diagnostic=_DIAGNOSTIC,
            )
        return self._apply_transition(
            user_id,
            update,
            current,
            occurred,
            correction=False,
            digest=digest,
        )

    def correct_activity(
        self, user_id: str, update: ActivityUpdate
    ) -> ActivityResult:
        """Correção explícita (§15.4: "sair de completed exige correção
        explícita, não transição ordinária"). Único caminho que altera um
        bloco ``completed``; a correção é registrada no evento e o bloco
        volta ao status alvo informado. Retry do mesmo ``operation_id``
        devolve o recibo original (§11)."""
        occurred = _aware(update.occurred_at, "occurred_at")
        digest = _intent_digest(update, correction=True)
        if update.operation_id:
            receipt = self._effects.receipt_for(
                user_id, update.operation_id, digest
            )
            if receipt is not None:
                _, current = self._load_block(
                    user_id, str(_uuid.UUID(str(update.block_id)))
                )
                return self._retry_result(receipt, current, update.operation_id)
        _, current = self._load_block(
            user_id, str(_uuid.UUID(str(update.block_id)))
        )
        if current.status != STATUS_COMPLETED:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "correct_activity aplica-se apenas a blocos completed; "
                "transições ordinárias usam update_activity (§15.4)",
                diagnostic=_DIAGNOSTIC,
            )
        return self._apply_transition(
            user_id,
            update,
            current,
            occurred,
            correction=True,
            digest=digest,
        )

    def _retry_result(
        self, receipt: Receipt, current: BlockRecord, operation_id: str
    ) -> ActivityResult:
        """Resultado de retry (§11): recibo original e estado vigente —
        o replan do evento já foi disparado uma única vez no commit."""
        return ActivityResult(
            receipt=receipt,
            block=current,
            replan_requested=current.last_replan_event == operation_id,
            replan_event_id=current.last_replan_event,
            end_conflict=current.end_conflict,
            message="retry: recibo original devolvido (§11)",
        )

    def _apply_transition(
        self,
        user_id: str,
        update: ActivityUpdate,
        current: BlockRecord,
        occurred: datetime,
        *,
        correction: bool,
        digest: str | None = None,
    ) -> ActivityResult:
        target = update.status.value
        actual_start = (
            _aware(update.actual_start, "actual_start")
            if update.actual_start is not None
            else current.actual_start_utc
        )
        actual_end = (
            _aware(update.actual_end, "actual_end")
            if update.actual_end is not None
            else current.actual_end_utc
        )
        planned_end = current.planned_end_utc
        end_conflict = current.end_conflict
        message = ""

        if target == STATUS_STARTED:
            # Início real = occurred_at (ou informado). Sessão iniciada
            # além do fim previsto: conflito registrado até esclarecimento
            # (§15.4) — o scheduler não presume nada por relógio.
            actual_start = actual_start or occurred
            if planned_end is not None and actual_start > planned_end:
                end_conflict = True
                message = (
                    "sessão iniciada além do fim previsto: informe a "
                    "atualização de término antes de resolver (§15.4)"
                )
        elif target == STATUS_COMPLETED:
            if current.status == STATUS_PLANNED and not correction:
                # Complete direto de planned: exige início/fim reais
                # informados (§15.4).
                if update.actual_start is None or update.actual_end is None:
                    raise EduAgentError(
                        ErrorCode.SCHEMA_INVALID,
                        "complete direto de planned exige início/fim reais "
                        "informados (§15.4)",
                        diagnostic=_DIAGNOSTIC,
                    )
            actual_start = actual_start or occurred
            actual_end = actual_end or occurred
            if actual_start > actual_end:
                raise EduAgentError(
                    ErrorCode.SCHEMA_INVALID,
                    "início real posterior ao fim real",
                    diagnostic=_DIAGNOSTIC,
                )
            if (
                planned_end is not None
                and actual_end > planned_end
                and current.status == STATUS_STARTED
                and end_conflict
            ):
                # Término real informado esclarece o conflito (§15.4).
                end_conflict = False
                message = "término real registrado: conflito esclarecido"
            elif planned_end is not None and actual_end > planned_end:
                message = (
                    "sessão terminou além do fim previsto: término real "
                    "prevalece no conjunto de ocupação (§15.4)"
                )
        # missed/cancelled: declaração explícita — nada inferido por relógio.

        payload = {
            "block_id": str(current.block_id),
            "from_status": current.status,
            "to_status": target,
            "occurred_at": occurred.isoformat(),
            "actual_start": (
                actual_start.isoformat() if actual_start else None
            ),
            "actual_end": actual_end.isoformat() if actual_end else None,
            "end_conflict": end_conflict,
            "correction": correction,
        }
        if digest is None:  # pragma: no cover — chamadores passam o digest
            digest = _digest(payload)
        statements: tuple[tuple[str, tuple[Any, ...]], ...] = (
            (
                "UPDATE logical_blocks SET status = ?, actual_start_utc = ?, "
                "actual_end_utc = ?, end_conflict = ?, event_sequence = "
                "event_sequence + 1, last_replan_event = ? "
                "WHERE id = ? AND user_id = ?",
                (
                    target,
                    actual_start.isoformat() if actual_start else None,
                    actual_end.isoformat() if actual_end else None,
                    int(end_conflict),
                    update.operation_id,
                    str(current.block_id),
                    user_id,
                ),
            ),
        )
        request = CommitRequest(
            operation_id=update.operation_id,
            user_id=user_id,
            action=ACTION_ACTIVITY_UPDATE,
            digest=digest,
            expected_version=update.expected_version,
            event=EventSpec(
                id=str(_uuid.uuid4()),
                kind=EVENT_ACTIVITY_UPDATED,
                occurred_at=occurred.isoformat(),
                recorded_at=self._clock()
                .astimezone(timezone.utc)
                .isoformat(),
                payload=payload,
            ),
            projection=statements,
        )
        receipt = self._effects.commit(request)
        _, updated = self._load_block(user_id, str(current.block_id))
        replan = (
            not correction and (current.status, target) in REPLAN_TRANSITIONS
        ) or correction
        return ActivityResult(
            receipt=receipt,
            block=updated,
            replan_requested=replan,
            replan_event_id=(
                update.operation_id if replan else updated.last_replan_event
            ),
            end_conflict=updated.end_conflict,
            message=message,
        )

    # -- ocupação fixa (§15.4/§9) ----------------------------------------------

    def fixed_occupation(
        self, user_id: str
    ) -> list[tuple[_uuid.UUID, datetime, datetime]]:
        """Intervalos fixos de ocupação (§15.4: "Started bloqueia intervalo
        aprovado"; §9: "Compromissos, blocos iniciados e concluídos são
        fixos"). Cada bloco entra **uma única vez**; started ocupa
        [início real, fim planejado] até término confirmado; completed
        ocupa [início real, fim real]. Blocos com conflito de término
        pendente continuam ocupando o intervalo aprovado (nada é presumido).
        ``planned``/``missed``/``cancelled`` não ocupam."""
        rows = self._store.fetch_user_rows(
            "SELECT id, status, planned_start_utc, planned_end_utc, "
            "actual_start_utc, actual_end_utc, end_conflict FROM "
            "logical_blocks WHERE user_id = ? AND status IN "
            "('started','completed') ORDER BY id",
            (user_id,),
        )
        occupation: list[tuple[_uuid.UUID, datetime, datetime]] = []
        seen: set[str] = set()
        for row in rows:
            key = str(row["id"])
            if key in seen:  # fixos inseridos uma vez (§15.4)
                continue
            seen.add(key)
            start = _parse_utc_text(row["actual_start_utc"]) or _parse_utc_text(
                row["planned_start_utc"]
            )
            if row["status"] == STATUS_COMPLETED:
                end = _parse_utc_text(row["actual_end_utc"]) or _parse_utc_text(
                    row["planned_end_utc"]
                )
            else:
                # started: intervalo aprovado bloqueado até esclarecimento.
                end = _parse_utc_text(row["planned_end_utc"])
            if start is None or end is None:  # pragma: no cover — DDL exige
                continue
            occupation.append((_uuid.UUID(key), start, end))
        return occupation

    # -- dependências temporais (§15.4) ----------------------------------------

    def declare_dependency(
        self,
        user_id: str,
        *,
        dependent_demand_id: _uuid.UUID | str,
        predecessor_demand_id: _uuid.UUID | str,
        operation_id: str | None = None,
    ) -> Receipt:
        """Declara dependência temporal entre demandas (§15.4: a dependência
        referencia demanda/atividade, NÃO ID de tópico). Pré-requisito
        pedagógico de tópico é informação de recomendação — só vira
        dependência aqui quando explicitada/confirmada. Ciclo é erro
        tipado (§9)."""
        dependent = str(_uuid.UUID(str(dependent_demand_id)))
        predecessor = str(_uuid.UUID(str(predecessor_demand_id)))
        if dependent == predecessor:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "dependência circular: demanda não depende de si (§9)",
                diagnostic=_DIAGNOSTIC,
            )
        dep_record = self._demand_row(user_id, dependent)
        pred_record = self._demand_row(user_id, predecessor)
        # Digest de intenção (estável entre retries): o mesmo
        # operation_id devolve o recibo original antes de qualquer
        # revalidação (§11).
        digest = _digest(
            {
                "action": "declare_dependency",
                "dependent": dependent,
                "predecessor": predecessor,
            }
        )
        if operation_id is not None:
            receipt = self._effects.receipt_for(user_id, operation_id, digest)
            if receipt is not None:
                return receipt
        dependencies = self._demand_dependencies(user_id, dep_record)
        if any(ref.id == _uuid.UUID(predecessor) for ref in dependencies):
            # Idempotência declarativa: dependência já registrada é no-op
            # com evento? Não — registrar de novo criaria duplicata na
            # lista; recusa tipada mantém o estado intacto.
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "dependência já declarada para a demanda dependente",
                diagnostic=_DIAGNOSTIC,
            )
        # Ciclo: existe caminho predecessor → ... → dependente?
        if self._reaches(user_id, predecessor, dependent):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "dependência cíclica é erro, não inviabilidade misteriosa "
                "(§9): o predecessor já depende (transitivamente) da "
                "demanda dependente",
                diagnostic=_DIAGNOSTIC,
            )
        new_refs = [
            *dependencies,
            Ref(kind="demand", id=_uuid.UUID(predecessor), version=1),
        ]
        payload = json.loads(dep_record["payload_json"])
        demand = StudyDemand.model_validate(payload["demand"])
        updated = demand.model_copy(update={"dependencies": new_refs})
        payload["demand"] = updated.model_dump(mode="json")
        request = CommitRequest(
            operation_id=operation_id or str(_uuid.uuid4()),
            user_id=user_id,
            action="demand.upsert",
            digest=digest,
            expected_version=self._store.domain_revision(user_id),
            event=EventSpec(
                id=str(_uuid.uuid4()),
                kind=EVENT_DEPENDENCY_DECLARED,
                occurred_at=self._clock()
                .astimezone(timezone.utc)
                .isoformat(),
                recorded_at=self._clock()
                .astimezone(timezone.utc)
                .isoformat(),
                payload={
                    "dependent_demand_id": dependent,
                    "predecessor_demand_id": predecessor,
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
                        dependent,
                        user_id,
                    ),
                ),
            ),
        )
        return self._effects.commit(request)

    def dependency_state(
        self,
        user_id: str,
        *,
        dependent_demand_id: _uuid.UUID | str,
        predecessor_demand_id: _uuid.UUID | str,
        horizon_end_utc: datetime,
    ) -> DependencyState:
        """Semântica de dependência (§15.4):
        - predecessor concluído → presença satisfeita com término real;
        - predecessor iniciado → ocupa fixo, dependente espera término
          confirmado;
        - predecessor pendente com bloco planejado além do horizonte →
          bloqueia o dependente com razão;
        - caso contrário → pronto para o solver avaliar.
        """
        dependent = str(_uuid.UUID(str(dependent_demand_id)))
        predecessor = str(_uuid.UUID(str(predecessor_demand_id)))
        horizon_end = _aware(horizon_end_utc, "horizon_end_utc")
        block = self._block_for_demand(user_id, predecessor)
        if block is not None:
            if block.status == STATUS_COMPLETED and block.actual_end_utc:
                return DependencyState(
                    dependent_demand_id=_uuid.UUID(dependent),
                    predecessor_demand_id=_uuid.UUID(predecessor),
                    state="satisfied",
                    reason="predecessor concluído com término real",
                )
            if block.status == STATUS_STARTED:
                return DependencyState(
                    dependent_demand_id=_uuid.UUID(dependent),
                    predecessor_demand_id=_uuid.UUID(predecessor),
                    state="waits_confirmed_end",
                    reason=(
                        "predecessor iniciado ocupa fixo; dependente "
                        "espera término confirmado (§15.4)"
                    ),
                )
            if (
                block.status == STATUS_PLANNED
                and block.planned_start_utc is not None
                and block.planned_start_utc > horizon_end
            ):
                return DependencyState(
                    dependent_demand_id=_uuid.UUID(dependent),
                    predecessor_demand_id=_uuid.UUID(predecessor),
                    state="blocked_outside_horizon",
                    reason=(
                        "predecessor pendente fora do horizonte bloqueia "
                        "o dependente (§15.4)"
                    ),
                )
        else:
            demand_row = self._demand_row(user_id, predecessor)
            payload = json.loads(demand_row["payload_json"])
            deadline = payload["demand"].get("deadline")
            if isinstance(deadline, str) and "T" not in deadline:
                due = date.fromisoformat(deadline)
                if due > horizon_end.date():
                    return DependencyState(
                        dependent_demand_id=_uuid.UUID(dependent),
                        predecessor_demand_id=_uuid.UUID(predecessor),
                        state="blocked_outside_horizon",
                        reason=(
                            "predecessor pendente com prazo além do "
                            "horizonte bloqueia o dependente (§15.4)"
                        ),
                    )
        return DependencyState(
            dependent_demand_id=_uuid.UUID(dependent),
            predecessor_demand_id=_uuid.UUID(predecessor),
            state="ready",
            reason="predecessor dentro do horizonte",
        )

    # -- decomposição (§15.4) ---------------------------------------------------

    def declare_splittable(
        self,
        user_id: str,
        demand_id: _uuid.UUID | str,
        *,
        subtask_count: int,
        subtask_minutes: int,
        confirmed_by_user: bool,
        operation_id: str | None = None,
    ) -> Receipt:
        """Declara a demanda pai como divisível (§15.4: decomposição só
        após a demanda pai declarar ``splittable``, número/duração de
        subtarefas e soma ≥ duração original, **confirmados pelo
        usuário**). Sem confirmação explícita: recusa tipada."""
        key = str(_uuid.UUID(str(demand_id)))
        row = self._demand_row(user_id, key)
        payload = json.loads(row["payload_json"])
        demand = StudyDemand.model_validate(payload["demand"])
        if not confirmed_by_user:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "decomposição exige confirmação explícita do usuário (§15.4)",
                diagnostic=_DIAGNOSTIC,
            )
        if subtask_count < 1 or subtask_minutes <= 0:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "número e duração de subtarefas devem ser positivos",
                diagnostic=_DIAGNOSTIC,
            )
        if subtask_count * subtask_minutes < demand.duration_minutes:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"soma das subtarefas ({subtask_count * subtask_minutes}min) "
                f"é menor que a duração original ({demand.duration_minutes}min) "
                "(§15.4: soma ≥ duração original)",
                diagnostic=_DIAGNOSTIC,
            )
        payload["splittable_declaration"] = {
            "subtask_count": subtask_count,
            "subtask_minutes": subtask_minutes,
            "confirmed_by_user": True,
        }
        # Digest de intenção — estável entre retries (§11).
        digest = _digest(
            {
                "action": "declare_splittable",
                "demand_id": key,
                "subtask_count": subtask_count,
                "subtask_minutes": subtask_minutes,
            }
        )
        request = CommitRequest(
            operation_id=operation_id or str(_uuid.uuid4()),
            user_id=user_id,
            action="demand.upsert",
            digest=digest,
            expected_version=self._store.domain_revision(user_id),
            event=EventSpec(
                id=str(_uuid.uuid4()),
                kind=EVENT_DEMAND_SPLIT,
                occurred_at=self._clock()
                .astimezone(timezone.utc)
                .isoformat(),
                recorded_at=self._clock()
                .astimezone(timezone.utc)
                .isoformat(),
                payload={
                    "demand_id": key,
                    "subtask_count": subtask_count,
                    "subtask_minutes": subtask_minutes,
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
        return self._effects.commit(request)

    def split_demand(
        self,
        user_id: str,
        demand_id: _uuid.UUID | str,
        *,
        operation_id: str | None = None,
    ) -> list[_uuid.UUID]:
        """Cria as subtarefas da demanda pai divisível (§15.4). Exige
        declaração ``splittable`` confirmada (``declare_splittable``);
        sem ela, recusa tipada — tarefa é indivisível por default."""
        key = str(_uuid.UUID(str(demand_id)))
        row = self._demand_row(user_id, key)
        payload = json.loads(row["payload_json"])
        declaration = payload.get("splittable_declaration")
        if not declaration or not declaration.get("confirmed_by_user"):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "decomposição sem declaração splittable confirmada é "
                "recusada: tarefa é indivisível por default (§15.4)",
                diagnostic=_DIAGNOSTIC,
            )
        demand = StudyDemand.model_validate(payload["demand"])
        count = int(declaration["subtask_count"])
        minutes = int(declaration["subtask_minutes"])
        subtask_ids: list[_uuid.UUID] = []
        statements: list[tuple[str, tuple[Any, ...]]] = []
        for index in range(count):
            # ID determinístico por (pai, índice): o retry da mesma
            # operação recomputa os mesmos IDs e o mesmo digest (§11).
            subtask_id = _uuid.uuid5(
                _DEMAND_NAMESPACE, f"split|{key}|{index}"
            )
            subtask_ids.append(subtask_id)
            subtask = StudyDemand(
                demand_id=subtask_id,
                topic_ids=list(demand.topic_ids),
                kind=demand.kind,
                duration_minutes=minutes,
                earliest=demand.earliest,
                deadline=demand.deadline,
                mandatory=False,  # obrigatoriedade é da pai confirmada
                dependencies=[
                    Ref(kind="demand", id=demand.demand_id, version=1)
                ],
                priority_class=demand.priority_class,
                evidence_ids=list(demand.evidence_ids),
                duration_status=demand.duration_status,
            )
            sub_payload = {
                "demand": subtask.model_dump(mode="json"),
                "policy_version": payload.get(
                    "policy_version", "assessment_review_policy_v1"
                ),
                "origin": "split",
                "parent_demand_id": key,
                "subtask_index": index,
                "subtask_count": count,
            }
            statements.append(
                (
                    "INSERT INTO demands(id, user_id, payload_json, status, "
                    "revision, topic_id, activity_kind, due_local_date, "
                    "policy_version) VALUES (?,?,?,'split',0,?,?,?,?)",
                    (
                        str(subtask_id),
                        user_id,
                        json.dumps(
                            sub_payload, sort_keys=True, ensure_ascii=False
                        ),
                        str(demand.topic_ids[0]),
                        demand.kind.value,
                        str(row["due_local_date"]),
                        payload.get("policy_version", ""),
                    ),
                )
            )
        digest = _digest(
            {"action": "split_demand", "parent": key, "count": count}
        )
        request = CommitRequest(
            operation_id=operation_id or str(_uuid.uuid4()),
            user_id=user_id,
            action="demand.upsert",
            digest=digest,
            expected_version=self._store.domain_revision(user_id),
            event=EventSpec(
                id=str(_uuid.uuid4()),
                kind=EVENT_DEMAND_SPLIT,
                occurred_at=self._clock()
                .astimezone(timezone.utc)
                .isoformat(),
                recorded_at=self._clock()
                .astimezone(timezone.utc)
                .isoformat(),
                payload={
                    "demand_id": key,
                    "subtask_ids": [str(s) for s in subtask_ids],
                },
            ),
            projection=tuple(statements),
        )
        self._effects.commit(request)
        return subtask_ids

    # -- auxiliares --------------------------------------------------------------

    def _demand_row(self, user_id: str, demand_id: str) -> Any:
        rows = self._store.fetch_user_rows(
            "SELECT id, user_id, payload_json, status, topic_id, "
            "activity_kind, due_local_date, policy_version FROM demands "
            "WHERE user_id = ? AND id = ?",
            (user_id, demand_id),
        )
        if not rows:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"demanda {demand_id} não resolve para o usuário",
                diagnostic=_DIAGNOSTIC,
            )
        return rows[0]

    def _demand_dependencies(self, user_id: str, row: Any) -> list[Ref]:
        payload = json.loads(row["payload_json"])
        demand = StudyDemand.model_validate(payload["demand"])
        return list(demand.dependencies)

    def _reaches(
        self, user_id: str, source: str, target: str
    ) -> bool:
        """Existe caminho de dependência source → ... → target?"""
        seen: set[str] = set()
        stack = [source]
        while stack:
            current = stack.pop()
            if current == target:
                return True
            if current in seen:
                continue
            seen.add(current)
            row = self._demand_row(user_id, current)
            for ref in self._demand_dependencies(user_id, row):
                stack.append(str(ref.id))
        return False

    def _block_for_demand(
        self, user_id: str, demand_id: str
    ) -> BlockRecord | None:
        rows = self._store.fetch_user_rows(
            "SELECT id, user_id, uid, status, planned_start_utc, "
            "planned_end_utc, actual_start_utc, actual_end_utc, "
            "source_demand_id, event_sequence, end_conflict, "
            "last_replan_event FROM logical_blocks WHERE user_id = ? AND "
            "source_demand_id = ? ORDER BY rowid LIMIT 1",
            (user_id, demand_id),
        )
        if not rows:
            return None
        return self._record_from_row(rows[0])


__all__ = [
    "ACTION_ACTIVITY_UPDATE",
    "ActivityResult",
    "ActivityStatus",
    "ActivityUpdate",
    "ALLOWED_TRANSITIONS",
    "BlockRecord",
    "DependencyState",
    "PlannerAgent",
]
