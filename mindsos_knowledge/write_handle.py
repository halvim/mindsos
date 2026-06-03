"""``KLWriteHandle`` — KL-side write-routing handle (Phase 34; ADR-0143 Accepted).

L2's entry-point surface for L3 write capacities. The handle is a
*non-mutating accessor* (ADR-0143 §Constraint "never mutates"): it
encapsulates the routing + IRI-builder + ``write_and_validate`` composite
an L3 write capacity needs, but does not call L1 mutation primitives
directly. L3 capacities reach mutation through ``handle.graph()`` (raw
L1 access) or through ``handle.write_and_validate(...)`` (the composite
that mints an IRI, calls ``add_node`` on the role-graph, and constructs
a :class:`WriteResult`).

**Phase 34 wiring (ADR-0146 §amendment-1 clauses 4 + 5 closed).**

- ``metagraph()`` — returns the real :class:`Metagraph` (unchanged from
  Phase 33).
- ``graph()`` — iterates ``_metagraph.graphs.values()`` and returns the
  L1 :class:`Graph` whose ``role`` matches ``self.role``. Raises
  :class:`KeyError` if no role-graph is present (programmer error per
  ADR-0146 §Decision — capacity asked for a role the metagraph wasn't
  bootstrapped with).
- ``mint_iri(type_, **content)`` — dispatches via ``_IRI_BUILDERS``
  registry keyed by ``(role, NodeType_name)`` per ADR-0146
  §amendment-3 (Phase 39 multi-NodeType dispatch). The handle's
  ``_version`` literal threads in; ``content`` kwargs flow to the
  role+NodeType-specific builder. Missing kwargs surface as
  ``KeyError`` per ADR-0146 §Decision ("programmer error →
  propagate").
- ``write_and_validate(*, value, type_, **mint_content)`` — composite
  that mints an IRI, calls ``self.graph().add_node(...)``, returns
  :class:`WriteResult` on success. L1 raises (``UnknownTypeError``,
  ``IdentityError``, ``PropertyShapeError``) propagate; the
  ``runtime.invoke`` envelope catches per ADR-0072. **Phase 36 scope:**
  ``write_and_validate`` itself remains unchanged from Phase 34 —
  structural validation via L1 schema only. Semantic validators are
  composed in the *capacity body precondition* immediately preceding
  the call (ADR-0139 §Decision §Capacity-contract); capacities call
  ``handle.validate_node(...)`` (Phase 36 wired) or compose individual
  validators directly per the §Capacity-contract fallback.

**Phase 36 wiring (ADR-0139 §amendment-1; ADR-0143 §Impl Phase 36 footer).**

- ``validate_node(*, value, type_, **refs)`` — wired. Dispatches via
  :data:`mindsos_knowledge.validators._VALIDATORS_BY_ROLE` (per-role
  adapter registry; per-role-only dispatch — distinct from Phase 39
  ``_IRI_BUILDERS`` tuple-key shape since validator dispatch is
  per-role-only per ADR-0139 §amendment-1 unchanged).
  Returns :class:`ValidationResult`. Phase 39 ships 2 adapter entries
  (``episodic_memories`` + ``problem-trace``); roles without an
  adapter raise
  :class:`WriteHandleNotWiredError` per the per-flow extension
  pattern (ADR-0139 §amendment-1 clause 3 carry-forward).
- ``validate_xref(...)`` — STAYS raising
  :class:`WriteHandleNotWiredError`. Defers per-flow alongside the
  first XRef-writing L3 capacity (Phase 36 ships no XRef writers; the
  2 shipped capacities perform node writes only).

The handle never accretes mutation methods (``add_node`` / ``add_xref``
/ ``set_property`` etc.). Code review enforces this discipline per
ADR-0143 §Constraint + ``docs/dev/review-checklist.md`` (Phase 34).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal, Optional

from mindsos_capacity.exceptions import WriteHandleNotWiredError
from mindsos_capacity.write_outcome import WriteResult

from .identifiers import _IRI_BUILDERS
from .validators import ValidationResult, _VALIDATORS_BY_ROLE

if TYPE_CHECKING:
    from mindsos_core import Graph, Metagraph

    from .knowledge_layer import KnowledgeLayer
    from .types import SessionProtocol


@dataclass(frozen=True)
class KLWriteHandle:
    """Lightweight typed handle returned by :meth:`KnowledgeLayer.writeable`.

    Binds a ``(session, role, scope, version)`` tuple to its target L1
    Metagraph + role-graph routing. Capacity code calls
    ``handle.write_and_validate(...)`` (the composite) or
    ``handle.graph().add_node(...)`` (raw L1 access) for mutation; the
    handle itself never mutates.

    Attributes:
        role: The role-graph role this handle writes to (e.g.,
            ``"episodic_memories"`` for ``capacity:consolidate:mm``;
            ``"problem-trace"`` for ``capacity:trace:problem``).
        scope: ``'local'`` (per-user) or ``'global'`` (shared).
        session: Bearer of capability + user identity. ``None`` is
            permitted only for ``scope='global'`` per ADR-0080
            bootstrap carve-out; :meth:`KnowledgeLayer.writeable`
            rejects ``session=None`` for ``scope='local'`` with a
            :class:`ValueError`.
        _kl: Back-reference to the constructing
            :class:`KnowledgeLayer`. Underscore-prefixed to signal
            "internals; tests may probe; capacity code should not".
        _metagraph: The L1 :class:`Metagraph` the handle routes into
            (Local of ``session.user_id`` for ``scope='local'``;
            Global for ``scope='global'``).
        _version: Role-version literal embedded into minted IRIs.
            Phase 34 lock — Phase 17 retirement (ADR-0150 §am-3) left
            no active-version dispatch mechanism; the handle holds a
            single version literal bound at construction.
    """

    role: str
    scope: Literal["local", "global"]
    session: Optional["SessionProtocol"]
    _kl: "KnowledgeLayer"
    _metagraph: "Metagraph"
    _version: str

    def metagraph(self) -> "Metagraph":
        """Return the L1 Metagraph this handle writes into (real; not stubbed).

        Read-only state inspection. Used by capacity bodies to derive
        XRef target identifiers and inspect existing nodes before
        mutation.
        """
        return self._metagraph

    def graph(self) -> "Graph":
        """Return the L1 :class:`Graph` for ``self.role`` in ``_metagraph``.

        Phase 34 body (ADR-0146 §Implementation): iterates the parent
        metagraph's graphs and returns the one whose ``.role`` matches
        ``self.role``. Raises :class:`KeyError` if no matching role-graph
        exists — that is a programmer error (capacity asked for a role
        the metagraph wasn't bootstrapped with) per ADR-0146 §Decision
        "programmer error → propagate".

        Phase 17 retirement (ADR-0150 §am-3) locks the one-graph-per-role
        invariant in the metagraph; ``next(...)`` returns the first
        matching graph deterministically.

        Raises:
            KeyError: No graph with ``role == self.role`` exists in
                ``self._metagraph``.
        """
        for g in self._metagraph.graphs.values():
            if g.role == self.role:
                return g
        raise KeyError(
            f"KLWriteHandle.graph(role={self.role!r}): no graph with that "
            f"role in metagraph {self._metagraph.metagraph_id!r}. "
            f"Bootstrap the role-graph before constructing the handle."
        )

    def mint_iri(self, type_: str, **content: Any) -> str:
        """Mint a stable IRI per the (role, NodeType) IRI builder.

        Phase 39 body (ADR-0146 §amendment-3): dispatches via the
        ``_IRI_BUILDERS`` registry in
        ``mindsos_knowledge/identifiers.py``, keyed by
        ``(self.role, type_)``. Threads the handle's ``_version``
        literal as the first positional arg; ``content`` kwargs flow
        to the role+NodeType-specific builder wrapper.

        Required ``content`` keys per (role, NodeType):

        * ``(episodic_memories, Episode)`` — ``user_id`` + ``episode_id``
        * ``(episodic_memories, Memory)`` — ``user_id`` + ``memory_id``
        * ``(problem-trace, ProblemTraceEntry)`` — ``trace_id``

        Missing keys raise :class:`KeyError` per ADR-0146 §Decision
        (programmer error). Unsupported ``(role, type_)`` pairs raise
        :class:`KeyError` from the registry lookup.

        Args:
            type_: NodeType name (L2 convention; e.g., ``"Episode"`` or
                ``"Memory"`` or ``"ProblemTraceEntry"``). Forwarded to
                the registry lookup as the second key component.
            **content: Per-(role, NodeType) kwargs forwarded to the
                role+NodeType-specific builder wrapper.

        Raises:
            KeyError: ``(self.role, type_)`` not in ``_IRI_BUILDERS``
                OR required content kwargs missing.
            RefFormatError: content values fail the IRI charset/format
                validation (raised by the underlying builder).
        """
        try:
            builder = _IRI_BUILDERS[(self.role, type_)]
        except KeyError as exc:
            raise KeyError(
                f"KLWriteHandle.mint_iri(role={self.role!r}, type_={type_!r}): "
                f"no IRI builder registered for (role, NodeType). Phase 39 "
                f"supports {sorted(_IRI_BUILDERS.keys())!r}; per-flow add "
                f"the (role, NodeType) pair's builder when the capacity "
                f"lands (ADR-0146 §amendment-3 + ADR-0147)."
            ) from exc
        return builder(self._version, **content)  # type: ignore[operator]

    def write_and_validate(
        self,
        *,
        value: Any,
        type_: str,
        **mint_content: Any,
    ) -> WriteResult:
        """Composite write: mint IRI → add_node → return :class:`WriteResult`.

        Phase 34 ship (PHASE_MAP §34 feature line; ADR-0146 §Implementation
        criterion (b)). Encapsulates the 3-line ``mint_iri → add_node →
        WriteResult`` sequence so capacity bodies don't repeat it.

        **Phase 34 scope:** structural validation via L1 schema only
        (``Graph.add_node`` fires ``UnknownTypeError`` /
        ``PropertyShapeError`` / ``IdentityError`` as configured).
        Semantic validators (KL ``validate_node`` per ADR-0139) integrate
        at Phase 36; this method does NOT call them today (they still
        raise :class:`WriteHandleNotWiredError`). The "validate" half of
        the name refers to L1's structural validators that fire on
        ``add_node``.

        L1 raises propagate to ``runtime.invoke`` which envelopes as
        ``InvocationResult(success=False, error=...)`` per ADR-0072 —
        Phase 34 does NOT wrap L1 errors as ``ProblemTraceRecord``
        (ADR-0146 §amendment-1 clause 1 remains open; L4 consumer drives
        the eventual flip in a later phase).

        Args:
            value: Primary node value passed to ``add_node`` as ``value=``.
            type_: NodeType name (L2 convention); translated to L1's
                ``type_name`` kwarg at the call site, and forwarded to
                :meth:`mint_iri` as the registry-dispatch key per
                ADR-0146 §amendment-3. Phase 39 schema whitelists:
                ``"Episode"`` or ``"Memory"`` (episodic_memories role)
                or ``"ProblemTraceEntry"`` (problem-trace role).
            **mint_content: Per-(role, NodeType) kwargs forwarded to
                :meth:`mint_iri` (e.g., ``user_id`` + ``episode_id``
                for Episode; ``user_id`` + ``memory_id`` for Memory).

        Returns:
            :class:`WriteResult` with ``iri`` (minted), ``role`` /
            ``scope`` (from handle), ``written_at`` (UTC now), and
            empty ``extras``.

        Raises:
            KeyError: As :meth:`mint_iri`.
            UnknownTypeError / PropertyShapeError / IdentityError /
            RefFormatError: L1 add_node validation errors; propagate
                per ADR-0146 §Decision.
        """
        iri = self.mint_iri(type_, **mint_content)
        # L1 ``add_node`` signature: (value, type_name, *, properties=None,
        # node_id=None, _validate=True). L2 convention exposes ``type_``;
        # translate at the boundary per Phase 34 R4 §am-impl-1.
        self.graph().add_node(value=value, type_name=type_, node_id=iri)
        return WriteResult(
            iri=iri,
            role=self.role,
            scope=self.scope,
            written_at=datetime.now(timezone.utc),
            extras={},
        )

    def validate_node(
        self,
        *,
        value: Any,
        type_: str,
        **refs: Any,
    ) -> ValidationResult:
        """Compose role-appropriate KL semantic validators (Phase 36; ADR-0139).

        Phase 36 body (ADR-0139 §amendment-1; ADR-0143 §Impl Phase 36
        footer). Dispatches via
        :data:`mindsos_knowledge.validators._VALIDATORS_BY_ROLE` —
        per-role adapter registry mirroring ``_IRI_BUILDERS`` shape
        (R3-PB-A). The adapter for ``self.role`` returns a
        :class:`ValidationResult` reflecting the composed chain (first-
        failure-wins per R3-PB-I; Phase 36 chains are single-validator
        so the semantic reduces to "the one validator's result").

        Phase 39 ships 2 adapter entries — ``episodic_memories`` +
        ``problem-trace`` (the 2 shipped write capacities' roles; per
        ADR-0044 §amendment-3 rename).
        Roles without a registered adapter raise
        :class:`WriteHandleNotWiredError` per the per-flow extension
        discipline (ADR-0139 §amendment-1 clause 3 carry-forward; new
        adapters land alongside the consuming write capacity).

        ``write_and_validate`` itself does NOT call this method —
        composition lives in the *capacity body precondition* per
        ADR-0139 §Decision §Capacity-contract (PB-1 = B). Capacity
        authors invoke ``handle.validate_node(value=..., type_=...)``
        explicitly before ``handle.write_and_validate(...)`` and raise
        :class:`SemanticValidationError` on ``not result.ok`` (per
        R2-PB-J wiring shape).

        Args:
            value: The proposed node value (forwarded to the
                adapter; reserved for future validators that inspect
                value-shape).
            type_: The proposed node type (forwarded; reserved).
            **refs: Per-role ref content (forwarded; reserved for
                future ``validate_local_to_global_ref`` adapter
                compositions).

        Returns:
            :class:`ValidationResult` — the composed adapter result.

        Raises:
            WriteHandleNotWiredError: ``self.role`` not in
                ``_VALIDATORS_BY_ROLE`` (no adapter registered yet
                for this role's writes).
        """
        try:
            adapter = _VALIDATORS_BY_ROLE[self.role]
        except KeyError as exc:
            raise WriteHandleNotWiredError(
                f"KLWriteHandle.validate_node(role={self.role!r}): no "
                f"validator adapter registered for role. Phase 36 supports "
                f"{sorted(_VALIDATORS_BY_ROLE.keys())!r}; per-flow add the "
                f"role's adapter when the capacity lands (ADR-0139 "
                "§amendment-1 clause 3 carry-forward)."
            ) from exc
        return adapter(self, value, type_, **refs)  # type: ignore[operator]

    def validate_xref(
        self,
        *,
        target_metagraph: "Metagraph",
        target_role: str,
        target_id: str,
        ref_type: str,
    ) -> Any:
        """Validate cross-metagraph XRef target existence + ref_type membership.

        **Phase 36 status:** STILL raises :class:`WriteHandleNotWiredError`.
        Per-flow deferred (R1-PB-B): Phase 36 ships no XRef-writing
        capacity, so the composite has no consumer; the body wires
        alongside the first XRef writer per ADR-0139 §amendment-1
        clause 3 carry-forward.

        The underlying validators
        (:func:`mindsos_knowledge.validators.validate_local_to_global_ref`,
        :func:`mindsos_knowledge.validators.validate_ref_type`) ship at
        Phase 36 as pure functions — direct calls from a capacity body
        are valid per ADR-0139 §Capacity-contract fallback. The
        composite is what defers.
        """
        raise WriteHandleNotWiredError(
            f"KLWriteHandle.validate_xref(role={self.role!r}, "
            f"target_role={target_role!r}, ref_type={ref_type!r}) "
            "is not wired — defers per-flow alongside first XRef-writing "
            "capacity (ADR-0139 §amendment-1 clause 3 carry-forward; "
            "underlying validators available via "
            "mindsos_knowledge.validators)."
        )


__all__ = ["KLWriteHandle"]
