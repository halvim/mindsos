"""``capacity:trace:problem`` — Global problem-trace write capacity (Phase 33; stub).

Ships the first occupant of the existing ``CATEGORY_TRACE`` category to
have a *write* role (Phase 30 shipped the in-memory
:class:`ProblemTraceSink` + ``emit_problem_trace`` writing to a
per-:class:`CapacityLayer` in-memory sink; Phase 33 introduces the
capacity that writes a single :class:`ProblemTraceRecord` into KL's
Global ``problem-trace`` role-graph — distinct mechanism, distinct
consumer).

IRI: ``capacity:trace:problem`` (ADR-0145 §Impl line 75 verbatim).

**Phase 33 stub-phase status (ADR-0146 §amendment-1 clauses 1-5).** Two
failure modes surface through ``runtime.invoke``'s envelope at Phase 33:

1. **Capability denial** — when ``session is not None`` and the session
   lacks ``CAN_WRITE_GLOBAL``, body raises
   :class:`CapabilityDeniedError`. ``session is None`` skips the gate
   per ADR-0080 bootstrap carve-out.
2. **Handle not wired** — body reaches
   ``kl.writeable(session, role=ROLE_PROBLEM_TRACE, scope='global')``
   and calls ``handle.graph()`` which raises
   :class:`WriteHandleNotWiredError`.

Phase 34 (ADR-0146) wires the working body + the handle's L1 access
path; Phase 34+ may shift the capability-denial path to return
``ProblemTraceRecord(kind="CAPABILITY_DENIED")`` per ADR-0146 §Decision.

**Outputs (R2 PB-K).** ``outputs=()`` — pipeline terminator.
"""

from __future__ import annotations

from typing import Any, List

from ..bootstrap import ensure_datastate_graph
from ..capabilities import CAN_WRITE_GLOBAL
from ..capacity import Capacity
from ..datastate import DataState, ShapeDescriptor
from ..exceptions import CapabilityDeniedError, CapacityRegistrationError
from ..identifiers import (
    CATEGORY_TRACE,
    capacity_iri,
    datastate_iri,
)


# ── DataState IRIs (placeholder per R1 PB-B; tightened Phase 34) ──────

DS_PROBLEM_TRACE_RECORD = datastate_iri("problem_trace.record")


def problem_trace_datastates() -> List[DataState]:
    """Return the placeholder DataState(s) used by ``capacity:trace:problem``.

    Single-member list at Phase 33; opaque-tag shape. Phase 34 / first
    L4 flow tightens to a record-form DataState binding
    :class:`ProblemTraceRecord` fields.
    """
    return [
        DataState(
            name="problem_trace.record",
            shape=ShapeDescriptor.opaque(tag="problem_trace.record"),
            description=(
                "Placeholder for a single ProblemTraceRecord destined for "
                "the Global problem-trace role-graph. Phase 33 stub shape; "
                "tightened at Phase 34 / first L4 trace flow."
            ),
            provenance_category=CATEGORY_TRACE,
        ),
    ]


# ── Capacity body ──────────────────────────────────────────────────────


def _trace_problem_impl(**kwargs: Any) -> Any:
    """Body of ``capacity:trace:problem`` — Phase 33 stub path.

    Cap-denied (session-bearer lacks ``CAN_WRITE_GLOBAL``) → raises
    :class:`CapabilityDeniedError`. Otherwise reaches the handle's
    ``graph()`` which raises :class:`WriteHandleNotWiredError`. Both
    surface through ``runtime.invoke``'s envelope as ``success=False``.
    """
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_knowledge.identifiers import ROLE_PROBLEM_TRACE

    context = kwargs.get("context") or {}
    session = context.get("session")

    # ADR-0080 carve-out: session is None is the bootstrap path; no
    # cap gate. Production callers carry a session; admin lacks
    # CAN_WRITE_GLOBAL → cap-denied.
    if session is not None and not session.has(CAN_WRITE_GLOBAL):
        raise CapabilityDeniedError(
            f"capacity:trace:problem requires CAN_WRITE_GLOBAL; session "
            f"{session.session_id!r} (user={session.user_id!r}) lacks it."
        )

    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(session, role=ROLE_PROBLEM_TRACE, scope="global")
    handle.graph()  # raises WriteHandleNotWiredError at Phase 33.
    raise AssertionError("unreachable at Phase 33")


# ── Capacity factory ──────────────────────────────────────────────────


def build_trace_problem() -> Capacity:
    """Build the ``capacity:trace:problem`` declaration.

    IRI: ``capacity:trace:problem`` (ADR-0145 §Impl line 75 verbatim).

    Inputs: ``(DS_PROBLEM_TRACE_RECORD,)`` (placeholder).
    Outputs: ``()`` — write-capacity terminator semantic (R2 PB-K).
    """
    return Capacity(
        name="problem",
        category=CATEGORY_TRACE,
        inputs=(DS_PROBLEM_TRACE_RECORD,),
        outputs=(),
        implementation=_trace_problem_impl,
        description=(
            "Write a single ProblemTraceRecord into the Global problem-"
            "trace role-graph. Phase 33 stub — handle raises "
            "WriteHandleNotWiredError. Phase 34 (ADR-0146) wires the body."
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
