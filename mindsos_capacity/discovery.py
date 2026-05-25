"""Auto-discovery of TYPE_COMPAT edges (Phase 29 ship).

When a new capacity node ``C`` is registered, discovery scans every
already-registered capacity ``C'`` for a DataState appearing both as
``C`` output and ``C'`` input. For each such match:

- a Core ``Edge`` of type :data:`EDGE_TYPE_COMPAT` is added to the
  **source capacity's home graph** if both capacities share that graph
  (intra-category);
- otherwise a ``MetaEdge`` is added at the metagraph level so the L3
  flow is still expressible across category boundaries (cross-category).

The algorithm is symmetric — it also checks ``C'`` outputs against
``C`` inputs.

When a DataState is registered, discovery re-runs across every
capacity pair to pick up matches that were impossible before (because
a shape was not yet declared). Note: under the current Phase 28-29
contract, ``CapacityLayer.register_capacity`` validates input/output
DataState IRIs against the already-registered DataState graph
(``_CapacityBase.validate_for_registration``), so forward-reference
DataStates are not permitted; the ``discover_for_datastate`` trigger
emits zero edges at v1. The function is shipped for parent parity +
future scope (Phase 33+ write-side flows may relax the forward-ref
restriction).

Near-compatibility via adapters is handled implicitly — an
:class:`~mindsos_capacity.capacity.Adapter` is just another
``_CapacityBase`` and its ``inputs``/``outputs`` get walked like any
other capacity. The ``adapter_capacity`` field on
:class:`~mindsos_capacity.views.SuccessorHop` is reserved for the
adapter-bridge synthesis step a future phase will ship; Phase 29 only
emits ``strictness="strict"`` hops with ``adapter_capacity=None``.

Auto-discovered edges carry ``discovered_automatically=True`` per
ADR-0069 + ADR-0086 — admin overrides omit the flag and survive
``rediscover_all``. See ADR-0086 §Implementation (Phase 29) for the
admin-deleted-auto-edge open question (deferred to first reported
foot-gun per R1 PB-13).

Halvim divergence from parent: :meth:`mindsos_core.Metagraph.add_metaedge`
takes ``source_graph_id: str`` + ``target_graph_id: str`` (not Graph
objects) — :func:`_add_edge` passes ``.graph_id``. MetaEdge removal in
:func:`_drop_auto_edges` uses the public
:meth:`mindsos_core.Metagraph.remove_metaedge` method (parent reaches
into private state; halvim's public method exists since Phase 05a).
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from mindsos_core import Edge, Graph, MetaEdge, Metagraph, Node

from .identifiers import EDGE_TYPE_COMPAT


# ── Public discovery entry points ──────────────────────────────────────

def discover_for_capacity(
    metagraph: Metagraph,
    capacity_node: Node,
    capacity_graph: Graph,
    *,
    capacity_index: Dict[str, Tuple[Node, Graph]],
) -> List[object]:
    """Discover TYPE_COMPAT edges for a freshly-registered capacity.

    Args:
        metagraph: The L3 metagraph the capacity lives in.
        capacity_node: The newly-registered capacity node.
        capacity_graph: The category graph containing ``capacity_node``.
        capacity_index: Maps every already-registered capacity IRI to
            ``(node, graph)`` pairs — used to discover back-edges from
            existing capacities to the new one. The new capacity's
            entry MUST already be present (caller responsibility); the
            loop skips self via ``node_id`` comparison.

    Returns:
        The list of ``Edge`` / ``MetaEdge`` objects that were created.
    """
    created: List[object] = []
    new_inputs = _prop_list(capacity_node, "inputs")
    new_outputs = _prop_list(capacity_node, "outputs")

    for other_iri, (other_node, other_graph) in capacity_index.items():
        if other_node.node_id == capacity_node.node_id:
            continue
        other_inputs = _prop_list(other_node, "inputs")
        other_outputs = _prop_list(other_node, "outputs")

        # Forward: new outputs → other inputs.
        for ds in new_outputs:
            if ds in other_inputs:
                edge = _add_edge(
                    metagraph,
                    capacity_node,
                    capacity_graph,
                    other_node,
                    other_graph,
                    via_datastate=ds,
                )
                if edge is not None:
                    created.append(edge)
        # Backward: other outputs → new inputs.
        for ds in other_outputs:
            if ds in new_inputs:
                edge = _add_edge(
                    metagraph,
                    other_node,
                    other_graph,
                    capacity_node,
                    capacity_graph,
                    via_datastate=ds,
                )
                if edge is not None:
                    created.append(edge)
    return created


def discover_for_datastate(
    metagraph: Metagraph,
    datastate_iri: str,
    *,
    capacity_index: Dict[str, Tuple[Node, Graph]],
) -> List[object]:
    """Re-run discovery when a new DataState is added.

    Only pairs that use ``datastate_iri`` as the connecting DataState
    are considered, keeping the cost manageable.

    Phase 29 contract: under the current Phase 28-29 registration
    invariant (``_CapacityBase.validate_for_registration`` forbids
    forward-reference DataStates), this trigger emits zero edges —
    every existing capacity referencing ``datastate_iri`` must have
    been registered AFTER the DataState was registered. Shipped for
    parent parity + future-scope (a phase that relaxes the forward-ref
    restriction can rely on this hook).
    """
    created: List[object] = []
    for a_iri, (a_node, a_graph) in capacity_index.items():
        a_outputs = _prop_list(a_node, "outputs")
        if datastate_iri not in a_outputs:
            continue
        for b_iri, (b_node, b_graph) in capacity_index.items():
            if a_iri == b_iri:
                continue
            b_inputs = _prop_list(b_node, "inputs")
            if datastate_iri in b_inputs and not _edge_already_exists(
                metagraph, a_node, b_node, datastate_iri
            ):
                edge = _add_edge(
                    metagraph, a_node, a_graph, b_node, b_graph,
                    via_datastate=datastate_iri,
                )
                if edge is not None:
                    created.append(edge)
    return created


def rediscover_all(
    metagraph: Metagraph,
    *,
    capacity_index: Dict[str, Tuple[Node, Graph]],
) -> List[object]:
    """Full re-run (drop every auto-discovered edge, rebuild from scratch).

    Useful after bulk re-registration and during tests. Manual
    admin-added edges carry ``discovered_automatically=False`` (or
    absent the property entirely) and are preserved per ADR-0086.

    Phase 29 open gap (deferred): if an admin DELETES an auto edge,
    the next ``rediscover_all`` re-adds it. ADR-0086 §Implementation
    (Phase 29) flags this for resolution by the first reported
    foot-gun (proposed mechanisms: anti-edge marker, ``blocked=True``
    flag, or admin-deletion-tombstone).
    """
    _drop_auto_edges(metagraph)
    created: List[object] = []
    for a_iri, (a_node, a_graph) in capacity_index.items():
        a_outputs = _prop_list(a_node, "outputs")
        for b_iri, (b_node, b_graph) in capacity_index.items():
            if a_iri == b_iri:
                continue
            b_inputs = _prop_list(b_node, "inputs")
            for ds in a_outputs:
                if ds in b_inputs and not _edge_already_exists(
                    metagraph, a_node, b_node, ds
                ):
                    edge = _add_edge(
                        metagraph, a_node, a_graph, b_node, b_graph,
                        via_datastate=ds,
                    )
                    if edge is not None:
                        created.append(edge)
    return created


# ── Internals ──────────────────────────────────────────────────────────

def _prop_list(node: Node, key: str) -> Sequence[str]:
    """Return a node's property as a sequence, tolerating missing keys."""
    value = node.properties.get(key)
    if value is None:
        return ()
    if not isinstance(value, list):
        raise TypeError(f"Node {node.node_id!r} property {key!r} is not a list")
    return value


