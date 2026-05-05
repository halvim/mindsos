"""Schema: type declarations, property validation, and strictness control.

Phase 04 slim port of ``mindsos_core/schema/`` from the parent project.
Phase 04-v2 adds ``HyperEdgeType`` (ADR-0017 / MC-2 / HET-1).

Defers ``validate_namespaced_properties`` (graph-level property bag,
ADR-0130) to Phase 05/10. ``Schema`` ctor matches parent shape — no
``name`` field on the class; the state-file basename is the identity
that the Phase 04 CLI persists by.
"""

from __future__ import annotations

from .schema import Schema
from .types import EdgeType, HyperEdgeType, NodeType, PropertyType
from .validation import (
    REF_PROPERTY_PREFIX,
    RESERVED_PROPERTY_KEYS,
    validate_user_properties,
)

__all__ = [
    "EdgeType",
    "HyperEdgeType",
    "NodeType",
    "PropertyType",
    "REF_PROPERTY_PREFIX",
    "RESERVED_PROPERTY_KEYS",
    "Schema",
    "validate_user_properties",
]
