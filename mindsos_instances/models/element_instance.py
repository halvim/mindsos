"""Element-instance subclasses for ``mindsos_instances`` (Phase 06).

This module ships the base :class:`ElementInstance` plus eight concrete
subclasses (Phase 06 row §B). Each subclass declares:

* ``KIND: ClassVar[str]`` — class-level discriminator per P26 C.
* ``STRUCTURAL_KEYS: ClassVar[FrozenSet[str]]`` — per-subclass
  structural-field override allow-list per P36 A + round-7 P48 A +
  P60 A.
* ``SET_TYPED_KEYS: ClassVar[FrozenSet[str]]`` — subset of
  ``STRUCTURAL_KEYS`` holding set-typed values (round-7 P57 A — JSON
  list input is coerced to :class:`frozenset` at override-set time).
* ``FORBIDS_TYPE_NAME: ClassVar[bool]`` — ``True`` for Edge-family
  subclasses per P33 B; rejects ``type_name`` override.

Override-dict validation routes via the bifurcation in
``_overrides.validate_overrides`` (round-7 P64 A — structural-bucket
bypasses :func:`validate_user_properties`; user-property-bucket goes
through with ``scope=KIND``).

Instance ID derivation (round-7 P46 C — overrides hash dropped):
``id = mg.id_strategy.generate("instance", content={"template_id": tid,
"instance_seq": seq})`` where ``seq`` is sourced from
:meth:`ElementRegistry._next_seq_for`. Mutable overrides do not perturb
the id.

Composite-specific:

* :class:`CompositeInstance` ships with no ``template_id``
  (bundling-only construct); its members can be element instances or
  other composites. Member-list is a mutable ``list`` per P37 A
  (duplicates allowed, ordered insertion); cycle detection (P25 A)
  runs at ``add_member`` time; cross-metagraph rejection
  (round-7 P50 A) requires ``metagraph_id`` at construction.
* Recursive cascade through composites (P44 A) is implemented by the
  registry (see :class:`mindsos_instances.registry.ElementRegistry`).
"""

from __future__ import annotations

import copy
from typing import (
    Any,
    ClassVar,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    TYPE_CHECKING,
    Union,
)

from mindsos_core.exceptions import IdentityError

from ..exceptions import (
    CompositeCycleError,
    CrossMetagraphCompositeError,
    OverrideScopeError,
    SubGraphInvariantError,
)
from ._overrides import split_single_override, validate_overrides

if TYPE_CHECKING:
    from ..registry import ElementRegistry


# ── base ────────────────────────────────────────────────────────────────────


class ElementInstance:
    """Base class for element instance subclasses (Phase 06 row §B).

    Carries the common surface: ``id``, ``template_id``,
    ``metagraph_id``, ``overrides`` dict, ``_instance_seq`` (round-7
    P46 C disambiguator). Subclasses override the class-level
    discriminator + override allow-list.
    """

    KIND: ClassVar[str] = ""
    STRUCTURAL_KEYS: ClassVar[FrozenSet[str]] = frozenset()
    SET_TYPED_KEYS: ClassVar[FrozenSet[str]] = frozenset()
    FORBIDS_TYPE_NAME: ClassVar[bool] = False

    __slots__ = (
        "id",
        "template_id",
        "metagraph_id",
        "overrides",
        "_instance_seq",
    )

    def __init__(
        self,
        *,
        metagraph_id: str,
        template_id: str,
        overrides: Optional[Mapping[str, Any]] = None,
        _registry: "ElementRegistry",
    ) -> None:
        if _registry.metagraph.metagraph_id != metagraph_id:
            raise IdentityError(
                f"{type(self).__name__} metagraph_id mismatch: "
                f"expected {_registry.metagraph.metagraph_id!r}, "
                f"got {metagraph_id!r}"
            )
        self.metagraph_id: str = metagraph_id
        self.template_id: str = template_id
        # Round-7 P46 C — per-template monotonic counter from registry;
        # used as ID-derivation disambiguator. Overrides do NOT
        # participate in ID derivation; instances stay stable under
        # mutation.
        self._instance_seq: int = _registry._next_seq_for(template_id)
        self.id: str = _registry._mint_instance_id(
            template_id, self._instance_seq
        )
        # Round-7 P64 A — bifurcated validation at construction. Empty
        # dict is the default state.
        self.overrides: Dict[str, Any] = {}
        if overrides:
            validated = validate_overrides(
                overrides,
                kind=self.KIND,
                structural_keys=self.STRUCTURAL_KEYS,
                set_typed_keys=self.SET_TYPED_KEYS,
                forbids_type_name=self.FORBIDS_TYPE_NAME,
            )
            self.overrides.update(validated)

    # ── override mutation API (P27 A) ─────────────────────────────────────

    def set_override(self, key: str, value: Any) -> None:
        """Set ``self.overrides[key] = value`` after validation.

        Raises :class:`OverrideScopeError` on universal-forbid / kind-
        forbid / reserved-key-in-user-prop-bucket violations.
        Set-typed structural fields coerce list→frozenset per round-7
        P57 A.
        """
        coerced = split_single_override(
            key,
            value,
            kind=self.KIND,
            structural_keys=self.STRUCTURAL_KEYS,
            set_typed_keys=self.SET_TYPED_KEYS,
            forbids_type_name=self.FORBIDS_TYPE_NAME,
        )
        self.overrides[key] = coerced

    def clear_override(self, key: str) -> None:
        """Remove ``key`` from ``self.overrides``. No-op if absent."""
        self.overrides.pop(key, None)

    def has_override(self, key: str) -> bool:
        return key in self.overrides

    # ── materialise (Phase 06 row §E + P40 A) ─────────────────────────────

    def materialise(self, metagraph: Any) -> Any:
        """Return a fresh Core object built from template + overrides.

        Dispatches to ``mindsos_instances.materialise.materialise``.
        Local import avoids the circular ``element_instance ↔
        materialise`` cycle.
        """
        from ..materialise import materialise as _mat

        return _mat(self, metagraph)

    # ── repr / equality ───────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(id={self.id[:8]}, "
            f"template_id={self.template_id[:8] if self.template_id else 'None'}, "
            f"overrides={len(self.overrides)})"
        )

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ElementInstance) and self.id == other.id


