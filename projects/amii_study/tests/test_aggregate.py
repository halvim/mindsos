"""Validation for multi-seed aggregation + the CI math (torch-free)."""
import numpy as np
import pytest

from study.aggregate import mean_ci, run_multiseed
from study.generator import ALL_CLASSES

NC = len(ALL_CLASSES)


class ConstantArm:
    def __init__(self, vec):
        self.vec = np.asarray(vec, dtype=int)

    def fit(self, X, Y):
        return self

    def predict(self, X):
        return np.tile(self.vec, (len(X), 1))


def test_mean_ci_known_values():
    # samples 1..5: mean 3, sd 1.5811, sem 0.7071, t(df=4)=2.776 -> +-1.963
    m, lo, hi = mean_ci([1, 2, 3, 4, 5])
    assert m == pytest.approx(3.0)
    assert (hi - lo) / 2 == pytest.approx(2.776 * (np.std([1, 2, 3, 4, 5], ddof=1) / np.sqrt(5)), rel=1e-3)


def test_mean_ci_single_sample_is_point():
    assert mean_ci([0.7]) == (0.7, 0.7, 0.7)


def test_run_multiseed_zero_variance_for_constant_arm():
    # a data-independent arm gives identical results every seed -> CI width 0
    res = run_multiseed(lambda s: ConstantArm(np.zeros(NC)), seeds=[0, 1, 2],
                        n_train=4, n_test=4)
    m, lo, hi = res["aggregate"]["bwt_primitives"]
    assert lo == pytest.approx(m) and hi == pytest.approx(m)
    assert len(res["runs"]) == 3
