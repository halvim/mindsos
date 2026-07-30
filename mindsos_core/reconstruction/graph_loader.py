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
import os
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Tuple

from ..exceptions import PersistenceError, UnknownEdgeTypeError
from ..models.graph import Graph
from ..models.identity import IdentityRegistry
from ..persistence.client import Client
from ..persistence.value_codec import decode_node_value
from .load_report import LoadReport

_log = logging.getLogger(__name__)


# ── Phase 11 — loader policy (ADR-0134 §amendment-2) ─────────────────────────


#: Default loader policy if neither the kwarg nor the env var is set.
#: Per ADR-0134: "default flips from silent ignore to warn."
_DEFAULT_UNKNOWN_EDGE_POLICY = "warn"

#: Recognised values for ``unknown_edge_type_policy``.
_VALID_UNKNOWN_EDGE_POLICIES = ("warn", "error", "ignore")

#: Env var override (Phase 11 PB-14 A; symmetric with
#: ``feedback_cli_config_manifest_fallback.md`` — env wins over default).
_UNKNOWN_EDGE_POLICY_ENV = "MINDSOS_UNKNOWN_EDGE_POLICY"


def _resolve_unknown_edge_policy(arg: Optional[str]) -> str:
    """Resolve ``unknown_edge_type_policy`` per Phase 11 PB-14 A precedence.

    Per-call kwarg wins → env var fallback → hard-coded default
    (``"warn"``). Raises :class:`ValueError` on an unrecognised value
    from either source.
    """
    if arg is not None:
        if arg not in _VALID_UNKNOWN_EDGE_POLICIES:
            raise ValueError(
                f"unknown_edge_type_policy must be one of "
                f"{_VALID_UNKNOWN_EDGE_POLICIES}; got {arg!r}"
            )
        return arg
    env_val = os.environ.get(_UNKNOWN_EDGE_POLICY_ENV)
    if env_val is not None:
        if env_val not in _VALID_UNKNOWN_EDGE_POLICIES:
            raise ValueError(
                f"{_UNKNOWN_EDGE_POLICY_ENV} must be one of "
                f"{_VALID_UNKNOWN_EDGE_POLICIES}; got {env_val!r}"
            )
        return env_val
    return _DEFAULT_UNKNOWN_EDGE_POLICY


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
    # Phase 50 — ADR-0182. Node-level JSON-encoded structured-value
    # column; decoded into ``value`` by ``_add_node_from_row``, never
    # surfaced in the user-property bag.
    "_value_json",
    # Phase 10 — ADR-0133 soft-delete fields are typed dataclass attrs,
    # not user-property bag keys.
    "deprecated_at",
    "disputed_at",
})


