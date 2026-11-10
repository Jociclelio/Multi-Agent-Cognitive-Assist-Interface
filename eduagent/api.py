"""API HTTP loopback (127.0.0.1) do EduAgent-OS v0.1 (§12 + Interface Gráfica Local).

Superfície finíssima sobre :class:`EduAgentGraph` e os serviços de domínio.
Nenhuma lógica de negócio vive aqui — os endpoints chamam os mesmos
caminhos da CLI:

- ``POST /turns`` — executa um turno contra ``graph.run_turn``.
- ``POST /turns/{session_id}/resume`` — retoma interrupção de confirmação.
- ``POST /turns/{session_id}/cancel`` — cancela sessão ativa.
- ``GET /artifacts/{id}`` — lê artefato exportado (ex.: ``.ics``) confinado
  a ``data/<user_id>/exports/``.
- ``GET /health`` — verificação rápida de prontidão do processo e gates.
- Endpoints de leitura e staging da Interface Gráfica Local (exigem
  ``X-EduAgent-User``):
  - ``GET /courses`` e ``POST /courses``
  - ``GET /courses/{course_id}/sessions`` e ``GET /sessions/{session_id}``
  - ``GET /operations``
  - ``GET /calendar``
  - ``GET /progress``
  - ``GET /library`` e ``POST /library/upload``
  - ``GET /review/flashcards``
  - ``GET /search?q=...``
- Entrega estática da SPA local em ``GET /`` e ``GET /ui/*`` a partir de
  ``ui/dist/``.

Todas as rotas de usuário exigem o cabeçalho ``X-EduAgent-User`` com UUID
canônico e validam que o usuário existe no ``DomainStore`` (§5). O servidor
recusa bind fora de ``127.0.0.1`` / ``localhost``.
"""

from __future__ import annotations

import argparse
import base64
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import pathlib
import re
import sqlite3
import sys
import threading
from typing import Any
from urllib.parse import parse_qs, urlparse
import uuid
import webbrowser

from eduagent.config import resolve_timezone, validate_iana_timezone
from eduagent.contracts import EduAgentError, ErrorCode, TypedError
from eduagent.graph import TurnResult
from eduagent.policy import resolve_owned_path
from eduagent.runtime import RuntimeContext

DIAGNOSTIC = "eduagent/api.py"

#: Porta default da API loopback (escolha de ensaio local; o 8079 é do
#: runtime do modelo, mapa §3.1).
DEFAULT_PORT = 8094

LOOPBACK_HOSTS: frozenset[str] = frozenset({"127.0.0.1", "localhost", "::1"})
AUTH_HEADER = "X-EduAgent-User"
USER_HEADER = AUTH_HEADER
MAX_BODY_BYTES = 64 * 1024 * 1024  # 64 MiB teto HTTP para acomodar envelope de upload de 50 MiB
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # §6.1: limite normativo de 50 MiB por documento

#: Mapa de erro tipado §4 → status HTTP do loopback.
HTTP_STATUS_BY_ERROR: dict[ErrorCode, int] = {
    ErrorCode.SCHEMA_INVALID: 400,
    ErrorCode.AMBIGUOUS_INPUT: 400,
    ErrorCode.SOURCE_UNRESOLVED: 404,
    ErrorCode.VERSION_CONFLICT: 409,
    ErrorCode.RESOURCE_LIMIT: 429,
    ErrorCode.TIMEOUT: 504,
    ErrorCode.TOOL_DENIED: 403,
    ErrorCode.MODEL_NOT_ADMITTED: 503,
    ErrorCode.NO_EVIDENCE: 422,
    ErrorCode.UNKNOWN_EFFECT: 500,
    ErrorCode.INTERNAL_FAILURE: 500,
    ErrorCode.CANCELLED: 200,
}

_SAFE_ARTIFACT_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._ -]{1,180}$")
_EVENT_REF_RE = re.compile(
    r"^event:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})@\d+$"
)

_UI_DIST_DIR = pathlib.Path(__file__).resolve().parent.parent / "ui" / "dist"
_STATIC_MIMES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


