"""Conector de curadoria web (mapa normativo §6 — "Curadoria web opcional";
§10 — rota ``curate`` e tabela ``web.search/fetch``).

Contrato implementado aqui (§6, textual):

- interface ``search(query, language, max_results) -> candidates`` e
  ``fetch(url) -> resource``;
- até **5 candidatos** e **3 fetches** por consulta, ``fetch`` com
  ``10 s`` de timeout e ``5 MiB`` de corpo, **dois redirects com
  revalidação** (cada hop revalida destino/DNS com
  ``policy.assert_public_url``/``assert_redirect_target`` — §10);
- estados ``metadata_only/text_read/transcript_read/unavailable`` com URL
  final, data (``captured_at``), hash SHA-256 e fonte;
- **vídeo sem transcrição só pode ser recomendado por metadados, nunca
  resumido** — conteúdo ``video/*``/``audio/*`` é sempre ``metadata_only``;
- **conector de busca**: questão aberta do plano 04 — NÃO decidida nesta
  entrega. Nenhum backend de busca é implementado nem admitido; sem ele,
  ``search`` recusa ``CONNECTOR_DISABLED`` e a rota ``curate`` do grafo
  permanece desabilitada (``network_gate`` + ``web_search``, §6);
- **cache offline é marcado com data, nunca fingido como consulta atual**:
  entrada de cache devolve ``cached=True``, ``source="cache"`` e o
  ``captured_at`` original — nunca a data da consulta.

Segurança (§10, herdada da task 014 e revalidada aqui em cada fetch):
esquema http(s), sem credenciais na URL, host que resolve SOMENTE para IPs
públicos; redirect revalidado hop a hop (privado/loopback é bloqueado por
código ``TOOL_DENIED`` — ação proibida é negada, nunca convertida em
estado de recurso).

Os limites numéricos deste módulo são **defaults de ensaio** a calibrar
(mapa §1/§3/§6), nunca resultados medidos.
"""

from __future__ import annotations

import base64
import hashlib
import json
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from eduagent.contracts import EduAgentError, ErrorCode
from eduagent.policy import assert_public_url, assert_redirect_target

DIAGNOSTIC = "eduagent/services/web.py"

#: Máximo de candidatos por consulta (§6: "Até 5 candidatos/3 fetches").
MAX_CANDIDATES = 5

#: Máximo de fetches por consulta (§6) — aplicado no grafo (``_MAX_FETCHES``).
MAX_FETCHES = 3

#: Timeout por requisição HTTP em segundos (§6: "10s/5MiB").
DEFAULT_TIMEOUT_S = 10.0

#: Limite de corpo por resposta em bytes (§6: "10s/5MiB").
MAX_BODY_BYTES = 5 * 1024 * 1024

#: Máximo de redirects seguidos (§6: "dois redirects com revalidação").
MAX_REDIRECTS = 2


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


class ResourceState(str, Enum):
    """Estados de acesso do recurso (§6). ``TRANSCRIPT_READ`` só é produzido
    por conector de transcrição admitido — nenhum existe no MVP (questão
    aberta; nenhum comportamento é inventado)."""

    METADATA_ONLY = "metadata_only"
    TEXT_READ = "text_read"
    TRANSCRIPT_READ = "transcript_read"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class WebCandidate:
    """Candidato de busca (§6). A fonte do candidato é registrada — candidatos
    nunca aparecem sem origem rotulada."""

    url: str
    title: str = ""
    snippet: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "source": self.source,
        }


