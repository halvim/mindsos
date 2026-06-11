# A0 — Pre-Phase-39 Housekeeping Commit Checklist

> **Drafted:** 2026-06-02 (Phase 43 pre-R0 chat — surfaced as S9 blocker).
> **Owner:** Henrique (manual run, local box).
> **Status:** Blocker for Phase 39 branch creation AND Phase 43 branch creation.
> **Why:** The entire post-Phase-38 corpus (4 chat closures, 5 ADRs 0150 §am-4 + 0151-0154 + 0155-0159, HANDOFF.md, this seed, the Phase 39 design log, the Phase 43 prompt, the `docs/_workbench/` tree, all 144 ADRs themselves) is **untracked or modified on `main` but not committed**. Branching off `main` would not see any of it.

---

## §0. Why this is not a phase

Stream A items go on `main` directly (no `phase-NN-confirmed` tag, no `mindsos confirm-phase`, no version bump) per `STREAM_A_BACKLOG.md` convention. A0 is the corpus-commit prerequisite that **precedes** the Stream A interleaved track itself.

The work is documentation + design housekeeping. Code (`mindsos_*/`) is unchanged in A0 except for 13 sentinel-test path fixes.

---

## §1. Current state

```
last commit on main:    5236857  "Phase 38 — next-chat prompt for L4/L5 follow-up plan kickoff"
untracked entries:      20
modified files:         16
removed root .md files: 44 (notes-phase-NN.md moved to confirmation_docs/notes/)
diff stat:              ~5,800 net line changes
```

Run `git status --short` to confirm before starting.

---

## §2. Pre-flight checks

1. `git fetch origin && git status` — confirm `main` is current; no remote-side drift.
2. `git log --oneline -1` should show `5236857`. If not, A0 was already partially done — read remaining state and adjust scope.
3. `ls _archive_Layered_Intelligence/` should exist as an untracked directory (large; ~10s of MB).
4. **Recommend:** create a `pre-a0-backup` tag on current `main` HEAD before starting: `git tag pre-a0-backup` (rollback insurance).

---

## §3. Suggested grouping — 4 commits

Order matters. Land in sequence; each builds on the prior.

### A0-1 — Housekeeping moves + ADR tree + parent-tree archive

**Goal:** Move parent-tree content into MindsOS folder layout per HANDOFF §7.2-§7.3.

```
removes:   notes-phase-*.md            (44 files at root)
adds:      confirmation_docs/notes/    (destination of the move)
adds:      _archive_Layered_Intelligence/   (forensic; pre-housekeeping content)
adds:      docs/decisions/             (full ADR tree: 144 base + 0150 §am-4 + 0151-0159 + machinery)
modifies:  mkdocs.yml                  (nav: add Decisions section + L4/L5 dev pages)
modifies:  tests/phase_*/test_adr_amendment_sentinels.py × 13  (path fix: _ADR_DIR drops .parent)
removes:  checksums.txt, mindsos-phase04.tar.gz                (stray pre-housekeeping artifacts)
modifies:  PHASE_38_DESIGN_LOG.md       (Chat C IL-8 R6-lesson preservation paragraph)
modifies:  docs/changelog/CHANGELOG.md (release log additions)
removes:   confirmation_docs/PHASE_38_NEXT_CHAT_PROMPT.md  (superseded by HANDOFF reading-map)
```

Commit message:
```
A0-1: housekeeping — relocate notes to confirmation_docs/, vendor ADR tree, archive parent

- Move 44 root-level notes-phase-NN.md files into confirmation_docs/notes/ per HANDOFF §7.3 layout.
- Vendor docs/decisions/ ADR tree (144 base ADRs + machinery; 0150 §am-4 + 0151-0159 added by closures).
- Archive forensic parent-tree content under _archive_Layered_Intelligence/ per HANDOFF §7.2.
- Drop stale root artifacts (checksums.txt, mindsos-phase04.tar.gz, PHASE_38_NEXT_CHAT_PROMPT.md).
- Fix 13 sentinel-test _ADR_DIR paths post-move (drop .parent; ADRs now live in-tree).
- Extend mkdocs.yml nav with Decisions section + L4/L5 dev-page links.
- Append Chat C IL-8 R6-lesson preservation paragraph to PHASE_38_DESIGN_LOG.md.
- Update CHANGELOG.

No source code touched. Sentinel tests verified green post-path-fix:
  pytest tests/phase_13/test_adr_amendment_sentinels.py tests/phase_36/test_adr_amendment_sentinels.py
```

