# Phase 19 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

Server: sessions

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

Phase 19 ships the sessions half of the L0 auth substrate per
ADR-0003. Extends the Phase 18 `mindsos_server/` package in-place
(no new top-level pkg; no 7-site checklist). 15 picks across 3
design rounds (see `confirmation_docs/PHASE_19_DESIGN_LOG.md`);
round 4 self-flagged as impl-detail-saturation and skipped at
user confirmation, mirroring Phase 18's 4→3 truncation precedent.

Surface shipped:
- `mindsos_server/sessions.py` (NEW) — free-function surface per
  PB-13 (MindsOSServer class deferred to Phase 25 per
  ADR-0011 §am1). `login(conn, user_id, password, *, ttl, params)
  -> LoginResult`, `logout(conn, token) -> bool`,
  `session_from_token(conn, token, *, ttl) -> Session`,
  `kill_my_own_sessions(conn, user_id, password, *, ttl, params)
  -> int`. SessionTTL(sliding_seconds, absolute_seconds) +
  PRODUCTION_TTL (8h / 24h) + _TEST_FAST_TTL (1s / 2s) per PB-12.
  LoginResult(session, token, created_at, expires_at) per PB-6
  keeps Session bare (Phase 18 PB-33 shape preserved).
- `mindsos_server/_token_storage.py` (NEW) — file 0600 default +
  MINDSOS_TOKEN env override + MINDSOS_TOKEN_FILE path override
  per PB-5; mirrors Phase 18 PB-17 manifest-fallback chain.
  Atomic-replace write pattern; silent delete-on-logout; no
  `--token` CLI flag declared (mirrors Phase 18 PB-8's
  no-`--password` rule).
- `mindsos_server/errors.py` (MODIFIED) — added
  `InvalidSessionError + InvalidSessionCause` enum per PB-14 +
  ADR-0003 §am1 (replaces ADR-0003 §Decision's `SessionExpiredError`;
  single opaque class with private cause enum mirrors Phase 18
  PB-23 `AuthFailedError`); added `AlreadyLoggedInError` with
  2-field payload {existing_session_id, created_at} per PB-3 +
  ADR-0005 §am1 (source field deferred to HTTP daemon phase).
- `mindsos_server/_schema.py` (MODIFIED) — `_SCHEMA_VERSION` 1→2;
  added `_DDL_SESSIONS` (5-column shape per PB-10; `expires_at`
  computed not stored per ADR-0004 §am1) + `_DDL_SESSIONS_INDEXES`
  (idx_sessions_user_id for the refuse-concurrent-login + multi-row
  delete hot paths); appended v1→v2 migration branch in
  `init_or_migrate`. Forward-only append; no data migration needed.
- `mindsos_server/users.py` (MODIFIED) — verify() drops audit write
  per PB-9 + ADR-0013 §am1. Pure predicate now; callers
  (`login` + `kill_my_own_sessions`) own EVT_LOGIN_FAILED emission
  with context-appropriate `extra_json`. Revises Phase 18 PB-13
  contract. Phase 18 `test_users.py::test_audit_row_written_on_failure`
  flipped to `test_verify_writes_no_audit_row` (PB-9 regression
  guard); equivalent positive assertion lives at
  `tests/phase_19/test_audit_events_login_logout.py`.
- `mindsos_server/__init__.py` — exports updated per design log §5:
  +login, +logout, +session_from_token, +kill_my_own_sessions,
  +LoginResult, +SessionTTL, +PRODUCTION_TTL, +InvalidSessionError,
  +InvalidSessionCause, +AlreadyLoggedInError.
- `mindsos_cli/commands/server.py` (MODIFIED) — added `login`,
  `whoami`, `logout` subverbs. `login` reads password from stdin
  per PB-8 (no `--password` flag); writes token to
  `~/.mindsos/token` mode 0600 by default; `--print-token` ALSO
  emits to stdout for shell capture. `whoami` always exits 0 in
  `--json` mode (pipe-friendly minor lock); plain mode exits 1 if
  not logged in. `logout` is silent no-op on missing/invalid
  token; instructs the user to `unset MINDSOS_TOKEN` if env was set.

Phase 19 extensions to Phase 18's sentinel-paths list:
- `mindsos_server/sessions.py`
- `mindsos_server/_token_storage.py`

(No 7-site checklist — same Phase 18 package; just two new files
under it. Dockerfile `COPY mindsos_server` picks them up
automatically as a directory copy.)

Version bump `+phase18 → +phase19` across 9 sites: 6 `__init__.py`
+ pyproject.toml + docker-compose.yml + manifest.toml.

