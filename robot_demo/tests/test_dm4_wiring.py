"""DM-4 — full wired gate flow → frames (sandbox, no MuJoCo, no socket).

Drives a real ``place_order`` through the wiring module with a CaptureHub
standing in for the WS layer, and asserts the emitted frames narrate the real
flow: order → dispatch → arm executes (real arm lifecycle) → report, with the
brain ids aliased to the contract (arm1→a1) and the §3 transients present.
"""

from __future__ import annotations

import threading
import time

from robot_demo.backend.brain import build_brain_stack
from robot_demo.backend.profiles import DEVICE_PROFILES
from robot_demo.backend.frames import DemoEvents
from robot_demo.backend.bus import BrainBus
from robot_demo.backend.wiring import wire_demo


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


class _DuckSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.session_id = f"sess-{user_id}"
        self.actor_role = "user"
        self.capabilities = frozenset()

    def has(self, capability):
        return True


def _episode_count(brain):
    from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
    from mindsos_knowledge.metagraph_view import MetagraphView
    g = MetagraphView(brain.kl.local_metagraph(brain.device_id)).graphs_by_role(
        ROLE_EPISODIC_MEMORIES
    )[0]
    return sum(1 for n in g.nodes.values()
               if getattr(n, "type_name", None) == "Episode")


def test_place_order_drives_flow_and_emits_frames():
    mgr = build_brain_stack(DEVICE_PROFILES["mgr"], _DuckSession("mgr"))
    arm = build_brain_stack(DEVICE_PROFILES["arm1"], _DuckSession("arm1"))
    brains = {"mgr": mgr, "arm1": arm}
    bus = BrainBus()
    hub = _CaptureHub()
    events = DemoEvents(hub)

    ran = {}

    def run_atomic(brain, target):
        ran["target"] = target
        ran["brain"] = brain.device_id
        return {"status": "succeeded"}

    on_command = wire_demo(
        brains, bus, events, run_atomic=run_atomic, install_datastates=True
    )

    try:
        on_command("place_order", {"lines": [{"item": "sheet", "shelf": "a1"}]})
        # the mgr lifecycle runs on its IL pool; wait for the arm to execute
        for _ in range(100):
            if ran.get("target") and hub.of_type("state"):
                # wait until the terminal "Reported" mgr frame lands
                if any(f.get("title") == "Reported" for f in hub.of_type("state")):
                    break
            time.sleep(0.05)

        # flow ran end-to-end through both lifecycles
        assert ran.get("target") == "home"
        assert ran.get("brain") == "arm1"
        assert _episode_count(mgr) >= 1
        assert _episode_count(arm) >= 1

        # frames narrate the flow
        states = hub.of_type("state")
        messages = hub.of_type("message")
        titles = [f.get("title") for f in states if f.get("title")]
        assert "Order placed" in titles
        assert "Assign task" in titles
        assert "Reported" in titles

        # brain ids aliased to contract ids (arm1 → a1)
        arm_states = [f for f in states if "a1" in f.get("brains", {})]
        assert arm_states, "expected at least one a1 (arm1) state frame"
        for f in arm_states:
            assert "arm1" not in f["brains"]
            b = f["brains"]["a1"]
            assert "active" in b and "flags" in b      # §3 transients present

        # message round-trip: dispatch out, report back (display names)
        texts = [(m["from"], m["to"], m["text"]) for m in messages]
        # sanitized behavior-level text (policy B): "move to …" / "reported: …"
        assert any(frm == "Orchestrator" and to == "Arm1" and "move to" in txt
                   for frm, to, txt in texts)
        assert any(frm == "Arm1" and to == "Orchestrator" and "reported" in txt
                   for frm, to, txt in texts)
    finally:
        bus.stop()
        mgr.il.stop()
        arm.il.stop()


def test_multiple_orders_do_not_collide_chain_iris():
    """PB-HHH regression: a 2nd order on the same brains used to crash with
    IdentityError (chain-artifact IRI collision from a constant per-brain
    task_scope). run_task's unique per-task scope must let N orders run."""
    mgr = build_brain_stack(DEVICE_PROFILES["mgr"], _DuckSession("mgr"))
    arm = build_brain_stack(DEVICE_PROFILES["arm1"], _DuckSession("arm1"))
    brains = {"mgr": mgr, "arm1": arm}
    bus = BrainBus()
    hub = _CaptureHub()
    events = DemoEvents(hub)

    runs = []

    def run_atomic(brain, target):
        runs.append((brain.device_id, target))
        return {"status": "succeeded"}

    on_command = wire_demo(
        brains, bus, events, run_atomic=run_atomic, install_datastates=True
    )

    try:
        N = 3
        for i in range(N):
            on_command("place_order", {"lines": [{"item": "sheet", "shelf": "a1"}]})
            # wait until THIS order concluded (i+1 Reported frames) before next
            for _ in range(200):
                reported = [f for f in hub.of_type("state")
                            if f.get("title") == "Reported"]
                if len(reported) >= i + 1:
                    break
                time.sleep(0.05)

        # all N orders ran the arm + concluded — no IdentityError crash
        assert len(runs) == N, f"only {len(runs)}/{N} orders reached the arm"
        reported = [f for f in hub.of_type("state") if f.get("title") == "Reported"]
        assert len(reported) == N, f"only {len(reported)}/{N} Reported frames"
        assert _episode_count(mgr) >= N      # one Episode per order, accumulating
        assert _episode_count(arm) >= N
    finally:
        bus.stop()
        mgr.il.stop()
        arm.il.stop()
