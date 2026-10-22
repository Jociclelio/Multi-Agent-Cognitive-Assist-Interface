"""Conectores de sincronização de calendário (mapa normativo §9 — "Sync
opcional via MCP"; §10 — ``calendar.apply``; §15.1/§15.5).

Contratos de estados/precondições vieram da task 013
(``eduagent/services/calendar.py``): ``CalendarConnector`` expõe
``read_all``/``read_one``/``create``/``update``/``delete`` com IDs (uid/href)
e precondições condicionais. Nesta task 016 os conectores são ADMITIDOS
individualmente, cada um após contrato e testes de falha de rede:

- **CalDAV (RFC 4791) — ADMITIDO**: href estável por recurso; criação
  ``PUT`` com ``If-None-Match: *``; atualização/remoção ``PUT``/``DELETE``
  com ``If-Match: <ETag>`` do read anterior; timeout de transporte levanta
  ``ConnectorTimeout`` → o dispatcher reconcilia por leitura, **sem retry
  cego** (§9/§11). A conexão real usa urllib com credenciais configuradas;
  os testes usam transporte injetado (sem rede real).
- **Google Calendar — NÃO ADMITIDO**: update/delete condicional exige
  verificação documental específica (§9) que não foi realizada nesta
  entrega, e não há credenciais para testes de falha de rede. O conector
  NÃO é implementado — ``GoogleCalendarConnector`` recusa por código, e
  ``CONNECTOR_ADMISSION`` registra o motivo. ICS/preview são mantidos (§9).
- **Sem conector configurado**: ``build_calendar_connector`` devolve
  ``None`` e ``calendar.apply`` reporta ``CONNECTOR_DISABLED`` mantendo
  ICS/preview (§9) — sem credenciais o núcleo segue funcional.

O adaptador MCP é a superfície allowlisted de ferramentas (§10: "MCP é
adaptador allowlisted de ferramentas"): expõe exatamente
``read/create/update/delete`` com IDs/precondições; qualquer outra
ferramenta — ou precondição ausente — é negada por código
(``TOOL_DENIED``/``SCHEMA_INVALID``). Integração com um servidor MCP real
é a mesma superfície; o contrato de ferramentas é o entregável.

Limites numéricos (timeout) são **defaults de ensaio** (mapa §1/§3), nunca
resultados medidos.
"""

from __future__ import annotations

import base64
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urljoin, urlsplit

from eduagent.contracts import EduAgentError, ErrorCode
from eduagent.services.calendar import (
    ConnectorTimeout,
    OUTBOX_TARGET,
    RemoteEvent,
    RemoteOpKind,
    SyncOutcome,
    parse_ics,
)

DIAGNOSTIC = "eduagent/services/sync_connectors.py"

#: Timeout por requisição HTTP em segundos (default de ensaio, §3/§12).
DEFAULT_SYNC_TIMEOUT_S = 10.0

#: Registro de admissão dos conectores (§9: cada conector é admitido
#: individualmente; o que não é admitido fica registrado com motivo).
CONNECTOR_ADMISSION: dict[str, str] = {
    "caldav": (
        "ADMITIDO (§9): contrato RFC 4791 — href estável, criação "
        "If-None-Match: *, atualização/remoção If-Match ETag; timeout → "
        "ConnectorTimeout → read/reconcile sem retry cego; testes de falha "
        "de rede (timeout, precondição falhada, resposta inválida) com "
        "transporte injetado."
    ),
    "google": (
        "NÃO ADMITIDO (§9): update/delete condicional só é habilitado "
        "depois de verificar documentação específica — verificação NÃO "
        "realizada nesta entrega e sem credenciais para testes de falha de "
        "rede. Conector não implementado; ICS/preview mantidos. Nenhum "
        "comportamento é inventado."
    ),
}


def connector_admission() -> dict[str, str]:
    """Cópia do registro de admissão (§9) — para doctor/relatório."""
    return dict(CONNECTOR_ADMISSION)


def _error(
    code: ErrorCode,
    message: str,
    *,
    retryable: bool | None = None,
    diagnostic: str = DIAGNOSTIC,
) -> EduAgentError:
    return EduAgentError(
        code, message, retryable=retryable, diagnostic=diagnostic
    )


class ConnectorError(Exception):
    """Falha DEFINIDA de transporte (conexão recusada, resposta inválida):
    o efeito certamente não ocorreu (a conexão não foi estabelecida/concluída)
    — mapeado a ``NOT_APPLIED`` nas escritas e propagado nas leituras (§11:
    reconciliação decide por leitura; timeout é o caso desconhecido)."""


