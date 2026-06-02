# ADR-0013: Universal audit logging and `Session.for_testing()` shim

- **Status:** Accepted
- **Date:** 2026-04-22
- **Related:** ADR-0002, ADR-0009, ADR-0010, ADR-0012

## Context

Two orthogonal needs share one ADR because each is small and both shape how non-production concerns interact with the server:

1. **Audit.** Every security-relevant action must be recorded: logins (success, failure, concurrent-rejected), password changes, permission denials, admin user/session ops, cross-user reads, audit queries themselves, promotion outcomes (committed, rejected-stale, failed), session kills, hard deletes, reset-admin. Ops must be able to answer "what happened to user X in the last 24 hours" and "who ran which admin actions."
2. **Testing.** Virtually every unit and integration test needs a `Session`, but real sessions require SQLite writes, argon2 hashing, and a login call. That's orders of magnitude too much ceremony for "this KL method accepts a session."

## Decision

**Universal audit logging.** `mindsos_server/audit.py` defines a stable set of event constants (e.g., `EVT_LOGIN`, `EVT_LOGIN_FAILED`, `EVT_PERMISSION_DENIED`, `EVT_PROMOTION_COMMITTED`, `EVT_PROMOTION_REJECTED_STALE_REPORT`, `EVT_PROMOTION_FAILED`, `EVT_ADMIN_CREATE_USER`, `EVT_KILL_SESSION`, ...). Every privileged endpoint audits both its happy path and its denial path:

- Capability checks go through `_require_or_audit(session, CAP)` which writes `PERMISSION_DENIED` before raising `PermissionDeniedError`.
- Promotion writes `PROMOTION_REJECTED_STALE_REPORT` on freshness failure, `PROMOTION_FAILED` on flush rollback, `PROMOTION_COMMITTED` on success with `candidate_count`, `promotion_forced`, `report_id`, and the promoted node list in `extra_json`.
- Bootstrap and reset-admin audit with the OS user as actor (no session).
- The audit table schema: `id | ts | actor_user | event | target_user | extra_json`. `extra_json` is flexible; schema changes to it are backward-compatible.

Audits are written in the same SQLite transaction as the state change where feasible; promotion audits are best-effort after the mutation because the rollback path itself also audits.

Admins query audits via `admin_query_audit(session, *, actor=None, event=None, target=None, since=None, limit=...)`, gated on `CAN_VIEW_AUDIT_LOG`.

**Test shim: `Session.for_testing(user_id, *, is_admin=False)`.** Returns a `Session` whose capabilities are `ADMIN_CAPS` if `is_admin=True` else `USER_CAPS`, with a stable synthetic `session_id`. No SQLite, no argon2, no login. Tests that exercise full server flows use the real `login()`; tests that exercise KL/L3/L4 seams use `for_testing`.

## Rationale

- **Audit everything once, or you'll miss things.** Opt-in auditing gets forgotten; centralizing it in `_require_or_audit` and the orchestration paths guarantees coverage.
- **JSON extras, not columns.** The audit schema stays stable as new event types add new context; queries on `extra_json` keys are SQLite-native via `json_extract`.
- **Permission denials are audit events.** A failed capability check is a signal, not an exception to swallow.
- **Test shim in the server package, not a test utility.** Keeping `for_testing` as a classmethod on `Session` makes it obvious where to go; hiding it in a test fixture would tempt consumers to build their own, fragmenting the shape.
- **No KL coupling.** The shim lives in `mindsos_server.session`; KL still sees a normal `Session` via its `SessionProtocol` (ADR-0010).

## Consequences

- Every new admin endpoint must wire at least two audit events (denied + happy path) as part of its review checklist.
- Audit table growth is unbounded by design; operators should prune old rows per their retention policy. The developer guide documents the recommended schema and indexes.
- `Session.for_testing` is technically callable in production code. Convention: it's only for tests; review catches stray usage.
- Auditability of the `reset-admin` path relies on the OS user's uid — adequate for the local-first threat model; a hosted deployment that runs the CLI in a container would document how to make the actor meaningful.
- The test suite asserts exact audit events on every security-significant path (e.g., `test_promote_rejects_stale_report` checks for `PROMOTION_REJECTED_STALE_REPORT`; `test_promote_requires_can_promote` checks for `PERMISSION_DENIED`).

