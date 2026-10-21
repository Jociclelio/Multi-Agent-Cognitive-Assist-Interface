"""Serviço de ingestão do Curador (mapa normativo
``fase2/documentos/04_mapa_completo_do_sistema.md``, §6 itens 1–2, §3, §12;
task 006).

Contratos implementados:

- **§6.1 — validação de entrada**: ownership (usuário existe; disciplina
  pertence ao usuário), MIME decidido **pelos bytes** (número mágico/hex
  válido — o tipo declarado nunca decide sozinho e divergência é recusada),
  limites de §3 (50 MiB / 500 páginas / 600 s / subprocesso 4 GiB — defaults
  de ensaio a calibrar; oversized é **recusado** ou dividido pelo usuário) e
  path canônico construído só de SHA-256/UUID sob ``data/<user_id>/`` —
  caminho de traversal é impossível por construção e o nome do arquivo é
  reduzido a uma extensão da allowlist. Original é arquivado com o SHA-256
  calculado dos bytes.
- **§6.1 — duplicata exata**: mesma bytes (mesmo SHA-256, mesmo usuário) na
  mesma disciplina devolvem a versão existente sem nova versão (dedup antes
  da versão, lixo da 005); em outra disciplina, um **novo documento** é
  criado reaproveitando os mesmos bytes arquivados (mesmo ``original_ref``),
  preservando vínculos por disciplina. Bytes não são reescritos.
- **§6.1 — ciclo de versão**: nova versão nasce ``pending``; só fica
  ``indexed`` após extração completa (todas as páginas processadas); só uma
  versão ``indexed`` pode virar ``active`` — versão incompleta nunca vira
  ativa (§12).
- **§6.2 — extração com proveniência**: o extrator (protocolo
  ``BlockExtractor``; Docling no MVP) produz blocos ordenados por página com
  kind/texto/bbox; cada bloco persistido carrega proveniência completa
  (``SourceRef`` computável: doc, versão, página física, índice, offsets,
  hash do texto). Páginas vazias/ruidosas recebem diagnóstico explícito
  (``empty``/``noisy``), nunca silêncio (§12: métrica desconhecida não é
  zero).
- **§6.2 — OCR seletivo**: disparado quando a versão base tem páginas
  vazias/ruidosas; idiomas permitidos ``por``/``por+eng``; produz um
  **derivado separado** (nova ``doc_version`` com ``derived_from`` em
  ``artifact_dependencies``) e **reextrai o documento inteiro** (não só as
  páginas falhas). Texto que veio apenas do sidecar OCR nunca é texto total:
  página só com sidecar é diagnosticada ``sidecar_only`` e um documento cujo
  texto integral é sidecar não indexa (recusa tipada).
- **§6.2/§12 — pendências e job**: equações/tabelas não legíveis ficam
  pendentes (``legible=false``, contadas em ``pending_items``); progresso por
  página (``pages_done``); job cancelável — cancelamento produz erro tipado
  ``CANCELLED`` e a versão fica ``failed``/``pending``, nunca ativa; timeout
  do §3 produz ``TIMEOUT``.

O subprocesso com limite de memória (§3) é usado pelo adaptador Docling real
(``run_in_subprocess``) e verificável por teste com função picklável. A
lógica de pipeline é testada com extratores injetados que implementam o
mesmo protocolo — o extrator é fronteira injetável, não parte do contrato.

Nada aqui apresenta resultados medidos: limites são defaults de ensaio
(mapa §1/§3) e contadores são estado do pipeline.
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import re
import resource
import threading
import time
import uuid as _uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from eduagent.contracts import ErrorCode, EduAgentError, SourceRef
from eduagent.storage.repository import DomainStore

#: Referência de diagnóstico local do serviço (mapa §4).
DIAGNOSTIC = "eduagent/services/ingestion.py"

# ---------------------------------------------------------------------------
# Limites de §3 — defaults de ensaio a calibrar no hardware registrado;
# NÃO são resultados medidos (mapa §1/§3).
# ---------------------------------------------------------------------------

MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MiB
MAX_PAGES = 500
TIMEOUT_S = 600
SUBPROCESS_MEM_GIB = 4

#: MIME permitidos e a assinatura por bytes de cada um (§6.1: "MIME por
#: bytes"). ``text/plain`` não tem número mágico: exige decodificação UTF-8
#: estrita dos bytes (heurística declarada aqui, não inferida de extensão).
MIME_SIGNATURES: dict[str, bytes | None] = {
    "application/pdf": b"%PDF-",
    "text/plain": None,
}

#: Extensões canônicas por MIME — o nome do arquivo nunca define o tipo;
#: a extensão do path canônico deriva do MIME detectado por bytes.
MIME_EXTENSIONS: dict[str, str] = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
}

#: Idiomas do OCR seletivo (§6.2: "OCR seletivo `por`/`por+eng`").
OCR_LANGUAGES = frozenset({"por", "por+eng"})

#: Limiar de densidade de caracteres para diagnóstico de página ruidosa —
#: default de ensaio (caracteres imprimíveis por página), não resultado
#: medido.
NOISY_CHAR_FLOOR = 32


# ---------------------------------------------------------------------------
# Limites configuráveis
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IngestionLimits:
    """Limites de ingestão do §3 (defaults de ensaio)."""

    max_size_bytes: int = MAX_SIZE_BYTES
    max_pages: int = MAX_PAGES
    timeout_s: float = TIMEOUT_S
    subprocess_mem_gib: int = SUBPROCESS_MEM_GIB

    @classmethod
    def from_mapping(cls, config: dict[str, Any] | None) -> "IngestionLimits":
        """Constrói a partir de ``config['ingestion']`` do default.yaml;
        chaves ausentes mantêm os defaults de ensaio."""
        section = (config or {}).get("ingestion") or {}
        return cls(
            max_size_bytes=int(section.get("max_size_mib", 50)) * 1024 * 1024,
            max_pages=int(section.get("max_pages", MAX_PAGES)),
            timeout_s=float(section.get("timeout_s", TIMEOUT_S)),
            subprocess_mem_gib=int(section.get("subprocess_mem_gib", SUBPROCESS_MEM_GIB)),
        )


# ---------------------------------------------------------------------------
# MIME por bytes (§6.1)
# ---------------------------------------------------------------------------


def sniff_mime(data: bytes) -> str | None:
    """Detecta o MIME **pelos bytes** (§6.1).

    - ``%PDF-`` no início → ``application/pdf``;
    - decodificação UTF-8 estrita → ``text/plain``;
    - caso contrário → ``None`` (tipo não admitido).
    """
    if data.startswith(MIME_SIGNATURES["application/pdf"]):
        return "application/pdf"
    if data:
        try:
            data.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return None
        # Texto com bytes de controle (exceto tab/newline/CR) não é texto.
        if any(b < 9 or (13 < b < 32) for b in data):
            return None
        return "text/plain"
    return None


def _canonical_extension(mime: str) -> str:
    extension = MIME_EXTENSIONS.get(mime)
    if extension is None:
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            f"MIME {mime!r} sem extensão canônica (mapa §6.1)",
            diagnostic=DIAGNOSTIC,
        )
    return extension


# ---------------------------------------------------------------------------
# Path canônico (§6.1) e subprocesso com limite (§3)
# ---------------------------------------------------------------------------


def canonical_original_path(data_root: Path, user_id: str, sha256: str, mime: str) -> Path:
    """Path canônico do original arquivado (§6.1).

    Componentes: ``<data_root>/<user_id>/originals/<sha256><ext>`` — SHA-256
    hex minúsculo e extensão derivada do MIME por bytes; nenhum componente
    vem do nome do arquivo enviado, então traversal é impossível por
    construção. A checagem explícita abaixo é defesa em profundidade.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise EduAgentError(
            ErrorCode.INTERNAL_FAILURE,
            "SHA-256 fora da forma canônica (mapa §6.1)",
            diagnostic=DIAGNOSTIC,
        )
    path = Path(data_root) / user_id / "originals" / f"{sha256}{_canonical_extension(mime)}"
    resolved_root = Path(data_root).resolve()
    if not path.resolve().is_relative_to(resolved_root):
        raise EduAgentError(
            ErrorCode.INTERNAL_FAILURE,
            "path canônico escapou da raiz de dados (mapa §6.1)",
            diagnostic=DIAGNOSTIC,
        )
    return path


