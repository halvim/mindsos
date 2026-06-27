"""FAITHFUL real-data diagnostic — run our perception on the RAW marks of a
real Bongard-LOGO panel (NVlabs `00-rectangle_vs_circle`), binarize-only, no
morphological fabrication (PLAN real-data diagnostic).

The question (Henrique): how does our system actually recognize the panel, whose
contours are drawn as trails of small triangle/circle GLYPHs + solid arcs? This
test individuates the raw foreground into connected components (what our
`parse_scene` does) and reports, per mark, what our atoms deduce —
`solve(polygon_k)` / `abstain(reason)` — plus the mark's pixel size.

Expected finding (not asserted as success, it IS the limitation): our perception
(vertex/segment/angle → polygon, closed-stroke gate, ~44-60px regime) sees the
local marks or abstains on them; it has NO perception of how the marks ARRANGE
into the enclosing rectangle/circle. So a panel shatters into ~15-23 marks and
the gestalt shape is never formed. This is the grounded wall — no shape is
fabricated by scipy; the report is what OUR system earns from real pixels.
"""

from __future__ import annotations

from collections import Counter

import pytest

from bongard.control import build_solver
from bongard.ingest import load_problem
from bongard.render import Sample
from bongard.scene import connected_components
from bongard.shapes import register_shapes


@pytest.fixture(scope="module")
def solver():
    s = build_solver()
    register_shapes(s.cl, s.session)
    return s


def _marks(solver, img):
    """Per connected component: (size_px, 'solve:<type>' | 'abstain:<reason>').

    Guarded: raw panels contain 1-2px specks our synthetic scenes never make,
    so a degenerate perceive is recorded as an outcome, not a crash."""
    out = []
    for sub in connected_components(img):
        try:
            v = solver.perceive(Sample(name="m", pixels=sub, truth_vertices=None,
                                       expect="", reason=""))
            if v.solved and v.shape is not None:
                out.append((len(sub.fg), f"solve:{v.shape.polygon_type}"))
            else:
                out.append((len(sub.fg), f"abstain:{v.reason}"))
        except Exception as e:
            out.append((len(sub.fg), f"error:{type(e).__name__}"))
    return out


def _report(solver, panels, label):
    print(f"\n=== {label} (raw marks, per panel) ===")
    n_components = 0
    verdicts = Counter()
    gestalt_solves = 0   # a panel-spanning solved shape (>400px) = a real gestalt
    for i, img in enumerate(panels):
        marks = _marks(solver, img)
        n_components += len(marks)
        verdicts.update(v for _, v in marks)
        gestalt_solves += sum(1 for sz, v in marks if v.startswith("solve") and sz > 400)
        summ = Counter(v for _, v in marks)
        print(f"  panel{i}: {len(marks)} marks -> {dict(summ)}")
    print(f"  TOTAL {label}: {n_components} marks, verdicts={dict(verdicts)}, gestalt_solves={gestalt_solves}")
    return n_components, verdicts, gestalt_solves


def test_raw_marks_no_gestalt(solver):
    prob = load_problem("rectangle_vs_circle")
    poly_n, poly_v, poly_gestalt = _report(solver, prob["1"], "rectangle-side")
    curve_n, curve_v, curve_gestalt = _report(solver, prob["0"], "circle-side")

    # 1. raw panels SHATTER — our individuation sees many marks, not one shape.
    assert poly_n >= 7 * 3 and curve_n >= 7 * 3, (poly_n, curve_n)
    # 2. the GESTALT is never formed — no panel-spanning shape is solved on
    #    either side. Our system has no arrangement perception (the wall).
    assert poly_gestalt == 0 and curve_gestalt == 0, (poly_gestalt, curve_gestalt)
