"""Phase 43 PR2 — episodic_memories body finalization.

Per ADR-0152 §7 + ADR-0153 §1 + Chat B D-B47. Episode + Memory
NodeTypes with content/metadata partition + MEMORY_CONTAINS_EPISODE
EdgeType per impl-time R6 discovery (regular EdgeType not
IntergraphEdgeType; both NodeTypes live in the same role-graph).
"""

from __future__ import annotations

from mindsos_knowledge.schemas import build_episodic_memories_schema
from mindsos_knowledge.schemas._base import Discipline
from mindsos_knowledge.schemas.episodic_memories import (
    EDGE_MEMORY_CONTAINS_EPISODE,
    EPISODE_CONTENT_FIELDS,
    EPISODE_METADATA_FIELDS,
    EPISODE_PROPS,
    MEMORY_CONTENT_FIELDS,
    MEMORY_METADATA_FIELDS,
    MEMORY_PROPS,
    NODE_EPISODE,
    NODE_MEMORY,
)
from mindsos_knowledge.validators import validate_partition_invariant


def test_schema_registers_episode_and_memory_node_types() -> None:
    s = build_episodic_memories_schema()
    assert NODE_EPISODE in s.node_types
    assert NODE_MEMORY in s.node_types


def test_schema_registers_memory_contains_episode_edge_type() -> None:
    s = build_episodic_memories_schema()
    assert EDGE_MEMORY_CONTAINS_EPISODE in s.edge_types
    et = s.edge_types[EDGE_MEMORY_CONTAINS_EPISODE]
    assert NODE_MEMORY in et.allowed_sources
    assert NODE_EPISODE in et.allowed_targets


def test_schema_discipline_is_append_only_with_lazy_inline() -> None:
    s = build_episodic_memories_schema()
    assert s.mutation_discipline == Discipline.APPEND_ONLY_WITH_LAZY_INLINE


def test_episode_content_partition_cardinality() -> None:
    assert len(EPISODE_CONTENT_FIELDS) == 6
    assert EPISODE_METADATA_FIELDS == frozenset()
    expected_content = {
        "request_input_ref",
        "mm_root_ref",
        "request_pattern_iri",
        "outcome_classification",
        "crash_marker",
        "consolidated_at",
    }
    assert EPISODE_CONTENT_FIELDS == expected_content


def test_memory_content_partition_cardinality() -> None:
    assert MEMORY_CONTENT_FIELDS == frozenset({"request_pattern_iri"})
    assert MEMORY_METADATA_FIELDS == frozenset(
        {"created_at", "admin_notes", "rejected_promotions"}
    )


def test_episode_partition_is_clean() -> None:
    r = validate_partition_invariant(
        content_fields=EPISODE_CONTENT_FIELDS,
        metadata_fields=EPISODE_METADATA_FIELDS,
        all_fields=EPISODE_PROPS,
    )
    assert r.ok


def test_memory_partition_is_clean() -> None:
    r = validate_partition_invariant(
        content_fields=MEMORY_CONTENT_FIELDS,
        metadata_fields=MEMORY_METADATA_FIELDS,
        all_fields=MEMORY_PROPS,
    )
    assert r.ok
