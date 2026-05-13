"""Integrity scanner (ADR-0123 §3 — Phase 07 slim port).

5-bucket integrity scanner runs in-memory on a :class:`Metagraph` and
its contained :class:`Graph` objects.

Per ADR-0123 §3 buckets:

1. ``duplicate_ids`` — same id used on more than one element per label
   within the metagraph.
2. ``cross_graph_edges`` — :class:`Edge` whose source/target nodes live
   in different graphs (Edge is intra-graph by ADR; an IntergraphEdge
   would be the right primitive).
3. ``orphan_hyperedges`` — :class:`HyperEdge` with zero members.
4. ``orphan_metaedges`` — :class:`MetaEdge` /
   :class:`MetaHyperEdge` referencing graphs not present in the
   metagraph.
5. ``dangling_tombstones`` — tombstone references (Phase 10 read-path
   filter) without a corresponding deleted element record. **Empty at
   Phase 07** — tombstone-write primitives ship (P16-pre) but no read
   filter consumer exists yet; bucket is reserved for Phase 10.

Per P98 A — :func:`verify_invariants_graph` ships as a sibling that
runs the **3 graph-internal buckets only** (``duplicate_ids`` restricted
to graph-local labels, ``orphan_hyperedges``, ``dangling_tombstones``).
The 2 Metagraph-context buckets (``cross_graph_edges`` and
``orphan_metaedges``) are reported as ``[skipped]`` when callers run
``verify --source=db --graph G`` per P49 A. Phase 08's metagraph
loader unblocks the full scanner against FalkorDB.

All buckets return ``List`` types so callers can iterate over the
specific offenders, not just a count.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, List, Tuple

if TYPE_CHECKING:
    from ..models.graph import Graph
    from ..models.metagraph import Metagraph


@dataclass
class IntegrityReport:
    """Output of :func:`verify_invariants` — five buckets of findings.

    Each list element is enough to identify the offending element so
    operator-level diagnosis can proceed. ``__bool__`` is true iff any
    bucket is non-empty; :meth:`summary` returns a one-line human
    description suitable for CLI output.
    """

    duplicate_ids: List[Tuple[str, List[str]]] = field(default_factory=list)
    """``(label, [ids])`` — same id appears under more than one element."""

    cross_graph_edges: List[Tuple[str, str]] = field(default_factory=list)
    """``(edge_id, source_graph_id)`` — Edge crosses graph boundaries."""

    orphan_hyperedges: List[str] = field(default_factory=list)
    """``[hyperedge_id]`` — HyperEdge with zero members (defensive scan)."""

    orphan_metaedges: List[str] = field(default_factory=list)
    """``[metaedge_id]`` — MetaEdge/MetaHyperEdge referencing missing graphs."""

    dangling_tombstones: List[str] = field(default_factory=list)
    """``[tombstone_id]`` — soft-delete reference without underlying record."""

    def __bool__(self) -> bool:
        """``True`` iff any bucket has findings."""
        return bool(
            self.duplicate_ids
            or self.cross_graph_edges
            or self.orphan_hyperedges
            or self.orphan_metaedges
            or self.dangling_tombstones
        )

    def summary(self) -> str:
        """One-line human summary; ``"clean"`` if no findings."""
        if not self:
            return "clean"
        parts = []
        if self.duplicate_ids:
            parts.append(f"{len(self.duplicate_ids)} duplicate-id label(s)")
        if self.cross_graph_edges:
            parts.append(f"{len(self.cross_graph_edges)} cross-graph edge(s)")
        if self.orphan_hyperedges:
            parts.append(f"{len(self.orphan_hyperedges)} orphan hyperedge(s)")
        if self.orphan_metaedges:
            parts.append(f"{len(self.orphan_metaedges)} orphan metaedge(s)")
        if self.dangling_tombstones:
            parts.append(f"{len(self.dangling_tombstones)} dangling tombstone(s)")
        return "; ".join(parts)


@dataclass
class PartialIntegrityReport:
    """Output of :func:`verify_invariants_graph` (P98 A) — 3-bucket subset.

    Same shape as the 3 graph-internal buckets in
    :class:`IntegrityReport`. The 2 Metagraph-context buckets
    (``cross_graph_edges``, ``orphan_metaedges``) are absent here;
    CLI's ``verify --source=db --graph G`` reports them as
    ``[skipped — requires --source=memory --metagraph M]`` per P49 A.
    """

    duplicate_ids: List[Tuple[str, List[str]]] = field(default_factory=list)
    orphan_hyperedges: List[str] = field(default_factory=list)
    dangling_tombstones: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(
            self.duplicate_ids
            or self.orphan_hyperedges
            or self.dangling_tombstones
        )

    def summary(self) -> str:
        if not self:
            return "clean (3 of 5 buckets — see [skipped])"
        parts = []
        if self.duplicate_ids:
            parts.append(f"{len(self.duplicate_ids)} duplicate-id label(s)")
        if self.orphan_hyperedges:
            parts.append(f"{len(self.orphan_hyperedges)} orphan hyperedge(s)")
        if self.dangling_tombstones:
            parts.append(f"{len(self.dangling_tombstones)} dangling tombstone(s)")
        return "; ".join(parts)


# ── public API ──────────────────────────────────────────────────────────────


def verify_invariants(mg: "Metagraph") -> IntegrityReport:
    """Run the full 5-bucket scanner on a Metagraph.

    Cheap enough to call before every release-ship (ADR-0123 — admin
    gate hook).
    """
    report = IntegrityReport()
    report.duplicate_ids = list(_scan_duplicate_ids(mg))
    report.cross_graph_edges = list(_scan_cross_graph_edges(mg))
    report.orphan_hyperedges = list(_scan_orphan_hyperedges(mg.graphs.values()))
    report.orphan_metaedges = list(_scan_orphan_metaedges(mg))
    # Phase 07 — dangling tombstones bucket is reserved (read-path filter
    # is Phase 10). Always empty here; populating it requires the read
    # filter's element-existence index to know what's missing.
    report.dangling_tombstones = []
    return report


def verify_invariants_graph(graph: "Graph") -> PartialIntegrityReport:
    """Run the 3 graph-internal buckets on a single Graph (P98 A).

    Used by ``mindsos persistence verify --source=db --graph G`` —
    a full Metagraph reconstruction is Phase 08 territory, so this
    sibling lets 07 ship a working ``--source=db`` verb for graphs.
    """
    report = PartialIntegrityReport()
    report.duplicate_ids = list(_scan_duplicate_ids_graph(graph))
    report.orphan_hyperedges = list(_scan_orphan_hyperedges([graph]))
    # Tombstones empty at Phase 07 (see above).
    report.dangling_tombstones = []
    return report


# ── per-bucket scanners (private) ───────────────────────────────────────────


def _scan_duplicate_ids(mg: "Metagraph") -> Iterable[Tuple[str, List[str]]]:
    """Bucket 1: same id appears > 1× under a single label.

    In-memory invariant guarded by :class:`IdentityRegistry` (Phase 02);
    scanner exists for FalkorDB-side direct-Cypher writes that bypass
    Core.
    """
    # Build per-label id occurrence map.
    by_label: dict = {
        "Graph": [],
        "Node": [],
        "Edge": [],
        "HyperEdge": [],
        "MetaEdge": [],
        "MetaHyperEdge": [],
        "IntergraphEdge": [],
        "IntergraphHyperEdge": [],
    }
    for g in mg.graphs.values():
        by_label["Graph"].append(g.graph_id)
        for n in g.nodes.values():
            by_label["Node"].append(n.node_id)
        for e in g.edges.values():
            by_label["Edge"].append(e.edge_id)
        for h in g.hyperedges.values():
            by_label["HyperEdge"].append(h.edge_id)
    for me in mg.metaedges.values():
        by_label["MetaEdge"].append(me.edge_id)
    for mh in mg.metahyperedges.values():
        by_label["MetaHyperEdge"].append(mh.edge_id)
    for ie in mg.intergraph_edges.values():
        by_label["IntergraphEdge"].append(ie.edge_id)
    for ih in mg.intergraph_hyperedges.values():
        by_label["IntergraphHyperEdge"].append(ih.edge_id)

    for label, ids in by_label.items():
        dupes = _duplicates(ids)
        if dupes:
            yield (label, dupes)


def _scan_duplicate_ids_graph(graph: "Graph") -> Iterable[Tuple[str, List[str]]]:
    """Bucket 1 restricted to one graph's labels (P98 A)."""
    nodes = [n.node_id for n in graph.nodes.values()]
    edges = [e.edge_id for e in graph.edges.values()]
    hyperedges = [h.edge_id for h in graph.hyperedges.values()]
    for label, ids in (("Node", nodes), ("Edge", edges), ("HyperEdge", hyperedges)):
        dupes = _duplicates(ids)
        if dupes:
            yield (label, dupes)


