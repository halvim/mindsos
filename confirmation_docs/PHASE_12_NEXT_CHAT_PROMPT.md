# Phase 13 — Handoff Prompt (authored at Phase 12 close)

> Authored 2026-05-16 at close of Phase 12 ship. Paste the **PROMPT
> BODY** below into a fresh Claude chat (MindsOS project) when ready
> to design + ship Phase 13. The prompt is a **navigation guide**,
> not a content dump — every fact about scope, locks, prior phases,
> and modules lives in files; the prompt routes you there.

---

## PROMPT BODY (copy from here)

```
══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 13 design + implementation
══════════════════════════════════════════════════════════════════════

Project: MindsOS — folder `halvim_mindsos/` under `Layered Intelligence`.

ROLE: Critical design reviewer + implementer for Phase 13. Follow
the project-level CLAUDE.md skeptical-default + terse + pros/cons +
alternatives behavior.

PHASE 13 SCOPE — L2 Schemas (alignment, lexicon, ontology, concepts)
Read the Phase 13 row in `halvim_mindsos/confirmation_docs/PHASE_MAP.md`
(grep `^### Phase 13`). PHASE_MAP is the source of truth for the
row's Features / Tests / Risks / Docs fields — do not paraphrase
here; read it.

Deps: 04 (Phase 04 — L1 Schema), 12 (Phase 12 — L2 Identifiers).
Layer: L2. Net-new? No (per PHASE_MAP). Second L2 phase.

BEFORE DOING ANYTHING ELSE — REQUIRED READING (in order):

1. `MEMORY.md` (auto-loaded). Every `feedback_*` entry is a hard
   rule. Particularly load-bearing for Phase 13:
   * feedback_batch_fix_dont_iterate.md
   * feedback_never_suggest_skip_tests.md
   * feedback_sandbox_vs_mac_git_separation.md
   * feedback_release_tag_after_squash_merge_only.md
   * feedback_sentinel_paths_runtime_only.md
   * feedback_phase_baseline_literal_audit.md
   * feedback_confirm_phase_timeout.md
   * feedback_confirm_phase_file_paths.md
   * feedback_confirm_phase_invocation_paths.md
   * feedback_state_file_key_canonicalization.md
   * feedback_tomllib_stdlib_fallback.md
   * feedback_state_file_serializer_deserializer_symmetry.md
   * feedback_state_version_audit_scope.md
   * feedback_new_top_level_package.md  ← still relevant if Phase 13 adds anything; less load-bearing now that mindsos_knowledge exists
   * feedback_host_pip_refresh_on_new_package.md  ← NEW Phase 12 B-12-T1 audit class

2. `project_mindsos_phase_12_implemented.md` (memory) — canonical
   inventory of what Phase 12 shipped: 14 IRI builders, parser table,
   REF_TYPES, ref-key helpers, role constants, CLI sub-subgroup,
   4-pkg doctor parity, ADR-0044 §amendment-1, B-12-T1 hotfix class
   (host-pip refresh on new package), carry-forward list.

3. `halvim_mindsos/confirmation_docs/PHASE_12_DESIGN_LOG.md` —
   Phase 12 pushbacks (PB-1..22); Step-0 9-probe audit table
   (0 prior-phase cascade); carry-forward Phase 13 may or may not
   pick up (MetagraphSchema scanner is the obvious candidate).

4. `halvim_mindsos/confirmation_docs/PHASE_12_CONFIRMED.md`
   `tester_notes` — the load-bearing field per PHASE_MAP §0.
   Read for any surprises / open issues from Phase 12.

5. `halvim_mindsos/confirmation_docs/PHASE_11_CONFIRMED.md`
   `tester_notes` (two-prior context per §0 read rule).

6. `project_mindsos_l2_redesign_locks.md` (memory) — KL drops
   write API; hybrid validators; MetagraphView read-only; server
   owns importers. Phase 13 is the second L2 phase — these locks
   continue to bound the design space.

7. `halvim_mindsos/confirmation_docs/PHASE_MAP.md` §1-§2 (project
   process + chat etiquette) if unfamiliar.

ADRs IN SCOPE — read the ones whose status you need to verify or
amend. Phase 13 likely touches:

* ADR-0017 (Schema strictness opt-in; Phase 04 baseline) — verify
  the L2 role-graph schemas honor `strict=False` per
  DESIGN_UPPER_LAYER_ROLES.md §2.1 (deferred tightening rule).
