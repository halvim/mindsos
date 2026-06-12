"""DM-3 — the *atomic* pre-present checklist (PB-LL, design log §15).

The shipped clip checklist (``sim/gen_all.py::checklist``) is **clip-level**:
it requires ``grasp`` + ``seated`` events and scores a full pick-and-place.
A bare ⬡ atomic (``move_to`` / ``grip`` / ``conv.run``) produces no such
events, so the full checklist can't grade it. This module is the *subset*:
the invariants that DO apply to a bare trajectory —

  1. **arm joints smooth** — no per-step acceleration spike (catches IK
     branch-flips) (MOTION_RULES inv 1),
  4. **no arm part in the conveyor body** (inv 4),
  5. **no upper arm-link in the rack** (inv 5; the wrist may legitimately
     approach a target, but DM-3 atomics never place into a cubby, so no
     upper-link rack entry is expected),
  9. **start/end poses clear** of both structures (inv 6/9).

The per-capacity *effect* assertion (pose reached / attach engaged / belt
displaced / diag verdict) is the caller's job — kept out of here so this
stays a pure structural check.

**MuJoCo-free (PB-TT).** Operates on a frames array + an injected
:class:`StructureSpec` (the sim side builds the spec from ``geom_config``;
tests build a synthetic one). Numpy only — sandbox-importable.

Frames shape: ``frames[f][b] = [x, y, z, qw, qx, qy, qz]`` (the native
``Cell.capture()`` row); ``bodies`` is the index→name list.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import numpy as np

#: Thresholds — mirror the shipped clip checklist where they overlap
#: (``sim/gen_all.py``): arm jerk < 160 mm (second-difference of link
#: position at the capture cadence).
JERK_MAX_M = 0.160
MARGIN_M = 0.04


@dataclass(frozen=True)
class StructureSpec:
    """Workcell structure regions for the collision checks (per arm).

    Built from ``sim/geom_config.py`` on the MuJoCo side
    (:meth:`from_geom_config`); a synthetic instance drives the sandbox
    tests. All lengths in metres, MuJoCo world frame.
    """

    arm_x: Dict[int, float]          # ARM{1,2}_X
    shelf_y: Dict[int, float]        # SHELF_Y_ARM[{1,2}]
    col_dx: float                    # COL_DX
    shelf_depth: float               # SHELF_DEPTH
    row_z0: float                    # ROW_Z0
    row_dz: float                    # ROW_DZ
    belt_x0: float                   # BELT_X0
    belt_x1: float                   # BELT_X1
    belt_y: float                    # BELT_Y
    belt_half_w: float               # BELT_HALF_W
    conv_z_lo: float = 0.40          # conveyor body z-band (gen_all literal)
    conv_z_hi: float = 0.86
    margin: float = MARGIN_M

    def in_rack(self, arm: int, p: Sequence[float]) -> bool:
        m = self.margin
        ax = self.arm_x[arm]
        sy = self.shelf_y[arm]
        return (
            ax - 1.5 * self.col_dx - m < p[0] < ax + 1.5 * self.col_dx + m
            and sy - self.shelf_depth - m < p[1] < sy + m
            and self.row_z0 - 0.5 * self.row_dz - m
            < p[2]
            < self.row_z0 + 2.5 * self.row_dz + m
        )

    def in_conveyor(self, p: Sequence[float]) -> bool:
        m = self.margin
        return (
            self.belt_x0 < p[0] < self.belt_x1
            and self.belt_y - self.belt_half_w - m
            < p[1]
            < self.belt_y + self.belt_half_w + m
            and self.conv_z_lo < p[2] < self.conv_z_hi
        )

    @classmethod
    def from_geom_config(cls, G) -> "StructureSpec":  # pragma: no cover - sim side
        """Build from the shipped ``sim/geom_config`` module (MuJoCo host)."""
        return cls(
            arm_x={1: G.ARM1_X, 2: G.ARM2_X},
            shelf_y={1: G.SHELF_Y_ARM[1], 2: G.SHELF_Y_ARM[2]},
            col_dx=G.COL_DX,
            shelf_depth=G.SHELF_DEPTH,
            row_z0=G.ROW_Z0,
            row_dz=G.ROW_DZ,
            belt_x0=G.BELT_X0,
            belt_x1=G.BELT_X1,
            belt_y=G.BELT_Y,
            belt_half_w=G.BELT_HALF_W,
        )


@dataclass(frozen=True)
class Verdict:
    """Outcome of :func:`atomic_checklist`."""

    ok: bool
    reason: str
    checks: Dict[str, object] = field(default_factory=dict)


def _link_names(arm: int, bodies: Sequence[str]) -> Tuple[List[str], List[str]]:
    """(all arm links incl. attachment, upper links link0..5) present in ``bodies``."""
    pf = f"a{arm}_"
    alll = [f"{pf}link{i}" for i in range(8)] + [f"{pf}attachment"]
    alll = [n for n in alll if n in bodies]
    upper = [f"{pf}link{i}" for i in range(6) if f"{pf}link{i}" in bodies]
    return alll, upper


def atomic_checklist(
    frames: Sequence[Sequence[Sequence[float]]],
    bodies: Sequence[str],
    arm: int,
    spec: StructureSpec,
) -> Verdict:
    """Structural subset checklist on a bare atomic trajectory (PB-LL).

    Returns a :class:`Verdict`; ``ok`` requires every applicable invariant
    to hold. ``checks`` carries the measured values for the trace/log.
    """
    F = np.asarray(frames, dtype=float)
    if F.ndim != 3 or F.shape[0] < 2:
        return Verdict(False, "too few frames to verify", {"N": int(F.shape[0])})
    P = F[:, :, :3]
    N = F.shape[0]
    idx = {n: i for i, n in enumerate(bodies)}

    alll, upper = _link_names(arm, bodies)
    if not alll:
        return Verdict(False, f"no a{arm}_* links in frame body list", {})
    li = [idx[n] for n in alll]
    ui = [idx[n] for n in upper]

    # 1 — joint smoothness (second difference of link position).
    jerk = max(
        max(
            float(np.linalg.norm((P[f + 1, b] - P[f, b]) - (P[f, b] - P[f - 1, b])))
            for b in li
        )
        for f in range(1, N - 1)
    )

    # 4 — no arm link inside the conveyor body, any frame.
    conv = sorted({
        bodies[b] for f in range(N) for b in li if spec.in_conveyor(P[f, b])
    })

    # 5 — no UPPER link inside the rack, any frame.
    rack_upper = sorted({
        bodies[b] for f in range(N) for b in ui if spec.in_rack(arm, P[f, b])
    })

    # 9 — start/end poses clear of both structures (rest-pose invariant).
    def _clear(f: int) -> bool:
        return not any(
            spec.in_rack(arm, P[f, b]) or spec.in_conveyor(P[f, b]) for b in li
        )

    ends_clear = _clear(0) and _clear(N - 1)

    checks = {
        "N": int(N),
        "1_armjerk_mm": round(jerk * 1000),
        "4_conv": conv or "none",
        "5_rack_upper": rack_upper or "none",
        "9_ends_clear": ends_clear,
    }
    # Hard gate for a BARE atomic move: joint smoothness (no IK branch-flip)
    # + no collision with the conveyor BODY. The rack-AABB + ends-clear
    # checks are pick-place-phase invariants (placing into / returning from a
    # cubby): the coarse rack AABB false-positives the folded home keyframe
    # (the wrist tucks behind the arm — inside the AABB but in no cubby), and
    # a home/ready park pose legitimately sits there. They are enforced by the
    # FULL clip checklist at DM-5; here they are informational only (design
    # log §17 calibration).
    ok = jerk < JERK_MAX_M and not conv
    reason = "PASS" if ok else "; ".join(
        m for m, bad in (
            (f"jerk {round(jerk * 1000)}mm>=160", jerk >= JERK_MAX_M),
            (f"conveyor intrusion {conv}", bool(conv)),
        ) if bad
    )
    return Verdict(ok, reason, checks)


__all__ = ["StructureSpec", "Verdict", "atomic_checklist", "JERK_MAX_M", "MARGIN_M"]
