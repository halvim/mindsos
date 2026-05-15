"""Metagraph XRef API — add_xref / iter_xrefs / remove_xref + inverse indexes.

Locks PB-2 (AND-composed iter), PB-6 (no dedup), and the Phase 09
in-memory state shape (xrefs / _xrefs_by_source / _xrefs_by_target /
_xrefs_dirty).
"""

from __future__ import annotations

import pytest

from mindsos_core import Graph, IdentityError, Metagraph
from mindsos_core.models.xref import XRef


def _seed_mg() -> Metagraph:
    """Helper — minimal mg with one graph + two source nodes."""
    mg = Metagraph(name="src", metagraph_id="mg-src")
    g = Graph(name="ont", role="ontology")
    mg.add_graph(g)
    g.add_node("n1", type_name="Concept", node_id="n1")
    g.add_node("n2", type_name="Concept", node_id="n2")
    return mg


def test_add_xref_in_memory_returns_xref_with_uuid():
    mg = _seed_mg()
    x = mg.add_xref(
        source_id="n1",
        target_metagraph_id="mg-tgt",
        target_role="lexicon",
        target_id="t1",
        ref_type="SPECIALISES",
    )
    assert isinstance(x, XRef)
    assert x.source_id == "n1"
    assert x.target_metagraph_id == "mg-tgt"
    assert x.xref_id in mg.xrefs
    # P54 — programmatic add (no _persist_client) marks dirty.
    assert x.xref_id in mg._xrefs_dirty


def test_add_xref_populates_inverse_indexes():
    mg = _seed_mg()
    x = mg.add_xref(
        source_id="n1",
        target_metagraph_id="mg-tgt",
        target_role="lex",
        target_id="t1",
        ref_type="SPECIALISES",
    )
    assert x.xref_id in mg._xrefs_by_source["n1"]
    assert x.xref_id in mg._xrefs_by_target[("mg-tgt", "t1")]


def test_add_xref_registers_in_identity():
    mg = _seed_mg()
    x = mg.add_xref(
        source_id="n1",
        target_metagraph_id="mg-tgt",
        target_role="lex",
        target_id="t1",
        ref_type="SPECIALISES",
    )
    assert mg.identity.contains(x.xref_id)


def test_add_xref_unknown_source_raises_identity_error():
    mg = _seed_mg()
    with pytest.raises(IdentityError, match="not registered"):
        mg.add_xref(
            source_id="ghost-node",
            target_metagraph_id="mg-tgt",
            target_role="lex",
            target_id="t1",
            ref_type="SPECIALISES",
        )


def test_add_xref_no_dedup_pb_6():
    """PB-6 — duplicate calls mint distinct UUIDs; no dedup."""
    mg = _seed_mg()
    x1 = mg.add_xref(
        source_id="n1", target_metagraph_id="mg-tgt", target_role="lex",
        target_id="t1", ref_type="SPECIALISES",
    )
    x2 = mg.add_xref(
        source_id="n1", target_metagraph_id="mg-tgt", target_role="lex",
        target_id="t1", ref_type="SPECIALISES",
    )
    assert x1.xref_id != x2.xref_id
    assert len(mg.xrefs) == 2


def test_iter_xrefs_no_filter_yields_all():
    mg = _seed_mg()
    mg.add_xref(source_id="n1", target_metagraph_id="m", target_role="r",
                target_id="t1", ref_type="SPECIALISES")
    mg.add_xref(source_id="n2", target_metagraph_id="m", target_role="r",
                target_id="t2", ref_type="INSTANCE_OF")
    assert len(list(mg.iter_xrefs())) == 2


def test_iter_xrefs_filter_source_id():
    mg = _seed_mg()
    mg.add_xref(source_id="n1", target_metagraph_id="m", target_role="r",
                target_id="t1", ref_type="SPECIALISES")
    mg.add_xref(source_id="n2", target_metagraph_id="m", target_role="r",
                target_id="t2", ref_type="INSTANCE_OF")
    out = list(mg.iter_xrefs(source_id="n1"))
    assert len(out) == 1
    assert out[0].source_id == "n1"


def test_iter_xrefs_filter_compound_target():
    mg = _seed_mg()
    mg.add_xref(source_id="n1", target_metagraph_id="m1", target_role="r",
                target_id="t1", ref_type="SPECIALISES")
    mg.add_xref(source_id="n1", target_metagraph_id="m2", target_role="r",
                target_id="t1", ref_type="SPECIALISES")
    out = list(mg.iter_xrefs(target_metagraph_id="m1", target_id="t1"))
    assert len(out) == 1
    assert out[0].target_metagraph_id == "m1"


def test_iter_xrefs_and_composed_pb_2():
    """PB-2 — multi-filter narrows by AND; only XRefs matching ALL."""
    mg = _seed_mg()
    mg.add_xref(source_id="n1", target_metagraph_id="m", target_role="r",
                target_id="t1", ref_type="SPECIALISES")
    mg.add_xref(source_id="n1", target_metagraph_id="m", target_role="r",
                target_id="t2", ref_type="INSTANCE_OF")
    mg.add_xref(source_id="n2", target_metagraph_id="m", target_role="r",
                target_id="t1", ref_type="SPECIALISES")
    out = list(mg.iter_xrefs(source_id="n1", ref_type="SPECIALISES"))
    assert len(out) == 1
    assert out[0].source_id == "n1"
    assert out[0].ref_type == "SPECIALISES"


def test_iter_xrefs_filter_ref_type_only():
    mg = _seed_mg()
    mg.add_xref(source_id="n1", target_metagraph_id="m", target_role="r",
                target_id="t1", ref_type="SPECIALISES")
    mg.add_xref(source_id="n1", target_metagraph_id="m", target_role="r",
                target_id="t2", ref_type="INSTANCE_OF")
    out = list(mg.iter_xrefs(ref_type="INSTANCE_OF"))
    assert len(out) == 1
    assert out[0].ref_type == "INSTANCE_OF"


def test_remove_xref_clears_inverse_indexes_and_identity():
    mg = _seed_mg()
    x = mg.add_xref(source_id="n1", target_metagraph_id="m", target_role="r",
                   target_id="t1", ref_type="SPECIALISES")
    mg.remove_xref(x.xref_id)
    assert x.xref_id not in mg.xrefs
    assert x.xref_id not in mg._xrefs_by_source.get("n1", set())
    assert x.xref_id not in mg._xrefs_by_target.get(("m", "t1"), set())
    assert not mg.identity.contains(x.xref_id)
    # P54 — dirty cleared too.
    assert x.xref_id not in mg._xrefs_dirty


def test_remove_xref_unknown_id_raises_identity_error():
    mg = _seed_mg()
    with pytest.raises(IdentityError, match="Unknown xref"):
        mg.remove_xref("does-not-exist")
