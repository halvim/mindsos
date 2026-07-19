"""Incremental runner — eval rig driver (hardened).

Trains an *arm* through the concept stream one increment at a time and scores it
against a single **joint** frozen test whose negatives include other
disturbances (confusable negatives), so discrimination — not just
presence-vs-silence — is measured. Arm interface (duck-typed):

    arm.fit(X, Y)        # X: (n, samples) float, Y: (n, n_classes) 0/1
    arm.predict(X) -> (n, n_classes) 0/1

One arm instance is fit across increments (continual setting).

Outputs (per-class, credible):
* R[i, c] = F1 of class c on the joint test after increment i;
* bwt_primitives = mean over taught primitives of (F1_end − F1 right after the
  class was first taught) — negative = forgetting (axis A3);
* heldout_composition = zero-shot rate at which BOTH constituents of a
  never-trained combination fire on its examples (axis A4, continual proxy);
* notch_f1 = F1 on the never-taught primitive (axis A5 — should stay low / be
  refused, not confidently emitted).

Threshold is fixed at the arm's own 0.5 here; dev-set threshold selection and
multi-seed ± CI aggregation are added in the aggregation layer.
"""
from __future__ import annotations

import numpy as np

from .generator import (
    ALL_CLASSES,
    HELD_OUT_COMBINATIONS,
    HELD_OUT_PRIMITIVE,
    TAUGHT_COMBINATIONS,
    TAUGHT_PRIMITIVES,
    TEST_SNRS_DB,
    SignalConfig,
    generate_event,
    multihot,
)
from .metrics import per_class_f1
from .stream import CLEAN, CONCEPT_STREAM, build_increment

_IDX = {c: i for i, c in enumerate(ALL_CLASSES)}

# The joint test pools every concept + clean, so a negative for any class can
# still carry a different disturbance (confusable), not just silence.
JOINT_CONCEPTS = (
    [CLEAN]
    + [frozenset({p}) for p in TAUGHT_PRIMITIVES]
    + [frozenset(c) for c in TAUGHT_COMBINATIONS]
    + [frozenset({HELD_OUT_PRIMITIVE})]
    + [frozenset(c) for c in HELD_OUT_COMBINATIONS]
)


def build_joint_test(n_per_concept: int, seed: int, cfg: SignalConfig):
    rng = np.random.default_rng(seed)
    X, Y = [], []
    for concept in JOINT_CONCEPTS:
        for _ in range(n_per_concept):
            snr = float(rng.choice(TEST_SNRS_DB))
            sig, label = generate_event(concept, cfg, rng, snr)
            X.append(sig)
            Y.append(multihot(label))
    return np.asarray(X), np.asarray(Y)


def _first_increment(cls: str):
    for i, (_, concept) in enumerate(CONCEPT_STREAM):
        if cls in concept:
            return i
    return None


def run_stream(arm, *, n_train: int = 64, n_test: int = 48, seed: int = 0, cfg=None):
    cfg = cfg or SignalConfig()
    Xte, Yte = build_joint_test(n_test, seed=770_000 + seed, cfg=cfg)

    T, C = len(CONCEPT_STREAM), len(ALL_CLASSES)
    R = np.zeros((T, C))
    for i in range(T):
        Xtr, Ytr = build_increment(i, n_train, seed=seed, cfg=cfg)
        arm.fit(Xtr, Ytr)
        R[i] = per_class_f1(Yte, arm.predict(Xte))

    bwt = float(np.mean([R[-1, _IDX[c]] - R[_first_increment(c), _IDX[c]] for c in TAUGHT_PRIMITIVES]))

    pred = arm.predict(Xte)
    composition = {}
    for a, b in HELD_OUT_COMBINATIONS:
        mask = (Yte[:, _IDX[a]] == 1) & (Yte[:, _IDX[b]] == 1)
        if mask.any():
            both = (pred[mask][:, _IDX[a]] == 1) & (pred[mask][:, _IDX[b]] == 1)
            composition["+".join((a, b))] = float(np.mean(both))
        else:
            composition["+".join((a, b))] = float("nan")

    return {
        "R": R,
        "classes": list(ALL_CLASSES),
        "final_f1": {c: float(R[-1, _IDX[c]]) for c in ALL_CLASSES},
        "bwt_primitives": bwt,
        "notch_f1": float(R[-1, _IDX[HELD_OUT_PRIMITIVE]]),
        "heldout_composition": composition,
    }
