"""The ``Graph`` primitive (Phase 04 surface).

A ``Graph`` owns collections of nodes, edges, and hyperedges keyed by id,
plus an optional ``IdentityRegistry`` (shared with its containing
``Metagraph`` when one exists in Phase 05+).

A ``Graph`` may carry a ``role`` string — ``"ontology"``, ``"lexicon"``,
``"concepts"``, … — which the Knowledge Layer uses to identify what the
graph represents.

A ``Graph`` may carry an optional ``Schema`` (Phase 04). When attached,
every ``add_node`` / ``add_edge`` / ``add_hyperedge`` / ``update_*``
runs through the schema's validation hooks. Without a schema, the graph
behaves identically to Phase 03 (open property bags, no type vocabulary).

Phase 04 slim-port still strips (deferral list inherited from Phase 03):

* ``properties`` parameter / graph-level property bag (ADR-0130) — Phase 05/10.
* ``Node._version`` OCC bump on update (ADR-0127) — Phase 07.
  (``update_*_properties`` ships in Phase 04 WITHOUT the version bump.)
* Soft-delete iterators / ``deprecate_*`` / ``dispute_*`` (ADR-0133) — Phase 10.
* ``_restore_*`` reconstruction helpers — Phase 08.

Phase 04 ships exactly: ``__init__``, ``add_node``, ``add_edge``,
``add_hyperedge``, ``update_node_properties``, ``update_edge_properties``,
``remove_node``, ``remove_edge``, ``remove_hyperedge``, ``__repr__``.

The ``_validate`` kwarg on ``add_*`` (Phase 04 — NEW1):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each ``add_*`` accepts ``_validate: bool = True``. When ``True``
(default), the call runs ``mindsos_core.schema.validate_user_properties``
on the property bag. When ``False``, that helper is skipped — but
schema-level checks (``Schema.require_node_type``,
``Schema.validate_node_properties`` / ``validate_edge``,
``Schema.validate_edge_properties``) STILL run if a schema is attached.

The kwarg exists ONLY for the Phase 04 graph-state-file rehydration path
to tolerate Phase 03 v=1 files that may contain reserved-key or
non-primitive properties (Phase 03 had no validate_user_properties at
all, so any property bag was accepted at write time). Mutations
(set-prop, fresh adds, attach-schema replay) keep the default ``True``
and continue to enforce the user-property contract — recovery from
poisoned legacy nodes is via ``set-prop --replace``.

Phase 08's ``_restore_*`` reconstruction helpers will subsume this kwarg
(restore paths bypass validation by design); Phase 04's ``_validate``
is the bridge.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional

from ..cypher.identifiers import validate_edge_type_identifier
from ..exceptions import IdentityError, SchemaError
from ..schema import Schema, validate_user_properties
from .edge import Edge, HyperEdge
from .identity import IdentityRegistry, generate_uuid
from .node import Node


class Graph:
    """A typed graph with identity guards and optional schema enforcement."""

    def __init__(
        self,
        name: str,
        *,
        role: Optional[str] = None,
        graph_id: Optional[str] = None,
        identity: Optional[IdentityRegistry] = None,
        schema: Optional[Schema] = None,
    ) -> None:
        """Create an empty graph.

        Args:
            name: Human-readable graph name.
            role: Optional semantic role ("ontology", "lexicon", …).
            graph_id: Optional explicit id (used during reconstruction in
                Phase 08; tester-facing graphs in Phase 03+ always
                auto-mint).
            identity: Optional shared registry (used when a Phase 05
                metagraph contains this graph). If ``None``, a fresh
                per-graph registry is created.
            schema: Optional :class:`mindsos_core.schema.Schema`. When
                provided, every ``add_*`` and ``update_*`` runs through
                the schema's validation hooks. Without a schema, the
                graph behaves identically to Phase 03 (open bags, no
                type vocabulary).
        """
        self.graph_id: str = graph_id or generate_uuid()
        self.name: str = name
        self.role: Optional[str] = role
        self.identity: IdentityRegistry = identity or IdentityRegistry()
        self.schema: Optional[Schema] = schema
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
        _validate: bool = True,
    ) -> Node:
        """Create and register a new node.

        Args:
            value: Primary display value (any JSON-serialisable type).
            type_name: Node type name. When a :class:`Schema` is attached,
                ``type_name`` MUST be a registered :class:`NodeType`
                (``UnknownTypeError`` otherwise). Without a schema, any
                non-empty string is accepted (parity with Phase 03).
            properties: Open property bag. Routed through the
                user-properties validator (reserved keys, primitives only)
                and — under a strict schema — the per-type ``PropertyType``
                check.
            node_id: Optional explicit id. If ``None`` (default), a fresh
                UUID is generated.
            _validate: When ``True`` (default), run
                ``validate_user_properties`` on the property bag. Set to
                ``False`` ONLY by the rehydration path
                (``mindsos_cli.commands.graph._state_to_graph``) to
                tolerate Phase 03 legacy state files. Schema-level
                checks (type registration, strict PropertyType maps)
                always run regardless of this flag.

        Raises:
            UnknownTypeError: under a schema, ``type_name`` is unregistered.
            PropertyShapeError: the property bag fails validation
                (only under ``_validate=True``).
            IdentityError: ``node_id`` collides with an existing id.
        """
        props = self._validated_node_properties(
            type_name, properties or {}, validate_user_props=_validate
        )
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
        _validate: bool = True,
    ) -> Edge:
        """Create and register a new directed edge.

        Validates ``type_name`` against the Cypher rel-type identifier
        regex (ADR-0021) before construction. Under a :class:`Schema`,
        also validates the source/target node types against the
        :class:`EdgeType`'s allowed sets and (under ``strict=True``) the
        property bag against the per-type ``PropertyType`` map.

        Args:
            edge_id: Optional explicit id. If ``None``, a UUID is generated.
            _validate: See :meth:`add_node`. Skips
                ``validate_user_properties`` only.

        Raises:
            CypherError: ``type_name`` is unsafe to splice into Cypher.
            IdentityError: ``source`` or ``target`` is not in this graph.
            UnknownTypeError: under a schema, ``type_name`` is unregistered
                or the source/target node type is outside the allowed set.
            PropertyShapeError: the property bag fails validation
                (only under ``_validate=True``).
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
        if self.schema is not None:
            self.schema.validate_edge(type_name, source.type_name, target.type_name)
        props = self._validated_edge_properties(
            type_name, properties or {}, validate_user_props=_validate
        )
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
        _validate: bool = True,
    ) -> HyperEdge:
        """Create and register a new n-ary hyperedge.

        HyperEdges are not typed in Phase 04 (no per-hyperedge ``type_name``);
        the property bag is validated against the user-properties contract
        only (no per-type ``PropertyType`` map).

        Args:
            edge_id: Optional explicit id. If ``None``, a UUID is generated.
            _validate: See :meth:`add_node`. Skips
                ``validate_user_properties`` on the property bag.

        Raises:
            SchemaError: ``nodes`` is empty (via ``HyperEdge.__post_init__``).
            IdentityError: any member is not in this graph.
            PropertyShapeError: the property bag fails validation
                (only under ``_validate=True``).
        """
        node_set = set(nodes)
        for n in node_set:
            if n.node_id not in self.nodes:
                raise IdentityError(
                    f"HyperEdge member {n.node_id!r} not in graph {self.name!r}"
                )
        raw_props = properties or {}
        props = (
            validate_user_properties(raw_props, scope="hyperedge")
            if _validate
            else dict(raw_props)
        )
        if edge_id is not None:
            he = HyperEdge(nodes=node_set, label=label, edge_id=edge_id, properties=props)
        else:
            he = HyperEdge(nodes=node_set, label=label, properties=props)
        self.identity.register(he.edge_id)
        self.hyperedges[he.edge_id] = he
        return he

    # ── updates (Phase 04) ────────────────────────────────────────────────

    def update_node_properties(
        self,
        node_id: str,
        properties: Mapping[str, Any],
        *,
        replace: bool = False,
    ) -> Node:
        """Merge (or replace) a node's property bag.

        Routes through schema validation when a :class:`Schema` is
        attached. Phase 04 does NOT bump ``Node._version`` (the OCC
        field doesn't exist on the slim-port Node — Phase 07 ADR-0127
        ships that).

        Note: ``update_*`` always validates the FULL merged candidate bag
        (no ``_validate=False`` escape hatch). If a node was loaded from
        a Phase 03 v=1 state file that contains reserved-key properties,
        a default merge will fail; recovery is via ``replace=True``,
        which strips the offending keys (and preserves ``ref:*`` keys —
        see the CLI ``set-prop`` command).

        Args:
            replace: If ``True``, swap the existing property bag entirely.
                Default ``False`` performs a ``dict.update``-style merge
                (parity with the parent project).

        Raises:
            IdentityError: ``node_id`` is not in this graph.
            UnknownTypeError / PropertyShapeError: schema validation failed.
        """
        node = self.nodes.get(node_id)
        if node is None:
            raise IdentityError(f"Unknown node id: {node_id!r}")
        candidate = dict(properties) if replace else {**node.properties, **properties}
        validated = self._validated_node_properties(node.type_name, candidate)
        if replace:
            node.properties = validated
        else:
            node.properties.update(validated)
        return node

    def update_edge_properties(
        self,
        edge_id: str,
        properties: Mapping[str, Any],
        *,
        replace: bool = False,
    ) -> Edge:
        """Merge (or replace) an edge's property bag.

        See :meth:`update_node_properties` for semantics.
        """
        edge = self.edges.get(edge_id)
        if edge is None:
            raise IdentityError(f"Unknown edge id: {edge_id!r}")
        candidate = dict(properties) if replace else {**edge.properties, **properties}
        validated = self._validated_edge_properties(edge.type_name, candidate)
        if replace:
            edge.properties = validated
        else:
            edge.properties.update(validated)
        return edge

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

    # ── helpers ───────────────────────────────────────────────────────────

    def _validated_node_properties(
        self,
        type_name: str,
        properties: Mapping[str, Any],
        *,
        validate_user_props: bool = True,
    ) -> Dict[str, Any]:
        """Run user-property + (under schema) per-type validation.

        Args:
            validate_user_props: When ``True`` (default), run
                ``validate_user_properties``. When ``False`` (rehydration
                path), skip it. Schema-level checks always run.
        """
        if validate_user_props:
            props = validate_user_properties(properties, scope="node")
        else:
            props = dict(properties)
        if self.schema is not None:
            self.schema.require_node_type(type_name)
            self.schema.validate_node_properties(type_name, props)
        return props

    def _validated_edge_properties(
        self,
        type_name: str,
        properties: Mapping[str, Any],
        *,
        validate_user_props: bool = True,
    ) -> Dict[str, Any]:
        """Run user-property + (under schema) per-type validation."""
        if validate_user_props:
            props = validate_user_properties(properties, scope="edge")
        else:
            props = dict(properties)
        if self.schema is not None:
            self.schema.require_edge_type(type_name)
            self.schema.validate_edge_properties(type_name, props)
        return props

    def __repr__(self) -> str:
        schema_tag = " strict" if (self.schema and self.schema.strict) else (
            " schema" if self.schema is not None else ""
        )
        return (
            f"Graph(name={self.name!r}, role={self.role!r}, "
            f"nodes={len(self.nodes)}, edges={len(self.edges)}, "
            f"hyperedges={len(self.hyperedges)}{schema_tag})"
        )
