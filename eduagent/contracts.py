"""Contratos Pydantic estritos, envelope comum, estado do grafo e erros
tipados (mapa normativo §4: ``fase2/documentos/04_mapa_completo_do_sistema.md``).

Regras contratuais do mapa §4 implementadas aqui:

- ``extra='forbid'`` em todos os modelos (campo desconhecido é rejeitado);
- enums para papéis, tipos de artefato, status e códigos de erro;
- IDs UUID (``uuid.UUID``) e datetimes ISO-8601 **com zona**, normalizados
  para UTC; datetime ingênuo (sem tz) é rejeitado;
- datas parciais têm tipo específico (``date`` / ``PartialDate``) — nunca
  coerção silenciosa para datetime (mapa §6.3: "Prazo só de dia não ganha
  horário automático");
- tamanhos limitados em todo campo textual/lista (limites são defaults de
  ensaio, não resultados medidos);
- campos ``*_ref`` contêm ID + versão (``Ref``), nunca caminho produzido por
  LLM — qualquer string com separador de caminho é rejeitada;
- payload externo não muda papel/permissões: ``sender_role`` é atribuído pelo
  dispatcher e a proposta de ferramenta é validada contra a tabela de papéis
  do mapa §10 (absorve o achado F1 da revisão da task 002);
- exportação dos JSON Schemas como parte do build
  (``python -m eduagent.contracts --export schemas``).

Não há lógica de agentes aqui: este módulo é somente contrato.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid as _uuid
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StringConstraints,
    model_validator,
)

__all__ = [
    # tipos primitivos
    "SHA256Hex",
    "SourceLocator",
    "Ref",
    "UtcDatetime",
    "PartialDate",
    "UUIDField",
    "UUIDList",
    # erros tipados
    "ErrorCode",
    "TypedError",
    "EduAgentError",
    # roles/tools (payload externo não muda papel/permissões — mapa §4/§10)
    "SenderRole",
    "ToolName",
    "TOOL_PERMISSIONS",
    "ToolRequest",
    "validate_tool_request",
    # artefatos (tabela do mapa §4)
    "SourceRef",
    "AcademicFact",
    "EvidencePack",
    "MemoryPack",
    "LearningItem",
    "TutorTurn",
    "Assessment",
    "TopicState",
    "StudyDemand",
    "ScheduleProposal",
    "Operation",
    # envelope e estado do grafo
    "EnvelopeStatus",
    "ArtifactType",
    "Envelope",
    "Intent",
    "GraphStatus",
    "Budgets",
    "GraphState",
    # exportação de schemas (build)
    "ALL_CONTRACT_MODELS",
    "SCHEMA_VERSION",
    "export_schemas",
    "schemas_are_current",
]


# ---------------------------------------------------------------------------
# Base estrita e tipos primitivos
# ---------------------------------------------------------------------------


class _StrictModel(BaseModel):
    """Base comum: campo desconhecido é rejeitado (mapa §4)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


def _to_uuid(value: Any) -> Any:
    """Aceita somente ``uuid.UUID`` ou string canônica; int/bytes são
    rejeitados (IDs UUID, mapa §4)."""
    if isinstance(value, _uuid.UUID) or value is None:
        return value
    if isinstance(value, str):
        return _uuid.UUID(value)
    raise ValueError(f"esperado UUID, obtido {value!r}")


def _to_uuid_list(value: Any) -> Any:
    if isinstance(value, list):
        return [_to_uuid(item) for item in value]
    raise ValueError(f"esperado lista de UUIDs, obtido {value!r}")


#: Campo UUID (aceita forma string canônica; rejeita int/bytes).
UUIDField = Annotated[_uuid.UUID, BeforeValidator(_to_uuid)]

#: Lista de UUIDs.
UUIDList = Annotated[list[_uuid.UUID], BeforeValidator(_to_uuid_list)]

#: Hash SHA-256 em hex minúsculo (originais, ``text_hash``, ``payload_hash``,
#: hashes de configuração — mapa §4/§6/§11).
SHA256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

#: Identificador curto sem separador de caminho (block_id, criterion_id,
#: misconception_code etc.). ``/``, ``\`` e ``..`` são impossíveis por
#: construção do padrão.
_ShortId = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
]

#: Inteiros e booleanos estritos: ``bool`` não vira ``1`` e string numérica
#: não vira inteiro (Pydantic estrito, mapa §4/§14). Datas/datetimes/UUIDs
#: mantêm aceitação explícita de string ISO-8601 canônica via before-validators.
_StrictInt = StrictInt
_StrictBool = StrictBool

#: Limites de tamanho — defaults de ensaio (mapa §1/§3), não resultados medidos.
_MAX_TEXT = 4000
_MAX_MESSAGE = 1000
_MAX_LIST = 64


# ---------------------------------------------------------------------------
# Datetimes com zona e datas parciais (mapa §4)
# ---------------------------------------------------------------------------


def _parse_utc(value: Any) -> Any:
    """Aceita ISO-8601 **com zona** ou ``datetime`` aware; rejeita ingênuo."""
    if isinstance(value, str):
        text = value.strip()
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        value = datetime.fromisoformat(text)  # pode levantar ValueError
    if isinstance(value, datetime):
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError(
                "datetime ingênuo (sem zona) não é aceito; informe offset/UTC"
            )
        return value.astimezone(timezone.utc)
    raise ValueError(
        f"esperado ISO-8601 com zona ou datetime aware, obtido {value!r}"
    )


#: Datetime ISO-8601 com zona, normalizado para UTC (mapa §4/§9).
UtcDatetime = Annotated[datetime, BeforeValidator(_parse_utc)]


