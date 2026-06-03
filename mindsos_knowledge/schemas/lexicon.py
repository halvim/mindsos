"""OEWN three-level lexicon schema (Phase 13 PB-1 — v3 verbatim port).

Lemma / Sense / Synset is the canonical decomposition.

``strict=False`` per PB-3 / ADR-0149: glosses, examples, and lex-file
metadata vary per release; tightening waits for the inventory helper
(deferred per PB-7).
"""

from __future__ import annotations

from mindsos_core import EdgeType, NodeType

from ._base import Discipline, L2Schema


# ── Node types ─────────────────────────────────────────────────────────

NODE_LEMMA = "Lemma"
NODE_SENSE = "Sense"
NODE_SYNSET = "Synset"
NODE_SENSE_EXAMPLE = "SenseExample"

LEXICON_NODE_TYPES: tuple[str, ...] = (
    NODE_LEMMA,
    NODE_SENSE,
    NODE_SYNSET,
    NODE_SENSE_EXAMPLE,
)


# ── Edge types ─────────────────────────────────────────────────────────

# Structural
EDGE_HAS_SENSE = "HAS_SENSE"
EDGE_IN_SYNSET = "IN_SYNSET"

# Synset → Synset (taxonomic)
EDGE_HYPERNYM_OF = "HYPERNYM_OF"
EDGE_HYPONYM_OF = "HYPONYM_OF"
EDGE_INSTANCE_HYPERNYM_OF = "INSTANCE_HYPERNYM_OF"
EDGE_INSTANCE_HYPONYM_OF = "INSTANCE_HYPONYM_OF"

# Part / whole
EDGE_MERONYM_PART_OF = "MERONYM_PART_OF"
EDGE_MERONYM_MEMBER_OF = "MERONYM_MEMBER_OF"
EDGE_MERONYM_SUBSTANCE_OF = "MERONYM_SUBSTANCE_OF"
EDGE_HOLONYM_PART_OF = "HOLONYM_PART_OF"
EDGE_HOLONYM_MEMBER_OF = "HOLONYM_MEMBER_OF"
EDGE_HOLONYM_SUBSTANCE_OF = "HOLONYM_SUBSTANCE_OF"

# Verb-synset relations
EDGE_ENTAILS = "ENTAILS"
EDGE_CAUSES = "CAUSES"

# Misc synset relations
EDGE_SIMILAR_TO = "SIMILAR_TO"
EDGE_ATTRIBUTE_OF = "ATTRIBUTE_OF"
EDGE_ALSO_SEE = "ALSO_SEE"

# Sense-level
EDGE_ANTONYM_OF = "ANTONYM_OF"
EDGE_DERIVATIONALLY_RELATED_TO = "DERIVATIONALLY_RELATED_TO"
EDGE_PERTAINS_TO = "PERTAINS_TO"
EDGE_PARTICIPLE_OF = "PARTICIPLE_OF"

# Example attachment
EDGE_HAS_EXAMPLE = "HAS_EXAMPLE"

LEXICON_EDGE_TYPES: tuple[str, ...] = (
    EDGE_HAS_SENSE,
    EDGE_IN_SYNSET,
    EDGE_HYPERNYM_OF,
    EDGE_HYPONYM_OF,
    EDGE_INSTANCE_HYPERNYM_OF,
    EDGE_INSTANCE_HYPONYM_OF,
    EDGE_MERONYM_PART_OF,
    EDGE_MERONYM_MEMBER_OF,
    EDGE_MERONYM_SUBSTANCE_OF,
    EDGE_HOLONYM_PART_OF,
    EDGE_HOLONYM_MEMBER_OF,
    EDGE_HOLONYM_SUBSTANCE_OF,
    EDGE_ENTAILS,
    EDGE_CAUSES,
    EDGE_SIMILAR_TO,
    EDGE_ATTRIBUTE_OF,
    EDGE_ALSO_SEE,
    EDGE_ANTONYM_OF,
    EDGE_DERIVATIONALLY_RELATED_TO,
    EDGE_PERTAINS_TO,
    EDGE_PARTICIPLE_OF,
    EDGE_HAS_EXAMPLE,
)


def build_lexicon_schema(strict: bool = False) -> L2Schema:
    """Construct the OEWN three-level lexicon Schema (Phase 13)."""
    s = L2Schema(
        mutation_discipline=Discipline.ADMIN_AUTHORED, strict=strict
    )

    for nt in LEXICON_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    any_node = frozenset(LEXICON_NODE_TYPES)
    for et in LEXICON_EDGE_TYPES:
        s.add_edge_type(EdgeType(et, any_node, any_node))

    return s
