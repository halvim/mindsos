"""Task 2 gate — synthetic renderer + abstain-negative fixtures.

Pure-Python (no core dependency). Asserts the build/calibration shapes
render with the right oracle vertex counts and that the negatives carry
the gate they should trip.
"""

from __future__ import annotations

import pytest

from bongard import render as R


def test_clean_polygons_have_oracle_vertices():
    for s, n in [(R.triangle(), 3), (R.square(), 4), (R.pentagon(), 5)]:
        assert s.expect == "solve"
        assert s.truth_vertices is not None and len(s.truth_vertices) == n
        assert len(s.pixels.fg) > 0


def test_calibration_seed_is_the_triangle():
    seed = R.calibration_seed()
    assert seed.name == "triangle"
    assert len(seed.truth_vertices) == 3


def test_negatives_declare_their_gate():
    neg = {s.name: s for s in [R.circle(), R.open_strokes(), R.near_miss_polygon()]}
    assert neg["circle"].expect == "abstain" and neg["circle"].reason == "fit"
    assert neg["open_strokes"].reason == "structure"
    assert neg["near_miss"].reason == "structure"
    for s in neg.values():
        assert s.truth_vertices is None


def test_build_samples_covers_positives_and_negatives():
    samples = R.build_samples()
    solves = [s for s in samples if s.expect == "solve"]
    abstains = [s for s in samples if s.expect == "abstain"]
    assert len(solves) == 3 and len(abstains) == 4
    # every sample renders some foreground
    assert all(len(s.pixels.fg) > 0 for s in samples)


def test_nvlabs_smoke_absent_returns_empty():
    # Dataset not vendored by default; loader must degrade gracefully.
    assert R.load_nvlabs_smoke() == []
