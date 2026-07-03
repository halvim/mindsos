"""LifecyclePhase 1 — task interpretation (ADR-0172 + ADR-0195 seam).

The interpretation flow — ``process -> extract_hints -> derive_goal ->
map_to_task_pattern`` (+ optional reference ``resolve``) — is factored into
a **standalone** :func:`interpret` decoupled from the orchestrator's
``run_lifecycle`` (ADR-0195 §Decision.2). Two callers:

* :func:`run` — the full-lifecycle wrapper: calls :func:`interpret`, then
  emits the HintSet + MappingResult chain artifacts into intelligence-MM
  and returns the :class:`Phase1Result` the orchestrator's plan
  construction consumes. Byte-for-byte the Phase-47 behavior when the
  dispatcher carries no ``Phase1Profile`` (all-v0).
* An interpretation-only consumer (e.g. arc-solver) calls :func:`interpret`
  directly with its own ``Phase1Profile`` and reads the
  :class:`InterpretationResult` — no writer, no MM, no consolidation.

Each step dispatches ``profile.<slot> or <v0 default IRI>`` (ADR-0195
§Decision.1). Reference ``resolve`` is not a fixed slot: when the hint body
reports an indirect ``reference_kind`` and the profile names a
``resolve_target_datastate``, the shipped bipartite ``find_pipeline``
(ADR-0156) composes the resolve chain by DataState type and the shipped
``pipeline_execution`` executor runs it (ADR-0195 §Decision.3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from mindsos_capacity.builtins.phase1_v0 import (
    DS_GOAL,
    DS_HINT_SET,
    DS_MAPPING,
    DS_RAW_INPUT,
    DS_STRUCTURED_INPUT,
)
from mindsos_capacity.exceptions import PipelineNotFoundError
from mindsos_capacity.identifiers import (
    CATEGORY_DECISION,
    CATEGORY_HINT,
    CATEGORY_PROCESS,
    capacity_iri,
)
from mindsos_capacity.needs_input import NeedsInput
from mindsos_capacity.pipeline import find_pipeline
from mindsos_knowledge import ROLE_TASK_PATTERNS

from .phase1_profile import Phase1Profile
from .pipeline_execution import execute_pipeline

PROCESS_IRI = capacity_iri(CATEGORY_PROCESS, "identity")
HINT_IRI = capacity_iri(CATEGORY_HINT, "global")
DERIVE_GOAL_IRI = capacity_iri(CATEGORY_DECISION, "derive_goal")
MAP_IRI = capacity_iri(CATEGORY_DECISION, "map_to_task_pattern")

#: Hint-dict keys the seam reads for reference resolution (ADR-0195
#: §Decision.4). Both are consumer-populated (opaque-dict hints): a
#: ``reference_kind`` DataState IRI naming the reference's *type* (the
#: find_pipeline start), and the raw ``reference`` value.
HINT_REFERENCE_KIND = "reference_kind"
HINT_REFERENCE = "reference"


class InterpretationError(RuntimeError):
    """A real-consumer interpretation invariant failed (ADR-0195):
    an unresolvable ``map`` target, a below-threshold mapping confidence,
    or a reference-resolve pipeline that could not run. (The graceful
    ``dont_know`` / ``needs_input`` verdicts are ADR-0196 / S2.)"""


@dataclass
class InterpretationResult:
    """Outcome of :func:`interpret` (ADR-0195 §Decision.2).

    ``resolved_reference`` is the canonical reference produced by the
    resolve chain (``None`` when the profile declares no
    ``resolve_target_datastate`` or the request carried no reference).
    """

    structured_input: Any
    hints: Mapping[str, Any]
    goal: Any
    task_pattern_iri: str
    mapping_confidence: float
    resolved_reference: Any = None


@dataclass
class Phase1Result:
    structured_input: Any
    hint_set_ref: str
    goal: Any
    task_pattern_iri: str
    mapping_confidence: float
    mapping_result_ref: str


def _slot(profile: Optional[Phase1Profile], attr: str, default: str) -> str:
    """The bound IRI for a Phase-1 step, or its v0 default (ADR-0195)."""
    if profile is None:
        return default
    return getattr(profile, attr) or default


def _map_target_resolves(dispatcher, task_pattern_iri: str) -> bool:
    """True iff ``task_pattern_iri`` resolves in ``task-patterns`` (Local→
    Global). A consumer authors its pattern Local (ADR-0150 §am-8)."""
    kl = getattr(dispatcher, "kl", None)
    if kl is None:
        # No KL bound → cannot check; treat as resolved (the v0 smoke path
        # never reaches here — the check is gated on a real ``map`` slot).
        return True
    user_id = getattr(getattr(dispatcher, "session", None), "user_id", None)
    if user_id is not None and kl.has_local(user_id):
        node = kl.local_view(user_id).get_node(ROLE_TASK_PATTERNS, task_pattern_iri)
        if node is not None:
            return True
    return kl.global_view().get_node(ROLE_TASK_PATTERNS, task_pattern_iri) is not None


def _resolve_reference(
    dispatcher, profile: Phase1Profile, hints: Mapping[str, Any], task_id: str
) -> Any:
    """Compose + run the reference-resolve chain by DataState type
    (ADR-0195 §Decision.3). Returns the canonical reference, ``None`` (no
    reference to resolve), or a :class:`NeedsInput` verdict bubbled from the
    resolve body (ADR-0196).
    """
    target = profile.resolve_target_datastate
    if target is None:
        return None
    start = hints.get(HINT_REFERENCE_KIND)
    if start is None:
        return None
    reference = hints.get(HINT_REFERENCE)
    if start == target:
        # Reference is already canonical — 0-step pipeline / pass-through.
        return reference
    try:
        pipeline = find_pipeline(
            dispatcher.capacity_layer,
            session=dispatcher.session,
            start_datastate=start,
            target_datastate=target,
        )
    except PipelineNotFoundError as exc:  # no route → interpretation dead-end
        raise InterpretationError(
            f"no resolve pipeline from {start!r} to {target!r}"
        ) from exc
    exec_result = execute_pipeline(
        dispatcher, pipeline, {start: reference}, task_id=task_id
    )
    if exec_result.needs_input is not None:
        return exec_result.needs_input
    if not exec_result.success:
        raise InterpretationError(
            f"resolve pipeline failed at {exec_result.failed_step!r}"
        )
    return exec_result.outputs.get(target)


def interpret(
    dispatcher,
    task_input,
    *,
    profile: Optional[Phase1Profile] = None,
    task_id: str = "interpret",
    mapping_confidence_threshold: float = 0.0,
) -> "InterpretationResult | NeedsInput":
    """Run the standalone interpretation flow (ADR-0195 / ADR-0196).

    Returns an :class:`InterpretationResult`, or a :class:`NeedsInput`
    verdict (ADR-0196) when the resolve step's body asks the user — the
    caller (e.g. arc) drives the two-turn clarification itself.

    ``profile`` defaults to the dispatcher's construction-bound
    ``phase1_profile`` (``None`` → all-v0). The map-target-resolves check
    and the reference-resolve step fire only when a *real* consumer supplies
    the corresponding slots (``map`` / ``resolve_target_datastate``), so the
    all-v0 path is unchanged.
    """
    if profile is None:
        profile = getattr(dispatcher, "phase1_profile", None)

    structured = dispatcher.dispatch(
        _slot(profile, "process", PROCESS_IRI), {DS_RAW_INPUT: task_input}
    ).outputs[DS_STRUCTURED_INPUT]
    hints = dispatcher.dispatch(
        _slot(profile, "hint", HINT_IRI), {DS_STRUCTURED_INPUT: structured}
    ).outputs[DS_HINT_SET]
    goal = dispatcher.dispatch(
        _slot(profile, "derive_goal", DERIVE_GOAL_IRI),
        {DS_STRUCTURED_INPUT: structured, DS_HINT_SET: hints},
    ).outputs[DS_GOAL]
    mapping = dispatcher.dispatch(
        _slot(profile, "map", MAP_IRI),
        {DS_STRUCTURED_INPUT: structured, DS_HINT_SET: hints, DS_GOAL: goal},
    ).outputs[DS_MAPPING]

    task_pattern_iri = mapping["task_pattern_iri"]
    mapping_confidence = mapping["mapping_confidence"]

    resolved_reference = None
    # Real-consumer validation (gated on a supplied ``map`` slot so the v0
    # trivial pattern — which is not KL-registered — never trips it).
    if profile is not None and profile.map is not None:
        if mapping_confidence < mapping_confidence_threshold:
            raise InterpretationError(
                f"mapping confidence {mapping_confidence} < threshold "
                f"{mapping_confidence_threshold}"
            )
        if not _map_target_resolves(dispatcher, task_pattern_iri):
            raise InterpretationError(
                f"map target {task_pattern_iri!r} does not resolve in "
                f"{ROLE_TASK_PATTERNS!r}"
            )
        resolved_reference = _resolve_reference(dispatcher, profile, hints, task_id)
        # ADR-0196 — the resolve body asked the user; surface it directly.
        if isinstance(resolved_reference, NeedsInput):
            return resolved_reference

    return InterpretationResult(
        structured_input=structured,
        hints=hints,
        goal=goal,
        task_pattern_iri=task_pattern_iri,
        mapping_confidence=mapping_confidence,
        resolved_reference=resolved_reference,
    )


def run(dispatcher, writer, task_input) -> "Phase1Result | NeedsInput":
    """Full-lifecycle Phase 1: interpret, then emit the HintSet +
    MappingResult chain artifacts and return :class:`Phase1Result`.

    When interpretation surfaces a :class:`NeedsInput` verdict (ADR-0196),
    return it un-emitted (no chain artifacts) so ``run_lifecycle`` can
    short-circuit into a non-terminal ``pending_confirmation`` outcome
    without consolidating."""
    r = interpret(dispatcher, task_input)
    if isinstance(r, NeedsInput):
        return r
    hint_set = writer.emit_hint_set(r.hints)
    mr = writer.emit_mapping_result(
        hint_set.iri, r.task_pattern_iri, r.mapping_confidence
    )
    return Phase1Result(
        structured_input=r.structured_input,
        hint_set_ref=hint_set.iri,
        goal=r.goal,
        task_pattern_iri=r.task_pattern_iri,
        mapping_confidence=r.mapping_confidence,
        mapping_result_ref=mr.iri,
    )


__all__ = [
    "run",
    "interpret",
    "Phase1Result",
    "InterpretationResult",
    "InterpretationError",
    "Phase1Profile",
]
