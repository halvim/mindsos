"""Geometry core — Douglas–Peucker ε-sweep + scale-normalized residuals.

Pure functions (no core dependency), the substrate for the E proposer
(PLAN §10 E) and the D fit metric (PLAN §10 D):

- **Proposer:** polyline simplification (Douglas–Peucker) over the ordered
  closed boundary; sweep ε to emit a *ranked candidate family* (F's
  interface), rank by RMS residual with vertex-count parsimony as the
  tiebreak. Deterministic — the audit story needs it (PLAN §10 E).
- **Fit metric:** scale-normalized point-to-line residual, normalized by
  the figure bbox-diagonal (size is a Bongard nuisance — mandatory).
  **RMS = accept score; max-residual = abstain guard** (PLAN §10 D).

ε is swept as a *fraction of the bbox diagonal*, so τ_fit is a
scale-free threshold that transfers across shape sizes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

Point = Tuple[float, float]
Segment = Tuple[Point, Point]


@dataclass(frozen=True)
class Candidate:
    """One ε-sweep segmentation hypothesis (F's ranked-candidate element)."""

    vertices: Tuple[Point, ...]
    segments: Tuple[Segment, ...]
    rms: float          # scale-normalized RMS residual (accept score)
    max_resid: float    # scale-normalized max residual (abstain guard)
    epsilon_frac: float

    @property
    def n_vertices(self) -> int:
        return len(self.vertices)


def bbox_diag(points: List[Point]) -> float:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    dx = max(xs) - min(xs)
    dy = max(ys) - min(ys)
    return math.hypot(dx, dy) or 1.0


def _perp_dist(p: Point, a: Point, b: Point) -> float:
    """Perpendicular distance of p to the infinite line through a,b."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    denom = math.hypot(dx, dy)
    if denom == 0:
        return math.hypot(px - ax, py - ay)
    return abs(dy * (px - ax) - dx * (py - ay)) / denom


def point_seg_dist(p: Point, a: Point, b: Point) -> float:
    """Euclidean distance from p to the *segment* a-b (clamped)."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    if seg2 == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / seg2
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def _dp_open(arc: List[Point], epsilon: float) -> List[Point]:
    """Douglas–Peucker on an open polyline. Returns kept points."""
    if len(arc) < 3:
        return list(arc)
    a, b = arc[0], arc[-1]
    idx, dmax = 0, -1.0
    for i in range(1, len(arc) - 1):
        d = _perp_dist(arc[i], a, b)
        if d > dmax:
            idx, dmax = i, d
    if dmax > epsilon:
        left = _dp_open(arc[: idx + 1], epsilon)
        right = _dp_open(arc[idx:], epsilon)
        return left[:-1] + right
    return [a, b]


def simplify_closed(trace: List[Point], epsilon: float) -> List[Point]:
    """Closed-curve DP → polygon vertices (no repeated closing point).

    Split the loop at its two most distant anchors (start + farthest),
    DP each arc, concatenate. Robust for non-convex outlines where a
    single open DP would mis-anchor.
    """
    if len(trace) < 3:
        return list(trace)
    p0 = trace[0]
    far = max(range(len(trace)), key=lambda i: (trace[i][0] - p0[0]) ** 2
              + (trace[i][1] - p0[1]) ** 2)
    arc1 = trace[: far + 1]
    arc2 = trace[far:] + [p0]
    v1 = _dp_open(arc1, epsilon)
    v2 = _dp_open(arc2, epsilon)
    verts = v1[:-1] + v2[:-1]          # drop shared anchors / closing dup
    # de-dup consecutive identical
    out: List[Point] = []
    for v in verts:
        if not out or out[-1] != v:
            out.append(v)
    return merge_collinear(merge_close_vertices(out))


def _turn_angle(a: Point, b: Point, c: Point) -> float:
    """Interior turn at b on path a→b→c, in degrees (0 = straight)."""
    v1 = (b[0] - a[0], b[1] - a[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    n1 = math.hypot(*v1)
    n2 = math.hypot(*v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    cos = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return math.degrees(math.acos(cos))


def merge_collinear(vertices: List[Point], angle_tol_deg: float = 25.0) -> List[Point]:
    """Drop vertices whose turn is near-straight (DP / staircase artifacts).

    A real polygon corner turns by its exterior angle (≥ ~51° even for a
    heptagon); spurious mid-edge vertices turn by ~0–10°. One pass is
    enough for clean shapes. Operates on the cyclic ring.
    """
    n = len(vertices)
    if n <= 3:
        return list(vertices)
    keep: List[Point] = []
    for i in range(n):
        a = vertices[(i - 1) % n]
        b = vertices[i]
        c = vertices[(i + 1) % n]
        if _turn_angle(a, b, c) >= angle_tol_deg:
            keep.append(b)
    return keep if len(keep) >= 3 else list(vertices)


def merge_close_vertices(vertices: List[Point], min_frac: float = 0.05,
                         abs_floor: float = 8.0) -> List[Point]:
    """Collapse runs of consecutive near-coincident vertices to a centroid.

    A single true corner sometimes splits into two vertices a few pixels
    apart (DP anchor + staircase at larger scales); ``merge_collinear``
    misses them because the kink between them turns sharply. The split is
    ~constant in *pixels* while shapes vary in size, so the threshold is
    ``max(abs_floor, min_frac·diag)`` — the absolute floor catches
    rasterization splits on small shapes, the fractional term scales up
    for large ones. This is what makes the parse generalize across shape
    size / rotation (PLAN §3 held-out signal).
    """
    n = len(vertices)
    if n <= 3:
        return list(vertices)
    thr = max(abs_floor, min_frac * bbox_diag(vertices))
    out: List[Point] = []
    i = 0
    while i < n:
        cluster = [vertices[i]]
        j = i + 1
        while j < n and math.hypot(vertices[j][0] - vertices[j - 1][0],
                                   vertices[j][1] - vertices[j - 1][1]) < thr:
            cluster.append(vertices[j])
            j += 1
        cx = sum(p[0] for p in cluster) / len(cluster)
        cy = sum(p[1] for p in cluster) / len(cluster)
        out.append((cx, cy))
        i = j
    if len(out) > 3 and math.hypot(out[0][0] - out[-1][0],
                                   out[0][1] - out[-1][1]) < thr:
        out[0] = ((out[0][0] + out[-1][0]) / 2, (out[0][1] + out[-1][1]) / 2)
        out.pop()
    return out if len(out) >= 3 else list(vertices)


def segments_from_vertices(vertices: List[Point]) -> List[Segment]:
    """Closed polygon edges from an ordered vertex ring."""
    n = len(vertices)
    return [(vertices[i], vertices[(i + 1) % n]) for i in range(n)]


def fit_residuals(trace: List[Point], segments: List[Segment], diag: float):
    """(rms_norm, max_norm): every boundary point to its nearest edge."""
    if not segments:
        return float("inf"), float("inf")
    sq = 0.0
    mx = 0.0
    for p in trace:
        d = min(point_seg_dist(p, a, b) for (a, b) in segments)
        sq += d * d
        mx = max(mx, d)
    rms = math.sqrt(sq / len(trace))
    return rms / diag, mx / diag


def per_edge_max_residual(trace: List[Point], vertices, diag: float) -> float:
    """Worst per-edge scale-normalized RMS residual (PLAN §10 D revision).

    Each boundary point is assigned to its nearest polygon edge; the RMS
    residual is computed *per edge* over its assigned points; the worst
    edge is returned. A true polygon edge → ~0; a chord across a curve, or
    a curved/decorated edge → high. One bad edge is enough to reject, so
    this also *localizes* edge-decoration (the disaggregated form of the
    aggregate fit metric). ``max_sides`` is no longer needed: a curve fails
    this even when finely sampled, because each chord still bows.
    """
    segs = segments_from_vertices(list(vertices))
    if not segs:
        return float("inf")
    buckets: List[List[float]] = [[] for _ in segs]
    for p in trace:
        dists = [point_seg_dist(p, a, b) for (a, b) in segs]
        i = min(range(len(dists)), key=lambda k: dists[k])
        buckets[i].append(dists[i])
    worst = 0.0
    for v in buckets:
        if v:
            worst = max(worst, math.sqrt(sum(d * d for d in v) / len(v)))
    return worst / diag


def epsilon_profile(trace: List[Point], k: int = 24,
                    lo_frac: float = 0.004, hi_frac: float = 0.12):
    """Per-ε simplification in ε order, WITHOUT dedup/sort (persistence).

    Returns ``[(eps_frac, vertices_tuple), ...]``. The persistence signal
    (a vertex count that stays *stable across a wide ε band* = a polygon;
    a *wandering* count = a curve) reads off this ordered profile.
    :func:`epsilon_sweep` dedups + ranks by RMS, which destroys the ε
    ordering and the repeated counts a plateau is measured from — so it is
    unsuitable here.
    """
    diag = bbox_diag(trace)
    fracs = [lo_frac * (hi_frac / lo_frac) ** (i / (k - 1)) for i in range(k)]
    return [(f, tuple(simplify_closed(trace, f * diag))) for f in fracs]


def epsilon_sweep(trace: List[Point], k: int = 12,
                  lo_frac: float = 0.004, hi_frac: float = 0.08) -> List[Candidate]:
    """Sweep K ε fractions; return candidates ranked by (RMS, n_vertices).

    Self-bounding (PLAN §10 H): a finite candidate set, so inner-loop
    exhaustion is a *semantic* outcome ("nothing fit"), not a budget.
    """
    diag = bbox_diag(trace)
    fracs = [lo_frac * (hi_frac / lo_frac) ** (i / (k - 1)) for i in range(k)]
    cands: List[Candidate] = []
    seen = set()
    for f in fracs:
        verts = simplify_closed(trace, f * diag)
        if len(verts) < 3:
            continue
        key = tuple(verts)
        if key in seen:
            continue
        seen.add(key)
        segs = segments_from_vertices(verts)
        rms, mx = fit_residuals(trace, segs, diag)
        cands.append(Candidate(tuple(verts), tuple(segs), rms, mx, f))
    cands.sort(key=lambda c: (round(c.rms, 6), c.n_vertices))
    return cands
