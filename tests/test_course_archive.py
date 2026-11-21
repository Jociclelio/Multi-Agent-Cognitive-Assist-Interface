"""Testes do arquivamento e exclusão de matérias (fluxo Acervo).

Cobre a migração 0009 (``courses.archived_at``), ``POST
/courses/{id}/archive``, ``GET /courses?include_archived=1`` e
``DELETE /courses/{id}`` (cascade de documentos/tópicos + limpeza de
originais). Sem resultado medido — only spec do mapa §5/§15.1.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from eduagent.api import LoopbackAPI
from eduagent.runtime import RuntimeContext

UID = "123e4567-e89b-12d3-a456-426614174000"


def _open_runtime(tmp_path: Path) -> RuntimeContext:
    ctx = RuntimeContext.open(tmp_path / "data", config={}, telemetry=False)
    ctx.store.ensure_user(UID)
    return ctx


def _req(base: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict[str, Any]]:
    headers = {"X-EduAgent-User": UID}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def _create_course(base: str, title: str) -> str:
    status, data = _req(base, "POST", "/courses", {"title": title, "topics": ["T1"]})
    assert status == 200, data
    return data["course"]["id"]


def test_archive_unarchive_and_default_filtering(tmp_path: Path) -> None:
    ctx = _open_runtime(tmp_path)
    server = LoopbackAPI(ctx, host="127.0.0.1", port=0)
    host, port = server.start()
    base = f"http://{host}:{port}"
    try:
        c1 = _create_course(base, "Matéria A")
        c2 = _create_course(base, "Matéria B")

        # Default: as duas ativas
        status, data = _req(base, "GET", "/courses")
        assert {c["id"] for c in data["courses"]} == {c1, c2}

        # Arquiva A
        status, data = _req(base, "POST", f"/courses/{c1}/archive", {"archived": True})
        assert status == 200 and data["archived"] is True and data["archived_at"]

        # Default esconde; include_archived mostra
        status, data = _req(base, "GET", "/courses")
        assert {c["id"] for c in data["courses"]} == {c2}
        status, data = _req(base, "GET", "/courses?include_archived=1")
        assert {c["id"] for c in data["courses"]} == {c1, c2}

        # Desarquivar volta ao default
        status, data = _req(base, "POST", f"/courses/{c1}/archive", {"archived": False})
        assert status == 200 and data["archived_at"] is None
        status, data = _req(base, "GET", "/courses")
        assert {c["id"] for c in data["courses"]} == {c1, c2}

        # course_id inválido e inexistente
        status, _ = _req(base, "POST", "/courses/nada/archive", {"archived": True})
        assert status == 400
        status, _ = _req(base, "POST", f"/courses/{uuid.uuid4()}/archive", {"archived": True})
        assert status == 404
        status, _ = _req(base, "POST", f"/courses/{c2}/archive", {})
        assert status == 400
    finally:
        server.stop()
        ctx.close()


def test_delete_course_cascades_docs_topics_and_files(tmp_path: Path) -> None:
    ctx = _open_runtime(tmp_path)
    server = LoopbackAPI(ctx, host="127.0.0.1", port=0)
    host, port = server.start()
    base = f"http://{host}:{port}"
    try:
        cid = _create_course(base, "Matéria Para Apagar")
        doc_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        # Documento + versão + arquivo original fake (active_version NULL:
        # trigger §15.1 exige que a versão pertença ao documento)
        ctx.store.execute_write(
            UID,
            [
                (
                    "INSERT INTO documents(id, user_id, course_id, active_version) "
                    "VALUES (?, ?, ?, NULL)",
                    (doc_id, UID, cid),
                ),
                (
                    "INSERT INTO doc_versions(id, user_id, doc_id, sha256, mime, "
                    "original_ref, extractor_manifest, status) VALUES (?, ?, ?, "
                    "?, 'application/pdf', ?, '{}', 'active')",
                    (
                        version_id,
                        UID,
                        doc_id,
                        "ab" * 32,
                        f"{UID}/originals/excluir-{doc_id}.pdf",
                    ),
                ),
            ],
        )
        original = Path(ctx.data_root) / UID / "originals" / f"excluir-{doc_id}.pdf"
        original.parent.mkdir(parents=True, exist_ok=True)
        original.write_bytes(b"%PDF-fake")

        status, data = _req(base, "DELETE", f"/courses/{cid}")
        assert status == 200 and data["deleted_course"] == cid

        rows = ctx.store.fetch_user_rows(
            "SELECT (SELECT COUNT(*) FROM courses WHERE id = ?) AS c, "
            "(SELECT COUNT(*) FROM documents WHERE id = ?) AS d, "
            "(SELECT COUNT(*) FROM topics WHERE course_id = ?) AS t, "
            "(SELECT COUNT(*) FROM doc_versions WHERE id = ?) AS v",
            (cid, doc_id, cid, version_id),
        )
        assert tuple(rows[0]) == (0, 0, 0, 0)
        assert not original.exists()

        # DELETE repetido → 404
        status, _ = _req(base, "DELETE", f"/courses/{cid}")
        assert status == 404
    finally:
        server.stop()
        ctx.close()
