"""L4 pipelines — composed by the finder, not hand-listed (arc A6/D8).

The flagship is the `cycle` recognition **segment**: from a fitted
`cycle_model` + its `voltage_window` (produced by the L4 refinement loop) to
`cycle_verdict`. We compose it with the real `ConjunctionFinder` (sound on the
multi-input `calibrate`/`verdict`; BFS is unsound there — arc A7) and execute
it with core's `execute_pipeline`. That the finder *returns* this pipeline AND
it *executes to real values* is the objective acceptance gate (arc F1/F2), not
a narrative.

Why a *segment* and not `raw_data -> cycle_verdict` end-to-end: `window` is a
fan-out over the signal and the 3-4 refinement is repeat-until-converged —
both are L4 iteration, not composition (arc A4/C4). So `find(raw_data ->
cycle_verdict)` is *correctly* NOT FOUND across the fan-out; L4 (control.py)
drives parse/bind/window/fit and hands each converged window to this segment.

`power` and `harmonic_amplitudes` are in the doc registry; their caps are
registered, but `power` needs a current-signal bind (a second `bind` output,
v1) before it composes, so they are not wired here — flagged, not faked.
"""

from __future__ import annotations

from typing import Tuple

from mindsos_capacity import ConjunctionFinder

from .ontology import (
    CYCLE_MODEL, VOLTAGE_WINDOW, FS, F0, HARMONIC_ORDERS, HARMONIC_BANDWIDTH,
    N_TIME_BINS, CYCLE_MODEL_HISTORY, CALIBRATE_PARAMS, STRUCTUREDNESS_THRESHOLDS,
    REQUIRED_CONFIDENCE, KNOWN_REFERENCES, CYCLE_VERDICT,
)


def recognition_segment_starts() -> Tuple[str, ...]:
    """The DataStates the segment consumes but does not produce — supplied by
    L4 (the converged model/window, the running history) and L2/L5 (params,
    thresholds, references, task confidence). All are legitimate entry inputs,
    not orphans (arc C2b)."""
    return (
        CYCLE_MODEL.iri, VOLTAGE_WINDOW.iri,
        FS.iri, F0.iri, HARMONIC_ORDERS.iri, HARMONIC_BANDWIDTH.iri, N_TIME_BINS.iri,
        CYCLE_MODEL_HISTORY.iri, CALIBRATE_PARAMS.iri, STRUCTUREDNESS_THRESHOLDS.iri,
        REQUIRED_CONFIDENCE.iri, KNOWN_REFERENCES.iri,
    )


def compose_recognition_segment(cl, session, *, max_depth: int = 16):
    """Compose the cycle-recognition segment with the sound finder.

    Returns a `Pipeline` (topologically-ordered DAGSteps) or raises
    `PipelineNotFoundError` — an honest "I cannot compose this", never a
    fabricated chain.
    """
    return ConjunctionFinder().find(
        cl, session=session,
        start_datastates=recognition_segment_starts(),
        target_datastate=CYCLE_VERDICT.iri,
        max_depth=max_depth,
    )
