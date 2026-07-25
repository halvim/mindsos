"""ElementRegistry + idempotent attach helper (Phase 06 row §C + §F).

Per-metagraph in-memory registry holding live :class:`ElementInstance`
and :class:`CompositeInstance` objects. The registry subscribes to the
metagraph's Core-side remove observers and cascades dependent instances
when a template is removed (Phase 06 §F + round-7 P49 B + P56 A +
P59 A + P65 A).

Phase 06 ships in-memory only (P4 B + P8 B). ``InstanceRepository`` +
``InstanceLoader`` (persistence) are deferred to Phase 07; the
``MetagraphLoader.register_attach_handler`` extension point is deferred
to Phase 08.
"""

from __future__ import annotations

from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Set,
    Union,
)

from mindsos_core import Metagraph
from mindsos_core._observers import ObserverHandle

from .models.element_instance import (
    CompositeInstance,
    ElementInstance,
    GraphInstance,
    SubGraphInstance,
)

#: Type alias — anything the registry holds.
RegistryEntry = Union[ElementInstance, CompositeInstance]


def _remap_value(value: Any, id_map: Mapping[str, str]) -> Any:
    """Substitute any string in ``value`` that is a key of ``id_map`` with its
    mapped value, recursing through list/tuple/set/frozenset. Used to reid
    id-bearing override values (e.g. an IntergraphEdgeInstance's graph ids)
    after the parent metagraph regenerated its ids. Non-id strings and other
    scalars pass through unchanged."""
    if isinstance(value, str):
        return id_map.get(value, value)
    if isinstance(value, frozenset):
        return frozenset(_remap_value(v, id_map) for v in value)
    if isinstance(value, (list, tuple, set)):
        return type(value)(_remap_value(v, id_map) for v in value)
    return value


