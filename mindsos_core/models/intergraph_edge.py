"""``IntergraphEdge`` — binary node↔node edge across graphs in one Metagraph.

Phase 05b primitive (ADR-0148 first draft). Per
``confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`` §2.1, an
``IntergraphEdge`` is a directed binary edge between two nodes that
live in *different* graphs within the same metagraph. The metagraph
owns the edge (registers it in the metagraph's IdentityRegistry per
ADR-0020; persists it in the metagraph state file). Per Phase 05b
Pushback 1-C, this file ships the binary primitive only;
``IntergraphHyperEdge`` (n-ary) lands in Phase 05c.

Locked round-1-6 design picks reflected here:

* **Pushback 2-A** — ``compositional: bool`` is a top-level dataclass
  field; the reserved key ``_compositional`` (in ``RESERVED_PROPERTY_KEYS``
  per Pushback 18-A) is reserved for the future Phase 07 Cypher emit's
  stamped property name on the anchor-node Pattern B. Only the
  underscore-prefixed Cypher-property form is reserved at user-property
  scope; the dataclass field itself is plain ``compositional``.
* **Pushback 16-A** — ``__post_init__`` runs ADR-0021 cypher rel-type
  regex on ``type_name``; the factory ``Metagraph.add_intergraph_edge``
  ALSO runs the validation chain (14 steps) before construction.
* **Pushback 22-A** — ``__setattr__`` override enforces ``compositional``
  immutability post-init. Other field mutations
  (``label``, ``properties`` via ``Metagraph.update_intergraph_edge_properties``)
  work normally. The flag is set at construction; re-assigning raises
  :class:`CompositionalImmutableError`.
* **Pushback 31-A** — ``label`` is set-at-create only; no
  ``update-intergraph-edge-label`` CLI in 05b. (Filed as future work
  per Pushback 31-B.)
* Soft-delete fields (``deprecated_at`` / ``disputed_at``) **NOT**
  shipped in 05b per SOFT_DELETE_AUDIT_NOTE — Phase 10 lands the
  substrate uniformly across all 4 edge variants
  (Edge / HyperEdge / MetaEdge / MetaHyperEdge / IntergraphEdge).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..cypher.identifiers import validate_edge_type_identifier
from ..exceptions import CompositionalImmutableError
from .identity import generate_uuid


# ── IntergraphEdge dataclass (Pushback 2-A + 16-A + 22-A) ────────────────────


@dataclass(kw_only=True)
class IntergraphEdge:
    """A directed binary edge between two nodes across graphs in one Metagraph.

    Phase 05b slim shape (Pushback 1-C — binary only; n-ary deferred to
    Phase 05c). Field ordering does not matter since ``kw_only=True``
    (carry-forward from 05a P8 pattern). ``__post_init__`` runs ADR-0021
    cypher rel-type regex on ``type_name`` (carry-forward from 05a P9).
    ``__setattr__`` enforces ``compositional`` immutability post-init
    (Pushback 22-A).

    Attributes:
        source_graph_id: ``Graph.graph_id`` of the source graph
            (must be a contained graph in the owning Metagraph; must
            differ from ``target_graph_id`` per design §2.1 row 3).
        source_node_id: ``Node.node_id`` of the source node (must
            exist in ``source_graph.nodes`` per Pushback 13-A — single
            check, no ``mg.identity`` belt-and-suspenders).
        target_graph_id: ``Graph.graph_id`` of the target graph
            (must be contained AND ``!= source_graph_id``).
        target_node_id: ``Node.node_id`` of the target node (must
            exist in ``target_graph.nodes``).
        type_name: Cypher rel-type (validated against ADR-0021 regex
            in ``__post_init__``).
        compositional: Identity-bearing composition flag. Default
            ``False``. Immutable post-construction (Pushback 22-A).
            When ``True``, removal/property-mutation/deprecation raise
            :class:`CompositionalImmutableError`.
        edge_id: Auto-minted UUID4 if not supplied. Factory
            ``Metagraph.add_intergraph_edge`` mints via
            ``mg.mint_id("intergraph_edge")`` (Pushback 14-A); direct
            construction (rehydration / tests) uses the field default.
        label: Optional human-readable label.
        properties: Namespaced property bag; reserved-key-aware via
            :func:`mindsos_core.schema.validation.validate_user_properties`.
    """

    source_graph_id: str
    source_node_id: str
    target_graph_id: str
    target_node_id: str
    type_name: str
    compositional: bool = False
    edge_id: str = field(default_factory=generate_uuid)
    label: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Pushback 16-A step 6 — cypher rel-type regex enforced at
        # dataclass boundary so direct construction (rehydration paths,
        # future tests) cannot bypass the invariant. The factory
        # ``Metagraph.add_intergraph_edge`` ALSO validates at the API
        # boundary — both paths converge here.
        validate_edge_type_identifier(self.type_name)
        # Pushback 22-A — mark instance as initialised so __setattr__
        # below knows to enforce ``compositional`` immutability.
        # Stash via object.__setattr__ to bypass our own override.
        object.__setattr__(self, "_initialized", True)

    def __setattr__(self, name: str, value: Any) -> None:
        # Pushback 22-A — enforce ``compositional`` immutability
        # post-init. Other fields mutate normally (label is
        # convention-immutable per Pushback 31-A but not enforced here;
        # properties bag mutates via
        # ``Metagraph.update_intergraph_edge_properties``).
        if (
            name == "compositional"
            and getattr(self, "_initialized", False)
        ):
            raise CompositionalImmutableError(
                f"IntergraphEdge.compositional is immutable post-create "
                f"(Pushback 22-A). Edge {getattr(self, 'edge_id', '?')[:8]} "
                f"compositional flag cannot be re-assigned."
            )
        object.__setattr__(self, name, value)

    def __hash__(self) -> int:
        return hash(self.edge_id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, IntergraphEdge) and self.edge_id == other.edge_id

    def __repr__(self) -> str:
        flag = " compositional" if self.compositional else ""
        return (
            f"IntergraphEdge({self.source_graph_id}.{self.source_node_id} "
            f"-[{self.type_name}]-> "
            f"{self.target_graph_id}.{self.target_node_id}{flag}, "
            f"id={self.edge_id[:8]})"
        )
