"""Testes de aceite da task 012 — solver CP-SAT lexicográfico e verificador
independente (mapa §9, §15.5; ``ScheduleProposal`` §4; demandas/atividades
da task 011, storage da 004, contratos da 003).

Não é a suíte quantitativa da etapa 8 (mapa de testes): testes locais de
curta duração, sem chamada ao modelo real. C4 (mapa intocado, commits
separados, submódulo intocado) é verificado por inspeção de git e registrado
no task.md. Defaults numéricos (solver_budget_s=10, slot_minutes=15,
horizon_days=7, seed=0, num_workers=1) são escolhas de ensaio da config —
NUNCA resultados medidos.

Tabela de testes (código → caso):

| Código | Caso |
|---|---|
| G1 | modelo base: obrigatória Σ=1 com disponibilidade → OPTIMAL, bloco no início da janela |
| G2 | earliest confirmado respeitado |
| G3 | deadline datetime respeitado (instante original, sem arredondar prazo) |
| G4 | deadline só de dia: vale até a meia-noite seguinte; dia seguinte fica fora |
| G5 | precedência end_i ≤ start_j quando ambos presentes (§9) |
| G6 | presence_j ≤ presence_i: pré-requisito obrigatório não é omitido |
| G7 | dependência cíclica (e auto-dependência) → erro explícito, não INFEASIBLE |
| G8 | exclusividade por slot: duas obrigatórias que não cabem → INFEASIBLE provado + mensagem da grade conservadora |
| G9 | candidatos não atravessam meia-noite (§15.5) |
| G10 | horizonte de 7 datas: dia dentro agenda; dia fora fica não agendado |
| G11 | capacidade diária mede minutos reservados (arredondamento p/ cima), não duração nominal |
| G12 | compromisso pessoal arredondado para fora e não conta como estudo (§15.5) |
| G13 | bloco fixo de estudo conta na capacidade diária (§15.5) |
| G14 | instantes locais inexistentes/ambíguos são rejeitados até confirmação (§15.5) |
| G15 | settings inválidos (slot que não divide 1440) → erro tipado |
| L1 | lexicografia completa com defaults da config: 6 etapas OPTIMAL, status OPTIMAL |
| L2 | prioridade lexicográfica: classe1 vence classe2 no mesmo slot |
| L3 | FEASIBLE numa fase interrompe a lexicografia e conserva solução válida com provas |
| L4 | primeira fase UNKNOWN → UNKNOWN, nada publicado como aprovado |
| L5 | UNKNOWN posterior → incumbent anterior publicado como FEASIBLE com provas |
| L6 | INFEASIBLE é conflito provado (sem solução, sem relaxação publicada) |
| L7 | MODEL_INVALID é defeito e não publica blocos |
| L8 | orçamento dividido por remaining_seconds/remaining_stages com tempo reaproveitado |
| L9 | minimizar alterações vence preferência: ocorrência aprovada é mantida |
| L10 | deslocamento mínimo em slots quando a manutenção é impossível |
| L11 | preferências (overlap em minutos) como desempate final |
| L12 | identidade: block_id/uid permanecem em mudança de horário (§15.5) |
| V1 | verificador aprova proposta válida do solver |
| V2 | violação só visível fora da matriz (duração reduzida nos instantes) é rejeitada |
| V3 | sobreposição de blocos é rejeitada |
| V4 | snapshot divergente é rejeitado (§15.1) |
| V5 | obrigatória ausente é rejeitada |
| V6 | diff inconsistente com a identidade é rejeitado (§15.5) |
| V7 | status sem solução com blocos é rejeitado (nunca publicar relaxação) |
| V8 | preview com diff por identidade: movida + adicionada, sem remoção |
| K1 | config default.yaml alimenta SolverSettings (10/15/7/0/1) e from_mapping |
| K2 | slot_minutes e horizon_days da config governam o solve |
| R1 | schedule.solve só pode ser proposto pelo Planejador (mapa §10) |
| J1 | janelas adjacentes (8:15–9:15 e 9:15–10:15) com obrigatória de 90 min: solução válida publicada, nunca INTERNAL_FAILURE (correção 012a) |
| J2 | janelas sobrepostas sem janela única que caiba a demanda: união das janelas governa enumerador e verificador (correção 012a) |
| J3 | verificador: emenda adjacente é cobertura pela união; vão entre janelas disjuntas é rejeitado (bloqueios para fora, §9) |
| J4 | identidade do diff preservada entre preview e proposta: movida mantém block_id/uid; ocorrências distintas nunca colidem na mesma identidade |
"""

from __future__ import annotations

import uuid as _uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

import eduagent.services.scheduling as sched
from eduagent.contracts import (
    EduAgentError,
    ErrorCode,
    ScheduleProposal,
    SenderRole,
)
from eduagent.services.scheduling import (
    DailyStudyLimit,
    ExistingOccurrence,
    FixedBlock,
    SchedulingProblem,
    SolverDemand,
    SolverSettings,
    TimeWindow,
    load_solver_settings,
    solve_schedule,
    verify_schedule,
)

UTC = timezone.utc
D0 = date(2026, 10, 21)  # quarta-feira


def _uid(n: int) -> _uuid.UUID:
    return _uuid.UUID(f"00000000-0000-0000-0000-{n:012d}")


