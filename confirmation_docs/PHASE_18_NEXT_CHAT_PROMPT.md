══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 18 (Server: user store + auth)
══════════════════════════════════════════════════════════════════════
Project: MindsOS — folder `halvim_mindsos/` under
`/Layered Intelligence/`. Branch off `origin/main` tip.

Phase 17 RETIRED 2026-05-20 (design-only-with-code; tag-free).
Expected `origin/main` shape:
    git fetch origin && git log --oneline origin/main | head -4
* Line 1 = `06ec866 Phase 17 retirement: backfill squash-merge SHA in design log`
* Line 2 = `6d6f8bc Phase 17 — RETIRED: vacuous against ADR-0150 §closure; versions_in_role + CLI verb + ADR-0150 §amendment-3 (#26)`
* Line 3 = `58e76a5 Phase 16 — L2 admin similarity surface (read-only) (#25)`
* Line 4 = `ec94565 Phase 15b — design-only ...`

If line 1/2 don't show the Phase 17 retirement commits, STOP — the
retirement PR didn't land yet; resolve before branching.

**No `phase-17-confirmed` tag exists or should be created** (per
ADR-0150 §amendment-3 + Phase 15b design-only-with-code precedent).
Phase 18 RESUMES the tagged-ship cadence with `phase-18-confirmed`.
ROLE: Critical design reviewer + implementer. Follow project-level
CLAUDE.md skeptical-default + terse + pros/cons + alternatives +
**picks-per-pushback** behavior (per `feedback_pushback_format_with_picks.md`).
Phase 18 scope is locked at PHASE_MAP §Phase 18 row — read that row,
do not re-derive scope from training. Mirror Phase 16's 5-round
design pushback ledger discipline.
══════════════════════════════════════════════════════════════════════
REQUIRED READING — in this order; READ THE FILES, do not guess
══════════════════════════════════════════════════════════════════════
The handoff principle (per PHASE_MAP §0 load-bearing read rule):
read your own row + the two prior phase rows + the most recent
confirmation/retirement docs + only the docs paths your row names.
This prompt does NOT duplicate file content — it tells you which
files to open.
1. `MEMORY.md` (auto-loaded at chat start). Every `feedback_*` entry
   is a hard rule. Pay special attention to:
   * `feedback_pushback_format_with_picks.md` — picks per pushback
     + final Picks summary; user has flagged twice that options-
     without-picks is unacceptable.
   * `feedback_pre_impl_probe_check_existing_modules.md` — Phase
     18 is L0 NEW; pre-impl probe must verify NO `mindsos_server/`
     package exists yet (NEW top-level pkg territory; 7-site
     checklist in play).
   * `feedback_new_top_level_package.md` + extensions: pyproject +
     Dockerfile prod+test + sentinel_paths + doctor parity (4→5
     pkg or 5→6 depending on whether retirement bumped doctor's
     pkg count — verify) + Linux host pip refresh + image-
     completeness test.
   * `feedback_phase_baseline_literal_audit.md` — Phase 18 is the
     first version bump since Phase 17 retirement (`+phase17 →
     +phase18`).
   * `feedback_test_image_rebuild_after_source_change.md` /
     `feedback_stale_local_tag_silent_overwrite_failure.md` /
     `feedback_release_tag_after_squash_merge_only.md` — Phase 18
     IS a tagged shipped-phase (retirement was tag-free; Phase 18
     resumes the tag cadence).
   * `feedback_batch_fix_dont_iterate.md`,
     `feedback_sandbox_vs_mac_git_separation.md`.
2. Phase-recap memory entries — durable handoff context:
   * `project_mindsos_phase_16_implemented.md` — most recent
     code-shipping phase before retirement.
   * `project_mindsos_phase_17_retired.md` — retirement decision
     log; the version-dispatch lock + escape clause + what shipped
     at retirement chat (do NOT re-litigate).
   * `project_mindsos_auth_and_concerns.md` — original 8-concern
     resolution + server-auth model decisions that pre-date this
     phase.
   * `project_mindsos_l0_server_pivot.md` — multi-tenant SaaS
     framing; admin-curated Globals; per-user transactional
     promotion; ADR-0118 drafted.
