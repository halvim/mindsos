"""MetagraphRepository.persist Step 1h drain emits soft-delete writes to real DB."""

from __future__ import annotations

import pytest

from mindsos_core import Graph, Metagraph
from mindsos_core.persistence import MetagraphRepository
from mindsos_core.persistence.bootstrap import bootstrap

pytestmark = pytest.mark.integration


def test_metaedge_deprecate_persists_to_db(falkor_client):
    bootstrap(falkor_client)
    mg = Metagraph(name="int-drain-emit")
    g1, g2 = Graph(name="g1", role="ont"), Graph(name="g2", role="lex")
    mg.add_graph(g1); mg.add_graph(g2)
    me = mg.add_metaedge(source_graph_id=g1.graph_id, target_graph_id=g2.graph_id, type_name="ALIGNS")

    mg.deprecate_metaedge(me.edge_id)
    MetagraphRepository(falkor_client).persist(mg)

    res = falkor_client.run_query(
        "MATCH (:Graph)-[e {id: $eid, metagraph_id: $mid}]->(:Graph) "
        "RETURN e.deprecated_at AS dep",
        {"eid": me.edge_id, "mid": mg.metagraph_id},
    )
    assert res.rows
    assert res.rows[0]["dep"] is not None


def test_edge_deprecate_persists_to_db(falkor_client):
    """Graph-side dirty drain emits per-edge SET cypher."""
    bootstrap(falkor_client)
    mg = Metagraph(name="int-edge-drain")
    g = Graph(name="g", role="ont")
    mg.add_graph(g)
    n1 = g.add_node(value="a", type_name="Person")
    n2 = g.add_node(value="b", type_name="Person")
    e = g.add_edge(source=n1, target=n2, type_name="KNOWS")

    g.deprecate_edge(e.edge_id)
    MetagraphRepository(falkor_client).persist(mg)

    res = falkor_client.run_query(
        "MATCH ()-[r {id: $eid, graph_id: $gid}]->() "
        "RETURN r.deprecated_at AS dep",
        {"eid": e.edge_id, "gid": g.graph_id},
    )
    assert res.rows
    assert res.rows[0]["dep"] is not None
