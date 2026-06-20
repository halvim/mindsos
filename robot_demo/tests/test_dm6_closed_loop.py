"""DM-6 — closed-loop verification core (divergence + tiered decision).

Sandbox-runnable (no MuJoCo): unit-tests the pure decision body that maps the
joint commanded-vs-actual divergence onto the shipped ReplanVerdict decision
(design-log §25 PB-25.11 / §25.A). The live sim wiring (sim_engine.disturb_joint
+ motion-body verify→replan) is gate-validated separately.
"""

from __future__ import annotations

from robot_demo.backend.closed_loop import (
    DECISION_CONTINUE,
    DECISION_REPLAN,
    DECISION_REPORT,
    TIER_OK,
    TIER_RECALIBRATE,
    TIER_REPORT,
    classify,
    decide,
    divergence_band,
    joint_divergence,
)
from robot_demo.backend.sanitize import find_leaks


def test_joint_divergence_is_max_abs_error():
    assert joint_divergence([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]) == 0.0
    assert abs(joint_divergence([0.0, 0.0, 0.0], [0.0, 0.03, 0.0]) - 0.03) < 1e-9
    # length-mismatch-safe (common prefix), empty -> 0.0
    assert joint_divergence([], []) == 0.0
    assert joint_divergence([1.0, 2.0], [1.0, 2.0, 9.0]) == 0.0


def test_classify_tiers():
    assert classify(0.0) == TIER_OK
    assert classify(0.003) == TIER_OK
    assert classify(0.03) == TIER_RECALIBRATE
    assert classify(0.5) == TIER_REPORT


def test_ok_continues():
    decision, tier, mag = decide(0.0, 0)
    assert decision == DECISION_CONTINUE and tier == TIER_OK and mag == 0.0


def test_small_divergence_recalibrates_until_budget_then_reports():
    # transient bump -> replan (recalibrate) while retries remain
    decision, tier, _ = decide(0.03, 0, budget=3)
    assert decision == DECISION_REPLAN and tier == TIER_RECALIBRATE
    decision, tier, _ = decide(0.03, 2, budget=3)
    assert decision == DECISION_REPLAN
    # persistence backstop: retries spent -> escalate to report
    decision, tier, _ = decide(0.03, 3, budget=3)
    assert decision == DECISION_REPORT and tier == TIER_REPORT


def test_major_divergence_reports_immediately():
    # frozen joint -> large commanded-vs-actual -> report on the first check
    decision, tier, mag = decide(0.6, 0, budget=3)
    assert decision == DECISION_REPORT and tier == TIER_REPORT and mag == 0.6


def test_band_is_behavior_level_and_clean():
    assert divergence_band(0.0) == "none"
    assert divergence_band(0.03) == "minor"
    assert divergence_band(0.6) == "major"
    # no raw radians / internal tokens leak on the wire (policy B)
    assert find_leaks({"divergence_band": divergence_band(0.03)}) == []
