"""Serviço de memória do Bibliotecário (mapa normativo §7, §5, §15.1, §13.6;
task 010).

Contratos implementados:

- **Memória temporal (§7)**: eventos mantêm ``occurred_at`` e ``recorded_at``
  (colunas do DDL §5); fatos mantêm validade (``valid_from``/``valid_to``) e
  ``supersedes``. Origem ``observed/asserted/inferred`` registrada no payload
  (``MemoryPack.Origin``, §4/§7). **Preferência declarada não é evidência de
  aprendizagem**: eventos de ``preference`` são apenas registros de memória —
  a projeção de competência (``TopicState``) só é atualizada por assessments
  aceitos no redutor (§8); nenhum caminho aqui escreve em ``topic_states``
  a partir de preferências/leitura/autorrelato.
- **"Atual" vs "como mudou" (§7)**: a projeção vigente (``current_facts``)
  exclui fato ``superseded`` — um fato com sucessor ativo (ou ``valid_to``
  no passado) não volta a ser atual **por similaridade ou por qualquer
  consulta de recuperação**: a projeção é derivada do grafo de ``supersedes``
  e da validade, nunca do ranking. "Como mudou" (``fact_history``) devolve
  as versões em ordem temporal (``recorded_at``), com as versões anteriores
  explicitamente marcadas como anteriores — consulta de evidências antigas
  pode trazê-las de forma explícita (``include_superseded=True``), nunca
  como atuais.
- **Contradição não conciliada (§7)**: dois fatos ativos da mesma entidade
  com valores normalizados distintos são devolvidos **ambos** como
  ``MemoryPack.Contradiction`` com ``pending=True`` — nada é conciliado
  silenciosamente (a correção é operação explícita do usuário,
  ``correct_fact``).
- **Recuperação (§7)**: filtros usuário/disciplina/tópico/tempo → busca
  lexical (BM25 sobre payloads) **+ densa** (embedder injetável; produto
  interno exato, sem ANN) → fusão RRF → **até 8 originais em 2.048 tokens**
  (defaults normativos do §7) **+ fatos atuais obrigatórios** (sempre
  inclusos, fora do corte). Correções relevantes **substituem** candidatos:
  se o evento selecionado foi corrigido/invalidado por evento posterior, o
  evento de correção entra no lugar. Eventos purgados (payload NULL) nunca
  são candidatos — originais excluídos não ressuscitam.
- **Síntese (§7)**: nasce **dos originais** (eventos ``summary_published``
  são recusados como fonte — não encadear resumo de resumo), com
  ``claim→event_ids``, cobertura temporal e verificação exata de datas,
  números, polaridade, ajuda e estado (``eduagent/context.py``: extração e
  conferência). Falha de verificação **mantém os originais** — a síntese não
  é publicada (``verification='failed'``) e o evento fonte jamais é apagado
  por compactação: publicar síntese é artefato derivado novo na tabela
  ``summaries`` + evento ``summary_published``, com arestas
  ``derived_from`` nas ``artifact_dependencies``.
- **Correção e deleção (§7/§10/§15.1)**: ``correct_fact`` cria fato novo com
  ``supersedes`` apontando para o anterior, fecha a validade do antigo
  (``valid_to``), registra aresta ``supersedes`` em ``artifact_dependencies``
  e **percorre os dependentes** (BFS pelos dois sentidos do grafo),
  invalidando versões publicadas (evento ``artifact_invalidated`` +
  ``verification='failed'`` em resumos dependentes). ``delete_data`` exige
  confirmação explícita (rota §10: preview → confirm), aplica tombstone
  **sem payload** (catálogo ``tombstones`` — migração 0005), purge de
  payloads de eventos sem **nenhum hash reversível** do texto excluído
  (§5: gatilho ``events_no_undrop_payload`` impede restauração), identifica
  o backup como **pendente até expiração** (retenção proposta de 30 dias —
  default de ensaio, §5/§15.1; deleção que remove todos os dados de memória
  do usuário registra backup já removido na solicitação) e **reconstitui
  projeções** (``topic_states`` recalculados desde os registros restantes).
  Checkpoints (task 014) e traces (task 015) ainda não existem no MVP: a
  propagação a eles é registrada pelos tombstones e eventos de invalidação,
  que o replay dessas camadas consume quando existirem — nada é alegado
  como propagado sem existir.

Defaults numéricos (2048/8/30 dias) são os valores do §7/§5 ou escolhas de
ensaio a calibrar — nunca resultados medidos.
"""

from __future__ import annotations

import hashlib
import json
import uuid as _uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

import numpy as np
from rank_bm25 import BM25Okapi

from eduagent.contracts import (
    AcademicFact,
    EduAgentError,
    ErrorCode,
    MemoryPack,
    SenderRole,
    SourceRef,
    ToolName,
    TopicState,
    validate_tool_request,
)
from eduagent.context import verify_claim_against_sources
from eduagent.services.effects import CommitRequest, EffectsService, EventSpec
from eduagent.storage.repository import DomainStore, Receipt

_DIAGNOSTIC = "eduagent/services/memory.py"

# ---------------------------------------------------------------------------
# Ações e kinds de evento (mapa §4/§5/§11)
# ---------------------------------------------------------------------------

ACTION_EVENT_APPEND = "event.append"
ACTION_FACT_CORRECT = "fact.correct"
ACTION_DATA_DELETE = "data.delete"

EVENT_FACT_CORRECTED = "fact_corrected"
EVENT_ARTIFACT_INVALIDATED = "artifact_invalidated"
EVENT_SUMMARY_PUBLISHED = "summary_published"

#: Kind→MemoryPack.EventKind (mapa §4): mapeamento de exibição do pacote.
_EVENT_KIND_MAP: dict[str, MemoryPack.EventKind] = {
    "attempt_recorded": MemoryPack.EventKind.ATTEMPT,
    "assessment_recorded": MemoryPack.EventKind.ASSESSMENT,
    "fact_corrected": MemoryPack.EventKind.CORRECTION,
    "hint": MemoryPack.EventKind.HINT,
    "reading": MemoryPack.EventKind.READING,
    "self_report": MemoryPack.EventKind.SELF_REPORT,
    "preference": MemoryPack.EventKind.PREFERENCE,
}

# ---------------------------------------------------------------------------
# Defaults do §7/§5 — valores normativos (2.048/8) e escolha de ensaio (30d)
# ---------------------------------------------------------------------------

MEMORY_TOKEN_BUDGET = 2048  # §7: "até 8 originais em 2.048 tokens"
MEMORY_MAX_ORIGINALS = 8  # §7: "até 8 originais"
BACKUP_RETENTION_DAYS = 30  # §5/§15.1: "retenção proposta 30 dias" (ensaio)

_BM25_K1 = 1.5  # mesmos defaults de ensaio do §6.5 (task 007)
_BM25_B = 0.75

#: Refs de artefatos: convenção ``<prefixo>:<uuid>@<versão>``; a versão da
#: ref de fato é ``revision + 1`` (``facts.revision`` começa em 0 e ``Ref``
#: exige versão ≥ 1 — mapa §4).
FACT_REF_VERSION_OFFSET = 1


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


