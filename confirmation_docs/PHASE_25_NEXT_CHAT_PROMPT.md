══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 25 IMPLEMENTATION
(design locked 2026-05-23; Phase 24 substrate intact on origin/main HEAD)
══════════════════════════════════════════════════════════════════════

You are the implementer for MindsOS Phase 25. The design pass is done.
This chat ships the locked scope to a `phase-25` branch + PR + tag.

Branch off `origin/main` tip (currently `a6bd4fd` — Phase 24 squash).
Tag `phase-24-confirmed` resolves to the same commit.
New branch: `phase-25`.
New tag at ship: `phase-25-confirmed`.

════════════════════════════════════════════════════════════════════
REQUIRED READING — read these files in full BEFORE coding
════════════════════════════════════════════════════════════════════

1. **`halvim_mindsos/confirmation_docs/PHASE_25_DESIGN_LOG.md`** —
   canonical design contract. Contains:
   * §0 scope summary (what ships / what defers)
   * §1 round-by-round ledger (47 PB candidates; ~17 locked picks
     after iterative re-litigation cascade through Rounds 0→4)
   * §2 final 17-pick consolidated table
   * §3 cross-chat dependencies (backward: P14/P18/P19/P21/P22/P24;
     forward: first user-Local-write phase + v2 daemon + v2 quorum-
     approve)
   * §4 ADR delta (7 touches: 0008 Status flip + 0011 §am2 + 0040
     first ship + 0006 §am2 + 0013 §am + 0114 §am4 + 0125 unchanged)
   * **§5 implementation references WITH CONCRETE CODE SHAPES** for
     every NEW + MODIFIED surface. Copy verbatim into impl with one
     Round 6 pre-impl re-analysis pass for any gaps.
   * §6 out-of-scope (what NOT to implement)
   * §7 saturation note (retirement-escape clause)
   * §8 Phase 24 carry-forwards disposition

2. **`halvim_mindsos/confirmation_docs/PHASE_24_DESIGN_LOG.md`** —
   precedent for:
   * §1 Round 0 PB-Z1..Z22 methodology — pre-impl re-analysis
     pattern. Phase 24's Round 0 surfaced 16 substantive picks AFTER
     design-lock. **Run an equivalent Round 6 pass for Phase 25.**
   * §3 cross-chat dependencies + §4 ADR delta pattern.

3. **ADRs at `/Layered Intelligence/docs/decisions/adr/`** — read
   ONLY the ones with Phase 25 touches per design log §4:
   * 0008 (cross-user reads no flush) — flips Accepted at P25 ship
   * 0011 (LocalPersister Protocol) — §am2 lands at P25 ship
   * 0040 (SessionProtocol duck-typing) — first ship at P25
   * 0006 (per-user RLocks + GLOBAL_PROMOTE_LOCK) — §am2 lands at P25
   * 0013 (audit log content) — §am lands at P25 (EVT_HARD_DELETE_USER
     additive key)
   * 0114 (release manifest schema) — §am4 lands at P25 (Phase 24 FK
     gap closure)
   * 0125 (lazy hydration) — stays Proposed; review only

4. **Memory MEMORY.md feedback entries** — apply the following
   hard rules:
   * `feedback_pushback_format_with_picks.md` — for any Round 6 pre-
     impl pushbacks
   * `feedback_pre_impl_probe_check_existing_modules.md` — probe
     before assuming module/API existence
   * `feedback_l1_api_signature_probe_before_writing_tests.md` —
     probe before writing test assertions
   * `feedback_phase_baseline_literal_audit.md` — schema_version
     literal sweep (Phase 25 doesn't bump but cumulative tests
     reference)
   * `feedback_pk_column_per_table_probe.md` — grep `_schema.py` for
     CREATE TABLE column names before writing verification SQL
   * `feedback_test_image_rebuild_after_source_change.md` — rebuild
     `mindsos-test` after NEW modules added
   * `feedback_smoke_harness_host_native.md` — host-native smoke is
     canonical
   * `feedback_release_workflow_ordering.md` +
     `feedback_release_tag_after_squash_merge_only.md` — tag AFTER
     squash-merge of PR to main
   * `feedback_batch_fix_dont_iterate.md` — enumerate ALL failures via
     static grep BEFORE patching; one commit / one push / one rebuild
   * `feedback_sandbox_vs_mac_git_separation.md` — use Edit/Write for
     files; hand user the git commands for ops
   * `feedback_two_machine_setup.md` — tag recipes [Mac] vs [Linux]
   * `feedback_new_top_level_package.md` — N/A; P25 adds no new top-
     level package (mindsos_server/persistence/ is a sub-package)

