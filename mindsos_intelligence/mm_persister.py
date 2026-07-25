"""L4 MM persistence — write a single MM graph to Falkor (DQ-8 / CR#4; extended
by CR: capacity_mm persist Slice B).

The Mental Model is a live per-session working memory. Two MM graphs now
persist at consolidation:

* the per-task **chain** graph (intelligence_mm), so an Episode's
  ``mm_root_ref`` resolves instead of dangling (DQ-8 / CR#4); and
* the per-run **capacity** grounding graphs + their task-level index graph
  (capacity_mm), so an Episode's ``capacity_root_ref`` resolves (CR: reopen
  DQ-8 — capacity_mm is **no longer live-only**; the ADR-0202 "live-only until
  WSD" clause is reversed for capacity_mm). ``knowledge_mm`` stays live-only
  (Slice 3 / later).

Persisting a *single* graph (not :meth:`MetagraphRepository.persist`, which
re-walks every graph in the metagraph — a full MERGE each call, no add-side
dirty tracking) is what keeps consolidation O(this task) rather than
O(session²) across a resident session. The metagraph anchor is MERGE-created
first because ``build_create_graph_anchor`` links via ``MATCH (m:Metagraph)``
and would otherwise leave the graph unlinked.

Node values that the ADR-0182 codec cannot take (it accepts only primitives /
dict / list) are reduced to codec-safe form in a *snapshot* that keeps the same
``graph_id`` (so the Episode ref still resolves) while the live graph keeps its
in-memory values for in-session readers:

* Chain nodes hold dataclass values (HintSet, TaskRun, …) → reduced via
  ``dataclasses.asdict`` (the default). Serializing at persist time (not emit
  time) captures each artifact's final mutated state (e.g. ``TaskRun.status``
  set to ``completed`` at the terminal path).
* Capacity DataStateInstance nodes hold arbitrary domain values → reduced via
  the caller-supplied ``node_value_encoder`` (the PB-1 per-DataState ``encode``
  dispatch; see :mod:`mindsos_intelligence.capacity_persister`).

**Edges are persisted** (CR Slice B / PB-4): the capacity grounding DAG's
``PRODUCES`` / ``CONSUMES`` intra-graph edges *are* its structure, so the
snapshot copies ``graph.edges`` too. ``GraphRepository.persist`` already writes
and reloads edges (batched per rel-type); the chain graph simply carries none.

Both calls are Core (L1) persistence primitives; this class only orchestrates
them with the injected client — it does not reimplement persistence.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Protocol, runtime_checkable


@runtime_checkable
class MMPersister(Protocol):
    """The narrow surface the Orchestrator/consolidation depend on. Keeps L4
    ignorant of Falkor/Core-persistence detail (mirrors ``checkpoint_store``)."""

    def persist(
        self,
        metagraph: Any,
        graph: Any,
        *,
        node_value_encoder: Optional[Callable[[Any], Any]] = None,
    ) -> None: ...


class FalkorMMPersister:
    """Persist one graph within ``metagraph`` to Falkor via Core repositories.

    Caller owns the ``client`` lifecycle (Phase 07 P4 A), as elsewhere.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def persist(
        self,
        metagraph: Any,
        graph: Any,
        *,
        node_value_encoder: Optional[Callable[[Any], Any]] = None,
    ) -> None:
        """Persist one graph within ``metagraph`` (anchor + nodes + edges).

        ``node_value_encoder`` (CR Slice B / PB-1), when given, maps a live
        :class:`Node` to its codec-safe persist value — the capacity path
        passes the per-DataState ``encode`` dispatch here. When ``None`` the
        default reduces dataclass values via ``asdict`` (the chain path) and
        passes primitives / dict / list through unchanged.
        """
        from dataclasses import asdict, is_dataclass

        from mindsos_core import Graph
        from mindsos_core.cypher.builders import build_create_metagraph_anchor
        from mindsos_core.persistence.graph_repository import GraphRepository
        from mindsos_core.persistence.metagraph_repository import MetagraphRepository

        # 1. MERGE-idempotent metagraph anchor (so the graph's IN_METAGRAPH
        #    MATCH resolves). Cheap: one MERGE, no graph walk.
        props_json = MetagraphRepository._encode_props_json(metagraph.properties)
        q, p = build_create_metagraph_anchor(
            metagraph.metagraph_id,
            metagraph.name,
            props_json=props_json,
            schema_name=metagraph.schema_name,
        )
        self._client.run_query(q, p)

        # 2. Snapshot the graph with node values reduced to codec-safe form,
        #    preserving graph_id / type_name / node_id. The default reduces
        #    dataclasses (chain artifacts) to dicts; ``node_value_encoder``
        #    overrides it (capacity DataStateInstance payloads, PB-1).
        snapshot = Graph(graph.name, role=graph.role, graph_id=graph.graph_id)
        for node in graph.nodes.values():
            if node_value_encoder is not None:
                value = node_value_encoder(node)
            elif is_dataclass(node.value):
                value = asdict(node.value)
            else:
                value = node.value
            snapshot.add_node(
                value,
                node.type_name,
                properties=dict(node.properties or {}),
                node_id=node.node_id,
            )

        # 3. Copy edges (CR Slice B / PB-4). The capacity grounding DAG's
        #    PRODUCES/CONSUMES intra-graph edges are its structure; the chain
        #    graph carries none, so this is a no-op there. Endpoint nodes were
        #    recreated with the same node_id in step 2, so the lookups resolve.
        for edge in graph.edges.values():
            snapshot.add_edge(
                snapshot.nodes[edge.source.node_id],
                snapshot.nodes[edge.target.node_id],
                edge.type_name,
                label=edge.label,
                properties=dict(edge.properties or {}),
                edge_id=edge.edge_id,
            )

        # 4. Persist the snapshot (anchor + nodes + edges) — one graph only.
        GraphRepository(self._client).persist(
            snapshot, metagraph_id=metagraph.metagraph_id
        )


__all__ = ["MMPersister", "FalkorMMPersister"]
