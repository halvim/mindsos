---
phase: 22
phase_title: "Server: admin ops"
layer: L0
status: design-locked
date_locked: 2026-05-22
branch: phase-22
tag_on_confirm: phase-22-confirmed
net_new: false   # extends Phase 18 mindsos_server/ pkg in-place; no new module; no schema bump
design_rounds: 5
total_picks: 27
prior_phase: 21
next_phase: 23
---

# Phase 22 Design Log — Server: admin ops

## §0. Scope summary

Phase 22 closes the long-deferred PB-B from Phase 20 §amendment-2:
ships `_assert_not_sole_admin(conn, target_user_id) -> None` helper
+ `LastAdminError(target_user_id)` exception class + wires all three
call sites ADR-0012 §Decision enumerates (`admin_demote_user`,
`admin_disable_user`, `hard_delete_user`).

Phase 22 ALSO ships the three additional admin-management verbs the
ADR did not explicitly enumerate but PHASE_MAP §22 row demanded:
`admin_promote_user`, `admin_enable_user`, `admin_kill_session`.

Plus a critical correctness fix surfaced at R4: `admin_tx(conn)`
context manager wrapping `BEGIN IMMEDIATE` to close the SQLite WAL
concurrent-admin race (two parallel admin verbs in separate
connections could each pass `_assert_not_sole_admin` against a stale
DEFERRED-isolation snapshot and both commit — leaving zero active
admins).

Five design rounds / 27 picks. Cross-user read (ADR-0008) was the
load-bearing scope-narrow at R1 PB-1 — the §Decision-mandated
mechanisms (`MindsOSServer._installed_locals` + `LocalPersister.load`
+ `KL.install_local_metagraph`) all ship at Phase 25, so Phase 22
cannot honor §Decision in any meaningful form; the verb shifts to
Phase 25 with its dependencies. ADR-0008 §amendment-1 documents the
phase shift; PHASE_MAP §22 row rewrites away the cross-user-read
Feature; PHASE_MAP §25 row absorbs the feature.

Code lives inside the Phase 18 `mindsos_server/` package — no new
top-level pkg, no 7-site checklist. No new module: extensions land
in `mindsos_server/admin.py` (per Phase 20 PB-Z module-home lock).
No schema bump: `_assert_not_sole_admin` is a single SELECT against
existing `users` columns; no new tables or indexes.

