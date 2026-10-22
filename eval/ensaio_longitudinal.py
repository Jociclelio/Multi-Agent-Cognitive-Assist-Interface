"""Ensaio longitudinal offline do EduAgent-OS v0.1 (task 017; mapa §13.8/§13.10).

Protocolo mecânico de rota completa em dados de teste locais: ingestão →
pergunta/prática com pausas e retomadas → avaliação → replanejamento →
exportação ICS → crash/recuperação — cada passo é uma invocação separada
(pausa/retomada do próprio protocolo, dentro do limite de 10 min por
execução local). Nada aqui é resultado medido de qualidade: é evidência
executável de aceite funcional (mapa §13.235).

Uso (cada passo grava JSON de evidência em --evidence-dir):

    python eval/ensaio_longitudinal.py setup   --data-root DIR ...
    python eval/ensaio_longitudinal.py doctor  --data-root DIR --model-url URL
    python eval/ensaio_longitudinal.py ingest  --data-root DIR --file PDF ...
    python eval/ensaio_longitudinal.py ask     --data-root DIR --message "..."
    python eval/ensaio_longitudinal.py practice --data-root DIR ...
    python eval/ensaio_longitudinal.py hint    --data-root DIR ...
    python eval/ensaio_longitudinal.py submit  --data-root DIR --answer "..."
    python eval/ensaio_longitudinal.py submit-known --data-root DIR ...
    python eval/ensaio_longitudinal.py plan    --data-root DIR
    python eval/ensaio_longitudinal.py resume  --data-root DIR --data '{"confirmed":true}'
    python eval/ensaio_longitudinal.py approve --data-root DIR
    python eval/ensaio_longitudinal.py export  --data-root DIR
    python eval/ensaio_longitudinal.py cancel  --data-root DIR
    python eval/ensaio_longitudinal.py backup  --data-root DIR
    python eval/ensaio_longitudinal.py restore --data-root DIR --to DIR
    python eval/ensaio_longitudinal.py crash   --data-root DIR
    python eval/ensaio_longitudinal.py state   --data-root DIR

Componentes reais (não dobras de teste): extrator Docling (fiação default do
runtime), embedder BGE-M3 (--embedder-dir) e modelo Bonsai 2 via runtime
loopback pinado (--model-url), com capacidade json_schema lida do manifesto
congelado (--manifest). O "student" mecânico usa o gabarito do domínio
somente em ``submit-known`` (privilégio de harness registrado no relatório).
"""

from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
import time
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eduagent.cli import run as run_cli
from eduagent.contracts import EduAgentError
from eduagent.services.model_adapter import ModelAdapter
from eduagent.services.retrieval import BgeM3Embedder
from eduagent.runtime import RuntimeContext

UTC = timezone.utc
DIAGNOSTIC = "eval/ensaio_longitudinal.py"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ensaio_longitudinal",
        description="Ensaio longitudinal offline (task 017).",
    )
    parser.add_argument("--data-root", default="/tmp/opencode/017/ensaio")
    parser.add_argument("--model-url", default=None)
    parser.add_argument("--embedder-dir", default=None)
    parser.add_argument(
        "--manifest", default=None, help="manifesto congelado (default: manifest.json)"
    )
    parser.add_argument(
        "--evidence-dir", default="/tmp/opencode/017/evidencias"
    )
    parser.add_argument("--step", required=True)
    parser.add_argument("--file", default=None, help="PDF para ingest")
    parser.add_argument("--message", default=None)
    parser.add_argument("--answer", default=None)
    parser.add_argument("--session", default=None)
    parser.add_argument("--course", default=None)
    parser.add_argument("--topic", action="append", default=[])
    parser.add_argument("--data", default=None, help="JSON de retomada")
    parser.add_argument("--to", default=None, help="diretório do restore")
    parser.add_argument("--config", default=None, help="config YAML do ensaio")
    return parser


