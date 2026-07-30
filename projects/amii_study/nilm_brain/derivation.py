"""Derivation family — the 17 single-step deterministic capacities (§6).

Every body **owns its numpy** (arc D4: a capacity whose body wraps an inline
oracle is a label, not a transition — there is no `probe.py` imported here).
Inputs arrive as `**kw` keyed by DataState IRI; each returns `{out_iri: value}`.
`eps` values below are numerical divide-by-zero guards, not decision constants
(every decision constant arrives as a DataState).

Cycle-path caps (compose + execute in the flagship pipeline): `bind`, `window`,
`fit_reference`, `synthesize`, `subtract`, `rms`, `fft`, `spectral_flatness`,
`temporal_flatness`, `band_energy`, `compare_across_windows`.
Secondary / acquisition caps (registered; serve power / harmonic_amplitudes /
future rungs): `multiply`, `normalize`, `angle`, `segment`, `count`,
`induce_structure`.
"""

from __future__ import annotations

import numpy as np

from mindsos_capacity import Capacity, CATEGORY_DERIVATION

from .ontology import (
    VOLTAGE, CURRENT, TIME, SIGNAL, CURRENT_SIGNAL, FREQ_ESTIMATE, WINDOW_CYCLES,
    WINDOW_START, FS, F0, SIGNAL_WINDOW, CYCLE_REFERENCE, FREQ_SEARCH_FRAC,
    N_GRID, CYCLE_MODEL, RECONSTRUCTED_WINDOW, RESIDUAL, RESIDUAL_ENERGY,
    RESIDUAL_SPECTRUM, SPECTRAL_CONCENTRATION, N_TIME_BINS, TEMPORAL_CONCENTRATION,
    HARMONIC_ORDERS, HARMONIC_BANDWIDTH, HARMONIC_FRACTION, HARMONIC_AMPLITUDES,
    CYCLE_MODEL_HISTORY,
    PERIOD_STABILITY, POWER, NORMALIZED_SIGNAL, PHASE, SEGMENTS, CYCLE_COUNT,
    INDUCED_STRUCTURE,
    CURRENT_WINDOW, VOLTAGE_WINDOW, RAW_HARMONICS, POWER_FEATURES,
    STEADY_SIGNATURE, ONSET_FEATURES, APPLIANCE_SIGNATURE, REFERENCE_SIGNATURE,
    SIGNATURE_NORM, MATCH_DISTANCE, APPLIANCE_LIBRARY, SCORED_LIBRARY,
    CURRENT_SIGNAL, VOLTAGE_SIGNAL,
)

_EPS = 1e-20
_PI = np.pi


def _shift(tmpl, lag, n):
    """Place `tmpl` into a length-`n` zero array at offset `lag`:
    out[i] = tmpl[i - lag] over the valid overlap. Used to align a taught
    template to an observation (shift-invariant template matching)."""
    out = np.zeros(n, dtype=float)
    dst0 = max(0, lag); dst1 = min(n, lag + len(tmpl))
    if dst1 > dst0:
        out[dst0:dst1] = tmpl[dst0 - lag:dst1 - lag]
    return out


# ── cycle-path bodies ──────────────────────────────────────────────────

def _bind(**kw):
    return {SIGNAL.iri: {"values": np.asarray(kw[VOLTAGE.iri], dtype=float),
                                 "time": np.asarray(kw[TIME.iri], dtype=float)}}


def _bind_current(**kw):
    """Bind the current channel into the generic `signal` under analysis — the
    current-channel sibling of `bind`. Same transition (value+time -> signal),
    distinct floor atom (current, not voltage). This is what lets the recognition
    segment run on current for appliance-signature recognition (#3)."""
    return {SIGNAL.iri: {"values": np.asarray(kw[CURRENT.iri], dtype=float),
                         "time": np.asarray(kw[TIME.iri], dtype=float)}}