def _parse_partial(value: Any) -> Any:
    """Data parcial: ``YYYY-MM-DD`` vira ``date`` (sem horário inventado);
    instantes exigem zona. Nunca coerção de data para datetime (mapa §6.3)."""
    if isinstance(value, str):
        text = value.strip()
        if "T" in text or "t" in text or " " in text:
            return _parse_utc(text)
        if text.endswith("Z"):
            raise ValueError("data parcial não aceita sufixo Z")
        return date.fromisoformat(text)  # só aceita YYYY-MM-DD
    if isinstance(value, datetime):
        return _parse_utc(value)
    if isinstance(value, date):
        return value
    raise ValueError(f"esperado 'YYYY-MM-DD' ou datetime com zona, obtido {value!r}")


#: ``date`` puro (dia sem hora) **ou** ``datetime`` com zona — tipo específico
#: para prazos que podem ser só de dia (mapa §6.3/§9: "Datas sem hora exigem
#: confirmação"; a confirmação é de processo, fora deste contrato).
PartialDate = Annotated[Union[date, datetime], BeforeValidator(_parse_partial)]


# ---------------------------------------------------------------------------
# Refs (ID + versão, nunca caminho) e localizadores de citação
# ---------------------------------------------------------------------------

#: Localizador de citação ``doc:<doc_id>@<versão>:p<página>:b<bloco>``
#: (mapa §4 envelope/§6.7). Padrão fecha caminhos por construção.
SourceLocator = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=160,
        pattern=(
            r"^doc:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
            r"[0-9a-f]{4}-[0-9a-f]{12}@[1-9][0-9]*:p[1-9][0-9]*:b[1-9][0-9]*$"
        ),
    ),
]

#: Prefixos admitidos em ``Ref``; prefixo inventado por LLM é rejeitado.
_REF_KINDS = (
    "artifact",
    "item",
    "plan",
    "fact",
    "answer",
    "rubric",
    "receipt",
    "confirmation",
    "demand",
    "block",
    "attempt",
    "assessment",
    "event",
    "summary",
    "operation",
    "doc",
)
_UUID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


class Ref(_StrictModel):
    """Referência ``ID + versão`` (mapa §4: "campos ``*_ref`` contêm ID+versão,
    não caminho produzido pelo LLM"). Forma string aceita:
    ``<uuid>@<versão>`` ou ``<prefixo>:<uuid>@<versão>``; separadores de
    caminho (``/``, ``\\``, ``..``) não casam com o padrão e são rejeitados.
    """

    kind: Optional[Literal[_REF_KINDS]] = None  # type: ignore[valid-type]
    id: UUIDField
    version: StrictInt = Field(ge=1)

    @model_validator(mode="before")
    @classmethod
    def _parse_ref_string(cls, value: Any) -> Any:
        import re as _re

        if isinstance(value, Ref):
            return value
        if not isinstance(value, str):
            return value
        text = value.strip()
        # Qualquer '/' ou '\\' já é rejeitado pelo regex abaixo; a checagem
        # explícita dá mensagem de erro mais clara para caminho.
        if "/" in text or "\\" in text or ".." in text:
            raise ValueError(
                f"*ref não aceita caminho (recebido {value!r}); use ID+versão"
            )
        pattern = rf"^(?:({'|'.join(_REF_KINDS)}):)?({_UUID_PATTERN})@([1-9][0-9]*)$"
        match = _re.fullmatch(pattern, text)
        if match is None:
            raise ValueError(
                f"*ref inválida (recebido {value!r}); forma esperada "
                "'<uuid>@<versão>' ou '<prefixo>:<uuid>@<versão>'"
            )
        kind, raw_id, version = match.group(1), match.group(2), match.group(3)
        return {"kind": kind, "id": raw_id, "version": int(version)}

    def to_locator(self) -> str:
        prefix = f"{self.kind}:" if self.kind else ""
        return f"{prefix}{self.id}@{self.version}"


# ---------------------------------------------------------------------------
# Erros tipados (mapa §4)
# ---------------------------------------------------------------------------


class ErrorCode(str, Enum):
    """Os 12 códigos de erro do mapa §4."""

    SCHEMA_INVALID = "SCHEMA_INVALID"
    SOURCE_UNRESOLVED = "SOURCE_UNRESOLVED"
    AMBIGUOUS_INPUT = "AMBIGUOUS_INPUT"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    TOOL_DENIED = "TOOL_DENIED"
    MODEL_NOT_ADMITTED = "MODEL_NOT_ADMITTED"
    NO_EVIDENCE = "NO_EVIDENCE"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    TIMEOUT = "TIMEOUT"
    UNKNOWN_EFFECT = "UNKNOWN_EFFECT"
    CANCELLED = "CANCELLED"
    INTERNAL_FAILURE = "INTERNAL_FAILURE"


#: Retentabilidade por código — decisões contratuais do mapa: UNKNOWN_EFFECT
#: "permanece UNKNOWN_EFFECT, sem retry automático" (§11); VERSION_CONFLICT é
#: retentável após reload do snapshot (§15.1); TIMEOUT/RESOURCE_LIMIT são
#: retentáveis como orçamento; falhas determinísticas não são. Onde o mapa
#: não fixa, são defaults de ensaio (documentados, não medidos).
RETRYABILITY: dict[ErrorCode, bool] = {
    ErrorCode.SCHEMA_INVALID: False,
    ErrorCode.SOURCE_UNRESOLVED: False,
    ErrorCode.AMBIGUOUS_INPUT: False,
    ErrorCode.VERSION_CONFLICT: True,
    ErrorCode.TOOL_DENIED: False,
    ErrorCode.MODEL_NOT_ADMITTED: False,
    ErrorCode.NO_EVIDENCE: False,
    ErrorCode.RESOURCE_LIMIT: True,
    ErrorCode.TIMEOUT: True,
    ErrorCode.UNKNOWN_EFFECT: False,
    ErrorCode.CANCELLED: False,
    ErrorCode.INTERNAL_FAILURE: False,
}