def _manifest_capabilities(manifest_path: Path) -> dict[str, Any] | None:
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def open_runtime(args: argparse.Namespace) -> RuntimeContext:
    manifest = _manifest_capabilities(
        Path(args.manifest) if args.manifest else Path("manifest.json")
    )
    backend = None
    if args.model_url:
        from eduagent.services.model_adapter import RuntimeCapabilities

        if manifest is None:
            capabilities = RuntimeCapabilities(
                json_schema=False,
                json_schema_evidence="sem manifesto (capacidade não presumida)",
            )
        else:
            capabilities = RuntimeCapabilities(
                json_schema=bool(
                    (manifest.get("capacidades") or {})
                    .get("json_schema", {})
                    .get("suportada")
                ),
                json_schema_evidence=(
                    "manifesto congelado; verificação registrada no gate G5 "
                    "da task 002 (ensaio 017)"
                ),
            )
        backend = ModelAdapter(base_url=args.model_url, capabilities=capabilities)
    embedder = BgeM3Embedder(args.embedder_dir) if args.embedder_dir else None
    return RuntimeContext.open(
        args.data_root,
        config_path=args.config,
        backend=backend,
        embedder=embedder,
    )


def _record(args: argparse.Namespace, step: str, payload: dict[str, Any]) -> None:
    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).isoformat()
    out = {"step": step, "recorded_at": stamp, **payload}
    target = evidence_dir / f"{step}.json"
    target.write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(out, ensure_ascii=False, default=str))


def _elapsed(start: float) -> float:
    return round(time.monotonic() - start, 2)


def step_setup(args: argparse.Namespace) -> int:
    """Fixture mecânica do ensaio: usuário/disciplina/tópico no domínio."""
    start = time.monotonic()
    runtime = open_runtime(args)
    try:
        user_id = str(_uuid.uuid5(_uuid.NAMESPACE_URL, "ensaio017:user"))
        course_id = str(_uuid.uuid5(_uuid.NAMESPACE_URL, "ensaio017:course"))
        topic_id = str(_uuid.uuid5(_uuid.NAMESPACE_URL, "ensaio017:topic"))
        runtime.store.ensure_user(user_id)
        runtime.store.execute_write(
            user_id,
            [
                (
                    "INSERT OR IGNORE INTO courses(id, user_id, title) VALUES (?,?,?)",
                    (course_id, user_id, "MO810"),
                ),
                (
                    "INSERT OR IGNORE INTO topics(id, course_id, title) VALUES (?,?,?)",
                    (topic_id, course_id, "Commit idempotente e recibos"),
                ),
            ],
            bump_domain_revision=False,
        )
        _record(
            args,
            "setup",
            {
                "user_id": user_id,
                "course_id": course_id,
                "topic_id": topic_id,
                "elapsed_s": _elapsed(start),
                "note": "fixture mecânica do ensaio (registrada no relatório)",
            },
        )
    finally:
        runtime.close()
    return 0


def step_cli(args: argparse.Namespace, name: str, extra: list[str]) -> int:
    """Passo executado pela própria CLI (superfície real do MVP)."""
    import io as _io

    start = time.monotonic()
    argv = [
        "--data-root", args.data_root,
        "--user", _fixed_ids()["user"],
    ]
    if args.model_url:
        argv += ["--model-url", args.model_url]
    if args.embedder_dir:
        argv += ["--embedder-dir", args.embedder_dir]
    if args.manifest:
        argv += ["--manifest", args.manifest]
    if args.config:
        argv += ["--config", args.config]
    argv += [name] + extra
    buffer = _io.StringIO()
    code = run_cli(argv, stdout=buffer)
    stdout_text = buffer.getvalue()
    try:
        cli_payload = json.loads(stdout_text)
    except json.JSONDecodeError:
        cli_payload = {"stdout": stdout_text}
    _record(
        args,
        name,
        {"exit_code": code, "elapsed_s": _elapsed(start), "cli": cli_payload},
    )
    print(f"exit={code} elapsed={_elapsed(start)}s")
    return code


