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

* Strips direct ``InstanceRepository`` call — replaced by observer
  (M9).
* ``_props_json`` write wraps in narrow chained driver-exception
  catch per P97 B (no size cap per P83 C).
* ``schema_name`` persisted as plain Cypher property using the
  existing ``mg.schema_name`` dataclass field per P100 A (no
  ``:MetagraphSchema`` labeled node; no ``:HAS_SCHEMA`` edge).
* Programmatic-only — no CLI verb in 07 (P60 A); metagraph sync
  CLI lands Phase 08 per M14/P12 D.

**Phase 09 changes (RR-17 + P54 dirty-tracking):**

* New Step 1g — drains ``mg._xrefs_dirty`` via
  :class:`XRefRepository`. Inline-persisted XRefs (added via
  ``add_xref`` while ``mg._persist_client`` was set) are NOT in the
  dirty set, so this step is a no-op for the loader-attached path.
  Programmatic ``add_xref`` (no client attached) populates the dirty
  set; this step writes those entries. P54 atomic-clear: dirty set is
  cleared at end-of-loop, not per-entry — partial-crash mid-loop
  retries the whole set on next persist (MERGE-idempotent so safe).
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
    # Phase 10 — soft-delete drain (per-method builders, PB-4a).
    build_set_edge_deprecated_at,
    build_set_edge_disputed_at,
    build_set_hyperedge_deprecated_at,
    build_set_hyperedge_disputed_at,
    build_set_metaedge_deprecated_at,
    build_set_metaedge_disputed_at,
    build_set_metahyperedge_deprecated_at,
    build_set_metahyperedge_disputed_at,
    build_set_xref_deprecated_at,
    build_set_xref_target_stale,
    build_unset_edge_deprecated_at,
    build_unset_edge_disputed_at,
    build_unset_hyperedge_deprecated_at,
    build_unset_hyperedge_disputed_at,
    build_unset_metaedge_deprecated_at,
    build_unset_metaedge_disputed_at,
    build_unset_metahyperedge_deprecated_at,
    build_unset_metahyperedge_disputed_at,
    build_unset_xref_deprecated_at,
    build_unset_xref_target_stale,
    build_unwind_create_intergraph_edges,
    build_unwind_create_intergraph_hyperedges,
    build_unwind_create_metaedges,
    build_unwind_create_metahyperedges,
)
from ..exceptions import PersistenceError
from ..models.metagraph import Metagraph
from .client import Client
from .graph_repository import GraphRepository
from .soft_delete import SoftDeleteKind
from .xref_repository import XRefRepository

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
        # Phase 08 B-08-T3 — row gains ``type_name`` so the builder can
        # SET it on the persisted node; Phase 07 omitted this, blocking
        # round-trip.
        if metagraph.metahyperedges:
            rows = [
                {
                    "id": mh.edge_id,
                    "type_name": mh.type_name,
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
        # Phase 08 P61 A — additively persist ``anchors`` alongside
        # ``members`` so the dataclass n_anchors >= 1 invariant survives
        # round-trip. Phase 07 wrote only the members list.
        # Phase 08 B-08-T3 — also include ``type_name`` in the row so
        # the builder can SET it on the persisted node (Phase 07
        # omitted this, breaking round-trip with CypherError on load).
        if metagraph.intergraph_hyperedges:
            rows = [
                {
                    "id": ih.edge_id,
                    "type_name": ih.type_name,
                    "label": ih.label,
                    "ordered": True,  # Phase 05c: ordered baked into type
                    "compositional": ih.compositional,
                    "props": dict(ih.properties),
                    "anchors": [
                        {"node_id": nid, "graph_id": gid}
                        for (gid, nid) in ih.anchors
                    ],
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

        # ── Step 1g: XRefs (Phase 09 RR-17 + P54 dirty-tracking). ───────
        # Drain ``_xrefs_dirty``. Entries inline-persisted by
        # ``Metagraph.add_xref`` (when ``_persist_client`` was set) are
        # NOT in this set — that path already wrote them via
        # ``XRefRepository.persist`` directly.
        if metagraph._xrefs_dirty:
            xref_repo = XRefRepository(self._client)
            for xref_id in list(metagraph._xrefs_dirty):
                xref = metagraph.xrefs.get(xref_id)
                if xref is None:
                    # Removed between add and persist; drop from dirty.
                    metagraph._xrefs_dirty.discard(xref_id)
                    continue
                xref_repo.persist(xref)
            # P54 — atomic clear at end-of-loop (only on full success).
            # Mid-loop crash leaves dirty intact; next persist retries
            # (MERGE-idempotent per PB-8 makes retry safe).
            metagraph._xrefs_dirty.clear()

        # ── Step 1h: soft-delete drain (Phase 10 — RPB-5 + RR-17). ──────
        # Drain order locked at RPB-5: EDGE → HYPEREDGE → METAEDGE →
        # METAHYPEREDGE → XREF.
        #
        # The 5 buckets live at TWO scopes per P86:
        #   * Graph-side (EDGE + HYPEREDGE): mg.graphs[*]._soft_delete_dirty
        #   * Metagraph-side (METAEDGE + METAHYPEREDGE + XREF):
        #     mg._soft_delete_dirty
        #
        # Per M17b — this drain handles the "no _persist_client at setter
        # time" path. Programmatic setter calls without a client attached
        # populate the dirty buckets; this step emits cypher for each.
        # The drain emits cypher only (no WAL) — crash-safety on the
        # programmatic path is by-design absent in Phase 10 (mirrors
        # Phase 09 _xrefs_dirty's no-WAL drain semantic; mid-drain
        # crashes lose any unflushed mutations).
        #
        # Per RPB-1 — replayer bodies (Step 13) bypass public setters and
        # call cypher builders directly. The drain here uses the same
        # builders for shape parity. Each dirty element emits 2 SET
        # statements (one per field) so the DB row matches the dataclass.
        # Atomic clear per-bucket on full success (parallels Step 1g P54).
        self._drain_soft_delete(metagraph)

        # ── Step 2: WAL commit (mechanism-only at Phase 07; no caller). ─

        # ── Step 3: observers fire (M9). ────────────────────────────────
        # Attach the active Client onto the metagraph so observer
        # callbacks (e.g. ``mindsos_instances.attach_registry``'s
        # persist hook) can locate it without a closure over us.
        # Cleared after dispatch so the metagraph object stays
        # detached between persists.
        try:
            metagraph._persist_client = self._client  # type: ignore[attr-defined]
            _dispatch_after_persist(metagraph._persist_observers, metagraph)
        finally:
            if hasattr(metagraph, "_persist_client"):
                try:
                    delattr(metagraph, "_persist_client")
                except AttributeError:
                    pass

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

    # ── Phase 10 soft-delete drain (Step 1h) ──────────────────────────────

    def _drain_soft_delete(self, metagraph: Metagraph) -> None:
        """Drain ``_soft_delete_dirty`` buckets in RPB-5 order (Phase 10).

        Order locked at RPB-5: EDGE → HYPEREDGE → METAEDGE → METAHYPEREDGE
        → XREF. Per-bucket atomic clear on full success; mid-bucket crash
        leaves remaining entries for the next persist (idempotent SET is
        safe to retry).

        Per P86 — Graph-side buckets (EDGE + HYPEREDGE) live on
        ``mg.graphs[*]._soft_delete_dirty``; Metagraph-side
        (METAEDGE / METAHYPEREDGE / XREF) on ``mg._soft_delete_dirty``.
        """
        # ── Bucket 1: EDGE (Graph-side, P86) ─────────────────────────────
        for g in metagraph.graphs.values():
            edge_ids = g._soft_delete_dirty.get(SoftDeleteKind.EDGE)
            if edge_ids:
                for eid in list(edge_ids):
                    edge = g.edges.get(eid)
                    if edge is None:
                        edge_ids.discard(eid)
                        continue
                    self._sync_pair(
                        build_set_edge_deprecated_at,
                        build_unset_edge_deprecated_at,
                        g.graph_id, eid, edge.deprecated_at,
                    )
                    self._sync_pair(
                        build_set_edge_disputed_at,
                        build_unset_edge_disputed_at,
                        g.graph_id, eid, edge.disputed_at,
                    )
                edge_ids.clear()

        # ── Bucket 2: HYPEREDGE (Graph-side, P86) ───────────────────────
        for g in metagraph.graphs.values():
            he_ids = g._soft_delete_dirty.get(SoftDeleteKind.HYPEREDGE)
            if he_ids:
                for hid in list(he_ids):
                    he = g.hyperedges.get(hid)
                    if he is None:
                        he_ids.discard(hid)
                        continue
                    self._sync_pair(
                        build_set_hyperedge_deprecated_at,
                        build_unset_hyperedge_deprecated_at,
                        g.graph_id, hid, he.deprecated_at,
                    )
                    self._sync_pair(
                        build_set_hyperedge_disputed_at,
                        build_unset_hyperedge_disputed_at,
                        g.graph_id, hid, he.disputed_at,
                    )
                he_ids.clear()

        # ── Bucket 3: METAEDGE (Metagraph-side) ─────────────────────────
        me_ids = metagraph._soft_delete_dirty.get(SoftDeleteKind.METAEDGE)
        if me_ids:
            for eid in list(me_ids):
                me = metagraph.metaedges.get(eid)
                if me is None:
                    me_ids.discard(eid)
                    continue
                self._sync_pair(
                    build_set_metaedge_deprecated_at,
                    build_unset_metaedge_deprecated_at,
                    metagraph.metagraph_id, eid, me.deprecated_at,
                )
                self._sync_pair(
                    build_set_metaedge_disputed_at,
                    build_unset_metaedge_disputed_at,
                    metagraph.metagraph_id, eid, me.disputed_at,
                )
            me_ids.clear()

        # ── Bucket 4: METAHYPEREDGE (Metagraph-side) ────────────────────
        mhe_ids = metagraph._soft_delete_dirty.get(SoftDeleteKind.METAHYPEREDGE)
        if mhe_ids:
            for mhid in list(mhe_ids):
                mhe = metagraph.metahyperedges.get(mhid)
                if mhe is None:
                    mhe_ids.discard(mhid)
                    continue
                self._sync_pair(
                    build_set_metahyperedge_deprecated_at,
                    build_unset_metahyperedge_deprecated_at,
                    metagraph.metagraph_id, mhid, mhe.deprecated_at,
                )
                self._sync_pair(
                    build_set_metahyperedge_disputed_at,
                    build_unset_metahyperedge_disputed_at,
                    metagraph.metagraph_id, mhid, mhe.disputed_at,
                )
            mhe_ids.clear()

        # ── Bucket 5: XREF (Metagraph-side; target_stale + deprecated_at) ─
        xref_ids = metagraph._soft_delete_dirty.get(SoftDeleteKind.XREF)
        if xref_ids:
            for xid in list(xref_ids):
                xref = metagraph.xrefs.get(xid)
                if xref is None:
                    xref_ids.discard(xid)
                    continue
                # target_stale is bool — use set/unset directly.
                if xref.target_stale:
                    q, p = build_set_xref_target_stale(xid)
                else:
                    q, p = build_unset_xref_target_stale(xid)
                self._client.run_query(q, p)
                # deprecated_at — datetime|None.
                self._sync_pair(
                    build_set_xref_deprecated_at,
                    build_unset_xref_deprecated_at,
                    None, xid, xref.deprecated_at,
                    xref_mode=True,
                )
            xref_ids.clear()

    def _sync_pair(
        self,
        set_builder: Any,
        unset_builder: Any,
        scope_id: Any,
        element_id: str,
        value: Any,
        *,
        xref_mode: bool = False,
    ) -> None:
        """Emit a SET-or-UNSET pair for a single datetime field.

        Phase 10 helper for :meth:`_drain_soft_delete`. When ``value`` is
        non-None, calls ``set_builder(scope_id, element_id, iso_string)``
        (or ``set_builder(element_id, iso_string)`` for XRef mode).
        When ``value`` is None, calls ``unset_builder(scope_id, element_id)``
        (or ``unset_builder(element_id)`` for XRef mode).
        """
        if value is not None:
            iso = value.isoformat() if hasattr(value, "isoformat") else value
            if xref_mode:
                q, p = set_builder(element_id, iso)
            else:
                q, p = set_builder(scope_id, element_id, iso)
        else:
            if xref_mode:
                q, p = unset_builder(element_id)
            else:
                q, p = unset_builder(scope_id, element_id)
        self._client.run_query(q, p)


__all__ = ["MetagraphRepository"]
