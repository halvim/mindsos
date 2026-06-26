"""Multi-object scene parse — individuation + scene assembly (PLAN m3).

This is **demo control wiring (L4-style)**, NOT a registered capacity
(PLAN D-M3-4, consistent with the m1 control loop / G6): the core L4
orchestrator is a fixed six-phase whole-pipeline replan, so multi-object
orchestration lives here. The per-figure perception chain underneath is
still real ``cl.invoke`` (via ``Solver.perceive``); only the
*individuation + looping + assembly* is plain demo Python.

Individuation = **connected components** (PLAN D-M3-2): split the raster
foreground into 8-connected components, run the existing single-figure
``perceive`` on each, assemble a :class:`Scene`. A multi-figure image
that m1's topology gate would have rejected as ``structure`` (one raster,
many components) is now individuated *first*, so each component meets the
single-closed-stroke gate on its own.

**Overlapping / touching figures share one component → honest abstain**
(the moat working; clean Bongard-LOGO images are typically disjoint).
Separating touching figures needs the non-convex connectivity tracer —
deferred with that leaf swap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .control import Solver, Verdict
from .ontology import RELATION_SET, SCENE
from .predicate import Shape
from .render import Image, Sample


# ── individuation ──────────────────────────────────────────────────────

def _neighbours(x: int, y: int):
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx or dy:
                yield (x + dx, y + dy)


def connected_components(image: Image) -> List[Image]:
    """Split an Image's foreground into 8-connected components.

    Returns one sub-:class:`Image` per component (same canvas dims, only
    that component's foreground). Deterministic order: components are
    sorted by their top-left-most pixel so a scene parse is stable.
    """
    remaining = set(image.fg)
    comps: List[frozenset] = []
    while remaining:
        seed = next(iter(remaining))
        stack = [seed]
        remaining.discard(seed)
        comp = {seed}
        while stack:
            px = stack.pop()
            for nb in _neighbours(*px):
                if nb in remaining:
                    remaining.discard(nb)
                    comp.add(nb)
                    stack.append(nb)
        comps.append(frozenset(comp))
    comps.sort(key=lambda c: min((y, x) for (x, y) in c))
    return [Image(width=image.width, height=image.height, fg=c) for c in comps]


# ── scene artifact ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class Scene:
    """A parsed multi-object scene (the SCENE DataState payload).

    ``shapes`` are the solved figures (in individuation order); ``figures``
    holds the per-component :class:`Verdict` (so abstains are auditable,
    not silently dropped).
    """

    shapes: Tuple[Shape, ...]
    figures: Tuple[Verdict, ...] = field(default_factory=tuple)

    @property
    def n_shapes(self) -> int:
        return len(self.shapes)

    @property
    def n_abstained(self) -> int:
        return sum(1 for v in self.figures if not v.solved)


def parse_scene(solver: Solver, image: Image) -> Scene:
    """Individuate ``image`` into figures and parse each through ``Solver``.

    Demo control: connected-components individuation, then the real
    per-figure ``cl.invoke`` chain per component. Abstained components are
    retained in ``Scene.figures`` (auditable) but excluded from
    ``Scene.shapes``.
    """
    verdicts: List[Verdict] = []
    shapes: List[Shape] = []
    for sub in connected_components(image):
        sample = Sample(name="figure", pixels=sub, truth_vertices=None,
                        expect="", reason="")
        v = solver.perceive(sample)
        verdicts.append(v)
        if v.solved and v.shape is not None:
            shapes.append(v.shape)
    return Scene(shapes=tuple(shapes), figures=tuple(verdicts))


def scene_relations(solver: Solver, scene: Scene):
    """Extract relations over a parsed Scene through the real ``cl.invoke``.

    The relation extractor is a registered L3 predicate (PLAN D-M3-4); the
    Scene-collection is delivered as the single ``scene`` input (no Part-5
    operand collision). Returns the produced ``relation_set`` tuple.
    """
    r = solver.cl.invoke(solver.rel_iri, {SCENE.iri: scene},
                         session=solver.session)
    if not r.success:
        raise r.error
    return r.outputs[RELATION_SET.iri]
