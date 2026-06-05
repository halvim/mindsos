"""Capacity / Monitor / Adapter dataclass def-time tests (Phase 27).

PHASE_MAP §27 features: "Capacity / Monitor / Adapter define; IRI form
``capacity:<category>:<name>`` enforced."

Parent has no isolated dataclass-only test file — ``tests_l3/unit/
test_registration.py`` mixes the dataclass surface with the
``CapacityLayer`` registry which doesn't ship until Phase 28. This
file (NEW at Phase 27 per R2 PB-10 pick) exercises the def-time IRI +
property bag + ``validate_for_registration`` slice that's actually
shipped at Phase 27.

R2 PB-23 14-test inventory:
1. capacity_iri built from category + name
2. monitor_iri matches capacity_iri form
3. adapter_iri matches capacity_iri form
4. capacity to_properties shape
5. monitor to_properties includes subscribes_to + emits
6. adapter to_properties includes is_adapter=True
7. validate_for_registration accepts known IRIs
8. validate_for_registration rejects unknown input IRI
9. validate_for_registration rejects unknown output IRI
10. capacity node_type defaults to "Capacity"
11. monitor node_type is "Monitor"
12. adapter node_type is "Adapter" and kind is "adapter"
13. REF_TYPES subset of KL.REF_TYPES (ADR-0067 §amendment-1 parity)
14. RESERVED_PROPERTY_KEYS fingerprint stable
"""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    Adapter,
    Capacity,
    CapacityRegistrationError,
    KIND_ADAPTER,
    KIND_MONITOR,
    KIND_REACTIVE,
    Monitor,
    NODE_TYPE_ADAPTER,
    NODE_TYPE_CAPACITY,
    NODE_TYPE_MONITOR,
    REF_TYPES,
    RESERVED_PROPERTY_KEYS,
    capacity_iri,
)


# ── Fixtures ──────────────────────────────────────────────────────────

_DS_RAW = "datastate:text.raw"
_DS_TOKENS = "datastate:text.tokens"
_KNOWN_IRIS = (_DS_RAW, _DS_TOKENS)


def _make_capacity() -> Capacity:
    return Capacity(
        name="text.space_split",
        category="perception",
        inputs=(_DS_RAW,),
        outputs=(_DS_TOKENS,),
        description="Whitespace split.",
        cost_prior=1.5,
        latency_ms_prior=2.0,
    )


def _make_monitor() -> Monitor:
    return Monitor(
        name="text.token_change_monitor",
        category="signalling",
        inputs=(_DS_TOKENS,),
        outputs=(_DS_TOKENS,),
        subscribes_to=(_DS_TOKENS,),
        emits=(_DS_TOKENS,),
    )


def _make_adapter() -> Adapter:
    return Adapter(
        name="adapter.tokens_to_first",
        category="perception",
        inputs=(_DS_TOKENS,),
        outputs=(_DS_RAW,),
    )


# ── IRI form tests ────────────────────────────────────────────────────


def test_capacity_iri_built_from_category_and_name():
    c = _make_capacity()
    assert c.iri == capacity_iri("perception", "text.space_split")
    assert c.iri == "capacity:perception:text.space_split"


def test_monitor_iri_matches_capacity_iri_form():
    m = _make_monitor()
    assert m.iri == "capacity:signalling:text.token_change_monitor"


def test_adapter_iri_matches_capacity_iri_form():
    a = _make_adapter()
    assert a.iri == "capacity:perception:adapter.tokens_to_first"


# ── to_properties shape tests ─────────────────────────────────────────


def test_capacity_to_properties_shape():
    c = _make_capacity()
    props = c.to_properties()
    assert props["name"] == "text.space_split"
    assert props["category"] == "perception"
    assert props["node_kind"] == KIND_REACTIVE
    assert props["is_adapter"] is False
    assert props["inputs"] == [_DS_RAW]
    assert props["outputs"] == [_DS_TOKENS]
    assert props["cost_prior"] == 1.5
    assert props["latency_ms_prior"] == 2.0
    assert props["description"] == "Whitespace split."


