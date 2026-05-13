---
last_confirmed_phase: 07
---

# `mindsos_core.persistence.Client` API

Sync + async surfaces over FalkorDB.

## `Client` Protocol (ADR-0030)

Minimal sync protocol:

```python
from typing import Protocol
from mindsos_core.persistence import Client, QueryResult

class Client(Protocol):
    def run_query(self, query: str, params: dict | None = None) -> QueryResult: ...
    def run_batch(self, statements: Sequence[tuple[str, dict]]) -> list[QueryResult]: ...
    def close(self) -> None: ...
```

No transactions (FalkorDB doesn't expose them). No async (parallel
`AsyncClient` Protocol below). No per-call timeout. `run_batch` is
**sequential** — failure on statement N of M leaves 1..N-1 committed
and N+1..M unwritten; recovery semantics live in
`WriteAheadLog` (ADR-0122) and `MetagraphRepository.persist`'s 4-step
lifecycle (P96 A).

`QueryResult` carries `rows: list[dict]` (driver-normalised) + an
optional `stats: dict` of counters.

## `FalkorClient` — production sync client

Lazy import of the `falkordb` driver; raises `PersistenceError` on
import failure or connection failure. `__init__` fires
`bootstrap(self)` per P2 A (idempotent).

```python
from mindsos_core.config import FalkorConfig
from mindsos_core.persistence import FalkorClient

config = FalkorConfig.from_env_and_manifest(manifest_path)
client = FalkorClient(config)
try:
    res = client.run_query("MATCH (n) RETURN count(n) AS n")
finally:
    client.close()
```

Pass `skip_bootstrap=True` to suppress the lazy bootstrap for tests
that want to inspect a pristine FalkorDB graph.

## `InMemoryClient` — unit-test call recorder

Records every `run_query` / `run_batch` invocation as `(query,
params)` tuples on `.calls`; does NOT execute Cypher. Use `.script(rows)`
to enqueue a scripted `QueryResult` for the next `run_query`.

```python
from mindsos_core.persistence import InMemoryClient

c = InMemoryClient()
c.script([{"id": "x", "version": 1}])
res = c.run_query("MATCH (n) WHERE n.id = $id RETURN n.id, n._version AS version",
                  {"id": "x"})
assert res.rows == [{"id": "x", "version": 1}]
```

Round-trip tests that need real Cypher execution use `FalkorClient`
against the sidecar — marked `@pytest.mark.integration` (M11).

## `AsyncClient` Protocol (ADR-0126)

Parallel async surface; mirrors the sync `Client`:

```python
from mindsos_core.persistence import AsyncClient, ThreadPoolAsyncClient

async def main():
    sync = FalkorClient(FalkorConfig.from_env())
    client = ThreadPoolAsyncClient(sync)
    res = await client.run_query("MATCH (n) RETURN count(n)")
    await client.close()
```

`ThreadPoolAsyncClient` wraps a sync `Client` via `asyncio.to_thread`.
Each call blocks one worker thread for the duration of the underlying
Cypher query.

### Gotchas (per ADR-0126)

- **Thread-pool starvation** under high concurrency. The default
  asyncio pool is CPU-count-sized. Install a larger pool if needed.
- **Cancellation is cosmetic.** `asyncio.CancelledError` propagates
  from `to_thread` but the underlying Cypher query keeps running.
  FalkorDB driver doesn't expose cancellation; a future native async
  driver would fix this.
