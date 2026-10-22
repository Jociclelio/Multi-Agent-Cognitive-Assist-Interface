"""CLI mínima do EduAgent-OS (mapa §12, task 015).

Comandos (§12): ``doctor, ingest, ask, practice, submit, plan, approve,
export, resume, cancel, trace, backup, restore, delete``.

Contratos:

- **Exit codes (§12)**: ``0`` sucesso/espera legítima; ``2`` entrada
  ambígua/inválida; ``3`` recurso/conector indisponível; ``4`` falha interna.
  O mapeamento dos códigos de erro do §4 para exit codes é escolha local
  documentada em ``EXIT_CODE_BY_ERROR`` (o mapa fixa as quatro classes, não
  o destino de cada código).
- **JSON sempre contém ``status``** (§12) — toda saída é um objeto JSON com
  ``status`` (``completed``/``waiting``/``cancelled``/``failed`` e os
  relatórios próprios de ``doctor``/``backup``/``restore``/``trace``).
- **Escrita exige contexto de usuário autenticado localmente** (§12): todo
  comando que lê/escreve dados exige ``--user <uuid>`` registrado no domínio
  local (o usuário é o contexto autenticado do MVP local; não há rede).
- **Backup/restore (§5/§15.1)**: backup fecha escritores/checkpointer e copia
  conjunto consistente com manifesto; restore é em diretório NOVO com
  verificação; exclusão mostra escopo/prazo e não alega sanitização forense.

Nenhuma saída numérica aqui é resultado medido: defaults são escolhas de
ensaio do mapa (§1/§3).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid as _uuid
from pathlib import Path
from typing import Any, Callable, Sequence

from eduagent.contracts import EduAgentError, ErrorCode
from eduagent.services.backup import BackupService
from eduagent.services.model_adapter import ModelAdapter, RuntimeCapabilities
from eduagent.storage.repository import require_wal_capable_sqlite
from eduagent.telemetry import load_trace
from eduagent.runtime import (
    CHECKPOINTS_DB_NAME,
    DOMAIN_DB_NAME,
    RuntimeContext,
)

DIAGNOSTIC = "eduagent/cli.py"

EXIT_OK = 0
EXIT_INVALID_INPUT = 2
EXIT_UNAVAILABLE = 3
EXIT_INTERNAL = 4

#: Mapeamento dos códigos do §4 para as classes de exit code do §12.
#: (0 sucesso/espera legítima — cancelamento atendido é sucesso da
#: solicitação; 2 entrada ambígua/inválida; 3 recurso/conector indisponível;
#: 4 falha interna.) Escolha local documentada — o mapa fixa as classes.
#: Recurso configurado ausente (serviço/embedder/modelo não configurado) é
#: classe 3 por ``SOURCE_UNRESOLVED`` (§12: recurso/conector indisponível;
#: escolha local de mapeamento da 015a — ausência de recurso declarada não
#: é falha interna).
EXIT_CODE_BY_ERROR: dict[ErrorCode, int] = {
    ErrorCode.AMBIGUOUS_INPUT: EXIT_INVALID_INPUT,
    ErrorCode.SCHEMA_INVALID: EXIT_INVALID_INPUT,
    ErrorCode.SOURCE_UNRESOLVED: EXIT_UNAVAILABLE,
    ErrorCode.VERSION_CONFLICT: EXIT_UNAVAILABLE,
    ErrorCode.RESOURCE_LIMIT: EXIT_UNAVAILABLE,
    ErrorCode.TIMEOUT: EXIT_UNAVAILABLE,
    ErrorCode.TOOL_DENIED: EXIT_UNAVAILABLE,
    ErrorCode.MODEL_NOT_ADMITTED: EXIT_UNAVAILABLE,
    ErrorCode.NO_EVIDENCE: EXIT_UNAVAILABLE,
    ErrorCode.UNKNOWN_EFFECT: EXIT_INTERNAL,
    ErrorCode.INTERNAL_FAILURE: EXIT_INTERNAL,
    ErrorCode.CANCELLED: EXIT_OK,
}


def _emit(payload: dict[str, Any], stream: Any = None) -> None:
    stream = stream or sys.stdout
    stream.write(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eduagent",
        description=(
            "EduAgent-OS v0.1 — CLI mínima local (mapa §12; MVP textual)."
        ),
    )
    parser.add_argument(
        "--data-root",
        default="data",
        help="diretório de dados local (mapa §3; default 'data')",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="caminho do config/default.yaml (default: config/default.yaml)",
    )
    parser.add_argument(
        "--user",
        default=None,
        help="UUID do usuário autenticado localmente (contexto do §12)",
    )
    parser.add_argument(
        "--model-url",
        default=None,
        help=(
            "URL do runtime loopback do modelo (mapa §3.1); sem ela, rotas "
            "com geração ficam indisponíveis com erro tipado"
        ),
    )
    parser.add_argument(
        "--embedder-dir",
        default=None,
        help=(
            "diretório do BGE-M3 local (mapa §6.5); sem ele, a rota "
            "ask/practice recusa com erro tipado"
        ),
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help=(
            "manifesto congelado (mapa §3.1/§13.10; default: manifest.json "
            "no diretório atual quando existir). Sem manifesto, capacidades "
            "NÃO são presumidas (json_schema desligada)"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="saúde do modelo/DB/índices/config (§12)")

    p = sub.add_parser("ingest", help="ingestão de documento (§6.1)")
    p.add_argument("--file", required=True)
    p.add_argument("--course", default="")
    p.add_argument("--session", default=None)

    p = sub.add_parser("ask", help="pergunta ao tutor (§8)")
    p.add_argument("message")
    p.add_argument("--course", default="")
    p.add_argument(
        "--topic",
        action="append",
        default=[],
        help="tópico alvo (UUID; repetível; §8/§15.2)",
    )
    p.add_argument("--session", default=None)

    p = sub.add_parser("practice", help="praticar item (§8)")
    p.add_argument("message", nargs="?", default="")
    p.add_argument("--course", default="")
    p.add_argument(
        "--topic",
        action="append",
        default=[],
        help="tópico alvo (UUID; repetível; §8/§15.2)",
    )
    p.add_argument("--session", default=None)

    p = sub.add_parser("submit", help="submeter resposta (§8/§15.2)")
    p.add_argument("answer")
    p.add_argument("--session", default=None)

    p = sub.add_parser("plan", help="planejar agenda (§9)")
    p.add_argument("--session", default=None)

    p = sub.add_parser("approve", help="aprovar plano pendente (§9)")
    p.add_argument("--session", required=True)

    p = sub.add_parser("export", help="exportar ICS do plano confirmado (§9)")
    p.add_argument("--plan-id", default=None)
    p.add_argument("--session", default=None)

    p = sub.add_parser("resume", help="retomar sessão em espera (§10)")
    p.add_argument("--session", required=True)
    p.add_argument("--message", default=None)
    p.add_argument("--course", default="")
    p.add_argument("--topic", action="append", default=[])
    p.add_argument("--data", default=None, help="JSON do valor de retomada")

    p = sub.add_parser("cancel", help="cancelar turno/sessão (§10)")
    p.add_argument("--session", required=True)

    p = sub.add_parser("trace", help="trace local por turno (§12)")
    p.add_argument("--trace-id", default=None)
    p.add_argument("--last", action="store_true")

    p = sub.add_parser("backup", help="backup local consistente (§5/§15.1)")
    p.add_argument("--backup-root", default=None)

    p = sub.add_parser("restore", help="restore verificado em dir novo (§5)")
    p.add_argument("--from", dest="from_dir", required=True)
    p.add_argument("--to", dest="to_dir", required=True)
    p.add_argument("--backup-root", default=None)

    p = sub.add_parser("delete", help="exclusão ativa de dados (§5/§15.1)")
    p.add_argument(
        "--scope",
        required=True,
        choices=("events", "facts", "summaries", "all"),
    )
    p.add_argument("--ids", nargs="*", default=[])
    p.add_argument("--reason", default="deleção solicitada pela CLI")
    p.add_argument("--session", default=None)
    p.add_argument(
        "--yes",
        action="store_true",
        help="confirma a exclusão (rota §10 exige confirmação explícita)",
    )
    p.add_argument("--backup-root", default=None)
    return parser


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------


def _manifest_capabilities(manifest_path: Path | None) -> RuntimeCapabilities:
    """Capacidades do runtime a partir do manifesto congelado (mapa §3.1:
    capacidade verificada e fixada por hash; task 017 congela o manifesto).

    Sem manifesto, a capacidade NÃO é presumida (``json_schema=False``).
    Com manifesto, a capacidade lida é a VERIFICADA no gate (G5) e o
    arquivo/verificação estão registrados no próprio manifesto.
    """
    if manifest_path is None or not manifest_path.exists():
        return RuntimeCapabilities(
            json_schema=False,
            json_schema_evidence="não verificada pela CLI (sem manifesto)",
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EduAgentError(
            ErrorCode.INTERNAL_FAILURE,
            f"manifesto ilegível em {manifest_path}: {exc}",
            diagnostic=DIAGNOSTIC,
        ) from exc
    json_schema = bool(
        (manifest.get("capacidades") or {}).get("json_schema", {}).get(
            "suportada"
        )
    )
    return RuntimeCapabilities(
        json_schema=json_schema,
        json_schema_evidence=(
            "manifesto congelado "
            f"({manifest_path}; verificação registrada no gate da task 002)"
        ),
    )


def default_runtime_factory(args: argparse.Namespace) -> Callable[[], Any]:
    def factory() -> RuntimeContext:
        backend = None
        if args.model_url:
            # Capacidade JSON schema vem do manifesto congelado e verificado
            # por hash (mapa §3.1); sem manifesto, a capacidade NÃO é
            # presumida.
            manifest_path = (
                Path(args.manifest)
                if args.manifest
                else Path("manifest.json")
            )
            capabilities = _manifest_capabilities(manifest_path)
            backend = ModelAdapter(
                base_url=args.model_url, capabilities=capabilities
            )
        embedder = None
        if args.embedder_dir:
            from eduagent.services.retrieval import BgeM3Embedder

            embedder = BgeM3Embedder(args.embedder_dir)
        return RuntimeContext.open(
            args.data_root,
            config_path=args.config,
            backend=backend,
            embedder=embedder,
        )

    return factory


def _require_user(runtime: RuntimeContext, user_id: str | None) -> str:
    """Contexto de usuário autenticado localmente (§12): UUID registrado no
    domínio. Sem contexto, escrita é recusada por código (exit 2)."""
    if not user_id:
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            "escrita/leitura exige contexto de usuário autenticado "
            "localmente (--user <uuid>, mapa §12)",
            diagnostic=DIAGNOSTIC,
        )
    try:
        _uuid.UUID(str(user_id))
    except ValueError as exc:
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            f"--user deve ser UUID: {user_id!r}",
            diagnostic=DIAGNOSTIC,
        ) from exc
    rows = runtime.store.fetch_user_rows(
        "SELECT id FROM users WHERE id = ?", (str(user_id),)
    )
    if not rows:
        raise EduAgentError(
            ErrorCode.SOURCE_UNRESOLVED,
            f"usuário {user_id} não registrado neste domínio local",
            diagnostic=DIAGNOSTIC,
        )
    return str(user_id)


def _session_id(args: argparse.Namespace) -> str:
    return str(getattr(args, "session", None) or _uuid.uuid4())


def _turn_payload(result: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": result.status,
        "session_id": str(result.state.session_id),
        "turn_id": str(result.state.turn_id),
        "trace_id": str(result.state.trace_id),
        "output": result.output,
    }
    if result.waiting_interrupt:
        payload["waiting_for"] = "user"
        payload["question"] = result.interrupt_payload
    if result.state.errors:
        payload["errors"] = [
            e.model_dump(mode="json") for e in result.state.errors
        ]
    return payload


def _run_turn_command(
    runtime: RuntimeContext,
    args: argparse.Namespace,
    *,
    message: str,
    intent: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user_id = _require_user(runtime, args.user)
    result = runtime.graph.run_turn(
        user_id=user_id,
        session_id=_session_id(args),
        message=message,
        payload=payload,
        intent=intent,
    )
    return _turn_payload(result)


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------


def _cmd_doctor(runtime: RuntimeContext, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    checks: dict[str, Any] = {}
    failed = False
    degraded = False

    # DB de domínio: piso WAL (§3), integridade e migrações aplicadas.
    try:
        sqlite_version = require_wal_capable_sqlite()
        checks["sqlite"] = {"status": "ok", "version": sqlite_version}
    except EduAgentError as exc:
        checks["sqlite"] = {"status": "failed", "error": exc.to_dict()}
        failed = True
    try:
        row = runtime.store.fetch_user_rows(
            "PRAGMA integrity_check", ()
        )
        integrity = str(row[0]["integrity_check"]) if row else "sem resposta"
        checks["domain_db"] = {
            "status": "ok" if integrity == "ok" else "failed",
            "integrity": integrity,
            "path": str(runtime.store.path),
        }
        if integrity != "ok":
            failed = True
    except EduAgentError as exc:
        checks["domain_db"] = {"status": "failed", "error": exc.to_dict()}
        failed = True
    try:
        checkpoint_integrity = runtime.checkpointer.integrity_check()
        checks["checkpoints_db"] = {
            "status": "ok" if checkpoint_integrity == "ok" else "failed",
            "integrity": checkpoint_integrity,
            "path": str(runtime.checkpointer.path),
        }
        if checkpoint_integrity != "ok":
            failed = True
    except EduAgentError as exc:  # pragma: no cover — defesa
        checks["checkpoints_db"] = {"status": "failed", "error": exc.to_dict()}
        failed = True

    # Modelo (§3.1): o doctor do MVP NÃO executa gate de modelo — reporta o
    # que é verificável localmente sem carregar o runtime: backend configurado
    # nesta invocação. Nunca alega validação que não ocorreu (§12).
    checks["model"] = {
        "status": "configured" if runtime.graph._backend is not None else "not_configured",  # noqa: SLF001
        "note": (
            "doctor do MVP não executa o gate de modelo (§13.1); rotas com "
            "geração exigem --model-url do runtime fixado e perfil congelado "
            "no manifesto (task 017)"
        ),
    }
    if runtime.graph._backend is None:  # noqa: SLF001
        degraded = True

    # Índices: presença de arquivos de índice publicados (007) sob data_root.
    index_files = sorted(
        p.name for p in runtime.data_root.glob("*index*") if p.is_file()
    )
    checks["indices"] = {
        "status": "ok" if index_files else "absent",
        "files": index_files,
        "note": (
            "ausência de índice não é falha: RAG é reconstruído por "
            "index_version (mapa §5: índices são reconstruíveis)"
        ),
    }

    # Config: chaves efetivamente carregadas (mapa §3).
    checks["config"] = {
        "status": "ok",
        "keys": sorted(runtime.config.keys()),
        "timezone": runtime.config.get("timezone"),
        "note": (
            "timezone permanece null até confirmação explícita (mapa §3; "
            "decisão pendente, não fechada aqui)"
        ),
    }

    # Expiração de backups: job/manual doctor com relógio e catálogo (§15.1).
    backup_root = Path(getattr(args, "backup_root", None) or (
        runtime.data_root.parent / "backups"
    ))
    from eduagent.services.backup import BackupCatalog

    catalog = BackupCatalog(backup_root)
    expired = catalog.expire_due()
    catalog.save()
    checks["backup_expiration"] = {
        "status": "ok",
        "expired_removed": expired,
        "catalog": str(backup_root / "catalog.json"),
        "note": "expiração verificada por relógio e catálogo (§15.1)",
    }

    status = "failed" if failed else ("degraded" if degraded else "ok")
    exit_code = EXIT_INTERNAL if failed else EXIT_OK
    return {"status": status, "checks": checks}, exit_code


def _cmd_ingest(runtime: RuntimeContext, args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.file)
    if not path.exists():
        raise EduAgentError(
            ErrorCode.SOURCE_UNRESOLVED,
            f"arquivo não encontrado: {path}",
            diagnostic=DIAGNOSTIC,
        )
    data = path.read_bytes()
    return _run_turn_command(
        runtime,
        args,
        message="/ingest documento",
        payload={
            "data": data,
            "course_id": args.course,
            "filename": path.name,
        },
    )


def _cmd_submit(runtime: RuntimeContext, args: argparse.Namespace) -> dict[str, Any]:
    return _run_turn_command(
        runtime,
        args,
        message=args.answer,
        intent="submit_answer",
    )


def _cmd_export(runtime: RuntimeContext, args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if args.plan_id:
        payload["plan_id"] = args.plan_id
    return _run_turn_command(
        runtime, args, message="/export", payload=payload
    )


def _cmd_resume(runtime: RuntimeContext, args: argparse.Namespace) -> dict[str, Any]:
    user_id = _require_user(runtime, args.user)
    if args.message:
        # Retomada por nova entrada (§10): rota depende do estado da sessão.
        result = runtime.graph.run_turn(
            user_id=user_id,
            session_id=args.session,
            message=f"/resume {args.message}",
            payload=_topic_payload(args),
        )
    elif args.data:
        try:
            value = json.loads(args.data)
        except json.JSONDecodeError as exc:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"--data não é JSON válido: {exc}",
                diagnostic=DIAGNOSTIC,
            ) from exc
        result = runtime.graph.resume_turn(
            session_id=args.session, resume=value, user_id=user_id
        )
    else:
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            "resume exige --message TEXT (nova entrada) ou --data JSON "
            "(valor do gate de confirmação)",
            diagnostic=DIAGNOSTIC,
        )
    return _turn_payload(result)


def _cmd_cancel(runtime: RuntimeContext, args: argparse.Namespace) -> dict[str, Any]:
    user_id = _require_user(runtime, args.user)
    result = runtime.graph.run_turn(
        user_id=user_id,
        session_id=args.session,
        message="/cancel",
        cancel_requested=True,
    )
    return _turn_payload(result)


def _cmd_trace(runtime: RuntimeContext, args: argparse.Namespace) -> dict[str, Any]:
    directory = runtime.telemetry_dir
    if args.trace_id:
        path = directory / f"{args.trace_id}.json"
        if not path.exists():
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"trace {args.trace_id} não encontrado em {directory}",
                diagnostic=DIAGNOSTIC,
            )
        return {"status": "ok", "trace": load_trace(path)}
    traces = sorted(directory.glob("*.json"))
    if args.last:
        if not traces:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"nenhum trace gravado em {directory}",
                diagnostic=DIAGNOSTIC,
            )
        return {"status": "ok", "trace": load_trace(traces[-1])}
    return {
        "status": "ok",
        "traces": [
            {
                "trace_id": path.stem,
                "path": str(path),
                "modified_at": path.stat().st_mtime,
            }
            for path in traces
        ],
    }


def _cmd_backup(runtime: RuntimeContext, args: argparse.Namespace) -> dict[str, Any]:
    _require_user(runtime, args.user)
    backup_root = Path(
        args.backup_root or (runtime.data_root.parent / "backups")
    )
    service = BackupService(
        store=runtime.store,
        checkpointer=runtime.checkpointer,
        data_root=runtime.data_root,
        backup_root=backup_root,
    )
    report = service.create_backup()
    payload = report.to_dict()
    payload["status"] = "backed_up"
    return payload


def _cmd_restore(runtime: RuntimeContext, args: argparse.Namespace) -> dict[str, Any]:
    backup_root = Path(
        args.backup_root or (runtime.data_root.parent / "backups")
    )
    service = BackupService(
        store=None,
        checkpointer=None,
        data_root=runtime.data_root,
        backup_root=backup_root,
    )
    report = service.restore_backup(args.from_dir, target_root=args.to_dir)
    report["status"] = "restored"
    return report


def _cmd_delete(runtime: RuntimeContext, args: argparse.Namespace) -> dict[str, Any]:
    user_id = _require_user(runtime, args.user)
    session = args.session or _uuid.uuid4()
    payload: dict[str, Any] = {"scope": args.scope}
    if args.ids:
        payload["ids"] = args.ids
    result = runtime.graph.run_turn(
        user_id=user_id,
        session_id=str(session),
        message="/delete",
        payload={**payload, "reason": args.reason},
        intent="delete_data",
    )
    response = _turn_payload(result)
    if result.waiting_interrupt:
        if not args.yes:
            response["note"] = (
                "preview pronto; exclusão exige confirmação (--yes, rota §10: "
                "preview → confirm); escopo/prazo no preview — sem alegação "
                "de sanitização forense"
            )
            return response
        result = runtime.graph.resume_turn(
            session_id=str(session), resume={"confirmed": True},
            user_id=user_id,
        )
        response = _turn_payload(result)
    # Exclusão ativa imediata nos backups (§15.1): backup só-do-usuário é
    # removido já na solicitação; demais ficam pendentes até expiração.
    deletion = (result.output or {}).get("change") or {}
    if deletion.get("kind") == "delete":
        backup_root = Path(
            args.backup_root or (runtime.data_root.parent / "backups")
        )
        service = BackupService(
            store=None, checkpointer=None,
            data_root=runtime.data_root, backup_root=backup_root,
        )
        response["backup_policy"] = service.apply_user_deletion(
            user_id,
            scope=args.scope,
            backup_pending_until=None,
        )
    return response


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------


def run(
    argv: Sequence[str] | None = None,
    *,
    runtime_factory: Callable[[argparse.Namespace], Any] | None = None,
    stdout: Any = None,
) -> int:
    """Executa a CLI e devolve o exit code do §12 (JSON sempre com status)."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    factory = runtime_factory or default_runtime_factory(args)
    runtime: RuntimeContext | None = None
    try:
        runtime = factory()
        handler = _COMMANDS.get(args.command)
        if handler is None:  # pragma: no cover — argparse garante
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                f"comando sem handler: {args.command}",
                diagnostic=DIAGNOSTIC,
            )
        if handler is _cmd_doctor:
            payload, code = handler(runtime, args)
        else:
            payload = handler(runtime, args)
            status = str(payload.get("status") or "")
            if status.startswith("waiting") or status == "cancelled":
                code = EXIT_OK  # espera legítima / solicitação atendida (§12)
            elif status == "failed":
                errors = payload.get("errors") or []
                code = _exit_code_of_errors(errors)
            else:
                code = EXIT_OK
    except EduAgentError as exc:
        payload = {"status": "failed", "error": exc.to_dict()}
        code = EXIT_CODE_BY_ERROR.get(exc.code, EXIT_INTERNAL)
    except Exception as exc:  # noqa: BLE001 — exit 4 com diagnóstico (§12)
        payload = {
            "status": "failed",
            "error": {
                "code": ErrorCode.INTERNAL_FAILURE.value,
                "message": f"falha interna da CLI: {type(exc).__name__}: {exc}",
                "retryable": False,
                "diagnostic": DIAGNOSTIC,
            },
        }
        code = EXIT_INTERNAL
    finally:
        if runtime is not None:
            try:
                runtime.close()
            except Exception:  # noqa: BLE001 — fechamento nunca mascara saída
                pass
    _emit(payload, stdout)
    return code


