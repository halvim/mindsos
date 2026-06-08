"""Phase 46 — TierEnum owning-family + defaults (ADR-0169 / ADR-0163)."""

from __future__ import annotations

from mindsos_capacity.tiers import (
    ATTENTION_SCORE_MAX,
    ATTENTION_SCORE_MIN,
    DEFAULT_HYSTERESIS,
    DEFAULT_TIER_SCORES,
    TierEnum,
    default_score,
)
from mindsos_capacity.context import TierVerdict


def test_critical_sorts_first():
    assert TierEnum.CRITICAL < TierEnum.FOREGROUND < TierEnum.BACKGROUND < TierEnum.DREAM


def test_default_scores():
    assert DEFAULT_TIER_SCORES == {
        TierEnum.CRITICAL: 1000,
        TierEnum.FOREGROUND: 500,
        TierEnum.BACKGROUND: 100,
        TierEnum.DREAM: 10,
    }
    assert default_score(TierEnum.CRITICAL) == 1000


def test_score_bounds_and_hysteresis():
    assert ATTENTION_SCORE_MIN == 0
    assert ATTENTION_SCORE_MAX == 9999
    assert DEFAULT_HYSTERESIS == 50


def test_tier_verdict_accepts_tier_enum():
    v = TierVerdict(tier=TierEnum.CRITICAL, rationale="urgent")
    assert v.tier is TierEnum.CRITICAL
    assert TierVerdict(tier=None, rationale="dont-know").tier is None
