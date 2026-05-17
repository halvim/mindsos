"""Tier 3 — Loader policy end-to-end against an InMemoryClient stub.

Exercises ``load_graph_with_report(...)`` across the three policies
(warn/error/ignore) × schema-attached / schema-unattached × env-var
override. Uses an InMemoryClient-style stub so no FalkorDB sidecar is
required. The Phase 07 / 08 in-memory client tests use the same
pattern.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List
from unittest import mock

import pytest

from mindsos_core.exceptions import UnknownEdgeTypeError
from mindsos_core.persistence.client import QueryResult
from mindsos_core.reconstruction import load_graph_with_report
from mindsos_core.reconstruction.graph_loader import (
    _UNKNOWN_EDGE_POLICY_ENV,
)
from mindsos_core.schema import EdgeType, NodeType, Schema


class _StubClient:
    """Minimal :class:`Client` stub returning canned query results."""

    def __init__(self, scripts: Dict[str, List[Dict[str, Any]]]) -> None:
        self._scripts = scripts
        self.calls: List[tuple] = []

    def run_query(self, q: str, params: Dict[str, Any] | None = None) -> QueryResult:
        params = params or {}
        self.calls.append((q, params))
        for sub, rows in self._scripts.items():
            if sub in q:
                return QueryResult(rows=list(rows))
        return QueryResult(rows=[])

    def close(self) -> None:  # pragma: no cover - test stub
        pass


def _scripted_anchor_and_nodes(
    gid: str = "g1", node_ids: List[str] | None = None
) -> Dict[str, List[Dict[str, Any]]]:
    """Construct a script that returns a Graph anchor + N nodes."""
    if node_ids is None:
        node_ids = ["n1", "n2"]
    return {
        # _load_graph_anchor's MATCH.
        "MATCH (g:Graph {id: $gid})": [
            {"name": gid, "role": None, "version": 1, "metagraph_id": None},
        ],
        # _fetch_node_page's MATCH (n:Node {graph_id: $gid}) ...
        "MATCH (n:Node {graph_id: $gid})": [
            {
                "id": nid,
                "type_name": "Person",
                "value": None,
                "version": 1,
                "props": {"id": nid, "graph_id": gid, "type_name": "Person"},
            }
            for nid in node_ids
        ],
    }


def _scripted_with_edges(
    edges: List[Dict[str, Any]],
    gid: str = "g1",
    node_ids: List[str] | None = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Anchor + nodes + edges (with given type_names)."""
    base = _scripted_anchor_and_nodes(gid=gid, node_ids=node_ids)
    # _load_edges' MATCH (s)-[e]->(t).
    base["MATCH (s:Node {graph_id: $gid})-[e]->(t:Node {graph_id: $gid})"] = edges
    # Empty hyperedge + cross-graph leak scripts.
    base["MATCH (h:HyperEdge {graph_id: $gid})"] = []
    base["MATCH (s:Node)-[e]->(t:Node)"] = []
    return base


def _build_schema_with_known_types() -> Schema:
    """Schema known to recognise ``Person`` + ``WORKS_AT`` only."""
    s = Schema(strict=False)
    s.add_node_type(NodeType(name="Person"))
    s.add_edge_type(
        EdgeType(
            name="WORKS_AT",
            allowed_sources=frozenset({"Person"}),
            allowed_targets=frozenset({"Person"}),
        )
    )
    return s


# ── policy × schema-attached matrix ─────────────────────────────────────────


def test_warn_policy_with_schema_drops_unknown_edge_types() -> None:
    """``warn`` + schema attached → unknown types filtered + counted."""
    edges = [
        {
            "id": "e1", "type_name": "WORKS_AT", "label": None,
            "version": 1, "source_id": "n1", "target_id": "n2",
            "props": {"id": "e1", "graph_id": "g1", "type_name": "WORKS_AT"},
        },
        {
            "id": "e2", "type_name": "WORKS_AT_LEGACY", "label": None,
            "version": 1, "source_id": "n1", "target_id": "n2",
            "props": {"id": "e2", "graph_id": "g1", "type_name": "WORKS_AT_LEGACY"},
        },
        {
            "id": "e3", "type_name": "WORKS_AT_LEGACY", "label": None,
            "version": 1, "source_id": "n2", "target_id": "n1",
            "props": {"id": "e3", "graph_id": "g1", "type_name": "WORKS_AT_LEGACY"},
        },
    ]
    client = _StubClient(_scripted_with_edges(edges))
    schema = _build_schema_with_known_types()
    g, report = load_graph_with_report(
        client, "g1", schema=schema, unknown_edge_type_policy="warn",
    )
    # Only the known edge survives.
    assert len(g.edges) == 1
    # Drops counted per distinct unknown type.
    assert report.dropped_edge_count == 2
    assert report.dropped_by_type == {"WORKS_AT_LEGACY": 2}


def test_error_policy_raises_on_first_unknown_edge_type() -> None:
    """``error`` raises :class:`UnknownEdgeTypeError` on first hit."""
    edges = [
        {
            "id": "e1", "type_name": "WORKS_AT_LEGACY", "label": None,
            "version": 1, "source_id": "n1", "target_id": "n2",
            "props": {"id": "e1", "graph_id": "g1", "type_name": "WORKS_AT_LEGACY"},
        },
    ]
    client = _StubClient(_scripted_with_edges(edges))
    schema = _build_schema_with_known_types()
    with pytest.raises(UnknownEdgeTypeError) as exc_info:
        load_graph_with_report(
            client, "g1", schema=schema, unknown_edge_type_policy="error",
        )
    assert exc_info.value.type_name == "WORKS_AT_LEGACY"
    assert exc_info.value.element_kind == "Edge"


