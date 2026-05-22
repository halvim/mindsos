══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 23 (Server: MetagraphSnapshot rollback infrastructure)
══════════════════════════════════════════════════════════════════════

This prompt is intentionally lean. The phase chat reads files for
context; this prompt only points at them + locks process expectations.

Project: MindsOS — folder `halvim_mindsos/` under
`/Layered Intelligence/`. Branch off `origin/main` tip (currently the
Phase 22 squash; tag `phase-22-confirmed` resolves to the same SHA).

ROLE: Critical design reviewer + implementer. Read the project-level
CLAUDE.md at `/Layered Intelligence/CLAUDE.md` AND the MindsOS
sub-project CLAUDE.md if present. Follow strict picks-per-pushback
discipline (each pushback ends with a pick; final picks summary at
the end of every multi-pushback round; see
`feedback_pushback_format_with_picks.md`).

Phase 23 scope is locked at PHASE_MAP §Phase 23 row. Read the row;
do not re-derive scope from training. **Phase 23 may RETIRE during
its own design chat** — the row explicitly notes "the wrapper has
no real consumer until Phase 24's `release_update` calls into it.
Phase 23 may instead defer entirely to Phase 24 — phase chat decides
at design time." This is a precedent-matched escape: Phase 17
retired via Phase 17's own chat (ADR-0150 §am3); Phase 37 retired
during Phase 15a (ADR-0140 §am1). If Phase 23's design analysis
finds no consumer pre-P24, the right answer is RETIREMENT + design-
only documentation amending Phase 24's row to absorb the
snapshot-rollback wrapper.

══════════════════════════════════════════════════════════════════════
REQUIRED READING (in this order)
══════════════════════════════════════════════════════════════════════

1. **`MEMORY.md`** — auto-loaded at chat start. Every `feedback_*`
   entry is a hard rule. Pay special attention to:
   * `feedback_pushback_format_with_picks.md`
   * `feedback_pre_impl_probe_check_existing_modules.md`
   * `feedback_phase_baseline_literal_audit.md`
   * `feedback_smoke_harness_host_native.md`
   * `user_two_machine_setup.md` (Mac/Linux split + commands)

2. **`halvim_mindsos/confirmation_docs/PHASE_MAP.md`** §0 (load-bearing
   read rule) + §1 (settled cross-cutting decisions — read in full) +
   §Phase 21 / §Phase 22 (most-recent context — Phase 22 shipped the
   6-verb admin subgroup + `_assert_not_sole_admin` + `LastAdminError`
   + `admin_tx` race protection) + §Phase 23 (own row — scope source;
   pay close attention to the "may retire" clause) + §Phase 24 (the
   absorber-of-retirement target) + §Phase 10 (the actual snapshot
   module ship; ADR-0027 / ADR-0129).

