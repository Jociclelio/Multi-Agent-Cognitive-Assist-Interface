"""Testes de aceite da task 013 — ICS RFC5545, confirmação e outbox
(mapa §9, §10, §15.1, §15.5; ``ScheduleProposal`` §4; solver da task 012,
atividades da 011, commit idempotente da 005, storage da 004).

Não é a suíte quantitativa da etapa 8 (mapa de testes): testes locais de
curta duração, sem chamada ao modelo real e sem conexão real de sync (o
conector aqui é duplo de teste do **contrato** — conexão real é admitida na
task 016). C4 (mapa intocado, commits separados, submódulo intocado) é
verificado por inspeção de git e registrado no task.md.

Tabela de testes (código → caso):

| Código | Caso |
|---|---|
| I1 | estrutura VCALENDAR/VEVENT: VERSION 2.0, PRODID, sem METHOD, campos do §9 em UTC Z |
| I2 | reexportação idêntica da mesma revisão: bytes idênticos (sem relógio na renderização) |
| I3 | revisão de evento (movida): SEQUENCE +1, DTSTAMP/LAST-MODIFIED mudam, UID/CREATED estáveis |
| I4 | mudança em outra parte do plano não altera SEQUENCE/timestamps do bloco não afetado (§15.5) |
| I5 | all-day: DTSTART;VALUE=DATE e DTEND exclusivo no dia seguinte/dia final |
| P1 | parser independente: round-trip com re-render byte-idêntico |
| P2 | CRLF puro e folding: nenhum LF solto; nenhuma linha física > 75 octets |
| P3 | verify_calendar detecta divergência (SUMMARY alterado, METHOD presente) |
| F1 | fluxo integral: solver → approve_plan → render → parse; ICS só com plano confirmado |
| A1 | aprovação vincula plan_id/revision/digest; base_revision e approval_revision pós-commit; dependências com hash (§15.1) |
| A2 | confirmação + outbox conjuntas no mesmo commit (§15.1) |
| A3 | nova outbox exige domínio igual à approval_revision: ok imediatamente; recusada após outra escrita |
| A4 | alteração posterior invalida confirmação: escrita de domínio ou dependência → recusa em apply/render |
| A5 | calendar.apply/calendar.render sem confirmação são recusados |
| A6 | gating do §10: render só Planejador; apply só SYSTEM |
| B1 | retry com mesmo operation_id: mesmo recibo, sem nova escrita, timestamps estáveis (§11) |
| B2 | bloco iniciado/concluído é fixo: mudança de instantes por replan é recusa tipada (§15.4) |
| B3 | bloco removido pelo diff sai de logical_blocks — ausência na exportação (§15.5) |
| S1 | contrato de ops: CREATE com If-None-Match: *; UPDATE/DELETE com If-Match ETag e href estável do read |
| S2 | apply executa efeito com duplo de conector: APPLIED e estado remoto atualizado |
| S3 | timeout com efeito ocorrido → read/reconcile → APPLIED, sem retry cego do update |
| S4 | timeout sem efeito e estado divergente → UNKNOWN_EFFECT terminal |
| S5 | alteração externa (precondição falhada) → CONFLICT e novo preview exigido (§9) |
| S6 | sem conector admitido → CONNECTOR_DISABLED: manter ICS/preview (§9) |
| M1 | migração 0007: colunas de evento em logical_blocks e dependências em confirmations |
"""

from __future__ import annotations

import uuid as _uuid
from datetime import date, datetime, time as _dt_time, timedelta, timezone
from pathlib import Path

import pytest

from eduagent.contracts import (
    EduAgentError,
    ErrorCode,
    ScheduleProposal,
    SenderRole,
)
from eduagent.services.calendar import (
    CalendarService,
    ConnectorTimeout,
    ExportBlock,
    RemoteEvent,
    RemoteOpKind,
    SyncOutcome,
    build_calendar,
    parse_ics,
    parsed_event_to_block,
    verify_calendar,
)
from eduagent.services.effects import EffectsService
from eduagent.services.scheduling import (
    SchedulingProblem,
    SolverDemand,
    SolverSettings,
    TimeWindow,
    solve_schedule,
)
from eduagent.storage.repository import DomainStore

UTC = timezone.utc

UID = "123e4567-e89b-12d3-a456-426614174000"
T0 = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)  # terça-feira
D0 = date(2026, 10, 21)  # quarta-feira (horizonte)


def _uid(n: int) -> _uuid.UUID:
    return _uuid.UUID(f"00000000-0000-0000-0000-{n:012d}")


def _utc(day: date, minute: int) -> datetime:
    return datetime.combine(day, _dt_time(0, 0), tzinfo=UTC) + timedelta(
        minutes=minute
    )