def _utc_iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat()


def fact_ref(fact_id: str, revision: int) -> str:
    return f"fact:{fact_id}@{int(revision) + FACT_REF_VERSION_OFFSET}"


def event_ref(event_id: str) -> str:
    return f"event:{event_id}@1"


def summary_ref(summary_id: str, revision: int) -> str:
    return f"summary:{summary_id}@{max(int(revision), 1)}"


# ---------------------------------------------------------------------------
# Registros projetados
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FactRecord:
    """Fato projetado (§7): validade, ``supersedes``, origem e status."""

    fact_id: _uuid.UUID
    entity_id: _uuid.UUID
    kind: str
    original_expression: str
    normalized_value: str
    precision: str
    status: str
    authority: str
    origin: str
    valid_from: str | None
    valid_to: str | None
    recorded_at: str
    supersedes: str | None
    revision: int
    source_refs: tuple[dict[str, Any], ...] = ()
    timezone: str | None = None

    @property
    def ref(self) -> str:
        return fact_ref(str(self.fact_id), self.revision)

    @property
    def superseded(self) -> bool:
        """Fato com validade fechada — nunca é 'atual' (§7)."""
        return self.valid_to is not None

    def to_academic_fact(self) -> AcademicFact:
        """Contrato ``AcademicFact`` (mapa §4) a partir do registro."""
        source_refs: list[SourceRef] = []
        for entry in self.source_refs:
            source_refs.append(SourceRef.model_validate(entry))
        return AcademicFact(
            entity_id=self.entity_id,
            kind=AcademicFact.FactKind(self.kind),
            original_expression=self.original_expression,
            normalized_value=self.normalized_value,
            precision=AcademicFact.Precision(self.precision),
            timezone=self.timezone,
            source_refs=source_refs,
            status=AcademicFact.FactStatus(self.status),
            authority=AcademicFact.FactAuthority(self.authority),
        )


@dataclass(frozen=True)
class HistoricalFact:
    """Versão anterior de fato, explícita em consulta de evidências antigas
    (§7): nunca apresentada como atual."""

    fact: FactRecord
    superseded_by: str | None  # ref do fato sucessor, se houver


@dataclass(frozen=True)
class EventRow:
    """Evento bruto projetado (§5/§7)."""

    event_id: _uuid.UUID
    kind: str
    payload: dict[str, Any] | None
    occurred_at: datetime
    recorded_at: datetime
    session_id: str | None

    @property
    def purged(self) -> bool:
        return self.payload is None

    @property
    def ref(self) -> str:
        return event_ref(str(self.event_id))

    def pack_kind(self) -> MemoryPack.EventKind:
        return _EVENT_KIND_MAP.get(self.kind, MemoryPack.EventKind.OTHER)


@dataclass(frozen=True)
class SynthesisClaim:
    """Claim de síntese com ``claim→event_ids`` (§7)."""

    text: str
    event_ids: tuple[str, ...]


@dataclass(frozen=True)
class SynthesisProposal:
    """Proposta de síntese: claims, cobertura temporal e verificação (§7)."""

    claims: tuple[SynthesisClaim, ...]
    coverage_from: datetime | None
    coverage_to: datetime | None
    verification: str  # 'verified' | 'failed'
    failed_claims: tuple[str, ...] = ()

    @property
    def verified(self) -> bool:
        return self.verification == "verified"


@dataclass(frozen=True)
class CorrectionResult:
    """Resultado de ``correct_fact`` (§15.1)."""

    new_fact_id: _uuid.UUID
    old_fact_id: _uuid.UUID
    receipt: Receipt
    invalidated_refs: tuple[str, ...]


@dataclass(frozen=True)
class DeletePreview:
    """Preview da deleção (rota §10: validate_scope → preview → confirm)."""

    scope: str
    event_ids: tuple[str, ...]
    fact_ids: tuple[str, ...]
    summary_ids: tuple[str, ...]
    backup_pending_until: str | None


@dataclass(frozen=True)
class DeleteResult:
    """Resultado de ``delete_data`` (§15.1)."""

    receipt: Receipt
    tombstoned_refs: tuple[str, ...]
    invalidated_refs: tuple[str, ...]
    backup_pending_until: str | None
    projections_reconstituted: bool


@dataclass(frozen=True)
class MemoryQueryResult:
    """Resultado de ``memory_query`` (§7): pacote contrato-tipo + seleção
    detalhada e versões antigas explícitas quando pedidas."""

    pack: MemoryPack
    selected_events: tuple[EventRow, ...]
    historical_facts: tuple[HistoricalFact, ...] = ()
    rankings: tuple[str, ...] = ()  # 'lexical' | 'dense' (usados)


# ---------------------------------------------------------------------------
# Serviço
# ---------------------------------------------------------------------------