#: Transporte HTTP injetável:
#: ``(method, url, body, headers) -> (status, headers, body)``.
#: Levanta ``TimeoutError`` (efeito desconhecido) ou ``ConnectionError`` /
#: ``OSError`` / ``ConnectorError`` (falha definida). A construção de
#: precondições (If-None-Match/If-Match) fica NO conector, fora do seam.
SyncTransport = Callable[
    [str, str, bytes, Mapping[str, str]],
    tuple[int, Mapping[str, str], bytes],
]


def make_urllib_transport(
    base_url: str,
    username: str | None,
    password: str | None,
    *,
    timeout_s: float = DEFAULT_SYNC_TIMEOUT_S,
) -> SyncTransport:
    """Transporte padrão (urllib) com autenticação Basic. Apenas para uso
    real configurado; os testes usam transporte injetado (sem rede)."""
    host = urlsplit(base_url)
    if host.scheme not in {"http", "https"} or not host.netloc:
        raise _error(
            ErrorCode.SCHEMA_INVALID,
            "base_url do CalDAV deve ser URL http(s) absoluta",
        )
    headers: dict[str, str] = {"User-Agent": "EduAgent-OS/0.1"}
    if username is not None or password is not None:
        token = base64.b64encode(
            f"{username or ''}:{password or ''}".encode("utf-8")
        ).decode("ascii")
        headers["Authorization"] = f"Basic {token}"

    def transport(
        method: str, url: str, body: bytes, extra: Mapping[str, str]
    ) -> tuple[int, Mapping[str, str], bytes]:
        request = urllib.request.Request(
            url, data=body if body else None, method=method
        )
        for key, value in {**headers, **extra}.items():
            request.add_header(key, value)
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as resp:
                return int(resp.status), dict(resp.headers), resp.read()
        except urllib.error.HTTPError as exc:
            return int(exc.code), dict(exc.headers or {}), exc.read() or b""
        except (TimeoutError, ConnectionError):
            raise
        except OSError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError):
                raise TimeoutError(str(reason)) from exc
            raise ConnectorError(str(exc)) from exc

    return transport


_DAV = "DAV:"
_CALDAV = "urn:ietf:params:xml:ns:caldav"


def parse_multistatus(
    xml_body: bytes, base_url: str
) -> list[dict[str, Any]]:
    """Parse mínimo de ``207 Multi-Status`` (RFC 4918): devolve
    ``{href, etag, ics}`` por response. Corpo de calendário ausente ou
    ilegível NÃO é inventado — ``ics`` vem ``None``."""
    responses: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_body)
    except ET.ParseError as exc:
        raise ConnectorError(f"multistatus inválido: {exc}") from exc
    for response in root.findall(f"{{{ _DAV }}}response"):
        href_el = response.find(f"{{{ _DAV }}}href")
        raw_href = (
            (href_el.text or "").strip() if href_el is not None else ""
        )
        href = urljoin(base_url, raw_href) if raw_href else ""
        etag_el = response.find(f"{{{ _DAV }}}propstat/{{{ _DAV }}}prop/{{{ _DAV }}}getetag")
        etag = (etag_el.text or "").strip() if etag_el is not None else None
        if etag is not None and len(etag) >= 2 and etag.startswith('"') and etag.endswith('"'):
            # ETag costuma vir entre aspas no protocolo — a versão usada nas
            # precondições é o valor interno (mesma forma do If-Match).
            etag = etag[1:-1]
        ics_el = response.find(
            f"{{{ _DAV }}}propstat/{{{ _DAV }}}prop/"
            f"{{{ _CALDAV }}}calendar-data"
        )
        ics = (ics_el.text or "").encode("utf-8") if ics_el is not None and ics_el.text else None
        responses.append({"href": href, "etag": etag, "ics": ics})
    return responses


@dataclass(frozen=True)
class CaldavConfig:
    """Configuração do conector CalDAV (coleção alvo + credenciais).
    Credenciais vêm da configuração local do usuário — sem elas, o conector
    não é construído e o núcleo segue funcional (§9)."""

    base_url: str
    username: str | None = None
    password: str | None = None
    timeout_s: float = DEFAULT_SYNC_TIMEOUT_S


