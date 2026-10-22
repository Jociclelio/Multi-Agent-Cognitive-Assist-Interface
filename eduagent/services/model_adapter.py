"""Adaptador de geração e servidor loopback do modelo (mapa §3.1).

Contrato do mapa §3.1: adaptador ``generate(messages, schema, sampler,
deadline, seed) -> GenerationResult`` que devolve texto final, contagens,
finish_reason e erro tipado; o pensamento (``reasoning_content``) NÃO é fonte
de evidência e nunca é misturado ao texto final. Servidor loopback com um slot
de geração e fila de quatro pedidos; sem visão.

Runtime obrigatório do candidato (mapa §3.1): fork ``PrismML-Eng/llama.cpp``
(tag candidata ``prism-b10743-adfffbe``). A compatibilidade do stock
llama.cpp não é presumida e a capacidade ``json_schema`` do runtime é
verificada e fixada por hash no ``manifest.json`` — nunca presumida aqui:
o adaptador só envia ``response_format`` se a capacidade fixada estiver
marcada como verificada.

Perfis de sampling publicados (model card Bonsai 2 27B, revisão
``b072e1d3b35a0a630cece372c2127528e0994386``):
- non-thinking: temp 0.7 / top_p 0.80 / top_k 20 / min_p 0.0 (presence 1.5,
  repeat 1.0 conforme o perfil instruct publicado) — primeiro modo a testar;
- thinking: temp 1.0 / top_p 0.95 / top_k 20 / min_p 0.05 — SOMENTE
  comparativo em desenvolvimento (mapa §3.1); o perfil final é congelado no
  manifesto.

Ferramentas são NEGADAS por política (mapa §3.1, gate §13.1): mensagens com
``tool_calls``/papel ``tool`` produzem ``TOOL_DENIED``; o adaptador nunca envia
``tools`` ao runtime.

Sem rede externa: o único acesso é HTTP loopback ao runtime local
(``network_enabled=false``, mapa §3). Implementação apenas com a biblioteca
padrão — nenhuma dependência nova (``uv.lock`` inalterado).
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from concurrent.futures import Future
from dataclasses import dataclass, field
from typing import Any, Sequence

from eduagent.contracts import ErrorCode  # reexportado p/ gates (mapa §4)


class ModelAdapterError(Exception):
    """Erro tipado do caminho do modelo (mapa §4)."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool,
        diagnostic: str = "eduagent/services/model_adapter.py",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.diagnostic = diagnostic

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "retryable": self.retryable,
            "diagnostic": self.diagnostic,
        }


@dataclass(frozen=True)
class Sampler:
    """Parâmetros de sampling enviados ao runtime por pedido."""

    temperature: float
    top_p: float
    top_k: int
    min_p: float
    max_tokens: int = 16384  # default de ensaio do mapa §3 (max_output_tokens)
    presence_penalty: float = 0.0
    repeat_penalty: float = 1.0
    thinking: bool = False


#: Perfil non-thinking publicado (`.7/.8/20/min_p=0`): primeiro modo a testar
#: (mapa §3.1). Presence 1.5 / repeat 1.0 vêm do perfil instruct do model card.
NON_THINKING_SAMPLER = Sampler(
    temperature=0.7,
    top_p=0.80,
    top_k=20,
    min_p=0.0,
    presence_penalty=1.5,
    repeat_penalty=1.0,
    thinking=False,
)

#: Perfil thinking publicado (`1/.95/20/.05`): SOMENTE comparativo em
#: desenvolvimento (mapa §3.1); não é perfil de admissão.
THINKING_SAMPLER = Sampler(
    temperature=1.0,
    top_p=0.95,
    top_k=20,
    min_p=0.05,
    presence_penalty=0.0,
    repeat_penalty=1.0,
    thinking=True,
)


@dataclass(frozen=True)
class RuntimeCapabilities:
    """Capacidades do runtime, VERIFICADAS e fixadas por hash no manifesto.

    ``json_schema`` só pode ser ``True`` após verificação registrada no gate
    (mapa §3.1: capacidade do fork verificada por hash; stock llama.cpp não é
    presumido). Ferramentas são negadas por política, não por capacidade.
    """

    json_schema: bool
    json_schema_evidence: str
    tools_denied: bool = True
    vision: bool = False  # sem visão (mapa §3.1)


@dataclass(frozen=True)
class GenerationResult:
    """Resultado de uma geração (mapa §3.1).

    ``text`` é o texto final; ``thinking`` carrega o ``reasoning_content``
    separado — não é evidência e não entra no texto final.
    """

    text: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    thinking: str | None
    model_id: str
    seed: int | None
    sampler: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


