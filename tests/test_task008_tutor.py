"""Testes de aceite da task 008 — catálogo de skills YAML e máquina de
estados do Tutor (mapa §8, §13.5 parte 1; contratos TutorTurn/LearningItem da
task 003, adaptador da 002, commit idempotente da 005).

Não é a suíte quantitativa da etapa 8 (mapa de testes): são testes locais de
curta duração com o backend de geração injetado (FakeBackend determinístico;
nenhuma chamada ao modelo real). C4 (mapa intocado, commits separados,
submódulo intocado) é verificado por inspeção de git e registrado no task.md.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from eduagent.agents.tutor import (
    ChunkView,
    EventItemSink,
    StudentMove,
    Tutor,
    TutorConfig,
    TutorEvidence,
    TutorSession,
    new_session,
)
from eduagent.contracts import (
    EduAgentError,
    ErrorCode,
    LearningItem,
    SourceRef,
    TutorTurn,
)
from eduagent.services.effects import EffectsService
from eduagent.services.model_adapter import (
    ModelAdapterError,
    RuntimeCapabilities,
)
from eduagent.skills import SkillCatalog, SkillSpec, SkillSpecError, rehash
from eduagent.storage.repository import DomainStore

UID = "123e4567-e89b-12d3-a456-426614174000"
UID2 = "223e4567-e89b-12d3-a456-426614174001"
SESSION = "7c9e6679-7425-40de-944b-e07fc1f90ae7"
DOC_ID = "3ea0f0e2-0c1e-4d9a-9b1f-0a2b3c4d5e6f"
TOPIC = "4b9f5e34-1111-4d9a-9b1f-0a2b3c4d5e60"
HASH = "ab" * 32
CITATION = f"doc:{DOC_ID}@1:p1:b1"

FIXED_NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)

ITEM_PROMPT = (
    "Explique por que o commit idempotente confere operation_id antes de "
    "expected_version."
)
ITEM_ANSWER = (
    "Porque a dedup por operation_id garante que retries devolvam o recibo "
    "anterior sem repetir o efeito."
)
EXPLANATION = (
    f"A dedup vem antes ({CITATION}): retries devolvem o recibo anterior."
)
FLASHCARD = {
    "concept": "WAL no SQLite",
    "question": "O que o modo WAL muda na concorrência de escrita?",
    "verse": "Permite um escritor simultâneo aos leitores, com journal "
    "em arquivo separado.",
    "citations": [0],
}


# ---------------------------------------------------------------------------
# Fronteira injetável: backend de geração determinístico + recorder
# ---------------------------------------------------------------------------


class FakeBackend:
    """Backend determinístico (contrato do adaptador da task 002): devolve
    respostas roteirizadas e registra cada chamada."""

    def __init__(
        self,
        responses: list[str],
        *,
        json_schema_capability: bool = False,
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
        self.calls.append(
            {
                "messages": [dict(m) for m in messages],
                "schema": schema,
                "sampler": sampler,
                "deadline": deadline,
                "seed": seed,
            }
        )
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

    @property
    def last_messages(self) -> list[dict]:
        return self.calls[-1]["messages"]


class ListRecorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def record(self, kind: str, payload) -> None:
        self.events.append((kind, dict(payload)))


def item_payload() -> str:
    return json.dumps(
        {
            "prompt": ITEM_PROMPT,
            "expected_answer": ITEM_ANSWER,
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


def make_source() -> SourceRef:
    return SourceRef(
        doc_id=_uuid.UUID(DOC_ID),
        version_id=_uuid.UUID(DOC_ID),
        physical_page=1,
        block_id="b1",
        text_hash=HASH,
    )


def make_evidence(
    *,
    citations: tuple[str, ...] = (CITATION,),
    texts: tuple[str, ...] = ("O commit idempotente confere operation_id.",),
    topic_ids: tuple[str, ...] = (TOPIC,),
) -> TutorEvidence:
    assert len(citations) == len(texts)
    chunks = tuple(
        ChunkView(
            chunk_id=str(index),
            text=text,
            citation=citation,
            source_ref=make_source(),
        )
        for index, (citation, text) in enumerate(zip(citations, texts))
    )
    return TutorEvidence(
        chunks=chunks, coverage="supported", topic_ids=topic_ids
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path: Path) -> DomainStore:
    domain = DomainStore.open(tmp_path / "domain.sqlite")
    domain.ensure_user(UID)
    yield domain
    domain.close()


@pytest.fixture()
def sink(store: DomainStore) -> EventItemSink:
    return EventItemSink(
        store, EffectsService(store), clock=lambda: FIXED_NOW
    )


@pytest.fixture()
def recorder() -> ListRecorder:
    return ListRecorder()


def make_tutor(
    backend: FakeBackend,
    sink: EventItemSink | None,
    recorder: ListRecorder | None = None,
    config: TutorConfig | None = None,
) -> Tutor:
    return Tutor(
        backend,
        SkillCatalog.load(),
        item_sink=sink,
        config=config,
        recorder=recorder,
        clock=lambda: FIXED_NOW,
    )


def items_count(store: DomainStore, user_id: str = UID) -> int:
    row = store._conn.execute(
        "SELECT COUNT(*) AS n FROM items WHERE user_id = ?", (user_id,)
    ).fetchone()
    return int(row["n"])


# ---------------------------------------------------------------------------
# C1 — máquina de estados: um turno principal, terminais, sem insistência
# ---------------------------------------------------------------------------


class TestStateMachineC1:
    def test_ask_direct_gets_direct_explanation_and_completes(self, store):
        backend = FakeBackend([text_payload(EXPLANATION)])
        tutor = make_tutor(backend, sink=None)
        session = new_session(UID, SESSION)
        outcome = tutor.handle(
            session, StudentMove.ASK_DIRECT, "Por que dedup vem antes?",
            evidence=make_evidence(),
        )
        turn = outcome.turn
        # Um turno principal por chamada: exatamente 1 turno e 1 chamada.
        assert len(session.history) == 1
        assert len(backend.calls) == 1
        assert turn.objective is TutorTurn.TutorState.EXPLAIN
        assert turn.terminal is TutorTurn.Terminal.COMPLETED
        assert turn.next_state is TutorTurn.TutorState.CLOSE
        assert turn.skill_id == "explain"
        assert turn.hint_level == 0
        assert turn.citations == [CITATION]
        assert not outcome.general
        assert session.state is TutorTurn.TutorState.CLOSE

    def test_ask_direct_without_sources_is_labeled_general(self, store):
        backend = FakeBackend([text_payload("RRF funde rankings lexicais.")])
        tutor = make_tutor(backend, sink=None)
        session = new_session(UID, SESSION)
        outcome = tutor.handle(
            session, StudentMove.ASK_DIRECT, "O que é RRF?",
            evidence=TutorEvidence(),
        )
        assert outcome.general
        assert turn_citations(outcome) == []
        assert outcome.turn.text.startswith("[explicação geral, sem fonte documental]")

    def test_practice_publishes_item_and_waits_for_student(
        self, store, sink
    ):
        backend = FakeBackend([item_payload()])
        tutor = make_tutor(backend, sink)
        session = new_session(UID, SESSION)
        outcome = tutor.handle(
            session, StudentMove.PRACTICE, "Me dá um exercício de commit.",
            evidence=make_evidence(),
        )
        turn = outcome.turn
        assert turn.objective is TutorTurn.TutorState.ATTEMPT
        assert turn.terminal is TutorTurn.Terminal.WAITING_STUDENT
        assert turn.next_state is TutorTurn.TutorState.ATTEMPT
        assert turn.item_ref is not None
        assert outcome.item is not None
        assert outcome.item.prompt == ITEM_PROMPT
        assert items_count(store) == 1
        # Um turno principal: exatamente 1 chamada de geração.
        assert len(backend.calls) == 1

    def test_hint_levels_1_2_3_then_deterministic_offer(self, store, sink):
        backend = FakeBackend(
            [
                item_payload(),
                text_payload("Pense no que protege o recibo em retry."),
                text_payload("Qual linha confere o ID antes da versão?"),
                text_payload("Veja como um pagamento duplicado é tratado."),
            ]
        )
        tutor = make_tutor(backend, sink)
        session = new_session(UID, SESSION)
        tutor.handle(
            session, StudentMove.PRACTICE, "Prática, por favor.",
            evidence=make_evidence(),
        )
        calls_after_practice = len(backend.calls)
        for expected_level in (1, 2, 3):
            outcome = tutor.handle(
                session, StudentMove.REQUEST_HINT, "Mais ajuda."
            )
            assert outcome.turn.objective is TutorTurn.TutorState.HINT
            assert outcome.turn.hint_level == expected_level
            assert outcome.turn.terminal is TutorTurn.Terminal.WAITING_STUDENT
            assert outcome.turn.next_state is TutorTurn.TutorState.HINT
        # Após três pistas: oferta determinística SEM chamar o modelo.
        outcome = tutor.handle(session, StudentMove.REQUEST_HINT, "Outra?")
        assert len(backend.calls) == calls_after_practice + 3
        assert outcome.turn.objective is TutorTurn.TutorState.CLOSE
        assert outcome.turn.terminal is TutorTurn.Terminal.WAITING_STUDENT
        assert "solução comentada" in outcome.turn.text
        assert "encerrar" in outcome.turn.text

    def test_request_solution_reveals_records_and_closes_without_pushing(
        self, store, sink, recorder
    ):
        backend = FakeBackend(
            [item_payload(), text_payload("Solução comentada: a dedup vem antes...")]
        )
        tutor = make_tutor(backend, sink, recorder)
        session = new_session(UID, SESSION)
        outcome = tutor.handle(
            session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
        )
        family = outcome.item.family_id
        outcome = tutor.handle(
            session, StudentMove.REQUEST_SOLUTION, "Me dá a solução."
        )
        assert outcome.revealed
        assert outcome.solution_exposed_in_session
        assert session.closed
        assert session.revealed
        assert outcome.turn.terminal is TutorTurn.Terminal.COMPLETED
        assert outcome.turn.objective is TutorTurn.TutorState.CLOSE
        # Revelação explícita é registrada (mapa §8).
        kinds = [kind for kind, _payload in recorder.events]
        assert "tutor.reveal" in kinds
        reveal = dict(recorder.events[kinds.index("tutor.reveal")][1])
        assert reveal["family_id"] == str(family)
        assert reveal["kind"] == "explicit_request"

    def test_refuse_closes_without_insistence(self, store, sink, recorder):
        backend = FakeBackend([item_payload()])
        tutor = make_tutor(backend, sink, recorder)
        session = new_session(UID, SESSION)
        tutor.handle(
            session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
        )
        outcome = tutor.handle(session, StudentMove.REFUSE, "Não quero mais.")
        assert outcome.turn.terminal is TutorTurn.Terminal.COMPLETED
        assert outcome.turn.objective is TutorTurn.TutorState.CLOSE
        assert session.closed
        with pytest.raises(EduAgentError) as exc:
            tutor.handle(
                session, StudentMove.ASK_DIRECT, "Ainda estou aqui.",
                evidence=make_evidence(),
            )
        assert exc.value.code is ErrorCode.AMBIGUOUS_INPUT

    def test_cancel_closes_without_insistence(self, store, sink):
        backend = FakeBackend([item_payload()])
        tutor = make_tutor(backend, sink)
        session = new_session(UID, SESSION)
        tutor.handle(
            session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
        )
        outcome = tutor.handle(session, StudentMove.CANCEL, "Cancela.")
        assert outcome.turn.terminal is TutorTurn.Terminal.CANCELLED
        assert session.closed

    def test_hint_and_solution_require_pending_item(self, store, sink):
        tutor = make_tutor(FakeBackend([]), sink)
        session = new_session(UID, SESSION)
        with pytest.raises(EduAgentError) as exc:
            tutor.handle(session, StudentMove.REQUEST_HINT, "Ajuda.")
        assert exc.value.code is ErrorCode.AMBIGUOUS_INPUT
        with pytest.raises(EduAgentError) as exc:
            tutor.handle(session, StudentMove.REQUEST_SOLUTION, "Solução.")
        assert exc.value.code is ErrorCode.AMBIGUOUS_INPUT

    def test_empty_and_oversized_messages_rejected(self, store):
        tutor = make_tutor(FakeBackend([]), sink=None)
        session = new_session(UID, SESSION)
        with pytest.raises(EduAgentError) as exc:
            tutor.handle(session, StudentMove.ASK_DIRECT, "   ")
        assert exc.value.code is ErrorCode.SCHEMA_INVALID
        with pytest.raises(EduAgentError) as exc:
            tutor.handle(session, StudentMove.ASK_DIRECT, "x" * 2001)
        assert exc.value.code is ErrorCode.SCHEMA_INVALID

    def test_solution_never_enters_hint_context(self, store, sink):
        # A solução publicada no gabarito separado não pode aparecer nas
        # mensagens de pista (separação enunciado/solução, mapa §8).
        secret = "MARCA_SECRETA_DA_SOLUCAO_42"
        payload = json.dumps(
            {
                "prompt": ITEM_PROMPT,
                "expected_answer": f"{ITEM_ANSWER} {secret}",
                "rubric": [
                    {
                        "criterion_id": "dedup",
                        "description": "Explica a dedup por operation_id.",
                    }
                ],
                "citations": [0],
            },
            ensure_ascii=False,
        )
        backend = FakeBackend(
            [payload, text_payload("Pista 1: pense em retries.")]
        )
        tutor = make_tutor(backend, sink)
        session = new_session(UID, SESSION)
        tutor.handle(
            session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
        )
        tutor.handle(session, StudentMove.REQUEST_HINT, "Pista, por favor.")
        hint_messages = backend.last_messages
        joined = " ".join(str(m["content"]) for m in hint_messages)
        assert secret not in joined
        assert ITEM_ANSWER not in joined


def turn_citations(outcome) -> list[str]:
    return list(outcome.turn.citations)


# ---------------------------------------------------------------------------
# C2 — catálogo de skills YAML: schema do mapa, hash/version, sem autoedição
# ---------------------------------------------------------------------------


class TestSkillCatalogC2:
    def test_five_mandatory_skills_load_with_mapa_fields(self):
        catalog = SkillCatalog.load()
        assert set(catalog.ids()) == {
            "explain", "graduated_hint", "quiz", "flashcard", "self_explain"
        }
        expected_fields = {
            "id", "version", "tasks", "input_schema", "preconditions",
            "steps", "allowed_tools", "output_schema", "postconditions",
            "stop_conditions", "max_calls", "cases",
        }
        for skill_id in catalog.ids():
            spec = catalog.require(skill_id)
            assert isinstance(spec, SkillSpec)
            assert set(type(spec).model_fields) == expected_fields
            assert spec.version >= 1
            assert spec.steps
            assert spec.stop_conditions
            for tool in spec.allowed_tools:
                assert tool.value in {"document.search", "memory.query"}

    def test_hashes_and_versions_registered_and_verified(self):
        catalog = SkillCatalog.load()
        summary = catalog.summary()
        assert set(summary) == set(catalog.ids())
        for skill_id, entry in summary.items():
            path = SkillCatalog.load.__self__ if False else None  # noqa: F841
            raw = (Path(catalog.directory) / f"{skill_id}/skill.yaml").read_bytes()
            assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
            assert entry["version"] == catalog.require(skill_id).version
            assert entry["file"] == f"{skill_id}/skill.yaml"

    def test_loading_does_not_modify_catalog_files(self):
        """Sem autoedição ao vivo: carregar não altera nenhum arquivo (§8)."""
        before = {
            p: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path("eduagent/skills").rglob("*")
            if p.is_file()
        }
        SkillCatalog.load()
        after = {
            p: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path("eduagent/skills").rglob("*")
            if p.is_file()
        }
        assert before == after

    def _copy_catalog(self, tmp_path: Path) -> Path:
        target = tmp_path / "skills"
        shutil.copytree("eduagent/skills", target)
        return target

    def test_tampered_skill_fails_typed(self, tmp_path):
        target = self._copy_catalog(tmp_path)
        skill = target / "quiz" / "skill.yaml"
        skill.write_text(
            skill.read_text(encoding="utf-8") + "\n# adulterado\n",
            encoding="utf-8",
        )
        with pytest.raises(EduAgentError) as exc:
            SkillCatalog.load(target)
        assert exc.value.code is ErrorCode.SCHEMA_INVALID
        assert "revisão offline" in exc.value.message

    def test_registered_but_missing_file_fails_typed(self, tmp_path):
        target = self._copy_catalog(tmp_path)
        shutil.rmtree(target / "flashcard")
        with pytest.raises(EduAgentError) as exc:
            SkillCatalog.load(target)
        assert exc.value.code is ErrorCode.SCHEMA_INVALID

    def test_unknown_tool_in_skill_rejected(self, tmp_path):
        target = self._copy_catalog(tmp_path)
        skill = target / "quiz" / "skill.yaml"
        text = skill.read_text(encoding="utf-8").replace(
            "allowed_tools:\n  - document.search",
            "allowed_tools:\n  - web.search\n  - document.search",
        )
        skill.write_text(text, encoding="utf-8")
        # A ferramenta não proposável pelo Tutor é rejeitada na revisão
        # offline (tabela do mapa §10) — nunca entra no catálogo.
        with pytest.raises(EduAgentError) as exc:
            rehash(target)
        assert exc.value.code is ErrorCode.SCHEMA_INVALID
        assert "ferramenta" in exc.value.message

    def test_unknown_field_in_skill_rejected(self, tmp_path):
        target = self._copy_catalog(tmp_path)
        skill = target / "explain" / "skill.yaml"
        skill.write_text(
            skill.read_text(encoding="utf-8")
            + "\nauto_editavel: true\n",
            encoding="utf-8",
        )
        # O campo extra é rejeitado na revisão offline (rehash) — e o
        # catálogo existente nunca carrega um YAML fora do schema do mapa §8.
        with pytest.raises(EduAgentError) as exc:
            rehash(target)
        assert exc.value.code is ErrorCode.SCHEMA_INVALID

    def test_missing_mandatory_skill_rejected(self, tmp_path):
        target = self._copy_catalog(tmp_path)
        shutil.rmtree(target / "graduated_hint")
        shutil.rmtree(target / "flashcard")
        # Remove do registro para testar só a exigência do catálogo §8.
        registry = json.loads((target / "catalog.json").read_text("utf-8"))
        registry["skills"].pop("graduated_hint")
        registry["skills"].pop("flashcard")
        (target / "catalog.json").write_text(
            json.dumps(registry, ensure_ascii=False, indent=2), "utf-8"
        )
        with pytest.raises(EduAgentError) as exc:
            SkillCatalog.load(target)
        assert exc.value.code is ErrorCode.SCHEMA_INVALID
        assert "catálogo obrigatório" in exc.value.message


# ---------------------------------------------------------------------------
# C3 — item com gabarito/rubrica separados; flashcard pergunta/verso;
#      transferência com família identificada
# ---------------------------------------------------------------------------


class TestItemsC3:
    def test_solution_and_rubric_stored_separately_from_prompt(
        self, store, sink
    ):
        backend = FakeBackend([item_payload()])
        tutor = make_tutor(backend, sink)
        session = new_session(UID, SESSION)
        outcome = tutor.handle(
            session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
        )
        item = outcome.item
        assert item is not None
        # Gabarito/rubrica vivem atrás de refs (ID+versão), fora do prompt.
        assert item.expected_answer_ref.kind == "event"
        assert item.rubric_ref.kind == "event"
        assert ITEM_ANSWER not in item.prompt
        # Resolução do ref devolve o payload separado (gabarito + rubrica).
        payload = sink.resolve(UID, item.expected_answer_ref)
        assert payload["expected_answer"] == ITEM_ANSWER
        assert payload["rubric"][0]["criterion_id"] == "dedup"
        # Projeção na tabela items (§5) com refs na forma ID+versão.
        row = store._conn.execute(
            "SELECT answer_ref, rubric_ref, source_refs_json FROM items "
            "WHERE id = ?",
            (str(item.item_id),),
        ).fetchone()
        assert row["answer_ref"] == item.expected_answer_ref.to_locator()
        assert row["rubric_ref"] == item.rubric_ref.to_locator()
        assert DOC_ID in row["source_refs_json"]  # fonte armazenada com o item

    def test_flashcard_separates_question_verse_with_source(self, store, sink):
        backend = FakeBackend([json.dumps(FLASHCARD, ensure_ascii=False)])
        tutor = make_tutor(backend, sink)
        session = new_session(UID, SESSION)
        outcome = tutor.handle(
            session, StudentMove.FLASHCARD, "Cria um flashcard de WAL.",
            evidence=make_evidence(),
        )
        item = outcome.item
        assert item is not None
        assert item.kind is LearningItem.ItemKind.FLASHCARD
        # Pergunta (frente) é o prompt; verso fica no gabarito separado.
        assert item.prompt == FLASHCARD["question"]
        payload = sink.resolve(UID, item.expected_answer_ref)
        assert payload["expected_answer"] == FLASHCARD["verse"]
        assert payload["expected_answer"] != item.prompt
        assert item.source_refs  # fonte indicada (mapa §8)

    def test_flashcard_equal_question_verse_is_repaired_then_rejected(
        self, store, sink
    ):
        bad = dict(FLASHCARD)
        bad["verse"] = bad["question"]
        backend = FakeBackend(
            [json.dumps(bad, ensure_ascii=False),
             json.dumps(FLASHCARD, ensure_ascii=False)]
        )
        tutor = make_tutor(backend, sink)
        session = new_session(UID, SESSION)
        outcome = tutor.handle(
            session, StudentMove.FLASHCARD, "Flashcard.", evidence=make_evidence()
        )
        # Primeira saída violou a separação; o reparo corrigiu.
        assert len(backend.calls) == 2
        assert outcome.item.prompt == FLASHCARD["question"]

    def test_transfer_requires_identified_family(self, store, sink):
        tutor = make_tutor(FakeBackend([]), sink)
        session = new_session(UID, SESSION)
        with pytest.raises(EduAgentError) as exc:
            tutor.handle(
                session, StudentMove.TRANSFER, "Faz uma variação.",
                evidence=make_evidence(),
            )
        assert exc.value.code is ErrorCode.AMBIGUOUS_INPUT
        assert items_count(store) == 0

    def test_transfer_uses_identified_family_and_increments_version(
        self, store, sink
    ):
        backend = FakeBackend([item_payload(), item_payload()])
        tutor = make_tutor(backend, sink)
        session = new_session(UID, SESSION)
        first = tutor.handle(
            session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
        )
        family = first.item.family_id
        outcome = tutor.handle(
            session, StudentMove.TRANSFER, "Agora em outro contexto.",
            evidence=make_evidence(),
            family_id=family,
        )
        assert outcome.transfer
        assert outcome.item.family_id == family
        assert outcome.item.version == 2  # mesma família, versão nova
        assert items_count(store) == 2
        payload = sink.resolve(UID, outcome.item.expected_answer_ref)
        assert payload["exposure"]["transfer"] is True

    def test_transfer_after_reveal_flags_solution_exposure(self, store, sink):
        # Cópia não conta como aprendizagem independente (§15.2): a sessão
        # registra a solução exposta da família.
        backend = FakeBackend([item_payload(), item_payload()])
        tutor = make_tutor(backend, sink)
        session = new_session(UID, SESSION)
        first = tutor.handle(
            session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
        )
        # Revela em sessão separada para a mesma família não é possível
        # aqui (a sessão encerra); a marcação de sessão corrente:
        session.family_solution_seen.add(first.item.family_id)
        outcome = tutor.handle(
            session, StudentMove.TRANSFER, "Variação.",
            evidence=make_evidence(),
            family_id=first.item.family_id,
        )
        assert outcome.solution_exposed_in_session
        payload = sink.resolve(UID, outcome.item.expected_answer_ref)
        assert payload["exposure"]["family_solution_seen_in_session"] is True

    def test_practice_without_evidence_is_no_evidence(self, store, sink):
        tutor = make_tutor(FakeBackend([]), sink)
        session = new_session(UID, SESSION)
        with pytest.raises(EduAgentError) as exc:
            tutor.handle(
                session, StudentMove.PRACTICE, "Prática.",
                evidence=TutorEvidence(topic_ids=(TOPIC,)),
            )
        assert exc.value.code is ErrorCode.NO_EVIDENCE
        assert items_count(store) == 0

    def test_practice_without_topics_is_ambiguous(self, store, sink):
        tutor = make_tutor(FakeBackend([]), sink)
        session = new_session(UID, SESSION)
        with pytest.raises(EduAgentError) as exc:
            tutor.handle(
                session, StudentMove.PRACTICE, "Prática.",
                evidence=TutorEvidence(
                    chunks=make_evidence(topic_ids=()).chunks,
                    coverage="supported",
                ),
            )
        assert exc.value.code is ErrorCode.AMBIGUOUS_INPUT

    def test_prompt_leaking_solution_fails_typed(self, store, sink):
        leak = json.dumps(
            {
                "prompt": f"{ITEM_PROMPT} Resposta: {ITEM_ANSWER}",
                "expected_answer": ITEM_ANSWER,
                "rubric": [{"criterion_id": "a", "description": "b"}],
                "citations": [0],
            },
            ensure_ascii=False,
        )
        backend = FakeBackend([leak, leak, leak])
        config = TutorConfig(max_llm_calls=3, max_repairs_total=2)
        tutor = make_tutor(backend, sink, config=config)
        session = new_session(UID, SESSION)
        with pytest.raises(EduAgentError) as exc:
            tutor.handle(
                session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
            )
        assert exc.value.code is ErrorCode.SCHEMA_INVALID
        assert "enunciado contém a solução" in exc.value.message
        assert items_count(store) == 0

    def test_item_without_source_citation_fails_typed(self, store, sink):
        no_source = json.dumps(
            {
                "prompt": ITEM_PROMPT,
                "expected_answer": ITEM_ANSWER,
                "rubric": [{"criterion_id": "a", "description": "b"}],
                "citations": [],
            },
            ensure_ascii=False,
        )
        backend = FakeBackend([no_source, no_source])
        config = TutorConfig(max_llm_calls=2, max_repairs_total=1)
        tutor = make_tutor(backend, sink, config=config)
        session = new_session(UID, SESSION)
        with pytest.raises(EduAgentError) as exc:
            tutor.handle(
                session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
            )
        assert exc.value.code is ErrorCode.SCHEMA_INVALID
        assert len(backend.calls) == 2  # 1 geração + 1 reparo orçado
        assert items_count(store) == 0


# ---------------------------------------------------------------------------
# Adapter/policy — schema da 002, parse/parse-reparo/orçamento, citações
# ---------------------------------------------------------------------------


class TestGenerationPolicy:
    def test_schema_sent_only_when_capability_verified(self, store, sink):
        payload = item_payload()
        backend = FakeBackend([payload], json_schema_capability=True)
        tutor = make_tutor(backend, sink)
        session = new_session(UID, SESSION)
        tutor.handle(
            session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
        )
        assert isinstance(backend.calls[0]["schema"], dict)

        backend2 = FakeBackend([payload], json_schema_capability=False)
        tutor2 = make_tutor(backend2, sink)
        session2 = new_session(UID, SESSION)
        tutor2.handle(
            session2, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
        )
        # Parse/política continuam obrigatórios mesmo sem schema no runtime.
        assert backend2.calls[0]["schema"] is None

    def test_sampler_is_admitted_non_thinking_profile(self, store, sink):
        backend = FakeBackend([item_payload()])
        tutor = make_tutor(backend, sink)
        session = new_session(UID, SESSION)
        tutor.handle(
            session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
        )
        sampler = backend.calls[0]["sampler"]
        assert sampler.thinking is False
        assert sampler.temperature == 0.7
        assert backend.calls[0]["seed"] == 0

    def test_malformed_json_repaired_once_then_success(self, store, sink):
        backend = FakeBackend(["isto não é json", item_payload()])
        tutor = make_tutor(backend, sink)
        session = new_session(UID, SESSION)
        outcome = tutor.handle(
            session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
        )
        assert outcome.item is not None
        assert len(backend.calls) == 2
        # A mensagem de reparo cita a rejeição (parse/limpo, sem saída parcial).
        repair = backend.last_messages[-1]["content"]
        assert "rejeitada" in repair

    def test_repairs_exhausted_fail_typed_without_partial_output(
        self, store, sink
    ):
        backend = FakeBackend(["lixo", "lixo"])
        config = TutorConfig(max_llm_calls=2, max_repairs_total=1)
        tutor = make_tutor(backend, sink, config=config)
        session = new_session(UID, SESSION)
        with pytest.raises(EduAgentError) as exc:
            tutor.handle(
                session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
            )
        assert exc.value.code is ErrorCode.SCHEMA_INVALID
        assert "Nenhuma saída parcial" in exc.value.message
        assert len(backend.calls) == 2
        assert items_count(store) == 0

    def test_skill_max_calls_caps_budget(self, store, sink):
        # explain tem max_calls=2 (mapa §8): orçamento do turno é o mínimo.
        backend = FakeBackend(["lixo", "lixo", "lixo"])
        tutor = make_tutor(backend, sink=None)
        session = new_session(UID, SESSION)
        with pytest.raises(EduAgentError):
            tutor.handle(
                session, StudentMove.ASK_DIRECT, "Pergunta.",
                evidence=make_evidence(),
            )
        assert len(backend.calls) == 2

    def test_invented_citation_fails_typed(self, store):
        other = f"doc:{_uuid.UUID(DOC_ID)}@1:p9:b9"
        backend = FakeBackend(
            [text_payload(f"Explicação com {other}."), text_payload("sem citação")]
        )
        tutor = make_tutor(backend, sink=None)
        session = new_session(UID, SESSION)
        outcome = tutor.handle(
            session, StudentMove.ASK_DIRECT, "Pergunta.",
            evidence=make_evidence(),
        )
        # A primeira saída citou fora do pacote; o reparo corrigiu.
        assert len(backend.calls) == 2
        assert outcome.turn.citations == []

    def test_citation_outside_pack_never_passes(self, store):
        other = f"doc:{_uuid.UUID(DOC_ID)}@1:p9:b9"
        backend = FakeBackend(
            [text_payload(f"Explicação com {other}.")] * 3
        )
        config = TutorConfig(max_llm_calls=2, max_repairs_total=1)
        tutor = make_tutor(backend, sink=None, config=config)
        session = new_session(UID, SESSION)
        with pytest.raises(EduAgentError) as exc:
            tutor.handle(
                session, StudentMove.ASK_DIRECT, "Pergunta.",
                evidence=make_evidence(),
            )
        assert exc.value.code is ErrorCode.SCHEMA_INVALID
        assert "citação fictícia" in exc.value.message

    def test_adapter_error_propagates_typed(self, store, sink):
        backend = FakeBackend(
            [],
            error=ModelAdapterError(
                ErrorCode.TIMEOUT, "deadline excedido", retryable=True
            ),
        )
        tutor = make_tutor(backend, sink)
        session = new_session(UID, SESSION)
        with pytest.raises(EduAgentError) as exc:
            tutor.handle(
                session, StudentMove.ASK_DIRECT, "Pergunta.",
                evidence=make_evidence(),
            )
        assert exc.value.code is ErrorCode.TIMEOUT
        assert exc.value.retryable


# ---------------------------------------------------------------------------
# Sink e política configurável
# ---------------------------------------------------------------------------


class TestSinkAndPolicy:
    def test_publication_is_idempotent_commit_with_revision_bump(
        self, store, sink
    ):
        backend = FakeBackend([item_payload()])
        tutor = make_tutor(backend, sink)
        session = new_session(UID, SESSION)
        before = store.domain_revision(UID)
        tutor.handle(
            session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
        )
        assert store.domain_revision(UID) == before + 1
        row = store._conn.execute(
            "SELECT kind FROM events WHERE kind = 'item_published'"
        ).fetchone()
        assert row is not None

    def test_sink_resolve_rejects_foreign_user(self, store, sink):
        backend = FakeBackend([item_payload()])
        tutor = make_tutor(backend, sink)
        session = new_session(UID, SESSION)
        outcome = tutor.handle(
            session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
        )
        with pytest.raises(EduAgentError) as exc:
            sink.resolve(UID2, outcome.item.expected_answer_ref)
        assert exc.value.code is ErrorCode.SOURCE_UNRESOLVED

    def test_review_intervals_is_configurable_policy(self):
        # Mapa §8: revisão inicial 1/3/7 dias é política CONFIGURÁVEL.
        assert TutorConfig().review_intervals_days == (1, 3, 7)
        custom = TutorConfig(review_intervals_days=(2, 5))
        assert custom.review_intervals_days == (2, 5)

    def test_sink_requires_store(self, store):
        # Publicar sem sink configurado falha tipado (gabarito não tem onde
        # ficar separado do enunciado).
        tutor = make_tutor(FakeBackend([item_payload()]), sink=None)
        session = new_session(UID, SESSION)
        with pytest.raises(EduAgentError) as exc:
            tutor.handle(
                session, StudentMove.PRACTICE, "Prática.", evidence=make_evidence()
            )
        assert exc.value.code is ErrorCode.INTERNAL_FAILURE