def _subprocess_target(
    fn: Callable[[], Any], queue: "multiprocessing.Queue[Any]", mem_gib: int
) -> None:
    """Alvo do subprocesso: aplica o limite de memória (§3) como primeira
    ação do filho e executa ``fn``, devolvendo resultado/erro pela fila."""
    try:
        limit_bytes = mem_gib * (1 << 30)
        resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
    except (ValueError, OSError):
        pass  # plataforma sem RLIMIT_AS: o limite de ensaio não se aplica
    try:
        queue.put(("ok", fn()))
    except BaseException as exc:  # noqa: BLE001 — erro cruza fronteira de processo
        queue.put(("error", f"{type(exc).__name__}: {exc}"))


def run_in_subprocess(
    fn: Callable[[], Any],
    *,
    mem_gib: int,
    timeout_s: float,
) -> Any:
    """Executa ``fn`` (picklável, nível de módulo) em subprocesso com
    ``RLIMIT_AS = mem_gib`` GiB e timeout ``timeout_s`` (mapa §3).

    Timeout levanta ``EduAgentError(TIMEOUT)`` (retentável, §4); o filho é
    terminado (SIGKILL após TERM curto). Falha do filho é refeita como
    ``INTERNAL_FAILURE`` com o motivo relatado. Usado pelo adaptador Docling
    real; testes exercitam o mecanismo com função trivial picklável.
    """
    queue: "multiprocessing.Queue[Any]" = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=_subprocess_target,
        args=(fn, queue, mem_gib),
    )
    process.start()
    process.join(timeout_s)
    if process.is_alive():
        process.terminate()
        process.join(1.0)
        if process.is_alive():
            process.kill()
            process.join(1.0)
        raise EduAgentError(
            ErrorCode.TIMEOUT,
            f"extração excedeu {timeout_s}s de subprocesso e foi terminada "
            "(mapa §3)",
            diagnostic=DIAGNOSTIC,
        )
    if process.exitcode != 0:
        raise EduAgentError(
            ErrorCode.INTERNAL_FAILURE,
            f"subprocesso de extração terminou com exitcode {process.exitcode}",
            diagnostic=DIAGNOSTIC,
        )
    try:
        status, payload = queue.get_nowait()
    except Exception as exc:  # noqa: BLE001 — fila vazia/corrompida
        raise EduAgentError(
            ErrorCode.INTERNAL_FAILURE,
            f"subprocesso não devolveu resultado: {type(exc).__name__}",
            diagnostic=DIAGNOSTIC,
        ) from exc
    if status != "ok":
        raise EduAgentError(
            ErrorCode.INTERNAL_FAILURE,
            f"extração falhou no subprocesso: {payload}",
            diagnostic=DIAGNOSTIC,
        )
    return payload


