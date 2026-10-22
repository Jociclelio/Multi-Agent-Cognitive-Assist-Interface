"""Grafo LangGraph do EduAgent-OS: intenções, rotas, checkpoints, limites e
cancelamento (mapa §10, §12; estado do grafo e erros do §4).

Contratos implementados:

- **Intenções (§10)**: as 14 intenções do enum ``Intent``. Comandos
  explícitos (payload/intenção passada ao turno, incluindo comandos ``/`` na
  mensagem) prevalecem; o classificador LLM retorna **enum validado** (parse
  + schema locais) e, em ambiguidade, **pergunta antes de efeito** (turno
  termina com ``pending_question``; nada é executado).
- **Rotas (§10)**: exatamente as 11 rotas do mapa; cada ``+`` é leitura
  independente do snapshot comum (branch paralelo no grafo) e a geração usa
  **fila serial** (``policy.GenerationGate`` sobre o servidor loopback da
  task 002).
- **Checkpoints (§10)**: ``SQLiteCheckpointer`` (DB separado,
  ``durability=sync``) com ``thread_id`` = ``session_id``. A espera por
  aluno é FIM da invocação (terminal ``waiting_student``) e a nova entrada
  retoma o item — sem timeout ativo durante a espera (§10). Gates de
  confirmação usam ``interrupt()``: o nó é retomado **desde o início**
  (preparação é pura; efeitos ficam em nós idempotentes separados, com
  ``operation_id`` persistido no estado para replay §11).
- **Limites (§12)**: ``policy.TurnLimits`` confere cancelamento, deadline e
  budget ANTES de cada nó/tool/geração; reparo consome chamada e contador;
  ao esgotar, terminal com erro tipado e artefatos já válidos preservados;
  fila cheia responde ``RESOURCE_LIMIT``.
- **Cancelamento (§10)**: rota ``cancel`` → ``stop_dispatch`` →
  ``reconcile_started_effects`` → ``persist`` → terminal ``cancelled``.
- **Política de ferramentas (§10)**: toda proposta passa por
  ``policy.require_tool`` (papel atribuído pelo dispatcher, pré-condição da
  tabela); nenhum agente recebe shell genérico nem escrita direta no DB —
  as únicas escritas são via serviços determinísticos (commit idempotente,
  §11). Fonte/tool result é dado rotulado e não altera política; JSON
  correto para ação proibida é negado por código.
- **Segurança (§10)**: paths resolvidos com ``policy.resolve_owned_path``;
  destinos de fetch validados com ``policy.assert_public_url`` (IP
  privado/loopback bloqueado; redirects revalidados).
- **Divergência não é votada (§10)**: divergência com solver/fato
  confirmado vira esclarecimento (pergunta) ou falha controlada (erro
  tipado), nunca média/votação de saídas.

Nota de escopo: o MVP é local e single-threaded por processo (mapa §1 —
multiusuário concorrente em rede fora do deploy inicial); os limites do
turno são instância do runner e cada invocação é sequencial. A disponibilidade
default do problema de agendamento é escolha de ENSAIO (mapa §1/§3), não
resultado medido.
"""

from __future__ import annotations

import json
import re
import uuid as _uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import ValidationError

from eduagent.agents.curator import CuratorAgent
from eduagent.agents.librarian import Librarian
from eduagent.agents.monitor import Monitor, MonitorInput, MonitorMode
from eduagent.agents.planner import ActivityUpdate, PlannerAgent
from eduagent.agents.tutor import (
    StudentMove,
    Tutor,
    TutorSession,
    new_session,
)
from eduagent.contracts import (
    Assessment,
    EduAgentError,
    ErrorCode,
    GraphState,
    GraphStatus,
    Intent,
    LearningItem,
    Ref,
    RubricCriterion,
    ScheduleProposal,
    SenderRole,
    SourceRef,
    ToolName,
    TutorTurn,
    TypedError,
)
from eduagent.policy import (
    GenerationGate,
    TurnLimits,
    assert_public_url,
    assert_redirect_target,
    require_tool,
    resolve_owned_path,
    typed_error_of,
)
from eduagent.services.assessment import AssessmentService
from eduagent.services.calendar import CalendarService
from eduagent.services.effects import OutboxDispatcher
from eduagent.services.memory import MemoryService
from eduagent.services.model_adapter import (
    NON_THINKING_SAMPLER,
    ModelAdapterError,
)
from eduagent.services.scheduling import (
    DemandRecord,
    DemandService,
    PolicyOutcome,
    SchedulingProblem,
    SolverDemand,
    SolverSettings,
    TimeWindow,
    load_solver_settings,
    solve_schedule,
    verify_schedule,
)
from eduagent.storage.checkpoints import SQLiteCheckpointer
from eduagent.storage.repository import DomainStore
from eduagent.telemetry import SPAN_KIND_BY_NODE, TurnTraceRecorder

DIAGNOSTIC = "eduagent/graph.py"

_STATUS_FAILED = GraphStatus.FAILED.value
_STATUS_CANCELLED = GraphStatus.CANCELLED.value
_STATUS_WAITING = GraphStatus.WAITING_STUDENT.value
_STATUS_COMPLETED = GraphStatus.COMPLETED.value

#: Janela padrão de disponibilidade do problema de agendamento (escolha de
#: ENSAIO — não resultado medido): seg–sex, 08:00–12:00 e 14:00–18:00 no dia
#: local (UTC enquanto a timezone não for confirmada, mapa §3).
_DEFAULT_WINDOWS: tuple[tuple[int, int], ...] = (
    (8 * 60, 12 * 60),
    (14 * 60, 18 * 60),
)

#: Fetches por turno de curadoria (mapa §6: "Até 5 candidatos/3 fetches";
#: default de ensaio).
_MAX_FETCHES = 3

#: Candidatos por turno de curadoria (mapa §6: "Até 5 candidatos/3 fetches";
#: default de ensaio). O conector também limita; o corte aqui é defesa em
#: profundidade — payload não amplia o limite normativo.
_MAX_CANDIDATES = 5


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


def _require_service(service: Any, name: str, route: str) -> Any:
    """Recurso configurado ausente → classe 3 do §12 (recurso/conector
    indisponível): a ausência de serviço/embedder configurado NÃO é falha
    interna — é indisponibilidade do recurso declarada por código
    (``SOURCE_UNRESOLVED``, mapeada para exit 3 na CLI e 404/503-family na
    API). Escolha local de mapeamento §12 documentada."""
    if service is None:
        raise _error(
            ErrorCode.SOURCE_UNRESOLVED,
            f"recurso configurado ausente: serviço {name!r} indisponível "
            f"na rota {route!r} (§12 classe 3: recurso/conector "
            "indisponível)",
        )
    return service


def _ref_locator(kind: str | None, id_: Any, version: int = 1) -> str:
    prefix = f"{kind}:" if kind else ""
    return f"{prefix}{_uuid.UUID(str(id_))}@{version}"


# ---------------------------------------------------------------------------
# Estado do turno (canais do LangGraph)
# ---------------------------------------------------------------------------


class TurnState(TypedDict, total=False):
    """Canais do estado do turno (mapa §4). Cada chave é um canal LastValue;
    valores são dados JSON-serializáveis — o checkpoint guarda refs e dados
    textuais de turno, não PDFs integrais (mapa §4)."""

    # identidade do turno (mapa §4)
    user_id: str
    session_id: str
    turn_id: str
    trace_id: str
    task_id: Optional[str]
    message: str
    payload: dict
    intent: Optional[str]
    intent_classified: bool
    seed: int
    # estado do grafo (mapa §4)
    snapshot_version: Optional[int]
    snapshot_digest: str
    artifact_refs: list
    pending_question: Optional[str]
    pending_item_ref: Optional[str]
    status: str
    errors: list
    result: dict
    budget_snapshot: dict
    cancel_requested: bool
    #: Canal interno da rota cancel (stop_dispatch já executou).
    cancelling: bool
    # sessão do tutor preservada no checkpoint (C2)
    tutor_session: Optional[dict]
    # dados de rota
    evidence: dict
    memory_summary: dict
    tutor_evidence: dict
    tutor_outcome: dict
    validated_turn: dict
    pending_item: dict
    attempt_record: dict
    monitor_outcome: dict
    validated_assessment: dict
    critical_criterion_ids: list
    assessment_result: dict
    operation_ids: dict
    pending_demands: list
    needs_confirmation: bool
    resume_value: dict
    confirmations_applied: list
    solve_result: dict
    independent_validation: dict
    pending_plan: Optional[dict]
    approved_plan_id: Optional[str]
    activity_update: dict
    activity_result: dict
    export_plan_id: str
    ics: bytes
    ics_events: int
    ingest: dict
    extraction: dict
    change: dict
    web_candidates: list
    fetched: list
    curate_ranked: list
    curate_connector: bool


# ---------------------------------------------------------------------------
# Configuração de limites derivada da config (mapa §3/§12)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LimitsConfig:
    """Limites do turno a partir de ``config/default.yaml`` (mapa §3).
    Todos os valores são defaults de ensaio a calibrar — não resultados
    medidos."""

    max_llm_calls: int = 6
    max_tool_calls: int = 8
    max_graph_steps: int = 16
    max_repairs_total: int = 2
    active_deadline_s: float = 120

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any] | None) -> "LimitsConfig":
        config = config or {}
        return cls(
            max_llm_calls=int(config.get("max_llm_calls", 6)),
            max_tool_calls=int(config.get("max_tool_calls", 8)),
            max_graph_steps=int(config.get("max_graph_steps", 16)),
            max_repairs_total=int(config.get("max_repairs_total", 2)),
            active_deadline_s=float(config.get("active_deadline_s", 120)),
        )


# ---------------------------------------------------------------------------
# Classificador de intenções (§10)
# ---------------------------------------------------------------------------

_CLASSIFIER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["intent"],
    "properties": {
        "intent": {"type": "string", "enum": [i.value for i in Intent]},
        "ambiguous": {"type": "boolean"},
    },
}

_EXPLICIT_COMMANDS: dict[str, Intent] = {
    "/ingest": Intent.INGEST,
    "/ask": Intent.ASK,
    "/practice": Intent.PRACTICE,
    "/submit": Intent.SUBMIT_ANSWER,
    "/plan": Intent.PLAN,
    "/replan": Intent.REPLAN,
    "/approve": Intent.APPROVE_PLAN,
    "/export": Intent.EXPORT_CALENDAR,
    "/resume": Intent.ASK,  # retomada: nova entrada; rota depende do estado
    "/cancel": Intent.CANCEL,
    "/curate": Intent.CURATE,
}


def _explicit_intent(
    message: str, payload: Mapping[str, Any]
) -> Intent | None:
    """Comandos explícitos prevalecem (§10): intenção passada no payload
    (CLI/API da task 015) ou comando ``/`` no início da mensagem."""
    declared = payload.get("intent")
    if declared is not None:
        try:
            return Intent(str(declared))
        except ValueError as exc:
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                f"intenção explícita desconhecida: {declared!r}",
            ) from exc
    text = (message or "").strip()
    lowered = text.lower()
    for prefix, intent in _EXPLICIT_COMMANDS.items():
        if lowered.startswith(prefix):
            return intent
    if lowered in {"cancelar", "cancela", "parar", "stop"}:
        return Intent.CANCEL
    return None


class _IntentClassifier:
    """Classificador LLM com enum validado (§10): parse + schema locais são
    obrigatórios; saída inválida/ambígua consome reparo (§12) e, persistindo
    a ambiguidade, o grafo PERGUNTA antes de qualquer efeito."""

    def __init__(self, gate: GenerationGate) -> None:
        self._gate = gate

    def classify(
        self,
        *,
        message: str,
        limits: TurnLimits,
        deadline: datetime | None,
        seed: int | None,
    ) -> tuple[Intent | None, bool]:
        """Devolve ``(intenção, ambígua)``; cada tentativa consome orçamento
        de LLM, e o reparo consome chamada e contador (§12)."""
        messages = [
            {
                "role": "system",
                "content": (
                    "Você classifica a intenção do estudante. Responda "
                    "APENAS JSON com a chave 'intent' (enum fechado) e "
                    "'ambiguous' (true se a mensagem não permite decidir). "
                    "Não execute ações."
                ),
            },
            {"role": "user", "content": message},
        ]
        parsed, ambiguous = self._attempt(messages, limits, deadline, seed)
        if parsed is not None and not ambiguous:
            return parsed, False
        if limits.repairs_remaining > 0:
            limits.consume_repair()
            parsed, ambiguous = self._attempt(messages, limits, deadline, seed)
            if parsed is not None and not ambiguous:
                return parsed, False
        return parsed, True

    def _attempt(
        self,
        messages: list[dict[str, Any]],
        limits: TurnLimits,
        deadline: datetime | None,
        seed: int | None,
    ) -> tuple[Intent | None, bool]:
        result = self._gate.generate(
            limits=limits,
            messages=messages,
            schema=_CLASSIFIER_SCHEMA,
            sampler=NON_THINKING_SAMPLER,
            seed=seed,
            deadline=deadline,
        )
        try:
            data = json.loads(result.text)
        except json.JSONDecodeError:
            return None, True
        if not isinstance(data, dict) or "intent" not in data:
            return None, True
        try:
            intent = Intent(str(data["intent"]))
        except ValueError:
            return None, True
        return intent, bool(data.get("ambiguous", False))