3. `halvim_mindsos/confirmation_docs/PHASE_MAP.md`:
   * §0 (load-bearing read rule) + §1 (settled cross-cutting
     decisions).
   * §Phase 18 row — primary scope source-of-truth.
   * §Phase 16 + §Phase 17 (RETIRED) rows — two prior phases per
     §0 (Phase 17 is the RETIRED tombstone; read it for absorbed
     surfaces but expect "no code shipped at 18 from §17" because
     retirement absorbed everything).
   * §Phase 19 row — confirm Phase 18 does NOT cross the session
     boundary (sessions ship at 19).
4. `halvim_mindsos/confirmation_docs/PHASE_17_RETIREMENT_DESIGN_LOG.md`
   — most recent confirmation/retirement doc (per §0 chain-read
   rule). Skim §7 (final shipped state) + §8 (why not tag).
5. `halvim_mindsos/confirmation_docs/PHASE_16_DESIGN_LOG.md` (if
   relevant to Phase 18 deps):
   * §3 Cross-chat dependencies "Forward (Phase 16 → later phases)"
     subsection — Phase 18 may inherit carry-forwards from Phase
     16 (e.g., `user_id` charset from ADR-0044 §amendment-1 must
     be preserved end-to-end in the server user-store).
6. ADRs (in `/Layered Intelligence/docs/decisions/adr/` per Model C):
   * ADR-0001 (dedicated server layer) — Phase 18 is the first L0
     phase that materializes this.
   * ADR-0002 (session and capability model) — read; Phase 19
     consumes but Phase 18 sets the capability assignment surface.
   * ADR-0003 (password and token scheme) — argon2id contract.
   * ADR-0010 (layer isolation) — Phase 18 stays L0; domain layers
     (L1/L2/L3) do NOT import `mindsos_server`.
   * ADR-0040 (session protocol duck-typing) — the seam Phase 25
     consumes; Phase 18 must NOT pre-bind to a concrete
     SessionProtocol shape that breaks duck-typing.
   * ADR-0041 (duplicate capability constants parity test) — Phase
     18 ships the canonical capability constants; parity test
     against L2/L3 lives here.
   * ADR-0044 §amendment-1 — `user_id` charset
     `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$` MUST be inherited verbatim
     by the server user-store; preserves IRI-parseability invariant
     end-to-end (Phase 12 lock).
   * ADR-0046 (admin enforcement, capability-based) — Phase 18
     bootstrap admin path.
   * Phase 18 may need to NEW-author 0 or 1 ADR if a user-store
     decision lacks a prior ADR (e.g., user-store persistence
     backend — SQLite per ADR-0004 §split-persistence? verify).
══════════════════════════════════════════════════════════════════════
PRE-IMPL PROBE (run BEFORE any design pushbacks; per the memory rule)
══════════════════════════════════════════════════════════════════════
    cd halvim_mindsos
    # Verify NO `mindsos_server/` package exists yet.
    ls -d mindsos_server/ 2>&1 | head -2
    # Verify version-bump baseline.
    grep -rn '__version__ = "0\.0\.0+phase' --include="*.py" | head -10
    # Verify retirement landed clean.
    git log --oneline origin/main | head -3
    grep -n "RETIRED 2026-05-20" confirmation_docs/PHASE_MAP.md | head -5
    # If any auth-related code already exists somewhere unexpected:
    grep -rnE "argon2|verify_password|hash_password|user_store" \
        mindsos_*/ 2>/dev/null | head -10
Report findings. If `mindsos_server/` already exists OR auth helpers
already ship somewhere unexpected, surface as a reframe pushback
BEFORE agreeing scope as net-new (Phase 15b / Phase 17 retirement
precedents — pre-impl probe IS the first round).
══════════════════════════════════════════════════════════════════════
LIKELY PUSHBACK SURFACES (probe before locking scope; not exhaustive)
══════════════════════════════════════════════════════════════════════
1. **`user_id` charset inheritance.** ADR-0044 §amendment-1's regex
   MUST live in `mindsos_server` user-store creation path
   identically. Where does the regex constant live — duplicated,
   shared-import, or parity-tested? Each option has trade-offs.