@dataclass(frozen=True)
class WebResource:
    """Recurso obtido por ``fetch`` (§6): estado, URL final, data/hash e
    fonte. ``cached=True`` marca leitura de cache offline — com o
    ``captured_at`` ORIGINAL, nunca como consulta atual."""

    url: str
    state: ResourceState
    captured_at: datetime
    hash: str | None = None
    source: str = "network"
    content_type: str | None = None
    text: str | None = None
    cached: bool = False
    reason: str = ""
    redirect_chain: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "state": self.state.value,
            "captured_at": self.captured_at.isoformat(),
            "hash": self.hash,
            "source": self.source,
            "content_type": self.content_type,
            "text": self.text,
            "cached": self.cached,
            "reason": self.reason,
            "redirect_chain": list(self.redirect_chain),
        }


#: Transporte HTTP injetável: ``(url, timeout_s) -> (status, headers, body)``.
#: Levanta ``TimeoutError`` em timeout e ``ConnectionError``/``OSError`` em
#: falha de rede. A invalidação de destino (§10) fica FORA do transporte —
#: nenhuma camada injetável burla a barreira de IP privado/loopback.
Transport = Callable[[str, float], tuple[int, Mapping[str, str], bytes]]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Desativa o auto-follow do urllib: o laço de redirects é do conector,
    com revalidação de cada hop (§6/§10)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def urllib_transport(url: str, timeout_s: float) -> tuple[int, Mapping[str, str], bytes]:
    """Transporte padrão (urllib): devolve ``(status, headers, body)`` para
    qualquer status HTTP (2xx/3xx/4xx/5xx); erros de rede propagam
    ``TimeoutError``/``OSError``. Usado apenas quando nenhum transporte é
    injetado — os testes usam transporte falso, sem rede real."""
    request = urllib.request.Request(url, headers={"User-Agent": "EduAgent-OS/0.1"})
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=timeout_s) as response:
            return int(response.status), dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), dict(exc.headers or {}), exc.read() or b""


def _content_type_of(headers: Mapping[str, str]) -> str:
    return str(headers.get("Content-Type") or headers.get("content-type") or "")


def _state_for(content_type: str) -> ResourceState:
    """Estado por tipo de conteúdo (§6): texto legível é ``text_read``;
    ``video/*``/``audio/*`` é SEMPRE ``metadata_only`` — vídeo sem
    transcrição só pode ser recomendado por metadados, nunca resumido.
    Demais tipos (binários desconhecidos) não são lidos como texto."""
    base = content_type.split(";", 1)[0].strip().lower()
    if base.startswith(("video/", "audio/")):
        return ResourceState.METADATA_ONLY
    if base.startswith("text/") or base in {
        "application/json",
        "application/xml",
        "application/xhtml+xml",
    }:
        return ResourceState.TEXT_READ
    return ResourceState.METADATA_ONLY


class WebResourceCache:
    """Cache offline de recursos (§6): "Cache offline é marcado com data, não
    fingido como consulta atual". Cada entrada guarda o dict do recurso e o
    corpo; a leitura devolve SEMPRE ``cached=True``, ``source="cache"`` e o
    ``captured_at`` original da captura."""

    def __init__(self, directory: Path | str) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def put(self, url: str, resource: dict[str, Any], body: bytes) -> None:
        entry = dict(resource)
        entry["body"] = base64.b64encode(body).decode("ascii")
        path = self._dir / f"{self._key(url)}.json"
        path.write_text(
            json.dumps(entry, ensure_ascii=False), encoding="utf-8"
        )

    def get(self, url: str) -> dict[str, Any] | None:
        path = self._dir / f"{self._key(url)}.json"
        if not path.is_file():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        body = base64.b64decode(str(entry.pop("body", "")) or b"")
        entry["body_bytes"] = body
        return entry


