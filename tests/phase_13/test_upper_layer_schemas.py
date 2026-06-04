"""Phase 13 — 5 upper-layer schemas (NET-NEW per PB-1).

Verifies node + edge type sets per DESIGN_UPPER_LAYER_ROLES.md §2.1.
"""

from __future__ import annotations

import pytest

from mindsos_core import Schema

from mindsos_knowledge.schemas import (
    build_capacity_state_schema,
    build_episodic_memories_schema,
    build_problem_trace_schema,
    build_promoted_pipelines_schema,
    build_task_patterns_schema,
)
from mindsos_knowledge.schemas.capacity_state import (
    CAPACITY_STATE_EDGE_TYPES,
    CAPACITY_STATE_NODE_TYPES,
    NODE_CAPACITY_SNAPSHOT,
)
from mindsos_knowledge.schemas.episodic_memories import (
    EPISODIC_MEMORIES_NODE_TYPES,
    NODE_EPISODE,
    NODE_MEMORY,
)
from mindsos_knowledge.schemas.problem_trace import (
    NODE_PROBLEM_TRACE_ENTRY,
    PROBLEM_TRACE_EDGE_TYPES,
    PROBLEM_TRACE_NODE_TYPES,
)
from mindsos_knowledge.schemas.promoted_pipelines import (
    EDGE_DERIVED_FROM,
    EDGE_HAS_STEP,
    HAS_STEP_POSITION_PROPERTY,
    NODE_PIPELINE,
    NODE_PIPELINE_STEP,
    PROMOTED_PIPELINES_EDGE_TYPES,
    PROMOTED_PIPELINES_NODE_TYPES,
)
from mindsos_knowledge.schemas.task_patterns import (
    EDGE_DECOMPOSES_INTO,
    EDGE_PREREQUISITE_OF,
    NODE_SUBGOAL_TEMPLATE,
    NODE_TASK_PATTERN,
    TASK_PATTERNS_EDGE_TYPES,
    TASK_PATTERNS_NODE_TYPES,
)


# ── promoted_pipelines ─────────────────────────────────────────────────


def test_promoted_pipelines_nodes_match() -> None:
    s = build_promoted_pipelines_schema()
    assert set(s.node_types) == set(PROMOTED_PIPELINES_NODE_TYPES)
    assert NODE_PIPELINE in s.node_types
    assert NODE_PIPELINE_STEP in s.node_types


def test_promoted_pipelines_edges_match() -> None:
    s = build_promoted_pipelines_schema()
    assert set(s.edge_types) == set(PROMOTED_PIPELINES_EDGE_TYPES)
    assert EDGE_HAS_STEP in s.edge_types
    assert EDGE_DERIVED_FROM in s.edge_types


def test_promoted_pipelines_has_step_is_regular_edge_not_hyperedge() -> None:
    # PB-9 — HAS_STEP is a regular EdgeType with `position` property,
    # NOT an ordered HyperEdgeType.
    s = build_promoted_pipelines_schema()
    assert EDGE_HAS_STEP in s.edge_types
    assert EDGE_HAS_STEP not in s.hyperedge_types
    assert HAS_STEP_POSITION_PROPERTY == "position"


# ── task_patterns ──────────────────────────────────────────────────────


def test_task_patterns_nodes_match() -> None:
    s = build_task_patterns_schema()
    assert set(s.node_types) == set(TASK_PATTERNS_NODE_TYPES)
    assert NODE_TASK_PATTERN in s.node_types
    assert NODE_SUBGOAL_TEMPLATE in s.node_types


def test_task_patterns_edges_match() -> None:
    s = build_task_patterns_schema()
    assert set(s.edge_types) == set(TASK_PATTERNS_EDGE_TYPES)
    assert EDGE_DECOMPOSES_INTO in s.edge_types
    assert EDGE_PREREQUISITE_OF in s.edge_types


# ── episodic_memories (Phase 39 rename per ADR-0044 §am-3) ─────────────


def test_episodic_memories_nodes_match() -> None:
    s = build_episodic_memories_schema()
    assert set(s.node_types) == set(EPISODIC_MEMORIES_NODE_TYPES)
    assert NODE_EPISODE in s.node_types
    assert NODE_MEMORY in s.node_types


def test_episodic_memories_has_memory_contains_episode_edge_at_phase_43() -> None:
    """Phase 39 design log PB-R1-A: Phase 13 vestigial USED_CAPACITY +
    PART_OF_PIPELINE EdgeTypes dropped. Phase 43 PR2 commit 1 ships
    MEMORY_CONTAINS_EPISODE EdgeType per ADR-0152 §7 + Chat B D-B47
    (impl-time R6 reconciliation: regular EdgeType not IntergraphEdgeType
    — both NodeTypes in same role-graph).
    """
    s = build_episodic_memories_schema()
    assert set(s.edge_types) == {"MEMORY_CONTAINS_EPISODE"}


# ── problem_trace ──────────────────────────────────────────────────────


def test_problem_trace_nodes_match() -> None:
    s = build_problem_trace_schema()
    assert set(s.node_types) == set(PROBLEM_TRACE_NODE_TYPES)
    assert NODE_PROBLEM_TRACE_ENTRY in s.node_types


def test_problem_trace_has_no_edges_in_v1() -> None:
    s = build_problem_trace_schema()
    assert s.edge_types == {}
    assert PROBLEM_TRACE_EDGE_TYPES == ()


# ── capacity_state ─────────────────────────────────────────────────────


def test_capacity_state_nodes_match() -> None:
    s = build_capacity_state_schema()
    assert set(s.node_types) == set(CAPACITY_STATE_NODE_TYPES)
    assert NODE_CAPACITY_SNAPSHOT in s.node_types


def test_capacity_state_has_no_edges_in_v1() -> None:
    s = build_capacity_state_schema()
    assert s.edge_types == {}
    assert CAPACITY_STATE_EDGE_TYPES == ()


# ── strict=True smoke (parametric) ─────────────────────────────────────


@pytest.mark.parametrize(
    "builder",
    [
        build_promoted_pipelines_schema,
        build_task_patterns_schema,
        build_episodic_memories_schema,
        build_problem_trace_schema,
        build_capacity_state_schema,
    ],
)
def test_upper_layer_schema_strict_true_round_trip(builder) -> None:
    s = builder(strict=True)
    assert isinstance(s, Schema)
    assert s.strict is True


@pytest.mark.parametrize(
    "builder",
    [
        build_promoted_pipelines_schema,
        build_task_patterns_schema,
        build_episodic_memories_schema,
        build_problem_trace_schema,
        build_capacity_state_schema,
    ],
)
def test_upper_layer_schema_no_hyperedges(builder) -> None:
    # PB-9 + design — upper-layer schemas use regular edges only.
    s = builder()
    assert s.hyperedge_types == {}