def _window(**kw):
    vs = kw[SIGNAL.iri]
    fe = float(kw[FREQ_ESTIMATE.iri]); wc = float(kw[WINDOW_CYCLES.iri])
    fs = float(kw[FS.iri]); start = int(kw[WINDOW_START.iri])
    length = int(round(wc * fs / fe))
    v = vs["values"]; t = vs["time"]
    i1 = min(len(v), start + length)
    return {SIGNAL_WINDOW.iri: {"values": v[start:i1], "time": t[start:i1]}}


def _window_current(**kw):
    """Slice one analysis window from the CURRENT channel — the channel-specific
    sibling of `window` (current_signal -> current_window). Distinct input/output
    DataStates so a declared plan can window both channels: the sound finder fires
    one capacity per IRI, so two channels need two capacities (not `window` twice
    under one `signal` IRI)."""
    vs = kw[CURRENT_SIGNAL.iri]
    fe = float(kw[FREQ_ESTIMATE.iri]); wc = float(kw[WINDOW_CYCLES.iri])
    fs = float(kw[FS.iri]); start = int(kw[WINDOW_START.iri])
    length = int(round(wc * fs / fe))
    v = vs["values"]; t = vs["time"]
    i1 = min(len(v), start + length)
    return {CURRENT_WINDOW.iri: {"values": v[start:i1], "time": t[start:i1]}}


def _window_voltage(**kw):
    """Slice one analysis window from the VOLTAGE channel: voltage_signal ->
    voltage_window (channel-specific sibling of `window`)."""
    vs = kw[VOLTAGE_SIGNAL.iri]
    fe = float(kw[FREQ_ESTIMATE.iri]); wc = float(kw[WINDOW_CYCLES.iri])
    fs = float(kw[FS.iri]); start = int(kw[WINDOW_START.iri])
    length = int(round(wc * fs / fe))
    v = vs["values"]; t = vs["time"]
    i1 = min(len(v), start + length)
    return {VOLTAGE_WINDOW.iri: {"values": v[start:i1], "time": t[start:i1]}}


def _fit_reference(**kw):
    """Fit the L2 reference to the window. Basis comes from the reference
    (`form`), not from this body — the sinusoid knowledge lives in L2."""
    vw = kw[SIGNAL_WINDOW.iri]; ref = kw[CYCLE_REFERENCE.iri]
    fe = float(kw[FREQ_ESTIMATE.iri]); fs = float(kw[FS.iri])
    frac = float(kw[FREQ_SEARCH_FRAC.iri]); n = int(kw[N_GRID.iri])
    v = vw["values"]; t = vw["time"]
    if ref["form"] == "template":
        # Match a taught template to the observation, SHIFT-INVARIANTLY: the
        # signature sits at a different offset in each window (periodic current,
        # or a disturbance the window catches at a different phase). Cross-
        # correlate to find the best lag, align, then least-squares scale. Basis
        # = the stored residual shape, so the knowledge lives in the L2 reference.
        tmpl = np.asarray(ref["template"], dtype=float)
        vv = np.asarray(v, dtype=float)
        corr = np.correlate(vv, tmpl, mode="full")
        lag = int(np.argmax(np.abs(corr))) - (len(tmpl) - 1)
        ts = _shift(tmpl, lag, len(vv))
        scale = float(np.dot(vv, ts) / (float(np.dot(ts, ts)) + _EPS))
        return {CYCLE_MODEL.iri: {"reference": ref["name"], "form": "template",
                                  "scale": scale, "lag": lag, "template": tmpl.tolist()}}
    if ref["form"] != "sinusoid":
        raise ValueError(f"unknown reference form: {ref['form']!r}")
    lo, hi = fe * (1.0 - frac), fe * (1.0 + frac)
    best = None
    for f in np.linspace(lo, hi, n):
        M = np.stack([np.ones_like(t), np.cos(2 * _PI * f * t), np.sin(2 * _PI * f * t)], 1)
        coef, *_ = np.linalg.lstsq(M, v, rcond=None)
        e = float(np.sum((v - M @ coef) ** 2))
        if best is None or e < best[0]:
            best = (e, f, coef)
    _, f, coef = best
    return {CYCLE_MODEL.iri: {"reference": ref["name"], "form": ref["form"],
                              "freq": float(f), "DC": float(coef[0]),
                              "a": float(coef[1]), "b": float(coef[2])}}


