"""Problem-trace role-graph schema (Phase 13 PB-1 — NET-NEW).

Per DESIGN_UPPER_LAYER_ROLES.md §2.1.

Single NodeType; no EdgeTypes in v1 (failures are independent records
linked back to the failing task via ``request_id`` property, not via
graph edges within problem-trace). Cross-references to ``capacity-iri``
+ ``request_id`` are property-level, not edge-level.

``strict=False`` per PB-3 / ADR-0149. Advisory properties per PB-8.
"""

from __future__ import annotations

from mindsos_core import NodeType

from ._base import Discipline, L2Schema


# ── Node type ──────────────────────────────────────────────────────────

NODE_PROBLEM_TRACE_ENTRY = "ProblemTraceEntry"

PROBLEM_TRACE_NODE_TYPES: tuple[str, ...] = (NODE_PROBLEM_TRACE_ENTRY,)


# ── Edge types ─────────────────────────────────────────────────────────

PROBLEM_TRACE_EDGE_TYPES: tuple[str, ...] = ()  # v1 has no edge types.


# ── ProblemTraceEntry content / metadata partition (Phase 43 — ADR-0153 §3) ──
#
# All 7 fields are content under ``append_only`` discipline — failure
# records are write-once, never amended. Metadata partition is empty
# (no admin-tunable / lifecycle-mutable fields in v1). Discipline
# enforcement rejects any in-place write to content fields.

PROBLEM_TRACE_ENTRY_CONTENT_FIELDS: frozenset[str] = frozenset({
    "capacity_iri",
    "request_id",
    "step_id",
    "error_type",
    "error_message",
    "emitted_at",
    "context",
})

PROBLEM_TRACE_ENTRY_METADATA_FIELDS: frozenset[str] = frozenset()

PROBLEM_TRACE_ENTRY_PROPS: frozenset[str] = (
    PROBLEM_TRACE_ENTRY_CONTENT_FIELDS | PROBLEM_TRACE_ENTRY_METADATA_FIELDS
)


def build_problem_trace_schema(strict: bool = False) -> L2Schema:
    """Construct the problem-trace role Schema."""
    s = L2Schema(
        mutation_discipline=Discipline.APPEND_ONLY, strict=strict
    )

    for nt in PROBLEM_TRACE_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    # No EdgeTypes per design §2.1.
    return s
