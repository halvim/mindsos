"""m4 eyeball card — render each problem as a 6+6 Bongard-style card with
the system's concluded concept (PLAN m4 D-M4-9).

For every problem it runs the real ``search_and_verify`` loop to get a
conclusion, then draws a fresh 6-positive / 6-negative card. Each scene is
parsed end-to-end through the m3 chain and labelled with the **concluded
concept's** verdict via ``evaluate_concept`` (``cl.invoke``); a green frame =
predicted positive, red = predicted negative, and a ``✓``/``✗`` marks whether
that prediction matches the scene's true side of the card.

Run (Linux test image)::

    docker compose -p mindsos-bongard --profile test run --rm --build \
        -e PYTHONPATH=/app/projects/bongard_demo mindsos-test \
        python projects/bongard_demo/scripts/m4_card.py --out /app/_pics
"""

from __future__ import annotations

import argparse
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from bongard.control import Solver
from bongard.problem import PROBLEMS
from bongard.scene import parse_scene, scene_relations
from bongard.ontology import SCENE, RELATION_SET
from bongard.concepts import CONCEPT_CANDIDATE, CONCEPT_VERDICT
from bongard.search import search_and_verify

_CARD_SEED = 777   # disjoint from train (0) and held-out (1000) seeds


def _verdict(solver, concept, image) -> bool:
    scene = parse_scene(solver, image)
    rels = scene_relations(solver, scene)
    r = solver.cl.invoke(solver.concept_iri,
                         {SCENE.iri: scene, RELATION_SET.iri: rels,
                          CONCEPT_CANDIDATE.iri: concept},
                         session=solver.session)
    return bool(r.outputs[CONCEPT_VERDICT.iri])


def _show(ax, image, pred, truth):
    grid = np.ones((image.height, image.width))
    for (x, y) in image.fg:
        grid[y, x] = 0
    ax.imshow(grid, cmap="gray", origin="upper", vmin=0, vmax=1, interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([])
    colour = "#2ca02c" if pred else "#d62728"        # predicted pos / neg
    for sp in ax.spines.values():
        sp.set_edgecolor(colour); sp.set_linewidth(3)
    mark = "✓" if pred == truth else "✗"
    ax.text(0.5, -0.08, mark, transform=ax.transAxes, ha="center", va="top",
            fontsize=12, color=("#2ca02c" if pred == truth else "#d62728"))


def card(problem, solver, out):
    r = search_and_verify(solver, problem, seed=0)
    pos, neg = problem.batch(6, _CARD_SEED)

    fig, axes = plt.subplots(2, 6, figsize=(13, 4.8))
    for j, im in enumerate(pos):
        _show(axes[0, j], im, _verdict(solver, r.concept, im) if r.concept else False, True)
    for j, im in enumerate(neg):
        _show(axes[1, j], im, _verdict(solver, r.concept, im) if r.concept else False, False)
    axes[0, 0].set_ylabel("POSITIVES", fontsize=11)
    axes[1, 0].set_ylabel("NEGATIVES", fontsize=11)

    if r.concluded:
        banner = f"CONCLUDED: {r.concept.describe()}"
        bc = "#2ca02c"
    else:
        banner = f"ABSTAIN ({r.reason}) — {r.detail}"
        bc = "#d62728"
    fig.suptitle(f"Problem: “{problem.name}”   ·   {banner}", fontsize=13, color=bc, y=1.02)
    fig.tight_layout()
    path = os.path.join(out, f"m4_card_{problem.truth.template}.png")
    fig.savefig(path, dpi=125, bbox_inches="tight")
    print("wrote", path, "->", banner)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="./_pics")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    solver = Solver("bongard-m4-card")
    for problem in PROBLEMS:
        card(problem, solver, args.out)


if __name__ == "__main__":
    main()
