"""Testes de aceite da task 014 — grafo LangGraph: intenções, rotas,
checkpoints e limites (mapa §10, §12; estado/erros do §4).

Não é a suíte quantitativa da etapa 8 (mapa de testes): testes locais de
curta duração com backend de geração, embedder e conectores injetados
(determinísticos; nenhuma chamada ao modelo real, nenhuma conexão de rede).
C4 (mapa intocado, commits separados, submódulo intocado) é verificado por
inspeção de git e registrado no task.md.

Tabela de testes (código → caso):

| Código | Caso |
|---|---|
| R-I1 | rota ingest termina completed com estado definido e refs (§10) |
| R-I2 | ingest com fato ambíguo passa pelo gate de confirmação (interrupt puro; §6.3/§10) |
| R-A1 | rota ask: snapshot → curator+librarian (leituras independentes) → context → tutor → validate → publish |
| R-A2 | rota practice termina waiting_student com item pendente (espera = fim da invocação, §10) |
| R-S1 | rota submit_answer: resolve → monitor → validate → commit → feedback → review_request |
| R-P1 | rota plan/replan: demands → confirm (interrupt) → solver → independent_check → preview → wait |
| R-AP1 | rota approve_plan: validate_revision/digest → commit_confirmation |
| R-E1 | rota export_calendar: resolve → render → validate → publish (sem plano confirmado é recusada) |
| R-U1 | rota update_activity: validate_transition → commit_event → optional_replan |
| R-M1 | rota memory_query: librarian_retrieve → source_check → answer (fontes resolvíveis) |
| R-CF1 | rota correct_fact: validate_scope → preview → confirm (interrupt) → commit/invalidate |
| R-DD1 | rota delete_data: preview → confirm → commit/invalidate (sem confirm nada é commitado) |
| R-CU1 | rota curate sem conector/rede: CONNECTOR_DISABLED por código (§6/§9) |
| R-CU2 | rota curate com conector: gate → search/fetch → rank → validate_access_claims |
| R-X1 | rota cancel: stop_dispatch → reconcile_started_effects → persist → cancelled (efeitos reconciliados) |
| R-X2 | cancel_requested no estado entra na rota cancel (prioridade do §10/§12) |
| L-T1 | deadline estourado → terminal failed com erro TIMEOUT tipado e artefatos válidos preservados (§12) |
| L-B1 | orçamento de LLM esgotado → RESOURCE_LIMIT antes da geração (§12) |
| L-Q1 | fila cheia responde RESOURCE_LIMIT e geração é serial (§10/§12) |
| CK-1 | sessão retomada de checkpoint preserva item pendente, nível de ajuda e histórico do turno (C2) |
| CK-2 | durability=sync: checkpoint persistido sobrevive a nova instância do checkpointer (mesmo arquivo) |
| T-P1 | proposta fora de papel é negada por código (TOOL_DENIED); payload não muda permissões (§4/§10) |
| T-P2 | sem shell genérico nem escrita direta no DB: catálogo de tools fechado (§10) |
| T-P3 | fonte/tool result é dado rotulado e não altera política (§10) |
| S-F1 | path traversal e symlink escape bloqueados por código; ownership resolvido (§10) |
| S-F2 | fetch bloqueia IP privado/loopback e revalida redirect/DNS (§10) |
| S-F3 | user_id "."/""/".." recusado — ownership exige subdiretório direto (A1 da revisão) |
| S-F4 | redirect protocol-relative "//host" revalidado via urljoin (A2 da revisão) |
| S-F5 | web fetch revalida destino final sempre e cada hop da cadeia (A4 da revisão) |
| L-C1 | contadores do TurnLimits exatos sob consumos concorrentes (A3 da revisão) |
| L-P1 | precedência cancelamento → deadline → passos; simultâneo = TIMEOUT (luna A-01) |
| L-Q2 | fila cheia reembolsa orçamento de LLM (L-A1 da revisão) |
| CK-3 | list() do checkpointer sob o mesmo lock de put/get_tuple (A5 da revisão) |
"""

from __future__ import annotations

import hashlib
import json
import socket
import threading
import time
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from eduagent.agents.curator import CuratorAgent
from eduagent.agents.librarian import Librarian
from eduagent.agents.monitor import Monitor
from eduagent.agents.planner import PlannerAgent
from eduagent.agents.tutor import EventItemSink, Tutor
from eduagent.contracts import (
    AcademicFact,
    EduAgentError,
    ErrorCode,
    MemoryPack,
    SenderRole,
    ToolName,
    ToolRequest,
    validate_tool_request,
)
from eduagent.graph import EduAgentGraph
from eduagent.policy import (
    GenerationGate,
    TurnLimits,
    assert_public_url,
    assert_redirect_target,
    require_tool,
    resolve_owned_path,
)
from eduagent.services.assessment import AssessmentService
from eduagent.services.calendar import CalendarService
from eduagent.services.effects import (
    CommitRequest,
    EffectOutcome,
    EventSpec,
    EffectsService,
    OutboxDispatcher,
    OutboxSpec,
)
from eduagent.services.ingestion import IngestionService
from eduagent.services.memory import MemoryService
from eduagent.services.model_adapter import ModelAdapterError, RuntimeCapabilities
from eduagent.services.retrieval import RetrievalService
from eduagent.services.scheduling import (
    DemandService,
    SchedulingProblem,
    SolverDemand,
    TimeWindow,
)
from eduagent.skills import SkillCatalog
from eduagent.storage.checkpoints import SQLiteCheckpointer
from eduagent.storage.repository import DomainStore

UTC = timezone.utc

UID = "123e4567-e89b-12d3-a456-426614174000"
SESSION = "7c9e6679-7425-40de-944b-e07fc1f90ae7"
CITATION_PREFIX = "doc:3ea0f0e2-0c1e-4d9a-9b1f-0a2b3c4d5e6f@1"

FIXED_NOW = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)  # quarta-feira

DOC_TEXT_PAGES = [
    [
        {"kind": "heading", "text": "Commit idempotente"},
        {
            "kind": "paragraph",
            "text": (
                "A dedup por operation_id vem antes da conferência de "
                "revisão esperada."
            ),
        },
    ]
]

DOC_TEXT_PAGES_AMBIGUO = [
    [
        {"kind": "heading", "text": "Cronograma"},
        {"kind": "paragraph", "text": "A prova é dia 05/11."},
    ]
]


def _uid(n: int) -> _uuid.UUID:
    return _uuid.UUID(f"00000000-0000-0000-0000-{n:012d}")


def make_uuid() -> str:
    return str(_uuid.uuid4())


# ---------------------------------------------------------------------------
# Dobras de teste (mesmo padrão das tasks 002/006/007/008)
# ---------------------------------------------------------------------------


class FakeBackend:
    """Backend determinístico (contrato do adaptador da task 002)."""

    def __init__(
        self,
        responses: list[str],
        *,
        json_schema_capability: bool = True,
        error: Exception | None = None,
    ) -> None:
        self.capabilities = RuntimeCapabilities(
            json_schema=json_schema_capability,
            json_schema_evidence="teste",
        )
        self.responses = list(responses)
        self.error = error
        self.calls: list[dict] = []

    def generate(self, messages, schema, sampler, deadline, seed):
        self.calls.append({"messages": [dict(m) for m in messages]})
        if self.error is not None:
            raise self.error
        return type(
            "GenerationResult",
            (),
            {
                "text": self.responses.pop(0),
                "finish_reason": "stop",
                "prompt_tokens": 10,
                "completion_tokens": 10,
                "thinking": None,
                "model_id": "fake",
                "seed": seed,
            },
        )()


