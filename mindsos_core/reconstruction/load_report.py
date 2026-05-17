"""Loader report dataclasses (Phase 11 — PB-9 B + PB-13 A).

Phase 11 adds a structured load report so the loader's new
``unknown_edge_type_policy`` (ADR-0134 + Phase 11 §amendment-2) can
surface drop counts to callers without mutating the loaded
:class:`Graph` / :class:`Metagraph`.

Two report types:

* :class:`LoadReport` — per-:class:`Graph` load outcome. Returned by
  :func:`mindsos_core.reconstruction.load_graph_with_report`. Carries
  the total dropped-edge count plus a per-distinct-type breakdown
  (PB-10 A — per-distinct-type WARN granularity, not per-edge).
* :class:`MetagraphLoadReport` — per-:class:`Metagraph` aggregate.
  Returned by :func:`mindsos_core.reconstruction.load_with_report`.
  Carries per-Graph :class:`LoadReport` entries plus
  Metagraph-aggregate totals.

Both follow the Phase 07 :class:`mindsos_core.persistence.integrity.IntegrityReport`
convention: mutable :func:`dataclasses.dataclass` with ``__bool__``
(true iff any drops) and a ``summary()`` one-liner suitable for CLI
output. Callers should treat instances as read-only post-construction.

Phase 11 design picks recorded in
``confirmation_docs/PHASE_11_DESIGN_LOG.md``:

* PB-9 B — drop count lives on the report, NOT on :class:`Graph`.
  Avoids state-file v=5 → v=6 bump.
* PB-12 B — additive sibling pattern; existing
  :func:`load_graph` signature unchanged.
* PB-13 A — :class:`MetagraphLoadReport` aggregates per-Graph reports
  via ``per_graph: dict[graph_id, LoadReport]``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping


@dataclass
class LoadReport:
    """Per-:class:`Graph` load outcome (Phase 11 — PB-9 B).

    Returned by :func:`mindsos_core.reconstruction.load_graph_with_report`
    alongside the loaded :class:`Graph`.

    Attributes:
        graph_id: The :class:`Graph` this report describes.
        dropped_edge_count: Total edges dropped during load (sum of
            :attr:`dropped_by_type` values).
        dropped_by_type: Map of edge ``type_name`` → drop count. Empty
            when no edges were dropped or when the policy is ``ignore``
            (in which case no tracking is done).

    Phase 11 only drops on the ``warn`` and ``error`` policy paths —
    ``ignore`` short-circuits before reaching the report. ``error``
    raises :class:`UnknownEdgeTypeError` before any subsequent
    drops are tracked, so the report sees at most one entry under
    ``error``.
    """

    graph_id: str = ""
    dropped_edge_count: int = 0
    dropped_by_type: Dict[str, int] = field(default_factory=dict)

    def __bool__(self) -> bool:
        """``True`` iff any edges were dropped."""
        return self.dropped_edge_count > 0

    def add_drop(self, type_name: str) -> None:
        """Record a single dropped edge of ``type_name`` (loader use only).

        Increments :attr:`dropped_edge_count` by 1 and the corresponding
        :attr:`dropped_by_type` entry by 1.
        """
        self.dropped_by_type[type_name] = (
            self.dropped_by_type.get(type_name, 0) + 1
        )
        self.dropped_edge_count += 1

    def summary(self) -> str:
        """One-line human summary; ``"clean"`` if no drops."""
        if not self:
            return "clean"
        type_count = len(self.dropped_by_type)
        return (
            f"{self.dropped_edge_count} edge(s) dropped across "
            f"{type_count} type(s)"
        )


@dataclass
class MetagraphLoadReport:
    """Per-:class:`Metagraph` aggregate load outcome (Phase 11 — PB-13 A).

    Returned by :func:`mindsos_core.reconstruction.load_with_report`
    alongside the loaded :class:`Metagraph`.

    Aggregates per-:class:`Graph` :class:`LoadReport` entries plus
    Metagraph-level totals so the CLI can render either granularity
    without re-walking the per-graph dict.

    Attributes:
        metagraph_id: The :class:`Metagraph` this report describes.
        per_graph: Map of ``graph_id`` → :class:`LoadReport` for every
            contained graph that the loader processed (one entry per
            graph, including clean ones).
        total_dropped_edge_count: Sum of
            ``per_graph[*].dropped_edge_count``.
        total_dropped_by_type: Map of edge ``type_name`` → total drop
            count summed across all per-graph reports.
    """

    metagraph_id: str = ""
    per_graph: Dict[str, LoadReport] = field(default_factory=dict)
    total_dropped_edge_count: int = 0
    total_dropped_by_type: Dict[str, int] = field(default_factory=dict)

    def __bool__(self) -> bool:
        """``True`` iff any per-graph report has drops."""
        return self.total_dropped_edge_count > 0

    def attach(self, report: LoadReport) -> None:
        """Attach a per-:class:`Graph` :class:`LoadReport` (loader use only).

        Adds the report to :attr:`per_graph` keyed by
        :attr:`LoadReport.graph_id` and folds its counts into the
        Metagraph-level totals.
        """
        self.per_graph[report.graph_id] = report
        self.total_dropped_edge_count += report.dropped_edge_count
        for type_name, count in report.dropped_by_type.items():
            self.total_dropped_by_type[type_name] = (
                self.total_dropped_by_type.get(type_name, 0) + count
            )

    def summary(self) -> str:
        """One-line human summary; ``"clean"`` if no drops."""
        if not self:
            return "clean"
        graph_count = sum(1 for r in self.per_graph.values() if r)
        type_count = len(self.total_dropped_by_type)
        return (
            f"{self.total_dropped_edge_count} edge(s) dropped across "
            f"{type_count} type(s) in {graph_count} graph(s)"
        )


__all__ = ["LoadReport", "MetagraphLoadReport"]
