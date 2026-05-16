"""P67 + P81 — cascade gate is independent of force (raises regardless)."""

from __future__ import annotations

from mindsos_core import BlockedReason, Graph, Metagraph, RemoveGraphBlockedError


def _fresh() -> tuple[Metagraph, Graph, Graph]:
    mg = Metagraph(name="t")
    g1 = Graph(name="g1", role="ontology")
    g2 = Graph(name="g2", role="lexicon")
    mg.add_graph(g1)
    mg.add_graph(g2)
    return mg, g1, g2


def test_cascade_false_with_incident_metaedge_raises() -> None:
    mg, g1, g2 = _fresh()
    me = mg.add_metaedge(source_graph_id=g1.graph_id, target_graph_id=g2.graph_id, type_name="X")
    try:
        mg.remove_graph(g1.graph_id, cascade=False)
        raise AssertionError("expected RemoveGraphBlockedError")
    except RemoveGraphBlockedError as e:
        assert e.blocked_reason is BlockedReason.INCIDENT_META_EDGES_CASCADE_FALSE
    # State unchanged
    assert g1.graph_id in mg.graphs
    assert me.edge_id in mg.metaedges


def test_cascade_false_force_true_still_raises_p81() -> None:
    """P81 — force does NOT override the cascade gate."""
    mg, g1, g2 = _fresh()
    mg.add_metaedge(source_graph_id=g1.graph_id, target_graph_id=g2.graph_id, type_name="X")
    try:
        mg.remove_graph(g1.graph_id, cascade=False, force=True)
        raise AssertionError("P81 violated — force should not override cascade gate")
    except RemoveGraphBlockedError as e:
        assert e.blocked_reason is BlockedReason.INCIDENT_META_EDGES_CASCADE_FALSE


def test_cascade_true_default_cascades_metaedge() -> None:
    mg, g1, g2 = _fresh()
    me = mg.add_metaedge(source_graph_id=g1.graph_id, target_graph_id=g2.graph_id, type_name="X")
    impact = mg.remove_graph(g1.graph_id)
    assert impact.proceeded is True
    assert g1.graph_id not in mg.graphs
    assert me.edge_id not in mg.metaedges
