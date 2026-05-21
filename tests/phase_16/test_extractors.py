"""Phase 16 PB-B2 — per-role feature extractor outputs.

Three extractors (ontology / lexicon / concepts) — exercised against
the deterministic Phase 16 corpus. ADR-0144 §Heuristic feature set:
``(frame_elements, synonyms, parents)``.
"""

from __future__ import annotations

import pytest

from mindsos_admin.similarity import (
    _empty_features,
    _extract_concepts,
    _extract_features,
    _extract_lexicon,
    _extract_ontology,
)
from tests.phase_16.fixtures.build_corpus import (
    CON_FE_AGENT,
    CON_FE_THEME,
    CON_FRAME_EVENT,
    CON_FRAME_MOTION,
    LEX_LEMMA_CAR,
    LEX_SYNSET_CAR,
    LEX_SYNSET_VEHICLE,
    ONT_CLASS_ENT,
    ONT_CLASS_PHYS,
    build_corpus,
)


@pytest.fixture
def mg():
    return build_corpus()


def _get(mg, role, node_id):
    graph = next(g for g in mg.graphs.values() if g.role == role)
    return graph, graph.nodes[node_id]


class TestOntologyExtractor:
    def test_subclass_of_targets_become_parents(self, mg) -> None:
        graph, node = _get(mg, "ontology", ONT_CLASS_PHYS)
        feats = _extract_ontology(graph, node)
        assert feats["parents"] == frozenset({ONT_CLASS_ENT})

    def test_synonyms_and_frame_elements_are_empty(self, mg) -> None:
        graph, node = _get(mg, "ontology", ONT_CLASS_PHYS)
        feats = _extract_ontology(graph, node)
        assert feats["synonyms"] == frozenset()
        assert feats["frame_elements"] == frozenset()

    def test_leaf_class_has_no_parents(self, mg) -> None:
        graph, node = _get(mg, "ontology", ONT_CLASS_ENT)
        feats = _extract_ontology(graph, node)
        assert feats["parents"] == frozenset()


class TestLexiconExtractor:
    def test_hypernym_of_targets_become_parents(self, mg) -> None:
        graph, node = _get(mg, "lexicon", LEX_SYNSET_CAR)
        feats = _extract_lexicon(graph, node)
        assert feats["parents"] == frozenset({LEX_SYNSET_VEHICLE})

    def test_in_synset_targets_become_synonyms(self, mg) -> None:
        graph, node = _get(mg, "lexicon", LEX_LEMMA_CAR)
        feats = _extract_lexicon(graph, node)
        assert feats["synonyms"] == frozenset({LEX_SYNSET_CAR})

    def test_frame_elements_empty(self, mg) -> None:
        graph, node = _get(mg, "lexicon", LEX_SYNSET_CAR)
        feats = _extract_lexicon(graph, node)
        assert feats["frame_elements"] == frozenset()


class TestConceptsExtractor:
    def test_inherits_from_targets_become_parents(self, mg) -> None:
        graph, node = _get(mg, "concepts", CON_FRAME_MOTION)
        feats = _extract_concepts(graph, node)
        assert feats["parents"] == frozenset({CON_FRAME_EVENT})

    def test_has_fe_targets_become_frame_elements(self, mg) -> None:
        graph, node = _get(mg, "concepts", CON_FRAME_MOTION)
        feats = _extract_concepts(graph, node)
        assert feats["frame_elements"] == frozenset({CON_FE_AGENT, CON_FE_THEME})

    def test_synonyms_empty(self, mg) -> None:
        graph, node = _get(mg, "concepts", CON_FRAME_MOTION)
        feats = _extract_concepts(graph, node)
        assert feats["synonyms"] == frozenset()


class TestExtractFeaturesDispatch:
    def test_unknown_role_returns_empty(self, mg) -> None:
        # Per PB-B2 bounded scope: roles outside ontology/lexicon/concepts
        # return empty features. Empty-pair exclusion handles the rest.
        graph, node = _get(mg, "ontology", ONT_CLASS_PHYS)
        feats = _extract_features(graph, node, role="memories")
        assert feats == _empty_features()

    def test_alignment_prefix_returns_empty(self, mg) -> None:
        graph, node = _get(mg, "ontology", ONT_CLASS_PHYS)
        feats = _extract_features(graph, node, role="alignment:foo:bar")
        assert feats == _empty_features()

    def test_dispatch_routes_to_ontology(self, mg) -> None:
        graph, node = _get(mg, "ontology", ONT_CLASS_PHYS)
        feats_direct = _extract_ontology(graph, node)
        feats_via_dispatch = _extract_features(graph, node, role="ontology")
        assert feats_direct == feats_via_dispatch
