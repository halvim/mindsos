"""Concept-labelled scene generators for m5 tier-1 invention (test/demo
scaffolding; PLAN m5 atom-grain block + sizing result).

A *problem* exposes ``labelled(n, seed) -> (pos_images, neg_images)`` and
``probe(n, seed) -> images`` (a DECORRELATED, unlabelled batch used only to
dedup survivors by divergence — never labelled, the §5-F firewall). Figures
are rendered disjoint in the parseable band so the real m3 chain parses them.
"""

from __future__ import annotations

import random
from typing import List, Tuple

from . import render as R

#: disjoint slot centres per figure count (r-band keeps each parseable + gaps
#: > 0 so connected-components individuates them).
_SLOTS = {
    2: [(36, 64), (92, 64)],
    3: [(32, 40), (96, 40), (64, 98)],
    4: [(32, 32), (96, 32), (32, 96), (96, 96)],
}
NS = (3, 4, 5)            # triangle / square / pentagon (vertex counts)
RS = (22.0, 26.0, 30.0)   # absolute sizes (so the size feature varies)


def render_scene(types: List[int], rs: List[float]) -> "R.Image":
    slots = _SLOTS[len(types)]
    return R._compose([R._ngon_image(int(n), cx=cx, cy=cy, r=r, stroke=0)
                       for n, (cx, cy), r in zip(types, slots, rs)])


def _force_diff(types: List[int], rng: random.Random) -> List[int]:
    if len(set(types)) == 1:
        i = rng.randrange(len(types))
        types[i] = rng.choice([x for x in NS if x != types[i]])
    return types


def _decorrelated_probe(n: int, seed: int) -> List["R.Image"]:
    """Types and sizes drawn INDEPENDENTLY → separates an n-relation from a
    size-relation (the dedup probe)."""
    rng = random.Random(seed * 7 + 1)
    out = []
    for _ in range(n):
        k = rng.choice((2, 3, 4))
        out.append(render_scene([rng.choice(NS) for _ in range(k)],
                                [rng.choice(RS) for _ in range(k)]))
    return out


class AllSameProblem:
    """truth = all figures share one polygon-type (vertex-count)."""

    def labelled(self, n: int, seed: int) -> Tuple[List, List]:
        rng = random.Random(seed)
        pos, neg = [], []
        for _ in range(n):
            k = rng.choice((2, 3, 4)); t = rng.choice(NS)
            pos.append(render_scene([t] * k, [rng.choice(RS) for _ in range(k)]))
        for _ in range(n):
            k = rng.choice((2, 3, 4))
            types = _force_diff([rng.choice(NS) for _ in range(k)], rng)
            neg.append(render_scene(types, [rng.choice(RS) for _ in range(k)]))
        return pos, neg

    def probe(self, n: int, seed: int):
        return _decorrelated_probe(n, seed)


class NoiseProblem:
    """No in-language rule: the label is a coin flip independent of geometry
    → no atomic relation separates → abstain (the moat)."""

    def labelled(self, n: int, seed: int) -> Tuple[List, List]:
        rng = random.Random(seed + 999)

        def scene():
            k = rng.choice((2, 3, 4))
            return render_scene([rng.choice(NS) for _ in range(k)],
                                [rng.choice(RS) for _ in range(k)])
        return [scene() for _ in range(n)], [scene() for _ in range(n)]

    def probe(self, n: int, seed: int):
        return _decorrelated_probe(n, seed)


class ConfoundProblem:
    """size PERFECTLY tracks the label (pos = same type AND same size; neg =
    differ in both). Both the n- and size-relations survive labelled held-out;
    only the decorrelated probe separates them → abstain(ambiguous)."""

    def labelled(self, n: int, seed: int) -> Tuple[List, List]:
        rng = random.Random(seed + 77)
        pos, neg = [], []
        for _ in range(n):
            k = rng.choice((2, 3, 4)); t = rng.choice(NS); r = rng.choice(RS)
            pos.append(render_scene([t] * k, [r] * k))
        for _ in range(n):
            k = rng.choice((2, 3, 4))
            types = _force_diff([rng.choice(NS) for _ in range(k)], rng)
            rs = ([22.0, 30.0] + [rng.choice(RS) for _ in range(k)])[:k]
            neg.append(render_scene(types, rs))
        return pos, neg

    def probe(self, n: int, seed: int):
        return _decorrelated_probe(n, seed)
