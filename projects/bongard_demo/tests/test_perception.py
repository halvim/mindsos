"""Task 8 — milestone-1 perception verification (the §11 guard).

Pass set defends against the easy-20% trap: positives solve with the right
parse; every negative abstains at the correct gate; generalization holds
on held-out (freshly generated) polygons parsed prior-free; and the
geometric structure gate + R=1 re-segment branch is exercised directly
(it is the non-convex seam the convex tracer otherwise subsumes).
"""

from __future__ import annotations

import pytest

from bongard import render as R
from bongard.control import build_solver, Solver
from bongard.geometry import Candidate, segments_from_vertices
from bongard.calibration import calibrate


@pytest.fixture(scope="module")
def solver():
    return build_solver()


# ── positives: solve with the right parse ──────────────────────────────

@pytest.mark.parametrize("sample,n,ptype", [
    (R.triangle(), 3, "triangle"),
    (R.square(), 4, "quadrilateral"),
    (R.pentagon(), 5, "pentagon"),
])
def test_clean_polygons_solve(solver, sample, n, ptype):
    v = solver.perceive(sample)
    assert v.solved, v
    assert v.shape.polygon_type == ptype
    assert len(v.shape.vertices) == n
    assert v.shape.valid and v.shape.confidence > 0.9


# ── negatives: abstain at the correct gate ─────────────────────────────

@pytest.mark.parametrize("sample,reason", [
    (R.circle(), "fit"),            # smooth curve -> fit gate
    (R.open_strokes(), "structure"),  # 2 components -> topological gate
    (R.near_miss_polygon(), "structure"),  # open endpoint -> topological gate
    (R.bowtie(), "fit"),           # convex tracer routes self-intersection to fit
])
def test_negatives_abstain(solver, sample, reason):
    v = solver.perceive(sample)
    assert v.status == "abstain", v
    assert v.reason == reason, f"{sample.name}: {v.reason} != {reason}"


# ── generalization: held-out, prior-free (PLAN §3) ─────────────────────

@pytest.mark.parametrize("n", [3, 4, 5])
@pytest.mark.parametrize("cx,cy,r,rot", [
    (40.0, 70.0, 28.0, 0.3), (88.0, 50.0, 22.0, 1.1), (64.0, 64.0, 50.0, -2.0),
])
def test_generalizes_to_held_out_polygons(solver, n, cx, cy, r, rot):
    # Fresh polygons at unseen size/position/rotation, parsed prior-free.
    s = R.polygon_sample(f"g{n}", n, cx=cx, cy=cy, r=r, rot=rot)
    v = solver.perceive(s)
    assert v.solved, v
    assert len(v.shape.vertices) == n


def test_held_out_parsed_prior_free(solver):
    # F-seam firewall (G7): a ParsePrior may be passed but must not be
    # required, and (body deferred) must not change the held-out verdict.
    s = R.pentagon()
    base = solver.perceive(s)
    primed = solver.perceive(s, parse_prior={"expected_atoms": 99})
    assert base.solved and primed.solved
    assert len(base.shape.vertices) == len(primed.shape.vertices) == 5


# ── geometric structure gate + R=1 re-segment (non-convex seam) ────────

def _bowtie_candidate() -> Candidate:
    # Order 4 corners so the two diagonals cross -> a non-simple ring whose
    # edges still lie on straight lines (passes fit, fails simplicity).
    tl, br, tr, bl = (34.0, 34.0), (94.0, 94.0), (94.0, 34.0), (34.0, 94.0)
    verts = (tl, br, tr, bl)
    segs = tuple(segments_from_vertices(list(verts)))
    return Candidate(vertices=verts, segments=segs, rms=0.001,
                     max_resid=0.002, epsilon_frac=0.02)


def test_predicate_rejects_self_intersection(solver):
    shape = solver._verify(_bowtie_candidate())
    assert not shape.valid
    assert "simple_ok=False" in shape.detail


def test_resegment_branch_retries_then_abstains():
    # Drive step 5 directly: a solver whose segmentation always returns a
    # geometrically-invalid (self-intersecting) candidate. perceive() must
    # attempt the R=1 re-segment and then abstain(structure, resegmented).
    bad = _bowtie_candidate()

    class StuckSolver(Solver):
        def _segment(self, boundary, params):
            return bad

    s = StuckSolver()
    v = s.perceive(R.triangle())   # triangle pixels pass the topology gate
    assert v.status == "abstain" and v.reason == "structure"
    assert v.resegmented is True


# ── calibration ────────────────────────────────────────────────────────

def test_calibration_tau_in_range():
    p = calibrate()
    assert 0.006 <= p.tau_fit <= 0.03   # seed-derived, slack-padded, floored
    # curve discriminator (PLAN §10 D revision): per-edge fit + ε-persistence
    assert p.per_edge_tau <= 0.015
    assert 0.4 <= p.plateau_min_frac <= 0.7
