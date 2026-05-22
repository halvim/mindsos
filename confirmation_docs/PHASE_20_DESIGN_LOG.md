---
phase: 20
phase_title: "Server: admin reset + last-admin protection (narrowed twice)"
layer: L0
status: design-locked
date_locked: 2026-05-21
branch: phase-20
tag_on_confirm: phase-20-confirmed
net_new: false   # extends Phase 18 mindsos_server/ pkg; new module admin.py inside the pkg (no new top-level pkg = no 7-site checklist)
design_rounds: 4
total_picks: 13
prior_phase: 19
next_phase: 21
---

# Phase 20 Design Log — Server: admin reset (narrowed twice)

## §0. Scope summary

Phase 20 ships ONE feature: `mindsos server reset-admin <user_id>`, the
lock-out recovery escape hatch per ADR-0012. Scope is narrowed TWICE:

1. **Phase 18 PB-27** lifted the bootstrap CLI verb from Phase 20 to
   Phase 18 (the verb was unusable end-to-end without it). PHASE_MAP §20
   row dropped from 3 Features to 2.
2. **Phase 20 PB-B** (this chat, round 1) drops the second remaining
   Feature — `_assert_not_sole_admin` helper + `LastAdminError` class —
   to Phase 22, where the three call sites that consume it ship
   (`admin_demote_user`, `admin_disable_user`, `hard_delete_user`).
   No P20 caller would exercise it; shipping it naked invites drift
   between helper signature and P22 callers.

Phase 20 narrows to ONE Feature. Per PHASE_MAP §1 row-rewrite rule, the
§20 row at ship-time amends Features down to:

> `reset-admin` recovery (`mindsos server reset-admin <user_id>`).

The deferred Feature appears as a forward-dep note on §22.

Code lives inside the Phase 18 `mindsos_server/` package — no new
top-level pkg, so the 7-site `feedback_new_top_level_package.md`
checklist does NOT apply. Phase 20 DOES add a new module
`mindsos_server/admin.py` (PB-Z) — one sentinel-paths entry, one
`__init__.py` export, no Dockerfile change (existing `COPY mindsos_server/`
directory-copy picks up the new file).

This phase **does NOT** ship: `_assert_not_sole_admin` helper +
`LastAdminError` class (Phase 22 per PB-B); promotion of non-admin
users to admin (Phase 22 `admin_promote_user`); admin_disable_user /
admin_demote_user / hard_delete_user (Phase 22); audit query reader
(Phase 21); HTTP transport (no roadmap; CLI-only per Phase 18 §6).

