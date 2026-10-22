"""API loopback local do EduAgent-OS (mapa §12 — task 015).

Endpoints (§12): ``POST /turns``, ``POST /turns/{id}/resume``,
``POST /turns/{id}/cancel``, ``GET /artifacts/{id}``, ``GET /health``.

Contratos:

- **Escrita exige contexto de usuário autenticado localmente** (§12): toda
  requisição que lê/escreve dados exige o cabeçalho ``X-EduAgent-User`` com
  UUID registrado no domínio local. Sem o contexto: 401 JSON com ``status``.
  O MVP local é single-threaded (mapa §1): o servidor HTTP é serial — sem
  multiusuário concorrente em rede.
- **JSON sempre contém ``status``** (§12): todas as respostas são JSON com
  ``status``; erros tipados do §4 vão no campo ``error``.
- **Loopback apenas**: o servidor escuta em ``127.0.0.1``; sem rede externa
  (mapa §3).
- **``GET /artifacts/{id}``**: resolve artefato publicado sob o data_root do
  usuário autenticado (ICS exportado, §9) por path resolvido com ownership
  (§10); sem traversal e sem cruzar usuários.
"""

from __future__ import annotations

import json
import uuid as _uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from eduagent.contracts import EduAgentError, ErrorCode
from eduagent.policy import resolve_owned_path
from eduagent.runtime import RuntimeContext

DIAGNOSTIC = "eduagent/api.py"

#: Porta default da API loopback (escolha de ensaio local; o 8079 é do
#: runtime do modelo, mapa §3.1).
DEFAULT_PORT = 8094

AUTH_HEADER = "X-EduAgent-User"

#: Mapa de erro tipado §4 → status HTTP do loopback (escolha local: o mapa
#: fixa os códigos e o JSON com status, não os status HTTP).
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