def _fixed_ids() -> dict[str, str]:
    return {
        "user": str(_uuid.uuid5(_uuid.NAMESPACE_URL, "ensaio017:user")),
        "course": str(_uuid.uuid5(_uuid.NAMESPACE_URL, "ensaio017:course")),
        "topic": str(_uuid.uuid5(_uuid.NAMESPACE_URL, "ensaio017:topic")),
    }


def step_ingest(args: argparse.Namespace) -> int:
    """Ingestão real (Docling) + confirmação do gate (§6.3) + indexação
    densa real (BGE-M3) + ativação após indexação completa (§6.1)."""
    start = time.monotonic()
    code = step_cli(
        args, "ingest",
        ["--file", args.file or "", "--course", _fixed_ids()["course"],
         "--session", _session(args)],
    )
    if code != 0:
        return code
    evidence = Path(args.evidence_dir) / "ingest.json"
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    cli_payload = payload.get("cli") or {}
    if str(cli_payload.get("status")) == "waiting_student" or cli_payload.get(
        "waiting_for"
    ):
        # Gate de confirmação (§6.3): fatos ambíguos/prazos só-de-dia ficam
        # candidatos até confirmação — pausa/retomada do próprio protocolo.
        code = step_cli(
            args, "resume",
            ["--session", _session(args), "--data", '{"confirmed": true}'],
        )
        if code != 0:
            return code
    ids = _fixed_ids()
    runtime = open_runtime(args)
    try:
        rows = runtime.store.fetch_user_rows(
            "SELECT id, active_version FROM documents WHERE user_id = ?",
            (ids["user"],),
        )
        doc_id = str(rows[-1]["id"])
        pending = runtime.store.fetch_user_rows(
            "SELECT id, status FROM doc_versions WHERE doc_id = ? ORDER BY rowid DESC LIMIT 1",
            (doc_id,),
        )
        version_id = str(pending[0]["id"])
        if args.embedder_dir:
            # Índice denso real (BGE-M3) SEMPRE publicado antes da ativação
            # (§6.1: nova versão só ativa após indexação completa); a
            # publicação é atômica e reconstrói o índice da versão (007).
            from eduagent.services.retrieval import RetrievalService

            retrieval = RetrievalService(runtime.store, runtime.data_root)
            retrieval.index_version(
                ids["user"], doc_id, version_id,
                embedder=BgeM3Embedder(args.embedder_dir),
            )
        # Ativação só após indexação completa (§6.1); idempotente.
        runtime.graph._ingestion.activate_version(  # noqa: SLF001 — fronteira do ensaio (harness)
            ids["user"], doc_id, version_id
        )
        active = runtime.store.fetch_user_rows(
            "SELECT active_version FROM documents WHERE id = ?", (doc_id,)
        )
        _record(
            args,
            "ingest_index",
            {
                "doc_id": doc_id,
                "version_id": version_id,
                "active_version": str(active[0]["active_version"]) if active else None,
                "elapsed_s": _elapsed(start),
                "note": "índice denso publicado (BGE-M3 real) e versão ativada após indexação completa (§6.1)",
            },
        )
    finally:
        runtime.close()
    return 0


def step_state(args: argparse.Namespace) -> int:
    """Estado do domínio (inspeção autoritativa do harness, §12)."""
    ids = _fixed_ids()
    runtime = open_runtime(args)
    try:
        user = ids["user"]
        counts = {}
        user_columns = {"assessments": "attempt_user_id"}
        for table in (
            "documents", "doc_versions", "facts",
            "items", "attempts", "assessments", "demands", "plans",
            "confirmations", "logical_blocks", "operations",
        ):
            column = user_columns.get(table, "user_id")
            rows = runtime.store.fetch_user_rows(
                f"SELECT COUNT(*) AS n FROM {table} WHERE {column} = ?",
                (user,),
            )
            counts[table] = int(rows[0]["n"]) if rows else 0
        for table in ("blocks", "chunks", "events"):
            rows = runtime.store.fetch_user_rows(
                f"SELECT COUNT(*) AS n FROM {table} WHERE user_id = ?", (user,)
            )
            counts[table] = int(rows[0]["n"]) if rows else 0
        pending = runtime.store.fetch_user_rows(
            "SELECT id, status FROM demands "
            "WHERE user_id = ? AND status = 'pending'",
            (user,),
        )
        _record(
            args,
            "state",
            {
                "counts": counts,
                "pending_demands": [str(r["id"]) for r in pending],
                "domain_revision": runtime.store.domain_revision(user),
                "elapsed_s": 0.0,
            },
        )
    finally:
        runtime.close()
    return 0