class CaldavConnector:
    """Conector CalDAV (RFC 4791) — ADMITIDO individualmente (§9).

    Contrato implementado:
    - ``read_all``/``read_one``: leitura com IDs (uid/href) e versão (etag);
      href é o identificador estável do recurso no servidor.
    - ``create``: ``PUT`` no href estável derivado do UID com
      ``If-None-Match: *`` (obrigatório — recusa ``SCHEMA_INVALID`` sem ele).
    - ``update``: ``PUT`` no href do read com ``If-Match: <ETag>``.
    - ``delete``: ``DELETE`` no href do read com ``If-Match: <ETag>``;
      HTTP 404 mapeia a APPLIED (recurso já ausente — estado igual ao
      desejado; escolha local documentada, evita reenvio inútil).
    - ``TimeoutError`` do transporte → ``ConnectorTimeout`` (efeito
      DESCONHECIDO — dispatcher reconcilia por leitura, §9/§11).
    - Falha definida de conexão (``ConnectorError``/``ConnectionError``) →
      ``NOT_APPLIED`` nas escritas (efeito certamente não ocorreu; reenvio
      condicional é seguro) e propagação nas leituras.
    """

    def __init__(
        self,
        config: CaldavConfig,
        *,
        transport: SyncTransport | None = None,
    ) -> None:
        base = config.base_url.rstrip("/")
        if not base.lower().startswith(("http://", "https://")):
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                "base_url do CalDAV deve ser URL http(s) absoluta",
            )
        self._base_url = base + "/"
        self._transport = transport or make_urllib_transport(
            config.base_url,
            config.username,
            config.password,
            timeout_s=config.timeout_s,
        )

    # -- helpers --------------------------------------------------------------

    def _href_for(self, uid: str) -> str:
        """Href estável por UID (§9): recurso ``<UID>.ics`` na coleção."""
        return urljoin(self._base_url, quote(uid, safe="") + ".ics")

    def _request(
        self, method: str, url: str, body: bytes, headers: Mapping[str, str]
    ) -> tuple[int, Mapping[str, str], bytes]:
        try:
            return self._transport(method, url, body, dict(headers))
        except TimeoutError as exc:
            raise ConnectorTimeout(
                f"timeout no transporte CalDAV ({method}): efeito desconhecido"
            ) from exc

    # -- leitura (§9: read com IDs e versão) -----------------------------------

    def read_all(self, target: str) -> list[RemoteEvent]:
        status, _, body = self._request(
            "REPORT",
            self._base_url,
            (
                '<?xml version="1.0" encoding="utf-8"?>'
                f'<c:calendar-query xmlns:d="{_DAV}" xmlns:c="{_CALDAV}">'
                "<d:prop><d:getetag/><c:calendar-data/></d:prop>"
                '<c:filter><c:comp-filter name="VCALENDAR"/></c:filter>'
                "</c:calendar-query>"
            ).encode("utf-8"),
            {
                "Depth": "1",
                "Content-Type": "application/xml; charset=utf-8",
            },
        )
        if status != 207:
            raise ConnectorError(
                f"REPORT CalDAV respondeu HTTP {status} (esperado 207)"
            )
        events: list[RemoteEvent] = []
        for entry in parse_multistatus(body, self._base_url):
            ics = entry["ics"]
            uid = None
            if ics:
                try:
                    parsed = parse_ics(ics)
                    if parsed.events:
                        uid = parsed.events[0].uid
                except Exception:  # noqa: BLE001 — corpo ilegível não é UID
                    uid = None
            if uid is None:
                # UID do href (convenção comum); sem corpo legível,
                # ``event_ics`` fica None — reconciliação de update nesses
                # recursos é UNKNOWN (conservador, §9).
                href = str(entry["href"])
                uid = href.rsplit("/", 1)[-1].removesuffix(".ics")
            events.append(
                RemoteEvent(
                    uid=uid,
                    href=str(entry["href"]),
                    etag=entry["etag"],
                    event_ics=ics if ics else None,
                )
            )
        return events

    def read_one(self, target: str, uid: str) -> RemoteEvent | None:
        # MVP: coleções locais pequenas — reconciliação por leitura usa o
        # mesmo REPORT de ``read_all``; nenhuma suposição extra sobre o
        # servidor (ex.: mapeamento filename→UID) é inventada.
        for event in self.read_all(target):
            if event.uid == uid:
                return event
        return None

    # -- escrita com precondições (§9) -----------------------------------------

    def create(
        self,
        target: str,
        uid: str,
        event_ics: bytes,
        *,
        if_none_match_star: bool = True,
    ) -> SyncOutcome:
        if not if_none_match_star:
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                "criação CalDAV exige If-None-Match: * (§9)",
            )
        try:
            status, _, _ = self._request(
                "PUT",
                self._href_for(uid),
                event_ics,
                {
                    "If-None-Match": "*",
                    "Content-Type": "text/calendar; charset=utf-8",
                },
            )
        except (ConnectorError, ConnectionError, OSError):
            return SyncOutcome.NOT_APPLIED
        if status in (201, 204):
            return SyncOutcome.APPLIED
        if status == 412:
            return SyncOutcome.CONFLICT
        return SyncOutcome.NOT_APPLIED

    def update(
        self,
        target: str,
        uid: str,
        href: str,
        event_ics: bytes,
        *,
        if_match_etag: str | None,
    ) -> SyncOutcome:
        if if_match_etag is None:
            # §9: atualização é SEMPRE condicional — sem ETag do read
            # anterior não há precondição; escrita incondicional é recusada.
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                "atualização CalDAV exige If-Match ETag do read anterior (§9)",
            )
        headers = {
            "If-Match": if_match_etag,
            "Content-Type": "text/calendar; charset=utf-8",
        }
        try:
            status, _, _ = self._request("PUT", href, event_ics, headers)
        except (ConnectorError, ConnectionError, OSError):
            return SyncOutcome.NOT_APPLIED
        if status in (200, 204):
            return SyncOutcome.APPLIED
        if status == 412:
            return SyncOutcome.CONFLICT
        return SyncOutcome.NOT_APPLIED

    def delete(
        self,
        target: str,
        uid: str,
        href: str,
        *,
        if_match_etag: str | None,
    ) -> SyncOutcome:
        if if_match_etag is None:
            # §9: remoção é SEMPRE condicional (mesma regra do update).
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                "remoção CalDAV exige If-Match ETag do read anterior (§9)",
            )
        headers: dict[str, str] = {"If-Match": if_match_etag}
        try:
            status, _, _ = self._request("DELETE", href, b"", headers)
        except (ConnectorError, ConnectionError, OSError):
            return SyncOutcome.NOT_APPLIED
        if status in (200, 204):
            return SyncOutcome.APPLIED
        if status == 404:
            # Recurso já ausente: estado remoto igual ao desejado. Escolha
            # local documentada — evita reenvio de remoção inexistente.
            return SyncOutcome.APPLIED
        if status == 412:
            return SyncOutcome.CONFLICT
        return SyncOutcome.NOT_APPLIED