def test_monitor_to_properties_includes_subscribes_to_emits():
    m = _make_monitor()
    props = m.to_properties()
    assert props["subscribes_to"] == [_DS_TOKENS]
    assert props["emits"] == [_DS_TOKENS]
    assert props["node_kind"] == KIND_MONITOR


def test_adapter_to_properties_includes_is_adapter_true():
    a = _make_adapter()
    props = a.to_properties()
    assert props["is_adapter"] is True
    assert props["node_kind"] == KIND_ADAPTER


# ── validate_for_registration tests ───────────────────────────────────


def test_validate_for_registration_accepts_known_iris():
    c = _make_capacity()
    # Should not raise.
    c.validate_for_registration(_KNOWN_IRIS)


def test_validate_for_registration_rejects_unknown_input_iri():
    c = Capacity(
        name="bad.input",
        category="perception",
        inputs=("datastate:nonexistent",),
        outputs=(_DS_TOKENS,),
    )
    with pytest.raises(CapacityRegistrationError, match="unknown DataState"):
        c.validate_for_registration(_KNOWN_IRIS)


def test_validate_for_registration_rejects_unknown_output_iri():
    c = Capacity(
        name="bad.output",
        category="perception",
        inputs=(_DS_RAW,),
        outputs=("datastate:nonexistent",),
    )
    with pytest.raises(CapacityRegistrationError, match="unknown DataState"):
        c.validate_for_registration(_KNOWN_IRIS)


# ── Node-type defaults ────────────────────────────────────────────────


def test_capacity_node_type_defaults_to_capacity():
    c = _make_capacity()
    assert c.node_type == NODE_TYPE_CAPACITY
    assert c.node_kind == KIND_REACTIVE
    assert c.is_adapter is False


def test_monitor_node_type_is_monitor():
    m = _make_monitor()
    assert m.node_type == NODE_TYPE_MONITOR
    assert m.node_kind == KIND_MONITOR


def test_adapter_node_type_is_adapter_and_kind_is_adapter():
    a = _make_adapter()
    assert a.node_type == NODE_TYPE_ADAPTER
    assert a.node_kind == KIND_ADAPTER
    assert a.is_adapter is True


# ── REF_TYPES parity (ADR-0067 §amendment-1) ──────────────────────────


def test_ref_types_subset_of_kl_ref_types():
    """ADR-0067 §amendment-1: L3.REF_TYPES is a 6-member subset of L2's
    7-member set; PROMOTED is L2-exclusive.

    Test-level import of mindsos_knowledge is permitted (test-only
    cross-layer reach; not a runtime dependency).
    """
    from mindsos_knowledge.identifiers import REF_TYPES as KL_REF_TYPES

    assert REF_TYPES <= KL_REF_TYPES, (
        f"L3.REF_TYPES must be a subset of L2.REF_TYPES; "
        f"L3 has extras: {REF_TYPES - KL_REF_TYPES!r}"
    )
    assert KL_REF_TYPES - REF_TYPES == {"PROMOTED"}, (
        f"L2 - L3 expected to be exactly {{'PROMOTED'}}; "
        f"got {KL_REF_TYPES - REF_TYPES!r}"
    )
    assert len(REF_TYPES) == 6
    assert len(KL_REF_TYPES) == 7


def test_reserved_property_keys_fingerprint_stable():
    """RESERVED_PROPERTY_KEYS fingerprint — fails loudly if a key is
    added/removed without intent. Update this fingerprint together
    with any RESERVED_PROPERTY_KEYS change.
    """
    expected = {
        "ref:global_capacity",
        "ref:global_datastate",
        "ref_type",
        "inputs",
        "outputs",
        "node_kind",
        "category",
        "shape_kind",
        "is_adapter",
    }
    assert RESERVED_PROPERTY_KEYS == frozenset(expected)
