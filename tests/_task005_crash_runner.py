"""Runner de crash dos testes da task 005 (mapa §11).

Executado como subprocesso por ``tests/test_task005_effects.py``. Simula
crash real matando o próprio processo com ``os._exit`` em pontos definidos —
sem unwind de exceções, sem ``finally``, sem ``COMMIT``: exatamente o que o
mapa §11 manda validar (pré-commit, pós-commit, pós-efeito sem ACK).

Uso::

    python tests/_task005_crash_runner.py POINT DB USER OP DIGEST OUTBOX EVENT MARKER

Pontos:
- ``pre-commit``: mata o processo exatamente antes do ``COMMIT`` da
  transação do commit idempotente (trace callback do sqlite3, invocado
  antes da execução do statement).
- ``post-commit``: commit completo, mata antes de despachar o outbox.
- ``post-effect``: commit, dispatcher apropria com lease, efeito aplicado
  no destino (marcador em arquivo), mata antes do ACK.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eduagent.services.effects import (  # noqa: E402
    CommitRequest,
    EffectOutcome,
    EffectsService,
    EventSpec,
    OutboxDispatcher,
    OutboxSpec,
)
from eduagent.storage.repository import DomainStore  # noqa: E402

T0 = "2026-10-21T12:00:00Z"


def _record_effect(marker_path: str, operation_id: str) -> None:
    """Registra o efeito aplicado no 'destino' (arquivo marcador)."""
    path = Path(marker_path)
    data: dict[str, object] = {"applied": [], "apply_calls": 0}
    if path.exists():
        data = json.loads(path.read_text())
    applied = list(data["applied"])  # type: ignore[arg-type]
    applied.append(operation_id)
    data["applied"] = applied
    data["apply_calls"] = int(data["apply_calls"]) + 1  # type: ignore[arg-type]
    path.write_text(json.dumps(data))


def main(argv: list[str]) -> int:
    point, db_path, user_id, operation_id, digest, outbox_id, event_id, marker = argv
    store = DomainStore.open(db_path)
    store.ensure_user(user_id)
    service = EffectsService(store)
    request = CommitRequest(
        operation_id=operation_id,
        user_id=user_id,
        action="fact.upsert",
        digest=digest,
        expected_version=0,
        event=EventSpec(
            id=event_id,
            kind="reading",
            occurred_at=T0,
            recorded_at=T0,
            payload={"origin": "crash-test"},
        ),
        outbox=OutboxSpec(
            id=outbox_id,
            target="sidecar",
            payload={"operation_id": operation_id},
        ),
        projection=(
            (
                "INSERT INTO facts(id, user_id, kind, value_json, authority, "
                "recorded_at, status) VALUES (?,?,?,?,?,?,?)",
                (event_id, user_id, "note", "{}", "user", T0, "confirmed"),
            ),
        ),
    )

    if point == "pre-commit":
        # ``sqlite3.Connection`` é imutável: o crash exato antes do COMMIT é
        # simulado com trace callback, invocado pelo sqlite3 ANTES de
        # executar cada statement — COMMIT nunca chega a executar.
        def crash_before_commit(statement: str) -> None:
            if statement.strip().upper() == "COMMIT":
                os._exit(137)  # crash antes do commit: sem rollback, sem finally

        store._conn.set_trace_callback(crash_before_commit)
        service.commit(request)
        return 1  # inalcançável: o COMMIT mata o processo

    if point == "post-commit":
        service.commit(request)
        os._exit(137)  # crash após o commit, antes de despachar o outbox

    if point == "post-effect":
        service.commit(request)

        class CrashAfterEffect:
            def apply(
                self, target: str, payload: object, operation_id: str
            ) -> EffectOutcome:
                _record_effect(marker, operation_id)
                os._exit(137)  # efeito aplicado, ACK nunca acontece

            def probe(self, target: str, operation_id: str) -> EffectOutcome:
                return EffectOutcome.APPLIED

        # lease de 30 s a partir de T0: o pai recupera a linha com o lease
        # já expirado (now = T0 + 2 min) e reconcilia por identidade.
        OutboxDispatcher(store, CrashAfterEffect()).dispatch_pending(
            now=datetime(2026, 10, 21, 12, 0, 0, tzinfo=timezone.utc)
        )
        return 1  # inalcançável: o apply mata o processo

    return 2  # ponto desconhecido


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