One ADR amendment at this ship: ADR-0012 §amendment-2 batches all six
documentary changes (PB-A + PB-D + PB-E + PB-G + PB-R + PB-U) into
a single revision entry. ADR-0013 left untouched (audit-constant
first-firers are impl-level, not ADR-level — PB-D's EVT_KILL_SESSION
and PB-U's EVT_ADMIN_ENABLE_USER first-fires shift P22→P20 silently).

## §1. Round-by-round design ledger

Four rounds of pushbacks before lock. Picks per pushback + final picks
summary per `feedback_pushback_format_with_picks.md`. Phase 18's
four-round shape was the precedent; Phase 19 stopped at three; Phase 20
ran four with round 4 explicitly flagged as forward-positioning and
audit-reader convenience (not correctness).

### Round 1 — Premise audit + scope narrowing (PB-A..PB-C)

Pre-impl probe established: (a) Phase 19 squash `80a1b02` at
`origin/main` tip + `phase-19-confirmed` resolves to the same SHA;
(b) `mindsos_server/` intact with all 11 Phase 19 files including
`sessions.py` and `_token_storage.py`; (c) `EVT_RESET_ADMIN` +
`EVT_BOOTSTRAP` + `EVT_KILL_SESSION` + `EVT_ADMIN_ENABLE_USER` all
already declared at Phase 18 (audit.py per PB-34); (d) `count_admins()`
helper exists in `users.py`; (e) `_SCHEMA_VERSION=2` from Phase 19;
(f) all 6 packages at `+phase19`; (g) no `reset_admin` /
`_assert_not_sole_admin` / `LastAdminError` shipped — only references
in comments. Sandbox `git fetch` blocked by SSH key; tag verification
done by user on Mac.

Read ADRs 0002 (+§am1), 0003 (+§am1), 0005 (+§am1), 0012 (+§am1),
0013 (+§am1) to ground each pushback. The Round 1 thesis: the
narrowed §20 row still has a scope ambiguity (reset-admin on new user
ID) and a deferral question (helper without consumer).

**PB-A — `reset-admin` user scope: existing-only vs accept-new.**
ADR-0012 §Decision: "Accepts `--user-id` (existing or new) and a new
password." §Rationale frames the verb as "lock-out recovery." If
reset-admin can mint *new* admins, bootstrap's idempotency guard
becomes moot — anyone with `server.db` write access mints admins
forever, bypassing the documented "first admin via bootstrap" install
story. **Pick: (a) Existing user only** — raise `UserNotFoundError`
on missing target; recovery semantics honest; new-admin path stays
bootstrap+`admin_promote_user` (P22). ADR-0012 §am2 narrows the "or
new" clause.

**PB-B — `_assert_not_sole_admin` helper ships at P20 with no P20
consumer.** ADR-0012 names three call sites — all Phase 22. Reset-admin
itself never violates the zero-admin invariant (it only adds /
refreshes admins). Dead code in main between P20 ship and P22 ship
risks helper-signature drift against eventual P22 callers. **Pick: (b)
Defer the entire helper + `LastAdminError` class to Phase 22.** Phase 20
narrows from two Features to one. Precedent for narrowing: Phase 18
PB-27 (lift), Phase 16 PB-4c (deferral), Phase 23 (already narrowed).

**PB-C — Upsert mechanism: `INSERT OR REPLACE` vs ON CONFLICT vs
UPDATE-only (contingent on PB-A).** With PB-A=(a) existing-only, the
upsert collapses to plain `UPDATE users SET …`. **Pick: UPDATE-only.**
`UPDATE users SET password_hash=?, actor_role='admin', disabled=0
WHERE user_id=?` plus a `changes()` check; 0 rows affected → raise
`UserNotFoundError`. Preserves `created_at`; no FK cascade side-effects
on sessions (sessions get explicitly DELETEd in the same tx per PB-R).

### Round 2 — Audit shape + role guard + CLI shape (PB-D, PB-E, PB-G)

(PB-F — disabled-target handling — was raised in round 2 then subsumed
into PB-U at round 3 once role-guard semantics locked.)

**PB-D — Audit shape for killed sessions.** `kill_my_own_sessions`
(P19) precedent: 1× summary event + N× `EVT_LOGOUT`. Reset-admin's
session kills aren't logouts — they're admin-initiated evictions.
**Pick: (c) 1× `EVT_RESET_ADMIN` + N× `EVT_KILL_SESSION`.** Constant
already declared at Phase 18 (audit.py:85); reuse lifts its
first-fire from P22 → P20. Lets P21 audit reader differentiate
"user logged out" from "admin killed your session" without parsing
`extra_json.context`. ADR-0012 §am2 records the audit-event roster.

**PB-E — Target's existing `actor_role`: must be 'admin' or any
user gets promoted?** PB-A locked existence; silent on role. ADR-0012
§Decision wording ("Upserts the row with `role='admin'`") *could* be
read as silent-promotion-OK, but reset-admin then doubles as a
"promote arbitrary user to admin" backdoor — exactly the power that
Phase 22's `admin_promote_user` (gated by `CAN_MANAGE_USERS`) is
meant to control. **Pick: (a) Strict — target must already be admin.**
Else raise `NotAnAdminError` (new class, PB-N). The (rare) "I demoted
my only admin" foot-gun gets closed by P22's `_assert_not_sole_admin`
(PB-B); until then it's a known-deferred risk explicitly noted in §6
below.

**PB-G — CLI shape: positional vs flag; required vs prompt-fallback.**
ADR-0012 says `--user-id` flag. Bootstrap (P18) ships positional with
interactive prompt fallback. Recovery is destructive — deliberate is
better than convenient. **Pick: (c) Positional + REQUIRED, no prompt.**
`mindsos server reset-admin <user_id>` — Typer raises if missing; no
`typer.prompt()` fallback. Diverges from bootstrap by design.
ADR-0012 §am2 locks both the positional shape AND the no-prompt
deliberation as one revision item.

### Round 3 — Atomicity + error class shapes + disabled handling (PB-N, PB-O, PB-R, PB-U)

**PB-N — `NotAnAdminError` payload shape.** New class lands in
`mindsos_server/errors.py`. Caller has proof-of-authority (filesystem
access to `server.db`) — user-role enumeration is not a security
concern. **Pick: (a) `NotAnAdminError(target_user_id: str, actual_role:
str)`.** Informative; admin sees "you're trying to reset 'foo', who
is role='user'; use `admin_promote_user` instead". Beats minimal.

**PB-O — `UserNotFoundError` reuse vs new class.** Reset-admin's
"user_id doesn't exist" is not an auth failure. Reusing
`AuthFailedError(cause=UNKNOWN_USER)` ships the wrong public message
("auth failed") for an operator who attempted no auth. **Pick: (a)
New `UserNotFoundError(target_user_id: str)`** in errors.py. Pre-
positions for P22 admin verbs (`admin_demote_user` on missing target,
etc.) — those callers reuse the same class.

**PB-R — Transaction scope: UPDATE + DELETE atomicity.** UPDATE-only
path means sessions don't FK-cascade. If UPDATE commits and we crash
before DELETE, old tokens stay valid against the new password — a
*worse* state than pre-reset (old tokens minted under old password now
authenticate against new password; admin runs reset again, second admin
reports `sessions_killed=N` while first run silently leaked them).
**Pick: (b) Single transaction, DELETE-then-UPDATE order:** `DELETE
sessions WHERE user_id=? → UPDATE users SET … → INSERT N× audit rows
→ commit`. Atomic + intuitive read order ("kill the sessions, then
change the lock"). ADR-0012 §am2 §Consequences-style note locks the
ordering.

**PB-U — Disabled admin as reset-admin target.** ADR-0012 §Decision:
"fresh argon2 hash, `disabled=0`" — implies re-enable. With PB-E=(a)
strict-admin-only target, the disabled+admin case is the explicit
recovery scenario ("admin got disabled AND lost password"). **Pick:
(b) Conditional `EVT_ADMIN_ENABLE_USER` fire** IFF target was
disabled (in addition to `EVT_RESET_ADMIN`). Reuses P18-declared
constant; first-fire shifts P22 → P20 (mirroring PB-D's
EVT_KILL_SESSION shift). P21 audit reader sees clean
`EVT_ADMIN_ENABLE_USER` event for the disable→enable transition
independent of the password-rotation event.

### Round 4 — Forward-positioning + audit-reader convenience (PB-Z, PB-AA, PB-BB)

User explicitly authorized round 4 after round 3's saturation note.
Picks below are NOT correctness-critical — they pre-position the
`admin.py` module for Phase 22 and lock audit-row payload shapes so
the P21 audit reader doesn't have to special-case.

**PB-Z — Reset-admin helper module placement.** ADR-0012 doesn't
specify. Bootstrap's `_insert_first_admin` lives in `users.py`. Phase
22 will add `admin_demote_user`, `admin_disable_user`,
`admin_kill_session`, `hard_delete_user`. Picks: (a) extend `users.py`
(Phase 18 precedent); (b) new `mindsos_server/admin.py` at P20;
(c) extend users.py + split at P22. **Pick: (b)** — pre-positions the
admin module while it has one clean inhabitant; avoids P22 having to
split users.py + relocate reset_admin (which would invalidate P20
tests' import paths). Costs: one sentinel-paths entry + one
`__init__.py` export. No Dockerfile change (existing `COPY
mindsos_server/` picks up the new file as a directory copy).

**PB-AA — `EVT_KILL_SESSION` `extra_json.context` key value.** P19
`kill_my_own_sessions` used `extra={"context":
"kill_my_own_sessions"}` for its EVT_LOGOUT rows. **Pick: (a)
`extra={"session_id": sid, "context": "reset_admin"}`** — key
consistency with P19 wins over semantic precision (the alternative
"killer_verb" key would force the P21 audit reader to handle two
key names).

**PB-BB — `EVT_RESET_ADMIN` `extra_json` payload.** Picks: (a)
minimal `{"was_disabled": bool}`; (b) denormalized `{"was_disabled":
bool, "sessions_killed": N}`; (c) verbose including session_ids list.
**Pick: (b)** — single SELECT-by-event answers "how many sessions
were killed in the last reset of user X" without joining EVT_KILL_SESSION
rows. Free at write-time; no schema cost.

### Minor locks (no options needed)

Batched at the end of rounds 2-4; no plausible alternative survives
the picks above:

- **Audit actor format:** `actor=os_user` verbatim (from
  `pwd.getpwuid(os.getuid()).pw_name`), `target=user_id`. Mirrors
  Phase 18 `EVT_BOOTSTRAP` shape exactly. No "OS:" prefix; no
  `extra.auth="filesystem"` payload.
- **§am2 batching:** all Phase 20 documentary changes (PB-A + PB-D +
  PB-E + PB-G + PB-R + PB-U) into one ADR-0012 §amendment-2 entry.
  ADR-0013 not amended (audit-constant first-firers are impl-level).
  Phase 19's 3-change batching is the batching precedent.
- **No `--confirm` flag.** CLI invocation is itself the consent
  signal; OS-user audit row is the accountability mechanism. Matches
  Phase 19 logout precedent.
- **SELECT-then-DELETE race in `DELETE sessions WHERE user_id=?`:**
  same race as P19 `kill_my_own_sessions`; CLI-only product →
  concurrency is one-shell-per-invocation. Not opening a new
  vulnerability surface; deferred.
- **argon2id params injection:** `params: Argon2Params =
  PRODUCTION_PARAMS` kwarg on `reset_admin()`; `_TEST_FAST_PARAMS`
  threaded in tests. Mirrors `_insert_first_admin` convention.
- **Password reading:** reuse existing `_read_password_stdin()`
  helper in `mindsos_cli/commands/server.py` — already shipped at
  P18 for bootstrap / user-create. No new password-reading code.
- **CLI output:**
  - Plain success: `admin reset: user_id='foo'; sessions_killed=N`
    (+ `; re-enabled=true` if `was_disabled=true`)
  - `--json` success: `{"status": "reset", "user_id": "foo",
    "sessions_killed": N, "was_disabled": bool}`
  - Plain failure (UserNotFoundError / NotAnAdminError /
    ValueError): stderr `error: <message>`, exit 2
- **`LastAdminError` HTTP-409 mapping:** deferred with class itself
  to Phase 22 per PB-B. Phase 20 ships no HTTP transport (per
  PHASE_MAP §1).
- **Sandbox git separation:** per
  `feedback_sandbox_vs_mac_git_separation.md`, no `git
  add/commit/push` from sandbox. All git ops happen on Mac (user
  runs them); sandbox is Write/Edit-only for the file artifacts.
- **Test image rebuild discipline:** per
  `feedback_test_image_rebuild_after_source_change.md`, rebuild
  `mindsos-test` after `admin.py` lands. Linux tester runs the
  rebuild before `pytest tests/phase_20/`.

## §2. Final locks consolidated (13-pick reference)

| # | Pick | ADR cite / precedent |
|---|---|---|
| A | Existing user only; `UserNotFoundError` on missing | ADR-0012 §am2 (narrows "or new") |
| B | Defer `_assert_not_sole_admin` + `LastAdminError` to Phase 22 | Phase 18 PB-27 narrowing precedent |
| C | UPDATE-only (contingent on A) | ADR-0012 §am2 |
| D | 1× `EVT_RESET_ADMIN` + N× `EVT_KILL_SESSION` | ADR-0012 §am2 + ADR-0013 (first-fire shift P22→P20) |
| E | Strict — target must already be admin; `NotAnAdminError` else | ADR-0012 §am2 |
| G | Positional + REQUIRED, no prompt | ADR-0012 §am2 (diverges from bootstrap) |
| N | `NotAnAdminError(target_user_id, actual_role)` | filesystem-access threat model |
| O | New `UserNotFoundError(target_user_id)` in errors.py | pre-positions for P22 admin verbs |
| R | Single tx, DELETE-then-UPDATE order | ADR-0012 §am2 §Consequences |
| U | Conditional `EVT_ADMIN_ENABLE_USER` IFF disabled target | ADR-0013 (first-fire shift P22→P20) |
| Z | New `mindsos_server/admin.py`; reset_admin lives there | Phase 22 pre-positioning |
| AA | `extra={"session_id": sid, "context": "reset_admin"}` | P19 key-name consistency |
| BB | `EVT_RESET_ADMIN` extra_json includes `sessions_killed: N` | P21 reader avoids join/count |

## §3. Cross-chat dependencies

### Backward (Phase 20 inherits from earlier phases)

- **Phase 18 `mindsos_server/` package** — `users.verify` (PB-13),
  `users.insert_user` / `users._insert_first_admin` / `users.count_admins`
  (PB-9/PB-24/PB-29), `Argon2Params` + `PRODUCTION_PARAMS` +
  `_TEST_FAST_PARAMS` + `hash_password` / `verify_password` (PB-14),
  `_db.open_db()` (PB-19), `write_audit()` (PB-34), `_now_utc_iso()`
  (PB-35), `_SCHEMA_VERSION` framework (PB-2), audit-constant roster
  including `EVT_RESET_ADMIN` + `EVT_KILL_SESSION` +
  `EVT_ADMIN_ENABLE_USER` (PB-34).
- **Phase 18 `mindsos_cli/commands/server.py`** — `_resolve_and_open`,
  `_ensure_migrated`, `_read_password_stdin` helpers; `server_app`
  Typer group; bootstrap verb pattern (positional `user_id` Argument).
  Reset-admin reuses these.
- **Phase 18 audit-row shape lock** —
  `(id, ts, actor_user, event, target_user, extra_json)`. Phase 20
  writes through `write_audit()` unchanged. `extra_json` is
  open-schema (PB-34).
- **Phase 18 `_insert_first_admin` actor pattern** — OS user from
  `pwd.getpwuid(os.getuid()).pw_name`. Phase 20 mirrors verbatim
  for `EVT_RESET_ADMIN` actor.
- **Phase 19 `sessions` table** — 5-column shape per PB-10
  (`session_id`, `user_id`, `token_hash`, `created_at`,
  `last_seen_at`); `idx_sessions_user_id` index per ADR-0004 §am1.
  `DELETE FROM sessions WHERE user_id=?` is Phase 20's hot path.
  `sessions.user_id` FK has `ON DELETE CASCADE` but Phase 20 doesn't
  trigger it (UPDATE on users, not DELETE).
- **Phase 19 `kill_my_own_sessions` pattern** — verify → audit-on-fail
  → SELECT session_ids → DELETE → per-row audit → commit. Phase 20's
  reset-admin body mirrors the DELETE+per-row-audit shape (no verify
  step; OS-user authority instead).
- **`feedback_pushback_format_with_picks.md`** — every pushback
  ended with a pick (4 rounds × 13 total picks).
- **`feedback_phase_baseline_literal_audit.md`** — Phase 19 shipped
  `_SCHEMA_VERSION=2`; Phase 20 does NOT bump (no new tables). Phase
  19 dynamic-baseline test pattern (`TestAll6PkgsAtCurrentPhase`)
  handles the `+phase19 → +phase20` bump automatically.
- **`feedback_pre_impl_probe_check_existing_modules.md`** — probe
  confirmed `reset_admin` / `_assert_not_sole_admin` / `LastAdminError`
  not yet shipped; only comment references in `_schema.py:184` +
  `__init__.py:60` + `commands/server.py:190`. Phase 20 lands the
  function definitions; comment references are forward-looking and
  remain correct.
- **`feedback_l1_api_signature_probe_before_writing_tests.md`** —
  probe checked `count_admins` signature, `_insert_first_admin`
  signature, `kill_my_own_sessions` audit-write pattern, `write_audit`
  kwarg shape (`actor=`, `event=`, `target=`, `extra=`). Phase 20
  tests model the same.

### Forward (Phase 20 → later phases)

- **Phase 21 (audit reader)** — consumes `EVT_RESET_ADMIN` +
  `EVT_KILL_SESSION` (with `extra.context="reset_admin"`
  discriminator) + `EVT_ADMIN_ENABLE_USER` rows written by Phase 20.
  PB-BB's `sessions_killed` field on `EVT_RESET_ADMIN.extra_json`
  lets P21 answer "how many sessions were killed in user X's last
  reset" without a join.
- **Phase 22 (admin ops)** — lands `_assert_not_sole_admin` helper +
  `LastAdminError` class (PB-B deferral). Wires the helper into
  `admin_demote_user`, `admin_disable_user`, `hard_delete_user`.
  Lands `admin_promote_user` (the "user → admin" path that Phase 20
  refuses per PB-E). Lands `admin_kill_session` (second consumer of
  `EVT_KILL_SESSION` — Phase 20 is the first). All four admin_*
  verbs land in `mindsos_server/admin.py` (PB-Z pre-positions the
  module).
- **Phase 22 admin verbs** — reuse `UserNotFoundError` (PB-O)
  + `NotAnAdminError` (PB-N) where target-validation parallels
  reset-admin's. Same errors.py classes; no new exception types
  needed for those gates.

## §4. ADR delta at Phase 20 ship

One ADR amendment. ADR-0012 already has §amendment-1 (Phase 18 ship
— bootstrap lift); Phase 20's §amendment-2 batches six documentary
changes into one revision entry per Phase 19 batching precedent.

| ADR | Action | Reason |
|---|---|---|
| **0012** | §amendment-2 | Six changes batched at Phase 20 ship: (a) reset-admin target narrowed to existing user_id only (PB-A); (b) audit-event roster locked at `1× EVT_RESET_ADMIN + N× EVT_KILL_SESSION + conditional 1× EVT_ADMIN_ENABLE_USER` (PB-D + PB-U); (c) target must already be `actor_role='admin'` else `NotAnAdminError` (PB-E); (d) CLI shape positional + REQUIRED, no prompt fallback (PB-G); (e) transaction order DELETE-then-UPDATE locked in §Consequences-style note (PB-R); (f) `_assert_not_sole_admin` helper + `LastAdminError` first-construction shifts to Phase 22 (PB-B). Status: documentary — §Decision's "lock-out recovery" thesis preserved; only the mechanism specifics shift to match the CLI-only product + the strict separation between reset-admin (rotate creds) and admin_promote_user (escalate role). |

ADR-0013 is **not** amended. PB-D's `EVT_KILL_SESSION` first-fire
shift (P22 → P20) and PB-U's `EVT_ADMIN_ENABLE_USER` first-fire shift
(P22 → P20) are audit-constant-usage events, not ADR-level decisions
— the constants are pre-declared at Phase 18 per PB-34 and any verb
may use them. ADR-0012 §am2 records both shifts in passing.

## §5. Implementation references

```
mindsos_server/                        # extends Phase 18 pkg; PB-Z adds admin.py
├── __init__.py                        # +exports: reset_admin, NotAnAdminError, UserNotFoundError
├── admin.py                           # NEW (PB-Z): reset_admin(conn, user_id, password, *, params, os_user) -> ResetAdminResult
├── errors.py                          # MODIFIED: +NotAnAdminError (PB-N), +UserNotFoundError (PB-O)
├── _schema.py                         # UNCHANGED (no new tables; _SCHEMA_VERSION stays 2)
├── users.py                           # UNCHANGED (count_admins / verify / _insert_first_admin already shipped at P18)
├── sessions.py                        # UNCHANGED (DELETE SQL inlined in admin.py, no helper extraction at P20)
└── (all other Phase 18+19 files unchanged)

mindsos_cli/commands/server.py         # MODIFIED: +reset_admin Typer verb (positional user_id, stdin password, --json)

mindsos_cli/_sentinel_paths.py         # +mindsos_server/admin.py runtime sentinel

tests/phase_20/                        # ~7-8 test files
├── test_reset_admin_happy_path.py     # existing admin, password rotated, was_disabled=false, sessions=0
├── test_reset_admin_user_not_found.py # missing user_id → UserNotFoundError (PB-A + PB-O)
├── test_reset_admin_not_an_admin.py   # actor_role='user' target → NotAnAdminError (PB-E + PB-N)
├── test_reset_admin_disabled_admin.py # was_disabled=true; re-enabled; EVT_ADMIN_ENABLE_USER fires (PB-U)
├── test_reset_admin_session_kills.py  # N=0, N=1, N=multi; per-row EVT_KILL_SESSION with context="reset_admin" (PB-D + PB-AA)
├── test_reset_admin_atomicity.py      # mock failure mid-tx; rollback verifies no partial state (PB-R)
├── test_reset_admin_cli.py            # CLI verb: positional required (no prompt — PB-G); stdin password; --json shape (PB-BB)
└── test_reset_admin_audit_actor.py    # actor=os_user verbatim; pwd.getpwuid mock; mirrors P18 bootstrap shape

docs/usage/server/bootstrap.md         # AMENDED: +reset-admin section (per master prompt); last_confirmed_phase: 20

# Modified outside mindsos_server/ + tests/:
mindsos_cli/_sentinel_paths.py         # +mindsos_server/admin.py runtime sentinel
docker-compose.yml                     # phase19→phase20 tag bump
manifest.toml                          # phase = "20" + version = "0.0.0+phase20"
confirmation_docs/PHASE_MAP.md         # §20 row Features narrowed to 1 (per PB-B); §22 row inherits PB-B deferrals
docs/decisions/adr/0012-…              # §am2 (6-change batch — PB-A + PB-D + PB-E + PB-G + PB-R + PB-U)

# Version bump +phase19 → +phase20 across 9 sites:
mindsos_core/__init__.py
mindsos_knowledge/__init__.py
mindsos_admin/__init__.py
mindsos_instances/__init__.py
mindsos_cli/__init__.py
mindsos_server/__init__.py
pyproject.toml [project] version
docker-compose.yml image tags (3 occurrences: mindsos / mindsos-test / etc.)
manifest.toml [mindsos] version + [mindsos] phase

# Doctor self-test (6-pkg parity) unchanged — auto-detects new version literal via
# Phase 19 TestAll6PkgsAtCurrentPhase pattern (manifest.toml [mindsos] version
# as source-of-truth).
```

### `reset_admin` signature reference

```python
# mindsos_server/admin.py

from dataclasses import dataclass
from typing import Optional
import sqlite3

from mindsos_server._argon2 import Argon2Params, PRODUCTION_PARAMS, hash_password
from mindsos_server.errors import NotAnAdminError, UserNotFoundError
from mindsos_server.audit import (
    EVT_RESET_ADMIN, EVT_KILL_SESSION, EVT_ADMIN_ENABLE_USER, write_audit,
)


@dataclass(frozen=True)
class ResetAdminResult:
    user_id: str
    sessions_killed: int
    was_disabled: bool


def reset_admin(
    conn: sqlite3.Connection,
    user_id: str,
    new_password: str,
    *,
    os_user: str,
    params: Argon2Params = PRODUCTION_PARAMS,
) -> ResetAdminResult:
    """
    Lock-out recovery per ADR-0012 §am2.

    Requires target user to exist (UserNotFoundError) AND already be
    actor_role='admin' (NotAnAdminError). Rotates password (fresh
    argon2id salt), re-enables if disabled, kills all active sessions
    for the target, audits in a single SQLite transaction per PB-R
    (DELETE sessions → UPDATE users → INSERT audit rows → commit).
    """
    # 1. Probe target row (existence + role + disabled state).
    row = conn.execute(
        "SELECT actor_role, disabled FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        raise UserNotFoundError(user_id)
    actual_role, disabled_int = row[0], int(row[1])
    if actual_role != "admin":
        raise NotAnAdminError(user_id, actual_role)
    was_disabled = bool(disabled_int)

    # 2. Single transaction: DELETE sessions → UPDATE users → INSERT audits → commit.
    session_ids = [
        r[0] for r in conn.execute(
            "SELECT session_id FROM sessions WHERE user_id = ?", (user_id,)
        ).fetchall()
    ]
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    new_hash = hash_password(new_password, params=params)
    conn.execute(
        "UPDATE users SET password_hash = ?, disabled = 0 WHERE user_id = ?",
        (new_hash, user_id),
    )

    # 3. Audit: EVT_RESET_ADMIN (summary) + N× EVT_KILL_SESSION + conditional EVT_ADMIN_ENABLE_USER.
    for sid in session_ids:
        write_audit(
            conn,
            actor=os_user,
            event=EVT_KILL_SESSION,
            target=user_id,
            extra={"session_id": sid, "context": "reset_admin"},
        )
    if was_disabled:
        write_audit(
            conn,
            actor=os_user,
            event=EVT_ADMIN_ENABLE_USER,
            target=user_id,
            extra={"context": "reset_admin"},
        )
    write_audit(
        conn,
        actor=os_user,
        event=EVT_RESET_ADMIN,
        target=user_id,
        extra={"was_disabled": was_disabled, "sessions_killed": len(session_ids)},
    )
    conn.commit()

    return ResetAdminResult(
        user_id=user_id,
        sessions_killed=len(session_ids),
        was_disabled=was_disabled,
    )
```

### `NotAnAdminError` + `UserNotFoundError` reference

```python
# mindsos_server/errors.py (additions)

class UserNotFoundError(Exception):
    """
    Raised when an admin verb targets a user_id that does not exist in
    `users`. Phase 20 first-fires from reset-admin (PB-O); Phase 22
    admin verbs reuse.
    """

    def __init__(self, target_user_id: str) -> None:
        super().__init__(f"user not found: {target_user_id!r}")
        self.target_user_id = target_user_id


class NotAnAdminError(Exception):
    """
    Raised by reset-admin when the target user_id exists but has
    actor_role != 'admin' (PB-E + PB-N). Filesystem-access threat
    model: target's actual role is included in the public message
    (no enumeration concern — caller already has server.db read access).
    """

    def __init__(self, target_user_id: str, actual_role: str) -> None:
        super().__init__(
            f"target user {target_user_id!r} is not an admin "
            f"(actor_role={actual_role!r}); use `mindsos server "
            f"admin promote-user` (Phase 22) to escalate"
        )
        self.target_user_id = target_user_id
        self.actual_role = actual_role
```

## §6. Scope boundaries (out-of-scope at Phase 20 ship)

- **`_assert_not_sole_admin` helper** — Phase 22 per PB-B. Phase 20
  has no caller; helper without consumer invites drift.
- **`LastAdminError` class** — Phase 22 per PB-B (bundled with the
  helper).
- **`admin_promote_user` (user → admin escalation)** — Phase 22.
  Until P22 ships, the "I demoted my only admin" foot-gun gap exists
  — but `_assert_not_sole_admin` (P22) closes the demotion path that
  would create the gap, so the gap is theoretical at P20 unless an
  operator hand-edits `server.db`. Documented as a known-deferred
  risk for the install guide.
- **`admin_demote_user` / `admin_disable_user` / `hard_delete_user`** —
  Phase 22. These are the `_assert_not_sole_admin` consumers.
- **`admin_kill_session`** — Phase 22. Phase 20 first-fires
  `EVT_KILL_SESSION`; Phase 22 is the second user.
- **`admin_query_audit` reader + `CAN_VIEW_AUDIT_LOG` enforcement** —
  Phase 21.
- **HTTP transport** — no roadmap; CLI-only product per Phase 18 §6
  + PHASE_MAP §1.
- **`LastAdminError` HTTP-409 mapping** — Phase 22 (with class
  itself).
- **Promotion of non-admin to admin via reset-admin** — refused per
  PB-E. Use `admin_promote_user` (P22).
- **`reset-admin` on a new user_id (mint admin from scratch)** —
  refused per PB-A. Use `bootstrap` (P18) for first admin; subsequent
  admins via `admin_promote_user` (P22).
- **`reset-admin --confirm` flag** — not shipped. CLI invocation is
  itself the consent signal; OS-user audit row is the accountability
  mechanism. Matches Phase 19 logout precedent.
- **`session_from_token` invalidation feedback to the killed user** —
  out of scope. Killed sessions raise `InvalidSessionError(cause=
  NOT_FOUND)` on the killed user's next `mindsos server whoami` /
  CLI call; that user can re-login (assuming reset-admin gave them
  the new password out-of-band).
- **Audit retention / pruning of `EVT_RESET_ADMIN` rows** — operator
  responsibility per ADR-0013 §Consequences ("Audit table growth is
  unbounded by design").

## §7. Design saturation note

Four rounds (13 picks total: round 1 = 3, round 2 = 3, round 3 = 4,
round 4 = 3). Phase 20 narrowness justified a smaller ledger than
Phase 18 (38 picks / 4 rounds) and matches Phase 19 (15 picks / 3
rounds) in density. Round 4 was explicitly flagged at the close of
round 3 as forward-positioning + audit-reader convenience (not
correctness); user authorized round 4 anyway.

Implementation proceeds per the task list. Any new pushback surfaced
during implementation is recorded as a B-20-T* hotfix in the
confirmation doc, not a retroactive PB-NN entry (Phase 18 / 19
precedent).