## Alternatives considered

1. **Log audit to stderr instead of SQLite.** Rejected — queryability is a first-class requirement; log-scraping is not a substitute.
2. **Per-event columns instead of `extra_json`.** Rejected — every new event type would require a migration.
3. **Real `Session` in tests, with a shared test-only admin seeded in a fixture.** Works, but every test that needed a session would pay the argon2 cost; `for_testing` is strictly cheaper with no loss of coverage (full-stack tests still run the real path).
4. **Structured logging library (e.g., structlog) as the audit back-end.** Overkill; `audit` is a single-writer single-schema table, not a streaming pipeline. A future exporter can tail it.

## Revisions

### amendment-1 (Phase 19 ship — 2026-05-21) — `users.verify()` no longer writes audit; callers own the audit event

**Trigger:** Phase 18 PB-13 shipped `users.verify(user_id, password) -> User` with the audit write (`EVT_LOGIN_FAILED` on failure) baked inside the function. Phase 19 ships ADR-0005's `kill_my_own_sessions(credentials)` escape valve, which also calls `verify()` to gate the deletion on fresh credentials. The Phase 18 audit-inside-verify shape produces a semantically wrong event in the recovery path:

* Caller of `kill_my_own_sessions` is trying to recover from a lost / wedged session, not to log in. Audit row would carry `EVT_LOGIN_FAILED` for what is actually a `kill_my_own_sessions` failure.
* §Decision says "Every privileged endpoint audits both its happy path and its denial path." `verify()` is no longer the endpoint at Phase 19+ — `login()` and `kill_my_own_sessions()` are. `verify()` becomes a pure predicate used by both.

**Amended behavior:**

* **`users.verify()` is a pure predicate at Phase 19+:** it raises `AuthFailedError(cause: AuthFailureCause)` on failure (PB-13 contract preserved) but does NOT write any audit row. Removes the `EVT_LOGIN_FAILED` write + the `write_audit` import from `users.py`.
* **`login()` writes `EVT_LOGIN_FAILED`** on `AuthFailedError` from verify(), in the same SQLite transaction as the failed-login state change (which is null — no row INSERT — but the audit row INSERT + commit is the state change). `extra_json` carries the private `cause` value so the differential is preserved for admin audit review.
* **`kill_my_own_sessions()` writes `EVT_LOGIN_FAILED`** on `AuthFailedError` from verify() as well, mirroring login's behavior (consistent with §Decision "permission denials are audit events"). Future amendment may introduce a distinct `EVT_KILL_SESSIONS_FAILED` constant if the differential becomes important; Phase 19 doesn't pre-ship that constant.
* **Phase 18 `tests/phase_18/test_users.py`** audit-write assertions that were asserting `verify()`-internal writes get moved to `tests/phase_19/` covering the new login()-writes-on-failure shape. Net test count balances (subtract from P18, add to P19).

**Rationale:** §Decision "Every privileged endpoint audits both its happy path and its denial path" is preserved — what shifted is who owns the audit write. The endpoint is the function on the public API surface (login, kill_my_own_sessions); `verify()` is internal plumbing both use. Internal plumbing emitting endpoint-named events crosses a layer that Phase 19 design review surfaced as a real semantic leak.

**Out-of-scope:** `EVT_KILL_SESSIONS_FAILED` distinct constant (potential Phase 22 introduction if audit-differential becomes important). `verify()` contract beyond audit removal — return type, exception type, parameters all stay at Phase 18 PB-13 shape.

See `halvim_mindsos/confirmation_docs/PHASE_19_DESIGN_LOG.md` §1 round 2 PB-9 for the rationale chain.

### amendment-2 (Phase 21 ship — 2026-05-22) — audit log reader: `admin_query_audit` signature locked + `_require_or_audit` first-construction + schema v3 + `EVT_AUDIT_QUERY` happy-path-audit honored + 9-change documentary batch

