"""``capacity:consolidate:mm`` — Local memory write capacity (Phase 34; wired).

Ships the first ``CATEGORY_CONSOLIDATE`` occupant per ADR-0145 §Decision
+ §Implementation. The capacity targets the user's Local ``memories``
role-graph (ADR-0044): a record bearing ``memory_id`` + ``value`` becomes
a ``Memory`` node under ``memories-v1:memory:<user_id>:<memory_id>``.

**Phase 34 ship (ADR-0146 §amendment-1 clauses 4 + 5 closed).** The
capacity body now wires through to L1 via
:meth:`KLWriteHandle.write_and_validate` and returns a typed
:class:`WriteResult`. Failure modes:

1. **Cap-denial** — body does NOT check capabilities for consolidate
   (Local writes are scoped to the session's own user; no cross-user
   risk). The ADR-0080 carve-out applies to scope='local' only via
   :meth:`KnowledgeLayer.writeable` raising ``ValueError`` when
   ``session is None``.
2. **Missing-KL** — ``context.get("kl")`` returns ``None`` →
   :class:`RuntimeError` (CapacityLayer constructed without ``kl=``;
   programmer error per R3 PB-F).
3. **L1 schema reject** — ``add_node`` raises ``UnknownTypeError`` /
   ``PropertyShapeError`` etc.; envelope catches as
   ``InvocationResult(success=False, error=...)``.
4. **Session-None for scope='local'** — ``KnowledgeLayer.writeable``
   raises ``ValueError`` (no user_id to route on).

**Input shape (Phase 34 R2 PB-A + R4 §am-impl-2).** Tightened from Phase
33's opaque to record-form ``{"memory_id": "str", "value": "Any"}``.
``opaque_tag`` preserved for backward-compat. L4 consolidation flow
tightens further with consumer-specific fields (e.g., binding to
``CompositeInstance`` attributes).

**Outputs (R2 PB-K).** ``outputs=()`` — write capacities are pipeline
terminators. Phase 30's BFS pipeline finder treats them as dead-ends.
``runtime.invoke``'s Phase 34 bypass branch surfaces the
:class:`WriteResult` via ``InvocationResult.write_outcome``.
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


# ── DataState IRIs (record-shape per Phase 34 R2 PB-A) ────────────────

DS_MM_COMPOSITE_INSTANCE = datastate_iri("mm.composite_instance")


def mm_composite_datastates() -> List[DataState]:
    """Return the DataState(s) used by ``capacity:consolidate:mm``.

    Phase 34 ship: ``ShapeDescriptor.record`` with ``memory_id`` + ``value``
    fields (the minimum surface :meth:`KLWriteHandle.write_and_validate`
    needs). ``opaque_tag`` preserved for Phase 33 sentinel backward-compat
    and downstream consumer disambiguation.
    """
    return [
        DataState(
            name="mm.composite_instance",
            shape=ShapeDescriptor.record(
                {"memory_id": "str", "value": "Any"},
                opaque_tag="mm.composite_instance",
            ),
            description=(
                "Record bearing the minimum keys ``capacity:consolidate:mm`` "
                "extracts: ``memory_id`` (IRI key per ADR-0044) and "
                "``value`` (node value). Phase 34 R2 PB-A tighten; L4 "
                "consolidation flow extends the field set."
            ),
            provenance_category=CATEGORY_CONSOLIDATE,
        ),
    ]


# ── Capacity body ──────────────────────────────────────────────────────


def _consolidate_mm_impl(**kwargs: Any) -> Any:
    """Body of ``capacity:consolidate:mm`` — Phase 34 wired path.

    Extracts session + KL from context; mints + writes through the
    handle's :meth:`write_and_validate`; returns :class:`WriteResult`.
    """
    from mindsos_knowledge.identifiers import ROLE_MEMORIES

    context = kwargs.get("context") or {}
    session = context.get("session")
    kl = context.get("kl")
    if kl is None:
        raise RuntimeError(
            "capacity:consolidate:mm requires CapacityLayer to be "
            "constructed with kl=<KnowledgeLayer> (Phase 34 R0 PB-5). "
            "Programmer error: no KL in context."
        )

    record = kwargs[DS_MM_COMPOSITE_INSTANCE]
    # ``writeable(scope='local')`` raises ValueError when session is None
    # (no user_id to route on; ADR-0080 carve-out doesn't extend to Local).
    handle = kl.writeable(
        session, role=ROLE_MEMORIES, scope="local", version="v1"
    )
    return handle.write_and_validate(
        value=record["value"],
        type_="Memory",
        user_id=session.user_id,
        memory_id=record["memory_id"],
    )


# ── Capacity factory ──────────────────────────────────────────────────


def build_consolidate_mm() -> Capacity:
    """Build the ``capacity:consolidate:mm`` declaration.

    IRI: ``capacity:consolidate:mm`` (ADR-0145 §Impl line 75 verbatim).

    Inputs: ``(DS_MM_COMPOSITE_INSTANCE,)`` (record shape).
    Outputs: ``()`` — write-capacity terminator semantic (R2 PB-K).
    """
    return Capacity(
        name="mm",
        category=CATEGORY_CONSOLIDATE,
        inputs=(DS_MM_COMPOSITE_INSTANCE,),
        outputs=(),
        implementation=_consolidate_mm_impl,
        description=(
            "Consolidate an MM record into the user's Local memories "
            "role-graph. Phase 34 wired — returns WriteResult on success; "
            "L1 raises propagate per ADR-0146 §am-1 clause 1."
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
    ``install_text_capacities`` precedent.

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