This phase **does NOT** ship: cross-user read (`read_other_local`) +
`InstallRecord` refcount-install model + `EVT_CROSS_USER_READ_INSTALL`
first-fire — all deferred to Phase 25 per R1 PB-1 + ADR-0008 §am1;
KL-side Local hard-delete (the user-row deletion + session CASCADE at
Phase 22 is L0-clean; Local Local-cleanup deferred to a KL phase);
two-step archive-then-delete precondition (`CAN_HARD_DELETE_ARCHIVED`
cap name is documentary debt per R2 PB-17); `--dry-run` flag (no
demand surfaced); HTTP-409 mapping for `LastAdminError` (no HTTP
transport roadmap per PHASE_MAP §1); retrofit of P20 reset-admin
through `admin_tx` (P20 has no `_assert_not_sole_admin` consumer; the
cross-process race wasn't surfaced then — flagged for future cleanup);
retrofit of P18 `user create/list/verify` through `_require_or_audit`
(pre-bootstrap-era verbs hold filesystem authority).

Two ADR amendments at this ship: ADR-0012 §amendment-3 (6-clause batch
batching all six locked picks per Phase 21 batching precedent — 9
clauses there, 6 here); ADR-0008 §amendment-1 (cross-user read
first-consumer phase shift P22→P25). ADR-0002 left untouched
(`CAN_HARD_DELETE_ARCHIVED` cap-name mismatch is documentary debt;
rename deferred per ADR-0002 §Consequences "renaming is a breaking
change"). ADR-0010 left untouched (Phase 22 is L0-only; no KL imports).

## §1. Round-by-round design ledger

Five rounds of pushbacks before lock. Picks per pushback + final
picks summary per `feedback_pushback_format_with_picks.md`. Phase
22's five rounds reflect the wider scope vs Phase 19-21 (three to
four rounds each); Phase 18's four rounds remain the high-water for
pick count (38), but Phase 22's 27 picks across 5 rounds is the
deeper of the recent ledgers.

### Round 1 — Architecture (PB-1..PB-11)

Pre-impl probe established: (a) Phase 21 squash `d90f752` at
`origin/main` tip + `phase-21-confirmed` resolves to the same SHA; (b)
`mindsos_server/admin.py` (P20+P21), `authz.py` (P21), `errors.py`
(through P21) all intact at expected shapes; (c) all six packages at
`+phase21`; (d) Phase 22 verbs absent except comment-stub references
in `errors.py:233`, `_schema.py:28+157+198`, `admin.py:10+98+114+208`,
`capabilities.py:49+52`, `sessions.py:19+188`; (e) `count_admins(conn)`
helper already exists at `users.py:359`; (f) FK `sessions.user_id
REFERENCES users(user_id) ON DELETE CASCADE` in P18 schema — gets
hard_delete sessions cleanup for free; (g) audit table has NO FK to
users (P18 _schema.py:96-104 lock) — audit rows outlive subjects; (h)
6 EVT_* constants needed at P22 all pre-declared at P18 (`EVT_ADMIN_PROMOTE_USER`,
`EVT_ADMIN_DEMOTE_USER`, `EVT_ADMIN_DISABLE_USER`, `EVT_ADMIN_ENABLE_USER`,
`EVT_HARD_DELETE_USER`, `EVT_CROSS_USER_READ_INSTALL` — last one defers to P25).

ADRs read at first probe: 0002 (+§am1), 0008, 0010, 0012 (+§am1+§am2),
0013 (+§am1+§am2). 0011 / 0041 / 0046 spot-checked via tangential
references; not load-bearing for R1.

**PB-1 — Cross-user read (ADR-0008) cannot honor §Decision at Phase 22.**
§Decision REQUIRES `MindsOSServer._installed_locals: dict[str, InstallRecord]`
+ `LocalPersister.load` + `KL.install_local_metagraph` /
`KL.extract_local_metagraph`. All three substrates first-ship at
Phase 25 per ADR-0011 §am1. **Pick: (b) narrow Phase 22 to admin
user mgmt only; cross-user read moves to Phase 25** alongside
`MindsOSServer` + `LocalPersister`. ADR-0008 §am1 documents the phase
shift; PHASE_MAP §22 row rewrites away the Feature; §25 row absorbs.
Precedent: Phase 19 PB-2 / PB-13 shifted `LocalPersister` +
`MindsOSServer` to Phase 25 for identical "dependency available at
later slot" reasoning.

**PB-2 — CLI verb grouping: flat vs `admin` subgroup?**
`NotAnAdminError` message (P20 ship) already references
`mindsos server admin promote-user` — implying the subgroup was the
intended shape. Adding 5+ destructive admin verbs flat under
`mindsos server` clutters the namespace. **Pick: (b) `mindsos server
admin <verb>` subgroup** for the six Phase 22 verbs (promote-user,
demote-user, disable-user, enable-user, kill-session,
hard-delete-user). P20 reset-admin + P21 query-audit stay flat (no
migration); future cleanup phase could optionally rehome them.

**PB-3 — `admin_promote_user` on already-admin: new error class, not
`NotAnAdminError` reuse.** `NotAnAdminError` semantic = "target is
NOT an admin" — that's the SUCCESS precondition for promote, not a
failure. **Pick: (b) NEW `AlreadyAnAdminError(target_user_id)`
exception class** — symmetric with `NotAnAdminError`. Idempotent
no-op rejected (masks accidental double-promotes); silent no-op
rejected per ADR-0013 §Decision happy-path-audit clause.

**PB-4 — `admin_demote_user` MUST kill target's sessions atomically.**
ADR-0002 §Rationale: "Session is immutable after issue; permissions
can't drift mid-request." A demoted admin with a live session keeps
ADMIN_CAPS until lazy expiry — the demote does nothing observable.
**Pick: (a) atomic DELETE sessions → UPDATE actor_role → audit
emission, single tx** (mirrors reset-admin PB-R atomicity from P20).
Per-row EVT_KILL_SESSION + summary EVT_ADMIN_DEMOTE_USER per the
R3 non-pushback ordering lock.

**PB-5 — `admin_promote_user` SILENT — no session kill.**
Promotion expands caps; existing sessions with USER_CAPS are safe.
**Pick: (a) silent promote** (no DELETE-sessions side effect) — caps
update on next login per ADR-0002 immutable-session principle.
Asymmetric with demote (PB-4) — but justified: demote is destructive
(cap shrink under stale session is dangerous); promote is additive
(cap expand delayed is safe).

**PB-6 — `admin_disable_user` MUST kill sessions atomically.**
Same argument as PB-4. **Pick: (a) atomic DELETE sessions + UPDATE
disabled + audit** mirrors reset-admin PB-R + PB-D pattern.

**PB-7 — `_assert_not_sole_admin` signature shape.** ADR-0012
§Decision names the helper without arguments; says "counts
`role='admin' AND disabled=0` rows". Existing `count_admins(conn)`
(users.py:359) already does this. **Pick: (a)
`_assert_not_sole_admin(conn, target_user_id) -> None`** — matches
ADR wording; internal impl uses single SELECT of active-admin
user_ids and checks `list == [target_user_id]` exactly (R3
non-pushback lock — atomic-in-tx, one query, most readable).

**PB-8 — Check-first ordering inside multi-step verbs.** All three
of demote/disable/hard-delete have a check phase (exists / role /
sole-admin / session). **Pick: (a) check FIRST in every multi-step
verb (fail-fast before any state change)**. Cost = one SELECT in
the fail path; benefit = no half-state.

**PB-9 — `admin_kill_session` arg shape: by `target_session_id` or
by `target_user_id`?** By-user_id overlaps reset-admin /
admin_disable_user side effects. **Pick: (a) by
`target_session_id`** — deliberate-target verb; "kill all of user
X's sessions" is already covered by disable / demote / reset-admin.

**PB-10 — `admin_enable_user` audit-emission policy.** Phase 20
PB-U conditional-emits `EVT_ADMIN_ENABLE_USER` (only when target was
disabled). **Pick: (a) thin verb; audit always per ADR-0013
§Decision** ("every privileged endpoint audits both its happy path
and its denial path"). Standalone verb invocation IS the privileged
endpoint event; whether the underlying UPDATE was a no-op is
recoverable from `extra.was_already_enabled`. P20's conditional was
inside reset-admin (a recovery verb), not a standalone management
verb.

**PB-11 — `hard_delete_user` audit ordering vs FK CASCADE.**
`sessions.user_id REFERENCES users(user_id) ON DELETE CASCADE` —
deleting a user row auto-deletes their sessions. **Pick: (a) audit
BEFORE state mutation: SELECT session_ids → emit N×
EVT_KILL_SESSION → emit 1× EVT_HARD_DELETE_USER → DELETE user row
→ commit, single tx**. Audit rows have NO FK to users (P18 schema
lock) so target_user_id strings survive the DELETE per ADR-0013
§Consequences "audit MUST outlive subjects."

### Round 2 — Mechanism + audit + behavior (PB-12..PB-18)

**PB-12 — Promote on disabled-user: leave-disabled vs auto-enable.**
**Pick: (c) leave `disabled` alone; promote-of-disabled converges to
"disabled admin"** — orthogonal verbs. Reset-admin's auto-enable
is justified because it's a recovery verb (target was locked out);
promote is a management verb where side effects make scripted use
less predictable.

**PB-13 — `admin_kill_session` order + missing-session error.**
**Pick: (a) SELECT user_id → raise `SessionNotFoundError` (NEW class)
on missing → DELETE → audit → commit**. New error class mirrors
UserNotFoundError density (P20 PB-O). Idempotent no-op rejected
(hides operator typos on session_ids).

**PB-14 — `EVT_KILL_SESSION.extra.context` vocabulary across four
callers.** **Pick: (a) verbatim verb names** — `"admin_kill_session"`,
`"admin_disable_user"`, `"admin_demote_user"`, `"hard_delete_user"`.
Grep-able + symmetric with P20's `"reset_admin"` context discriminator.

**PB-15 — `admin_disable_user` on already-disabled target.**
**Pick: (a) idempotent; audit always; `extra.was_already_disabled =
True` records the no-op marker**. Symmetric with PB-10 enable.
Plus: enable adds `extra.was_already_enabled: bool` for the same
reason (back-fills PB-10's payload shape).

**PB-16 — Audit `extra_json` payload shapes for six new EVT events.**
Locked once at design time to prevent per-PR drift. **Pick: (a) lock
six shapes inline**:
- `EVT_ADMIN_PROMOTE_USER.extra = {"prior_role": "user"}`
- `EVT_ADMIN_DEMOTE_USER.extra = {"prior_role": "admin", "sessions_killed": N}`
- `EVT_ADMIN_DISABLE_USER.extra = {"was_already_disabled": bool, "sessions_killed": N}`
- `EVT_ADMIN_ENABLE_USER.extra = {"was_already_enabled": bool}` (P22 shape; P20 conditional emission uses `{"context": "reset_admin"}` — distinct shapes coexist by key-presence)
- `EVT_HARD_DELETE_USER.extra = {"prior_role": str, "was_disabled": bool, "sessions_killed": N}`
- `EVT_KILL_SESSION.extra = {"session_id": sid, "context": <PB-14 string>}`

Denormalization principle inherited from P20 PB-BB.

**PB-17 — `hard_delete_user` precondition: archive-first required?**
`CAN_HARD_DELETE_ARCHIVED` cap name is misleading (no `archived`
column in schema; no `admin_archive_user` verb). **Pick: (a) no
precondition beyond `_assert_not_sole_admin` + existence + capability
gate**. Document the cap-name mismatch as documentary debt; defer
rename per ADR-0002 §Consequences "renaming is breaking."

**PB-18 — Self-targeting policy.** Can admin verbs target the calling
admin (self)? **Pick: (a) no special-case; rely on
`_assert_not_sole_admin` + natural mechanics; no
`SelfTargetError`**. ADR-0012 §Rationale: filesystem access IS the
authority floor; theatrical self-protection adds complexity for
marginal benefit; reset-admin via filesystem is the recovery floor.

### Round 3 — API surface + output + amendment posture (PB-19..PB-23)

**PB-19 — Return type for six verbs.** **Pick: (a) six per-verb
frozen dataclasses** — `PromoteUserResult`, `DemoteUserResult`,
`DisableUserResult`, `EnableUserResult`, `KillSessionResult`,
`HardDeleteUserResult`. Mirrors P20 `ResetAdminResult` precedent;
each result has verb-specific fields documenting what happened.

**PB-20 — `--json` support pattern.** **Pick: (a) all six verbs
support `--json`** with shape `{"verb": str, "target": str, ...,
"ts": ISO8601}`. Plain default: `key=value` one-liner. Operator
scripting parity with P21 query-audit.

**PB-21 — CLI exit-code policy.** **Pick: (a) bucketed by failure
family**: 4 = admin-policy (LastAdmin / AlreadyAnAdmin / NotAnAdmin
combined), 5 = not-found (User / Session combined). Revised at R5
PB-27 after probe revealed P20 used 2 for NotAnAdmin + UserNotFound
+ ValueError lumped — buckets would break P20 contract.

**PB-22 — ADR amendment scope at P22 ship.** **Pick: ADR-0012 §am3
+ ADR-0008 §am1; ADR-0002 design-log-note only**. Two amendments,
plus a non-amending note on the `CAN_HARD_DELETE_ARCHIVED` cap-name
mismatch (rename is breaking; defer to a dedicated rename ADR if
demand surfaces).

**PB-23 — `LastAdminError` constructor shape.** **Pick: (a)
`LastAdminError(target_user_id)` single-attr**. Mirrors P20
`NotAnAdminError` / P21 `PermissionDeniedError` density. The override
hint (per ADR-0012 §Consequences "names `reset-admin` as the official
override") lives in the message text, embedded inline; tests assert
on `"reset-admin" in str(exc)` substring.

### Round 4 — Correctness + symmetry locks (PB-24..PB-26)

**PB-24 — Concurrent-admin race (LOAD-BEARING miss).** SQLite WAL
+ Python sqlite3 `isolation_level="DEFERRED"` means each tx gets a
snapshot-at-tx-start view. Two parallel admin verbs in separate
connections could both pass `_assert_not_sole_admin` against stale
snapshots and both commit, leaving zero active admins. **Pick: (a)
`admin_tx(conn)` context manager wrapping `BEGIN IMMEDIATE`**.
RESERVED write-lock at tx-start; second verb blocks (up to
`busy_timeout=5000` ms set in `_db.open_db`) until first commits;
then second's snapshot reflects first commit; `_assert_not_sole_admin`
fires correctly.

R4 catch parallel to Phase 21 PB-16 (EVT_AUDIT_QUERY happy-path-audit
clause) — both surfaced load-bearing correctness fixes that rounds
1-3 missed.

Reset-admin (Phase 20) does NOT use this wrapper — flagged as a
known minor inconsistency for future cleanup (P20 had no
`_assert_not_sole_admin` consumer; cross-process race wasn't
surfaced).

**PB-25 — `NotAnAdminError` message rework verb-agnostic.** P20
wording embedded reset-admin's "use `admin_promote_user` to
escalate" hint; that's misleading for `admin_demote_user`'s failure
(where target-is-non-admin is the "already where you want them"
state). **Pick: (a) reuse class; rework message verb-agnostic**:
`f"user {target_user_id!r} has actor_role={actual_role!r}; admin
role required"`. CLI handlers inject verb-specific framing on
stderr; tests assert on `exc.target_user_id` / `exc.actual_role`
attrs (not full message text). P20 substring assertions on "alice"
+ "user" still pass.

**PB-26 — CLI: all six verbs REQUIRED-positional, no prompt
fallback, no `--force`/`--dry-run`.** **Pick: (a) P20 PB-G symmetry
verbatim**. Capability gate is the primary protection;
positional-REQUIRED is the secondary protection.

### Round 5 — Exit-code reconciliation (PB-27)

Probe at end of R4: P20 reset-admin's docstring documents exit code
**2** for `UserNotFoundError + NotAnAdminError + ValueError on bad
user_id` (lumped). R3 PB-21(a)'s bucket scheme (4=admin-policy
lumps NotAnAdminError) would silently retrofit P20's exit-2 to
exit-4 — breaking P20 contract for any operator script.

**PB-27 — Revise R3 PB-21: extend, don't retrofit.** **Pick: (a)
extend exit-code namespace; P20-era codes stay; net-new P22 error
classes get net-new codes**:
- 0 = success
- 1 = generic / not-logged-in
- 2 = ValueError + UserNotFoundError + NotAnAdminError (P20 baseline, untouched)
- 3 = PermissionDeniedError (P21)
- 4 = LastAdminError (NEW @ P22)
- 5 = AlreadyAnAdminError (NEW @ P22)
- 6 = SessionNotFoundError (NEW @ P22)

Backward compat preserved; each new exception class gets a distinct
code going forward. Future phases can extend with the next free code.

### Minor locks (no options needed)

- **`admin_tx` mechanism with Python sqlite3 DEFERRED isolation:**
  `_require_or_audit` on the HAPPY path does no DB writes; on
  entering `admin_tx`, the conn's auto-BEGIN hasn't fired (no DML
  yet under DEFERRED isolation), so `conn.execute("BEGIN IMMEDIATE")`
  succeeds. Subsequent DML inside the block runs under the explicit
  IMMEDIATE tx. `busy_timeout=5000` ms gives the second concurrent
  verb a 5-second grace before raising SQLITE_BUSY.
- **`_assert_not_sole_admin` query shape:** single SELECT
  `SELECT user_id FROM users WHERE actor_role='admin' AND
  disabled=0`; check `list == [target_user_id]` exactly. One query,
  atomic-in-tx, most readable.
- **Helper module placement:** `_assert_not_sole_admin` + `admin_tx`
  + six verb fns + six result dataclasses all live in
  `mindsos_server/admin.py` per Phase 20 PB-Z. `LastAdminError` +
  `AlreadyAnAdminError` + `SessionNotFoundError` live in
  `mindsos_server/errors.py` (matches all other exception class
  placements).
- **Audit-emission ordering inside multi-event verbs:** per-session
  `EVT_KILL_SESSION` rows emitted FIRST (in session_id order), then
  the summary `EVT_ADMIN_*_USER`. Reader sees "what happened, then
  the conclusion" in ASC `id` walk.
- **P18 `user create/list/verify` retrofit:** OUT of P22 scope.
  Pre-bootstrap-era verbs hold filesystem authority; session-gated
  alternatives are P22's six verbs. Document the dual model in §6
  below; treat retrofit as a future cleanup phase.
- **Test budget:** ~16 test files per the test-budget-unlimited
  feedback rule. Includes one critical concurrent-race regression
  test (`test_concurrent_demote_race.py`) using threading + on-disk
  DB. Per-row + summary audit shape verified in
  `test_audit_payload_shapes.py` (six EVT shapes) +
  `test_evt_kill_session_context_vocab.py` (four context strings).
- **Sandbox git separation** per
  `feedback_sandbox_vs_mac_git_separation.md`: no `git add/commit/
  push` from sandbox. All git ops happen on Mac (user runs them).

## §2. Final locks consolidated (27-pick reference)

| # | Pick | ADR cite / precedent |
|---|---|---|
| 1 | (b) narrow P22; cross-user read → P25 | ADR-0008 §am1 |
| 2 | (b) `mindsos server admin <verb>` subgroup | NotAnAdminError text implied (P20 ship) |
| 3 | (b) NEW `AlreadyAnAdminError(target_user_id)` | symmetric with NotAnAdminError |
| 4 | (a) demote atomic DELETE-sessions + UPDATE | ADR-0002 immutable-session; P20 PB-R |
| 5 | (a) promote SILENT (no session kill) | ADR-0002 immutable-session (safe direction) |
| 6 | (a) disable atomic DELETE-sessions + UPDATE | ADR-0002 immutable-session; P20 PB-R |
| 7 | (a) `_assert_not_sole_admin(conn, target_user_id)` reusing count_admins | ADR-0012 §Decision verbatim |
| 8 | (a) check-first ordering | fail-fast |
| 9 | (a) admin_kill_session by `target_session_id` | deliberate-target verb |
| 10 | (a) admin_enable_user audits always | ADR-0013 §Decision happy-path-audit clause |
| 11 | (a) hard_delete audit → DELETE user → CASCADE clears sessions | ADR-0013 §Consequences audit-outlives-subjects |
| 12 | (c) promote leaves disabled alone | orthogonal verbs; no side effects |
| 13 | (a) admin_kill_session SELECT→audit→DELETE; SessionNotFoundError | UserNotFoundError density precedent |
| 14 | (a) four EVT_KILL_SESSION.extra.context strings verbatim | grep-ability; P20 vocab precedent |
| 15 | (a) admin_disable_user idempotent + audit always; was_already_disabled | symmetric with PB-10 enable |
| 16 | (a) six EVT_*.extra_json shapes locked (denormalized) | P20 PB-BB denormalization principle |
| 17 | (a) hard_delete no archive-first precondition | cap-name documentary debt |
| 18 | (a) self-targeting allowed; no SelfTargetError | ADR-0012 §Rationale filesystem-floor |
| 19 | (a) six per-verb frozen result dataclasses | P20 ResetAdminResult precedent |
| 20 | (a) --json universal across six verbs; key=value plain default | P21 query-audit parity |
| 21 | (a) family-bucket exit codes (revised at PB-27) | superseded by PB-27 |
| 22 | ADR-0012 §am3 + ADR-0008 §am1; ADR-0002 design-log-note only | two amendments + doc note |
| 23 | (a) LastAdminError(target_user_id) single-attr; override hint in msg | P20 exception density |
| 24 | (a) admin_tx BEGIN IMMEDIATE wrapper closing WAL race | R4 load-bearing catch |
| 25 | (a) NotAnAdminError verb-agnostic message; CLI hint on stderr | one error class for reset-admin + demote |
| 26 | (a) all six verbs REQUIRED-positional no-prompt no-force | P20 PB-G symmetry |
| 27 | (a) extend exit-code namespace (P20 codes preserved; 4/5/6 new) | backward compat with P20 reset-admin scripts |

## §3. Cross-chat dependencies

### Backward (Phase 22 inherits)

- **Phase 18 audit substrate + 6 EVT_* constants** pre-declared at
  PB-34 (EVT_ADMIN_PROMOTE_USER / DEMOTE_USER / DISABLE_USER /
  ENABLE_USER / HARD_DELETE_USER + EVT_KILL_SESSION). All
  consumed at P22; none first-fired before P22 (EVT_KILL_SESSION
  first-fired P20 via reset-admin).
- **Phase 18 `Session` + capability roster** — ADR-0002's
  CAN_MANAGE_USERS / CAN_KILL_SESSION / CAN_HARD_DELETE_ARCHIVED
  all in ADMIN_CAPS only per §am1; P22 is the first consumer of all
  three.
- **Phase 18 `_schema.py` FK lock** — `sessions.user_id
  REFERENCES users(user_id) ON DELETE CASCADE` makes hard_delete's
  session cleanup automatic; `audit.actor_user`/`target_user` have
  NO FK so audit outlives subjects per ADR-0013 §Consequences.
- **Phase 18 `errors.py` density precedent** — 8 exception classes
  through P21; P22 adds 3 (LastAdminError, AlreadyAnAdminError,
  SessionNotFoundError); reuses UserNotFoundError + NotAnAdminError
  from P20.
- **Phase 19 `sessions.py`** — DELETE FROM sessions WHERE user_id=?
  pattern reused in demote/disable verbs; session_from_token
  (gating CLI session-resolution).
- **Phase 20 `mindsos_server/admin.py` module + PB-Z home + PB-R
  atomicity** — P22 verbs follow same `(conn, session, *, ...)`
  signature + same DELETE-then-UPDATE-then-audit ordering.
- **Phase 20 `count_admins(conn)`** at `users.py:359` — reused
  inside `_assert_not_sole_admin` (R3 non-pushback lock; single
  SELECT shape).
- **Phase 21 `_require_or_audit(conn, session, capability, *, verb)`**
  in `mindsos_server/authz.py` — P22 six verbs all gate through
  this wrapper. EVT_PERMISSION_DENIED + commit + raise on denial;
  silent on happy. Denial path's `extra = {"capability": <CAP>,
  "verb": <verb>}` per P21 PB-13.
- **Phase 21 `AuditRow` + `admin_query_audit`** — P22 audit rows
  visible through P21 reader; tests use the reader for cross-call
  audit-state verification.

### Forward (Phase 22 → later phases)

- **Phase 23 (snapshot rollback infrastructure)** — Phase 22
  doesn't directly feed; snapshot is L0 infra for Phase 24's
  release_update. The Phase 23 design chat decides whether the
  phase ships or retires to Phase 24 (Phase 23 row notes this
  flexibility).
- **Phase 25 (SessionProtocol + LocalPersister + MindsOSServer)** —
  ABSORBS cross-user read (ADR-0008 `read_other_local` +
  refcount-install model + `EVT_CROSS_USER_READ_INSTALL` first-fire)
  per ADR-0008 §am1. P25 row updated at P22 ship.
- **Phase 26 (Integration A)** — composes P22's admin verbs via the
  CLI; scenario step 4 (load fixture into Global) could trigger an
  admin verb downstream. Phase 26's scenario is regression-catching,
  not feature-adding; no P22-specific feature surfaces there.
- **Phase 38 (doc consolidation)** — `docs/usage/server/admin.md`
  deferred to P38 per established P18/P19/P20/P21 pattern. ADR-0012
  §am3 + ADR-0008 §am1 ship at this phase as the canonical
  references.

### Memory + feedback rules consumed

- `feedback_pushback_format_with_picks.md` — 27 picks across 5
  rounds, each with a pick + final picks summary per round.
- `feedback_pre_impl_probe_check_existing_modules.md` — probe
  confirmed Phase 22 surfaces absent except for comment stubs;
  Phase 20/21 surfaces intact at expected locations.
- `feedback_phase_baseline_literal_audit.md` — Phase 19 dynamic-
  baseline (`TestAll6PkgsAtCurrentPhase` against manifest version)
  handles `+phase21 → +phase22` automatically; `_SCHEMA_VERSION = 3`
  unchanged (no schema bump at P22).
- `feedback_l1_api_signature_probe_before_writing_tests.md` —
  probe verified `write_audit(conn, *, actor, event, target,
  extra)` shape; `Session.for_testing(user_id, is_admin=True)`
  shim usage; `count_admins(conn)` existing helper.
- `feedback_test_image_rebuild_after_source_change.md` — rebuild
  `mindsos-test` after admin.py + errors.py + server.py changes
  land before isolated phase_22 pytest.
- `feedback_smoke_harness_host_native.md` — host-native is
  canonical smoke harness; docker --rm has no `~/.mindsos/` mount.

## §4. ADR delta at Phase 22 ship

Two ADR amendments. ADR-0012 §am3 closes the PB-B deferral from
§am2 (Phase 20 ship) and documents the six-verb roster, `admin_tx`
race protection, `NotAnAdminError` message rework, and exit-code
namespace. ADR-0008 §am1 documents the cross-user-read first-consumer
phase shift P22→P25.

| ADR | Action | Reason |
|---|---|---|
| **0012** | §amendment-3 | Six-clause batch: (1) `_assert_not_sole_admin` ships with locked signature; (2) `LastAdminError(target_user_id)` ships with single-attr constructor + override-hint message; (3) six verb roster + capability gating + result dataclasses; (4) `admin_tx` BEGIN IMMEDIATE wrapper closes WAL concurrent-admin race; (5) `NotAnAdminError` message reworked verb-agnostic + verb-specific CLI framing; (6) CLI subgroup + exit-code namespace extension. Status: documentary — §Decision's three-invariant thesis preserved; what shifts is the mechanism. Phase 21 batching precedent (ADR-0013 §am2 nine clauses); P20 batching precedent (ADR-0012 §am2 six clauses). |
| **0008** | §amendment-1 | Phase-placement amendment: first consumer of `read_other_local(admin_session, target_user_id)` + `InstallRecord` refcount-install model shifts from P22 to P25 (where `MindsOSServer._installed_locals` + `LocalPersister.load` + `KL.install_local_metagraph` substrates first-ship). §Decision / §Rationale / §Consequences unchanged. Precedent: ADR-0011 §am1 + ADR-0042 §am1 — Phase 19 PB-2/PB-13 shifted LocalPersister + MindsOSServer to P25 for identical "dependency available at later slot" reasoning. |

ADR-0002 is **not** amended. The `CAN_HARD_DELETE_ARCHIVED` cap-name
mismatch (R2 PB-17) is documentary debt; renaming a capability string
is a breaking change per §Consequences. A dedicated rename ADR can
land in a future cleanup phase if operator demand surfaces.

ADR-0010 is **not** amended. Phase 22 is L0-only; no KL imports.

PHASE_MAP §22 row rewrite at ship per §1 row-rewrite rule — records
the cross-user-read deferral + the 27-pick contract.

PHASE_MAP §25 row update at ship — absorbs cross-user read from P22
+ documents ADR-0008 §am1 phase-shift.

## §5. Implementation references

```
mindsos_server/                         # extends Phase 18 pkg in-place; no new module
├── __init__.py                         # +19 exports: 6 verbs + 6 result dataclasses +
│                                       #  3 errors + _assert_not_sole_admin + admin_tx +
│                                       #  5 EVT_* constants
├── admin.py                            # MODIFIED: +admin_tx ctx mgr; +_assert_not_sole_admin;
│                                       #  +6 verb fns; +6 frozen result dataclasses
├── errors.py                           # MODIFIED: +LastAdminError + AlreadyAnAdminError +
│                                       #  SessionNotFoundError; NotAnAdminError msg rework
└── (all other Phase 18+19+20+21 files unchanged)

mindsos_cli/commands/server.py          # MODIFIED: +admin Typer subgroup with 6 verbs +
                                        #  _resolve_session helper + _admin_exit_for mapper

tests/phase_22/                         # ~16 test files
├── __init__.py
├── conftest.py                         # admin_session / non_admin_session / seeded_two_admins /
│                                       #  seeded_admin_target_with_sessions / seeded_user_with_sessions /
│                                       #  seeded_disabled_user / seeded_disabled_admin_extra
├── test_admin_promote_user.py          # happy path + AlreadyAnAdminError + UserNotFoundError +
│                                       #  disabled-target-stays-disabled + silent-no-session-kill
├── test_admin_demote_user.py           # happy + LastAdminError + NotAnAdminError verb-agnostic +
│                                       #  per-row EVT_KILL_SESSION context + summary audit
├── test_admin_disable_user.py          # happy + already-disabled idempotent + sole-admin check
├── test_admin_enable_user.py           # happy + already-enabled idempotent + no session kill
├── test_admin_kill_session.py          # happy + SessionNotFoundError + audit shape
├── test_hard_delete_user.py            # happy + sole-admin + CASCADE + audit-outlives-user
├── test_assert_not_sole_admin.py       # helper isolated; disabled-admin-doesn't-count
├── test_admin_tx.py                    # wrapper commit + rollback + in_transaction flag
├── test_concurrent_demote_race.py      # R4 PB-24 critical regression (threading + on-disk DB)
├── test_capability_denial.py           # parametrized over all 6 verbs
├── test_self_targeting.py              # PB-18 — demote/disable/kill-self allowed
├── test_no_schema_bump.py              # _SCHEMA_VERSION still 3; no new audit indexes
├── test_audit_payload_shapes.py        # PB-16 — six extra_json shapes locked
├── test_evt_kill_session_context_vocab.py  # PB-14 — four context strings
└── test_cli_admin_subgroup.py          # Typer wiring + exit-code mapping per PB-27

docs/usage/server/admin.md              # DEFERRED to Phase 38 doc-review per established pattern

# Version bump +phase21 → +phase22 across 9 sites / 11 lines:
mindsos_core/__init__.py
mindsos_knowledge/__init__.py
mindsos_admin/__init__.py
mindsos_instances/__init__.py
mindsos_cli/__init__.py
mindsos_server/__init__.py
pyproject.toml [project] version + description
mindsos_cli/manifest.toml [mindsos] phase + version
docker-compose.yml image tags (2 occurrences: mindsos / mindsos-test)
```

## §6. Scope boundaries (out-of-scope at Phase 22 ship)

- **Cross-user read (`read_other_local()` + `InstallRecord` refcount-
  install model)** — deferred to Phase 25 per R1 PB-1 + ADR-0008
  §am1.
- **KL-side Local hard-delete** — `hard_delete_user` at Phase 22
  deletes the user row + sessions only. Local cleanup is a KL
  concern; deferred to a future KL phase.
- **`admin_archive_user` two-step delete** — PB-17 rejected; cap
  name `CAN_HARD_DELETE_ARCHIVED` is documentary debt.
- **`--dry-run` flag for destructive verbs** — no operator demand
  surfaced; would be a useful add but not P22 scope.
- **HTTP transport / HTTP-409 mapping for LastAdminError** — no
  roadmap per PHASE_MAP §1 CLI-only product.
- **Retrofit of P20 `reset-admin` through `admin_tx`** — P20 has no
  `_assert_not_sole_admin` consumer; the cross-process race wasn't
  surfaced at P20. Known minor inconsistency; flagged for future
  cleanup.
- **Retrofit of P18 `user create/list/verify` through
  `_require_or_audit`** — pre-bootstrap-era verbs hold filesystem
  authority (file-system-or-bootstrap is the authority floor per
  ADR-0012 §Rationale); session-gated alternatives are Phase 22's
  six verbs. Document the dual model; treat retrofit as a future
  cleanup phase if/when operator demand surfaces.
- **Audit-row mutation / DELETE verbs** — audit is append-only per
  ADR-0013 §Consequences; `hard_delete_user` does NOT cascade to
  audit rows (FK absent per P18 _schema.py:96-104).
- **Cap rename `CAN_HARD_DELETE_ARCHIVED → CAN_HARD_DELETE_USER`** —
  ADR-0002 §Consequences locks capability strings as stable API
  surface; rename is breaking. Defer to a dedicated rename ADR.
- **`EVT_KILL_SESSIONS_FAILED` distinct constant** (Phase 19 §am1
  out-of-scope item also applies here) — Phase 22 verbs don't fail
  in a way that needs a new audit event.
- **Sole-admin protection on `admin_kill_session`** — not needed; an
  admin can kill any session (including their own) via this verb. If
  the killed session is the caller's, they're locked out of the
  current shell but the user row + other sessions persist.

## §7. Design saturation note

Five rounds (27 picks total: round 1 = 11, round 2 = 7, round 3 = 5,
round 4 = 3, round 5 = 1). Round 4's load-bearing miss
(concurrent-admin WAL race) parallels Phase 21 round 4's
EVT_AUDIT_QUERY happy-path-audit catch — both surfaced
correctness fixes that rounds 1-3 missed. Round 5's PB-27 revision
of R3 PB-21 (exit-code namespace) was triggered by a post-R4 probe
of P20 reset-admin's actual exit-code mapping; backward-compat
preserved at one-pick cost.

Phase 22 sits between Phase 21 (20 picks / 4 rounds) and Phase 18
(38 picks / 4 rounds) on density. 27 picks across 5 rounds reflects
the wider Phase 22 scope (six verbs + helper + class + Typer
subgroup + race protection + ADR amendment + exit-code namespace)
vs the narrower Phase 19-21 scopes (each adding 1-2 verbs).
Implementation proceeds per the task list. Any new pushback surfaced
during implementation is recorded as a B-22-T* hotfix in the
confirmation doc, not a retroactive PB-NN entry (Phase 18/19/20/21
precedent).
