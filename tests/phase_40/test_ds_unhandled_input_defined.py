"""Phase 40 — DS_UNHANDLED_INPUT marker constant (ADR-0157 + ADR-0158).

Per PB-6: Phase 40 ships the constant + family_rules wiring only; no
builtin DataState is bootstrap-registered in product, so this verifies
the value, its marker realm, and that the strict validator accepts it
(registerable) — NOT that a node exists at bootstrap.
"""

from __future__ import annotations

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    DS_UNHANDLED_INPUT,
    CapacityLayer,
    DataState,
    ShapeDescriptor,
)
from mindsos_capacity.identifiers import (
    REALM_MARKER,
    parse_datastate_iri,
)


def test_constant_value():
    assert DS_UNHANDLED_INPUT == "datastate:marker.unhandled_input"


def test_marker_realm():
    name = parse_datastate_iri(DS_UNHANDLED_INPUT)
    realm, suffix = name.split(".", 1)
    assert realm == REALM_MARKER
    assert suffix == "unhandled_input"


def test_registerable_via_validator():
    layer = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    name = parse_datastate_iri(DS_UNHANDLED_INPUT)
    node = layer.register_datastate(
        DataState(name=name, shape=ShapeDescriptor.scalar("str"))
    )
    assert node is not None
