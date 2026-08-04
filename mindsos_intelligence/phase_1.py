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

from mindsos_capacity.identifiers import (
    CATEGORY_DECISION,
    CATEGORY_HINT,
    CATEGORY_PROCESS,
    capacity_iri,
)
from mindsos_capacity.needs_input import NeedsInput
from mindsos_capacity.pipeline import find_pipeline
from mindsos_knowledge import ROLE_REQUEST_PATTERNS

from .ingress import InputEnvelope
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
    request_pattern_iri: str
    mapping_confidence: float
    resolved_reference: Any = None


@dataclass
class Phase1Result:
    structured_input: Any
    hint_set_ref: str
    goal: Any
    request_pattern_iri: str
    mapping_confidence: float
    mapping_result_ref: str
    #: The canonical reference the resolve chain produced (``None`` when the
    #: consumer declares no ``resolve_target_datastate`` or the request carried
    #: no reference). Carried out of ``interpret()`` so Phase 2/3 can plan +
    #: execute against the resolved task instead of dropping it (out-of-CR
    #: Step 5 / ADR-0172 §Step-5 amendment; subsumes CORE_CR_PHASE1_RESOLVED_
    #: REFERENCE). Byte-identical when absent — every existing caller reads a
    #: default ``None``.
    resolved_reference: Any = None


def _slot(profile: Optional[Phase1Profile], attr: str, default: str) -> str:
    """The bound IRI for a Phase-1 step, or its v0 default (ADR-0195)."""
    if profile is None:
        return default
    return getattr(profile, attr) or default


def _run_step(dispatcher, capacity_iri: str, env: dict) -> Any:
    """Run one interpretation step, wiring its inputs from ``env`` by the
    selected capacity's declared ``CONSUMES`` and merging its outputs back
    (ADR-0197 §Build-decision-2 — environment-threaded spine).

    Returns the step's sole declared output value. Raises
    :class:`InterpretationError` when a declared input was not produced
    upstream (a mis-wired profile) — a clear failure ahead of the strict
    ``_validate_inputs`` no-unexpected/missing-required contract.
    """
    decl = dispatcher.capacity_layer.resolve_declaration(capacity_iri, session=dispatcher.session)
    missing = [ds for ds in decl.inputs if ds not in env]
    if missing:
        raise InterpretationError(
            f"phase-1 step {capacity_iri!r} needs {missing!r} not produced "
            f"upstream (mis-wired profile; env has {sorted(env)})"
        )
    result = dispatcher.dispatch(capacity_iri, {ds: env[ds] for ds in decl.inputs})
    env.update(result.outputs)
    return result.outputs[decl.outputs[0]]


def _map_target_resolves(dispatcher, request_pattern_iri: str) -> bool:
    """True iff ``request_pattern_iri`` resolves in ``request-patterns`` (Local→
    Global). A consumer authors its pattern Local (ADR-0150 §am-8)."""
    kl = getattr(dispatcher, "kl", None)
    if kl is None:
        # No KL bound → cannot check; treat as resolved (the v0 smoke path
        # never reaches here — the check is gated on a real ``map`` slot).
        return True
    user_id = getattr(getattr(dispatcher, "session", None), "user_id", None)
    if user_id is not None and kl.has_local(user_id):
        node = kl.local_view(user_id).get_node(ROLE_REQUEST_PATTERNS, request_pattern_iri)
        if node is not None:
            return True
    return kl.global_view().get_node(ROLE_REQUEST_PATTERNS, request_pattern_iri) is not None


