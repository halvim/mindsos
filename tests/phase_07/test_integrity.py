"""Integrity scanner tests (Phase 07 — 5 buckets + 3-bucket partial per P98 A)."""

from __future__ import annotations

from mindsos_core.models.edge import Edge, HyperEdge
from mindsos_core.models.graph import Graph
from mindsos_core.models.metagraph import Metagraph
from mindsos_core.models.node import Node
from mindsos_core.persistence import (
    IntegrityReport,
    PartialIntegrityReport,
    verify_invariants,
    verify_invariants_graph,
)


def test_empty_metagraph_is_clean() -> None:
    mg = Metagraph(name="mg")
    rep = verify_invariants(mg)
    assert not rep
    assert rep.summary() == "clean"


def test_empty_graph_is_clean() -> None:
    g = Graph(name="g")
    rep = verify_invariants_graph(g)
    assert not rep


def test_report_is_truthy_when_any_bucket_populated() -> None:
    rep = IntegrityReport(duplicate_ids=[("Node", ["dup1"])])
    assert rep
    rep2 = IntegrityReport(cross_graph_edges=[("e1", "g1")])
    assert rep2


def test_partial_report_skips_2_buckets() -> None:
    """Partial report has 3 graph-internal buckets only."""
    rep = PartialIntegrityReport()
    assert not hasattr(rep, "cross_graph_edges")
    assert not hasattr(rep, "orphan_metaedges")
    # 3 graph-internal buckets exist:
    assert hasattr(rep, "duplicate_ids")
    assert hasattr(rep, "orphan_hyperedges")
    assert hasattr(rep, "dangling_tombstones")


def test_cross_graph_edges_bucket_detects_leak() -> None:
    """Edge with endpoints in different graphs surfaces as cross-graph leak."""
    mg = Metagraph(name="mg")
    g1 = Graph(name="g1")
    g2 = Graph(name="g2")
    mg.add_graph(g1)
    mg.add_graph(g2)
    n1 = g1.add_node("v", "T")
    n2 = g2.add_node("v", "T")
    # Inject a broken Edge directly (bypassing add_edge's same-graph check)
    # to simulate a FalkorDB-side direct-Cypher leak.
    bad = Edge(source=n1, target=n2, type_name="REL")
    g1.edges[bad.edge_id] = bad

    rep = verify_invariants(mg)
    assert rep.cross_graph_edges
    assert any(eid == bad.edge_id for eid, _ in rep.cross_graph_edges)


def test_orphan_metaedge_detects_missing_target() -> None:
    """MetaEdge pointing at a graph that's not in the metagraph."""
    from mindsos_core.models.metagraph import MetaEdge

    mg = Metagraph(name="mg")
    g1 = Graph(name="g1")
    mg.add_graph(g1)
    me = MetaEdge(source_graph_id=g1.graph_id, target_graph_id="GHOST", type_name="MREL")
    mg.metaedges[me.edge_id] = me

    rep = verify_invariants(mg)
    assert me.edge_id in rep.orphan_metaedges


def test_dangling_tombstones_bucket_empty_at_phase_07() -> None:
    """P16-pre — tombstone-write primitives ship; read-filter is Phase 10."""
    mg = Metagraph(name="mg")
    rep = verify_invariants(mg)
    assert rep.dangling_tombstones == []


def test_partial_scanner_detects_orphan_hyperedge() -> None:
    """Graph-scoped scanner catches zero-member HyperEdge."""
    g = Graph(name="g")
    n = g.add_node("v", "T")
    h = g.add_hyperedge([n], "HE")
    # Manually clear members to simulate corruption.
    h.nodes.clear()

    rep = verify_invariants_graph(g)
    assert h.edge_id in rep.orphan_hyperedges


def test_partial_scanner_clean_returns_clean_summary() -> None:
    g = Graph(name="g")
    rep = verify_invariants_graph(g)
    assert "clean" in rep.summary()


def test_duplicate_ids_bucket_surfaces_dupes() -> None:
    """Manually inject a duplicate Node id to exercise the scanner."""
    mg = Metagraph(name="mg")
    g = Graph(name="g")
    mg.add_graph(g)
    n = g.add_node("v", "T", node_id="dup")
    # Inject a 2nd Node sharing the id directly (bypasses add_node's
    # identity registration).
    n2 = Node(value="v2", type_name="T", node_id="dup")
    g.nodes[n2.node_id + "_extra_key"] = n2  # different dict key, same id
    rep = verify_invariants(mg)
    assert any(label == "Node" and "dup" in ids for label, ids in rep.duplicate_ids)