def _edge_already_exists(
    metagraph: Metagraph,
    source: Node,
    target: Node,
    datastate_iri: str,
) -> bool:
    """Avoid emitting duplicate TYPE_COMPAT edges for the same DataState.

    Walks both intra-graph Edges (across every category graph) and
    cross-graph MetaEdges. Used by :func:`discover_for_datastate` +
    :func:`rediscover_all`'s de-dup guard. Parent-verbatim semantics
    (R5 PB-37): no soft-delete filter — deprecated edges still count
    as "exists" and block re-emission.
    """
    # Within-graph edges.
    for g in metagraph.graphs.values():
        for e in g.edges.values():
            if (
                e.type_name == EDGE_TYPE_COMPAT
                and e.source.node_id == source.node_id
                and e.target.node_id == target.node_id
                and e.properties.get("via_datastate") == datastate_iri
            ):
                return True
    # Cross-graph metaedges.
    for me in metagraph.metaedges.values():
        if (
            me.type_name == EDGE_TYPE_COMPAT
            and me.properties.get("source_capacity") == source.node_id
            and me.properties.get("target_capacity") == target.node_id
            and me.properties.get("via_datastate") == datastate_iri
        ):
            return True
    return False


def _drop_auto_edges(metagraph: Metagraph) -> None:
    """Drop every edge / metaedge stamped ``discovered_automatically=True``.

    Manual edges (no flag, or flag explicitly ``False``) are preserved
    per ADR-0086. Parent-verbatim semantics (R5 PB-38): no soft-delete
    filter — tombstoned auto edges also get removed.

    Halvim divergence: MetaEdge removal uses the public
    :meth:`mindsos_core.Metagraph.remove_metaedge` method (parent
    reaches into private state; halvim's public method exists since
    Phase 05a).
    """
    # Intra-graph.
    for g in metagraph.graphs.values():
        to_remove = [
            eid for eid, e in g.edges.items()
            if e.type_name == EDGE_TYPE_COMPAT
            and e.properties.get("discovered_automatically") is True
        ]
        for eid in to_remove:
            g.remove_edge(eid)
    # Meta-level.
    to_remove_me = [
        me_id for me_id, me in metagraph.metaedges.items()
        if me.type_name == EDGE_TYPE_COMPAT
        and me.properties.get("discovered_automatically") is True
    ]
    for me_id in to_remove_me:
        metagraph.remove_metaedge(me_id)


