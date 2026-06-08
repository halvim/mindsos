"""MM resolution + instantiation layer (ADR-0166 / Chat B D-B13/B14).

The concrete :class:`~mindsos_capacity.context.MMHandle` the Phase 42
Protocol named as "the L4 substrate's MM handle (Phase 46)". L4 reads
only from the MM; on cache-miss the resolver fetches the source node at
its current version, instantiates one node into the IRI-dispatched sub-MM
(ADR-0165), pins ``(iri, version)``, and returns it. Lazy single-node;
monotone-grow (never evicted mid-task); pinned (the task reads its pinned
version regardless of later source writes).

The KL/CL source is injected as a Protocol so the substrate ships ahead
of its Phase-47 orchestrator consumer (consumer discipline). Lazy
inline-on-retire (D'1) lands Phase 48 with ``kl.read_at_version`` /
``kl.retire_version``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from .mm import MentalModel


@dataclass(frozen=True)
class PinnedRef:
    iri: str
    version: int


@dataclass
class SourceNode:
    iri: str
    version: int
    type_iri: Optional[str] = None
    payload: Any = None
    produces: tuple = ()
    consumes: tuple = ()


@dataclass
class InstantiatedNode:
    iri: str
    pin: PinnedRef
    type_iri: Optional[str]
    payload: Any


@runtime_checkable
class MMSource(Protocol):
    def get_node(self, iri: str) -> SourceNode: ...


class MMResolver:
    def __init__(self, mm: MentalModel, source: MMSource) -> None:
        self._mm = mm
        self._source = source
        self._instantiated: Dict[str, InstantiatedNode] = {}

    def get_or_instantiate(self, node_iri: str) -> InstantiatedNode:
        existing = self._instantiated.get(node_iri)
        if existing is not None:
            return existing
        self._mm.sub_mm_for_iri(node_iri)
        with self._mm.lock.write_locked():
            existing = self._instantiated.get(node_iri)
            if existing is not None:
                return existing
            src = self._source.get_node(node_iri)
            node = InstantiatedNode(
                iri=node_iri,
                pin=PinnedRef(node_iri, src.version),
                type_iri=src.type_iri,
                payload=src.payload,
            )
            self._instantiated[node_iri] = node
            return node

    def find_instances_by_type(self, type_iri: str) -> List[InstantiatedNode]:
        with self._mm.lock.read_locked():
            return [n for n in self._instantiated.values() if n.type_iri == type_iri]

    def produces_of(self, capacity_instance: InstantiatedNode) -> List[InstantiatedNode]:
        src = self._source.get_node(capacity_instance.iri)
        return [self.get_or_instantiate(iri) for iri in src.produces]

    def consumes_of(self, data_state_instance: InstantiatedNode) -> List[InstantiatedNode]:
        src = self._source.get_node(data_state_instance.iri)
        return [self.get_or_instantiate(iri) for iri in src.consumes]

    def instantiated_count(self) -> int:
        return len(self._instantiated)


__all__ = [
    "MMResolver",
    "MMSource",
    "SourceNode",
    "InstantiatedNode",
    "PinnedRef",
]
