"""Decision family — `verdict`, the terminal router (§6.1 row 13).

One `cycle_verdict` DataState; its **value** carries the terminal state
(`cycle` / `held_ambiguity` / `request_reference`). A capacity has a fixed
output signature, so a branching terminal *type* is not expressible — the
three outcomes are values, and L4 routes on `cycle_verdict["state"]`. The
decision family's don't-know contract is VERDICT (family_rules.py): the verdict
IS the honest "what happened", including request_reference.

Routing (doc §6.1):
- confidence ≥ required_confidence                          -> `cycle`
- else, structured on an axis AND no known reference matches -> `request_reference`
  (names the axis + the structure the library can't explain)
- else (flat on both axes, low confidence)                  -> `held_ambiguity`

No literals: every gate value (`required_confidence`, per-axis thresholds, the
reference library) arrives as a DataState (arc D2 — no buried L3 knowledge).
"""

from __future__ import annotations

from mindsos_capacity import Capacity
from mindsos_capacity.identifiers import CATEGORY_DECISION

from .ontology import (
    CYCLE_MODEL, CYCLE_CONFIDENCE, SPECTRAL_CONCENTRATION, TEMPORAL_CONCENTRATION,
    KNOWN_REFERENCES, REQUIRED_CONFIDENCE, STRUCTUREDNESS_THRESHOLDS, CYCLE_VERDICT,
)


def default_thresholds() -> dict:
    """Bootstrap per-axis structuredness gates — the L2-learned band *before* a
    seed is fit (mirrors ``scoring.default_params``' GLOBAL_DEFAULT role). The
    0.5 values are a deliberately-uncommitted placeholder; they do NOT
    discriminate yet — fitting them off the clean-cycle seed is step 2 of open
    item #1. Held on the Solver and threaded into the segment exactly like
    ``calibrate_params`` — NOT a domain constant in ``build_given`` (doc §7:
    ``structuredness_thresholds`` is learned in L2, not a given)."""
    return {"spectral": 0.5, "temporal": 0.5}


def _verdict(**kw):
    cm = kw[CYCLE_MODEL.iri]
    conf = float(kw[CYCLE_CONFIDENCE.iri])
    sc = float(kw[SPECTRAL_CONCENTRATION.iri])
    tc = float(kw[TEMPORAL_CONCENTRATION.iri])
    known = kw[KNOWN_REFERENCES.iri]
    req = float(kw[REQUIRED_CONFIDENCE.iri])
    th = kw[STRUCTUREDNESS_THRESHOLDS.iri]

    base = {"reference": cm.get("reference"), "confidence": conf,
            "spectral": sc, "temporal": tc}

    if conf >= req:
        return {CYCLE_VERDICT.iri: {"state": "cycle", "axis": None, **base}}

    spectral_hit = sc >= float(th["spectral"])
    temporal_hit = tc >= float(th["temporal"])
    if spectral_hit or temporal_hit:
        # Residual carries structure. Does any KNOWN reference beyond the one
        # already fit explain it? In v0 the library is just cycle_reference,
        # already used -> nothing matches -> request a new reference.
        used = cm.get("reference")
        unused = [r for r in known if r.get("name") != used]
        axis = "spectral" if spectral_hit and sc >= tc else ("temporal" if temporal_hit else None)
        if not unused:
            return {CYCLE_VERDICT.iri: {
                "state": "request_reference", "axis": axis,
                "structure": f"unexplained {axis}-axis structure", **base}}
        return {CYCLE_VERDICT.iri: {"state": "held_ambiguity", "axis": axis,
                                    "structure": "multiple candidate references", **base}}

    return {CYCLE_VERDICT.iri: {"state": "held_ambiguity", "axis": None,
                                "structure": "low confidence, flat on both axes", **base}}


def register_decision(cl, session):
    caps = [
        Capacity(
            name="verdict", category=CATEGORY_DECISION,
            inputs=(CYCLE_MODEL.iri, CYCLE_CONFIDENCE.iri, SPECTRAL_CONCENTRATION.iri,
                    TEMPORAL_CONCENTRATION.iri, KNOWN_REFERENCES.iri,
                    REQUIRED_CONFIDENCE.iri, STRUCTUREDNESS_THRESHOLDS.iri),
            outputs=(CYCLE_VERDICT.iri,), implementation=_verdict,
            description="(model, confidence, structure, references) -> cycle_verdict",
        ),
    ]
    for c in caps:
        cl.register_capacity(c, session=session, if_exists="upsert")
    return [c.iri for c in caps]
