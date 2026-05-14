"""Integration — persist → load_metagraph → assert_metagraphs_equal round-trip.

Covers the 4 fixture variants from the Phase 08 row's Automated tests:
(a) single contained Graph; (b) 2 graphs + MetaEdges; (c) MetaHyperEdges
+ 3-graph fixture; (d) IntergraphEdges + IntergraphHyperEdges across 2
graphs.
"""

from __future__ import annotations

import pytest

from tests._shared.metagraph_equality import assert_metagraphs_equal


pytestmark = pytest.mark.integration


def _persist(client, mg):
    """Helper — persist mg through MetagraphRepository."""
    from mindsos_core.persistence import MetagraphRepository

    MetagraphRepository(client).persist(mg)


def _new_mg(name: str = "m1"):
    """Helper — fresh Metagraph with isolated identity registry."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph

    return Metagraph(name=name, identity=IdentityRegistry())


def _new_graph(mg, name: str, role: str, gid: str | None = None):
    from mindsos_core.models.graph import Graph

    g = Graph(name=name, role=role, identity=mg.identity, graph_id=gid)
    mg.add_graph(g)
    return g


def test_round_trip_single_contained_graph(falkor_client) -> None:
    """Fixture (a) — single contained Graph; 2 nodes; 1 edge."""
    from mindsos_core.reconstruction import load_metagraph

    mg = _new_mg("rt-a")
    g = _new_graph(mg, "g1", "lex")
    n1 = g.add_node(value="x", type_name="T", node_id="n1", _validate=False)
    n2 = g.add_node(value="y", type_name="T", node_id="n2", _validate=False)
    g.add_edge(
        source=n1, target=n2, type_name="LINKS",
        edge_id="e1", _validate=False,
    )

    _persist(falkor_client, mg)
    mg2 = load_metagraph(falkor_client, mg.metagraph_id)
    assert_metagraphs_equal(mg, mg2)


def test_round_trip_two_graphs_with_metaedges(falkor_client) -> None:
    """Fixture (b) — 2 graphs + MetaEdges."""
    from mindsos_core.reconstruction import load_metagraph

    mg = _new_mg("rt-b")
    g1 = _new_graph(mg, "g1", "lex")
    g2 = _new_graph(mg, "g2", "ont")
    mg.add_metaedge(
        source_graph_id=g1.graph_id,
        target_graph_id=g2.graph_id,
        type_name="ALIGNS_TO",
        edge_id="me-1",
    )

    _persist(falkor_client, mg)
    mg2 = load_metagraph(falkor_client, mg.metagraph_id)
    assert_metagraphs_equal(mg, mg2)


def test_round_trip_three_graphs_with_metahyperedges(falkor_client) -> None:
    """Fixture (c) — MetaHyperEdges + 3-graph fixture."""
    from mindsos_core.reconstruction import load_metagraph

    mg = _new_mg("rt-c")
    g1 = _new_graph(mg, "g1", "lex")
    g2 = _new_graph(mg, "g2", "ont")
    g3 = _new_graph(mg, "g3", "frames")
    mg.add_metahyperedge(
        graph_ids=[g1.graph_id, g2.graph_id, g3.graph_id],
        type_name="TRIPLE_LINK",
        edge_id="mhe-1",
    )

    _persist(falkor_client, mg)
    mg2 = load_metagraph(falkor_client, mg.metagraph_id)
    assert_metagraphs_equal(mg, mg2)


def test_round_trip_intergraph_edges_and_hyperedges(falkor_client) -> None:
    """Fixture (d) — IntergraphEdges + IntergraphHyperEdges across 2 graphs."""
    from mindsos_core.reconstruction import load_metagraph

    mg = _new_mg("rt-d")
    g1 = _new_graph(mg, "g1", "lex")
    g2 = _new_graph(mg, "g2", "ont")
    a1 = g1.add_node(value="a", type_name="T", node_id="a1", _validate=False)
    b1 = g1.add_node(value="b", type_name="T", node_id="b1", _validate=False)
    a2 = g2.add_node(value="a", type_name="T", node_id="a2", _validate=False)
    b2 = g2.add_node(value="b", type_name="T", node_id="b2", _validate=False)

    mg.add_intergraph_edge(
        source_graph_id=g1.graph_id,
        source_node_id="a1",
        target_graph_id=g2.graph_id,
        target_node_id="a2",
        type_name="ALIGNS",
        edge_id="ie-1",
    )
    mg.add_intergraph_hyperedge(
        anchors=[(g1.graph_id, "a1"), (g1.graph_id, "b1")],
        members=[(g2.graph_id, "a2"), (g2.graph_id, "b2")],
        type_name="COMPOSE",
        intergraph_hyperedge_id="ihe-1",
    )

    _persist(falkor_client, mg)
    mg2 = load_metagraph(falkor_client, mg.metagraph_id)
    assert_metagraphs_equal(mg, mg2)
