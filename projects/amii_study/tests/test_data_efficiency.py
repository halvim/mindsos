"""Data-efficiency sweep mechanics — torch-free (constant arm)."""
import numpy as np

from study.data_efficiency import concept_efficiency_curve
from study.generator import ALL_CLASSES

NC = len(ALL_CLASSES)


class ConstantArm:
    def __init__(self, vec):
        self.vec = np.asarray(vec, dtype=int)

    def fit(self, X, Y):
        return self

    def predict(self, X):
        return np.tile(self.vec, (len(X), 1))


def test_curve_shape_and_ltc():
    res = concept_efficiency_curve(lambda s: ConstantArm(np.zeros(NC)),
                                   {"sag"}, budgets=[4, 8, 16], n_test=8)
    assert res["budgets"] == [4, 8, 16]
    assert len(res["f1"]) == 3
    assert all(f == 0.0 for f in res["f1"])           # predicts nothing
    assert res["labels_to_competence"] is None


def test_all_ones_never_reaches_competence_on_balanced_test():
    # all-ones -> F1 = 2/3 on the concept class (false positives on clean); < 0.95
    res = concept_efficiency_curve(lambda s: ConstantArm(np.ones(NC)),
                                   {"sag"}, budgets=[4, 8], n_test=8)
    assert all(abs(f - 2 / 3) < 1e-9 for f in res["f1"])
    assert res["labels_to_competence"] is None
