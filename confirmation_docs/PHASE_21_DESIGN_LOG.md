---
phase: 21
phase_title: "Server: audit log reader"
layer: L0
status: design-locked
date_locked: 2026-05-22
branch: phase-21
tag_on_confirm: phase-21-confirmed
net_new: false   # extends Phase 18 mindsos_server/ pkg; one new module mindsos_server/authz.py inside the pkg (no new top-level pkg = no 7-site checklist)
design_rounds: 4
total_picks: 20
prior_phase: 20
next_phase: 22
---

# Phase 21 Design Log — Server: audit log reader

## §0. Scope summary

Phase 21 ships the audit log reader half of ADR-0013 — the
counterpart to Phase 18's audit writer surface. ONE primary verb:

> `admin_query_audit(conn, session, *, actor=None, event=None,
> target=None, since=None, until=None, after_id=None,
> limit=100) -> list[AuditRow]`

plus CLI verb `mindsos server query-audit <flags>`, gated on
`CAN_VIEW_AUDIT_LOG` (in `ADMIN_CAPS` only per ADR-0002 §am1 strict
USER_CAPS lock).

Phase 21 also ships the **first general capability-enforcement
wrapper** `_require_or_audit(conn, session, capability, *, verb)`
in a NEW module `mindsos_server/authz.py` (PB-6) — the ADR-0013
§Decision-named pattern that all Phase 22+ admin verbs will reuse.

Five resolved contradictions across ADR-0013 / PHASE_MAP §21 /
PHASE_21_NEXT_CHAT_PROMPT.md drove rounds 1-2. Two ADR-0013
under-specifications and one ADR-0013 happy-path-audit clause
omission drove rounds 3-4. ADR-0013 §amendment-2 batches all of
the resulting documentary changes into one entry.

Code lives inside the Phase 18 `mindsos_server/` package — no new
top-level pkg, so the 7-site `feedback_new_top_level_package.md`
checklist does NOT apply. Phase 21 DOES add a new module
`mindsos_server/authz.py` (PB-6) — one sentinel-paths entry, one
`__init__.py` export, no Dockerfile change (existing
`COPY mindsos_server/` directory-copy picks up the new file).

This phase **does NOT** ship: separate "audit stats" verb (PB-4 —
reframed to `--count-only` flag on `admin_query_audit`); HTTP
transport (no roadmap; CLI-only per PHASE_MAP §1); promotion of
audit-coverage retest from prior phases (PB-3 — Phase 21 tests
read-only, not re-asserting P18-20 emission contracts); audit
retention/pruning (operator responsibility per ADR-0013
§Consequences); audit-row deletion / soft-delete (audit is
append-only); admin-reader for cross-user audit-row subset
filtering by capability (rejected — ADR-0013 grants
`CAN_VIEW_AUDIT_LOG` holders access to all rows uniformly).

One ADR amendment at this ship: ADR-0013 §amendment-2 batches nine
documentary changes (PB-1 + PB-2 + PB-7 + PB-8 + PB-10 + PB-11 +
PB-12 + PB-16 + PB-19) into a single revision entry per Phase 20's
six-change batching precedent. ADR-0002 left untouched (§am1
already locks `CAN_VIEW_AUDIT_LOG` in `ADMIN_CAPS` only at Phase
18; Phase 21 is the first consumer, no §Decision change). ADR-0010
left untouched (Phase 21 is L0-only; no KL imports).

## §1. Round-by-round design ledger

Four rounds of pushbacks before lock. Picks per pushback + final
picks summary per `feedback_pushback_format_with_picks.md`. Phase
20's four-round shape is the precedent; Phase 21 also ran four
because round 4 (PB-16..PB-19) surfaced a load-bearing miss —
ADR-0013's "every privileged endpoint audits its happy path"
clause hadn't been honored by rounds 1-3.

### Round 1 — Source-of-truth contradictions (PB-1..PB-5)

Pre-impl probe established: (a) Phase 20 squash `c6687ed` at
`origin/main` tip + `phase-20-confirmed` resolves to the same SHA
(via tag verification on Mac — sandbox SSH key blocked); (b)
`mindsos_server/admin.py` shipped with `reset_admin` + 19 EVT_*
constants in audit.py (no `EVT_AUDIT_QUERY` — caught at round 4);
(c) `CAN_VIEW_AUDIT_LOG` already in capabilities.py at Phase 18
(`ADMIN_CAPS` only; `USER_CAPS = frozenset()` per ADR-0002 §am1);
(d) Session has `for_testing(user_id, is_admin)` shim per ADR-0013;
(e) `_schema.py:120-122` ships 3 audit indexes (ts/event/actor) but
NO `idx_audit_target`; (f) `PermissionDeniedError` class does NOT
exist in errors.py — `_require_or_audit` wrapper does not exist in
mindsos_server/; (g) all 6 packages at `+phase20`; (h) no Phase
21-shaped surfaces shipped (`admin_query_audit` / `AuditQuery` /
`audit_reader.py` absent — only one comment reference at
`capabilities.py:55`).

