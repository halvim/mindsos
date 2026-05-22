══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 22 (Server: admin ops)
══════════════════════════════════════════════════════════════════════

This prompt is intentionally lean. The phase chat reads files for
context; this prompt only points at them + locks process expectations.

Project: MindsOS — folder `halvim_mindsos/` under
`/Layered Intelligence/`. Branch off `origin/main` tip
(currently `d90f752` Phase 21 squash; tag `phase-21-confirmed`
resolves to the same SHA).

ROLE: Critical design reviewer + implementer. Read the project-level
CLAUDE.md at `/Layered Intelligence/CLAUDE.md` AND the MindsOS
sub-project CLAUDE.md if present. Follow strict picks-per-pushback
discipline (each pushback ends with a pick; final picks summary at
the end of every multi-pushback round; see
`feedback_pushback_format_with_picks.md`).

Phase 22 scope is locked at PHASE_MAP §Phase 22 row. Read the row;
do not re-derive scope from training. Phase 22 is wider than 19/20/21
(5+ verbs + the long-deferred PB-B helper from Phase 20) — expect
4-5 design rounds, possibly 30+ picks.

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
   * `feedback_smoke_harness_host_native.md` (NEW @ Phase 21 — host-native
     is the default smoke harness; `docker compose run --rm` has no
     `~/.mindsos/` mount)
   * `user_two_machine_setup.md` (Mac/Linux split + commands)

