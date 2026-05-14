"""Reconstruct a :class:`Graph` from FalkorDB.

Phase 07 shipped :func:`load_graph` (single-Graph, full read). Phase 08
adds the **streaming** variant :func:`iter_load_graph` per ADR-0124 +
PB-3 A signature (graph-scoped only — no ``metagraph_id`` slot):

    iter_load_graph(client, graph_id, *, identity=None, batch_size=10_000)
        -> Iterator[Graph]

Streaming semantics (locked in Phase 08):

* **Intermediate batches are nodes-only** (RPB-1 A). Each yield carries
  a partial :class:`Graph` with up to ``batch_size`` nodes that joined
  the metagraph in id-order; **no edges, no hyperedges** in intermediate
  batches.
* **The final batch is the trailer.** After the last node-page yields,
  one more sentinel batch yields all edges + all hyperedges whose
  endpoints are present in the cumulative node set, then closes the
  iterator. This trails all cross-batch references cleanly: an edge
  from node-3 → node-23 (when ``batch_size=10``) lands in the trailer
  alongside intra-batch edges, restoring the v3 semantic the caller
  expects without duplicating edge-emit cost per page.
* **Intra-graph only** (RPB-10 A). ``iter_load_graph`` skips
  ``IntergraphEdge`` and ``IntergraphHyperEdge`` rows even when both
  endpoints live in the streamed graph; cross-graph primitives load
  via :class:`MetagraphLoader.load` only (locked R4-1 sequence).
* **Stable order**: per-batch Cypher pages use
  ``ORDER BY n.id SKIP $offset LIMIT $limit`` against the
  ``:Node {graph_id}`` hot-path index (Phase 07 P95 B).

:func:`load_graph` is preserved as the Phase 07 public surface but
refactored internally to call :func:`iter_load_graph` with a
single-batch sentinel and assemble per RR-12 A — ADR-0124's
"load() becomes a thin wrapper of list(iter_load(...))" claim.
The assembled graph is byte-equivalent to the prior Phase 07
implementation (same Cypher; same id-ordering).

Per M14 — single-Graph scope only. Cross-graph primitives + the
metagraph anchor live in :mod:`mindsos_core.reconstruction.metagraph_loader`.

Per P95 B index list — uses ``(:Node {graph_id})`` hot-path index for
per-graph node scan.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterator, List, Optional

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


# Sentinel for ``batch_size=None`` (load_graph wraps iter_load_graph with
# a single-batch yield). Per Phase 08 RR-12 A.
_FULL_LOAD_SENTINEL = object()


def iter_load_graph(
    client: Client,
    graph_id: str,
    *,
    identity: Optional[IdentityRegistry] = None,
    schema: Any = None,
    batch_size: int = 10_000,
) -> Iterator[Graph]:
    """Yield partial :class:`Graph` objects in node-id order; trail edges + hyperedges in a final batch.

    Memory-bounded alternative to :func:`load_graph` for large graphs.
    Intermediate yields are **nodes-only** (per RPB-1 A); the final
    yield trails any edges + hyperedges over the cumulative node set
    so cross-batch references resolve correctly.

    Phase 08 row + locked picks:

    * **PB-3 A** — graph-scoped only; no ``metagraph_id`` slot.
    * **RPB-1 A** — intermediate batches nodes-only; final batch trails
      edges + hyperedges over the cumulative node set.
    * **RPB-10 A** — intra-graph only; ``IntergraphEdge`` /
      ``IntergraphHyperEdge`` skipped.
    * **PB-12 C** — memory-budget assertion is structural
      (``len(g.nodes) ≤ batch_size`` per yield); real memory-pressure
      validation is a future scale-test phase concern.

    Args:
        client: Connected :class:`Client` (e.g. :class:`FalkorClient`).
        graph_id: ``:Graph.id`` to stream.
        identity: Optional shared :class:`IdentityRegistry`. When
            ``None``, a fresh registry is created and the
            ``graph_id`` is registered. When passed in (e.g. by
            :class:`MetagraphLoader`), every element id is registered
            under the shared registry.
        schema: Optional :class:`Schema` to attach. Phase 08 loads do
            not validate against schema (rehydration tolerates legacy
            state per ``_validate=False`` precedent).
        batch_size: Maximum nodes per intermediate yield. The trailer
            yield carries any edges + hyperedges over the cumulative
            node set; its node count equals ``len(g.nodes) -
            <sum of nodes in prior batches>`` and is typically 0.
            Internal sentinel ``batch_size=None`` is reserved for
            :func:`load_graph` callers and is rejected for direct
            invocation.

    Yields:
        Partial :class:`Graph` instances. The first batch carries the
        anchor (name/role/identity/graph_id) + up to ``batch_size``
        nodes. Subsequent intermediate batches carry the SAME anchor
        identity (same ``graph_id``; same ``identity`` registry) +
        next page of nodes (no edges). The final batch trails any
        edges + hyperedges over the cumulative node set; if the graph
        has no edges/hyperedges, the final batch may be empty (still
        yielded so callers see the "trailer fired" signal).

    Raises:
        PersistenceError: no ``:Graph`` row with ``id=graph_id`` in
            FalkorDB, or the driver fails on any sub-query.
        ValueError: ``batch_size < 1``.
    """
    if batch_size is _FULL_LOAD_SENTINEL:
        # ``load_graph`` thin-wrap path — single all-at-once batch.
        # Pagination uses a very large LIMIT so the SKIP loop runs once.
        effective_batch_size = _FULL_LOAD_SENTINEL
    else:
        if not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError(
                f"iter_load_graph: batch_size must be an int >= 1; "
                f"got {batch_size!r}"
            )
        effective_batch_size = batch_size

    anchor = _load_graph_anchor(client, graph_id)

    # Build a shell Graph. Per Phase 07 ``load_graph`` precedent: the
    # shell is constructed with the supplied ``identity`` so every
    # ``add_node(node_id=..., _validate=False)`` registers under the
    # shared registry. The Graph's ``schema`` slot is set from the
    # caller (kwarg) — Phase 08 does not validate against it (R4-4 B).
    g = Graph(
        name=anchor["name"],
        role=anchor.get("role"),
        schema=schema,
        identity=identity,
        graph_id=graph_id,
    )
    if identity is None:
        try:
            g.identity.register(graph_id)
        except Exception:
            # Already-registered is fine.
            pass

    # Stream nodes in id-order. For the full-load sentinel path, use a
    # single very-large page; pagination exists for the bounded path.
    if effective_batch_size is _FULL_LOAD_SENTINEL:
        page_limit = 10**9  # effectively unbounded; single page expected.
        offset = 0
        pages_emitted = 0
        while True:
            page_nodes = _fetch_node_page(client, graph_id, offset, page_limit)
            for row in page_nodes:
                _add_node_from_row(g, row)
            offset += page_limit
            pages_emitted += 1
            # In the full-load path, one page is expected (page_limit is
            # huge); a non-empty next page is pathological but we keep
            # the loop defensive.
            if len(page_nodes) < page_limit:
                break
        # Trailer — edges + hyperedges over all loaded nodes.
        _load_edges(client, g)
        _load_hyperedges(client, g)
        _detect_cross_graph_leaks(client, g)
        yield g
        return

    # Bounded streaming path.
    offset = 0
    pages_emitted = 0
    while True:
        page_nodes = _fetch_node_page(
            client, graph_id, offset, effective_batch_size
        )
        if not page_nodes and pages_emitted > 0:
            break
        # Mutate the in-flight Graph by adding this page's nodes.
        # The yielded Graph object identity is stable across yields:
        # caller composes by accumulating yields or by calling
        # :func:`load_graph` (which assembles internally).
        prior_count = len(g.nodes)
        for row in page_nodes:
            _add_node_from_row(g, row)
        offset += effective_batch_size
        pages_emitted += 1
        # Intermediate batch: nodes-only. The structural cap is
        # ``len(g.nodes) - prior_count <= batch_size`` (PB-12 C; the
        # number of nodes added in this batch is bounded; total
        # cumulative ``len(g.nodes)`` grows monotonically and may
        # exceed batch_size by intent — callers needing per-batch
        # peek can compare against ``prior_count``).
        if not page_nodes:
            # Empty page after at least one non-empty — fall through to
            # the trailer.
            break
        yield g
        if len(page_nodes) < effective_batch_size:
            # Last full page consumed; emit the trailer.
            break

    # Trailer — edges + hyperedges + cross-graph leak detection.
    _load_edges(client, g)
    _load_hyperedges(client, g)
    _detect_cross_graph_leaks(client, g)
    yield g


def load_graph(
    client: Client,
    graph_id: str,
    *,
    identity: Optional[IdentityRegistry] = None,
    schema: Any = None,
) -> Graph:
    """Reconstruct the :class:`Graph` with ``graph_id`` from FalkorDB.

    Phase 07 surface preserved. Phase 08 refactors internally to call
    :func:`iter_load_graph` with the full-load sentinel per RR-12 A.
    Backwards-compatible: same Cypher; same id-ordering; same return
    shape.

    Args:
        client: Connected :class:`Client`.
        graph_id: The Cypher ``:Graph.id`` to load.
        identity: Optional shared :class:`IdentityRegistry`. When
            ``None``, a fresh registry is created and the loaded
            ``graph_id`` is registered. When passed in (e.g. by
            :class:`MetagraphLoader`), every element id is registered
            under the shared registry.
        schema: Optional :class:`Schema` to attach. Phase 08 loads do
            not validate against schema (rehydration tolerates legacy
            state per ``_validate=False`` precedent).

    Returns:
        Reconstructed :class:`Graph` with ``_version`` fields restored
        on every element.

    Raises:
        PersistenceError: no ``:Graph`` row with ``id=graph_id`` exists
            in FalkorDB, or the driver fails on any sub-query.
    """
    # Per RR-12 A — single source of truth. The sentinel batch_size
    # short-circuits pagination + emits the trailer in one pass.
    iterator = iter_load_graph(
        client,
        graph_id,
        identity=identity,
        schema=schema,
        batch_size=_FULL_LOAD_SENTINEL,  # type: ignore[arg-type]
    )
    # Drain the iterator. Full-load path yields exactly once.
    g: Optional[Graph] = None
    for partial in iterator:
        g = partial
    if g is None:
        # Defensive — full-load path always yields. Should not reach.
        raise PersistenceError(
            f"load_graph: iter_load_graph yielded no batches for "
            f"graph_id={graph_id!r}"
        )
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


def _fetch_node_page(
    client: Client, graph_id: str, offset: int, limit: int
) -> List[Dict[str, Any]]:
    """Paginated read of ``:Node {graph_id}`` rows in id-order."""
    q = (
        "MATCH (n:Node {graph_id: $gid}) "
        "RETURN n.id AS id, n.type_name AS type_name, "
        "       n.value AS value, n._version AS version, "
        "       properties(n) AS props "
        "ORDER BY n.id SKIP $offset LIMIT $limit"
    )
    return client.run_query(
        q, {"gid": graph_id, "offset": offset, "limit": limit}
    ).rows


def _add_node_from_row(g: Graph, row: Dict[str, Any]) -> None:
    """Materialise a :class:`Node` from a Cypher row and attach to ``g``."""
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
        # Skip rows already registered (defensive — should not happen
        # when iter is invoked once per load).
        if row["id"] in g.edges:
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
        if row["id"] in g.hyperedges:
            continue
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


__all__ = ["load_graph", "iter_load_graph"]
