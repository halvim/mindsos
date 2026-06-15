"""DM-7 — carrier-box cooperation Plan (F6), sandbox (no MuJoCo, no socket).

The first multi-leaf decompose with real cross-device coordination (PB-4,
probe A): a per-CL ``planning.decompose``/``is_leaf`` override emits a real
3-leaf plan (arm1 load → conveyor bridge → arm2 receive); the manager's
derive runs the cooperation over the bus. Normal orders stay single-leaf.
"""

from __future__ import annotations

import threading
import time

from robot_demo.backend.brain import build_brain_stack
from robot_demo.backend.bus import BrainBus
from robot_demo.backend.frames import DemoEvents
from robot_demo.backend.installers import install_core_datastates
from robot_demo.backend.profiles import DEVICE_PROFILES
from robot_demo.backend.sanitize import find_leaks
from robot_demo.backend.serializer import build_episode_audit_snapshot
from robot_demo.backend.wiring import wire_demo


class _Duck:
    def __init__(self, u):
        self.user_id = u
        self.session_id = f"s-{u}"
        self.actor_role = "user"
        self.capabilities = frozenset()

    def has(self, c):
        return False


class _CaptureHub:
    def __init__(self):
        self.frames = []
        self._lock = threading.Lock()

    def publish(self, frame):
        with self._lock:
            self.frames.append(frame)

    def of_type(self, t):
        with self._lock:
            return [f for f in self.frames if f.get("type") == t]


def _brains():
    bs = {}
    for did in ("mgr", "arm1", "arm2", "conv"):
        b = build_brain_stack(DEVICE_PROFILES[did], _Duck(did))
        install_core_datastates(b.cl)
        bs[did] = b
    return bs


def _wait(pred, n=80, dt=0.03):
    for _ in range(n):
        if pred():
            return True
        time.sleep(dt)
    return pred()


def _mgr_pipelines(mgr):
    snap = build_episode_audit_snapshot(mgr)
    eps = snap["brains"]["mgr"]["episodes"]
    return [len(e["reasoning"].get("pipelines", [])) for e in eps], snap


def test_carrier_box_emits_three_leaf_plan_and_coordinates():
    brains = _brains()
    bus = BrainBus()
    hub = _CaptureHub()
    events = DemoEvents(hub)
    on_command = wire_demo(brains, bus, events, install_datastates=True)
    try:
        on_command("cooperate", {"item": "box1"})
        assert _wait(lambda: any(f.get("title") == "Reported"
                                 for f in hub.of_type("state")))

        # real multi-leaf plan: 4 milestones (root + 3) → 3 leaf pipelines
        counts, snap = _mgr_pipelines(brains["mgr"])
        assert 3 in counts, f"expected a 3-leaf plan, got pipeline counts {counts}"
        ep = next(e for e in snap["brains"]["mgr"]["episodes"]
                  if len(e["reasoning"].get("pipelines", [])) == 3)
        assert len(ep["reasoning"]["milestones"]) == 4

        # real cross-device coordination: the manager drove all three devices
        msgs = [(m["from"], m["to"]) for m in hub.of_type("message")]
        assert ("Orchestrator", "Arm1") in msgs
        assert ("Orchestrator", "Conveyor") in msgs
        assert ("Orchestrator", "Arm2") in msgs

        # clean wire (policy B)
        assert find_leaks(snap) == []
        assert find_leaks({"frames": hub.frames}) == []
    finally:
        bus.stop()
        for b in brains.values():
            b.il.stop()


def test_normal_order_stays_single_leaf():
    """Regression: the carrier-box overrides are inert for a normal order —
    is_leaf→True / decompose→[] → exactly one leaf pipeline."""
    brains = _brains()
    bus = BrainBus()
    hub = _CaptureHub()
    events = DemoEvents(hub)

    def run_atomic(brain, target):
        return {"status": "succeeded"}

    on_command = wire_demo(brains, bus, events, run_atomic=run_atomic,
                           install_datastates=True)
    try:
        on_command("place_order", {"lines": [{"item": "box1", "shelf": "a1"}]})
        assert _wait(lambda: any(f.get("title") == "Reported"
                                 for f in hub.of_type("state")))
        counts, _ = _mgr_pipelines(brains["mgr"])
        assert counts and all(c == 1 for c in counts), \
            f"normal order must stay single-leaf, got {counts}"
    finally:
        bus.stop()
        for b in brains.values():
            b.il.stop()
