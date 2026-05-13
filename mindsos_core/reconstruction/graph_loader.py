"""Reconstruct a :class:`Graph` from FalkorDB (Phase 07 single-Graph load — M14).

Phase 07 slim port. Loads:

* Graph anchor row (name + role + metagraph_id?).
* All :Node rows with ``graph_id`` matching.
* All edges where both endpoints live in this graph (cross-graph leakage
  surfaces as a logged warning; rows are skipped).
* All :HyperEdge rows + their :MEMBER edges.

Per P77 B — defensive read of ``_props_json`` on the Graph anchor row
is **stripped** in Phase 07 because the writer is skipped (P9 C; Graph
``.properties`` defer per §7 Q4). Add back when the writer ships
(Phase 10 likely).

Per M14 — single-Graph scope only. Metagraph reconstruction +
streaming loader (ADR-0124) + refresh (ADR-0125) deferred to Phase 08.

Per P95 B index list — uses ``(:Node {graph_id})`` hot-path index for
per-graph node scan.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..exceptions import PersistenceError
from ..models.graph import Graph
from ..models.identity import IdentityRegistry
from ..persistence.client import Client

_log = logging.getLogger(__name__)


# Reserved Cypher-row property keys stripped from the user-property bag
# before reconstructing a Node / Edge / HyperEdge. Anything Core writes
# as a structural column (id, graph_id, type_name, ...) goes here.
_CORE_KEYS = frozenset({
    "id",
    "graph_id",
    "metagraph_id",
    "type_name",
    "label",
    "value",
    "_version",
    "_props_json",
    "schema_name",
})


def load_graph(
    client: Client,
    graph_id: str,
    *,
    identity: Optional[IdentityRegistry] = None,
    schema: Any = None,
) -> Graph:
    """Reconstruct the :class:`Graph` with ``graph_id`` from FalkorDB.

    Args:
        client: Connected :class:`Client` (e.g. :class:`FalkorClient`).
        graph_id: The Cypher ``:Graph.id`` to load.
        identity: Optional shared :class:`IdentityRegistry`. When
            ``None``, a fresh registry is created and the loaded
            ``graph_id`` is registered. When passed in (e.g. by a
            future Phase 08 metagraph loader), every element id is
            registered under the shared registry.
        schema: Optional :class:`Schema` to attach. Phase 07 loads do
            not validate against schema (rehydration tolerates legacy
            state per ``_validate=False`` precedent).

    Returns:
        Reconstructed :class:`Graph` with ``_version`` fields restored
        on every element.

    Raises:
        PersistenceError: no :Graph row with ``id=graph_id`` exists in
            FalkorDB, or the driver fails on any sub-query.
    """
    anchor = _load_graph_anchor(client, graph_id)

    g = Graph(
        name=anchor["name"],
        role=anchor.get("role"),
        schema=schema,
        identity=identity,
        graph_id=graph_id,
    )
    if identity is None:
        # When standalone, Graph.__init__ registers graph_id only if
        # graph_id was None at construction; on the restore path we
        # supplied an explicit id, so register it now.
        try:
            g.identity.register(graph_id)
        except Exception:
            # Already-registered is fine.
            pass

    _load_nodes(client, g)
    _load_edges(client, g)
    _load_hyperedges(client, g)
    _detect_cross_graph_leaks(client, g)
    return g


# ── private steps ───────────────────────────────────────────────────────────


def _load_graph_anchor(client: Client, graph_id: str) -> Dict[str, Any]:
    """Read the :Graph anchor row + optional metagraph_id back-pointer."""
    q = (
        "MATCH (g:Graph {id: $gid}) "
        "RETURN g.name AS name, g.role AS role, g._version AS version, "
        "       g.metagraph_id AS metagraph_id"
    )
    res = client.run_query(q, {"gid": graph_id})
    if not res.rows:
        raise PersistenceError(
            f"No :Graph row with id {graph_id!r} in FalkorDB"
        )
    return res.rows[0]


def _load_nodes(client: Client, g: Graph) -> None:
    q = (
        "MATCH (n:Node {graph_id: $gid}) "
        "RETURN n.id AS id, n.type_name AS type_name, n.value AS value, "
        "       n._version AS version, properties(n) AS props"
    )
    res = client.run_query(q, {"gid": g.graph_id})
    for row in res.rows:
        props = _strip_core_keys(row.get("props") or {})
        node = g.add_node(
            value=row.get("value"),
            type_name=row["type_name"],
            properties=props,
            node_id=row["id"],
            _validate=False,
        )
        if row.get("version") is not None:
            node._version = int(row["version"])


def _load_edges(client: Client, g: Graph) -> None:
    """Load edges where both endpoints live in this graph.

    Cross-graph rows skipped here; logged in
    :func:`_detect_cross_graph_leaks` for operator visibility.
    """
    q = (
        "MATCH (s:Node {graph_id: $gid})-[e]->(t:Node {graph_id: $gid}) "
        "WHERE e.graph_id = $gid AND e.id IS NOT NULL "
        "RETURN e.id AS id, e.type_name AS type_name, e.label AS label, "
        "       e._version AS version, "
        "       s.id AS source_id, t.id AS target_id, properties(e) AS props"
    )
    res = client.run_query(q, {"gid": g.graph_id})
    for row in res.rows:
        src = g.nodes.get(row["source_id"])
        tgt = g.nodes.get(row["target_id"])
        if src is None or tgt is None:
            _log.warning(
                "Edge %r in graph %r references missing node "
                "(src=%r tgt=%r); skipping",
                row["id"], g.graph_id, row["source_id"], row["target_id"],
            )
            continue
        props = _strip_core_keys(row.get("props") or {})
        edge = g.add_edge(
            source=src,
            target=tgt,
            type_name=row["type_name"],
            label=row.get("label"),
            properties=props,
            edge_id=row["id"],
            _validate=False,
        )
        if row.get("version") is not None:
            edge._version = int(row["version"])


def _load_hyperedges(client: Client, g: Graph) -> None:
    """Load hyperedges with their :MEMBER edges in a single round-trip."""
    q = (
        "MATCH (h:HyperEdge {graph_id: $gid}) "
        "OPTIONAL MATCH (h)-[:MEMBER]->(n:Node) "
        "WITH h, collect(n.id) AS member_ids "
        "RETURN h.id AS id, h.type_name AS type_name, h.label AS label, "
        "       h._version AS version, properties(h) AS props, member_ids"
    )
    res = client.run_query(q, {"gid": g.graph_id})
    for row in res.rows:
        member_ids = [mid for mid in (row.get("member_ids") or []) if mid]
        members = []
        for mid in member_ids:
            n = g.nodes.get(mid)
            if n is None:
                _log.warning(
                    "HyperEdge %r references missing node %r in graph %r; dropping",
                    row["id"], mid, g.graph_id,
                )
                continue
            members.append(n)
        if not members:
            _log.warning(
                "HyperEdge %r has no valid members in graph %r; skipping",
                row["id"], g.graph_id,
            )
            continue
        props = _strip_core_keys(row.get("props") or {})
        type_name = row.get("type_name") or "UNSPECIFIED"
        h = g.add_hyperedge(
            nodes=members,
            type_name=type_name,
            label=row.get("label"),
            properties=props,
            edge_id=row["id"],
            _validate=False,
        )
        if row.get("version") is not None:
            h._version = int(row["version"])


def _detect_cross_graph_leaks(client: Client, g: Graph) -> None:
    """Log a warning for every cross-graph edge in the DB tagged with this graph.

    Edge is intra-graph by ADR-0021. A leak surfaces as a warning here
    and as a finding in the integrity scanner's ``cross_graph_edges``
    bucket per ADR-0123.
    """
    q = (
        "MATCH (s:Node)-[e]->(t:Node) "
        "WHERE e.graph_id = $gid "
        "  AND (s.graph_id <> $gid OR t.graph_id <> $gid) "
        "RETURN e.id AS id, s.graph_id AS src_gid, t.graph_id AS tgt_gid"
    )
    leaks = client.run_query(q, {"gid": g.graph_id})
    for row in leaks.rows:
        _log.warning(
            "Cross-graph edge leak detected: edge %r tagged graph_id=%r "
            "but endpoints live in graphs src=%r tgt=%r",
            row["id"], g.graph_id, row["src_gid"], row["tgt_gid"],
        )


def _strip_core_keys(props: Dict[str, Any]) -> Dict[str, Any]:
    """Drop Core-reserved property keys before handing the bag to a dataclass."""
    return {k: v for k, v in props.items() if k not in _CORE_KEYS}


__all__ = ["load_graph"]
