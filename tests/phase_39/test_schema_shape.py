"""Phase 39 ``episodic_memories`` schema-shape sentinel (Phase 43 updated).

Per Phase 39 design log §2 PB-R1-A + PB-R1-B: NodeType skeletons only
at Phase 39. EdgeTypes (Phase 13 vestigial USED_CAPACITY +
PART_OF_PIPELINE) dropped. Advisory property frozensets (``MEMORY_PROPS``)
dropped.

Phase 43 PR2 commit 1 fills the body: ``MEMORY_CONTAINS_EPISODE``
EdgeType ships (regular EdgeType not IntergraphEdgeType per impl-time
R6 reconciliation — both NodeTypes in same role-graph); ``EPISODE_PROPS``
+ ``MEMORY_PROPS`` ship as canonical union of CONTENT + METADATA
partitions per ADR-0153 §3.

Catches accidental re-introduction of Phase 13 vestigial constants at
Phase 43+ schema-v2 ship.
"""

from __future__ import annotations

from mindsos_knowledge.schemas import build_episodic_memories_schema
from mindsos_knowledge.schemas.episodic_memories import (
    EDGE_MEMORY_CONTAINS_EPISODE,
    EPISODIC_MEMORIES_NODE_TYPES,
    NODE_EPISODE,
    NODE_MEMORY,
)


def test_episodic_memories_node_types_episode_and_memory_only() -> None:
    """2 NodeTypes — Episode (per-task) + Memory (composite)."""
    assert EPISODIC_MEMORIES_NODE_TYPES == (NODE_EPISODE, NODE_MEMORY)
    assert NODE_EPISODE == "Episode"
    assert NODE_MEMORY == "Memory"


def test_episodic_memories_schema_has_two_node_types() -> None:
    s = build_episodic_memories_schema()
    assert set(s.node_types) == {NODE_EPISODE, NODE_MEMORY}


def test_episodic_memories_schema_has_memory_contains_episode_edge() -> None:
    """Phase 43 PR2 commit 1: MEMORY_CONTAINS_EPISODE EdgeType per
    ADR-0152 §7 + Chat B D-B47. Phase 13 vestigial USED_CAPACITY +
    PART_OF_PIPELINE remain retired.
    """
    s = build_episodic_memories_schema()
    assert set(s.edge_types) == {EDGE_MEMORY_CONTAINS_EPISODE}


def test_episodic_memories_schema_has_zero_hyperedges() -> None:
    s = build_episodic_memories_schema()
    assert s.hyperedge_types == {}


def test_episodic_memories_module_does_not_export_legacy_edge_constants() -> None:
    """Phase 13 ``EDGE_USED_CAPACITY`` + ``EDGE_PART_OF_PIPELINE`` retired."""
    import mindsos_knowledge.schemas.episodic_memories as em

    assert not hasattr(em, "EDGE_USED_CAPACITY")
    assert not hasattr(em, "EDGE_PART_OF_PIPELINE")
    assert not hasattr(em, "MEMORIES_EDGE_TYPES")


def test_episodic_memories_module_exports_phase_43_partition_constants() -> None:
    """Phase 43 PR2 commit 1: EPISODE_PROPS + MEMORY_PROPS + partition
    frozensets ship per ADR-0153 §3.
    """
    import mindsos_knowledge.schemas.episodic_memories as em

    assert hasattr(em, "EPISODE_PROPS")
    assert hasattr(em, "MEMORY_PROPS")
    assert hasattr(em, "EPISODE_CONTENT_FIELDS")
    assert hasattr(em, "EPISODE_METADATA_FIELDS")
    assert hasattr(em, "MEMORY_CONTENT_FIELDS")
    assert hasattr(em, "MEMORY_METADATA_FIELDS")


def test_episodic_memories_strict_false_default() -> None:
    """Per ADR-0149 — schemas at strict=False by default."""
    s = build_episodic_memories_schema()
    assert s.strict is False


def test_episodic_memories_strict_true_threading() -> None:
    """``strict=True`` kwarg plumbs through."""
    s = build_episodic_memories_schema(strict=True)
    assert s.strict is True
