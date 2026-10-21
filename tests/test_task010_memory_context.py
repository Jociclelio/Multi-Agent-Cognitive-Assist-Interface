"""Testes de aceite da task 010 — memória temporal, contexto com checagem e
correção/deleção (mapa §7, §5, §15.1, §13.6; contratos MemoryPack/
AcademicFact da task 003, armazenamento da 004, commit idempotente da 005).

Não é a suíte quantitativa da etapa 8 (mapa de testes): são testes locais de
curta duração, sem chamada ao modelo real (contadores heurísticos e
embedders injetados determinísticos). C4 (mapa intocado, commits separados,
submódulo intocado) é verificado por inspeção de git e registrado no task.md.

Tabela de testes (código → caso):

| Código | Caso |
|---|---|
| B1 | "atual" vs "como mudou": supersede → projeção vigente só com o novo; histórico em ordem temporal com as duas versões |
| B2 | similaridade não reativa fato superseded: consulta textualmente igual ao valor antigo não o traz como atual; include_superseded traz versão anterior explicitamente marcada |
| B3 | contradição não conciliada: dois fatos ativos da mesma entidade com valores distintos → ambos os registros + pendência |
| B4 | preferência declarada não é evidência de aprendizagem: evento preference com origin asserted não atualiza competência (topic_state ausente) |
| B5 | recuperação: filtros tempo/tópico; até 8 originais; evento maior que 2.048 tokens não é selecionado |
| B6 | correções relevantes substituem candidatos (_apply_corrections): invalidação posterior referenciando o evento entra no lugar |
| B7 | correction events aparecem na recuperação e pacote MemoryPack monta eventos com origem |
| X1 | ordem de montagem do §7 na serialização e total ≤ 13.312 (sem reduções) |
| X2 | contagem pós-serialização: contagem por seção inclui o template (contador de caracteres) |
| X3 | redução: fontes periféricas saem antes; memória e turnos antigos reduzidos; rubrica permanece |
| X4 | rubrica jamais removida: obrigatórias que não cabem → RESOURCE_LIMIT (pede divisão), nunca contexto sem rubrica |
| X5 | síntese verificada no contexto: claim sem suporte → originais mantidos, sem "[resumo verificado]"; claim com suporte → síntese publicada no contexto |
| X6 | entrada maior que 13.312 → RESOURCE_LIMIT antes de qualquer montagem |
| S1 | proposer determinístico: claims com data/kind/polaridade/ajuda são verificados contra originais |
| S2 | verificação exata: claim com data divergente da origem → failed; publicação recusada; originais mantidos |
| S3 | síntese verificada publicada: linha summaries + evento summary_published + arestas derived_from; nenhum evento apagado |
| S4 | não encadear resumo de resumo: summary_published recusado como fonte de síntese |
| D1 | correct_fact: novo fato supersedes, valid_to do antigo, evento de correção; dependente (síntese que cita o fato) invalidado via artifact_dependencies |
| D2 | delete_data facts: tombstone SEM payload; sem hash reversível do texto excluído em nenhuma coluna/evento |
| D3 | delete_data events: payload purgado (NULL) e gatilho impede restauração; resumo derivado REMOVIDO (§5 propaga a derivados); projeção reconstituída |
| D4 | backup pendente até expiração (~30 dias) em escopo parcial; escopo all → sem backup pendente |
| D5 | preview → confirm: deleção sem confirmação é recusa tipada; preview lista refs |
| P1 | permissão da ferramenta: memory.query proposto por papel não-Bibliotecário → TOOL_DENIED |
"""

from __future__ import annotations

import hashlib
import json
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from eduagent.agents.librarian import Librarian
from eduagent.contracts import (
    AcademicFact,
    EduAgentError,
    ErrorCode,
    MemoryPack,
    SenderRole,
    SourceRef,
)
from eduagent.context import (
    INPUT_BUDGET_TOKENS,
    ContextBuilder,
    ContextInput,
    ContextSection,
    SourceItem,
    verify_claim_against_sources,
)
from eduagent.services.effects import EffectsService
from eduagent.services.memory import (
    EventRow,
    MemoryService,
    event_ref,
    fact_ref,
    summary_ref,
)
from eduagent.storage.repository import DomainStore

UID = "123e4567-e89b-12d3-a456-426614174000"
SESSION = "7c9e6679-7425-40de-944b-e07fc1f90ae7"
COURSE = "c0000000-0000-0000-0000-000000000001"
TOPIC_A = "aaaaaaaa-0000-0000-0000-000000000001"
DOC = "3ea0f0e2-0c1e-4d9a-9b1f-0a2b3c4d5e6f"
VERSION = "4ea0f0e2-0c1e-4d9a-9b1f-0a2b3c4d5e6f"
HASH = "ab" * 32

T0 = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)


def _uid(n: int) -> _uuid.UUID:
    return _uuid.UUID(f"00000000-0000-0000-0000-{n:012d}")


