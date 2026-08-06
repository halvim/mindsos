"""``IntergraphHyperEdge`` — n-ary node↔node edge across graphs in one Metagraph.

Phase 05c primitive (ADR-0148 amended for n-ary). Per
``confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`` §2.2 + 2026-05-06
amendment block, an ``IntergraphHyperEdge`` is a directed n-ary edge
between ``n`` *anchor* nodes and ``m`` *member* nodes across one or more
graphs within the same metagraph (n ≥ 1, m ≥ 1, NOT 1-to-1 — 1-to-1 case
uses :class:`IntergraphEdge`). The metagraph owns the edge (registers in
the metagraph's :class:`IdentityRegistry` per ADR-0020; persists in the
metagraph state file). Per Phase 05c P1-B scope split, this file ships
the n-ary primitive plus the replace-only update factory; meta-vocabs
(``MetaEdgeType`` + ``MetaHyperEdgeType``) defer to Phase 05d.

Locked Phase 05c design picks reflected here (PHASE_MAP §5 row appendix):

* **P2-refined + P27 (this chat A)** — strict ``__setattr__`` scope.
  ``compositional`` is always immutable post-init; ``anchors`` /
  ``members`` / ``properties`` are also always immutable on direct user
  mutation, regardless of the ``compositional`` flag value. The factory
  ``Metagraph.update_intergraph_hyperedge`` uses ``object.__setattr__``
  to bypass the gate for legitimate, validated updates ("set-via-factory"
  contract). Tuple-conversion of ``anchors`` and ``members`` happens at
  ``__post_init__`` regardless of compositional flag — eliminates
  list-mutation hole even for non-compositional hyperedges.
* **P14-A + P32 (this chat A)** — ADR-0021 cypher rel-type regex on
  ``type_name`` is enforced both at the factory inline (step 5 of the
  16-step validation order) AND at ``__post_init__`` (belt-and-suspenders
  for direct-construction safety, e.g. rehydration paths and tests). The
  factory's inline check fires before construction so a CypherError
  surfaces at step 5; the ``__post_init__`` re-check defends the
  rehydration path. Both paths converge on the same regex.
* **P5-refined / P9-A** — ``ordered`` is type-driven (set-vs-list), but
  the ``ordered`` flag lives on :class:`IntergraphHyperEdgeType`, NOT on
  the dataclass instance. Canonicalization (sort+dedup if
  ``ordered=False``) happens in the factory before construction; the
  dataclass receives already-canonicalized data. Direct-construction
  paths (rehydration / tests) bypass canonicalization and store
  whatever-was-passed.
* **P8-A — RETIRED at CORE-C2R2** (ADR-0205 §amendment-3.1). The
  ``compositional=True`` + ``ordered=False`` refusal used to be enforced
  at the factory boundary (validation step 10 of the 16-step order); it is
  lifted, and the combination is now legal. The ground: ``ordered``
  expresses a TOTAL order over members, while a plan's milestones are a
  SET whose PARTIAL order lives in sibling dependency links (ADR-0206 §2),
  so the refusal made a plan with two parallel milestones inexpressible.
  The dataclass boundary is unchanged and always accepted
  ``compositional=True``; there is simply no factory gate now.
* **P19-A** — refusal of ``update_intergraph_hyperedge`` calls that
  would collapse to 1-to-1 cardinality is enforced at the factory's
  step 8 cardinality check on the resolved replacement values. The
  dataclass ``__post_init__`` enforces the same NOT 1-to-1 rule for
  direct-construction safety (n=m=1 inputs raise ``SchemaError`` here).

Soft-delete fields ``deprecated_at`` / ``disputed_at`` (ADR-0133) are
**NOT shipped in 05c** — Phase 10 lands the substrate uniformly across
all 5 edge variants per SOFT_DELETE_AUDIT_NOTE, mirror 05b precedent.

Cardinality + overlap rules (enforced at ``__post_init__``):

* ``len(anchors) ≥ 1`` — at least one anchor.
* ``len(members) ≥ 1`` — at least one member.
* ``len(anchors) > 1 OR len(members) > 1`` — NOT 1-to-1; use
  :class:`IntergraphEdge` for the binary 1-to-1 case.
* No ``(graph_id, node_id)`` pair appears in both ``anchors`` and
  ``members`` — anchor-member overlap forbidden.
* Duplicates **within** a side are allowed when the schema declares
  ``ordered=True`` (the cat=c+a+t case where word "letter" has
  ``members=[(lg,l), (lg,e), (lg,t), (lg,t), (lg,e), (lg,r)]``).
  Duplicates within a side under ``ordered=False`` are silently deduped
  by the factory's canonicalization step; the dataclass sees the
  canonicalized form.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional, Tuple

from ..cypher.identifiers import validate_edge_type_identifier
from ..exceptions import CompositionalImmutableError, SchemaError
from .identity import generate_uuid


#: Field names that are immutable post-``__post_init__``. Per P2-refined
#: + P27 (this chat A), all four are always blocked on direct user
#: mutation; the factory uses ``object.__setattr__`` to bypass the gate
#: for legitimate (validated) updates ("set-via-factory" contract).
_FROZEN_POST_INIT_FIELDS: FrozenSet[str] = frozenset({
    "compositional", "anchors", "members", "properties",
    "type_name", "edge_id", "label",
})


# ── IntergraphHyperEdge dataclass (P2-refined + P14-A + P32) ────────────────


@dataclass(kw_only=True)
class IntergraphHyperEdge:
    """A directed n-ary edge between anchor nodes and member nodes across graphs.

    Phase 05c slim shape (P1-B scope — n-ary only; meta-vocabs deferred
    to 05d). Field ordering does not matter since ``kw_only=True``
    (carry-forward from 05a P8 + 05b pattern). ``__post_init__`` runs
    tuple-conversion of ``anchors`` / ``members``, ADR-0021 cypher
    rel-type regex on ``type_name``, cardinality check, and anchor-member
    overlap check (P14-A + P19-A direct-construction defense).
    ``__setattr__`` enforces strict post-init immutability per P27 pick A
    on the four structural fields plus type_name/edge_id/label
    (set-at-create).

    Attributes:
        anchors: ``Tuple[Tuple[str, str], ...]`` — n ≥ 1
            ``(graph_id, node_id)`` pairs identifying the "identity-bearing"
            side of the hyperedge (the cat in cat=c+a+t). Same-graph or
            cross-graph anchors allowed. Stored as tuple-of-tuples
            post-``__post_init__`` (tuple-conversion regardless of
            compositional flag — eliminates list-mutation hole).
        members: ``Tuple[Tuple[str, str], ...]`` — m ≥ 1
            ``(graph_id, node_id)`` pairs identifying the "constituent"
            side (the c, a, t in cat=c+a+t).
        type_name: Cypher rel-type (validated against ADR-0021 regex
            in ``__post_init__``).
        compositional: Identity-bearing composition flag. Default
            ``False``. Immutable post-construction. When ``True``,
            removal/structural-mutation/property-mutation/deprecation raise
            :class:`CompositionalImmutableError`. ``compositional=True``
            with ``type.ordered=False`` is **legal since CORE-C2R2** — the
            P8-A refusal at validation step 10 is retired (ADR-0205
            §amendment-3.1).
        edge_id: Auto-minted UUID4 if not supplied. Factory
            ``Metagraph.add_intergraph_hyperedge`` mints via
            ``mg.mint_id("intergraph_hyperedge")`` (carry-forward from
            05b Pushback 14-A); direct construction (rehydration / tests)
            uses the field default.
        label: Optional human-readable label. Set-at-create per 05b
            Pushback 31-A precedent.
        properties: Namespaced property bag; reserved-key-aware via
            :func:`mindsos_core.schema.validation.validate_user_properties`.
    """

    anchors: Tuple[Tuple[str, str], ...]
    members: Tuple[Tuple[str, str], ...]
    type_name: str
    compositional: bool = False
    edge_id: str = field(default_factory=generate_uuid)
    label: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    _version: int = 1  # Phase 07 — ADR-0127 OCC.

    def __post_init__(self) -> None:
        # P2-refined — tuple-conversion of ``anchors`` and ``members``
        # regardless of compositional flag. Idempotent on already-tuple
        # input; converts list-of-tuple, list-of-list, tuple-of-list to
        # tuple-of-tuples uniformly. ``object.__setattr__`` skips our
        # ``__setattr__`` override (which enforces post-init immutability;
        # at this point ``_initialized`` is still unset so the override
        # would let it through, but using object.__setattr__ keeps the
        # init path uniform with the factory's update path).
        object.__setattr__(
            self, "anchors", tuple(tuple(p) for p in self.anchors),
        )
        object.__setattr__(
            self, "members", tuple(tuple(p) for p in self.members),
        )

        # P14-A step 5 + P32 belt-and-suspenders — cypher rel-type regex
        # at dataclass boundary so direct construction (rehydration paths,
        # tests) cannot bypass the invariant. The factory
        # ``Metagraph.add_intergraph_hyperedge`` ALSO validates inline at
        # step 5 of the 16-step order BEFORE construction so the
        # CypherError surfaces with factory-context error text. Both
        # paths converge here.
        validate_edge_type_identifier(self.type_name)

        # P14-A direct-construction defense — cardinality (n ≥ 1, m ≥ 1,
        # NOT 1-to-1). The factory enforces this on the canonicalized
        # values at step 8; this check defends the direct-construction
        # path (rehydration / tests / fixtures) which bypasses
        # canonicalization. The factory's step 7 canonicalization
        # cannot make a valid input invalid, so the constraint here is
        # equivalent.
        n = len(self.anchors)
        m = len(self.members)
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
                f"IntergraphHyperEdge is NOT 1-to-1 "
                f"(use IntergraphEdge for the binary 1-1 case); "
                f"got n={n} anchors and m={m} members."
            )

        # P14-A step 9 — anchor-member overlap forbidden. Enforced here
        # for direct-construction safety; the factory enforces on
        # canonical anchors/members at step 9. Self-referential
        # compositions are out-of-contract.
        anchor_set = set(self.anchors)
        member_set = set(self.members)
        overlap = anchor_set & member_set
        if overlap:
            raise SchemaError(
                f"IntergraphHyperEdge anchor-member overlap forbidden: "
                f"{sorted(overlap)!r} appear(s) in both anchors and members."
            )

        # P2-refined + P27 (this chat A) — mark instance as initialised
        # so ``__setattr__`` below knows to enforce post-init immutability
        # on the seven frozen fields. Stash via ``object.__setattr__`` to
        # bypass our own override.
        object.__setattr__(self, "_initialized", True)

    def __setattr__(self, name: str, value: Any) -> None:
        # P27 (this chat A) — strict ``__setattr__`` scope. Post-init,
        # the seven frozen fields raise
        # :class:`CompositionalImmutableError` on any direct user
        # mutation. The factory ``Metagraph.update_intergraph_hyperedge``
        # uses ``object.__setattr__`` to bypass the gate for legitimate
        # (validated) updates — set-via-factory contract.
        if (
            name in _FROZEN_POST_INIT_FIELDS
            and getattr(self, "_initialized", False)
        ):
            raise CompositionalImmutableError(
                f"IntergraphHyperEdge.{name} is immutable post-create "
                f"(P2-refined + P27). Edge "
                f"{getattr(self, 'edge_id', '?')[:8]}: use "
                f"Metagraph.update_intergraph_hyperedge for structural "
                f"or property updates (refused on compositional=True per "
                f"design §4.3)."
            )
        object.__setattr__(self, name, value)

    def __hash__(self) -> int:
        return hash(self.edge_id)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, IntergraphHyperEdge)
            and self.edge_id == other.edge_id
        )

    def __repr__(self) -> str:
        flag = " compositional" if self.compositional else ""
        return (
            f"IntergraphHyperEdge(type={self.type_name!r}, "
            f"n_anchors={len(self.anchors)}, n_members={len(self.members)}"
            f"{flag}, id={self.edge_id[:8]})"
        )
