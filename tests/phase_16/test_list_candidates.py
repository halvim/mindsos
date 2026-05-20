"""Phase 16 PB-C2 + PB-J3 — `list_candidates` filter semantics.

Default: role-wide minus ADR-0051 PROMOTED breadcrumbs.
Optional: ``node_type`` NodeType filter; ``where`` caller predicate.
Result ordering: deterministic sort by ``node_id``.
"""

from __future__ import annotations

import pytest

from mindsos_admin import CandidateRef, list_candidates
from mindsos_core import Graph, Metagraph
from tests.phase_16.fixtures.build_corpus import (
    LEX_LEMMA_CAR,
    LEX_LEMMA_AUTO,
    LEX_SYNSET_CAR,
    build_corpus,
)


@pytest.fixture
def mg():
    return build_corpus()


class TestDefaultBehaviour:
    def test_returns_role_wide_all_nodetypes(self, mg) -> None:
        refs = list_candidates(mg, role="lexicon")
        # Corpus lexicon has 3 Synset + 2 Lemma = 5 nodes; all included.
        assert len(refs) == 5
        node_types = {r.node_type for r in refs}
        assert node_types == {"Synset", "Lemma"}

    def test_results_sorted_by_node_id(self, mg) -> None:
        refs = list_candidates(mg, role="ontology")
        ids = [r.node_id for r in refs]
        assert ids == sorted(ids)

    def test_returns_candidaterefs(self, mg) -> None:
        refs = list_candidates(mg, role="ontology")
        for r in refs:
            assert isinstance(r, CandidateRef)
            assert r.role == "ontology"
            assert r.source_user_id is None  # Phase 16: no user concept yet


class TestPromotedFilter:
    def test_promoted_breadcrumbs_excluded(self, mg) -> None:
        # Stamp the breadcrumb on one lexicon node.
        lex = next(g for g in mg.graphs.values() if g.role == "lexicon")
        lex.update_node_properties(LEX_LEMMA_CAR, {"ref_type": "PROMOTED"})
        refs = list_candidates(mg, role="lexicon")
        ids = {r.node_id for r in refs}
        assert LEX_LEMMA_CAR not in ids, (
            "PROMOTED-tagged node was included; PB-C2 default-filter violated."
        )
        # And the rest are still there.
        assert LEX_LEMMA_AUTO in ids
        assert LEX_SYNSET_CAR in ids


class TestNodeTypeFilter:
    def test_filter_to_single_nodetype(self, mg) -> None:
        refs = list_candidates(mg, role="lexicon", node_type="Synset")
        assert len(refs) == 3
        assert all(r.node_type == "Synset" for r in refs)

    def test_filter_to_unknown_nodetype_returns_empty(self, mg) -> None:
        refs = list_candidates(
            mg, role="lexicon", node_type="DoesNotExist"
        )
        assert refs == []


class TestWherePredicate:
    def test_caller_predicate_filters(self, mg) -> None:
        refs = list_candidates(
            mg,
            role="lexicon",
            where=lambda node: node.value.startswith("car"),
        )
        ids = {r.node_id for r in refs}
        # car (Lemma) + car.n.01 (Synset).
        assert LEX_LEMMA_CAR in ids
        assert LEX_SYNSET_CAR in ids
        # automobile not included.
        assert LEX_LEMMA_AUTO not in ids

    def test_where_combines_with_node_type(self, mg) -> None:
        refs = list_candidates(
            mg,
            role="lexicon",
            node_type="Lemma",
            where=lambda node: node.value.startswith("car"),
        )
        assert len(refs) == 1
        assert refs[0].node_id == LEX_LEMMA_CAR


class TestEmptyRoleGraph:
    def test_role_with_no_matching_graph_returns_empty(self, mg) -> None:
        # `memories` role has no graph in the corpus.
        refs = list_candidates(mg, role="memories")
        assert refs == []
