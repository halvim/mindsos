"""Phase 16 — `compute_similarity` end-to-end behaviour.

Covers PB-J3 (NodeType partition) / PB-K2 (cross-mg target) / PB-L1
(outer-mean renormalization) / PB-M2 (inter-candidate findings) /
PB-T2 (6-decimal rounding) / PB-G2 (empty-pair inner exclusion) +
:class:`EmptyComparisonError` per ADR-0144 §amendment-2.
"""

from __future__ import annotations

import pytest

from mindsos_admin import (
    CandidateRef,
    EmptyComparisonError,
    SimilarityReport,
    compute_similarity,
    list_candidates,
)
from mindsos_core import Graph, Metagraph
from tests.phase_16.fixtures.build_corpus import (
    CON_FRAME_MOTION,
    CON_FRAME_MOTION_NEAR,
    LEX_SYNSET_AUTO,
    LEX_SYNSET_CAR,
    ONT_CLASS_PHYS,
    ONT_CLASS_PHYS_NEAR,
    build_corpus,
)


@pytest.fixture
def mg():
    return build_corpus()


# ── §1 Report-shape + determinism ──────────────────────────────────────


class TestReportShape:
    def test_returns_similarity_report(self, mg) -> None:
        candidates = list_candidates(mg, role="ontology")
        report = compute_similarity(mg, candidates, role="ontology")
        assert isinstance(report, SimilarityReport)

    def test_report_id_is_64_char_hex(self, mg) -> None:
        candidates = list_candidates(mg, role="ontology")
        report = compute_similarity(mg, candidates, role="ontology")
        assert len(report.report_id) == 64
        int(report.report_id, 16)

    def test_report_id_deterministic(self, mg) -> None:
        candidates = list_candidates(mg, role="ontology")
        r1 = compute_similarity(mg, candidates, role="ontology")
        r2 = compute_similarity(mg, candidates, role="ontology")
        assert r1.report_id == r2.report_id

    def test_findings_sorted_by_candidate_then_score_desc(self, mg) -> None:
        candidates = list_candidates(mg, role="ontology")
        report = compute_similarity(mg, candidates, role="ontology")
        sort_key = [(f.candidate_id, -f.score, f.matched_id) for f in report.findings]
        assert sort_key == sorted(sort_key)

    def test_threshold_defaults_match_adr_0144(self, mg) -> None:
        candidates = list_candidates(mg, role="ontology")
        report = compute_similarity(mg, candidates, role="ontology")
        assert report.threshold_blocking == 0.85
        assert report.threshold_review == 0.5


# ── §2 PB-T2 — 6-decimal rounding ──────────────────────────────────────


class TestSixDecimalRounding:
    def test_finding_score_is_six_decimals(self, mg) -> None:
        candidates = list_candidates(mg, role="ontology")
        report = compute_similarity(mg, candidates, role="ontology")
        for f in report.findings:
            # Float values rounded to 6 decimals via `round(x, 6)`.
            assert f.score == round(f.score, 6)


# ── §3 PB-M2 — inter-candidate findings flagged ────────────────────────


class TestInterCandidate:
    def test_close_ontology_pair_flagged_as_inter_candidate(self, mg) -> None:
        # The corpus has PhysicalObject vs PhysicalObjects — both ontology
        # Classes; included as findings of each other.
        cand_phys = CandidateRef(
            node_id=ONT_CLASS_PHYS, role="ontology", node_type="Class"
        )
        cand_phys_near = CandidateRef(
            node_id=ONT_CLASS_PHYS_NEAR, role="ontology", node_type="Class"
        )
        report = compute_similarity(
            mg, [cand_phys, cand_phys_near], role="ontology"
        )
        # At least one finding should have matched_is_candidate=True.
        inter = [f for f in report.findings if f.matched_is_candidate]
        assert inter, (
            "Inter-candidate findings missing — PB-M2 contract violated."
        )

    def test_self_comparison_never_in_findings(self, mg) -> None:
        cand = CandidateRef(
            node_id=ONT_CLASS_PHYS, role="ontology", node_type="Class"
        )
        report = compute_similarity(mg, [cand], role="ontology")
        for f in report.findings:
            assert f.candidate_id != f.matched_id, (
                "Self-comparison leaked into findings — PB-M2 violated."
            )


