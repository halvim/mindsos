"""feat/subminds Slice 1 — SubMind runtime core (ADR-0188 / ADR-0189 §1).

Pure, threadless: severity/proximity math, monotonic tier mapping +
hysteresis, attention_score scaling, adaptive cadence, storm suppression
(emit-once + escalation-on-step + re-arm), activation floor cadence.
"""

from __future__ import annotations

import pytest

from mindsos_capacity.tiers import ATTENTION_SCORE_MAX, TierEnum
from mindsos_intelligence import (
    ActivationState,
    CadenceLaw,
    SubMind,
    SubMindDefinition,
    SubMindState,
    VitalDirection,
)

_BANDS = (
    (0.0, TierEnum.BACKGROUND),
    (0.6, TierEnum.FOREGROUND),
    (0.8, TierEnum.CRITICAL),
)


def _battery(reading_box, **over):
    activation = over.pop("activation", ActivationState.ACTIVE)
    kw = dict(
        name="battery",
        check=lambda: reading_box["v"],
        direction=VitalDirection.LOW_BAD,
        safe=100.0,
        threshold=50.0,
        failure=0.0,
        severity_tier_bands=_BANDS,
        importance_weight=1000,
        cadence=CadenceLaw(0.1, 2.0, 10.0),
        reset_margin=0.1,
    )
    kw.update(over)
    return SubMind(SubMindDefinition(**kw), activation=activation)


# ── physical quantities ────────────────────────────────────────────────


def test_severity_zero_on_safe_side():
    sm = _battery({"v": 80.0})
    assert sm.severity_of(80.0) == 0.0
    assert sm.severity_of(50.0) == 0.0


def test_severity_linear_over_threshold_to_failure():
    sm = _battery({"v": 0.0})
    assert sm.severity_of(40.0) == pytest.approx(0.2)
    assert sm.severity_of(10.0) == pytest.approx(0.8)
    assert sm.severity_of(0.0) == 1.0
    assert sm.severity_of(-5.0) == 1.0  # clamped


def test_proximity_drives_cadence_span():
    sm = _battery({"v": 0.0})
    assert sm.proximity_of(100.0) == 0.0
    assert sm.proximity_of(75.0) == pytest.approx(0.5)
    assert sm.proximity_of(50.0) == 1.0
    assert sm.proximity_of(20.0) == 1.0  # at/over threshold ⇒ fastest


def test_high_bad_direction_symmetry():
    box = {"v": 0.0}
    sm = SubMind(SubMindDefinition(
        name="temp", check=lambda: box["v"], direction=VitalDirection.HIGH_BAD,
        safe=20.0, threshold=70.0, failure=100.0,
        severity_tier_bands=_BANDS, importance_weight=500,
        cadence=CadenceLaw(0.1, 1.0, 5.0),
    ))
    assert sm.severity_of(85.0) == pytest.approx(0.5)
    assert sm.proximity_of(45.0) == pytest.approx(0.5)


# ── tier + score ───────────────────────────────────────────────────────


def test_tier_mapping_step_function():
    sm = _battery({"v": 0.0})
    assert sm.tier_for(0.1) is TierEnum.BACKGROUND
    assert sm.tier_for(0.6) is TierEnum.FOREGROUND
    assert sm.tier_for(0.85) is TierEnum.CRITICAL


def test_non_monotonic_bands_rejected():
    with pytest.raises(ValueError):
        _battery({"v": 0.0}, severity_tier_bands=(
            (0.0, TierEnum.CRITICAL), (0.5, TierEnum.BACKGROUND),
        ))


def test_attention_score_scales_weight_by_severity():
    sm = _battery({"v": 0.0}, importance_weight=1000)
    assert sm.attention_score(0.0) == 0
    assert sm.attention_score(0.2) == 200
    assert sm.attention_score(1.0) == 1000


def test_attention_score_clamped_to_heap_max():
    sm = _battery({"v": 0.0}, importance_weight=ATTENTION_SCORE_MAX)
    assert sm.attention_score(1.0) == ATTENTION_SCORE_MAX


def test_weight_out_of_range_rejected():
    with pytest.raises(ValueError):
        _battery({"v": 0.0}, importance_weight=ATTENTION_SCORE_MAX + 1)


# ── cadence ────────────────────────────────────────────────────────────


def test_cadence_faster_near_threshold():
    law = CadenceLaw(0.1, 2.0, 10.0)
    assert law.interval_for(0.0, floored=False) == pytest.approx(2.0)  # safe ⇒ slow
    assert law.interval_for(1.0, floored=False) == pytest.approx(0.1)  # near ⇒ fast
    assert law.interval_for(0.5, floored=False) == pytest.approx(1.05)


def test_floored_uses_floor_cadence():
    sm = _battery({"v": 20.0}, activation=ActivationState.FLOORED)
    sm.tick()  # populate last reading (proximity would be 1.0 = fast)
    assert sm.next_interval() == 10.0  # floor, not the fast adaptive value


def test_cadence_bounds_validated():
    with pytest.raises(ValueError):
        CadenceLaw(2.0, 1.0, 10.0)   # min > max
    with pytest.raises(ValueError):
        CadenceLaw(0.1, 2.0, 1.0)    # floor < max


# ── storm suppression ──────────────────────────────────────────────────


def test_emit_once_on_crossing_then_silent():
    box = {"v": 80.0}
    sm = _battery(box)
    assert sm.tick() is None             # safe
    box["v"] = 40.0
    sig = sm.tick()                      # cross
    assert sig is not None and sig.kind == "signal"
    assert sm.state is SubMindState.FIRED
    assert sm.tick() is None             # storm-silent at same level


def test_escalation_on_worsening_step():
    box = {"v": 40.0}
    sm = _battery(box)
    first = sm.tick()
    assert first.tier is TierEnum.BACKGROUND
    box["v"] = 10.0                      # severity 0.8 ⇒ CRITICAL
    esc = sm.tick()
    assert esc is not None and esc.kind == "escalation"
    assert esc.tier is TierEnum.CRITICAL
    assert sm.tick() is None             # no re-emit at same level


def test_no_escalation_within_same_tier():
    box = {"v": 40.0}                    # severity 0.2 BACKGROUND
    sm = _battery(box)
    sm.tick()
    box["v"] = 35.0                      # severity 0.3 still BACKGROUND
    assert sm.tick() is None


def test_rearm_only_after_reset_margin():
    box = {"v": 40.0}
    sm = _battery(box)                   # reset_margin 0.1 ⇒ clear @ 55
    sm.tick()
    box["v"] = 52.0                      # recovered but inside margin
    assert sm.tick() is None
    assert sm.state is SubMindState.FIRED
    box["v"] = 60.0                      # cleared margin
    assert sm.tick() is None
    assert sm.state is SubMindState.ARMED
    box["v"] = 40.0
    again = sm.tick()                    # fresh crossing emits again
    assert again is not None and again.kind == "signal"


def test_off_submind_never_ticks():
    sm = _battery({"v": 10.0}, activation=ActivationState.OFF)
    assert sm.tick() is None
    assert sm.state is SubMindState.ARMED