def _utc(day: date, minute: int) -> datetime:
    return datetime.combine(day, datetime.min.time(), tzinfo=UTC) + timedelta(
        minutes=minute
    )


def _demand(
    n: int,
    *,
    duration: int = 30,
    mandatory: bool = False,
    klass: int = 3,
    earliest: datetime | None = None,
    deadline: datetime | date | None = None,
    dependencies: tuple[_uuid.UUID, ...] = (),
    occurrence_id: _uuid.UUID | None = None,
) -> SolverDemand:
    return SolverDemand(
        demand_id=_uid(n),
        duration_minutes=duration,
        mandatory=mandatory,
        priority_class=klass,
        earliest_utc=earliest or _utc(D0, 0),
        deadline=deadline if deadline is not None else date(D0.year, 12, 31),
        dependencies=dependencies,
        occurrence_id=occurrence_id,
    )


def _window(day: date, start: int, end: int) -> TimeWindow:
    return TimeWindow(day=day, start_minute=start, end_minute=end)


def _solve(problem: SchedulingProblem, **kwargs):
    settings = kwargs.pop("settings", None) or SolverSettings(
        solver_budget_s=2.0
    )
    return solve_schedule(
        problem,
        sender_role=SenderRole.PLANNER,
        settings=settings,
        clock=lambda: _utc(D0, 6 * 60),
        **kwargs,
    )


def _script_driver(monkeypatch: pytest.MonkeyPatch, script: list[str | None]):
    """Sobrescreve o status reportado por etapa (protocolo do §15.5) sem
    alterar o modelo: a seleção continua sendo a solução real do CP-SAT."""
    calls: list[tuple[str, float]] = []
    original = sched._LexicographicDriver._solve_stage

    def fake(self, stage, seconds):
        index = len(calls)
        calls.append((stage.name, seconds))
        status, value, selected = original(self, stage, seconds)
        override = script[index] if index < len(script) else None
        if override is not None:
            status = override
            if override in ("UNKNOWN", "INFEASIBLE", "MODEL_INVALID"):
                value = None
                selected = None
        return status, value, selected

    monkeypatch.setattr(sched._LexicographicDriver, "_solve_stage", fake)
    return calls


# ---------------------------------------------------------------------------
# C1 — modelo, grade/UTC/horizonte, erro de ciclo
# ---------------------------------------------------------------------------


def test_g1_modelo_base_obrigatoria_sigma_1():
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1, mandatory=True),),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    result = _solve(problem)
    proposal = result.proposal
    assert proposal.status is ScheduleProposal.SolverStatus.OPTIMAL
    assert len(proposal.blocks) == 1
    block = proposal.blocks[0]
    assert block.start_utc == _utc(D0, 8 * 60)
    assert block.end_utc == _utc(D0, 8 * 60 + 30)
    assert proposal.validation.passed is True
    assert proposal.diff.added and not proposal.diff.moved
    assert proposal.unmet_demands == []


def test_g2_earliest_confirmado():
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(
            _demand(1, mandatory=True, earliest=_utc(D0, 10 * 60)),
        ),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    result = _solve(problem)
    assert result.proposal.blocks[0].start_utc == _utc(D0, 10 * 60)


def test_g3_deadline_datetime_instante_original():
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(
            _demand(1, mandatory=True, deadline=_utc(D0, 9 * 60)),
        ),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    result = _solve(problem)
    assert result.proposal.blocks[0].end_utc <= _utc(D0, 9 * 60)


def test_g4_deadline_sozinho_de_dia_vale_ate_meia_noite_seguinte():
    # Prazo é o próprio dia D0: bloco pode terminar exatamente na meia-noite
    # seguinte (fim exclusivo); janela no dia seguinte já está fora.
    late = _window(D0, 23 * 60 + 30, 24 * 60)
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1, mandatory=True, deadline=D0),),
        availability=(late,),
    )
    result = _solve(problem)
    assert result.proposal.blocks[0].end_utc == _utc(D0 + timedelta(days=1), 0)

    problem_next = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1, deadline=D0),),
        availability=(_window(D0 + timedelta(days=1), 8 * 60, 9 * 60),),
    )
    result_next = _solve(problem_next)
    assert result_next.proposal.blocks == []
    assert result_next.proposal.diff.deficit_minutes == 30


def test_g5_precedencia_end_antes_de_start():
    pred = _demand(1, mandatory=True)
    dep = _demand(2, mandatory=True, dependencies=(pred.demand_id,))
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(pred, dep),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    result = _solve(problem)
    by_demand = {b.demand_id: b for b in result.proposal.blocks}
    assert by_demand[pred.demand_id].end_utc <= by_demand[dep.demand_id].start_utc


def test_g6_presence_le_presence_pre_requisito_obrigatorio():
    # Janela de 30 min comporta só um bloco: se o dependente opcional fosse
    # selecionado, o pré-requisito obrigatório seria omitido — presence_j ≤
    # presence_i impede; resultado: pré-requisito agendado, dependente não.
    pred = _demand(1, mandatory=True)
    dep = _demand(2, klass=1, dependencies=(pred.demand_id,))
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(pred, dep),
        availability=(_window(D0, 8 * 60, 8 * 60 + 30),),
    )
    result = _solve(problem)
    scheduled = {b.demand_id for b in result.proposal.blocks}
    assert scheduled == {pred.demand_id}
    assert result.proposal.unmet_demands == [dep.demand_id]


