"""Priority-tier vocabulary shared by the L4 Executor and the L3
``decision.signal_to_tier`` classifier (ADR-0169).

This is the owning family for the tier type that ``context.TierVerdict.tier``
references. It lives in L3 (``mindsos_capacity``) so the L3 classifier can
return it and the L4 substrate can import it downward — an L4 home would force
an upward import that layer isolation forbids.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Dict


class TierEnum(IntEnum):
    """The four L4 scheduling tiers (ADR-0163 / Chat A D32.5b).

    Integer-valued with ``CRITICAL`` lowest so the Executor's
    ``(tier, -attention_score, submit_time)`` key sorts CRITICAL first.
    """

    CRITICAL = 0
    FOREGROUND = 1
    BACKGROUND = 2
    DREAM = 3


DEFAULT_TIER_SCORES: Dict[TierEnum, int] = {
    TierEnum.CRITICAL: 1000,
    TierEnum.FOREGROUND: 500,
    TierEnum.BACKGROUND: 100,
    TierEnum.DREAM: 10,
}

DEFAULT_HYSTERESIS: int = 50

ATTENTION_SCORE_MIN: int = 0
ATTENTION_SCORE_MAX: int = 9999


def default_score(tier: TierEnum) -> int:
    """Cold-start ``attention_score`` for ``tier`` (ADR-0163 §4)."""
    return DEFAULT_TIER_SCORES[tier]


__all__ = [
    "TierEnum",
    "DEFAULT_TIER_SCORES",
    "DEFAULT_HYSTERESIS",
    "ATTENTION_SCORE_MIN",
    "ATTENTION_SCORE_MAX",
    "default_score",
]
