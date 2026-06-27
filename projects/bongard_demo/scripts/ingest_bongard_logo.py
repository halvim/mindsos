"""Provenance / regeneration script for the Bongard-LOGO panel fixtures
(sandbox-side; NOT run by the gate — needs PIL).

FAITHFUL ingestion: binarize ONLY (native 512), no morphological fabrication.
An earlier version closed+filled+skeletonized the glyph trails into a clean
contour, but `fill_holes` is the actual perceptual act (deciding scattered
glyphs enclose a region) done by scipy, not by our atoms — it cheated the
perception and was removed. We feed the real marks and let OUR system report
what it deduces (see `tests/test_real_bongard.py`).

Bongard-LOGO draws outlines as discrete glyphs (small triangles/circles) + solid
arcs, so a raw panel is ~15-23 connected components. The fixtures store the raw
foreground coordinates; the gate loads them via `bongard.ingest` (pure python).

Usage (with the dataset cloned to BONGARD_LOGO_DIR):

    python scripts/ingest_bongard_logo.py /path/to/Bongard-LOGO
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image as PImage

PROBLEMS = {
    "00-rectangle_vs_circle": ("rectangle_vs_circle",
                               {"side0": "curve(circle)", "side1": "polygon(rectangle)"}),
    "01-convex_vs_concave": ("convex_vs_concave",
                             {"side0": "concave", "side1": "convex"}),
}
FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "bongard_logo"
TRANSFORM = "binarize(gray<128) ONLY — faithful raw marks, native 512, NO fabrication"


def ingest_panel(path: str):
    """Faithful: the raw foreground pixels (threshold only), native resolution."""
    g = np.array(PImage.open(path).convert("L"))
    ys, xs = np.where(g < 128)
    return [[int(x), int(y)] for x, y in zip(xs, ys)]


def main(dataset_dir: str) -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for prob, (name, meta) in PROBLEMS.items():
        first = f"{dataset_dir}/examples/{prob}/demo/png/0/0.png"
        w = h = int(PImage.open(first).size[0])
        rec = {"width": w, "height": h,
               "source": f"NVlabs/Bongard-LOGO examples/{prob}",
               "transform": TRANSFORM, "meta": meta, "sides": {}}
        for side in (0, 1):
            rec["sides"][str(side)] = [
                ingest_panel(f"{dataset_dir}/examples/{prob}/demo/png/{side}/{p}.png")
                for p in range(7)
            ]
        (FIXTURES / f"{name}.json").write_text(json.dumps(rec))
        print(f"wrote {name}.json")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Bongard-LOGO")
