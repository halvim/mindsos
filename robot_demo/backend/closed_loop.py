"""DM-6 closed-loop verification — divergence magnitude + tiered decision.

Maps the demo's expected-vs-actual joint check onto MindsOS's **shipped** replan
substrate (`ReplanVerdict.divergence` + the 3-way `decision`). MindsOS supplies
the substrate (`decision.should_replan` / `predicate.sufficient` / the replan
loop); THIS module is the installed verification capability's decision body —
the real MSUR/SCMS divergence body ships in (unbuilt) WSD installation, so the
demo supplies it. Pure + unit-testable; the live sim wiring lives in the motion
bodies (the orchestrator's re-execution is hollow — design-log PB-25.1).

Tiers (design-log §25 PB-25.11 / §25.A), keyed off the divergence magnitude:
  - OK         (~0)            -> continue
  - RECALIBRATE (small)        -> replan-from-current (no servo-back); bounded
  - REPORT     (large/persist) -> escalate to the user (sufficient=False -> dont-know)
"""

from __future__ import annotations

from typing import Sequence, Tuple

TIER_OK = "ok"
TIER_RECALIBRATE = "recalibrate"
TIER_REPORT = "report"

# decision values align with ReplanVerdict.decision {continue, replan, abort};
# "report" escalates via sufficient=False (dont-know), not via abort.
DECISION_CONTINUE = "continue"
DECISION_REPLAN = "replan"      # recalibrate: replan-to-goal-from-current-pose
DECISION_REPORT = "report"      # major: surface to the user

# Demo-supplied policy (NOT MindsOS-tuned thresholds — see §25 honesty note).
OK_MAX_RAD = 0.005
RECALIBRATE_MAX_RAD = 0.05
DEFAULT_RECAL_BUDGET = 3


def joint_divergence(commanded: Sequence[float], achieved: Sequence[float]) -> float:
    """Max abs per-joint commanded-vs-actual error (rad) — the divergence
    magnitude. Length-mismatch-safe (compares the common prefix); 0.0 if empty.
    This is the honest signal (joint-space, exact), NOT the cartesian TCP residual
    (hundreds of mm even healthy — gate experiment 2026-06-13)."""
    n = min(len(commanded), len(achieved))
    if n == 0:
        return 0.0
    return max(abs(float(commanded[i]) - float(achieved[i])) for i in range(n))


def classify(divergence: float, *, ok_max: float = OK_MAX_RAD,
             recal_max: float = RECALIBRATE_MAX_RAD) -> str:
    if divergence <= ok_max:
        return TIER_OK
    if divergence <= recal_max:
        return TIER_RECALIBRATE
    return TIER_REPORT


def decide(divergence: float, recal_attempts: int, *,
           budget: int = DEFAULT_RECAL_BUDGET, ok_max: float = OK_MAX_RAD,
           recal_max: float = RECALIBRATE_MAX_RAD) -> Tuple[str, str, float]:
    """Return ``(decision, tier, divergence)`` with decision in
    {continue, replan, report}. A RECALIBRATE tier escalates to REPORT once the
    bounded recalibration retries are spent (persistence backstop)."""
    tier = classify(divergence, ok_max=ok_max, recal_max=recal_max)
    if tier == TIER_OK:
        return (DECISION_CONTINUE, tier, divergence)
    if tier == TIER_RECALIBRATE:
        if recal_attempts < budget:
            return (DECISION_REPLAN, tier, divergence)
        return (DECISION_REPORT, TIER_REPORT, divergence)  # exhausted -> report
    return (DECISION_REPORT, tier, divergence)


def divergence_band(divergence: float, *, ok_max: float = OK_MAX_RAD,
                    recal_max: float = RECALIBRATE_MAX_RAD) -> str:
    """Behaviour-level band for the UI / sanitized export — ``none|minor|major``
    (no raw radians on the wire; IP-safe, policy B)."""
    return {TIER_OK: "none", TIER_RECALIBRATE: "minor",
            TIER_REPORT: "major"}[classify(divergence, ok_max=ok_max, recal_max=recal_max)]


__all__ = [
    "TIER_OK", "TIER_RECALIBRATE", "TIER_REPORT",
    "DECISION_CONTINUE", "DECISION_REPLAN", "DECISION_REPORT",
    "OK_MAX_RAD", "RECALIBRATE_MAX_RAD", "DEFAULT_RECAL_BUDGET",
    "joint_divergence", "classify", "decide", "divergence_band",
]
