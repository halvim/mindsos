"""RPB-5 + RR-17 — Step 1h drain order: EDGE → HYPEREDGE → METAEDGE → METAHYPEREDGE → XREF."""

from __future__ import annotations

from mindsos_core import SoftDeleteKind
from mindsos_core.persistence import InMemoryClient, MetagraphRepository

from tests._shared.soft_delete_fixture import make_metagraph_with_soft_delete


def test_drain_emits_per_kind_cypher() -> None:
    mg, ids = make_metagraph_with_soft_delete()
    g = mg.graphs[ids["graph_ont"]]
    g.deprecate_edge(ids["edge"])
    g.dispute_edge(ids["edge"])
    g.deprecate_hyperedge(ids["hyperedge"])
    mg.deprecate_metaedge(ids["metaedge"])
    mg.dispute_metahyperedge(ids["metahyperedge"])
    mg.mark_xref_stale(ids["xref"])
    mg.deprecate_xref(ids["xref"])

    client = InMemoryClient()
    repo = MetagraphRepository(client)
    repo._drain_soft_delete(mg)

    # 2 cypher emits per element × 5 element kinds = 10 total
    assert len(client.calls) == 10


def test_drain_atomic_clear() -> None:
    mg, ids = make_metagraph_with_soft_delete()
    g = mg.graphs[ids["graph_ont"]]
    g.deprecate_edge(ids["edge"])
    mg.deprecate_metaedge(ids["metaedge"])
    mg.mark_xref_stale(ids["xref"])

    client = InMemoryClient()
    MetagraphRepository(client)._drain_soft_delete(mg)
    assert all(len(g._soft_delete_dirty[k]) == 0 for k in g._soft_delete_dirty)
    assert all(len(mg._soft_delete_dirty[k]) == 0 for k in mg._soft_delete_dirty)


def test_drain_stale_id_discarded() -> None:
    """Element deleted between mark + drain → dropped from dirty."""
    mg, ids = make_metagraph_with_soft_delete()
    mg.mark_xref_stale(ids["xref"])
    del mg.xrefs[ids["xref"]]
    client = InMemoryClient()
    MetagraphRepository(client)._drain_soft_delete(mg)
    assert len(mg._soft_delete_dirty[SoftDeleteKind.XREF]) == 0


def test_drain_order_buckets() -> None:
    """RPB-5 — emits sequential buckets; first cypher targets EDGE, last targets XREF."""
    mg, ids = make_metagraph_with_soft_delete()
    g = mg.graphs[ids["graph_ont"]]
    g.deprecate_edge(ids["edge"])
    mg.mark_xref_stale(ids["xref"])

    client = InMemoryClient()
    MetagraphRepository(client)._drain_soft_delete(mg)
    # First emission should be edge-side; last should be xref-side.
    first_q = client.calls[0][0]
    last_q = client.calls[-1][0]
    assert "()-[e" in first_q  # untyped rel match → edge
    assert ":XRef" in last_q
