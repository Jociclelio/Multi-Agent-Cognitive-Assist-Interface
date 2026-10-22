"""Serviço de calendário: exportação ICS RFC5545, confirmação de plano
(``approve_plan``) e outbox/sync como contratos (mapa normativo §9, §10,
§15.1, §15.5; contratos da task 003, commit idempotente da 005, solver da
012, atividades da 011).

Implementação da task 013. Contratos cobertos:

- **ICS por ``icalendar`` (§9)**: VCALENDAR ``VERSION:2.0``/PRODID; VEVENT
  UID/DTSTAMP/DTSTART/DTEND/SUMMARY mais CREATED/LAST-MODIFIED/SEQUENCE;
  UTF-8/CRLF/folding pela serialização da biblioteca; UTC ``Z`` para
  início/fim com **fim exclusivo**; exportação simples **sem METHOD**.
  UID é UUID estável por bloco lógico (``logical_blocks.uid``, §15.5);
  CREATED vem da criação; DTSTAMP/LAST-MODIFIED vêm da última revisão
  persistida (``modified_at``); SEQUENCE vem de ``event_sequence`` — começa
  em 0 e incrementa **apenas se campos de evento mudam** (§15.5: "não
  porque outra parte do plano mudou"). Retries/reexportações da mesma
  revisão não alteram timestamps (o conteúdo exportado é função pura do
  estado persistido — nenhum relógio na renderização).
  All-day usa ``DATE`` com fim exclusivo no dia seguinte.
- **Parser independente**: ``parse_ics``/``verify_calendar`` reimplementam
  unfolding/parse sem usar a biblioteca de renderização, validando
  round-trip e equivalência com o estado persistido (§9: "parser
  independente valida round-trip"). Importador manual pode duplicar apesar
  de UID — **não prometemos dedup universal** (§9).
- **Persistência em ``logical_blocks`` (§15.5)**: created_at, modified_at,
  event_sequence, summary, value_type, source_demand_id e
  actual_start/end (migrações 0006/0007). Remoção no ICS é **ausência na
  exportação**, não comando remoto de delete; remoto só remove com
  operação confirmada (§9/§15.5).
- **Confirmação (§9/§15.1)**: ``approve_plan`` vincula
  ``plan_id``/``revision``/``digest`` e guarda ``base_revision``,
  ``approval_revision`` pós-commit e conjunto/hash das dependências.
  Alteração posterior (qualquer escrita de domínio ou mudança em
  dependência registrada) invalida a confirmação; nova outbox exige domínio
  igual à ``approval_revision`` (§15.1); confirmação/outbox conjuntas podem
  ocorrer no mesmo commit (um único ``CommitRequest`` — §15.1).
- **``calendar.apply`` (dispatcher determinístico, §10)**: exige
  confirmação atual (domínio igual à ``approval_revision`` e dependências
  inalteradas); outbox somente após confirmação. Sync MCP/CalDAV/Google
  aparece aqui **apenas como contrato e estados** (``CalendarConnector``,
  ``RemoteOp`` com precondições, ``SyncOutcome``): href estável; criação
  ``If-None-Match: *``; atualização ``If-Match`` ETag; update/delete
  condicional do Google só depois de verificar documentação específica
  (task 016). Timeout → ``UNKNOWN_EFFECT`` → read/reconcile, **sem retry
  cego**; alteração externa → conflito e novo preview; conector que não
  preserva leitura/IDs/versão é declarado **não admitido** — mantém-se
  ICS/preview (§9). Conexão real é admitida na task 016.

Nada aqui apresenta resultados medidos; decisões de codificação do MVP
estão documentadas junto de cada contrato.

Correção 013a (sem reabrir decisões da 013): a representação de
DTSTAMP/CREATED/LAST-MODIFIED e as comparações de renderização/verificação/
sync usam o instante **truncado para segundos** (precisão RFC5545/§9) — os
``created_at``/``modified_at`` persistidos conservam a precisão original e
seguem sendo a fonte da revisão (§15.5); a fronteira all-day no sync é
aplicada uma única vez (``_all_day_bounds``/``build_calendar``);
``apply_plan`` revalida a confirmação imediatamente antes de cada efeito
remoto (§15.1); status agregado propaga ``NOT_APPLIED`` reconciliado;
parser de ``dependencies_json`` tolerante ao default ``'[]'`` da migração
0007; igualdade de UPDATE remoto inclui DTSTART/DTEND.
"""

from __future__ import annotations

import hashlib
import json
import uuid as _uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time as _dt_time, timedelta, timezone, tzinfo
from enum import Enum
from typing import Any, Protocol

from icalendar import Calendar as IcsCalendar
from icalendar import Event as IcsEvent

from eduagent.contracts import (
    EduAgentError,
    ErrorCode,
    ScheduleProposal,
    SenderRole,
    ToolName,
    validate_tool_request,
)
from eduagent.services.effects import CommitRequest, EffectsService, EventSpec, OutboxSpec
from eduagent.storage.repository import DomainStore, Receipt

_DIAGNOSTIC = "eduagent/services/calendar.py"

#: Versão do protocolo de calendário do produto (PRODID, mapa §9).
PRODID = "-//EduAgent//EduAgent-OS 0.1//PT"

#: Versão obrigatória do VCALENDAR (RFC5545/§9).
ICS_VERSION = "2.0"

#: Ação de commit idempotente da aprovação (mapa §4 ``PLAN_APPROVE``).
ACTION_PLAN_APPROVE = "plan.approve"

#: Ação de commit idempotente para criação de outbox de calendário
#: (operação de domínio própria; a outbox em si é efeito pendente, §11).
ACTION_EVENT_APPEND = "event.append"

#: Kinds de evento (catálogo default de ensaio, como em MemoryPack.EventKind).
EVENT_PLAN_APPROVED = "plan_approved"
EVENT_CALENDAR_OUTBOX = "calendar_outbox_created"

#: Alvo do outbox de sincronização (task 016 admite os conectores reais).
OUTBOX_TARGET = "calendar.sync"

#: Tipos de valor de evento (§9: all-day usa DATE; resto é DATE-TIME UTC Z).
VALUE_TYPE_DATETIME = "DATE-TIME"
VALUE_TYPE_DATE = "DATE"

#: Status de bloco presente na exportação (decisão de codificação do MVP):
#: ``planned``/``started``/``completed`` são exportados; ``missed`` e
#: ``cancelled`` ficam **ausentes** — remoção no ICS é ausência na
#: exportação, não comando remoto de delete (§9/§15.5).
EXPORT_STATUSES: tuple[str, ...] = ("planned", "started", "completed")

#: Status de bloco fixo (§15.4/§9: "Compromissos, blocos iniciados e
#: concluídos são fixos") — instantes não podem mudar por replan.
FIXED_STATUSES: tuple[str, ...] = ("started", "completed")

#: Namespace determinístico para IDs derivados (confirmação, §15.5).
_CALENDAR_NAMESPACE = _uuid.uuid5(_uuid.NAMESPACE_URL, "eduagent:calendar:v1")

#: Um dia (fim exclusivo all-day, §9).
_ONE_DAY = timedelta(days=1)


def _digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _utc(moment: datetime) -> datetime:
    return moment.astimezone(timezone.utc)


def _ics_moment(moment: datetime) -> datetime:
    """Instante na representação usada pelo ICS: RFC5545 tem precisão de
    segundos (§9), então DTSTAMP/CREATED/LAST-MODIFIED e as comparações de
    renderização/verificação/sync usam o instante truncado para segundos
    (correção 013a, achado A-01). Os ``created_at``/``modified_at``
    persistidos conservam a precisão original e seguem sendo a fonte da
    revisão (§15.5: timestamps derivados da revisão persistida,
    reexportação byte-idêntica — truncar é função pura do estado)."""
    return _utc(moment).replace(microsecond=0)


def _aware(moment: datetime, name: str) -> datetime:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            f"{name} exige datetime com zona (mapa §4)",
            diagnostic=_DIAGNOSTIC,
        )
    return moment


def _parse_utc_text(text: str | None) -> datetime | None:
    if not text:
        return None
    parsed = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


# ---------------------------------------------------------------------------
# Visão de exportação de um bloco lógico (§15.5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExportBlock:
    """Campos de evento persistidos de um bloco lógico (§15.5): identidade
    (``block_id``/``uid``), timestamps de criação/última revisão, sequência
    do evento e instantes efetivos (``actual`` quando presente, senão
    ``planned``)."""

    block_id: _uuid.UUID
    uid: _uuid.UUID
    summary: str
    value_type: str  # VALUE_TYPE_DATE | VALUE_TYPE_DATETIME
    start_utc: datetime
    end_utc: datetime
    created_at: datetime
    modified_at: datetime
    event_sequence: int
    source_demand_id: _uuid.UUID | None = None
    status: str = "planned"


