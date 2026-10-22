"""Contexto de execução local do EduAgent-OS (mapa §3/§12 — task 015).

Abre o conjunto local (domínio SQLite, checkpointer, serviços e grafo) com a
configuração de ``config/default.yaml`` e o ``data_root`` registrado. É o
ponto único usado pela CLI e pela API loopback — os testes injetam backend,
embedder e extrator falsos; a CLI/API padrão usa os serviços reais do MVP.

Sem resultado medido aqui: a disponibilidade default do problema de
agendamento e os limites são escolhas de ensaio do mapa (§1/§3).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eduagent.agents.curator import CuratorAgent
from eduagent.agents.librarian import Librarian
from eduagent.agents.monitor import Monitor
from eduagent.agents.planner import PlannerAgent
from eduagent.agents.tutor import EventItemSink, Tutor
from eduagent.contracts import ErrorCode, EduAgentError
from eduagent.graph import EduAgentGraph
from eduagent.services.assessment import AssessmentService
from eduagent.services.calendar import CalendarService
from eduagent.services.effects import EffectsService
from eduagent.services.ingestion import IngestionService
from eduagent.services.memory import MemoryService
from eduagent.services.retrieval import RetrievalService
from eduagent.services.scheduling import DemandService
from eduagent.services.sync_connectors import build_calendar_connector
from eduagent.skills import SkillCatalog
from eduagent.storage.checkpoints import SQLiteCheckpointer
from eduagent.storage.repository import DomainStore

#: Layout local do MVP (mapa §3): bancos sob ``<data_root>``.
DOMAIN_DB_NAME = "domain.sqlite"
CHECKPOINTS_DB_NAME = "checkpoints.sqlite"
TELEMETRY_DIR_NAME = "telemetry"

DEFAULT_CONFIG_PATH = Path("config/default.yaml")


def _default_extractor(config: dict[str, Any]) -> Any | None:
    """Extrator real da superfície CLI/API (mapa §3/§6.2).

    Sem extrator injetado (testes), o Docling é usado quando disponível
    (pin do uv.lock; smoke real executado na task 017); ``ingestion.
    extractor: none`` na configuração desliga explicitamente. Docling
    indisponível devolve ``None`` — a versão permanece ``pending`` com
    impedimento explícito, nunca ``indexed`` como completa (§6.1/§12).
    """
    choice = str((config.get("ingestion") or {}).get("extractor", "docling"))
    if choice == "none":
        return None
    from eduagent.services.ingestion import DoclingExtractor, docling_available

    if not docling_available():
        return None
    return DoclingExtractor()


def load_config(path: Path | str | None = None) -> dict[str, Any]:
    """Configuração do MVP (mapa §3). YAML quando ``pyyaml`` está disponível;
    JSON é aceito como alternativa; arquivo ausente → defaults vazios (os
    defaults numéricos vivem no código como escolhas de ensaio, §3)."""
    target = Path(path) if path else DEFAULT_CONFIG_PATH
    if not target.exists():
        return {}
    text = target.read_text(encoding="utf-8")
    if target.suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError:  # pragma: no cover — pyyaml é dependência do MVP
            raise EduAgentError(
                ErrorCode.INTERNAL_FAILURE,
                "config YAML exige pyyaml (dependência do pyproject)",
            ) from None
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    return dict(data or {})


@dataclass
class RuntimeContext:
    """Conjunto local aberto (mapa §3/§12). ``close()`` libera escritores."""

    data_root: Path
    config: dict[str, Any]
    store: DomainStore
    checkpointer: SQLiteCheckpointer
    graph: EduAgentGraph
    memory: MemoryService
    calendar: CalendarService
    telemetry_dir: Path
    _closed: bool = field(default=False, repr=False)

    @classmethod
    def open(
        cls,
        data_root: Path | str,
        *,
        config_path: Path | str | None = None,
        config: dict[str, Any] | None = None,
        backend: Any | None = None,
        embedder: Any | None = None,
        extractor: Any | None = None,
        clock: Any = None,
        telemetry: bool = True,
    ) -> "RuntimeContext":
        """Abre o conjunto local. ``backend=None`` deixa as rotas com geração
        indisponíveis com erro tipado (§4) — a tutoria exige modelo admitido
        (mapa §3.1: MODEL_NOT_ADMITTED bloqueia tutoria)."""
        root = Path(data_root)
        root.mkdir(parents=True, exist_ok=True)
        effective_config = dict(load_config(config_path))
        if config:
            effective_config.update(config)
        store = DomainStore.open(root / DOMAIN_DB_NAME)
        checkpointer = SQLiteCheckpointer(root / CHECKPOINTS_DB_NAME)
        clock_fn = clock or (lambda: datetime.now(timezone.utc))
        effects = EffectsService(store)
        memory = MemoryService(store, effects, clock=clock_fn)
        assessment = AssessmentService(store, effects, clock=clock_fn)
        demands = DemandService(store, effects, clock=clock_fn)
        calendar = CalendarService(store, effects, clock=clock_fn)
        planner = PlannerAgent(store, effects, clock=clock_fn)
        ingestion = IngestionService(store, root, extractor=extractor or _default_extractor(effective_config))
        curator = CuratorAgent(store, ingestion=ingestion)
        retrieval = RetrievalService(store, root)
        tutor = (
            Tutor(
                backend,
                SkillCatalog.load(),
                item_sink=EventItemSink(store, effects, clock=clock_fn),
                clock=clock_fn,
            )
            if backend is not None
            else None
        )
        telemetry_dir = root / TELEMETRY_DIR_NAME
        graph = EduAgentGraph(
            store=store,
            checkpointer=checkpointer,
            config=effective_config,
            clock=clock_fn,
            backend=backend,
            tutor=tutor,
            librarian=Librarian(memory),
            curator=curator,
            retrieval=retrieval,
            embedder=embedder,
            memory=memory,
            assessment=assessment,
            monitor=Monitor(),
            planner=planner,
            demands=demands,
            calendar=calendar,
            ingestion=ingestion,
            # Wiring do conector de sync (correção 016a, achado QW-A1):
            # CalDAV configurado/admitido chega ao grafo pela superfície
            # CLI/API; sem config, ``None`` mantém CONNECTOR_DISABLED com
            # ICS/preview (§9, comportamento S7 preservado).
            calendar_connector=build_calendar_connector(effective_config),
            data_root=root,
            telemetry_dir=telemetry_dir if telemetry else None,
        )
        return cls(
            data_root=root,
            config=effective_config,
            store=store,
            checkpointer=checkpointer,
            graph=graph,
            memory=memory,
            calendar=calendar,
            telemetry_dir=telemetry_dir,
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.graph.close()
        self.checkpointer.close()
        self.store.close()


__all__ = ["RuntimeContext", "load_config"]
