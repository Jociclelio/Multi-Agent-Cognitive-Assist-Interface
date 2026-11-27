"""Testes da visualização do grafo (``eduagent.graph_view``).

Cobrem apenas a camada de leitura: serialização de nós/arestas, DOT com ids
estáveis, resumo de trace (disparos e fios percorridos) e escolha do trace
mais recente. Nenhum teste invoca o grafo, o modelo ou a rede.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from langchain_core.runnables.graph import Graph

from eduagent.graph_view import (
    build_dot,
    build_view,
    graph_payload,
    latest_trace,
    summarize_trace,
)


def _sample_graph() -> Graph:
    graph = Graph()
    start = graph.add_node(None, id="__start__")
    classify = graph.add_node(None, id="classify")
    collect = graph.add_node(None, id="exam_collect")
    commit = graph.add_node(None, id="exam_commit")
    end = graph.add_node(None, id="__end__")
    graph.add_edge(start, classify)
    graph.add_edge(classify, collect, data="exam", conditional=True)
    graph.add_edge(classify, end, data="ask", conditional=True)
    graph.add_edge(collect, commit)
    graph.add_edge(commit, end)
    return graph


def _trace(*, spans: list[dict], started: datetime, finished: datetime) -> dict:
    return {
        "trace_id": "trace-1",
        "turn_id": "turn-1",
        "session_id": "session-1",
        "status": "completed",
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "message": {"sha256": "x", "length": 12},
        "spans": spans,
        "llm": [{"queue_s": 0.1}, {"queue_s": 0.2}],
        "errors": [],
        "timing": {"total_s": 1.0},
    }


def test_graph_payload_lists_nodes_and_edges_with_stable_ids() -> None:
    payload = graph_payload(_sample_graph())
    assert [n["id"] for n in payload["nodes"]] == [
        "__start__",
        "classify",
        "exam_collect",
        "exam_commit",
        "__end__",
    ]
    assert payload["nodes"][1]["kind"] == "llm"
    assert payload["nodes"][0]["terminal"] is True
    conditional = [e for e in payload["edges"] if e["conditional"]]
    assert [(e["source"], e["target"], e["label"]) for e in conditional] == [
        ("classify", "exam_collect", "exam"),
        ("classify", "__end__", "ask"),
    ]
    assert payload["edge_ids"][("classify", "exam_collect")] == (
        "e_classify__exam_collect"
    )


def test_build_dot_uses_stable_svg_ids_and_conditional_style() -> None:
    payload = graph_payload(_sample_graph())
    dot = build_dot(payload)
    assert dot.startswith("digraph EduAgent {")
    assert 'id="n_classify"' in dot
    assert 'id="e_classify__exam_collect"' in dot
    assert 'style="dashed"' in dot
    assert 'label="exam"' in dot


def test_summarize_trace_reports_fired_nodes_and_edges_in_order() -> None:
    payload = graph_payload(_sample_graph())
    started = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)
    trace = _trace(
        started=started,
        finished=started + timedelta(seconds=2.5),
        spans=[
            {"node": "classify", "kind": "llm", "started_at": started.isoformat()},
            {
                "node": "exam_collect",
                "kind": "tools",
                "started_at": (started + timedelta(seconds=1)).isoformat(),
            },
            {
                "node": "exam_commit",
                "kind": "commit",
                "started_at": (started + timedelta(seconds=2)).isoformat(),
            },
        ],
    )
    summary = summarize_trace(trace, payload)
    assert summary["fired_nodes"] == ["classify", "exam_collect", "exam_commit"]
    assert [e["svg_id"] for e in summary["fired_edges"]] == [
        "e_classify__exam_collect",
        "e_exam_collect__exam_commit",
    ]
    assert summary["duration_s"] == 2.5
    assert summary["llm_calls"] == 2
    assert summary["message_length"] == 12


def test_summarize_trace_ignores_unknown_nodes() -> None:
    payload = graph_payload(_sample_graph())
    started = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)
    trace = _trace(
        started=started,
        finished=started,
        spans=[{"node": "nó_inexistente", "kind": "tools", "started_at": "x"}],
    )
    summary = summarize_trace(trace, payload)
    assert summary["fired_nodes"] == []
    assert summary["fired_edges"] == []


def test_latest_trace_picks_most_recent_and_skips_corrupted(tmp_path: Path) -> None:
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    broken = tmp_path / "broken.json"
    old.write_text(json.dumps({"trace_id": "old"}), encoding="utf-8")
    new.write_text(json.dumps({"trace_id": "new"}), encoding="utf-8")
    broken.write_text("{não é json", encoding="utf-8")
    import os

    os.utime(old, (1000, 1000))
    os.utime(new, (2000, 2000))
    os.utime(broken, (3000, 3000))
    assert latest_trace(tmp_path)["trace_id"] == "new"


def test_latest_trace_missing_directory_returns_none(tmp_path: Path) -> None:
    assert latest_trace(tmp_path / "ausente") is None
    assert latest_trace(None) is None


def test_build_view_without_telemetry_has_no_trace(tmp_path: Path) -> None:
    view = build_view(_sample_graph(), telemetry_dir=tmp_path)
    assert view["status"] == "ok"
    assert view["node_count"] == 5
    assert view["edge_count"] == 5
    assert view["trace"] is None
    assert view["dot"].startswith("digraph EduAgent {")
    assert view["svg"] is None or "<svg" in view["svg"]
