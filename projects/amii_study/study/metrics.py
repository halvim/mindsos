"""Evaluation metrics — eval rig, part 2.

Arm-agnostic scoring against the frozen test, mapped to the study axes:

* per-class F1 + the competence threshold (target competence, prereg §6);
* Backward Transfer (BWT) — axis A3, no-forgetting;
* Forward Transfer (FWT) — axis A4, transfer;
* average accuracy; and labels-to-competence for the A1 efficiency curve.

``R`` is the forgetting matrix: ``R[i, j]`` = F1 on concept ``j``'s test
subset after training increment ``i`` (rows = increments in stream order,
cols = concepts, both square over the taught stream).
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np


def per_class_f1(y_true, y_pred, zero_division: float = 0.0) -> np.ndarray:
    """Multi-label F1 per class: 2·TP / (2·TP + FP + FN), column-wise."""
    y_true = np.asarray(y_true).astype(bool)
    y_pred = np.asarray(y_pred).astype(bool)
    tp = np.sum(y_true & y_pred, axis=0)
    fp = np.sum(~y_true & y_pred, axis=0)
    fn = np.sum(y_true & ~y_pred, axis=0)
    denom = 2 * tp + fp + fn
    return np.where(denom == 0, zero_division, (2 * tp) / np.where(denom == 0, 1, denom))


def average_accuracy(R) -> float:
    """Mean F1 across concepts after the final increment (last row of R)."""
    return float(np.mean(np.asarray(R, dtype=float)[-1]))


def backward_transfer(R) -> float:
    """Mean change on earlier concepts after learning all of them.

    Negative = forgetting (axis A3 kill side). ``R[i, i]`` is F1 on concept
    ``i`` right after learning it; ``R[-1, i]`` is F1 on it at the end.
    """
    R = np.asarray(R, dtype=float)
    T = R.shape[0]
    return float(np.mean([R[-1, i] - R[i, i] for i in range(T - 1)]))


def forward_transfer(R, baseline: float | Sequence[float] = 0.0) -> float:
    """Mean zero-shot F1 on concept ``i`` *before* training it, minus baseline.

    Positive = having the earlier primitives transfers to the new concept
    (axis A4). ``R[i-1, i]`` is performance on concept ``i`` before its own
    increment.
    """
    R = np.asarray(R, dtype=float)
    T = R.shape[0]
    base = np.full(T, baseline, float) if np.isscalar(baseline) else np.asarray(baseline, float)
    return float(np.mean([R[i - 1, i] - base[i] for i in range(1, T)]))


def labels_to_competence(labels, f1s, threshold: float = 0.95) -> Optional[int]:
    """Smallest label count at which F1 first reaches ``threshold`` (else None)."""
    labels = np.asarray(labels)
    f1s = np.asarray(f1s)
    order = np.argsort(labels)
    for n, f in zip(labels[order], f1s[order]):
        if f >= threshold:
            return int(n)
    return None