#: Referência de diagnóstico local padrão por código (arquivo responsável).
#: Paths de módulos ainda stub apontam para o arquivo planejado da task
#: correspondente (mapa §13); é referência de diagnóstico, não execução.
DEFAULT_DIAGNOSTICS: dict[ErrorCode, str] = {
    ErrorCode.SCHEMA_INVALID: "eduagent/contracts.py",
    ErrorCode.SOURCE_UNRESOLVED: "eduagent/storage/repository.py",
    ErrorCode.AMBIGUOUS_INPUT: "eduagent/graph.py",
    ErrorCode.VERSION_CONFLICT: "eduagent/services/effects.py",
    ErrorCode.TOOL_DENIED: "eduagent/policy.py",
    ErrorCode.MODEL_NOT_ADMITTED: "eduagent/services/model_adapter.py",
    ErrorCode.NO_EVIDENCE: "eduagent/services/retrieval.py",
    ErrorCode.RESOURCE_LIMIT: "eduagent/graph.py",
    ErrorCode.TIMEOUT: "eduagent/graph.py",
    ErrorCode.UNKNOWN_EFFECT: "eduagent/services/effects.py",
    ErrorCode.CANCELLED: "eduagent/graph.py",
    ErrorCode.INTERNAL_FAILURE: "eduagent/graph.py",
}


class TypedError(_StrictModel):
    """Erro tipado do mapa §4: código, mensagem ao usuário, retentabilidade e
    referência de diagnóstico local."""

    code: ErrorCode
    message: Annotated[str, StringConstraints(min_length=1, max_length=_MAX_MESSAGE)]
    retryable: StrictBool
    diagnostic: Annotated[
        str, StringConstraints(min_length=1, max_length=512)
    ] = DEFAULT_DIAGNOSTICS[ErrorCode.INTERNAL_FAILURE]

    @classmethod
    def of(
        cls,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool | None = None,
        diagnostic: str | None = None,
    ) -> "TypedError":
        return cls(
            code=code,
            message=message,
            retryable=RETRYABILITY[code] if retryable is None else retryable,
            diagnostic=(
                DEFAULT_DIAGNOSTICS[code] if diagnostic is None else diagnostic
            ),
        )


