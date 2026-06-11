# Phase 43 — Ship Execution Chat Prompt

> **You are the Phase 43 ship execution chat.** Predecessor: the Phase 43 full design pass (closed 2026-06-03) captured in `confirmation_docs/PHASE_43_DESIGN_LOG.md`. Your job is to execute PR1 + PR2 per the locked design log, run cumulative gates per the tester runbook, and ship Phase 43 to `main`.

═══════════════════════════════════════════════════════════════════
ROLE
═══════════════════════════════════════════════════════════════════

Act as the impl + tester chat for Phase 43 (Rail A slot 2, L2 schema-v2 + 4 new role-graphs + mutation_discipline runtime invariant + storage_mode discipline + bootstrap `applies_after` field + 2 ADR amendments + 4 ADR in-place edits + cleanup). The design pass closed; you do NOT re-litigate design picks. You execute. Per the project's skeptical-reviewer default style, you push back on impl-time discoveries (gate failures, file-state surprises, R1-amendments) — not on closed architectural decisions.

═══════════════════════════════════════════════════════════════════
PREREQ CHECK (run before anything else)
═══════════════════════════════════════════════════════════════════

1. `git tag --list | grep phase-39-confirmed` — must exist (Phase 43 branches off this tag).
2. `git status` — clean working tree.
3. `cat mindsos_cli/manifest.toml | grep "^phase"` — should read `phase = "39"`.
4. `git log --oneline -3` — top should be `7a8bf10` or descendant; main-tip = `phase-39-confirmed`.
5. Confirm `confirmation_docs/PHASE_43_DESIGN_LOG.md` exists.

If any check fails, surface immediately. Do not branch.

═══════════════════════════════════════════════════════════════════
REQUIRED READING (in order; do NOT skip)
═══════════════════════════════════════════════════════════════════

1. **`HANDOFF.md` §1, §2.2, §3.1.11 (Phase 39 ship), §3.1.12 (Phase 43 design pass closure), §9 (process discipline).**
2. **`confirmation_docs/PHASE_43_DESIGN_LOG.md` IN FULL.** This is your spec. Sections you will execute against:
   - §5: PR1 module touches + test surface + 7-commit boundary.
   - §6: PR2 module touches + test surface + 6-commit boundary.
   - §7: process locks (PR1 owns manifest bump; both PRs target `phase-43` branch; single squash).
   - §8: the 5 R2 amendment text drafts — paste these verbatim into the target ADR files (insertion points specified per draft).
   - §9: reserved for YOUR impl-time amendments (gate failures, follow-up commits, ship closure anomalies, carry-forwards). You will append §9.1 through §9.6 as you go.
   - §11: tester runbook + risk notes (2-PR sync triples Mac/Linux coupling points; parallel-rail collision dormant; cumulative gate timeline doubles).
3. **`confirmation_docs/PHASE_43_R0_PICKS_SEED.md`** — historical pre-R0 picks. Note design-log §2 reconciliation for items that drifted post-R0.
4. **`confirmation_docs/PHASE_43_R0B_DERIVATIONS.md`** — `applies_after` edge set, L2Schema sketch (with NPB7-1 + NPB8-1 corrections per design log §2/§3).
5. **`confirmation_docs/PHASE_39_DESIGN_LOG.md` §9** — manifest-bump checklist + pre-confirm-phase squash discipline + ship-closure-anomaly recovery procedure you may need.
6. ADRs on disk you will touch:
   - `docs/decisions/adr/0150-l2-knowledge-lifecycle.md` — append §amendment-5 per design log §8.1.
   - `docs/decisions/adr/0153-l2-mutation-discipline.md` — append §amendment-1 per design log §8.2.
   - `docs/decisions/adr/0094-confidence-pipeline-level.md` — in-place edit lines 77-80 per design log §8.3.
   - `docs/decisions/adr/0151-l2-storage-tiers.md` — frontmatter Related block replacement per design log §8.4.
   - `docs/decisions/adr/0143-kl-write-handle-pattern.md` — §Implementation references cross-ref append per design log §8.5.
   - 6 ADRs for stale-example cleanup per design log §5.1 (`ROLE_MEMORIES` / `memory_iri` / `memories-` example rewrites): 0045, 0139, 0143 main body, 0146 main body outside §am-3, 0147, 0154.