def _parse_iso(value: Any) -> Optional[datetime]:
    """Parse an ISO-8601 datetime string or pass through ``None`` / ``datetime``.

    Phase 10 ADR-0133 helper — mirrors
    :func:`mindsos_core.reconstruction.metagraph_loader._parse_iso`. Loaders
    read soft-delete fields out of ``properties(row)`` driver dicts and
    recover the in-memory ``datetime`` instance.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None
    return None


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
    include_deprecated: bool = False,
    report: Optional[LoadReport] = None,
    unknown_edge_type_policy: Optional[str] = None,
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
        _policy = _resolve_unknown_edge_policy(unknown_edge_type_policy)
        _load_edges(
            client, g,
            include_deprecated=include_deprecated,
            report=report,
            unknown_edge_type_policy=_policy,
        )
        _load_hyperedges(
            client, g,
            include_deprecated=include_deprecated,
            report=report,
            unknown_edge_type_policy=_policy,
        )
        _detect_cross_graph_leaks(client, g)
        # Phase 10 PB-6a — clear graph-side soft-delete dirty after full
        # load (loader-attached path; symmetric with MetagraphLoader path).
        for kind in g._soft_delete_dirty:
            g._soft_delete_dirty[kind].clear()
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
    _policy = _resolve_unknown_edge_policy(unknown_edge_type_policy)
    _load_edges(
        client, g,
        include_deprecated=include_deprecated,
        report=report,
        unknown_edge_type_policy=_policy,
    )
    _load_hyperedges(
        client, g,
        include_deprecated=include_deprecated,
        report=report,
        unknown_edge_type_policy=_policy,
    )
    _detect_cross_graph_leaks(client, g)
    # Phase 10 PB-6a — clear graph-side soft-delete dirty after streamed load.
    for kind in g._soft_delete_dirty:
        g._soft_delete_dirty[kind].clear()
    yield g


def load_graph(
    client: Client,
    graph_id: str,
    *,
    identity: Optional[IdentityRegistry] = None,
    schema: Any = None,
    include_deprecated: bool = False,
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
        include_deprecated=include_deprecated,
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


def load_graph_with_report(
    client: Client,
    graph_id: str,
    *,
    identity: Optional[IdentityRegistry] = None,
    schema: Any = None,
    include_deprecated: bool = False,
    unknown_edge_type_policy: Optional[str] = None,
) -> Tuple[Graph, LoadReport]:
    """Phase 11 sibling of :func:`load_graph` returning a :class:`LoadReport`.

    Same load semantics as :func:`load_graph` but additionally tracks
    edge/hyperedge type drops per Phase 11 ADR-0134 §amendment-2. The
    policy is a no-op when ``schema is None`` (PB-11 lock).

    Args:
        client: Connected :class:`Client`.
        graph_id: The Cypher ``:Graph.id`` to load.
        identity: Optional shared :class:`IdentityRegistry`.
        schema: Optional :class:`Schema` to attach. When provided AND
            ``unknown_edge_type_policy != "ignore"``, edges /
            hyperedges whose ``type_name`` is absent from the schema
            are filtered per policy.
        include_deprecated: Phase 10 ADR-0133 — when ``False``
            (default), soft-deleted elements are excluded.
        unknown_edge_type_policy: ``"warn"`` (default; per-distinct
            WARN with counts), ``"error"`` (raise
            :class:`UnknownEdgeTypeError` on first unknown type), or
            ``"ignore"`` (silent drop). When ``None``, resolves from
            ``MINDSOS_UNKNOWN_EDGE_POLICY`` env var, then to
            ``"warn"`` per ADR-0134's "default flips" lock.

    Returns:
        ``(graph, report)``. The ``graph`` is identical to what
        :func:`load_graph` would return (modulo any rows filtered by
        policy under ``warn``/``error``). The ``report`` carries
        per-distinct-type drop counts.

    Raises:
        PersistenceError: anchor missing or driver fails.
        UnknownEdgeTypeError: ``unknown_edge_type_policy="error"`` and
            a persisted edge / hyperedge type is absent from
            ``schema``.
        ValueError: invalid ``unknown_edge_type_policy`` value.
    """
    report = LoadReport(graph_id=graph_id)
    iterator = iter_load_graph(
        client,
        graph_id,
        identity=identity,
        schema=schema,
        batch_size=_FULL_LOAD_SENTINEL,  # type: ignore[arg-type]
        include_deprecated=include_deprecated,
        report=report,
        unknown_edge_type_policy=unknown_edge_type_policy,
    )
    g: Optional[Graph] = None
    for partial in iterator:
        g = partial
    if g is None:
        raise PersistenceError(
            f"load_graph_with_report: iter_load_graph yielded no batches "
            f"for graph_id={graph_id!r}"
        )
    return g, report


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


def graph_anchors_by_role(
    client: Client,
    *,
    role_prefix: Optional[str] = None,
    name_suffix: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return ``:Graph`` anchor rows (``{id, role, name}``) matching a role prefix
    and/or a name suffix, across ALL metagraphs (Dream PRE-0 Slice 3).

    ``load_graph`` finds a graph by id, and ``MetagraphLoader.refresh`` finds
    role-graphs *within one metagraph*; neither helps when the writing
    ``metagraph_id`` is unknown -- the case for a crashed request's streamed
    grounding after a restart (its session MM object is gone, but the persisted
    ``:Graph`` rows survive with their deterministic ``role``/``name``). This
    locates them by those deterministic anchors. At least one filter is required.
    """
    clauses: List[str] = []
    params: Dict[str, Any] = {}
    if role_prefix is not None:
        clauses.append("g.role STARTS WITH $role_prefix")
        params["role_prefix"] = role_prefix
    if name_suffix is not None:
        clauses.append("g.name ENDS WITH $name_suffix")
        params["name_suffix"] = name_suffix
    if not clauses:
        raise ValueError(
            "graph_anchors_by_role requires role_prefix and/or name_suffix"
        )
    q = (
        "MATCH (g:Graph) WHERE "
        + " AND ".join(clauses)
        + " RETURN g.id AS id, g.role AS role, g.name AS name"
    )
    res = client.run_query(q, params)
    return list(res.rows)


