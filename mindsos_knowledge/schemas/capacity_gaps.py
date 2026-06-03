"""Capacity-gaps role-graph schema (Phase 43 — Rail A slot 2 NET-NEW).

Per ADR-0152 §5 + L2_CHAT_DECISIONS D-L2-14. Global-only — system
records unsolvable-task gaps + dream-found promotion candidates for
admin review.

Discriminated NodeType: ``gap_kind ∈ {unsolvable_task, promotion_candidate}``
per ADR-0152 §5. Unsolvable-task gaps record task-shape + datastates +
attempted searches. Promotion-candidate gaps record dream-found
candidates per Chat B D-B53 + L5 cascade L0-13.

Single NodeType (``CapacityGap``); no EdgeTypes in v1.

Discipline: ``mutable_with_retention`` per ADR-0153 §1 (admin actions
mutate status; retention policy per admin tuning). Originally tabled
as ``admin_authored`` at L2 chat closure D-L2-3 — Phase 43 PR1 commit 7
cascade cleanup reassigned to ``mutable_with_retention`` per ADR-0152
§5 + ADR-0153 §1. No per-field partition required.

``strict=False`` per ADR-0149.
"""

from __future__ import annotations

from mindsos_core import NodeType

from ._base import Discipline, L2Schema


# ── Node type ──────────────────────────────────────────────────────────

NODE_CAPACITY_GAP = "CapacityGap"

CAPACITY_GAPS_NODE_TYPES: tuple[str, ...] = (NODE_CAPACITY_GAP,)


# ── Edge types ─────────────────────────────────────────────────────────

CAPACITY_GAPS_EDGE_TYPES: tuple[str, ...] = ()  # v1 has no edge types.


# ── Advisory property constants (Phase 43 — ADR-0152 §5) ──────────────

CAPACITY_GAP_PROPS: frozenset[str] = frozenset({
    "gap_kind",
    "task_shape_iri",
    "start_datastate_iri",
    "goal_datastate_iri",
    "candidate_kind",
    "candidate_proposal",
    "attempted_searches",
    "first_seen_at",
    "last_seen_at",
    "occurrence_count",
    "status",
    "resolution",
    "resolved_at",
    "resolved_by",
})


def build_capacity_gaps_schema(strict: bool = False) -> L2Schema:
    """Construct the capacity-gaps role Schema (Global-only)."""
    s = L2Schema(
        mutation_discipline=Discipline.MUTABLE_WITH_RETENTION, strict=strict
    )

    for nt in CAPACITY_GAPS_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    # No EdgeTypes per ADR-0152 §5.
    return s
