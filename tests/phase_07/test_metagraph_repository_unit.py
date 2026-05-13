"""MetagraphRepository unit tests + 4-step lifecycle (P96 A)."""

from __future__ import annotations

from mindsos_core.models.graph import Graph
from mindsos_core.models.metagraph import Metagraph
from mindsos_core.persistence import InMemoryClient, MetagraphRepository


def test_persist_emits_metagraph_anchor_with_schema_name() -> None:
    """P100 A — schema_name persists as plain Cypher property."""
    mg = Metagraph(name="mg1")
    # Phase 05c attaches schema by reference; simulate by setting field.
    mg.schema_name = "lex_v1"
    c = InMemoryClient()
    repo = MetagraphRepository(c)
    repo.persist(mg)
    anchor = c.calls[0][0]
    assert "MERGE (m:Metagraph" in anchor
    assert "m.schema_name = $schema_name" in anchor
    assert c.calls[0][1]["schema_name"] == "lex_v1"


def test_persist_emits_props_json_with_canonical_encoding() -> None:
    """P62 A — canonical JSON encoding (sort_keys + ensure_ascii=False)."""
    mg = Metagraph(name="mg1", properties={"core:k1": "v1", "kl:k2": "v2"})
    c = InMemoryClient()
    repo = MetagraphRepository(c)
    repo.persist(mg)
    params = c.calls[0][1]
    # sort_keys=True puts core: before kl:
    assert params["props_json"] == '{"core:k1":"v1","kl:k2":"v2"}'


def test_persist_observer_fires_after_core_writes() -> None:
    """M9 + P96 A step 3 — observer fires after Core writes."""
    mg = Metagraph(name="mg1")
    fired = []
    mg.register_persist_observer(lambda m: fired.append(m.metagraph_id))
    c = InMemoryClient()
    repo = MetagraphRepository(c)
    repo.persist(mg)
    assert fired == [mg.metagraph_id]


def test_persist_client_attribute_cleared_after_dispatch() -> None:
    """_persist_client is set during observer fire, cleared in finally."""
    mg = Metagraph(name="mg1")
    captured = []
    mg.register_persist_observer(lambda m: captured.append(getattr(m, "_persist_client", "ABSENT")))
    c = InMemoryClient()
    repo = MetagraphRepository(c)
    repo.persist(mg)
    # During dispatch, _persist_client was set to the client.
    assert captured[0] is c
    # After dispatch returns, the attribute is gone.
    assert not hasattr(mg, "_persist_client")


def test_persist_observer_exception_propagates() -> None:
    """Observer failure surfaces; Core+WAL state is consistent per P33 A."""
    import pytest

    mg = Metagraph(name="mg1")
    def _failer(m):
        raise RuntimeError("observer crashed")
    mg.register_persist_observer(_failer)
    c = InMemoryClient()
    repo = MetagraphRepository(c)
    with pytest.raises(RuntimeError, match="observer crashed"):
        repo.persist(mg)
    # Even on observer failure, cleanup ran.
    assert not hasattr(mg, "_persist_client")


def test_persist_emits_contained_graphs() -> None:
    """Step 1b — each contained graph routes through GraphRepository."""
    mg = Metagraph(name="mg1")
    g1 = Graph(name="g1")
    g2 = Graph(name="g2")
    mg.add_graph(g1)
    mg.add_graph(g2)
    c = InMemoryClient()
    repo = MetagraphRepository(c)
    repo.persist(mg)
    # Two graph anchors emitted.
    graph_anchors = [q for q, _ in c.calls if "MERGE (g:Graph" in q]
    assert len(graph_anchors) == 2


def test_persist_emits_metaedges_grouped_by_type() -> None:
    """Step 1c — MetaEdges batched per rel type."""
    from mindsos_core.models.metagraph import MetaEdge

    mg = Metagraph(name="mg1")
    g1 = Graph(name="g1"); g2 = Graph(name="g2"); g3 = Graph(name="g3")
    mg.add_graph(g1); mg.add_graph(g2); mg.add_graph(g3)
    me1 = MetaEdge(source_graph_id=g1.graph_id, target_graph_id=g2.graph_id, type_name="RELA")
    me2 = MetaEdge(source_graph_id=g2.graph_id, target_graph_id=g3.graph_id, type_name="RELB")
    mg.metaedges[me1.edge_id] = me1
    mg.metaedges[me2.edge_id] = me2

    c = InMemoryClient()
    repo = MetagraphRepository(c)
    repo.persist(mg)
    # Two UNWIND statements, one per rel type (RELA and RELB spliced).
    rela = [q for q, _ in c.calls if "[e:RELA " in q]
    relb = [q for q, _ in c.calls if "[e:RELB " in q]
    assert len(rela) == 1
    assert len(relb) == 1


def test_persist_emits_metahyperedges() -> None:
    """Step 1d — MetaHyperEdges UNWIND-batched."""
    from mindsos_core.models.metagraph import MetaHyperEdge

    mg = Metagraph(name="mg1")
    for nm in ("g1", "g2", "g3"):
        mg.add_graph(Graph(name=nm))
    gids = list(mg.graphs.keys())
    mh = MetaHyperEdge(graph_ids=gids, type_name="MHE")
    mg.metahyperedges[mh.edge_id] = mh

    c = InMemoryClient()
    repo = MetagraphRepository(c)
    repo.persist(mg)
    assert any("MetaHyperEdge" in q for q, _ in c.calls)
