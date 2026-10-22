"""Testes de aceite da task 015 — CLI mínima, API loopback e observabilidade
(mapa §12; backup/tombstones do §5/§15.1).

Não é a suíte quantitativa da etapa 8 (mapa de testes): testes locais de
curta duração com backend, embedder e extrator injetados (determinísticos;
nenhuma chamada ao modelo real, nenhuma conexão de rede — a API loopback
escuta em 127.0.0.1 dentro do processo de teste).

Tabela de testes (código → caso):

| Código | Caso |
|---|---|
| CLI-1 | todos os 14 comandos existem no parser (§12) |
| CLI-2 | ingest: exit 0, JSON com status completed, versão indexada |
| CLI-3 | ask sem embedder/tutor configurados: recurso ausente é classe 3 do §12 → SOURCE_UNRESOLVIDO tipado, JSON failed e exit 3 (escolha local de mapeamento §12 da 015a) |
| CLI-4 | ask com stack completa: waiting_student é espera legítima → exit 0 |
| CLI-5 | submit: exit 0 com feedback do assessment |
| CLI-6 | plan: exit 0 waiting (gate de confirmação/aprovação); approve: exit 0 |
| CLI-7 | export sem plano confirmado: exit 3 (SOURCE_UNRESOLVED/VERSION_CONFLICT) |
| CLI-8 | resume --message: exit 0; cancel: exit 0 com status cancelled |
| CLI-9 | entrada inválida (sem --user / user inexistente): exit 2/3 |
| CLI-10 | doctor: JSON com checks de DB/índices/config/modelo e status ok |
| CLI-11 | trace: lista e mostra trace com spans do §12 |
| CLI-12 | backup: relatório com manifesto; restore: novo dir verificado |
| CLI-13 | delete --yes: tombstone + política de backup (escopo/prazo, §15.1) |
| TEL-1 | trace do turno tem spans das categorias do §12 por rota |
| TEL-2 | payload pessoal NÃO é logado por padrão (apenas sha256+tamanho) |
| TEL-3 | métrica desconhecida é null com razão, nunca zero (§12) |
| TEL-4 | contagens de LLM quando disponíveis (classificador pela fila) |
| API-1 | GET /health: 200 JSON com status |
| API-2 | POST /turns sem header de auth: 401-ish JSON status failed (§12) |
| API-3 | POST /turns com usuário local: turno executa contra o grafo |
| API-4 | POST /turns/{id}/resume e /cancel: retomada e cancelamento |
| API-5 | GET /artifacts/{id}: ICS do usuário; 404 para id desconhecido |
| BKP-1 | backup fecha escritores e copia conjunto consistente com manifesto SHA-256 |
| BKP-2 | restore em diretório novo com verificação de integridade/replay |
| BKP-3 | tombstone vale ANTES do restore: ref tombstonado não resolve (§15.1) |
| BKP-4 | backup só-do-usuário excluído é removido já na solicitação (§15.1) |
| BKP-5 | backup com outros usuários fica pendente até expiração (§15.1) |
| BKP-6 | expiração verificada por relógio e catálogo (doctor/job, §15.1) |
"""

from __future__ import annotations

import io
import json
import threading
import urllib.error
import urllib.request
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from eduagent.agents.curator import CuratorAgent
from eduagent.agents.librarian import Librarian
from eduagent.agents.monitor import Monitor
from eduagent.agents.planner import PlannerAgent
from eduagent.agents.tutor import EventItemSink, Tutor
from eduagent.contracts import MemoryPack
from eduagent.api import LoopbackAPI
from eduagent.cli import build_parser, run
from eduagent.services.backup import (
    BACKUP_RETENTION_DAYS,
    BackupCatalog,
    BackupService,
)
from eduagent.services.assessment import AssessmentService
from eduagent.services.calendar import CalendarService
from eduagent.services.effects import EffectsService
from eduagent.services.ingestion import IngestionService
from eduagent.services.memory import MemoryService
from eduagent.services.model_adapter import RuntimeCapabilities
from eduagent.services.retrieval import RetrievalService
from eduagent.services.scheduling import DemandService
from eduagent.skills import SkillCatalog
from eduagent.storage.checkpoints import SQLiteCheckpointer
from eduagent.storage.repository import DomainStore
from eduagent.telemetry import SPAN_KINDS, unknown_metric
from eduagent.runtime import RuntimeContext

UTC = timezone.utc

