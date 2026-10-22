"""Testes da task 017 — congelamento do manifesto, smoke real do Docling e
regressões dos achados do ensaio longitudinal (mapa §13.8/§13.10/§13.235).

Não é a suíte quantitativa da etapa 8 (mapa de testes): nenhum resultado de
qualidade é produzido aqui. Tabela de testes (código → caso):

| Código | Caso |
|---|---|
| G-1 | manifesto congelado: hashes de skills = arquivos = catálogo (§8/§13.10) |
| G-2 | manifesto: sha256 do uv.lock confere; timezone permanece null (§3) |
| G-3 | manifesto: modelo Bonsai 2 inalterado e perfil congelado = NON_THINKING_SAMPLER (§3.1) |
| G-4 | manifesto: versões de pacotes = importlib.metadata no .venv (§3) |
| G-5 | smoke real do Docling: blocos com página/bbox e ocr_source=None para texto nativo (§6.2; pulado sem modelos em cache) |
| M-1 | origem de política no pacote de memória: demand_generated não quebra o MemoryPack (achado do ensaio) |
| M-2 | origem desconhecida no evento cai no default observado (§7), sem exceção |
| O-1 | ID de operação por turno: turnos distintos geram IDs distintos; interrupt dentro do turno reusa (§11) |
| O-2 | dois submits na MESMA sessão commitam (regressão do achado do ensaio; §10/§11) |
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing
from pathlib import Path

import pytest

from eduagent.agents.curator import CuratorAgent
from eduagent.agents.librarian import Librarian
from eduagent.agents.monitor import Monitor
from eduagent.agents.planner import PlannerAgent
from eduagent.agents.tutor import EventItemSink, Tutor
from eduagent.contracts import MemoryPack
from eduagent.graph import EduAgentGraph, _turn_operation_id
from eduagent.services.assessment import AssessmentService
from eduagent.services.calendar import CalendarService
from eduagent.services.effects import EffectsService
from eduagent.services.ingestion import (
    DoclingExtractor,
    IngestionService,
    docling_available,
)
from eduagent.services.memory import MemoryService, _pack_origin
from eduagent.services.model_adapter import NON_THINKING_SAMPLER, Sampler
from eduagent.services.retrieval import RetrievalService
from eduagent.services.scheduling import DemandService
from eduagent.skills import SkillCatalog
from eduagent.storage.checkpoints import SQLiteCheckpointer
from eduagent.storage.repository import DomainStore

MANIFEST_PATH = Path("manifest.json")
EXPECTED_MODEL_SHA256 = (
    "53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3"
)
EXPECTED_UV_LOCK_SHA256 = (
    "40c5156cec3cdcb4114c84c686ff298e4f865d9080547068c7e90713748706ff"
)


# ---------------------------------------------------------------------------
# G-1..G-4: congelamento do manifesto (C2)
# ---------------------------------------------------------------------------


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_g1_hashes_de_skills_conferem_com_arquivos_e_catalogo():
    skills = _manifest()["congelamento"]["skills"]
    catalog_path = Path(skills["catalog"])
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert (
        hashlib.sha256(catalog_path.read_bytes()).hexdigest()
        == skills["catalog_sha256"]
    )
    for name, recorded in skills["skill_sha256"].items():
        skill_file = Path(f"eduagent/skills/{name}/skill.yaml")
        digest = hashlib.sha256(skill_file.read_bytes()).hexdigest()
        assert digest == recorded, name
        assert catalog["skills"][name]["sha256"] == recorded, name


def test_g2_uv_lock_e_timezone_null():
    freeze = _manifest()["congelamento"]
    assert (
        hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest()
        == freeze["lock"]["uv_lock_sha256"]
        == EXPECTED_UV_LOCK_SHA256
    )
    assert freeze["lock"]["alterado_na_017"] is False
    # Timezone NÃO confirmada: permanece null (mapa §3) — pendência, não decisão.
    assert freeze["timezone"]["valor"] is None
    assert "PENDENTE" in freeze["timezone"]["estado"]


def test_g3_modelo_inalterado_e_perfil_congelado():
    freeze = _manifest()["congelamento"]
    assert _manifest()["modelo"]["sha256"] == EXPECTED_MODEL_SHA256
    assert _manifest()["modelo"]["arquivo"] == "Ternary-Bonsai-2-27B-PTQ1_0.gguf"
    perfil = freeze["perfil_selecionado"]
    assert perfil["modo"] == "non-thinking"
    sampler = NON_THINKING_SAMPLER
    assert isinstance(sampler, Sampler)
    for campo, valor in perfil["sampler"].items():
        if campo == "max_tokens":
            assert sampler.max_tokens == valor
        else:
            assert getattr(sampler, campo) == valor, campo
    assert sampler.thinking is False
    # Perfil thinking permanece registrado como NÃO validado (§3.1).
    assert "PENDENTE" in json.dumps(
        _manifest()["congelamento"]["pendencias_congelamento"],
        ensure_ascii=False,
    )


def test_g4_versoes_de_pacotes_reais():
    from importlib.metadata import version

    principais = _manifest()["pacotes"]["principais"]
    for pacote, esperado in principais.items():
        instalado = version(pacote.replace("-", "_"))
        # normalização PEP 503: '-' e '_' equivalentes
        assert instalado.replace("_", "-") == esperado.replace("_", "-"), pacote


# ---------------------------------------------------------------------------
# G-5: smoke real do Docling (pulado sem modelos em cache — sem downloads)
# ---------------------------------------------------------------------------


def _layout_models_cached() -> bool:
    hub = Path.home() / ".cache" / "huggingface" / "hub"
    heron = hub / "models--docling-project--docling-layout-heron"
    docmodels = hub / "models--docling-project--docling-models"
    return heron.exists() and docmodels.exists()


@pytest.mark.skipif(
    not docling_available() or not _layout_models_cached(),
    reason="Docling ou modelos de layout ausentes neste ambiente — smoke real pulado sem download",
)
def test_g5_smoke_real_docling_texto_nativo():
    """PDF mínimo gerado em teste (texto nativo) passa pelo pipeline real do
    Docling no subprocesso (spawn, RLIMIT_AS de §3) e devolve blocos com
    página física e proveniência; texto nativo vem com ocr_source=None
    (§6.2: nunca atribuição incondicional de OCR)."""
    import io

    pytest.importorskip("PIL")
    from PIL import Image

    # PDF mínimo de 1 página via imagem renderizada em memória é frágil;
    # aqui usamos um PDF de texto construído por bytes (mesma técnica dos
    # fixtures do ensaio) e conferimos a extração real.
    lines = [
        "Sistemas de informacao - Caderno de aula",
        "A deduplicacao por operation_id ocorre antes da conferencia da",
        "revisao esperada; um retry devolve o recibo anterior.",
    ]

    def esc(s: str) -> str:
        return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    stream = (
        "BT\n/F1 11 Tf\n72 760 Td\n16 TL\n"
        + "\n".join(f"({esc(ln)}) Tj" + (" T*" if i < len(lines) - 1 else "")
                    for i, ln in enumerate(lines))
        + "\nET"
    ).encode("latin-1")
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        4: f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream\n",
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for i in range(1, 6):
        offsets[i] = len(out)
        out += f"{i} 0 obj\n".encode() + objs[i] + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for i in range(1, 6):
        out += f"{offsets[i]:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )

    doc = DoclingExtractor().extract(
        bytes(out), "application/pdf", max_pages=10
    )
    assert doc.total_pages == 1
    texts = [b.text for page in doc.pages for b in page.blocks if b.text]
    assert any("deduplicacao por operation_id" in t for t in texts)
    for page in doc.pages:
        for block in page.blocks:
            if block.legible:
                assert block.ocr_source is None  # nativo, nunca OCR inventado
            assert block.page >= 1


# ---------------------------------------------------------------------------
# M-1/M-2: origem de política no pacote de memória (achado do ensaio)
# ---------------------------------------------------------------------------


def test_m1_origem_de_politica_nao_quebra_memory_pack():
    assert (
        _pack_origin({"origin": "review_after_error"})
        is MemoryPack.Origin.INFERRED
    )
    assert (
        _pack_origin({"origin": "recovery_after_correct"})
        is MemoryPack.Origin.INFERRED
    )
    assert (
        _pack_origin({"origin": "duration_confirmed"})
        is MemoryPack.Origin.ASSERTED
    )


def test_m2_origem_desconhecida_cai_no_default_observed():
    assert _pack_origin({"origin": "desconhecida"}) is MemoryPack.Origin.OBSERVED
    assert _pack_origin({}) is MemoryPack.Origin.OBSERVED
    assert _pack_origin({"origin": "asserted"}) is MemoryPack.Origin.ASSERTED


# ---------------------------------------------------------------------------
# O-1/O-2: ID de operação por turno (achado do ensaio) — §10/§11
# ---------------------------------------------------------------------------


def test_o1_id_por_turno_distinto_e_estavel_no_turno():
    turno_a = {"turn_id": "aaaaaaaa-0000-0000-0000-000000000001"}
    turno_b = {"turn_id": "bbbbbbbb-0000-0000-0000-000000000002"}
    id_a1 = _turn_operation_id(turno_a, "attempt")
    id_a2 = _turn_operation_id(turno_a, "attempt")
    id_b = _turn_operation_id(turno_b, "attempt")
    assert id_a1 == id_a2  # estável dentro do turno (interrupt retomado)
    assert id_a1 != id_b  # turnos distintos têm IDs distintos
    assert _turn_operation_id(turno_a, "assessment") != id_a1


class _FakeResult:
    def __init__(self, text: str) -> None:
        self.text = text
        self.finish_reason = "stop"
        self.prompt_tokens = 10
        self.completion_tokens = 10
        self.thinking = None
        self.model_id = "fake"
        self.seed = 0


class _FakeBackend:
    capabilities = type(
        "Caps", (), {"json_schema": True, "json_schema_evidence": "teste"}
    )()

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)

    def generate(self, messages, schema, sampler, deadline, seed):
        return _FakeResult(self.responses.pop(0))


class _FakeExtractor:
    name = "fake-extractor"
    version = "1"

    def __init__(self, pages: list[list[dict]]) -> None:
        self.pages = pages

    def extract(self, data, mime, *, max_pages, languages=None, on_page=None, cancelled=lambda: False):
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
                    kind=str(b.get("kind", "paragraph")),
                    text=str(b.get("text", "")),
                    order_in_page=o,
                    legible=True,
                )
                for o, b in enumerate(blocks)
            ]
            extracted.pages.append(PageRecord(page=page_no, blocks=records))
        extracted.diagnose_pages()
        return extracted


class _HashEmbedder:
    name = "hash-fake"
    revision = "test"
    dim = 8

    def file_manifest(self) -> dict[str, str]:
        return {"fake": "0" * 64}

    def embed(self, texts):
        import numpy as np

        vecs = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            v = [b / 255.0 for b in digest[: self.dim]]
            n = sum(x * x for x in v) ** 0.5 or 1.0
            vecs.append([x / n for x in v])
        return __import__("numpy").ascontiguousarray(vecs, dtype=np.float32)


def _item_payload() -> str:
    return json.dumps(
        {
            "prompt": "Explique por que a dedup por operation_id vem antes.",
            "expected_answer": "Porque a dedup garante o recibo anterior.",
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


def _open_stack(tmp_path: Path, responses: list[str]):
    import numpy as np

    store = DomainStore.open(tmp_path / "domain.sqlite")
    store.ensure_user(_UID)
    store.execute_write(
        _UID,
        [
            ("INSERT OR IGNORE INTO courses(id, user_id, title) VALUES (?,?,?)", (_COURSE, _UID, "MO810")),
            ("INSERT OR IGNORE INTO topics(id, course_id, title) VALUES (?,?,?)", (_TOPIC, _COURSE, "T")),
        ],
        bump_domain_revision=False,
    )
    clock = lambda: __import__("datetime").datetime(  # noqa: E731
        2026, 10, 21, 12, 0, tzinfo=__import__("datetime").timezone.utc
    )
    effects = EffectsService(store)
    memory = MemoryService(store, effects, clock=clock)
    backend = _FakeBackend(responses)
    graph = EduAgentGraph(
        store=store,
        checkpointer=SQLiteCheckpointer(tmp_path / "checkpoints.sqlite"),
        clock=clock,
        backend=backend,
        tutor=Tutor(
            backend,
            SkillCatalog.load(),
            item_sink=EventItemSink(store, effects, clock=clock),
            clock=clock,
        ),
        librarian=Librarian(memory),
        curator=CuratorAgent(
            store,
            ingestion=IngestionService(
                store, tmp_path / "data", extractor=_FakeExtractor(
                    [[{"kind": "paragraph", "text": "A dedup por operation_id vem antes da conferência de revisão esperada."}]]
                )
            ),
        ),
        retrieval=RetrievalService(store, tmp_path / "data"),
        embedder=_HashEmbedder(),
        memory=memory,
        assessment=AssessmentService(store, effects, clock=clock),
        planner=PlannerAgent(store, effects, clock=clock),
        demands=DemandService(store, effects, clock=clock),
        calendar=CalendarService(store, effects, clock=clock),
        ingestion=IngestionService(
            store, tmp_path / "data", extractor=_FakeExtractor(
                [[{"kind": "paragraph", "text": "A dedup por operation_id vem antes da conferência de revisão esperada."}]]
            )
        ),
        data_root=tmp_path / "data",
    )
    return store, graph, (tmp_path / "data")


_UID = "123e4567-e89b-12d3-a456-426614174000"
_COURSE = "00000000-0000-0000-0000-000000000021"
_TOPIC = "00000000-0000-0000-0000-000000000011"
_SESSION = "7c9e6679-7425-40de-944b-e07fc1f90ae7"


def _ingest_and_index(graph, store, data_root: Path) -> None:
    result = graph.run_turn(
        user_id=_UID,
        session_id=_SESSION,
        message="/ingest documento",
        payload={"data": b"%PDF-1.7\ndedup\n", "course_id": _COURSE},
    )
    assert result.status == "completed", result.output
    ingest = result.output["index"]
    RetrievalService(store, data_root).index_version(
        _UID, ingest["doc_id"], ingest["version_id"], embedder=_HashEmbedder()
    )
    graph._ingestion.activate_version(_UID, ingest["doc_id"], ingest["version_id"])


def test_o2_dois_submits_na_mesma_sessao_commitam(tmp_path: Path):
    """Regressão do achado do ensaio (017): o segundo submit na MESMA sessão
    não pode reusar o operation_id do primeiro (mesmo ID com digest diferente
    é erro, §11)."""
    store, graph, data_root = _open_stack(
        tmp_path,
        [
            _item_payload(),
            _item_payload(),
        ],
    )
    try:
        _ingest_and_index(graph, store, data_root)
        first = graph.run_turn(
            user_id=_UID,
            session_id=_SESSION,
            message="quero praticar",
            intent="practice",
            payload={"course_id": _COURSE, "topic_ids": [_TOPIC]},
        )
        assert first.status == "waiting_student", first.output
        s1 = graph.run_turn(
            user_id=_UID,
            session_id=_SESSION,
            message="Porque a dedup garante que retries devolvam o recibo anterior.",
            intent="submit_answer",
        )
        assert s1.status == "completed", s1.output
        # Prática e submissão NOVAMENTE na mesma sessão.
        second = graph.run_turn(
            user_id=_UID,
            session_id=_SESSION,
            message="quero praticar outra vez",
            intent="practice",
            payload={"course_id": _COURSE, "topic_ids": [_TOPIC]},
        )
        assert second.status == "waiting_student", second.output
        s2 = graph.run_turn(
            user_id=_UID,
            session_id=_SESSION,
            message="Porque a dedup garante que retries devolvam o recibo anterior.",
            intent="submit_answer",
        )
        assert s2.status == "completed", s2.output
        rows = store.fetch_user_rows(
            "SELECT id FROM operations WHERE user_id = ?", (_UID,)
        )
        ids = {str(r["id"]) for r in rows}
        # 2 tentativas + 2 avaliações, todos IDs distintos (§11).
        assert len(ids) >= 4
    finally:
        store.close()
        graph._checkpointer.close()


def _alvo_trivial() -> str:
    return "ok"


def test_run_in_subprocess_spawn_continua_funcionando(tmp_path):
    """Mudança do ensaio (spawn no Docling) não altera o contrato do
    mecanismo: função picklável em nível de módulo executa e devolve."""
    from eduagent.services.ingestion import run_in_subprocess

    assert (
        run_in_subprocess(_alvo_trivial, mem_gib=2, timeout_s=30, start_method="spawn")
        == "ok"
    )