# ---------------------------------------------------------------------------
# Resultado do turno
# ---------------------------------------------------------------------------


@dataclass
class TurnResult:
    """Saída de uma invocação: estado final validado pelo contrato
    ``GraphState`` (mapa §4) + payload de resultado para CLI/API (§12)."""

    status: str
    state: GraphState
    output: dict[str, Any]
    #: True quando a invocação terminou em interrupt aguardando o usuário.
    waiting_interrupt: bool
    interrupt_payload: Any = None
    #: Trace local do turno (mapa §12); None quando sem diretório de
    #: telemetria configurado. Metadado operacional, fora do contrato §4.
    trace: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Grafo
# ---------------------------------------------------------------------------


class EduAgentGraph:
    """Orquestrador do turno (mapa §10/§12). Componha os serviços já
    construídos pelas tasks 005–013; os opcionais (``None``) tornam a rota
    correspondente indisponível com erro tipado.

    ``thread_id`` do LangGraph = ``session_id`` (checkpointer por sessão).
    """

    def __init__(
        self,
        *,
        store: DomainStore,
        checkpointer: SQLiteCheckpointer,
        config: Mapping[str, Any] | None = None,
        clock: Callable[[], datetime] | None = None,
        backend: Any | None = None,
        queue_size: int = 4,
        tutor: Tutor | None = None,
        librarian: Librarian | None = None,
        curator: CuratorAgent | None = None,
        retrieval: Any | None = None,
        embedder: Any | None = None,
        memory: MemoryService | None = None,
        assessment: AssessmentService | None = None,
        monitor: Monitor | None = None,
        rubric_grader: Any | None = None,
        planner: PlannerAgent | None = None,
        demands: DemandService | None = None,
        calendar: CalendarService | None = None,
        ingestion: Any | None = None,
        dispatcher: OutboxDispatcher | None = None,
        web_connector: Any | None = None,
        calendar_connector: Any | None = None,
        data_root: Path | str | None = None,
        telemetry_dir: Path | str | None = None,
        build_problem: Callable[
            [str, Sequence[Mapping[str, Any]], int | None],
            SchedulingProblem,
        ]
        | None = None,
        solver_settings: SolverSettings | None = None,
    ) -> None:
        self._store = store
        self._config = dict(config or {})
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._limits_config = LimitsConfig.from_mapping(self._config)
        self._network_enabled = bool(self._config.get("network_enabled", False))
        self._checkpointer = checkpointer
        self._backend = backend
        # Observador do trace local (mapa §12): a fila de geração publica
        # queue/LLM ao recorder do turno corrente.
        self._gate_observer = self._observe_llm if backend is not None else None
        self._gate = (
            GenerationGate(
                backend,
                queue_size=queue_size,
                clock=self._clock,
                observer=self._gate_observer,
            )
            if backend is not None
            else None
        )
        self._classifier = (
            _IntentClassifier(self._gate) if self._gate is not None else None
        )
        self._tutor = tutor
        self._librarian = librarian
        self._curator = curator
        self._retrieval = retrieval
        self._embedder = embedder
        self._memory = memory
        self._assessment = assessment
        self._monitor = monitor or Monitor()
        self._rubric_grader = rubric_grader
        self._planner = planner
        self._demands = demands
        self._calendar = calendar
        self._ingestion = ingestion
        self._dispatcher = dispatcher
        self._web_connector = web_connector
        # Conector de sync de calendário admitido (task 016, §9): ``None``
        # (default) → ``calendar.apply`` reporta ``CONNECTOR_DISABLED``
        # mantendo ICS/preview — sem credenciais o núcleo segue funcional.
        self._calendar_connector = calendar_connector
        self._data_root = Path(data_root) if data_root else None
        # Trace local por turno (mapa §12, task 015): quando um diretório é
        # configurado, cada invocação grava um trace JSON (spans, contagens,
        # recursos) — metadado operacional fora do estado do grafo (§4).
        self._telemetry_dir = Path(telemetry_dir) if telemetry_dir else None
        self._trace: TurnTraceRecorder | None = None
        self._build_problem = build_problem
        self._solver_settings = solver_settings or load_solver_settings()
        # Turno corrente (MVP single-threaded, §1): limites conferidos antes
        # de cada nó/tool/geração (§12).
        self._limits: TurnLimits | None = None
        self._graph = self._build()

    # ------------------------------------------------------------------
    # Construção do grafo (rotas do §10)
    # ------------------------------------------------------------------

    def _guarded(
        self, fn: Callable[[dict], dict], *, cancellable: bool = True
    ) -> Callable[[dict], dict]:
        """Envolve o nó: limites ANTES do nó (§12) e erro tipado → terminal
        com erro e artefatos já válidos preservados (§12). Nós após uma
        falha viram pass-through: a execução segue até o terminal ``finish``
        sem novos efeitos. Nós da própria rota ``cancel`` não são bloqueados
        pela guarda de cancelamento — o trabalho deles É processar o
        cancelamento (§10). Cada nó executa dentro do span do trace local
        (mapa §12: spans de fila/LLM/retrieval/context/solver/commit/tools)."""

        def node(state: dict) -> dict:
            name = getattr(fn, "__name__", str(fn))
            if state.get("status") == _STATUS_FAILED:
                return {}
            try:
                assert self._limits is not None  # runner sequencial (§1)
                self._limits.begin_step(
                    cancel_requested=bool(state.get("cancel_requested"))
                    if cancellable
                    else False,
                    step=name,
                )
                trace = self._trace
                if trace is not None:
                    span_name = name.removeprefix("_node_")
                    with trace.span(
                        SPAN_KIND_BY_NODE.get(span_name, "tools"),
                        node=span_name,
                    ):
                        return fn(state)
                return fn(state)
            except EduAgentError as exc:
                return self._failure(state, exc)
            except ModelAdapterError as exc:
                return self._failure(
                    state,
                    EduAgentError(
                        exc.code,
                        exc.message,
                        retryable=exc.retryable,
                        diagnostic=exc.diagnostic,
                    ),
                )

        node.__name__ = getattr(fn, "__name__", "node")
        return node

    def _failure(self, state: dict, exc: EduAgentError) -> dict:
        # Artefatos já válidos (refs em estado) são preservados — nunca
        # saída parcial silenciosamente aprovada (§12).
        errors = list(state.get("errors") or [])
        errors.append(typed_error_of(exc).model_dump(mode="json"))
        return {
            "status": _STATUS_FAILED,
            "errors": errors,
            "result": {
                "error": typed_error_of(exc).model_dump(mode="json"),
                "artifact_refs": list(state.get("artifact_refs") or []),
            },
        }

    @staticmethod
    def _failed(state: dict) -> bool:
        return state.get("status") == _STATUS_FAILED

    def _build(self):
        g = StateGraph(TurnState)
        guarded = self._guarded

        g.add_node("classify", guarded(self._node_classify, cancellable=False))
        g.add_node("wait_user", guarded(self._node_wait_user))
        # ingest
        g.add_node("ingest_extract", guarded(self._node_ingest_extract))
        g.add_node("curator_facts", guarded(self._node_curator_facts))
        g.add_node("ingest_validate", guarded(self._node_ingest_validate))
        g.add_node("confirm_if_needed", guarded(self._node_confirm_if_needed))
        g.add_node("commit_index", guarded(self._node_commit_index))
        # ask/practice
        g.add_node("snapshot", guarded(self._node_snapshot))
        g.add_node("curator_retrieve", guarded(self._node_curator_retrieve))
        g.add_node(
            "librarian_retrieve", guarded(self._node_librarian_retrieve)
        )
        g.add_node("context", guarded(self._node_context))
        g.add_node("tutor", guarded(self._node_tutor))
        g.add_node("tutor_validate", guarded(self._node_tutor_validate))
        g.add_node("publish_wait", guarded(self._node_publish_wait))
        # submit_answer
        g.add_node(
            "resolve_pending_item", guarded(self._node_resolve_pending_item)
        )
        g.add_node("monitor_node", guarded(self._node_monitor))
        g.add_node("answer_validate", guarded(self._node_answer_validate))
        g.add_node(
            "commit_assessment", guarded(self._node_commit_assessment)
        )
        g.add_node("feedback", guarded(self._node_feedback))
        g.add_node(
            "optional_review_request",
            guarded(self._node_optional_review_request),
        )
        # plan/replan
        g.add_node("planner_demands", guarded(self._node_planner_demands))
        g.add_node(
            "commit_confirmations", guarded(self._node_commit_confirmations)
        )
        g.add_node("solver", guarded(self._node_solver))
        g.add_node(
            "independent_check", guarded(self._node_independent_check)
        )
        g.add_node("preview", guarded(self._node_preview))
        g.add_node("wait_approval", guarded(self._node_wait_approval))
        g.add_node("commit_approval", guarded(self._node_commit_approval))
        # approve_plan (rota explícita)
        g.add_node(
            "validate_approval", guarded(self._node_validate_approval)
        )
        # update_activity
        g.add_node(
            "validate_transition", guarded(self._node_validate_transition)
        )
        g.add_node("commit_event", guarded(self._node_commit_event))
        g.add_node("optional_replan", guarded(self._node_optional_replan))
        # export_calendar
        g.add_node(
            "resolve_approved_plan", guarded(self._node_resolve_approved_plan)
        )
        g.add_node("render_ics", guarded(self._node_render_ics))
        g.add_node("ics_validate", guarded(self._node_ics_validate))
        g.add_node("publish_ics", guarded(self._node_publish_ics))
        # memory_query
        g.add_node("source_check", guarded(self._node_source_check))
        g.add_node("answer", guarded(self._node_answer))
        # correct_fact/delete_data
        g.add_node("validate_scope", guarded(self._node_validate_scope))
        g.add_node("delete_preview", guarded(self._node_delete_preview))
        g.add_node("confirm_change", guarded(self._node_confirm_change))
        g.add_node(
            "commit_invalidate", guarded(self._node_commit_invalidate)
        )
        # curate
        g.add_node("network_gate", guarded(self._node_network_gate))
        g.add_node("web_search", guarded(self._node_web_search))
        g.add_node("web_fetch", guarded(self._node_web_fetch))
        g.add_node("curator_rank", guarded(self._node_curator_rank))
        g.add_node(
            "validate_access_claims",
            guarded(self._node_validate_access_claims),
        )
        # cancel
        g.add_node(
            "stop_dispatch",
            guarded(self._node_stop_dispatch, cancellable=False),
        )
        g.add_node(
            "reconcile_started_effects",
            guarded(self._node_reconcile_started_effects, cancellable=False),
        )
        g.add_node(
            "persist", guarded(self._node_persist, cancellable=False)
        )
        g.add_node(
            "cancelled", guarded(self._node_cancelled, cancellable=False)
        )
        # terminal
        g.add_node("finish", self._node_finish)

        # entrada + classificação
        g.add_edge(START, "classify")
        g.add_conditional_edges(
            "classify",
            self._route_intent,
            {
                "wait_user": "wait_user",
                "ingest": "ingest_extract",
                "tutor": "snapshot",
                "submit": "resolve_pending_item",
                "plan": "snapshot",
                "approve": "validate_approval",
                "activity": "validate_transition",
                "export": "resolve_approved_plan",
                "memory": "librarian_retrieve",
                "change": "validate_scope",
                "curate": "network_gate",
                "cancel": "stop_dispatch",
                "finish": "finish",
            },
        )
        g.add_edge("wait_user", "finish")
        # cancel (§10: stop_dispatch → reconcile → persist → cancelled)
        g.add_edge("stop_dispatch", "reconcile_started_effects")
        g.add_edge("reconcile_started_effects", "persist")
        g.add_edge("persist", "cancelled")
        g.add_edge("cancelled", "finish")
        # ingest (§10: extract → curator_facts → validate → confirm → commit)
        g.add_edge("ingest_extract", "curator_facts")
        g.add_edge("curator_facts", "ingest_validate")
        g.add_edge("ingest_validate", "confirm_if_needed")
        # confirm_if_needed é compartilhado (ingest/plan) — rota por intenção
        g.add_edge("commit_index", "finish")
        # ask/practice (§10: snapshot → curator + librarian → context →
        # tutor → validate → publish/wait) — o snapshot é compartilhado com
        # a rota plan; o fan-out (leituras independentes) é só da tutoria.
        g.add_conditional_edges(
            "snapshot",
            self._route_after_snapshot,
            {
                "curator_retrieve": "curator_retrieve",
                "librarian_retrieve": "librarian_retrieve",
                "planner_demands": "planner_demands",
                "finish": "finish",
            },
        )
        g.add_edge("curator_retrieve", "context")
        g.add_edge("context", "tutor")
        g.add_edge("tutor", "tutor_validate")
        g.add_edge("tutor_validate", "publish_wait")
        g.add_edge("publish_wait", "finish")
        # librarian_retrieve é compartilhado (tutor/memory) — rota por intenção
        g.add_conditional_edges(
            "librarian_retrieve",
            self._route_after_librarian,
            {"context": "context", "source_check": "source_check", "finish": "finish"},
        )
        # submit_answer (§10: resolve → monitor → validate → commit →
        # feedback → optional_review_request → finish)
        g.add_edge("resolve_pending_item", "monitor_node")
        g.add_edge("monitor_node", "answer_validate")
        g.add_edge("answer_validate", "commit_assessment")
        g.add_edge("commit_assessment", "feedback")
        g.add_edge("feedback", "optional_review_request")
        g.add_edge("optional_review_request", "finish")
        # plan/replan (§10: snapshot → demands → confirm → solver → check →
        # preview → wait)
        g.add_edge("planner_demands", "confirm_if_needed")
        g.add_conditional_edges(
            "confirm_if_needed",
            self._route_after_confirm,
            {
                "commit_index": "commit_index",
                "commit_confirmations": "commit_confirmations",
                "finish": "finish",
            },
        )
        g.add_conditional_edges(
            "commit_confirmations",
            self._route_after_plan_confirm,
            {"solver": "solver", "finish": "finish"},
        )
        g.add_edge("solver", "independent_check")
        g.add_edge("independent_check", "preview")
        g.add_edge("preview", "wait_approval")
        g.add_edge("wait_approval", "commit_approval")
        g.add_edge("commit_approval", "finish")
        # approve_plan (§10: validate_revision/digest → commit_confirmation)
        g.add_edge("validate_approval", "commit_approval")
        # update_activity (§10: validate_transition/time → commit_event →
        # optional_replan)
        g.add_edge("validate_transition", "commit_event")
        g.add_edge("commit_event", "optional_replan")
        g.add_edge("optional_replan", "finish")
        # export_calendar (§10: resolve → render → validate → publish
        # [→ confirmed_outbox])
        g.add_edge("resolve_approved_plan", "render_ics")
        g.add_edge("render_ics", "ics_validate")
        g.add_edge("ics_validate", "publish_ics")
        g.add_edge("publish_ics", "finish")
        # memory_query (§10: librarian_retrieve → source_check → answer)
        g.add_edge("source_check", "answer")
        g.add_edge("answer", "finish")
        # correct_fact/delete_data (§10: validate_scope → preview → confirm
        # → commit/invalidate)
        g.add_edge("validate_scope", "delete_preview")
        g.add_edge("delete_preview", "confirm_change")
        g.add_edge("confirm_change", "commit_invalidate")
        g.add_edge("commit_invalidate", "finish")
        # curate (§10: network_gate → search/fetch → curator_rank →
        # validate_access_claims)
        g.add_edge("network_gate", "web_search")
        g.add_edge("web_search", "web_fetch")
        g.add_edge("web_fetch", "curator_rank")
        g.add_edge("curator_rank", "validate_access_claims")
        g.add_edge("validate_access_claims", "finish")
        return g.compile(checkpointer=self._checkpointer)

    # ------------------------------------------------------------------
    # Trace local por turno (mapa §12)
    # ------------------------------------------------------------------

    def _start_trace(
        self,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        turn_id: str | None = None,
        message: str | None = None,
        seed: int | None = None,
    ) -> TurnTraceRecorder | None:
        """Abre o trace do turno (mapa §12) quando há diretório configurado;
        sem diretório, nenhum trace é produzido (MVP: observabilidade local
        opcional)."""
        if self._telemetry_dir is None:
            self._trace = None
            return None
        recorder = TurnTraceRecorder(
            trace_id=str(_uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            turn_id=turn_id,
            message=message,
            seed=seed,
            sampler=asdict(NON_THINKING_SAMPLER),
            model_id=getattr(self._backend, "model_id", None),
            clock=self._clock,
        )
        self._trace = recorder
        return recorder

    def _observe_llm(self, event: Mapping[str, Any]) -> None:
        """Observador do ``GenerationGate``: evento de fila/LLM do turno
        corrente vai ao trace (mapa §12); falha de telemetria é isolada."""
        trace = self._trace
        if trace is None:
            return
        try:
            trace.observe_llm(event)
        except Exception:  # noqa: BLE001 — telemetria nunca derruba o turno
            return

    def _finish_trace(
        self,
        trace: TurnTraceRecorder | None,
        *,
        status: str,
        final: Mapping[str, Any] | None = None,
        error: BaseException | None = None,
    ) -> dict[str, Any] | None:
        """Fecha o trace, grava no diretório configurado e devolve o dict
        (TurnResult.trace). Erros do §4 vão ao trace com o estado final."""
        if trace is None:
            return None
        final = final or {}
        if error is not None:
            if isinstance(error, EduAgentError):
                typed = [typed_error_of(error).model_dump(mode="json")]
            else:
                typed = [
                    typed_error_of(
                        _error(
                            ErrorCode.INTERNAL_FAILURE,
                            f"exceção fora do contrato do turno: {error}",
                        )
                    ).model_dump(mode="json")
                ]
        else:
            typed = list(final.get("errors") or [])
        data = trace.finish(
            status=status,
            errors=typed,
            user_id=(
                str(final.get("user_id")) if final.get("user_id") else None
            ),
            session_id=(
                str(final.get("session_id"))
                if final.get("session_id")
                else None
            ),
            turn_id=(
                str(final.get("turn_id")) if final.get("turn_id") else None
            ),
        )
        try:
            trace.save(self._telemetry_dir)  # type: ignore[arg-type]
        except OSError:  # pragma: no cover — disco cheio/permissão: turno vale
            pass
        self._trace = None
        return data

    # ------------------------------------------------------------------
    # Invocação
    # ------------------------------------------------------------------

    def _deadline(self) -> datetime | None:
        seconds = self._limits_config.active_deadline_s
        if seconds == 0:
            return None  # sem deadline configurado
        # negativo → instante já vencido (testes de §12); positivo →
        # deadline do turno ativo (default de ensaio, mapa §3).
        return self._clock() + timedelta(seconds=seconds)

    def _new_limits(self) -> TurnLimits:
        return TurnLimits(
            max_llm_calls=self._limits_config.max_llm_calls,
            max_tool_calls=self._limits_config.max_tool_calls,
            max_graph_steps=self._limits_config.max_graph_steps,
            max_repairs_total=self._limits_config.max_repairs_total,
            deadline=self._deadline(),
            clock=self._clock,
        )

    def _session_owner(self, session_id: str) -> str | None:
        """Dono registrado da sessão (thread do checkpoint, §10/§12): o
        estado do grafo guarda o ``user_id`` do turno que abriu a sessão.
        Sessão sem checkpoint (nova) não tem dono ainda."""
        config = {"configurable": {"thread_id": str(session_id)}}
        snapshot = self._graph.get_state(config)
        owner = (snapshot.values or {}).get("user_id")
        return str(owner) if owner else None

    def _require_session_owner(
        self, session_id: str, user_id: str | None
    ) -> None:
        """Ownership usuário↔sessão (§12): efeitos de retomada, cancelamento
        e aprovação exigem que a sessão pertença ao usuário autenticado.
        Sessão de outro usuário é recusada por código ANTES de qualquer
        efeito (``TOOL_DENIED`` — ação proibida é negada por código, §4/§10;
        mesmo precedente de ownership da 014a)."""
        if user_id is None:
            return
        owner = self._session_owner(session_id)
        if owner is None or owner == str(user_id):
            return
        raise _error(
            ErrorCode.TOOL_DENIED,
            "sessão de outro usuário: a sessão "
            f"{session_id} pertence ao usuário {owner}; o usuário "
            f"autenticado {user_id} não pode retomar, cancelar ou aprovar "
            "efeitos dela (§12: escrita exige o contexto autenticado da "
            "própria sessão)",
        )

    def run_turn(
        self,
        *,
        user_id: str,
        session_id: str,
        message: str,
        payload: Mapping[str, Any] | None = None,
        intent: str | None = None,
        cancel_requested: bool = False,
        seed: int | None = None,
    ) -> TurnResult:
        """Um turno (mapa §10/§12): nova entrada no ``thread_id`` da sessão;
        espera por aluno e gates de confirmação terminam a invocação."""
        config = {"configurable": {"thread_id": str(session_id)}}
        # Ownership ANTES da escrita no thread (§12): turno em sessão de
        # outro usuário é recusado sem aplicar efeito (inclui cancel).
        self._require_session_owner(str(session_id), str(user_id))
        self._limits = self._new_limits()
        payload = dict(payload or {})
        if intent is not None:
            payload = {**payload, "intent": intent}
        seed_value = int(
            seed if seed is not None else self._config.get("seed", 0)
        )
        incoming: dict[str, Any] = {
            "user_id": str(user_id),
            "session_id": str(session_id),
            "turn_id": str(_uuid.uuid4()),
            "trace_id": str(_uuid.uuid4()),
            "task_id": None,
            "message": str(message or ""),
            "payload": payload,
            "cancel_requested": bool(cancel_requested),
            "status": "running",
            "errors": [],
            "result": {},
            "budget_snapshot": self._limits.to_dict(),
            "seed": seed_value,
        }
        if cancel_requested:
            # §10/§12: cancelamento tem prioridade — vai direto à rota
            # cancel (sem classificação nem efeito).
            incoming["intent"] = Intent.CANCEL.value
        # deadline do turno é efêmero: NÃO entra no estado persistido —
        # §10 ("sem timeout ativo durante espera").
        trace = self._start_trace(
            user_id=str(user_id),
            session_id=str(session_id),
            message=str(message or ""),
            seed=seed_value,
        )
        try:
            out = self._graph.invoke(incoming, config=config)
        except BaseException as exc:
            self._finish_trace(trace, status="failed", error=exc)
            raise
        interrupted = "__interrupt__" in (out or {})
        final = self._final_state(config)
        interrupt_payload = None
        if interrupted:
            interrupt_payload = getattr(out["__interrupt__"][0], "value", None)
            status = _STATUS_WAITING
        else:
            status = final.get("status", _STATUS_COMPLETED)
        graph_state = self._contract_state(final, status)
        trace_data = self._finish_trace(trace, status=status, final=final)
        return TurnResult(
            status=status,
            state=graph_state,
            output=final.get("result") or {},
            waiting_interrupt=interrupted,
            interrupt_payload=interrupt_payload,
            trace=trace_data,
        )

    def resume_turn(
        self,
        *,
        session_id: str,
        resume: Mapping[str, Any] | Any,
        user_id: str | None = None,
    ) -> TurnResult:
        """Retoma um nó interrompido desde o início com o valor de retomada
        (§10: interrupt retoma o nó; preparação pura, efeitos idempotentes).
        Com ``user_id`` informado (CLI/API com contexto autenticado), a
        sessão de outro usuário é recusada por código antes de qualquer
        efeito (§12: ownership usuário↔sessão)."""
        config = {"configurable": {"thread_id": str(session_id)}}
        self._require_session_owner(str(session_id), user_id)
        self._limits = self._new_limits()
        value = dict(resume) if isinstance(resume, Mapping) else resume
        trace = self._start_trace(session_id=str(session_id), message=None)
        try:
            out = self._graph.invoke(Command(resume=value), config=config)
        except BaseException as exc:
            self._finish_trace(trace, status="failed", error=exc)
            raise
        interrupted = "__interrupt__" in (out or {})
        final = self._final_state(config)
        status = (
            _STATUS_WAITING
            if interrupted
            else final.get("status", _STATUS_COMPLETED)
        )
        interrupt_payload = (
            getattr(out["__interrupt__"][0], "value", None)
            if interrupted
            else None
        )
        trace_data = self._finish_trace(trace, status=status, final=final)
        return TurnResult(
            status=status,
            state=self._contract_state(final, status),
            output=final.get("result") or {},
            waiting_interrupt=interrupted,
            interrupt_payload=interrupt_payload,
            trace=trace_data,
        )

    def _final_state(self, config: dict) -> dict:
        snapshot = self._graph.get_state(config)
        return dict(snapshot.values or {})

    def _contract_state(self, final: dict, status: str) -> GraphState:
        """Estado final validado pelo contrato (mapa §4): falha aqui é
        INTERNAL_FAILURE — o terminal nunca sai fora do contrato."""
        budgets = final.get("budget_snapshot") or {}
        errors = [
            TypedError.model_validate(e)
            for e in (final.get("errors") or [])
        ]
        intent = final.get("intent")
        try:
            return GraphState(
                user_id=_uuid.UUID(str(final.get("user_id"))),
                session_id=_uuid.UUID(str(final.get("session_id"))),
                turn_id=_uuid.UUID(str(final.get("turn_id"))),
                task_id=(
                    _uuid.UUID(str(final["task_id"]))
                    if final.get("task_id")
                    else None
                ),
                trace_id=_uuid.UUID(str(final.get("trace_id"))),
                intent=Intent(str(intent)) if intent else Intent.ASK,
                snapshot_version=final.get("snapshot_version"),
                artifact_refs=[
                    Ref.model_validate(r)
                    for r in (final.get("artifact_refs") or [])
                ],
                pending_question=final.get("pending_question"),
                pending_item_ref=(
                    Ref.model_validate(final["pending_item_ref"])
                    if final.get("pending_item_ref")
                    else None
                ),
                budgets=BudgetsOf(
                    llm_calls_remaining=int(
                        budgets.get("llm_calls_remaining", 0)
                    ),
                    tool_calls_remaining=int(
                        budgets.get("tool_calls_remaining", 0)
                    ),
                    tokens_remaining=None,
                ),
                deadline=None,  # deadline é do turno ativo, não do estado
                cancel_requested=bool(final.get("cancel_requested")),
                status=GraphStatus(status),
                errors=errors,
            )
        except (ValidationError, ValueError) as exc:
            raise _error(
                ErrorCode.INTERNAL_FAILURE,
                f"estado final viola o contrato GraphState (mapa §4): {exc}",
            ) from exc

    # ------------------------------------------------------------------
    # Roteamento (§10)
    # ------------------------------------------------------------------

    def _route_intent(self, state: dict) -> str:
        if self._failed(state):
            return "finish"
        # Cancelamento tem prioridade (§10/§12): cancel_requested no estado
        # (ex.: POST /turns/{id}/cancel da task 015) vai para a rota cancel.
        if bool(state.get("cancel_requested")) or state.get(
            "intent"
        ) == Intent.CANCEL.value:
            return "cancel"
        intent = state.get("intent")
        if intent in (Intent.ASK.value, Intent.PRACTICE.value):
            return "tutor"
        if intent == Intent.INGEST.value:
            return "ingest"
        if intent == Intent.SUBMIT_ANSWER.value:
            return "submit"
        if intent in (Intent.PLAN.value, Intent.REPLAN.value):
            return "plan"
        if intent == Intent.APPROVE_PLAN.value:
            return "approve"
        if intent == Intent.UPDATE_ACTIVITY.value:
            return "activity"
        if intent == Intent.EXPORT_CALENDAR.value:
            return "export"
        if intent == Intent.MEMORY_QUERY.value:
            return "memory"
        if intent in (Intent.CORRECT_FACT.value, Intent.DELETE_DATA.value):
            return "change"
        if intent == Intent.CURATE.value:
            return "curate"
        return "wait_user"

    def _route_after_librarian(self, state: dict) -> str:
        if self._failed(state):
            return "finish"
        if state.get("intent") == Intent.MEMORY_QUERY.value:
            return "source_check"
        return "context"

    def _route_after_snapshot(self, state: dict) -> Any:
        if self._failed(state):
            return "finish"
        if state.get("intent") in (Intent.PLAN.value, Intent.REPLAN.value):
            return "planner_demands"
        # §10: cada "+" é leitura independente do snapshot comum — as duas
        # leituras partem do mesmo snapshot materializado.
        return ["curator_retrieve", "librarian_retrieve"]

    def _route_after_confirm(self, state: dict) -> str:
        if self._failed(state):
            return "finish"
        if state.get("intent") == Intent.INGEST.value:
            return "commit_index"
        return "commit_confirmations"

    def _route_after_plan_confirm(self, state: dict) -> str:
        if self._failed(state):
            return "finish"
        resume = dict(state.get("resume_value") or {})
        if not resume.get("confirmed", False):
            return "finish"  # demandas não confirmadas: nada é publicado
        return "solver"

    # ------------------------------------------------------------------
    # Classificação (§10)
    # ------------------------------------------------------------------

    def _node_classify(self, state: dict) -> dict:
        message = str(state.get("message") or "")
        payload = dict(state.get("payload") or {})
        try:
            explicit = _explicit_intent(message, payload)
        except EduAgentError as exc:
            return self._failure(state, exc)
        if explicit is Intent.ASK and lowered(message).startswith("/resume"):
            # Retomada (CLI `resume`, §12): nova entrada — a rota depende do
            # estado da sessão (item pendente → submit_answer).
            if state.get("pending_item_ref") or (
                (state.get("tutor_session") or {}).get("pending_item")
            ):
                explicit = Intent.SUBMIT_ANSWER
        if explicit is not None:
            return {"intent": explicit.value, "intent_classified": True}
        if self._classifier is None:
            # Sem modelo/classificador: pergunta antes de efeito (§10) —
            # nada é executado nesta invocação.
            return {
                "intent": None,
                "intent_classified": False,
                "pending_question": (
                    "Não consegui classificar seu pedido sem comando "
                    "explícito. Qual das ações você quer: ingest, ask, "
                    "practice, submit_answer, plan, replan, approve_plan, "
                    "update_activity, memory_query, correct_fact, "
                    "delete_data, export_calendar, curate ou cancel?"
                ),
                "status": _STATUS_WAITING,
            }
        limits = self._limits
        assert limits is not None
        try:
            intent, ambiguous = self._classifier.classify(
                message=message,
                limits=limits,
                deadline=self._deadline(),
                seed=int(state.get("seed") or 0),
            )
        except EduAgentError as exc:
            return self._failure(state, exc)
        if ambiguous:
            return {
                "intent": None,
                "intent_classified": False,
                "pending_question": (
                    f"Sua mensagem parece '{intent.value if intent else '?'}',"
                    " mas está ambígua. Confirme a ação antes de qualquer "
                    "efeito (mapa §10): qual das intenções você deseja?"
                ),
                "status": _STATUS_WAITING,
            }
        return {"intent": intent.value, "intent_classified": True}

    def _node_wait_user(self, state: dict) -> dict:
        result = dict(state.get("result") or {})
        result["intent_classified"] = bool(
            state.get("intent_classified", False)
        )
        result["waiting_for"] = "user"
        result["pending_question"] = state.get("pending_question")
        return {"result": result, "status": _STATUS_WAITING}

    # ------------------------------------------------------------------
    # Rota ingest (§10)
    # ------------------------------------------------------------------

    def _node_ingest_extract(self, state: dict) -> dict:
        require_tool(
            ToolName.DOCUMENT_EXTRACT,
            SenderRole.CURATOR,
            limits=self._limits,
        )
        curator = _require_service(self._curator, "curator", "ingest")
        payload = dict(state.get("payload") or {})
        data = payload.get("data")
        if not isinstance(data, (bytes, bytearray)) or not data:
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                "rota ingest exige payload['data'] (bytes do documento)",
            )
        result = curator.request_document_extract(
            SenderRole.CURATOR,
            user_id=str(state["user_id"]),
            course_id=str(payload.get("course_id") or ""),
            data=bytes(data),
            filename=payload.get("filename"),
            doc_id=payload.get("doc_id"),
        )
        return {
            "ingest": {
                "doc_id": result.doc_id,
                "version_id": result.version_id,
                "version_status": result.version_status,
                "mime": result.mime,
                "sha256": result.sha256,
                "original_path": result.original_path,
                "duplicate": bool(result.duplicate),
            },
            "artifact_refs": list(state.get("artifact_refs") or [])
            + [
                _ref_locator("artifact", result.doc_id),
                _ref_locator("artifact", result.version_id),
            ],
            "result": {
                "ingested": {
                    "doc_id": result.doc_id,
                    "version_id": result.version_id,
                    "version_status": result.version_status,
                    "original_path": result.original_path,
                }
            },
        }

    def _node_curator_facts(self, state: dict) -> dict:
        curator = _require_service(self._curator, "curator", "ingest")
        ingest = dict(state.get("ingest") or {})
        extraction = curator.curate_document(
            str(state["user_id"]),
            ingest["doc_id"],
            ingest["version_id"],
        )
        ambiguous = sum(
            1 for fact in extraction.facts if fact.validation != "ok"
        )
        return {
            "extraction": {
                "topics": len(extraction.topics),
                "facts": len(extraction.facts),
                "ambiguous": ambiguous,
                "conflicts": len(extraction.conflicts),
                "pending_items": len(extraction.pending_items),
                "persisted_fact_ids": list(extraction.persisted_fact_ids),
            },
            "artifact_refs": list(state.get("artifact_refs") or [])
            + [
                _ref_locator("fact", fid)
                for fid in extraction.persisted_fact_ids
            ],
        }

    def _node_ingest_validate(self, state: dict) -> dict:
        extraction = dict(state.get("extraction") or {})
        ambiguous = int(extraction.get("ambiguous") or 0)
        conflicts = int(extraction.get("conflicts") or 0)
        result = dict(state.get("result") or {})
        result["curated"] = {
            "topics": extraction.get("topics"),
            "fact_candidates": extraction.get("facts"),
            "ambiguous_facts": ambiguous,
            "conflicts": conflicts,
            "pending_items": extraction.get("pending_items"),
        }
        # §6.3: o usuário confirma ou corrige a tabela extraída — ambíguos/
        # conflitos precisam de confirmação (nó puro; efeito no commit).
        return {
            "result": result,
            "needs_confirmation": bool(ambiguous or conflicts),
        }

    def _node_confirm_if_needed(self, state: dict) -> dict:
        """Gate de confirmação (§10): nó PURO — o efeito fica nos nós de
        commit. O interrupt retoma o nó desde o início; nada aqui escreve."""
        if not state.get("needs_confirmation"):
            return {"resume_value": {"confirmed": True}}
        answer = interrupt(
            {
                "question": (
                    "Há fatos ambíguos/conflitos a confirmar (mapa §6.3) ou "
                    "durações/prazos a confirmar (mapa §9/§15.3). Confirmar?"
                ),
                "ambiguous": (state.get("extraction") or {}).get("ambiguous"),
                "conflicts": (state.get("extraction") or {}).get("conflicts"),
            }
        )
        confirmed = bool(
            isinstance(answer, Mapping) and answer.get("confirmed")
        )
        return {"resume_value": {"confirmed": confirmed}}

    def _node_commit_index(self, state: dict) -> dict:
        # §6.1: a publicação do índice ocorreu na ingestão (nova versão só
        # ativa após indexação completa); o commit idempotente dos fatos
        # candidatos ocorreu no Curador (§11). Este nó fecha a rota com os
        # refs do estado de domínio (autoridade; checkpoint não substitui
        # commit — §4/§11).
        ingest = dict(state.get("ingest") or {})
        extraction = dict(state.get("extraction") or {})
        resume = dict(state.get("resume_value") or {})
        result = dict(state.get("result") or {})
        confirmed = bool(resume.get("confirmed", True))
        result["confirmed"] = confirmed
        if state.get("needs_confirmation") and not confirmed:
            result["note"] = (
                "extração não confirmada: fatos ambíguos/conflitos ficam "
                "pendentes como candidatos; nada confirmado (§6.3)"
            )
        result["index"] = {
            "doc_id": ingest.get("doc_id"),
            "version_id": ingest.get("version_id"),
            "version_status": ingest.get("version_status"),
            "facts_persisted": extraction.get("persisted_fact_ids") or [],
        }
        return {"result": result, "status": _STATUS_COMPLETED}

    # ------------------------------------------------------------------
    # Rota ask/practice (§10)
    # ------------------------------------------------------------------

    def _node_snapshot(self, state: dict) -> dict:
        snapshot = self._store.materialize_snapshot(str(state["user_id"]))
        # §15.1: snapshot imutável em transação curta; agentes não hidratam a
        # versão atual silenciosamente — commits usam a revisão lida aqui.
        return {
            "snapshot_version": int(snapshot.version),
            "snapshot_digest": snapshot.digest,
        }

    def _node_curator_retrieve(self, state: dict) -> dict:
        retrieval = _require_service(self._retrieval, "retrieval", "ask")
        if self._embedder is None:
            # Recurso configurado ausente → classe 3 do §12 (não é falha
            # interna): a rota ask/practice exige embedder (RAG denso, §6.5).
            raise _error(
                ErrorCode.SOURCE_UNRESOLVED,
                "recurso configurado ausente: embedder indisponível na rota "
                "ask/practice (RAG denso, §6.5; §12 classe 3)",
            )
        require_tool(
            ToolName.DOCUMENT_SEARCH,
            SenderRole.TUTOR,
            limits=self._limits,
        )
        query = content_of(state)
        if not query:
            raise _error(ErrorCode.SCHEMA_INVALID, "mensagem vazia")
        payload = dict(state.get("payload") or {})
        pack = retrieval.document_search(
            str(state["user_id"]),
            query,
            course_id=str(payload.get("course_id") or ""),
            embedder=self._embedder,
            sender_role=SenderRole.TUTOR,
        )
        # Leitura independente do snapshot comum (§10): sem efeitos. As
        # citações saem na forma do contrato ``SourceLocator``
        # (``doc:<uuid>@<ordinal>:p<página>:b<bloco>``, §4/§6.7).
        pack_dump = pack.model_dump(mode="json")
        citations: list[str] = []
        for chunk in pack.chunks:
            ref = chunk.source_ref
            ordinal = retrieval.version_ordinal(
                str(state["user_id"]), str(ref.doc_id), str(ref.version_id)
            )
            block = str(ref.block_id)
            match = re.match(r"^p\d+(.*)$", block)
            suffix = (
                match.group(1)
                if match and match.group(1)
                else (block if block.startswith("b") else f"b{block or '1'}")
            )
            citations.append(
                f"doc:{ref.doc_id}@{ordinal}:p{ref.physical_page}:{suffix}"
            )
        pack_dump["citations"] = citations
        return {"evidence": pack_dump}

    def _node_librarian_retrieve(self, state: dict) -> dict:
        librarian = _require_service(self._librarian, "librarian", "ask")
        # Leitura independente do snapshot comum (§10): a memória não altera
        # a evidência documental nem a política (fonte é dado rotulado).
        result = librarian.memory_query(
            str(state["user_id"]),
            content_of(state),
            sender_role=SenderRole.LIBRARIAN,
        )
        pack = result.pack
        return {
            "memory_summary": {
                "current_fact_entities": [
                    str(fact.entity_id) for fact in pack.current_facts
                ],
                "contradictions_pending": len(pack.contradictions),
                "selected_event_refs": [event.ref for event in result.selected_events],
                "rankings": list(result.rankings),
            }
        }

    def _node_context(self, state: dict) -> dict:
        """Montagem de contexto (§7/§10): fontes rotuladas; as citações
        permitidas do turno são SOMENTE as do EvidencePack (anti-citação
        fictícia, §6.8). A citação usa o locator do contrato
        ``SourceLocator`` (``doc:<uuid>@<versão>:p<página>:b<bloco>``)."""
        evidence = dict(state.get("evidence") or {})
        citations = list(evidence.get("citations") or [])
        views = []
        for index, chunk in enumerate(evidence.get("chunks") or []):
            source = dict(chunk.get("source_ref") or {})
            locator = (
                citations[index]
                if index < len(citations)
                else _source_locator(source)
            ) or f"chunk:{index}"
            views.append(
                {
                    "chunk_id": str(chunk.get("id") or index),
                    "text": str(chunk.get("text") or ""),
                    "citation": locator,
                    "source_ref": source or None,
                }
            )
        return {
            "tutor_evidence": {
                "chunks": views,
                "coverage": str(evidence.get("coverage") or "none"),
                "topic_ids": [
                    str(t) for t in (evidence.get("topic_ids") or [])
                ],
            }
        }

    def _node_tutor(self, state: dict) -> dict:
        tutor = _require_service(self._tutor, "tutor", "ask/practice")
        session = self._session_from_state(state)
        evidence_data = dict(state.get("tutor_evidence") or {})
        from eduagent.agents.tutor import ChunkView, TutorEvidence

        chunks = tuple(
            ChunkView(
                chunk_id=str(c["chunk_id"]),
                text=str(c["text"]),
                citation=str(c["citation"]),
                source_ref=SourceRef.model_validate(c["source_ref"])
                if c.get("source_ref")
                else None,
            )
            for c in (evidence_data.get("chunks") or [])
        )
        evidence = TutorEvidence(
            chunks=chunks,
            coverage=str(evidence_data.get("coverage") or "none"),
            topic_ids=tuple(evidence_data.get("topic_ids") or ()),
        )
        intent = state.get("intent")
        if intent == Intent.PRACTICE.value:
            move = (
                StudentMove.REQUEST_HINT
                if session.pending_item is not None
                else StudentMove.PRACTICE
            )
        else:
            move = StudentMove.ASK_DIRECT
        outcome = tutor.handle(
            session,
            move,
            content_of(state),
            evidence=evidence,
            topic_ids=[
                str(t)
                for t in (dict(state.get("payload") or {}).get("topic_ids") or ())
            ]
            or None,
        )
        return {
            "tutor_session": self._session_to_state(session),
            "tutor_outcome": {
                "turn": outcome.turn.model_dump(mode="json"),
                "item": (
                    outcome.item.model_dump(mode="json")
                    if outcome.item is not None
                    else None
                ),
                "general": bool(outcome.general),
                "solution_exposed_in_session": bool(
                    outcome.solution_exposed_in_session
                ),
            },
        }

    def _node_tutor_validate(self, state: dict) -> dict:
        outcome = dict(state.get("tutor_outcome") or {})
        if not outcome:
            raise _error(
                ErrorCode.INTERNAL_FAILURE,
                "turno do tutor ausente para validar",
            )
        turn = TutorTurn.model_validate(outcome["turn"])
        if turn.terminal is None:
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                "turno sem terminal de invocação explícito (mapa §8)",
            )
        evidence = dict(state.get("tutor_evidence") or {})
        allowed = {
            str(c.get("citation")) for c in (evidence.get("chunks") or [])
        }
        for citation in turn.citations:
            if str(citation) not in allowed:
                # Citação fora do conjunto permitido: falha controlada, nunca
                # publicação com citação fictícia (§6.8/§10).
                raise _error(
                    ErrorCode.SCHEMA_INVALID,
                    f"citação fora das fontes rotuladas do turno: {citation}",
                )
        return {"validated_turn": turn.model_dump(mode="json")}

    def _node_publish_wait(self, state: dict) -> dict:
        outcome = dict(state.get("tutor_outcome") or {})
        turn = TutorTurn.model_validate(outcome["turn"])
        item = outcome.get("item")
        updates: dict[str, Any] = {}
        refs = list(state.get("artifact_refs") or [])
        if item is not None:
            item_ref = f"item:{item['item_id']}@{item['version']}"
            updates["pending_item_ref"] = item_ref
            refs.append(item_ref)
        if turn.terminal == TutorTurn.Terminal.WAITING_STUDENT:
            updates["status"] = _STATUS_WAITING
        else:
            updates["status"] = _STATUS_COMPLETED
        updates["artifact_refs"] = refs
        result = dict(state.get("result") or {})
        result["turn"] = turn.model_dump(mode="json")
        result["waiting_student"] = (
            turn.terminal == TutorTurn.Terminal.WAITING_STUDENT
        )
        updates["result"] = result
        return updates

    # ------------------------------------------------------------------
    # Rota submit_answer (§10)
    # ------------------------------------------------------------------

    def _load_item_event(self, user_id: str, item_id: str) -> dict[str, Any]:
        rows = self._store.fetch_user_rows(
            "SELECT payload_json FROM events WHERE user_id = ? AND "
            "kind = 'item_published' AND payload_json LIKE ? ORDER BY rowid "
            "DESC",
            (user_id, f'%"{item_id}"%'),
        )
        if not rows:
            raise _error(
                ErrorCode.SOURCE_UNRESOLVED,
                f"item {item_id} não resolve no domínio (estado de domínio "
                "é autoridade; §11)",
            )
        return json.loads(str(rows[0]["payload_json"]))

    def _node_resolve_pending_item(self, state: dict) -> dict:
        _require_service(self._assessment, "assessment", "submit")
        session_state = dict(state.get("tutor_session") or {})
        pending_ref = state.get("pending_item_ref")
        pending_item = session_state.get("pending_item")
        if not pending_ref and not pending_item:
            raise _error(
                ErrorCode.AMBIGUOUS_INPUT,
                "nenhum item pendente nesta sessão para submeter resposta "
                "(mapa §10: resolve_pending_item)",
            )
        item: dict[str, Any]
        if pending_item:
            # O item pendente vem do checkpoint (refs + dados de turno, §4).
            item = dict(pending_item)
            payload = self._load_item_event(
                str(state["user_id"]), str(item["item_id"])
            )
        else:
            ref = Ref.model_validate(pending_ref)
            payload = self._load_item_event(
                str(state["user_id"]), str(ref.id)
            )
            item = {
                "item_id": payload["item_id"],
                "family_id": payload["family_id"],
                "version": ref.version,
                "topic_ids": (payload.get("exposure") or {}).get("topic_ids")
                or [],
                "prompt": payload["prompt"],
                "expected_answer_ref": None,
                "rubric_ref": None,
                "source_refs": payload["source_refs"],
                "kind": payload["kind"],
                "published_at": payload["published_at"],
            }
        # Gabarito/rubrica/fontes vêm do evento de publicação (solução
        # separada do enunciado, §8; domínio é autoridade, §11).
        item.setdefault("prompt", payload["prompt"])
        item["expected_answer"] = payload["expected_answer"]
        item["rubric"] = payload["rubric"]
        item["source_refs"] = payload["source_refs"]
        item["kind"] = payload["kind"]
        if not item.get("topic_ids"):
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                "item publicado sem tópicos: tentativa não atualiza "
                "competência (mapa §15.2)",
            )
        response = content_of(state)
        if not response:
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                "resposta vazia: submission exige resposta original (§8)",
            )
        operation_ids = dict(state.get("operation_ids") or {})
        operation_ids.setdefault("attempt", str(_uuid.uuid4()))
        operation_ids.setdefault("assessment", str(_uuid.uuid4()))
        return {"pending_item": item, "operation_ids": operation_ids}

    def _node_monitor(self, state: dict) -> dict:
        assessment = _require_service(self._assessment, "assessment", "submit")
        item = dict(state.get("pending_item") or {})
        session_state = dict(state.get("tutor_session") or {})
        occurred = self._clock().astimezone(timezone.utc)
        help_level = int(
            (session_state.get("help_level_by_item") or {}).get(
                str(item["item_id"]), 0
            )
        )
        revealed = bool(session_state.get("revealed"))
        family_seen = {
            _uuid.UUID(f)
            for f in (session_state.get("family_solution_seen") or [])
        }
        solution_seen = (
            _uuid.UUID(str(item["family_id"])) in family_seen
            if item.get("family_id")
            else False
        )
        record = assessment.record_attempt(
            user_id=str(state["user_id"]),
            session_id=str(state.get("session_id")),
            item_id=_uuid.UUID(str(item["item_id"])),
            family_id=_uuid.UUID(str(item["family_id"])),
            response_text=content_of(state),
            help_level=help_level,
            revealed=revealed,
            family_solution_seen_in_session=solution_seen,
            occurred_at=occurred,
            operation_id=(state.get("operation_ids") or {}).get("attempt"),
        )
        topic_ids = [str(t) for t in item["topic_ids"]]
        rubric = tuple(
            _rubric_from_payload(payload, topic_ids)
            for payload in (item.get("rubric") or [])
        )
        source_refs = [
            SourceRef.model_validate(payload)
            for payload in (item.get("source_refs") or [])
        ]
        mode = (
            MonitorMode.DETERMINISTIC
            if item.get("kind") == "quiz"
            else MonitorMode.TEXT
        )
        monitor_input = MonitorInput(
            attempt_id=record.attempt_id,
            item_ref=Ref(
                kind="item",
                id=_uuid.UUID(str(item["item_id"])),
                version=int(item.get("version") or 1),
            ),
            assessment_revision=1,
            supersedes=None,
            prompt=str(item.get("prompt") or ""),
            response=content_of(state),
            expected_answer=str(item.get("expected_answer") or ""),
            rubric=rubric,
            source_refs=source_refs,
            mode=mode,
            help_level=help_level,
            revealed=revealed,
            family_solution_seen_in_session=solution_seen,
        )
        outcome = self._monitor.evaluate(
            monitor_input, grader=self._rubric_grader
        )
        abstention = None
        if outcome.abstention is not None:
            abstention = {
                "trigger": outcome.abstention.trigger.value,
                "code": outcome.abstention.error_code.value,
                "detail": outcome.abstention.detail,
            }
        return {
            "attempt_record": {
                "attempt_id": str(record.attempt_id),
                "attempt_ordinal": record.attempt_ordinal,
                "help_level": help_level,
                "revealed": revealed,
            },
            "monitor_outcome": {
                "accepted": bool(outcome.accepted),
                "assessment": outcome.assessment.model_dump(mode="json"),
                "abstention": abstention,
            },
        }

    def _node_answer_validate(self, state: dict) -> dict:
        outcome = dict(state.get("monitor_outcome") or {})
        if outcome.get("assessment") is None:
            # Abstinência do Monitor: falha controlada com motivo tipado
            # (§8) — nunca julgamento inventado.
            abstention = dict(outcome.get("abstention") or {})
            raise EduAgentError(
                ErrorCode(abstention.get("code", ErrorCode.NO_EVIDENCE.value)),
                str(abstention.get("detail") or "avaliação em abstinência"),
            )
        assessment = Assessment.model_validate(outcome["assessment"])
        rubric = (state.get("pending_item") or {}).get("rubric") or []
        critical = [
            criterion["criterion_id"]
            for criterion in rubric
            if criterion.get("critical")
        ]
        for result in assessment.criterion_results:
            if (
                result.evidence_kind == Assessment.EvidenceKind.PRESENT
                and result.response_span is None
            ):
                raise _error(
                    ErrorCode.SCHEMA_INVALID,
                    "critério present sem span da resposta (§15.2)",
                )
        return {
            "validated_assessment": assessment.model_dump(mode="json"),
            "critical_criterion_ids": critical,
        }

    def _node_commit_assessment(self, state: dict) -> dict:
        assessment = _require_service(self._assessment, "assessment", "submit")
        validated = Assessment.model_validate(state["validated_assessment"])
        result = assessment.check(
            user_id=str(state["user_id"]),
            session_id=str(state.get("session_id")),
            assessment=validated,
            critical_criterion_ids=list(
                state.get("critical_criterion_ids") or []
            ),
            operation_id=(state.get("operation_ids") or {}).get("assessment"),
        )
        # §15.1: escrita nova após leitura exige reload para o próximo commit
        # — o snapshot do turno fica obsoleto após o commit.
        return {
            "assessment_result": {
                "assessment_id": str(result.assessment_id),
                "accepted": bool(result.accepted),
                "receipt": result.receipt.to_json(),
                "topic_states": {
                    str(topic): state_payload.model_dump(mode="json")
                    for topic, state_payload in result.topic_states.items()
                },
            },
            "artifact_refs": list(state.get("artifact_refs") or [])
            + [_ref_locator("assessment", result.assessment_id)],
        }

    def _node_feedback(self, state: dict) -> dict:
        result = dict(state.get("result") or {})
        assessment = dict(state.get("assessment_result") or {})
        raw = dict(state.get("validated_assessment") or {})
        result["feedback"] = {
            "correctness": raw.get("correctness"),
            "help_level": (state.get("attempt_record") or {}).get("help_level"),
            "topic_states": assessment.get("topic_states") or {},
        }
        session_state = dict(state.get("tutor_session") or {})
        submitted_item = str((state.get("pending_item") or {}).get("item_id"))
        pending = (session_state.get("pending_item") or {}).get("item_id")
        if pending and str(pending) == submitted_item:
            session_state["pending_item"] = None
        return {
            "result": result,
            "tutor_session": session_state,
            "pending_item_ref": None,
        }

    def _node_optional_review_request(self, state: dict) -> dict:
        demands = _require_service(self._demands, "demands", "submit")
        validated = Assessment.model_validate(state["validated_assessment"])
        critical_ids = set(state.get("critical_criterion_ids") or [])
        result = dict(state.get("result") or {})
        topic_states = dict(
            (state.get("assessment_result") or {}).get("topic_states") or {}
        )
        critical_error = any(
            r.level == 0 and r.criterion_id in critical_ids
            for r in validated.criterion_results
        )
        generated: list[dict[str, Any]] = []
        topic_ids = sorted(
            {
                str(topic)
                for r in validated.criterion_results
                for topic in r.topic_ids
            }
        )
        for topic_id in topic_ids:
            topic_state = topic_states.get(topic_id) or {}
            correctness = _topic_correctness(validated, topic_id)
            if correctness in ("incorrect", "partial"):
                outcome = PolicyOutcome.REVIEW_AFTER_ERROR
            elif correctness == "correct":
                outcome = PolicyOutcome.RECOVERY_AFTER_CORRECT
            else:
                continue  # undecidable não atualiza competência (§15.2)
            generation = demands.generate_review_demand(
                str(state["user_id"]),
                topic_id=_uuid.UUID(topic_id),
                occurrence_utc=self._clock().astimezone(timezone.utc),
                outcome=outcome,
                critical_error=critical_error,
                evidence_ids=[validated.attempt_id],
            )
            generated.append(
                {
                    "demand_ids": [
                        str(d.demand_id) for d in generation.demands
                    ],
                    "topic_id": topic_id,
                    "outcome": outcome.value,
                    "created": bool(generation.created),
                    "consolidated": bool(generation.consolidated),
                }
            )
        result["review_requests"] = generated
        return {"result": result}

    # ------------------------------------------------------------------
    # Rota plan/replan (§10)
    # ------------------------------------------------------------------

    def _node_planner_demands(self, state: dict) -> dict:
        demands = _require_service(self._demands, "demands", "plan")
        pending = demands.pending_demands(str(state["user_id"]))
        if not pending:
            raise _error(
                ErrorCode.AMBIGUOUS_INPUT,
                "nenhuma demanda pendente para planejar (§9): gere demandas "
                "por avaliação ou confirme durações antes",
            )
        result = dict(state.get("result") or {})
        result["pending_demands"] = [
            {
                "demand_id": str(record.demand_id),
                "kind": record.demand.kind.value,
                "duration_status": record.demand.duration_status.value,
                "duration_minutes": record.demand.duration_minutes,
                "mandatory": record.demand.mandatory,
                "deadline": str(record.demand.deadline),
            }
            for record in pending
        ]
        # §9/§15.3: duração estimada e prazo só-de-dia exigem confirmação
        # antes do plano (nó puro; efeito em commit_confirmations).
        needs = any(
            record.demand.duration_status.value == "estimated"
            or isinstance(record.demand.deadline, date)
            for record in pending
        )
        operation_ids = dict(state.get("operation_ids") or {})
        for record in pending:
            operation_ids.setdefault(
                f"confirm:{record.demand_id}", str(_uuid.uuid4())
            )
        operation_ids.setdefault("approval", str(_uuid.uuid4()))
        return {
            "result": result,
            "pending_demands": [
                {
                    "demand_id": str(record.demand_id),
                    "topic_id": str(record.topic_id),
                    "activity_kind": record.activity_kind,
                    "duration_minutes": record.demand.duration_minutes,
                    "mandatory": record.demand.mandatory,
                    "priority_class": record.demand.priority_class,
                    "earliest": record.demand.earliest.isoformat(),
                    "deadline": str(record.demand.deadline),
                    "dependencies": [
                        str(d) for d in record.demand.dependencies
                    ],
                    "duration_status": record.demand.duration_status.value,
                }
                for record in pending
            ],
            "needs_confirmation": needs,
            "operation_ids": operation_ids,
        }

    def _node_commit_confirmations(self, state: dict) -> dict:
        demands = _require_service(self._demands, "demands", "plan")
        resume = dict(state.get("resume_value") or {})
        if not resume.get("confirmed", False):
            return {"resume_value": resume, "confirmations_applied": []}
        edits = dict(resume.get("durations") or {})
        applied = []
        for demand_id, minutes in sorted(edits.items()):
            record = demands.confirm_duration(
                str(state["user_id"]),
                demand_id,
                minutes=int(minutes),
                mandatory=True,
                operation_id=(state.get("operation_ids") or {}).get(
                    f"confirm:{demand_id}"
                ),
            )
            applied.append(
                {
                    "demand_id": str(record.demand_id),
                    "duration_minutes": record.demand.duration_minutes,
                    "mandatory": record.demand.mandatory,
                }
            )
        return {"resume_value": resume, "confirmations_applied": applied}

    def _default_problem(
        self,
        user_id: str,
        pending: Sequence[Mapping[str, Any]],
        snapshot_version: int | None,
    ) -> SchedulingProblem:
        """Problema com disponibilidade default de ENSAIO (não medido):
        seg–sex 08:00–12:00 e 14:00–18:00 (UTC enquanto a timezone não for
        confirmada, mapa §3). Substituível por ``build_problem``."""
        now = self._clock().astimezone(timezone.utc)
        horizon_start: date = now.date()
        windows = []
        day = horizon_start
        for _ in range(7):
            if day.weekday() < 5:
                for start, end in _DEFAULT_WINDOWS:
                    windows.append(
                        TimeWindow(day=day, start_minute=start, end_minute=end)
                    )
            day += timedelta(days=1)
        solver_demands = []
        for record in pending:
            earliest = datetime.fromisoformat(str(record["earliest"]))
            if earliest.tzinfo is None:
                earliest = earliest.replace(tzinfo=timezone.utc)
            deadline_raw = str(record["deadline"])
            deadline: Any
            if "T" in deadline_raw or "Z" in deadline_raw:
                deadline = datetime.fromisoformat(
                    deadline_raw.replace("Z", "+00:00")
                )
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
            else:
                deadline = date.fromisoformat(deadline_raw)
            solver_demands.append(
                SolverDemand(
                    demand_id=_uuid.UUID(str(record["demand_id"])),
                    duration_minutes=int(record["duration_minutes"]),
                    mandatory=bool(record["mandatory"]),
                    priority_class=int(record["priority_class"]),
                    earliest_utc=earliest,
                    deadline=deadline,
                    dependencies=tuple(
                        _uuid.UUID(d)
                        for d in (record.get("dependencies") or [])
                    ),
                )
            )
        return SchedulingProblem(
            user_id=user_id,
            horizon_start=horizon_start,
            local_timezone=None,  # timezone só após confirmação (mapa §3)
            snapshot_version=int(snapshot_version or 0),
            demands=tuple(solver_demands),
            availability=tuple(windows),
        )

    def _problem_of(self, state: dict) -> SchedulingProblem:
        pending = list(state.get("pending_demands") or [])
        if self._build_problem is not None:
            return self._build_problem(
                str(state["user_id"]), pending, state.get("snapshot_version")
            )
        return self._default_problem(
            str(state["user_id"]), pending, state.get("snapshot_version")
        )

    def _node_solver(self, state: dict) -> dict:
        require_tool(
            ToolName.SCHEDULE_SOLVE, SenderRole.PLANNER, limits=self._limits
        )
        problem = self._problem_of(state)
        solve_result = solve_schedule(
            problem,
            sender_role=SenderRole.PLANNER,
            settings=self._solver_settings,
            clock=self._clock,
        )
        return {
            "solve_result": {
                "proposal": solve_result.proposal.model_dump(mode="json"),
                "proofs": [
                    {"stage": p.stage, "status": p.status, "value": p.value}
                    for p in solve_result.proofs
                ],
            },
        }

    def _node_independent_check(self, state: dict) -> dict:
        """Verificador independente separado (§9): revalida a proposta contra
        o problema confirmado. Divergência não é votada — falha controlada."""
        solve = dict(state.get("solve_result") or {})
        proposal = ScheduleProposal.model_validate(solve.get("proposal") or {})
        if proposal.status not in (
            ScheduleProposal.SolverStatus.OPTIMAL,
            ScheduleProposal.SolverStatus.FEASIBLE,
        ):
            raise _error(
                ErrorCode.INTERNAL_FAILURE,
                f"solver devolveu status {proposal.status.value} sem proposta "
                "publicável (§9: UNKNOWN é inconclusivo; INFEASIBLE é conflito "
                "provado)",
            )
        validation = verify_schedule(
            self._problem_of(state),
            proposal,
            settings=self._solver_settings,
            clock=self._clock,
        )
        if not validation.passed:
            raise _error(
                ErrorCode.INTERNAL_FAILURE,
                "verificador independente recusou a proposta do solver "
                f"(§9): {list(validation.issues)[:3]}",
            )
        return {"independent_validation": {"passed": True}}

    def _node_preview(self, state: dict) -> dict:
        solve = dict(state.get("solve_result") or {})
        proposal = ScheduleProposal.model_validate(solve.get("proposal") or {})
        result = dict(state.get("result") or {})
        result["preview"] = {
            "plan_id": str(proposal.plan_id),
            "revision": proposal.revision,
            "status": proposal.status.value,
            "diff": proposal.diff.model_dump(mode="json"),
            "unmet_demands": [str(u) for u in proposal.unmet_demands],
            "blocks": len(proposal.blocks),
            "explanation": proposal.explanation,
        }
        return {
            "result": result,
            "pending_plan": proposal.model_dump(mode="json"),
            "artifact_refs": list(state.get("artifact_refs") or [])
            + [_ref_locator("plan", proposal.plan_id, proposal.revision)],
        }

    def _node_wait_approval(self, state: dict) -> dict:
        """Preview → wait (§10): espera por confirmação é interrupt — o nó é
        puro e é retomado desde o início; a aprovação é commit idempotente
        em nó separado."""
        if not state.get("pending_plan"):
            return {"resume_value": {"approved": False}}
        answer = interrupt(
            {
                "question": (
                    "Aprovar o plano proposto? (preview no resultado)"
                ),
                "preview": (state.get("result") or {}).get("preview"),
            }
        )
        approved = bool(
            isinstance(answer, Mapping) and answer.get("approved")
        )
        return {"resume_value": {"approved": approved}}

    def _node_commit_approval(self, state: dict) -> dict:
        calendar = _require_service(self._calendar, "calendar", "approve")
        pending_plan = state.get("pending_plan")
        resume = dict(state.get("resume_value") or {})
        result = dict(state.get("result") or {})
        if pending_plan is None or not resume.get("approved", False):
            # Plano recusado no gate (§9): nada é publicado.
            result["approved"] = False
            result["note"] = "plano não aprovado: nada publicado (§9)"
            return {"result": result, "status": _STATUS_COMPLETED}
        proposal = ScheduleProposal.model_validate(pending_plan)
        approve = calendar.approve_plan(
            str(state["user_id"]),
            proposal,
            operation_id=(state.get("operation_ids") or {}).get("approval"),
            create_outbox=bool(
                (state.get("payload") or {}).get("create_outbox")
            ),
        )
        result["approved"] = True
        result["approval"] = {
            "plan_id": str(proposal.plan_id),
            "revision": proposal.revision,
            "confirmation_digest": approve.confirmation.digest,
            "receipt": approve.receipt.to_json(),
            "outbox_created": bool(approve.outbox_created),
        }
        return {
            "result": result,
            "approved_plan_id": str(proposal.plan_id),
            "status": _STATUS_COMPLETED,
        }

    # ------------------------------------------------------------------
    # Rota approve_plan (§10)
    # ------------------------------------------------------------------

    def _node_validate_approval(self, state: dict) -> dict:
        pending_plan = state.get("pending_plan")
        if not pending_plan:
            raise _error(
                ErrorCode.SOURCE_UNRESOLVED,
                "nenhum plano pendente nesta sessão para aprovar "
                "(rota approve_plan exige preview anterior)",
            )
        proposal = ScheduleProposal.model_validate(pending_plan)
        if proposal.status not in (
            ScheduleProposal.SolverStatus.OPTIMAL,
            ScheduleProposal.SolverStatus.FEASIBLE,
        ) or not proposal.validation.passed:
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                "só plano validado pelo verificador independente é "
                "aprovável (§9)",
            )
        # Validação de revisão/digest (§15.1): a aprovação confere revisão/
        # digest no commit — calendar.approve_plan recusa divergência com
        # VERSION_CONFLICT (nova escrita de domínio invalida o preview).
        operation_ids = dict(state.get("operation_ids") or {})
        operation_ids.setdefault("approval", str(_uuid.uuid4()))
        return {"operation_ids": operation_ids}

    # ------------------------------------------------------------------
    # Rota update_activity (§10)
    # ------------------------------------------------------------------

    def _node_validate_transition(self, state: dict) -> dict:
        planner = _require_service(
            self._planner, "planner", "update_activity"
        )
        payload = dict(state.get("payload") or {})
        try:
            update = ActivityUpdate.model_validate(
                payload.get("activity") or {}
            )
        except ValidationError as exc:
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                f"ActivityUpdate viola o contrato (§15.4): {exc}",
            ) from exc
        block = planner.get_block(str(state["user_id"]), update.block_id)
        if block is None:
            raise _error(
                ErrorCode.SOURCE_UNRESOLVED,
                f"bloco {update.block_id} não resolve para o usuário",
            )
        operation_ids = dict(state.get("operation_ids") or {})
        operation_ids.setdefault("activity", str(update.operation_id))
        return {
            "activity_update": update.model_dump(mode="json"),
            "operation_ids": operation_ids,
        }

    def _node_commit_event(self, state: dict) -> dict:
        planner = _require_service(
            self._planner, "planner", "update_activity"
        )
        update = ActivityUpdate.model_validate(state["activity_update"])
        # Transição ordinária; sair de completed é recusa do serviço
        # (correção explícita é caminho separado, §15.4).
        activity = planner.update_activity(str(state["user_id"]), update)
        return {
            "activity_result": {
                "block_id": str(activity.block.block_id),
                "status": activity.block.status,
                "receipt": activity.receipt.to_json(),
                "replan_requested": bool(activity.replan_requested),
                "end_conflict": bool(activity.end_conflict),
            },
            "artifact_refs": list(state.get("artifact_refs") or [])
            + [_ref_locator("block", activity.block.block_id)],
        }

    def _node_optional_replan(self, state: dict) -> dict:
        activity = dict(state.get("activity_result") or {})
        result = dict(state.get("result") or {})
        result["activity"] = activity
        # §15.4: transição que muda ocupação futura dispara replan uma vez
        # por evento — o replan em si é um novo turno com intenção replan.
        result["replan_available"] = bool(activity.get("replan_requested"))
        return {"result": result, "status": _STATUS_COMPLETED}

    # ------------------------------------------------------------------
    # Rota export_calendar (§10)
    # ------------------------------------------------------------------

    def _node_resolve_approved_plan(self, state: dict) -> dict:
        calendar = _require_service(self._calendar, "calendar", "export")
        payload = dict(state.get("payload") or {})
        plan_id = payload.get("plan_id") or state.get("approved_plan_id")
        if not plan_id and state.get("pending_plan"):
            plan_id = str(
                ScheduleProposal.model_validate(state["pending_plan"]).plan_id
            )
        if not plan_id:
            raise _error(
                ErrorCode.SOURCE_UNRESOLVED,
                "nenhum plano aprovado para exportar (§9: nenhum ICS sem "
                "plano confirmado)",
            )
        plan_key = str(_uuid.UUID(str(plan_id)))
        # §15.1: plano que não resolve é SOURCE_UNRESOLVED; plano resolvido
        # sem confirmação atual (ou invalidada) é VERSION_CONFLICT — novo
        # preview é exigido (§9).
        plan_rows = self._store.fetch_user_rows(
            "SELECT id FROM plans WHERE user_id = ? AND id = ?",
            (str(state["user_id"]), plan_key),
        )
        if not plan_rows:
            raise _error(
                ErrorCode.SOURCE_UNRESOLVED,
                f"plano {plan_key} não resolve para o usuário",
            )
        confirmation = self._current_confirmation(str(state["user_id"]), plan_key)
        if confirmation is None:
            raise _error(
                ErrorCode.VERSION_CONFLICT,
                f"plano {plan_key} sem confirmação: exportação exige plano "
                "confirmado e atual (§9/§15.1)",
            )
        calendar.check_confirmation_current(
            str(state["user_id"]), confirmation
        )
        return {"export_plan_id": plan_key}

    def _current_confirmation(self, user_id: str, plan_id: str):
        from eduagent.services.calendar import ConfirmationRecord

        rows = self._store.fetch_user_rows(
            "SELECT id, artifact_id, artifact_revision, digest, occurred_at, "
            "base_revision, approval_revision, dependencies_json "
            "FROM confirmations WHERE user_id = ? AND artifact_id = ? "
            "ORDER BY rowid DESC",
            (user_id, plan_id),
        )
        if not rows:
            return None
        row = rows[0]
        deps = json.loads(row["dependencies_json"] or "[]")
        if isinstance(deps, dict):
            dependencies = tuple(sorted(deps.items()))
        else:
            dependencies = tuple(tuple(d) for d in deps)
        return ConfirmationRecord(
            confirmation_id=_uuid.UUID(str(row["id"])),
            plan_id=_uuid.UUID(str(row["artifact_id"])),
            plan_revision=int(row["artifact_revision"]),
            digest=str(row["digest"]),
            occurred_at=datetime.fromisoformat(str(row["occurred_at"])),
            base_revision=int(row["base_revision"] or 0),
            approval_revision=int(row["approval_revision"] or 0),
            dependencies=dependencies,  # type: ignore[arg-type]
            dependencies_hash="",  # consulta atual usa domínio+dependências
        )

    def _node_render_ics(self, state: dict) -> dict:
        calendar = _require_service(self._calendar, "calendar", "export")
        require_tool(
            ToolName.CALENDAR_RENDER, SenderRole.PLANNER, limits=self._limits
        )
        render = calendar.render_plan(
            str(state["user_id"]),
            state["export_plan_id"],
            sender_role=SenderRole.PLANNER,
        )
        return {"ics": render.ics, "render_blocks": len(render.blocks)}

    def _node_ics_validate(self, state: dict) -> dict:
        from eduagent.services.calendar import parse_ics

        data = state.get("ics")
        if not data:
            raise _error(
                ErrorCode.INTERNAL_FAILURE,
                "ICS ausente para validar (§9)",
            )
        parsed = parse_ics(data)
        if parsed is None or not parsed.events:
            raise _error(
                ErrorCode.INTERNAL_FAILURE,
                "ICS vazio: exportação exige blocos do plano confirmado",
            )
        return {"ics_events": len(parsed.events)}

    def _node_publish_ics(self, state: dict) -> dict:
        data = state.get("ics")
        result = dict(state.get("result") or {})
        result["calendar"] = {
            "plan_id": state.get("export_plan_id"),
            "events": state.get("ics_events"),
            "bytes": len(data or b""),
        }
        if self._data_root is not None:
            # Path resolvido com ownership e bloqueio de traversal (§10).
            exports = resolve_owned_path(
                self._data_root,
                str(state["user_id"]),
                f"exports/{state['export_plan_id']}.ics",
            )
            exports.parent.mkdir(parents=True, exist_ok=True)
            exports.write_bytes(data or b"")
            result["calendar"]["path"] = str(exports)
        payload = dict(state.get("payload") or {})
        if payload.get("sync"):
            # [→ confirmed_outbox] (§10) é opcional e usa calendar.apply
            # (dispatcher determinístico, §11); sem conector admitido,
            # CONNECTOR_DISABLED mantendo ICS/preview (§9). O conector
            # CalDAV admitido na task 016 entra por ``calendar_connector``
            # quando configurado (task 016, §9).
            calendar = _require_service(self._calendar, "calendar", "export")
            report = calendar.apply_plan(
                str(state["user_id"]),
                state["export_plan_id"],
                connector=self._calendar_connector,
                sender_role=SenderRole.SYSTEM,
            )
            result["calendar"]["sync"] = {
                "status": report.status.value,
                "detail": report.detail,
            }
        return {"result": result, "status": _STATUS_COMPLETED}

    # ------------------------------------------------------------------
    # Rota memory_query (§10)
    # ------------------------------------------------------------------

    def _node_source_check(self, state: dict) -> dict:
        _require_service(self._memory, "memory", "memory_query")
        summary = dict(state.get("memory_summary") or {})
        missing: list[str] = []
        for ref in summary.get("selected_event_refs") or []:
            locator = str(ref)
            raw_id = locator.split("@", 1)[0].split(":", 1)[-1]
            rows = self._store.fetch_user_rows(
                "SELECT id FROM events WHERE user_id = ? AND id = ?",
                (str(state["user_id"]), raw_id),
            )
            if not rows:
                missing.append(locator)
        for entity in summary.get("current_fact_entities") or []:
            rows = self._store.fetch_user_rows(
                "SELECT id FROM facts WHERE user_id = ? AND value_json LIKE ?",
                (str(state["user_id"]), f"%{entity}%"),
            )
            if not rows:
                missing.append(f"fact:{entity}")
        if missing:
            raise _error(
                ErrorCode.SOURCE_UNRESOLVED,
                f"fontes da memória não resolvem no snapshot: {missing[:3]}",
            )
        return {"sources_checked": True}

    def _node_answer(self, state: dict) -> dict:
        summary = dict(state.get("memory_summary") or {})
        result = dict(state.get("result") or {})
        # Resposta composta dos originais rotulados (§7): sem citação
        # fictícia — cada peça carrega a ref do evento/fato; contradição não
        # conciliada devolve ambos os registros (§7).
        result["memory_answer"] = {
            "sources": summary.get("selected_event_refs") or [],
            "current_facts": summary.get("current_fact_entities") or [],
            "contradictions_pending": summary.get(
                "contradictions_pending"
            )
            or 0,
        }
        return {"result": result, "status": _STATUS_COMPLETED}

    # ------------------------------------------------------------------
    # Rota correct_fact/delete_data (§10)
    # ------------------------------------------------------------------

    def _node_validate_scope(self, state: dict) -> dict:
        memory = _require_service(self._memory, "memory", "change")
        payload = dict(state.get("payload") or {})
        intent = state.get("intent")
        if intent == Intent.CORRECT_FACT.value:
            fact_id = payload.get("fact_id")
            if not fact_id:
                raise _error(
                    ErrorCode.SCHEMA_INVALID,
                    "correção de fato exige payload['fact_id']",
                )
            if not payload.get("corrected_value"):
                raise _error(
                    ErrorCode.SCHEMA_INVALID,
                    "correção de fato exige payload['corrected_value']",
                )
            fact = memory._fact_record(  # noqa: SLF001 — preview de correção
                str(state["user_id"]), str(fact_id)
            )
            if fact is None:
                raise _error(
                    ErrorCode.SOURCE_UNRESOLVED,
                    f"fato {fact_id} não resolve para o usuário",
                )
            return {"change": {"kind": "fact", "fact_id": str(fact_id)}}
        scope = payload.get("scope")
        if scope is None:
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                "deleção exige payload['scope'] (events/facts/summaries/all)",
            )
        ids = [str(i) for i in (payload.get("ids") or [])]
        # validate_scope (§10): escopo/ids são validados no preview — erro
        # tipado para escopo inválido ou ID que não resolve.
        return {"change": {"kind": "delete", "scope": str(scope), "ids": ids}}

    def _node_delete_preview(self, state: dict) -> dict:
        memory = _require_service(self._memory, "memory", "change")
        change = dict(state.get("change") or {})
        result = dict(state.get("result") or {})
        operation_ids = dict(state.get("operation_ids") or {})
        operation_ids.setdefault("change", str(_uuid.uuid4()))
        if change["kind"] == "fact":
            fact = memory._fact_record(  # noqa: SLF001
                str(state["user_id"]), change["fact_id"]
            )
            if fact is None:
                raise _error(
                    ErrorCode.SOURCE_UNRESOLVED,
                    f"fato {change['fact_id']} não resolve (preview)",
                )
            dependents = self._store.dependents_of(
                str(state["user_id"]),
                _ref_locator("fact", change["fact_id"]),
            )
            preview = {
                "kind": "fact",
                "fact_id": change["fact_id"],
                "current_value": fact.normalized_value,
                "dependents_to_invalidate": [
                    str(child.get("child_ref")) for child in dependents
                ],
            }
        else:
            preview_payload = memory.preview_delete(
                str(state["user_id"]),
                change["scope"],
                ids=change.get("ids") or (),
            )
            preview = {
                "kind": "delete",
                "scope": preview_payload.scope,
                "event_ids": list(preview_payload.event_ids),
                "fact_ids": list(preview_payload.fact_ids),
                "summary_ids": list(preview_payload.summary_ids),
                "backup_pending_until": preview_payload.backup_pending_until,
            }
        result["preview"] = preview
        return {"result": result, "operation_ids": operation_ids}

    def _node_confirm_change(self, state: dict) -> dict:
        """preview → confirm (§10): nó puro com interrupt; commit/invalidate
        em nó idempotente separado."""
        answer = interrupt(
            {
                "question": (
                    "Confirmar a alteração de dados? (preview no resultado)"
                ),
                "preview": (state.get("result") or {}).get("preview"),
            }
        )
        confirmed = bool(
            isinstance(answer, Mapping) and answer.get("confirmed")
        )
        return {"resume_value": {"confirmed": confirmed}}

    def _node_commit_invalidate(self, state: dict) -> dict:
        memory = _require_service(self._memory, "memory", "change")
        payload = dict(state.get("payload") or {})
        resume = dict(state.get("resume_value") or {})
        change = dict(state.get("change") or {})
        result = dict(state.get("result") or {})
        if not resume.get("confirmed", False):
            result["change_applied"] = False
            result["note"] = (
                "alteração não confirmada: nada commitado (§10)"
            )
            return {"result": result, "status": _STATUS_COMPLETED}
        operation_id = (state.get("operation_ids") or {}).get("change")
        if change["kind"] == "fact":
            correction = memory.correct_fact(
                user_id=str(state["user_id"]),
                fact_id=change["fact_id"],
                corrected_value=str(payload.get("corrected_value")),
                reason=str(payload.get("reason") or "correção do usuário"),
                operation_id=operation_id,
            )
            result["change_applied"] = True
            result["change"] = {
                "kind": "fact",
                "fact_id": change["fact_id"],
                "new_fact_id": str(correction.new_fact_id),
                "invalidated": [
                    str(x) for x in (correction.invalidated_refs or ())
                ],
            }
        else:
            deletion = memory.delete_data(
                user_id=str(state["user_id"]),
                scope=change["scope"],
                confirmed=True,
                reason=str(payload.get("reason") or "deleção confirmada"),
                ids=change.get("ids") or (),
                operation_id=operation_id,
            )
            result["change_applied"] = True
            result["change"] = {
                "kind": "delete",
                "scope": change["scope"],
                "tombstoned_refs": [
                    str(x) for x in (deletion.tombstoned_refs or ())
                ],
                "invalidated_refs": [
                    str(x) for x in (deletion.invalidated_refs or ())
                ],
            }
            # §5: deleção propaga a checkpoints — a deleção de todos os dados
            # de memória remove também os checkpoints da sessão do usuário.
            if change["scope"] == "all":
                self._checkpointer.delete_thread(str(state["session_id"]))
        return {"result": result, "status": _STATUS_COMPLETED}

    # ------------------------------------------------------------------
    # Rota curate (§10)
    # ------------------------------------------------------------------

    def _node_network_gate(self, state: dict) -> dict:
        require_tool(
            ToolName.WEB_SEARCH,
            SenderRole.CURATOR,
            network_enabled=self._network_enabled,
            connector_available=self._web_connector is not None,
            limits=self._limits,
        )
        return {"curate_connector": True}

    def _node_web_search(self, state: dict) -> dict:
        payload = dict(state.get("payload") or {})
        query = str(payload.get("query") or content_of(state) or "")
        if not query.strip():
            raise _error(
                ErrorCode.SCHEMA_INVALID, "consulta de curadoria vazia"
            )
        # Correção 016a (achado GLM-A2): ``max_results`` do payload é cortado
        # ANTES de chamar ``search`` — o backend nunca vê pedido acima do
        # limite normativo §6 (o corte defensivo pós-busca é mantido).
        candidates = self._web_connector.search(
            query,
            language=payload.get("language", "pt"),
            max_results=min(
                int(payload.get("max_results", _MAX_CANDIDATES)),
                _MAX_CANDIDATES,
            ),
        )
        # §6: até 5 candidatos — payload não amplia o limite normativo
        # (o conector também limita; corte defensivo em segunda camada).
        for candidate in list(candidates)[:_MAX_CANDIDATES]:
            # §10: destino validado por código; redirect revalidado abaixo.
            assert_public_url(str(candidate.get("url")))
        return {"web_candidates": list(candidates)}

    def _node_web_fetch(self, state: dict) -> dict:
        if not state.get("web_candidates"):
            return {"fetched": []}
        fetched = []
        for candidate in list(state.get("web_candidates") or [])[
            :_MAX_FETCHES
        ]:
            url = str(candidate["url"])
            resource = self._web_connector.fetch(url)
            # §10: o destino final é SEMPRE revalidado — mesmo quando o
            # conector devolve a URL original (DNS pode ter mudado entre a
            # validação da busca e o fetch; revalidação de redirect/DNS a
            # cada consulta, §10).
            final_url = str(resource.get("url") or url)
            assert_public_url(final_url)
            # Pré-condição contratual do conector real (task 016): se o
            # recurso expõe a cadeia de hops (``redirect_chain``, URLs
            # absolutas em ordem), CADA hop é revalidado contra o hop
            # anterior com ``assert_redirect_target`` ("dois redirects com
            # revalidação", §10) — recusa tipada bloqueia a rota inteira.
            hop_anterior = url
            for hop in [str(h) for h in resource.get("redirect_chain") or []]:
                assert_redirect_target(hop_anterior, hop)
                hop_anterior = hop
            fetched.append({**candidate, "resource": dict(resource)})
        return {"fetched": fetched}

    def _node_curator_rank(self, state: dict) -> dict:
        fetched = list(state.get("fetched") or [])
        seen: set[str] = set()
        ranked = []
        for item in fetched:
            url = str(item.get("url"))
            if url in seen:
                continue
            seen.add(url)
            ranked.append(item)
        return {"curate_ranked": ranked}

    def _node_validate_access_claims(self, state: dict) -> dict:
        result = dict(state.get("result") or {})
        claims = []
        for item in state.get("curate_ranked") or []:
            resource = dict(item.get("resource") or {})
            state_name = str(resource.get("state") or "metadata_only")
            # §6: vídeo sem transcrição só por metadados — nunca resumido.
            if state_name == "metadata_only":
                claims.append(
                    {
                        "url": item.get("url"),
                        "access": "metadata_only",
                        "note": "recomendável apenas por metadados (§6)",
                    }
                )
            else:
                claims.append(
                    {
                        "url": item.get("url"),
                        "access": state_name,
                        "hash": resource.get("hash"),
                        "captured_at": resource.get("captured_at"),
                    }
                )
        result["curated_web"] = claims
        return {"result": result, "status": _STATUS_COMPLETED}

    # ------------------------------------------------------------------
    # Rota cancel (§10: stop_dispatch → reconcile → persist → cancelled)
    # ------------------------------------------------------------------

    def _node_stop_dispatch(self, state: dict) -> dict:
        result = dict(state.get("result") or {})
        result["cancel"] = {
            "stage": "stop_dispatch",
            "note": "nenhum novo efeito é despachado após o cancelamento",
        }
        # Canal interno da rota cancel (não re-dispara a guarda de
        # cancelamento nos nós da própria rota).
        return {"result": result, "cancelling": True}

    def _node_reconcile_started_effects(self, state: dict) -> dict:
        result = dict(state.get("result") or {})
        if self._dispatcher is None:
            result["cancel"]["reconciled"] = {
                "claimed": 0,
                "acked": 0,
                "note": (
                    "sem outbox/despachante configurado: nada a reconciliar"
                ),
            }
            return {"result": result}
        # Efeitos já iniciados são reconciliados por identidade (§10/§11);
        # UNKNOWN_EFFECT permanece terminal, sem retry automático (§11).
        report = self._dispatcher.dispatch_pending(
            now=self._clock().astimezone(timezone.utc)
        )
        result["cancel"]["reconciled"] = {
            "claimed": report.claimed,
            "acked": report.acked,
            "requeued": report.requeued,
            "unknown_effect": list(report.unknown_effect),
        }
        return {"result": result}

    def _node_persist(self, state: dict) -> dict:
        # §10: persist — o estado do grafo é persistido pelo checkpointer
        # (durability=sync) e o estado de domínio já foi commitado pelos
        # serviços idempotentes; checkpoint não substitui commit (§4/§11).
        result = dict(state.get("result") or {})
        result["cancel"]["persisted"] = True
        return {"result": result}

    def _node_cancelled(self, state: dict) -> dict:
        error = typed_error_of(
            _error(
                ErrorCode.CANCELLED,
                "turno cancelado; efeitos já iniciados foram reconciliados "
                "(§10/§11)",
            )
        )
        return {
            "status": _STATUS_CANCELLED,
            "cancel_requested": True,
            "errors": list(state.get("errors") or [])
            + [error.model_dump(mode="json")],
        }

    # ------------------------------------------------------------------
    # Terminal (§12: terminal com estado definido e artefatos válidos)
    # ------------------------------------------------------------------

    def _node_finish(self, state: dict) -> dict:
        assert self._limits is not None
        status = state.get("status") or _STATUS_COMPLETED
        if status == "running":
            # Nenhum nó pediu espera/falha/cancelamento: terminal completed.
            status = _STATUS_COMPLETED
        result = dict(state.get("result") or {})
        if status == _STATUS_FAILED and not state.get("errors"):
            raise _error(
                ErrorCode.INTERNAL_FAILURE,
                "terminal failed sem erro tipado",
            )
        result["artifact_refs"] = list(state.get("artifact_refs") or [])
        return {
            "status": status,
            "result": result,
            "budget_snapshot": self._limits.to_dict(),
        }

    # ------------------------------------------------------------------
    # Sessão do tutor (checkpoint: item pendente, nível de ajuda, histórico)
    # ------------------------------------------------------------------

    @staticmethod
    def _session_to_state(session: TutorSession) -> dict[str, Any]:
        return {
            "state": session.state.value,
            "pending_item": (
                session.pending_item.model_dump(mode="json")
                if session.pending_item is not None
                else None
            ),
            "pending_skill": list(session.pending_skill),
            "help_level_by_item": dict(session.help_level_by_item),
            "revealed": session.revealed,
            "closed": session.closed,
            "family_solution_seen": sorted(
                str(f) for f in session.family_solution_seen
            ),
            "history": [
                turn.model_dump(mode="json") for turn in session.history
            ],
        }

    @staticmethod
    def _session_from_state(state: dict) -> TutorSession:
        data = dict(state.get("tutor_session") or {})
        if not data:
            return new_session(
                str(state["user_id"]), str(state["session_id"])
            )
        session = TutorSession(
            user_id=str(state["user_id"]),
            session_id=str(state["session_id"]),
            state=TutorTurn.TutorState(data.get("state", "explain")),
            pending_skill=tuple(data.get("pending_skill") or ("explain", 1)),
            help_level_by_item=dict(data.get("help_level_by_item") or {}),
            revealed=bool(data.get("revealed")),
            closed=bool(data.get("closed")),
            family_solution_seen={
                _uuid.UUID(f)
                for f in (data.get("family_solution_seen") or [])
            },
        )
        if data.get("pending_item"):
            session.pending_item = LearningItem.model_validate(
                data["pending_item"]
            )
        session.history = [
            TutorTurn.model_validate(turn)
            for turn in (data.get("history") or [])
        ]
        return session

    def close(self) -> None:
        if self._gate is not None:
            self._gate.close()


