"""P75 (PA1) — force=False + dangling refs raises; force=True stamps + proceeds."""

from __future__ import annotations

from mindsos_core import BlockedReason, Graph, Metagraph, RemoveGraphBlockedError


def _fresh_with_xref() -> tuple[Metagraph, str, str, str]:
    mg = Metagraph(name="t")
    g1 = Graph(name="g1", role="ontology")
    g2 = Graph(name="g2", role="lexicon")
    mg.add_graph(g1)
    mg.add_graph(g2)
    n1 = g1.add_node(value="a", type_name="Person")
    n2 = g2.add_node(value="b", type_name="Person")
    xref = mg.add_xref(
        source_id=n2.node_id,
        target_metagraph_id=mg.metagraph_id,
        target_role="ontology",
        target_id=n1.node_id,
        ref_type="SPECIALISES",
    )
    return mg, g1.graph_id, n1.node_id, xref.xref_id


def test_force_false_with_dangling_xref_raises() -> None:
    mg, gid, _, xid = _fresh_with_xref()
    try:
        mg.remove_graph(gid)
        raise AssertionError("expected RemoveGraphBlockedError")
    except RemoveGraphBlockedError as e:
        assert e.blocked_reason is BlockedReason.DANGLING_REFS
        assert len(e.impact.incoming_xrefs) == 1
        assert e.impact.incoming_xrefs[0].xref_id == xid
    # XRef NOT stamped on block path
    assert mg.xrefs[xid].target_stale is False


def test_force_true_proceeds_and_stamps_xref() -> None:
    mg, gid, _, xid = _fresh_with_xref()
    impact = mg.remove_graph(gid, force=True)
    assert impact.proceeded is True
    assert len(impact.incoming_xrefs) == 1
    # gid removed; xref still there (it lives on the surviving source side) and stamped
    assert gid not in mg.graphs
    assert mg.xrefs[xid].target_stale is True


def test_force_false_with_dangling_ref_property_raises() -> None:
    mg = Metagraph(name="t")
    g1 = Graph(name="g1", role="ontology")
    g2 = Graph(name="g2", role="lexicon")
    mg.add_graph(g1)
    mg.add_graph(g2)
    n1 = g1.add_node(value="a", type_name="Person")
    n2 = g2.add_node(value="b", type_name="Person")
    g2.update_node_properties(n2.node_id, properties={"ref:ontology": n1.node_id})
    try:
        mg.remove_graph(g1.graph_id)
        raise AssertionError("expected RemoveGraphBlockedError")
    except RemoveGraphBlockedError as e:
        assert e.blocked_reason is BlockedReason.DANGLING_REFS
        assert (n2.node_id, "ref:ontology") in e.impact.incoming_ref_properties