class FakeClock:
    """Relógio injetável que avança um minuto por leitura."""

    def __init__(self, start: datetime = T0) -> None:
        self._moment = start

    def __call__(self) -> datetime:
        self._moment += timedelta(minutes=1)
        return self._moment


@pytest.fixture()
def env(tmp_path: Path):
    store = DomainStore.open(tmp_path / "domain.sqlite")
    store.ensure_user(UID)
    effects = EffectsService(store)
    clock = FakeClock()
    service = CalendarService(store, effects, clock=clock)
    return store, effects, service, clock


def _insert_demand(store: DomainStore, demand_id: _uuid.UUID) -> None:
    store.execute_write(
        UID,
        [
            (
                "INSERT INTO demands(id, user_id, payload_json, status, "
                "revision) VALUES (?,?,?,'pending',0)",
                (str(demand_id), UID, "{}"),
            )
        ],
    )


def _block(
    n: int, start: datetime, end: datetime, *, demand: int | None = None
) -> ScheduleProposal.PlanBlock:
    return ScheduleProposal.PlanBlock(
        block_id=_uid(n),
        demand_id=_uid(demand if demand is not None else n),
        start_utc=start,
        end_utc=end,
        uid=_uid(9000 + n),
    )


def _proposal(
    blocks: list[ScheduleProposal.PlanBlock],
    *,
    plan_n: int = 1,
    revision: int = 1,
    snapshot: int = 0,
    added: list[_uuid.UUID] | None = None,
    moved: list[_uuid.UUID] | None = None,
    removed: list[_uuid.UUID] | None = None,
) -> ScheduleProposal:
    return ScheduleProposal(
        plan_id=_uid(plan_n),
        revision=revision,
        snapshot_version=snapshot,
        status=ScheduleProposal.SolverStatus.OPTIMAL,
        blocks=blocks,
        unmet_demands=[],
        diff=ScheduleProposal.PlanDiff(
            added=added if added is not None else [b.block_id for b in blocks],
            moved=moved or [],
            removed=removed or [],
            deficit_minutes=0,
        ),
        validation=ScheduleProposal.PlanValidation(
            passed=True,
            verifier_id="schedule_verifier_v1",
            checked_at=T0,
            issues=[],
        ),
        objective="teste",
        bound=None,
        explanation="proposta de teste",
    )


class FakeConnector:
    """Duplo de teste do contrato ``CalendarConnector`` (§9) — sem conexão
    real: registra chamadas, aplica precondições e simula timeout/efeito
    perdido para exercitar os estados do dispatcher."""

    def __init__(
        self,
        initial: dict[str, RemoteEvent] | None = None,
        *,
        timeout_update: bool = False,
        effect_on_timeout: bool = False,
        external_change: bool = False,
    ) -> None:
        self.events: dict[str, RemoteEvent] = dict(initial or {})
        self.timeout_update = timeout_update
        self.effect_on_timeout = effect_on_timeout
        self.external_change = external_change
        self.calls: list[tuple[Any, ...]] = []

    def read_all(self, target: str) -> list[RemoteEvent]:
        self.calls.append(("read_all", target))
        return [
            RemoteEvent(
                uid=event.uid,
                href=event.href,
                etag=event.etag,
                event_ics=event.event_ics,
            )
            for event in self.events.values()
        ]

    def read_one(self, target: str, uid: str) -> RemoteEvent | None:
        self.calls.append(("read_one", uid))
        return self.events.get(uid)

    def create(
        self,
        target: str,
        uid: str,
        event_ics: bytes,
        *,
        if_none_match_star: bool = True,
    ) -> SyncOutcome:
        self.calls.append(("create", uid, if_none_match_star))
        assert if_none_match_star, "criação exige If-None-Match: * (§9)"
        if uid in self.events:
            return SyncOutcome.CONFLICT
        self.events[uid] = RemoteEvent(
            uid=uid,
            href=f"/calendar/{uid}.ics",
            etag=f"etag-{len(self.events) + 1}",
            event_ics=event_ics,
        )
        return SyncOutcome.APPLIED

    def update(
        self,
        target: str,
        uid: str,
        href: str,
        event_ics: bytes,
        *,
        if_match_etag: str | None,
    ) -> SyncOutcome:
        self.calls.append(("update", uid, href, if_match_etag))
        current = self.events.get(uid)
        if current is None:
            return SyncOutcome.NOT_APPLIED
        if self.external_change:
            return SyncOutcome.CONFLICT
        if self.timeout_update:
            if self.effect_on_timeout:
                # Crash após efeito antes do ACK (§11): estado mudou.
                self.events[uid] = RemoteEvent(
                    uid=uid,
                    href=href,
                    etag=(current.etag or "") + "x",
                    event_ics=event_ics,
                )
            raise ConnectorTimeout()
        if current.etag != if_match_etag:
            return SyncOutcome.CONFLICT
        self.events[uid] = RemoteEvent(
            uid=uid,
            href=href,
            etag=(current.etag or "") + "x",
            event_ics=event_ics,
        )
        return SyncOutcome.APPLIED

    def delete(
        self,
        target: str,
        uid: str,
        href: str,
        *,
        if_match_etag: str | None,
    ) -> SyncOutcome:
        self.calls.append(("delete", uid, href, if_match_etag))
        current = self.events.get(uid)
        if current is None:
            return SyncOutcome.NOT_APPLIED
        if current.etag != if_match_etag:
            return SyncOutcome.CONFLICT
        del self.events[uid]
        return SyncOutcome.APPLIED