# ---------------------------------------------------------------------------
# Helpers locais
# ---------------------------------------------------------------------------


def BudgetsOf(**kwargs: Any):
    from eduagent.contracts import Budgets

    return Budgets(**kwargs)


def _rubric_from_payload(payload: Mapping[str, Any], topic_ids: list[str]):
    """``RubricCriterion`` a partir do payload do item publicado; critério
    sem tópicos herda os tópicos do item (rubrica por tópico, §15.2)."""
    data = dict(payload)
    data.setdefault("topic_ids", topic_ids)
    return RubricCriterion.model_validate(data)


def _topic_correctness(assessment: Assessment, topic_id: str) -> str:
    """Agregação por tópico da §15.2 (todos 2=correct; todos 0=incorrect;
    mistura=partial) — o serviço autoritativo já aplicou a regra; aqui é
    apenas o gatilho da política de revisão (§15.3)."""
    levels = [
        result.level
        for result in assessment.criterion_results
        if topic_id in {str(t) for t in result.topic_ids}
    ]
    if not levels:
        return "undecidable"
    if all(level == 2 for level in levels):
        return "correct"
    if all(level == 0 for level in levels):
        return "incorrect"
    return "partial"


def lowered(text: str) -> str:
    return (text or "").strip().lower()


def content_of(state: Mapping[str, Any]) -> str:
    """Conteúdo do turno sem o comando explícito (``/ask texto`` →
    ``texto``): comandos prevalecem para a ROTA (§10) e não entram no
    conteúdo usado como consulta/resposta."""
    text = str(state.get("message") or "")
    for prefix in _EXPLICIT_COMMANDS:
        if lowered(text).startswith(prefix):
            stripped = text[len(prefix):].strip()
            return stripped if stripped else text
    return text.strip()


def _source_locator(source: Mapping[str, Any]) -> str | None:
    """Locator ``doc:<uuid>@<versão>:p<página>:b<bloco>`` (contrato
    ``SourceLocator``, mapa §4) a partir do ``SourceRef`` do chunk; o
    ``block_id`` persistido pela ingestão (``p<página>b<ordem>``, 006a) é
    reduzido ao sufixo ``b<ordem>`` do locator."""
    doc_id = source.get("doc_id")
    version = source.get("version_id")
    page = source.get("physical_page")
    if not doc_id or not version or not page:
        return None
    block = str(source.get("block_id") or "")
    match = re.match(r"^p\d+(.*)$", block)
    suffix = match.group(1) if match and match.group(1) else (
        block if block.startswith("b") else f"b{block or '1'}"
    )
    return f"doc:{doc_id}@{version}:p{page}:{suffix}"


__all__ = ["EduAgentGraph", "LimitsConfig", "TurnResult"]