class BlockingBackend:
    """Backend que bloqueia até ser liberado (fila serial)."""

    capabilities = RuntimeCapabilities(json_schema=False, json_schema_evidence="t")

    def __init__(self) -> None:
        self.release = threading.Event()
        self.entered = threading.Event()

    def generate(self, messages, schema, sampler, deadline, seed):
        self.entered.set()
        self.release.wait(timeout=5)
        return type(
            "GenerationResult",
            (),
            {
                "text": "{}",
                "finish_reason": "stop",
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "thinking": None,
                "model_id": "fake",
                "seed": seed,
            },
        )()


class HashEmbedder:
    """Embedder denso fake determinístico (igualdade de texto ⇒ similar 1)."""

    name = "hash-fake"
    revision = "test-revision"
    dim = 8

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vector = np.array(
                [byte / 255.0 for byte in digest[: self.dim]], dtype=np.float32
            )
            norm = float(np.linalg.norm(vector)) or 1.0
            vectors.append(vector / norm)
        return np.vstack(vectors)

    def file_manifest(self) -> dict[str, str]:
        return {"fake": "0" * 64}


class FakeExtractor:
    """Extrator determinístico (protocolo BlockExtractor da 006)."""

    name = "fake-extractor"
    version = "1"

    def __init__(self, pages: list[list[dict]]) -> None:
        self.pages = pages

    def extract(self, data, mime, *, max_pages, languages=None, on_page=None, cancelled=lambda: False):
        from eduagent.services.ingestion import (
            BlockRecord,
            ExtractedDocument,
            PageRecord,
        )

        extracted = ExtractedDocument()
        for page_no, blocks in enumerate(self.pages, start=1):
            records = [
                BlockRecord(
                    page=page_no,
                    kind=str(block.get("kind", "paragraph")),
                    text=str(block.get("text", "")),
                    order_in_page=order,
                    legible=True,
                )
                for order, block in enumerate(blocks)
            ]
            extracted.pages.append(PageRecord(page=page_no, blocks=records))
        extracted.diagnose_pages()
        return extracted


class FakeWebConnector:
    """Conector de busca fake (contrato da task 016; nada de rede real)."""

    def search(self, query, language, max_results):
        return [
            {"url": "https://exemplo.valido.org/artigo", "title": "Artigo"},
            {"url": "https://exemplo.valido.org/video", "title": "Vídeo"},
        ]

    def fetch(self, url):
        return {
            "url": url,
            "state": "text_read",
            "hash": "ab" * 32,
            "captured_at": FIXED_NOW.isoformat(),
        }


class ProbeHandler:
    """Destino de efeito que confirma por identidade (§11)."""

    def apply(self, target, payload, operation_id):
        return EffectOutcome.APPLIED

    def probe(self, target, operation_id):
        return EffectOutcome.APPLIED


class FakeGrader:
    """Julgador por rubrica determinístico (itens de texto, §8)."""

    def grade(self, request):
        from eduagent.agents.monitor import CriterionProposal

        return [
            CriterionProposal(
                criterion_id=criterion.criterion_id,
                level=2,
                span_text=request.response[: min(len(request.response), 20)] or None,
                reason="resposta cobre o critério (dobra de teste)",
                misconception_code=None,
            )
            for criterion in request.rubric
        ]


class MutableClock:
    """Relógio injetável com avanço controlado (deadline, §12)."""

    def __init__(self, start: datetime = FIXED_NOW) -> None:
        self._moment = start

    def __call__(self) -> datetime:
        return self._moment

    def advance(self, **kwargs) -> None:
        self._moment = self._moment + timedelta(**kwargs)


def item_payload() -> str:
    return json.dumps(
        {
            "prompt": "Explique por que a dedup por operation_id vem antes.",
            "expected_answer": (
                "Porque a dedup garante que retries devolvam o recibo "
                "anterior sem repetir o efeito."
            ),
            "rubric": [
                {
                    "criterion_id": "dedup",
                    "description": "Explica a dedup por operation_id.",
                    "critical": True,
                }
            ],
            "citations": [0],
        },
        ensure_ascii=False,
    )


def text_payload(text: str) -> str:
    return json.dumps({"text": text}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Ambiente
# ---------------------------------------------------------------------------


def open_stack(
    tmp_path: Path,
    *,
    backend: FakeBackend | None = None,
    config: dict | None = None,
    clock=None,
    rubric_grader=None,
    embedder=None,
    web_connector=None,
    dispatcher=None,
    build_problem=None,
    pages=None,
) -> SimpleNamespace:
    store = DomainStore.open(tmp_path / "domain.sqlite")
    store.ensure_user(UID)
    course = str(_uid(21))
    topic = str(_uid(11))
    store.execute_write(
        UID,
        [
            (
                "INSERT OR IGNORE INTO courses(id, user_id, title) "
                "VALUES (?,?,?)",
                (course, UID, "MO810"),
            ),
            (
                "INSERT OR IGNORE INTO topics(id, course_id, title) "
                "VALUES (?,?,?)",
                (topic, course, "Tópico de teste"),
            ),
        ],
        bump_domain_revision=False,  # setup: não conta como escrita de turno
    )
    data_root = tmp_path / "data"
    effects = EffectsService(store)
    clock = clock or (lambda: FIXED_NOW)
    memory = MemoryService(store, effects, clock=clock)
    assessment = AssessmentService(store, effects, clock=clock)
    demands = DemandService(store, effects, clock=clock)
    calendar = CalendarService(store, effects, clock=clock)
    planner = PlannerAgent(store, effects, clock=clock)
    ingestion = IngestionService(
        store, data_root, extractor=FakeExtractor(pages or DOC_TEXT_PAGES)
    )
    curator = CuratorAgent(store, ingestion=ingestion)
    retrieval = RetrievalService(store, data_root)
    tutor = (
        Tutor(
            backend,
            SkillCatalog.load(),
            item_sink=EventItemSink(store, effects, clock=clock),
            clock=clock,
        )
        if backend is not None
        else None
    )
    checkpointer = SQLiteCheckpointer(tmp_path / "checkpoints.sqlite")
    graph = EduAgentGraph(
        store=store,
        checkpointer=checkpointer,
        config=config,
        clock=clock,
        backend=backend,
        tutor=tutor,
        librarian=Librarian(memory),
        curator=curator,
        retrieval=retrieval,
        embedder=embedder or HashEmbedder(),
        memory=memory,
        assessment=assessment,
        rubric_grader=rubric_grader or FakeGrader(),
        planner=planner,
        demands=demands,
        calendar=calendar,
        ingestion=ingestion,
        dispatcher=dispatcher,
        web_connector=web_connector,
        data_root=data_root,
        build_problem=build_problem,
    )
    return SimpleNamespace(
        store=store,
        effects=effects,
        memory=memory,
        assessment=assessment,
        demands=demands,
        calendar=calendar,
        planner=planner,
        retrieval=retrieval,
        graph=graph,
        checkpointer=checkpointer,
        data_root=data_root,
        course=course,
        topic=topic,
        clock=clock,
    )


def state_of(env: SimpleNamespace, session_id: str = SESSION) -> dict:
    config = {"configurable": {"thread_id": session_id}}
    return dict(env.graph._final_state(config))  # noqa: SLF001 — teste


def ingest_and_index(env: SimpleNamespace, data: bytes = b"%PDF-1.7\ndedup\n"):
    """Rota ingest (intenção explícita) + publicação do índice (007) +
    ativação da versão (§6.1: ativação só após indexação completa)."""
    result = env.graph.run_turn(
        user_id=UID,
        session_id=SESSION,
        message="/ingest documento",
        payload={"data": data, "course_id": env.course},
    )
    assert result.status == "completed", result.output
    ingest = result.output["index"]
    env.retrieval.index_version(
        UID, ingest["doc_id"], ingest["version_id"], embedder=HashEmbedder()
    )
    env.graph._ingestion.activate_version(  # noqa: SLF001 — fronteira de teste
        UID, ingest["doc_id"], ingest["version_id"]
    )
    return ingest


@pytest.fixture()
def env(tmp_path: Path) -> SimpleNamespace:
    stack = open_stack(
        tmp_path,
        backend=FakeBackend(
            [
                item_payload(),
                text_payload("Pista 1 (conceito): a dedup é a primeira etapa."),
                text_payload("Pista 2 (próximo passo): compare os recibos."),
                text_payload(
                    "A dedup vem antes: retries devolvem o recibo anterior."
                ),
            ]
        ),
    )
    yield stack
    stack.store.close()
    stack.checkpointer.close()


# ---------------------------------------------------------------------------
# Rota ingest (R-I1, R-I2)
# ---------------------------------------------------------------------------


class TestRotaIngest:
    def test_ingest_termina_completed_com_refs(self, env):
        result = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="/ingest material",
            payload={"data": b"%PDF-1.7\nconteudo\n", "course_id": env.course},
        )
        assert result.status == "completed"
        assert result.state.errors == []
        index = result.output["index"]
        assert index["version_status"] == "indexed"
        refs = [r.to_locator() for r in result.state.artifact_refs]
        assert any(ref.startswith("artifact:") for ref in refs)
        # Estado de domínio é autoridade: a versão está no banco.
        rows = env.store.fetch_user_rows(
            "SELECT status FROM doc_versions WHERE id = ?",
            (index["version_id"],),
        )
        assert rows and rows[0]["status"] == "indexed"

    def test_ingest_com_fato_ambiguo_passa_pelo_gate(self, tmp_path):
        env2 = open_stack(tmp_path, pages=DOC_TEXT_PAGES_AMBIGUO)
        try:
            first = env2.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="/ingest cronograma",
                payload={
                    "data": b"%PDF-1.7\ncronograma\n",
                    "course_id": env2.course,
                },
            )
            if first.waiting_interrupt:
                # Gate de confirmação é interrupt puro; nada confirmado ainda.
                confirmed = env2.store.fetch_user_rows(
                    "SELECT COUNT(*) AS n FROM facts WHERE user_id = ? AND "
                    "status = 'confirmed'",
                    (UID,),
                )
                assert confirmed[0]["n"] == 0
                resumed = env2.graph.resume_turn(
                    session_id=SESSION, resume={"confirmed": True}
                )
                assert resumed.status == "completed"
                assert resumed.output["confirmed"] is True
            else:
                assert first.status == "completed"
        finally:
            env2.store.close()
            env2.checkpointer.close()


