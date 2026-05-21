---
phase: 19
phase_title: "Server: sessions"
layer: L0
status: design-locked
date_locked: 2026-05-21
branch: phase-19
tag_on_confirm: phase-19-confirmed
net_new: false   # extends Phase 18 mindsos_server/ pkg; no new top-level pkg (no 7-site checklist)
design_rounds: 3
total_picks: 15
prior_phase: 18
next_phase: 20
---

# Phase 19 Design Log — Server: sessions

## §0. Scope summary

Phase 19 ships the sessions half of the L0 auth substrate per ADR-0003.
All code lives inside the Phase 18 `mindsos_server/` package — no new
top-level pkg, so the 7-site `feedback_new_top_level_package.md`
checklist does NOT apply. v2 SQLite migration adds the `sessions` table
+ index; new `mindsos_server/sessions.py` module ships `login`,
`logout`, `session_from_token`, and `kill_my_own_sessions` as **free
functions** (per round-3 PB-13 — `MindsOSServer` orchestrator class
deferred to Phase 25). CLI verbs `mindsos server {login,whoami,logout}`
land in the existing `mindsos_cli/commands/server.py`.

This phase **does NOT** ship: `MindsOSServer` orchestrator class
(Phase 25 per PB-13); `LocalPersister` Protocol + `MetagraphDump`
(Phase 25 per PB-2; supersedes Phase 18 PB-18 deferral); KL hydration
on login (Phase 25 — no consumer exists at Phase 19); `reset-admin` +
last-admin protection (Phase 20); audit query reader (Phase 21);
sweeper thread (deferred to future HTTP daemon phase per PB-4);
`source` field on `AlreadyLoggedInError` payload (deferred to HTTP
daemon era per PB-3).

Five ADR amendments at this ship (PB-1 / PB-2 / PB-3 / PB-4 / PB-7 /
PB-9 / PB-10 / PB-13 / PB-14 batch into 5 documentary-or-scope
amendments — see §4).

## §1. Round-by-round design ledger

Three rounds of pushbacks before lock. Picks per pushback + final picks
summary per `feedback_pushback_format_with_picks.md`. Phase 18's
four-round shape was the precedent; round 4 was self-flagged as
saturating on impl detail and skipped.

### Round 1 — Premise audit + ADR coherence (PB-1..PB-8)

Pre-impl probe established that (a) `mindsos_server/sessions.py` +
`mindsos_server/persistence.py` are both absent on `origin/main` tip
(`cf892b2` + handoff refresh `6de9cfe`), (b) Phase 18 surfaces intact
(`_SCHEMA_VERSION=1`, audit constants present including
`EVT_LOGIN_FAILED`, `class Session` slim per Phase 18 PB-33),
(c) all 6 packages at `+phase18`. Sandbox `git fetch` blocked by SSH
key — `phase-18-confirmed` tag verified at handoff by user on Mac.

Read ADRs 0001-0005, 0010-0013, 0040-0042 to ground each pushback.
The Round 1 thesis: several ADR premises are stale for the CLI-only
product as it ships; lock the amendments before any code.

**PB-1 — ADR-0005's "sessions die on server restart" is incoherent in
a CLI-only product.** ADR-0004/0005 lean on "in-memory Local state
from FalkorDB hydration is gone at restart" to justify wiping
sessions. CLI has no daemon, no in-memory Local that survives across
invocations. **Pick:** scope the wipe-on-restart rule to a future
HTTP daemon phase via ADR-0004 + ADR-0005 documentary amendments.
Sessions persist across CLI invocations; die on (a) lazy TTL expiry,
(b) `logout` / `kill_my_own_sessions` / `admin_kill_session`, or (c)
manual `server.db` deletion.

**PB-2 — `LocalPersister` Protocol "Phase 19 first consumer"
(Phase 18 PB-18) is premature.** Login at Phase 19 doesn't need to
hydrate a Local — it mints a token, writes a sessions row, returns.
KL hydration belongs to Phase 25 (SessionProtocol seam) where the
orchestrator + KL `install_local_metagraph` integration both exist.
**Pick:** defer the entire LocalPersister surface to Phase 25. ADR-0011
§am1 documentary records the shift.