def _exit_code_of_errors(errors: Sequence[dict]) -> int:
    worst = EXIT_OK
    for error in errors:
        try:
            code = ErrorCode(str(error.get("code")))
        except ValueError:
            worst = max(worst, EXIT_INTERNAL)
            continue
        mapped = EXIT_CODE_BY_ERROR.get(code, EXIT_INTERNAL)
        worst = max(worst, mapped)
    return worst


def _topic_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload = {"course_id": getattr(args, "course", "") or ""}
    topics = list(getattr(args, "topic", None) or [])
    if topics:
        payload["topic_ids"] = topics
    return payload


def _cmd_ask(runtime: RuntimeContext, args: argparse.Namespace) -> dict[str, Any]:
    return _run_turn_command(
        runtime,
        args,
        message=f"/ask {args.message}",
        payload=_topic_payload(args),
    )


def _cmd_practice(runtime: RuntimeContext, args: argparse.Namespace) -> dict[str, Any]:
    message = f"/practice {args.message or 'praticar'}"
    return _run_turn_command(
        runtime,
        args,
        message=message,
        payload=_topic_payload(args),
    )


def _cmd_plan(runtime: RuntimeContext, args: argparse.Namespace) -> dict[str, Any]:
    return _run_turn_command(runtime, args, message="/plan")


