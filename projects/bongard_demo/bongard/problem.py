"""A *problem* = positive vs negative image sets, sampled from a held-out
generator (PLAN m4 D-M4-9, §3).

The generator is the **verifier**: search sees only a small TRAIN split; the
held-out batch is drawn from a *disjoint seed* (the §5-F held-out firewall,
applied to concepts). Two mirror-image problems (D-M4-8):

* ``all_same_shape`` — positives are all-one-type but **count varies** (2–4),
  so the ``count_eq`` distractor cannot fit; the type varies across positives,
  so ``exists_type`` cannot fit either → only ``all_same_shape`` survives.
* ``count_eq(3)`` — positives have exactly 3 figures of **mixed types**, so
  ``all_same_shape`` is always false on positives (cannot survive) and the
  varying types kill ``exists_type`` → only ``count_eq(3)`` survives.

Figures are placed disjointly in the parseable band (r=22, the m3
individuation precondition) so perception does not abstain and corrupt the
concept labels; scenes are parsed end-to-end through the real m3 chain.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, List, Tuple

from . import render
from .concepts import (ConceptCandidate, TEMPLATE_ALL_SAME, TEMPLATE_COUNT_EQ)

#: polygon types used by the generators (n-sides → name handled downstream).
TYPE_NS = (3, 4, 5)           # triangle, square, pentagon

#: Disjoint slot centres per figure count (r=22 keeps each in the band and
#: the gaps > 0 so connected-components individuates them — D-M3-2).
_SLOTS = {
    2: [(36, 64), (92, 64)],
    3: [(32, 40), (96, 40), (64, 98)],
    4: [(32, 32), (96, 32), (32, 96), (96, 96)],
}
_R = 22.0


def _render(type_ns: List[int]) -> "render.Image":
    slots = _SLOTS[len(type_ns)]
    imgs = [render._ngon_image(int(ns), cx=cx, cy=cy, r=_R)
            for ns, (cx, cy) in zip(type_ns, slots)]
    return render._compose(imgs)


def _not_all_same(types: List[int], rng: random.Random) -> List[int]:
    """Force at least one differing element (for negatives / mixed sets)."""
    if len(set(types)) == 1:
        i = rng.randrange(len(types))
        other = [t for t in TYPE_NS if t != types[i]]
        types[i] = rng.choice(other)
    return types


# ── generators ─────────────────────────────────────────────────────────

def gen_all_same(label: bool, rng: random.Random) -> "render.Image":
    n = rng.choice((2, 3, 4))                 # COUNT VARIES → kills count_eq
    if label:                                  # positive: all one (varying) type
        t = rng.choice(TYPE_NS)
        return _render([t] * n)
    types = [rng.choice(TYPE_NS) for _ in range(n)]   # negative: a differing pair
    return _render(_not_all_same(types, rng))


def gen_count_eq(label: bool, rng: random.Random, k: int = 3) -> "render.Image":
    if label:                                  # positive: exactly k, MIXED types
        types = [rng.choice(TYPE_NS) for _ in range(k)]
        return _render(_not_all_same(types, rng))   # mixed → kills all_same
    n = rng.choice([m for m in (2, 4) if m != k])    # negative: count != k
    types = [rng.choice(TYPE_NS) for _ in range(n)]
    return _render(types)


@dataclass(frozen=True)
class Problem:
    """A named problem + its latent truth concept (truth is for labelling /
    assertions only — it is NEVER handed to the search)."""

    name: str
    truth: ConceptCandidate
    gen: Callable[[bool, random.Random], "render.Image"]

    def batch(self, n_each: int, seed: int) -> Tuple[List, List]:
        """Draw ``n_each`` positives + ``n_each`` negatives at ``seed``."""
        rng = random.Random(seed)
        pos = [self.gen(True, rng) for _ in range(n_each)]
        neg = [self.gen(False, rng) for _ in range(n_each)]
        return pos, neg


ALL_SAME_PROBLEM = Problem(
    name="all figures share one shape",
    truth=ConceptCandidate(TEMPLATE_ALL_SAME),
    gen=gen_all_same,
)

COUNT_EQ_PROBLEM = Problem(
    name="exactly three figures",
    truth=ConceptCandidate(TEMPLATE_COUNT_EQ, (3,)),
    gen=gen_count_eq,
)

PROBLEMS = (ALL_SAME_PROBLEM, COUNT_EQ_PROBLEM)