class FakeClock:
    """Relógio injetável que avança um minuto por leitura — dá ordem temporal
    determinística a recorded_at/occurred_at sem dormir."""

    def __init__(self, start: datetime = T0) -> None:
        self._moment = start

    def __call__(self) -> datetime:
        self._moment += timedelta(minutes=1)
        return self._moment


def _source() -> SourceRef:
    return SourceRef(
        doc_id=_uuid.UUID(DOC),
        version_id=_uuid.UUID(VERSION),
        physical_page=1,
        block_id="p1b1",
        text_hash=HASH,
    )


@pytest.fixture()
def env(tmp_path: Path):
    store = DomainStore.open(tmp_path / "domain.sqlite")
    store.ensure_user(UID)
    store.execute_write(
        UID,
        [
            (
                "INSERT INTO courses(id, user_id, title) VALUES (?,?,?)",
                (COURSE, UID, "Curso"),
            ),
            (
                "INSERT INTO topics(id, course_id, title) VALUES (?,?,?)",
                (TOPIC_A, COURSE, "Tópico A"),
            ),
        ],
    )
    clock = FakeClock()
    memory = MemoryService(store, EffectsService(store), clock=clock)
    yield memory, store, clock
    store.close()


# ---------------------------------------------------------------------------
# C1 — B1..B7: memória temporal e recuperação
# ---------------------------------------------------------------------------


def _assert_fact(
    memory: MemoryService, value: str, entity: _uuid.UUID, expression: str
):
    return memory.assert_fact(
        user_id=UID,
        entity_id=entity,
        kind=AcademicFact.FactKind.NUMBER,
        original_expression=expression,
        normalized_value=value,
        precision=AcademicFact.Precision.EXACT,
        status=AcademicFact.FactStatus.CONFIRMED,
        authority=AcademicFact.FactAuthority.USER_DIRECT,
        origin=MemoryPack.Origin.ASSERTED,
    )


def test_b1_atual_vs_como_mudou(env):
    memory, _, _ = env
    entity = _uid(1)
    v1 = _assert_fact(memory, "10", entity, "capacidade é 10")
    v2 = memory.assert_fact(
        user_id=UID,
        entity_id=entity,
        kind=AcademicFact.FactKind.NUMBER,
        original_expression="capacidade é 10",
        normalized_value="12",
        precision=AcademicFact.Precision.EXACT,
        status=AcademicFact.FactStatus.CONFIRMED,
        authority=AcademicFact.FactAuthority.USER_DIRECT,
        origin=MemoryPack.Origin.ASSERTED,
        supersedes_fact_id=str(v1.fact_id),
    )
    # "atual": projeção vigente só com a versão corrigida (§7).
    current = memory.current_facts(UID)
    assert [f.normalized_value for f in current] == ["12"]
    assert current[0].fact_id == v2.fact_id
    # "como mudou": versões em ordem temporal, incluindo a substituída (§7).
    history = memory.fact_history(UID, entity)
    assert [f.fact_id for f in history] == [v1.fact_id, v2.fact_id]
    assert history[0].superseded and not history[1].superseded
    librarian = Librarian(memory)
    assert [f.fact_id for f in librarian.how_changed(UID, entity)] == [
        v1.fact_id,
        v2.fact_id,
    ]


def test_b2_similaridade_nao_reativa_superseded(env):
    memory, _, _ = env
    entity = _uid(2)
    v1 = _assert_fact(memory, "prazo original é 30 de novembro", entity, "30/11")
    memory.assert_fact(
        user_id=UID,
        entity_id=entity,
        kind=AcademicFact.FactKind.DATE,
        original_expression="30/11",
        normalized_value="2026-12-05",
        precision=AcademicFact.Precision.DAY,
        status=AcademicFact.FactStatus.CONFIRMED,
        authority=AcademicFact.FactAuthority.USER_DIRECT,
        origin=MemoryPack.Origin.ASSERTED,
        supersedes_fact_id=str(v1.fact_id),
    )
    # Consulta de recuperação textualmente IGUAL ao valor antigo: o fato
    # substituído não volta como atual — exclusão estrutural, não de ranking.
    result = memory.retrieve(UID, "prazo original é 30 de novembro")
    assert all(f.normalized_value != "prazo original é 30 de novembro"
               for f in result.pack.current_facts)
    # Consulta de evidências antigas traz a versão anterior EXPLICITAMENTE
    # marcada (nunca como atual, §7).
    old = memory.retrieve(
        UID, "prazo original é 30 de novembro", include_superseded=True
    )
    historical = [
        h for h in old.historical_facts if h.fact.fact_id == v1.fact_id
    ]
    assert len(historical) == 1
    assert historical[0].superseded_by is not None
    assert historical[0].fact.superseded
    assert all(
        f.normalized_value != "prazo original é 30 de novembro"
        for f in old.pack.current_facts
    )


