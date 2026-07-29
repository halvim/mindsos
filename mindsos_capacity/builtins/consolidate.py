"""``capacity:consolidate:mm`` — Local episode write capacity (Phase 34; retargeted Phase 43).

Ships the first ``CATEGORY_CONSOLIDATE`` occupant per ADR-0145 §Decision
+ §Implementation. The capacity targets the user's Local
``episodic_memories`` role-graph (ADR-0044 §am-3 rename): a record
bearing ``episode_id`` + ``value`` becomes an ``Episode`` node under
``episodic-memories-v1:episode:<user_id>:<episode_id>``.

**Phase 43 PR2 commit 3 retarget per R0 PB-43-9.** Phase 39 shipped this
capacity writing ``type_="Memory"`` + ``memory_id``-keyed IRIs as
interim tech debt; D-L2-17 + Chat B D-B47 lock Episode as the per-task
entry NodeType (Memory is a clustering composite over Episodes,
materialized by a separate consolidation flow). Phase 43 retargets to
``type_="Episode"`` + ``episode_id`` per the canonical Chat B D-B47
shape, closing the two-phase tech-debt window. The ``Memory`` NodeType
remains in the schema for the future composite-consolidation flow
(Phase 48+); ``consolidate:mm`` now writes Episodes only.

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

**Input shape (Phase 34 R2 PB-A + R4 §am-impl-2; Phase 43 retarget).**
Tightened from Phase 33's opaque to record-form
``{"episode_id": "str", "value": "Any"}`` (Phase 43 rename of the
Phase 34 ``memory_id`` key per R0 PB-43-9 + Chat B D-B47).
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

    Phase 34 ship: ``ShapeDescriptor.record`` with ``memory_id`` +
    ``value`` fields (the minimum surface
    :meth:`KLWriteHandle.write_and_validate` needs). Phase 43 retarget
    renames ``memory_id`` to ``episode_id`` per R0 PB-43-9 + Chat B
    D-B47. ``opaque_tag`` preserved for Phase 33 sentinel
    backward-compat and downstream consumer disambiguation.
    """
    return [
        DataState(
            name="mm.composite_instance",
            shape=ShapeDescriptor.record(
                {"episode_id": "str", "value": "Any"},
                opaque_tag="mm.composite_instance",
            ),
            description=(
                "Record bearing the minimum keys ``capacity:consolidate:mm`` "
                "extracts: ``episode_id`` (IRI key per ADR-0044 §am-3 +"
                " Chat B D-B47) and ``value`` (node value). Phase 34 R2"
                " PB-A tighten; Phase 43 retarget (R0 PB-43-9);"
                " L4 consolidation flow extends the field set."
            ),
            provenance_category=CATEGORY_CONSOLIDATE,
        ),
    ]


# ── Capacity body ──────────────────────────────────────────────────────


def _encode_props(props: Any) -> dict:
    """Coerce an Episode field bag into an L1-property-safe dict.

    L1 node properties are **primitives only** (``validate_user_properties``:
    str / int / float / bool / None / primitive-list). Dream PRE-0 Slice 1b (D1)
    stores the Episode's fields as real properties, so any non-primitive field
    (today only ``crash_marker``, a dict) is JSON-encoded to a string; the Dream
    reader decodes it. ``None`` values pass through (allowed).
    """
    import json

    if not isinstance(props, dict):
        return {}
    out: dict = {}
    for k, v in props.items():
        out[k] = json.dumps(v) if isinstance(v, (dict, tuple)) else v
    return out