_ALLOWED_ROLES = frozenset({"system", "user", "assistant"})


def _validate_messages(messages: Sequence[dict[str, Any]]) -> None:
    """Valida papéis e nega ferramentas (mapa §3.1: ferramentas negadas)."""
    if not messages:
        raise ModelAdapterError(
            ErrorCode.SCHEMA_INVALID,
            "Lista de mensagens vazia.",
            retryable=False,
        )
    for i, msg in enumerate(messages):
        role = msg.get("role")
        # Ferramentas negadas por política (mapa §3.1): papel 'tool' OU
        # qualquer 'tool_calls' no payload — inclusive sob papel permitido
        # (payload externo não muda papel/permissões; achado F1 da revisão
        # da task 002, absorvido nos contratos da task 003).
        if role == "tool" or "tool_calls" in msg:
            raise ModelAdapterError(
                ErrorCode.TOOL_DENIED,
                f"Ferramentas são negadas nesta etapa (mapa §3.1); "
                f"mensagem {i} com papel '{role}' ou 'tool_calls'.",
                retryable=False,
            )
        if role not in _ALLOWED_ROLES:
            raise ModelAdapterError(
                ErrorCode.SCHEMA_INVALID,
                f"Papel de mensagem inválido na posição {i}: {role!r}.",
                retryable=False,
            )