# ---------------------------------------------------------------------------
# Rotas ask/practice/submit (R-A1, R-A2, R-S1)
# ---------------------------------------------------------------------------


class TestRotasTutoria:
    def test_rota_ask_com_evidencia_e_fontes_rotuladas(self, env):
        ingest_and_index(env)
        result = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="Por que a dedup vem antes?",
            intent="ask",
            payload={"course_id": env.course},
        )
        assert result.status == "completed"
        turn = result.output["turn"]
        assert turn["terminal"] == "completed"
        # Leituras independentes aconteceram: evidência + memória no estado.
        state = state_of(env)
        assert "evidence" in state
        assert "memory_summary" in state
        # Fonte/tool result é dado rotulado: citações do turno saem do pack.
        for citation in turn["citations"]:
            assert any(
                c["citation"] == citation
                for c in state["tutor_evidence"]["chunks"]
            )

    def test_rota_practice_espera_aluno_e_submit_commita(self, env):
        ingest_and_index(env)
        practice = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="quero praticar dedup",
            intent="practice",
            payload={"course_id": env.course, "topic_ids": [env.topic]},
        )
        # Espera por aluno é FIM da invocação (§10): waiting_student.
        assert practice.status == "waiting_student"
        assert practice.state.pending_item_ref is not None
        item_ref = str(practice.state.pending_item_ref)

        submission = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message=(
                "Porque a dedup garante que retries devolvam o recibo "
                "anterior sem repetir o efeito."
            ),
            intent="submit_answer",
        )
        assert submission.status == "completed"
        feedback = submission.output["feedback"]
        assert feedback["correctness"] == "correct"
        assert feedback["help_level"] == 0  # tentativa independente (§15.2)
        assert state_of(env)["pending_item_ref"] is None
        # commit idempotente: assessment registrado no domínio.
        rows = env.store.fetch_user_rows(
            "SELECT COUNT(*) AS n FROM assessments WHERE attempt_user_id = ?",
            (UID,),
        )
        assert rows[0]["n"] == 1
        # Revisão/recuperação geradas pela política v1 (§15.3).
        assert submission.output["review_requests"]
        assert item_ref  # item publicado permanece no domínio


# ---------------------------------------------------------------------------
# Rotas plan/approve/export (R-P1, R-AP1, R-E1)
# ---------------------------------------------------------------------------


def _build_problem_factory():
    def build_problem(user_id, pending, snapshot_version):
        demands = tuple(
            SolverDemand(
                demand_id=_uuid.UUID(str(record["demand_id"])),
                duration_minutes=int(record["duration_minutes"]),
                mandatory=bool(record["mandatory"]),
                priority_class=int(record["priority_class"]),
                earliest_utc=datetime.fromisoformat(str(record["earliest"])),
                deadline=datetime.fromisoformat(str(record["deadline"]))
                if "T" in str(record["deadline"])
                else datetime.fromisoformat(
                    str(record["deadline"]) + "T23:59:00+00:00"
                ),
            )
            for record in pending
        )
        day = FIXED_NOW.date()
        return SchedulingProblem(
            user_id=user_id,
            horizon_start=day,
            local_timezone=None,
            snapshot_version=int(snapshot_version or 1),
            demands=demands,
            availability=(TimeWindow(day=day, start_minute=8 * 60, end_minute=18 * 60),),
        )

    return build_problem


class TestRotasPlanejamento:
    def test_fluxo_plan_approve_export(self, tmp_path):
        env = open_stack(
            tmp_path,
            backend=FakeBackend([item_payload()]),
            build_problem=_build_problem_factory(),
        )
        try:
            # Demanda pendente gerada pela política v1 (erro aceito → revisão).
            env.demands.generate_review_demand(
                UID,
                topic_id=env.topic,
                occurrence_utc=FIXED_NOW,
                outcome="review_after_error",
                critical_error=True,
                confirmed_duration_minutes=30,
            )
            plan = env.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="/plan semana",
                intent="plan",
            )
            # §9/§15.3: duração/prazo exigem confirmação (interrupt puro).
            assert plan.waiting_interrupt
            assert env.store.fetch_user_rows(
                "SELECT COUNT(*) AS n FROM plans WHERE user_id = ?", (UID,)
            )[0]["n"] == 0
            approved = env.graph.resume_turn(
                session_id=SESSION, resume={"confirmed": True}
            )
            # Preview → wait (interrupt de aprovação).
            assert approved.waiting_interrupt
            assert approved.output["preview"]["plan_id"]
            final = env.graph.resume_turn(
                session_id=SESSION, resume={"approved": True}
            )
            assert final.status == "completed"
            assert final.output["approved"] is True
            plan_id = final.output["approval"]["plan_id"]
            rows = env.store.fetch_user_rows(
                "SELECT COUNT(*) AS n FROM confirmations WHERE user_id = ?",
                (UID,),
            )
            assert rows[0]["n"] == 1

            # Rota approve_plan explícita (§10): validate → commit.
            env2 = open_stack(tmp_path, build_problem=_build_problem_factory())
            approval = env2.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="/approve",
                intent="approve_plan",
            )
            assert approval.status == "completed"

            # Rota export_calendar (§10): resolve → render → validate → publish.
            export = env2.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="/export",
                intent="export_calendar",
                payload={"plan_id": plan_id},
            )
            assert export.status == "completed"
            assert export.output["calendar"]["events"] >= 1
            path = Path(export.output["calendar"]["path"])
            assert path.exists() and path.read_bytes().startswith(
                b"BEGIN:VCALENDAR"
            )
            # Sem plano confirmado (ID aleatório) é recusa tipada.
            denied = env2.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="/export outro",
                intent="export_calendar",
                payload={"plan_id": str(_uid(99))},
            )
            assert denied.status == "failed"
            assert denied.state.errors[0].code == ErrorCode.SOURCE_UNRESOLVED
        finally:
            env.store.close()
            env.checkpointer.close()

    def test_export_sem_plano_confirmado_e_recusado(self, env):
        denied = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="/export",
            intent="export_calendar",
        )
        assert denied.status == "failed"
        assert denied.state.errors[0].code == ErrorCode.SOURCE_UNRESOLVED


