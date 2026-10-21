"""Testes de aceite da task 007 — chunking, BM25, denso, RRF, citação e
abstinência (mapa §6.4–§6.8, §10, §3; §15.1 para ownership).

Não é a suíte quantitativa da etapa 8 (mapa de testes): são testes locais de
curta duração que verificam os critérios C1–C4 da task com embedder e
contador de tokens injetados (o BGE-M3 real é fronteira injetável; o smoke
do modelo real baixado com revisão/hash fixados é registrado à parte no
task.md). C4 (mapa intocado, commits separados, submodule intocado) é
verificado por inspeção de git e registrado no task.md.
"""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from eduagent.contracts import (
    EvidencePack,
    EduAgentError,
    ErrorCode,
    SenderRole,
)
from eduagent.services.ingestion import (
    BlockRecord,
    ExtractedDocument,
    IngestionService,
    PageRecord,
)
from eduagent.services.retrieval import (
    CHUNK_TARGET_TOKENS,
    BlockInput,
    BgeM3Embedder,
    HeuristicTokenCounter,
    RetrievalConfig,
    RetrievalService,
    chunk_blocks,
    retrieval_config_hash,
    rrf_merge,
    tokenize,
    tokenizer_fingerprint,
)
from eduagent.storage.repository import DomainStore

UID = "123e4567-e89b-12d3-a456-426614174000"
UID2 = "223e4567-e89b-12d3-a456-426614174000"
PDF_BYTES = b"%PDF-1.7\nconteudo de teste\n"


def make_uuid() -> str:
    import uuid as _uuid

    return str(_uuid.uuid4())


# ---------------------------------------------------------------------------
# Fixtures e fronteira injetável (extrator da 006, embedder e contador fake)
# ---------------------------------------------------------------------------


class ScriptedExtractor:
    """Extrator determinístico (mesmo protocolo de BlockExtractor da 006)."""

    name = "scripted"
    version = "1"

    def __init__(self, pages: list[list[dict]]) -> None:
        self.pages = pages  # páginas de blocos: [{"kind", "text"}]

    def extract(self, data, mime, *, max_pages, languages=None, on_page=None,
                cancelled=lambda: False) -> ExtractedDocument:
        extracted = ExtractedDocument()
        for page_number, blocks in enumerate(self.pages, start=1):
            records = [
                BlockRecord(
                    page=page_number,
                    kind=block.get("kind", "paragraph"),
                    text=block["text"],
                    order_in_page=index,
                    legible=block.get("legible", True),
                )
                for index, block in enumerate(blocks)
            ]
            extracted.pages.append(PageRecord(page=page_number, blocks=records))
        extracted.diagnose_pages()
        return extracted


class HashEmbedder:
    """Embedder denso fake determinístico (fronteira injetável): vetor derivado
    do SHA-256 do texto, L2-normalizado — igualdade de texto ⇒ similaridade 1."""

    name = "hash-fake"
    revision = "test-revision"
    dim = 8

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vector = np.array(
                [byte / 255.0 for byte in digest[: self.dim]], dtype=np.float32
            )
            norm = float(np.linalg.norm(vector))
            if norm == 0.0:
                norm = 1.0
            vectors.append(vector / norm)
        return np.vstack(vectors)

    def file_manifest(self) -> dict[str, str]:
        return {"fake": "0" * 64}


class FixedTokenCounter:
    """Contador fake que conta um número fixo de tokens por texto — isola os
    testes do orçamento do EvidencePack da heurística real."""

    name = "fixed-fake"
    version = "1"

    def __init__(self, tokens: int) -> None:
        self.tokens = tokens

    def count(self, text: str) -> int:
        return self.tokens

    def spans(self, text: str) -> list[tuple[int, int]]:
        return [(0, len(text))]


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
        UID,
        [("INSERT INTO courses(id, user_id, title) VALUES (?,?,?)", (course_id, UID, "MO810"))],
    )
    return course_id


def make_service(store: DomainStore, tmp_path: Path) -> tuple[IngestionService, RetrievalService]:
    data_root = tmp_path / "data"
    ingestion = IngestionService(store, data_root)
    retrieval = RetrievalService(store, data_root)
    return ingestion, retrieval


