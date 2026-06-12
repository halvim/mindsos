"""DM-4 — Mode-A L5 export (episode-audit) serializer + command path.

Asserts the snapshot is well-formed against the §D schema, the reasoning
lineage is linked (PB-13 opaque tokens preserve ref↔iri edges), the internal
refs are nulled (PB-14), ``task_input`` is captured (PB-17), the honest empties
are present (PB-5/18), and NOTHING internal leaks on the wire (PB-7/13).
"""

from __future__ import annotations

import threading

from robot_demo.backend.brain import build_brain_stack, run_task
from robot_demo.backend.bus import BrainBus
from robot_demo.backend.frames import DemoEvents, FrameHub
from robot_demo.backend.profiles import DEVICE_PROFILES
from robot_demo.backend.sanitize import find_leaks
from robot_demo.backend.serializer import (
    KIND_EPISODE_AUDIT,
    build_episode_audit_snapshot,
)
from robot_demo.backend.wiring import wire_demo

_VALUE_FIELDS = {
    "task_input_ref", "mm_root_ref", "task_pattern_iri",
    "outcome_classification", "crash_marker", "consolidated_at",
}


class _Duck:
    def __init__(self, u):
        self.user_id = u; self.session_id = f"s-{u}"
        self.actor_role = "user"; self.capabilities = frozenset()

    def has(self, c):
        return False


def test_episode_audit_snapshot_wellformed_and_clean():
    b = build_brain_stack(DEVICE_PROFILES["mgr"], _Duck("mgr"))
    try:
        out = run_task(b, {"text": "audit-payload"}, task_id="t").result(timeout=30)
        assert out.status == "succeeded"

        snap = build_episode_audit_snapshot(b)
        assert snap["snapshot_version"] == 1
        assert snap["kind"] == KIND_EPISODE_AUDIT
        assert "mindsos_version" not in snap                    # PB-3
        brec = snap["brains"]["mgr"]
        assert brec["device_type"] == "manager"
        assert len(brec["episodes"]) >= 1
        assert len(brec["memories"]) >= 1

        e = brec["episodes"][0]
        assert set(e["value"]) == _VALUE_FIELDS
        assert e["value"]["task_input_ref"] is None             # PB-14
        assert e["value"]["mm_root_ref"] is None                # PB-14
        assert e["value"]["outcome_classification"] == "succeeded"
        assert e["task_input"] == {"text": "audit-payload"}     # PB-17 captured
        assert e["problem_trace"] == []                         # PB-5

        r = e["reasoning"]
        # full lifecycle skeleton present (all real artifacts).
        assert r["hint_set"]["iri"].startswith("n")
        assert r["hint_set"]["hints"] == {}                     # v0 hint.global
        assert r["mapping_result"]["mapping_confidence"] == 1.0
        assert r["task_run"]["iri"].startswith("n")
        assert r["milestones"] and r["pipelines"] and r["pipeline_runs"]
        assert r["steps"] and r["steps"][0]["capacity_iri"] == "execute step"  # PB-18
        # honest empties on the happy path (PB-18).
        assert r["replans"] == [] and r["blame"] is None and r["dont_know"] is None

        # PB-13 — the token rewrite preserves lineage: the PipelineRun's
        # task_run_ref still equals the TaskRun's iri after tokenization.
        assert r["pipeline_runs"][0]["task_run_ref"] == r["task_run"]["iri"]

        # PB-7/13 — clean wire.
        assert find_leaks(snap) == []
    finally:
        b.il.stop()


def test_export_command_responds_targeted_snapshot():
    mgr = build_brain_stack(DEVICE_PROFILES["mgr"], _Duck("mgr"))
    arm = build_brain_stack(DEVICE_PROFILES["arm1"], _Duck("arm1"))
    bus = BrainBus()
    events = DemoEvents(FrameHub())
    on_command = wire_demo(
        {"mgr": mgr, "arm1": arm}, bus, events,
        run_atomic=lambda b, t: {"status": "succeeded"},
        install_datastates=True,
    )
    try:
        # seed an episode deterministically (avoid the async bus timing).
        run_task(mgr, {"text": "x"}, task_id="seed").result(timeout=30)

        # contract scope "mgr" → mgr brain; the reply is targeted via respond.
        box = {}
        done = threading.Event()

        def respond(frame):
            box["frame"] = frame
            done.set()

        on_command("export_state", {"mode": "episode-audit", "scope": "mgr"}, respond)
        assert done.wait(15)
        f = box["frame"]
        assert f["type"] == "state_snapshot"
        assert f["snapshot"]["kind"] == "episode-audit"
        assert f["snapshot"]["brains"]["mgr"]["episodes"]
        assert find_leaks(f) == []

        # unknown scope → honest error snapshot, not silence.
        box.clear(); done.clear()
        on_command("export_state", {"mode": "episode-audit", "scope": "nope"}, respond)
        assert done.wait(5)
        assert box["frame"]["snapshot"]["error"] == "unknown brain"
    finally:
        bus.stop()
        mgr.il.stop()
        arm.il.stop()
