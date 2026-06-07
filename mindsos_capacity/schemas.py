"""Schema builders for L3 role-graphs.

Two schema shapes are enough for the vertical slice:

- :func:`build_datastates_schema` for the shared ``capacity:datastates``
  graph holding every DataState node (ADR-0064).
- :func:`build_category_schema` for each ``capacity:<category>`` graph
  holding Capacity / Monitor / Adapter nodes (ADR-0065).

Both schemas default to ``strict=False`` — the property-type maps
declared here are advisory unless callers opt in. Strict mode is wired
through to every write via :class:`CapacityLayer`'s ``strict`` flag.

**Reserved-not-populated edges.** The category schema declares
``EDGE_PRODUCES`` + ``EDGE_CONSUMES`` (capacity↔datastate reification)
even though Phase 28 does not populate them. Per ADR-0064 §Implementation,
these are placeholders for the eventual write-API flow-graph (Phase 33+
ADR-0147 per-flow validators). Declaring them up-front avoids a schema
migration when a future phase materialises them.
"""

from __future__ import annotations

from mindsos_core import EdgeType, NodeType, Schema
from mindsos_core.schema.types import PropertyType

from .identifiers import (
    EDGE_CONSTRAINT,
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    NODE_TYPE_ADAPTER,
    NODE_TYPE_CAPACITY,
    NODE_TYPE_DATASTATE,
    NODE_TYPE_MONITOR,
    ROLE_DATASTATES,
)


def build_datastates_schema(*, strict: bool = False) -> Schema:
    """Schema for the shared ``capacity:datastates`` graph (ADR-0064)."""
    schema = Schema(strict=strict)
    schema.add_node_type(
        NodeType(
            name=NODE_TYPE_DATASTATE,
            description="A named representation shape consumed/produced by capacities.",
            property_types={
                "name": PropertyType.STRING,
                "shape_kind": PropertyType.STRING,
                "description": PropertyType.STRING,
                "node_kind": PropertyType.STRING,
                "provenance_category": PropertyType.STRING,
                "l2_roles": PropertyType.LIST_STRING,
            },
        )
    )
    return schema


def build_category_schema(*, strict: bool = False) -> Schema:
    """Schema for any ``capacity:<category>`` graph (ADR-0065).

    Holds Capacity, Monitor, and Adapter nodes plus the CONSTRAINT edge
    type. PRODUCES / CONSUMES register the bipartite rel-type vocabulary
    (ADR-0156); the edges themselves are metagraph-owned IntergraphEdges
    emitted at register_capacity time.
    """
    schema = Schema(strict=strict)

    capacity_props = {
        "name": PropertyType.STRING,
        "category": PropertyType.STRING,
        "description": PropertyType.STRING,
        "node_kind": PropertyType.STRING,
        "is_adapter": PropertyType.BOOL,
        "inputs": PropertyType.LIST_STRING,
        "outputs": PropertyType.LIST_STRING,
        "subscribes_to": PropertyType.LIST_STRING,
        "emits": PropertyType.LIST_STRING,
        "cost_prior": PropertyType.FLOAT,
        "latency_ms_prior": PropertyType.FLOAT,
    }
    schema.add_node_type(
        NodeType(
            name=NODE_TYPE_CAPACITY,
            description="Reactive capacity node.",
            property_types=dict(capacity_props),
        )
    )
    schema.add_node_type(
        NodeType(
            name=NODE_TYPE_MONITOR,
            description="Resident capacity (monitor) node.",
            property_types=dict(capacity_props),
        )
    )
    schema.add_node_type(
        NodeType(
            name=NODE_TYPE_ADAPTER,
            description="Adapter node bridging near-compatible DataStates.",
            property_types=dict(capacity_props),
        )
    )

    nodes = frozenset({NODE_TYPE_CAPACITY, NODE_TYPE_MONITOR, NODE_TYPE_ADAPTER})

    schema.add_edge_type(
        EdgeType(
            name=EDGE_CONSTRAINT,
            allowed_sources=nodes,
            allowed_targets=nodes,
            description="Admin-authored pipeline constraint.",
            property_types={
                "constraint_kind": PropertyType.STRING,
                "rate_limit": PropertyType.INT,
                "note": PropertyType.STRING,
            },
        )
    )
    schema.add_edge_type(
        EdgeType(
            name=EDGE_PRODUCES,
            allowed_sources=nodes,
            allowed_targets=nodes,
            description=(
                "Bipartite topology (ADR-0156): capacity→DataState. "
                "Populated as metagraph-owned IntergraphEdges at "
                "register_capacity time; this graph-schema entry registers "
                "the rel-type vocabulary."
            ),
        )
    )
    schema.add_edge_type(
        EdgeType(
            name=EDGE_CONSUMES,
            allowed_sources=nodes,
            allowed_targets=nodes,
            description=(
                "Bipartite topology (ADR-0156): DataState→capacity. "
                "Populated as metagraph-owned IntergraphEdges at "
                "register_capacity time; this graph-schema entry registers "
                "the rel-type vocabulary."
            ),
        )
    )
    return schema


def schema_for_role(role: str, *, strict: bool = False) -> Schema:
    """Return the appropriate schema for ``role``.

    Mirrors :func:`mindsos_knowledge.bootstrap._schema_for_role`. Used
    by :mod:`mindsos_capacity.bootstrap` when materialising role-graphs.
    """
    from .identifiers import ROLE_DATASTATES, category_role

    if role == ROLE_DATASTATES:
        return build_datastates_schema(strict=strict)
    if role.startswith("capacity:") and role != ROLE_DATASTATES:
        return build_category_schema(strict=strict)
    raise ValueError(f"Unknown L3 role: {role!r}")


__all__ = [
    "build_datastates_schema",
    "build_category_schema",
    "schema_for_role",
]
