"""Serviço de efeitos (mapa §11, §13.2): commit idempotente com recibo,
consulta autoritativa para replay de checkpoint e dispatcher com lease para
o outbox.

Contratos implementados (task 005):

- **Commit idempotente (§11)**: ``EffectsService.commit`` valida o pedido
  pelo contrato ``Operation`` da task 003 **fora** da transação, abre
  transação curta e **primeiro verifica ``operation_id``**: mesmo
  ID+digest+usuário devolve o recibo anterior mesmo que a
  ``expected_version`` agora seja antiga; digest/usuário diferente para o
  mesmo ID falha. Operação nova confere a revisão esperada e insere
  evento/operação/outbox e atualiza a projeção atomicamente — a garantia
  atômica vive em ``DomainStore.commit_operation`` (transação única,
  ``BEGIN IMMEDIATE``). Nenhuma transação permanece aberta durante LLM/rede
  (§11): a validação Pydantic e a construção dos statements ocorrem antes
  de ``BEGIN``.
- **Replay autoritativo (§11)**: o checkpoint vive em DB separado (task 014)
  e não é atômico; o replay consulta a operação autoritativa
  (``EffectsService.receipt_for``/``DomainStore.get_operation``) e reutiliza
  o recibo. Operação inexistente → ``None`` (replay reapresenta o commit e a
  dedup decide); identidade divergente → ``SCHEMA_INVALID``.
- **Dispatcher com lease (§11)**: ``OutboxDispatcher`` apropria linhas
  ``pending`` (e linhas ``in_flight`` com lease expirado) numa transação
  curta, aplica o efeito **fora** de qualquer transação e confirma com ACK
  em transação própria. Crash antes do commit não promove estado (a
  transação do commit não chegou a ``COMMIT`` — nada persiste); crash após
  o commit recupera a linha pendente em ciclo futuro; crash após o efeito
  antes do ACK reconcilia o destino por identidade (``probe`` pela
  ``operation_id``) antes de reentregar. Efeito desconhecido sem consulta
  possível permanece ``UNKNOWN_EFFECT`` sem retry automático (linha
  terminal ``failed``; código tipado ``ErrorCode.UNKNOWN_EFFECT``, §4).
- **Entrega ao menos uma vez (§11)**: resultado definitivamente "não
  aplicado" volta a ``pending`` e é recuperado por ciclo futuro; não há
  promessa de exactly-once distribuído — a reconciliação por identidade é
  quem evita duplicar efeito reconhecido quando o destino oferece consulta.

Lease/recibo são metadados operacionais (§15.1, linha 247): nenhuma
operação daqui incrementa ``domain_revision`` — o incremento único por
operação nova de domínio acontece dentro do ``commit_operation``.

Defaults de ensaio (não resultados medidos): ``DEFAULT_LEASE_SECONDS`` é
escolha operacional local a calibrar.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Protocol

from pydantic import ValidationError

from eduagent.contracts import ErrorCode, EduAgentError, Operation
from eduagent.storage.repository import DomainStore, OutboxRow, Receipt

#: Referência de diagnóstico local do serviço (mapa §4).
DIAGNOSTIC = "eduagent/services/effects.py"

#: Duração do lease do dispatcher — default de ensaio (escolha operacional
#: local, não resultado medido): deve exceder com folga a latência máxima
#: esperada de um efeito e ser menor que o intervalo entre ciclos de
#: recuperação.
DEFAULT_LEASE_SECONDS = 30

#: Limite de linhas apropriadas por ciclo — default de ensaio.
DEFAULT_BATCH_LIMIT = 16


def _utc_iso(moment: datetime) -> str:
    """ISO-8601 UTC com o mesmo formato de ``repository._utc_now_iso``
    (comparação lexicográfica no ``claim_outbox``)."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Especificações de entrada do commit
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventSpec:
    """Evento a inserir no mesmo commit da operação (mapa §5/§11)."""

    id: str
    kind: str
    occurred_at: str
    recorded_at: str
    payload: Mapping[str, Any] | None = None
    session_id: str | None = None