def ingest_document(
    store: DomainStore,
    tmp_path: Path,
    course_id: str,
    pages: list[list[dict]],
    *,
    user_id: str = UID,
    data: bytes = PDF_BYTES,
) -> tuple[str, str]:
    ingestion, _ = make_service(store, tmp_path)
    result = ingestion.ingest(
        user_id, course_id, data, extractor=ScriptedExtractor(pages)
    )
    return result.doc_id, result.version_id


def index_version(
    store: DomainStore,
    tmp_path: Path,
    doc_id: str,
    version_id: str,
    *,
    user_id: str = UID,
    activate: bool = True,
) -> dict:
    _, retrieval = make_service(store, tmp_path)
    manifest = retrieval.index_version(
        user_id, doc_id, version_id, embedder=HashEmbedder()
    )
    if activate:
        IngestionService(store, tmp_path / "data").activate_version(
            user_id, doc_id, version_id
        )
    return manifest


# ---------------------------------------------------------------------------
# C1 — chunking 384/64, IDs e páginas preservados, tabelas (§6.4)
# ---------------------------------------------------------------------------


class TestC1Chunking:
    def test_chunking_target_and_overlap(self) -> None:
        counter = HeuristicTokenCounter()
        long_text = " ".join(f"palavra{i}" for i in range(900))
        chunks = chunk_blocks(
            [BlockInput(1, 0, "p1b1", "paragraph", long_text)],
            version_id="v1",
            token_counter=counter,
        )
        assert len(chunks) == 3
        for chunk in chunks:
            assert counter.count(chunk.text) <= CHUNK_TARGET_TOKENS
        # overlap de continuidade: últimas 64 tokens da janela anterior
        # reaparecem no início da seguinte (passo = alvo − overlap)
        tokens_0 = chunk_text_tokens(chunks[0].text)
        tokens_1 = chunk_text_tokens(chunks[1].text)
        assert tokens_0[-64:] == tokens_1[:64]
        assert tokens_1[-64:] == chunk_text_tokens(chunks[2].text)[:64]
        # todas as janelas referem o mesmo bloco com spans sobrepostos pelo
        # overlap e sempre avançando
        assert all(c.block_refs[0].block_id == "p1b1" for c in chunks)
        assert chunks[0].block_refs[0].offsets[0] < chunks[1].block_refs[0].offsets[0]
        assert chunks[1].block_refs[0].offsets[0] < chunks[2].block_refs[0].offsets[0]

    def test_chunking_preserves_pages_and_block_ids(self) -> None:
        counter = HeuristicTokenCounter()
        blocks = [
            BlockInput(1, 0, "p1b1", "paragraph", "texto da página um " * 10),
            BlockInput(2, 0, "p2b1", "paragraph", "texto da página dois " * 10),
            BlockInput(3, 0, "p3b1", "paragraph", "texto da página três " * 10),
        ]
        chunks = chunk_blocks(blocks, version_id="v1", token_counter=counter)
        assert len(chunks) == 1
        pages = chunks[0].pages
        assert pages == (1, 2, 3)  # todas as páginas de origem preservadas
        assert [ref.block_id for ref in chunks[0].block_refs] == ["p1b1", "p2b1", "p3b1"]

    def test_chunk_ids_deterministic(self) -> None:
        counter = HeuristicTokenCounter()
        blocks = [BlockInput(1, 0, "p1b1", "paragraph", "conteúdo " * 50)]
        first = chunk_blocks(blocks, version_id="v1", token_counter=counter)
        second = chunk_blocks(blocks, version_id="v1", token_counter=counter)
        assert [c.id for c in first] == [c.id for c in second]
        other = chunk_blocks(blocks, version_id="v2", token_counter=counter)
        assert [c.id for c in first] != [c.id for c in other]

    def test_table_header_repeated_and_offsets_correct(self) -> None:
        counter = HeuristicTokenCounter()
        table = "coluna_a | coluna_b\n" + "\n".join(
            f"valor_a{i} | valor_b{i}" for i in range(300)
        )
        chunks = chunk_blocks(
            [BlockInput(2, 0, "p2b1", "table", table)],
            version_id="v1",
            token_counter=counter,
        )
        assert len(chunks) >= 2
        for chunk in chunks:
            # cabeçalho repetido em cada pedaço (§6.4)
            assert chunk.text.splitlines()[0] == "coluna_a | coluna_b"
            ref = chunk.block_refs[0]
            assert ref.block_id == "p2b1" and ref.page == 2
            start, end = ref.offsets  # type: ignore[misc]
            # o span do offset recorta linhas reais da tabela original
            span_text = table[start:end]
            assert "valor_a" in span_text

    def test_whole_blocks_never_split(self) -> None:
        counter = HeuristicTokenCounter()
        blocks = [
            BlockInput(1, i, f"p1b{i+1}", "paragraph", f"bloco {i} " * 5)
            for i in range(4)
        ]
        chunks = chunk_blocks(blocks, version_id="v1", token_counter=counter)
        assert len(chunks) == 1
        assert all(ref.offsets is None for ref in chunks[0].block_refs)