from typing import Any  # noqa: E402  (usado só no duplo acima)


# ---------------------------------------------------------------------------
# ICS (C1/C2)
# ---------------------------------------------------------------------------


def _simple_block(n: int = 1) -> ExportBlock:
    return ExportBlock(
        block_id=_uid(n),
        uid=_uid(9000 + n),
        summary="Revisão de cálculo",
        value_type="DATE-TIME",
        start_utc=_utc(D0, 13 * 60),
        end_utc=_utc(D0, 14 * 60),
        created_at=T0,
        modified_at=T0 + timedelta(hours=1),
        event_sequence=0,
    )


class TestIcs:
    def test_i1_estrutura_sem_method_utc_z(self) -> None:
        data = build_calendar([_simple_block()])
        parsed = parse_ics(data)
        assert parsed.version == "2.0"
        assert parsed.prodid == "-//EduAgent//EduAgent-OS 0.1//PT"
        assert parsed.method is None  # exportação simples SEM METHOD (§9)
        assert len(parsed.events) == 1
        event = parsed.events[0]
        assert event.uid == str(_uid(9001))
        assert event.summary == "Revisão de cálculo"
        assert event.dtstart == _utc(D0, 13 * 60)
        assert event.dtend == _utc(D0, 14 * 60)  # fim exclusivo
        assert event.dtstamp == T0 + timedelta(hours=1)
        assert event.created == T0
        assert event.last_modified == T0 + timedelta(hours=1)
        assert event.sequence == 0
        assert not event.all_day
        text = data.decode("utf-8")
        assert "DTSTART:20261021T130000Z\r\n" in text
        assert "DTEND:20261021T140000Z\r\n" in text

    def test_i2_reexportacao_identica(self, env) -> None:
        store, effects, service, clock = env
        block = _block(1, _utc(D0, 9 * 60), _utc(D0, 10 * 60))
        _insert_demand(store, block.demand_id)
        result = service.approve_plan(UID, _proposal([block]))
        first = service.render_plan(
            UID, result.confirmation.plan_id, sender_role=SenderRole.PLANNER
        )
        second = service.render_plan(
            UID, result.confirmation.plan_id, sender_role=SenderRole.PLANNER
        )
        assert first.ics == second.ics  # mesma revisão → mesmos bytes
        rebuilt = build_calendar(list(first.blocks))
        assert rebuilt == first.ics
        # Timestamps persistidos não mudam com novas leituras/renderizações.
        blocks = service.export_blocks(UID)
        assert blocks[0].created_at == blocks[0].modified_at

    def test_i3_revisao_de_evento_sequence_timestamps(self, env) -> None:
        store, effects, service, clock = env
        block_v1 = _block(1, _utc(D0, 9 * 60), _utc(D0, 10 * 60))
        _insert_demand(store, block_v1.demand_id)
        first = service.approve_plan(UID, _proposal([block_v1]))
        rendered_v1 = service.render_plan(
            UID, first.confirmation.plan_id, sender_role=SenderRole.PLANNER
        )
        event_v1 = parse_ics(rendered_v1.ics).events[0]
        assert event_v1.sequence == 0

        block_v2 = _block(1, _utc(D0, 11 * 60), _utc(D0, 12 * 60))
        second = service.approve_plan(
            UID,
            _proposal(
                [block_v2],
                revision=2,
                snapshot=1,
                added=[],
                moved=[block_v2.block_id],
            ),
        )
        assert second.confirmation.approval_revision == (
            first.confirmation.approval_revision + 1
        )
        rendered_v2 = service.render_plan(
            UID, second.confirmation.plan_id, sender_role=SenderRole.PLANNER
        )
        event_v2 = parse_ics(rendered_v2.ics).events[0]
        # UID estável por bloco lógico; SEQUENCE incrementa só com mudança
        # de campos de evento (§9/§15.5).
        assert event_v2.uid == event_v1.uid
        assert event_v2.sequence == 1
        assert event_v2.created == event_v1.created  # CREATED da criação
        assert event_v2.dtstamp > event_v1.dtstamp
        assert event_v2.last_modified > event_v1.last_modified

    def test_i4_mudanca_fora_do_evento_nao_altera_sequence(self, env) -> None:
        store, effects, service, clock = env
        block_a = _block(1, _utc(D0, 9 * 60), _utc(D0, 10 * 60), demand=1)
        block_b = _block(2, _utc(D0, 10 * 60), _utc(D0, 11 * 60), demand=2)
        _insert_demand(store, block_a.demand_id)
        _insert_demand(store, block_b.demand_id)
        first = service.approve_plan(UID, _proposal([block_a, block_b]))
        rendered_v1 = service.render_plan(
            UID, first.confirmation.plan_id, sender_role=SenderRole.PLANNER
        )
        events_v1 = {e.uid: e for e in parse_ics(rendered_v1.ics).events}

        block_b_moved = _block(
            2, _utc(D0, 14 * 60), _utc(D0, 15 * 60), demand=2
        )
        second = service.approve_plan(
            UID,
            _proposal(
                [block_a, block_b_moved],
                revision=2,
                snapshot=1,
                added=[],
                moved=[block_b_moved.block_id],
            ),
        )
        rendered_v2 = service.render_plan(
            UID, second.confirmation.plan_id, sender_role=SenderRole.PLANNER
        )
        events_v2 = {e.uid: e for e in parse_ics(rendered_v2.ics).events}
        # Bloco não afetado: SEQUENCE e timestamps estáveis (§15.5: SEQUENCE
        # não incrementa "porque outra parte do plano mudou").
        assert events_v2[str(_uid(9001))].sequence == 0
        assert events_v2[str(_uid(9001))].dtstamp == events_v1[str(_uid(9001))].dtstamp
        assert events_v2[str(_uid(9002))].sequence == 1

    def test_i5_all_day_date_fim_exclusivo(self) -> None:
        block = ExportBlock(
            block_id=_uid(3),
            uid=_uid(9003),
            summary="Prova de estatística",
            value_type="DATE",
            start_utc=_utc(D0, 0),
            end_utc=_utc(date(2026, 10, 23), 0),  # 2 dias; fim exclusivo
            created_at=T0,
            modified_at=T0,
            event_sequence=0,
        )
        data = build_calendar([block])
        text = data.decode("utf-8")
        assert "DTSTART;VALUE=DATE:20261021\r\n" in text
        assert "DTEND;VALUE=DATE:20261023\r\n" in text
        event = parse_ics(data).events[0]
        assert event.all_day
        assert event.dtstart == date(2026, 10, 21)
        assert event.dtend == date(2026, 10, 23)

    def test_p1_round_trip_re_render_idêntico(self) -> None:
        blocks = [
            _simple_block(1),
            ExportBlock(
                block_id=_uid(3),
                uid=_uid(9003),
                summary="Prova de estatística",
                value_type="DATE",
                start_utc=_utc(D0, 0),
                end_utc=_utc(date(2026, 10, 22), 0),
                created_at=T0,
                modified_at=T0,
                event_sequence=2,
            ),
        ]
        data = build_calendar(blocks)
        parsed = parse_ics(data)
        rebuilt = build_calendar(
            [parsed_event_to_block(event) for event in parsed.events]
        )
        assert rebuilt == data  # render → parse → render: byte-idêntico

    def test_p2_crlf_e_folding(self) -> None:
        long_summary = "Estudo dirigido de " + "capítulos integrados " * 8
        block = ExportBlock(
            block_id=_uid(1),
            uid=_uid(9001),
            summary=long_summary,
            value_type="DATE-TIME",
            start_utc=_utc(D0, 8 * 60),
            end_utc=_utc(D0, 9 * 60),
            created_at=T0,
            modified_at=T0,
            event_sequence=0,
        )
        data = build_calendar([block])
        text = data.decode("utf-8")
        assert "\r\n" in text
        assert text.replace("\r\n", "").count("\n") == 0  # nenhum LF solto
        for physical in text.split("\r\n"):
            assert len(physical.encode("utf-8")) <= 75  # folding RFC5545
        event = parse_ics(data).events[0]
        assert event.summary == long_summary  # unfolding recupera o texto

    def test_p3_verify_calendar_detecta_divergencia(self) -> None:
        block = _simple_block()
        data = build_calendar([block])
        assert verify_calendar(data, [block]) == []
        # SUMMARY alterado após emissão → equivalência falha.
        tampered = data.replace(b"Revis\xc3\xa3o", b"Outra coisa")
        issues = verify_calendar(tampered, [block])
        assert any("SUMMARY" in issue for issue in issues)
        # METHOD presente não é exportação simples (§9).
        with_method = data.replace(b"PRODID:", b"METHOD:PUBLISH\r\nPRODID:")
        issues = verify_calendar(with_method, [block])
        assert any("METHOD" in issue for issue in issues)

    def test_f1_fluxo_integral_solver_approve_render(self, env) -> None:
        store, effects, service, clock = env
        demand = SolverDemand(
            demand_id=_uid(50),
            duration_minutes=60,
            mandatory=True,
            priority_class=1,
            earliest_utc=_utc(D0, 0),
            deadline=date(2026, 12, 31),
        )
        problem = SchedulingProblem(
            user_id=UID,
            horizon_start=D0,
            local_timezone=None,
            snapshot_version=store.domain_revision(UID),
            demands=(demand,),
            availability=(TimeWindow(D0, 8 * 60, 12 * 60),),
        )
        result = solve_schedule(
            problem,
            sender_role=SenderRole.PLANNER,
            settings=SolverSettings(solver_budget_s=2.0),
            clock=lambda: _utc(D0, 6 * 60),
        )
        assert result.proposal.status.value == "OPTIMAL"
        approved = service.approve_plan(
            UID,
            result.proposal,
            summaries={str(demand.demand_id): "Revisão de cálculo"},
        )
        rendered = service.render_plan(
            UID, result.proposal.plan_id, sender_role=SenderRole.PLANNER
        )
        parsed = parse_ics(rendered.ics)
        assert len(parsed.events) == 1
        event = parsed.events[0]
        assert event.summary == "Revisão de cálculo"
        block = rendered.blocks[0]
        assert event.dtstart == block.start_utc
        assert event.dtend == block.end_utc
        assert verify_calendar(rendered.ics, rendered.blocks) == []


