"""M3 + P84 — snapshot covers full mutable state surface; restore drops adds, rebuilds removes."""

from __future__ import annotations

from mindsos_core import Graph, MetagraphSnapshot

from tests._shared.soft_delete_fixture import make_metagraph_with_soft_delete


def test_added_graph_dropped_on_restore() -> None:
    mg, _ = make_metagraph_with_soft_delete()
    snap = MetagraphSnapshot.of(mg)
    n_before = len(mg.graphs)
    g_new = Graph(name="added-after-snapshot", role="ontology")
    mg.add_graph(g_new)
    snap.restore_into(mg)
    assert len(mg.graphs) == n_before
    assert g_new.graph_id not in mg.graphs


def test_property_bag_restored() -> None:
    mg, ids = make_metagraph_with_soft_delete()
    mg.properties["kl:active"] = "g1"
    mg.graphs[ids["graph_ont"]].properties["source"] = "dolce"
    snap = MetagraphSnapshot.of(mg)
    mg.properties.clear()
    mg.graphs[ids["graph_ont"]].properties.clear()
    snap.restore_into(mg)
    assert mg.properties == {"kl:active": "g1"}
    assert mg.graphs[ids["graph_ont"]].properties == {"source": "dolce"}


def test_xref_inverse_indexes_rebuilt() -> None:
    mg, ids = make_metagraph_with_soft_delete()
    snap = MetagraphSnapshot.of(mg)
    mg.xrefs.clear()
    mg._xrefs_by_source.clear()
    mg._xrefs_by_target.clear()
    snap.restore_into(mg)
    assert ids["xref"] in mg.xrefs
    assert len(mg._xrefs_by_source) > 0
    assert len(mg._xrefs_by_target) > 0


def test_intergraph_attrs_captured() -> None:
    """P84 — intergraph_edges / intergraph_hyperedges captured."""
    mg, _ = make_metagraph_with_soft_delete()
    snap = MetagraphSnapshot.of(mg)
    assert isinstance(snap._intergraph_edges, dict)
    assert isinstance(snap._intergraph_hyperedges, dict)
