"""Async surface over the sync :class:`Client` protocol (ADR-0126, W5).

Wraps any sync :class:`Client` via :func:`asyncio.to_thread` so async
consumers (web UIs, L4's per-session orchestrator) can interact with the
underlying graph without pinning a thread per request explicitly.

.. note::

   This is a *thread-pool wrapper*, not a real async driver. Each call
   blocks one worker thread for the duration of the underlying Cypher
   query. Cancellation propagates ``asyncio.CancelledError`` from
   :func:`asyncio.to_thread` but does **not** cancel the in-flight
   query — FalkorDB's driver doesn't expose cancellation. Documented
   gotcha (per ADR-0126 §Consequences).

   When FalkorDB ships a native async driver, swap
   :class:`ThreadPoolAsyncClient` for a ``NativeAsyncFalkorClient``
   without changing the :class:`AsyncClient` Protocol or any caller.

Phase 07 ships AsyncClient with no L1 consumer (per ADR-0126
§Rationale — prevents downstream layers from inventing their own).
"""

from __future__ import annotations

import asyncio
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

from .client import Client, QueryResult


@runtime_checkable
class AsyncClient(Protocol):
    """Async surface mirroring the sync :class:`Client` Protocol (ADR-0126)."""

    async def run_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """Execute ``query`` and return a :class:`QueryResult`."""
        ...

    async def run_batch(
        self, statements: Sequence[Tuple[str, Dict[str, Any]]]
    ) -> List[QueryResult]:
        """Run several statements; semantics match sync :meth:`Client.run_batch`."""
        ...

    async def close(self) -> None:
        """Release the underlying connection."""
        ...


class ThreadPoolAsyncClient:
    """Default :class:`AsyncClient` implementation.

    Wraps a sync :class:`Client` by dispatching each call to the default
    asyncio thread pool. No connection pooling beyond what the underlying
    sync client provides.

    Usage::

        from mindsos_core import FalkorClient, FalkorConfig, ThreadPoolAsyncClient

        sync = FalkorClient(FalkorConfig.from_env())
        client = ThreadPoolAsyncClient(sync)
        result = await client.run_query("MATCH (n) RETURN count(n)")
        await client.close()
    """

    def __init__(self, sync_client: Client) -> None:
        self._sync = sync_client

    async def run_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        return await asyncio.to_thread(self._sync.run_query, query, params)

    async def run_batch(
        self, statements: Sequence[Tuple[str, Dict[str, Any]]]
    ) -> List[QueryResult]:
        return await asyncio.to_thread(self._sync.run_batch, statements)

    async def close(self) -> None:
        await asyncio.to_thread(self._sync.close)


__all__ = [
    "AsyncClient",
    "ThreadPoolAsyncClient",
]
