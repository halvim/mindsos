"""Picture demo — render each scene + overlay what the system recognized.

Human-eyeball view (NOT a test): for every multi-figure scene it
rasterizes the image, runs the **real** m3 recognition through
``cl.invoke`` (connected-components individuation → per-figure perceive →
``Scene``), and draws each individuated component tinted + labelled with
its recognized polygon type (or ``ABSTAIN`` + reason). Relations are
captioned underneath.

Run (Linux test image)::

    docker compose -p mindsos-bongard --profile test run --rm --build \
        -e PYTHONPATH=/app/projects/bongard_demo mindsos-test \
        python projects/bongard_demo/scripts/picture_demo.py --out /app/_pics

Or in-memory anywhere mindsos_* imports (Py3.10 + ``pip install tomli``)::

    PYTHONPATH=.:projects/bongard_demo python projects/bongard_demo/scripts/picture_demo.py --out ./_pics
"""

from __future__ import annotations

import argparse
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

from bongard import render
from bongard.control import Solver
from bongard.scene import connected_components, parse_scene, scene_relations
from bongard.relations import REL_SAME_SHAPE


def scene_all_four() -> "render.Image":
    """Four disjoint figures, all different: triangle, square, pentagon,
    and a circle (the curve → honest fit-abstain). r=22 keeps each inside
    the calibrated band and the quadrants disjoint on the 128 canvas."""
    tri = render._ngon_image(3, cx=32.0, cy=32.0, r=22.0)
    sq = render._ngon_image(4, cx=96.0, cy=32.0, r=22.0)
    pen = render._ngon_image(5, cx=32.0, cy=96.0, r=22.0)
    cir = render.circle(cx=96.0, cy=96.0, r=22.0).pixels
    return render._compose([tri, sq, pen, cir])


SCENES = [
    ("two squares", render.scene_two_squares()),
    ("square + triangle", render.scene_square_triangle()),
    ("three mixed (2 triangles + pentagon)", render.scene_three_mixed()),
    ("all four (tri/square/pentagon/circle)", scene_all_four()),
    ("overlapping squares", render.scene_overlapping()),
]

# Distinct tints per component (foreground only; background stays white).
_TINTS = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf"]


def _component_centroid(comp_fg):
    xs = [x for (x, y) in comp_fg]
    ys = [y for (x, y) in comp_fg]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _fmt_rel(r) -> str:
    arrow = "==" if r.symmetric else "->"
    return f"{r.rel_type}(#{r.subj} {arrow} #{r.obj})"


def draw(ax, title, image, solver):
    comps = connected_components(image)
    scene = parse_scene(solver, image)
    rels = scene_relations(solver, scene)

    # Paint: background 0 (white); each component its own index colour.
    grid = np.zeros((image.height, image.width), dtype=int)
    for ci, comp in enumerate(comps):
        for (x, y) in comp.fg:
            grid[y, x] = ci + 1
    cmap = ListedColormap(["white"] + [_TINTS[i % len(_TINTS)] for i in range(len(comps))])
    ax.imshow(grid, cmap=cmap, origin="upper", interpolation="nearest", vmin=0, vmax=len(comps))

    # Label each component at its centroid with the recognized verdict.
    for ci, (comp, v) in enumerate(zip(comps, scene.figures)):
        cx, cy = _component_centroid(comp.fg)
        if v.solved and v.shape is not None:
            label = f"#{ci} {v.shape.polygon_type}\n({len(v.shape.vertices)} vtx)"
        else:
            label = f"#{ci} ABSTAIN\n({v.reason})"
        ax.text(cx, cy, label, ha="center", va="center", fontsize=8,
                fontweight="bold", color="black",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="black", alpha=0.85))

    rel_txt = ", ".join(_fmt_rel(r) for r in rels) if rels else "(none)"
    ax.set_title(f"{title}\nsolved {scene.n_shapes} · abstained {scene.n_abstained} · "
                 f"relations: {rel_txt}", fontsize=9)
    ax.set_xticks([]); ax.set_yticks([])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="./_pics")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    solver = Solver("bongard-pictures")
    n = len(SCENES)
    cols = 2
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(9, 4.2 * rows))
    axes = axes.ravel()
    for ax, (title, image) in zip(axes, SCENES):
        draw(ax, title, image, solver)
    for ax in axes[n:]:
        ax.axis("off")
    fig.suptitle("Bongard demo — individual-shape recognition in group scenes "
                 "(real cl.invoke; m3)", fontsize=12, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    out = os.path.join(args.out, "group_recognition.png")
    fig.savefig(out, dpi=130)
    print("wrote", out)


if __name__ == "__main__":
    main()