def test_g7_dependencia_ciclica_e_erro_explicito():
    # a → b → a: ciclo real (§9: dependência cíclica é erro explícito).
    a = _demand(1, dependencies=(_uid(2),))
    b = _demand(2, dependencies=(_uid(1),))
    base = dict(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    with pytest.raises(EduAgentError) as exc:
        solve_schedule(
            SchedulingProblem(demands=(a, b), **base),  # a → b → a
            sender_role=SenderRole.PLANNER,
            settings=SolverSettings(solver_budget_s=1.0),
        )
    assert exc.value.code is ErrorCode.SCHEMA_INVALID
    assert "cíclica" in exc.value.message

    with pytest.raises(EduAgentError) as exc_self:
        solve_schedule(
            SchedulingProblem(
                demands=(_demand(4, dependencies=(_uid(4),)),), **base
            ),
            sender_role=SenderRole.PLANNER,
            settings=SolverSettings(solver_budget_s=1.0),
        )
    assert exc_self.value.code is ErrorCode.SCHEMA_INVALID


def test_g8_exclusividade_por_slot_infeasible_provido():
    first = _demand(1, mandatory=True)
    second = _demand(2, mandatory=True)
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(first, second),
        availability=(_window(D0, 8 * 60, 8 * 60 + 45),),  # 3 slots, 4 precisos
    )
    result = _solve(problem)
    proposal = result.proposal
    assert proposal.status is ScheduleProposal.SolverStatus.INFEASIBLE
    assert proposal.blocks == []
    assert proposal.validation.passed is False
    assert "inviável na grade conservadora de 15 min" in proposal.explanation
    assert "viabilidade contínua não determinada" in proposal.explanation


def test_g9_candidatos_nao_atravessam_meia_noite():
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1, mandatory=True),),
        availability=(_window(D0, 23 * 60 + 45, 24 * 60),),  # 1 slot só
    )
    result = _solve(problem)
    # 30 min exigiriam 2 slots atravessando a meia-noite — proibido no MVP.
    assert result.proposal.status is ScheduleProposal.SolverStatus.INFEASIBLE


def test_g10_horizonte_de_sete_datas():
    inside = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1),),
        availability=(_window(D0 + timedelta(days=6), 8 * 60, 9 * 60),),
    )
    result = _solve(inside)
    assert len(result.proposal.blocks) == 1

    outside = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1),),
        availability=(_window(D0 + timedelta(days=7), 8 * 60, 9 * 60),),
    )
    result_outside = _solve(outside)
    assert result_outside.proposal.blocks == []
    assert result_outside.proposal.diff.deficit_minutes == 30


def test_g11_capacidade_diaria_em_minutos_reservados():
    # Duração nominal 20 min reserva 30 min (ceil) — limite de 25 não basta.
    demand = _demand(1, duration=20)
    tight = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(demand,),
        availability=(_window(D0, 8 * 60, 12 * 60),),
        daily_limits=(DailyStudyLimit(day=D0, study_minutes=25),),
    )
    result = _solve(tight)
    assert result.proposal.blocks == []
    assert result.proposal.diff.deficit_minutes == 20

    loose = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(demand,),
        availability=(_window(D0, 8 * 60, 12 * 60),),
        daily_limits=(DailyStudyLimit(day=D0, study_minutes=30),),
    )
    result_loose = _solve(loose)
    assert len(result_loose.proposal.blocks) == 1
    block = result_loose.proposal.blocks[0]
    assert (block.end_utc - block.start_utc) == timedelta(minutes=30)


def test_g12_compromisso_arredondado_para_fora_e_nao_conta_como_estudo():
    commitment = FixedBlock(
        start_utc=_utc(D0, 8 * 60 + 5),
        end_utc=_utc(D0, 8 * 60 + 20),
        counts_as_study=False,
    )
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1, duration=15, mandatory=True),),
        availability=(_window(D0, 8 * 60, 12 * 60),),
        fixed_blocks=(commitment,),
        daily_limits=(DailyStudyLimit(day=D0, study_minutes=15),),
    )
    result = _solve(problem)
    block = result.proposal.blocks[0]
    # Bloqueio arredondado para fora: 08:00–08:30 ocupado; compromisso de
    # 15 min não conta como estudo — limite de 15 min ainda permite estudar.
    assert block.start_utc >= _utc(D0, 8 * 60 + 30)
    assert block.end_utc <= _utc(D0, 12 * 60)


def test_g13_bloco_fixo_de_estudo_conta_na_capacidade():
    fixed_study = FixedBlock(
        start_utc=_utc(D0, 8 * 60),
        end_utc=_utc(D0, 8 * 60 + 30),
        counts_as_study=True,
    )
    base = dict(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1, duration=15),),
        availability=(_window(D0, 8 * 60, 12 * 60),),
        fixed_blocks=(fixed_study,),
    )
    full = SchedulingProblem(
        daily_limits=(DailyStudyLimit(day=D0, study_minutes=30),), **base
    )
    result = _solve(full)
    assert result.proposal.blocks == []
    assert result.proposal.diff.deficit_minutes == 15

    free = SchedulingProblem(
        daily_limits=(DailyStudyLimit(day=D0, study_minutes=45),), **base
    )
    assert len(_solve(free).proposal.blocks) == 1

    # Limite confirmado menor que os fixos é inconsistência explícita.
    inconsistent = SchedulingProblem(
        daily_limits=(DailyStudyLimit(day=D0, study_minutes=15),), **base
    )
    with pytest.raises(EduAgentError) as exc:
        _solve(inconsistent)
    assert exc.value.code is ErrorCode.SCHEMA_INVALID


