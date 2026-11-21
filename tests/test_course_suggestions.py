"""Testes da classificação de documentos e do fluxo "+Nova" em duas fases.

Cobre: migração 0010 (``doc_classifications`` por sha256), Fase 1
(classificação com cache e escalada única), Fase 2 (agregação de batch em
rascunhos pendentes), rotas loopback (classify / aggregate / backfill) e
confirmação/descarte. Modelo e extrator são falsos — nenhum resultado medido.
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
from eduagent.services.doc_classifier import DocumentClassifierService
from eduagent.services.ingestion import BlockRecord, ExtractedDocument, PageRecord
from eduagent.services.model_adapter import GenerationResult
from eduagent.storage.repository import DomainStore

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
    """Extrator falso: página 1 = capa (heading), páginas seguintes = corpo."""

    name = "fake"
    version = "0"

    def __init__(self, deep_text: str = "") -> None:
        self._deep_text = deep_text

    def extract(self, data: bytes, mime: str, *, max_pages: int, **_: Any) -> ExtractedDocument:
        base = data.decode("utf-8", errors="replace")[:300]
        pages = [
            PageRecord(
                page=1,
                blocks=[
                    BlockRecord(page=1, kind="heading", text=base[:60], order_in_page=1),
                ],
            )
        ]
        if max_pages > 6 and self._deep_text:
            # Amostra da escalada: headings de verdade (sumário)
            pages.append(
                PageRecord(
                    page=2,
                    blocks=[
                        BlockRecord(page=2, kind="heading", text=chunk, order_in_page=i)
                        for i, chunk in enumerate(self._deep_text.split("\n")[:20])
                    ],
                )
            )
        return ExtractedDocument(pages=pages, page_diagnosis={p.page: "ok" for p in pages})


class ScriptedBackend:
    """Backend falso: devolve respostas em fila (classificação, depois agregação)."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    def generate(self, *, messages: list[dict[str, Any]], schema: Any, sampler: Any, deadline: float, seed: int | None) -> GenerationResult:
        self.prompts.append(str(messages[0]["content"]))
        if not self.responses:
            raise AssertionError("backend sem respostas configuradas")
        payload = self.responses.pop(0)
        return GenerationResult(
            text=json.dumps(payload, ensure_ascii=False),
            finish_reason="stop",
            prompt_tokens=10,
            completion_tokens=10,
            thinking=None,
            model_id="fake-model",
            seed=seed,
        )


CLASS_OK = {
    "doc_class": "programa",
    "confidence": "alta",
    "needs_more": False,
    "disciplina_hints": ["MC8322"],
    "topics_seen": ["Programação Linear", "Simplex"],
}

AGG_OK = {
    "courses": [
        {
            "title": "MC8322 — Otimização",
            "topics": ["Programação Linear", "Simplex", "Dualidade"],
        }
    ],
    "assignments": [{"file": 1, "course": 1}, {"file": 2, "course": 1}],
}


def _open_runtime(tmp_path: Path, backend: Any, extractor: Any | None = None) -> RuntimeContext:
    ctx = RuntimeContext.open(
        tmp_path / "data",
        config={},
        backend=backend,
        extractor=extractor if extractor is not None else FakeExtractor(),
        telemetry=False,
    )
    ctx.store.ensure_user(UID)
    return ctx


# ============================================================================
# Migração 0010 + classificador
# ============================================================================
def test_migration_0010_and_classify_with_cache(tmp_path: Path) -> None:
    backend = ScriptedBackend([CLASS_OK, CLASS_OK])
    ctx = _open_runtime(tmp_path, backend)
    svc = ctx.doc_classifier
    rows = ctx.store.fetch_user_rows(
        "SELECT name FROM sqlite_master WHERE type='table' AND "
        "name = 'doc_classifications'"
    )
    assert len(rows) == 1

    raw = b"PDF conteudo estavel"
    meta = svc.classify_bytes("programa.pdf", raw)
    assert meta["doc_class"] == "programa"
    assert meta["disciplina_hints"] == ["MC8322"]
    assert backend.prompts and "classifica" in backend.prompts[0]

    # Mesmo conteúdo (sha256) → cache, zero chamadas novas
    meta2 = svc.classify_bytes("outro-nome.pdf", raw)
    assert meta2["doc_class"] == "programa"
    assert len(backend.prompts) == 1

    # Conteúdo novo → nova chamada
    svc.classify_bytes("outro.pdf", b"outro conteudo X")
    assert len(backend.prompts) == 2
    ctx.close()


