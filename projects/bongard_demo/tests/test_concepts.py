"""m4 — concept search + held-out verify (in-memory, sandbox-fast).

Exercises the full m4 vertical (PLAN m4 design block, D-M4-*): a declarative
``ConceptCandidate`` evaluated through the real ``evaluate_concept`` L3
predicate via ``cl.invoke``, and the demo-control ``search_and_verify`` loop
selecting from the CLOSED template library + verifying on a disjoint-seed
held-out batch. Both CONCLUDE paths (the two shipped problems) and both
ABSTAIN paths (ambiguous / no_consistent) are covered. No ``mindsos_*``
edits, no FalkorDB.
"""

from __future__ import annotations

import random

from bongard.control import Solver
from bongard import render
from bongard.scene import parse_scene, scene_relations
from bongard.ontology import SCENE, RELATION_SET
from bongard.concepts import (ConceptCandidate, CONCEPT_CANDIDATE, CONCEPT_VERDICT,
                              TEMPLATE_ALL_SAME, TEMPLATE_COUNT_EQ)
from bongard.problem import (ALL_SAME_PROBLEM, COUNT_EQ_PROBLEM, Problem,
                             _render, _not_all_same, TYPE_NS)
from bongard.search import search_and_verify


def _solver() -> Solver:
    return Solver("bongard-m4")


def _verdict(s, scene, rels, cand) -> bool:
    r = s.cl.invoke(s.concept_iri,
                    {SCENE.iri: scene, RELATION_SET.iri: rels, CONCEPT_CANDIDATE.iri: cand},
                    session=s.session)
    assert r.success, r.error
    return r.outputs[CONCEPT_VERDICT.iri]


# ── evaluate_concept predicate through real cl.invoke ──────────────────

def test_all_same_verdict_through_invoke():
    s = _solver()
    sc = parse_scene(s, render.scene_two_squares())
    rels = scene_relations(s, sc)
    assert _verdict(s, sc, rels, ConceptCandidate(TEMPLATE_ALL_SAME)) is True


def test_all_same_false_on_mixed_scene():
    s = _solver()
    sc = parse_scene(s, render.scene_square_triangle())
    rels = scene_relations(s, sc)
    assert _verdict(s, sc, rels, ConceptCandidate(TEMPLATE_ALL_SAME)) is False


def test_count_eq_verdict_through_invoke():
    s = _solver()
    sc = parse_scene(s, render.scene_three_mixed())   # 3 figures
    rels = scene_relations(s, sc)
    assert _verdict(s, sc, rels, ConceptCandidate(TEMPLATE_COUNT_EQ, (3,))) is True
    assert _verdict(s, sc, rels, ConceptCandidate(TEMPLATE_COUNT_EQ, (2,))) is False


# ── search + held-out verify: the two shipped problems CONCLUDE ────────

def test_all_same_problem_concludes_all_same():
    r = search_and_verify(_solver(), ALL_SAME_PROBLEM, seed=0)
    assert r.concluded, r.detail
    assert r.concept.template == TEMPLATE_ALL_SAME


def test_count_eq_problem_concludes_count_eq_3():
    r = search_and_verify(_solver(), COUNT_EQ_PROBLEM, seed=0)
    assert r.concluded, r.detail
    assert r.concept.template == TEMPLATE_COUNT_EQ
    assert r.concept.params == (3,)


# ── ABSTAIN paths ──────────────────────────────────────────────────────

def _gen_ambiguous(label: bool, rng: random.Random):
    """Positives = 3 same-type figures; negatives = 2 mixed figures.
    Both COUNT_EQ(3) and ALL_SAME_SHAPE separate these — and no scene
    distinguishes them → ambiguous."""
    if label:
        t = rng.choice(TYPE_NS)
        return _render([t] * 3)
    return _render(_not_all_same([rng.choice(TYPE_NS) for _ in range(2)], rng))


def _gen_constant(label: bool, rng: random.Random):
    """Every scene identical regardless of label → no template can separate."""
    return _render([3, 4])


def test_ambiguous_problem_abstains():
    prob = Problem("ambiguous", ConceptCandidate(TEMPLATE_COUNT_EQ, (3,)), _gen_ambiguous)
    r = search_and_verify(_solver(), prob, seed=0)
    assert r.status == "abstain"
    assert r.reason == "ambiguous"
    templates = {c.template for c in r.survivors}
    assert TEMPLATE_ALL_SAME in templates and TEMPLATE_COUNT_EQ in templates


def test_no_consistent_problem_abstains():
    prob = Problem("constant", ConceptCandidate(TEMPLATE_ALL_SAME), _gen_constant)
    r = search_and_verify(_solver(), prob, seed=0)
    assert r.status == "abstain"
    assert r.reason == "no_consistent"
