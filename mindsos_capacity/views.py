"""Read-only views over an L3 Metagraph.

:class:`CapacityLayerView` is the analogue of
:class:`mindsos_knowledge.views.MetagraphView` — a thin facade exposing
the capacity- and DataState-level lookups L4's pipeline-finder needs,
without any write surface.

Phase 28 shipped the accessor surface (``category_graph`` /
``datastates_graph`` / ``iter_categories`` / ``get_capacity`` /
``get_datastate`` / ``iter_capacities`` / ``iter_datastates``).

**Bipartite topology (ADR-0156, Phase 42).** The successor / producer /
consumer walks read the explicit ``PRODUCES`` / ``CONSUMES``
IntergraphEdges (the single query-time source of truth per PB-9) rather
than the retired ``inputs``/``outputs`` node properties or the retired
type-compatibility edges. ``inputs_of`` / ``outputs_of`` co-ship per
ADR-0156.

**Parent-verbatim semantics (R5 PB-37):** the walks do NOT filter
soft-deleted edges or nodes — :meth:`iter_capacities` doesn't filter
either; consistency wins.
"""

from __future__ import annotations

from typing import Iterator, List, Optional

from mindsos_core import Graph, IntergraphEdge, Metagraph, Node

from .identifiers import (
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    NODE_TYPE_ADAPTER,
    NODE_TYPE_CAPACITY,
    NODE_TYPE_DATASTATE,
    NODE_TYPE_MONITOR,
    ROLE_DATASTATES,
    category_role,
)


# ── CapacityLayerView ──────────────────────────────────────────────────

class CapacityLayerView:
    """Read-only view over an L3 Metagraph.

    Exposes capacity / DataState lookup, category iteration, and the
    bipartite successor / producer / consumer walks. Modifications must
    go through :class:`mindsos_capacity.capacity_layer.CapacityLayer`.
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

    # ── bipartite walk primitive (ADR-0156) ──────────────────────────

    def _iter_edges(self, type_name: str) -> Iterator[IntergraphEdge]:
        """Yield this metagraph's IntergraphEdges of one ``type_name``.

        The metagraph's in-memory ``iter_intergraph_edges`` is the walk
        substrate; Pattern B anchor-node persistence is invisible here.
        """
        for ie in self._mg.iter_intergraph_edges():
            if ie.type_name == type_name:
                yield ie

    # ── producer / consumer / input / output walks ───────────────────

    def outputs_of(self, capacity_iri: str) -> List[str]:
        """DataState IRIs this capacity PRODUCES (edge-sourced; PB-9)."""
        return [
            ie.target_node_id
            for ie in self._iter_edges(EDGE_PRODUCES)
            if ie.source_node_id == capacity_iri
        ]

    def inputs_of(self, capacity_iri: str) -> List[str]:
        """DataState IRIs this capacity CONSUMES (edge-sourced; PB-9)."""
        return [
            ie.source_node_id
            for ie in self._iter_edges(EDGE_CONSUMES)
            if ie.target_node_id == capacity_iri
        ]

    def producers_of(self, datastate_iri: str) -> List[Node]:
        """Return every capacity that PRODUCES ``datastate_iri``."""
        hits: List[Node] = []
        for ie in self._iter_edges(EDGE_PRODUCES):
            if ie.target_node_id == datastate_iri:
                node = self.get_capacity(ie.source_node_id)
                if node is not None:
                    hits.append(node)
        return hits

    def consumers_of(self, datastate_iri: str) -> List[Node]:
        """Return every capacity that CONSUMES ``datastate_iri``."""
        hits: List[Node] = []
        for ie in self._iter_edges(EDGE_CONSUMES):
            if ie.source_node_id == datastate_iri:
                node = self.get_capacity(ie.target_node_id)
                if node is not None:
                    hits.append(node)
        return hits

    # ── successor enumeration (used by pipeline-finder) ───────────────

    def successors_of(self, capacity_iri: str) -> List[str]:
        """Return successor capacity IRIs via the two-hop bipartite walk.

        ``capacity → PRODUCES → DataState → CONSUMES → successor``
        (ADR-0156). Semantic-preserving replacement for the retired
        one-hop type-compatibility walk; self is excluded. Order is walk
        order; callers needing determinism should sort or set-compare.
        """
        if self.get_capacity(capacity_iri) is None:
            return []
        seen: List[str] = []
        for ds_iri in self.outputs_of(capacity_iri):
            for ie in self._iter_edges(EDGE_CONSUMES):
                if ie.source_node_id == ds_iri:
                    succ = ie.target_node_id
                    if succ != capacity_iri and succ not in seen:
                        seen.append(succ)
        return seen

    def __repr__(self) -> str:
        return f"CapacityLayerView({self._mg.name!r}, graphs={len(self._mg.graphs)})"


class LocalPreferringView:
    """Local-preferring UNION over a Global + one Local metagraph view.

    Presents the finder read surface (``producers_of`` / ``consumers_of`` /
    ``inputs_of`` / ``outputs_of`` / ``get_capacity``) as the union of the two
    underlying :class:`CapacityLayerView` s, with **Local overriding Global at
    a colliding capacity IRI**: a Global capacity whose IRI is also registered
    Locally is hidden entirely (its node + its PRODUCES/CONSUMES edges are
    dropped), so a one-step Local override composes inside an otherwise-Global
    pipeline without the finder OR-over-producers pick re-selecting the
    shadowed Global capacity. Read-only (mirrors :class:`CapacityLayerView`).
    """

    def __init__(
        self, global_view: "CapacityLayerView", local_view: "CapacityLayerView"
    ) -> None:
        self._g = global_view
        self._l = local_view
        self._local_iris = {n.node_id for n in local_view.iter_capacities()}

    def _merge(self, local_nodes: List[Node], global_nodes: List[Node]) -> List[Node]:
        out: List[Node] = list(local_nodes)
        seen = {n.node_id for n in out}
        for n in global_nodes:
            if n.node_id in self._local_iris or n.node_id in seen:
                continue
            seen.add(n.node_id)
            out.append(n)
        return out

    def producers_of(self, datastate_iri: str) -> List[Node]:
        return self._merge(
            self._l.producers_of(datastate_iri), self._g.producers_of(datastate_iri)
        )

    def consumers_of(self, datastate_iri: str) -> List[Node]:
        return self._merge(
            self._l.consumers_of(datastate_iri), self._g.consumers_of(datastate_iri)
        )

    def inputs_of(self, capacity_iri: str) -> List[str]:
        src = self._l if capacity_iri in self._local_iris else self._g
        return src.inputs_of(capacity_iri)

    def outputs_of(self, capacity_iri: str) -> List[str]:
        src = self._l if capacity_iri in self._local_iris else self._g
        return src.outputs_of(capacity_iri)

    def get_capacity(self, iri: str) -> Optional[Node]:
        return self._l.get_capacity(iri) or self._g.get_capacity(iri)


__all__ = ["CapacityLayerView", "LocalPreferringView"]