════════════════════════════════════════════════════════════════════
PRE-IMPL PROBE (Round 6 — Phase 24 Round 0 precedent)
════════════════════════════════════════════════════════════════════

Run BEFORE coding. Phase 24 Round 0 surfaced 16 substantive picks
post-design-lock; Phase 25's design chat already executed two probes
(edge-endpoint API + Phase 24 FK gap) but more may surface.

```
cd halvim_mindsos
git status                                       # clean tree on origin/main
git log --oneline -3                             # confirm HEAD = a6bd4fd (Phase 24)
git checkout -b phase-25

# Probe 1: KL has the local_metagraph(user_id) getter? (assumed in design log §5)
grep -n "def local_metagraph\|def get_local" mindsos_knowledge/knowledge_layer.py

# Probe 2: Metagraph attribute names (graphs_by_role, xrefs, intergraph_edges)
grep -n "graphs_by_role\|def graphs_by_role\|self.xrefs\|self.intergraph_edges" mindsos_core/models/metagraph.py | head -20

# Probe 3: Phase 22 hard_delete_user current signature + admin_tx pattern
grep -n "def hard_delete_user\|HardDeleteUserResult" mindsos_server/admin.py

# Probe 4: existing _admin_exit_for + admin_app surface in CLI
grep -n "def _admin_exit_for\|admin_app\|_resolve_session" mindsos_cli/commands/server.py | head -20

# Probe 5: mindsos_admin imports — does it already import mindsos_knowledge.types?
grep -rn "from mindsos_knowledge\|import mindsos_knowledge" mindsos_admin/ --include="*.py"

# Probe 6: bootstrap_global helper signature (CLI _resolve_kl needs it)
grep -n "def bootstrap_global\|^def bootstrap_global" mindsos_admin/bootstrap.py

# Probe 7: confirm UserMutexRegistry shape (consumer at P25 — verify import path)
grep -n "class UserMutexRegistry\|def user_mutexes\|def get(" mindsos_server/locks.py
```

**Round 6 pre-impl re-analysis:** after probes, list ANY substantive
gaps the design chat didn't surface, options per gap, and your pick.
If 5+ substantive gaps surface, the design log may need a §am.
Phase 24 Round 0 produced 16 picks — budget for it.

Likely Round 6 candidates (per design log §3 memory rules consumed):
* `KL.local_metagraph(user_id)` getter may not exist as named —
  Phase 14 PB-9 implied it; verify or add 5-LOC method.
* `Metagraph.graphs_by_role` attribute name vs alternative (probe).
* `_resolve_persister` + `_resolve_kl` CLI helpers — singleton
  pattern at module-level or per-command-construction?
* `hard_delete_user(persister=None)` default — backward-compat sweep
  across Phase 22 tests.
* Test-fixture-reset pattern for `_installed_locals` — autouse
  fixture in `conftest.py` (per design log §5 test specs).

════════════════════════════════════════════════════════════════════
IMPLEMENTATION ORDER (per design log §5)
════════════════════════════════════════════════════════════════════

1. **`mindsos_knowledge/types.py`** (NEW, ~30 LOC) — SessionProtocol
   first. Smallest unit; no upstream dependencies.
2. **`mindsos_server/exceptions.py`** extensions — add
   `FlushFailedError` + `UserHasPromotionHistoryError`.
3. **`mindsos_server/persistence/__init__.py`** + **`local_persister.py`**
   (NEW, ~85 LOC total) — Protocol + InMemory + fail_save_for hook.
4. **`mindsos_server/orchestrator.py`** (NEW, ~120 LOC) —
   InstallRecord + read_other_local + _install_for + _release +
   _node_counts; module-level _installed_locals + _install_lock +
   _mutex_registry.
