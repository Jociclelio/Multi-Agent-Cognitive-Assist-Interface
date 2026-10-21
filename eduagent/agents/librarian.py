"""Agente Bibliotecário: memória temporal, recuperação e projeções
(mapa normativo §7, §10, §13.6; task 010).

Contratos implementados:

- **Ferramenta ``memory.query``** (tabela §10): só o papel Bibliotecário
  pode propor — a permissão é validada por ``validate_tool_request``
  (task 003) e JSON correto para ação proibida é negado por código
  (``TOOL_DENIED``). Pré-condição da tabela: "usuário/tópico/tempo";
  resultado: "versão e correções" — o pacote devolve a projeção vigente
  (fatos atuais), correções recentes e, quando pedido, versões anteriores
  **explicitamente marcadas** como anteriores.
- **"Atual" recupera projeção vigente e correções (§7)**: fatos com
  sucessor ativo ou validade fechada nunca aparecem como atuais — a
  exclusão é estrutural (grafo ``supersedes`` + ``valid_to``), nunca de
  ranking: **similaridade não reativa fato superseded**.
- **"Como mudou" recupera versões em ordem temporal (§7)**: histórico da
  entidade por ``recorded_at``, incluindo versões substituídas.
- **Contradição não conciliada (§7)**: devolve **ambos** os registros na
  ``MemoryPack.contradictions`` com ``pending=True`` — nada é conciliado
  silenciosamente.
- **Preferência declarada não é evidência de aprendizagem (§7)**: eventos
  de preferência/autorrelato são registros de memória; nenhum caminho daqui
  atualiza competência (``TopicState``) — só o redutor com assessments
  aceitos o faz (§8).

O Bibliotecário não recebe shell genérico nem escrita direta no DB (§10):
toda escrita passa pelos serviços (commit idempotente, §11).
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from typing import Any, Sequence

from eduagent.contracts import (
    MemoryPack,
    SenderRole,
    validate_tool_request,
)
from eduagent.services.memory import (
    FactRecord,
    HistoricalFact,
    MemoryQueryResult,
    MemoryService,
)

_DIAGNOSTIC = "eduagent/agents/librarian.py"


class Librarian:
    """Bibliotecário: ``memory.query`` e projeções de memória (mapa §7/§10)."""

    def __init__(self, memory: MemoryService) -> None:
        self._memory = memory

    # -- memory.query (§10: pré-condição usuário/tópico/tempo) -----------------

    def memory_query(
        self,
        user_id: str,
        query: str,
        *,
        topic_ids: Sequence[str] = (),
        course_id: str | None = None,
        from_at: datetime | None = None,
        to_at: datetime | None = None,
        include_superseded: bool = False,
        embedder: Any | None = None,
        sender_role: SenderRole = SenderRole.LIBRARIAN,
    ) -> MemoryQueryResult:
        """Ferramenta ``memory.query`` (mapa §10): permissão validada pelo
        papel (payload não muda permissões, §4); recuperação temporal do
        §7 com até 8 originais em 2.048 tokens + fatos atuais obrigatórios.

        ``include_superseded=True`` é a consulta de evidências antigas:
        devolve versões anteriores explicitamente marcadas — nunca como
        atuais (§7)."""
        return self._memory.retrieve(
            user_id,
            query,
            topic_ids=topic_ids,
            course_id=course_id,
            from_at=from_at,
            to_at=to_at,
            include_superseded=include_superseded,
            embedder=embedder,
            sender_role=sender_role,
        )

    # -- "atual": projeção vigente + correções (§7) -----------------------------

    def current_memory(self, user_id: str) -> MemoryPack:
        """Memória atual (§7): fatos atuais obrigatórios (projeção vigente,
        já corrigida — fato substituído não aparece), estados de tópico
        projetados e contradições pendentes, se houver."""
        return self._memory.build_memory_pack(user_id, [])

    def current_facts(self, user_id: str) -> list[FactRecord]:
        """Projeção vigente dos fatos (§7)."""
        return self._memory.current_facts(user_id)

    # -- "como mudou": versões em ordem temporal (§7) ----------------------------

    def how_changed(
        self, user_id: str, entity_id: _uuid.UUID
    ) -> list[FactRecord]:
        """Versões da entidade em ordem temporal (§7), incluindo as
        substituídas (consulta de evidências antigas pode trazê-las
        explicitamente)."""
        return self._memory.fact_history(user_id, entity_id)

    def historical_versions(
        self, user_id: str, entity_id: _uuid.UUID
    ) -> list[HistoricalFact]:
        """Versões anteriores explícitas, com o sucessor de cada uma (§7)."""
        return self._memory.historical_facts(user_id, entity_id)


__all__ = ["Librarian"]