def chunk_text_tokens(text: str) -> list[str]:
    return tokenize(text)


# ---------------------------------------------------------------------------
# C2 — BM25/denso conforme o mapa, hashes, RRF com caso conhecido (§6.5-6)
# ---------------------------------------------------------------------------


class TestC2TokenizerAndRRF:
    def test_tokenizer_nfkc_lowercase_keeps_codes(self) -> None:
        tokens = tokenize("Função Ção RFC5545 bge-m3 CP-SAT 42 ﬁle")
        assert "função" in tokens  # lowercase Unicode
        assert "ção" in tokens
        assert "rfc5545" in tokens  # código preservado, nunca removido
        assert "42" in tokens  # números preservados
        assert "file" in tokens  # NFKC decompõe a ligadura ﬁ
        # sem remoção de stopwords: palavras comuns permanecem
        assert "de" in tokenize("termo de teste")
        assert "bge" in tokens and "m3" in tokens

    def test_tokenizer_fingerprint_is_stable_hash(self) -> None:
        import hashlib

        fingerprint = tokenizer_fingerprint()
        assert len(fingerprint) == 64
        assert fingerprint == tokenizer_fingerprint()

    def test_rrf_known_case_exact_fractions(self) -> None:
        # Caso conhecido: rankings lexicais e densos com sobreposição parcial.
        # lexical: [c3, c1]; denso: [c2, c3, c1]
        merged = dict(rrf_merge([["c3", "c1"], ["c2", "c3", "c1"]], k=60))
        # rank 1-based: c3 → 1/(60+1) + 1/(60+2)
        expected_c3 = float(Fraction(1, 61) + Fraction(1, 62))
        expected_c1 = float(Fraction(1, 62) + Fraction(1, 63))
        expected_c2 = float(Fraction(1, 61))
        assert merged["c3"] == pytest.approx(expected_c3)
        assert merged["c1"] == pytest.approx(expected_c1)
        assert merged["c2"] == pytest.approx(expected_c2)
        # ordem final decrescente
        order = [cid for cid, _ in rrf_merge([["c3", "c1"], ["c2", "c3", "c1"]], k=60)]
        assert order == ["c3", "c1", "c2"]  # c3 (0.03252) > c1 (0.03200) > c2

    def test_rrf_tie_broken_by_id(self) -> None:
        # Empate exato: mesmo chunk em ranks espelhados
        # a: 1/61 (lex) + 1/63 (den) = b: 1/62 + ... construído simetricamente:
        merged = dict(rrf_merge([["b", "a"], ["a", "b"]], k=60))
        assert merged["a"] == merged["b"]  # empate
        order = [cid for cid, _ in rrf_merge([["b", "a"], ["a", "b"]], k=60)]
        assert order == ["a", "b"]  # desempate pelo ID (lexicográfico)

    def test_rrf_rank_is_one_based(self) -> None:
        # Se rank fosse 0-based, o primeiro contribuiria 1/60 — não acontece.
        merged = dict(rrf_merge([["x"]], k=60))
        assert merged["x"] == pytest.approx(1.0 / 61.0)