def test_g14_instantes_locais_inexistentes_ou_ambiguos_sao_rejeitados():
    tz = ZoneInfo("America/Sao_Paulo")  # zona explícita do teste, não default
    # DST 2018/2019: em 04/11/2018 a meia-noite local não existe.
    nonexistent = SchedulingProblem(
        user_id="u",
        horizon_start=date(2018, 11, 4),
        local_timezone=tz,
        snapshot_version=1,
        demands=(_demand(1, duration=15, mandatory=True),),
        availability=(_window(date(2018, 11, 4), 0, 60),),
    )
    with pytest.raises(EduAgentError) as exc:
        _solve(nonexistent)
    assert exc.value.code is ErrorCode.AMBIGUOUS_INPUT
    assert "não existe" in exc.value.message

    # Fim do DST: em 16/02/2019 a hora 23:00–23:59 ocorre duas vezes.
    ambiguous = SchedulingProblem(
        user_id="u",
        horizon_start=date(2019, 2, 16),
        local_timezone=tz,
        snapshot_version=1,
        demands=(_demand(2, duration=15, mandatory=True),),
        availability=(_window(date(2019, 2, 16), 23 * 60, 24 * 60),),
    )
    with pytest.raises(EduAgentError) as exc_amb:
        _solve(ambiguous)
    assert exc_amb.value.code is ErrorCode.AMBIGUOUS_INPUT
    assert "ambíguo" in exc_amb.value.message


def test_g15_settings_invalidos_erro_tipado():
    with pytest.raises(EduAgentError) as exc:
        SolverSettings(slot_minutes=7)  # 1440 % 7 != 0
    assert exc.value.code is ErrorCode.SCHEMA_INVALID


# ---------------------------------------------------------------------------
# C2 — lexicografia com orçamento de 10 s
# ---------------------------------------------------------------------------


def test_l1_lexicografia_completa_com_defaults_da_config():
    first = _demand(1, klass=1)
    second = _demand(2, klass=2)
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(first, second),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    # Defaults da config (solver_budget_s=10 etc.) — escolha de ensaio.
    result = solve_schedule(
        problem,
        sender_role=SenderRole.PLANNER,
        clock=lambda: _utc(D0, 6 * 60),
    )
    assert result.proposal.status is ScheduleProposal.SolverStatus.OPTIMAL
    assert [p.status for p in result.proofs] == ["OPTIMAL"] * 6
    assert [p.stage for p in result.proofs] == [
        "max_class1",
        "max_class2",
        "max_class3",
        "min_changes",
        "min_displacement_min",
        "max_preferences",
    ]
    assert len(result.proposal.blocks) == 2


def test_l2_classe1_vence_classe2_no_mesmo_slot():
    first = _demand(1, klass=1)
    second = _demand(2, klass=2)
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(first, second),
        availability=(_window(D0, 8 * 60, 8 * 60 + 30),),
    )
    result = _solve(problem)
    scheduled = {b.demand_id for b in result.proposal.blocks}
    assert scheduled == {first.demand_id}
    assert result.proposal.unmet_demands == [second.demand_id]
    assert "max_class1=1" in result.proposal.objective


def test_l3_feasible_interrompe_e_conserva_solucao_valida(monkeypatch):
    calls = _script_driver(monkeypatch, ["OPTIMAL", "FEASIBLE"])
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1, klass=1), _demand(2, klass=2)),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    result = _solve(problem)
    assert result.proposal.status is ScheduleProposal.SolverStatus.FEASIBLE
    assert [p.status for p in result.proofs] == ["OPTIMAL", "FEASIBLE"]
    assert len(calls) == 2  # lexicografia interrompida na segunda etapa
    assert result.proposal.validation.passed is True
    assert len(result.proposal.blocks) >= 1


def test_l4_primeira_fase_unknown_nao_publica_nada(monkeypatch):
    _script_driver(monkeypatch, ["UNKNOWN"])
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1, mandatory=True),),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    result = _solve(problem)
    proposal = result.proposal
    assert proposal.status is ScheduleProposal.SolverStatus.UNKNOWN
    assert proposal.blocks == []
    assert proposal.validation.passed is False
    assert set(proposal.unmet_demands) == {_uid(1)}
    assert proposal.diff.deficit_minutes == 30


def test_l5_unknown_posterior_publica_incumbent_anterior_como_feasible(
    monkeypatch,
):
    _script_driver(monkeypatch, ["OPTIMAL", "UNKNOWN"])
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1, klass=1),),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    result = _solve(problem)
    assert result.proposal.status is ScheduleProposal.SolverStatus.FEASIBLE
    assert [p.status for p in result.proofs] == ["OPTIMAL", "UNKNOWN"]
    assert len(result.proposal.blocks) == 1
    assert result.proposal.validation.passed is True


