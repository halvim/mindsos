"""Task-patterns role-graph schema (Phase 13 PB-1 — NET-NEW).

Per DESIGN_UPPER_LAYER_ROLES.md §2.1.

``strict=False`` per PB-3 / ADR-0149. Advisory properties per PB-8.
"""

from __future__ import annotations

from mindsos_core import EdgeType, NodeType

from ._base import Discipline, L2Schema


# ── Node types ─────────────────────────────────────────────────────────

NODE_REQUEST_PATTERN = "RequestPattern"
NODE_SUBGOAL_TEMPLATE = "SubgoalTemplate"

REQUEST_PATTERNS_NODE_TYPES: tuple[str, ...] = (
    NODE_REQUEST_PATTERN,
    NODE_SUBGOAL_TEMPLATE,
)


# ── Edge types ─────────────────────────────────────────────────────────

EDGE_DECOMPOSES_INTO = "DECOMPOSES_INTO"
EDGE_PREREQUISITE_OF = "PREREQUISITE_OF"

REQUEST_PATTERNS_EDGE_TYPES: tuple[str, ...] = (
    EDGE_DECOMPOSES_INTO,
    EDGE_PREREQUISITE_OF,
)


# ── RequestPattern content / metadata partition (Phase 43 — ADR-0152 §2 + ADR-0153 §3) ──
#
# 13-field RequestPattern schema v2 per ADR-0152 §2. ``confidence`` KEPT
# (metadata; per-pattern confidence remains useful for L4 prioritisation
# distinct from per-pipeline confidence dropped on Pipeline). Discipline
# is ``immutable_successor`` (ADR-0153 §1).

REQUEST_PATTERN_CONTENT_FIELDS: frozenset[str] = frozenset({
    "pattern_name",
    "task_shape_recognizer",
    "sufficient_predicate_iri",
    "domain",
    "paired_pipelines",
})

REQUEST_PATTERN_METADATA_FIELDS: frozenset[str] = frozenset({
    "relevant_hints",
    "mapping_confidence_threshold",
    "n_observations",
    "confidence",
    "provenance",
    "routing_override",
    "created_at",
    "last_updated_at",
})

REQUEST_PATTERN_PROPS: frozenset[str] = (
    REQUEST_PATTERN_CONTENT_FIELDS | REQUEST_PATTERN_METADATA_FIELDS
)

# SubgoalTemplate partition deferred per ADR-0152 §2 (edge types
# unchanged; SubgoalTemplate carries flat advisory set under Phase 13
# shape). Phase 43 keeps Phase 13's advisory set.
SUBGOAL_TEMPLATE_PROPS: frozenset[str] = frozenset({
    "subgoal_kind",
    "ordering_hint",
})


def build_request_patterns_schema(strict: bool = False) -> L2Schema:
    """Construct the request-patterns role Schema."""
    s = L2Schema(
        mutation_discipline=Discipline.IMMUTABLE_SUCCESSOR, strict=strict
    )

    for nt in REQUEST_PATTERNS_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    any_node = frozenset(REQUEST_PATTERNS_NODE_TYPES)
    for et in REQUEST_PATTERNS_EDGE_TYPES:
        s.add_edge_type(EdgeType(et, any_node, any_node))

    return s
