"""Pending-promotions role-graph schema (Phase 43 — Rail A slot 2 NET-NEW).

Per ADR-0152 §4 + L2_CHAT_DECISIONS D-L2-13. Dual-scope (Local +
Global) — ALS-driven promotion proposals + audit chain for parameter
applies. Local stores user-scoped promotions in flight; Global stores
system-proposed cross-user promotions.

Single NodeType (``PendingPromotion``); no EdgeTypes in v1.

Discipline: ``audit_only_after_settled`` per ADR-0153 §1. Rows mutate
until terminal ``status ∈ {applied, rejected}``; once settled, frozen
for audit chain integrity. No per-field partition required —
audit_only discipline is gated by the ``is_settled`` flag, not by
content/metadata classification.

``strict=False`` per ADR-0149.
"""

from __future__ import annotations

from mindsos_core import NodeType

from ._base import Discipline, L2Schema


# ── Node type ──────────────────────────────────────────────────────────

NODE_PENDING_PROMOTION = "PendingPromotion"

PENDING_PROMOTIONS_NODE_TYPES: tuple[str, ...] = (NODE_PENDING_PROMOTION,)


# ── Edge types ─────────────────────────────────────────────────────────

PENDING_PROMOTIONS_EDGE_TYPES: tuple[str, ...] = ()  # v1 has no edge types.


# ── Advisory property constants (Phase 43 — ADR-0152 §4) ──────────────

PENDING_PROMOTION_PROPS: frozenset[str] = frozenset({
    "parameter_set_iri",
    "proposed_at",
    "scope",
    "proposer",
    "audit_policy",
    "validation_results",
    "proposed_diff",
    "evidence_summary",
    "status",
    "decision_at",
    "decided_by",
    "decision_notes",
})


def build_pending_promotions_schema(strict: bool = False) -> L2Schema:
    """Construct the pending-promotions role Schema (Local + Global)."""
    s = L2Schema(
        mutation_discipline=Discipline.AUDIT_ONLY_AFTER_SETTLED,
        strict=strict,
    )

    for nt in PENDING_PROMOTIONS_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    # No EdgeTypes per ADR-0152 §4.
    return s
