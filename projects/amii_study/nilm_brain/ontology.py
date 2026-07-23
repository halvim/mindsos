"""NILM DataState ontology — the ``nilm.*`` realm (§7 of the NILM application doc).

Every DataState the brain moves between capacities, declared in a *new*
(non-reserved) realm ``nilm``, so each registration passes
``allow_new_realm=True`` against a Local session (the bongard_demo pattern).

Descriptors are purely structural per the core rule ("semantic richness is
not typed"): we use an opaque tag per name so no two DataStates auto-match.
The *meaning* of each state lives in the value the capacity bodies pass, not
in the type.

Groups (doc §7): **given** (input/const/L2/L5/state) · **floor** (irreducible
atom) · **derived** (composition output) · **verdict** (terminal). The three
terminal outcomes (`cycle` / `held_ambiguity` / `request_reference`) are the
*value* of the single `cycle_verdict` DataState, not separate DataStates — a
capacity has a fixed output signature, so a branching terminal type is not
expressible; L4 routes on `cycle_verdict.state`.
"""

from __future__ import annotations

from typing import Dict, Tuple

from mindsos_capacity import DataState, ShapeDescriptor

#: The brain's own realm (new, non-reserved; needs allow_new_realm=True).
NILM_REALM = "nilm"


def _ds(suffix: str, description: str = "") -> DataState:
    name = f"{NILM_REALM}.{suffix}"
    return DataState(name=name, shape=ShapeDescriptor.opaque(name),
                     description=description)


# ── given — domain constants (input / const) ───────────────────────────
RAW_DATA      = _ds("raw_data", "the submetered record: [N, 2] current+voltage waveform")
FS            = _ds("fs", "sample rate (Hz)")
F0            = _ds("f0", "nominal grid frequency (Hz)")
V_NOM         = _ds("v_nom", "nominal RMS voltage")
CHANNEL_MAP   = _ds("channel_map", "{'current': col, 'voltage': col}")
WINDOW_CYCLES = _ds("window_cycles", "cycles per analysis window")
WINDOW_STEP   = _ds("window_step", "cycles advanced between windows")
HARMONIC_ORDERS    = _ds("harmonic_orders", "harmonic orders k to measure")
HARMONIC_BANDWIDTH = _ds("harmonic_bandwidth", "Hz half-width around each k*f0")
N_TIME_BINS   = _ds("n_time_bins", "bins for temporal_flatness")
PERIOD_TOL    = _ds("period_tol", "refinement-loop convergence tol on |Δperiod|")
# search / loop hyperparameters — promoted to DataStates so nothing is a
# literal in a body (beyond doc §7; the "no hardcoded values" rule made
# explicit): fit_reference's local grid search + the L4 refinement bound.
FREQ_SEARCH_FRAC = _ds("freq_search_frac", "±fraction of freq_estimate fit_reference searches")
N_GRID           = _ds("n_grid", "grid points in fit_reference's frequency search")
MAX_LOOP_ITERS   = _ds("max_loop_iters", "L4 refinement-loop iteration bound")

# ── given — task (L5) ──────────────────────────────────────────────────
REQUIRED_CONFIDENCE = _ds("required_confidence", "L5 task threshold for a confident cycle")

# ── given — references (L2) ────────────────────────────────────────────
CYCLE_REFERENCE  = _ds("cycle_reference", "L2: 'a grid cycle is a sinusoid at ~f0'")
KNOWN_REFERENCES = _ds("known_references", "L2: the growing reference library (§8)")

# ── given — learned (L2) ───────────────────────────────────────────────
STRUCTUREDNESS_THRESHOLDS = _ds("structuredness_thresholds", "L2 per-axis structuredness gates")
CALIBRATE_PARAMS = _ds("calibrate_params", "L2 learned scoring params (fit off a clean-cycle seed)")

