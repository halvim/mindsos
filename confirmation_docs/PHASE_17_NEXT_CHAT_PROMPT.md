══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 17 (L2 versioning + breadcrumbs)
══════════════════════════════════════════════════════════════════════

Project: MindsOS — folder `halvim_mindsos/` under
`/Layered Intelligence/`. Branch off `origin/main` tip. Phase 16's
squash-merge SHA `58e76a5` is at `origin/main` HEAD; Phase 15b's
`ec94565` immediately under it. Verify:

    git fetch origin && git log --oneline origin/main | head -3

Line 1 must read `58e76a5 Phase 16 — L2 admin similarity surface
(read-only) (#25)`. If not, STOP and resolve before branching.

ROLE: Critical design reviewer + implementer. Follow project-level
CLAUDE.md skeptical-default + terse + pros/cons + alternatives
behavior. Phase 17 scope is locked at PHASE_MAP §Phase 17 row — read
that row, do not re-derive scope from training. Mirror Phase 16's
discipline: 5-round design pushback ledger before any code lands.

══════════════════════════════════════════════════════════════════════
REQUIRED READING — in this order; READ THE FILES, do not guess
══════════════════════════════════════════════════════════════════════

The handoff principle (per PHASE_MAP §0 load-bearing read rule): read
your own row + the two prior phase rows + the most recent
confirmation doc + only the docs paths your row names. This prompt
does NOT duplicate file content — it tells you which files to open.

1. `MEMORY.md` (auto-loaded at chat start). Every `feedback_*` entry
   is a hard rule. Pay special attention to:
   * `feedback_pre_impl_probe_check_existing_modules.md` — Phase
     14 PB-15 deferred `MetagraphView.step(version=)` to Phase 17;
     Phase 14 PB-13 deferred KL CLI verbs to Phase 17. Grep for
     these BEFORE agreeing scope as net-new.
   * `feedback_phase_baseline_literal_audit.md` — Phase 17 is the
     first version bump since Phase 16 (`+phase16 → +phase17`).
   * `feedback_test_image_rebuild_after_source_change.md` — NEW
     from Phase 16; rebuild test image after every source edit.
   * `feedback_stale_local_tag_silent_overwrite_failure.md` — NEW
     from Phase 16; check `git rev-parse phase-17-confirmed` before
     re-tagging if a prior attempt left a stale local tag.
   * `feedback_release_tag_after_squash_merge_only.md` — strict
     ordering.
   * `feedback_batch_fix_dont_iterate.md`,
     `feedback_sandbox_vs_mac_git_separation.md`.

2. Phase-recap memory entries — the durable handoff context:
   * `project_mindsos_phase_15a_implemented.md` — Phase 15a admin
     package permanence + 3 importers.
   * `project_mindsos_phase_15b_shipped.md` — Phase 15b design-only
     reframe pattern (Phase 16 mirrored it; Phase 17 may need it
     too if pre-impl probe surfaces already-shipped surface).
   * `project_mindsos_phase_16_implemented.md` — Phase 16's
     read-only similarity surface; PB-1c reframe; PHASE_MAP §16
     rewrite + §23 narrow + §24 absorb; ADR-0144 §amendment-1
     partial-flip mechanism; PHASE_MAP §23/§24 deps cascade.

3. `halvim_mindsos/confirmation_docs/PHASE_MAP.md`:
   * §0 (load-bearing read rule) + §1 (settled cross-cutting
     decisions).
   * §Phase 17 row — primary scope source-of-truth.
   * §Phase 15a + §Phase 16 rows — two prior phases per §0.
   * §Phase 24 row — confirm Phase 17 does NOT touch the deferred
     promotion entry-point.

4. `halvim_mindsos/confirmation_docs/PHASE_16_CONFIRMED.md` — most
   recent confirmation doc (per §0 chain-read rule). Skim only the
   tester_notes block to understand what shipped at 16.

5. `halvim_mindsos/confirmation_docs/PHASE_16_DESIGN_LOG.md` (if
   relevant to Phase 17 deps):
   * §3 Cross-chat dependencies "Forward (Phase 16 → later phases)"
     subsection — Phase 17 inherits NO carry-forwards from Phase 16
     per that section. Verify against current code.

6. ADRs (in `/Layered Intelligence/docs/decisions/adr/` per Model C):
   * ADR-0010 (layer isolation) — Phase 17 stays L2; no
     `mindsos_server` imports.
   * ADR-0017 — schema strictness opt-in.
   * ADR-0042 §amendment-1 + §amendment-2 — first-install sequences
     unchanged at Phase 17.
   * ADR-0044 — memories Local-per-user (relevant if
     version-routing reads Local).
   * ADR-0051 — PROMOTED ref_type breadcrumb (Phase 17 surfaces in
     `MetagraphView`).
   * ADR-0138 (Proposed) — KL drops write API; honored by absence
     at Phase 17 (no write surface added).
   * ADR-0149 — strict=False L2 default + 2-week tightening rule.
   * Phase 17 may need to NEW-author 0 or 1 ADR if a versioning
     decision lacks a prior ADR (e.g., version selection policy);
     surface during design.

