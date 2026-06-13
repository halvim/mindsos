"""DM-5 live gate — runs INSIDE the demo container (real stack + WebSocket).

The authoritative DM-5 gate (plan §8), greppable like ``dm4_check``: boots the
real per-device stacks (``bootstrap`` — which registers the ⬡ atomics AND the ◆
assembled ``pick``/``place_at_cell``/``conv.stage_at``, and seeds each arm's
embodiment), wires the BrainBus + comms + WS (with the DM-5 allocator), then
drives two orders over a real WebSocket:

  1. a **feasible** order with a real ``pos`` clause → the Plan ▸ Resolve panel
     narrows (9→1) and the matched arm runs the ◆ assembled pick→place;
  2. a **wrong-gripper** order (tube → the suction arm) → the embodiment gate
     fires: a ``GATED`` cap badge + a real ``dont_know`` report, exported as a
     Mode-A snapshot with ``outcome_classification:"dont_know"`` + populated,
     sanitized ``reasoning.dont_know``/``blame``.

    docker compose ... run --rm demo-backend python -m robot_demo.backend.dm5_check

Prints ``DM-5 GATE PASS`` + a frame summary; exits non-zero on any missing beat.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Dict, List

import websockets


async def _drive(port: int, timeout: float = 60.0) -> List[dict]:
    frames: List[dict] = []
    async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
        frames.append(json.loads(await asyncio.wait_for(ws.recv(), timeout=10)))

        async def _order_until_reported(args, want_reports):
            await ws.send(json.dumps(
                {"type": "command", "name": "place_order", "args": args}))
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

        # 1) feasible: box → centre on the suction arm's shelf (real resolve + place)
        await _order_until_reported(
            {"lines": [{"item": "box", "shelf": "a1",
                        "pos": [{"type": "shelf", "pos": "center"}]}]}, 1)
        # 2) wrong-gripper: tube → suction arm = honest refusal
        await _order_until_reported(
            {"lines": [{"item": "tube", "shelf": "a1",
                        "pos": [{"type": "shelf", "pos": "center"}]}]}, 2)

        # 3) Mode-A export of the ARM (a1) — the refusal lives in its chain
        await ws.send(json.dumps({"type": "command", "name": "export_state",
                                  "args": {"mode": "episode-audit", "scope": "a1"}}))
        end = time.time() + 15.0
        while time.time() < end:
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            except asyncio.TimeoutError:
                continue
            frames.append(msg)
            if msg.get("type") == "state_snapshot":
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
    from .sanitize import find_leaks

    port = int(os.environ.get("DEMO_WS_PORT", "8765"))
    print("[DM-5] booting real stacks…")
    result = bootstrap()
    if not result.ok:
        print(f"[DM-5] bootstrap not ok: {result.total_episodes}/4 episodes")
        return 1
    server, bus = _start_ws(result)
    print(f"[DM-5] WS serving on :{port}; body={'yes' if result.sim_engine else 'no(stub)'}")

    failures: List[str] = []
    try:
        frames = asyncio.run(_drive(port))
        states = [f for f in frames if f.get("type") == "state"]
        resolves = [f for f in frames if f.get("type") == "resolve"]
        snaps = [f for f in frames if f.get("type") == "state_snapshot"]

        def need(cond, label):
            failures.append(label) if not cond else print(f"  [DM-5] ✓ {label}")

        # ── Plan ▸ Resolve producer (9→…→1) ──────────────────────────────
        need(bool(resolves), "resolve frame emitted")
        if resolves:
            r0 = resolves[0]
            need(len(r0.get("stages", [])) >= 2, "resolve: ≥2 narrowing stages")
            need(r0.get("winner") is not None, "resolve: a winner cell")
            need(find_leaks(r0) == [], "resolve: no IP tokens")

        # ── embodiment gate: a GATED badge surfaced ──────────────────────
        gated = [s for s in states if any(
            cap == ["pick", "GATED"]
            for b in s.get("brains", {}).values() for cap in b.get("caps", []))]
        need(bool(gated), "state: GATED badge (wrong-gripper refusal)")

        # ── Mode-A export: the arm's real dont-know ──────────────────────
        need(bool(snaps), "export → state_snapshot reply")
        if snaps:
            snap = snaps[0]["snapshot"]
            need(snap.get("kind") == "episode-audit", "snapshot kind episode-audit")
            eps = ((snap.get("brains") or {}).get("a1") or {}).get("episodes") or []
            dk = [e for e in eps
                  if e.get("value", {}).get("outcome_classification") == "dont_know"]
            need(bool(dk), "snapshot: a real dont_know episode")
            if dk:
                rsn = dk[0].get("reasoning", {})
                need(bool(rsn.get("dont_know")), "snapshot: dont_know populated")
                need(bool(rsn.get("blame")), "snapshot: blame populated")
            need(find_leaks(snaps[0]) == [], "snapshot: no IP tokens leaked")

        # ── the ◆ assembled capacities are registered (graph-honest) ─────
        from mindsos_capacity.identifiers import capacity_iri
        a1 = result.brains["arm1"]
        for nm in ("a1.pick", "a1.place_at_cell"):
            iri = capacity_iri("mechanism", nm)
            try:
                present = a1.cl.get_declaration(iri) is not None
            except Exception:
                present = False
            need(present, f"registered ◆ {nm}")

        print(f"[DM-5] frame summary: {_summary(frames)}")
    finally:
        server.stop()
        bus.stop()
        if result.sim_engine is not None:
            result.sim_engine.stop()
        for brain in result.brains.values():
            brain.il.stop()

    if failures:
        print("DM-5 GATE FAIL: " + "; ".join(failures))
        return 1
    print("DM-5 GATE PASS")
    return 0


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)  # bypass MuJoCo/GL teardown segfault (body=yes), like dm4_check
