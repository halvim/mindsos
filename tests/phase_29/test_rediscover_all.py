"""Phase 29 — rediscover_all drops auto edges + rebuilds from scratch."""

from __future__ import annotations

from mindsos_capacity import (
    CATEGORY_COMPREHENSION,
    CATEGORY_PERCEPTION,
    CapacityLayer,
    EDGE_TYPE_COMPAT,
    rediscover_all,
)

from ._fixtures import (
    analysis_sentiment_datastate,
    sentiment_capacity,
    text_demo_capacity,
    text_join_capacity,
    text_raw_datastate,
    text_tokens_datastate,
)


def _populated_layer():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION, CATEGORY_COMPREHENSION))
    cl.register_datastate(text_raw_datastate())
    cl.register_datastate(text_tokens_datastate())
    cl.register_datastate(analysis_sentiment_datastate())
    cl.register_capacity(text_demo_capacity())
    cl.register_capacity(text_join_capacity())
    cl.register_capacity(sentiment_capacity())
    return cl


def _count_auto_edges(mg):
    intra = sum(
        1 for g in mg.graphs.values()
        for e in g.edges.values()
        if e.type_name == EDGE_TYPE_COMPAT
        and e.properties.get("discovered_automatically") is True
    )
    meta = sum(
        1 for me in mg.metaedges.values()
        if me.type_name == EDGE_TYPE_COMPAT
        and me.properties.get("discovered_automatically") is True
    )
    return intra, meta


def test_rediscover_all_idempotent():
    """Running rediscover twice produces the same edge counts."""
    cl = _populated_layer()
    mg = cl.global_metagraph()
    before = _count_auto_edges(mg)
    rediscover_all(mg, capacity_index=cl._capacity_index[mg.metagraph_id])
    after_one = _count_auto_edges(mg)
    rediscover_all(mg, capacity_index=cl._capacity_index[mg.metagraph_id])
    after_two = _count_auto_edges(mg)
    assert before == after_one == after_two


def test_rediscover_all_drops_then_rebuilds_intra_and_meta_edges():
    cl = _populated_layer()
    mg = cl.global_metagraph()
    intra_before, meta_before = _count_auto_edges(mg)
    assert intra_before >= 1  # demo↔join in PERCEPTION
    assert meta_before >= 1   # demo→sentiment cross-graph
    rediscover_all(mg, capacity_index=cl._capacity_index[mg.metagraph_id])
    intra_after, meta_after = _count_auto_edges(mg)
    assert (intra_after, meta_after) == (intra_before, meta_before)


def test_capacity_layer_rediscover_returns_created_edges():
    """Layer.rediscover wraps rediscover_all and returns the created list."""
    cl = _populated_layer()
    created = cl.rediscover()
    # Mix of intra-graph Edges and cross-graph MetaEdges.
    assert len(created) >= 2