class EduAgentError(Exception):
    """Exceção carregando um erro tipado do mapa §4 (código, mensagem ao
    usuário, retentabilidade e diagnóstico local)."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool | None = None,
        diagnostic: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = RETRYABILITY[code] if retryable is None else retryable
        self.diagnostic = (
            DEFAULT_DIAGNOSTICS[code] if diagnostic is None else diagnostic
        )

    @property
    def error(self) -> TypedError:
        return TypedError.of(
            self.code,
            self.message,
            retryable=self.retryable,
            diagnostic=self.diagnostic,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.error.model_dump()


# ---------------------------------------------------------------------------
# Papéis e ferramentas — payload externo não muda papel/permissões
# ---------------------------------------------------------------------------


class SenderRole(str, Enum):
    """Papéis lógicos (mapa §1/§4). O papel é atribuído pelo dispatcher a
    partir do contexto autenticado local — nunca lido do payload."""

    CURATOR = "curator"
    LIBRARIAN = "librarian"
    TUTOR = "tutor"
    MONITOR = "monitor"
    PLANNER = "planner"
    SYSTEM = "system"
    USER = "user"


class ToolName(str, Enum):
    """Ferramentas da tabela do mapa §10."""

    DOCUMENT_EXTRACT = "document.extract"
    DOCUMENT_SEARCH = "document.search"
    MEMORY_QUERY = "memory.query"
    ASSESSMENT_CHECK = "assessment.check"
    SCHEDULE_SOLVE = "schedule.solve"
    CALENDAR_RENDER = "calendar.render"
    WEB_SEARCH = "web.search"
    WEB_FETCH = "web.fetch"
    DOMAIN_COMMIT = "domain.commit"
    CALENDAR_APPLY = "calendar.apply"


#: Quem pode propor cada ferramenta (mapa §10, tabela de ferramentas).
#: ``domain.commit``/``calendar.apply`` são serviços determinísticos (SYSTEM).
TOOL_PERMISSIONS: dict[ToolName, frozenset[SenderRole]] = {
    ToolName.DOCUMENT_EXTRACT: frozenset({SenderRole.CURATOR}),
    ToolName.DOCUMENT_SEARCH: frozenset({SenderRole.CURATOR, SenderRole.TUTOR}),
    ToolName.MEMORY_QUERY: frozenset({SenderRole.LIBRARIAN}),
    ToolName.ASSESSMENT_CHECK: frozenset({SenderRole.MONITOR}),
    ToolName.SCHEDULE_SOLVE: frozenset({SenderRole.PLANNER}),
    ToolName.CALENDAR_RENDER: frozenset({SenderRole.PLANNER}),
    ToolName.WEB_SEARCH: frozenset({SenderRole.CURATOR}),
    ToolName.WEB_FETCH: frozenset({SenderRole.CURATOR}),
    ToolName.DOMAIN_COMMIT: frozenset({SenderRole.SYSTEM}),
    ToolName.CALENDAR_APPLY: frozenset({SenderRole.SYSTEM}),
}


def validate_tool_request(tool: ToolName, sender_role: SenderRole) -> None:
    """Valida a permissão de proposta de ferramenta (mapa §10).

    A permissão é decidida **somente** pelo papel explícito do chamador,
    atribuído pelo dispatcher — o payload (incluindo qualquer campo
    ``sender_role`` vindo de fora) não muda papel/permissões (mapa §4;
    absorve o achado F1 da revisão da task 002). JSON correto para ação
    proibida é negado por código (``TOOL_DENIED``), nunca interpretado.

    Nota de escopo: a garantia definitiva de que o papel alegado no payload
    é descartado na fronteira de entrada é responsabilidade do dispatcher
    (task 014) — este contrato avalia apenas o papel que lhe é passado.
    """
    allowed = TOOL_PERMISSIONS.get(tool)
    if allowed is None:
        raise EduAgentError(
            ErrorCode.TOOL_DENIED,
            f"Ferramenta desconhecida: {tool!r}.",
            diagnostic="eduagent/contracts.py:TOOL_PERMISSIONS",
        )
    if sender_role not in allowed:
        allowed_names = ", ".join(sorted(role.value for role in allowed))
        raise EduAgentError(
            ErrorCode.TOOL_DENIED,
            f"Ferramenta {tool.value} não pode ser proposta pelo papel "
            f"'{sender_role.value}' (permitido: {allowed_names}).",
            diagnostic="eduagent/contracts.py:TOOL_PERMISSIONS",
        )


class ToolRequest(_StrictModel):
    """Proposta de chamada de ferramenta com papel explícito do proponente.

    ``sender_role`` é preenchido pelo dispatcher a partir do contexto
    autenticado local; um payload externo que chegue com ``sender_role``
    diferente não altera a permissão — a validação usa o papel atribuído.
    """

    tool: ToolName
    sender_role: SenderRole
    target_ref: Optional[Ref] = None

    @model_validator(mode="after")
    def _check_permission(self) -> "ToolRequest":
        validate_tool_request(self.tool, self.sender_role)
        return self


# ---------------------------------------------------------------------------
# Artefatos da tabela do mapa §4
# ---------------------------------------------------------------------------


class SourceRef(_StrictModel):
    """``SourceRef`` — origem física resolvível no snapshot (mapa §4/§6.7).
    A resolvibilidade no snapshot é verificada em leitura (task de
    armazenamento); o contrato fixa a forma."""

    doc_id: UUIDField
    version_id: UUIDField
    physical_page: StrictInt = Field(ge=1)
    block_id: _ShortId
    offsets: Optional[tuple[StrictInt, StrictInt]] = None
    bbox: Optional[tuple[float, float, float, float]] = None
    text_hash: SHA256Hex

    @model_validator(mode="after")
    def _check_offsets(self) -> "SourceRef":
        if self.offsets is not None:
            start, end = self.offsets
            if start > end:
                raise ValueError("offsets exigem start <= end")
        if self.bbox is not None and any(v != v for v in self.bbox):  # NaN
            raise ValueError("bbox não aceita NaN")
        return self


class AcademicFact(_StrictModel):
    """``AcademicFact`` — fato acadêmico com proveniência (mapa §4/§6.3)."""

    class FactKind(str, Enum):
        DATE = "date"
        DATETIME = "datetime"
        NUMBER = "number"
        TERM = "term"

    class Precision(str, Enum):
        EXACT = "exact"
        DAY = "day"
        MONTH = "month"
        YEAR = "year"
        APPROX = "approx"

    class FactStatus(str, Enum):
        CANDIDATE = "candidate"
        AMBIGUOUS = "ambiguous"
        CONFIRMED = "confirmed"
        REJECTED = "rejected"

    class FactAuthority(str, Enum):
        DOCUMENT = "document"
        USER_DIRECT = "user_direct"  # entrada direta inequívoca do usuário
        USER_CONFIRMED = "user_confirmed"  # confirmação explícita
        DERIVED = "derived"

    entity_id: UUIDField
    kind: FactKind
    original_expression: Annotated[
        str, StringConstraints(min_length=1, max_length=256)
    ]
    normalized_value: Annotated[
        str, StringConstraints(min_length=1, max_length=256)
    ]
    precision: Precision
    timezone: Optional[
        Annotated[
            str,
            StringConstraints(
                # Limite de tamanho: default de ensaio (nomes IANA conhecidos
                # ficam bem abaixo); não é resultado medido.
                max_length=100,
                pattern=r"^[A-Za-z_]+/[A-Za-z0-9_+-]+(/[A-Za-z0-9_+-]+)?$",
            ),
        ]
    ] = None
    source_refs: list[SourceRef] = Field(
        default_factory=list, max_length=_MAX_LIST
    )
    status: FactStatus
    authority: FactAuthority

    @model_validator(mode="after")
    def _confirmed_requires_user(self) -> "AcademicFact":
        # Mapa §4: "confirmado exige confirmação ou entrada direta inequívoca
        # do usuário".
        if self.status == AcademicFact.FactStatus.CONFIRMED and self.authority not in (
            AcademicFact.FactAuthority.USER_DIRECT,
            AcademicFact.FactAuthority.USER_CONFIRMED,
        ):
            raise ValueError(
                "fato 'confirmed' exige authority user_direct ou user_confirmed"
            )
        if self.kind == AcademicFact.FactKind.DATE and self.timezone is not None:
            raise ValueError("fato de data (sem hora) não carrega timezone")
        return self


class EvidencePack(_StrictModel):
    """``EvidencePack`` — pacote de recuperação com citações resolvíveis
    (mapa §4/§6.7). Invariante de processo: não contém instruções de servidor
    (fonte/tool result é dado rotulado, mapa §10)."""

    class Coverage(str, Enum):
        SUPPORTED = "supported"
        PARTIAL = "partial"
        NONE = "none"

    class Chunk(_StrictModel):
        id: UUIDField
        text: Annotated[
            str, StringConstraints(min_length=1, max_length=_MAX_TEXT)
        ]
        source_ref: SourceRef
        rank: StrictInt = Field(ge=1)

    query: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    topic_ids: UUIDList = Field(default_factory=list, max_length=_MAX_LIST)
    chunks: list[Chunk] = Field(min_length=0, max_length=_MAX_LIST)
    retrieval_config_hash: SHA256Hex
    coverage: Coverage

    @model_validator(mode="after")
    def _unique_ranks(self) -> "EvidencePack":
        ranks = [chunk.rank for chunk in self.chunks]
        if len(set(ranks)) != len(ranks):
            raise ValueError("ranks de chunks devem ser únicos")
        return self


class LearningItem(_StrictModel):
    """``LearningItem`` — item de prática com pergunta e solução separadas
    (mapa §4/§8): a solução vive atrás de ``expected_answer_ref``/``rubric_ref``;
    o contrato carrega o ``prompt`` somente."""

    class ItemKind(str, Enum):
        QUIZ = "quiz"
        FLASHCARD = "flashcard"
        SELF_EXPLANATION = "self_explanation"
        OPEN_RESPONSE = "open_response"

    item_id: UUIDField
    family_id: UUIDField
    version: StrictInt = Field(ge=1)
    topic_ids: UUIDList = Field(min_length=1, max_length=_MAX_LIST)
    prompt: Annotated[str, StringConstraints(min_length=1, max_length=_MAX_TEXT)]
    expected_answer_ref: Ref
    rubric_ref: Ref
    source_refs: list[SourceRef] = Field(min_length=1, max_length=_MAX_LIST)
    kind: ItemKind
    published_at: UtcDatetime


class TutorTurn(_StrictModel):
    """``TutorTurn`` — um turno principal por chamada com terminal de
    invocação explícito (mapa §4/§8)."""

    class TutorState(str, Enum):
        # Mapa §8: explain, attempt, hint, self_explain, transfer, close.
        EXPLAIN = "explain"
        ATTEMPT = "attempt"
        HINT = "hint"
        SELF_EXPLAIN = "self_explain"
        TRANSFER = "transfer"
        CLOSE = "close"

    class Terminal(str, Enum):
        WAITING_STUDENT = "waiting_student"
        COMPLETED = "completed"
        CANCELLED = "cancelled"
        FAILED = "failed"

    skill_id: Annotated[
        str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    ]
    skill_version: StrictInt = Field(ge=1)
    objective: TutorState
    text: Annotated[str, StringConstraints(min_length=1, max_length=_MAX_TEXT)]
    item_ref: Optional[Ref] = None
    hint_level: StrictInt = Field(ge=0, le=3)
    citations: list[SourceLocator] = Field(
        default_factory=list, max_length=_MAX_LIST
    )
    next_state: TutorState
    terminal: Terminal

    @model_validator(mode="after")
    def _hint_invariants(self) -> "TutorTurn":
        # Mapa §8: pistas 1=conceito, 2=próximo passo, 3=exemplo análogo.
        if self.objective == TutorTurn.TutorState.HINT and self.hint_level < 1:
            raise ValueError("turno de hint exige hint_level em 1..3")
        if self.objective != TutorTurn.TutorState.HINT and self.hint_level != 0:
            raise ValueError("hint_level só pode ser >0 em turno de hint")
        return self


class Assessment(_StrictModel):
    """``Assessment`` — avaliação por critérios com spans (mapa §4/§8/§15.2).
    Span existe salvo ``evidence_kind='missing'``; ``missing`` exige span nulo
    e descrição do critério ausente em ``reason`` (§15.2)."""

    class EvidenceKind(str, Enum):
        PRESENT = "present"
        MISSING = "missing"

    class Correctness(str, Enum):
        CORRECT = "correct"
        PARTIAL = "partial"
        INCORRECT = "incorrect"
        UNDECIDABLE = "undecidable"

    class Reliability(str, Enum):
        ACCEPTED = "accepted"
        ABSTAIN = "abstain"

    class CriterionResult(_StrictModel):
        criterion_id: _ShortId
        topic_ids: UUIDList = Field(min_length=1, max_length=_MAX_LIST)
        level: StrictInt = Field(ge=0, le=2)
        evidence_kind: "Assessment.EvidenceKind"
        response_span: Optional[tuple[StrictInt, StrictInt]] = None
        reason: Annotated[
            str, StringConstraints(min_length=1, max_length=_MAX_MESSAGE)
        ]
        misconception_code: Optional[_ShortId] = None

        @model_validator(mode="after")
        def _span_invariants(self) -> "Assessment.CriterionResult":
            # §15.2: evidence_kind=present requer offsets válidos; missing
            # exige span=null. Nunca inventar span para silêncio.
            if self.evidence_kind == Assessment.EvidenceKind.MISSING:
                if self.response_span is not None:
                    raise ValueError(
                        "evidence_kind='missing' exige response_span nulo"
                    )
            else:
                if self.response_span is None:
                    raise ValueError(
                        "evidence_kind='present' exige response_span (offsets)"
                    )
                start, end = self.response_span
                if start < 0 or start > end:
                    raise ValueError("response_span exige 0 <= start <= end")
            return self

    attempt_id: UUIDField
    item_ref: Ref
    assessment_revision: StrictInt = Field(ge=1)
    supersedes: Optional[Ref] = None
    criterion_results: list[CriterionResult] = Field(
        min_length=1, max_length=32
    )
    correctness: Correctness
    help_level: StrictInt = Field(ge=0, le=3)
    revealed: StrictBool
    evidence_ids: UUIDList = Field(default_factory=list, max_length=_MAX_LIST)
    reliability: Reliability
    reason: Annotated[
        str, StringConstraints(min_length=1, max_length=_MAX_MESSAGE)
    ]

    @model_validator(mode="after")
    def _abstain_requires_reason(self) -> "Assessment":
        # Mapa §8: span inventado/item ambíguo/sem fonte → abstinência; a
        # abstinência deve vir com razão explícita.
        if (
            self.reliability == Assessment.Reliability.ABSTAIN
            and not self.reason.strip()
        ):
            raise ValueError("assessment em abstinência exige reason")
        return self


def _parse_date_only(value: Any) -> Any:
    """``review_due`` é data parcial (mapa §15.3): datetime (objeto ou string
    com hora) é rejeitado — nunca coerção silenciosa para datetime."""
    if isinstance(value, datetime):
        raise ValueError(
            "review_due é data (YYYY-MM-DD); datetime não é aceito"
        )
    if isinstance(value, str) and ("T" in value or ":" in value):
        raise ValueError(
            "review_due é data (YYYY-MM-DD); datetime não é aceito"
        )
    return value


class TopicState(_StrictModel):
    """``TopicState`` — estado de competência por tópico (mapa §4/§8).
    ``estimate`` é ``null`` no MVP (mapa §8: BKT é futuro, não inventar
    priors); ``review_due`` é **data** (parcial), nunca datetime."""

    class TopicStatus(str, Enum):
        INSUFFICIENT = "insufficient"
        MIXED = "mixed"
        FAVORABLE = "favorable"

    topic_id: UUIDField  # chave do estado por tópico (DDL topic_states)
    independent_attempt_ids: UUIDList = Field(
        default_factory=list, max_length=256
    )
    assisted_attempt_ids: UUIDList = Field(
        default_factory=list, max_length=256
    )
    error_codes: list[ErrorCode] = Field(
        default_factory=list, max_length=_MAX_LIST
    )
    last_attempt_at: Optional[UtcDatetime] = None
    status: TopicStatus
    estimate: None = None  # MVP (mapa §8): estimate=null
    review_due: Annotated[Optional[date], BeforeValidator(_parse_date_only)] = (
        None
    )
    model_version: _ShortId
    revision: StrictInt = Field(ge=0)


class StudyDemand(_StrictModel):
    """``StudyDemand`` — demanda de estudo (mapa §4/§9/§15.3). ``deadline``
    é ``PartialDate``: prazo só de dia não ganha horário automático (§6.3)."""

    class DemandKind(str, Enum):
        # Catálogo de duração da política v1 (§15.3): practice/review/flashcard.
        PRACTICE = "practice"
        REVIEW = "review"
        FLASHCARD = "flashcard"
        OTHER = "other"

    class DurationStatus(str, Enum):
        CONFIRMED = "confirmed"
        ESTIMATED = "estimated"

    demand_id: UUIDField
    topic_ids: UUIDList = Field(min_length=1, max_length=_MAX_LIST)
    kind: DemandKind
    duration_minutes: StrictInt = Field(gt=0, le=10080)  # limite de ensaio: 1 semana
    earliest: UtcDatetime
    deadline: PartialDate
    mandatory: StrictBool
    dependencies: list[Ref] = Field(default_factory=list, max_length=_MAX_LIST)
    priority_class: StrictInt = Field(ge=1, le=3)
    evidence_ids: UUIDList = Field(default_factory=list, max_length=_MAX_LIST)
    duration_status: DurationStatus

    @model_validator(mode="after")
    def _mandatory_requires_confirmed(self) -> "StudyDemand":
        # Mapa §4: "restrição dura exige confirmação"; §15.3: "rótulo
        # estimated e mandatory=false. Usuário pode editar e confirmar para
        # obrigatória. Não converter percentual de domínio em duração";
        # §8 (replanejamento): "a duração recomendada é explicitamente
        # estimada e confirmada quando virar obrigatória … não converter
        # incerteza em obrigação". Demanda obrigatória só com duração
        # confirmada — estimated não sustenta obrigação.
        if (
            self.mandatory
            and self.duration_status is not StudyDemand.DurationStatus.CONFIRMED
        ):
            raise ValueError(
                "demanda obrigatória (mandatory=true) exige "
                "duration_status='confirmed'"
            )
        return self


class ScheduleProposal(_StrictModel):
    """``ScheduleProposal`` — proposta de grade (mapa §4/§9/§15.5).
    Sem validação do verificador independente não há aprovação: status
    OPTIMAL/FEASIBLE exige ``validation.passed=True``."""

    class SolverStatus(str, Enum):
        OPTIMAL = "OPTIMAL"
        FEASIBLE = "FEASIBLE"
        UNKNOWN = "UNKNOWN"
        INFEASIBLE = "INFEASIBLE"
        MODEL_INVALID = "MODEL_INVALID"

    class PlanBlock(_StrictModel):
        block_id: UUIDField
        demand_id: UUIDField
        start_utc: UtcDatetime
        end_utc: UtcDatetime
        uid: UUIDField  # UID estável por bloco lógico (mapa §9/§15.5)

    class PlanDiff(_StrictModel):
        """Diff por identidade (§15.5): adições/movimentos/remoções e déficit."""

        added: UUIDList = Field(default_factory=list, max_length=1024)
        moved: UUIDList = Field(default_factory=list, max_length=1024)
        removed: UUIDList = Field(default_factory=list, max_length=1024)
        deficit_minutes: StrictInt = Field(ge=0)

    class PlanValidation(_StrictModel):
        """Verificador independente (mapa §9) — separado do solver."""

        passed: StrictBool
        verifier_id: _ShortId
        checked_at: UtcDatetime
        issues: list[
            Annotated[str, StringConstraints(min_length=1, max_length=512)]
        ] = Field(default_factory=list, max_length=64)

    plan_id: UUIDField
    revision: StrictInt = Field(ge=1)
    snapshot_version: StrictInt = Field(ge=0)
    status: SolverStatus
    blocks: list[PlanBlock] = Field(default_factory=list, max_length=1024)
    unmet_demands: UUIDList = Field(default_factory=list, max_length=1024)
    diff: PlanDiff
    validation: PlanValidation
    objective: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    bound: Optional[float] = None
    explanation: Annotated[
        str, StringConstraints(min_length=1, max_length=_MAX_TEXT)
    ]

    @model_validator(mode="after")
    def _invariants(self) -> "ScheduleProposal":
        block_ids = [block.block_id for block in self.blocks]
        if len(set(block_ids)) != len(block_ids):
            raise ValueError("block_id deve ser único na proposta")
        uids = [block.uid for block in self.blocks]
        if len(set(uids)) != len(uids):
            raise ValueError("uid deve ser único na proposta")
        for block in self.blocks:
            if block.start_utc >= block.end_utc:
                raise ValueError("bloco exige start_utc < end_utc")
        # Mapa §9: sem validação não há aprovação — solução publicada
        # (OPTIMAL/FEASIBLE) exige verificador independente aprovado.
        if self.status in (
            ScheduleProposal.SolverStatus.OPTIMAL,
            ScheduleProposal.SolverStatus.FEASIBLE,
        ) and not self.validation.passed:
            raise ValueError(
                "plano OPTIMAL/FEASIBLE exige validation.passed=True "
                "(verificador independente)"
            )
        return self


class Operation(_StrictModel):
    """``Operation`` — operação de commit com versionamento (mapa §4/§11/§15.1).
    Mesmo ``operation_id`` com digest diferente é erro — verificação do commit
    idempotente (§11), de processo, não deste contrato."""

    class OperationAction(str, Enum):
        # Ações de domínio do MVP (mapa §5/§8/§9/§15). Nomenclatura default de
        # ensaio; novas ações exigem revisão de contrato.
        FACT_UPSERT = "fact.upsert"
        FACT_CORRECT = "fact.correct"
        ITEM_PUBLISH = "item.publish"
        ASSESSMENT_RECORD = "assessment.record"
        EVENT_APPEND = "event.append"
        DEMAND_UPSERT = "demand.upsert"
        PLAN_APPROVE = "plan.approve"
        ACTIVITY_UPDATE = "activity.update"
        DATA_DELETE = "data.delete"

    class OperationState(str, Enum):
        PENDING = "pending"
        COMMITTED = "committed"
        FAILED = "failed"

    operation_id: UUIDField
    user_id: UUIDField
    action: OperationAction
    expected_version: StrictInt = Field(ge=0)  # domain_revision (mapa §15.1)
    payload_hash: SHA256Hex
    confirmation_ref: Optional[Ref] = None
    state: OperationState
    receipt_ref: Optional[Ref] = None

    @model_validator(mode="after")
    def _receipt_coupling(self) -> "Operation":
        # Toda escrita passa pelo commit idempotente com recibo (mapa §11).
        if (
            self.state == Operation.OperationState.COMMITTED
            and self.receipt_ref is None
        ):
            raise ValueError("operação committed exige receipt_ref")
        if (
            self.state != Operation.OperationState.COMMITTED
            and self.receipt_ref is not None
        ):
            raise ValueError("receipt_ref só existe para operação committed")
        return self


class MemoryPack(_StrictModel):
    """``MemoryPack`` — memória projetada de um snapshot (mapa §4/§7).
    Invariante de processo: não mistura usuários — a projeção é construída
    por usuário no snapshot (mapa §15.1)."""

    class EventKind(str, Enum):
        # Catálogo de kinds de evento: default de ensaio (mapa §7 lista o
        # campo ``kind`` sem fechar os valores); novos kinds exigem revisão
        # de contrato (como em OperationAction).
        ATTEMPT = "attempt"
        HINT = "hint"
        ASSESSMENT = "assessment"
        CORRECTION = "correction"
        READING = "reading"
        SELF_REPORT = "self_report"
        PREFERENCE = "preference"
        OTHER = "other"

    class Origin(str, Enum):
        # Mapa §7: "Origem: observed/asserted/inferred".
        OBSERVED = "observed"
        ASSERTED = "asserted"
        INFERRED = "inferred"

    class EventRecord(_StrictModel):
        id: UUIDField
        occurred_at: UtcDatetime
        recorded_at: UtcDatetime
        kind: "MemoryPack.EventKind"
        help_level: Optional[StrictInt] = Field(default=None, ge=0, le=3)
        source: "MemoryPack.Origin"

    class Contradiction(_StrictModel):
        """Contradição não conciliada: devolve ambos os registros e pendência
        (mapa §7)."""

        entity_id: UUIDField
        records: list[AcademicFact] = Field(min_length=2, max_length=8)
        pending: StrictBool = True

    class SummaryEntry(_StrictModel):
        """Síntese derivada de originais com claim→event_ids (mapa §7/DDL
        ``summaries``). Publicada como artefato derivado; nunca apaga
        evento."""

        id: UUIDField
        source_event_ids: UUIDList = Field(min_length=1, max_length=_MAX_LIST)
        claims: list[
            Annotated[str, StringConstraints(min_length=1, max_length=512)]
        ] = Field(min_length=1, max_length=32)
        verification: Literal["pending", "verified", "failed"]
        revision: StrictInt = Field(ge=1)

    snapshot_version: StrictInt = Field(ge=0)
    current_facts: list[AcademicFact] = Field(
        default_factory=list, max_length=256
    )
    topic_state: list["TopicState"] = Field(
        default_factory=list, max_length=256
    )
    events: list[EventRecord] = Field(default_factory=list, max_length=256)
    contradictions: list[Contradiction] = Field(
        default_factory=list, max_length=_MAX_LIST
    )
    summaries: list[SummaryEntry] = Field(
        default_factory=list, max_length=_MAX_LIST
    )


# MemoryPack referencia TopicState definido acima; reconstrói o modelo com a
# referência resolvida (ordem da tabela do mapa §4 preservada).
MemoryPack.model_rebuild()


# ---------------------------------------------------------------------------
# Envelope comum (mapa §4)
# ---------------------------------------------------------------------------


class EnvelopeStatus(str, Enum):
    """Estados do envelope (mapa §4). Catálogo default de ensaio; alterar
    exige revisão de contrato (como em Operation.Action)."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_STUDENT = "waiting_student"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArtifactType(str, Enum):
    """Os 11 artefatos obrigatórios da tabela do mapa §4."""

    SOURCE_REF = "SourceRef"
    ACADEMIC_FACT = "AcademicFact"
    EVIDENCE_PACK = "EvidencePack"
    MEMORY_PACK = "MemoryPack"
    LEARNING_ITEM = "LearningItem"
    TUTOR_TURN = "TutorTurn"
    ASSESSMENT = "Assessment"
    TOPIC_STATE = "TopicState"
    STUDY_DEMAND = "StudyDemand"
    SCHEDULE_PROPOSAL = "ScheduleProposal"
    OPERATION = "Operation"