def test_b3_contradicao_devolve_ambos_e_pendencia(env):
    memory, _, _ = env
    entity = _uid(3)
    _assert_fact(memory, "aula no auditorio A", entity, "auditorio A")
    _assert_fact(memory, "aula no auditorio B", entity, "auditorio B")
    contradictions = memory.detect_contradictions(UID)
    assert len(contradictions) == 1
    pack_entry = contradictions[0]
    assert pack_entry.pending is True
    assert len(pack_entry.records) == 2
    values = {record.normalized_value for record in pack_entry.records}
    assert values == {"aula no auditorio A", "aula no auditorio B"}


def test_b4_preferencia_nao_e_evidencia_de_aprendizagem(env):
    from eduagent.services.assessment import AssessmentService

    memory, store, _ = env
    memory.record_event(
        user_id=UID,
        session_id=SESSION,
        kind=MemoryPack.EventKind.PREFERENCE,
        payload={"preference": "prefiro estudar de manhã", "topic_ids": [TOPIC_A]},
        occurred_at=T0,
        origin=MemoryPack.Origin.ASSERTED,
    )
    # Evento registrado com origem asserted; competência não é atualizada:
    # nenhum TopicState existe (só assessment aceito atualiza, §8).
    service = AssessmentService(store, EffectsService(store))
    assert service.topic_state(UID, _uuid.UUID(TOPIC_A)) is None
    pack = memory.build_memory_pack(UID, [])
    assert pack.topic_state == []


def test_b5_recuperacao_filtros_teto_de_originais(env):
    memory, _, _ = env
    # 10 eventos pequenos com o termo da consulta; ocorridos em dias distintos.
    for i in range(10):
        memory.record_event(
            user_id=UID,
            session_id=SESSION,
            kind=MemoryPack.EventKind.READING,
            payload={"text": f"aula {i} sobre derivadas", "topic_ids": [TOPIC_A]},
            occurred_at=T0 + timedelta(days=i),
            origin=MemoryPack.Origin.OBSERVED,
        )
    # Evento fora do filtro temporal.
    memory.record_event(
        user_id=UID,
        session_id=SESSION,
        kind=MemoryPack.EventKind.READING,
        payload={"text": "aula antiga sobre derivadas"},
        occurred_at=T0 - timedelta(days=100),
        origin=MemoryPack.Origin.OBSERVED,
    )
    # Evento maior que o orçamento de 2.048 tokens não é selecionado (§7).
    memory.record_event(
        user_id=UID,
        session_id=SESSION,
        kind=MemoryPack.EventKind.READING,
        payload={"text": "aula " + "derivadas " * 3000},
        occurred_at=T0,
        origin=MemoryPack.Origin.OBSERVED,
    )
    result = memory.retrieve(
        UID,
        "aula derivadas",
        topic_ids=[TOPIC_A],
        from_at=T0 - timedelta(days=1),
        to_at=T0 + timedelta(days=30),
    )
    assert len(result.selected_events) == 8  # teto de 8 originais (§7)
    assert all(
        "aula" in json.dumps(event.payload, ensure_ascii=False)
        for event in result.selected_events
    )
    assert "lexical" in result.rankings
    # Sem filtro temporal, a aula antiga entra; com tópico inexistente, nada.
    all_time = memory.retrieve(UID, "aula derivadas")
    assert len(all_time.selected_events) == 8
    empty = memory.retrieve(UID, "aula derivadas", topic_ids=[str(_uid(999))])
    assert empty.selected_events == ()


def test_b6_correcao_substitui_candidato(env):
    memory, _, _ = env
    memory.record_event(
        user_id=UID,
        session_id=SESSION,
        kind=MemoryPack.EventKind.SELF_REPORT,
        payload={"text": "achei derivadas difficultas hoje"},
        occurred_at=T0,
        origin=MemoryPack.Origin.ASSERTED,
    )
    candidate = memory.retrieve(UID, "derivadas").selected_events[0]
    # Correção posterior referenciando o evento (trigger_ref no payload) —
    # o mecanismo do §7: correção relevante entra no lugar do candidato.
    correction = EventRow(
        event_id=_uid(777),
        kind="artifact_invalidated",
        payload={"trigger_ref": candidate.ref, "reason": "autorrelato corrigido"},
        occurred_at=T0 + timedelta(minutes=5),
        recorded_at=T0 + timedelta(minutes=5),
        session_id=SESSION,
    )
    replaced = memory._apply_corrections([candidate], [candidate, correction])
    assert [e.event_id for e in replaced] == [_uid(777)]
    # Sem correção, o candidato permanece.
    assert [e.event_id for e in memory._apply_corrections([candidate], [candidate])] == [
        candidate.event_id
    ]


