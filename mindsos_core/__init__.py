"""MindsOS Core Layer — Phase 04-v2 surface (identity + graph elements + cypher safety + schema incl. HyperEdgeType).

Phase 02 shipped identity primitives. Phase 03 added graph elements and
the Cypher identifier-safety regex (ADR-0021). Phase 04 adds the
``Schema`` machinery (NodeType / EdgeType / PropertyType + opt-in strict
property typing) and restores ``Graph``'s ``schema`` ctor parameter +
``update_node_properties`` / ``update_edge_properties`` (deferred from
Phase 03). Phase 04-v2 adds ``HyperEdgeType`` + ``HyperEdge.type_name``
+ ``Graph.update_hyperedge_properties`` + ``Graph.update_hyperedge_type``
(MC-2 / HET-1 / SENT-1 / UHT-1 locks):

    from mindsos_core import (
        # exceptions (Phase 02 + 03 + 04)
        CoreError, IdentityError, SchemaError, CypherError,
        PropertyShapeError, UnknownTypeError,
        # identity (Phase 02)
        IdentityRegistry, generate_uuid,
        IdStrategy, UUID4Strategy, UUID5FromContentStrategy,
        IRIPassthroughStrategy, NAMESPACE_MINDSOS,
        # graph elements (Phase 03)
        Graph, Node, Edge, HyperEdge,
        # cypher safety (Phase 03 — ADR-0021)
        validate_edge_type_identifier, validate_label_identifier,
        # schema (Phase 04 + 04-v2 — ADR-0017)
        Schema, NodeType, EdgeType, HyperEdgeType, PropertyType,
        validate_user_properties,
        RESERVED_PROPERTY_KEYS, REF_PROPERTY_PREFIX,
    )

Subsequent phases append: Phase 05 brings ``Metagraph``, Phase 07 brings
persistence, etc. Each phase that adds a new sub-package must also extend
``[tool.setuptools.packages.find].include`` in ``pyproject.toml`` if it
introduces a new top-level subdirectory not covered by the existing
wildcards (``mindsos_core*`` is wildcarded — auto-covers
``mindsos_core.cypher``, ``mindsos_core.models``, and the new
``mindsos_core.schema``).

The Core Layer owns data primitives, schema, identity, persistence, and
reconstruction. It owns no reasoning, no derivation, and no domain logic
— those belong to the Intellectual Capacity, Intelligence, and Mental
Model layers built on top of this package (ADR-0014).

Slim-port deferral list (Phase 04 closes 4 entries from Phase 03's list;
the remaining ports phase-by-phase):

* ``Graph.properties`` bag (ADR-0130) → Phase 05 or 10.
* ``Node._version`` / OCC bumps (ADR-0127) → Phase 07.
* ``Edge.deprecated_at`` / ``disputed_at`` + soft-delete iterators
  (ADR-0133) → Phase 10.
* ``Graph._restore_*`` reconstruction helpers → Phase 08.
* ``validate_namespaced_properties`` (graph-level / metagraph-level
  property bag, ADR-0130) → Phase 05/10.
"""

from __future__ import annotations

from .cypher.identifiers import (
    validate_edge_type_identifier,
    validate_label_identifier,
)
from .exceptions import (
    CoreError,
    CypherError,
    IdentityError,
    PropertyShapeError,
    SchemaError,
    UnknownTypeError,
)
from .models.edge import Edge, HyperEdge
from .models.graph import Graph
from .models.identity import (
    IRIPassthroughStrategy,
    IdentityRegistry,
    IdStrategy,
    NAMESPACE_MINDSOS,
    UUID4Strategy,
    UUID5FromContentStrategy,
    generate_uuid,
)
from .models.node import Node
from .schema import (
    EdgeType,
    HyperEdgeType,
    NodeType,
    PropertyType,
    REF_PROPERTY_PREFIX,
    RESERVED_PROPERTY_KEYS,
    Schema,
    validate_user_properties,
)

__all__ = [
    # exceptions
    "CoreError",
    "IdentityError",
    "SchemaError",
    "CypherError",
    "PropertyShapeError",
    "UnknownTypeError",
    # identity (Phase 02)
    "IdentityRegistry",
    "generate_uuid",
    # ADR-0131 — pluggable id strategies (Phase 02)
    "IdStrategy",
    "UUID4Strategy",
    "UUID5FromContentStrategy",
    "IRIPassthroughStrategy",
    "NAMESPACE_MINDSOS",
    # graph elements (Phase 03)
    "Graph",
    "Node",
    "Edge",
    "HyperEdge",
    # cypher safety (Phase 03 — ADR-0021)
    "validate_edge_type_identifier",
    "validate_label_identifier",
    # schema (Phase 04 + 04-v2 — ADR-0017)
    "Schema",
    "NodeType",
    "EdgeType",
    "HyperEdgeType",
    "PropertyType",
    "validate_user_properties",
    "RESERVED_PROPERTY_KEYS",
    "REF_PROPERTY_PREFIX",
]

__version__ = "0.0.0+phase04.v2"
