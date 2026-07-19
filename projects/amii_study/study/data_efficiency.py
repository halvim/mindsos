"""Data-efficiency curve (axis A1): labels-to-competence for a target concept.

For each label budget B, train a FRESH arm on B positives of the target concept
(+ B clean negatives) and measure per-class F1 on the concept's frozen test.
Arm-agnostic. A method that reuses learned primitives (MindsOS) should reach
competence on a held-out combination at a far smaller B than a from-scratch
learner — that leftward shift is the A1 story (and, on held-out combos, A4).
"""
from __future__ import annotations

import numpy as np

from .generator import (
    ALL_CLASSES,
    TEST_SNRS_DB,
    TRAIN_SNRS_DB,
    SignalConfig,
    generate_event,
    multihot,
)
from .metrics import labels_to_competence, per_class_f1
from .stream import CLEAN


def _balanced_set(concept, n, snrs, seed, cfg):
    rng = np.random.default_rng(seed)
    X, Y = [], []
    for present in [frozenset(concept)] * n + [CLEAN] * n:
        snr = float(rng.choice(snrs))
        sig, label = generate_event(present, cfg, rng, snr)
        X.append(sig)
        Y.append(multihot(label))
    return np.asarray(X), np.asarray(Y)


def concept_efficiency_curve(make_arm, target, budgets, *, n_test=96, threshold=0.95, seed=0, cfg=None):
    """``make_arm(seed)`` -> fresh arm. Returns budgets, per-budget mean F1 over
    the target's classes, and labels-to-competence."""
    cfg = cfg or SignalConfig()
    Xte, Yte = _balanced_set(target, n_test, TEST_SNRS_DB, seed=808_000 + seed, cfg=cfg)
    target_idx = [ALL_CLASSES.index(c) for c in target]

    f1s = []
    for b in budgets:
        arm = make_arm(seed)
        Xtr, Ytr = _balanced_set(target, b, TRAIN_SNRS_DB, seed=seed * 7 + b, cfg=cfg)
        arm.fit(Xtr, Ytr)
        f1 = per_class_f1(Yte, arm.predict(Xte))
        f1s.append(float(np.mean(f1[target_idx])))

    return {
        "target": "+".join(sorted(target)),
        "budgets": list(budgets),
        "f1": f1s,
        "labels_to_competence": labels_to_competence(budgets, f1s, threshold),
    }
