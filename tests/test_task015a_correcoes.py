"""Testes de regressão da task 015a — correção da entrega da 015
(ownership usuário↔sessão, tombstones do domínio corrente no restore,
confinamento de caminhos do manifesto, JSON em falha interna da API,
observador de erro de geração e span de fila).

Sondas da revisão da 015 reproduzidas ANTES da correção (comportamento
defeituoso) e corrigidas; cada teste abaixo fixa o comportamento corrigido.
Não é a suíte quantitativa da etapa 8: testes locais de curta duração, sem
rede externa e sem modelo real.

Tabela (código → caso):

| Código | Caso |
|---|---|
| OWN-1 | API: usuário B não resume gate da sessão de A (403 TOOL_DENIED sem efeito); A retoma |
| OWN-2 | API: usuário B não cancela sessão de A (403 TOOL_DENIED; estado intacto); A cancela |
| OWN-3 | CLI: B não aplica deleção de A via resume --data (exit 3 TOOL_DENIED); A aplica |
| OWN-4 | CLI: B não aprova sessão de A (exit 3 TOOL_DENIED) |
| TOM-1 | backup pré-deleção + delete + restore → recusa tipada com diretório descartado (§15.1, domínio corrente) |
| TOM-2 | verificador de tombstones: ref tombstonado vivo no manifesto → recusa INTERNAL_FAILURE com diretório descartado (teste negativo, GLM-A3) |
| PTH-1 | manifesto com componente ``..`` → recusa tipada SCHEMA_INVALID, diretório descartado (§10) |
| PTH-2 | manifesto com caminho ABSOLUTO → recusa tipada SCHEMA_INVALID, diretório descartado (§10) |
| API-6 | exceção fora do contrato no POST /turns → JSON status failed/INTERNAL_FAILURE com HTTP 500 (§12: JSON sempre com status) |
| TEL-5 | falha de geração publica evento de erro ao observador do trace (baixo a) |
| TEL-6 | categoria ``queue`` emite span por evento de geração (baixo b) |
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from eduagent.contracts import EduAgentError, ErrorCode
from eduagent.services.backup import BackupService
from eduagent.services.model_adapter import ModelAdapterError
from eduagent.storage.repository import DomainStore

from test_task015_cli_api import (  # noqa: F401 — fixtures reexportadas
    COURSE,
    SESSION,
    TOPIC,
    UID,
    UID2,
    api,
    base_args,
    http_json,
    make_factory,
    open_full_runtime,
    prepare_evidence,
    run_cli,
    stack,
)
from datetime import datetime, timezone
from eduagent.policy import GenerationGate, TurnLimits
from eduagent.telemetry import SPAN_KINDS

UTC = timezone.utc

# Mensagem do erro de ownership (§12): recusa tipada por código.
OWNERSHIP_MARK = "sessão de outro usuário"


def ensure_user(tmp_path: Path, user_id: str) -> None:
    """Registra o segundo usuário do domínio local (contexto autenticado)."""
    store = DomainStore.open(tmp_path / "data" / "domain.sqlite")
    try:
        store.ensure_user(user_id)
    finally:
        store.close()


def new_backup_service(context, tmp_path: Path, clock=None) -> BackupService:
    return BackupService(
        store=context.store,
        checkpointer=context.checkpointer,
        data_root=context.data_root,
        backup_root=tmp_path / "backups",
        clock=clock,
    )


def restore_service(context, tmp_path: Path, clock=None) -> BackupService:
    """Serviço de restore como na CLI (store fechado; domínio corrente é o
    ``data_root`` vivo)."""
    return BackupService(
        store=None,
        checkpointer=None,
        data_root=context.data_root,
        backup_root=tmp_path / "backups",
        clock=clock,
    )


# ---------------------------------------------------------------------------
# Item 1 — ownership usuário↔sessão (GLM-A1, precedente A1 da 014a)
# ---------------------------------------------------------------------------


class TestOwnershipSessao:
    def test_api_b_nao_resume_sessao_de_a(self, api, stack):
        tmp_path = stack["tmp_path"]
        ensure_user(tmp_path, UID2)
        # A abre a sessão com gate de espera (waiting_student, §10)
        status, created = http_json(
            f"{api.url}/turns",
            method="POST",
            body={
                "message": "/practice",
                "payload": {"course_id": COURSE, "topic_ids": []},
            },
            headers={"X-EduAgent-User": UID},
        )
        session_id = created["session_id"]
        # B autenticado tenta retomar a sessão de A → recusa tipada, 403
        status, payload = http_json(
            f"{api.url}/turns/{session_id}/resume",
            method="POST",
            body={"resume": {"confirmed": True}},
            headers={"X-EduAgent-User": UID2},
        )
        assert status == 403, payload
        assert payload["status"] == "failed"
        assert payload["error"]["code"] == "TOOL_DENIED"
        assert OWNERSHIP_MARK in payload["error"]["message"]
        # O dono retoma normalmente (nenhum efeito foi aplicado por B)
        status, payload = http_json(
            f"{api.url}/turns/{session_id}/resume",
            method="POST",
            body={"resume": {"confirmed": True}},
            headers={"X-EduAgent-User": UID},
        )
        assert status == 200, payload

    def test_api_b_nao_cancela_sessao_de_a(self, api, stack):
        tmp_path = stack["tmp_path"]
        ensure_user(tmp_path, UID2)
        status, created = http_json(
            f"{api.url}/turns",
            method="POST",
            body={
                "message": "/practice",
                "payload": {"course_id": COURSE, "topic_ids": []},
            },
            headers={"X-EduAgent-User": UID},
        )
        session_id = created["session_id"]
        status, payload = http_json(
            f"{api.url}/turns/{session_id}/cancel",
            method="POST",
            body={},
            headers={"X-EduAgent-User": UID2},
        )
        assert status == 403, payload
        assert payload["error"]["code"] == "TOOL_DENIED"
        # Estado intacto: A cancela com sucesso depois da recusa de B
        status, payload = http_json(
            f"{api.url}/turns/{session_id}/cancel",
            method="POST",
            body={},
            headers={"X-EduAgent-User": UID},
        )
        assert status == 200, payload
        assert payload["status"] == "cancelled"

    def test_cli_b_nao_aplica_delecao_de_a(self, stack):
        tmp_path = stack["tmp_path"]
        ensure_user(tmp_path, UID2)
        # A pede exclusão sem --yes: gate de confirmação na sessão de A (§10)
        code, preview = run_cli(
            base_args(tmp_path)
            + ["delete", "--scope", "events", "--session", SESSION],
            make_factory(stack),
        )
        assert code == 0, preview
        assert preview["status"].startswith("waiting")
        # B tenta confirmar a deleção de A: recusa tipada SEM aplicar efeito
        code, payload = run_cli(
            ["--data-root", str(tmp_path / "data"), "--user", UID2,
             "resume", "--session", SESSION,
             "--data", json.dumps({"confirmed": True})],
            make_factory(stack),
        )
        assert code == 3, payload
        assert payload["status"] == "failed"
        assert payload["error"]["code"] == "TOOL_DENIED"
        assert OWNERSHIP_MARK in payload["error"]["message"]
        # A confirma: efeito aplicado pelo dono (nada foi aplicado por B)
        code, payload = run_cli(
            base_args(tmp_path)
            + ["resume", "--session", SESSION,
               "--data", json.dumps({"confirmed": True})],
            make_factory(stack),
        )
        assert code == 0, payload
        change = (payload.get("output") or {}).get("change") or {}
        assert change.get("kind") == "delete"

    def test_cli_b_nao_aprova_sessao_de_a(self, stack):
        tmp_path = stack["tmp_path"]
        ensure_user(tmp_path, UID2)
        # Sessão EXISTENTE de A (turno de espera, §10): approve de B é
        # recusado ANTES da retomada (§12: efeito de sessão exige o dono
        # autenticado)
        prepare_evidence(tmp_path)
        code, payload = run_cli(
            base_args(tmp_path)
            + ["practice", "--course", COURSE, "--topic", TOPIC, "--session", SESSION],
            make_factory(stack),
        )
        assert code == 0, payload
        code, payload = run_cli(
            ["--data-root", str(tmp_path / "data"), "--user", UID2,
             "approve", "--session", SESSION],
            make_factory(stack),
        )
        assert code == 3, payload
        assert payload["status"] == "failed"
        assert payload["error"]["code"] == "TOOL_DENIED"
        assert OWNERSHIP_MARK in payload["error"]["message"]


# ---------------------------------------------------------------------------
# Item 2 — tombstones do domínio corrente no restore (qwen-A1, §15.1)
# ---------------------------------------------------------------------------


class TestTombstoneDominioCorrente:
    def test_backup_pre_delecao_nao_ressuscita_payload(self, tmp_path):
        """§15.1: tombstone sem payload aplicado ANTES de liberar restore —
        backup que ANTECEDE a deleção não pode ressuscitar o payload
        tombstonado no domínio corrente (sonda qwen-A1 corrigida)."""
        from eduagent.contracts import MemoryPack
        from eduagent.services.effects import EffectsService
        from eduagent.services.memory import MemoryService

        context = open_full_runtime(tmp_path)
        clock_value = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
        memory = MemoryService(
            context.store,
            EffectsService(context.store),
            clock=lambda: clock_value,
        )
        memory.record_event(
            user_id=UID,
            session_id=SESSION,
            kind=MemoryPack.EventKind.READING,
            payload={"text": "PAGODO-SECRETO-DELETA-ME"},
            occurred_at=clock_value,
            origin=MemoryPack.Origin.OBSERVED,
        )
        service_pre = new_backup_service(context, tmp_path)
        report_pre = service_pre.create_backup()  # fecha escritores (§5)
        # deleção APÓS o backup: tombstone no domínio corrente
        context2 = open_full_runtime(tmp_path)
        try:
            deletion = context2.memory.delete_data(
                user_id=UID,
                scope="events",
                confirmed=True,
                reason="teste 015a",
                operation_id="00000000-0000-0000-0000-0000000000cc",
            )
            assert deletion.tombstoned_refs
            target = tmp_path / "restaurado-pre"
            with pytest.raises(EduAgentError) as exc:
                restore_service(context2, tmp_path).restore_backup(
                    report_pre.directory, target_root=target
                )
            assert exc.value.code == ErrorCode.INTERNAL_FAILURE
            assert "domínio corrente" in str(exc.value)
            # diretório descartado: nada parcial é liberado (§5)
            assert not target.exists()
        finally:
            context2.close()

    def test_verificador_recusa_ref_tombstonado_vivo(self, tmp_path):
        """Teste negativo do verificador (GLM-A3): ref tombstonado VIVO no
        manifesto do próprio backup → recusa INTERNAL_FAILURE com diretório
        descartado (caminho alegado pela evidência do C3 da 015)."""
        from eduagent.contracts import MemoryPack
        from eduagent.services.effects import EffectsService
        from eduagent.services.memory import MemoryService

        context = open_full_runtime(tmp_path)
        clock_value = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
        memory = MemoryService(
            context.store,
            EffectsService(context.store),
            clock=lambda: clock_value,
        )
        recorded = memory.record_event(
            user_id=UID,
            session_id=SESSION,
            kind=MemoryPack.EventKind.READING,
            payload={"text": "conteudo vivo sonda"},
            occurred_at=clock_value,
            origin=MemoryPack.Origin.OBSERVED,
        )
        row = context.store.fetch_user_rows(
            "SELECT id FROM events WHERE user_id = ? "
            "ORDER BY rowid DESC LIMIT 1",
            (UID,),
        )
        assert row, "evento de teste não registrado"
        event_id = str(row[0]["id"])
        service = new_backup_service(context, tmp_path)
        report = service.create_backup()  # fecha escritores (§5)
        manifest_path = Path(report.directory) / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["tombstones"] = [
            {"ref": f"event:{event_id}@1", "kind": "event"}
        ]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        target = tmp_path / "restaurado-neg"
        with pytest.raises(EduAgentError) as exc:
            service.restore_backup(report.directory, target_root=target)
        assert exc.value.code == ErrorCode.INTERNAL_FAILURE
        assert "tombstone violado no restore" in str(exc.value)
        assert not target.exists()


# ---------------------------------------------------------------------------
# Item 3 — confinamento de caminhos do manifesto (luna-A1, §10)
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestConfinamentoCaminhosRestore:
    @pytest.fixture()
    def backup_com_arquivo(self, tmp_path):
        """Backup legítimo + manifesto original preservado para adulteração."""
        context = open_full_runtime(tmp_path)
        service = new_backup_service(context, tmp_path)
        report = service.create_backup()  # fecha escritores (§5)
        pristine = (
            Path(report.directory) / "manifest.json"
        ).read_bytes()
        return service, report, pristine

    def _restore_com_manifesto(self, service, report, pristine, evil: str,
                               tmp_path: Path) -> None:
        directory = Path(report.directory)
        (directory / "manifest.json").write_bytes(pristine)
        planted = directory / evil
        planted.parent.mkdir(parents=True, exist_ok=True)
        planted.write_text("payload fora da raiz", encoding="utf-8")
        manifest = json.loads(
            (directory / "manifest.json").read_text(encoding="utf-8")
        )
        manifest["files"] = {
            **manifest["files"],
            evil: _sha256(planted),  # hash REAL: só o confinamento decide
        }
        (directory / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        target = tmp_path / f"alvo-{abs(hash(evil))}"
        with pytest.raises(EduAgentError) as exc:
            service.restore_backup(directory, target_root=target)
        assert exc.value.code == ErrorCode.SCHEMA_INVALID
        assert not target.exists()

    def test_manifesto_com_traversal_recusado(
        self, backup_com_arquivo, tmp_path
    ):
        service, report, pristine = backup_com_arquivo
        self._restore_com_manifesto(
            service, report, pristine, "../vazou.txt", tmp_path
        )

    def test_manifesto_com_caminho_absoluto_recusado(
        self, backup_com_arquivo, tmp_path
    ):
        service, report, pristine = backup_com_arquivo
        self._restore_com_manifesto(
            service, report, pristine,
            str(tmp_path / "fora" / "vazou-abs.txt"), tmp_path,
        )

    def test_verificador_tambem_recusa_caminho_malicioso(
        self, backup_com_arquivo, tmp_path
    ):
        """A verificação (primeira etapa do restore) já recusa por código —
        nada é copiado antes do confinamento (§10)."""
        service, report, pristine = backup_com_arquivo
        directory = Path(report.directory)
        (directory / "manifest.json").write_bytes(pristine)
        manifest = json.loads(
            (directory / "manifest.json").read_text(encoding="utf-8")
        )
        manifest["files"] = {**manifest["files"], "../x.txt": "0" * 64}
        (directory / "manifest.json").write_text(json.dumps(manifest))
        with pytest.raises(EduAgentError) as exc:
            service.verify_backup(directory)
        assert exc.value.code == ErrorCode.SCHEMA_INVALID
        assert ".." in str(exc.value)


# ---------------------------------------------------------------------------
# Item 4 — API responde JSON em falha interna (qwen-A2, §12)
# ---------------------------------------------------------------------------


class TestAPIFalhaInterna:
    def test_excecao_fora_do_contrato_responde_json_500(self, api):
        """ValueError de UUID malformado escapa dos handlers tipados: o
        dispatch responde JSON com status failed e INTERNAL_FAILURE (§12:
        JSON sempre contém status; a conexão nunca é encerrada sem corpo)."""
        status, payload = http_json(
            f"{api.url}/turns",
            method="POST",
            body={
                "message": "/export",
                "payload": {"plan_id": "nao-e-uuid"},
                "session_id": SESSION,
            },
            headers={"X-EduAgent-User": UID},
        )
        assert status == 500, payload
        assert payload["status"] == "failed"
        assert payload["error"]["code"] == "INTERNAL_FAILURE"
        assert payload["error"]["diagnostic"] == "eduagent/api.py"


# ---------------------------------------------------------------------------
# Itens baixos — observador de erro de geração (a) e span de fila (b)
# ---------------------------------------------------------------------------


class _FailBackend:
    """Backend que falha no caminho da geração (erro tipado do §4)."""

    model_id = "fake-fail"

    def generate(self, messages, schema, sampler, deadline, seed):
        raise ModelAdapterError(
            ErrorCode.TIMEOUT,
            "geração simulada excedeu o deadline",
            retryable=True,
        )


class TestItensBaixos:
    def test_falha_de_geracao_publica_evento_ao_observador(self):
        """(a) Falha de geração publica evento com erro ao observador do
        trace (mesma forma da recusa de fila) — o caminho de erro não fica
        sem evento (qwen-A3/GLM-A5)."""
        events: list[dict] = []
        gate = GenerationGate(
            _FailBackend(), clock=lambda: datetime.now(UTC),
            observer=events.append,
        )
        limits = TurnLimits(
            max_llm_calls=2,
            max_tool_calls=2,
            max_graph_steps=10,
            max_repairs_total=1,
            deadline=None,
            clock=lambda: datetime.now(UTC),
        )
        from eduagent.contracts import EduAgentError

        with pytest.raises(EduAgentError):
            gate.generate(
                limits=limits,
                messages=[{"role": "user", "content": "pergunta"}],
                schema=None,
                sampler={"temperature": 0.0, "top_p": 1.0},
                seed=0,
            )
        assert len(events) == 1, "falha de geração sem evento ao observador"
        assert events[0]["result"] is None
        assert events[0]["error"] is not None

    def test_categoria_queue_emite_span_no_trace(self, stack, tmp_path):
        """(b) Span de fila por evento de geração: a categoria ``queue`` do
        §12 aparece no trace do turno (GLM-A4/qwen-A4)."""
        context = open_full_runtime(
            tmp_path, backend=type(
                "B", (),
                {
                    "model_id": "fake",
                    "capabilities": None,
                    "generate": lambda self, *a, **k: type(
                        "R", (),
                        {
                            "text": json.dumps({"intent": "ask"}),
                            "finish_reason": "stop",
                            "prompt_tokens": 5,
                            "completion_tokens": 3,
                            "thinking": None,
                            "model_id": "fake",
                            "seed": 0,
                        },
                    )(),
                },
            )()
        )
        try:
            result = context.graph.run_turn(
                user_id=UID,
                session_id=SESSION,
                # mensagem sem comando explícito: passa pelo classificador
                # (geração real pela fila → evento de fila ao observador)
                message="o que é dedup?",
            )
        finally:
            context.close()
        trace = result.trace
        assert trace is not None
        kinds = {span["kind"] for span in trace["spans"]}
        assert "queue" in kinds
        assert kinds <= set(SPAN_KINDS)
        queue_spans = [s for s in trace["spans"] if s["kind"] == "queue"]
        assert queue_spans[0]["attributes"].get("queue_known") is True
        assert queue_spans[0]["active_s"] is not None