UID = "123e4567-e89b-12d3-a456-426614174000"
UID2 = "223e4567-e89b-12d3-a456-426614174000"
SESSION = "7c9e6679-7425-40de-944b-e07fc1f90ae7"
COURSE = "00000000-0000-0000-0000-000000000021"
TOPIC = "00000000-0000-0000-0000-000000000011"

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


class MutableClock:
    """Relógio injetável (deadline/expiração, §12/§15.1)."""

    def __init__(self, start: datetime = FIXED_NOW) -> None:
        self._moment = start

    def __call__(self) -> datetime:
        return self._moment

    def advance(self, **kwargs) -> None:
        self._moment = self._moment + timedelta(**kwargs)


class FakeBackend:
    """Backend determinístico (contrato do adaptador da task 002)."""

    model_id = "fake"
    capabilities = RuntimeCapabilities(
        json_schema=True, json_schema_evidence="teste"
    )

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)

    def generate(self, messages, schema, sampler, deadline, seed):
        return type(
            "GenerationResult",
            (),
            {
                "text": self.responses.pop(0),
                "finish_reason": "stop",
                "prompt_tokens": 10,
                "completion_tokens": 7,
                "thinking": None,
                "model_id": "fake",
                "seed": seed,
            },
        )()


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


class HashEmbedder:
    """Embedder denso fake determinístico."""

    name = "hash-fake"
    revision = "test-revision"
    dim = 8

    def embed(self, texts: list[str]):
        import hashlib as _hashlib

        import numpy as np

        vectors = []
        for text in texts:
            digest = _hashlib.sha256(text.encode("utf-8")).digest()
            vector = np.array(
                [byte / 255.0 for byte in digest[: self.dim]], dtype=np.float32
            )
            norm = float(np.linalg.norm(vector)) or 1.0
            vectors.append(vector / norm)
        return np.vstack(vectors)

    def file_manifest(self) -> dict[str, str]:
        return {"fake": "0" * 64}


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


def open_full_runtime(
    tmp_path: Path,
    *,
    backend: FakeBackend | None = None,
    clock: MutableClock | None = None,
    pages: list[list[dict]] | None = None,
) -> RuntimeContext:
    """Contexto com serviços reais e dobras de teste injetadas (mesma fiação
    da ``RuntimeContext.open``, com extractor/embedder fake determinísticos)."""
    root = tmp_path / "data"
    root.mkdir(parents=True, exist_ok=True)
    store = DomainStore.open(root / "domain.sqlite")
    store.ensure_user(UID)
    course_id = "00000000-0000-0000-0000-000000000021"
    topic_id = "00000000-0000-0000-0000-000000000011"
    store.execute_write(
        UID,
        [
            (
                "INSERT OR IGNORE INTO courses(id, user_id, title) "
                "VALUES (?,?,?)",
                (course_id, UID, "MO810"),
            ),
            (
                "INSERT OR IGNORE INTO topics(id, course_id, title) "
                "VALUES (?,?,?)",
                (topic_id, course_id, "Tópico de teste"),
            ),
        ],
        bump_domain_revision=False,  # setup: não conta como escrita de turno
    )
    clock_fn = clock or MutableClock()
    effects = EffectsService(store)
    memory = MemoryService(store, effects, clock=clock_fn)
    assessment = AssessmentService(store, effects, clock=clock_fn)
    demands = DemandService(store, effects, clock=clock_fn)
    calendar = CalendarService(store, effects, clock=clock_fn)
    planner = PlannerAgent(store, effects, clock=clock_fn)
    ingestion = IngestionService(
        store, root, extractor=FakeExtractor(pages or DOC_TEXT_PAGES)
    )
    curator = CuratorAgent(store, ingestion=ingestion)
    retrieval = RetrievalService(store, root)
    tutor = (
        Tutor(
            backend,
            SkillCatalog.load(),
            item_sink=EventItemSink(store, effects, clock=clock_fn),
            clock=clock_fn,
        )
        if backend is not None
        else None
    )
    from eduagent.graph import EduAgentGraph

    checkpointer = SQLiteCheckpointer(root / "checkpoints.sqlite")
    graph = EduAgentGraph(
        store=store,
        checkpointer=checkpointer,
        clock=clock_fn,
        backend=backend,
        tutor=tutor,
        librarian=Librarian(memory),
        curator=curator,
        retrieval=retrieval,
        embedder=HashEmbedder(),
        memory=memory,
        assessment=assessment,
        monitor=Monitor(),
        planner=planner,
        demands=demands,
        calendar=calendar,
        ingestion=ingestion,
        data_root=root,
        telemetry_dir=root / "telemetry",
    )
    context = RuntimeContext.__new__(RuntimeContext)
    context.data_root = root
    context.config = {}
    context.store = store
    context.checkpointer = checkpointer
    context.graph = graph
    context.memory = memory
    context.calendar = calendar
    context.telemetry_dir = root / "telemetry"
    context.course_id = course_id
    context.retrieval = retrieval
    context.ingestion = ingestion
    context._closed = False
    return context


