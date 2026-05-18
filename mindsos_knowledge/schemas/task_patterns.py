"""Task-patterns role-graph schema (Phase 13 PB-1 — NET-NEW).

Per DESIGN_UPPER_LAYER_ROLES.md §2.1.

``strict=False`` per PB-3 / ADR-0149. Advisory properties per PB-8.
"""

from __future__ import annotations

from mindsos_core import EdgeType, NodeType, Schema


# ── Node types ─────────────────────────────────────────────────────────

NODE_TASK_PATTERN = "TaskPattern"
NODE_SUBGOAL_TEMPLATE = "SubgoalTemplate"

TASK_PATTERNS_NODE_TYPES: tuple[str, ...] = (
    NODE_TASK_PATTERN,
    NODE_SUBGOAL_TEMPLATE,
)


# ── Edge types ─────────────────────────────────────────────────────────

EDGE_DECOMPOSES_INTO = "DECOMPOSES_INTO"
EDGE_PREREQUISITE_OF = "PREREQUISITE_OF"

TASK_PATTERNS_EDGE_TYPES: tuple[str, ...] = (
    EDGE_DECOMPOSES_INTO,
    EDGE_PREREQUISITE_OF,
)


# ── Advisory property constants (PB-8) ─────────────────────────────────

TASK_PATTERN_PROPS: frozenset[str] = frozenset({
    "task_type",
    "n_observations",
    "confidence",
})

SUBGOAL_TEMPLATE_PROPS: frozenset[str] = frozenset({
    "subgoal_kind",
    "ordering_hint",
})


def build_task_patterns_schema(strict: bool = False) -> Schema:
    """Construct the task-patterns role Schema."""
    s = Schema(strict=strict)

    for nt in TASK_PATTERNS_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    any_node = frozenset(TASK_PATTERNS_NODE_TYPES)
    for et in TASK_PATTERNS_EDGE_TYPES:
        s.add_edge_type(EdgeType(et, any_node, any_node))

    return s