def _scan_cross_graph_edges(mg: "Metagraph") -> Iterable[Tuple[str, str]]:
    """Bucket 2: Edge whose source/target nodes are in different graphs.

    Edge is intra-graph by ADR; cross-graph linking is what
    IntergraphEdge is for. A leaked cross-graph Edge in FalkorDB is a
    write-path bug that this scan surfaces.
    """
    # Build (node_id -> containing graph_id) index.
    node_graph: dict = {}
    for g in mg.graphs.values():
        for n in g.nodes.values():
            node_graph[n.node_id] = g.graph_id

    for g in mg.graphs.values():
        for e in g.edges.values():
            s_gid = node_graph.get(e.source.node_id)
            t_gid = node_graph.get(e.target.node_id)
            if s_gid != g.graph_id or t_gid != g.graph_id:
                yield (e.edge_id, g.graph_id)


def _scan_orphan_hyperedges(graphs: Iterable["Graph"]) -> Iterable[str]:
    """Bucket 3: HyperEdge with zero members.

    Constructor enforces n ≥ 1 (Phase 03 SchemaError) but a direct
    Cypher write or a FalkorDB-side delete-member-without-cleanup can
    leave orphans. Scanner surfaces them.
    """
    for g in graphs:
        for h in g.hyperedges.values():
            if not h.nodes:
                yield h.edge_id


def _scan_orphan_metaedges(mg: "Metagraph") -> Iterable[str]:
    """Bucket 4: MetaEdge or MetaHyperEdge referencing missing graphs."""
    graph_ids = set(mg.graphs.keys())
    for me in mg.metaedges.values():
        if me.source_graph_id not in graph_ids:
            yield me.edge_id
            continue
        if me.target_graph_id not in graph_ids:
            yield me.edge_id
    for mh in mg.metahyperedges.values():
        missing = [gid for gid in mh.graph_ids if gid not in graph_ids]
        if missing:
            yield mh.edge_id


def _duplicates(ids: List[str]) -> List[str]:
    """Return sorted list of ids that appear more than once."""
    seen = set()
    dup = set()
    for i in ids:
        if i in seen:
            dup.add(i)
        seen.add(i)
    return sorted(dup)


__all__ = [
    "IntegrityReport",
    "PartialIntegrityReport",
    "verify_invariants",
    "verify_invariants_graph",
]