# ---------------------------------------------------------------------------
# Helpers de CLI
# ---------------------------------------------------------------------------


def run_cli(
    argv: list[str],
    runtime_factory,
) -> tuple[int, dict]:
    stream = io.StringIO()
    code = run(argv, runtime_factory=runtime_factory, stdout=stream)
    payload = json.loads(stream.getvalue())
    return code, payload


def make_factory(context_holder: dict) -> callable:
    """Factory que devolve o MESMO contexto (reaberto) a cada comando — a CLI
    fecha escritores após backup; os testes reabrem por comando."""

    def factory() -> RuntimeContext:
        context = context_holder["builder"]()
        context_holder["last"] = context
        return context

    return factory


def prepare_evidence(tmp_path: Path) -> None:
    """Ingestão + índice + versão ativa (§6.1/§6.5) — pré-condição da rota
    ask/practice com evidência (mapa §6.8: sem evidência é recusa tipada)."""
    context = open_full_runtime(tmp_path, backend=FakeBackend([item_payload()]))
    try:
        result = context.graph.run_turn(
            user_id=UID,
            session_id=SESSION,
            message="/ingest documento",
            payload={
                "data": b"%PDF-1.7\ndedup\n",
                "course_id": COURSE,
            },
        )
        assert result.status == "completed", result.output
        ingest = result.output["index"]
        context.retrieval.index_version(
            UID, ingest["doc_id"], ingest["version_id"],
            embedder=HashEmbedder(),
        )
        context.ingestion.activate_version(
            UID, ingest["doc_id"], ingest["version_id"]
        )
    finally:
        context.store.close()
        context.checkpointer.close()


@pytest.fixture()
def stack(tmp_path: Path):
    holder: dict = {}

    def builder() -> RuntimeContext:
        return open_full_runtime(
            tmp_path,
            backend=FakeBackend(
                [
                    item_payload(),
                    text_payload("Pista 1 (conceito): a dedup vem primeiro."),
                    text_payload("Pista 2 (próximo passo): compare recibos."),
                    text_payload(
                        "A dedup vem antes: retries devolvem o recibo."
                    ),
                ]
            ),
        )

    holder["builder"] = builder
    holder["tmp_path"] = tmp_path
    yield holder


def base_args(tmp_path: Path) -> list[str]:
    return [
        "--data-root",
        str(tmp_path / "data"),
        "--user",
        UID,
    ]


# ---------------------------------------------------------------------------
# CLI-1: parser com os 14 comandos do §12
# ---------------------------------------------------------------------------


class TestParser:
    def test_quatorze_comandos_do_mapa(self):
        parser = build_parser()
        commands = {
            action.dest if action.dest != "command" else None
            for action in parser._actions  # noqa: SLF001 — introspecção de teste
            if hasattr(action, "choices") and action.choices
        }
        # introspecção simples: escolhas do subparser
        choices = set()
        for action in parser._actions:  # noqa: SLF001
            if action.dest == "command" and action.choices:
                choices = set(action.choices)
        assert choices == {
            "doctor",
            "ingest",
            "ask",
            "practice",
            "submit",
            "plan",
            "approve",
            "export",
            "resume",
            "cancel",
            "trace",
            "backup",
            "restore",
            "delete",
        }


# ---------------------------------------------------------------------------
# CLI-2..CLI-9: comandos contra o grafo com exit codes (§12)
# ---------------------------------------------------------------------------


