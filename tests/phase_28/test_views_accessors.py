"""Phase 28 — CapacityLayerView accessor surface."""

from __future__ import annotations

from mindsos_capacity import (
    CapacityLayer,
    CapacityLayerView,
    CATEGORY_PATH_FINDING,
    CATEGORY_PERCEPTION,
    NODE_TYPE_CAPACITY,
    NODE_TYPE_DATASTATE,
)

from ._fixtures import text_demo_capacity, text_raw_datastate, text_tokens_datastate


def _populated_layer():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION, CATEGORY_PATH_FINDING))
    cl.register_datastate(text_raw_datastate())
    cl.register_datastate(text_tokens_datastate())
    cl.register_capacity(text_demo_capacity())
    return cl


def test_view_construct_and_repr():
    cl = _populated_layer()
    v = cl.global_view()
    assert isinstance(v, CapacityLayerView)
    r = repr(v)
    assert "CapacityLayerView" in r


def test_iter_categories_yields_bare_names_sorted_by_role():
    cl = _populated_layer()
    cats = list(cl.global_view().iter_categories())
    assert "perception" in cats
    assert "path-finding" in cats
    assert "datastates" not in cats


def test_category_graph_resolves_known_category():
    cl = _populated_layer()
    g = cl.global_view().category_graph(CATEGORY_PERCEPTION)
    assert g is not None
    assert g.role == "capacity:perception"


def test_category_graph_returns_none_for_unknown_category():
    cl = _populated_layer()
    g = cl.global_view().category_graph("nonexistent-category")
    assert g is None


def test_datastates_graph_returns_shared_graph():
    cl = _populated_layer()
    g = cl.global_view().datastates_graph()
    assert g is not None
    assert g.role == "capacity:datastates"


def test_get_capacity_searches_across_categories():
    cl = _populated_layer()
    cap = text_demo_capacity()
    node = cl.global_view().get_capacity(cap.iri)
    assert node is not None
    assert node.node_id == cap.iri
    assert node.type_name == NODE_TYPE_CAPACITY


def test_get_capacity_returns_none_for_unknown_iri():
    cl = _populated_layer()
    assert cl.global_view().get_capacity("capacity:perception:nonexistent") is None


def test_get_datastate_resolves_and_returns_none_for_unknown():
    cl = _populated_layer()
    raw = text_raw_datastate()
    node = cl.global_view().get_datastate(raw.iri)
    assert node is not None
    assert node.type_name == NODE_TYPE_DATASTATE
    assert cl.global_view().get_datastate("datastate:nonexistent") is None


def test_iter_capacities_unfiltered_and_filtered():
    cl = _populated_layer()
    v = cl.global_view()
    all_caps = list(v.iter_capacities())
    assert len(all_caps) == 1
    perception_caps = list(v.iter_capacities(CATEGORY_PERCEPTION))
    assert len(perception_caps) == 1
    pathfind_caps = list(v.iter_capacities(CATEGORY_PATH_FINDING))
    assert pathfind_caps == []
    unknown_caps = list(v.iter_capacities("nonexistent-category"))
    assert unknown_caps == []


def test_iter_datastates_yields_registered():
    cl = _populated_layer()
    dss = list(cl.global_view().iter_datastates())
    iris = {n.node_id for n in dss}
    assert text_raw_datastate().iri in iris
    assert text_tokens_datastate().iri in iris


def test_empty_metagraph_iter_datastates_returns_empty_iterator():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    alice_view = cl.local_view("alice")
    assert list(alice_view.iter_datastates()) == []
    assert alice_view.get_datastate("datastate:anything") is None
