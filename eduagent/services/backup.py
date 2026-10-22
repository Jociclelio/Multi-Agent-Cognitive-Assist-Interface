"""Backup local, restore verificado e ciclo de tombstones (mapa §5, §15.1).

Contratos implementados (task 015):

- **Backup consistente (§5)**: "Backup inicial deve fechar escritores/
  checkpointer, consolidar e copiar um conjunto consistente com originais/
  manifesto." O serviço fecha o checkpointer e o escritor do domínio (com
  ``wal_checkpoint(TRUNCATE)`` antes do fechamento), copia os bancos SQLite
  e a árvore de arquivos de dados (originais, índices, exports, traces) e
  grava um manifesto com SHA-256 por arquivo.
- **Catálogo e expiração (§15.1)**: retenção PROPOSTA de 30 dias (default de
  ensaio — nunca apresentada como resultado medido); "Expiração deve ser
  verificada por job/manual doctor com relógio e catálogo" —
  ``expire_due(now)`` usa o relógio injetado e o catálogo JSON.
- **Exclusão ativa imediata (§15.1)**: na aplicação da deleção, backups que
  contêm APENAS o usuário excluído são REMOVIDOS já na solicitação; backups
  com outros usuários ficam identificados como pendentes até expiração.
- **Restore em diretório novo (§5)**: nunca sobrescreve o original; roda
  verificador de integridade (SHA-256 do manifesto, ``integrity_check``,
  replay idempotente das migrações) e confere que tombstones registrados
  continuam aplicados — o tombstone sem payload vale ANTES de liberar o
  restore (mapa §15.1: "Tombstone sem payload é aplicado **antes** de
  liberar restore").
- **Sem alegação de sanitização forense (§15.1)**: os relatórios mostram
  escopo/prazo; nada aqui alega apaga­mento forense de mídia.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import uuid as _uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from eduagent.contracts import ErrorCode, EduAgentError
from eduagent.storage.migrations import apply_migrations

DIAGNOSTIC = "eduagent/services/backup.py"

#: Retenção de backup PROPOSTA (mapa §5/§15.1): default de ensaio a calibrar
#: com o usuário — não é resultado medido nem decisão fechada.
BACKUP_RETENTION_DAYS = 30

_BACKUP_SCHEMA_VERSION = "1.0"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _error(code: ErrorCode, message: str) -> EduAgentError:
    return EduAgentError(code, message, diagnostic=DIAGNOSTIC)


@dataclass
class BackupEntry:
    """Entrada do catálogo de backups (§15.1: catálogo + relógio)."""

    backup_id: str
    created_at: str
    expires_at: str
    users: list[str]
    status: str  # active | pending_expiry | removed
    directory: str
    tombstone_count: int = 0
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BackupCatalog:
    """Catálogo JSON dos backups locais (§15.1: "com relógio e catálogo")."""

    def __init__(self, backup_root: Path | str, clock: Any = None) -> None:
        self._root = Path(backup_root)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._path = self._root / "catalog.json"
        self._entries: list[dict[str, Any]] = []
        self._load()

    # -- persistência --------------------------------------------------------

    def _load(self) -> None:
        if self._path.exists():
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._entries = list(data.get("entries") or [])
        else:
            self._entries = []

    def save(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(
                {
                    "schema_version": _BACKUP_SCHEMA_VERSION,
                    "updated_at": _utc_now_iso(),
                    "entries": self._entries,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    # -- consultas/mutações --------------------------------------------------

    def entries(self, *, status: str | None = None) -> list[dict[str, Any]]:
        if status is None:
            return list(self._entries)
        return [e for e in self._entries if e.get("status") == status]

    def add(self, entry: BackupEntry) -> dict[str, Any]:
        record = entry.to_dict()
        self._entries.append(record)
        return record

    def update(self, backup_id: str, **fields: Any) -> dict[str, Any]:
        for record in self._entries:
            if record.get("backup_id") == backup_id:
                record.update(fields)
                return record
        raise _error(
            ErrorCode.SOURCE_UNRESOLVED,
            f"backup {backup_id} não está no catálogo",
        )

    def remove_entry(self, backup_id: str) -> None:
        self._entries = [
            e for e in self._entries if e.get("backup_id") != backup_id
        ]

    def backups_containing_user(self, user_id: str) -> list[dict[str, Any]]:
        return [
            e
            for e in self._entries
            if e.get("status") in ("active", "pending_expiry")
            and user_id in (e.get("users") or [])
        ]

    def expire_due(self, now: datetime | None = None) -> list[str]:
        """Expiração verificada por relógio e catálogo (§15.1): backups com
        ``expires_at`` vencido são removidos do disco e marcados no catálogo.
        Nada é removido por heurística silenciosa: a decisão é só por data."""
        moment = now or self._clock()
        removed: list[str] = []
        for record in list(self._entries):
            if record.get("status") == "removed":
                continue
            expires = record.get("expires_at")
            if not expires:
                continue
            if moment >= datetime.fromisoformat(str(expires)):
                directory = Path(record.get("directory") or "")
                if directory.exists():
                    shutil.rmtree(directory, ignore_errors=True)
                record["status"] = "removed"
                record["removed_at"] = _utc_now_iso()
                removed.append(str(record.get("backup_id")))
        return removed


@dataclass
class BackupReport:
    """Relatório de backup/restore (escopo/prazo, sem alegação forense)."""

    backup_id: str
    status: str
    directory: str
    files: int
    bytes_total: int
    users: list[str]
    tombstone_count: int
    created_at: str
    expires_at: str
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BackupService:
    """Backup/restore do conjunto local (§5/§15.1). Requer o store e o
    checkpointer ABERTOS no momento da chamada: o serviço fecha os escritores
    (§5) — após ``create_backup`` o contexto da sessão precisa ser reaberto
    (a CLI reabre por comando)."""

    def __init__(
        self,
        *,
        store: Any,
        checkpointer: Any | None,
        data_root: Path | str,
        backup_root: Path | str,
        clock: Any = None,
    ) -> None:
        self._store = store
        self._checkpointer = checkpointer
        self._data_root = Path(data_root)
        self._backup_root = Path(backup_root)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.catalog = BackupCatalog(self._backup_root, clock=self._clock)

    # -- criação -------------------------------------------------------------

    def create_backup(self) -> BackupReport:
        """Fecha escritores/checkpointer, consolida e copia o conjunto
        consistente com manifesto SHA-256 (mapa §5)."""
        now = self._clock()
        created_at = _utc_now_iso()
        expires_at = (
            now + timedelta(days=BACKUP_RETENTION_DAYS)
        ).isoformat()
        # Estado de domínio lido ANTES de fechar os escritores (§5).
        users = [
            str(row["id"])
            for row in self._store.fetch_user_rows(
                "SELECT id FROM users ORDER BY id", ()
            )
        ]
        tombstones = [
            {
                "ref": str(row["artifact_ref"]),
                "kind": str(row["kind"]),
            }
            for row in self._store.fetch_user_rows(
                "SELECT artifact_ref, kind FROM tombstones ORDER BY rowid",
                (),
            )
        ]
        backup_id = str(_uuid.uuid4())
        target = self._backup_root / backup_id
        if target.exists():  # pragma: no cover — UUID colide
            raise _error(
                ErrorCode.INTERNAL_FAILURE,
                f"diretório de backup já existe: {target}",
            )
        # §5: fechar escritores/checkpointer — wal_checkpoint(TRUNCATE)
        # consolida o WAL no arquivo principal antes da cópia.
        if self._checkpointer is not None:
            self._checkpointer.checkpoint_wal()
            self._checkpointer.close()
        self._store.checkpoint_wal()
        self._store.close()
        # Conjunto consistente: bancos SQLite + árvore de arquivos de dados.
        files: dict[str, str] = {}
        bytes_total = 0
        selected: dict[Path, str] = {}  # caminho absoluto → nome relativo

        def add(source: Path) -> None:
            resolved = source.resolve()
            if resolved in selected or not source.exists():
                return
            if source.is_relative_to(self._data_root):
                relative = str(source.relative_to(self._data_root.parent))
            else:
                relative = source.name
            selected[resolved] = relative

        domain_path = Path(self._store.path)  # type: ignore[attr-defined]
        add(domain_path)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(domain_path) + suffix)
            if sidecar.exists() and sidecar.stat().st_size > 0:
                add(sidecar)
        if self._checkpointer is not None:
            add(Path(self._checkpointer.path))  # type: ignore[attr-defined]
        if self._data_root.exists():
            for candidate in sorted(self._data_root.rglob("*")):
                if candidate.is_file():
                    add(candidate)
        for source, relative in selected.items():
            dest = target / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            digest = _sha256(dest)
            files[relative] = digest
            bytes_total += dest.stat().st_size
        manifest = {
            "schema_version": _BACKUP_SCHEMA_VERSION,
            "backup_id": backup_id,
            "created_at": created_at,
            "expires_at": expires_at,
            "users": users,
            "tombstones": tombstones,
            "files": files,
        }
        (target / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        report = BackupReport(
            backup_id=backup_id,
            status="active",
            directory=str(target),
            files=len(files),
            bytes_total=bytes_total,
            users=users,
            tombstone_count=len(tombstones),
            created_at=created_at,
            expires_at=expires_at,
            note=(
                "retenção PROPOSTA de "
                f"{BACKUP_RETENTION_DAYS} dias (default de ensaio, §15.1); "
                "escopo/prazo exibidos — sem alegação de sanitização forense"
            ),
        )
        self.catalog.add(
            BackupEntry(
                backup_id=backup_id,
                created_at=created_at,
                expires_at=expires_at,
                users=users,
                status="active",
                directory=str(target),
                tombstone_count=len(tombstones),
            )
        )
        self.catalog.save()
        return report

    # -- verificação/restore -------------------------------------------------

    def _manifest_of(self, directory: Path) -> dict[str, Any]:
        path = directory / "manifest.json"
        if not path.exists():
            raise _error(
                ErrorCode.SOURCE_UNRESOLVED,
                f"backup sem manifesto: {directory}",
            )
        return json.loads(path.read_text(encoding="utf-8"))

    def verify_backup(self, directory: Path | str) -> dict[str, Any]:
        """Verificador de integridade (§5): SHA-256 por arquivo, integridade
        dos bancos SQLite e presença do manifesto."""
        directory = Path(directory)
        manifest = self._manifest_of(directory)
        problems: list[str] = []
        for relative, expected in (manifest.get("files") or {}).items():
            candidate = directory / relative
            if not candidate.exists():
                problems.append(f"arquivo ausente: {relative}")
                continue
            if _sha256(candidate) != expected:
                problems.append(f"hash divergente: {relative}")
        for relative in manifest.get("files") or {}:
            if relative.endswith(".sqlite"):
                database = directory / relative
                if not database.exists():
                    continue
                conn = sqlite3.connect(
                    f"file:{database}?mode=ro", uri=True
                )
                try:
                    row = conn.execute("PRAGMA integrity_check").fetchone()
                    if str(row[0]) != "ok":
                        problems.append(
                            f"integrity_check falhou em {relative}: {row[0]}"
                        )
                finally:
                    conn.close()
        return {
            "backup_id": manifest.get("backup_id"),
            "directory": str(directory),
            "files": len(manifest.get("files") or {}),
            "problems": problems,
            "status": "verified" if not problems else "inconsistent",
        }

    def restore_backup(
        self, directory: Path | str, *, target_root: Path | str
    ) -> dict[str, Any]:
        """Restore em DIRETÓRIO NOVO (§5) com verificador de integridade e
        replay; tombstones registrados valem ANTES de liberar o restore
        (§15.1): refs tombstonados NÃO podem resolver no conjunto restaurado.
        Qualquer falha descarta o diretório novo (nada parcial é liberado)."""
        directory = Path(directory)
        target_root = Path(target_root)
        verification = self.verify_backup(directory)
        if verification["status"] != "verified":
            raise _error(
                ErrorCode.INTERNAL_FAILURE,
                "backup inconsistente — restore recusado (§5): "
                f"{verification['problems'][:3]}",
            )
        if target_root.exists() and any(target_root.iterdir()):
            raise _error(
                ErrorCode.SCHEMA_INVALID,
                f"restore exige diretório NOVO: {target_root} já tem conteúdo",
            )
        target_root.mkdir(parents=True, exist_ok=True)
        try:
            for relative in self._manifest_of(directory).get("files") or {}:
                source = directory / relative
                if not source.exists():
                    continue
                dest = target_root / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
            report = self._verify_restored_set(target_root, directory)
        except BaseException:
            shutil.rmtree(target_root, ignore_errors=True)
            raise
        return {
            "status": "restored",
            "backup_id": verification["backup_id"],
            "target": str(target_root),
            "verification": report,
            "note": (
                "restore verificado em diretório novo; tombstones aplicados "
                "ANTES de liberar o restore (§15.1); sem sanitização forense"
            ),
        }

    def _verify_restored_set(
        self, target_root: Path, source_directory: Path
    ) -> dict[str, Any]:
        """Replay e tombstones no conjunto restaurado (§5/§15.1)."""
        manifest = self._manifest_of(source_directory)
        problems: list[str] = []
        domain_file = target_root / Path(
            self._relative_domain_name(manifest)
        )
        if not domain_file.exists():
            raise _error(
                ErrorCode.INTERNAL_FAILURE,
                "conjunto restaurado sem banco de domínio (§5)",
            )
        conn = sqlite3.connect(str(domain_file))
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            if str(row[0]) != "ok":
                problems.append(f"integrity_check: {row[0]}")
            # Replay idempotente das migrações (§5: verificador de replay).
            apply_migrations(conn)
            # Tombstone ANTES de liberar restore (§15.1): nenhum ref
            # tombstonado pode resolver no conjunto restaurado.
            for tombstone in manifest.get("tombstones") or []:
                ref = str(tombstone.get("ref") or "")
                if self._ref_resolves(conn, ref):
                    problems.append(f"tombstone violado no restore: {ref}")
            users = [
                str(r[0]) for r in conn.execute("SELECT id FROM users").fetchall()
            ]
        finally:
            conn.close()
        if problems:
            raise _error(
                ErrorCode.INTERNAL_FAILURE,
                "verificação do conjunto restaurado falhou (§5/§15.1): "
                f"{problems[:3]}",
            )
        return {
            "integrity": "ok",
            "migrations_replay": "ok",
            "tombstones_checked": len(manifest.get("tombstones") or []),
            "users": users,
        }

    @staticmethod
    def _relative_domain_name(manifest: dict[str, Any]) -> str:
        for relative in manifest.get("files") or {}:
            if relative.endswith("domain.sqlite"):
                return relative
        raise _error(
            ErrorCode.INTERNAL_FAILURE,
            "manifesto sem banco de domínio",
        )

    @staticmethod
    def _ref_resolves(conn: sqlite3.Connection, ref: str) -> bool:
        """True se o artefato do ref ``<prefixo>:<uuid>@<versão>`` ainda
        existe com conteúdo no conjunto restaurado — ressurreição proibida
        (§5/§15.1). Eventos permanecem como linha purgada (payload ``NULL``,
        sem hash reversível, §5): linha purgada NÃO é violação do tombstone.
        """
        prefix, _, _ = ref.partition(":")
        raw = ref.split(":", 1)[-1].split("@", 1)[0]
        try:
            _uuid.UUID(raw)
        except ValueError:
            return False
        if prefix == "event":
            row = conn.execute(
                "SELECT payload_json FROM events WHERE id = ?", (raw,)
            ).fetchone()
            if row is None:
                return False
            return row[0] is not None  # payload vivo = violação
        table = {"fact": "facts", "summary": "summaries"}.get(prefix)
        if table is None:
            return False
        row = conn.execute(
            f"SELECT 1 FROM {table} WHERE id = ?", (raw,)
        ).fetchone()
        return row is not None

    # -- exclusão ativa (§15.1) ----------------------------------------------

    def apply_user_deletion(
        self,
        user_id: str,
        *,
        scope: str,
        backup_pending_until: str | None,
    ) -> dict[str, Any]:
        """Exclusão ativa imediata na aplicação (§15.1): backup que contém
        APENAS o usuário excluído é removido JÁ NA SOLICITAÇÃO; backup com
        outros usuários fica pendente até expiração (prazo registrado)."""
        now = self._clock()
        removed: list[str] = []
        marked: list[dict[str, Any]] = []
        for entry in self.catalog.backups_containing_user(user_id):
            users = list(entry.get("users") or [])
            if scope == "all" and users == [user_id]:
                directory = Path(entry.get("directory") or "")
                if directory.exists():
                    shutil.rmtree(directory, ignore_errors=True)
                self.catalog.update(
                    str(entry["backup_id"]),
                    status="removed",
                    removed_at=_utc_now_iso(),
                    note=(
                        "removido já na solicitação: backup continha apenas "
                        "o usuário excluído (§15.1)"
                    ),
                )
                removed.append(str(entry["backup_id"]))
            else:
                deadline = backup_pending_until or (
                    now + timedelta(days=BACKUP_RETENTION_DAYS)
                ).isoformat()
                self.catalog.update(
                    str(entry["backup_id"]),
                    status="pending_expiry",
                    expires_at=deadline,
                    note=(
                        f"backup pendente até {deadline} (exclusão de dados "
                        f"do usuário {user_id}, escopo {scope!r})"
                    ),
                )
                marked.append(
                    {
                        "backup_id": str(entry["backup_id"]),
                        "backup_pending_until": deadline,
                    }
                )
        self.catalog.save()
        return {
            "removed_backups": removed,
            "pending_backups": marked,
            "scope": scope,
            "note": (
                "escopo/prazo exibidos; sem alegação de sanitização forense "
                "(§15.1)"
            ),
        }


__all__ = [
    "BACKUP_RETENTION_DAYS",
    "BackupCatalog",
    "BackupEntry",
    "BackupReport",
    "BackupService",
]