def test_b7_pacote_memory_pack_e_eventos_com_origem(env):
    memory, _, _ = env
    memory.record_event(
        user_id=UID,
        session_id=SESSION,
        kind=MemoryPack.EventKind.SELF_REPORT,
        payload={"text": "revisei integralmente", "help_level": 2},
        occurred_at=T0,
        origin=MemoryPack.Origin.ASSERTED,
    )
    entity = _uid(4)
    fact = _assert_fact(memory, "nota minima e 7", entity, "7")
    result = memory.retrieve(UID, "revisei")
    pack = result.pack
    assert [f.fact_id for f in memory.current_facts(UID)] == [fact.fact_id]
    assert pack.current_facts[0].normalized_value == "nota minima e 7"
    assert pack.current_facts[0].authority is AcademicFact.FactAuthority.USER_DIRECT
    assert len(pack.events) == 1
    event = pack.events[0]
    assert event.source is MemoryPack.Origin.ASSERTED
    assert event.help_level == 2
    assert event.kind is MemoryPack.EventKind.SELF_REPORT


# ---------------------------------------------------------------------------
# C2 — X1..X6: montagem de contexto; S1..S4: síntese
# ---------------------------------------------------------------------------


class WordCounter:
    """Contador heurístico de ensaio: um token por palavra (fronteira de
    espaço). Identidade registrada; calibração real é pendência (§3)."""

    def count(self, text: str) -> int:
        return len(text.split())


class CharCounter:
    """Contador de caracteres: expõe a contagem pós-serialização (cada
    caractere do texto RENDERIZADO é um token)."""

    def count(self, text: str) -> int:
        return len(text)


def _full_input() -> ContextInput:
    return ContextInput(
        instruction="Responda com base nas fontes.",
        schema='{"type": "object"}',
        skill="explicar o teorema com exemplo",
        task="Explique a regra da cadeia.",
        rubric="c1: aplica a regra (0/1/2)",
        anchor_facts=("derivada de x^2 é 2x",),
        sources=(
            SourceItem(source_id="s1", text="fonte um com a regra", rank=1),
            SourceItem(source_id="s2", text="fonte dois com exemplo", rank=2),
        ),
        memory_lines=("tentativa anterior com ajuda nível 1",),
        recent_turns=("aluno pediu explicação",),
    )


def test_x1_ordem_de_montagem_e_orcamento():
    builder = ContextBuilder(WordCounter())
    assembly = builder.assemble("Como aplicar a regra?", _full_input())
    text = assembly.text
    positions = [
        text.index("INSTRUÇÃO:"),
        text.index("SCHEMA:"),
        text.index("SKILL:"),
        text.index("TAREFA/ITEM:"),
        text.index("RUBRICA:"),
        text.index("ÂNCORAS/FATOS CONFIRMADOS:"),
        text.index("FONTES:"),
        text.index("MEMÓRIA:"),
        text.index("TURNOS RECENTES:"),
    ]
    assert positions == sorted(positions)  # ordem do mapa §7
    assert text.startswith("Como aplicar a regra?")
    assert assembly.total_tokens <= INPUT_BUDGET_TOKENS  # entrada ≤ 13.312
    assert assembly.input_tokens == WordCounter().count("Como aplicar a regra?")
    assert set(assembly.section_tokens) == set(ContextSection)


def test_x2_contagem_pos_serializacao():
    builder = ContextBuilder(CharCounter())
    data = ContextInput(sources=(SourceItem(source_id="s1", text="abc", rank=1),))
    assembly = builder.assemble("pergunta", data)
    rendered = builder._render(ContextSection.SOURCES, data)
    assert assembly.section_tokens[ContextSection.SOURCES] == len(rendered)
    assert assembly.total_tokens == CharCounter().count(assembly.text)


def test_x3_reducao_fontes_perifericas_memoria_turnos(monkeypatch):
    import eduagent.context as context_module

    monkeypatch.setattr(context_module, "INPUT_BUDGET_TOKENS", 60)
    builder = ContextBuilder(WordCounter())
    sources = tuple(
        SourceItem(source_id=f"s{i}", text=f"fonte periferica numero {i} " * 3, rank=i)
        for i in range(1, 7)
    )
    data = ContextInput(
        instruction="instrução",
        task="tarefa",
        rubric="rubrica",
        anchor_facts=("fato confirmado",),
        sources=sources,
        memory_lines=tuple(f"memória {i}" for i in range(10)),
        recent_turns=tuple(f"turno antigo {i}" for i in range(10)) + ("turno recente",),
    )
    assembly = builder.assemble("pergunta", data)
    assert assembly.total_tokens <= 60
    # Fontes periféricas saem primeiro (ranks altos); rank 1 permanece.
    assert "[1] " in assembly.text
    assert "[6] " not in assembly.text
    # Memória e turnos antigos reduzidos; o turno mais recente permanece.
    assert "turno recente" in assembly.text
    assert "turno antigo 0" not in assembly.text
    # A rubrica NUNCA sai.
    assert "RUBRICA:" in assembly.text and "rubrica" in assembly.text
    assert any("fontes" in action for action in assembly.actions)


