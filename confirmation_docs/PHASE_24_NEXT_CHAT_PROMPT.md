══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 24 (Server + admin: per-user transactional
promotion + RELEASE_SHIP_LOCK + audit gate + release manifest +
lazy migration)
══════════════════════════════════════════════════════════════════════

This prompt is intentionally lean. The phase chat reads files for
context; this prompt only points at them + locks process expectations.

Project: MindsOS — folder `halvim_mindsos/` under
`/Layered Intelligence/`. Branch off `origin/main` tip (currently the
Phase 23 retirement squash + the Phase 22 squash; tag
`phase-22-confirmed` resolves to the most recent code phase).

ROLE: Critical design reviewer + implementer. Read the project-level
CLAUDE.md at `/Layered Intelligence/CLAUDE.md` AND the MindsOS
sub-project CLAUDE.md if present. Follow strict picks-per-pushback
discipline (each pushback ends with a pick; final picks summary at
the end of every multi-pushback round; see
`feedback_pushback_format_with_picks.md`).

**Phase 24 is the largest unshipped phase by far.** It absorbs
substrates from FOUR upstream phases and flips THREE ADRs from
Proposed to Accepted. Expect 5-7 design rounds, 30-50 picks. Phase 22
set a five-round / 27-pick precedent; Phase 24's scope is larger.

**Phase 23 was RETIRED 2026-05-22 (design-only retirement).** Read
`confirmation_docs/PHASE_23_RETIREMENT_DESIGN_LOG.md` for the
13-pick ledger. ADR-0129 §amendment-1 locked the inline
`MetagraphSnapshot.of` / `.restore_into` pattern for `release_update`
— Phase 24 honours that contract; do NOT re-litigate the
wrapper-vs-inline question.

══════════════════════════════════════════════════════════════════════
REQUIRED READING (in this order)
══════════════════════════════════════════════════════════════════════

1. **`MEMORY.md`** — auto-loaded at chat start. Every `feedback_*`
   entry is a hard rule. Pay special attention to:
   * `feedback_pushback_format_with_picks.md`
   * `feedback_pre_impl_probe_check_existing_modules.md`
   * `feedback_phase_baseline_literal_audit.md`
   * `feedback_smoke_harness_host_native.md`
   * `feedback_pk_column_per_table_probe.md` (Phase 22 B-22-T1 lesson)
   * `user_two_machine_setup.md` (Mac/Linux split + commands)

