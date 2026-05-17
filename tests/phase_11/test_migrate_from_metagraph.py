"""Tier 6 — :func:`migrate_from` per-Metagraph dispatch (PB-17 C).

Verifies the per-Metagraph walk aggregates per-Graph scans + emits the
``old_schema_name`` mismatch policy warning (logger WARN, NOT a
``SchemaViolation``) per the warn-not-mutate discipline.
"""

from __future__ import annotations

import logging

import pytest

from mindsos_core.models.graph import Graph
from mindsos_core.models.metagraph import Metagraph
from mindsos_core.schema import (
    EdgeType,
    NodeType,
    Schema,
    SchemaMigrationError,
    migrate_from,
)


def _two_graph_metagraph() -> Metagraph:
    """Construct a Metagraph with 2 graphs, both schema-less for seeding."""
    mg = Metagraph(name="m")
    g1 = Graph(name="g1")
    a = g1.add_node("a", "Person", _validate=False)
    b = g1.add_node("b", "Person", _validate=False)
    g1.add_edge(source=a, target=b, type_name="WORKS_AT",
                properties={}, _validate=False)
    g1.schema_name = "v1"
    g2 = Graph(name="g2")
    c = g2.add_node("c", "Person", _validate=False)
    d = g2.add_node("d", "Person", _validate=False)
    g2.add_edge(source=c, target=d, type_name="WORKS_AT",
                properties={}, _validate=False)
    g2.schema_name = "v1"
    mg.add_graph(g1)
    mg.add_graph(g2)
    return mg


def _old_v1() -> Schema:
    s = Schema(strict=True)
    s.add_node_type(NodeType(name="Person"))
    s.add_edge_type(EdgeType(name="WORKS_AT"))
    return s


def _new_v2_dropping_works_at() -> Schema:
    s = Schema(strict=True)
    s.add_node_type(NodeType(name="Person"))
    return s


def test_metagraph_dispatch_aggregates_violations_across_contained_graphs() -> None:
    """Per-Metagraph scan returns one bucket per (kind, type, graph_id)."""
    mg = _two_graph_metagraph()
    old = _old_v1()
    new = _new_v2_dropping_works_at()
    violations = migrate_from(old, mg, new=new, detail="summary")
    removed_edge = [v for v in violations if v.kind == "removed_edge_type"]
    # One summary entry per graph (graph_id distinguishes them).
    assert len(removed_edge) == 2
    assert {v.graph_id for v in removed_edge} == {
        v.graph_id for v in mg.graphs.values()
    }


def test_metagraph_dispatch_each_mode_emits_per_element_per_graph() -> None:
    """Each mode emits one violation per offending element in each graph."""
    mg = _two_graph_metagraph()
    old = _old_v1()
    new = _new_v2_dropping_works_at()
    violations = migrate_from(old, mg, new=new, detail="each")
    removed_edge = [v for v in violations if v.kind == "removed_edge_type"]
    # 1 WORKS_AT edge per graph × 2 graphs = 2 each-entries.
    assert len(removed_edge) == 2


def test_metagraph_dispatch_skips_graphs_without_attached_schema_when_no_new(
) -> None:
    """When ``new`` is omitted, graphs without ``graph.schema`` are skipped."""
    mg = _two_graph_metagraph()  # graphs have no schema attached.
    old = _old_v1()
    violations = migrate_from(old, mg, detail="summary")  # no new, no schemas
    assert violations == []


def test_metagraph_dispatch_emits_name_mismatch_warning(caplog) -> None:
    """``old_schema_name`` mismatch emits logger WARN (PB-17 C)."""
    mg = _two_graph_metagraph()
    # Override one graph's schema_name so it mismatches.
    list(mg.graphs.values())[0].schema_name = "v999"
    old = _old_v1()
    new = _new_v2_dropping_works_at()
    with caplog.at_level(logging.WARNING,
                         logger="mindsos_core.schema.migration"):
        violations = migrate_from(
            old, mg, new=new, detail="summary", old_schema_name="v1",
        )
    name_mismatch_logs = [
        r for r in caplog.records
        if "schema_name" in r.message and "v999" in r.message
    ]
    assert len(name_mismatch_logs) == 1
    # The mismatched graph IS skipped, so only the other graph contributes.
    removed_edge = [v for v in violations if v.kind == "removed_edge_type"]
    assert len(removed_edge) == 1


def test_metagraph_dispatch_with_no_graphs_returns_empty() -> None:
    """Empty Metagraph → no violations."""
    mg = Metagraph(name="empty")
    old = _old_v1()
    new = _new_v2_dropping_works_at()
    assert migrate_from(old, mg, new=new, detail="summary") == []
