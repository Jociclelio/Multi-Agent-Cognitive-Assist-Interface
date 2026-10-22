"""Política de ferramentas, limites do turno e barreiras de segurança
(mapa §10 — tabela de ferramentas e segurança; §12 — limites).

Responsabilidades desta camada (todas por código, nunca interpretadas de
payload — mapa §4/§10):

- **Limites (§12)**: antes de cada nó/tool/geração conferir cancelamento,
  deadline e budget; reparo consome chamada e contador; ao esgotar, erro
  tipado (nunca saída parcial silenciosamente aprovada); ``RESOURCE_LIMIT``
  quando a fila de geração enche.
- **Fila serial de geração (§10)**: toda geração LLM do grafo passa pelo
  servidor loopback da task 002 (um slot + fila de quatro, §3.1).
- **Tabela de ferramentas (§10)**: quem pode proposer (papel atribuído pelo
  dispatcher, nunca lido do payload) e pré-condições; JSON correto para ação
  proibida é negado por código (``TOOL_DENIED``); nenhum agente recebe shell
  genérico nem escrita direta no DB (as únicas escritas são
  ``domain.commit``/``calendar.apply`` do serviço determinístico).
- **Segurança de paths (§10)**: resolver paths/ownership e bloquear
  traversal/symlink escapes.
- **Segurança de fetch (§10)**: bloquear IP privado/loopback e revalidar
  redirects/DNS — usada pelo conector web admitido na task 016.

Nota de escopo: a negação ``CONNECTOR_DISABLED`` usa ``RESOURCE_LIMIT``
(recurso/conector indisponível, exit code 3 do mapa §12) com mensagem
prefixada ``CONNECTOR_DISABLED`` — o enum de códigos do §4 é fechado e não
tem código próprio para conector ausente (mesma convenção de
``calendar.apply`` da task 013, que reporta ``CONNECTOR_DISABLED`` no
``detail``).
"""

from __future__ import annotations

import ipaddress
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from eduagent.contracts import (
    Budgets,
    EduAgentError,
    ErrorCode,
    ToolName,
    TypedError,
    SenderRole,
    validate_tool_request,
)
from eduagent.services.model_adapter import (
    GenerationResult,
    LoopbackGenerationServer,
    ModelAdapterError,
    Sampler,
)

DIAGNOSTIC = "eduagent/policy.py"


def _error(
    code: ErrorCode,
    message: str,
    *,
    diagnostic: str = DIAGNOSTIC,
    retryable: bool | None = None,
) -> EduAgentError:
    return EduAgentError(
        code, message, retryable=retryable, diagnostic=diagnostic
    )


def typed_error_of(exc: EduAgentError | ModelAdapterError) -> TypedError:
    """Erro tipado uniforme para ``EduAgentError`` e ``ModelAdapterError``."""
    if isinstance(exc, EduAgentError):
        return exc.error
    return TypedError.of(
        code=exc.code,
        message=exc.message,
        retryable=exc.retryable,
        diagnostic=exc.diagnostic,
    )


# ---------------------------------------------------------------------------
# Limites do turno (mapa §12)
# ---------------------------------------------------------------------------


