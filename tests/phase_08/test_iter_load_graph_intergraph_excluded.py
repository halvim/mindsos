"""RPB-10 A — iter_load_graph skips IntergraphEdge / IntergraphHyperEdge."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def test_iter_load_graph_skips_intergraph_primitives(falkor_client) -> None:
    """RPB-10 A — cross-graph primitives load via MetagraphLoader only."""
    from mindsos_core.models.graph import Graph
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import iter_load_graph

    mg = Metagraph(name="m1", identity=IdentityRegistry())
    g1 = Graph(name="g1", role="lex", identity=mg.identity)
    g2 = Graph(name="g2", role="ont", identity=mg.identity)
    n1 = g1.add_node(value="x", type_name="T", node_id="n1", _validate=False)
    n2 = g2.add_node(value="y", type_name="T", node_id="n2", _validate=False)
    mg.add_graph(g1)
    mg.add_graph(g2)
    # Cross-graph IntergraphEdge — should NOT load via iter_load_graph.
    mg.add_intergraph_edge(
        source_graph_id=g1.graph_id,
        source_node_id="n1",
        target_graph_id=g2.graph_id,
        target_node_id="n2",
        type_name="ALIGNS",
        edge_id="ie-1",
    )

    MetagraphRepository(falkor_client).persist(mg)

    # iter_load_graph for g1 alone — should NOT carry the intergraph
    # edge in its assembled `g1.edges` (which holds intra-graph edges
    # only per ADR-0021).
    last = None
    for partial in iter_load_graph(
        falkor_client, g1.graph_id, batch_size=100,
    ):
        last = partial
    assert last is not None
    # No intra-graph edges were added; the intergraph edge is not in
    # the per-Graph view.
    assert "ie-1" not in last.edges