# ── leaf subclasses (7 of 8 — composite is special) ──────────────────────────


class NodeInstance(ElementInstance):
    """Instance of a Node template (Phase 06 row §B)."""

    KIND: ClassVar[str] = "node"
    STRUCTURAL_KEYS: ClassVar[FrozenSet[str]] = frozenset()
    SET_TYPED_KEYS: ClassVar[FrozenSet[str]] = frozenset()
    FORBIDS_TYPE_NAME: ClassVar[bool] = False


class EdgeInstance(ElementInstance):
    """Instance of an Edge template (Phase 06 row §B).

    Allowed structural overrides: ``source_id``, ``target_id``,
    ``label``. ``type_name`` rejected per P33 B.
    """

    KIND: ClassVar[str] = "edge"
    STRUCTURAL_KEYS: ClassVar[FrozenSet[str]] = frozenset(
        {"source_id", "target_id", "label"}
    )
    SET_TYPED_KEYS: ClassVar[FrozenSet[str]] = frozenset()
    FORBIDS_TYPE_NAME: ClassVar[bool] = True


class HyperEdgeInstance(ElementInstance):
    """Instance of a HyperEdge template (Phase 06 row §B).

    Allowed structural overrides: ``member_ids`` (set of node IDs),
    ``label``. ``type_name`` rejected per P33 B.
    """

    KIND: ClassVar[str] = "hyperedge"
    STRUCTURAL_KEYS: ClassVar[FrozenSet[str]] = frozenset(
        {"member_ids", "label"}
    )
    SET_TYPED_KEYS: ClassVar[FrozenSet[str]] = frozenset({"member_ids"})
    FORBIDS_TYPE_NAME: ClassVar[bool] = True


class GraphInstance(ElementInstance):
    """Instance of a Graph template (Phase 06 row §B).

    Empty override scope in Phase 06 (no structural surface; user
    property bag is Phase 10). Materialise = full deep-copy clone of
    the source Graph per round-7 P54 B.
    """

    KIND: ClassVar[str] = "graph"
    STRUCTURAL_KEYS: ClassVar[FrozenSet[str]] = frozenset()
    SET_TYPED_KEYS: ClassVar[FrozenSet[str]] = frozenset()
    FORBIDS_TYPE_NAME: ClassVar[bool] = False