class TurnLimits:
    """Orçamento do turno (mapa §12): conferido **antes** de cada
    nó/tool/geração. Reparo consome chamada e contador. Ao esgotar: erro
    tipado — o terminal carrega os artefatos já válidos, nunca saída parcial
    silenciosamente aprovada.

    ``deadline`` é o instante limite do turno (``active_deadline_s`` a partir
    da abertura, mapa §3); ``None`` significa sem deadline configurado —
    unknown fica ``None`` nas métricas, nunca zero (§12). Contadores começam
    nos máximos da config; valores da config são defaults de ensaio a
    calibrar (mapa §1/§3), não resultados medidos.
    """

    def __init__(
        self,
        *,
        max_llm_calls: int,
        max_tool_calls: int,
        max_graph_steps: int,
        max_repairs_total: int,
        deadline: datetime | None = None,
        clock: Any = None,
    ) -> None:
        if min(
            max_llm_calls,
            max_tool_calls,
            max_graph_steps,
            max_repairs_total,
        ) < 0:
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                "limites do turno não podem ser negativos",
            )
        if deadline is not None and deadline.tzinfo is None:
            raise _error(
                ErrorCode.SCHEMA_INVALID, "deadline do turno exige zona (§4)"
            )
        self.max_llm_calls = int(max_llm_calls)
        self.max_tool_calls = int(max_tool_calls)
        self.max_graph_steps = int(max_graph_steps)
        self.max_repairs_total = int(max_repairs_total)
        self.deadline = deadline
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.llm_calls_remaining = int(max_llm_calls)
        self.tool_calls_remaining = int(max_tool_calls)
        self.repairs_remaining = int(max_repairs_total)
        self.steps_used = 0

    # -- conferências (§12: antes de cada node/tool/geração) -----------------

    def begin_step(
        self, *, cancel_requested: bool = False, step: str = ""
    ) -> None:
        """Abre um passo do grafo: cancelamento → deadline → steps (§12,
        nessa ordem). Cancelamento tem prioridade sobre tudo — o terminal é
        ``CANCELLED``, nunca um erro de budget de um turno pedido para parar.
        """
        if cancel_requested:
            raise _error(
                ErrorCode.CANCELLED,
                "turno cancelado antes do passo "
                f"{step!r}: nada além de efeitos já iniciados é executado",
            )
        if self.steps_used >= self.max_graph_steps:
            raise _error(
                ErrorCode.RESOURCE_LIMIT,
                "limite de passos do grafo esgotado "
                f"({self.max_graph_steps}; default de ensaio, mapa §3)",
            )
        self.steps_used += 1
        self.check_deadline()

    def check_deadline(self) -> None:
        if self.deadline is not None and self._clock() >= self.deadline:
            raise _error(
                ErrorCode.TIMEOUT,
                "deadline ativo do turno esgotado (mapa §12); artefatos já "
                "válidos são preservados e nada parcial é publicado",
            )

    def check_cancelled(self, cancel_requested: bool) -> None:
        if cancel_requested:
            raise _error(
                ErrorCode.CANCELLED,
                "turno cancelado; nenhuma nova ação é executada",
            )

    # -- consumo de orçamento -------------------------------------------------

    def consume_llm(self, count: int = 1) -> None:
        """Geração LLM: consome chamada e contador (§12). Fila/budget cheios
        respondem ``RESOURCE_LIMIT``."""
        if count <= 0:
            raise _error(ErrorCode.SCHEMA_INVALID, "consumo de LLM deve ser > 0")
        if self.llm_calls_remaining < count:
            raise _error(
                ErrorCode.RESOURCE_LIMIT,
                "orçamento de chamadas LLM do turno esgotado "
                f"({self.max_llm_calls}; default de ensaio, mapa §3)",
            )
        self.llm_calls_remaining -= count

    def consume_tool(self, count: int = 1) -> None:
        if count <= 0:
            raise _error(
                ErrorCode.SCHEMA_INVALID, "consumo de tools deve ser > 0"
            )
        if self.tool_calls_remaining < count:
            raise _error(
                ErrorCode.RESOURCE_LIMIT,
                "orçamento de chamadas de ferramentas do turno esgotado "
                f"({self.max_tool_calls}; default de ensaio, mapa §3)",
            )
        self.tool_calls_remaining -= count

    def consume_repair(self) -> None:
        """Reparo consome chamada (de LLM) e contador próprio (§12)."""
        if self.repairs_remaining < 1:
            raise _error(
                ErrorCode.RESOURCE_LIMIT,
                "orçamento de reparos do turno esgotado "
                f"({self.max_repairs_total}; default de ensaio, mapa §3)",
            )
        self.repairs_remaining -= 1
        self.consume_llm()

    # -- projeção para o contrato GraphState (mapa §4) ------------------------

    def budgets(self) -> Budgets:
        return Budgets(
            llm_calls_remaining=self.llm_calls_remaining,
            tool_calls_remaining=self.tool_calls_remaining,
            tokens_remaining=None,  # desconhecido: null, nunca zero (§12)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "llm_calls_remaining": self.llm_calls_remaining,
            "tool_calls_remaining": self.tool_calls_remaining,
            "repairs_remaining": self.repairs_remaining,
            "steps_used": self.steps_used,
        }


