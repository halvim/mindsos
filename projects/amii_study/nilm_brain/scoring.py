"""Scoring family — `calibrate`, the one learned capacity (§6, marked **L**).

The learned content lives in L2 (a `calibrate_params` value); the capacity
structure is fixed. Params are fit off a **clean-cycle seed** — a window whose
known answer is "this is a healthy grid cycle" — exactly bongard's
definitional-seed calibration ("few examples, no training run"). That seed
sets *how much residual is normal for a healthy cycle*, which is precisely the
tolerance the design lacked when every window collapsed to request_reference.

v0 threads `calibrate_params` as a DataState value seeded into the blackboard
(no hidden context). Persisting it as a durable L2 `learned-parameters` node
is v1 (arc3 B6). The scoring family's don't-know contract is OPTIONAL_RETURN:
the body returns ``None`` if it cannot score (never here — features are always
present once the segment runs).
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from mindsos_capacity import Capacity, CATEGORY_SCORING

from .ontology import (
    RESIDUAL_ENERGY, HARMONIC_FRACTION, SPECTRAL_CONCENTRATION,
    TEMPORAL_CONCENTRATION, PERIOD_STABILITY, CALIBRATE_PARAMS, CYCLE_CONFIDENCE,
)

_EPS = 1e-12


def default_params() -> Dict:
    """Global default band — bootstraps the very first pass before a seed is
    fit (bongard's GLOBAL_DEFAULT role). Wide, deliberately uncommitted."""
    return {"energy_mean": 0.0, "energy_std": 1.0,
            "harmonic_mean": 0.0, "harmonic_std": 1.0,
            "provenance": "global_default"}


def fit_calibrate_params(seed_features: List[Dict]) -> Dict:
    """Learn the params from the clean-cycle seed's window features.

    The seed's known answer is "healthy cycle", so its residual_energy and
    harmonic_fraction define the *normal* band. Confidence later falls off as
    an observation departs from this band. "Few shots, no training run": this
    is a fit over a handful of seed windows, not a training loop.
    """
    e = np.array([f["residual_energy"] for f in seed_features], dtype=float)
    h = np.array([f["harmonic_fraction"] for f in seed_features], dtype=float)
    return {"energy_mean": float(np.mean(e)), "energy_std": float(np.std(e) + _EPS),
            "harmonic_mean": float(np.mean(h)), "harmonic_std": float(np.std(h) + _EPS),
            "provenance": f"seed_fit:{len(seed_features)}_windows"}


def _calibrate(**kw):
    re_ = float(kw[RESIDUAL_ENERGY.iri])
    ps = float(kw[PERIOD_STABILITY.iri])
    p = kw[CALIBRATE_PARAMS.iri]
    # Excess residual energy above the seed's normal band, in seed-sigmas.
    z = max(0.0, (re_ - p["energy_mean"]) / (p["energy_std"] + _EPS))
    energy_score = float(np.exp(-0.5 * z * z))     # 1 when energy is seed-normal
    confidence = energy_score * ps                  # and the period is stable
    return {CYCLE_CONFIDENCE.iri: float(confidence)}


def register_scoring(cl, session):
    caps = [
        Capacity(
            name="calibrate", category=CATEGORY_SCORING,
            inputs=(RESIDUAL_ENERGY.iri, HARMONIC_FRACTION.iri,
                    SPECTRAL_CONCENTRATION.iri, TEMPORAL_CONCENTRATION.iri,
                    PERIOD_STABILITY.iri, CALIBRATE_PARAMS.iri),
            outputs=(CYCLE_CONFIDENCE.iri,), implementation=_calibrate,
            description="features + L2 params -> cycle_confidence (the only learned cap)",
        ),
    ]
    for c in caps:
        cl.register_capacity(c, session=session, if_exists="upsert")
    return [c.iri for c in caps]
