"""Cypher-level concerns: identifier safety + parameterised query builders.

Phase 03 shipped identifier safety only (ADR-0021). Phase 07 adds the
parameterised query builders (``build_create_*`` / ``build_unwind_*`` /
``build_update_*_properties`` / ``build_remove_*``) consumed by
``mindsos_core.persistence`` repositories.
"""

from __future__ import annotations

from .builders import (
    build_create_composite_instance,
    build_create_element_instance,
    build_create_graph_anchor,
    build_create_metagraph_anchor,
    build_create_tombstone,
    build_remove_edge,
    build_remove_hyperedge,
    build_remove_node,
    build_unwind_create_edges,
    build_unwind_create_hyperedges,
    build_unwind_create_intergraph_edges,
    build_unwind_create_intergraph_hyperedges,
    build_unwind_create_metaedges,
    build_unwind_create_metahyperedges,
    build_unwind_create_nodes,
    build_update_edge_properties,
    build_update_hyperedge_properties,
    build_update_node_properties,
)
from .identifiers import (
    EDGE_TYPE_IDENTIFIER_RE,
    validate_edge_type_identifier,
    validate_label_identifier,
)

__all__ = [
    # Identifier safety (Phase 03).
    "EDGE_TYPE_IDENTIFIER_RE",
    "validate_edge_type_identifier",
    "validate_label_identifier",
    # Anchor builders (Phase 07).
    "build_create_metagraph_anchor",
    "build_create_graph_anchor",
    "build_create_tombstone",
    # UNWIND batched creates.
    "build_unwind_create_nodes",
    "build_unwind_create_edges",
    "build_unwind_create_hyperedges",
    "build_unwind_create_metaedges",
    "build_unwind_create_metahyperedges",
    "build_unwind_create_intergraph_edges",
    "build_unwind_create_intergraph_hyperedges",
    # Updates with _version bump + OCC predicate.
    "build_update_node_properties",
    "build_update_edge_properties",
    "build_update_hyperedge_properties",
    # Removals (tombstone-write + DETACH DELETE).
    "build_remove_node",
    "build_remove_edge",
    "build_remove_hyperedge",
    # Instance builders (consumed by mindsos_instances.persistence).
    "build_create_element_instance",
    "build_create_composite_instance",
]
