# ADR-0011: `LocalPersister` protocol with session-scoped hydrate/flush

- **Status:** Accepted
- **Date:** 2026-04-22
- **Related:** ADR-0004, ADR-0007, ADR-0008

## Context

Per-user Local Metagraphs must be loaded from persistent storage at login and written back at logout. The reference storage is FalkorDB, but we also need an in-memory fake for tests, and future consumers may want alternative back-ends (file-backed for local-first workflows, remote service for a hosted deployment). KL itself has no business knowing which store is in use.

We also need a narrow enough interface that the promotion orchestrator (ADR-0007, ADR-0009) can reason about flush timing — failed saves must be detectable and must roll back cleanly.

## Decision

Introduce `mindsos_server.persistence.LocalPersister`, a `typing.Protocol`:

```python
class LocalPersister(Protocol):
    def load(self, user_id: str) -> MetagraphDump | None: ...
    def save(self, user_id: str, dump: MetagraphDump) -> None: ...
    def delete(self, user_id: str) -> None: ...
```

Ship two implementations:

- `InMemoryLocalPersister` — dict-backed; used in tests; supports a `fail_save_for: set[str]` hook that makes `save` raise for a given `user_id`, used to prove rollback correctness.
- `FalkorDBLocalPersister` — thin wrapper over the existing FalkorDB adapter; `delete` is best-effort (`delete_graph` with a query-fallback).

Session-scoped wiring:

- **On login**, the server calls `persister.load(user_id)` and hands the dump to KL via the install hook.
- **On logout**, the server extracts the Local via KL and calls `persister.save(user_id, dump)`. If `save` raises, the session stays alive, the Local is re-installed, and `FlushFailedError` bubbles to the caller.
- **On promote**, the server calls `persister.save` for each author's Local after `KL.promote` succeeds. Any `save` failure triggers the snapshot rollback (ADR-0007), audits `PROMOTION_FAILED`, and raises `FlushFailedError`.
- **On `hard_delete_user`**, the server calls `persister.delete(user_id)` after the `users` row is removed.

## Rationale

- **Protocol, not base class.** Callers get static type-checking without inheritance; downstream consumers can satisfy the contract without importing our class.
- **Three-method minimum.** Load, save, delete are the only IO verbs the server needs; keeping the surface small means alternative back-ends are easy to audit.
- **Failure as exceptions.** `save` raising on failure is strictly better than returning a boolean; exceptions propagate through the orchestrator's `finally` blocks without extra plumbing.
- **Test hook for fault injection.** The in-memory implementation's `fail_save_for` set is essential — it turns the rollback path from "hope it works" to "exercised in CI on every run."
- **`delete` in the protocol, not a side effect.** Hard-delete of a user must wipe the Local; having it in the protocol means no back-end can forget.

## Consequences

- `FalkorDBLocalPersister.delete` is best-effort because FalkorDB's `delete_graph` doesn't universally fail gracefully for missing graphs; the wrapper falls back to a `MATCH (n) DETACH DELETE n` query. Documented in the developer guide.
- The persister is configured once at `MindsOSServer` construction and held for the process lifetime. Swapping at runtime is not supported.
- `MetagraphDump` is the serialized form Core exposes for bulk load/save; its schema is stable enough that protocol implementations don't need to know KL internals.
- Future persisters (e.g., S3-backed for backup) can be added without touching the server.

## Alternatives considered

1. **Direct FalkorDB calls from the server.** Rejected — breaks testability and hard-codes a storage choice into the orchestrator.
2. **Two-phase commit across store + KL.** Rejected — KL is in-memory; the "rollback" we need is a snapshot restore (ADR-0007), not a distributed transaction.
3. **Event-sourced persistence (append-only log).** Interesting for a future scale regime; overkill for v1. The protocol doesn't preclude a future log-backed implementation.
4. **Fat protocol with batch ops, streaming, partial updates.** Rejected for v1 — add only when a concrete use case demands it.

## Revisions

### amendment-1 (Phase 19 ship — 2026-05-21) — `LocalPersister` + `MindsOSServer` first-consumer shifts from Phase 19 to Phase 25