def _synthesize(**kw):
    m = kw[CYCLE_MODEL.iri]; vw = kw[SIGNAL_WINDOW.iri]
    t = vw["time"]
    if m.get("form") == "template":
        tmpl = np.asarray(m["template"], dtype=float)
        recon = float(m["scale"]) * _shift(tmpl, int(m.get("lag", 0)), len(t))
        return {RECONSTRUCTED_WINDOW.iri: {"values": recon, "time": t}}
    recon = m["DC"] + m["a"] * np.cos(2 * _PI * m["freq"] * t) + m["b"] * np.sin(2 * _PI * m["freq"] * t)
    return {RECONSTRUCTED_WINDOW.iri: {"values": recon, "time": t}}


def _subtract(**kw):
    vw = kw[SIGNAL_WINDOW.iri]; rw = kw[RECONSTRUCTED_WINDOW.iri]
    return {RESIDUAL.iri: {"values": vw["values"] - rw["values"], "time": vw["time"]}}


def _rms(**kw):
    r = kw[RESIDUAL.iri]["values"]
    return {RESIDUAL_ENERGY.iri: float(np.sqrt(np.mean(r ** 2)))}


def _fft(**kw):
    r = kw[RESIDUAL.iri]["values"]; fs = float(kw[FS.iri])
    mag = np.abs(np.fft.rfft(r * np.hanning(len(r))))
    freqs = np.fft.rfftfreq(len(r), 1.0 / fs)
    return {RESIDUAL_SPECTRUM.iri: {"mag": mag, "freqs": freqs}}


def _spectral_flatness(**kw):
    p = kw[RESIDUAL_SPECTRUM.iri]["mag"] ** 2 + _EPS
    flat = float(np.exp(np.mean(np.log(p))) / np.mean(p))   # 1 = flat across FREQ
    return {SPECTRAL_CONCENTRATION.iri: 1.0 - flat}


def _temporal_flatness(**kw):
    r = kw[RESIDUAL.iri]["values"] ** 2
    n = int(kw[N_TIME_BINS.iri])
    e = np.array([float(np.sum(b)) for b in np.array_split(r, n)]) + _EPS
    flat = float(np.exp(np.mean(np.log(e))) / np.mean(e))   # 1 = flat across TIME
    return {TEMPORAL_CONCENTRATION.iri: 1.0 - flat}


def _band_energy(**kw):
    rs = kw[RESIDUAL_SPECTRUM.iri]; f0 = float(kw[F0.iri])
    orders = kw[HARMONIC_ORDERS.iri]; bw = float(kw[HARMONIC_BANDWIDTH.iri])
    fr = rs["freqs"]; pw = rs["mag"] ** 2
    tot = float(np.sum(pw)) + _EPS
    harm = float(sum(np.sum(pw[np.abs(fr - k * f0) <= bw]) for k in orders))
    return {HARMONIC_FRACTION.iri: harm / tot}


def _harmonic_profile(**kw):
    """Per-order harmonic magnitude profile of the residual spectrum — the
    phase-invariant appliance signature (energy at each k*f0), normalized to a
    shape (unit sum). Unlike `band_energy` (one scalar fraction) this keeps the
    full per-order vector, which is what distinguishes a laptop from a kettle."""
    rs = kw[RESIDUAL_SPECTRUM.iri]; f0 = float(kw[F0.iri])
    orders = kw[HARMONIC_ORDERS.iri]; bw = float(kw[HARMONIC_BANDWIDTH.iri])
    fr = rs["freqs"]; pw = rs["mag"] ** 2
    prof = np.array([float(np.sum(pw[np.abs(fr - k * f0) <= bw])) for k in orders], dtype=float)
    return {HARMONIC_AMPLITUDES.iri: (prof / (float(np.sum(prof)) + _EPS)).tolist()}