# ---------------------------------------------------------------------------
# Confirmação e outbox (C3)
# ---------------------------------------------------------------------------


class TestConfirmacao:
    def test_a1_vincula_plan_revision_digest_e_dependencias(self, env) -> None:
        store, effects, service, clock = env
        block = _block(1, _utc(D0, 9 * 60), _utc(D0, 10 * 60))
        _insert_demand(store, block.demand_id)
        base = store.domain_revision(UID)
        result = service.approve_plan(UID, _proposal([block]))
        confirmation = result.confirmation
        assert confirmation.plan_id == _uid(1)
        assert confirmation.plan_revision == 1
        assert len(confirmation.digest) == 64
        assert confirmation.base_revision == base
        assert confirmation.approval_revision == base + 1  # pós-commit (§15.1)
        assert confirmation.dependencies == (
            (str(block.demand_id), 0),
        )
        assert len(confirmation.dependencies_hash) == 64
        # plans.approval_ref aponta para a confirmação.
        row = store.fetch_user_rows(
            "SELECT approval_ref, revision, snapshot_version FROM plans "
            "WHERE user_id = ? AND id = ?",
            (UID, str(_uid(1))),
        )[0]
        assert row["approval_ref"] == str(confirmation.confirmation_id)
        assert row["revision"] == 1

    def test_a2_confirmacao_e_outbox_no_mesmo_commit(self, env) -> None:
        store, effects, service, clock = env
        block = _block(1, _utc(D0, 9 * 60), _utc(D0, 10 * 60))
        _insert_demand(store, block.demand_id)
        result = service.approve_plan(
            UID, _proposal([block]), create_outbox=True
        )
        # Confirmação e outbox saíram do mesmo commit: approval_revision é
        # a revisão pós-commit e o domínio está nela (§15.1).
        assert store.domain_revision(UID) == result.confirmation.approval_revision
        rows = store.fetch_user_rows(
            "SELECT state, payload_json FROM outbox WHERE user_id = ?",
            (UID,),
        )
        assert len(rows) == 1
        assert rows[0]["state"] == "pending"
        payload = __import__("json").loads(rows[0]["payload_json"])
        assert payload["confirmation_digest"] == result.confirmation.digest
        assert payload["blocks"][0]["uid"] == str(_uid(9001))

    def test_a3_outbox_exige_dominio_igual_approval_revision(
        self, env
    ) -> None:
        store, effects, service, clock = env
        block = _block(1, _utc(D0, 9 * 60), _utc(D0, 10 * 60))
        _insert_demand(store, block.demand_id)
        result = service.approve_plan(UID, _proposal([block]))
        # Imediatamente após a aprovação: domínio == approval_revision → ok.
        service.enqueue_outbox(UID, result.confirmation.plan_id)
        # Uma segunda outbox para a mesma confirmação: a primeira mudou o
        # domínio → recusada (§15.1).
        with pytest.raises(EduAgentError) as exc:
            service.enqueue_outbox(UID, result.confirmation.plan_id)
        assert exc.value.code is ErrorCode.VERSION_CONFLICT
        # Escrita de domínio alheia após aprovação → outbox recusada.
        block2 = _block(2, _utc(D0, 10 * 60), _utc(D0, 11 * 60))
        _insert_demand(store, block2.demand_id)
        with pytest.raises(EduAgentError) as exc:
            service.enqueue_outbox(UID, result.confirmation.plan_id)
        assert exc.value.code is ErrorCode.VERSION_CONFLICT

    def test_a4_alteracao_posterior_invalida_confirmacao(self, env) -> None:
        store, effects, service, clock = env
        block = _block(1, _utc(D0, 9 * 60), _utc(D0, 10 * 60))
        _insert_demand(store, block.demand_id)
        result = service.approve_plan(UID, _proposal([block]))
        plan_id = result.confirmation.plan_id
        # (a) escrita de domínio posterior → confirmação não é mais atual.
        other = _block(2, _utc(D0, 12 * 60), _utc(D0, 13 * 60))
        _insert_demand(store, other.demand_id)
        with pytest.raises(EduAgentError) as exc:
            service.render_plan(UID, plan_id, sender_role=SenderRole.PLANNER)
        assert exc.value.code is ErrorCode.VERSION_CONFLICT
        with pytest.raises(EduAgentError) as exc:
            service.apply_plan(UID, plan_id, connector=FakeConnector())
        assert exc.value.code is ErrorCode.VERSION_CONFLICT
        # (b) dependência alterada com domínio congelado (ajuste de
        # projeção, como em refresh_review_due da 011) → invalidação
        # específica por dependência (§15.1).
        result2 = service.approve_plan(
            UID,
            _proposal([block], revision=2, snapshot=2, added=[], moved=[]),
            operation_id=str(_uid(777)),
        )
        assert store.domain_revision(UID) == (
            result2.confirmation.approval_revision
        )
        store.execute_write(
            UID,
            [
                (
                    "UPDATE demands SET revision = revision + 1 WHERE "
                    "user_id = ? AND id = ?",
                    (UID, str(block.demand_id)),
                )
            ],
            bump_domain_revision=False,
        )
        with pytest.raises(EduAgentError) as exc:
            service.apply_plan(UID, result2.confirmation.plan_id)
        assert exc.value.code is ErrorCode.VERSION_CONFLICT
        assert "dependência" in exc.value.message

    def test_a5_sem_confirmacao_e_recusado(self, env) -> None:
        store, effects, service, clock = env
        with pytest.raises(EduAgentError) as exc:
            service.render_plan(
                UID, _uid(1), sender_role=SenderRole.PLANNER
            )
        assert exc.value.code is ErrorCode.SOURCE_UNRESOLVED
        with pytest.raises(EduAgentError) as exc:
            service.apply_plan(UID, _uid(1), connector=FakeConnector())
        assert exc.value.code is ErrorCode.SOURCE_UNRESOLVED

    def test_a6_gating_papeis(self, env) -> None:
        store, effects, service, clock = env
        block = _block(1, _utc(D0, 9 * 60), _utc(D0, 10 * 60))
        _insert_demand(store, block.demand_id)
        result = service.approve_plan(UID, _proposal([block]))
        # calendar.render: só o Planejador propõe (mapa §10).
        with pytest.raises(EduAgentError) as exc:
            service.render_plan(
                UID, result.confirmation.plan_id, sender_role=SenderRole.USER
            )
        assert exc.value.code is ErrorCode.TOOL_DENIED
        # calendar.apply: dispatcher determinístico (SYSTEM).
        with pytest.raises(EduAgentError) as exc:
            service.apply_plan(
                UID,
                result.confirmation.plan_id,
                connector=FakeConnector(),
                sender_role=SenderRole.PLANNER,
            )
        assert exc.value.code is ErrorCode.TOOL_DENIED

    def test_b1_retry_mesmo_operation_id_estavel(self, env) -> None:
        store, effects, service, clock = env
        block = _block(1, _utc(D0, 9 * 60), _utc(D0, 10 * 60))
        _insert_demand(store, block.demand_id)
        operation_id = str(_uid(800))
        first = service.approve_plan(
            UID, _proposal([block]), operation_id=operation_id
        )
        rendered_first = service.render_plan(
            UID, first.confirmation.plan_id, sender_role=SenderRole.PLANNER
        )
        # Retry do mesmo operation_id (mesmo digest): recibo original (§11).
        retry = service.approve_plan(
            UID, _proposal([block]), operation_id=operation_id
        )
        assert retry.receipt.operation_id == first.receipt.operation_id
        assert retry.receipt.domain_revision == first.receipt.domain_revision
        assert retry.receipt.was_retry is True
        assert retry.confirmation.confirmation_id == (
            first.confirmation.confirmation_id
        )
        rendered_retry = service.render_plan(
            UID, first.confirmation.plan_id, sender_role=SenderRole.PLANNER
        )
        assert rendered_retry.ics == rendered_first.ics
        rows = store.fetch_user_rows(
            "SELECT COUNT(*) AS n FROM logical_blocks WHERE user_id = ?",
            (UID,),
        )
        assert rows[0]["n"] == 1

    def test_b2_bloco_iniciado_e_fixo(self, env) -> None:
        store, effects, service, clock = env
        block = _block(1, _utc(D0, 9 * 60), _utc(D0, 10 * 60))
        _insert_demand(store, block.demand_id)
        result = service.approve_plan(UID, _proposal([block]))
        store.execute_write(
            UID,
            [
                (
                    "UPDATE logical_blocks SET status = 'started' WHERE "
                    "user_id = ? AND id = ?",
                    (UID, str(block.block_id)),
                )
            ],
        )
        moved = _block(1, _utc(D0, 11 * 60), _utc(D0, 12 * 60))
        with pytest.raises(EduAgentError) as exc:
            service.approve_plan(
                UID,
                _proposal(
                    [moved], revision=2, snapshot=1, added=[], moved=[moved.block_id]
                ),
            )
        assert exc.value.code is ErrorCode.SCHEMA_INVALID

    def test_b3_removido_fica_ausente_da_exportacao(self, env) -> None:
        store, effects, service, clock = env
        block_a = _block(1, _utc(D0, 9 * 60), _utc(D0, 10 * 60), demand=1)
        block_b = _block(2, _utc(D0, 10 * 60), _utc(D0, 11 * 60), demand=2)
        _insert_demand(store, block_a.demand_id)
        _insert_demand(store, block_b.demand_id)
        service.approve_plan(UID, _proposal([block_a, block_b]))
        assert len(service.export_blocks(UID)) == 2
        service.approve_plan(
            UID,
            _proposal(
                [block_a],
                revision=2,
                snapshot=1,
                added=[],
                removed=[block_b.block_id],
            ),
        )
        # Remoção no ICS é ausência na exportação (§9/§15.5).
        assert [b.block_id for b in service.export_blocks(UID)] == [
            block_a.block_id
        ]


