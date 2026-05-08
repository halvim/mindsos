"""``MetagraphSchema`` — metagraph-level schema container (Phase 05b + 05c + 05d).

Per ADR-0148 + ``confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`` §3.3, a
metagraph schema gathers ``IntergraphEdgeType`` declarations (Phase 05b)
plus ``IntergraphHyperEdgeType`` declarations (Phase 05c — ADR-0148
amended). Phase 05d (ADR-0014 third amendment) lands ``MetaEdgeType`` +
``MetaHyperEdgeType`` here per the 05c P1-B scope split. The schema
attaches to a metagraph by name reference and is reusable across N
metagraphs (Pushback 11-A); one schema attached at most per metagraph
(Pushback 12-A).

Constructor signature mirrors Phase 04 :class:`Schema` exactly: no
``name`` field on the class — the state-file basename is the identity
that the CLI persists by. ``strict: bool = False`` ships from day one
(Pushback 10-A); gates property-type validation only (Pushback 5-A) —
type-existence is mandatory whenever a schema is attached.

Validation API:

* :meth:`validate_intergraph_edge` enforces type-existence + role/name
  constraints (``allowed_source_types`` / ``allowed_target_types`` /
  ``allowed_source_graphs`` / ``allowed_target_graphs``). Empty
  frozenset on any allowed-* axis means "any" (mirrors :class:`EdgeType`
  empty-set semantics).
* :meth:`validate_intergraph_edge_properties` enforces per-type
  property-type maps when ``strict=True``; early-returns when not
  strict (Phase 04 :meth:`Schema.validate_node_properties` precedent).
* (Phase 05c) :meth:`validate_intergraph_hyperedge` — symmetric for
  the n-ary primitive; enforces type-existence + role/name constraints
  on anchors and members (``allowed_anchor_types`` /
  ``allowed_member_types`` / ``allowed_anchor_graphs`` /
  ``allowed_member_graphs``).
* (Phase 05c) :meth:`validate_intergraph_hyperedge_properties` —
  symmetric strict-only property-type check.

Phase 05d (round-7 P31 A) drops the locked-design fingerprint
mechanism entirely; the v=2 → v=3 schema state-file bump is the only
state surface change. Empty `MetaEdgeType` / `MetaHyperEdgeType` vocab
+ non-strict eager-attach passes silently per round-7 P39 A (mirrors
05b/05c "Pushback 24-hybrid" precedent). `add_metaedge` / `add_metahyperedge`
on empty vocab raises `UnknownTypeError` regardless of strict (preserves
the precedent asymmetry surfaced in 05b for `IntergraphEdgeType`).

Per Pushback 19-B (round 2), eager-attach time stderr warnings on
role-mismatch are emitted by the CLI layer (which has access to the
metagraph's contained graphs); the model layer just provides the
validators.

Per Pushback 23-A (05b round 4) + P12-A (05c carry-forward), schema
mutation while attached is the documented Phase 04 footgun; the CLI
layer emits the warning at ``add-intergraph-edge-type`` /
``add-intergraph-hyperedge-type`` time. The model layer's
:meth:`add_intergraph_edge_type` / :meth:`add_intergraph_hyperedge_type`
are pure registration calls.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from ..cypher.identifiers import validate_edge_type_identifier
from ..exceptions import PropertyShapeError, UnknownTypeError
from .types import (
    IntergraphEdgeType,
    IntergraphHyperEdgeType,
    MetaEdgeType,
    MetaHyperEdgeType,
    PropertyType,
)


_TYPE_PY_MAP = {
    PropertyType.STRING: (str,),
    PropertyType.INT: (int,),
    PropertyType.FLOAT: (float, int),  # ints coerce to floats in FalkorDB
    PropertyType.BOOL: (bool,),
    PropertyType.LIST_STRING: (list,),
    PropertyType.LIST_INT: (list,),
    PropertyType.LIST_FLOAT: (list,),
    PropertyType.LIST_BOOL: (list,),
}


class MetagraphSchema:
    """Metagraph-level schema container with optional strict property typing.

    Phase 05b ships ``IntergraphEdgeType`` only. Phase 05c extends with
    ``IntergraphHyperEdgeType`` (P1-B scope narrowing — meta-vocabs
    further deferred to Phase 05d). Phase 05d adds ``MetaEdgeType`` +
    ``MetaHyperEdgeType``.
    """

    def __init__(self, *, strict: bool = False) -> None:
        self.strict: bool = strict
        self._intergraph_edge_types: Dict[str, IntergraphEdgeType] = {}
        # Phase 05c — IntergraphHyperEdgeType vocabulary (ADR-0148 amended).
        self._intergraph_hyperedge_types: Dict[
            str, IntergraphHyperEdgeType,
        ] = {}
        # Phase 05d — MetaEdgeType + MetaHyperEdgeType vocabularies
        # (ADR-0014 third amendment). The 4-vocab Cypher namespace policy
        # (P2 A): same `name` MAY appear in all four vocabularies; same-
        # name lookup hint per P38 B is informational only.
        self._meta_edge_types: Dict[str, MetaEdgeType] = {}
        self._meta_hyperedge_types: Dict[str, MetaHyperEdgeType] = {}

    # ── registration ─────────────────────────────────────────────────────

    def add_intergraph_edge_type(
        self, iet: IntergraphEdgeType
    ) -> IntergraphEdgeType:
        """Register an :class:`IntergraphEdgeType`.

        Raises:
            CypherError: ``iet.name`` fails ADR-0021 cypher rel-type regex.
            UnknownTypeError: duplicate name.
        """
        validate_edge_type_identifier(iet.name)
        if iet.name in self._intergraph_edge_types:
            raise UnknownTypeError(
                f"IntergraphEdge type {iet.name!r} already registered"
            )
        self._intergraph_edge_types[iet.name] = iet
        return iet

    def add_intergraph_hyperedge_type(
        self, iht: IntergraphHyperEdgeType
    ) -> IntergraphHyperEdgeType:
        """Register an :class:`IntergraphHyperEdgeType` (Phase 05c).

        Raises:
            CypherError: ``iht.name`` fails ADR-0021 cypher rel-type regex.
            UnknownTypeError: duplicate name. Note that
                ``IntergraphEdgeType`` and ``IntergraphHyperEdgeType``
                vocabularies share a CYPHER NAMESPACE for FalkorDB
                relationship types but are tracked in *separate* dicts on
                the schema — the same name MAY appear in both vocabularies
                (the binary case uses :class:`IntergraphEdgeType`; the
                n-ary case uses :class:`IntergraphHyperEdgeType`). Phase
                05c does NOT cross-check name collisions across
                vocabularies; future Phase 11 schema-migration may flag
                them.
        """
        validate_edge_type_identifier(iht.name)
        if iht.name in self._intergraph_hyperedge_types:
            raise UnknownTypeError(
                f"IntergraphHyperEdge type {iht.name!r} already registered"
            )
        self._intergraph_hyperedge_types[iht.name] = iht
        return iht

    # ── queries ──────────────────────────────────────────────────────────

    @property
    def intergraph_edge_types(self) -> Mapping[str, IntergraphEdgeType]:
        return dict(self._intergraph_edge_types)

    def require_intergraph_edge_type(self, name: str) -> IntergraphEdgeType:
        iet = self._intergraph_edge_types.get(name)
        if iet is None:
            raise UnknownTypeError(f"Unknown intergraph edge type: {name!r}")
        return iet

    @property
    def intergraph_hyperedge_types(
        self,
    ) -> Mapping[str, IntergraphHyperEdgeType]:
        """Defensive copy of registered :class:`IntergraphHyperEdgeType`."""
        return dict(self._intergraph_hyperedge_types)

    def require_intergraph_hyperedge_type(
        self, name: str
    ) -> IntergraphHyperEdgeType:
        """Look up an :class:`IntergraphHyperEdgeType` or raise.

        Raises:
            UnknownTypeError: type ``name`` not registered.
        """
        iht = self._intergraph_hyperedge_types.get(name)
        if iht is None:
            raise UnknownTypeError(
                f"Unknown intergraph hyperedge type: {name!r}"
            )
        return iht

    # ── validation ───────────────────────────────────────────────────────

    def validate_intergraph_edge(
        self,
        type_name: str,
        source_node_type: str,
        target_node_type: str,
        source_graph_role: "str | None",
        target_graph_role: "str | None",
    ) -> None:
        """Enforce type-existence + role/name constraints (Pushback 4-A + 5-A).

        Always runs (independent of ``self.strict``). Empty frozenset on
        any allowed-* axis means "any" (mirror :class:`EdgeType` empty-set
        semantics). ``Graph.role=None`` is unmatchable when the
        ``allowed_*_graphs`` constraint is non-empty (Python set
        membership semantics: ``None not in frozenset({"x"})``).

        Raises:
            UnknownTypeError: type not registered, or any constraint
                violated. Error message names which constraint failed.
        """
        iet = self.require_intergraph_edge_type(type_name)
        if iet.allowed_source_types and source_node_type not in iet.allowed_source_types:
            raise UnknownTypeError(
                f"IntergraphEdge type {type_name!r} does not permit source "
                f"node type {source_node_type!r} "
                f"(allowed_source_types: {sorted(iet.allowed_source_types)})"
            )
        if iet.allowed_target_types and target_node_type not in iet.allowed_target_types:
            raise UnknownTypeError(
                f"IntergraphEdge type {type_name!r} does not permit target "
                f"node type {target_node_type!r} "
                f"(allowed_target_types: {sorted(iet.allowed_target_types)})"
            )
        if iet.allowed_source_graphs and source_graph_role not in iet.allowed_source_graphs:
            raise UnknownTypeError(
                f"IntergraphEdge type {type_name!r} does not permit source "
                f"graph role {source_graph_role!r} "
                f"(allowed_source_graphs: {sorted(iet.allowed_source_graphs)})"
            )
        if iet.allowed_target_graphs and target_graph_role not in iet.allowed_target_graphs:
            raise UnknownTypeError(
                f"IntergraphEdge type {type_name!r} does not permit target "
                f"graph role {target_graph_role!r} "
                f"(allowed_target_graphs: {sorted(iet.allowed_target_graphs)})"
            )

    def validate_intergraph_edge_properties(
        self, type_name: str, properties: Mapping[str, Any]
    ) -> None:
        """Enforce strict per-type property-type checks when ``strict=True``.

        Phase 04 :meth:`Schema.validate_node_properties` precedent: this
        method early-returns when ``not self.strict``. Type-existence is
        re-checked here (so callers can invoke this as a standalone
        validator without first calling :meth:`validate_intergraph_edge`).
        """
        if not self.strict:
            return
        iet = self.require_intergraph_edge_type(type_name)
        for key, value in properties.items():
            if key.startswith("ref:"):
                # ref:* validated upstream as a UUID-shaped str.
                continue
            expected = iet.property_types.get(key)
            if expected is None:
                # Under strict: unknown keys allowed only if declared
                # map is empty (type author opted out of strict typing
                # for this type).
                if iet.property_types:
                    raise PropertyShapeError(
                        f"intergraph_edge type {type_name!r} has strict "
                        f"property typing but property {key!r} is not "
                        f"declared"
                    )
                continue
            if not _matches_type(value, expected):
                raise PropertyShapeError(
                    f"intergraph_edge type {type_name!r} property {key!r} "
                    f"expected {expected.value}, got {type(value).__name__}"
                )

    # ── n-ary intergraph hyperedge validation (Phase 05c) ────────────────

    def validate_intergraph_hyperedge(
        self,
        type_name: str,
        anchor_node_types: Iterable[str],
        member_node_types: Iterable[str],
        anchor_graph_roles: Iterable["str | None"],
        member_graph_roles: Iterable["str | None"],
    ) -> None:
        """Enforce type-existence + role/name constraints for n-ary primitive (Phase 05c).

        Always runs (independent of ``self.strict``). Empty frozenset on
        any allowed-* axis means "any" (mirror :class:`IntergraphEdgeType`
        empty-set semantics). ``Graph.role=None`` is unmatchable when the
        ``allowed_*_graphs`` constraint is non-empty (Python set
        membership: ``None not in frozenset({"x"})``).

        The four iterables must each carry one entry per anchor or
        member; iteration order does not matter (the check is set
        membership, not positional). Per P5-refined, the factory-side
        canonicalization step has already normalized order/dedup BEFORE
        this validator runs, so the iterables reflect canonical state.

        Raises:
            UnknownTypeError: type not registered, or any constraint
                violated. Error message names which constraint failed
                AND which side (anchor / member) failed.
        """
        iht = self.require_intergraph_hyperedge_type(type_name)
        # Anchor type-name constraints.
        if iht.allowed_anchor_types:
            for ant in anchor_node_types:
                if ant not in iht.allowed_anchor_types:
                    raise UnknownTypeError(
                        f"IntergraphHyperEdge type {type_name!r} does not "
                        f"permit anchor node type {ant!r} "
                        f"(allowed_anchor_types: "
                        f"{sorted(iht.allowed_anchor_types)})"
                    )
        # Member type-name constraints.
        if iht.allowed_member_types:
            for mnt in member_node_types:
                if mnt not in iht.allowed_member_types:
                    raise UnknownTypeError(
                        f"IntergraphHyperEdge type {type_name!r} does not "
                        f"permit member node type {mnt!r} "
                        f"(allowed_member_types: "
                        f"{sorted(iht.allowed_member_types)})"
                    )
        # Anchor graph-role constraints.
        if iht.allowed_anchor_graphs:
            for arole in anchor_graph_roles:
                if arole not in iht.allowed_anchor_graphs:
                    raise UnknownTypeError(
                        f"IntergraphHyperEdge type {type_name!r} does not "
                        f"permit anchor graph role {arole!r} "
                        f"(allowed_anchor_graphs: "
                        f"{sorted(iht.allowed_anchor_graphs)})"
                    )
        # Member graph-role constraints.
        if iht.allowed_member_graphs:
            for mrole in member_graph_roles:
                if mrole not in iht.allowed_member_graphs:
                    raise UnknownTypeError(
                        f"IntergraphHyperEdge type {type_name!r} does not "
                        f"permit member graph role {mrole!r} "
                        f"(allowed_member_graphs: "
                        f"{sorted(iht.allowed_member_graphs)})"
                    )

    def validate_intergraph_hyperedge_properties(
        self, type_name: str, properties: Mapping[str, Any]
    ) -> None:
        """Enforce strict per-type property-type checks when ``strict=True`` (Phase 05c).

        Mirror of :meth:`validate_intergraph_edge_properties`. Phase 04
        :meth:`Schema.validate_node_properties` precedent: this method
        early-returns when ``not self.strict``. Type-existence is
        re-checked here so callers can invoke this as a standalone
        validator without first calling
        :meth:`validate_intergraph_hyperedge`.
        """
        if not self.strict:
            return
        iht = self.require_intergraph_hyperedge_type(type_name)
        for key, value in properties.items():
            if key.startswith("ref:"):
                # ref:* validated upstream as a UUID-shaped str.
                continue
            expected = iht.property_types.get(key)
            if expected is None:
                # Under strict: unknown keys allowed only if declared
                # map is empty (type author opted out of strict typing
                # for this type). Mirror IntergraphEdgeType precedent.
                if iht.property_types:
                    raise PropertyShapeError(
                        f"intergraph_hyperedge type {type_name!r} has strict "
                        f"property typing but property {key!r} is not "
                        f"declared"
                    )
                continue
            if not _matches_type(value, expected):
                raise PropertyShapeError(
                    f"intergraph_hyperedge type {type_name!r} property "
                    f"{key!r} expected {expected.value}, got "
                    f"{type(value).__name__}"
                )

    # ── Phase 05d — meta-vocab registration ──────────────────────────────

    def add_meta_edge_type(self, met: MetaEdgeType) -> MetaEdgeType:
        """Register a :class:`MetaEdgeType` (Phase 05d — ADR-0014 third amendment).

        Raises:
            CypherError: ``met.name`` fails ADR-0021 cypher rel-type regex.
            UnknownTypeError: duplicate name. Note that the four vocabs
                share the FalkorDB Cypher relationship namespace but are
                tracked in separate dicts (4-vocab namespace policy P2 A);
                duplicate-detection runs WITHIN the MetaEdgeType vocab
                only.
        """
        validate_edge_type_identifier(met.name)
        if met.name in self._meta_edge_types:
            raise UnknownTypeError(
                f"MetaEdge type {met.name!r} already registered"
            )
        self._meta_edge_types[met.name] = met
        return met

    def add_meta_hyperedge_type(
        self, mht: MetaHyperEdgeType
    ) -> MetaHyperEdgeType:
        """Register a :class:`MetaHyperEdgeType` (Phase 05d — ADR-0014 third amendment).

        :class:`MetaHyperEdgeType` deliberately omits the ``ordered``
        field present on :class:`IntergraphHyperEdgeType` because
        :class:`MetaHyperEdge` enforces graph-set uniqueness at
        ``__post_init__`` (no duplicate-preservation use case for
        graph-level n-ary edges). See memory
        ``reference_mindsos_four_edge_primitives.md`` for the canonical
        primitive distinction.

        Raises:
            CypherError: ``mht.name`` fails ADR-0021 cypher rel-type regex.
            UnknownTypeError: duplicate name within MetaHyperEdgeType vocab.
        """
        validate_edge_type_identifier(mht.name)
        if mht.name in self._meta_hyperedge_types:
            raise UnknownTypeError(
                f"MetaHyperEdge type {mht.name!r} already registered"
            )
        self._meta_hyperedge_types[mht.name] = mht
        return mht

    @property
    def meta_edge_types(self) -> Mapping[str, MetaEdgeType]:
        """Defensive copy of registered :class:`MetaEdgeType`."""
        return dict(self._meta_edge_types)

    def require_meta_edge_type(self, name: str) -> MetaEdgeType:
        """Look up a :class:`MetaEdgeType` or raise.

        Per round-7 P38 B (informational cross-vocab hint, no editorial
        recommendation): when ``name`` is missing in ``MetaEdgeType`` but
        present in ``IntergraphEdgeType``, the error message reports the
        sibling registration as an information point. The 4-vocab
        namespace policy (P2 A) explicitly allows same-name registration
        across vocabs; the hint does not second-guess that choice.

        Raises:
            UnknownTypeError: type ``name`` not registered.
        """
        met = self._meta_edge_types.get(name)
        if met is None:
            sibling = (
                "IntergraphEdgeType"
                if name in self._intergraph_edge_types
                else None
            )
            hint = (
                f" Name {name!r} is registered in {sibling} but not in "
                f"MetaEdgeType."
                if sibling
                else ""
            )
            raise UnknownTypeError(
                f"Unknown meta-edge type: {name!r}.{hint}"
            )
        return met

    @property
    def meta_hyperedge_types(self) -> Mapping[str, MetaHyperEdgeType]:
        """Defensive copy of registered :class:`MetaHyperEdgeType`."""
        return dict(self._meta_hyperedge_types)

    def require_meta_hyperedge_type(self, name: str) -> MetaHyperEdgeType:
        """Look up a :class:`MetaHyperEdgeType` or raise.

        Per round-7 P38 B (informational cross-vocab hint): when ``name``
        is missing in ``MetaHyperEdgeType`` but present in
        ``IntergraphHyperEdgeType``, the error reports the sibling.

        Raises:
            UnknownTypeError: type ``name`` not registered.
        """
        mht = self._meta_hyperedge_types.get(name)
        if mht is None:
            sibling = (
                "IntergraphHyperEdgeType"
                if name in self._intergraph_hyperedge_types
                else None
            )
            hint = (
                f" Name {name!r} is registered in {sibling} but not in "
                f"MetaHyperEdgeType."
                if sibling
                else ""
            )
            raise UnknownTypeError(
                f"Unknown meta-hyperedge type: {name!r}.{hint}"
            )
        return mht

    # ── Phase 05d — meta-vocab validation ────────────────────────────────

    def validate_meta_edge(
        self,
        type_name: str,
        source_graph_role: "str | None",
        target_graph_role: "str | None",
    ) -> None:
        """Enforce type-existence + role constraints for meta-edge (Phase 05d).

        Always runs (independent of ``self.strict``). Empty frozenset on
        any allowed-* axis means "any". ``Graph.role=None`` is
        unmatchable when the corresponding ``allowed_*_graphs`` is
        non-empty (Python set membership semantics).

        Raises:
            UnknownTypeError: type not registered, or any role constraint
                violated. Error message names which constraint failed.
        """
        met = self.require_meta_edge_type(type_name)
        if (
            met.allowed_source_graphs
            and source_graph_role not in met.allowed_source_graphs
        ):
            raise UnknownTypeError(
                f"MetaEdge type {type_name!r} does not permit source "
                f"graph role {source_graph_role!r} "
                f"(allowed_source_graphs: "
                f"{sorted(met.allowed_source_graphs)})"
            )
        if (
            met.allowed_target_graphs
            and target_graph_role not in met.allowed_target_graphs
        ):
            raise UnknownTypeError(
                f"MetaEdge type {type_name!r} does not permit target "
                f"graph role {target_graph_role!r} "
                f"(allowed_target_graphs: "
                f"{sorted(met.allowed_target_graphs)})"
            )

    def validate_meta_edge_properties(
        self, type_name: str, properties: Mapping[str, Any]
    ) -> None:
        """Enforce strict per-type property-type checks when ``strict=True``.

        Mirrors :meth:`validate_intergraph_edge_properties`. Phase 04
        :meth:`Schema.validate_node_properties` precedent: this method
        early-returns when ``not self.strict``. Type-existence is
        re-checked here so callers can invoke standalone.
        """
        if not self.strict:
            return
        met = self.require_meta_edge_type(type_name)
        for key, value in properties.items():
            if key.startswith("ref:"):
                continue
            expected = met.property_types.get(key)
            if expected is None:
                if met.property_types:
                    raise PropertyShapeError(
                        f"meta-edge type {type_name!r} has strict "
                        f"property typing but property {key!r} is not "
                        f"declared"
                    )
                continue
            if not _matches_type(value, expected):
                raise PropertyShapeError(
                    f"meta-edge type {type_name!r} property {key!r} "
                    f"expected {expected.value}, got {type(value).__name__}"
                )

    def validate_meta_hyperedge(
        self,
        type_name: str,
        member_graph_roles: Iterable["str | None"],
    ) -> None:
        """Enforce type-existence + role constraints for meta-hyperedge (Phase 05d).

        Always runs (independent of ``self.strict``). The iterable
        carries one entry per member graph; iteration order is
        non-positional (set membership). Empty frozenset on
        ``allowed_member_graphs`` means "any".

        Raises:
            UnknownTypeError: type not registered, or any member role
                constraint violated. Error message names the offending
                role.
        """
        mht = self.require_meta_hyperedge_type(type_name)
        if mht.allowed_member_graphs:
            for mrole in member_graph_roles:
                if mrole not in mht.allowed_member_graphs:
                    raise UnknownTypeError(
                        f"MetaHyperEdge type {type_name!r} does not "
                        f"permit member graph role {mrole!r} "
                        f"(allowed_member_graphs: "
                        f"{sorted(mht.allowed_member_graphs)})"
                    )

    def validate_meta_hyperedge_properties(
        self, type_name: str, properties: Mapping[str, Any]
    ) -> None:
        """Enforce strict per-type property-type checks when ``strict=True``.

        Mirrors :meth:`validate_meta_edge_properties` symmetric for the
        n-ary primitive.
        """
        if not self.strict:
            return
        mht = self.require_meta_hyperedge_type(type_name)
        for key, value in properties.items():
            if key.startswith("ref:"):
                continue
            expected = mht.property_types.get(key)
            if expected is None:
                if mht.property_types:
                    raise PropertyShapeError(
                        f"meta-hyperedge type {type_name!r} has strict "
                        f"property typing but property {key!r} is not "
                        f"declared"
                    )
                continue
            if not _matches_type(value, expected):
                raise PropertyShapeError(
                    f"meta-hyperedge type {type_name!r} property "
                    f"{key!r} expected {expected.value}, got "
                    f"{type(value).__name__}"
                )

    def __repr__(self) -> str:
        return (
            f"MetagraphSchema(strict={self.strict}, "
            f"intergraph_edge_types={len(self._intergraph_edge_types)}, "
            f"intergraph_hyperedge_types="
            f"{len(self._intergraph_hyperedge_types)}, "
            f"meta_edge_types={len(self._meta_edge_types)}, "
            f"meta_hyperedge_types={len(self._meta_hyperedge_types)})"
        )


def _matches_type(value: Any, expected: PropertyType) -> bool:
    """Per-PropertyType type check. Mirror ``schema.py:_matches_type``."""
    py_types = _TYPE_PY_MAP[expected]
    if not isinstance(value, py_types):
        return False
    if expected == PropertyType.LIST_STRING:
        return all(isinstance(x, str) for x in value)
    if expected == PropertyType.LIST_INT:
        return all(isinstance(x, int) and not isinstance(x, bool) for x in value)
    if expected == PropertyType.LIST_FLOAT:
        return all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in value)
    if expected == PropertyType.LIST_BOOL:
        return all(isinstance(x, bool) for x in value)
    if expected == PropertyType.INT:
        return not isinstance(value, bool)
    return True