**PB-3 — `AlreadyLoggedInError` `source` field has no meaning in
CLI-only.** ADR-0005 locks payload = `{existing_session_id, created_at,
source}`. In single-host CLI, "source" doesn't distinguish anything
useful (no remote IP, no client app). Hardcoding `"cli"` ships a
stub. **Pick:** ship 2-field payload `{existing_session_id,
created_at}`; defer `source` to HTTP daemon era. ADR-0005 §am1.

**PB-4 — ADR-0003 sweeper thread has no host in CLI-only.** A CLI
command's process lives for one verb-call; spawning a sweeper thread
inside each invocation reaps nothing meaningful. **Pick:** lazy-only
at Phase 19; ADR-0003 §am1 scopes the sweeper to the future daemon.
Expired rows accumulate harmlessly (size bounded by user count ×
24h ÷ avg-session-life — trivial for local-first).

**PB-5 — Token storage: handoff omits the env-var pattern.**
PHASE_MAP §19 Risks names `--token` argument vs `~/.mindsos/token`
file only. Industry convention (`gh`, `kubectl`, `docker login`) is
env-var first, file fallback. **Pick:** hybrid — file
`~/.mindsos/token` mode 0600 default; `MINDSOS_TOKEN` env override;
no `--token` flag. Mirrors Phase 18 PB-17 manifest-fallback pattern.

**PB-6 — Session field expansion (resolves Phase 18 PB-33 deferral).**
Phase 19 needs `created_at` / `last_seen_at` / TTL math.
**Pick:** keep `Session` dataclass bare (Phase 18 shape preserved);
timestamps live on the `sessions` row only; `login()` returns a
`LoginResult(session, token, created_at, expires_at)` named tuple
where callers can read the timestamps. SessionProtocol parity stays
trivial; KL never sees fields it doesn't need.

**PB-7 — ADR-0003 "constant-time comparison" misleading on
indexed SQLite SELECT.** Actual lookup is
`SELECT WHERE token_hash = ?` against an indexed column — not
constant-time, doesn't need to be (256-bit SHA-256 preimage
resistance dominates). **Pick:** drop the constant-time clause;
ADR-0003 §am1 records that indexed-equality is the mechanism and is
sufficient.

**PB-8 — Concurrent-login check MUST run after lazy expiry, not
before.** Edge case: existing session is 9 hours stale (sliding TTL
= 8h). New `login()` arrives. If concurrent-check fires first, it
raises `AlreadyLoggedInError` against a dead session; caller is
locked out. **Pick:** lock ordering = lazy-expire → concurrent-check
→ mint-new. Explicit in code + dedicated test.

### Round 2 — Implementation contracts (PB-9..PB-12)

**PB-9 — `users.verify()` already writes `EVT_LOGIN_FAILED`; it
will double-audit on `kill_my_own_sessions` failure.** Phase 18
baked the audit write inside `verify()`. ADR-0005's
`kill_my_own_sessions(credentials)` also calls `verify()` — but the
caller isn't trying to log in. **Pick:** move audit out of
`verify()`; callers (`login`, `kill_my_own_sessions`) write the
correct event themselves. verify() becomes a pure predicate.
Revises Phase 18 PB-13 contract (verify still raises
`AuthFailedError`; just no longer audits). ADR-0013 §am1
documentary.

**PB-10 — Store `expires_at` column or compute on read?**
expires_at = `min(created_at + 24h_abs, last_seen_at + 8h_sliding)`
is a pure function of two source columns. Storing it invites drift.
**Pick:** don't store; compute lazily at lookup. ADR-0004 §am1
records the schema simplification. Final `sessions` shape: 5
columns `(session_id, user_id, token_hash, created_at,
last_seen_at)`.