def _compare_across_windows(**kw):
    cm = kw[CYCLE_MODEL.iri]; hist = list(kw[CYCLE_MODEL_HISTORY.iri])
    per = np.array([1.0 / m["freq"] for m in hist + [cm]])
    if len(per) < 2:
        return {PERIOD_STABILITY.iri: 1.0}
    cv = float(np.std(per) / (np.mean(per) + _EPS))
    return {PERIOD_STABILITY.iri: 1.0 / (1.0 + cv)}


# ── secondary / acquisition bodies ─────────────────────────────────────

def _multiply(**kw):
    a = kw[SIGNAL.iri]["values"]; b = kw[CURRENT_SIGNAL.iri]["values"]
    t = kw[SIGNAL.iri]["time"]
    return {POWER.iri: {"values": a * b, "time": t}}


def _normalize(**kw):
    v = kw[SIGNAL.iri]["values"]; t = kw[SIGNAL.iri]["time"]
    mu = float(np.mean(v)); sd = float(np.std(v)) + _EPS
    return {NORMALIZED_SIGNAL.iri: {"values": (v - mu) / sd, "time": t}}


def _angle(**kw):
    m = kw[CYCLE_MODEL.iri]
    return {PHASE.iri: float(np.arctan2(m["b"], m["a"]))}


def _segment(**kw):
    vs = kw[SIGNAL.iri]; fs = float(kw[FS.iri]); f0 = float(kw[F0.iri])
    v = vs["values"]; t = vs["time"]
    step = int(round(fs / f0))
    segs = [{"values": v[i:i + step], "time": t[i:i + step]}
            for i in range(0, max(1, len(v) - step + 1), step)]
    return {SEGMENTS.iri: segs}


def _count(**kw):
    return {CYCLE_COUNT.iri: int(len(kw[SEGMENTS.iri]))}


def _induce_structure(**kw):
    """Minimal honest structure induction: name the cardinality of the
    example set. Real DAG induction (the acquisition #2 path) is not yet
    designed — declared placeholder so it never reads as complete."""
    segs = kw[SEGMENTS.iri]
    return {INDUCED_STRUCTURE.iri: {"kind": "cycle_series", "n": int(len(segs))}}


# ── appliance-signature bodies (#3) — own their numpy, no residual path ────
# These implement the cross-instance-validated feature set: power factor +
# crest + log-RMS current (magnitude/reactivity) and raw-current harmonic
# ratios (waveform shape), plus a record-level turn-on onset. Every constant
# (orders) arrives as a DataState; eps is a divide guard only.

def _harm_amps(x, f0, fs, orders):
    """Fourier projection amplitude of `x` at each k*f0 (k in orders)."""
    n = len(x); t = np.arange(n) / fs
    out = []
    for k in orders:
        w = 2.0 * _PI * f0 * k
        a = 2.0 / n * float(np.sum(x * np.sin(w * t)))
        b = 2.0 / n * float(np.sum(x * np.cos(w * t)))
        out.append(float(np.hypot(a, b)))
    return out


def _power_features(**kw):
    """[power_factor, crest, log10(irms)] from a raw current+voltage window.
    Magnitude and reactivity — the axes the normalized cycle path throws away."""
    iw = np.asarray(kw[CURRENT_WINDOW.iri]["values"], dtype=float)
    vw = np.asarray(kw[VOLTAGE_WINDOW.iri]["values"], dtype=float)
    irms = float(np.sqrt(np.mean(iw ** 2))) + _EPS
    vrms = float(np.sqrt(np.mean(vw ** 2))) + _EPS
    pf = float(np.mean(vw * iw)) / (vrms * irms)
    crest = float(np.max(np.abs(iw))) / irms
    return {POWER_FEATURES.iri: [pf, crest, float(np.log10(irms))]}


def _current_harmonics(**kw):
    """Raw-current Fourier amplitudes at [fundamental] + orders (waveform shape,
    kept in raw amplitude so a THD ratio can be formed downstream)."""
    iw = np.asarray(kw[CURRENT_WINDOW.iri]["values"], dtype=float)
    fs = float(kw[FS.iri]); f0 = float(kw[F0.iri])
    orders = list(kw[HARMONIC_ORDERS.iri])
    return {RAW_HARMONICS.iri: _harm_amps(iw, f0, fs, [1] + orders)}


