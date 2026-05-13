---
last_confirmed_phase: 07
---

# `mindsos_core.persistence.WriteAheadLog`

Per-Metagraph write-ahead log for multi-statement write safety
(ADR-0122). Primary surface is the context-manager API (Phase 07
P50 B); raw `begin` / `commit` primitives accessible for
failure-injection tests and direct programmatic use.

## Primary API — `WriteAheadLog.entry(...)` context manager

```python
from uuid import uuid4
from mindsos_core.persistence import WriteAheadLog

wal = WriteAheadLog(client, metagraph_id="mg1")
with wal.entry(
    operation_id=uuid4().hex,
    kind="kl.propose_for_promotion",
    payload={"draft_id": "...", "target_role": "lexicon"},
) as op_id:
    # ... apply writes against the target graph ...
    # __exit__ stamps committed=true on normal exit.
    # On exception, the entry stays committed=false for recovery.
```

`__enter__` calls `begin()`; `__exit__` calls `commit()` on success
and re-raises on failure (entry stays uncommitted; `recover()`
handles it on next server boot).

## Raw primitives

```python
op_id = wal.begin(operation_id=uuid4().hex, kind="my.kind", payload={"x": 1})
# ... do writes ...
wal.commit(op_id)
```

- `begin(*, operation_id, kind, payload=None) -> str` — write a
  `committed=false` row; returns `operation_id`.
- `commit(operation_id) -> None` — stamp `committed=true`. Raises
  `PersistenceError` if the row doesn't exist.
- `list_uncommitted() -> list[WALEntry]` — every uncommitted row for
  this metagraph.
- `count_uncommitted() -> int` — cheap count for `diagnose`.
- `gc(*, older_than_seconds: int) -> int` — delete committed rows
  older than the threshold; returns count deleted.

## Replayer registry

```python
from mindsos_core.persistence import register_replayer, recover

def my_replayer(payload: dict) -> None:
    # ... reapply writes for this kind ...
    pass

register_replayer("my.kind", my_replayer)

# At server start:
n = recover(client, metagraph_id="mg1")
# n = number of uncommitted entries successfully replayed and committed.
```

Replayers MUST be idempotent — `recover()` retries on the next start
if a replayer fails. Unknown `kind` strings are skipped (don't
auto-commit; a future deployment may register the replayer).
`clear_replayers()` resets the registry (tests use this between
cases).

## Phase 07 consumer

None. WAL ships as the mechanism only; L0/L2 wires replayers later
(KL `propose_for_promotion`, server `release_update`).

## Failure-injection (P82 A — `test_whole_batch_refused`)

`tests/_shared/raises_on_nth_call.py` provides `RaisesOnNthCall(real,
n=N)` — wraps a real `Client` and raises `PersistenceError` on the
N-th call. Used by `tests/phase_07/test_wal.py::test_whole_batch_refused`
to verify the WAL commit step is skipped when the underlying write
fails. **NOTE**: this does NOT simulate a real mid-batch crash (that
requires a subprocess-crash fixture deferred to Phase 11); the
wrapper at Client surface refuses the entire batch.
