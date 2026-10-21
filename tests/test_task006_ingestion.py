"""Testes de aceite da task 006 — ingestão, OCR seletivo, proveniência e
fatos candidatos (mapa §6.1–3, §3, §12; §15.1 para ownership).

Não é a suíte quantitativa da etapa 8 (mapa de testes): são testes locais de
curta duração que verificam os critérios C1–C3 da task com extratores
injetados (o Docling real exige download de modelos de layout, fora das
autorizações de download desta task — impedimento documentado no task.md).
C4 (mapa intocado, commits separados, submodule intocado) é verificado por
inspeção de git e registrado no task.md.
"""

from __future__ import annotations

import functools
import json
import pickle
import resource
import sqlite3
import time
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from eduagent.agents.curator import (
    _FACT_NAMESPACE,
    CuratorAgent,
    detect_prerequisite_cycles,
    resolve_relative_date,
    validate_against_source,
    validate_date,
    validate_number,
)
from eduagent.contracts import (
    AcademicFact,
    EduAgentError,
    ErrorCode,
    SenderRole,
)
from eduagent.services import ingestion as ingestion_mod
from eduagent.services.ingestion import (
    DIAGNOSTIC,
    DoclingExtractor,
    ExtractionJob,
    ExtractedDocument,
    IngestionLimits,
    IngestionService,
    BlockRecord,
    PageRecord,
    _docling_pages_payload,
    _deterministic_block_id,
    canonical_original_path,
    run_in_subprocess,
    sniff_mime,
)
from eduagent.storage.repository import DomainStore

UID = "123e4567-e89b-12d3-a456-426614174000"
UID2 = "223e4567-e89b-12d3-a456-426614174000"
PDF_BYTES = b"%PDF-1.7\nconteudo de teste\n"


def make_uuid() -> str:
    return str(_uuid.uuid4())


# ---------------------------------------------------------------------------
# Extrator fake (mesmo protocolo de BlockExtractor)
# ---------------------------------------------------------------------------


class FakeExtractor:
    """Extrator determinístico para testes de pipeline (fronteira injetável).

    ``pages`` é uma lista de páginas; cada página é uma lista de dicts com
    ``kind``/``text``/``legible``/``ocr_source``. ``languages_for_ocr`` troca
    as páginas quando o OCR seletivo reextrai (deriva páginas OCR).
    """

    name = "fake-extractor"
    version = "1"

    def __init__(
        self,
        pages: list[list[dict]],
        *,
        ocr_pages: list[list[dict]] | None = None,
        respect_max_pages: bool = True,
    ) -> None:
        self.pages = pages
        self.ocr_pages = ocr_pages
        self.respect_max_pages = respect_max_pages
        self.calls: list[dict] = []
        self.page_callbacks: list[int] = []

    def extract(
        self,
        data: bytes,
        mime: str,
        *,
        max_pages: int,
        languages=None,
        on_page=None,
        cancelled=lambda: False,
    ) -> ExtractedDocument:
        self.calls.append({"languages": languages, "mime": mime})
        source = self.ocr_pages if (languages and self.ocr_pages) else self.pages
        extracted = ExtractedDocument()
        for page_no, blocks in enumerate(source, start=1):
            if cancelled():
                raise EduAgentError(
                    ErrorCode.CANCELLED,
                    "extração cancelada (mapa §12)",
                    diagnostic=DIAGNOSTIC,
                )
            if self.respect_max_pages and page_no > max_pages:
                break
            records = [
                BlockRecord(
                    page=page_no,
                    kind=str(block.get("kind", "paragraph")),
                    text=str(block.get("text", "")),
                    order_in_page=order,
                    legible=bool(block.get("legible", True)),
                    ocr_source=block.get("ocr_source"),
                )
                for order, block in enumerate(blocks)
            ]
            extracted.pages.append(PageRecord(page=page_no, blocks=records))
            self.page_callbacks.append(page_no)
            if on_page is not None:
                on_page(page_no)
        extracted.diagnose_pages()
        return extracted


def _heading(text: str) -> dict:
    return {"kind": "heading", "text": text}


def _paragraph(text: str) -> dict:
    return {"kind": "paragraph", "text": text}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path: Path) -> DomainStore:
    s = DomainStore.open(tmp_path / "domain.sqlite")
    s.ensure_user(UID)
    yield s
    s.close()


@pytest.fixture()
def course(store: DomainStore) -> str:
    course_id = make_uuid()
    store.execute_write(
        UID, [("INSERT INTO courses(id, user_id, title) VALUES (?,?,?)", (course_id, UID, "MO810"))]
    )
    return course_id


def _service(store: DomainStore, tmp_path: Path, extractor=None, **kw) -> IngestionService:
    return IngestionService(
        store, tmp_path / "data", extractor=extractor, **kw
    )


# ---------------------------------------------------------------------------
# C1 — validação de entrada, duplicata e ciclo de versão (§6.1, §3)
# ---------------------------------------------------------------------------


