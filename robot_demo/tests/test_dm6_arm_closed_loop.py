"""DM-6 task 3 (decision layer) — the arm's merged sufficient/blame + stash-
driven should_replan turn a closed-loop verification outcome into the right
chain artifacts (design-log §25 PB-T3.1/T3.3).

Sandbox-runnable (stub motion — the fault state is set directly; the live
verify→replan motion loop in run_atomic is gate-validated separately). Asserts:
  - recalibrate/recovery: N recalibrations -> N real ReplanRecords + succeeded;
  - reported fault: sufficient=False -> dont-know + blame carrying the cause;
  - the merge is backward-compatible (no fault state -> DM-5 gate-only behaviour).
"""

from __future__ import annotations

from robot_demo.backend.brain import build_brain_stack, run_task
from robot_demo.backend.gate import install_arm_gate, set_fault_state
from robot_demo.backend.installers import install_core_datastates
from robot_demo.backend.profiles import DEVICE_PROFILES
from robot_demo.backend.sanitize import find_leaks
from robot_demo.backend.serializer import build_episode_audit_snapshot


class _Duck:
    def __init__(self, u):
        self.user_id = u
        self.session_id = f"s-{u}"
        self.actor_role = "user"
        self.capabilities = frozenset()

    def has(self, c):
        return False


def _arm():
    b = build_brain_stack(DEVICE_PROFILES["arm1"], _Duck("arm1"))
    install_core_datastates(b.cl)
    install_arm_gate(b)
    return b


def test_recalibrate_recovery_emits_real_replans_and_succeeds():
    b = _arm()
    try:
        set_fault_state(b, recalibrations=2, max_divergence=0.03, reported=False)
        out = run_task(b, {"text": "recal"}, task_id="t").result(timeout=30)
        assert out.status == "succeeded"
        assert out.replans_used == 2

        snap = build_episode_audit_snapshot(b)
        r = snap["brains"]["a1"]["episodes"][0]["reasoning"]   # UI contract alias
        assert len(r["replans"]) == 2
        assert all(e["verdict"]["divergence"] == 0.03 for e in r["replans"])
        assert r["blame"] is None and r["dont_know"] is None   # recovered cleanly
        assert find_leaks(snap) == []
    finally:
        b.il.stop()


def test_reported_fault_escalates_to_dont_know_with_cause():
    b = _arm()
    try:
        set_fault_state(b, recalibrations=1, max_divergence=0.29, reported=True,
                        cause="a fault prevented completion")
        out = run_task(b, {"text": "fault"}, task_id="t").result(timeout=30)
        assert out.status == "dont_know"
        assert out.replans_used == 1                            # tried to recalibrate once

        snap = build_episode_audit_snapshot(b)
        r = snap["brains"]["a1"]["episodes"][0]["reasoning"]   # UI contract alias
        assert r["blame"] is not None
        assert r["blame"]["rationale"] == "a fault prevented completion"
        assert r["dont_know"] is not None
        assert len(r["replans"]) == 1
        assert find_leaks(snap) == []
    finally:
        b.il.stop()


def test_no_fault_state_is_dm5_backward_compatible():
    b = _arm()
    try:
        # no set_fault_state + no gate verdict -> clean success, no replans/blame
        out = run_task(b, {"text": "happy"}, task_id="t").result(timeout=30)
        assert out.status == "succeeded"
        assert out.replans_used == 0
        snap = build_episode_audit_snapshot(b)
        r = snap["brains"]["a1"]["episodes"][0]["reasoning"]   # UI contract alias
        assert r["replans"] == [] and r["blame"] is None and r["dont_know"] is None
    finally:
        b.il.stop()