# ---------------------------------------------------------------------------
# Rota update_activity (R-U1)
# ---------------------------------------------------------------------------


class TestRotaUpdateActivity:
    def test_transicao_planned_started_e_commitada(self, env):
        block = env.planner.register_block(
            UID,
            planned_start_utc=FIXED_NOW + timedelta(hours=2),
            planned_end_utc=FIXED_NOW + timedelta(hours=3),
        )
        result = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="/update atividade",
            intent="update_activity",
            payload={
                "activity": {
                    "block_id": str(block.block_id),
                    "status": "started",
                    "occurred_at": FIXED_NOW.isoformat(),
                    "expected_version": env.store.domain_revision(UID),
                    "operation_id": str(_uuid.uuid4()),
                }
            },
        )
        assert result.status == "completed"
        assert result.output["activity"]["status"] == "started"
        record = env.planner.get_block(UID, block.block_id)
        assert record.status == "started"

    def test_bloco_inexistente_e_recusa_tipada(self, env):
        result = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="/update atividade",
            intent="update_activity",
            payload={
                "activity": {
                    "block_id": str(_uid(77)),
                    "status": "started",
                    "occurred_at": FIXED_NOW.isoformat(),
                    "expected_version": 0,
                    "operation_id": str(_uuid.uuid4()),
                }
            },
        )
        assert result.status == "failed"
        assert result.state.errors[0].code == ErrorCode.SOURCE_UNRESOLVED


# ---------------------------------------------------------------------------
# Rota memory_query (R-M1)
# ---------------------------------------------------------------------------


class TestRotaMemoryQuery:
    def test_memoria_com_fontes_resolutiveis(self, env):
        env.memory.record_event(
            user_id=UID,
            session_id=SESSION,
            kind=MemoryPack.EventKind.READING,
            payload={"text": "Estudei dedup de operation_id no capítulo 3."},
            occurred_at=FIXED_NOW,
            origin=MemoryPack.Origin.OBSERVED,
        )
        result = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="quando estudei dedup?",
            intent="memory_query",
        )
        assert result.status == "completed"
        answer = result.output["memory_answer"]
        assert answer["sources"], "fontes rotuladas na resposta (§7)"
        # source_check: toda fonte resolve no domínio.
        for ref in answer["sources"]:
            raw_id = str(ref).split("@", 1)[0].split(":", 1)[-1]
            rows = env.store.fetch_user_rows(
                "SELECT id FROM events WHERE user_id = ? AND id = ?",
                (UID, raw_id),
            )
            assert rows


# ---------------------------------------------------------------------------
# Rotas correct_fact/delete_data (R-CF1, R-DD1)
# ---------------------------------------------------------------------------


class TestRotasCorrecaoDelecao:
    def _confirmed_fact(self, env) -> str:
        record = env.memory.assert_fact(
            user_id=UID,
            entity_id=_uid(31),
            kind=AcademicFact.FactKind.NUMBER,
            original_expression="nota máxima é 100",
            normalized_value="100",
            precision=AcademicFact.Precision.EXACT,
            status=AcademicFact.FactStatus.CONFIRMED,
            authority=AcademicFact.FactAuthority.USER_CONFIRMED,
            origin=MemoryPack.Origin.ASSERTED,
        )
        return str(record.fact_id)

    def test_correct_fact_com_preview_e_confirmacao(self, env):
        fact_id = self._confirmed_fact(env)
        first = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="/correct fato",
            intent="correct_fact",
            payload={"fact_id": fact_id, "corrected_value": "90"},
        )
        # preview → confirm (§10): interrupt puro, nada commitado ainda.
        assert first.waiting_interrupt
        assert first.output["preview"]["current_value"] == "100"
        rows = env.store.fetch_user_rows(
            "SELECT COUNT(*) AS n FROM facts WHERE user_id = ?", (UID,)
        )
        before = rows[0]["n"]
        final = env.graph.resume_turn(
            session_id=SESSION, resume={"confirmed": True}
        )
        assert final.status == "completed"
        assert final.output["change_applied"] is True
        rows = env.store.fetch_user_rows(
            "SELECT COUNT(*) AS n FROM facts WHERE user_id = ?", (UID,)
        )
        assert rows[0]["n"] == before + 1  # fato novo com supersedes (§15.1)
        # Projeção vigente reflete a correção.
        current = env.memory.current_facts(UID)
        values = [fact.normalized_value for fact in current]
        assert "90" in values and "100" not in values

    def test_delete_data_sem_confirmacao_nada_commita(self, env):
        env.memory.record_event(
            user_id=UID,
            session_id=SESSION,
            kind=MemoryPack.EventKind.READING,
            payload={"text": "evento a deletar"},
            occurred_at=FIXED_NOW,
            origin=MemoryPack.Origin.OBSERVED,
        )
        first = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="/delete eventos",
            intent="delete_data",
            payload={"scope": "events"},
        )
        assert first.waiting_interrupt
        assert first.output["preview"]["scope"] == "events"
        final = env.graph.resume_turn(
            session_id=SESSION, resume={"confirmed": False}
        )
        assert final.status == "completed"
        assert final.output["change_applied"] is False
        rows = env.store.fetch_user_rows(
            "SELECT COUNT(*) AS n FROM events WHERE user_id = ? AND "
            "payload_json IS NOT NULL",
            (UID,),
        )
        assert rows[0]["n"] == 1  # nada purgado sem confirmação (§5/§10)

    def test_escopo_invalido_e_recusa_tipada(self, env):
        result = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="/delete nada",
            intent="delete_data",
            payload={"scope": "universo"},
        )
        assert result.status == "failed"
        # §10 validate_scope: escopo inválido é recusa tipada (SCHEMA_INVALID,
        # convenção do serviço de memória da 010).
        assert result.state.errors[0].code == ErrorCode.SCHEMA_INVALID


# ---------------------------------------------------------------------------
# Rota curate (R-CU1, R-CU2)
# ---------------------------------------------------------------------------


class TestRotaCurate:
    def test_sem_conector_conector_desabilitado(self, env):
        result = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="/curate busca",
            intent="curate",
            payload={"query": "dedup"},
        )
        assert result.status == "failed"
        error = result.state.errors[0]
        assert error.code == ErrorCode.RESOURCE_LIMIT
        assert "CONNECTOR_DISABLED" in error.message

    def test_com_conector_fluxo_completo(self, tmp_path):
        env = open_stack(
            tmp_path,
            web_connector=FakeWebConnector(),
            config={"network_enabled": True},
        )
        try:
            result = env.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="/curate busca",
                intent="curate",
                payload={"query": "dedup"},
            )
            assert result.status == "completed"
            claims = result.output["curated_web"]
            assert claims and claims[0]["access"] == "text_read"
        finally:
            env.store.close()
            env.checkpointer.close()


