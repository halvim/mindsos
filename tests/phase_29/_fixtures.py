"""Phase 29 — fixtures driving auto-discovery + walks tests.

Builds on Phase 28's `tests/phase_28/_fixtures.py` text-realm. Adds:

- A second DataState (``analysis.sentiment``) for cross-category producer/
  consumer discovery scenarios.
- A capacity in a different category (``CATEGORY_COMPREHENSION``) that
  consumes ``text.tokens`` — drives the cross-graph MetaEdge code path.
- A "consumer" capacity in the same category (``CATEGORY_PERCEPTION``)
  that consumes ``text.tokens`` — drives the intra-graph Edge code path.

All fixtures hand-rolled — no Phase 31 builtins dependency.
"""

from __future__ import annotations

from mindsos_capacity import (
    CATEGORY_COMPREHENSION,
    CATEGORY_PERCEPTION,
    Capacity,
    DataState,
    ShapeDescriptor,
)


def text_raw_datastate() -> DataState:
    return DataState(
        name="text.raw",
        shape=ShapeDescriptor.scalar("str", opaque_tag="text.raw"),
    )


def text_tokens_datastate() -> DataState:
    return DataState(
        name="text.tokens",
        shape=ShapeDescriptor.list_of("str", opaque_tag="text.tokens"),
    )


def analysis_sentiment_datastate() -> DataState:
    return DataState(
        name="analysis.sentiment",
        shape=ShapeDescriptor.scalar("float", opaque_tag="analysis.sentiment"),
    )


def text_demo_capacity() -> Capacity:
    """Perception capacity: text.raw → text.tokens."""
    raw = text_raw_datastate()
    tokens = text_tokens_datastate()
    return Capacity(
        name="text.demo",
        category=CATEGORY_PERCEPTION,
        inputs=(raw.iri,),
        outputs=(tokens.iri,),
        implementation=lambda **kw: {tokens.iri: kw[raw.iri].split()},
    )


def text_join_capacity() -> Capacity:
    """Intra-category consumer in PERCEPTION — drives intra-graph Edge path.

    Consumes text.tokens → text.raw (round-trip / re-join).
    """
    raw = text_raw_datastate()
    tokens = text_tokens_datastate()
    return Capacity(
        name="text.join",
        category=CATEGORY_PERCEPTION,
        inputs=(tokens.iri,),
        outputs=(raw.iri,),
        implementation=lambda **kw: {raw.iri: " ".join(kw[tokens.iri])},
    )


def sentiment_capacity() -> Capacity:
    """Cross-category consumer in COMPREHENSION — drives MetaEdge path.

    Consumes text.tokens → analysis.sentiment.
    """
    tokens = text_tokens_datastate()
    sentiment = analysis_sentiment_datastate()
    return Capacity(
        name="text.sentiment",
        category=CATEGORY_COMPREHENSION,
        inputs=(tokens.iri,),
        outputs=(sentiment.iri,),
        implementation=lambda **kw: {sentiment.iri: 0.5},
    )


__all__ = [
    "text_raw_datastate",
    "text_tokens_datastate",
    "analysis_sentiment_datastate",
    "text_demo_capacity",
    "text_join_capacity",
    "sentiment_capacity",
]
