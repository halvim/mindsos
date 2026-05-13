"""The ``Node`` primitive (Phase 03 slim port + Phase 07 ``_version`` field).

A ``Node`` is a typed, UUID-identified vertex with an open property bag.
Properties are validated by the containing ``Graph`` / ``Schema`` before
the node is inserted; construction itself never validates so that
reconstruction and composition are always cheap.

Phase 07 adds the ``_version: int`` field per P26 A — the slim Phase 03
form stripped it; Phase 07's persistence layer needs OCC support per
ADR-0127.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .identity import generate_uuid


@dataclass
class Node:
    """A typed vertex with identity and properties.

    Attributes:
        value: Primary display value (name, label, …). Any JSON-serialisable
            type (str / int / float / bool / None / list / dict).
        type_name: The node type name. Phase 04's ``Schema`` validates this
            against a declared NodeType vocabulary; Phase 03 stores it
            verbatim with no validation.
        node_id: UUID string (or caller-supplied IRI), stable for the
            lifetime of the object.
        properties: Open dict of domain attributes.
        _version: Monotonic version counter (ADR-0127 OCC). Starts at 1
            on construction; persistence layer bumps on every update
            path. Reserved property key per Phase 04
            ``schema/validation.py``.
    """

    value: Any
    type_name: str
    node_id: str = field(default_factory=generate_uuid)
    properties: Dict[str, Any] = field(default_factory=dict)
    _version: int = 1

    def __hash__(self) -> int:
        return hash(self.node_id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Node) and self.node_id == other.node_id

    def __repr__(self) -> str:
        return (
            f"Node(value={self.value!r}, type={self.type_name!r}, "
            f"id={self.node_id[:8]})"
        )