def build_calendar_connector(
    config: Mapping[str, Any] | None,
) -> CaldavConnector | None:
    """Fábrica de conector de sync (§9): devolve ``None`` quando o sync está
    desabilitado ou sem CalDAV configurado — ``calendar.apply`` reporta
    ``CONNECTOR_DISABLED`` e mantém ICS/preview; o núcleo segue funcional.
    Chaves esperadas: ``calendar_sync_enabled`` e ``calendar_sync`` com
    ``{base_url, username?, password?, timeout_s?}``."""
    if not config or not config.get("calendar_sync_enabled"):
        return None
    caldav = config.get("calendar_sync") or {}
    base_url = str(caldav.get("base_url") or "")
    if not base_url:
        return None
    return CaldavConnector(
        CaldavConfig(
            base_url=base_url,
            username=caldav.get("username"),
            password=caldav.get("password"),
            timeout_s=float(
                caldav.get("timeout_s", DEFAULT_SYNC_TIMEOUT_S)
            ),
        )
    )


class GoogleCalendarConnector:
    """Conector Google — **NÃO ADMITIDO** (§9). Nenhum método é implementado:
    update/delete condicional exige verificação documental específica (não
    realizada) e não há credenciais para testes de falha de rede. Construir
    uma instância é recusado por código — nenhuma saída parcial silenciosa."""

    NOT_ADMITTED_REASON = CONNECTOR_ADMISSION["google"]

    def __init__(self) -> None:
        raise _error(
            ErrorCode.RESOURCE_LIMIT,
            "CONNECTOR_DISABLED: conector Google " + self.NOT_ADMITTED_REASON,
            retryable=True,
            diagnostic=DIAGNOSTIC,
        )


