"""The ``Metagraph`` primitive — Phase 05a slim port + Phase 05b extensions.

A ``Metagraph`` is a graph whose nodes are :class:`Graph` objects. It owns:

* A collection of contained ``Graph`` instances.
* ``MetaEdge`` — directed typed relationship between two contained graphs (05a).
* ``MetaHyperEdge`` — n-ary typed relationship across two-or-more contained
  graphs (05a).
* ``IntergraphEdge`` — directed binary node↔node edge across two contained
  graphs (Phase 05b — ADR-0148 first draft).
* A namespaced property bag (ADR-0130, 05a N1-A1).
* Optional :class:`MetagraphSchema` attached by name reference (Phase 05b
  Pushback 11-A — schema reusable across N metagraphs; Pushback 12-A —
  one schema attached per metagraph at most; Pushback 32-D — re-attach is
  fresh validation, not silent no-op).

The metagraph shares its :class:`IdentityRegistry` with every contained
graph (ADR-0020) so that no two elements anywhere in the metagraph can
share an id.

Phase 05a slim-port deferral list (kept for reference; ports phase-by-phase):

* ``Metagraph.add_xref`` / ``iter_xrefs`` / ``remove_xref`` (ADR-0128) — Phase 09.
* ``element_instances`` / ``composite_instances`` + ``instantiate_*`` /
  ``compose`` (ADR-0024 / ADR-0025) — Phase 06 (``mindsos_instances`` package).
* Soft-delete fields on ``MetaEdge`` / ``MetaHyperEdge`` / ``IntergraphEdge``
  (ADR-0133) — Phase 10 (uniformly across all 4 edge variants per
  SOFT_DELETE_AUDIT_NOTE).
* ``RemovalImpact`` return + ``force=True`` flag + ``cascade=False`` semantics
  on ``remove_graph`` (ADR-0135) — Phase 10.
* ``CompositionalMetaEdge`` (ADR-0117) — DROPPED entirely (N3-D + P3 lock;
  ADR-0117 Withdrawn in 05a). Compositional concept moves to a flag on
  intergraph primitives (05b ships ``IntergraphEdge.compositional``;
  05c ships ``IntergraphHyperEdge.compositional``).
* Backward-compat aliases ``_kl_active_graph_ids`` / ``user_id`` (N1-A2) —
  re-added in Phase 14 / Phase 18 with their consumers.

Phase 05a ships exactly: ``__init__``, ``add_graph``, ``remove_graph``
(slim — no cascade param per P19), ``add_metaedge`` (graph_id strings per
P11), ``remove_metaedge``, ``add_metahyperedge`` (List[str] graph_ids per
P11), ``remove_metahyperedge``, ``iter_metaedges``, ``iter_metahyperedges``,
``update_metaedge_properties``, ``update_metahyperedge_properties``,
``__repr__``.

Phase 05b extensions (this row):

* ``Metagraph.add_intergraph_edge`` factory + 14-step validation order
  (Pushback 16-A).
* ``Metagraph.remove_intergraph_edge`` (refuses on compositional per
  design §4.3).
* ``Metagraph.update_intergraph_edge_properties`` (refuses on compositional).
* ``Metagraph.iter_intergraph_edges``.
* ``Metagraph.attach_schema(MS, *, schema_name)`` + ``detach_schema()``
  (Pushback 32-A; eager validation Pushback 7-A; atomic Pushback 29-A).
* ``Metagraph.mint_id(kind, content)`` — ADR-0131 helper (P7 carry-forward
  from 05a; IntergraphEdge factory's id-minting path; Pushback 14-A
  uniform).
* ``Metagraph.remove_graph`` cascade extended with the Pushback 17-A
  precheck pass for compositional intergraph_edges.

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
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    TYPE_CHECKING,
)

from .._observers import (
    ObserverHandle,
    RemoveCallback,
    _dispatch_precheck,
    _register,
)
from ..cypher.identifiers import validate_edge_type_identifier
from ..exceptions import (
    CompositionalImmutableError,
    IdentityError,
    PropertyShapeError,
    SchemaError,
    UnknownTypeError,
)
from ..schema.validation import validate_user_properties
from .graph import Graph
from .identity import IdentityRegistry, IdStrategy, UUID4Strategy, generate_uuid
from .intergraph_edge import IntergraphEdge
from .intergraph_hyperedge import IntergraphHyperEdge

if TYPE_CHECKING:
    from ..schema.metagraph_schema import MetagraphSchema

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

        # Phase 05b — IntergraphEdge storage (ADR-0148 first draft;
        # Pushback 1-C scope = binary only).
        self.intergraph_edges: Dict[str, IntergraphEdge] = {}

        # Phase 05c — IntergraphHyperEdge storage (ADR-0148 amended for
        # n-ary). Per P1-B, 05c ships the n-ary primitive and replace-only
        # update verb only; meta-vocabs (MetaEdgeType / MetaHyperEdgeType)
        # defer to 05d.
        self.intergraph_hyperedges: Dict[str, IntergraphHyperEdge] = {}

        # ADR-0130 — namespaced metagraph property bag (N1-A1 lock).
        self.properties: Dict[str, Any] = validate_user_properties(
            properties or {}, scope="metagraph"
        )

        # Phase 05b — MetagraphSchema attach state (Pushback 11-A: schema
        # reusable across N metagraphs by name reference; Pushback 12-A:
        # one attached at most). ``schema_name`` is the persisted
        # reference; ``schema`` is the in-memory cached instance set by
        # ``attach_schema`` and cleared by ``detach_schema``. Both default
        # to None (no schema attached).
        self.schema_name: Optional[str] = None
        self.schema: Optional["MetagraphSchema"] = None

        # Phase 06 (P31 A + round-7 P49 B + P65 A) — observer plumbing
        # for cascade-delete notification. Core ships plumbing only;
        # ``mindsos_instances.ElementRegistry`` subscribes on attach via
        # ``mindsos_instances.attach_registry(metagraph)``. Precheck-style
        # dispatch: callbacks fire BEFORE the underlying mutation; a
        # callback that raises aborts the remove cleanly.
        self._remove_observers: List[RemoveCallback] = []
        # Phase 06 round-7 P66 (implementation pushback): graphs added
        # AFTER ``attach_registry`` would otherwise miss the per-graph
        # remove-observer subscription. ``add_graph`` fires this list so
        # the registry can wire itself to newcomers.
        self._graph_added_observers: List[Callable[[Graph], None]] = []

        if metagraph_id is None:
            self.identity.register(self.metagraph_id)

    # ── observer plumbing (Phase 06 — P31 A + round-7 P49 B) ─────────────

    def register_remove_observer(
        self, callback: RemoveCallback
    ) -> ObserverHandle:
        """Subscribe ``callback`` to remove events on this metagraph.

        Returns an :class:`ObserverHandle` whose ``unsubscribe()`` method
        revokes the subscription. The callback is invoked with the id of
        the element about to be removed (``graph_id``, ``metaedge_id``,
        ``metahyperedge_id``, ``intergraph_edge_id``, or
        ``intergraph_hyperedge_id``) BEFORE the underlying mutation
        runs (precheck-style per round-7 P65 A).

        Phase 06 single consumer:
        :class:`mindsos_instances.ElementRegistry`. The registry
        examines the removed id for ``template_id`` matches on element
        instances (including ``GraphInstance`` and ``SubGraphInstance``
        when a contained ``Graph`` is removed) and for
        ``SubGraphInstance.node_ids/edge_ids`` membership when a node/
        edge inside a contained graph is removed (round-7 P59 A — the
        per-graph subscription handles those cases).
        """
        return _register(self._remove_observers, callback)

    def register_graph_added_observer(
        self, callback: Callable[[Graph], None]
    ) -> "ObserverHandle":
        """Subscribe ``callback`` to ``add_graph`` events.

        Phase 06 round-7 P66 — the registry uses this to wire a per-
        ``Graph`` remove-observer when a graph is added AFTER
        ``attach_registry`` was called. Callback receives the newly-
        added :class:`Graph` (post-unification per P16).
        """
        # Local import: ObserverHandle is already imported at module top.
        self._graph_added_observers.append(callback)
        return ObserverHandle(self._graph_added_observers, callback)

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
        # Phase 06 round-7 P66 — notify subscribed registries so they
        # can wire their per-Graph remove-observer to the newcomer.
        for cb in self._graph_added_observers:
            cb(graph)
        return graph

    def remove_graph(self, graph_id: str) -> None:
        """Remove a contained graph and cascade incident edges (P19 + Pushback 17-A + Phase 05c).

        Always cascades: every incident :class:`MetaEdge`,
        :class:`MetaHyperEdge`, :class:`IntergraphEdge`, AND
        :class:`IntergraphHyperEdge` is removed. Per Pushback 17-A
        (extended in Phase 05c per the smaller-items fold of the row),
        an atomic precheck pass runs BEFORE any mutation: walks BOTH
        ``self.intergraph_edges`` AND ``self.intergraph_hyperedges``;
        if any incident edge of either variant has
        ``compositional=True``, the entire ``remove_graph`` raises
        :class:`CompositionalImmutableError` with the offending edge_id
        AND ``edge_kind`` (``"intergraph_edge"`` /
        ``"intergraph_hyperedge"``) — no metaedges, metahyperedges, or
        intergraph_edges/intergraph_hyperedges are removed and the graph
        stays in the metagraph. Tester recovery is ``mindsos metagraph
        reset --name <MG> --force --yes`` per Pushback 6-A.

        No ``force`` flag, no ``RemovalImpact`` return, no
        ``cascade=False`` semantic — Phase 10 reintroduces the full
        ADR-0135 surface (which will likely add a force-bypass for the
        compositional check).

        Raises:
            IdentityError: ``graph_id`` not contained in this metagraph.
            CompositionalImmutableError: any incident
                :class:`IntergraphEdge` OR
                :class:`IntergraphHyperEdge` has
                ``compositional=True``. State unchanged. Error message
                names the offending edge_id AND edge_kind.
        """
        if graph_id not in self.graphs:
            raise IdentityError(f"Unknown graph id: {graph_id!r}")

        # Pushback 17-A (extended for Phase 05c) — atomic precheck for
        # compositional intergraph_edges AND intergraph_hyperedges. Walk
        # incident edges of both variants; refuse with the first
        # compositional incident BEFORE mutating anything.
        for ie in self.intergraph_edges.values():
            if (
                ie.source_graph_id == graph_id or ie.target_graph_id == graph_id
            ) and ie.compositional:
                raise CompositionalImmutableError(
                    f"Cannot remove graph {graph_id!r}: incident "
                    f"intergraph_edge {ie.edge_id} is compositional=True "
                    f"(edge_kind=intergraph_edge). Recovery: 'mindsos "
                    f"metagraph reset --name <MG> --force --yes' "
                    f"(Pushback 6-A)."
                )
        for ihe in self.intergraph_hyperedges.values():
            # An IntergraphHyperEdge is incident on graph_id if any anchor
            # OR member references the graph.
            if not ihe.compositional:
                continue
            for (gid, _node_id) in ihe.anchors:
                if gid == graph_id:
                    raise CompositionalImmutableError(
                        f"Cannot remove graph {graph_id!r}: incident "
                        f"intergraph_hyperedge {ihe.edge_id} is "
                        f"compositional=True "
                        f"(edge_kind=intergraph_hyperedge; anchor side). "
                        f"Recovery: 'mindsos metagraph reset --name <MG> "
                        f"--force --yes' (Pushback 6-A)."
                    )
            for (gid, _node_id) in ihe.members:
                if gid == graph_id:
                    raise CompositionalImmutableError(
                        f"Cannot remove graph {graph_id!r}: incident "
                        f"intergraph_hyperedge {ihe.edge_id} is "
                        f"compositional=True "
                        f"(edge_kind=intergraph_hyperedge; member side). "
                        f"Recovery: 'mindsos metagraph reset --name <MG> "
                        f"--force --yes' (Pushback 6-A)."
                    )

        # Phase 06 (P31 A + round-7 P65 A) — observer precheck for the
        # graph_id being removed. Fires AFTER compositional refusal but
        # BEFORE any cascade mutation. A subscribed
        # ``ElementRegistry`` examines the graph's contents and cascades
        # any referencing ``GraphInstance`` / ``SubGraphInstance`` /
        # element-level instance (round-7 P59 A handles the
        # node/edge/hyperedge contents reachability).
        _dispatch_precheck(self._remove_observers, graph_id)

        # Cascade incident metaedges + metahyperedges + intergraph_edges
        # + intergraph_hyperedges.
        incident_meta = [
            eid for eid, me in self.metaedges.items()
            if me.source_graph_id == graph_id or me.target_graph_id == graph_id
        ]
        incident_mhe = [
            eid for eid, mhe in self.metahyperedges.items()
            if graph_id in mhe.graph_ids
        ]
        incident_ie = [
            eid for eid, ie in self.intergraph_edges.items()
            if ie.source_graph_id == graph_id or ie.target_graph_id == graph_id
        ]
        incident_ihe = [
            eid for eid, ihe in self.intergraph_hyperedges.items()
            if any(
                gid == graph_id for (gid, _) in ihe.anchors
            )
            or any(gid == graph_id for (gid, _) in ihe.members)
        ]
        for eid in incident_meta:
            self.remove_metaedge(eid)
        for eid in incident_mhe:
            self.remove_metahyperedge(eid)
        # Note: incident_ie / incident_ihe at this point are guaranteed
        # non-compositional by the precheck above, so the per-edge
        # ``remove_*`` calls won't raise.
        for eid in incident_ie:
            self.remove_intergraph_edge(eid)
        for eid in incident_ihe:
            self.remove_intergraph_hyperedge(eid)

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
        # Phase 05d (round-7 P44 A) — validation order mirrors actual
        # 05b ``add_intergraph_edge`` precedent at metagraph.py:735-798:
        # containment → source≠target → properties bag → (if schema)
        # require_*_type → validate_* → validate_*_properties (strict
        # only) → register-and-construct (cypher regex via __post_init__).
        # Step 1-2 — graph existence.
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
        # Step 3 — P15 self-loop refusal.
        if source_graph_id == target_graph_id:
            raise SchemaError(
                f"MetaEdge self-loop refused (P15 lock): "
                f"source_graph_id == target_graph_id == {source_graph_id!r}"
            )
        # Step 4 — property bag validation (reserved-key + primitive scope).
        props = validate_user_properties(properties or {}, scope="metaedge")
        # Steps 5-7 — schema validation when attached. Per round-7 P39 A
        # the empty-MetaEdgeType-vocab + add_metaedge case raises
        # ``UnknownTypeError`` regardless of strict (preserves the
        # precedent asymmetry surfaced for IntergraphEdgeType in 05b);
        # operator workaround: detach → add → re-attach (eager-attach is
        # permissive on empty vocab + non-strict per attach_schema).
        if self.schema is not None:
            source_graph = self.graphs[source_graph_id]
            target_graph = self.graphs[target_graph_id]
            self.schema.require_meta_edge_type(type_name)
            self.schema.validate_meta_edge(
                type_name=type_name,
                source_graph_role=source_graph.role,
                target_graph_role=target_graph.role,
            )
            self.schema.validate_meta_edge_properties(type_name, props)
        # Step 8 — construct (cypher regex fires in __post_init__).
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
        """Remove a metaedge by id. Fires precheck remove-observers (Phase 06)."""
        if edge_id not in self.metaedges:
            raise IdentityError(f"Unknown metaedge id: {edge_id!r}")
        _dispatch_precheck(self._remove_observers, edge_id)
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
        # Phase 05d (round-7 P44 A) — validation order mirrors 05b
        # precedent: member containment → properties bag → (if schema)
        # require_*_type → validate_* → validate_*_properties (strict
        # only) → register-and-construct (n≥2 + uniqueness + cypher
        # regex via __post_init__).
        gid_list = list(graph_ids)
        for gid in gid_list:
            if gid not in self.graphs:
                raise IdentityError(
                    f"MetaHyperEdge member {gid!r} not in metagraph "
                    f"{self.name!r}"
                )
        props = validate_user_properties(properties or {}, scope="metahyperedge")
        if self.schema is not None:
            self.schema.require_meta_hyperedge_type(type_name)
            member_roles = [self.graphs[gid].role for gid in gid_list]
            self.schema.validate_meta_hyperedge(
                type_name=type_name,
                member_graph_roles=member_roles,
            )
            self.schema.validate_meta_hyperedge_properties(type_name, props)
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
        """Remove a metahyperedge by id. Fires precheck remove-observers (Phase 06)."""
        if edge_id not in self.metahyperedges:
            raise IdentityError(f"Unknown metahyperedge id: {edge_id!r}")
        _dispatch_precheck(self._remove_observers, edge_id)
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

    # ── intergraph edges (Phase 05b — ADR-0148; Pushbacks 14-A + 16-A + 17-A) ──

    def mint_id(
        self, kind: str, content: Optional[Dict[str, Any]] = None
    ) -> str:
        """ADR-0131 helper — mint an id via this metagraph's :class:`IdStrategy`.

        Phase 05b ports this from parent code (P7 carry-forward from 05a;
        consumer is the ``add_intergraph_edge`` factory). Per Pushback
        14-A, the IntergraphEdge factory ALWAYS uses this path,
        delegating to ``self.id_strategy.generate(kind, content)``.

        Default :class:`UUID4Strategy` ignores ``kind`` / ``content`` and
        returns a UUID4 string. Future strategies (IRIPassthrough,
        UUID5FromContent) may use ``kind`` (``"intergraph_edge"``,
        ``"metaedge"``, etc.) and ``content`` (a canonical content
        dict) to derive deterministic ids.

        Args:
            kind: short tag identifying what kind of element is being
                minted (e.g. ``"intergraph_edge"``).
            content: optional canonical content dict; ignored by
                UUID4Strategy.

        Returns:
            A new id string, NOT yet registered in ``self.identity``
            (the caller registers explicitly to keep mint and register
            decoupled — symmetric with parent code).
        """
        return self.id_strategy.generate(kind, content)

    def add_intergraph_edge(
        self,
        source_graph_id: str,
        source_node_id: str,
        target_graph_id: str,
        target_node_id: str,
        type_name: str,
        *,
        compositional: bool = False,
        label: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        edge_id: Optional[str] = None,
    ) -> IntergraphEdge:
        """Create a directed binary node↔node edge across contained graphs.

        Phase 05b primitive (ADR-0148). Implements the 14-step validation
        order locked in Pushback 16-A:

            1. ``source_graph_id`` must be in ``self.graphs``.
            2. ``target_graph_id`` must be in ``self.graphs``.
            3. ``source_graph_id != target_graph_id`` (use ``Graph.add_edge``
               for same-graph edges).
            4. ``source_node_id`` must exist in ``source_graph.nodes``
               (single check — Pushback 13-A; ADR-0020 unified registry
               makes the secondary ``mg.identity`` check redundant).
            5. ``target_node_id`` must exist in ``target_graph.nodes``.
            6. ``type_name`` cypher rel-type regex enforced at
               ``IntergraphEdge.__post_init__`` (P9 pattern).
            7. ``validate_user_properties`` — reserved-key + primitive-only.
            8. (if ``self.schema``) ``require_intergraph_edge_type(type_name)``.
            9. (if attached) ``validate_intergraph_edge`` — allowed_*_types
               + allowed_*_graphs (role-based per Pushback 4-A).
            10. (if attached and strict) ``validate_intergraph_edge_properties``.
            11. ``edge_id = mg.mint_id("intergraph_edge")`` (Pushback 14-A)
                or use caller-supplied ``edge_id`` if not None.
            12. Construct :class:`IntergraphEdge` (``__post_init__`` runs
                cypher regex; ``_initialized`` set for ``__setattr__``
                compositional immutability per Pushback 22-A).
            13. ``self.identity.register(edge_id)``.
            14. ``self.intergraph_edges[edge_id] = edge``. Return.

        Args:
            source_graph_id: source graph (must be contained,
                ``!= target_graph_id``).
            source_node_id: source node id (must exist in source graph).
            target_graph_id: target graph (must be contained).
            target_node_id: target node id (must exist in target graph).
            type_name: Cypher rel-type (ADR-0021 regex).
            compositional: identity-bearing flag (default ``False``;
                immutable post-create per Pushback 22-A).
            label: optional human-readable label.
            properties: optional namespaced bag.
            edge_id: optional caller-supplied id (for rehydration /
                deterministic ids in tests). When ``None``, mint via
                ``mg.mint_id``.

        Raises:
            IdentityError: source/target graph or node not found, or
                edge_id collides in identity registry.
            SchemaError: source == target.
            CypherError: invalid ``type_name`` (via ``__post_init__``).
            PropertyShapeError: properties violate the contract or fail
                strict-mode property typing.
            UnknownTypeError: schema attached but ``type_name`` not in
                vocab, or any allowed-* constraint violated.
        """
        # Step 1-2 — graph existence.
        if source_graph_id not in self.graphs:
            raise IdentityError(
                f"IntergraphEdge source graph {source_graph_id!r} not in "
                f"metagraph {self.name!r}"
            )
        if target_graph_id not in self.graphs:
            raise IdentityError(
                f"IntergraphEdge target graph {target_graph_id!r} not in "
                f"metagraph {self.name!r}"
            )
        # Step 3 — different graphs.
        if source_graph_id == target_graph_id:
            raise SchemaError(
                f"IntergraphEdge requires different source and target "
                f"graphs (use Graph.add_edge for same-graph edges); got "
                f"{source_graph_id!r} for both."
            )
        source_graph = self.graphs[source_graph_id]
        target_graph = self.graphs[target_graph_id]
        # Step 4-5 — node existence (Pushback 13-A — single check).
        if source_node_id not in source_graph.nodes:
            raise IdentityError(
                f"IntergraphEdge source node {source_node_id!r} not in "
                f"graph {source_graph.name!r}"
            )
        if target_node_id not in target_graph.nodes:
            raise IdentityError(
                f"IntergraphEdge target node {target_node_id!r} not in "
                f"graph {target_graph.name!r}"
            )
        # Step 7 — property bag validation (reserved keys + primitive).
        # NOTE: step 6 (cypher regex) runs at ``__post_init__`` after the
        # dataclass instantiation; we let it raise from there.
        props = validate_user_properties(
            properties or {}, scope="intergraph_edge"
        )
        # Step 8-10 — schema validation (only when attached).
        if self.schema is not None:
            # require_intergraph_edge_type raises UnknownTypeError if
            # the type is not registered.
            self.schema.require_intergraph_edge_type(type_name)
            source_node = source_graph.nodes[source_node_id]
            target_node = target_graph.nodes[target_node_id]
            self.schema.validate_intergraph_edge(
                type_name=type_name,
                source_node_type=source_node.type_name,
                target_node_type=target_node.type_name,
                source_graph_role=source_graph.role,
                target_graph_role=target_graph.role,
            )
            # Strict mode property-type check (Pushback 5-A early-returns
            # when not strict).
            self.schema.validate_intergraph_edge_properties(type_name, props)
        # Step 11 — mint or use caller-supplied id.
        if edge_id is None:
            edge_id = self.mint_id("intergraph_edge")
        # Step 12 — construct (cypher regex + initialised flag).
        edge = IntergraphEdge(
            source_graph_id=source_graph_id,
            source_node_id=source_node_id,
            target_graph_id=target_graph_id,
            target_node_id=target_node_id,
            type_name=type_name,
            compositional=compositional,
            edge_id=edge_id,
            label=label,
            properties=props,
        )
        # Step 13 — register in identity (raises IdentityError on collision).
        self.identity.register(edge.edge_id)
        # Step 14 — insert.
        self.intergraph_edges[edge.edge_id] = edge
        return edge

    def remove_intergraph_edge(self, edge_id: str) -> None:
        """Remove an intergraph edge by id; refuses on compositional.

        Per design §4.3 (Pushback 6-A — no escape hatch), removal is
        refused with :class:`CompositionalImmutableError` if the edge
        has ``compositional=True``. Tester recovery is metagraph reset.

        Raises:
            IdentityError: unknown ``edge_id``.
            CompositionalImmutableError: ``edge.compositional`` is True.
        """
        if edge_id not in self.intergraph_edges:
            raise IdentityError(f"Unknown intergraph edge id: {edge_id!r}")
        edge = self.intergraph_edges[edge_id]
        if edge.compositional:
            raise CompositionalImmutableError(
                f"Cannot remove IntergraphEdge {edge_id!r}: "
                f"compositional=True (design §4.3 + Pushback 6-A). "
                f"Recovery: 'mindsos metagraph reset --name <MG> "
                f"--force --yes' to wipe and rebuild."
            )
        _dispatch_precheck(self._remove_observers, edge_id)
        self.identity.unregister(edge_id)
        del self.intergraph_edges[edge_id]

    def update_intergraph_edge_properties(
        self,
        edge_id: str,
        properties: Dict[str, Any],
        *,
        replace: bool = False,
    ) -> IntergraphEdge:
        """Update an intergraph edge's property bag; refuses on compositional.

        Mirror of :meth:`update_metaedge_properties` semantics. Per
        design §4.3 + Pushback 6-A, mutation is refused on
        ``compositional=True`` edges.

        Args:
            edge_id: target edge.
            properties: bag to merge or replace.
            replace: when ``True``, swap entirely; when ``False``, merge.

        Raises:
            IdentityError: unknown ``edge_id``.
            CompositionalImmutableError: ``edge.compositional`` is True.
            PropertyShapeError: properties violate the contract.
        """
        if edge_id not in self.intergraph_edges:
            raise IdentityError(f"Unknown intergraph edge id: {edge_id!r}")
        edge = self.intergraph_edges[edge_id]
        if edge.compositional:
            raise CompositionalImmutableError(
                f"Cannot mutate properties on IntergraphEdge {edge_id!r}: "
                f"compositional=True (design §4.3 + Pushback 6-A)."
            )
        new_props = validate_user_properties(
            properties or {}, scope="intergraph_edge"
        )
        # If a schema is attached and strict, re-run property-type check
        # against the new bag (parity with what ``add_intergraph_edge``
        # would enforce).
        if self.schema is not None:
            self.schema.validate_intergraph_edge_properties(
                edge.type_name, new_props
            )
        if replace:
            edge.properties = dict(new_props)
        else:
            edge.properties = {**edge.properties, **new_props}
        return edge

    # ── intergraph hyperedges (Phase 05c — ADR-0148 amended; P14-A 16-step) ──

    def add_intergraph_hyperedge(
        self,
        anchors: Iterable[Tuple[str, str]],
        members: Iterable[Tuple[str, str]],
        type_name: str,
        *,
        compositional: bool = False,
        label: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        intergraph_hyperedge_id: Optional[str] = None,
    ) -> IntergraphHyperEdge:
        """Create an n-ary node↔node hyperedge across contained graphs (Phase 05c).

        Implements the locked 16-step validation order at PHASE_MAP §5
        Phase 05c row appendix §A (P14-A). Canonicalize-BEFORE-cardinality
        catches dedup-collapse-to-1-1 under ``ordered=False`` types.

        Validation order (factory perspective; ``__post_init__`` re-checks
        cypher regex + cardinality + overlap as belt-and-suspenders for
        direct-construction safety per P32):

            1. For each ``(graph_id, _)`` in anchors: graph_id must be
               in ``self.graphs`` → else IdentityError.
            2. Same for members → IdentityError.
            3. Node-existence per anchor (in source graph's nodes).
            4. Node-existence per member.
            5. Cypher rel-type regex on type_name (inline; ALSO at
               ``IntergraphHyperEdge.__post_init__`` per P32 belt-and-
               suspenders).
            6. (if schema attached) ``require_intergraph_hyperedge_type``
               → extracts ``type.ordered``. (P9-A no-schema default =
               ordered=True.)
            7. **Canonicalize** anchors + members per ``type.ordered``
               (sort+dedup if False; preserve insertion if True).
            8. **Cardinality check** on canonical: n≥1, m≥1, NOT 1-to-1.
               (P19-A: collapse to 1-1 under ordered=False refused
               here.)
            9. **Anchor-member overlap check** on canonical.
            10. **P8-A refusal**: compositional=True + ordered=False
                → SchemaError.
            11. ``validate_user_properties(scope="intergraph_hyperedge")``.
            12. (if attached) ``schema.validate_intergraph_hyperedge``.
            13. (if attached and strict)
                ``schema.validate_intergraph_hyperedge_properties``.
            14. Mint id (or use caller-supplied).
            15. Construct dataclass (``__post_init__`` re-checks).
            16. Register + insert.

        Args:
            anchors: iterable of ``(graph_id, node_id)`` pairs (n ≥ 1).
            members: iterable of ``(graph_id, node_id)`` pairs (m ≥ 1;
                NOT 1-1 with anchors).
            type_name: Cypher rel-type (ADR-0021 regex).
            compositional: identity-bearing flag (default False;
                immutable post-create per P2-refined).
            label: optional human-readable label (set-at-create only).
            properties: optional namespaced bag.
            intergraph_hyperedge_id: optional caller-supplied id (for
                rehydration / deterministic ids in tests). When None,
                mint via ``self.mint_id``.

        Raises:
            IdentityError: graph or node not found, or id collision.
            SchemaError: cardinality violation (1-1 / n=0 / m=0),
                anchor-member overlap, or compositional+ordered=False
                (P8-A).
            CypherError: invalid type_name.
            UnknownTypeError: schema attached but type_name not in vocab,
                or any allowed-* constraint violated.
            PropertyShapeError: properties violate the contract or fail
                strict-mode property typing.
        """
        # Normalize input to tuple-of-tuples up front so subsequent
        # validation steps can iterate without mutating callers' lists.
        anchors_t: Tuple[Tuple[str, str], ...] = tuple(
            (g, n) for (g, n) in anchors
        )
        members_t: Tuple[Tuple[str, str], ...] = tuple(
            (g, n) for (g, n) in members
        )

        # Step 1-2 — graph existence per anchor / member.
        for (gid, _) in anchors_t:
            if gid not in self.graphs:
                raise IdentityError(
                    f"IntergraphHyperEdge anchor graph {gid!r} not in "
                    f"metagraph {self.name!r}"
                )
        for (gid, _) in members_t:
            if gid not in self.graphs:
                raise IdentityError(
                    f"IntergraphHyperEdge member graph {gid!r} not in "
                    f"metagraph {self.name!r}"
                )
        # Step 3-4 — node existence per anchor / member.
        for (gid, nid) in anchors_t:
            graph = self.graphs[gid]
            if nid not in graph.nodes:
                raise IdentityError(
                    f"IntergraphHyperEdge anchor node {nid!r} not in "
                    f"graph {graph.name!r}"
                )
        for (gid, nid) in members_t:
            graph = self.graphs[gid]
            if nid not in graph.nodes:
                raise IdentityError(
                    f"IntergraphHyperEdge member node {nid!r} not in "
                    f"graph {graph.name!r}"
                )
        # Step 5 — cypher rel-type regex inline (P32 belt-and-suspenders;
        # ``__post_init__`` re-checks on construction for direct paths).
        validate_edge_type_identifier(type_name)

        # Step 6 — schema type-existence lookup; extract type.ordered.
        # Per P9-A, when no schema attached OR no type registered, treat
        # as ordered=True (permissive list semantics; no canonicalization).
        if self.schema is not None:
            iht = self.schema.require_intergraph_hyperedge_type(type_name)
            ordered = iht.ordered
        else:
            ordered = True

        # Step 7 — canonicalize anchors + members per type.ordered.
        # P5-refined: ordered=True preserves insertion order + duplicates;
        # ordered=False sorts lexicographically by (graph_id, node_id)
        # then dedups silently.
        if ordered:
            canon_anchors = anchors_t
            canon_members = members_t
        else:
            # Dedup while preserving sort order. Use sorted+dict.fromkeys
            # to dedup deterministically.
            canon_anchors = tuple(sorted(set(anchors_t)))
            canon_members = tuple(sorted(set(members_t)))

        # Step 8 — cardinality on canonical (P14-A: catches dedup-collapse).
        n = len(canon_anchors)
        m = len(canon_members)
        if n < 1:
            raise SchemaError(
                f"IntergraphHyperEdge requires at least 1 anchor; got 0"
            )
        if m < 1:
            raise SchemaError(
                f"IntergraphHyperEdge requires at least 1 member; got 0"
            )
        if n == 1 and m == 1:
            raise SchemaError(
                f"IntergraphHyperEdge is NOT 1-to-1 — use IntergraphEdge "
                f"for the binary 1-1 case. After canonicalization "
                f"(ordered={ordered}): n={n} anchors={list(canon_anchors)} "
                f"m={m} members={list(canon_members)}."
            )

        # Step 9 — anchor-member overlap forbidden on canonical.
        anchor_set = set(canon_anchors)
        member_set = set(canon_members)
        overlap = anchor_set & member_set
        if overlap:
            raise SchemaError(
                f"IntergraphHyperEdge anchor-member overlap forbidden: "
                f"{sorted(overlap)!r} appear(s) in both anchors and "
                f"members (post-canonicalization, ordered={ordered})."
            )

        # Step 10 — P8-A refusal: compositional=True + ordered=False.
        if compositional and not ordered:
            raise SchemaError(
                f"compositional hyperedges require ordered=True types "
                f"(P8-A): IntergraphHyperEdge type {type_name!r} has "
                f"ordered=False; refusing add. Either rebuild the type "
                f"with ordered=True OR call add_intergraph_hyperedge "
                f"with compositional=False."
            )

        # Step 11 — property bag validation (reserved + primitive).
        props = validate_user_properties(
            properties or {}, scope="intergraph_hyperedge"
        )

        # Step 12-13 — schema validators (only when attached). P5-A:
        # validate_*_properties early-returns when not strict.
        if self.schema is not None:
            anchor_node_types = [
                self.graphs[gid].nodes[nid].type_name
                for (gid, nid) in canon_anchors
            ]
            member_node_types = [
                self.graphs[gid].nodes[nid].type_name
                for (gid, nid) in canon_members
            ]
            anchor_graph_roles = [
                self.graphs[gid].role for (gid, _) in canon_anchors
            ]
            member_graph_roles = [
                self.graphs[gid].role for (gid, _) in canon_members
            ]
            self.schema.validate_intergraph_hyperedge(
                type_name=type_name,
                anchor_node_types=anchor_node_types,
                member_node_types=member_node_types,
                anchor_graph_roles=anchor_graph_roles,
                member_graph_roles=member_graph_roles,
            )
            self.schema.validate_intergraph_hyperedge_properties(
                type_name, props
            )

        # Step 14 — mint or use caller-supplied id.
        if intergraph_hyperedge_id is None:
            intergraph_hyperedge_id = self.mint_id("intergraph_hyperedge")

        # Step 15 — construct (cypher regex + cardinality + overlap +
        # tuple-conversion + ``_initialized`` set in ``__post_init__``).
        ihe = IntergraphHyperEdge(
            anchors=canon_anchors,
            members=canon_members,
            type_name=type_name,
            compositional=compositional,
            edge_id=intergraph_hyperedge_id,
            label=label,
            properties=props,
        )

        # Step 16 — register + insert.
        self.identity.register(ihe.edge_id)
        self.intergraph_hyperedges[ihe.edge_id] = ihe
        return ihe

    def remove_intergraph_hyperedge(
        self, intergraph_hyperedge_id: str
    ) -> None:
        """Remove an intergraph hyperedge by id; refuses on compositional.

        Per design §4.3 (P05b Pushback 6-A; carry-forward to 05c — no
        escape hatch), removal is refused with
        :class:`CompositionalImmutableError` if the hyperedge has
        ``compositional=True``. Tester recovery is metagraph reset.

        Raises:
            IdentityError: unknown id.
            CompositionalImmutableError: ``ihe.compositional`` is True.
        """
        if intergraph_hyperedge_id not in self.intergraph_hyperedges:
            raise IdentityError(
                f"Unknown intergraph hyperedge id: "
                f"{intergraph_hyperedge_id!r}"
            )
        ihe = self.intergraph_hyperedges[intergraph_hyperedge_id]
        if ihe.compositional:
            raise CompositionalImmutableError(
                f"Cannot remove IntergraphHyperEdge "
                f"{intergraph_hyperedge_id!r}: compositional=True "
                f"(design §4.3 + Pushback 6-A). Recovery: 'mindsos "
                f"metagraph reset --name <MG> --force --yes' to wipe "
                f"and rebuild."
            )
        _dispatch_precheck(
            self._remove_observers, intergraph_hyperedge_id
        )
        self.identity.unregister(intergraph_hyperedge_id)
        del self.intergraph_hyperedges[intergraph_hyperedge_id]

    def update_intergraph_hyperedge(
        self,
        intergraph_hyperedge_id: str,
        *,
        anchors: Optional[Iterable[Tuple[str, str]]] = None,
        members: Optional[Iterable[Tuple[str, str]]] = None,
        properties: Optional[Dict[str, Any]] = None,
        replace_properties: bool = False,
    ) -> IntergraphHyperEdge:
        """Replace-only structural update on an intergraph hyperedge (P10-C; Phase 05c).

        Per P10-C, this is a single combined factory + CLI verb covering
        anchors, members, and properties. Refuses if compositional=True
        (design §4.3 + Pushback 6-A). Re-runs the full 16-step validation
        on the resolved replacement values; atomic rollback on failure
        (no in-memory mutation). Any field passed as ``None`` retains the
        current value.

        Per P10-C ``replace_properties=False`` default: properties merge
        with existing (carry-forward of 05b
        :meth:`update_intergraph_edge_properties` precedent + the P28
        accept). With ``replace_properties=True``, properties is fully
        replaced.

        Per P19-A, refusal of update calls that would collapse to 1-to-1
        cardinality is enforced at the validation step 8 cardinality
        check on resolved replacement values. No in-place
        hyperedge→edge "downgrade".

        Per P20-A, update under detached schema validates structurally
        only (cardinality, overlap, regex; NO schema/role/property-type
        check). Subsequent re-attach surfaces drift per Push7-A.

        Args:
            intergraph_hyperedge_id: target hyperedge id.
            anchors: replacement anchors (or None to retain current).
            members: replacement members (or None to retain current).
            properties: new properties bag (or None to retain current).
            replace_properties: when True, swap entire properties dict;
                when False (default), merge with existing.

        Returns:
            The mutated :class:`IntergraphHyperEdge` instance (same id).

        Raises:
            IdentityError: unknown id.
            CompositionalImmutableError: ``ihe.compositional`` is True.
            SchemaError / CypherError / UnknownTypeError /
                PropertyShapeError: any validation step fails. State
                unchanged on raise.
        """
        if intergraph_hyperedge_id not in self.intergraph_hyperedges:
            raise IdentityError(
                f"Unknown intergraph hyperedge id: "
                f"{intergraph_hyperedge_id!r}"
            )
        ihe = self.intergraph_hyperedges[intergraph_hyperedge_id]
        if ihe.compositional:
            raise CompositionalImmutableError(
                f"Cannot update IntergraphHyperEdge "
                f"{intergraph_hyperedge_id!r}: compositional=True "
                f"(design §4.3 + Pushback 6-A). Recovery: 'mindsos "
                f"metagraph reset --name <MG> --force --yes' to wipe "
                f"and rebuild."
            )

        # Resolve replacement values (None = retain current).
        new_anchors_in: Tuple[Tuple[str, str], ...]
        new_members_in: Tuple[Tuple[str, str], ...]
        if anchors is None:
            new_anchors_in = ihe.anchors
        else:
            new_anchors_in = tuple((g, n) for (g, n) in anchors)
        if members is None:
            new_members_in = ihe.members
        else:
            new_members_in = tuple((g, n) for (g, n) in members)

        # Resolve properties: merge or replace.
        if properties is None:
            new_props_in = dict(ihe.properties)
        elif replace_properties:
            # User-supplied bag wins entirely; reserved-key check happens
            # at step 11.
            new_props_in = dict(properties)
        else:
            # Merge (mirror update_intergraph_edge_properties default).
            new_props_in = {**ihe.properties, **properties}

        # Steps 1-2 — graph existence per anchor / member.
        for (gid, _) in new_anchors_in:
            if gid not in self.graphs:
                raise IdentityError(
                    f"IntergraphHyperEdge update: anchor graph {gid!r} "
                    f"not in metagraph {self.name!r}"
                )
        for (gid, _) in new_members_in:
            if gid not in self.graphs:
                raise IdentityError(
                    f"IntergraphHyperEdge update: member graph {gid!r} "
                    f"not in metagraph {self.name!r}"
                )
        # Steps 3-4 — node existence.
        for (gid, nid) in new_anchors_in:
            if nid not in self.graphs[gid].nodes:
                raise IdentityError(
                    f"IntergraphHyperEdge update: anchor node {nid!r} "
                    f"not in graph {self.graphs[gid].name!r}"
                )
        for (gid, nid) in new_members_in:
            if nid not in self.graphs[gid].nodes:
                raise IdentityError(
                    f"IntergraphHyperEdge update: member node {nid!r} "
                    f"not in graph {self.graphs[gid].name!r}"
                )
        # Step 5 — cypher regex on existing type_name (set-at-create;
        # update doesn't change it but defense-in-depth re-validates).
        validate_edge_type_identifier(ihe.type_name)
        # Step 6 — schema type lookup + extract ordered. Per P20-A,
        # detached schema → structural-only; ordered=True default.
        if self.schema is not None:
            iht = self.schema.require_intergraph_hyperedge_type(
                ihe.type_name
            )
            ordered = iht.ordered
        else:
            ordered = True
        # Step 7 — canonicalize.
        if ordered:
            canon_anchors = new_anchors_in
            canon_members = new_members_in
        else:
            canon_anchors = tuple(sorted(set(new_anchors_in)))
            canon_members = tuple(sorted(set(new_members_in)))
        # Step 8 — cardinality (P19-A: collapse to 1-1 refused here).
        n = len(canon_anchors)
        m = len(canon_members)
        if n < 1:
            raise SchemaError(
                f"IntergraphHyperEdge update: requires at least 1 "
                f"anchor; got 0"
            )
        if m < 1:
            raise SchemaError(
                f"IntergraphHyperEdge update: requires at least 1 "
                f"member; got 0"
            )
        if n == 1 and m == 1:
            raise SchemaError(
                f"IntergraphHyperEdge update would collapse to 1-to-1 "
                f"cardinality (P19-A refusal). After canonicalization "
                f"(ordered={ordered}): n={n} m={m}. No in-place "
                f"hyperedge→edge downgrade in 05c — recovery is "
                f"remove_intergraph_hyperedge + add_intergraph_edge "
                f"(loses edge_id stability across the type boundary; "
                f"future-work entry filed)."
            )
        # Step 9 — anchor-member overlap.
        anchor_set = set(canon_anchors)
        member_set = set(canon_members)
        overlap = anchor_set & member_set
        if overlap:
            raise SchemaError(
                f"IntergraphHyperEdge update: anchor-member overlap "
                f"forbidden: {sorted(overlap)!r} appear(s) in both "
                f"sides (post-canonicalization, ordered={ordered})."
            )
        # Step 10 — P8-A refusal (compositional=True + ordered=False).
        # ihe.compositional is False here (the early refusal above
        # rejects compositional updates), but defense-in-depth.
        if ihe.compositional and not ordered:
            raise SchemaError(
                f"IntergraphHyperEdge update: compositional+ordered=False "
                f"refused (P8-A)."
            )
        # Step 11 — property bag validation.
        new_props = validate_user_properties(
            new_props_in, scope="intergraph_hyperedge"
        )
        # Step 12-13 — schema validators (only when attached; P20-A).
        if self.schema is not None:
            anchor_node_types = [
                self.graphs[gid].nodes[nid].type_name
                for (gid, nid) in canon_anchors
            ]
            member_node_types = [
                self.graphs[gid].nodes[nid].type_name
                for (gid, nid) in canon_members
            ]
            anchor_graph_roles = [
                self.graphs[gid].role for (gid, _) in canon_anchors
            ]
            member_graph_roles = [
                self.graphs[gid].role for (gid, _) in canon_members
            ]
            self.schema.validate_intergraph_hyperedge(
                type_name=ihe.type_name,
                anchor_node_types=anchor_node_types,
                member_node_types=member_node_types,
                anchor_graph_roles=anchor_graph_roles,
                member_graph_roles=member_graph_roles,
            )
            self.schema.validate_intergraph_hyperedge_properties(
                ihe.type_name, new_props
            )

        # All validation passed. Skip step 14 (mint id — update keeps
        # the existing edge_id) and step 16 (register/insert — already
        # in identity + dict).
        # Step 15 modified — replace tuple/dict in-place via
        # ``object.__setattr__`` to bypass ``__setattr__`` gate (P27 A
        # set-via-factory contract).
        object.__setattr__(ihe, "anchors", canon_anchors)
        object.__setattr__(ihe, "members", canon_members)
        object.__setattr__(ihe, "properties", new_props)
        return ihe

    def iter_intergraph_hyperedges(self) -> Iterator[IntergraphHyperEdge]:
        """Yield every intergraph hyperedge (no filtering in 05c; Phase 10 adds)."""
        return iter(self.intergraph_hyperedges.values())

    # ── iterators ────────────────────────────────────────────────────────

    def iter_metaedges(self) -> Iterator[MetaEdge]:
        """Yield every metaedge (no filtering in 05a; Phase 10 adds)."""
        return iter(self.metaedges.values())

    def iter_metahyperedges(self) -> Iterator[MetaHyperEdge]:
        """Yield every metahyperedge."""
        return iter(self.metahyperedges.values())

    def iter_intergraph_edges(self) -> Iterator[IntergraphEdge]:
        """Yield every intergraph edge (no filtering in 05b; Phase 10 adds)."""
        return iter(self.intergraph_edges.values())

    # ── schema attach/detach (Phase 05b — Pushbacks 7-A, 12-A, 29-A, 32-A/D) ──

    def attach_schema(
        self, schema: "MetagraphSchema", *, schema_name: str
    ) -> "MetagraphSchema":
        """Attach a :class:`MetagraphSchema` and eagerly validate intergraph_edges.

        Per Pushback 32-A, this method takes the schema instance plus
        the ``schema_name`` keyword (basename — Phase 04 precedent for
        schemas being basename-keyed on disk). Per Pushback 32-D, calling
        ``attach_schema`` while the SAME schema_name is already attached
        runs a fresh eager validation (NOT a silent no-op) — schema
        mutation drift since previous attach surfaces here.

        Per Pushback 12-A, attaching while a *different* schema is
        attached refuses with :class:`IdentityError` ("detach first").

        Per Pushback 7-A + 9-A + 29-A, the eager validation walks every
        existing :class:`IntergraphEdge` in this metagraph and runs the
        full schema check (type-existence + role/name + property typing
        if strict). On first violation: raises with offending edge_id;
        no mutation to ``self.schema`` or ``self.schema_name``. On
        all-pass: ``self.schema = schema`` + ``self.schema_name =
        schema_name``.

        Phase 05d (round-7 P39 A) extends the walk to metaedges +
        metahyperedges, with the empty-vocab pass-silently precedent
        carrying forward. Push9-A (from 05b) expires here: the schema
        now covers all four vocabularies.

        Per Pushback 24-hybrid (extended uniformly to all four vocabs in
        05d): when a vocab dict is empty AND ``schema.strict`` is False,
        the corresponding walk is skipped (existing primitives are
        grandfathered through the migration window). When a vocab dict
        is empty AND ``schema.strict`` is True, the walk runs and every
        existing primitive fails (its ``type_name`` is not in the empty
        vocab). When a vocab dict is non-empty, every primitive MUST
        resolve through it regardless of strict.

        Args:
            schema: the schema instance (loaded by CLI from
                ``metagraph-schema-<name>.json`` or constructed in-tests).
            schema_name: basename of the schema state file; persisted in
                metagraph state file v=2 as ``schema_name`` field.

        Returns:
            The attached schema instance (for chaining).

        Raises:
            IdentityError: a different schema is already attached.
            UnknownTypeError: any existing intergraph_edge violates the
                new schema (type-existence or constraint).
            PropertyShapeError: strict-mode property-type violation on
                an existing intergraph_edge.
        """
        # Pushback 12-A — refuse if a *different* schema is attached.
        # Re-attach with same schema_name is allowed and runs fresh
        # validation (Pushback 32-D).
        if self.schema_name is not None and self.schema_name != schema_name:
            raise IdentityError(
                f"Metagraph {self.name!r} already has schema "
                f"{self.schema_name!r} attached; use "
                f"'mindsos metagraph detach-schema --name {self.name}' "
                f"first (Pushback 12-A)."
            )
        # Pushback 7-A + 29-A — atomic precheck: walk all intergraph_edges,
        # validate each. First violation → raise; state unchanged.
        for edge in self.intergraph_edges.values():
            source_graph = self.graphs[edge.source_graph_id]
            target_graph = self.graphs[edge.target_graph_id]
            source_node = source_graph.nodes[edge.source_node_id]
            target_node = target_graph.nodes[edge.target_node_id]
            # require_intergraph_edge_type raises UnknownTypeError if
            # type missing.
            schema.require_intergraph_edge_type(edge.type_name)
            schema.validate_intergraph_edge(
                type_name=edge.type_name,
                source_node_type=source_node.type_name,
                target_node_type=target_node.type_name,
                source_graph_role=source_graph.role,
                target_graph_role=target_graph.role,
            )
            schema.validate_intergraph_edge_properties(
                edge.type_name, edge.properties
            )
        # Phase 05c P6-A — extend eager-attach to walk
        # ``intergraph_hyperedges`` IN ADDITION to ``intergraph_edges``
        # (which 05b already walked above). Phase 05d (round-7 P39 A)
        # additionally walks metaedges + metahyperedges; Push9-A from
        # 05b expires here.
        #
        # Per Push7-A eager-validation contract, re-attach with a schema
        # whose ``IntergraphHyperEdgeType.ordered`` setting conflicts with
        # an existing hyperedge's canonical state surfaces here as a
        # subtle drift case. The hyperedge stores already-canonicalized
        # data (factory step 7); the schema's ``ordered`` flag determines
        # whether the validator's allowed-* checks fire on the canonical
        # state. Today both ordered=True and ordered=False produce
        # canonical state that this validator examines uniformly via the
        # iterables — there is no "ordered=True data fails an ordered=False
        # type" structural mismatch at validate time. The drift surfaces
        # downstream when a tester adds a NEW hyperedge under a
        # newly-flipped ordered flag (factory step 7 produces different
        # canonical data than what's persisted). 05c row Risks documents.
        for ihe in self.intergraph_hyperedges.values():
            # require_intergraph_hyperedge_type raises UnknownTypeError
            # if type missing.
            schema.require_intergraph_hyperedge_type(ihe.type_name)
            anchor_node_types = [
                self.graphs[gid].nodes[nid].type_name
                for (gid, nid) in ihe.anchors
            ]
            member_node_types = [
                self.graphs[gid].nodes[nid].type_name
                for (gid, nid) in ihe.members
            ]
            anchor_graph_roles = [
                self.graphs[gid].role for (gid, _) in ihe.anchors
            ]
            member_graph_roles = [
                self.graphs[gid].role for (gid, _) in ihe.members
            ]
            schema.validate_intergraph_hyperedge(
                type_name=ihe.type_name,
                anchor_node_types=anchor_node_types,
                member_node_types=member_node_types,
                anchor_graph_roles=anchor_graph_roles,
                member_graph_roles=member_graph_roles,
            )
            schema.validate_intergraph_hyperedge_properties(
                ihe.type_name, ihe.properties
            )
        # Phase 05d (round-7 P39 A) — empty-vocab pass-silently rule
        # (mirrors 05b/05c "Pushback 24-hybrid" precedent for
        # IntergraphEdgeType): if the corresponding meta-vocab is empty
        # AND ``schema.strict`` is False, skip the walk entirely (existing
        # metaedges grandfathered through the migration window). If the
        # vocab is empty under strict mode, fall through to the walk —
        # ``require_meta_*_type`` will raise on every existing primitive
        # (matches 05b/05c precedent for IntergraphEdgeType).
        # If the vocab is non-empty, every metaedge / metahyperedge
        # MUST resolve through it.
        if schema._meta_edge_types or schema.strict:
            for me in self.metaedges.values():
                schema.require_meta_edge_type(me.type_name)
                source_graph = self.graphs[me.source_graph_id]
                target_graph = self.graphs[me.target_graph_id]
                schema.validate_meta_edge(
                    type_name=me.type_name,
                    source_graph_role=source_graph.role,
                    target_graph_role=target_graph.role,
                )
                schema.validate_meta_edge_properties(
                    me.type_name, me.properties
                )
        if schema._meta_hyperedge_types or schema.strict:
            for mhe in self.metahyperedges.values():
                schema.require_meta_hyperedge_type(mhe.type_name)
                member_roles = [
                    self.graphs[gid].role for gid in mhe.graph_ids
                ]
                schema.validate_meta_hyperedge(
                    type_name=mhe.type_name,
                    member_graph_roles=member_roles,
                )
                schema.validate_meta_hyperedge_properties(
                    mhe.type_name, mhe.properties
                )
        # All-pass — commit attachment in memory.
        self.schema = schema
        self.schema_name = schema_name
        return schema

    def detach_schema(self) -> Optional[str]:
        """Detach the currently-attached :class:`MetagraphSchema` (if any).

        Per Pushback 26-A, detach is non-destructive: data unchanged;
        ``self.schema_name`` cleared to ``None``; ``self.schema`` cleared.
        Subsequent ``add_intergraph_edge`` runs without schema validation.

        Returns:
            The previous ``schema_name`` (or ``None`` if no schema was
            attached).
        """
        previous = self.schema_name
        self.schema = None
        self.schema_name = None
        return previous

    # ── repr ────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"Metagraph(name={self.name!r}, "
            f"id={self.metagraph_id[:8]}, "
            f"graphs={len(self.graphs)}, "
            f"metaedges={len(self.metaedges)}, "
            f"metahyperedges={len(self.metahyperedges)}, "
            f"intergraph_edges={len(self.intergraph_edges)}, "
            f"intergraph_hyperedges={len(self.intergraph_hyperedges)}"
            f"{', schema=' + repr(self.schema_name) if self.schema_name else ''})"
        )