def test_l6_infeasible_provido_sem_relaxacao_publicada():
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1, mandatory=True),),
        availability=(),  # nenhuma disponibilidade no horizonte
    )
    result = _solve(problem)
    proposal = result.proposal
    assert proposal.status is ScheduleProposal.SolverStatus.INFEASIBLE
    assert proposal.blocks == []
    assert proposal.validation.passed is False
    assert "inviável na grade conservadora de 15 min" in proposal.explanation


def test_l7_model_invalid_e_defeito_sem_blocos(monkeypatch):
    _script_driver(monkeypatch, ["MODEL_INVALID"])
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1),),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    result = _solve(problem)
    proposal = result.proposal
    assert proposal.status is ScheduleProposal.SolverStatus.MODEL_INVALID
    assert proposal.blocks == []
    assert proposal.validation.passed is False


def test_l8_orcamento_dividido_e_reaproveitado(monkeypatch):
    calls = _script_driver(monkeypatch, [None] * 6)
    budget = 6.0
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1),),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    result = _solve(problem, settings=SolverSettings(solver_budget_s=budget))
    assert result.proposal.status is ScheduleProposal.SolverStatus.OPTIMAL
    assert len(calls) == 6
    limits = [seconds for _, seconds in calls]
    assert limits[0] == pytest.approx(budget / 6, abs=1e-6)
    assert all(limit <= budget + 1e-9 for limit in limits)
    # Tempo não consumido é reaproveitado: os recortes crescem.
    assert limits == sorted(limits)


def test_l9_minimizar_alteracoes_vence_preferencia():
    demand = _demand(1, occurrence_id=_uid(101))
    existing = ExistingOccurrence(
        occurrence_id=_uid(101),
        block_id=_uid(201),
        demand_id=demand.demand_id,
        start_utc=_utc(D0, 9 * 60),
        end_utc=_utc(D0, 9 * 60 + 30),
    )
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(demand,),
        availability=(_window(D0, 8 * 60, 12 * 60),),
        preferred=(_window(D0, 10 * 60, 11 * 60),),
        existing=(existing,),
    )
    result = _solve(problem)
    block = result.proposal.blocks[0]
    assert block.start_utc == _utc(D0, 9 * 60)  # mantida apesar da preferência
    assert result.proposal.diff.moved == []
    assert result.proposal.diff.added == []


def test_l10_deslocamento_minimo_quando_manutencao_e_impossivel():
    demand = _demand(1, occurrence_id=_uid(101))
    existing = ExistingOccurrence(
        occurrence_id=_uid(101),
        block_id=_uid(201),
        demand_id=demand.demand_id,
        start_utc=_utc(D0, 9 * 60),
        end_utc=_utc(D0, 9 * 60 + 30),
    )
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(demand,),
        availability=(
            _window(D0, 8 * 60, 9 * 60),  # Δ mínimo possível: 30 min (08:30)
            _window(D0, 10 * 60, 12 * 60),  # Δ ≥ 60 min para frente
        ),
        existing=(existing,),
    )
    result = _solve(problem)
    block = result.proposal.blocks[0]
    assert block.start_utc == _utc(D0, 8 * 60 + 30)  # Δ = 30 min, o menor
    assert result.proposal.diff.moved == [_uid(201)]
    assert "min_changes=1" in result.proposal.objective


def test_l11_preferencias_como_desempate_final():
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1),),
        availability=(
            _window(D0, 8 * 60, 9 * 60),
            _window(D0, 10 * 60, 11 * 60),
        ),
        preferred=(_window(D0, 10 * 60, 10 * 60 + 30),),  # overlap máximo único
    )
    result = _solve(problem)
    assert result.proposal.blocks[0].start_utc == _utc(D0, 10 * 60)
    assert "max_preferences=30" in result.proposal.objective


def test_l12_identidade_permanece_em_mudanca_de_horario():
    demand = _demand(1, occurrence_id=_uid(101))
    existing = ExistingOccurrence(
        occurrence_id=_uid(101),
        block_id=_uid(201),
        demand_id=demand.demand_id,
        start_utc=_utc(D0, 9 * 60),
        end_utc=_utc(D0, 9 * 60 + 30),
        uid=_uid(301),
    )
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(demand,),
        availability=(_window(D0, 10 * 60, 12 * 60),),
        existing=(existing,),
    )
    result = _solve(problem)
    block = result.proposal.blocks[0]
    assert block.block_id == _uid(201)  # §15.5: block_id permanece
    assert block.uid == _uid(301)  # uid permanece
    assert result.proposal.diff.moved == [_uid(201)]


# ---------------------------------------------------------------------------
# C3 — verificador separado em minutos/instantes originais
# ---------------------------------------------------------------------------


def _fabricated(
    blocks: list[ScheduleProposal.PlanBlock],
    *,
    status: ScheduleProposal.SolverStatus = ScheduleProposal.SolverStatus.OPTIMAL,
    snapshot: int = 1,
    diff: ScheduleProposal.PlanDiff | None = None,
    unmet: list[_uuid.UUID] | None = None,
) -> ScheduleProposal:
    return ScheduleProposal(
        plan_id=_uid(900),
        revision=1,
        snapshot_version=snapshot,
        status=status,
        blocks=blocks,
        unmet_demands=unmet or [],
        diff=diff
        or ScheduleProposal.PlanDiff(
            added=[], moved=[], removed=[], deficit_minutes=0
        ),
        validation=ScheduleProposal.PlanValidation(
            passed=True,
            verifier_id="fabricado",
            checked_at=_utc(D0, 6 * 60),
            issues=[],
        ),
        objective="fabricado",
        explanation="proposta fabricada para exercitar o verificador",
    )