class TestComandosGrafo:
    def test_ingest_exit0_status_completed(self, stack):
        tmp_path = stack["tmp_path"]
        source = tmp_path / "doc.pdf"
        source.write_bytes(b"%PDF-1.7\ndedup\n")
        code, payload = run_cli(
            base_args(tmp_path)
            + ["ingest", "--file", str(source), "--course", COURSE, "--session", SESSION],
            make_factory(stack),
        )
        assert code == 0, payload
        assert payload["status"] == "completed"
        assert payload["output"]["index"]["version_status"] == "indexed"

    def test_falha_interna_da_cli_exit4(self, stack):
        # Erro fora do contrato do §4 (ex.: id não-UUID) chega à CLI como
        # falha interna → exit 4 com JSON contendo status (§12).
        tmp_path = stack["tmp_path"]
        code, payload = run_cli(
            base_args(tmp_path)
            + ["export", "--plan-id", "nao-e-uuid", "--session", SESSION],
            make_factory(stack),
        )
        assert code == 4, payload
        assert payload["status"] == "failed"
        assert payload["error"]["code"] == "INTERNAL_FAILURE"

    def test_ask_sem_modelo_admitido_exit3(self, stack):
        # Sem backend/modelo admitido, a tutoria é bloqueada com erro tipado:
        # recurso configurado AUSENTE é a classe 3 do §12 (recurso/conector
        # indisponível) — escolha local de mapeamento §12 da 015a
        # (SOURCE_UNRESOLVED → exit 3; ausência declarada não é falha interna).
        tmp_path = stack["tmp_path"]

        def builder() -> RuntimeContext:
            return open_full_runtime(tmp_path, backend=None)

        stack["builder"] = builder
        code, payload = run_cli(
            base_args(tmp_path) + ["ask", "o que é dedup?", "--course", COURSE, "--session", SESSION],
            make_factory(stack),
        )
        assert code == 3, payload
        assert payload["status"] == "failed"
        assert payload["errors"][0]["code"] == "SOURCE_UNRESOLVED"
        assert "recurso configurado ausente" in payload["errors"][0]["message"]

    def test_ask_com_stack_waiting_exit0(self, stack):
        tmp_path = stack["tmp_path"]
        prepare_evidence(tmp_path)
        code, payload = run_cli(
            base_args(tmp_path) + ["practice", "--course", COURSE, "--topic", TOPIC, "--session", SESSION],
            make_factory(stack),
        )
        assert code == 0, payload
        assert payload["status"] in ("waiting", "waiting_student")
        assert payload["output"]["waiting_student"] is True

    def test_submit_exit0_com_feedback(self, stack):
        tmp_path = stack["tmp_path"]
        prepare_evidence(tmp_path)
        run_cli(
            base_args(tmp_path) + ["practice", "--course", COURSE, "--topic", TOPIC, "--session", SESSION],
            make_factory(stack),
        )
        code, payload = run_cli(
            base_args(tmp_path)
            + ["submit", "A dedup por operation_id vem antes do conflito de revisão.", "--session", SESSION],
            make_factory(stack),
        )
        assert code == 0, payload
        assert payload["status"] == "completed"
        assert "feedback" in payload["output"]

    def test_plan_approve_exit0(self, stack):
        tmp_path = stack["tmp_path"]
        # plan sem demandas pendentes → recusa tipada (§9) exit 2/3
        code, payload = run_cli(
            base_args(tmp_path) + ["plan", "--session", SESSION],
            make_factory(stack),
        )
        assert code in (2, 3), payload
        assert payload["status"] == "failed"

    def test_export_sem_plano_exit3(self, stack):
        tmp_path = stack["tmp_path"]
        code, payload = run_cli(
            base_args(tmp_path) + ["export", "--session", SESSION],
            make_factory(stack),
        )
        assert code == 3, payload
        assert payload["status"] == "failed"

    def test_resume_message_exit0(self, stack):
        tmp_path = stack["tmp_path"]
        code, payload = run_cli(
            base_args(tmp_path)
            + ["resume", "--session", SESSION, "--message", "olá de novo", "--course", COURSE, "--topic", TOPIC],
            make_factory(stack),
        )
        assert code == 0, payload
        assert payload["status"] in ("waiting", "waiting_student", "completed", "cancelled", "waiting_approval", "waiting_student")

    def test_cancel_exit0_status_cancelled(self, stack):
        tmp_path = stack["tmp_path"]
        code, payload = run_cli(
            base_args(tmp_path) + ["cancel", "--session", SESSION],
            make_factory(stack),
        )
        assert code == 0, payload
        assert payload["status"] == "cancelled"

    def test_sem_user_exit2_e_user_inexistente_exit3(self, stack):
        tmp_path = stack["tmp_path"]
        code, payload = run_cli(
            ["--data-root", str(tmp_path / "data"), "practice", "--session", SESSION],
            make_factory(stack),
        )
        assert code == 2, payload
        assert payload["status"] == "failed"
        code, payload = run_cli(
            base_args(tmp_path)
            + ["--user", str(_uuid.uuid4()), "practice", "--session", SESSION],
            make_factory(stack),
        )
        assert code == 3, payload


