"""Serviço de recuperação do Curador/Tutor (mapa normativo
``fase2/documentos/04_mapa_completo_do_sistema.md``, §6.4–§6.8, §10, §3;
task 007).

Contratos implementados:

- **§6.4 — chunking por seção/bloco**: blocos persistidos pela ingestão (006)
  são agrupados em chunks com **alvo de 384 tokens do embedding** e overlap de
  até 64 tokens **quando continuidade requerer** (blocos maiores que o alvo
  são janelados com passo ``alvo − overlap``, de modo que cada janela repete
  as últimas ≤64 tokens da anterior). Blocos que cabem no alvo nunca são
  partidos — IDs e **todas as páginas de origem** são preservados em
  ``block_refs_json``. Bloco de **tabela** que precisa ser dividido repete o
  cabeçalho (primeira linha) em cada pedaço, e cada pedaço referencia o span
  correto do bloco original via ``offsets`` (células/blocos corretos).
  IDs de chunk são determinísticos (``uuid5`` de versão + ordinal + hash do
  texto) — reindexação idempotente.
- **§6.5 — índice lexical BM25**: ``rank_bm25.BM25Okapi`` com ``k1=1.5`` e
  ``b=0.75`` (defaults de ensaio do §3), tokenização Unicode NFKC + lowercase
  **sem remover termos técnicos e códigos** (nenhum stopword list, códigos
  como ``RFC5545`` permanecem inteiros); versão e hash (fingerprint) do
  tokenizer são registrados no manifesto do índice e no hash de configuração.
  **Busca densa**: BGE-M3 local (``FlagEmbedding.BGEM3FlagModel``) com
  revisão/hash fixados no download e registrados no manifesto; vetor
  **normalizado** (L2) e **produto interno exato** (sem ANN — ANN/Qdrant é
  extensão fora do MVP). Vetores são **arrays NumPy por snapshot de versão**
  (``dense.npy``) com **mapeamento chunk→vetor persistido** (``chunks.json`` +
  ``index_manifest.json``, publicado por último — o índice só é publicado
  após construção completa, §6.1/§12).
- **§6.6 — filtros antes do ranking**: usuário, disciplina e versão são
  filtrados **na consulta SQL** (com ``user_id`` sempre presente — §15.1),
  antes de qualquer ranking; lexical e denso produzem rankings top-40
  (``retrieval_top_k``); fusão por **RRF** ``Σ 1/(60 + rank)`` com rank
  **1-based** e empate resolvido pelo ID do chunk (ordem lexicográfica
  crescente — determinismo). **Reranker** ``BAAI/bge-reranker-v2-m3`` é
  opcional (§6.6): a configuração inicial é **SEM reranker**
  (``config/default.yaml: reranker_enabled: false``) e a seleção fica como
  **pendência de validação** — habilitar o reranker aqui falha tipado em vez
  de simular uma etapa não implementada (§12).
- **§6.7 — pacote de evidência**: ``EvidencePack`` montado com até
  ``evidence_chunks`` (6) chunks dentro do **orçamento de 4.096 tokens**
  (``doc_tokens`` do §3; contagem via contador de tokens injetável — a
  contagem exata do Bonsai é calibração de validação). A citação
  ``[doc_id@versão:página:bloco]`` (formato ``format_citation``) **resolve ao
  original armazenado** pela coluna ``blocks.block_id`` persistida (006a) e
  pelo ordinal de versão do documento; ``validate_evidence_pack`` confere
  IDs, offsets, versão e hash do texto contra o banco. Apoio semântico é
  avaliado separadamente (§6.7) — existência de citação não garante suporte.
- **§6.8 — abstinência**: sem evidência documental (nenhum candidato após os
  filtros, ou RRF máximo abaixo do limiar de abstinência quando configurado),
  o pacote vem com ``coverage=none`` e **zero chunks — nenhuma citação
  fictícia**; ``require_evidence=True`` falha tipada ``NO_EVIDENCE``. O
  limiar de abstinência é default de ensaio (``None`` = abster apenas com
  conjunto vazio) a ajustar em validação — **não** há sigmoid tratado como
  probabilidade.

Nada aqui apresenta resultados medidos: todos os parâmetros numéricos são
defaults de ensaio a calibrar no hardware registrado (mapa §1/§3), e a
cobertura ``supported/partial/none`` segue regra declarada do MVP, não
avaliação de suporte semântico.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import shutil
import unicodedata
import uuid as _uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from rank_bm25 import BM25Okapi

from eduagent.contracts import (
    EvidencePack,
    SenderRole,
    SourceRef,
    ToolName,
    EduAgentError,
    ErrorCode,
    validate_tool_request,
)
from eduagent.storage.repository import DomainStore

#: Referência de diagnóstico local do serviço (mapa §4).
DIAGNOSTIC = "eduagent/services/retrieval.py"

# ---------------------------------------------------------------------------
# Defaults de ensaio (mapa §3; config/default.yaml) — a calibrar no hardware
# registrado antes do congelamento; NÃO são resultados medidos (mapa §1/§3).
# ---------------------------------------------------------------------------

CHUNK_TARGET_TOKENS = 384  # alvo em tokens do embedding (mapa §6.4)
CHUNK_MAX_OVERLAP_TOKENS = 64  # overlap máximo quando continuidade requerer
#: Teto secundário de caracteres por chunk: impede que um chunk viole o limite
#: de ``EvidencePack.Chunk.text`` (4000 chars, contrato §4) em scripts densos.
#: Escolha conservadora de ensaio, não medida.
CHUNK_MAX_CHARS = 3000

BM25_K1 = 1.5  # mapa §6.5
BM25_B = 0.75  # mapa §6.5
RETRIEVAL_TOP_K = 40  # mapa §3/§6.6 (lexical e denso)
RRF_K = 60  # mapa §6.6: Σ 1/(60 + rank)
EVIDENCE_CHUNKS = 6  # mapa §3/§6.6 (top-40 → até 6 sem reranker)
DOC_TOKEN_BUDGET = 4096  # mapa §3/§6.7 (doc_tokens)

#: Schema do manifesto de índice publicado.
INDEX_SCHEMA = "eduagent-index/1"

#: Revisão do BGE-M3 fixada no download desta task (HEAD de BAAI/bge-m3
#: consultado na API do Hub em 2026-10-21); hashes dos arquivos conferidos e
#: registrados em /tmp/opencode/task007/bge-m3-sha256.txt.
BGE_M3_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
BGE_M3_REPO = "BAAI/bge-m3"

#: Namespace UUIDv5 dos chunks (mesmo padrão do Curador, 006).
_CHUNK_NAMESPACE = _uuid.UUID("7c4a2d10-9e3f-4b8a-8c1d-2e5f6a7b8c9d")

_CITATION_RE = re.compile(
    r"^\[?([0-9a-fA-F-]{36})@(\d+):(\d+):([A-Za-z0-9][A-Za-z0-9._-]*)\]?$"
)


# ---------------------------------------------------------------------------
# Tokenização lexical (§6.5) — Unicode NFKC + lowercase, sem remover termos
# técnicos e códigos
# ---------------------------------------------------------------------------

TOKENIZER_VERSION = "1"

#: Palavras Unicode (letras/dígitos/underscore) — sem lista de stopwords e sem
#: filtro de "termos técnicos": ``RFC5545``, ``CP-SAT``, ``bge-m3`` e números
#: permanecem (como tokens inteiros ou hifenizados pelo separador, nunca
#: descartados). A fronteira é decisão explícita do tokenizer registrado.
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Tokenização lexical do §6.5: NFKC → casefold → palavras Unicode.

    Sem remoção de stopwords e sem descarte de códigos/números (§6.5: "sem
    remover termos técnicos e códigos"). Usada pelo BM25 e, como aproximação
    de contagem, pelo contador heurístico de tokens.
    """
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return _TOKEN_RE.findall(normalized)


