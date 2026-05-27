"""``KLWriteHandle`` — KL-side write-routing handle (Phase 33 stub; ADR-0143).

L2's entry-point surface for L3 write capacities. The handle is a
*non-mutating accessor* (ADR-0143 §Constraint "never mutates"): it
encapsulates the routing + IRI-builder + validator composition an L3
write capacity needs, but does not call L1 mutation primitives itself.
L3 capacities reach mutation through ``handle.graph()`` and call L1
directly.

**Phase 33 stub-phase shape (ADR-0146 §amendment-1 clause 5).** Phase
33 ships the surface so L3 write capacities can register + invoke; the
handle bodies are partially stubbed:

- ``metagraph()`` — returns the real :class:`Metagraph` (read-only state
  inspection; safe at stub phase).
- ``graph()`` — raises :class:`WriteHandleNotWiredError`.
- ``mint_iri(**content)`` — raises :class:`WriteHandleNotWiredError`
  (version handling deferred post-Phase 17 retirement per ADR-0150
  §amendment-3).
- ``validate_node(...)`` — raises :class:`WriteHandleNotWiredError`
  (KL semantic validators land at Phase 36; ADR-0139).
- ``validate_xref(...)`` — raises :class:`WriteHandleNotWiredError`.

Phase 34 (ADR-0146) wires the working bodies + deletes the raise sites
in ``graph()`` and ``mint_iri()``. Phase 36 (ADR-0139) wires the two
validator methods.

The handle never accretes mutation methods (``add_node`` / ``add_xref``
/ ``set_property`` etc.). Code review enforces this discipline per
ADR-0143 §Constraint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Optional

from mindsos_capacity.exceptions import WriteHandleNotWiredError

if TYPE_CHECKING:
    from mindsos_core import Graph, Metagraph

    from .knowledge_layer import KnowledgeLayer
    from .types import SessionProtocol


@dataclass(frozen=True)
class KLWriteHandle:
    """Lightweight typed handle returned by :meth:`KnowledgeLayer.writeable`.

    The handle binds a (session, role, scope) triple to its target
    L1 Metagraph + role-graph routing. Capacity code calls
    ``handle.graph().add_node(...)`` etc. for mutation; the handle
    itself never mutates.

    **Phase 33 status:** ``metagraph()`` returns real;
    ``graph`` / ``mint_iri`` / ``validate_node`` / ``validate_xref``
    raise :class:`WriteHandleNotWiredError`. Phase 34 (ADR-0146 +
    ADR-0143) wires the working bodies.

    Attributes:
        role: The role-graph role this handle writes to (e.g.,
            ``"memories"`` for ``capacity:consolidate:mm``;
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
    """

    role: str
    scope: Literal["local", "global"]
    session: Optional["SessionProtocol"]
    _kl: "KnowledgeLayer"
    _metagraph: "Metagraph"

    def metagraph(self) -> "Metagraph":
        """Return the L1 Metagraph this handle writes into (real; not stubbed).

        Read-only state inspection. Used by capacity bodies to derive
        XRef target identifiers and inspect existing nodes before
        mutation. Phase 34's ``graph()`` wiring builds on this.
        """
        return self._metagraph

    def graph(self) -> "Graph":
        """Return the L1 :class:`Graph` for ``role``'s active version.

        **Phase 33 stub:** raises :class:`WriteHandleNotWiredError`.
        Phase 34 (ADR-0146 §Implementation) wires the active-version
        lookup + returns the real :class:`Graph`. L3 capacity bodies
        call ``handle.graph().add_node(...)`` etc. once wired.
        """
        raise WriteHandleNotWiredError(
            f"KLWriteHandle.graph(role={self.role!r}, scope={self.scope!r}) "
            "is not wired at Phase 33 — Phase 34 (ADR-0146) implements "
            "the working body."
        )

    def mint_iri(self, **content: Any) -> str:
        """Mint a stable IRI per the role's IRI builder.

        **Phase 33 stub:** raises :class:`WriteHandleNotWiredError`.
        Version handling is the load-bearing decision Phase 34 must
        make — Phase 17 retirement (ADR-0150 §amendment-3) locked the
        version-dispatch model as IRI-string-only with no active-version
        lookup mechanism. Phase 34 picks how the handle obtains the
        version literal (constructor-bound? from session context?
        per-role default constant?) and unstubs.
        """
        raise WriteHandleNotWiredError(
            f"KLWriteHandle.mint_iri(role={self.role!r}, content={content!r}) "
            "is not wired at Phase 33 — Phase 34 (ADR-0146) resolves the "
            "version-source decision and implements the body."
        )

    def validate_node(
        self,
        *,
        value: Any,
        type_: str,
        **refs: Any,
    ) -> Any:
        """Compose role-appropriate KL semantic validators.

        **Phase 33 stub:** raises :class:`WriteHandleNotWiredError`.
        KL semantic validators land at Phase 36 (ADR-0139 hybrid
        invariant home — structural at L1, semantic at L2). The handle
        method exposes the surface; the validator functions get wired
        when Phase 36 ships ``mindsos_knowledge/validators.py``.
        """
        raise WriteHandleNotWiredError(
            f"KLWriteHandle.validate_node(role={self.role!r}, "
            f"type_={type_!r}) is not wired — Phase 36 (ADR-0139) "
            "ships KL semantic validators."
        )

    def validate_xref(
        self,
        *,
        target_metagraph: "Metagraph",
        target_role: str,
        target_id: str,
        ref_type: str,
    ) -> Any:
        """Validate cross-metagraph XRef target existence + ref_type membership.

        **Phase 33 stub:** raises :class:`WriteHandleNotWiredError`.
        Phase 36 wires the body together with :meth:`validate_node`.
        """
        raise WriteHandleNotWiredError(
            f"KLWriteHandle.validate_xref(role={self.role!r}, "
            f"target_role={target_role!r}, ref_type={ref_type!r}) "
            "is not wired — Phase 36 (ADR-0139) ships KL validators."
        )


__all__ = ["KLWriteHandle"]
