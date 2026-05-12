"""Cascade observer + mg.identity unregister + SubGraphInstance routing
+ atomicity (Phase 06 row §F + round-7 P56 A + P59 A + P65 A)."""

from __future__ import annotations

import pytest

from mindsos_core import Graph, Metagraph
from mindsos_core.exceptions import IdentityError
import mindsos_instances as mi


# ── basic cascade (P31 A) ──────────────────────────────────────────────────


def test_removing_node_template_cascades_node_instance(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    template = next(iter(g.nodes.values()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=template.node_id,
        _registry=reg,
    )
    reg.add(ni)
    assert ni.id in reg
    g.remove_node(template.node_id)
    assert ni.id not in reg


def test_removing_edge_template_cascades_edge_instance(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    template = next(iter(g.edges.values()))
    ei = mi.EdgeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=template.edge_id,
        _registry=reg,
    )
    reg.add(ei)
    g.remove_edge(template.edge_id)
    assert ei.id not in reg


def test_removing_hyperedge_template_cascades_hyperedge_instance(
    mg_with_graph, reg
):
    g = next(iter(mg_with_graph.graphs.values()))
    template = next(iter(g.hyperedges.values()))
    hi = mi.HyperEdgeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=template.edge_id,
        _registry=reg,
    )
    reg.add(hi)
    g.remove_hyperedge(template.edge_id)
    assert hi.id not in reg


# ── recursive composite cascade (P44 A) ────────────────────────────────────


def test_composite_cascades_when_member_template_removed(
    mg_with_graph, reg
):
    g = next(iter(mg_with_graph.graphs.values()))
    template = next(iter(g.nodes.values()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=template.node_id,
        _registry=reg,
    )
    reg.add(ni)
    comp = mi.CompositeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        _registry=reg,
    )
    reg.add(comp)
    comp.add_member(ni, _registry=reg)
    g.remove_node(template.node_id)
    assert ni.id not in reg
    assert comp.id not in reg  # composite cascaded recursively


def test_nested_composite_cascades(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    template = next(iter(g.nodes.values()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=template.node_id,
        _registry=reg,
    )
    reg.add(ni)
    inner = mi.CompositeInstance(
        metagraph_id=mg_with_graph.metagraph_id, _registry=reg
    )
    reg.add(inner)
    inner.add_member(ni, _registry=reg)
    outer = mi.CompositeInstance(
        metagraph_id=mg_with_graph.metagraph_id, _registry=reg
    )
    reg.add(outer)
    outer.add_member(inner, _registry=reg)
    g.remove_node(template.node_id)
    assert all(x not in reg for x in (ni.id, inner.id, outer.id))


# ── mg.identity unregister (round-7 P56 A) ─────────────────────────────────


def test_cascade_unregisters_mg_identity(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    template = next(iter(g.nodes.values()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=template.node_id,
        _registry=reg,
    )
    reg.add(ni)
    assert ni.id in mg_with_graph.identity
    g.remove_node(template.node_id)
    assert ni.id not in mg_with_graph.identity


# ── SubGraphInstance referenced-element routing (round-7 P59 A) ────────────


def test_subgraph_cascades_when_referenced_node_removed(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    edge_id = next(iter(g.edges.keys()))
    e = g.edges[edge_id]
    sgi = mi.SubGraphInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=g.graph_id,
        overrides={
            "node_ids": [e.source.node_id, e.target.node_id],
            "edge_ids": [edge_id],
        },
        _registry=reg,
    )
    reg.add(sgi)
    # Remove the source node → also removes the edge (Graph cascade) →
    # observer fires for both. SubGraphInstance referenced both → cascades.
    g.remove_node(e.source.node_id)
    assert sgi.id not in reg


def test_subgraph_cascades_when_referenced_edge_removed_directly(
    mg_with_graph, reg
):
    g = next(iter(mg_with_graph.graphs.values()))
    edge_id = next(iter(g.edges.keys()))
    e = g.edges[edge_id]
    sgi = mi.SubGraphInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=g.graph_id,
        overrides={
            "node_ids": [e.source.node_id, e.target.node_id],
            "edge_ids": [edge_id],
        },
        _registry=reg,
    )
    reg.add(sgi)
    g.remove_edge(edge_id)  # direct edge removal
    assert sgi.id not in reg


# ── atomicity on observer-callback exception (round-7 P65 A) ───────────────


def test_observer_exception_aborts_remove(mg_with_graph, reg):
    """If an observer raises, the Core remove method does NOT mutate."""
    g = next(iter(mg_with_graph.graphs.values()))
    template = next(iter(g.nodes.values()))

    # Register a malicious observer that raises.
    def bad_observer(_id):
        raise RuntimeError("test failure")

    g.register_remove_observer(bad_observer)

    nodes_before = dict(g.nodes)
    with pytest.raises(RuntimeError, match="test failure"):
        g.remove_node(template.node_id)
    # Node should still exist.
    assert template.node_id in g.nodes
    assert g.nodes == nodes_before


# ── GraphInstance cascade ──────────────────────────────────────────────────


def test_graph_instance_cascades_on_metagraph_remove_graph():
    mg = Metagraph(name="MG")
    reg = mi.attach_registry(mg)
    g = Graph(name="G")
    mg.add_graph(g)
    gi = mi.GraphInstance(
        metagraph_id=mg.metagraph_id,
        template_id=g.graph_id,
        _registry=reg,
    )
    reg.add(gi)
    mg.remove_graph(g.graph_id)
    assert gi.id not in reg


# ── newly-added graph also gets observer subscription ──────────────────────


def test_observer_subscribes_to_newly_added_graphs():
    """Round-7 P66 — graphs added AFTER attach_registry get per-Graph
    observer subscription via Metagraph's graph_added hook."""
    mg = Metagraph(name="MG")
    reg = mi.attach_registry(mg)
    g = Graph(name="G_LATE")
    mg.add_graph(g)  # fires graph_added_observer → registry subscribes
    n = g.add_node("late_node", type_name="T")
    ni = mi.NodeInstance(
        metagraph_id=mg.metagraph_id,
        template_id=n.node_id,
        _registry=reg,
    )
    reg.add(ni)
    g.remove_node(n.node_id)
    # P66 ensures the cascade fires.
    assert ni.id not in reg
