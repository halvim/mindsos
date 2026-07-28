"""``capacity:learning-methods:learn_parameter`` — Local learned-parameter write.

CR learned-parameters (amends ADR-0152 §6). Persists/updates ONE
probabilistically-learned parameter (a confidence / distribution / weight) as a
node in the user's Local ``learned-parameters`` role-graph, addressed by
``(parameter_set, target)`` (Option B: one node per knob). Overwrite-in-place —
a re-learn REPLACES the node at the same IRI; no version history is kept
(review decision: "we don't need old versions... just update"). Every write
stamps who/when/why (``learned_by`` / ``recorded_at`` / ``reason``).

Write-body per ADR-0180: obtains its :class:`KLWriteHandle` from the
L4-injected ``context.writeable`` capability (the body holds no session and
makes no authorization decision). Because
:meth:`KLWriteHandle.write_and_validate` sets only ``value``+IRI and cannot
overwrite a live id (``add_node`` raises ``IdentityError``), the body writes
through ``handle.graph()`` directly: ``remove_node`` the prior node (if any)
then ``add_node`` with the parameter properties. Overwrite is delete+create
(a fresh node at the same id), not an in-place field edit, so the ADR-0153 §3
edit-time discipline machinery is not engaged.

Realm: this capacity ALWAYS targets ``scope="local"``. Global
``learned-parameters`` is ``admin_authored`` — ``write_and_validate`` (and the
admin gate) forbid L3/L4 Global writes. System improvement of a Global
parameter is Local-write + a promotion proposal (the separate approval CR).

Outputs: ``()`` — write-capacity terminator (R2 PB-K). The runtime surfaces the
:class:`WriteResult` via ``InvocationResult.write_outcome``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, List

from ..capacity import Capacity
from ..datastate import DataState, ShapeDescriptor
from ..identifiers import (
    CATEGORY_LEARNING_METHODS,
    capacity_iri,
    datastate_iri,
)

# ── DataState IRI (record shape) ───────────────────────────────────────

DS_LEARNED_PARAMETER_WRITE = datastate_iri("learned_parameter.write")


def learn_parameter_datastates() -> List[DataState]:
    """The record DataState ``capacity:learning-methods:learn_parameter`` reads.

    Required keys: ``parameter_set`` (str), ``target`` (str), ``value`` (Any),
    ``learned_by`` (str). Optional: ``confidence`` (float|None), ``reason``
    (str|None) — read defensively in the body.
    """
    return [
        DataState(
            name="learned_parameter.write",
            shape=ShapeDescriptor.record(
                {
                    "parameter_set": "str",
                    "target": "str",
                    "value": "Any",
                    "learned_by": "str",
                },
                opaque_tag="learned_parameter.write",
            ),
            description=(
                "Record bearing one learned parameter to persist/update in the "
                "user's Local learned-parameters role-graph: parameter_set + "
                "target address the node (Option B), value is the payload, "
                "learned_by/reason are provenance, confidence is optional."
            ),
            provenance_category=CATEGORY_LEARNING_METHODS,
        ),
    ]


def _now_iso() -> str:
    """ISO-8601 UTC millisecond timestamp (matches mindsos_server.pipelines)."""
    now = datetime.now(UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


# ── Capacity body ──────────────────────────────────────────────────────


def _learn_parameter_impl(**kwargs: Any) -> Any:
    """Body of ``capacity:learning-methods:learn_parameter`` (write-half; ADR-0180).

    Overwrite-in-place via ``handle.graph()``: ``remove_node`` the prior node
    at the derived IRI (if present) then ``add_node`` the new value + props.
    Returns a :class:`WriteResult` (the write-body envelope contract).
    """
    from mindsos_knowledge.identifiers import ROLE_LEARNED_PARAMETERS
    from mindsos_knowledge.schemas.learned_parameters import (
        NODE_LEARNED_PARAMETER,
    )
    from mindsos_knowledge.write_handle import WriteResult

    context = kwargs.get("context")
    writeable = getattr(context, "writeable", None)
    if writeable is None:
        raise RuntimeError(
            "capacity:learning-methods:learn_parameter requires L4 dispatch: "
            "the CapacityContext must carry a pre-authorized `writeable` "
            "capability (ADR-0180). Write capacities are not invocable via the "
            "L3-internal dict path."
        )

    rec = kwargs[DS_LEARNED_PARAMETER_WRITE]
    pset = str(rec["parameter_set"])
    target = str(rec["target"])
    value = rec["value"]
    learned_by = str(rec["learned_by"])
    confidence = rec.get("confidence")
    reason = rec.get("reason")

    handle = writeable(
        role=ROLE_LEARNED_PARAMETERS, scope="local", version="v1"
    )
    iri = handle.mint_iri("LearnedParameter", parameter_id=f"{pset}:{target}")

    now = _now_iso()
    # Property bag: primitives only (add_node validates); omit None-valued
    # optionals rather than storing None.
    props: dict[str, Any] = {
        "parameter_set_iri": pset,
        "target_parameter_iri": target,
        "storage_mode": "inline",
        "learned_by": learned_by,
        "recorded_at": now,
        "applied_at": now,
    }
    if confidence is not None:
        props["confidence"] = confidence
    if reason is not None:
        props["reason"] = reason

    g = handle.graph()
    if iri in g.nodes:
        g.remove_node(iri)  # overwrite = remove + add (mutable_with_retention)
    g.add_node(
        value=value,
        type_name=NODE_LEARNED_PARAMETER,
        properties=props,
        node_id=iri,
    )
    return WriteResult(
        iri=iri,
        role=ROLE_LEARNED_PARAMETERS,
        scope="local",
        written_at=datetime.now(UTC),
        extras={},
    )


# ── Capacity factory ───────────────────────────────────────────────────


def build_learn_parameter() -> Capacity:
    """Build the ``capacity:learning-methods:learn_parameter`` declaration."""
    return Capacity(
        name="learn_parameter",
        category=CATEGORY_LEARNING_METHODS,
        inputs=(DS_LEARNED_PARAMETER_WRITE,),
        outputs=(),
        implementation=_learn_parameter_impl,
        description=(
            "Persist/update one probabilistically-learned parameter in the "
            "user's Local learned-parameters role-graph, addressed by "
            "(parameter_set, target); overwrite-in-place; stamps "
            "learned_by/recorded_at/reason. Write terminator (outputs=())."
        ),
        cost_prior=2.0,
        latency_ms_prior=5.0,
    )


# ── Idempotent installer (consolidate.py precedent) ────────────────────

_LEARN_PARAMETER_IRI = capacity_iri(CATEGORY_LEARNING_METHODS, "learn_parameter")
_DS_IRIS = (DS_LEARNED_PARAMETER_WRITE,)
_CAP_IRIS = (_LEARN_PARAMETER_IRI,)
_FAMILY_IRIS = _DS_IRIS + _CAP_IRIS


def install_learn_parameter_capacities(capacity_layer) -> None:
    """Register the learn_parameter DataState + capacity on ``capacity_layer``.

    Idempotent with partial-state detection (Phase 31 install precedent).
    Targets Global (capacity registry is Global; the WRITE targets Local at
    invoke time via the scope='local' handle).
    """
    from ..bootstrap import ensure_datastate_graph
    from ..exceptions import CapacityRegistrationError

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
            "install_learn_parameter_capacities: partial install state — "
            f"datastates_present={sorted(ds_present)}, "
            f"capacities_present={sorted(cap_present)}"
        )
    for ds in learn_parameter_datastates():
        capacity_layer.register_datastate(ds)
    capacity_layer.register_capacity(build_learn_parameter())


__all__ = [
    "DS_LEARNED_PARAMETER_WRITE",
    "learn_parameter_datastates",
    "build_learn_parameter",
    "install_learn_parameter_capacities",
]
