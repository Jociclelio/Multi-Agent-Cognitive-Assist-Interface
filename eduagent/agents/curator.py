"""Agente Curador: ingestão, extração de tópicos/fatos candidatos, OCR
seletivo e confirmação pelo usuário (mapa normativo
``fase2/documentos/04_mapa_completo_do_sistema.md``, §6 itens 1–3; task 006).

Contratos implementados (§6.3, complementando a ingestão de §6.1–2 em
``eduagent/services/ingestion.py``):

- **Ferramenta ``document.extract``** (tabela §10): só o papel Curador pode
  propor — a permissão é validada por ``validate_tool_request`` (task 003) e
  JSON correto para ação proibida é negado por código (``TOOL_DENIED``).
- **Extração determinística de tópicos e fatos candidatos por schema**
  (§6.3): tópicos vêm de blocos de título; fatos (datas/números) vêm do texto
  dos blocos legíveis e são validados contra o contrato ``AcademicFact`` da
  task 003 — candidato/ambíguo/rejeitado/confirmado nunca sai do enum e
  ``confirmed`` exige autoridade do usuário (o validador do contrato recusa
  o resto).
- **Validação de datas/números com texto de origem** (§6.3): a expressão
  original precisa existir no texto do bloco de origem e o valor normalizado
  precisa ser derivável dela; divergência vira ``ambiguous``, nunca fato
  inventado (§12: nenhuma saída parcial silenciosamente aprovada).
- **Datas relativas** (§6.3): usam a **data da fala** (``spoken_at``) e a
  **zona confirmada** do usuário; sem zona confirmada é erro tipado
  ``AMBIGUOUS_INPUT`` (mapa §3: ``America/Sao_Paulo`` só após confirmação).
- **Prazo só de dia** (§6.3/§4): fatos de data têm ``kind=date``,
  ``precision=day`` e ``timezone=None`` — horário nunca é inventado (o
  contrato rejeita timezone em fato de data).
- **PDD confirmado** (§6.3): fato já confirmado tem prioridade; uma revisão
  (novo fato de mesma entidade com valor diferente) **não** sobrescreve —
  gera conflito a reconciliar: o novo fica ``ambiguous`` e o par é devolvido
  pendente (§7: contradição devolve ambos os registros). A identidade da
  entidade é estável por documento + âncora de conteúdo (expressão original),
  não pela versão — a revisão real do mesmo fato numa versão nova do mesmo
  documento confronta o PDD confirmado (correção da 006a); reconciliação
  entre documentos distintos fica para a memória (§7), limite declarado.
- **Ciclos de pré-requisito** (§6.3/§9): arestas de pré-requisito são
  verificadas por detecção de ciclo **antes** de qualquer escrita —
  dependência cíclica é erro tipado, não inviabilidade misteriosa (§9).
- **Confirmação do usuário** (§6.3): o usuário confirma ou corrige a tabela
  extraída; ``confirmed`` exige confirmação explícita (registrada em
  ``confirmations`` do DDL §5, com digest do fato e revisões de §15.1) ou
  entrada direta inequívoca (``authority=user_direct``).

A extração aqui é determinística (texto local); no sistema completo ela é
feita por LLM com schema — a fronteira de validação é esta mesma.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone as _tz
from typing import Any
from zoneinfo import ZoneInfo

from eduagent.contracts import (
    AcademicFact,
    ErrorCode,
    EduAgentError,
    SenderRole,
    SourceRef,
    ToolName,
    validate_tool_request,
)
from eduagent.services.ingestion import IngestionService
from eduagent.storage.repository import DomainStore

#: Referência de diagnóstico local do agente (mapa §4).
DIAGNOSTIC = "eduagent/agents/curator.py"

#: Namespace determinístico para entity_id de fatos extraídos (UUID v5).
_FACT_NAMESPACE = _uuid.UUID("6f1f0e2a-0c1e-4d9a-9b1f-0a2b3c4d5e6f")

#: Expressões de data aceitas na extração determinística (§6.3).
_DATE_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
_DATE_SLASH_FULL = re.compile(r"\d{2}/\d{2}/\d{4}")
_DATE_SLASH_SHORT = re.compile(r"(?<!\d)\d{2}/\d{2}(?![/\d])")
#: Números: inteiro/decimal opcionalmente com % — o token é a expressão
#: original validada contra o texto de origem.
_NUMBER = re.compile(r"(?<![\w.])(\d{1,9}(?:[.,]\d+)?%?)(?![\w.])")

#: Expressões relativas suportadas na política de datas (§6.3) — default de
#: ensaio; novas formas exigem revisão da política, não improvização.
_RELATIVE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^\s*hoje\s*$", re.IGNORECASE), "today"),
    (re.compile(r"^\s*amanh[aã]\s*$", re.IGNORECASE), "tomorrow"),
    (re.compile(r"^\s*depois\s+de\s+amanh[aã]\s*$", re.IGNORECASE), "after_tomorrow"),
    (re.compile(r"^\s*(?:em|daqui\s+a)\s+(\d{1,3})\s+dias?\s*$", re.IGNORECASE), "in_days"),
]


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    )


# ---------------------------------------------------------------------------
# Candidatos e resultado de extração
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TopicCandidate:
    """Tópico candidato extraído de bloco de título (§6.3)."""

    title: str
    source_block_id: str
    source_page: int


@dataclass
class FactCandidate:
    """Fato candidato com resultado de validação contra a origem (§6.3).

    Mutável por necessidade do §6.3: a reconciliação com PDD confirmado
    pode rebaixar o status para ``ambiguous`` antes da persistência.
    """

    fact: AcademicFact
    validation: str  # 'ok' | 'expression_not_in_source' | 'value_mismatch' | ...
    block_key: tuple[int, int] | None  # (page, order_index) do bloco de origem


@dataclass
class FactConflict:
    """Conflito de revisão de PDD (§6.3): fator confirmado tem prioridade; o
    par fica pendente de reconciliação — nunca sobrescrita silenciosa."""

    entity_id: str
    kind: str
    existing_fact_id: str
    existing_value: str
    incoming_fact_id: str
    incoming_value: str
    pending: bool = True


@dataclass
class CuratorExtraction:
    """Resultado da curadoria de um documento (§6.3)."""

    doc_id: str
    version_id: str
    topics: list[TopicCandidate] = field(default_factory=list)
    facts: list[FactCandidate] = field(default_factory=list)
    pending_items: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[FactConflict] = field(default_factory=list)
    persisted_fact_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validação contra origem (§6.3)
# ---------------------------------------------------------------------------


def validate_against_source(expression: str, source_text: str) -> str:
    """Verifica que a expressão original existe no texto de origem (§6.3).

    Retorna ``'ok'`` ou ``'expression_not_in_source'`` — chamador decide o
    status (candidato só com ``ok``).
    """
    if expression and expression in source_text:
        return "ok"
    return "expression_not_in_source"


def validate_number(expression: str, normalized_value: str) -> str:
    """Verifica que o valor normalizado é derivável da expressão (§6.3).

    Para números: o valor normalizado precisa ser numericamente igual ao
    número presente na expressão (``30%`` → ``30``; ``7,5`` → ``7.5``).
    """
    match = _NUMBER.search(expression)
    if match is None:
        return "no_number_in_expression"
    raw = match.group(1).rstrip("%").replace(",", ".")
    try:
        parsed = float(raw)
    except ValueError:
        return "value_mismatch"
    try:
        claimed = float(normalized_value.rstrip("%"))
    except ValueError:
        return "value_mismatch"
    return "ok" if abs(parsed - claimed) < 1e-9 else "value_mismatch"


def validate_date(expression: str, normalized_value: str) -> str:
    """Verifica que a data normalizada é derivável da expressão (§6.3)."""
    iso = _DATE_ISO.fullmatch(expression)
    if iso is not None:
        return "ok" if normalized_value == expression else "value_mismatch"
    full = _DATE_SLASH_FULL.fullmatch(expression)
    if full is not None:
        day, month, year = expression.split("/")
        return "ok" if normalized_value == f"{year}-{month}-{day}" else "value_mismatch"
    short = _DATE_SLASH_SHORT.fullmatch(expression)
    if short is not None:
        # Dia/mês sem ano: o par é derivável da origem, mas a data está
        # incompleta — não ganha ano inventado; status sai ambiguous.
        day, month = expression.split("/")
        if normalized_value == f"--{month}-{day}":
            return "year_missing"
        return "value_mismatch"
    return "expression_not_a_date"


# ---------------------------------------------------------------------------
# Datas relativas (§6.3: data da fala + zona confirmada)
# ---------------------------------------------------------------------------


def resolve_relative_date(
    expression: str,
    spoken_at_utc: datetime,
    confirmed_timezone: str | None,
) -> date:
    """Resolve data relativa usando a **data da fala** e a **zona
    confirmada** (§6.3).

    - ``confirmed_timezone is None`` → erro tipado ``AMBIGUOUS_INPUT``
      (mapa §3: timezone default só após confirmação explícita);
    - ``spoken_at_utc`` deve ser aware (contrato §4); é convertido para a
      zona confirmada antes de extrair a data da fala;
    - o resultado é **data** (dia) — horário nunca é inventado (§6.3).
    """
    if confirmed_timezone is None:
        raise EduAgentError(
            ErrorCode.AMBIGUOUS_INPUT,
            "data relativa exige zona confirmada do usuário (mapa §3/§6.3)",
            diagnostic=DIAGNOSTIC,
        )
    if spoken_at_utc.tzinfo is None or spoken_at_utc.utcoffset() is None:
        raise EduAgentError(
            ErrorCode.AMBIGUOUS_INPUT,
            "data da fala deve ser aware (mapa §4)",
            diagnostic=DIAGNOSTIC,
        )
    normalized = _strip_accents(expression).strip().lower()
    spoken_local = spoken_at_utc.astimezone(ZoneInfo(confirmed_timezone))
    spoken_date = spoken_local.date()
    for pattern, rule in _RELATIVE_PATTERNS:
        match = pattern.match(normalized)
        if match is None:
            continue
        if rule == "today":
            return spoken_date
        if rule == "tomorrow":
            return spoken_date + timedelta(days=1)
        if rule == "after_tomorrow":
            return spoken_date + timedelta(days=2)
        if rule == "in_days":
            return spoken_date + timedelta(days=int(match.group(1)))
    raise EduAgentError(
        ErrorCode.AMBIGUOUS_INPUT,
        f"expressão relativa {expression!r} fora da política de datas (§6.3)",
        diagnostic=DIAGNOSTIC,
    )


# ---------------------------------------------------------------------------
# Ciclos de pré-requisito (§6.3/§9)
# ---------------------------------------------------------------------------


def detect_prerequisite_cycles(
    edges: list[tuple[str, str]],
) -> list[list[str]]:
    """Detecta ciclos em arestas de pré-requisito ``(pré-requisito, tópico)``
    (§6.3; §9: "Dependência cíclica é erro, não inviabilidade misteriosa").

    Retorna a lista de ciclos (vazia = sem ciclo). Um ciclo fechado é erro
    de domínio: o chamador deve recusar a escrita antes de qualquer efeito.
    """
    adjacency: dict[str, list[str]] = {}
    for parent, child in edges:
        adjacency.setdefault(parent, []).append(child)

    cycles: list[list[str]] = []
    state: dict[str, int] = {}  # 0 = novo, 1 = em pilha, 2 = fechado
    stack: list[str] = []

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for child in adjacency.get(node, []):
            status = state.get(child, 0)
            if status == 0:
                visit(child)
            elif status == 1:
                cycle = stack[stack.index(child):]
                cycles.append(cycle + [child])
        stack.pop()
        state[node] = 2

    for node in list(adjacency):
        if state.get(node, 0) == 0:
            visit(node)
    return cycles


# ---------------------------------------------------------------------------
# Agente Curador
# ---------------------------------------------------------------------------


class CuratorAgent:
    """Agente Curador do MVP (mapa §6): ingestão via ``document.extract``,
    extração de tópicos/fatos candidatos e confirmação pelo usuário."""

    def __init__(
        self,
        store: DomainStore,
        ingestion: IngestionService | None = None,
    ) -> None:
        self._store = store
        self._ingestion = ingestion

    # -- §10: ferramenta document.extract (proposta do Curador) --------------

    def request_document_extract(self, sender_role: SenderRole, **kwargs: Any) -> Any:
        """Propõe ``document.extract`` (tabela §10). Papel é atribuído pelo
        dispatcher; proposta de outro papel é negada por código (§10: "JSON
        correto para ação proibida é negado por código")."""
        validate_tool_request(ToolName.DOCUMENT_EXTRACT, sender_role)
        if self._ingestion is None:
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                "serviço de ingestão não configurado no Curador",
                diagnostic=DIAGNOSTIC,
            )
        return self._ingestion.ingest(**kwargs)

    # -- §6.3: extração de tópicos e fatos candidatos --------------------------

    def curate_document(
        self,
        user_id: str,
        doc_id: str,
        version_id: str,
        *,
        persist: bool = True,
    ) -> CuratorExtraction:
        """Extrai tópicos e fatos candidatos por schema (§6.3) dos blocos
        legíveis da versão, valida contra o texto de origem, reconcilia com
        fatos confirmados (PDD, §6.3) e persiste candidatos/ambíguos.

        Equações/tabelas não legíveis **não** geram fato — ficam pendentes
        (§6.2), reportadas em ``pending_items``.
        """
        rows = self._store.fetch_user_rows(
            "SELECT page, order_index, block_id, kind, text, diagnosis_json "
            "FROM blocks WHERE user_id = ? AND version_id = ? "
            "ORDER BY page, order_index",
            (user_id, version_id),
        )
        if not rows:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                "versão sem blocos indexados — extração exige versão completa "
                "(mapa §6.1/§6.3)",
                diagnostic=DIAGNOSTIC,
            )
        extraction = CuratorExtraction(doc_id=doc_id, version_id=version_id)
        extraction.pending_items = self._pending_items(rows)

        for row in rows:
            if str(row["kind"]) == "heading" and str(row["text"]).strip():
                extraction.topics.append(
                    TopicCandidate(
                        title=str(row["text"]).strip(),
                        source_block_id=str(row["block_id"])
                        if row["block_id"]
                        else self._block_id(int(row["page"]), int(row["order_index"])),
                        source_page=int(row["page"]),
                    )
                )
                continue
            if not self._block_is_textual(row):
                continue  # tabelas/equações não legíveis ficam pendentes (§6.2)
            source_text = str(row["text"])
            for expression, kind, precision, normalized, validation in (
                self._date_candidates(source_text)
                + self._number_candidates(self._mask_dates(source_text))
            ):
                source_refs = self._source_refs_for_block(
                    user_id, doc_id=doc_id, version_id=version_id, row=row
                )
                fact = AcademicFact(
                    # Identidade estável da entidade por documento + âncora de
                    # conteúdo (expressão original) — NÃO pela versão (correção
                    # da 006a, §6.3): a revisão real do mesmo fato numa versão
                    # nova do mesmo documento confronta o PDD confirmado.
                    # Reconciliação entre documentos distintos fica para a
                    # memória (§7) — limite declarado, coberto por teste.
                    entity_id=_uuid.uuid5(_FACT_NAMESPACE, f"{doc_id}:{expression}"),
                    kind=kind,
                    original_expression=expression,
                    normalized_value=normalized,
                    precision=precision,
                    timezone=None,  # fato de data nunca carrega zona (§4/§6.3)
                    source_refs=source_refs,
                    status=AcademicFact.FactStatus.CANDIDATE
                    if validation == "ok"
                    else AcademicFact.FactStatus.AMBIGUOUS,
                    authority=AcademicFact.FactAuthority.DOCUMENT,
                )
                extraction.facts.append(
                    FactCandidate(
                        fact=fact,
                        validation=validation,
                        block_key=(int(row["page"]), int(row["order_index"])),
                    )
                )

        # PDD confirmado tem prioridade (§6.3): revisão de fato confirmado
        # com valor diferente gera conflito a reconciliar — novo fica
        # ambiguous e o par é reportado pendente.
        conflicts = self._reconcile_with_confirmed(user_id, extraction)
        extraction.conflicts = conflicts

        if persist:
            extraction.persisted_fact_ids = self.persist_fact_candidates(
                user_id, extraction
            )
        return extraction

    @staticmethod
    def _block_is_textual(row: Any) -> bool:
        """Bloco textual legível: base de fatos. Tabela/equação não legível
        fica pendente (§6.2) e nunca vira fato."""
        diagnosis = row["diagnosis_json"]
        if diagnosis:
            payload = json.loads(str(diagnosis))
            if payload.get("legible") is False:
                return False
        return bool(str(row["text"]).strip())

    @staticmethod
    def _pending_items(rows: list[Any]) -> list[dict[str, Any]]:
        pending: list[dict[str, Any]] = []
        for row in rows:
            diagnosis = row["diagnosis_json"]
            if diagnosis:
                payload = json.loads(str(diagnosis))
                if payload.get("legible") is False:
                    pending.append(
                        {
                            "page": int(row["page"]),
                            "kind": str(row["kind"]),
                            "reason": "not_legible",
                        }
                    )
        return pending

    @staticmethod
    def _date_candidates(source_text: str) -> list[tuple[str, AcademicFact.FactKind, AcademicFact.Precision, str, str]]:
        """Candidatos de data do texto (§6.3), todos validados contra a
        origem: ISO e DD/MM/YYYY viram data completa (``precision=day``);
        DD/MM sem ano não ganha ano inventado — ``ambiguous``."""
        candidates: list[
            tuple[str, AcademicFact.FactKind, AcademicFact.Precision, str, str]
        ] = []
        for expression in _DATE_ISO.findall(source_text):
            try:
                date.fromisoformat(expression)
            except ValueError:
                candidates.append(
                    (
                        expression,
                        AcademicFact.FactKind.DATE,
                        AcademicFact.Precision.DAY,
                        expression,
                        "value_mismatch",
                    )
                )
                continue
            candidates.append(
                (
                    expression,
                    AcademicFact.FactKind.DATE,
                    AcademicFact.Precision.DAY,
                    expression,
                    validate_date(expression, expression),
                )
            )
        for expression in _DATE_SLASH_FULL.findall(source_text):
            day, month, year = expression.split("/")
            try:
                date(int(year), int(month), int(day))
            except ValueError:
                candidates.append(
                    (
                        expression,
                        AcademicFact.FactKind.DATE,
                        AcademicFact.Precision.DAY,
                        expression,
                        "value_mismatch",
                    )
                )
                continue
            normalized = f"{year}-{month}-{day}"
            candidates.append(
                (
                    expression,
                    AcademicFact.FactKind.DATE,
                    AcademicFact.Precision.DAY,
                    normalized,
                    validate_date(expression, normalized),
                )
            )
        for expression in _DATE_SLASH_SHORT.findall(source_text):
            day, month = expression.split("/")
            # Sem ano: não há data normalizada — valor carrega o par e o
            # status sai ambiguous pela validação (§6.3: validar com origem).
            normalized = f"--{month}-{day}"
            candidates.append(
                (
                    expression,
                    AcademicFact.FactKind.DATE,
                    AcademicFact.Precision.DAY,
                    normalized,
                    validate_date(expression, normalized),
                )
            )
        return candidates

    @staticmethod
    def _mask_dates(source_text: str) -> str:
        """Remove trechos de data do texto antes da extração numérica — um
        número dentro de ``12/05/2026`` não é fato numérico (§6.3)."""
        masked = _DATE_ISO.sub(" ", source_text)
        masked = _DATE_SLASH_FULL.sub(" ", masked)
        masked = _DATE_SLASH_SHORT.sub(" ", masked)
        return masked

    @staticmethod
    def _number_candidates(source_text: str) -> list[tuple[str, AcademicFact.FactKind, AcademicFact.Precision, str, str]]:
        """Candidatos numéricos do texto (§6.3) validados contra a origem:
        o normalizado é derivado do token encontrado — divergência não ocorre
        por construção aqui, mas a validação é aplicada de qualquer forma."""
        candidates: list[
            tuple[str, AcademicFact.FactKind, AcademicFact.Precision, str, str]
        ] = []
        for match in _NUMBER.finditer(source_text):
            expression = match.group(1)
            raw = expression.rstrip("%").replace(",", ".")
            normalized = str(float(raw)) if "." in raw or "," in expression else str(int(raw))
            candidates.append(
                (
                    expression,
                    AcademicFact.FactKind.NUMBER,
                    AcademicFact.Precision.EXACT,
                    normalized,
                    validate_number(expression, normalized),
                )
            )
        return candidates

    def _source_refs_for_block(
        self,
        user_id: str,
        *,
        doc_id: str,
        version_id: str,
        row: Any,
    ) -> list[SourceRef]:
        """Proveniência do fato: ``SourceRef`` do bloco de origem (§4/§6.2)."""
        page = int(row["page"])
        order = int(row["order_index"])
        text = str(row["text"])
        persisted = row["block_id"]
        return [
            SourceRef(
                doc_id=_uuid.UUID(doc_id),
                version_id=_uuid.UUID(version_id),
                physical_page=page,
                block_id=(
                    str(persisted)
                    if persisted
                    else self._block_id(page, order)
                ),
                offsets=None,
                bbox=None,
                text_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            )
        ]

    @staticmethod
    def _block_id(page: int, order_index: int) -> str:
        """Fallback determinístico (mesma fórmula de
        ``ingestion._deterministic_block_id``): o valor canônico é a coluna
        persistida ``blocks.block_id`` (correção da 006a, §6.7)."""
        return f"p{page}b{order_index % 10_000 + 1}"[:64]

    # -- PDD confirmado: prioridade e conflito (§6.3) ---------------------------

    def _reconcile_with_confirmed(
        self, user_id: str, extraction: CuratorExtraction
    ) -> list[FactConflict]:
        """Fato confirmado existente (mesma entidade) tem prioridade (§6.3):
        candidato com valor diferente vira ``ambiguous`` e o par é reportado;
        valor igual segue candidato."""
        conflicts: list[FactConflict] = []
        for candidate in extraction.facts:
            fact = candidate.fact
            confirmed = self._store.fetch_user_rows(
                "SELECT id, value_json, status FROM facts WHERE user_id = ? "
                "AND status = 'confirmed' AND kind = ?",
                (user_id, fact.kind.value),
            )
            for row in confirmed:
                payload = json.loads(str(row["value_json"]))
                if payload.get("entity_id") != str(fact.entity_id):
                    continue
                if payload.get("normalized_value") == fact.normalized_value:
                    continue
                # Revisão de fato confirmado: conflito a reconciliar (§6.3).
                candidate.fact = candidate.fact.model_copy(
                    update={"status": AcademicFact.FactStatus.AMBIGUOUS}
                )
                candidate.validation = "conflicts_with_confirmed_fact"
                conflicts.append(
                    FactConflict(
                        entity_id=str(fact.entity_id),
                        kind=fact.kind.value,
                        existing_fact_id=str(row["id"]),
                        existing_value=str(payload.get("normalized_value")),
                        incoming_fact_id=str(fact.entity_id),
                        incoming_value=fact.normalized_value,
                        pending=True,
                    )
                )
                break
        return conflicts

    # -- Persistência de fatos candidatos (DDL §5 facts) -------------------------

    def persist_fact_candidates(
        self, user_id: str, extraction: CuratorExtraction
    ) -> list[str]:
        """Persiste candidatos/ambíguos na tabela ``facts`` (§5) após
        validação pelo contrato ``AcademicFact`` (task 003). Retorna os IDs
        persistidos."""
        statements: list[tuple[str, tuple[Any, ...]]] = []
        persisted: list[str] = []
        recorded_at = datetime.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for candidate in extraction.facts:
            fact = candidate.fact
            value_json = json.dumps(
                {
                    "entity_id": str(fact.entity_id),
                    "original_expression": fact.original_expression,
                    "normalized_value": fact.normalized_value,
                    "precision": fact.precision.value,
                    "timezone": fact.timezone,
                    "validation": candidate.validation,
                },
                sort_keys=True,
            )
            fact_id = str(_uuid.uuid4())
            statements.append(
                (
                    "INSERT INTO facts(id, user_id, kind, value_json, authority, "
                    "valid_from, valid_to, recorded_at, source_refs_json, "
                    "supersedes, status, revision) VALUES (?,?,?,?,?,?,?,?,?,?,?,0)",
                    (
                        fact_id,
                        user_id,
                        fact.kind.value,
                        value_json,
                        fact.authority.value,
                        None,
                        None,
                        recorded_at,
                        json.dumps(
                            [ref.model_dump(mode="json") for ref in fact.source_refs]
                        ),
                        None,
                        fact.status.value,
                    ),
                )
            )
            persisted.append(fact_id)
        if statements:
            self._store.execute_write(user_id, statements)
        return persisted

    # -- Confirmação/correção pelo usuário (§6.3) --------------------------------

    def set_fact_status(
        self,
        user_id: str,
        fact_id: str,
        new_status: str,
        *,
        expected_revision: int | None = None,
        user_confirms: bool = False,
        direct_value: str | None = None,
    ) -> dict[str, Any]:
        """Usuário confirma ou corrige a tabela extraída (§6.3).

        - ``confirmed`` exige ``user_confirms=True`` (confirmação explícita,
          registrada em ``confirmations`` — DDL §5/§15.1) ou
          ``direct_value`` (entrada direta inequívoca, ``authority=
          user_direct``); sem uma das duas é recusa tipada — o contrato
          ``AcademicFact`` da 003 recusa confirmado sem autoridade do usuário.
        - ``rejected``/``ambiguous``/``candidate`` são transições simples
          com revisão validada (§5: todo estado mutável valida revisão).
        - Correção com ``direct_value`` atualiza o valor normalizado e
          registra a origem da entrada.
        """
        if new_status not in ("candidate", "ambiguous", "confirmed", "rejected"):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"status {new_status!r} fora do enum do §4 (AcademicFact)",
                diagnostic=DIAGNOSTIC,
            )
        rows = self._store.fetch_user_rows(
            "SELECT id, kind, value_json, authority, revision, status FROM "
            "facts WHERE id = ? AND user_id = ?",
            (fact_id, user_id),
        )
        if not rows:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"fato {fact_id} inexistente para o usuário",
                diagnostic=DIAGNOSTIC,
            )
        row = rows[0]
        revision = int(row["revision"])
        if expected_revision is not None and expected_revision != revision:
            raise EduAgentError(
                ErrorCode.VERSION_CONFLICT,
                f"revisão esperada {expected_revision} difere da atual "
                f"{revision} (mapa §5)",
                diagnostic=DIAGNOSTIC,
            )
        payload = json.loads(str(row["value_json"]))

        authority = str(row["authority"])
        if direct_value is not None:
            payload["normalized_value"] = direct_value
            payload["corrected_by"] = "user_direct"
            authority = AcademicFact.FactAuthority.USER_DIRECT.value
        if new_status == "confirmed":
            if direct_value is None and not user_confirms:
                raise EduAgentError(
                    ErrorCode.SCHEMA_INVALID,
                    "fato 'confirmed' exige confirmação explícita ou entrada "
                    "direta inequívoca do usuário (mapa §4/§6.3)",
                    diagnostic=DIAGNOSTIC,
                )
            if authority not in (
                AcademicFact.FactAuthority.USER_DIRECT.value,
                AcademicFact.FactAuthority.USER_CONFIRMED.value,
            ):
                authority = AcademicFact.FactAuthority.USER_CONFIRMED.value
            # Contrato da 003 como barreira final: confirmado sem autoridade
            # de usuário é impossível.
            AcademicFact(
                entity_id=_uuid.UUID(payload["entity_id"]),
                kind=AcademicFact.FactKind(str(row["kind"])),
                original_expression=payload["original_expression"],
                normalized_value=payload["normalized_value"],
                precision=AcademicFact.Precision(payload["precision"]),
                timezone=payload.get("timezone"),
                source_refs=[],
                status=AcademicFact.FactStatus.CONFIRMED,
                authority=AcademicFact.FactAuthority(authority),
            )

        digest = hashlib.sha256(
            json.dumps(
                {"fact_id": fact_id, "status": new_status, "value": payload},
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        confirmation_id = str(_uuid.uuid4())
        occurred_at = datetime.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._store.write_transaction(user_id) as tx:
            # base_revision é a revisão pré-commit lida dentro da transação;
            # approval_revision é a revisão pós-commit (bump único do §15.1
            # acontece no COMMIT desta transação).
            base_revision = self._store.domain_revision(user_id)
            tx.execute(
                "UPDATE facts SET status = ?, authority = ?, value_json = ?, "
                "revision = revision + 1 WHERE id = ? AND user_id = ?",
                (new_status, authority, json.dumps(payload, sort_keys=True), fact_id, user_id),
            )
            if new_status == "confirmed":
                tx.execute(
                    "INSERT INTO confirmations(id, user_id, artifact_id, "
                    "artifact_revision, digest, occurred_at, base_revision, "
                    "approval_revision) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        confirmation_id,
                        user_id,
                        fact_id,
                        revision + 1,
                        digest,
                        occurred_at,
                        base_revision,
                        base_revision + 1,
                    ),
                )
        return {
            "fact_id": fact_id,
            "status": new_status,
            "authority": authority,
            "confirmation_id": confirmation_id if new_status == "confirmed" else None,
            "revision": revision + 1,
        }

    def confirmation_record(self, user_id: str, confirmation_id: str) -> dict[str, Any] | None:
        """Leitura do registro de confirmação (§5 ``confirmations``)."""
        rows = self._store.fetch_user_rows(
            "SELECT id, artifact_id, artifact_revision, digest, occurred_at, "
            "base_revision, approval_revision FROM confirmations WHERE id = ? "
            "AND user_id = ?",
            (confirmation_id, user_id),
        )
        return dict(rows[0]) if rows else None

    # -- Fato relativo com data da fala + zona confirmada (§6.3) ------------------

    def resolve_fact_deadline(
        self,
        user_id: str,
        *,
        expression: str,
        spoken_at_utc: datetime,
        source_text: str | None = None,
    ) -> FactCandidate:
        """Resolve prazo relativo (§6.3): data da fala + zona confirmada do
        usuário; resultado é data pura (dia), sem horário inventado.

        Se ``source_text`` for dado, a expressão é validada contra ele
        (§6.3: validar datas com texto de origem).
        """
        rows = self._store.fetch_user_rows(
            "SELECT timezone FROM users WHERE id = ?", (user_id,)
        )
        if not rows:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"usuário {user_id} não existe no domínio",
                diagnostic=DIAGNOSTIC,
            )
        confirmed_tz: str | None = rows[0]["timezone"]
        resolved = resolve_relative_date(expression, spoken_at_utc, confirmed_tz)
        validation = (
            validate_against_source(expression, source_text)
            if source_text is not None
            else "ok"
        )
        fact = AcademicFact(
            entity_id=_uuid.uuid5(_FACT_NAMESPACE, f"{user_id}:{expression}"),
            kind=AcademicFact.FactKind.DATE,
            original_expression=expression,
            normalized_value=resolved.isoformat(),
            precision=AcademicFact.Precision.DAY,
            timezone=None,  # data pura não carrega zona (§4/§6.3)
            source_refs=[],
            status=AcademicFact.FactStatus.CANDIDATE
            if validation == "ok"
            else AcademicFact.FactStatus.AMBIGUOUS,
            authority=AcademicFact.FactAuthority.DOCUMENT,
        )
        return FactCandidate(fact=fact, validation=validation, block_key=None)

    # -- Tópicos e pré-requisitos (§6.3/§9) ----------------------------------------

    def register_topics(
        self,
        user_id: str,
        course_id: str,
        titles: list[str],
        prerequisite_edges: list[tuple[str, str]] | None = None,
    ) -> list[str]:
        """Registra tópicos extraídos e arestas de pré-requisito (§6.3).

        Ciclo de pré-requisito é **erro antes de qualquer escrita** (§9) —
        nada é gravado quando há ciclo. A detecção inclui as arestas
        **persistidas de chamadas anteriores** do curso além das arestas da
        chamada (correção da 006a): um ciclo fechado entre chamadas não é
        persistido. Arestas referem tópicos já registrados (títulos como IDs
        lógicos aqui; o DDL do §5 usa UUIDs, então o chamador mapeia
        título→ID).
        """
        courses = self._store.fetch_user_rows(
            "SELECT id FROM courses WHERE id = ? AND user_id = ?",
            (course_id, user_id),
        )
        if not courses:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                "disciplina inexistente ou fora do ownership (mapa §15.1)",
                diagnostic=DIAGNOSTIC,
            )
        edges = prerequisite_edges or []
        persisted_edges = [
            (str(row["parent"]), str(row["child"]))
            for row in self._store.fetch_user_rows(
                "SELECT tp.title AS parent, tc.title AS child "
                "FROM topic_edges te "
                "JOIN topics tp ON tp.id = te.parent_id "
                "JOIN topics tc ON tc.id = te.child_id "
                "JOIN courses c ON c.id = tp.course_id "
                "WHERE c.id = ? AND c.user_id = ?",
                (course_id, user_id),
            )
        ]
        cycles = detect_prerequisite_cycles(persisted_edges + edges)
        if cycles:
            raise EduAgentError(
                ErrorCode.AMBIGUOUS_INPUT,
                "ciclo de pré-requisito detectado (mapa §6.3/§9): "
                f"{cycles[0]}",
                diagnostic=DIAGNOSTIC,
            )
        statements: list[tuple[str, tuple[Any, ...]]] = []
        topic_ids: list[str] = []
        for title in titles:
            existing = self._store.fetch_user_rows(
                "SELECT t.id FROM topics t JOIN courses c ON c.id = t.course_id "
                "WHERE t.course_id = ? AND t.title = ? AND c.user_id = ?",
                (course_id, title, user_id),
            )
            if existing:
                topic_ids.append(str(existing[0]["id"]))
                continue
            topic_id = str(_uuid.uuid4())
            topic_ids.append(topic_id)
            statements.append(
                (
                    "INSERT INTO topics(id, course_id, title) VALUES (?,?,?)",
                    (topic_id, course_id, title),
                )
            )
        title_to_id = dict(zip(titles, topic_ids))
        # Arestas podem referir tópicos registrados em chamadas anteriores do
        # mesmo curso (correção da 006a): títulos persistidos também resolvem.
        persisted_titles = {
            str(row["title"]): str(row["id"])
            for row in self._store.fetch_user_rows(
                "SELECT t.id, t.title FROM topics t "
                "JOIN courses c ON c.id = t.course_id "
                "WHERE t.course_id = ? AND c.user_id = ?",
                (course_id, user_id),
            )
        }
        for title, topic_id in persisted_titles.items():
            title_to_id.setdefault(title, topic_id)
        for parent_title, child_title in edges:
            parent_id = title_to_id.get(parent_title)
            child_id = title_to_id.get(child_title)
            if parent_id is None or child_id is None:
                raise EduAgentError(
                    ErrorCode.SOURCE_UNRESOLVED,
                    "aresta de pré-requisito referencia tópico não registrado "
                    "nesta chamada (mapa §6.3)",
                    diagnostic=DIAGNOSTIC,
                )
            # O trigger do DDL (§15.1) recusa aresta entre cursos diferentes.
            statements.append(
                (
                    "INSERT INTO topic_edges(parent_id, child_id) VALUES (?,?)",
                    (parent_id, child_id),
                )
            )
        if statements:
            self._store.execute_write(user_id, statements)
        return topic_ids


__all__ = [
    "CuratorAgent",
    "CuratorExtraction",
    "FactCandidate",
    "FactConflict",
    "TopicCandidate",
    "detect_prerequisite_cycles",
    "resolve_relative_date",
    "validate_against_source",
    "validate_date",
    "validate_number",
]
