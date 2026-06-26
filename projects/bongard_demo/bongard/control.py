"""Demo control loop — hypothesize → verify → {conclude | re-segment | abstain}.

This is **demo-built control wiring (L4-style)**, NOT shipped L4 — the core
orchestrator is a fixed six-phase whole-pipeline replan (G6), so the
per-figure backtrack loop lives here. It drives the registered L3
capacities through ``cl.invoke`` (the chain is real + auditable) and owns
the abstain / re-segment **verdict** (G5): the leaf emits a perception
marker, the predicate returns a hard bool, the gates live here.

Two abstain gates (PLAN §10 D) + bounded re-segment (PLAN §10 H):

- **fit gate** — ``segments`` returns ``DontKnow("fit")`` (curve / edge-
  decoration; the circle).
- **structure gate (topological)** — raster is not a single closed stroke
  (``open_strokes`` 2 components; ``near_miss`` open). Re-segmentation
  cannot repair stroke topology, so this abstains immediately, R=0 (PLAN
  §10 H "can't localize → abstain immediately").
- **structure gate (geometric)** — raster IS a single closed stroke but the
  fitted polygon is non-simple / non-closing (``bowtie``). This is a
  segmentation fault that re-segmentation *might* fix, so it triggers the
  **R=1** monotone re-segment (finer band, once); still invalid → abstain.

ParsePrior (F seam) is accepted as an optional consumed input (G7,
default unbound); rank-not-score; held-out is always parsed prior-free.
The ``re_rank`` body is deferred and never built for this instance (PLAN
§5 §F — clean Bongard yields no ambiguous-parse ties).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from . import geometry as G
from .calibration import GLOBAL_DEFAULT, Params, calibrate
from .leaf import register_leaf
from .ontology import (PIXELS, POINT_SET, BOUNDARY_TRACE, SEGMENT_SET,
                       VERTEX_SET, SHAPE, PARSE_PRIOR)
from .ontology import register_ontology
from .predicate import Shape, register_predicate
from .render import Sample
from .segments import register_segments
from .signals import DontKnow, is_dont_know
from .topology import analyze
from .harness import DuckSession

from mindsos_capacity import CapacityLayer


@dataclass(frozen=True)
class Verdict:
    """The control-loop outcome (a per-figure parse result)."""

    status: str               # "solve" | "abstain"
    shape: Optional[Shape] = None
    reason: str = ""          # "" | "fit" | "structure" | "trace"
    detail: str = ""
    resegmented: bool = False

    @property
    def solved(self) -> bool:
        return self.status == "solve"


class Solver:
    """A built Bongard perception instance over the pinned core."""

    def __init__(self, user_id: str = "bongard", *, cl=None, session=None,
                 register: bool = True):
        self.cl = cl if cl is not None else CapacityLayer()
        self.session = session if session is not None else DuckSession(user_id)
        if register:
            register_ontology(self.cl, self.session)
            register_leaf(self.cl, self.session)
            register_segments(self.cl, self.session)
            register_predicate(self.cl, self.session)
            from .relations import register_relations
            register_relations(self.cl, self.session)
            from .concepts import register_concepts
            register_concepts(self.cl, self.session)
        from .leaf import PIXELS_TO_POINTS_IRI, POINTS_TO_BOUNDARY_IRI
        from .segments import SEGMENTS_IRI, VERTICES_IRI
        from .predicate import PREDICATE_IRI
        from .relations import EXTRACT_RELATIONS_IRI
        from .concepts import EVALUATE_CONCEPT_IRI
        self.pix_iri, self.bnd_iri = PIXELS_TO_POINTS_IRI, POINTS_TO_BOUNDARY_IRI
        self.seg_iri, self.vts_iri = SEGMENTS_IRI, VERTICES_IRI
        self.pred_iri = PREDICATE_IRI
        self.rel_iri = EXTRACT_RELATIONS_IRI
        self.concept_iri = EVALUATE_CONCEPT_IRI
        # τ_fit + band calibrated off the definitional triangle seed (D).
        self.params: Params = calibrate()

    # ── chain steps (each a real cl.invoke) ────────────────────────────

    def _invoke(self, iri, inputs, ctx=None):
        r = self.cl.invoke(iri, inputs, session=self.session, context=ctx)
        if not r.success:                       # core raised inside a body
            raise r.error
        return r.outputs

    def _segment(self, boundary, params: Params):
        out = self._invoke(self.seg_iri, {BOUNDARY_TRACE.iri: boundary},
                           ctx=params.as_context())
        return out[SEGMENT_SET.iri]

    def _verify(self, seg) -> Shape:
        vts = self._invoke(self.vts_iri, {SEGMENT_SET.iri: seg})[VERTEX_SET.iri]
        return self._invoke(self.pred_iri,
                            {SEGMENT_SET.iri: seg, VERTEX_SET.iri: vts})[SHAPE.iri]

    # ── the loop ───────────────────────────────────────────────────────

    def perceive(self, sample: Sample, parse_prior=None) -> Verdict:
        # 1. grounding leaf: pixels -> point-set -> boundary trace
        pts = self._invoke(self.pix_iri, {PIXELS.iri: sample.pixels})[POINT_SET.iri]
        boundary = self._invoke(self.bnd_iri, {POINT_SET.iri: pts})[BOUNDARY_TRACE.iri]
        if is_dont_know(boundary):
            return Verdict("abstain", reason=boundary.reason, detail=boundary.detail)

        # 2. structure gate (topological) — raster must be a single closed
        #    stroke; re-segmentation cannot repair it (R=0).
        topo = analyze(sample.pixels)
        if not topo.is_single_closed_stroke:
            return Verdict("abstain", reason="structure",
                           detail=f"comps={topo.n_components} endpoints={topo.n_endpoints}")

        # 3. fit gate — segments | DontKnow("fit")
        seg = self._segment(boundary, self.params)
        if is_dont_know(seg):
            return Verdict("abstain", reason=seg.reason, detail=seg.detail)

        # 4. verify (predicate, hard bool)
        shape = self._verify(seg)
        if shape.valid:
            return Verdict("solve", shape=shape)

        # 5. structure gate (geometric) — R=1 monotone re-segment, once.
        tighter = replace(self.params, lo_frac=self.params.lo_frac / 2,
                          k=self.params.k + 4)
        seg2 = self._segment(boundary, tighter)
        if not is_dont_know(seg2):
            shape2 = self._verify(seg2)
            if shape2.valid:
                return Verdict("solve", shape=shape2, resegmented=True)
        return Verdict("abstain", reason="structure", detail=shape.detail,
                       resegmented=True)


def build_solver(user_id: str = "bongard") -> Solver:
    return Solver(user_id)