# ── given — state (L4 running fold / loop) ─────────────────────────────
CYCLE_MODEL_HISTORY = _ds("cycle_model_history", "prior windows' cycle_models (L4 fold)")
FREQ_ESTIMATE       = _ds("freq_estimate", "current freq estimate (init f0; updated each loop pass)")
DECLARED_STRUCTURE  = _ds("declared_structure", "human-authored DAG (acquisition input)")
WINDOW_START        = _ds("window_start", "L4 iteration offset into the signal (sample index)")

# ── floor — irreducible atoms ──────────────────────────────────────────
VOLTAGE = _ds("voltage", "voltage channel (floor)")
CURRENT = _ds("current", "current channel (floor)")
TIME    = _ds("time", "sample times (floor)")

# ── derived — composition outputs ──────────────────────────────────────
SIGNAL      = _ds("signal", "the signal under analysis (voltage or current) bound to time")
CURRENT_SIGNAL      = _ds("current_signal", "current bound to time")
SIGNAL_WINDOW      = _ds("signal_window", "one analysis window of the signal")
CYCLE_MODEL         = _ds("cycle_model", "fitted reference params {reference, freq, DC, a, b}")
RECONSTRUCTED_WINDOW = _ds("reconstructed_window", "the reference synthesized over the window")
RESIDUAL            = _ds("residual", "signal_window - reconstructed_window")
RESIDUAL_ENERGY     = _ds("residual_energy", "RMS of the residual")
RESIDUAL_SPECTRUM   = _ds("residual_spectrum", "windowed FFT of the residual")
SPECTRAL_CONCENTRATION = _ds("spectral_concentration", "1 - spectral flatness (freq-axis structure)")
TEMPORAL_CONCENTRATION = _ds("temporal_concentration", "1 - temporal flatness (time-axis structure)")
HARMONIC_FRACTION   = _ds("harmonic_fraction", "residual energy fraction at k*f0 bands")
PERIOD_STABILITY    = _ds("period_stability", "cross-window period consistency")
POWER               = _ds("power", "instantaneous power P = V*I")
HARMONIC_AMPLITUDES = _ds("harmonic_amplitudes", "per-order harmonic amplitudes")
SHAPE               = _ds("shape", "a normalized signature shape")
PHASE               = _ds("phase", "phase of the fundamental")

# ── auxiliary derived — outputs of the general/acquisition capacities ──
NORMALIZED_SIGNAL   = _ds("normalized_signal", "normalize() output")
SEGMENTS            = _ds("segments", "segment() output: per-cycle slices", )
CYCLE_COUNT         = _ds("cycle_count", "count() output")
COMPARISON          = _ds("comparison", "compare() output: predicate result")
STRUCTURE_AGREEMENT = _ds("structure_agreement", "compare_structures(): declared vs induced")
INDUCED_STRUCTURE   = _ds("induced_structure", "induce_structure() output DAG")
BOUND_DECLARATION   = _ds("bound_declaration", "bind_declaration(): bound | request")

# ── learned output ─────────────────────────────────────────────────────
CYCLE_CONFIDENCE = _ds("cycle_confidence", "calibrate() output (per-rung: <rung>_confidence)")