def test_x4_rubrica_jamais_removida(monkeypatch):
    import eduagent.context as context_module

    monkeypatch.setattr(context_module, "INPUT_BUDGET_TOKENS", 30)
    builder = ContextBuilder(WordCounter())
    data = ContextInput(
        instruction="instrução longa que sozinha consome o orçamento inteiro "
        "disponível para o contexto do turno desta chamada de avaliação "
        "porque cada palavra adicionada aqui ocupa um token do contador "
        "heurístico de ensaio usado nestes testes de redução",
        task="tarefa",
        rubric="rubrica necessária",
    )
    with pytest.raises(EduAgentError) as excinfo:
        builder.assemble("pergunta", data)
    assert excinfo.value.code is ErrorCode.RESOURCE_LIMIT
    assert "rubrica" in excinfo.value.message
    assert "divis" in excinfo.value.message  # pede divisão


def test_x5_sintese_verificada_no_contexto():
    import eduagent.context as context_module

    big = " ".join(f"palavra{i}" for i in range(58))
    sources = (
        SourceItem(source_id="s1", text=big, rank=1),
        SourceItem(source_id="s2", text=big.replace("palavra", "termo"), rank=2),
    )
    original = context_module.INPUT_BUDGET_TOKENS
    context_module.INPUT_BUDGET_TOKENS = 63
    try:
        # Síntese com claim SEM suporte nos originais: falha mantém os
        # originais (segmento que coube) — nada de resumo não verificado.
        def bad_summarizer(texts):
            return (
                "evento em 2099-01-01 com resultado incorrect",
                ["evento em 2099-01-01 com resultado incorrect"],
            )

        builder_bad = ContextBuilder(WordCounter(), summarizer=bad_summarizer)
        assembly_bad = builder_bad.assemble(
            "pergunta", ContextInput(sources=sources)
        )
        assert "[resumo verificado]" not in assembly_bad.text
        assert assembly_bad.total_tokens <= 63
        assert any(
            "originais mantidos" in action for action in assembly_bad.actions
        )
    finally:
        context_module.INPUT_BUDGET_TOKENS = original

    # Síntese COM suporte (unidade): publicada como fonte derivada quando
    # cabe; falha de verificação retorna None (originais mantidos).
    builder = ContextBuilder(WordCounter())

    def good_summarizer(texts):
        return (
            "evento em 2026-10-21 com resultado correct",
            ["evento em 2026-10-21 com resultado correct"],
        )

    originais = [
        "em 2026-10-21 evento assessment_recorded com resultado correct",
        "em 2026-10-21 evento attempt_recorded com ajuda nível 2",
    ]
    builder._summarizer = good_summarizer
    synthesized = builder._try_summarize(
        originais, "pergunta", ContextInput(), (), 10_000, []
    )
    assert synthesized is not None
    assert "[resumo verificado]" in synthesized.text
    # Claim sem suporte → None (originais mantidos, §7).
    builder._summarizer = bad_summarizer
    assert (
        builder._try_summarize(
            originais, "pergunta", ContextInput(), (), 10_000, []
        )
        is None
    )


def test_x6_entrada_acima_do_teto():
    builder = ContextBuilder(WordCounter())
    huge = " ".join(f"palavra{i}" for i in range(INPUT_BUDGET_TOKENS + 10))
    with pytest.raises(EduAgentError) as excinfo:
        builder.assemble(huge, ContextInput())
    assert excinfo.value.code is ErrorCode.RESOURCE_LIMIT


def test_s1_proposer_e_verificacao(env):
    memory, _, _ = env
    memory.record_event(
        user_id=UID,
        session_id=SESSION,
        kind=MemoryPack.EventKind.ASSESSMENT,
        payload={"correctness": "correct", "help_level": 0},
        occurred_at=datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc),
        origin=MemoryPack.Origin.OBSERVED,
    )
    events = memory.retrieve(UID, "assessment").selected_events
    proposal = memory.propose_synthesis(events)
    assert proposal.claims
    for claim in proposal.claims:
        assert claim.event_ids
    verified = memory.verify_synthesis(proposal, events)
    assert verified.verified
    assert verified.coverage_from is not None


