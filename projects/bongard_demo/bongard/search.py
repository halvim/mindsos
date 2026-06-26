"""Concept search + held-out verify — demo control (PLAN m4 D-M4-3/5/10).

This is **demo control wiring (L4-style)**, NOT a registered capacity (the
core orchestrator is a fixed six-phase whole-pipeline replan — G6); it drives
the L3 ``evaluate_concept`` predicate through real ``cl.invoke`` and owns the
select / verify / abstain decision the way the m1 control loop owns the
perception abstain (G5). The L3 *selection learner* is deferred to m5.

The loop (D-M4-10, the moat = Option 1):

1. parse each train/held-out image end-to-end through the real m3 chain →
   ``(Scene, RelationSet)``;
2. enumerate the CLOSED candidate library, params bound from the observed
   scenes (counts, types) — m4 SELECTS, it does not discover (D-M4-1);
3. keep candidates that perfectly separate the TRAIN split;
4. score survivors on a disjoint-seed HELD-OUT batch, keep the 100% ones;
5. **extensional dedup** — survivors with identical held-out verdicts are the
   same concept (different phrasing) → one representative;
6. **unique** distinct survivor → CONCLUDE; **≥2** distinct → ABSTAIN
   (ambiguous); **none** → ABSTAIN (no_consistent / no_held_out_survivor).

Parsimony is reported as a *diagnostic only*, never a tiebreak that forces an
answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .concepts import (ConceptCandidate, CONCEPT_CANDIDATE, CONCEPT_VERDICT,
                       TEMPLATE_ALL_SAME, TEMPLATE_COUNT_EQ, TEMPLATE_EXISTS_TYPE)
from .ontology import SCENE, RELATION_SET
from .scene import parse_scene, scene_relations


@dataclass(frozen=True)
class ConceptResult:
    status: str                       # "conclude" | "abstain"
    concept: Optional[ConceptCandidate] = None
    reason: str = ""                  # "" | "ambiguous" | "no_consistent" | "no_held_out_survivor"
    survivors: Tuple[ConceptCandidate, ...] = ()   # distinct held-out survivors
    detail: str = ""

    @property
    def concluded(self) -> bool:
        return self.status == "conclude"


_ParsedScene = Tuple[object, tuple]   # (Scene, relation_set tuple)


def _parse(solver, image) -> _ParsedScene:
    scene = parse_scene(solver, image)
    rels = scene_relations(solver, scene)
    return scene, rels


def _evaluate(solver, cand: ConceptCandidate, parsed: _ParsedScene) -> bool:
    scene, rels = parsed
    r = solver.cl.invoke(
        solver.concept_iri,
        {SCENE.iri: scene, RELATION_SET.iri: rels, CONCEPT_CANDIDATE.iri: cand},
        session=solver.session,
    )
    if not r.success:
        raise r.error
    return bool(r.outputs[CONCEPT_VERDICT.iri])


def _library(train: List[_ParsedScene]) -> List[ConceptCandidate]:
    """Closed template set with params bound from the observed train scenes."""
    counts = sorted({scene.n_shapes for scene, _ in train})
    types = sorted({s.polygon_type for scene, _ in train for s in scene.shapes})
    lib = [ConceptCandidate(TEMPLATE_ALL_SAME)]
    lib += [ConceptCandidate(TEMPLATE_COUNT_EQ, (k,)) for k in counts]
    lib += [ConceptCandidate(TEMPLATE_EXISTS_TYPE, (t,)) for t in types]
    return lib


def _separates(solver, cand, pos: List[_ParsedScene], neg: List[_ParsedScene]) -> bool:
    return (all(_evaluate(solver, cand, p) for p in pos)
            and not any(_evaluate(solver, cand, n) for n in neg))


def _arity(cand: ConceptCandidate) -> int:
    """Parsimony key (diagnostic only): fewer params + earlier template = simpler."""
    order = {TEMPLATE_ALL_SAME: 0, TEMPLATE_COUNT_EQ: 1, TEMPLATE_EXISTS_TYPE: 2}
    return (len(cand.params), order.get(cand.template, 9))


def search_and_verify(solver, problem, *, n_train: int = 4,
                      n_holdout: int = 12, seed: int = 0) -> ConceptResult:
    train_pos = [_parse(solver, im) for im in problem.batch(n_train, seed)[0]]
    train_neg = [_parse(solver, im) for im in problem.batch(n_train, seed)[1]]
    hp_imgs, hn_imgs = problem.batch(n_holdout, seed + 1000)   # disjoint seed (firewall)
    hold_pos = [_parse(solver, im) for im in hp_imgs]
    hold_neg = [_parse(solver, im) for im in hn_imgs]

    # 2–3. enumerate + train-consistency filter
    consistent = [c for c in _library(train_pos + train_neg)
                  if _separates(solver, c, train_pos, train_neg)]
    if not consistent:
        return ConceptResult("abstain", reason="no_consistent",
                             detail="no template separated the train split")

    # 4. held-out: keep candidates perfect on the disjoint batch
    held = [im for im in hold_pos + hold_neg]
    labels = [True] * len(hold_pos) + [False] * len(hold_neg)
    target = tuple(labels)
    survivors = [c for c in consistent
                 if tuple(_evaluate(solver, c, im) for im in held) == target]
    if not survivors:
        return ConceptResult("abstain", reason="no_held_out_survivor",
                             detail="train-consistent candidate(s) failed held-out")

    # 5–6. A 100%-survivor agrees with the labels on EVERY held-out scene, so
    # any two survivors are extensionally equal here — that equivalence IS the
    # ambiguity (the examples contain no scene that separates the two rules),
    # surfaced as an honest abstain rather than collapsed into a false
    # conclude. Unique survivor → conclude.
    if len(survivors) == 1:
        c = survivors[0]
        return ConceptResult("conclude", concept=c, survivors=(c,),
                             detail=f"concept = {c.describe()}")
    names = ", ".join(c.describe() for c in sorted(survivors, key=_arity))
    return ConceptResult("abstain", reason="ambiguous", survivors=tuple(survivors),
                         detail=f"examples consistent with {{{names}}} and contain no scene that separates them")
