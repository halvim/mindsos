"""Override-validation bifurcation tests (round-7 P64 A)."""

from __future__ import annotations

import pytest

import mindsos_instances as mi
from mindsos_instances.exceptions import OverrideScopeError


# ── structural bucket bypasses user-property validation ─────────────────────


def test_edge_source_id_override_accepted(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    eid = next(iter(g.edges.keys()))
    ei = mi.EdgeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=eid,
        overrides={"source_id": "node-1"},
        _registry=reg,
    )
    # source_id is in EdgeInstance.STRUCTURAL_KEYS → structural bucket;
    # not rejected even though it's in RESERVED_PROPERTY_KEYS.
    assert ei.overrides["source_id"] == "node-1"


def test_edge_label_override_accepted(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    eid = next(iter(g.edges.keys()))
    ei = mi.EdgeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=eid,
        overrides={"label": "custom-edge"},
        _registry=reg,
    )
    assert ei.overrides["label"] == "custom-edge"


# ── user-property bucket rejects reserved keys ─────────────────────────────


def test_node_label_override_rejected(mg_with_graph, reg):
    """NodeInstance has no `label` in STRUCTURAL_KEYS; reserved-key check
    fires in user-property bucket."""
    g = next(iter(mg_with_graph.graphs.values()))
    nid = next(iter(g.nodes.keys()))
    with pytest.raises(OverrideScopeError):
        mi.NodeInstance(
            metagraph_id=mg_with_graph.metagraph_id,
            template_id=nid,
            overrides={"label": "ignored"},
            _registry=reg,
        )


def test_node_value_override_rejected_as_reserved(mg_with_graph, reg):
    """`value` is in RESERVED_PROPERTY_KEYS and not in NodeInstance's
    structural allow-list."""
    g = next(iter(mg_with_graph.graphs.values()))
    nid = next(iter(g.nodes.keys()))
    with pytest.raises(OverrideScopeError):
        mi.NodeInstance(
            metagraph_id=mg_with_graph.metagraph_id,
            template_id=nid,
            overrides={"value": "spoofed"},
            _registry=reg,
        )


# ── user-property accepted when non-reserved ───────────────────────────────


def test_node_arbitrary_property_accepted(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    nid = next(iter(g.nodes.keys()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=nid,
        overrides={"nickname": "Ace", "score": 99},
        _registry=reg,
    )
    assert ni.overrides == {"nickname": "Ace", "score": 99}


# ── set-typed coercion (round-7 P57 A) ─────────────────────────────────────


def test_hyperedge_member_ids_list_coerced_to_frozenset(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    hid = next(iter(g.hyperedges.keys()))
    hi = mi.HyperEdgeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=hid,
        overrides={"member_ids": ["N1", "N2", "N3"]},
        _registry=reg,
    )
    assert isinstance(hi.overrides["member_ids"], frozenset)
    assert hi.overrides["member_ids"] == frozenset({"N1", "N2", "N3"})


def test_hyperedge_member_ids_duplicates_dedup(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    hid = next(iter(g.hyperedges.keys()))
    hi = mi.HyperEdgeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=hid,
        overrides={"member_ids": ["N1", "N1", "N2"]},
        _registry=reg,
    )
    assert hi.overrides["member_ids"] == frozenset({"N1", "N2"})


def test_hyperedge_member_ids_non_list_rejected(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    hid = next(iter(g.hyperedges.keys()))
    with pytest.raises(OverrideScopeError):
        mi.HyperEdgeInstance(
            metagraph_id=mg_with_graph.metagraph_id,
            template_id=hid,
            overrides={"member_ids": "not_a_list"},
            _registry=reg,
        )


def test_hyperedge_accepts_set_directly(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    hid = next(iter(g.hyperedges.keys()))
    hi = mi.HyperEdgeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=hid,
        overrides={"member_ids": {"N1", "N2"}},
        _registry=reg,
    )
    assert hi.overrides["member_ids"] == frozenset({"N1", "N2"})


# ── set_override / clear_override APIs ────────────────────────────────────


def test_set_override_validates(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    nid = next(iter(g.nodes.keys()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=nid,
        _registry=reg,
    )
    ni.set_override("age", 42)
    assert ni.overrides["age"] == 42
    with pytest.raises(OverrideScopeError):
        ni.set_override("id", "spoofed")


def test_clear_override_idempotent(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    nid = next(iter(g.nodes.keys()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=nid,
        overrides={"age": 30},
        _registry=reg,
    )
    ni.clear_override("age")
    assert "age" not in ni.overrides
    ni.clear_override("age")  # no-op
    assert "age" not in ni.overrides


def test_has_override_returns_membership(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    nid = next(iter(g.nodes.keys()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=nid,
        overrides={"age": 30},
        _registry=reg,
    )
    assert ni.has_override("age")
    assert not ni.has_override("nickname")
