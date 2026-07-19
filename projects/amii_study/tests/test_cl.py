"""Mechanics smoke for the CL arms (needs torch; skipped where torch is absent)."""
import numpy as np
import pytest

pytest.importorskip("torch")

from study.baselines.cl import EWCArm, LwFArm, ReplayArm
from study.generator import ALL_CLASSES
from study.runner import run_stream

NC = len(ALL_CLASSES)


@pytest.mark.parametrize("make", [
    lambda: ReplayArm(epochs=2, seed=0),
    lambda: EWCArm(epochs=2, seed=0),
    lambda: LwFArm(epochs=2, seed=0),
])
def test_cl_arm_runs_through_stream(make):
    res = run_stream(make(), n_train=8, n_test=6, seed=0)
    assert res["R"].shape[1] == NC
    assert np.all((res["R"] >= 0.0) & (res["R"] <= 1.0))
    assert -1.0 <= res["bwt_primitives"] <= 1.0


def test_cl_arms_are_deterministic():
    a = run_stream(ReplayArm(epochs=2, seed=7), n_train=8, n_test=6, seed=0)
    b = run_stream(ReplayArm(epochs=2, seed=7), n_train=8, n_test=6, seed=0)
    assert np.array_equal(a["R"], b["R"])
