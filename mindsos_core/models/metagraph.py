"""The ``Metagraph`` primitive and its graph-level edges (Phase 05a slim port).

A ``Metagraph`` is a graph whose nodes are :class:`Graph` objects. It owns:

* A collection of contained ``Graph`` instances.
* ``MetaEdge`` — directed typed relationship between two contained graphs.
* ``MetaHyperEdge`` — n-ary typed relationship across two-or-more contained
  graphs.
* A namespaced property bag (ADR-0130).

The metagraph shares its :class:`IdentityRegistry` with every contained
graph (ADR-0020) so that no two elements anywhere in the metagraph can
share an id.

Phase 05a slim-port deferral list (kept for reference; ports phase-by-phase):

* ``Metagraph.add_xref`` / ``iter_xrefs`` / ``remove_xref`` (ADR-0128) — Phase 09.
* ``element_instances`` / ``composite_instances`` + ``instantiate_*`` /
  ``compose`` (ADR-0024 / ADR-0025) — Phase 06 (``mindsos_instances`` package).
* Soft-delete fields on ``MetaEdge`` / ``MetaHyperEdge`` (ADR-0133) — Phase 10
  (uniformly across all 4 edge variants per SOFT_DELETE_AUDIT_NOTE).
* ``RemovalImpact`` return + ``force=True`` flag + ``cascade=False`` semantics
  on ``remove_graph`` (ADR-0135) — Phase 10.
* ``mint_id`` (ADR-0131 helper) — Phase 05b (consumer = IntergraphEdge).
* ``CompositionalMetaEdge`` (ADR-0117) — DROPPED entirely (N3-D + P3 lock;
  ADR-0117 Withdrawn in 05a). Compositional concept moves to a flag on
  intergraph primitives in 05b/05c.
* Backward-compat aliases ``_kl_active_graph_ids`` / ``user_id`` (N1-A2) —
  re-added in Phase 14 / Phase 18 with their consumers.

Phase 05a ships exactly: ``__init__``, ``add_graph``, ``remove_graph``
(slim — no cascade param per P19), ``add_metaedge`` (graph_id strings per
P11), ``remove_metaedge``, ``add_metahyperedge`` (List[str] graph_ids per
P11), ``remove_metahyperedge``, ``iter_metaedges``, ``iter_metahyperedges``,
``update_metaedge_properties``, ``update_metahyperedge_properties``,
``__repr__``.

Locked round 1-4 design picks reflected here:

* **P1** — Soft-delete fields (``deprecated_at`` / ``disputed_at``) NOT shipped
  on ``MetaEdge`` / ``MetaHyperEdge``. Phase 10 lands them uniformly across
  all 4 edge variants.
* **P8** — ``MetaEdge`` and ``MetaHyperEdge`` use ``@dataclass(kw_only=True)``;
  field ordering does not matter; symmetry preserved.
* **P9** — ``MetaEdge`` and ``MetaHyperEdge`` ``__post_init__`` run cypher
  rel-type regex (ADR-0021) on ``type_name``.
* **P11** — Factories take ``source_graph_id: str`` / ``target_graph_id: str``
  / ``graph_ids: List[str]`` — NOT ``Graph`` objects. Internal lookup in
  ``self.graphs``. Persistence shape (graph names) is the source of truth;
  CLI translates name→graph_id at the boundary.
* **P15** — ``add_metaedge`` refuses ``source_graph_id == target_graph_id``
  (no self-loops). ``add_metahyperedge`` refuses ``len(graph_ids) < 2``
  (no degenerate 1-member n-ary). Both raise :class:`SchemaError`.
* **P16** — ``add_graph`` invariants: ``g.identity is self.identity`` after
  unification (shared reference, not clone); ``g.id_strategy`` is left
  untouched (graph keeps its own per-graph strategy; metagraph strategy
  applies to metagraph-level mints only).
* **P19** — ``remove_graph(graph_id)`` is single-behavior (always-cascade).
  No ``cascade`` parameter, no ``force`` parameter, no ``RemovalImpact``
  return. Phase 10 reintroduces the full ADR-0135 surface.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Optional

from ..cypher.identifiers import validate_edge_type_identifier
from ..exceptions import IdentityError, SchemaError
from ..schema.validation import validate_user_properties
from .graph import Graph
from .identity import IdentityRegistry, IdStrategy, UUID4Strategy, generate_uuid

_log = logging.getLogger(__name__)


# ── metagraph edges (P1 + P8 + P9) ───────────────────────────────────────────


@dataclass(kw_only=True)
class MetaEdge:
    """A directed, typed relationship between two contained ``Graph`` objects.

    Phase 05a slim shape (P1 — no soft-delete fields). Field ordering
    does not matter since ``kw_only=True`` (P8). ``__post_init__`` runs
    ADR-0021 cypher rel-type regex on ``type_name`` (P9).

    Attributes:
        source_graph_id: ``Graph.graph_id`` of the source graph
            (must be contained in the owning Metagraph).
        target_graph_id: ``Graph.graph_id`` of the target graph
            (must be contained AND ``!= source_graph_id`` per P15).
        type_name: Cypher rel-type (validated against ADR-0021 regex).
        label: Optional human-readable label.
        edge_id: Auto-minted UUID4 if not supplied.
        properties: Namespaced property bag; reserved-key-aware.
    """

    source_graph_id: str
    target_graph_id: str
    type_name: str
    label: Optional[str] = None
    edge_id: str = field(default_factory=generate_uuid)
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # P9 — cypher rel-type regex enforced at dataclass boundary so direct
        # construction (tests / fixtures / future rehydration) cannot bypass
        # the invariant. The factory ``Metagraph.add_metaedge`` ALSO validates
        # at the API boundary — both paths converge here.
        validate_edge_type_identifier(self.type_name)

    def __hash__(self) -> int:
        return hash(self.edge_id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, MetaEdge) and self.edge_id == other.edge_id

    def __repr__(self) -> str:
        return (
            f"MetaEdge({self.source_graph_id} -[{self.type_name}]-> "
            f"{self.target_graph_id}, id={self.edge_id[:8]})"
        )


@dataclass(kw_only=True)
class MetaHyperEdge:
    """An n-ary typed relationship across n ≥ 2 contained ``Graph`` objects.

    Phase 05a slim shape (P1 — no soft-delete fields, P8 — kw_only,
    P11 — graph_ids list of strings, P15 — refuses < 2 members).

    Attributes:
        graph_ids: List of contained-graph ids; n ≥ 2 enforced
            (P15: 1-member n-ary is degenerate). Stored as list (parent
            used Set, but persistence sorts deterministically by graph
            name and order doesn't carry semantic in 05a).
        type_name: Cypher rel-type (validated against ADR-0021 regex).
        label: Optional human-readable label.
        edge_id: Auto-minted UUID4 if not supplied.
        properties: Namespaced property bag; reserved-key-aware.
    """

    graph_ids: List[str]
    type_name: str
    label: Optional[str] = None
    edge_id: str = field(default_factory=generate_uuid)
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # P15 — minimum 2 members; 1-member n-ary is degenerate
        # (use no edge at all, or label the single graph directly).
        if len(self.graph_ids) < 2:
            raise SchemaError(
                f"MetaHyperEdge requires at least 2 member graphs; "
                f"got {len(self.graph_ids)}: {self.graph_ids!r}"
            )
        # Duplicate detection — same graph cannot appear twice.
        if len(set(self.graph_ids)) != len(self.graph_ids):
            raise SchemaError(
                f"MetaHyperEdge member graphs must be unique; "
                f"got duplicates in {self.graph_ids!r}"
            )
        # P9 — cypher rel-type regex enforced at dataclass boundary.
        validate_edge_type_identifier(self.type_name)

    def __hash__(self) -> int:
        return hash(self.edge_id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, MetaHyperEdge) and self.edge_id == other.edge_id

    def __repr__(self) -> str:
        return (
            f"MetaHyperEdge(type={self.type_name!r}, "
            f"graphs=[{', '.join(self.graph_ids)}], "
            f"id={self.edge_id[:8]})"
        )


# ── Metagraph ───────────────────────────────────────────────────────────────


class Metagraph:
    """Graph-of-graphs container with shared identity (Phase 05a slim port).

    Owns contained ``Graph`` instances, ``MetaEdge`` / ``MetaHyperEdge``
    relationships between them, and a namespaced property bag (ADR-0130).
    All contained objects share the metagraph's :class:`IdentityRegistry`
    (ADR-0020).

    Per P16 (round-3 lock): on ``add_graph(g)``,
        - ``g.identity is self.identity`` after unification (shared
          reference, not clone). Cached pre-unify ``g.identity``
          handles on the caller side become dangling — ADR-0138 INFO
          log surfaces this when the graph already had registered ids.
        - ``g.id_strategy`` is left UNTOUCHED. The metagraph's own
          ``id_strategy`` applies only to metagraph-level mints
          (defer to Phase 05b when ``mint_id`` is reintroduced for
          IntergraphEdge consumers). Per-graph strategies survive,
          so a metagraph can contain graphs with mixed id strategies
          (e.g., UUID4 for one, IRI-passthrough for another).
    """

    def __init__(
        self,
        name: str,
        *,
        identity: Optional[IdentityRegistry] = None,
        metagraph_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        id_strategy: Optional[IdStrategy] = None,
    ) -> None:
        """Create an empty metagraph.

        Args:
            name: Human-readable metagraph name.
            identity: Optional shared registry. ``None`` → fresh.
            metagraph_id: Optional explicit id (used during reconstruction).
                ``None`` → fresh UUID4.
            properties: Optional ADR-0130 property bag. Reserved-key-aware.
                ``None`` → empty.
            id_strategy: Optional :class:`IdStrategy`. Defaults to
                :class:`UUID4Strategy`. Per P16, this strategy applies
                ONLY to metagraph-level mints; contained graphs keep
                their own per-graph strategies.
        """
        self.metagraph_id: str = metagraph_id or generate_uuid()
        self.name: str = name
        self.identity: IdentityRegistry = identity or IdentityRegistry()
        # ADR-0131 — pluggable id strategy (slim consumer in 05b).
        self.id_strategy: IdStrategy = id_strategy or UUID4Strategy()

        # In-memory dicts keyed by id (matches parent shape). Persistence
        # uses graph NAMES (per spec); serialization layer translates.
        self.graphs: Dict[str, Graph] = {}
        self.metaedges: Dict[str, MetaEdge] = {}
        self.metahyperedges: Dict[str, MetaHyperEdge] = {}

        # ADR-0130 — namespaced metagraph property bag (N1-A1 lock).
        self.properties: Dict[str, Any] = validate_user_properties(
            properties or {}, scope="metagraph"
        )

        if metagraph_id is None:
            self.identity.register(self.metagraph_id)

    # ── graph membership ─────────────────────────────────────────────────

    def add_graph(self, graph: Graph) -> Graph:
        """Add a :class:`Graph` to this metagraph (P16 invariant locks).

        The graph's :class:`IdentityRegistry` is unified with the
        metagraph's registry. Every id the graph already owns is
        re-registered under the shared registry; collisions raise
        :class:`IdentityError`.

        Per ADR-0138 (§A2), an INFO log fires when a non-empty registry
        is unified — callers holding a cached pre-unify ``g.identity``
        reference will have a dangling handle, which is the heisenbug
        this surfacing prevents.

        Per P16:
            - Post-call invariant: ``graph.identity is self.identity``.
            - ``graph.id_strategy`` is NOT touched — the contained graph
              keeps whatever strategy it was created with. Mixed-strategy
              metagraphs are supported.
        """
        if graph.graph_id in self.graphs:
            raise IdentityError(
                f"Graph {graph.graph_id!r} already in metagraph {self.name!r}"
            )

        # Unify identity scopes.
        if graph.identity is not self.identity:
            existing_ids = list(graph.identity.ids)
            n_existing = len(existing_ids)
            # Q5-A — eager id-collision check BEFORE any mutation. If the
            # graph carries an id that conflicts with anything already in
            # the metagraph's registry, refuse the entire add atomically.
            for uid in existing_ids:
                if self.identity.contains(uid):
                    raise IdentityError(
                        f"Id collision when merging graph {graph.name!r} "
                        f"into metagraph {self.name!r}: {uid!r}"
                    )
            for uid in existing_ids:
                self.identity.register(uid)
            graph.identity = self.identity  # P16 — shared reference.
            if n_existing > 0:
                _log.info(
                    "Unifying identity registry of graph %r (%d entries) "
                    "into metagraph %r; cached g.identity references on the "
                    "caller side will be dangling.",
                    graph.graph_id, n_existing, self.metagraph_id,
                )

        self.graphs[graph.graph_id] = graph
        return graph

    def remove_graph(self, graph_id: str) -> None:
        """Remove a contained graph and cascade incident metaedges (P19 slim).

        Always cascades: every incident :class:`MetaEdge` and
        :class:`MetaHyperEdge` is removed first. No ``force`` flag, no
        ``RemovalImpact`` return, no ``cascade=False`` semantic — Phase
        10 reintroduces the full ADR-0135 surface.

        Raises:
            IdentityError: ``graph_id`` not contained in this metagraph.
        """
        if graph_id not in self.graphs:
            raise IdentityError(f"Unknown graph id: {graph_id!r}")

        # Cascade incident metaedges + metahyperedges.
        incident_meta = [
            eid for eid, me in self.metaedges.items()
            if me.source_graph_id == graph_id or me.target_graph_id == graph_id
        ]
        incident_mhe = [
            eid for eid, mhe in self.metahyperedges.items()
            if graph_id in mhe.graph_ids
        ]
        for eid in incident_meta:
            self.remove_metaedge(eid)
        for eid in incident_mhe:
            self.remove_metahyperedge(eid)

        # Unregister every id that belonged to this graph.
        graph = self.graphs[graph_id]
        owned_ids = {graph.graph_id}
        owned_ids.update(graph.nodes.keys())
        owned_ids.update(graph.edges.keys())
        owned_ids.update(graph.hyperedges.keys())
        for uid in owned_ids:
            self.identity.unregister(uid)
        del self.graphs[graph_id]

    # ── metaedges (P11 + P15) ────────────────────────────────────────────

    def add_metaedge(
        self,
        source_graph_id: str,
        target_graph_id: str,
        type_name: str,
        *,
        label: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> MetaEdge:
        """Create a directed graph-to-graph edge (P11 — id strings).

        Args:
            source_graph_id: ``graph_id`` of source (must be contained).
            target_graph_id: ``graph_id`` of target (must be contained AND
                ``!= source_graph_id`` per P15 — no self-loops).
            type_name: Cypher rel-type (ADR-0021 regex).
            label: Optional human-readable label.
            properties: Optional namespaced bag.

        Raises:
            IdentityError: source or target not contained.
            SchemaError: source == target (P15 self-loop refusal).
            CypherError: invalid type_name (via ``__post_init__``).
            PropertyShapeError: properties violate the contract.
        """
        if source_graph_id not in self.graphs:
            raise IdentityError(
                f"MetaEdge source {source_graph_id!r} not in metagraph "
                f"{self.name!r}"
            )
        if target_graph_id not in self.graphs:
            raise IdentityError(
                f"MetaEdge target {target_graph_id!r} not in metagraph "
                f"{self.name!r}"
            )
        # P15 — refuse self-loop. If Phase 14 KL ever wants graph-self
        # references, it relaxes this with explicit semantic.
        if source_graph_id == target_graph_id:
            raise SchemaError(
                f"MetaEdge self-loop refused (P15 lock): "
                f"source_graph_id == target_graph_id == {source_graph_id!r}"
            )
        props = validate_user_properties(properties or {}, scope="metaedge")
        me = MetaEdge(
            source_graph_id=source_graph_id,
            target_graph_id=target_graph_id,
            type_name=type_name,
            label=label,
            properties=props,
        )
        self.identity.register(me.edge_id)
        self.metaedges[me.edge_id] = me
        return me

    def remove_metaedge(self, edge_id: str) -> None:
        """Remove a metaedge by id."""
        if edge_id not in self.metaedges:
            raise IdentityError(f"Unknown metaedge id: {edge_id!r}")
        self.identity.unregister(edge_id)
        del self.metaedges[edge_id]

    def update_metaedge_properties(
        self,
        edge_id: str,
        properties: Dict[str, Any],
        *,
        replace: bool = False,
    ) -> MetaEdge:
        """Update a metaedge's property bag (parity with Phase 04 update_*_properties).

        Args:
            edge_id: target metaedge id.
            properties: bag to merge or replace.
            replace: when ``True``, swap entirely; when ``False``, merge.

        Returns:
            The mutated MetaEdge instance.

        Raises:
            IdentityError: unknown edge_id.
            PropertyShapeError: properties violate the contract.
        """
        if edge_id not in self.metaedges:
            raise IdentityError(f"Unknown metaedge id: {edge_id!r}")
        me = self.metaedges[edge_id]
        new_props = validate_user_properties(
            properties or {}, scope="metaedge"
        )
        if replace:
            me.properties = dict(new_props)
        else:
            me.properties = {**me.properties, **new_props}
        return me

    # ── metahyperedges (P11 + P15) ───────────────────────────────────────

    def add_metahyperedge(
        self,
        graph_ids: Iterable[str],
        *,
        type_name: str,
        label: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> MetaHyperEdge:
        """Create an n-ary graph-level hyperedge (P11 — id strings).

        Args:
            graph_ids: Iterable of contained-graph ids (n ≥ 2 per P15).
            type_name: Cypher rel-type (ADR-0021 regex).
            label: Optional label.
            properties: Optional namespaced bag.

        Raises:
            IdentityError: any member id not contained.
            SchemaError: ``len(graph_ids) < 2`` (P15) OR duplicates.
            CypherError: invalid type_name.
            PropertyShapeError: properties violate contract.
        """
        gid_list = list(graph_ids)
        for gid in gid_list:
            if gid not in self.graphs:
                raise IdentityError(
                    f"MetaHyperEdge member {gid!r} not in metagraph "
                    f"{self.name!r}"
                )
        props = validate_user_properties(properties or {}, scope="metahyperedge")
        mhe = MetaHyperEdge(
            graph_ids=gid_list,
            type_name=type_name,
            label=label,
            properties=props,
        )
        self.identity.register(mhe.edge_id)
        self.metahyperedges[mhe.edge_id] = mhe
        return mhe

    def remove_metahyperedge(self, edge_id: str) -> None:
        """Remove a metahyperedge by id."""
        if edge_id not in self.metahyperedges:
            raise IdentityError(f"Unknown metahyperedge id: {edge_id!r}")
        self.identity.unregister(edge_id)
        del self.metahyperedges[edge_id]

    def update_metahyperedge_properties(
        self,
        edge_id: str,
        properties: Dict[str, Any],
        *,
        replace: bool = False,
    ) -> MetaHyperEdge:
        """Update a metahyperedge's property bag."""
        if edge_id not in self.metahyperedges:
            raise IdentityError(f"Unknown metahyperedge id: {edge_id!r}")
        mhe = self.metahyperedges[edge_id]
        new_props = validate_user_properties(
            properties or {}, scope="metahyperedge"
        )
        if replace:
            mhe.properties = dict(new_props)
        else:
            mhe.properties = {**mhe.properties, **new_props}
        return mhe

    # ── iterators ────────────────────────────────────────────────────────

    def iter_metaedges(self) -> Iterator[MetaEdge]:
        """Yield every metaedge (no filtering in 05a; Phase 10 adds)."""
        return iter(self.metaedges.values())

    def iter_metahyperedges(self) -> Iterator[MetaHyperEdge]:
        """Yield every metahyperedge."""
        return iter(self.metahyperedges.values())

    # ── repr ────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"Metagraph(name={self.name!r}, "
            f"id={self.metagraph_id[:8]}, "
            f"graphs={len(self.graphs)}, "
            f"metaedges={len(self.metaedges)}, "
            f"metahyperedges={len(self.metahyperedges)})"
        )