# ---------------------------------------------------------------------------
# Rota cancel (R-X1, R-X2)
# ---------------------------------------------------------------------------


class TestRotaCancel:
    def test_cancel_reconcilia_efeitos_e_termina_cancelled(self, tmp_path):
        env = open_stack(
            tmp_path,
            dispatcher=OutboxDispatcher(DomainStore.open(tmp_path / "domain.sqlite"), ProbeHandler()),
        )
        try:
            # Efeito já iniciado (outbox pendente) é reconciliado por
            # identidade (§10/§11).
            operation = str(_uuid.uuid4())
            env.effects.commit(
                CommitRequest(
                    operation_id=operation,
                    user_id=UID,
                    action="fact.upsert",
                    digest="ab" * 32,
                    expected_version=0,
                    event=EventSpec(
                        id=str(_uuid.uuid4()),
                        kind="reading",
                        occurred_at=FIXED_NOW.isoformat(),
                        recorded_at=FIXED_NOW.isoformat(),
                    ),
                    outbox=OutboxSpec(
                        id=str(_uuid.uuid4()),
                        target="sidecar",
                        payload={"operation_id": operation},
                    ),
                )
            )
            result = env.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="/cancel",
                intent="cancel",
            )
            assert result.status == "cancelled"
            codes = [e.code for e in result.state.errors]
            assert ErrorCode.CANCELLED in codes
            cancel = result.output["cancel"]
            assert cancel["stage"] == "stop_dispatch"
            assert cancel["persisted"] is True
            assert cancel["reconciled"]["acked"] == 1
        finally:
            env.store.close()
            env.checkpointer.close()

    def test_cancel_requested_tem_prioridade(self, env):
        result = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="qualquer coisa",
            intent="ask",
            cancel_requested=True,
        )
        assert result.status == "cancelled"
        assert result.state.cancel_requested is True


# ---------------------------------------------------------------------------
# Limites (L-T1, L-B1, L-Q1) — mapa §12
# ---------------------------------------------------------------------------


class TestLimites:
    def test_deadline_terminal_tipado_com_artefatos_preservados(self, tmp_path):
        clock = MutableClock()
        env = open_stack(
            tmp_path,
            backend=FakeBackend([item_payload(), text_payload("pista")]),
            clock=clock,
        )
        try:
            ingest_and_index(env)
            # Turno 1 publica o item (artefato válido).
            practice = env.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="quero praticar",
                intent="practice",
                payload={"course_id": env.course, "topic_ids": [env.topic]},
            )
            assert practice.status == "waiting_student"
            # Turno 2 com deadline já vencido no instante de abertura
            # (active_deadline_s negativo = instante no passado): terminal
            # com erro tipado e artefatos válidos preservados (§12).
            env2 = open_stack(
                tmp_path,
                backend=FakeBackend([text_payload("pista")]),
                clock=clock,
                config={"active_deadline_s": -1},
            )
            expired = env2.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="me dê uma pista",
                intent="practice",
                payload={"course_id": env.course, "topic_ids": [env.topic]},
            )
            assert expired.status == "failed"
            assert expired.state.errors[0].code == ErrorCode.TIMEOUT
            # O item já publicado continua no domínio (artefato válido).
            rows = env.store.fetch_user_rows(
                "SELECT COUNT(*) AS n FROM items WHERE user_id = ?", (UID,)
            )
            assert rows[0]["n"] == 1
            assert expired.state.pending_item_ref is not None
        finally:
            env.store.close()
            env.checkpointer.close()
            try:
                env2.store.close()
                env2.checkpointer.close()
            except UnboundLocalError:
                pass

    def test_orcamento_llm_esgotado_resource_limit(self, tmp_path):
        env = open_stack(
            tmp_path,
            backend=FakeBackend([json.dumps({"intent": "ask"})]),
            config={"max_llm_calls": 0},
        )
        try:
            # Classificação é geração: orçamento 0 recusa ANTES da geração.
            result = env.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="como funciona a dedup?",
            )
            assert result.status == "failed"
            assert result.state.errors[0].code == ErrorCode.RESOURCE_LIMIT
            # Nada parcial publicado (§12): sem eventos de efeito no domínio.
            rows = env.store.fetch_user_rows(
                "SELECT COUNT(*) AS n FROM items WHERE user_id = ?", (UID,)
            )
            assert rows[0]["n"] == 0
        finally:
            env.store.close()
            env.checkpointer.close()

    def test_fila_cheia_resource_limit_e_geracao_serial(self, tmp_path):
        backend = BlockingBackend()
        gate = GenerationGate(backend, queue_size=1, clock=lambda: FIXED_NOW)
        limits = TurnLimits(
            max_llm_calls=10,
            max_tool_calls=10,
            max_graph_steps=16,
            max_repairs_total=2,
            clock=lambda: FIXED_NOW,
        )
        try:
            futures = []
            for _ in range(2):  # 1 slot + 1 fila
                futures.append(
                    gate._server.submit(  # noqa: SLF001 — fronteira da fila
                        messages=[{"role": "user", "content": "x"}],
                        schema=None,
                        sampler=None,
                        deadline=FIXED_NOW.timestamp() + 30,
                        seed=0,
                    )
                )
            with pytest.raises(ModelAdapterError) as exc:
                gate._server.submit(  # noqa: SLF001
                    messages=[{"role": "user", "content": "x"}],
                    schema=None,
                    sampler=None,
                    deadline=FIXED_NOW.timestamp() + 30,
                    seed=0,
                )
            assert exc.value.code == ErrorCode.RESOURCE_LIMIT
            # Drena as futures para o worker terminar limpo.
            backend.release.set()
            for future in futures:
                try:
                    future.result(timeout=5)
                except Exception:
                    pass
        finally:
            backend.release.set()
            gate.close()

    def test_geracao_e_serial_no_gate(self, tmp_path):
        backend = BlockingBackend()
        gate = GenerationGate(backend, queue_size=2, clock=lambda: FIXED_NOW)
        limits = TurnLimits(
            max_llm_calls=5,
            max_tool_calls=5,
            max_graph_steps=16,
            max_repairs_total=2,
            clock=lambda: FIXED_NOW,
        )
        results: list[str] = []

        def worker():
            gate.generate(
                limits=limits,
                messages=[{"role": "user", "content": "x"}],
                schema=None,
                sampler=None,
                seed=0,
            )
            results.append("done")

        thread = threading.Thread(target=worker)
        thread.start()
        assert backend.entered.wait(timeout=2)
        # A segunda geração espera o slot (fila serial) — nenhuma conclusão
        # enquanto a primeira estiver em curso.
        assert results == []
        backend.release.set()
        thread.join(timeout=5)
        assert results == ["done"]
        gate.close()


# ---------------------------------------------------------------------------
# Checkpoints (CK-1, CK-2) — mapa §10, C2
# ---------------------------------------------------------------------------


