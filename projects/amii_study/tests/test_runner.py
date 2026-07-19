"""Harness mechanics for the hardened runner — torch-free (a constant arm).

Validates: the joint test carries confusable negatives; R has the right shape
and range; BWT/composition/notch wire up; and a trivial arm gives the exact
hand-computable composition outcome.
"""
import numpy as np

from study.generator import ALL_CLASSES, SignalConfig
from study.runner import build_joint_test, run_stream
from study.stream import CONCEPT_STREAM

IDX = {c: i for i, c in enumerate(ALL_CLASSES)}
NC = len(ALL_CLASSES)


class ConstantArm:
    def __init__(self, vec):
        self.vec = np.asarray(vec, dtype=int)

    def fit(self, X, Y):
        return self

    def predict(self, X):
        return np.tile(self.vec, (len(X), 1))


def test_joint_test_has_confusable_negatives():
    X, Y = build_joint_test(4, seed=1, cfg=SignalConfig())
    # among examples WITHOUT sag, some still carry another disturbance
    neg = Y[Y[:, IDX["sag"]] == 0]
    others = [IDX[c] for c in ("swell", "harmonic", "flicker", "transient", "notch")]
    assert neg[:, others].sum() > 0


def test_run_stream_shape_and_range():
    res = run_stream(ConstantArm(np.zeros(NC)), n_train=4, n_test=4, seed=0)
    assert res["R"].shape == (len(CONCEPT_STREAM), NC)
    assert np.all((res["R"] >= 0.0) & (res["R"] <= 1.0))
    assert -1.0 <= res["bwt_primitives"] <= 1.0
    assert set(res["heldout_composition"]) == {"sag+transient", "swell+transient"}


def test_zero_arm_detects_nothing():
    res = run_stream(ConstantArm(np.zeros(NC)), n_train=4, n_test=4, seed=0)
    assert res["notch_f1"] == 0.0
    assert all(v == 0.0 for v in res["heldout_composition"].values())


def test_all_ones_arm_detects_every_composition():
    res = run_stream(ConstantArm(np.ones(NC)), n_train=4, n_test=4, seed=0)
    assert all(v == 1.0 for v in res["heldout_composition"].values())