══════════════════════════════════════════════════════════════════════
PRE-IMPL PROBE (run BEFORE any design pushbacks; per the memory rule)
══════════════════════════════════════════════════════════════════════

    cd halvim_mindsos
    grep -rnE "active_version|with_version|active-version|breadcrumb" \
        mindsos_knowledge/ mindsos_core/ mindsos_cli/ 2>/dev/null
    grep -nE "def step" mindsos_knowledge/metagraph_view.py 2>/dev/null
    grep -rnE "version_for_role|role_versions|version=" \
        mindsos_knowledge/ 2>/dev/null | head -20

Report findings. If anything beyond the Phase 14 PB-15 carry-forward
(`step(version=)` kwarg) already exists in code, surface as a
reframe pushback BEFORE agreeing scope as net-new. Phase 15b reframed
to design-only exactly because the pre-impl probe found Phase 11 had
already shipped the scanner; Phase 16 reframed because ADR
cross-reading exposed a scope contradiction. Phase 17 should run the
same gate.

══════════════════════════════════════════════════════════════════════
LIKELY PUSHBACK SURFACES (probe before locking scope; not exhaustive)
══════════════════════════════════════════════════════════════════════

1. **Version representation source-of-truth.** IRI tail (Phase 12
   builders embed version like `dolce:dolce-dul-4.1:Class:Foo`) vs
   per-graph `version` property vs per-metagraph version map.
2. **Active-version selection policy.** First by import order? Latest
   by semver? Admin-configurable per role? Implicit per role-graph?
   Needs a decision; possibly a NEW ADR.
3. **`step(version=)` semantics.** `version=None` means "use active"
   or "use any"? Cross-metagraph step behaviour under
   version-routing?
4. **PROMOTED breadcrumb surfacing.** Hide PROMOTED nodes from views
   by default? Surface with a tag in the read shape? Filter via
   kwarg?
5. **Multi-version coexistence.** Can Global hold `ontology@4.1` AND
   `ontology@4.2` simultaneously? If yes, version-active routing is
   load-bearing. If no, Phase 17 is mostly metadata + breadcrumb.
6. **CLI surface.** `mindsos knowledge versions [--role R]` +
   `mindsos knowledge active-version --role R` (Phase 14 PB-13
   carry-forward); subgroup naming + flag shape.

══════════════════════════════════════════════════════════════════════
PROCESS DISCIPLINE — see MEMORY.md feedback entries (do not restate)
══════════════════════════════════════════════════════════════════════

Branch: `phase-17` off `origin/main` tip (verify `58e76a5` first).
Notes file: `notes-phase-17.md` at repo root.
`mindsos confirm-phase --init-notes 17` runs ONCE (overwrites; see
`feedback_confirm_phase_init_notes_overwrites.md`).
Pre-build test image (`docker compose --profile test build
mindsos-test`) before AND after every hotfix.
Version bump `+phase16 → +phase17` across 5 packages; manifest
`phase = "17"`; image tags `mindsos:phase17-{prod,test}`.
No 7-site new-top-level-package checklist (likely extends existing
`mindsos_knowledge/` package only; subpackage additions get sentinel
entries but no Dockerfile COPY changes).
Tag `phase-17-confirmed` AFTER squash-merge only; verify
`git rev-parse phase-17-confirmed` returns "unknown" BEFORE creating
to avoid the Phase 16 stale-tag false-start.

══════════════════════════════════════════════════════════════════════
FIRST RESPONSE IN THE NEW CHAT SHOULD
══════════════════════════════════════════════════════════════════════

1. Confirm cited files read; report any missing.
2. Verify `git log --oneline origin/main | head -3` shows `58e76a5
   Phase 16 ...` at tip.
3. Run the pre-impl probe above; report findings.
4. Surface 1–3 pre-design pushbacks from §Likely pushback surfaces
   (or new ones surfaced by the probe).
5. Ask the single highest-value missing-constraint question.

DO NOT write code in the first response. Phase 16's 5-round design
pushback ledger is the shape this project favors — sign off the
architecture first, then implement. The reframe-from-handoff
discipline (Phase 15b: scope already shipped; Phase 16: scope
contradicts ADRs) should be applied to Phase 17's handoff scope too
if the probe surfaces evidence.

══════════════════════════════════════════════════════════════════════
HANDOFF EXIT CRITERIA
══════════════════════════════════════════════════════════════════════

Phase 17 squash-merges to main; `phase-17-confirmed` tag pushed AFTER
merge per `feedback_release_tag_after_squash_merge_only.md`;
`release.yml` runs green; GitHub Release created. Phase 17 writes
`confirmation_docs/PHASE_18_NEXT_CHAT_PROMPT.md` as exit artifact
(Phase 18 = "Server: user store + auth"; deps Phase 07 only).

══════════════════════════════════════════════════════════════════════
