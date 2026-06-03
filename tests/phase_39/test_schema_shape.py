"""Phase 39 ``episodic_memories`` schema-shape sentinel.

Per design log §2 PB-R1-A + PB-R1-B: NodeType skeletons only at
Phase 39. EdgeTypes (Phase 13 vestigial USED_CAPACITY + PART_OF_PIPELINE)
dropped. Advisory property frozensets (MEMORY_PROPS) dropped.

Catches accidental re-introduction at Phase 43 schema-v2 ship.
"""

from __future__ import annotations

from mindsos_knowledge.schemas import build_episodic_memories_schema
from mindsos_knowledge.schemas.episodic_memories import (
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


def test_episodic_memories_schema_has_zero_edges() -> None:
    """PB-R1-A: vestigial USED_CAPACITY + PART_OF_PIPELINE dropped."""
    s = build_episodic_memories_schema()
    assert s.edge_types == {}


def test_episodic_memories_schema_has_zero_hyperedges() -> None:
    s = build_episodic_memories_schema()
    assert s.hyperedge_types == {}


def test_episodic_memories_module_does_not_export_legacy_edge_constants() -> None:
    """Phase 13 ``EDGE_USED_CAPACITY`` + ``EDGE_PART_OF_PIPELINE`` retired."""
    import mindsos_knowledge.schemas.episodic_memories as em

    assert not hasattr(em, "EDGE_USED_CAPACITY")
    assert not hasattr(em, "EDGE_PART_OF_PIPELINE")
    assert not hasattr(em, "MEMORIES_EDGE_TYPES")


def test_episodic_memories_module_does_not_export_legacy_property_frozenset() -> None:
    """PB-R1-B: ``MEMORY_PROPS`` dropped at Phase 39; lands Phase 43."""
    import mindsos_knowledge.schemas.episodic_memories as em

    assert not hasattr(em, "MEMORY_PROPS")


def test_episodic_memories_strict_false_default() -> None:
    """Per ADR-0149 — schemas at strict=False by default."""
    s = build_episodic_memories_schema()
    assert s.strict is False


def test_episodic_memories_strict_true_threading() -> None:
    """``strict=True`` kwarg plumbs through."""
    s = build_episodic_memories_schema(strict=True)
    assert s.strict is True
