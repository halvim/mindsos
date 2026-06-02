# ADR-0006: Per-user RLocks + GLOBAL_PROMOTE_LOCK acquired in lexicographic order

- **Status:** Accepted
- **Date:** 2026-04-22
- **Related:** ADR-0007, ADR-0009

## Context

Promotion (Local → Global) is the only operation that mutates Global shared state on a user-authored pathway. It touches:

- **N user Locals** (the authors of the candidate drafts) — each must be installed and readable.
- **The Global Metagraph** — receives new nodes stamped with attribution.

Any two promotions that touch an overlapping set of authors must serialize on those authors' Locals. Every promotion must serialize with every other promotion on the Global. And the lock order must be deterministic, or concurrent promotions will deadlock at the first overlapping user.

## Decision

Two tiers of locks:

1. **Per-user `threading.RLock`**, one per `user_id`, lazily created in `mindsos_server.mutex.UserMutexRegistry`. The registry exposes `user_mutexes(user_ids: Iterable[str]) -> AbstractContextManager` which:
   - Sorts `user_ids` lexicographically.
   - Acquires each lock in order.
   - Releases in reverse on exit.
2. **`GLOBAL_PROMOTE_LOCK: threading.RLock`**, a module-level singleton in `mindsos_server.mutex`.

The `promote()` orchestrator always acquires in this order:

```
with GLOBAL_PROMOTE_LOCK:
    with user_mutexes(sorted(authors)):
        ... install, snapshot, promote, flush ...
```

`similarity_report()` acquires **only** the per-user mutexes (no Global lock) because it doesn't mutate Global.

Other admin paths (`read_other_local`, admin user ops) acquire only the single user mutex they need, and never the Global lock.

## Rationale

- **Deterministic lock order eliminates deadlock.** Lexicographic sort on `user_ids` is stable across callers; two promotions with overlapping author sets will acquire in the same order and wait instead of deadlocking.
- **Global lock is a single point.** Promotion is rare relative to other ops; serializing it globally is a non-issue for throughput and removes an entire class of invariant-violation bugs (two promotions snapshot-racing on the Global).
- **`RLock` not `Lock`.** The orchestrator and its helpers are layered; the same thread may need to re-enter the same lock (e.g., promotion calls into similarity check, which in a legacy path held the same lock). Reentrancy is cheap insurance.
- **Registry pattern, not a dict-of-locks-visible-everywhere.** Keeps the acquire/release sequence in one place; callers can't forget to sort.

## Consequences

- `similarity_report` and `promote` serialize across threads. For the current tool-sized workload this is fine; a future scale event would partition Globals by role and revisit.
- Deadlock by misuse is only possible if a caller acquires a per-user lock *outside* `user_mutexes()` and then tries to promote — enforced by code review and the convention that per-user locks are only acquired via the registry.
- The test suite exercises the Global lock with a spawned thread that attempts `GLOBAL_PROMOTE_LOCK.acquire(blocking=False)` while promote holds it, asserting the non-blocking acquire fails.

## Alternatives considered

1. **Single global mutex for everything.** Rejected — blocks unrelated admin reads behind promotions; hurts latency for cheap ops.
2. **Hash-based lock order (e.g., acquire by `hash(user_id)`).** Rejected — still deterministic but opaque; debugging a deadlock with lex-sorted names is materially easier.
3. **Two-phase locking with timeouts.** Rejected — introduces retry complexity without removing the underlying need for an order.
4. **Lock-free promotion via CAS on a Global version number.** Interesting but incompatible with in-place `restore_into` (ADR-0007) and with the session-scoped install pattern (ADR-0008).

## Revisions

### amendment-1 (Phase 24 ship — 2026-05-22) — GLOBAL_PROMOTE_LOCK renamed to RELEASE_SHIP_LOCK; substrate threading.RLock confirmed; per-user mutex retained