class ElementRegistry:
    """In-memory per-metagraph registry of element + composite instances.

    Created via :func:`attach_registry` (idempotent helper). Stored on
    the metagraph as ``mg.element_registry`` after first attach.

    The registry subscribes to the metagraph's Core-side remove
    observers and cascades instances per the rules in Phase 06 row §F.
    See module docstring for cascade order.
    """

    def __init__(self, metagraph: Metagraph) -> None:
        self.metagraph: Metagraph = metagraph
        self._instances: Dict[str, RegistryEntry] = {}
        #: Per-template monotonic counter used for instance-ID
        #: derivation (round-7 P46 C disambiguator).
        self._template_seq: Dict[str, int] = {}
        #: Subscription handles — kept so the registry can unsubscribe
        #: if a future API exposes teardown. Phase 06 expects lifecycle
        #: to follow Python ownership (P35 A); no explicit teardown
        #: tests exist (round-7 P52 A strikes the test category).
        self._subscription_handles: List[ObserverHandle] = []

        # Subscribe to metagraph-level remove events (graph,
        # metaedge, metahyperedge, intergraph_edge,
        # intergraph_hyperedge).
        self._subscription_handles.append(
            metagraph.register_remove_observer(self._on_metagraph_remove)
        )
        # Subscribe to per-graph remove events for every currently
        # contained graph. New graphs added after attach also get
        # subscribed via the ``register_graph_added_observer`` hook
        # (round-7 P66 — closes the late-added-graph regression).
        for graph in metagraph.graphs.values():
            self._subscribe_to_graph(graph)
        self._subscription_handles.append(
            metagraph.register_graph_added_observer(self._subscribe_to_graph)
        )

    # ── public API (Phase 06 row §C) ──────────────────────────────────────

    def add(self, instance: RegistryEntry) -> None:
        """Register ``instance``. Also registers its id in
        ``mg.identity`` (P11 A shared registry)."""
        if instance.id in self._instances:
            from mindsos_core.exceptions import IdentityError

            raise IdentityError(
                f"ElementRegistry.add: duplicate instance id "
                f"{instance.id!r}"
            )
        self.metagraph.identity.register(instance.id)
        self._instances[instance.id] = instance

    def get(self, instance_id: str) -> RegistryEntry:
        """Look up an instance by id; raises ``IdentityError`` if
        unknown."""
        if instance_id not in self._instances:
            from mindsos_core.exceptions import IdentityError

            raise IdentityError(
                f"ElementRegistry.get: unknown instance id "
                f"{instance_id!r}"
            )
        return self._instances[instance_id]

    def remove(self, instance_id: str) -> None:
        """Remove an instance; fire recursive cascade through
        composites containing it; also unregister from
        ``mg.identity`` (round-7 P56 A)."""
        if instance_id not in self._instances:
            return
        instance = self._instances[instance_id]
        del self._instances[instance_id]
        # Round-7 P56 A — also unregister from the shared identity
        # registry to close the leak surfaced during round-7 review.
        self.metagraph.identity.unregister(instance_id)

        # P44 A — recursive cascade through composites containing this
        # instance. Collect composites first so we don't mutate during
        # iteration.
        to_remove: List[str] = []
        for cid, entry in self._instances.items():
            if isinstance(entry, CompositeInstance):
                if any(m.id == instance_id for m in entry.members):
                    to_remove.append(cid)
        for cid in to_remove:
            self.remove(cid)

    def iter(
        self, kind: Optional[str] = None
    ) -> Iterator[RegistryEntry]:
        """Iterate registered instances. ``kind=None`` returns all
        (element instances + composites)."""
        for entry in self._instances.values():
            if kind is None:
                yield entry
            else:
                entry_kind = type(entry).KIND  # ClassVar
                if entry_kind == kind:
                    yield entry

    def __contains__(self, instance_id: object) -> bool:
        return isinstance(instance_id, str) and instance_id in self._instances

    def __len__(self) -> int:
        return len(self._instances)

    # ── fork independence (ADR-0201 / CR#4 Slice 1) ──────────────────────

    def remap_ids(self, id_map: Mapping[str, str]) -> None:
        """Reid every held instance after the parent metagraph regenerated
        its ids (fork independence). Rewrites each instance's ``metagraph_id``
        and any ``template_id`` / override value that is a regenerated id (a
        key of ``id_map``). Instance ids themselves are NOT remapped — node /
        instance ids are not regenerated, so they stay valid in the fork.

        No-op when ``id_map`` is empty. ``object.__setattr__`` is used for the
        structural fields because ``ElementInstance`` enforces post-init
        immutability on them (P27)."""
        if not id_map:
            return
        for inst in self._instances.values():
            mg = getattr(inst, "metagraph_id", None)
            if isinstance(mg, str) and mg in id_map:
                object.__setattr__(inst, "metagraph_id", id_map[mg])
            tid = getattr(inst, "template_id", None)
            if isinstance(tid, str) and tid in id_map:
                object.__setattr__(inst, "template_id", id_map[tid])
            overrides = getattr(inst, "overrides", None)
            if isinstance(overrides, dict):
                for key, val in list(overrides.items()):
                    overrides[key] = _remap_value(val, id_map)

    # ── private helpers (Phase 06 row §C — P46 C, P55 A, P59 A) ──────────

    def _next_seq_for(self, template_id: str) -> int:
        """Round-7 P46 C — per-template monotonic counter used as the
        instance-ID disambiguator. Counter increments on each call."""
        cur = self._template_seq.get(template_id, 0)
        nxt = cur + 1
        self._template_seq[template_id] = nxt
        return nxt

    def _mint_instance_id(
        self, template_id: str, instance_seq: int
    ) -> str:
        """Derive a stable instance id via the metagraph's pluggable
        id_strategy (round-7 P46 C — overrides not in content)."""
        return self.metagraph.id_strategy.generate(
            "instance",
            content={
                "template_id": template_id,
                "instance_seq": instance_seq,
            },
        )

    def _subscribe_to_graph(self, graph: Any) -> None:
        """Subscribe to a contained Graph's remove events."""
        handle = graph.register_remove_observer(
            lambda removed_id, graph=graph: self._on_graph_remove(
                graph, removed_id
            )
        )
        self._subscription_handles.append(handle)

    # ── observer callbacks (precheck-style per round-7 P65 A) ────────────

    def _on_metagraph_remove(self, removed_id: str) -> None:
        """Metagraph-level remove event handler.

        The removed id may be a contained ``Graph.graph_id``, a
        ``MetaEdge.edge_id``, a ``MetaHyperEdge.edge_id``, an
        ``IntergraphEdge.edge_id``, or an
        ``IntergraphHyperEdge.edge_id``. We don't know which without
        consulting the metagraph; the cascade strategy handles all
        cases uniformly (match by ``template_id`` and — for graph
        removal — additionally walk the graph's contents per
        round-7 P59 A).
        """
        # Per round-7 P65 A precheck semantics, this callback fires
        # BEFORE the Core mutation. The removed entity is still
        # reachable in the metagraph at this point. If it's a graph,
        # walk its contents and cascade SubGraphInstances + element
        # instances referencing those contents.
        if removed_id in self.metagraph.graphs:
            graph = self.metagraph.graphs[removed_id]
            # Cascade element-level instances whose template lives
            # inside this graph (NodeInstance / EdgeInstance /
            # HyperEdgeInstance). Plus any SubGraphInstance whose
            # template_id is the about-to-be-removed graph.
            inner_ids: Set[str] = set(graph.nodes.keys())
            inner_ids.update(graph.edges.keys())
            inner_ids.update(graph.hyperedges.keys())
            for inner_id in inner_ids:
                self._cascade_referencing_id(inner_id)
        # Cascade by template_id match (covers GraphInstance,
        # SubGraphInstance, MetaEdgeInstance, MetaHyperEdgeInstance,
        # and any element-level instance whose template was the
        # outer object — when removed_id is itself an instance
        # template).
        self._cascade_referencing_id(removed_id)

    def _on_graph_remove(self, graph: Any, removed_id: str) -> None:
        """Per-graph remove event handler (precheck-style).

        Cascade element-level instances (NodeInstance / EdgeInstance /
        HyperEdgeInstance) whose ``template_id == removed_id``. Also
        route through any SubGraphInstance whose ``node_ids`` or
        ``edge_ids`` contains ``removed_id`` (round-7 P59 A — closes
        the stale-reference bug-class).
        """
        self._cascade_referencing_id(removed_id)

    def _cascade_referencing_id(self, removed_id: str) -> None:
        """Cascade every instance that references ``removed_id`` via
        ``template_id`` OR ``SubGraphInstance.node_ids/edge_ids``
        (round-7 P59 A)."""
        to_remove: List[str] = []
        for entry_id, entry in self._instances.items():
            # template_id match (covers element instances + GraphInstance
            # + SubGraphInstance whose template is the removed entity).
            tid: Optional[str] = getattr(entry, "template_id", None)
            if tid == removed_id:
                to_remove.append(entry_id)
                continue
            # SubGraphInstance referenced-element routing (round-7 P59 A).
            if isinstance(entry, SubGraphInstance):
                ovr = entry.overrides
                if removed_id in ovr.get("node_ids", frozenset()):
                    to_remove.append(entry_id)
                    continue
                if removed_id in ovr.get("edge_ids", frozenset()):
                    to_remove.append(entry_id)
                    continue
        for rid in to_remove:
            self.remove(rid)