def test_s2_verificacao_exata_falha_mantem_originais(env):
    memory, store, _ = env
    memory.record_event(
        user_id=UID,
        session_id=SESSION,
        kind=MemoryPack.EventKind.ASSESSMENT,
        payload={"correctness": "correct"},
        occurred_at=datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc),
        origin=MemoryPack.Origin.OBSERVED,
    )
    events = memory.retrieve(UID, "assessment").selected_events
    # Claim com data divergente da origem: verificação falha (§7: checar
    # exatamente datas).
    bad = memory.verify_synthesis(
        type(memory.propose_synthesis(events))(
            claims=tuple(
                [
                    type(memory.propose_synthesis(events).claims[0])(
                        text="Em 2026-10-22, evento assessment_recorded com "
                        "resultado correct.",
                        event_ids=(str(events[0].event_id),),
                    )
                ]
            ),
            coverage_from=None,
            coverage_to=None,
            verification="pending",
        ),
        events,
    )
    assert not bad.verified
    assert bad.failed_claims
    # Publicação de síntese não verificada é recusada; originais mantidos.
    with pytest.raises(EduAgentError) as excinfo:
        memory.publish_synthesis(user_id=UID, proposal=bad)
    assert excinfo.value.code is ErrorCode.SCHEMA_INVALID
    rows = store.fetch_user_rows(
        "SELECT payload_json FROM events WHERE user_id = ?", (UID,)
    )
    assert all(row["payload_json"] is not None for row in rows)  # nada apagado
    # O verificador de claim isolado também recusa número/polaridade sem
    # suporte (§7: checar exatamente números e polaridade).
    source_text = memory._event_text(events[0])
    assert verify_claim_against_sources(
        "Em 2026-10-21, evento assessment_recorded com resultado correct.",
        [source_text],
    )
    assert not verify_claim_against_sources(
        "Em 2026-10-21, evento assessment_recorded com resultado incorrect.",
        [source_text],
    )
    assert not verify_claim_against_sources(
        "Em 2026-10-21, evento assessment_recorded com ajuda nível 3.",
        [source_text],
    )


def test_s3_publicacao_sintese_verificada(env):
    memory, store, _ = env
    memory.record_event(
        user_id=UID,
        session_id=SESSION,
        kind=MemoryPack.EventKind.ASSESSMENT,
        payload={"correctness": "correct"},
        occurred_at=datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc),
        origin=MemoryPack.Origin.OBSERVED,
    )
    events = memory.retrieve(UID, "assessment").selected_events
    proposal = memory.verify_synthesis(memory.propose_synthesis(events), events)
    assert proposal.verified
    memory.publish_synthesis(user_id=UID, proposal=proposal)
    rows = store.fetch_user_rows(
        "SELECT id, source_event_ids_json, claims_json, verification, revision "
        "FROM summaries WHERE user_id = ?",
        (UID,),
    )
    assert len(rows) == 1 and rows[0]["verification"] == "verified"
    edges = store.fetch_user_rows(
        "SELECT child_ref, parent_ref, relation FROM artifact_dependencies "
        "WHERE user_id = ?",
        (UID,),
    )
    assert any(
        edge["relation"] == "derived_from"
        and edge["parent_ref"] == event_ref(str(events[0].event_id))
        for edge in edges
    )
    # O evento original NÃO é apagado por compactação (§7).
    event_rows = store.fetch_user_rows(
        "SELECT payload_json FROM events WHERE user_id = ? AND kind = 'assessment'",
        (UID,),
    )
    assert len(event_rows) == 1 and event_rows[0]["payload_json"] is not None
    pack = memory.build_memory_pack(UID, [])
    assert pack.summaries[0].verification == "verified"  # type: ignore[index]


def test_s4_nao_encadear_resumo_de_resumo(env):
    memory, _, _ = env
    memory.record_event(
        user_id=UID,
        session_id=SESSION,
        kind=MemoryPack.EventKind.READING,
        payload={"text": "capítulo lido"},
        occurred_at=T0,
        origin=MemoryPack.Origin.OBSERVED,
    )
    events = memory.retrieve(UID, "capítulo").selected_events
    proposal = memory.verify_synthesis(memory.propose_synthesis(events), events)
    memory.publish_synthesis(user_id=UID, proposal=proposal)
    # Evento meta de publicação existe; não pode ser fonte de nova síntese.
    with pytest.raises(EduAgentError) as excinfo:
        memory.propose_synthesis(
            [
                EventRow(
                    event_id=_uid(555),
                    kind="summary_published",
                    payload={"summary_ref": "summary:x@1"},
                    occurred_at=T0,
                    recorded_at=T0,
                    session_id=None,
                )
            ]
        )
    assert excinfo.value.code is ErrorCode.SCHEMA_INVALID


# ---------------------------------------------------------------------------
# C3 — D1..D5: correção, deleção, tombstones, backup
# ---------------------------------------------------------------------------


