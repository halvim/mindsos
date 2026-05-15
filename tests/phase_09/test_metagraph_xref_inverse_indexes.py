"""In-memory inverse-index correctness — _xrefs_by_source + _xrefs_by_target."""

from __future__ import annotations

from mindsos_core import Graph, Metagraph


def _seed() -> Metagraph:
    mg = Metagraph(name="m", metagraph_id="mg-1")
    g = Graph(name="g", role="r")
    mg.add_graph(g)
    g.add_node("n1", type_name="C", node_id="n1")
    g.add_node("n2", type_name="C", node_id="n2")
    return mg


def test_add_xref_populates_source_index():
    mg = _seed()
    x1 = mg.add_xref(source_id="n1", target_metagraph_id="mt", target_role="r",
                    target_id="t1", ref_type="SPECIALISES")
    x2 = mg.add_xref(source_id="n1", target_metagraph_id="mt", target_role="r",
                    target_id="t2", ref_type="SPECIALISES")
    assert mg._xrefs_by_source["n1"] == {x1.xref_id, x2.xref_id}


def test_add_xref_populates_target_index():
    mg = _seed()
    x1 = mg.add_xref(source_id="n1", target_metagraph_id="mt", target_role="r",
                    target_id="t1", ref_type="SPECIALISES")
    x2 = mg.add_xref(source_id="n2", target_metagraph_id="mt", target_role="r",
                    target_id="t1", ref_type="SPECIALISES")
    assert mg._xrefs_by_target[("mt", "t1")] == {x1.xref_id, x2.xref_id}


def test_remove_xref_cleans_source_index_partially():
    """Removing one of multiple XRefs from same source leaves others."""
    mg = _seed()
    x1 = mg.add_xref(source_id="n1", target_metagraph_id="mt", target_role="r",
                    target_id="t1", ref_type="SPECIALISES")
    x2 = mg.add_xref(source_id="n1", target_metagraph_id="mt", target_role="r",
                    target_id="t2", ref_type="SPECIALISES")
    mg.remove_xref(x1.xref_id)
    assert mg._xrefs_by_source["n1"] == {x2.xref_id}


def test_iter_xrefs_uses_source_index_for_seed():
    """Performance hint — when source_id is set, only matching IDs traversed."""
    mg = _seed()
    x = mg.add_xref(source_id="n1", target_metagraph_id="mt", target_role="r",
                   target_id="t1", ref_type="SPECIALISES")
    mg.add_xref(source_id="n2", target_metagraph_id="mt", target_role="r",
                target_id="t2", ref_type="SPECIALISES")
    out = list(mg.iter_xrefs(source_id="n1"))
    assert len(out) == 1
    assert out[0].xref_id == x.xref_id
