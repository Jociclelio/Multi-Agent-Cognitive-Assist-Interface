"""Testes de aceite da task 003 — contratos Pydantic, envelope, estado do
grafo e erros tipados (mapa §4).

Não é a suíte quantitativa da etapa 8 (mapa de testes): são testes locais de
curta duração que verificam os critérios C1–C4 da task.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from eduagent import contracts as C

UID = "123e4567-e89b-12d3-a456-426614174000"
UID2 = "223e4567-e89b-12d3-a456-426614174000"
HASH = "ab" * 32
NOW = datetime(2026, 10, 21, 12, 0, 0, tzinfo=timezone.utc)


def _source_ref(**over):
    base = dict(
        doc_id=UID,
        version_id=UID2,
        physical_page=3,
        block_id="b7",
        offsets=(0, 10),
        text_hash=HASH,
    )
    base.update(over)
    return C.SourceRef(**base)


def _fact(**over):
    base = dict(
        entity_id=UID,
        kind="date",
        original_expression="em 25/10/2026",
        normalized_value="2026-10-25",
        precision="day",
        source_refs=[_source_ref()],
        status="candidate",
        authority="document",
    )
    base.update(over)
    return C.AcademicFact(**base)


def _ref(prefix="artifact", uid=UID, version=1):
    return C.Ref(kind=prefix, id=uid, version=version)


def _topic_state(**over):
    base = dict(
        topic_id=UID,
        status="insufficient",
        model_version="deterministic-reducer-v0",
        revision=0,
    )
    base.update(over)
    return C.TopicState(**base)


# ---------------------------------------------------------------------------
# C1 — 11 tipos da tabela §4: round-trip e rejeição de extra fields
# ---------------------------------------------------------------------------


def test_all_eleven_artifact_types_exist():
    expected = {
        "SourceRef",
        "AcademicFact",
        "EvidencePack",
        "MemoryPack",
        "LearningItem",
        "TutorTurn",
        "Assessment",
        "TopicState",
        "StudyDemand",
        "ScheduleProposal",
        "Operation",
    }
    assert {m.__name__ for m in C.ALL_CONTRACT_MODELS[:11]} == expected
    assert set(C.ArtifactType) == expected


def test_strict_extra_forbid_every_contract_model():
    for model in C.ALL_CONTRACT_MODELS:
        assert model.model_config.get("extra") == "forbid", model.__name__


def test_round_trip_artifacts():
    sr = _source_ref()
    fact = _fact(status="confirmed", authority="user_confirmed")
    pack = C.EvidencePack(
        query="teorema de Pitágoras",
        topic_ids=[UID],
        chunks=[
            C.EvidencePack.Chunk(
                id=UID, text="bloco de texto", source_ref=sr, rank=1
            )
        ],
        retrieval_config_hash=HASH,
        coverage="partial",
    )
    memory = C.MemoryPack(
        snapshot_version=12,
        current_facts=[fact],
        topic_state=[_topic_state()],
        events=[
            C.MemoryPack.EventRecord(
                id=UID,
                occurred_at=NOW,
                recorded_at=NOW,
                kind="attempt",
                help_level=0,
                source="observed",
            )
        ],
        contradictions=[
            C.MemoryPack.Contradiction(
                entity_id=UID, records=[_fact(), _fact(precision="year")]
            )
        ],
        summaries=[
            C.MemoryPack.SummaryEntry(
                id=UID,
                source_event_ids=[UID],
                claims=["afirmação verificada"],
                verification="verified",
                revision=1,
            )
        ],
    )
    item = C.LearningItem(
        item_id=UID,
        family_id=UID2,
        version=1,
        topic_ids=[UID],
        prompt="Qual é a hipotenusa?",
        expected_answer_ref=_ref("answer"),
        rubric_ref=_ref("rubric"),
        source_refs=[sr],
        kind="quiz",
        published_at=NOW,
    )
    turn = C.TutorTurn(
        skill_id="graduated_hint",
        skill_version=1,
        objective="hint",
        text="Pense no conceito de catetos.",
        item_ref=_ref("item"),
        hint_level=1,
        citations=[f"doc:{UID}@2:p3:b7"],
        next_state="attempt",
        terminal="waiting_student",
    )
    assessment = C.Assessment(
        attempt_id=UID,
        item_ref=_ref("item"),
        assessment_revision=1,
        criterion_results=[
            C.Assessment.CriterionResult(
                criterion_id="c1",
                topic_ids=[UID],
                level=2,
                evidence_kind="present",
                response_span=(0, 18),
                reason="resposta cobre o critério",
            )
        ],
        correctness="correct",
        help_level=0,
        revealed=False,
        evidence_ids=[UID],
        reliability="accepted",
        reason="avaliação por critérios",
    )
    demand = C.StudyDemand(
        demand_id=UID,
        topic_ids=[UID],
        kind="review",
        duration_minutes=15,
        earliest=NOW,
        deadline="2026-10-25",
        mandatory=False,
        dependencies=[_ref("demand", UID2)],
        priority_class=3,
        evidence_ids=[UID],
        duration_status="estimated",
    )
    proposal = C.ScheduleProposal(
        plan_id=UID,
        revision=1,
        snapshot_version=12,
        status="FEASIBLE",
        blocks=[
            C.ScheduleProposal.PlanBlock(
                block_id=UID,
                demand_id=UID2,
                start_utc=NOW,
                end_utc=NOW + timedelta(minutes=15),
                uid=UID,
            )
        ],
        unmet_demands=[],
        diff=C.ScheduleProposal.PlanDiff(
            added=[UID], moved=[], removed=[], deficit_minutes=0
        ),
        validation=C.ScheduleProposal.PlanValidation(
            passed=True,
            verifier_id="independent-check-v0",
            checked_at=NOW,
            issues=[],
        ),
        objective="maximizar opcionais classe 1",
        bound=1.0,
        explanation="grade viável",
    )
    operation = C.Operation(
        operation_id=UID,
        user_id=UID2,
        action="fact.upsert",
        expected_version=12,
        payload_hash=HASH,
        confirmation_ref=None,
        state="committed",
        receipt_ref=_ref("receipt", UID2),
    )
    envelope = C.Envelope(
        task_id=UID,
        trace_id=UID2,
        parent_task_id=None,
        sender_role="curator",
        artifact_type="EvidencePack",
        snapshot_version=12,
        source_refs=[f"doc:{UID}@2:p3:b7"],
        payload_ref=_ref(),
        status="completed",
        error=None,
    )
    artifacts = [sr, fact, pack, memory, item, turn, assessment, demand,
                 proposal, operation, envelope, _topic_state()]
    for artifact in artifacts:
        dump = json.loads(artifact.model_dump_json())
        again = type(artifact).model_validate(dump)
        assert again == artifact, type(artifact).__name__


@pytest.mark.parametrize("model", C.ALL_CONTRACT_MODELS)
def test_extra_field_rejected(model):
    sample = _minimal_payload(model)
    sample["campo_intruso"] = "x"
    with pytest.raises(Exception):
        model.model_validate(sample)


def _minimal_payload(model):
    """Payload mínimo válido por modelo, para testar extra='forbid'."""
    if model is C.SourceRef:
        return dict(doc_id=UID, version_id=UID2, physical_page=1,
                    block_id="b1", text_hash=HASH)
    if model is C.AcademicFact:
        return dict(entity_id=UID, kind="date",
                    original_expression="x", normalized_value="2026-10-25",
                    precision="day", status="candidate", authority="document")
    if model is C.EvidencePack:
        return dict(query="q", topic_ids=[UID], chunks=[],
                    retrieval_config_hash=HASH, coverage="none")
    if model is C.MemoryPack:
        return dict(snapshot_version=1)
    if model is C.LearningItem:
        return dict(item_id=UID, family_id=UID2, version=1, topic_ids=[UID],
                    prompt="p", expected_answer_ref=_ref(), rubric_ref=_ref(),
                    source_refs=[_source_ref()], kind="quiz",
                    published_at=NOW)
    if model is C.RubricCriterion:
        return dict(criterion_id="c1", topic_ids=[UID],
                    description="resposta usa a unidade correta",
                    critical=False)
    if model is C.TutorTurn:
        return dict(skill_id="explain", skill_version=1, objective="explain",
                    text="t", hint_level=0, next_state="close",
                    terminal="completed")
    if model is C.Assessment:
        return dict(attempt_id=UID, item_ref=_ref(), assessment_revision=1,
                    criterion_results=[dict(
                        criterion_id="c1", topic_ids=[UID], level=0,
                        evidence_kind="missing",
                        reason="critério ausente na resposta")],
                    correctness="undecidable", help_level=0, revealed=False,
                    evidence_ids=[], reliability="accepted", reason="r")
    if model is C.TopicState:
        return dict(topic_id=UID, status="insufficient",
                    model_version="deterministic-reducer-v0", revision=0)
    if model is C.StudyDemand:
        return dict(demand_id=UID, topic_ids=[UID], kind="practice",
                    duration_minutes=30, earliest=NOW, deadline="2026-10-30",
                    mandatory=False, priority_class=3,
                    duration_status="estimated")
    if model is C.ScheduleProposal:
        return dict(plan_id=UID, revision=1, snapshot_version=1,
                    status="UNKNOWN",
                    diff=dict(added=[], moved=[], removed=[], deficit_minutes=0),
                    validation=dict(passed=False, verifier_id="v0",
                                    checked_at=NOW, issues=[]),
                    objective="o", explanation="e")
    if model is C.Operation:
        return dict(operation_id=UID, user_id=UID2, action="event.append",
                    expected_version=0, payload_hash=HASH, state="pending")
    if model is C.TypedError:
        return dict(code="INTERNAL_FAILURE", message="m", retryable=False)
    if model is C.Envelope:
        return dict(task_id=UID, trace_id=UID2, sender_role="system",
                    artifact_type="Operation", snapshot_version=0,
                    payload_ref=_ref(), status="pending")
    if model is C.ToolRequest:
        return dict(tool="memory.query", sender_role="librarian")
    if model is C.GraphState:
        return dict(user_id=UID, session_id=UID2, turn_id=UID, trace_id=UID2,
                    intent="ask",
                    budgets=dict(llm_calls_remaining=1,
                                 tool_calls_remaining=1),
                    status="running")
    raise AssertionError(model.__name__)


# ---------------------------------------------------------------------------
# C1 — invariantes finas: datas ingênuas, datas parciais, *_ref com caminho
# ---------------------------------------------------------------------------


def test_naive_datetime_rejected():
    with pytest.raises(Exception, match="zona"):
        C.LearningItem(
            item_id=UID, family_id=UID2, version=1, topic_ids=[UID],
            prompt="p", expected_answer_ref=_ref(), rubric_ref=_ref(),
            source_refs=[_source_ref()], kind="quiz",
            published_at="2026-10-21T12:00:00",  # sem zona
        )


def test_utc_normalization():
    item_date = "2026-10-21T09:00:00-03:00"
    item = C.LearningItem(
        item_id=UID, family_id=UID2, version=1, topic_ids=[UID],
        prompt="p", expected_answer_ref=_ref(), rubric_ref=_ref(),
        source_refs=[_source_ref()], kind="quiz", published_at=item_date,
    )
    assert item.published_at.utcoffset() == timedelta(0)
    assert item.published_at.hour == 12


def test_partial_date_is_date_not_datetime():
    demand = C.StudyDemand(
        demand_id=UID, topic_ids=[UID], kind="review", duration_minutes=15,
        earliest=NOW, deadline="2026-10-25", mandatory=False,
        priority_class=3, duration_status="estimated",
    )
    assert isinstance(demand.deadline, date) and not isinstance(
        demand.deadline, datetime
    )
    # Instante com zona é aceito como datetime (UTC).
    demand2 = C.StudyDemand.model_validate(
        demand.model_dump(mode="json") | {"deadline": "2026-10-25T23:00:00-03:00"}
    )
    assert isinstance(demand2.deadline, datetime)
    # Ingênuo com hora é rejeitado (não há coerção para nada).
    with pytest.raises(Exception):
        C.StudyDemand.model_validate(
            demand.model_dump(mode="json") | {"deadline": "2026-10-25T10:00:00"}
        )


def test_review_due_is_partial_date_only():
    state = _topic_state(review_due="2026-10-28")
    assert state.review_due == date(2026, 10, 28)
    with pytest.raises(Exception, match="review_due"):
        _topic_state(review_due="2026-10-28T10:00:00Z")
    with pytest.raises(Exception, match="review_due"):
        _topic_state(review_due=datetime(2026, 10, 28, tzinfo=timezone.utc))


def test_estimate_must_be_none_in_mvp():
    assert _topic_state().estimate is None
    with pytest.raises(Exception):
        _topic_state(estimate=0.42)


def _study_demand(**over):
    base = dict(
        demand_id=UID,
        topic_ids=[UID],
        kind="practice",
        duration_minutes=30,
        earliest=NOW,
        deadline="2026-10-30",
        mandatory=False,
        priority_class=3,
        duration_status="estimated",
    )
    base.update(over)
    return C.StudyDemand(**base)


def test_mandatory_study_demand_requires_confirmed_duration():
    """A1/003a — mapa §4: "restrição dura exige confirmação"; §15.3:
    "rótulo estimated e mandatory=false. Usuário pode editar e confirmar
    para obrigatória"; §8: "não converter incerteza em obrigação".
    Demanda obrigatória só com duration_status='confirmed'."""
    # Aceitação: estimada e opcional; confirmada e obrigatória.
    C.StudyDemand.model_validate(_study_demand().model_dump())
    confirmed = C.StudyDemand.model_validate(
        _study_demand(mandatory=True, duration_status="confirmed").model_dump()
    )
    assert confirmed.duration_status is C.StudyDemand.DurationStatus.CONFIRMED
    # Rejeição: probe do revisor — mandatory=True com estimated é negado.
    with pytest.raises(Exception, match="confirmed"):
        _study_demand(mandatory=True, duration_status="estimated")


def test_topic_state_error_codes_restricted_to_typed_enum():
    """A2/003a — mapa §4: ``error_codes`` carrega os 12 códigos tipados;
    string arbitrária é rejeitada e o JSON Schema sai com ``enum`` fechado."""
    state = _topic_state(error_codes=["TIMEOUT", "NO_EVIDENCE"])
    assert set(state.error_codes) == {
        C.ErrorCode.TIMEOUT,
        C.ErrorCode.NO_EVIDENCE,
    }
    with pytest.raises(Exception):
        _topic_state(error_codes=["ERRO_INVENTADO"])
    schema = C.TopicState.model_json_schema(mode="validation")
    ref = schema["properties"]["error_codes"]["items"]["$ref"]
    def_name = ref.rsplit("/", 1)[-1]
    assert set(schema["$defs"][def_name]["enum"]) == {
        code.value for code in C.ErrorCode
    }


@pytest.mark.parametrize(
    "bad_ref",
    [
        "../../etc/passwd",
        "data/originals/arquivo.pdf",
        "artifact:123e4567-e89b-12d3-a456-426614174000@1/x",
        "artifact:123e4567-e89b-12d3-a456-426614174000@1/../../etc",
        "gadget:123e4567-e89b-12d3-a456-426614174000@1",
        "123e4567-e89b-12d3-a456-426614174000@0",
    ],
)
def test_ref_rejects_paths_and_bad_prefixes(bad_ref):
    with pytest.raises(Exception):
        C.Ref.model_validate(bad_ref)


def test_ref_accepts_id_version_forms():
    assert C.Ref.model_validate(f"{UID}@2").to_locator() == f"{UID}@2"
    assert C.Ref.model_validate(
        f"item:{UID}@3"
    ).to_locator() == f"item:{UID}@3"


def test_source_locator_citation_format():
    turn = C.TutorTurn(
        skill_id="explain", skill_version=1, objective="explain",
        text="t", hint_level=0, next_state="close", terminal="completed",
        citations=[f"doc:{UID}@2:p3:b7"],
    )
    assert turn.citations == [f"doc:{UID}@2:p3:b7"]
    with pytest.raises(Exception):
        C.TutorTurn.model_validate(
            turn.model_dump() | {"citations": ["doc/" + UID]}
        )


# ---------------------------------------------------------------------------
# Invariantes específicos por artefato
# ---------------------------------------------------------------------------


def test_confirmed_fact_requires_user_authority():
    with pytest.raises(Exception, match="confirmed"):
        _fact(status="confirmed", authority="document")
    _fact(status="confirmed", authority="user_direct")
    _fact(status="confirmed", authority="user_confirmed")


def test_evidence_pack_unique_ranks():
    sr = _source_ref()
    chunks = [
        C.EvidencePack.Chunk(id=UID, text="a", source_ref=sr, rank=1),
        C.EvidencePack.Chunk(id=UID2, text="b", source_ref=sr, rank=1),
    ]
    with pytest.raises(Exception, match="únicos"):
        C.EvidencePack(query="q", topic_ids=[UID], chunks=chunks,
                       retrieval_config_hash=HASH, coverage="partial")


def test_assessment_span_invariants():
    with pytest.raises(Exception, match="present"):
        C.Assessment.CriterionResult(
            criterion_id="c1", topic_ids=[UID], level=2,
            evidence_kind="present", reason="sem span",
        )
    with pytest.raises(Exception, match="missing"):
        C.Assessment.CriterionResult(
            criterion_id="c1", topic_ids=[UID], level=0,
            evidence_kind="missing", response_span=(0, 5),
            reason="critério ausente",
        )
    with pytest.raises(Exception, match="start <= end"):
        C.Assessment.CriterionResult(
            criterion_id="c1", topic_ids=[UID], level=0,
            evidence_kind="present", response_span=(5, 5 - 10),
            reason="span invertido",
        )


def test_tutor_hint_level_invariants():
    with pytest.raises(Exception, match="hint"):
        C.TutorTurn(skill_id="graduated_hint", skill_version=1,
                    objective="hint", text="t", hint_level=0,
                    next_state="attempt", terminal="waiting_student")
    with pytest.raises(Exception, match="hint"):
        C.TutorTurn(skill_id="explain", skill_version=1, objective="explain",
                    text="t", hint_level=2, next_state="close",
                    terminal="completed")


def test_plan_without_validation_not_publishable():
    base = dict(
        plan_id=UID, revision=1, snapshot_version=1,
        diff=dict(added=[], moved=[], removed=[], deficit_minutes=0),
        validation=dict(passed=False, verifier_id="v0", checked_at=NOW),
        objective="o", explanation="e",
    )
    with pytest.raises(Exception, match="validation"):
        C.ScheduleProposal(status="OPTIMAL", **base)
    with pytest.raises(Exception, match="validation"):
        C.ScheduleProposal(status="FEASIBLE", **base)
    # UNKNOWN/INFEASIBLE não publicam solução e não exigem passed=True.
    C.ScheduleProposal(status="UNKNOWN", **base)
    C.ScheduleProposal(status="INFEASIBLE", **base)


def test_operation_receipt_coupling():
    with pytest.raises(Exception, match="receipt_ref"):
        C.Operation(operation_id=UID, user_id=UID2, action="fact.upsert",
                    expected_version=0, payload_hash=HASH, state="committed")
    with pytest.raises(Exception, match="receipt_ref"):
        C.Operation(operation_id=UID, user_id=UID2, action="fact.upsert",
                    expected_version=0, payload_hash=HASH, state="pending",
                    receipt_ref=_ref("receipt", UID2))


def test_envelope_status_error_coupling():
    base = dict(task_id=UID, trace_id=UID2, sender_role="system",
                artifact_type="Operation", snapshot_version=0,
                payload_ref=_ref())
    with pytest.raises(Exception, match="failed"):
        C.Envelope(status="failed", **base)
    with pytest.raises(Exception, match="failed"):
        C.Envelope(
            status="completed",
            error=C.TypedError.of(C.ErrorCode.INTERNAL_FAILURE, "x"),
            **base,
        )


# ---------------------------------------------------------------------------
# C2 — envelope, estado do grafo e 12 erros tipados
# ---------------------------------------------------------------------------


def test_envelope_example_shape_from_map():
    """O envelope do mapa §4 (exemplo JSON) valida como contrato."""
    envelope = C.Envelope.model_validate(
        {
            "schema_version": "1.0",
            "task_id": UID,
            "trace_id": UID2,
            "parent_task_id": None,
            "sender_role": "curator",
            "artifact_type": "EvidencePack",
            "snapshot_version": 12,
            "source_refs": [f"doc:{UID}@2:p3:b7"],
            "payload_ref": f"artifact:{UID}@1",
            "status": "completed",
            "error": None,
        }
    )
    assert envelope.sender_role is C.SenderRole.CURATOR
    assert envelope.artifact_type is C.ArtifactType.EVIDENCE_PACK


def test_graph_state_fields_and_terminals():
    state = C.GraphState.model_validate(
        {
            "user_id": UID,
            "session_id": UID2,
            "turn_id": UID,
            "task_id": None,
            "trace_id": UID2,
            "intent": "submit_answer",
            "snapshot_version": 12,
            "artifact_refs": [f"item:{UID}@1"],
            "pending_question": None,
            "pending_item_ref": f"item:{UID}@1",
            "budgets": {"llm_calls_remaining": 2, "tool_calls_remaining": 1,
                        "tokens_remaining": None},
            "deadline": "2026-10-21T12:10:00Z",
            "cancel_requested": False,
            "status": "running",
            "errors": [],
        }
    )
    assert state.intent is C.Intent.SUBMIT_ANSWER
    assert state.artifact_refs[0].kind == "item"
    failed = state.model_dump() | {
        "status": "failed",
        "errors": [C.TypedError.of(C.ErrorCode.RESOURCE_LIMIT, "orçamento")],
    }
    C.GraphState.model_validate(failed)
    with pytest.raises(Exception, match="failed"):
        C.GraphState.model_validate(state.model_dump() | {"status": "failed"})
    with pytest.raises(Exception, match="CANCELLED"):
        C.GraphState.model_validate(
            state.model_dump() | {"status": "cancelled", "errors": []}
        )


def test_twelve_error_codes_with_retryability_and_diagnostics():
    codes = {code.value for code in C.ErrorCode}
    assert codes == {
        "SCHEMA_INVALID", "SOURCE_UNRESOLVED", "AMBIGUOUS_INPUT",
        "VERSION_CONFLICT", "TOOL_DENIED", "MODEL_NOT_ADMITTED",
        "NO_EVIDENCE", "RESOURCE_LIMIT", "TIMEOUT", "UNKNOWN_EFFECT",
        "CANCELLED", "INTERNAL_FAILURE",
    }
    assert len(codes) == 12
    for code in C.ErrorCode:
        error = C.TypedError.of(code, f"mensagem de teste ({code.value})")
        assert error.message
        assert isinstance(error.retryable, bool)
        assert error.diagnostic.startswith("eduagent/")
        assert C.RETRYABILITY[code] == error.retryable
        # Invariantes contratuais: UNKNOWN_EFFECT nunca retentável (§11).
    assert C.RETRYABILITY[C.ErrorCode.UNKNOWN_EFFECT] is False
    assert C.RETRYABILITY[C.ErrorCode.VERSION_CONFLICT] is True


def test_typed_error_exception():
    err = C.EduAgentError(C.ErrorCode.SOURCE_UNRESOLVED, "fonte não achada")
    assert err.retryable is False
    payload = err.to_dict()
    assert set(payload) == {"code", "message", "retryable", "diagnostic"}
    C.TypedError.model_validate(payload)


def test_numeric_and_boolean_strictness():
    """Pydantic estrito: bool não vira inteiro e string numérica não vira
    número (mapa §4/§14); strings ISO-8601 continuam aceitas nos tipos com
    conversão explícita (datetime com zona, UUID, data parcial)."""
    with pytest.raises(Exception):
        C.Budgets(llm_calls_remaining=True, tool_calls_remaining=1)
    with pytest.raises(Exception):
        C.Budgets(llm_calls_remaining="3", tool_calls_remaining=1)
    with pytest.raises(Exception):
        C.TypedError(code="SCHEMA_INVALID", message="m", retryable=1)


def test_payload_external_sender_role_does_not_grant_permission():
    """Payload externo não muda papel/permissões (mapa §4; achado F1/002).

    O ``sender_role`` que chega no payload é papel **ALEGADO**: a decisão de
    permissão é tomada contra o papel atribuído pelo dispatcher a partir do
    contexto autenticado local. Aqui um payload externo alegando papel
    privilegiado (``monitor``, permitido para ``assessment.check``) é
    avaliado contra o papel real do chamador (``tutor``) e negado. A garantia
    definitiva de descarte do papel alegado na fronteira é responsabilidade
    do dispatcher (task 014) — este contrato avalia só o papel recebido.
    """
    # Payload externo com papel alegado 'monitor' (privilegiado para a
    # ferramenta) é aceito como dado — quem decide é o dispatcher:
    external = C.ToolRequest.model_validate(
        {"tool": "assessment.check", "sender_role": "monitor"}
    )
    # Papel real atribuído pelo dispatcher (tutor) → negado, mesmo com o
    # payload alegando 'monitor':
    with pytest.raises(C.EduAgentError) as exc:
        C.validate_tool_request(external.tool, C.SenderRole.TUTOR)
    assert exc.value.code is C.ErrorCode.TOOL_DENIED
    # O papel legítimo da tabela §10, atribuído pelo dispatcher, passa:
    C.validate_tool_request(external.tool, C.SenderRole.MONITOR)
    C.validate_tool_request(C.ToolName.DOCUMENT_SEARCH, C.SenderRole.CURATOR)
    C.validate_tool_request(C.ToolName.DOCUMENT_SEARCH, C.SenderRole.TUTOR)
    C.validate_tool_request(C.ToolName.DOMAIN_COMMIT, C.SenderRole.SYSTEM)
    for tool, roles in C.TOOL_PERMISSIONS.items():
        assert roles, tool  # toda ferramenta tem ao menos um papel


# ---------------------------------------------------------------------------
# C3 — JSON Schemas exportados, regeneráveis e round-trip
# ---------------------------------------------------------------------------


def test_exported_schemas_match_regeneration(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    C.export_schemas("schemas")
    assert C.schemas_are_current("schemas")
    # Mutação simula schemas/ desatualizado em relação ao código.
    (tmp_path / "schemas" / "Envelope.schema.json").write_text("{}\n")
    assert not C.schemas_are_current("schemas")


def test_committed_schemas_are_current_in_repo():
    # schemas/ versionado no repositório deve estar sincronizado com o código.
    repo_root = Path(__file__).resolve().parents[1]
    assert C.schemas_are_current(repo_root / "schemas")


@pytest.mark.parametrize("model", C.ALL_CONTRACT_MODELS)
def test_json_schema_validates_valid_instance(model):
    schema = model.model_json_schema(mode="validation")
    validator = Draft202012Validator(schema)
    # Round-trip mínimo: payload válido → instância → JSON → valida no schema.
    instance = model.model_validate(_minimal_payload(model))
    errors = list(validator.iter_errors(json.loads(instance.model_dump_json())))
    assert errors == [], [e.message for e in errors]
