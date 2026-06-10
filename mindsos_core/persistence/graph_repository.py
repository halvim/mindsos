"""Persist + update + remove on a single :class:`Graph` (Phase 07 slim port).

Per row §Features:

* :meth:`persist` orchestrates anchor + nodes + edges + hyperedges
  using the typed builders in :mod:`mindsos_core.cypher.builders`.
* :meth:`update_*_properties` always bumps ``_version`` per P7 C;
  OCC enforcement is opt-in via ``expected_version`` — stale write
  raises :class:`OptimisticConcurrencyConflict` (zero-row MATCH).
* :meth:`remove_*` writes a per-(graph, element) tombstone per
  P69 A + DETACH DELETE. Read-path filter is Phase 10 (P16-pre).

Phase 07 changes from v3:

* Graph ``.properties`` writer NOT shipped (P9 C; deferred per §7 Q4) —
  anchor builder accepts no ``properties`` arg.
* ``_version`` field initialised on every element row; OCC predicate
  hard-wired into update path.
* Persist-time check (ADR-0123 §2) runs after each UNWIND batch and
  raises :class:`IntegrityCheckError` if duplicate ids surface.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Mapping, Optional

from ..cypher.builders import (
    build_create_graph_anchor,
    build_remove_edge,
    build_remove_hyperedge,
    build_remove_node,
    build_unwind_create_edges,
    build_unwind_create_hyperedges,
    build_unwind_create_nodes,
    build_update_edge_properties,
    build_update_hyperedge_properties,
    build_update_node_properties,
)
from ..exceptions import IntegrityCheckError, OptimisticConcurrencyConflict
from ..models.graph import Graph
from .client import Client
from .value_codec import encode_node_value


class GraphRepository:
    """Persist and update a single :class:`Graph`.

    Caller manages the :class:`Client` lifecycle (per P6 A).
    """

    def __init__(self, client: Client) -> None:
        self._client = client

    # ── persist ──────────────────────────────────────────────────────────

    def persist(
        self, graph: Graph, *, metagraph_id: Optional[str] = None
    ) -> None:
        """Persist a Graph: anchor + nodes (batched) + edges (per-type batched) + hyperedges (batched).

        Per ADR-0123 §2 — persist-time check after each batch surfaces
        duplicate-id violations via :class:`IntegrityCheckError`.
        """
        # 1. anchor (no _props_json per P9 C; Graph .properties deferred).
        q, p = build_create_graph_anchor(
            graph.graph_id, graph.name, graph.role, metagraph_id
        )
        self._client.run_query(q, p)

        # 2. nodes (UNWIND batched). Structured values split into the
        # (value, _value_json) pair per ADR-0182 (Phase 50); primitives
        # pass through with a NULL _value_json (rule 1).
        if graph.nodes:
            rows: List[Dict[str, Any]] = []
            for n in graph.nodes.values():
                value, value_json = encode_node_value(n.value)
                rows.append({
                    "id": n.node_id,
                    "type_name": n.type_name,
                    "value": value,
                    "_value_json": value_json,
                    "props": _filter_user_props(n.properties),
                    "_version": getattr(n, "_version", 1),
                })
            q, p = build_unwind_create_nodes(graph.graph_id, rows)
            self._client.run_query(q, p)
            self._verify_unique_ids(
                "Node", [row["id"] for row in rows], graph_id=graph.graph_id
            )

        # 3. edges — grouped by type_name (one batch per rel type).
        if graph.edges:
            by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for e in graph.edges.values():
                by_type[e.type_name].append({
                    "id": e.edge_id,
                    "source": e.source.node_id,
                    "target": e.target.node_id,
                    "label": e.label,
                    "props": _filter_user_props(e.properties),
                    "_version": getattr(e, "_version", 1),
                })
            for type_name, rows in by_type.items():
                q, p = build_unwind_create_edges(graph.graph_id, type_name, rows)
                self._client.run_query(q, p)
                # Edge-id persist-time check requires a rel-type-aware
                # MATCH — skip the cross-label scan for Phase 07; the
                # integrity scanner catches duplicates per ADR-0123 §3.

        # 4. hyperedges (UNWIND batched).
        if graph.hyperedges:
            rows = [
                {
                    "id": h.edge_id,
                    "type_name": h.type_name,
                    "label": h.label,
                    "props": _filter_user_props(h.properties),
                    "member_ids": [n.node_id for n in h.nodes],
                    "_version": getattr(h, "_version", 1),
                }
                for h in graph.hyperedges.values()
            ]
            q, p = build_unwind_create_hyperedges(graph.graph_id, rows)
            self._client.run_query(q, p)
            self._verify_unique_ids(
                "HyperEdge",
                [row["id"] for row in rows],
                graph_id=graph.graph_id,
            )

    # ── update (always bumps _version; OCC opt-in) ───────────────────────

    def update_node_properties(
        self,
        graph_id: str,
        node_id: str,
        properties: Mapping[str, Any],
        *,
        expected_version: Optional[int] = None,
    ) -> int:
        """Update node properties; bump ``_version``; return new version.

        Per P7 C — ``_version`` ALWAYS bumps on the update path. When
        ``expected_version`` is provided, the MATCH predicate carries
        it; zero rows ⇒ :class:`OptimisticConcurrencyConflict` (stale
        write).
        """
        q, p = build_update_node_properties(
            graph_id, node_id, dict(properties),
            expected_version=expected_version,
        )
        res = self._client.run_query(q, p)
        return self._extract_new_version(
            res, node_id, expected_version,
        )

    def update_edge_properties(
        self,
        graph_id: str,
        edge_id: str,
        properties: Mapping[str, Any],
        *,
        expected_version: Optional[int] = None,
    ) -> int:
        q, p = build_update_edge_properties(
            graph_id, edge_id, dict(properties),
            expected_version=expected_version,
        )
        res = self._client.run_query(q, p)
        return self._extract_new_version(
            res, edge_id, expected_version,
        )

    def update_hyperedge_properties(
        self,
        graph_id: str,
        hyperedge_id: str,
        properties: Mapping[str, Any],
        *,
        expected_version: Optional[int] = None,
    ) -> int:
        q, p = build_update_hyperedge_properties(
            graph_id, hyperedge_id, dict(properties),
            expected_version=expected_version,
        )
        res = self._client.run_query(q, p)
        return self._extract_new_version(
            res, hyperedge_id, expected_version,
        )

    # ── remove (P16-pre — tombstone-write primitives) ───────────────────

    def remove_node(
        self, graph_id: str, node_id: str, *, removed_by: Optional[str] = None
    ) -> None:
        q, p = build_remove_node(graph_id, node_id, removed_by=removed_by)
        self._client.run_query(q, p)

    def remove_edge(
        self, graph_id: str, edge_id: str, *, removed_by: Optional[str] = None
    ) -> None:
        q, p = build_remove_edge(graph_id, edge_id, removed_by=removed_by)
        self._client.run_query(q, p)

    def remove_hyperedge(
        self,
        graph_id: str,
        hyperedge_id: str,
        *,
        removed_by: Optional[str] = None,
    ) -> None:
        q, p = build_remove_hyperedge(
            graph_id, hyperedge_id, removed_by=removed_by,
        )
        self._client.run_query(q, p)

    # ── internals ───────────────────────────────────────────────────────

    def _verify_unique_ids(
        self, label: str, ids: List[str], *, graph_id: str
    ) -> None:
        """ADR-0123 §2 persist-time check on a single node label.

        Run after each UNWIND batch. Cost: one indexed scan per batch
        per label. Raises :class:`IntegrityCheckError` if any id row
        appears more than once.
        """
        if not ids:
            return
        q = (
            f"MATCH (n:{label}) "
            "WHERE n.id IN $ids "
            "RETURN n.id AS id, count(n) AS c"
        )
        res = self._client.run_query(q, {"ids": list(ids)})
        offenders = [r["id"] for r in res.rows if int(r.get("c", 0)) > 1]
        if offenders:
            raise IntegrityCheckError(
                f"Persist-time duplicate-id check failed on {label!r} "
                f"(graph_id={graph_id!r}): {offenders!r}"
            )

    def _extract_new_version(
        self,
        res,
        element_id: str,
        expected_version: Optional[int],
    ) -> int:
        """Pull ``version`` from update result; raise OCC on empty result."""
        row = res.first()
        if row is None:
            if expected_version is not None:
                raise OptimisticConcurrencyConflict(
                    element_id, expected_version, actual_version=None,
                )
            # No expected version supplied AND no row matched ⇒ element
            # missing entirely. Treat as integrity check error.
            raise IntegrityCheckError(
                f"Update target {element_id!r} not present in FalkorDB"
            )
        version = row.get("version")
        return int(version) if version is not None else 0


def _filter_user_props(properties: Mapping[str, Any]) -> Dict[str, Any]:
    """Drop reserved Cypher-row keys from the user-property bag.

    Defensive: properties bags should never carry reserved keys at
    runtime (Phase 04 ``validate_user_properties`` blocks them), but
    the persist path should not trust the caller blindly.
    """
    reserved = {"id", "graph_id", "metagraph_id", "type_name", "_version", "_props_json", "_value_json"}
    return {k: v for k, v in properties.items() if k not in reserved}


__all__ = ["GraphRepository"]