# ── §4 PB-J3 — NodeType partition ──────────────────────────────────────


class TestNodeTypePartition:
    def test_findings_pair_same_nodetype_only(self, mg) -> None:
        # Lexicon has Synset + Lemma — they should never cross-pair.
        candidates = list_candidates(mg, role="lexicon")
        report = compute_similarity(mg, candidates, role="lexicon")
        for f in report.findings:
            assert f.candidate_node_type == f.matched_node_type, (
                "Cross-NodeType finding emitted — PB-J3 partition violated."
            )


# ── §5 PB-K2 — cross-mg target ─────────────────────────────────────────


class TestCrossMg:
    def test_target_mg_default_intra_mg(self, mg) -> None:
        candidates = list_candidates(mg, role="ontology")
        intra = compute_similarity(mg, candidates, role="ontology")
        cross = compute_similarity(
            mg, candidates, role="ontology", target_mg=mg
        )
        # target_mg=mg should be equivalent to target_mg=None.
        assert intra.report_id == cross.report_id
        assert len(intra.findings) == len(cross.findings)

    def test_distinct_target_mg_changes_report(self, mg) -> None:
        candidates = list_candidates(mg, role="ontology")
        # Build a second mg with one extra ontology node to differentiate.
        mg2 = build_corpus()
        ont2 = next(g for g in mg2.graphs.values() if g.role == "ontology")
        ont2.add_node(
            value="ExtraClass",
            type_name="Class",
            node_id="dolce:Class:Extra",
        )
        report_self = compute_similarity(mg, candidates, role="ontology")
        report_cross = compute_similarity(
            mg, candidates, role="ontology", target_mg=mg2
        )
        # report_id should differ — different target_mg content.
        assert report_self.report_id != report_cross.report_id


# ── §6 PB-L1 — outer-mean renormalization + EmptyComparisonError ───────


class TestRenormalization:
    def test_breakdown_omits_undefined_components(self, mg) -> None:
        # Ontology Classes have no synonyms or frame-elements (extractor
        # returns those empty); breakdown should reflect this.
        candidates = list_candidates(mg, role="ontology")
        report = compute_similarity(mg, candidates, role="ontology")
        for f in report.findings:
            # All findings include a `lev` component (IRI tails are
            # non-empty); structural may or may not be present depending
            # on parent set overlap; reference component is absent
            # (corpus has no XRef rows and no ref:<role> properties).
            assert "lev" in f.breakdown
            assert "ref" not in f.breakdown  # ref Jaccard undefined here.


class TestEmptyComparisonError:
    def test_raises_when_all_components_undefined(self) -> None:
        # Construct a degenerate mg: two nodes with empty IRI tails
        # (no `:` separator means tail is the whole string — to truly
        # force undefined Lev, we need empty string nodes, which
        # requires bypassing Node validation. Instead, the realistic
        # test uses a custom mg with all-empty extractor features +
        # IRIs that produce empty Lev under both being empty.
        #
        # Simpler approach: construct a custom test mg where neither
        # node has Lev, struct, OR ref signal. Easiest: use empty
        # IRI tails by skipping the colon — but `_iri_tail` returns
        # the whole IRI as tail when no `:`. To force Lev=None we'd
        # need empty strings.
        #
        # We mock the path via a direct private-helper call instead.
        from mindsos_admin.similarity import _score_pair
        from mindsos_core import Graph
        from mindsos_core.models.node import Node

        # Build two nodes whose IRI tails are empty. Node() permits
        # any string for node_id, including the empty string at
        # construction (constructor doesn't validate).
        a = Node(value="a", type_name="X", node_id="")
        b = Node(value="b", type_name="X", node_id="")
        # No containing graph → struct undefined; no properties → ref
        # undefined; empty tails → Lev undefined. All three components
        # undefined → EmptyComparisonError.
        with pytest.raises(EmptyComparisonError):
            _score_pair(
                source_graph=None,
                source_node=a,
                target_graph=None,
                target_node=b,
            )
