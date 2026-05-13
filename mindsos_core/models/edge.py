"""Directed edges and n-ary hyperedges (Phase 03 slim port + Phase 04-v2 type_name).

An ``Edge`` connects two ``Node`` objects with a relationship type and an
optional label. A ``HyperEdge`` connects any non-empty set of nodes with
a relationship type (Phase 04-v2 — ADR-0017 / MC-2) and an optional label.

Phase 03 stripped the soft-delete fields (``deprecated_at`` /
``disputed_at``, ADR-0133) — those land in Phase 10 alongside the
snapshot / RemovalImpact machinery. The ``datetime`` import drops
accordingly.

Phase 04-v2 adds ``HyperEdge.type_name: str`` (required) — cypher
rel-type validation per ADR-0021 in ``__post_init__``. Legacy v=1/v=2
hyperedges (no type_name) are populated with the SENT-1 sentinel
``"UNSPECIFIED"`` at load time; the sentinel is a deliberate cypher-regex
fit (uppercase, no underscores at the start). Recovery via
``Graph.update_hyperedge_type`` (UHT-1) or ``mindsos graph
update-hyperedge-type`` CLI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

from ..cypher.identifiers import validate_edge_type_identifier
from ..exceptions import SchemaError
from .identity import generate_uuid
from .node import Node


@dataclass
class Edge:
    """A directed, typed relationship between two nodes.

    Phase 07 — ``_version: int = 1`` field added (ADR-0127 OCC).
    """

    source: Node
    target: Node
    type_name: str
    label: Optional[str] = None
    edge_id: str = field(default_factory=generate_uuid)
    properties: Dict[str, Any] = field(default_factory=dict)
    _version: int = 1

    def __hash__(self) -> int:
        return hash(self.edge_id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Edge) and self.edge_id == other.edge_id

    def __repr__(self) -> str:
        return (
            f"Edge({self.source.value!r} -[{self.type_name}]-> "
            f"{self.target.value!r}, id={self.edge_id[:8]})"
        )


@dataclass
class HyperEdge:
    """An n-ary, typed relationship across an arbitrary set of nodes.

    Phase 04-v2 — ``type_name`` is required (ADR-0017 / MC-2). Cypher
    rel-type validation per ADR-0021 runs in ``__post_init__``; the
    SENT-1 sentinel ``"UNSPECIFIED"`` (assigned to legacy v=1/v=2
    hyperedges by the loader) is uppercase and passes the regex.

    Raises:
        SchemaError: if instantiated with an empty member set.
        CypherError: if ``type_name`` is unsafe to splice into Cypher.

    Member ordering is canonicalised by the containing ``Graph`` /
    state-file (de)serializer (sorted by ``node_id``) — the in-memory
    ``nodes`` set itself is unordered as Python sets are.
    """

    nodes: Set[Node] = field(default_factory=set)
    type_name: str = ""  # Phase 04-v2 — required; cypher-regex validated.
    label: Optional[str] = None
    edge_id: str = field(default_factory=generate_uuid)
    properties: Dict[str, Any] = field(default_factory=dict)
    _version: int = 1  # Phase 07 — ADR-0127 OCC.

    def __post_init__(self) -> None:
        if not self.nodes:
            raise SchemaError("HyperEdge must have at least one member node")
        # Phase 04-v2 — cypher rel-type validation per ADR-0021. The
        # default empty-string default is rejected; callers MUST supply
        # a valid type_name (or rehydrate the SENT-1 sentinel).
        validate_edge_type_identifier(self.type_name)

    def __hash__(self) -> int:
        return hash(self.edge_id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, HyperEdge) and self.edge_id == other.edge_id

    def __repr__(self) -> str:
        members = ", ".join(str(n.value) for n in self.nodes)
        return (
            f"HyperEdge(type={self.type_name!r}, label={self.label!r}, "
            f"nodes=[{members}], id={self.edge_id[:8]})"
        )
