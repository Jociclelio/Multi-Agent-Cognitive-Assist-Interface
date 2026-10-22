"""Trace local por turno (mapa §12): spans de fila/LLM/retrieval/context/
solver/commit/tools e registro operacional do turno.

Contrato implementado (task 015):

- **Spans do §12**: ``queue``, ``llm``, ``retrieval``, ``context``,
  ``solver``, ``commit`` e ``tools`` — abertos pelo grafo em volta dos nós
  (tabela ``SPAN_KIND_BY_NODE``) e, para fila de geração, pelo servidor
  loopback (observador do ``GenerationGate``).
- **Registro operacional**: versões (eduagent/Python/modelo), seed/sampling,
  contagens entrada/raciocínio/saída QUANDO disponíveis, status/truncamento,
  tempo ativo/fila/total, RSS/VRAM e erros tipados do §4.
- **Nada de payload pessoal completo por padrão** (§12): a mensagem do aluno
  é registrada apenas como SHA-256 + tamanho; conteúdo de artefato/documento
  nunca entra no trace (refs ID+versão apenas, §4).
- **Métrica desconhecida é ``null`` com razão, nunca zero** (§12): toda
  métrica não medida é ``{"value": null, "reason": "..."}`` — energia,
  VRAM, custo de API e contagens ausentes seguem essa forma. Nenhum número
  aqui é resultado medido do sistema: é estado operacional do turno local.

O trace é metadado operacional (não incrementa ``domain_revision``, §15.1)
e não entra no estado do grafo nem no checkpoint (refs apenas, §4).
"""

from __future__ import annotations

import hashlib
import json
import platform
import resource
import sys
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

#: Versão do schema do arquivo de trace (evolução local; não é contrato do §4).
TRACE_SCHEMA_VERSION = "1.0"

DIAGNOSTIC = "eduagent/telemetry.py"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def unknown(reason: str) -> dict[str, Any]:
    """Métrica desconhecida: ``null`` com razão, nunca zero (mapa §12)."""
    return {"value": None, "reason": reason}


def unknown_metric(metric: dict[str, Any]) -> bool:
    """True se o valor segue a forma ``null`` com razão deste módulo."""
    return (
        isinstance(metric, dict)
        and metric.get("value") is None
        and isinstance(metric.get("reason"), str)
    )


@dataclass
class SpanRecord:
    """Um span do trace do §12 (categoria + nó do grafo + janela de tempo)."""

    kind: str
    node: str | None
    started_at: str
    ended_at: str | None = None
    active_s: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


#: Spans do §12 (mapa: "spans de fila/LLM/retrieval/context/solver/commit/
#: tools"). A fila (``queue``) não é um nó: é medida pelo servidor loopback
#: entre o enqueue e o início da execução (observador do ``GenerationGate``).
SPAN_KINDS = (
    "queue",
    "llm",
    "retrieval",
    "context",
    "solver",
    "commit",
    "tools",
)

#: Mapeamento nó do grafo → categoria de span do §12. Nós não listados são
#: registrados como ``tools`` com o ``node`` explícito (span informativo, sem
#: alegar categoria que não corresponde). Escolha de organização local do MVP.
SPAN_KIND_BY_NODE: dict[str, str] = {
    # LLM (classificador e turnos com geração)
    "classify": "llm",
    "tutor": "llm",
    "tutor_validate": "llm",
    "answer": "llm",
    # retrieval (leituras independentes do snapshot, §10)
    "curator_retrieve": "retrieval",
    "librarian_retrieve": "retrieval",
    # context (montagem de contexto + snapshot materializado, §7/§15.1)
    "snapshot": "context",
    "context": "context",
    # solver (CP-SAT + verificador independente, §9)
    "solver": "solver",
    "independent_check": "solver",
    # commit (efeitos via commit idempotente, §11)
    "commit_index": "commit",
    "commit_confirmations": "commit",
    "commit_assessment": "commit",
    "commit_approval": "commit",
    "commit_event": "commit",
    "commit_invalidate": "commit",
    "publish_ics": "commit",
    # tools (propostas de ferramenta/execuções sob a tabela §10)
    "ingest_extract": "tools",
    "web_search": "tools",
    "web_fetch": "tools",
    "render_ics": "tools",
}