def _steady_signature(**kw):
    """Assemble the steady per-window signature: [pf, crest, log_irms, THD,
    ratio_k...] — power features (+) harmonic ratios relative to the fundamental."""
    pf, crest, logi = [float(x) for x in kw[POWER_FEATURES.iri]]
    raw = np.asarray(kw[RAW_HARMONICS.iri], dtype=float)
    fund = float(raw[0]) + _EPS
    harm = raw[1:]
    thd = float(np.linalg.norm(harm)) / fund
    return {STEADY_SIGNATURE.iri: [pf, crest, logi, thd] + (harm / fund).tolist()}


def _onset_features(**kw):
    """Record-level turn-on signature (PLAID captures are off-on): the inrush
    ratio (peak just after switch-on / steady RMS) and the onset time fraction.
    Computed once per record in L4 from the raw current signal."""
    sig = np.asarray(kw[SIGNAL.iri]["values"], dtype=float)
    fs = float(kw[FS.iri]); f0 = float(kw[F0.iri])
    env = np.abs(sig)
    steady = float(np.sqrt(np.mean(env[int(0.8 * len(env)):] ** 2))) + _EPS
    thr = 0.2 * (float(np.max(env)) + _EPS)
    on = int(np.argmax(env > thr)) if np.any(env > thr) else 0
    span = int(5 * fs / f0)
    inrush = float(np.max(env[on:on + span])) if on < len(env) else float(np.max(env))
    return {ONSET_FEATURES.iri: [inrush / steady, on / len(env)]}


def _assemble_signature(**kw):
    """Concatenate the steady signature with the record-level onset features
    into the full appliance signature used for matching."""
    steady = list(kw[STEADY_SIGNATURE.iri])
    onset = list(kw[ONSET_FEATURES.iri])
    return {APPLIANCE_SIGNATURE.iri: steady + onset}


def _signature_distance(**kw):
    """Standardized Euclidean distance between an observed signature and one
    taught reference (per-dim mean/std = the learned L2 `signature_norm`). The
    SCORE is a derivation; the recognized DECISION is the decision family; the
    k-NN vote over the (variable-size) library is L4 iteration."""
    a = np.asarray(kw[APPLIANCE_SIGNATURE.iri], dtype=float)
    b = np.asarray(kw[REFERENCE_SIGNATURE.iri], dtype=float)
    norm = kw[SIGNATURE_NORM.iri]
    sd = np.asarray(norm["std"], dtype=float) + _EPS
    return {MATCH_DISTANCE.iri: float(np.linalg.norm((a - b) / sd))}


def _score_appliance_library(**kw):
    """Standardized-Euclidean distance from ONE query signature to EVERY taught
    exemplar in the library, as a scored collection ``[{score, label}]`` (the
    reduction ``scored_collection`` shape). Replaces the L4 per-exemplar Python
    loop: the variable-size library fan-out is now this one derivation, so
    matching is ``score_appliance_library`` -> ``reduction.argmin`` (two
    capabilities, no Python loop). Same per-dim standardizer as
    ``signature_distance`` (``std`` = the learned ``signature_norm``)."""
    q = np.asarray(kw[APPLIANCE_SIGNATURE.iri], dtype=float)
    library = kw[APPLIANCE_LIBRARY.iri] or []
    sd = np.asarray(kw[SIGNATURE_NORM.iri]["std"], dtype=float) + _EPS
    scored = [
        {"score": float(np.linalg.norm((q - np.asarray(r["vector"], dtype=float)) / sd)),
         "label": r["name"]}
        for r in library
    ]
    return {SCORED_LIBRARY.iri: scored}


