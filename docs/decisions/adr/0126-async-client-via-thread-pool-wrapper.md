---
title: AsyncClient protocol via asyncio.to_thread
status: Accepted
date: 2026-04-27
accepted_date: 2026-05-13
layer: L1
amends: [0030]
---

# ADR-0126: `AsyncClient` Protocol via `asyncio.to_thread`

**Status:** Accepted (Phase 07 — M3 A inline flip 2026-05-13)

**Date:** 2026-04-27 · **Accepted:** 2026-05-13

**Amends:** ADR-0030 (Client Protocol minimal sync — extends with parallel async surface).

## Context

The FalkorDB Python driver is sync. Every `client.run_query` blocks the calling thread. Future consumers (web UI, API gateway, L4's per-session orchestrator running concurrent capacities) either pin a thread per request or fake async.

Today there is no front-end and no async caller. The previous L1 redesign decision (W5 in the design conversation) was to **ship AsyncClient now** rather than defer until a real consumer exists, because the wrapper is small (~50 LOC), independent of all other ADRs, and prevents downstream layers from inventing their own.

## Decision

Add an `AsyncClient` Protocol parallel to the existing `Client` Protocol. The default implementation wraps `Client` via `asyncio.to_thread`.

```python
from typing import Protocol

class AsyncClient(Protocol):
    """Async surface over a sync Client."""

    async def run_query(self, query: str, params: dict | None = None) -> QueryResult: ...
    async def run_batch(self, statements: list[tuple[str, dict]]) -> list[QueryResult]: ...
    async def close(self) -> None: ...


class ThreadPoolAsyncClient:
    """Default AsyncClient implementation. Wraps a sync Client by dispatching
    each call to a thread pool via asyncio.to_thread. No connection pooling —
    the underlying sync Client owns its connection."""

    def __init__(self, sync_client: Client):
        self._sync = sync_client

    async def run_query(self, query, params=None):
        return await asyncio.to_thread(self._sync.run_query, query, params)

    async def run_batch(self, statements):
        return await asyncio.to_thread(self._sync.run_batch, statements)

    async def close(self):
        await asyncio.to_thread(self._sync.close)
```

**Surface decisions:**

- `AsyncClient` is its own Protocol, not a subclass of `Client`. Static type-checkers can demand one or the other; mixing in a single call site is a type error.
- The wrapper runs in the default `asyncio` thread pool. No new pool created. Caller can override by setting their own pool before calling.
- No connection pooling beyond what the sync `Client` provides. FalkorDB's driver is connection-per-client; wrapping doesn't change that.
- No transactions. Same as `Client` (per ADR-0030 + ADR-0122).
- No cancellation. `asyncio.CancelledError` propagates from `to_thread`, but the underlying Cypher query continues executing. Documented in the developer guide as a known gotcha.

**Public API:**

```python
from mindsos_core import AsyncClient, ThreadPoolAsyncClient

async def main():
    sync = FalkorClient(FalkorConfig.from_env())
    async_client = ThreadPoolAsyncClient(sync)
    result = await async_client.run_query("MATCH (n) RETURN count(n)")
    await async_client.close()
```

`AsyncClient` is exported from `mindsos_core/__init__.py`. Repository classes do **not** gain async variants in v1 — async is a Client-Protocol-level concern, and v1 callers can wrap repositories themselves if needed.

## Rationale

Shipping AsyncClient now (instead of "when first front-end arrives") prevents three problems:

1. Downstream layers that need async will wrap the sync Client themselves; multiple ad-hoc wrappers would drift.
2. L4's per-session orchestrator (per L4 design handoff §3) runs capacities concurrently; without an async client, it pins a thread per concurrent capacity. AsyncClient avoids the thread-pool starvation pattern.
3. The cost is small (~50 LOC) and the surface is stable (the Protocol matches the sync Client's three methods); deferral has a marginal payoff.

The thread-pool wrapper is the standard pattern for sync-to-async adaptation. If/when FalkorDB ships a native async driver, `ThreadPoolAsyncClient` swaps to a `NativeAsyncFalkorClient` without changing the Protocol surface or any caller.

## Consequences

**Good:**

- Front-end work (CLI's interactive shell, future web UI, L4 orchestrator) gets async ergonomics from day one.
- Layer authors don't reinvent the wrapper.
- The Protocol is forward-compatible with native async drivers.

**Tradeoffs:**

- Thread pool starvation under high concurrency. The default `asyncio` pool is small (CPU count); running many concurrent Cypher queries blocks. Mitigation: callers can set a larger pool. Documented in the developer guide.
- Not real async — every call still blocks a thread. The performance characteristic is "thread-per-concurrent-query," not "events on one event loop."
- Cancellation is cosmetic; the underlying query keeps running. Documented as a gotcha.

**Coordinated changes:**

- `mindsos_core/persistence/async_client.py` (new) — Protocol + `ThreadPoolAsyncClient`.
- `mindsos_core/__init__.py` — export.
- `docs/api/core/client.md` — async section.
- `docs/dev/internals/core.md` — gotcha section on thread-pool starvation and cancellation semantics.

## Alternatives considered

1. **Defer until first front-end.** Rejected — L4's orchestrator needs concurrency; downstream layers will wrap ad-hoc; the deferral pays off only if no consumer arrives, which is unlikely.
2. **Subclass `Client` instead of parallel Protocol.** Rejected — confuses static type checkers (sync code can't accidentally call async methods); separate Protocol forces the caller to choose explicitly.
3. **Wait for a native async FalkorDB driver.** Rejected — timeline outside our control; thread-pool wrapper unblocks immediately and swaps cleanly when native lands.
4. **Build a connection pool in the wrapper.** Rejected for v1 — adds complexity for a benefit no current consumer has measured. Defer.

## Implementation references

- `mindsos_core/persistence/async_client.py` (new, ~50 LOC).
- `mindsos_core/__init__.py` — re-export.
- Tests: `tests/unit/core/test_async_client.py` (~5 tests; covers wrapper correctness and exception propagation).
- Documentation: `docs/api/core/client.md` (new "Async surface" section), `docs/dev/internals/core.md` (gotchas section).

**Acceptance criteria (Phase 07 P27 C amendment):** *Accepted when L1 mechanism ships + `core.md` documents the surface; consumer integration tracked separately.* Met by Phase 07: `AsyncClient` Protocol + `ThreadPoolAsyncClient` ship in `mindsos_core/persistence/async_client.py` (~100 LOC); `docs/api/core/client.md` documents the async surface + thread-pool starvation + cancellation gotcha.