class TestC1MimeAndLimits:
    def test_mime_by_bytes(self) -> None:
        assert sniff_mime(PDF_BYTES) == "application/pdf"
        assert sniff_mime("texto simples".encode()) == "text/plain"
        assert sniff_mime(b"\x00\x01\x02\x03") is None
        assert sniff_mime(b"") is None

    def test_declared_mime_divergent_from_bytes_refused(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        service = _service(store, tmp_path)
        with pytest.raises(EduAgentError) as exc:
            service.ingest(
                UID, course, PDF_BYTES, declared_mime="text/plain"
            )
        assert exc.value.code is ErrorCode.SCHEMA_INVALID

    def test_binary_bytes_refused(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        service = _service(store, tmp_path)
        with pytest.raises(EduAgentError) as exc:
            service.ingest(UID, course, b"\x00\x01binario")
        assert exc.value.code is ErrorCode.SCHEMA_INVALID

    def test_oversized_refused(self, store: DomainStore, tmp_path: Path, course: str) -> None:
        limits = IngestionLimits(max_size_bytes=8, max_pages=500)
        service = _service(store, tmp_path, limits=limits)
        with pytest.raises(EduAgentError) as exc:
            service.ingest(UID, course, PDF_BYTES)
        assert exc.value.code is ErrorCode.RESOURCE_LIMIT
        # Nada foi arquivado nem versionado (recusa antes de qualquer efeito).
        assert not list((tmp_path / "data" / UID / "originals").glob("*")) if (
            tmp_path / "data" / UID / "originals"
        ).exists() else True

    def test_ownership_user_and_course(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        service = _service(store, tmp_path)
        # Usuário inexistente → SOURCE_UNRESOLVED.
        with pytest.raises(EduAgentError) as exc:
            service.ingest(UID2, course, PDF_BYTES)
        assert exc.value.code is ErrorCode.SOURCE_UNRESOLVED
        # Disciplina de outro dono → SOURCE_UNRESOLVED (§15.1).
        store.ensure_user(UID2)
        other_course = make_uuid()
        store.execute_write(
            UID2,
            [("INSERT INTO courses(id, user_id, title) VALUES (?,?,?)", (other_course, UID2, "Outra"))],
        )
        with pytest.raises(EduAgentError) as exc:
            service.ingest(UID, other_course, PDF_BYTES)
        assert exc.value.code is ErrorCode.SOURCE_UNRESOLVED

    def test_canonical_path_ignores_filename_and_blocks_traversal(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        extractor = FakeExtractor([[_heading("Cap 1")], [_paragraph("texto suficiente para nao ser ruidoso nesta pagina de teste")]])
        service = _service(store, tmp_path, extractor=extractor)
        result = service.ingest(
            UID, course, PDF_BYTES, filename="../../etc/passwd.pdf"
        )
        path = Path(result.original_path)
        assert path.is_relative_to("123e4567-e89b-12d3-a456-426614174000/originals")
        assert path.suffix == ".pdf"
        assert path.name == f"{result.sha256}.pdf"
        assert (tmp_path / "data" / path).is_file()
        with pytest.raises(EduAgentError):
            canonical_original_path(tmp_path / "data", UID, "ZZ" * 32, "application/pdf")

    def test_page_limit_defense(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        # Extrator mal-comportado ignora max_pages; o serviço defende (§3).
        pages = [[_paragraph(f"pagina {i} com texto")] for i in range(1, 6)]
        extractor = FakeExtractor(pages, respect_max_pages=False)
        limits = IngestionLimits(max_pages=3)
        service = _service(store, tmp_path, limits=limits, extractor=extractor)
        with pytest.raises(EduAgentError) as exc:
            service.ingest(UID, course, PDF_BYTES)
        assert exc.value.code is ErrorCode.RESOURCE_LIMIT
        assert service.version_status(UID, _last_version(store, UID)) == "failed"


def _last_version(store: DomainStore, user_id: str) -> str:
    rows = store.fetch_user_rows(
        "SELECT id FROM doc_versions WHERE user_id = ? ORDER BY rowid DESC LIMIT 1",
        (user_id,),
    )
    return str(rows[0]["id"])


class TestC1DuplicateAndVersions:
    def test_exact_duplicate_same_course_reuses_bytes(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        extractor = FakeExtractor([[_heading("Cap 1")]])
        service = _service(store, tmp_path, extractor=extractor)
        first = service.ingest(UID, course, PDF_BYTES)
        second = service.ingest(UID, course, PDF_BYTES)
        assert first.duplicate is False and first.new_version is True
        assert second.duplicate is True and second.new_version is False
        assert second.version_id == first.version_id
        assert second.doc_id == first.doc_id
        # Uma única versão e um único arquivo para bytes idênticos (§6.1).
        rows = store.fetch_user_rows(
            "SELECT COUNT(*) AS n FROM doc_versions WHERE user_id = ?", (UID,)
        )
        assert int(rows[0]["n"]) == 1
        originals = list((tmp_path / "data" / UID / "originals").iterdir())
        assert len(originals) == 1

    def test_same_bytes_other_course_reuses_bytes_and_keeps_links(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        other_course = make_uuid()
        store.execute_write(
            UID,
            [("INSERT INTO courses(id, user_id, title) VALUES (?,?,?)", (other_course, UID, "Outra"))],
        )
        extractor = FakeExtractor([[_heading("Cap 1")]])
        service = _service(store, tmp_path, extractor=extractor)
        first = service.ingest(UID, course, PDF_BYTES)
        second = service.ingest(UID, other_course, PDF_BYTES)
        assert second.duplicate is False and second.bytes_reused is True
        assert second.doc_id != first.doc_id
        # Mesmo arquivo físico (bytes reaproveitados), dois vínculos (§6.1).
        originals = list((tmp_path / "data" / UID / "originals").iterdir())
        assert len(originals) == 1
        links = store.fetch_user_rows(
            "SELECT d.id AS doc, d.course_id, dv.original_ref FROM documents d "
            "JOIN doc_versions dv ON dv.doc_id = d.id WHERE d.user_id = ?",
            (UID,),
        )
        refs = {str(row["original_ref"]) for row in links}
        courses = {str(row["course_id"]) for row in links}
        assert refs == {first.original_path}
        assert courses == {course, other_course}

    def test_version_active_only_after_full_indexing(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        extractor = FakeExtractor([[_heading("Cap 1")]])
        service = _service(store, tmp_path, extractor=extractor)
        result = service.ingest(UID, course, PDF_BYTES)
        # Extração completa → indexed; ativação é passo explícito (§6.1).
        assert result.version_status == "indexed"
        active = store.fetch_user_rows(
            "SELECT active_version FROM documents WHERE id = ?", (result.doc_id,)
        )
        assert active[0]["active_version"] is None
        service.activate_version(UID, result.doc_id, result.version_id)
        active = store.fetch_user_rows(
            "SELECT active_version FROM documents WHERE id = ?", (result.doc_id,)
        )
        assert str(active[0]["active_version"]) == result.version_id

    def test_new_version_pending_does_not_activate_and_keeps_old_active(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        extractor = FakeExtractor([[_heading("Cap 1")]])
        service = _service(store, tmp_path, extractor=extractor)
        v1 = service.ingest(UID, course, PDF_BYTES)
        service.activate_version(UID, v1.doc_id, v1.version_id)
        # Nova versão do mesmo documento por serviço sem extrator: fica
        # pending (indexação incompleta).
        service_pending = _service(store, tmp_path)
        v2 = service_pending.ingest(
            UID, course, PDF_BYTES + b"v2", doc_id=v1.doc_id
        )
        assert v2.doc_id == v1.doc_id and v2.version_id != v1.version_id
        assert v2.version_status == "pending"
        with pytest.raises(EduAgentError) as exc:
            service.activate_version(UID, v1.doc_id, v2.version_id)
        assert exc.value.code is ErrorCode.SCHEMA_INVALID
        active = store.fetch_user_rows(
            "SELECT active_version FROM documents WHERE id = ?", (v1.doc_id,)
        )
        # Versão incompleta nunca vira ativa; a anterior permanece (§12).
        assert str(active[0]["active_version"]) == v1.version_id

    def test_failed_version_never_activates(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        service = _service(store, tmp_path, extractor=None)
        result = service.ingest(UID, course, PDF_BYTES)
        assert result.version_status == "pending"
        with pytest.raises(EduAgentError):
            service.activate_version(UID, result.doc_id, result.version_id)


# ---------------------------------------------------------------------------
# C2 — blocos/proveniência, diagnóstico, OCR seletivo, job (§6.2, §12)
# ---------------------------------------------------------------------------


class TestC2ExtractionAndProvenance:
    def test_blocks_ordered_with_provenance(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        extractor = FakeExtractor(
            [
                [_heading("Unidade 1"), _paragraph("texto da pagina um")],
                [_paragraph("texto da pagina dois"), {"kind": "table", "text": "| a | b |"}],
            ]
        )
        service = _service(store, tmp_path, extractor=extractor)
        result = service.ingest(UID, course, PDF_BYTES)
        rows = store.fetch_user_rows(
            "SELECT page, order_index, kind, text FROM blocks WHERE user_id = ? "
            "AND version_id = ? ORDER BY page, order_index",
            (UID, result.version_id),
        )
        assert [str(r["text"]) for r in rows] == [
            "Unidade 1",
            "texto da pagina um",
            "texto da pagina dois",
            "| a | b |",
        ]
        assert [str(r["kind"]) for r in rows] == [
            "heading",
            "paragraph",
            "paragraph",
            "table",
        ]
        refs = service.source_refs_for_version(UID, result.version_id, result.doc_id)
        assert len(refs) == 4
        for ref, row in zip(refs, rows):
            assert ref.physical_page == int(row["page"])
            assert ref.text_hash == __import__("hashlib").sha256(
                str(row["text"]).encode()
            ).hexdigest()
            assert ref.version_id == _uuid.UUID(result.version_id)
            assert ref.doc_id == _uuid.UUID(result.doc_id)

    def test_page_diagnosis_empty_noisy_and_ok(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        extractor = FakeExtractor(
            [
                [_paragraph("pagina completa com bastante texto legivel para passar do limiar de ruido do ensaio")],
                [],  # vazia
                [_paragraph("pouco")],  # ruidosa
            ]
        )
        service = _service(store, tmp_path, extractor=extractor)
        result = service.ingest(UID, course, PDF_BYTES)
        diagnoses = {
            json.loads(str(r["diagnosis_json"]))["page"]
            for r in store.fetch_user_rows(
                "SELECT diagnosis_json FROM blocks WHERE user_id = ? AND version_id = ?",
                (UID, result.version_id),
            )
        }
        # Páginas vazias/ruidosas são diagnosticadas, não silenciadas (§6.2).
        # A página vazia não tem blocos: o diagnóstico dela aparece na versão
        # via reextração/pendências; aqui as páginas com blocos carregam
        # 'ok' e 'noisy'.
        assert "ok" in diagnoses and "noisy" in diagnoses
        assert extractor.calls and extractor.page_callbacks == [1, 2, 3]

    def test_selective_ocr_creates_separate_derived_and_reextracts_all(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        base_pages = [
            [_paragraph("pagina nativa com texto suficiente para o limiar")],
            [],  # vazia → motiva OCR seletivo
        ]
        ocr_pages = [
            [_paragraph("pagina nativa com texto suficiente para o limiar")],
            [{"kind": "paragraph", "text": "pagina recuperada por ocr seletivo com texto suficiente", "ocr_source": "embedded"}],
        ]
        extractor = FakeExtractor(base_pages, ocr_pages=ocr_pages)
        service = _service(store, tmp_path, extractor=extractor)
        result = service.ingest(UID, course, PDF_BYTES)
        derived = service.selective_ocr(
            UID,
            result.doc_id,
            result.version_id,
            "por+eng",
            data=PDF_BYTES,
            extractor=extractor,
        )
        # Derivado separado (§6.2), não substitui a base.
        assert derived.derived_version_id != result.version_id
        assert derived.base_version_id == result.version_id
        assert service.version_status(UID, result.version_id) == "indexed"
        assert service.version_status(UID, derived.derived_version_id) == "indexed"
        # Reextração do documento inteiro: as duas páginas passaram de novo.
        assert derived.total_pages_reextracted == 2
        assert extractor.calls[-1]["languages"] == ("por+eng",)
        # proveniência derivada registrada (§15.1 artifact_dependencies).
        deps = store.fetch_user_rows(
            "SELECT child_ref, parent_ref, relation FROM artifact_dependencies "
            "WHERE user_id = ? AND relation = 'derived_from'",
            (UID,),
        )
        assert len(deps) == 1 and str(deps[0]["relation"]) == "derived_from"
        # Manifesto do derivado registra OCR e reextração integral.
        rows = store.fetch_user_rows(
            "SELECT extractor_manifest FROM doc_versions WHERE id = ?",
            (derived.derived_version_id,),
        )
        manifest = json.loads(str(rows[0]["extractor_manifest"]))
        assert manifest["ocr_languages"] == "por+eng"
        assert manifest["full_reextraction"] is True

    def test_selective_ocr_language_whitelist(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        extractor = FakeExtractor([[_paragraph("texto")], []])
        service = _service(store, tmp_path, extractor=extractor)
        result = service.ingest(UID, course, PDF_BYTES)
        with pytest.raises(EduAgentError) as exc:
            service.selective_ocr(
                UID, result.doc_id, result.version_id, "eng+fra", data=PDF_BYTES
            )
        assert exc.value.code is ErrorCode.SCHEMA_INVALID

    def test_sidecar_only_document_never_indexed(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        # Todo o texto vem de sidecar OCR: nunca é texto total (§6.2).
        extractor = FakeExtractor(
            [
                [{"kind": "paragraph", "text": "apenas sidecar ocr", "ocr_source": "sidecar"}],
                [{"kind": "paragraph", "text": "mais sidecar", "ocr_source": "sidecar"}],
            ]
        )
        service = _service(store, tmp_path, extractor=extractor)
        with pytest.raises(EduAgentError) as exc:
            service.ingest(UID, course, PDF_BYTES)
        assert exc.value.code is ErrorCode.SCHEMA_INVALID
        assert service.version_status(UID, _last_version(store, UID)) == "failed"

    def test_mixed_sidecar_page_diagnosed_but_document_indexes(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        extractor = FakeExtractor(
            [
                [_paragraph("pagina nativa com texto suficiente para o limiar de ruido")],
                [{"kind": "paragraph", "text": "sidecar", "ocr_source": "sidecar"}],
            ]
        )
        service = _service(store, tmp_path, extractor=extractor)
        result = service.ingest(UID, course, PDF_BYTES)
        assert result.version_status == "indexed"
        diagnoses = {
            json.loads(str(r["diagnosis_json"]))["page"]
            for r in store.fetch_user_rows(
                "SELECT diagnosis_json FROM blocks WHERE user_id = ? AND version_id = ?",
                (UID, result.version_id),
            )
        }
        assert "sidecar_only" in diagnoses  # diagnóstico por página (§6.2)

    def test_job_progress_per_page_and_report(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        extractor = FakeExtractor(
            [[_paragraph("a" * 64)], [_paragraph("b" * 64)], [_paragraph("c" * 64)]]
        )
        service = _service(store, tmp_path, extractor=extractor)
        job = ExtractionJob(timeout_s=600)
        result = service.ingest(UID, course, PDF_BYTES, job=job)
        report = job.report()
        assert report["pages_done"] == 3
        assert report["total_pages"] == 3
        assert report["cancelled"] is False
        assert result.job_report == report
        # Progresso por página: callback chamado a cada página, em ordem.
        assert extractor.page_callbacks == [1, 2, 3]

    def test_job_cancellable_version_never_active(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        extractor = FakeExtractor(
            [[_paragraph("a" * 64)], [_paragraph("b" * 64)]]
        )
        service = _service(store, tmp_path, extractor=extractor)
        job = ExtractionJob(timeout_s=600)
        job.cancel()
        with pytest.raises(EduAgentError) as exc:
            service.ingest(UID, course, PDF_BYTES, job=job)
        assert exc.value.code is ErrorCode.CANCELLED
        version_id = _last_version(store, UID)
        assert service.version_status(UID, version_id) == "failed"
        doc_rows = store.fetch_user_rows(
            "SELECT id FROM documents WHERE user_id = ?", (UID,)
        )
        with pytest.raises(EduAgentError):
            service.activate_version(UID, str(doc_rows[0]["id"]), version_id)

    def test_job_timeout_typed_error(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        extractor = FakeExtractor([[_paragraph("a" * 64)]])
        service = _service(store, tmp_path, extractor=extractor)
        job = ExtractionJob(timeout_s=-1.0)  # deadline já vencido
        with pytest.raises(EduAgentError) as exc:
            service.ingest(UID, course, PDF_BYTES, job=job)
        assert exc.value.code is ErrorCode.TIMEOUT
        assert service.version_status(UID, _last_version(store, UID)) == "failed"

    def test_equations_and_tables_not_legible_stay_pending(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        extractor = FakeExtractor(
            [
                [
                    _paragraph("texto legivel com numero 30 por cento"),
                    {"kind": "equation", "text": "", "legible": False},
                    {"kind": "table", "text": "", "legible": False},
                ]
            ]
        )
        service = _service(store, tmp_path, extractor=extractor)
        result = service.ingest(UID, course, PDF_BYTES)
        rows = store.fetch_user_rows(
            "SELECT kind, diagnosis_json FROM blocks WHERE version_id = ? AND user_id = ?",
            (result.version_id, UID),
        )
        pending = [
            json.loads(str(r["diagnosis_json"]))
            for r in rows
            if json.loads(str(r["diagnosis_json"])).get("legible") is False
        ]
        assert len(pending) == 2  # pendências explícitas, nunca silêncio (§6.2)


# ---------------------------------------------------------------------------
# Subprocesso com limite de memória (§3)
# ---------------------------------------------------------------------------


def _read_rlimit():
    return resource.getrlimit(resource.RLIMIT_AS)


def _sleep_a_bit():
    time.sleep(5)
    return "done"


class TestC1SubprocessLimits:
    def test_rlimit_applied_to_subprocess(self) -> None:
        soft, _ = run_in_subprocess(_read_rlimit, mem_gib=4, timeout_s=60)
        assert soft == 4 * (1 << 30)  # 4 GiB (§3)

    def test_subprocess_timeout(self) -> None:
        with pytest.raises(EduAgentError) as exc:
            run_in_subprocess(_sleep_a_bit, mem_gib=4, timeout_s=1)
        assert exc.value.code is ErrorCode.TIMEOUT

    def test_subprocess_with_spawn_context_start_method_independent(self) -> None:
        # Correção da 006a (item 8): o alvo é picklável em nível de módulo —
        # o mecanismo funciona com spawn explícito, sem depender do start
        # method default da plataforma.
        soft, _ = run_in_subprocess(
            _read_rlimit, mem_gib=4, timeout_s=60, start_method="spawn"
        )
        assert soft == 4 * (1 << 30)

    def test_docling_subprocess_target_is_picklable(self) -> None:
        # O alvo real do adaptador é partial de função module-level: pickle
        # round-trip (qualquer start method), nunca lambda (item 8).
        target = functools.partial(
            ingestion_mod._docling_convert,
            PDF_BYTES,
            "application/pdf",
            10,
            ("por",),
        )
        clone = pickle.loads(pickle.dumps(target))
        assert clone.func is ingestion_mod._docling_convert
        assert clone.args == (PDF_BYTES, "application/pdf", 10, ("por",))


# ---------------------------------------------------------------------------
# 006a — correções do adaptador Docling e semântica de ciclos/PDD
# ---------------------------------------------------------------------------


def _docling_payload(
    pages: list[dict],
    *,
    limit_exceeded: bool = False,
    ocr_languages: list[str] | None = None,
) -> dict:
    return {
        "pages": pages,
        "limit_exceeded": limit_exceeded,
        "ocr_languages": ocr_languages,
    }


def _fake_docling_run(payload: dict, captured: dict):
    def run(fn, *, mem_gib, timeout_s, start_method=None):
        captured["fn"] = fn
        captured["start_method"] = start_method
        return payload

    return run


class Test006aDoclingAdapter:
    def test_page_limit_payload_marks_exceeded_never_silent(self) -> None:
        # Correção da 006a (item 1): entrada com página além do limite marca
        # limit_exceeded — nunca truncamento silencioso (§3/§12).
        entries = [
            {
                "page": page,
                "kind": "paragraph",
                "text": f"pagina {page}",
                "bbox": None,
                "legible": True,
                "ocr_source": None,
            }
            for page in range(1, 4)
        ]
        payload = _docling_pages_payload(entries, 2)
        assert payload["limit_exceeded"] is True
        assert [p["page"] for p in payload["pages"]] == [1, 2]
        ok = _docling_pages_payload(entries[:2], 2)
        assert ok["limit_exceeded"] is False
        assert [p["page"] for p in ok["pages"]] == [1, 2]

    def test_docling_pdf_over_page_limit_never_indexed(
        self, store: DomainStore, tmp_path: Path, course: str, monkeypatch
    ) -> None:
        # Simulacro fiel do fluxo real: o payload é o que _docling_convert
        # devolve quando o documento tem páginas além do limite. A ingestão
        # termina em RESOURCE_LIMIT com versão failed — nunca 'indexed'
        # como completa (§3/§12).
        monkeypatch.setattr(ingestion_mod, "docling_available", lambda: True)
        payload = _docling_payload(
            [
                {
                    "page": page,
                    "blocks": [
                        {
                            "kind": "paragraph",
                            "text": f"pagina {page}",
                            "bbox": None,
                            "legible": True,
                            "ocr_source": None,
                        }
                    ],
                }
                for page in range(1, 4)
            ],
            limit_exceeded=True,
        )
        captured: dict = {}
        monkeypatch.setattr(
            ingestion_mod, "run_in_subprocess", _fake_docling_run(payload, captured)
        )
        limits = IngestionLimits(max_pages=2)
        service = _service(
            store, tmp_path, limits=limits, extractor=DoclingExtractor()
        )
        with pytest.raises(EduAgentError) as exc:
            service.ingest(UID, course, PDF_BYTES)
        assert exc.value.code is ErrorCode.RESOURCE_LIMIT
        version_id = _last_version(store, UID)
        assert service.version_status(UID, version_id) == "failed"
        # Nenhum bloco foi persistido (nada é indexado parcialmente).
        rows = store.fetch_user_rows(
            "SELECT id FROM blocks WHERE user_id = ?", (UID,)
        )
        assert rows == []
        # O alvo despachado ao subprocesso é o partial picklável (item 8).
        assert isinstance(captured["fn"], functools.partial)
        assert captured["fn"].func is ingestion_mod._docling_convert

    def test_ocr_languages_plumbed_to_subprocess_and_blocks_marked(
        self, monkeypatch
    ) -> None:
        # Correção da 006a (item 2): languages atravessa a fronteira do
        # subprocesso (parâmetro do alvo picklável) e os blocos da passada
        # com OCR de página inteira carregam ocr_source='embedded' — nunca
        # None incondicional.
        monkeypatch.setattr(ingestion_mod, "docling_available", lambda: True)
        payload = _docling_payload(
            [
                {
                    "page": 1,
                    "blocks": [
                        {
                            "kind": "paragraph",
                            "text": "pagina recuperada por ocr",
                            "bbox": None,
                            "legible": True,
                            "ocr_source": "embedded",
                        }
                    ],
                }
            ],
            ocr_languages=["por"],
        )
        captured: dict = {}
        monkeypatch.setattr(
            ingestion_mod, "run_in_subprocess", _fake_docling_run(payload, captured)
        )
        extracted = DoclingExtractor().extract(
            PDF_BYTES, "application/pdf", max_pages=10, languages=("por",)
        )
        assert captured["fn"].args == (PDF_BYTES, "application/pdf", 10, ("por",))
        assert extracted.pages[0].blocks[0].ocr_source == "embedded"

    def test_ocr_pipeline_options_configure_languages_and_full_page(self) -> None:
        # O plumbing real: opções do pipeline de PDF com idiomas e OCR de
        # página inteira (§6.2). Construir opções não baixa modelos nem
        # executa o pipeline (smoke real segue pendente — task 017).
        pytest.importorskip("docling")
        from docling.datamodel.pipeline_options import OcrMode

        options = ingestion_mod._ocr_pipeline_options(("por", "eng"))
        assert options.do_ocr is True
        assert list(options.ocr_options.lang) == ["por", "eng"]
        assert options.ocr_options.mode is OcrMode.FULL_PAGE

    def test_ocr_requested_for_non_pdf_fails_typed(self) -> None:
        # Manifesto não descreve intenção não executada (§12): OCR só é
        # honrável em PDF; caso contrário, recusa tipada.
        with pytest.raises(EduAgentError) as exc:
            DoclingExtractor().extract(
                "texto simples".encode(), "text/plain", max_pages=10, languages=("por",)
            )
        assert exc.value.code is ErrorCode.SCHEMA_INVALID

    def test_docling_cancellation_is_cooperative_post_conversion(
        self, monkeypatch
    ) -> None:
        # Correção da 006a (item 3, opção b registrada): cancelamento é
        # cooperativo pós-conversão, com o timeout de §3 como teto; o flag é
        # observado ao fim da conversão — nada é reportado como progresso e
        # o erro é tipado CANCELLED.
        monkeypatch.setattr(ingestion_mod, "docling_available", lambda: True)
        payload = _docling_payload(
            [
                {
                    "page": 1,
                    "blocks": [
                        {
                            "kind": "paragraph",
                            "text": "x",
                            "bbox": None,
                            "legible": True,
                            "ocr_source": None,
                        }
                    ],
                }
            ]
        )
        monkeypatch.setattr(
            ingestion_mod,
            "run_in_subprocess",
            _fake_docling_run(payload, {}),
        )
        reported: list[int] = []
        with pytest.raises(EduAgentError) as exc:
            DoclingExtractor().extract(
                PDF_BYTES,
                "application/pdf",
                max_pages=10,
                on_page=reported.append,
                cancelled=lambda: True,
            )
        assert exc.value.code is ErrorCode.CANCELLED
        assert reported == []  # nenhuma página reportada como concluída


class Test006aDedupRetry:
    def test_dedup_ignores_non_reusable_versions_and_retries_same_document(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        # Correção da 006a (item 6): versão pending/failed com o mesmo SHA
        # não é devolvida como duplicata — a reingestão vira nova versão do
        # MESMO documento (caminho de retry acionável, §6.1/§12).
        pending_service = _service(store, tmp_path)
        first = pending_service.ingest(UID, course, PDF_BYTES)
        assert first.version_status == "pending"

        extractor = FakeExtractor([[_heading("Cap 1")]])
        service = _service(store, tmp_path, extractor=extractor)
        retry = service.ingest(UID, course, PDF_BYTES)
        assert retry.duplicate is False and retry.new_version is True
        assert retry.doc_id == first.doc_id
        assert retry.version_status == "indexed"

        # Versão failed com bytes distintos → mesmo caminho de retry.
        sidecar_only = FakeExtractor(
            [[{"kind": "paragraph", "text": "so sidecar", "ocr_source": "sidecar"}]]
        )
        failing_service = _service(store, tmp_path, extractor=sidecar_only)
        with pytest.raises(EduAgentError) as exc:
            failing_service.ingest(UID, course, PDF_BYTES + b"falha")
        assert exc.value.code is ErrorCode.SCHEMA_INVALID
        failed_rows = store.fetch_user_rows(
            "SELECT doc_id, status FROM doc_versions WHERE id = ? AND user_id = ?",
            (_last_version(store, UID), UID),
        )
        assert str(failed_rows[0]["status"]) == "failed"
        failed_doc_id = str(failed_rows[0]["doc_id"])
        retry_failed = service.ingest(UID, course, PDF_BYTES + b"falha")
        assert retry_failed.duplicate is False and retry_failed.new_version is True
        assert retry_failed.doc_id == failed_doc_id
        assert retry_failed.version_status == "indexed"

        # Versão reutilizável (indexed) continua sendo duplicata (§6.1).
        again = service.ingest(UID, course, PDF_BYTES)
        assert again.duplicate is True and again.new_version is False
        assert again.version_id == retry.version_id


class Test006aBlockIdCitation:
    def test_block_id_persisted_unique_and_closes_citation(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        # Correção da 006a (item 7): o ID determinístico p{n}b{n} é
        # persistido em blocks.block_id com UNIQUE (version_id, block_id) —
        # a citação fecha pela coluna, de forma inequívoca (§6.7).
        extractor = FakeExtractor(
            [
                [_heading("Unidade 1"), _paragraph("texto da pagina um")],
                [_paragraph("texto da pagina dois")],
            ]
        )
        service = _service(store, tmp_path, extractor=extractor)
        result = service.ingest(UID, course, PDF_BYTES)
        rows = store.fetch_user_rows(
            "SELECT block_id, page, order_index FROM blocks "
            "WHERE user_id = ? AND version_id = ? ORDER BY page, order_index",
            (UID, result.version_id),
        )
        expected = ["p1b1", "p1b2", "p2b1"]
        assert [str(r["block_id"]) for r in rows] == expected

        index_row = store._conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND "
            "name = 'uq_blocks_version_block'"
        ).fetchone()
        assert index_row is not None
        assert "UNIQUE" in str(index_row[0]).upper()

        # Violar a unicidade é recusado pelo banco.
        with pytest.raises(sqlite3.IntegrityError):
            store.execute_write(
                UID,
                [
                    (
                        "INSERT INTO blocks(id, user_id, version_id, page, "
                        "order_index, block_id, kind, text, bbox_json, "
                        "diagnosis_json) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (
                            make_uuid(),
                            UID,
                            result.version_id,
                            1,
                            0,
                            "p1b1",
                            "paragraph",
                            "duplicado",
                            None,
                            "{}",
                        ),
                    )
                ],
            )

        # A citação devolve exatamente os IDs persistidos.
        refs = service.source_refs_for_version(
            UID, result.version_id, result.doc_id
        )
        assert [ref.block_id for ref in refs] == expected

    def test_curator_source_ref_uses_persisted_block_id(
        self, store: DomainStore, curator: CuratorAgent
    ) -> None:
        version_id = make_uuid()
        doc_id = _insert_blocks(
            store, version_id, [{"kind": "paragraph", "text": "A prova vale 30%."}]
        )
        extraction = curator.curate_document(UID, doc_id, version_id)
        assert extraction.facts
        ref = extraction.facts[0].fact.source_refs[0]
        rows = store.fetch_user_rows(
            "SELECT block_id FROM blocks WHERE user_id = ? AND version_id = ?",
            (UID, version_id),
        )
        assert ref.block_id == str(rows[0]["block_id"])
        assert ref.block_id == "p1b1"


# ---------------------------------------------------------------------------
# C3 — tópicos, fatos candidatos, datas relativas, PDD, ciclos, confirmação
# ---------------------------------------------------------------------------


def _insert_blocks(
    store: DomainStore,
    version_id: str,
    blocks: list[dict],
    *,
    doc_id: str | None = None,
) -> str:
    """Insere versão indexada + blocos (com ``block_id`` determinístico
    persistido, correção da 006a). Se ``doc_id`` for dado, cria apenas a
    nova versão de um documento existente."""
    if doc_id is None:
        doc_id = make_uuid()
        course_id = make_uuid()
        store.execute_write(
            UID,
            [
                (
                    "INSERT INTO courses(id, user_id, title) VALUES (?,?,?)",
                    (course_id, UID, "Disciplina da curadoria"),
                ),
                (
                    "INSERT INTO documents(id, user_id, course_id) VALUES (?,?,?)",
                    (doc_id, UID, course_id),
                ),
            ],
        )
    store.execute_write(
        UID,
        [
            (
                "INSERT INTO doc_versions(id, user_id, doc_id, sha256, mime, "
                "original_ref, extractor_manifest, status) "
                "VALUES (?,?,?,?,?,?,?,'indexed')",
                (version_id, UID, doc_id, "ab" * 32, "application/pdf", "x/y.pdf", "{}"),
            ),
        ],
    )
    statements = []
    for i, block in enumerate(blocks):
        page = int(block.get("page", 1))
        statements.append(
            (
                "INSERT INTO blocks(id, user_id, version_id, page, order_index, "
                "block_id, kind, text, bbox_json, diagnosis_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    make_uuid(),
                    UID,
                    version_id,
                    page,
                    i,
                    _deterministic_block_id(page, i),
                    block["kind"],
                    block["text"],
                    None,
                    json.dumps(
                        {"page": "ok", "legible": block.get("legible", True)},
                        sort_keys=True,
                    ),
                ),
            )
        )
    store.execute_write(UID, statements)
    return doc_id


@pytest.fixture()
def curator(store: DomainStore) -> CuratorAgent:
    return CuratorAgent(store)


class TestC3FactsAndDates:
    def test_facts_follow_academic_contract_and_source_validation(
        self, store: DomainStore, curator: CuratorAgent
    ) -> None:
        version_id = make_uuid()
        _insert_blocks(
            store,
            version_id,
            [
                {
                    "kind": "paragraph",
                    "text": "A prova ocorre em 2026-11-10 e vale 30% da nota. "
                    "Entrega: 15/08/2026. Estudo sugerido: 12/05.",
                }
            ],
        )
        extraction = curator.curate_document(UID, make_uuid(), version_id)
        statuses = {}
        for candidate in extraction.facts:
            # Cada fato é um AcademicFact válido do contrato da 003.
            assert isinstance(candidate.fact, AcademicFact)
            statuses[(candidate.fact.original_expression)] = (
                candidate.fact.status,
                candidate.validation,
            )
        assert statuses["2026-11-10"] == (
            AcademicFact.FactStatus.CANDIDATE,
            "ok",
        )
        assert statuses["15/08/2026"] == (
            AcademicFact.FactStatus.CANDIDATE,
            "ok",
        )
        # DD/MM sem ano: não ganha ano inventado — ambiguous (§6.3).
        assert statuses["12/05"][0] is AcademicFact.FactStatus.AMBIGUOUS
        assert statuses["12/05"][1] == "year_missing"
        # Número com validação contra a origem.
        assert statuses["30%"] == (AcademicFact.FactStatus.CANDIDATE, "ok")
        # Fatos de data nunca carregam timezone nem horário (§4/§6.3).
        for candidate in extraction.facts:
            if candidate.fact.kind is AcademicFact.FactKind.DATE:
                assert candidate.fact.timezone is None
                assert "T" not in candidate.fact.normalized_value
        # Persistidos no DDL §5 com o status do contrato.
        rows = store.fetch_user_rows(
            "SELECT status FROM facts WHERE user_id = ?", (UID,)
        )
        assert {str(r["status"]) for r in rows} == {"candidate", "ambiguous"}

    def test_number_validation_against_source(self) -> None:
        assert validate_number("30%", "30") == "ok"
        assert validate_number("7,5 pontos", "7.5") == "ok"
        assert validate_number("30%", "31") == "value_mismatch"
        assert validate_against_source("30%", "vale 30% da nota") == "ok"
        assert validate_against_source("99%", "vale 30% da nota") == (
            "expression_not_in_source"
        )
        assert validate_date("2026-11-10", "2026-11-10") == "ok"
        assert validate_date("15/08/2026", "2026-08-15") == "ok"
        assert validate_date("15/08/2026", "2026-08-16") == "value_mismatch"

    def test_non_legible_blocks_never_become_facts(
        self, store: DomainStore, curator: CuratorAgent
    ) -> None:
        version_id = make_uuid()
        _insert_blocks(
            store,
            version_id,
            [
                {"kind": "table", "text": "", "legible": False},
                {"kind": "equation", "text": "", "legible": False},
            ],
        )
        extraction = curator.curate_document(UID, make_uuid(), version_id)
        assert extraction.facts == []
        assert len(extraction.pending_items) == 2  # pendências (§6.2)

    def test_topics_from_headings(self, store: DomainStore, curator: CuratorAgent) -> None:
        version_id = make_uuid()
        _insert_blocks(
            store,
            version_id,
            [
                {"kind": "heading", "text": "Grafos"},
                {"kind": "paragraph", "text": "conteudo"},
                {"kind": "heading", "text": "Arvores"},
            ],
        )
        extraction = curator.curate_document(UID, make_uuid(), version_id)
        assert [t.title for t in extraction.topics] == ["Grafos", "Arvores"]

    def test_relative_date_uses_spoken_date_and_confirmed_zone(
        self, store: DomainStore, curator: CuratorAgent
    ) -> None:
        # Zona não confirmada (users.timezone null, default §3) → erro tipado.
        with pytest.raises(EduAgentError) as exc:
            resolve_relative_date(
                "amanhã", datetime(2026, 3, 6, 2, 0, tzinfo=timezone.utc), None
            )
        assert exc.value.code is ErrorCode.AMBIGUOUS_INPUT
        with pytest.raises(EduAgentError) as exc:
            curator.resolve_fact_deadline(
                UID, expression="amanhã", spoken_at_utc=datetime.now(timezone.utc)
            )
        assert exc.value.code is ErrorCode.AMBIGUOUS_INPUT

        # Zona confirmada: data da fala convertida para a zona local (§6.3).
        store.execute_write(
            UID,
            [("UPDATE users SET timezone = 'America/Sao_Paulo' WHERE id = ?", (UID,))],
        )
        # 2026-03-06T02:00Z == 2026-03-05 23:00 em São Paulo → "amanhã" é 06/03.
        candidate = curator.resolve_fact_deadline(
            UID,
            expression="amanhã",
            spoken_at_utc=datetime(2026, 3, 6, 2, 0, tzinfo=timezone.utc),
        )
        assert candidate.fact.normalized_value == "2026-03-06"
        assert candidate.fact.kind is AcademicFact.FactKind.DATE
        assert candidate.fact.precision is AcademicFact.Precision.DAY
        assert candidate.fact.timezone is None  # prazo só de dia: sem hora/zona
        assert "T" not in candidate.fact.normalized_value
        # "daqui a 3 dias" a partir de 2026-03-05 (local) → 2026-03-08.
        candidate3 = curator.resolve_fact_deadline(
            UID,
            expression="daqui a 3 dias",
            spoken_at_utc=datetime(2026, 3, 6, 2, 0, tzinfo=timezone.utc),
        )
        assert candidate3.fact.normalized_value == "2026-03-08"
        # Expressão relativa fora da política → erro tipado, nunca chute.
        with pytest.raises(EduAgentError):
            curator.resolve_fact_deadline(
                UID,
                expression="na semana que vem",
                spoken_at_utc=datetime.now(timezone.utc),
            )

    def test_confirmed_pdd_priority_and_revision_conflict(
        self, store: DomainStore, curator: CuratorAgent
    ) -> None:
        version_id = make_uuid()
        doc_id = _insert_blocks(
            store,
            version_id,
            [{"kind": "paragraph", "text": "A prova vale 30% da nota."}],
        )
        extraction = curator.curate_document(UID, doc_id, version_id)
        fact_30 = next(
            c for c in extraction.facts if c.fact.original_expression == "30%"
        )
        assert fact_30.fact.status is AcademicFact.FactStatus.CANDIDATE

        # PDD confirmado com valor divergente para a mesma entidade (§6.3):
        # confirmação registra prioridade; revisão gera conflito. A identidade
        # da entidade é estável por documento + expressão (correção da 006a —
        # não namespaced pela versão).
        entity_id = str(_uuid.uuid5(_FACT_NAMESPACE, f"{doc_id}:30%"))
        fact_id = make_uuid()
        store.execute_write(
            UID,
            [
                (
                    "INSERT INTO facts(id, user_id, kind, value_json, authority, "
                    "recorded_at, source_refs_json, status, revision) "
                    "VALUES (?,?,?,?,?,?,?,?,1)",
                    (
                        fact_id,
                        UID,
                        "number",
                        json.dumps(
                            {
                                "entity_id": entity_id,
                                "original_expression": "30%",
                                "normalized_value": "40",
                                "precision": "exact",
                                "timezone": None,
                            }
                        ),
                        "user_confirmed",
                        "2026-01-01T00:00:00Z",
                        "[]",
                        "confirmed",
                    ),
                )
            ],
        )
        extraction2 = curator.curate_document(UID, doc_id, version_id)
        conflict_fact = next(
            c
            for c in extraction2.facts
            if c.fact.original_expression == "30%"
        )
        # Confirmado tem prioridade: o novo não sobrescreve — fica ambiguous
        # e o par é reportado pendente de reconciliação (§6.3/§7).
        assert conflict_fact.fact.status is AcademicFact.FactStatus.AMBIGUOUS
        assert conflict_fact.validation == "conflicts_with_confirmed_fact"
        assert len(extraction2.conflicts) == 1
        conflict = extraction2.conflicts[0]
        assert conflict.pending is True
        assert conflict.existing_value == "40"
        assert conflict.incoming_value == "30"

    def test_prerequisite_cycle_is_error_before_any_write(
        self, store: DomainStore, curator: CuratorAgent, course: str
    ) -> None:
        assert detect_prerequisite_cycles([("a", "b"), ("b", "c")]) == []
        cycle = detect_prerequisite_cycles([("a", "b"), ("b", "c"), ("c", "a")])
        assert cycle  # ciclo detectado (§9: erro, não inviabilidade misteriosa)
        with pytest.raises(EduAgentError) as exc:
            curator.register_topics(
                UID,
                course,
                ["Grafos", "Arvores", "Buscas"],
                [("Grafos", "Arvores"), ("Arvores", "Buscas"), ("Buscas", "Grafos")],
            )
        assert exc.value.code is ErrorCode.AMBIGUOUS_INPUT
        # Nada foi escrito (§9: erro antes de qualquer efeito).
        assert store.fetch_user_rows(
            "SELECT t.id FROM topics t JOIN courses c ON c.id = t.course_id WHERE c.user_id = ?",
            (UID,),
        ) == []
        assert store.fetch_user_rows("SELECT parent_id FROM topic_edges") == []
        # Sem ciclo: tópicos e arestas registrados (trigger de mesmo curso ativo).
        topic_ids = curator.register_topics(
            UID, course, ["Grafos", "Arvores"], [("Grafos", "Arvores")]
        )
        assert len(topic_ids) == 2
        edges = store.fetch_user_rows("SELECT parent_id, child_id FROM topic_edges")
        assert len(edges) == 1

    def test_user_confirmation_recorded_in_confirmations(
        self, store: DomainStore, curator: CuratorAgent
    ) -> None:
        version_id = make_uuid()
        doc_id = _insert_blocks(
            store,
            version_id,
            [
                {
                    "kind": "paragraph",
                    "text": "A prova ocorre em 2026-11-10 e vale 30% da nota; "
                    "o trabalho vale 20%.",
                }
            ],
        )
        extraction = curator.curate_document(UID, doc_id, version_id)
        assert len(extraction.persisted_fact_ids) == 3
        fact_id = extraction.persisted_fact_ids[0]
        revision_before = store.domain_revision(UID)

        # Confirmado sem confirmação do usuário é recusado (§4/§6.3).
        with pytest.raises(EduAgentError) as exc:
            curator.set_fact_status(UID, fact_id, "confirmed")
        assert exc.value.code is ErrorCode.SCHEMA_INVALID

        result = curator.set_fact_status(
            UID, fact_id, "confirmed", user_confirms=True
        )
        assert result["authority"] == "user_confirmed"
        confirmation = curator.confirmation_record(UID, result["confirmation_id"])
        assert confirmation is not None
        assert str(confirmation["artifact_id"]) == fact_id
        assert int(confirmation["artifact_revision"]) == 1
        assert len(str(confirmation["digest"])) == 64
        # Revisões de §15.1: approval = base + 1 = revisão pós-commit.
        assert int(confirmation["base_revision"]) == revision_before
        assert int(confirmation["approval_revision"]) == revision_before + 1
        assert store.domain_revision(UID) == revision_before + 1

        # Entrada direta inequívoca do usuário: corrige e confirma (§6.3).
        fact2 = extraction.persisted_fact_ids[1]
        result2 = curator.set_fact_status(
            UID, fact2, "confirmed", direct_value="35"
        )
        assert result2["authority"] == "user_direct"
        rows = store.fetch_user_rows(
            "SELECT value_json FROM facts WHERE id = ?", (fact2,)
        )
        assert json.loads(str(rows[0]["value_json"]))["normalized_value"] == "35"
        assert curator.confirmation_record(UID, result2["confirmation_id"]) is not None

        # Rejeição é transição válida do enum (§4).
        fact3 = extraction.persisted_fact_ids[-1]
        result3 = curator.set_fact_status(UID, fact3, "rejected")
        assert result3["status"] == "rejected"

    def test_document_extract_tool_denied_for_non_curator(
        self, store: DomainStore, curator: CuratorAgent
    ) -> None:
        # Tabela §10: document.extract só pode ser proposto pelo Curador;
        # JSON correto para ação proibida é negado por código (§10).
        with pytest.raises(EduAgentError) as exc:
            curator.request_document_extract(
                SenderRole.USER,
                user_id=UID,
                course_id=make_uuid(),
                data=PDF_BYTES,
            )
        assert exc.value.code is ErrorCode.TOOL_DENIED
        with pytest.raises(EduAgentError) as exc:
            curator.request_document_extract(
                SenderRole.TUTOR, user_id=UID, course_id=make_uuid(), data=PDF_BYTES
            )
        assert exc.value.code is ErrorCode.TOOL_DENIED


class Test006aCuratorSemantics:
    def test_prerequisite_cycle_across_calls_detected_before_any_write(
        self, store: DomainStore, curator: CuratorAgent, course: str
    ) -> None:
        # Correção da 006a (item 4): arestas persistidas de chamadas
        # anteriores entram no grafo de detecção — ciclo fechado ENTRE
        # chamadas é erro antes de qualquer escrita (§6.3/§9).
        curator.register_topics(
            UID, course, ["Grafos", "Arvores"], [("Grafos", "Arvores")]
        )
        edges_before = store.fetch_user_rows(
            "SELECT parent_id, child_id FROM topic_edges"
        )
        assert len(edges_before) == 1

        with pytest.raises(EduAgentError) as exc:
            curator.register_topics(
                UID, course, [], [("Arvores", "Grafos")]
            )
        assert exc.value.code is ErrorCode.AMBIGUOUS_INPUT
        # Nada novo foi escrito (§9: erro antes de qualquer efeito).
        edges_after = store.fetch_user_rows(
            "SELECT parent_id, child_id FROM topic_edges"
        )
        assert edges_after == edges_before

        # Aresta válida referindo tópico registrado em chamada anterior é
        # aceita (a resolução de títulos persistidos não é confundida com
        # ciclo).
        topic_ids = curator.register_topics(
            UID, course, ["Buscas"], [("Arvores", "Buscas")]
        )
        assert len(topic_ids) == 1
        assert len(store.fetch_user_rows("SELECT parent_id FROM topic_edges")) == 2

    def test_pdd_conflict_detected_across_versions_of_same_document(
        self, store: DomainStore, curator: CuratorAgent
    ) -> None:
        # Correção da 006a (item 5): identidade da entidade estável por
        # documento + expressão (não pela versão) — a revisão real do mesmo
        # fato numa versão nova do mesmo documento confronta o PDD
        # confirmado (§6.3).
        text = [{"kind": "paragraph", "text": "A prova vale 30% da nota."}]
        version1 = make_uuid()
        doc_id = _insert_blocks(store, version1, text)
        extraction1 = curator.curate_document(UID, doc_id, version1)
        index_30 = [
            i
            for i, c in enumerate(extraction1.facts)
            if c.fact.original_expression == "30%"
        ][0]
        fact_id = extraction1.persisted_fact_ids[index_30]
        curator.set_fact_status(UID, fact_id, "confirmed", direct_value="40")

        # Nova versão do MESMO documento, mesmo texto (revisão real).
        version2 = make_uuid()
        _insert_blocks(store, version2, text, doc_id=doc_id)
        extraction2 = curator.curate_document(UID, doc_id, version2)
        conflict_fact = next(
            c for c in extraction2.facts if c.fact.original_expression == "30%"
        )
        assert conflict_fact.fact.status is AcademicFact.FactStatus.AMBIGUOUS
        assert conflict_fact.validation == "conflicts_with_confirmed_fact"
        assert len(extraction2.conflicts) == 1
        assert extraction2.conflicts[0].existing_value == "40"
        assert extraction2.conflicts[0].incoming_value == "30"
        assert extraction2.conflicts[0].pending is True

    def test_pdd_reconciliation_across_documents_is_declared_limit(
        self, store: DomainStore, curator: CuratorAgent
    ) -> None:
        # Limite declarado (correção da 006a, item 5): a identidade é estável
        # por documento — o mesmo conteúdo em documento DISTINTO não confronta
        # o PDD confirmado aqui; a reconciliação entre documentos fica para a
        # memória (§7). Comportamento explícito, não silêncio.
        text = [{"kind": "paragraph", "text": "A prova vale 30% da nota."}]
        version_a = make_uuid()
        doc_a = _insert_blocks(store, version_a, text)
        extraction_a = curator.curate_document(UID, doc_a, version_a)
        index_30 = [
            i
            for i, c in enumerate(extraction_a.facts)
            if c.fact.original_expression == "30%"
        ][0]
        curator.set_fact_status(
            UID,
            extraction_a.persisted_fact_ids[index_30],
            "confirmed",
            direct_value="40",
        )

        version_b = make_uuid()
        doc_b = _insert_blocks(store, version_b, text)  # documento distinto
        assert doc_b != doc_a
        extraction_b = curator.curate_document(UID, doc_b, version_b)
        fact_b = next(
            c for c in extraction_b.facts if c.fact.original_expression == "30%"
        )
        assert fact_b.fact.status is AcademicFact.FactStatus.CANDIDATE
        assert extraction_b.conflicts == []
