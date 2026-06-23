"""Grounding leaf — pixels → point-set → ordered boundary trace (PLAN §5).

Two ``perception``-family capacities (DATASTATE_MARKER don't-know). This
is the **swappable / domain-specific** entry: licensed as an auditable
symbolic leaf *only* because the shapes are clean line-art (PLAN §1/§11).
A messy-image variant swaps in a path-2 neural leaf behind the SAME typed
``point-set`` output (the quarantine seam — skill-acq §6.2).

Bodies follow the core contract (verified against ``call_capacity``):
inputs are splatted as ``**kw`` keyed by **DataState IRI** (IRIs contain
``:`` so they cannot be named params), ``context`` is a plain dict for
read bodies, and each body returns an explicit ``{output_iri: value}``
dict (so a dict-valued output like a Shape is never mistaken for the
output-mapping itself).

Abstain policy here is deliberately thin: the leaf only emits
:class:`DontKnow` when it cannot order *any* boundary (degenerate input).
The real gates live downstream where PLAN §10 D puts them — the **fit
gate** at ``point-set → segments`` and the **structure gate** at the
polygon predicate — so the clean negatives (circle / open / near-miss)
flow through the chain to the gate that should reject them, exercising
the whole loop rather than short-circuiting at the leaf.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from mindsos_capacity import Capacity, CATEGORY_PERCEPTION

from .ontology import PIXELS, POINT_SET, BOUNDARY_TRACE
from .render import Image
from .signals import DontKnow

Point = Tuple[float, float]

PIXELS_TO_POINTS_IRI = f"capacity:{CATEGORY_PERCEPTION}:pixels_to_points"
POINTS_TO_BOUNDARY_IRI = f"capacity:{CATEGORY_PERCEPTION}:points_to_boundary"


# ── bodies ─────────────────────────────────────────────────────────────

def _pixels_to_points(**kw):
    """Threshold the binary raster into a foreground point-set.

    Trivial for clean synthetic line-art (the licensed leaf); the typed
    ``point-set`` output is the contract a future neural leaf must match.
    """
    img: Image = kw[PIXELS.iri]
    pts: List[Point] = [(float(x), float(y)) for (x, y) in img.fg]
    return {POINT_SET.iri: pts}


def _angle_boundary(points: List[Point]) -> List[Point]:
    """Angle-sort around the centroid → a cyclic boundary ordering.

    Robust for the **convex** polygon family (m1): every boundary point is
    star-visible from the centroid, so polar-angle order is exactly the
    boundary order — immune to the nearest-neighbour stranding that
    fabricates spurious corners. Non-convex / concave shapes need a
    connectivity tracer instead; that is a later swap (the leaf is the
    swappable element — PLAN §5). Topological validity (single closed
    stroke vs disconnected/open) is judged separately by the control
    loop's structure gate (see ``topology.py``), not fabricated here.
    """
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return sorted(points, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))


def _points_to_boundary(**kw):
    """Order the point-set into a cyclic boundary trace, or abstain."""
    pts: List[Point] = list(kw[POINT_SET.iri])
    # de-duplicate (raster thickening can repeat coords)
    uniq = list(dict.fromkeys((round(x, 3), round(y, 3)) for (x, y) in pts))
    if len(uniq) < 3:
        return {BOUNDARY_TRACE.iri: DontKnow(reason="trace",
                                             detail=f"only {len(uniq)} points")}
    return {BOUNDARY_TRACE.iri: _angle_boundary(uniq)}


# ── registration ───────────────────────────────────────────────────────

def register_leaf(cl, session) -> Tuple[str, str]:
    """Register both grounding-leaf capacities Local. Returns their IRIs."""
    pix = Capacity(
        name="pixels_to_points",
        category=CATEGORY_PERCEPTION,
        inputs=(PIXELS.iri,),
        outputs=(POINT_SET.iri,),
        implementation=_pixels_to_points,
        description="grounding leaf: binary raster -> foreground point-set (swappable)",
    )
    bnd = Capacity(
        name="points_to_boundary",
        category=CATEGORY_PERCEPTION,
        inputs=(POINT_SET.iri,),
        outputs=(BOUNDARY_TRACE.iri,),
        implementation=_points_to_boundary,
        description="grounding leaf: point-set -> ordered cyclic boundary trace",
    )
    cl.register_capacity(pix, session=session)
    cl.register_capacity(bnd, session=session)
    return pix.iri, bnd.iri
