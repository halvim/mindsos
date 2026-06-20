"""DM-4 — frame layer tests (no websockets, no domain stack; 3.10 sandbox).

DemoEvents frame shaping (aliasing, §3 transients, contract shapes) + the
FrameHub thread→asyncio bridge (publish from a worker thread, fan out on the
loop thread).
"""

from __future__ import annotations

import asyncio
import threading

from robot_demo.backend.frames import DemoEvents, FrameHub


class _CaptureHub:
    """A hub stand-in that records frames synchronously (no loop)."""

    def __init__(self):
        self.frames = []

    def publish(self, frame):
        self.frames.append(frame)


# ── DemoEvents shaping ────────────────────────────────────────────────
def test_state_aliases_device_ids_and_sets_transients():
    hub = _CaptureHub()
    ev = DemoEvents(hub)
    ev.state(
        {"arm1": {"intent": "Place Sheet", "decision": "move_to ✓", "active": True}},
        title="Cooperative execution", narr="the arm runs the move",
    )
    f = hub.frames[-1]
    assert f["type"] == "state"
    assert "a1" in f["brains"] and "arm1" not in f["brains"]   # aliased
    b = f["brains"]["a1"]
    assert b["active"] is True
    assert b["flags"] == []                                    # §3 default present
    assert f["title"] == "Cooperative execution"
    assert f["beat"] == 0


def test_state_beat_monotonic_and_optional_fields_omitted():
    hub = _CaptureHub()
    ev = DemoEvents(hub)
    ev.state({"mgr": {"intent": "plan"}})
    ev.state({"mgr": {"intent": "dispatch", "active": True}})
    assert [f["beat"] for f in hub.frames] == [0, 1]
    assert "title" not in hub.frames[0]      # not supplied → omitted
    assert "items" not in hub.frames[0]


def test_message_maps_display_names():
    hub = _CaptureHub()
    ev = DemoEvents(hub)
    ev.message("mgr", "arm1", "dispatch(move_to)")
    f = hub.frames[-1]
    assert f == {"type": "message", "from": "Orchestrator", "to": "Arm1",
                 "text": "dispatch(move_to)", "t": f["t"]}


def test_pose_defaults_eff_null():
    hub = _CaptureHub()
    ev = DemoEvents(hub)
    ev.pose(items={"box1": [0.1, -0.6]})
    f = hub.frames[-1]
    assert f["type"] == "pose"
    assert f["items"] == {"box1": [0.1, -0.6]}
    assert f["eff"] == {"a1": None, "a2": None}


def test_reset_resets_beat():
    hub = _CaptureHub()
    ev = DemoEvents(hub)
    ev.state({"mgr": {"intent": "x"}})
    ev.reset()
    ev.state({"mgr": {"intent": "y"}})
    assert hub.frames[-1]["beat"] == 0          # beat counter reset


def test_hello_frame_shape():
    f = DemoEvents.hello_frame(beats_total=4)
    assert f["type"] == "hello"
    assert f["brains"] == ["mgr", "a1", "a2", "conv"]
    assert f["beats_total"] == 4


# ── FrameHub thread→asyncio bridge ────────────────────────────────────
def test_framehub_bridges_worker_thread_to_loop():
    results = []

    async def main():
        loop = asyncio.get_event_loop()
        hub = FrameHub()
        hub.bind_loop(loop)
        q = hub.register()
        # publish from a DIFFERENT (worker) thread — the PB-ZZ path
        threading.Thread(
            target=lambda: hub.publish({"type": "state", "beat": 7}), daemon=True
        ).start()
        frame = await asyncio.wait_for(q.get(), timeout=2.0)
        results.append(frame)
        assert hub.client_count() == 1
        hub.unregister(q)
        assert hub.client_count() == 0

    asyncio.run(main())
    assert results == [{"type": "state", "beat": 7}]


def test_framehub_publish_before_loop_is_noop():
    hub = FrameHub()  # no loop bound
    hub.publish({"type": "state"})  # must not raise


# ── pose stream wiring (sim → pose frames) ────────────────────────────
def test_wire_pose_stream_projects_and_emits():
    from robot_demo.backend.wiring import wire_pose_stream

    class _FakeEngine:
        bodies = ["box1", "sheet1", "tube1", "a1_suction", "a2g_base"]
        def __init__(self):
            self._cb = None
        def subscribe(self, cb):
            self._cb = cb
        def tick(self, frame):
            self._cb(frame, self.bodies)

    hub = _CaptureHub()
    ev = DemoEvents(hub)
    eng = _FakeEngine()
    wire_pose_stream(eng, ev)
    # one sim frame (sim-world rows): box1 at sim (0.7,-0.6)
    eng.tick([[0.7, -0.6, 0.5, 1, 0, 0, 0], [-1.1, -0.6, 0.6, 1, 0, 0, 0],
              [1.1, 0.1, 0.9, 1, 0, 0, 0], [-0.7, -0.7, 0.9, 1, 0, 0, 0],
              [0.7, -0.62, 0.9, 1, 0, 0, 0]])
    f = hub.frames[-1]
    assert f["type"] == "pose"
    assert f["items"]["box1"] == [0.3792, -0.3627]   # affine-mapped, in box
    assert f["eff"]["a1"] == [-0.3792, -0.3045]
    assert "bodies" not in f
