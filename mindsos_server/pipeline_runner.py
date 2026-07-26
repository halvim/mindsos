"""Thin standalone pipeline runner (Slice 2).

Runs a :class:`~mindsos_capacity.pipeline.Pipeline` outside the six-phase
lifecycle: no ChainArtifactWriter, no synthetic RequestRun, no MM coupling.
Walks the topo-ordered ``steps``, threading a ``{datastate_iri: value}``
state map (seeded with the caller's inputs), dispatching each capacity via
the live ``dispatcher`` and folding its outputs back into the map.

Serves both ``execute`` (declared skill entry) and ``invoke`` of a whole
pipeline. Pure over ``(dispatcher, pipeline, seed)``; returns
``(state, error)`` — never raises for a step failure.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def run_pipeline(
    dispatcher: Any, pipeline: Any, seed: Dict[str, Any]
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Run ``pipeline`` from ``seed`` inputs; return ``(state, error)``.

    ``seed`` maps start-datastate IRIs to values. Steps are assumed
    topologically ordered (BFSFinder / ConjunctionFinder guarantee this).
    On the first failing step, returns the state so far + an error string.
    """
    state: Dict[str, Any] = dict(seed)
    for step in pipeline.steps:
        inputs = {ds: state[ds] for ds in step.input_datastates if ds in state}
        try:
            result = dispatcher.dispatch(step.capacity_iri, inputs)
        except Exception as e:  # pragma: no cover - defensive
            return state, f"step {step.capacity_iri} raised {type(e).__name__}: {e}"
        if not result.success:
            return state, f"step {step.capacity_iri} failed: {result.error}"
        if getattr(result, "needs_input", None) is not None:
            return state, f"step {step.capacity_iri} needs input: {result.needs_input}"
        for k, v in dict(result.outputs).items():
            state[k] = v
    return state, None


__all__ = ["run_pipeline"]