class TestC2IndexAndRanking:
    def test_index_builds_chunks_vectors_and_manifest(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        doc_id, version_id = ingest_document(
            store,
            tmp_path,
            course,
            [[{"text": "A teoria de controle clássico usa realimentação " * 6}]],
        )
        manifest = index_version(store, tmp_path, doc_id, version_id)
        assert manifest["chunk_count"] >= 1
        assert manifest["tokenizer"]["version"] == "1"
        assert len(manifest["tokenizer"]["fingerprint"]) == 64
        assert manifest["embedder"]["name"] == "hash-fake"
        assert len(manifest["embedder"]["files"]) >= 1
        assert len(manifest["config_hash"]) == 64
        # arrays NumPy por snapshot + mapeamento chunk→vetor persistido (§6.5)
        index_dir = tmp_path / "data" / UID / "index" / version_id
        matrix = np.load(index_dir / "dense.npy", allow_pickle=False)
        mapping = json.loads((index_dir / "chunks.json").read_text())
        assert matrix.shape[0] == manifest["chunk_count"]
        assert matrix.dtype == np.float32
        assert mapping["chunk_ids"] == manifest["chunk_ids"]
        # vetores normalizados (§6.5)
        norms = np.linalg.norm(matrix, axis=1)
        assert np.allclose(norms, 1.0)
        # linhas de chunks no banco com proveniência
        rows = store.fetch_user_rows(
            "SELECT id, block_refs_json, text, embedding_manifest FROM chunks "
            "WHERE user_id = ? AND version_id = ? ORDER BY rowid",
            (UID, version_id),
        )
        assert [row["id"] for row in rows] == manifest["chunk_ids"]

    def test_bm25_params_and_config_hash_registered(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        doc_id, version_id = ingest_document(
            store,
            tmp_path,
            course,
            [[{"text": "equação de Navier-Stokes descreve fluidos " * 8}]],
        )
        manifest = index_version(store, tmp_path, doc_id, version_id)
        config = RetrievalConfig()
        expected_hash = retrieval_config_hash(
            config,
            embedder_name="hash-fake",
            embedder_revision="test-revision",
            counter_name="heuristic-unicode-word@1",
        )
        assert manifest["config_hash"] == expected_hash
        assert config.bm25_k1 == 1.5 and config.bm25_b == 0.75
        assert config.top_k == 40 and config.rrf_k == 60

    def test_search_lexical_and_dense_fusion(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        doc_id, version_id = ingest_document(
            store,
            tmp_path,
            course,
            [
                [{"text": "O teorema fundamental do cálculo liga derivação e "
                          "integração. " * 4}],
                [{"text": "A fotossíntese converte luz solar em energia "
                          "química. " * 4}],
            ],
        )
        index_version(store, tmp_path, doc_id, version_id)
        _, retrieval = make_service(store, tmp_path)
        ingestion = IngestionService(store, tmp_path / "data")
        ingestion.activate_version(UID, doc_id, version_id)
        pack = retrieval.document_search(
            UID,
            "fotossíntese converte luz solar",
            course_id=course,
            embedder=HashEmbedder(),
        )
        assert pack.coverage in (
            EvidencePack.Coverage.SUPPORTED,
            EvidencePack.Coverage.PARTIAL,
        )
        assert len(pack.chunks) >= 1
        # o chunk da fotossíntese lidera (lexical + denso concordam)
        top = pack.chunks[0]
        assert "fotossíntese" in top.text
        assert top.rank == 1
        # ranks únicos e 1-based (contrato §4)
        ranks = [chunk.rank for chunk in pack.chunks]
        assert ranks == sorted(ranks) and ranks[0] == 1
        assert len(set(ranks)) == len(ranks)

    def test_dense_exact_inner_product_ranks_identical_text_first(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        target_text = "vetor alvo distinto para produto interno exato " * 8
        doc_a, version_a = ingest_document(
            store,
            tmp_path,
            course,
            [[{"text": "texto distrator com outras palavras completamente " * 8}]],
        )
        doc_b, version_b = ingest_document(
            store,
            tmp_path,
            course,
            [[{"text": target_text}]],
            data=b"%PDF-1.7\ntarget doc\n",
        )
        # bytes distintos para não cair no dedup de duplicata exata (§6.1)
        index_version(store, tmp_path, doc_a, version_a)
        index_version(store, tmp_path, doc_b, version_b)
        _, retrieval = make_service(store, tmp_path)
        pack = retrieval.document_search(
            UID,
            target_text,  # consulta idêntica ao chunk alvo ⇒ IP exato = 1.0
            course_id=course,
            embedder=HashEmbedder(),
        )
        assert len(pack.chunks) >= 1
        assert pack.chunks[0].text.startswith("vetor alvo distinto")
        assert {str(c.source_ref.doc_id) for c in pack.chunks} <= {doc_a, doc_b}

    def test_reindex_is_idempotent(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        doc_id, version_id = ingest_document(
            store, tmp_path, course, [[{"text": "conteúdo para reindexação " * 10}]]
        )
        first = index_version(store, tmp_path, doc_id, version_id)
        second = index_version(store, tmp_path, doc_id, version_id)
        assert first["chunk_ids"] == second["chunk_ids"]
        rows = store.fetch_user_rows(
            "SELECT id FROM chunks WHERE user_id = ? AND version_id = ?",
            (UID, version_id),
        )
        assert len(rows) == first["chunk_count"]

    def test_embedder_failure_leaves_index_unpublished(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        doc_id, version_id = ingest_document(
            store, tmp_path, course, [[{"text": "conteúdo qualquer " * 10}]]
        )

        class BrokenEmbedder(HashEmbedder):
            def embed(self, texts):
                raise RuntimeError("falha simulada do embedder")

        _, retrieval = make_service(store, tmp_path)
        with pytest.raises(RuntimeError):
            retrieval.index_version(UID, doc_id, version_id, embedder=BrokenEmbedder())
        # índice NÃO foi publicado (§6.1/§12): sem manifesto
        assert not (tmp_path / "data" / UID / "index" / version_id / "index_manifest.json").exists()
        # e a versão não é buscável nem por filtro explícito de versão
        with pytest.raises(EduAgentError) as exc:
            retrieval.document_search(
                UID, "consulta", course_id=course, embedder=HashEmbedder(),
                version_id=version_id,
            )
        assert exc.value.code is ErrorCode.SOURCE_UNRESOLVED


# ---------------------------------------------------------------------------
# C3 — filtros antes do ranking, citação resolvível, orçamento (§6.6-7)
# ---------------------------------------------------------------------------


class TestC3FiltersBeforeRanking:
    def test_user_isolation_same_content(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        store.ensure_user(UID2)
        course_b = make_uuid()
        store.execute_write(
            UID2,
            [("INSERT INTO courses(id, user_id, title) VALUES (?,?,?)", (course_b, UID2, "MO810-B"))],
        )
        pages = [[{"text": "conteúdo idêntico entre dois usuários " * 8}]]
        doc_a, version_a = ingest_document(store, tmp_path, course, pages)
        doc_b, version_b = ingest_document(
            store, tmp_path, course_b, pages, user_id=UID2
        )
        index_version(store, tmp_path, doc_a, version_a)
        index_version(store, tmp_path, doc_b, version_b, user_id=UID2)
        _, retrieval = make_service(store, tmp_path)
        # Consulta com o TEXTO de A: usuário B não recebe nenhum chunk de A
        pack_b = retrieval.document_search(
            UID2,
            "conteúdo idêntico entre dois usuários",
            course_id=course_b,
            embedder=HashEmbedder(),
        )
        assert len(pack_b.chunks) >= 1
        assert {str(chunk.source_ref.version_id) for chunk in pack_b.chunks} == {version_b}
        assert all(str(c.source_ref.doc_id) == doc_b for c in pack_b.chunks)

    def test_course_isolation(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        other_course = make_uuid()
        store.execute_write(
            UID,
            [("INSERT INTO courses(id, user_id, title) VALUES (?,?,?)", (other_course, UID, "Outra"))],
        )
        doc_a, version_a = ingest_document(
            store, tmp_path, course, [[{"text": "documento da disciplina alvo " * 8}]]
        )
        doc_b, version_b = ingest_document(
            store, tmp_path, other_course, [[{"text": "documento da outra disciplina " * 8}]]
        )
        index_version(store, tmp_path, doc_a, version_a)
        index_version(store, tmp_path, doc_b, version_b)
        _, retrieval = make_service(store, tmp_path)
        pack = retrieval.document_search(
            UID, "documento da disciplina alvo", course_id=course, embedder=HashEmbedder()
        )
        assert {str(c.source_ref.doc_id) for c in pack.chunks} == {doc_a}

    def test_version_filter_before_ranking(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        doc_id, version_v1 = ingest_document(
            store, tmp_path, course, [[{"text": "primeira versão do documento " * 8}]]
        )
        # nova versão do mesmo documento (v2)
        result = IngestionService(store, tmp_path / "data").ingest(
            UID,
            course,
            PDF_BYTES,
            doc_id=doc_id,
            extractor=ScriptedExtractor([[{"text": "segunda versão do documento " * 8}]]),
        )
        version_v2 = result.version_id
        index_version(store, tmp_path, doc_id, version_v1)
        index_version(store, tmp_path, doc_id, version_v2)
        _, retrieval = make_service(store, tmp_path)
        pack_v1 = retrieval.document_search(
            UID, "primeira versão do documento", course_id=course,
            embedder=HashEmbedder(), version_id=version_v1,
        )
        assert {str(c.source_ref.version_id) for c in pack_v1.chunks} == {version_v1}

    def test_version_without_published_index_refused(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        doc_id, version_id = ingest_document(
            store, tmp_path, course, [[{"text": "versão sem índice " * 8}]]
        )
        _, retrieval = make_service(store, tmp_path)
        with pytest.raises(EduAgentError) as exc:
            retrieval.document_search(
                UID, "qualquer consulta", course_id=course,
                embedder=HashEmbedder(), version_id=version_id,
            )
        assert exc.value.code is ErrorCode.SOURCE_UNRESOLVED

    def test_course_ownership_required(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        _, retrieval = make_service(store, tmp_path)
        with pytest.raises(EduAgentError) as exc:
            retrieval.document_search(
                UID, "consulta", course_id=make_uuid(), embedder=HashEmbedder()
            )
        assert exc.value.code is ErrorCode.SOURCE_UNRESOLVED

    def test_tool_permission_enforced(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        doc_id, version_id = ingest_document(
            store, tmp_path, course, [[{"text": "conteúdo " * 10}]]
        )
        index_version(store, tmp_path, doc_id, version_id)
        _, retrieval = make_service(store, tmp_path)
        # Tutor pode propor document.search (§10)
        pack = retrieval.document_search(
            UID, "conteúdo", course_id=course, embedder=HashEmbedder(),
            sender_role=SenderRole.TUTOR,
        )
        assert pack is not None
        # Monitor não pode (§10)
        with pytest.raises(EduAgentError) as exc:
            retrieval.document_search(
                UID, "conteúdo", course_id=course, embedder=HashEmbedder(),
                sender_role=SenderRole.MONITOR,
            )
        assert exc.value.code is ErrorCode.TOOL_DENIED


class TestC3CitationAndBudget:
    def _indexed_pack(self, store, tmp_path, course):
        doc_id, version_id = ingest_document(
            store,
            tmp_path,
            course,
            [[{"text": "bloco original citável sobre termodinâmica " * 6}]],
        )
        index_version(store, tmp_path, doc_id, version_id)
        _, retrieval = make_service(store, tmp_path)
        pack = retrieval.document_search(
            UID, "termodinâmica citável", course_id=course, embedder=HashEmbedder()
        )
        return retrieval, pack, doc_id, version_id

    def test_citation_resolves_to_original(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        retrieval, pack, doc_id, version_id = self._indexed_pack(store, tmp_path, course)
        chunk = pack.chunks[0]
        citation = retrieval.format_citation(UID, chunk.source_ref)
        assert citation == f"[{doc_id}@1:{chunk.source_ref.physical_page}:{chunk.source_ref.block_id}]"
        resolved = retrieval.resolve_citation(UID, citation)
        # resolve ao original armazenado (§6.7)
        assert resolved.version_id == version_id
        assert resolved.block_id == chunk.source_ref.block_id
        # texto do bloco original está no banco e fecha com o hash
        block_rows = store.fetch_user_rows(
            "SELECT text FROM blocks WHERE user_id = ? AND version_id = ? AND block_id = ?",
            (UID, version_id, resolved.block_id),
        )
        assert resolved.text == str(block_rows[0]["text"])
        assert resolved.text_hash == hashlib.sha256(resolved.text.encode()).hexdigest()

    def test_citation_second_version_ordinal(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        doc_id, version_v1 = ingest_document(
            store, tmp_path, course, [[{"text": "primeira versão citável " * 8}]]
        )
        result = IngestionService(store, tmp_path / "data").ingest(
            UID, course, PDF_BYTES, doc_id=doc_id,
            extractor=ScriptedExtractor([[{"text": "segunda versão citável " * 8}]]),
        )
        version_v2 = result.version_id
        index_version(store, tmp_path, doc_id, version_v2)
        _, retrieval = make_service(store, tmp_path)
        pack = retrieval.document_search(
            UID, "segunda versão citável", course_id=course,
            embedder=HashEmbedder(), version_id=version_v2,
        )
        citation = retrieval.format_citation(UID, pack.chunks[0].source_ref)
        assert citation.endswith(f"@2:") or f"@2:" in citation
        resolved = retrieval.resolve_citation(UID, citation)
        assert resolved.version_id == version_v2
        assert resolved.version_ordinal == 2

    def test_citation_malformed_refused(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        _, retrieval = make_service(store, tmp_path)
        with pytest.raises(EduAgentError) as exc:
            retrieval.resolve_citation(UID, "citação inventada sem formato")
        assert exc.value.code is ErrorCode.SCHEMA_INVALID

    def test_validator_accepts_pack_and_detects_tampering(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        retrieval, pack, _, _ = self._indexed_pack(store, tmp_path, course)
        retrieval.validate_evidence_pack(UID, pack)  # não levanta
        # texto adulterado → INTERNAL_FAILURE (§6.7/§12)
        from eduagent.contracts import SourceRef

        bad = pack.model_copy(deep=True)
        bad.chunks[0].text += " trecho adulterado"
        with pytest.raises(EduAgentError) as exc:
            retrieval.validate_evidence_pack(UID, bad)
        assert exc.value.code is ErrorCode.INTERNAL_FAILURE
        # hash adulterado → INTERNAL_FAILURE
        bad_hash = pack.model_copy(deep=True)
        bad_hash.chunks[0].source_ref = bad_hash.chunks[0].source_ref.model_copy(
            update={"text_hash": "0" * 64}
        )
        with pytest.raises(EduAgentError) as exc:
            retrieval.validate_evidence_pack(UID, bad_hash)
        assert exc.value.code is ErrorCode.INTERNAL_FAILURE

    def test_evidence_pack_respects_token_budget(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        # 7 blocos grandes (~300 tokens cada: um por chunk); contador fixo de
        # 900 tokens por chunk e orçamento 4096 → no máximo 4 chunks cabem
        # (4×900=3600; 5×900=4500 > 4096)
        pages = [
            [{"text": f"bloco numerado {i} com conteúdo distinto suficiente " + ("texto de preenchimento do bloco " * 48)}]
            for i in range(7)
        ]
        doc_id, version_id = ingest_document(store, tmp_path, course, pages)
        index_version(store, tmp_path, doc_id, version_id)
        _, retrieval = make_service(store, tmp_path)
        pack = retrieval.document_search(
            UID, "bloco numerado", course_id=course, embedder=HashEmbedder(),
            token_counter=FixedTokenCounter(900),
        )
        assert len(pack.chunks) == 4
        assert all(
            FixedTokenCounter(900).count(chunk.text) == 900 for chunk in pack.chunks
        )

    def test_evidence_pack_default_chunks_limit(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        pages = [
            [{"text": f"parágrafo distinto numero {i} sobre topicos varios {i}" * 3}]
            for i in range(9)
        ]
        doc_id, version_id = ingest_document(store, tmp_path, course, pages)
        index_version(store, tmp_path, doc_id, version_id)
        _, retrieval = make_service(store, tmp_path)
        pack = retrieval.document_search(
            UID, "parágrafo distinto numero", course_id=course, embedder=HashEmbedder()
        )
        assert len(pack.chunks) <= RetrievalConfig().evidence_chunks


# ---------------------------------------------------------------------------
# C4 — sem reranker, abstinência sem citação fictícia
# ---------------------------------------------------------------------------


class TestC4RerankerAndAbstention:
    def test_reranker_disabled_by_default_and_refused_when_enabled(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        assert RetrievalConfig().reranker_enabled is False
        doc_id, version_id = ingest_document(
            store, tmp_path, course, [[{"text": "conteúdo para reranker " * 8}]]
        )
        index_version(store, tmp_path, doc_id, version_id)
        _, retrieval = make_service(store, tmp_path)
        enabled = RetrievalConfig(reranker_enabled=True)
        refused = RetrievalService(store, tmp_path / "data", config=enabled)
        with pytest.raises(EduAgentError) as exc:
            refused.document_search(
                UID, "conteúdo para reranker", course_id=course, embedder=HashEmbedder()
            )
        assert exc.value.code is ErrorCode.SCHEMA_INVALID
        assert "validação" in exc.value.message

    def test_abstention_empty_corpus_no_fictitious_citation(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        _, retrieval = make_service(store, tmp_path)
        pack = retrieval.document_search(
            UID, "consulta sem nenhum documento", course_id=course,
            embedder=HashEmbedder(),
        )
        assert pack.coverage is EvidencePack.Coverage.NONE
        assert pack.chunks == []  # nenhuma citação fictícia (§6.8)

    def test_abstention_version_filtered_empty(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        doc_id, version_id = ingest_document(
            store, tmp_path, course, [[{"text": "conteúdo sem relação " * 8}]]
        )
        index_version(store, tmp_path, doc_id, version_id)
        _, retrieval = make_service(store, tmp_path)
        # Consulta sem termo comum: com o limiar configurado (0.5 — acima de
        # qualquer RRF real, máx 2×1/61 ≈ 0.033), a busca abstém (§6.8)
        strict = RetrievalService(
            store, tmp_path / "data", config=RetrievalConfig(abstention_min_rrf=0.5)
        )
        pack = strict.document_search(
            UID, "zzztermoinexistente", course_id=course, embedder=HashEmbedder()
        )
        assert pack.coverage is EvidencePack.Coverage.NONE
        assert pack.chunks == []
        # Controle: sem limiar (default), a mesma consulta devolve candidatos
        # — o limiar é escolha de validação, não comportamento fixo
        lax = retrieval.document_search(
            UID, "zzztermoinexistente", course_id=course, embedder=HashEmbedder(),
        )
        assert lax.coverage is not EvidencePack.Coverage.NONE

    def test_require_evidence_raises_no_evidence(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        _, retrieval = make_service(store, tmp_path)
        with pytest.raises(EduAgentError) as exc:
            retrieval.document_search(
                UID, "consulta sem evidência", course_id=course,
                embedder=HashEmbedder(), require_evidence=True,
            )
        assert exc.value.code is ErrorCode.NO_EVIDENCE

    def test_abstention_threshold_default_none(
        self, store: DomainStore, tmp_path: Path, course: str
    ) -> None:
        # Default: abster apenas com conjunto vazio; limiar numérico é
        # escolha de validação (§6.8) — nunca sigmoid como probabilidade.
        assert RetrievalConfig().abstention_min_rrf is None


# ---------------------------------------------------------------------------
# BGE-M3 real — carregamento local (revisão/hash fixados no download)
# ---------------------------------------------------------------------------


class TestBgeM3Embedder:
    def test_missing_model_dir_refused(self, tmp_path: Path) -> None:
        with pytest.raises(EduAgentError) as exc:
            BgeM3Embedder(tmp_path / "inexistente")
        assert exc.value.code is ErrorCode.SOURCE_UNRESOLVED

    def test_real_model_local_if_available(self) -> None:
        """Smoke do BGE-M3 local baixado com revisão fixada — pulado sem o
        diretório de pesos (a suíte unitária usa HashEmbedder)."""
        model_dir = Path("runner-llm/models/bge-m3")
        if not (model_dir / "pytorch_model.bin").exists():
            pytest.skip("BGE-M3 local não presente neste checkout")
        embedder = BgeM3Embedder(model_dir)
        assert embedder.revision == "5617a9f61b028005a4858fdac845db406aefb181"
        vectors = embedder.embed(["A fotossíntese produz glicose.", "RDF triplas."])
        assert vectors.shape == (2, 1024)
        assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0)
        files = embedder.file_manifest()
        assert (
            files["pytorch_model.bin"]
            == "b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38"
        )
