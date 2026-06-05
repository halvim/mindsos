"""Phase 40 — strict-by-default DataState realm validation (ADR-0158)."""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    CapacityLayer,
    CapacityRegistrationError,
    DataState,
    ShapeDescriptor,
)
from mindsos_capacity.identifiers import RESERVED_REALMS


def _layer() -> CapacityLayer:
    return CapacityLayer(categories=(CATEGORY_PERCEPTION,))


def _ds(name: str) -> DataState:
    return DataState(name=name, shape=ShapeDescriptor.scalar("str"))


def test_nine_reserved_realms():
    assert RESERVED_REALMS == frozenset({
        "core",
        "marker",
        "bridge",
        "text",
        "mm",
        "problem_trace",
        "nlu",
        "code",
        "dream",
    })


def test_reserved_realm_single_dot_accepted():
    layer = _layer()
    node = layer.register_datastate(_ds("mm.realm_ok"))
    assert node is not None


def test_bare_name_rejected():
    layer = _layer()
    with pytest.raises(CapacityRegistrationError):
        layer.register_datastate(_ds("bareword"))


def test_multi_dot_rejected():
    layer = _layer()
    with pytest.raises(CapacityRegistrationError):
        layer.register_datastate(_ds("mm.alpha.beta"))


def test_unknown_realm_rejected_by_default():
    layer = _layer()
    with pytest.raises(CapacityRegistrationError):
        layer.register_datastate(_ds("zzz.thing"))


def test_unknown_realm_accepted_with_opt_in():
    layer = _layer()
    node = layer.register_datastate(_ds("zzz.thing"), allow_new_realm=True)
    assert node is not None
