"""DM-5 — order → (arm, cell) allocation + the Plan ▸ Resolve producer.

Unit-tests the deterministic resolver (absolute term + relational narrowing,
9→…→1) and the allocator, then drives a real ``place_order`` with a ``pos``
clause through ``wire_demo`` to assert a live ``resolve`` frame + the arm
moving to the resolved cell. MuJoCo-free (``run_atomic`` stubbed).
"""

from __future__ import annotations

import time

from robot_demo.backend.allocation import (
    allocate,
    arm_for_shelf,
    cell_target,
    make_allocator,
    resolve_pos,
)
from robot_demo.backend.brain import build_brain_stack
from robot_demo.backend.bus import BrainBus
from robot_demo.backend.frames import DemoEvents, FrameHub
from robot_demo.backend.profiles import DEVICE_PROFILES
from robot_demo.backend.sanitize import find_leaks
from robot_demo.backend.seeds import seed_local_embodiment
from robot_demo.backend.serializer import build_episode_audit_snapshot
from robot_demo.backend.wiring import wire_demo


class _DuckSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.username = user_id

    @property
    def caps(self):
        return set()


class _CaptureHub(FrameHub):
    def __init__(self):
        super().__init__()
        self.frames = []

    def publish(self, frame):
        self.frames.append(frame)

    def of_type(self, t):
        return [f for f in self.frames if f.get("type") == t]


# ── resolver units ────────────────────────────────────────────────────────
def test_arm_for_shelf():
    assert arm_for_shelf("a1") == "arm1"
    assert arm_for_shelf("a2") == "arm2"
    assert arm_for_shelf("shelf_R") == "arm2"
    assert arm_for_shelf(None) == "arm1"
    assert cell_target(4) == "r1c1"
    assert cell_target(0) == "r0c0"


def test_resolve_absolute_term():
    res = resolve_pos([{"type": "shelf", "pos": "center"}], {})
    assert res.feasible and res.winner == 4
    # 9 → 1 narrowing: first stage all cand, last stage a single win
    assert res.stages[0]["cells"][0] == "cand"
    assert sum(1 for v in res.stages[-1]["cells"].values() if v == "win") == 1
    assert res.stages[-1]["cells"][4] == "win"


def test_resolve_relational_above_tube():
    # Tube at centre (cell 4); "above Tube" → the cell directly above (1).
    res = resolve_pos(
        [{"type": "rel", "rel": "above", "obj": "Tube"}], {"tube": 4}
    )
    assert res.feasible and res.winner == 1
    assert res.tube == 4  # reference marker for the UI dot
    # a 3-candidate stage exists nowhere here (single offset), but the narrowing
    # is honest: all(9) → above(1)
    assert res.stages[0]["cap"].startswith("all")


def test_resolve_unknown_term_is_infeasible():
    res = resolve_pos([{"type": "shelf", "pos": "nowhere"}], {})
    assert not res.feasible and res.winner is None
    assert "don't know" in res.reason.lower()


def test_resolve_relation_needs_reference_present():
    # "above Tube" with no tube on the shelf → honest infeasible, not a guess
    res = resolve_pos([{"type": "rel", "rel": "above", "obj": "Tube"}], {})
    assert not res.feasible and "isn't on the shelf" in res.reason


def test_allocate_updates_shelf_state():
    state = {}
    res = allocate(
        {"lines": [{"item": "box", "shelf": "a1",
                    "pos": [{"type": "shelf", "pos": "center"}]}]},
        state,
    )
    assert res.arm == "arm1" and res.winner == 4
    assert state["arm1"][4] == "box"  # occupancy recorded
    # a follow-up "above box" now resolves against the recorded reference
    res2 = allocate(
        {"lines": [{"item": "tube", "shelf": "a1",
                    "pos": [{"type": "rel", "rel": "above", "obj": "box"}]}]},
        state,
    )
    assert res2.winner == 1  # directly above cell 4


def test_resolve_frame_is_clean():
    hub = _CaptureHub()
    events = DemoEvents(hub)
    decide = make_allocator(events)
    arm, target = decide({"order": {"lines": [
        {"item": "box", "shelf": "a1", "pos": [{"type": "shelf", "pos": "center"}]}
    ]}})
    assert (arm, target) == ("arm1", "r1c1")
    rf = hub.of_type("resolve")
    assert rf and rf[0]["winner"] == 4 and rf[0]["brain"] == "mgr"
    assert find_leaks(rf[0]) == []  # no IP tokens in cap labels / clause


# ── end-to-end through wire_demo ──────────────────────────────────────────
def test_place_order_resolves_and_moves_to_cell():
    mgr = build_brain_stack(DEVICE_PROFILES["mgr"], _DuckSession("mgr"))
    arm = build_brain_stack(DEVICE_PROFILES["arm1"], _DuckSession("arm1"))
    seed_local_embodiment(arm.kl, arm.session, "arm1")
    brains = {"mgr": mgr, "arm1": arm}
    bus = BrainBus()
    hub = _CaptureHub()
    events = DemoEvents(hub)
    ran = {}

    def run_atomic(brain, target):
        ran["target"] = target
        return {"status": "succeeded", "target": target}

    decide = make_allocator(events)
    on_command = wire_demo(
        brains, bus, events, run_atomic=run_atomic, decide=decide,
        install_datastates=True,
    )
    try:
        on_command("place_order", {"lines": [
            {"item": "box", "shelf": "a1", "pos": [{"type": "shelf", "pos": "center"}]}
        ]})
        deadline = time.time() + 10
        while time.time() < deadline:
            if any(f.get("title") == "Reported" for f in hub.of_type("state")):
                break
            time.sleep(0.05)
        time.sleep(0.2)
        # the resolve panel got its live narrowing
        rf = hub.of_type("resolve")
        assert rf and rf[0]["winner"] == 4
        # the arm moved to the resolved cell (not the DM-4 fixed "home")
        assert ran.get("target") == "r1c1"
        # and it succeeded (box is suction-graspable)
        snap = build_episode_audit_snapshot(arm)
        eps = snap["brains"]["a1"]["episodes"]
        assert eps and eps[0]["value"]["outcome_classification"] == "succeeded"
    finally:
        bus.stop()
        mgr.il.stop()
        arm.il.stop()