def _add_edge(
    metagraph: Metagraph,
    source_node: Node,
    source_graph: Graph,
    target_node: Node,
    target_graph: Graph,
    *,
    via_datastate: str,
):
    """Add a TYPE_COMPAT edge — intra-graph when possible, meta-level otherwise.

    Halvim divergence from parent: :meth:`Metagraph.add_metaedge`
    takes ``source_graph_id: str`` + ``target_graph_id: str`` (not
    Graph objects) — we pass ``.graph_id``.
    """
    properties = {
        "via_datastate": via_datastate,
        "strictness": "strict",
        "discovered_automatically": True,
    }
    if source_graph.graph_id == target_graph.graph_id:
        # Intra-graph Edge — Core-enforced schema (Phase 28 EDGE_TYPE_COMPAT
        # EdgeType whitelist permits via_datastate / strictness /
        # discovered_automatically per schemas.py).
        return source_graph.add_edge(
            source_node, target_node, EDGE_TYPE_COMPAT, properties=properties
        )
    # Cross-graph MetaEdge. Capacity IDs are stored as properties so the
    # pipeline-finder (Phase 30) can recover source/target capacity
    # without touching private state.
    properties = dict(properties)
    properties["source_capacity"] = source_node.node_id
    properties["target_capacity"] = target_node.node_id
    return metagraph.add_metaedge(
        source_graph.graph_id,
        target_graph.graph_id,
        EDGE_TYPE_COMPAT,
        label=f"{source_node.node_id} -> {target_node.node_id}",
        properties=properties,
    )


__all__ = [
    "discover_for_capacity",
    "discover_for_datastate",
    "rediscover_all",
]
