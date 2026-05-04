"""Tests for the 8-variant ``PropertyType`` vocabulary under strict mode.

Direct unit tests of ``Schema.validate_node_properties`` to lock the
type-coercion edge cases (FalkorDB int→float, bool-vs-int subtype trap,
empty list, list[bool], list[float] mixed-int).
"""

from __future__ import annotations

import pytest

from mindsos_core import (
    NodeType,
    PropertyShapeError,
    PropertyType,
    Schema,
)


def _strict_with_type(prop_name: str, ptype: PropertyType) -> Schema:
    s = Schema(strict=True)
    s.add_node_type(NodeType("T", property_types={prop_name: ptype}))
    return s


@pytest.mark.parametrize("good_value", ["hello", "", "with whitespace"])
def test_string_accepts_strings(good_value):
    s = _strict_with_type("k", PropertyType.STRING)
    s.validate_node_properties("T", {"k": good_value})


def test_string_rejects_int():
    s = _strict_with_type("k", PropertyType.STRING)
    with pytest.raises(PropertyShapeError):
        s.validate_node_properties("T", {"k": 42})


@pytest.mark.parametrize("good_value", [0, 1, -1, 999999])
def test_int_accepts_ints(good_value):
    s = _strict_with_type("k", PropertyType.INT)
    s.validate_node_properties("T", {"k": good_value})


def test_int_rejects_bool_even_though_python_bool_is_int_subtype():
    """The strict typer must not accept True/False where INT is declared."""
    s = _strict_with_type("k", PropertyType.INT)
    with pytest.raises(PropertyShapeError):
        s.validate_node_properties("T", {"k": True})


@pytest.mark.parametrize("good_value", [3.14, 0.0, -0.5])
def test_float_accepts_floats(good_value):
    s = _strict_with_type("k", PropertyType.FLOAT)
    s.validate_node_properties("T", {"k": good_value})


def test_float_accepts_int_via_falkordb_coercion():
    """FalkorDB stores ints in float columns — the typer follows that rule."""
    s = _strict_with_type("k", PropertyType.FLOAT)
    s.validate_node_properties("T", {"k": 5})  # int counts as float


def test_float_rejects_string():
    s = _strict_with_type("k", PropertyType.FLOAT)
    with pytest.raises(PropertyShapeError):
        s.validate_node_properties("T", {"k": "5"})


@pytest.mark.parametrize("good_value", [True, False])
def test_bool_accepts_booleans(good_value):
    s = _strict_with_type("k", PropertyType.BOOL)
    s.validate_node_properties("T", {"k": good_value})


def test_bool_rejects_int():
    s = _strict_with_type("k", PropertyType.BOOL)
    with pytest.raises(PropertyShapeError):
        s.validate_node_properties("T", {"k": 1})


def test_list_string_accepts_homogeneous_list():
    s = _strict_with_type("k", PropertyType.LIST_STRING)
    s.validate_node_properties("T", {"k": ["a", "b"]})


def test_list_string_rejects_mixed_list():
    s = _strict_with_type("k", PropertyType.LIST_STRING)
    with pytest.raises(PropertyShapeError):
        s.validate_node_properties("T", {"k": ["a", 1]})


def test_list_string_accepts_empty_list():
    s = _strict_with_type("k", PropertyType.LIST_STRING)
    s.validate_node_properties("T", {"k": []})


def test_list_int_accepts_ints():
    s = _strict_with_type("k", PropertyType.LIST_INT)
    s.validate_node_properties("T", {"k": [1, 2, 3]})


def test_list_int_rejects_bool_in_list():
    s = _strict_with_type("k", PropertyType.LIST_INT)
    with pytest.raises(PropertyShapeError):
        s.validate_node_properties("T", {"k": [1, True]})


def test_list_float_accepts_mixed_int_and_float():
    """Same FalkorDB coercion rule as scalar FLOAT."""
    s = _strict_with_type("k", PropertyType.LIST_FLOAT)
    s.validate_node_properties("T", {"k": [1, 2.5, 3]})


def test_list_float_rejects_bool_in_list():
    s = _strict_with_type("k", PropertyType.LIST_FLOAT)
    with pytest.raises(PropertyShapeError):
        s.validate_node_properties("T", {"k": [True]})


def test_list_bool_accepts_bools():
    s = _strict_with_type("k", PropertyType.LIST_BOOL)
    s.validate_node_properties("T", {"k": [True, False]})


def test_list_bool_rejects_int_in_list():
    s = _strict_with_type("k", PropertyType.LIST_BOOL)
    with pytest.raises(PropertyShapeError):
        s.validate_node_properties("T", {"k": [1, 0]})


def test_undeclared_key_under_strict_typed_type_rejected():
    s = Schema(strict=True)
    s.add_node_type(NodeType("T", property_types={"a": PropertyType.INT}))
    with pytest.raises(PropertyShapeError):
        s.validate_node_properties("T", {"a": 1, "rogue": "x"})


def test_undeclared_key_under_strict_when_declared_empty_is_allowed():
    """Type with empty property_types map opts out of strict typing for that type."""
    s = Schema(strict=True)
    s.add_node_type(NodeType("T", property_types={}))
    # No PropertyShapeError — empty declared map = "any keys allowed"
    s.validate_node_properties("T", {"anything": "goes"})


def test_non_strict_schema_skips_property_type_check():
    s = Schema(strict=False)
    s.add_node_type(NodeType("T", property_types={"k": PropertyType.INT}))
    # Type mismatch under non-strict is silently allowed.
    s.validate_node_properties("T", {"k": "not-an-int"})


def test_ref_property_skipped_by_property_type_check():
    s = _strict_with_type("k", PropertyType.INT)
    # ref:* keys are not validated against the property-type map.
    s.validate_node_properties("T", {"k": 1, "ref:anchor": "some-uuid-string"})


def test_validate_edge_rejects_disallowed_target():
    from mindsos_core import EdgeType, UnknownTypeError
    s = Schema(strict=False)
    s.add_node_type(NodeType("Person"))
    s.add_node_type(NodeType("Org"))
    s.add_edge_type(EdgeType("WORKS_AT", frozenset({"Person"}), frozenset({"Org"})))
    with pytest.raises(UnknownTypeError):
        s.validate_edge("WORKS_AT", "Person", "Person")  # target must be Org


def test_validate_edge_empty_allowed_set_means_any():
    from mindsos_core import EdgeType
    s = Schema(strict=False)
    s.add_node_type(NodeType("Anything"))
    s.add_edge_type(EdgeType("REL"))
    s.validate_edge("REL", "Anything", "Anything")  # no UnknownTypeError
