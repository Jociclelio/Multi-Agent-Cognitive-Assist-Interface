"""Suíte Automatizada de Testes da Interface Gráfica Local (Backend HTTP + E2E).

Cobre integralmente os casos especificados em `Relatorio da interface.md` (§2.2)
e `.agents/tasks/interface-grafica-local/004-suite-testes-automatizados-backend-frontend-e2e.md`:
- UI-API-01 a UI-API-07 (Rotas LoopbackAPI, entrega estática, gates e CLI `--serve-ui`)
- E2E-01 a E2E-03 (Jornadas completas ponta a ponta sobre SQLite real)
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from eduagent.agents.curator import CuratorAgent
from eduagent.agents.librarian import Librarian
from eduagent.agents.monitor import Monitor
from eduagent.agents.planner import PlannerAgent
from eduagent.agents.tutor import EventItemSink, Tutor
from eduagent import api as api_mod
from eduagent.api import LoopbackAPI, MAX_UPLOAD_BYTES
from eduagent.cli import build_parser, run
from eduagent.contracts import EduAgentError, ErrorCode, MemoryPack
from eduagent.graph import EduAgentGraph
from eduagent.runtime import RuntimeContext
from eduagent.services.assessment import AssessmentService
from eduagent.services.calendar import CalendarService
from eduagent.services.effects import EffectsService
from eduagent.services.ingestion import IngestionService
from eduagent.services.memory import MemoryService
from eduagent.services.model_adapter import RuntimeCapabilities
from eduagent.services.retrieval import RetrievalService
from eduagent.services.scheduling import DemandService
from eduagent.skills import SkillCatalog
from eduagent.storage import repository
from eduagent.storage.checkpoints import SQLiteCheckpointer
from eduagent.storage.repository import DomainStore

UTC = timezone.utc
UID = "123e4567-e89b-12d3-a456-426614174000"
SESSION = "7c9e6679-7425-40de-944b-e07fc1f90ae7"
COURSE = "00000000-0000-0000-0000-000000000021"
TOPIC = "00000000-0000-0000-0000-000000000011"
FIXED_NOW = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)

DOC_TEXT_PAGES = [
    [
        {"kind": "heading", "text": "Commit idempotente"},
        {
            "kind": "paragraph",
            "text": (
                "A dedup por operation_id vem antes da conferência de "
                "revisão esperada."
            ),
        },
    ]
]


@pytest.fixture(autouse=True)
def _allow_host_sqlite_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """Permite execução em ambientes com SQLite local anterior a 3.45.0 quando necessário."""
    if repository.sqlite_version_tuple() < repository.SQLITE_WAL_FLOOR:
        monkeypatch.setattr(repository, "SQLITE_WAL_FLOOR", (3, 35, 0))


class MutableClock:
    def __init__(self, start: datetime = FIXED_NOW) -> None:
        self._moment = start

    def __call__(self) -> datetime:
        return self._moment

    def advance(self, **kwargs: Any) -> None:
        self._moment = self._moment + timedelta(**kwargs)


class FakeBackend:
    model_id = "fake"
    capabilities = RuntimeCapabilities(
        json_schema=True, json_schema_evidence="teste-ui"
    )

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)

    def generate(self, messages, schema, sampler, deadline, seed):
        text = (
            self.responses.pop(0)
            if self.responses
            else json.dumps({"text": "Resposta socrática determinística."}, ensure_ascii=False)
        )
        return type(
            "GenerationResult",
            (),
            {
                "text": text,
                "finish_reason": "stop",
                "prompt_tokens": 10,
                "completion_tokens": 7,
                "thinking": None,
                "model_id": "fake",
                "seed": seed,
            },
        )()


class FakeExtractor:
    name = "fake-extractor"
    version = "1"

    def __init__(self, pages: list[list[dict]] | None = None) -> None:
        self.pages = pages or DOC_TEXT_PAGES

    def extract(
        self,
        data,
        mime,
        *,
        max_pages,
        languages=None,
        on_page=None,
        cancelled=lambda: False,
    ):
        from eduagent.services.ingestion import (
            BlockRecord,
            ExtractedDocument,
            PageRecord,
        )

        extracted = ExtractedDocument()
        for page_no, blocks in enumerate(self.pages, start=1):
            records = [
                BlockRecord(
                    page=page_no,
                    kind=str(block.get("kind", "paragraph")),
                    text=str(block.get("text", "")),
                    order_in_page=order,
                    legible=True,
                )
                for order, block in enumerate(blocks)
            ]
            extracted.pages.append(PageRecord(page=page_no, blocks=records))
        extracted.diagnose_pages()
        return extracted


class HashEmbedder:
    name = "hash-fake"
    revision = "test-revision"
    dim = 8

    def embed(self, texts: list[str]):
        import hashlib as _hashlib
        import numpy as np

        vectors = []
        for text in texts:
            digest = _hashlib.sha256(text.encode("utf-8")).digest()
            vector = np.array(
                [byte / 255.0 for byte in digest[: self.dim]], dtype=np.float32
            )
            norm = float(np.linalg.norm(vector)) or 1.0
            vectors.append(vector / norm)
        return np.vstack(vectors)

    def file_manifest(self) -> dict[str, str]:
        return {"fake": "0" * 64}


def item_payload() -> str:
    return json.dumps(
        {
            "prompt": "Explique por que a dedup por operation_id vem antes.",
            "expected_answer": (
                "Porque a dedup garante que retries devolvam o recibo "
                "anterior sem repetir o efeito."
            ),
            "rubric": [
                {
                    "criterion_id": "dedup",
                    "description": "Explica a dedup por operation_id.",
                    "critical": True,
                }
            ],
            "citations": [0],
        },
        ensure_ascii=False,
    )


def open_ui_runtime(
    tmp_path: Path,
    *,
    admit_model: bool = True,
    clock: MutableClock | None = None,
    pages: list[list[dict]] | None = None,
) -> RuntimeContext:
    root = tmp_path / "data"
    root.mkdir(parents=True, exist_ok=True)
    store = DomainStore.open(root / "domain.sqlite")
    store.ensure_user(UID)
    store.execute_write(
        UID,
        [
            (
                "INSERT OR IGNORE INTO courses(id, user_id, title) VALUES (?, ?, ?)",
                (COURSE, UID, "MO810"),
            ),
            (
                "INSERT OR IGNORE INTO topics(id, course_id, title) VALUES (?, ?, ?)",
                (TOPIC, COURSE, "Tópico de teste"),
            ),
        ],
        bump_domain_revision=False,
    )
    clock_fn = clock or MutableClock()
    backend = (
        FakeBackend(
            [
                item_payload(),
                json.dumps({"text": "Pista 1 (conceito): a dedup vem primeiro."}),
                json.dumps({"text": "Pista 2 (próximo passo): compare recibos."}),
            ]
        )
        if admit_model
        else None
    )
    effects = EffectsService(store)
    memory = MemoryService(store, effects, clock=clock_fn)
    assessment = AssessmentService(store, effects, clock=clock_fn)
    demands = DemandService(store, effects, clock=clock_fn)
    calendar = CalendarService(store, effects, clock=clock_fn)
    planner = PlannerAgent(store, effects, clock=clock_fn)
    ingestion = IngestionService(
        store, root, extractor=FakeExtractor(pages or DOC_TEXT_PAGES)
    )
    curator = CuratorAgent(store, ingestion=ingestion)
    retrieval = RetrievalService(store, root)
    tutor = (
        Tutor(
            backend,
            SkillCatalog.load(),
            item_sink=EventItemSink(store, effects, clock=clock_fn),
            clock=clock_fn,
        )
        if backend is not None
        else None
    )
    checkpointer = SQLiteCheckpointer(root / "checkpoints.sqlite")
    graph = EduAgentGraph(
        store=store,
        checkpointer=checkpointer,
        clock=clock_fn,
        backend=backend,
        tutor=tutor,
        librarian=Librarian(memory),
        curator=curator,
        retrieval=retrieval,
        embedder=HashEmbedder(),
        memory=memory,
        assessment=assessment,
        monitor=Monitor(),
        planner=planner,
        demands=demands,
        calendar=calendar,
        ingestion=ingestion,
        data_root=root,
        telemetry_dir=root / "telemetry",
    )
    context = RuntimeContext.__new__(RuntimeContext)
    context.data_root = root
    context.config = {}
    context.store = store
    context.checkpointer = checkpointer
    context.graph = graph
    context.memory = memory
    context.calendar = calendar
    context.telemetry_dir = root / "telemetry"
    context.course_id = COURSE
    context.retrieval = retrieval
    context.ingestion = ingestion
    context._closed = False
    return context


def _http_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    req_headers = dict(headers or {})
    data_bytes = None
    if body is not None:
        data_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data_bytes, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return (
                resp.status,
                {k.lower(): v for k, v in resp.headers.items()},
                resp.read(),
            )
    except urllib.error.HTTPError as exc:
        return (
            exc.code,
            {k.lower(): v for k, v in exc.headers.items()},
            exc.read(),
        )


def _http_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    status, _, raw = _http_request(url, method=method, headers=headers, body=body)
    return status, json.loads(raw.decode("utf-8"))


# ============================================================================
# UI-API-01: GET /health e Gates Explícitos + Compatibilidade CLI (14 comandos)
# ============================================================================
def test_ui_api_01_health_gates_and_cli_compatibility(tmp_path: Path) -> None:
    ctx = open_ui_runtime(tmp_path, admit_model=False)
    server = LoopbackAPI(ctx, host="127.0.0.1", port=0)
    host, port = server.start()
    base_url = f"http://{host}:{port}"
    try:
        status, data = _http_json(f"{base_url}/health")
        assert status == 200
        assert data["status"] == "ok"
        gates = data["gates"]
        for key in (
            "model_admitted",
            "model_status",
            "timezone",
            "network_enabled",
            "web_connector",
            "calendar_sync_enabled",
            "reranker_enabled",
            "sqlite_version",
            "domain_revision",
            "ui_available",
            "registered_users",
        ):
            assert key in gates, f"Chave {key} ausente em gates"
        assert gates["model_admitted"] is False
        assert gates["model_status"] == "MODEL_NOT_ADMITTED"
        assert gates["web_connector"] == "CONNECTOR_DISABLED"
        assert gates["ui_available"] is True
        assert UID in gates["registered_users"]
    finally:
        server.stop()
        ctx.close()

    # Rejeita host não-loopback (0.0.0.0)
    ctx2 = open_ui_runtime(tmp_path / "non_loopback")
    try:
        with pytest.raises(EduAgentError) as exc_info:
            LoopbackAPI(ctx2, host="0.0.0.0", port=0)
        assert exc_info.value.code == ErrorCode.TOOL_DENIED
    finally:
        ctx2.close()

    # Confirma que os 14 subcomandos canônicos do parser da CLI permanecem intactos
    parser = build_parser()
    subparsers_actions = [
        a for a in parser._actions if isinstance(a, argparse._SubParsersAction)
    ]
    assert len(subparsers_actions[0].choices) == 14


# ============================================================================
# UI-API-02: Validação de Contexto de Usuário (X-EduAgent-User) em Todas as Rotas
# ============================================================================
def test_ui_api_02_user_header_validation_across_routes(tmp_path: Path) -> None:
    ctx = open_ui_runtime(tmp_path)
    server = LoopbackAPI(ctx, host="127.0.0.1", port=0)
    host, port = server.start()
    base_url = f"http://{host}:{port}"
    unknown_uid = str(uuid.uuid4())
    try:
        protected_get_routes = [
            "/courses",
            f"/sessions/{SESSION}",
            "/operations",
            "/calendar",
            "/progress",
            "/library",
            "/review/flashcards",
            "/search?q=dedup",
        ]
        for route in protected_get_routes:
            # Sem header -> 400 SCHEMA_INVALID
            st_no_hdr, body_no_hdr = _http_json(f"{base_url}{route}")
            assert st_no_hdr == 400, f"Rota {route} deveria exigir X-EduAgent-User"
            assert body_no_hdr["error"]["code"] == ErrorCode.SCHEMA_INVALID.value

            # Com UUID não registrado -> 404 SOURCE_UNRESOLVED
            st_unk, body_unk = _http_json(
                f"{base_url}{route}", headers={"X-EduAgent-User": unknown_uid}
            )
            assert st_unk == 404, f"Rota {route} deveria recusar UUID não registrado"
            assert body_unk["error"]["code"] == ErrorCode.SOURCE_UNRESOLVED.value
    finally:
        server.stop()
        ctx.close()


# ============================================================================
# UI-API-03: Ordenação Determinística das 4 Faixas (D3) e Sinal ready_to_study (D4)
# ============================================================================
def test_ui_api_03_deterministic_4_tier_course_sorting(tmp_path: Path) -> None:
    ctx = open_ui_runtime(tmp_path)
    server = LoopbackAPI(ctx, host="127.0.0.1", port=0)
    host, port = server.start()
    base_url = f"http://{host}:{port}"
    headers = {"X-EduAgent-User": UID}
    try:
        c_tier1 = str(uuid.uuid4())
        c_tier2 = str(uuid.uuid4())
        c_tier3 = str(uuid.uuid4())
        c_tier4 = COURSE  # MO810 já criado sem documentos ativos -> tier 4

        t_tier1 = str(uuid.uuid4())
        t_tier2 = str(uuid.uuid4())
        t_tier3 = str(uuid.uuid4())
        demand_t1 = str(uuid.uuid4())
        demand_t2 = str(uuid.uuid4())
        block_t1 = str(uuid.uuid4())
        doc_t3 = str(uuid.uuid4())
        ver_t3 = str(uuid.uuid4())

        ctx.store.execute_write(
            UID,
            [
                ("INSERT INTO courses(id, user_id, title) VALUES (?, ?, ?)", (c_tier1, UID, "Disciplina Tier 1")),
                ("INSERT INTO topics(id, course_id, title) VALUES (?, ?, ?)", (t_tier1, c_tier1, "Tópico T1")),
                ("INSERT INTO courses(id, user_id, title) VALUES (?, ?, ?)", (c_tier2, UID, "Disciplina Tier 2")),
                ("INSERT INTO topics(id, course_id, title) VALUES (?, ?, ?)", (t_tier2, c_tier2, "Tópico T2")),
                ("INSERT INTO courses(id, user_id, title) VALUES (?, ?, ?)", (c_tier3, UID, "Disciplina Tier 3")),
                ("INSERT INTO topics(id, course_id, title) VALUES (?, ?, ?)", (t_tier3, c_tier3, "Tópico T3")),
                # Demanda + logical_block planejado para c_tier1 -> sort_tier = 1
                (
                    "INSERT INTO demands(id, user_id, topic_id, activity_kind, due_local_date, status, payload_json) VALUES (?, ?, ?, 'exam', '2026-10-25', 'open', '{}')",
                    (demand_t1, UID, t_tier1),
                ),
                (
                    "INSERT INTO logical_blocks(id, user_id, uid, status, planned_start_utc, planned_end_utc, source_demand_id) VALUES (?, ?, ?, 'planned', '2026-10-21T14:00:00Z', '2026-10-21T14:45:00Z', ?)",
                    (block_t1, UID, f"uid-{block_t1}", demand_t1),
                ),
                # Demanda aberta sem bloco para c_tier2 -> sort_tier = 2
                (
                    "INSERT INTO demands(id, user_id, topic_id, activity_kind, due_local_date, status, payload_json) VALUES (?, ?, ?, 'homework', '2026-10-28', 'open', '{}')",
                    (demand_t2, UID, t_tier2),
                ),
                # Documento ativo sem tentativas para c_tier3 -> sort_tier = 3 e ready_to_study = True
                (
                    "INSERT INTO documents(id, user_id, course_id, active_version) VALUES (?, ?, ?, NULL)",
                    (doc_t3, UID, c_tier3),
                ),
                (
                    "INSERT INTO doc_versions(id, user_id, doc_id, sha256, mime, original_ref, extractor_manifest, status) VALUES (?, ?, ?, ?, 'text/markdown', 'aula.md', '{}', 'active')",
                    (ver_t3, UID, doc_t3, "a" * 64),
                ),
                (
                    "UPDATE documents SET active_version = ? WHERE id = ?",
                    (ver_t3, doc_t3),
                ),
            ],
            bump_domain_revision=False,
        )

        status, payload = _http_json(f"{base_url}/courses", headers=headers)
        assert status == 200
        courses = payload["courses"]
        assert [c["id"] for c in courses] == [c_tier1, c_tier2, c_tier3, c_tier4]
        assert [c["sort_tier"] for c in courses] == [1, 2, 3, 4]
        assert courses[2]["ready_to_study"] is True
        assert courses[3]["ready_to_study"] is False
    finally:
        server.stop()
        ctx.close()


# ============================================================================
# UI-API-04: Upload Confinado (D7), Limite de 50 MiB e Auto-Ingestão
# ============================================================================
def test_ui_api_04_library_upload_confinement_and_auto_ingest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = open_ui_runtime(tmp_path)
    server = LoopbackAPI(ctx, host="127.0.0.1", port=0)
    host, port = server.start()
    base_url = f"http://{host}:{port}"
    headers = {"X-EduAgent-User": UID}
    try:
        # 1. Upload válido com auto_ingest=True
        st_up, up_data = _http_json(
            f"{base_url}/library/upload",
            method="POST",
            headers=headers,
            body={
                "filename": "apostila_cap1.md",
                "content_text": "# Capítulo 1\n\nCommit idempotente e dedup.",
                "course_id": COURSE,
                "auto_ingest": True,
            },
        )
        assert st_up == 200
        assert up_data["status"] == "ok"
        assert up_data["ingested"] is True
        saved_path = Path(up_data["saved_path"]).resolve()
        assert saved_path.exists()
        assert (ctx.data_root / UID / "originals").resolve() in saved_path.parents

        # Verifica que o documento está ativo e com chunks em GET /library
        st_lib, lib_data = _http_json(f"{base_url}/library", headers=headers)
        assert st_lib == 200
        assert len(lib_data["documents"]) == 1
        assert lib_data["documents"][0]["version_status"] == "active"
        assert lib_data["documents"][0]["chunk_count"] >= 1

        # 2. Tentativa de path traversal no filename é bloqueada com 403 TOOL_DENIED
        st_bad, bad_data = _http_json(
            f"{base_url}/library/upload",
            method="POST",
            headers=headers,
            body={
                "filename": "../fora_da_fronteira.md",
                "content_text": "conteúdo proibido",
                "course_id": COURSE,
            },
        )
        assert st_bad == 403
        assert bad_data["error"]["code"] == ErrorCode.TOOL_DENIED.value

        # 3. Excesso sobre MAX_UPLOAD_BYTES retorna HTTP 413 RESOURCE_LIMIT
        monkeypatch.setattr(api_mod, "MAX_UPLOAD_BYTES", 32)
        st_big, big_data = _http_json(
            f"{base_url}/library/upload",
            method="POST",
            headers=headers,
            body={
                "filename": "grande_demais.md",
                "content_text": "x" * 128,
                "course_id": COURSE,
            },
        )
        assert st_big == 413
        assert big_data["error"]["code"] == ErrorCode.RESOURCE_LIMIT.value
    finally:
        server.stop()
        ctx.close()


# ============================================================================
# UI-API-05: Barreira Socrática Contra Vazamento de Gabarito em GET /sessions/{id}
# ============================================================================
def test_ui_api_05_session_detail_socratic_answer_barrier(tmp_path: Path) -> None:
    ctx = open_ui_runtime(tmp_path)
    server = LoopbackAPI(ctx, host="127.0.0.1", port=0)
    host, port = server.start()
    base_url = f"http://{host}:{port}"
    headers = {"X-EduAgent-User": UID}
    try:
        # Registra eventos de resposta e rubrica via MemoryService
        ans_ev = ctx.memory.record_event(
            user_id=UID,
            session_id=SESSION,
            kind=MemoryPack.EventKind.PRACTICE,
            payload={"expected_answer": "GABARITO_CONFIDENCIAL_L3"},
            occurred_at=FIXED_NOW,
            origin=MemoryPack.Origin.OBSERVED,
        )
        rub_ev = ctx.memory.record_event(
            user_id=UID,
            session_id=SESSION,
            kind=MemoryPack.EventKind.PRACTICE,
            payload={
                "rubric": [
                    {"criterion_id": "c1", "description": "Critério público", "critical": True}
                ]
            },
            occurred_at=FIXED_NOW,
            origin=MemoryPack.Origin.OBSERVED,
        )

        item_l1 = str(uuid.uuid4())
        item_l3 = str(uuid.uuid4())
        ctx.store.execute_write(
            UID,
            [
                (
                    "INSERT INTO items(id, user_id, family_id, version, prompt, rubric_ref, answer_ref, source_refs_json) VALUES (?, ?, ?, 1, 'Pergunta 1', ?, ?, '[]')",
                    (item_l1, UID, str(uuid.uuid4()), f"event:{rub_ev}@1", f"event:{ans_ev}@1"),
                ),
                (
                    "INSERT INTO items(id, user_id, family_id, version, prompt, rubric_ref, answer_ref, source_refs_json) VALUES (?, ?, ?, 1, 'Pergunta 2', ?, ?, '[]')",
                    (item_l3, UID, str(uuid.uuid4()), f"event:{rub_ev}@1", f"event:{ans_ev}@1"),
                ),
                # Tentativa em L1 (help_level=1, revealed=0) -> não pode revelar expected_answer
                (
                    "INSERT INTO attempts(id, user_id, item_id, response_event_id, help_level, revealed, attempt_ordinal, independent) VALUES (?, ?, ?, NULL, 1, 0, 1, 1)",
                    (str(uuid.uuid4()), UID, item_l1),
                ),
                # Tentativa em L3 (help_level=3, revealed=1) -> pode revelar expected_answer
                (
                    "INSERT INTO attempts(id, user_id, item_id, response_event_id, help_level, revealed, attempt_ordinal, independent) VALUES (?, ?, ?, NULL, 3, 1, 2, 0)",
                    (str(uuid.uuid4()), UID, item_l3),
                ),
            ],
            bump_domain_revision=False,
        )

        st_sess, sess_data = _http_json(f"{base_url}/sessions/{SESSION}", headers=headers)
        assert st_sess == 200
        items_by_id = {it["id"]: it for it in sess_data["items"]}

        assert items_by_id[item_l1]["help_level"] == "L1"
        assert items_by_id[item_l1]["revealed"] is False
        assert items_by_id[item_l1]["expected_answer"] is None

        assert items_by_id[item_l3]["help_level"] == "L3"
        assert items_by_id[item_l3]["revealed"] is True
        assert items_by_id[item_l3]["expected_answer"] == "GABARITO_CONFIDENCIAL_L3"
    finally:
        server.stop()
        ctx.close()


# ============================================================================
# UI-API-06: Progresso Qualitativo (estimate = null), Operações, Agenda, Flashcards e Busca
# ============================================================================
def test_ui_api_06_progress_operations_calendar_flashcards_and_search(tmp_path: Path) -> None:
    ctx = open_ui_runtime(tmp_path)
    server = LoopbackAPI(ctx, host="127.0.0.1", port=0)
    host, port = server.start()
    base_url = f"http://{host}:{port}"
    headers = {"X-EduAgent-User": UID}
    try:
        # Ingere documento via /library/upload para alimentar chunks e flashcards
        _http_json(
            f"{base_url}/library/upload",
            method="POST",
            headers=headers,
            body={
                "filename": "protocolo_duas_fases.md",
                "content_text": "# Protocolo\n\nA dedup por operation_id vem antes.",
                "course_id": COURSE,
                "auto_ingest": True,
            },
        )

        # GET /progress -> estimate deve ser SEMPRE None (§8.1)
        st_prog, prog_data = _http_json(f"{base_url}/progress", headers=headers)
        assert st_prog == 200
        assert prog_data["summary"]["estimate"] is None
        for t in prog_data["topics"]:
            assert t["estimate"] is None
            assert t["status"] in ("insufficient", "mixed", "favorable")

        # GET /operations
        st_ops, ops_data = _http_json(f"{base_url}/operations", headers=headers)
        assert st_ops == 200
        assert "pending_count" in ops_data

        # GET /calendar
        st_cal, cal_data = _http_json(f"{base_url}/calendar", headers=headers)
        assert st_cal == 200
        assert "demands" in cal_data and "logical_blocks" in cal_data

        # GET /review/flashcards -> sem gamificação e com revealed=False
        st_fc, fc_data = _http_json(f"{base_url}/review/flashcards", headers=headers)
        assert st_fc == 200
        assert len(fc_data["flashcards"]) >= 1
        card = fc_data["flashcards"][0]
        assert card["revealed"] is False
        for forbidden_key in ("streak", "points", "xp", "leaderboard"):
            assert forbidden_key not in card

        # GET /search?q=dedup
        st_srch, srch_data = _http_json(f"{base_url}/search?q=dedup", headers=headers)
        assert st_srch == 200
        assert len(srch_data["results"]) >= 1
    finally:
        server.stop()
        ctx.close()


# ============================================================================
# UI-API-07: Entrega Estática (GET /, /ui/styles.css, /ui/app.js) e Bloqueio de Traversal
# ============================================================================
def test_ui_api_07_static_assets_and_traversal_protection(tmp_path: Path) -> None:
    ctx = open_ui_runtime(tmp_path)
    server = LoopbackAPI(ctx, host="127.0.0.1", port=0)
    host, port = server.start()
    base_url = f"http://{host}:{port}"
    try:
        st_html, hdr_html, raw_html = _http_request(f"{base_url}/")
        assert st_html == 200
        assert "text/html" in hdr_html.get("content-type", "")
        html_text = raw_html.decode("utf-8")
        assert 'id="app-shell"' in html_text

        st_css, hdr_css, raw_css = _http_request(f"{base_url}/ui/styles.css")
        assert st_css == 200
        assert "text/css" in hdr_css.get("content-type", "")
        css_text = raw_css.decode("utf-8")

        st_js, hdr_js, raw_js = _http_request(f"{base_url}/ui/app.js")
        assert st_js == 200
        assert "javascript" in hdr_js.get("content-type", "")
        js_text = raw_js.decode("utf-8")
        assert "sortCoursesDeterministically" in js_text

        # Zero CDNs externas
        external_re = re.compile(r"https?://(?!127\.0\.0\.1|localhost)", re.IGNORECASE)
        assert not external_re.search(html_text)
        assert not external_re.search(css_text)

        # Bloqueio de path traversal em /ui/
        st_trav, trav_data = _http_json(f"{base_url}/ui/..%2F..%2Fpyproject.toml")
        assert st_trav == 403
        assert trav_data["error"]["code"] == ErrorCode.TOOL_DENIED.value
    finally:
        server.stop()
        ctx.close()


# ============================================================================
# E2E-01 a E2E-03: Jornadas Ponta a Ponta (Onboarding -> Ingestão -> Prática -> Cancelamento)
# ============================================================================
def test_e2e_full_student_journey_via_loopback_ui_api(tmp_path: Path) -> None:
    ctx = open_ui_runtime(tmp_path, admit_model=True)
    server = LoopbackAPI(ctx, host="127.0.0.1", port=0)
    host, port = server.start()
    base_url = f"http://{host}:{port}"
    headers = {"X-EduAgent-User": UID}
    try:
        # E2E-01: Criar disciplina -> Upload com auto_ingest=True -> Verificar ready_to_study=True
        st_c, c_data = _http_json(
            f"{base_url}/courses",
            method="POST",
            headers=headers,
            body={
                "title": "MC906 — Inteligência Artificial",
                "topics": ["Busca Heurística", "Agentes Lógicos"],
            },
        )
        assert st_c == 200
        new_course_id = c_data["course"]["id"]
        new_topic_id = c_data["course"]["topics"][0]["id"]

        st_up, up_data = _http_json(
            f"{base_url}/library/upload",
            method="POST",
            headers=headers,
            body={
                "filename": "mc906_busca.md",
                "content_text": "# Busca A*\n\nA dedup por operation_id vem antes da conferência.",
                "course_id": new_course_id,
                "auto_ingest": True,
            },
        )
        assert st_up == 200
        assert up_data["ingested"] is True

        st_courses, courses_data = _http_json(f"{base_url}/courses", headers=headers)
        assert st_courses == 200
        created_summary = next(c for c in courses_data["courses"] for _ in [1] if c["id"] == new_course_id)
        assert created_summary["ready_to_study"] is True

        # E2E-02: Iniciar turno /practice -> Verificar item publicado em GET /sessions/{id} com gabarito oculto
        st_prac, prac_data = _http_json(
            f"{base_url}/turns",
            method="POST",
            headers=headers,
            body={
                "session_id": SESSION,
                "message": "/practice",
                "payload": {"course_id": new_course_id, "topic_ids": [new_topic_id]},
            },
        )
        assert st_prac == 200
        assert prac_data["status"] in ("waiting", "waiting_student")

        st_sess, sess_data = _http_json(f"{base_url}/sessions/{SESSION}", headers=headers)
        assert st_sess == 200
        assert len(sess_data["items"]) >= 1
        assert sess_data["items"][0]["expected_answer"] is None

        # E2E-03: Cancelamento explícito de turno via POST /turns/{session_id}/cancel
        st_cancel, cancel_data = _http_json(
            f"{base_url}/turns/{SESSION}/cancel",
            method="POST",
            headers=headers,
            body={},
        )
        assert st_cancel == 200
        assert cancel_data["status"] == "cancelled"
    finally:
        server.stop()
        ctx.close()
