# Phase 15 — Handoff Prompt (written by Phase 14, 2026-05-19)

> Phase 15 branches off **main-tip** after Phase 14's PR squash-merges.
> Phase 15 ships the 4 L2 importers (DOLCE → ontology, OEWN → lexicon,
> FrameNet → concepts, Alignments → alignment:<a>:<b>) that populate
> the Global metagraph Phase 14's `KL.bootstrap()` mints empty.
>
> Paste the **PROMPT BODY** below into a fresh Claude chat (MindsOS
> project) when ready to run Phase 15. The prompt is a **navigation
> guide** — every fact about scope, locks, prior phases, ADRs, and
> modules lives in files; the prompt routes you there.

---

## PROMPT BODY (copy from here)

```
══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 15 (L2 Importers — DOLCE, OEWN, FrameNet,
Alignments)
══════════════════════════════════════════════════════════════════════

Project: MindsOS — folder `halvim_mindsos/` under `Layered
Intelligence`. **Branch off `main` tip** after running
`git fetch origin && git checkout origin/main`. Phase 14's squash-
merge commit (4-package version bumped to `0.0.0+phase14`; image
tags `mindsos:phase14-{prod,test}`) sits at tip.

ROLE: Critical design reviewer + implementer for the L2 importers.
Follow project-level CLAUDE.md skeptical-default + terse + pros/cons
+ alternatives behavior. Phase 15 ships NEW CODE — the shipping
feedback rules apply (host pip refresh, dimension-table cross-check,
state-file key canonicalisation, phase-baseline literal audit,
batch-fix-don't-iterate, tag-AFTER-squash-merge).

BEFORE DOING ANYTHING — REQUIRED READING (in order; READ THE FILES,
do not guess from training):

1. `MEMORY.md` (auto-loaded). Every `feedback_*` entry is a hard rule.
   Particularly load-bearing for Phase 15:
   * `feedback_batch_fix_dont_iterate.md`
   * `feedback_phase_baseline_literal_audit.md` (now bumps `+phase14`
     → `+phase15`; the literal-audit class is in its 5th phase of
     consecutive bumps).
   * `feedback_dimension_table_cross_check.md` (Phase 15 ships 4
     importer fixture counts; cross-check ALL count tables against
     `len(builder())` output during Step-0 probe).
   * `feedback_state_file_key_canonicalization.md`
   * `feedback_state_file_serializer_deserializer_symmetry.md`
   * `feedback_sandbox_vs_mac_git_separation.md`
   * `feedback_release_tag_after_squash_merge_only.md`

2. `project_mindsos_phase_14_implemented.md` (memory — written
   post-Phase 14 ship) — what Phase 14 shipped (`KnowledgeLayer` +
   `bootstrap` + `MetagraphView` + install/extract). Phase 15 is the
   FIRST consumer of `KL.bootstrap()` + `KL.global_metagraph()` +
   `ensure_global_role_graph(mg, role)` (for alignment-pair graphs).

3. `halvim_mindsos/confirmation_docs/PHASE_14_CONFIRMED.md`
   tester_notes — load-bearing field per PHASE_MAP §0. Includes the
   smoke ledger + any B-14-T* hotfix classes.

4. `halvim_mindsos/confirmation_docs/PHASE_MAP.md` — §0 (read rule)
   + §1 (settled cross-cutting decisions) + §Phase 15 row + §Phase 14
   row + §Phase 13 row (the two-prior context per §0).

5. `halvim_mindsos/docs/concepts/global-local.md` — Phase 14's
   Bootstrap-stage owner page. Phase 15's Shipping stage is owned by
   `docs/concepts/admin-global-shipping.md` (Phase 14a). Phase 15
   flips the lifecycle-table row Status `planned → shipped` for
   Phase 15 in a one-cell edit.

6. ADRs Phase 15 honours / flips:
   * [ADR-0010](../decisions/adr/0010-layer-isolation.md) — L2 still
     no `mindsos_server` imports. Phase 14's isolation test extends
     to Phase 15 surfaces.
   * [ADR-0045](../decisions/adr/0045-per-role-iri-builders.md) —
     importers mint IRIs via Phase 12's builders verbatim.
   * [ADR-0044](../decisions/adr/0044-memories-move-to-local-per-user.md)
     — importers write Global only. Memories is Local; importers
     never write it.
   * [ADR-0150](../decisions/adr/0150-l2-knowledge-lifecycle.md) +
     §amendment-1 (Phase 14) — alignment is Global-only at v1; the
     Alignments importer writes into Global alignment pair-graphs.
   * **ADR-0134 (Proposed → Accepted flip).** Phase 11/12/13/14
     carry-forward. Phase 15 is the importer phase that drives the
     schema-migration scanner from theory to practice; flip ADR-0134
     to Accepted as part of the PR. Draft `docs/dev/migration-
     playbook.md` full content (Phase 13 carry-forward). Add ADR-0134
     §amendment-3 (Phase 13 carry-forward) documenting the importer
     interaction.
   * [ADR-0140](../decisions/adr/0140-server-owns-admin-operations.md)
     (Proposed) — importers are admin-operations; Phase 37 relocates
     to `mindsos_server/`. Phase 15 ships them in `mindsos_knowledge/`
     and Phase 37 moves; do NOT pre-relocate.

PHASE 15 SCOPE (per PHASE_MAP §Phase 15 row + Phase 14 carry-forward):

* 4 importer modules in `mindsos_knowledge/importers/`:
  * `dolce.py` — DOLCE OWL → `ontology` role-graph in Global.
  * `oewn.py` — Open English WordNet → `lexicon` role-graph in Global.
  * `framenet.py` — FrameNet JSON → `concepts` role-graph in Global.
  * `alignments.py` — Per-pair alignment → `alignment:<a>:<b>`
    role-graphs in Global. First consumer of Phase 14's deferred
    per-edge alignment-anchor IRI builder (Phase 12 PB-4 / Phase 13
    PB-5 / Phase 14 PB-1 carry — 3rd hop). Lock the IRI form here
    (wrapper-IRI vs entity-IRI-reuse) per Phase 13's design log.
* Per-edge alignment-anchor IRI builder in `mindsos_knowledge/
  identifiers.py` (Phase 12 PB-4 / Phase 14 PB-1 carry).
* MetagraphSchema scanner consumer — Phase 15 is the first phase
  that writes content the scanner can check. Phase 11's scanner
  module (Phase 14 PB-1 carry — 4th hop) wires into the importer
  flow. Decide: per-importer post-write scan, or batched post-all-
  importers scan.
* ADR-0134 Proposed → Accepted flip (Phase 11/12/13/14 carry).
* `docs/dev/migration-playbook.md` full content (Phase 13 carry).
* ADR-0134 §amendment-3 (Phase 13 carry).
* `mindsos knowledge import {dolce,oewn,framenet,alignments}` CLI
  verbs (Phase 13 ships `knowledge schema {show,validate}`; Phase 15
  extends `knowledge` group with `import` sub-subgroup).
* Phase 15 lifecycle row flip on `knowledge-lifecycle.md` (Status
  `planned → shipped`; `last_confirmed_phase: 14 → 15`).
* `docs/knowledge-sources/*.md` — per-importer reference pages.

NOT IN SCOPE (per Phase 14a design locks + Phase 14 PB-1 / PB-14):

* Validators surface (Phase 36 owns per ADR-0139).
* Promotion machinery (Phase 16 owns).
* Importer relocation to `mindsos_server/` (Phase 37 per ADR-0140).
* CLI state-file access for the KL surface (deferred to Phase 26).
* L3 write capacities (Phase 33-35).
* `KLWriteHandle` (ADR-0143 Proposed; Phase 33-35).

PROCESS DISCIPLINE:

* **Tag on confirm:** `phase-15-confirmed`. Branch point is **main-tip
  after Phase 14 merged**. Verify with
  `git log --oneline origin/main | head -5` before branching.
* Pre-build the test image; timeout 1800s (per
  `feedback_confirm_phase_timeout.md`).
* `notes-phase-15.md` at REPO ROOT per
  `feedback_confirm_phase_file_paths.md`.
* Cumulative literal audit per
  `feedback_phase_baseline_literal_audit.md` — grep ALL tests for
  `+phase14` / `phase 14` / `Phase 14` literals before patching.
* Tag AFTER squash-merge per
  `feedback_release_tag_after_squash_merge_only.md`.
* Phase 15 carries no version-bump exemption — bump to `+phase15`
  across all 4 packages (`mindsos_core`, `mindsos_cli`,
  `mindsos_instances`, `mindsos_knowledge`); `manifest.toml
  [mindsos] phase = "15"`; image tags `mindsos:phase15-{prod,test}`.
* `mindsos_knowledge/importers/` is a NEW sub-package (analogous to
  `mindsos_knowledge/schemas/` in Phase 13). Subpackage of an
  existing top-level — no new Dockerfile COPY directive needed; no
  host pip refresh needed (the 7th-site checklist per
  `feedback_host_pip_refresh_on_new_package.md` applies only to
  brand-new top-level packages).
* Per `feedback_batch_fix_dont_iterate.md`: enumerate ALL failures
  via static grep BEFORE patching; one commit, one push, one rebuild.

CARRY-FORWARD ITEMS (Phase 14 → Phase 15):

* **Per-edge alignment-anchor IRI builder** — Phase 12 PB-4 / Phase
  13 PB-5 / Phase 14 PB-1 re-carry (3rd hop). Phase 15's Alignments
  importer is the first concrete consumer; lock the IRI form
  (wrapper vs entity-IRI-reuse) here.
* **MetagraphSchema scanner** — Phase 11 PB-7 C / Phase 12 PB-5 /
  Phase 13 PB-2 / Phase 14 PB-1 re-carry (4th hop). Phase 15's
  importers are the first phase that writes content for the scanner
  to verify.
* **ADR-0134 Proposed → Accepted** — Phase 11 PB-7 / Phase 12 PB-5 /
  Phase 13/14 carry. Phase 15 drives the flip + §amendment-3.
* **`docs/dev/migration-playbook.md` full content** — Phase 13/14
  carry; Phase 15 writes.

FIRST RESPONSE IN THE NEW CHAT SHOULD:

1. Confirm cited files read; report missing.
2. Verify `git log --oneline origin/main | head -3` shows Phase 14's
   squash-merge SHA at tip.
3. Surface 1-3 pre-design pushbacks. Likely candidates:
   * Importer pinning — which DOLCE/OEWN/FrameNet/Alignments dataset
     versions (the v3 design doc §4 + §8.4 has the v3 picks; review
     for staleness).
   * Per-edge alignment-anchor IRI form: `(role-a, role-b, anchor-id)`
     ternary vs `(role-pair, anchor-id)` binary vs entity-IRI-reuse.
   * MetagraphSchema scanner wiring: per-importer post-write scan vs
     batched post-all-importers scan.
   * Importer file-I/O contract: ADR-0043 (KL is in-memory) + Phase
     14's design says KL touches no I/O. Importer modules — where do
     they read the dataset files? Phase 15 needs to decide whether
     importers are pure "given a parsed dict, write to metagraph"
     functions (caller does I/O) or full file-I/O modules. Phase 37
     relocation to server makes this question matter.
4. Ask the single highest-value missing-constraint question.

DO NOT start writing code in the first response. Design first,
sign-off, then implement.

When complete, Phase 15 squash-merges to main; `phase-15-confirmed`
tag pushed AFTER merge per
`feedback_release_tag_after_squash_merge_only.md`. Downstream Phase
16 (Promotion machinery) opens from
`confirmation_docs/PHASE_16_NEXT_CHAT_PROMPT.md` (Phase 15 writes it).
══════════════════════════════════════════════════════════════════════
```
