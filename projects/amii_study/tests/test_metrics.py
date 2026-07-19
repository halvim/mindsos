"""Validation for the metrics, against hand-computed values."""
import numpy as np
import pytest

from study.metrics import (
    average_accuracy,
    backward_transfer,
    forward_transfer,
    labels_to_competence,
    per_class_f1,
    select_thresholds,
)


def test_per_class_f1_perfect_and_wrong():
    y = np.array([[1, 0], [0, 1], [1, 1]])
    assert np.allclose(per_class_f1(y, y), [1.0, 1.0])           # perfect
    assert np.allclose(per_class_f1(y, 1 - y), [0.0, 0.0])       # all wrong


def test_per_class_f1_partial():
    y_true = np.array([[1], [1], [0], [0]])
    y_pred = np.array([[1], [0], [1], [0]])  # tp=1, fp=1, fn=1 -> F1 = 2/(2+1+1)=0.5
    assert per_class_f1(y_true, y_pred)[0] == 0.5


def test_absent_class_is_zero_division_default():
    y_true = np.array([[0], [0]])
    y_pred = np.array([[0], [0]])            # nothing present or predicted
    assert per_class_f1(y_true, y_pred)[0] == 0.0


def test_backward_transfer_detects_forgetting():
    R = np.array([[1.0, 0.0, 0.0],
                  [0.9, 1.0, 0.0],
                  [0.7, 0.8, 1.0]])          # end row drops on concepts 0,1
    assert backward_transfer(R) == np.mean([0.7 - 1.0, 0.8 - 1.0])  # -0.25


def test_forward_transfer_detects_transfer():
    R = np.array([[1.0, 0.3, 0.0],
                  [0.0, 1.0, 0.4],
                  [0.0, 0.0, 1.0]])          # zero-shot 0.3 on c1, 0.4 on c2
    assert forward_transfer(R) == np.mean([0.3, 0.4])


def test_average_accuracy_is_last_row_mean():
    R = np.array([[1.0, 0.0], [0.8, 0.9]])
    assert average_accuracy(R) == pytest.approx(0.85)


def test_labels_to_competence():
    assert labels_to_competence([10, 20, 40], [0.5, 0.9, 0.97], 0.95) == 40
    assert labels_to_competence([10, 20], [0.5, 0.9], 0.95) is None


def test_select_thresholds_beats_fixed_half():
    # class where positives score 0.6 and negatives 0.55: a 0.5 threshold calls
    # everything positive (poor), but a dev-tuned threshold separates them.
    proba = np.array([[0.60], [0.60], [0.55], [0.55]])
    y = np.array([[1], [1], [0], [0]])
    th = select_thresholds(proba, y)
    pred_tuned = (proba[:, 0] >= th[0]).astype(int)
    assert np.array_equal(pred_tuned, [1, 1, 0, 0])   # perfectly separated
    assert 0.55 < th[0] <= 0.60