**PB-11 — `logout` by token or by session_id?** Caller has the token;
they don't naturally have their session_id. **Pick:**
`logout(token)` — server SHA-256s, deletes matching row, audits
`EVT_LOGOUT` with the deleted row's session_id in extra_json. Admin
path (Phase 22 `admin_kill_session`) stays by-session_id — asymmetry
is correct because admin doesn't possess the target's token.

**PB-12 — Test-only fast TTL — without it the test suite hangs.**
Sliding 8h + absolute 24h. **Pick:** `SessionTTL(sliding_seconds,
absolute_seconds)` dataclass; `PRODUCTION_TTL` =
`SessionTTL(sliding_seconds=8*3600, absolute_seconds=24*3600)`;
`_TEST_FAST_TTL` = `SessionTTL(sliding_seconds=1, absolute_seconds=2)`.
Mirrors Phase 18 PB-14 `_TEST_FAST_PARAMS` for argon2.

### Round 3 — Architecture commits (PB-13..PB-15)

**PB-13 — Free functions vs `MindsOSServer` orchestrator class.**
ADR-0011 §Consequences names `MindsOSServer` but PB-2 deferred
LocalPersister (the original reason for the class) to Phase 25.
Phase 18 ships free functions. **Pick:** continue free functions
at Phase 19. `login`, `logout`, `session_from_token`,
`kill_my_own_sessions` all take `conn` + explicit `ttl=` + explicit
`params=` kwargs. Class deferred to Phase 25 where both halves of
the orchestrator (auth/sessions + persister + KL) arrive together.
ADR-0011 §am1 (documentary) records the Phase 25 first-construction
shift.

**PB-14 — `SessionExpiredError` vs uniform `InvalidSessionError`.**
ADR-0003 §Decision names `SessionExpiredError` specifically. Phase
18 PB-23 set the project pattern: single opaque exception + private
cause enum (`AuthFailedError`). Different failure modes on
`session_from_token` (expired-sliding, expired-absolute,
never-existed) have the same threat-model property — the
differential leaks no useful information to a 256-bit-random
guesser. **Pick:** `InvalidSessionError(cause: InvalidSessionCause)`
mirroring Phase 18 PB-23. Cause enum =
`{EXPIRED_SLIDING, EXPIRED_ABSOLUTE, NOT_FOUND}`. Public message
uniform ("invalid session"). ADR-0003 §am1 records the unification.

**PB-15 — `SessionTTL` injection point.** PB-12 picked the
dataclass; PB-13 picked free functions. **Pick:** explicit kwarg on
every call site — `login(conn, ..., *, ttl=PRODUCTION_TTL)`,
`session_from_token(conn, token, *, ttl=PRODUCTION_TTL)`,
`kill_my_own_sessions(conn, ..., *, ttl=PRODUCTION_TTL)`. Mirrors
Phase 18 PB-14 `Argon2Params` injection convention. No module-level
global (anti-PB-14 precedent).

### Minor locks (no options needed; user can flag if disagrees)

These were batched at the end of Round 2 + Round 3 and are recorded
here for completeness — they did not require option-with-pick form
because no plausible alternative survives the locks above:

- **`session_id` generation:** `secrets.token_urlsafe(16)` — 128-bit
  opaque random. Separate primitive from the 256-bit token. Admins
  copy session_ids from audit rows; ids never derivable from token.
- **`sessions` schema final:**
  ```sql
  CREATE TABLE IF NOT EXISTS sessions (
      session_id    TEXT PRIMARY KEY,
      user_id       TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
      token_hash    TEXT NOT NULL UNIQUE,
      created_at    TEXT NOT NULL,
      last_seen_at  TEXT NOT NULL
  )
  ```
  PRAGMA `foreign_keys=ON` (already set per Phase 18 PB-19) makes
  the CASCADE active for Phase 22 `hard_delete_user`. Plus index
  `CREATE INDEX idx_sessions_user_id ON sessions(user_id)` for the
  concurrent-login lookup hot path.