class Envelope(_StrictModel):
    """Envelope comum de mensagem/artefato (mapa §4).

    ``sender_role`` é atribuído pelo dispatcher a partir do contexto
    autenticado local; payload externo não muda papel/permissões (mapa §4).
    """

    schema_version: Literal["1.0"] = "1.0"
    task_id: UUIDField
    trace_id: UUIDField
    parent_task_id: Optional[UUIDField] = None
    sender_role: SenderRole
    artifact_type: ArtifactType
    snapshot_version: StrictInt = Field(ge=0)
    source_refs: list[SourceLocator] = Field(
        default_factory=list, max_length=_MAX_LIST
    )
    payload_ref: Ref
    status: EnvelopeStatus
    error: Optional[TypedError] = None

    @model_validator(mode="after")
    def _status_error_coupling(self) -> "Envelope":
        if self.status == EnvelopeStatus.FAILED and self.error is None:
            raise ValueError("envelope 'failed' exige error tipado")
        if self.status != EnvelopeStatus.FAILED and self.error is not None:
            raise ValueError("error só acompanha envelope 'failed'")
        return self


# ---------------------------------------------------------------------------
# Estado do grafo (mapa §4) — checkpoint guarda refs, não PDFs integrais
# ---------------------------------------------------------------------------


class Intent(str, Enum):
    """Intenções do grafo (mapa §10)."""

    INGEST = "ingest"
    ASK = "ask"
    PRACTICE = "practice"
    SUBMIT_ANSWER = "submit_answer"
    PLAN = "plan"
    REPLAN = "replan"
    APPROVE_PLAN = "approve_plan"
    UPDATE_ACTIVITY = "update_activity"
    MEMORY_QUERY = "memory_query"
    CORRECT_FACT = "correct_fact"
    DELETE_DATA = "delete_data"
    EXPORT_CALENDAR = "export_calendar"
    CURATE = "curate"
    CANCEL = "cancel"


