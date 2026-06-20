"""DM-7 — teach + peer-transfer (F1/F2), sandbox (no MuJoCo, no socket).

Covers the locked picks (design-log §27):
- PB-1 Local-override: teach writes a Local ``learned-parameters`` node + a CL
  composite (no Global write).
- PB-2 receiver-side: a bus ``share`` message writes the descriptor into the
  RECEIVER's OWN Local — never the sender's.
- PB-3 honesty: the §5.2 embodiment gate still fires receiver-side after a
  transfer (it reads the receiver's own body).
- Integration: the ``teach`` / ``transfer`` WS commands drive it end-to-end and
  narrate behavior-level (policy B — no IP leak).
"""

from __future__ import annotations

import threading
import time

from robot_demo.backend.brain import build_brain_stack
from robot_demo.backend.bus import BrainBus, Message
from robot_demo.backend.feasibility import feasibility_for_brain
from robot_demo.backend.frames import DemoEvents
from robot_demo.backend.installers import install_core_datastates
from robot_demo.backend.profiles import DEVICE_PROFILES
from robot_demo.backend.sanitize import find_leaks
from robot_demo.backend.seeds import seed_local_embodiment
from robot_demo.backend.transfer import (
    KIND_SHARE,
    build_share_artifact,
    has_taught,
    make_share_handler,
    teach_local,
)
from robot_demo.backend.wiring import box_workaround_artifact, wire_demo
from robot_demo.backend.capacities import CAT_MECHANISM, DS_MOTION_DONE, DS_POSE_TARGET
from mindsos_capacity.identifiers import capacity_iri


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


def _arm(did):
    b = build_brain_stack(DEVICE_PROFILES[did], _Duck(did))
    install_core_datastates(b.cl)
    return b


_CAP = capacity_iri(CAT_MECHANISM, "load_into_box")


def test_teach_local_writes_own_local_and_cl():
    arm1 = _arm("arm1")
    try:
        node = teach_local(arm1, box_workaround_artifact())
        assert node == "learned-parameters-v1:parameter:load_into_box"
        assert has_taught(arm1, "load_into_box")
        assert arm1.cl.get_declaration(_CAP) is not None       # composite registered
    finally:
        arm1.il.stop()


def test_taught_composite_invokes():
    arm1 = _arm("arm1")
    try:
        teach_local(arm1, box_workaround_artifact())
        impl = arm1.cl.get_declaration(_CAP).implementation
        out = impl(**{DS_POSE_TARGET: {"item": "carrier"}})[DS_MOTION_DONE]
        assert out["taught"] is True and out["composite"] is True
        assert len(out["steps"]) == 4                          # the 4 descriptor steps
    finally:
        arm1.il.stop()


def test_receiver_side_share_writes_receiver_not_sender():
    arm1 = _arm("arm1")          # sender (never taught here)
    arm2 = _arm("arm2")          # receiver
    bus = BrainBus()
    bus.register_endpoint("arm2")
    bus.set_handler("arm2", KIND_SHARE, make_share_handler(arm2))
    try:
        artifact = build_share_artifact(
            "load_into_box",
            steps=box_workaround_artifact()["steps"],
            requires_affordances=["grasp:box"], peer="arm2")
        bus.send("arm1", "arm2", KIND_SHARE, artifact)
        for _ in range(40):
            if has_taught(arm2, "load_into_box"):
                break
            time.sleep(0.02)
        assert has_taught(arm2, "load_into_box")               # receiver got it
        assert arm2.cl.get_declaration(_CAP) is not None
        assert not has_taught(arm1, "load_into_box")           # sender NOT written
    finally:
        bus.stop()
        arm1.il.stop()
        arm2.il.stop()


def test_embodiment_gate_still_fires_after_transfer():
    """A transferred capability does not bypass the gate: it is evaluated
    against the RECEIVER's own embodiment (jaw arm still refused a suction item)."""
    arm2 = _arm("arm2")
    try:
        seed_local_embodiment(arm2.kl, arm2.session, "arm2")   # jaw arm
        teach_local(arm2, box_workaround_artifact())
        assert has_taught(arm2, "load_into_box")
        # sheet = suction-only → jaw arm refused; box = dual → feasible.
        assert feasibility_for_brain(arm2.kl, "arm2", "sheet1").gated is True
        assert feasibility_for_brain(arm2.kl, "arm2", "box1").gated is False
    finally:
        arm2.il.stop()


def test_teach_and_transfer_commands_end_to_end_and_clean_wire():
    brains = {did: _arm(did) for did in ("mgr", "arm1", "arm2", "conv")}
    bus = BrainBus()
    hub = _CaptureHub()
    events = DemoEvents(hub)
    on_command = wire_demo(brains, bus, events, install_datastates=True)
    try:
        on_command("teach", {"arm": "a1"})
        assert has_taught(brains["arm1"], "load_into_box")

        on_command("transfer", {"from": "a1"})
        for _ in range(50):
            if has_taught(brains["arm2"], "load_into_box"):
                break
            time.sleep(0.02)
        assert has_taught(brains["arm2"], "load_into_box")     # peer received it

        titles = [f.get("title") for f in hub.of_type("state") if f.get("title")]
        assert "Skill taught" in titles and "Peer transfer" in titles

        # policy B: no MindsOS IP on the wire (values-only leak scan).
        assert find_leaks({"frames": hub.frames}) == []
    finally:
        bus.stop()
        for b in brains.values():
            b.il.stop()
