"""DM-6 Fork-2 + PB-25.15 gate experiment — runs INSIDE the demo container.

NOT a pass/fail gate: an **experiment that prints a verdict** to settle two
DM-6 design forks against the *real* sim (design-log §25), because neither can
be answered in the MuJoCo-free sandbox:

  Fork 2  — does a frozen arm2 joint exist whose freeze degrades a **fine**
            cylinder grasp while a **coarse** carrier (box) place still
            reaches?  If YES, the scenario-as-written ("arm2 keeps carriers,
            only fine-grasp disabled") is *physically earned*; if NO, DM-6
            falls back to fleet-level partial (arm2 down → reroute) with zero
            rework (the capability-typed gap is identical either way).

  PB-25.15 — is the arm1 / arm2 reach genuinely disjoint, so a reroute of a
            cylinder staged at arm2's feeder needs a conveyor re-stage?

    docker compose ... run --rm demo-backend \
        python -m robot_demo.backend.dm6_reach_experiment

HONEST SIGNAL (design-log §25 finding): ``MotionOutcome.ok`` is freeze-
INSENSITIVE (it checks the planned path + jerk + submit, never the achieved
pose), and ``set_grip`` accepts a 30 cm proximity gate — so a clamped joint
does NOT make a reach report failure. This experiment therefore measures the
GROUND-TRUTH achieved TCP pose (``site_xpos``) against the target, cache-busted
(direct ``generate_arm_reach`` + ``submit``, never the cached BodyHandle path),
resetting to home between trials. ``probe_actuators`` confirms each freeze is
live. Expected to iterate at the gate (DM-3 §18 / DM-5 §24 precedent: the
stand-offs are first-cut).
"""

from __future__ import annotations

import sys
from typing import List, Optional, Tuple

_PLAY_TIMEOUT_S = 30.0
#: a reach counts as "degraded" if the frozen TCP error exceeds the healthy
#: baseline by more than this (m). Generous vs the 30 cm grasp gate — reported
#: numbers let a human re-judge.
_DEGRADE_MARGIN_M = 0.05


def _classify_items(poses: dict) -> Tuple[Optional[str], Optional[str]]:
    from .feasibility import item_kind

    box_item = tube_item = None
    for name in sorted(poses):
        k = item_kind(name)
        if k == "box" and box_item is None:
            box_item = name
        elif k == "tube" and tube_item is None:
            tube_item = name
    return box_item, tube_item


