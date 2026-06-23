"""{segments, vertices} → polygon — the shape verifier (PLAN §5, G5).

Registered as a ``predicate`` (NO_DONT_KNOW): it returns a **hard**
verdict (``Shape.valid``), never abstains. The abstain / re-segment
decision belongs to the **control loop**, which combines this geometric
verdict with the raster structure gate (``topology``) — G5/G6.

Geometric validity = count (≥3) + closure (each vertex joins exactly two
segments, the ring is connected) + simplicity (no non-adjacent edge
crossing). Symbolic; no rendering (PLAN §10 D demotes whole-shape
reconstruction to an optional sanity check). ``input_group=all_required``
so Part 6 enforces both inputs are present (D-M2-b: the core validates
this, the body does not re-check).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from mindsos_capacity import Capacity
from mindsos_capacity.identifiers import CATEGORY_PREDICATE

from . import geometry as G
from .ontology import SEGMENT_SET, VERTEX_SET, SHAPE

PREDICATE_IRI = f"capacity:{CATEGORY_PREDICATE}:is_polygon"

_NAMES = {3: "triangle", 4: "quadrilateral", 5: "pentagon",
          6: "hexagon", 7: "heptagon", 8: "octagon"}


@dataclass(frozen=True)
class Shape:
    """A completed Shape{type, vertices, confidence} or a hard rejection."""

    polygon_type: str
    vertices: Tuple[G.Point, ...]
    valid: bool
    confidence: float
    detail: str = ""


def _segments_cross(s1, s2) -> bool:
    (a, b), (c, d) = s1, s2

    def ccw(p, q, r):
        return (r[1] - p[1]) * (q[0] - p[0]) - (q[1] - p[1]) * (r[0] - p[0])

    d1, d2 = ccw(c, d, a), ccw(c, d, b)
    d3, d4 = ccw(a, b, c), ccw(a, b, d)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def _is_simple(segments) -> bool:
    n = len(segments)
    for i in range(n):
        for j in range(i + 1, n):
            if j == i or (i + 1) % n == j or (j + 1) % n == i:
                continue   # skip adjacent (shared-endpoint) edges
            if _segments_cross(segments[i], segments[j]):
                return False
    return True


def _is_polygon(**kw):
    cand: G.Candidate = kw[SEGMENT_SET.iri]
    verts = kw[VERTEX_SET.iri]
    n = len(verts)
    count_ok = n >= 3
    closure_ok = bool(verts) and all(v.degree == 2 for v in verts)
    simple_ok = _is_simple(cand.segments)
    valid = count_ok and closure_ok and simple_ok
    ptype = _NAMES.get(cand.n_vertices, f"polygon_{cand.n_vertices}")
    conf = max(0.0, 1.0 - cand.rms) if valid else 0.0
    detail = "" if valid else (
        f"count_ok={count_ok} closure_ok={closure_ok} simple_ok={simple_ok}")
    return {SHAPE.iri: Shape(polygon_type=ptype, vertices=cand.vertices,
                             valid=valid, confidence=conf, detail=detail)}


def register_predicate(cl, session) -> str:
    pred = Capacity(
        name="is_polygon", category=CATEGORY_PREDICATE,
        inputs=(SEGMENT_SET.iri, VERTEX_SET.iri), outputs=(SHAPE.iri,),
        implementation=_is_polygon,
        description="hard verdict: closed simple polygon (count+closure+simplicity)",
    )
    cl.register_capacity(pred, session=session)
    return pred.iri
