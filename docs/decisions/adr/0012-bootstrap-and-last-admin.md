# ADR-0012: `bootstrap` and `reset-admin` CLIs + last-admin protection

- **Status:** Accepted
- **Date:** 2026-04-22
- **Related:** ADR-0002, ADR-0003

## Context

A fresh install has no users; someone has to seed the first admin, and they can't do it through the normal admin endpoints because those require an admin session. If an operator later demotes, disables, or deletes the only remaining admin, the system becomes unreachable through normal administration. Both scenarios need explicit answers.

## Decision

Two CLI subcommands and one invariant:

**`mindsos-server bootstrap`** (interactive, idempotent):

- If `server.db` has zero admins, prompt for `user_id` and password, argon2id-hash, insert with `role="admin"` and the full `ADMIN_CAPS`.
- If admins already exist, exit 0 with a message — never modify state. Makes the command safe to run in deployment scripts.
- Password is read via `getpass` (no echo); never logged, never stored outside the argon2 hash.

**`mindsos-server reset-admin`** (lock-out recovery):

- Accepts `--user-id` (existing or new) and a new password.
- Upserts the row with `role="admin"`, fresh argon2 hash, `disabled=0`, and full `ADMIN_CAPS`.
- Kills every active session for that user.
- Writes an `AUDIT_RESET_ADMIN` row with the calling OS user from `pwd.getpwuid(os.getuid())`.
- Intended to be run only with filesystem access to `server.db` — that's the proof of authority.

**Last-admin protection.** The following admin endpoints refuse to leave the system with zero admins:

- `admin_demote_user` — raises `LastAdminError` (HTTP 409) if target is the sole admin.
- `admin_disable_user` — same check, plus kills sessions on success.
- `hard_delete_user` — same check.

Enforcement is a single helper `_assert_not_sole_admin(target_user_id)` that counts `role='admin' AND disabled=0` rows.

## Rationale

- **Bootstrap as a CLI, not an endpoint.** Running locally proves the operator has filesystem access, which is a stronger authority signal than any endpoint-level shim.
- **Idempotent.** Makes `bootstrap` safe in deploy pipelines; no "was this already run?" state tracking needed.
- **`reset-admin` as an escape hatch.** Lock-out is a real risk; pretending it can't happen costs us a recovery story. Filesystem access is the acceptable authority floor.
- **Last-admin check in the server, not the CLI.** It applies to every path that could orphan the install — `admin_*` endpoints and `hard_delete_user` — not just the CLI.
- **Never zero admins, always at least one.** This is the only invariant strong enough to guarantee admin endpoints remain usable. Anything weaker leaves recovery to `reset-admin` only.

## Consequences

- `reset-admin` is audited with the OS user as actor because there is no `Session` when it runs. Operators are expected to audit their shell/terminal access.
- A single-admin install must either promote a second admin before demoting/disabling the first, or accept the `LastAdminError` and think again. The error message names `reset-admin` as the official override.
- `bootstrap` is the documented first step in the install guide; CI smoke tests run it.
- Test coverage: promote-second-admin-then-demote-first, disable-last-admin-refused, hard-delete-last-admin-refused, reset-admin happy path.

## Alternatives considered

1. **Auto-create `root` admin with random password, printed once.** Rejected — brittle in container deployments where stdout is lost; idempotent interactive prompt is cleaner.
2. **Environment-variable bootstrap (password via `$FMG_ADMIN_PASS`).** Considered as an add-on for non-interactive deploys; not v1, but `bootstrap` can grow it without an ADR change.
3. **No last-admin protection; rely on `reset-admin` for recovery.** Rejected — makes a trivially-preventable foot-gun (one demote away from lock-out) cheap to hit, while the check is a single COUNT query.
4. **HTTP endpoint for reset-admin gated by a one-time token printed to stdout.** Rejected — reinvents filesystem authority without improving on it.

## Revisions

