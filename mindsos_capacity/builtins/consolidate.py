"""``capacity:consolidate:mm`` — Local memory write capacity (Phase 34; wired).

Ships the first ``CATEGORY_CONSOLIDATE`` occupant per ADR-0145 §Decision
+ §Implementation. The capacity targets the user's Local
``episodic_memories`` role-graph (ADR-0044 §am-3 rename): a record
bearing ``memory_id`` + ``value`` becomes a ``Memory`` node under
``episodic-memories-v1:memory:<user_id>:<memory_id>``.

NOTE(phase-48-retarget): Phase 39 keeps ``type_="Memory"`` writing
per-task entries through the Memory-composite NodeType. Per
L2_CHAT_DECISIONS D-L2-17 + Chat B D-B47, ``Episode`` is the per-task
entry; ``Memory`` is a clustering composite over Episodes. This is
semantically wrong (interim tech debt for two phases); Phase 48
retargets ``consolidate:mm`` to write ``Episode`` per D-B47.

**Phase 34 ship (ADR-0146 §amendment-1 clauses 4 + 5 closed).** The
capacity body wires through to L1 via
:meth:`KLWriteHandle.write_and_validate` and returns a typed
:class:`WriteResult`.

**Phase 36 addition (ADR-0139 §Capacity-contract).** A semantic-
validator precondition runs via ``handle.validate_node(...)`` before
``write_and_validate``. On ``not result.ok``, the body raises
:class:`SemanticValidationError` carrying the failed
:class:`ValidationResult`; the runtime envelope catches per
ADR-0072. Phase 39 chain for ``episodic_memories`` role is
single-validator (``validate_role_routing``); future per-flow
validators extend the
adapter chain in ``mindsos_knowledge.validators._VALIDATORS_BY_ROLE``
without capacity-body edits.

Failure modes:

1. **Cap-denial** — body does NOT check capabilities for consolidate
   (Local writes are scoped to the session's own user; no cross-user
   risk). The ADR-0080 carve-out applies to scope='local' only via
   :meth:`KnowledgeLayer.writeable` raising ``ValueError`` when
   ``session is None``.
2. **Missing-KL** — ``context.get("kl")`` returns ``None`` →
   :class:`RuntimeError` (CapacityLayer constructed without ``kl=``;
   programmer error per R3 PB-F).
3. **Semantic-validation reject** (Phase 36 NEW) — ``validate_node``
   returns ``ok=False``; body raises
   :class:`SemanticValidationError`. ADR-0146 §amendment-1 clause 1
   remains open — Phase 36 stays raise-not-PTR; L4 consumer drives
   the eventual flip.
4. **L1 schema reject** — ``add_node`` raises ``UnknownTypeError`` /
   ``PropertyShapeError`` etc.; envelope catches as
   ``InvocationResult(success=False, error=...)``.
5. **Session-None for scope='local'** — ``KnowledgeLayer.writeable``
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
    """Body of ``capacity:consolidate:mm`` — Phase 36 wired path.

    Extracts session + KL from context; runs semantic-validator
    precondition via ``handle.validate_node`` (ADR-0139
    §Capacity-contract); mints + writes through
    :meth:`write_and_validate`; returns :class:`WriteResult`. Raises
    :class:`SemanticValidationError` on validator failure.
    """
    from mindsos_knowledge.exceptions import SemanticValidationError
    from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES

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
    handle = kl.writeable(
        session, role=ROLE_EPISODIC_MEMORIES, scope="local", version="v1"
    )
    # NOTE(phase-48-retarget): type_="Memory" writes per-task entry
    # through Memory-composite NodeType — semantically wrong per
    # D-L2-17 (Episode is per-task; Memory is composite). Phase 48
    # retargets to type_="Memory" → type_="Episode" + episode_id
    # plumbing per Chat B D-B47.
    vr = handle.validate_node(value=record["value"], type_="Memory")
    if not vr.ok:
        raise SemanticValidationError(vr)
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
            "Consolidate an MM record into the user's Local "
            "episodic_memories role-graph (Phase 39 rename per ADR-0044 "
            "§am-3). Phase 36 wired — semantic-validator precondition via "
            "handle.validate_node (ADR-0139); returns WriteResult on "
            "success; raises SemanticValidationError on validator failure; "
            "L1 raises propagate per ADR-0146 §am-1 clause 1 (open)."
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
