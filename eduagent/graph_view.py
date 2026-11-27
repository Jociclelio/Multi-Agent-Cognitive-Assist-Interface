"""Visualização do grafo multiagente (mapa §10/§12).

Este módulo só **lê** o grafo compilado (``CompiledStateGraph.get_graph()``) e
os traces locais de ``data/telemetry``; não altera estado, checkpoint nem
domínio. O SVG é gerado offline com o binário ``dot`` (Graphviz), sem rede e
sem ``pygraphviz``; quando o ``dot`` não existe, o payload continua válido com
DOT/Mermaid e ``svg: null``.

Os identificadores de nós/arestas no SVG são determinísticos
(``n_<nome>``/``e_<origem>__<destino>``) para a UI destacar o caminho do
último turno sem reinterpretar o desenho.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from eduagent.telemetry import SPAN_KIND_BY_NODE

#: Cor de preenchimento/borda por categoria de span (§12). Nós não mapeados
#: caem em ``tools`` (mesma convenção de ``SPAN_KIND_BY_NODE``).
KIND_STYLES: dict[str, tuple[str, str]] = {
    "llm": ("#dbeafe", "#2563eb"),
    "retrieval": ("#dcfce7", "#16a34a"),
    "context": ("#fef9c3", "#ca8a04"),
    "solver": ("#fde68a", "#d97706"),
    "commit": ("#fce7f3", "#db2777"),
    "tools": ("#f1f5f9", "#64748b"),
    "queue": ("#e5e7eb", "#4b5563"),
}

_EDGE_COLOR = "#94a3b8"
_FONT = "Helvetica, Arial, sans-serif"
_SAFE = re.compile(r"[^0-9A-Za-z_]")


def _svg_id(prefix: str, value: str, used: set[str]) -> str:
    base = f"{prefix}_{_SAFE.sub('_', value) or 'x'}"
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _dot_escape(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )


def graph_payload(drawable: Any) -> dict[str, Any]:
    """Serializa o grafo desenhável em listas estáveis de nós/arestas."""
    used: set[str] = set()
    node_ids: dict[str, str] = {}
    nodes: list[dict[str, Any]] = []
    for node in drawable.nodes.values():
        name = str(getattr(node, "name", None) or node.id)
        node_id = _svg_id("n", name, used)
        node_ids[node.id] = node_id
        kind = SPAN_KIND_BY_NODE.get(name, "tools")
        nodes.append(
            {
                "id": name,
                "svg_id": node_id,
                "kind": kind,
                "terminal": name in ("__start__", "__end__"),
            }
        )
    edges: list[dict[str, Any]] = []
    edge_ids: dict[tuple[str, str], str] = {}
    for edge in drawable.edges:
        source = str(edge.source)
        target = str(edge.target)
        svg_id = _svg_id("e", f"{source}__{target}", used)
        edge_ids[(source, target)] = svg_id
        edges.append(
            {
                "source": source,
                "target": target,
                "svg_id": svg_id,
                "conditional": bool(edge.conditional),
                "label": edge.data,
            }
        )
    return {"nodes": nodes, "edges": edges, "node_ids": node_ids, "edge_ids": edge_ids}


def build_dot(payload: dict[str, Any]) -> str:
    """DOT do grafo com cores por categoria e ids estáveis para o SVG."""
    lines = [
        "digraph EduAgent {",
        '  rankdir="LR";',
        '  bgcolor="transparent";',
        f'  graph [fontname="{_FONT}", nodesep="0.30", ranksep="0.55"];',
        f'  node [fontname="{_FONT}", fontsize="10", shape="box", '
        'style="rounded,filled", penwidth="1.1", margin="0.10,0.06"];',
        f'  edge [fontname="{_FONT}", fontsize="8", color="{_EDGE_COLOR}", '
        'arrowsize="0.65"];',
    ]
    for node in payload["nodes"]:
        name = node["id"]
        label = {"__start__": "início", "__end__": "fim"}.get(name, name)
        fill, stroke = KIND_STYLES.get(node["kind"], KIND_STYLES["tools"])
        shape = "oval" if node["terminal"] else "box"
        lines.append(
            f'  "{node["svg_id"]}" [id="{node["svg_id"]}", '
            f'label="{_dot_escape(label)}", shape="{shape}", '
            f'fillcolor="{fill}", color="{stroke}"];'
        )
    for edge in payload["edges"]:
        attrs = [
            f'id="{edge["svg_id"]}"',
            f'style="{"dashed" if edge["conditional"] else "solid"}"',
        ]
        if edge["label"]:
            attrs.append(f'label="{_dot_escape(edge["label"])}"')
        lines.append(
            f'  "{payload["node_ids"][edge["source"]]}" -> '
            f'"{payload["node_ids"][edge["target"]]}" [{", ".join(attrs)}];'
        )
    lines.append("}")
    return "\n".join(lines)


def render_svg(dot_source: str, *, timeout: float = 20.0) -> str | None:
    """Renderiza DOT → SVG via ``dot``; ausência/falha do binário vira ``None``."""
    try:
        proc = subprocess.run(
            ["dot", "-Tsvg"],
            input=dot_source.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    return proc.stdout.decode("utf-8", "replace")


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def summarize_trace(
    trace: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Resumo do trace: disparos em ordem + arestas percorridas (§12)."""
    spans = [s for s in trace.get("spans") or [] if isinstance(s, dict)]
    ordered = sorted(
        spans,
        key=lambda s: str(s.get("started_at") or ""),
    )
    fired_nodes: list[str] = []
    fired: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str]] = set()
    previous: str | None = None
    for span in ordered:
        node = span.get("node")
        if not node or node not in payload["node_ids"]:
            continue
        if node not in fired_nodes:
            fired_nodes.append(node)
        if previous is not None and previous != node:
            key = (previous, node)
            if key not in seen_edges:
                seen_edges.add(key)
                svg_id = payload["edge_ids"].get(key)
                if svg_id:
                    fired.append(
                        {"source": previous, "target": node, "svg_id": svg_id}
                    )
        previous = node
    started = _parse_iso(trace.get("started_at"))
    finished = _parse_iso(trace.get("finished_at"))
    duration = None
    if started and finished:
        try:
            duration = max(0.0, (finished - started).total_seconds())
        except TypeError:  # offsets diferentes (defensivo)
            duration = None
    return {
        "trace_id": trace.get("trace_id"),
        "turn_id": trace.get("turn_id"),
        "session_id": trace.get("session_id"),
        "status": trace.get("status"),
        "started_at": trace.get("started_at"),
        "finished_at": trace.get("finished_at"),
        "duration_s": duration,
        "message_length": (trace.get("message") or {}).get("length")
        if isinstance(trace.get("message"), dict)
        else None,
        "fired_nodes": fired_nodes,
        "fired_edges": fired,
        "spans": [
            {
                "node": s.get("node"),
                "kind": s.get("kind"),
                "active_s": s.get("active_s"),
                "started_at": s.get("started_at"),
                "ended_at": s.get("ended_at"),
            }
            for s in ordered
            if s.get("node")
        ],
        "llm_calls": len(trace.get("llm") or []),
        "errors": trace.get("errors") or [],
        "timing": trace.get("timing") or {},
    }