# ---------------------------------------------------------------------------
# Registros de extração (contrato do extrator — §6.2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BlockRecord:
    """Bloco produzido pelo extrator (§6.2): ordenado, com kind e texto.

    ``ocr_source`` é ``None`` (texto nativo), ``"embedded"`` (camada de texto
    do PDF) ou ``"sidecar"`` (texto de sidecar OCR). Blocos de
    tabela/equação não legíveis chegam com ``legible=False`` e ficam
    pendentes (§6.2).
    """

    page: int
    kind: str  # heading | paragraph | table | equation | caption | ...
    text: str
    order_in_page: int
    bbox: tuple[float, float, float, float] | None = None
    offsets: tuple[int, int] | None = None
    legible: bool = True
    ocr_source: str | None = None


@dataclass(frozen=True)
class PageRecord:
    """Página extraída com blocos ordenados (§6.2)."""

    page: int
    blocks: list[BlockRecord]


@dataclass
class ExtractedDocument:
    """Documento extraído: páginas em ordem, diagnóstico por página e
    pendências (§6.2)."""

    pages: list[PageRecord] = field(default_factory=list)
    page_diagnosis: dict[int, str] = field(default_factory=dict)
    sidecar_only_pages: set[int] = field(default_factory=set)

    @property
    def total_pages(self) -> int:
        return len(self.pages)

    def diagnose_pages(self, *, noisy_char_floor: int = NOISY_CHAR_FLOOR) -> None:
        """Diagnóstico explícito por página (§6.2): ``empty`` (sem texto),
        ``noisy`` (densidade abaixo do piso de ensaio), ``sidecar_only``
        (texto apenas de sidecar OCR) ou ``ok``. Página ausente de
        ``page_diagnosis`` após a chamada é falha interna — diagnóstico é
        obrigatório, nunca silêncio (§12)."""
        for record in self.pages:
            text = "".join(block.text for block in record.blocks)
            if not text.strip():
                diagnosis = "empty"
            elif all(
                block.ocr_source == "sidecar"
                for block in record.blocks
                if block.text.strip()
            ) and any(block.text.strip() for block in record.blocks):
                diagnosis = "sidecar_only"
                self.sidecar_only_pages.add(record.page)
            elif len(text.strip()) < noisy_char_floor:
                diagnosis = "noisy"
            else:
                diagnosis = "ok"
            self.page_diagnosis[record.page] = diagnosis
        if len(self.page_diagnosis) != len(self.pages):
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                "páginas sem diagnóstico após extração (mapa §6.2/§12)",
                diagnostic=DIAGNOSTIC,
            )

    def has_empty_or_noisy_pages(self) -> bool:
        return any(
            diagnosis in ("empty", "noisy")
            for diagnosis in self.page_diagnosis.values()
        )

    def pending_items(self) -> list[dict[str, Any]]:
        """Equações/tabelas não legíveis ficam pendentes (§6.2)."""
        return [
            {
                "page": block.page,
                "kind": block.kind,
                "reason": "not_legible",
            }
            for record in self.pages
            for block in record.blocks
            if not block.legible
        ]

    def assert_not_sidecar_only_document(self) -> None:
        """Nunca usar apenas sidecar OCR como texto total (§6.2).

        Se **todo** o texto do documento veio de sidecar OCR, o documento não
        tem texto próprio: indexá-lo seria promover sidecar a texto total.
        Recusa tipada; o caminho correto é OCR seletivo com reextração
        integral (``selective_ocr``)."""
        text_blocks = [
            block for record in self.pages for block in record.blocks if block.text.strip()
        ]
        if text_blocks and all(
            block.ocr_source == "sidecar" for block in text_blocks
        ):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "texto integral do documento é apenas sidecar OCR — recusado "
                "como texto total (mapa §6.2); rode OCR seletivo com "
                "reextração do documento inteiro",
                diagnostic=DIAGNOSTIC,
            )


class BlockExtractor(Protocol):
    """Protocolo do extrator (Docling no MVP; fronteira injetável).

    Implementações DEVEM checar ``cancelled`` e ``on_page`` a cada página e
    respeitar ``max_pages`` — o serviço também confere, mas o extrator é quem
    itera.
    """

    name: str
    version: str

    def extract(
        self,
        data: bytes,
        mime: str,
        *,
        max_pages: int,
        languages: tuple[str, ...] | None = None,
        on_page: Callable[[int], None] | None = None,
        cancelled: Callable[[], bool] = lambda: False,
    ) -> ExtractedDocument:
        """Extrai o documento inteiro em páginas ordenadas (§6.2)."""
        ...


# ---------------------------------------------------------------------------
# Job de extração — progresso por página e cancelamento (§12)
# ---------------------------------------------------------------------------


