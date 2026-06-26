"""Scene → relations — the m3 relation extractor (PLAN D-M3-1/3/4).

A single L3 ``predicate``-lane capacity that **consumes ONE ``scene``
DataState** (the Scene-collection route — one CONSUMES edge, no IRI
collision) and **produces a ``relation_set``**: a tuple of role-labeled
relation hyperedge records. The operand-role axis lives in the *output
data* (``subj``/``obj`` indices into the scene's shapes), not in the input
topology — so the unbuilt core Part 5 (operand-arity) is routed around,
not forced (PLAN D-M3-1 + CORE_CHANGES Part-5 note).

First slice = **attribute relations** (PLAN D-M3-3): pure functions of
already-parsed ``Shape`` fields — no new perception. ``same_shape``
(equal ``polygon_type``) is the shipped relation; ``larger_than`` /
``left_of`` (bbox-diagonal / centroid over ``Shape.vertices``) are cheap
follow-ons; topological relations (``inside`` / ``touching``) are deferred
(they need containment / intersection geometry).

Registered as a ``predicate`` (hard verdict over the parse, like
``is_polygon`` — G5); the category graph is created lazily on first
register (``CATEGORY_PREDICATE`` is not a ``FUNCTIONAL_CATEGORY``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from mindsos_capacity import Capacity
from mindsos_capacity.identifiers import CATEGORY_PREDICATE

from .ontology import SCENE, RELATION_SET

EXTRACT_RELATIONS_IRI = f"capacity:{CATEGORY_PREDICATE}:extract_relations"

#: Relation type vocabulary shipped this slice. ``symmetric`` records
#: whether ``subj``/``obj`` order is meaningful (it is not for
#: ``same_shape``) — kept so a downstream concept predicate can treat the
#: pair as unordered without re-deriving it.
REL_SAME_SHAPE = "same_shape"


@dataclass(frozen=True)
class Relation:
    """A role-labeled relation hyperedge over two scene shapes.

    ``subj`` / ``obj`` are indices into ``Scene.shapes`` (the hyperedge's
    role-bearing endpoints). Auditable: the roles are explicit data, not a
    positional invoke argument.
    """

    rel_type: str
    subj: int
    obj: int
    symmetric: bool = False


def _same_shape(shapes) -> Tuple[Relation, ...]:
    rels = []
    n = len(shapes)
    for i in range(n):
        for j in range(i + 1, n):
            if shapes[i].polygon_type == shapes[j].polygon_type:
                rels.append(Relation(REL_SAME_SHAPE, subj=i, obj=j,
                                     symmetric=True))
    return tuple(rels)


def _extract_relations(**kw):
    scene = kw[SCENE.iri]
    rels = _same_shape(scene.shapes)
    return {RELATION_SET.iri: rels}


def register_relations(cl, session) -> str:
    """Register the ``extract_relations`` predicate Local. Returns its IRI."""
    cap = Capacity(
        name="extract_relations", category=CATEGORY_PREDICATE,
        inputs=(SCENE.iri,), outputs=(RELATION_SET.iri,),
        implementation=_extract_relations,
        description="scene -> role-labeled relation hyperedges (same_shape; m3)",
    )
    cl.register_capacity(cap, session=session)
    return cap.iri
