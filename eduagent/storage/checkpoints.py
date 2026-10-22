"""Checkpointer SQLite persistente separado do DB de domínio (mapa §10:
``durability=sync``, ``thread_id`` por sessão).

Contratos implementados:

- **durability=sync**: conexão SQLite com ``PRAGMA synchronous=FULL`` —
  cada checkpoint sobrevive a queda do processo (WAL no modo corrigido,
  mapa §3). O DB de checkpoints é **separado** do DB de domínio (mapa §4/§11:
  "Checkpoint em DB separado não é atômico").
- **thread_id por sessão**: o ``thread_id`` do LangGraph é o
  ``session_id`` — cada sessão tem seu histórico de checkpoints e a
  retomada de interrupt reconstrói o nó desde o início (mapa §10).
- **Guarda refs, não PDFs integrais** (mapa §4): o estado serializado é o
  estado do grafo (refs ``ID+versão`` e dados textuais de turno). Originais
  e PDFs vivem no DB de domínio/arquivos — o estado de domínio é autoridade
  e o checkpoint não substitui commit (§11): replay consulta a operação
  autoritativa e reutiliza o recibo.

Implementa ``BaseCheckpointSaver`` do LangGraph (task 002 pina ``langgraph``)
com o serializador do próprio LangGraph (``JsonPlusSerializer``). Os métodos
assíncronos delegam aos síncronos: o MVP é local/loopback sem concorrência
em rede (mapa §1).
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional, Sequence

from langgraph.checkpoint.base import (
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    ChannelVersions,
    PendingWrite,
    RunnableConfig,
    SerializerProtocol,
    JsonPlusSerializer,
    BaseCheckpointSaver,
    get_checkpoint_id,
    writes_sort_key,
)

DIAGNOSTIC = "eduagent/storage/checkpoints.py"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    checkpoint_type TEXT NOT NULL,
    checkpoint_blob BLOB NOT NULL,
    metadata_type TEXT NOT NULL,
    metadata_blob BLOB NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (thread_id, checkpoint_id)
);
CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    task_path TEXT NOT NULL DEFAULT '',
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BLOB,
    PRIMARY KEY (thread_id, checkpoint_id, task_id, task_path, idx)
);
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread
    ON checkpoints (thread_id, created_at DESC, checkpoint_id DESC);
"""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteCheckpointer(BaseCheckpointSaver):
    """Checkpointer SQLite com ``durability=sync`` e ``thread_id`` por
    sessão (mapa §10). Persistente entre processos; arquivo separado do DB
    de domínio (``data/checkpoints.sqlite``, mapa §3).

    ``synchronous=FULL`` é durability=sync efetivo; WAL dá leitores
    concorrentes sem violar a serialização do escritor único (§5). Escrita
    de checkpoint e writes usa transações curtas (§5).
    """

    def __init__(
        self,
        path: Path | str,
        *,
        serde: SerializerProtocol | None = None,
    ) -> None:
        super().__init__(serde=serde or JsonPlusSerializer())
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            str(self._path), check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        # durability=sync (mapa §10): cada commit espera o fsync do SO/disco.
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _thread_id(config: RunnableConfig) -> str:
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            raise ValueError("checkpointer exige thread_id (sessão)")
        return str(thread_id)

    def _config_with_id(
        self, config: RunnableConfig, checkpoint_id: str | None
    ) -> RunnableConfig:
        if checkpoint_id is None:
            return config
        return {
            **config,
            "configurable": {
                **config.get("configurable", {}),
                "checkpoint_id": checkpoint_id,
            },
        }

    def _load_writes(
        self, thread_id: str, checkpoint_id: str
    ) -> list[PendingWrite]:
        rows = self._conn.execute(
            "SELECT task_id, task_path, idx, channel, type, blob "
            "FROM checkpoint_writes WHERE thread_id = ? AND checkpoint_id = ?",
            (thread_id, checkpoint_id),
        ).fetchall()
        enriched = sorted(
            rows,
            key=lambda row: (
                str(row["task_path"]),
                str(row["task_id"]),
                int(row["idx"]),
            ),
        )
        return [
            (
                str(row["task_id"]),
                str(row["channel"]),
                self.serde.loads_typed((str(row["type"]), row["blob"]))
                if row["type"] is not None
                else None,
            )
            for row in enriched
        ]

    # -- BaseCheckpointSaver (síncrono) ---------------------------------------

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id = self._thread_id(config)
        checkpoint_id = get_checkpoint_id(config)
        with self._lock:
            if checkpoint_id:
                row = self._conn.execute(
                    "SELECT * FROM checkpoints WHERE thread_id = ? AND "
                    "checkpoint_id = ?",
                    (thread_id, checkpoint_id),
                ).fetchone()
            else:
                row = self._conn.execute(
                    "SELECT * FROM checkpoints WHERE thread_id = ? "
                    "ORDER BY checkpoint_id DESC LIMIT 1",
                    (thread_id,),
                ).fetchone()
            if row is None:
                return None
            pending_writes = self._load_writes(
                thread_id, str(row["checkpoint_id"])
            )
        checkpoint: Checkpoint = self.serde.loads_typed(
            (str(row["checkpoint_type"]), row["checkpoint_blob"])
        )
        metadata: CheckpointMetadata = self.serde.loads_typed(
            (str(row["metadata_type"]), row["metadata_blob"])
        )
        parent_id = row["parent_checkpoint_id"]
        return CheckpointTuple(
            config=self._config_with_id(config, str(row["checkpoint_id"])),
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=(
                self._config_with_id(config, str(parent_id))
                if parent_id
                else None
            ),
            pending_writes=pending_writes,
        )

    def list(  # type: ignore[override]
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        thread_id = (
            str(self._thread_id(config))
            if config and config.get("configurable", {}).get("thread_id")
            else None
        )
        query = (
            "SELECT thread_id, checkpoint_id, parent_checkpoint_id, "
            "checkpoint_type, checkpoint_blob, metadata_type, metadata_blob "
            "FROM checkpoints "
            + ("WHERE thread_id = ? " if thread_id else "")
            + "ORDER BY checkpoint_id DESC"
        )
        params: tuple[Any, ...] = (thread_id,) if thread_id else ()
        if limit is not None:
            query += " LIMIT ?"
            params = params + (limit,)
        rows = self._conn.execute(query, params).fetchall()
        for row in rows:
            if filter:
                metadata = self.serde.loads_typed(
                    (str(row["metadata_type"]), row["metadata_blob"])
                )
                if any(metadata.get(k) != v for k, v in filter.items()):
                    continue
            if before is not None:
                before_id = get_checkpoint_id(before)
                if before_id and str(row["checkpoint_id"]) >= str(before_id):
                    continue
            base_config: RunnableConfig = {"configurable": {"thread_id": row["thread_id"]}}
            checkpoint = self.serde.loads_typed(
                (str(row["checkpoint_type"]), row["checkpoint_blob"])
            )
            metadata = self.serde.loads_typed(
                (str(row["metadata_type"]), row["metadata_blob"])
            )
            parent_id = row["parent_checkpoint_id"]
            yield CheckpointTuple(
                config=self._config_with_id(
                    base_config, str(row["checkpoint_id"])
                ),
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=(
                    self._config_with_id(base_config, str(parent_id))
                    if parent_id
                    else None
                ),
            )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id = self._thread_id(config)
        checkpoint_id = str(checkpoint["id"])
        parent_id = config.get("configurable", {}).get("checkpoint_id")
        cp_type, cp_blob = self.serde.dumps_typed(checkpoint)
        md_type, md_blob = self.serde.dumps_typed(metadata)
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO checkpoints (thread_id, "
                "checkpoint_id, parent_checkpoint_id, checkpoint_type, "
                "checkpoint_blob, metadata_type, metadata_blob, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    thread_id,
                    checkpoint_id,
                    str(parent_id) if parent_id else None,
                    cp_type,
                    cp_blob,
                    md_type,
                    md_blob,
                    _utc_now_iso(),
                ),
            )
            self._conn.commit()
        return self._config_with_id(config, checkpoint_id)

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = self._thread_id(config)
        checkpoint_id = get_checkpoint_id(config)
        if checkpoint_id is None:
            raise ValueError(
                "put_writes exige checkpoint_id no config (thread em curso)"
            )
        with self._lock:
            for idx, (channel, value) in enumerate(writes):
                type_, blob = self.serde.dumps_typed(value)
                self._conn.execute(
                    "INSERT OR REPLACE INTO checkpoint_writes (thread_id, "
                    "checkpoint_id, task_id, task_path, idx, channel, type, "
                    "blob) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        thread_id,
                        str(checkpoint_id),
                        task_id,
                        task_path,
                        idx,
                        channel,
                        type_,
                        blob,
                    ),
                )
            self._conn.commit()

    def delete_thread(self, thread_id: str) -> None:
        """Deleção em cascata inclui checkpoints (§5: "Deleção propaga a
        todos os derivados, checkpoints e traces") — chamada pela deleção de
        dados do usuário (task 010/014)."""
        with self._lock:
            self._conn.execute(
                "DELETE FROM checkpoint_writes WHERE thread_id = ?",
                (thread_id,),
            )
            self._conn.execute(
                "DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,)
            )
            self._conn.commit()

    # -- síncrono→assíncrono (MVP local: sem concorrência em rede, §1) --------

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return self.get_tuple(config)

    async def aput(  # type: ignore[override]
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        return self.put(config, checkpoint, metadata, new_versions)

    async def aput_writes(  # type: ignore[override]
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        self.put_writes(config, writes, task_id, task_path)

    async def alist(  # type: ignore[override]
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        return self.list(config, filter=filter, before=before, limit=limit)

    async def adelete_thread(self, thread_id: str) -> None:
        self.delete_thread(thread_id)

    # -- integridade (backup/restore, §5) ------------------------------------

    def integrity_check(self) -> str:
        row = self._conn.execute("PRAGMA integrity_check").fetchone()
        return str(row[0])

    def close(self) -> None:
        with self._lock:
            self._conn.close()


__all__ = ["SQLiteCheckpointer"]
