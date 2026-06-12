"""DM-4 live gate — runs INSIDE the demo container (real stack + WebSocket).

The authoritative DM-4 gate (plan §8), greppable like ``dm3_check``: it boots
the real per-device stacks (``bootstrap``), wires the BrainBus + comms +
WS server (``main._start_ws``), then connects a real WebSocket client and
drives ``place_order`` — asserting the gate flow lands as live frames:

    place_order → mgr lifecycle → comms.dispatch → arm lifecycle runs move_to
                → comms.report → mgr,  visible as state + message frames.

    docker compose ... run --rm demo-backend python -m robot_demo.backend.dm4_check

Prints ``DM-4 GATE PASS`` + a frame summary; exits non-zero on any missing
beat. With ``DEMO_BODY=0`` the move runs as the no-body stub (still a full
dispatch→report round-trip; no pose frames) — the body path is the default.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Dict, List

import websockets


async def _drive(port: int, timeout: float = 45.0) -> List[dict]:
    frames: List[dict] = []
    async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
        hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        frames.append(hello)
        await ws.send(json.dumps({
            "type": "command", "name": "place_order",
            "args": {"lines": [{"item": "sheet", "shelf": "a1"}]},
        }))
        end = time.time() + timeout
        while time.time() < end:
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            except asyncio.TimeoutError:
                continue
            frames.append(msg)
            if msg.get("type") == "state" and msg.get("title") == "Reported":
                break
    return frames


def _summary(frames: List[dict]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for f in frames:
        out[f.get("type", "?")] = out.get(f.get("type", "?"), 0) + 1
    return out


def main() -> int:
    from .bootstrap import bootstrap
    from .main import _start_ws

    port = int(os.environ.get("DEMO_WS_PORT", "8765"))
    print("[DM-4] booting real stacks…")
    result = bootstrap()
    if not result.ok:
        print(f"[DM-4] bootstrap not ok: {result.total_episodes}/4 episodes")
        return 1
    server, bus = _start_ws(result)
    print(f"[DM-4] WS serving on :{port}; body={'yes' if result.sim_engine else 'no(stub)'}")

    failures: List[str] = []
    try:
        frames = asyncio.run(_drive(port))
        states = [f for f in frames if f.get("type") == "state"]
        messages = [f for f in frames if f.get("type") == "message"]
        titles = [f.get("title") for f in states if f.get("title")]
        texts = [(m.get("from"), m.get("to"), m.get("text")) for m in messages]

        def need(cond, label):
            if not cond:
                failures.append(label)
            else:
                print(f"  [DM-4] ✓ {label}")

        need(frames and frames[0].get("type") == "hello", "hello on connect")
        need("Order placed" in titles, "state: Order placed")
        need("Assign task" in titles, "state: Assign task")
        need(any(f == "Orchestrator" and t == "Arm1" and "move to" in (x or "")
                 for f, t, x in texts), "message: Orchestrator→Arm1 assign move")
        need(any("a1" in s.get("brains", {}) and s["brains"]["a1"].get("active")
                 for s in states), "state: a1 active (arm executing)")
        need(any(f == "Arm1" and t == "Orchestrator" and "reported" in (x or "")
                 for f, t, x in texts), "message: Arm1→Orchestrator report")
        need("Reported" in titles, "state: Reported")
        if result.sim_engine is not None:
            need(any(f.get("type") == "pose" for f in frames), "pose frames streaming")

        print(f"[DM-4] frame summary: {_summary(frames)}")
    finally:
        server.stop()
        bus.stop()
        for brain in result.brains.values():
            brain.il.stop()

    if failures:
        print("DM-4 GATE FAIL: " + "; ".join(failures))
        return 1
    print("DM-4 GATE PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
