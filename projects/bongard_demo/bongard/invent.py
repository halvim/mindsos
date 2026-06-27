"""m5 tier-1 — INVENT an atomic relation from the geometric atoms (PLAN m5
atom-grain block + the sizing result).

Where m4 SELECTED a concept from a closed library, m5 tier-1 DISCOVERS the
per-pair atomic relation that defines a concept, composed from the ontology
atoms (vertex-count, interior-angle, size) — `same_shape` is *invented*, not
handed in. This is m2's mint loop lifted from within-figure to across-figure.

Mechanism (the sizing study fixed the dedup):

1. parse train / held-out / probe scenes end-to-end through the real m3 chain
   (`parse_scene`), then extract each figure's atoms through the real
   `extract_shape_atoms` L3 capability (`cl.invoke`) — features come from a
   capability, the search is demo control (PLAN D-M5-12 / PB-10).
2. enumerate candidate atomic relations = (feature × aggregation); a candidate
   holds on a scene iff the per-pair comparator aggregates true.
3. keep candidates that separate the labelled TRAIN split;
4. keep those that match the labels on a larger labelled HELD-OUT (H1);
5. **dedup by divergence on a separate DECORRELATED probe (H2)** — survivors
   that never disagree on the probe are the same relation (collapse, e.g.
   `n==` ≡ `angle==` for regular polygons); survivors that disagree are
   genuinely distinct → abstain(ambiguous). (Deduping on H1 is degenerate —
   all survivors match truth there; that was the v1 bug.)
6. unique class → CONCLUDE + name (fixture, m2's name-at-teach-time); none →
   abstain(no_consistent / no_held_out_survivor); ≥2 → abstain(ambiguous).

The relation/comparator vocabulary is taught (authored once); the *combination*
is discovered. Only `n` is needed to invent `same_shape`; `angle` (redundant
encoding) + `size` (a confound/distractor) are included so the wired test
exercises collapse + the decorrelated-probe abstain on real parses.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations
from typing import Callable, Dict, List, Optional, Tuple

from mindsos_capacity import (
    COMPOSITE_DAG,
    Capacity,
    DAGEdge,
    DAGStep,
    DataState,
    Pipeline,
    REACTIVATION_KEY,
    ShapeDescriptor,
    register_reactivation_factory,
)
from mindsos_capacity.identifiers import CATEGORY_PREDICATE
from mindsos_capacity.pipeline import START

from .ontology import BONGARD_REALM, SCENE, SHAPE
from .scene import parse_scene
from .shapes import ATOMS, EXTRACT_IRI


# ── atom features of one parsed figure (n + angle via the L3 extractor; size
#    a derived absolute measure of the vertex ring) ─────────────────────────

def _bbox_diag(vertices) -> float:
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys))


#: feature name → (extractor over (atoms, shape), comparator tolerance).
#: tol == 0 → exact equality; tol > 0 → |a-b| ≤ tol.
FEATURES: Dict[str, Tuple[Callable, float]] = {
    "n":     (lambda a, s: float(a.n), 0.0),
    "angle": (lambda a, s: round(sum(a.interior_angles) / len(a.interior_angles), 3), 0.5),
    "size":  (lambda a, s: _bbox_diag(s.vertices), 4.0),
}
AGGREGATIONS = ("all", "exists")

#: every candidate atomic relation (feature × aggregation). `('n','all')` is
#: the `same_shape` target; the rest are redundant encodings / distractors.
CANDIDATES: Tuple[Tuple[str, str], ...] = tuple(
    (f, agg) for f in FEATURES for agg in AGGREGATIONS
)


def figure_features(atoms, shape) -> Dict[str, float]:
    return {name: ext(atoms, shape) for name, (ext, _tol) in FEATURES.items()}


def relation_holds(cand: Tuple[str, str], scene_feats: List[Dict[str, float]],
                   tol: Optional[float] = None) -> bool:
    """Does atomic relation ``cand`` hold on one scene's per-figure features?"""
    feature, agg = cand
    if tol is None:
        tol = FEATURES[feature][1]
    vals = [ff[feature] for ff in scene_feats]
    pairs = list(combinations(vals, 2))
    if not pairs:                      # singleton scene: vacuously not a relation
        return False
    held = [abs(a - b) <= tol for a, b in pairs]
    return all(held) if agg == "all" else any(held)


def describe(cand: Tuple[str, str]) -> str:
    feature, agg = cand
    comp = "==" if FEATURES[feature][1] == 0.0 else "≈"
    return f"{agg}-pairs[{feature} {comp}]"


# ── scene → per-figure features through the REAL parse + L3 extractor ───────