class McpCalendarAdapter:
    """Adaptador MCP allowlisted do sync de calendário (§10: "Sync opcional
    via MCP deve expor ``read/create/update/delete`` com IDs/precondições";
    "MCP é adaptador allowlisted de ferramentas").

    Superfície exposta (e somente ela):
    - ``calendar.read``    — ``{uid}`` → estado remoto ou ``null``;
    - ``calendar.create``  — ``{uid, event_ics, if_none_match_star}``;
      ``if_none_match_star`` é OBRIGATÓRIO ser ``true`` (§9);
    - ``calendar.update``  — ``{uid, href, event_ics, if_match_etag}``;
    - ``calendar.delete``  — ``{uid, href, if_match_etag}``.

    Qualquer outra ferramenta é negada por código (``TOOL_DENIED``); IDs e
    precondições ausentes são recusados (``SCHEMA_INVALID``). O adaptador
    NÃO abre transação no banco de domínio (§11) — só repassa ao conector.
    """

    TOOL_NAMES = (
        "calendar.read",
        "calendar.create",
        "calendar.update",
        "calendar.delete",
    )

    def __init__(
        self,
        connector: Any,
        *,
        target: str = OUTBOX_TARGET,
    ) -> None:
        self._connector = connector
        self._target = target

    def list_tools(self) -> list[dict[str, Any]]:
        """Ferramentas allowlisted com schema de entrada (IDs/precondições)."""
        return [
            {
                "name": "calendar.read",
                "description": "Lê o evento remoto por UID (§9).",
                "input_schema": {
                    "type": "object",
                    "required": ["uid"],
                    "properties": {"uid": {"type": "string"}},
                },
            },
            {
                "name": "calendar.create",
                "description": "Cria evento remoto (If-None-Match: *, §9).",
                "input_schema": {
                    "type": "object",
                    "required": ["uid", "event_ics", "if_none_match_star"],
                    "properties": {
                        "uid": {"type": "string"},
                        "event_ics": {"type": "string"},
                        "if_none_match_star": {"const": True},
                    },
                },
            },
            {
                "name": "calendar.update",
                "description": "Atualiza evento remoto (If-Match ETag, §9).",
                "input_schema": {
                    "type": "object",
                    "required": ["uid", "href", "event_ics", "if_match_etag"],
                    "properties": {
                        "uid": {"type": "string"},
                        "href": {"type": "string"},
                        "event_ics": {"type": "string"},
                        "if_match_etag": {"type": "string"},
                    },
                },
            },
            {
                "name": "calendar.delete",
                "description": "Remove evento remoto (If-Match ETag, §9).",
                "input_schema": {
                    "type": "object",
                    "required": ["uid", "href", "if_match_etag"],
                    "properties": {
                        "uid": {"type": "string"},
                        "href": {"type": "string"},
                        "if_match_etag": {"type": "string"},
                    },
                },
            },
        ]

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Any:
        """Dispatch allowlisted: ferramenta fora da lista é negada por código
        (§10 — "JSON correto para ação proibida é negado por código")."""
        args = dict(arguments or {})
        if name == "calendar.read":
            uid = self._required_str(args, "uid")
            event = self._connector.read_one(self._target, uid)
            if event is None:
                return None
            return {
                "uid": event.uid,
                "href": event.href,
                "etag": event.etag,
                "event_ics": (
                    event.event_ics.decode("utf-8", errors="replace")
                    if event.event_ics
                    else None
                ),
            }
        if name == "calendar.create":
            uid = self._required_str(args, "uid")
            event_ics = self._required_str(args, "event_ics")
            if args.get("if_none_match_star") is not True:
                raise _error(
                    ErrorCode.TOOL_DENIED,
                    "calendar.create exige if_none_match_star=true "
                    "(criação com If-None-Match: *, §9)",
                )
            outcome = self._connector.create(
                self._target,
                uid,
                event_ics.encode("utf-8"),
                if_none_match_star=True,
            )
            return {"outcome": outcome.value}
        if name == "calendar.update":
            uid = self._required_str(args, "uid")
            href = self._required_str(args, "href")
            event_ics = self._required_str(args, "event_ics")
            etag = self._required_str(args, "if_match_etag")
            outcome = self._connector.update(
                self._target,
                uid,
                href,
                event_ics.encode("utf-8"),
                if_match_etag=etag,
            )
            return {"outcome": outcome.value}
        if name == "calendar.delete":
            uid = self._required_str(args, "uid")
            href = self._required_str(args, "href")
            etag = self._required_str(args, "if_match_etag")
            outcome = self._connector.delete(
                self._target, uid, href, if_match_etag=etag
            )
            return {"outcome": outcome.value}
        raise _error(
            ErrorCode.TOOL_DENIED,
            f"ferramenta {name!r} não está na allowlist MCP do sync de "
            "calendário (§10)",
        )

    @staticmethod
    def _required_str(args: dict[str, Any], key: str) -> str:
        value = args.get(key)
        if not isinstance(value, str) or not value.strip():
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                f"argumento {key!r} (ID/precondição) é obrigatório (§9)",
            )
        return value


__all__ = [
    "CONNECTOR_ADMISSION",
    "CaldavConfig",
    "CaldavConnector",
    "ConnectorError",
    "DEFAULT_SYNC_TIMEOUT_S",
    "GoogleCalendarConnector",
    "McpCalendarAdapter",
    "RemoteOpKind",
    "SyncTransport",
    "build_calendar_connector",
    "connector_admission",
    "make_urllib_transport",
    "parse_multistatus",
]
