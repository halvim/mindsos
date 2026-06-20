"""Phase 51 — ADR-0184 live round-trip (phase-map §2 WSD-1 pass criterion).

A lexicon graph carrying SEL_ASSOC_* edges (the §3 property set) plus a
``corpus_frequency``-stamped Sense node persists and reloads byte-equal
through the ADR-0182 persister path (``MetagraphRepository`` →
``MetagraphLoader`` — the same path the Phase-50 codec landed on).
Integration-marked; skips without the FalkorDB sidecar (Phase 32/49
fixture precedent).
"""

from __future__ import annotations

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture
from tests._shared.metagraph_equality import assert_metagraphs_equal

pytestmark = pytest.mark.integration


def test_live_empirical_layer_round_trip(falkor_client) -> None:  # noqa: F811
    from mindsos_core import Metagraph
    from mindsos_core.models.graph import Graph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import MetagraphLoader
    from mindsos_knowledge.schemas.lexicon import (
        EDGE_SEL_ASSOC_DOBJ,
        EDGE_SEL_ASSOC_NSUBJ,
        NODE_SENSE,
        NODE_SYNSET,
        SENSE_PROP_CORPUS_FREQUENCY,
        build_lexicon_schema,
    )

    mg = Metagraph(name="empirical-rt-probe")
    g = mg.add_graph(
        Graph(name="lexicon", role="lexicon", schema=build_lexicon_schema())
    )
    sense = g.add_node(
        "eat%2:34:00::",
        NODE_SENSE,
        properties={SENSE_PROP_CORPUS_FREQUENCY: 61},  # ADR-0184 §5
    )
    food = g.add_node("food.n.01", NODE_SYNSET)
    person = g.add_node("person.n.01", NODE_SYNSET)
    # Parallel provenance edges on the SAME (sense, role, class) triple —
    # ADR-0184 §4 (one edge per source corpus; id-keyed MERGE).
    g.add_edge(
        sense, food, EDGE_SEL_ASSOC_DOBJ,
        properties={
            "count": 17, "smoothed_score": 0.42,
            "source": "semcor", "corpus_version": "semcor-3.0",
        },
    )
    g.add_edge(
        sense, food, EDGE_SEL_ASSOC_DOBJ,
        properties={
            "count": 5, "smoothed_score": 0.31,
            "source": "glosstag", "corpus_version": "glosstag-1.0",
        },
    )
    g.add_edge(
        sense, person, EDGE_SEL_ASSOC_NSUBJ,
        properties={
            "count": 23, "smoothed_score": 0.55,
            "source": "semcor", "corpus_version": "semcor-3.0",
        },
    )

    MetagraphRepository(falkor_client).persist(mg)

    loader = MetagraphLoader(falkor_client)
    mid = loader.find_by_name("empirical-rt-probe")
    assert mid is not None
    loaded = loader.load(mid)
    assert_metagraphs_equal(mg, loaded)

    (lg,) = loaded.graphs.values()
    assert (
        lg.nodes[sense.node_id].properties[SENSE_PROP_CORPUS_FREQUENCY] == 61
    )
    dobj = [
        e for e in lg.edges.values() if e.type_name == EDGE_SEL_ASSOC_DOBJ
    ]
    assert len(dobj) == 2  # parallel co-typed provenance edges survive
    assert {e.properties["source"] for e in dobj} == {"semcor", "glosstag"}

    # Idempotent re-persist (MERGE-safe) keeps the pair equal.
    MetagraphRepository(falkor_client).persist(loaded)
    assert_metagraphs_equal(mg, loader.load(mid))
