"""MindsOS Core Layer — Phase 03 surface (identity + graph elements + cypher safety).

Phase 02 shipped identity primitives. Phase 03 adds graph elements and
the Cypher identifier-safety regex (ADR-0021):

    from mindsos_core import (
        # exceptions (Phase 02 + 03)
        CoreError, IdentityError, SchemaError, CypherError,
        # identity (Phase 02)
        IdentityRegistry, generate_uuid,
        IdStrategy, UUID4Strategy, UUID5FromContentStrategy,
        IRIPassthroughStrategy, NAMESPACE_MINDSOS,
        # graph elements (Phase 03)
        Graph, Node, Edge, HyperEdge,
        # cypher safety (Phase 03 — ADR-0021)
        validate_edge_type_identifier, validate_label_identifier,
    )

Subsequent phases append: Phase 04 brings ``Schema``, Phase 05 brings
``Metagraph``, Phase 07 brings persistence, etc. Each phase that adds a
new sub-package must also extend ``[tool.setuptools.packages.find].include``
in ``pyproject.toml`` if it introduces a new top-level subdirectory not
covered by the existing wildcards (``mindsos_core*`` is wildcarded —
auto-covers ``mindsos_core.cypher`` and ``mindsos_core.models``).

The Core Layer owns data primitives, schema, identity, persistence, and
reconstruction. It owns no reasoning, no derivation, and no domain logic
— those belong to the Intellectual Capacity, Intelligence, and Mental
Model layers built on top of this package (ADR-0014).

Slim-port deferral list (Phase 03 strips these from the parent project's
full ``mindsos_core``; each lands in its named phase):

* ``Graph.properties`` bag (ADR-0130) → Phase 05 or 10.
* ``Optional[Schema]`` typing + per-add validation hooks → Phase 04.
* ``Node._version`` / OCC bumps (ADR-0127) → Phase 07.
* ``Edge.deprecated_at`` / ``disputed_at`` + soft-delete iterators
  (ADR-0133) → Phase 10.
* ``Graph._restore_*`` reconstruction helpers → Phase 08.
* ``Graph.update_node_properties`` / ``update_edge_properties`` → Phase 04.
"""

from __future__ import annotations

from .cypher.identifiers import (
    validate_edge_type_identifier,
    validate_label_identifier,
)
from .exceptions import CoreError, CypherError, IdentityError, SchemaError
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

__all__ = [
    # exceptions
    "CoreError",
    "IdentityError",
    "SchemaError",
    "CypherError",
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
]

__version__ = "0.0.0+phase03"