@dataclass(frozen=True)
class OutboxSpec:
    """Entrada de outbox a inserir no mesmo commit da operação (§11):
    efeito externo pendente entregue pelo dispatcher."""

    id: str
    target: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class CommitRequest:
    """Pedido de commit idempotente (mapa §11).

    ``operation_id``/``user_id`` são UUID canônico, ``digest`` é SHA-256 hex
    do payload canônico da operação e ``expected_version`` é a
    ``domain_revision`` esperada (§15.1). ``projection`` são statements SQL
    de atualização de projeção aplicados na mesma transação; ``event`` e
    ``outbox`` são inserções estruturadas na mesma transação.
    """

    operation_id: str
    user_id: str
    action: str
    digest: str
    expected_version: int
    event: EventSpec | None = None
    outbox: OutboxSpec | None = None
    projection: tuple[tuple[str, tuple[Any, ...]], ...] = ()


# ---------------------------------------------------------------------------
# Serviço de commit idempotente
# ---------------------------------------------------------------------------


class EffectsService:
    """Fachada do commit idempotente e do replay autoritativo (mapa §11)."""

    def __init__(self, store: DomainStore) -> None:
        self._store = store

    # -- validação pelo contrato Operation (task 003, mapa §4) ------------

    def _validate_contract(self, request: CommitRequest) -> Operation:
        """Valida o pedido contra o contrato ``Operation`` **antes** de abrir
        transação (§11: transação curta; validação não segura escritor).
        Estado ``PENDING``: a operação ainda não tem recibo — o acoplamento
        receipt⇔committed do contrato é verificado aqui na forma aplicável
        ao pré-commit; o recibo em si é produzido e armazenado pelo
        ``DomainStore.commit_operation`` (``operations.receipt_json``)."""
        try:
            return Operation(
                operation_id=request.operation_id,
                user_id=request.user_id,
                action=Operation.OperationAction(request.action),
                expected_version=request.expected_version,
                payload_hash=request.digest,
                state=Operation.OperationState.PENDING,
            )
        except (ValidationError, ValueError) as exc:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "pedido de commit viola o contrato Operation (mapa §4): "
                f"{type(exc).__name__} na validação do contrato",
                diagnostic=DIAGNOSTIC,
            ) from exc

    # -- commit ------------------------------------------------------------

    def commit(self, request: CommitRequest) -> Receipt:
        """Commit idempotente (mapa §11).

        1. Validação do contrato (fora da transação).
        2. ``DomainStore.commit_operation``: dedup por ``operation_id``
           **antes** de ``expected_version``; recibo anterior devolvido em
           retry sem novo incremento (mesmo com ``expected_version`` antiga).
        3. Operação nova: evento + projeção + outbox + incremento de revisão
           + registro da operação, atomicamente.
        """
        self._validate_contract(request)
        statements: list[tuple[str, tuple[Any, ...]]] = []
        if request.event is not None:
            statements.append(self._event_statement(request.user_id, request.event))
        statements.extend(request.projection)
        outbox_statement = (
            self._outbox_statement(
                request.user_id, request.operation_id, request.outbox
            )
            if request.outbox is not None
            else None
        )
        return self._store.commit_operation(
            request.user_id,
            request.operation_id,
            request.digest,
            statements,
            expected_version=request.expected_version,
            outbox_statement=outbox_statement,
        )

    @staticmethod
    def _event_statement(
        user_id: str, event: EventSpec
    ) -> tuple[str, tuple[Any, ...]]:
        payload_json = (
            json.dumps(dict(event.payload), sort_keys=True)
            if event.payload is not None
            else None
        )
        return (
            "INSERT INTO events(id, user_id, session_id, kind, payload_json, "
            "occurred_at, recorded_at) VALUES (?,?,?,?,?,?,?)",
            (
                event.id,
                user_id,
                event.session_id,
                event.kind,
                payload_json,
                event.occurred_at,
                event.recorded_at,
            ),
        )

    @staticmethod
    def _outbox_statement(
        user_id: str, operation_id: str, spec: OutboxSpec
    ) -> tuple[str, tuple[Any, ...]]:
        return (
            "INSERT INTO outbox(id, user_id, operation_id, target, "
            "payload_json, state) VALUES (?,?,?,?,?,'pending')",
            (
                spec.id,
                user_id,
                operation_id,
                spec.target,
                json.dumps(dict(spec.payload), sort_keys=True),
            ),
        )

    # -- replay autoritativo ------------------------------------------------

    def receipt_for(
        self, user_id: str, operation_id: str, digest: str
    ) -> Receipt | None:
        """Recibo autoritativo para replay de checkpoint (§11).

        O checkpoint (DB separado, task 014) não é atômico: o replay consulta
        a operação no banco de domínio e reutiliza o recibo; ``None`` permite
        reapresentar o commit (a dedup decide). Identidade divergente falha.
        """
        return self._store.receipt_for(user_id, operation_id, digest)


