"""The ``Graph`` primitive (Phase 03 slim port).

A ``Graph`` owns collections of nodes, edges, and hyperedges keyed by id,
plus an optional ``IdentityRegistry`` (shared with its containing
``Metagraph`` when one exists in Phase 05+).

A ``Graph`` may carry a ``role`` string — ``"ontology"``, ``"lexicon"``,
``"concepts"``, … — which the Knowledge Layer uses to identify what the
graph represents.

Phase 03 slim-port strips (per PHASE_MAP Phase 03 row, deferral list):

* ``schema`` parameter and all ``Schema`` validation hooks — Phase 04.
* ``properties`` parameter / graph-level property bag (ADR-0130) — Phase 05/10.
* ``_version`` OCC bump on update (ADR-0127) — Phase 07.
* Soft-delete iterators / ``deprecate_*`` / ``dispute_*`` (ADR-0133) — Phase 10.
* ``_restore_*`` reconstruction helpers — Phase 08.
* ``update_node_properties`` / ``update_edge_properties`` — Phase 04.
* ``_validated_*_properties`` schema-aware property validation — Phase 04.

Phase 03 ships exactly: ``__init__``, ``add_node``, ``add_edge``,
``add_hyperedge``, ``remove_node``, ``remove_edge``, ``remove_hyperedge``,
``__repr__``.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from ..cypher.identifiers import validate_edge_type_identifier
from ..exceptions import IdentityError, SchemaError
from .edge import Edge, HyperEdge
from .identity import IdentityRegistry, generate_uuid
from .node import Node


class Graph:
    """A typed graph with identity guards. No schema enforcement in Phase 03."""

    def __init__(
        self,
        name: str,
        *,
        role: Optional[str] = None,
        graph_id: Optional[str] = None,
        identity: Optional[IdentityRegistry] = None,
    ) -> None:
        """Create an empty graph.

        Args:
            name: Human-readable graph name.
            role: Optional semantic role ("ontology", "lexicon", …).
            graph_id: Optional explicit id (used during reconstruction in
                Phase 08; tester-facing graphs in Phase 03 always auto-mint).
            identity: Optional shared registry (used when a Phase 05
                metagraph contains this graph). If ``None``, a fresh
                per-graph registry is created.
        """
        self.graph_id: str = graph_id or generate_uuid()
        self.name: str = name
        self.role: Optional[str] = role
        self.identity: IdentityRegistry = identity or IdentityRegistry()
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        self.hyperedges: Dict[str, HyperEdge] = {}
        if graph_id is None:
            # Only register when we generated the id ourselves; restore
            # paths register explicitly after swapping in the DB id (Phase 08).
            self.identity.register(self.graph_id)

    # ── creation ──────────────────────────────────────────────────────────

    def add_node(
        self,
        value: Any,
        type_name: str,
        *,
        properties: Optional[Dict[str, Any]] = None,
        node_id: Optional[str] = None,
    ) -> Node:
        """Create and register a new node.

        Args:
            value: Primary display value (any JSON-serialisable type).
            type_name: Node type name. No validation in Phase 03 (Phase 04
                Schema validates against a declared NodeType vocabulary).
            properties: Open property bag. Defensive-copied; no validation
                in Phase 03 (Phase 04 adds property-shape validation).
            node_id: Optional explicit id. If ``None`` (default), a fresh
                UUID is generated. Used by importers that need stable
                content-addressed ids (e.g. the Knowledge Layer's stable
                IRI convention). Collisions raise :class:`IdentityError`.
        """
        props = dict(properties or {})
        if node_id is not None:
            node = Node(
                value=value, type_name=type_name, node_id=node_id, properties=props
            )
        else:
            node = Node(value=value, type_name=type_name, properties=props)
        self.identity.register(node.node_id)
        self.nodes[node.node_id] = node
        return node

    def add_edge(
        self,
        source: Node,
        target: Node,
        type_name: str,
        *,
        label: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        edge_id: Optional[str] = None,
    ) -> Edge:
        """Create and register a new directed edge.

        Validates ``type_name`` against the Cypher rel-type identifier
        regex (ADR-0021) before construction.

        Args:
            edge_id: Optional explicit id. If ``None``, a UUID is generated.
                Used by importers that want deterministic edge ids.

        Raises:
            CypherError: if ``type_name`` is unsafe to splice into Cypher.
            IdentityError: if ``source`` or ``target`` is not in this graph.
        """
        if source.node_id not in self.nodes:
            raise IdentityError(
                f"Source node {source.node_id!r} not in graph {self.name!r}"
            )
        if target.node_id not in self.nodes:
            raise IdentityError(
                f"Target node {target.node_id!r} not in graph {self.name!r}"
            )
        validate_edge_type_identifier(type_name)
        props = dict(properties or {})
        if edge_id is not None:
            edge = Edge(source, target, type_name, label, edge_id=edge_id, properties=props)
        else:
            edge = Edge(source, target, type_name, label, properties=props)
        self.identity.register(edge.edge_id)
        self.edges[edge.edge_id] = edge
        return edge

    def add_hyperedge(
        self,
        nodes: Iterable[Node],
        *,
        label: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        edge_id: Optional[str] = None,
    ) -> HyperEdge:
        """Create and register a new n-ary hyperedge.

        Args:
            edge_id: Optional explicit id. If ``None``, a UUID is generated.

        Raises:
            SchemaError: if ``nodes`` is empty (via ``HyperEdge.__post_init__``).
            IdentityError: if any member is not in this graph.
        """
        node_set = set(nodes)
        for n in node_set:
            if n.node_id not in self.nodes:
                raise IdentityError(
                    f"HyperEdge member {n.node_id!r} not in graph {self.name!r}"
                )
        props = dict(properties or {})
        if edge_id is not None:
            he = HyperEdge(nodes=node_set, label=label, edge_id=edge_id, properties=props)
        else:
            he = HyperEdge(nodes=node_set, label=label, properties=props)
        self.identity.register(he.edge_id)
        self.hyperedges[he.edge_id] = he
        return he

    # ── deletion ──────────────────────────────────────────────────────────

    def remove_node(self, node_id: str, *, cascade: bool = True) -> None:
        """Remove a node.

        With ``cascade=True``, incident edges and hyperedges are removed
        as well. With ``cascade=False``, raises :class:`SchemaError` if
        any edge or hyperedge still references the node.
        """
        if node_id not in self.nodes:
            raise IdentityError(f"Unknown node id: {node_id!r}")

        incident_edge_ids = [
            eid for eid, e in self.edges.items()
            if e.source.node_id == node_id or e.target.node_id == node_id
        ]
        incident_he_ids = [
            hid for hid, he in self.hyperedges.items()
            if any(n.node_id == node_id for n in he.nodes)
        ]

        if not cascade and (incident_edge_ids or incident_he_ids):
            raise SchemaError(
                f"Cannot remove node {node_id!r}: "
                f"{len(incident_edge_ids)} edge(s), "
                f"{len(incident_he_ids)} hyperedge(s) still reference it"
            )

        for eid in incident_edge_ids:
            self.remove_edge(eid)
        for hid in incident_he_ids:
            self.remove_hyperedge(hid)

        self.identity.unregister(node_id)
        del self.nodes[node_id]

    def remove_edge(self, edge_id: str) -> None:
        if edge_id not in self.edges:
            raise IdentityError(f"Unknown edge id: {edge_id!r}")
        self.identity.unregister(edge_id)
        del self.edges[edge_id]

    def remove_hyperedge(self, edge_id: str) -> None:
        if edge_id not in self.hyperedges:
            raise IdentityError(f"Unknown hyperedge id: {edge_id!r}")
        self.identity.unregister(edge_id)
        del self.hyperedges[edge_id]

    def __repr__(self) -> str:
        return (
            f"Graph(name={self.name!r}, role={self.role!r}, "
            f"nodes={len(self.nodes)}, edges={len(self.edges)}, "
            f"hyperedges={len(self.hyperedges)})"
        )