@dataclass
class ExtractionJob:
    """Job de ingestão cancelável com progresso por página (mapa §12)."""

    total_pages: int = 0
    pages_done: int = 0
    started_at: float = field(default_factory=time.monotonic)
    timeout_s: float = TIMEOUT_S
    _cancel: threading.Event = field(default_factory=threading.Event, repr=False)

    def cancel(self) -> None:
        """Pede cancelamento; o loop de páginas observa a cada página."""
        self._cancel.set()

    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def check_cancelled(self) -> None:
        if self._cancel.is_set():
            raise EduAgentError(
                ErrorCode.CANCELLED,
                "job de ingestão cancelado (mapa §12)",
                diagnostic=DIAGNOSTIC,
            )

    def check_deadline(self) -> None:
        if time.monotonic() - self.started_at > self.timeout_s:
            raise EduAgentError(
                ErrorCode.TIMEOUT,
                f"ingestão excedeu o limite de {self.timeout_s}s (mapa §3)",
                diagnostic=DIAGNOSTIC,
            )

    def report(self) -> dict[str, Any]:
        """Progresso e pêndencias (§12: "indica páginas concluídas")."""
        return {
            "total_pages": self.total_pages,
            "pages_done": self.pages_done,
            "cancelled": self.cancelled(),
        }


# ---------------------------------------------------------------------------
# Resultados do serviço
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IngestResult:
    """Resultado da ingestão de um documento (§6.1)."""

    doc_id: str
    version_id: str
    version_status: str
    sha256: str
    mime: str
    original_path: str  # relativo a data_root (canônico, §6.1)
    bytes_reused: bool
    duplicate: bool
    new_version: bool
    job_report: dict[str, Any] | None = None


@dataclass(frozen=True)
class OcrDeriveResult:
    """Resultado do OCR seletivo (§6.2): derivado separado do documento
    inteiro."""

    base_version_id: str
    derived_version_id: str
    languages: str
    total_pages_reextracted: int


# ---------------------------------------------------------------------------
# Serviço de ingestão
# ---------------------------------------------------------------------------