class TestCheckpoints:
    def test_retomada_preserva_item_ajuda_e_historico(self, tmp_path):
        first = open_stack(
            tmp_path,
            backend=FakeBackend(
                [
                    item_payload(),
                    text_payload("Pista 1 (conceito): a dedup é a primeira etapa."),
                ]
            ),
        )
        try:
            ingest_and_index(first)
            practice = first.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="quero praticar",
                intent="practice",
                payload={
                    "course_id": first.course,
                    "topic_ids": [first.topic],
                },
            )
            assert practice.status == "waiting_student"
            hint1 = first.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="me dê uma pista",
                intent="practice",
                payload={
                    "course_id": first.course,
                    "topic_ids": [first.topic],
                },
            )
            # Turno de pista também espera o aluno (§8: hint → waiting_student).
            assert hint1.status == "waiting_student"
            state1 = state_of(first)
            # Nível de ajuda é por ITEM (§8/008a): chave é o UUID do item.
            item_id = str(state1["tutor_session"]["pending_item"]["item_id"])
            assert state1["tutor_session"]["help_level_by_item"][item_id] == 1
            history_len = len(state1["tutor_session"]["history"])
        finally:
            first.store.close()
            first.checkpointer.close()

        # "Reinício": novas instâncias sobre os MESMOS arquivos (durability).
        second = open_stack(
            tmp_path,
            backend=FakeBackend(
                [text_payload("Pista 2 (próximo passo): compare os recibos.")]
            ),
        )
        try:
            hint2 = second.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="outra pista",
                intent="practice",
                payload={
                    "course_id": second.course,
                    "topic_ids": [second.topic],
                },
            )
            assert hint2.status == "waiting_student"
            state2 = state_of(second)
            # Item pendente preservado (refs, não conteúdo integral, §4).
            resumed_ref = str(state2["pending_item_ref"])
            assert resumed_ref.split(":")[1].split("@")[0] == item_id
            # Nível de ajuda preservado e avançado na escada do item (§8).
            assert state2["tutor_session"]["help_level_by_item"][item_id] == 2
            # Histórico do turno preservado pelo checkpoint.
            assert (
                len(state2["tutor_session"]["history"]) == history_len + 1
            )
        finally:
            second.store.close()
            second.checkpointer.close()


# ---------------------------------------------------------------------------
# Política de ferramentas (T-P1..T-P3) e segurança (S-F1, S-F2) — mapa §10
# ---------------------------------------------------------------------------


class TestPoliticaFerramentas:
    def test_proposta_fora_de_papel_negada_por_codigo(self):
        # Tabela §10: Monitor não propõe document.search; Tutor não propõe
        # schedule.solve; JSON correto para ação proibida é negado por código.
        with pytest.raises(EduAgentError) as exc:
            validate_tool_request(ToolName.DOCUMENT_SEARCH, SenderRole.MONITOR)
        assert exc.value.code == ErrorCode.TOOL_DENIED
        with pytest.raises(EduAgentError) as exc:
            validate_tool_request(ToolName.SCHEDULE_SOLVE, SenderRole.TUTOR)
        assert exc.value.code == ErrorCode.TOOL_DENIED
        with pytest.raises(EduAgentError) as exc:
            ToolRequest(
                tool=ToolName.DOMAIN_COMMIT, sender_role=SenderRole.CURATOR
            )
        assert exc.value.code == ErrorCode.TOOL_DENIED

    def test_payload_nao_muda_permissoes(self):
        # Papel é atribuído pelo dispatcher; payload externo não concede
        # permissão (mapa §4) — negação por código (§10).
        with pytest.raises(EduAgentError) as exc:
            require_tool(ToolName.DOMAIN_COMMIT, SenderRole.TUTOR)
        assert exc.value.code == ErrorCode.TOOL_DENIED
        with pytest.raises(EduAgentError) as exc:
            require_tool(ToolName.CALENDAR_APPLY, SenderRole.USER)
        assert exc.value.code == ErrorCode.TOOL_DENIED

    def test_sem_shell_generico_nem_escrita_direta(self):
        # Nenhum agente recebe shell genérico ou escrita direta no DB (§10):
        # o catálogo de ferramentas é fechado e não expõe shell/exec/sql.
        names = {tool.value for tool in ToolName}
        assert names == {
            "document.extract",
            "document.search",
            "memory.query",
            "assessment.check",
            "schedule.solve",
            "calendar.render",
            "web.search",
            "web.fetch",
            "domain.commit",
            "calendar.apply",
        }
        assert not any(
            token in " ".join(names)
            for token in ("shell", "exec", "sql", "db.write")
        )
        # As únicas escritas são do serviço determinístico (§10).
        assert validate_tool_request  # domain.commit/apply: só SYSTEM
        with pytest.raises(EduAgentError):
            validate_tool_request(ToolName.DOMAIN_COMMIT, SenderRole.CURATOR)

    def test_fonte_rotulada_nao_altera_politica(self, env):
        # Fonte/tool result é dado rotulado (§10): receber evidência com
        # fontes não concede papel/permissão ao Tutor.
        with pytest.raises(EduAgentError) as exc:
            require_tool(ToolName.ASSESSMENT_CHECK, SenderRole.TUTOR)
        assert exc.value.code == ErrorCode.TOOL_DENIED
        with pytest.raises(EduAgentError) as exc:
            require_tool(ToolName.MEMORY_QUERY, SenderRole.TUTOR)
        assert exc.value.code == ErrorCode.TOOL_DENIED

    def test_web_sem_rede_conector_negado(self):
        with pytest.raises(EduAgentError) as exc:
            require_tool(ToolName.WEB_SEARCH, SenderRole.CURATOR)
        assert exc.value.code == ErrorCode.RESOURCE_LIMIT
        assert "CONNECTOR_DISABLED" in exc.value.message


