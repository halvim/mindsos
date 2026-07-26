"""CR#4 Slice 1 — deep_copy / fork independence (ADR-0201 §deep_copy).

``copy.deepcopy`` preserves ids verbatim, so a forked MentalModel used to
collide with its origin (same metagraph_id / graph_id) and its provenance
XRef resolved back to the origin. This covers the three-layer fix:

* core   — ``Metagraph.regenerate_ids`` / ``remap_xref_targets``
* L1      — ``ElementRegistry.remap_ids`` (instances carry metagraph_id)
* L5      — ``MentalModel.deep_copy`` orchestration
"""

from __future__ import annotations

import mindsos_instances as mi
from mindsos_core import Graph, Metagraph
from mindsos_instances import NodeInstance
from mindsos_intelligence.mm import MentalModel

from tests._shared.cross_metagraph_fixture import (
    make_source_and_target_metagraphs,
)


# ── core: regenerate_ids ─────────────────────────────────────────────────

def _mg_two_graphs():
    mg = Metagraph(name="t", metagraph_id="mg-old-1")
    g1 = Graph(name="g1", role="ontology")
    g2 = Graph(name="g2", role="lexicon")
    mg.add_graph(g1)
    mg.add_graph(g2)
    g1.add_node("n1", type_name="Concept", node_id="n1")
    return mg, g1, g2


def test_regenerate_ids_changes_metagraph_and_graph_ids():
    mg, g1, g2 = _mg_two_graphs()
    o_mg, o_g1, o_g2 = mg.metagraph_id, g1.graph_id, g2.graph_id

    id_map = mg.regenerate_ids()

    assert mg.metagraph_id != o_mg
    assert g1.graph_id != o_g1
    assert g2.graph_id != o_g2
    assert id_map[o_mg] == mg.metagraph_id
    assert id_map[o_g1] == g1.graph_id
    assert id_map[o_g2] == g2.graph_id
    # graphs dict rekeyed to the new ids, same Graph objects
    assert set(mg.graphs.keys()) == {g1.graph_id, g2.graph_id}
    assert mg.graphs[g1.graph_id] is g1
    # identity holds the new ids, not the old
    assert mg.identity.contains(mg.metagraph_id)
    assert not mg.identity.contains(o_mg)
    assert mg.identity.contains(g1.graph_id)
    assert not mg.identity.contains(o_g1)
    # node ids are NOT regenerated
    assert "n1" in g1.nodes


# ── core: cross-metagraph xref target remap ──────────────────────────────

def test_regenerate_and_remap_xref_targets_point_into_the_fork():
    source, target = make_source_and_target_metagraphs()
    x = source.add_xref(
        source_id="src-node-1",
        target_metagraph_id=target.metagraph_id,
        target_role="lexicon",
        target_id="tgt-node-1",
        ref_type="SPECIALISES",
        target_metagraph=target,
    )
    o_src, o_tgt = source.metagraph_id, target.metagraph_id

    smap = source.regenerate_ids()
    tmap = target.regenerate_ids()

    # regenerate_ids fixes the SOURCE leg; the target leg is still stale
    assert x.source_metagraph_id == source.metagraph_id != o_src
    assert x.target_metagraph_id == o_tgt

    source.remap_xref_targets({**smap, **tmap})

    assert x.target_metagraph_id == target.metagraph_id != o_tgt
    # compound index rebuilt under the new target id
    hits = list(
        source.iter_xrefs(
            target_metagraph_id=target.metagraph_id, target_id="tgt-node-1"
        )
    )
    assert x in hits
    # the stale target key no longer resolves
    assert (
        list(
            source.iter_xrefs(
                target_metagraph_id=o_tgt, target_id="tgt-node-1"
            )
        )
        == []
    )


# ── L1: registry instance reid ───────────────────────────────────────────

def test_registry_remap_ids_updates_instance_metagraph_id():
    mg = Metagraph(name="t", metagraph_id="mg-old-2")
    g = Graph(name="g", role="ontology")
    mg.add_graph(g)
    g.add_node("n1", type_name="Concept", node_id="n1")
    mi.attach_registry(mg)
    reg = mg.element_registry

    inst = NodeInstance(metagraph_id=mg.metagraph_id, template_id="n1", _registry=reg)
    reg.add(inst)

    id_map = mg.regenerate_ids()
    reg.remap_ids(id_map)

    assert inst.metagraph_id == mg.metagraph_id
    assert inst.metagraph_id == id_map["mg-old-2"]
    # template_id is a node id (not regenerated) -> unchanged
    assert inst.template_id == "n1"


# ── L5: end-to-end fork (the CR test-4 requirement) ──────────────────────

def _seed_provenance_mm() -> MentalModel:
    mm = MentalModel(session_id="s1", user_id="u1")
    kg = Graph(name="know", role="ontology")
    mm.knowledge_mm.add_graph(kg)
    kg.add_node("k1", type_name="Concept", node_id="k1")
    cg = Graph(name="cap", role="lexicon")
    mm.capacity_mm.add_graph(cg)
    cg.add_node("c1", type_name="Concept", node_id="c1")
    mm.capacity_mm.add_xref(
        source_id="c1",
        target_metagraph_id=mm.knowledge_mm.metagraph_id,
        target_role="ontology",
        target_id="k1",
        ref_type="INSTANCE_OF",
        target_metagraph=mm.knowledge_mm,
    )
    return mm


def test_fork_regenerates_ids_and_provenance_xref_resolves_in_fork():
    mm = _seed_provenance_mm()
    o_cap = mm.capacity_mm.metagraph_id
    o_know = mm.knowledge_mm.metagraph_id
    o_cap_graphs = set(mm.capacity_mm.graphs.keys())

    clone = mm.deep_copy()

    # distinct metagraph ids
    assert clone.capacity_mm.metagraph_id != o_cap
    assert clone.knowledge_mm.metagraph_id != o_know
    # distinct graph ids
    assert set(clone.capacity_mm.graphs.keys()).isdisjoint(o_cap_graphs)
    # the cloned provenance XRef resolves WITHIN the fork
    cx = next(iter(clone.capacity_mm.xrefs.values()))
    assert cx.source_metagraph_id == clone.capacity_mm.metagraph_id
    assert cx.target_metagraph_id == clone.knowledge_mm.metagraph_id
    assert cx.target_metagraph_id != o_know
    # target index rebuilt -> lookup by the fork's ids finds it
    hits = list(
        clone.capacity_mm.iter_xrefs(
            target_metagraph_id=clone.knowledge_mm.metagraph_id, target_id="k1"
        )
    )
    assert cx in hits
    # origin is untouched
    ox = next(iter(mm.capacity_mm.xrefs.values()))
    assert ox.source_metagraph_id == o_cap
    assert ox.target_metagraph_id == o_know


def test_fork_root_and_object_independence_preserved():
    # The pre-existing independence guarantee (phase_46) still holds.
    mm = MentalModel(session_id="s1", user_id="u1")
    mm.root.request_run_ref = "requestrun:orig"
    clone = mm.deep_copy()
    assert clone.root.request_run_ref == "requestrun:orig"
    clone.root.outcome_ref = "outcome:x"
    assert mm.root.outcome_ref is None
    assert clone.knowledge_mm is not mm.knowledge_mm
    assert clone.capacity_mm is not mm.capacity_mm
    assert clone.lock is not mm.lock
