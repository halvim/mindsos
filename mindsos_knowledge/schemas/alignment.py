"""Alignment-graph schema — shared-anchor pattern (Phase 13 PB-5 + PB-14).

An alignment graph contains:

* ``AlignmentAnchor`` nodes, each carrying a ``ref:<role>`` property
  pointing at the aligned entity on that side. Shared-anchor rule:
  if the same entity participates in N mappings, ONE anchor node
  serves all N.
* Edges between anchors, typed by the mapping vocabulary below.

Per PB-14: the alignment vocabulary is intentionally OPEN —
``extra_edge_types`` kwarg lets callers register additional mapping
types at build time without forking the module.

Per PB-5: the schema is **parametric** — one builder serves all
alignment-pair graphs (`alignment:concepts:lexicon`,
`alignment:lexicon:ontology`, etc.; sorted role atoms separated by
`:` per ADR-0154 + L2_CHAT_DECISIONS D-L2-1, Phase 39 L2-35
reconciliation). Anchor IRI minting is deferred
to Phase 14 (KL bootstrap) — Phase 13 only declares the
``AlignmentAnchor`` NodeType and the edge vocabulary; how anchors
identify themselves to the system is a Phase 14 decision.

``strict=False`` per PB-3 / ADR-0149.
"""

from __future__ import annotations

from mindsos_core import EdgeType, NodeType, Schema


# ── Node types ─────────────────────────────────────────────────────────

NODE_ALIGNMENT_ANCHOR = "AlignmentAnchor"

ALIGNMENT_NODE_TYPES: tuple[str, ...] = (NODE_ALIGNMENT_ANCHOR,)


# ── Mapping vocabulary (open — extra_edge_types extends) ───────────────

EDGE_LEXICALIZES = "LEXICALIZES"
EDGE_EXACT_MATCH = "EXACT_MATCH"
EDGE_CLOSE_MATCH = "CLOSE_MATCH"
EDGE_NARROWER_THAN = "NARROWER_THAN"
EDGE_BROADER_THAN = "BROADER_THAN"
EDGE_EVOKES = "EVOKES"
EDGE_INSTANCE_OF_CLASS = "INSTANCE_OF_CLASS"
EDGE_RELATED_TO = "RELATED_TO"

ALIGNMENT_EDGE_TYPES: tuple[str, ...] = (
    EDGE_LEXICALIZES,
    EDGE_EXACT_MATCH,
    EDGE_CLOSE_MATCH,
    EDGE_NARROWER_THAN,
    EDGE_BROADER_THAN,
    EDGE_EVOKES,
    EDGE_INSTANCE_OF_CLASS,
    EDGE_RELATED_TO,
)


def build_alignment_schema(
    strict: bool = False, extra_edge_types: tuple[str, ...] = ()
) -> Schema:
    """Construct an alignment-graph Schema.

    Args:
        strict: Opt-in property-type enforcement. Default ``False``
            per PB-3 / ADR-0149.
        extra_edge_types: Additional mapping types beyond the 8-element
            starter vocabulary. Each entry MUST match ADR-0021's Cypher
            rel-type regex ``^[A-Z][A-Z0-9_]{0,63}$`` (validated by
            ``Schema.add_edge_type``).
    """
    s = Schema(strict=strict)
    s.add_node_type(NodeType(NODE_ALIGNMENT_ANCHOR))

    any_node = frozenset(ALIGNMENT_NODE_TYPES)
    for et in tuple(ALIGNMENT_EDGE_TYPES) + tuple(extra_edge_types):
        s.add_edge_type(EdgeType(et, any_node, any_node))

    return s