def _fetch_node_page(
    client: Client, graph_id: str, offset: int, limit: int
) -> List[Dict[str, Any]]:
    """Paginated read of ``:Node {graph_id}`` rows in id-order."""
    q = (
        "MATCH (n:Node {graph_id: $gid}) "
        "RETURN n.id AS id, n.type_name AS type_name, "
        "       n.value AS value, n._value_json AS value_json, "
        "       n._version AS version, "
        "       properties(n) AS props "
        "ORDER BY n.id SKIP $offset LIMIT $limit"
    )
    return client.run_query(
        q, {"gid": graph_id, "offset": offset, "limit": limit}
    ).rows


def _add_node_from_row(g: Graph, row: Dict[str, Any]) -> None:
    """Materialise a :class:`Node` from a Cypher row and attach to ``g``.

    Phase 50 ADR-0182 rule 3 — a non-NULL ``value_json`` column is the
    structured-value discriminator: decode it as ``value``; otherwise
    the primitive ``value`` column passes through (fast path).
    """
    props = _strip_core_keys(row.get("props") or {})
    node = g.add_node(
        value=decode_node_value(row.get("value"), row.get("value_json")),
        type_name=row["type_name"],
        properties=props,
        node_id=row["id"],
        _validate=False,
    )
    if row.get("version") is not None:
        node._version = int(row["version"])


def _load_edges(
    client: Client,
    g: Graph,
    *,
    include_deprecated: bool = False,
    report: Optional[LoadReport] = None,
    unknown_edge_type_policy: str = _DEFAULT_UNKNOWN_EDGE_POLICY,
) -> None:
    """Load edges where both endpoints live in this graph.

    Cross-graph rows skipped here; logged in
    :func:`_detect_cross_graph_leaks` for operator visibility.

    Phase 10 ADR-0133 — when ``include_deprecated=False`` (default),
    appends ``AND e.deprecated_at IS NULL`` to the WHERE clause.
    Soft-delete fields round-tripped from row props onto the dataclass
    post-construction.

    Phase 11 ADR-0134 — when ``report`` is provided AND ``g.schema``
    is non-None, edges whose ``type_name`` is absent from
    :attr:`Schema.edge_types` are filtered per
    ``unknown_edge_type_policy``:

    * ``warn`` — drop + record in ``report``; one WARN per distinct
      type with running counts (PB-10 A per-distinct-type granularity).
    * ``error`` — record in ``report`` and raise
      :class:`UnknownEdgeTypeError` on first hit.
    * ``ignore`` — silent drop (still records in ``report`` for
      observability symmetry with ``warn``).

    Policy is a no-op when ``g.schema is None`` (PB-11 lock) OR when
    ``report is None`` (preserves existing :func:`load_graph` behavior).
    """
    # Phase 10 — conditional WHERE clause.
    where_extra = "" if include_deprecated else " AND e.deprecated_at IS NULL"
    q = (
        "MATCH (s:Node {graph_id: $gid})-[e]->(t:Node {graph_id: $gid}) "
        f"WHERE e.graph_id = $gid AND e.id IS NOT NULL{where_extra} "
        "RETURN e.id AS id, e.type_name AS type_name, e.label AS label, "
        "       e._version AS version, "
        "       s.id AS source_id, t.id AS target_id, properties(e) AS props"
    )
    res = client.run_query(q, {"gid": g.graph_id})
    # Phase 11 — track per-distinct-type WARN emission so each type
    # surfaces exactly once (PB-10 A).
    warned_types: set = set()
    schema_active = report is not None and g.schema is not None
    known_edge_types = (
        set(g.schema.edge_types.keys()) if schema_active else None
    )
    for row in res.rows:
        # Phase 11 — schema-aware filter BEFORE node lookup.
        if schema_active and row["type_name"] not in known_edge_types:
            _apply_unknown_edge_policy(
                graph_id=g.graph_id,
                type_name=row["type_name"],
                element_kind="Edge",
                report=report,
                policy=unknown_edge_type_policy,
                warned_types=warned_types,
            )
            continue
        src = g.nodes.get(row["source_id"])
        tgt = g.nodes.get(row["target_id"])
        if src is None or tgt is None:
            _log.warning(
                "Edge %r in graph %r references missing node "
                "(src=%r tgt=%r); skipping",
                row["id"], g.graph_id, row["source_id"], row["target_id"],
            )
            continue
        if row["id"] in g.edges:
            continue
        # Phase 10 — extract soft-delete fields BEFORE strip.
        raw_props = row.get("props") or {}
        dep_at = _parse_iso(raw_props.get("deprecated_at"))
        dis_at = _parse_iso(raw_props.get("disputed_at"))
        props = _strip_core_keys(raw_props)
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
        # Phase 10 — restore soft-delete fields onto the dataclass.
        edge.deprecated_at = dep_at
        edge.disputed_at = dis_at
    # Phase 11 — emit final per-distinct-type WARN with totals (PB-10 A).
    if report is not None and warned_types:
        for type_name in sorted(warned_types):
            count = report.dropped_by_type.get(type_name, 0)
            _log.warning(
                "dropped %d edge(s) of unknown type %r in graph %r "
                "(policy=warn; schema does not list this edge type)",
                count, type_name, g.graph_id,
            )