**Trigger:** Phase 18 PB-18 deferred the `LocalPersister` Protocol + `MetagraphDump` surface from Phase 18 to Phase 19 on the assumption that Phase 19's `login()` would be the first real consumer (hydrate the user's Local from FalkorDB → hand to KL). Phase 19 round-1 pre-impl review (PB-2) found this premise stale:

* Phase 19 `login()` mints a token, writes a `sessions` row, and returns. It does NOT need to hydrate a Local — there is no caller at Phase 19 that consumes a hydrated Local.
* The KL `install_local_metagraph` hook (ADR-0042 §Decision) requires a `Session` argument, but the seam that wires login → KL hydration is `SessionProtocol` in KL (ADR-0040) plus the orchestrator that holds both — both of which ship at Phase 25 per PHASE_MAP §25.
* Shipping the Protocol + `InMemoryLocalPersister` + `FalkorDBLocalPersister` at Phase 19 with no live consumer means dead code that tests can exercise via fault-injection but no end-to-end caller can integrate.

In parallel, Phase 19 round-3 PB-13 audited the `MindsOSServer` orchestrator class first-construction:

* §Consequences names `MindsOSServer` ("The persister is configured once at `MindsOSServer` construction and held for the process lifetime.") as the natural lifecycle host for the persister.
* If the persister doesn't ship at Phase 19, the class has nothing to hold. Phase 19 ships `login` / `logout` / `session_from_token` / `kill_my_own_sessions` as **free functions** (matching the Phase 18 convention `insert_user` / `verify` / `_insert_first_admin`).
* The class first-construction therefore also shifts to Phase 25, where the persister it would hold also lands. At that phase the class wraps both halves: auth/sessions methods (calling into Phase 19's free functions) + persister-driven hydration on login + persister-driven flush on logout.

**Amended behavior:**

* **`LocalPersister` Protocol + `MetagraphDump`** first ship at Phase 25 (was: Phase 19). The §Decision Protocol shape and §Decision two-implementations roster (`InMemoryLocalPersister` + `FalkorDBLocalPersister`) are unchanged — only the ship-phase moves.
* **`MindsOSServer` orchestrator class** first-construction is at Phase 25 (was: implicit Phase 19 per §Consequences). The class consolidates Phase 19's free-function auth/sessions surface with the Phase 25 persister + ADR-0042 install/extract hooks under one lifecycle.
* **Phase 19 `login()` signature** is forward-compatible: free function with `conn`, `user_id`, `password`, `ttl`, `params` parameters; Phase 25 adds `persister` + `kl` as kwargs with defaults (so Phase 19 callers continue to work without modification) and wires the hydration step.

**Rationale:** Ship only what has a live consumer. Phase 18 PB-18 was a reasonable defer-by-one-phase guess; Phase 19's pre-impl probe found the real first-consumer is two more phases out. Premature Protocol surface + class lifecycle would be dead code with no end-to-end exercise path.

**Out-of-scope:** §Decision Protocol shape (load / save / delete) stays as designed. §Decision two-implementation roster stays as designed. Only the ship-phase moves.

See `halvim_mindsos/confirmation_docs/PHASE_19_DESIGN_LOG.md` §1 round 1 PB-2 + round 3 PB-13 for the rationale chain.

### amendment-2 (Phase 25 ship — 2026-05-23) — Protocol uses Metagraph at v1; InMemory ships; class + MetagraphDump + SQLite/Falkor + on-login/on-logout defer

**Trigger:** Phase 25 ships the cross-user-read substrate per §amendment-1. Multi-round re-litigation through 5 design rounds collapsed the original §Decision scope (3 method shapes + 2 impl roster + class lifecycle + on-login/on-logout) to the v1-shipping subset: only what has a live consumer (the `read_other_local` ctx mgr) lands at Phase 25; everything that has no v1 consumer defers.

**Amended decisions (5 clauses):**

1. **Protocol shape uses `Metagraph` directly at v1; `MetagraphDump` dataclass defers.** The §Decision Protocol method signatures change from `load(user_id) -> MetagraphDump | None` / `save(user_id, dump: MetagraphDump) -> None` to `load(user_id) -> Optional[Metagraph]` / `save(user_id, metagraph: Metagraph) -> None`. The `MetagraphDump` serialization shape decision defers to the first phase that ships a backing-store persister (SQLite or Falkor) — designing the dump format before there's a real persistence boundary to test against is speculative. The Phase 25 `InMemoryLocalPersister` stores live `Metagraph` references; future persisters can introduce `MetagraphDump` as a separate Protocol-shape revision at their consumer phase.

2. **`delete(user_id) -> bool` (was `-> None`).** Phase 25 PB-39 consumes the return-value: `EVT_HARD_DELETE_USER.extra_json[local_dump_existed]` denormalizes the bool so the audit reader can distinguish "user had a Local dump on disk" from "user had nothing." Idempotent semantics: a missing dump returns `False` without raising. `InMemoryLocalPersister.delete` is the v1 reference implementation.

3. **`InMemoryLocalPersister` ships at Phase 25 with `fail_save_for: set[str]` hook (PB-33); SQLite + Falkor defer.** The dict-backed in-memory implementation is the v1 sole impl. `SQLiteLocalPersister` and `FalkorDBLocalPersister` defer to the first phase that ships a user-Local-write surface — without writes, there's nothing to persist; the in-memory store is sufficient. The `fail_save_for` test-fault-injection hook exercises the future logout-flush + promotion-flush error path before its first live consumer exists.

4. **`MindsOSServer` class first-construction defers to the first user-Local-write phase.** Phase 25 PB-38 ships the orchestrator as free functions in `mindsos_server/orchestrator.py` with module-level `_installed_locals` + `_install_lock` + `_mutex_registry`. The class-vs-free-function choice is mechanically equivalent at v1 (single-process CLI); free functions match the Phase 18-22 codebase convention (`insert_user`, `verify`, `admin_promote_user`, etc.). The class first-construction lands at the user-Local-write phase alongside SQLite + Falkor persisters and on-login / on-logout hydration / flush hooks — the four things that justify the class lifecycle. Until then, persister + KL are passed per-call via kwargs (PB-40, Phase 22 `admin_tx(conn)` precedent).

5. **§"On login" + §"On logout" install/extract sequences defer to the first user-Local-write phase (PB-37).** The original §Decision wired login → `persister.load` → `KL.install_local_metagraph` and logout → `KL.extract_local_metagraph` → `persister.save`. Phase 25 collapses both: at v1 the CLI's caller never touches their own Local content (KL has no write API yet; lazy migration defers; no command writes to caller-Local), so login/logout's flush path has no consumer. Phase 19's free functions remain canonical unchanged; the persister + KL kwargs pattern is reserved for the cross-user-read code path only at v1.

**Module placement clarification:** `LocalPersister` Protocol lives at `mindsos_server/persistence/local_persister.py`; the `mindsos_server/persistence/` directory is a sub-package (NOT a top-level sibling package) per ADR-0010 §am1 — no new top-level package edge.

**Coordinated changes at this amendment:**

* `mindsos_server/persistence/__init__.py` + `mindsos_server/persistence/local_persister.py` (NEW) — Protocol + `InMemoryLocalPersister` impl.
* `mindsos_server/errors.py` — `FlushFailedError` extension class (declared but no v1 production caller — first consumer ships at user-Local-write phase).
* `tests/phase_25/test_local_persister_*.py` — 3 tests covering Protocol satisfaction, roundtrip, fault injection.

**Out-of-scope:** All four deferral clauses above. Phase 19 `login()` / `logout()` free-function signatures unchanged at Phase 25.

**Phase 25 design log:** `halvim_mindsos/confirmation_docs/PHASE_25_DESIGN_LOG.md` §1 Round 2 PB-25 (Metagraph at v1) + PB-37 (caller-Local collapse) + PB-38 (free functions) + PB-39 (delete bool) + PB-33 (fail_save hook) + §4 ADR delta + §5 implementation references.