5. **`mindsos_server/audit.py`** PB-31 payload-shape docstring.
6. **`mindsos_server/admin.py`** extensions — hard_delete_user pre-
   check + persister.delete + extra key; read_other_local_summary +
   ReadOtherLocalSummary + RoleGraphSummary dataclasses.
7. **`mindsos_server/__init__.py`** new exports.
8. **`mindsos_cli/commands/server.py`** — `_resolve_persister` +
   `_resolve_kl` helpers; admin_read_local_cmd verb; _admin_exit_for
   extension (exit 10); admin_hard_delete_user_cmd persister kwarg.
9. **Version bump** `+phase24 → +phase25` across the 9-site list per
   `feedback_phase_baseline_literal_audit.md`.
10. **Tests** at `tests/phase_25/` — conftest first (autouse reset
    fixture + persister + kl + seeded_admin fixtures), then 15 tests
    per design log §5 test specs.
11. **ADR amendments** — write the 6 §amendments to live ADR files:
    * `docs/decisions/adr/0008-cross-user-reads-no-flush.md` —
      flip Status to Accepted; add Revisions §amendment-2 (Phase 25
      first-consumer ship; refcount-bump branch test-only in v1 prod)
    * `docs/decisions/adr/0011-local-persister-protocol.md` —
      add Revisions §amendment-2 (5 clauses per design log §4)
    * `docs/decisions/adr/0040-session-protocol-duck-typing.md` —
      add Revisions §amendment-1 (first ship at Phase 25)
    * `docs/decisions/adr/0006-promotion-locking.md` — add
      Revisions §amendment-2 (UserMutexRegistry first consumer)
    * `docs/decisions/adr/0013-audit-log-content.md` — add
      Revisions §amendment-N (EVT_HARD_DELETE_USER additive key)
    * `docs/decisions/adr/0114-release-manifest-and-version-db-schema.md`
      — add Revisions §amendment-4 (Phase 24 FK gap closure)
12. **`confirmation_docs/PHASE_MAP.md`** §25 row — already updated at
    design lock; no further edit at impl.

════════════════════════════════════════════════════════════════════
TEST DISCIPLINE (per memory rules)
════════════════════════════════════════════════════════════════════

* `tests/phase_25/` first, THEN cumulative `tests/` sweep
  (`feedback_test_order_current_then_cumulative.md`).
* Rebuild `mindsos-test` after every source change
  (`feedback_test_image_rebuild_after_source_change.md`).
* Static-grep ALL failure modes before patching; batch fixes in one
  commit (`feedback_batch_fix_dont_iterate.md`).
* Never suggest `--skip-tests` (`feedback_never_suggest_skip_tests.md`).
* Cumulative literal-decay sweep — Phase 18+22 caps-roster + schema-
  version literals — already at 9 caps + schema v4 after Phase 24;
  Phase 25 doesn't bump either, so likely no decay. Still grep ALL
  test files for `caps_count == 9` + `schema_version == 4` + `phase
  == "+phase24"` to be sure.
* Phase 18 dynamic-baseline test (`TestAll6PkgsAtCurrentPhase`
  against manifest version) handles `+phase24 → +phase25` automatically.

════════════════════════════════════════════════════════════════════
SHIP CHECKLIST (per memory rules)
════════════════════════════════════════════════════════════════════

1. All `tests/phase_25/` GREEN host-native.
2. All cumulative `tests/` GREEN host-native + in docker (`mindsos-test`).
3. `notes-phase-25.md` at REPO ROOT with smoke results + any hotfix
   ledger (`feedback_confirm_phase_file_paths.md`).
4. **Manual smoke** — host-native (`feedback_smoke_harness_host_native.md`):
   - `mindsos server bootstrap` (admin already exists path)
   - `mindsos server login admin --password ...`
   - `mindsos server admin create-user alice --password ...`
   - `mindsos server admin read-local alice` → exit 0; shows empty Local summary
   - `mindsos server admin read-local nonexistent` → exit 2 (UserNotFoundError)
   - As non-admin: `mindsos server admin read-local alice` → exit 3 (PermissionDeniedError)
   - `mindsos server admin hard-delete-user alice` → exit 0; local_dump_existed=False in audit
   - Try `mindsos server admin hard-delete-user some-admin-with-promotions` → exit 10
     (UserHasPromotionHistoryError; Phase 24 FK gap closure verified)