* L2-namespace ADRs covering alignment / lexicon / ontology /
  concepts schema sketches (currently in
  `_source_backup/docs_legacy_full/DESIGN_UPPER_LAYER_ROLES.md`
  §2.1 — NOT yet ADRs; decide whether to promote to ADR-0149+ in
  this phase).
* ADR-0134 (schema migration scanner) — STAYS Proposed unless
  Phase 13 bumps a MetagraphSchema, in which case the
  MetagraphSchema-scanner extension (Phase 11 PB-7 C carry-forward)
  fires HERE for the first time.

CARRY-FORWARD FROM PHASE 12 THAT MAY HIT PHASE 13 (read
PHASE_12_DESIGN_LOG.md §4 + project_mindsos_phase_12_implemented.md
"Carry-forward" section for full list):

* **MetagraphSchema scanner** — Phase 11 PB-7 C deferred
  MetagraphSchema migration (MetaEdge / IntergraphEdge / etc.
  type vocab) to "Phase 12+." Phase 12 shipped no metagraph/schema
  surface, so it re-carried-forward. If Phase 13 bumps a
  MetagraphSchema, the scanner ships HERE. Surface as a pre-design
  pushback if PHASE_MAP §Phase 13 implies a MetagraphSchema bump.
* **ADR-0134 Proposed → Accepted flip** — owed to Phase 15
  (Importers, first KL consumer of migrate_from output). Phase 13
  is one step earlier; the flip likely stays deferred. Surface
  only if Phase 13 unexpectedly becomes the first consumer.
* **Migration playbook content** — same trigger as ADR-0134 flip
  (Phase 15).
* **Per-edge alignment IRI builder** (if Phase 13's alignment
  schema needs versioned per-edge IRIs) — Phase 12 shipped only
  `alignment_role()` graph-name helper. Per PB-4 lock, per-edge
  builders are deferred until a consumer needs them. Phase 13
  alignment schema MAY surface this need.

THE EXECUTION DISCIPLINE (Phase 02-12 PRECEDENT — DO NOT INVENT
NEW PATTERNS):

* Two-machine setup: Mac for Claude sessions + git ops; Linux for
  Docker + confirm-phase. Per `user_two_machine_setup.md`. Tag
  every command with [Mac] or [Linux].
* notes-phase-13.md lives at REPO ROOT, NOT in confirmation_docs/.
* `mindsos confirm-phase --init-notes 13` writes
  ./notes-phase-13.md at repo root.
* Pre-build the test image before confirm-phase. Timeout 1800s.
  confirm-phase runs pytest inside the test image with the
  notes-phase-*.md COPYd in.
* **NEW from Phase 12 B-12-T1:** if Phase 13 adds any new top-level
  Python package, host `pip install -e . --user
  --break-system-packages` MUST be re-run on the Linux box BEFORE
  any host-native `mindsos` invocation works. See
  `feedback_host_pip_refresh_on_new_package.md`.
* Ship sequence is the 8-step strict ordering in
  `feedback_release_tag_after_squash_merge_only.md` — do NOT tag
  before squash-merge.

DESIGN-PHASE WORKFLOW THE USER EXPECTS (Phase 10-12 precedent):

1. Design reanalysis with pushbacks BEFORE implementing. Number
   every pushback (PB-N), give the user pros/cons + a
   recommendation. User signs off batch-by-batch with "agreed".
2. After design sign-off, present a numbered implementation step
   list. The user signs off step-by-step. Phase 11 had 31 steps;
   Phase 12 had 42 (new-package overhead).
3. Tests written in one batch at end (Phase 10 + 11 + 12 chose
   this; ~60-120 test files).
4. Phase-NN tests run FIRST in isolation, THEN cumulative `tests/`
   sweep (feedback_test_order_current_then_cumulative.md).
5. Hotfix cycles labeled B-13-T1..TN. File new feedback memories
   at chat-end for any new audit classes.

THE PHASE-BASELINE LITERAL AUDIT (NON-NEGOTIABLE STEP 0):

Before Phase 13 lands ANY code, grep ALL of tests/ for:

* state-file version literals (`_state_version == N`,
  `CURRENT_VERSION == N`)
* phase-string literals (`"12"`, `"0.0.0+phase12"`,
  `mindsos:phase12-prod/test`)
* index-count literals (`len(DEFAULT_INDEXES) == N`,
  `len(c.calls) == N`)
