"""Schema type declarations.

``NodeType`` and ``EdgeType`` record the *shape* of a type in the
schema: its name, optional property-type map, and (for edges) permitted
source/target node types.

``PropertyType`` enumerates the primitive property value types that
Schema can enforce when ``strict=True``. Lists of primitives are also
allowed (Redis/FalkorDB stores them natively).

Phase 04 ships the full 8-variant vocabulary verbatim from the parent
project. Splitting (e.g. shipping only primitives in Phase 04, lists in
Phase 05) was rejected — the variants are paired in one Enum and
removing them later creates Phase 04→05 forward debt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, Optional


class PropertyType(str, Enum):
    """Primitive property value kinds recognised by strict schemas."""

    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    LIST_STRING = "list[string]"
    LIST_INT = "list[int]"
    LIST_FLOAT = "list[float]"
    LIST_BOOL = "list[bool]"


@dataclass(frozen=True)
class NodeType:
    """Declaration of a node type."""

    name: str
    #: Optional property-name -> expected PropertyType. Used when the
    #: owning Schema has ``strict=True``. When empty the node type
    #: accepts any primitive properties.
    property_types: Dict[str, PropertyType] = field(default_factory=dict)
    description: Optional[str] = None

    def __repr__(self) -> str:
        return f"NodeType({self.name!r})"


@dataclass(frozen=True)
class EdgeType:
    """Declaration of an edge (relationship) type.

    ``allowed_sources`` / ``allowed_targets`` restrict which node types
    may appear on each end. An empty set means "any". The edge type
    ``name`` is used verbatim as the Cypher relationship identifier, so
    it MUST match ``^[A-Z][A-Z0-9_]{0,63}$`` (validated at registration
    time via :func:`mindsos_core.cypher.identifiers.validate_edge_type_identifier`).
    """

    name: str
    allowed_sources: FrozenSet[str] = field(default_factory=frozenset)
    allowed_targets: FrozenSet[str] = field(default_factory=frozenset)
    property_types: Dict[str, PropertyType] = field(default_factory=dict)
    description: Optional[str] = None

    def __repr__(self) -> str:
        return f"EdgeType({self.name!r})"
