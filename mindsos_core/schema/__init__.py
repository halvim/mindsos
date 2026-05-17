"""Schema: type declarations, property validation, and strictness control.

Phase 04 slim port of ``mindsos_core/schema/`` from the parent project.
Phase 04-v2 adds ``HyperEdgeType`` (ADR-0017 / MC-2 / HET-1).
Phase 05b adds ``IntergraphEdgeType`` (ADR-0148) and ``MetagraphSchema``
(metagraph-level container for intergraph-edge type vocabulary).
Phase 05c adds ``IntergraphHyperEdgeType``.
Phase 05d adds ``MetaEdgeType`` + ``MetaHyperEdgeType`` (ADR-0014 third
amendment).

Defers ``validate_namespaced_properties`` (graph-level property bag,
ADR-0130) to Phase 10. ``Schema`` and ``MetagraphSchema`` ctors match
parent shape — no ``name`` field on the class; the state-file basename
is the identity that the CLI persists by (mirror Phase 04 Schema).
"""

from __future__ import annotations

from .metagraph_schema import MetagraphSchema
from .migration import (
    SchemaMigrationError,
    SchemaViolation,
    migrate_from,
)
from .schema import Schema
from .types import (
    EdgeType,
    HyperEdgeType,
    IntergraphEdgeType,
    IntergraphHyperEdgeType,
    MetaEdgeType,
    MetaHyperEdgeType,
    NodeType,
    PropertyType,
)
from .validation import (
    REF_PROPERTY_PREFIX,
    RESERVED_PROPERTY_KEYS,
    validate_user_properties,
)

__all__ = [
    "EdgeType",
    "HyperEdgeType",
    "IntergraphEdgeType",
    "IntergraphHyperEdgeType",
    "MetaEdgeType",
    "MetaHyperEdgeType",
    "MetagraphSchema",
    "NodeType",
    "PropertyType",
    "REF_PROPERTY_PREFIX",
    "RESERVED_PROPERTY_KEYS",
    "Schema",
    "SchemaMigrationError",
    "SchemaViolation",
    "migrate_from",
    "validate_user_properties",
]
