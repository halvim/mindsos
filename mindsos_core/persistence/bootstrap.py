"""Bootstrap: create indexes required by the Core Layer (Phase 07).

Run lazily once per :class:`FalkorClient` construction (P2 A). Safe to
re-run — every statement uses ``CREATE INDEX IF NOT EXISTS`` (P42 B);
already-exists errors are also caught defensively for FalkorDB versions
that don't honour the ``IF NOT EXISTS`` clause.

Per P95 B — **14 indexes total**:

* **10 node-label `id` indexes**: ``:Metagraph``, ``:Graph``, ``:Node``,
  ``:HyperEdge``, ``:MetaHyperEdge``, ``:IntergraphHyperEdge``,
  ``:ElementInstance``, ``:CompositeInstance``, ``:Tombstone``
  (indexed on ``graph_id``; per-(graph, element) shape per P69 A
  uses a compound key but the secondary index on ``graph_id`` carries
  the persist-time check), ``:WALEntry`` (indexed on ``operation_id``).
* **3 relationship-type `id` indexes** per ADR-0021: ``:Edge``,
  ``:MetaEdge``, ``:IntergraphEdge``. Per P89 A — FalkorDB v4.18.3
  relationship-index syntax is ``CREATE INDEX FOR ()-[r:Edge]-() ON
  (r.id)``. Step 0 probe confirms support.
* **1 hot-path index**: ``:Node {graph_id}`` for persist-time check
  per ADR-0123 §2 (single-graph scan cost). Other hot-path indexes
  (graph_id on additional labels; metagraph_id) deferred to Phase 08
  when streaming/loader drives the actual scan needs.

Total: 14.
"""

from __future__ import annotations

from typing import List, Literal, Tuple

from ..exceptions import PersistenceError
from .client import Client


#: Index kind: "node" → ``CREATE INDEX FOR (n:Label) ON (n.prop)``;
#: "rel" → ``CREATE INDEX FOR ()-[r:RelType]-() ON (r.prop)``.
IndexKind = Literal["node", "rel"]


#: 14 indexes per P95 B. Ordering: anchors first, then elements, then
#: instance kinds, then relationship types, then the hot-path index.
DEFAULT_INDEXES: List[Tuple[IndexKind, str, str]] = [
    # ── 10 node-label id indexes ───────────────────────────────────
    ("node", "Metagraph", "id"),
    ("node", "Graph", "id"),
    ("node", "Node", "id"),
    ("node", "HyperEdge", "id"),
    ("node", "MetaHyperEdge", "id"),
    ("node", "IntergraphHyperEdge", "id"),
    ("node", "ElementInstance", "id"),
    ("node", "CompositeInstance", "id"),
    # Tombstone is keyed per-(graph, element) per P69 A; the graph_id
    # secondary index is what persist-time check needs.
    ("node", "Tombstone", "graph_id"),
    # WALEntry's primary key is operation_id (UUID per row).
    ("node", "WALEntry", "operation_id"),
    # ── 3 relationship-type id indexes (ADR-0021 rel types) ───────
    ("rel", "Edge", "id"),
    ("rel", "MetaEdge", "id"),
    ("rel", "IntergraphEdge", "id"),
    # ── 1 hot-path index per ADR-0123 §2 ──────────────────────────
    ("node", "Node", "graph_id"),
]


def _ddl_for(kind: IndexKind, label: str, prop: str) -> str:
    """Render the ``CREATE INDEX IF NOT EXISTS`` DDL for one entry.

    Per P89 A — relationship-index syntax differs from node-label syntax
    in FalkorDB v4.18.3. Step 0 probe confirms both forms supported with
    the ``IF NOT EXISTS`` clause.
    """
    if kind == "node":
        return f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.{prop})"
    # kind == "rel"
    return f"CREATE INDEX IF NOT EXISTS FOR ()-[r:{label}]-() ON (r.{prop})"


def bootstrap(client: Client) -> None:
    """Create all 14 indexes idempotently.

    Best-effort: per-statement failures matching known
    "already exists" / "indexed" patterns are swallowed so re-running
    against an older FalkorDB that doesn't honour ``IF NOT EXISTS``
    still completes. Other errors raise :class:`PersistenceError`.
    """
    for kind, label, prop in DEFAULT_INDEXES:
        query = _ddl_for(kind, label, prop)
        try:
            client.run_query(query)
        except PersistenceError as exc:
            msg = str(exc).lower()
            if "already" in msg or "exist" in msg or "indexed" in msg:
                continue
            raise


__all__ = [
    "DEFAULT_INDEXES",
    "IndexKind",
    "bootstrap",
]
