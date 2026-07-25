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

**Bipartite topology (ADR-0156, Phase 42).** :meth:`register_capacity`
emits ``PRODUCES`` (capacity→DataState) + ``CONSUMES`` (DataState→
capacity) IntergraphEdges from the declaration's ``outputs``/``inputs``;
``if_exists="upsert"`` makes re-registration idempotent. The Phase 29
type-compatibility auto-discovery (module, hooks, ``rediscover``) was
retired here — pipeline topology is now the explicit bipartite edge set.

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

The class always takes ``session: Optional[SessionProtocol]`` per
ADR-0080 bootstrap carve-out: ``None`` is the pre-server admin path; a
real :class:`Session` (typically ``mindsos_server.session.Session``) is
the production path. No legacy ``user_id=`` kw is supported (halvim
divergence from parent layout per R1 PB-14 lock — halvim has zero such
callers).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Literal, Mapping, Optional, Tuple

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
from .exceptions import (
    CapacityRegistrationError,
    ConstraintViolationError,
)
from .runtime import (
    ProblemTraceSink,
    invoke as _runtime_invoke,
)
from .identifiers import (
    CONSTRAINT_KINDS,
    EDGE_CONSTRAINT,
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    INPUT_GROUPS,
    REF_GLOBAL_CAPACITY,
    REF_TYPE_KEY,
    REF_TYPES,
    RESERVED_PROPERTY_KEYS,
    RESERVED_REALMS,
)