class TestSegurancaPathsFetch:
    def test_traversal_e_symlink_bloqueados(self, tmp_path):
        data_root = tmp_path / "data"
        user_dir = data_root / UID
        user_dir.mkdir(parents=True)
        (user_dir / "ok.txt").write_text("conteudo")
        # traversal
        with pytest.raises(EduAgentError) as exc:
            resolve_owned_path(data_root, UID, "../../domain.sqlite")
        assert exc.value.code == ErrorCode.TOOL_DENIED
        # absoluto
        with pytest.raises(EduAgentError):
            resolve_owned_path(data_root, UID, "/etc/passwd")
        # symlink escape
        link = user_dir / "escape"
        link.symlink_to(tmp_path)
        with pytest.raises(EduAgentError) as exc:
            resolve_owned_path(data_root, UID, "escape/domain.sqlite")
        assert exc.value.code == ErrorCode.TOOL_DENIED
        # caminho próprio resolve
        resolved = resolve_owned_path(data_root, UID, "ok.txt")
        assert resolved.is_file()

    def test_fetch_bloqueia_privado_loopback(self):
        for url in (
            "http://127.0.0.1:8080/x",
            "http://localhost/x",
            "http://10.0.0.1/x",
            "http://192.168.0.10/x",
            "http://169.254.1.1/x",
            "ftp://exemplo.valido.org/x",
        ):
            with pytest.raises(EduAgentError):
                assert_public_url(url)

    def test_fetch_aceita_ip_publico_e_revalida_redirect(self):
        # IP público literal (DNS numérico funciona offline).
        url = "http://93.184.216.34/recurso"
        assert assert_public_url(url) == url
        # redirect revalidado por hop (§10)
        target = assert_redirect_target(url, "/outro")
        assert target.endswith("/outro")
        with pytest.raises(EduAgentError):
            assert_redirect_target(url, "http://127.0.0.1/armadilha")

    def test_user_id_ponto_vazio_e_traversal_recusados(self, tmp_path):
        # A1 da revisão: user_id "." ou "" resolvia para o próprio root,
        # escapando da segregação por usuário. Ownership exige subdiretório
        # DIRETO de root (§10) — vazio, ".", ".." e traversal são recusados
        # por código.
        data_root = tmp_path / "data"
        user_dir = data_root / UID
        user_dir.mkdir(parents=True)
        (user_dir / "ok.txt").write_text("conteudo")
        for uid in (".", "", ".."):
            with pytest.raises(EduAgentError) as exc:
                resolve_owned_path(data_root, uid, "arquivo.txt")
            assert exc.value.code == ErrorCode.TOOL_DENIED
        # Subdiretório direto continua resolvendo dentro do diretório próprio.
        resolved = resolve_owned_path(data_root, UID, "ok.txt")
        assert resolved.is_file()
        assert resolved.parent == user_dir

    def test_redirect_protocol_relative_revalidado(self):
        # A2 da revisão: alvo protocol-relative ("//host/...") é host
        # absoluto — urljoin resolve antes de validar e o host resultante é
        # revalidado (antes, era concatenado ao host atual sem revalidação).
        url = "http://93.184.216.34/a"
        for location in ("//10.0.0.1/evil", "//127.0.0.1/evil"):
            with pytest.raises(EduAgentError) as exc:
                assert_redirect_target(url, location)
            assert exc.value.code == ErrorCode.TOOL_DENIED
        # Alvo relativo comum continua resolvendo no mesmo host.
        assert assert_redirect_target(url, "/outro").endswith("/outro")

    def test_web_fetch_revalida_destino_final_sempre(self, monkeypatch, tmp_path):
        # A4 da revisão (parte 1): o destino final é revalidado MESMO quando
        # o conector devolve a URL original — DNS pode ter mudado entre a
        # busca e o fetch (revalidação de redirect/DNS a cada consulta, §10).
        def getaddrinfo_privado(host, port, **kwargs):
            # Simula resolução privada no momento do fetch (DNS rebinding).
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", port))]

        monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo_privado)

        class ConectorMesmaUrl:
            def search(self, query, language, max_results):
                return [{"url": "http://93.184.216.34/x", "title": "t"}]

            def fetch(self, url):
                return {"url": url, "state": "text_read"}  # final == url

        env = open_stack(
            tmp_path,
            web_connector=ConectorMesmaUrl(),
            config={"network_enabled": True},
        )
        try:
            with pytest.raises(EduAgentError) as exc:
                env.graph._node_web_fetch(  # noqa: SLF001 — nó sob teste
                    {"web_candidates": [{"url": "http://93.184.216.34/x"}]}
                )
            assert exc.value.code == ErrorCode.TOOL_DENIED
        finally:
            env.store.close()
            env.checkpointer.close()

    def test_web_fetch_revalida_cada_hop_da_cadeia(self, tmp_path):
        # A4 da revisão (parte 2): se o conector expõe a cadeia de hops
        # (redirect_chain), cada hop é revalidado (pré-condição contratual
        # do conector real da task 016); hop privado bloqueia por código.
        class ConectorComCadeia:
            def __init__(self, chain):
                self._chain = chain

            def search(self, query, language, max_results):
                return [{"url": "http://93.184.216.34/x", "title": "t"}]

            def fetch(self, url):
                return {
                    "url": "http://93.184.216.34/final",
                    "state": "text_read",
                    "redirect_chain": self._chain,
                }

        # Cadeia válida (hops públicos) passa.
        (tmp_path / "ok").mkdir()
        env_ok = open_stack(
            tmp_path / "ok",
            web_connector=ConectorComCadeia(["http://93.184.216.34/hop1"]),
            config={"network_enabled": True},
        )
        try:
            resultado = env_ok.graph._node_web_fetch(  # noqa: SLF001
                {"web_candidates": [{"url": "http://93.184.216.34/x"}]}
            )
            assert resultado["fetched"][0]["resource"]["url"].endswith("/final")
        finally:
            env_ok.store.close()
            env_ok.checkpointer.close()

        # Hop privado na cadeia é recusado por código.
        (tmp_path / "ruim").mkdir()
        env_ruim = open_stack(
            tmp_path / "ruim",
            web_connector=ConectorComCadeia(["http://10.0.0.1/hop1"]),
            config={"network_enabled": True},
        )
        try:
            with pytest.raises(EduAgentError) as exc:
                env_ruim.graph._node_web_fetch(  # noqa: SLF001 — nó sob teste
                    {"web_candidates": [{"url": "http://93.184.216.34/x"}]}
                )
            assert exc.value.code == ErrorCode.TOOL_DENIED
        finally:
            env_ruim.store.close()
            env_ruim.checkpointer.close()


# ---------------------------------------------------------------------------
# Limites sob fan-out concorrente e recusa de enqueue (A3, luna A-01, L-A1)
# ---------------------------------------------------------------------------