# ---------------------------------------------------------------------------
# Renderização ICS (função pura do estado persistido — §9)
# ---------------------------------------------------------------------------


def _all_day_bounds(
    block: ExportBlock, local_timezone: tzinfo | None
) -> tuple[date, date]:
    """Fronteiras all-day (§9: "All-day usa DATE e fim exclusivo no dia
    seguinte"). Sem zona confirmada, o dia local é o dia UTC (mesma escolha
    conservadora documentada nas tasks 011/012). Exige instantes alinhados a
    meia-noite e dias inteiros — bloco all-day mal alinhado é recusa tipada,
    nunca promoção silenciosa de datetime."""
    zone = local_timezone if local_timezone is not None else timezone.utc
    start_local = block.start_utc.astimezone(zone)
    end_local = block.end_utc.astimezone(zone)
    midnight = _dt_time(0, 0)
    if (
        start_local.time() != midnight
        or end_local.time() != midnight
        or end_local <= start_local
    ):
        raise EduAgentError(
            ErrorCode.SCHEMA_INVALID,
            f"bloco {block.block_id} marcado all-day exige instantes "
            "alinhados a meia-noite local com dias inteiros (§9)",
            diagnostic=_DIAGNOSTIC,
        )
    return start_local.date(), end_local.date()


def build_calendar(
    blocks: Iterable[ExportBlock],
    *,
    prodid: str = PRODID,
    local_timezone: tzinfo | None = None,
) -> bytes:
    """Serializa o calendário (§9) — função pura do estado persistido.

    Sem METHOD (exportação simples); determinística: a mesma entrada produz
    os mesmos bytes, então reexportações da mesma revisão são idênticas e
    não alteram timestamps (§9). Ordenação por (início, UID) mantém a saída
    estável independentemente da ordem de leitura.
    """
    calendar = IcsCalendar()
    calendar.add("VERSION", ICS_VERSION)
    calendar.add("PRODID", prodid)
    # METHOD deliberadamente ausente (§9: "Exportação simples **sem METHOD**").
    for block in sorted(blocks, key=lambda b: (b.start_utc, str(b.uid))):
        _aware(block.start_utc, "start do bloco")
        _aware(block.end_utc, "end do bloco")
        if block.start_utc >= block.end_utc:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"bloco {block.block_id} exige start < end (fim exclusivo, §9)",
                diagnostic=_DIAGNOSTIC,
            )
        event = IcsEvent()
        event.add("UID", str(block.uid))
        # DTSTAMP/LAST-MODIFIED da última revisão persistida; CREATED da
        # criação (§9). Nenhum "agora" entra aqui. Truncados para segundos
        # (precisão RFC5545; correção 013a/A-01).
        event.add("DTSTAMP", _ics_moment(block.modified_at))
        event.add("CREATED", _ics_moment(block.created_at))
        event.add("LAST-MODIFIED", _ics_moment(block.modified_at))
        event.add("SEQUENCE", int(block.event_sequence))
        event.add("SUMMARY", block.summary)
        if block.value_type == VALUE_TYPE_DATE:
            start_day, end_day = _all_day_bounds(block, local_timezone)
            event.add("DTSTART", start_day)  # VALUE=DATE
            event.add("DTEND", end_day)  # fim exclusivo (§9)
        else:
            event.add("DTSTART", _utc(block.start_utc))
            event.add("DTEND", _utc(block.end_utc))
        calendar.add_component(event)
    return calendar.to_ical()


# ---------------------------------------------------------------------------
# Parser independente (§9: "parser independente valida round-trip") —
# reimplementa unfolding/parse RFC5545 sem usar a biblioteca de renderização.
# ---------------------------------------------------------------------------


class IcsParseError(ValueError):
    """Entrada ICS inválida para o parser independente."""


@dataclass(frozen=True)
class ParsedEvent:
    """VEVENT decodificado pelo parser independente."""

    uid: str
    summary: str
    dtstart: date | datetime
    dtend: date | datetime
    dtstamp: datetime | None
    created: datetime | None
    last_modified: datetime | None
    sequence: int | None
    all_day: bool


@dataclass(frozen=True)
class ParsedCalendar:
    """VCALENDAR decodificado: propriedades de nível superior e eventos."""

    version: str | None
    prodid: str | None
    method: str | None
    events: tuple[ParsedEvent, ...]


def _unfold(text: str) -> list[str]:
    """Unfolding RFC5545 §3.1: continuação de linha é CRLF seguido de
    espaço/tab (o parser independente consome tanto CRLF quanto LF solto
    para diagnóstico — a emissão correta é verificada à parte)."""
    lines: list[str] = []
    for physical in text.split("\r\n"):
        if physical[:1] in (" ", "\t") and lines:
            lines[-1] += physical[1:]
        else:
            lines.append(physical)
    return [line for line in lines if line != ""]


def _split_property(line: str) -> tuple[str, dict[str, str], str]:
    """Separa ``NAME;PARAM=VAL:value`` respeitando valores de parâmetro
    entre aspas (que podem conter ':')."""
    in_quotes = False
    for index, char in enumerate(line):
        if char == '"':
            in_quotes = not in_quotes
        elif char == ":" and not in_quotes:
            head, value = line[:index], line[index + 1 :]
            break
    else:  # pragma: no cover — linha sem ':' é rejeitada antes
        raise IcsParseError(f"linha de conteúdo sem ':': {line!r}")
    parts = head.split(";")
    name = parts[0].upper()
    params: dict[str, str] = {}
    for part in parts[1:]:
        if "=" not in part:
            raise IcsParseError(f"parâmetro sem '=': {part!r}")
        key, _, raw = part.partition("=")
        params[key.upper()] = raw.strip('"')
    return name, params, value


def _parse_datetime_value(value: str) -> datetime:
    text = value.strip()
    if not text.endswith("Z"):
        raise IcsParseError(f"timestamp sem UTC Z (§9): {value!r}")
    parsed = datetime.strptime(text, "%Y%m%dT%H%M%SZ")
    return parsed.replace(tzinfo=timezone.utc)


def _parse_date_value(value: str) -> date:
    return datetime.strptime(value.strip(), "%Y%m%d").date()


def _unescape_text(value: str) -> str:
    out: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value):
            nxt = value[index + 1]
            if nxt in ("n", "N"):
                out.append("\n")
                index += 2
                continue
            if nxt in ("\\", ";", ","):
                out.append(nxt)
                index += 2
                continue
        out.append(char)
        index += 1
    return "".join(out)


def parse_ics(data: bytes | str) -> ParsedCalendar:
    """Parser independente de VCALENDAR (§9). Decodifica apenas o conjunto
    de propriedades emitidas por ``build_calendar``; qualquer desvio
    estrutural é erro explícito."""
    text = data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data
    lines = _unfold(text)
    version: str | None = None
    prodid: str | None = None
    method: str | None = None
    events: list[ParsedEvent] = []
    inside_event = False
    current: dict[str, tuple[dict[str, str], str]] = {}
    depth = 0
    for line in lines:
        name, params, value = _split_property(line)
        if name == "BEGIN":
            if value.upper() == "VEVENT":
                inside_event = True
                current = {}
            elif value.upper() == "VCALENDAR":
                depth += 1
            else:
                raise IcsParseError(
                    f"componente não suportado pelo parser do MVP: {value!r}"
                )
            continue
        if name == "END":
            if value.upper() == "VEVENT":
                inside_event = False
                events.append(_event_from_properties(current))
                current = {}
            elif value.upper() == "VCALENDAR":
                depth -= 1
            continue
        if inside_event:
            current[name] = (params, value)
        elif name == "VERSION":
            version = value
        elif name == "PRODID":
            prodid = value
        elif name == "METHOD":
            method = value
    if depth != 0:
        raise IcsParseError("VCALENDAR sem END correspondente")
    return ParsedCalendar(
        version=version, prodid=prodid, method=method, events=tuple(events)
    )


