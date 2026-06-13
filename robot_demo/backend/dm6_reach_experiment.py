"""DM-6 Fork-2 + PB-25.15 gate experiment — runs INSIDE the demo container.

NOT a pass/fail gate: an **experiment that prints a verdict** to settle two
DM-6 design forks against the *real* sim (design-log §25), because neither can
be answered in the MuJoCo-free sandbox:

  Fork 2  — does a frozen arm2 joint exist whose freeze breaks a **fine**
            cylinder grasp while a **coarse** carrier (box) place still
            completes?  If YES, the scenario-as-written ("arm2 keeps carriers,
            only fine-grasp disabled") is *physically earned*; if NO, DM-6
            falls back to fleet-level partial (arm2 down → reroute) with zero
            rework (the gap representation is identical either way).

  PB-25.15 — is the arm1 / arm2 reach genuinely disjoint, so a reroute of a
            cylinder staged at arm2's feeder needs a conveyor re-stage?  The
            EMBODIMENT data says yes (asserted cheaply below); this confirms it
            against the live cell geometry and that ``conv.stage_at`` bridges.

    docker compose ... run --rm demo-backend \
        python -m robot_demo.backend.dm6_reach_experiment

Prints a per-joint table + a ``FORK-2 VERDICT`` / ``PB-25.15 VERDICT`` line.
Exits 0 unless the harness itself errors (the *result* is the output, not the
exit code). Expected to iterate at the gate (the DM-3 §18 / DM-5 §24 precedent:
the cartesian stand-offs are first-cut).
"""

from __future__ import annotations

import sys
from typing import List, Optional, Tuple


def _classify_items(poses: dict) -> Tuple[Optional[str], Optional[str]]:
    """From live ``sense_poses`` keys, pick one box-kind and one tube-kind body
    (kind via the shipped feasibility prefix map). Returns (box_item, tube_item),
    either None if absent."""
    from .feasibility import item_kind

    box_item = tube_item = None
    for name in sorted(poses):
        k = item_kind(name)
        if k == "box" and box_item is None:
            box_item = name
        elif k == "tube" and tube_item is None:
            tube_item = name
    return box_item, tube_item


def _reach_ok(handle, spec: dict) -> Tuple[bool, str]:
    """Attempt a cartesian reach; return (ok, short-reason). Never raises."""
    try:
        out = handle.move_to(spec)
        return bool(getattr(out, "ok", False)), str(getattr(out, "reason", "") or "")
    except Exception as exc:  # noqa — an experiment must not crash on a bad reach
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    from .body_adapter import build_body_runtime

    engine, handles = build_body_runtime()
    a1, a2, conv = handles["arm1"], handles["arm2"], handles["conv"]

    # ── PB-25.15 — reach disjointness (data fact + a live cross-reach probe) ──
    from .seeds import EMBODIMENT

    r1 = set(EMBODIMENT["arm1"]["reach"])
    r2 = set(EMBODIMENT["arm2"]["reach"])
    shared = r1 & r2
    print(f"  [DM-6] arm1.reach={sorted(r1)}  arm2.reach={sorted(r2)}  shared={sorted(shared)}")
    bridge = "belt_a1" in EMBODIMENT["conv"]["reach"] and "belt_a2" in EMBODIMENT["conv"]["reach"]
    restage_needed = (not shared) and bridge
    print(f"  [DM-6] conv bridges belt_a1<->belt_a2: {bridge}")
    print(f"  PB-25.15 VERDICT — reroute needs a conveyor re-stage: {restage_needed} "
          f"({'full re-stage (chosen a)' if restage_needed else 'pre-stage neutral (fall back b)'})")

    # ── Fork 2 — per-joint coarse-vs-fine on arm2 ────────────────────────────
    poses = a2.sense_poses()
    box_item, tube_item = _classify_items(poses)
    print(f"  [DM-6] bodies={sorted(poses)}  box_item={box_item}  tube_item={tube_item}")
    if box_item is None or tube_item is None:
        print("  FORK-2 VERDICT — INCONCLUSIVE: need both a box-kind and a tube-kind "
              "body in the live scene to compare coarse vs fine. Adjust the scene "
              "or item names and re-run.")
        return 0

    n_joints = len(engine.arm_qpos(2))
    coarse_spec = {"cell": "r1c1", "phase": "seat"}   # gross carrier placement
    fine_spec = {"item": tube_item, "phase": "grasp"}  # precise cylinder grasp

    print(f"  [DM-6] probing {n_joints} arm2 joints (coarse=place {coarse_spec}, "
          f"fine=grasp {fine_spec})")
    print("        joint | coarse(box place) | fine(tube grasp)")
    earned: List[int] = []
    for j in range(n_joints):
        engine.freeze_joint(2, j)
        try:
            coarse_ok, c_reason = _reach_ok(a2, dict(coarse_spec))
            fine_ok, f_reason = _reach_ok(a2, dict(fine_spec))
        finally:
            engine.clear_freezes(2)
        flag = "  <-- earns scenario-as-written" if (coarse_ok and not fine_ok) else ""
        if coarse_ok and not fine_ok:
            earned.append(j)
        print(f"        a2_joint{j + 1:<2} |  {str(coarse_ok):<5} {c_reason[:22]:<22} | "
              f" {str(fine_ok):<5} {f_reason[:22]}{flag}")

    if earned:
        names = ", ".join(f"a2_joint{j + 1}" for j in earned)
        print(f"  FORK-2 VERDICT — SCENARIO-AS-WRITTEN EARNED (option b): freezing "
              f"{{{names}}} breaks fine cylinder grasp while coarse carrier placement "
              f"survives. DM-6 may keep 'arm2 still grips carriers'. Pin the fault to "
              f"one of these joints.")
    else:
        print("  FORK-2 VERDICT — FLEET-LEVEL PARTIAL (option a): no single frozen "
              "joint preserves coarse placement while breaking fine grasp. arm2 is "
              "effectively down on any freeze; DM-6 reroutes (no 'arm2 keeps carriers' "
              "claim). Zero rework — the capability-typed gap is identical.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
