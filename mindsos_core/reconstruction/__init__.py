"""Reconstruction surface (Phase 07 + Phase 08).

Phase 07 shipped ``load_graph(client, graph_id) -> Graph`` (M14).
Phase 08 adds the metagraph + streaming surface per ADR-0124 (now
Accepted) + the locked R4-1 A load sequence:

* :func:`load_graph` — Phase 07 surface, refactored internally to call
  :func:`iter_load_graph` per RR-12 A.
* :func:`iter_load_graph` — NEW. Streaming variant (PB-3 A signature,
  RPB-1 A cross-batch trailer semantics, RPB-10 A intra-graph only).
* :class:`MetagraphLoader` — NEW. Orchestrator class (RR-8 A) with
  ``.load(mid, ...)`` + ``.refresh(mg, role, ...)`` per ADR-0124.
* :func:`load_metagraph` — NEW. Module-level convenience function
  (RR-5 B) wrapping :meth:`MetagraphLoader.load`.

Phase 08 also re-exports three new exception classes from
:mod:`mindsos_core.exceptions` for caller convenience:

* :class:`RefreshUnsafeError` — class-only per PB-5 B (no enforcement).
* :class:`WALReplayerMissingError` — recover-on-load sentinel
  (RPB-3 C; narrow-caught by ``load_metagraph``).
* :class:`RoleMismatchError` — refresh DB-drift signal (R4-2 D).
"""

from __future__ import annotations

from ..exceptions import (
    RefreshUnsafeError,
    RoleMismatchError,
    WALReplayerMissingError,
)
from .graph_loader import iter_load_graph, load_graph
from .metagraph_loader import MetagraphLoader, load_metagraph

__all__ = [
    "load_graph",
    "iter_load_graph",
    "MetagraphLoader",
    "load_metagraph",
    "RefreshUnsafeError",
    "RoleMismatchError",
    "WALReplayerMissingError",
]