def test_classify_requires_backend(tmp_path: Path) -> None:
    ctx = _open_runtime(tmp_path, None)
    with pytest.raises(EduAgentError) as exc:
        ctx.doc_classifier.classify_bytes("a.pdf", b"x")
    assert exc.value.code == ErrorCode.MODEL_NOT_ADMITTED
    ctx.close()


def test_classify_escalation_needs_more_once(tmp_path: Path) -> None:
    deep = "\n".join(f"{i}. Tópico Real {i}" for i in range(1, 9))
    backend = ScriptedBackend(
        [
            {**CLASS_OK, "doc_class": "outro", "needs_more": True},
            CLASS_OK,
        ]
    )
    ctx = _open_runtime(tmp_path, backend, extractor=FakeExtractor(deep_text=deep))
    meta = ctx.doc_classifier.classify_bytes("capa.pdf", b"capa somente")
    assert meta["doc_class"] == "programa"
    assert len(backend.prompts) == 2
    # A 2ª chamada viu os headings da escalada
    assert "Tópico Real" in backend.prompts[1]
    # Persistido com pages_scanned da 2ª passada
    row = ctx.store.fetch_user_rows(
        "SELECT pages_scanned FROM doc_classifications"
    )
    assert row[0]["pages_scanned"] == 30
    ctx.close()


# ============================================================================
# Fase 1 + Fase 2 no serviço de sugestões
# ============================================================================
def test_two_phase_flow_creates_pending_with_class_metadata(tmp_path: Path) -> None:
    backend = ScriptedBackend([CLASS_OK, CLASS_OK, AGG_OK])
    ctx = _open_runtime(tmp_path, backend)
    svc = ctx.course_suggestions

    r1 = svc.classify_staged(UID, "ProgramaMC.pdf", b"programa conteudo", None)
    batch_id = r1["batch_id"]
    assert r1["file"]["doc_class"] == "programa"
    svc.classify_staged(UID, "Chapter_6.pdf", b"livro conteudo", batch_id)

    created = svc.aggregate_batch(UID, batch_id)
    assert len(created) == 1
    assert created[0]["title"] == "MC8322 — Otimização"
    assert len(created[0]["files"]) == 2
    assert created[0]["files"][0]["doc_class"] == "programa"
    assert created[0]["files"][0]["staged_rel"].startswith("staging/")
    # staging do batch compartilhado ainda contém os 2 arquivos
    batch_dir = tmp_path / "data" / UID / "staging" / batch_id
    assert len(list(batch_dir.iterdir())) == 2

    pending = svc.list_pending(UID)
    assert len(pending) == 1
    ctx.close()


def test_confirm_moves_files_and_keeps_shared_batch_intact(tmp_path: Path) -> None:
    backend = ScriptedBackend([CLASS_OK, CLASS_OK, AGG_OK])
    ctx = _open_runtime(tmp_path, backend)
    svc = ctx.course_suggestions
    r1 = svc.classify_staged(UID, "a.pdf", b"conteudo-a", None)
    svc.classify_staged(UID, "b.pdf", b"conteudo-b", r1["batch_id"])
    created = svc.aggregate_batch(UID, r1["batch_id"])
    sid = created[0]["id"]
    ingested: list[str] = []

    result = svc.confirm(
        UID,
        sid,
        title="T",
        topics=["T1"],
        ingest_fn=lambda uid, fn, raw, cid: (ingested.append(fn), {"ingested": True})[1],
    )
    assert ingested == ["a.pdf", "b.pdf"]
    originals = tmp_path / "data" / UID / "originals"
    assert (originals / "a.pdf").exists()
    # staging limpo (batch tinha só os arquivos desta sugestão)
    assert not (tmp_path / "data" / UID / "staging" / r1["batch_id"]).exists()
    rows = ctx.store.fetch_user_rows(
        "SELECT status FROM course_suggestions WHERE id = ?", (sid,)
    )
    assert rows[0]["status"] == "approved"
    ctx.close()


def test_reject_removes_only_its_files(tmp_path: Path) -> None:
    backend = ScriptedBackend([CLASS_OK, CLASS_OK, AGG_OK])
    ctx = _open_runtime(tmp_path, backend)
    svc = ctx.course_suggestions
    r1 = svc.classify_staged(UID, "a.pdf", b"conteudo-a", None)
    batch_id = r1["batch_id"]
    svc.classify_staged(UID, "b.pdf", b"conteudo-b", batch_id)
    created = svc.aggregate_batch(UID, batch_id)
    svc.reject(UID, created[0]["id"])
    batch_dir = tmp_path / "data" / UID / "staging" / batch_id
    assert not batch_dir.exists()
    assert svc.list_pending(UID) == []
    ctx.close()