═══════════════════════════════════════════════════════════════════
EXECUTION ORDER (PR1 → PR2 → squash → confirm-phase)
═══════════════════════════════════════════════════════════════════

Follow the tester runbook at design log §11.1. Sequence:

1. Branch: `git checkout -b phase-43 phase-39-confirmed`.
2. PR1 commits 1-7 per design log §5.3. Commit 5 (sentinel tests + 9-surface manifest bump) is the cumulative-gate trigger.
3. Mac → push phase-43 branch → Linux pulls → cumulative gate via `docker compose run --rm mindsos-test pytest tests/`.
4. If gate fails: surface failures; add follow-up commits 5b/5c per Phase 39 §9.3 precedent. Record in design log §9.1.
5. PR2 commits 1-6 per design log §6.3. Commit 5 (tests) is PR2's cumulative-gate trigger; commit 6 is HANDOFF + PHASE_MAP §4 rewrite + L2_FUTURE_WORK + 3 doc files + design log §9 amendments + PHASE_44 seed.
6. Mac → push → Linux cumulative gate. If fails: follow-up commits per §9.3 precedent.
7. Mac squash-merges phase-43 to main (atomic; per Phase 39 §9.5 discipline this MUST land before confirm-phase).
8. Mac pushes main; Linux pulls main (post-squash).
9. Linux: `mindsos confirm-phase --phase 43 --notes-file notes-phase-43.md` from post-squash main.
10. Linux commits CONFIRMED.md + notes; push.
11. Mac tags `phase-43-confirmed` at the squash-merge commit; push tag.

═══════════════════════════════════════════════════════════════════
KEY GOTCHAS (carry-forward from Phase 39 + Phase 43 design pass)
═══════════════════════════════════════════════════════════════════

- **9-surface manifest bump atomic at PR1 commit 5.** Per design log NPB10-1 + Phase 39 §9.4. 11 file edits in lockstep. Doctor self-test gates.
- **Pre-confirm-phase squash-merge discipline.** Per Phase 39 §9.5: squash-merge MUST land + push to `main` BEFORE `mindsos confirm-phase` runs. Skipping yields semantically-backwards main commit order requiring reflog recovery.
- **2 cumulative gates this phase** (post-PR1 + post-PR2) vs Phase 39's 1. Budget time for follow-up commits per gate.
- **Phase 13 sentinel test extension** (`tests/phase_13/test_dispatch.py` gains 4 new role assertions) lands in PR2 commit 5, NOT PR1 — because the 4 new schemas ship in PR2. PR1 sentinel tests assert §am-5 text presence; PR2 sentinel tests assert new role-graph runtime registration.
- **Phase 33 test updates** (`tests/phase_33/test_consolidate_mm_capacity.py` 5 line changes: `memory_id` → `episode_id` + IRI literal `:memory:` → `:episode:`) land in PR2 commit 5 alongside the consolidate.py retarget per design log §6.1 NPB13-5.
- **`mindsos_core/schema.py` is NOT touched** despite PHASE_MAP §4 row line 443 claiming so. Design log §3 reconciliation: L2Schema(Schema) subclass in `mindsos_knowledge/schemas/_base.py` only. PR1 leaves L1 alone.
- **No `tools/migrate_phase_43_confidence_strip.py`.** Per design log §3: detector form is `tools/check_phase_43_confidence_state.py`. If you find yourself authoring a migrator, stop — read design log §3 reconciliation.
- **PHASE_44 seed at PR2 commit 6** per design log NPB13-1 (not PHASE_46). Phase 44 inherits L2-37 consumer + L2-39 audit constant + L2-41 KL retention surface.

═══════════════════════════════════════════════════════════════════
OUT OF SCOPE
═══════════════════════════════════════════════════════════════════

- Re-litigation of any design log §1-§8 pick. Design closed across 18 saturation rounds.
- Any phase row other than Phase 43 in `POST_PHASE_38_PHASE_MAP.md`.
- L0 substrate (Phase 44), Rail B (Phase 40/41/42), dream family (Phase 45), L4/L5/Integration C (Phase 46-49).
- WSD / FOL / DWF chat scope.
- Stream A items A1-A8 (separate maintenance track).
- `task_patterns.confidence` removal (kept per ADR-0152 §2 + design log §3).

