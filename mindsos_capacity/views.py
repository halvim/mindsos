"""Read-only views over an L3 Metagraph (Phase 28 slim ship).

:class:`CapacityLayerView` is the analogue of
:class:`mindsos_knowledge.views.MetagraphView` — a thin facade exposing
the capacity- and DataState-level lookups L4's pipeline-finder needs,
without any write surface.

**Phase 28 slim scope.** Ships accessors only:
``category_graph`` / ``datastates_graph`` / ``iter_categories`` /
``get_capacity`` / ``get_datastate`` / ``iter_capacities`` /
``iter_datastates``. Successors / producers / consumers walks are
deferred to Phase 29 (where TYPE_COMPAT auto-discovery substrate ships;
without that substrate the walks would return empty deterministically,
which is misleading). The :class:`SuccessorHop` dataclass + the three
walk methods will land atomically at Phase 29 alongside the discovery
substrate per Phase 28 R4 PB-45 lock.
"""

from __future__ import annotations

from typing import Iterator, Optional

from mindsos_core import Graph, Metagraph, Node

from .identifiers import (
    NODE_TYPE_ADAPTER,
    NODE_TYPE_CAPACITY,
    NODE_TYPE_DATASTATE,
    NODE_TYPE_MONITOR,
    ROLE_DATASTATES,
    category_role,
)


class CapacityLayerView:
    """Read-only view over an L3 Metagraph.

    Exposes capacity / DataState lookup + category iteration.
    Modifications must go through
    :class:`mindsos_capacity.capacity_layer.CapacityLayer`.

    Successor / producer / consumer walks are deferred to Phase 29; this
    Phase 28 ship gives L4 just enough to discover *what exists* in the
    Global / Local metagraphs.
    """

    def __init__(self, metagraph: Metagraph) -> None:
        self._mg = metagraph

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

    def __repr__(self) -> str:
        return f"CapacityLayerView({self._mg.name!r}, graphs={len(self._mg.graphs)})"


__all__ = ["CapacityLayerView"]
