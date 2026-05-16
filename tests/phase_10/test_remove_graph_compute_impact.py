"""PB-5a + ADR-0135 amendment-3 — in-memory _xrefs_by_target index drives impact."""

from __future__ import annotations

from mindsos_core import Graph, Metagraph


def test_compute_impact_uses_in_memory_index() -> None:
    mg = Metagraph(name="t")
    g1 = Graph(name="g1", role="ontology")
    g2 = Graph(name="g2", role="lexicon")
    mg.add_graph(g1); mg.add_graph(g2)
    n1 = g1.add_node(value="a", type_name="Person")
    n2 = g2.add_node(value="b", type_name="Person")
    xref = mg.add_xref(
        source_id=n2.node_id,
        target_metagraph_id=mg.metagraph_id,
        target_role="ontology",
        target_id=n1.node_id,
        ref_type="SPECIALISES",
    )
    impact = mg._compute_removal_impact(g1.graph_id)
    assert len(impact.incoming_xrefs) == 1
    assert impact.incoming_xrefs[0].xref_id == xref.xref_id


def test_compute_impact_no_refs_returns_empty() -> None:
    mg = Metagraph(name="t")
    g1 = Graph(name="g1", role="ontology")
    mg.add_graph(g1)
    g1.add_node(value="a", type_name="Person")
    impact = mg._compute_removal_impact(g1.graph_id)
    assert impact.incoming_xrefs == []
    assert impact.incoming_ref_properties == []


def test_compute_impact_skips_self_graph_in_ref_scan() -> None:
    """Ref scan walks OTHER graphs only; refs within the removed graph
    don't count as incoming (they're outgoing-by-removal)."""
    mg = Metagraph(name="t")
    g1 = Graph(name="g1", role="ontology")
    mg.add_graph(g1)
    n_a = g1.add_node(value="a", type_name="Person")
    n_b = g1.add_node(value="b", type_name="Person")
    g1.update_node_properties(n_b.node_id, properties={"ref:ontology": n_a.node_id})
    impact = mg._compute_removal_impact(g1.graph_id)
    assert impact.incoming_ref_properties == []
