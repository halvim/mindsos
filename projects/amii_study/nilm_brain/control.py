"""L4 control — the Solver. Registers the brain, calibrates off a seed, and
drives cycle recognition.

Honest layering (arc, shipped level):
- **Composition** is the finder's job: the recognition segment
  (`cycle_model` + `signal_window` -> `cycle_verdict`) is composed once by
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

from collections import Counter
from typing import Dict, List

import numpy as np

from mindsos_capacity import CapacityLayer, capacity_iri
from mindsos_capacity import (
    CATEGORY_PERCEPTION, CATEGORY_DERIVATION,
)
from mindsos_capacity.identifiers import CATEGORY_DECISION
from mindsos_intelligence.pipeline_execution import execute_pipeline

from . import ontology as O
from . import references as R
from .harness import DuckSession
from .dispatch import CLDispatcher
from .perception import register_perception
from .derivation import register_derivation
from .scoring import register_scoring, default_params, fit_calibrate_params
from .decision import (
    register_decision, default_thresholds, fit_thresholds,
    default_signature_norm, fit_signature_norm,
    default_match_cutoff, fit_match_cutoff,
)
from .comprehension import register_comprehension, register_predicate
from .pipelines import compose_recognition_segment, compose_appliance_segment

# capacity IRIs L4 dispatches directly (the refinement loop)
_PARSE_RAW = capacity_iri(CATEGORY_PERCEPTION, "parse_raw")
_BIND      = capacity_iri(CATEGORY_DERIVATION, "bind")
_BIND_CUR  = capacity_iri(CATEGORY_DERIVATION, "bind_current")
_WINDOW    = capacity_iri(CATEGORY_DERIVATION, "window")
_FIT       = capacity_iri(CATEGORY_DERIVATION, "fit_reference")
_FFT       = capacity_iri(CATEGORY_DERIVATION, "fft")
_SPEC_FLAT = capacity_iri(CATEGORY_DERIVATION, "spectral_flatness")
_TEMP_FLAT = capacity_iri(CATEGORY_DERIVATION, "temporal_flatness")
_SYNTH     = capacity_iri(CATEGORY_DERIVATION, "synthesize")
_SUBTRACT  = capacity_iri(CATEGORY_DERIVATION, "subtract")
_NORMALIZE = capacity_iri(CATEGORY_DERIVATION, "normalize")
_HARM_PROFILE = capacity_iri(CATEGORY_DERIVATION, "harmonic_profile")
# appliance recognition (#3): onset + assemble + distance are L4-dispatched;
# power_features/current_harmonics/steady_signature run inside the segment.
_ONSET     = capacity_iri(CATEGORY_DERIVATION, "onset_features")
_ASSEMBLE  = capacity_iri(CATEGORY_DERIVATION, "assemble_signature")
_SIG_DIST  = capacity_iri(CATEGORY_DERIVATION, "signature_distance")
_RECOGNIZE = capacity_iri(CATEGORY_DECISION, "recognize")


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

        # Appliance recognition (#3): the taught instance library (k-NN exemplars)
        # and its learned L2 state (distance normalizer + negative-aware cutoff).
        self.appliance_library: List[Dict] = []
        self.signature_norm = default_signature_norm()
        self.match_cutoff = default_match_cutoff()

        # Compose the segments once (finder-composed; F1 gate). The appliance
        # signature segment is parallel to the cycle segment.
        self.segment = compose_recognition_segment(self.cl, self.session)
        self.appliance_segment = compose_appliance_segment(self.cl, self.session)

    # ── invoke helper (checks success — arc C7) ────────────────────────
    def _invoke(self, iri, inputs):
        r = self.cl.invoke(iri, inputs, session=self.session)
        if not r.success:
            raise RuntimeError(f"{iri} failed: {r.error!r}")
        return r.outputs

    # ── L4 refinement loop: signal + start -> (signal_window, cycle_model)
    def _refine_window(self, signal, start):
        g = self.given
        fe = float(g[O.F0.iri])
        vw = None; cm = None
        for _ in range(int(g[O.MAX_LOOP_ITERS.iri])):
            vw = self._invoke(_WINDOW, {
                O.SIGNAL.iri: signal, O.FREQ_ESTIMATE.iri: fe,
                O.WINDOW_CYCLES.iri: g[O.WINDOW_CYCLES.iri], O.FS.iri: g[O.FS.iri],
                O.WINDOW_START.iri: start,
            })[O.SIGNAL_WINDOW.iri]
            cm = self._invoke(_FIT, {
                O.SIGNAL_WINDOW.iri: vw, O.CYCLE_REFERENCE.iri: self.cycle_reference,
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
            O.CYCLE_MODEL.iri: cm, O.SIGNAL_WINDOW.iri: vw,
            O.FS.iri: g[O.FS.iri], O.F0.iri: g[O.F0.iri],
            O.HARMONIC_ORDERS.iri: g[O.HARMONIC_ORDERS.iri],
            O.HARMONIC_BANDWIDTH.iri: g[O.HARMONIC_BANDWIDTH.iri],
            O.N_TIME_BINS.iri: g[O.N_TIME_BINS.iri],
            O.CYCLE_MODEL_HISTORY.iri: list(history),
            O.CALIBRATE_PARAMS.iri: self.params,
            O.STRUCTUREDNESS_THRESHOLDS.iri: self.thresholds,
            O.REQUIRED_CONFIDENCE.iri: g[O.REQUIRED_CONFIDENCE.iri],
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
    def fit_calibrate(self, seed_raw, max_windows: int = 16, k: float = 3.0,
                      channel: str = "voltage"):
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
        vs = self._signal(seed_raw, channel)
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

    def _signal(self, raw, channel: str = "voltage"):
        """Parse the record and bind the chosen channel into the generic
        `signal` under analysis. `channel="voltage"` (grid-cycle recognition,
        the default) or `channel="current"` (appliance-signature recognition,
        #3). The downstream segment is channel-agnostic."""
        g = self.given
        p = self._invoke(_PARSE_RAW, {O.RAW_DATA.iri: raw, O.FS.iri: g[O.FS.iri],
                                      O.CHANNEL_MAP.iri: g[O.CHANNEL_MAP.iri]})
        if channel == "current":
            sig = self._invoke(_BIND_CUR, {O.CURRENT.iri: p[O.CURRENT.iri],
                                           O.TIME.iri: p[O.TIME.iri]})[O.SIGNAL.iri]
            # Amplitude-normalize the current: appliance currents span orders of
            # magnitude and the confidence gate is absolute-energy, so without
            # this a low-power switching load reads as a clean cycle (its
            # harmonics masked). Shape — the appliance signature — survives;
            # absolute power does not (resistive discrimination is the harder
            # follow-up that would keep power as a feature).
            return self._invoke(_NORMALIZE, {O.SIGNAL.iri: sig})[O.NORMALIZED_SIGNAL.iri]
        return self._invoke(_BIND, {O.VOLTAGE.iri: p[O.VOLTAGE.iri],
                                    O.TIME.iri: p[O.TIME.iri]})[O.SIGNAL.iri]

    # ── recognize: per-window cycle verdicts over a record ─────────────
    def recognize(self, raw_data, max_windows: int = 40,
                  channel: str = "voltage") -> List[Dict]:
        vs = self._signal(raw_data, channel)
        history: List[Dict] = []
        out: List[Dict] = []
        for start in self._window_starts(len(vs["values"]))[:max_windows]:
            vw, cm = self._refine_window(vs, start)
            bb = self._run_segment(cm, vw, history)
            history.append(cm)
            verdict = self._match_verdict(bb[O.CYCLE_VERDICT.iri], vw, cm)
            out.append({"start": start, "freq": cm["freq"],
                        "verdict": verdict,
                        "residual_energy": bb[O.RESIDUAL_ENERGY.iri],
                        "spectral": bb[O.SPECTRAL_CONCENTRATION.iri],
                        "temporal": bb[O.TEMPORAL_CONCENTRATION.iri],
                        "harmonic": bb[O.HARMONIC_FRACTION.iri],
                        "confidence": bb[O.CYCLE_CONFIDENCE.iri]})
        return out

    # ── the matcher (L4 §4 joint inference): resolve a request by matching the
    #    residual against the taught reference library ──────────────────────
    def _window_residual(self, vw, cm):
        """Recompute this window's residual via the real synthesize/subtract
        capacities (independent of blackboard internals)."""
        fs = float(self.given[O.FS.iri])
        recon = self._invoke(_SYNTH, {O.CYCLE_MODEL.iri: cm, O.SIGNAL_WINDOW.iri: vw,
                                      O.FS.iri: fs})[O.RECONSTRUCTED_WINDOW.iri]
        return self._invoke(_SUBTRACT, {O.SIGNAL_WINDOW.iri: vw,
                                        O.RECONSTRUCTED_WINDOW.iri: recon})[O.RESIDUAL.iri]

    def _templates(self):
        return [r for r in self.known_references if r.get("form") == "template"]

    def _match_verdict(self, verdict, vw, cm):
        """If the segment flagged `request_reference`, try each taught template
        against the residual (analysis-by-synthesis with the real caps). A
        template that reduces the leftover below BOTH structuredness gates
        *explains* the residual -> upgrade to `recognized[<name>]`. Confident-only
        (the §4 anti-hallucination invariant): no match -> the request stands."""
        if verdict["state"] != "request_reference" or not self._templates():
            return verdict
        residual = self._window_residual(vw, cm)
        best = self._match_references(residual)
        if best is None:
            return verdict
        return {**verdict, "state": "recognized", "reference": best,
                "structure": f"matched taught reference {best!r}"}

    def _ref_leftover(self, residual, ref):
        """Fit one template `ref` to `residual` and return the leftover's
        (spectral, temporal) concentration after subtracting the aligned+scaled
        template — how well this reference explains the residual."""
        g = self.given; fs = float(g[O.FS.iri])
        model = self._invoke(_FIT, {
            O.SIGNAL_WINDOW.iri: residual, O.CYCLE_REFERENCE.iri: ref,
            O.FREQ_ESTIMATE.iri: float(g[O.F0.iri]), O.FS.iri: fs,
            O.FREQ_SEARCH_FRAC.iri: g[O.FREQ_SEARCH_FRAC.iri],
            O.N_GRID.iri: g[O.N_GRID.iri]})[O.CYCLE_MODEL.iri]
        recon = self._invoke(_SYNTH, {O.CYCLE_MODEL.iri: model,
                                      O.SIGNAL_WINDOW.iri: residual,
                                      O.FS.iri: fs})[O.RECONSTRUCTED_WINDOW.iri]
        leftover = self._invoke(_SUBTRACT, {O.SIGNAL_WINDOW.iri: residual,
                                            O.RECONSTRUCTED_WINDOW.iri: recon})[O.RESIDUAL.iri]
        spec = self._invoke(_FFT, {O.RESIDUAL.iri: leftover,
                                   O.FS.iri: fs})[O.RESIDUAL_SPECTRUM.iri]
        ls = float(self._invoke(_SPEC_FLAT,
                                {O.RESIDUAL_SPECTRUM.iri: spec})[O.SPECTRAL_CONCENTRATION.iri])
        lt = float(self._invoke(_TEMP_FLAT, {O.RESIDUAL.iri: leftover,
                                             O.N_TIME_BINS.iri: g[O.N_TIME_BINS.iri]})[O.TEMPORAL_CONCENTRATION.iri])
        return ls, lt

    def _match_references(self, residual):
        th = self.thresholds
        best = None
        for ref in self._templates():
            ls, lt = self._ref_leftover(residual, ref)
            if ls < float(th["spectral"]) and lt < float(th["temporal"]):
                if best is None or lt < best[1]:
                    best = (ref["name"], lt)
        return best[0] if best else None

    def match_leftovers(self, raw, ref_name, channel: str = "voltage",
                        max_windows: int = 16):
        """Diagnostic: per window, the verdict state and the leftover
        (spectral, temporal) after matching the named template to the residual
        — whether or not it matched. Reveals memorization vs near-miss."""
        ref = next((r for r in self.known_references if r.get("name") == ref_name), None)
        if ref is None:
            raise RuntimeError(f"no reference {ref_name!r}")
        vs = self._signal(raw, channel)
        history: List[Dict] = []
        rows: List[Dict] = []
        for start in self._window_starts(len(vs["values"]))[:max_windows]:
            vw, cm = self._refine_window(vs, start)
            bb = self._run_segment(cm, vw, history)
            history.append(cm)
            ls, lt = self._ref_leftover(self._window_residual(vw, cm), ref)
            rows.append({"start": start, "state": bb[O.CYCLE_VERDICT.iri]["state"],
                         "leftover_spec": ls, "leftover_temp": lt})
        return rows

    # ── SPECTRAL appliance signature (test — the harmonic-magnitude profile) ──
    def _residual_profile(self, residual):
        """The residual's per-order harmonic profile (phase-invariant appliance
        signature), via the real fft + harmonic_profile capacities."""
        g = self.given; fs = float(g[O.FS.iri])
        spec = self._invoke(_FFT, {O.RESIDUAL.iri: residual, O.FS.iri: fs})[O.RESIDUAL_SPECTRUM.iri]
        prof = self._invoke(_HARM_PROFILE, {
            O.RESIDUAL_SPECTRUM.iri: spec, O.F0.iri: g[O.F0.iri],
            O.HARMONIC_ORDERS.iri: g[O.HARMONIC_ORDERS.iri],
            O.HARMONIC_BANDWIDTH.iri: g[O.HARMONIC_BANDWIDTH.iri]})[O.HARMONIC_AMPLITUDES.iri]
        return np.asarray(prof, dtype=float)

    def teach_spectral(self, name, example_raw, channel: str = "voltage",
                       max_windows: int = 40):
        """Teach an appliance's spectral signature: the MEAN harmonic profile
        over its `request_reference` windows (robust to per-window noise)."""
        vs = self._signal(example_raw, channel)
        history: List[Dict] = []
        profs = []
        for start in self._window_starts(len(vs["values"]))[:max_windows]:
            vw, cm = self._refine_window(vs, start)
            bb = self._run_segment(cm, vw, history)
            history.append(cm)
            if bb[O.CYCLE_VERDICT.iri]["state"] == "request_reference":
                profs.append(self._residual_profile(self._window_residual(vw, cm)))
        if not profs:
            raise RuntimeError(f"teach_spectral({name!r}): no request_reference window")
        ref = {"name": name, "form": "spectral",
               "profile": np.mean(np.asarray(profs), axis=0).tolist()}
        self.known_references = self.known_references + [ref]
        return ref

    def profile_similarities(self, raw, ref_name, channel: str = "voltage",
                             max_windows: int = 16):
        """Diagnostic: per-window cosine similarity of the window's harmonic
        profile to the named taught spectral signature. High for the taught
        appliance, low for others iff the signature discriminates."""
        ref = next((r for r in self.known_references
                    if r.get("name") == ref_name and r.get("form") == "spectral"), None)
        if ref is None:
            raise RuntimeError(f"no spectral reference {ref_name!r}")
        p0 = np.asarray(ref["profile"], dtype=float)
        vs = self._signal(raw, channel)
        history: List[Dict] = []
        sims = []
        for start in self._window_starts(len(vs["values"]))[:max_windows]:
            vw, cm = self._refine_window(vs, start)
            self._run_segment(cm, vw, history)
            history.append(cm)
            p = self._residual_profile(self._window_residual(vw, cm))
            sims.append(float(np.dot(p, p0) /
                              ((np.linalg.norm(p) * np.linalg.norm(p0)) + 1e-12)))
        return sims

    # ── teach: add ONE template reference from a flagged residual (§5) ──────
    def teach(self, name: str, example_raw, max_windows: int = 40,
              channel: str = "voltage") -> Dict:
        """The leaf-learning: run recognition on `example_raw`, take the residual
        of the MOST structured `request_reference` window, and register it as one
        new template reference under `name`. Additive — existing references are
        untouched (no forgetting)."""
        vs = self._signal(example_raw, channel)
        history: List[Dict] = []
        best = None                                  # (temporal_concentration, values)
        for start in self._window_starts(len(vs["values"]))[:max_windows]:
            vw, cm = self._refine_window(vs, start)
            bb = self._run_segment(cm, vw, history)
            history.append(cm)
            if bb[O.CYCLE_VERDICT.iri]["state"] == "request_reference":
                t = float(bb[O.TEMPORAL_CONCENTRATION.iri])
                if best is None or t > best[0]:
                    best = (t, self._window_residual(vw, cm)["values"])
        if best is None:
            raise RuntimeError(f"teach({name!r}): no request_reference window to learn from")
        ref = {"name": name, "form": "template",
               "template": np.asarray(best[1], dtype=float).tolist()}
        self.known_references = self.known_references + [ref]
        return ref

    # ── appliance recognition (#3): signature -> k-NN match -> recognized ────
    def _raw_channels(self, raw):
        """Parse and bind BOTH channels, RAW (un-normalized): appliance identity
        lives in absolute current + power factor, which the cycle path's
        normalize step removes. Returns (current_signal, voltage_signal)."""
        g = self.given
        p = self._invoke(_PARSE_RAW, {O.RAW_DATA.iri: raw, O.FS.iri: g[O.FS.iri],
                                      O.CHANNEL_MAP.iri: g[O.CHANNEL_MAP.iri]})
        cur = self._invoke(_BIND_CUR, {O.CURRENT.iri: p[O.CURRENT.iri],
                                       O.TIME.iri: p[O.TIME.iri]})[O.SIGNAL.iri]
        volt = self._invoke(_BIND, {O.VOLTAGE.iri: p[O.VOLTAGE.iri],
                                    O.TIME.iri: p[O.TIME.iri]})[O.SIGNAL.iri]
        return cur, volt

    def _run_appliance_segment(self, cw, vw):
        g = self.given
        disp = CLDispatcher(self.cl, self.session)
        inputs = {O.CURRENT_WINDOW.iri: cw, O.VOLTAGE_WINDOW.iri: vw,
                  O.F0.iri: g[O.F0.iri], O.FS.iri: g[O.FS.iri],
                  O.HARMONIC_ORDERS.iri: g[O.HARMONIC_ORDERS.iri]}
        res = execute_pipeline(disp, self.appliance_segment, inputs,
                               task_id="nilm-appliance")
        if not res.success:
            raise RuntimeError(f"appliance segment failed at {res.failed_step}: {res.error!r}")
        return res.outputs[O.STEADY_SIGNATURE.iri]

    def _appliance_signatures(self, raw, max_windows: int = 16):
        """Per-window full appliance signatures over a record: run the composed
        signature segment on each steady window, then assemble with the record's
        turn-on onset. Windows before the detected onset are skipped (transient
        belongs to the onset feature, not the steady signature)."""
        g = self.given
        cur, volt = self._raw_channels(raw)
        onset = self._invoke(_ONSET, {O.SIGNAL.iri: cur, O.FS.iri: g[O.FS.iri],
                                      O.F0.iri: g[O.F0.iri]})[O.ONSET_FEATURES.iri]
        n = len(cur["values"])
        skip = int(float(onset[1]) * n) + int(5 * g[O.FS.iri] / g[O.F0.iri])
        starts = [s for s in self._window_starts(n) if s >= skip][:max_windows]
        if not starts:
            starts = self._window_starts(n)[:max_windows]
        sigs = []
        for start in starts:
            win_in = {O.FREQ_ESTIMATE.iri: g[O.F0.iri],
                      O.WINDOW_CYCLES.iri: g[O.WINDOW_CYCLES.iri],
                      O.FS.iri: g[O.FS.iri], O.WINDOW_START.iri: start}
            cw = self._invoke(_WINDOW, {O.SIGNAL.iri: cur, **win_in})[O.SIGNAL_WINDOW.iri]
            vw = self._invoke(_WINDOW, {O.SIGNAL.iri: volt, **win_in})[O.SIGNAL_WINDOW.iri]
            steady = self._run_appliance_segment(cw, vw)
            full = self._invoke(_ASSEMBLE, {O.STEADY_SIGNATURE.iri: steady,
                                            O.ONSET_FEATURES.iri: onset})[O.APPLIANCE_SIGNATURE.iri]
            sigs.append(full)
        return sigs

    def _sig_distance(self, a, b):
        return float(self._invoke(_SIG_DIST, {
            O.APPLIANCE_SIGNATURE.iri: a, O.REFERENCE_SIGNATURE.iri: b,
            O.SIGNATURE_NORM.iri: self.signature_norm})[O.MATCH_DISTANCE.iri])

    def teach_appliance(self, name: str, record, max_windows: int = 16) -> Dict:
        """Leaf-learning for appliances: store this instance's PER-WINDOW
        signatures as k-NN exemplars under `name`, tagged with an instance id.
        Additive — many instances of a class become many exemplars (recognition
        matches window-to-window, so exemplars, not a mean); existing references
        untouched (no forgetting)."""
        sigs = self._appliance_signatures(record, max_windows)
        if not sigs:
            raise RuntimeError(f"teach_appliance({name!r}): no usable window")
        inst = 1 + max((r.get("inst", -1) for r in self.appliance_library), default=-1)
        refs = [{"name": name, "form": "signature", "inst": inst, "vector": s}
                for s in sigs]
        self.appliance_library = self.appliance_library + refs
        return {"name": name, "inst": inst, "exemplars": len(refs)}

    def fit_appliance(self, margin: float = 0.25):
        """Learn the L2 distance normalizer and the NEGATIVE-AWARE, INSTANCE-aware
        match cutoff off the taught library. `within` = nearest same-class
        exemplar from a DIFFERENT instance (same-instance pairs are trivially
        close and would bias the cutoff tight); `between` = nearest different-class
        exemplar. The cutoff sits between them (never set from positives blind —
        the §2.2 rule). `margin` is an L4 fit arg (no capacity consumes it)."""
        lib = self.appliance_library
        if not lib:
            raise RuntimeError("fit_appliance: empty library")
        self.signature_norm = fit_signature_norm([r["vector"] for r in lib])
        within, between = [], []
        for i, ri in enumerate(lib):
            same, diff = [], []
            for j, rj in enumerate(lib):
                if j == i:
                    continue
                if rj["name"] == ri["name"]:
                    if rj.get("inst") == ri.get("inst"):
                        continue                       # same instance -> skip
                    same.append(self._sig_distance(ri["vector"], rj["vector"]))
                else:
                    diff.append(self._sig_distance(ri["vector"], rj["vector"]))
            if same:
                within.append(min(same))
            if diff:
                between.append(min(diff))
        self.match_cutoff = fit_match_cutoff(within, between, margin)
        return self.match_cutoff

    def _match_appliance(self, sig, k: int):
        """L4 k-NN over the taught library (variable-size fan-out = iteration,
        not composition): the k nearest references vote; return the winner with
        its nearest in-class distance and vote confidence."""
        lib = self.appliance_library
        if not lib:
            return None
        ranked = sorted(((self._sig_distance(sig, r["vector"]), r["name"]) for r in lib),
                        key=lambda x: x[0])[:max(1, k)]
        names = [n for _, n in ranked]
        win = Counter(names).most_common(1)[0][0]
        nearest = min(d for d, n in ranked if n == win)
        return {"name": win, "distance": float(nearest),
                "confidence": names.count(win) / len(names)}

    def recognize_appliance(self, raw, max_windows: int = 16, k: int = 5) -> List[Dict]:
        """Per-window appliance verdicts: signature -> L4 k-NN vote -> the
        `recognize` decision capacity (recognized[name] | request_reference)."""
        out = []
        for sig in self._appliance_signatures(raw, max_windows):
            voted = self._match_appliance(sig, k)
            verdict = self._invoke(_RECOGNIZE, {O.VOTED_APPLIANCE.iri: voted,
                                                O.MATCH_CUTOFF.iri: self.match_cutoff})[O.APPLIANCE_VERDICT.iri]
            out.append({"signature": sig, "voted": voted, "verdict": verdict})
        return out


def build_solver(user_id: str = "nilm", **given) -> Solver:
    return Solver(user_id, given=build_given(**given) if given else None)
