"""Phase 13 PB-4 — ontology HyperEdgeType lift from v3 label-constants.

Phase 04-v2 shipped ``HyperEdgeType`` to L1; Phase 13 closes the v3
drift by registering the 7 ontology hyperedge labels as
``HyperEdgeType`` instances on the ontology schema.
"""

from __future__ import annotations

import pytest

from mindsos_knowledge.schemas import build_ontology_schema
from mindsos_knowledge.schemas.ontology import (
    HE_ALL_DIFFERENT,
    HE_ALL_DISJOINT_CLASSES,
    HE_DISJOINT_UNION_OF,
    HE_INTERSECTION_OF,
    HE_ONE_OF,
    HE_PROPERTY_CHAIN,
    HE_UNION_OF,
    ONTOLOGY_HYPEREDGE_TYPES,
    ONTOLOGY_NODE_TYPES,
)


_EXPECTED_HE = (
    HE_INTERSECTION_OF,
    HE_UNION_OF,
    HE_ONE_OF,
    HE_PROPERTY_CHAIN,
    HE_DISJOINT_UNION_OF,
    HE_ALL_DISJOINT_CLASSES,
    HE_ALL_DIFFERENT,
)


def test_ontology_hyperedge_type_count_is_seven() -> None:
    s = build_ontology_schema()
    assert len(s.hyperedge_types) == 7


@pytest.mark.parametrize("het_name", _EXPECTED_HE)
def test_each_v3_label_lifted_to_hyperedge_type(het_name: str) -> None:
    s = build_ontology_schema()
    assert het_name in s.hyperedge_types


def test_ontology_hyperedge_type_set_matches_module_constant() -> None:
    s = build_ontology_schema()
    assert set(s.hyperedge_types) == set(ONTOLOGY_HYPEREDGE_TYPES)


def test_ontology_hyperedge_allowed_members_are_all_ontology_nodes() -> None:
    # PB-4 design — allowed_member_types is the full ontology NodeType
    # set; ordering semantics live at HyperEdge instance level.
    s = build_ontology_schema()
    expected = frozenset(ONTOLOGY_NODE_TYPES)
    for het_name in ONTOLOGY_HYPEREDGE_TYPES:
        het = s.require_hyperedge_type(het_name)
        assert het.allowed_member_types == expected


def test_validate_hyperedge_accepts_valid_members() -> None:
    s = build_ontology_schema()
    # PROPERTY_CHAIN with two ObjectProperty members — legal.
    s.validate_hyperedge(HE_PROPERTY_CHAIN, ["ObjectProperty", "ObjectProperty"])


def test_validate_hyperedge_rejects_unregistered_member_type() -> None:
    from mindsos_core import UnknownTypeError

    s = build_ontology_schema()
    with pytest.raises(UnknownTypeError):
        s.validate_hyperedge(HE_PROPERTY_CHAIN, ["NotAType"])