def _load_hyperedges(
    client: Client,
    g: Graph,
    *,
    include_deprecated: bool = False,
    report: Optional[LoadReport] = None,
    unknown_edge_type_policy: str = _DEFAULT_UNKNOWN_EDGE_POLICY,
) -> None:
    """Load hyperedges with their :MEMBER edges in a single round-trip.

    Phase 10 ADR-0133 — when ``include_deprecated=False`` (default),
    WHERE clause filters ``h.deprecated_at IS NULL``. Soft-delete fields
    round-tripped from props onto the dataclass post-construction.

    Phase 11 ADR-0134 — same policy semantics as :func:`_load_edges`,
    against :attr:`Schema.hyperedge_types`. ``element_kind="HyperEdge"``
    in any raised :class:`UnknownEdgeTypeError` and dropped-by-type
    keys are HyperEdge type names.
    """
    # Phase 10 — conditional WHERE clause.
    where_extra = "" if include_deprecated else " WHERE h.deprecated_at IS NULL"
    q = (
        "MATCH (h:HyperEdge {graph_id: $gid}) "
        f"{where_extra} "
        "OPTIONAL MATCH (h)-[:MEMBER]->(n:Node) "
        "WITH h, collect(n.id) AS member_ids "
        "RETURN h.id AS id, h.type_name AS type_name, h.label AS label, "
        "       h._version AS version, properties(h) AS props, member_ids"
    )
    res = client.run_query(q, {"gid": g.graph_id})
    # Phase 11 — per-distinct-type WARN bookkeeping.
    warned_types: set = set()
    schema_active = report is not None and g.schema is not None
    known_hyperedge_types = (
        set(g.schema.hyperedge_types.keys()) if schema_active else None
    )
    for row in res.rows:
        # Phase 11 — schema-aware filter.
        row_type = row.get("type_name") or "UNSPECIFIED"
        if schema_active and row_type not in known_hyperedge_types:
            _apply_unknown_edge_policy(
                graph_id=g.graph_id,
                type_name=row_type,
                element_kind="HyperEdge",
                report=report,
                policy=unknown_edge_type_policy,
                warned_types=warned_types,
            )
            continue
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
        # Phase 10 — extract soft-delete fields BEFORE strip.
        raw_props = row.get("props") or {}
        dep_at = _parse_iso(raw_props.get("deprecated_at"))
        dis_at = _parse_iso(raw_props.get("disputed_at"))
        props = _strip_core_keys(raw_props)
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
        # Phase 10 — restore soft-delete fields.
        h.deprecated_at = dep_at
        h.disputed_at = dis_at
    # Phase 11 — emit final per-distinct-type WARN with totals (PB-10 A).
    if report is not None and warned_types:
        for type_name in sorted(warned_types):
            count = report.dropped_by_type.get(type_name, 0)
            _log.warning(
                "dropped %d hyperedge(s) of unknown type %r in graph %r "
                "(policy=warn; schema does not list this hyperedge type)",
                count, type_name, g.graph_id,
            )


def _apply_unknown_edge_policy(
    *,
    graph_id: str,
    type_name: str,
    element_kind: str,
    report: LoadReport,
    policy: str,
    warned_types: set,
) -> None:
    """Apply ``unknown_edge_type_policy`` to a single drop (Phase 11).

    Always records the drop in ``report`` (so ``ignore`` callers can
    still inspect counts if they passed a report). Then:

    * ``error`` — raise :class:`UnknownEdgeTypeError` immediately.
    * ``warn`` — mark the type in ``warned_types`` for a per-distinct
      summary WARN at end-of-load (PB-10 A granularity).
    * ``ignore`` — no log emission.
    """
    report.add_drop(type_name)
    if policy == "error":
        raise UnknownEdgeTypeError(
            graph_id=graph_id,
            type_name=type_name,
            element_kind=element_kind,
        )
    if policy == "warn":
        warned_types.add(type_name)
    # ``ignore`` — silent.


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


__all__ = [
    "load_graph",
    "iter_load_graph",
    "load_graph_with_report",
]