def _json_safe(value: Any) -> Any:
    if isinstance(value, TypedError):
        return value.model_dump(mode="json")
    if isinstance(value, EduAgentError):
        return value.to_dict()
    if isinstance(value, (bytes, bytearray)):
        return {"bytes_len": len(value)}
    if isinstance(value, pathlib.Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _serialize_turn(result: TurnResult, session_id: str | None = None) -> dict[str, Any]:
    sid = str(session_id or result.state.session_id)
    intent_val = (
        result.state.intent.value
        if hasattr(result.state.intent, "value")
        else str(result.state.intent)
    )
    payload: dict[str, Any] = {
        "status": result.status,
        "session_id": sid,
        "turn_id": str(result.state.turn_id),
        "trace_id": str(result.state.trace_id),
        "intent": intent_val,
        "output": _json_safe(result.output),
        "errors": [
            e.model_dump(mode="json") if hasattr(e, "model_dump") else _json_safe(e)
            for e in (result.state.errors or [])
        ],
        "interrupted": (
            _json_safe(result.interrupt_payload) if result.waiting_interrupt else None
        ),
    }
    if result.waiting_interrupt:
        payload["waiting_for"] = "user"
        payload["question"] = _json_safe(result.interrupt_payload)
    return payload


def _safe_json_loads(raw: str | None, default: Any = None) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return default


def _normalize_help_level(raw_val: Any) -> str:
    if raw_val is None:
        return "L0"
    if isinstance(raw_val, int):
        return f"L{max(0, min(3, raw_val))}"
    s = str(raw_val).strip().upper()
    if s in ("L0", "L1", "L2", "L3"):
        return s
    if s.isdigit():
        return f"L{max(0, min(3, int(s)))}"
    return "L0"


def _error_body(
    code: ErrorCode,
    message: str,
    *,
    retryable: bool | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    err_dict = EduAgentError(
        code=code,
        message=message,
        retryable=retryable,
        diagnostic=DIAGNOSTIC,
    ).to_dict()
    if details:
        err_dict["details"] = details
    return {"status": "failed", "error": err_dict}


def _compute_course_priority(
    course_row: sqlite3.Row,
    *,
    topics: list[dict[str, Any]],
    active_docs: list[dict[str, Any]],
    indexed_docs: list[dict[str, Any]],
    plan_blocks: list[dict[str, Any]],
    demands: list[dict[str, Any]],
    attempts_count: int,
    last_event: dict[str, Any] | None,
    topic_states: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calcula a ordenação determinística em 4 faixas (Decisão D3) e o sinal
    'Pronta para estudar' (Decisão D4) sem alterar o DDL SQLite.

    Faixas (menor ``sort_tier`` tem maior prioridade):
    1. ``scheduled_block``: curso possui bloco planejado ativo ou agendado;
    2. ``critical_demand``: curso possui demanda aberta (crítica/alta ou com
       data de vencimento);
    3. ``new_curation``: curso possui versão documental ativa/indexada ainda
       sem tentativas registradas (curadoria recém-concluída);
    4. ``inactivity_days``: demais cursos, ordenados pela menor atividade
       recente e pelo título.
    """
    topic_ids = {t["id"] for t in topics}
    course_id_str = str(course_row["id"])
    course_title_lower = str(course_row["title"]).lower()

    all_course_demand_ids = {
        d["id"]
        for d in demands
        if d.get("topic_id") in topic_ids
        or (d.get("payload") or {}).get("course_id") == course_id_str
    }
    course_demands = [
        d
        for d in demands
        if d.get("status") not in ("completed", "cancelled", "rejected")
        and d["id"] in all_course_demand_ids
    ]
    course_blocks = [
        b
        for b in plan_blocks
        if b.get("status") in ("planned", "started", "in_progress", "confirmed", "active")
        and (
            b.get("source_demand_id") in all_course_demand_ids
            or course_title_lower in (b.get("summary") or "").lower()
            or course_id_str.lower() in (b.get("summary") or "").lower()
            or course_id_str.lower() in (b.get("uid") or "").lower()
        )
    ]

    active_doc_count = len(active_docs)
    indexed_doc_count = len(indexed_docs)
    ready_to_study = bool(
        active_doc_count > 0
        or indexed_doc_count > 0
        or len(course_demands) > 0
        or len(course_blocks) > 0
    )

    active_block = course_blocks[0] if course_blocks else None
    if active_block is not None:
        sort_tier = 1
        sort_key_secondary = str(active_block.get("planned_start_utc") or "")
        sort_reason_label = "Na agenda de hoje"
        recommended_intent = "/practice"
    elif course_demands:
        sort_tier = 2
        due_dates = [
            str(d.get("due_local_date") or "9999-12-31")
            for d in course_demands
        ]
        sort_key_secondary = min(due_dates)
        sort_reason_label = f"{len(course_demands)} demanda(s) pendente(s)"
        recommended_intent = "/practice" if ready_to_study else "/plan"
    elif (active_doc_count > 0 or indexed_doc_count > 0) and attempts_count == 0:
        sort_tier = 3
        sort_key_secondary = "0000-00-00"
        sort_reason_label = "Novo material indexado p/ praticar"
        recommended_intent = "/practice"
    else:
        sort_tier = 4
        last_ts = str((last_event or {}).get("occurred_at") or "0000-00-00T00:00:00Z")
        sort_key_secondary = last_ts
        sort_reason_label = (
            "Retomar estudo" if ready_to_study else "Aguardando ingestão de material"
        )
        recommended_intent = "/ask" if ready_to_study else "/ingest"

    status_counts = {"insufficient": 0, "mixed": 0, "favorable": 0}
    for ts in topic_states:
        st = (ts.get("payload") or {}).get("status")
        if st in status_counts:
            status_counts[st] += 1

    overall_status = "insufficient"
    if (
        status_counts["favorable"] > 0
        and status_counts["insufficient"] == 0
        and status_counts["mixed"] == 0
    ):
        overall_status = "favorable"
    elif status_counts["favorable"] > 0 or status_counts["mixed"] > 0:
        overall_status = "mixed"

    last_preview = "Nenhuma interação registrada nesta disciplina."
    if last_event:
        ev_payload = last_event.get("payload") or {}
        last_preview = str(
            ev_payload.get("message")
            or ev_payload.get("text")
            or ev_payload.get("summary")
            or f"Evento: {last_event.get('kind')}"
        )[:120]

    return {
        "id": course_row["id"],
        "user_id": course_row["user_id"],
        "title": course_row["title"],
        "aliases": _safe_json_loads(course_row["aliases_json"], []),
        "revision": int(course_row["revision"]),
        "topics": topics,
        "active_doc_count": active_doc_count,
        "indexed_doc_count": indexed_doc_count,
        "ready_to_study": ready_to_study,
        "sort_tier": sort_tier,
        "sort_key_secondary": sort_key_secondary,
        "sort_reason_label": sort_reason_label,
        "recommended_intent": recommended_intent,
        "pending_demands_count": len(course_demands),
        "active_plan_block": active_block,
        "last_turn_preview": last_preview,
        "last_activity_at": (last_event or {}).get("occurred_at"),
        "domain_status": overall_status,
        "topic_states_summary": status_counts,
        "attempts_count": attempts_count,
    }


class LoopbackAPI:
    """Servidor HTTP loopback concorrente (``ThreadingHTTPServer``) para CLI/UI local."""

    def __init__(
        self,
        runtime: RuntimeContext,
        *,
        host: str = "127.0.0.1",
        port: int = DEFAULT_PORT,
        ui_dir: pathlib.Path | None = None,
    ) -> None:
        if host not in LOOPBACK_HOSTS:
            raise EduAgentError(
                ErrorCode.TOOL_DENIED,
                f"LoopbackAPI só aceita bind em loopback; recebido {host!r}",
                diagnostic=DIAGNOSTIC,
            )
        self.runtime = runtime
        self.context = runtime
        self.host = host
        self._host = host
        self.port = port
        self._port = port
        self.ui_dir = (ui_dir or _UI_DIST_DIR).resolve()
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def address(self) -> tuple[str, int]:
        if self._httpd is not None:
            addr = self._httpd.server_address
            return str(addr[0]), int(addr[1])
        return self.host, self.port

    @property
    def url(self) -> str:
        bound_host, bound_port = self.address
        return f"http://{bound_host}:{bound_port}"

    def _fetchall(
        self, sql: str, params: tuple[Any, ...] = ()
    ) -> list[sqlite3.Row]:
        return self.runtime.store.fetch_user_rows(sql, params)

    def _fetchone(
        self, sql: str, params: tuple[Any, ...] = ()
    ) -> sqlite3.Row | None:
        rows = self.runtime.store.fetch_user_rows(sql, params)
        return rows[0] if rows else None

    def start(self) -> tuple[str, int]:
        """Inicia o servidor concorrente em thread daemon e devolve ``(host, port)``."""
        if self._httpd is not None:
            return self.address
        api = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "EduAgentLoopback/0.1"

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                # Silencia logs por padrão (evita poluir stdout JSON da CLI).
                return

            def do_OPTIONS(self) -> None:  # noqa: N802
                self.send_response(int(HTTPStatus.NO_CONTENT))
                self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header(
                    "Access-Control-Allow-Headers",
                    f"Content-Type, {USER_HEADER}",
                )
                self.end_headers()

            def do_GET(self) -> None:  # noqa: N802
                api._handle_get(self)

            def do_POST(self) -> None:  # noqa: N802
                api._handle_post(self)

        self._httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        self._httpd.runtime = self.runtime  # type: ignore[attr-defined]
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            name="eduagent-loopback-api",
            daemon=True,
        )
        self._thread.start()
        return self.address

    def serve_forever(self) -> None:  # pragma: no cover
        self.start()
        assert self._httpd is not None
        self._httpd.serve_forever()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    # ------------------------------------------------------------------
    # Helpers HTTP e Banco
    # ------------------------------------------------------------------
    def _send_json(
        self,
        handler: BaseHTTPRequestHandler,
        status: HTTPStatus | int,
        body: dict[str, Any],
    ) -> None:
        raw = json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
        handler.send_response(int(status))
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(raw)))
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        handler.wfile.write(raw)

    def _send_static(
        self,
        handler: BaseHTTPRequestHandler,
        rel_path: str,
    ) -> None:
        if not self.ui_dir.exists():
            self._send_json(
                handler,
                HTTPStatus.NOT_FOUND,
                _error_body(
                    ErrorCode.SOURCE_UNRESOLVED,
                    "diretório ui/dist não encontrado",
                ),
            )
            return
        if ".." in rel_path.split("/") or ".." in rel_path.split("\\"):
            self._send_json(
                handler,
                HTTPStatus.FORBIDDEN,
                _error_body(ErrorCode.TOOL_DENIED, "caminho estático inválido (traversal bloqueado)"),
            )
            return
        clean = rel_path.lstrip("/") or "index.html"
        target = (self.ui_dir / clean).resolve()
        try:
            target.relative_to(self.ui_dir)
        except ValueError:
            self._send_json(
                handler,
                HTTPStatus.FORBIDDEN,
                _error_body(ErrorCode.TOOL_DENIED, "caminho estático inválido"),
            )
            return
        if not target.exists() or not target.is_file():
            self._send_json(
                handler,
                HTTPStatus.NOT_FOUND,
                _error_body(
                    ErrorCode.SOURCE_UNRESOLVED,
                    f"arquivo estático não encontrado: {clean}",
                ),
            )
            return
        mime = _STATIC_MIMES.get(target.suffix.lower(), "application/octet-stream")
        raw = target.read_bytes()
        handler.send_response(int(HTTPStatus.OK))
        handler.send_header("Content-Type", mime)
        handler.send_header("Content-Length", str(len(raw)))
        handler.send_header("Cache-Control", "no-cache")
        handler.end_headers()
        handler.wfile.write(raw)

    def _require_user(self, handler: BaseHTTPRequestHandler) -> str | None:
        raw = (handler.headers.get(USER_HEADER) or "").strip()
        if not raw:
            self._send_json(
                handler,
                HTTPStatus.BAD_REQUEST,
                _error_body(
                    ErrorCode.SCHEMA_INVALID,
                    f"escrita/leitura exige cabeçalho {USER_HEADER} obrigatório (sem default implícito)",
                ),
            )
            return None
        try:
            uid = str(uuid.UUID(raw))
        except ValueError:
            self._send_json(
                handler,
                HTTPStatus.BAD_REQUEST,
                _error_body(
                    ErrorCode.SCHEMA_INVALID,
                    f"{USER_HEADER} inválido: esperado UUID canônico",
                    details={"user_id": raw},
                ),
            )
            return None
        row = self._fetchone("SELECT id FROM users WHERE id = ?", (uid,))
        if row is None:
            self._send_json(
                handler,
                HTTPStatus.NOT_FOUND,
                _error_body(
                    ErrorCode.SOURCE_UNRESOLVED,
                    f"usuário {uid} não encontrado no DomainStore",
                    details={"user_id": uid},
                ),
            )
            return None
        return uid

    def _read_json_body(
        self, handler: BaseHTTPRequestHandler
    ) -> dict[str, Any] | None:
        length_raw = handler.headers.get("Content-Length", "0")
        try:
            length = int(length_raw)
        except ValueError:
            length = 0
        if length > MAX_BODY_BYTES:
            self._send_json(
                handler,
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                _error_body(
                    ErrorCode.RESOURCE_LIMIT,
                    f"corpo HTTP excede {MAX_BODY_BYTES} bytes",
                ),
            )
            return None
        if length <= 0:
            return {}
        raw = handler.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._send_json(
                handler,
                HTTPStatus.BAD_REQUEST,
                _error_body(
                    ErrorCode.SCHEMA_INVALID,
                    f"JSON inválido no corpo da requisição: {exc}",
                ),
            )
            return None
        if not isinstance(parsed, dict):
            self._send_json(
                handler,
                HTTPStatus.BAD_REQUEST,
                _error_body(
                    ErrorCode.SCHEMA_INVALID,
                    "corpo JSON deve ser um objeto",
                ),
            )
            return None
        return parsed

    def _resolve_item_answer_and_rubric(
        self,
        user_id: str,
        answer_ref_raw: str | None,
        rubric_ref_raw: str | None,
    ) -> tuple[Any, list[Any]]:
        ans_str = str(answer_ref_raw or "")
        rub_str = str(rubric_ref_raw or "")
        expected_answer: Any = None
        rubric_list: list[Any] | None = None

        ans_match = _EVENT_REF_RE.fullmatch(ans_str)
        if ans_match:
            ev_id = ans_match.group(1)
            ev_row = self._fetchone(
                "SELECT payload_json FROM events WHERE user_id = ? AND id = ?",
                (user_id, ev_id),
            )
            if ev_row and ev_row["payload_json"]:
                ev_payload = _safe_json_loads(ev_row["payload_json"], {}) or {}
                expected_answer = ev_payload.get("expected_answer")
                if isinstance(ev_payload.get("rubric"), list):
                    rubric_list = ev_payload.get("rubric")
        else:
            expected_answer = _safe_json_loads(ans_str, ans_str if ans_str else None)

        if rubric_list is None:
            rub_match = _EVENT_REF_RE.fullmatch(rub_str)
            if rub_match:
                rub_row = self._fetchone(
                    "SELECT payload_json FROM events WHERE user_id = ? AND id = ?",
                    (user_id, rub_match.group(1)),
                )
                if rub_row and rub_row["payload_json"]:
                    rub_payload = _safe_json_loads(rub_row["payload_json"], {}) or {}
                    if isinstance(rub_payload.get("rubric"), list):
                        rubric_list = rub_payload.get("rubric")
            if rubric_list is None:
                rubric_parsed = _safe_json_loads(rub_str, [])
                rubric_list = rubric_parsed if isinstance(rubric_parsed, list) else []

        return expected_answer, rubric_list

    def _build_health_payload(self) -> dict[str, Any]:
        cfg = self.runtime.config or {}
        model_admitted = bool(
            getattr(self.runtime.graph, "_tutor", None) is not None
            or getattr(self.runtime.graph, "_backend", None) is not None
            or (cfg.get("model") or {}).get("gguf_path")
        )
        user_rows = self._fetchall(
            "SELECT id, timezone, domain_revision FROM users ORDER BY id LIMIT 10"
        )
        primary_user = dict(user_rows[0]) if user_rows else None
        user_tz = (
            str(primary_user["timezone"])
            if primary_user and primary_user.get("timezone")
            else None
        )
        resolved_tz, tz_source = resolve_timezone(
            cfg.get("timezone"),
            user_tz=user_tz,
            auto_detect=True,
            prompt_fallback=False,
        )
        if resolved_tz and primary_user and not user_tz:
            try:
                self.runtime.store.execute_write(
                    str(primary_user["id"]),
                    [
                        (
                            "UPDATE users SET timezone = ? WHERE id = ?",
                            (resolved_tz, str(primary_user["id"])),
                        )
                    ],
                    bump_domain_revision=False,
                )
            except Exception:  # noqa: BLE001
                pass
        return {
            "status": "ok",
            "service": "eduagent-loopback",
            "mode": "MVP local single-threaded (mapa §1)",
            "gates": {
                "model_admitted": model_admitted,
                "model_status": "admitted" if model_admitted else "MODEL_NOT_ADMITTED",
                "model_label": (
                    getattr(
                        getattr(self.runtime.graph, "_backend", None), "label", None
                    )
                    if model_admitted
                    else None
                ),
                "timezone": resolved_tz,
                "timezone_source": tz_source,
                "timezone_needs_prompt": bool(resolved_tz is None),
                "network_enabled": bool(cfg.get("network_enabled", False)),
                "web_connector": (
                    "enabled"
                    if (cfg.get("web_search") or {}).get("enabled")
                    else "CONNECTOR_DISABLED"
                ),
                "calendar_sync_enabled": bool(
                    (cfg.get("calendar") or {}).get("remote_enabled", False)
                ),
                "reranker_enabled": bool(
                    (cfg.get("retrieval") or {}).get("reranker_enabled", False)
                ),
                "sqlite_version": sqlite3.sqlite_version,
                "domain_revision": (
                    int(primary_user["domain_revision"]) if primary_user else 0
                ),
                "ui_available": (self.ui_dir / "index.html").exists(),
                "registered_users": [str(r["id"]) for r in user_rows],
            },
        }

    def _handle_get(self, handler: BaseHTTPRequestHandler) -> None:
        raw_path = handler.path
        parsed = urlparse(raw_path)
        raw_unnormalized_path = parsed.path
        if "/ui/" in raw_unnormalized_path and ".." in raw_unnormalized_path:
            self._send_json(
                handler,
                HTTPStatus.FORBIDDEN,
                _error_body(
                    ErrorCode.TOOL_DENIED,
                    "traversal em rota estática bloqueado",
                ),
            )
            return

        path = raw_unnormalized_path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        try:
            if path == "/health":
                self._send_json(handler, HTTPStatus.OK, self._build_health_payload())
                return

            # Entrega estática da Interface Gráfica Local (GET / e GET /ui/*)
            if path in ("/", "/index.html"):
                self._send_static(handler, "index.html")
                return
            if path.startswith("/ui/"):
                rel = path[len("/ui/") :]
                self._send_static(handler, rel)
                return

            if path.startswith("/artifacts/"):
                user_id = self._require_user(handler)
                if user_id is None:
                    return
                artifact_id = path[len("/artifacts/") :]
                self._handle_get_artifact(handler, user_id, artifact_id)
                return

            if path == "/courses":
                user_id = self._require_user(handler)
                if user_id is None:
                    return
                self._handle_get_courses(handler, user_id)
                return

            if path.startswith("/courses/") and path.endswith("/sessions"):
                user_id = self._require_user(handler)
                if user_id is None:
                    return
                parts = path.strip("/").split("/")
                if len(parts) == 3 and parts[0] == "courses" and parts[2] == "sessions":
                    self._handle_get_course_sessions(handler, user_id, parts[1])
                    return

            if path.startswith("/sessions/"):
                user_id = self._require_user(handler)
                if user_id is None:
                    return
                session_id = path[len("/sessions/") :]
                self._handle_get_session_detail(handler, user_id, session_id)
                return

            if path == "/operations":
                user_id = self._require_user(handler)
                if user_id is None:
                    return
                self._handle_get_operations(handler, user_id)
                return

            if path == "/calendar":
                user_id = self._require_user(handler)
                if user_id is None:
                    return
                self._handle_get_calendar(handler, user_id)
                return

            if path == "/progress":
                user_id = self._require_user(handler)
                if user_id is None:
                    return
                self._handle_get_progress(handler, user_id)
                return

            if path == "/library":
                user_id = self._require_user(handler)
                if user_id is None:
                    return
                course_filter = (query.get("course_id") or [None])[0]
                self._handle_get_library(handler, user_id, course_id=course_filter)
                return

            if path == "/review/flashcards":
                user_id = self._require_user(handler)
                if user_id is None:
                    return
                course_filter = (query.get("course_id") or [None])[0]
                self._handle_get_flashcards(handler, user_id, course_id=course_filter)
                return

            if path == "/search":
                user_id = self._require_user(handler)
                if user_id is None:
                    return
                q = (query.get("q") or [""])[0]
                self._handle_get_search(handler, user_id, q)
                return

            self._send_json(
                handler,
                HTTPStatus.NOT_FOUND,
                _error_body(ErrorCode.SOURCE_UNRESOLVED, f"rota não encontrada: {path}"),
            )
        except EduAgentError as exc:
            self._send_json(
                handler,
                HTTP_STATUS_BY_ERROR.get(exc.code, 500),
                {"status": "failed", "error": exc.to_dict()},
            )
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                handler,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                _error_body(
                    ErrorCode.INTERNAL_FAILURE,
                    f"falha interna da API: {type(exc).__name__}: {exc}",
                ),
            )

    def _handle_get_artifact(
        self,
        handler: BaseHTTPRequestHandler,
        user_id: str,
        artifact_id: str,
    ) -> None:
        if not _SAFE_ARTIFACT_ID.match(artifact_id) or ".." in artifact_id or "/" in artifact_id:
            self._send_json(
                handler,
                HTTPStatus.BAD_REQUEST,
                _error_body(
                    ErrorCode.SCHEMA_INVALID,
                    "identificador de artefato inválido",
                    details={"artifact_id": artifact_id},
                ),
            )
            return
        rel = f"exports/{artifact_id}"
        rel_ics = rel if rel.endswith(".ics") else f"{rel}.ics"
        target = resolve_owned_path(self.runtime.data_root, user_id, rel)
        if not target.exists():
            target = resolve_owned_path(
                self.runtime.data_root, user_id, rel_ics
            )
        if not target.exists() or not target.is_file():
            self._send_json(
                handler,
                HTTPStatus.NOT_FOUND,
                _error_body(
                    ErrorCode.SOURCE_UNRESOLVED,
                    f"artefato {artifact_id} não encontrado em exports/",
                    details={"artifact_id": artifact_id},
                ),
            )
            return
        content = target.read_text(encoding="utf-8", errors="replace")
        self._send_json(
            handler,
            HTTPStatus.OK,
            {
                "status": "ok",
                "artifact": {
                    "id": artifact_id,
                    "path": str(target),
                    "kind": "ics" if target.suffix == ".ics" else "file",
                    "content": content,
                },
            },
        )

    def _handle_get_courses(
        self,
        handler: BaseHTTPRequestHandler,
        user_id: str,
    ) -> None:
        course_rows = self._fetchall(
            "SELECT id, user_id, title, aliases_json, revision FROM courses WHERE user_id = ?",
            (user_id,),
        )
        topic_rows = self._fetchall(
            """
            SELECT t.id, t.course_id, t.title, t.aliases_json, t.revision
            FROM topics t
            JOIN courses c ON c.id = t.course_id
            WHERE c.user_id = ?
            ORDER BY t.title
            """,
            (user_id,),
        )
        doc_rows = self._fetchall(
            """
            SELECT d.id, d.course_id, d.active_version,
                   v.id AS version_id, v.status AS version_status, v.original_ref
            FROM documents d
            LEFT JOIN doc_versions v ON v.doc_id = d.id AND v.user_id = d.user_id
            WHERE d.user_id = ?
            """,
            (user_id,),
        )
        demand_rows = self._fetchall(
            """
            SELECT id, topic_id, activity_kind, due_local_date, status, payload_json
            FROM demands
            WHERE user_id = ?
            """,
            (user_id,),
        )
        block_rows = self._fetchall(
            """
            SELECT id, uid, status, planned_start_utc, planned_end_utc,
                   source_demand_id, summary
            FROM logical_blocks
            WHERE user_id = ?
            ORDER BY planned_start_utc ASC
            """,
            (user_id,),
        )
        ts_rows = self._fetchall(
            "SELECT topic_id, revision, payload_json FROM topic_states WHERE user_id = ?",
            (user_id,),
        )
        attempt_rows = self._fetchall(
            """
            SELECT a.id, a.item_id, i.source_refs_json
            FROM attempts a
            LEFT JOIN items i ON i.id = a.item_id AND i.user_id = a.user_id
            WHERE a.user_id = ?
            """,
            (user_id,),
        )
        event_rows = self._fetchall(
            """
            SELECT id, session_id, kind, payload_json, occurred_at
            FROM events
            WHERE user_id = ? AND purged_at IS NULL
            ORDER BY occurred_at DESC
            LIMIT 200
            """,
            (user_id,),
        )

        topics_by_course: dict[str, list[dict[str, Any]]] = {}
        for tr in topic_rows:
            cid = str(tr["course_id"])
            topics_by_course.setdefault(cid, []).append(
                {
                    "id": str(tr["id"]),
                    "course_id": cid,
                    "title": str(tr["title"]),
                    "aliases": _safe_json_loads(tr["aliases_json"], []),
                    "revision": int(tr["revision"]),
                }
            )

        demands_list = [
            {
                "id": str(r["id"]),
                "topic_id": r["topic_id"],
                "activity_kind": r["activity_kind"],
                "due_local_date": r["due_local_date"],
                "status": r["status"],
                "payload": _safe_json_loads(r["payload_json"], {}),
            }
            for r in demand_rows
        ]
        blocks_list = [dict(r) for r in block_rows]
        ts_by_topic: dict[str, dict[str, Any]] = {
            str(r["topic_id"]): {
                "topic_id": str(r["topic_id"]),
                "revision": int(r["revision"]),
                "payload": _safe_json_loads(r["payload_json"], {}),
            }
            for r in ts_rows
        }
        events_parsed = [
            {
                "id": str(r["id"]),
                "session_id": str(r["session_id"]),
                "kind": str(r["kind"]),
                "payload": _safe_json_loads(r["payload_json"], {}),
                "occurred_at": str(r["occurred_at"]),
            }
            for r in event_rows
        ]

        courses_out: list[dict[str, Any]] = []
        for crow in course_rows:
            cid = str(crow["id"])
            ctopics = topics_by_course.get(cid, [])
            ctopic_ids = {t["id"] for t in ctopics}
            cdocs = [r for r in doc_rows if str(r["course_id"]) == cid]
            cdoc_ids = {str(r["id"]) for r in cdocs}
            active_docs = [
                dict(r)
                for r in cdocs
                if r["active_version"] is not None or r["version_status"] == "active"
            ]
            indexed_docs = [
                dict(r)
                for r in cdocs
                if r["version_status"] in ("indexed", "active")
            ]
            course_attempts = 0
            for ar in attempt_rows:
                srefs = _safe_json_loads(ar["source_refs_json"], [])
                if isinstance(srefs, list) and srefs:
                    if any(
                        isinstance(sr, dict)
                        and (
                            str(sr.get("doc_id") or "") in cdoc_ids
                            or str(sr.get("course_id") or "") == cid
                        )
                        for sr in srefs
                    ):
                        course_attempts += 1
                elif len(course_rows) == 1:
                    course_attempts += 1

            course_ts = [
                ts_by_topic[tid] for tid in ctopic_ids if tid in ts_by_topic
            ]
            course_events = [
                ev
                for ev in events_parsed
                if (ev["payload"] or {}).get("course_id") == cid
                or (ev["payload"] or {}).get("topic_id") in ctopic_ids
            ]
            last_ev = (
                course_events[0]
                if course_events
                else (events_parsed[0] if events_parsed and len(course_rows) == 1 else None)
            )
            courses_out.append(
                _compute_course_priority(
                    crow,
                    topics=ctopics,
                    active_docs=active_docs,
                    indexed_docs=indexed_docs,
                    plan_blocks=blocks_list,
                    demands=demands_list,
                    attempts_count=course_attempts,
                    last_event=last_ev,
                    topic_states=course_ts,
                )
            )

        courses_out.sort(
            key=lambda c: (
                int(c["sort_tier"]),
                str(c["sort_key_secondary"]),
                str(c["title"]).lower(),
            )
        )
        self._send_json(
            handler,
            HTTPStatus.OK,
            {
                "status": "ok",
                "courses": courses_out,
                "total": len(courses_out),
            },
        )

    def _handle_post_courses(
        self,
        handler: BaseHTTPRequestHandler,
        user_id: str,
        body: dict[str, Any],
    ) -> None:
        title = str(body.get("title") or "").strip()
        if not title:
            self._send_json(
                handler,
                HTTPStatus.BAD_REQUEST,
                _error_body(
                    ErrorCode.SCHEMA_INVALID,
                    "campo 'title' é obrigatório para criar disciplina",
                ),
            )
            return
        raw_course_id = body.get("course_id") or body.get("id")
        if raw_course_id:
            try:
                course_id = str(uuid.UUID(str(raw_course_id)))
            except ValueError:
                self._send_json(
                    handler,
                    HTTPStatus.BAD_REQUEST,
                    _error_body(
                        ErrorCode.SCHEMA_INVALID,
                        "course_id deve ser um UUID canônico",
                    ),
                )
                return
        else:
            course_id = str(uuid.uuid4())

        aliases = body.get("aliases") if isinstance(body.get("aliases"), list) else []
        topics_in = body.get("topics") if isinstance(body.get("topics"), list) else []
        statements: list[tuple[str, tuple[Any, ...]]] = [
            (
                "INSERT INTO courses(id, user_id, title, aliases_json, revision) "
                "VALUES (?, ?, ?, ?, 1) "
                "ON CONFLICT(id) DO UPDATE SET title = excluded.title, "
                "aliases_json = excluded.aliases_json, revision = courses.revision + 1",
                (course_id, user_id, title, json.dumps(aliases, ensure_ascii=False)),
            )
        ]
        created_topics: list[dict[str, Any]] = []
        for idx, t_entry in enumerate(topics_in):
            if isinstance(t_entry, str):
                t_title = t_entry.strip()
                t_id = str(uuid.uuid4())
            elif isinstance(t_entry, dict):
                t_title = str(t_entry.get("title") or f"Tópico {idx + 1}").strip()
                t_id = str(t_entry.get("id") or uuid.uuid4())
            else:
                continue
            if not t_title:
                continue
            statements.append(
                (
                    "INSERT INTO topics(id, course_id, title, aliases_json, revision) "
                    "VALUES (?, ?, ?, '[]', 1) "
                    "ON CONFLICT(id) DO UPDATE SET title = excluded.title",
                    (t_id, course_id, t_title),
                )
            )
            created_topics.append({"id": t_id, "course_id": course_id, "title": t_title})

        if not created_topics and body.get("create_default_topic", True):
            default_tid = str(uuid.uuid4())
            statements.append(
                (
                    "INSERT INTO topics(id, course_id, title, aliases_json, revision) "
                    "VALUES (?, ?, ?, '[]', 1)",
                    (default_tid, course_id, f"Fundamentos de {title}"),
                )
            )
            created_topics.append(
                {
                    "id": default_tid,
                    "course_id": course_id,
                    "title": f"Fundamentos de {title}",
                }
            )

        self.runtime.store.execute_write(
            user_id,
            statements,
            bump_domain_revision=True,
        )
        self._send_json(
            handler,
            HTTPStatus.OK,
            {
                "status": "ok",
                "course": {
                    "id": course_id,
                    "user_id": user_id,
                    "title": title,
                    "aliases": aliases,
                    "topics": created_topics,
                },
            },
        )

    def _handle_get_course_sessions(
        self,
        handler: BaseHTTPRequestHandler,
        user_id: str,
        course_id: str,
    ) -> None:
        rows = self._fetchall(
            """
            SELECT session_id, COUNT(*) AS event_count,
                   MIN(occurred_at) AS started_at,
                   MAX(occurred_at) AS last_event_at
            FROM events
            WHERE user_id = ? AND purged_at IS NULL
            GROUP BY session_id
            ORDER BY last_event_at DESC
            """,
            (user_id,),
        )
        sessions = [
            {
                "session_id": str(r["session_id"]),
                "course_id": course_id,
                "event_count": int(r["event_count"]),
                "started_at": str(r["started_at"]),
                "last_event_at": str(r["last_event_at"]),
            }
            for r in rows
        ]
        self._send_json(
            handler,
            HTTPStatus.OK,
            {"status": "ok", "course_id": course_id, "sessions": sessions},
        )

    def _handle_get_session_detail(
        self,
        handler: BaseHTTPRequestHandler,
        user_id: str,
        session_id: str,
    ) -> None:
        event_rows = self._fetchall(
            """
            SELECT id, session_id, kind, payload_json, occurred_at, recorded_at
            FROM events
            WHERE user_id = ? AND session_id = ? AND purged_at IS NULL
            ORDER BY occurred_at ASC, recorded_at ASC
            """,
            (user_id, session_id),
        )
        events = []
        for r in event_rows:
            ev_payload = _safe_json_loads(r["payload_json"], {})
            if isinstance(ev_payload, dict) and r["kind"] == "item_published":
                ev_payload = {
                    k: v for k, v in ev_payload.items() if k != "expected_answer"
                }
            events.append(
                {
                    "id": str(r["id"]),
                    "session_id": str(r["session_id"]),
                    "kind": str(r["kind"]),
                    "payload": ev_payload,
                    "occurred_at": str(r["occurred_at"]),
                }
            )

        # Recupera itens e tentativas do usuário sem vazar gabarito quando revealed=0 (§7.3)
        item_rows = self._fetchall(
            """
            SELECT i.id, i.family_id, i.version, i.prompt, i.answer_ref,
                   i.rubric_ref, i.source_refs_json,
                   a.id AS attempt_id, a.help_level, a.revealed, a.attempt_ordinal, a.independent
            FROM items i
            LEFT JOIN attempts a ON a.item_id = i.id AND a.user_id = i.user_id
            WHERE i.user_id = ?
            ORDER BY i.rowid DESC
            LIMIT 30
            """,
            (user_id,),
        )
        items_out: list[dict[str, Any]] = []
        for ir in item_rows:
            revealed = bool(ir["revealed"])
            help_level = _normalize_help_level(ir["help_level"])
            answer_data, rubric_data = self._resolve_item_answer_and_rubric(
                user_id, ir["answer_ref"], ir["rubric_ref"]
            )
            # Invariante Fail-Closed: NUNCA expor expected_answer antes de L3 ou revealed=True
            safe_answer = answer_data if (revealed or help_level == "L3") else None
            items_out.append(
                {
                    "id": str(ir["id"]),
                    "family_id": str(ir["family_id"]),
                    "version": int(ir["version"]),
                    "prompt": str(ir["prompt"]),
                    "help_level": help_level,
                    "revealed": revealed,
                    "expected_answer": safe_answer,
                    "rubric": rubric_data,
                    "source_refs": _safe_json_loads(ir["source_refs_json"], []),
                    "attempt_id": ir["attempt_id"],
                    "attempt_ordinal": ir["attempt_ordinal"],
                    "independent": (
                        bool(ir["independent"])
                        if ir["independent"] is not None
                        else (help_level in ("L0", "L1") and not revealed)
                    ),
                }
            )

        assessment_rows = self._fetchall(
            """
            SELECT id, attempt_id, assessor_version, payload_json, assessment_revision
            FROM assessments
            WHERE attempt_user_id = ?
            ORDER BY assessment_revision DESC
            LIMIT 20
            """,
            (user_id,),
        )
        assessments_out = [
            {
                "id": str(r["id"]),
                "attempt_id": str(r["attempt_id"]),
                "assessor_version": str(r["assessor_version"]),
                "revision": int(r["assessment_revision"]),
                "payload": _safe_json_loads(r["payload_json"], {}),
            }
            for r in assessment_rows
        ]

        # Chunks recentes como EvidencePack auditável para a gaveta direita
        chunk_rows = self._fetchall(
            """
            SELECT c.id, c.version_id, c.block_refs_json, c.text,
                   v.doc_id, v.original_ref, v.status AS version_status
            FROM chunks c
            JOIN doc_versions v ON v.id = c.version_id AND v.user_id = c.user_id
            WHERE c.user_id = ?
            ORDER BY c.rowid DESC
            LIMIT 15
            """,
            (user_id,),
        )
        evidence_chunks = [
            {
                "chunk_id": str(r["id"]),
                "doc_id": str(r["doc_id"]),
                "version_id": str(r["version_id"]),
                "original_ref": str(r["original_ref"]),
                "version_status": str(r["version_status"]),
                "block_refs": _safe_json_loads(r["block_refs_json"], []),
                "text": str(r["text"]),
            }
            for r in chunk_rows
        ]

        checkpoint = None
        try:
            tup = self.runtime.checkpointer.get_tuple(
                {"configurable": {"thread_id": session_id}}
            )
            if tup is not None:
                cp_values = (tup.checkpoint or {}).get("channel_values") or {}
                checkpoint = {
                    "step": (tup.metadata or {}).get("step") if tup.metadata else None,
                    "status": cp_values.get("status"),
                    "interrupted": _json_safe(cp_values.get("pending_question")),
                }
        except Exception:  # noqa: BLE001
            checkpoint = None

        self._send_json(
            handler,
            HTTPStatus.OK,
            {
                "status": "ok",
                "session_id": session_id,
                "events": events,
                "items": items_out,
                "assessments": assessments_out,
                "evidence_pack": {
                    "coverage": "sufficient" if evidence_chunks else "insufficient",
                    "chunks": evidence_chunks,
                },
                "checkpoint": checkpoint,
            },
        )

    def _handle_get_operations(
        self,
        handler: BaseHTTPRequestHandler,
        user_id: str,
    ) -> None:
        op_rows = self._fetchall(
            """
            SELECT id, digest, state, expected_version, receipt_json
            FROM operations
            WHERE user_id = ?
            ORDER BY rowid DESC
            LIMIT 50
            """,
            (user_id,),
        )
        fact_rows = self._fetchall(
            """
            SELECT id, kind, value_json, authority, recorded_at, status, revision
            FROM facts
            WHERE user_id = ? AND status IN ('candidate', 'ambiguous')
            ORDER BY recorded_at DESC
            """,
            (user_id,),
        )
        plan_rows = self._fetchall(
            """
            SELECT id, revision, snapshot_version, payload_json, approval_ref
            FROM plans
            WHERE user_id = ? AND approval_ref IS NULL
            ORDER BY revision DESC
            """,
            (user_id,),
        )
        conf_rows = self._fetchall(
            """
            SELECT id, artifact_id, artifact_revision, digest, occurred_at
            FROM confirmations
            WHERE user_id = ?
            ORDER BY occurred_at DESC
            LIMIT 30
            """,
            (user_id,),
        )

        operations = [
            {
                "id": str(r["id"]),
                "digest": str(r["digest"]),
                "state": str(r["state"]),
                "expected_version": r["expected_version"],
                "receipt": _safe_json_loads(r["receipt_json"], {}),
            }
            for r in op_rows
        ]
        pending_facts = [
            {
                "id": str(r["id"]),
                "kind": str(r["kind"]),
                "value": _safe_json_loads(r["value_json"], {}),
                "authority": str(r["authority"]),
                "recorded_at": str(r["recorded_at"]),
                "status": str(r["status"]),
                "revision": int(r["revision"]),
            }
            for r in fact_rows
        ]
        unapproved_plans = [
            {
                "id": str(r["id"]),
                "revision": int(r["revision"]),
                "snapshot_version": int(r["snapshot_version"]),
                "payload": _safe_json_loads(r["payload_json"], {}),
                "approval_ref": r["approval_ref"],
            }
            for r in plan_rows
        ]
        confirmations = [dict(r) for r in conf_rows]
        pending_ops = [op for op in operations if op["state"] not in ("committed", "completed")]
        pending_count = len(pending_ops) + len(pending_facts) + len(unapproved_plans)

        self._send_json(
            handler,
            HTTPStatus.OK,
            {
                "status": "ok",
                "pending_count": pending_count,
                "operations": operations,
                "pending_facts": pending_facts,
                "unapproved_plans": unapproved_plans,
                "confirmations": confirmations,
            },
        )

    def _handle_get_calendar(
        self,
        handler: BaseHTTPRequestHandler,
        user_id: str,
    ) -> None:
        demand_rows = self._fetchall(
            """
            SELECT id, topic_id, activity_kind, due_local_date, status, revision, payload_json
            FROM demands
            WHERE user_id = ?
            ORDER BY COALESCE(due_local_date, '9999-12-31') ASC
            """,
            (user_id,),
        )
        plan_rows = self._fetchall(
            """
            SELECT id, revision, snapshot_version, payload_json, approval_ref
            FROM plans
            WHERE user_id = ?
            ORDER BY revision DESC
            LIMIT 10
            """,
            (user_id,),
        )
        block_rows = self._fetchall(
            """
            SELECT id, uid, revision, status, planned_start_utc, planned_end_utc,
                   actual_start_utc, actual_end_utc, source_demand_id,
                   end_conflict, summary
            FROM logical_blocks
            WHERE user_id = ?
            ORDER BY planned_start_utc ASC
            """,
            (user_id,),
        )
        exports_list: list[dict[str, Any]] = []
        try:
            exports_dir = resolve_owned_path(self.runtime.data_root, user_id, "exports")
            if exports_dir.exists() and exports_dir.is_dir():
                for f in sorted(exports_dir.glob("*.ics")):
                    exports_list.append(
                        {
                            "id": f.stem,
                            "filename": f.name,
                            "size_bytes": f.stat().st_size,
                        }
                    )
        except EduAgentError:
            pass

        demands = [
            {
                "id": str(r["id"]),
                "topic_id": r["topic_id"],
                "activity_kind": r["activity_kind"],
                "due_local_date": r["due_local_date"],
                "status": str(r["status"]),
                "revision": int(r["revision"]),
                "payload": _safe_json_loads(r["payload_json"], {}),
            }
            for r in demand_rows
        ]
        plans = [
            {
                "id": str(r["id"]),
                "revision": int(r["revision"]),
                "snapshot_version": int(r["snapshot_version"]),
                "payload": _safe_json_loads(r["payload_json"], {}),
                "approval_ref": r["approval_ref"],
            }
            for r in plan_rows
        ]
        blocks = [dict(r) for r in block_rows]

        self._send_json(
            handler,
            HTTPStatus.OK,
            {
                "status": "ok",
                "demands": demands,
                "plans": plans,
                "active_plan": plans[0] if plans else None,
                "logical_blocks": blocks,
                "exports": exports_list,
            },
        )

    def _handle_get_progress(
        self,
        handler: BaseHTTPRequestHandler,
        user_id: str,
    ) -> None:
        rows = self._fetchall(
            """
            SELECT t.id AS topic_id, t.title AS topic_title,
                   c.id AS course_id, c.title AS course_title,
                   ts.revision AS state_revision, ts.payload_json
            FROM topics t
            JOIN courses c ON c.id = t.course_id
            LEFT JOIN topic_states ts ON ts.topic_id = t.id AND ts.user_id = c.user_id
            WHERE c.user_id = ?
            ORDER BY c.title ASC, t.title ASC
            """,
            (user_id,),
        )
        attempt_rows = self._fetchall(
            """
            SELECT id, item_id, help_level, revealed, independent
            FROM attempts
            WHERE user_id = ?
            """,
            (user_id,),
        )
        topics_progress: list[dict[str, Any]] = []
        counts = {"insufficient": 0, "mixed": 0, "favorable": 0}
        for r in rows:
            payload = _safe_json_loads(r["payload_json"], {}) or {}
            status = str(payload.get("status") or "insufficient")
            if status not in counts:
                status = "insufficient"
            counts[status] += 1
            topics_progress.append(
                {
                    "topic_id": str(r["topic_id"]),
                    "topic_title": str(r["topic_title"]),
                    "course_id": str(r["course_id"]),
                    "course_title": str(r["course_title"]),
                    "revision": int(r["state_revision"] or 0),
                    "status": status,
                    # Invariante §8.1: estimate numérico permanece SEMPRE null na v0.1
                    "estimate": None,
                    "rationale": payload.get(
                        "rationale",
                        "Sem evidência independente suficiente acumulada neste tópico.",
                    ),
                    "critical_errors": payload.get("critical_errors", []),
                    "independent_attempts": int(payload.get("independent_attempts", 0)),
                    "assisted_attempts": int(payload.get("assisted_attempts", 0)),
                }
            )

        independent_total = sum(1 for a in attempt_rows if a["independent"])
        assisted_total = sum(1 for a in attempt_rows if not a["independent"])
        self._send_json(
            handler,
            HTTPStatus.OK,
            {
                "status": "ok",
                "summary": {
                    "counts_by_status": counts,
                    "total_topics": len(topics_progress),
                    "total_attempts": len(attempt_rows),
                    "independent_attempts": independent_total,
                    "assisted_attempts": assisted_total,
                    "estimate": None,
                },
                "topics": topics_progress,
            },
        )

    def _handle_get_library(
        self,
        handler: BaseHTTPRequestHandler,
        user_id: str,
        *,
        course_id: str | None = None,
    ) -> None:
        if course_id:
            doc_rows = self._fetchall(
                """
                SELECT d.id AS doc_id, d.course_id, d.active_version,
                       c.title AS course_title,
                       v.id AS version_id, v.sha256, v.mime, v.original_ref,
                       v.extractor_manifest, v.status AS version_status
                FROM documents d
                JOIN courses c ON c.id = d.course_id
                LEFT JOIN doc_versions v ON v.doc_id = d.id AND v.user_id = d.user_id
                WHERE d.user_id = ? AND d.course_id = ?
                ORDER BY d.rowid DESC
                """,
                (user_id, course_id),
            )
        else:
            doc_rows = self._fetchall(
                """
                SELECT d.id AS doc_id, d.course_id, d.active_version,
                       c.title AS course_title,
                       v.id AS version_id, v.sha256, v.mime, v.original_ref,
                       v.extractor_manifest, v.status AS version_status
                FROM documents d
                JOIN courses c ON c.id = d.course_id
                LEFT JOIN doc_versions v ON v.doc_id = d.id AND v.user_id = d.user_id
                WHERE d.user_id = ?
                ORDER BY d.rowid DESC
                """,
                (user_id,),
            )

        chunk_counts_rows = self._fetchall(
            """
            SELECT version_id, COUNT(*) AS chunk_count
            FROM chunks
            WHERE user_id = ?
            GROUP BY version_id
            """,
            (user_id,),
        )
        chunk_counts = {
            str(r["version_id"]): int(r["chunk_count"]) for r in chunk_counts_rows
        }

        documents = [
            {
                "doc_id": str(r["doc_id"]),
                "course_id": str(r["course_id"]),
                "course_title": str(r["course_title"]),
                "active_version": r["active_version"],
                "version_id": r["version_id"],
                "sha256": r["sha256"],
                "mime": r["mime"],
                "original_ref": r["original_ref"],
                "version_status": (
                    "active"
                    if (
                        r["active_version"] is not None
                        and r["version_id"] is not None
                        and str(r["active_version"]) == str(r["version_id"])
                    )
                    else (r["version_status"] or "pending")
                ),
                "chunk_count": chunk_counts.get(str(r["version_id"]), 0),
                "extractor_manifest": _safe_json_loads(r["extractor_manifest"], {}),
            }
            for r in doc_rows
        ]

        fact_rows = self._fetchall(
            """
            SELECT id, kind, value_json, authority, recorded_at, source_refs_json, status, revision
            FROM facts
            WHERE user_id = ?
            ORDER BY recorded_at DESC
            LIMIT 50
            """,
            (user_id,),
        )
        facts = [
            {
                "id": str(r["id"]),
                "kind": str(r["kind"]),
                "value": _safe_json_loads(r["value_json"], {}),
                "authority": str(r["authority"]),
                "recorded_at": str(r["recorded_at"]),
                "source_refs": _safe_json_loads(r["source_refs_json"], []),
                "status": str(r["status"]),
                "revision": int(r["revision"]),
            }
            for r in fact_rows
        ]

        self._send_json(
            handler,
            HTTPStatus.OK,
            {
                "status": "ok",
                "documents": documents,
                "facts": facts,
            },
        )

    def _handle_post_library_upload(
        self,
        handler: BaseHTTPRequestHandler,
        user_id: str,
        body: dict[str, Any],
    ) -> None:
        raw_filename = str(body.get("filename") or "").strip()
        if (
            not raw_filename
            or "/" in raw_filename
            or "\\" in raw_filename
            or ".." in raw_filename
            or not _SAFE_FILENAME.match(raw_filename)
        ):
            self._send_json(
                handler,
                HTTPStatus.FORBIDDEN,
                _error_body(
                    ErrorCode.TOOL_DENIED,
                    "nome de arquivo inválido ou fora do confinamento permitido",
                    details={"filename": raw_filename},
                ),
            )
            return

        content_b64 = body.get("content_base64")
        content_text = body.get("content_text")
        if isinstance(content_b64, str):
            try:
                raw_bytes = base64.b64decode(content_b64, validate=True)
            except Exception as exc:  # noqa: BLE001
                self._send_json(
                    handler,
                    HTTPStatus.BAD_REQUEST,
                    _error_body(
                        ErrorCode.SCHEMA_INVALID,
                        f"content_base64 inválido: {exc}",
                    ),
                )
                return
        elif isinstance(content_text, str):
            raw_bytes = content_text.encode("utf-8")
        else:
            self._send_json(
                handler,
                HTTPStatus.BAD_REQUEST,
                _error_body(
                    ErrorCode.SCHEMA_INVALID,
                    "forneça 'content_base64' ou 'content_text'",
                ),
            )
            return

        if len(raw_bytes) > MAX_UPLOAD_BYTES:
            self._send_json(
                handler,
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                _error_body(
                    ErrorCode.RESOURCE_LIMIT,
                    f"documento excede o limite de 50 MiB ({len(raw_bytes)} bytes)",
                    details={"size_bytes": len(raw_bytes), "max_bytes": MAX_UPLOAD_BYTES},
                ),
            )
            return

        target = resolve_owned_path(
            self.runtime.data_root, user_id, f"originals/{raw_filename}"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw_bytes)

        ingest_result_serialized: dict[str, Any] | None = None
        if body.get("auto_ingest") and body.get("course_id"):
            session_id = str(body.get("session_id") or uuid.uuid4())
            turn_res = self.runtime.graph.run_turn(
                user_id=user_id,
                session_id=session_id,
                message=f"/ingest {raw_filename}",
                payload={
                    "data": raw_bytes,
                    "course_id": str(body["course_id"]),
                    "filename": raw_filename,
                },
            )
            idx_info = (turn_res.output or {}).get("index") or {}
            doc_id = idx_info.get("doc_id")
            version_id = idx_info.get("version_id")
            if (
                turn_res.status == "completed"
                and doc_id
                and version_id
                and idx_info.get("version_status") == "indexed"
            ):
                retrieval = getattr(self.runtime, "retrieval", None) or getattr(
                    self.runtime.graph, "_retrieval", None
                )
                embedder = getattr(self.runtime.graph, "_embedder", None)
                ingestion = getattr(self.runtime, "ingestion", None) or getattr(
                    self.runtime.graph, "_ingestion", None
                )
                if retrieval is not None and embedder is not None:
                    try:
                        retrieval.index_version(
                            user_id, str(doc_id), str(version_id), embedder=embedder
                        )
                    except Exception:  # noqa: BLE001
                        pass
                if ingestion is not None and body.get("activate", True):
                    try:
                        ingestion.activate_version(
                            user_id, str(doc_id), str(version_id)
                        )
                    except Exception:  # noqa: BLE001
                        pass
            ingest_result_serialized = _serialize_turn(turn_res, session_id)

        self._send_json(
            handler,
            HTTPStatus.OK,
            {
                "status": "ok",
                "saved_path": str(target),
                "size_bytes": len(raw_bytes),
                "ingested": bool(
                    ingest_result_serialized
                    and ingest_result_serialized.get("status") == "completed"
                ),
                "upload": {
                    "filename": raw_filename,
                    "stored_path": str(target),
                    "relative_ref": f"originals/{raw_filename}",
                    "size_bytes": len(raw_bytes),
                },
                "ingest_turn": ingest_result_serialized,
            },
        )

    def _handle_get_flashcards(
        self,
        handler: BaseHTTPRequestHandler,
        user_id: str,
        *,
        course_id: str | None = None,
    ) -> None:
        item_rows = self._fetchall(
            """
            SELECT i.id, i.family_id, i.prompt, i.answer_ref, i.rubric_ref, i.source_refs_json,
                   a.help_level, a.revealed
            FROM items i
            LEFT JOIN attempts a ON a.item_id = i.id AND a.user_id = i.user_id
            WHERE i.user_id = ?
            ORDER BY i.rowid DESC
            LIMIT 40
            """,
            (user_id,),
        )
        chunk_rows = self._fetchall(
            """
            SELECT c.id, c.text, v.doc_id, d.course_id, co.title AS course_title
            FROM chunks c
            JOIN doc_versions v ON v.id = c.version_id AND v.user_id = c.user_id
            JOIN documents d ON d.id = v.doc_id AND d.user_id = c.user_id
            JOIN courses co ON co.id = d.course_id
            WHERE c.user_id = ?
            ORDER BY c.rowid DESC
            LIMIT 25
            """,
            (user_id,),
        )

        cards: list[dict[str, Any]] = []
        for ir in item_rows:
            answer_data, rubric = self._resolve_item_answer_and_rubric(
                user_id, ir["answer_ref"], ir["rubric_ref"]
            )
            source_refs = _safe_json_loads(ir["source_refs_json"], [])
            # Separação estrita Frente/Verso: o verso sintetiza os critérios públicos
            # da rubrica e só inclui gabarito literal se o item já tiver sido revelado.
            revealed = bool(ir["revealed"])
            help_level = _normalize_help_level(ir["help_level"])
            criteria_summary = "; ".join(
                str(c.get("description") or "")
                for c in (rubric if isinstance(rubric, list) else [])
                if isinstance(c, dict) and c.get("description")
            )
            back_content = (
                str(answer_data)
                if (revealed or help_level == "L3") and answer_data is not None
                else (
                    criteria_summary
                    or "Verifique sua explicação contra a fonte citada antes de revelar a resposta completa no modo Prática."
                )
            )
            cards.append(
                {
                    "id": f"card-item-{ir['id']}",
                    "kind": "item_review",
                    "front": str(ir["prompt"]),
                    "back": back_content,
                    "revealed": revealed or help_level == "L3",
                    "source_refs": source_refs,
                    "course_id": course_id,
                }
            )

        for cr in chunk_rows:
            if course_id and str(cr["course_id"]) != course_id:
                continue
            text = str(cr["text"]).strip()
            if not text:
                continue
            cards.append(
                {
                    "id": f"card-chunk-{cr['id']}",
                    "kind": "concept_recall",
                    "front": f"[{cr['course_title']}] Explique com suas próprias palavras (Método Feynman) o conceito central do trecho #{str(cr['id'])[:8]}:",
                    "back": text,
                    "revealed": False,
                    "source_refs": [
                        {"doc_id": str(cr["doc_id"]), "chunk_id": str(cr["id"])}
                    ],
                    "course_id": str(cr["course_id"]),
                }
            )

        self._send_json(
            handler,
            HTTPStatus.OK,
            {
                "status": "ok",
                "flashcards": cards,
                "total": len(cards),
            },
        )

    def _handle_get_search(
        self,
        handler: BaseHTTPRequestHandler,
        user_id: str,
        query_text: str,
    ) -> None:
        q = query_text.strip()
        if not q:
            self._send_json(
                handler,
                HTTPStatus.OK,
                {"status": "ok", "query": "", "results": []},
            )
            return
        like_pat = f"%{q}%"
        results: list[dict[str, Any]] = []

        course_rows = self._fetchall(
            "SELECT id, title FROM courses WHERE user_id = ? AND title LIKE ? LIMIT 10",
            (user_id, like_pat),
        )
        for r in course_rows:
            results.append(
                {
                    "kind": "course",
                    "id": str(r["id"]),
                    "title": str(r["title"]),
                    "snippet": f"Disciplina: {r['title']}",
                }
            )

        topic_rows = self._fetchall(
            """
            SELECT t.id, t.course_id, t.title, c.title AS course_title
            FROM topics t
            JOIN courses c ON c.id = t.course_id
            WHERE c.user_id = ? AND t.title LIKE ?
            LIMIT 10
            """,
            (user_id, like_pat),
        )
        for r in topic_rows:
            results.append(
                {
                    "kind": "topic",
                    "id": str(r["id"]),
                    "course_id": str(r["course_id"]),
                    "title": str(r["title"]),
                    "snippet": f"Tópico em {r['course_title']}",
                }
            )

        chunk_rows = self._fetchall(
            """
            SELECT c.id, c.text, v.doc_id
            FROM chunks c
            JOIN doc_versions v ON v.id = c.version_id AND v.user_id = c.user_id
            WHERE c.user_id = ? AND c.text LIKE ?
            LIMIT 10
            """,
            (user_id, like_pat),
        )
        for r in chunk_rows:
            results.append(
                {
                    "kind": "chunk",
                    "id": str(r["id"]),
                    "doc_id": str(r["doc_id"]),
                    "title": f"Evidência #{str(r['id'])[:8]}",
                    "snippet": str(r["text"])[:160],
                }
            )

        self._send_json(
            handler,
            HTTPStatus.OK,
            {"status": "ok", "query": q, "results": results},
        )

    def _handle_post_settings_timezone(
        self,
        handler: BaseHTTPRequestHandler,
        user_id: str,
        body: dict[str, Any],
    ) -> None:
        raw_tz = body.get("timezone")
        source = str(body.get("source") or "user_manual").strip() or "user_manual"
        if raw_tz is None or not str(raw_tz).strip():
            self._send_json(
                handler,
                HTTPStatus.BAD_REQUEST,
                _error_body(
                    ErrorCode.SCHEMA_INVALID,
                    "campo 'timezone' é obrigatório (ex.: 'America/Sao_Paulo')",
                ),
            )
            return
        validated_tz = validate_iana_timezone(str(raw_tz))
        assert validated_tz is not None
        self.runtime.store.execute_write(
            user_id,
            [("UPDATE users SET timezone = ? WHERE id = ?", (validated_tz, user_id))],
            bump_domain_revision=False,
        )
        if self.runtime.config is not None:
            self.runtime.config["timezone"] = validated_tz
            self.runtime.config["timezone_source"] = source
        self._send_json(
            handler,
            HTTPStatus.OK,
            {
                "status": "ok",
                "user_id": user_id,
                "timezone": validated_tz,
                "timezone_source": source,
            },
        )

    def _handle_post(self, handler: BaseHTTPRequestHandler) -> None:
        user_id = self._require_user(handler)
        if user_id is None:
            return
        body = self._read_json_body(handler)
        if body is None:
            return
        path = urlparse(handler.path).path.rstrip("/")

        try:
            if path == "/courses":
                self._handle_post_courses(handler, user_id, body)
                return

            if path == "/settings/timezone":
                self._handle_post_settings_timezone(handler, user_id, body)
                return

            if path == "/library/upload":
                self._handle_post_library_upload(handler, user_id, body)
                return

            if path == "/turns":
                session_id = str(body.get("session_id") or uuid.uuid4())
                message = str(body.get("message") or "")
                payload = body.get("payload")
                if payload is not None and not isinstance(payload, dict):
                    self._send_json(
                        handler,
                        HTTPStatus.BAD_REQUEST,
                        _error_body(
                            ErrorCode.SCHEMA_INVALID,
                            "campo 'payload' deve ser objeto JSON",
                        ),
                    )
                    return
                intent = body.get("intent")
                result = self.runtime.graph.run_turn(
                    user_id=user_id,
                    session_id=session_id,
                    message=message,
                    payload=dict(payload or {}),
                    intent=str(intent) if intent else None,
                )
                self._send_json(
                    handler, HTTPStatus.OK, _serialize_turn(result, session_id)
                )
                return

            # /turns/{session_id}/resume ou /turns/{session_id}/cancel
            parts = [p for p in path.split("/") if p]
            if len(parts) == 3 and parts[0] == "turns" and parts[2] in ("resume", "cancel"):
                session_id = parts[1]
                action = parts[2]
                if action == "cancel":
                    result = self.runtime.graph.run_turn(
                        user_id=user_id,
                        session_id=session_id,
                        message="/cancel",
                        cancel_requested=True,
                    )
                    self._send_json(
                        handler, HTTPStatus.OK, _serialize_turn(result, session_id)
                    )
                    return
                resume_payload = body.get("resume", body)
                result = self.runtime.graph.resume_turn(
                    session_id=session_id,
                    resume=resume_payload,
                    user_id=user_id,
                )
                self._send_json(
                    handler, HTTPStatus.OK, _serialize_turn(result, session_id)
                )
                return

            self._send_json(
                handler,
                HTTPStatus.NOT_FOUND,
                _error_body(ErrorCode.SOURCE_UNRESOLVED, f"rota POST desconhecida: {path}"),
            )
        except EduAgentError as exc:
            self._send_json(
                handler,
                HTTP_STATUS_BY_ERROR.get(exc.code, 500),
                {"status": "failed", "error": exc.to_dict()},
            )
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                handler,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                _error_body(
                    ErrorCode.INTERNAL_FAILURE,
                    f"falha interna da API: {type(exc).__name__}: {exc}",
                ),
            )


def serve_ui_forever(
    context: RuntimeContext,
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
    open_browser: bool = False,
) -> int:
    """Inicia a LoopbackAPI servindo a Interface Gráfica Local até Ctrl+C."""
    server = LoopbackAPI(context, host=host, port=port)
    bound_host, bound_port = server.start()
    url = f"http://{bound_host}:{bound_port}/"
    print(
        json.dumps(
            {
                "status": "listening",
                "service": "eduagent-loopback-ui",
                "url": url,
                "host": bound_host,
                "port": bound_port,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass
    try:
        if server._thread is not None:
            while server._thread.is_alive():
                server._thread.join(timeout=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m eduagent.api",
        description="Servidor HTTP loopback + Interface Gráfica Local do EduAgent-OS v0.1",
    )
    parser.add_argument("--data-root", default="data", help="Diretório raiz de dados")
    parser.add_argument("--user", default=None, help="UUID canônico para garantir usuário inicial")
    parser.add_argument("--host", default="127.0.0.1", help="Host loopback (127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Porta TCP local (default: 8080)")
    parser.add_argument("--open-browser", action="store_true", help="Abre navegador automaticamente")
    parser.add_argument(
        "--model-url",
        default=None,
        help=(
            "URL OpenAI-compatible do runtime do modelo (ex.: "
            "http://127.0.0.1:8081/v1); sem ela a UI roda sem geração "
            "(MODEL_NOT_ADMITTED bloqueia a tutoria, mapa §3.1)"
        ),
    )
    parser.add_argument(
        "--model-id",
        default="bonsai-27b-ada",
        help="ID do modelo no runtime (default: bonsai-27b-ada)",
    )
    parser.add_argument(
        "--model-label",
        default=None,
        help=(
            "rótulo exibido no banner de gates da UI (ex.: 'GLM-5.3-Flash "
            "Admitido'); default deriva do --model-id"
        ),
    )
    parser.add_argument(
        "--embedder-dir",
        default=None,
        help=(
            "diretório do BGE-M3 local (mapa §6.5); sem ele, a rota "
            "ask/practice recusa com SOURCE_UNRESOLVED"
        ),
    )
    parser.add_argument(
        "--model-capabilities",
        choices=("manifest", "off"),
        default="manifest",
        help=(
            "origem da capacidade json_schema alegada ao runtime: 'manifest' "
            "lê do manifesto congelado (gate G5, válido para o runtime Bonsai "
            "verificado); 'off' não alega capacidade verificada (use para "
            "runtimes não cobertos pelo manifesto, ex.: GLM/sglang) — "
            "fail-closed, mapa §3.1"
        ),
    )
    args = parser.parse_args(argv)

    # Backend do modelo (mapa §3.1): capacidade json_schema lida do manifesto
    # congelado e verificada por hash (gate G5 da task 002); sem manifesto a
    # capacidade NÃO é presumida — mesmo contrato da CLI (cli.py).
    backend = None
    if args.model_url:
        from eduagent.services.model_adapter import ModelAdapter, RuntimeCapabilities

        manifest_path = pathlib.Path("manifest.json")
        json_schema = False
        evidence = "não verificada — sem manifesto"
        if args.model_capabilities == "manifest" and manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                caps = (manifest.get("capacidades") or {}).get("json_schema") or {}
                json_schema = bool(caps.get("suportada"))
                evidence = f"manifesto congelado ({manifest_path})"
            except (OSError, json.JSONDecodeError):
                pass
        backend = ModelAdapter(
            base_url=args.model_url,
            model_id=args.model_id,
            capabilities=RuntimeCapabilities(
                json_schema=json_schema,
                json_schema_evidence=evidence,
            ),
        )
        backend.label = args.model_label or args.model_id

    embedder = None
    if args.embedder_dir:
        from eduagent.services.retrieval import BgeM3Embedder

        embedder = BgeM3Embedder(args.embedder_dir)

    ctx = RuntimeContext.open(args.data_root, backend=backend, embedder=embedder)
    try:
        if args.user:
            ctx.store.ensure_user(str(uuid.UUID(args.user)))
        else:
            existing = ctx.store.fetch_user_rows("SELECT id FROM users LIMIT 1")
            if not existing:
                default_uid = "00000000-0000-0000-0000-000000000001"
                ctx.store.ensure_user(default_uid)
                ctx.store.execute_write(
                    default_uid,
                    [
                        (
                            "INSERT OR IGNORE INTO courses(id, user_id, title) VALUES (?, ?, ?)",
                            (
                                "00000000-0000-0000-0000-000000000021",
                                default_uid,
                                "MO810 — Sistemas Multiagente",
                            ),
                        ),
                        (
                            "INSERT OR IGNORE INTO topics(id, course_id, title) VALUES (?, ?, ?)",
                            (
                                "00000000-0000-0000-0000-000000000011",
                                "00000000-0000-0000-0000-000000000021",
                                "Arquitetura Cognitiva e Orquestração LangGraph",
                            ),
                        ),
                    ],
                    bump_domain_revision=False,
                )
        return serve_ui_forever(
            ctx,
            host=args.host,
            port=args.port,
            open_browser=args.open_browser,
        )
    finally:
        ctx.close()


__all__ = ["DEFAULT_PORT", "LoopbackAPI", "main", "serve_ui_forever"]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
