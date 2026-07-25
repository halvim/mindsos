"""MM resolution + instantiation layer (ADR-0166 / Chat B D-B13/B14).

The concrete :class:`~mindsos_capacity.context.MMHandle` the Phase 42
Protocol named as "the L4 substrate's MM handle (Phase 46)". L4 reads
only from the MM; on cache-miss the resolver fetches the source node at
its current version, instantiates one node into the IRI-dispatched sub-MM
(ADR-0165), pins ``(iri, version)``, and returns it. Lazy single-node;
monotone-grow (never evicted mid-task); pinned (the task reads its pinned
version regardless of later source writes).

**Slice 3 (knowledge writer) — finish the instantiation INTO the graph.**
``get_or_instantiate`` now writes the pinned version-ref as a real node in
the IRI-dispatched sub-MM (``mm:instances`` graph), not only a shadow dict.
An ``ontology:``/``episodic:`` corpus entry therefore lands in
``knowledge_mm`` — giving it a genuine writer (it was empty by construction
before) and a concrete node the ``capacity_mm``→``knowledge_mm`` provenance
XRef (DQ-1) can target (``add_xref`` requires target existence). The
``self._instantiated`` dict stays as the run-local pin cache/index over those
nodes (pinned, monotone-grow); the graph is the store of record — closing the
ADR-0165/0166 "no shadow state outside the MM" invariant for the knowledge
room.

The KL/CL source is injected as a Protocol so the substrate ships ahead
of its Phase-47 orchestrator consumer (consumer discipline).
:class:`KnowledgeMMSource` is the shipped L2-backed source, wired as the
resolver's source at the L4 dispatcher sites (ADR-0200). Lazy
inline-on-retire (D'1) lands Phase 48 with ``kl.read_at_version`` /
``kl.retire_version``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from mindsos_core import Graph, Metagraph

from .mm import MentalModel

#: Role of the per-sub-MM graph holding the pinned version-ref nodes the
#: resolver writes on cache-miss. One such graph per sub-MM (find-or-create).
INSTANCE_GRAPH_ROLE = "mm:instances"

#: Node type carried by a resolver-minted instance (free-form — the sub-MMs
#: carry no schema, ``Metagraph.schema is None``).
NODE_TYPE_MM_INSTANCE = "MMInstance"

#: Property keys on an instance node: the pinned source version + the source
#: type IRI (recoverable without parsing the node id).
PROP_PIN_VERSION = "pin_version"
PROP_INSTANCE_TYPE = "instance_type"


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
        # Route first (raises KeyError on an unowned namespace) so an
        # un-routable IRI is rejected before any lock / graph mutation.
        sub = self._mm.sub_mm_for_iri(node_iri)
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
            # Slice 3 — write the pinned instance into the routed sub-MM graph
            # (store of record); the dict below is the pin cache / index.
            self._write_instance(sub, node)
            self._instantiated[node_iri] = node
            return node

    # ── graph write (caller holds the write lock) ─────────────────────────

    def _instance_graph(self, sub_mm: Metagraph) -> Graph:
        for g in sub_mm.graphs.values():
            if g.role == INSTANCE_GRAPH_ROLE:
                return g
        g = Graph(name=INSTANCE_GRAPH_ROLE, role=INSTANCE_GRAPH_ROLE)
        sub_mm.add_graph(g)
        return g

    def _write_instance(self, sub_mm: Metagraph, node: InstantiatedNode) -> None:
        graph = self._instance_graph(sub_mm)
        if node.iri in graph.nodes:  # monotone-grow: one node per pinned IRI
            return
        graph.add_node(
            value=node.payload,
            type_name=NODE_TYPE_MM_INSTANCE,
            properties={
                PROP_PIN_VERSION: node.pin.version,
                PROP_INSTANCE_TYPE: node.type_iri or "",
            },
            node_id=node.iri,
        )

    # ── read surface (ADR-0159 MMHandle) ──────────────────────────────────

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


class KnowledgeMMSource:
    """:class:`MMSource` backed by the KnowledgeLayer (L2 read surface).

    Wired as the :class:`MMResolver` source at the L4 dispatcher sites
    (ADR-0200 / Slice 3) so a ``reads_mm=True`` body gets a working read
    handle instead of the raw ``MentalModel``. Duck-typed on ``kl`` — no
    ``mindsos_knowledge`` import (layer isolation, Phase-28 invariant).

    Inert in prod until a ``reads_mm=True`` consumer ships (no shipped
    capacity declares it, ADR-0200 §blast-radius); exercised structurally by
    tests, which pass a fake source. ``get_node`` resolves the node via
    ``kl.read_at_version`` (the shipped ADR-0159 surface; under the
    one-version-per-role store the IRI already identifies the version). The
    pin version is read from the node's ``version`` property when present,
    else 1. L2 corpus/ontology nodes carry no produces/consumes (that is L3
    capacity topology), so both default empty.
    """

    def __init__(self, kl: Any) -> None:
        self._kl = kl

    def get_node(self, iri: str) -> SourceNode:
        node = self._kl.read_at_version(iri, 0)
        if node is None:
            raise KeyError(f"KnowledgeMMSource: no L2 node for iri {iri!r}")
        props = getattr(node, "properties", None) or {}
        try:
            version = int(props.get("version", 1))
        except (TypeError, ValueError):
            version = 1
        return SourceNode(
            iri=iri,
            version=version,
            type_iri=getattr(node, "type_name", None),
            payload=getattr(node, "value", None),
        )


__all__ = [
    "MMResolver",
    "MMSource",
    "SourceNode",
    "InstantiatedNode",
    "PinnedRef",
    "KnowledgeMMSource",
    "INSTANCE_GRAPH_ROLE",
    "NODE_TYPE_MM_INSTANCE",
    "PROP_PIN_VERSION",
    "PROP_INSTANCE_TYPE",
]
