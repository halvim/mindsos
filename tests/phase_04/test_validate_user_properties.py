"""Direct unit tests for ``mindsos_core.schema.validation.validate_user_properties``."""

from __future__ import annotations

import pytest

from mindsos_core import (
    PropertyShapeError,
    REF_PROPERTY_PREFIX,
    RESERVED_PROPERTY_KEYS,
    validate_user_properties,
)


def test_validate_user_properties_returns_defensive_copy():
    src = {"a": 1}
    out = validate_user_properties(src)
    assert out == src
    assert out is not src


def test_validate_user_properties_accepts_primitives():
    out = validate_user_properties(
        {"s": "x", "i": 1, "f": 1.5, "b": True, "n": None, "lst": ["a", "b"]}
    )
    assert out == {"s": "x", "i": 1, "f": 1.5, "b": True, "n": None, "lst": ["a", "b"]}


@pytest.mark.parametrize("reserved", sorted(RESERVED_PROPERTY_KEYS))
def test_validate_user_properties_rejects_reserved_keys(reserved):
    with pytest.raises(PropertyShapeError):
        validate_user_properties({reserved: "x"})


def test_validate_user_properties_rejects_ov_prefix():
    with pytest.raises(PropertyShapeError):
        validate_user_properties({"ov__age": 30})


def test_validate_user_properties_rejects_dict_value():
    with pytest.raises(PropertyShapeError):
        validate_user_properties({"meta": {"nested": 1}})


def test_validate_user_properties_rejects_tuple_value():
    with pytest.raises(PropertyShapeError):
        validate_user_properties({"k": (1, 2)})


def test_validate_user_properties_rejects_set_value():
    with pytest.raises(PropertyShapeError):
        validate_user_properties({"k": {1, 2, 3}})


def test_validate_user_properties_rejects_mixed_list():
    with pytest.raises(PropertyShapeError):
        validate_user_properties({"k": [1, "a"]})


def test_validate_user_properties_rejects_empty_key():
    with pytest.raises(PropertyShapeError):
        validate_user_properties({"": 1})


def test_validate_user_properties_accepts_ref_property():
    out = validate_user_properties({f"{REF_PROPERTY_PREFIX}anchor": "some-uuid"})
    assert out == {"ref:anchor": "some-uuid"}


def test_validate_user_properties_rejects_empty_ref_value():
    with pytest.raises(PropertyShapeError):
        validate_user_properties({f"{REF_PROPERTY_PREFIX}anchor": ""})


def test_validate_user_properties_rejects_non_string_ref_value():
    with pytest.raises(PropertyShapeError):
        validate_user_properties({f"{REF_PROPERTY_PREFIX}anchor": 42})


def test_validate_user_properties_accepts_empty_list():
    out = validate_user_properties({"k": []})
    assert out == {"k": []}
