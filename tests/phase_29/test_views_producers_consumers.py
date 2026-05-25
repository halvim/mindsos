"""Phase 29 — CapacityLayerView.producers_of + consumers_of walks."""

from __future__ import annotations

from mindsos_capacity import (
    CATEGORY_COMPREHENSION,
    CATEGORY_PERCEPTION,
    CapacityLayer,
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
    cl.register_capacity(text_demo_capacity())
    cl.register_capacity(text_join_capacity())
    cl.register_capacity(sentiment_capacity())
    return cl


def test_producers_of_tokens_returns_text_demo():
    view = _layer().global_view()
    tokens_iri = text_tokens_datastate().iri
    iris = {n.node_id for n in view.producers_of(tokens_iri)}
    assert text_demo_capacity().iri in iris
    # text.join also produces text.raw, not tokens.
    assert text_join_capacity().iri not in iris


def test_consumers_of_tokens_returns_join_and_sentiment():
    view = _layer().global_view()
    tokens_iri = text_tokens_datastate().iri
    iris = {n.node_id for n in view.consumers_of(tokens_iri)}
    assert text_join_capacity().iri in iris
    assert sentiment_capacity().iri in iris


def test_producers_consumers_unknown_datastate_returns_empty():
    view = _layer().global_view()
    assert view.producers_of("datastate:nonexistent") == []
    assert view.consumers_of("datastate:nonexistent") == []


def test_producers_consumers_symmetric_for_known_match():
    """A capacity that produces X is in producers_of(X); same for consumers."""
    view = _layer().global_view()
    raw_iri = text_raw_datastate().iri
    # text.demo consumes raw, text.join produces raw.
    consumer_iris = {n.node_id for n in view.consumers_of(raw_iri)}
    producer_iris = {n.node_id for n in view.producers_of(raw_iri)}
    assert text_demo_capacity().iri in consumer_iris
    assert text_join_capacity().iri in producer_iris