ADRs read at first probe: 0002 (+§am1), 0010, 0012 (+§am1+§am2),
0013 (+§am1), 0046 (+§am1). 0001 spot-checked. 0011 + 0038-0042
not read in full (L2/KL-side; Phase 25's concern). Round 1 surfaced
that three documents disagree on what Phase 21 actually is — the
contradictions had to be resolved before any architectural pushback
could fire.

**PB-1 — Filter signature: three contradictory sources.**
ADR-0013 §Decision: `actor=None, event=None, target=None,
since=None, limit=...`. PHASE_MAP §21 Features: `since/until/user/
event` — adds `until`, collapses actor+target → `user`, drops
`limit`. PHASE_21_NEXT_CHAT_PROMPT.md: superset with `until`,
`offset`, `extra_json_filter`, `--after-id` cursor, `--extra
KEY=VALUE`. **Pick: (b) ADR + `until`** — single PHASE_MAP
carry-forward (bounded time window is the obvious use case); reject
PHASE_MAP's collapsed `user` filter (PB-2 below) and the
handoff's superset (defer extra_json filtering per PB-4 / "audit
stats" deferral). ADR-0013 §am2 records the additive `until`.

**PB-2 — `actor` vs `target` filter separation.** PHASE_MAP §21
collapses to a single `user` kwarg; ADR-0013 keeps `actor` and
`target` separate. Audit rows have both `actor_user` and
`target_user` columns. **Pick: (a) Separate `actor=` / `target=`
kwargs per ADR.** PHASE_MAP §21 row gets corrective rewrite at
ship (§1 row-rewrite rule). Diverges from PHASE_MAP wording by
design — the collapsed `user` filter is ambiguous (actor-only?
target-only? either?).

**PB-3 — PHASE_MAP §21 Tests criterion scope-creep.** "Every
login/logout/bootstrap emits an audit record" describes assertions
on Phases 18-20's emission contracts, not Phase 21's reader. Two
distinct test budgets being merged. **Pick: (a) Narrow Phase 21
to reader-only tests** (seed-and-query pattern). Emission-coverage
audit deferred to Phase 26 integration phase (or stays implicit in
the per-phase suites that already assert each verb's audit
emission). PHASE_MAP §21 Tests row rewritten at ship to match.

**PB-4 — "audit stats" undefined.** PHASE_MAP §21 Features lists
"audit stats" with no use case. **Pick: (a) Defer the stats verb
entirely; ship `--count-only` flag** on `admin_query_audit`
(`SELECT COUNT(*)` form). Covers the obvious "how many rows
match" use case at zero scope cost. PHASE_MAP §21 row rewrites
"audit stats" to "--count-only flag."

**PB-5 — Reader depends on Phase 20?** PHASE_MAP §21 row says
`Deps: 19`. Handoff prompt assumes reader consumes
EVT_RESET_ADMIN / EVT_KILL_SESSION / EVT_ADMIN_ENABLE_USER from
P20. Those rows are just data; reader is event-agnostic. PB-BB's
`sessions_killed` denormalization is a convenience for an unseen
"reset-admin summary" caller, not a hard dependency. **Pick: (a)
Keep Deps=19; reader event-agnostic; no `--summary EVT_RESET_ADMIN`
verb at v1.** PHASE_MAP §21 Deps row stays "19" at rewrite.

### Round 2 — Architecture (PB-6..PB-10)

User authorized round 2 after round 1's five locks. Picks below are
load-bearing architecture decisions: module placement, schema
versioning, function signature, return type, pagination.

**PB-6 — `_require_or_audit` + `PermissionDeniedError` placement.**
Probe: errors.py has 7 exception classes; `PermissionDeniedError`
absent. audit.py:17 + capabilities.py:55 + session.py:81 reference
the wrapper as "Phase 21+". Phase 21 is the first consumer per
ADR-0013 §Decision. **Pick: (a) Ship `_require_or_audit(conn,
session, capability, *, verb)` in NEW module `mindsos_server/
authz.py` + `PermissionDeniedError` in errors.py.** Pre-positions
for Phase 22's 5+ gated verbs (admin_promote/demote/disable/
enable_user, admin_kill_session, hard_delete_user — all need
the wrapper). PB-Z (Phase 20) precedent: new module for one
inhabitant when known multi-caller phase is next. Costs: one
sentinel-paths entry + one `__init__.py` export. No Dockerfile
change (existing `COPY mindsos_server/` picks up via directory
copy).

**PB-7 — `idx_audit_target` index + schema version bump.** PB-2(a)
locked `target=` as a first-class filter ⇒ `WHERE target_user=?`
needs an index. `_schema.py:120-122` ships only ts/event/actor
indexes. `_schema.py:215-225` runs `_DDL_AUDIT_INDEXES` ONLY in
the v0→v1 install block — additions don't reach existing v2
installs. **Pick: (a) Bump schema_version v2→v3 with
`idx_audit_target` migration.** Explicit, audited via
`init_or_migrate`'s version-bump logging, one new branch in init.
Matches Phase 18→19 v1→v2 precedent (sessions table). ADR-0013
§am2 records the bump. Deferred until Phase 21 design discovered
the missing index — phase 18 _schema.py comment "Phase 21 will
likely add more indexes as query patterns crystallize" was the
breadcrumb.

**PB-8 — Function signature shape.** ADR-0013 §Decision wording:
`admin_query_audit(session, *, actor=None, ...)` — no `conn`. But
reader needs `conn` to query SQLite. Phase 20 `reset_admin(conn,
user_id, ...)` puts conn first positionally; Phase 19
`login/logout/session_from_token/kill_my_own_sessions` all take
conn first. **Pick: (a) `admin_query_audit(conn, session, *,
actor=None, event=None, target=None, since=None, until=None,
after_id=None, limit=100) -> list[AuditRow]`** — mirrors Phase
20 reset_admin shape; conn explicit positional. Diverges from
ADR-0013 wording for codebase consistency; ADR-0013 §am2 documents
the conn-prefix addition.

**PB-9 — Return type.** Phase 18 `User` and Phase 20
`ResetAdminResult` are frozen dataclasses. Audit row has 6
columns. `extra_json` is TEXT in DB; caller almost always wants
parsed dict. **Pick: (a) `AuditRow(id, ts, actor, event, target,
extra)` frozen dataclass with `extra: Mapping[str, Any]`
(parsed).** Parsing JSON at read-time is cheap; ergonomics win is
real for both reader tests and Phase 22 admin verbs that consume
audit rows. Returns `list[AuditRow]`. ADR-0013 §am2 records the
return type.

**PB-10 — Pagination model.** Locked PB-1(b) kept `limit` in
signature; didn't lock offset. Audit table is append-only with
monotonic `id INTEGER PRIMARY KEY`. Cursor-based pagination is
index-friendly + stable under concurrent writes; `offset` has
correctness issues. **Pick: (b) `limit + after_id` cursor**
(`WHERE id > ?`). 4 LOC vs `--offset N`; future-proofs the
HTTP-daemon scenario where between-page writes are normal. ADR-0013
§am2 records `after_id` addition + the `since + after_id`
AND-together semantic (PB-22 below).

### Round 3 — Tail-end semantics (PB-11..PB-15)

User authorized round 3 after round 2. Picks below are
sensible-defaults but each has a real ambiguity worth a pick.

**PB-11 — `since/until` bound inclusivity.** Half-open `[since,
until)` vs closed `[since, until]`. **Pick: (b) Both inclusive
(`>=` / `<=`).** CLI tool, operator-facing — "audits from May 1
to May 21" should include both endpoints. Millisecond-boundary
edge case is essentially never the failure mode in practice.
ADR-0013 §am2 records the inclusive bounds.

**PB-12 — Default row ordering.** ASC (chronological) vs DESC
(newest first). **Pick: (a) `ORDER BY id ASC`** — pairs naturally
with PB-10(b) `after_id` cursor (page forward in time). Operators
wanting newest-first pass narrower `since=` or pipe through `tac`.
Avoids shipping a parallel `before_id` cursor shape. ADR-0013 §am2
records ASC default.