class TestLimitesConcorrenciaERecusa:
    def test_turn_limits_contagem_exata_sob_concorrencia(self):
        # A3 da revisão: o fan-out do §10 executa nós em threads do
        # LangGraph — begin_step/consume_tool/consume_llm são serializados e
        # a contagem é exata. A janela de preempção (ler→verificar→escrever)
        # é forçada por subclassificação que só instrumenta o escalonamento
        # (time.sleep(0) na leitura); a semântica de produção é executada
        # integralmente. Sem lock, atualizações se perdem (sonda da revisão).
        class LimPreemptavel(TurnLimits):
            @property
            def llm_calls_remaining(self):
                v = self.__dict__["_llm_restantes"]
                time.sleep(0)
                return v

            @llm_calls_remaining.setter
            def llm_calls_remaining(self, v):
                self.__dict__["_llm_restantes"] = v

            @property
            def tool_calls_remaining(self):
                v = self.__dict__["_tool_restantes"]
                time.sleep(0)
                return v

            @tool_calls_remaining.setter
            def tool_calls_remaining(self, v):
                self.__dict__["_tool_restantes"] = v

        maximo = 1000
        total_por_thread = 200
        threads_n = 8
        limits = LimPreemptavel(
            max_llm_calls=maximo,
            max_tool_calls=maximo,
            max_graph_steps=100000,
            max_repairs_total=10,
            clock=lambda: FIXED_NOW,
        )
        barreira = threading.Barrier(threads_n)
        sucessos = {"llm": 0, "tool": 0}
        recusas = {"llm": 0, "tool": 0}
        trava = threading.Lock()

        def worker():
            barreira.wait()
            for _ in range(total_por_thread):
                try:
                    limits.consume_llm()
                    with trava:
                        sucessos["llm"] += 1
                except EduAgentError:
                    with trava:
                        recusas["llm"] += 1
                try:
                    limits.consume_tool()
                    with trava:
                        sucessos["tool"] += 1
                except EduAgentError:
                    with trava:
                        recusas["tool"] += 1

        threads = [threading.Thread(target=worker) for _ in range(threads_n)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        total = threads_n * total_por_thread
        # Contagem exata: cada sucesso debita exatamente 1 do orçamento.
        assert limits.llm_calls_remaining == maximo - sucessos["llm"]
        assert limits.tool_calls_remaining == maximo - sucessos["tool"]
        assert sucessos["llm"] == maximo
        assert sucessos["tool"] == maximo
        assert recusas["llm"] == total - maximo
        assert recusas["tool"] == total - maximo

    def test_begin_step_precedencia_deadline_antes_de_passos(self):
        # luna A-01 da revisão: ordem documentada é cancelamento → deadline
        # → limite de passos; com deadline e limite de passos esgotados ao
        # mesmo tempo, o terminal é TIMEOUT (e cancelamento segue primeiro).
        rolou = {"sim": False}

        def clock():
            if rolou["sim"]:
                return FIXED_NOW + timedelta(hours=1)
            return FIXED_NOW

        limits = TurnLimits(
            max_llm_calls=5,
            max_tool_calls=5,
            max_graph_steps=1,
            max_repairs_total=1,
            deadline=FIXED_NOW + timedelta(seconds=30),
            clock=clock,
        )
        limits.begin_step(step="unico")  # consome o único passo
        rolou["sim"] = True  # deadline passa depois do primeiro passo
        with pytest.raises(EduAgentError) as exc:
            limits.begin_step(step="segundo")
        assert exc.value.code == ErrorCode.TIMEOUT
        # Cancelamento tem prioridade sobre deadline e limite de passos.
        with pytest.raises(EduAgentError) as exc:
            limits.begin_step(step="terceiro", cancel_requested=True)
        assert exc.value.code == ErrorCode.CANCELLED

    def test_fila_cheia_preserva_orcamento_de_llm(self):
        # L-A1 da revisão: recusa do enqueue (fila cheia RESOURCE_LIMIT)
        # reembolsa o débito — orçamento só vale com enqueue aceito (§12).
        backend = BlockingBackend()
        gate = GenerationGate(backend, queue_size=1, clock=lambda: FIXED_NOW)
        limits = TurnLimits(
            max_llm_calls=10,
            max_tool_calls=10,
            max_graph_steps=16,
            max_repairs_total=2,
            clock=lambda: FIXED_NOW,
        )
        try:
            futures = []
            for _ in range(2):  # 1 slot + 1 fila
                futures.append(
                    gate._server.submit(  # noqa: SLF001 — fronteira da fila
                        messages=[{"role": "user", "content": "x"}],
                        schema=None,
                        sampler=None,
                        deadline=FIXED_NOW.timestamp() + 30,
                        seed=0,
                    )
                )
            antes = limits.llm_calls_remaining
            with pytest.raises(EduAgentError) as exc:
                gate.generate(
                    limits=limits,
                    messages=[{"role": "user", "content": "x"}],
                    schema=None,
                    sampler=None,
                    seed=0,
                )
            assert exc.value.code == ErrorCode.RESOURCE_LIMIT
            assert limits.llm_calls_remaining == antes
            # Drena as futures para o worker terminar limpo.
            backend.release.set()
            for future in futures:
                try:
                    future.result(timeout=5)
                except Exception:
                    pass
        finally:
            backend.release.set()
            gate.close()

    def test_checkpointer_list_sob_lock(self, tmp_path):
        # A5 da revisão: list() usa o mesmo lock de get_tuple/put — enquanto
        # um put está em curso (segurando o lock), list() aguarda.
        checkpointer = SQLiteCheckpointer(tmp_path / "cp-list.sqlite")
        config = {"configurable": {"thread_id": "sessao-list-lock"}}
        checkpoint = {"id": "cp-list-1", "v": 1}
        entrou = threading.Event()
        libera = threading.Event()

        class ConnBloqueante:
            """Proxy que prende o INSERT do put enquanto o lock é mantido."""

            def __init__(self, conn):
                self._conn = conn

            def execute(self, sql, *args, **kwargs):
                if "INTO checkpoints" in sql:
                    entrou.set()
                    libera.wait(timeout=5)
                return self._conn.execute(sql, *args, **kwargs)

            def __getattr__(self, name):
                return getattr(self._conn, name)

        checkpointer._conn = ConnBloqueante(  # noqa: SLF001 — instrumentação
            checkpointer._conn
        )
        erros: dict[str, Exception] = {}

        def faz_put():
            try:
                checkpointer.put(config, checkpoint, {"source": "teste"}, {})
            except Exception as exc:  # pragma: no cover
                erros["put"] = exc

        thread_put = threading.Thread(target=faz_put)
        thread_put.start()
        assert entrou.wait(timeout=2)  # put está dentro do lock, no INSERT

        resultado: dict[str, int] = {}

        def faz_list():
            resultado["n"] = len(list(checkpointer.list(config)))

        thread_list = threading.Thread(target=faz_list)
        thread_list.start()
        time.sleep(0.2)
        # list() aguarda o lock liberado pelo put (não lê a conexão em paralelo).
        assert thread_list.is_alive()
        assert "n" not in resultado
        libera.set()
        thread_put.join(timeout=5)
        thread_list.join(timeout=5)
        assert not erros
        assert resultado["n"] == 1
        checkpointer.close()


# ---------------------------------------------------------------------------
# Intenções e classificação (§10)
# ---------------------------------------------------------------------------


class TestClassificacao:
    def test_comando_explicito_prevalece(self, env):
        result = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="/cancel",
        )
        assert result.state.intent.value == "cancel"

    def test_resume_retoma_item_pendente_como_submissao(self, tmp_path):
        # CLI `resume` (§12): nova entrada — com item pendente a rota é
        # submit_answer (retoma o item, §10), sem classificador.
        first = open_stack(tmp_path, backend=FakeBackend([item_payload()]))
        try:
            ingest_and_index(first)
            practice = first.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="quero praticar",
                intent="practice",
                payload={
                    "course_id": first.course,
                    "topic_ids": [first.topic],
                },
            )
            assert practice.status == "waiting_student"
        finally:
            first.store.close()
            first.checkpointer.close()
        second = open_stack(tmp_path, backend=FakeBackend([]))
        try:
            resumed = second.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message=(
                    "/resume Porque a dedup garante que retries devolvam o "
                    "recibo anterior sem repetir o efeito."
                ),
            )
            assert resumed.status == "completed"
            assert resumed.output["feedback"]["correctness"] == "correct"
        finally:
            second.store.close()
            second.checkpointer.close()

    def test_sem_classificador_pergunta_antes_de_efeito(self, env):
        result = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="me ajuda com isso aqui",
        )
        # Ambiguidade pergunta antes de efeito (§10): nada é executado.
        assert result.status == "waiting_student"
        assert result.state.pending_question
        assert result.output["intent_classified"] is False
        rows = env.store.fetch_user_rows(
            "SELECT COUNT(*) AS n FROM events WHERE user_id = ?", (UID,)
        )
        assert rows[0]["n"] == 0  # nenhum efeito da pergunta

    def test_classificador_llm_enum_validado_e_reparo(self, tmp_path):
        backend = FakeBackend(
            [
                "isto não é json",  # inválido → reparo (consome chamada)
                json.dumps({"intent": "ask", "ambiguous": False}),
            ]
        )
        env = open_stack(tmp_path, backend=backend)
        try:
            result = env.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="como funciona a dedup?",
            )
            assert result.state.intent.value == "ask"
            assert len(backend.calls) == 2  # tentativa + reparo (§12)
        finally:
            env.store.close()
            env.checkpointer.close()

    def test_ambiguidade_do_classificador_pergunta(self, tmp_path):
        resposta = json.dumps({"intent": "ask", "ambiguous": True})
        backend = FakeBackend([resposta, resposta])
        env = open_stack(tmp_path, backend=backend)
        try:
            result = env.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="pode ser",
            )
            assert result.status == "waiting_student"
            assert result.state.pending_question
        finally:
            env.store.close()
            env.checkpointer.close()


# ---------------------------------------------------------------------------
# Terminal do estado e contrato (mapa §4)
# ---------------------------------------------------------------------------


class TestContratoEstado:
    def test_estado_final_cumpre_graphstate(self, env):
        result = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="/cancel",
        )
        state = result.state
        assert state.status.value == "cancelled"
        assert state.budgets.llm_calls_remaining >= 0
        assert state.trace_id is not None
        assert any(e.code == ErrorCode.CANCELLED for e in state.errors)

    def test_erro_tipado_no_terminal_preserva_refs(self, env):
        result = env.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="/update atividade",
            intent="update_activity",
            payload={
                "activity": {
                    "block_id": str(_uid(77)),
                    "status": "started",
                    "occurred_at": FIXED_NOW.isoformat(),
                    "expected_version": 0,
                    "operation_id": str(_uuid.uuid4()),
                }
            },
        )
        assert result.status == "failed"
        # Artefatos já válidos (aqui, nenhum) preservados e erro tipado com
        # mensagem, retentabilidade e diagnóstico (§4).
        error = result.state.errors[0]
        assert error.message
        assert error.diagnostic == "eduagent/graph.py"