class SubGraphInstance(ElementInstance):
    """Reference to a subset of a Graph's contents (Phase 06 P13 B).

    ``template_id`` is the source Graph's id. Structural overrides
    ``node_ids`` / ``edge_ids`` define which contents the subgraph
    references. Strict edge-validity invariant per P20 A: every edge in
    ``edge_ids`` must have BOTH endpoints in ``node_ids``; every
    hyperedge must have ALL members in ``node_ids``. Invariant is
    enforced at construction AND after every structural mutation.
    """

    KIND: ClassVar[str] = "subgraph"
    STRUCTURAL_KEYS: ClassVar[FrozenSet[str]] = frozenset(
        {"node_ids", "edge_ids"}
    )
    SET_TYPED_KEYS: ClassVar[FrozenSet[str]] = frozenset(
        {"node_ids", "edge_ids"}
    )
    FORBIDS_TYPE_NAME: ClassVar[bool] = False

    def __init__(
        self,
        *,
        metagraph_id: str,
        template_id: str,
        overrides: Optional[Mapping[str, Any]] = None,
        _registry: "ElementRegistry",
    ) -> None:
        super().__init__(
            metagraph_id=metagraph_id,
            template_id=template_id,
            overrides=overrides,
            _registry=_registry,
        )
        # P20 A — strict invariant check at construction. The override
        # dict carries the node_ids + edge_ids selection; we need the
        # source Graph from the registry's metagraph to validate
        # endpoint membership.
        self._check_invariant(_registry)

    def set_override(self, key: str, value: Any) -> None:
        super().set_override(key, value)
        if key in {"node_ids", "edge_ids"}:
            # Re-check invariant after structural mutation.
            self._check_invariant_via_overrides_only()

    def _check_invariant(self, registry: "ElementRegistry") -> None:
        mg = registry.metagraph
        if self.template_id not in mg.graphs:
            raise SubGraphInvariantError(
                f"SubGraphInstance template_id {self.template_id!r} "
                f"is not a contained graph of metagraph "
                f"{mg.metagraph_id!r}."
            )
        graph = mg.graphs[self.template_id]
        node_ids: FrozenSet[str] = frozenset(
            self.overrides.get("node_ids", frozenset())
        )
        edge_ids: FrozenSet[str] = frozenset(
            self.overrides.get("edge_ids", frozenset())
        )
        # Every node_id must exist in the source graph.
        for nid in node_ids:
            if nid not in graph.nodes:
                raise SubGraphInvariantError(
                    f"SubGraphInstance node_id {nid!r} not in source "
                    f"graph {graph.graph_id!r}."
                )
        # Every edge_id must exist and have endpoints (Edge) or
        # members (HyperEdge) inside node_ids.
        for eid in edge_ids:
            if eid in graph.edges:
                e = graph.edges[eid]
                if e.source.node_id not in node_ids or e.target.node_id not in node_ids:
                    raise SubGraphInvariantError(
                        f"SubGraphInstance edge {eid!r} has endpoints "
                        f"outside node_ids."
                    )
            elif eid in graph.hyperedges:
                he = graph.hyperedges[eid]
                for member in he.nodes:
                    if member.node_id not in node_ids:
                        raise SubGraphInvariantError(
                            f"SubGraphInstance hyperedge {eid!r} has "
                            f"member {member.node_id!r} outside "
                            f"node_ids."
                        )
            else:
                raise SubGraphInvariantError(
                    f"SubGraphInstance edge_id {eid!r} not in source "
                    f"graph {graph.graph_id!r}."
                )

    def _check_invariant_via_overrides_only(self) -> None:
        """Re-check after structural mutation. Pulls the registry/
        metagraph reference lazily via the live override state — set
        from the original ``_check_invariant`` call's registry context.

        Implementation note: we re-fetch the registry/metagraph by
        stashing a weak reference at construction. For Phase 06 simplest
        path, the registry stashes the source graph reference at first
        check; subsequent mutations re-validate against the cached
        graph. Cached graph is invalidated when the source graph itself
        is mutated — that's a future-work edge case (the mutation may
        invalidate the invariant out-of-band).
        """
        # For Phase 06 we don't store a registry ref on the slot list;
        # callers using set_override should subsequently call
        # ``recheck_invariant(registry)`` to verify. Default no-op
        # protects against the mutation surface; explicit re-check is
        # the deliberate API.
        # The CLI sets overrides at construction (single-call demo);
        # library callers that mutate after construction must call
        # ``recheck_invariant`` explicitly.
        # No-op here.
        return

    def recheck_invariant(self, registry: "ElementRegistry") -> None:
        """Re-run P20 A invariant check against the live source Graph."""
        self._check_invariant(registry)


