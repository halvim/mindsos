"""m5 tier-2 — DISCOVER a conjunction over invented + taught SCENE->bool
operands, and mint it as a referencing composite (PLAN D-M5-15/16, atom-grain
tier-2; the de-risk seam proven 60-green).

Where tier-1 INVENTED ``same_shape`` from atoms, tier-2 composes
``count_eq ∧ same_shape`` over the *persisted* invented relation + the taught
``count_eq`` operator — proving an invented relation is CONSUMED by a higher
tier (§14 growing vocabulary). The conjunction is shallow (bool AND bool) but
load-bearing: the basis contains the persisted invented IRI and NOT an authored
``all_same`` template (D-M5-13), so the consumption is real, not re-derived.

This is demo control (L4-style, G6): the per-operand verdict is an L3
``cl.invoke``; the loop owns only set-arithmetic (D-M5-2). Mechanism:

1. parse train / labelled-held-out (H1) scenes through the real m3 chain, and
   evaluate every operand once per scene (a SCENE->bool ``cl.invoke``);
2. enumerate conjunctions of ≤``max_len`` operands; keep those that separate
   the TRAIN split;
3. keep those perfect on the labelled held-out H1;
4. **minimality-reduce** (D-M5-3) — drop a conjunction if a proper subset also
   survives (the redundant-conjunct guard); the survivor whose every conjunct
   is load-bearing is the most-general boundary;
5. unique minimal survivor → CONCLUDE + mint (``compose.mint_composite``,
   referencing the operand IRIs); ≥2 distinct minimal → abstain(ambiguous);
   none → abstain(no_consistent / no_held_out_survivor).

No decorrelated probe: the operand set (same_shape + count_eq_k) is
non-redundant, so distinctness is syntactic + H1 (the repass — H2 was inert at
tier-2; it cured tier-1's redundant n/angle ENCODINGS, which do not exist here).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Dict, List, Tuple

from .compose import mint_composite, register_composite
from .ontology import SCENE
from .scene import parse_scene


@dataclass(frozen=True)
class ConjResult:
    status: str                       # "conclude" | "abstain"
    operands: Tuple[str, ...] = ()    # the concluded conjunction's operand IRIs
    reason: str = ""                  # "" | "no_consistent" | "no_held_out_survivor" | "ambiguous"
    survivors: Tuple[Tuple[str, ...], ...] = ()
    detail: str = ""

    @property
    def concluded(self) -> bool:
        return self.status == "conclude"


def _operand_bool(solver, iri: str, scene) -> bool:
    r = solver.cl.invoke(iri, {SCENE.iri: scene}, session=solver.session)
    if not r.success:
        raise r.error
    return bool(next(iter(r.outputs.values())))


def _scene_vec(solver, operands: List[str], scene) -> Dict[str, bool]:
    """Evaluate every operand once on one parsed scene (cached for the search)."""
    return {iri: _operand_bool(solver, iri, scene) for iri in operands}


def _conj_holds(conj: Tuple[str, ...], vec: Dict[str, bool]) -> bool:
    return all(vec[iri] for iri in conj)


def discover_conjunction(
    solver, problem, operands: List[str], *, name: str = "discovered",
    n_train: int = 4, n_holdout: int = 8, seed: int = 0, max_len: int = 2,
    mint: bool = False, kl=None, persister=None,
) -> ConjResult:
    """Discover the minimal conjunction over ``operands`` that defines
    ``problem`` (``problem.batch(n, seed) -> (pos_images, neg_images)``).

    On a unique conclude, persists the conjunction: ``mint_composite`` (durable
    Local, restart-safe) when ``mint`` else ``register_composite`` (in-memory).
    """
    tp_imgs, tn_imgs = problem.batch(n_train, seed)
    hp_imgs, hn_imgs = problem.batch(n_holdout, seed + 1000)   # disjoint seed (firewall)

    def vecs(imgs):
        return [_scene_vec(solver, operands, parse_scene(solver, im)) for im in imgs]

    tp, tn = vecs(tp_imgs), vecs(tn_imgs)
    hp, hn = vecs(hp_imgs), vecs(hn_imgs)

    # 2. enumerate ≤max_len conjunctions + train-consistency
    cands: List[Tuple[str, ...]] = []
    for L in range(1, max_len + 1):
        cands += [tuple(c) for c in combinations(operands, L)]

    def separates(conj, pos, neg):
        return (all(_conj_holds(conj, v) for v in pos)
                and not any(_conj_holds(conj, v) for v in neg))

    consistent = [c for c in cands if separates(c, tp, tn)]
    if not consistent:
        return ConjResult("abstain", reason="no_consistent",
                          detail="no conjunction separated the train split")

    # 3. labelled held-out (H1) survival
    held = hp + hn
    truth = tuple([True] * len(hp) + [False] * len(hn))
    survivors = [c for c in consistent
                 if tuple(_conj_holds(c, v) for v in held) == truth]
    if not survivors:
        return ConjResult("abstain", reason="no_held_out_survivor",
                          detail="train-consistent conjunction(s) failed held-out")

    # 4. minimality — drop a survivor if a proper subset also survives.
    surv_set = set(survivors)

    def has_surviving_subset(c: Tuple[str, ...]) -> bool:
        for L in range(1, len(c)):
            for sub in combinations(c, L):
                if sub in surv_set:
                    return True
        return False

    minimal = sorted({c for c in survivors if not has_surviving_subset(c)},
                     key=lambda c: (len(c), c))

    # 5. verdict
    if len(minimal) >= 2:
        return ConjResult("abstain", reason="ambiguous", survivors=tuple(minimal),
                          detail=f"distinct minimal conjunctions survive: {minimal}")
    chosen = minimal[0]
    if mint:
        mint_composite(solver, kl, persister, name, list(chosen))
    else:
        register_composite(solver, name, list(chosen))
    return ConjResult("conclude", operands=tuple(chosen),
                      detail=f"{name} := AND{chosen}")