# ── idempotent attach helper (round-7 P49 A) ────────────────────────────────


def attach_registry(metagraph: Metagraph) -> ElementRegistry:
    """Construct (or return the existing) ``ElementRegistry`` for
    ``metagraph``. Idempotent — subsequent calls return the same
    registry object.

    The registry is stored on the metagraph as ``mg.element_registry``
    after first attach. Core does NOT import ``mindsos_instances``;
    this attach helper is the boundary-preserving caller-facing entry
    point (round-7 P49 B + A).

    Phase 07 extension (M9 + P96 A) — on first attach, subscribes a
    persist-observer that routes sibling-side instance persistence
    through :class:`mindsos_instances.persistence.InstanceRepository`.
    The observer reads ``mg._persist_client`` to obtain the Client
    instance at fire time (set by the caller of
    ``MetagraphRepository.persist`` before invoking; ``None`` means
    no-op — pure in-memory ``persist`` calls don't trigger DB writes).

    Phase 08 extension (PB-4 A + RR-9 A) — on first attach, ALSO
    subscribes an after-load observer that routes sibling-side
    reconstruction through
    :class:`mindsos_instances.reconstruction.InstanceLoader`. The
    observer reads ``mg._persist_client`` (transiently set by
    :meth:`mindsos_core.reconstruction.MetagraphLoader.load` during
    the locked R4-1 A sequence) to obtain the Client instance.
    Per-observer exception isolation lives inside
    :func:`mindsos_core._observers._dispatch_after_load` (RR-9 A) so
    a failing rehydration does NOT tear down the Core load.

    Idempotent: re-attach does not double-subscribe.
    """
    existing = getattr(metagraph, "element_registry", None)
    if isinstance(existing, ElementRegistry):
        return existing
    registry = ElementRegistry(metagraph)
    # ``Metagraph`` is a plain class (not __slots__-locked); attribute
    # assignment is permitted.
    metagraph.element_registry = registry  # type: ignore[attr-defined]

    # Phase 07 — persist observer wiring. Lives behind a `getattr`
    # guard so older Metagraph instances (pre-Phase-07) without the
    # ``register_persist_observer`` method don't crash on import.
    register_persist = getattr(metagraph, "register_persist_observer", None)
    if callable(register_persist):
        def _on_persist(mg: Metagraph) -> None:
            client = getattr(mg, "_persist_client", None)
            if client is None:
                return  # No DB binding; pure in-memory persist — no-op.
            from .persistence import InstanceRepository

            InstanceRepository(client).persist_all(registry)

        register_persist(_on_persist)

    # Phase 08 — after-load observer wiring (PB-4 A). Same getattr-guard
    # pattern as Phase 07 so pre-Phase-08 Metagraph instances don't
    # crash on import / attach. The observer routes sibling-side
    # reconstruction through ``InstanceLoader.load_into(mg)``.
    register_after_load = getattr(
        metagraph, "register_after_load_observer", None
    )
    if callable(register_after_load):
        def _on_after_load(mg: Metagraph) -> None:
            client = getattr(mg, "_persist_client", None)
            if client is None:
                return  # No DB binding; pure in-memory load — no-op.
            # Local import keeps the boundary clean (Core does not
            # import ``mindsos_instances``; this module sits in
            # ``mindsos_instances`` so the import is allowed).
            from .reconstruction.instance_loader import InstanceLoader

            InstanceLoader(client).load_into(mg)

        register_after_load(_on_after_load)

    return registry
