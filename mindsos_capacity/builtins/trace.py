"""``capacity:trace:problem`` — Global problem-trace write capacity (Phase 34; wired).

Ships the first WRITE occupant of ``CATEGORY_TRACE`` per ADR-0145
§Decision + §Implementation. The capacity targets the shared Global
``problem-trace`` role-graph (ADR-0044 inverse — Global, not per-user):
a record bearing ``trace_id`` + ``value`` becomes a
``ProblemTraceEntry`` node under ``problem-trace-v1:entry:<trace_id>``.

(Phase 30 shipped the in-memory :class:`ProblemTraceSink` +
``emit_problem_trace`` writing to a per-:class:`CapacityLayer` in-memory
sink. This capacity is a DIFFERENT mechanism — writes a single record
into KL's Global ``problem-trace`` role-graph — distinct consumer.)

IRI: ``capacity:trace:problem`` (ADR-0145 §Impl line 75 verbatim).

**Phase 34 ship (ADR-0146 §amendment-1 clauses 4 + 5 closed).**

**Phase 36 addition (ADR-0139 §Capacity-contract).** A semantic-
validator precondition runs via ``handle.validate_node(...)`` after
the capability gate, before ``write_and_validate``. On
``not result.ok``, the body raises :class:`SemanticValidationError`
carrying the failed :class:`ValidationResult`; the runtime envelope
catches per ADR-0072. Phase 36 chain for ``problem-trace`` role is
single-validator (``validate_role_routing``).

Failure modes surface through ``runtime.invoke``'s envelope:

1. **Capability denial** — when ``session is not None`` and the session
   lacks ``CAN_WRITE_GLOBAL``, body raises
   :class:`CapabilityDeniedError`. ``session is None`` skips the gate
   per ADR-0080 bootstrap carve-out.
2. **Missing-KL** — ``context.get("kl")`` returns ``None`` →
   :class:`RuntimeError` (programmer error per R3 PB-F).
3. **Semantic-validation reject** (Phase 36 NEW) — ``validate_node``
   returns ``ok=False``; body raises
   :class:`SemanticValidationError`.
4. **L1 schema reject** — ``add_node`` raises; envelope catches.

Cap-denial + semantic-validation reject keep RAISING (not return-PTR)
per Phase 34 R0 PB-6 + ADR-0146 §amendment-1 clause 1 (open). L4
consumer drives the eventual flip in a later phase.

**Outputs (R2 PB-K).** ``outputs=()`` — pipeline terminator.
"""

from __future__ import annotations

from typing import Any, List

from ..bootstrap import ensure_datastate_graph
from ..capacity import Capacity
from ..datastate import DataState, ShapeDescriptor
from ..exceptions import CapacityRegistrationError
from ..identifiers import (
    CATEGORY_TRACE,
    capacity_iri,
    datastate_iri,
)


# ── DataState IRIs (record-shape per Phase 34 R2 PB-A) ────────────────

DS_PROBLEM_TRACE_RECORD = datastate_iri("problem_trace.record")


def problem_trace_datastates() -> List[DataState]:
    """Return the DataState(s) used by ``capacity:trace:problem``.

    Phase 34 ship: ``ShapeDescriptor.record`` with ``trace_id`` + ``value``
    fields. ``opaque_tag`` preserved for backward-compat.
    """
    return [
        DataState(
            name="problem_trace.record",
            shape=ShapeDescriptor.record(
                {"trace_id": "str", "value": "Any"},
                opaque_tag="problem_trace.record",
            ),
            description=(
                "Record bearing the minimum keys ``capacity:trace:problem`` "
                "extracts: ``trace_id`` (IRI key) and ``value`` (node "
                "value, typically a ProblemTraceRecord). Phase 34 R2 PB-A "
                "tighten; L4 trace flow extends the field set."
            ),
            provenance_category=CATEGORY_TRACE,
        ),
    ]


# ── Capacity body ──────────────────────────────────────────────────────