class IngestionService:
    """Fachada de ingestão do Curador (mapa §6.1–2, §3, §12).

    Usa ``DomainStore`` (task 004) para estado de domínio — escritas por
    transação curta com ``domain_revision``; os bytes/arquivos vivem sob
    ``data_root`` com paths canônicos.
    """

    def __init__(
        self,
        store: DomainStore,
        data_root: Path | str,
        *,
        limits: IngestionLimits | None = None,
        extractor: BlockExtractor | None = None,
    ) -> None:
        self._store = store
        self._data_root = Path(data_root)
        self.limits = limits or IngestionLimits()
        self._extractor = extractor

    # -- §6.1: validação -----------------------------------------------------

    def _validate_ownership(self, user_id: str, course_id: str) -> None:
        """Ownership (§6.1/§15.1): usuário existe; disciplina pertence ao
        usuário. Consulta sempre parametrizada por ``user_id``."""
        rows = self._store.fetch_user_rows(
            "SELECT id FROM users WHERE id = ?", (user_id,)
        )
        if not rows:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"usuário {user_id} não existe no domínio",
                diagnostic=DIAGNOSTIC,
            )
        courses = self._store.fetch_user_rows(
            "SELECT id FROM courses WHERE id = ? AND user_id = ?",
            (course_id, user_id),
        )
        if not courses:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"disciplina {course_id} inexistente ou fora do ownership do "
                f"usuário {user_id} (mapa §6.1/§15.1)",
                diagnostic=DIAGNOSTIC,
            )

    @staticmethod
    def _validate_mime_by_bytes(data: bytes, declared_mime: str | None) -> str:
        """MIME decidido pelos bytes (§6.1); tipo declarado divergente é
        recusado — JSON/declaração não substitui a inspeção dos bytes."""
        mime = sniff_mime(data)
        if mime is None or mime not in MIME_SIGNATURES:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "MIME dos bytes não é admitido (permitido: "
                f"{sorted(MIME_SIGNATURES)}; mapa §6.1)",
                diagnostic=DIAGNOSTIC,
            )
        if declared_mime is not None and declared_mime != mime:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"MIME declarado {declared_mime!r} diverge do detectado por "
                f"bytes {mime!r} (mapa §6.1)",
                diagnostic=DIAGNOSTIC,
            )
        return mime

    def _validate_size(self, data: bytes) -> None:
        """Limite de tamanho (§3): oversized é recusado (ou dividido pelo
        usuário — divisão é decisão do usuário, fora deste serviço)."""
        if len(data) > self.limits.max_size_bytes:
            raise EduAgentError(
                ErrorCode.RESOURCE_LIMIT,
                f"documento com {len(data)} bytes excede o limite de "
                f"{self.limits.max_size_bytes} bytes (mapa §3); recusado — "
                "divida pelo usuário e reenvie",
                diagnostic=DIAGNOSTIC,
            )

    # -- §6.1: arquivamento e duplicata ---------------------------------------

    def _archive_original(self, user_id: str, sha256: str, mime: str, data: bytes) -> tuple[Path, bool]:
        """Arquiva o original e devolve ``(path, reused)``; bytes idênticos
        (mesmo SHA) não são reescritos (§6.1: duplicata reaproveita bytes)."""
        path = canonical_original_path(self._data_root, user_id, sha256, mime)
        if path.exists():
            existing = path.read_bytes()
            if existing != data:
                raise EduAgentError(
                    ErrorCode.INTERNAL_FAILURE,
                    "colisão de SHA-256 com conteúdo diferente — integridade "
                    "violada (mapa §6.1)",
                    diagnostic=DIAGNOSTIC,
                )
            return path, True
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path, False

    def _find_exact_duplicate(
        self, user_id: str, sha256: str, course_id: str
    ) -> dict[str, Any] | None:
        """Duplicata exata (§6.1): mesma bytes do mesmo usuário **na mesma
        disciplina** → devolve a versão existente (dedup antes da versão)."""
        rows = self._store.fetch_user_rows(
            "SELECT dv.id AS version_id, dv.doc_id, dv.status, dv.mime "
            "FROM doc_versions dv JOIN documents d ON d.id = dv.doc_id "
            "WHERE dv.user_id = ? AND dv.sha256 = ? AND d.course_id = ? "
            "ORDER BY dv.rowid LIMIT 1",
            (user_id, sha256, course_id),
        )
        return dict(rows[0]) if rows else None

    # -- §6.1: ciclo de versão --------------------------------------------------

    def activate_version(self, user_id: str, doc_id: str, version_id: str) -> None:
        """Promove a versão a ativa — **somente** se ``indexed`` (§6.1: nova
        versão não ativa antes da indexação completa; §12: versão incompleta
        nunca vira ativa). Tentativa com versão ``pending``/``failed`` é
        recusa tipada."""
        rows = self._store.fetch_user_rows(
            "SELECT id, doc_id, status FROM doc_versions WHERE id = ? "
            "AND user_id = ? AND doc_id = ?",
            (version_id, user_id, doc_id),
        )
        if not rows:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"versão {version_id} inexistente para o documento/docínio "
                "informado (mapa §6.1)",
                diagnostic=DIAGNOSTIC,
            )
        status = str(rows[0]["status"])
        if status != "indexed":
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"versão em estado {status!r} não pode ativar — indexação "
                "completa é pré-condição (mapa §6.1/§12)",
                diagnostic=DIAGNOSTIC,
            )
        self._store.execute_write(
            user_id,
            [("UPDATE documents SET active_version = ? WHERE id = ?", (version_id, doc_id))],
        )

    def version_status(self, user_id: str, version_id: str) -> str:
        rows = self._store.fetch_user_rows(
            "SELECT status FROM doc_versions WHERE id = ? AND user_id = ?",
            (version_id, user_id),
        )
        if not rows:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"versão {version_id} não existe para o usuário",
                diagnostic=DIAGNOSTIC,
            )
        return str(rows[0]["status"])

    # -- ingestão completa -----------------------------------------------------

    def ingest(
        self,
        user_id: str,
        course_id: str,
        data: bytes,
        *,
        filename: str | None = None,
        declared_mime: str | None = None,
        doc_id: str | None = None,
        job: ExtractionJob | None = None,
        extractor: BlockExtractor | None = None,
        expected_version: int | None = None,
    ) -> IngestResult:
        """Ingestão completa (§6.1): validação → arquivamento → dedup →
        documento/versão ``pending`` → extração completa → ``indexed``.

        ``filename`` nunca define o tipo nem entra no path canônico (§6.1);
        ``doc_id`` informado cria **nova versão** de documento existente do
        usuário/disciplina (que só ativa após indexação completa, §6.1);
        ``job`` permite cancelamento e leitura de progresso por página.
        """
        del filename  # nunca usado para tipo/path (§6.1: MIME por bytes)
        self._validate_ownership(user_id, course_id)
        self._validate_size(data)
        mime = self._validate_mime_by_bytes(data, declared_mime)
        sha256 = hashlib.sha256(data).hexdigest()
        original_path, bytes_reused = self._archive_original(user_id, sha256, mime, data)
        relative = str(original_path.relative_to(Path(self._data_root).resolve()))

        duplicate = self._find_exact_duplicate(user_id, sha256, course_id)
        if duplicate is not None and doc_id is None:
            # Duplicata exata na mesma disciplina: bytes reaproveitados,
            # vínculo por disciplina preservado, nenhuma versão nova (§6.1).
            return IngestResult(
                doc_id=str(duplicate["doc_id"]),
                version_id=str(duplicate["version_id"]),
                version_status=str(duplicate["status"]),
                sha256=sha256,
                mime=mime,
                original_path=relative,
                bytes_reused=True,
                duplicate=True,
                new_version=False,
                job_report=None,
            )

        # Mesmo SHA em outra disciplina: novo documento reaproveita os bytes
        # arquivados (mesmo original_ref), preservando vínculos (§6.1).
        new_document = doc_id is None
        if new_document:
            doc_id = str(_uuid.uuid4())
        else:
            owned = self._store.fetch_user_rows(
                "SELECT id FROM documents WHERE id = ? AND user_id = ? AND "
                "course_id = ?",
                (doc_id, user_id, course_id),
            )
            if not owned:
                raise EduAgentError(
                    ErrorCode.SOURCE_UNRESOLVED,
                    "documento base da nova versão inexistente ou fora do "
                    "ownership do usuário/disciplina (mapa §6.1/§15.1)",
                    diagnostic=DIAGNOSTIC,
                )
        version_id = str(_uuid.uuid4())
        manifest = self._extractor_manifest(extractor)
        statements: list[tuple[str, tuple[Any, ...]]] = []
        if new_document:
            statements.append(
                (
                    "INSERT INTO documents(id, user_id, course_id) VALUES (?,?,?)",
                    (doc_id, user_id, course_id),
                )
            )
        statements.append(
            (
                "INSERT INTO doc_versions(id, user_id, doc_id, sha256, mime, "
                "original_ref, extractor_manifest, status) "
                "VALUES (?,?,?,?,?,?,?,'pending')",
                (version_id, user_id, doc_id, sha256, mime, relative, manifest),
            )
        )
        self._store.execute_write(user_id, statements, expected_version=expected_version)

        self._run_extraction(
            user_id,
            doc_id=doc_id,
            version_id=version_id,
            data=data,
            mime=mime,
            job=job,
            extractor=extractor,
        )
        return IngestResult(
            doc_id=doc_id,
            version_id=version_id,
            version_status=self.version_status(user_id, version_id),
            sha256=sha256,
            mime=mime,
            original_path=relative,
            bytes_reused=bytes_reused,
            duplicate=False,
            new_version=True,
            job_report=job.report() if job is not None else None,
        )

    def _extractor_manifest(self, extractor: BlockExtractor | None) -> str:
        """Manifesto do extrator registrado na versão (§5: ``extractor_
        manifest``); identidade real do extrator, nunca promessa."""
        active = extractor or self._extractor
        if active is None:
            return json.dumps({"extractor": None, "note": "no_extractor_configured"})
        return json.dumps(
            {
                "extractor": getattr(active, "name", "unknown"),
                "version": str(getattr(active, "version", "0")),
            },
            sort_keys=True,
        )

    # -- §6.2: extração com proveniência e progresso ----------------------------

    def _run_extraction(
        self,
        user_id: str,
        *,
        doc_id: str,
        version_id: str,
        data: bytes,
        mime: str,
        job: ExtractionJob | None,
        extractor: BlockExtractor | None,
        languages: str | None = None,
    ) -> None:
        active_extractor = extractor or self._extractor
        if active_extractor is None:
            # Sem extrator configurado, a versão permanece 'pending' — nunca
            # 'indexed' nem ativa (§6.1/§12). Impedimento explícito, não
            # sucesso fingido.
            return
        local_job = job if job is not None else ExtractionJob(timeout_s=self.limits.timeout_s)
        try:
            local_job.check_deadline()
            extracted = active_extractor.extract(
                data,
                mime,
                max_pages=self.limits.max_pages,
                languages=(languages,) if languages else None,
                on_page=lambda page: self._on_page(local_job, page),
                cancelled=local_job.cancelled,
            )
            local_job.check_cancelled()
            local_job.check_deadline()
            extracted.diagnose_pages()
            local_job.total_pages = extracted.total_pages
            if extracted.total_pages > self.limits.max_pages:
                raise EduAgentError(
                    ErrorCode.RESOURCE_LIMIT,
                    f"documento com {extracted.total_pages} páginas excede o "
                    f"limite de {self.limits.max_pages} (mapa §3)",
                    diagnostic=DIAGNOSTIC,
                )
            extracted.assert_not_sidecar_only_document()
            self._persist_blocks(user_id, version_id=version_id, extracted=extracted)
            local_job.pages_done = extracted.total_pages
            # Extração completa: versão 'indexed'. Ativação é passo separado e
            # explícito (§6.1: nova versão não ativa antes da indexação
            # completa; a indexação BM25/vetorial da 007 ocorre antes de
            # ativar).
            self._store.execute_write(
                user_id,
                [
                    (
                        "UPDATE doc_versions SET status = 'indexed' WHERE id = ?",
                        (version_id,),
                    )
                ],
            )
        except EduAgentError:
            self._mark_version_failed(user_id, version_id)
            raise
        except Exception as exc:
            self._mark_version_failed(user_id, version_id)
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                f"extração falhou: {type(exc).__name__}",
                diagnostic=DIAGNOSTIC,
            ) from exc

    @staticmethod
    def _on_page(job: ExtractionJob, page: int) -> None:
        job.check_cancelled()
        job.check_deadline()
        job.pages_done = max(job.pages_done, page)

    def _mark_version_failed(self, user_id: str, version_id: str) -> None:
        self._store.execute_write(
            user_id,
            [("UPDATE doc_versions SET status = 'failed' WHERE id = ?", (version_id,))],
        )

    def _persist_blocks(
        self,
        user_id: str,
        *,
        version_id: str,
        extracted: ExtractedDocument,
    ) -> None:
        """Persiste blocos ordenados com proveniência completa (§6.2) e
        diagnóstico por página em ``diagnosis_json`` (§5)."""
        statements: list[tuple[str, tuple[Any, ...]]] = []
        for record in extracted.pages:
            diagnosis = extracted.page_diagnosis[record.page]
            for block in record.blocks:
                block_id = f"p{record.page}b{block.order_in_page + 1}"
                block_id = block_id[:64]
                statements.append(
                    (
                        "INSERT INTO blocks(id, user_id, version_id, page, "
                        "order_index, kind, text, bbox_json, diagnosis_json) "
                        "VALUES (?,?,?,?,?,?,?,?,?)",
                        (
                            str(_uuid.uuid4()),
                            user_id,
                            version_id,
                            record.page,
                            self._global_order(extracted, record, block),
                            block.kind,
                            block.text,
                            (
                                json.dumps(block.bbox)
                                if block.bbox is not None
                                else None
                            ),
                            json.dumps(
                                {
                                    "page": diagnosis,
                                    "legible": block.legible,
                                    "ocr_source": block.ocr_source,
                                },
                                sort_keys=True,
                            ),
                        ),
                    )
                )
        self._store.execute_write(user_id, statements)

    @staticmethod
    def _global_order(extracted: ExtractedDocument, record: PageRecord, block: BlockRecord) -> int:
        """Ordem global estável: página × 10⁴ + ordem na página (§6.2: blocos
        ordenados)."""
        return record.page * 10_000 + block.order_in_page

    def source_refs_for_version(
        self, user_id: str, version_id: str, doc_id: str
    ) -> list[SourceRef]:
        """Proveniência resolvível (§6.2/§4): ``SourceRef`` por bloco
        persistido, com hash do texto — citação fecha de volta ao bloco."""
        rows = self._store.fetch_user_rows(
            "SELECT page, order_index, kind, text FROM blocks "
            "WHERE user_id = ? AND version_id = ? ORDER BY page, order_index",
            (user_id, version_id),
        )
        refs: list[SourceRef] = []
        for row in rows:
            page = int(row["page"])
            order = int(row["order_index"])
            text = str(row["text"])
            refs.append(
                SourceRef(
                    doc_id=_uuid.UUID(doc_id),
                    version_id=_uuid.UUID(version_id),
                    physical_page=page,
                    block_id=f"p{page}b{order % 10_000 + 1}"[:64],
                    offsets=None,
                    bbox=None,
                    text_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                )
            )
        return refs

    # -- §6.2: OCR seletivo ------------------------------------------------------

    def selective_ocr(
        self,
        user_id: str,
        doc_id: str,
        base_version_id: str,
        languages: str,
        *,
        data: bytes,
        job: ExtractionJob | None = None,
        extractor: BlockExtractor | None = None,
    ) -> OcrDeriveResult:
        """OCR seletivo (§6.2): idiomas ``por``/``por+eng``, **derivado
        separado** (nova versão + ``derived_from`` em
        ``artifact_dependencies``) e **reextração do documento inteiro**.

        A base permanece intacta; o derivado nasce ``pending`` e só fica
        ``indexed`` após a reextração completa. Páginas legíveis da base não
        dispensam a reextração integral (§6.2: "reextrair documento
        inteiro").
        """
        if languages not in OCR_LANGUAGES:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"idiomas de OCR {languages!r} fora do permitido "
                f"{sorted(OCR_LANGUAGES)} (mapa §6.2)",
                diagnostic=DIAGNOSTIC,
            )
        base = self._store.fetch_user_rows(
            "SELECT id, doc_id, sha256, mime FROM doc_versions WHERE id = ? "
            "AND user_id = ? AND doc_id = ?",
            (base_version_id, user_id, doc_id),
        )
        if not base:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                "versão base do OCR seletivo inexistente (mapa §6.2)",
                diagnostic=DIAGNOSTIC,
            )
        mime = str(base[0]["mime"])
        sha256 = str(base[0]["sha256"])
        derived_version_id = str(_uuid.uuid4())
        manifest = json.dumps(
            {
                "extractor": getattr(
                    extractor or self._extractor, "name", "unknown"
                ),
                "version": str(
                    getattr(extractor or self._extractor, "version", "0")
                ),
                "ocr_languages": languages,
                "full_reextraction": True,
            },
            sort_keys=True,
        )
        original_path = canonical_original_path(
            self._data_root, user_id, sha256, mime
        )
        version_ids = [
            str(row["id"])
            for row in self._store.fetch_user_rows(
                "SELECT id FROM doc_versions WHERE user_id = ? AND doc_id = ? "
                "ORDER BY rowid",
                (user_id, doc_id),
            )
        ]
        base_ordinal = version_ids.index(base_version_id) + 1
        derived_ordinal = len(version_ids) + 1
        self._store.execute_write(
            user_id,
            [
                (
                    "INSERT INTO doc_versions(id, user_id, doc_id, sha256, mime, "
                    "original_ref, extractor_manifest, status) "
                    "VALUES (?,?,?,?,?,?,?,'pending')",
                    (
                        derived_version_id,
                        user_id,
                        doc_id,
                        sha256,
                        mime,
                        str(original_path.relative_to(Path(self._data_root).resolve())),
                        manifest,
                    ),
                ),
                (
                    "INSERT INTO artifact_dependencies(user_id, child_ref, "
                    "parent_ref, relation) VALUES (?,?,?,'derived_from')",
                    (
                        user_id,
                        f"doc:{doc_id}@{derived_ordinal}",
                        f"doc:{doc_id}@{base_ordinal}",
                    ),
                ),
            ],
        )
        local_job = (
            job if job is not None else ExtractionJob(timeout_s=self.limits.timeout_s)
        )
        self._run_extraction(
            user_id,
            doc_id=doc_id,
            version_id=derived_version_id,
            data=data,
            mime=mime,
            job=local_job,
            extractor=extractor,
            languages=languages,
        )
        return OcrDeriveResult(
            base_version_id=base_version_id,
            derived_version_id=derived_version_id,
            languages=languages,
            total_pages_reextracted=local_job.total_pages,
        )


