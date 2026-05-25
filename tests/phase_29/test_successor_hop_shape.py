"""Phase 29 — SuccessorHop dataclass shape + frozen invariants."""

from __future__ import annotations

import dataclasses

import pytest

from mindsos_capacity import SuccessorHop


def test_successor_hop_has_six_fields():
    fields = {f.name for f in dataclasses.fields(SuccessorHop)}
    assert fields == {
        "source_capacity",
        "target_capacity",
        "via_datastate",
        "same_category",
        "strictness",
        "adapter_capacity",
    }


def test_successor_hop_is_frozen():
    h = SuccessorHop(
        source_capacity="capacity:a:x",
        target_capacity="capacity:b:y",
        via_datastate="datastate:foo",
        same_category=True,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        h.strictness = "adapter"  # type: ignore[misc]


def test_successor_hop_defaults_strict_and_none_adapter():
    h = SuccessorHop(
        source_capacity="capacity:a:x",
        target_capacity="capacity:b:y",
        via_datastate="datastate:foo",
        same_category=False,
    )
    assert h.strictness == "strict"
    assert h.adapter_capacity is None