# ---------------------------------------------------------------------------
# Dispatcher do outbox com lease
# ---------------------------------------------------------------------------


class EffectOutcome(str, Enum):
    """Resultado declarado pelo destino do efeito.

    - ``APPLIED``: efeito confirmado aplicado (identidade verificada).
    - ``NOT_APPLIED``: destino afirma definitivamente que o efeito não
      ocorreu (ex.: recusa local antes de qualquer efeito colateral) —
      seguro reentregar (entrega ao menos uma vez, §11).
    - ``UNKNOWN``: não foi possível confirmar nem negar (ex.: timeout após
      envio) — segue para reconciliação por identidade.
    """

    APPLIED = "applied"
    NOT_APPLIED = "not_applied"
    UNKNOWN = "unknown"


class EffectHandler(Protocol):
    """Destino do efeito (injetável; MVP usa destinos locais textuais).

    Implementações NÃO devem abrir transações no banco de domínio: o
    dispatcher chama ``apply``/``probe`` fora de qualquer transação (§11).
    """

    def apply(
        self, target: str, payload: Mapping[str, Any], operation_id: str
    ) -> EffectOutcome:
        """Aplica o efeito no destino ``target``. ``operation_id`` é a
        identidade do efeito para dedup do destino."""
        ...

    def probe(
        self, target: str, operation_id: str
    ) -> EffectOutcome | None:
        """Consulta o destino pela identidade da operação (§11: "reconcilia
        destino por identidade").

        Retorna ``APPLIED``/``NOT_APPLIED`` quando o destino oferece
        consulta; ``None`` quando NÃO há consulta possível — nesse caso um
        resultado desconhecido permanece ``UNKNOWN_EFFECT`` sem retry
        automático (§11).
        """
        ...


@dataclass
class DispatchReport:
    """Resultado de um ciclo de despacho (observabilidade local, §12)."""

    claimed: int = 0
    acked: int = 0
    requeued: int = 0
    unknown_effect: list[str] = field(default_factory=list)
    errors: list[EduAgentError] = field(default_factory=list)


