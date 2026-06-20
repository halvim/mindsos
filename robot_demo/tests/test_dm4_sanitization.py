"""DM-4 — IP-sanitization guard (policy B, ROBOT_DEMO_IP_SANITIZATION.md).

The wire must leave the backend already clean — the UI does not re-sanitize.
This drives the real wired flow, collects every emitted frame, and asserts no
MindsOS implementation/IP token appears in any participant-visible text, and
that `message` parties use only the sanitized display vocabulary.
"""

from __future__ import annotations

import time

from robot_demo.backend.brain import build_brain_stack, run_task
from robot_demo.backend.profiles import DEVICE_PROFILES
from robot_demo.backend.frames import DemoEvents, server_status_frame
from robot_demo.backend.bus import BrainBus
from robot_demo.backend.wiring import wire_demo
from robot_demo.backend.sanitize import find_leaks
from robot_demo.backend.serializer import build_episode_audit_snapshot


class _CaptureHub:
    def __init__(self):
        self.frames = []

    def publish(self, frame):
        self.frames.append(frame)


class _DuckSession:
    def __init__(self, u):
        self.user_id = u; self.session_id = f"s-{u}"
        self.actor_role = "user"; self.capabilities = frozenset()

    def has(self, c):
        return True


# Implementation/IP substrings that must never reach the wire (case-insensitive).
BANNED = [
    "falkor", "sqlite", "server.db", "redis",
    "episodic_memories", "promoted-pipelines", "capacity-state",
    "register_capacity", "writeable", "datastate", "data state",
    "hintset", "mappingresult", "pipelinerun", "taskrun", "task_run",
    "evt_", "can_write", "can_read",
    "move_to", "place_at_cell", "load_into_box",
    "query_capabilities", "dispatch", "promote(",
    "comms.", "capacity:", "datastate:", "task-pattern:",
    "intelligence_mm", "run_lifecycle",
]

# The only allowed `message` party display names (sanitized vocabulary).
ALLOWED_PARTIES = {
    "User", "Orchestrator", "Arm1", "Arm2", "Conveyor",
    "Fleet", "Library", "Demonstration",
}


def _text_fields(frame):
    out = []
    for k in ("title", "narr", "text"):
        if isinstance(frame.get(k), str):
            out.append(frame[k])
    for b in (frame.get("brains") or {}).values():
        for k in ("intent", "decision"):
            if isinstance(b.get(k), str):
                out.append(b[k])
    return out


def test_no_ip_tokens_on_the_wire():
    mgr = build_brain_stack(DEVICE_PROFILES["mgr"], _DuckSession("mgr"))
    arm = build_brain_stack(DEVICE_PROFILES["arm1"], _DuckSession("arm1"))
    bus = BrainBus()
    hub = _CaptureHub()
    events = DemoEvents(hub)
    on_command = wire_demo({"mgr": mgr, "arm1": arm}, bus, events,
                           run_atomic=lambda b, t: {"status": "succeeded"},
                           install_datastates=True)
    try:
        on_command("place_order", {"lines": [{"item": "sheet", "shelf": "a1"}]})
        for _ in range(200):
            if any(f.get("title") == "Reported" for f in hub.frames
                   if f.get("type") == "state"):
                break
            time.sleep(0.05)

        leaks = []
        for f in hub.frames:
            for txt in _text_fields(f):
                low = txt.lower()
                for tok in BANNED:
                    if tok in low:
                        leaks.append((tok, txt))
            if f.get("type") == "message":
                for party in (f.get("from"), f.get("to")):
                    if party not in ALLOWED_PARTIES:
                        leaks.append(("party", party))
        assert not leaks, "IP leaks on the wire:\n" + "\n".join(
            f"  [{tok}] {txt!r}" for tok, txt in leaks)
    finally:
        bus.stop()
        mgr.il.stop()
        arm.il.stop()


def test_l5_snapshot_and_server_status_are_clean():
    """The DM-4-added surfaces (Mode-A ``state_snapshot`` + ``server_status``)
    must leave the backend already clean. Uses the canonical banned list in
    ``sanitize`` (the same one the producers enforce) so the test and the wire
    can't drift."""
    b = build_brain_stack(DEVICE_PROFILES["mgr"], _DuckSession("mgr"))
    try:
        run_task(b, {"text": "scrub"}, task_id="t").result(timeout=30)
        snapshot = build_episode_audit_snapshot(b)
        status = server_status_frame(
            [{"device_id": "mgr", "since": "2026-06-12T00:00:00+00:00"}],
            uptime_s=1, state_saved=True,
        )
        # values-only recursive guard (PB-7): every banned token, every nested
        # string value, both new frames.
        assert find_leaks({"type": "state_snapshot", "snapshot": snapshot}) == []
        assert find_leaks(status) == []
    finally:
        b.il.stop()
