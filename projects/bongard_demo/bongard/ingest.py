"""Ingest real Bongard-LOGO panels into our `Image` format (demo-side; the
real-data limitation test — PLAN real-data diagnostic block).

FAITHFUL diagnostic (Henrique 2026-06-26): the fixtures are the **raw** marks —
`binarize(gray<128)` ONLY, native 512, NO closing/fill/skeletonize. An earlier
version morphologically closed+filled the glyphs into a clean contour, but that
was *cheating the perception*: `fill_holes` is the actual perceptual act
(deciding scattered glyphs enclose a region), done by scipy with operations not
in our atom vocabulary. The faithful test feeds the real pixels and reports what
OUR atoms deduce.

Bongard-LOGO (NVlabs) draws outlines as discrete decorative GLYPHs (small
triangles ▷ / circles ○ along the path) + solid arcs — NOT closed strokes. So a
raw panel is ~15-23 connected components: a few big arc segments + many ~12px
glyphs. Our perception (vertex/segment/angle → polygon, closed-stroke gate,
~44-60px size regime) therefore sees the local MARKS (or abstains on them), not
the gestalt rectangle/circle. That gap — no perception of how marks ARRANGE into
an enclosing shape — is the real, grounded finding.

This module is the GATE-side loader only (pure python, no PIL/scipy): it reads
the serialized fg-coordinate fixtures into `render.Image`, so the Linux gate
runs real `parse_scene` on real raw panels without any image libraries.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from .render import Image

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "bongard_logo"


def _image(fg, w: int, h: int) -> Image:
    return Image(width=w, height=h, fg=frozenset((int(x), int(y)) for x, y in fg))


def load_problem(name: str) -> Dict[str, List[Image]]:
    """Load a serialized Bongard-LOGO problem → ``{side: [Image per panel]}``.

    ``name`` ∈ {``"rectangle_vs_circle"``, ``"convex_vs_concave"``}. Each side
    is the 7 panels of that side of the Bongard problem.
    """
    data = json.loads((FIXTURES / f"{name}.json").read_text())
    w, h = data["width"], data["height"]
    return {side: [_image(fg, w, h) for fg in panels]
            for side, panels in data["sides"].items()}
