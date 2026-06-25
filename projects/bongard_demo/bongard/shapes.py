"""Atom-relation shape recognition (PLAN §4/§7, m2).

A minted shape is defined from a small universal atom basis — vertices
(count), segments (normalized lengths), angles (interior degrees) — by a
*conjunction of relations* over those atoms, not by an opaque feature
vector. ``square = n==4 ∧ sides-equal ∧ angles==90``. This is auditable,
compositional, and naturally scale/rotation-invariant (it compares atoms
to each other, not to absolute values).

Two tiers, per the §4 split between definitional schema and minted shape:

* **Definitional polygon law (built-in):** the interior angles of a
  simple n-gon sum to ``(n-2)·180``. A *validity* gate — it confirms a
  clean closed polygon but discriminates nothing among n-gons (every quad
  sums to 360). ``_angle_sum_ok``.
* **Minted definition (example-derived):** the relation set that defines
  one shape (count + side-equality + angle-target) with tolerances
  induced from the teach examples (formula sets each target value; the
  example spread sets the tolerance width, floored — the τ_fit discipline).

Three ``[SYSTEM]`` capacities so recognition lives in registered
capabilities, never in a Python closure (PB-10 attribution):
``extract_shape_atoms`` (SHAPE → ATOMS), ``induce_definition``
(ATOMS_SET → DEFINITION, the teach-time learning step), and the
``matches_definition`` predicate (ATOMS + DEFINITION → bool).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

from mindsos_capacity import (
    Capacity,
    CATEGORY_DERIVATION,
    DataState,
    ShapeDescriptor,
)
from mindsos_capacity.identifiers import CATEGORY_PREDICATE

from . import geometry as G
from .ontology import BONGARD_REALM, SHAPE


def _ds(suffix: str) -> DataState:
    name = f"{BONGARD_REALM}.{suffix}"
    return DataState(name=name, shape=ShapeDescriptor.opaque(name))


ATOMS = _ds("atoms")
ATOMS_SET = _ds("atoms_set")
SHAPE_DEFINITION = _ds("shape_definition")
DEFINITION_MATCH = _ds("definition_match")

EXTRACT_IRI = f"capacity:{CATEGORY_DERIVATION}:extract_shape_atoms"
INDUCE_IRI = f"capacity:{CATEGORY_DERIVATION}:induce_definition"
MATCHES_IRI = f"capacity:{CATEGORY_PREDICATE}:matches_definition"

SHAPE_DATASTATES: Tuple[DataState, ...] = (
    ATOMS, ATOMS_SET, SHAPE_DEFINITION, DEFINITION_MATCH,
)


@dataclass(frozen=True)
class ShapeAtoms:
    """The three atom measures of one parsed shape."""

    n: int
    sides_norm: Tuple[float, ...]      # side lengths / mean side (scale-free)
    interior_angles: Tuple[float, ...]


@dataclass(frozen=True)
class ShapeDefinition:
    """A minted shape definition (minimal slice: count + equal-sides +
    equal-angle-target). Extensible to per-side / per-angle relations."""

    n: int
    target_angle: float
    side_tol: float
    angle_tol: float


def atoms_of(vertices) -> ShapeAtoms:
    """Extract the three atom measures from an ordered vertex ring."""
    verts = list(vertices)
    n = len(verts)
    sides = [math.dist(verts[i], verts[(i + 1) % n]) for i in range(n)]
    mean = sum(sides) / n if n else 1.0
    sides_norm = tuple(s / mean for s in sides)
    angles = tuple(
        180.0 - G._turn_angle(verts[(i - 1) % n], verts[i], verts[(i + 1) % n])
        for i in range(n)
    )
    return ShapeAtoms(n=n, sides_norm=sides_norm, interior_angles=angles)


def angle_sum_ok(atoms: ShapeAtoms, rel_tol: float = 0.02) -> bool:
    """Definitional polygon law: interior angles sum to (n-2)·180."""
    expected = (atoms.n - 2) * 180.0
    return abs(sum(atoms.interior_angles) - expected) <= rel_tol * expected + 2.0


def induce_definition(
    examples: List[ShapeAtoms],
    *, margin: float = 1.5, side_floor: float = 0.06, angle_floor: float = 2.0,
) -> ShapeDefinition:
    """Induce the shared definition from teach examples.

    Vertex count must agree across positives. The per-angle target is the
    regular-n-gon formula ``(n-2)·180/n``; tolerances are the worst
    example deviation × ``margin``, floored (formula sets the centre,
    examples set the width — the τ_fit discipline)."""
    ns = {a.n for a in examples}
    if len(ns) != 1:
        raise ValueError(f"teach examples disagree on vertex count: {sorted(ns)}")
    n = ns.pop()
    target = (n - 2) * 180.0 / n
    side_dev = max(max(abs(s - 1.0) for s in a.sides_norm) for a in examples)
    ang_dev = max(max(abs(x - target) for x in a.interior_angles) for a in examples)
    return ShapeDefinition(
        n=n, target_angle=target,
        side_tol=max(side_dev * margin, side_floor),
        angle_tol=max(ang_dev * margin, angle_floor),
    )


def matches_definition(atoms: ShapeAtoms, definition: ShapeDefinition) -> bool:
    """Hard verdict: does a parse's atoms satisfy the minted definition?"""
    if not angle_sum_ok(atoms):
        return False
    if atoms.n != definition.n:
        return False
    if max(abs(s - 1.0) for s in atoms.sides_norm) > definition.side_tol:
        return False
    if max(abs(x - definition.target_angle) for x in atoms.interior_angles) > definition.angle_tol:
        return False
    return True


def _extract(**kw):
    shape = kw[SHAPE.iri]
    return {ATOMS.iri: atoms_of(shape.vertices)}


def _induce(**kw):
    return {SHAPE_DEFINITION.iri: induce_definition(list(kw[ATOMS_SET.iri]))}


def _matches(**kw):
    return {DEFINITION_MATCH.iri: matches_definition(kw[ATOMS.iri], kw[SHAPE_DEFINITION.iri])}


def register_shapes(cl, session) -> Tuple[str, str, str]:
    """Register the atom/definition DataStates + the three capacities Local.

    Returns ``(extract_iri, induce_iri, matches_iri)``."""
    for ds in SHAPE_DATASTATES:
        cl.register_datastate(ds, session=session, allow_new_realm=True)
    extract = Capacity(
        name="extract_shape_atoms", category=CATEGORY_DERIVATION,
        inputs=(SHAPE.iri,), outputs=(ATOMS.iri,),
        implementation=_extract,
        description="parse -> (n, normalized side lengths, interior angles)",
    )
    induce = Capacity(
        name="induce_definition", category=CATEGORY_DERIVATION,
        inputs=(ATOMS_SET.iri,), outputs=(SHAPE_DEFINITION.iri,),
        implementation=_induce,
        description="teach examples' atoms -> shared shape definition + tolerances",
    )
    matches = Capacity(
        name="matches_definition", category=CATEGORY_PREDICATE,
        inputs=(ATOMS.iri, SHAPE_DEFINITION.iri), outputs=(DEFINITION_MATCH.iri,),
        implementation=_matches,
        description="hard verdict: atoms satisfy the minted definition",
    )
    cl.register_capacity(extract, session=session)
    cl.register_capacity(induce, session=session)
    cl.register_capacity(matches, session=session)
    return extract.iri, induce.iri, matches.iri