- **`logout` with invalid/expired/missing token:** silent no-op,
  exit 0. No `EVT_LOGOUT_FAILED` constant. Rationale: logout is
  idempotent by nature; no security signal worth auditing.
- **`whoami` exit code shape:**
  - logged-in → exit 0 + identity + computed expires_at
  - not-logged-in → exit 1 + stderr "not logged in"
  - `--json` mode always exits 0 + structured payload (pipe-friendly):
    `{"logged_in": false}` OR `{"logged_in": true, "user_id": "...",
    "actor_role": "...", "capabilities": [...], "session_id": "...",
    "created_at": "...", "last_seen_at": "...", "expires_at": "..."}`.
- **Audit + state-change in one transaction:** `login` = single
  transaction (sessions INSERT + audit INSERT + commit). Per ADR-0013
  §Decision ("Audits are written in the same SQLite transaction as
  the state change where feasible").
- **`session_from_token` write semantics:** UPDATE `last_seen_at`
  on every successful lookup (sliding refresh). Under WAL the cost
  is negligible for a local-first tool. Lazy-expired rows are
  DELETEd at the same lookup before the InvalidSessionError raises.
- **Token hash function:** `hashlib.sha256(token.encode("ascii")).hexdigest()`
  — 64-char hex stored in `sessions.token_hash`. Per ADR-0003 verbatim.
- **CLI login token output:** default writes to `~/.mindsos/token`
  mode 0600 + prints confirmation to stderr; `--print-token` flag
  emits to stdout for shell capture; `--json` includes token in the
  payload.

## §2. Final locks consolidated (15-pick reference)

| # | Pick | ADR cite |
|---|---|---|
| 1 | "Sessions die on restart" scoped to future HTTP daemon; CLI sessions persist | ADR-0004 §am1 + ADR-0005 §am1 |
| 2 | `LocalPersister` + `MetagraphDump` deferred to Phase 25 | ADR-0011 §am1 |
| 3 | `AlreadyLoggedInError` 2-field payload; `source` deferred | ADR-0005 §am1 |
| 4 | Sweeper thread deferred to daemon phase; lazy-only at P19 | ADR-0003 §am1 |
| 5 | Hybrid token storage: file 0600 default + env override; no `--token` flag | Phase 18 PB-17 pattern |
| 6 | `Session` stays bare; `login()` returns `LoginResult` named tuple | ADR-0040 (parity preserved) |
| 7 | Drop "constant-time" clause; indexed SHA-256 equality sufficient | ADR-0003 §am1 |
| 8 | Lazy-expire → concurrent-check → mint-new ordering locked | ADR-0005 |
| 9 | `users.verify()` no longer audits; callers audit with correct event | ADR-0013 §am1 |
| 10 | `expires_at` computed, not stored; 5-column `sessions` schema | ADR-0004 §am1 |
| 11 | `logout(token)` for self; `admin_kill_session(session_id)` for admin (P22) | ADR-0005 |
| 12 | `SessionTTL(sliding_seconds, absolute_seconds)` dataclass + `_TEST_FAST_TTL` | Phase 18 PB-14 mirror |
| 13 | Free functions at P19; `MindsOSServer` class deferred to P25 | ADR-0011 §am1 |
| 14 | Single `InvalidSessionError` + cause enum (matches Phase 18 PB-23) | ADR-0003 §am1 |
| 15 | `SessionTTL` injected as explicit kwarg per call (anti-global) | Phase 18 PB-14 mirror |

## §3. Cross-chat dependencies

### Backward (Phase 19 inherits from earlier phases)

- **Phase 18 `mindsos_server/` package** — `Session` dataclass (PB-33),
  `User` (PB-24), `AuthFailedError` (PB-23), `EVT_LOGIN` /
  `EVT_LOGOUT` / `EVT_LOGIN_REJECTED_CONCURRENT` constants (PB-34),
  `verify()` (PB-13), `_db.open_db()` (PB-19), `write_audit()` (PB-34),
  `_now_utc_iso()` (PB-35), `_SCHEMA_VERSION` framework (PB-2).
- **Phase 18 PB-9 / PB-13 contract revision** — `verify()` no longer
  emits `EVT_LOGIN_FAILED` per Round-2 PB-9. Callers (`login`,
  `kill_my_own_sessions`) take ownership of the audit write. Updates
  Phase 18's `tests/phase_18/test_users.py` audit assertions (or moves
  them to Phase 19 tests).