def test_expired_suggestion_not_listed(tmp_path: Path) -> None:
    ctx = _open_runtime(tmp_path, ScriptedBackend([CLASS_OK, AGG_OK]))
    svc = ctx.course_suggestions
    r1 = svc.classify_staged(UID, "a.pdf", b"x", None)
    created = svc.aggregate_batch(UID, r1["batch_id"])
    clock_now = datetime.now(timezone.utc) + timedelta(hours=25)
    svc._clock = lambda: clock_now  # simula passagem do TTL
    assert svc.list_pending(UID) == []
    with pytest.raises(EduAgentError):
        svc.get_pending(UID, created[0]["id"])
    ctx.close()


# ============================================================================
# Rotas loopback
# ============================================================================
def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _req(base: str, method: str, path: str, body: dict | None = None, headers: dict | None = None) -> tuple[int, dict[str, Any]]:
    hdrs = {"X-EduAgent-User": UID, **(headers or {})}
    data = None
    if body is not None:
        hdrs["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def test_api_classify_aggregate_backfill_end_to_end(tmp_path: Path) -> None:
    # 3 respostas: 2 classificações + 1 agregação; depois 1 classificação no backfill
    backend = ScriptedBackend(
        [CLASS_OK, CLASS_OK, AGG_OK, CLASS_OK]
    )
    ctx = _open_runtime(tmp_path, backend)
    server = LoopbackAPI(ctx, host="127.0.0.1", port=0)
    host, port = server.start()
    base = f"http://{host}:{port}"
    try:
        # Fase 1 via API (2 arquivos, mesmo batch)
        status, data = _req(
            base, "POST", "/courses/suggestions/classify",
            {"filename": "Programa.pdf", "content_base64": _b64(b"conteudo 1")},
        )
        assert status == 200 and data["file"]["doc_class"] == "programa"
        batch_id = data["batch_id"]
        status, data = _req(
            base, "POST", "/courses/suggestions/classify",
            {"filename": "Chapter.pdf", "content_base64": _b64(b"conteudo 2"),
             "batch_id": batch_id},
        )
        assert status == 200 and data["batch_id"] == batch_id

        # Sem header → 400
        status, _ = _req(base, "POST", "/courses/suggestions/classify",
                         {"filename": "x.pdf", "content_base64": _b64(b"x")},
                         headers={"X-EduAgent-User": ""})
        assert status == 400

        # Fase 2 via API
        status, data = _req(base, "POST", "/courses/suggestions", {"batch_id": batch_id})
        assert status == 200 and len(data["suggestions"]) == 1
        sid = data["suggestions"][0]["id"]

        # GET lista rascunhos com metadados de classe
        status, data = _req(base, "GET", "/courses/suggestions")
        assert status == 200
        assert data["suggestions"][0]["files"][0]["doc_class"] == "programa"

        # Backfill: sugestão ainda não ingerida → nada pendente no acervo
        status, data = _req(base, "POST", "/library/classify-pending", {})
        assert status == 200 and data["classified"] == 0

        # Confirma → ingere; o gancho pós-ingestão NÃO chama o modelo de novo
        # (sha256 já classificado no batch). O backfill fica a zero de chamadas.
        status, data = _req(base, "POST", f"/courses/suggestions/{sid}/confirm", {})
        assert status == 200 and data["course"]["title"] == "MC8322 — Otimização"
        calls_after_confirm = 3
        assert len(backend.prompts) == calls_after_confirm

        # Backfill pós-ingestão: documento já classificado pelo gancho → 0 novo
        status, data = _req(base, "POST", "/library/classify-pending", {})
        assert status == 200 and data["classified"] == 0
        assert len(backend.prompts) == calls_after_confirm

        # GET arquivo em staging (preview) ainda funciona pós-confirmação? Não:
        # sugestão resolvida → 404 tipado
        status, _ = _req(
            base, "GET",
            f"/courses/suggestions/{sid}/files/Programa.pdf",
        )
        assert status == 404

        # DELETE em sugestão resolvida → 404
        status, _ = _req(base, "DELETE", f"/courses/suggestions/{sid}")
        assert status == 404
    finally:
        server.stop()
        ctx.close()


def test_api_classify_without_model_is_503(tmp_path: Path) -> None:
    ctx = _open_runtime(tmp_path, None)
    server = LoopbackAPI(ctx, host="127.0.0.1", port=0)
    host, port = server.start()
    base = f"http://{host}:{port}"
    try:
        status, data = _req(
            base, "POST", "/courses/suggestions/classify",
            {"filename": "a.pdf", "content_base64": _b64(b"x")},
        )
        assert status == 503
        assert data["error"]["code"] == "MODEL_NOT_ADMITTED"
    finally:
        server.stop()
        ctx.close()
