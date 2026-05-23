"""In-memory :class:`Metagraph` snapshot/restore helper (Phase 10).

.. warning::

   **Scope narrowed by ADR-0129.** This helper is intended for
   ``mindsos_server`` release-ship rollback only — specifically, to
   protect the canonical-Global FalkorDB write inside
   ``release_update`` (per ADR-0118). Knowledge Layer's ordinary
   multi-statement writes should use the WAL graph (ADR-0122) instead;
   the WAL pattern is substrate-friendly and survives process crashes
   where this in-memory snapshot doesn't.

   Callers outside ``mindsos_server`` should plan to migrate. The class
   itself stays in Core because the deep-copy / mutate-in-place
   primitive is generic; the *use* is narrowed. CI lint rule (``grep
   MetagraphSnapshot.of outside mindsos_server/``) rescheduled to
   Phase 24 alongside ``release_update`` per ADR-0129 §amendment-1
   (the original Phase 10 design Q "Phase 18+" deferral was silently
   missed across Phases 18-22; Phase 23 retirement absorbed the
   reschedule). Runtime DeprecationWarning was retired in the same
   amendment as vestigial (KL never adopted snapshot in halvim).

Used by the Server Layer to roll an in-memory Metagraph back to a
pre-release-ship state when a FalkorDB batch write fails mid-commit.
A snapshot captures every mutable attribute of the Metagraph (and of
its contained :class:`Graph` objects, plus :class:`XRef` rows per
ADR-0128 + intergraph primitives per ADR-0148 + Phase 10 dirty sets)
via deep copy; :meth:`MetagraphSnapshot.restore_into` mutates the
original Metagraph **in place** — it never replaces the object.

The in-place contract matters because the Knowledge Layer installs
each Local Metagraph by reference (``installed_locals[user_id] = mg``);
replacing the Metagraph object would leave KL pointing at a dead
instance. Where possible, the helper also preserves the identity of
contained :class:`Graph` objects (external layers may cache those too)
by mutating their ``nodes`` / ``edges`` / ``hyperedges`` dicts in place
rather than swapping new Graph instances in.

Snapshots are in-process, session-scoped artefacts only. They are
**not** serialisable to disk and intentionally so: serialising would
couple Core to a durable rollback format, which is out of scope
(ADR-0028 retained).

**Phase 10 port boundary (PB-1):**

Slim-port of project-root ``mindsos_core/metagraph_snapshot.py`` (v3
baseline; 271 LoC). 4 strips + 2 additions + 1 allow-list correction:

* Strip ``_PIGGYBACK_ATTRS`` tuple + ``_piggyback`` dataclass field +
  the two piggyback capture/restore loops + the ``_kl_active_graph_ids``
  skip-clause (PK1 — closed by ADR-0130 Phase 09 Metagraph-side
  acceptance + Phase 10 P85 Graph-side backfill).
* Add ``_xrefs_dirty`` capture/restore (RB1) — pre-existing dirty
  state survives the snapshot/restore cycle.
* Add ``_soft_delete_dirty`` capture/restore (RPB-11) — mirror of
  RB1 for Phase 10's setter dirty-tracking. Keys are
  :class:`SoftDeleteKind` (P72 typo-proof shape).
* **P84 allow-list correction** (Step 6 in-flight) — M3 lock enumerated
  ``_element_instances`` + ``_composite_instances`` (v3-baseline
  attribute names) but halvim per ADR-0132 moved instancing to
  ``mindsos_instances`` package; those attributes are NOT on halvim's
  ``Metagraph``. Drop. ADD ``_intergraph_edges`` (Phase 05b),
  ``_intergraph_hyperedges`` (Phase 05c), ``_schema_name`` + ``_schema``
  (Phase 05b attach state). ADR-0027 §Revisions amendment-1 documents
  the corrected covered-fields set.

**Phase 10 V3 lock — restore semantics:**

Per-attribute deep-copy + identity-preserving restore. The helper
explicitly does NOT do ``copy.deepcopy(mg)`` (would orphan KL's
``installed_locals`` reference). Instead, every mutable dict/set is
cleared and re-populated; the ``IdentityRegistry`` is cleared in place
via :meth:`IdentityRegistry.clear` (Phase 10 RF — docstring amend at
identity.py).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set, Tuple

from .models.graph import Graph
from .models.intergraph_edge import IntergraphEdge
from .models.intergraph_hyperedge import IntergraphHyperEdge
from .models.metagraph import MetaEdge, Metagraph, MetaHyperEdge
from .models.xref import XRef
from .persistence.soft_delete import SoftDeleteKind


@dataclass
class _GraphSnap:
    """Frozen attribute-level snapshot of a single contained :class:`Graph`.

    Per V3 design (Round-3 lock): snapshot at the attribute level (not
    the whole ``Graph`` object) so :meth:`MetagraphSnapshot.restore_into`
    can mutate the live ``Graph`` in place — any external reference to
    a survived ``Graph`` stays valid.

    Phase 10 P85 backfill — ``properties`` field captures the ADR-0130
    Graph-side property bag added in this same row.

    Phase 10 P86 backfill — ``soft_delete_dirty`` field captures the
    Graph-side dirty buckets (EDGE + HYPEREDGE) introduced when 8 Graph
    setters landed at Step 7. RPB-11 extended to Graph scope.
    """

    graph_id: str
    name: str
    role: Optional[str]
    schema: Any  # Schema treated as immutable; share by reference.
    nodes: Dict[str, Any]
    edges: Dict[str, Any]
    hyperedges: Dict[str, Any]
    # ADR-0130 — graph-level property bag (Phase 10 P85 backfill).
    properties: Dict[str, Any] = field(default_factory=dict)
    # Phase 10 P86 — Graph-side soft-delete dirty (EDGE + HYPEREDGE).
    # Keyed by SoftDeleteKind enum (P72 typo-proof).
    soft_delete_dirty: Dict[SoftDeleteKind, Set[str]] = field(default_factory=dict)


@dataclass
class MetagraphSnapshot:
    """Deep-copied snapshot of a :class:`Metagraph`'s mutable in-memory state.

    Opaque to callers. The only supported operations are the classmethod
    :meth:`of` (construct a snapshot) and the instance method
    :meth:`restore_into` (restore the snapshot into a Metagraph).

    Phase 10 M3 + P84 corrected allow-list (12 covered attributes;
    ``_persist_client`` and per-process observer lists deliberately
    EXCLUDED — see module docstring §Phase 10 port boundary).

    .. note::

       Per ADR-0129, this helper's caller-side use is **narrowed to
       release-ship rollback only** in v5+. Knowledge Layer's ordinary
       multi-statement writes will switch to the WAL graph (ADR-0122,
       deferred to Phase 18+ follow-up PR). Until then the snapshot is
       generally available; callers outside ``mindsos_server`` should
       plan migration off it.
    """

    _metagraph_id: str = ""
    _metagraph_props: Dict[str, Any] = field(default_factory=dict, repr=False)
    _graphs: Dict[str, _GraphSnap] = field(default_factory=dict, repr=False)
    _metaedges: Dict[str, MetaEdge] = field(default_factory=dict, repr=False)
    _metahyperedges: Dict[str, MetaHyperEdge] = field(default_factory=dict, repr=False)
    # P84 additions — Phase 05b/05c intergraph primitives.
    _intergraph_edges: Dict[str, IntergraphEdge] = field(default_factory=dict, repr=False)
    _intergraph_hyperedges: Dict[str, IntergraphHyperEdge] = field(
        default_factory=dict, repr=False
    )
    # P84 additions — Phase 05b schema attach state.
    _schema_name: Optional[str] = field(default=None, repr=False)
    _schema: Any = field(default=None, repr=False)
    # ADR-0128 — XRef snapshot (full row + Phase 09 dirty set).
    _xrefs: Dict[str, XRef] = field(default_factory=dict, repr=False)
    # RB1 — Phase 09 _xrefs_dirty survives the snapshot/restore cycle.
    _xrefs_dirty: Set[str] = field(default_factory=set, repr=False)
    # RPB-11 — Phase 10 _soft_delete_dirty survives the cycle. Keyed
    # by SoftDeleteKind enum (P72 typo-proof shape).
    _soft_delete_dirty: Dict[SoftDeleteKind, Set[str]] = field(
        default_factory=dict, repr=False
    )
    _identity_ids: Set[str] = field(default_factory=set, repr=False)

    # ── construction ─────────────────────────────────────────────────────

    @classmethod
    def of(cls, mg: Metagraph) -> "MetagraphSnapshot":
        """Return a deep-copied snapshot of ``mg``'s mutable state.

        Captures the 12 covered attributes per M3 + P84 corrected
        allow-list. Per-graph data is captured at the attribute level
        (via ``_GraphSnap``) so the live Graph object's identity is
        preserved on restore.
        """
        snap = cls(_metagraph_id=mg.metagraph_id)

        # ADR-0130 — capture metagraph-level property bag (Phase 09
        # Metagraph-side acceptance carry).
        snap._metagraph_props = copy.deepcopy(mg.properties)

        # Per-graph: attribute-level deep-copy. Includes Phase 10 P85
        # graph-level property bag + Phase 10 P86 graph-side dirty.
        for gid, g in mg.graphs.items():
            snap._graphs[gid] = _GraphSnap(
                graph_id=g.graph_id,
                name=g.name,
                role=g.role,
                schema=g.schema,  # Schema treated as immutable; share ref.
                nodes=copy.deepcopy(g.nodes),
                edges=copy.deepcopy(g.edges),
                hyperedges=copy.deepcopy(g.hyperedges),
                properties=copy.deepcopy(g.properties),
                # P86 — capture Graph-side dirty (EDGE + HYPEREDGE buckets).
                soft_delete_dirty={
                    kind: set(ids)
                    for kind, ids in g._soft_delete_dirty.items()
                },
            )

        snap._metaedges = copy.deepcopy(mg.metaedges)
        snap._metahyperedges = copy.deepcopy(mg.metahyperedges)
        # P84 — Phase 05b/05c intergraph primitives.
        snap._intergraph_edges = copy.deepcopy(mg.intergraph_edges)
        snap._intergraph_hyperedges = copy.deepcopy(mg.intergraph_hyperedges)
        # P84 — Phase 05b schema attach state. ``schema_name`` is a
        # string reference; ``schema`` is the cached MetagraphSchema
        # instance (treated as immutable; share by reference, mirroring
        # ``Graph.schema``'s pattern).
        snap._schema_name = mg.schema_name
        snap._schema = mg.schema

        # ADR-0128 — capture XRefs + Phase 09 RB1 dirty set.
        snap._xrefs = copy.deepcopy(mg.xrefs)
        snap._xrefs_dirty = set(mg._xrefs_dirty)
        # Phase 10 RPB-11 — capture soft-delete dirty set. Deep-copy
        # the per-kind set values (sets of element ids); enum keys are
        # immutable.
        snap._soft_delete_dirty = {
            kind: set(ids) for kind, ids in mg._soft_delete_dirty.items()
        }
        # IdentityRegistry.ids is a @property (defensive copy of _ids).
        snap._identity_ids = mg.identity.ids

        return snap

    # ── restore ──────────────────────────────────────────────────────────

    def restore_into(self, mg: Metagraph) -> None:
        """Mutate ``mg`` back to the snapshotted state.

        CRITICAL: does not replace the Metagraph object or its shared
        :class:`IdentityRegistry`. KL's ``installed_locals`` dict holds
        references to the original instance; replacing the object would
        leave KL pointing at a dead metagraph. Mutate, don't replace.

        Phase 10 V3 lock — explicit per-attribute restore (not
        ``copy.deepcopy(mg)``). 12 covered attributes per M3 + P84.
        """
        if mg.metagraph_id != self._metagraph_id:
            raise ValueError(
                f"Snapshot metagraph_id {self._metagraph_id!r} does not match "
                f"target metagraph_id {mg.metagraph_id!r}"
            )

        # ADR-0130 — restore metagraph property bag in place.
        mg.properties.clear()
        mg.properties.update(copy.deepcopy(self._metagraph_props))

        # 1. Graphs: restore survivors in place, drop added graphs,
        #    reinsert removed graphs as fresh objects (we no longer hold
        #    the original reference for those).
        live_gids = set(mg.graphs.keys())
        snap_gids = set(self._graphs.keys())

        for gid in live_gids - snap_gids:
            del mg.graphs[gid]

        for gid, gsnap in self._graphs.items():
            if gid in mg.graphs:
                g = mg.graphs[gid]
                g.name = gsnap.name
                g.role = gsnap.role
                g.schema = gsnap.schema
                g.nodes.clear()
                g.nodes.update(copy.deepcopy(gsnap.nodes))
                g.edges.clear()
                g.edges.update(copy.deepcopy(gsnap.edges))
                g.hyperedges.clear()
                g.hyperedges.update(copy.deepcopy(gsnap.hyperedges))
                # Phase 10 P85 — restore graph property bag in place.
                g.properties.clear()
                g.properties.update(copy.deepcopy(gsnap.properties))
                # Phase 10 P86 — restore graph-side dirty in place
                # (clear per-kind sets; outer dict identity preserved).
                for kind in list(g._soft_delete_dirty.keys()):
                    g._soft_delete_dirty[kind].clear()
                for kind, ids in gsnap.soft_delete_dirty.items():
                    g._soft_delete_dirty.setdefault(kind, set()).update(ids)
            else:
                # Removed graph: rebuild a fresh Graph. The shared
                # registry was cleared below, so reconstruction takes
                # the identity from there.
                g = Graph(
                    name=gsnap.name,
                    role=gsnap.role,
                    schema=gsnap.schema,
                    identity=mg.identity,
                    graph_id=gsnap.graph_id,
                    properties=copy.deepcopy(gsnap.properties),
                )
                # Graph's ctor auto-registers graph_id on the shared
                # registry when graph_id was None — but we pass graph_id
                # so registration is skipped (see Graph.__init__ guard).
                # Manually re-register the graph_id below as part of the
                # identity rebuild.
                g.nodes.update(copy.deepcopy(gsnap.nodes))
                g.edges.update(copy.deepcopy(gsnap.edges))
                g.hyperedges.update(copy.deepcopy(gsnap.hyperedges))
                mg.graphs[gid] = g

        # 2. Metaedges / metahyperedges. Halvim Phase 05a P11: endpoints
        #    are graph-id strings (not Graph objects per v3 baseline),
        #    so no rebinding pass is needed — deep-copy is sufficient.
        mg.metaedges.clear()
        mg.metaedges.update(copy.deepcopy(self._metaedges))

        mg.metahyperedges.clear()
        mg.metahyperedges.update(copy.deepcopy(self._metahyperedges))

        # 3. P84 — Phase 05b/05c intergraph primitives.
        mg.intergraph_edges.clear()
        mg.intergraph_edges.update(copy.deepcopy(self._intergraph_edges))

        mg.intergraph_hyperedges.clear()
        mg.intergraph_hyperedges.update(copy.deepcopy(self._intergraph_hyperedges))

        # 4. P84 — Phase 05b schema attach state.
        mg.schema_name = self._schema_name
        mg.schema = self._schema

        # 5. XRefs (ADR-0128) — clear + repopulate, rebuild inverse
        #    indexes (Phase 09 _xrefs_by_source + _xrefs_by_target).
        mg.xrefs.clear()
        mg._xrefs_by_source.clear()
        mg._xrefs_by_target.clear()
        for xid, xref in self._xrefs.items():
            x = copy.deepcopy(xref)
            mg.xrefs[xid] = x
            mg._xrefs_by_source.setdefault(x.source_id, set()).add(xid)
            mg._xrefs_by_target.setdefault(
                (x.target_metagraph_id, x.target_id), set()
            ).add(xid)

        # RB1 — restore Phase 09 _xrefs_dirty.
        mg._xrefs_dirty.clear()
        mg._xrefs_dirty.update(self._xrefs_dirty)

        # RPB-11 — restore Phase 10 _soft_delete_dirty (typed enum keys
        # per P72). Clear per-kind sets in place and re-populate so the
        # outer dict identity survives.
        for kind, ids in self._soft_delete_dirty.items():
            mg._soft_delete_dirty.setdefault(kind, set()).clear()
            mg._soft_delete_dirty.setdefault(kind, set()).update(ids)
        # Drop any kind keys not present in snapshot (defensive against
        # forward-incompatible snapshots — should not occur in v1 since
        # SoftDeleteKind is fixed-5).
        for kind in list(mg._soft_delete_dirty.keys()):
            if kind not in self._soft_delete_dirty:
                mg._soft_delete_dirty[kind].clear()

        # 6. IdentityRegistry: clear its _ids set in place (preserves
        #    the shared-registry object reference per ADR-0020), then
        #    re-register every snapshotted id. Phase 10 RF — docstring
        #    on IdentityRegistry.clear() amended to document this
        #    snapshot-restore consumer.
        mg.identity.clear()
        for uid in self._identity_ids:
            mg.identity.register(uid)


__all__ = ["MetagraphSnapshot"]
