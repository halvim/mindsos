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

**Monitor enumeration (Phase 41).** :meth:`iter_monitors` enumerates
registered :class:`Monitor` declarations for the L4 substrate to build
its session-scope subscription registry. Monitor *lifecycle* (start /
stop / dispatch) relocated to the L4 substrate per ADR-0155 — the
Phase 31 resident lifecycle methods + per-layer subscription registry
were retired in Phase 41.

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

import logging
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from mindsos_core import Edge, Graph, Metagraph, Node
# Phase 34 B-34-T3: ``kl`` constructor param annotated as ``Optional[Any]``
# (not ``Optional["KnowledgeLayer"]``). The Phase 28 import-isolation
# test (``tests/phase_28/test_import_isolation_phase_28.py``) AST-walks
# every ``mindsos_capacity/*.py`` and forbids ANY top-level import of
# ``mindsos_knowledge`` — including ``if TYPE_CHECKING: from
# mindsos_knowledge import KnowledgeLayer``. Layer-discipline wins over
# static-type signal here. Capacity body validates the duck-type at
# invocation per R3 PB-F (raises RuntimeError on missing/wrong-type kl).

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
)
from .runtime import (
    ProblemTraceSink,
    invoke as _runtime_invoke,
)
from .identifiers import (
    CONSTRAINT_KINDS,
    EDGE_CONSTRAINT,
    REF_GLOBAL_CAPACITY,
    REF_TYPE_KEY,
    REF_TYPES,
    RESERVED_PROPERTY_KEYS,
    RESERVED_REALMS,
)
from .types import SessionArg, SessionProtocol
from .views import CapacityLayerView

log = logging.getLogger(__name__)


class CapacityLayer:
    """Top-level façade over Global + per-user Local L3 metagraphs."""

    def __init__(
        self,
        *,
        global_metagraph: Optional[Metagraph] = None,
        strict: bool = False,
        categories: Optional[Iterable[str]] = None,
        kl: Optional[Any] = None,
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
                :meth:`invoke` injects the KL
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
        self._kl: Optional[Any] = kl

        self._capacity_index: Dict[str, Dict[str, Tuple[Node, Graph]]] = {
            self._global.metagraph_id: {},
        }
        self._declarations: Dict[str, _CapacityBase] = {}

        # Phase 30 — single in-memory ProblemTraceSink per layer instance
        # (ADR-0074 §Implementation). Multi-tenant scoping is L4's
        # concern (R2 PB-29(a) lock; payload-side ``user_id`` provenance).
        self.problem_trace: ProblemTraceSink = ProblemTraceSink()

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
        allow_new_realm: bool = False,
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
        name = datastate.name
        if "." not in name:
            raise CapacityRegistrationError(
                f"DataState name {name!r} missing realm prefix; "
                "expected '<realm>.<name>'"
            )
        realm, suffix = name.split(".", 1)
        if "." in suffix:
            raise CapacityRegistrationError(
                f"DataState name {name!r} has multi-dot; "
                "v1 allows single-dot only"
            )
        if realm not in RESERVED_REALMS and not allow_new_realm:
            raise CapacityRegistrationError(
                f"Realm {realm!r} not in reserved set "
                f"{sorted(RESERVED_REALMS)}; pass allow_new_realm=True "
                "for admin extension"
            )
        if realm not in RESERVED_REALMS and allow_new_realm:
            log.info(
                "admin extension: registering DataState in new realm %r",
                realm,
            )
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

    # ── Phase 41 — monitor enumeration (ADR-0155) ─────────────────────

    def iter_monitors(self) -> List[Monitor]:
        """Return every registered :class:`Monitor` declaration.

        The L4 substrate consumes this at session start to build its
        session-scope ``MonitorSubscriptionRegistry``
        (``Dict[DataState IRI, List[Monitor IRI]]``) per ADR-0155;
        Monitor *lifecycle* (start / stop / dispatch) is owned by L4,
        not L3.

        Enumeration is merged + Local-wins by construction: declarations
        live in the single IRI-keyed ``self._declarations`` map (one
        object per IRI, last-write-wins on a Local/Global IRI collision —
        the same single-object-per-IRI model :meth:`_resolve_declaration`
        relies on). Multi-tenant scoping (restricting to one user's
        Locals + Global) is an L4 concern, consistent with the
        single-sink ``problem_trace`` discipline (R2 PB-29). Returns an
        empty list when no Monitors are registered.
        """
        return [
            d for d in self._declarations.values() if isinstance(d, Monitor)
        ]

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
