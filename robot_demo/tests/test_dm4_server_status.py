"""DM-4 — Server panel (``server_status``) frame shape + sanitization.

The frame deviates from the originally-locked §D keys per the IP-sanitization
addendum (design-log PB-3/4): no ``mindsos_version``; ``persistence.falkordb``
→ ``storage:"connected"``; ``globals_persisted`` → ``state_saved``; the raw
``user`` is dropped (display-name only).
"""

from __future__ import annotations

from robot_demo.backend.frames import server_status_frame
from robot_demo.backend.sanitize import find_leaks
from robot_demo.backend.wiring import make_status_provider


def test_server_status_frame_sanitized():
    f = server_status_frame(
        [{"device_id": "mgr", "since": "2026-06-12T00:00:00+00:00"},
         {"device_id": "arm1", "since": "2026-06-12T00:00:00+00:00"}],
        uptime_s=42, state_saved=True,
    )
    assert f["type"] == "server_status"
    assert f["storage"] == "connected"        # PB-3 — not "Falkor"
    assert f["state_saved"] is True
    assert f["uptime_s"] == 42
    # PB-3 — banned/renamed keys are gone from the wire.
    assert "mindsos_version" not in f
    assert "falkordb" not in f and "persistence" not in f and "globals_persisted" not in f
    # PB-4 — sessions carry display names only; raw user dropped.
    assert {s["brain"] for s in f["sessions"]} == {"Orchestrator", "Arm1"}
    assert all("user" not in s for s in f["sessions"])
    assert find_leaks(f) == []


def test_status_provider_from_result():
    class _Result:
        brains = {"mgr": 1, "arm1": 1, "arm2": 1, "conv": 1}
        persisted_global = True

    provider = make_status_provider(_Result())
    f = provider()
    assert f["type"] == "server_status"
    assert len(f["sessions"]) == 4
    assert {s["brain"] for s in f["sessions"]} == {
        "Orchestrator", "Arm1", "Arm2", "Conveyor"}
    assert f["state_saved"] is True
    assert f["uptime_s"] >= 0
    assert find_leaks(f) == []