- **Phase 18 PB-17 manifest-fallback pattern** — env > manifest >
  hard-coded. Phase 19 token storage applies the same chain:
  `MINDSOS_TOKEN` env > file > absent.
- **`feedback_pushback_format_with_picks.md`** — every pushback ended
  with a pick (3 rounds × 5 picks).
- **`feedback_phase_baseline_literal_audit.md`** — Phase 18 ships
  `_SCHEMA_VERSION=1`; Phase 19 baseline literal audit at impl time
  greps for "schema_version=1" assertions that must flip to 2.
- **`feedback_state_file_serializer_deserializer_symmetry.md`** —
  schema bump pairs DDL + migration step + any consumer that reads
  `_SCHEMA_VERSION` (doctor check per Phase 18 PB-37).

### Forward (Phase 19 → later phases)

- **Phase 20 (reset-admin + last-admin)** — `reset-admin` kills all
  sessions for the target user (`DELETE FROM sessions WHERE
  user_id = ?`); Phase 19 ships the table the verb operates on.
- **Phase 21 (audit reader)** — consumes `EVT_LOGIN`,
  `EVT_LOGIN_FAILED`, `EVT_LOGIN_REJECTED_CONCURRENT`, `EVT_LOGOUT`
  audit rows written by Phase 19.
- **Phase 22 (admin ops)** — `admin_kill_session(target_session_id)`
  per ADR-0005 escape valve; `admin_disable_user` should also kill
  sessions on success per ADR-0012 §Decision (Phase 22 wires this
  in; Phase 19 ships only the self-kill verb).
- **Phase 25 (SessionProtocol seam + persister)** — lands
  `MindsOSServer` orchestrator class (PB-13 deferral); lands
  `LocalPersister` Protocol + `InMemoryLocalPersister` +
  `FalkorDBLocalPersister` (PB-2 deferral); `login()` grows a
  hydration step that calls `persister.load(user_id)` and hands the
  dump to `KL.install_local_metagraph`. Phase 19's free `login()`
  signature is forward-compatible: extra parameters added as kwargs
  with defaults.
- **Future HTTP-daemon phase (post-38)** — re-activates the
  "sessions die on restart" rule (PB-1 deferral) and ships the
  sweeper thread (PB-4 deferral) and the `source` field on
  `AlreadyLoggedInError` (PB-3 deferral). All three are ADR §am1
  documentary scope-clarifications; the daemon phase amends them
  back into force.

## §4. ADR delta at Phase 19 ship

Five ADR amendments. All Accepted ADRs already have prior amendments
(precedent + mechanism established at Phase 13 / 14 / 14a / 15a / 16
/ 18) — Phase 19 amendments follow the same documentary form.