def latest_trace(directory: Path | str | None) -> dict[str, Any] | None:
    """Trace mais recente do diretório de telemetria (``None`` se não houver)."""
    if directory is None:
        return None
    root = Path(directory)
    if not root.is_dir():
        return None
    candidates = sorted(
        root.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return None


def build_view(
    drawable: Any,
    *,
    telemetry_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Payload completo de ``GET /graph`` (diagrama + último turno)."""
    payload = graph_payload(drawable)
    dot_source = build_dot(payload)
    svg = render_svg(dot_source)
    mermaid: str | None = None
    try:
        mermaid = drawable.draw_mermaid()
    except Exception:  # noqa: BLE001 — Mermaid é conveniência, não contrato
        mermaid = None
    trace = latest_trace(telemetry_dir)
    return {
        "status": "ok",
        "node_count": len(payload["nodes"]),
        "edge_count": len(payload["edges"]),
        "nodes": payload["nodes"],
        "edges": payload["edges"],
        "svg": svg,
        "dot": dot_source,
        "mermaid": mermaid,
        "trace": summarize_trace(trace, payload) if trace else None,
    }


__all__ = [
    "KIND_STYLES",
    "build_dot",
    "build_view",
    "graph_payload",
    "latest_trace",
    "render_svg",
    "summarize_trace",
]