# ---------------------------------------------------------------------------
# Adaptador Docling real (fronteira de §3/§6.2)
# ---------------------------------------------------------------------------

#: Import preguiçoso: Docling é dependência pesada e o MVP permite rodar sem
#: extrator configurado (versão permanece 'pending', nunca ativa — §12).
_DOCLING_AVAILABLE: bool | None = None


def docling_available() -> bool:
    """Verifica (e memoriza) se o Docling importa neste ambiente."""
    global _DOCLING_AVAILABLE
    if _DOCLING_AVAILABLE is None:
        try:
            import docling  # noqa: F401
            _DOCLING_AVAILABLE = True
        except Exception:  # noqa: BLE001 — qualquer falha de import conta
            _DOCLING_AVAILABLE = False
    return _DOCLING_AVAILABLE


class DoclingExtractor:
    """Adaptador do Docling (mapa §3/§6.2) executando em subprocesso com
    limite de memória e timeout de §3.

    Importante (transparência da entrega): o pipeline de PDF do Docling
    requer download de modelos de layout; este MVP roda o adaptador com
    extratores injetados nos testes de pipeline e NÃO executa o download dos
    modelos nesta task (fora das autorizações de download registradas). A
    identidade do extrator real fica no ``extractor_manifest`` da versão.
    """

    name = "docling"
    version = "2"

    def __init__(
        self,
        *,
        mem_gib: int = SUBPROCESS_MEM_GIB,
        timeout_s: float = TIMEOUT_S,
    ) -> None:
        self.mem_gib = mem_gib
        self.timeout_s = timeout_s

    def extract(
        self,
        data: bytes,
        mime: str,
        *,
        max_pages: int,
        languages: tuple[str, ...] | None = None,
        on_page: Callable[[int], None] | None = None,
        cancelled: Callable[[], bool] = lambda: False,
    ) -> ExtractedDocument:
        if not docling_available():
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                "Docling indisponível neste ambiente — ingestão não pode "
                "fingir extração (mapa §3/§6.2)",
                diagnostic=DIAGNOSTIC,
            )
        # O corpo roda em subprocesso com RLIMIT_AS (§3); a função alvo é
        # picklável e recebe os bytes por argumeento.
        payload = run_in_subprocess(
            lambda: _docling_convert(data, mime, max_pages),
            mem_gib=self.mem_gib,
            timeout_s=self.timeout_s,
        )
        extracted = _extracted_from_docling_payload(payload, languages=languages)
        for record in extracted.pages:
            if cancelled():
                break
            if on_page is not None:
                on_page(record.page)
        return extracted


