"""End-to-end: persist soft-deleted state → load via MetagraphLoader → fields preserved."""

from __future__ import annotations

import pytest

from mindsos_core import Graph, Metagraph
from mindsos_core.persistence import MetagraphRepository
from mindsos_core.persistence.bootstrap import bootstrap
from mindsos_core.reconstruction.metagraph_loader import MetagraphLoader

pytestmark = pytest.mark.integration


def _seed(client) -> tuple[Metagraph, str, str, str]:
    bootstrap(client)
    mg = Metagraph(name="int-persist-load")
    g1 = Graph(name="ont", role="ontology")
    g2 = Graph(name="lex", role="lexicon")
    mg.add_graph(g1); mg.add_graph(g2)
    n1 = g1.add_node(value="alice", type_name="Person")
    n2 = g1.add_node(value="bob", type_name="Person")
    e = g1.add_edge(source=n1, target=n2, type_name="KNOWS")
    he = g1.add_hyperedge(nodes={n1, n2}, type_name="LINKS")
    me = mg.add_metaedge(source_graph_id=g1.graph_id, target_graph_id=g2.graph_id, type_name="ALIGNS")
    return mg, e.edge_id, he.edge_id, me.edge_id


def test_metaedge_soft_delete_round_trip(falkor_client):
    """Phase 10 round-trip — deprecate metaedge → persist → load → field preserved."""
    mg, _, _, me_id = _seed(falkor_client)
    mg.deprecate_metaedge(me_id)
    MetagraphRepository(falkor_client).persist(mg)
    loaded = MetagraphLoader(falkor_client).load(mg.metagraph_id, include_deprecated=True)
    assert me_id in loaded.metaedges
    assert loaded.metaedges[me_id].deprecated_at is not None


def test_edge_soft_delete_round_trip(falkor_client):
    """Graph-side Edge soft-delete survives persist + load."""
    mg, e_id, _, _ = _seed(falkor_client)
    g_ont = next(g for g in mg.graphs.values() if g.name == "ont")
    g_ont.deprecate_edge(e_id)
    g_ont.dispute_edge(e_id)
    MetagraphRepository(falkor_client).persist(mg)
    loaded = MetagraphLoader(falkor_client).load(mg.metagraph_id, include_deprecated=True)
    g_loaded = next(g for g in loaded.graphs.values() if g.name == "ont")
    assert g_loaded.edges[e_id].deprecated_at is not None
    assert g_loaded.edges[e_id].disputed_at is not None


def test_load_include_deprecated_false_filters_metaedges(falkor_client):
    """Default include_deprecated=False — deprecated metaedges NOT materialized."""
    mg, _, _, me_id = _seed(falkor_client)
    mg.deprecate_metaedge(me_id)
    MetagraphRepository(falkor_client).persist(mg)
    loaded = MetagraphLoader(falkor_client).load(mg.metagraph_id)  # default False
    assert me_id not in loaded.metaedges


def test_load_include_deprecated_true_passes_metaedges(falkor_client):
    """include_deprecated=True — deprecated metaedges loaded normally."""
    mg, _, _, me_id = _seed(falkor_client)
    mg.deprecate_metaedge(me_id)
    MetagraphRepository(falkor_client).persist(mg)
    loaded = MetagraphLoader(falkor_client).load(mg.metagraph_id, include_deprecated=True)
    assert me_id in loaded.metaedges


def test_loader_clears_soft_delete_dirty(falkor_client):
    """PB-6a — load + refresh leave _soft_delete_dirty empty (state already in DB)."""
    from mindsos_core import SoftDeleteKind
    mg, e_id, _, me_id = _seed(falkor_client)
    g_ont = next(g for g in mg.graphs.values() if g.name == "ont")
    g_ont.deprecate_edge(e_id)
    mg.deprecate_metaedge(me_id)
    MetagraphRepository(falkor_client).persist(mg)
    loaded = MetagraphLoader(falkor_client).load(mg.metagraph_id, include_deprecated=True)
    assert all(len(loaded._soft_delete_dirty[k]) == 0 for k in loaded._soft_delete_dirty)
    for g in loaded.graphs.values():
        assert all(len(g._soft_delete_dirty[k]) == 0 for k in g._soft_delete_dirty)
