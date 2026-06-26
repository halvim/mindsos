"""Bongard instance ontology — built fresh in its own ``bongard.*`` realm.

Per PLAN §4/§5. The atom layer sits between Point and Shape: an ordered
boundary trace → straight **segments** → shared-endpoint **vertices** →
a closed-simple-loop **shape**. DataState descriptors are purely
structural (the core's rule: "semantic richness is not typed"); we use
opaque tags only to keep the shapes from auto-matching one another.

The ``bongard.*`` realm is a *new* (non-reserved) realm, so every
registration passes ``allow_new_realm=True`` against a Local session
(G0 — verified to need no core change). The perception-family don't-know
*marker* DataState is registered with the grounding leaf (see
``leaf.py``), not here, because that is where it is emitted (G8).
"""

from __future__ import annotations

from typing import Tuple

from mindsos_capacity import DataState, ShapeDescriptor

#: The instance's own realm (new, non-reserved; needs allow_new_realm).
BONGARD_REALM = "bongard"


def _ds(suffix: str) -> DataState:
    """A bongard.* DataState with an opaque, self-distinct shape.

    Milestone-1 perception passes rich Python objects (point lists,
    segment records, a Shape dict) between bodies; the core only needs a
    *structural* descriptor for finder/registration, so an opaque tag per
    suffix is sufficient and keeps any two atoms from auto-matching.
    """
    name = f"{BONGARD_REALM}.{suffix}"
    return DataState(name=name, shape=ShapeDescriptor.opaque(name))


# ── Ontology atoms (consumes → produces chain of PLAN §5) ──────────────

#: Raw input image (foreground/background pixel grid). The grounding leaf
#: consumes this; it is the swappable/domain-specific entry (PLAN §5).
PIXELS = _ds("pixels")

#: Foreground point-set (raw signal → normalized points). The reusable
#: grounding contract generalizes as "any point-set," not "any picture."
POINT_SET = _ds("point_set")

#: Ordered boundary trace (a cyclic ordering of the point-set boundary)
#: — the substrate the ε-sweep simplifier runs over (PLAN §10 E).
BOUNDARY_TRACE = _ds("boundary_trace")

#: Straight segments fitted to the boundary trace (grounding, line-art).
SEGMENT_SET = _ds("segment_set")

#: Shared-endpoint vertices derived from the segments (a vertex joins
#: exactly two segments — PLAN §4, not an infinite-line intersection).
VERTEX_SET = _ds("vertex_set")

#: A completed Shape{type, vertices, pose, confidence} — a closed simple
#: polygon (PLAN §4). Produced by the predicate verifier path.
SHAPE = _ds("shape")

#: ParsePrior — the F-seam top-down half (PLAN §5 §F), carried as a
#: *consumed* DataState (G7: never a CapacityContext field). Default
#: unbound; rank-not-score; held-out is always parsed prior-free.
PARSE_PRIOR = _ds("parse_prior")

#: m3 (PLAN D-M3-1) — a parsed multi-object scene: a tuple of solved
#: ``Shape`` over one image. The relation/concept capacities consume this
#: ONE collection (one CONSUMES edge, no IRI collision) and index pairs
#: internally — the Scene-collection route that sidesteps the unbuilt core
#: Part 5 (operand-arity). This *is* the §6 framing (concept = predicate
#: over the whole scene parse). Assembled by demo control, not a capacity.
SCENE = _ds("scene")

#: m3 (PLAN D-M3-1/D-M3-3) — the relations extracted over a Scene: a tuple
#: of role-labeled relation **hyperedge** records (``rel_type, subj, obj``
#: indices into the Scene's shapes). The role axis lives in the *output
#: data* (subj/obj explicit + auditable), NOT in the input topology — so no
#: core change. Produced by the ``extract_relations`` predicate.
RELATION_SET = _ds("relation_set")


#: Closed ontology atom set, in chain order. Registration order is not
#: load-bearing (each is independent), but kept chain-ordered for reading.
ONTOLOGY: Tuple[DataState, ...] = (
    PIXELS,
    POINT_SET,
    BOUNDARY_TRACE,
    SEGMENT_SET,
    VERTEX_SET,
    SHAPE,
    PARSE_PRIOR,
    SCENE,
    RELATION_SET,
)


def register_ontology(cl, session) -> dict:
    """Register every ontology atom into the session's Local DataState graph.

    Returns ``{iri: Node}``. Local-scoped (``session`` non-None) + a new
    realm, so each registration uses ``allow_new_realm=True``. A fresh
    ``CapacityLayer`` per instance keeps this a clean (non-duplicate)
    registration; re-registration on the same layer would raise by
    contract.
    """
    nodes = {}
    for ds in ONTOLOGY:
        nodes[ds.iri] = cl.register_datastate(
            ds, session=session, allow_new_realm=True
        )
    return nodes