def _docling_convert(data: bytes, mime: str, max_pages: int) -> dict[str, Any]:
    """Corpo de conversão Docling (roda no subprocesso; picklável).

    Usa a API pública do Docling: ``DocumentConverter.convert`` e
    ``document.iterate_items()`` — itens textuais com ``item.text`` e
    proveniência ``item.prov`` (página física e bbox). Tabelas são
    exportadas em texto legível quando possível; itens sem texto legível
    chegam como pendência (``legible=false``, §6.2).
    """
    from io import BytesIO

    from docling_core.types.doc import TextItem

    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(BytesIO(data))
    document = result.document

    blocks_by_page: dict[int, list[dict[str, Any]]] = {}
    for item in document.iterate_items():
        prov = item.prov[0] if item.prov else None
        page = int(prov.page) if prov is not None else 1
        if page > max_pages:
            continue
        text = ""
        legible = True
        kind = str(getattr(item, "type", "paragraph"))
        if isinstance(item, TextItem):
            text = item.text
        elif hasattr(item, "export_to_markdown"):
            try:
                text = item.export_to_markdown()  # tabelas legíveis (§6.2)
            except Exception:  # noqa: BLE001 — tabela não legível fica pendente
                legible = False
        else:
            legible = False
        bbox = None
        if prov is not None and getattr(prov, "bbox", None) is not None:
            raw = prov.bbox
            bbox = (
                float(raw.l),
                float(raw.t),
                float(raw.r),
                float(raw.b),
            )
        blocks_by_page.setdefault(page, []).append(
            {
                "kind": "table" if "table" in kind else kind,
                "text": text,
                "bbox": bbox,
                "legible": legible,
                "ocr_source": None,  # texto nativo do Docling (não sidecar)
            }
        )

    return {
        "pages": [
            {"page": page, "blocks": blocks}
            for page, blocks in sorted(blocks_by_page.items())
        ]
    }


