"""DM-6 live gate — runs INSIDE the demo container (real stack + WebSocket).

Exercises the closed-loop verify→replan/report beat end-to-end over the live
sim (the sandbox has no MuJoCo). Boots the real stacks + WS (like ``dm5_check``),
then drives two feasible orders to the suction arm with a fault injected first:

  1. a **minor** perturbation (``disturb_joint``) → the arm's verified-approach
     recalibrates-from-current and RECOVERS → a ``succeeded`` Episode carrying a
     real ``reasoning.replans`` (the recalibration);
  2. a **major** fault (``freeze_joint``) → the verified-approach REPORTS →
     self-diagnosis writes the gap → a real ``dont_know`` Episode with populated,
     sanitized ``reasoning.blame``.

    docker compose ... run --rm demo-backend python -m robot_demo.backend.dm6_check

Prints ``DM-6 GATE PASS`` + a frame summary; exits non-zero on any missing beat.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Dict, List

import websockets

_BOX = {"lines": [{"item": "box", "shelf": "a1",
                   "pos": [{"type": "shelf", "pos": "center"}]}]}
_SHEET = {"lines": [{"item": "sheet", "shelf": "a1",
                     "pos": [{"type": "shelf", "pos": "center"}]}]}


async def _drive(port: int, timeout: float = 90.0) -> List[dict]:
    frames: List[dict] = []
    async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
        frames.append(json.loads(await asyncio.wait_for(ws.recv(), timeout=10)))

        async def _cmd(name, args):
            await ws.send(json.dumps({"type": "command", "name": name, "args": args}))

        async def _order_until_reports(args, want_reports):
            await _cmd("place_order", args)
            end = time.time() + timeout
            while time.time() < end:
                try:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                except asyncio.TimeoutError:
                    continue
                frames.append(msg)
                reports = [f for f in frames if f.get("type") == "message"
                           and "reported" in (f.get("text") or "")]
                if len(reports) >= want_reports:
                    return

        async def _export(scope):
            await _cmd("export_state", {"mode": "episode-audit", "scope": scope})
            end = time.time() + 15.0
            while time.time() < end:
                try:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                except asyncio.TimeoutError:
                    continue
                frames.append(msg)
                if msg.get("type") == "state_snapshot":
                    return

        # 1) MINOR perturbation on the suction arm → recalibrate + recover (arm-side)
        await _cmd("inject_fault", {"scope": "a1", "kind": "disturb", "joint": 1})
        await _order_until_reports(_BOX, 1)
        await _cmd("inject_fault", {"scope": "a1", "kind": "clear"})

        # 2) MAJOR fault, item has NO alternate grasp (sheet = suction-only) →
        #    arm reports + Manager dead-ends honestly (no reroute possible).
        await _cmd("inject_fault", {"scope": "a1", "kind": "freeze", "joint": 1})
        await _order_until_reports(_SHEET, 2)
        await _cmd("inject_fault", {"scope": "a1", "kind": "clear"})

        # 3) MAJOR fault, item HAS an alternate grasp (box → jaw) → Manager
        #    reroutes (the reroute decision fires = a real manager ReplanRecord;
        #    the physical recovery needs the conv re-stage = task 7b).
        await _cmd("inject_fault", {"scope": "a1", "kind": "freeze", "joint": 1})
        await _order_until_reports(_BOX, 3)
        await _cmd("inject_fault", {"scope": "a1", "kind": "clear"})

        # Mode-A exports: the arm chain (recalibrate/report) + the manager chain
        # (reroute decision + dead-end).
        await _export("a1")
        await _export("mgr")
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
    print("[DM-6] booting real stacks…")
    result = bootstrap()
    if not result.ok:
        print(f"[DM-6] bootstrap not ok: {result.total_episodes}/4 episodes")
        return 1
    if result.sim_engine is None:
        print("[DM-6] no body (DEMO_BODY=0) — the closed-loop beat needs the live sim")
        return 1
    server, bus = _start_ws(result)
    print(f"[DM-6] WS serving on :{port}; body=yes")

    failures: List[str] = []
    try:
        frames = asyncio.run(_drive(port))
        snaps = [f for f in frames if f.get("type") == "state_snapshot"]

        def need(cond, label):
            failures.append(label) if not cond else print(f"  [DM-6] ✓ {label}")

        def _snap_for(scope):
            for s in snaps:
                if scope in ((s.get("snapshot") or {}).get("brains") or {}):
                    return s["snapshot"]
            return None

        need(len(snaps) >= 2, "two export snapshots (arm + manager)")
        a1 = _snap_for("a1")
        mgr = _snap_for("mgr")

        # ── arm chain: recalibrate (recovery) + report (fault) ───────────────
        need(a1 is not None, "arm snapshot present")
        if a1:
            eps = ((a1.get("brains") or {}).get("a1") or {}).get("episodes") or []
            recov = [e for e in eps
                     if e.get("value", {}).get("outcome_classification") == "succeeded"
                     and e.get("reasoning", {}).get("replans")]
            need(bool(recov), "arm recovery episode: succeeded + real replan (recalibrated)")
            fault = [e for e in eps
                     if e.get("value", {}).get("outcome_classification") == "dont_know"
                     and e.get("reasoning", {}).get("blame")]
            need(bool(fault), "arm fault episode: dont_know + blame")

        # ── manager chain: physical recovery (reroute) + honest dead-end ─────
        need(mgr is not None, "manager snapshot present")
        if mgr:
            meps = ((mgr.get("brains") or {}).get("mgr") or {}).get("episodes") or []
            # recovery: box fault → conv re-stage → healthy arm completes →
            # succeeded WITH a real reroute ReplanRecord on the manager chain.
            recov = [e for e in meps
                     if e.get("value", {}).get("outcome_classification") == "succeeded"
                     and e.get("reasoning", {}).get("replans")]
            need(bool(recov), "manager recovery episode: succeeded + reroute ReplanRecord")
            # dead-end: sheet fault, no alternate grasp → honest dont-know + blame.
            dead = [e for e in meps
                    if e.get("value", {}).get("outcome_classification") == "dont_know"
                    and e.get("reasoning", {}).get("blame")]
            need(bool(dead), "manager dead-end episode: dont_know + blame")

        need(find_leaks(snaps) == [], "snapshots: no IP tokens leaked")

        print(f"[DM-6] frame summary: {_summary(frames)}")
    finally:
        server.stop()
        bus.stop()
        if result.sim_engine is not None:
            result.sim_engine.stop()
        for brain in result.brains.values():
            brain.il.stop()

    if failures:
        print("DM-6 GATE FAIL: " + "; ".join(failures))
        return 1
    print("DM-6 GATE PASS")
    return 0


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)  # bypass MuJoCo/GL teardown segfault (body=yes), like dm5_check
