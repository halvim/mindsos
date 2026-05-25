"""Phase 29 — CapacityLayerView.successors_of walks intra + cross edges."""

from __future__ import annotations

from mindsos_capacity import (
    CATEGORY_COMPREHENSION,
    CATEGORY_PERCEPTION,
    CapacityLayer,
    SuccessorHop,
)

from ._fixtures import (
    analysis_sentiment_datastate,
    sentiment_capacity,
    text_demo_capacity,
    text_join_capacity,
    text_raw_datastate,
    text_tokens_datastate,
)


def _layer():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION, CATEGORY_COMPREHENSION))
    cl.register_datastate(text_raw_datastate())
    cl.register_datastate(text_tokens_datastate())
    cl.register_datastate(analysis_sentiment_datastate())
    return cl


def test_successors_of_unknown_capacity_returns_empty():
    cl = _layer()
    view = cl.global_view()
    assert view.successors_of("capacity:perception:nonexistent") == []


def test_successors_of_no_peers_returns_empty():
    """Single capacity in metagraph — no successors."""
    cl = _layer()
    cl.register_capacity(text_demo_capacity())
    view = cl.global_view()
    assert view.successors_of(text_demo_capacity().iri) == []


def test_successors_of_intra_category_returns_same_category_hop():
    cl = _layer()
    cl.register_capacity(text_demo_capacity())
    cl.register_capacity(text_join_capacity())
    view = cl.global_view()
    hops = view.successors_of(text_demo_capacity().iri)
    assert all(isinstance(h, SuccessorHop) for h in hops)
    # demo → join via tokens — same_category=True.
    target_iris = {h.target_capacity for h in hops}
    assert text_join_capacity().iri in target_iris
    for h in hops:
        if h.target_capacity == text_join_capacity().iri:
            assert h.same_category is True
            assert h.strictness == "strict"
            assert h.adapter_capacity is None
            assert h.via_datastate == text_tokens_datastate().iri


def test_successors_of_cross_category_returns_metaedge_hop():
    cl = _layer()
    cl.register_capacity(text_demo_capacity())
    cl.register_capacity(sentiment_capacity())
    view = cl.global_view()
    hops = view.successors_of(text_demo_capacity().iri)
    # Expect 1 hop: demo → sentiment via tokens (cross-graph MetaEdge).
    cross_hops = [h for h in hops if h.same_category is False]
    assert len(cross_hops) == 1
    h = cross_hops[0]
    assert h.source_capacity == text_demo_capacity().iri
    assert h.target_capacity == sentiment_capacity().iri
    assert h.via_datastate == text_tokens_datastate().iri
    assert h.strictness == "strict"
    assert h.adapter_capacity is None
