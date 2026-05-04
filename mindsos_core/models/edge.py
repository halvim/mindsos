"""Directed edges and n-ary hyperedges (Phase 03 slim port).

An ``Edge`` connects two ``Node`` objects with a relationship type and an
optional label. A ``HyperEdge`` connects any non-empty set of nodes with
a label.

Phase 03 strips the soft-delete fields (``deprecated_at`` / ``disputed_at``,
ADR-0133) — those land in Phase 10 alongside the snapshot / RemovalImpact
machinery. The ``datetime`` import drops accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

from ..exceptions import SchemaError
from .identity import generate_uuid
from .node import Node


@dataclass
class Edge:
    """A directed, typed relationship between two nodes."""

    source: Node
    target: Node
    type_name: str
    label: Optional[str] = None
    edge_id: str = field(default_factory=generate_uuid)
    properties: Dict[str, Any] = field(default_factory=dict)

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
    """An n-ary relationship across an arbitrary set of nodes.

    Raises:
        SchemaError: if instantiated with an empty member set.

    Member ordering is canonicalised by the containing ``Graph`` /
    state-file (de)serializer (sorted by ``node_id``) — the in-memory
    ``nodes`` set itself is unordered as Python sets are.
    """

    nodes: Set[Node] = field(default_factory=set)
    label: Optional[str] = None
    edge_id: str = field(default_factory=generate_uuid)
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.nodes:
            raise SchemaError("HyperEdge must have at least one member node")

    def __hash__(self) -> int:
        return hash(self.edge_id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, HyperEdge) and self.edge_id == other.edge_id

    def __repr__(self) -> str:
        members = ", ".join(str(n.value) for n in self.nodes)
        return (
            f"HyperEdge(label={self.label!r}, nodes=[{members}], "
            f"id={self.edge_id[:8]})"
        )
