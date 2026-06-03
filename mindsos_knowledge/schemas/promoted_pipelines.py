"""Promoted-pipelines role-graph schema (Phase 13 PB-1 — NET-NEW).

Per DESIGN_UPPER_LAYER_ROLES.md §2.1 + Phase 13 PB-1 closure of the
L2 schema dispatch table.

``HAS_STEP`` is a regular EdgeType with ``position`` as an advisory
property (Phase 13 PB-9 lock — NOT an ordered hyperedge). The
``position`` ordering claim is on the *set of steps from one Pipeline*,
not on the edge itself; property-on-edge is the right model.

``strict=False`` per PB-3 / ADR-0149. Properties documented as
module-level advisory constants per PB-8 — NOT registered on the
NodeType (strict-tighten PR converts these to ``PropertyType`` enum
declarations once the inventory helper observes which types L4 actually
writes).
"""

from __future__ import annotations

from mindsos_core import EdgeType, NodeType

from ._base import Discipline, L2Schema


# ── Node types ─────────────────────────────────────────────────────────

NODE_PIPELINE = "Pipeline"
NODE_PIPELINE_STEP = "PipelineStep"

PROMOTED_PIPELINES_NODE_TYPES: tuple[str, ...] = (
    NODE_PIPELINE,
    NODE_PIPELINE_STEP,
)


# ── Edge types ─────────────────────────────────────────────────────────

EDGE_HAS_STEP = "HAS_STEP"
EDGE_DERIVED_FROM = "DERIVED_FROM"

PROMOTED_PIPELINES_EDGE_TYPES: tuple[str, ...] = (
    EDGE_HAS_STEP,
    EDGE_DERIVED_FROM,
)


# ── Pipeline content / metadata partition (Phase 43 — ADR-0152 §1 + ADR-0153 §3) ──
#
# 16-field Pipeline schema v2 per ADR-0152 §1. ``confidence`` DROPPED per
# ADR-0094 §amendment-1; per-pipeline confidence migrates to ALS
# subsystems on ``learned-parameters``. Discipline is
# ``immutable_successor`` (ADR-0153 §1) — content fields require
# successor IRIs on change; metadata fields mutate in place under the
# per-field partition.

PIPELINE_CONTENT_FIELDS: frozenset[str] = frozenset({
    "pipeline_name",
    "edge_sequence",
    "start_ds",
    "end_ds",
    "expression_metadata",
})

PIPELINE_METADATA_FIELDS: frozenset[str] = frozenset({
    "status",
    "n_runs",
    "outcome_history",
    "provenance",
    "quarantine_threshold",
    "created_at",
    "tested_at",
    "activated_at",
    "quarantined_at",
    "quarantined_by",
    "retired_at",
})

PIPELINE_PROPS: frozenset[str] = (
    PIPELINE_CONTENT_FIELDS | PIPELINE_METADATA_FIELDS
)

# PipelineStep partition deferred to ADR-0152 §amendment-1 (post-reframe
# HAS_STEP shape resolution). Phase 43 keeps Phase 13's advisory set.
PIPELINE_STEP_PROPS: frozenset[str] = frozenset({
    "capacity_iri",
    "input_datastate",
    "output_datastate",
    "position",
})

HAS_STEP_POSITION_PROPERTY = "position"


def build_promoted_pipelines_schema(strict: bool = False) -> L2Schema:
    """Construct the promoted-pipelines role Schema."""
    s = L2Schema(
        mutation_discipline=Discipline.IMMUTABLE_SUCCESSOR, strict=strict
    )

    for nt in PROMOTED_PIPELINES_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    # HAS_STEP: Pipeline → PipelineStep. DERIVED_FROM: Pipeline → Pipeline.
    # PB-9 lock: regular EdgeType, not hyperedge. Endpoint constraints
    # documented in comments here; structural typing is permissive
    # (any_node → any_node) to mirror v3 pattern + allow future
    # extension without amendment.
    any_node = frozenset(PROMOTED_PIPELINES_NODE_TYPES)
    for et in PROMOTED_PIPELINES_EDGE_TYPES:
        s.add_edge_type(EdgeType(et, any_node, any_node))

    return s