class GraphStatus(str, Enum):
    RUNNING = "running"
    WAITING_STUDENT = "waiting_student"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Budgets(_StrictModel):
    """Orçamentos do turno (mapa §12). Valores atribuídos por configuração
    (defaults de ensaio, mapa §3); ``null`` significa desconhecido, nunca
    zero (mapa §12: "Métricas desconhecidas ficam null com razão")."""

    llm_calls_remaining: StrictInt = Field(ge=0)
    tool_calls_remaining: StrictInt = Field(ge=0)
    tokens_remaining: Optional[StrictInt] = Field(default=None, ge=0)


class GraphState(_StrictModel):
    """Estado do grafo com os campos do mapa §4.

    ``artifact_refs`` guarda refs (ID+versão), não conteúdo — checkpoint
    guarda refs, não PDFs integrais; estado de domínio é autoridade e
    checkpoint não substitui commit (mapa §4/§11).
    """

    user_id: UUIDField
    session_id: UUIDField
    turn_id: UUIDField
    task_id: Optional[UUIDField] = None
    trace_id: UUIDField
    intent: Intent
    snapshot_version: Optional[StrictInt] = Field(default=None, ge=0)
    artifact_refs: list[Ref] = Field(default_factory=list, max_length=256)
    pending_question: Optional[
        Annotated[str, StringConstraints(min_length=1, max_length=2000)]
    ] = None
    pending_item_ref: Optional[Ref] = None
    budgets: Budgets
    deadline: Optional[UtcDatetime] = None
    cancel_requested: StrictBool = False
    status: GraphStatus
    errors: list[TypedError] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def _terminal_invariants(self) -> "GraphState":
        # Mapa §10/§12: cancelamento e deadline produzem terminais com erro
        # tipado; falha carrega ao menos um erro.
        if self.status == GraphStatus.FAILED and not self.errors:
            raise ValueError("estado 'failed' exige ao menos um erro tipado")
        if self.status == GraphStatus.CANCELLED and not any(
            error.code == ErrorCode.CANCELLED for error in self.errors
        ):
            raise ValueError("estado 'cancelled' exige erro tipado CANCELLED")
        if self.status in (GraphStatus.COMPLETED, GraphStatus.WAITING_STUDENT):
            if any(
                error.code == ErrorCode.CANCELLED for error in self.errors
            ):
                raise ValueError(
                    "estado terminal positivo não carrega CANCELLED"
                )
        return self