def _block(n_block: int, n_demand: int, start: int, end: int):
    return ScheduleProposal.PlanBlock(
        block_id=_uid(n_block),
        demand_id=_uid(n_demand),
        start_utc=_utc(D0, start),
        end_utc=_utc(D0, end),
        uid=_uid(n_block + 500),
    )


def test_v1_verificador_aprova_proposta_valida_do_solver():
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1, mandatory=True),),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    result = _solve(problem)
    validation = verify_schedule(
        problem, result.proposal, clock=lambda: _utc(D0, 6 * 60)
    )
    assert validation.passed is True
    assert validation.issues == []
    assert validation.verifier_id == "schedule_verifier_v1"


def test_v2_violacao_somente_visivel_fora_da_matriz():
    # Duração original de 20 min reserva 2 slots; uma checagem que só conta
    # slots livres veria 2 slots disponíveis e aprovaria. O verificador
    # independente reaplica a regra nos instantes originais (§9) e rejeita:
    # os instantes do bloco cobrem apenas 15 min.
    demand = _demand(1, duration=20, mandatory=True)
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(demand,),
        availability=(_window(D0, 8 * 60, 9 * 60),),
    )
    proposal = _fabricated([_block(11, 1, 8 * 60, 8 * 60 + 15)])
    validation = verify_schedule(
        problem, proposal, clock=lambda: _utc(D0, 6 * 60)
    )
    assert validation.passed is False
    assert any("duração reduzida" in issue for issue in validation.issues)


def test_v3_sobreposicao_de_blocos_rejeitada():
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1), _demand(2)),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    proposal = _fabricated(
        [
            _block(11, 1, 10 * 60, 10 * 60 + 30),
            _block(12, 2, 10 * 60 + 15, 10 * 60 + 45),
        ]
    )
    validation = verify_schedule(
        problem, proposal, clock=lambda: _utc(D0, 6 * 60)
    )
    assert validation.passed is False
    assert any("conflito" in issue for issue in validation.issues)


def test_v4_snapshot_divergente_rejeitado():
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=7,
        demands=(_demand(1, mandatory=True),),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    result = _solve(problem)
    stale = result.proposal.model_copy(update={"snapshot_version": 6})
    validation = verify_schedule(
        problem, stale, clock=lambda: _utc(D0, 6 * 60)
    )
    assert validation.passed is False
    assert any("snapshot" in issue for issue in validation.issues)


def test_v5_obrigatoria_ausente_rejeitada():
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1, mandatory=True),),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    proposal = _fabricated([])
    validation = verify_schedule(
        problem, proposal, clock=lambda: _utc(D0, 6 * 60)
    )
    assert validation.passed is False
    assert any("obrigatória" in issue for issue in validation.issues)


def test_v6_diff_inconsistente_com_identidade_rejeitado():
    demand = _demand(1, occurrence_id=_uid(101))
    existing = ExistingOccurrence(
        occurrence_id=_uid(101),
        block_id=_uid(201),
        demand_id=demand.demand_id,
        start_utc=_utc(D0, 9 * 60),
        end_utc=_utc(D0, 9 * 60 + 30),
    )
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(demand,),
        availability=(_window(D0, 8 * 60, 12 * 60),),
        existing=(existing,),
    )
    # Mesma identidade com instantes diferentes, mas diff alega nada movido.
    proposal = _fabricated([_block(201, 1, 10 * 60, 10 * 60 + 30)])
    validation = verify_schedule(
        problem, proposal, clock=lambda: _utc(D0, 6 * 60)
    )
    assert validation.passed is False
    assert any("diff" in issue for issue in validation.issues)


def test_v7_status_sem_solucao_nao_publica_blocos():
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1, mandatory=True),),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    proposal = _fabricated(
        [_block(11, 1, 8 * 60, 8 * 60 + 30)],
        status=ScheduleProposal.SolverStatus.UNKNOWN,
    )
    validation = verify_schedule(
        problem, proposal, clock=lambda: _utc(D0, 6 * 60)
    )
    assert validation.passed is False
    assert any("relaxação" in issue for issue in validation.issues)


def test_v8_preview_diff_por_identidade_de_ocorrencia():
    existing_demand = _demand(1, occurrence_id=_uid(101))
    existing = ExistingOccurrence(
        occurrence_id=_uid(101),
        block_id=_uid(201),
        demand_id=existing_demand.demand_id,
        start_utc=_utc(D0, 9 * 60),
        end_utc=_utc(D0, 9 * 60 + 30),
    )
    new_demand = _demand(2)
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=2,
        demands=(existing_demand, new_demand),
        availability=(
            _window(D0, 10 * 60, 12 * 60),  # 09:00 deixou de estar disponível
        ),
        existing=(existing,),
    )
    result = _solve(problem)
    diff = result.proposal.diff
    assert diff.moved == [_uid(201)]  # mesma identidade, novo horário
    assert len(diff.added) == 1  # ocorrência nova para a demanda 2
    assert diff.removed == []
    assert diff.deficit_minutes == 0
    validation = verify_schedule(
        problem, result.proposal, clock=lambda: _utc(D0, 6 * 60)
    )
    assert validation.passed is True