class MemoryService:
    """Memória temporal, recuperação, síntese, correção e deleção
    (mapa §7, §5, §15.1; ferramenta ``memory.query`` do §10)."""

    def __init__(
        self,
        store: DomainStore,
        effects: EffectsService,
        *,
        clock: Any = None,
    ) -> None:
        self._store = store
        self._effects = effects
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    # -- gravação de eventos (§5/§7) -----------------------------------------

    def record_event(
        self,
        *,
        user_id: str,
        session_id: str | None,
        kind: MemoryPack.EventKind,
        payload: dict[str, Any],
        occurred_at: datetime,
        origin: MemoryPack.Origin,
        operation_id: str | None = None,
    ) -> Receipt:
        """Apêndice de evento de memória com ``occurred_at``/``recorded_at``
        e origem rotulada (§7), via commit idempotente (§11).

        Preferência declarada (``kind='preference'``) é registro de memória —
        **não** atualiza competência (§7/§8): este método não escreve em
        ``topic_states``.
        """
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "occurred_at do evento exige zona (UTC/offset)",
                diagnostic=_DIAGNOSTIC,
            )
        occurred_iso = _utc_iso(occurred_at)
        now_iso = _utc_iso(self._clock())
        event_payload = dict(payload)
        event_payload["origin"] = origin.value
        digest = _digest(
            {
                "kind": kind.value,
                "payload": event_payload,
                "occurred_at": occurred_iso,
            }
        )
        request = CommitRequest(
            operation_id=operation_id or str(_uuid.uuid4()),
            user_id=user_id,
            action=ACTION_EVENT_APPEND,
            digest=digest,
            expected_version=self._store.domain_revision(user_id),
            event=EventSpec(
                id=str(_uuid.uuid4()),
                kind=kind.value,
                occurred_at=occurred_iso,
                recorded_at=now_iso,
                payload=event_payload,
                session_id=session_id,
            ),
        )
        return self._effects.commit(request)

    # -- fatos: asserção, supersessão e projeção "atual" ----------------------

    def assert_fact(
        self,
        *,
        user_id: str,
        entity_id: _uuid.UUID,
        kind: AcademicFact.FactKind,
        original_expression: str,
        normalized_value: str,
        precision: AcademicFact.Precision,
        status: AcademicFact.FactStatus,
        authority: AcademicFact.FactAuthority,
        origin: MemoryPack.Origin,
        supersedes_fact_id: str | None = None,
        source_refs: Sequence[SourceRef] = (),
        operation_id: str | None = None,
    ) -> FactRecord:
        """Cria fato com validade e ``supersedes`` (§7): o fato antigo tem a
        validade fechada (``valid_to``) e aresta ``supersedes`` registrada em
        ``artifact_dependencies`` (§15.1).

        O contrato ``AcademicFact`` (task 003) recusa ``confirmed`` sem
        autoridade do usuário — a barreira vale aqui também.
        """
        fact = AcademicFact(
            entity_id=entity_id,
            kind=kind,
            original_expression=original_expression,
            normalized_value=normalized_value,
            precision=precision,
            timezone=None,
            source_refs=list(source_refs),
            status=status,
            authority=authority,
        )
        now_iso = _utc_iso(self._clock())
        value_json = json.dumps(
            {
                "entity_id": str(fact.entity_id),
                "original_expression": fact.original_expression,
                "normalized_value": fact.normalized_value,
                "precision": fact.precision.value,
                "origin": origin.value,
            },
            sort_keys=True,
        )
        fact_id = str(_uuid.uuid4())
        statements: list[tuple[str, tuple[Any, ...]]] = [
            (
                "INSERT INTO facts(id, user_id, kind, value_json, authority, "
                "valid_from, valid_to, recorded_at, source_refs_json, "
                "supersedes, status, revision) VALUES (?,?,?,?,?,?,?,?,?,?,?,0)",
                (
                    fact_id,
                    user_id,
                    fact.kind.value,
                    value_json,
                    fact.authority.value,
                    now_iso,
                    None,
                    now_iso,
                    json.dumps(
                        [ref.model_dump(mode="json") for ref in fact.source_refs]
                    ),
                    supersedes_fact_id,
                    fact.status.value,
                ),
            )
        ]
        if supersedes_fact_id is not None:
            old = self._fact_row(user_id, supersedes_fact_id)
            if old is None:
                raise EduAgentError(
                    ErrorCode.SOURCE_UNRESOLVED,
                    f"fato {supersedes_fact_id} não resolve para o usuário",
                    diagnostic=_DIAGNOSTIC,
                )
            # Fecha a validade do antigo e registra a aresta (§15.1).
            statements.append(
                (
                    "UPDATE facts SET valid_to = ? WHERE id = ? AND user_id = ?",
                    (now_iso, supersedes_fact_id, user_id),
                )
            )
            statements.append(self._supersedes_edge(user_id, fact_id, 0, old))
        digest = _digest({"fact": value_json, "supersedes": supersedes_fact_id})
        self._effects.commit(
            CommitRequest(
                operation_id=operation_id or str(_uuid.uuid4()),
                user_id=user_id,
                action=ACTION_EVENT_APPEND,
                digest=digest,
                expected_version=self._store.domain_revision(user_id),
                projection=tuple(statements),
            )
        )
        record = self._fact_record(user_id, fact_id)
        assert record is not None  # commit confirmou a inserção
        return record

    @staticmethod
    def _supersedes_edge(
        user_id: str, new_fact_id: str, new_revision: int, old_row: Any
    ) -> tuple[str, tuple[Any, ...]]:
        return (
            "INSERT OR IGNORE INTO artifact_dependencies(user_id, child_ref, "
            "parent_ref, relation) VALUES (?,?,?,'supersedes')",
            (
                user_id,
                fact_ref(new_fact_id, new_revision),
                fact_ref(str(old_row["id"]), int(old_row["revision"])),
            ),
        )

    def _fact_row(self, user_id: str, fact_id: str) -> Any:
        rows = self._store.fetch_user_rows(
            "SELECT id, kind, value_json, authority, valid_from, valid_to, "
            "recorded_at, source_refs_json, supersedes, status, revision "
            "FROM facts WHERE id = ? AND user_id = ?",
            (fact_id, user_id),
        )
        return rows[0] if rows else None

    def _fact_record(self, user_id: str, fact_id: str) -> FactRecord | None:
        row = self._fact_row(user_id, fact_id)
        if row is None:
            return None
        payload = json.loads(str(row["value_json"]))
        return FactRecord(
            fact_id=_uuid.UUID(str(row["id"])),
            entity_id=_uuid.UUID(str(payload["entity_id"])),
            kind=str(row["kind"]),
            original_expression=str(payload["original_expression"]),
            normalized_value=str(payload["normalized_value"]),
            precision=str(payload["precision"]),
            status=str(row["status"]),
            authority=str(row["authority"]),
            origin=str(payload.get("origin", "observed")),
            valid_from=row["valid_from"],
            valid_to=row["valid_to"],
            recorded_at=str(row["recorded_at"]),
            supersedes=row["supersedes"],
            revision=int(row["revision"]),
            source_refs=tuple(json.loads(str(row["source_refs_json"]))),
            timezone=payload.get("timezone"),
        )

    def current_facts(self, user_id: str) -> list[FactRecord]:
        """Projeção vigente (§7: "'atual' recupera projeção vigente e
        correções"): fatos confirmados com validade aberta e **sem sucessor
        ativo**. Fato ``superseded`` nunca volta por similaridade — a
        exclusão é estrutural (grafo ``supersedes``), não de ranking.
        """
        rows = self._store.fetch_user_rows(
            "SELECT id FROM facts WHERE user_id = ? AND status = 'confirmed' "
            "AND valid_to IS NULL AND NOT EXISTS ("
            "  SELECT 1 FROM facts s WHERE s.supersedes = facts.id"
            "  AND s.status != 'rejected') ORDER BY facts.recorded_at, facts.id",
            (user_id,),
        )
        records: list[FactRecord] = []
        for row in rows:
            record = self._fact_record(user_id, str(row["id"]))
            if record is not None:
                records.append(record)
        return records

    def fact_history(self, user_id: str, entity_id: _uuid.UUID) -> list[FactRecord]:
        """Versões da entidade em ordem temporal (§7: "'como mudou' recupera
        versões em ordem temporal"), incluindo as substituídas."""
        rows = self._store.fetch_user_rows(
            "SELECT id FROM facts WHERE user_id = ? AND "
            "json_extract(value_json, '$.entity_id') = ? "
            "ORDER BY facts.recorded_at, facts.id",
            (user_id, str(entity_id)),
        )
        records: list[FactRecord] = []
        for row in rows:
            record = self._fact_record(user_id, str(row["id"]))
            if record is not None:
                records.append(record)
        return records

    def historical_facts(
        self, user_id: str, entity_id: _uuid.UUID
    ) -> list[HistoricalFact]:
        """Versões anteriores explícitas (§7: "consulta de evidências antigas
        pode trazer versões anteriores explicitamente"), com o sucessor."""
        successor_rows = {
            str(row["supersedes"]): str(row["id"])
            for row in self._store.fetch_user_rows(
                "SELECT supersedes, id FROM facts "
                "WHERE user_id = ? AND supersedes IS NOT NULL",
                (user_id,),
            )
        }
        history: list[HistoricalFact] = []
        for record in self.fact_history(user_id, entity_id):
            if record.superseded:
                successor = successor_rows.get(str(record.fact_id))
                history.append(
                    HistoricalFact(fact=record, superseded_by=successor)
                )
        return history

    def detect_contradictions(
        self, user_id: str, facts: Sequence[FactRecord] | None = None
    ) -> list[MemoryPack.Contradiction]:
        """Contradição não conciliada (§7): ≥2 fatos ativos da mesma entidade
        com valores distintos → **ambos** os registros + ``pending=True``.
        Fato substituído não participa — a correção conciliada fechou sua
        validade.
        """
        active = list(facts) if facts is not None else self.current_facts(user_id)
        by_entity: dict[_uuid.UUID, list[FactRecord]] = {}
        for fact in active:
            if fact.status != "confirmed":
                continue
            by_entity.setdefault(fact.entity_id, []).append(fact)
        contradictions: list[MemoryPack.Contradiction] = []
        for entity_id, group in sorted(by_entity.items(), key=lambda kv: str(kv[0])):
            values = {fact.normalized_value.casefold() for fact in group}
            if len(values) > 1:
                contradictions.append(
                    MemoryPack.Contradiction(
                        entity_id=entity_id,
                        records=[fact.to_academic_fact() for fact in group],
                        pending=True,
                    )
                )
        return contradictions

    # -- correção (§10/§15.1) --------------------------------------------------

    def correct_fact(
        self,
        *,
        user_id: str,
        fact_id: str,
        corrected_value: str,
        reason: str,
        operation_id: str | None = None,
    ) -> CorrectionResult:
        """Correção de fato (§15.1): fato novo com ``supersedes``, validade
        do antigo fechada, aresta registrada e **dependentes invalidados**
        por percurso das ``artifact_dependencies`` (BFS nos dois sentidos),
        com reconstituição da projeção de fatos (derivada em leitura — a
        correção é imediatamente visível na projeção vigente).

        Checkpoints (014) e traces (015) não existem no MVP: a propagação a
        eles fica registrada nos eventos de invalidação e nos tombstones.
        """
        old = self._fact_record(user_id, fact_id)
        if old is None:
            raise EduAgentError(
                ErrorCode.SOURCE_UNRESOLVED,
                f"fato {fact_id} não resolve para o usuário",
                diagnostic=_DIAGNOSTIC,
            )
        now = self._clock()
        now_iso = _utc_iso(now)
        new_fact_id = str(_uuid.uuid4())
        value_json = json.dumps(
            {
                "entity_id": str(old.entity_id),
                "original_expression": old.original_expression,
                "normalized_value": corrected_value,
                "precision": old.precision,
                "origin": MemoryPack.Origin.ASSERTED.value,
                "corrected_from": old.ref,
            },
            sort_keys=True,
        )
        ref_old = old.ref
        statements: list[tuple[str, tuple[Any, ...]]] = [
            (
                "INSERT INTO facts(id, user_id, kind, value_json, authority, "
                "valid_from, valid_to, recorded_at, source_refs_json, "
                "supersedes, status, revision) VALUES (?,?,?,?,?,?,?,?,?,?,?,0)",
                (
                    new_fact_id,
                    user_id,
                    old.kind,
                    value_json,
                    AcademicFact.FactAuthority.USER_DIRECT.value,
                    now_iso,
                    None,
                    now_iso,
                    json.dumps(list(old.source_refs)),
                    fact_id,
                    AcademicFact.FactStatus.CONFIRMED.value,
                ),
            ),
            # Fecha a validade do antigo (fato substituído não é atual, §7).
            (
                "UPDATE facts SET valid_to = ? WHERE id = ? AND user_id = ?",
                (now_iso, fact_id, user_id),
            ),
            self._supersedes_edge_by_ref(user_id, new_fact_id, ref_old),
        ]
        # Percurso dos dependentes (§15.1: "percorre dependentes, invalida
        # versões publicadas e reconstitui projeções") — BFS transitivo.
        invalidated = self._invalidation_statements(
            user_id, ref_old, reason, statements, seen={ref_old}
        )
        digest = _digest(
            {
                "fact_id": fact_id,
                "corrected_value": corrected_value,
                "reason": reason,
            }
        )
        receipt = self._effects.commit(
            CommitRequest(
                operation_id=operation_id or str(_uuid.uuid4()),
                user_id=user_id,
                action=ACTION_FACT_CORRECT,
                digest=digest,
                expected_version=self._store.domain_revision(user_id),
                event=EventSpec(
                    id=str(_uuid.uuid4()),
                    kind=EVENT_FACT_CORRECTED,
                    occurred_at=now_iso,
                    recorded_at=now_iso,
                    payload={
                        "new_fact_ref": fact_ref(new_fact_id, 0),
                        "old_fact_ref": ref_old,
                        "reason": reason,
                        "invalidated": list(invalidated),
                    },
                ),
                projection=tuple(statements),
            )
        )
        return CorrectionResult(
            new_fact_id=_uuid.UUID(new_fact_id),
            old_fact_id=old.fact_id,
            receipt=receipt,
            invalidated_refs=tuple(invalidated),
        )

    @staticmethod
    def _supersedes_edge_by_ref(
        user_id: str, new_fact_id: str, old_ref: str
    ) -> tuple[str, tuple[Any, ...]]:
        return (
            "INSERT OR IGNORE INTO artifact_dependencies(user_id, child_ref, "
            "parent_ref, relation) VALUES (?,?,?,'supersedes')",
            (user_id, fact_ref(new_fact_id, 0), old_ref),
        )

    def _invalidation_statements(
        self,
        user_id: str,
        trigger_ref: str,
        reason: str,
        statements: list[tuple[str, tuple[Any, ...]]],
        *,
        seen: set[str],
    ) -> list[str]:
        """Invalida dependentes do ``trigger_ref`` (§15.1): evento
        ``artifact_invalidated`` por dependente; resumo dependente tem
        ``verification='failed'`` (artefato derivado de fonte corrigida não
        permanece verificado). BFS transitivo pelos dois sentidos."""
        invalidated: list[str] = []
        frontier = [trigger_ref]
        while frontier:
            current = frontier.pop()
            children = self._store.dependents_of(user_id, current)
            for child in children:
                child_ref = child["child_ref"]
                if child_ref in seen:
                    continue
                seen.add(child_ref)
                invalidated.append(child_ref)
                statements.append(
                    (
                        "INSERT INTO events(id, user_id, session_id, kind, "
                        "payload_json, occurred_at, recorded_at) "
                        "VALUES (?,?,NULL,?,?,?,?)",
                        (
                            str(_uuid.uuid4()),
                            user_id,
                            EVENT_ARTIFACT_INVALIDATED,
                            json.dumps(
                                {
                                    "artifact_ref": child_ref,
                                    "trigger_ref": current,
                                    "reason": reason,
                                },
                                sort_keys=True,
                            ),
                            _utc_iso(self._clock()),
                            _utc_iso(self._clock()),
                        ),
                    )
                )
                if child_ref.startswith("summary:"):
                    summary_id = child_ref.split(":", 1)[1].split("@", 1)[0]
                    statements.append(
                        (
                            "UPDATE summaries SET verification = 'failed', "
                            "revision = revision + 1 WHERE id = ? AND user_id = ?",
                            (summary_id, user_id),
                        )
                    )
                frontier.append(child_ref)
        return invalidated

    # -- deleção (§5/§10/§15.1) -------------------------------------------------

    def preview_delete(
        self, user_id: str, scope: str, *, ids: Sequence[str] = ()
    ) -> DeletePreview:
        """Preview da deleção (rota §10: ``validate_scope → preview``):
        lista refs e o prazo de backup pendente proposto."""
        scope_events, scope_facts, scope_summaries = self._delete_scope(
            user_id, scope, ids=ids
        )
        return DeletePreview(
            scope=scope,
            event_ids=tuple(event_ref(eid) for eid in scope_events),
            fact_ids=tuple(
                fact_ref(fid, self._fact_row(user_id, fid)["revision"])
                for fid in scope_facts
            ),
            summary_ids=tuple(summary_ref(sid, 1) for sid in scope_summaries),
            backup_pending_until=self._backup_pending_until(scope, self._clock),
        )

    @staticmethod
    def _backup_pending_until(scope: str, clock: Any) -> str | None:
        """Backup identificado como pendente até expiração (§5/§15.1):
        retenção proposta de 30 dias (default de ensaio) para escopos
        parciais; deleção de todos os dados de memória do usuário conteria
        apenas esse usuário no backup — remoção já na solicitação
        (``None``)."""
        if scope == "all":
            return None
        return _utc_iso(clock() + timedelta(days=BACKUP_RETENTION_DAYS))

    def _delete_scope(
        self, user_id: str, scope: str, *, ids: Sequence[str] = ()
    ) -> tuple[list[str], list[str], list[str]]:
        if scope not in ("events", "facts", "summaries", "all"):
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"escopo de deleção inválido: {scope!r} (mapa §10: "
                "validate_scope)",
                diagnostic=_DIAGNOSTIC,
            )
        wanted = [str(i) for i in ids]
        events: list[str] = []
        facts: list[str] = []
        summaries: list[str] = []
        if scope in ("events", "all"):
            rows = self._store.fetch_user_rows(
                "SELECT id FROM events WHERE user_id = ? AND payload_json "
                "IS NOT NULL",
                (user_id,),
            )
            events = [str(r["id"]) for r in rows if not wanted or str(r["id"]) in wanted]
        if scope in ("facts", "all"):
            rows = self._store.fetch_user_rows(
                "SELECT id FROM facts WHERE user_id = ?", (user_id,)
            )
            facts = [str(r["id"]) for r in rows if not wanted or str(r["id"]) in wanted]
        if scope in ("summaries", "all"):
            rows = self._store.fetch_user_rows(
                "SELECT id FROM summaries WHERE user_id = ?", (user_id,)
            )
            summaries = [
                str(r["id"]) for r in rows if not wanted or str(r["id"]) in wanted
            ]
        return events, facts, summaries

    def delete_data(
        self,
        *,
        user_id: str,
        scope: str,
        confirmed: bool,
        reason: str,
        ids: Sequence[str] = (),
        operation_id: str | None = None,
    ) -> DeleteResult:
        """Deleção confirmada (§5/§15.1): purge de payloads de eventos sem
        hash reversível, tombstones **sem payload**, invalidação de
        dependentes por ``artifact_dependencies`` e reconstituição das
        projeções.

        ``confirmed=False`` é recusa tipada — a rota do §10 exige preview →
        confirm antes do commit/invalidate.
        """
        if not confirmed:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "deleção exige confirmação explícita (mapa §10: preview → "
                "confirm → commit/invalidate)",
                diagnostic=_DIAGNOSTIC,
            )
        preview = self.preview_delete(user_id, scope, ids=ids)
        clock_fn = self._clock
        now = clock_fn()
        now_iso = _utc_iso(now)
        backup_pending_until = self._backup_pending_until(scope, clock_fn)
        statements: list[tuple[str, tuple[Any, ...]]] = []
        tombstoned: list[str] = []

        # Eventos: purge sem hash reversível do texto excluído (§5) — o
        # payload vira NULL e o gatilho ``events_no_undrop_payload`` impede
        # restauração; tombstone cataloga a exclusão (sem payload).
        event_ids = [ref.split(":", 1)[1].split("@", 1)[0] for ref in preview.event_ids]
        if event_ids:
            placeholders = ",".join("?" for _ in event_ids)
            statements.append(
                (
                    f"UPDATE events SET payload_json = NULL, purged_at = ?, "
                    f"purge_reason = ? WHERE user_id = ? AND id IN ({placeholders})",
                    (now_iso, reason, user_id, *event_ids),
                )
            )
            for eid in event_ids:
                ref = event_ref(eid)
                tombstoned.append(ref)
                statements.append(self._tombstone(user_id, ref, "event", reason, now_iso, backup_pending_until))

        # Fatos: linha removida; tombstone (ref, sem payload) impede
        # ressurreição e identifica o backup pendente.
        fact_refs = list(preview.fact_ids)
        for ref in fact_refs:
            tombstoned.append(ref)
            statements.append(self._tombstone(user_id, ref, "fact", reason, now_iso, backup_pending_until))
        if fact_refs:
            fact_ids = [ref.split(":", 1)[1].split("@", 1)[0] for ref in fact_refs]
            placeholders = ",".join("?" for _ in fact_ids)
            statements.append(
                (
                    f"DELETE FROM facts WHERE user_id = ? AND id IN ({placeholders})",
                    (user_id, *fact_ids),
                )
            )

        # Resumos: artefatos derivados removidos com tombstone.
        summary_refs = list(preview.summary_ids)
        seen: set[str] = {ref for ref in summary_refs}
        for ref in summary_refs:
            statements.append(self._tombstone(user_id, ref, "summary", reason, now_iso, backup_pending_until))
            statements.append(
                (
                    "DELETE FROM summaries WHERE id = ? AND user_id = ?",
                    (ref.split(":", 1)[1].split("@", 1)[0], user_id),
                )
            )
            tombstoned.append(ref)
        invalidated: list[str] = []
        for ref in list(summary_refs) + fact_refs + [event_ref(eid) for eid in event_ids]:
            invalidated.extend(
                self._invalidation_statements(
                    user_id, ref, reason, statements, seen=seen
                )
            )
        # §5: "deleção propaga a todos os derivados" — resumos dependentes
        # descobertos no percurso são REMOVIDOS (com tombstone), não apenas
        # invalidados: claims derivados de payload excluído não sobrevivem.
        for ref in invalidated:
            if not ref.startswith("summary:"):
                continue
            summary_id = ref.split(":", 1)[1].split("@", 1)[0]
            statements.append(self._tombstone(user_id, ref, "summary", reason, now_iso, backup_pending_until))
            statements.append(
                (
                    "DELETE FROM summaries WHERE id = ? AND user_id = ?",
                    (summary_id, user_id),
                )
            )
            tombstoned.append(ref)

        digest = _digest(
            {"scope": scope, "ids": sorted(want for want in ids), "reason": reason}
        )
        receipt = self._effects.commit(
            CommitRequest(
                operation_id=operation_id or str(_uuid.uuid4()),
                user_id=user_id,
                action=ACTION_DATA_DELETE,
                digest=digest,
                expected_version=self._store.domain_revision(user_id),
                event=EventSpec(
                    id=str(_uuid.uuid4()),
                    kind="data_deleted",
                    occurred_at=now_iso,
                    recorded_at=now_iso,
                    payload={
                        "scope": scope,
                        "reason": reason,
                        "tombstones": list(tombstoned),
                        "invalidated": invalidated,
                        "backup_pending_until": backup_pending_until,
                    },
                ),
                projection=tuple(statements),
            )
        )
        # Reconstitui projeções (§15.1): topic_states recalculados desde os
        # registros restantes (projeções são reconstruíveis, §5).
        reconstituted = self.reconstitute_topic_states(user_id) if scope in (
            "events",
            "all",
        ) else False
        return DeleteResult(
            receipt=receipt,
            tombstoned_refs=tuple(tombstoned),
            invalidated_refs=tuple(invalidated),
            backup_pending_until=backup_pending_until,
            projections_reconstituted=reconstituted,
        )

    @staticmethod
    def _tombstone(
        user_id: str,
        ref: str,
        kind: str,
        reason: str,
        now_iso: str,
        backup_pending_until: str | None,
    ) -> tuple[str, tuple[Any, ...]]:
        # Tombstone SEM payload (§5/§15.1): ref + motivo + instante; nenhum
        # hash reversível do texto excluído.
        return (
            "INSERT INTO tombstones(id, user_id, artifact_ref, kind, reason, "
            "tombstoned_at, backup_pending_until) VALUES (?,?,?,?,?,?,?)",
            (
                str(_uuid.uuid4()),
                user_id,
                ref,
                kind,
                reason,
                now_iso,
                backup_pending_until,
            ),
        )

    def reconstitute_topic_states(self, user_id: str) -> bool:
        """Reconstitui ``topic_states`` desde os registros restantes (§15.1:
        "reconstitui projeções"; §5: projeções são reconstruíveis). Import
        local evita ciclo de importação (assessment não depende daqui)."""
        from eduagent.services.assessment import (
            AssessmentService,
            compute_topic_states,
        )

        service = AssessmentService(self._store, self._effects)
        attempts_facts, assessments_facts = service.load_facts(user_id)
        with self._store.read_transaction() as conn:
            revisions = {
                _uuid.UUID(r["topic_id"]): int(r["revision"])
                for r in conn.execute(
                    "SELECT topic_id, revision FROM topic_states WHERE user_id = ?",
                    (user_id,),
                ).fetchall()
            }
        states = compute_topic_states(
            attempts_facts, assessments_facts, revision_by_topic=revisions
        )
        statements: list[tuple[str, tuple[Any, ...]]] = [
            (
                "INSERT INTO topic_states(user_id, topic_id, revision, "
                "payload_json) VALUES (?,?,?,?) ON CONFLICT(user_id, topic_id) "
                "DO UPDATE SET revision = excluded.revision, payload_json = "
                "excluded.payload_json",
                (
                    user_id,
                    str(topic_id),
                    state.revision,
                    state.model_dump_json(),
                ),
            )
            for topic_id, state in states.items()
        ]
        if statements:
            self._store.execute_write(user_id, statements)
        # Executou (mesmo sem estados a projetar — sem tentativas, a
        # projeção vigente é vazia): a reconstituição aconteceu.
        return True

    # -- recuperação (§7) --------------------------------------------------------

    def retrieve(
        self,
        user_id: str,
        query: str,
        *,
        topic_ids: Sequence[str] = (),
        course_id: str | None = None,
        from_at: datetime | None = None,
        to_at: datetime | None = None,
        embedder: Any | None = None,
        token_counter: Any | None = None,
        include_superseded: bool = False,
        sender_role: SenderRole = SenderRole.LIBRARIAN,
    ) -> MemoryQueryResult:
        """``memory.query`` (§10): filtros usuário/disciplina/tópico/tempo →
        busca lexical+densa de rounds/eventos → até 8 originais em 2.048
        tokens + fatos atuais obrigatórios; correções relevantes substituem
        candidatos; similaridade **não** reativa fato superseded como atual;
        consulta de evidências antigas (``include_superseded=True``) traz
        versões anteriores explicitamente marcadas.

        ``embedder`` é o mesmo protocolo ``DenseEmbedder`` da 007 (embed
        normalizado, produto interno exato — sem ANN, extensão fora do
        MVP); sem embedder, só lexical (registrado em ``rankings``).
        """
        validate_tool_request(ToolName.MEMORY_QUERY, sender_role)
        if not query.strip():
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "consulta de memória vazia (mapa §4)",
                diagnostic=_DIAGNOSTIC,
            )
        if len(query) > 512:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                f"consulta com {len(query)} caracteres excede o limite do "
                "contrato (512; mapa §4)",
                diagnostic=_DIAGNOSTIC,
            )
        from eduagent.services.retrieval import HeuristicTokenCounter, tokenize

        counter = token_counter or HeuristicTokenCounter()
        rows = self._store.fetch_user_rows(
            "SELECT id, kind, payload_json, occurred_at, recorded_at, "
            "session_id FROM events WHERE user_id = ? AND payload_json IS "
            "NOT NULL AND kind != ? ORDER BY rowid",
            (user_id, EVENT_SUMMARY_PUBLISHED),
        )
        events: list[EventRow] = []
        for row in rows:
            occurred = _parse_iso(str(row["occurred_at"]))
            if from_at is not None and occurred < from_at:
                continue
            if to_at is not None and occurred > to_at:
                continue
            payload = json.loads(str(row["payload_json"]))
            if topic_ids and not _payload_matches_topics(payload, topic_ids):
                continue
            if course_id and payload.get("course_id") != course_id:
                continue
            events.append(
                EventRow(
                    event_id=_uuid.UUID(str(row["id"])),
                    kind=str(row["kind"]),
                    payload=payload,
                    occurred_at=occurred,
                    recorded_at=_parse_iso(str(row["recorded_at"])),
                    session_id=row["session_id"],
                )
            )
        rankings: list[str] = []
        if not events:
            selected: list[EventRow] = []
        else:
            rankings.append("lexical")
            lexical = self._lexical_ranking(query, events, tokenize)
            dense: list[str] = []
            if embedder is not None:
                rankings.append("dense")
                dense = self._dense_ranking(query, events, embedder)
            from eduagent.services.retrieval import rrf_merge

            merged = rrf_merge([lexical, dense])
            selected = self._select_originals(
                merged, events, counter
            )
            selected = self._apply_corrections(selected, events)
        current = self.current_facts(user_id)
        pack = self.build_memory_pack(user_id, selected, current_facts=current)
        historical: tuple[HistoricalFact, ...] = ()
        if include_superseded:
            by_entity: dict[_uuid.UUID, list[HistoricalFact]] = {}
            for fact in current:
                by_entity.setdefault(fact.entity_id, [])
            for fact in self._store_facts(user_id):
                if fact.superseded:
                    successor = self._successor_of(user_id, str(fact.fact_id))
                    by_entity.setdefault(fact.entity_id, []).append(
                        HistoricalFact(fact=fact, superseded_by=successor)
                    )
            historical = tuple(
                item
                for _, group in sorted(by_entity.items(), key=lambda kv: str(kv[0]))
                for item in group
            )
        return MemoryQueryResult(
            pack=pack,
            selected_events=tuple(selected),
            historical_facts=historical,
            rankings=tuple(rankings),
        )

    def _store_facts(self, user_id: str) -> list[FactRecord]:
        rows = self._store.fetch_user_rows(
            "SELECT id FROM facts WHERE user_id = ?", (user_id,)
        )
        records: list[FactRecord] = []
        for row in rows:
            record = self._fact_record(user_id, str(row["id"]))
            if record is not None:
                records.append(record)
        return records

    def _successor_of(self, user_id: str, fact_id: str) -> str | None:
        rows = self._store.fetch_user_rows(
            "SELECT id, revision FROM facts WHERE user_id = ? AND supersedes = ?",
            (user_id, fact_id),
        )
        if not rows:
            return None
        return fact_ref(str(rows[0]["id"]), int(rows[0]["revision"]))

    def _lexical_ranking(
        self, query: str, events: list[EventRow], tokenize: Any
    ) -> list[str]:
        """Ranking BM25 top-k (§6.5/§7). Diferente da busca documental
        (§6.8, com abstinência), a consulta de memória é filtro+ordenação:
        scores ≤ 0 (IDF negativo quando o termo está em todos os documentos)
        permanecem no ranking — a recuperação não pode esvaziar por causa da
        frequência do termo; empate resolvido pelo ID (determinismo)."""
        corpus = [tokenize(self._event_text(event)) for event in events]
        if not any(corpus):
            return []
        bm25 = BM25Okapi(corpus, k1=_BM25_K1, b=_BM25_B)
        scores = bm25.get_scores(tokenize(query))
        ranked = sorted(
            (
                (str(event.event_id), float(score))
                for event, score in zip(events, scores)
            ),
            key=lambda item: (-item[1], item[0]),
        )
        return [eid for eid, _ in ranked]

    def _dense_ranking(
        self, query: str, events: list[EventRow], embedder: Any
    ) -> list[str]:
        """Ranking denso com produto interno exato (§6.5/§7; sem ANN)."""
        if not events:
            return []
        vectors = embedder.embed([self._event_text(event) for event in events])
        query_vector = np.asarray(embedder.embed([query])[0], dtype=float)
        scored = sorted(
            (
                (str(event.event_id), float(np.dot(np.asarray(vector, dtype=float), query_vector)))
                for event, vector in zip(events, vectors)
            ),
            key=lambda item: (-item[1], item[0]),
        )
        return [eid for eid, _ in scored]

    @staticmethod
    def _event_text(event: EventRow) -> str:
        payload = event.payload or {}
        return json.dumps(
            {
                "kind": event.kind,
                "occurred_at": _utc_iso(event.occurred_at),
                "payload": payload,
            },
            sort_keys=True,
            ensure_ascii=False,
        )

    def _select_originals(
        self,
        merged: list[tuple[str, float]],
        events: list[EventRow],
        counter: Any,
    ) -> list[EventRow]:
        """Até 8 originais dentro de 2.048 tokens (§7), em ordem de ranking."""
        by_id = {str(event.event_id): event for event in events}
        selected: list[EventRow] = []
        used = 0
        for event_id, _ in merged:
            if len(selected) >= MEMORY_MAX_ORIGINALS:
                break
            event = by_id.get(event_id)
            if event is None or event.purged:
                continue
            tokens = counter.count(self._event_text(event))
            if used + tokens > MEMORY_TOKEN_BUDGET:
                continue
            selected.append(event)
            used += tokens
        return selected

    def _apply_corrections(
        self, selected: list[EventRow], events: list[EventRow]
    ) -> list[EventRow]:
        """Correções relevantes substituem candidatos (§7): evento de
        correção/invalidação posterior que referencie o evento selecionado
        (``trigger_ref``/``corrects_event_ref`` no payload) entra no lugar
        dele — o candidato corrigido não é exibido sem a correção."""
        corrections: dict[str, EventRow] = {}
        for event in events:
            payload = event.payload or {}
            trigger = payload.get("trigger_ref") or payload.get(
                "corrects_event_ref"
            )
            if trigger and event.kind in (
                EVENT_ARTIFACT_INVALIDATED,
                EVENT_FACT_CORRECTED,
            ):
                corrections.setdefault(trigger, event)
        replaced: list[EventRow] = []
        used: set[str] = set()
        for event in selected:
            correction = corrections.get(event.ref)
            if correction is not None:
                if str(correction.event_id) in used:
                    continue  # correção já presente — não duplicar
                replaced.append(correction)
                used.add(str(correction.event_id))
            else:
                replaced.append(event)
                used.add(str(event.event_id))
        return replaced

    # -- pacote de memória (contrato MemoryPack, §4/§7) ---------------------------

    def build_memory_pack(
        self,
        user_id: str,
        events: Sequence[EventRow],
        *,
        current_facts: Sequence[FactRecord] | None = None,
    ) -> MemoryPack:
        facts = list(current_facts) if current_facts is not None else self.current_facts(user_id)
        with self._store.read_transaction() as conn:
            topic_rows = conn.execute(
                "SELECT payload_json FROM topic_states WHERE user_id = ?",
                (user_id,),
            ).fetchall()
            summary_rows = conn.execute(
                "SELECT id, source_event_ids_json, claims_json, verification, "
                "revision FROM summaries WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        topic_states = [
            TopicState.model_validate_json(str(row["payload_json"]))
            for row in topic_rows
        ]
        summaries = [
            MemoryPack.SummaryEntry(
                id=_uuid.UUID(str(row["id"])),
                source_event_ids=[
                    _uuid.UUID(eid)
                    for eid in json.loads(str(row["source_event_ids_json"]))
                ],
                claims=list(json.loads(str(row["claims_json"]))),
                verification=str(row["verification"]),  # type: ignore[arg-type]
                revision=int(row["revision"]),
            )
            for row in summary_rows
        ]
        return MemoryPack(
            snapshot_version=self._store.domain_revision(user_id),
            current_facts=[fact.to_academic_fact() for fact in facts],
            topic_state=topic_states,
            events=[
                MemoryPack.EventRecord(
                    id=event.event_id,
                    occurred_at=event.occurred_at,
                    recorded_at=event.recorded_at,
                    kind=event.pack_kind(),
                    help_level=(
                        int(help)
                        if (help := (event.payload or {}).get("help_level"))
                        is not None
                        else None
                    ),
                    source=MemoryPack.Origin(
                        (event.payload or {}).get("origin", "observed")
                    ),
                )
                for event in events
            ],
            contradictions=self.detect_contradictions(user_id, facts),
            summaries=summaries,
        )

    # -- síntese (§7) ---------------------------------------------------------

    def propose_synthesis(self, events: Sequence[EventRow]) -> SynthesisProposal:
        """Proposta determinística de síntese **a partir dos originais**
        (§7): um claim por evento com os elementos verificáveis (data,
        polaridade, ajuda, estado, números) e ``claim→event_ids``. Eventos
        ``summary_published`` são recusados — não encadear resumo de resumo.
        """
        for event in events:
            if event.kind == EVENT_SUMMARY_PUBLISHED:
                raise EduAgentError(
                    ErrorCode.SCHEMA_INVALID,
                    "síntese não pode ter resumo como fonte (mapa §7: não "
                    "encadear indefinidamente resumo de resumo)",
                    diagnostic=_DIAGNOSTIC,
                )
        claims: list[SynthesisClaim] = []
        for event in events:
            claims.append(SynthesisClaim(text=_claim_text(event), event_ids=(str(event.event_id),)))
        coverage_from = min((event.occurred_at for event in events), default=None)
        coverage_to = max((event.occurred_at for event in events), default=None)
        return SynthesisProposal(
            claims=tuple(claims),
            coverage_from=coverage_from,
            coverage_to=coverage_to,
            verification="pending",
        )

    def verify_synthesis(
        self, proposal: SynthesisProposal, events: Sequence[EventRow]
    ) -> SynthesisProposal:
        """Verificação exata dos claims (§7: "checar exatamente datas,
        números, polaridade, ajuda e estado") contra os originais; claim sem
        suporte falha — falha **mantém os originais** (a síntese não é
        publicada)."""
        sources = [self._event_text(event) for event in events]
        failed: list[str] = []
        for claim in proposal.claims:
            known = {str(event.event_id) for event in events}
            if not claim.event_ids or any(
                event_id not in known for event_id in claim.event_ids
            ):
                failed.append(claim.text)
                continue
            if not verify_claim_against_sources(claim.text, sources):
                failed.append(claim.text)
        verification = "verified" if not failed else "failed"
        return SynthesisProposal(
            claims=proposal.claims,
            coverage_from=proposal.coverage_from,
            coverage_to=proposal.coverage_to,
            verification=verification,
            failed_claims=tuple(failed),
        )

    def publish_synthesis(
        self,
        *,
        user_id: str,
        proposal: SynthesisProposal,
        operation_id: str | None = None,
    ) -> Receipt:
        """Publica síntese **verificada** como artefato derivado (§7):
        linha em ``summaries`` + evento ``summary_published`` + arestas
        ``derived_from`` para cada evento fonte. Nenhum evento é apagado —
        compactação nunca remove originais (§7). Síntese não verificada é
        recusada (falha mantém originais ou pede divisão)."""
        if not proposal.verified:
            raise EduAgentError(
                ErrorCode.SCHEMA_INVALID,
                "síntese não verificada não é publicada (mapa §7); mantenha "
                "os originais ou divida a consulta",
                diagnostic=_DIAGNOSTIC,
            )
        summary_id = str(_uuid.uuid4())
        now_iso = _utc_iso(self._clock())
        statements: list[tuple[str, tuple[Any, ...]]] = [
            (
                "INSERT INTO summaries(id, user_id, source_event_ids_json, "
                "claims_json, verification, revision) VALUES (?,?,?,?,?,1)",
                (
                    summary_id,
                    user_id,
                    json.dumps(
                        [eid for claim in proposal.claims for eid in claim.event_ids]
                    ),
                    json.dumps([claim.text for claim in proposal.claims]),
                    "verified",
                ),
            )
        ]
        for claim in proposal.claims:
            for event_id in claim.event_ids:
                statements.append(
                    (
                        "INSERT OR IGNORE INTO artifact_dependencies(user_id, "
                        "child_ref, parent_ref, relation) VALUES "
                        "(?,?,?,'derived_from')",
                        (user_id, summary_ref(summary_id, 1), event_ref(event_id)),
                    )
                )
        digest = _digest(
            {"summary_id": summary_id, "claims": [c.text for c in proposal.claims]}
        )
        return self._effects.commit(
            CommitRequest(
                operation_id=operation_id or str(_uuid.uuid4()),
                user_id=user_id,
                action=ACTION_EVENT_APPEND,
                digest=digest,
                expected_version=self._store.domain_revision(user_id),
                event=EventSpec(
                    id=str(_uuid.uuid4()),
                    kind=EVENT_SUMMARY_PUBLISHED,
                    occurred_at=now_iso,
                    recorded_at=now_iso,
                    payload={"summary_ref": summary_ref(summary_id, 1)},
                ),
                projection=tuple(statements),
            )
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _payload_matches_topics(payload: dict[str, Any], topic_ids: Sequence[str]) -> bool:
    event_topics = payload.get("topic_ids")
    if not isinstance(event_topics, list):
        return False  # filtro de tópico exige tópico declarado no evento
    return bool(set(str(t) for t in event_topics) & set(topic_ids))


def _claim_text(event: EventRow) -> str:
    """Claim determinístico do proposer com elementos verificáveis (data do
    evento, kind, polaridade/ajuda quando o payload os traz — §7)."""
    payload = event.payload or {}
    parts = [
        f"Em {event.occurred_at.date().isoformat()}",
        f"evento {event.kind}",
    ]
    correctness = payload.get("assessment", {}).get("correctness") if isinstance(
        payload.get("assessment"), dict
    ) else payload.get("correctness")
    if correctness:
        parts.append(f"com resultado {correctness}")
    help_level = payload.get("help_level")
    if help_level is not None:
        parts.append(f"com ajuda nível {int(help_level)}")
    status = payload.get("status")
    if status:
        parts.append(f"com estado {status}")
    return ", ".join(parts) + "."


__all__ = [
    "ACTION_DATA_DELETE",
    "ACTION_EVENT_APPEND",
    "ACTION_FACT_CORRECT",
    "BACKUP_RETENTION_DAYS",
    "CorrectionResult",
    "DeletePreview",
    "DeleteResult",
    "EVENT_ARTIFACT_INVALIDATED",
    "EVENT_FACT_CORRECTED",
    "EVENT_SUMMARY_PUBLISHED",
    "EventRow",
    "FactRecord",
    "HistoricalFact",
    "MEMORY_MAX_ORIGINALS",
    "MEMORY_TOKEN_BUDGET",
    "MemoryQueryResult",
    "MemoryService",
    "SynthesisClaim",
    "SynthesisProposal",
    "event_ref",
    "fact_ref",
    "summary_ref",
]