ADR amendments at this ship (5):
- ADR-0003 §am1 — 3-change batch: (a) drop "constant-time comparison"
  language per PB-7 (indexed SHA-256 equality is the mechanism);
  (b) scope sweeper thread to future HTTP daemon phase per PB-4
  (no daemon to host a thread in CLI-only product); (c) unify
  `SessionExpiredError` into `InvalidSessionError + cause enum`
  per PB-14 (mirrors Phase 18 PB-23 AuthFailedError pattern).
- ADR-0004 §am1 — 2-change batch: (a) scope "session state dies on
  server restart" §Consequences to future HTTP daemon per PB-1
  (no restart event in CLI-only); (b) simplify `sessions` schema to
  5 columns per PB-10 (`expires_at` computed at lookup, not stored;
  drift class eliminated).
- ADR-0005 §am1 — 2-change batch: (a) scope "sessions die on server
  restart" §Decision to future HTTP daemon per PB-1; (b) drop
  `source` field from `AlreadyLoggedInError` payload per PB-3
  (no meaningful "source" distinction in single-host CLI). §Consequences
  notes the PB-8 ordering lock (lazy-expire → concurrent-check →
  mint-new) closing the 9-hour-stale-session foot-gun.
- ADR-0011 §am1 — `LocalPersister` Protocol + `MetagraphDump` +
  `MindsOSServer` orchestrator class first-construction all shift
  from Phase 19 (the Phase 18 PB-18 deferral target) to Phase 25.
  Rationale: Phase 19 `login()` doesn't need to hydrate Locals
  (no consumer at Phase 19); the orchestrator class has nothing
  to hold without the persister. Phase 19's free-function
  signatures are forward-compatible (Phase 25 adds `persister` +
  `kl` as kwargs with defaults).
- ADR-0013 §am1 — `users.verify()` no longer writes
  `EVT_LOGIN_FAILED` per PB-9. Callers (`login` +
  `kill_my_own_sessions`) own the audit emission. §Decision's
  "Every privileged endpoint audits both its happy path and its
  denial path" still holds — verify() is no longer the endpoint;
  login() and kill_my_own_sessions() are.

PHASE_MAP §19 row expanded per design log §5 (Features +
Modules touched + Tests + Risks + Docs + Breaking changes). §25
row absorbed PB-2 + PB-13 — LocalPersister + MindsOSServer class
first-construction land at Phase 25 (was: implicit Phase 19).

Tests/phase_19: 11 test files per design log §5
(test_db_schema_v2 + test_sessions_table_ddl + test_login +
test_logout + test_session_from_token +
test_kill_my_own_sessions + test_ttl_injection +
test_cli_server_login_whoami_logout +
test_audit_events_login_logout + test_verify_no_longer_audits +
test_token_storage). Phase 18 tests adjusted per
feedback_phase_baseline_literal_audit.md (schema_version literal
1→2 in test_db_schema.py; `test_no_sessions_table_at_v1` flipped
to `test_sessions_table_exists_at_v2`; verify-audit assertion
inverted to PB-9 regression guard).

Manual CLI smoke (to be run by tester):
1. `mindsos server bootstrap admin` (Phase 18 carry-forward;
   should still pass; idempotent skip if Phase 18 left an admin).
2. `echo adminpw | mindsos server login admin` → exit 0;
   token file `~/.mindsos/token` exists mode 0600.
3. `mindsos server whoami` → exit 0; identity printed.
4. `mindsos server whoami --json | jq .logged_in` → "true".
5. `echo adminpw | mindsos server login admin` → exit 1 +
   "already logged in" stderr (refuse-concurrent per ADR-0005).
6. `mindsos server logout` → exit 0; token file removed.
7. `mindsos server whoami` → exit 1 + "not logged in" stderr.
8. `mindsos server whoami --json | jq .logged_in` → "false";
   exit 0 (pipe-friendly minor lock).

Deferred / out-of-scope (see DESIGN_LOG §6 for full list):
LocalPersister + MetagraphDump (P25 per PB-2; ADR-0011 §am1
supersedes Phase 18 PB-18); MindsOSServer orchestrator class
(P25 per PB-13); reset-admin + last-admin protection (P20);
audit query reader (P21); admin_kill_session + admin ops (P22);
admin_disable_user killing sessions (P22); sweeper thread
(future HTTP daemon phase per PB-4); `source` field on
AlreadyLoggedInError (future HTTP daemon phase per PB-3); KL-side
SessionProtocol seam + KL capability constants mirror (P25).
