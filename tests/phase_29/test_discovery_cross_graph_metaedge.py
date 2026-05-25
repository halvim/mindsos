"""Phase 29 — cross-category producer/consumer drives MetaEdge code path."""

from __future__ import annotations

from mindsos_capacity import (
    CATEGORY_COMPREHENSION,
    CATEGORY_PERCEPTION,
    CapacityLayer,
    EDGE_TYPE_COMPAT,
)

from ._fixtures import (
    analysis_sentiment_datastate,
    sentiment_capacity,
    text_demo_capacity,
    text_raw_datastate,
    text_tokens_datastate,
)


def _layer():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION, CATEGORY_COMPREHENSION))
    cl.register_datastate(text_raw_datastate())
    cl.register_datastate(text_tokens_datastate())
    cl.register_datastate(analysis_sentiment_datastate())
    return cl


def test_cross_category_writes_metaedge_not_edge():
    cl = _layer()
    cl.register_capacity(text_demo_capacity())  # PERCEPTION: out=tokens
    cl.register_capacity(sentiment_capacity())  # COMPREHENSION: in=tokens

    mg = cl.global_metagraph()
    # No intra-graph TYPE_COMPAT edges expected (the two capacities live
    # in different category graphs).
    intra = [
        e for g in mg.graphs.values()
        for e in g.edges.values() if e.type_name == EDGE_TYPE_COMPAT
    ]
    assert intra == []
    # Exactly one cross-graph MetaEdge (text.demo → text.sentiment via tokens).
    metas = [me for me in mg.metaedges.values() if me.type_name == EDGE_TYPE_COMPAT]
    assert len(metas) == 1


def test_metaedge_carries_capacity_ids_and_label():
    cl = _layer()
    cl.register_capacity(text_demo_capacity())
    cl.register_capacity(sentiment_capacity())
    mg = cl.global_metagraph()
    me = next(me for me in mg.metaedges.values() if me.type_name == EDGE_TYPE_COMPAT)
    assert me.properties["source_capacity"] == text_demo_capacity().iri
    assert me.properties["target_capacity"] == sentiment_capacity().iri
    assert me.properties["via_datastate"] == text_tokens_datastate().iri
    assert me.properties["discovered_automatically"] is True
    assert me.properties["strictness"] == "strict"
    assert me.label == f"{text_demo_capacity().iri} -> {sentiment_capacity().iri}"


def test_metaedge_endpoints_match_category_graphs():
    cl = _layer()
    cl.register_capacity(text_demo_capacity())
    cl.register_capacity(sentiment_capacity())
    mg = cl.global_metagraph()
    me = next(me for me in mg.metaedges.values() if me.type_name == EDGE_TYPE_COMPAT)
    src_graph = mg.graphs[me.source_graph_id]
    tgt_graph = mg.graphs[me.target_graph_id]
    assert src_graph.role == "capacity:perception"
    assert tgt_graph.role == "capacity:comprehension"
