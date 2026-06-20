"""Phase 13 — seed-role schemas (ontology / lexicon / concepts /
alignment) happy paths. Per PB-1 — v3 verbatim ports + ontology
HyperEdgeType lift per PB-4.
"""

from __future__ import annotations

import pytest

from mindsos_core import Schema

from mindsos_knowledge.schemas import (
    build_alignment_schema,
    build_concepts_schema,
    build_lexicon_schema,
    build_ontology_schema,
)
from mindsos_knowledge.schemas.alignment import (
    ALIGNMENT_EDGE_TYPES,
    ALIGNMENT_NODE_TYPES,
    NODE_ALIGNMENT_ANCHOR,
)
from mindsos_knowledge.schemas.concepts import (
    CONCEPTS_EDGE_TYPES,
    CONCEPTS_NODE_TYPES,
)
from mindsos_knowledge.schemas.lexicon import (
    LEXICON_EDGE_TYPES,
    LEXICON_EMPIRICAL_EDGE_TYPES,
    LEXICON_NODE_TYPES,
)
from mindsos_knowledge.schemas.ontology import (
    ONTOLOGY_EDGE_TYPES,
    ONTOLOGY_HYPEREDGE_TYPES,
    ONTOLOGY_NODE_TYPES,
)


def test_ontology_schema_returns_a_schema() -> None:
    s = build_ontology_schema()
    assert isinstance(s, Schema)


def test_ontology_schema_strict_false_by_default() -> None:
    assert build_ontology_schema().strict is False


def test_ontology_nodes_and_edges_match_module_constants() -> None:
    s = build_ontology_schema()
    assert set(s.node_types) == set(ONTOLOGY_NODE_TYPES)
    assert set(s.edge_types) == set(ONTOLOGY_EDGE_TYPES)
    # PB-4 — HyperEdgeType lift from v3 label constants.
    assert set(s.hyperedge_types) == set(ONTOLOGY_HYPEREDGE_TYPES)


def test_ontology_hyperedge_count_is_seven() -> None:
    # Phase 13 PB-4 explicit count sanity-check.
    s = build_ontology_schema()
    assert len(s.hyperedge_types) == 7


def test_lexicon_schema_returns_a_schema() -> None:
    s = build_lexicon_schema()
    assert isinstance(s, Schema)


def test_lexicon_nodes_and_edges_match_module_constants() -> None:
    # Phase 51 (ADR-0184): edge vocabulary = structural ∪ empirical strata.
    s = build_lexicon_schema()
    assert set(s.node_types) == set(LEXICON_NODE_TYPES)
    assert set(s.edge_types) == (
        set(LEXICON_EDGE_TYPES) | set(LEXICON_EMPIRICAL_EDGE_TYPES)
    )
    assert s.hyperedge_types == {}


def test_concepts_schema_returns_a_schema() -> None:
    s = build_concepts_schema()
    assert isinstance(s, Schema)


def test_concepts_nodes_and_edges_match_module_constants() -> None:
    s = build_concepts_schema()
    assert set(s.node_types) == set(CONCEPTS_NODE_TYPES)
    assert set(s.edge_types) == set(CONCEPTS_EDGE_TYPES)
    assert s.hyperedge_types == {}


def test_alignment_schema_returns_a_schema() -> None:
    s = build_alignment_schema()
    assert isinstance(s, Schema)


def test_alignment_single_anchor_node_type() -> None:
    s = build_alignment_schema()
    assert set(s.node_types) == set(ALIGNMENT_NODE_TYPES)
    assert NODE_ALIGNMENT_ANCHOR in s.node_types


def test_alignment_starter_edge_vocabulary() -> None:
    s = build_alignment_schema()
    assert set(s.edge_types) == set(ALIGNMENT_EDGE_TYPES)


@pytest.mark.parametrize(
    "builder",
    [
        build_ontology_schema,
        build_lexicon_schema,
        build_concepts_schema,
        build_alignment_schema,
    ],
)
def test_seed_schema_strict_true_round_trip(builder) -> None:
    # PB-3 sentinel — strict=False is the default but strict=True must
    # still build cleanly (the flag is plumbed through).
    s = builder(strict=True)
    assert s.strict is True