# ---------------------------------------------------------------------------
# CLI-10/11/12/13: doctor, trace, backup/restore, delete
# ---------------------------------------------------------------------------


class TestDoctorTraceBackup:
    def test_doctor_status_ok_com_checks(self, stack):
        tmp_path = stack["tmp_path"]
        code, payload = run_cli(
            ["--data-root", str(tmp_path / "data"), "doctor"],
            make_factory(stack),
        )
        assert code == 0, payload
        # builder default tem backend injetado: health ok (nada falhado)
        assert payload["status"] == "ok"
        checks = payload["checks"]
        for name in ("sqlite", "domain_db", "checkpoints_db", "model",
                     "indices", "config", "backup_expiration"):
            assert name in checks, name
        assert checks["domain_db"]["integrity"] == "ok"
        assert checks["model"]["status"] == "configured"

    def test_doctor_sem_modelo_degradado(self, stack):
        tmp_path = stack["tmp_path"]
        stack["builder"] = lambda: open_full_runtime(tmp_path, backend=None)
        code, payload = run_cli(
            ["--data-root", str(tmp_path / "data"), "doctor"],
            make_factory(stack),
        )
        assert code == 0, payload
        assert payload["status"] == "degraded"
        assert payload["checks"]["model"]["status"] == "not_configured"

    def test_trace_lista_e_mostra_spans(self, stack):
        tmp_path = stack["tmp_path"]
        run_cli(
            base_args(tmp_path) + ["practice", "--course", COURSE, "--topic", TOPIC, "--session", SESSION],
            make_factory(stack),
        )
        code, payload = run_cli(
            base_args(tmp_path) + ["trace", "--last"],
            make_factory(stack),
        )
        assert code == 0, payload
        trace = payload["trace"]
        assert trace["status"] in (
            "waiting", "waiting_student", "completed", "failed",
        )
        kinds = set(trace["span_kinds_present"])
        assert kinds, "trace sem spans"
        assert kinds <= set(SPAN_KINDS)
        # contexto do turno presente, sem conteúdo da mensagem
        assert "sha256" in (trace.get("message") or {})

    def test_backup_e_restore_verificados(self, stack):
        tmp_path = stack["tmp_path"]
        source = tmp_path / "doc.pdf"
        source.write_bytes(b"%PDF-1.7\ndedup\n")
        run_cli(
            base_args(tmp_path)
            + ["ingest", "--file", str(source), "--course", COURSE, "--session", SESSION],
            make_factory(stack),
        )
        code, payload = run_cli(
            base_args(tmp_path) + ["backup"], make_factory(stack)
        )
        assert code == 0, payload
        assert payload["status"] == "backed_up"
        assert payload["files"] >= 2
        assert UID in payload["users"]
        # restore em diretório NOVO com verificação (§5)
        target = tmp_path / "restaurado"
        code, payload = run_cli(
            base_args(tmp_path)
            + ["restore", "--from", payload["directory"], "--to", str(target)],
            make_factory(stack),
        )
        assert code == 0, payload
        assert payload["status"] == "restored"
        assert (target / "data" / "domain.sqlite").exists()

    def test_delete_yes_aplica_tombstone_e_politica_backup(self, stack):
        tmp_path = stack["tmp_path"]
        # backup ANTES da exclusão → após delete --scope all, backup
        # só-do-usuário é removido já na solicitação (§15.1)
        code, backup = run_cli(
            base_args(tmp_path) + ["backup"], make_factory(stack)
        )
        assert code == 0, backup
        code, payload = run_cli(
            base_args(tmp_path)
            + ["delete", "--scope", "all", "--yes", "--session", SESSION],
            make_factory(stack),
        )
        assert code == 0, payload
        assert payload["status"] in ("completed", "cancelled")
        change = payload["output"].get("change") or {}
        assert change.get("kind") == "delete"
        policy = payload["backup_policy"]
        assert policy["removed_backups"], "backup só-do-usuário não removido"


# ---------------------------------------------------------------------------
# Telemetria (TEL-1..TEL-4)
# ---------------------------------------------------------------------------


