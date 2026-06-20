"""OEWN three-level lexicon schema (Phase 13 PB-1 — v3 verbatim port).

Lemma / Sense / Synset is the canonical decomposition.

``strict=False`` per PB-3 / ADR-0149: glosses, examples, and lex-file
metadata vary per release; tightening waits for the inventory helper
(deferred per PB-7).

**Empirical layer (Phase 51 / WSD-1 — ADR-0184).** A second, distinct
stratum of EdgeTypes carrying corpus-derived selectional-association
data (the D-L2-2 ``sense-correlations`` disposition; PB-W2). Kept in a
separate tuple (``LEXICON_EMPIRICAL_EDGE_TYPES``) so the
structural/empirical boundary stays explicit; endpoints are restricted
``Sense → Synset`` (deliberate deviation from the structural any→any
pattern). Discipline unchanged: ``ADMIN_AUTHORED`` — writers are the
Phase-52 bootstrap importers and the Phase-55 promotion application
only (PB-W21).
"""

from __future__ import annotations

from mindsos_core import EdgeType, NodeType, PropertyType

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


# ── Empirical layer (Phase 51 — ADR-0184) ──────────────────────────────
#
# Selectional-association stratum: ``Sense -[SEL_ASSOC_<ROLE>]-> Synset``
# ("this verb sense selects this hypernym class in this UD argument
# position"). The role lives in the EdgeType NAME — ``role`` is in
# ``RESERVED_PROPERTY_KEYS`` and would be rejected as an edge property
# (ADR-0184 §Context). Per-corpus provenance = parallel edges (id-keyed
# MERGE; one edge per (sense, role-type, class, source corpus)); the
# Phase-53 scorer sums across them. Obliques (v2) are additive types.

EDGE_SEL_ASSOC_NSUBJ = "SEL_ASSOC_NSUBJ"
EDGE_SEL_ASSOC_DOBJ = "SEL_ASSOC_DOBJ"
EDGE_SEL_ASSOC_IOBJ = "SEL_ASSOC_IOBJ"

LEXICON_EMPIRICAL_EDGE_TYPES: tuple[str, ...] = (
    EDGE_SEL_ASSOC_NSUBJ,
    EDGE_SEL_ASSOC_DOBJ,
    EDGE_SEL_ASSOC_IOBJ,
)

#: Declared on every empirical EdgeType (informative at ``strict=False``
#: per ADR-0149; binding if strict ever lands). All Falkor-primitive —
#: the ADR-0182 node-value codec does NOT extend to edge property bags
#: (ADR-0184 §6). ``smoothed_score`` is a cache: ``count`` is ground
#: truth; the Phase-55 promotion application owns recomputes (§4).
EMPIRICAL_EDGE_PROPERTY_TYPES: dict[str, PropertyType] = {
    "count": PropertyType.INT,
    "smoothed_score": PropertyType.FLOAT,
    "source": PropertyType.STRING,
    "corpus_version": PropertyType.STRING,
}

#: Per-``Sense`` node property backing the MFS prior (ADR-0184 §5).
#: Named here at Phase 51 so the vocabulary is complete before the
#: Phase-52 importers ship; populated from SemCor counts at Phase 52.
#: Absence ⇒ the MFS prior is unavailable for that lemma (the scorer's
#: behavior on absence is Phase 53's contract).
SENSE_PROP_CORPUS_FREQUENCY = "corpus_frequency"


def build_lexicon_schema(strict: bool = False) -> L2Schema:
    """Construct the OEWN three-level lexicon Schema (Phase 13).

    Phase 51 (ADR-0184): also registers the empirical-layer
    selectional-association EdgeTypes — endpoint-restricted
    ``Sense → Synset``, with declared ``property_types``.
    """
    s = L2Schema(
        mutation_discipline=Discipline.ADMIN_AUTHORED, strict=strict
    )

    for nt in LEXICON_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    any_node = frozenset(LEXICON_NODE_TYPES)
    for et in LEXICON_EDGE_TYPES:
        s.add_edge_type(EdgeType(et, any_node, any_node))

    sense_only = frozenset({NODE_SENSE})
    synset_only = frozenset({NODE_SYNSET})
    for et in LEXICON_EMPIRICAL_EDGE_TYPES:
        s.add_edge_type(
            EdgeType(
                et,
                sense_only,
                synset_only,
                property_types=dict(EMPIRICAL_EDGE_PROPERTY_TYPES),
            )
        )

    return s
