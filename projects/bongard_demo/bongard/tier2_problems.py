"""Concept-labelled generators for m5 tier-2 (PLAN D-M5-15). Each exposes the
m4 ``batch(n, seed) -> (pos_images, neg_images)`` interface, so the SAME
problem object drives both tier-2's ``discover_conjunction`` and m4's
``search_and_verify`` — that lets a test assert the delta directly (m4 ABSTAINs
where tier-2 CONCLUDEs, same generator).

Reuses the tier-1 render machinery (``invent_problems.render_scene``). Kept in
the reliably-parseable regime: **2–3 figures only** (the 4-slot layout crowds
at these sizes → merged components → dropped figures, which silently corrupts
``count_eq``) and **triangles/squares only** (pentagons sit near the parse band
edge). ``discover_conjunction`` additionally skips any scene whose parse
abstained (the noise guard) — this just keeps the generators inside that guard.
"""

from __future__ import annotations

import random
from typing import List, Tuple

from .invent_problems import RS, render_scene

NS_T2 = (3, 4)            # triangle / square — the reliably-parseable types


def _mixed3(rng: random.Random) -> List[int]:
    """Three figures guaranteed to contain both a triangle and a square
    (so ``same_shape`` is False), with the third drawn freely."""
    types = [3, 4, rng.choice(NS_T2)]
    rng.shuffle(types)
    return types


class DeltaProblem:
    """``count_eq(3) ∧ all_same`` — the delta-vs-m4 case (D-M5-15).

    pos = exactly 3 figures, all one (varying) type.
    neg = 3 mixed-type (kills ``count_eq_3`` alone) OR 2 all-same (kills
    ``same_shape`` alone). NEITHER conjunct alone separates → m4 abstains,
    tier-2 concludes the conjunction (and consumes the invented ``same_shape``).
    Only 2- and 3-figure scenes → no 4-slot crowding.
    """

    K = 3

    def batch(self, n: int, seed: int) -> Tuple[List, List]:
        rng = random.Random(seed + 11)
        pos, neg = [], []
        for _ in range(n):
            t = rng.choice(NS_T2)
            pos.append(render_scene([t] * self.K, [rng.choice(RS) for _ in range(self.K)]))
        for i in range(n):
            if i % 2 == 0:                       # 3 mixed → count_eq_3 True, same_shape False
                neg.append(render_scene(_mixed3(rng), [rng.choice(RS) for _ in range(3)]))
            else:                                # 2 all-same → same_shape True, count_eq_3 False
                t = rng.choice(NS_T2)
                neg.append(render_scene([t] * 2, [rng.choice(RS) for _ in range(2)]))
        return pos, neg


class AllSameOnlyProblem:
    """``all_same`` alone separates; count fixed at 3 on BOTH sides so
    ``count_eq_3 ∧ all_same`` is train+H1 consistent but **non-minimal**.
    Tests minimality (D-M5-3): tier-2 must conclude ``same_shape`` alone, NOT
    the redundant conjunction. (Concludes the SAME concept m4 would — proves
    the guard, not a delta.)
    """

    K = 3

    def batch(self, n: int, seed: int) -> Tuple[List, List]:
        rng = random.Random(seed + 22)
        pos, neg = [], []
        for _ in range(n):
            t = rng.choice(NS_T2)
            pos.append(render_scene([t] * self.K, [rng.choice(RS) for _ in range(self.K)]))
        for _ in range(n):
            neg.append(render_scene(_mixed3(rng), [rng.choice(RS) for _ in range(self.K)]))
        return pos, neg


class NoRuleProblem:
    """Coin-flip label, independent of geometry → no conjunction separates →
    abstain (the moat). 2–3 figures, parseable types."""

    def batch(self, n: int, seed: int) -> Tuple[List, List]:
        rng = random.Random(seed + 33)

        def scene():
            k = rng.choice((2, 3))
            return render_scene([rng.choice(NS_T2) for _ in range(k)],
                                [rng.choice(RS) for _ in range(k)])

        return [scene() for _ in range(n)], [scene() for _ in range(n)]
