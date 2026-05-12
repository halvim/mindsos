"""Materialise machinery (Phase 06 row §E + P6 A + P18 A + P40 A +
round-7 P51 A + P54 B + P58 A + P63 A).

Each subclass exposes ``materialise(metagraph) -> Core object | dict``.
Returns fresh Core objects (fresh UUIDs per call); endpoint overrides
resolve via ``_resolve.py``; SubGraphInstance + GraphInstance produce
fresh ``Graph`` instances with fresh ``IdentityRegistry`` and copied
contents; CompositeInstance returns a recursive tree dict (top-level
shape per P39 A) wrapped through ``canonicalize`` for stable JSON
output (round-7 P63 A).

Materialise does NOT validate against schema (P16 A — attach-time
concern; Phase 07).
"""

from __future__ import annotations

import copy
from dataclasses import asdict
from typing import Any, Dict, Optional

from mindsos_core import (
    Edge,
    Graph,
    HyperEdge,
    IdentityRegistry,
    Metagraph,
    Node,
)
from mindsos_core.exceptions import IdentityError
from mindsos_core.models.metagraph import MetaEdge, MetaHyperEdge

from ._resolve import resolve_graph, resolve_node, resolve_nodes
from .exceptions import DanglingTemplateError
from .models.element_instance import (
    CompositeInstance,
    EdgeInstance,
    ElementInstance,
    GraphInstance,
    HyperEdgeInstance,
    MetaEdgeInstance,
    MetaHyperEdgeInstance,
    NodeInstance,
    SubGraphInstance,
)
from .utils.canonicalize import canonicalize


# ── per-subclass materialise dispatch ───────────────────────────────────────


def materialise(instance: Any, metagraph: Metagraph) -> Any:
    """Materialise ``instance`` into a fresh Core object (or composite
    tree dict). Dispatch by class."""
    if isinstance(instance, NodeInstance):
        return _materialise_node(instance, metagraph)
    if isinstance(instance, EdgeInstance):
        return _materialise_edge(instance, metagraph)
    if isinstance(instance, HyperEdgeInstance):
        return _materialise_hyperedge(instance, metagraph)
    if isinstance(instance, SubGraphInstance):
        return _materialise_subgraph(instance, metagraph)
    if isinstance(instance, GraphInstance):
        return _materialise_graph(instance, metagraph)
    if isinstance(instance, MetaEdgeInstance):
        return _materialise_metaedge(instance, metagraph)
    if isinstance(instance, MetaHyperEdgeInstance):
        return _materialise_metahyperedge(instance, metagraph)
    if isinstance(instance, CompositeInstance):
        return _materialise_composite(instance, metagraph)
    raise TypeError(
        f"materialise: unsupported instance type {type(instance).__name__}"
    )


# ── NodeInstance ────────────────────────────────────────────────────────────


def _materialise_node(instance: NodeInstance, metagraph: Metagraph) -> Node:
    template = _find_node_template(instance.template_id, metagraph)
    overrides = instance.overrides
    user_props = _user_property_subset(overrides, instance.STRUCTURAL_KEYS)
    merged_props = {**template.properties, **user_props}
    return Node(
        value=template.value,
        type_name=template.type_name,
        properties=merged_props,
    )


# ── EdgeInstance ────────────────────────────────────────────────────────────


def _materialise_edge(instance: EdgeInstance, metagraph: Metagraph) -> Edge:
    template = _find_edge_template(instance.template_id, metagraph)
    overrides = instance.overrides

    # Endpoint resolution per round-7 P58 A.
    if "source_id" in overrides:
        source = resolve_node(metagraph, overrides["source_id"])
    else:
        source = template.source
    if "target_id" in overrides:
        target = resolve_node(metagraph, overrides["target_id"])
    else:
        target = template.target

    label = overrides.get("label", template.label)
    user_props = _user_property_subset(overrides, instance.STRUCTURAL_KEYS)
    merged_props = {**template.properties, **user_props}
    return Edge(
        source=source,
        target=target,
        type_name=template.type_name,
        label=label,
        properties=merged_props,
    )


# ── HyperEdgeInstance ───────────────────────────────────────────────────────


def _materialise_hyperedge(
    instance: HyperEdgeInstance, metagraph: Metagraph
) -> HyperEdge:
    template = _find_hyperedge_template(instance.template_id, metagraph)
    overrides = instance.overrides

    if "member_ids" in overrides:
        nodes = resolve_nodes(metagraph, overrides["member_ids"])
    else:
        nodes = set(template.nodes)

    label = overrides.get("label", template.label)
    user_props = _user_property_subset(overrides, instance.STRUCTURAL_KEYS)
    merged_props = {**template.properties, **user_props}
    return HyperEdge(
        nodes=nodes,
        type_name=template.type_name,
        label=label,
        properties=merged_props,
    )


