"""Concept layer — a concept is a declarative predicate over the scene parse
(PLAN §6 / m4 design block D-M4-1/3/4).

A :class:`ConceptCandidate` is **declarative data** (a closed-set
``template`` id + bound ``params``), not a Python lambda — auditable and,
later (m5), persistable/promotable. ``evaluate_concept`` is the single L3
``CATEGORY_PREDICATE`` capacity that executes a candidate against one parsed
scene; it consumes ``SCENE`` + ``RELATION_SET`` + ``CONCEPT_CANDIDATE`` and
produces a hard ``CONCEPT_VERDICT`` bool (the verdict lives in a capability —
G5/PB-10). The search + held-out loop that *selects* among candidates is demo
control (``search.py``), not this capacity — and the L3 *selection learner*
is deferred to m5 (it is only needed when a concluded concept must
persist/promote).

m4 **SELECTS** from this CLOSED template library; it does **not** discover
new templates — growing the library is m5 (the real thesis test, PLAN §11).

First-slice library (D-M4-8):

* ``all_same_shape`` — every figure shares one polygon type. Evaluated over
  the m3 ``RelationSet`` (``|same_shape rels| == C(n,2)`` ∧ n≥2) so the
  m3→m4 dataflow is load-bearing, not decorative.
* ``count_eq(k)`` — the scene has exactly ``k`` solved figures.
* ``exists_type(t)`` — at least one figure of polygon type ``t``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Tuple

from mindsos_capacity import Capacity, DataState, ShapeDescriptor
from mindsos_capacity.identifiers import CATEGORY_PREDICATE

from .ontology import BONGARD_REALM, SCENE, RELATION_SET
from .relations import REL_SAME_SHAPE


def _ds(suffix: str) -> DataState:
    name = f"{BONGARD_REALM}.{suffix}"
    return DataState(name=name, shape=ShapeDescriptor.opaque(name))


#: A candidate concept handed to ``evaluate_concept`` as an input value.
CONCEPT_CANDIDATE = _ds("concept_candidate")
#: The hard bool verdict produced by ``evaluate_concept``.
CONCEPT_VERDICT = _ds("concept_verdict")

CONCEPT_DATASTATES: Tuple[DataState, ...] = (CONCEPT_CANDIDATE, CONCEPT_VERDICT)

EVALUATE_CONCEPT_IRI = f"capacity:{CATEGORY_PREDICATE}:evaluate_concept"

# ── closed template library (D-M4-1: m4 selects from THIS; m5 grows it) ──
TEMPLATE_ALL_SAME = "all_same_shape"
TEMPLATE_COUNT_EQ = "count_eq"
TEMPLATE_EXISTS_TYPE = "exists_type"
TEMPLATES = (TEMPLATE_ALL_SAME, TEMPLATE_COUNT_EQ, TEMPLATE_EXISTS_TYPE)


@dataclass(frozen=True)
class ConceptCandidate:
    """A declarative concept = a closed-set template id + bound params.

    ``params`` is a tuple so the candidate is hashable/auditable (e.g.
    ``("count_eq", (3,))`` or ``("exists_type", ("triangle",))``)."""

    template: str
    params: Tuple[Any, ...] = field(default_factory=tuple)

    def describe(self) -> str:
        if self.template == TEMPLATE_ALL_SAME:
            return "ALL_SAME_SHAPE"
        if self.template == TEMPLATE_COUNT_EQ:
            return f"COUNT_EQ({self.params[0]})"
        if self.template == TEMPLATE_EXISTS_TYPE:
            return f"EXISTS({self.params[0]})"
        return f"{self.template}{self.params}"


def holds(candidate: ConceptCandidate, scene, relation_set) -> bool:
    """Does ``candidate`` hold on one parsed scene? (pure; the capability
    body is a thin wrapper around this so it is unit-testable directly)."""
    shapes = scene.shapes
    n = len(shapes)
    t = candidate.template
    if t == TEMPLATE_ALL_SAME:
        if n < 2:
            return False
        same = sum(1 for r in relation_set if r.rel_type == REL_SAME_SHAPE)
        return same == n * (n - 1) // 2
    if t == TEMPLATE_COUNT_EQ:
        return n == candidate.params[0]
    if t == TEMPLATE_EXISTS_TYPE:
        return any(s.polygon_type == candidate.params[0] for s in shapes)
    raise ValueError(f"unknown concept template: {t!r}")


def _evaluate_concept(**kw):
    scene = kw[SCENE.iri]
    relation_set = kw[RELATION_SET.iri]
    candidate = kw[CONCEPT_CANDIDATE.iri]
    return {CONCEPT_VERDICT.iri: holds(candidate, scene, relation_set)}


def register_concepts(cl, session) -> str:
    """Register the concept DataStates + the ``evaluate_concept`` predicate
    Local. Returns the capacity IRI."""
    for ds in CONCEPT_DATASTATES:
        cl.register_datastate(ds, session=session, allow_new_realm=True)
    cap = Capacity(
        name="evaluate_concept", category=CATEGORY_PREDICATE,
        inputs=(SCENE.iri, RELATION_SET.iri, CONCEPT_CANDIDATE.iri),
        outputs=(CONCEPT_VERDICT.iri,),
        implementation=_evaluate_concept,
        description="hard verdict: does a declarative concept candidate hold on a scene parse (m4)",
    )
    cl.register_capacity(cap, session=session)
    return cap.iri
