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

import numpy as np

from mindsos_capacity import Capacity
from mindsos_capacity.identifiers import CATEGORY_DECISION

from .ontology import (
    CYCLE_MODEL, CYCLE_CONFIDENCE, SPECTRAL_CONCENTRATION, TEMPORAL_CONCENTRATION,
    REQUIRED_CONFIDENCE, STRUCTUREDNESS_THRESHOLDS, CYCLE_VERDICT,
    VOTED_APPLIANCE, MATCH_CUTOFF, APPLIANCE_VERDICT,
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


def fit_thresholds(clean_features: list, noise_features: list, k: float) -> dict:
    """Learn the per-axis structuredness gates off the clean-cycle seed (open
    item #1, step 1b). A residual is 'structured' on an axis only if its
    concentration exceeds **both** what a clean cycle shows **and** what
    unstructured noise shows — so each gate is::

        gate_axis = max( clean_mean + k·σ_clean ,  noise_mean + k·σ_noise )

    Why both floors: a steady cycle is near-flat on the *temporal* axis
    (concentration ~0), so the clean floor there is ~0 and would gate in even
    noise — the *noise* floor is what binds. On the *spectral* axis the clean
    grid harmonics dominate (concentration ~0.995), so the *clean* floor binds
    and the noise floor (~0.44) is irrelevant. `max` picks the right one per
    axis with no special-casing. `noise_features` are measured by running the
    real fft/flatness capacities on a white-noise surrogate (see
    ``Solver._noise_floor``).

    ``k`` is an L4 fit hyperparameter (passed by ``Solver.fit_calibrate``), NOT a
    DataState: no capacity consumes it, so registering it would be a dead (orphan)
    ontology node."""
    def _floor(feats, key):
        x = np.asarray([f[key] for f in feats], dtype=float)
        return float(np.mean(x) + k * np.std(x))

    return {
        "spectral": max(_floor(clean_features, "spectral_concentration"),
                        _floor(noise_features, "spectral_concentration")),
        "temporal": max(_floor(clean_features, "temporal_concentration"),
                        _floor(noise_features, "temporal_concentration")),
        "provenance": f"seed_fit:{len(clean_features)}w+noise_floor,k={k}",
    }


# ── appliance recognition (#3): learned norm + cutoff, and the decision ────

def default_signature_norm() -> dict:
    """Bootstrap per-dim standardizer for the signature distance (before a
    library is fit). Unit std = raw Euclidean; the real values are learned off
    the taught library (`fit_signature_norm`)."""
    return {"mean": [], "std": [], "provenance": "default:unit"}


def fit_signature_norm(vectors: list) -> dict:
    """Per-dim mean/std over the taught reference vectors — so no single feature
    axis (log-current vs a harmonic ratio) dominates the distance by its scale."""
    x = np.asarray(vectors, dtype=float)
    return {"mean": x.mean(0).tolist(), "std": (x.std(0) + 1e-9).tolist(),
            "provenance": f"library_fit:{len(vectors)}refs"}


def default_match_cutoff() -> dict:
    """Bootstrap match cutoff (before a library is fit). +inf = accept the
    nearest reference always; the real, negative-aware value is learned."""
    return {"cutoff": float("inf"), "provenance": "default:accept-all"}


def fit_match_cutoff(within: list, between: list, margin: float) -> dict:
    """Learn the nearest-distance cutoff for a valid match — NEGATIVE-AWARE: it
    sits between the taught classes' own within-class nearest distances and the
    cross-class (between) nearest distances, so it is not set from positives
    blind (the §2.2 'need negatives to place a boundary' rule). Falls back to the
    within-class spread when no negatives exist (single-class library).

        cutoff = mean(max within-class NN, min between-class NN), clamped so a
        genuine within-class neighbour always clears it.
    `margin` is an L4 fit arg (not a DataState — no capacity consumes it)."""
    w = np.asarray(within, dtype=float) if len(within) else np.asarray([0.0])
    hi_within = float(np.quantile(w, 0.9))
    if len(between):
        lo_between = float(np.quantile(np.asarray(between, dtype=float), 0.1))
        cut = 0.5 * (hi_within + lo_between)
        cut = max(cut, hi_within * (1.0 + margin))     # never reject a true neighbour
        prov = f"neg_aware:w90={hi_within:.3f},b10={lo_between:.3f}"
    else:
        cut = hi_within * (1.0 + margin)
        prov = f"within_only:w90={hi_within:.3f}"
    return {"cutoff": float(cut), "provenance": prov}


def _recognize(**kw):
    """Emit the appliance verdict from the L4 k-NN result and the learned cutoff.
    The vote (name, nearest distance, confidence) is computed in L4 over the
    variable library; THIS capacity is the honest decision: near enough ->
    `recognized[name]`, else `request_reference` (an unknown appliance to teach)."""
    voted = kw[VOTED_APPLIANCE.iri]
    cut = float(kw[MATCH_CUTOFF.iri]["cutoff"])
    if voted and float(voted["distance"]) <= cut:
        return {APPLIANCE_VERDICT.iri: {
            "state": "recognized", "appliance": voted["name"],
            "distance": float(voted["distance"]), "confidence": float(voted["confidence"])}}
    return {APPLIANCE_VERDICT.iri: {
        "state": "request_reference", "appliance": None,
        "distance": (float(voted["distance"]) if voted else None),
        "structure": "no taught appliance within the learned match cutoff"}}


def _verdict(**kw):
    cm = kw[CYCLE_MODEL.iri]
    conf = float(kw[CYCLE_CONFIDENCE.iri])
    sc = float(kw[SPECTRAL_CONCENTRATION.iri])
    tc = float(kw[TEMPORAL_CONCENTRATION.iri])
    req = float(kw[REQUIRED_CONFIDENCE.iri])
    th = kw[STRUCTUREDNESS_THRESHOLDS.iri]

    base = {"reference": cm.get("reference"), "confidence": conf,
            "spectral": sc, "temporal": tc}

    if conf >= req:
        return {CYCLE_VERDICT.iri: {"state": "cycle", "axis": None, **base}}

    spectral_hit = sc >= float(th["spectral"])
    temporal_hit = tc >= float(th["temporal"])
    if spectral_hit or temporal_hit:
        # Residual carries structure the base cycle_reference does not explain.
        # This is a *tentative* request: the L4 matcher (control.py) then tries
        # the taught reference library against the residual and may upgrade this
        # to `recognized[<name>]`. Real matching lives in L4 (§4 joint
        # inference), not a name-check here (that was the arc PB3 half-build).
        axis = "spectral" if spectral_hit and sc >= tc else ("temporal" if temporal_hit else None)
        return {CYCLE_VERDICT.iri: {
            "state": "request_reference", "axis": axis,
            "structure": f"unexplained {axis}-axis structure", **base}}

    return {CYCLE_VERDICT.iri: {"state": "held_ambiguity", "axis": None,
                                "structure": "low confidence, flat on both axes", **base}}


def register_decision(cl, session):
    caps = [
        Capacity(
            name="verdict", category=CATEGORY_DECISION,
            inputs=(CYCLE_MODEL.iri, CYCLE_CONFIDENCE.iri, SPECTRAL_CONCENTRATION.iri,
                    TEMPORAL_CONCENTRATION.iri,
                    REQUIRED_CONFIDENCE.iri, STRUCTUREDNESS_THRESHOLDS.iri),
            outputs=(CYCLE_VERDICT.iri,), implementation=_verdict,
            description="(model, confidence, structuredness) -> cycle_verdict "
                        "(cycle/request_reference/held_ambiguity; recognized is L4)",
        ),
        Capacity(
            name="recognize", category=CATEGORY_DECISION,
            inputs=(VOTED_APPLIANCE.iri, MATCH_CUTOFF.iri),
            outputs=(APPLIANCE_VERDICT.iri,), implementation=_recognize,
            description="(k-NN vote, learned cutoff) -> appliance_verdict "
                        "(recognized[name] | request_reference)",
        ),
    ]
    for c in caps:
        cl.register_capacity(c, session=session, if_exists="upsert")
    return [c.iri for c in caps]