# ── SubGraphInstance (round-7 P51 A spec) ───────────────────────────────────


def _materialise_subgraph(
    instance: SubGraphInstance, metagraph: Metagraph
) -> Graph:
    """Fresh ``Graph`` containing copied nodes/edges from the source
    Graph's selected subset. Fresh ``IdentityRegistry``; fresh ids;
    deep-copy of properties; ``role`` inherited.
    """
    source = _find_graph_template(instance.template_id, metagraph)
    node_ids = frozenset(instance.overrides.get("node_ids", frozenset()))
    edge_ids = frozenset(instance.overrides.get("edge_ids", frozenset()))

    return _clone_graph_subset(
        source,
        node_ids=node_ids,
        edge_ids=edge_ids,
        name=f"{source.name}__subgraph_{instance.id[:8]}",
        inherit_role=True,
    )


# ── GraphInstance (round-7 P54 B — full clone) ──────────────────────────────


def _materialise_graph(
    instance: GraphInstance, metagraph: Metagraph
) -> Graph:
    """Deep-copy clone of the source Graph: all nodes / edges /
    hyperedges, fresh ids, fresh IdentityRegistry, role inherited.
    """
    source = _find_graph_template(instance.template_id, metagraph)
    return _clone_graph_subset(
        source,
        node_ids=frozenset(source.nodes.keys()),
        edge_ids=frozenset(source.edges.keys()) | frozenset(
            source.hyperedges.keys()
        ),
        name=f"{source.name}__instance_{instance.id[:8]}",
        inherit_role=True,
    )


def _clone_graph_subset(
    source: Graph,
    *,
    node_ids: frozenset,
    edge_ids: frozenset,
    name: str,
    inherit_role: bool,
) -> Graph:
    """Shared clone path for SubGraphInstance + GraphInstance
    materialise."""
    fresh_identity = IdentityRegistry()
    new_graph = Graph(
        name=name,
        role=source.role if inherit_role else None,
        identity=fresh_identity,
    )
    # Map old-node-id → new Node object for edge reconstruction.
    node_remap: Dict[str, Node] = {}
    for nid in node_ids:
        if nid not in source.nodes:
            raise IdentityError(
                f"_clone_graph_subset: node_id {nid!r} not in source "
                f"graph {source.graph_id!r}."
            )
        orig = source.nodes[nid]
        new_node = new_graph.add_node(
            value=orig.value,
            type_name=orig.type_name,
            properties=copy.deepcopy(orig.properties),
            _validate=False,
        )
        node_remap[nid] = new_node

    # Clone edges + hyperedges. Edges only if both endpoints survived
    # the node_ids filter.
    for eid in edge_ids:
        if eid in source.edges:
            orig_edge = source.edges[eid]
            sid = orig_edge.source.node_id
            tid = orig_edge.target.node_id
            if sid not in node_remap or tid not in node_remap:
                # Caller is GraphInstance (full clone), so node_ids
                # should cover all source nodes; or SubGraphInstance
                # which already invariant-checked endpoint membership.
                # Defensive raise for safety.
                raise IdentityError(
                    f"_clone_graph_subset: edge {eid!r} endpoint "
                    f"missing from node_ids selection."
                )
            new_graph.add_edge(
                source=node_remap[sid],
                target=node_remap[tid],
                type_name=orig_edge.type_name,
                label=orig_edge.label,
                properties=copy.deepcopy(orig_edge.properties),
                _validate=False,
            )
        elif eid in source.hyperedges:
            orig_he = source.hyperedges[eid]
            new_members = set()
            for member in orig_he.nodes:
                if member.node_id not in node_remap:
                    raise IdentityError(
                        f"_clone_graph_subset: hyperedge {eid!r} "
                        f"member {member.node_id!r} missing from "
                        f"node_ids selection."
                    )
                new_members.add(node_remap[member.node_id])
            new_graph.add_hyperedge(
                nodes=new_members,
                type_name=orig_he.type_name,
                label=orig_he.label,
                properties=copy.deepcopy(orig_he.properties),
                _validate=False,
            )
        else:
            raise IdentityError(
                f"_clone_graph_subset: edge_id {eid!r} not in source "
                f"graph (neither edges nor hyperedges)."
            )
    return new_graph


# ── MetaEdgeInstance / MetaHyperEdgeInstance ────────────────────────────────


