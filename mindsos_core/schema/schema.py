"""The ``Schema`` class.

A ``Schema`` gathers a set of ``NodeType`` and ``EdgeType`` declarations
and exposes a few cheap validation entry points used by the ``Graph``
primitive when adding or updating elements. Per-schema strictness
(``strict=True``) additionally enforces the property-type maps declared
on ``NodeType`` / ``EdgeType``; with ``strict=False`` (the default),
types are registered but property values are not individually
type-checked — only the generic primitive/reserved-key rules from
:mod:`mindsos_core.schema.validation` apply.

Phase 04 slim port keeps the parent ctor verbatim
(``__init__(*, strict: bool = False)``). The Phase 04 CLI persists
schemas to ``${MINDSOS_STATE_DIR}/schema-<name>.json``; the basename
``<name>`` is the schema's identity for the CLI, NOT a field on this
class.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ..cypher.identifiers import validate_edge_type_identifier
from ..exceptions import PropertyShapeError, UnknownTypeError
from .types import EdgeType, NodeType, PropertyType


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


class Schema:
    """Collection of node/edge types with optional strict property typing."""

    def __init__(self, *, strict: bool = False) -> None:
        self.strict: bool = strict
        self._node_types: Dict[str, NodeType] = {}
        self._edge_types: Dict[str, EdgeType] = {}

    # ── registration ─────────────────────────────────────────────────────

    def add_node_type(self, nt: NodeType) -> NodeType:
        if nt.name in self._node_types:
            raise UnknownTypeError(f"Node type {nt.name!r} already registered")
        self._node_types[nt.name] = nt
        return nt

    def add_edge_type(self, et: EdgeType) -> EdgeType:
        validate_edge_type_identifier(et.name)
        if et.name in self._edge_types:
            raise UnknownTypeError(f"Edge type {et.name!r} already registered")
        for s in et.allowed_sources:
            if s not in self._node_types:
                raise UnknownTypeError(
                    f"EdgeType {et.name!r} allowed_source {s!r} is not a registered NodeType"
                )
        for t in et.allowed_targets:
            if t not in self._node_types:
                raise UnknownTypeError(
                    f"EdgeType {et.name!r} allowed_target {t!r} is not a registered NodeType"
                )
        self._edge_types[et.name] = et
        return et

    # ── queries ──────────────────────────────────────────────────────────

    @property
    def node_types(self) -> Mapping[str, NodeType]:
        return dict(self._node_types)

    @property
    def edge_types(self) -> Mapping[str, EdgeType]:
        return dict(self._edge_types)

    def require_node_type(self, name: str) -> NodeType:
        nt = self._node_types.get(name)
        if nt is None:
            raise UnknownTypeError(f"Unknown node type: {name!r}")
        return nt

    def require_edge_type(self, name: str) -> EdgeType:
        et = self._edge_types.get(name)
        if et is None:
            raise UnknownTypeError(f"Unknown edge type: {name!r}")
        return et

    # ── validation ───────────────────────────────────────────────────────

    def validate_edge(
        self,
        edge_type_name: str,
        source_type_name: str,
        target_type_name: str,
    ) -> None:
        et = self.require_edge_type(edge_type_name)
        if et.allowed_sources and source_type_name not in et.allowed_sources:
            raise UnknownTypeError(
                f"Edge type {edge_type_name!r} does not permit source "
                f"{source_type_name!r} (allowed: {sorted(et.allowed_sources)})"
            )
        if et.allowed_targets and target_type_name not in et.allowed_targets:
            raise UnknownTypeError(
                f"Edge type {edge_type_name!r} does not permit target "
                f"{target_type_name!r} (allowed: {sorted(et.allowed_targets)})"
            )

    def validate_node_properties(
        self, type_name: str, properties: Mapping[str, Any]
    ) -> None:
        """Enforce strict property-type checks when ``strict=True``."""
        if not self.strict:
            return
        nt = self.require_node_type(type_name)
        self._check_property_types("node", nt.name, nt.property_types, properties)

    def validate_edge_properties(
        self, type_name: str, properties: Mapping[str, Any]
    ) -> None:
        if not self.strict:
            return
        et = self.require_edge_type(type_name)
        self._check_property_types("edge", et.name, et.property_types, properties)

    # ── helpers ──────────────────────────────────────────────────────────

    def _check_property_types(
        self,
        scope: str,
        type_name: str,
        declared: Mapping[str, PropertyType],
        properties: Mapping[str, Any],
    ) -> None:
        for key, value in properties.items():
            if key.startswith("ref:"):
                # ref:* is validated upstream as a UUID-string.
                continue
            expected = declared.get(key)
            if expected is None:
                # Under strict mode: unknown keys are allowed only if
                # the declared map is empty (meaning the type author
                # opted out of strict typing for this type).
                if declared:
                    raise PropertyShapeError(
                        f"{scope} type {type_name!r} has strict property "
                        f"typing but property {key!r} is not declared"
                    )
                continue
            if not _matches_type(value, expected):
                raise PropertyShapeError(
                    f"{scope} type {type_name!r} property {key!r} "
                    f"expected {expected.value}, got {type(value).__name__}"
                )


def _matches_type(value: Any, expected: PropertyType) -> bool:
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
