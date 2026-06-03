"""Parameter-staging role-graph schema (Phase 43 — Rail A slot 2 NET-NEW).

Per ADR-0152 §3 + L2_CHAT_DECISIONS D-L2-11. Local-per-user only — ALS
subsystem evidence-staging buffer where signal-source observations
collect before ALS promotion decisions move them to
``learned-parameters`` (Global) or ``pending-promotions`` (audit chain).

Single NodeType (``StagedEvidence``); no EdgeTypes in v1.
``parameter_set_iri`` is opaque per D-L2-12 (FOL #4 split deferred).

Discipline: ``mutable_with_retention`` per ADR-0153 §1. TTL-pruned
evidence rows (retention_window_until field; admin-tunable default
30 days per ADR-0152 §3). No per-field partition required at
``mutable_with_retention`` discipline.

``strict=False`` per ADR-0149.
"""

from __future__ import annotations

from mindsos_core import NodeType

from ._base import Discipline, L2Schema


# ── Node type ──────────────────────────────────────────────────────────

NODE_STAGED_EVIDENCE = "StagedEvidence"

PARAMETER_STAGING_NODE_TYPES: tuple[str, ...] = (NODE_STAGED_EVIDENCE,)


# ── Edge types ─────────────────────────────────────────────────────────

PARAMETER_STAGING_EDGE_TYPES: tuple[str, ...] = ()  # v1 has no edge types.


# ── Advisory property constants (Phase 43 — ADR-0152 §3) ──────────────

STAGED_EVIDENCE_PROPS: frozenset[str] = frozenset({
    "parameter_set_iri",
    "signal_source_iri",
    "target_parameter_iri",
    "target_value",
    "evidence_pointer",
    "signal_weight",
    "blame_weight",
    "staged_at",
    "retention_window_until",
})


def build_parameter_staging_schema(strict: bool = False) -> L2Schema:
    """Construct the parameter-staging role Schema (Local-per-user)."""
    s = L2Schema(
        mutation_discipline=Discipline.MUTABLE_WITH_RETENTION, strict=strict
    )

    for nt in PARAMETER_STAGING_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    # No EdgeTypes per ADR-0152 §3.
    return s