Impl-time amendments (gate failures, file-state surprises) are EXPECTED and ARE in scope — record in design log §9.1+.

═══════════════════════════════════════════════════════════════════
OUTPUTS EXPECTED AT CHAT CLOSE
═══════════════════════════════════════════════════════════════════

Per `POST_PHASE_38_PHASE_MAP.md §1 + §4 Phase 43 row` (the row body is stale; design log §5+§6 is authoritative):

- `phase-43` branch off `phase-39-confirmed` → squash-merged PR → `phase-43-confirmed` tag from main-tip.
- `confirmation_docs/PHASE_43_CONFIRMED.md` via `mindsos confirm-phase`.
- `confirmation_docs/notes/notes-phase-43.md` (tester notes).
- 5 ADR amendment/edit landings per design log §8.
- 9 existing schema audits (discipline transcription) + 4 new schema files + all PR2 consumer wiring per design log §5+§6.
- `tools/check_phase_43_confidence_state.py` detector.
- `tests/phase_43/` test suite (~14 files per design log §5.2 + §6.2).
- Stale-example cleanup in 6 ADRs + ADR-0151 frontmatter + ADR-0094 §am-1 in-place + ADR-0143 cross-ref + D-L2-3/4/10 corrections (PR1 commits 6+7).
- Manifest bump 9-surface checklist applied at PR1 commit 5 per design log §9.4 / Phase 39 §9.4.
- `HANDOFF.md` §1 line bump + §2.2 update reflecting Phase 43 ship + §3.1.X status flip (new section appending after §3.1.12).
- `confirmation_docs/POST_PHASE_38_PHASE_MAP.md` §4 Phase 43 row **scope-rewrite** per design log NPB11-2 + Status: SHIPPED.
- `docs/future_work/L2_FUTURE_WORK.md` §11 routing notes updated (L2-29/30/31/32/33/37(field)/40 marked CLOSED — shipped Phase 43; routing-note text per design log NPB14-2).
- `confirmation_docs/PHASE_44_NEXT_CHAT_PROMPT.md` — seed for Phase 44 (L0 substrate; gates on `L0_SUBSTRATE_CHAT` closure independently).
- `confirmation_docs/PHASE_43_DESIGN_LOG.md` §9 filled with impl-time amendments accumulated during this chat.

═══════════════════════════════════════════════════════════════════
PROCESS NOTES (inherited)
═══════════════════════════════════════════════════════════════════

- **Probe-first** (Phase 38 R5-PB-I; Phase 39 §8). Read file state before mutating.
- **Tester two-machine sync** per HANDOFF §9: Mac runs git, Linux runs pytest via `docker compose run --rm mindsos-test pytest <args>`. Bridge is `git push` / `git pull`. No shared FS.
- **In-place ADR text edits** are legitimate house style for pre-ship amendments (per design log §8.3/§8.4/§8.5). Git log is the audit trail.
- **Mid-granularity commit splits** per Phase 39 PB-R1-E. Each commit must be independently buildable; do not split finer than that (creates non-buildable intermediates that defeat per-commit gating).
- **Saturation discipline** (Chat C): for impl-time amendments, three consecutive reversal-free rounds = ready to land in §9. Reversals reset the clock.

═══════════════════════════════════════════════════════════════════
SUCCESS CRITERION
═══════════════════════════════════════════════════════════════════

Phase 43 shipped iff:
1. `phase-43-confirmed` tag on `main`.
2. `PHASE_43_CONFIRMED.md` on disk via `mindsos confirm-phase`.
3. Cumulative gate green: estimated ~3620-3750 passed (Phase 39 ended at 3501; Phase 43 adds ~120-250 new tests).
4. `mkdocs build` clean (no NEW broken-link warnings beyond Phase 39 carry-forward).
5. Doctor self-test pass post-bump (9 surfaces consistent).
6. HANDOFF.md + PHASE_MAP §4 Phase 43 row both flipped to SHIPPED.
7. PHASE_44 seed on disk.

═══════════════════════════════════════════════════════════════════
FIRST ACTION
═══════════════════════════════════════════════════════════════════

Run the prereq check above. Confirm `phase-39-confirmed` tag + clean working tree + manifest phase = "39" + design log on disk. Then ack required reading completion to the user before branching.
