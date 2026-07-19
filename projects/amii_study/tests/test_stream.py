"""Validation for the concept stream + dataset builder.

The incremental order is pre-registered; the held-outs must never leak into
training; the frozen test must cover everything; and it must be deterministic.
"""
import numpy as np

from study.generator import ALL_CLASSES, HELD_OUT_COMBINATIONS
from study.stream import (
    CONCEPT_STREAM,
    FROZEN_TEST_CONCEPTS,
    build_frozen_test,
    build_increment,
)

IDX = {c: i for i, c in enumerate(ALL_CLASSES)}


def test_stream_order():
    assert [name for name, _ in CONCEPT_STREAM] == [
        "sag", "swell", "harmonic", "flicker", "transient",
        "sag+harmonic", "swell+harmonic", "flicker+harmonic",
    ]


def test_notch_never_trained():
    for i in range(len(CONCEPT_STREAM)):
        _, Y = build_increment(i, 8, seed=0)
        assert Y[:, IDX["notch"]].sum() == 0


def test_heldout_combinations_never_trained():
    trained = {c for _, c in CONCEPT_STREAM}
    for combo in HELD_OUT_COMBINATIONS:
        assert frozenset(combo) not in trained


def test_increment_shapes_and_labels():
    X, Y = build_increment(0, 8, seed=1)  # sag
    assert X.shape == (16, 2560) and Y.shape == (16, len(ALL_CLASSES))
    assert Y[:, IDX["sag"]].sum() == 8              # 8 positives
    assert (Y.sum(axis=1) == 0).sum() == 8          # 8 clean negatives


def test_frozen_test_covers_all_including_heldout():
    X, Y = build_frozen_test(4, seed=5)
    assert X.shape[0] == len(FROZEN_TEST_CONCEPTS) * 4
    assert Y[:, IDX["notch"]].sum() == 4            # held-out primitive, test-only
    both = (Y[:, IDX["sag"]] == 1) & (Y[:, IDX["transient"]] == 1)
    assert np.any(both)                             # held-out combination present


def test_determinism():
    a, _ = build_increment(2, 8, seed=3)
    b, _ = build_increment(2, 8, seed=3)
    assert np.array_equal(a, b)