def step_crash(args: argparse.Namespace) -> int:
    """Crash/recuperação: processo do SUT morto com SIGKILL no meio de um
    turno; reabertura e retomada provam checkpoint + domínio autoritativo."""
    start = time.monotonic()
    marker = Path(args.data_root) / "ensaio-crash.marker"
    if marker.exists():
        marker.unlink()
    child = subprocess.Popen(
        [
            sys.executable, __file__,
            "--data-root", args.data_root,
            "--model-url", args.model_url or "",
            "--embedder-dir", args.embedder_dir or "",
            "--manifest", args.manifest or "manifest.json",
            "--evidence-dir", args.evidence_dir,
            "--step", "crash-child",
            "--message", "Resuma o que acontece em um retry com o mesmo operation_id.",
            "--session", "crash-session-017",
            "--course", _fixed_ids()["course"],
            "--topic", _fixed_ids()["topic"],
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Espera o filho registrar o início do turno e abrir o conjunto (BGE-M3
    # real carrega em segundos); mata no meio do processamento do turno.
    deadline = time.monotonic() + 120
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    time.sleep(25.0)  # turno em voo (processamento com modelo real)
    child.send_signal(signal.SIGKILL)
    child.wait(timeout=30)
    runtime = open_runtime(args)
    try:
        integrity = runtime.store.fetch_user_rows(
            "PRAGMA integrity_check", ()
        )[0]["integrity_check"]
        crash_session = str(_uuid.uuid5(
            _uuid.NAMESPACE_URL, "ensaio017:sessao:crash-session-017"
        ))
        sessions = runtime.store.fetch_user_rows(
            "SELECT DISTINCT session_id FROM events WHERE user_id = ?",
            (_fixed_ids()["user"],),
        )
        evidence = {
            "child_killed": "SIGKILL durante turno em voo",
            "domain_integrity_after_crash": str(integrity),
            "sessions_in_domain": sorted(str(r["session_id"]) for r in sessions),
            "crash_session": crash_session,
            "recovery": "reabertura e novo turno na MESMA sessão (passo ask-crash-recovery)",
            "elapsed_s": _elapsed(start),
        }
        _record(args, "crash", evidence)
    finally:
        runtime.close()
    return 0


def step_crash_child(args: argparse.Namespace) -> int:
    """Processo vítima: marca início do turno e roda ask (morre no meio)."""
    marker = Path(args.data_root) / "ensaio-crash.marker"
    marker.write_text("turn-started", encoding="utf-8")
    return step_cli(args, "ask", [
        "--message", args.message or "resumo",
        "--course", _fixed_ids()["course"],
        "--session", args.session or "crash-session-017",
    ])


def step_backup(args: argparse.Namespace) -> int:
    start = time.monotonic()
    code = step_cli(args, "backup", [])
    if code == 0:
        _record(args, "backup_done", {"elapsed_s": _elapsed(start)})
    return code


def step_restore(args: argparse.Namespace) -> int:
    start = time.monotonic()
    runtime = open_runtime(args)
    try:
        from eduagent.services.backup import BackupCatalog

        catalog = BackupCatalog(Path(args.data_root).parent / "backups")
        entries = catalog.entries()
        active = [e for e in entries if e.get("status") == "active"]
        latest = active[-1] if active else None
    finally:
        runtime.close()
    if latest is None:
        _record(args, "restore", {"status": "sem backup no catálogo"})
        return 3
    code = step_cli(args, "restore", ["--from", str(latest["directory"]), "--to", args.to or ""])
    if code == 0:
        _record(args, "restore_done", {"elapsed_s": _elapsed(start), "from": str(latest["directory"])})
    return code


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    steps = {
        "setup": step_setup,
        "doctor": lambda a: step_cli(a, "doctor", []),
        "ingest": step_ingest,
        "ask": lambda a: step_cli(a, "ask", [
            a.message or "",
            "--course", _fixed_ids()["course"],
            "--session", _session(a),
        ]),
        "practice": lambda a: step_cli(a, "practice", [
            a.message or "quero praticar",
            "--course", _fixed_ids()["course"],
            "--topic", *_fixed_topic(a),
            "--session", _session(a),
        ]),
        "hint": lambda a: step_cli(a, "practice", [
            a.message or "quero uma pista",
            "--course", _fixed_ids()["course"],
            "--topic", *_fixed_topic(a),
            "--session", _session(a),
        ]),
        "submit": lambda a: step_cli(a, "submit", [
            a.answer or "",
            "--session", _session(a),
        ]),
        "submit-known": step_submit_known,
        "plan": lambda a: step_cli(a, "plan", ["--session", _session(a)]),
        "resume": lambda a: step_cli(a, "resume", [
            "--session", _session(a),
            "--data", a.data or "{}",
        ]),
        "approve": lambda a: step_cli(a, "approve", ["--session", _session(a)]),
        "export": lambda a: step_cli(a, "export", ["--session", _session(a)]),
        "cancel": lambda a: step_cli(a, "cancel", ["--session", _session(a)]),
        "trace": lambda a: step_cli(a, "trace", ["--last"]),
        "backup": step_backup,
        "restore": step_restore,
        "crash": step_crash,
        "crash-child": step_crash_child,
        "state": step_state,
    }
    handler = steps.get(args.step)
    if handler is None:
        print(f"passo desconhecido: {args.step}", file=sys.stderr)
        return 4
    try:
        return int(handler(args))
    except EduAgentError as exc:
        _record(args, args.step, {"failed": exc.to_dict()})
        return 4


def _session(args: argparse.Namespace) -> str:
    """Sessões são UUIDs (contrato GraphState, mapa §4): o nome pedido pelo
    protocolo é derivado deterministicamente para um UUID de sessão."""
    return str(
        _uuid.uuid5(
            _uuid.NAMESPACE_URL,
            f"ensaio017:sessao:{args.session or 'main'}",
        )
    )


def _fixed_topic(args: argparse.Namespace) -> list[str]:
    return args.topic or [_fixed_ids()["topic"]]


def step_submit_known(args: argparse.Namespace) -> int:
    """Submissão com o gabarito lido do domínio (privilégio de harness,
    registrado no relatório): prova o caminho CORRETO da avaliação."""
    start = time.monotonic()
    ids = _fixed_ids()
    runtime = open_runtime(args)
    try:
        ev = runtime.store.fetch_user_rows(
            "SELECT payload_json FROM events WHERE user_id = ? AND kind = 'item_published' "
            "ORDER BY occurred_at DESC LIMIT 1",
            (ids["user"],),
        )
        if not ev:
            _record(args, "submit-known", {"status": "sem item publicado"})
            return 3
        payload = json.loads(ev[0]["payload_json"])
        expected = str(payload.get("expected_answer", ""))
    finally:
        runtime.close()
    code = step_cli(args, "submit", [expected, "--session", _session(args)])
    if code == 0:
        _record(args, "submit-known_done", {"elapsed_s": _elapsed(start), "gabarito": "lido do domínio (harness)"})
    return code


if __name__ == "__main__":  # pragma: no cover — ponto de entrada do ensaio
    raise SystemExit(main())
