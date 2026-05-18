"""Memories role-graph schema (Phase 13 PB-1 — NET-NEW).

Per DESIGN_UPPER_LAYER_ROLES.md §2.1. Memories live in the per-user
Local Metagraph (ADR-0044); ``user_id`` is baked into ``memory_iri``
per Phase 12 PB-11 + ADR-0044 §amendment-1.

``USED_CAPACITY`` is a Memory→capacity-IRI edge (via ref-resolution at
runtime). ``PART_OF_PIPELINE`` is a Memory→Pipeline edge (Pipeline lives
in Global ``promoted-pipelines``; cross-metagraph ref handled via
``ref:global_promoted_pipelines`` property + Phase 09 XRef machinery).

``strict=False`` per PB-3 / ADR-0149. Advisory properties per PB-8.
"""

from __future__ import annotations

from mindsos_core import EdgeType, NodeType, Schema


# ── Node types ─────────────────────────────────────────────────────────

NODE_MEMORY = "Memory"

MEMORIES_NODE_TYPES: tuple[str, ...] = (NODE_MEMORY,)


# ── Edge types ─────────────────────────────────────────────────────────

EDGE_USED_CAPACITY = "USED_CAPACITY"
EDGE_PART_OF_PIPELINE = "PART_OF_PIPELINE"

MEMORIES_EDGE_TYPES: tuple[str, ...] = (
    EDGE_USED_CAPACITY,
    EDGE_PART_OF_PIPELINE,
)


# ── Advisory property constants (PB-8) ─────────────────────────────────

MEMORY_PROPS: frozenset[str] = frozenset({
    "task_id",
    "task_type",
    "user_id",
    "completed_at",
    "result",
    "retention_policy",
    # Optional — present only when the task failed.
    "ref:problem_trace",
})


def build_memories_schema(strict: bool = False) -> Schema:
    """Construct the memories role Schema (per-user Local; ADR-0044)."""
    s = Schema(strict=strict)

    for nt in MEMORIES_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    any_node = frozenset(MEMORIES_NODE_TYPES)
    for et in MEMORIES_EDGE_TYPES:
        s.add_edge_type(EdgeType(et, any_node, any_node))

    return s