def _event_from_properties(
    props: Mapping[str, tuple[dict[str, str], str]]
) -> ParsedEvent:
    def value_of(name: str) -> str | None:
        entry = props.get(name)
        return entry[1] if entry else None

    uid = value_of("UID")
    if not uid:
        raise IcsParseError("VEVENT sem UID (RFC5545 obrigatório)")
    summary = value_of("SUMMARY")
    if summary is None:
        raise IcsParseError(f"VEVENT {uid} sem SUMMARY (mapa §9)")
    dtstart_entry = props.get("DTSTART")
    dtend_entry = props.get("DTEND")
    if dtstart_entry is None or dtend_entry is None:
        raise IcsParseError(f"VEVENT {uid} exige DTSTART e DTEND (§9)")
    all_day = dtstart_entry[0].get("VALUE", "").upper() == "DATE"
    if all_day:
        dtstart: date | datetime = _parse_date_value(dtstart_entry[1])
        dtend: date | datetime = _parse_date_value(dtend_entry[1])
    else:
        dtstart = _parse_datetime_value(dtstart_entry[1])
        dtend = _parse_datetime_value(dtend_entry[1])
    sequence = (
        int(value_of("SEQUENCE")) if value_of("SEQUENCE") is not None else None
    )
    return ParsedEvent(
        uid=uid,
        summary=_unescape_text(summary),
        dtstart=dtstart,
        dtend=dtend,
        dtstamp=(
            _parse_datetime_value(value_of("DTSTAMP"))
            if value_of("DTSTAMP")
            else None
        ),
        created=(
            _parse_datetime_value(value_of("CREATED"))
            if value_of("CREATED")
            else None
        ),
        last_modified=(
            _parse_datetime_value(value_of("LAST-MODIFIED"))
            if value_of("LAST-MODIFIED")
            else None
        ),
        sequence=sequence,
        all_day=all_day,
    )


def parsed_event_to_block(event: ParsedEvent) -> ExportBlock:
    """Reconstrói um ``ExportBlock`` a partir do evento parseado — usado
    para provar round-trip: render → parse → render reproduz bytes
    idênticos (o ``block_id`` não aparece no ICS; a ordenação usa o UID)."""
    if event.all_day:
        assert isinstance(event.dtstart, date) and not isinstance(
            event.dtstart, datetime
        )
        assert isinstance(event.dtend, date) and not isinstance(
            event.dtend, datetime
        )
        start = datetime.combine(event.dtstart, _dt_time(0, 0), tzinfo=timezone.utc)
        end = datetime.combine(event.dtend, _dt_time(0, 0), tzinfo=timezone.utc)
    else:
        assert isinstance(event.dtstart, datetime)
        assert isinstance(event.dtend, datetime)
        start = event.dtstart
        end = event.dtend
    stamp = event.dtstamp or event.last_modified or _utc(
        datetime.now(timezone.utc)
    )
    created = event.created or stamp
    return ExportBlock(
        block_id=_uuid.uuid5(_CALENDAR_NAMESPACE, f"parsed|{event.uid}"),
        uid=_uuid.UUID(event.uid),
        summary=event.summary,
        value_type=VALUE_TYPE_DATE if event.all_day else VALUE_TYPE_DATETIME,
        start_utc=start,
        end_utc=end,
        created_at=created,
        modified_at=stamp,
        event_sequence=event.sequence or 0,
    )


def verify_calendar(
    data: bytes,
    blocks: Sequence[ExportBlock],
    *,
    prodid: str = PRODID,
    local_timezone: tzinfo | None = None,
) -> list[str]:
    """Validação de publicação (rota ``export_calendar``: render_ics →
    validate; §10): parser independente confere estrutura RFC5545/§9 e
    equivalência campo a campo com o estado persistido. Retorna problemas
    (lista vazia = válido)."""
    issues: list[str] = []
    text = data.decode("utf-8")
    if "\n" in text.replace("\r\n", ""):
        issues.append("quebra de linha fora de CRLF (RFC5545)")
    for physical in text.split("\r\n"):
        if len(physical.encode("utf-8")) > 75:
            issues.append("linha física acima de 75 octets (folding, RFC5545)")
            break
    try:
        parsed = parse_ics(data)
    except (IcsParseError, ValueError, _uuid.UUIDError) as exc:
        return [*issues, f"parse independente falhou: {exc}"]
    if parsed.version != ICS_VERSION:
        issues.append(f"VERSION {parsed.version!r} != {ICS_VERSION!r}")
    if parsed.prodid != prodid:
        issues.append(f"PRODID {parsed.prodid!r} != {prodid!r}")
    if parsed.method is not None:
        issues.append("METHOD presente — exportação simples não deve ter METHOD (§9)")
    expected_by_uid = {str(b.uid): b for b in blocks}
    parsed_by_uid = {e.uid: e for e in parsed.events}
    for uid, block in expected_by_uid.items():
        event = parsed_by_uid.get(uid)
        if event is None:
            issues.append(f"evento {uid} ausente no ICS renderizado")
            continue
        if event.summary != block.summary:
            issues.append(f"SUMMARY divergente para {uid}")
        if event.sequence != block.event_sequence:
            issues.append(f"SEQUENCE divergente para {uid}")
        if event.created != _ics_moment(block.created_at):
            issues.append(f"CREATED divergente para {uid}")
        stamp = _ics_moment(block.modified_at)
        if event.dtstamp != stamp or event.last_modified != stamp:
            issues.append(f"DTSTAMP/LAST-MODIFIED divergentes para {uid}")
        if block.value_type == VALUE_TYPE_DATE:
            start_day, end_day = _all_day_bounds(block, local_timezone)
            if not event.all_day or event.dtstart != start_day or event.dtend != end_day:
                issues.append(f"DTSTART/DTEND all-day divergentes para {uid}")
        else:
            if event.all_day or event.dtstart != _utc(block.start_utc):
                issues.append(f"DTSTART divergente para {uid}")
            if event.dtend != _utc(block.end_utc):
                issues.append(f"DTEND divergente para {uid} (fim exclusivo)")
    for uid in parsed_by_uid:
        if uid not in expected_by_uid:
            issues.append(f"evento {uid} no ICS sem bloco persistido")
    if len(parsed_by_uid) != len(parsed.events):
        issues.append("UID repetido no ICS (§15.5)")
    return issues


# ---------------------------------------------------------------------------
# Contratos de sincronização — SOMENTE contrato/estados nesta task (§9);
# conexão real é admitida na task 016.
# ---------------------------------------------------------------------------