**Trigger:** Phase 21 design pass found that three documents disagreed on what the audit-reader verb actually is — ADR-0013 §Decision (`actor=None, event=None, target=None, since=None, limit=...`), PHASE_MAP §21 Features (`since/until/user/event`), and PHASE_21_NEXT_CHAT_PROMPT.md (six+ kwargs including `until`, `offset`, `extra_json_filter`, `--after-id` cursor). The contradictions had to be resolved before any architectural pushback could fire. Round 4 separately caught that §Decision's "Every privileged endpoint audits both its happy path and its denial path" clause hadn't been honored — the constant `EVT_AUDIT_QUERY` did not exist in `mindsos_server/audit.py` and rounds 1-3 would have shipped a verb that diverged from §Decision without recording it. Four design rounds / 20 picks batched into this single revision per Phase 19's batching precedent (ADR-0003/0004/0005/0011/0013 §am1) and Phase 20's six-change precedent (ADR-0012 §am2).

**Amended behavior (nine changes batched):**

1. **`admin_query_audit` signature locked (PB-1 + PB-8 + PB-10):** `admin_query_audit(conn: sqlite3.Connection, session: Session, *, actor: str | None = None, event: str | None = None, target: str | None = None, since: str | None = None, until: str | None = None, after_id: int | None = None, limit: int = 100, count_only: bool = False) -> list[AuditRow] | int`. Three changes against §Decision wording: (a) `conn` first positional per codebase convention (Phase 19/20 verbs all take `conn` first); (b) additive `until` kwarg for bounded time windows (single PHASE_MAP §21 carry-forward — handoff's superset `extra_json_filter` / `offset` rejected); (c) additive `after_id` cursor for stable monotonic-id pagination (`offset` rejected per its correctness issue under concurrent writes). `count_only` flag is the reframed "audit stats" feature from PHASE_MAP §21 (PB-4) — `SELECT COUNT(*)` form returns `int`.

2. **`actor` and `target` kept separate per §Decision (PB-2):** PHASE_MAP §21's collapsed `user` filter is ambiguous (actor-only? target-only? either?). §Decision wording verbatim wins; PHASE_MAP §21 row rewritten at Phase 21 ship to document the divergence. CLI exposes `--actor X` + `--target Y` flags. `actor=None` / `target=None` mean "no filter" (skip WHERE clause for that column) — does NOT match rows where the column itself is NULL.

3. **`_require_or_audit(conn, session, capability, *, verb: str) -> None` first-construction (PB-6 + PB-13):** New module `mindsos_server/authz.py` ships the capability-check wrapper per §Decision ("Capability checks go through `_require_or_audit(session, CAP)` which writes `PERMISSION_DENIED` before raising `PermissionDeniedError`"). Conn-first positional matches the codebase convention; additive `verb` kwarg (operator audit-review pattern "which verbs got denied for user X" — Phase 22's 5+ admin verbs will all route through this wrapper). `EVT_PERMISSION_DENIED.extra_json = {"capability": "<CAP>", "verb": "<verb>"}`. The audit row INSERT + commit is the state change on the denial path. Happy path returns silently — caller's verb-specific happy-path audit is the caller's responsibility. `PermissionDeniedError(target_user_id, capability)` lands in `mindsos_server/errors.py` (PB-14, mirroring Phase 20 `NotAnAdminError` density). Phase 21 is the first consumer; Phase 22 admin verbs are second+.

4. **Schema v2→v3 with `idx_audit_target` migration (PB-7 + PB-19):** PB-2's separate `target=` kwarg makes `WHERE target_user=?` a first-class query shape; no index existed before. `_SCHEMA_VERSION` bumps 2→3. The new index is added to BOTH `_DDL_AUDIT_INDEXES` (for fresh-install v0→v1 path) AND the v2→v3 migration block (for existing-v2 installs); duplication is intentional and drift-free because `CREATE INDEX IF NOT EXISTS` is idempotent. Mirrors Phase 19's sessions-table-in-both-paths pattern. Compound indexes deferred — single-column intersection ample for CLI-only product's bounded audit table.

5. **`AuditRow` frozen-dataclass return type (PB-9):** `AuditRow(id: int, ts: str, actor: str | None, event: str, target: str | None, extra: Mapping[str, Any])`. `extra_json` TEXT column parsed at read-time to `Mapping[str, Any]` so callers don't re-parse JSON. Frozen + immutable per Phase 18 `User` + Phase 20 `ResetAdminResult` precedent. Returns `list[AuditRow]` from the reader (in `id` ASC order per PB-12); returns `int` when `count_only=True`.

6. **`since` / `until` both inclusive (PB-11):** Half-open `[since, until)` rejected; both bounds use `>=` / `<=` SQL. CLI-tool operator-facing — "audits from May 1 to May 21" should include both endpoints. Millisecond-boundary edge case is not the realistic failure mode for an audit-review workflow. Lenient ISO-8601 parsing (PB-22): accept `2026-05-21T00:00:00Z` and `2026-05-21T00:00:00.000Z`; normalize internally to fixed-width ms+Z before SQL `ts >= ?` lexicographic compare. Reject date-only and Unix-timestamp forms at v1.

7. **`ORDER BY id ASC` default + `after_id` cursor (PB-12 + PB-20):** Chronological order pairs naturally with the `after_id` cursor (page forward in time). When both `since` and `after_id` are passed, SQL ANDs them: `WHERE ts >= ? AND ts <= ? AND id > ? ORDER BY id ASC LIMIT ?`. Operators wanting newest-first pass narrower `since=` or pipe through `tac`. Parallel `before_id` cursor + DESC default rejected (avoids shipping two cursor shapes).

8. **`EVT_AUDIT_QUERY` new constant; happy-path audit honored (PB-16 + PB-16i):** New audit-event constant in `mindsos_server/audit.py`: `EVT_AUDIT_QUERY = "EVT_AUDIT_QUERY"`. `admin_query_audit` writes one `EVT_AUDIT_QUERY` row before returning, per §Decision "Every privileged endpoint audits both its happy path and its denial path." `EVT_AUDIT_QUERY` rows are INCLUDED in default reader output (transparency — an attacker running `admin_query_audit` is visible in the log). Operators filter via `--event EVT_LOGIN` (or similar negative-filter pattern) if they want to ignore self-emitted query rows.

9. **`EVT_AUDIT_QUERY.extra_json` payload (PB-17 + PB-18):** Sparse filter snapshot + count + count_only marker: `{"filters": {non-null kwargs only}, "count": N, "count_only": bool}`. Null-valued filter kwargs omitted from the dict (sparse representation). `count_only=true` invocations write the SAME EVT_AUDIT_QUERY row with the flag set — consistent auditability; reviewers differentiate via the marker. Future-auditor can reconstruct the exact query that was issued from the snapshot.

**Rationale:** §Decision's capability-gated audit-reader thesis is preserved verbatim. What shifts are the *mechanism specifics* — signature shape to match the codebase's conn-first convention (PB-8), additive `until` + `after_id` for CLI-friendly bounded queries (PB-1 + PB-10), separate filter columns to remove PHASE_MAP §21's ambiguity (PB-2), schema-version bump for the new index (PB-7 + PB-19), frozen-dataclass return type matching Phase 18/20 precedent (PB-9), inclusive time bounds + ASC order for CLI ergonomics (PB-11 + PB-12), capability-denial wrapper module placement (PB-6), and the load-bearing addition of `EVT_AUDIT_QUERY` to honor §Decision's happy-path-audit clause (PB-16 + PB-16i + PB-17 + PB-18). All nine changes flow from the Phase 21 design review's principle: the reader implements §Decision verbatim, with mechanism specifics adjusted to the CLI-only product and the codebase's established conventions.

**Phase 21 narrowing:** Phase 21's Features list rewritten at PHASE_MAP §21 from the 2026-04-22 stub ("audit query (since/until/user/event); audit stats; capability-gated") to the actually-shipped signature: "audit query (`admin_query_audit(conn, session, *, actor=None, event=None, target=None, since=None, until=None, after_id=None, limit=100, count_only=False) -> list[AuditRow] | int`); CLI `mindsos server query-audit` flat verb with `--actor/--event/--target/--since/--until/--after-id/--limit/--count-only/--json` flags; gated on `CAN_VIEW_AUDIT_LOG` via new `_require_or_audit` wrapper in `mindsos_server/authz.py`; happy-path audit emission via new `EVT_AUDIT_QUERY` constant; schema v2→v3 with `idx_audit_target` migration." Tests row rewritten to reader-only seed-and-query pattern per PB-3 (audit-coverage retest of P18-20 deferred). PHASE_MAP §21 row amended at Phase 21 ship.

**Out-of-scope (deferred to later phases):** `extra_json` filtering via `json_extract` (deferred per PB-1(b); ADR-0013 §Decision names the mechanism but Phase 21 ships top-level column filters only); separate "audit stats" verb (PB-4 reframed to `--count-only`; real group-by-day / top-N stats deferred only if operator demand surfaces); compound indexes (PB-15; single-column intersection ample at CLI-product scale); cross-user audit-row filtering by capability (rejected — `CAN_VIEW_AUDIT_LOG` grants uniform access per §Decision); sweeper thread for old audit rows (no daemon to host one in CLI-only product; ADR-0003 §am1 sweeper-scope-to-HTTP-daemon precedent applies); audit-row mutation / DELETE verbs (audit is append-only; hard-delete-user does NOT cascade per Phase 18 _schema.py:96-104 lock); `AuditQuery` dataclass packing all filters (kwargs work fine at 7 filters; defer if set grows); HTTP transport / HTTP exception mapping for `PermissionDeniedError` (no roadmap — CLI-only per PHASE_MAP §1; CLI wraps to exit code 3).

See `halvim_mindsos/confirmation_docs/PHASE_21_DESIGN_LOG.md` §1 rounds 1-4 for the round-by-round rationale and §2 for the 20-pick consolidated reference table.

### amendment-3 (Phase 25 ship — 2026-05-23) — `EVT_HARD_DELETE_USER.extra_json` gains additive `local_dump_existed: bool` key

**Trigger:** Phase 25 PB-39 extends `mindsos_server.admin.hard_delete_user` with a `persister: LocalPersister | None = None` kwarg that calls `persister.delete(target_user_id)` on hard-delete. The delete return value (`bool` per ADR-0011 §amendment-2 clause 2) denormalizes into the audit row's `extra_json` so the audit reader can distinguish "user had a Local dump on disk at hard-delete time" from "user had nothing." Mirrors Phase 22 PB-16's additive-extra discipline.

**Amended behavior:**

* **Audit roster extends to 4 keys.** `EVT_HARD_DELETE_USER.extra_json` shape at Phase 25 ship: `{prior_role: str, was_disabled: bool, sessions_killed: int, local_dump_existed: bool}`. The fourth key is additive — pre-Phase-25 readers tolerating unknown keys (per ADR-0013 §"JSON extras") continue to work without modification.

* **Backward-compat semantics for `persister=None` callers.** A pre-Phase-25 caller invoking `hard_delete_user` without the new kwarg gets `local_dump_existed=False` in both the audit row and the `HardDeleteUserResult` return value. This is the v1 production observed behavior anyway — the CLI's `InMemoryLocalPersister` is fresh-per-invocation and never holds dumps; the bool is forward-shape for the first user-Local-write phase.

* **`HardDeleteUserResult` dataclass gains `local_dump_existed` as the 6th field** (PB-R7-01 from Round 7 pre-impl re-analysis — design log §5 sample omitted the existing `ts` field; the impl appends after `ts` to preserve Phase 22 positional order for any kwargs-less call sites).

**Coordinated changes at this amendment:**

* `mindsos_server/admin.py::hard_delete_user` — `persister` kwarg + `persister.delete` call + 4-key `extra_json` payload + 6-field `HardDeleteUserResult` return.
* `mindsos_server/admin.py::HardDeleteUserResult` — appends `local_dump_existed: bool` field.
* `mindsos_cli/commands/server.py::admin_hard_delete_user_cmd` — passes `persister=_resolve_persister()` + surfaces `local_dump_existed` in `--json` and human-readable output.
* `tests/phase_25/test_hard_delete_user_persister_delete_called.py` — 3 cases (persister had dump / persister empty / persister=None backward-compat).
* `tests/phase_25/test_evt_hard_delete_user_local_dump_existed.py` — audit row payload-shape assertion.

**Out-of-scope:** `EVT_HARD_DELETE_USER.extra_json` shape changes for source-user-Local content (e.g., `local_node_count`, `local_edge_count` for forensic reconstruction) defer to the user-Local-write phase. v1 only adds the one bool.

**Phase 25 design log:** `halvim_mindsos/confirmation_docs/PHASE_25_DESIGN_LOG.md` §1 Round 3 PB-39 (additive `local_dump_existed` key) + §4 ADR delta.