# ---------------------------------------------------------------------------
# Fila serial de geração (mapa §10: "geração usa fila serial")
# ---------------------------------------------------------------------------


class GenerationGate:
    """Porta única de geração do grafo: TODA geração LLM passa pelo servidor
    loopback da task 002 (um slot + fila de quatro, mapa §3.1) — fila cheia
    responde ``RESOURCE_LIMIT`` (§12), nunca seguida turna.

    ``limits.consume_llm()`` é debitado ANTES do submit: estourar orçamento é
    recusa tipada sem enfileirar pedido.
    """

    def __init__(
        self,
        backend: Any,
        *,
        queue_size: int = 4,
        llm_timeout_s: float = 90,
        clock: Any = None,
    ) -> None:
        self._server = LoopbackGenerationServer(backend, queue_size=queue_size)
        self._llm_timeout_s = float(llm_timeout_s)
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def generate(
        self,
        *,
        limits: TurnLimits,
        messages: Sequence[Mapping[str, Any]],
        schema: Mapping[str, Any] | None,
        sampler: Sampler,
        seed: int | None,
        deadline: datetime | None = None,
    ) -> GenerationResult:
        """Geração serial: consome orçamento, respeita deadline do turno e
        devolve o ``GenerationResult`` do adaptador (erro tipado propagado)."""
        limits.consume_llm()
        limits.check_deadline()
        if deadline is not None and deadline.tzinfo is None:
            raise _error(
                ErrorCode.SCHEMA_INVALID, "deadline de geração exige zona"
            )
        try:
            future = self._server.submit(
                messages=[dict(m) for m in messages],
                schema=dict(schema) if schema is not None else None,
                sampler=sampler,
                deadline=(deadline or self._clock()).timestamp(),
                seed=seed,
            )
        except ModelAdapterError as exc:
            raise EduAgentError(
                exc.code,
                exc.message,
                retryable=exc.retryable,
                diagnostic=exc.diagnostic,
            ) from exc
        remaining = self._llm_timeout_s
        if deadline is not None:
            remaining = max(0.0, (deadline - self._clock()).total_seconds())
        try:
            result, _ = future.result(timeout=remaining)
        except ModelAdapterError as exc:
            raise EduAgentError(
                exc.code,
                exc.message,
                retryable=exc.retryable,
                diagnostic=exc.diagnostic,
            ) from exc
        except TimeoutError as exc:
            raise _error(
                ErrorCode.TIMEOUT,
                "geração excedeu o deadline do turno (mapa §12)",
            ) from exc
        return result

    def close(self) -> None:
        self._server.close()


# ---------------------------------------------------------------------------
# Tabela de ferramentas (mapa §10)
# ---------------------------------------------------------------------------


def require_tool(
    tool: ToolName,
    sender_role: SenderRole,
    *,
    network_enabled: bool = False,
    connector_available: bool | None = None,
    limits: TurnLimits | None = None,
) -> None:
    """Aplica a tabela §10 ANTES da chamada: papel proponente (atribuído pelo
    dispatcher — payload não muda permissões, §4) e pré-condições.

    ``web.search``/``web.fetch`` exigem rede habilitada E conector admitido;
    sem eles, recusa ``CONNECTOR_DISABLED`` (§6/§9; ver nota de escopo do
    módulo). ``limits`` é consumido como chamada de ferramenta (§12).
    """
    validate_tool_request(tool, sender_role)  # TOOL_DENIED por código (§10)
    if tool in (ToolName.WEB_SEARCH, ToolName.WEB_FETCH):
        if not network_enabled or connector_available is not True:
            raise _error(
                ErrorCode.RESOURCE_LIMIT,
                "CONNECTOR_DISABLED: nenhum conector de busca admitido "
                "(rede habilitada e conector configurado são pré-condições "
                "da tabela §10; §6/§9)",
                retryable=True,
            )
    if limits is not None:
        limits.consume_tool()


# ---------------------------------------------------------------------------
# Segurança de paths (mapa §10: resolver paths/ownership, bloquear
# traversal/symlink escapes)
# ---------------------------------------------------------------------------


