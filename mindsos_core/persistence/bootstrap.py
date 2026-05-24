"""Bootstrap: create indexes + register WAL replayers (Phase 07 + Phase 09).

Run lazily once per :class:`FalkorClient` construction (P2 A). Safe to
re-run — the bare ``CREATE INDEX FOR`` syntax is the only form FalkorDB
v4.18.3 accepts (Step 0 probe B-07-T1 2026-05-13 confirmed
``CREATE INDEX IF NOT EXISTS`` is a hard syntax error in the Cypher
parser, not an "already exists" run-time error). Idempotency comes from
the defensive try/except that catches the
``Attribute 'id' is already indexed`` error returned on re-create.

**Phase 07 ships 14 indexes per P95 B:**

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
  per ADR-0123 §2.

**Phase 09 adds 4 `:XRef` indexes per M15 (bootstrap grows 14 → 18):**

* ``:XRef {id}`` — primary lookup by xref id.
* ``:XRef {source_metagraph_id}`` — XRefLoader query
  ``MATCH (x:XRef {source_metagraph_id: $mid})``.
* ``:XRef {source_id}`` — forward walk
  (``mg.iter_xrefs(source_id=...)``).
* ``:XRef {target_metagraph_id, target_id}`` compound — reverse walk
  (``mg.iter_xrefs(target_metagraph_id=..., target_id=...)``) +
  ``--target-metagraph`` filter via prefix-match (RPB-5; tester probe
  P56 verifies prefix-match works on FalkorDB v4.18.3).

**Phase 09 WAL replayers** registered via
:func:`register_all_l1_replayers` per RR-16. Per-kind modules own
their registration; this central wrapper composes them. Phase 10/11
extend the wrapper as new replayer kinds ship.
"""

from __future__ import annotations

from typing import List, Literal, Tuple, Union

from ..exceptions import PersistenceError
from .client import Client


#: Index kind: "node" → ``CREATE INDEX FOR (n:Label) ON (n.prop)``;
#: "rel" → ``CREATE INDEX FOR ()-[r:RelType]-() ON (r.prop)``.
IndexKind = Literal["node", "rel"]

#: A single property name, or a tuple of property names for a compound
#: index. Compound rendering: ``ON (n.p1, n.p2)``.
IndexProp = Union[str, Tuple[str, ...]]


#: 19 indexes total: 14 from Phase 07 + 4 :XRef from Phase 09 (M15)
#: + 1 hot-path :Metagraph.name from Phase 26a (ADR-0123 §am1).
#: Ordering: anchors first, then elements, then instance kinds, then
#: relationship types, then the hot-path indexes, then the Phase 09
#: :XRef block.
DEFAULT_INDEXES: List[Tuple[IndexKind, str, IndexProp]] = [
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
    # ── 2 hot-path indexes per ADR-0123 §2 + §am1 ─────────────────
    ("node", "Node", "graph_id"),
    # Phase 26a (ADR-0123 §am1): `MetagraphLoader.find_by_name(name)`
    # invoked on every CLI invocation that needs KL via
    # `bootstrap_kl_from_falkordb`. Index keeps lookup O(1) vs scan
    # of all Metagraph anchors (Global + pending + canonical + every
    # user Local).
    ("node", "Metagraph", "name"),
    # ── 4 :XRef indexes (Phase 09 M15) ─────────────────────────────
    ("node", "XRef", "id"),
    ("node", "XRef", "source_metagraph_id"),
    ("node", "XRef", "source_id"),
    # Compound (target_metagraph_id, target_id) — reverse-walk index +
    # prefix-match for --target-metagraph alone (RPB-5). Tester probe
    # P56 verifies FalkorDB v4.18.3 accepts the syntax + executes
    # prefix-match against the compound; if it fails, fallback to
    # 5-index ship per P56 option C (split into single + compound).
    ("node", "XRef", ("target_metagraph_id", "target_id")),
]


def _ddl_for(kind: IndexKind, label: str, prop: IndexProp) -> str:
    """Render the ``CREATE INDEX FOR`` DDL for one entry.

    Per P89 A + B-07-T1 hotfix (2026-05-13): relationship-index syntax
    differs from node-label syntax. FalkorDB v4.18.3 does NOT support
    ``CREATE INDEX IF NOT EXISTS`` (Cypher parser rejects ``IF NOT EXISTS``
    as a syntax error); idempotency comes from the defensive try/except
    in :func:`bootstrap` that swallows the
    ``Attribute 'id' is already indexed`` re-create error.

    Phase 09 adds compound-index rendering: when ``prop`` is a tuple,
    emits ``ON (n.p1, n.p2, ...)``.
    """
    var = "n" if kind == "node" else "r"
    if isinstance(prop, tuple):
        prop_text = ", ".join(f"{var}.{p}" for p in prop)
    else:
        prop_text = f"{var}.{prop}"
    if kind == "node":
        return f"CREATE INDEX FOR (n:{label}) ON ({prop_text})"
    # kind == "rel"
    return f"CREATE INDEX FOR ()-[r:{label}]-() ON ({prop_text})"


def bootstrap(client: Client) -> None:
    """Create all 18 indexes idempotently (14 Phase 07 + 4 :XRef Phase 09).

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


def register_all_l1_replayers(client: Client) -> None:
    """Register every L1-owned WAL replayer on ``client`` (Phase 09 RR-16 + Phase 10 M8).

    Per-kind modules own their registration function; this central
    wrapper composes them.

    **Phase 10 — wrapper grows 2 → 10 kinds** per M8:

    * Phase 09 (2 kinds): ``xref_add`` + ``xref_remove`` via
      :func:`mindsos_core.persistence.xref_repository.register_xref_replayers`.
    * Phase 10 XRef-side (4 kinds, PX2): ``xref_mark_stale`` /
      ``xref_unmark_stale`` / ``xref_deprecate`` / ``xref_undeprecate`` —
      extension of the same ``register_xref_replayers`` function (2 → 6).
    * Phase 10 element-side (4 kinds, M8): ``element_deprecate`` /
      ``element_undeprecate`` / ``element_dispute`` / ``element_undispute``
      via :func:`mindsos_core.persistence.soft_delete.register_soft_delete_replayers`.

    Called by :class:`FalkorClient.__init__` immediately after
    :func:`bootstrap`. ``InMemoryClient`` may invoke it explicitly in
    tests that exercise WAL recovery (per Phase 09 RR-16).
    """
    # Late imports — break the bootstrap → xref_repository → builders →
    # ... cycle.
    from .soft_delete import register_soft_delete_replayers
    from .xref_repository import register_xref_replayers

    register_xref_replayers(client)  # 6 kinds (2 Phase 09 + 4 Phase 10 PX2)
    register_soft_delete_replayers(client)  # 4 Phase 10 element-side kinds


__all__ = [
    "DEFAULT_INDEXES",
    "IndexKind",
    "IndexProp",
    "bootstrap",
    "register_all_l1_replayers",
]
