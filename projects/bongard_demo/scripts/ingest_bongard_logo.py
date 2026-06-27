"""Provenance / regeneration script for the Bongard-LOGO panel fixtures
(sandbox-side; NOT run by the gate — needs PIL/scipy/scikit-image).

Bongard-LOGO draws outlines as discrete decorative glyphs, which shatter our
solid-stroke perception into 9-23 components per panel. This bridges that with
a morphological pass and serializes the result as fg-coordinate JSON fixtures
that the gate loads via `bongard.ingest` (pure python, no image libs).

Transform (the only demo-side image processing; it makes strokes solid, it does
NOT decide the label):

    binarize(gray < 128)
    -> binary_closing(kernel=9)          # bridge the glyph trail into one stroke
    -> block-max downscale 512 -> 128     # into our perception's calibrated regime
    -> skeletonize                        # 1px closed contour (native input)

Usage (with the dataset cloned to BONGARD_LOGO_DIR):

    python scripts/ingest_bongard_logo.py /path/to/Bongard-LOGO

Re-creates tests/fixtures/bongard_logo/{rectangle_vs_circle,convex_vs_concave}.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image as PImage
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

PROBLEMS = {
    "00-rectangle_vs_circle": ("rectangle_vs_circle",
                               {"side0": "curve(circle)", "side1": "polygon(rectangle)"}),
    "01-convex_vs_concave": ("convex_vs_concave",
                             {"side0": "concave", "side1": "convex"}),
}
FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "bongard_logo"


def ingest_panel(path: str, close_k: int = 9, target: int = 128):
    g = np.array(PImage.open(path).convert("L"))
    fg = g < 128
    fg = ndi.binary_closing(fg, structure=np.ones((close_k, close_k)))
    h, _ = fg.shape
    s = h // target
    small = fg[:s * target, :s * target].reshape(target, s, target, s).max(axis=(1, 3))
    skel = skeletonize(small)
    ys, xs = np.where(skel)
    return [[int(x), int(y)] for x, y in zip(xs, ys)]


def main(dataset_dir: str) -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for prob, (name, meta) in PROBLEMS.items():
        rec = {
            "width": 128, "height": 128,
            "source": f"NVlabs/Bongard-LOGO examples/{prob}",
            "transform": "binarize(<128) -> binary_closing(9) -> block-max downscale 512->128 -> skeletonize",
            "meta": meta, "sides": {},
        }
        for side in (0, 1):
            rec["sides"][str(side)] = [
                ingest_panel(f"{dataset_dir}/examples/{prob}/demo/png/{side}/{p}.png")
                for p in range(7)
            ]
        (FIXTURES / f"{name}.json").write_text(json.dumps(rec))
        print(f"wrote {name}.json")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Bongard-LOGO")