Pre-commit verification:
```bash
pytest tests/phase_13/test_adr_amendment_sentinels.py \
       tests/phase_14/test_adr_amendment_sentinels.py \
       tests/phase_15a/test_adr_amendment_sentinels.py \
       tests/phase_15b/test_adr_amendment_sentinels.py \
       tests/phase_16/test_adr_amendment_sentinels.py \
       tests/phase_17/test_retirement_sentinels.py \
       tests/phase_28/test_adr_amendment_sentinels.py \
       tests/phase_29/test_adr_amendment_sentinels.py \
       tests/phase_30/test_adr_amendment_sentinels.py \
       tests/phase_31/test_adr_amendment_sentinels.py \
       tests/phase_35/test_adr_amendment_sentinels.py \
       tests/phase_36/test_adr_amendment_sentinels.py
```

All 12 must pass before commit. (`phase_17` is `test_retirement_sentinels.py`.)

---

### A0-2 — Foundational handoff + sister projects

**Goal:** Land the canonical entry point + project instructions + sister project intake.

```
adds:      HANDOFF.md
modifies:  CLAUDE.md                   (expanded with Phase 43+ project status block)
adds:      docs/dev/l4_intelligence_design_notes.md
adds:      docs/dev/l5_mental_model_design_notes.md
adds:      docs/dev/use_cases_text_realm.md
adds:      projects/   (README.md + dwf_mapping/ + wsd/ + fol/ — sister project ANALYSIS + FUTURE_CHAT_PROMPT + source/)
```

Commit message:
```
A0-2: handoff + sister projects — HANDOFF.md, CLAUDE.md expansion, L4/L5 dev notes, projects/

- Add canonical HANDOFF.md as the entry point (per HANDOFF §0).
- Expand CLAUDE.md with Phase 43+ operating-mode block + Cowork setup notes.
- Land L4 + L5 design-notes pages under docs/dev/ (referenced by Chat A + Chat B closures).
- Land use_cases_text_realm.md (read by L4/L5 notes + FOL/WSD chats).
- Intake 3 sister projects (DWF / WSD / FOL) into projects/ per HANDOFF §5.

No source code touched.
```

Pre-commit verification:
```bash
grep -c "^##" HANDOFF.md     # expect ~12 top-level sections
ls projects/dwf_mapping/ projects/wsd/ projects/fol/
ls docs/dev/ | grep -E "l4_|l5_|use_cases"
```

---

### A0-3 — Chat closures + Chat C plan + workbench

**Goal:** Land the four closure docs + Chat C plan + the active `_workbench/` index.

```
adds:      confirmation_docs/CHAT_A_DECISIONS.md          (L4 design-resolution)
adds:      confirmation_docs/CHAT_A_L4_BASELINE.md        (Chat A R0 baseline)
adds:      confirmation_docs/CHAT_B_DECISIONS.md          (L5 + note-fork)
adds:      confirmation_docs/CHAT_PLAN_L4_L5.md           (chat-split decision record)
adds:      confirmation_docs/L1_L3_REFRAME_DECISIONS.md   (ADRs 0155-0159)
adds:      confirmation_docs/L2_CHAT_DECISIONS.md         (ADRs 0151-0154)
adds:      confirmation_docs/L4_L5_PLAN_NEXT_CHAT_PROMPT.md
adds:      confirmation_docs/POST_PHASE_38_PHASE_MAP.md   (active Phase 39-49 plan)
adds:      docs/_workbench/   (L2_FUTURE_WORK, STREAM_A_BACKLOG, cookbook_routing, L0_FUTURE_WORK, L3_FUTURE_WORK, L4_FUTURE_WORK, etc.)
```

Commit message:
```
A0-3: chat closures + Chat C plan + workbench index

- Land 4 design-chat closure docs in confirmation_docs/:
  - CHAT_A_DECISIONS (L4 architecture, 2026-05-28)
  - CHAT_B_DECISIONS (L5 + note-fork retired, 2026-05-31)
  - L1_L3_REFRAME_DECISIONS (ADRs 0155-0159, 2026-06-01)
  - L2_CHAT_DECISIONS (ADRs 0151-0154, 2026-06-01)
- Land POST_PHASE_38_PHASE_MAP.md (Chat C plan-authoring closure 2026-06-02; Phase 39-49 4-rail DAG).
- Land Chat A R0 baseline + chat-split record + L4/L5 plan next-chat prompt for forensic trace.
- Land docs/_workbench/ — active backlog indices (L2_FUTURE_WORK, STREAM_A_BACKLOG, L0/L3/L4_FUTURE_WORK, cookbook_routing).

These are documentation; no source code touched. References between them and HANDOFF.md become resolvable post-merge.
```

Pre-commit verification:
```bash
ls confirmation_docs/CHAT_A_DECISIONS.md confirmation_docs/CHAT_B_DECISIONS.md
ls confirmation_docs/L1_L3_REFRAME_DECISIONS.md confirmation_docs/L2_CHAT_DECISIONS.md
ls confirmation_docs/POST_PHASE_38_PHASE_MAP.md
ls docs/_workbench/STREAM_A_BACKLOG.md docs/_workbench/L2_FUTURE_WORK.md
grep -l "Phase 43" confirmation_docs/POST_PHASE_38_PHASE_MAP.md  # sanity: phase 43 row present
```

