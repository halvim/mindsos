"""Reconstruct a :class:`Metagraph` from FalkorDB (Phase 08 — ADR-0124).

Slim-port of the v3 baseline at
``/Layered Intelligence/mindsos_core/reconstruction/metagraph_loader.py``
(236 LOC) with the following adaptations per Phase 08 locked picks:

* **RPB-6 A** — Strip the legacy ``_migrate_legacy_settings`` migration.
  Phase 07 writes via ``_props_json`` only (ADR-0130); no
  ``:MetagraphSettings`` rows can exist in halvim_mindsos substrate.
* **M1 / Phase 09 carry-forward** — Strip the v3 ``XRefLoader`` sub-
  loader. Phase 09 ships ``XRefLoader`` as an
  :func:`Metagraph.register_after_load_observer` subscriber per RR-10 A;
  :class:`MetagraphLoader` stays orchestration-only (RR-8 A).
* **R4-3 A** — ``ReconstructionError`` umbrella dropped; replace every
  v3 raise with :class:`PersistenceError`. ``WALReplayerMissingError`` /
  ``RoleMismatchError`` are the only new raise paths in Phase 08.
* **PB-6 B** — :meth:`MetagraphLoader.load` ALWAYS calls
  :func:`mindsos_core.persistence.wal.recover` BEFORE its reads. First
  L1 WAL consumer ships via this path.
* **Phase 09 P62** — the Phase 08 silent narrow-catch of
  :class:`WALReplayerMissingError` was removed. Phase 09 ships actual
  L1 replayers (``xref_add`` / ``xref_remove``) registered via
  :func:`mindsos_core.persistence.bootstrap.register_all_l1_replayers`
  on ``FalkorClient.__init__``. An unknown kind in WAL post-Phase-09
  is a real bug; the exception now propagates as
  :class:`PersistenceError`.
* **PB-11 A** — ``schema_name`` plain Cypher property (Phase 07 P100 A)
  decoded into ``mg.schema_name``; MetagraphSchema content is NOT
  auto-attached (L2 territory; tester recipe is
  ``mindsos metagraph attach-schema`` post-load).
* **R4-1 A / R4-8 A** — Locked load sequence:
  ``recover()`` → anchor → contained graphs → MetaEdges →
  MetaHyperEdges → IntergraphEdges → IntergraphHyperEdges →
  fire ``after_load(mg)`` observers (single fire per RPB-9 A;
  per-observer exception isolation per RR-9 A — see
  :func:`mindsos_core._observers._dispatch_after_load`).
* **RR-8 A** — Class is an orchestrator only. No ``_instance_loader``
  / ``_xref_loader`` handles. Sub-loaders subscribe via ``after_load``.
* **RR-2 D** — ``load_metagraph(client, mid, *, batch_size=None,
  identity=None, schema=None)``: ``batch_size=None`` (default) full-
  loads via :func:`load_graph`; ``batch_size=int`` uses
  :func:`iter_load_graph` per contained graph + assemble.
* **R4-11 A** — Class constructor is minimal: ``MetagraphLoader(client)``.
  All other kwargs are per-call (on ``.load`` and ``.refresh``).
* **R4-4 B** — ``schema=None`` kwarg accepted as no-op forward-compat
  parity with Phase 07 :func:`load_graph`.

Provides:

* :class:`MetagraphLoader` — class form (per PB-2 C hybrid).
* :func:`load_metagraph` — module-level convenience function (per
  RR-5 B); thin wrapper of ``MetagraphLoader(client).load(mid, ...)``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..exceptions import (
    PersistenceError,
    RoleMismatchError,
)
from ..models.identity import IdentityRegistry
from ..models.metagraph import Metagraph
from ..persistence.client import Client
from ..persistence.soft_delete import SoftDeleteKind
from ..persistence.wal import recover as _wal_recover
from .graph_loader import iter_load_graph, load_graph, load_graph_with_report
from .load_report import LoadReport, MetagraphLoadReport

_log = logging.getLogger(__name__)


# ADR-0130 — JSON-encoded property bag on the :Metagraph anchor row.
_PROPS_JSON_KEY = "_props_json"


class MetagraphLoader:
    """Load a :class:`Metagraph` with all contained graphs and metagraph-context edges.

    Phase 08 orchestrator (RR-8 A). Owns the locked R4-1 A read
    sequence; sibling-package loaders (InstanceLoader in Phase 08;
    XRefLoader in Phase 09 per RR-10 A) subscribe via
    :meth:`Metagraph.register_after_load_observer` and fire after the
    orchestrator's reads complete.

    Minimal constructor surface (R4-11 A) — ``MetagraphLoader(client)``.
    All per-call kwargs live on :meth:`load` and :meth:`refresh`.
    """

    def __init__(self, client: Client) -> None:
        self._client = client

    # ── public API ─────────────────────────────────────────────────────────

    def find_by_name(self, name: str) -> Optional[str]:
        """Resolve a Metagraph's ``metagraph_id`` from its ``name`` (Phase 26a).

        Phase 26a (R5-PB-4 (a) + R6-PB-1 (a)). Cheap O(1) lookup
        backed by the ``Metagraph(name)`` index added at Phase 26a
        per ADR-0123 §amendment-1.

        Returns ``None`` when no Metagraph with that name exists
        (first-ever bootstrap path in
        :func:`mindsos_server.persistence.bootstrap.bootstrap_kl_from_falkordb`).

        Args:
            name: The Metagraph name to look up (e.g.,
                ``_GLOBAL_METAGRAPH_NAME`` for the canonical Global).

        Returns:
            The matched ``metagraph_id`` string, or ``None`` if no
            Metagraph anchor with that name is present in FalkorDB.

        Raises:
            PersistenceError: If the lookup query itself fails (driver
                error). Missing-row is NOT an error; returns ``None``.
        """
        query = "MATCH (m:Metagraph {name: $name}) RETURN m.id AS metagraph_id LIMIT 1"
        result = self._client.run_query(query, {"name": name})
        first = result.first()
        if first is None:
            return None
        return first["metagraph_id"]

    def load(
        self,
        metagraph_id: str,
        *,
        batch_size: Optional[int] = None,
        identity: Optional[IdentityRegistry] = None,
        schema: Any = None,
        include_deprecated: bool = False,
    ) -> Metagraph:
        """Reconstruct the :class:`Metagraph` with ``metagraph_id`` from FalkorDB.

        **Phase 10 ADR-0133 — soft-delete filter at load time.** When
        ``include_deprecated=False`` (default), MetaEdges and
        MetaHyperEdges whose ``deprecated_at IS NOT NULL`` are filtered
        out at the Cypher level — they are NOT materialized into the
        in-memory :class:`Metagraph`. Consequence (ADR-0133 §Loader
        behavior gotcha): subsequent calls to
        :meth:`Metagraph.iter_metaedges` with ``include_deprecated=True``
        return nothing extra (the deprecated rows were never loaded).
        Audit-gate / repair-tool callers pass ``include_deprecated=True``
        to load the full set.

        Phase 10 PB-6a — :attr:`Metagraph._soft_delete_dirty` (per-Metagraph
        + per-Graph buckets) is cleared post-load so refresh-then-persist
        doesn't re-write loaded rows (P64 mirror — loaded rows are by
        definition already persisted).

        Locked R4-1 A / R4-8 A sequence:

            0. ``recover(client, metagraph_id)`` — first L1 WAL consumer
               (PB-6 B). Phase 09 ships actual replayers via
               :func:`register_all_l1_replayers` on
               ``FalkorClient.__init__``; missing replayer for any
               uncommitted kind raises :class:`WALReplayerMissingError`
               per Phase 09 P62 (the Phase 08 silent narrow-catch was
               removed).
            1. Load the ``:Metagraph`` anchor row (decode ``_props_json``).
            2. Construct the shell ``Metagraph`` with a fresh or shared
               :class:`IdentityRegistry`.
            3. Load contained ``Graph`` rows in id-order; use
               :func:`load_graph` when ``batch_size is None`` (RR-2 D
               default) or :func:`iter_load_graph` per-graph when
               ``batch_size: int``.
            4. Load MetaEdges (cross-graph rel-typed; one query covers
               every type via untyped MATCH + ``r.metagraph_id`` filter).
            5. Load MetaHyperEdges (n-ary; ``:MEMBER_GRAPH`` rels).
            6. Load IntergraphEdges (binary cross-graph node↔node;
               untyped MATCH + ``e.metagraph_id`` filter).
            7. Load IntergraphHyperEdges (n-ary; ``:ANCHOR`` +
               ``:MEMBER`` rels per Phase 08 P61 A fix).
            8. Fire ``after_load(mg)`` observers ONCE per RPB-9 A.

        Args:
            metagraph_id: Cypher ``:Metagraph.id`` to load.
            batch_size: Per RR-2 D. ``None`` (default) — full-load each
                contained Graph via :func:`load_graph`. ``int`` — use
                :func:`iter_load_graph` per contained graph + assemble;
                bounded per-graph memory.
            identity: Optional shared :class:`IdentityRegistry`. When
                ``None``, a fresh registry is created; every loaded
                element registers under it (and so does
                ``metagraph_id``).
            schema: Optional :class:`MetagraphSchema`. Phase 08 accepts
                as no-op kwarg (R4-4 B); L2 may consume in later phases.

        Returns:
            Reconstructed :class:`Metagraph`. Identity-registry is
            populated; ``element_registry`` is populated if the
            sibling-package :func:`mindsos_instances.attach_registry`
            was bound BEFORE the load (per Phase 08 row §Pass criterion).

        Raises:
            PersistenceError: no ``:Metagraph`` row with
                ``id=metagraph_id``; or driver-level WAL recovery
                failure; or any sub-read driver error.
        """
        # Step 0 — WAL recover-on-load (PB-6 B).
        # Phase 09 P62 — the silent narrow-catch of
        # WALReplayerMissingError was removed. Phase 09 ships actual L1
        # replayers (xref_add / xref_remove) on FalkorClient.__init__.
        # An unknown kind here is a real bug; let it propagate.
        _wal_recover(self._client, metagraph_id)

        # Step 1 — anchor row.
        anchor = self._load_metagraph_anchor(metagraph_id)
        props_json = anchor.get(_PROPS_JSON_KEY)
        decoded_props: Dict[str, Any] = {}
        if props_json:
            try:
                decoded_props = json.loads(props_json)
            except (TypeError, ValueError) as exc:
                raise PersistenceError(
                    f"Metagraph {metagraph_id!r} has malformed "
                    f"_props_json: {props_json!r}"
                ) from exc

        # Step 2 — construct shell Metagraph + identity wiring.
        if identity is None:
            identity = IdentityRegistry()
        mg = Metagraph(
            name=anchor["name"],
            identity=identity,
            metagraph_id=metagraph_id,
            properties=decoded_props,
        )
        # ``Metagraph.__init__`` only auto-registers the metagraph_id
        # on the fresh-id path; we supplied an explicit id, so register
        # explicitly. Idempotent on already-registered.
        try:
            mg.identity.register(metagraph_id)
        except Exception:
            # Already-registered fine — happens when ``identity`` arrived
            # pre-populated.
            pass

        # PB-11 A — restore ``schema_name`` plain Cypher property
        # (Phase 07 P100 A). Vocab content NOT auto-attached.
        schema_name = anchor.get("schema_name")
        if schema_name is not None:
            mg.schema_name = schema_name

        # Step 3 — contained graphs.
        # Phase 11 — transient `_active_report`/`_active_policy` set by
        # :meth:`load_with_report` opt-in path. ``None`` on the plain
        # :meth:`load` path (preserves Phase 08 behavior exactly).
        _report = getattr(self, "_active_report", None)
        _policy = getattr(self, "_active_policy", None)
        for gid in self._list_graph_ids(metagraph_id):
            self._attach_graph(
                mg, gid, batch_size=batch_size, schema=schema,
                include_deprecated=include_deprecated,
                report=_report,
                unknown_edge_type_policy=_policy,
            )

        # Step 4 — meta-edges.
        self._load_metaedges(mg, include_deprecated=include_deprecated)

        # Step 5 — meta-hyperedges.
        self._load_metahyperedges(mg, include_deprecated=include_deprecated)

        # Step 6 — intergraph-edges.
        self._load_intergraph_edges(mg)

        # Step 7 — intergraph-hyperedges.
        self._load_intergraph_hyperedges(mg)

        # Step 8 — observer fire (RR-9 A per-observer exception
        # isolation; RPB-9 A single fire after Core + sub-reads).
        # Phase 07 ``MetagraphRepository.persist`` parallel: transiently
        # attach the active client onto ``mg._persist_client`` so
        # observer callbacks (e.g. sibling-package InstanceLoader's
        # subscription) can locate it without a closure over self.
        try:
            mg._persist_client = self._client  # type: ignore[attr-defined]
            from .._observers import _dispatch_after_load
            _dispatch_after_load(mg._after_load_observers, mg)
        finally:
            if hasattr(mg, "_persist_client"):
                try:
                    delattr(mg, "_persist_client")
                except AttributeError:
                    pass

        # Phase 10 PB-6a — clear soft-delete dirty after full load
        # (P64 mirror). Loaded rows are by definition already in DB; the
        # dirty set must be empty post-load.
        _clear_soft_delete_dirty(mg)

        return mg

    def load_with_report(
        self,
        metagraph_id: str,
        *,
        batch_size: Optional[int] = None,
        identity: Optional[IdentityRegistry] = None,
        schema: Any = None,
        include_deprecated: bool = False,
        unknown_edge_type_policy: Optional[str] = None,
    ) -> Tuple[Metagraph, MetagraphLoadReport]:
        """Phase 11 sibling of :meth:`load` returning :class:`MetagraphLoadReport`.

        Same load semantics + sequence as :meth:`load`. Each contained
        :class:`Graph` is loaded via
        :func:`load_graph_with_report` (or :func:`iter_load_graph` with
        a per-:class:`Graph` :class:`LoadReport` for the streamed path)
        and the per-graph report is folded into the
        :class:`MetagraphLoadReport`.

        Per PB-7 lock — only :attr:`Schema.edge_types` /
        :attr:`Schema.hyperedge_types` participate in the policy.
        ``MetagraphSchema`` is **not** consulted; MetaEdge /
        IntergraphEdge type drops are out of scope for Phase 11 and
        carry forward to Phase 12+.

        Args + Raises: see :meth:`load`, plus
        ``unknown_edge_type_policy`` (``"warn"`` default;
        ``MINDSOS_UNKNOWN_EDGE_POLICY`` env override).

        Returns:
            ``(mg, report)``. The ``mg`` is identical to what
            :meth:`load` would return (modulo policy-filtered rows).
            The ``report`` has one :class:`LoadReport` per contained
            :class:`Graph` (including clean ones) plus aggregate totals.
        """
        report = MetagraphLoadReport(metagraph_id=metagraph_id)
        # Reuse the existing :meth:`load` sequence via a closure-attached
        # report — simpler than copy-pasting the 8-step body. The only
        # mutation is in :meth:`_attach_graph` which checks ``report``.
        # We do this by setting an instance-level transient field, then
        # calling :meth:`load`.
        self._active_report = report  # type: ignore[attr-defined]
        self._active_policy = unknown_edge_type_policy  # type: ignore[attr-defined]
        try:
            mg = self.load(
                metagraph_id,
                batch_size=batch_size,
                identity=identity,
                schema=schema,
                include_deprecated=include_deprecated,
            )
        finally:
            self._active_report = None  # type: ignore[attr-defined]
            self._active_policy = None  # type: ignore[attr-defined]
        return mg, report

    def refresh(
        self,
        mg: Metagraph,
        role: str,
        *,
        schema: Any = None,
        include_deprecated: bool = False,
    ) -> None:
        """Reload role-graph(s) of ``role`` in ``mg`` in place (ADR-0124).

        Drops the existing graphs with the given role from ``mg`` via
        the proper :meth:`Metagraph.remove_graph` API (RPB-2 A) — fires
        Phase 06 remove-observer cascade for dependent instances —
        then loads the current persisted state from FalkorDB and fires
        ``after_load(mg)`` for sibling-side rehydration.

        Identity preservation (R4-7 A+C): ``id(mg)`` AND
        ``id(mg.identity)`` survive; external references (e.g. cached
        ``weakref.proxy(mg.identity)``) continue to resolve.

        Edge cases (R4-2 D):

        * **Empty role** — no graphs in ``mg`` with ``role=$role``:
          log WARNING + no-op return.
        * **Role mismatch** — for some ``gid``, the in-memory
          ``mg.graphs[gid].role`` differs from the persisted
          ``:Graph.role`` for the same id: raise
          :class:`RoleMismatchError` with both roles surfaced.
          Indicates substrate corruption (external write race or
          manual DB edit); not user-recoverable at runtime.

        Args:
            mg: target :class:`Metagraph` to refresh in place.
            role: role label to refresh (e.g. ``"lexicon"``).
            schema: optional schema; no-op at L1 (R4-4 B parity).

        Raises:
            RoleMismatchError: substrate role drift for a graph that
                exists in both memory and DB.
            PersistenceError: driver-level read failure.
        """
        # R4-2 D — role-mismatch precheck against DB role for EVERY
        # graph in mg with this role. Loud failure before any mutation.
        affected = [g for g in mg.graphs.values() if g.role == role]
        if not affected:
            # R4-2 D empty-role — log + no-op return. Programmatic
            # callers that need "nothing happened" detection check
            # ``mg.graphs_by_role(role)`` post-refresh.
            _log.warning(
                "MetagraphLoader.refresh: no graphs with role=%r in "
                "metagraph %r; no-op return",
                role, mg.metagraph_id,
            )
            return

        # Check DB role for each affected graph BEFORE drop. A drift
        # raises before any local mutation so identity preservation is
        # guaranteed (R4-7 A) even on the error path.
        db_roles = self._fetch_graph_roles_for_metagraph(
            mg.metagraph_id, [g.graph_id for g in affected]
        )
        for g in affected:
            db_role = db_roles.get(g.graph_id)
            if db_role != role:
                raise RoleMismatchError(
                    graph_id=g.graph_id,
                    in_memory_role=g.role,
                    db_role=db_role,
                )

        # RPB-2 A — drop via proper public API. Phase 06's
        # remove-observer cascade fires for dependent SubGraphInstances
        # / GraphInstances / ElementInstances. Identity unregistration
        # happens inside remove_graph (per its implementation).
        for g in list(affected):
            mg.remove_graph(g.graph_id)

        # Reload role-graphs from DB; reuse ``mg.identity`` (shared
        # registry; identity preservation per R4-7 A).
        new_gids = self._list_graph_ids_for_role(mg.metagraph_id, role)
        for gid in new_gids:
            self._attach_graph(
                mg, gid, batch_size=None, schema=schema,
                include_deprecated=include_deprecated,
            )

        # Fire ``after_load(mg)`` so sibling-side reconstruction (e.g.
        # InstanceLoader) rehydrates against the new role-graph state.
        # Per-observer exception isolation per RR-9 A.
        try:
            mg._persist_client = self._client  # type: ignore[attr-defined]
            from .._observers import _dispatch_after_load
            _dispatch_after_load(mg._after_load_observers, mg)
        finally:
            if hasattr(mg, "_persist_client"):
                try:
                    delattr(mg, "_persist_client")
                except AttributeError:
                    pass

        # Phase 10 PB-6a — clear soft-delete dirty after refresh.
        _clear_soft_delete_dirty(mg)

    # ── private read helpers ────────────────────────────────────────────

    def _attach_graph(
        self,
        mg: Metagraph,
        graph_id: str,
        *,
        batch_size: Optional[int],
        schema: Any,
        include_deprecated: bool = False,
        report: Optional["MetagraphLoadReport"] = None,
        unknown_edge_type_policy: Optional[str] = None,
    ) -> None:
        """Load one contained Graph (full or streamed) + attach to ``mg``.

        Phase 11 — when ``report`` is provided (the
        :meth:`load_with_report` path), routes through
        :func:`load_graph_with_report` per-graph and folds the
        per-:class:`Graph` :class:`LoadReport` into the
        :class:`MetagraphLoadReport`. ``report=None`` preserves the
        Phase 08 behavior exactly (PB-12 B + PB-13 A — additive
        sibling discipline; existing :meth:`load` path unaffected).
        """
        per_graph_report: Optional[LoadReport] = None
        if batch_size is None:
            if report is not None:
                g, per_graph_report = load_graph_with_report(
                    self._client,
                    graph_id,
                    identity=mg.identity,
                    schema=schema,
                    include_deprecated=include_deprecated,
                    unknown_edge_type_policy=unknown_edge_type_policy,
                )
            else:
                g = load_graph(
                    self._client,
                    graph_id,
                    identity=mg.identity,
                    schema=schema,
                    include_deprecated=include_deprecated,
                )
        else:
            # Drain the iterator; the assembled Graph is the final
            # yield (which trails edges + hyperedges per RPB-1 A).
            g = None  # type: ignore[assignment]
            if report is not None:
                per_graph_report = LoadReport(graph_id=graph_id)
            for partial in iter_load_graph(
                self._client,
                graph_id,
                identity=mg.identity,
                schema=schema,
                batch_size=batch_size,
                include_deprecated=include_deprecated,
                report=per_graph_report,
                unknown_edge_type_policy=unknown_edge_type_policy,
            ):
                g = partial
            if g is None:
                raise PersistenceError(
                    f"_attach_graph: iter_load_graph yielded no "
                    f"batches for graph_id={graph_id!r}"
                )
        mg.add_graph(g)
        if report is not None and per_graph_report is not None:
            report.attach(per_graph_report)

    def _load_metagraph_anchor(self, metagraph_id: str) -> Dict[str, Any]:
        """Read the :Metagraph anchor row + property bag + schema_name."""
        q = (
            "MATCH (m:Metagraph {id: $mid}) "
            f"RETURN m.name AS name, m.{_PROPS_JSON_KEY} AS {_PROPS_JSON_KEY}, "
            "       m.schema_name AS schema_name, m._version AS version"
        )
        res = self._client.run_query(q, {"mid": metagraph_id})
        if not res.rows:
            raise PersistenceError(
                f"No :Metagraph row with id {metagraph_id!r} in FalkorDB"
            )
        return res.rows[0]

    def _list_graph_ids(self, metagraph_id: str) -> List[str]:
        """Return contained graph ids in stable id-order."""
        q = (
            "MATCH (g:Graph)-[:IN_METAGRAPH]->(m:Metagraph {id: $mid}) "
            "RETURN g.id AS id "
            "ORDER BY g.id"
        )
        res = self._client.run_query(q, {"mid": metagraph_id})
        return [row["id"] for row in res.rows]

    def _list_graph_ids_for_role(
        self, metagraph_id: str, role: str
    ) -> List[str]:
        """Return contained graph ids whose role matches ``role`` in DB."""
        q = (
            "MATCH (g:Graph {role: $role})-[:IN_METAGRAPH]->"
            "(m:Metagraph {id: $mid}) "
            "RETURN g.id AS id "
            "ORDER BY g.id"
        )
        res = self._client.run_query(
            q, {"mid": metagraph_id, "role": role}
        )
        return [row["id"] for row in res.rows]

    def _fetch_graph_roles_for_metagraph(
        self, metagraph_id: str, graph_ids: List[str]
    ) -> Dict[str, Optional[str]]:
        """Return ``{graph_id: db_role}`` for the supplied ids.

        Missing rows omit the id; caller treats absent as ``None`` for
        the role-mismatch comparison.
        """
        if not graph_ids:
            return {}
        q = (
            "MATCH (g:Graph)-[:IN_METAGRAPH]->(m:Metagraph {id: $mid}) "
            "WHERE g.id IN $gids "
            "RETURN g.id AS id, g.role AS role"
        )
        res = self._client.run_query(
            q, {"mid": metagraph_id, "gids": graph_ids}
        )
        return {row["id"]: row.get("role") for row in res.rows}

    def _load_metaedges(
        self, mg: Metagraph, *, include_deprecated: bool = False
    ) -> None:
        """Load MetaEdges (graph→graph cross-graph rels) over all types.

        The persist side emits each MetaEdge with a Cypher rel-type
        equal to its ``type_name`` (per
        :func:`build_unwind_create_metaedges`); the read MATCHes
        untyped + filters via the ``r.metagraph_id`` property.

        Phase 10 ADR-0133 — when ``include_deprecated=False`` (default),
        the WHERE clause adds ``r.deprecated_at IS NULL``. Soft-delete
        fields ``deprecated_at`` / ``disputed_at`` are round-tripped from
        the row's properties bag onto the dataclass post-construction.
        """
        # Phase 10 — conditional WHERE clause for deprecated_at filter.
        where_extra = "" if include_deprecated else " AND r.deprecated_at IS NULL"
        q = (
            "MATCH (s:Graph)-[r]->(t:Graph) "
            f"WHERE r.metagraph_id = $mid AND r.id IS NOT NULL{where_extra} "
            "RETURN r.id AS id, r.type_name AS type_name, r.label AS label, "
            "       r._version AS version, s.id AS sid, t.id AS tid, "
            "       properties(r) AS props"
        )
        res = self._client.run_query(q, {"mid": mg.metagraph_id})
        for row in res.rows:
            if row["sid"] not in mg.graphs or row["tid"] not in mg.graphs:
                _log.warning(
                    "MetaEdge %r references missing contained graph "
                    "(src=%r tgt=%r); skipping",
                    row["id"], row["sid"], row["tid"],
                )
                continue
            if row["id"] in mg.metaedges:
                continue
            # Phase 10 — extract soft-delete fields BEFORE strip.
            raw_props = row.get("props") or {}
            dep_at = _parse_iso(raw_props.get("deprecated_at"))
            dis_at = _parse_iso(raw_props.get("disputed_at"))
            props = _strip_metaedge_keys(raw_props)
            me = mg.add_metaedge(
                source_graph_id=row["sid"],
                target_graph_id=row["tid"],
                type_name=row["type_name"],
                label=row.get("label"),
                properties=props,
                edge_id=row["id"],
                _validate=False,
            )
            if row.get("version") is not None:
                try:
                    me._version = int(row["version"])
                except (TypeError, ValueError):
                    pass
            # Phase 10 — restore soft-delete fields onto the dataclass.
            me.deprecated_at = dep_at
            me.disputed_at = dis_at

    def _load_metahyperedges(
        self, mg: Metagraph, *, include_deprecated: bool = False
    ) -> None:
        """Load MetaHyperEdges (:MetaHyperEdge node + :MEMBER_GRAPH rels).

        Phase 10 ADR-0133 — when ``include_deprecated=False`` (default),
        WHERE clause adds ``h.deprecated_at IS NULL``. Soft-delete fields
        round-tripped onto the dataclass per :meth:`_load_metaedges`
        pattern.
        """
        # Phase 10 — conditional WHERE clause for deprecated_at filter.
        where_extra = "" if include_deprecated else " WHERE h.deprecated_at IS NULL"
        q = (
            "MATCH (h:MetaHyperEdge {metagraph_id: $mid}) "
            f"{where_extra} "
            "OPTIONAL MATCH (h)-[:MEMBER_GRAPH]->(g:Graph) "
            "WITH h, collect(g.id) AS gids "
            "RETURN h.id AS id, h.type_name AS type_name, h.label AS label, "
            "       h._version AS version, properties(h) AS props, gids"
        )
        res = self._client.run_query(q, {"mid": mg.metagraph_id})
        for row in res.rows:
            if row["id"] in mg.metahyperedges:
                continue
            gids = [gid for gid in (row.get("gids") or []) if gid]
            valid_gids = [gid for gid in gids if gid in mg.graphs]
            if len(valid_gids) < 2:
                _log.warning(
                    "MetaHyperEdge %r has <2 valid member graphs "
                    "(have=%r); skipping",
                    row["id"], valid_gids,
                )
                continue
            # Phase 10 — extract soft-delete fields BEFORE strip.
            raw_props = row.get("props") or {}
            dep_at = _parse_iso(raw_props.get("deprecated_at"))
            dis_at = _parse_iso(raw_props.get("disputed_at"))
            props = _strip_metahyperedge_keys(raw_props)
            type_name = row.get("type_name") or "UNSPECIFIED"
            mhe = mg.add_metahyperedge(
                graph_ids=valid_gids,
                type_name=type_name,
                label=row.get("label"),
                properties=props,
                edge_id=row["id"],
                _validate=False,
            )
            if row.get("version") is not None:
                try:
                    mhe._version = int(row["version"])
                except (TypeError, ValueError):
                    pass
            # Phase 10 — restore soft-delete fields.
            mhe.deprecated_at = dep_at
            mhe.disputed_at = dis_at

    def _load_intergraph_edges(self, mg: Metagraph) -> None:
        """Load IntergraphEdges (binary node↔node across graphs).

        The persist side emits each IntergraphEdge with a Cypher rel-
        type equal to its ``type_name`` between two ``:Node`` endpoints
        in different ``graph_id``s. The read MATCHes untyped + filters
        via ``e.metagraph_id`` + cross-graph endpoint guard.
        """
        q = (
            "MATCH (s:Node)-[e]->(t:Node) "
            "WHERE e.metagraph_id = $mid AND e.id IS NOT NULL "
            "  AND s.graph_id <> t.graph_id "
            "RETURN e.id AS id, e.type_name AS type_name, e.label AS label, "
            "       e.compositional AS compositional, e._version AS version, "
            "       s.id AS source_node_id, s.graph_id AS source_graph_id, "
            "       t.id AS target_node_id, t.graph_id AS target_graph_id, "
            "       properties(e) AS props"
        )
        res = self._client.run_query(q, {"mid": mg.metagraph_id})
        for row in res.rows:
            if row["id"] in mg.intergraph_edges:
                continue
            # Defensive — endpoints must be in loaded contained graphs.
            sgid = row["source_graph_id"]
            tgid = row["target_graph_id"]
            if sgid not in mg.graphs or tgid not in mg.graphs:
                _log.warning(
                    "IntergraphEdge %r references missing contained "
                    "graph (src_gid=%r tgt_gid=%r); skipping",
                    row["id"], sgid, tgid,
                )
                continue
            sg = mg.graphs[sgid]
            tg = mg.graphs[tgid]
            snid = row["source_node_id"]
            tnid = row["target_node_id"]
            if snid not in sg.nodes or tnid not in tg.nodes:
                _log.warning(
                    "IntergraphEdge %r references missing node "
                    "(src=%r in %r; tgt=%r in %r); skipping",
                    row["id"], snid, sgid, tnid, tgid,
                )
                continue
            props = _strip_intergraph_edge_keys(row.get("props") or {})
            compositional = bool(row.get("compositional") or False)
            ie = mg.add_intergraph_edge(
                source_graph_id=sgid,
                source_node_id=snid,
                target_graph_id=tgid,
                target_node_id=tnid,
                type_name=row["type_name"],
                compositional=compositional,
                label=row.get("label"),
                properties=props,
                edge_id=row["id"],
            )
            if row.get("version") is not None:
                try:
                    ie._version = int(row["version"])
                except (TypeError, ValueError):
                    pass

    def _load_intergraph_hyperedges(self, mg: Metagraph) -> None:
        """Load IntergraphHyperEdges (n-ary; :ANCHOR + :MEMBER rels).

        Phase 08 P61 A fix: Phase 07's persist only wrote :MEMBER rels;
        Phase 08's builder additively writes :ANCHOR rels alongside.
        This loader reads BOTH and reconstructs ``anchors`` + ``members``.
        Old data persisted before the P61 A fix has empty anchors —
        such rows surface in this loader's WARNING log + are SKIPPED
        (the dataclass invariant ``n_anchors >= 1`` would otherwise
        raise; documented as a Phase 07 → Phase 08 migration gap).
        """
        q = (
            "MATCH (ih:IntergraphHyperEdge {metagraph_id: $mid}) "
            "OPTIONAL MATCH (ih)-[:ANCHOR]->(an:Node) "
            "WITH ih, collect(DISTINCT {node_id: an.id, graph_id: an.graph_id}) AS anchors "
            "OPTIONAL MATCH (ih)-[:MEMBER]->(mn:Node) "
            "WITH ih, anchors, collect(DISTINCT {node_id: mn.id, graph_id: mn.graph_id}) AS members "
            "RETURN ih.id AS id, ih.type_name AS type_name, ih.label AS label, "
            "       ih.compositional AS compositional, ih.ordered AS ordered, "
            "       ih._version AS version, properties(ih) AS props, "
            "       anchors, members"
        )
        res = self._client.run_query(q, {"mid": mg.metagraph_id})
        for row in res.rows:
            if row["id"] in mg.intergraph_hyperedges:
                continue
            anchors_raw = [
                (a["graph_id"], a["node_id"])
                for a in (row.get("anchors") or [])
                if a and a.get("node_id") and a.get("graph_id")
            ]
            members_raw = [
                (m["graph_id"], m["node_id"])
                for m in (row.get("members") or [])
                if m and m.get("node_id") and m.get("graph_id")
            ]
            # Filter to endpoints whose graphs + nodes loaded.
            def _present(pair):
                gid, nid = pair
                return gid in mg.graphs and nid in mg.graphs[gid].nodes
            anchors = [p for p in anchors_raw if _present(p)]
            members = [p for p in members_raw if _present(p)]
            if not anchors:
                _log.warning(
                    "IntergraphHyperEdge %r has no recoverable anchors "
                    "(Phase 07 wrote only :MEMBER rels; Phase 08 P61 A "
                    "fix only applies to writes after this phase); "
                    "skipping. Persist the metagraph again under Phase "
                    "08 to repopulate :ANCHOR rels.",
                    row["id"],
                )
                continue
            if not members:
                _log.warning(
                    "IntergraphHyperEdge %r has no recoverable members; "
                    "skipping",
                    row["id"],
                )
                continue
            if len(anchors) == 1 and len(members) == 1:
                _log.warning(
                    "IntergraphHyperEdge %r recovered as 1-1 (use "
                    "IntergraphEdge for binary); skipping",
                    row["id"],
                )
                continue
            props = _strip_intergraph_hyperedge_keys(row.get("props") or {})
            compositional = bool(row.get("compositional") or False)
            ihe = mg.add_intergraph_hyperedge(
                anchors=anchors,
                members=members,
                type_name=row["type_name"],
                compositional=compositional,
                label=row.get("label"),
                properties=props,
                intergraph_hyperedge_id=row["id"],
            )
            if row.get("version") is not None:
                try:
                    ihe._version = int(row["version"])
                except (TypeError, ValueError):
                    pass


# ── module convenience function (RR-5 B) ────────────────────────────────────


def load_metagraph(
    client: Client,
    metagraph_id: str,
    *,
    batch_size: Optional[int] = None,
    identity: Optional[IdentityRegistry] = None,
    schema: Any = None,
    include_deprecated: bool = False,
) -> Metagraph:
    """Reconstruct a :class:`Metagraph` from FalkorDB.

    Module-level convenience function (RR-5 B). Thin wrapper of
    :meth:`MetagraphLoader.load`. Symmetric with Phase 07
    :func:`load_graph`'s function-style surface.

    Phase 10 — accepts ``include_deprecated`` per ADR-0133 §Loader
    behavior.

    Args + Returns: see :meth:`MetagraphLoader.load`.
    """
    return MetagraphLoader(client).load(
        metagraph_id,
        batch_size=batch_size,
        identity=identity,
        schema=schema,
        include_deprecated=include_deprecated,
    )


def load_metagraph_with_report(
    client: Client,
    metagraph_id: str,
    *,
    batch_size: Optional[int] = None,
    identity: Optional[IdentityRegistry] = None,
    schema: Any = None,
    include_deprecated: bool = False,
    unknown_edge_type_policy: Optional[str] = None,
) -> Tuple[Metagraph, MetagraphLoadReport]:
    """Phase 11 sibling of :func:`load_metagraph` returning aggregate report.

    Thin wrapper of :meth:`MetagraphLoader.load_with_report`. Symmetric
    with :func:`load_graph_with_report` at the Graph layer.
    """
    return MetagraphLoader(client).load_with_report(
        metagraph_id,
        batch_size=batch_size,
        identity=identity,
        schema=schema,
        include_deprecated=include_deprecated,
        unknown_edge_type_policy=unknown_edge_type_policy,
    )


# ── private helpers ────────────────────────────────────────────────────────


_METAEDGE_RESERVED = frozenset({
    "id", "type_name", "label", "metagraph_id",
    "source_graph_id", "target_graph_id", "_version",
    # Phase 10 — ADR-0133 soft-delete fields are typed dataclass attrs,
    # not user-property bag keys.
    "deprecated_at", "disputed_at",
})
_METAHYPEREDGE_RESERVED = frozenset({
    "id", "type_name", "label", "metagraph_id", "_version",
    # Phase 10 — ADR-0133 soft-delete fields.
    "deprecated_at", "disputed_at",
})
_INTERGRAPH_EDGE_RESERVED = frozenset({
    "id", "type_name", "label", "metagraph_id",
    "source_node_id", "source_graph_id",
    "target_node_id", "target_graph_id",
    "compositional", "_version",
})
_INTERGRAPH_HYPEREDGE_RESERVED = frozenset({
    "id", "type_name", "label", "metagraph_id",
    "compositional", "ordered", "_version",
})


def _parse_iso(value: Any) -> Optional[datetime]:
    """Parse an ISO-8601 datetime string into a ``datetime`` or pass-through.

    Phase 10 ADR-0133 — soft-delete fields persist as ISO strings (RR-8).
    Loaders read via ``properties(row)`` (a Python dict from the driver)
    and need to recover ``datetime`` instances onto the dataclass.

    * ``None`` → ``None``.
    * ``datetime`` → return as-is (driver path that already parses).
    * ``str`` → ``datetime.fromisoformat(...)``; malformed → ``None``
      (defensive — emit nothing rather than poison the dataclass).
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