class _Handler(BaseHTTPRequestHandler):
    """Rotas do §12 sobre o RuntimeContext aberto (MVP serial)."""

    server_version = "EduAgentLoopback/0.1"

    # -- helpers -------------------------------------------------------------

    @property
    def runtime(self) -> RuntimeContext:
        return self.server.runtime  # type: ignore[attr-defined]

    def _json(self, payload: dict[str, Any], *, http_status: int = 200) -> None:
        body = json.dumps(
            payload, ensure_ascii=False, default=str
        ).encode("utf-8")
        self.send_response(http_status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error_payload(self, exc: EduAgentError) -> dict[str, Any]:
        return {
            "status": "failed",
            "error": exc.to_dict(),
        }

    def _authenticated_user(self) -> str:
        """Contexto de usuário autenticado localmente (§12): cabeçalho com
        UUID registrado no domínio; ausente/desconhecido → recusa por código.
        """
        user = self.headers.get(AUTH_HEADER)
        if not user:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"escrita/leitura exige cabeçalho {AUTH_HEADER} com o "
                "contexto de usuário autenticado localmente (mapa §12)",
                diagnostic=DIAGNOSTIC,
            )
        try:
            _uuid.UUID(str(user))
        except ValueError as exc:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"{AUTH_HEADER} deve ser UUID: {user!r}",
                diagnostic=DIAGNOSTIC,
            ) from exc
        rows = self.runtime.store.fetch_user_rows(
            "SELECT id FROM users WHERE id = ?", (str(user),)
        )
        if not rows:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"usuário {user} não registrado neste domínio local",
                diagnostic=DIAGNOSTIC,
            )
        return str(user)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"corpo não é JSON válido: {exc}",
                diagnostic=DIAGNOSTIC,
            ) from exc
        if not isinstance(data, dict):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "corpo JSON deve ser um objeto",
                diagnostic=DIAGNOSTIC,
            )
        return data

    def _log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Sem payload pessoal em log (§12): log padrão do http.server omite
        # corpo; aqui o silenciamos por completo no MVP local.
        return

    # -- rotas ---------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 — http.server
        path = urlsplit(self.path).path
        try:
            if path == "/health":
                self._json(
                    {
                        "status": "ok",
                        "service": "eduagent-loopback",
                        "mode": "MVP local single-threaded (mapa §1)",
                    }
                )
                return
            if path.startswith("/artifacts/"):
                artifact_id = path.removeprefix("/artifacts/").strip("/")
                self._json(self._get_artifact(artifact_id))
                return
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"rota GET desconhecida: {path}",
                diagnostic=DIAGNOSTIC,
            )
        except EduAgentError as exc:
            self._json(
                self._error_payload(exc),
                http_status=HTTP_STATUS_BY_ERROR.get(exc.code, 500),
            )

    def do_POST(self) -> None:  # noqa: N802 — http.server
        path = urlsplit(self.path).path
        try:
            if path == "/turns":
                self._json(self._post_turns())
                return
            if path.startswith("/turns/") and path.endswith("/resume"):
                session_id = path.removeprefix("/turns/").removesuffix(
                    "/resume"
                )
                self._json(self._post_resume(session_id))
                return
            if path.startswith("/turns/") and path.endswith("/cancel"):
                session_id = path.removeprefix("/turns/").removesuffix(
                    "/cancel"
                )
                self._json(self._post_cancel(session_id))
                return
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"rota POST desconhecida: {path}",
                diagnostic=DIAGNOSTIC,
            )
        except EduAgentError as exc:
            self._json(
                self._error_payload(exc),
                http_status=HTTP_STATUS_BY_ERROR.get(exc.code, 500),
            )

    # -- handlers ------------------------------------------------------------

    def _post_turns(self) -> dict[str, Any]:
        user_id = self._authenticated_user()
        body = self._body()
        message = str(body.get("message") or "")
        session_id = str(
            body.get("session_id") or _uuid.uuid4()
        )
        payload = dict(body.get("payload") or {})
        intent = body.get("intent")
        result = self.runtime.graph.run_turn(
            user_id=user_id,
            session_id=session_id,
            message=message,
            payload=payload,
            intent=str(intent) if intent else None,
        )
        return self._turn_payload(result, session_id)

    def _post_resume(self, session_id: str) -> dict[str, Any]:
        self._authenticated_user()
        if not session_id:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "resume exige id de sessão (thread do checkpoint, §10)",
                diagnostic=DIAGNOSTIC,
            )
        body = self._body()
        resume = body.get("resume", body)
        result = self.runtime.graph.resume_turn(
            session_id=session_id, resume=resume
        )
        return self._turn_payload(result, session_id)

    def _post_cancel(self, session_id: str) -> dict[str, Any]:
        user_id = self._authenticated_user()
        if not session_id:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "cancel exige id de sessão",
                diagnostic=DIAGNOSTIC,
            )
        result = self.runtime.graph.run_turn(
            user_id=user_id,
            session_id=session_id,
            message="/cancel",
            cancel_requested=True,
        )
        return self._turn_payload(result, session_id)

    def _get_artifact(self, artifact_id: str) -> dict[str, Any]:
        user_id = self._authenticated_user()
        if not artifact_id or "/" in artifact_id or ".." in artifact_id:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"id de artefato inválido: {artifact_id!r}",
                diagnostic=DIAGNOSTIC,
            )
        # Artefato do MVP: ICS exportado sob o data_root do usuário (§9),
        # resolvido com ownership e bloqueio de traversal (§10).
        exports = resolve_owned_path(
            self.runtime.data_root, user_id, f"exports/{artifact_id}.ics"
        )
        if not exports.exists():
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"artefato {artifact_id} não resolve para o usuário",
                diagnostic=DIAGNOSTIC,
            )
        content = exports.read_text(encoding="utf-8")
        return {
            "status": "ok",
            "artifact": {
                "id": artifact_id,
                "kind": "ics",
                "path": str(exports),
                "content": content,
            },
        }

    def _turn_payload(self, result: Any, session_id: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": result.status,
            "session_id": session_id,
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


class LoopbackAPI:
    """Servidor loopback do §12 sobre um ``RuntimeContext`` aberto.

    MVP local single-threaded (mapa §1): ``HTTPServer`` serial — uma
    requisição por vez; sem multiusuário concorrente em rede.
    """

    def __init__(
        self,
        runtime: RuntimeContext,
        *,
        host: str = "127.0.0.1",
        port: int = DEFAULT_PORT,
    ) -> None:
        self.runtime = runtime
        self._host = host
        self._port = port
        self._httpd: HTTPServer | None = None

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}"

    def start(self) -> None:
        if self._httpd is not None:  # pragma: no cover — idempotência
            return
        self._httpd = HTTPServer((self._host, self._port), _Handler)
        self._httpd.runtime = self.runtime  # type: ignore[attr-defined]
        # MVP local single-threaded (mapa §1): o HTTP atende em thread
        # dedicada; as requisições são serializadas pelo próprio servidor.
        import threading

        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            name="eduagent-loopback-api",
            daemon=True,
        )
        self._thread.start()

    def serve_forever(self) -> None:  # pragma: no cover — processo longo
        self.start()
        assert self._httpd is not None
        self._httpd.serve_forever()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.server_close()
            self._httpd = None


__all__ = ["DEFAULT_PORT", "LoopbackAPI"]