def scene_features(solver, image) -> Optional[List[Dict[str, float]]]:
    """Parse ``image`` and return per-figure atom features, or ``None`` if the
    parse abstained on any figure (a corrupt label — drop the scene)."""
    scene = parse_scene(solver, image)
    if scene.n_shapes == 0 or scene.n_abstained > 0:
        return None
    feats: List[Dict[str, float]] = []
    for sh in scene.shapes:
        atoms = solver.cl.invoke(
            EXTRACT_IRI, {SHAPE.iri: sh}, session=solver.session
        ).outputs[ATOMS.iri]
        feats.append(figure_features(atoms, sh))
    return feats


# ── the invention result ───────────────────────────────────────────────────

@dataclass(frozen=True)
class InventResult:
    status: str                              # "conclude" | "abstain"
    name: str = ""                           # fixture name on conclude
    relation: Optional[Tuple[str, str]] = None
    members: Tuple[Tuple[str, str], ...] = ()  # the collapsed equivalence class
    reason: str = ""                         # "" | "no_consistent" | "no_held_out_survivor" | "ambiguous"
    detail: str = ""

    @property
    def concluded(self) -> bool:
        return self.status == "conclude"


def _separates(cand, pos: List, neg: List) -> bool:
    return (all(relation_holds(cand, s) for s in pos)
            and not any(relation_holds(cand, s) for s in neg))


def _parsimony(cand: Tuple[str, str]) -> Tuple[int, int]:
    """Representative pick within a collapsed class (diagnostic): prefer an
    exact comparator and the most-fundamental feature (n < angle < size)."""
    feature, agg = cand
    feat_order = {"n": 0, "angle": 1, "size": 2}
    exact = 0 if FEATURES[feature][1] == 0.0 else 1
    return (exact, feat_order.get(feature, 9))


def invent_relation(
    solver, problem, *, name: str = "same_shape",
    n_train: int = 3, n_holdout: int = 10, n_probe: int = 12, seed: int = 0,
) -> InventResult:
    """Discover + name the atomic relation defining ``problem`` from atoms.

    ``problem`` exposes ``labelled(n, seed) -> (pos_images, neg_images)`` and
    ``probe(n, seed) -> images`` (a DECORRELATED, unlabelled batch).
    """
    tp = [f for im in problem.labelled(n_train, seed)[0] if (f := scene_features(solver, im))]
    tn = [f for im in problem.labelled(n_train, seed)[1] if (f := scene_features(solver, im))]
    hp = [f for im in problem.labelled(n_holdout, seed + 1)[0] if (f := scene_features(solver, im))]
    hn = [f for im in problem.labelled(n_holdout, seed + 1)[1] if (f := scene_features(solver, im))]
    probe = [f for im in problem.probe(n_probe, seed + 2) if (f := scene_features(solver, im))]

    # 3. train-consistency
    consistent = [c for c in CANDIDATES if _separates(c, tp, tn)]
    if not consistent:
        return InventResult("abstain", reason="no_consistent",
                            detail="no atomic relation separated the train split")

    # 4. labelled held-out survival (H1)
    held = hp + hn
    truth = tuple([True] * len(hp) + [False] * len(hn))
    survivors = [c for c in consistent
                 if tuple(relation_holds(c, s) for s in held) == truth]
    if not survivors:
        return InventResult("abstain", reason="no_held_out_survivor",
                            detail="train-consistent relation(s) failed held-out")

    # 5. dedup by divergence on the DECORRELATED probe (H2)
    classes: Dict[Tuple[bool, ...], List[Tuple[str, str]]] = {}
    for c in survivors:
        key = tuple(relation_holds(c, s) for s in probe)
        classes.setdefault(key, []).append(c)
    distinct = list(classes.values())

    # 6. verdict
    if len(distinct) >= 2:
        names = ", ".join(describe(min(cls, key=_parsimony)) for cls in distinct)
        return InventResult("abstain", reason="ambiguous",
                            detail=f"distinct relations survive, none separable on the probe: {{{names}}}")
    members = tuple(sorted(distinct[0], key=_parsimony))
    rep = members[0]
    return InventResult("conclude", name=name, relation=rep, members=members,
                        detail=f"{name} := {describe(rep)}"
                               + (f"  (≡ {', '.join(describe(m) for m in members[1:])})" if len(members) > 1 else ""))


# ── persistence: the named relation as a durable, reactivatable predicate ──
# The invented relation, once named (fixture — m2's name-at-teach-time, PB-H),
# is persisted exactly like an m2 minted shape: a `learned-parameters`
# descriptor carrying the relation spec + a COMPOSITE_DAG; a reactivation
# factory rebuilds a SCENE→bool predicate at boot that re-extracts atoms and
# evaluates the stored relation. Reuses the m2 mint machinery verbatim.

RELATION_REACTIVATION_KEY = "bongard_relation"


def _ds(suffix: str) -> DataState:
    name = f"{BONGARD_REALM}.{suffix}"
    return DataState(name=name, shape=ShapeDescriptor.opaque(name))


#: the bool verdict a reactivated invented-relation predicate produces.
RELATION_VERDICT = _ds("relation_verdict")