class TurnTraceRecorder:
    """Recorder de um turno (mapa §12). Criado pelo grafo por invocação;
    nada aqui toca o estado do domínio nem o checkpoint."""

    def __init__(
        self,
        *,
        trace_id: str,
        session_id: str | None = None,
        user_id: str | None = None,
        turn_id: str | None = None,
        message: str | None = None,
        seed: int | None = None,
        sampler: Mapping[str, Any] | None = None,
        model_id: str | None = None,
        clock: Any = None,
        redact: bool = True,
    ) -> None:
        self.trace_id = str(trace_id)
        self.session_id = session_id
        self.user_id = user_id
        self.turn_id = turn_id
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._redact = redact
        self._started_monotonic = _monotonic()
        self.started_at = _utc_now_iso()
        self.finished_at: str | None = None
        self.status: str | None = None
        self.seed = seed
        self.sampler: dict[str, Any] = dict(sampler or {})
        self.model_id = model_id
        self.spans: list[SpanRecord] = []
        self.llm_events: list[dict[str, Any]] = []
        self.queue_s_total: float | None = None
        self.budgets: dict[str, Any] | None = None
        self.errors: list[dict[str, Any]] = []
        self.notes: dict[str, Any] = {}
        self.message_digest: dict[str, Any] | None = None
        if message is not None:
            self.set_message(message)

    # -- contexto ------------------------------------------------------------

    def set_context(
        self,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        turn_id: str | None = None,
        message: str | None = None,
    ) -> None:
        """Preenche identidade desconhecida na criação (turno retomado)."""
        if user_id is not None:
            self.user_id = user_id
        if session_id is not None:
            self.session_id = session_id
        if turn_id is not None:
            self.turn_id = turn_id
        if message is not None:
            self.set_message(message)

    def set_message(self, message: str) -> None:
        """Payload pessoal NÃO é logado por padrão (§12): apenas digest e
        tamanho. Com ``redact=False`` (desenvolvimento explícito) o conteúdo
        ainda não entra aqui — o recorder não guarda texto."""
        text = message or ""
        if self._redact:
            self.message_digest = {
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "length": len(text),
            }
        else:
            self.message_digest = {"length": len(text)}

    # -- spans ---------------------------------------------------------------

    @contextmanager
    def span(
        self, kind: str, *, node: str | None = None, **attributes: Any
    ) -> Iterator[SpanRecord]:
        """Abre um span do §12; ``kind`` fora das categorias é recusado
        (categorias fechadas evitam span inventado)."""
        if kind not in SPAN_KINDS:
            raise ValueError(
                f"span kind desconhecido: {kind!r} (categorias do §12: "
                f"{', '.join(SPAN_KINDS)})"
            )
        record = SpanRecord(
            kind=kind,
            node=node,
            started_at=_utc_now_iso(),
            attributes=dict(attributes),
        )
        started = _monotonic()
        self.spans.append(record)
        try:
            yield record
        finally:
            record.ended_at = _utc_now_iso()
            record.active_s = max(0.0, _monotonic() - started)

    def _null_span(self) -> Any:
        """Context manager nulo quando não há recorder (turno sem trace)."""
        from contextlib import nullcontext

        return nullcontext(None)

    # -- eventos de geração (observador do GenerationGate) -------------------

    def observe_llm(self, event: Mapping[str, Any]) -> None:
        """Evento de geração do servidor loopback: contagens quando o backend
        as disponibiliza; ausente é ``null`` com razão (§12), nunca zero."""
        result = event.get("result")
        error = event.get("error")
        entry: dict[str, Any] = {
            "started_at": _utc_now_iso(),
            "queue_s": (
                float(event["queue_s"])
                if event.get("queue_s") is not None
                else unknown("fila não instrumentada neste pedido")
            ),
            "active_s": (
                float(event["active_s"])
                if event.get("active_s") is not None
                else unknown("tempo ativo não instrumentado neste pedido")
            ),
            "error": (
                {"code": getattr(error, "code", None) and str(error.code),
                 "message": str(error)}
                if error is not None
                else None
            ),
        }
        if result is not None:
            prompt_tokens = getattr(result, "prompt_tokens", None)
            completion_tokens = getattr(result, "completion_tokens", None)
            thinking = getattr(result, "thinking", None)
            finish_reason = getattr(result, "finish_reason", None)
            entry.update(
                {
                    "model_id": getattr(result, "model_id", None),
                    "seed": getattr(result, "seed", None),
                    "finish_reason": finish_reason,
                    "truncated": finish_reason == "length",
                    "input_tokens": (
                        int(prompt_tokens)
                        if prompt_tokens is not None
                        else unknown("backend não reporta contagem de entrada")
                    ),
                    "output_tokens": (
                        int(completion_tokens)
                        if completion_tokens is not None
                        else unknown("backend não reporta contagem de saída")
                    ),
                    # O pensamento não é fonte de evidência (§3.1); contagem
                    # de raciocínio só quando o runtime a reporta.
                    "reasoning_tokens": (
                        unknown("runtime não reporta contagem de raciocínio")
                        if thinking is None
                        else unknown(
                            "runtime reporta texto de raciocínio sem contagem "
                            "de tokens"
                        )
                    ),
                    "thinking_recorded": False,  # conteúdo nunca entra no trace
                }
            )
        else:
            entry.update(
                {
                    "input_tokens": unknown("geração falhou sem contagem"),
                    "output_tokens": unknown("geração falhou sem contagem"),
                    "reasoning_tokens": unknown("geração falhou sem contagem"),
                }
            )
        self.llm_events.append(entry)

    def set_budgets(self, budgets: Mapping[str, Any] | None) -> None:
        self.budgets = dict(budgets) if budgets else None

    def add_error(self, error: Mapping[str, Any]) -> None:
        self.errors.append(dict(error))

    def note(self, key: str, value: Any) -> None:
        self.notes[key] = value

    # -- encerramento --------------------------------------------------------

    def finish(
        self,
        *,
        status: str,
        errors: list[Mapping[str, Any]] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        turn_id: str | None = None,
    ) -> dict[str, Any]:
        self.set_context(
            user_id=user_id, session_id=session_id, turn_id=turn_id
        )
        for error in errors or []:
            self.add_error(error)
        self.status = status
        self.finished_at = _utc_now_iso()
        return self.to_dict()

    # -- métricas derivadas (§12: null com razão, nunca zero) ----------------

    def _aggregate_tokens(self, key: str) -> dict[str, Any]:
        values: list[int] = []
        for event in self.llm_events:
            metric = event.get(key)
            if isinstance(metric, (int, float)):
                values.append(int(metric))
        if not self.llm_events:
            return unknown("nenhuma geração passou pela fila neste turno")
        if not values:
            return unknown(
                "backend não reportou contagens nas gerações do turno"
            )
        return {"value": sum(values), "reason": None}

    def _resource_metrics(self) -> dict[str, Any]:
        # RSS é medido no processo local (ru_maxrss em KiB no Linux); VRAM e
        # energia não têm medidor no processo — null com razão (§12).
        try:
            rss_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except (OSError, ValueError):  # pragma: no cover - plataforma sem rusage
            rss_metric: dict[str, Any] = unknown(
                "ru_maxrss indisponível nesta plataforma"
            )
        else:
            rss_metric = {"value": int(rss_kib), "reason": None}
        return {
            "rss_kib": rss_metric,
            "vram": unknown(
                "runtime CPU local sem medidor de VRAM no processo (mapa §3.1)"
            ),
            "energy": unknown(
                "nenhum medidor de energia disponível no processo local"
            ),
            "cost_api": unknown(
                "nenhum conector pago usado no MVP local (mapa §12: custo de "
                "API apenas se conector pago usado)"
            ),
        }

    def _timing(self) -> dict[str, Any]:
        total_s = max(0.0, _monotonic() - self._started_monotonic)
        active_s = sum(
            span.active_s or 0.0 for span in self.spans if span.kind != "queue"
        )
        queue_events = [
            event["queue_s"]
            for event in self.llm_events
            if isinstance(event.get("queue_s"), (int, float))
        ]
        queue_s = (
            sum(float(q) for q in queue_events)
            if queue_events
            else None
        )
        return {
            "total_s": total_s,
            "active_s_nodes": active_s,
            "queue_s": (
                queue_s
                if queue_s is not None
                else unknown("nenhuma espera de fila instrumentada no turno")
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        """Trace serializável do turno (§12)."""
        timing = self._timing()
        return {
            "schema_version": TRACE_SCHEMA_VERSION,
            "trace_id": self.trace_id,
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "versions": {
                "eduagent": _eduagent_version(),
                "python": sys.version.split()[0],
                "platform": platform.platform(terse=True),
                "model_id": self.model_id,
            },
            "seed": self.seed,
            "sampler": dict(self.sampler),
            "message": self.message_digest
            or unknown("turno sem mensagem de entrada (retomada de gate)"),
            "spans": [span.to_dict() for span in self.spans],
            "span_kinds_present": sorted({span.kind for span in self.spans}),
            "llm": self.llm_events,
            "counts": {
                "input_tokens": self._aggregate_tokens("input_tokens"),
                "reasoning_tokens": self._aggregate_tokens(
                    "reasoning_tokens"
                ),
                "output_tokens": self._aggregate_tokens("output_tokens"),
            },
            "budgets": self.budgets,
            "timing": timing,
            "resources": self._resource_metrics(),
            "errors": self.errors,
            "notes": self.notes,
        }

    def save(self, directory: Path | str) -> Path:
        """Persiste o trace como JSON local por turno (mapa §12: trace local
        por turno). Diretório é criado; retorno é o caminho gravado."""
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        target = path / f"{self.trace_id}.json"
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target


def _monotonic() -> float:
    import time

    return time.monotonic()


def _eduagent_version() -> str:
    try:
        from eduagent import __version__

        return __version__
    except Exception:  # pragma: no cover - import circular improvável
        return "unknown"


def load_trace(path: Path | str) -> dict[str, Any]:
    """Carrega um trace gravado (leitura do comando ``trace`` da CLI)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


__all__ = [
    "SPAN_KINDS",
    "SPAN_KIND_BY_NODE",
    "TRACE_SCHEMA_VERSION",
    "SpanRecord",
    "TurnTraceRecorder",
    "load_trace",
    "unknown",
    "unknown_metric",
]