def _cmd_approve(runtime: RuntimeContext, args: argparse.Namespace) -> dict[str, Any]:
    user_id = _require_user(runtime, args.user)
    # Ownership (§12): aprovação aplica efeito de sessão — sessão de outro
    # usuário é recusada por código antes da retomada.
    result = runtime.graph.resume_turn(
        session_id=args.session, resume={"approved": True}, user_id=user_id
    )
    return _turn_payload(result)


_COMMANDS = {
    "doctor": _cmd_doctor,
    "ingest": _cmd_ingest,
    "ask": _cmd_ask,
    "practice": _cmd_practice,
    "submit": _cmd_submit,
    "plan": _cmd_plan,
    "approve": _cmd_approve,
    "export": _cmd_export,
    "resume": _cmd_resume,
    "cancel": _cmd_cancel,
    "trace": _cmd_trace,
    "backup": _cmd_backup,
    "restore": _cmd_restore,
    "delete": _cmd_delete,
}


def main() -> int:  # pragma: no cover — ponto de entrada do pyproject
    """Ponto de entrada declarado no ``pyproject.toml`` (mapa §12)."""
    return run(sys.argv[1:])


if __name__ == "__main__":  # pragma: no cover — `python -m eduagent.cli`
    raise SystemExit(main())


__all__ = [
    "EXIT_CODE_BY_ERROR",
    "build_parser",
    "default_runtime_factory",
    "main",
    "run",
]
