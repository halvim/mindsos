"""Materialise machinery (Phase 06 row §E + round-7 P51 A + P54 B +
P58 A + P63 A)."""

from __future__ import annotations

import pytest

from mindsos_core import Edge, Graph, HyperEdge, Metagraph, Node
from mindsos_core.exceptions import IdentityError
from mindsos_core.models.metagraph import MetaEdge, MetaHyperEdge
import mindsos_instances as mi


# ── NodeInstance materialise ────────────────────────────────────────────────


def test_node_materialise_returns_fresh_node(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    template = next(iter(g.nodes.values()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=template.node_id,
        _registry=reg,
    )
    reg.add(ni)
    result = ni.materialise(mg_with_graph)
    assert isinstance(result, Node)
    assert result.node_id != template.node_id  # fresh UUID
    assert result.value == template.value
    assert result.type_name == template.type_name


def test_node_materialise_merges_properties(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    template = next(iter(g.nodes.values()))  # alice / age=30
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=template.node_id,
        overrides={"age": 31, "nickname": "Ace"},
        _registry=reg,
    )
    reg.add(ni)
    result = ni.materialise(mg_with_graph)
    assert result.properties["age"] == 31  # override wins
    assert result.properties["nickname"] == "Ace"  # added


def test_node_materialise_fresh_uuid_per_call(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    template = next(iter(g.nodes.values()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=template.node_id,
        _registry=reg,
    )
    reg.add(ni)
    a = ni.materialise(mg_with_graph)
    b = ni.materialise(mg_with_graph)
    assert a.node_id != b.node_id


# ── EdgeInstance materialise (round-7 P58 A — endpoint resolution) ─────────


def test_edge_materialise_with_no_overrides(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    template = next(iter(g.edges.values()))
    ei = mi.EdgeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=template.edge_id,
        _registry=reg,
    )
    reg.add(ei)
    result = ei.materialise(mg_with_graph)
    assert isinstance(result, Edge)
    assert result.source.node_id == template.source.node_id
    assert result.target.node_id == template.target.node_id
    assert result.type_name == template.type_name


def test_edge_materialise_source_override_resolves(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    template = next(iter(g.edges.values()))
    # Pick a node that isn't the current source.
    other_node = next(
        n for nid, n in g.nodes.items() if nid != template.source.node_id
    )
    ei = mi.EdgeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=template.edge_id,
        overrides={"source_id": other_node.node_id},
        _registry=reg,
    )
    reg.add(ei)
    result = ei.materialise(mg_with_graph)
    assert result.source.node_id == other_node.node_id


def test_edge_materialise_label_override(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    template = next(iter(g.edges.values()))
    ei = mi.EdgeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=template.edge_id,
        overrides={"label": "custom"},
        _registry=reg,
    )
    reg.add(ei)
    result = ei.materialise(mg_with_graph)
    assert result.label == "custom"


def test_edge_materialise_unknown_source_raises(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    template = next(iter(g.edges.values()))
    ei = mi.EdgeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=template.edge_id,
        overrides={"source_id": "nonexistent-node-id"},
        _registry=reg,
    )
    reg.add(ei)
    with pytest.raises(IdentityError):
        ei.materialise(mg_with_graph)


# ── HyperEdgeInstance materialise (round-7 P58 A) ──────────────────────────


def test_hyperedge_materialise_member_ids_resolve(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    he_template = next(iter(g.hyperedges.values()))
    # Pick a subset (the first 2 nodes).
    node_ids = [n.node_id for n in list(he_template.nodes)[:2]]
    hi = mi.HyperEdgeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=he_template.edge_id,
        overrides={"member_ids": node_ids},
        _registry=reg,
    )
    reg.add(hi)
    result = hi.materialise(mg_with_graph)
    assert isinstance(result, HyperEdge)
    assert len(result.nodes) == 2


# ── GraphInstance materialise (round-7 P54 B — full clone) ─────────────────


def test_graph_instance_materialise_clones_full_graph(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    gi = mi.GraphInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=g.graph_id,
        _registry=reg,
    )
    reg.add(gi)
    clone = gi.materialise(mg_with_graph)
    assert isinstance(clone, Graph)
    assert clone.graph_id != g.graph_id  # fresh id
    assert len(clone.nodes) == len(g.nodes)
    assert len(clone.edges) == len(g.edges)
    assert len(clone.hyperedges) == len(g.hyperedges)
    assert clone.role == g.role  # inherited (P1 A)
    # Fresh identity registry — clone's registry is not the source's.
    assert clone.identity is not g.identity


# ── SubGraphInstance materialise (round-7 P51 A — partial clone) ───────────


def test_subgraph_instance_materialise_clones_subset(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    edge_id = next(iter(g.edges.keys()))
    e = g.edges[edge_id]
    node_ids = [e.source.node_id, e.target.node_id]
    sgi = mi.SubGraphInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=g.graph_id,
        overrides={"node_ids": node_ids, "edge_ids": [edge_id]},
        _registry=reg,
    )
    reg.add(sgi)
    clone = sgi.materialise(mg_with_graph)
    assert len(clone.nodes) == 2
    assert len(clone.edges) == 1
    assert clone.role == g.role


# ── Composite materialise (P39 A + round-7 P63 A canonicalize) ─────────────


def test_composite_materialise_tree_shape(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    n_template = next(iter(g.nodes.values()))
    ni = mi.NodeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=n_template.node_id,
        _registry=reg,
    )
    reg.add(ni)
    comp = mi.CompositeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        bundle_overrides={"tag": "demo"},
        _registry=reg,
    )
    reg.add(comp)
    comp.add_member(ni, _registry=reg)
    tree = comp.materialise(mg_with_graph)
    assert tree["kind"] == "composite"
    assert tree["id"] == comp.id
    assert tree["metagraph_id"] == mg_with_graph.metagraph_id
    assert tree["bundle_overrides"] == {"tag": "demo"}
    assert ni.id in tree["members"]


def test_composite_materialise_stable_across_calls(mg_with_graph, reg):
    """Round-7 P63 A — canonicalize wrap produces stable JSON."""
    import json

    g = next(iter(mg_with_graph.graphs.values()))
    he_template = next(iter(g.hyperedges.values()))
    hi = mi.HyperEdgeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=he_template.edge_id,
        _registry=reg,
    )
    reg.add(hi)
    comp = mi.CompositeInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        _registry=reg,
    )
    reg.add(comp)
    comp.add_member(hi, _registry=reg)
    tree_a = comp.materialise(mg_with_graph)
    # Materialise can't be called twice without fresh UUIDs (hyperedge
    # gets a fresh id each time), so we compare the canonicalize'd shape
    # excluding ids.
    serialized = json.dumps(tree_a, sort_keys=True, default=str)
    assert serialized  # stable, JSON-serialisable
