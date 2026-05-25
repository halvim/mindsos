"""Tests for DataState shape descriptors and compatibility helpers.

Phase 27 port from parent ``tests_l3/unit/test_datastate.py``. Verbatim
content; only the file location changes (slim halvim tests tree).
"""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    DataState,
    DataStateError,
    ShapeDescriptor,
    list_of_compat,
    strict_compatible,
    validate_datastate,
)


def test_shape_descriptor_signature_stable():
    a = ShapeDescriptor.scalar("str", opaque_tag="x")
    b = ShapeDescriptor.scalar("str", opaque_tag="x")
    assert a.signature() == b.signature()
    assert strict_compatible(a, b)


def test_shape_descriptor_signature_differs_on_tag():
    a = ShapeDescriptor.scalar("str", opaque_tag="x")
    b = ShapeDescriptor.scalar("str", opaque_tag="y")
    assert not strict_compatible(a, b)


def test_list_of_compat():
    lst = ShapeDescriptor.list_of("str", opaque_tag="text.tokens")
    scalar = ShapeDescriptor.scalar("str", opaque_tag="text.tokens")
    assert list_of_compat(lst, scalar)
    assert not list_of_compat(scalar, lst)


def test_record_shape_sorts_fields_for_determinism():
    s = ShapeDescriptor.record({"b": "str", "a": "int"})
    assert s.fields == (("a", "int"), ("b", "str"))


def test_datastate_properties_include_structural_info():
    ds = DataState(
        name="text.tokens",
        shape=ShapeDescriptor.list_of("str", opaque_tag="text.tokens"),
        description="Whitespace tokens.",
        provenance_category="perception",
        l2_roles=("lexicon",),
    )
    props = ds.to_properties()
    assert props["shape_kind"] == "list"
    assert props["shape_elem"] == "str"
    assert props["shape_opaque_tag"] == "text.tokens"
    assert props["l2_roles"] == ["lexicon"]
    assert props["provenance_category"] == "perception"


def test_validate_datastate_rejects_bad_shape():
    with pytest.raises(DataStateError):
        validate_datastate(  # type: ignore[arg-type]
            DataState(name="bad", shape="not-a-shape")  # type: ignore[arg-type]
        )


def test_validate_datastate_rejects_empty_name():
    with pytest.raises(DataStateError):
        validate_datastate(DataState(name="", shape=ShapeDescriptor.scalar("str")))


def test_datastate_iri_roundtrip():
    ds = DataState(name="text.raw", shape=ShapeDescriptor.scalar("str"))
    assert ds.iri == "datastate:text.raw"