**PB-13 — `EVT_PERMISSION_DENIED.extra_json` payload.**
**Pick: (a) `{"capability": "CAN_VIEW_AUDIT_LOG", "verb":
"admin_query_audit"}`** — full provenance. Operator question
"which verbs got denied for user X" is a real audit-review
pattern (Phase 22 will have 5+ gated verbs all routing through
`_require_or_audit`). Capturing `verb` at write time costs nothing
+ saves a future ADR amendment.
`_require_or_audit(conn, session, capability, *, verb: str)` is
the locked wrapper signature.

**PB-14 — `PermissionDeniedError` constructor shape.**
**Pick: (a) `PermissionDeniedError(user_id, capability)`** —
matches `NotAnAdminError(target_user_id, actual_role)` density
from Phase 20 PB-N. No enumeration concern (caller has
filesystem-or-session authority). Attributes `target_user_id: str`,
`capability: str` mirror the audit-row payload from PB-13 so test
assertions can pair them.

**PB-15 — Compound index at v3.** Common audit query "EVT_LOGIN_FAILED
in last 24h" exercises both filters. **Pick: (a) v3 ships ONLY
`idx_audit_target`** — SQLite's planner intersects single-column
indexes for AND'd predicates. CLI-only product → bounded audit
table → single-column intersection ample. If it bites in
production, schema v4 adds a compound as a targeted migration.
Matches PHASE_MAP §1 "ship the obvious indexes; complicate later"
tone.

### Round 4 — Happy-path audit catch (PB-16..PB-19)

User authorized round 4 after round 3 closed. Round 4 caught a
load-bearing miss: ADR-0013 §Decision ("Every privileged endpoint
audits both its happy path and its denial path") had been honored
for the denial path (PB-13) but NOT for the happy path. The
constant `EVT_AUDIT_QUERY` did not exist in audit.py. Rounds 1-3
would have shipped a verb that diverged from ADR-0013 §Decision
without recording the divergence — a §Decision-level violation,
not §am-typical documentary work. Round 4 was justified.

**PB-16 — `admin_query_audit` MUST emit happy-path
`EVT_AUDIT_QUERY`.** ADR-0013 §Decision: "Every privileged endpoint
audits both its happy path and its denial path." Probe: audit.py
has 19 EVT_* constants; no `EVT_AUDIT_QUERY`. ADR-0013 §Context
names "audit queries themselves" among privileged actions to
record. **Pick: (a) Add `EVT_AUDIT_QUERY` constant in audit.py;
emit one row per `admin_query_audit` call before return.** ADR-0013
§am2 records the addition.

  **Sub-pick PB-16i — Default-filter `EVT_AUDIT_QUERY` rows out?**
  **Pick: (i) Include in default reader output.** Full transparency
  — an attacker running `admin_query_audit` is visible in the log.
  Filter trivial via `--event EVT_LOGIN` if operator wants to ignore.

**PB-17 — `EVT_AUDIT_QUERY.extra_json` payload.** **Pick: (a)
`{"filters": {actor, event, target, since, until, after_id,
limit}, "count": N, "count_only": bool}`** — full filters
snapshot + result count + count_only flag. All filter values
operator-supplied (no PII); full snapshot lets a future auditor
reconstruct exactly what was queried. Mirrors PB-BB's
denormalization principle from P20. Null-valued filter kwargs
omitted from the dict (not stored as `"actor": null` — sparse
representation).

**PB-18 — `--count-only` audit consistency.** With PB-16(a)
locked, does `--count-only` skip the audit write? **Pick: (a)
Emit identically with `extra.count_only=true` in payload (PB-17
covers this field).** Consistency + auditability. Operator using
`--count-only` as a "is there anything?" probe is still issuing a
privileged query. The `count_only` flag in extra_json lets
reviewers differentiate without losing the trail.

**PB-19 — `idx_audit_target` duplication risk after v3.** Fresh
installs get all 4 indexes via `_DDL_AUDIT_INDEXES` list at v0→v1;
existing-v2 installs get the new one via v2→v3 migration block.
Two lists, drift risk. **Pick: (a) Add `idx_audit_target` to
BOTH the `_DDL_AUDIT_INDEXES` list AND the v2→v3 migration block.**
Document the intentional duplication in a comment. Mirrors Phase
19's pattern (sessions DDL appears in both v0→v1 path for fresh
installs and v1→v2 migration block for existing). Refactor into
versioned index lists deferred to a future cleanup phase; not
piggybacking on Phase 21. ADR-0013 §am2 notes the intentional
duplication.

### Minor locks (no options needed)

Batched at the end of rounds 1-4; no plausible alternative survives
the picks above:

