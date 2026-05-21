"""Phase 16 PB-V2 sentinel — `build_corpus()` is deterministic.

Two calls produce identical content (same graph count, same node ids,
same edge count). If the generator ever drifts, this test fails before
any downstream similarity-test does — surfacing the cause at the
source rather than as opaque downstream score changes.
"""

from __future__ import annotations

from tests.phase_16.fixtures.build_corpus import corpus_fingerprint


def test_build_corpus_returns_same_fingerprint_on_two_calls() -> None:
    fp1 = corpus_fingerprint()
    fp2 = corpus_fingerprint()
    assert fp1 == fp2, (
        f"corpus generator drifted between calls — "
        f"fp1={fp1!r} vs fp2={fp2!r}"
    )


def test_corpus_has_three_role_graphs() -> None:
    n_graphs, _n_nodes, _n_edges, _ids = corpus_fingerprint()
    assert n_graphs == 3, (
        f"corpus should ship 3 role-graphs (ontology/lexicon/concepts); got {n_graphs}"
    )


def test_corpus_node_ids_are_iri_shaped() -> None:
    """All corpus node-ids carry the IRI tail convention used by the Lev scorer."""
    _g, _n, _e, ids = corpus_fingerprint()
    for nid in ids:
        assert ":" in nid, (
            f"corpus node id {nid!r} lacks the `:`-separated IRI structure "
            "expected by the Levenshtein scorer's `_iri_tail` helper."
        )