def _has_intergraph_edge(
    mg: Metagraph,
    source_graph_id: str,
    source_node_id: str,
    target_graph_id: str,
    target_node_id: str,
    type_name: str,
) -> bool:
    """True if a matching IntergraphEdge already exists (upsert idempotency).

    Replaces the retired ``discovery._edge_already_exists``; scans the
    metagraph's in-memory ``iter_intergraph_edges`` (ADR-0156 bipartite
    walk primitive — Pattern B persistence is invisible at this layer).
    """
    for ie in mg.iter_intergraph_edges():
        if (
            ie.source_graph_id == source_graph_id
            and ie.source_node_id == source_node_id
            and ie.target_graph_id == target_graph_id
            and ie.target_node_id == target_node_id
            and ie.type_name == type_name
        ):
            return True
    return False
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

        self._capacity_index: Dict[str, Dict[str, Tuple[Node, Graph, _CapacityBase]]] = {
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
        return node

    def register_capacity(
        self,
        declaration: _CapacityBase,
        *,
        session: SessionArg = None,
        ref_to_global: Optional[str] = None,
        ref_type: Optional[str] = None,
        extra_properties: Optional[Mapping[str, Any]] = None,
        if_exists: Literal["raise", "upsert"] = "raise",
    ) -> Node:
        """Register a Capacity / Monitor / Adapter.

        ADR-0156 bipartite topology: emits ``PRODUCES`` (capacity→DataState)
        + ``CONSUMES`` (DataState→capacity) IntergraphEdges from the
        declaration's ``outputs``/``inputs`` at registration time. With
        ``if_exists="upsert"`` an already-registered IRI re-emits any
        missing edges idempotently (migrator + partial-state recovery
        path) instead of raising, **and re-binds the in-memory declaration**
        (last-registration-wins, mirroring the fresh-registration branch
        and the Local-wins ``_declarations`` semantic) so the swapped
        ``implementation`` is the one ``invoke`` resolves. Per ADR-0156
        §amendment-1 this broadens the original edge-only idempotency
        scope; the persisted node ``properties`` are **not** rewritten on
        upsert (the existing node is reused), so metadata-only re-registration
        is out of contract.

        ADR-0159 registration contract v2: validates the new contract
        fields (``inline`` requires ``max_latency_ms``; ``precondition_iri``
        / ``effect_iri`` must be well-formed capacity IRIs and, when they
        resolve, belong to the ``predicate`` family).

        Raises:
            CapacityRegistrationError: declaration is not
                ``_CapacityBase``-derived, IRI duplicate (``if_exists=
                "raise"``), IRI collides with existing node id, unknown
                DataState in inputs/outputs, reserved property key in
                extras, ref-type invariants violated, or a contract-field
                invariant is violated.
            PermissionError: ``session`` lacks ``CAN_WRITE_GLOBAL`` when
                writing to Global.
        """
        if not isinstance(declaration, _CapacityBase):
            raise CapacityRegistrationError(
                f"Expected a Capacity/Monitor/Adapter, got "
                f"{type(declaration).__name__}"
            )
        self._validate_contract_fields(declaration)
        target_uid = session.user_id if session is not None else None
        if target_uid is None:
            self._enforce_global_write(session, op="register_capacity")

        mg = self._metagraph_for(target_uid)
        index = self._capacity_index[mg.metagraph_id]

        ds_graph = ensure_datastate_graph(mg, strict=self._strict)
        if target_uid is not None:
            # ADR-0185 (A2′): a Local capacity may reference DataStates
            # that live only in the Global DataState graph (the common
            # case — a taught composite chaining Global builtins). Both
            # ``validate_for_registration`` and the ADR-0156
            # PRODUCES/CONSUMES edge emission below are Local-scoped (the
            # edges target ``ds_graph``, the Local DataState graph), so
            # mirror any referenced Global-only DataState into the Local
            # graph first. Idempotent — already-Local IRIs and IRIs
            # absent from Global too are skipped, the latter falling
            # through to ``validate_for_registration``'s raise.
            self._mirror_global_datastates(
                ds_graph,
                tuple(declaration.inputs) + tuple(declaration.outputs),
            )
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
        existing = index.get(declaration.iri)
        if existing is not None:
            if if_exists == "raise":
                raise CapacityRegistrationError(
                    f"Capacity {declaration.iri!r} already registered"
                )
            # if_exists="upsert": reuse the node; re-emit missing edges
            # below. Also re-bind the in-memory declaration (ADR-0156
            # §amendment-1) — last-registration-wins, mirroring the
            # fresh-registration branch — so a re-registered IRI swaps the
            # bound ``implementation`` that ``invoke`` resolves via
            # ``_declarations``. The persisted node ``properties`` are left
            # as-is (the existing node is reused).
            node, category_graph, _ = existing
            index[declaration.iri] = (node, category_graph, declaration)
            self._declarations[declaration.iri] = declaration
        else:
            if declaration.iri in category_graph.nodes:
                raise CapacityRegistrationError(
                    f"Capacity IRI collides with existing node id in graph "
                    f"{category_graph.role!r}"
                )
            node = category_graph.add_node(
                value=declaration.name,
                type_name=declaration.node_type,
                properties=props,
                node_id=declaration.iri,
            )
            index[declaration.iri] = (node, category_graph, declaration)
            self._declarations[declaration.iri] = declaration

        # ADR-0156 — bipartite topology. The declaration's inputs/outputs
        # are the single authoring-time source; persistence is the
        # PRODUCES (capacity→DataState) + CONSUMES (DataState→capacity)
        # IntergraphEdges emitted here. Idempotent — skips edges that
        # already exist so the upsert/migrator path is safe to re-run.
        cap_gid = category_graph.graph_id
        ds_gid = ds_graph.graph_id
        for out_iri in declaration.outputs:
            if not _has_intergraph_edge(
                mg, cap_gid, node.node_id, ds_gid, out_iri, EDGE_PRODUCES
            ):
                mg.add_intergraph_edge(
                    cap_gid, node.node_id, ds_gid, out_iri, EDGE_PRODUCES
                )
        for in_iri in declaration.inputs:
            if not _has_intergraph_edge(
                mg, ds_gid, in_iri, cap_gid, node.node_id, EDGE_CONSUMES
            ):
                mg.add_intergraph_edge(
                    ds_gid, in_iri, cap_gid, node.node_id, EDGE_CONSUMES
                )
        return node

    def _validate_contract_fields(self, declaration: _CapacityBase) -> None:
        """ADR-0159 register-time contract-field validation.

        ``inline=True`` requires ``max_latency_ms``. ``precondition_iri``
        and ``effect_iri``, when set, must be well-formed capacity IRIs;
        the predicate-family resolution check is soft (enforced only when
        the IRI resolves to an already-registered declaration — the
        ``predicate.*`` family ships downstream of v1 per ADR-0157).
        """
        if declaration.inline and declaration.max_latency_ms is None:
            raise CapacityRegistrationError(
                f"Capacity {declaration.iri!r}: inline=True requires "
                "max_latency_ms to be declared"
            )
        # ADR-0159 §amendment-1 — typed input-group value check.
        if declaration.input_group not in INPUT_GROUPS:
            raise CapacityRegistrationError(
                f"Capacity {declaration.iri!r}: input_group="
                f"{declaration.input_group!r} is not one of "
                f"{sorted(INPUT_GROUPS)}"
            )
        for field_name, iri_val in (
            ("precondition_iri", declaration.precondition_iri),
            ("effect_iri", declaration.effect_iri),
        ):
            if iri_val is None:
                continue
            if not iri_val.startswith("capacity:"):
                raise CapacityRegistrationError(
                    f"Capacity {declaration.iri!r}: {field_name}={iri_val!r} "
                    "is not a well-formed capacity IRI"
                )
            resolved = self._declarations.get(iri_val)
            if resolved is not None and resolved.category != "predicate":
                raise CapacityRegistrationError(
                    f"Capacity {declaration.iri!r}: {field_name}={iri_val!r} "
                    f"resolves to a non-predicate capacity "
                    f"(category={resolved.category!r})"
                )

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
            source_node, source_graph, _ = index[source_iri]
            target_node, target_graph, _ = index[target_iri]
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

    def resolve_declaration(
        self, capacity_iri: str, *, session: SessionArg = None
    ) -> _CapacityBase:
        """Scope-correct resolution: the owner's Local override when one
        exists, else Global. Two-tier surface for dispatch + input-wiring;
        ``get_declaration`` stays sessionless/merged.
        """
        target_uid = session.user_id if session is not None else None
        return self._resolve_declaration(capacity_iri, user_id=target_uid)

    def iter_declarations(self) -> List[_CapacityBase]:
        """Return every registered declaration (Local + Global)."""
        return list(self._declarations.values())

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
        # ADR-0180 (Phase 48): write-bodies (zero declared outputs) receive a
        # typed CapacityContext carrying the pre-authorized, session-bound
        # ``writeable`` capability (the gate travels with the capability,
        # built here by the session-holder for the CLI / direct-invoke path —
        # the L4 task path builds it in ``mindsos_intelligence.dispatch``).
        # Read-bodies keep the legacy dict context (A1 scope boundary — no
        # read-corpus churn; the transitional union annotation is retained).
        if not declaration.outputs:
            from .context import CapacityContext, make_writeable

            write_ctx = CapacityContext(
                session_id=getattr(session, "session_id", "session"),
                user_id=getattr(session, "user_id", "user"),
                learned_parameters_snapshot={},
                kl=self._kl,
                cl=self,
                writeable=make_writeable(self._kl, session),
            )
            return _runtime_invoke(
                declaration,
                inputs,
                context=write_ctx,
                task_id=task_id,
                step_id=step_id,
                problem_trace_sink=self.problem_trace,
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

    def _mirror_global_datastates(self, local_ds_graph: Graph, iris) -> None:
        """Mirror referenced Global DataStates into a Local DataState graph.

        ADR-0185 (A2′). A Local capacity registration may reference
        DataStates that live only in the Global DataState graph — the
        common case for a taught composite chaining Global builtins.
        Both :meth:`_CapacityBase.validate_for_registration` and the
        ADR-0156 ``PRODUCES``/``CONSUMES`` :class:`IntergraphEdge`
        emission are Local-scoped (the edges' DataState endpoint must be
        in ``local_ds_graph``), so the referenced nodes must exist in the
        *Local* DataState graph. Copy each Global-only referenced
        DataState node verbatim (value / type / properties / id) into the
        Local graph. The Local and Global Metagraphs have independent
        identity registries, so re-using the IRI as the Local node id is
        well-formed (mirrors the capacity Local-wins model). Idempotent:
        IRIs already present Local-side are skipped; IRIs absent from
        Global too are skipped (left for ``validate_for_registration`` to
        reject).
        """
        global_ds = ensure_datastate_graph(self._global, strict=self._strict)
        for iri in iris:
            if iri in local_ds_graph.nodes:
                continue
            gnode = global_ds.nodes.get(iri)
            if gnode is None:
                continue
            local_ds_graph.add_node(
                value=gnode.value,
                type_name=gnode.type_name,
                properties=dict(gnode.properties),
                node_id=gnode.node_id,
            )

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
            local_mg = self._locals.get(user_id)
            if local_mg is not None:
                local_index = self._capacity_index[local_mg.metagraph_id]
                if capacity_iri in local_index:
                    return local_index[capacity_iri][2]
        global_index = self._capacity_index[self._global.metagraph_id]
        if capacity_iri in global_index:
            return global_index[capacity_iri][2]
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