def _clear_soft_delete_dirty(mg: Metagraph) -> None:
    """Clear soft-delete dirty buckets after load/refresh (Phase 10 PB-6a).

    Mirrors Phase 09 P64 (XRef dirty post-load clear). Loaded rows are
    by definition already persisted in FalkorDB; the dirty set must be
    empty so a subsequent :meth:`MetagraphRepository.persist` does not
    re-emit them.

    Clears:

    * ``mg._soft_delete_dirty[<SoftDeleteKind>]`` for all 5 metagraph-side
      kinds (METAEDGE / METAHYPEREDGE / XREF + the EDGE / HYPEREDGE
      buckets that exist for symmetry per P86 mirror).
    * ``g._soft_delete_dirty[<SoftDeleteKind>]`` for each contained
      ``Graph`` — Graph-side EDGE + HYPEREDGE buckets per P86.
    """
    for kind in mg._soft_delete_dirty:
        mg._soft_delete_dirty[kind].clear()
    for g in mg.graphs.values():
        for kind in g._soft_delete_dirty:
            g._soft_delete_dirty[kind].clear()


def _strip_metaedge_keys(props: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in props.items() if k not in _METAEDGE_RESERVED}


def _strip_metahyperedge_keys(props: Dict[str, Any]) -> Dict[str, Any]:
    return {
        k: v
        for k, v in props.items()
        if k not in _METAHYPEREDGE_RESERVED
    }


def _strip_intergraph_edge_keys(props: Dict[str, Any]) -> Dict[str, Any]:
    return {
        k: v for k, v in props.items() if k not in _INTERGRAPH_EDGE_RESERVED
    }


def _strip_intergraph_hyperedge_keys(props: Dict[str, Any]) -> Dict[str, Any]:
    return {
        k: v
        for k, v in props.items()
        if k not in _INTERGRAPH_HYPEREDGE_RESERVED
    }


__all__ = ["MetagraphLoader", "load_metagraph"]
