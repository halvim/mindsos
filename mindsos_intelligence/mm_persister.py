"""L4 MM persistence — write a per-task chain graph to Falkor (DQ-8 / CR#4).

The Mental Model is a live per-session working memory. Under DQ-8 only the
per-task **chain** graph is persisted, so an Episode's ``mm_root_ref`` (that
graph's ``graph_id``) resolves instead of dangling. ``capacity_mm`` /
``knowledge_mm`` stay live-only until WSD.

Persisting a *single* graph (not :meth:`MetagraphRepository.persist`, which
re-walks every graph in the metagraph — a full MERGE each call, no add-side
dirty tracking) is what keeps consolidation O(this task) rather than
O(session²) across a resident session. The metagraph anchor is MERGE-created
first because ``build_create_graph_anchor`` links via ``MATCH (m:Metagraph)``
and would otherwise leave the graph unlinked.

Both calls are Core (L1) persistence primitives; this class only orchestrates
them with the injected client — it does not reimplement persistence.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MMPersister(Protocol):
    """The narrow surface the Orchestrator/consolidation depend on. Keeps L4
    ignorant of Falkor/Core-persistence detail (mirrors ``checkpoint_store``)."""

    def persist(self, metagraph: Any, graph: Any) -> None: ...


class FalkorMMPersister:
    """Persist one graph within ``metagraph`` to Falkor via Core repositories.

    Caller owns the ``client`` lifecycle (Phase 07 P4 A), as elsewhere.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def persist(self, metagraph: Any, graph: Any) -> None:
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

        # 2. Persist just this task's chain graph (anchor + nodes + edges).
        GraphRepository(self._client).persist(
            graph, metagraph_id=metagraph.metagraph_id
        )


__all__ = ["MMPersister", "FalkorMMPersister"]
