"""Stroke topology — the structure-gate evidence (PLAN §10 D gate-b).

The fit gate (``point-set → segments``) rejects curves; the **structure
gate** rejects strokes that are not a single closed loop. Because the
convex-family boundary tracer (``leaf._angle_boundary``) *fabricates* a
closed ring by polar-sorting, closure cannot be read off the fitted
polygon — it must be measured on the raster directly:

- **single component** (8-connectivity) — ``open_strokes`` has 2 → fail.
- **closed loop** — a clean 1px closed outline has no degree-1 endpoint
  pixels; ``near_miss`` leaves a gap → 2 endpoints → fail.

The control loop (not this module, not the predicate) combines these into
the abstain/re-segment verdict (G5/G6).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Tuple

from .render import Image

Pixel = Tuple[int, int]

_NEIGHBORS = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
              (0, 1), (1, -1), (1, 0), (1, 1)]


@dataclass(frozen=True)
class Topology:
    n_components: int
    n_endpoints: int

    @property
    def single_component(self) -> bool:
        return self.n_components == 1

    @property
    def closed(self) -> bool:
        return self.n_endpoints == 0

    @property
    def is_single_closed_stroke(self) -> bool:
        return self.single_component and self.closed


def _degree(px: Pixel, fg: FrozenSet[Pixel]) -> int:
    x, y = px
    return sum((x + dx, y + dy) in fg for dx, dy in _NEIGHBORS)


def _count_components(fg: FrozenSet[Pixel]) -> int:
    seen = set()
    comps = 0
    for start in fg:
        if start in seen:
            continue
        comps += 1
        stack = [start]
        seen.add(start)
        while stack:
            x, y = stack.pop()
            for dx, dy in _NEIGHBORS:
                nb = (x + dx, y + dy)
                if nb in fg and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
    return comps


def analyze(image: Image) -> Topology:
    fg = image.fg
    n_end = sum(1 for px in fg if _degree(px, fg) == 1)
    return Topology(n_components=_count_components(fg), n_endpoints=n_end)
