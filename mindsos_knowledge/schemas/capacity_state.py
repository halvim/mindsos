"""Capacity-state role-graph schema (Phase 13 PB-1 — NET-NEW).

Per DESIGN_UPPER_LAYER_ROLES.md §2.1. Capacity-state lives in the
per-user Local Metagraph (ADR-0044); ``capacity_snapshot_iri`` bakes in
``user_id`` per Phase 12 PB-8 + PB-11.

Single NodeType (``CapacitySnapshot``); no EdgeTypes in v1.
Cross-references to the capacity IRI live as an opaque body inside the
snapshot IRI itself (PB-8 lock; field-level inverse deferred to
Phase 28+).

``strict=False`` per PB-3 / ADR-0149. Advisory properties per PB-8.
"""

from __future__ import annotations

from mindsos_core import NodeType

from ._base import Discipline, L2Schema


# ── Node type ──────────────────────────────────────────────────────────

NODE_CAPACITY_SNAPSHOT = "CapacitySnapshot"

CAPACITY_STATE_NODE_TYPES: tuple[str, ...] = (NODE_CAPACITY_SNAPSHOT,)


# ── Edge types ─────────────────────────────────────────────────────────

CAPACITY_STATE_EDGE_TYPES: tuple[str, ...] = ()  # v1 has no edge types.


# ── Advisory property constants (PB-8) ─────────────────────────────────

CAPACITY_SNAPSHOT_PROPS: frozenset[str] = frozenset({
    "capacity_iri",
    "user_id",
    "taken_at",
    "state_blob",
})


def build_capacity_state_schema(strict: bool = False) -> L2Schema:
    """Construct the capacity-state role Schema (per-user Local; ADR-0044)."""
    s = L2Schema(
        mutation_discipline=Discipline.MUTABLE_WITH_RETENTION, strict=strict
    )

    for nt in CAPACITY_STATE_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    # No EdgeTypes per design §2.1.
    return s
