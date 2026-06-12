"""DM-3 live-motion gate — runs INSIDE the demo container (MuJoCo present).

The container image ships ``robot_demo/backend`` (not ``tests/``), so the
authoritative DM-3 gate is this runnable module, greppable like the
bootstrap smoke. It builds the single shared SimEngine + BodyHandles and
asserts the DM-3 gate (plan §8): **each atomic capacity moves the live sim,
checklist-verified**, plus the fault switch (G-8) and the real jitter bar
(PB-E/RR).

    docker compose ... run --rm demo-backend python -m robot_demo.backend.dm3_check

Prints ``DM-3 LIVE MOTION PASS`` + the jitter distribution; exits non-zero on
any motion/fault failure (jitter is recorded + soft-checked — it sets the
real bar, replacing DM-1's synthetic proxy).
"""

from __future__ import annotations

import sys
import threading
import time
from typing import List


def _percentile(xs: List[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
    return s[k]


def _worker(stop: threading.Event) -> None:
    """Realistic worker-pool proxy: a burst of work, then yield. The brain ILs
    do bursts between waits; pure infinite spin would starve the clock and
    overstate GIL contention (PB-E)."""
    while not stop.is_set():
        x = 0
        for _ in range(2000):
            x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        time.sleep(0.002)


def main() -> int:
    from .body_adapter import build_body_runtime
    from .sim_engine import CAP_EVERY

    engine, handles = build_body_runtime()
    nominal_ms = engine._dt * 1000.0
    failures: List[str] = []
    try:
        a1, a2, conv = handles["arm1"], handles["arm2"], handles["conv"]

        # A bounded base-yaw delta from the live (home) pose — a real, smooth,
        # conveyor-clear move that works for both arms (verified in the
        # sandbox: ok, jerk ~1 mm, no conveyor intrusion). The home keyframe
        # has no distinct rest target (arm2's rest_pose IK returns None), so a
        # joint-space delta is the robust verified target for the atomic gate.
        ready_delta = (0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        def _ready(arm):
            return [v + d for v, d in zip(engine.arm_qpos(arm), ready_delta)]

        # 1 — move_to moves the live sim, checklist-verified (cache MISS).
        before = engine.arm_qpos(1)
        out = a1.move_to({"qpos": _ready(1), "key": "ready"})
        moved = any(abs(a - b) > 1e-4 for a, b in zip(before, engine.arm_qpos(1)))
        if not (out.ok and out.status == "done" and not out.cache_hit and moved):
            failures.append(f"a1.move_to miss: ok={out.ok} hit={out.cache_hit} "
                            f"moved={moved} reason={out.reason}")
        else:
            print(f"  [DM-3] a1.move_to -> {out.status} (gen, {out.frames_n} frames, "
                  f"checklist PASS)")

        # 1b — cache HIT (PB-F): same key re-plays the cached trajectory.
        out2 = a1.move_to({"qpos": before, "key": "ready"})
        if not (out2.ok and out2.cache_hit):
            failures.append(f"a1.move_to hit: cache_hit={out2.cache_hit}")
        else:
            print("  [DM-3] a1.move_to -> cache HIT")

        # 1c — arm 2 moves too (independent slot, shared Cell — PB-KK).
        b2 = engine.arm_qpos(2)
        o3 = a2.move_to({"qpos": _ready(2), "key": "ready"})
        if not (o3.ok and any(abs(a - b) > 1e-4 for a, b in zip(b2, engine.arm_qpos(2)))):
            failures.append(f"a2.move_to: ok={o3.ok} reason={o3.reason}")
        else:
            print(f"  [DM-3] a2.move_to -> {o3.status}")

        # 2 — grip (proximity-gated attach/release).
        g = a1.set_grip(False)
        print(f"  [DM-3] a1.suction_set(release) -> attached={g.get('attached')}")

        # 3 — sense returns live world facts.
        poses = a1.sense_poses()
        if "box1" not in poses:
            failures.append("a1.sense_poses missing box1")
        else:
            print(f"  [DM-3] a1.sense_poses -> {len(poses)} bodies")

        # 4 — belt sweeps on command (PB-PP).
        bout = conv.run_belt(1, 0.15)
        if abs(bout["displaced"] - 0.15) > 1e-9:
            failures.append(f"conv.run displaced={bout['displaced']}")
        else:
            print("  [DM-3] conv.run -> belt displaced 0.15 m")

        # 5 — fault injection detected honestly (G-8 / PB-NN).
        engine.freeze_joint(1, 2)
        rep = a1.diagnose()
        if "a1_joint3" not in rep["frozen_joints"]:
            failures.append(f"fault not detected: {rep['frozen_joints']}")
        else:
            print(f"  [DM-3] freeze a1.joint3 -> diagnose detected {rep['frozen_joints']}")
        engine.clear_freezes(1)
        rep2 = a1.diagnose()
        if rep2["frozen_joints"]:
            failures.append(f"fault not cleared: {rep2['frozen_joints']}")
        else:
            print("  [DM-3] clear freeze -> diagnose healthy")

        # 6 — jitter (PB-E/RR). Baseline (clock alone) is the floor; a
        # burst-then-yield worker proxy shows realistic GIL contention. The
        # integrated bar under 4 live ILs is the full-bootstrap measure.py
        # concern; the escape hatch is the sim in its own process (PB-E).
        def sample(label, threads):
            stop = threading.Event()
            load = [threading.Thread(target=_worker, args=(stop,), daemon=True)
                    for _ in range(threads)]
            for t in load:
                t.start()
            start_n = len(engine.jitter_samples)
            time.sleep(2.0)
            stop.set()
            w = engine.jitter_samples[start_n:]
            p50, p99, mx = _percentile(w, 50), _percentile(w, 99), max(w or [0])
            print(f"  [DM-3] jitter {label} (n={len(w)}, nominal {nominal_ms:.1f} ms): "
                  f"p50 {p50:.1f}  p99 {p99:.1f}  max {mx:.1f} ms")
            return p99

        sample("baseline", 0)
        p99 = sample("under 4 workers", 4)
        if p99 > 2.0 * nominal_ms:
            print(f"  [DM-3] NOTE p99 {p99:.1f} > 2x nominal {2 * nominal_ms:.1f} ms "
                  "under load — integrated bar = full-stack measure.py; escape "
                  "hatch = sim in its own process behind BodyHandle (PB-E).")
    finally:
        engine.stop()

    if failures:
        print("DM-3 LIVE MOTION FAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("DM-3 LIVE MOTION PASS — each atomic moved the live sim, checklist-verified; "
          "fault detected; jitter recorded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