class WebFetchConnector:
    """Conector de fetch HTTP (§6/§10) com busca DESABILITADA.

    A questão aberta "qual conector de busca" NÃO é decidida nesta entrega:
    nenhum backend de busca é implementado/admitido — ``search`` recusa
    ``CONNECTOR_DISABLED``. O conector de fetch existe para ser admitido
    INDIVIDUALMENTE (contratos + testes de falha de rede: timeout, redirect
    malicioso, resposta inválida) e para tornar a rota ``curate`` operável
    quando um backend de busca for escolhido em decisão própria.
    """

    def __init__(
        self,
        *,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        max_body_bytes: int = MAX_BODY_BYTES,
        max_redirects: int = MAX_REDIRECTS,
        max_candidates: int = MAX_CANDIDATES,
        transport: Transport | None = None,
        cache_dir: Path | str | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if timeout_s <= 0 or max_body_bytes <= 0 or max_redirects < 0:
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                "limites do conector web devem ser positivos",
            )
        if not 1 <= max_candidates <= MAX_CANDIDATES:
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                "max_candidates deve ficar entre 1 e "
                f"{MAX_CANDIDATES} (limite normativo §6)",
            )
        self._timeout_s = float(timeout_s)
        self._max_body_bytes = int(max_body_bytes)
        self._max_redirects = int(max_redirects)
        self._max_candidates = int(max_candidates)
        self._transport = transport or urllib_transport
        self._cache = (
            WebResourceCache(cache_dir) if cache_dir is not None else None
        )
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    # -- search (§6): sem conector de busca, CONNECTOR_DISABLED ---------------

    def search(
        self,
        query: str,
        language: str = "pt",
        max_results: int = MAX_CANDIDATES,
    ) -> list[WebCandidate]:
        """Interface normativa (§6). Nenhum conector de busca é admitido —
        questão aberta do plano, não decidida: recusa tipada
        ``CONNECTOR_DISABLED`` (convenção do §12: recurso/conector
        indisponível, código ``RESOURCE_LIMIT`` com prefixo no ``message``)."""
        raise _error(
            ErrorCode.RESOURCE_LIMIT,
            "CONNECTOR_DISABLED: nenhum conector de busca configurado ou "
            "admitido (mapa §6 — questão aberta, não decidida nesta entrega; "
            "sem ele a rota curate permanece desabilitada)",
            retryable=True,
        )

    # -- fetch (§6/§10) --------------------------------------------------------

    def fetch(self, url: str) -> dict[str, Any]:
        """Busca o recurso em ``url`` (§6): valida destino por código (§10),
        segue até dois redirects com revalidação de cada hop, limita corpo a
        5 MiB e timeout a 10 s (defaults de ensaio). Falha de rede/resposta
        inválida → estado ``unavailable`` (com fallback de cache marcado com
        a data original); destino proibido (IP privado/loopback, esquema,
        credenciais na URL) é NEGADO por código (``TOOL_DENIED``, §10)."""
        # §10: destino validado ANTES de qualquer conexão — a validação
        # resolve DNS e bloqueia privado/loopback por código.
        assert_public_url(url)
        try:
            resource = self._fetch_hops(url)
        except EduAgentError:
            raise
        except (TimeoutError, ConnectionError, OSError) as exc:
            return self._unavailable(
                url,
                f"falha de rede ({type(exc).__name__}): {exc}",
            )
        self._store_cache(url, resource)
        return resource

    def _fetch_hops(self, url: str) -> dict[str, Any]:
        chain: list[str] = []
        current = url
        for hop in range(self._max_redirects + 1):
            try:
                status, headers, body = self._transport(
                    current, self._timeout_s
                )
            except (TimeoutError, ConnectionError, OSError) as exc:
                return self._unavailable(
                    current,
                    f"falha de rede no hop {hop} "
                    f"({type(exc).__name__}): {exc}",
                    fallback_url=url,
                    chain=chain,
                )
            if 300 <= status < 400:
                location = ""
                for key in ("Location", "location"):
                    if key in headers:
                        location = str(headers[key])
                        break
                if not location:
                    return self._unavailable(
                        current,
                        f"redirect HTTP {status} sem Location",
                        fallback_url=url,
                        chain=chain,
                    )
                if hop == self._max_redirects:
                    return self._unavailable(
                        current,
                        "mais de "
                        f"{self._max_redirects} redirects (limite normativo "
                        "§6, default de ensaio)",
                        fallback_url=url,
                        chain=chain,
                    )
                # §6/§10: CADA hop de redirect é revalidado por código —
                # destino privado/loopback é negado (TOOL_DENIED propaga).
                nxt = assert_redirect_target(current, location)
                chain.append(nxt)
                current = nxt
                continue
            if not 200 <= status < 300:
                return self._unavailable(
                    current,
                    f"resposta HTTP {status}",
                    fallback_url=url,
                    chain=chain,
                )
            return self._build_resource(current, headers, body, chain)
        # Inalcançável (o laço retorna sempre), mantido por robustez.
        return self._unavailable(url, "laço de redirects exaurido")

    def _build_resource(
        self,
        final_url: str,
        headers: Mapping[str, str],
        body: bytes,
        chain: list[str],
    ) -> dict[str, Any]:
        if len(body) > self._max_body_bytes:
            return self._unavailable(
                final_url,
                f"corpo excede {self._max_body_bytes} bytes "
                "(limite normativo §6, default de ensaio)",
                chain=chain,
            )
        content_type = _content_type_of(headers)
        state = _state_for(content_type)
        text: str | None = None
        if state is ResourceState.TEXT_READ:
            charset = "utf-8"
            for part in content_type.split(";")[1:]:
                name, _, value = part.strip().partition("=")
                if name.strip().lower() == "charset" and value.strip():
                    charset = value.strip().strip('"')
            text = body.decode(charset, errors="replace")
        resource = WebResource(
            url=final_url,
            state=state,
            captured_at=self._clock(),
            hash=hashlib.sha256(body).hexdigest(),
            source="network",
            content_type=content_type or None,
            text=text,
            redirect_chain=tuple(chain),
        )
        return resource.to_dict()

    def _unavailable(
        self,
        url: str,
        reason: str,
        *,
        fallback_url: str | None = None,
        chain: list[str] | None = None,
    ) -> dict[str, Any]:
        # §6: estado ``unavailable`` com URL, data e fonte — falha explícita,
        # nunca saída parcial silenciosa. Cache offline (se houver) entra
        # MARCADO com a data original, nunca como consulta atual.
        if self._cache is not None:
            cached = self._cache.get(fallback_url or url)
            if cached is not None:
                body = cached.pop("body_bytes", b"")
                entry = dict(cached)
                entry["cached"] = True
                entry["source"] = "cache"
                entry["reason"] = (
                    f"cache offline (consulta atual falhou: {reason})"
                )
                if entry.get("redirect_chain") is None and chain:
                    entry["redirect_chain"] = list(chain)
                if body and not entry.get("hash"):
                    entry["hash"] = hashlib.sha256(body).hexdigest()
                return entry
        resource = WebResource(
            url=url,
            state=ResourceState.UNAVAILABLE,
            captured_at=self._clock(),
            source="network",
            reason=reason,
            redirect_chain=tuple(chain or ()),
        )
        return resource.to_dict()

    def _store_cache(self, url: str, resource: dict[str, Any]) -> None:
        """Cacheia apenas leituras bem-sucedidas (§6); ``unavailable`` não é
        cacheado — cache vazio não vira conteúdo."""
        if self._cache is None or resource.get("state") == (
            ResourceState.UNAVAILABLE.value
        ):
            return
        text = resource.get("text")
        body = text.encode("utf-8") if isinstance(text, str) else b""
        self._cache.put(url, resource, body)


__all__ = [
    "DEFAULT_TIMEOUT_S",
    "MAX_BODY_BYTES",
    "MAX_CANDIDATES",
    "MAX_FETCHES",
    "MAX_REDIRECTS",
    "ResourceState",
    "Transport",
    "WebCandidate",
    "WebFetchConnector",
    "WebResource",
    "WebResourceCache",
    "urllib_transport",
]
