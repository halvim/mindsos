"""Phase 28 — L3 schema builders."""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    EDGE_CONSTRAINT,
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    NODE_TYPE_ADAPTER,
    NODE_TYPE_CAPACITY,
    NODE_TYPE_DATASTATE,
    NODE_TYPE_MONITOR,
    ROLE_DATASTATES,
    build_category_schema,
    build_datastates_schema,
    category_role,
    schema_for_role,
)


def test_build_datastates_schema_has_one_node_type():
    s = build_datastates_schema()
    assert NODE_TYPE_DATASTATE in s.node_types
    assert len(s.edge_types) == 0


def test_build_category_schema_has_three_node_types_and_three_edge_types():
    # ADR-0156 (Phase 42): EDGE_TYPE_COMPAT retired; category schema now
    # registers CONSTRAINT + PRODUCES + CONSUMES rel-type vocabulary.
    s = build_category_schema()
    assert {NODE_TYPE_CAPACITY, NODE_TYPE_MONITOR, NODE_TYPE_ADAPTER}.issubset(s.node_types)
    assert {EDGE_CONSTRAINT, EDGE_PRODUCES, EDGE_CONSUMES}.issubset(
        s.edge_types
    )


def test_schema_for_role_dispatches_datastates():
    s = schema_for_role(ROLE_DATASTATES)
    assert NODE_TYPE_DATASTATE in s.node_types
    assert NODE_TYPE_CAPACITY not in s.node_types


def test_schema_for_role_dispatches_category():
    s = schema_for_role(category_role("perception"))
    assert NODE_TYPE_CAPACITY in s.node_types
    assert NODE_TYPE_DATASTATE not in s.node_types


def test_schema_for_role_rejects_unknown_role():
    with pytest.raises(ValueError, match="Unknown L3 role"):
        schema_for_role("nonsense:role")


def test_schemas_respect_strict_flag():
    s_loose = build_category_schema(strict=False)
    s_strict = build_category_schema(strict=True)
    assert s_loose.strict is False
    assert s_strict.strict is True
