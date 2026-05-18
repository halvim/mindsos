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

from mindsos_core import EdgeType, NodeType, Schema


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


# ── Advisory property constants (PB-8) ─────────────────────────────────

PIPELINE_PROPS: frozenset[str] = frozenset({
    "pipeline_name",
    "task_type",
    "confidence",
    "n_runs",
})

PIPELINE_STEP_PROPS: frozenset[str] = frozenset({
    "capacity_iri",
    "input_datastate",
    "output_datastate",
    "position",
})

HAS_STEP_POSITION_PROPERTY = "position"


def build_promoted_pipelines_schema(strict: bool = False) -> Schema:
    """Construct the promoted-pipelines role Schema."""
    s = Schema(strict=strict)

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