def resolve_owned_path(
    data_root: Path | str,
    user_id: str,
    relative: str,
    *,
    must_exist: bool = False,
) -> Path:
    """Resolve ``data_root/<user_id>/<relative>`` de forma segura (§10).

    - canonicaliza o caminho (resolvendo symlinks) e exige que o resultado
      permaneça dentro do diretório do usuário (ownership);
    - ``..`` e symlink que escapem do diretório do usuário são bloqueados
      por código (``TOOL_DENIED`` — ação proibida é negada, nunca
      interpretada);
    - ``relative`` absoluto ou vazio é recusado (o chamador não escolhe
      raiz).
    """
    if not isinstance(relative, str) or not relative or relative.strip() == "":
        raise _error(ErrorCode.SCHEMA_INVALID, "caminho relativo obrigatório")
    if Path(relative).is_absolute():
        raise _error(
            ErrorCode.TOOL_DENIED,
            "caminho absoluto não é aceito: o path é resolvido sob o "
            "diretório do usuário (§10)",
        )
    root = Path(data_root).resolve()
    user_dir = (root / user_id).resolve()
    if user_dir != root and user_dir.parent != root:
        # user_id não pode conter traversal (defesa em profundidade).
        raise _error(
            ErrorCode.TOOL_DENIED, "user_id não resolve para diretório próprio"
        )
    candidate = (user_dir / relative).resolve()
    if candidate != user_dir and user_dir not in candidate.parents:
        raise _error(
            ErrorCode.TOOL_DENIED,
            f"caminho {relative!r} escapa do diretório do usuário "
            "(traversal/symlink bloqueado, §10)",
        )
    if must_exist and not candidate.is_file():
        raise _error(
            ErrorCode.SOURCE_UNRESOLVED,
            f"arquivo {relative!r} não existe no diretório do usuário",
        )
    return candidate


# ---------------------------------------------------------------------------
# Segurança de fetch (mapa §10: bloquear IP privado/loopback, revalidar
# redirects/DNS)
# ---------------------------------------------------------------------------

_ALLOWED_SCHEMES = frozenset({"http", "https"})


def _addr_is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        not ip.is_global
        or ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def assert_public_url(url: str) -> str:
    """Valida destino de fetch (§10): apenas http(s), sem credenciais na URL,
    host que resolve SOMENTE para IPs públicos (privado/loopback/link-local/
    reservado é bloqueado por código). Revalidar DNS a cada hop — chamar de
    novo para cada redirect (revalidação de redirect/DNS, §10)."""
    parts = urlsplit(url)
    if parts.scheme.lower() not in _ALLOWED_SCHEMES:
        raise _error(
            ErrorCode.TOOL_DENIED,
            f"esquema {parts.scheme!r} não permitido para fetch (§10)",
        )
    if parts.username or parts.password:
        raise _error(
            ErrorCode.TOOL_DENIED,
            "credenciais na URL não são permitidas (§10)",
        )
    host = parts.hostname
    if not host:
        raise _error(ErrorCode.TOOL_DENIED, "URL sem host (§10)")
    try:
        infos = socket.getaddrinfo(host, parts.port or (443 if parts.scheme.lower() == "https" else 80), proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise _error(
            ErrorCode.SOURCE_UNRESOLVED,
            f"host {host!r} não resolve (§10)",
        ) from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if _addr_is_blocked(ip):
            raise _error(
                ErrorCode.TOOL_DENIED,
                f"destino {host!r} resolve para IP não público "
                f"({ip}); privado/loopback é bloqueado (§10)",
            )
    return url


def assert_redirect_target(current_url: str, location: str) -> str:
    """Revalida destino de redirect (§10: "dois redirects com revalidação";
    a revalidação de DNS/destino é reaplicada ao alvo resolvido)."""
    parts = urlsplit(current_url)
    if urlsplit(location).scheme:
        target = location
    else:
        base = f"{parts.scheme}://{parts.netloc}"
        if location.startswith("/"):
            target = base + location
        else:
            target = base + "/" + location
    return assert_public_url(target)


__all__ = [
    "GenerationGate",
    "TurnLimits",
    "assert_public_url",
    "assert_redirect_target",
    "require_tool",
    "resolve_owned_path",
    "typed_error_of",
]