def _consolidate_mm_impl(**kwargs: Any) -> Any:
    """Body of ``capacity:consolidate:mm`` — the Episode lifecycle write surface.

    Obtains its :class:`KLWriteHandle` from the **pre-authorized
    ``context.writeable`` capability** (L4-injected; scope-aware gate at
    call-time) rather than ``kl.writeable(session, …)`` — the body holds
    no session and makes no authorization decision (ADR-0170 §am-1).

    **Dream PRE-0 Slice 1b (D1 + open/close lifecycle).** The record's ``value``
    now carries ``{"op": ..., "props": {...}}`` where ``props`` are the Episode's
    fields written as real L1 node **properties** (not an opaque ``value`` blob):

    * ``op == "open"`` — CREATE the Episode node ``state=open`` with the
      known-at-start fields (idempotent: no-op if the node already exists).
    * ``op == "suspend"`` — flip ``state=suspended`` on the existing node
      (needs-input; metadata-only edit, resumes later).
    * ``op == "close"`` (default) — UPSERT: update the open node's ``state`` +
      the now-known content fields via :meth:`update_and_validate`
      (``via_lazy_inline=True``, the retire-time inline), or create it whole if
      no open node exists (crash-recovery write / open was unwired). Materialises
      the Memory composite once ``request_pattern_iri`` is present.

    Returns the :class:`WriteResult` (create or update). Raises
    :class:`SemanticValidationError` on validator failure.
    """
    from mindsos_knowledge.exceptions import SemanticValidationError
    from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
    from mindsos_knowledge.schemas.episodic_memories import (
        EPISODE_CONTENT_FIELDS,
        EPISODE_STATE_CLOSED,
        EPISODE_STATE_SUSPENDED,
    )

    context = kwargs.get("context")
    writeable = getattr(context, "writeable", None)
    if writeable is None:
        raise RuntimeError(
            "capacity:consolidate:mm requires L4 dispatch: the CapacityContext "
            "must carry a pre-authorized `writeable` capability (ADR-0180). "
            "Write capacities are not invocable via the L3-internal dict path."
        )

    record = kwargs[DS_MM_COMPOSITE_INSTANCE]
    handle = writeable(role=ROLE_EPISODIC_MEMORIES, scope="local", version="v1")
    payload = record["value"]
    episode_id = record["episode_id"]

    # ── LEGACY value-blob write (pre-Slice-1b callers) ────────────────
    # A payload WITHOUT an ``op`` key is the historical opaque ``value`` blob:
    # write it byte-identically as the node value (no properties). Preserves
    # every pre-Slice-1b caller/test; the streaming lifecycle (below) always
    # tags ``op``.
    if not (isinstance(payload, dict) and "op" in payload):
        vr = handle.validate_node(value=payload, type_="Episode")
        if not vr.ok:
            raise SemanticValidationError(vr)
        episode_result = handle.write_and_validate(
            value=payload,
            type_="Episode",
            user_id=context.user_id,
            episode_id=episode_id,
        )
        rpi = payload.get("request_pattern_iri") if isinstance(payload, dict) else None
        if rpi:
            _materialise_memory(handle, context.user_id, rpi, episode_result.iri)
        return episode_result

    # ── Streaming lifecycle (Dream PRE-0 Slice 1b): fields as properties ──
    op = payload["op"]
    props = _encode_props(payload.get("props", {}))
    if op == "close" and "state" not in props:
        props["state"] = EPISODE_STATE_CLOSED
    epi_iri = handle.mint_iri(
        "Episode", user_id=context.user_id, episode_id=episode_id
    )
    exists = epi_iri in handle.graph().nodes

    # ── suspend: metadata-only flip on the existing node ──────────────
    if op == "suspend":
        if not exists:
            return None
        return handle.update_and_validate(
            iri=epi_iri,
            field_updates={"state": props.get("state", EPISODE_STATE_SUSPENDED)},
            content_fields=EPISODE_CONTENT_FIELDS,
        )

    # ── open: create the streaming Episode (idempotent) ───────────────
    if op == "open":
        if exists:
            return None
        vr = handle.validate_node(value=episode_id, type_="Episode")
        if not vr.ok:
            raise SemanticValidationError(vr)
        return handle.write_and_validate(
            value=episode_id,
            type_="Episode",
            properties=props,
            user_id=context.user_id,
            episode_id=episode_id,
        )

    # ── close (default): upsert the terminal content + flip state ─────
    if exists:
        result = handle.update_and_validate(
            iri=epi_iri,
            field_updates=props,
            content_fields=EPISODE_CONTENT_FIELDS,
            via_lazy_inline=True,
        )
        result_iri = epi_iri
    else:
        vr = handle.validate_node(value=episode_id, type_="Episode")
        if not vr.ok:
            raise SemanticValidationError(vr)
        result = handle.write_and_validate(
            value=episode_id,
            type_="Episode",
            properties=props,
            user_id=context.user_id,
            episode_id=episode_id,
        )
        result_iri = result.iri

    # Memory materialise-on-first-episode + MEMORY_CONTAINS_EPISODE edge
    # (Chat B D-B47 §4.6; ADR-0176 §3). Cluster key = the Episode's
    # ``request_pattern_iri``; Memory materialises once per pattern (idempotent
    # on its derived IRI) and each episode attaches via the within-role-graph
    # edge.
    request_pattern_iri = props.get("request_pattern_iri")
    if request_pattern_iri:
        _materialise_memory(
            handle, context.user_id, request_pattern_iri, result_iri
        )
    return result


def _memory_id_for(request_pattern_iri: str) -> str:
    """Deterministic, fragment-safe ``memory_id`` for a request-pattern cluster
    key (ADR-0176 §3). The raw ``request_pattern_iri`` is the cluster key but is
    not a stable IRI fragment, so the Memory IRI uses a content hash —
    idempotent (same pattern → same Memory)."""
    import hashlib

    digest = hashlib.sha1(request_pattern_iri.encode("utf-8")).hexdigest()[:16]
    return f"tp-{digest}"


def _materialise_memory(handle, user_id, request_pattern_iri, episode_iri) -> None:
    """Materialise the Memory composite for ``request_pattern_iri`` on first
    episode (idempotent) and add the ``MEMORY_CONTAINS_EPISODE`` edge
    (Memory → Episode) for ``episode_iri`` (ADR-0176 §3)."""
    from mindsos_knowledge.schemas.episodic_memories import (
        EDGE_MEMORY_CONTAINS_EPISODE,
    )

    memory_id = _memory_id_for(request_pattern_iri)
    mem_iri = handle.mint_iri("Memory", user_id=user_id, memory_id=memory_id)
    g = handle.graph()
    if mem_iri not in g.nodes:
        handle.write_and_validate(
            value={"request_pattern_iri": request_pattern_iri},
            type_="Memory",
            user_id=user_id,
            memory_id=memory_id,
        )
    g.add_edge(
        g.nodes[mem_iri],
        g.nodes[episode_iri],
        type_name=EDGE_MEMORY_CONTAINS_EPISODE,
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