def test_ignore_policy_silently_filters_unknown_types_but_still_counts() -> None:
    """``ignore`` filters silently; report still tracks for inspection."""
    edges = [
        {
            "id": "e1", "type_name": "WORKS_AT_LEGACY", "label": None,
            "version": 1, "source_id": "n1", "target_id": "n2",
            "props": {"id": "e1", "graph_id": "g1", "type_name": "WORKS_AT_LEGACY"},
        },
    ]
    client = _StubClient(_scripted_with_edges(edges))
    schema = _build_schema_with_known_types()
    g, report = load_graph_with_report(
        client, "g1", schema=schema, unknown_edge_type_policy="ignore",
    )
    assert len(g.edges) == 0
    # ``ignore`` still records — observability symmetry per impl.
    assert report.dropped_edge_count == 1


def test_no_schema_attached_is_noop_under_any_policy() -> None:
    """Policy is a no-op when ``graph.schema is None`` (PB-11 lock)."""
    edges = [
        {
            "id": "e1", "type_name": "WHATEVER", "label": None,
            "version": 1, "source_id": "n1", "target_id": "n2",
            "props": {"id": "e1", "graph_id": "g1", "type_name": "WHATEVER"},
        },
    ]
    for policy in ("warn", "error", "ignore"):
        client = _StubClient(_scripted_with_edges(edges))
        g, report = load_graph_with_report(
            client, "g1", schema=None, unknown_edge_type_policy=policy,
        )
        # No schema → no filtering; edge survives + zero drops.
        assert len(g.edges) == 1, f"policy={policy}: no-schema must no-op"
        assert report.dropped_edge_count == 0, f"policy={policy}: no drops"


def test_env_var_override_takes_effect_when_kwarg_omitted() -> None:
    """``MINDSOS_UNKNOWN_EDGE_POLICY=ignore`` short-circuits drops silently."""
    edges = [
        {
            "id": "e1", "type_name": "WORKS_AT_LEGACY", "label": None,
            "version": 1, "source_id": "n1", "target_id": "n2",
            "props": {"id": "e1", "graph_id": "g1", "type_name": "WORKS_AT_LEGACY"},
        },
    ]
    client = _StubClient(_scripted_with_edges(edges))
    schema = _build_schema_with_known_types()
    with mock.patch.dict(os.environ, {_UNKNOWN_EDGE_POLICY_ENV: "ignore"}):
        g, report = load_graph_with_report(client, "g1", schema=schema)
    assert len(g.edges) == 0
    assert report.dropped_edge_count == 1


def test_invalid_policy_value_raises_value_error() -> None:
    """Bogus policy value raises before reaching the loader proper."""
    client = _StubClient(_scripted_anchor_and_nodes())
    schema = _build_schema_with_known_types()
    with pytest.raises(ValueError, match="unknown_edge_type_policy"):
        load_graph_with_report(
            client, "g1", schema=schema, unknown_edge_type_policy="bogus",
        )


def test_warn_policy_emits_per_distinct_type_warn_log(caplog) -> None:
    """PB-10 A — one WARN per distinct type at end-of-load, with count."""
    import logging
    edges = [
        {
            "id": f"e{i}", "type_name": "WORKS_AT_LEGACY", "label": None,
            "version": 1, "source_id": "n1", "target_id": "n2",
            "props": {"id": f"e{i}", "graph_id": "g1",
                      "type_name": "WORKS_AT_LEGACY"},
        }
        for i in range(5)
    ]
    client = _StubClient(_scripted_with_edges(edges))
    schema = _build_schema_with_known_types()
    with caplog.at_level(logging.WARNING,
                         logger="mindsos_core.reconstruction.graph_loader"):
        g, report = load_graph_with_report(
            client, "g1", schema=schema, unknown_edge_type_policy="warn",
        )
    # Exactly ONE WARN line for the distinct type (not 5).
    summary_warns = [
        rec for rec in caplog.records
        if "WORKS_AT_LEGACY" in rec.message and "dropped" in rec.message
    ]
    assert len(summary_warns) == 1
    assert "5" in summary_warns[0].message  # count surfaces in the log


def test_hyperedge_policy_branches_to_hyperedge_types() -> None:
    """``warn`` policy on hyperedges filters against ``hyperedge_types``."""
    # Schema with NO hyperedge type defined — every hyperedge is unknown.
    schema = _build_schema_with_known_types()
    # Script returns 2 hyperedges; both must be filtered.
    base = _scripted_with_edges([])
    base["MATCH (h:HyperEdge {graph_id: $gid})"] = [
        {
            "id": "h1", "type_name": "MEETING_LEGACY", "label": None,
            "version": 1,
            "props": {"id": "h1", "graph_id": "g1",
                      "type_name": "MEETING_LEGACY"},
            "member_ids": ["n1", "n2"],
        },
        {
            "id": "h2", "type_name": "MEETING_LEGACY", "label": None,
            "version": 1,
            "props": {"id": "h2", "graph_id": "g1",
                      "type_name": "MEETING_LEGACY"},
            "member_ids": ["n1"],
        },
    ]
    client = _StubClient(base)
    g, report = load_graph_with_report(
        client, "g1", schema=schema, unknown_edge_type_policy="warn",
    )
    assert len(g.hyperedges) == 0
    assert report.dropped_edge_count == 2
    assert report.dropped_by_type == {"MEETING_LEGACY": 2}