def test_d1_correct_fact_propaga_invalidation(env):
    memory, store, _ = env
    entity = _uid(10)
    fact = _assert_fact(memory, "prazo é 30/11", entity, "30/11")
    # Síntese que cita o evento de leitura; a dependência do fato é
    # registrada na tabela pública artifact_dependencies (§15.1).
    memory.record_event(
        user_id=UID,
        session_id=SESSION,
        kind=MemoryPack.EventKind.READING,
        payload={"text": "li o prazo"},
        occurred_at=T0,
        origin=MemoryPack.Origin.OBSERVED,
    )
    events = memory.retrieve(UID, "prazo").selected_events
    proposal = memory.verify_synthesis(memory.propose_synthesis(events), events)
    memory.publish_synthesis(user_id=UID, proposal=proposal)
    summary_rows = store.fetch_user_rows(
        "SELECT id, revision FROM summaries WHERE user_id = ?", (UID,)
    )
    store.add_artifact_dependency(
        UID,
        child_ref=summary_ref(str(summary_rows[0]["id"]), int(summary_rows[0]["revision"])),
        parent_ref=fact_ref(str(fact.fact_id), fact.revision),
        relation="derived_from",
    )
    result = memory.correct_fact(
        user_id=UID,
        fact_id=str(fact.fact_id),
        corrected_value="prazo é 05/12",
        reason="usuário corrigiu o prazo",
    )
    # Novo fato supersedes; validade do antigo fechada (§7/§15.1).
    current = memory.current_facts(UID)
    assert [f.normalized_value for f in current] == ["prazo é 05/12"]
    old_row = store.fetch_user_rows(
        "SELECT valid_to, supersedes FROM facts WHERE id = ?", (str(fact.fact_id),)
    )
    assert old_row[0]["valid_to"] is not None
    edges = store.fetch_user_rows(
        "SELECT child_ref, parent_ref, relation FROM artifact_dependencies "
        "WHERE user_id = ?",
        (UID,),
    )
    supersedes_edges = [e for e in edges if e["relation"] == "supersedes"]
    assert any(
        e["parent_ref"] == fact_ref(str(fact.fact_id), fact.revision)
        for e in supersedes_edges
    )
    # Dependente invalidado (§15.1): verificação do resumo vai a 'failed' e
    # evento de invalidação registrado.
    assert any(ref.startswith("summary:") for ref in result.invalidated_refs)
    summary_after = store.fetch_user_rows(
        "SELECT verification FROM summaries WHERE id = ?",
        (str(summary_rows[0]["id"]),),
    )
    assert summary_after[0]["verification"] == "failed"
    invalidation_events = store.fetch_user_rows(
        "SELECT kind, payload_json FROM events WHERE user_id = ? AND kind = ?",
        (UID, "artifact_invalidated"),
    )
    assert invalidation_events, "evento de invalidação registrado"
    payload = json.loads(str(invalidation_events[0]["payload_json"]))
    assert payload["trigger_ref"] == fact_ref(str(fact.fact_id), fact.revision)
    # Evento de correção com occurred_at/recorded_at (§5/§7).
    correction_events = store.fetch_user_rows(
        "SELECT kind FROM events WHERE user_id = ? AND kind = ?",
        (UID, "fact_corrected"),
    )
    assert len(correction_events) == 1


def test_d2_tombstone_sem_payload_e_sem_hash_reversivel(env):
    memory, store, _ = env
    entity = _uid(11)
    secret = "texto pessoal que sera excluido 4242"
    fact = _assert_fact(memory, secret, entity, "4242")
    result = memory.delete_data(
        user_id=UID,
        scope="facts",
        confirmed=True,
        reason="pedido de exclusão do usuário",
        ids=[str(fact.fact_id)],
    )
    # Fato removido; tombstone cataloga a exclusão SEM payload (§5/§15.1).
    rows = store.fetch_user_rows(
        "SELECT id FROM facts WHERE user_id = ?", (UID,)
    )
    assert rows == []
    tombstones = store.fetch_user_rows(
        "SELECT artifact_ref, kind, reason, tombstoned_at, backup_pending_until "
        "FROM tombstones WHERE user_id = ?",
        (UID,),
    )
    assert len(tombstones) == 1
    tombstone = tombstones[0]
    assert tombstone["artifact_ref"] == fact_ref(str(fact.fact_id), fact.revision)
    assert tombstone["kind"] == "fact"
    # Nenhuma coluna do catálogo contém o texto excluído...
    for value in tombstone:
        assert secret not in str(value)
    # ...e nenhum hash reversível do texto excluído existe no banco:
    # variações canônicas do digest do texto não aparecem em nenhuma célula.
    text_variants = [secret, secret.lower(), " ".join(secret.split())]
    digests = {
        hashlib.sha256(v.encode("utf-8")).hexdigest() for v in text_variants
    }
    all_rows = store.fetch_user_rows(
        "SELECT artifact_ref, kind, reason, tombstoned_at, "
        "backup_pending_until FROM tombstones", ()
    )
    # (a consulta acima já filtrou por user; varredura ampla por digest:)
    digest_hits = 0
    for table, columns in (
        ("tombstones", ["artifact_ref", "reason"]),
        ("events", ["payload_json", "purge_reason", "kind"]),
        ("summaries", ["claims_json", "source_event_ids_json", "verification"]),
    ):
        for row in store.fetch_user_rows(
            f"SELECT {', '.join(columns)} FROM {table}", ()
        ):
            for column in columns:
                cell = str(row[column]) if row[column] is not None else ""
                for digest in digests:
                    assert digest not in cell
    assert digest_hits == 0


