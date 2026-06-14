"""DM-6 perturbation primitive gate-check — runs INSIDE the demo container.

Validates `sim_engine.disturb_joint` against the LIVE sim (the sandbox has no
MuJoCo, and no unit test can exercise it) — the primitive task 3's recalibrate
tier is built on. Asserts the two-tier contract (design-log §25 PB-25.11):

  - DISTURB (one-shot, auto-clear) -> a MINOR divergence that a replan-from-
    current RECOVERS (next clean motion tracks its command).
  - FREEZE  (persistent clamp)     -> a MAJOR divergence that PERSISTS across a
    replan (the clamped joint can't be re-pathed away).

Uses the honest joint-level signal (`closed_loop.joint_divergence`: commanded
final qpos vs achieved) + the shipped tier `classify`. Joint-space moves (exact,
no IK residual) so the baseline is ~0.

    docker compose ... run --rm demo-backend \
        python -m robot_demo.backend.dm6_perturbation_check

Prints all divergences + ``DM-6 PERTURBATION CHECK PASS``; exits non-zero on any
tier violation. Thresholds/joint are first-cut — tune at the gate from the
printed numbers if needed (DM-3 §18 precedent).
"""

from __future__ import annotations

import sys
from typing import List

_PLAY_TIMEOUT_S = 30.0
_J = 1            # arm2 joint index to fault (0-based); must be free to move +_MOVE
_MOVE = 0.30      # commanded joint delta (rad) — large -> major when frozen
_DISTURB = 0.03   # one-shot recoverable offset (rad) — minor


def main() -> int:
    from .body_adapter import build_body_runtime
    from .closed_loop import (
        TIER_OK,
        TIER_RECALIBRATE,
        TIER_REPORT,
        classify,
        joint_divergence,
    )
    from .sim_engine import SLOT_A2

    engine, handles = build_body_runtime()
    failures: List[str] = []

    def go_home() -> None:
        engine.clear_freezes(2)
        qpos, _ = engine.generate_arm_move(2, engine.named_target(2, "home"))
        engine.submit(SLOT_A2, qpos).result(timeout=_PLAY_TIMEOUT_S)

    def commanded_move() -> float:
        """Command joint _J to move +_MOVE from the live pose; return the
        commanded-vs-achieved joint divergence (the honest signal)."""
        target = list(engine.arm_qpos(2))
        target[_J] = target[_J] + _MOVE
        qpos, _ = engine.generate_arm_move(2, target)
        engine.submit(SLOT_A2, qpos).result(timeout=_PLAY_TIMEOUT_S)
        return joint_divergence(list(qpos[-1]), list(engine.arm_qpos(2)))

    # ── baseline (no fault) — should track exactly ───────────────────────────
    go_home()
    d0 = commanded_move()
    print(f"  [DM-6] baseline divergence        = {d0:.4f} rad ({classify(d0)})")
    if classify(d0) != TIER_OK:
        failures.append(f"baseline not OK ({d0:.4f}) — joint {_J} may be clamped/limited; retune _J/_MOVE")

    # ── DISTURB: minor + recoverable ─────────────────────────────────────────
    go_home()
    engine.disturb_joint(2, _J, _DISTURB)
    d1 = commanded_move()                 # disturbed motion -> minor divergence
    d1b = commanded_move()                # replan-from-current (disturb auto-cleared) -> recovers
    print(f"  [DM-6] disturbed divergence       = {d1:.4f} rad ({classify(d1)})")
    print(f"  [DM-6] post-disturb recovery      = {d1b:.4f} rad ({classify(d1b)})")
    if classify(d1) != TIER_RECALIBRATE:
        failures.append(f"disturb not in recalibrate tier ({d1:.4f})")
    if classify(d1b) != TIER_OK:
        failures.append(f"disturb did NOT recover after replan ({d1b:.4f}) — one-shot/auto-clear broken")

    # ── FREEZE: major + persistent ───────────────────────────────────────────
    go_home()
    engine.freeze_joint(2, _J)
    d2 = commanded_move()                 # frozen motion -> major divergence
    d2b = commanded_move()                # replan-from-current can't move a clamped joint -> persists
    engine.clear_freezes(2)
    print(f"  [DM-6] frozen divergence          = {d2:.4f} rad ({classify(d2)})")
    print(f"  [DM-6] post-freeze (still frozen) = {d2b:.4f} rad ({classify(d2b)})")
    if classify(d2) != TIER_REPORT:
        failures.append(f"freeze not in report tier ({d2:.4f})")
    if classify(d2b) != TIER_REPORT:
        failures.append(f"freeze unexpectedly recovered ({d2b:.4f}) — clamp not persistent")

    if failures:
        print("  DM-6 PERTURBATION CHECK FAIL: " + "; ".join(failures))
        return 1
    print("  DM-6 PERTURBATION CHECK PASS — disturb=minor+recoverable, freeze=major+persistent")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