---

### A0-4 — Phase 39 design pass + Phase 43 seed

**Goal:** Land Phase 39 design-pass output + Phase 43 prompt + Phase 43 R0 picks seed (this file).

```
adds:      confirmation_docs/PHASE_39_DESIGN_LOG.md
adds:      confirmation_docs/PHASE_39_NEXT_CHAT_PROMPT.md
adds:      confirmation_docs/PHASE_43_NEXT_CHAT_PROMPT.md
adds:      confirmation_docs/PHASE_43_R0_PICKS_SEED.md   (this chat's output)
adds:      confirmation_docs/A0_HOUSEKEEPING_COMMIT_CHECKLIST.md   (this file)
```

Commit message:
```
A0-4: Phase 39 design close + Phase 43 seed + this checklist

- Land Phase 39 design-pass closure log (saturation 3 reversal-free rounds; locked picks per §2).
- Land Phase 39 next-chat prompt (for the impl + tester loop that ships rename + §am-4 surgery).
- Land Phase 43 next-chat prompt + R0 picks seed (this chat's pre-R0 design pass; 4 rounds + R0a probes + N-now-C resolution).
- Land A0 checklist (this file) for forensic trace of why corpus was committed in 4 commits.

Post-A0 state: branching off main now yields the full housekeeping + closure + design baseline. Phase 39 impl branch can be created.
```

Pre-commit verification:
```bash
ls confirmation_docs/PHASE_39_*.md confirmation_docs/PHASE_43_*.md
grep "S9" confirmation_docs/PHASE_43_R0_PICKS_SEED.md   # sanity: this chat's surfaced blocker recorded
```

---

## §4. Post-A0 verification

After all four commits land on `main`:

```bash
git log --oneline -5
# Should show A0-4, A0-3, A0-2, A0-1, then 5236857.

git status
# Should be clean (no M / D / ??).

git ls-files | wc -l
# Significantly higher than pre-A0 count.

ls docs/decisions/adr/ | wc -l
# Expect ~159 ADR files (144 base + 0150 §am-4 + 0151/52/53/54 + 0155-0159 + machinery).

pytest -q --tb=no 2>&1 | tail -3
# Cumulative should pass: ~3,379 / 57 skipped / 0 failed (Phase 38 baseline).

mkdocs build 2>&1 | tail -10
# Should build; warning count is the still-outstanding ~50 filename-normalization items (PB-8, lands Phase 42).
```

If pytest fails post-A0-1 with sentinel test errors, A0-1 path-fix was incomplete — investigate the failing test's `_ADR_DIR` resolution before continuing.

---

## §5. After A0 lands

1. Tag: `git tag a0-corpus-landed` (or similar; optional, but useful for the Phase 39 chat to reference).
2. **Open Phase 39 impl chat.** Hand it: `confirmation_docs/PHASE_39_DESIGN_LOG.md` (primary) + `confirmation_docs/PHASE_39_NEXT_CHAT_PROMPT.md` (spec) + `docs/_workbench/STREAM_A_BACKLOG.md` (A1 `release.yml` retention amendment lands FIRST per Phase 39 design pass).
3. Phase 39 ships → `phase-39-confirmed` tag.
4. **Open Phase 43 impl chat.** Hand it: `confirmation_docs/PHASE_43_R0_PICKS_SEED.md` (primary; picks already locked) + `confirmation_docs/PHASE_43_NEXT_CHAT_PROMPT.md` (spec) + Phase 39 confirmed metadata.

---

## §6. Risks

- **A0-1 is the largest commit.** ~5,800 net lines, 200+ files moving. Squash review is awkward; consider whether to split into A0-1a (notes moves + archive) and A0-1b (ADR tree vendor) if the reviewer ergonomics matter. Defaulted to single commit for atomicity.
- **The 13 sentinel-test path fixes are load-bearing for A0-1.** If `_ADR_DIR` path is wrong post-move, the entire sentinel chain breaks and every subsequent phase fails its sentinel test. Run `pytest tests/phase_*/test_adr_amendment_sentinels.py tests/phase_*/test_retirement_sentinels.py` after A0-1 lands.
- **`_archive_Layered_Intelligence/` is large.** May exceed GitHub PR size warnings. If pushing to remote, consider whether the archive should be `.gitignored` instead (note: HANDOFF §7.2 treats it as authoritative forensic state, so committing is intentional).

---

*End of A0_HOUSEKEEPING_COMMIT_CHECKLIST.md. Drop after A0-4 lands and `a0-corpus-landed` tag is in place.*
