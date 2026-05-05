"""MindsOS Core Layer — Phase 05a surface (identity + graph elements + cypher safety + schema incl. HyperEdgeType + Metagraph + MetaEdge + MetaHyperEdge).

Phase 02 shipped identity primitives. Phase 03 added graph elements and
the Cypher identifier-safety regex (ADR-0021). Phase 04 added the
``Schema`` machinery (NodeType / EdgeType / PropertyType + opt-in strict
property typing). Phase 04-v2 added ``HyperEdgeType`` + ``HyperEdge.type_name``
+ ``Graph.update_hyperedge_properties`` + ``Graph.update_hyperedge_type``.

Phase 05a slim port adds the metagraph primitives:

* ``Metagraph`` — graph-of-graphs container with shared
  :class:`IdentityRegistry` (ADR-0020) and namespaced property bag
  (ADR-0130 Accepted in 05a per N1-A1).
* ``MetaEdge`` — directed typed graph↔graph edge.
* ``MetaHyperEdge`` — n-ary typed graph-set edge.

Round 1-4 design picks reflected in the slim shape:

* P1 — soft-delete fields stripped from MetaEdge/MetaHyperEdge (Phase 10
  adds across all 4 edge variants uniformly).
* P3 — ``CompositionalMetaEdge`` dropped entirely (ADR-0117 Withdrawn in 05a).
* P8 — kw_only dataclasses on MetaEdge + MetaHyperEdge.
* P9 — ``__post_init__`` cypher rel-type regex on both edge types.
* P11 — factories take graph_id strings (not ``Graph`` objects).
* P15 — refuse self-loop MetaEdge + 1-member MetaHyperEdge.
* P16 — ``add_graph`` post-conditions: shared identity, untouched
  ``id_strategy``.
* P19 — ``remove_graph`` is single-behavior always-cascade (no flag,
  no RemovalImpact return).

Slim-port deferral list (subsequent phases append):

* ``Metagraph.add_xref`` / ``iter_xrefs`` / ``remove_xref`` (ADR-0128) — Phase 09.
* ``element_instances`` / ``composite_instances`` (ADR-0024 / ADR-0025) — Phase 06.
* Soft-delete on edges/hyperedges/metaedges/metahyperedges (ADR-0133) — Phase 10.
* ``RemovalImpact`` + ``force=True`` on ``remove_graph`` (ADR-0135) — Phase 10.
* ``Metagraph.mint_id`` (ADR-0131 helper) — Phase 05b (consumer = IntergraphEdge).
* ``Graph.properties`` graph-level property bag (ADR-0130) — Phase 10.
* ``IntergraphEdge`` (binary 1-1 cross-graph node↔node) — Phase 05b.
* ``IntergraphHyperEdge`` (n-ary cross-graph) — Phase 05c.
* ``MetagraphSchema`` + ``MetaEdgeType`` / ``MetaHyperEdgeType`` /
  ``IntergraphEdgeType`` — Phase 05b.
* ``CompositionalMetaEdge`` — DROPPED (N3-D + P3 lock; ADR-0117 Withdrawn
  in 05a per round-1 lock; the compositional concept moves to a flag on
  intergraph primitives in 05b/05c).
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
from .models.metagraph import MetaEdge, MetaHyperEdge, Metagraph
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
    # metagraph (Phase 05a — ADR-0020 + ADR-0130)
    "Metagraph",
    "MetaEdge",
    "MetaHyperEdge",
]

__version__ = "0.0.0+phase05a"