* summary-shape literals
* timeout literals (`_CONFIRM_PHASE_TIMEOUT_SECONDS == N`)
* package-count literals (now 4 packages incl mindsos_knowledge)

Predict + patch ALL in one commit per
`feedback_batch_fix_dont_iterate.md`. Phase 11 + Phase 12 BOTH
surfaced ZERO prior-phase patches — streak of 2; celebrate but
don't assume; re-run the audit.

Also re-run the 9 Step-0 probes Phase 12 used (see
PHASE_12_DESIGN_LOG.md §3 for the audit table):

* state-file version stays at current
* phase-string literal sites (now 9 bump points incl
  mindsos_knowledge/__init__.py)
* caplog/capsys assertions over loader paths
* Dockerfile COPY discipline (tree-wide; new files COPY for free
  unless a new top-level pkg ships)
* confirm-phase pytest summary regex (verify still matches both
  framed + bare forms per B-10-T6 fix)
* doctor 4-pkg version-string parity (no longer 3-pkg)
* ref-key helper literals in any test
* cumulative-count literal in any test
* ADR-0045 closure sentinel (any prior-phase test assume builder
  count?)

MISTAKES PRIOR PHASES MADE — DO NOT REPEAT:

* Suggested --skip-tests (Phase 10 fail). See
  feedback_never_suggest_skip_tests.md.
* Iterated patches one-failure-at-a-time (Phase 10 cost ~2h).
  feedback_batch_fix_dont_iterate.md.
* Added docs/*.md to SENTINEL_PATHS (Phase 10 RPB-8).
  feedback_sentinel_paths_runtime_only.md.
* Conflated notes-phase-NN.md (repo root, input) with
  PHASE_NN_CONFIRMED.md (auto-generated output). Phase 11 PB-25
  fixed by splitting into 4 sub-steps.
* Ran `git add` in sandbox shell (corrupts Mac .git).
  feedback_sandbox_vs_mac_git_separation.md.
* Tagged phase-NN-confirmed BEFORE squash-merge.
  feedback_release_tag_after_squash_merge_only.md.
* Used `import tomli` instead of stdlib `tomllib` (B-11-T1).
  feedback_tomllib_stdlib_fallback.md.
* Used `e["id"]` / `n["id"]` instead of `edge_id` / `node_id`
  when rehydrating state files (B-11-T2).
  feedback_state_file_key_canonicalization.md.
* Forgot to refresh the Linux host `pip install -e .` after
  shipping a new top-level package (B-12-T1). Surfaced as
  `ModuleNotFoundError: No module named 'mindsos_knowledge'` at
  `mindsos confirm-phase --init-notes 12`.
  feedback_host_pip_refresh_on_new_package.md.

TONE + STYLE THE USER PREFERS:

* Concise. Skeptical default per project CLAUDE.md.
* When giving commands during execution, ONE command at a time
  with expected outcome, then wait for the user's reply. Tag with
  [Mac] / [Linux] / [sandbox].
* No filler ("Great question", "Interesting approach").
* No restating the user's message.
* No emojis unless the user uses one first.
* Pushback on vague requirements; do not guess.
* Critical reviewer first, implementer second.
* When the user says "agreed... proceed", power through obvious
  next steps in one pass and surface only when feedback is needed
  or end of a logical chunk is reached.

FIRST RESPONSE IN THE NEW CHAT SHOULD:

1. Confirm you've read the cited files (or report which are
   missing).
2. Surface 1-3 PRE-DESIGN pushbacks about Phase 13 scope based on
   PHASE_MAP §13 + Phase 12 carry-forward (especially the
   MetagraphSchema scanner question — does Phase 13 bump a
   MetagraphSchema, triggering Phase 11 PB-7 C carry-forward?
   And does the alignment role-graph schema need a per-edge
   alignment IRI builder, surfacing Phase 12 PB-4 carry-forward?).
3. Ask the user the single highest-value missing-constraint
   question needed to start the design analysis.

DO NOT START WRITING CODE in the first response. Design analysis
first, sign-off, then implementation step list, then code.

Branch off `phase-12-confirmed` tag (the squash-merge commit on
main). Per Phase 11 PB-18 ordering: bundle phase-bump + cascade
patches in ONE commit late in the impl plan (9 sites now per the
Phase 12 cascade; same 9 carry to Phase 13).
══════════════════════════════════════════════════════════════════════
```
