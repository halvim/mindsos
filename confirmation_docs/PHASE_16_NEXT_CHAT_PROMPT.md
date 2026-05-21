══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 16 (L2 admin promotion machinery at
`mindsos_admin/promotion.py`)
══════════════════════════════════════════════════════════════════════

Project: MindsOS — folder `halvim_mindsos/` under `Layered Intelligence`.

**Branch off `main` tip** after running
`git fetch origin && git checkout origin/main`. Phase 15b is a
**design-only phase** (PHASE_MAP §1 exception, mirroring Phase 14a) —
no `phase-15b-confirmed` tag, no version bump, no image rebuild.
Phase 15b's squash-merge SHA sits at main tip; Phase 16 branches off
that SHA per Phase 14a precedent ("downstream code phases branch off
main-tip after the design PR squash-merges, not off a tag"). Verify
with `git log --oneline origin/main | head -5` before branching.

ROLE: Critical design reviewer + implementer for Phase 16 — admin
promotion machinery. Follow project-level CLAUDE.md skeptical-default
+ terse + pros/cons + alternatives behavior. Phase 16 ships NEW CODE
(`mindsos_admin/promotion.py` is net-new per ADR-0140 §amendment-1
permanent-home decision; supersedes the original ADR-0140 §Decision
§2 routing to `mindsos_server/promotion.py`). The shipping feedback
rules apply: host pip refresh NOT needed (`mindsos_admin/` already
top-level since Phase 15a); dimension-table cross-check per
`feedback_dimension_table_cross_check.md`; phase-baseline literal
audit `+phase15a → +phase16` (NOTE: Phase 15b is design-only and did
NOT bump the version — Phase 16 is the first version bump since
Phase 15a); batch-fix-don't-iterate; tag-AFTER-squash-merge per
`feedback_release_tag_after_squash_merge_only.md`.

BEFORE DOING ANYTHING — REQUIRED READING (in order; READ THE FILES,
do not guess from training):

1. `MEMORY.md` (auto-loaded). Every `feedback_*` entry is a hard
   rule. Particularly load-bearing for Phase 16:
   * `feedback_lock_sh_reads_requirements_in.md` (no new runtime deps
     expected at Phase 16; if any, BOTH pyproject.toml + requirements.in)
   * `feedback_phase_baseline_literal_audit.md` (`+phase15a →
     +phase16`; first version bump since 15a — TWO phase delta because
     15b was design-only; audit cumulative grep across ALL `tests/`
     directories)
   * `feedback_release_tag_after_squash_merge_only.md`
   * `feedback_batch_fix_dont_iterate.md`
   * `feedback_sandbox_vs_mac_git_separation.md`
   * `feedback_release_workflow_ordering.md`

2. `project_mindsos_phase_15a_implemented.md` (memory) — what Phase
   15a shipped (the `mindsos_admin/` package + `bootstrap_global` +
   `ImporterProtocol` + 3 source importers + admin CLI).

3. `confirmation_docs/PHASE_15a_DESIGN_LOG.md` — particularly:
   * §PB-3-i Round 4 (Promotion machinery permanent home is
     `mindsos_admin/promotion.py`, NOT `mindsos_server/promotion.py`).
     This is the load-bearing forward-cite to Phase 16.
   * §PB-17 Round 4 (admin permanent home; ADR-0140 §amendment-1).
   * §PB-20 Round 4 (conservative day-one layout — Phase 16 adds
     `mindsos_admin/promotion.py` to the existing structure).
   * §8 Carry-forward list (Phase 15a → 15b → ??? for alignment;
     unchanged for Phase 16's promotion scope).

4. `confirmation_docs/PHASE_15b_DESIGN_LOG.md` — design-only phase
   ratifying ADR-0134 + correcting ADR-0150 §amendment-1 supporting
   evidence. Phase 16 is NOT a downstream code consumer of Phase 15b
   (Phase 15b's deliverables are ADR amendments + a dev doc + sentinel
   tests; Phase 16's promotion machinery doesn't touch scanner output
   per ADR-0049/0052/0053 similarity-report-based design). Phase 16
   deps stay at 14, 15a.

5. `confirmation_docs/PHASE_MAP.md` — §0 (read rule) + §1 (settled
   cross-cutting decisions) + §Phase 16 row + §Phase 15a row +
   §Phase 15b row (the two-prior-context per §0; Phase 15b's
   design-only status means it's a "row read" but not a code-dep).

6. ADRs Phase 16 honours / flips:
   * [ADR-0010](../decisions/adr/0010-layer-isolation.md) (Accepted)
     — `mindsos_admin/` no `mindsos_server/` imports; admin may
     import `mindsos_knowledge` + `mindsos_core` downward.
   * [ADR-0049](../decisions/adr/0049-similarity-report-before-promotion.md)
     (Accepted) — promote refuses without similarity report unless
     `--force`.
   * [ADR-0052](../decisions/adr/0052-report-id-deterministic-content-hash.md)
     (Accepted) — `report_id` is a content-hash of similarity inputs.
   * [ADR-0053](../decisions/adr/0053-promote-per-candidate-atomic-rollback.md)
     (Accepted) — promote-per-candidate atomicity; rollback on per-row
     failure.
   * [ADR-0055](../decisions/adr/0055-baseline-similarity-heuristic-crude.md)
     (Accepted) — baseline similarity is deterministic + crude
     (string-edit-distance or equivalent); not ML-driven at Phase 16.
   * [ADR-0056](../decisions/adr/0056-promotion-result-preserves-input-order.md)
     (Accepted) — promotion result list preserves input candidate
     order.
   * [ADR-0140](../decisions/adr/0140-server-owns-admin-operations.md)
     (Proposed) + §amendment-1 (Phase 15a) — `mindsos_admin/promotion.py`
     permanent home. ADR Status stays Proposed at Phase 16; flip
     waits for capability framework (Phase 18+).
   * **ADR-0049 + ADR-0118 (Proposed) interaction:** Phase 16 ships
     **pre-pivot** promotion machinery (single-user, no
     `pending_global` routing, no `RELEASE_SHIP_LOCK`, no release
     manifest). Phase 24 ships full ADR-0118 transactional promotion.
     Phase 16's scope per Phase 14 design log was deliberately
     narrowed to the ADR-0049/0052/0053 mechanics; the pivot
     orchestration is Phase 24.

PHASE 16 SCOPE (per PHASE_MAP §16 row + Phase 15a §PB-3-i Round 4
forward-cite):

* **`mindsos_admin/promotion.py`** NEW (~250-350 LOC estimate):
  * `propose_for_promotion(*, candidates: list[CandidateRef],
    similarity_report: SimilarityReport, force: bool = False) ->
    PromotionResult` — main entry point.
  * `list_candidates(mg: Metagraph, *, role: str) -> list[CandidateRef]`
    — discover Local-originated content awaiting promotion (per-role).
  * `compute_similarity(mg: Metagraph, candidates: list[CandidateRef])
    -> SimilarityReport` — baseline similarity heuristic per ADR-0055;
    deterministic content-hash `report_id` per ADR-0052.
  * `PromotionResult` dataclass (frozen) — per-candidate status +
    rollback record per ADR-0053; input-order-preserving per
    ADR-0056.
  * `SimilarityReport` dataclass — content-hashed `report_id`; per-pair
    similarity scores; freshness timestamp.
  * `CandidateRef` dataclass — node/edge identifier + source graph +
    target role.
* **`mindsos_admin/__init__.py` re-exports** — add
  `propose_for_promotion`, `list_candidates`, `compute_similarity`,
  `PromotionResult`, `SimilarityReport`, `CandidateRef`.
* **`mindsos admin promote` CLI verbs** (Phase 16 grows the admin CLI
  group):
  * `mindsos admin promote list --role R [--json]` — list candidates.
  * `mindsos admin promote similarity --role R [--json]` — emit
    similarity report.
  * `mindsos admin promote propose --role R --report REPORT_ID
    [--force] [--json]` — run propose_for_promotion.
* **NOT in scope (Phase 24 owns per ADR-0118):**
  * `pending_global` metagraph routing.
  * `RELEASE_SHIP_LOCK` (per ADR-0118).
  * Release manifest in `version_db/`.
  * Lazy migration semantics.
  * Per-user transactional promotion (single-user pre-pivot mechanics
    only at Phase 16).
* **NOT in scope (Phase 18+ owns per ADR-0140 capability framework):**
  * `CAN_PROPOSE_MUTATION` capability gate.
  * HTTP endpoint exposure (`mindsos_server/endpoints/admin_promote.py`
    when server ships at 18+).

NOT IN SCOPE (carry-forward unchanged from Phase 15a/15b):

* AlignmentsImporter — closure phase TBD per Phase 28 review (Phase
  15b Round 5 PB-18 lock).
* Per-edge alignment-anchor IRI builder — 5th-hop defer.
* `mindsos admin scan-schema` CLI verb — Phase 26 (Phase 14a round-3
  lock; Phase 15a PB-3 + Phase 15b Round 1 PB-3 reaffirmed).
* L3 alignment-lookup capacity — Phase 28 review will decide its
  natural home.

PROCESS DISCIPLINE:

* **Tag on confirm:** `phase-16-confirmed`. Branch point is
  **main-tip after Phase 15b's design-only PR squash-merged**.
  Verify with `git log --oneline origin/main | head -5` before
  branching. Phase 15b's squash-merge SHA is the branch-off point per
  Phase 14a precedent.
* **Sandbox vs Mac git** — file edits in sandbox; git ops on Mac.
* **Pull-rebase before every Mac commit** — Phase 15a precedent.
* **Pre-build test image** before confirm-phase per
  `feedback_confirm_phase_timeout.md`: `docker compose --profile test
  build mindsos-test`. Timeout 1800s.
* **`notes-phase-16.md` at REPO ROOT** per
  `feedback_confirm_phase_file_paths.md`.
* **`mindsos confirm-phase --init-notes 16` ONLY ONCE** per
  `feedback_confirm_phase_init_notes_overwrites.md`; subsequent runs
  use `--phase 16 --notes-file notes-phase-16.md`.
* **Cumulative literal audit** per
  `feedback_phase_baseline_literal_audit.md`: grep ALL `tests/` for
  `+phase15a` / `phase 15a` / `Phase 15a` literals — Phase 15b did
  NOT bump (design-only); Phase 16 is the first version bump since
  15a. Expect TWO-phase delta in some test literals (e.g., dimensional
  snapshots from Phase 15a expect `+phase15a`; update to `+phase16`).
* **Version bump:** `+phase16` across all 5 packages (`mindsos_core`
  / `mindsos_cli` / `mindsos_instances` / `mindsos_knowledge` /
  `mindsos_admin`); `manifest.toml [mindsos] phase = "16"`; image
  tags `mindsos:phase16-{prod,test}`.
* **NO 7-site new-top-level-package checklist** — `mindsos_admin/` is
  existing top-level (Phase 15a shipped). `mindsos_admin/promotion.py`
  is a new module in an existing package.
* **Lock step** — if new runtime deps appear (unlikely; similarity
  heuristic is stdlib-friendly per ADR-0055), BOTH `pyproject.toml`
  + `requirements.in`.
* **Tag AFTER squash-merge** per
  `feedback_release_tag_after_squash_merge_only.md`.

CARRY-FORWARD ITEMS (unchanged from Phase 15b → Phase 16):

* AlignmentsImporter — closure phase TBD per Phase 28 review.
* Per-edge alignment-anchor IRI builder — 5th-hop carry.
* Real FN-WN extraction script — alongside AlignmentsImporter.
* Importer idempotency tightening — alongside AlignmentsImporter.
* `mindsos admin scan-schema` CLI verb — Phase 26.

FIRST RESPONSE IN THE NEW CHAT SHOULD:

1. Confirm cited files read; report missing.
2. Verify `git log --oneline origin/main | head -3` shows Phase 15b's
   design-only squash-merge SHA at tip (followed by Phase 15a's
   squash-merge SHA).
3. Surface 1-3 pre-design pushbacks. Likely candidates:
   * Where exactly do `SimilarityReport` and `CandidateRef`
     dataclasses live — `mindsos_admin/promotion.py` or a new
     `mindsos_admin/types.py`? Inform by Phase 24's anticipated reuse
     (or non-reuse) of these types when full ADR-0118 transactional
     promotion ships.
   * Similarity heuristic concrete pick per ADR-0055 — string-edit-distance
     (Levenshtein/Damerau-Levenshtein) vs Jaccard on tokenised
     properties vs hash-equality only. ADR-0055 says "crude" — what
     does that mean operationally for Phase 16?
   * State-file vs in-memory candidate discovery at Phase 16 (without
     state-file access for KL surface — that's Phase 26) — does
     `list_candidates` operate on a constructed Metagraph in-memory
     only? If so, how does the CLI verb populate the Metagraph?
4. Ask the single highest-value missing-constraint question.

DO NOT start writing code in the first response. Design first,
sign-off, then implement.

When complete, Phase 16 squash-merges to main; `phase-16-confirmed`
tag pushed AFTER merge. Downstream Phase 17 (L2 active-version
queries; PROMOTED breadcrumb routing) opens from
`confirmation_docs/PHASE_17_NEXT_CHAT_PROMPT.md` (Phase 16 writes it).

**Superseded by Phase 17 retirement (2026-05-20):** Phase 17
retired without tag; "active-version queries" and "PROMOTED
breadcrumb routing" vacated per ADR-0150 §amendment-3 (one graph
per role; version is IRI-string). See `PHASE_MAP.md` §17 RETIRED
block + `PHASE_17_RETIREMENT_DESIGN_LOG.md` + memory entry
`project_mindsos_phase_17_retired.md`. Downstream is now Phase 18
(Server: user store + auth) per `PHASE_18_NEXT_CHAT_PROMPT.md`.
══════════════════════════════════════════════════════════════════════