class OutboxDispatcher:
    """Dispatcher com lease do outbox (mapa §11).

    Ciclo por linha apropriada (efeito sempre fora de transação):

    - Linha **nova** (``pending``): ``apply``; ``APPLIED`` → ACK;
      ``NOT_APPLIED`` → volta a ``pending`` (ciclo futuro recupera — "após
      commit recupera pendente"); ``UNKNOWN`` → tenta ``probe``.
    - Linha **recuperada** (lease expirado de um crash — crash após efeito
      antes do ACK): ``probe`` primeiro, reconciliando por identidade;
      ``APPLIED`` → ACK sem reentrega (sem duplicação de efeito reconhecido);
      ``NOT_APPLIED`` → o efeito não ocorreu, segue para ``apply``.
    - ``UNKNOWN`` sem consulta possível (``probe is None``): terminal
      ``UNKNOWN_EFFECT`` — linha ``failed``, sem retry automático (§11),
      erro tipado ``ErrorCode.UNKNOWN_EFFECT`` no relatório.
    """

    def __init__(
        self,
        store: DomainStore,
        handler: EffectHandler,
        *,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> None:
        self._store = store
        self._handler = handler
        self._lease_seconds = lease_seconds

    def dispatch_pending(
        self,
        *,
        now: datetime | None = None,
        limit: int = DEFAULT_BATCH_LIMIT,
    ) -> DispatchReport:
        """Um ciclo de despacho: apropria com lease, aplica efeitos fora de
        transação e confirma com ACK (§11).

        ``now`` permite injetar o relógio (testes de expiração de lease);
        default é o relógio UTC atual.
        """
        moment = now if now is not None else datetime.now(timezone.utc)
        report = DispatchReport()
        rows = self._store.claim_outbox(
            now=_utc_iso(moment),
            lease_until=_utc_iso(
                moment + timedelta(seconds=self._lease_seconds)
            ),
            limit=limit,
        )
        report.claimed = len(rows)
        for row in rows:
            self._process(row, report)
        return report

    # -- um efeito por linha -------------------------------------------------

    def _process(self, row: OutboxRow, report: DispatchReport) -> None:
        if row.recovered:
            # Crash após efeito antes do ACK (ou antes do efeito, com lease
            # expirado): reconcilia o destino por identidade antes de
            # reentregar (§11).
            probe = self._safe_probe(row, report)
            if probe is EffectOutcome.APPLIED:
                self._store.ack_outbox(row.id)
                report.acked += 1
                return
            if probe is EffectOutcome.UNKNOWN or probe is None:
                self._mark_unknown_effect(row, report)
                return
            # probe NOT_APPLIED: efeito definitivamente não ocorreu —
            # seguro aplicar agora.
        outcome = self._safe_apply(row, report)
        if outcome is EffectOutcome.APPLIED:
            self._store.ack_outbox(row.id)
            report.acked += 1
            return
        if outcome is EffectOutcome.NOT_APPLIED:
            self._store.requeue_outbox(row.id)
            report.requeued += 1
            return
        # outcome UNKNOWN: tenta reconciliar por identidade antes de decidir.
        probe = self._safe_probe(row, report)
        if probe is EffectOutcome.APPLIED:
            self._store.ack_outbox(row.id)
            report.acked += 1
            return
        if probe is EffectOutcome.NOT_APPLIED:
            # Sabe-se que não aplicou: nova tentativa é entrega ao menos uma
            # vez (§11), não retry de desconhecido.
            self._store.requeue_outbox(row.id)
            report.requeued += 1
            return
        self._mark_unknown_effect(row, report)

    def _safe_apply(
        self, row: OutboxRow, report: DispatchReport
    ) -> EffectOutcome:
        try:
            return self._handler.apply(row.target, row.payload, row.operation_id)
        except Exception as exc:  # falha de rede/destino: resultado desconhecido
            report.errors.append(
                EduAgentError(
                    ErrorCode.UNKNOWN_EFFECT,
                    f"apply do outbox {row.id} falhou com {type(exc).__name__}; "
                    "resultado desconhecido — reconciliação por identidade",
                    diagnostic=DIAGNOSTIC,
                )
            )
            return EffectOutcome.UNKNOWN

    def _safe_probe(
        self, row: OutboxRow, report: DispatchReport
    ) -> EffectOutcome | None:
        try:
            return self._handler.probe(row.target, row.operation_id)
        except Exception as exc:  # consulta indisponível = sem consulta possível
            report.errors.append(
                EduAgentError(
                    ErrorCode.UNKNOWN_EFFECT,
                    f"probe do outbox {row.id} falhou com "
                    f"{type(exc).__name__}; sem consulta possível",
                    diagnostic=DIAGNOSTIC,
                )
            )
            return None

    def _mark_unknown_effect(
        self, row: OutboxRow, report: DispatchReport
    ) -> None:
        """Terminal ``UNKNOWN_EFFECT`` (§11): linha ``failed`` — o dispatcher
        nunca apropria ``failed``, logo não há retry automático."""
        self._store.fail_outbox(row.id)
        report.unknown_effect.append(row.id)
        report.errors.append(
            EduAgentError(
                ErrorCode.UNKNOWN_EFFECT,
                f"efeito do outbox {row.id} (operação {row.operation_id}) "
                "permanece UNKNOWN_EFFECT: destino sem consulta possível — "
                "sem retry automático (mapa §11)",
                diagnostic=DIAGNOSTIC,
            )
        )


__all__ = [
    "DEFAULT_BATCH_LIMIT",
    "DEFAULT_LEASE_SECONDS",
    "CommitRequest",
    "DispatchReport",
    "EffectHandler",
    "EffectOutcome",
    "EffectsService",
    "EventSpec",
    "OutboxDispatcher",
    "OutboxSpec",
]
