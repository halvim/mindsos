"""DM-3 ↔ DM-4 pose-frame projection (WS contract §2.3, design log §16).

The UI consumes a ``pose`` frame:
  * ``items[name] = [x, y]``  (2D cell view; consumed now)
  * ``eff[id]     = [x, y] | null``  (effector targets; consumed now)
  * ``bodies[name] = [x, y, z, qw, qx, qy, qz]``  (reserved 3D robot view)

``Cell.capture()`` already emits ``[x, y, z, qw, qx, qy, qz]`` per body in
metres (MuJoCo world frame, quat wxyz) — so ``bodies`` is the native output
and the source of truth. The 2D ``items``/``eff`` are a **front-elevation
projection** ``screen_x ← world_x``, ``screen_y ← world_z`` (so shelf-row
motion reads vertically), through an affine ``screen = a·world + b``.

The affine constants are a placeholder (identity = raw metres) until the
UI side confirms the cell view's coordinate box; baking them is a one-line
change here, so DM-4 wraps the result in ``{"type":"pose", "t":…, …}`` with
no reshape. MuJoCo-free (PB-TT).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

#: contract item-id → sim body name. Sim also has ``box2`` (each arm has its
#: own box in the load/convey flow) — included so the cell view can show it.
ITEM_BODIES: Dict[str, str] = {
    "box1": "box1",
    "box2": "box2",
    "sheet1": "sheet1",
    "tube1": "tube1",
}

#: contract effector-id → sim body name (the checklist's grip refs). The TCP
#: *site* (``a{1,2}_tcp``) is not in the captured frame; switch to it here if
#: the UI wants the pinch point.
EFF_BODIES: Dict[str, str] = {
    "a1": "a1_suction",
    "a2": "a2g_base",
}


@dataclass(frozen=True)
class Affine2D:
    """``screen = a·world + b`` per axis. Identity = raw metres (placeholder).

    ``sx = ax * world_x + bx`` ; ``sy = az * world_z + bz`` (front elevation).
    Confirm constants with the UI side, then set them here (design log §16).
    """

    ax: float = 1.0
    bx: float = 0.0
    az: float = 1.0
    bz: float = 0.0

    def project(self, world: Sequence[float]) -> List[float]:
        return [self.ax * world[0] + self.bx, self.az * world[2] + self.bz]


IDENTITY_AFFINE = Affine2D()


def _index(bodies: Sequence[str]) -> Dict[str, int]:
    return {n: i for i, n in enumerate(bodies)}


def project_pose(
    frame: Sequence[Sequence[float]],
    bodies: Sequence[str],
    *,
    affine: Affine2D = IDENTITY_AFFINE,
    body_allowlist: Optional[Sequence[str]] = None,
) -> Dict[str, object]:
    """Project one captured ``frame`` into the contract's pose fields.

    Returns ``{"items":…, "eff":…, "bodies":…}`` (no ``type``/``t`` — DM-4
    adds those). ``items``/``eff`` are 2D (affine over world x,z); ``bodies``
    is the raw 3D ``[x,y,z,qw,qx,qy,qz]`` for the item/eff/arm bodies (or
    ``body_allowlist`` when given).
    """
    idx = _index(bodies)

    items: Dict[str, List[float]] = {}
    for cid, bname in ITEM_BODIES.items():
        if bname in idx:
            items[cid] = affine.project(frame[idx[bname]][:3])

    eff: Dict[str, Optional[List[float]]] = {}
    for cid, bname in EFF_BODIES.items():
        eff[cid] = affine.project(frame[idx[bname]][:3]) if bname in idx else None

    if body_allowlist is None:
        want = set(ITEM_BODIES.values()) | set(EFF_BODIES.values())
        want |= {n for n in bodies if n.startswith(("a1_link", "a2_link"))}
    else:
        want = set(body_allowlist)
    bodies_out: Dict[str, List[float]] = {
        n: [round(float(x), 4) for x in frame[idx[n]][:7]]
        for n in bodies
        if n in want
    }

    return {"items": items, "eff": eff, "bodies": bodies_out}


__all__ = [
    "ITEM_BODIES",
    "EFF_BODIES",
    "Affine2D",
    "IDENTITY_AFFINE",
    "project_pose",
]