### amendment-1 (Phase 18 ship — 2026-05-21) — bootstrap CLI verb lifted from Phase 20 to Phase 18

**Trigger:** Phase 18 design pass surfaced a chicken-and-egg between
the row scope ("user create / list / verify") and the original Phase
20 home of the bootstrap CLI verb. Without bootstrap, Phase 18's
`mindsos server user create` CLI verb has no admin caller and is
unusable end-to-end until Phase 19 (login) + Phase 20 (bootstrap)
both ship. Phase 18 PB-27 lifted the bootstrap CLI verb up to Phase
18 so the package ships end-to-end-usable.

**Amended behavior:**

* **`mindsos server bootstrap`** ships at Phase 18 (was: Phase 20).
  Single-binary form per PHASE_MAP §1 — verb-group `server`, verb
  `bootstrap`; supersedes the ADR's original `mindsos-server bootstrap`
  separate-binary wording.
* The verb's idempotency check lives at the CLI layer per Phase 18
  PB-29: `SELECT COUNT(*) FROM users WHERE actor_role='admin' AND
  disabled=0`; if ≥1, exits 0 with message. The underlying helper
  `mindsos_server.users._insert_first_admin(conn, user_id, password,
  *, params, os_user)` is a pure insert; tests exercise both layers
  independently.
* The `EVT_BOOTSTRAP` audit row uses the OS user (from
  `pwd.getpwuid(os.getuid()).pw_name`) as `actor_user` per §Decision
  ("Writes an `AUDIT_RESET_ADMIN` row with the calling OS user")
  — Phase 18 generalizes the "no Session at bootstrap time → OS user
  is the audit actor" pattern to `EVT_BOOTSTRAP`.