# ---------------------------------------------------------------------------
# Exportação de JSON Schemas (parte do build — mapa §4)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0"

ALL_CONTRACT_MODELS: tuple[type[BaseModel], ...] = (
    SourceRef,
    AcademicFact,
    EvidencePack,
    MemoryPack,
    LearningItem,
    TutorTurn,
    Assessment,
    TopicState,
    StudyDemand,
    ScheduleProposal,
    Operation,
    TypedError,
    Envelope,
    ToolRequest,
    GraphState,
)


def export_schemas(output_dir: str | Path = "schemas") -> list[Path]:
    """Exporta os JSON Schemas dos contratos para ``output_dir`` (build).

    Saída determinística (chaves ordenadas) para que a regeneração seja
    verificável byte a byte pelo teste de aceite.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    index: dict[str, str] = {}
    for model in ALL_CONTRACT_MODELS:
        schema = model.model_json_schema(mode="validation")
        path = out / f"{model.__name__}.schema.json"
        path.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        written.append(path)
        index[model.__name__] = path.name
    (out / "index.json").write_text(
        json.dumps(
            {"schema_version": SCHEMA_VERSION, "models": index},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    written.append(out / "index.json")
    return written


def schemas_are_current(output_dir: str | Path = "schemas") -> bool:
    """Verifica se ``schemas/`` está idêntico à regeneração atual (build)."""
    import tempfile

    out = Path(output_dir)
    if not out.is_dir():
        return False
    with tempfile.TemporaryDirectory(prefix="eduagent-schemas-") as tmp:
        expected = {p.name: p for p in export_schemas(Path(tmp))}
        for name, path in expected.items():
            target = out / name
            if not target.is_file():
                return False
            if target.read_bytes() != path.read_bytes():
                return False
    return True


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Exporta os JSON Schemas dos contratos (mapa §4)."
    )
    parser.add_argument(
        "--export",
        default="schemas",
        help="diretório de saída (default: schemas/)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="apenas verifica se schemas/ está atualizado (exit 1 se não)",
    )
    args = parser.parse_args(argv)
    if args.check:
        if schemas_are_current(args.export):
            print(f"schemas/ atualizado: {args.export}")
            return 0
        print(f"schemas/ desatualizado: {args.export}", file=sys.stderr)
        return 1
    written = export_schemas(args.export)
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