2. **`halvim_mindsos/confirmation_docs/PHASE_MAP.md`** §0
   (load-bearing read rule) + §1 (settled cross-cutting decisions
   — read in full) + §Phase 22 (admin ops shipped) + §Phase 23
   (RETIRED — read the row to internalize the locked decisions Phase
   24 absorbs) + §Phase 24 (own row — the absorption note is
   concrete; honour the locked inline pattern + audit-gate sequencing
   + CI lint rule slot) + §Phase 16 (similarity surface — Phase 24
   consumes `compute_similarity` for the audit gate per ADR-0144
   §Placement) + §Phase 14 (KL bootstrap — `propose_for_promotion`
   replaces the long-dropped `KL.promote()`) + §Phase 10 (snapshot
   primitives — the substrate Phase 24's inline rollback calls into).

3. **`halvim_mindsos/confirmation_docs/PHASE_23_RETIREMENT_DESIGN_LOG.md`**
   — Phase 23 retirement chat (13 picks across 3 rounds). §7
   carry-forwards are LOCKED for Phase 24; do not re-litigate.

4. **`halvim_mindsos/confirmation_docs/PHASE_22_DESIGN_LOG.md`** —
   most recent code phase's design log. Read §0 scope summary + §2
   final locks table (27-pick reference; the `admin_tx` BEGIN
   IMMEDIATE pattern is the closest precedent for Phase 24's
   `RELEASE_SHIP_LOCK` posture) + §3 cross-chat dependencies Forward
   subsection + §4 ADR delta + §6 out-of-scope.

5. **`halvim_mindsos/confirmation_docs/PHASE_22_CONFIRMED.md`** —
   ground truth for what shipped at Phase 22 tag. Tester notes
   capture B-22-T1 hotfix lesson (per-table PK column probe).

6. **ADRs** at `/Layered Intelligence/docs/decisions/adr/`. Read in
   full at first probe:
   * **ADR-0118** (Proposed → flips to Accepted at Phase 24 ship)
     — per-user transactional promotion + release-boundary atomicity.
     The master spec for `propose_for_promotion` + `release_update`
     + `RELEASE_SHIP_LOCK` + lazy migration.
   * **ADR-0141** (Proposed → flips to Accepted at Phase 24 ship)
     — `propose_for_promotion` replaces `KL.promote()` as the
     canonical promotion entry-point.
   * **ADR-0144 §Placement** + **§amendment-1** (partial Accept →
     full Accept; §amendment-1 retires) — `compute_similarity` from
     Phase 16 wires into the release-ship audit gate.
   * **ADR-0129 §amendment-1** — the SIX locked clauses Phase 24
     must honour (inline pattern, lint rule slot, no runtime warning,
     ADR-0007 flip timing, version bump path).
   * **ADR-0027** — snapshot mutate-in-place contract (covered-fields
     allow-list per §Revisions §1; the substrate Phase 24's inline
     rollback calls into).
   * **ADR-0007** (Accepted with supersession-in-progress banner →
     flips to Superseded at Phase 24 ship) — original snapshot-based
     promotion rollback; superseded structurally by ADR-0118.
   * **ADR-0006** (amended in place by ADR-0118 — `GLOBAL_PROMOTE_LOCK`
     renamed to `RELEASE_SHIP_LOCK`) — per-user mutex retained;
     release-ship holds only the global lock.
   * **ADR-0115** (Proposed) — release-ship audit gate. Phase 24
     consumes this; may flip to Accepted or remain Proposed depending
     on phase chat scope decision.
   * **ADR-0010** (Accepted) — layer isolation. Phase 24 must NOT
     have L2/KL import `mindsos_server` (parity test enforces).

7. **PIVOT_V1_SCOPE_2026-04-26.md** at `/Layered Intelligence/docs/`
   — §6.A code change summary, §7.1 PromotionProposal shape, §7.2
   pending-Global graph layout, §7.3 lazy migration, §7.4 ref
   rewrite, §7.5 releases table schema, §7.6 audit event enum,
   §7.7 version DB schema. **This is the data-shape source of truth
   for Phase 24**; ADR-0118 governs the atomicity model but defers
   data shapes to PIVOT §7.

══════════════════════════════════════════════════════════════════════
PRE-IMPL PROBE (run BEFORE any design pushbacks)
══════════════════════════════════════════════════════════════════════

```
cd halvim_mindsos
# Verify Phase 22 baseline + Phase 23 retirement squashed at main tip.
git fetch origin && git log --oneline origin/main | head -5
git rev-parse phase-22-confirmed 2>&1 | head -1

# Verify Phase 22 surfaces intact.
ls mindsos_server/admin.py
grep -n "admin_tx\|_assert_not_sole_admin\|admin_promote_user\|hard_delete_user" \
    mindsos_server/admin.py | head -10
grep -n "LastAdminError\|AlreadyAnAdminError\|SessionNotFoundError" \
    mindsos_server/errors.py | head

# Verify Phase 10 snapshot module intact (the inline rollback substrate).
ls mindsos_core/metagraph_snapshot.py
grep -n "MetagraphSnapshot\|def of\|def restore_into" \
    mindsos_core/metagraph_snapshot.py | head

# Verify Phase 16 similarity surface intact (audit-gate consumer).
ls mindsos_admin/similarity.py
grep -n "compute_similarity\|list_candidates\|metagraph_content_hash" \
    mindsos_admin/similarity.py | head

# Verify Phase 23 retirement landed in docs + PHASE_MAP.
grep -A1 "amendment-1" /Layered\ Intelligence/docs/decisions/adr/0129-metagraph-snapshot-narrowed-to-release-ship.md | head
grep -n "RETIRED 2026-05-22\|~~23~~" confirmation_docs/PHASE_MAP.md | head

# Verify Phase 24-shaped surfaces NOT yet shipped.
grep -rn "release_update\|propose_for_promotion\|RELEASE_SHIP_LOCK\|pending_global" \
    mindsos_admin/ mindsos_server/ 2>/dev/null | grep -v "\.pyc\|docstring\|reserved" | head
find mindsos_server -name "release.py" -o -name "promotion.py" 2>&1

# Verify ADR-0118 + ADR-0141 + ADR-0144 still Proposed.
head -10 /Layered\ Intelligence/docs/decisions/adr/0118-per-user-transactional-promotion.md
head -10 /Layered\ Intelligence/docs/decisions/adr/0141-*.md 2>/dev/null
head -10 /Layered\ Intelligence/docs/decisions/adr/0144-*.md 2>/dev/null

# Verify ADR-0007 still Accepted with supersession-in-progress banner.
head -10 /Layered\ Intelligence/docs/decisions/adr/0007-metagraph-snapshot-rollback.md

# Version baseline.
grep -rn '__version__ = "0\.0\.0+phase' --include="*.py" mindsos_*/__init__.py
```

Verify all 6 packages at `+phase22`; verify Phase 24-shaped surfaces
absent (`release.py`, `promotion.py`, `release_update`,
`propose_for_promotion`); verify Phase 22 + Phase 10 + Phase 16
surfaces present; verify ADR-0129 §amendment-1 landed.

══════════════════════════════════════════════════════════════════════
LIKELY PUSHBACK SURFACES (probe before locking scope)
══════════════════════════════════════════════════════════════════════

Each pushback ends with a pick. Final round closes with a Picks
summary. The Phase 23 retirement design log §7 carry-forwards are
LOCKED — do NOT open the following as pushback surfaces:

* Wrapper-vs-inline call shape (locked: inline).
* DeprecationWarning implementation (locked: dropped).
* CI lint rule location (locked: Phase 24 home; halvim's
  test_layer_isolation equivalent).
* Snapshot taken before vs after audit gate (locked: AFTER gate +
  AFTER lock acquisition, BEFORE first per-role copy).
* Pending cleanup on rollback (locked: pending stays intact for
  retry per ADR-0118 §"Decision" §2).

Open pushback surfaces (non-exhaustive — probe will surface more):

1. **`release.py` module placement.** ADR-0118 names
   `mindsos_server.release_update`. Where does the function live?
   New `mindsos_server/release.py` module is the obvious home, but
   Phase 24 also lands `propose_for_promotion` — does that go in
   `mindsos_admin/promotion.py` per the Phase 16 PB-1c deferral note,
   or in `mindsos_server/promotion.py` for symmetric server-owned
   placement? ADR-0010 (L2 must not import `mindsos_server`) bears
   on this.

2. **`RELEASE_SHIP_LOCK` substrate.** ADR-0006 amended by ADR-0118
   renames `GLOBAL_PROMOTE_LOCK` → `RELEASE_SHIP_LOCK`. Substrate
   options: (a) `threading.Lock` (in-process only — same as Phase
   22's `admin_tx` BEGIN IMMEDIATE pattern's effective scope); (b)
   SQLite advisory lock via BEGIN IMMEDIATE on a `release_lock` row;
   (c) FalkorDB-side lock. Phase 22 `admin_tx` precedent points at
   (b). v1 is single-process per ADR-0129 §Rationale.

3. **`propose_for_promotion`'s four `PromotionItemKind` values.**
   ADR-0118 names ATOM, STRUCTURE, SUBGRAPH, PIPELINE. PIVOT §7.1
   has full shapes. All four at Phase 24, or staged? Phase 24's
   scope already extends to lazy migration + release manifest;
   staging the kinds could shrink Phase 24 to "ATOM only" with
   STRUCTURE/SUBGRAPH/PIPELINE at a follow-up phase.

4. **`pending_global_<role>` FalkorDB graph layout.** PIVOT §7.2.
   One pending graph per role, or one combined pending? ADR-0118
   §"Decision" §2 says "for each role with pending content."
   Confirm: 10+ pending graphs (one per role) coexist with 10+
   canonical Global role-graphs. Naming convention:
   `mindsos_pending_global_<role>` per PIVOT §7.2.

5. **`releases` table schema.** PIVOT §7.5. New SQLite table in
   `server.db`? Or a separate `version_db/` SQLite database per
   CLAUDE.md's "non-graph state lives in SQLite" + the
   `version_db/` mention? Schema bump probably; coordinate with
   Phase 22's `_SCHEMA_VERSION == 3` baseline.

6. **`shipped_in_release` stamp on `pending_mutations` rows.**
   PIVOT §7.5 specifies. New column on a new table — chicken-and-egg
   with the propose_for_promotion's writes. Migration shape?

7. **Audit event enum extension.** PIVOT §7.6 lists
   `DRAFT_FROZEN`, `DRAFT_UNFROZEN`, `PROMOTION_PROPOSED`,
   `PROMOTION_APPROVED`, `PROMOTION_REJECTED`, `RELEASE_SHIPPED`,
   `MIGRATION_APPLIED`, `MIGRATION_FAILED`. Phase 22 added five
   `EVT_*` constants; Phase 24 adds eight. Confirm payload shapes
   per PIVOT §7.6.

8. **Lazy migration code path.** ADR-0118 §"Decision" §3 +
   PIVOT §7.3. Per-session check on read path:
   `last_synced_release_id < current_release_id` triggers
   per-release rewrite-map application. Where does the check live?
   Phase 19's session creation? Phase 25's `MindsOSServer`
   orchestrator? PHASE_MAP §25 row says the `MindsOSServer` class
   first-construction is Phase 25. Phase 24 may need a stub or
   defer the per-session check.

9. **Release-ship audit gate (ADR-0115 Proposed).** Phase 24 calls
   it; does Phase 24 also ship ADR-0115's surface, or assume
   ADR-0115 lands separately first? ADR-0115 is currently Proposed
   with no shipped code. Phase 24 chat decides scope split.

10. **ADR-0144 §Placement full Accept.** §amendment-1 was a partial
    Accept at Phase 16; full Accept lands when `compute_similarity`
    is wired into the release-ship audit gate at Phase 24.
    Documentary §amendment-2 retires §amendment-1.

11. **ADRs 0113–0117 / 0119 / 0120 are RESERVED but not drafted**
    (PHASE_MAP §24 row + §7 Open Questions). Phase 24 chat may need
    to draft them as part of this phase. Subset that's truly
    load-bearing for v1 (vs deferrable to a follow-up phase): chat
    decides.

12. **CI lint rule location in halvim.** ADR-0129 §Decision specifies
    `tests/unit/test_layer_isolation.py`. halvim's layout uses
    `tests/phase_NN/` for phase-isolated tests + `tests/` cumulative.
    Does the lint rule go in `tests/phase_24/test_layer_isolation.py`
    or a cumulative `tests/test_layer_isolation.py`? Cumulative is
    probably right (the rule guards against drift over time, not
    just at Phase 24).

13. **ADR-0007 flip mechanics.** §amendment to ADR-0007's
    supersession-in-progress banner: Phase 24 ships the code that
    closes the banner's promise. Status header changes from
    `Accepted` (with banner) → `Superseded`. Confirm.

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

**Version bump path: `+phase22 → +phase24`.** Skip the `+phase23`
slot per Phase 23 retirement (pure design-only retirement, no version
bump per PHASE_MAP §1 design-only-phases clause). Precedent: Phase
14a + Phase 15b (both skipped their slots). Note: Phase 17 retirement
DID earn `+phase16 → +phase17` because it shipped 5 LOC of code; do
NOT use Phase 17 as the version-bump precedent here.

**9-site version bump checklist:**
* 6 pkg `__init__.py` (mindsos_core, mindsos_knowledge, mindsos_cli,
  mindsos_admin, mindsos_instances, mindsos_server)
* `pyproject.toml` [project] version + description
* `mindsos_cli/manifest.toml` [mindsos] phase + version
* `docker-compose.yml` image tags (2 occurrences — prod + test)

**Tag `phase-24-confirmed` AFTER squash-merge only** (per
`feedback_release_tag_after_squash_merge_only.md`). 8-step ordering
strict.

══════════════════════════════════════════════════════════════════════
EXIT CRITERIA
══════════════════════════════════════════════════════════════════════

Phase 24 squash-merges to main; `phase-24-confirmed` tag pushed AFTER
merge; `release.yml` green; GitHub Release created.

ADR status flips at ship:
* **ADR-0007** → Superseded
* **ADR-0118** → Accepted
* **ADR-0141** → Accepted
* **ADR-0144** → fully Accepted (§amendment-1 retires; §amendment-2
  documents the full §Placement flip)
* **ADR-0049 / 0053 / 0056** → Superseded (per their Phase 16
  §amendment-1 documentation)

Phase 24 writes `confirmation_docs/PHASE_25_NEXT_CHAT_PROMPT.md` as
exit artifact.

══════════════════════════════════════════════════════════════════════
