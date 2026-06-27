"""Ingest real Bongard-LOGO panels into our `Image` format (demo-side; the
real-data limitation test — PLAN real-data diagnostic block).

Bongard-LOGO (NVlabs) draws shape outlines as discrete decorative GLYPHs
(triangles/circles spaced along the path) + occasional arcs, NOT solid closed
strokes. Our perception assumes *shape = one continuous closed stroke*, so a
raw panel shatters into 9-23 connected components (every glyph = its own blob).
The fixtures bridge that with a morphological pass (sandbox-side, see
`scripts/ingest_bongard_logo.py`):

    binarize(<128) -> binary_closing(9) -> block-max downscale 512->128 -> skeletonize

which yields a 1px closed contour — our perception's native input. The bridge
makes the stroke solid; it does NOT inject the answer (it never decides
rectangle vs circle). No `mindsos_*` edits.

This module is the GATE-side loader only (pure python, no PIL/scipy): it reads
the serialized fg-coordinate fixtures into `render.Image`, so the Linux gate
runs real `parse_scene` on real-derived panels without any image libraries.
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
