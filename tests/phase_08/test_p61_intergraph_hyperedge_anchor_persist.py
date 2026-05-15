"""P61 A — Phase 07 anchor persist gap fix; :ANCHOR rels written + read."""

from __future__ import annotations

import pytest


def test_cypher_builder_includes_anchor_unwind() -> None:
    """The Phase 08 builder query writes :ANCHOR rels alongside :MEMBER."""
    from mindsos_core.cypher.builders import (
        build_unwind_create_intergraph_hyperedges,
    )

    q, p = build_unwind_create_intergraph_hyperedges(
        metagraph_id="m-1",
        rows=[
            {
                "id": "ih-1",
                "label": None,
                "ordered": True,
                "compositional": False,
                "props": {},
                "anchors": [{"node_id": "n1", "graph_id": "g1"}],
                "members": [
                    {"node_id": "n2", "graph_id": "g2"},
                    {"node_id": "n3", "graph_id": "g2"},
                ],
                "_version": 1,
            }
        ],
    )
    # Both :ANCHOR and :MEMBER UNWINDs present.
    assert "UNWIND row.anchors AS anc" in q
    assert ":ANCHOR" in q
    assert "UNWIND row.members AS mem" in q
    assert ":MEMBER" in q


def test_persist_row_includes_anchors_field() -> None:
    """metagraph_repository persist row construction includes ``anchors``."""
    from mindsos_core.models.graph import Graph
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import InMemoryClient, MetagraphRepository

    mg = Metagraph(name="m-anchors", identity=IdentityRegistry())
    g1 = Graph(name="g1", role="lex", identity=mg.identity)
    g2 = Graph(name="g2", role="ont", identity=mg.identity)
    n1 = g1.add_node(value="x", type_name="T", node_id="n1", _validate=False)
    n2 = g2.add_node(value="y", type_name="T", node_id="n2", _validate=False)
    n3 = g2.add_node(value="z", type_name="T", node_id="n3", _validate=False)
    mg.add_graph(g1)
    mg.add_graph(g2)
    mg.add_intergraph_hyperedge(
        anchors=[(g1.graph_id, "n1")],
        members=[(g2.graph_id, "n2"), (g2.graph_id, "n3")],
        type_name="COMPOSE",
        intergraph_hyperedge_id="ihe-1",
    )

    c = InMemoryClient()
    MetagraphRepository(c).persist(mg)

    # Find the intergraph_hyperedges builder call.
    found_anchor_row = False
    for q, p in c.calls:
        if "IntergraphHyperEdge" in q and "UNWIND row.anchors" in q:
            rows = p.get("rows") or []
            for row in rows:
                if "anchors" in row and row["anchors"]:
                    found_anchor_row = True
                    break
    assert found_anchor_row, (
        "Phase 08 P61 A — persist row construction must include "
        "non-empty `anchors` list when the IntergraphHyperEdge has "
        "anchors."
    )


@pytest.mark.integration
def test_intergraph_hyperedge_anchors_round_trip(falkor_client) -> None:
    """End-to-end — anchors persist + reload preserves the dataclass invariant."""
    from mindsos_core.models.graph import Graph
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import load_metagraph

    mg = Metagraph(name="ihe-rt", identity=IdentityRegistry())
    g1 = Graph(name="g1", role="lex", identity=mg.identity)
    g2 = Graph(name="g2", role="ont", identity=mg.identity)
    g1.add_node(value="x", type_name="T", node_id="n1", _validate=False)
    g2.add_node(value="y", type_name="T", node_id="n2", _validate=False)
    g2.add_node(value="z", type_name="T", node_id="n3", _validate=False)
    mg.add_graph(g1)
    mg.add_graph(g2)
    mg.add_intergraph_hyperedge(
        anchors=[(g1.graph_id, "n1")],
        members=[(g2.graph_id, "n2"), (g2.graph_id, "n3")],
        type_name="COMPOSE",
        intergraph_hyperedge_id="ihe-rt-1",
    )

    MetagraphRepository(falkor_client).persist(mg)
    mg2 = load_metagraph(falkor_client, mg.metagraph_id)

    assert "ihe-rt-1" in mg2.intergraph_hyperedges
    ihe2 = mg2.intergraph_hyperedges["ihe-rt-1"]
    assert len(ihe2.anchors) == 1
    assert len(ihe2.members) == 2