| ADR | Action | Reason |
|---|---|---|
| **0003** | §amendment-1 | Three changes batched: (a) drop "constant-time comparison" language (PB-7) — indexed SHA-256 equality is the mechanism; (b) sweeper thread scope-clarified to future HTTP daemon (PB-4); (c) `SessionExpiredError` unified into `InvalidSessionError` + cause enum (PB-14). |
| **0004** | §amendment-1 | Two changes batched: (a) "session state dies on server restart" §Consequences scope-clarified to future HTTP daemon (PB-1); (b) `sessions` table schema simplified — `expires_at` computed at lookup, not stored (PB-10). Final schema = 5 columns. |
| **0005** | §amendment-1 | Two changes batched: (a) "Sessions die on server restart" §Decision scope-clarified to future HTTP daemon (PB-1); (b) `AlreadyLoggedInError` payload reduced from 3 fields to 2 — `source` field deferred to HTTP daemon era (PB-3). Lazy-expire-then-concurrent-check ordering locked (PB-8) recorded in §Consequences. |
| **0011** | §amendment-1 | `LocalPersister` Protocol + `MetagraphDump` first-consumer shifts from "server `login()` at Phase 19" to "Phase 25 (SessionProtocol seam)" — Phase 19's `login()` does not hydrate Locals (no consumer at Phase 19) per PB-2. `MindsOSServer` orchestrator class first-construction also shifts to Phase 25 per PB-13. |
| **0013** | §amendment-1 | `users.verify()` no longer writes `EVT_LOGIN_FAILED` internally per PB-9. Audit-write moves to callers (`login` + `kill_my_own_sessions`) so the event accurately names the user's intent. Status: documentary; ADR §Decision "Every privileged endpoint audits both its happy path and its denial path" still holds — verify() is no longer the endpoint; login() and kill_my_own_sessions() are. |

## §5. Implementation references

```
mindsos_server/                        # extends Phase 18 pkg; no new top-level
├── __init__.py                        # +exports: LoginResult, InvalidSessionError, InvalidSessionCause, AlreadyLoggedInError, SessionTTL, PRODUCTION_TTL, login, logout, session_from_token, kill_my_own_sessions
├── _schema.py                         # MODIFIED: _SCHEMA_VERSION 1→2, +_DDL_SESSIONS, +_DDL_SESSIONS_INDEXES, +v1→v2 migration branch
├── errors.py                          # MODIFIED: +InvalidSessionError + InvalidSessionCause enum (PB-14); +AlreadyLoggedInError (PB-3)
├── users.py                           # MODIFIED: verify() drops audit write (PB-9); pure predicate now
├── sessions.py                        # NEW: login, logout, session_from_token, kill_my_own_sessions, LoginResult, SessionTTL, PRODUCTION_TTL, _TEST_FAST_TTL
├── _token_storage.py                  # NEW: file 0600 + env override resolution (PB-5)
└── (other Phase 18 files unchanged)

mindsos_cli/commands/server.py         # MODIFIED: +login, +whoami, +logout subcommands

tests/phase_19/
├── test_db_schema_v2.py               # v1→v2 migration + idempotency + schema_version row
├── test_sessions_table_ddl.py         # DDL shape + FK cascade + UNIQUE token_hash + index
├── test_login.py                      # happy path + refuse-concurrent (PB-8 ordering) + expired-then-relogin
├── test_logout.py                     # by-token (PB-11) + invalid-token silent no-op + audit row
├── test_session_from_token.py         # sliding refresh + absolute expiry + InvalidSessionError 3 causes + lazy delete on expired
├── test_kill_my_own_sessions.py       # multi-row delete + fresh-credentials gate (no token) + per-row audit
├── test_ttl_injection.py              # SessionTTL kwarg threading + PRODUCTION_TTL vs _TEST_FAST_TTL
├── test_cli_server_login_whoami_logout.py  # CLI verbs end-to-end (file storage + env override + --print-token + --json)
├── test_audit_events_login_logout.py  # EVT_LOGIN + EVT_LOGIN_FAILED + EVT_LOGIN_REJECTED_CONCURRENT + EVT_LOGOUT firing + extra_json shape
├── test_verify_no_longer_audits.py    # PB-9 regression: users.verify() does NOT write audit
└── test_token_storage.py              # ~/.mindsos/token file 0600 + MINDSOS_TOKEN env override resolution

docs/usage/server/sessions.md          # NEW (PHASE_MAP §19 Docs entry); mkdocs last_confirmed_phase: 19

# Modified outside mindsos_server/ + tests/:
mindsos_cli/_sentinel_paths.py         # +mindsos_server/sessions.py runtime sentinel
docker-compose.yml                     # phase18→phase19 tag bump
manifest.toml                          # phase = "19" + version = "0.0.0+phase19"
confirmation_docs/PHASE_MAP.md         # §19 row Features expanded with kill_my_own_sessions + token storage; §20/21/22/25 rows updated forward-deps as needed
docs/decisions/adr/0003-…              # §am1 (3-change batch — PB-7 + PB-4 + PB-14)
docs/decisions/adr/0004-…              # §am1 (2-change batch — PB-1 + PB-10)
docs/decisions/adr/0005-…              # §am1 (2-change batch — PB-1 + PB-3; §Consequences notes PB-8 ordering)
docs/decisions/adr/0011-…              # §am1 (LocalPersister + MindsOSServer Phase 25 shift)
docs/decisions/adr/0013-…              # §am1 (verify() no longer audits)

# Version bump +phase18 → +phase19 across 9 sites:
mindsos_core/__init__.py
mindsos_knowledge/__init__.py
mindsos_admin/__init__.py
mindsos_instances/__init__.py
mindsos_cli/__init__.py
mindsos_server/__init__.py
pyproject.toml [project] version
docker-compose.yml image tags
manifest.toml [mindsos] version + [mindsos] phase

# Doctor self-test check (6): version-string parity across [mindsos]
# version + pyproject + mindsos_cli/__init__.py:__version__ — Phase 18
# PB-21 bumped to 6-pkg parity; Phase 19 just bumps the literal.
# No new package + no 7-site checklist (the Phase 18 first-time
# new-pkg surface stays; Phase 19 extends in-place).
```

