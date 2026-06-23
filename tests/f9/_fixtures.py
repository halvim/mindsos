"""F9 — shared fixtures for the re-activation tests.

Hand-rolled DataState + descriptor shapes (no Phase 31 builtins
dependency), mirroring the Phase 28 fixture style.
"""

from __future__ import annotations

from typing import Any, Dict

from mindsos_capacity import (
    Capacity,
    CATEGORY_PERCEPTION,
    DataState,
    REACTIVATION_KEY,
    ShapeDescriptor,
)


def raw_ds() -> DataState:
    return DataState(
        name="text.raw",
        shape=ShapeDescriptor.scalar("str", opaque_tag="text.raw"),
    )


def tokens_ds() -> DataState:
    return DataState(
        name="text.tokens",
        shape=ShapeDescriptor.list_of("str", opaque_tag="text.tokens"),
    )


def taught_descriptor(reactivation_key: str = "taught") -> Dict[str, Any]:
    """A PB-F-enriched ``learned-parameters`` value dict.

    Carries the shipped taught-composite fields plus the full declaration
    spec (``category``/``inputs``/``outputs``/``node_kind``) and the
    ``reactivation_key`` naming the factory. DataState *definitions* are
    NOT carried — they resolve cross-scope via ADR-0185 §A2′.
    """
    return {
        "capability": "text.demo",
        "steps": ["upper"],
        "requires_affordances": [],
        "cache_key": None,
        "source": "device-1",
        REACTIVATION_KEY: reactivation_key,
        "category": CATEGORY_PERCEPTION,
        "inputs": [raw_ds().iri],
        "outputs": [tokens_ds().iri],
        "node_kind": "reactive",
    }


def taught_factory(desc):
    """Rebuild the taught composite, binding a fresh (non-serialized) impl."""
    out = desc["outputs"][0]
    inp = desc["inputs"][0]
    return Capacity(
        name=desc["capability"],
        category=desc["category"],
        inputs=tuple(desc["inputs"]),
        outputs=tuple(desc["outputs"]),
        implementation=lambda **kw: {out: kw[inp].upper()},
    )


class DuckSession:
    """Minimal Local-scoped session (the Local register/invoke path uses
    only ``user_id``; never ``.has()``)."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.session_id = f"sess-{user_id}"

    def has(self, _cap) -> bool:  # pragma: no cover - never hit on Local path
        return False
