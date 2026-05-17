# Phase 12 — Handoff Prompt (authored at Phase 11 close)

> Authored 2026-05-16 at close of Phase 11 ship. Paste the **PROMPT
> BODY** below into a fresh Claude chat (MindsOS project) when ready
> to design + ship Phase 12. The prompt is a **navigation guide**,
> not a content dump — every fact about scope, locks, prior phases,
> and modules lives in files; the prompt routes you there.

---

## PROMPT BODY (copy from here)

```
══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 12 design + implementation
══════════════════════════════════════════════════════════════════════

Project: MindsOS — folder `halvim_mindsos/` under `Layered Intelligence`.

ROLE: Critical design reviewer + implementer for Phase 12. Follow
the project-level CLAUDE.md skeptical-default + terse + pros/cons +
alternatives behavior.

PHASE 12 SCOPE — L2 Identifiers + role IRIs + REF_TYPES
Read the Phase 12 row in `halvim_mindsos/confirmation_docs/PHASE_MAP.md`
(grep `^### Phase 12`). PHASE_MAP is the source of truth for the
row's Features / Tests / Risks / Docs fields — do not paraphrase
here; read it.

Deps: 02 (Phase 02 — L1 Identity). Layer: L2. Net-new? No (per
PHASE_MAP). First L2 phase to ship.

BEFORE DOING ANYTHING ELSE — REQUIRED READING (in order):

1. `MEMORY.md` (auto-loaded). Every `feedback_*` entry is a hard
   rule. Particularly load-bearing for Phase 12:
   * feedback_batch_fix_dont_iterate.md
   * feedback_never_suggest_skip_tests.md
   * feedback_sandbox_vs_mac_git_separation.md
   * feedback_release_tag_after_squash_merge_only.md
   * feedback_sentinel_paths_runtime_only.md
   * feedback_phase_baseline_literal_audit.md
   * feedback_confirm_phase_timeout.md
   * feedback_confirm_phase_file_paths.md
   * feedback_confirm_phase_invocation_paths.md
   * feedback_state_file_key_canonicalization.md  ← B-11-T2
   * feedback_tomllib_stdlib_fallback.md          ← B-11-T1
   * feedback_state_file_serializer_deserializer_symmetry.md
   * feedback_state_version_audit_scope.md

2. `project_mindsos_phase_11_implemented.md` (memory) — canonical
   inventory of what Phase 11 shipped: loader policy, schema
   migration scanner, additive sibling API discipline, ADR-0134
   §amendments-1+2, B-11-T1 + B-11-T2 hotfix classes,
   carry-forward list.

3. `halvim_mindsos/confirmation_docs/PHASE_11_DESIGN_LOG.md` —
   Phase 11 pushbacks (PB-1..17 + 4 step-list PBs); Step-0 audit
   model (0-cascade prediction confirmed by impl); carry-forward
   that Phase 12 may or may not pick up.

4. `halvim_mindsos/confirmation_docs/PHASE_11_CONFIRMED.md`
   `tester_notes` — the load-bearing field per PHASE_MAP §0.
   Read for any surprises / open issues from Phase 11.

5. `halvim_mindsos/confirmation_docs/PHASE_10_CONFIRMED.md`
   `tester_notes` (two-prior context per §0 read rule).

6. `project_mindsos_l2_redesign_locks.md` (memory) — KL drops
   write API; hybrid validators; MetagraphView read-only; server
   owns importers. Phase 12 is the first L2 phase — these locks
   bound the design space.

7. `halvim_mindsos/confirmation_docs/PHASE_MAP.md` §1-§2 (project
   process + chat etiquette) if unfamiliar.

ADRs IN SCOPE — read the ones whose status you need to verify or
amend. Phase 12 likely touches:
* ADR-0045 (per-role IRI builders) — verify status; Phase 12 may
  consume.
* ADR-0067 (REF_TYPES parity test) — see PHASE_MAP §Phase 12
  Tests field.