def _trace_problem_impl(**kwargs: Any) -> Any:
    """Body of ``capacity:trace:problem`` — Phase 48 write-half (ADR-0180).

    Obtains its :class:`KLWriteHandle` from the **pre-authorized
    ``context.writeable`` capability** (L4-injected). The global-scope
    capability gate (``CAN_WRITE_GLOBAL``; ``session is None`` is the
    ADR-0080 bootstrap carve-out) now fires **at call-time inside the
    capability**, not in this body — the body holds no session and makes
    no authorization decision (ADR-0170 §am-1). Runs the semantic-validator
    precondition via ``handle.validate_node`` (ADR-0139 §Capacity-contract),
    then writes; raises :class:`SemanticValidationError` on validator
    failure (``CapabilityDeniedError`` propagates from the gate).
    """
    from mindsos_knowledge.exceptions import SemanticValidationError
    from mindsos_knowledge.identifiers import ROLE_PROBLEM_TRACE

    context = kwargs.get("context")
    writeable = getattr(context, "writeable", None)
    if writeable is None:
        raise RuntimeError(
            "capacity:trace:problem requires L4 dispatch: the CapacityContext "
            "must carry a pre-authorized `writeable` capability (ADR-0180). "
            "Write capacities are not invocable via the L3-internal dict path."
        )

    record = kwargs[DS_PROBLEM_TRACE_RECORD]
    handle = writeable(role=ROLE_PROBLEM_TRACE, scope="global", version="v1")
    vr = handle.validate_node(value=record["value"], type_="ProblemTraceEntry")
    if not vr.ok:
        raise SemanticValidationError(vr)
    return handle.write_and_validate(
        value=record["value"],
        type_="ProblemTraceEntry",
        trace_id=record["trace_id"],
    )


# ── Capacity factory ──────────────────────────────────────────────────


def build_trace_problem() -> Capacity:
    """Build the ``capacity:trace:problem`` declaration.

    IRI: ``capacity:trace:problem`` (ADR-0145 §Impl line 75 verbatim).

    Inputs: ``(DS_PROBLEM_TRACE_RECORD,)`` (record shape).
    Outputs: ``()`` — write-capacity terminator semantic (R2 PB-K).
    """
    return Capacity(
        name="problem",
        category=CATEGORY_TRACE,
        inputs=(DS_PROBLEM_TRACE_RECORD,),
        outputs=(),
        implementation=_trace_problem_impl,
        description=(
            "Write a single ProblemTraceEntry into the Global problem-"
            "trace role-graph. Phase 36 wired — semantic-validator "
            "precondition via handle.validate_node (ADR-0139); returns "
            "WriteResult on success; raises CapabilityDeniedError on "
            "cap-denial or SemanticValidationError on validator failure; "
            "L1 raises propagate per ADR-0146 §am-1 clause 1 (open)."
        ),
        cost_prior=1.0,
        latency_ms_prior=2.0,
    )


# ── Idempotent installer ──────────────────────────────────────────────

_TRACE_PROBLEM_IRI = capacity_iri(CATEGORY_TRACE, "problem")
_DS_IRIS = (DS_PROBLEM_TRACE_RECORD,)
_CAP_IRIS = (_TRACE_PROBLEM_IRI,)
_FAMILY_IRIS = _DS_IRIS + _CAP_IRIS


def install_trace_capacities(capacity_layer) -> None:
    """Register every ``trace``-family write DataState + capacity on ``capacity_layer``.

    Idempotent with partial-state detection per Phase 31's
    ``install_text_capacities`` precedent.

    Targets Global. No ``session`` argument (admin/bootstrap concern).

    Raises:
        CapacityRegistrationError: Partial install state detected.
    """
    mg = capacity_layer.global_metagraph()
    cap_index = capacity_layer._capacity_index[mg.metagraph_id]
    ds_graph = ensure_datastate_graph(mg, strict=capacity_layer._strict)

    ds_present = {iri for iri in _DS_IRIS if iri in ds_graph.nodes}
    cap_present = {iri for iri in _CAP_IRIS if iri in cap_index}
    present_total = len(ds_present) + len(cap_present)

    if present_total == len(_FAMILY_IRIS):
        return
    if present_total > 0:
        raise CapacityRegistrationError(
            "install_trace_capacities: partial install state detected — "
            f"datastates_present={sorted(ds_present)}, "
            f"capacities_present={sorted(cap_present)}, "
            f"missing="
            f"{sorted(set(_FAMILY_IRIS) - ds_present - cap_present)}"
        )
    for ds in problem_trace_datastates():
        capacity_layer.register_datastate(ds)
    capacity_layer.register_capacity(build_trace_problem())


__all__ = [
    "DS_PROBLEM_TRACE_RECORD",
    "problem_trace_datastates",
    "build_trace_problem",
    "install_trace_capacities",
]