- **PB-20 — `since + after_id` AND-together semantic.** When both
  passed: `WHERE ts >= ? AND ts <= ? AND id > ? ORDER BY id ASC
  LIMIT ?`. Simple SQL; matches operator mental model ("audits
  after timestamp T, paginating via id cursor for stability"). No
  exclusivity gate.

- **PB-21 — Default `limit=100`.** Small enough to fit in a
  terminal; "show me recent N" default. Max effective limit
  10000 (CLI flag `--limit N`; SQL clamps to max via `min(limit,
  10000)`).

- **PB-22 — ISO-8601 parsing leniency.** Accept both `2026-05-21T00:00:00Z`
  and `2026-05-21T00:00:00.000Z`. Normalize internally to fixed-width
  ms+Z before SQL `ts >= ?` lexicographic compare. Reject
  date-only or Unix-timestamp forms at v1.

- **PB-23 — CLI verb flat: `mindsos server query-audit`.** Matches
  Phase 20 `reset-admin` flat-verb shape. Phase 22 may introduce
  an `admin` subgroup if its 5+ admin verbs warrant — not P21's
  concern. CLI flags: `--actor X`, `--event Y`, `--target Z`,
  `--since ISO`, `--until ISO`, `--after-id N`, `--limit N`,
  `--count-only`, `--json`.

- **PB-24 — Default `--json` shape.** Per-row mode:
  `{"rows": [{"id": int, "ts": str, "actor": str|null, "event":
  str, "target": str|null, "extra": {...}}, ...], "count": N,
  "next_after_id": int | null}`. `next_after_id` null when
  `len(rows) < limit` (last page sentinel). `--count-only` mode:
  `{"count": N}` (no `rows` / `next_after_id`).

- **PB-25 — Default plain output (no `--json`).** TSV one row per
  line: `id<TAB>ts<TAB>actor<TAB>event<TAB>target<TAB>extra_json_oneline`.
  No header row. `--count-only` plain: `count=N\n`. Null
  `actor`/`target` rendered as `-` (single dash).

- **PB-26 — `--after-id` CLI flag.** Matches kwarg name; explicit
  semantic. Not `--cursor` (cursor shape locked at id).

- **PB-27 — `actor=None` / `target=None` filter semantics.**
  Means "no filter on this column" — skip the WHERE clause for
  that column. Does NOT match audit rows where the column itself
  is NULL. Explicit `--actor-is-null` flag deferred (no current
  use case).

- **PB-28 — `_require_or_audit` happy path.** Returns silently
  (no return value); raises `PermissionDeniedError(user_id,
  capability)` on denial AFTER writing one
  `EVT_PERMISSION_DENIED` row in the same SQLite transaction. The
  audit row INSERT + commit is the state change on the denial
  path. Happy path writes no audit (the caller's verb-specific
  happy-path audit covers that).

- **PB-29 — Test image rebuild discipline:** per
  `feedback_test_image_rebuild_after_source_change.md`, rebuild
  `mindsos-test` after authz.py + admin.py + audit.py + _schema.py
  + errors.py + admin.py changes land. Linux tester runs the
  rebuild before `pytest tests/phase_21/`.

- **PB-30 — Sandbox git separation:** per
  `feedback_sandbox_vs_mac_git_separation.md`, no `git add/
  commit/push` from sandbox. All git ops happen on Mac (user runs
  them); sandbox is Write/Edit-only for the file artifacts.

## §2. Final locks consolidated (20-pick reference)

| # | Pick | ADR cite / precedent |
|---|---|---|
| 1 | ADR + `until` carry-forward (drops PHASE_MAP "user" + handoff's superset) | ADR-0013 §am2 (PHASE_MAP §21 rewrite) |
| 2 | Separate `actor=` / `target=` kwargs per ADR | ADR-0013 §Decision verbatim |
| 3 | Reader-only tests; emission-coverage deferred to P26 integration | PHASE_MAP §21 rewrite |
| 4 | Defer stats verb; `--count-only` flag on the reader | PHASE_MAP §21 rewrite ("audit stats" reframed) |
| 5 | Deps=19; reader event-agnostic; no reset-admin summary verb | PHASE_MAP §21 confirmed |
| 6 | new `mindsos_server/authz.py` + `_require_or_audit` + `PermissionDeniedError` in errors.py | ADR-0013 §Decision verbatim; PB-Z (Phase 20) precedent |
| 7 | Schema v2→v3 with `idx_audit_target` migration | ADR-0013 §am2 + _schema.py:117 breadcrumb |
| 8 | `(conn, session, *, ...)` signature shape | Phase 19/20 codebase precedent |
| 9 | `AuditRow(id, ts, actor, event, target, extra)` frozen with parsed extra | Phase 18 User + Phase 20 ResetAdminResult precedent |
| 10 | `limit + after_id` cursor pagination | ADR-0013 §am2 (additive after_id) |
| 11 | `since` / `until` both inclusive | ADR-0013 §am2 |
| 12 | `ORDER BY id ASC` default | ADR-0013 §am2; PB-10(b) cursor consistency |
| 13 | `EVT_PERMISSION_DENIED.extra={"capability", "verb"}` | ADR-0013 §am2 |
| 14 | `PermissionDeniedError(user_id, capability)` payload | Phase 20 PB-N density precedent |
| 15 | Only `idx_audit_target` at v3; no compound at this phase | PHASE_MAP §1 "ship obvious; complicate later" |
| 16 | Add `EVT_AUDIT_QUERY` constant; emit per call (happy-path audit) | ADR-0013 §Decision; §am2 |
| 16i | Include `EVT_AUDIT_QUERY` rows in default reader output (no exclusion flag) | ADR-0013 §Decision (audit-log transparency) |
| 17 | `EVT_AUDIT_QUERY.extra={"filters", "count", "count_only"}` (sparse filters) | ADR-0013 §am2; PB-BB denormalization principle |
| 18 | `--count-only` emits identical EVT_AUDIT_QUERY with `count_only=true` | ADR-0013 §am2 |
| 19 | `idx_audit_target` lives in BOTH `_DDL_AUDIT_INDEXES` AND v2→v3 block | Phase 19 sessions-table dup-list precedent |

## §3. Cross-chat dependencies

### Backward (Phase 21 inherits from earlier phases)

- **Phase 18 audit substrate.** `write_audit(conn, *, actor, event,
  target=None, extra=None)` signature (PB-34) — Phase 21 calls it
  for `EVT_PERMISSION_DENIED` (in `_require_or_audit`) and
  `EVT_AUDIT_QUERY` (in `admin_query_audit`). `_now_utc_iso()` ISO-8601
  with ms+Z format lock — Phase 21 parser normalizes to this form
  for SQL `ts >= ?` lexicographic compare. Audit table 6-column
  schema (id INTEGER PK / ts TEXT / actor_user TEXT / event TEXT /
  target_user TEXT / extra_json TEXT) — Phase 21's `AuditRow` mirrors.

- **Phase 18 capability roster.** `capabilities.py` ships seven
  capabilities including `CAN_VIEW_AUDIT_LOG` (in `ADMIN_CAPS`
  only; `USER_CAPS = frozenset()` per ADR-0002 §am1). Phase 21
  is the first consumer.

- **Phase 18 `Session` dataclass** (PB-33). `session.has(cap)`
  predicate + `for_testing(user_id, *, is_admin=False)` shim per
  ADR-0013. Phase 21's `_require_or_audit` calls `session.has(cap)`.
  Tests use `for_testing(is_admin=True)` to get a session with
  `CAN_VIEW_AUDIT_LOG`.

- **Phase 18 `_schema.py` framework.** `_SCHEMA_VERSION = 2`
  (Phase 19); `init_or_migrate(conn) -> int` idempotent migrator
  with per-version branches; `_DDL_AUDIT_INDEXES` list ships
  3 single-column indexes. Phase 21 adds the v2→v3 branch with
  `idx_audit_target` + `_write_version(conn, 3)`.

- **Phase 18 errors.py module.** 7 exception classes already
  shipped (`AuthFailureCause` enum + `AuthFailedError`,
  `UserAlreadyExistsError`, `InvalidSessionCause` enum +
  `InvalidSessionError`, `AlreadyLoggedInError`, `UserNotFoundError`,
  `NotAnAdminError`). Phase 21 adds `PermissionDeniedError` as the
  8th, following the same constructor pattern.

- **Phase 19 audit-event roster.** `EVT_LOGIN`, `EVT_LOGIN_FAILED`,
  `EVT_LOGIN_REJECTED_CONCURRENT`, `EVT_LOGOUT` shipped (P19 PB-13
  / §am1). Phase 21 reader tests query for these events.

- **Phase 20 audit-event roster shifts.** `EVT_KILL_SESSION` +
  `EVT_ADMIN_ENABLE_USER` first-fires shifted P22→P20 (PB-D + PB-U).
  `EVT_RESET_ADMIN.extra_json.sessions_killed` denormalization (PB-BB).
  Phase 21 reader can query for these events but does NOT special-
  case them; reader is event-agnostic per PB-5(a).

- **Phase 20 `admin.py` module.** Phase 21's `admin_query_audit`
  lives here (PB-Z module locked the home for admin verbs).
  Phase 20 `reset_admin(conn, user_id, ...)` is the signature
  precedent for `admin_query_audit(conn, session, *, ...)`.

- **`feedback_pushback_format_with_picks.md`** — every pushback
  ended with a pick (4 rounds × 20 total picks).

- **`feedback_phase_baseline_literal_audit.md`** — Phase 19 dynamic
  `TestAll6PkgsAtCurrentPhase` against manifest [mindsos] version
  handles the `+phase20 → +phase21` bump automatically. State
  literals: `_SCHEMA_VERSION = 3` (bumped at this phase) — grep
  ALL tests for `_SCHEMA_VERSION = 2` literal at Step 0 to confirm
  the bump propagates.

- **`feedback_pre_impl_probe_check_existing_modules.md`** — probe
  confirmed `admin_query_audit` / `_require_or_audit` /
  `PermissionDeniedError` / `EVT_AUDIT_QUERY` / `idx_audit_target`
  / `AuditRow` / `authz.py` not yet shipped. Pre-positions for
  Phase 22 are intentional, not duplicate (one consumer NOW).

- **`feedback_l1_api_signature_probe_before_writing_tests.md`** —
  probe checked `write_audit` kwarg shape (`actor=`, `event=`,
  `target=`, `extra=`), `session.has(cap)` predicate, `session.
  for_testing(user_id, is_admin=True)` classmethod. Phase 21
  tests model the same.

### Forward (Phase 21 → later phases)

- **Phase 22 (admin ops)** — second consumer of `_require_or_audit`.
  Five gated verbs (`admin_promote_user`, `admin_demote_user`,
  `admin_disable_user`, `admin_enable_user`, `admin_kill_session`,
  `hard_delete_user`) all use `_require_or_audit(conn, session,
  CAP, verb="…")` for the gate. Lands `_assert_not_sole_admin` +
  `LastAdminError` deferred from Phase 20 PB-B. Second-fire of
  `EVT_KILL_SESSION` (first-fired P20) via `admin_kill_session`.
  Phase 22 may introduce an `admin` CLI subgroup if its verbs
  warrant — Phase 21's flat `query-audit` doesn't preclude that.

- **Phase 25 (KL session seam)** — `Session.for_testing` is L2-
  visible per ADR-0013; the wrapper `_require_or_audit` stays in
  L0 (KL gates on `session.has(cap)` directly per ADR-0010 — no
  L2→L0 import). Phase 25's `MindsOSServer` orchestrator may
  wrap audit-reader access through a method, but the underlying
  free function stays the canonical surface.

- **Phase 33 (PROMOTED reader)** — design-symmetric with Phase 21:
  read-only verb gated on a capability, paginates via cursor.
  Phase 21's `_require_or_audit` + `AuditRow`-style frozen
  dataclass + `after_id` cursor pattern are all reusable templates.

- **Phase 38 (doc consolidation)** — `docs/usage/server/audit.md`
  deferred to Phase 38 doc-review per established Phase 18/19/20
  pattern. The ADR-0013 §am2 amendment ships at this phase as the
  user-facing reference; concrete how-to doc lands at P38.

## §4. ADR delta at Phase 21 ship

One ADR amendment. ADR-0013 already has §amendment-1 (Phase 19
ship — `verify()` no longer writes audit); Phase 21's
§amendment-2 batches nine documentary changes into one revision
entry per Phase 19 / Phase 20 batching precedent.

| ADR | Action | Reason |
|---|---|---|
| **0013** | §amendment-2 | Nine changes batched at Phase 21 ship: (a) `admin_query_audit` signature with `conn` first + `until` + `after_id` (PB-1 + PB-8 + PB-10); (b) `actor`/`target` kept separate; PHASE_MAP §21 row rewrite documents the divergence from "user" wording (PB-2); (c) `_require_or_audit(conn, session, capability, *, verb)` first-construction in `mindsos_server/authz.py` (PB-6); (d) schema v2→v3 with `idx_audit_target`; intentional duplication in `_DDL_AUDIT_INDEXES` (PB-7 + PB-19); (e) `AuditRow` frozen-dataclass return type with parsed `extra: Mapping` (PB-9); (f) `since` / `until` both inclusive (PB-11); (g) `ORDER BY id ASC` default with `after_id` cursor semantic (PB-12); (h) `EVT_PERMISSION_DENIED.extra` carries `{capability, verb}` (PB-13); (i) `EVT_AUDIT_QUERY` new constant; `admin_query_audit` writes one row per call per §Decision happy-path-audit clause; `EVT_AUDIT_QUERY.extra` carries `{filters (sparse), count, count_only}` (PB-16 + PB-16i + PB-17 + PB-18). Status: documentary — §Decision's "audit query verb gated on `CAN_VIEW_AUDIT_LOG`" thesis preserved; §Decision's "every privileged endpoint audits both happy + denial path" thesis HONORED by adding `EVT_AUDIT_QUERY` (clause was already in §Decision; Phase 21 first-fires it). Only signature/implementation specifics shift to match the codebase's conn-first convention + CLI-only product. |

ADR-0002 is **not** amended. `CAN_VIEW_AUDIT_LOG` already in
`ADMIN_CAPS` only per §am1 strict-USER_CAPS lock. Phase 21 first-
consumes it; no §Decision change.

ADR-0010 is **not** amended. Phase 21 is L0-only; no KL imports.
`mindsos_server/authz.py` lives in L0; KL stays on
`session.has(cap)` direct check per ADR-0010 §Decision.

PHASE_MAP §21 row rewrite at ship per §1 row-rewrite rule —
records the resolved contradictions (PB-1 / PB-2 / PB-3 / PB-4 /
PB-5) so future phase chats read the SHIPPED contract, not the
2026-04-22 design-spec stub.

## §5. Implementation references

```
mindsos_server/                         # extends Phase 18 pkg; PB-6 adds authz.py
├── __init__.py                         # +exports: admin_query_audit, AuditRow, _require_or_audit, PermissionDeniedError, EVT_AUDIT_QUERY
├── admin.py                            # MODIFIED: +admin_query_audit + AuditRow
├── audit.py                            # MODIFIED: +EVT_AUDIT_QUERY constant
├── authz.py                            # NEW (PB-6): _require_or_audit(conn, session, capability, *, verb)
├── errors.py                           # MODIFIED: +PermissionDeniedError(user_id, capability)
├── _schema.py                          # MODIFIED: _SCHEMA_VERSION 2→3; +idx_audit_target; +v2→v3 migration block (PB-7 + PB-19)
├── capabilities.py                     # UNCHANGED (CAN_VIEW_AUDIT_LOG already in ADMIN_CAPS)
├── session.py                          # UNCHANGED (has() + for_testing() already shipped)
├── sessions.py                         # UNCHANGED
├── users.py                            # UNCHANGED
└── (all other Phase 18+19+20 files unchanged)

mindsos_cli/commands/server.py          # MODIFIED: +query-audit Typer verb (positional flags-only; --json; --count-only)

tests/_shared/sentinel_paths.py         # +mindsos_server/authz.py runtime sentinel

tests/phase_21/                         # ~10 test files
├── conftest.py                         # seeded_audit_rows fixture (multi-actor / multi-event / multi-target / time-spanning)
├── test_admin_query_audit_happy_path.py     # admin session, default limit=100, ASC order, returns AuditRow list
├── test_admin_query_audit_capability_denial.py  # non-admin → PermissionDeniedError + EVT_PERMISSION_DENIED row + EVT_AUDIT_QUERY NOT written
├── test_admin_query_audit_filters.py        # actor/event/target filter combinations; null-valued kwargs skip WHERE
├── test_admin_query_audit_time_window.py    # since/until inclusive bounds; ms-boundary; lenient ISO-8601 parsing
├── test_admin_query_audit_cursor.py         # after_id cursor; since+after_id AND-together; next_after_id sentinel
├── test_admin_query_audit_count_only.py     # --count-only SQL form; EVT_AUDIT_QUERY.extra.count_only=true
├── test_admin_query_audit_cli.py            # CLI flag parsing; --json shape (rows + count + next_after_id); TSV default
├── test_admin_query_audit_audit_row_dataclass.py  # AuditRow frozen + extra parsed Mapping + equality
├── test_admin_query_audit_evt_query_emission.py   # EVT_AUDIT_QUERY emitted with filters snapshot per call
├── test_require_or_audit_wrapper.py         # denial: caps + audit write + raise; happy: no audit write, returns silently
└── test_schema_v3_migration.py              # idx_audit_target exists post-migrate; v2→v3 idempotent; v0→v1 list also contains target index

docs/usage/server/audit.md              # DEFERRED to Phase 38 doc-review per established pattern
                                        # (Phase 18 + Phase 19 + Phase 20 all deferred docs/usage/server/*)

# Modified outside mindsos_server/ + tests/:
mindsos_cli/commands/server.py          # +query-audit verb
tests/_shared/sentinel_paths.py         # +mindsos_server/authz.py runtime sentinel
docker-compose.yml                      # phase20→phase21 tag bump (3 image refs)
manifest.toml                           # phase = "21" + version = "0.0.0+phase21"
confirmation_docs/PHASE_MAP.md          # §21 row rewrite (5-pick resolution) + §22 unchanged
docs/decisions/adr/0013-…               # §am2 (9-change batch)

# Version bump +phase20 → +phase21 across 9 sites / 11 lines:
mindsos_core/__init__.py
mindsos_knowledge/__init__.py
mindsos_admin/__init__.py
mindsos_instances/__init__.py
mindsos_cli/__init__.py
mindsos_server/__init__.py
pyproject.toml [project] version
docker-compose.yml image tags (3 occurrences: mindsos / mindsos-test / ...)
manifest.toml [mindsos] version + [mindsos] phase

# Doctor self-test (6-pkg parity) unchanged — auto-detects new version literal via
# Phase 19 TestAll6PkgsAtCurrentPhase pattern (manifest.toml [mindsos] version
# as source-of-truth).
```

### `admin_query_audit` signature reference

```python
# mindsos_server/admin.py (additions)

from dataclasses import dataclass
from typing import Any, Mapping, Optional
import json
import sqlite3

from mindsos_server.audit import (
    EVT_AUDIT_QUERY, write_audit,
)
from mindsos_server.authz import _require_or_audit
from mindsos_server.capabilities import CAN_VIEW_AUDIT_LOG
from mindsos_server.session import Session


_MAX_LIMIT = 10_000


@dataclass(frozen=True)
class AuditRow:
    """
    A single row from the ``audit`` table, with ``extra_json``
    parsed to a Mapping.

    Phase 21 PB-9 lock. ``extra`` field is parsed at read-time;
    callers do not re-parse JSON. Frozen + immutable per Phase 18
    User / Phase 20 ResetAdminResult precedent.
    """

    id: int
    ts: str  # ISO-8601 with ms + Z (e.g. '2026-05-22T03:35:59.123Z')
    actor: Optional[str]  # actor_user column; may be NULL
    event: str  # one of mindsos_server.audit.ALL_AUDIT_EVENTS
    target: Optional[str]  # target_user column; may be NULL
    extra: Mapping[str, Any]  # parsed from extra_json TEXT


def admin_query_audit(
    conn: sqlite3.Connection,
    session: Session,
    *,
    actor: Optional[str] = None,
    event: Optional[str] = None,
    target: Optional[str] = None,
    since: Optional[str] = None,  # inclusive lower bound (PB-11)
    until: Optional[str] = None,  # inclusive upper bound (PB-11)
    after_id: Optional[int] = None,  # cursor (PB-10); WHERE id > ?
    limit: int = 100,  # PB-21
    count_only: bool = False,  # PB-4 reframe; PB-18 audit-row marker
) -> list[AuditRow] | int:
    """
    Read rows from the ``audit`` table per ADR-0013 §Decision +
    ADR-0013 §am2.

    Gated on ``CAN_VIEW_AUDIT_LOG`` via :func:`_require_or_audit`
    (PB-6) — emits :data:`EVT_PERMISSION_DENIED` audit row + raises
    :class:`PermissionDeniedError` on denial.

    Happy path emits one :data:`EVT_AUDIT_QUERY` row with filters
    snapshot + result count (PB-16 + PB-17), then returns the rows
    (or count if ``count_only=True``).

    ``since`` / ``until`` accept lenient ISO-8601 (with or without
    .sss / Z); both bounds inclusive (PB-11).

    ``after_id`` cursor + ``since`` AND-together per PB-20.

    Returns ``list[AuditRow]`` in ASC ``id`` order (PB-12).
    With ``count_only=True``, returns ``int``.
    """
    # 1. Cap gate (PB-6 + PB-13) — writes EVT_PERMISSION_DENIED + raises
    #    PermissionDeniedError on denial; commits the audit row.
    _require_or_audit(
        conn, session, CAN_VIEW_AUDIT_LOG, verb="admin_query_audit",
    )

    # 2. Build WHERE clauses + params from non-None filters (PB-27).
    where_clauses: list[str] = []
    params: list[Any] = []
    if actor is not None:
        where_clauses.append("actor_user = ?")
        params.append(actor)
    if event is not None:
        where_clauses.append("event = ?")
        params.append(event)
    if target is not None:
        where_clauses.append("target_user = ?")
        params.append(target)
    if since is not None:
        where_clauses.append("ts >= ?")
        params.append(_normalize_iso8601(since))
    if until is not None:
        where_clauses.append("ts <= ?")
        params.append(_normalize_iso8601(until))
    if after_id is not None:
        where_clauses.append("id > ?")
        params.append(after_id)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # 3. Execute the read query. ASC + LIMIT per PB-10 + PB-12 + PB-21.
    if count_only:
        sql = f"SELECT COUNT(*) FROM audit {where_sql}"
        result = conn.execute(sql, params).fetchone()
        count = int(result[0])
        rows_returned: list[AuditRow] | int = count
    else:
        effective_limit = min(limit, _MAX_LIMIT)
        sql = (
            f"SELECT id, ts, actor_user, event, target_user, extra_json "
            f"FROM audit {where_sql} ORDER BY id ASC LIMIT ?"
        )
        result = conn.execute(sql, params + [effective_limit]).fetchall()
        rows = [
            AuditRow(
                id=r[0], ts=r[1], actor=r[2], event=r[3], target=r[4],
                extra=json.loads(r[5]) if r[5] else {},
            )
            for r in result
        ]
        rows_returned = rows
        count = len(rows)

    # 4. Happy-path audit (PB-16 + PB-17): EVT_AUDIT_QUERY with sparse
    #    filters snapshot + count + count_only.
    filters_snapshot: dict[str, Any] = {}
    if actor is not None: filters_snapshot["actor"] = actor
    if event is not None: filters_snapshot["event"] = event
    if target is not None: filters_snapshot["target"] = target
    if since is not None: filters_snapshot["since"] = since
    if until is not None: filters_snapshot["until"] = until
    if after_id is not None: filters_snapshot["after_id"] = after_id
    filters_snapshot["limit"] = limit

    write_audit(
        conn,
        actor=session.user_id,
        event=EVT_AUDIT_QUERY,
        target=None,
        extra={
            "filters": filters_snapshot,
            "count": count,
            "count_only": count_only,
        },
    )
    conn.commit()

    return rows_returned


def _normalize_iso8601(ts: str) -> str:
    """Normalize a lenient ISO-8601 input to fixed-width ms+Z form for
    lexicographic SQL compare. Accepts ``2026-05-21T00:00:00Z`` and
    ``2026-05-21T00:00:00.000Z``. Raises ValueError on unparseable input."""
    from datetime import datetime, UTC
    # strict parse: require T separator + Z suffix
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        raise ValueError(f"timestamp must include timezone: {ts!r}")
    dt = dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"
```

### `_require_or_audit` + `PermissionDeniedError` reference

```python
# mindsos_server/authz.py (NEW)

"""
Capability-check wrapper with audit-on-denial.

Phase 21 PB-6 lock. ADR-0013 §Decision: "Capability checks go through
``_require_or_audit(session, CAP)`` which writes ``PERMISSION_DENIED``
before raising ``PermissionDeniedError``." Phase 21 first-construction;
Phase 22 second+ consumers (5+ admin verbs).

ADR-0013 §am2 documents the conn-first signature divergence from the
ADR's original wording (the codebase's conn-first convention wins;
all P19/P20 verbs take conn positionally).
"""

import sqlite3

from mindsos_server.audit import EVT_PERMISSION_DENIED, write_audit
from mindsos_server.errors import PermissionDeniedError
from mindsos_server.session import Session


def _require_or_audit(
    conn: sqlite3.Connection,
    session: Session,
    capability: str,
    *,
    verb: str,
) -> None:
    """
    Assert ``session`` has ``capability``. On denial, write one
    :data:`EVT_PERMISSION_DENIED` audit row (committed) and raise
    :class:`PermissionDeniedError`. Happy path returns silently
    (caller's verb-specific happy-path audit is the caller's
    responsibility).

    ``verb`` is the calling function name; recorded in audit
    extra_json per Phase 21 PB-13 (operator audit-review pattern
    "which verbs got denied for user X").

    Args:
        conn: SQLite connection.
        session: Caller's session.
        capability: Capability constant from
            :mod:`mindsos_server.capabilities`.
        verb: Calling function name (e.g. ``"admin_query_audit"``).

    Raises:
        PermissionDeniedError: If ``session.has(capability)`` is
            False. The audit row is written + committed BEFORE the
            raise.
    """
    if session.has(capability):
        return
    # Denial path: write audit + commit + raise.
    write_audit(
        conn,
        actor=session.user_id,
        event=EVT_PERMISSION_DENIED,
        target=None,
        extra={"capability": capability, "verb": verb},
    )
    conn.commit()
    raise PermissionDeniedError(session.user_id, capability)


# mindsos_server/errors.py (additions)

class PermissionDeniedError(Exception):
    """
    Raised by :func:`mindsos_server.authz._require_or_audit` when a
    session lacks the required capability. Phase 21 first-fires from
    ``admin_query_audit``; Phase 22 admin verbs are second+ consumers.

    Mirrors :class:`NotAnAdminError` density per Phase 20 PB-N — no
    enumeration concern (caller has filesystem-or-session authority).

    Phase 21 PB-14 lock.
    """

    def __init__(self, target_user_id: str, capability: str) -> None:
        super().__init__(
            f"user {target_user_id!r} lacks capability {capability!r}"
        )
        self.target_user_id = target_user_id
        self.capability = capability
```

### `_schema.py` v2→v3 migration reference

```python
# mindsos_server/_schema.py (modifications)

_SCHEMA_VERSION = 3  # bumped from 2 per PB-7

# _DDL_AUDIT_INDEXES — list ships at v0→v1 for fresh installs;
# PB-19 intentional duplication: idx_audit_target is ALSO added
# via the v2→v3 migration block below to reach existing-v2 installs.
_DDL_AUDIT_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit(ts)",
    "CREATE INDEX IF NOT EXISTS idx_audit_event ON audit(event)",
    "CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit(actor_user)",
    "CREATE INDEX IF NOT EXISTS idx_audit_target ON audit(target_user)",  # NEW @ v3 (PB-7)
]


def init_or_migrate(conn: sqlite3.Connection) -> int:
    # ... existing v0→v1 + v1→v2 branches unchanged ...

    # v2 → v3: ship the Phase 21 idx_audit_target index per PB-7.
    # NB: also present in _DDL_AUDIT_INDEXES above for fresh installs
    # (PB-19 intentional duplication — drift impossible because
    # CREATE INDEX IF NOT EXISTS is idempotent).
    if current < 3:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_target ON audit(target_user)"
        )
        _write_version(conn, 3)
        conn.commit()
        current = 3

    return current
```

### `EVT_AUDIT_QUERY` constant addition

```python
# mindsos_server/audit.py (one-line addition + ALL_AUDIT_EVENTS append)

EVT_AUDIT_QUERY = "EVT_AUDIT_QUERY"  # NEW @ Phase 21 PB-16

# ... ALL_AUDIT_EVENTS frozenset gets EVT_AUDIT_QUERY appended.
```

### CLI verb reference

```python
# mindsos_cli/commands/server.py (additions)

@server_app.command("query-audit")
def server_query_audit(
    actor: Optional[str] = typer.Option(None, "--actor"),
    event: Optional[str] = typer.Option(None, "--event"),
    target: Optional[str] = typer.Option(None, "--target"),
    since: Optional[str] = typer.Option(None, "--since", help="ISO-8601 UTC, inclusive"),
    until: Optional[str] = typer.Option(None, "--until", help="ISO-8601 UTC, inclusive"),
    after_id: Optional[int] = typer.Option(None, "--after-id"),
    limit: int = typer.Option(100, "--limit"),
    count_only: bool = typer.Option(False, "--count-only"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Read rows from the audit log (admin only)."""
    conn = _resolve_and_open()
    _ensure_migrated(conn)
    session = _resolve_session(conn)  # reads ~/.mindsos/token + session_from_token

    try:
        result = admin_query_audit(
            conn, session,
            actor=actor, event=event, target=target,
            since=since, until=until,
            after_id=after_id, limit=limit,
            count_only=count_only,
        )
    except PermissionDeniedError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=3)

    if count_only:
        if json_output:
            typer.echo(json.dumps({"count": result}))
        else:
            typer.echo(f"count={result}")
        return

    # result is list[AuditRow]
    if json_output:
        next_after_id = result[-1].id if len(result) >= limit else None
        typer.echo(json.dumps({
            "rows": [
                {"id": r.id, "ts": r.ts, "actor": r.actor, "event": r.event,
                 "target": r.target, "extra": dict(r.extra)}
                for r in result
            ],
            "count": len(result),
            "next_after_id": next_after_id,
        }))
    else:
        for r in result:
            actor_str = r.actor if r.actor is not None else "-"
            target_str = r.target if r.target is not None else "-"
            extra_oneline = json.dumps(dict(r.extra), separators=(",", ":"))
            typer.echo(
                f"{r.id}\t{r.ts}\t{actor_str}\t{r.event}\t{target_str}\t{extra_oneline}"
            )
```

## §6. Scope boundaries (out-of-scope at Phase 21 ship)

- **Separate "audit stats" verb** — Phase 21 PB-4 reframed to
  `--count-only` flag. Real "stats" (group-by-event-per-day, top-N
  actors, etc.) deferred to a future phase only if operator
  demand surfaces.
- **`extra_json` filtering via `json_extract`** — ADR-0013 §Decision
  names this as available but Phase 21 ships top-level column
  filters only. Defer per PB-1(b) (handoff superset rejected).
- **Cross-user audit row subset filtering by capability** — Phase 21
  grants `CAN_VIEW_AUDIT_LOG` holders access to all rows uniformly
  per ADR-0013. No "auditor can only see X user's rows" mode.
- **Audit retention / pruning** — operator responsibility per
  ADR-0013 §Consequences ("Audit table growth is unbounded by
  design").
- **Audit-row mutation** — audit table is append-only; no UPDATE
  or DELETE verbs at any phase. Hard-delete-user does NOT cascade
  to audit rows (FK absent per Phase 18 _schema.py:96-104 lock).
- **HTTP transport** — no roadmap; CLI-only product per Phase 18
  §6 + PHASE_MAP §1. `_require_or_audit` does not raise HTTP-shaped
  exceptions; the CLI wraps `PermissionDeniedError` → exit code 3.
- **Sweeper thread for old audit rows** — no daemon to host one
  in CLI-only product. Deferred per ADR-0003 §am1 pattern (sweeper
  scoped to future HTTP daemon phase).
- **Compound indexes** — only `idx_audit_target` at v3 per PB-15.
  SQLite planner intersects single-column indexes for AND'd
  predicates; bounded audit table size makes table scans
  tolerable; complicate later if benchmarks demand.
- **Audit-coverage retest of P18-20 emission contracts** — PB-3
  defers; per-phase suites already assert each verb's audit
  emission. Phase 26 integration phase (if it runs an
  emission-coverage matrix) is the natural home.
- **`audit_reader.py` separate module** — PB-6 placed
  `admin_query_audit` in admin.py (PB-Z lock from P20).
  Separate module would split read from write concerns but
  conflicts with the admin-verbs-cluster decision.
- **`AuditQuery` dataclass packing all filters** — kwargs work
  fine at 7 filters. Refactor to dataclass deferred to a future
  phase if filter set grows substantially.
- **Sole-admin protection for `_require_or_audit`** — irrelevant
  (the wrapper does not mutate user state).
- **`--exclude-event` flag for `EVT_AUDIT_QUERY` self-filtering** —
  PB-16i(i) rejected the exclusion. Operators can pass
  `--event EVT_LOGIN` (or similar) to filter manually.
- **Tag pinning of underlying audit table format** — schema_version
  alone is the API contract; the (id, ts, actor_user, event,
  target_user, extra_json) shape has been stable since v1 and is
  expected to remain so.

## §7. Design saturation note

Four rounds (20 picks total: round 1 = 5, round 2 = 5, round 3 = 5,
round 4 = 5). Round 4 was justified by a load-bearing miss —
ADR-0013's "every privileged endpoint audits its happy path"
clause hadn't been honored by rounds 1-3. Without round 4, Phase
21 would have shipped a §Decision-level divergence requiring a
disruptive §amendment after the fact. The catch arrived because
the design log §3 cross-chat ADR cite step found the §Decision
text in re-reading, not because pre-impl probe surfaced it (the
constant's absence wasn't enough on its own — the §Decision
contract had to be re-read).

Phase 21 sits between Phase 19 (15 picks / 3 rounds) and Phase 20
(13 picks / 4 rounds) on density. Higher pick count reflects
both the three-source contradiction surface at rounds 1-2 and
the ADR-0013 happy-path-audit catch at round 4 — neither of which
was visible from the PHASE_MAP §21 stub alone.

Implementation proceeds per the task list. Any new pushback
surfaced during implementation is recorded as a B-21-T* hotfix in
the confirmation doc, not a retroactive PB-NN entry (Phase 18/19/20
precedent).
