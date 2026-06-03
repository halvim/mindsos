"""FrameNet concepts schema (Phase 13 PB-1 — v3 verbatim port).

``strict=False`` per PB-3 / ADR-0149.
"""

from __future__ import annotations

from mindsos_core import EdgeType, NodeType

from ._base import Discipline, L2Schema


# ── Node types ─────────────────────────────────────────────────────────

NODE_FRAME = "Frame"
NODE_FRAME_ELEMENT = "FrameElement"
NODE_LEXICAL_UNIT = "LexicalUnit"
NODE_SEMANTIC_TYPE = "SemanticType"

CONCEPTS_NODE_TYPES: tuple[str, ...] = (
    NODE_FRAME,
    NODE_FRAME_ELEMENT,
    NODE_LEXICAL_UNIT,
    NODE_SEMANTIC_TYPE,
)


# ── Edge types ─────────────────────────────────────────────────────────

EDGE_EVOKES = "EVOKES"
EDGE_HAS_FE = "HAS_FE"

# Frame-to-frame relations
EDGE_INHERITS_FROM = "INHERITS_FROM"
EDGE_USES = "USES"
EDGE_PERSPECTIVE_ON = "PERSPECTIVE_ON"
EDGE_SUBFRAME_OF = "SUBFRAME_OF"
EDGE_PRECEDES = "PRECEDES"
EDGE_IS_CAUSATIVE_OF = "IS_CAUSATIVE_OF"
EDGE_IS_INCHOATIVE_OF = "IS_INCHOATIVE_OF"

# FE-level
EDGE_FE_TYPED_AS = "FE_TYPED_AS"
EDGE_FE_MAPPED_TO = "FE_MAPPED_TO"

CONCEPTS_EDGE_TYPES: tuple[str, ...] = (
    EDGE_EVOKES,
    EDGE_HAS_FE,
    EDGE_INHERITS_FROM,
    EDGE_USES,
    EDGE_PERSPECTIVE_ON,
    EDGE_SUBFRAME_OF,
    EDGE_PRECEDES,
    EDGE_IS_CAUSATIVE_OF,
    EDGE_IS_INCHOATIVE_OF,
    EDGE_FE_TYPED_AS,
    EDGE_FE_MAPPED_TO,
)


def build_concepts_schema(strict: bool = False) -> L2Schema:
    """Construct the FrameNet concepts Schema (Phase 13)."""
    s = L2Schema(
        mutation_discipline=Discipline.ADMIN_AUTHORED, strict=strict
    )

    for nt in CONCEPTS_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    any_node = frozenset(CONCEPTS_NODE_TYPES)
    for et in CONCEPTS_EDGE_TYPES:
        s.add_edge_type(EdgeType(et, any_node, any_node))

    return s
