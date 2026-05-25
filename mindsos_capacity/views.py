"""Read-only views over an L3 Metagraph.

:class:`CapacityLayerView` is the analogue of
:class:`mindsos_knowledge.views.MetagraphView` — a thin facade exposing
the capacity- and DataState-level lookups L4's pipeline-finder needs,
without any write surface.

Phase 28 shipped the accessor surface (``category_graph`` /
``datastates_graph`` / ``iter_categories`` / ``get_capacity`` /
``get_datastate`` / ``iter_capacities`` / ``iter_datastates``). Phase 29
adds the :class:`SuccessorHop` dataclass + the successor / producer /
consumer walks atomically with the TYPE_COMPAT auto-discovery
substrate per Phase 28 R4 PB-45.

**Parent-verbatim semantics (R5 PB-37):** the walks do NOT filter
soft-deleted edges or nodes at Phase 29 — Phase 28's
:meth:`iter_capacities` doesn't filter either; consistency wins.
``include_deprecated`` parameter discipline across L3 walks is a
Phase 30+ carry-forward (R5 PB-37 new item).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Optional

from mindsos_core import Edge, Graph, Metagraph, Node

from .identifiers import (
    EDGE_TYPE_COMPAT,
    NODE_TYPE_ADAPTER,
    NODE_TYPE_CAPACITY,
    NODE_TYPE_DATASTATE,
    NODE_TYPE_MONITOR,
    ROLE_DATASTATES,
    category_role,
)


# ── SuccessorHop ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class SuccessorHop:
    """One step in a pipeline.

    Attributes:
        source_capacity: The capacity IRI that produces the DataState.
        target_capacity: The capacity IRI that consumes the DataState.
        via_datastate: The DataState IRI connecting them.
        same_category: ``True`` iff both capacities sit in the same
            functional-category graph (the edge is intra-graph).
        strictness: ``"strict"`` or ``"adapter"`` — Phase 29 vertical
            slice only emits ``"strict"``. The ``"adapter"`` variant
            requires adapter-bridge synthesis which a future phase
            ships.
        adapter_capacity: The adapter IRI inserted, if any. Always
            ``None`` at Phase 29 (no adapter-bridge synthesis yet).
    """

    source_capacity: str
    target_capacity: str
    via_datastate: str
    same_category: bool
    strictness: str = "strict"
    adapter_capacity: Optional[str] = None


# ── CapacityLayerView ──────────────────────────────────────────────────

class CapacityLayerView:
    """Read-only view over an L3 Metagraph.

    Exposes capacity / DataState lookup, category iteration, and
    type-compatibility successor lookup. Modifications must go through
    :class:`mindsos_capacity.capacity_layer.CapacityLayer`.
    """

    def __init__(self, metagraph: Metagraph) -> None:
        self._mg = metagraph

    # ── basic accessors ────────────────────────────────────────────────

    @property
    def metagraph(self) -> Metagraph:
        return self._mg

    @property
    def name(self) -> str:
        return self._mg.name

    def category_graph(self, category: str) -> Optional[Graph]:
        """Return the graph for a functional ``category``, or ``None``."""
        role = category_role(category)
        for g in self._mg.graphs.values():
            if g.role == role:
                return g
        return None

    def datastates_graph(self) -> Optional[Graph]:
        """Return the shared ``capacity:datastates`` graph, or ``None``."""
        for g in self._mg.graphs.values():
            if g.role == ROLE_DATASTATES:
                return g
        return None

    def iter_categories(self) -> Iterator[str]:
        """Yield the functional-category names present in this metagraph.

        Walks ``mg.graphs`` for any role beginning ``capacity:`` and
        excluding the shared DataStates role. Yields the bare category
        name (the ``capacity:`` prefix is stripped).
        """
        prefix = "capacity:"
        for g in self._mg.graphs.values():
            if g.role and g.role.startswith(prefix) and g.role != ROLE_DATASTATES:
                yield g.role[len(prefix):]

    # ── capacity / datastate lookup ────────────────────────────────────

    def get_capacity(self, iri: str) -> Optional[Node]:
        """Return the capacity node with IRI ``iri``, searching every category."""
        for g in self._mg.graphs.values():
            if g.role == ROLE_DATASTATES:
                continue
            node = g.nodes.get(iri)
            if node is not None:
                return node
        return None

    def get_datastate(self, iri: str) -> Optional[Node]:
        """Return the DataState node with IRI ``iri``, or ``None``."""
        g = self.datastates_graph()
        if g is None:
            return None
        return g.nodes.get(iri)

    def iter_capacities(self, category: Optional[str] = None) -> Iterator[Node]:
        """Yield capacity nodes, optionally filtered to one ``category``."""
        capacity_types = (NODE_TYPE_CAPACITY, NODE_TYPE_MONITOR, NODE_TYPE_ADAPTER)
        if category is None:
            for g in self._mg.graphs.values():
                if g.role == ROLE_DATASTATES:
                    continue
                yield from (
                    n for n in g.nodes.values() if n.type_name in capacity_types
                )
        else:
            g = self.category_graph(category)
            if g is None:
                return
            yield from (
                n for n in g.nodes.values() if n.type_name in capacity_types
            )

    def iter_datastates(self) -> Iterator[Node]:
        """Yield all DataState nodes in the metagraph."""
        g = self.datastates_graph()
        if g is None:
            return iter(())
        return (n for n in g.nodes.values() if n.type_name == NODE_TYPE_DATASTATE)

    # ── successor enumeration (used by pipeline-finder) ───────────────

    def successors_of(self, capacity_iri: str) -> List[SuccessorHop]:
        """Return every TYPE_COMPAT successor of ``capacity_iri``.

        Walks both intra-graph Edges and cross-graph MetaEdges. Parent-
        verbatim — no soft-delete filter at Phase 29 (R5 PB-37).
        Returns hops in dict-iteration order; tests should use set
        comparison or explicit sort.
        """
        hops: List[SuccessorHop] = []
        source = self.get_capacity(capacity_iri)
        if source is None:
            return hops
        # Intra-graph.
        for g in self._mg.graphs.values():
            if g.role == ROLE_DATASTATES:
                continue
            for e in g.edges.values():
                if (
                    e.type_name == EDGE_TYPE_COMPAT
                    and e.source.node_id == source.node_id
                ):
                    hops.append(_hop_from_edge(e, same_category=True))
        # Cross-graph.
        for me in self._mg.metaedges.values():
            if (
                me.type_name == EDGE_TYPE_COMPAT
                and me.properties.get("source_capacity") == source.node_id
            ):
                hops.append(
                    SuccessorHop(
                        source_capacity=me.properties["source_capacity"],
                        target_capacity=me.properties["target_capacity"],
                        via_datastate=me.properties.get("via_datastate", ""),
                        same_category=False,
                        strictness=me.properties.get("strictness", "strict"),
                        adapter_capacity=me.properties.get("adapter_id"),
                    )
                )
        return hops

    def producers_of(self, datastate_iri: str) -> List[Node]:
        """Return every capacity whose ``outputs`` list contains ``datastate_iri``."""
        hits: List[Node] = []
        for node in self.iter_capacities():
            outs = node.properties.get("outputs") or []
            if datastate_iri in outs:
                hits.append(node)
        return hits

    def consumers_of(self, datastate_iri: str) -> List[Node]:
        """Return every capacity whose ``inputs`` list contains ``datastate_iri``."""
        hits: List[Node] = []
        for node in self.iter_capacities():
            ins = node.properties.get("inputs") or []
            if datastate_iri in ins:
                hits.append(node)
        return hits

    def __repr__(self) -> str:
        return f"CapacityLayerView({self._mg.name!r}, graphs={len(self._mg.graphs)})"


def _hop_from_edge(edge: Edge, *, same_category: bool) -> SuccessorHop:
    """Internal helper: build a SuccessorHop from an intra-graph Edge."""
    return SuccessorHop(
        source_capacity=edge.source.node_id,
        target_capacity=edge.target.node_id,
        via_datastate=edge.properties.get("via_datastate", ""),
        same_category=same_category,
        strictness=edge.properties.get("strictness", "strict"),
        adapter_capacity=edge.properties.get("adapter_id"),
    )


__all__ = ["CapacityLayerView", "SuccessorHop"]