# ── appliance recognition (#3): signature + k-NN match ─────────────────
# The appliance path is PARALLEL to the cycle segment: it keeps BOTH channels
# and absolute amplitude (power factor + current magnitude are discriminative),
# which the normalized single-signal cycle path discards. Feature set validated
# cross-instance on real PLAID (union + turn-on onset).
CURRENT_WINDOW      = _ds("current_window", "one analysis window of the current channel")
VOLTAGE_WINDOW      = _ds("voltage_window", "one analysis window of the voltage channel")
RAW_HARMONICS       = _ds("raw_harmonics", "raw-current Fourier amplitudes at [1]+orders")
POWER_FEATURES      = _ds("power_features", "[power_factor, crest, log_irms] from a V,I window")
STEADY_SIGNATURE    = _ds("steady_signature", "steady per-window appliance signature (composed)")
ONSET_FEATURES      = _ds("onset_features", "record-level turn-on [inrush_ratio, onset_frac]")
APPLIANCE_SIGNATURE = _ds("appliance_signature", "full appliance signature (steady (+) onset)")
REFERENCE_SIGNATURE = _ds("reference_signature", "L2 taught appliance signature (one exemplar)")
SIGNATURE_NORM      = _ds("signature_norm", "L2 learned per-dim mean/std for the distance")
MATCH_DISTANCE      = _ds("match_distance", "standardized distance signature<->reference")
MATCH_CUTOFF        = _ds("match_cutoff", "L2 learned nearest-distance cutoff for a valid match")
VOTED_APPLIANCE     = _ds("voted_appliance", "L4 k-NN vote {name, distance, confidence}")
APPLIANCE_VERDICT   = _ds("appliance_verdict", "terminal: recognized[name] | request_reference")

# ── verdict / terminal ─────────────────────────────────────────────────
#: value = {"state": "cycle" | "held_ambiguity" | "request_reference",
#:          "structure": <named structure>, "axis": "spectral"|"temporal"|None}
CYCLE_VERDICT = _ds("cycle_verdict", "terminal verdict; state carried in the value")


#: Closed DataState set, grouped for reading. Registration order is not
#: load-bearing (each is independent).
ONTOLOGY: Tuple[DataState, ...] = (
    # given
    RAW_DATA, FS, F0, V_NOM, CHANNEL_MAP, WINDOW_CYCLES, WINDOW_STEP,
    HARMONIC_ORDERS, HARMONIC_BANDWIDTH, N_TIME_BINS, PERIOD_TOL,
    FREQ_SEARCH_FRAC, N_GRID, MAX_LOOP_ITERS,
    REQUIRED_CONFIDENCE, CYCLE_REFERENCE, KNOWN_REFERENCES,
    STRUCTUREDNESS_THRESHOLDS, CALIBRATE_PARAMS,
    CYCLE_MODEL_HISTORY, FREQ_ESTIMATE, DECLARED_STRUCTURE, WINDOW_START,
    # floor
    VOLTAGE, CURRENT, TIME,
    # derived
    SIGNAL, CURRENT_SIGNAL, SIGNAL_WINDOW, CYCLE_MODEL,
    RECONSTRUCTED_WINDOW, RESIDUAL, RESIDUAL_ENERGY, RESIDUAL_SPECTRUM,
    SPECTRAL_CONCENTRATION, TEMPORAL_CONCENTRATION, HARMONIC_FRACTION,
    PERIOD_STABILITY, POWER, HARMONIC_AMPLITUDES, SHAPE, PHASE,
    NORMALIZED_SIGNAL, SEGMENTS, CYCLE_COUNT, COMPARISON,
    STRUCTURE_AGREEMENT, INDUCED_STRUCTURE, BOUND_DECLARATION,
    # learned output
    CYCLE_CONFIDENCE,
    # appliance recognition (#3)
    CURRENT_WINDOW, VOLTAGE_WINDOW, RAW_HARMONICS, POWER_FEATURES,
    STEADY_SIGNATURE, ONSET_FEATURES, APPLIANCE_SIGNATURE, REFERENCE_SIGNATURE,
    SIGNATURE_NORM, MATCH_DISTANCE, MATCH_CUTOFF, VOTED_APPLIANCE, APPLIANCE_VERDICT,
    # verdict
    CYCLE_VERDICT,
)


def register_ontology(cl, session) -> Dict[str, "object"]:
    """Register every DataState into the session's Local DataState graph.

    Mint-once: ``register_datastate`` has no upsert and hard-raises on a
    duplicate (arc3 C10), so callers use a fresh CapacityLayer per instance.
    Returns ``{iri: Node}``.
    """
    nodes = {}
    for ds in ONTOLOGY:
        nodes[ds.iri] = cl.register_datastate(ds, session=session, allow_new_realm=True)
    return nodes