## §6. Scope boundaries (out-of-scope at Phase 19 ship)

- **`MindsOSServer` orchestrator class** — Phase 25 per PB-13. Free
  functions ship in `mindsos_server/sessions.py` at P19.
- **`LocalPersister` Protocol + `MetagraphDump` + `InMemoryLocalPersister`
  + `FalkorDBLocalPersister`** — Phase 25 per PB-2 (revises Phase 18
  PB-18 which said P19).
- **KL hydration on login** — Phase 25 (consumer exists only after
  SessionProtocol seam lands).
- **`reset-admin` CLI verb + `_assert_not_sole_admin` helper** —
  Phase 20.
- **`admin_kill_session` + `CAN_KILL_SESSION` enforcement** — Phase 22.
- **`admin_disable_user` killing sessions** — Phase 22 (ADR-0012
  §Decision; Phase 19 ships only the self-kill path).
- **`admin_query_audit` reader + `CAN_VIEW_AUDIT_LOG` enforcement** —
  Phase 21.
- **Sweeper thread for expired-sessions GC** — future HTTP daemon
  phase per PB-4.
- **`source` field on `AlreadyLoggedInError` payload** — future HTTP
  daemon phase per PB-3.
- **`session_from_token` + KL `install_local_metagraph` integration**
  — Phase 25.
- **Promotion (`propose_for_promotion`, `release_update`)** —
  Phase 24.
- **HTTP transport** — no roadmap; CLI-only product per Phase 18 §6.
- **`mindsos server reset-sessions` nuclear-wipe verb** — not shipped;
  `kill_my_own_sessions(credentials)` covers self-recovery; admins
  can `DELETE FROM sessions` directly on `server.db` for emergency.

## §7. Design saturation note

Three rounds (15 picks). Phase 18's four-round shape was the
precedent; Phase 19 round 4 was self-flagged at the close of round 3
as likely impl-detail (CLI exit codes, `--json` payload field sets,
`tests/phase_19/` file split, whether `_DEFAULT_SESSION_ID_BYTES` is
a public knob, `SessionTTL` units choice — int seconds vs
`timedelta`). User confirmed lock at round 3. Implementation proceeds
per the task list in this chat. Any new pushback surfaced during
implementation is recorded as a B-19-TN hotfix in the confirmation
doc, not a retroactive PB-NN entry (Phase 18 precedent).
