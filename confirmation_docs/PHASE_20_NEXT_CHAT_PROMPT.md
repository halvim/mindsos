══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 20 (Server: reset-admin + last-admin protection)
══════════════════════════════════════════════════════════════════════

This prompt is intentionally lean. The phase chat reads files for
context; this prompt only points at them + locks process expectations.

Project: MindsOS — folder `halvim_mindsos/` under
`/Layered Intelligence/`. Branch off `origin/main` tip.

ROLE: Critical design reviewer + implementer. Read the project-level
CLAUDE.md at `/Layered Intelligence/CLAUDE.md` AND the MindsOS
sub-project CLAUDE.md if present. Follow strict picks-per-pushback
discipline (each pushback ends with a pick; final picks summary at
the end of every multi-pushback round; see
`feedback_pushback_format_with_picks.md`).

Phase 20 scope is locked at PHASE_MAP §Phase 20 row, NARROWED at Phase
18 PB-27 (bootstrap CLI verb lifted to Phase 18). Read the row; do not
re-derive scope from training.

══════════════════════════════════════════════════════════════════════
REQUIRED READING (in this order)
══════════════════════════════════════════════════════════════════════

1. **`MEMORY.md`** — auto-loaded at chat start. Every `feedback_*`
   entry is a hard rule. Pay special attention to:
   * `feedback_pushback_format_with_picks.md`
   * `feedback_pre_impl_probe_check_existing_modules.md`
   * `feedback_l1_api_signature_probe_before_writing_tests.md`
   * `feedback_phase_baseline_literal_audit.md`
   * `feedback_test_image_rebuild_after_source_change.md`
   * `feedback_stale_local_tag_silent_overwrite_failure.md`
   * `feedback_batch_fix_dont_iterate.md`
   * `feedback_sandbox_vs_mac_git_separation.md`
   * `user_two_machine_setup.md` (Mac/Linux split + commands)