def relation_pipeline() -> Pipeline:
    """Minimal declarative body: SCENE → (extract atoms per figure + aggregate)
    → verdict. The per-figure extract loop is supplied by the runner closure
    at boot (the F9 pattern); the DAG records the shape for audit."""
    return Pipeline(
        start_datastates=(SCENE.iri,),
        target_datastate=RELATION_VERDICT.iri,
        steps=(DAGStep(EXTRACT_IRI, (SCENE.iri,), (RELATION_VERDICT.iri,)),),
        edges=(DAGEdge(START, 0, SCENE.iri),),
    )


def relation_descriptor(result: InventResult) -> dict:
    """The durable ``learned-parameters`` value dict for an invented relation."""
    feature, agg = result.relation
    return {
        "capability": result.name,
        REACTIVATION_KEY: RELATION_REACTIVATION_KEY,
        "category": CATEGORY_PREDICATE,
        "inputs": [SCENE.iri],
        "outputs": [RELATION_VERDICT.iri],
        "node_kind": "reactive",
        COMPOSITE_DAG: relation_pipeline().to_dict(),
        "relation": {"feature": feature, "agg": agg, "tol": FEATURES[feature][1]},
        "members": [list(m) for m in result.members],
    }


def relation_reactivation_factory(cl):
    """Rebuild a named-relation predicate: SCENE → re-extract atoms per figure
    → evaluate the stored (feature, agg, tol) → bool."""
    def factory(desc):
        spec = desc["relation"]
        cand = (spec["feature"], spec["agg"])
        tol = spec["tol"]
        out_iri = desc["outputs"][0]

        def run(**kw):
            ctx = kw.get("context") or {}
            session = ctx.get("session")
            scene = kw[SCENE.iri]
            feats: List[Dict[str, float]] = []
            for sh in scene.shapes:
                atoms = cl.invoke(EXTRACT_IRI, {SHAPE.iri: sh},
                                  session=session).outputs[ATOMS.iri]
                feats.append(figure_features(atoms, sh))
            return {out_iri: relation_holds(cand, feats, tol=tol)}

        return Capacity(
            name=desc["capability"], category=desc["category"],
            inputs=tuple(desc["inputs"]), outputs=tuple(desc["outputs"]),
            implementation=run,
        )

    return factory


def register_relation_reactivation(cl) -> None:
    """Register the invented-relation reactivation factory (idempotent)."""
    register_reactivation_factory(
        RELATION_REACTIVATION_KEY, relation_reactivation_factory(cl), if_exists="upsert"
    )


def register_relation_datastates(cl, session) -> None:
    """Register the invented-relation output DataState (must run at boot, like
    m2's ``register_shapes`` registers ``DEFINITION_MATCH``, so a reactivated
    relation's declared output is known on a fresh CapacityLayer)."""
    cl.register_datastate(RELATION_VERDICT, session=session, allow_new_realm=True)


def register_invented_relation(solver, result: InventResult) -> str:
    """In-memory register the concluded relation as a SCENE→bool predicate
    (usable immediately); returns its capability IRI. Durable persistence to
    Local ``learned-parameters`` + cross-process restart is the m2 mint path
    (Linux-gated), driven from the same descriptor."""
    register_relation_datastates(solver.cl, solver.session)
    register_relation_reactivation(solver.cl)
    decl = relation_reactivation_factory(solver.cl)(relation_descriptor(result))
    solver.cl.register_capacity(decl, session=solver.session, if_exists="upsert")
    return decl.iri


def mint_relation(solver, kl, persister, result: InventResult) -> str:
    """Durably mint the invented relation Local (restart-safe; the m2 path).

    Writes the relation descriptor into the user's Local ``learned-parameters``
    → persists → registers the predicate now. Survives a fresh-process restart
    via ``boot_local`` reactivation (Linux-gated). Returns the capability IRI.
    """
    from mindsos_knowledge import (
        ROLE_LEARNED_PARAMETERS,
        ensure_local_role_graph,
        learned_parameter_iri,
    )
    from mindsos_knowledge.schemas.learned_parameters import NODE_LEARNED_PARAMETER

    descriptor = relation_descriptor(result)
    user_id = solver.session.user_id
    local_mg = kl.local_metagraph(user_id)
    g = ensure_local_role_graph(local_mg, ROLE_LEARNED_PARAMETERS)
    g.add_node(
        dict(descriptor), NODE_LEARNED_PARAMETER,
        properties={"parameter_set_iri": f"invented:{result.name}", "confidence": 1.0},
        node_id=learned_parameter_iri("v1", result.name),
    )
    persister.save(user_id, local_mg)

    register_relation_datastates(solver.cl, solver.session)
    register_relation_reactivation(solver.cl)
    decl = relation_reactivation_factory(solver.cl)(descriptor)
    solver.cl.register_capacity(decl, session=solver.session, if_exists="upsert")
    return decl.iri