* ADR-0134 (schema migration scanner) — STAYS Proposed per
  Phase 11 PB-5 A. Flips to Accepted when Phase 12 KL importer
  consumes scanner output for at least one role-graph schema bump.
  See ADR-0134 §closing + §amendment-3 (reserved for first KL
  consumer's structural feedback).

CARRY-FORWARD FROM PHASE 11 THAT MAY HIT PHASE 12 (read
PHASE_11_DESIGN_LOG.md §4 + project_mindsos_phase_11_implemented.md
"Carry-forward" section for full list):

* **MetagraphSchema scanner** — Phase 11 PB-7 C deferred
  MetagraphSchema migration (MetaEdge / IntergraphEdge / etc.
  type vocab) to Phase 12+. If Phase 12 bumps MetagraphSchema, the
  scanner needs to ship — surface as a pre-design pushback if
  PHASE_MAP §Phase 12 implies a MetagraphSchema bump.
* **Migration playbook** at `docs/dev/migration-playbook.md` ships
  as a stub awaiting first cross-layer consumer. If Phase 12's KL
  importer is that consumer, fill in the playbook AS PART OF
  Phase 12 ship.
* **ADR-0134 Proposed → Accepted flip** — Phase 11 designed the
  acceptance contract to trigger on first KL consumer + playbook
  fill. Likely Phase 12 territory; consider in design pushbacks.

THE EXECUTION DISCIPLINE (Phase 02-11 PRECEDENT — DO NOT INVENT
NEW PATTERNS):

* Two-machine setup: Mac for Claude sessions + git ops; Linux for
  Docker + confirm-phase. Per `user_two_machine_setup.md`. Tag
  every command with [Mac] or [Linux].
* notes-phase-12.md lives at REPO ROOT, NOT in confirmation_docs/.
* `mindsos confirm-phase --init-notes 12` writes
  ./notes-phase-12.md at repo root.
* Pre-build the test image before confirm-phase. Timeout 1800s.
  confirm-phase runs pytest inside the test image with the
  notes-phase-*.md COPYd in.
* Ship sequence is the 8-step strict ordering in
  `feedback_release_tag_after_squash_merge_only.md` — do NOT tag
  before squash-merge.

DESIGN-PHASE WORKFLOW THE USER EXPECTS (Phase 10 + Phase 11
precedent):

1. Design reanalysis with pushbacks BEFORE implementing. Number
   every pushback (PB-N), give the user pros/cons + a
   recommendation. User signs off batch-by-batch with "agreed".
2. After design sign-off, present a numbered implementation step
   list. The user signs off step-by-step. Phase 11 had 31 steps.
3. Tests written in one batch at end (Phase 10 + Phase 11 chose
   this; ~60-120 test files).
4. Phase-NN tests run FIRST in isolation, THEN cumulative `tests/`
   sweep (feedback_test_order_current_then_cumulative.md).
5. Hotfix cycles labeled B-12-T1..TN. File new feedback memories
   at chat-end for any new audit classes.

THE PHASE-BASELINE LITERAL AUDIT (NON-NEGOTIABLE STEP 0):

Before Phase 12 lands ANY code, grep ALL of tests/ for:
* state-file version literals (`_state_version == N`,
  `CURRENT_VERSION == N`)
* phase-string literals (`"11"`, `"0.0.0+phase11"`,
  `mindsos:phase11-prod/test`)
* index-count literals (`len(DEFAULT_INDEXES) == N`,
  `len(c.calls) == N`)
* summary-shape literals
* timeout literals (`_CONFIRM_PHASE_TIMEOUT_SECONDS == N`)

Predict + patch ALL in one commit per
`feedback_batch_fix_dont_iterate.md`. Phase 11 surfaced ZERO
prior-phase patches — celebrate but don't assume; re-run the
audit.

Also re-run the 6 Step-0 probes Phase 11 used (see
PHASE_11_DESIGN_LOG.md §3 for the audit table):
* state-file version stays at current
* phase-string literal sites (just the 8 bump points)
* caplog/capsys assertions over loader paths
* Dockerfile COPY discipline (tree-wide vs file-by-file)
* confirm-phase pytest summary regex (PB-33 — verify still
  matches both framed + bare forms)
* stricter-schema test load patterns

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
2. Surface 1-3 PRE-DESIGN pushbacks about Phase 12 scope based on
   PHASE_MAP §12 + Phase 11 carry-forward (especially the
   MetagraphSchema scanner question and the ADR-0134 acceptance
   flip).
3. Ask the user the single highest-value missing-constraint
   question needed to start the design analysis.

DO NOT START WRITING CODE in the first response. Design analysis
first, sign-off, then implementation step list, then code.

Branch off `phase-11-confirmed` tag (the squash-merge commit
`2eca5c5` on main). Per Phase 11 PB-18 ordering: bundle phase-bump
+ cascade patches in ONE commit late in the impl plan.

══════════════════════════════════════════════════════════════════════
```

## END PROMPT BODY (copy ends here)
