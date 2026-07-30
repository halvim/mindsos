"""Reconstruction surface (Phase 07 + Phase 08 + Phase 09).

Phase 07 shipped ``load_graph(client, graph_id) -> Graph`` (M14).
Phase 08 added the metagraph + streaming surface per ADR-0124 +
the locked R4-1 A load sequence:

* :func:`load_graph` — Phase 07 surface, refactored internally to call
  :func:`iter_load_graph` per RR-12 A.
* :func:`iter_load_graph` — Streaming variant (PB-3 A signature,
  RPB-1 A cross-batch trailer semantics, RPB-10 A intra-graph only).
* :class:`MetagraphLoader` — Orchestrator class (RR-8 A) with
  ``.load(mid, ...)`` + ``.refresh(mg, role, ...)`` per ADR-0124.
* :func:`load_metagraph` — Module-level convenience function
  (RR-5 B) wrapping :meth:`MetagraphLoader.load`.

**Phase 09 (this row) adds the XRef reconstruction surface:**

* :class:`XRefLoader` — clear-first :class:`XRef` reconstruction
  (PB-9 + P55 + P64). Direct dict assignment; bypasses
  :meth:`Metagraph.add_xref` (which would trigger inline DB writes).
* :func:`attach_xref_loader` — M18 idempotent helper that subscribes
  the loader as a :meth:`Metagraph.register_after_load_observer`
  callback.

Re-exports three exception classes from :mod:`mindsos_core.exceptions`
for caller convenience:

* :class:`RefreshUnsafeError` — class-only per Phase 08 PB-5 B.
* :class:`WALReplayerMissingError` — recover-on-load sentinel
  (Phase 09 P62 — propagates loud after the silent narrow-catch was
  removed).
* :class:`RoleMismatchError` — refresh DB-drift signal (R4-2 D).
"""

from __future__ import annotations

from ..exceptions import (
    RefreshUnsafeError,
    RoleMismatchError,
    WALReplayerMissingError,
)
from .graph_loader import (
    graph_anchors_by_role,
    iter_load_graph,
    load_graph,
    load_graph_with_report,
)
from .load_report import LoadReport, MetagraphLoadReport
from .metagraph_loader import (
    MetagraphLoader,
    load_metagraph,
    load_metagraph_with_report,
)
from .xref_loader import XRefLoader, attach_xref_loader

__all__ = [
    "load_graph",
    "graph_anchors_by_role",
    "iter_load_graph",
    "load_graph_with_report",
    "load_metagraph_with_report",
    "LoadReport",
    "MetagraphLoadReport",
    "MetagraphLoader",
    "load_metagraph",
    "XRefLoader",
    "attach_xref_loader",
    "RefreshUnsafeError",
    "RoleMismatchError",
    "WALReplayerMissingError",
]
