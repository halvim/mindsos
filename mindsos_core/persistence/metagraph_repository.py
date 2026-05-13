"""Persist a :class:`Metagraph` (Phase 07 slim port).

**4-step lifecycle per P96 A:**

1. **Core writes** — anchor + contained graphs (via :class:`GraphRepository`)
   + MetaEdges + MetaHyperEdges + IntergraphEdges + IntergraphHyperEdges.
2. **WAL commit** — if a :class:`WriteAheadLog` context was opened,
   stamp ``committed=true``.
3. **Observers fire** — ``Metagraph._persist_observers`` invoked with
   ``mg``. Phase 07 consumer:
   ``mindsos_instances.InstanceRepository`` (via
   ``mindsos_instances.attach_registry(mg)`` extension).
4. **Return.**

Observer failure (step 3) leaves Core+WAL consistent but instance
persistence partial; tester convention per P33 A is to re-run
``persist`` (MERGE-idempotent).

**Phase 07 changes from v3:**

* Strips XRef call (Phase 09 territory).
* Strips direct ``InstanceRepository`` call — replaced by observer
  (M9).
* ``_props_json`` write wraps in narrow chained driver-exception
  catch per P97 B (no size cap per P83 C).
* ``schema_name`` persisted as plain Cypher property using the
  existing ``mg.schema_name`` dataclass field per P100 A (no
  ``:MetagraphSchema`` labeled node; no ``:HAS_SCHEMA`` edge).
* Programmatic-only — no CLI verb in 07 (P60 A); metagraph sync
  CLI lands Phase 08 per M14/P12 D.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any, Dict, List

# falkordb / redis driver exception classes — narrow chained catch per P97 B.
# Imported lazily / defensively so import-time path doesn't require the
# driver in environments using InMemoryClient only.
try:
    from falkordb.exceptions import FalkorDBError as _FalkorDBError  # type: ignore
except Exception:  # pragma: no cover
    _FalkorDBError = Exception  # type: ignore
try:
    from redis.exceptions import ResponseError as _RedisResponseError  # type: ignore
except Exception:  # pragma: no cover
    _RedisResponseError = Exception  # type: ignore

from .._observers import _dispatch_after_persist
from ..cypher.builders import (
    build_create_metagraph_anchor,
    build_unwind_create_intergraph_edges,
    build_unwind_create_intergraph_hyperedges,
    build_unwind_create_metaedges,
    build_unwind_create_metahyperedges,
)
from ..exceptions import PersistenceError
from ..models.metagraph import Metagraph
from .client import Client
from .graph_repository import GraphRepository

_log = logging.getLogger(__name__)


class MetagraphRepository:
    """Persist a :class:`Metagraph` programmatically (Phase 07 — P60 A).

    No CLI verb consumes this in 07; metagraph sync ships Phase 08 per
    M14/P12 D. The programmatic API is the test-and-integration
    surface for the 4-step lifecycle (P96 A).
    """

    def __init__(self, client: Client) -> None:
        self._client = client
        self._graphs = GraphRepository(client)

    def persist(self, metagraph: Metagraph) -> None:
        """Persist a Metagraph + its contained Graphs + cross-graph edges.

        Lifecycle per P96 A:

        1. Core writes (this method body, steps 1a-1f).
        2. (WAL commit not yet shipped in 07; mechanism only.)
        3. Observers fire (instance persistence sibling-side).
        4. Return.
        """
        # ── Step 1a: anchor (with _props_json + schema_name?) ────────────
        props_json = self._encode_props_json(metagraph.properties)
        q, p = build_create_metagraph_anchor(
            metagraph.metagraph_id,
            metagraph.name,
            props_json=props_json,
            schema_name=metagraph.schema_name,
        )
        self._safe_run(q, p)

        # ── Step 1b: contained graphs ────────────────────────────────────
        for g in metagraph.graphs.values():
            self._graphs.persist(g, metagraph_id=metagraph.metagraph_id)

        # ── Step 1c: metaedges (grouped by type) ────────────────────────
        if metagraph.metaedges:
            by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for me in metagraph.metaedges.values():
                by_type[me.type_name].append({
                    "id": me.edge_id,
                    "source_graph_id": me.source_graph_id,
                    "target_graph_id": me.target_graph_id,
                    "label": me.label,
                    "props": dict(me.properties),
                    "_version": getattr(me, "_version", 1),
                })
            for type_name, rows in by_type.items():
                q, p = build_unwind_create_metaedges(
                    metagraph.metagraph_id, type_name, rows,
                )
                self._client.run_query(q, p)

        # ── Step 1d: metahyperedges ─────────────────────────────────────
        if metagraph.metahyperedges:
            rows = [
                {
                    "id": mh.edge_id,
                    "label": mh.label,
                    "props": dict(mh.properties),
                    "member_graph_ids": list(mh.graph_ids),
                    "_version": getattr(mh, "_version", 1),
                }
                for mh in metagraph.metahyperedges.values()
            ]
            q, p = build_unwind_create_metahyperedges(
                metagraph.metagraph_id, rows,
            )
            self._client.run_query(q, p)

        # ── Step 1e: intergraph edges (grouped by type) ─────────────────
        if metagraph.intergraph_edges:
            ig_by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for ie in metagraph.intergraph_edges.values():
                ig_by_type[ie.type_name].append({
                    "id": ie.edge_id,
                    "source_node_id": ie.source_node_id,
                    "source_graph_id": ie.source_graph_id,
                    "target_node_id": ie.target_node_id,
                    "target_graph_id": ie.target_graph_id,
                    "label": ie.label,
                    "compositional": ie.compositional,
                    "props": dict(ie.properties),
                    "_version": getattr(ie, "_version", 1),
                })
            for type_name, rows in ig_by_type.items():
                q, p = build_unwind_create_intergraph_edges(
                    metagraph.metagraph_id, type_name, rows,
                )
                self._client.run_query(q, p)

        # ── Step 1f: intergraph hyperedges ──────────────────────────────
        if metagraph.intergraph_hyperedges:
            rows = [
                {
                    "id": ih.edge_id,
                    "label": ih.label,
                    "ordered": True,  # Phase 05c: ordered baked into type
                    "compositional": ih.compositional,
                    "props": dict(ih.properties),
                    "members": [
                        {"node_id": nid, "graph_id": gid}
                        for (gid, nid) in ih.members
                    ],
                    "_version": getattr(ih, "_version", 1),
                }
                for ih in metagraph.intergraph_hyperedges.values()
            ]
            q, p = build_unwind_create_intergraph_hyperedges(
                metagraph.metagraph_id, rows,
            )
            self._client.run_query(q, p)

        # ── Step 2: WAL commit (mechanism-only at Phase 07; no caller). ─

        # ── Step 3: observers fire (M9). ────────────────────────────────
        _dispatch_after_persist(metagraph._persist_observers, metagraph)

        # ── Step 4: return. ─────────────────────────────────────────────

    # ── helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _encode_props_json(properties: Dict[str, Any]) -> str:
        """Encode metagraph ``.properties`` dict to canonical JSON string (ADR-0130 + P62 A).

        Per P83 C — no size cap; oversize errors surface from the
        driver via the narrow chained catch in :meth:`_safe_run`.
        """
        # Empty bag → empty JSON object so the property is always set
        # (rather than NULL) and round-trip is stable.
        return json.dumps(
            properties or {},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def _safe_run(self, query: str, params: Dict[str, Any]) -> None:
        """Run an anchor write with narrow chained driver-exception catch (P97 B).

        Driver errors (typically oversized ``_props_json`` strings) are
        re-raised as :class:`PersistenceError` with the original
        chained via ``raise ... from e``. The narrow catch tuple
        targets the actual driver exception classes (``redis.exceptions
        .ResponseError`` and ``falkordb.exceptions.FalkorDBError``) so
        unrelated bugs in our own code path don't get masked.
        """
        try:
            self._client.run_query(query, params)
        except (_RedisResponseError, _FalkorDBError) as e:
            raise PersistenceError(
                f"Metagraph anchor write failed: {e}"
            ) from e


__all__ = ["MetagraphRepository"]