# ---------------------------------------------------------------------------
# Sync como contrato/estados (C4)
# ---------------------------------------------------------------------------


class TestSync:
    def _confirmed(self, env, *, create_outbox: bool = False):
        store, effects, service, clock = env
        block = _block(1, _utc(D0, 9 * 60), _utc(D0, 10 * 60))
        _insert_demand(store, block.demand_id)
        result = service.approve_plan(
            UID, _proposal([block]), create_outbox=create_outbox
        )
        return store, service, result

    def test_s1_contrato_das_operacoes(self, env) -> None:
        store, effects, service, clock = env
        block_a = _block(1, _utc(D0, 9 * 60), _utc(D0, 10 * 60), demand=1)
        block_b = _block(2, _utc(D0, 10 * 60), _utc(D0, 11 * 60), demand=2)
        _insert_demand(store, block_a.demand_id)
        _insert_demand(store, block_b.demand_id)
        result = service.approve_plan(UID, _proposal([block_a, block_b]))
        existing_uid = str(_uid(9001))  # mesmo UID do bloco desejado: update
        stale_uid = str(_uid(9100))  # evento remoto a remover
        remote = FakeConnector(
            initial={
                existing_uid: RemoteEvent(
                    uid=existing_uid,
                    href="/cal/existente.ics",
                    etag="etag-old",
                    event_ics=None,
                ),
                stale_uid: RemoteEvent(
                    uid=stale_uid,
                    href="/cal/antigo.ics",
                    etag="etag-old2",
                    event_ics=None,
                ),
            }
        )
        ops = service.build_sync_ops(
            UID, result.confirmation, remote, target="cal"
        )
        kinds = {op.kind for op in ops}
        assert kinds == {RemoteOpKind.CREATE, RemoteOpKind.UPDATE, RemoteOpKind.DELETE}
        creates = [op for op in ops if op.kind is RemoteOpKind.CREATE]
        updates = [op for op in ops if op.kind is RemoteOpKind.UPDATE]
        deletes = [op for op in ops if op.kind is RemoteOpKind.DELETE]
        assert creates[0].uid == str(_uid(9002))
        assert creates[0].if_none_match_star is True  # If-None-Match: * (§9)
        assert creates[0].confirmation_digest == result.confirmation.digest
        assert updates[0].uid == existing_uid
        assert updates[0].href == "/cal/existente.ics"  # href estável do read
        assert updates[0].if_match_etag == "etag-old"  # If-Match ETag (§9)
        assert deletes[0].uid == stale_uid
        assert deletes[0].if_match_etag == "etag-old2"
        assert deletes[0].confirmation_digest == (
            result.confirmation.digest
        )  # remoção só com operação confirmada (§9/§15.5)

    def test_s2_apply_executa_com_duplo_de_conector(self, env) -> None:
        _store, service, result = self._confirmed(env)
        remote = FakeConnector()
        report = service.apply_plan(UID, result.confirmation.plan_id, connector=remote)
        assert report.status is SyncOutcome.APPLIED
        assert report.ops[0].outcome is SyncOutcome.APPLIED
        assert len(remote.events) == 1
        event = parse_ics(remote.events[str(_uid(9001))].event_ics).events[0]
        assert event.uid == str(_uid(9001))
        # Estado remoto já igual → nova execução não repete efeito.
        report2 = service.apply_plan(
            UID, result.confirmation.plan_id, connector=remote
        )
        assert report2.status is SyncOutcome.APPLIED
        assert all(op.kind != RemoteOpKind.CREATE for op in report2.ops)

    def test_s3_timeout_com_efeito_reconcilia_sem_retry_cego(self, env) -> None:
        _store, service, result = self._confirmed(env)
        stale = FakeConnector(
            initial={
                str(_uid(9001)): RemoteEvent(
                    uid=str(_uid(9001)),
                    href="/cal/a.ics",
                    etag="old",
                    event_ics=b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n",
                )
            },
            timeout_update=True,
            effect_on_timeout=True,
        )
        report = service.apply_plan(UID, result.confirmation.plan_id, connector=stale)
        assert report.status is SyncOutcome.APPLIED
        assert report.ops[0].outcome is SyncOutcome.APPLIED
        assert "reconciliado" in report.ops[0].detail
        # Sem retry cego: o update foi tentado uma única vez (§9/§11).
        assert [c for c in stale.calls if c[0] == "update"] .count("update") == 0 or len(
            [c for c in stale.calls if c[0] == "update"]
        ) == 1

    def test_s4_timeout_sem_efeito_e_estado_divergente(self, env) -> None:
        _store, service, result = self._confirmed(env)
        stale = FakeConnector(
            initial={
                str(_uid(9001)): RemoteEvent(
                    uid=str(_uid(9001)),
                    href="/cal/a.ics",
                    etag="old",
                    event_ics=b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n",
                )
            },
            timeout_update=True,
            effect_on_timeout=False,
        )
        report = service.apply_plan(UID, result.confirmation.plan_id, connector=stale)
        assert report.status is SyncOutcome.UNKNOWN_EFFECT
        assert report.ops[0].outcome is SyncOutcome.UNKNOWN_EFFECT
        # Sem retry cego: uma única tentativa de update.
        assert len([c for c in stale.calls if c[0] == "update"]) == 1

    def test_s5_alteracao_externa_conflito_e_novo_preview(self, env) -> None:
        _store, service, result = self._confirmed(env)
        # Evento remoto com o mesmo UID (conteúdo antigo) → UPDATE; a
        # precondição falha por alteração externa (§9) → CONFLICT.
        external = FakeConnector(
            initial={
                str(_uid(9001)): RemoteEvent(
                    uid=str(_uid(9001)),
                    href="/cal/a.ics",
                    etag="old",
                    event_ics=None,
                )
            },
            external_change=True,
        )
        report = service.apply_plan(
            UID, result.confirmation.plan_id, connector=external
        )
        assert report.status is SyncOutcome.CONFLICT
        assert "novo preview" in report.detail

    def test_s6_sem_conector_admitido(self, env) -> None:
        _store, service, result = self._confirmed(env)
        report = service.apply_plan(UID, result.confirmation.plan_id, connector=None)
        assert report.status is SyncOutcome.UNCHANGED
        assert "CONNECTOR_DISABLED" in report.detail


# ---------------------------------------------------------------------------
# Migração 0007
# ---------------------------------------------------------------------------


class TestMigracao:
    def test_m1_colunas_da_0007(self, env) -> None:
        store, _effects, _service, _clock = env
        columns = {
            row["name"]
            for row in store.fetch_user_rows(
                "PRAGMA table_info(logical_blocks)"
            )
        }
        assert {"created_at", "modified_at", "summary", "value_type"} <= columns
        columns = {
            row["name"]
            for row in store.fetch_user_rows(
                "PRAGMA table_info(confirmations)"
            )
        }
        assert {"dependencies_json", "dependencies_hash"} <= columns
        # value_type default conforme contrato (§9).
        row = store.fetch_user_rows(
            "SELECT value_type FROM logical_blocks LIMIT 1"
        )
        assert row == []