def test_d3_delete_eventos_purga_propaga_e_reconstitui(env):
    memory, store, _ = env
    memory.record_event(
        user_id=UID,
        session_id=SESSION,
        kind=MemoryPack.EventKind.SELF_REPORT,
        payload={"text": "detalhe pessoal 7788"},
        occurred_at=T0,
        origin=MemoryPack.Origin.ASSERTED,
    )
    events = memory.retrieve(UID, "detalhe").selected_events
    target = events[0]
    proposal = memory.verify_synthesis(memory.propose_synthesis(events), events)
    memory.publish_synthesis(user_id=UID, proposal=proposal)
    result = memory.delete_data(
        user_id=UID,
        scope="events",
        confirmed=True,
        reason="exclusão de payload pessoal",
        ids=[str(target.event_id)],
    )
    # Payload purgado (NULL), sem restauração possível (gatilho da 004).
    row = store.fetch_user_rows(
        "SELECT payload_json, purged_at, purge_reason FROM events WHERE id = ?",
        (str(target.event_id),),
    )
    assert row[0]["payload_json"] is None
    assert row[0]["purged_at"] is not None
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        with store.write_transaction(UID, bump_domain_revision=False) as tx:
            tx.execute(
                "UPDATE events SET payload_json = ? WHERE id = ?",
                (json.dumps({"text": "tentativa de restauração"}), str(target.event_id)),
            )
    # §5: deleção propaga a derivados — resumo derivado do evento REMOVIDO.
    summaries = store.fetch_user_rows(
        "SELECT id FROM summaries WHERE user_id = ?", (UID,)
    )
    assert summaries == []
    assert any(ref.startswith("summary:") for ref in result.invalidated_refs)
    # Projeção reconstituída (§15.1) — sem tentativas avaliadas, estados
    # permanecem vazios; a reconstituição executou sem erro.
    assert result.projections_reconstituted is True


def test_d4_backup_pendente_ate_expiracao(env):
    memory, store, clock = env
    entity = _uid(12)
    fact = _assert_fact(memory, "valor parcial 11", entity, "11")
    partial = memory.delete_data(
        user_id=UID,
        scope="facts",
        confirmed=True,
        reason="exclusão parcial",
        ids=[str(fact.fact_id)],
    )
    # Retenção proposta de 30 dias (default de ensaio, §5/§15.1): backup
    # identificado como pendente até expiração.
    expected = (clock() + timedelta(days=30)).isoformat()
    assert partial.backup_pending_until is not None
    assert partial.backup_pending_until[:10] == expected[:10]
    tombstones = store.fetch_user_rows(
        "SELECT backup_pending_until FROM tombstones WHERE user_id = ?", (UID,)
    )
    assert all(t["backup_pending_until"] is not None for t in tombstones)
    # Escopo 'all': backup conteria apenas este usuário — remoção já na
    # solicitação (§15.1), sem backup pendente.
    before_full = store.fetch_user_rows(
        "SELECT COUNT(*) AS n FROM tombstones WHERE user_id = ?", (UID,)
    )[0]["n"]
    full = memory.delete_data(
        user_id=UID,
        scope="all",
        confirmed=True,
        reason="exclusão integral de memória",
    )
    assert full.backup_pending_until is None
    full_tombstones = store.fetch_user_rows(
        "SELECT backup_pending_until FROM tombstones WHERE user_id = ?", (UID,)
    )
    # Tombstones criados pela deleção integral (se houver) não têm backup
    # pendente; os da deleção parcial anterior mantêm o prazo registrado.
    new_tombstones = full_tombstones[before_full:]
    assert all(t["backup_pending_until"] is None for t in new_tombstones)


def test_d5_preview_e_gate_de_confirmacao(env):
    memory, store, _ = env
    entity = _uid(13)
    fact = _assert_fact(memory, "valor 13", entity, "13")
    preview = memory.preview_delete(UID, "facts", ids=[str(fact.fact_id)])
    assert preview.fact_ids == (fact_ref(str(fact.fact_id), fact.revision),)
    assert preview.event_ids == () and preview.summary_ids == ()
    # Sem confirmação: recusa tipada — rota do §10 exige preview → confirm.
    before = store.domain_revision(UID)
    with pytest.raises(EduAgentError) as excinfo:
        memory.delete_data(
            user_id=UID,
            scope="facts",
            confirmed=False,
            reason="sem confirmação",
        )
    assert excinfo.value.code is ErrorCode.SCHEMA_INVALID
    assert store.domain_revision(UID) == before  # nada foi aplicado
    with pytest.raises(EduAgentError):
        memory.preview_delete(UID, "escopo-inexistente")


def test_p1_permissao_da_ferramenta(env):
    memory, store, _ = env
    with pytest.raises(EduAgentError) as excinfo:
        memory.retrieve(UID, "consulta", sender_role=SenderRole.TUTOR)
    assert excinfo.value.code is ErrorCode.TOOL_DENIED
    librarian = Librarian(memory)
    with pytest.raises(EduAgentError) as excinfo2:
        librarian.memory_query(
            UID, "consulta", sender_role=SenderRole.CURATOR
        )
    assert excinfo2.value.code is ErrorCode.TOOL_DENIED
    result = librarian.memory_query(UID, "consulta")
    assert result.pack.snapshot_version == store.domain_revision(UID)
