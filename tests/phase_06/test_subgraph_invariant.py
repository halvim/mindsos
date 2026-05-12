"""SubGraphInstance strict edge-validity invariant (Phase 06 P20 A)."""

from __future__ import annotations

import pytest

import mindsos_instances as mi
from mindsos_instances.exceptions import SubGraphInvariantError


def test_subgraph_invariant_passes_with_consistent_subset(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    node_ids = list(g.nodes.keys())
    edge_id = next(iter(g.edges.keys()))
    e = g.edges[edge_id]
    # node_ids must contain both endpoints of the edge.
    subgraph_nodes = {e.source.node_id, e.target.node_id}
    sgi = mi.SubGraphInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=g.graph_id,
        overrides={"node_ids": list(subgraph_nodes), "edge_ids": [edge_id]},
        _registry=reg,
    )
    assert sgi.template_id == g.graph_id


def test_subgraph_invariant_rejects_edge_missing_endpoint(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    edge_id = next(iter(g.edges.keys()))
    e = g.edges[edge_id]
    # Only include ONE endpoint, then ask for the edge. Should fail.
    with pytest.raises(SubGraphInvariantError):
        mi.SubGraphInstance(
            metagraph_id=mg_with_graph.metagraph_id,
            template_id=g.graph_id,
            overrides={
                "node_ids": [e.source.node_id],
                "edge_ids": [edge_id],
            },
            _registry=reg,
        )


def test_subgraph_invariant_rejects_unknown_node_id(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    with pytest.raises(SubGraphInvariantError):
        mi.SubGraphInstance(
            metagraph_id=mg_with_graph.metagraph_id,
            template_id=g.graph_id,
            overrides={"node_ids": ["nonexistent-node"]},
            _registry=reg,
        )


def test_subgraph_invariant_rejects_unknown_edge_id(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    node_ids = list(g.nodes.keys())
    with pytest.raises(SubGraphInvariantError):
        mi.SubGraphInstance(
            metagraph_id=mg_with_graph.metagraph_id,
            template_id=g.graph_id,
            overrides={
                "node_ids": node_ids,
                "edge_ids": ["nonexistent-edge"],
            },
            _registry=reg,
        )


def test_subgraph_invariant_rejects_hyperedge_member_missing(
    mg_with_graph, reg
):
    g = next(iter(mg_with_graph.graphs.values()))
    he_id = next(iter(g.hyperedges.keys()))
    he = g.hyperedges[he_id]
    # Include only the first member, ask for the hyperedge. Should fail.
    first_member = next(iter(he.nodes))
    with pytest.raises(SubGraphInvariantError):
        mi.SubGraphInstance(
            metagraph_id=mg_with_graph.metagraph_id,
            template_id=g.graph_id,
            overrides={
                "node_ids": [first_member.node_id],
                "edge_ids": [he_id],
            },
            _registry=reg,
        )


def test_subgraph_template_must_be_contained_graph(mg_with_graph, reg):
    with pytest.raises(SubGraphInvariantError):
        mi.SubGraphInstance(
            metagraph_id=mg_with_graph.metagraph_id,
            template_id="some-bogus-graph-id",
            overrides={"node_ids": [], "edge_ids": []},
            _registry=reg,
        )


def test_subgraph_empty_subset_legal(mg_with_graph, reg):
    g = next(iter(mg_with_graph.graphs.values()))
    sgi = mi.SubGraphInstance(
        metagraph_id=mg_with_graph.metagraph_id,
        template_id=g.graph_id,
        overrides={"node_ids": [], "edge_ids": []},
        _registry=reg,
    )
    assert sgi.overrides["node_ids"] == frozenset()
    assert sgi.overrides["edge_ids"] == frozenset()
