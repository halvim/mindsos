"""L4 control — the Solver. Registers the brain, calibrates off a seed, and
drives cycle recognition.

Honest layering (arc, shipped level):
- **Composition** is the finder's job: the recognition segment
  (`cycle_model` + `voltage_window` -> `cycle_verdict`) is composed once by
  `ConjunctionFinder` and executed by core's `execute_pipeline` — never a
  hand-rolled walk (D8).
- **Iteration/refinement** is L4's job (A4/C4): parse/bind, the window
  fan-out, and the repeat-until-converged 3-4 loop are Python control flow
  here, dispatching `window`/`fit_reference` by IRI.
- Every `invoke`/`dispatch` checks `success` (C7).

Rung 5 (mindsos's own orchestrator driving this) is out of reach until core
ships the WSD/phase-1 placeholders — same as both arc brains. Not faked.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from mindsos_capacity import CapacityLayer, capacity_iri
from mindsos_capacity import (
    CATEGORY_PERCEPTION, CATEGORY_DERIVATION,
)
from mindsos_intelligence.pipeline_execution import execute_pipeline

from . import ontology as O
from . import references as R
from .harness import DuckSession
from .dispatch import CLDispatcher
from .perception import register_perception
from .derivation import register_derivation
from .scoring import register_scoring, default_params, fit_calibrate_params
from .decision import register_decision, default_thresholds, fit_thresholds
from .comprehension import register_comprehension, register_predicate
from .pipelines import compose_recognition_segment

# capacity IRIs L4 dispatches directly (the refinement loop)
_PARSE_RAW = capacity_iri(CATEGORY_PERCEPTION, "parse_raw")
_BIND      = capacity_iri(CATEGORY_DERIVATION, "bind")
_WINDOW    = capacity_iri(CATEGORY_DERIVATION, "window")
_FIT       = capacity_iri(CATEGORY_DERIVATION, "fit_reference")
_FFT       = capacity_iri(CATEGORY_DERIVATION, "fft")
_SPEC_FLAT = capacity_iri(CATEGORY_DERIVATION, "spectral_flatness")
_TEMP_FLAT = capacity_iri(CATEGORY_DERIVATION, "temporal_flatness")


def build_given(**overrides) -> Dict[str, object]:
    """The caller-supplied domain constants for PLAID 2018, as DataState
    values (IRI -> value). These are *inputs the caller declares*, not
    literals inside any body. Override any of them per dataset/task.
    """
    g = {
        O.FS.iri: 30000.0,
        O.F0.iri: 60.0,
        O.V_NOM.iri: 120.0,
        O.CHANNEL_MAP.iri: {"current": 0, "voltage": 1},
        O.WINDOW_CYCLES.iri: 4,
        O.WINDOW_STEP.iri: 2,
        O.HARMONIC_ORDERS.iri: [2, 3, 4, 5, 6, 7],
        O.HARMONIC_BANDWIDTH.iri: 8.0,
        O.N_TIME_BINS.iri: 24,
        O.PERIOD_TOL.iri: 1e-4,
        O.FREQ_SEARCH_FRAC.iri: 0.02,
        O.N_GRID.iri: 21,
        O.MAX_LOOP_ITERS.iri: 6,
        O.REQUIRED_CONFIDENCE.iri: 0.9,
    }
    g.update(overrides)
    return g


class Solver:
    """A built NILM cycle-recognition brain over a pinned core (in-memory)."""

    def __init__(self, user_id: str = "nilm", *, given: Dict = None,
                 cl=None, session=None):
        self.cl = cl if cl is not None else CapacityLayer()
        self.session = session if session is not None else DuckSession(user_id)
        self.given = given if given is not None else build_given()

        O.register_ontology(self.cl, self.session)
        register_perception(self.cl, self.session)
        register_derivation(self.cl, self.session)
        register_scoring(self.cl, self.session)
        register_decision(self.cl, self.session)
        register_comprehension(self.cl, self.session)
        register_predicate(self.cl, self.session)

        self.cycle_reference = R.cycle_reference()
        self.known_references = R.known_references()
        self.params = default_params()          # until fit off a seed
        self.thresholds = default_thresholds()  # L2-learned gate; seed-fit is step 2 (#1b)

        # Compose the recognition segment once (finder-composed; F1 gate).
        self.segment = compose_recognition_segment(self.cl, self.session)

    # ── invoke helper (checks success — arc C7) ────────────────────────
    def _invoke(self, iri, inputs):
        r = self.cl.invoke(iri, inputs, session=self.session)
        if not r.success:
            raise RuntimeError(f"{iri} failed: {r.error!r}")
        return r.outputs

    # ── L4 refinement loop: signal + start -> (voltage_window, cycle_model)
    def _refine_window(self, voltage_signal, start):
        g = self.given
        fe = float(g[O.F0.iri])
        vw = None; cm = None
        for _ in range(int(g[O.MAX_LOOP_ITERS.iri])):
            vw = self._invoke(_WINDOW, {
                O.VOLTAGE_SIGNAL.iri: voltage_signal, O.FREQ_ESTIMATE.iri: fe,
                O.WINDOW_CYCLES.iri: g[O.WINDOW_CYCLES.iri], O.FS.iri: g[O.FS.iri],
                O.WINDOW_START.iri: start,
            })[O.VOLTAGE_WINDOW.iri]
            cm = self._invoke(_FIT, {
                O.VOLTAGE_WINDOW.iri: vw, O.CYCLE_REFERENCE.iri: self.cycle_reference,
                O.FREQ_ESTIMATE.iri: fe, O.FS.iri: g[O.FS.iri],
                O.FREQ_SEARCH_FRAC.iri: g[O.FREQ_SEARCH_FRAC.iri], O.N_GRID.iri: g[O.N_GRID.iri],
            })[O.CYCLE_MODEL.iri]
            if abs(cm["freq"] - fe) / fe < float(g[O.PERIOD_TOL.iri]):
                fe = cm["freq"]; break
            fe = cm["freq"]
        return vw, cm

    def _segment_inputs(self, cm, vw, history):
        g = self.given
        return {
            O.CYCLE_MODEL.iri: cm, O.VOLTAGE_WINDOW.iri: vw,
            O.FS.iri: g[O.FS.iri], O.F0.iri: g[O.F0.iri],
            O.HARMONIC_ORDERS.iri: g[O.HARMONIC_ORDERS.iri],
            O.HARMONIC_BANDWIDTH.iri: g[O.HARMONIC_BANDWIDTH.iri],
            O.N_TIME_BINS.iri: g[O.N_TIME_BINS.iri],
            O.CYCLE_MODEL_HISTORY.iri: list(history),
            O.CALIBRATE_PARAMS.iri: self.params,
            O.STRUCTUREDNESS_THRESHOLDS.iri: self.thresholds,
            O.REQUIRED_CONFIDENCE.iri: g[O.REQUIRED_CONFIDENCE.iri],
            O.KNOWN_REFERENCES.iri: self.known_references,
        }

    def _run_segment(self, cm, vw, history):
        disp = CLDispatcher(self.cl, self.session)
        res = execute_pipeline(disp, self.segment, self._segment_inputs(cm, vw, history),
                               task_id="nilm-cycle")
        if not res.success:
            raise RuntimeError(f"segment failed at {res.failed_step}: {res.error!r}")
        return res.outputs      # blackboard: all feature DataStates + cycle_verdict

    def _window_starts(self, n_samples):
        g = self.given
        wlen = int(round(int(g[O.WINDOW_CYCLES.iri]) * g[O.FS.iri] / g[O.F0.iri]))
        step = int(round(int(g[O.WINDOW_STEP.iri]) * g[O.FS.iri] / g[O.F0.iri]))
        return list(range(0, max(1, n_samples - wlen), step))

    # ── seed calibration: fit params off clean-cycle windows ───────────
    def fit_calibrate(self, seed_raw, max_windows: int = 16, k: float = 3.0):
        """Fit the learned L2 state off a clean-cycle seed. Runs the feature
        path on the seed's windows (calibrate's own output is ignored during
        the fit — we read the feature DataStates off the blackboard), then
        learns two things:
          - `calibrate_params` — the normal residual/harmonic band, so a healthy
            cycle scores high and a disturbance low (resolves the single-pass
            collapse);
          - `structuredness_thresholds` — the per-axis gates (step 1b), each set
            to `max(clean floor, noise floor)` so 'structured' means *more
            concentrated than BOTH a clean cycle and unstructured noise*. The
            noise floor is measured per window by `_noise_floor` (a white-noise
            surrogate through the real fft/flatness capacities); it is what binds
            the temporal axis, where a clean cycle is ~flat.
        `k` is an L4 fit hyperparameter (default 3.0), not a DataState."""
        g = self.given
        fs = float(g[O.FS.iri]); n_bins = g[O.N_TIME_BINS.iri]
        rng = np.random.default_rng(0)
        vs = self._voltage_signal(seed_raw)
        history: List[Dict] = []
        clean_feats: List[Dict] = []
        noise_feats: List[Dict] = []
        for start in self._window_starts(len(vs["values"]))[:max_windows]:
            vw, cm = self._refine_window(vs, start)
            bb = self._run_segment(cm, vw, history)
            clean_feats.append({"residual_energy": bb[O.RESIDUAL_ENERGY.iri],
                                "harmonic_fraction": bb[O.HARMONIC_FRACTION.iri],
                                "spectral_concentration": bb[O.SPECTRAL_CONCENTRATION.iri],
                                "temporal_concentration": bb[O.TEMPORAL_CONCENTRATION.iri]})
            noise_feats.append(self._noise_floor(len(vw["values"]), fs, n_bins, rng))
            history.append(cm)
        self.params = fit_calibrate_params(clean_feats)
        self.thresholds = fit_thresholds(clean_feats, noise_feats, k)
        return self.params

    def _noise_floor(self, n_samples, fs, n_bins, rng):
        """Measure the concentration an *unstructured* residual produces — the
        null the structuredness gate must clear. A white-noise surrogate of the
        window's length is pushed through the real `fft`/`spectral_flatness`/
        `temporal_flatness` capacities (concentration is scale-invariant, so
        unit-variance noise suffices; no duplicated numpy — the bodies own it,
        arc D4)."""
        surr = {"values": rng.standard_normal(int(n_samples))}
        spec = self._invoke(_FFT, {O.RESIDUAL.iri: surr,
                                   O.FS.iri: fs})[O.RESIDUAL_SPECTRUM.iri]
        return {
            "spectral_concentration": self._invoke(
                _SPEC_FLAT, {O.RESIDUAL_SPECTRUM.iri: spec})[O.SPECTRAL_CONCENTRATION.iri],
            "temporal_concentration": self._invoke(
                _TEMP_FLAT, {O.RESIDUAL.iri: surr,
                             O.N_TIME_BINS.iri: n_bins})[O.TEMPORAL_CONCENTRATION.iri],
        }

    def _voltage_signal(self, raw):
        g = self.given
        p = self._invoke(_PARSE_RAW, {O.RAW_DATA.iri: raw, O.FS.iri: g[O.FS.iri],
                                      O.CHANNEL_MAP.iri: g[O.CHANNEL_MAP.iri]})
        return self._invoke(_BIND, {O.VOLTAGE.iri: p[O.VOLTAGE.iri],
                                    O.TIME.iri: p[O.TIME.iri]})[O.VOLTAGE_SIGNAL.iri]

    # ── recognize: per-window cycle verdicts over a record ─────────────
    def recognize(self, raw_data, max_windows: int = 40) -> List[Dict]:
        vs = self._voltage_signal(raw_data)
        history: List[Dict] = []
        out: List[Dict] = []
        for start in self._window_starts(len(vs["values"]))[:max_windows]:
            vw, cm = self._refine_window(vs, start)
            bb = self._run_segment(cm, vw, history)
            history.append(cm)
            out.append({"start": start, "freq": cm["freq"],
                        "verdict": bb[O.CYCLE_VERDICT.iri],
                        "residual_energy": bb[O.RESIDUAL_ENERGY.iri],
                        "spectral": bb[O.SPECTRAL_CONCENTRATION.iri],
                        "temporal": bb[O.TEMPORAL_CONCENTRATION.iri],
                        "harmonic": bb[O.HARMONIC_FRACTION.iri],
                        "confidence": bb[O.CYCLE_CONFIDENCE.iri]})
        return out


def build_solver(user_id: str = "nilm", **given) -> Solver:
    return Solver(user_id, given=build_given(**given) if given else None)