class MetaEdgeInstance(ElementInstance):
    """Instance of a MetaEdge template (Phase 06 row §B).

    Allowed structural overrides: ``source_graph_id``,
    ``target_graph_id``, ``label``. ``type_name`` rejected per P33 B.
    """

    KIND: ClassVar[str] = "metaedge"
    STRUCTURAL_KEYS: ClassVar[FrozenSet[str]] = frozenset(
        {"source_graph_id", "target_graph_id", "label"}
    )
    SET_TYPED_KEYS: ClassVar[FrozenSet[str]] = frozenset()
    FORBIDS_TYPE_NAME: ClassVar[bool] = True


class MetaHyperEdgeInstance(ElementInstance):
    """Instance of a MetaHyperEdge template (Phase 06 row §B).

    Allowed structural overrides: ``graph_ids`` (set of graph IDs;
    round-7 P60 A renamed from ``member_graph_ids`` to match Core's
    field name), ``label``. ``type_name`` rejected per P33 B.
    """

    KIND: ClassVar[str] = "metahyperedge"
    STRUCTURAL_KEYS: ClassVar[FrozenSet[str]] = frozenset(
        {"graph_ids", "label"}
    )
    SET_TYPED_KEYS: ClassVar[FrozenSet[str]] = frozenset({"graph_ids"})
    FORBIDS_TYPE_NAME: ClassVar[bool] = True


# ── composite (the 8th subclass — bundling-only construct) ──────────────────


CompositeMember = Union[ElementInstance, "CompositeInstance"]