def _resolve_reference(
    dispatcher, profile: Phase1Profile, hints: Mapping[str, Any], request_id: str
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
    # CORE-C3R1: the finder returns a verdict; no route is a don't-know about
    # the world, not a raise. Interpretation still treats it as a dead-end —
    # faithful conversion, no new failure mode — but now names the reason.
    verdict = find_pipeline(
        dispatcher.capacity_layer,
        session=dispatcher.session,
        start_datastate=start,
        target_datastate=target,
    )
    if not verdict.found:
        raise InterpretationError(
            f"no resolve pipeline from {start!r} to {target!r} "
            f"[{verdict.reason}]: {verdict.detail}"
        )
    pipeline = verdict.pipeline
    exec_result = execute_pipeline(
        dispatcher, pipeline, {start: reference}, request_id=request_id
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
    request_input,
    *,
    profile: Optional[Phase1Profile] = None,
    request_id: str = "interpret",
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

    A *stamped* modality (``InputEnvelope.modality``) is authoritative
    (ADR-0197 am-1): it must route via the dispatcher's
    ``{modality -> Phase1Profile}`` table or ``interpret`` raises
    :class:`InterpretationError` -- Mode A when the modality has no registered
    profile (an unroutable input; it does *not* fall back to the
    construction-bound profile or v0), Mode B when the selected profile's
    ``process`` declares an ingress != the modality. ``run_lifecycle`` maps the
    raise to a terminal ``dont_know`` (ADR-0196). The ``modality=None`` legacy
    path is unaffected.
    """
    # ADR-0197 (+ am-1) — unwrap the ingress envelope and select the profile
    # by modality. A raw value / modality=None is the legacy path. A stamped
    # modality is AUTHORITATIVE: it must route via the {modality->Phase1Profile}
    # table or interpret raises (am-1); it does NOT fall back to the
    # construction-bound profile or v0. An explicit ``profile=`` arg still wins.
    # ``source`` is provenance only — never selects.
    if isinstance(request_input, InputEnvelope):
        value = request_input.value
        modality = request_input.modality
    else:
        value = request_input
        modality = None

    if profile is None and modality is not None:
        table = getattr(dispatcher, "modality_profiles", None) or {}
        if modality not in table:
            raise InterpretationError(
                f"unroutable modality {modality!r}: no profile registered "
                f"(ADR-0197 am-1). Register a modality profile, or omit the "
                f"modality to use the construction-bound / v0 path."
            )
        profile = table[modality]
    if profile is None:
        profile = getattr(dispatcher, "phase1_profile", None)

    # ADR-0197 §Build-decision-2 — environment-threaded spine. Seed with
    # the selected ``process`` cap's declared ingress DataState so a
    # modality-typed process (e.g. ``text.raw``) wires without a fixed
    # ``DS_RAW_INPUT`` assumption. All-v0 is byte-identical: the v0 caps
    # declare exactly DS_RAW_INPUT -> DS_STRUCTURED_INPUT -> ... .
    process_iri = _slot(profile, "process", PROCESS_IRI)
    ingress_ds = dispatcher.capacity_layer.resolve_declaration(process_iri, session=dispatcher.session).inputs[0]
    if modality is not None and ingress_ds != modality:
        raise InterpretationError(
            f"modality {modality!r} routes to process {process_iri!r} whose "
            f"declared ingress is {ingress_ds!r}; ADR-0197 §2 requires them "
            f"equal (mis-registered modality profile?)."
        )
    env: dict = {ingress_ds: value}

    structured = _run_step(dispatcher, process_iri, env)
    hints = _run_step(dispatcher, _slot(profile, "hint", HINT_IRI), env)
    goal = _run_step(dispatcher, _slot(profile, "derive_goal", DERIVE_GOAL_IRI), env)
    mapping = _run_step(dispatcher, _slot(profile, "map", MAP_IRI), env)

    request_pattern_iri = mapping["request_pattern_iri"]
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
        if not _map_target_resolves(dispatcher, request_pattern_iri):
            raise InterpretationError(
                f"map target {request_pattern_iri!r} does not resolve in "
                f"{ROLE_REQUEST_PATTERNS!r}"
            )
        resolved_reference = _resolve_reference(dispatcher, profile, hints, request_id)
        # ADR-0196 — the resolve body asked the user; surface it directly.
        if isinstance(resolved_reference, NeedsInput):
            return resolved_reference

    return InterpretationResult(
        structured_input=structured,
        hints=hints,
        goal=goal,
        request_pattern_iri=request_pattern_iri,
        mapping_confidence=mapping_confidence,
        resolved_reference=resolved_reference,
    )


def run(dispatcher, writer, request_input) -> "Phase1Result | NeedsInput":
    """Full-lifecycle Phase 1: interpret, then emit the HintSet +
    MappingResult chain artifacts and return :class:`Phase1Result`.

    When interpretation surfaces a :class:`NeedsInput` verdict (ADR-0196),
    return it un-emitted (no chain artifacts) so ``run_lifecycle`` can
    short-circuit into a non-terminal ``pending_confirmation`` outcome
    without consolidating."""
    r = interpret(dispatcher, request_input)
    if isinstance(r, NeedsInput):
        return r
    hint_set = writer.emit_hint_set(r.hints)
    mr = writer.emit_mapping_result(
        hint_set.iri, r.request_pattern_iri, r.mapping_confidence
    )
    return Phase1Result(
        structured_input=r.structured_input,
        hint_set_ref=hint_set.iri,
        goal=r.goal,
        request_pattern_iri=r.request_pattern_iri,
        mapping_confidence=r.mapping_confidence,
        mapping_result_ref=mr.iri,
        resolved_reference=r.resolved_reference,
    )


__all__ = [
    "run",
    "interpret",
    "Phase1Result",
    "InterpretationResult",
    "InterpretationError",
    "Phase1Profile",
]
