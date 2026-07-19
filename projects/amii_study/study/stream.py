"""Concept stream + dataset builder — evaluation rig, part 1.

Turns the generator into the pre-registered incremental protocol: a fixed
order of concepts taught one increment at a time, plus a frozen test set
(read once) covering every class including the held-outs no arm ever
trains on. Every arm runs this identical protocol.
"""
from __future__ import annotations

from typing import FrozenSet, List, Tuple

import numpy as np

from .generator import (
    ALL_CLASSES,
    HELD_OUT_COMBINATIONS,
    HELD_OUT_PRIMITIVE,
    TAUGHT_COMBINATIONS,
    TAUGHT_PRIMITIVES,
    TEST_SNRS_DB,
    TRAIN_SNRS_DB,
    SignalConfig,
    generate_event,
    multihot,
)

CLEAN: FrozenSet[str] = frozenset()

# Pre-registered training order: each primitive alone, then each taught combination.
CONCEPT_STREAM: List[Tuple[str, FrozenSet[str]]] = (
    [(p, frozenset({p})) for p in TAUGHT_PRIMITIVES]
    + [("+".join(c), frozenset(c)) for c in TAUGHT_COMBINATIONS]
)

# Frozen test covers clean, every taught concept, and the held-outs (never trained).
FROZEN_TEST_CONCEPTS: List[FrozenSet[str]] = (
    [CLEAN]
    + [frozenset({p}) for p in TAUGHT_PRIMITIVES]
    + [frozenset(c) for c in TAUGHT_COMBINATIONS]
    + [frozenset({HELD_OUT_PRIMITIVE})]
    + [frozenset(c) for c in HELD_OUT_COMBINATIONS]
)


def _dataset(specs, split, seed, cfg):
    rng = np.random.default_rng(seed)
    snrs = TRAIN_SNRS_DB if split == "train" else TEST_SNRS_DB
    X, Y = [], []
    for present, count in specs:
        for _ in range(count):
            snr = float(rng.choice(snrs))
            sig, label = generate_event(present, cfg, rng, snr)
            X.append(sig)
            Y.append(multihot(label))
    return np.asarray(X), np.asarray(Y)


def build_increment(idx: int, n_per_class: int = 64, *, seed: int = 0, cfg=None):
    """Training data for increment ``idx``: positives of the new concept plus
    an equal number of clean negatives (train SNR band). Only the new concept
    — no replay of earlier ones, so forgetting is possible in principle."""
    cfg = cfg or SignalConfig()
    _, concept = CONCEPT_STREAM[idx]
    return _dataset(
        [(concept, n_per_class), (CLEAN, n_per_class)],
        split="train",
        seed=seed + 1000 * (idx + 1),
        cfg=cfg,
    )


def build_frozen_test(n_per_class: int = 64, *, seed: int = 99991, cfg=None):
    """The read-once test set: every class incl. held-outs, test SNR band."""
    cfg = cfg or SignalConfig()
    return _dataset(
        [(c, n_per_class) for c in FROZEN_TEST_CONCEPTS],
        split="test",
        seed=seed,
        cfg=cfg,
    )
