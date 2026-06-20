"""DM-3 ↔ DM-4 pose-frame projection (WS contract §2.3 / §8, design-log §16).

The UI consumes a ``pose`` frame with **only**:
  * ``items[name] = [x, y]``  — top-down cell view, the UI's frozen world box
  * ``eff[id]     = [x, y] | null``  — effector targets

(The ``bodies`` 3D-transform field was dropped: the UI confirmed it consumes
only ``items``/``eff`` and builds both its 2D and three.js views from those —
``bodies`` has no v1 consumer. WS-contract answer #3, 2026-06-12.)

**Coordinate mapping (affine, owned by the backend — answer #2).** The UI's
cell view is a *stylized top-down* schematic, deliberately NOT the sim
geometry (its arms sit at ±0.65; the sim's at ±1.2). So the backend maps
sim-world ``(x, y)`` → the UI's frozen box via a per-axis affine
``screen = a·world + b``, fitted from physical anchors captured from the live
sim (2026-06-12):

  * x: sim arm bases ±1.2  → UI ARM ±0.65   ⟹  ax = 0.65/1.2,  bx = 0
  * y: sim arm base −0.45  → UI −0.45,  and
       sim item-rest 0.10  → UI shelf row −0.77  ⟹  ay = −0.5818, by = −0.7118

Region-accurate is sufficient until ``place_at_cell`` (DM-5); the UI draws
items at whatever ``[x, y]`` we send (no cell snapping). The frozen UI box is
``XR=[-1.35,1.35]``, ``YR=[-1.02,0.34]`` — every demo body lands inside it
after this transform. MuJoCo-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

#: contract item-id → sim body name. box2 is intentionally omitted — the UI
#: does not render it (answer #4); emitting it would be invisible noise.
ITEM_BODIES: Dict[str, str] = {
    "box1": "box1",
    "sheet1": "sheet1",
    "tube1": "tube1",
}

#: contract effector-id → sim body name (the DM-3 grip refs).
EFF_BODIES: Dict[str, str] = {
    "a1": "a1_suction",
    "a2": "a2g_base",
}


@dataclass(frozen=True)
class Affine2D:
    """Top-down ``screen = a·world + b`` per axis (sim-world x,y → UI box)."""

    ax: float = 0.5417
    bx: float = 0.0
    ay: float = -0.5818
    by: float = -0.7118

    def project(self, world: Sequence[float]) -> List[float]:
        return [round(self.ax * world[0] + self.bx, 4),
                round(self.ay * world[1] + self.by, 4)]


#: The fitted demo affine (sim → UI frozen box). Default for all projections.
DEMO_AFFINE = Affine2D()


def _index(bodies: Sequence[str]) -> Dict[str, int]:
    return {n: i for i, n in enumerate(bodies)}


def project_pose(
    frame: Sequence[Sequence[float]],
    bodies: Sequence[str],
    *,
    affine: Affine2D = DEMO_AFFINE,
) -> Dict[str, object]:
    """Project one captured ``frame`` (rows ``[x,y,z,qw,qx,qy,qz]`` per body,
    indexed by ``bodies``) into the contract's ``items``/``eff`` pose fields.

    Returns ``{"items":…, "eff":…}`` (no ``type``/``t`` — the caller adds
    those). Both are 2D top-down ``[x, y]`` via the affine. ``eff`` ids absent
    from the frame are emitted as ``None`` (contract §2.3 / §3)."""
    idx = _index(bodies)

    items: Dict[str, List[float]] = {}
    for cid, bname in ITEM_BODIES.items():
        if bname in idx:
            items[cid] = affine.project(frame[idx[bname]][:2])

    eff: Dict[str, Optional[List[float]]] = {}
    for cid, bname in EFF_BODIES.items():
        eff[cid] = affine.project(frame[idx[bname]][:2]) if bname in idx else None

    return {"items": items, "eff": eff}


__all__ = ["ITEM_BODIES", "EFF_BODIES", "Affine2D", "DEMO_AFFINE", "project_pose"]
