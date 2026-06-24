"""point-set→segments (ε-sweep + fit gate) and segments→vertices (PLAN §5).

``segments`` is a ``perception`` body (DATASTATE_MARKER don't-know): it
runs the deterministic ε-sweep over the boundary trace and applies the
**curve discriminator** (PLAN §10 D revision 2026-06-23, replacing the
old ``max_sides`` cap): a polygon is a vertex count that is BOTH
**ε-persistent** (a vertex count holding a stable plateau across a wide
band of the sweep — ``plateau_min_frac``) AND **per-edge-fit-passing**
(worst per-edge RMS ≤ ``per_edge_tau``). Among qualifying plateaus, pick
the **fewest-vertex** one (parsimony). No qualifier ⇒ ``DontKnow("fit")``
— the curve / edge-decoration rejector. Both gates are load-bearing: a
circle fails *persistence* (its count wanders); a self-intersecting
bowtie holds a plateau but fails *per-edge fit*. This drops ``max_sides``
entirely and is scale/N-invariant (validated across 10 shapes).

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


def select_polygon(trace: List[G.Point], p: Params) -> Optional[G.Candidate]:
    """Persistence + per-edge fit (PLAN §10 D revision); replaces max_sides.

    A polygon = a vertex count that is BOTH ε-stable across a wide band of
    the sweep (plateau width ≥ ``plateau_min_frac`` of the valid steps) AND
    per-edge-fit-passing (worst per-edge RMS ≤ ``per_edge_tau``). Among
    qualifying plateaus, the fewest-vertex one wins. Returns its
    representative :class:`~bongard.geometry.Candidate`, or ``None`` (the
    curve / edge-decoration verdict the control loop turns into abstain).
    """
    profile = G.epsilon_profile(trace, k=p.k, lo_frac=p.lo_frac, hi_frac=p.hi_frac)
    valid = [(f, v) for (f, v) in profile if len(v) >= 3]
    if not valid:
        return None
    diag = G.bbox_diag(trace)
    # group consecutive equal-count ε steps into plateaus
    plateaus: List[List] = []
    i = 0
    while i < len(valid):
        j = i
        while j + 1 < len(valid) and len(valid[j + 1][1]) == len(valid[i][1]):
            j += 1
        plateaus.append(valid[i:j + 1])
        i = j + 1
    nsteps = len(valid)
    qualifying = []
    for members in plateaus:
        if len(members) / nsteps < p.plateau_min_frac:
            continue                                   # not ε-persistent
        # representative = the plateau member with the cleanest per-edge fit
        _, verts = min(members,
                       key=lambda fv: G.per_edge_max_residual(trace, fv[1], diag))
        if G.per_edge_max_residual(trace, verts, diag) <= p.per_edge_tau:
            qualifying.append((len(verts), verts))
    if not qualifying:
        return None
    _, verts = min(qualifying, key=lambda q: q[0])     # fewest vertices
    segs = G.segments_from_vertices(list(verts))
    rms, mx = G.fit_residuals(trace, segs, diag)
    return G.Candidate(tuple(verts), tuple(segs), rms, mx, 0.0)


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
    best = select_polygon(list(trace), p)
    if best is None:
        return {SEGMENT_SET.iri: DontKnow(
            reason="fit",
            detail="no ε-persistent, per-edge-fitting polygon (curve/edge-decoration)")}
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
