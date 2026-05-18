"""Problem-trace role-graph schema (Phase 13 PB-1 — NET-NEW).

Per DESIGN_UPPER_LAYER_ROLES.md §2.1.

Single NodeType; no EdgeTypes in v1 (failures are independent records
linked back to the failing task via ``task_id`` property, not via
graph edges within problem-trace). Cross-references to ``capacity-iri``
+ ``task_id`` are property-level, not edge-level.

``strict=False`` per PB-3 / ADR-0149. Advisory properties per PB-8.
"""

from __future__ import annotations

from mindsos_core import NodeType, Schema


# ── Node type ──────────────────────────────────────────────────────────

NODE_PROBLEM_TRACE_ENTRY = "ProblemTraceEntry"

PROBLEM_TRACE_NODE_TYPES: tuple[str, ...] = (NODE_PROBLEM_TRACE_ENTRY,)


# ── Edge types ─────────────────────────────────────────────────────────

PROBLEM_TRACE_EDGE_TYPES: tuple[str, ...] = ()  # v1 has no edge types.


# ── Advisory property constants (PB-8) ─────────────────────────────────

PROBLEM_TRACE_ENTRY_PROPS: frozenset[str] = frozenset({
    "capacity_iri",
    "task_id",
    "step_id",
    "error_type",
    "error_message",
    "emitted_at",
    "context",
})


def build_problem_trace_schema(strict: bool = False) -> Schema:
    """Construct the problem-trace role Schema."""
    s = Schema(strict=strict)

    for nt in PROBLEM_TRACE_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    # No EdgeTypes per design §2.1.
    return s
