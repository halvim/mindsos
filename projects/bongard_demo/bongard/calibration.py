"""τ_fit calibration off the definitional triangle seed (PLAN §10 D).

Calibration is **circular** — you need ε to parse, and parses to calibrate
ε — so we bootstrap off the one shape with a known answer: the triangle
seed (PLAN §4 "the triangle seed is handed in"). A Global default band
makes the first parse possible; the seed parse then sets τ_fit from the
residual of the *correct* (3-vertex) candidate:

    τ_fit = (max accepted RMS over the seed parses) × (1 + slack)

"few examples, no training run" (PLAN §1). Stored Local-per-problem,
seeded by a Global default.

**G4 wiring.** Core ``invoke`` delivers a plain dict to read bodies and
hardcodes an empty ``learned_parameters`` for them (verified:
``capacity_layer.invoke`` only fills the snapshot for *write* bodies).
So the demo threads these params itself, via the read-path ``context``
dict under key ``"learned_parameters"`` (G7-safe: not a CapacityContext
field). The durable Local ``learned-parameters`` *node* write — the same
descriptor that backs the m2 mint — is the F9 path, deliberately out of
m1 scope; m1 calibrates in-memory.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

from . import geometry as G
from .leaf import _pixels_to_points, _points_to_boundary
from .ontology import PIXELS, POINT_SET, BOUNDARY_TRACE
from .render import Sample, calibration_seed
from .signals import is_dont_know

#: Context key the segments body reads its params from (G4).
PARAMS_CTX_KEY = "learned_parameters"


@dataclass(frozen=True)
class Params:
    """The Local per-problem parameter snapshot (PLAN §10 D/E/H).

    ``tau_fit``    — accept threshold on scale-normalized RMS (D); retained
                     for calibration provenance / aggregate sanity (the gate
                     is now per-edge, below).
    ``max_guard``  — abstain guard on scale-normalized max residual (D).
    ``per_edge_tau`` — worst per-edge RMS accepted (PLAN §10 D revision; the
                     curve discriminator, replaces the old ``max_sides`` cap).
    ``plateau_min_frac`` — min ε-persistence: the winning vertex count must
                     hold a plateau over ≥ this fraction of the valid sweep
                     steps (a curve's count wanders and fails this).
    ``lo_frac``/``hi_frac``/``k`` — the ε-sweep band + resolution (E/H);
                     widened + denser so the persistence plateau is resolved.
    """

    tau_fit: float = 0.012
    max_guard: float = 0.05
    per_edge_tau: float = 0.013   # admits small polygons (r≈22 tri @0.0105),
                                  # rejects bowtie hull (0.016); circle is
                                  # rejected by persistence, not this. Same
                                  # r≈20–55 band as tau_fit (per-problem
                                  # recalibration is the m2+ path).
    plateau_min_frac: float = 0.5
    lo_frac: float = 0.004
    hi_frac: float = 0.12
    k: int = 24

    def as_context(self) -> Dict[str, Dict]:
        return {PARAMS_CTX_KEY: asdict(self)}


#: Global default — seeds the very first (bootstrap) seed parse (PLAN §10 D
#: "stored Local per problem, seeded by a Global default").
GLOBAL_DEFAULT = Params()


def _trace(sample: Sample) -> Optional[List[G.Point]]:
    pts = _pixels_to_points(**{PIXELS.iri: sample.pixels})[POINT_SET.iri]
    bnd = _points_to_boundary(**{POINT_SET.iri: pts})[BOUNDARY_TRACE.iri]
    return None if is_dont_know(bnd) else bnd


def calibrate(seed: Optional[Sample] = None, *, slack: float = 0.6,
              floor: float = 0.012, base: Params = GLOBAL_DEFAULT) -> Params:
    """Derive a Local ``Params`` from the triangle seed's known answer.

    Runs the ε-sweep (Global-default band) on the seed, picks the
    candidate whose vertex count equals the seed's oracle count, and sets
    τ_fit from its RMS with slack (clamped to a floor). The floor is the
    pixelation-tolerance for the supported scale band (r≈20–55): a single
    r=40 seed under-estimates the worst-case (small-shape) residual,
    because normalized residual from 1px pixelation grows as ~1/size.
    Measured separation holds wide — polygons ≤0.008 across the band vs a
    circle at ~0.018 — so the floor sits comfortably between. Per-problem
    Local recalibration (PLAN §10 D) is the m2+ path. Band/cap inherit
    ``base``.
    """
    seed = seed or calibration_seed()
    assert seed.truth_vertices is not None, "seed must carry its oracle"
    target_n = len(seed.truth_vertices)
    trace = _trace(seed)
    assert trace is not None, "seed must trace"

    cands = G.epsilon_sweep(trace, k=base.k, lo_frac=base.lo_frac,
                            hi_frac=base.hi_frac)
    correct = [c for c in cands if c.n_vertices == target_n]
    assert correct, f"seed parse did not recover {target_n} vertices"
    seed_rms = min(c.rms for c in correct)
    tau = max(floor, seed_rms * (1.0 + slack))
    return Params(tau_fit=tau, max_guard=base.max_guard,
                  per_edge_tau=base.per_edge_tau,
                  plateau_min_frac=base.plateau_min_frac,
                  lo_frac=base.lo_frac, hi_frac=base.hi_frac, k=base.k)
