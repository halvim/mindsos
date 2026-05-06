"""``MetagraphSchema`` — metagraph-level schema container (Phase 05b).

Per ADR-0148 + ``confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`` §3.3, a
metagraph schema gathers ``IntergraphEdgeType`` declarations (and in
Phase 05c, ``IntergraphHyperEdgeType``; Phase 05c will also add
``MetaEdgeType`` and ``MetaHyperEdgeType`` here per Pushback 1-C scope
narrowing). The schema attaches to a metagraph by name reference and is
reusable across N metagraphs (Pushback 11-A); one schema attached at
most per metagraph (Pushback 12-A).

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

Phase 05c adds:
* ``MetaEdgeType`` + ``MetaHyperEdgeType`` + ``IntergraphHyperEdgeType``
  vocabularies and matching validators.
* State-file v=2 bump.

Per Pushback 19-B (round 2), eager-attach time stderr warnings on
role-mismatch are emitted by the CLI layer (which has access to the
metagraph's contained graphs); the model layer just provides the
validators.

Per Pushback 23-A (round 4), schema mutation while attached is the
documented Phase 04 footgun; the CLI layer emits the warning at
``add-intergraph-edge-type`` time. The model layer's
:meth:`add_intergraph_edge_type` is a pure registration call.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ..cypher.identifiers import validate_edge_type_identifier
from ..exceptions import PropertyShapeError, UnknownTypeError
from .types import IntergraphEdgeType, PropertyType


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
    ``MetaEdgeType`` + ``MetaHyperEdgeType`` + ``IntergraphHyperEdgeType``
    vocabularies (Pushback 1-C narrowing).
    """

    def __init__(self, *, strict: bool = False) -> None:
        self.strict: bool = strict
        self._intergraph_edge_types: Dict[str, IntergraphEdgeType] = {}

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

    # ── queries ──────────────────────────────────────────────────────────

    @property
    def intergraph_edge_types(self) -> Mapping[str, IntergraphEdgeType]:
        return dict(self._intergraph_edge_types)

    def require_intergraph_edge_type(self, name: str) -> IntergraphEdgeType:
        iet = self._intergraph_edge_types.get(name)
        if iet is None:
            raise UnknownTypeError(f"Unknown intergraph edge type: {name!r}")
        return iet

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

    def __repr__(self) -> str:
        return (
            f"MetagraphSchema(strict={self.strict}, "
            f"intergraph_edge_types={len(self._intergraph_edge_types)})"
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
