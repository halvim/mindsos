"""DM-6 task 6 — manager reroute decision layer + chain artifacts.

Sandbox-runnable: tests the alternate-arm grasp table (pure) and that the
manager's closed-loop overrides (install_manager_replan) turn a reroute / dead-
end fault stash into the right MANAGER-chain artifacts — the recovery episode
(succeeded + one real ReplanRecord, the reroute) and the dead-end (dont-know +
blame). The live mgr_derive reroute over the bus is gate-validated (dm6_check).
"""

from __future__ import annotations

from robot_demo.backend.brain import build_brain_stack, run_task
from robot_demo.backend.gate import install_manager_replan, set_fault_state
from robot_demo.backend.profiles import DEVICE_PROFILES
from robot_demo.backend.sanitize import find_leaks
from robot_demo.backend.serializer import build_episode_audit_snapshot
from robot_demo.backend.wiring import _alternate_arm


class _Duck:
    def __init__(self, u):
        self.user_id = u
        self.session_id = f"s-{u}"
        self.actor_role = "user"
        self.capabilities = frozenset()

    def has(self, c):
        return False


def test_alternate_arm_grasp_table():
    assert _alternate_arm("arm1", "box1") == "arm2"    # jaw can also grasp a box
    assert _alternate_arm("arm2", "box2") == "arm1"     # suction can also grasp a box
    assert _alternate_arm("arm1", "sheet1") is None     # sheet = suction-only -> dead-end
    assert _alternate_arm("arm2", "tube1") is None      # tube = jaw-only -> dead-end
    assert _alternate_arm("arm1", "widget9") is None    # unknown kind -> dead-end


def _mgr():
    b = build_brain_stack(DEVICE_PROFILES["mgr"], _Duck("mgr"))
    install_manager_replan(b)
    return b


def test_manager_recovery_emits_one_replan_and_succeeds():
    b = _mgr()
    try:
        set_fault_state(b, recalibrations=1, reported=False,
                        cause="re-routed to the other arm after a detected fault")
        out = run_task(b, {"text": "reroute"}, task_id="t").result(timeout=30)
        assert out.status == "succeeded"
        assert out.replans_used == 1

        snap = build_episode_audit_snapshot(b)
        r = snap["brains"]["mgr"]["episodes"][0]["reasoning"]
        assert len(r["replans"]) == 1                   # the reroute, on the manager chain
        assert r["blame"] is None and r["dont_know"] is None
        assert find_leaks(snap) == []
    finally:
        b.il.stop()


def test_manager_deadend_emits_dont_know_with_blame():
    b = _mgr()
    try:
        set_fault_state(b, recalibrations=0, reported=True,
                        cause="no available arm can handle this item")
        out = run_task(b, {"text": "deadend"}, task_id="t").result(timeout=30)
        assert out.status == "dont_know"

        snap = build_episode_audit_snapshot(b)
        r = snap["brains"]["mgr"]["episodes"][0]["reasoning"]
        assert r["blame"] is not None
        assert r["blame"]["rationale"] == "no available arm can handle this item"
        assert r["dont_know"] is not None
        assert find_leaks(snap) == []
    finally:
        b.il.stop()