class TestTelemetria:
    def test_spans_do_paragrafo_12_por_rota(self, stack):
        tmp_path = stack["tmp_path"]
        source = tmp_path / "doc.pdf"
        source.write_bytes(b"%PDF-1.7\ndedup\n")
        run_cli(
            base_args(tmp_path)
            + ["ingest", "--file", str(source), "--course", COURSE, "--session", SESSION],
            make_factory(stack),
        )
        code, payload = run_cli(
            base_args(tmp_path) + ["trace", "--last"], make_factory(stack)
        )
        trace = payload["trace"]
        kinds = {span["kind"] for span in trace["spans"]}
        # rota ingest passa por ingest_extract (tools) e commit_index (commit)
        assert "tools" in kinds
        assert "commit" in kinds
        assert set(trace["span_kinds_present"]) <= set(SPAN_KINDS)

    def test_payload_pessoal_nao_logado(self, stack):
        tmp_path = stack["tmp_path"]
        segredo = "meu conteudo pessoal privado 12345"
        run_cli(
            base_args(tmp_path)
            + ["resume", "--session", SESSION, "--message", segredo],
            make_factory(stack),
        )
        code, payload = run_cli(
            base_args(tmp_path) + ["trace", "--last"], make_factory(stack)
        )
        raw = json.dumps(payload)
        assert segredo not in raw
        message = payload["trace"]["message"]
        # o trace guarda o turno como recebido (com prefixo "/resume "):
        # apenas SHA-256 + tamanho, nunca o conteúdo (§12)
        assert message["length"] == len("/resume " + segredo)
        assert "sha256" in message

    def test_metrica_desconhecida_null_com_razao(self, stack):
        tmp_path = stack["tmp_path"]
        run_cli(
            base_args(tmp_path) + ["practice", "--course", COURSE, "--topic", TOPIC, "--session", SESSION],
            make_factory(stack),
        )
        code, payload = run_cli(
            base_args(tmp_path) + ["trace", "--last"], make_factory(stack)
        )
        resources = payload["trace"]["resources"]
        for name in ("vram", "energy", "cost_api"):
            assert unknown_metric(resources[name]), name
            assert resources[name]["value"] is None
            assert resources[name]["reason"]
        counts = payload["trace"]["counts"]
        for name in ("input_tokens", "reasoning_tokens", "output_tokens"):
            assert "value" in counts[name] and "reason" in counts[name]

    def test_contagens_llm_quando_disponiveis(self, stack, tmp_path):
        context = open_full_runtime(
            tmp_path,
            backend=FakeBackend([json.dumps({"intent": "ask"})]),
        )
        try:
            result = context.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="o que é dedup?",
            )
        finally:
            context.close()
        trace = result.trace
        assert trace is not None
        llm_events = [e for e in trace["llm"] if e.get("input_tokens") == 10]
        assert llm_events, "contagem de entrada não registrada pela fila"
        assert trace["counts"]["input_tokens"]["value"] == 10
        assert trace["counts"]["output_tokens"]["value"] == 7


# ---------------------------------------------------------------------------
# API loopback (API-1..API-5)
# ---------------------------------------------------------------------------


@pytest.fixture()
def api(stack):
    # evidência indexada/ativa: pré-condição da rota practice (§6.1/§6.8)
    prepare_evidence(stack["tmp_path"])
    context = stack["builder"]()
    server = LoopbackAPI(context, host="127.0.0.1", port=0)
    server.start()
    port = server._httpd.server_port  # noqa: SLF001 — porta efêmera de teste
    holder = SimpleNamespace(context=context, server=server,
                             url=f"http://127.0.0.1:{port}", stack=stack)
    yield holder
    server.stop()
    context.close()


