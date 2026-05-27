"""The ``CapacityLayer`` facade — top-level L3 API.

Owns:

- One Global L3 Metagraph (shared across users; ships with the system).
- N Local L3 Metagraphs (one per active user), created lazily.
- The per-metagraph capacity index (IRI → (Node, Graph)).
- The cross-metagraph declaration registry (IRI → Python declaration).

This class is **in-memory first**, mirroring
:class:`mindsos_knowledge.KnowledgeLayer`. Persistence adapters
(FalkorDB) live separately.

**Phase 28 substrate (R0 PB-3 lock).** Ships the registration,
look-up, constraint, and capability-gate surface.

**Phase 29 additions.** Auto-discovery hooks wire
:func:`discover_for_capacity` at the end of :meth:`register_capacity`
and :func:`discover_for_datastate` at the end of
:meth:`register_datastate`. Adds :meth:`rediscover` (drop auto edges
+ recompute from scratch). Raises :class:`DiscoveryFailedError` (sub
of :class:`CapacityRegistrationError`) when an auto-discovery write
fails mid-registration; partial-write state is observable by callers
(R2 PB-27 pick (b)).

**Phase 30 additions.** Ships :meth:`invoke` (reactive invocation;
ADR-0072 envelope) + ``self.problem_trace`` (per-layer
:class:`ProblemTraceSink`; ADR-0074). Lifts
:class:`InvocationResult` + :func:`call_capacity` exports via package
``__init__.py``.

**Phase 31 additions.** Ships the resident lifecycle methods
(:meth:`start_resident` / :meth:`stop_resident` /
:meth:`active_subscriptions`) backed by a per-layer
``self._subscriptions`` dict. Residents are descriptive per ADR-0073
— L3 builds the :class:`ResidentSubscription` handle and exposes
:meth:`on_signal` / :meth:`emit`; L4's event loop dispatches. ADR-0073
§amendment-1 records halvim divergences: (1) per-layer registry (not
module-level dict — closes the ADR-0073 §Cost row); (2) ``subscribes_to``
kwarg dropped (declaration is source of truth); (3)
``ResidentSubscription`` is ``eq=False`` (handle semantics);
(4) wrong-type raises ``ResidentError`` (not
``CapacityRegistrationError``).

Deferred to later phases:

- Cross-graph constraints — Phase 30+ (only same-category in v1; see
  :class:`ConstraintViolationError`).
- Additional-graph memberships per ADR-0085 — deferred to first
  consumer (Phase 33).
- Admin-authored TYPE_COMPAT API (``add_type_compat``) — Phase 30+
  (Phase 29 admins author via direct ``Graph.add_edge`` per
  ADR-0086 §Implementation).
- Bulk rediscover across all metagraphs — Phase 30+ (first admin
  caller).

The class always takes ``session: Optional[SessionProtocol]`` per
ADR-0080 bootstrap carve-out: ``None`` is the pre-server admin path; a
real :class:`Session` (typically ``mindsos_server.session.Session``) is
the production path. No legacy ``user_id=`` kw is supported (halvim
divergence from parent layout per R1 PB-14 lock — halvim has zero such
callers).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Mapping, Optional, Tuple

from mindsos_core import Edge, Graph, Metagraph, Node

if TYPE_CHECKING:
    # Phase 34 (R1 PB-C): TYPE_CHECKING guard avoids any circular-import
    # risk for the CapacityLayer.kl= constructor param. Runtime accepts
    # any object; missing-KL at write-capacity invoke surfaces as
    # ``RuntimeError`` from the body per R3 PB-F.
    from mindsos_knowledge import KnowledgeLayer

from .bootstrap import (
    create_global,
    create_local,
    ensure_category_graph,
    ensure_datastate_graph,
)
from .capabilities import CAN_WRITE_GLOBAL
from .capacity import InvocationResult, Monitor, _CapacityBase
from .datastate import DataState, validate_datastate
from .discovery import (
    discover_for_capacity,
    discover_for_datastate,
    rediscover_all,
)
from .exceptions import (
    CapacityRegistrationError,
    ConstraintViolationError,
    DiscoveryFailedError,
    ResidentError,
)
from .runtime import (
    ProblemTraceSink,
    ResidentSubscription,
    invoke as _runtime_invoke,
)
from .identifiers import (
    CONSTRAINT_KINDS,
    EDGE_CONSTRAINT,
    REF_GLOBAL_CAPACITY,
    REF_TYPE_KEY,
    REF_TYPES,
    RESERVED_PROPERTY_KEYS,
)
from .types import SessionArg, SessionProtocol
from .views import CapacityLayerView


class CapacityLayer:
    """Top-level façade over Global + per-user Local L3 metagraphs."""

    def __init__(
        self,
        *,
        global_metagraph: Optional[Metagraph] = None,
        strict: bool = False,
        categories: Optional[Iterable[str]] = None,
        kl: Optional["KnowledgeLayer"] = None,
    ) -> None:
        """Construct a Capacity Layer.

        Args:
            global_metagraph: Pre-built Global Metagraph (e.g. loaded
                from FalkorDB by a future
                ``bootstrap_capacity_from_falkordb`` helper). If
                ``None``, a fresh empty one is built by
                :func:`create_global`.
            strict: Schema strict-mode flag for lazily-created Local
                graphs.
            categories: Functional categories to bootstrap when
                constructing a fresh Global. Ignored when
                ``global_metagraph`` is supplied.
            kl: Phase 34 (R0 PB-5 + R1 PB-C) — :class:`KnowledgeLayer`
                reference for write-capacity bodies. When provided,
                :meth:`invoke` + :meth:`start_resident` inject the KL
                into capacity context under key ``"kl"``. ``None``
                (legacy default) — write-capacity invocations will
                raise :class:`RuntimeError` from the body when they
                try ``context["kl"]``. Read capacities ignore.
        """
        if global_metagraph is None:
            kwargs: Dict[str, Any] = {"strict": strict}
            if categories is not None:
                kwargs["categories"] = categories
            self._global: Metagraph = create_global(**kwargs)
        else:
            self._global = global_metagraph
        self._locals: Dict[str, Metagraph] = {}
        self._strict = strict
        self._kl: Optional["KnowledgeLayer"] = kl

        self._capacity_index: Dict[str, Dict[str, Tuple[Node, Graph]]] = {
            self._global.metagraph_id: {},
        }
        self._declarations: Dict[str, _CapacityBase] = {}

        # Phase 30 — single in-memory ProblemTraceSink per layer instance
        # (ADR-0074 §Implementation). Multi-tenant scoping is L4's
        # concern (R2 PB-29(a) lock; payload-side ``user_id`` provenance).
        self.problem_trace: ProblemTraceSink = ProblemTraceSink()

        # Phase 31 — per-layer resident subscription registry (ADR-0073
        # §amendment-1 clause 1; closes the ADR-0073 §Cost row "module-
        # level dict's sharing across layer instances flagged ... as a
        # test-hygiene hazard"). Accessed via :meth:`start_resident` /
        # :meth:`stop_resident` / :meth:`active_subscriptions` ONLY.
        self._subscriptions: Dict[str, ResidentSubscription] = {}

    def global_metagraph(self) -> Metagraph:
        return self._global

    def global_view(self) -> CapacityLayerView:
        return CapacityLayerView(self._global)

    def local_metagraph(self, user_id: str) -> Metagraph:
        """Return (creating lazily) the Local Metagraph for ``user_id``.

        Atomically initializes the per-Local ``_capacity_index`` entry
        (R3 PB-23 invariant: every metagraph in ``_locals`` MUST have
        an index entry).
        """
        mg = self._locals.get(user_id)
        if mg is None:
            mg = create_local(user_id, strict=self._strict)
            self._locals[user_id] = mg
            self._capacity_index[mg.metagraph_id] = {}
        return mg

    def local_view(self, user_id: str) -> CapacityLayerView:
        return CapacityLayerView(self.local_metagraph(user_id))

    def register_datastate(
        self,
        datastate: DataState,
        *,
        session: SessionArg = None,
    ) -> Node:
        """Create the Core DataState node for ``datastate``.

        Target scope:

        * ``session is not None`` → Local metagraph of ``session.user_id``.
          Provenance stamp ``created_by`` set to ``session.user_id``.
        * ``session is None`` → Global metagraph (ADR-0080 bootstrap
          carve-out; no stamp).

        Raises:
            DataStateError: ``datastate`` shape is malformed
                (propagated from :func:`validate_datastate`).
            CapacityRegistrationError: ``datastate.iri`` already
                registered in the target DataState graph.
            PermissionError: ``session`` lacks ``CAN_WRITE_GLOBAL``
                when the write targets Global.
        """
        target_uid = session.user_id if session is not None else None
        if target_uid is None:
            self._enforce_global_write(session, op="register_datastate")

        validate_datastate(datastate)
        mg = self._metagraph_for(target_uid)
        ds_graph = ensure_datastate_graph(mg, strict=self._strict)
        if datastate.iri in ds_graph.nodes:
            raise CapacityRegistrationError(
                f"DataState {datastate.iri!r} already registered in "
                f"metagraph {mg.name!r}"
            )
        props = datastate.to_properties()
        props["node_kind"] = "datastate"
        if session is not None:
            props["created_by"] = session.user_id
        node = ds_graph.add_node(
            value=datastate.name,
            type_name="DataState",
            properties=props,
            node_id=datastate.iri,
        )

        # Phase 29 — discovery hook. Under the current Phase 28-29
        # forward-ref restriction (_CapacityBase.validate_for_registration
        # forbids unregistered DataStates in inputs/outputs), this
        # trigger emits zero edges at v1. Shipped for parent parity +
        # future-scope per R1 PB-15 lock.
        try:
            discover_for_datastate(
                mg,
                datastate.iri,
                capacity_index=self._capacity_index[mg.metagraph_id],
            )
        except Exception as exc:
            raise DiscoveryFailedError(
                f"discover_for_datastate raised after register_datastate "
                f"for {datastate.iri!r}: {exc}"
            ) from exc
        return node

    def register_capacity(
        self,
        declaration: _CapacityBase,
        *,
        session: SessionArg = None,
        ref_to_global: Optional[str] = None,
        ref_type: Optional[str] = None,
        extra_properties: Optional[Mapping[str, Any]] = None,
    ) -> Node:
        """Register a Capacity / Monitor / Adapter.

        Raises:
            CapacityRegistrationError: declaration is not
                ``_CapacityBase``-derived, IRI duplicate, IRI collides
                with existing node id, unknown DataState in inputs/outputs,
                reserved property key in extras, ref-type invariants
                violated.
            PermissionError: ``session`` lacks ``CAN_WRITE_GLOBAL`` when
                writing to Global.
        """
        if not isinstance(declaration, _CapacityBase):
            raise CapacityRegistrationError(
                f"Expected a Capacity/Monitor/Adapter, got "
                f"{type(declaration).__name__}"
            )
        target_uid = session.user_id if session is not None else None
        if target_uid is None:
            self._enforce_global_write(session, op="register_capacity")

        mg = self._metagraph_for(target_uid)
        index = self._capacity_index[mg.metagraph_id]

        ds_graph = ensure_datastate_graph(mg, strict=self._strict)
        declaration.validate_for_registration(ds_graph.nodes.keys())

        self._validate_ref_invariants(ref_to_global, ref_type, user_id=target_uid)

        props: Dict[str, Any] = declaration.to_properties()
        if extra_properties:
            for k in extra_properties:
                if k in RESERVED_PROPERTY_KEYS:
                    raise CapacityRegistrationError(
                        f"Reserved property key {k!r} may not be supplied "
                        "in extra_properties"
                    )
            props.update(dict(extra_properties))
        if ref_to_global is not None:
            if ref_to_global not in self._capacity_index[self._global.metagraph_id]:
                raise CapacityRegistrationError(
                    f"ref_to_global={ref_to_global!r} does not resolve to a "
                    "registered Global capacity"
                )
            props[REF_GLOBAL_CAPACITY] = ref_to_global
            props[REF_TYPE_KEY] = ref_type
        if session is not None:
            props["created_by"] = session.user_id

        category_graph = ensure_category_graph(
            mg, declaration.category, strict=self._strict
        )
        if declaration.iri in index:
            raise CapacityRegistrationError(
                f"Capacity {declaration.iri!r} already registered"
            )
        if declaration.iri in category_graph.nodes:
            raise CapacityRegistrationError(
                f"Capacity IRI collides with existing node id in graph "
                f"{category_graph.role!r}"
            )
        node_type = declaration.node_type
        node = category_graph.add_node(
            value=declaration.name,
            type_name=node_type,
            properties=props,
            node_id=declaration.iri,
        )
        index[declaration.iri] = (node, category_graph)
        self._declarations[declaration.iri] = declaration

        # Phase 29 — auto-discover TYPE_COMPAT edges (ADR-0069 + ADR-0086).
        # Invocation ordering per R2 PB-24: index[] + _declarations[]
        # are set BEFORE discovery, so discover_for_capacity walks the
        # full index and excludes self via node_id comparison.
        try:
            discover_for_capacity(
                mg,
                node,
                category_graph,
                capacity_index=index,
            )
        except Exception as exc:
            raise DiscoveryFailedError(
                f"discover_for_capacity raised after register_capacity "
                f"for {declaration.iri!r}: {exc}"
            ) from exc
        return node

    def add_constraint(
        self,
        source_iri: str,
        target_iri: str,
        kind: str,
        *,
        session: SessionArg = None,
        note: Optional[str] = None,
        rate_limit: Optional[int] = None,
    ) -> Edge:
        """Add an admin-authored CONSTRAINT edge between two capacities.

        Raises:
            ConstraintViolationError: unknown ``kind``, missing endpoint,
                or cross-category endpoints.
            PermissionError: session present but lacks
                ``CAN_WRITE_GLOBAL`` when writing to Global.
        """
        if kind not in CONSTRAINT_KINDS:
            raise ConstraintViolationError(
                f"Unknown constraint kind {kind!r}; expected one of "
                f"{sorted(CONSTRAINT_KINDS)}"
            )
        target_uid = session.user_id if session is not None else None
        if target_uid is None:
            self._enforce_global_write(session, op="add_constraint")

        mg = self._metagraph_for(target_uid)
        index = self._capacity_index[mg.metagraph_id]
        try:
            source_node, source_graph = index[source_iri]
            target_node, target_graph = index[target_iri]
        except KeyError as exc:
            raise ConstraintViolationError(
                f"Constraint endpoints must be registered; missing {exc.args[0]!r}"
            ) from exc
        if source_graph.graph_id != target_graph.graph_id:
            raise ConstraintViolationError(
                "Cross-category constraints are not supported in the "
                "Phase 28 vertical slice; both endpoints must share a "
                "category graph"
            )
        props: Dict[str, Any] = {"constraint_kind": kind}
        if note:
            props["note"] = note
        if rate_limit is not None:
            props["rate_limit"] = int(rate_limit)
        if session is not None:
            props["created_by"] = session.user_id
        return source_graph.add_edge(
            source_node, target_node, EDGE_CONSTRAINT, properties=props
        )

    def iter_constraints(
        self,
        *,
        session: SessionArg = None,
    ) -> List[Edge]:
        """Return every CONSTRAINT edge in the target metagraph."""
        target_uid = session.user_id if session is not None else None
        mg = self._metagraph_for(target_uid)
        out: List[Edge] = []
        for g in mg.graphs.values():
            for e in g.edges.values():
                if e.type_name == EDGE_CONSTRAINT:
                    out.append(e)
        return out

    def get_declaration(self, capacity_iri: str) -> _CapacityBase:
        """Return the Python declaration registered for ``capacity_iri``."""
        try:
            return self._declarations[capacity_iri]
        except KeyError as exc:
            raise CapacityRegistrationError(
                f"No declaration registered for {capacity_iri!r}"
            ) from exc

    def iter_declarations(self) -> List[_CapacityBase]:
        """Return every registered declaration (Local + Global)."""
        return list(self._declarations.values())

    def rediscover(
        self,
        *,
        session: SessionArg = None,
    ) -> List[object]:
        """Drop auto-discovered TYPE_COMPAT edges + recompute from scratch.

        Manual edges (no ``discovered_automatically=True`` flag) are
        preserved per ADR-0086.

        Target scope:

        * ``session is not None`` → Local metagraph of ``session.user_id``;
          no capability gate (the user owns their Local).
        * ``session is None`` → Global metagraph; gated on
          ``CAN_WRITE_GLOBAL`` per ADR-0078 + ADR-0080.

        **Open gap (deferred):** if an admin DELETES an auto edge,
        the next ``rediscover`` re-adds it. See ADR-0086 §Implementation
        (Phase 29). Resolution deferred to first reported foot-gun.

        Raises:
            PermissionError: ``session`` lacks ``CAN_WRITE_GLOBAL`` when
                rediscover targets Global.
            DiscoveryFailedError: a write inside ``rediscover_all``
                raised mid-emit.

        Returns:
            The list of ``Edge`` / ``MetaEdge`` objects re-created.
        """
        target_uid = session.user_id if session is not None else None
        if target_uid is None:
            self._enforce_global_write(session, op="rediscover")
        mg = self._metagraph_for(target_uid)
        try:
            return rediscover_all(
                mg, capacity_index=self._capacity_index[mg.metagraph_id]
            )
        except Exception as exc:
            raise DiscoveryFailedError(
                f"rediscover_all raised for metagraph {mg.name!r}: {exc}"
            ) from exc

    # ── Phase 30 — invocation surface (ADR-0072) ──────────────────────

    def invoke(
        self,
        capacity_iri: str,
        inputs: Mapping[str, Any],
        *,
        session: SessionArg = None,
        context: Optional[Mapping[str, Any]] = None,
        task_id: Optional[str] = None,
        step_id: Optional[str] = None,
    ) -> InvocationResult:
        """Run the Python implementation bound to ``capacity_iri``.

        Looks the declaration up by IRI; Local metagraph (when a
        session is supplied) wins over Global on a collision (mirrors
        :func:`KL`'s specialisation rule per ADR-0061). On exception
        from the bound implementation, a problem-trace record is
        emitted to ``self.problem_trace`` (when ``task_id`` is also
        supplied) and ``InvocationResult(success=False, error=exc)``
        is returned. ADR-0072 §amendment-1 fixes the field rename.

        When a session is supplied, the session's ``user_id`` is
        injected into ``context['session_user_id']`` and
        ``context['session_id']`` for provenance-stamping capacities.
        Caller-set keys are never overwritten.

        Args:
            capacity_iri: The IRI to resolve.
            inputs: Mapping of input-DataState IRI → concrete value.
            session: Optional bearer of capability + user identity.
                ``None`` resolves against Global only (no Local lookup).
            context: Optional auxiliary mapping passed through to the
                callable.
            task_id: Optional L4 task identifier — required for problem-
                trace emission. ``None`` silently skips trace on
                exception (the envelope is still returned).
            step_id: Optional L4 step identifier — propagated into
                the trace record when emission occurs.

        Raises:
            CapacityRegistrationError: ``capacity_iri`` is not
                registered. Raised (not enveloped) per ADR-0072
                §Decision's "L3 raises for its own invariants" carve-out.

        Returns:
            :class:`InvocationResult` envelope; ``success=True`` on
            success, ``success=False`` with ``error`` set on
            implementation exception.
        """
        target_uid = session.user_id if session is not None else None
        declaration = self._resolve_declaration(
            capacity_iri, user_id=target_uid
        )
        ctx: Optional[Dict[str, Any]] = None
        if session is not None:
            ctx = dict(context) if context else {}
            ctx.setdefault("session_user_id", session.user_id)
            ctx.setdefault("session_id", session.session_id)
            # Phase 33 (ADR-0146 §amendment-1 clause 2): inject Session
            # object so write-capacity bodies can call ``session.has(cap)``
            # for capability gating. Read capacities ignore the key;
            # backward-compatible with Phase 30 + 31 ctx assertions
            # (which use ``in`` / ``not in`` membership, not exclusivity).
            ctx.setdefault("session", session)
        else:
            ctx = dict(context) if context else None
        # Phase 34 (R0 PB-5 + R5 PB-B): conditional KL injection. Only
        # write capacities consume ``context["kl"]``; reads ignore. When
        # ``self._kl is None`` (legacy CapacityLayer construction), the
        # key is NOT injected — capacity bodies see ``None`` from
        # ``context.get("kl")`` and raise ``RuntimeError`` per R3 PB-F.
        if self._kl is not None:
            if ctx is None:
                ctx = {}
            ctx.setdefault("kl", self._kl)
        return _runtime_invoke(
            declaration,
            inputs,
            context=ctx,
            task_id=task_id,
            step_id=step_id,
            problem_trace_sink=self.problem_trace,
        )

    # ── Phase 31 — resident lifecycle (ADR-0073 §amendment-1) ─────────

    def start_resident(
        self,
        capacity_iri: str,
        *,
        session: SessionArg = None,
        context: Optional[Mapping[str, Any]] = None,
    ) -> ResidentSubscription:
        """Bring a :class:`Monitor` up as a per-layer resident handle.

        Descriptive only — no thread, timer, or queue is spawned
        (ADR-0073). L4's event loop iterates
        :meth:`active_subscriptions` and calls
        :meth:`ResidentSubscription.emit` when its watched DataStates
        arrive.

        Looks the declaration up by IRI via the Local-wins rule
        (Local metagraph of ``session.user_id`` wins over Global on
        collision; mirrors :meth:`invoke`). ``subscribes_to`` is taken
        from the declaration unconditionally per ADR-0073 §amendment-1
        clause 2 (kwarg dropped — declaration is source of truth).

        When ``session`` is supplied, ``context['session_user_id']``
        and ``context['session_id']`` are injected for provenance-
        stamping of emitted signals. Caller-set keys are never
        overwritten.

        Args:
            capacity_iri: The Monitor's IRI to start.
            session: Optional bearer of capability + user identity.
                ``None`` resolves against Global only.
            context: Optional context mapping for the resident's
                callable; copied so the registered ``ResidentSubscription``
                does not alias caller state.

        Raises:
            CapacityRegistrationError: ``capacity_iri`` is not
                registered. Pass-through from
                :meth:`_resolve_declaration` per R3 PB-27.
            ResidentError: Declaration resolved by IRI is not a
                :class:`Monitor` (ADR-0073 §amendment-1 clause 4
                halvim divergence — parent raises
                ``CapacityRegistrationError``).

        Returns:
            A fresh :class:`ResidentSubscription` registered in this
            layer's ``_subscriptions`` dict.
        """
        target_uid = session.user_id if session is not None else None
        declaration = self._resolve_declaration(
            capacity_iri, user_id=target_uid
        )
        if not isinstance(declaration, Monitor):
            raise ResidentError(
                f"Capacity {capacity_iri!r} is not a Monitor and cannot "
                "be made resident"
            )
        # Provenance-stamp the resident context when a session is supplied
        # (parent Phase 30 capacity_layer.py:444-449 precedent for invoke).
        if session is not None:
            ctx = dict(context) if context else {}
            ctx.setdefault("session_user_id", session.user_id)
            ctx.setdefault("session_id", session.session_id)
            # Phase 33 (ADR-0146 §amendment-1 clause 2): symmetric with
            # invoke() — Session object injected so resident bodies
            # can call ``session.has(cap)`` for cap-gating.
            ctx.setdefault("session", session)
        else:
            ctx = dict(context) if context else None
        # Phase 34 (R0 PB-5 + R5 PB-B): symmetric conditional KL
        # injection with :meth:`invoke`.
        if self._kl is not None:
            if ctx is None:
                ctx = {}
            ctx.setdefault("kl", self._kl)
        # Build the subscription handle (ADR-0073 — eq=False; ADR-0088 —
        # declaration.subscribes_to is the source of truth).
        import uuid as _uuid  # local — module already imports uuid via runtime
        sub = ResidentSubscription(
            subscription_id=str(_uuid.uuid4()),
            declaration=declaration,
            subscribes_to=tuple(declaration.subscribes_to),
        )
        # Optionally seed the resident's state slot with the provenance
        # context (L4 reads + extends).
        if ctx is not None:
            sub.state["context"] = ctx
        self._subscriptions[sub.subscription_id] = sub
        return sub

    def stop_resident(self, subscription: ResidentSubscription) -> None:
        """Stop a resident, detaching all handlers and removing from registry.

        Strict: raises on already-stopped / never-registered handles
        per R1 PB-10 lock (halvim discipline — cleanup patterns wrap in
        try/except).

        Raises:
            ResidentError: ``subscription`` is not a
                :class:`ResidentSubscription`, OR its id is absent
                from this layer's ``_subscriptions`` registry
                (already stopped OR registered against a different layer).
        """
        if not isinstance(subscription, ResidentSubscription):
            raise ResidentError(
                "stop_resident expects a ResidentSubscription, got "
                f"{type(subscription).__name__}"
            )
        if subscription.subscription_id not in self._subscriptions:
            raise ResidentError(
                f"Unknown subscription id {subscription.subscription_id!r} "
                "(already stopped, or registered against a different layer)"
            )
        subscription._active = False
        subscription.handlers.clear()
        del self._subscriptions[subscription.subscription_id]

    def active_subscriptions(self) -> List[ResidentSubscription]:
        """Return a list copy of every currently-running resident handle.

        Returns a snapshot list (not a live view) so callers may iterate
        without holding the registry stable.
        """
        return list(self._subscriptions.values())

    def _metagraph_for(self, user_id: Optional[str]) -> Metagraph:
        if user_id is None:
            return self._global
        return self.local_metagraph(user_id)

    def _resolve_declaration(
        self, capacity_iri: str, *, user_id: Optional[str]
    ) -> _CapacityBase:
        """Local-wins lookup of a Capacity declaration by IRI.

        When ``user_id is not None``, searches the per-user Local
        ``_capacity_index`` first; falls back to Global. Mirrors KL's
        specialisation rule (Local overrides Global on IRI collision).
        """
        if user_id is not None:
            local_mg = self.local_metagraph(user_id)
            local_index = self._capacity_index[local_mg.metagraph_id]
            if capacity_iri in local_index:
                return self._declarations[capacity_iri]
        global_index = self._capacity_index[self._global.metagraph_id]
        if capacity_iri in global_index:
            return self._declarations[capacity_iri]
        raise CapacityRegistrationError(
            f"No capacity registered with IRI {capacity_iri!r} "
            f"(user_id={user_id!r})"
        )

    def _enforce_global_write(
        self,
        session: Optional[SessionProtocol],
        *,
        op: str,
    ) -> None:
        """Gate a Global-scoped write on ``CAN_WRITE_GLOBAL`` (ADR-0078 + ADR-0080)."""
        if session is None:
            return
        if not session.has(CAN_WRITE_GLOBAL):
            raise PermissionError(
                f"{op}: session {session.session_id!r} "
                f"(user={session.user_id!r}) lacks {CAN_WRITE_GLOBAL!r}"
            )

    def _validate_ref_invariants(
        self,
        ref_to_global: Optional[str],
        ref_type: Optional[str],
        *,
        user_id: Optional[str],
    ) -> None:
        """Per-ref invariants for ``register_capacity``'s ``ref_to_global``."""
        if ref_to_global is None and ref_type is None:
            return
        if user_id is None:
            raise CapacityRegistrationError(
                "ref_to_global is only meaningful for Local capacities "
                "(pass a session)"
            )
        if ref_to_global is None or ref_type is None:
            raise CapacityRegistrationError(
                "ref_to_global and ref_type must be supplied together"
            )
        if ref_type not in REF_TYPES:
            raise CapacityRegistrationError(
                f"ref_type {ref_type!r} not in REF_TYPES {sorted(REF_TYPES)}"
            )

    def __repr__(self) -> str:
        return (
            f"CapacityLayer(global={self._global.name!r}, "
            f"locals={len(self._locals)}, "
            f"capacities={len(self._declarations)})"
        )


__all__ = ["CapacityLayer"]