2. **Password CLI policy.** "CLI must NEVER read passwords from
   arguments — `--password-stdin` only" (PHASE_MAP §18 Risks).
   How is that enforced — typer-level refusal of `--password` arg,
   or convention-only? `--password-stdin` UX shape matters.
3. **First-admin bootstrap.** Phase 18 ships user-create + verify;
   Phase 20 ships bootstrap CLI. What's the chicken-and-egg between
   them? Can Phase 18 ship a one-shot bootstrap helper that Phase
   20 wraps in a CLI verb, or is bootstrap entirely Phase 20?
4. **Capability assignment surface.** Capabilities are constants
   (ADR-0041); the assignment API shape (per-user list? role-based
   sets? grant/revoke verbs?) is Phase 18's decision.
5. **User-store persistence backend.** SQLite per ADR-0004 — but
   schema? Migration story across Phase 18 amendments? Concurrent-
   write story?
6. **Test approach.** Server tests need a tmp SQLite DB per test;
   Phase 18 ships the fixture pattern that Phases 19-22 inherit.
7. **`mindsos_server` is a NEW top-level pkg.** 7-site checklist
   (pyproject + Dockerfile prod+test + sentinel paths + doctor pkg
   parity + Linux host pip refresh + image-completeness test +
   tests reading host files Dockerfile COPY pattern).
8. **`mindsos serve` CLI verb or separate binary?** Phase 18 ships
   user CRUD verbs (`server user create / list / verify`); the
   long-running server daemon is a later phase (presumably Phase
   20+). Decide verb-group naming + entry-point.
══════════════════════════════════════════════════════════════════════
PROCESS DISCIPLINE — see MEMORY.md feedback entries (do not restate)
══════════════════════════════════════════════════════════════════════
Branch: `phase-18` off `origin/main` tip (verify retirement-merge SHA
first via `git log`).
Notes file: `notes-phase-18.md` at repo root.
`mindsos confirm-phase --init-notes 18` runs ONCE (overwrites; see
`feedback_confirm_phase_init_notes_overwrites.md`).
Pre-build test image (`docker compose --profile test build
mindsos-test`) before AND after every hotfix.
Version bump `+phase17 → +phase18` across all version-bearing sites
(verify count — retirement added at least the manifest + pyproject +
docker-compose tags + 5 `__init__.py`).
**NEW top-level package `mindsos_server/` — 7-site checklist applies.**
Tag `phase-18-confirmed` AFTER squash-merge only; verify
`git rev-parse phase-18-confirmed` returns "unknown" BEFORE creating
to avoid the Phase 16 stale-tag false-start
(`feedback_stale_local_tag_silent_overwrite_failure.md`).
══════════════════════════════════════════════════════════════════════
FIRST RESPONSE IN THE NEW CHAT SHOULD
══════════════════════════════════════════════════════════════════════
1. Confirm cited files read; report any missing.
2. Verify `git log --oneline origin/main | head -3` shows the
   retirement merge at tip (not Phase 16's `58e76a5`).
3. Run the pre-impl probe above; report findings.
4. Surface 1–3 pre-design pushbacks from §Likely pushback surfaces
   (or new ones surfaced by the probe). **Each pushback ends with
   a pick per `feedback_pushback_format_with_picks.md`.**
5. Ask the single highest-value missing-constraint question.
DO NOT write code in the first response. Phase 16's 5-round design
pushback ledger is the shape this project favors — sign off the
architecture first, then implement. The reframe-from-handoff
discipline (Phase 15b: scope already shipped; Phase 16: scope
contradicts ADRs; Phase 17 retirement: scope vacuous against
shipped invariants) should be applied to Phase 18's handoff scope
too if the probe surfaces evidence.
══════════════════════════════════════════════════════════════════════
HANDOFF EXIT CRITERIA
══════════════════════════════════════════════════════════════════════
Phase 18 squash-merges to main; `phase-18-confirmed` tag pushed
AFTER merge per `feedback_release_tag_after_squash_merge_only.md`;
`release.yml` runs green; GitHub Release created. Phase 18 writes
`confirmation_docs/PHASE_19_NEXT_CHAT_PROMPT.md` as exit artifact
(Phase 19 = "Server: sessions"; deps Phase 18 only).
══════════════════════════════════════════════════════════════════════
