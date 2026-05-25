"""Phase 28 — hand-rolled DataState + Capacity fixtures for register tests.

Per R0 PB-5 (a)/(c): NEW thin test files at Phase 28 use hand-rolled
fixtures (no Phase 31 builtins dependency). Common shapes hoisted here
so every register / local-wins / constraint test stays focused.
"""

from __future__ import annotations

from mindsos_capacity import (
    Capacity,
    CATEGORY_PERCEPTION,
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


def text_demo_capacity() -> Capacity:
    raw = text_raw_datastate()
    tokens = text_tokens_datastate()
    return Capacity(
        name="text.demo",
        category=CATEGORY_PERCEPTION,
        inputs=(raw.iri,),
        outputs=(tokens.iri,),
        implementation=lambda **kw: {tokens.iri: kw[raw.iri].split()},
    )


def text_demo_v2_capacity() -> Capacity:
    raw = text_raw_datastate()
    tokens = text_tokens_datastate()
    return Capacity(
        name="text.demo",
        category=CATEGORY_PERCEPTION,
        inputs=(raw.iri,),
        outputs=(tokens.iri,),
        implementation=lambda **kw: {tokens.iri: kw[raw.iri].split(",")},
    )


__all__ = [
    "text_raw_datastate",
    "text_tokens_datastate",
    "text_demo_capacity",
    "text_demo_v2_capacity",
]