def register_derivation(cl, session):
    D = CATEGORY_DERIVATION
    caps = [
        Capacity(name="bind", category=D, inputs=(VOLTAGE.iri, TIME.iri),
                 outputs=(SIGNAL.iri,), implementation=_bind,
                 description="voltage+time -> signal"),
        Capacity(name="bind_current", category=D, inputs=(CURRENT.iri, TIME.iri),
                 outputs=(SIGNAL.iri,), implementation=_bind_current,
                 description="current+time -> signal (current-channel sibling of bind)"),
        Capacity(name="window", category=D,
                 inputs=(SIGNAL.iri, FREQ_ESTIMATE.iri, WINDOW_CYCLES.iri,
                         FS.iri, WINDOW_START.iri),
                 outputs=(SIGNAL_WINDOW.iri,), implementation=_window,
                 description="signal -> one analysis window (position = L4 window_start)"),
        Capacity(name="window_current", category=D,
                 inputs=(CURRENT_SIGNAL.iri, FREQ_ESTIMATE.iri, WINDOW_CYCLES.iri,
                         FS.iri, WINDOW_START.iri),
                 outputs=(CURRENT_WINDOW.iri,), implementation=_window_current,
                 description="current_signal -> one current window (position = window_start)"),
        Capacity(name="window_voltage", category=D,
                 inputs=(VOLTAGE_SIGNAL.iri, FREQ_ESTIMATE.iri, WINDOW_CYCLES.iri,
                         FS.iri, WINDOW_START.iri),
                 outputs=(VOLTAGE_WINDOW.iri,), implementation=_window_voltage,
                 description="voltage_signal -> one voltage window (position = window_start)"),
        Capacity(name="fit_reference", category=D,
                 inputs=(SIGNAL_WINDOW.iri, CYCLE_REFERENCE.iri, FREQ_ESTIMATE.iri,
                         FS.iri, FREQ_SEARCH_FRAC.iri, N_GRID.iri),
                 outputs=(CYCLE_MODEL.iri,), implementation=_fit_reference,
                 description="observation + L2 reference -> fitted model"),
        Capacity(name="synthesize", category=D,
                 inputs=(CYCLE_MODEL.iri, SIGNAL_WINDOW.iri, FS.iri),
                 outputs=(RECONSTRUCTED_WINDOW.iri,), implementation=_synthesize,
                 description="model -> reconstructed signal"),
        Capacity(name="subtract", category=D,
                 inputs=(SIGNAL_WINDOW.iri, RECONSTRUCTED_WINDOW.iri),
                 outputs=(RESIDUAL.iri,), implementation=_subtract,
                 description="observation - reconstruction -> residual"),
        Capacity(name="rms", category=D, inputs=(RESIDUAL.iri,),
                 outputs=(RESIDUAL_ENERGY.iri,), implementation=_rms,
                 description="residual -> residual_energy"),
        Capacity(name="fft", category=D, inputs=(RESIDUAL.iri, FS.iri),
                 outputs=(RESIDUAL_SPECTRUM.iri,), implementation=_fft,
                 description="residual -> windowed spectrum"),
        Capacity(name="spectral_flatness", category=D, inputs=(RESIDUAL_SPECTRUM.iri,),
                 outputs=(SPECTRAL_CONCENTRATION.iri,), implementation=_spectral_flatness,
                 description="spectrum -> spectral_concentration (freq-axis structure)"),
        Capacity(name="temporal_flatness", category=D, inputs=(RESIDUAL.iri, N_TIME_BINS.iri),
                 outputs=(TEMPORAL_CONCENTRATION.iri,), implementation=_temporal_flatness,
                 description="residual -> temporal_concentration (time-axis structure)"),
        Capacity(name="band_energy", category=D,
                 inputs=(RESIDUAL_SPECTRUM.iri, F0.iri, HARMONIC_ORDERS.iri, HARMONIC_BANDWIDTH.iri),
                 outputs=(HARMONIC_FRACTION.iri,), implementation=_band_energy,
                 description="spectrum -> harmonic_fraction at k*f0"),
        Capacity(name="harmonic_profile", category=D,
                 inputs=(RESIDUAL_SPECTRUM.iri, F0.iri, HARMONIC_ORDERS.iri, HARMONIC_BANDWIDTH.iri),
                 outputs=(HARMONIC_AMPLITUDES.iri,), implementation=_harmonic_profile,
                 description="spectrum -> per-order harmonic profile (appliance signature)"),
        Capacity(name="compare_across_windows", category=D,
                 inputs=(CYCLE_MODEL.iri, CYCLE_MODEL_HISTORY.iri),
                 outputs=(PERIOD_STABILITY.iri,), implementation=_compare_across_windows,
                 description="model + history -> period_stability"),
        # secondary / acquisition
        Capacity(name="multiply", category=D,
                 inputs=(SIGNAL.iri, CURRENT_SIGNAL.iri),
                 outputs=(POWER.iri,), implementation=_multiply,
                 description="V*I -> power (power pipeline; needs a current bind, v1)"),
        Capacity(name="normalize", category=D, inputs=(SIGNAL.iri,),
                 outputs=(NORMALIZED_SIGNAL.iri,), implementation=_normalize,
                 description="signal -> zero-mean unit-std"),
        Capacity(name="angle", category=D, inputs=(CYCLE_MODEL.iri,),
                 outputs=(PHASE.iri,), implementation=_angle,
                 description="model -> phase of the fundamental"),
        Capacity(name="segment", category=D,
                 inputs=(SIGNAL.iri, FS.iri, F0.iri),
                 outputs=(SEGMENTS.iri,), implementation=_segment,
                 description="signal -> per-cycle segments"),
        Capacity(name="count", category=D, inputs=(SEGMENTS.iri,),
                 outputs=(CYCLE_COUNT.iri,), implementation=_count,
                 description="segments -> count"),
        Capacity(name="induce_structure", category=D, inputs=(SEGMENTS.iri,),
                 outputs=(INDUCED_STRUCTURE.iri,), implementation=_induce_structure,
                 description="examples -> DAG (acquisition #2; placeholder body)",
                 placeholder=True),
        # appliance recognition (#3) — the signature segment composes 1->3->assemble
        Capacity(name="power_features", category=D,
                 inputs=(CURRENT_WINDOW.iri, VOLTAGE_WINDOW.iri),
                 outputs=(POWER_FEATURES.iri,), implementation=_power_features,
                 description="V,I window -> [power_factor, crest, log_irms]"),
        Capacity(name="current_harmonics", category=D,
                 inputs=(CURRENT_WINDOW.iri, F0.iri, FS.iri, HARMONIC_ORDERS.iri),
                 outputs=(RAW_HARMONICS.iri,), implementation=_current_harmonics,
                 description="current window -> raw Fourier amps at [1]+orders"),
        Capacity(name="steady_signature", category=D,
                 inputs=(POWER_FEATURES.iri, RAW_HARMONICS.iri),
                 outputs=(STEADY_SIGNATURE.iri,), implementation=_steady_signature,
                 description="power + harmonics -> steady appliance signature"),
        Capacity(name="onset_features", category=D,
                 inputs=(SIGNAL.iri, FS.iri, F0.iri),
                 outputs=(ONSET_FEATURES.iri,), implementation=_onset_features,
                 description="current signal -> turn-on [inrush_ratio, onset_frac]"),
        Capacity(name="assemble_signature", category=D,
                 inputs=(STEADY_SIGNATURE.iri, ONSET_FEATURES.iri),
                 outputs=(APPLIANCE_SIGNATURE.iri,), implementation=_assemble_signature,
                 description="steady (+) onset -> full appliance signature"),
        Capacity(name="signature_distance", category=D,
                 inputs=(APPLIANCE_SIGNATURE.iri, REFERENCE_SIGNATURE.iri, SIGNATURE_NORM.iri),
                 outputs=(MATCH_DISTANCE.iri,), implementation=_signature_distance,
                 description="signature + reference + norm -> standardized distance"),
        Capacity(name="score_appliance_library", category=D,
                 inputs=(APPLIANCE_SIGNATURE.iri, APPLIANCE_LIBRARY.iri, SIGNATURE_NORM.iri),
                 outputs=(SCORED_LIBRARY.iri,), implementation=_score_appliance_library,
                 description="query signature + taught library + norm -> scored_collection [{score,label}]"),
    ]
    for c in caps:
        cl.register_capacity(c, session=session, if_exists="upsert")
    return [c.iri for c in caps]