5. `git status` clean.
6. **Mac:** `git add` all changes including ADR amendments + notes-
   phase-25.md.
7. **Mac:** open PR against main from `phase-25` branch.
8. CI green (`release.yml` workflow).
9. **Mac:** squash-merge PR to main per
   `feedback_release_workflow_ordering.md`.
10. **Mac:** capture squash-merge SHA → tag `phase-25-confirmed` AT
    THAT SHA per `feedback_release_tag_after_squash_merge_only.md`
    + `feedback_stale_local_tag_silent_overwrite_failure.md` (use
    `git tag -f` if a stale tag exists locally).
11. **Mac:** `git push origin phase-25-confirmed`.
12. CI `release.yml` re-runs against the tag; confirm green.
13. Generate `confirmation_docs/PHASE_25_CONFIRMED.md` via `confirm-
    phase --phase 25 --notes-file notes-phase-25.md` per
    `feedback_confirm_phase_invocation_paths.md` +
    `feedback_confirm_phase_init_notes_overwrites.md` (use --notes-
    file, NEVER --init-notes).
14. **Mac:** commit + push the confirmation_docs/PHASE_25_CONFIRMED.md.

════════════════════════════════════════════════════════════════════
ESTIMATED SHIP SIZE
════════════════════════════════════════════════════════════════════

* ~250 LOC production code (orchestrator + persister + types + admin
  ext + CLI verb)
* ~400 LOC test code (16 test files)
* 6 ADR amendments (1 Status flip + 4 §amendments + 1 first ship)
* 0 schema bumps (stays at v4 from Phase 24)
* 0 new caps (consumes existing CAN_READ_OTHER_LOCALS from P18)
* 0 new audit-event constants (consumes existing EVT_CROSS_USER_READ_INSTALL from P18)
* 1 new CLI verb (`mindsos server admin read-local`)
* 1 new exit code (10 for UserHasPromotionHistoryError)
* 9-site version bump (`+phase24 → +phase25`)
* Estimated 1-2 hotfix rounds during ship (Phase 22-24 baseline:
  1-5 hotfixes per ship)

════════════════════════════════════════════════════════════════════
FIRST RESPONSE EXPECTATIONS
════════════════════════════════════════════════════════════════════

1. Confirm required-reading files read (terse list).
2. Run pre-impl probe (Round 6); report any substantive gaps.
3. If Round 6 surfaces 3+ picks, present them with options + your
   choice (per `feedback_pushback_format_with_picks.md`); pause for
   user confirmation before implementing.
4. If Round 6 is clean: confirm + proceed to implementation in the
   order listed above.

════════════════════════════════════════════════════════════════════
PROCESS DISCIPLINE
════════════════════════════════════════════════════════════════════

* Follow ALL hard-rule feedback memory entries (listed under
  "REQUIRED READING" §4).
* Terse step recipes during execution
  (`feedback_terse_step_recipes.md`); analysis voice only during
  Round 6.
* Picks-per-pushback format for any Round 6 pushbacks.
* Two-machine ([Mac] vs [Linux]) recipe tagging per
  `feedback_two_machine_setup.md`.

════════════════════════════════════════════════════════════════════
RETIREMENT-ESCAPE CLAUSE (per design log §7 + PB-34 + PB-47)
════════════════════════════════════════════════════════════════════

The design chat shipped P25 as scoped with an explicit retirement-
escape clause: IF implementation surfaces the substrate as
fundamentally misdesigned (e.g., `read_other_local` can't be made to
work against the current KL surface; `_installed_locals` registry
can't be tested coherently), Phase 25 may retire design-only per
Phase 17/23 precedent. The retirement decision is implementer's call
based on probe-revealed obstacles, not aesthetic preference.

If retirement is invoked: produce `PHASE_25_RETIREMENT_DESIGN_LOG.md`
following Phase 17/23 retirement template; roll the 7 P25 carry-
forwards to the first user-Local-write phase; no tag; no version
bump.

Default expectation: ship as scoped. Retirement clause is escape-
hatch only.
