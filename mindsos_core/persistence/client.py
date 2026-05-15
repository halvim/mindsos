"""Client abstraction over FalkorDB (Phase 07 slim port).

The Core Layer never talks to a specific driver directly — it talks to
a :class:`Client` Protocol. This makes the layer trivially testable
(via :class:`InMemoryClient`) and lets higher layers plug in a
production client (:class:`FalkorClient`) or a mock.

Per ADR-0030 the protocol is intentionally minimal: 3 methods, no
async (parallel :class:`AsyncClient` Protocol per ADR-0126), no
transactions (FalkorDB doesn't expose them), no per-call timeout.
``run_batch`` is sequential — a failure on statement N of M leaves
1..N-1 committed and N+1..M unwritten; recovery semantics live in
:class:`mindsos_core.persistence.wal.WriteAheadLog` (Phase 07) and
:class:`mindsos_core.persistence.MetagraphRepository` 4-step lifecycle
(P96 A).

The :class:`FalkorClient` lazily imports the ``falkordb`` package so
environments that only need the in-memory implementation don't pay the
driver install cost.

**Phase 07 invariants:**

* P2 A — :class:`FalkorClient.__init__` calls
  :func:`mindsos_core.persistence.bootstrap.bootstrap` (lazy index
  creation) so testers never see a "you forgot to bootstrap" error.
  ``InMemoryClient`` no-ops bootstrap.
* P4 A — Per-command connection lifecycle. CLI verbs open a client,
  run the verb, close. No long-lived process-scope clients.
* ``PersistenceError`` raised on driver-import failure, connection
  failure, and Cypher query failure (carrying offending statement).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    runtime_checkable,
)

from ..config import FalkorConfig
from ..exceptions import PersistenceError


@dataclass
class QueryResult:
    """Uniform result shape returned by every ``Client.run_query`` call.

    Rows are returned as ``dict[column_name -> value]`` regardless of
    driver. ``stats`` carries driver-specific counters when available
    (nodes_created, properties_set, etc.); empty dict when the driver
    doesn't surface them.
    """

    rows: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def first(self) -> Optional[Dict[str, Any]]:
        """Return the first row or ``None``."""
        return self.rows[0] if self.rows else None


@runtime_checkable
class Client(Protocol):
    """Minimal protocol the Core Layer requires of any graph backend (ADR-0030)."""

    def run_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """Execute ``query`` with bound ``params`` and return a :class:`QueryResult`."""
        ...

    def run_batch(
        self, statements: Sequence[Tuple[str, Dict[str, Any]]]
    ) -> List[QueryResult]:
        """Run several statements sequentially.

        Per ADR-0030: NO transactional semantics; a failure on statement
        N leaves 1..N-1 committed. Recovery via WAL (ADR-0122).
        """
        ...

    def close(self) -> None:
        """Release any underlying connection."""
        ...


# ── FalkorDB client ─────────────────────────────────────────────────────────


class FalkorClient:
    """Concrete :class:`Client` backed by the ``falkordb`` Python driver.

    The driver is imported lazily so importing this module doesn't
    require the package to be installed.

    Per P2 A — :func:`bootstrap` is called once on first construction;
    idempotent index creation. Bootstrap is best-effort: index-creation
    failures are surfaced as :class:`PersistenceError` only when none
    of the known "already exists" patterns match.
    """

    def __init__(
        self,
        config: FalkorConfig,
        *,
        skip_bootstrap: bool = False,
    ) -> None:
        try:
            from falkordb import FalkorDB  # type: ignore
        except ImportError as exc:  # pragma: no cover - import-time path
            raise PersistenceError(
                "The 'falkordb' package is required to use FalkorClient. "
                "Install it with: pip install falkordb"
            ) from exc

        self._config = config
        try:
            self._db = FalkorDB(
                host=config.host,
                port=config.port,
                password=config.password,
            )
            self._graph = self._db.select_graph(config.graph)
        except Exception as exc:  # pragma: no cover - depends on live DB
            raise PersistenceError(
                f"Failed to connect to FalkorDB at {config.host}:{config.port} "
                f"(graph={config.graph!r}): {exc}"
            ) from exc

        # Lazy bootstrap per P2 A. Skip flag exists for test harnesses
        # that want to inspect a pristine FalkorDB graph.
        if not skip_bootstrap:
            # Late import to break the
            # ``persistence.bootstrap`` <-> ``persistence.client`` cycle.
            # Phase 09 RR-16 — bootstrap creates indexes; the L1
            # replayer wrapper then registers ``xref_add`` /
            # ``xref_remove`` replayers onto this client's per-instance
            # ``_replayers`` dict (P51).
            from .bootstrap import bootstrap, register_all_l1_replayers

            bootstrap(self)
            register_all_l1_replayers(self)

    # ── query ──────────────────────────────────────────────────────────

    def run_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        try:
            res = self._graph.query(query, params or {})
        except Exception as exc:
            raise PersistenceError(
                f"FalkorDB query failed: {exc}\nQuery: {query}"
            ) from exc
        rows = self._rows_from_result(res)
        stats = getattr(res, "statistics", None) or {}
        return QueryResult(
            rows=rows, stats=dict(stats) if isinstance(stats, dict) else {}
        )

    def run_batch(
        self, statements: Sequence[Tuple[str, Dict[str, Any]]]
    ) -> List[QueryResult]:
        """Execute statements sequentially.

        FalkorDB does not expose a multi-statement transaction primitive
        over its Redis wire protocol. Failures surface the offending
        index in the error message for easier debugging; per ADR-0030
        statements 1..N-1 stay committed.
        """
        results: List[QueryResult] = []
        for idx, (q, p) in enumerate(statements):
            try:
                results.append(self.run_query(q, p))
            except PersistenceError as exc:
                raise PersistenceError(
                    f"Batch statement #{idx} failed: {exc}"
                ) from exc
        return results

    def close(self) -> None:
        # falkordb-py keeps a Redis connection pool; close if present.
        close = getattr(self._db, "close", None)
        if callable(close):
            try:
                close()
            except Exception:  # pragma: no cover
                pass

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _rows_from_result(res: Any) -> List[Dict[str, Any]]:
        """Normalise driver-specific result shapes to ``list[dict]``.

        falkordb-py's ``header`` is either a list of ``(type_code, name)``
        tuples or a plain list of names depending on version; handle both.
        """
        header = getattr(res, "header", None)
        raw_rows = getattr(res, "result_set", None)
        if not raw_rows:
            return []

        if header and isinstance(header[0], (list, tuple)) and len(header[0]) >= 2:
            columns = [h[1] for h in header]
        elif header:
            columns = list(header)
        else:
            columns = [f"col_{i}" for i in range(len(raw_rows[0]))]

        return [dict(zip(columns, row)) for row in raw_rows]


# ── in-memory client ────────────────────────────────────────────────────────


class InMemoryClient:
    """Minimal in-memory client for unit tests.

    Does NOT execute Cypher — records every statement that would have
    run. Sufficient to test query builders and repository orchestration
    without a live FalkorDB. Round-trip tests requiring real Cypher
    execution use :class:`FalkorClient` against the sidecar
    (:func:`pytest.mark.integration`).

    Per :class:`mindsos_core.persistence.bootstrap` — InMemoryClient
    does not run bootstrap on construction; tests that need
    bootstrap-emitted statements explicitly call ``bootstrap(client)``.
    """

    def __init__(self) -> None:
        self.calls: List[Tuple[str, Dict[str, Any]]] = []
        self._scripted_results: List[QueryResult] = []
        self.closed: bool = False

    # ── scripting ──────────────────────────────────────────────────────

    def script(self, rows: List[Dict[str, Any]]) -> None:
        """Enqueue a :class:`QueryResult` to be returned by the next ``run_query``."""
        self._scripted_results.append(QueryResult(rows=list(rows)))

    def script_result(self, result: QueryResult) -> None:
        """Enqueue a pre-built :class:`QueryResult` (e.g. with stats)."""
        self._scripted_results.append(result)

    # ── protocol methods ───────────────────────────────────────────────

    def run_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        self.calls.append((query, dict(params or {})))
        if self._scripted_results:
            return self._scripted_results.pop(0)
        return QueryResult()

    def run_batch(
        self, statements: Sequence[Tuple[str, Dict[str, Any]]]
    ) -> List[QueryResult]:
        return [self.run_query(q, p) for q, p in statements]

    def close(self) -> None:
        self.closed = True


__all__ = [
    "QueryResult",
    "Client",
    "FalkorClient",
    "InMemoryClient",
]
