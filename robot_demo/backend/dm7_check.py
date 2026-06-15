"""DM-7 live gate — runs INSIDE the demo container (real stack + WebSocket).

Exercises the teach → peer-transfer → carrier-box cooperation beat end-to-end
over the live WS (boots the real stacks like ``dm6_check``). Unlike DM-6, the
DM-7 core is graph/wire-level (no MuJoCo required): the transfer is a pure Local
write + CL registration, and the carrier-box Plan's honesty is its structure (a
real 3-leaf decompose) — so this gate passes with or without ``DEMO_BODY``.

  1. **teach** a skill on the suction arm → a "Skill taught" beat on the wire;
  2. **transfer** it arm1→arm2 (Local↔Local, no Global) → a "Peer transfer" beat
     + an Arm1→Arm2 share message;
  3. **cooperate** (carrier-box) → a real multi-leaf decompose: the manager drives
     Arm1 + Conveyor + Arm2, and the Mode-A export shows a 3-leaf plan.

    docker compose ... run --rm demo-backend python -m robot_demo.backend.dm7_check

Prints ``DM-7 GATE PASS`` + a frame summary; exits non-zero on any missing beat.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Dict, List

import websockets


async def _drive(port: int, timeout: float = 90.0) -> List[dict]:
    frames: List[dict] = []
    async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
        frames.append(json.loads(await asyncio.wait_for(ws.recv(), timeout=10)))

        async def _cmd(name, args):
            await ws.send(json.dumps({"type": "command", "name": name, "args": args}))

        async def _until(pred, t=timeout):
            end = time.time() + t
            while time.time() < end:
                try:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                except asyncio.TimeoutError:
                    continue
                frames.append(msg)
                if pred():
                    return

        def _title(t):
            return any(f.get("type") == "state" and f.get("title") == t for f in frames)

        # 1) teach on the suction arm
        await _cmd("teach", {"arm": "a1"})
        await _until(lambda: _title("Skill taught"), t=20)

        # 2) peer-transfer arm1 → arm2 (Local↔Local)
        await _cmd("transfer", {"from": "a1"})
        await _until(lambda: _title("Peer transfer"), t=20)

        # 3) carrier-box cooperation (multi-leaf decompose)
        await _cmd("cooperate", {"item": "box1"})
        await _until(lambda: _title("Reported"), t=timeout)

        # Mode-A export of the manager chain (the 3-leaf plan)
        await _cmd("export_state", {"mode": "episode-audit", "scope": "mgr"})
        await _until(lambda: any(f.get("type") == "state_snapshot" for f in frames), t=15)
    return frames


def _summary(frames: List[dict]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for f in frames:
        out[f.get("type", "?")] = out.get(f.get("type", "?"), 0) + 1
    return out


def main() -> int:
    from .bootstrap import bootstrap
    from .main import _start_ws
    from .sanitize import find_leaks

    port = int(os.environ.get("DEMO_WS_PORT", "8765"))
    print("[DM-7] booting real stacks…")
    result = bootstrap()
    if not result.ok:
        print(f"[DM-7] bootstrap not ok: {result.total_episodes}/4 episodes")
        return 1
    server, bus = _start_ws(result)
    print(f"[DM-7] WS serving on :{port}; body={'yes' if result.sim_engine else 'no'}")

    failures: List[str] = []
    try:
        frames = asyncio.run(_drive(port))
        snaps = [f for f in frames if f.get("type") == "state_snapshot"]
        msgs = [(m.get("from"), m.get("to")) for m in frames if m.get("type") == "message"]
        titles = [f.get("title") for f in frames if f.get("type") == "state" and f.get("title")]

        def need(cond, label):
            failures.append(label) if not cond else print(f"  [DM-7] ✓ {label}")

        # ── teach ────────────────────────────────────────────────────────────
        need("Skill taught" in titles, "teach beat on the wire")

        # ── peer-transfer (Local↔Local) ──────────────────────────────────────
        need("Peer transfer" in titles, "peer-transfer beat on the wire")
        need(("Arm1", "Arm2") in msgs, "Arm1→Arm2 share message (no central server)")

        # ── carrier-box cooperation: real 3-leaf decompose + coordination ────
        need(("Orchestrator", "Arm1") in msgs
             and ("Orchestrator", "Conveyor") in msgs
             and ("Orchestrator", "Arm2") in msgs,
             "manager coordinated all three devices (load → bridge → receive)")
        mgr = None
        for s in snaps:
            if "mgr" in ((s.get("snapshot") or {}).get("brains") or {}):
                mgr = s["snapshot"]
                break
        need(mgr is not None, "manager export snapshot present")
        if mgr:
            meps = ((mgr.get("brains") or {}).get("mgr") or {}).get("episodes") or []
            three_leaf = [e for e in meps
                          if len(e.get("reasoning", {}).get("pipelines", []) or []) == 3]
            need(bool(three_leaf), "carrier-box episode: a real 3-leaf plan")
            if three_leaf:
                need(len(three_leaf[0]["reasoning"].get("milestones", []) or []) == 4,
                     "3-leaf plan has 4 milestones (root + 3)")

        need(find_leaks(snaps) == [] and find_leaks({"frames": frames}) == [],
             "wire + snapshots: no IP tokens leaked (policy B)")

        print(f"[DM-7] frame summary: {_summary(frames)}")
    finally:
        server.stop()
        bus.stop()
        if result.sim_engine is not None:
            result.sim_engine.stop()
        for brain in result.brains.values():
            brain.il.stop()

    if failures:
        print("DM-7 GATE FAIL: " + "; ".join(failures))
        return 1
    print("DM-7 GATE PASS")
    return 0


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)  # bypass MuJoCo/GL teardown segfault (body=yes), like dm5/dm6_check
