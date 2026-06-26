"""Synthetic clean-shape renderer + abstain-negative fixtures (PLAN §3, m1).

Decision (option-3 build): **self-render** clean line-art polygons to a
binary raster for the build + the τ_fit calibration, using the rendering
vertices as the calibration *oracle* (PLAN §10 D — bootstrap ε off the
definitional triangle seed, which has a known answer). Bongard-LOGO is
turtle line-art, so a shape is its **outline strokes**, not a fill: we
rasterize the polygon edges.

Dependency-free on purpose (no numpy): "pixels" is a sparse binary raster
(:class:`Image` = a foreground coordinate set + canvas dims). For clean
synthetic shapes the ``pixels → point-set`` leaf is trivially a threshold;
the real perception work is ``point-set → boundary-trace → segments``
(PLAN §5). This is the licensed "from scratch" leaf — it expires the
moment shapes stop being clean (PLAN §11), at which point a path-2 neural
leaf grounds the same typed point-set (§14 / skill-acq §6.2).

The **abstain negatives** are first-class m1 fixtures, not later tasks:
they are what actually exercises the fit-gate / structure-gate / re-segment
logic that the §6 moat rests on (PLAN §11 guardrail). Each sample declares
its ``expect`` so the verification task asserts the *reason*, not just a
pass/fail.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import FrozenSet, List, Optional, Tuple

Point = Tuple[float, float]
Pixel = Tuple[int, int]


# ── Raster image (the "pixels" DataState payload) ──────────────────────

@dataclass(frozen=True)
class Image:
    """A sparse binary raster: foreground pixel coords on a W×H canvas."""

    width: int
    height: int
    fg: FrozenSet[Pixel]

    def __post_init__(self) -> None:
        if not self.fg:
            raise ValueError("empty raster (no foreground pixels)")


@dataclass(frozen=True)
class Sample:
    """A rendered fixture with its expected perception verdict.

    ``truth_vertices`` is the rendering oracle (the action-program-exact
    vertices) — used ONLY to calibrate τ_fit / score generalization,
    never fed into the parse (PLAN §10 E "action-program vertices skip
    pixels = cheats perception"). ``None`` for negatives.

    ``expect`` ∈ {``"solve"``, ``"abstain"``}; ``reason`` names which gate
    a negative should trip (``"fit"`` curve/edge-decoration, ``"structure"``
    non-closure) so the verification asserts the moat, not a bare boolean.
    """

    name: str
    pixels: Image
    truth_vertices: Optional[Tuple[Point, ...]]
    expect: str            # "solve" | "abstain"
    reason: str = ""       # "" | "fit" | "structure"


# ── Rasterization (Bresenham line, no deps) ────────────────────────────

def _line(p0: Pixel, p1: Pixel) -> List[Pixel]:
    """Integer Bresenham line from p0 to p1 (inclusive)."""
    x0, y0 = p0
    x1, y1 = p1
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    out: List[Pixel] = []
    while True:
        out.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return out


def _stroke(coords: List[Pixel], width: int) -> FrozenSet[Pixel]:
    """Thicken a 1px stroke into a (2*width+1)-neighborhood band."""
    if width <= 0:
        return frozenset(coords)
    out = set()
    for (x, y) in coords:
        for dx in range(-width, width + 1):
            for dy in range(-width, width + 1):
                out.add((x + dx, y + dy))
    return frozenset(out)


def _rasterize_path(
    pts: List[Point],
    *,
    closed: bool,
    canvas: int = 128,
    stroke: int = 0,
) -> Image:
    """Rasterize a polyline (closed=loop) of float points onto the canvas."""
    ipts = [(int(round(x)), int(round(y))) for (x, y) in pts]
    edges = list(zip(ipts, ipts[1:]))
    if closed:
        edges.append((ipts[-1], ipts[0]))
    fg: set = set()
    for a, b in edges:
        fg |= _stroke(_line(a, b), stroke)
    fg = {(x, y) for (x, y) in fg if 0 <= x < canvas and 0 <= y < canvas}
    return Image(width=canvas, height=canvas, fg=frozenset(fg))


def _regular_polygon(n: int, *, cx=64.0, cy=64.0, r=40.0, rot=-math.pi / 2) -> Tuple[Point, ...]:
    """Vertices of a regular n-gon (rot=-pi/2 puts a vertex up top)."""
    return tuple(
        (cx + r * math.cos(rot + 2 * math.pi * k / n),
         cy + r * math.sin(rot + 2 * math.pi * k / n))
        for k in range(n)
    )


# ── Clean shapes (build + calibration; truth = oracle) ─────────────────

def polygon_sample(name: str, n: int, *, stroke: int = 0, **kw) -> Sample:
    verts = _regular_polygon(n, **kw)
    img = _rasterize_path(list(verts), closed=True, stroke=stroke)
    return Sample(name=name, pixels=img, truth_vertices=verts,
                  expect="solve", reason="")


def triangle(**kw) -> Sample:
    return polygon_sample("triangle", 3, **kw)


def square(**kw) -> Sample:
    return polygon_sample("square", 4, **kw)


def pentagon(**kw) -> Sample:
    return polygon_sample("pentagon", 5, **kw)


# ── Abstain negatives (exercise the gates — PLAN §11) ──────────────────

def circle(*, cx=64.0, cy=64.0, r=40.0, steps=64) -> Sample:
    """A smooth curve: no straight-segment fit → fit-gate abstain."""
    pts = [(cx + r * math.cos(2 * math.pi * k / steps),
            cy + r * math.sin(2 * math.pi * k / steps)) for k in range(steps)]
    img = _rasterize_path(pts, closed=True)
    return Sample(name="circle", pixels=img, truth_vertices=None,
                  expect="abstain", reason="fit")


def open_strokes() -> Sample:
    """Disconnected / non-closing strokes → structure-gate abstain."""
    a = _rasterize_path([(24.0, 24.0), (96.0, 30.0)], closed=False)
    b = _rasterize_path([(30.0, 80.0), (90.0, 100.0)], closed=False)
    fg = frozenset(a.fg | b.fg)
    return Sample(name="open_strokes", pixels=Image(128, 128, fg),
                  truth_vertices=None, expect="abstain", reason="structure")


def bowtie() -> Sample:
    """A self-intersecting closed stroke (figure-8): single closed loop by
    topology, but not a simple polygon.

    m1 finding: under the convex-family angle-sort tracer the boundary is
    reconstructed as a convex hull that cannot match the crossing strokes,
    so its residual is high and it abstains at the **fit** gate — the fit
    gate *subsumes* the geometric structure gate for this tracer. The
    geometric structure gate + R=1 re-segment is the **non-convex seam**
    (unit-tested directly in test_perception, exercised for real only when
    the tracer is swapped for a connectivity tracer). Kept as a negative."""
    tl, tr, br, bl = (34.0, 34.0), (94.0, 34.0), (94.0, 94.0), (34.0, 94.0)
    img = _rasterize_path([tl, br, bl, tr], closed=True)
    return Sample(name="bowtie", pixels=img, truth_vertices=None,
                  expect="abstain", reason="fit")


def near_miss_polygon(gap: int = 10) -> Sample:
    """A would-be polygon whose last edge stops short → re-segment then,
    if it still won't close, structure-gate abstain (PLAN §10 H, R=1)."""
    verts = list(_regular_polygon(4))
    # Open the loop: draw edges but drop the closing edge, leaving a gap.
    pts = verts + [(verts[0][0] + gap, verts[0][1] + gap)]
    img = _rasterize_path(pts, closed=False)
    return Sample(name="near_miss", pixels=img, truth_vertices=None,
                  expect="abstain", reason="structure")


# ── Multi-figure scenes (m3 individuation fixtures) ────────────────────

def _compose(images: List[Image]) -> Image:
    """Union several rasters onto one canvas (disjoint = N components)."""
    w = max(im.width for im in images)
    h = max(im.height for im in images)
    fg: set = set()
    for im in images:
        fg |= set(im.fg)
    return Image(width=w, height=h, fg=frozenset(fg))


def _ngon_image(n: int, *, cx: float, cy: float, r: float, stroke: int = 0) -> Image:
    verts = _regular_polygon(n, cx=cx, cy=cy, r=r)
    return _rasterize_path(list(verts), closed=True, stroke=stroke)


def scene_two_squares(stroke: int = 0) -> Image:
    """Two disjoint squares → 2 components, both solve, same_shape pair."""
    a = _ngon_image(4, cx=34.0, cy=34.0, r=22.0, stroke=stroke)
    b = _ngon_image(4, cx=94.0, cy=94.0, r=22.0, stroke=stroke)
    return _compose([a, b])


def scene_square_triangle(stroke: int = 0) -> Image:
    """A square + a triangle → 2 components, both solve, no same_shape."""
    a = _ngon_image(4, cx=34.0, cy=34.0, r=22.0, stroke=stroke)
    b = _ngon_image(3, cx=94.0, cy=94.0, r=24.0, stroke=stroke)
    return _compose([a, b])


def scene_three_mixed(stroke: int = 0) -> Image:
    """Two triangles + one pentagon → 3 components; one same_shape pair."""
    a = _ngon_image(3, cx=30.0, cy=30.0, r=20.0, stroke=stroke)
    b = _ngon_image(3, cx=98.0, cy=30.0, r=20.0, stroke=stroke)
    c = _ngon_image(5, cx=64.0, cy=98.0, r=22.0, stroke=stroke)
    return _compose([a, b, c])


def scene_overlapping() -> Image:
    """Two overlapping squares → ONE component → honest abstain (D-M3-2)."""
    a = _ngon_image(4, cx=56.0, cy=56.0, r=24.0)
    b = _ngon_image(4, cx=72.0, cy=72.0, r=24.0)
    return _compose([a, b])


# ── Fixture sets ───────────────────────────────────────────────────────

def calibration_seed() -> Sample:
    """The definitional triangle seed — known answer for τ_fit bootstrap."""
    return triangle()


def build_samples() -> List[Sample]:
    """Clean positives + abstain negatives = the m1 verification set."""
    return [
        triangle(), square(), pentagon(),
        circle(), open_strokes(), near_miss_polygon(), bowtie(),
    ]


def load_nvlabs_smoke() -> List[Sample]:
    """Held-back smoke set from the real NVlabs Bongard-LOGO renders.

    Contract: drop binary rasters under
    ``projects/bongard_demo/fixtures/nvlabs/`` (one shape per file). Absent
    by default (the dataset is not vendored) → returns ``[]`` and the
    smoke test xfails/skips. This is the one-step-of-real-noise check
    before the clean-leaf claim is trusted (PLAN §3 update-2 picks).
    """
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.join(here, "..", "fixtures", "nvlabs")
    if not os.path.isdir(root):
        return []
    # Loader wired when fixtures are vendored; format TBD with the data.
    return []