class RemoteOpKind(str, Enum):
    """Operação remota do contrato de sync (§9: ``read/create/update/delete``
    com IDs/precondições)."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class SyncOutcome(str, Enum):
    """Estado de um efeito de sync (§9/§11). ``CONFLICT`` é alteração
    externa detectada → conflito e novo preview; ``UNKNOWN_EFFECT`` é
    terminal, sem retry automático."""

    APPLIED = "APPLIED"
    UNCHANGED = "UNCHANGED"
    NOT_APPLIED = "NOT_APPLIED"
    CONFLICT = "CONFLICT"
    UNKNOWN_EFFECT = "UNKNOWN_EFFECT"


class ConnectorTimeout(Exception):
    """Tempo esgotado no conector: o efeito pode ou não ter ocorrido — o
    dispatcher trata como UNKNOWN e reconcilia por leitura (§9/§11), nunca
    repete cegamente."""


@dataclass(frozen=True)
class RemoteEvent:
    """Estado remoto lido (contrato de leitura, §9).

    ``href`` é o identificador estável do recurso (CalDAV: href estável);
    ``etag`` é a versão usada nas precondições condicionais; ``event_ics``
    é o corpo quando o conector o expõe — conector sem leitura de corpo não
    suporta reconciliação de update e é declarado não admitido (§9).
    """

    uid: str
    href: str
    etag: str | None = None
    event_ics: bytes | None = None


@dataclass(frozen=True)
class RemoteOp:
    """Operação remota com precondições (§9).

    - CREATE: ``if_none_match_star=True`` (CalDAV: criação ``If-None-Match: *``).
    - UPDATE/DELETE: ``if_match_etag`` do read anterior (``If-Match`` ETag;
      href estável reutilizado). Google: update/delete condicional só é
      habilitado depois de verificar documentação específica (task 016).
    - DELETE só é gerado com operação confirmada: ``confirmation_digest``
      liga a remoção à confirmação vigente (§9/§15.5: "remoto só remove com
      operação confirmada").
    """

    kind: RemoteOpKind
    uid: str
    event_ics: bytes | None
    confirmation_digest: str
    href: str | None = None
    if_none_match_star: bool = False
    if_match_etag: str | None = None


class CalendarConnector(Protocol):
    """Contrato do conector de sincronização (§9) — nesta task, apenas o
    contrato/estados; conexão real é admitida na task 016.

    Regras do contrato:

    - ``read_all``/``read_one`` expõem leitura com IDs (uid/href) e versão
      (etag); conector que não preservar leitura, IDs e versão é declarado
      **não admitido** — mantém-se ICS/preview (§9).
    - Criação exige ``if_none_match_star=True``; atualização/remoção exigem
      ``if_match_etag`` do read anterior. Precondição falhada = alteração
      externa → CONFLICT e novo preview (§9).
    - Timeout sinalizado por ``ConnectorTimeout`` — o dispatcher reconcilia
      por leitura; **nunca retry cego** (§9/§11: timeout→unknown_effect→
      read/reconcile).
    - Implementações NÃO abrem transação no banco de domínio: o efeito roda
      fora de transação (§11).
    """

    def read_all(self, target: str) -> list[RemoteEvent]: ...

    def read_one(self, target: str, uid: str) -> RemoteEvent | None: ...

    def create(
        self,
        target: str,
        uid: str,
        event_ics: bytes,
        *,
        if_none_match_star: bool = True,
    ) -> SyncOutcome: ...

    def update(
        self,
        target: str,
        uid: str,
        href: str,
        event_ics: bytes,
        *,
        if_match_etag: str | None,
    ) -> SyncOutcome: ...

    def delete(
        self,
        target: str,
        uid: str,
        href: str,
        *,
        if_match_etag: str | None,
    ) -> SyncOutcome: ...


@dataclass(frozen=True)
class OpResult:
    """Resultado individual de uma operação de sync (observabilidade §12)."""

    uid: str
    kind: RemoteOpKind
    outcome: SyncOutcome
    detail: str = ""


@dataclass(frozen=True)
class ApplyReport:
    """Relatório de ``calendar.apply`` (dispatcher determinístico, §10)."""

    plan_id: _uuid.UUID
    confirmation_digest: str
    status: SyncOutcome
    ops: tuple[OpResult, ...] = ()
    detail: str = ""


# ---------------------------------------------------------------------------
# Confirmação (§9/§15.1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfirmationRecord:
    """Confirmação persistida (§15.1): vincula plan_id/revision/digest e
    guarda ``base_revision``, ``approval_revision`` pós-commit e conjunto/
    hash das dependências."""

    confirmation_id: _uuid.UUID
    plan_id: _uuid.UUID
    plan_revision: int
    digest: str
    occurred_at: datetime
    base_revision: int
    approval_revision: int
    dependencies: tuple[tuple[str, int | None], ...]
    dependencies_hash: str


@dataclass(frozen=True)
class ApprovePlanResult:
    """Resultado de ``approve_plan``: recibo do commit idempotente (§11),
    confirmação registrada e sinalização de outbox conjunta (§15.1)."""

    receipt: Receipt
    confirmation: ConfirmationRecord
    outbox_created: bool


@dataclass(frozen=True)
class RenderResult:
    """Resultado de ``calendar.render`` (§10): ICS validado pelo parser
    independente mais os blocos exportados."""

    ics: bytes
    blocks: tuple[ExportBlock, ...]
    confirmation: ConfirmationRecord
    issues: tuple[str, ...] = ()


class CalendarService:
    """Exportação ICS, confirmação de plano e dispatcher determinístico de
    calendário (mapa §9/§10/§15.1/§15.5)."""

    def __init__(
        self,
        store: DomainStore,
        effects: EffectsService,
        *,
        clock: Callable[[], datetime] | None = None,
        local_timezone: tzinfo | None = None,
        prodid: str = PRODID,
    ) -> None:
        self._store = store
        self._effects = effects
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._local_timezone = local_timezone
        self._prodid = prodid

    # -- blocos lógicos (§15.5) ----------------------------------------------

    def _blocks_from_rows(self, rows: Sequence[Any]) -> list[ExportBlock]:
        blocks: list[ExportBlock] = []
        for row in rows:
            start = _parse_utc_text(row["actual_start_utc"]) or _parse_utc_text(
                row["planned_start_utc"]
            )
            end = _parse_utc_text(row["actual_end_utc"]) or _parse_utc_text(
                row["planned_end_utc"]
            )
            if start is None or end is None:  # pragma: no cover — NOT NULL 0006
                raise EduAgentError(
                    ErrorCode.INTERNAL_FAILURE,
                    f"bloco {row['id']} sem instantes persistidos",
                    diagnostic=_DIAGNOSTIC,
                )
            created = _parse_utc_text(row["created_at"]) or self._clock()
            modified = _parse_utc_text(row["modified_at"]) or created
            blocks.append(
                ExportBlock(
                    block_id=_uuid.UUID(str(row["id"])),
                    uid=_uuid.UUID(str(row["uid"])),
                    summary=str(row["summary"] or ""),
                    value_type=str(row["value_type"] or VALUE_TYPE_DATETIME),
                    start_utc=start,
                    end_utc=end,
                    created_at=created,
                    modified_at=modified,
                    event_sequence=int(row["event_sequence"]),
                    source_demand_id=(
                        _uuid.UUID(str(row["source_demand_id"]))
                        if row["source_demand_id"]
                        else None
                    ),
                    status=str(row["status"]),
                )
            )
        return blocks

    def all_blocks(self, user_id: str) -> list[ExportBlock]:
        """Todos os blocos lógicos do usuário (§15.5)."""
        rows = self._store.fetch_user_rows(
            "SELECT id, uid, status, planned_start_utc, planned_end_utc, "
            "actual_start_utc, actual_end_utc, source_demand_id, "
            "event_sequence, created_at, modified_at, summary, value_type "
            "FROM logical_blocks WHERE user_id = ? ORDER BY rowid",
            (user_id,),
        )
        return self._blocks_from_rows(rows)

    def export_blocks(self, user_id: str) -> list[ExportBlock]:
        """Blocos presentes na exportação (§9/§15.5): ``planned``/``started``/
        ``completed``; ``missed``/``cancelled`` ausentes — remoção no ICS é
        ausência na exportação."""
        placeholders = ",".join("?" * len(EXPORT_STATUSES))
        rows = self._store.fetch_user_rows(
            "SELECT id, uid, status, planned_start_utc, planned_end_utc, "
            "actual_start_utc, actual_end_utc, source_demand_id, "
            "event_sequence, created_at, modified_at, summary, value_type "
            f"FROM logical_blocks WHERE user_id = ? AND status IN "
            f"({placeholders}) ORDER BY rowid",
            (user_id, *EXPORT_STATUSES),
        )
        return self._blocks_from_rows(rows)

    # -- dependências da aprovação (§15.1) ------------------------------------

    def _dependency_revisions(
        self, user_id: str, demand_ids: Sequence[_uuid.UUID]
    ) -> dict[str, int | None]:
        """Revisão atual de cada demanda dependente (``demands.revision``);
        demanda sem linha registra ``None`` — a comparação de hash detecta
        surgimento/mudança posterior."""
        if not demand_ids:
            return {}
        keys = sorted({str(d) for d in demand_ids})
        placeholders = ",".join("?" * len(keys))
        rows = self._store.fetch_user_rows(
            "SELECT id, revision FROM demands WHERE user_id = ? AND id IN "
            f"({placeholders})",
            (user_id, *keys),
        )
        found = {str(row["id"]): int(row["revision"]) for row in rows}
        return {key: found.get(key) for key in keys}

    @staticmethod
    def _dependencies_hash(
        dependencies: Mapping[str, int | None]
    ) -> tuple[str, str]:
        payload = {key: dependencies[key] for key in sorted(dependencies)}
        canonical = json.dumps(payload, sort_keys=True)
        return canonical, hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # -- aprovação (approve_plan, §9/§15.1) -----------------------------------

    def approve_plan(
        self,
        user_id: str,
        proposal: ScheduleProposal,
        *,
        summaries: Mapping[str, str] | None = None,
        all_day_demand_ids: Sequence[_uuid.UUID | str] = (),
        operation_id: str | None = None,
        create_outbox: bool = False,
    ) -> ApprovePlanResult:
        """Confirma o plano (rota ``approve_plan`` do §10: validar
        revisão/digest → commit_confirmation) e materializa os blocos lógicos
        (§15.5) no mesmo commit idempotente (§11).

        - Vincula ``plan_id``/``revision``/``digest``; guarda
          ``base_revision`` (pré-commit), ``approval_revision`` (pós-commit)
          e conjunto/hash das dependências (§15.1).
        - ``create_outbox=True`` insere confirmação **e** outbox no mesmo
          commit (§15.1: "confirmação/outbox conjunta pode ocorrer no mesmo
          commit") — a ``approval_revision`` é a revisão pós-commit, então a
          condição de outbox vale dentro do próprio commit.
        - Materialização por identidade (§15.5): bloco novo → INSERT
          (created_at=modified_at=commit, SEQUENCE 0); bloco mantido com os
          mesmos instantes → nenhum statement (timestamps estáveis); bloco
          movido → UPDATE com ``event_sequence`` +1 e ``modified_at`` novo;
          bloco aprovado antes e ausente agora → DELETE (ausência na
          exportação). Bloco iniciado/concluído é fixo (§15.4): instantes
          divergentes são recusa tipada.
        - Retry com o mesmo ``operation_id`` devolve o recibo original sem
          nova escrita (§11) — timestamps não mudam.
        """
        if proposal.status not in (
            ScheduleProposal.SolverStatus.OPTIMAL,
            ScheduleProposal.SolverStatus.FEASIBLE,
        ) or not proposal.validation.passed:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "só plano validado pelo verificador independente é "
                "aprovável (§9: nunca publicar relaxação como aprovado)",
                diagnostic=_DIAGNOSTIC,
            )
        now = _utc(self._clock())
        plan_key = str(_uuid.UUID(str(proposal.plan_id)))
        payload = proposal.model_dump(mode="json")
        digest = _digest(
            {
                "plan_id": plan_key,
                "revision": proposal.revision,
                "snapshot_version": proposal.snapshot_version,
                "blocks": payload["blocks"],
                "diff": payload["diff"],
                "unmet_demands": payload["unmet_demands"],
            }
        )
        base_revision = self._store.domain_revision(user_id)
        approval_revision = base_revision + 1  # pós-commit (§15.1)
        demand_ids = [block.demand_id for block in proposal.blocks]
        dependencies = self._dependency_revisions(user_id, demand_ids)
        dependencies_json, dependencies_hash = self._dependencies_hash(
            dependencies
        )
        operation_key = operation_id or str(_uuid.uuid4())
        confirmation_id = _uuid.uuid5(
            _CALENDAR_NAMESPACE, f"confirmation|{operation_key}"
        )

        # -- materialização por identidade (§15.5) ---------------------------
        statements: list[tuple[str, tuple[Any, ...]]] = []
        all_day = {str(_uuid.UUID(str(d))) for d in all_day_demand_ids}
        summaries_map = dict(summaries or {})
        desired: list[ExportBlock] = []
        for block in proposal.blocks:
            block_key = str(_uuid.UUID(str(block.block_id)))
            demand_key = str(_uuid.UUID(str(block.demand_id)))
            value_type = (
                VALUE_TYPE_DATE if demand_key in all_day else VALUE_TYPE_DATETIME
            )
            summary = summaries_map.get(demand_key, "Estudo")
            existing = self._store.fetch_user_rows(
                "SELECT id, uid, status, planned_start_utc, planned_end_utc, "
                "event_sequence, created_at, modified_at, summary, "
                "value_type FROM logical_blocks WHERE user_id = ? AND id = ?",
                (user_id, block_key),
            )
            start_text = _utc(block.start_utc).isoformat()
            end_text = _utc(block.end_utc).isoformat()
            if not existing:
                statements.append(
                    (
                        "INSERT INTO logical_blocks(id, user_id, uid, status, "
                        "planned_start_utc, planned_end_utc, "
                        "source_demand_id, event_sequence, created_at, "
                        "modified_at, summary, value_type) VALUES "
                        "(?,?,?,'planned',?,?,?,?,?,?,?,?)",
                        (
                            block_key,
                            user_id,
                            str(_uuid.UUID(str(block.uid))),
                            start_text,
                            end_text,
                            demand_key,
                            0,
                            now.isoformat(),
                            now.isoformat(),
                            summary,
                            value_type,
                        ),
                    )
                )
                desired.append(
                    ExportBlock(
                        block_id=block.block_id,
                        uid=_uuid.UUID(str(block.uid)),
                        summary=summary,
                        value_type=value_type,
                        start_utc=_utc(block.start_utc),
                        end_utc=_utc(block.end_utc),
                        created_at=now,
                        modified_at=now,
                        event_sequence=0,
                        source_demand_id=_uuid.UUID(demand_key),
                        status="planned",
                    )
                )
                continue
            row = existing[0]
            status = str(row["status"])
            same_instants = (
                _parse_utc_text(row["planned_start_utc"]) == _utc(block.start_utc)
                and _parse_utc_text(row["planned_end_utc"]) == _utc(block.end_utc)
            )
            persisted_created = (
                _parse_utc_text(row["created_at"]) or now
            )
            persisted_modified = (
                _parse_utc_text(row["modified_at"]) or persisted_created
            )
            persisted_sequence = int(row["event_sequence"])
            if status in FIXED_STATUSES:
                if not same_instants:
                    raise EduAgentError(
                        ErrorCode.SCHEMA_INVALID,
                        f"bloco {block_key} ({status}) é fixo (§15.4/§9): "
                        "replan não altera instantes de iniciado/concluído",
                        diagnostic=_DIAGNOSTIC,
                    )
                desired.append(
                    ExportBlock(
                        block_id=block.block_id,
                        uid=_uuid.UUID(str(block.uid)),
                        summary=str(row["summary"] or summary),
                        value_type=str(row["value_type"] or value_type),
                        start_utc=_utc(block.start_utc),
                        end_utc=_utc(block.end_utc),
                        created_at=persisted_created,
                        modified_at=persisted_modified,
                        event_sequence=persisted_sequence,
                        source_demand_id=_uuid.UUID(demand_key),
                        status=status,
                    )
                )
                continue  # fixo e igual: nada a fazer (timestamps estáveis)
            if same_instants:
                # Mesma revisão de evento: nenhum statement — SEQUENCE só
                # incrementa se campos de evento mudam (§15.5).
                desired.append(
                    ExportBlock(
                        block_id=block.block_id,
                        uid=_uuid.UUID(str(block.uid)),
                        summary=str(row["summary"] or summary),
                        value_type=str(row["value_type"] or value_type),
                        start_utc=_utc(block.start_utc),
                        end_utc=_utc(block.end_utc),
                        created_at=persisted_created,
                        modified_at=persisted_modified,
                        event_sequence=persisted_sequence,
                        source_demand_id=_uuid.UUID(demand_key),
                        status=status,
                    )
                )
                continue
            statements.append(
                (
                    "UPDATE logical_blocks SET planned_start_utc = ?, "
                    "planned_end_utc = ?, modified_at = ?, "
                    "event_sequence = event_sequence + 1 WHERE user_id = ? "
                    "AND id = ?",
                    (start_text, end_text, now.isoformat(), user_id, block_key),
                )
            )
            desired.append(
                ExportBlock(
                    block_id=block.block_id,
                    uid=_uuid.UUID(str(block.uid)),
                    summary=str(row["summary"] or summary),
                    value_type=str(row["value_type"] or value_type),
                    start_utc=_utc(block.start_utc),
                    end_utc=_utc(block.end_utc),
                    created_at=persisted_created,
                    modified_at=now,
                    event_sequence=persisted_sequence + 1,
                    source_demand_id=_uuid.UUID(demand_key),
                    status=status,
                )
            )

        # Removidos: diff por identidade da própria proposta (§15.5) —
        # ``removed`` lista block_ids aprovados antes e ausentes agora.
        # Remoção local = ausência na exportação (§9/§15.5); remoção remota
        # só ocorre com operação confirmada (``calendar.apply``).
        for removed_key in proposal.diff.removed:
            block_key = str(_uuid.UUID(str(removed_key)))
            rows = self._store.fetch_user_rows(
                "SELECT id, status FROM logical_blocks WHERE user_id = ? "
                "AND id = ?",
                (user_id, block_key),
            )
            if not rows:
                continue
            if str(rows[0]["status"]) in FIXED_STATUSES:
                raise EduAgentError(
                    ErrorCode.SCHEMA_INVALID,
                    f"bloco {block_key} ({rows[0]['status']}) é fixo e não "
                    "pode ser removido por replan (§15.4/§9)",
                    diagnostic=_DIAGNOSTIC,
                )
            statements.append(
                (
                    "DELETE FROM logical_blocks WHERE user_id = ? AND id = ?",
                    (user_id, block_key),
                )
            )

        # -- confirmação + plano + outbox no MESMO commit (§15.1) ------------
        statements.append(
            (
                "INSERT INTO plans(id, user_id, revision, snapshot_version, "
                "payload_json, approval_ref) VALUES (?,?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET revision = excluded.revision, "
                "snapshot_version = excluded.snapshot_version, "
                "payload_json = excluded.payload_json, "
                "approval_ref = excluded.approval_ref",
                (
                    plan_key,
                    user_id,
                    proposal.revision,
                    proposal.snapshot_version,
                    proposal.model_dump_json(),
                    str(confirmation_id),
                ),
            )
        )
        statements.append(
            (
                "INSERT INTO confirmations(id, user_id, artifact_id, "
                "artifact_revision, digest, occurred_at, base_revision, "
                "approval_revision, dependencies_json, dependencies_hash) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    str(confirmation_id),
                    user_id,
                    plan_key,
                    proposal.revision,
                    digest,
                    now.isoformat(),
                    base_revision,
                    approval_revision,
                    dependencies_json,
                    dependencies_hash,
                ),
            )
        )
        outbox_spec: OutboxSpec | None = None
        if create_outbox:
            outbox_payload = self._outbox_payload(
                user_id,
                digest=digest,
                approval_revision=approval_revision,
                desired_blocks=desired,
                plan_id=plan_key,
                plan_revision=proposal.revision,
            )
            outbox_spec = OutboxSpec(
                id=str(
                    _uuid.uuid5(
                        _CALENDAR_NAMESPACE, f"outbox|{operation_key}"
                    )
                ),
                target=OUTBOX_TARGET,
                payload=outbox_payload,
            )
        request = CommitRequest(
            operation_id=operation_key,
            user_id=user_id,
            action=ACTION_PLAN_APPROVE,
            digest=digest,
            expected_version=base_revision,
            event=EventSpec(
                id=str(_uuid.uuid4()),
                kind=EVENT_PLAN_APPROVED,
                occurred_at=now.isoformat(),
                recorded_at=now.isoformat(),
                payload={
                    "plan_id": plan_key,
                    "revision": proposal.revision,
                    "digest": digest,
                    "base_revision": base_revision,
                    "approval_revision": approval_revision,
                    "outbox": bool(create_outbox),
                },
            ),
            outbox=outbox_spec,
            projection=tuple(statements),
        )
        receipt = self._effects.commit(request)
        confirmation = self._require_confirmation(user_id, plan_key)
        return ApprovePlanResult(
            receipt=receipt,
            confirmation=confirmation,
            outbox_created=create_outbox,
        )

    # -- leitura de confirmação e validade (§15.1) ----------------------------

    def latest_confirmation(
        self, user_id: str, plan_id: _uuid.UUID | str
    ) -> ConfirmationRecord | None:
        """Última confirmação do plano (mais recente por rowid)."""
        plan_key = str(_uuid.UUID(str(plan_id)))
        rows = self._store.fetch_user_rows(
            "SELECT id, artifact_id, artifact_revision, digest, occurred_at, "
            "base_revision, approval_revision, dependencies_json, "
            "dependencies_hash FROM confirmations WHERE user_id = ? AND "
            "artifact_id = ? ORDER BY rowid DESC LIMIT 1",
            (user_id, plan_key),
        )
        if not rows:
            return None
        return self._confirmation_from_row(rows[0])

    def _require_confirmation(
        self, user_id: str, plan_key: str
    ) -> ConfirmationRecord:
        confirmation = self.latest_confirmation(user_id, plan_key)
        if confirmation is None:  # pragma: no cover — commit garante a linha
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                "confirmação não encontrada após commit confirmado",
                diagnostic=_DIAGNOSTIC,
            )
        return confirmation

    def _confirmation_from_row(self, row: Any) -> ConfirmationRecord:
        # Tolerante ao default da migração 0007 (correção 013a/G-A1):
        # ``dependencies_json`` pode chegar como ``'[]'`` (lista vazia) em
        # linha legada — conjunto vazio de dependências, nunca AttributeError.
        raw = json.loads(row["dependencies_json"] or "[]")
        if isinstance(raw, dict):
            dependencies = tuple(
                (str(key), revision) for key, revision in raw.items()
            )
        elif isinstance(raw, list) and not raw:
            # Default da migração 0007: confirmação sem conjunto de
            # dependências registrado — conjunto vazio (§15.1).
            dependencies = ()
        else:
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                "dependencies_json malformado em confirmação persistida "
                "(defeito)",
                diagnostic=_DIAGNOSTIC,
            )
        return ConfirmationRecord(
            confirmation_id=_uuid.UUID(str(row["id"])),
            plan_id=_uuid.UUID(str(row["artifact_id"])),
            plan_revision=int(row["artifact_revision"]),
            digest=str(row["digest"]),
            occurred_at=_parse_utc_text(row["occurred_at"])  # type: ignore[arg-type]
            or datetime.now(timezone.utc),
            base_revision=int(row["base_revision"] or 0),
            approval_revision=int(row["approval_revision"] or 0),
            dependencies=dependencies,
            dependencies_hash=str(row["dependencies_hash"] or ""),
        )

    def check_confirmation_current(
        self, user_id: str, confirmation: ConfirmationRecord
    ) -> None:
        """Confirmação atual (§15.1): domínio igual à ``approval_revision`` e
        dependências com as mesmas revisões. Alteração posterior invalida a
        confirmação ainda não aplicada → ``VERSION_CONFLICT`` (novo preview).
        Linha legada sem hash de dependências (default da migração 0007,
        correção 013a/G-A1) valida apenas a revisão de domínio."""
        current = self._store.domain_revision(user_id)
        if current != confirmation.approval_revision:
            raise EduAgentError(
                ErrorCode.VERSION_CONFLICT,
                "confirmação invalidada por alteração posterior do domínio "
                f"(approval_revision={confirmation.approval_revision}, "
                f"domínio={current}); gerar novo preview (§15.1)",
                diagnostic=_DIAGNOSTIC,
            )
        if not confirmation.dependencies_hash:
            # Sem conjunto de dependências registrado (linha legada da
            # migração 0007): a revisão de domínio acima continua a barrar
            # escrita posterior; nada a comparar por dependência.
            return
        dependencies = dict(confirmation.dependencies)
        _, current_hash = self._dependencies_hash(dependencies)
        if current_hash != confirmation.dependencies_hash:
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                "hash de dependências da confirmação divergente do conjunto "
                "registrado (defeito)",
                diagnostic=_DIAGNOSTIC,
            )
        demand_ids = [_uuid.UUID(key) for key, _ in confirmation.dependencies]
        now_revisions = self._dependency_revisions(user_id, demand_ids)
        _, fresh_hash = self._dependencies_hash(now_revisions)
        if fresh_hash != confirmation.dependencies_hash:
            raise EduAgentError(
                ErrorCode.VERSION_CONFLICT,
                "dependência da aprovação mudou após a confirmação; novo "
                "preview obrigatório (§15.1)",
                diagnostic=_DIAGNOSTIC,
            )

    def _current_confirmation_or_fail(
        self, user_id: str, plan_id: _uuid.UUID | str, *, tool: str
    ) -> ConfirmationRecord:
        confirmation = self.latest_confirmation(user_id, plan_id)
        if confirmation is None:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"{tool} exige confirmação atual do plano e nenhuma "
                f"confirmação existe para {plan_id} (§9/§10)",
                diagnostic=_DIAGNOSTIC,
            )
        self.check_confirmation_current(user_id, confirmation)
        return confirmation

    # -- outbox após confirmação (§15.1/§11) ----------------------------------

    def _outbox_payload(
        self,
        user_id: str,
        *,
        digest: str,
        approval_revision: int,
        desired_blocks: Sequence[ExportBlock],
        plan_id: str,
        plan_revision: int,
    ) -> dict[str, Any]:
        """Payload do efeito pendente de sync (task 016 despacha): conjunto
        de eventos desejados por identidade, com digest da confirmação como
        identidade do efeito (§11) e precondições resolvidas no despacho.
        No commit conjunto (§15.1) o estado desejado vem do plano de
        materialização — as projeções ainda não executaram."""
        return {
            "plan_id": plan_id,
            "revision": plan_revision,
            "approval_revision": approval_revision,
            "confirmation_digest": digest,
            "blocks": [
                {
                    "block_id": str(b.block_id),
                    "uid": str(b.uid),
                    "summary": b.summary,
                    "value_type": b.value_type,
                    "start_utc": _utc(b.start_utc).isoformat(),
                    "end_utc": _utc(b.end_utc).isoformat(),
                    "created_at": _utc(b.created_at).isoformat(),
                    "modified_at": _utc(b.modified_at).isoformat(),
                    "event_sequence": b.event_sequence,
                }
                for b in sorted(
                    desired_blocks, key=lambda b: (b.start_utc, str(b.uid))
                )
            ],
        }

    def enqueue_outbox(
        self,
        user_id: str,
        plan_id: _uuid.UUID | str,
        *,
        operation_id: str | None = None,
    ) -> Receipt:
        """Cria outbox de calendário **após** confirmação (§9: "Outbox
        somente após confirmação"; §15.1: "Antes de criar nova outbox exige
        domínio igual à ``approval_revision``"). É uma operação nova de
        domínio: incrementa a revisão — uma segunda outbox para a mesma
        confirmação é recusada (o domínio deixou de ser igual)."""
        plan_key = str(_uuid.UUID(str(plan_id)))
        confirmation = self.latest_confirmation(user_id, plan_key)
        if confirmation is None:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"outbox exige confirmação do plano {plan_key} (§9)",
                diagnostic=_DIAGNOSTIC,
            )
        self.check_confirmation_current(user_id, confirmation)
        proposal_row = self._store.fetch_user_rows(
            "SELECT payload_json FROM plans WHERE user_id = ? AND id = ?",
            (user_id, plan_key),
        )
        if not proposal_row:  # pragma: no cover — confirmação implica plano
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"plano {plan_key} não resolve para o usuário",
                diagnostic=_DIAGNOSTIC,
            )
        proposal = ScheduleProposal.model_validate_json(
            str(proposal_row[0]["payload_json"])
        )
        now = _utc(self._clock())
        payload = self._outbox_payload(
            user_id,
            digest=confirmation.digest,
            approval_revision=confirmation.approval_revision,
            desired_blocks=self.export_blocks(user_id),
            plan_id=plan_key,
            plan_revision=confirmation.plan_revision,
        )
        operation_key = operation_id or str(_uuid.uuid4())
        request = CommitRequest(
            operation_id=operation_key,
            user_id=user_id,
            action=ACTION_EVENT_APPEND,
            digest=_digest(payload),
            expected_version=confirmation.approval_revision,
            event=EventSpec(
                id=str(_uuid.uuid4()),
                kind=EVENT_CALENDAR_OUTBOX,
                occurred_at=now.isoformat(),
                recorded_at=now.isoformat(),
                payload={
                    "plan_id": plan_key,
                    "confirmation_id": str(confirmation.confirmation_id),
                },
            ),
            outbox=OutboxSpec(
                id=str(
                    _uuid.uuid5(
                        _CALENDAR_NAMESPACE, f"outbox|{operation_key}"
                    )
                ),
                target=OUTBOX_TARGET,
                payload=payload,
            ),
        )
        return self._effects.commit(request)

    # -- calendar.render (§10: Planejador; plano válido → parser e
    #    equivalência) ---------------------------------------------------------

    def render_plan(
        self,
        user_id: str,
        plan_id: _uuid.UUID | str,
        *,
        sender_role: SenderRole,
    ) -> RenderResult:
        """Ferramenta ``calendar.render`` (mapa §10): só o Planejador propõe;
        pré-condição "plano válido" = plano **confirmado e atual** (critério
        do plano 04: nenhum ICS é gerado sem plano confirmado; decisão
        conservadora: confirmação atual — evita exportar grade desalinhada
        do domínio). O ICS é validado pelo parser independente antes de
        publicar; divergência é defeito e nunca é publicada."""
        validate_tool_request(ToolName.CALENDAR_RENDER, sender_role)
        confirmation = self._current_confirmation_or_fail(
            user_id, plan_id, tool="calendar.render"
        )
        blocks = self.export_blocks(user_id)
        data = build_calendar(
            blocks, prodid=self._prodid, local_timezone=self._local_timezone
        )
        issues = verify_calendar(
            data,
            blocks,
            prodid=self._prodid,
            local_timezone=self._local_timezone,
        )
        if issues:
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                "ICS renderizado falhou no parser independente "
                f"(defeito, nada publicado): {'; '.join(issues[:3])}",
                diagnostic=_DIAGNOSTIC,
            )
        return RenderResult(
            ics=data,
            blocks=tuple(blocks),
            confirmation=confirmation,
        )

    # -- calendar.apply (dispatcher determinístico, §10) -----------------------

    def build_sync_ops(
        self,
        user_id: str,
        confirmation: ConfirmationRecord,
        connector: CalendarConnector,
        *,
        target: str = OUTBOX_TARGET,
    ) -> list[RemoteOp]:
        """Constrói o plano de sincronização (§9): diff por UID entre o
        estado desejado (blocos materializados) e o estado remoto lido.
        CREATE usa ``If-None-Match: *``; UPDATE/DELETE usam o ``If-Match``
        ETag e o href estável do read; DELETE só existe para UID remoto
        ausente do desejado e carrega o digest da confirmação (operação
        confirmada, §9/§15.5)."""
        remote = connector.read_all(target)
        remote_by_uid = {event.uid: event for event in remote}
        # A fronteira all-day é aplicada uma única vez, por
        # ``_all_day_bounds``/``build_calendar`` com o fuso do serviço
        # (correção 013a/A-02: sem pré-conversão para meia-noite UTC, que
        # causava dupla conversão de fuso com ``local_timezone`` ≠ UTC).
        desired = self.export_blocks(user_id)
        desired_by_uid = {str(b.uid): b for b in desired}
        ops: list[RemoteOp] = []
        for block in sorted(desired, key=lambda b: (b.start_utc, str(b.uid))):
            uid = str(block.uid)
            event_ics = build_calendar(
                [block],
                prodid=self._prodid,
                local_timezone=self._local_timezone,
            )
            current = remote_by_uid.get(uid)
            if current is None:
                ops.append(
                    RemoteOp(
                        kind=RemoteOpKind.CREATE,
                        uid=uid,
                        event_ics=event_ics,
                        confirmation_digest=confirmation.digest,
                        if_none_match_star=True,
                    )
                )
                continue
            parsed = parse_ics(current.event_ics) if current.event_ics else None
            event = parsed.events[0] if parsed and parsed.events else None
            # Igualdade de UPDATE remoto (correção 013a/G-A2): SUMMARY,
            # SEQUENCE, DTSTAMP **e DTSTART/DTEND** — remoto mutante com
            # SEQUENCE/DTSTAMP intactos é detectado. DTSTAMP compara na
            # representação truncada para segundos (A-01).
            if block.value_type == VALUE_TYPE_DATE:
                start_day, end_day = _all_day_bounds(
                    block, self._local_timezone
                )
                expected_start: date | datetime = start_day
                expected_end: date | datetime = end_day
            else:
                expected_start = _utc(block.start_utc)
                expected_end = _utc(block.end_utc)
            matches = (
                event is not None
                and event.summary == block.summary
                and event.sequence == block.event_sequence
                and event.dtstamp == _ics_moment(block.modified_at)
                and event.dtstart == expected_start
                and event.dtend == expected_end
            )
            if matches:
                continue  # estado remoto já igual: nenhum efeito
            ops.append(
                RemoteOp(
                    kind=RemoteOpKind.UPDATE,
                    uid=uid,
                    href=current.href,
                    event_ics=event_ics,
                    confirmation_digest=confirmation.digest,
                    if_match_etag=current.etag,
                )
            )
        for uid, event in sorted(remote_by_uid.items()):
            if uid in desired_by_uid:
                continue
            # Remoção remota só com operação confirmada (§9/§15.5): o apply
            # é autorizado pela confirmação vigente (digest no op).
            ops.append(
                RemoteOp(
                    kind=RemoteOpKind.DELETE,
                    uid=uid,
                    href=event.href,
                    event_ics=None,
                    confirmation_digest=confirmation.digest,
                    if_match_etag=event.etag,
                )
            )
        return ops

    def apply_plan(
        self,
        user_id: str,
        plan_id: _uuid.UUID | str,
        *,
        connector: CalendarConnector | None = None,
        sender_role: SenderRole = SenderRole.SYSTEM,
        target: str = OUTBOX_TARGET,
    ) -> ApplyReport:
        """``calendar.apply`` (mapa §10): dispatcher determinístico; exige
        confirmação atual (§10/§15.1) — sem confirmação, ou com confirmação
        invalidada por alteração posterior, é recusado com erro tipado.
        A confirmação é revalidada imediatamente antes de cada efeito remoto
        (§15.1): confirmação obsoleta no meio do lote interrompe o despacho
        com recusa tipada, sem aplicar os efeitos restantes; efeitos já
        enviados entram em reconciliação por leitura (§11), sem retry cego.

        Com conector admitido, executa as operações com precondições fora de
        transação (§11): timeout → ``UNKNOWN_EFFECT`` → read/reconcile por
        identidade, **sem retry cego**; alteração externa (precondição
        falhada) → CONFLICT e novo preview. Resultado reconciliado como
        ``NOT_APPLIED`` (total ou parcial) propaga no status agregado
        (correção 013a/L-A2). Sem conector admitido, declara
        ``CONNECTOR_DISABLED`` e mantém ICS/preview (§9). A conexão real é
        admitida na task 016 — aqui o contrato e os estados são o entregável.
        """
        validate_tool_request(ToolName.CALENDAR_APPLY, sender_role)
        plan_key = _uuid.UUID(str(plan_id))
        confirmation = self._current_confirmation_or_fail(
            user_id, plan_key, tool="calendar.apply"
        )
        if connector is None:
            return ApplyReport(
                plan_id=plan_key,
                confirmation_digest=confirmation.digest,
                status=SyncOutcome.UNCHANGED,
                ops=(),
                detail="CONNECTOR_DISABLED: nenhum conector de sync admitido "
                "— manter ICS/preview (§9); conexão real é admitida na task "
                "016",
            )
        ops = self.build_sync_ops(
            user_id, confirmation, connector, target=target
        )
        results: list[OpResult] = []
        final_status = SyncOutcome.APPLIED
        detail = ""
        applied_any = False
        not_applied = False
        for op in ops:
            # §15.1: "antes de envio, valida que nenhuma restrição/atividade
            # dependente mudou" — revalidação imediatamente antes de CADA
            # efeito remoto (correção 013a/L-A1). Confirmação obsoleta
            # (domínio/dependência alterados entre a checagem inicial e o
            # envio) interrompe o lote com recusa tipada, sem aplicar os
            # efeitos restantes; efeitos já enviados entram em reconciliação
            # por leitura (§11) — sem retry cego.
            self.check_confirmation_current(user_id, confirmation)
            result = self._run_remote_op(connector, target, op)
            results.append(result)
            if result.outcome is SyncOutcome.CONFLICT:
                final_status = SyncOutcome.CONFLICT
                detail = (
                    f"alteração externa em {op.uid}; novo preview "
                    "obrigatório (§9)"
                )
                break
            if result.outcome is SyncOutcome.UNKNOWN_EFFECT:
                final_status = SyncOutcome.UNKNOWN_EFFECT
                detail = (
                    f"efeito de {op.uid} permanece UNKNOWN_EFFECT; sem "
                    "retry automático (§9/§11)"
                )
                break
            if result.outcome is SyncOutcome.APPLIED:
                applied_any = True
            elif result.outcome is SyncOutcome.NOT_APPLIED:
                not_applied = True
        if not_applied and final_status is SyncOutcome.APPLIED:
            # Correção 013a/L-A2: o status agregado propaga o resultado não
            # aplicado (ou parcial) reconciliado por leitura, coerente com
            # os detalhes individuais (§11).
            final_status = SyncOutcome.NOT_APPLIED
            detail = detail or (
                "efeito remoto reconciliado como NOT_APPLIED"
                + (
                    " — execução parcial: parte dos efeitos foi aplicada"
                    if applied_any
                    else ""
                )
                + "; novo diff e confirmação antes de reenviar (§11)"
            )
        return ApplyReport(
            plan_id=plan_key,
            confirmation_digest=confirmation.digest,
            status=final_status,
            ops=tuple(results),
            detail=detail,
        )

    # -- execução de um op remoto (estado, §9/§11) -----------------------------

    def _run_remote_op(
        self, connector: CalendarConnector, target: str, op: RemoteOp
    ) -> OpResult:
        try:
            if op.kind is RemoteOpKind.CREATE:
                outcome = connector.create(
                    target,
                    op.uid,
                    op.event_ics or b"",
                    if_none_match_star=op.if_none_match_star,
                )
            elif op.kind is RemoteOpKind.UPDATE:
                assert op.href is not None
                outcome = connector.update(
                    target,
                    op.uid,
                    op.href,
                    op.event_ics or b"",
                    if_match_etag=op.if_match_etag,
                )
            else:
                assert op.href is not None
                outcome = connector.delete(
                    target,
                    op.uid,
                    op.href,
                    if_match_etag=op.if_match_etag,
                )
        except ConnectorTimeout:
            return self._reconcile(connector, target, op)
        if outcome is SyncOutcome.CONFLICT:
            return OpResult(
                uid=op.uid,
                kind=op.kind,
                outcome=SyncOutcome.CONFLICT,
                detail="precondição falhada: alteração externa (§9)",
            )
        if outcome is SyncOutcome.APPLIED:
            return OpResult(uid=op.uid, kind=op.kind, outcome=outcome)
        return OpResult(
            uid=op.uid,
            kind=op.kind,
            outcome=outcome,
            detail="definitivamente não aplicado; entrega ao menos uma vez (§11)",
        )

    def _reconcile(
        self, connector: CalendarConnector, target: str, op: RemoteOp
    ) -> OpResult:
        """Timeout → UNKNOWN → read/reconcile por identidade (§9/§11), sem
        retry cego. O estado reconciliado decide: efeito ocorreu (APPLIED),
        não ocorreu (NOT_APPLIED — seguro reaplicar como nova execução
        confirmada) ou permanece desconhecido (UNKNOWN_EFFECT terminal)."""
        try:
            remote = connector.read_one(target, op.uid)
        except ConnectorTimeout:
            return OpResult(
                uid=op.uid,
                kind=op.kind,
                outcome=SyncOutcome.UNKNOWN_EFFECT,
                detail="timeout sem consulta possível — UNKNOWN_EFFECT (§11)",
            )
        if op.kind is RemoteOpKind.CREATE:
            if remote is not None:
                return OpResult(
                    uid=op.uid,
                    kind=op.kind,
                    outcome=SyncOutcome.APPLIED,
                    detail="reconciliado por leitura: evento criado",
                )
            return OpResult(
                uid=op.uid,
                kind=op.kind,
                outcome=SyncOutcome.NOT_APPLIED,
                detail="reconciliado por leitura: não criado",
            )
        if op.kind is RemoteOpKind.DELETE:
            if remote is None:
                return OpResult(
                    uid=op.uid,
                    kind=op.kind,
                    outcome=SyncOutcome.APPLIED,
                    detail="reconciliado por leitura: evento removido",
                )
            return OpResult(
                uid=op.uid,
                kind=op.kind,
                outcome=SyncOutcome.NOT_APPLIED,
                detail="reconciliado por leitura: ainda presente",
            )
        # UPDATE: reconciliação exige leitura de corpo (conector sem leitura
        # de corpo não admite reconciliação de update — §9).
        if remote is None:
            return OpResult(
                uid=op.uid,
                kind=op.kind,
                outcome=SyncOutcome.NOT_APPLIED,
                detail="reconciliado por leitura: evento ausente",
            )
        if remote.event_ics is None:
            return OpResult(
                uid=op.uid,
                kind=op.kind,
                outcome=SyncOutcome.UNKNOWN_EFFECT,
                detail="conector sem leitura de corpo: reconciliação de "
                "update impossível (§9)",
            )
        parsed = parse_ics(remote.event_ics)
        event = parsed.events[0] if parsed.events else None
        desired = parse_ics(op.event_ics or b"").events[0] if op.event_ics else None
        if (
            event is not None
            and desired is not None
            and event.sequence == desired.sequence
            and event.dtstamp == desired.dtstamp
            and event.summary == desired.summary
            # Mesma igualdade do diff de UPDATE (correção 013a/G-A2):
            # instantes divergentes com SEQUENCE/DTSTAMP intactos não são
            # reconciliados como "corpo igual".
            and event.dtstart == desired.dtstart
            and event.dtend == desired.dtend
        ):
            return OpResult(
                uid=op.uid,
                kind=op.kind,
                outcome=SyncOutcome.APPLIED,
                detail="reconciliado por leitura: corpo igual ao desejado",
            )
        return OpResult(
            uid=op.uid,
            kind=op.kind,
            outcome=SyncOutcome.UNKNOWN_EFFECT,
            detail="estado remoto divergente após timeout — UNKNOWN_EFFECT",
        )


__all__ = [
    "ACTION_EVENT_APPEND",
    "ACTION_PLAN_APPROVE",
    "ApplyReport",
    "ApprovePlanResult",
    "CalendarConnector",
    "CalendarService",
    "ConfirmationRecord",
    "ConnectorTimeout",
    "EVENT_CALENDAR_OUTBOX",
    "EVENT_PLAN_APPROVED",
    "ExportBlock",
    "EXPORT_STATUSES",
    "FIXED_STATUSES",
    "IcsParseError",
    "ICS_VERSION",
    "OpResult",
    "OUTBOX_TARGET",
    "ParsedCalendar",
    "ParsedEvent",
    "PRODID",
    "RemoteEvent",
    "RemoteOp",
    "RemoteOpKind",
    "RenderResult",
    "SyncOutcome",
    "VALUE_TYPE_DATE",
    "VALUE_TYPE_DATETIME",
    "build_calendar",
    "parse_ics",
    "parsed_event_to_block",
    "verify_calendar",
]