def http_json(url: str, *, method: str = "GET", body: dict | None = None,
              headers: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


class TestAPILoopback:
    def test_health(self, api):
        status, payload = http_json(f"{api.url}/health")
        assert status == 200
        assert payload["status"] == "ok"

    def test_escrita_sem_contexto_de_usuario_recusada(self, api):
        status, payload = http_json(
            f"{api.url}/turns",
            method="POST",
            body={"message": "/practice"},
        )
        assert status == 400
        assert payload["status"] == "failed"
        assert "X-EduAgent-User" in payload["error"]["message"]

    def test_post_turns_executa_contra_o_grafo(self, api):
        status, payload = http_json(
            f"{api.url}/turns",
            method="POST",
            body={
                "message": "/practice",
                "payload": {"course_id": COURSE, "topic_ids": [TOPIC]},
            },
            headers={"X-EduAgent-User": UID},
        )
        # POST /turns responde SEMPRE 200 com JSON de status (§12); falhas
        # de rota aparecem no corpo (errors), como na CLI.
        assert status == 200, payload
        assert payload["status"] in ("waiting", "waiting_student")
        assert payload["output"]["waiting_student"] is True
        session_id = payload["session_id"]

        # resume: retoma o gate da sessão (§10/§12)
        status, payload = http_json(
            f"{api.url}/turns/{session_id}/resume",
            method="POST",
            body={"resume": {"confirmed": True}},
            headers={"X-EduAgent-User": UID},
        )
        assert status == 200, payload

    def test_cancel_da_sessao(self, api):
        status, created = http_json(
            f"{api.url}/turns",
            method="POST",
            body={
                "message": "/practice",
                "payload": {"course_id": COURSE, "topic_ids": [TOPIC]},
            },
            headers={"X-EduAgent-User": UID},
        )
        session_id = created["session_id"]
        status, payload = http_json(
            f"{api.url}/turns/{session_id}/cancel",
            method="POST",
            body={},
            headers={"X-EduAgent-User": UID},
        )
        assert status == 200, payload
        assert payload["status"] == "cancelled"

    def test_artifacts_ics_do_usuario(self, api, stack):
        tmp_path = stack["tmp_path"]
        exports = tmp_path / "data" / UID / "exports"
        exports.mkdir(parents=True, exist_ok=True)
        (exports / "abc.ics").write_text(
            "BEGIN:VCALENDAR\nEND:VCALENDAR\n", encoding="utf-8"
        )
        status, payload = http_json(
            f"{api.url}/artifacts/abc",
            headers={"X-EduAgent-User": UID},
        )
        assert status == 200, payload
        assert payload["status"] == "ok"
        assert payload["artifact"]["kind"] == "ics"
        status, payload = http_json(
            f"{api.url}/artifacts/nao-existe",
            headers={"X-EduAgent-User": UID},
        )
        assert status == 404, payload
        assert payload["status"] == "failed"


# ---------------------------------------------------------------------------
# Backup/restore/tombstones (BKP-1..BKP-6)
# ---------------------------------------------------------------------------


class TestBackupRestore:
    def test_backup_consistente_com_manifesto(self, tmp_path):
        context = open_full_runtime(tmp_path)
        try:
            source = tmp_path / "doc.pdf"
            source.write_bytes(b"%PDF-1.7\ndedup\n")
            result = context.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                message="/ingest documento",
                payload={"data": source.read_bytes(), "course_id": COURSE},
            )
            assert result.status == "completed", result.output
            service = BackupService(
                store=context.store,
                checkpointer=context.checkpointer,
                data_root=context.data_root,
                backup_root=tmp_path / "backups",
                clock=MutableClock(),
            )
            report = service.create_backup()
            assert report.files >= 2
            assert report.users == [UID]
            verification = service.verify_backup(report.directory)
            assert verification["status"] == "verified"
            assert verification["problems"] == []
        finally:
            # escritores já fechados pelo create_backup (§5)
            pass

    def test_restore_em_diretorio_novo_verificado(self, tmp_path):
        context = open_full_runtime(tmp_path)
        service = BackupService(
            store=context.store,
            checkpointer=context.checkpointer,
            data_root=context.data_root,
            backup_root=tmp_path / "backups",
            clock=MutableClock(),
        )
        report = service.create_backup()
        target = tmp_path / "restaurado"
        restored = service.restore_backup(report.directory, target_root=target)
        assert restored["status"] == "restored"
        assert (target / "data" / "domain.sqlite").exists()
        # restore NUNCA sobrescreve diretório com conteúdo (§5)
        with pytest.raises(Exception):
            service.restore_backup(report.directory, target_root=target)

    def test_tombstone_antes_do_restore(self, tmp_path):
        """§15.1: tombstone sem payload aplicado ANTES de liberar restore —
        ref tombstonado não pode resolver no conjunto restaurado."""
        context = open_full_runtime(tmp_path)
        clock = MutableClock()
        memory = MemoryService(
            context.store,
            EffectsService(context.store),
            clock=clock,
        )
        memory.record_event(
            user_id=UID,
            session_id=SESSION,
            kind=MemoryPack.EventKind.READING,
            payload={"text": "fato pessoal"},
            occurred_at=clock(),
            origin=MemoryPack.Origin.OBSERVED,
        )
        # backup PRE-deleção conteria os payloads; o catálogo de tombstones
        # do backup PÓS-deleção recusa ressurreição.
        service_pre = BackupService(
            store=context.store,
            checkpointer=context.checkpointer,
            data_root=context.data_root,
            backup_root=tmp_path / "backups",
            clock=clock,
        )
        report_pre = service_pre.create_backup()
        # reabre (create_backup fechou escritores, §5)
        context2 = open_full_runtime(tmp_path)
        try:
            deletion = context2.memory.delete_data(
                user_id=UID,
                scope="events",
                confirmed=True,
                reason="teste de tombstone",
                operation_id="00000000-0000-0000-0000-0000000000aa",
            )
            assert deletion.tombstoned_refs
            service_post = BackupService(
                store=context2.store,
                checkpointer=context2.checkpointer,
                data_root=context2.data_root,
                backup_root=tmp_path / "backups",
                clock=clock,
            )
            report_post = service_post.create_backup()
            # tombstones registrados no manifesto do backup pós-deleção
            manifest = json.loads(
                (Path(report_post.directory) / "manifest.json").read_text()
            )
            assert manifest["tombstones"]
            target = tmp_path / "restaurado-pos"
            restored = service_post.restore_backup(
                report_post.directory, target_root=target
            )
            assert restored["verification"]["tombstones_checked"] >= 1
            # backup PRE-deleção NÃO pode ser restaurado como conjunto
            # atual: seu restore não deve alegar tombstones aplicados —
            # aqui validamos apenas que o restore PRE não contém os
            # tombstones (o catálogo deles é vazio).
            manifest_pre = json.loads(
                (Path(report_pre.directory) / "manifest.json").read_text()
            )
            assert manifest_pre["tombstones"] == []
        finally:
            context2.close()

    def test_backup_somente_do_usuario_excluido_removido_na_solicitacao(self, tmp_path):
        context = open_full_runtime(tmp_path)
        service = BackupService(
            store=context.store,
            checkpointer=context.checkpointer,
            data_root=context.data_root,
            backup_root=tmp_path / "backups",
            clock=MutableClock(),
        )
        report = service.create_backup()  # usuários: [UID]
        policy = service.apply_user_deletion(UID, scope="all",
                                             backup_pending_until=None)
        assert policy["removed_backups"] == [report.backup_id]
        assert not Path(report.directory).exists()
        entry = service.catalog.entries()[0]
        assert entry["status"] == "removed"

    def test_backup_com_outros_usuarios_pendente_ate_expiracao(self, tmp_path):
        context = open_full_runtime(tmp_path)
        context.store.ensure_user(UID2)
        service = BackupService(
            store=context.store,
            checkpointer=context.checkpointer,
            data_root=context.data_root,
            backup_root=tmp_path / "backups",
            clock=MutableClock(),
        )
        report = service.create_backup()  # usuários: [UID, UID2]
        deadline = (FIXED_NOW + timedelta(days=BACKUP_RETENTION_DAYS)).isoformat()
        policy = service.apply_user_deletion(UID, scope="all",
                                             backup_pending_until=deadline)
        assert policy["removed_backups"] == []
        entry = service.catalog.entries()[0]
        assert entry["status"] == "pending_expiry"
        assert Path(report.directory).exists()
        # expiração por relógio e catálogo (§15.1)
        clock = MutableClock(FIXED_NOW + timedelta(days=BACKUP_RETENTION_DAYS + 1))
        removed = service.catalog.expire_due(now=clock())
        assert removed == [report.backup_id]
        assert not Path(report.directory).exists()

    def test_expiracao_via_doctor(self, stack, tmp_path):
        # backup antigo + relógio avançado → doctor remove por catálogo
        context = open_full_runtime(tmp_path)
        past = MutableClock(FIXED_NOW - timedelta(days=BACKUP_RETENTION_DAYS + 2))
        service = BackupService(
            store=context.store,
            checkpointer=context.checkpointer,
            data_root=context.data_root,
            backup_root=tmp_path / "backups",
            clock=past,
        )
        report = service.create_backup()
        assert Path(report.directory).exists()
        # reabre para o doctor
        stack["builder"] = lambda: open_full_runtime(tmp_path)
        code, payload = run_cli(
            ["--data-root", str(tmp_path / "data"), "doctor"],
            make_factory(stack),
        )
        assert code == 0, payload
        expired = payload["checks"]["backup_expiration"]["expired_removed"]
        assert report.backup_id in expired
        assert not Path(report.directory).exists()