def main() -> int:
    import numpy as np

    from .body_adapter import build_body_runtime
    from .sim_engine import SLOT_A2

    engine, handles = build_body_runtime()
    a2 = handles["arm2"]
    sid = engine._cell.arm[2]["sid"]  # TCP site id for the achieved-pose read

    def tcp_xyz() -> "np.ndarray":
        with engine._lock:
            return engine._cell.d.site_xpos[sid].copy()

    def move_home() -> None:
        engine.clear_freezes(2)
        home = engine.named_target(2, "home")
        qpos, _ = engine.generate_arm_move(2, home)
        engine.submit(SLOT_A2, qpos).result(timeout=_PLAY_TIMEOUT_S)

    def reach_err(target_xyz, R) -> float:
        """Achieved TCP error (m) for a fresh reach from the current live pose
        — bypasses the BodyHandle cache (the cache key ignores the freeze)."""
        qpos, _ = engine.generate_arm_reach(2, target_xyz, R)
        engine.submit(SLOT_A2, qpos).result(timeout=_PLAY_TIMEOUT_S)
        return float(np.linalg.norm(tcp_xyz() - np.asarray(target_xyz, float)))

    # ── PB-25.15 — reach disjointness (data fact + conveyor bridge) ──────────
    from .seeds import EMBODIMENT

    r1, r2 = set(EMBODIMENT["arm1"]["reach"]), set(EMBODIMENT["arm2"]["reach"])
    shared = r1 & r2
    bridge = ("belt_a1" in EMBODIMENT["conv"]["reach"]
              and "belt_a2" in EMBODIMENT["conv"]["reach"])
    restage = (not shared) and bridge
    print(f"  [DM-6] arm1.reach={sorted(r1)}  arm2.reach={sorted(r2)}  shared={sorted(shared)}")
    print(f"  [DM-6] conv bridges belt_a1<->belt_a2: {bridge}")
    print(f"  PB-25.15 VERDICT — reroute needs a conveyor re-stage: {restage} "
          f"({'full re-stage (chosen a)' if restage else 'pre-stage neutral (fall back b)'})")

    # ── Fork 2 — coarse vs fine achieved-pose error, per frozen arm2 joint ───
    poses = a2.sense_poses()
    box_item, tube_item = _classify_items(poses)
    print(f"  [DM-6] bodies={sorted(poses)}  box_item={box_item}  tube_item={tube_item}")
    if box_item is None or tube_item is None:
        print("  FORK-2 VERDICT — INCONCLUSIVE: need both a box-kind and a tube-kind "
              "body in the live scene. Adjust the scene/item names and re-run.")
        return 0

    coarse_xyz, coarse_R = engine.cell_target(2, "r1c1", "seat")     # gross place
    fine_xyz, fine_R = engine.item_grasp_target(2, tube_item, "grasp")  # fine grasp

    move_home()
    coarse_base = reach_err(coarse_xyz, coarse_R)
    move_home()
    fine_base = reach_err(fine_xyz, fine_R)
    print(f"  [DM-6] healthy TCP error — coarse(place)={coarse_base * 1000:.0f} mm  "
          f"fine(grasp)={fine_base * 1000:.0f} mm")

    n_joints = len(engine.arm_qpos(2))
    print(f"  [DM-6] probing {n_joints} arm2 joints "
          f"(degrade margin = {_DEGRADE_MARGIN_M * 1000:.0f} mm over healthy)")
    print("        joint | frozen? | coarse err (Δ) | fine err (Δ)")
    earned: List[int] = []
    for j in range(n_joints):
        move_home()
        engine.freeze_joint(2, j)
        probe = engine.probe_actuators(2)
        frozen_seen = f"a2_joint{j + 1}" in probe["frozen_joints"]
        move_home()  # probe_actuators restores pose; freeze persists
        engine.freeze_joint(2, j)
        c_err = reach_err(coarse_xyz, coarse_R)
        move_home()
        engine.freeze_joint(2, j)
        f_err = reach_err(fine_xyz, fine_R)
        engine.clear_freezes(2)

        c_deg = c_err > coarse_base + _DEGRADE_MARGIN_M
        f_deg = f_err > fine_base + _DEGRADE_MARGIN_M
        if f_deg and not c_deg:
            earned.append(j)
        flag = "  <-- earns scenario-as-written" if (f_deg and not c_deg) else ""
        print(f"        a2_joint{j + 1:<2} | {str(frozen_seen):<5}   | "
              f"{c_err * 1000:6.0f} mm {'DEG' if c_deg else '   '} | "
              f"{f_err * 1000:6.0f} mm {'DEG' if f_deg else '   '}{flag}")

    if earned:
        names = ", ".join(f"a2_joint{j + 1}" for j in earned)
        print(f"  FORK-2 VERDICT — SCENARIO-AS-WRITTEN EARNED (option b): freezing "
              f"{{{names}}} degrades the fine cylinder grasp while coarse carrier "
              f"placement still reaches. DM-6 may keep 'arm2 still grips carriers' — "
              f"pin the fault to one of these joints.")
    else:
        print("  FORK-2 VERDICT — FLEET-LEVEL PARTIAL (option a): no single frozen "
              "joint degrades fine grasp while sparing coarse placement. DM-6 reroutes "
              "on any arm2 fault (no 'arm2 keeps carriers' claim). Zero rework — the "
              "capability-typed gap is identical.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
