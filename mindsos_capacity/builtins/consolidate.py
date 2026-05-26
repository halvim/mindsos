"""``capacity:consolidate:mm`` — Local memory write capacity (Phase 33; stub).

Ships the first ``CATEGORY_CONSOLIDATE`` occupant per ADR-0145 §Decision
+ §Implementation (Phase 33). The capacity targets the user's Local
``memories`` role-graph (ADR-0044): an MM ``CompositeInstance`` becomes
a ``ConsolidatedMemory`` record under ``memories-<v>:memory:<user_id>:
<memory_id>``.

**Phase 33 stub-phase status (ADR-0146 §amendment-1 clauses 1-5).** The
capacity registers + invokes through the regular ``CapacityLayer.invoke``
envelope (ADR-0072). The body calls ``kl.writeable(session, role=
ROLE_MEMORIES, scope='local')`` — which:

1. Raises ``ValueError`` when ``session is None`` (Local writes require
   a session for user_id routing; ADR-0080 carve-out doesn't extend
   to Local).
2. Otherwise returns a partially-stubbed :class:`KLWriteHandle` whose
   ``graph()`` raises :class:`WriteHandleNotWiredError`.

Either path surfaces through ``runtime.invoke``'s envelope as
``InvocationResult(success=False, error=<...>)``. Phase 34 (ADR-0146)
wires the working body + the handle's L1 access path.

**Placeholder DataState (R1 PB-B lock).** ``datastate:mm.composite_instance``
is shipped as an opaque-tag DataState. Phase 33 capacity body never
touches the input value (the handle raises before any field access).
Phase 34 / first L4 flow tightens the shape (likely to a record-form
DataState binding ``CompositeInstance`` attributes).

**Outputs (R2 PB-K).** ``outputs=()`` — write capacities are pipeline
terminators. They consume but emit no DataState into the flow graph
(Phase 30's BFS pipeline finder treats them as dead-ends; correct,
since L4 invokes writes directly).
"""

from __future__ import annotations

from typing import Any, List

from ..bootstrap import ensure_datastate_graph
from ..capacity import Capacity
from ..datastate import DataState, ShapeDescriptor
from ..exceptions import CapacityRegistrationError
from ..identifiers import (
    CATEGORY_CONSOLIDATE,
    capacity_iri,
    datastate_iri,
)


# ── DataState IRIs (placeholder per R1 PB-B; tightened Phase 34) ──────

DS_MM_COMPOSITE_INSTANCE = datastate_iri("mm.composite_instance")


def mm_composite_datastates() -> List[DataState]:
    """Return the placeholder DataState(s) used by ``capacity:consolidate:mm``.

    Single-member list at Phase 33; opaque-tag shape per R1 PB-B
    (defer-input-lock pattern — capacity body never touches the value
    because the handle raises first).
    """
    return [
        DataState(
            name="mm.composite_instance",
            shape=ShapeDescriptor.opaque(tag="mm.composite_instance"),
            description=(
                "Placeholder for an MM CompositeInstance bundle. Phase 33 "
                "stub shape; tightened at Phase 34 / first L4 consolidation "
                "flow."
            ),
            provenance_category=CATEGORY_CONSOLIDATE,
        ),
    ]


# ── Capacity body ──────────────────────────────────────────────────────


def _consolidate_mm_impl(**kwargs: Any) -> Any:
    """Body of ``capacity:consolidate:mm`` — Phase 33 stub path.

    Reaches ``kl.writeable(session, role='memories', scope='local')``
    and calls ``handle.graph()``; both surface a contract-typed error
    that ``runtime.invoke`` envelopes. Phase 34 fills the success
    path + returns :class:`WriteResult`.
    """
    # Import here (not at module top) to avoid an import cycle —
    # mindsos_capacity/__init__.py imports from this module via the
    # builtins package, and mindsos_knowledge importing back during
    # module init would loop.
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_knowledge.identifiers import ROLE_MEMORIES

    context = kwargs.get("context") or {}
    session = context.get("session")

    # ``kl`` is constructed fresh per invocation at Phase 33 — there is
    # no Phase 33-shipped KL instance on CapacityLayer / context.
    # Phase 34 wires the real KL routing (likely through the server
    # orchestrator); for Phase 33 the only path is "construct a fresh
    # KL; call writeable(); the handle raises". The fresh-KL path is
    # NOT a forward-anchor — Phase 34 deletes it.
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(session, role=ROLE_MEMORIES, scope="local")
    handle.graph()  # raises WriteHandleNotWiredError at Phase 33.
    # Unreachable at Phase 33; Phase 34 returns WriteResult here.
    raise AssertionError("unreachable at Phase 33")


# ── Capacity factory ──────────────────────────────────────────────────


def build_consolidate_mm() -> Capacity:
    """Build the ``capacity:consolidate:mm`` declaration.

    IRI: ``capacity:consolidate:mm`` (ADR-0145 §Impl line 75 verbatim;
    no ``.write`` or other suffix).

    Inputs: ``(DS_MM_COMPOSITE_INSTANCE,)`` (placeholder).
    Outputs: ``()`` — write-capacity terminator semantic (R2 PB-K).
    """
    return Capacity(
        name="mm",
        category=CATEGORY_CONSOLIDATE,
        inputs=(DS_MM_COMPOSITE_INSTANCE,),
        outputs=(),
        implementation=_consolidate_mm_impl,
        description=(
            "Consolidate an MM CompositeInstance into the user's Local "
            "memories role-graph. Phase 33 stub — handle raises "
            "WriteHandleNotWiredError. Phase 34 (ADR-0146) wires the body."
        ),
        cost_prior=2.0,
        latency_ms_prior=5.0,
    )


# ── Idempotent installer (Phase 31 install_text_capacities pattern) ──

_CONSOLIDATE_MM_IRI = capacity_iri(CATEGORY_CONSOLIDATE, "mm")
_DS_IRIS = (DS_MM_COMPOSITE_INSTANCE,)
_CAP_IRIS = (_CONSOLIDATE_MM_IRI,)
_FAMILY_IRIS = _DS_IRIS + _CAP_IRIS


def install_consolidate_capacities(capacity_layer) -> None:
    """Register every ``consolidate`` family DataState + capacity on ``capacity_layer``.

    Idempotent with partial-state detection per Phase 31's
    ``install_text_capacities`` precedent:

    - All present → no-op (silent return).
    - Some present, some missing → :class:`CapacityRegistrationError`
      ("partial install state detected").
    - None present → install all members (1 DataState + 1 capacity at
      Phase 33).

    Targets Global. No ``session`` argument (admin/bootstrap concern).

    Probe both indexes per ``[[feedback-capacity-layer-index-dispatch]]``:
    DataStates in ``ds_graph.nodes``; Capacities in
    ``CapacityLayer._capacity_index``.

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
        return  # all present — no-op
    if present_total > 0:
        raise CapacityRegistrationError(
            "install_consolidate_capacities: partial install state "
            f"detected — datastates_present={sorted(ds_present)}, "
            f"capacities_present={sorted(cap_present)}, "
            f"missing="
            f"{sorted(set(_FAMILY_IRIS) - ds_present - cap_present)}"
        )
    # None present — install all members (DataStates first per
    # _CapacityBase.validate_for_registration forward-ref rule).
    for ds in mm_composite_datastates():
        capacity_layer.register_datastate(ds)
    capacity_layer.register_capacity(build_consolidate_mm())


__all__ = [
    "DS_MM_COMPOSITE_INSTANCE",
    "mm_composite_datastates",
    "build_consolidate_mm",
    "install_consolidate_capacities",
]