3. **`halvim_mindsos/confirmation_docs/PHASE_22_DESIGN_LOG.md`** —
   most recent design log. Read §0 scope summary + §2 final locks
   table (27-pick reference; the `admin_tx` BEGIN IMMEDIATE pattern
   is relevant if Phase 23's wrapper needs similar tx posture) + §3
   cross-chat dependencies Forward subsection + §4 ADR delta + §6
   out-of-scope.

4. **`halvim_mindsos/confirmation_docs/PHASE_22_CONFIRMED.md`** —
   ground truth for what shipped at Phase 22 tag. Tester notes
   capture any B-22-T* hotfix lessons.

5. **Phase 10 snapshot module** at
   `halvim_mindsos/mindsos_core/metagraph_snapshot.py` — the actual
   substrate the Phase 23 wrapper would compose. ADR-0027 / ADR-0129
   shape the contract.

6. **ADRs** at `/Layered Intelligence/docs/decisions/adr/`. Read in
   full at first probe:
   * **ADR-0027** (MetagraphSnapshot.of() + .restore_into()) — the
     core surface.
   * **ADR-0129** (narrowed-to-release-ship). Status check —
     Accepted or Proposed?
   * **ADR-0118** (per-user transactional promotion) — Phase 24's
     home; if Phase 23 retires here is the absorber.
   * **ADR-0010** (layer isolation) — Phase 23 is L0-only.

══════════════════════════════════════════════════════════════════════
PRE-IMPL PROBE (run BEFORE any design pushbacks)
══════════════════════════════════════════════════════════════════════

```
cd halvim_mindsos
# Verify Phase 22 squashed + tagged at main tip.
git fetch origin && git log --oneline origin/main | head -5
git rev-parse phase-22-confirmed 2>&1 | head -1

# Verify Phase 22 surfaces intact.
ls mindsos_server/admin.py
grep -n "admin_tx\|_assert_not_sole_admin\|admin_promote_user\|admin_demote_user\|admin_disable_user\|admin_enable_user\|admin_kill_session\|hard_delete_user" mindsos_server/admin.py | head -20
grep -n "LastAdminError\|AlreadyAnAdminError\|SessionNotFoundError" mindsos_server/errors.py | head

# Verify Phase 10 snapshot module + ADR-0027 surface intact.
ls mindsos_core/metagraph_snapshot.py
grep -n "MetagraphSnapshot\|class .*Snapshot\|of(\|restore_into" mindsos_core/metagraph_snapshot.py | head -10

# Verify Phase 23 surfaces NOT yet shipped.
grep -rn "snapshot_wrapper\|with_snapshot\|release_ship_lock\|RELEASE_SHIP_LOCK" \
    mindsos_server/ mindsos_cli/ 2>/dev/null | grep -v "\.pyc\|comment\|#" | head -10

# Look for Phase 24 prerequisites that the wrapper would expect to find
# (signal for whether Phase 23 has a consumer pre-P24).
grep -rn "propose_for_promotion\|release_update\|RELEASE_SHIP_LOCK" \
    mindsos_admin/ mindsos_server/ 2>/dev/null | head

# Version baseline.
grep -rn '__version__ = "0\.0\.0+phase' --include="*.py" mindsos_*/__init__.py
```

Verify all 6 packages at `+phase22`; verify Phase 23-shaped surfaces
absent; verify Phase 22 + Phase 10 surfaces present.

**Critical first-design probe:** establish whether ANY consumer of
the snapshot-rollback wrapper exists in shipped code today. If the
answer is "no consumer until Phase 24's `release_update`", the
**retirement option** is on the table from round 1.

══════════════════════════════════════════════════════════════════════
LIKELY PUSHBACK SURFACES (probe before locking scope)
══════════════════════════════════════════════════════════════════════

Each pushback ends with a pick. Final round closes with a Picks
summary.

1. **Retire Phase 23 entirely?** PHASE_MAP §23 row explicitly opens
   this door: "the wrapper has no real consumer until Phase 24's
   `release_update` calls into it. Phase 23 may instead defer
   entirely to Phase 24 — phase chat decides at design time."
   Precedent: Phase 17 retired (ADR-0150 §am3); Phase 37 retired
   (ADR-0140 §am1). Picks: (a) ship the wrapper at P23 as
   pre-positioning; (b) **retire Phase 23**; absorb the wrapper into
   Phase 24 alongside `release_update`'s direct call into snapshot
   primitives; (c) ship a stub Protocol at P23 + lock the impl at
   P24.

2. **Snapshot scope: stay narrowed to release-ship?** ADR-0129
   narrowed the snapshot scope; PHASE_MAP §23 confirms "Phase 23
   does NOT widen." Worth re-confirming the narrowing holds given
   any Phase 22+ surface that touches snapshots. Picks: (a) confirm
   narrow scope per ADR-0129; (b) widen if a new consumer surfaced;
   (c) further narrow.

3. **Snapshot tx wrapper interaction with `admin_tx`?** If Phase
   23 ships the wrapper AND Phase 22's `admin_tx` exists, do they
   compose? Phase 23 snapshot is FalkorDB-side (graph snapshot);
   `admin_tx` is SQLite-side (server.db). Different stores, no
   composition concern unless future code tries to wrap both. Picks:
   (a) document the two-tx-store boundary; (b) ship a unified
   composition helper; (c) defer to Phase 24.

4. **Context-manager shape: `MetagraphSnapshot.of()` + `.restore_into()`
   wrapper API.** ADR-0027 names the primitives. The Phase 23
   wrapper would expose something like `with snapshot_around(mg):
   ...`. Picks: (a) `with snapshot_around(mg): ...` — automatic
   restore on exception; (b) `with snapshot_acquire(mg) as snap:
   ... snap.restore()` — explicit restore; (c) defer the wrapper
   shape to Phase 24's call site.

5. **`RELEASE_SHIP_LOCK` placement.** PHASE_MAP §23 notes the lock
   moves to Phase 24 (along with `propose_for_promotion`) per
   §amendment to §23 row. Confirm: Phase 23 does NOT ship the
   lock. Picks: (a) confirm lock is P24 (not P23); (b) ship the
   lock pre-positioned at P23 with no consumer.

6. **No-consumer pre-positioning risk.** ADR-0150 §am3 + ADR-0140
   §am1 retired phases because shipping code with no consumer
   creates drift between the helper signature and the eventual
   consumer's needs. Phase 22's PB-Z module placement was OK because
   the home was clear; Phase 23's wrapper API surface depends on
   how Phase 24 wants to call it. Picks: (a) retirement (PB-1(b))
   eliminates the drift risk; (b) ship + document the drift risk;
   (c) ship a stub Protocol + lock the impl at P24.

══════════════════════════════════════════════════════════════════════
PROCESS DISCIPLINE
══════════════════════════════════════════════════════════════════════

Per `user_two_machine_setup.md` + PHASE_MAP §1 + Phase 22 lessons:

* **Mac**: code editing (Claude session), `git add/commit/push`,
  `gh pr create`, `gh pr merge --squash`, final `git tag` + push.
  Mac has NO docker. Mac Python 3.9.6 — do NOT `pip install -e .` on
  Mac.
* **Linux**: `git pull`, `docker compose --profile test build
  mindsos-test` (pre-build to avoid timeout), all `docker compose
  run --rm mindsos-test pytest ...` runs, all **host-native**
  `mindsos <verb>` smoke (per `feedback_smoke_harness_host_native.md`).
* **confirm-phase**: host-native is canonical. Run from a Python ≥
  3.12 venv on the Linux host (`pip install -e . --user
  --break-system-packages` after pulling phase-NN branch).

**If Phase 23 retires (PB-1(b) wins):** the squash-merged PR ships
only the ADR-0129 + ADR-0027 amendment (if any) + PHASE_MAP §23 row
rewrite to "RETIRED" + PHASE_MAP §24 row absorption + no version
bump (design-only phase per PHASE_MAP §1 design-only-phases clause).
No `phase-23-confirmed` tag (mirrors Phase 17 retirement + Phase 15b
design-only-phase precedent).

**If Phase 23 ships code (PB-1(a) wins):** branch `phase-23` off
`origin/main`. Version bump `+phase22 → +phase23` across the 9 sites.
Tag `phase-23-confirmed` AFTER squash-merge only.

══════════════════════════════════════════════════════════════════════
FIRST RESPONSE EXPECTATIONS
══════════════════════════════════════════════════════════════════════

1. Confirm cited files read; report any missing.
2. Run the pre-impl probe; report findings (verify Phase 22 surfaces
   intact; verify no Phase 23-shaped code shipped; check whether ANY
   consumer of the snapshot wrapper exists pre-P24).
3. Surface 1-3 pre-design pushbacks (with picks) from §Likely
   pushback surfaces OR from the probe. **The retire-or-ship
   question is the highest-value pushback.**
4. Ask the single highest-value missing-constraint question.

DO NOT write code in the first response. Phase 22's 5-round design
pushback ledger pattern is the shape this project favors — sign off
the architecture first, then implement (or retire).

══════════════════════════════════════════════════════════════════════
EXIT CRITERIA
══════════════════════════════════════════════════════════════════════

**If Phase 23 ships code:**
Phase 23 squash-merges to main; `phase-23-confirmed` tag pushed
AFTER merge; `release.yml` green; GitHub Release created. Phase 23
writes `confirmation_docs/PHASE_24_NEXT_CHAT_PROMPT.md` as exit
artifact.

**If Phase 23 retires:**
PR is design-only (ADR amendment + PHASE_MAP rewrites + retirement
note). Squash-merge to main; **NO tag**, **NO version bump**, **NO
release.yml invocation** per PHASE_MAP §1 design-only-phases clause.
Phase 23 writes `confirmation_docs/PHASE_24_NEXT_CHAT_PROMPT.md`
documenting the absorbed scope.

══════════════════════════════════════════════════════════════════════
