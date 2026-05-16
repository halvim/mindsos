"""RB1 + RPB-11 + P86 — snapshot captures dirty state at both scopes."""

from __future__ import annotations

from mindsos_core import MetagraphSnapshot, SoftDeleteKind

from tests._shared.soft_delete_fixture import make_metagraph_with_soft_delete


def test_xrefs_dirty_captured() -> None:
    """Phase 09 RB1 — _xrefs_dirty survives snapshot/restore."""
    mg, _ = make_metagraph_with_soft_delete()
    mg._xrefs_dirty.add("synthetic")
    snap = MetagraphSnapshot.of(mg)
    mg._xrefs_dirty.clear()
    snap.restore_into(mg)
    assert "synthetic" in mg._xrefs_dirty


def test_metagraph_soft_delete_dirty_captured() -> None:
    """RPB-11 — Metagraph._soft_delete_dirty (META + XREF buckets) survives roundtrip."""
    mg, ids = make_metagraph_with_soft_delete()
    mg.deprecate_metaedge(ids["metaedge"])
    mg.mark_xref_stale(ids["xref"])
    snap = MetagraphSnapshot.of(mg)
    mg._soft_delete_dirty[SoftDeleteKind.METAEDGE].clear()
    mg._soft_delete_dirty[SoftDeleteKind.XREF].clear()
    snap.restore_into(mg)
    assert ids["metaedge"] in mg._soft_delete_dirty[SoftDeleteKind.METAEDGE]
    assert ids["xref"] in mg._soft_delete_dirty[SoftDeleteKind.XREF]


def test_graph_soft_delete_dirty_captured() -> None:
    """P86 — Graph._soft_delete_dirty (EDGE + HYPEREDGE buckets) survives roundtrip."""
    mg, ids = make_metagraph_with_soft_delete()
    g = mg.graphs[ids["graph_ont"]]
    g.deprecate_edge(ids["edge"])
    g.deprecate_hyperedge(ids["hyperedge"])
    snap = MetagraphSnapshot.of(mg)
    g._soft_delete_dirty[SoftDeleteKind.EDGE].clear()
    g._soft_delete_dirty[SoftDeleteKind.HYPEREDGE].clear()
    snap.restore_into(mg)
    # Same Graph object (ADR-0027), dirty buckets restored.
    assert ids["edge"] in mg.graphs[ids["graph_ont"]]._soft_delete_dirty[SoftDeleteKind.EDGE]
    assert ids["hyperedge"] in mg.graphs[ids["graph_ont"]]._soft_delete_dirty[SoftDeleteKind.HYPEREDGE]