2. **`halvim_mindsos/confirmation_docs/PHASE_MAP.md`** §0 (load-bearing
   read rule) + §1 (settled cross-cutting decisions — read in full) +
   §Phase 18 (bootstrap CLI lifted here) + §Phase 19 (most recent
   shipped) + §Phase 20 (own row — narrowed scope source) + §Phase 21
   (audit reader; confirm Phase 20 doesn't cross into P21).

3. **`halvim_mindsos/confirmation_docs/PHASE_19_DESIGN_LOG.md`** —
   most recent design log. Read §0 scope summary + §2 final locks
   table + §3 cross-chat dependencies (Forward subsection — Phase 19
   → Phase 20 deltas) + §4 ADR delta + §6 out-of-scope. This is the
   durable contract for what Phase 20 inherits.

4. **`halvim_mindsos/confirmation_docs/PHASE_19_CONFIRMED.md`** —
   ground truth for the actually-shipped state at Phase 19 tag.
   Tester notes section captures any B-19-T* hotfixes + test counts
   + manual smoke. If the design log and the confirmation doc
   disagree, the confirmation doc wins (it's post-impl evidence).

5. **ADRs** at `/Layered Intelligence/docs/decisions/adr/`. Read in
   full at first probe — Phase 20 consumes:
   * **ADR-0012** (bootstrap + reset-admin + last-admin protection).
     Phase 18 §amendment-1 lifted bootstrap to P18; Phase 20 ships
     `reset-admin` + `_assert_not_sole_admin` helper.
   * **ADR-0013** (audit constants). `EVT_RESET_ADMIN` ships at
     Phase 18 per PB-34; Phase 20 fires it. New `EVT_*` for
     last-admin-removal-blocked may be needed (phase chat picks).
   * **ADR-0002** (capability model). Phase 20 may touch USER_CAPS /
     ADMIN_CAPS if last-admin-protection introduces new capability;
     more likely it does not (Phase 18 PB-12 USER_CAPS strictly empty
     still holds — Proposed-status caps wait).
   * **ADR-0003** (password scheme). Phase 20 reset-admin re-hashes
     with fresh argon2id salt per ADR-0012 §Decision; kills sessions
     for that user (DELETE FROM sessions WHERE user_id = ?). The
     sessions table shipped at Phase 19 is the consumer.
   * **ADR-0005 §am1** (Phase 19) — kill-on-reset-admin operates
     against the Phase 19 sessions table.

══════════════════════════════════════════════════════════════════════
PRE-IMPL PROBE (run BEFORE any design pushbacks)
══════════════════════════════════════════════════════════════════════

```
cd halvim_mindsos
# Verify Phase 19 squashed + tagged at main tip.
git fetch origin && git log --oneline origin/main | head -5
git rev-parse phase-19-confirmed 2>&1 | head -1

# Verify Phase 19 surfaces intact.
ls mindsos_server/
grep -n "_SCHEMA_VERSION" mindsos_server/_schema.py        # expect: 2
grep -n "EVT_RESET_ADMIN" mindsos_server/audit.py          # should exist (P18)
grep -n "class Session" mindsos_server/session.py
ls mindsos_server/sessions.py                              # Phase 19 — should exist

# Verify nothing Phase 20-shaped already shipped.
grep -rn "reset_admin\|_assert_not_sole_admin\|LastAdminError" \
    mindsos_server/ 2>/dev/null | head -10

# Verify the bootstrap → login → reset chain.
grep -n "bootstrap\|reset" mindsos_cli/commands/server.py | head -20

# Version baseline.
grep -rn '__version__ = "0\.0\.0+phase' --include="*.py" mindsos_*/__init__.py
```

If `mindsos_server/admin.py` or anything `reset_admin`-shaped already
exists, surface as a reframe pushback (Phase 15b / Phase 17 retirement
precedents).

══════════════════════════════════════════════════════════════════════
LIKELY PUSHBACK SURFACES (probe before locking scope)
══════════════════════════════════════════════════════════════════════

Each pushback ends with a pick. Final round closes with a Picks
summary.

1. **`reset-admin` CLI shape — interactive prompt vs flags.** ADR-0012
   §Decision says "Accepts `--user-id` and a new password." Phase 19
   PB-8 / PB-5 pattern: no `--password` flag; passwords via stdin.
   Phase 20 `reset-admin` should follow the same convention — stdin
   only, no `--password`. `--user-id` as positional matches the
   `bootstrap [<user_id>]` shape.

2. **`reset-admin` upsert semantics — update existing or insert if
   missing?** ADR-0012 §Decision says "Upserts the row with
   `role='admin'`, fresh argon2 hash, `disabled=0`." Phase 20 picks:
   (a) literal upsert (INSERT OR REPLACE) — replaces row entirely,
   loses created_at; (b) conditional UPDATE then INSERT — preserves
   created_at on existing rows; (c) only allow on existing rows
   (raise on missing — admin must use bootstrap for new admins).

3. **Last-admin protection placement — helper module or inline in
   each verb?** ADR-0012 §Decision names `_assert_not_sole_admin()`
   as a single helper. Phase 20 must wire it into Phase 22's
   `admin_demote_user`, `admin_disable_user`, `hard_delete_user`
   call sites — but Phase 22 hasn't shipped. Phase 20 picks: (a) ship
   helper now + Phase 22 wires; (b) ship helper + a placeholder
   Phase 20 verb that exercises it (e.g., a debug `mindsos server
   assert-not-sole-admin <user_id>` command — overkill); (c) defer
   helper entirely to Phase 22.

4. **`EVT_RESET_ADMIN` actor — OS user or session.user_id?** ADR-0012
   §Decision: "Writes an `AUDIT_RESET_ADMIN` row with the calling OS
   user from `pwd.getpwuid(os.getuid())`." Phase 18 PB-27 generalized
   this for `EVT_BOOTSTRAP`. Phase 20 follows the same pattern —
   reset-admin runs without a Session by definition (lock-out
   recovery), so OS user is the only identity available.

5. **Reset-admin killing sessions for the target user.** ADR-0012
   §Decision: "Kills every active session for that user." Phase 19
   shipped the `sessions` table; Phase 20 reset-admin issues
   `DELETE FROM sessions WHERE user_id = ?` for the reset target +
   per-row `EVT_LOGOUT` audit (mirrors Phase 19's
   `kill_my_own_sessions` pattern).

6. **`LastAdminError` exception shape — public message + payload.**
   ADR-0012 §Decision says "raises `LastAdminError` (HTTP 409) if
   target is the sole admin." Phase 20 picks the payload shape +
   class location (`mindsos_server.errors`). Phase 19 conventions
   suggest: `LastAdminError(target_user_id: str)`; public message
   includes target + a hint about reset-admin.

7. **CLI verbs at Phase 20.** Only `reset-admin` ships at Phase 20
   (per the Phase 18 PB-27 narrowing). Phase 22 ships the admin
   verbs that consume `_assert_not_sole_admin`. Confirm scope is just
   the reset verb at this phase.

8. **Idempotency / re-run safety of `reset-admin`.** Unlike bootstrap
   (which short-circuits if admin exists), reset-admin is destructive
   by design — each call rotates the password + kills sessions. No
   idempotency check; running it twice means the second password
   wins. Phase 20 picks the messaging shape (e.g., the CLI confirmation
   should explicitly say "password rotated; N sessions killed").

══════════════════════════════════════════════════════════════════════
PROCESS DISCIPLINE
══════════════════════════════════════════════════════════════════════

Per `user_two_machine_setup.md` + PHASE_MAP §1 amended at Phase 18:

* **Mac**: code editing (Claude session), `git add/commit/push`,
  `gh pr create`, `gh pr merge --squash`, final `git tag` + push.
  Mac has NO docker. Mac Python 3.9.6 — do NOT `pip install -e .`
  on Mac.
* **Linux**: `git pull`, `docker compose --profile test build
  mindsos-test` (pre-build to avoid timeout), all `docker compose
  run --rm mindsos-test pytest ...` runs, all `docker compose run
  --rm mindsos <verb>` CLI exploration.
* **confirm-phase**: either host venv (canonical) OR docker with
  bind-mount `-v "$(pwd)/confirmation_docs:/app/confirmation_docs"`
  (Phase 18 B-18-T3-bindmount lesson — without the `-v`, the doc
  is written inside the container and lost on `--rm`). PHASE_MAP
  §1 row reflects this.

Branch: `phase-20` off `origin/main` tip. Notes: `notes-phase-20.md`
at repo root. Version bump `+phase19 → +phase20` across 9 sites
(6 pkg `__init__.py` + pyproject + docker-compose + manifest.toml).
Tag `phase-20-confirmed` AFTER squash-merge only; verify
`git rev-parse phase-20-confirmed` returns "unknown" BEFORE creating.

Phase 19 ADR amendments at ship: 0003 / 0004 / 0005 / 0011 / 0013
(see `confirmation_docs/PHASE_19_DESIGN_LOG.md` §4). Phase 20 may
amend ADR-0012 §amendment-2 (after Phase 18 §amendment-1's bootstrap
lift) for the reset-admin specifics — phase chat decides at design
time.

══════════════════════════════════════════════════════════════════════
FIRST RESPONSE EXPECTATIONS
══════════════════════════════════════════════════════════════════════

1. Confirm cited files read; report any missing.
2. Run the pre-impl probe; report findings.
3. Surface 1-3 pre-design pushbacks (with picks) from §Likely
   pushback surfaces OR from the probe.
4. Ask the single highest-value missing-constraint question.

DO NOT write code in the first response. Phase 18's 4-round + Phase
19's 3-round design pushback ledger pattern is the shape this project
favors — sign off the architecture first, then implement. Phase 20 is
narrower in scope than 18 / 19 — likely 2-3 rounds suffice.

══════════════════════════════════════════════════════════════════════
EXIT CRITERIA
══════════════════════════════════════════════════════════════════════

Phase 20 squash-merges to main; `phase-20-confirmed` tag pushed
AFTER merge; `release.yml` green; GitHub Release created. Phase
20 writes `confirmation_docs/PHASE_21_NEXT_CHAT_PROMPT.md` as
exit artifact (Phase 21 = "Server: audit log" — admin_query_audit
reader + CAN_VIEW_AUDIT_LOG enforcement; consumes audit table
already shipped at Phase 18).
══════════════════════════════════════════════════════════════════════