class ModelAdapter:
    """Adaptador síncrono para o servidor loopback do runtime fixado."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8079/v1",
        model_id: str = "bonsai2-ptq1-0",
        capabilities: RuntimeCapabilities | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.capabilities = capabilities or RuntimeCapabilities(
            json_schema=False,
            json_schema_evidence="não verificada — response_format não enviado",
        )

    # -- contrato do mapa §3.1 ------------------------------------------
    def generate(
        self,
        messages: Sequence[dict[str, Any]],
        schema: dict[str, Any] | None,
        sampler: Sampler,
        deadline: float,
        seed: int | None,
    ) -> GenerationResult:
        """Gera uma resposta; ``deadline`` em segundos; ``seed`` fixa o RNG.

        Levanta ``ModelAdapterError`` tipado em falhas (mapa §3.1/§4).
        """
        _validate_messages(messages)
        if deadline <= 0:
            raise ModelAdapterError(
                ErrorCode.TIMEOUT,
                "Deadline expirado antes da requisição.",
                retryable=True,
            )
        if schema is not None:
            if not isinstance(schema, dict):
                raise ModelAdapterError(
                    ErrorCode.SCHEMA_INVALID,
                    "Schema deve ser um objeto JSON Schema (dict).",
                    retryable=False,
                )
            if not self.capabilities.json_schema:
                raise ModelAdapterError(
                    ErrorCode.SCHEMA_INVALID,
                    "Capacidade json_schema não verificada/fixada para este "
                    "runtime; parse/schema/política permanecem obrigatórios "
                    "(mapa §3.1).",
                    retryable=False,
                )

        body: dict[str, Any] = {
            "model": self.model_id,
            "messages": list(messages),
            "stream": False,
            "max_tokens": sampler.max_tokens,
            "temperature": sampler.temperature,
            "top_p": sampler.top_p,
            "top_k": sampler.top_k,
            "min_p": sampler.min_p,
            "presence_penalty": sampler.presence_penalty,
            "repeat_penalty": sampler.repeat_penalty,
            "chat_template_kwargs": {"enable_thinking": sampler.thinking},
        }
        if seed is not None:
            body["seed"] = int(seed)
        if schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "eduagent_output", "schema": schema},
            }

        started = time.monotonic()
        data = self._post("/chat/completions", body, deadline)
        elapsed = time.monotonic() - started

        try:
            choice = data["choices"][0]
            message = choice["message"]
            usage = data.get("usage", {}) or {}
            result = GenerationResult(
                text=message.get("content") or "",
                finish_reason=str(choice.get("finish_reason")),
                prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
                completion_tokens=int(usage.get("completion_tokens", 0) or 0),
                thinking=message.get("reasoning_content"),
                model_id=str(data.get("model", self.model_id)),
                seed=seed,
                sampler={
                    "temperature": sampler.temperature,
                    "top_p": sampler.top_p,
                    "top_k": sampler.top_k,
                    "min_p": sampler.min_p,
                    "presence_penalty": sampler.presence_penalty,
                    "repeat_penalty": sampler.repeat_penalty,
                    "thinking": sampler.thinking,
                    "max_tokens": sampler.max_tokens,
                    "elapsed_s": round(elapsed, 3),
                },
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelAdapterError(
                ErrorCode.INTERNAL_FAILURE,
                f"Resposta do runtime em formato inesperado: {exc!r}",
                retryable=True,
            ) from exc

        # Política de saída parcial: texto vazio não é aprovado silenciosamente.
        if not result.text.strip():
            raise ModelAdapterError(
                ErrorCode.INTERNAL_FAILURE,
                "Resposta sem texto final (texto vazio não é aprovado "
                "silenciosamente; mapa §12).",
                retryable=True,
            )
        return result

    # -- transporte -------------------------------------------------------
    def _post(self, path: str, body: dict[str, Any], deadline: float) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        payload = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=deadline) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:2000]
            finally:
                exc.close()
            code = ErrorCode.MODEL_NOT_ADMITTED if exc.code == 503 else ErrorCode.INTERNAL_FAILURE
            raise ModelAdapterError(
                code,
                f"Runtime respondeu HTTP {exc.code}: {detail}",
                retryable=exc.code in (429, 500, 502, 503, 504),
            ) from exc
        except urllib.error.URLError as exc:
            raise ModelAdapterError(
                ErrorCode.INTERNAL_FAILURE,
                f"Falha de conexão com o runtime loopback: {exc.reason}",
                retryable=True,
            ) from exc
        except TimeoutError as exc:
            raise ModelAdapterError(
                ErrorCode.TIMEOUT,
                f"Deadline de {deadline}s excedido na geração.",
                retryable=True,
            ) from exc


class LoopbackGenerationServer:
    """Servidor loopback lógico: UM slot de geração e fila de QUATRO pedidos.

    Pedidos além do slot + fila são recusados com ``RESOURCE_LIMIT`` (mapa
    §3.1). A execução em si é feita por um ``ModelAdapter`` injetado (real nos
    gates; falso determinístico em testes de agendamento).
    """

    def __init__(self, adapter: ModelAdapter | Any, queue_size: int = 4) -> None:
        if queue_size < 1:
            raise ValueError("queue_size deve ser >= 1")
        self._adapter = adapter
        self._queue_size = queue_size
        self._cv = threading.Condition()
        # Cada item carrega o instante de enqueue (monotônico) para medir a
        # espera de fila do span ``queue`` do trace local (mapa §12, task 015).
        self._queue: deque[
            tuple[Future[tuple[GenerationResult, dict[str, Any]]], dict[str, Any], float]
        ] = deque()
        self._busy = False
        self._closed = False
        self._worker = threading.Thread(
            target=self._run, name="eduagent-loopback-server", daemon=True
        )
        self._worker.start()

    def submit(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        schema: dict[str, Any] | None,
        sampler: Sampler,
        deadline: float,
        seed: int | None,
    ) -> Future[tuple[GenerationResult, str]]:
        """Enfileira um pedido; recusa com ``RESOURCE_LIMIT`` se a fila encher."""
        with self._cv:
            if self._closed:
                raise ModelAdapterError(
                    ErrorCode.INTERNAL_FAILURE,
                    "Servidor loopback encerrado.",
                    retryable=False,
                )
            in_flight = len(self._queue) + (1 if self._busy else 0)
            if in_flight >= 1 + self._queue_size:
                raise ModelAdapterError(
                    ErrorCode.RESOURCE_LIMIT,
                    f"Servidor loopback saturado (1 slot + {self._queue_size} "
                    "pedidos em fila); mapa §3.1.",
                    retryable=True,
                )
            future: Future[tuple[GenerationResult, dict[str, Any]]] = Future()
            self._queue.append(
                (
                    future,
                    {
                        "messages": list(messages),
                        "schema": schema,
                        "sampler": sampler,
                        "deadline": deadline,
                        "seed": seed,
                    },
                    time.monotonic(),
                )
            )
            self._cv.notify_all()
            return future

    def close(self) -> None:
        with self._cv:
            self._closed = True
            self._cv.notify_all()

    def _run(self) -> None:
        while True:
            with self._cv:
                while not self._queue and not self._closed:
                    self._cv.wait()
                if self._closed and not self._queue:
                    return
                future, request, enqueued_at = self._queue.popleft()
                started = time.monotonic()
                self._busy = True
            try:
                result = self._adapter.generate(**request)
                # Metadados de tempo do span fila/LLM (mapa §12): espera na
                # fila (enqueue → início da execução) e tempo ativo do slot.
                future.set_result(
                    (
                        result,
                        {
                            "queue_s": max(0.0, started - enqueued_at),
                            "active_s": max(0.0, time.monotonic() - started),
                        },
                    )
                )
            except BaseException as exc:  # propaga erro tipado ao chamador
                future.set_exception(exc)
            finally:
                with self._cv:
                    self._busy = False
                    self._cv.notify_all()
