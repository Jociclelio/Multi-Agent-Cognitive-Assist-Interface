"""Testes do fluxo "+Nova": sugestão de matérias a partir de arquivos.

Cobre a migração 0008 (``course_suggestions``), o serviço
``CourseSuggestionService`` (amostra → modelo → rascunhos pendentes →
confirmação/descarte) e as rotas loopback ``/courses/suggestions*``.
Modelo e extrator são falsos — nenhum resultado medido aqui (§1/§3).
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from eduagent.api import LoopbackAPI
from eduagent.contracts import EduAgentError, ErrorCode
from eduagent.runtime import RuntimeContext
from eduagent.services.course_suggest import CourseSuggestionService
from eduagent.services.ingestion import BlockRecord, ExtractedDocument, PageRecord
from eduagent.services.model_adapter import GenerationResult

UTC = timezone.utc
UID = "123e4567-e89b-12d3-a456-426614174000"


class MutableClock:
    def __init__(self, start: datetime | None = None) -> None:
        self._moment = start or datetime(2026, 11, 21, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self._moment

    def advance(self, **kwargs: Any) -> None:
        self._moment += timedelta(**kwargs)


class FakeExtractor:
    """Extrator falso: uma página de cabeçalho + parágrafo por arquivo."""

    name = "fake"
    version = "0"

    def __init__(self, texts: dict[str, str] | None = None) -> None:
        self._texts = texts or {}

    def extract(self, data: bytes, mime: str, *, max_pages: int, **_: Any) -> ExtractedDocument:
        text = self._texts.get(mime) or data.decode("utf-8", errors="replace")[:400]
        page = PageRecord(
            page=1,
            blocks=[
                BlockRecord(page=1, kind="heading", text=text[:80], order_in_page=1),
                BlockRecord(page=1, kind="paragraph", text=text[80:200], order_in_page=2),
            ],
        )
        return ExtractedDocument(pages=[page], page_diagnosis={1: "ok"})


class FakeBackend:
    """Backend falso: devolve o JSON de agrupamento configurado."""

    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.payload = payload or {
            "courses": [
                {"title": "Contabilidade Geral", "topics": ["Balanço", "DRE"]},
                {"title": "Álgebra Linear", "topics": ["Matrizes"]},
            ],
            "assignments": [
                {"file": 1, "course": 1},
                {"file": 2, "course": 1},
                {"file": 3, "course": 2},
            ],
        }
        self.calls = 0

    def generate(self, *, messages: list[dict[str, Any]], schema: Any, sampler: Any, deadline: float, seed: int | None) -> GenerationResult:
        self.calls += 1
        return GenerationResult(
            text=json.dumps(self.payload, ensure_ascii=False),
            finish_reason="stop",
            prompt_tokens=10,
            completion_tokens=10,
            thinking=None,
            model_id="fake-model",
            seed=seed,
        )


def _service(
    tmp_path: Path,
    *,
    backend: Any | None = None,
    extractor: Any | None = None,
    clock: MutableClock | None = None,
) -> CourseSuggestionService:
    root = tmp_path / "data"
    root.mkdir(parents=True, exist_ok=True)
    from eduagent.storage.repository import DomainStore

    store = DomainStore.open(root / "domain.sqlite")
    store.ensure_user(UID)
    return CourseSuggestionService(
        store,
        root,
        extractor=extractor or FakeExtractor(),
        backend=backend,
        clock=clock or MutableClock(),
    )


# ============================================================================
# Migração 0008
# ============================================================================
def test_migration_0008_creates_course_suggestions(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    rows = svc._store.fetch_user_rows(
        "SELECT name FROM sqlite_master WHERE type='table' AND "
        "name = 'course_suggestions'"
    )
    assert len(rows) == 1


# ============================================================================
# Serviço: suggest / list / confirm / reject
# ============================================================================
def test_suggest_groups_files_and_creates_pending(tmp_path: Path) -> None:
    backend = FakeBackend()
    svc = _service(tmp_path, backend=backend, extractor=FakeExtractor())
    created = svc.suggest(
        UID,
        [
            ("balanco.pdf", b"PDF-falso-1"),
            ("dre.pdf", b"PDF-falso-2"),
            ("matrizes.pdf", b"PDF-falso-3"),
        ],
    )
    assert backend.calls == 1
    assert [c["title"] for c in created] == [
        "Contabilidade Geral",
        "Álgebra Linear",
    ]
    assert len(created[0]["files"]) == 2
    assert created[0]["files"][0]["filename"] == "balanco.pdf"
    # Staging persistido no disco do dono
    for meta in created[0]["files"]:
        path = svc.staged_file_path(UID, created[0]["id"], meta["filename"])
        assert path.exists()
    pending = svc.list_pending(UID)
    assert {p["title"] for p in pending} == {
        "Contabilidade Geral",
        "Álgebra Linear",
    }


def test_suggest_without_backend_is_fail_closed(tmp_path: Path) -> None:
    svc = _service(tmp_path, backend=None)
    with pytest.raises(EduAgentError) as exc:
        svc.suggest(UID, [("a.pdf", b"x")])
    assert exc.value.code == ErrorCode.MODEL_NOT_ADMITTED


def test_suggest_invalid_model_payload_raises_typed_error(tmp_path: Path) -> None:
    class BadBackend:
        def generate(self, **_: Any) -> GenerationResult:
            return GenerationResult(
                text="```json\n{'courses': []}\n```",
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=1,
                thinking=None,
                model_id="fake",
                seed=0,
            )

    svc = _service(tmp_path, backend=BadBackend())
    with pytest.raises(EduAgentError) as exc:
        svc.suggest(UID, [("a.pdf", b"x")])
    assert exc.value.code == ErrorCode.SCHEMA_INVALID


def test_confirm_creates_course_ingests_and_clears_staging(tmp_path: Path) -> None:
    svc = _service(tmp_path, backend=FakeBackend())
    created = svc.suggest(UID, [("unico.pdf", b"conteudo")])
    suggestion_id = created[0]["id"]
    ingested: list[tuple[str, str]] = []

    def fake_ingest(user_id: str, filename: str, raw: bytes, course_id: str) -> dict:
        ingested.append((filename, course_id))
        return {"ingested": True, "turn": "fake"}

    result = svc.confirm(
        UID,
        suggestion_id,
        title="Matéria Editada",
        topics=["Tópico A"],
        ingest_fn=fake_ingest,
    )
    assert result["course"]["title"] == "Matéria Editada"
    assert ingested == [("unico.pdf", result["course"]["id"])]
    # Staging limpo e status aprovado
    assert not (tmp_path / "data" / UID / "staging" / suggestion_id).exists()
    rows = svc._store.fetch_user_rows(
        "SELECT status FROM course_suggestions WHERE id = ?",
        (suggestion_id,),
    )
    assert rows[0]["status"] == "approved"
    assert svc.list_pending(UID) == []


def test_reject_discards_and_clears_staging(tmp_path: Path) -> None:
    svc = _service(tmp_path, backend=FakeBackend())
    created = svc.suggest(UID, [("a.pdf", b"x")])
    suggestion_id = created[0]["id"]
    svc.reject(UID, suggestion_id)
    assert svc.list_pending(UID) == []
    with pytest.raises(EduAgentError) as exc:
        svc.get_pending(UID, suggestion_id)
    assert exc.value.code == ErrorCode.SOURCE_UNRESOLVED


def test_expired_suggestion_is_not_listed_or_confirmable(tmp_path: Path) -> None:
    clock = MutableClock()
    svc = _service(tmp_path, backend=FakeBackend(), clock=clock)
    created = svc.suggest(UID, [("a.pdf", b"x")])
    clock.advance(hours=25)
    assert svc.list_pending(UID) == []
    with pytest.raises(EduAgentError):
        svc.get_pending(UID, created[0]["id"])


# ============================================================================
# Rotas loopback
# ============================================================================
def _open_runtime(tmp_path: Path, backend: Any) -> RuntimeContext:
    ctx = RuntimeContext.open(
        tmp_path / "data",
        config={},
        backend=backend,
        extractor=FakeExtractor(),
        embedder=None,
        telemetry=False,
    )
    ctx.store.ensure_user(UID)
    return ctx


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def test_api_suggestions_end_to_end(tmp_path: Path) -> None:
    ctx = _open_runtime(tmp_path, FakeBackend())
    server = LoopbackAPI(ctx, host="127.0.0.1", port=0)
    host, port = server.start()
    base = f"http://{host}:{port}"
    headers = {"X-EduAgent-User": UID}
    try:
        # POST /courses/suggestions → rascunhos pendentes
        req = urllib.request.Request(
            f"{base}/courses/suggestions",
            data=json.dumps(
                {
                    "files": [
                        {
                            "filename": "aula-01.pdf",
                            "content_base64": _b64(b"conteudo aula 1"),
                        },
                        {
                            "filename": "aula-02.pdf",
                            "content_base64": _b64(b"conteudo aula 2"),
                        },
                    ]
                }
            ).encode(),
            headers={**headers, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        assert resp.status == 200
        suggestions = data["suggestions"]
        assert len(suggestions) >= 1
        sid = suggestions[0]["id"]

        # GET /courses/suggestions lista os rascunhos
        with urllib.request.urlopen(
            urllib.request.Request(f"{base}/courses/suggestions", headers=headers),
            timeout=10,
        ) as resp:
            listed = json.loads(resp.read().decode())
        assert any(s["id"] == sid for s in listed["suggestions"])

        # GET arquivo em staging (preview)
        filename = suggestions[0]["files"][0]["filename"]
        with urllib.request.urlopen(
            urllib.request.Request(
                f"{base}/courses/suggestions/{sid}/files/{filename}",
                headers=headers,
            ),
            timeout=10,
        ) as resp:
            assert resp.status == 200
            assert b"conteudo" in resp.read()

        # Sem header de usuário → 400
        try:
            urllib.request.urlopen(
                f"{base}/courses/suggestions", timeout=10
            )
            raise AssertionError("deveria exigir header")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400

        # DELETE descarta
        req = urllib.request.Request(
            f"{base}/courses/suggestions/{sid}", headers=headers, method="DELETE"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            assert resp.status == 200
        with urllib.request.urlopen(
            urllib.request.Request(f"{base}/courses/suggestions", headers=headers),
            timeout=10,
        ) as resp:
            assert json.loads(resp.read().decode())["suggestions"] == []
    finally:
        server.stop()
        ctx.close()


def test_api_suggestions_without_model_is_503(tmp_path: Path) -> None:
    ctx = _open_runtime(tmp_path, None)
    server = LoopbackAPI(ctx, host="127.0.0.1", port=0)
    host, port = server.start()
    base = f"http://{host}:{port}"
    headers = {"X-EduAgent-User": UID, "Content-Type": "application/json"}
    try:
        req = urllib.request.Request(
            f"{base}/courses/suggestions",
            data=json.dumps(
                {"files": [{"filename": "a.pdf", "content_base64": _b64(b"x")}]}
            ).encode(),
            headers=headers,
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            raise AssertionError("deveria recusar sem modelo")
        except urllib.error.HTTPError as exc:
            assert exc.code == 503
            payload = json.loads(exc.read().decode())
            assert payload["error"]["code"] == "MODEL_NOT_ADMITTED"
    finally:
        server.stop()
        ctx.close()
