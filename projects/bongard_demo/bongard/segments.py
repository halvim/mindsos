"""point-set→segments (ε-sweep + fit gate) and segments→vertices (PLAN §5).

``segments`` is a ``perception`` body (DATASTATE_MARKER don't-know): it
runs the deterministic ε-sweep over the boundary trace and applies the
**fit gate** — among candidates passing (RMS ≤ τ_fit, max ≤ guard,
n_vertices ≤ max_sides), it picks the **fewest-vertex** one (parsimony;
PLAN §10 E). No passer ⇒ ``DontKnow("fit")`` — the curve / edge-decoration
rejector (the circle lands here). Parsimony-primary, not RMS-primary:
RMS-primary would reward an over-fit N-gon over the true polygon, and let
a fine-enough polygon fit a circle within τ_fit (defeating the gate).

``vertices`` is a ``derivation`` body: it reads the shared endpoints of
the closed segment ring (PLAN §4 — a vertex joins exactly two segments)
and reports each vertex's degree, for the predicate's closure check.

Params arrive via the read-path ``context`` dict (G4 — see
``calibration.py``); both bodies pass a ``DontKnow`` input straight
through so an upstream abstain short-circuits the chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from mindsos_capacity import Capacity, CATEGORY_DERIVATION, CATEGORY_PERCEPTION

from . import geometry as G
from .calibration import GLOBAL_DEFAULT, PARAMS_CTX_KEY, Params
from .ontology import BOUNDARY_TRACE, SEGMENT_SET, VERTEX_SET
from .signals import DontKnow, is_dont_know

SEGMENTS_IRI = f"capacity:{CATEGORY_PERCEPTION}:segments"
VERTICES_IRI = f"capacity:{CATEGORY_DERIVATION}:vertices"


@dataclass(frozen=True)
class Vertex:
    point: G.Point
    degree: int        # number of incident segments (a polygon vertex = 2)


def select_polygon(cands: List[G.Candidate], p: Params) -> Optional[G.Candidate]:
    """Fit gate + parsimony: fewest-vertex candidate that passes, else None."""
    ok = [c for c in cands
          if c.rms <= p.tau_fit and c.max_resid <= p.max_guard
          and c.n_vertices <= p.max_sides]
    if not ok:
        return None
    return min(ok, key=lambda c: (c.n_vertices, round(c.rms, 6)))


def _params_from_ctx(kw) -> Params:
    ctx = kw.get("context") or {}
    raw = ctx.get(PARAMS_CTX_KEY)
    if not raw:
        return GLOBAL_DEFAULT
    return Params(**raw)


def _segments(**kw):
    trace = kw[BOUNDARY_TRACE.iri]
    if is_dont_know(trace):
        return {SEGMENT_SET.iri: trace}
    p = _params_from_ctx(kw)
    cands = G.epsilon_sweep(list(trace), k=p.k, lo_frac=p.lo_frac, hi_frac=p.hi_frac)
    best = select_polygon(cands, p)
    if best is None:
        return {SEGMENT_SET.iri: DontKnow(
            reason="fit",
            detail="no parsimonious polygon within tau_fit (curve/edge-decoration)")}
    return {SEGMENT_SET.iri: best}


def _vertices(**kw):
    seg = kw[SEGMENT_SET.iri]
    if is_dont_know(seg):
        return {VERTEX_SET.iri: seg}
    # degree = how many segments share each endpoint (rounded for float eq).
    deg = {}
    for (a, b) in seg.segments:
        for pt in (a, b):
            key = (round(pt[0], 3), round(pt[1], 3))
            deg[key] = deg.get(key, 0) + 1
    verts = tuple(Vertex(point=k, degree=d) for k, d in deg.items())
    return {VERTEX_SET.iri: verts}


def register_segments(cl, session) -> Tuple[str, str]:
    seg = Capacity(
        name="segments", category=CATEGORY_PERCEPTION,
        inputs=(BOUNDARY_TRACE.iri,), outputs=(SEGMENT_SET.iri,),
        implementation=_segments,
        description="epsilon-sweep DP + fit gate -> parsimonious segment ring | DontKnow(fit)",
    )
    vts = Capacity(
        name="vertices", category=CATEGORY_DERIVATION,
        inputs=(SEGMENT_SET.iri,), outputs=(VERTEX_SET.iri,),
        implementation=_vertices,
        description="shared-endpoint vertices of the closed segment ring",
    )
    cl.register_capacity(seg, session=session)
    cl.register_capacity(vts, session=session)
    return seg.iri, vts.iri
