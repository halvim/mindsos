"""``mindsos_core.persistence`` — Phase 07 backend addition.

Slim port of v3 ``mindsos_core/persistence/*``. Surface:

* :class:`Client` Protocol — minimal sync abstraction per ADR-0030
  (``run_query`` / ``run_batch`` / ``close``).
* :class:`FalkorClient` — concrete sync impl backed by the ``falkordb``
  Python driver; lazy driver import; :class:`PersistenceError` on
  connection failure.
* :class:`InMemoryClient` — call-recorder mock for unit tests; does not
  execute Cypher; tests using it assert "right Cypher emitted" only.
* :class:`AsyncClient` Protocol + :class:`ThreadPoolAsyncClient` (per
  ADR-0126) — ships in Phase 07 with no L1 consumer to prevent
  downstream ad-hoc wrappers.
* :func:`bootstrap` + :data:`DEFAULT_INDEXES` — 14 indexes per ADR-0123
  amended (10 node-label + 3 relationship + 1 hot-path) per P95 B.

JSON state files (managed by Phase 02-06 CLI verbs) remain
authoritative per M0 B. ``mindsos persistence sync --graph X``
projects JSON contents → FalkorDB.
"""

from __future__ import annotations

from .async_client import AsyncClient, ThreadPoolAsyncClient
from .bootstrap import DEFAULT_INDEXES, bootstrap
from .client import Client, FalkorClient, InMemoryClient, QueryResult
from .integrity import (
    IntegrityReport,
    PartialIntegrityReport,
    verify_invariants,
    verify_invariants_graph,
)

__all__ = [
    "Client",
    "FalkorClient",
    "InMemoryClient",
    "QueryResult",
    "AsyncClient",
    "ThreadPoolAsyncClient",
    "DEFAULT_INDEXES",
    "bootstrap",
    "IntegrityReport",
    "PartialIntegrityReport",
    "verify_invariants",
    "verify_invariants_graph",
]