# ---------------------------------------------------------------------------
# C4 — defaults da config e permissão da ferramenta
# ---------------------------------------------------------------------------


def test_k1_config_default_alimenta_settings(tmp_path: Path):
    settings = load_solver_settings()
    assert settings == SolverSettings(
        solver_budget_s=10.0,
        slot_minutes=15,
        horizon_days=7,
        seed=0,
        num_workers=1,
    )
    yaml_text = (
        "solver_budget_s: 3\n"
        "slot_minutes: 30\n"
        "horizon_days: 5\n"
        "seed: 2\n"
        "num_workers: 1\n"
    )
    custom = tmp_path / "default.yaml"
    custom.write_text(yaml_text, encoding="utf-8")
    loaded = load_solver_settings(custom)
    assert loaded == SolverSettings(
        solver_budget_s=3.0,
        slot_minutes=30,
        horizon_days=5,
        seed=2,
        num_workers=1,
    )
    assert SolverSettings.from_mapping({"solver_budget_s": 1, "seed": 4}) == (
        SolverSettings(
            solver_budget_s=1.0, slot_minutes=15, horizon_days=7, seed=4,
            num_workers=1,
        )
    )
    # Arquivo ausente → defaults de ensaio espelhando config/default.yaml.
    assert load_solver_settings(tmp_path / "ausente.yaml") == SolverSettings()


def test_k2_slot_e_horizonte_da_config_governam_o_solve():
    # slot_minutes=30: duração de 45 min reserva ceil(45/30)*30 = 60 min.
    demand = _demand(1, duration=45, mandatory=True)
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(demand,),
        availability=(_window(D0, 8 * 60, 10 * 60),),
    )
    result = _solve(problem, settings=SolverSettings(slot_minutes=30))
    block = result.proposal.blocks[0]
    assert (block.end_utc - block.start_utc) == timedelta(minutes=60)

    # horizon_days=2: janela no 3º dia fica fora do horizonte.
    outside = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(2),),
        availability=(_window(D0 + timedelta(days=2), 8 * 60, 9 * 60),),
    )
    result_outside = _solve(
        outside, settings=SolverSettings(solver_budget_s=1.0, horizon_days=2)
    )
    assert result_outside.proposal.blocks == []
    assert result_outside.proposal.diff.deficit_minutes == 30


def test_r1_schedule_solve_so_pelo_planejador():
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(_demand(1),),
        availability=(_window(D0, 8 * 60, 12 * 60),),
    )
    with pytest.raises(EduAgentError) as exc:
        solve_schedule(
            problem,
            sender_role=SenderRole.MONITOR,
            settings=SolverSettings(solver_budget_s=1.0),
        )
    assert exc.value.code is ErrorCode.TOOL_DENIED
    with pytest.raises(EduAgentError) as exc_curator:
        solve_schedule(
            problem,
            sender_role=SenderRole.CURATOR,
            settings=SolverSettings(solver_budget_s=1.0),
        )
    assert exc_curator.value.code is ErrorCode.TOOL_DENIED


# ---------------------------------------------------------------------------
# Correção 012a — janelas adjacentes/sobrepostas (§9/§15.5) e identidade do
# diff. Decisão de semântica (a): o verificador valida cobertura pela união
# das janelas do dia — a mesma semântica da grade (``_usable_slots``) e do
# enumerador (runs contíguos sobre a união). INTERNAL_FAILURE é reservado a
# contradição interna genuína (§15.5), nunca a entrada confirmada legítima.
# ---------------------------------------------------------------------------


def test_j1_janelas_adjacentes_nao_geram_internal_failure():
    # Sonda da revisão da 012 (achado A1): janelas adjacentes 8:15–9:15 e
    # 9:15–10:15 com obrigatória de 90 min. Antes da correção, o
    # verificador exigia contenção em janela única e ``schedule.solve``
    # devolvia INTERNAL_FAILURE para entrada confirmada legítima.
    demand = _demand(1, duration=90, mandatory=True)
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(demand,),
        availability=(
            _window(D0, 8 * 60 + 15, 9 * 60 + 15),
            _window(D0, 9 * 60 + 15, 10 * 60 + 15),
        ),
    )
    result = _solve(problem)
    assert result.proposal.status in (
        ScheduleProposal.SolverStatus.OPTIMAL,
        ScheduleProposal.SolverStatus.FEASIBLE,
    )
    block = result.proposal.blocks[0]
    # Bloco dentro da união das janelas do dia (8:15–10:15), contíguo.
    assert block.start_utc >= _utc(D0, 8 * 60 + 15)
    assert block.end_utc <= _utc(D0, 10 * 60 + 15)
    assert (block.end_utc - block.start_utc) == timedelta(minutes=90)
    validation = verify_schedule(
        problem, result.proposal, clock=lambda: _utc(D0, 6 * 60)
    )
    assert validation.passed is True
    assert validation.issues == []


