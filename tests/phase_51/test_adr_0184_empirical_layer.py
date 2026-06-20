"""Phase 51 — ADR-0184 empirical-layer vocabulary sentinels (hermetic).

Pins: the SEL_ASSOC_* EdgeTypes (separate empirical tuple; PB-51-9),
endpoint restriction Sense→Synset (PB-51-8), the declared property set
(PB-51-1/4), the MFS Sense-property name (PB-51-2), reserved-key
cleanliness, and the persist statement shape (rel-type + props ride the
id-keyed edge MERGE). The live save→load round-trip is in
``test_adr_0184_live_round_trip.py`` (integration-marked).
"""

from __future__ import annotations

import pytest

from mindsos_core import PropertyType
from mindsos_core.cypher.identifiers import validate_edge_type_identifier
from mindsos_core.schema.validation import RESERVED_PROPERTY_KEYS
from mindsos_knowledge.schemas.lexicon import (
    EDGE_SEL_ASSOC_DOBJ,
    EDGE_SEL_ASSOC_IOBJ,
    EDGE_SEL_ASSOC_NSUBJ,
    EMPIRICAL_EDGE_PROPERTY_TYPES,
    LEXICON_EDGE_TYPES,
    LEXICON_EMPIRICAL_EDGE_TYPES,
    NODE_SENSE,
    NODE_SYNSET,
    SENSE_PROP_CORPUS_FREQUENCY,
    build_lexicon_schema,
)


def test_empirical_tuple_is_separate_and_complete():
    """PB-51-9: stratum boundary lives in the constants — the structural
    tuple is untouched and the empirical tuple holds exactly the 3
    per-role types (PB-51-1: role in the NAME, not a property)."""
    assert LEXICON_EMPIRICAL_EDGE_TYPES == (
        EDGE_SEL_ASSOC_NSUBJ,
        EDGE_SEL_ASSOC_DOBJ,
        EDGE_SEL_ASSOC_IOBJ,
    )
    assert not set(LEXICON_EMPIRICAL_EDGE_TYPES) & set(LEXICON_EDGE_TYPES)
    assert len(LEXICON_EDGE_TYPES) == 22  # Phase 13 structural roster frozen


def test_empirical_edge_names_are_cypher_safe():
    for et in LEXICON_EMPIRICAL_EDGE_TYPES:
        validate_edge_type_identifier(et)  # raises on violation (ADR-0021)


def test_builder_registers_empirical_types_with_restricted_endpoints():
    """PB-51-8: Sense→Synset only — deliberate deviation from the
    structural any→any pattern."""
    s = build_lexicon_schema()
    for et_name in LEXICON_EMPIRICAL_EDGE_TYPES:
        et = s.edge_types[et_name]
        assert et.allowed_sources == frozenset({NODE_SENSE})
        assert et.allowed_targets == frozenset({NODE_SYNSET})
        assert et.property_types == EMPIRICAL_EDGE_PROPERTY_TYPES


def test_declared_property_set_matches_adr_0184():
    """ADR-0184 §3 — the consumer columns (slot-52 writers / slot-53
    reader), all Falkor-primitive (§6: no ADR-0182 codec on edges)."""
    assert EMPIRICAL_EDGE_PROPERTY_TYPES == {
        "count": PropertyType.INT,
        "smoothed_score": PropertyType.FLOAT,
        "source": PropertyType.STRING,
        "corpus_version": PropertyType.STRING,
    }


def test_property_names_clear_reserved_keys():
    """Round-2 grounding (design log §2 note 3): ``role`` IS reserved —
    these must never collide."""
    names = set(EMPIRICAL_EDGE_PROPERTY_TYPES) | {SENSE_PROP_CORPUS_FREQUENCY}
    assert not names & RESERVED_PROPERTY_KEYS


def test_mfs_property_name_pinned():
    """PB-51-2: the MFS prior's home is named at Phase 51; Phase 52
    populates it. Renaming it breaks the importer/scorer contract."""
    assert SENSE_PROP_CORPUS_FREQUENCY == "corpus_frequency"


def test_endpoint_violation_rejected_even_at_strict_false():
    """Phase-50 I5: type membership enforcement is independent of
    ``strict`` — a Synset→Sense SEL_ASSOC edge must be rejected."""
    from mindsos_core.exceptions import UnknownTypeError
    from mindsos_core.models.graph import Graph

    g = Graph(name="lex-probe", role="lexicon", schema=build_lexicon_schema())
    sense = g.add_node("eat%2:34:00::", NODE_SENSE)
    synset = g.add_node("food.n.01", NODE_SYNSET)

    edge = g.add_edge(
        sense,
        synset,
        EDGE_SEL_ASSOC_DOBJ,
        properties={
            "count": 17,
            "smoothed_score": 0.42,
            "source": "semcor",
            "corpus_version": "semcor-3.0",
        },
    )
    assert edge.type_name == EDGE_SEL_ASSOC_DOBJ

    with pytest.raises(UnknownTypeError):
        g.add_edge(synset, sense, EDGE_SEL_ASSOC_DOBJ)  # reversed endpoints


def test_persist_statement_carries_rel_type_and_props():
    """The empirical stratum rides the existing id-keyed edge MERGE
    (PB-51-4 retired risk): the builder splices the rel type and ships
    the property bag via ``e += row.props``."""
    from mindsos_core.cypher.builders import build_unwind_create_edges

    query, params = build_unwind_create_edges(
        "g1",
        EDGE_SEL_ASSOC_NSUBJ,
        [
            {
                "id": "e1",
                "source": "n1",
                "target": "n2",
                "label": None,
                "props": {
                    "count": 3,
                    "smoothed_score": 0.1,
                    "source": "glosstag",
                    "corpus_version": "glosstag-1.0",
                },
                "_version": 1,
            }
        ],
    )
    assert f"[e:{EDGE_SEL_ASSOC_NSUBJ} " in query
    assert "{id: row.id}" in query and "e += row.props" in query
    assert params["rows"][0]["props"]["count"] == 3