**Phase 20 narrowing:** Phase 20's Features list narrows from three
items ("first-admin bootstrap; reset-admin recovery; last-admin
removal blocked") to two ("reset-admin recovery; last-admin removal
blocked"). PHASE_MAP §20 row amended at Phase 18 ship.

**Out-of-scope:** `mindsos server reset-admin` + last-admin protection
helper (`_assert_not_sole_admin`) still land at Phase 20.

See `halvim_mindsos/confirmation_docs/PHASE_18_DESIGN_LOG.md` §1
round 3 PB-27 for the scope-shift rationale.

### amendment-2 (Phase 20 ship — 2026-05-21) — reset-admin narrowed (existing admin only); audit-event roster locked; CLI shape locked; transaction order locked; `_assert_not_sole_admin` deferred to Phase 22

**Trigger:** Phase 20 design pass surfaced six clauses where the
2026-04-22 §Decision text either (a) under-specifies a security-load-
bearing mechanism, (b) widens reset-admin's scope beyond the "lock-out
recovery" framing of §Rationale, or (c) commits to shipping a helper
that has no Phase 20 consumer. Four design rounds / 13 picks
batched into this single revision per Phase 19's batching precedent
(ADR-0003 §am1 / ADR-0004 §am1 / ADR-0005 §am1).

**Amended behavior (six changes batched):**

1. **`reset-admin` accepts existing user_id ONLY (PB-A).** §Decision's
   "Accepts `--user-id` (existing or new) and a new password" is
   narrowed to "Accepts `<user_id>` (existing admin) and a new password."
   Rationale: §Rationale frames reset-admin as "lock-out recovery";
   accepting a new user_id makes reset-admin a parallel `bootstrap`
   that ignores bootstrap's idempotency guard. Anyone with `server.db`
   write access could mint admins forever, bypassing the documented
   install story. New admins land via `bootstrap` (P18) for the first
   admin and `admin_promote_user` (P22) for subsequent ones. Reset-admin
   raises `UserNotFoundError(target_user_id)` on missing target.

2. **Target must already have `actor_role='admin'` (PB-E).** §Decision's
   "Upserts the row with `role='admin'`" — if read as silent-promotion-
   OK — would let reset-admin double as a "promote arbitrary user to
   admin" backdoor, exactly the power that Phase 22's `admin_promote_user`
   (gated by `CAN_MANAGE_USERS`) is meant to control. Reset-admin
   raises `NotAnAdminError(target_user_id, actual_role)` if target
   exists but is not an admin. The (rare) "I demoted my only admin
   and now nobody can admin" foot-gun gets closed by P22's
   `_assert_not_sole_admin`; until P22 ships it's a known-deferred
   risk noted in the Phase 20 design log §6.

3. **Audit-event roster locked: 1× `EVT_RESET_ADMIN` + N×
   `EVT_KILL_SESSION` + conditional 1× `EVT_ADMIN_ENABLE_USER` if
   target was disabled (PB-D + PB-U).** §Decision says "Writes an
   `AUDIT_RESET_ADMIN` row" + "Kills every active session for that
   user" without specifying the audit-event count for the session
   kills or the disable→enable transition. Per Phase 18 PB-34 the full
   audit-constant roster (including `EVT_KILL_SESSION` and
   `EVT_ADMIN_ENABLE_USER`) ships at P18 — Phase 20 first-fires both
   in addition to `EVT_RESET_ADMIN`. P21's audit reader can
   differentiate "user logged out" (`EVT_LOGOUT`) from "admin killed
   your session" (`EVT_KILL_SESSION`) without parsing `extra_json`.
   `EVT_KILL_SESSION.extra_json = {"session_id": sid, "context":
   "reset_admin"}` per P19 key-name precedent;
   `EVT_RESET_ADMIN.extra_json = {"was_disabled": bool,
   "sessions_killed": N}` for P21-reader denormalization.

4. **CLI shape: positional REQUIRED, no prompt fallback (PB-G).**
   §Decision says `--user-id` flag. Phase 20 ships
   `mindsos server reset-admin <user_id>` — positional, required, no
   `typer.prompt()` fallback if missing. Rationale: recovery is
   destructive; deliberate is better than convenient. Diverges from
   `bootstrap`'s positional-with-prompt-fallback convention by design
   (bootstrap is install-time and idempotent; reset is recovery-time
   and destructive).

5. **Transaction order locked: DELETE-then-UPDATE in single SQLite
   transaction (PB-R).** §Decision's "Upserts the row + kills every
   active session" leaves order unspecified. If UPDATE commits first
   and we crash before DELETE, old tokens (minted under old password)
   stay valid against the new password — a *worse* state than
   pre-reset. Locked order: `DELETE sessions WHERE user_id=? → UPDATE
   users SET password_hash=?, disabled=0 WHERE user_id=? → INSERT N×
   audit rows → commit()`. Atomic + intuitive read order ("kill the
   sessions, then change the lock").

6. **`_assert_not_sole_admin` helper + `LastAdminError` class shift
   from Phase 20 to Phase 22 (PB-B).** ADR-0012 §Decision names three
   call sites for the helper — `admin_demote_user`, `admin_disable_user`,
   `hard_delete_user` — all of which ship at Phase 22. Reset-admin
   itself never violates the zero-admin invariant (it only adds /
   refreshes admins). Shipping the helper at P20 with no consumer
   invites drift between the helper signature and the eventual P22
   callers. Phase 22 ships the helper, the `LastAdminError` class, and
   wires all three call sites in one chat.

**Rationale:** §Decision's "lock-out recovery" thesis is preserved.
What shifts are the *mechanism specifics* — narrower target scope
(PB-A + PB-E), explicit audit shape (PB-D + PB-U), explicit CLI
shape (PB-G), atomicity ordering (PB-R), and consumer-driven
helper placement (PB-B). All six changes flow from the Phase 20
design review's principle: reset-admin is a *narrow* recovery
mechanism, not a parallel admin-management API.

**Phase 20 narrowing:** Phase 20's Features list narrows from two
items (after Phase 18 §am1 already lifted bootstrap) down to one:
"reset-admin recovery (`mindsos server reset-admin <user_id>`)". The
last-admin-protection Feature moves entirely to Phase 22. PHASE_MAP
§20 row amended at Phase 20 ship.

**Out-of-scope (deferred to later phases):** `_assert_not_sole_admin`
+ `LastAdminError` (P22); `admin_promote_user` for user→admin
escalation (P22); `admin_kill_session` second-fire of
`EVT_KILL_SESSION` (P22); audit reader (P21); HTTP-409 mapping of
`LastAdminError` (P22 with class); HTTP transport (no roadmap —
CLI-only per PHASE_MAP §1).

See `halvim_mindsos/confirmation_docs/PHASE_20_DESIGN_LOG.md` §1
rounds 1-4 for the round-by-round rationale and §2 for the 13-pick
consolidated reference table.

### amendment-3 (Phase 22 ship — 2026-05-22) — admin ops: six verbs + helper + class + admin_tx race protection + exit-code namespace

**Trigger:** Phase 22 closes the PB-B deferral from Phase 20
§amendment-2: ships `_assert_not_sole_admin` + `LastAdminError` and
wires the three call sites the §Decision enumerates
(`admin_demote_user`, `admin_disable_user`, `hard_delete_user`).
Phase 22 also ships the three remaining admin-management verbs
(`admin_promote_user`, `admin_enable_user`, `admin_kill_session`) +
ADR-0008 cross-user read DEFERRED to Phase 25 per ADR-0008
§amendment-1. Five design rounds / 27 picks; ADR-0008 amendment is
its own document.

**Amended behavior (six clauses batched):**

1. **`_assert_not_sole_admin` shipped at Phase 22 (R1 PB-7).**
   Signature: `_assert_not_sole_admin(conn: sqlite3.Connection,
   target_user_id: str) -> None`. Implementation: single SELECT of
   active admin user_ids (`actor_role='admin' AND disabled=0`); raises
   :class:`LastAdminError` iff the result is exactly
   `[target_user_id]`. Lives in `mindsos_server/admin.py` per Phase 20
   PB-Z module-home precedent. The helper is called by
   `admin_demote_user`, `admin_disable_user`, and `hard_delete_user`
   — `admin_promote_user`, `admin_enable_user`, and
   `admin_kill_session` do NOT call it (they cannot shrink the
   active-admin count).

2. **`LastAdminError(target_user_id)` shipped at Phase 22 (R1 PB-23).**
   Single-attribute constructor; mirrors Phase 20
   :class:`NotAnAdminError` / Phase 21 :class:`PermissionDeniedError`
   density. Error message embeds the override hint per §Consequences
   ("names `reset-admin` as the official override") inline, not via a
   separate attribute. Future HTTP-409 mapping deferred per CLI-only
   product (no roadmap; future HTTP-transport phase ships the
   mapping).

3. **Six admin verbs locked in `mindsos_server/admin.py` (R1 PB-2
   subgroup + R3 PB-19 result types):**
   * `admin_promote_user(conn, session, *, target_user_id) ->
     PromoteUserResult` — UPDATE actor_role='admin'; raises
     :class:`AlreadyAnAdminError` on already-admin target (R1 PB-3,
     NEW class — symmetric with NotAnAdminError; no idempotent
     re-promote); `disabled` flag LEFT UNCHANGED per R2 PB-12 (no
     auto-enable side effect); SILENT (no session-kill) per R1 PB-5
     (cap expansion is safe).
   * `admin_demote_user(conn, session, *, target_user_id) ->
     DemoteUserResult` — atomic DELETE-sessions + UPDATE-role per
     R1 PB-4 (session-immutable caps mean demote MUST kill sessions
     to be observable); calls `_assert_not_sole_admin`.
   * `admin_disable_user(conn, session, *, target_user_id) ->
     DisableUserResult` — atomic DELETE-sessions + UPDATE-disabled
     per R1 PB-6; calls `_assert_not_sole_admin` ONLY when target is
     an active admin (R3 non-pushback lock). Idempotent on
     already-disabled per R2 PB-15 (verb invocation audited regardless
     of state change).
   * `admin_enable_user(conn, session, *, target_user_id) ->
     EnableUserResult` — UPDATE-disabled=0; audit always per R1 PB-10
     (privileged-endpoint invocation audited regardless of no-op
     status). No session kill.
   * `admin_kill_session(conn, session, *, target_session_id) ->
     KillSessionResult` — by-session_id deliberate-target verb per
     R1 PB-9; raises :class:`SessionNotFoundError` (NEW class per
     R2 PB-13) on missing target.
   * `hard_delete_user(conn, session, *, target_user_id) ->
     HardDeleteUserResult` — audit-then-DELETE order (per-session
     EVT_KILL_SESSION written BEFORE the user DELETE; FK CASCADE
     auto-clears sessions; audit rows have no FK so target_user
     string survives the user-row delete per ADR-0013 §Consequences).
     Calls `_assert_not_sole_admin` when target is an active admin.
     Cap name `CAN_HARD_DELETE_ARCHIVED` is documentary debt per R2
     PB-17 (no archive-first precondition; rename deferred per
     ADR-0002 §Consequences).

4. **`admin_tx` context manager — concurrent-admin race protection
   (R4 PB-24).** New helper in `mindsos_server/admin.py`:

   ```python
   @contextmanager
   def admin_tx(conn):
       conn.execute("BEGIN IMMEDIATE")
       try:
           yield
       except BaseException:
           conn.rollback()
           raise
       else:
           conn.commit()
   ```

   All six Phase 22 verbs wrap their body in `with admin_tx(conn):`
   AFTER the `_require_or_audit` cap-gate returns happy. `BEGIN
   IMMEDIATE` acquires the SQLite WAL RESERVED write lock at
   tx-start; the second concurrent admin verb blocks until the first
   commits (up to `busy_timeout=5000` ms set in
   :func:`mindsos_server._db.open_db`), then sees the first commit's
   state. Without this wrapper, two concurrent admin verbs in
   separate connections could each pass `_assert_not_sole_admin`
   against a stale snapshot and both commit — leaving the system with
   zero active admins. Reset-admin (Phase 20) does NOT yet use this
   wrapper — flagged as a minor inconsistency for future cleanup
   (Phase 20 had no `_assert_not_sole_admin` consumer; the
   cross-process race wasn't surfaced then).

5. **`NotAnAdminError` message reworked verb-agnostic (R4 PB-25).**
   Phase 20 wording embedded reset-admin's "use `admin promote-user`
   to escalate" hint; that hint is misleading for `admin_demote_user`'s
   failure (where target-is-non-admin is the "already where you want
   them" state). New message: `f"user {target_user_id!r} has
   actor_role={actual_role!r}; admin role required"`. Verb-specific
   stderr framing now lives in CLI handlers, not the exception.
   Phase 20 tests asserting on `"user"` + `"alice"` substring still
   pass (actor_role surfaced verbatim).

6. **CLI subgroup + exit-code namespace (R1 PB-2 + R3 PB-21 + R5 PB-27).**
   The six verbs ship under `mindsos server admin <verb>` Typer
   subgroup; flat `reset-admin` (Phase 20) + flat `query-audit` (Phase
   21) stay under `mindsos server` (no migration). All six verbs
   REQUIRED-positional, no prompt, no `--force`/`--dry-run` per R4
   PB-26; all support `--json` per R3 PB-20 (key=value plain
   default). Exit codes per R5 PB-27 (extend-don't-retrofit; P20
   baseline preserved):

   | Code | Class |
   |---|---|
   | 0 | success |
   | 1 | generic / not-logged-in |
   | 2 | ValueError / UserNotFoundError / NotAnAdminError (P20) |
   | 3 | PermissionDeniedError (P21) |
   | 4 | LastAdminError (NEW @ P22) |
   | 5 | AlreadyAnAdminError (NEW @ P22) |
   | 6 | SessionNotFoundError (NEW @ P22) |

**Audit-roster shifts (consequence of clause-3 verbs first-firing):**

* `EVT_ADMIN_PROMOTE_USER` first-fires at P22 with `extra =
  {"prior_role": "user"}`.
* `EVT_ADMIN_DEMOTE_USER` first-fires at P22 with `extra =
  {"prior_role": "admin", "sessions_killed": N}`.
* `EVT_ADMIN_DISABLE_USER` first-fires at P22 with `extra =
  {"was_already_disabled": bool, "sessions_killed": N}`.
* `EVT_ADMIN_ENABLE_USER` second-fires at P22 (first-fire was P20
  reset-admin's conditional clause; the two extra shapes coexist by
  key-presence). P22's extra: `{"was_already_enabled": bool}`.
* `EVT_HARD_DELETE_USER` first-fires at P22 with `extra =
  {"prior_role": str, "was_disabled": bool, "sessions_killed": N}`.
* `EVT_KILL_SESSION` second+-fires at P22 (first-fire was P20
  reset-admin per `EVT_KILL_SESSION.extra.context` discriminator).
  P22 contexts (R2 PB-14 vocab): `"admin_kill_session"`,
  `"admin_disable_user"`, `"admin_demote_user"`,
  `"hard_delete_user"`.

**Self-targeting (R2 PB-18):** Allowed across all six verbs. No
`SelfTargetError`. Operator authority is filesystem-equivalent per
§Rationale ("filesystem access is the acceptable authority floor");
`_assert_not_sole_admin` is the only invariant that constrains
self-targeting on demote/disable/hard-delete; reset-admin via
filesystem is the recovery floor for any operator who locks
themselves out.

**Rationale:** §Decision's three-invariant thesis ("never zero
admins; admin endpoints refuse to leave zero; `_assert_not_sole_admin`
is the single helper enforcing it") is preserved. What ships at
Phase 22 is the mechanism: helper + class + the three callers; plus
the three additional admin-management verbs the original §Decision
didn't enumerate but P22's scope row demanded; plus the concurrent-
admin race protection `admin_tx` (R4 PB-24 catch).

**Phase 22 narrowing:** Cross-user read (ADR-0008) DEFERRED from
PHASE_MAP §22 row Features per R1 PB-1. The §Decision-mandated
mechanisms (`MindsOSServer._installed_locals`, `LocalPersister.load`,
`KL.install_local_metagraph`) all ship at Phase 25; Phase 22 cannot
honor ADR-0008 §Decision at this slot. See ADR-0008 §amendment-1
for the phase shift documentation. PHASE_MAP §22 row rewrite at
Phase 22 ship documents the cross-user-read removal.

**Out-of-scope (deferred to later phases):** Cross-user read +
`read_other_local()` (Phase 25 with `MindsOSServer` +
`LocalPersister`); KL-side Local hard-delete (`hard_delete_user`
at Phase 22 deletes the user row + sessions only — KL Local-cleanup
deferred to a KL phase); two-step archive-then-delete (PB-17
rejected; cap name `CAN_HARD_DELETE_ARCHIVED` is documentary debt);
`--dry-run` flag for destructive verbs (no demand surfaced); HTTP
transport / HTTP-409 mapping for `LastAdminError`; reset-admin
retrofit through `admin_tx` (Phase 20 has no
`_assert_not_sole_admin` consumer; flagged for future cleanup);
retrofit of P18 `user create/list/verify` through
`_require_or_audit` (pre-bootstrap-era verbs hold filesystem
authority; flagged for a future cleanup phase).

See `halvim_mindsos/confirmation_docs/PHASE_22_DESIGN_LOG.md` §1
rounds 1-5 for the round-by-round rationale and §2 for the 27-pick
consolidated reference table.
