"""Testes de aceite da task 005 — commit idempotente, recibo, dispatcher com
lease e recuperação de crash/replay (mapa §11, §13.2; §15.1 lease/recibo não
incrementam ``domain_revision``).

Não é a suíte quantitativa da etapa 8 (mapa de testes): são testes locais de
curta duração que verificam os critérios C1–C3 da task. C4 (mapa intocado,
commits separados, submodule intocado) é verificado por inspeção de git e
registrado no task.md.

Os cenários de crash (C2) executam ``tests/_task005_crash_runner.py`` como
subprocesso e matam o processo com ``os._exit`` em pontos definidos —
pré-commit, pós-commit e pós-efeito sem ACK — sem rollback, sem ``finally``.
"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from eduagent.contracts import EduAgentError, ErrorCode
from eduagent.services.effects import (
    CommitRequest,
    DispatchReport,
    EffectOutcome,
    EffectsService,
    EventSpec,
    OutboxDispatcher,
    OutboxSpec,
)
from eduagent.storage.repository import DomainStore

ROOT = Path(__file__).resolve().parents[1]

UID = "123e4567-e89b-12d3-a456-426614174000"
UID2 = "223e4567-e89b-12d3-a456-426614174000"
DIGEST = "ab" * 32
DIGEST2 = "cd" * 32
T0 = datetime(2026, 10, 21, 12, 0, 0, tzinfo=timezone.utc)
T0_ISO = "2026-10-21T12:00:00Z"
T_PLUS_30 = "2026-10-21T12:00:30Z"
T_PLUS_120 = "2026-10-21T12:02:00Z"

OP = str(uuid.uuid4())
OUTBOX = str(uuid.uuid4())
EVENT = str(uuid.uuid4())
FACT = str(uuid.uuid4())


def _store(tmp_path: Path, name: str = "domain.sqlite") -> DomainStore:
    return DomainStore.open(tmp_path / name)


def _request(
    *,
    operation_id: str = OP,
    user_id: str = UID,
    digest: str = DIGEST,
    expected_version: int = 0,
    action: str = "fact.upsert",
    with_event: bool = True,
    with_outbox: bool = True,
    fact_id: str = FACT,
) -> CommitRequest:
    """Pedido de commit de referência: evento + fato (projeção) + outbox."""
    return CommitRequest(
        operation_id=operation_id,
        user_id=user_id,
        action=action,
        digest=digest,
        expected_version=expected_version,
        event=EventSpec(
            id=EVENT,
            kind="reading",
            occurred_at=T0_ISO,
            recorded_at=T0_ISO,
            payload={"origin": "task005"},
        )
        if with_event
        else None,
        outbox=OutboxSpec(
            id=OUTBOX,
            target="sidecar",
            payload={"operation_id": operation_id},
        )
        if with_outbox
        else None,
        projection=(
            (
                "INSERT INTO facts(id, user_id, kind, value_json, authority, "
                "recorded_at, status) VALUES (?,?,?,?,?,?,?)",
                (fact_id, user_id, "note", "{}", "user", T0_ISO, "confirmed"),
            ),
        ),
    )


def _counts(store: DomainStore, table: str, user_id: str = UID) -> int:
    row = store._conn.execute(
        f"SELECT COUNT(*) AS n FROM {table} WHERE user_id = ?", (user_id,)
    ).fetchone()
    return int(row["n"])


class RecordingHandler:
    """Destino de efeito gravável para testes de dispatcher."""

    def __init__(
        self,
        *,
        apply_outcome: EffectOutcome = EffectOutcome.APPLIED,
        probe_outcome: EffectOutcome | None = EffectOutcome.APPLIED,
        apply_raises: Exception | None = None,
        probe_raises: Exception | None = None,
    ) -> None:
        self.applied: list[str] = []
        self.probed: list[str] = []
        self._apply_outcome = apply_outcome
        self._probe_outcome = probe_outcome
        self._apply_raises = apply_raises
        self._probe_raises = probe_raises

    def apply(
        self, target: str, payload: object, operation_id: str
    ) -> EffectOutcome:
        self.applied.append(operation_id)
        if self._apply_raises is not None:
            raise self._apply_raises
        return self._apply_outcome

    def probe(self, target: str, operation_id: str) -> EffectOutcome | None:
        self.probed.append(operation_id)
        if self._probe_raises is not None:
            raise self._probe_raises
        return self._probe_outcome


def _dispatch(
    store: DomainStore,
    handler: RecordingHandler,
    *,
    now: datetime = T0,
) -> DispatchReport:
    return OutboxDispatcher(store, handler).dispatch_pending(now=now)


# ---------------------------------------------------------------------------
# C1 — Semântica exata do §11 no commit idempotente
# ---------------------------------------------------------------------------


class TestC1CommitIdempotente:
    def test_commit_applies_event_outbox_projection_atomically(
        self, tmp_path: Path
    ) -> None:
        store = _store(tmp_path)
        store.ensure_user(UID)
        service = EffectsService(store)
        receipt = service.commit(_request())
        assert receipt.operation_id == OP
        assert receipt.domain_revision == 1
        assert receipt.was_retry is False
        # evento + projeção + outbox + operação, todos visíveis pós-commit:
        assert _counts(store, "events") == 1
        assert _counts(store, "facts") == 1
        assert _counts(store, "outbox") == 1
        assert _counts(store, "operations") == 1
        outbox = store.outbox_row(OUTBOX)
        assert outbox is not None
        assert outbox["state"] == "pending"  # efeito externo pendente (§11)
        assert json.loads(outbox["payload_json"]) == {"operation_id": OP}
        assert store.domain_revision(UID) == 1  # incremento único (§15.1)

    def test_retry_returns_previous_receipt_even_with_stale_version(
        self, tmp_path: Path
    ) -> None:
        """§11: mesmo ID+digest+usuário devolve o recibo anterior MESMO que a
        ``expected_version`` agora seja antiga — dedup vem antes da versão."""
        store = _store(tmp_path)
        store.ensure_user(UID)
        service = EffectsService(store)
        first = service.commit(_request())
        assert store.domain_revision(UID) == 1
        # replay com expected_version=0, já ultrapassada pela revisão 1:
        retry = service.commit(_request(expected_version=0))
        assert retry.operation_id == first.operation_id
        assert retry.domain_revision == first.domain_revision == 1
        assert retry.applied_at == first.applied_at  # recibo estável
        assert retry.was_retry is True
        assert store.domain_revision(UID) == 1  # retry não incrementa (§15.1)
        # sem duplicação de evento/fato/outbox/operação:
        assert _counts(store, "events") == 1
        assert _counts(store, "facts") == 1
        assert _counts(store, "outbox") == 1
        assert _counts(store, "operations") == 1

    def test_same_id_different_digest_fails(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store.ensure_user(UID)
        service = EffectsService(store)
        service.commit(_request())
        with pytest.raises(EduAgentError) as excinfo:
            service.commit(_request(digest=DIGEST2))
        assert excinfo.value.code is ErrorCode.SCHEMA_INVALID
        assert store.domain_revision(UID) == 1

    def test_same_id_different_user_fails(self, tmp_path: Path) -> None:
        """§11: usuário diferente para o mesmo ID falha — ``operation_id`` é
        chave global, não por usuário (dedup consulta por ID)."""
        store = _store(tmp_path)
        store.ensure_user(UID)
        store.ensure_user(UID2)
        service = EffectsService(store)
        service.commit(_request())
        with pytest.raises(EduAgentError) as excinfo:
            service.commit(_request(user_id=UID2, fact_id=str(uuid.uuid4())))
        assert excinfo.value.code is ErrorCode.SCHEMA_INVALID
        assert store.domain_revision(UID) == 1
        assert _counts(store, "outbox", UID2) == 0

    def test_commit_unknown_user_source_unresolved(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        service = EffectsService(store)
        with pytest.raises(EduAgentError) as excinfo:
            service.commit(_request())
        assert excinfo.value.code is ErrorCode.SOURCE_UNRESOLVED

    def test_invalid_contract_rejected_before_transaction(
        self, tmp_path: Path
    ) -> None:
        """Contrato ``Operation`` da 003 valida o pedido FORA da transação
        (§11: transação curta; nada de validação segurando escritor)."""
        store = _store(tmp_path)
        store.ensure_user(UID)
        service = EffectsService(store)
        with pytest.raises(EduAgentError) as excinfo:
            service.commit(_request(action="nao.existe"))
        assert excinfo.value.code is ErrorCode.SCHEMA_INVALID
        with pytest.raises(EduAgentError) as excinfo:
            service.commit(_request(digest="zz" * 32))
        assert excinfo.value.code is ErrorCode.SCHEMA_INVALID
        # nada foi aplicado:
        assert store.domain_revision(UID) == 0
        assert _counts(store, "events") == 0
        assert _counts(store, "outbox") == 0


# ---------------------------------------------------------------------------
# Replay autoritativo (§11 — checkpoint não é atômico; recibo reutilizado)
# ---------------------------------------------------------------------------


class TestReplayAutoritativo:
    def test_receipt_for_reuses_stored_receipt(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store.ensure_user(UID)
        service = EffectsService(store)
        service.commit(_request())
        receipt = service.receipt_for(UID, OP, DIGEST)
        assert receipt is not None
        assert receipt.domain_revision == 1
        assert receipt.was_retry is True  # recibo reutilizado no replay
        assert store.domain_revision(UID) == 1

    def test_receipt_for_unknown_operation_returns_none(
        self, tmp_path: Path
    ) -> None:
        store = _store(tmp_path)
        store.ensure_user(UID)
        service = EffectsService(store)
        assert service.receipt_for(UID, OP, DIGEST) is None

    def test_receipt_for_digest_mismatch_fails(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store.ensure_user(UID)
        service = EffectsService(store)
        service.commit(_request())
        with pytest.raises(EduAgentError) as excinfo:
            service.receipt_for(UID, OP, DIGEST2)
        assert excinfo.value.code is ErrorCode.SCHEMA_INVALID

    def test_receipt_for_user_mismatch_fails(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store.ensure_user(UID)
        store.ensure_user(UID2)
        service = EffectsService(store)
        service.commit(_request())
        with pytest.raises(EduAgentError) as excinfo:
            service.receipt_for(UID2, OP, DIGEST)
        assert excinfo.value.code is ErrorCode.SCHEMA_INVALID

    def test_get_operation_exposes_authoritative_state(
        self, tmp_path: Path
    ) -> None:
        store = _store(tmp_path)
        store.ensure_user(UID)
        service = EffectsService(store)
        operation = store.get_operation(OP)
        assert operation is None  # antes do commit não há operação
        service.commit(_request())
        operation = store.get_operation(OP)
        assert operation is not None
        assert operation["state"] == "committed"
        assert operation["digest"] == DIGEST


# ---------------------------------------------------------------------------
# C3 — Dispatcher com lease; UNKNOWN_EFFECT sem retry; lease não bumpa
# ---------------------------------------------------------------------------


class TestC3DispatcherLease:
    def test_dispatch_applies_pending_and_acks(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store.ensure_user(UID)
        EffectsService(store).commit(_request())
        handler = RecordingHandler()
        report = _dispatch(store, handler)
        assert report.claimed == 1
        assert report.acked == 1
        assert handler.applied == [OP]
        assert store.outbox_row(OUTBOX)["state"] == "done"
        # lease/ACK/recibo são metadados operacionais: revisão intacta (§15.1)
        assert store.domain_revision(UID) == 1
        # segundo ciclo não encontra nada:
        report2 = _dispatch(store, handler, now=T0 + timedelta(minutes=1))
        assert report2.claimed == 0
        assert handler.applied == [OP]  # efeito aplicado uma única vez

    def test_not_applied_requeues_and_next_cycle_applies(
        self, tmp_path: Path
    ) -> None:
        """Entrega ao menos uma vez (§11): 'definitivamente não aplicado'
        volta a ``pending`` e um ciclo futuro recupera."""
        store = _store(tmp_path)
        store.ensure_user(UID)
        EffectsService(store).commit(_request())
        refusing = RecordingHandler(apply_outcome=EffectOutcome.NOT_APPLIED)
        report = _dispatch(store, refusing)
        assert report.requeued == 1
        assert store.outbox_row(OUTBOX)["state"] == "pending"
        assert store.domain_revision(UID) == 1
        willing = RecordingHandler()
        report2 = _dispatch(store, willing, now=T0 + timedelta(minutes=1))
        assert report2.acked == 1
        assert willing.applied == [OP]
        assert store.outbox_row(OUTBOX)["state"] == "done"

    def test_unknown_effect_without_probe_marks_failed_no_auto_retry(
        self, tmp_path: Path
    ) -> None:
        """§11: efeito desconhecido sem consulta possível permanece
        ``UNKNOWN_EFFECT``, sem retry automático."""
        store = _store(tmp_path)
        store.ensure_user(UID)
        EffectsService(store).commit(_request())
        blind = RecordingHandler(
            apply_outcome=EffectOutcome.UNKNOWN, probe_outcome=None
        )
        report = _dispatch(store, blind)
        assert report.unknown_effect == [OUTBOX]
        assert any(
            error.code is ErrorCode.UNKNOWN_EFFECT for error in report.errors
        )
        row = store.outbox_row(OUTBOX)
        assert row["state"] == "failed"  # terminal: dispatcher nunca apropria
        assert store.domain_revision(UID) == 1
        # sem retry automático: novo ciclo não chama o destino nem move a linha
        fresh = RecordingHandler()
        report2 = _dispatch(store, fresh, now=T0 + timedelta(minutes=1))
        assert report2.claimed == 0
        assert report2.acked == 0
        assert fresh.applied == []
        assert fresh.probed == []
        assert store.outbox_row(OUTBOX)["state"] == "failed"

    def test_recovered_row_probes_first_and_acks_without_reapply(
        self, tmp_path: Path
    ) -> None:
        """Crash após efeito antes do ACK: lease expira, o novo dispatcher
        reconcilia o destino por identidade e confirma sem reentregar."""
        store = _store(tmp_path)
        store.ensure_user(UID)
        EffectsService(store).commit(_request())
        # dispatcher "anterior": apropriou, aplicou o efeito e morreu sem ACK
        claimed = store.claim_outbox(now=T0_ISO, lease_until=T_PLUS_30)
        assert len(claimed) == 1
        assert claimed[0].recovered is False
        applied_before_crash = {OP}  # efeito que chegou ao destino antes do crash
        identity = RecordingHandler()  # apply não pode ser chamado
        identity.applied = []  # quem aplicou foi o processo morto
        probe_handler = _IdentityProbe(applied_before_crash, strict_apply=True)
        report = OutboxDispatcher(store, probe_handler).dispatch_pending(
            now=T0 + timedelta(minutes=2)  # lease de T_PLUS_30 já expirou
        )
        assert report.claimed == 1
        assert report.acked == 1
        assert probe_handler.apply_calls == 0  # sem duplicação de efeito
        assert store.outbox_row(OUTBOX)["state"] == "done"
        assert store.domain_revision(UID) == 1

    def test_recovered_row_probe_not_applied_applies_once(
        self, tmp_path: Path
    ) -> None:
        """Crash com lease expirado ANTES do efeito chegar ao destino: probe
        diz NOT_APPLIED, o efeito é aplicado exatamente uma vez."""
        store = _store(tmp_path)
        store.ensure_user(UID)
        EffectsService(store).commit(_request())
        store.claim_outbox(now=T0_ISO, lease_until=T_PLUS_30)
        probe_handler = _IdentityProbe(applied=set(), strict_apply=False)
        report = OutboxDispatcher(store, probe_handler).dispatch_pending(
            now=T0 + timedelta(minutes=2)
        )
        assert report.acked == 1
        assert probe_handler.apply_calls == 1  # nem zero, nem dois
        assert store.outbox_row(OUTBOX)["state"] == "done"

    def test_apply_exception_treated_as_unknown_then_reconciled(
        self, tmp_path: Path
    ) -> None:
        """Exceção em ``apply`` é resultado desconhecido: sem consulta
        possível vira UNKNOWN_EFFECT terminal; com probe NOT_APPLIED, a
        linha volta a pendente e o ciclo seguinte aplica."""
        store = _store(tmp_path)
        store.ensure_user(UID)
        EffectsService(store).commit(_request())
        failing = RecordingHandler(
            apply_raises=ConnectionError("rede indisponível"),
            probe_outcome=None,
        )
        report = _dispatch(store, failing)
        assert report.unknown_effect == [OUTBOX]
        # variante com consulta possível:
        store2 = _store(tmp_path, "domain2.sqlite")
        store2.ensure_user(UID)
        EffectsService(store2).commit(_request())
        failing_but_provable = RecordingHandler(
            apply_raises=ConnectionError("rede indisponível"),
            probe_outcome=EffectOutcome.NOT_APPLIED,
        )
        report2 = _dispatch(store2, failing_but_provable)
        assert report2.requeued == 1  # sabe-se que não aplicou: recupera
        assert store2.outbox_row(OUTBOX)["state"] == "pending"

    def test_lease_blocks_concurrent_claim_until_expiry(
        self, tmp_path: Path
    ) -> None:
        store = _store(tmp_path)
        store.ensure_user(UID)
        EffectsService(store).commit(_request())
        first = store.claim_outbox(now=T0_ISO, lease_until=T_PLUS_30)
        assert len(first) == 1
        # segundo dispatcher com lease válido do primeiro não apropria:
        again = store.claim_outbox(now=T0_ISO, lease_until=T_PLUS_30)
        assert again == []
        # após expiração do lease, a linha é recuperada como in_flight:
        recovered = store.claim_outbox(now=T_PLUS_120, lease_until="2026-10-21T12:03:00Z")
        assert len(recovered) == 1
        assert recovered[0].recovered is True

    def test_operational_metadata_never_bumps_domain_revision(
        self, tmp_path: Path
    ) -> None:
        """§15.1: receipt/lease/trace não incrementam ``domain_revision``."""
        store = _store(tmp_path)
        store.ensure_user(UID)
        service = EffectsService(store)
        service.commit(_request())
        assert store.domain_revision(UID) == 1
        store.claim_outbox(now=T0_ISO, lease_until=T_PLUS_30)
        assert store.domain_revision(UID) == 1
        store.requeue_outbox(OUTBOX)
        assert store.domain_revision(UID) == 1
        store.claim_outbox(now=T0_ISO, lease_until=T_PLUS_30)
        store.ack_outbox(OUTBOX)
        assert store.domain_revision(UID) == 1
        # recibo reutilizado em retry também não incrementa:
        service.commit(_request(expected_version=0))
        assert store.domain_revision(UID) == 1

    def test_state_transition_from_wrong_state_is_internal_failure(
        self, tmp_path: Path
    ) -> None:
        store = _store(tmp_path)
        store.ensure_user(UID)
        EffectsService(store).commit(_request())
        with pytest.raises(EduAgentError) as excinfo:
            store.ack_outbox(OUTBOX)  # ainda pending, não in_flight
        assert excinfo.value.code is ErrorCode.INTERNAL_FAILURE


class _IdentityProbe:
    """Destino com consulta por identidade (probe) para testes de
    reconciliação; ``strict_apply`` proíbe reentrega."""

    def __init__(self, applied: set[str], *, strict_apply: bool) -> None:
        self.applied = applied
        self.strict_apply = strict_apply
        self.apply_calls = 0

    def apply(
        self, target: str, payload: object, operation_id: str
    ) -> EffectOutcome:
        if self.strict_apply:
            raise AssertionError(
                "apply não deveria ser chamado: efeito já reconhecido"
            )
        self.apply_calls += 1
        return EffectOutcome.APPLIED

    def probe(self, target: str, operation_id: str) -> EffectOutcome:
        return (
            EffectOutcome.APPLIED
            if operation_id in self.applied
            else EffectOutcome.NOT_APPLIED
        )


# ---------------------------------------------------------------------------
# C2 — Crash/replay com processo morto em pontos definidos (§11)
# ---------------------------------------------------------------------------


def _run_crash(
    point: str,
    db_path: Path,
    marker_path: Path,
    *,
    operation_id: str = OP,
    outbox_id: str = OUTBOX,
    event_id: str = EVENT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "tests" / "_task005_crash_runner.py"),
            point,
            str(db_path),
            UID,
            operation_id,
            DIGEST,
            outbox_id,
            event_id,
            str(marker_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )


class TestC2CrashReplay:
    def test_crash_before_commit_promotes_nothing_and_replay_applies_once(
        self, tmp_path: Path
    ) -> None:
        db = tmp_path / "crash_pre.sqlite"
        proc = _run_crash("pre-commit", db, tmp_path / "marker.json")
        assert proc.returncode == 137, proc.stderr
        # nada foi promovido: transação sem COMMIT não persiste nada (§11)
        store = _store(tmp_path, "crash_pre.sqlite")
        assert store.domain_revision(UID) == 0
        assert _counts(store, "operations") == 0
        assert _counts(store, "events") == 0
        assert _counts(store, "facts") == 0
        assert _counts(store, "outbox") == 0
        # replay com a mesma identidade aplica exatamente uma vez:
        service = EffectsService(store)
        receipt = service.commit(_request())
        assert receipt.domain_revision == 1
        assert receipt.was_retry is False
        # replay repetido reutiliza o recibo mesmo com versão antiga:
        again = service.commit(_request(expected_version=0))
        assert again.applied_at == receipt.applied_at
        assert again.was_retry is True
        assert store.domain_revision(UID) == 1
        assert _counts(store, "events") == 1
        assert _counts(store, "facts") == 1
        assert _counts(store, "outbox") == 1
        assert _counts(store, "operations") == 1

    def test_crash_after_commit_recovers_pending_outbox(
        self, tmp_path: Path
    ) -> None:
        db = tmp_path / "crash_post.sqlite"
        proc = _run_crash("post-commit", db, tmp_path / "marker.json")
        assert proc.returncode == 137, proc.stderr
        store = _store(tmp_path, "crash_post.sqlite")
        assert store.domain_revision(UID) == 1  # commit persistiu
        assert _counts(store, "operations") == 1
        assert store.outbox_row(OUTBOX)["state"] == "pending"
        # dispatcher recupera o pendente e entrega uma única vez:
        handler = RecordingHandler()
        report = _dispatch(store, handler)
        assert report.claimed == 1
        assert report.acked == 1
        assert handler.applied == [OP]
        assert store.outbox_row(OUTBOX)["state"] == "done"
        assert store.domain_revision(UID) == 1  # lease/ACK não bumpam
        report2 = _dispatch(store, handler, now=T0 + timedelta(minutes=1))
        assert report2.claimed == 0
        assert handler.applied == [OP]  # sem duplicação

    def test_crash_after_effect_before_ack_reconciles_by_identity(
        self, tmp_path: Path
    ) -> None:
        db = tmp_path / "crash_effect.sqlite"
        marker = tmp_path / "marker.json"
        proc = _run_crash("post-effect", db, marker)
        assert proc.returncode == 137, proc.stderr
        # o efeito chegou ao destino exatamente uma vez antes do crash:
        applied = json.loads(marker.read_text())
        assert applied["apply_calls"] == 1
        assert applied["applied"] == [OP]
        store = _store(tmp_path, "crash_effect.sqlite")
        assert store.domain_revision(UID) == 1
        assert store.outbox_row(OUTBOX)["state"] == "in_flight"
        # novo dispatcher, com o lease já expirado, reconcilia por identidade:
        probe_handler = _IdentityProbe(applied={OP}, strict_apply=True)
        report = OutboxDispatcher(store, probe_handler).dispatch_pending(
            now=T0 + timedelta(minutes=2)
        )
        assert report.claimed == 1
        assert report.acked == 1
        assert probe_handler.apply_calls == 0  # sem reentrega (sem duplicação)
        assert store.outbox_row(OUTBOX)["state"] == "done"
        # efeito reconhecido não foi perdido nem duplicado:
        assert json.loads(marker.read_text())["apply_calls"] == 1
        assert store.domain_revision(UID) == 1
