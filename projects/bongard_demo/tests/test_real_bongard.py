"""Real-data limitation test — run our perception on REAL Bongard-LOGO panels
(NVlabs), ingested via the morphological glyph-bridge (PLAN real-data
diagnostic). Two contrasting problems:

  * rectangle_vs_circle — our system SEPARATES the two sides by PARSE-vs-ABSTAIN:
    rectangles parse (polygon), circles hit the existing fit-gate abstain. A
    real Bongard problem resolved by the abstain SIGNAL (on-philosophy).
  * convex_vs_concave — the vocabulary CEILING: both sides are curves our
    perception abstains on (and we hold no convexity atom), so our system does
    NOT separate it. Honest negative.

Bounded claim: ONE favorable real problem via parse-vs-abstain, NOT a general
Bongard-LOGO solver. The panels are real (ingested from the dataset); only the
stroke-bridge is demo-side and it never decides the label.
"""

from __future__ import annotations

import pytest

from bongard.control import build_solver
from bongard.ingest import load_problem
from bongard.scene import parse_scene
from bongard.shapes import register_shapes


@pytest.fixture(scope="module")
def solver():
    s = build_solver()
    register_shapes(s.cl, s.session)
    return s


def _panel(solver, img):
    """(n_solved_shapes, polygon_types, abstain_reasons) for one panel."""
    sc = parse_scene(solver, img)
    types = [s.polygon_type for s in sc.shapes]
    reasons = [v.reason for v in sc.figures if not v.solved]
    return sc.n_shapes, types, reasons


def _side(solver, panels):
    return [_panel(solver, im) for im in panels]


def test_rectangle_vs_circle_separates(solver):
    prob = load_problem("rectangle_vs_circle")
    curve = _side(solver, prob["0"])   # circles
    poly = _side(solver, prob["1"])    # rectangles
    poly_solves = sum(r[0] for r in poly)
    curve_solves = sum(r[0] for r in curve)
    print("\n[rect_vs_circle] polygon-side (n,types,reasons):", poly)
    print("[rect_vs_circle] curve-side  (n,types,reasons):", curve)
    # circles must abstain (the fit gate is the circle detector)
    assert curve_solves == 0, f"circles should abstain, got {curve_solves} solved: {curve}"
    # rectangles must parse at least once (else: ingestion/calibration gap = finding)
    assert poly_solves >= 1, f"no rectangle parsed (ingestion/calibration gap): {poly}"
    # the separation: parse-vs-abstain tells the two sides apart
    assert poly_solves > curve_solves


def test_convex_vs_concave_is_ceiling(solver):
    prob = load_problem("convex_vs_concave")
    s0 = _side(solver, prob["0"])
    s1 = _side(solver, prob["1"])
    n0 = sum(r[0] for r in s0)
    n1 = sum(r[0] for r in s1)
    print("\n[convex_vs_concave] side0 (n,types,reasons):", s0)
    print("[convex_vs_concave] side1 (n,types,reasons):", s1)
    # vocabulary ceiling: curves on both sides → our perception abstains on
    # both, so parse-vs-abstain gives NO separation (we cannot tell convex from
    # concave). Both sides should produce no parsed polygon.
    assert n0 == 0 and n1 == 0, f"expected the ceiling (no parse either side); got s0={n0} s1={n1}"
