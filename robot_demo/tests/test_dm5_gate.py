"""DM-5 — embodiment gate: real wrong-gripper refusal → dont-know Episode.

Exercises the gate end-to-end against the REAL ``mindsos_intelligence`` v0
lifecycle (MuJoCo-free; ``run_atomic`` stubbed): a tube dispatched to the
suction arm must produce a genuine ``outcome_classification:"dont_know"``
Episode with a populated, sanitized ``reasoning.dont_know``/``blame`` — and a
sheet (graspable by suction) must still succeed. Plus the feasibility unit
table.
"""

from __future__ import annotations

import time

from robot_demo.backend.brain import build_brain_stack, run_task
from robot_demo.backend.bus import BrainBus
from robot_demo.backend.feasibility import check_feasibility, item_kind
from robot_demo.backend.frames import DemoEvents, FrameHub
from robot_demo.backend.profiles import DEVICE_PROFILES
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


# ── feasibility unit table (scenario §2/§5.2) ─────────────────────────────
def test_feasibility_table():
    assert item_kind("tube1") == "tube"
    assert item_kind("box2") == "box"
    assert item_kind("widget9") is None
    suction = ["grasp:suction"]
    jaw = ["grasp:jaw"]
    # suction arm: sheet/box ok, tube refused
    assert check_feasibility("sheet1", suction).feasible
    assert check_feasibility("box1", suction).feasible
    assert not check_feasibility("tube1", suction).feasible
    # jaw arm: tube/box ok, sheet refused
    assert check_feasibility("tube1", jaw).feasible
    assert check_feasibility("box1", jaw).feasible
    assert not check_feasibility("sheet1", jaw).feasible
    # fail-open: no body model or unknown item → not gated (config gap ≠ refusal)
    assert check_feasibility("tube1", []).feasible
    assert check_feasibility("widget9", suction).feasible
    # the refusal reason is behavior-level (no affordance codes / IP)
    r = check_feasibility("tube1", suction).reason.lower()
    assert "gripper" in r and "grasp:" not in r


def _wire(brains):
    bus = BrainBus()
    hub = _CaptureHub()
    events = DemoEvents(hub)

    def run_atomic(brain, target):
        return {"status": "succeeded", "target": target}

    on_command = wire_demo(
        brains, bus, events, run_atomic=run_atomic, install_datastates=True
    )
    return bus, hub, events, on_command


def _wait_reported(hub, n=1, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if len([f for f in hub.of_type("state") if f.get("title") == "Reported"]) >= n:
            return True
        time.sleep(0.05)
    return False


def test_wrong_gripper_is_a_real_dont_know():
    mgr = build_brain_stack(DEVICE_PROFILES["mgr"], _DuckSession("mgr"))
    arm = build_brain_stack(DEVICE_PROFILES["arm1"], _DuckSession("arm1"))  # suction
    seed_local_embodiment(arm.kl, arm.session, "arm1")  # DM-2 body model
    brains = {"mgr": mgr, "arm1": arm}
    bus, hub, events, on_command = _wire(brains)
    try:
        # tube needs a jaw; arm1 is suction → honest refusal
        on_command("place_order", {"lines": [{"item": "tube", "shelf": "a1"}]})
        assert _wait_reported(hub), "manager never reported"
        time.sleep(0.2)  # let the arm's refusal-capture done-callback settle

        # a GATED badge surfaced on the arm card
        gated = [
            f for f in hub.of_type("state")
            if any(
                cap == ["pick", "GATED"]
                for b in f.get("brains", {}).values()
                for cap in b.get("caps", [])
            )
        ]
        assert gated, "expected a GATED cap badge on refusal"

        # the arm's Episode is a REAL dont-know with populated, sanitized reason
        snap = build_episode_audit_snapshot(arm)  # strict=True raises on any leak
        eps = snap["brains"]["a1"]["episodes"]
        assert eps, "no arm episode recorded"
        ep = eps[0]
        assert ep["value"]["outcome_classification"] == "dont_know"
        dk = ep["reasoning"]["dont_know"]
        bl = ep["reasoning"]["blame"]
        assert dk and "gripper" in dk["reason"].lower()
        assert bl and bl["rationale"]
        # the manager reported the refusal on the wire (behavior-level)
        msgs = [m["text"].lower() for m in hub.of_type("message")]
        assert any("dont_know" in t or "don't" in t or "block" in t for t in msgs) \
            or any("dont_know" in (m.get("text", "")) for m in hub.of_type("message"))
    finally:
        bus.stop()
        mgr.il.stop()
        arm.il.stop()


def test_right_gripper_still_succeeds():
    mgr = build_brain_stack(DEVICE_PROFILES["mgr"], _DuckSession("mgr"))
    arm = build_brain_stack(DEVICE_PROFILES["arm1"], _DuckSession("arm1"))  # suction
    seed_local_embodiment(arm.kl, arm.session, "arm1")
    brains = {"mgr": mgr, "arm1": arm}
    bus, hub, events, on_command = _wire(brains)
    try:
        # sheet is suction-graspable → the gate passes, the move runs
        on_command("place_order", {"lines": [{"item": "sheet", "shelf": "a1"}]})
        assert _wait_reported(hub), "manager never reported"
        time.sleep(0.2)
        snap = build_episode_audit_snapshot(arm)
        eps = snap["brains"]["a1"]["episodes"]
        assert eps and eps[0]["value"]["outcome_classification"] == "succeeded"
        assert eps[0]["reasoning"]["dont_know"] is None
        assert eps[0]["reasoning"]["blame"] is None
    finally:
        bus.stop()
        mgr.il.stop()
        arm.il.stop()