def _materialise_metaedge(
    instance: MetaEdgeInstance, metagraph: Metagraph
) -> MetaEdge:
    template = _find_metaedge_template(instance.template_id, metagraph)
    overrides = instance.overrides

    source_gid = overrides.get("source_graph_id", template.source_graph_id)
    target_gid = overrides.get("target_graph_id", template.target_graph_id)
    # P58 A validation — overrides must point to contained graphs.
    if source_gid not in metagraph.graphs:
        raise IdentityError(
            f"_materialise_metaedge: source_graph_id {source_gid!r} "
            f"not in metagraph."
        )
    if target_gid not in metagraph.graphs:
        raise IdentityError(
            f"_materialise_metaedge: target_graph_id {target_gid!r} "
            f"not in metagraph."
        )

    label = overrides.get("label", template.label)
    user_props = _user_property_subset(overrides, instance.STRUCTURAL_KEYS)
    merged_props = {**template.properties, **user_props}
    return MetaEdge(
        source_graph_id=source_gid,
        target_graph_id=target_gid,
        type_name=template.type_name,
        label=label,
        properties=merged_props,
    )


def _materialise_metahyperedge(
    instance: MetaHyperEdgeInstance, metagraph: Metagraph
) -> MetaHyperEdge:
    template = _find_metahyperedge_template(instance.template_id, metagraph)
    overrides = instance.overrides

    if "graph_ids" in overrides:
        gids = list(overrides["graph_ids"])
    else:
        gids = list(template.graph_ids)
    for gid in gids:
        if gid not in metagraph.graphs:
            raise IdentityError(
                f"_materialise_metahyperedge: graph_id {gid!r} not in "
                f"metagraph."
            )

    label = overrides.get("label", template.label)
    user_props = _user_property_subset(overrides, instance.STRUCTURAL_KEYS)
    merged_props = {**template.properties, **user_props}
    return MetaHyperEdge(
        graph_ids=gids,
        type_name=template.type_name,
        label=label,
        properties=merged_props,
    )


# ── CompositeInstance (round-7 P63 A — canonicalize-wrapped asdict) ─────────


def _materialise_composite(
    instance: CompositeInstance, metagraph: Metagraph
) -> Dict[str, Any]:
    """Recursive tree dict per P18 A + P39 A. Each element member
    materialised through ``asdict`` then wrapped in
    :func:`canonicalize` for stable JSON output."""
    members_out: Dict[str, Any] = {}
    for m in instance.members:
        if isinstance(m, CompositeInstance):
            members_out[m.id] = _materialise_composite(m, metagraph)
        else:
            # Element instance — materialise → Core dataclass → asdict
            # → canonicalize.
            core_obj = materialise(m, metagraph)
            members_out[m.id] = canonicalize(asdict(core_obj))
    return {
        "kind": "composite",
        "id": instance.id,
        "metagraph_id": instance.metagraph_id,
        "bundle_overrides": canonicalize(instance.bundle_overrides),
        "members": members_out,
    }


# ── template-lookup helpers ─────────────────────────────────────────────────


def _user_property_subset(
    overrides: Dict[str, Any], structural_keys: frozenset
) -> Dict[str, Any]:
    """Return the subset of ``overrides`` that are user-properties
    (not in the subclass's structural allow-list)."""
    return {k: v for k, v in overrides.items() if k not in structural_keys}


def _find_node_template(template_id: str, metagraph: Metagraph) -> Node:
    for graph in metagraph.graphs.values():
        if template_id in graph.nodes:
            return graph.nodes[template_id]
    raise DanglingTemplateError(
        f"Node template {template_id!r} not found in any contained "
        f"graph (template may have been removed)."
    )


def _find_edge_template(template_id: str, metagraph: Metagraph) -> Edge:
    for graph in metagraph.graphs.values():
        if template_id in graph.edges:
            return graph.edges[template_id]
    raise DanglingTemplateError(
        f"Edge template {template_id!r} not found in any contained "
        f"graph (template may have been removed)."
    )


def _find_hyperedge_template(
    template_id: str, metagraph: Metagraph
) -> HyperEdge:
    for graph in metagraph.graphs.values():
        if template_id in graph.hyperedges:
            return graph.hyperedges[template_id]
    raise DanglingTemplateError(
        f"HyperEdge template {template_id!r} not found in any "
        f"contained graph (template may have been removed)."
    )


def _find_graph_template(template_id: str, metagraph: Metagraph) -> Graph:
    if template_id not in metagraph.graphs:
        raise DanglingTemplateError(
            f"Graph template {template_id!r} not contained in metagraph."
        )
    return metagraph.graphs[template_id]


def _find_metaedge_template(
    template_id: str, metagraph: Metagraph
) -> MetaEdge:
    if template_id not in metagraph.metaedges:
        raise DanglingTemplateError(
            f"MetaEdge template {template_id!r} not in metagraph."
        )
    return metagraph.metaedges[template_id]


def _find_metahyperedge_template(
    template_id: str, metagraph: Metagraph
) -> MetaHyperEdge:
    if template_id not in metagraph.metahyperedges:
        raise DanglingTemplateError(
            f"MetaHyperEdge template {template_id!r} not in metagraph."
        )
    return metagraph.metahyperedges[template_id]