def _extracted_from_docling_payload(
    payload: dict[str, Any], *, languages: tuple[str, ...] | None = None
) -> ExtractedDocument:
    """Monta ``ExtractedDocument`` a partir do payload do Docling."""
    extracted = ExtractedDocument()
    for page_payload in payload.get("pages", []):
        blocks = [
            BlockRecord(
                page=int(page_payload["page"]),
                kind=str(block.get("kind", "paragraph")),
                text=str(block.get("text", "")),
                order_in_page=order,
                bbox=block.get("bbox"),
                legible=bool(block.get("legible", True)),
                ocr_source=block.get("ocr_source"),
            )
            for order, block in enumerate(page_payload.get("blocks", []))
        ]
        extracted.pages.append(PageRecord(page=int(page_payload["page"]), blocks=blocks))
    extracted.diagnose_pages()
    return extracted


__all__ = [
    "DIAGNOSTIC",
    "MAX_PAGES",
    "MAX_SIZE_BYTES",
    "OCR_LANGUAGES",
    "SUBPROCESS_MEM_GIB",
    "TIMEOUT_S",
    "BlockRecord",
    "BlockExtractor",
    "DoclingExtractor",
    "ExtractionJob",
    "ExtractedDocument",
    "IngestResult",
    "IngestionLimits",
    "IngestionService",
    "OcrDeriveResult",
    "PageRecord",
    "canonical_original_path",
    "docling_available",
    "run_in_subprocess",
    "sniff_mime",
]