2. **`halvim_mindsos/confirmation_docs/PHASE_MAP.md`** §0 (load-bearing
   read rule) + §1 (settled cross-cutting decisions — read in full) +
   §Phase 19 / §Phase 20 / §Phase 21 (most-recent context — Phase 21
   shipped `_require_or_audit` + `PermissionDeniedError` + `EVT_AUDIT_QUERY`;
   Phase 20 ships `admin.py` module + `UserNotFoundError` +
   `NotAnAdminError`) + §Phase 22 (own row — scope source) + §Phase 23
   (snapshot/promotion infra — confirm Phase 22 doesn't cross).

3. **`halvim_mindsos/confirmation_docs/PHASE_21_DESIGN_LOG.md`** —
   most recent design log. Read §0 scope summary + §2 final locks
   table (20-pick reference; PB-6 + PB-8 + PB-9 + PB-13 patterns
   that Phase 22 verbs will reuse) + §3 cross-chat dependencies
   Forward subsection (Phase 22 inheritances) + §4 ADR delta + §6
   out-of-scope.

4. **`halvim_mindsos/confirmation_docs/PHASE_20_DESIGN_LOG.md`** §1
   round 1 PB-B + §6 out-of-scope — Phase 20's deferral of
   `_assert_not_sole_admin` + `LastAdminError` to Phase 22, AND Phase
   20's documented "known-deferred risk" of the demote-only-admin
   foot-gun that Phase 22 closes.

5. **`halvim_mindsos/confirmation_docs/PHASE_21_CONFIRMED.md`** —
   ground truth for what shipped at Phase 21 tag. Tester notes
   captures B-21-T1 hotfix (read-then-write semantic) + the
   host-native smoke harness convention.

6. **ADRs** at `/Layered Intelligence/docs/decisions/adr/`. Read in
   full at first probe — Phase 22 consumes:
   * **ADR-0012** (bootstrap + last-admin) — §am1 (bootstrap CLI lifted
     to P18) + §am2 (Phase 20 6-clause batch; PB-B explicitly defers
     `_assert_not_sole_admin` to Phase 22). Phase 22 ships the helper +
     `LastAdminError` + wires all three call sites (`admin_demote_user`,
     `admin_disable_user`, `hard_delete_user`).
   * **ADR-0002** (capabilities) + §am1. Phase 22 first-consumes
     `CAN_MANAGE_USERS` (promote/demote/disable/enable) +
     `CAN_KILL_SESSION` (admin_kill_session) +
     `CAN_HARD_DELETE_ARCHIVED` (hard_delete_user) +
     `CAN_READ_OTHER_LOCALS` (cross-user read — if Phase 22 lands it;
     see §22 row).
   * **ADR-0008** (cross-user reads, no flush). Phase 22 lands the
     refcount-install entry-point per §22 row IF the design chat
     keeps it in scope; narrowing to a follow-up phase is a real
     pushback surface (see §Likely pushbacks below).
   * **ADR-0013** + §am1 + §am2 (audit + test shim). Phase 22 reuses
     `_require_or_audit(conn, session, capability, *, verb)` from
     Phase 21 PB-6 — 5+ verbs route through it. Each verb names its
     own happy-path audit constant; the constants are pre-declared at
     Phase 18 PB-34 (`EVT_ADMIN_PROMOTE_USER`, `EVT_ADMIN_DEMOTE_USER`,
     `EVT_ADMIN_DISABLE_USER`, `EVT_HARD_DELETE_USER`, `EVT_KILL_SESSION`,
     `EVT_CROSS_USER_READ_INSTALL`). `EVT_KILL_SESSION` first-fired at
     Phase 20 (reset-admin); Phase 22 is second consumer.
     `EVT_ADMIN_ENABLE_USER` also second consumer (first-fired
     conditional at Phase 20).
   * **ADR-0010** (layer isolation). Phase 22 is L0 only.

══════════════════════════════════════════════════════════════════════
PRE-IMPL PROBE (run BEFORE any design pushbacks)
══════════════════════════════════════════════════════════════════════

```
cd halvim_mindsos
# Verify Phase 21 squashed + tagged at main tip.
git fetch origin && git log --oneline origin/main | head -5
git rev-parse phase-21-confirmed 2>&1 | head -1

# Verify Phase 21 surfaces intact.
ls mindsos_server/authz.py mindsos_server/admin.py
grep -n "_require_or_audit\|PermissionDeniedError" mindsos_server/authz.py mindsos_server/errors.py | head -10
grep -n "admin_query_audit\|AuditRow" mindsos_server/admin.py | head -10
grep -n "EVT_AUDIT_QUERY" mindsos_server/audit.py

# Verify Phase 20 admin.py shape intact (Phase 22 extends it).
grep -n "^def reset_admin\|^class ResetAdminResult" mindsos_server/admin.py | head -5

# Verify Phase 20-era errors intact (Phase 22 reuses).
grep -n "UserNotFoundError\|NotAnAdminError" mindsos_server/errors.py | head -10

# Verify Phase 22 surfaces NOT yet shipped.
grep -rn "_assert_not_sole_admin\|LastAdminError\|admin_promote_user\|admin_demote_user\|admin_disable_user\|admin_enable_user\|admin_kill_session\|hard_delete_user" \
    mindsos_server/ mindsos_cli/ 2>/dev/null | grep -v "^Binary\|\.pyc" | head -30

# Verify the EVT_ constants Phase 22 will first-fire are pre-declared at P18.
grep -n "^EVT_ADMIN_PROMOTE_USER\|^EVT_ADMIN_DEMOTE_USER\|^EVT_ADMIN_DISABLE_USER\|^EVT_HARD_DELETE_USER\|^EVT_CROSS_USER_READ_INSTALL" mindsos_server/audit.py

# Verify ADR-0008 cross-user read scope — if Phase 22 includes it.
ls "/Layered Intelligence/docs/decisions/adr/0008-cross-user-reads-no-flush.md" && wc -l "/Layered Intelligence/docs/decisions/adr/0008-cross-user-reads-no-flush.md"

# Verify count_admins helper exists (Phase 22's _assert_not_sole_admin will use it).
grep -n "^def count_admins" mindsos_server/users.py

# Verify session table + sessions module (admin_kill_session reuses).
grep -n "^def kill_my_own_sessions\|DELETE FROM sessions" mindsos_server/sessions.py mindsos_server/admin.py

# Version baseline.
grep -rn '__version__ = "0\.0\.0+phase' --include="*.py" mindsos_*/__init__.py
```

Verify all 6 packages at `+phase21`; verify Phase 22-shaped surfaces
absent except for comment-references; verify Phase 20/21 surfaces
present at the locations the §22 row predicts.

══════════════════════════════════════════════════════════════════════
LIKELY PUSHBACK SURFACES (probe before locking scope)
══════════════════════════════════════════════════════════════════════

Each pushback ends with a pick. Final round closes with a Picks
summary.

1. **CLI verb grouping — flat vs `admin` subgroup?** Phase 20 shipped
   `mindsos server reset-admin` (flat); Phase 21 shipped
   `mindsos server query-audit` (flat). Phase 22 adds 5+ admin verbs.
   Subgroup `mindsos server admin promote-user / demote-user /
   disable-user / enable-user / kill-session` clusters them but
   diverges from Phase 20/21 precedent. Picks: (a) flat per
   precedent; (b) `admin` subgroup; (c) hybrid — high-frequency verbs
   flat, rare ops grouped. The error message in NotAnAdminError
   (Phase 20) already references `mindsos server admin promote-user`
   — that wording would be consistent with pick (b).

2. **`admin_promote_user` semantics on existing-admin target.**
   Idempotent (no-op) or error? Compare to bootstrap's idempotency.
   Picks: (a) idempotent — re-promoting an admin is a no-op with
   exit 0 + audit row; (b) error `AlreadyAnAdminError(target_user_id)`;
   (c) silent no-op without audit (rejected — every privileged
   endpoint audits per ADR-0013 §Decision).

3. **`admin_disable_user` — kill active sessions immediately?** A
   disabled user's existing sessions could still authenticate per
   the session-from-token path until lazy expiry. Picks: (a) yes —
   DELETE sessions WHERE user_id=? + per-row EVT_KILL_SESSION (matches
   reset_admin pattern from Phase 20 PB-R + PB-D); (b) no — leave
   sessions; `session_from_token` already gates on `users.disabled=0`
   (check current code via probe); (c) yes, but audit only the
   summary EVT_ADMIN_DISABLE_USER with `sessions_killed: N`
   denormalized (Phase 20 PB-BB pattern).

4. **`_assert_not_sole_admin` signature shape.** ADR-0012 §Decision
   names it as a helper. Picks: (a) `_assert_not_sole_admin(conn,
   target_user_id) -> None` — raises LastAdminError if the target IS
   the only admin (matches ADR wording); (b) explicit
   `_count_active_admins(conn) -> int` + caller does the check;
   (c) `_assert_not_sole_admin(conn, *, excluding: str) -> None` —
   semantic clearer at call site.

5. **`LastAdminError` HTTP-409 mapping.** ADR-0012 §Consequences
   notes HTTP-409 mapping but Phase 20 §am2 PB-B deferred the class
   itself. CLI-only product (no HTTP transport per PHASE_MAP §1) →
   does the class need the mapping at construction? Picks: (a) ship
   the class without HTTP mapping (Phase 22 is L0 CLI-only; mapping
   lands when HTTP transport ships); (b) embed `http_status = 409`
   as a class-attr (documentary future-proofing); (c) defer mapping
   via §amendment when HTTP transport phases land.

6. **Cross-user read (`ADR-0008` refcount-install) — in scope or
   defer?** PHASE_MAP §22 row Features mentions "cross-user read
   with refcount-install (ADR-0008)". This is a separate concern
   from admin user mgmt — it lands KL-side hydration of another
   user's Local with a refcount. Scope-narrowing precedent: Phase 16
   PB-1c, Phase 18 PB-27, Phase 20 PB-B all deferred features.
   Picks: (a) keep in scope — ships at P22 as designed; (b) narrow
   Phase 22 to admin user mgmt only; defer cross-user read to a new
   row (Phase 22b or shift to P25 since that's where KL session-seam
   lands); (c) ship a stub in P22 (Protocol + capability gate) and
   defer impl.

7. **`hard_delete_user` semantics — what gets deleted vs preserved?**
   ADR-0013 §Consequences locks "audit rows MUST outlive their
   subjects" — _schema.py:96-104 enforces (no FK from audit.actor_user
   / target_user to users.user_id). What about the user's Local? KL
   territory — Phase 22 might ship the user-row DELETE + session
   DELETE only, leaving Local cleanup for a future KL-side verb
   (consistent with Phase 21's L0-only scope). Picks: (a) Phase 22
   deletes user row + sessions only (L0-clean); Local hard-delete
   deferred to a KL phase; (b) Phase 22 calls into KL via
   `LocalPersister.hard_delete(user_id)` — but `LocalPersister`
   doesn't ship until Phase 25 per ADR-0011 §am1; (c) Phase 22 ships
   a `HARD_DELETE_PENDING` marker on the user row; KL phase
   processes pending markers later.

8. **`admin_kill_session(conn, session, target_session_id_or_user_id?)`
   arg shape.** Phase 19's `kill_my_own_sessions` takes `user_id` +
   `password`. Phase 20's reset_admin kills sessions as a side
   effect. Phase 22's admin_kill_session is a deliberate-target verb.
   Picks: (a) by session_id — `admin_kill_session(conn, session, *,
   target_session_id: str)`; (b) by user_id — kills ALL of target
   user's sessions (mirrors reset_admin); (c) by either — overloaded
   first kwarg.

9. **`admin_enable_user` symmetry with disable.** If PB-3(a) is
   locked (disable kills sessions), then enable is just `UPDATE
   users SET disabled = 0`. But Phase 20 reset_admin already
   conditional-emits EVT_ADMIN_ENABLE_USER — is the verb a thin
   wrapper or does it do more (e.g., audit-then-no-op if already
   enabled)? Picks: (a) thin verb — UPDATE + EVT_ADMIN_ENABLE_USER
   audit (idempotent on already-enabled rows); (b) error
   `AlreadyEnabledError` on already-enabled target; (c) thin verb
   but skip the audit row on no-op.

10. **`_assert_not_sole_admin` call ordering inside multi-step verbs.**
    `admin_demote_user` = check sole-admin → UPDATE actor_role →
    audit. `admin_disable_user` = check sole-admin → DELETE sessions
    → UPDATE disabled → audit. `hard_delete_user` = check sole-admin
    → DELETE sessions → DELETE user → audit. Picks: (a) check FIRST
    in every multi-step verb (fail fast before any state change);
    (b) check just before the destructive operation (within the same
    tx; rollback-safe).

══════════════════════════════════════════════════════════════════════
PROCESS DISCIPLINE
══════════════════════════════════════════════════════════════════════

Per `user_two_machine_setup.md` + PHASE_MAP §1 + Phase 21 lessons:

* **Mac**: code editing (Claude session), `git add/commit/push`,
  `gh pr create`, `gh pr merge --squash`, final `git tag` + push.
  Mac has NO docker. Mac Python 3.9.6 — do NOT `pip install -e .` on
  Mac.
* **Linux**: `git pull`, `docker compose --profile test build
  mindsos-test` (pre-build to avoid timeout), all `docker compose
  run --rm mindsos-test pytest ...` runs, all **host-native**
  `mindsos <verb>` smoke (per `feedback_smoke_harness_host_native.md`
  — Phase 21 finding).
* **confirm-phase**: host-native is canonical (per Phase 20 + 21
  experience). Run from a Python ≥ 3.12 venv on the Linux host (`pip
  install -e . --user --break-system-packages` after pulling
  phase-NN branch).

Branch: `phase-22` off `origin/main` tip. Notes: `notes-phase-22.md`
at repo root. Version bump `+phase21 → +phase22` across 9 sites /
11 lines (6 pkg `__init__.py` + pyproject + docker-compose 2× +
manifest.toml 2×). Tag `phase-22-confirmed` AFTER squash-merge only;
verify `git rev-parse phase-22-confirmed` returns "unknown" BEFORE
creating.

**Path (a) workflow validated at Phase 20-21** — land all impl
batches in ONE commit on phase-NN, skip per-batch round-trips
(squash collapses them anyway). Saves 3 Mac round-trips per phase.

Phase 22 likely ADR amendments at ship: ADR-0012 §am3 (closes the
helper + class deferral from §am2; documents helper signature +
call-site wiring); possibly ADR-0008 §am1 if cross-user read lands
+ refcount-install needs clarification (or §amendment to defer if
PB-6(b) wins).

══════════════════════════════════════════════════════════════════════
FIRST RESPONSE EXPECTATIONS
══════════════════════════════════════════════════════════════════════

1. Confirm cited files read; report any missing.
2. Run the pre-impl probe; report findings (verify
   `_assert_not_sole_admin` / `LastAdminError` / 5 admin verbs absent;
   verify Phase 20/21 surfaces intact).
3. Surface 1-3 pre-design pushbacks (with picks) from §Likely
   pushback surfaces OR from the probe.
4. Ask the single highest-value missing-constraint question.

DO NOT write code in the first response. Phase 18's 4-round + Phase
19's 3-round + Phase 20's 4-round + Phase 21's 4-round design
pushback ledger pattern is the shape this project favors — sign off
the architecture first, then implement. Phase 22 is wider in scope
than 19-21; expect 4-5 rounds and possibly 30+ picks. Phase 18
remains the high-water mark (38 picks).

══════════════════════════════════════════════════════════════════════
EXIT CRITERIA
══════════════════════════════════════════════════════════════════════

Phase 22 squash-merges to main; `phase-22-confirmed` tag pushed
AFTER merge; `release.yml` green; GitHub Release created. Phase 22
writes `confirmation_docs/PHASE_23_NEXT_CHAT_PROMPT.md` as exit
artifact (Phase 23 = "Server: MetagraphSnapshot rollback
infrastructure (narrowed)"; deps 10/19; may itself retire to
Phase 24 if the design chat decides the snapshot wrapper has no
real consumer until Phase 24's `release_update` lands).
══════════════════════════════════════════════════════════════════════
