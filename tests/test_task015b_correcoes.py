"""Testes de regressão da task 015b — correção da 015a: fail-closed do
confronto com tombstones do domínio corrente no restore.

Sonda da revisão da 015a (achado alto luna-A1, recomendado por GLM e qwen)
reproduzida ANTES da correção (``/tmp/opencode/015b/probe_ANTES.txt``: restore
liberado com payload excluído vivo — `except sqlite3.Error: return []` em
``backup.py:544-551``) e corrigida; cada teste abaixo fixa o comportamento
corrigido. Não é a suíte quantitativa da etapa 8: testes locais de curta
duração, sem rede externa e sem modelo real.

Tabela (código → caso):

| Código | Caso |
|---|---|
| TOM-3 | banco corrente PRESENTE porém ilegível + restore → recusa tipada INTERNAL_FAILURE com diretório alvo descartado (§15.1, fail-closed) |
| TOM-4 | diferenciação por existência do arquivo: sem ``domain.sqlite`` corrente → confronto trivialmente satisfeito (lista vazia documentada) |
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from eduagent.contracts import EduAgentError, ErrorCode, MemoryPack
from eduagent.services.backup import BackupService
from eduagent.services.effects import EffectsService
from eduagent.services.memory import MemoryService

from test_task015_cli_api import (  # noqa: F401 — fixtures reexportadas
    SESSION,
    UID,
    open_full_runtime,
)

UTC = timezone.utc


def new_backup_service(context, tmp_path: Path) -> BackupService:
    return BackupService(
        store=context.store,
        checkpointer=context.checkpointer,
        data_root=context.data_root,
        backup_root=tmp_path / "backups",
    )


def restore_service(context, tmp_path: Path) -> BackupService:
    """Serviço de restore como na CLI (store fechado; domínio corrente é o
    ``data_root`` vivo)."""
    return BackupService(
        store=None,
        checkpointer=None,
        data_root=context.data_root,
        backup_root=tmp_path / "backups",
    )


def _backup_com_evento(tmp_path: Path) -> Path:
    context = open_full_runtime(tmp_path)
    clock_value = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    memory = MemoryService(
        context.store,
        EffectsService(context.store),
        clock=lambda: clock_value,
    )
    memory.record_event(
        user_id=UID,
        session_id=SESSION,
        kind=MemoryPack.EventKind.READING,
        payload={"text": "SONDA-015B-PAYLOAD-EXCLUIDO"},
        occurred_at=clock_value,
        origin=MemoryPack.Origin.OBSERVED,
    )
    service = new_backup_service(context, tmp_path)
    report = service.create_backup()  # fecha escritores (§5)
    return Path(report.directory)


class TestFailClosedTombstonesCorrentes:
    def test_banco_corrente_ilegivel_recusa_restore(self, tmp_path):
        """TOM-3 (§15.1, fail-closed): banco corrente PRESENTE porém ilegível
        → recusa tipada INTERNAL_FAILURE com o diretório alvo descartado —
        o restore NUNCA prossegue sem confrontar tombstones (sonda luna-A1
        da revisão da 015a corrigida)."""
        backup_dir = _backup_com_evento(tmp_path)
        context = open_full_runtime(tmp_path)
        try:
            domain = context.data_root / "domain.sqlite"
            assert domain.exists()
            domain.write_bytes(b"isto nao e um banco sqlite\n" * 64)
            target = tmp_path / "alvo-tom3"
            with pytest.raises(EduAgentError) as exc:
                restore_service(context, tmp_path).restore_backup(
                    backup_dir, target_root=target
                )
            assert exc.value.code == ErrorCode.INTERNAL_FAILURE
            assert "ilegível" in str(exc.value)
            # diretório descartado: nada parcial é liberado (§5/§15.1)
            assert not target.exists()
        finally:
            context.close()

    def test_sem_banco_corrente_confronto_trivial(self, tmp_path):
        """TOM-4 (diferenciação por existência do arquivo): raiz de dados SEM
        ``domain.sqlite`` corrente (restore em raiz nova isolada) → lista
        vazia documentada, confronto trivialmente satisfeito; banco PRESENTE
        e ilegível seria recusa tipada (TOM-3)."""
        backup_dir = _backup_com_evento(tmp_path)
        context = open_full_runtime(tmp_path)
        try:
            (context.data_root / "domain.sqlite").unlink()
            assert not (context.data_root / "domain.sqlite").exists()
            assert restore_service(context, tmp_path)._current_domain_tombstones() == []
            target = tmp_path / "alvo-tom4"
            outcome = restore_service(context, tmp_path).restore_backup(
                backup_dir, target_root=target
            )
            assert outcome["status"] == "restored"
            assert (
                outcome["verification"]["current_domain_tombstones_checked"]
                == 0
            )
        finally:
            context.close()