def test_j2_janelas_sobrepostas_uniao_cobre_emenda():
    # Janelas sobrepostas 8:00–9:00 e 8:30–9:45: nenhuma janela única cabe
    # em 90 min (60 e 75 min), então toda solução viável cruza a emenda —
    # enumerador (runs sobre a união) e verificador (união dos minutos
    # originais) precisam concordar.
    demand = _demand(1, duration=90, mandatory=True)
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(demand,),
        availability=(
            _window(D0, 8 * 60, 9 * 60),
            _window(D0, 8 * 60 + 30, 9 * 60 + 45),
        ),
    )
    result = _solve(problem)
    assert result.proposal.status in (
        ScheduleProposal.SolverStatus.OPTIMAL,
        ScheduleProposal.SolverStatus.FEASIBLE,
    )
    block = result.proposal.blocks[0]
    assert block.start_utc >= _utc(D0, 8 * 60)
    assert block.end_utc <= _utc(D0, 9 * 60 + 45)
    # O bloco cruza a emenda 9:00: não está contido em nenhuma janela única.
    assert block.start_utc < _utc(D0, 9 * 60) < block.end_utc
    validation = verify_schedule(
        problem, result.proposal, clock=lambda: _utc(D0, 6 * 60)
    )
    assert validation.passed is True
    assert validation.issues == []


def test_j3_verificador_valida_uniao_e_rejeita_vao_entre_janelas():
    # Emenda adjacente: bloco 8:15–10:15 (120 min) coberto pela união das
    # janelas 8:15–9:15 e 9:15–10:15 é aceito pelo verificador…
    adjacent_demand = _demand(1, duration=120, mandatory=True)
    adjacent_problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(adjacent_demand,),
        availability=(
            _window(D0, 8 * 60 + 15, 9 * 60 + 15),
            _window(D0, 9 * 60 + 15, 10 * 60 + 15),
        ),
    )
    proposal = _fabricated(
        [_block(11, 1, 8 * 60 + 15, 10 * 60 + 15)],
        diff=ScheduleProposal.PlanDiff(
            added=[str(_uid(11))], moved=[], removed=[], deficit_minutes=0
        ),
    )
    validation = verify_schedule(
        adjacent_problem, proposal, clock=lambda: _utc(D0, 6 * 60)
    )
    assert validation.passed is True
    assert validation.issues == []

    # …mas o vão entre janelas disjuntas (9:00–10:00) não é cobertura:
    # bloqueios para fora (§9) continuam valendo no verificador.
    gap_demand = _demand(2, duration=180, mandatory=True)
    gap_problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=1,
        demands=(gap_demand,),
        availability=(
            _window(D0, 8 * 60, 9 * 60),
            _window(D0, 10 * 60, 11 * 60),
        ),
    )
    gap_proposal = _fabricated(
        [_block(12, 2, 8 * 60, 11 * 60)],
        diff=ScheduleProposal.PlanDiff(
            added=[str(_uid(12))], moved=[], removed=[], deficit_minutes=0
        ),
    )
    gap_validation = verify_schedule(
        gap_problem, gap_proposal, clock=lambda: _utc(D0, 6 * 60)
    )
    assert gap_validation.passed is False
    assert any(
        "fora das janelas de disponibilidade" in issue
        for issue in gap_validation.issues
    )


def test_j4_identidade_do_diff_preservada_e_sem_colisao_de_ocorrencias():
    # Preview (diff) e proposta compartilham a identidade (§15.5): movida
    # mantém block_id/uid; ocorrências distintas nunca colidem na mesma
    # identidade (block/uid derivados de occurrence_ids distintos).
    moved_demand = _demand(1, occurrence_id=_uid(101))
    existing = ExistingOccurrence(
        occurrence_id=_uid(101),
        block_id=_uid(201),
        demand_id=moved_demand.demand_id,
        start_utc=_utc(D0, 9 * 60),
        end_utc=_utc(D0, 9 * 60 + 30),
        uid=_uid(301),
    )
    added_demand = _demand(2)
    problem = SchedulingProblem(
        user_id="u",
        horizon_start=D0,
        local_timezone=None,
        snapshot_version=2,
        demands=(moved_demand, added_demand),
        availability=(
            _window(D0, 10 * 60, 12 * 60),  # 09:00 deixou de estar disponível
        ),
        existing=(existing,),
    )
    result = _solve(problem)
    proposal = result.proposal
    blocks_by_id = {str(b.block_id): b for b in proposal.blocks}
    # A movida do preview é a mesma identidade na proposta, com uid preservado.
    assert proposal.diff.moved == [_uid(201)]
    moved_block = blocks_by_id[str(_uid(201))]
    assert moved_block.uid == _uid(301)
    assert moved_block.start_utc == _utc(D0, 10 * 60)  # mudou de horário
    # Adição separada, sem colisão com a movida.
    assert len(proposal.diff.added) == 1
    assert set(proposal.diff.added).isdisjoint(proposal.diff.moved)
    # Duas ocorrências distintas nunca colidem na mesma identidade.
    identities = [(b.block_id, b.uid) for b in proposal.blocks]
    assert len(identities) == len(set(identities)) == 2
    assert len({b.uid for b in proposal.blocks}) == 2
    # Derivação determinística: mesma ocorrência gera block_id e uid
    # distintos entre si; ocorrências distintas geram identidades distintas.
    first = sched._mint_identity(added_demand, None)
    second = sched._mint_identity(_demand(3), None)
    assert first[1] != first[2]  # block|occ ≠ uid|occ
    assert (first[1], first[2]) != (second[1], second[2])
    validation = verify_schedule(
        problem, proposal, clock=lambda: _utc(D0, 6 * 60)
    )
    assert validation.passed is True