def tokenizer_fingerprint() -> str:
    """Hash SHA-256 do comportamento do tokenizer (§6.5: "versão/hash do
    tokenizer registrados"): fonte da função + padrão do regex + versão —
    pinnea a tokenização registrada no manifesto do índice."""
    payload = (
        TOKENIZER_VERSION
        + "\n"
        + inspect.getsource(tokenize)
        + "\n"
        + _TOKEN_RE.pattern
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Contadores de tokens (§6.4 "tokens do embedding"; §6.7 orçamento de 4096)
# ---------------------------------------------------------------------------


class TokenCounter(Protocol):
    """Contador de tokens injetável (fronteira).

    O chunking usa os tokens **do embedding** (§6.4) e o pacote usa o
    orçamento **do Bonsai** (§6.7); a contagem exata de cada um depende de
    tokenizer que não se presume disponível — o contador é fronteira
    injetável e sua identidade fica registrada no manifesto do índice.
    """

    name: str
    version: str

    def count(self, text: str) -> int: ...

    def spans(self, text: str) -> list[tuple[int, int]]:
        """Spans (start, end) de cada token no texto original — base do
        janelamento determinístico em fronteiras de token."""
        ...


class HeuristicTokenCounter:
    """Contador heurístico por palavras Unicode (``tokenize``) — aproximação
    de ensaio dos tokens do embedding/Bonsai, usada quando o tokenizer real
    não está disponível; a identidade fica registrada no manifesto e a
    calibração da contagem é pendência de validação (§3)."""

    name = "heuristic-unicode-word"
    version = "1"

    def count(self, text: str) -> int:
        # Contagem autossistente com os spans usados pelo janelamento (o
        # chunking precisa que contagem e fronteiras coincidam).
        return len(self.spans(text))

    def spans(self, text: str) -> list[tuple[int, int]]:
        # Spans sobre o texto original: a fronteira de palavra Unicode do
        # regex é preservada sob NFKC/casefold, e os offsets precisam referir
        # o texto original (fonte da citação), não a forma normalizada.
        return [match.span() for match in _TOKEN_RE.finditer(text)]


# ---------------------------------------------------------------------------
# Chunking (§6.4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BlockInput:
    """Bloco persistido da ingestão (006) na ordem global do documento."""

    page: int
    order_index: int
    block_id: str
    kind: str
    text: str


@dataclass(frozen=True)
class BlockRef:
    """Referência de um bloco dentro do chunk (§6.4: IDs e todas as páginas
    de origem preservados). ``offsets`` localiza o span do excerpt **no texto
    do bloco original** (``None`` = bloco inteiro) — células/blocos corretos."""

    block_id: str
    page: int
    offsets: tuple[int, int] | None = None


@dataclass(frozen=True)
class Chunk:
    """Chunk pronto para indexação (§6.4): texto, referências completas e
    ID determinístico (reindexação idempotente)."""

    id: str
    ordinal: int
    text: str
    block_refs: tuple[BlockRef, ...]
    pages: tuple[int, ...]


def _table_header(text: str) -> str:
    """Cabeçalho de tabela (§6.4: "tabela repete cabeçalhos"): primeira linha
    não vazia do texto do bloco."""
    for line in text.splitlines():
        if line.strip():
            return line
    return ""


def chunk_blocks(
    blocks: list[BlockInput],
    *,
    version_id: str,
    token_counter: TokenCounter,
    target_tokens: int = CHUNK_TARGET_TOKENS,
    max_overlap_tokens: int = CHUNK_MAX_OVERLAP_TOKENS,
    max_chars: int = CHUNK_MAX_CHARS,
) -> list[Chunk]:
    """Chunking por seção/bloco (§6.4) — determinístico.

    Regras:

    - Blocos que cabem no alvo (tokens ≤ alvo restante e chars ≤ teto)
      entram inteiros — IDs e páginas de origem preservados sem divisão.
    - Bloco maior que o alvo é **janelado** em fronteiras de token com passo
      ``alvo − overlap``: cada janela repete até ``max_overlap_tokens`` da
      anterior (overlap só quando a continuidade requer, §6.4). Cada janela
      de tabela repete o cabeçalho e referencia seu span do bloco via
      ``offsets``.
    - Chunks não misturam janelas de blocos partidos com outros blocos.
    """
    if target_tokens <= max_overlap_tokens:
        raise EduAgentError(
            ErrorCode.INTERNAL_FAILURE,
            "alvo de chunking deve exceder o overlap (mapa §6.4)",
            diagnostic=DIAGNOSTIC,
        )
    chunks: list[Chunk] = []
    ordinal = 0

    def _new_chunk_id(text: str) -> str:
        nonlocal ordinal
        ordinal += 1
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return str(
            _uuid.uuid5(_CHUNK_NAMESPACE, f"{version_id}:{ordinal}:{digest}")
        )

    def _flush(segments: list[tuple[BlockInput, str, tuple[int, int] | None]]) -> None:
        """Materializa o chunk corrente a partir de segmentos
        ``(bloco, texto_do_pedaco, offsets_no_bloco)``."""
        if not segments:
            return
        text = "\n".join(piece for _, piece, _ in segments)
        refs = tuple(
            BlockRef(block_id=block.block_id, page=block.page, offsets=offsets)
            for block, _, offsets in segments
        )
        pages = tuple(sorted({block.page for block, _, _ in segments}))
        chunks.append(
            Chunk(
                id=_new_chunk_id(text),
                ordinal=ordinal,
                text=text,
                block_refs=refs,
                pages=pages,
            )
        )

    current: list[tuple[BlockInput, str, tuple[int, int] | None]] = []
    current_tokens = 0
    current_chars = 0

    for block in blocks:
        if not block.text.strip():
            continue  # bloco vazio não gera chunk (diagnóstico fica na 006)
        tokens = token_counter.count(block.text)
        spans = token_counter.spans(block.text)
        if tokens <= target_tokens and len(block.text) <= max_chars:
            # Bloco inteiro: cabe no chunk corrente ou abre um novo.
            if (
                current
                and (
                    current_tokens + tokens > target_tokens
                    or current_chars + len(block.text) > max_chars
                )
            ):
                _flush(current)
                current, current_tokens, current_chars = [], 0, 0
            current.append((block, block.text, None))
            current_tokens += tokens
            current_chars += len(block.text)
            continue

        # Bloco maior que o alvo (ou acima do teto de chars): janelamento em
        # fronteiras de token com overlap de continuidade (§6.4).
        header = _table_header(block.text) if block.kind == "table" else ""
        step = target_tokens - max_overlap_tokens
        windows: list[tuple[int, int]] = []
        start_token = 0
        while start_token < len(spans):
            end_token = min(start_token + target_tokens, len(spans))
            windows.append(
                (spans[start_token][0], spans[end_token - 1][1])
            )
            if end_token >= len(spans):
                break
            start_token += step
        for window_index, (start, end) in enumerate(windows):
            piece = block.text[start:end]
            if header and window_index > 0:
                piece = f"{header}\n{piece}"  # cabeçalho repetido (§6.4)
            # Uma janela ~alvo esgota o chunk e não se mistura com outros
            # blocos: materializa imediatamente como chunk próprio.
            current = [(block, piece, (start, end))]
            _flush(current)
            current, current_tokens, current_chars = [], 0, 0
    _flush(current)
    return chunks


# ---------------------------------------------------------------------------
# Configuração da recuperação (defaults de ensaio do §3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrievalConfig:
    """Parâmetros de recuperação (§3/§6.5-6) — defaults de ensaio."""

    bm25_k1: float = BM25_K1
    bm25_b: float = BM25_B
    top_k: int = RETRIEVAL_TOP_K
    rrf_k: int = RRF_K
    evidence_chunks: int = EVIDENCE_CHUNKS
    doc_token_budget: int = DOC_TOKEN_BUDGET
    reranker_enabled: bool = False  # §6.6: configuração inicial SEM reranker
    abstention_min_rrf: float | None = None  # §6.8: limiar a calibrar
    chunk_target_tokens: int = CHUNK_TARGET_TOKENS
    chunk_max_overlap_tokens: int = CHUNK_MAX_OVERLAP_TOKENS

    def canonical(self) -> dict[str, Any]:
        return {
            "bm25_k1": self.bm25_k1,
            "bm25_b": self.bm25_b,
            "top_k": self.top_k,
            "rrf_k": self.rrf_k,
            "evidence_chunks": self.evidence_chunks,
            "doc_token_budget": self.doc_token_budget,
            "reranker_enabled": self.reranker_enabled,
            "abstention_min_rrf": self.abstention_min_rrf,
            "chunk_target_tokens": self.chunk_target_tokens,
            "chunk_max_overlap_tokens": self.chunk_max_overlap_tokens,
        }


def retrieval_config_hash(
    config: RetrievalConfig,
    *,
    embedder_name: str,
    embedder_revision: str,
    counter_name: str,
) -> str:
    """Hash SHA-256 da configuração de recuperação (§4: ``retrieval_config_
    hash``) — inclui identidade do tokenizer lexical, do contador de chunking
    e do embedder, para que o hash pinnee o pipeline inteiro."""
    payload = json.dumps(
        {
            **config.canonical(),
            "tokenizer_version": TOKENIZER_VERSION,
            "tokenizer_fingerprint": tokenizer_fingerprint(),
            "chunk_counter": counter_name,
            "embedder": {"name": embedder_name, "revision": embedder_revision},
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Embedder denso (§6.5) — BGE-M3 local, revisão/hash fixados
# ---------------------------------------------------------------------------


class DenseEmbedder(Protocol):
    """Fronteira do embedder denso (§6.5): vetores L2-normalizados."""

    name: str
    revision: str
    dim: int

    def embed(self, texts: list[str]) -> "np.ndarray": ...

    def file_manifest(self) -> dict[str, str]:
        """Hashes SHA-256 dos artefatos do modelo (revisão/hash fixados)."""
        ...


class BgeM3Embedder:
    """Embedder denso BGE-M3 local (mapa §6.5).

    ``model_dir`` deve conter a cópia local baixada da revisão pinada
    (``BGE_M3_REVISION``); os hashes SHA-256 dos arquivos são calculados no
    carregamento e registrados no manifesto do índice. Vetores densos vêm do
    ``BGEM3FlagModel`` e são **renormalizados explicitamente** (L2) — o
    produto interno exato do §6.5 pressupõe vetores unitários.
    """

    name = "bge-m3"
    revision = BGE_M3_REVISION
    dim = 1024

    #: Arquivos essenciais à inferência densa local (pinneados no download).
    _FILES = (
        "config.json",
        "pytorch_model.bin",
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "sentencepiece.bpe.model",
    )

    def __init__(self, model_dir: Path | str, *, revision: str = BGE_M3_REVISION) -> None:
        self.model_dir = Path(model_dir)
        self.revision = revision
        missing = [f for f in self._FILES if not (self.model_dir / f).exists()]
        if missing:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"BGE-M3 local incompleto em {self.model_dir}: ausentes "
                f"{missing} (mapa §6.5: revisão/hash fixados no download)",
                diagnostic=DIAGNOSTIC,
            )
        try:
            from FlagEmbedding import BGEM3FlagModel
        except Exception as exc:  # noqa: BLE001 — falha de import é tipada
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                f"FlagEmbedding indisponível para o embedder denso: "
                f"{type(exc).__name__}",
                diagnostic=DIAGNOSTIC,
            ) from exc
        self._model = BGEM3FlagModel(str(self.model_dir), use_fp16=False)

    def embed(self, texts: list[str]) -> "np.ndarray":
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        output = self._model.encode(texts, return_dense=True, return_sparse=False, return_colbert_vecs=False)
        vectors = np.asarray(output["dense_vecs"], dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return vectors / norms  # vetor normalizado (§6.5)

    def file_manifest(self) -> dict[str, str]:
        manifest: dict[str, str] = {}
        for file_name in self._FILES:
            digest = hashlib.sha256((self.model_dir / file_name).read_bytes())
            manifest[file_name] = digest.hexdigest()
        return manifest


# ---------------------------------------------------------------------------
# Fusão RRF (§6.6) — Σ 1/(k + rank), rank 1-based, empate pelo ID
# ---------------------------------------------------------------------------


def rrf_merge(
    rankings: list[list[str]], *, k: int = RRF_K
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion do §6.6: ``Σ 1/(k + rank)`` com rank
    **1-based**; empate de pontuação é resolvido pelo **ID** (ordem
    lexicográfica crescente) — fusão determinística.

    Devolve ``[(chunk_id, score)]`` em ordem decrescente de pontuação.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):  # rank 1-based
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


# ---------------------------------------------------------------------------
# Serviço de recuperação
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedCitation:
    """Citação ``[doc_id@versão:página:bloco]`` resolvida ao original (§6.7)."""

    doc_id: str
    version_id: str
    version_ordinal: int
    page: int
    block_id: str
    text: str
    text_hash: str
    source_ref: SourceRef


class RetrievalService:
    """Recuperação documental (mapa §6.4–§6.8; ferramenta ``document.search``
    do §10: alvo "snapshot e disciplina", garantias "ownership, citações,
    filtros").

    Usa ``DomainStore`` (004) para o estado de domínio e o mesmo
    ``data_root`` da ingestão (006) para os artefatos de índice
    (``data_root/<user_id>/index/<version_id>/``).
    """

    def __init__(
        self,
        store: DomainStore,
        data_root: Path | str,
        *,
        config: RetrievalConfig | None = None,
    ) -> None:
        self._store = store
        self._data_root = Path(data_root)
        self.config = config or RetrievalConfig()

    # -- helpers --------------------------------------------------------------

    def _index_dir(self, user_id: str, version_id: str) -> Path:
        return self._data_root / user_id / "index" / version_id

    def _load_manifest(self, user_id: str, version_id: str) -> dict[str, Any] | None:
        """Manifesto do índice publicado (§6.5/§12: publicado só após
        construção completa — o arquivo é gravado por último, atomically)."""
        path = self._index_dir(user_id, version_id) / "index_manifest.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _assert_searchable_version(
        self, user_id: str, version_id: str, *, doc_id: str | None = None
    ) -> None:
        """A versão existe para o usuário, pertence ao documento informado
        (quando houver) e tem índice publicado — caso contrário, recusa
        tipada (nunca busca silenciosa em índice incompleto, §6.1/§12)."""
        sql = (
            "SELECT dv.id, dv.doc_id FROM doc_versions dv "
            "WHERE dv.id = ? AND dv.user_id = ?"
        )
        params: list[Any] = [version_id, user_id]
        if doc_id is not None:
            sql += " AND dv.doc_id = ?"
            params.append(doc_id)
        rows = self._store.fetch_user_rows(sql, tuple(params))
        if not rows:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"versão {version_id} inexistente para o usuário/documento "
                "informado (mapa §6.6: filtros antes do ranking)",
                diagnostic=DIAGNOSTIC,
            )
        if self._load_manifest(user_id, version_id) is None:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"versão {version_id} sem índice publicado — a busca só "
                "consulta índice construído por completo (mapa §6.1/§12)",
                diagnostic=DIAGNOSTIC,
            )

    def version_ordinal(self, user_id: str, doc_id: str, version_id: str) -> int:
        """Ordinal da versão no documento (1-based, ordem de criação) — mesma
        convenção dos ``artifact_dependencies`` da 006; base da citação
        ``[doc_id@versão:...]``."""
        rows = self._store.fetch_user_rows(
            "SELECT id FROM doc_versions WHERE user_id = ? AND doc_id = ? "
            "ORDER BY rowid",
            (user_id, doc_id),
        )
        ids = [str(row["id"]) for row in rows]
        if version_id not in ids:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"versão {version_id} não pertence ao documento {doc_id} do "
                "usuário (mapa §6.7)",
                diagnostic=DIAGNOSTIC,
            )
        return ids.index(version_id) + 1

    # -- §6.4-5: indexação -----------------------------------------------------

    def index_version(
        self,
        user_id: str,
        doc_id: str,
        version_id: str,
        *,
        embedder: DenseEmbedder,
        token_counter: TokenCounter | None = None,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        """Constrói e publica o índice da versão (§6.4-5): chunking →
        embeddings densos normalizados → arrays NumPy + mapeamento chunk→vetor
        → linhas de ``chunks`` → manifesto publicado **por último**.

        Idempotente: índice completo com a mesma identidade (embedder,
        tokenizer, configuração) é devolvido sem reconstrução; identidade
        diferente reconstrói (linhas e arquivos antigos substituídos).
        Qualquer falha **antes** da publicação deixa a versão sem índice
        publicado (nada parcial aprovado, §12).
        """
        self._assert_owned_version(user_id, doc_id, version_id)
        counter = token_counter or HeuristicTokenCounter()
        config_hash = retrieval_config_hash(
            self.config,
            embedder_name=embedder.name,
            embedder_revision=embedder.revision,
            counter_name=f"{counter.name}@{counter.version}",
        )
        existing = self._load_manifest(user_id, version_id)
        if (
            existing is not None
            and existing.get("config_hash") == config_hash
            and existing.get("embedder", {}).get("revision") == embedder.revision
        ):
            return existing  # reindexação idempotente
        if existing is not None:
            # Identidade diferente: **despublica** antes de reconstruir — uma
            # falha no meio da reconstrução deixa a versão SEM índice
            # publicado (nunca manifesto antigo apontando para artefatos
            # novos, §12).
            manifest_path = self._index_dir(user_id, version_id) / "index_manifest.json"
            manifest_path.unlink(missing_ok=True)

        rows = self._store.fetch_user_rows(
            "SELECT page, order_index, block_id, kind, text FROM blocks "
            "WHERE user_id = ? AND version_id = ? ORDER BY page, order_index",
            (user_id, version_id),
        )
        blocks = [
            BlockInput(
                page=int(row["page"]),
                order_index=int(row["order_index"]),
                block_id=str(row["block_id"]),
                kind=str(row["kind"]),
                text=str(row["text"]),
            )
            for row in rows
        ]
        if not blocks:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"versão {version_id} sem blocos persistidos — indexação "
                "exige extração completa (mapa §6.1/§6.4)",
                diagnostic=DIAGNOSTIC,
            )
        chunks = chunk_blocks(
            blocks,
            version_id=version_id,
            token_counter=counter,
            target_tokens=self.config.chunk_target_tokens,
            max_overlap_tokens=self.config.chunk_max_overlap_tokens,
        )
        if not chunks:
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                "chunking não produziu chunks para versão com blocos "
                "(mapa §6.4)",
                diagnostic=DIAGNOSTIC,
            )
        vectors = embedder.embed([chunk.text for chunk in chunks])
        if vectors.shape[0] != len(chunks):
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                "embedder devolveu número de vetores diferente do número de "
                "chunks (mapa §6.5)",
                diagnostic=DIAGNOSTIC,
            )
        vectors = np.ascontiguousarray(vectors, dtype=np.float32)

        index_dir = self._index_dir(user_id, version_id)
        tmp_dir = index_dir.parent / f".tmp-{version_id}-{_uuid.uuid4().hex[:8]}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            dense_path = tmp_dir / "dense.npy"
            with open(dense_path, "wb") as handle:
                np.save(handle, vectors, allow_pickle=False)
            mapping = {"chunk_ids": [chunk.id for chunk in chunks]}
            chunks_path = tmp_dir / "chunks.json"
            chunks_path.write_text(
                json.dumps(mapping, sort_keys=True), encoding="utf-8"
            )
            dense_sha = hashlib.sha256(dense_path.read_bytes()).hexdigest()
            chunks_sha = hashlib.sha256(chunks_path.read_bytes()).hexdigest()
            # Linhas de chunks na transação única (FK composta por usuário,
            # §15.1); embedding_manifest referencia o embedder real.
            embedding_manifest = json.dumps(
                {
                    "embedder": embedder.name,
                    "embedder_revision": embedder.revision,
                    "dim": int(vectors.shape[1]),
                    "config_hash": config_hash,
                },
                sort_keys=True,
            )
            statements = [
                (
                    "DELETE FROM chunks WHERE user_id = ? AND version_id = ?",
                    (user_id, version_id),
                )
            ]
            statements.extend(
                (
                    "INSERT INTO chunks(id, user_id, version_id, "
                    "block_refs_json, text, embedding_manifest) "
                    "VALUES (?,?,?,?,?,?)",
                    (
                        chunk.id,
                        user_id,
                        version_id,
                        json.dumps(
                            [
                                {
                                    "block_id": ref.block_id,
                                    "page": ref.page,
                                    "offsets": (
                                        list(ref.offsets)
                                        if ref.offsets is not None
                                        else None
                                    ),
                                }
                                for ref in chunk.block_refs
                            ],
                            sort_keys=True,
                        ),
                        chunk.text,
                        embedding_manifest,
                    ),
                )
                for chunk in chunks
            )
            self._store.execute_write(
                user_id, statements, expected_version=expected_version
            )
            # Publicação por último (§6.1/§12): índice completo só vira
            # visível quando o manifesto é renomeado para o lugar final.
            manifest = {
                "schema": INDEX_SCHEMA,
                "doc_id": doc_id,
                "version_id": version_id,
                "chunk_count": len(chunks),
                "dim": int(vectors.shape[1]),
                "chunk_ids": mapping["chunk_ids"],
                "dense_file": "dense.npy",
                "dense_sha256": dense_sha,
                "chunks_file": "chunks.json",
                "chunks_sha256": chunks_sha,
                "embedder": {
                    "name": embedder.name,
                    "revision": embedder.revision,
                    "files": embedder.file_manifest(),
                },
                "tokenizer": {
                    "version": TOKENIZER_VERSION,
                    "fingerprint": tokenizer_fingerprint(),
                },
                "chunking": {
                    "token_counter": f"{counter.name}@{counter.version}",
                    "target_tokens": self.config.chunk_target_tokens,
                    "max_overlap_tokens": self.config.chunk_max_overlap_tokens,
                },
                "config_hash": config_hash,
            }
            manifest_path = tmp_dir / "index_manifest.json"
            manifest_path.write_text(
                json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8"
            )
            index_dir.mkdir(parents=True, exist_ok=True)
            for file_name in ("dense.npy", "chunks.json", "index_manifest.json"):
                os.replace(tmp_dir / file_name, index_dir / file_name)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return manifest

    def _assert_owned_version(
        self, user_id: str, doc_id: str, version_id: str
    ) -> None:
        rows = self._store.fetch_user_rows(
            "SELECT id FROM doc_versions WHERE id = ? AND user_id = ? AND "
            "doc_id = ?",
            (version_id, user_id, doc_id),
        )
        if not rows:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                "versão inexistente ou fora do ownership do usuário/documento "
                "(mapa §6.1/§15.1)",
                diagnostic=DIAGNOSTIC,
            )

    # -- §6.6-8: busca (document.search) ----------------------------------------

    def document_search(
        self,
        user_id: str,
        query: str,
        *,
        course_id: str,
        embedder: DenseEmbedder,
        token_counter: TokenCounter | None = None,
        doc_id: str | None = None,
        version_id: str | None = None,
        topic_ids: list[str] | None = None,
        sender_role: SenderRole = SenderRole.CURATOR,
        require_evidence: bool = False,
    ) -> EvidencePack:
        """Ferramenta ``document.search`` (§10): filtros de usuário,
        disciplina e versão **antes do ranking**; BM25 + denso top-40; RRF;
        pacote ≤ 4.096 tokens com citações resolvíveis; abstinência sem
        citação fictícia (§6.6-8).

        ``sender_role`` é validado contra a tabela de permissões do §10
        (Curador/Tutor podem propor ``document.search``). Com
        ``require_evidence=True``, ausência de evidência falha tipada
        ``NO_EVIDENCE``; sem a flag, devolve pacote com ``coverage=none``.
        """
        validate_tool_request(ToolName.DOCUMENT_SEARCH, sender_role)
        pack = self._search(
            user_id,
            query,
            course_id=course_id,
            embedder=embedder,
            token_counter=token_counter,
            doc_id=doc_id,
            version_id=version_id,
            topic_ids=topic_ids,
        )
        if require_evidence and pack.coverage is EvidencePack.Coverage.NONE:
            raise EduAgentError(
                ErrorCode.NO_EVIDENCE,
                "sem evidência documental para a consulta — abstinência "
                "declarada, nenhuma citação emitida (mapa §6.8)",
                diagnostic=DIAGNOSTIC,
            )
        return pack

    def _search(
        self,
        user_id: str,
        query: str,
        *,
        course_id: str,
        embedder: DenseEmbedder,
        token_counter: TokenCounter | None,
        doc_id: str | None,
        version_id: str | None,
        topic_ids: list[str] | None,
    ) -> EvidencePack:
        if not query.strip():
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "consulta vazia (mapa §4: tamanhos limitados)",
                diagnostic=DIAGNOSTIC,
            )
        if len(query) > 512:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"consulta com {len(query)} caracteres excede o limite do "
                "contrato EvidencePack (512; mapa §4)",
                diagnostic=DIAGNOSTIC,
            )
        counter = token_counter or HeuristicTokenCounter()
        config_hash = retrieval_config_hash(
            self.config,
            embedder_name=embedder.name,
            embedder_revision=embedder.revision,
            counter_name=f"{counter.name}@{counter.version}",
        )
        if self.config.reranker_enabled:
            # §6.6/§12: reranker é decisão de validação — não há etapa de
            # rerank implementada; habilitar sem implementação falha tipado
            # em vez de devolver ranking fingido.
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "reranker habilitado na configuração mas não implementado no "
                "MVP — seleção do reranker é pendência de validação "
                "(mapa §6.6); configuração inicial deve vir sem reranker",
                diagnostic=DIAGNOSTIC,
            )
        if version_id is not None:
            self._assert_searchable_version(
                user_id, version_id, doc_id=doc_id
            )

        candidates = self._candidate_chunks(
            user_id,
            course_id=course_id,
            doc_id=doc_id,
            version_id=version_id,
        )
        topic_uuids = [
            _uuid.UUID(topic) for topic in (topic_ids or [])
        ]
        if not candidates:
            return self._empty_pack(
                query, topic_uuids, config_hash
            )  # abstinência: conjunto vazio (§6.8)

        # --- ranking lexical (BM25, §6.5) -------------------------------------
        lexical_ranking = self._lexical_ranking(query, candidates)

        # --- ranking denso (produto interno exato, §6.5) ----------------------
        dense_ranking = self._dense_ranking(
            query, candidates, user_id, embedder
        )

        merged = rrf_merge(
            [lexical_ranking, dense_ranking], k=self.config.rrf_k
        )
        if not merged:
            return self._empty_pack(query, topic_uuids, config_hash)

        # Abstinência por limiar (§6.8): default None = só conjunto vazio;
        # limiar numérico é escolha de ensaio a calibrar em validação.
        if (
            self.config.abstention_min_rrf is not None
            and merged[0][1] < self.config.abstention_min_rrf
        ):
            return self._empty_pack(query, topic_uuids, config_hash)

        return self._build_pack(
            user_id,
            query=query,
            topic_uuids=topic_uuids,
            merged=merged,
            candidates={chunk_id: row for chunk_id, row in candidates},
            config_hash=config_hash,
            token_counter=counter,
        )

    def _candidate_chunks(
        self,
        user_id: str,
        *,
        course_id: str,
        doc_id: str | None,
        version_id: str | None,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Candidatos **após** os filtros de usuário/disciplina/versão (§6.6:
        filtrar antes do ranking). Só versões com índice publicado entram
        (§6.1/§12); por default apenas versões ativas são consultadas."""
        course_rows = self._store.fetch_user_rows(
            "SELECT id FROM courses WHERE id = ? AND user_id = ?",
            (course_id, user_id),
        )
        if not course_rows:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"disciplina {course_id} inexistente ou fora do ownership do "
                f"usuário (mapa §6.6/§15.1)",
                diagnostic=DIAGNOSTIC,
            )
        sql = (
            "SELECT c.id AS chunk_id, c.version_id, c.text, "
            "c.block_refs_json, dv.doc_id, dv.status "
            "FROM chunks c "
            "JOIN doc_versions dv ON dv.id = c.version_id "
            "AND dv.user_id = c.user_id "
            "JOIN documents d ON d.id = dv.doc_id "
            "WHERE c.user_id = ? AND d.course_id = ?"
        )
        params: list[Any] = [user_id, course_id]
        if doc_id is not None:
            sql += " AND dv.doc_id = ?"
            params.append(doc_id)
        if version_id is not None:
            sql += " AND dv.id = ?"
            params.append(version_id)
        else:
            # Default: apenas a versão publicada do documento (§6.1: só uma
            # versão completa/indexada é ativada; ativação marca
            # documents.active_version).
            sql += " AND d.active_version = dv.id"
        rows = self._store.fetch_user_rows(sql, tuple(params))
        candidates: list[tuple[str, dict[str, Any]]] = []
        for row in rows:
            chunk_id = str(row["chunk_id"])
            if self._load_manifest(user_id, str(row["version_id"])) is None:
                continue  # índice não publicado: fora antes do ranking
            candidates.append(
                (
                    chunk_id,
                    {
                        "chunk_id": chunk_id,
                        "version_id": str(row["version_id"]),
                        "doc_id": str(row["doc_id"]),
                        "text": str(row["text"]),
                        "block_refs": json.loads(str(row["block_refs_json"])),
                    },
                )
            )
        return candidates

    def _lexical_ranking(
        self, query: str, candidates: list[tuple[str, dict[str, Any]]]
    ) -> list[str]:
        """Ranking BM25 top-k (§6.5): ``BM25Okapi`` com k1/b da configuração;
        empate de pontuação resolvido pelo ID (determinismo). Scores lexicais
        zero (nenhum termo em comum) não entram no ranking lexical — escolha
        declarada para não alimentar a RRF com hits sem termo algum."""
        corpus = [
            tokenize(row["text"]) for _, row in candidates
        ]
        if not any(corpus):
            return []
        bm25 = BM25Okapi(corpus, k1=self.config.bm25_k1, b=self.config.bm25_b)
        scores = bm25.get_scores(tokenize(query))
        ranked = sorted(
            (
                (chunk_id, float(score))
                for (chunk_id, _), score in zip(candidates, scores)
                if score > 0.0
            ),
            key=lambda item: (-item[1], item[0]),
        )
        return [chunk_id for chunk_id, _ in ranked[: self.config.top_k]]

    def _dense_ranking(
        self,
        query: str,
        candidates: list[tuple[str, dict[str, Any]]],
        user_id: str,
        embedder: DenseEmbedder,
    ) -> list[str]:
        """Ranking denso top-k (§6.5): produto interno exato entre o vetor
        normalizado da consulta e os vetores por snapshot (``dense.npy``);
        empate resolvido pelo ID."""
        query_vector = embedder.embed([query])[0]
        scored: list[tuple[str, float]] = []
        by_version: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for chunk_id, row in candidates:
            by_version.setdefault(row["version_id"], []).append((chunk_id, row))
        for version_id, group in by_version.items():
            manifest = self._load_manifest(user_id, version_id)
            if manifest is None:
                continue
            index_dir = self._index_dir(user_id, version_id)
            dense_path = index_dir / str(manifest.get("dense_file", "dense.npy"))
            mapping_path = index_dir / str(manifest.get("chunks_file", "chunks.json"))
            if not dense_path.exists() or not mapping_path.exists():
                continue
            if (
                hashlib.sha256(dense_path.read_bytes()).hexdigest()
                != manifest.get("dense_sha256")
            ):
                raise EduAgentError(
                    ErrorCode.INTERNAL_FAILURE,
                    f"array denso da versão {version_id} diverge do manifesto "
                    "publicado (mapa §6.5/§12)",
                    diagnostic=DIAGNOSTIC,
                )
            matrix = np.load(dense_path, allow_pickle=False)
            chunk_ids = list(json.loads(mapping_path.read_text(encoding="utf-8"))["chunk_ids"])
            row_index = {chunk_id: i for i, chunk_id in enumerate(chunk_ids)}
            positions = [
                row_index[chunk_id]
                for chunk_id, _ in group
                if chunk_id in row_index
            ]
            if not positions:
                continue
            sub = matrix[positions]  # arrays NumPy por snapshot, IP exato
            similarities = sub @ query_vector
            for (chunk_id, _), similarity in zip(
                [entry for entry in group if entry[0] in row_index], similarities
            ):
                scored.append((chunk_id, float(similarity)))
        ranked = sorted(scored, key=lambda item: (-item[1], item[0]))
        return [chunk_id for chunk_id, _ in ranked[: self.config.top_k]]

    def _build_pack(
        self,
        user_id: str,
        *,
        query: str,
        topic_uuids: list[_uuid.UUID],
        merged: list[tuple[str, float]],
        candidates: dict[str, dict[str, Any]],
        config_hash: str,
        token_counter: TokenCounter,
    ) -> EvidencePack:
        """Pacote ≤ 4.096 tokens (§6.7): top ``evidence_chunks`` por RRF
        dentro do orçamento; ranks finais 1-based únicos; citação resolve ao
        bloco original persistido."""
        by_rrf = [chunk_id for chunk_id, _ in merged]
        rank_of = {chunk_id: rank for rank, chunk_id in enumerate(by_rrf, start=1)}
        selected: list[EvidencePack.Chunk] = []
        used_tokens = 0
        for chunk_id in by_rrf:
            if len(selected) >= self.config.evidence_chunks:
                break
            row = candidates[chunk_id]
            chunk_tokens = token_counter.count(row["text"])
            if used_tokens + chunk_tokens > self.config.doc_token_budget:
                continue  # sem espaço no orçamento; tenta o próximo
            ref = self._primary_source_ref(user_id, row)
            selected.append(
                EvidencePack.Chunk(
                    id=_uuid.UUID(chunk_id),
                    text=row["text"],
                    source_ref=ref,
                    rank=rank_of[chunk_id],
                )
            )
            used_tokens += chunk_tokens
        coverage = (
            EvidencePack.Coverage.SUPPORTED
            if len(selected) >= self.config.evidence_chunks
            else EvidencePack.Coverage.PARTIAL
        )
        return EvidencePack(
            query=query,
            topic_ids=topic_uuids,
            chunks=selected,
            retrieval_config_hash=config_hash,
            coverage=coverage,
        )

    def _primary_source_ref(
        self, user_id: str, row: dict[str, Any]
    ) -> SourceRef:
        """``SourceRef`` primário do chunk: primeiro bloco referenciado,
        conferido contra ``blocks`` (006a: ``block_id`` persistido) — citação
        resolve ao original (§6.7)."""
        refs = list(row["block_refs"])
        if not refs:
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                f"chunk {row['chunk_id']} sem referência de bloco (mapa §6.4)",
                diagnostic=DIAGNOSTIC,
            )
        primary = refs[0]
        block_id = str(primary["block_id"])
        page = int(primary["page"])
        offsets = primary.get("offsets")
        block_rows = self._store.fetch_user_rows(
            "SELECT text FROM blocks WHERE user_id = ? AND version_id = ? "
            "AND block_id = ? AND page = ?",
            (user_id, row["version_id"], block_id, page),
        )
        if not block_rows:
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                f"bloco {block_id} do chunk {row['chunk_id']} não resolve no "
                "original armazenado (mapa §6.7)",
                diagnostic=DIAGNOSTIC,
            )
        block_text = str(block_rows[0]["text"])
        return SourceRef(
            doc_id=_uuid.UUID(row["doc_id"]),
            version_id=_uuid.UUID(row["version_id"]),
            physical_page=page,
            block_id=block_id,
            offsets=tuple(offsets) if offsets else None,
            text_hash=hashlib.sha256(block_text.encode("utf-8")).hexdigest(),
        )

    @staticmethod
    def _empty_pack(
        query: str, topic_uuids: list[_uuid.UUID], config_hash: str
    ) -> EvidencePack:
        """Abstinência explícita (§6.8): ``coverage=none`` e **zero chunks** —
        nenhuma citação fictícia; explicação geral rotulada é responsabilidade
        do agente chamador e não recebe citação."""
        return EvidencePack(
            query=query,
            topic_ids=topic_uuids,
            chunks=[],
            retrieval_config_hash=config_hash,
            coverage=EvidencePack.Coverage.NONE,
        )

    # -- §6.7: citação e validação ----------------------------------------------

    def format_citation(self, user_id: str, ref: SourceRef) -> str:
        """Formata a citação ``[doc_id@versão:página:bloco]`` (§6.7) a partir
        de um ``SourceRef``: a versão é o **ordinal** da versão no documento
        (convenção das ``artifact_dependencies`` da 006)."""
        ordinal = self.version_ordinal(
            user_id, str(ref.doc_id), str(ref.version_id)
        )
        return f"[{ref.doc_id}@{ordinal}:{ref.physical_page}:{ref.block_id}]"

    def resolve_citation(self, user_id: str, citation: str) -> ResolvedCitation:
        """Resolve ``[doc_id@versão:página:bloco]`` ao original armazenado
        (§6.7): ordinal de versão → ``doc_versions``; bloco → coluna
        ``blocks.block_id`` persistida (UNIQUE por versão, 006a); hash do
        texto conferido. Citação malformada/não resolvível é recusa tipada —
        nunca silêncio."""
        match = _CITATION_RE.match(citation.strip())
        if match is None:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"citação fora do formato [doc_id@versão:página:bloco]: "
                f"{citation!r} (mapa §6.7)",
                diagnostic=DIAGNOSTIC,
            )
        doc_id, ordinal_raw, page_raw, block_id = match.groups()
        ordinal = int(ordinal_raw)
        page = int(page_raw)
        rows = self._store.fetch_user_rows(
            "SELECT id FROM doc_versions WHERE user_id = ? AND doc_id = ? "
            "ORDER BY rowid",
            (user_id, doc_id),
        )
        version_ids = [str(row["id"]) for row in rows]
        if not (1 <= ordinal <= len(version_ids)):
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"versão {ordinal} inexistente para o documento {doc_id} do "
                "usuário (mapa §6.7)",
                diagnostic=DIAGNOSTIC,
            )
        version_id = version_ids[ordinal - 1]
        block_rows = self._store.fetch_user_rows(
            "SELECT text FROM blocks WHERE user_id = ? AND version_id = ? "
            "AND block_id = ?",
            (user_id, version_id, block_id),
        )
        if not block_rows:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"bloco {block_id} da citação não resolve ao original "
                "armazenado (mapa §6.7)",
                diagnostic=DIAGNOSTIC,
            )
        text = str(block_rows[0]["text"])
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return ResolvedCitation(
            doc_id=doc_id,
            version_id=version_id,
            version_ordinal=ordinal,
            page=page,
            block_id=block_id,
            text=text,
            text_hash=text_hash,
            source_ref=SourceRef(
                doc_id=_uuid.UUID(doc_id),
                version_id=_uuid.UUID(version_id),
                physical_page=page,
                block_id=block_id,
                text_hash=text_hash,
            ),
        )

    def validate_evidence_pack(
        self, user_id: str, pack: EvidencePack
    ) -> None:
        """Validator do §6.7: confere IDs, offsets e versão de cada chunk
        contra o estado armazenado — chunk inexistente, versão divergente,
        bloco ausente, página divergente, offsets fora do texto do bloco ou
        hash divergente falham tipados (pacote nunca é aprovado em silêncio,
        §12)."""
        for chunk in pack.chunks:
            rows = self._store.fetch_user_rows(
                "SELECT version_id, text FROM chunks WHERE id = ? AND "
                "user_id = ?",
                (str(chunk.id), user_id),
            )
            if not rows:
                raise EduAgentError(
                    ErrorCode.INTERNAL_FAILURE,
                    f"chunk {chunk.id} do pacote não existe para o usuário "
                    "(mapa §6.7)",
                    diagnostic=DIAGNOSTIC,
                )
            if str(rows[0]["version_id"]) != str(chunk.source_ref.version_id):
                raise EduAgentError(
                    ErrorCode.INTERNAL_FAILURE,
                    f"versão do chunk {chunk.id} diverge do SourceRef "
                    "(mapa §6.7: validator confere versão)",
                    diagnostic=DIAGNOSTIC,
                )
            if chunk.text != str(rows[0]["text"]):
                raise EduAgentError(
                    ErrorCode.INTERNAL_FAILURE,
                    f"texto do chunk {chunk.id} diverge do armazenado "
                    "(mapa §6.7)",
                    diagnostic=DIAGNOSTIC,
                )
            block_rows = self._store.fetch_user_rows(
                "SELECT text FROM blocks WHERE user_id = ? AND version_id = ? "
                "AND block_id = ?",
                (user_id, str(chunk.source_ref.version_id), chunk.source_ref.block_id),
            )
            if not block_rows:
                raise EduAgentError(
                    ErrorCode.INTERNAL_FAILURE,
                    f"bloco {chunk.source_ref.block_id} do chunk {chunk.id} "
                    "não existe na versão (mapa §6.7: validator confere IDs)",
                    diagnostic=DIAGNOSTIC,
                )
            block_text = str(block_rows[0]["text"])
            if hashlib.sha256(block_text.encode("utf-8")).hexdigest() != chunk.source_ref.text_hash:
                raise EduAgentError(
                    ErrorCode.INTERNAL_FAILURE,
                    f"hash do bloco {chunk.source_ref.block_id} diverge do "
                    "SourceRef (mapa §6.7)",
                    diagnostic=DIAGNOSTIC,
                )
            if chunk.source_ref.offsets is not None:
                start, end = chunk.source_ref.offsets
                if start < 0 or end > len(block_text) or start > end:
                    raise EduAgentError(
                        ErrorCode.INTERNAL_FAILURE,
                        f"offsets do chunk {chunk.id} fora do texto do bloco "
                        "(mapa §6.7: validator confere offsets)",
                        diagnostic=DIAGNOSTIC,
                    )


__all__ = [
    "BGE_M3_REPO",
    "BGE_M3_REVISION",
    "BM25_B",
    "BM25_K1",
    "BlockInput",
    "BlockRef",
    "BgeM3Embedder",
    "CHUNK_MAX_CHARS",
    "CHUNK_MAX_OVERLAP_TOKENS",
    "CHUNK_TARGET_TOKENS",
    "Chunk",
    "DOC_TOKEN_BUDGET",
    "DIAGNOSTIC",
    "DenseEmbedder",
    "EVIDENCE_CHUNKS",
    "EvidencePack",
    "HeuristicTokenCounter",
    "INDEX_SCHEMA",
    "RETRIEVAL_TOP_K",
    "RRF_K",
    "ResolvedCitation",
    "RetrievalConfig",
    "RetrievalService",
    "TOKENIZER_VERSION",
    "TokenCounter",
    "chunk_blocks",
    "retrieval_config_hash",
    "rrf_merge",
    "tokenize",
    "tokenizer_fingerprint",
]