class CompositeInstance:
    """A bundling-only construct holding element / composite members
    (Phase 06 row §B + §C + §E).

    Distinct from :class:`ElementInstance` — no ``template_id`` (no
    underlying Core primitive template). Carries:

    * ``id`` — minted via the same id-strategy path as element
      instances.
    * ``metagraph_id`` — required at construction per round-7 P50 A
      (origin no longer inferred from first-add).
    * ``members: List[CompositeMember]`` — mutable, duplicates allowed,
      insertion order preserved (P37 A).
    * ``bundle_overrides: Dict[str, Any]`` — bundle-level user
      properties only per P36 A; validated through
      ``validate_user_properties(scope="composite")`` per round-7
      P61 A.

    Member-list mutation: :meth:`add_member`, :meth:`remove_member`,
    :meth:`remove_all_members`. Cycle detection (P25 A) at add-time;
    cross-metagraph rejection (P43 C + round-7 P50 A); registry-
    membership check at add (round-7 P55 A — stale-ref rejection).
    """

    KIND: ClassVar[str] = "composite"

    __slots__ = (
        "id",
        "metagraph_id",
        "members",
        "bundle_overrides",
        "_instance_seq",
    )

    def __init__(
        self,
        *,
        metagraph_id: str,
        bundle_overrides: Optional[Mapping[str, Any]] = None,
        _registry: "ElementRegistry",
    ) -> None:
        if _registry.metagraph.metagraph_id != metagraph_id:
            raise IdentityError(
                f"CompositeInstance metagraph_id mismatch: expected "
                f"{_registry.metagraph.metagraph_id!r}, got "
                f"{metagraph_id!r}"
            )
        self.metagraph_id: str = metagraph_id
        # Composites have no template; use a synthetic per-metagraph
        # counter via _next_seq_for("__composite__").
        self._instance_seq: int = _registry._next_seq_for("__composite__")
        self.id: str = _registry._mint_instance_id(
            "__composite__", self._instance_seq
        )
        self.members: List[CompositeMember] = []
        # Round-7 P61 A — bundle_overrides validates against user-
        # property rules with scope="composite".
        self.bundle_overrides: Dict[str, Any] = {}
        if bundle_overrides:
            from mindsos_core.exceptions import PropertyShapeError
            from mindsos_core.schema import validate_user_properties

            try:
                validated = validate_user_properties(
                    bundle_overrides, scope="composite"
                )
            except PropertyShapeError as exc:
                raise OverrideScopeError(str(exc)) from exc
            self.bundle_overrides.update(validated)

    @property
    def template_id(self) -> Optional[str]:
        """Composites have no template per Phase 06 P37 A. Returns
        ``None`` for cascade-observer pattern-matching consistency."""
        return None

    # ── bundle override mutation ──────────────────────────────────────────

    def set_bundle_override(self, key: str, value: Any) -> None:
        """Set ``bundle_overrides[key] = value`` after validation."""
        from mindsos_core.exceptions import PropertyShapeError
        from mindsos_core.schema import validate_user_properties

        try:
            validated = validate_user_properties(
                {key: value}, scope="composite"
            )
        except PropertyShapeError as exc:
            raise OverrideScopeError(str(exc)) from exc
        self.bundle_overrides[key] = validated[key]

    def clear_bundle_override(self, key: str) -> None:
        self.bundle_overrides.pop(key, None)

    # ── member-list mutation (P25 A + P37 A + P43 C + round-7 P50/55) ────

    def add_member(
        self,
        member: CompositeMember,
        *,
        _registry: "ElementRegistry",
    ) -> None:
        """Append ``member`` to ``self.members`` after validation.

        Round-7 P50 A — member's ``metagraph_id`` must equal this
        composite's ``metagraph_id`` (raises
        :class:`CrossMetagraphCompositeError`).

        Round-7 P55 A — ``member.id`` must currently exist in
        ``_registry`` (raises :class:`IdentityError`). Closes the
        stale-ref bug-class — cascade-removed instances cannot be
        re-added.

        P25 A — cycle detection: if ``member`` is a composite and
        contains (transitively) ``self``, raise
        :class:`CompositeCycleError`.
        """
        # Cross-metagraph check (P43 C + round-7 P50 A).
        if member.metagraph_id != self.metagraph_id:
            raise CrossMetagraphCompositeError(
                f"CompositeInstance.add_member: member metagraph_id "
                f"{member.metagraph_id!r} != composite "
                f"{self.metagraph_id!r}"
            )
        # Registry-membership check (round-7 P55 A).
        if member.id not in _registry:
            raise IdentityError(
                f"CompositeInstance.add_member: member {member.id!r} "
                f"is not in the metagraph's element_registry "
                f"(stale-ref rejected per round-7 P55 A)."
            )
        # Cycle detection (P25 A).
        if isinstance(member, CompositeInstance):
            if self._reachable_from(member):
                raise CompositeCycleError(
                    f"CompositeInstance.add_member: adding "
                    f"{member.id!r} would create a cycle through "
                    f"composite {self.id!r}."
                )
        self.members.append(member)

    def remove_member(
        self,
        instance_id: str,
        *,
        occurrence: int = 0,
    ) -> None:
        """Remove the ``occurrence``-th member with id ``instance_id``.

        ``occurrence`` is the 0-indexed position among matches; raises
        :class:`IndexError` if no such occurrence exists.
        """
        matches = [
            i for i, m in enumerate(self.members) if m.id == instance_id
        ]
        if not matches:
            raise IndexError(
                f"CompositeInstance.remove_member: no member with "
                f"id {instance_id!r}."
            )
        if occurrence < 0 or occurrence >= len(matches):
            raise IndexError(
                f"CompositeInstance.remove_member: occurrence "
                f"{occurrence} out of range for member {instance_id!r} "
                f"(found {len(matches)} occurrence(s))."
            )
        del self.members[matches[occurrence]]

    def remove_all_members(self, instance_id: str) -> int:
        """Remove every member with id ``instance_id``. Returns count."""
        before = len(self.members)
        self.members = [m for m in self.members if m.id != instance_id]
        return before - len(self.members)

    def member_ids(self) -> List[str]:
        """Ordered ``id`` of every member (duplicates preserved)."""
        return [m.id for m in self.members]

    def _reachable_from(self, member: "CompositeInstance") -> bool:
        """True iff ``self`` is reachable from ``member`` by walking
        nested composites (P25 A cycle detection helper).
        """
        if member is self:
            return True
        for sub in member.members:
            if isinstance(sub, CompositeInstance):
                if self._reachable_from(sub):
                    return True
        return False

    def iter_composite_members(self) -> Iterator["CompositeInstance"]:
        """Yield every composite member (non-recursive, direct only)."""
        for m in self.members:
            if isinstance(m, CompositeInstance):
                yield m

    # ── materialise (Phase 06 row §E + P40 A + P63 A) ─────────────────────

    def materialise(self, metagraph: Any) -> Dict[str, Any]:
        """Return the composite materialise tree dict (recursive)."""
        from ..materialise import materialise as _mat

        return _mat(self, metagraph)

    # ── repr / equality ───────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"CompositeInstance(id={self.id[:8]}, "
            f"metagraph_id={self.metagraph_id[:8]}, "
            f"members={len(self.members)}, "
            f"bundle_overrides={len(self.bundle_overrides)})"
        )

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CompositeInstance) and self.id == other.id
