"""Subclass construction + class-var invariants (Phase 06 row §B)."""

from __future__ import annotations

import pytest

import mindsos_instances as mi
from mindsos_instances.exceptions import OverrideScopeError


# ── class-level discriminators (P26 C) ─────────────────────────────────────


def test_kind_constants_present():
    assert mi.NodeInstance.KIND == "node"
    assert mi.EdgeInstance.KIND == "edge"
    assert mi.HyperEdgeInstance.KIND == "hyperedge"
    assert mi.SubGraphInstance.KIND == "subgraph"
    assert mi.GraphInstance.KIND == "graph"
    assert mi.MetaEdgeInstance.KIND == "metaedge"
    assert mi.MetaHyperEdgeInstance.KIND == "metahyperedge"
    assert mi.CompositeInstance.KIND == "composite"


# ── structural allow-list (P36 A + round-7 P48 A + P60 A) ──────────────────


def test_node_allow_list_is_empty():
    assert mi.NodeInstance.STRUCTURAL_KEYS == frozenset()


def test_edge_allow_list_has_endpoints_and_label():
    assert mi.EdgeInstance.STRUCTURAL_KEYS == frozenset(
        {"source_id", "target_id", "label"}
    )


def test_hyperedge_allow_list_member_ids_and_label():
    assert mi.HyperEdgeInstance.STRUCTURAL_KEYS == frozenset(
        {"member_ids", "label"}
    )


def test_subgraph_allow_list_node_ids_edge_ids():
    assert mi.SubGraphInstance.STRUCTURAL_KEYS == frozenset(
        {"node_ids", "edge_ids"}
    )


def test_graph_instance_empty_allow_list():
    assert mi.GraphInstance.STRUCTURAL_KEYS == frozenset()


def test_metaedge_allow_list_endpoints_and_label():
    assert mi.MetaEdgeInstance.STRUCTURAL_KEYS == frozenset(
        {"source_graph_id", "target_graph_id", "label"}
    )


def test_metahyperedge_allow_list_uses_graph_ids():
    # Round-7 P60 A — renamed from `member_graph_ids` to `graph_ids` to
    # match Core's MetaHyperEdge field.
    assert mi.MetaHyperEdgeInstance.STRUCTURAL_KEYS == frozenset(
        {"graph_ids", "label"}
    )


# ── set-typed structural keys (round-7 P57 A) ──────────────────────────────


def test_hyperedge_member_ids_is_set_typed():
    assert "member_ids" in mi.HyperEdgeInstance.SET_TYPED_KEYS


def test_subgraph_node_ids_edge_ids_set_typed():
    assert "node_ids" in mi.SubGraphInstance.SET_TYPED_KEYS
    assert "edge_ids" in mi.SubGraphInstance.SET_TYPED_KEYS


def test_metahyperedge_graph_ids_set_typed():
    assert "graph_ids" in mi.MetaHyperEdgeInstance.SET_TYPED_KEYS


def test_edge_has_no_set_typed_keys():
    assert mi.EdgeInstance.SET_TYPED_KEYS == frozenset()


# ── type_name forbid (P33 B) ───────────────────────────────────────────────


def test_edge_family_forbids_type_name():
    assert mi.EdgeInstance.FORBIDS_TYPE_NAME is True
    assert mi.HyperEdgeInstance.FORBIDS_TYPE_NAME is True
    assert mi.MetaEdgeInstance.FORBIDS_TYPE_NAME is True
    assert mi.MetaHyperEdgeInstance.FORBIDS_TYPE_NAME is True


def test_node_subgraph_graph_dont_forbid_type_name():
    assert mi.NodeInstance.FORBIDS_TYPE_NAME is False
    assert mi.SubGraphInstance.FORBIDS_TYPE_NAME is False
    assert mi.GraphInstance.FORBIDS_TYPE_NAME is False


# ── construction (basic) ────────────────────────────────────────────────────


def test_node_instance_constructs(mg_with_graph, reg):
    nid = next(iter(mg_with_graph.graphs.values())).nodes.keys().__iter__().__next__()
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=nid,
        _registry=reg,
    )
    assert ni.template_id == nid
    assert ni.metagraph_id == mg_with_graph.metagraph_id
    assert ni.id  # minted
    assert ni.overrides == {}


def test_instance_id_is_stable_across_calls(mg_with_graph, reg):
    """Round-7 P46 C — overrides do NOT participate in ID; ID is stable
    across mutation."""
    g = next(iter(mg_with_graph.graphs.values()))
    nid = next(iter(g.nodes.keys()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=nid,
        _registry=reg,
    )
    original_id = ni.id
    ni.set_override("age", 99)
    assert ni.id == original_id
    ni.set_override("nickname", "Ace")
    assert ni.id == original_id
    ni.clear_override("nickname")
    assert ni.id == original_id


def test_instance_seq_increments_per_template(mg_with_graph, reg):
    """Round-7 P46 C — per-template monotonic counter."""
    g = next(iter(mg_with_graph.graphs.values()))
    nid = next(iter(g.nodes.keys()))
    seqs = []
    for _ in range(5):
        ni = mi.NodeInstance(
            metagraph_id=mg_with_graph.metagraph_id,
            template_id=nid,
            _registry=reg,
        )
        seqs.append(ni._instance_seq)
        reg.add(ni)
    assert seqs == [1, 2, 3, 4, 5]


def test_two_instances_of_same_template_have_distinct_ids(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    nid = next(iter(g.nodes.keys()))
    a = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=nid,
        _registry=reg,
    )
    b = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=nid,
        _registry=reg,
    )
    assert a.id != b.id


def test_metagraph_id_mismatch_raises(mg_with_graph, reg):
    from mindsos_core.exceptions import IdentityError

    with pytest.raises(IdentityError):
        mi.NodeInstance(
            metagraph_id="bogus_id",
            template_id="N1",
            _registry=reg,
        )


# ── universally-forbidden keys (round-7 P47 C) ─────────────────────────────


def test_id_override_rejected(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    nid = next(iter(g.nodes.keys()))
    with pytest.raises(OverrideScopeError):
        mi.NodeInstance(
            metagraph_id=mg_with_graph.metagraph_id,
            template_id=nid,
            overrides={"id": "spoofed"},
            _registry=reg,
        )


def test_template_id_override_rejected(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    nid = next(iter(g.nodes.keys()))
    with pytest.raises(OverrideScopeError):
        mi.NodeInstance(
            metagraph_id=mg_with_graph.metagraph_id,
            template_id=nid,
            overrides={"template_id": "spoofed"},
            _registry=reg,
        )


def test_kind_override_rejected(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    nid = next(iter(g.nodes.keys()))
    with pytest.raises(OverrideScopeError):
        mi.NodeInstance(
            metagraph_id=mg_with_graph.metagraph_id,
            template_id=nid,
            overrides={"kind": "spoofed"},
            _registry=reg,
        )


def test_metagraph_id_override_rejected(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    nid = next(iter(g.nodes.keys()))
    with pytest.raises(OverrideScopeError):
        mi.NodeInstance(
            metagraph_id=mg_with_graph.metagraph_id,
            template_id=nid,
            overrides={"metagraph_id": "spoofed"},
            _registry=reg,
        )


# ── type_name forbid (P33 B) ───────────────────────────────────────────────


def test_edge_instance_type_name_override_rejected(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    eid = next(iter(g.edges.keys()))
    with pytest.raises(OverrideScopeError):
        mi.EdgeInstance(
            metagraph_id=mg_with_graph.metagraph_id,
            template_id=eid,
            overrides={"type_name": "NEW_TYPE"},
            _registry=reg,
        )