**Trigger:** ADR-0118 §"Consequences" amended this ADR in place
("`GLOBAL_PROMOTE_LOCK` renamed to `RELEASE_SHIP_LOCK` and held only
inside `release_update`"). Phase 24 ship lands the renamed lock in
code; this amendment ratifies the rename + locks the substrate.

**Amended decision:**

1. **`GLOBAL_PROMOTE_LOCK` → `RELEASE_SHIP_LOCK`.** Same semantics
   (single module-level lock, serializes the holder), narrower scope
   (held only inside `release_update`, not inside per-promotion
   path). Module location: `mindsos_server/locks.py` (NEW at Phase
   24).
2. **Substrate: `threading.RLock`** per Phase 24 design log PB-12(a).
   Matches the original §Decision §2 substrate (no change there);
   v1 is single-process per ADR-0129 §Rationale so threading
   primitive is sufficient. `release_update` body acquires RLock
   outer; SQLite-side write uses Phase 22 `admin_tx` BEGIN IMMEDIATE
   inner (separate primitive at separate store's scope).
3. **Per-user `threading.RLock`** from §Decision §1 **retained
   unchanged.** `mindsos_server.mutex.UserMutexRegistry` substrate
   from §Decision §1 stays as the per-user mutex registry. Note:
   the per-user mutex's first consumer is Phase 25 cross-user read
   substrate (`read_other_local()` context manager per ADR-0008
   §am1); at Phase 24, the per-user mutex is declared but unused.
4. **Lock acquisition order in `release_update`:** RELEASE_SHIP_LOCK
   only. No per-user mutexes are acquired inside `release_update`
   (no cross-user state is touched per ADR-0118 §"Decision" §2).
   The original §Decision §2 ordering ("`with GLOBAL_PROMOTE_LOCK:
   with user_mutexes(sorted(authors)): ...`") is **vacuous in v1**
   because release-ship doesn't touch user state. The ordering
   contract holds for the future hypothetical case of release-ship
   needing to coordinate with per-user state (none at v1).

**Coordinated changes at Phase 24 ship:**

* `mindsos_server/locks.py` (NEW) — `RELEASE_SHIP_LOCK = threading.
  RLock()` module-level; `UserMutexRegistry` class (declared, no
  consumer at Phase 24).
* `mindsos_server/release.py::release_update` — acquires
  `RELEASE_SHIP_LOCK` at function entry; releases on exit (success or
  failure).
* `tests/phase_24/test_release_ship_lock.py` — asserts RLock
  serializes two concurrent `release_update` calls.

**Rationale for `threading.RLock` over SQLite advisory:** Phase 24
design log PB-12(a) considered SQLite BEGIN IMMEDIATE on a
`release_lock` row as the lock substrate (Phase 22 `admin_tx`
precedent). Rejected for the outer lock because the multi-role
FalkorDB-copy loop is the protected critical section, not the
SQLite write — threading primitive serializes the in-process
critical section directly. `admin_tx` is still used for the SQLite-
side write inside the threading lock (two primitives at two stores'
scope), matching shipped Phase 22 pattern.

**Phase 24 design log:** `halvim_mindsos/confirmation_docs/PHASE_24_
DESIGN_LOG.md` §1 Round 2 PB-12 (substrate lock) + §4 ADR delta.

### amendment-2 (Phase 25 ship — 2026-05-23) — `UserMutexRegistry` first consumer

**Trigger:** Phase 24 §amendment-1 retained the `UserMutexRegistry` declaration in `mindsos_server/locks.py` despite zero Phase 24 callsites — the per-user mutex contract holds even at zero-consumer state per the "honoured by absence" discipline. Phase 25 supplies the first live consumer: the `mindsos_server.orchestrator.read_other_local` ctx mgr acquires the target user's per-user `RLock` via `_mutex_registry.user_mutexes([target_user_id])` for the duration of the install + audit-write + yield + release sequence.

**Amended behavior:**

* **`mindsos_server.orchestrator._mutex_registry`** is the module-level `UserMutexRegistry` instance Phase 25 ships. The `read_other_local` ctx mgr enters `_mutex_registry.user_mutexes([target_user_id])` as the outer lock; the inner SQLite audit-write happens inside that mutex but commits via the `conn.commit()` after `write_audit` (PB-R7-02), not via `admin_tx` (cross-user-read is a read-then-audit path, not a multi-mutation transaction).

* **Acquisition order matches Phase 24's `RELEASE_SHIP_LOCK` + `admin_tx` pattern.** Per-user mutex acquired BEFORE any state mutation; released AFTER the ctx mgr yield body returns and `_release` decrements refcount. The deterministic lex-order acquisition guard in `user_mutexes` is exercised in Phase 25 only for the single-user case (admin reads one target at a time); the multi-user case ships with the future promotion orchestrator's `_acquire_installs_for_promotion(author_user_ids)` consumer.

* **v1 contention is unreachable in production.** The CLI per-command-process model means each `mindsos server admin read-local` invocation has its own short-lived registry; cross-process contention requires the v2 HTTP daemon. In-process nested `with` invocations (the refcount-bump test) exercise the RLock's re-entrant property: same-thread re-acquisition succeeds without deadlock.

**Coordinated changes at this amendment:**

* `mindsos_server/orchestrator.py` (NEW) — module-level `_mutex_registry = UserMutexRegistry()`; `read_other_local` ctx mgr acquires via `_mutex_registry.user_mutexes([target_user_id])`.
* `mindsos_server/orchestrator.py::reset_state_for_tests` — re-instantiates `_mutex_registry` per-test (PB-R6-03 — hygiene; accumulated lock entries are benign but the fresh instance avoids cross-test bleed).
* `tests/phase_25/test_read_other_local_refcount_bump_in_process.py` — exercises RLock re-entrance via nested `with` invocations.

**Out-of-scope:** The promotion orchestrator's multi-user `_acquire_installs_for_promotion` consumer defers to the first user-Local-write phase alongside the source-user-Local propose path.

**Phase 25 design log:** `halvim_mindsos/confirmation_docs/PHASE_25_DESIGN_LOG.md` §1 Round 1 PB-22 (per-user mutex outer + admin_tx inner) + §4 ADR delta.
