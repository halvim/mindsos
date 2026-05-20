# Phase 15b — Handoff Prompt (written by Phase 15a, 2026-05-19)

> Phase 15b branches off **main-tip** after Phase 15a's PR squash-merges.
> Phase 15b ships the AlignmentsImporter + MetagraphSchema scanner L1
> module + `mindsos admin scan-schema` CLI verb + migration-playbook
> docs + ADR-0134 §amendment-3. All 4 are Phase 15a carry-forwards
> (15a/15b scope-split per Phase 15a PB-D1 Round 1).
>
> Paste the **PROMPT BODY** below into a fresh Claude chat (MindsOS
> project) when ready to run Phase 15b. The prompt is a **navigation
> guide** — every fact about scope, locks, prior phases, ADRs, and
> modules lives in files; the prompt routes you there.

---

## PROMPT BODY (copy from here)

```
══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 15b (L2 admin AlignmentsImporter + L1
MetagraphSchema scanner + scanner CLI verb)
══════════════════════════════════════════════════════════════════════

Project: MindsOS — folder `halvim_mindsos/` under `Layered Intelligence`.
**Branch off `main` tip** after running
`git fetch origin && git checkout origin/main`. Phase 15a's squash-merge
commit (5-package version bumped to `0.0.0+phase15a`; image tags
`mindsos:phase15a-{prod,test}`; NEW top-level `mindsos_admin/` package)
sits at tip.

ROLE: Critical design reviewer + implementer for the L2 admin
AlignmentsImporter + L1 scanner module. Follow project-level CLAUDE.md
skeptical-default + terse + pros/cons + alternatives behavior. Phase
15b ships NEW CODE — the shipping feedback rules apply (host pip
refresh NOT needed — `mindsos_admin/` already a top-level package;
dimension-table cross-check; state-file key canonicalisation;
phase-baseline literal audit `+phase15a → +phase15b`; batch-fix-don't-
iterate; tag-AFTER-squash-merge).

BEFORE DOING ANYTHING — REQUIRED READING (in order; READ THE FILES,
do not guess from training):

1. `MEMORY.md` (auto-loaded). Every `feedback_*` entry is a hard rule.
   Particularly load-bearing for Phase 15b:
   * `feedback_lock_sh_reads_requirements_in.md` (Phase 15a B-15a-T3 calibration; no new runtime deps for 15b unless AlignmentsImporter parser pulls one)
   * `feedback_write_tool_no_exec_bit.md` (Phase 15a B-15a-T2; chmod+x for any new shell script)
   * `feedback_confirm_phase_init_notes_overwrites.md` (workflow trap)
   * `feedback_tag_regex_audit.md` (B-15a-T1 surfaced — letter sub-phase grammar still ratcheting; check Phase 08/09/etc. for any pure-`\d{2}` literal)
   * `feedback_batch_fix_dont_iterate.md`
   * `feedback_phase_baseline_literal_audit.md` (bumps `+phase15a → +phase15b`; 6th consecutive phase bump)
   * `feedback_dimension_table_cross_check.md`
   * `feedback_sandbox_vs_mac_git_separation.md`
   * `feedback_release_tag_after_squash_merge_only.md`

2. `project_mindsos_phase_15a_implemented.md` (memory) — what Phase
   15a shipped (`mindsos_admin/` permanent home; `bootstrap_global`
   helper; `ImporterProtocol` self-describe via `target_roles`;
   DolceImporter/OewnImporter/FrameNetImporter; ADR-0042 §amendment-2
   + ADR-0140 §amendment-1; 23 PBs across 5 rounds; 3 hotfixes).
   Phase 15b is the FIRST consumer of `mindsos_admin/` as an
   established package — no 7-site checklist needed (subpackage of
   existing top-level).

3. `halvim_mindsos/confirmation_docs/PHASE_15a_CONFIRMED.md`
   tester_notes — load-bearing field per PHASE_MAP §0. Includes the
   smoke ledger + B-15a-T1/T2/T3 hotfix classes.

4. `halvim_mindsos/confirmation_docs/PHASE_15a_DESIGN_LOG.md` — full
   23-PB ledger across 5 rounds. §8 (Carry-forward) is THE spec
   source for Phase 15b's scope.

5. `halvim_mindsos/confirmation_docs/PHASE_MAP.md` — §0 (read rule)
   + §1 (settled cross-cutting decisions) + §Phase 15b row + §Phase
   15a row + §Phase 14 row (the two-prior context per §0).

6. `halvim_mindsos/docs/concepts/admin-global-shipping.md` (Phase
   15a's full rewrite owns this page; Phase 15b amends to flip the
   Alignments row to shipped). `last_confirmed_phase: 15a → 15b`.

7. ADRs Phase 15b honours / flips:
   * [ADR-0010](../decisions/adr/0010-layer-isolation.md) — L2/admin
     still no `mindsos_server` imports.
   * [ADR-0043](../decisions/adr/0043-kl-in-memory-only-server-owns-io.md)
     (Accepted) — `mindsos_knowledge/` no file I/O. Phase 15b's
     scanner module lives at `mindsos_core/schema/migration.py`
     (L1, not L2) per ADR-0134 §Implementation references; no
     ADR-0043 interaction.
   * [ADR-0045](../decisions/adr/0045-per-role-iri-builders.md) —
     AlignmentsImporter uses `alignment_role(role_a, role_b)`
     graph-name helper from `mindsos_knowledge.identifiers`. NO new
     per-edge alignment-anchor IRI builder at Phase 15b (deferred
     4th-hop to Phase 33-35 per Phase 15a PB-C1 — Phase 15b writes
     alignment edges via L1 with whatever ID L1 mints).
   * [ADR-0140](../decisions/adr/0140-server-owns-admin-operations.md)
     + §amendment-1 (Phase 15a) — admin permanent home. AlignmentsImporter
     ships at `mindsos_admin/importers/alignments.py`.
   * [ADR-0150](../decisions/adr/0150-l2-knowledge-lifecycle.md) +
     §amendment-1 (Phase 14) — alignment Global-only at v1.
     AlignmentsImporter writes into `alignment:<a>:<b>` pair-graphs
     in Global only.
   * **ADR-0134 (Proposed)** — schema migration scanner. Phase 15a
     PB-2 declined to flip Accepted. Phase 15b SHIPS the scanner
     module + CLI verb but STILL doesn't flip Accepted (Phase 15b's
     AlignmentsImporter isn't a real schema bump either; fresh
     write doesn't exercise migration semantics). The flip waits
     for whichever later phase first does a real role-graph schema
     v2 (likely Phase 17 versioning or a future re-import phase).
     Phase 15b DOES land §amendment-3 documenting the
     importer-flow interaction (Phase 13/14/15a carry).

PHASE 15b SCOPE (per Phase 15a DESIGN_LOG §8 + PHASE_MAP §Phase 15b row):

* **AlignmentsImporter** at `mindsos_admin/importers/alignments.py`:
  * Parametric `target_roles` set in `__init__` per Phase 15a PB-22
    (tuple of `alignment:<a>:<b>` strings derived from constructor
    `pairs=[(role_a, role_b), ...]`).
  * Writes alignment edges via L1 (intra-graph for now); NO per-edge
    anchor IRI per Phase 15a PB-C1 (4th-hop defer).
  * 3 ordered pairs by default per Phase 15a PB-23:
    `(ontology, lexicon)`, `(lexicon, concepts)`, `(ontology, concepts)`.
    Fallback to single pair if alignment dataset sourcing fails.
  * Source-format decision (Phase 15b owns): CSV `(source_iri,
    target_iri, ref_type[, confidence])` vs JSON Lines vs other.
    Surface as PB.

* **MetagraphSchema scanner L1 module** at
  `mindsos_core/schema/migration.py` per ADR-0134 §Implementation
  references:
  * `Schema.migrate_from(old_schema, on_violation="report") ->
    list[SchemaViolation]`.
  * `SchemaViolation` dataclass (kind / type_name / node_or_edge_id /
    detail).
  * Phase 15b's first concrete consumer is the scan-schema CLI verb
    (NOT an importer write-hook — Phase 15a PB-5 / F1 lock: scanner
    is admin-CLI-runnable, not write-time).

* **`mindsos_core/exceptions.py` additions** per ADR-0134:
  * `SchemaMigrationError`
  * `UnknownEdgeTypeError`

* **`mindsos admin scan-schema [--role R] [--json]` CLI verb**:
  * Backend home: TBD at impl time — either `mindsos_admin/scan.py`
    OR direct in `mindsos_cli/commands/admin.py`. Phase 15b decides.
  * Reads from the populated Global Metagraph (state-file or
    via session — Phase 26 owns real-user state-file access per
    Phase 14a round-3 lock).

* **`docs/dev/migration-playbook.md` full content** (Phase 13/14/15a
  carry) — explains how higher-layer consumers use scanner output
  (e.g., importer authoring against a schema bump).

* **ADR-0134 §amendment-3** (Phase 13/14/15a carry) — documents the
  importer-flow interaction; flip stays Proposed.

* **`docs/knowledge-sources/alignments.md`** NEW — per-pair sourcing,
  expected stats, import command.

* **PHASE_MAP §Phase 15b row** Status `planned → shipped`;
  `knowledge-lifecycle.md` Phase 15b row flip.

NOT IN SCOPE (per Phase 15a carry-forwards + ongoing defers):

* Per-edge alignment-anchor IRI builder (Phase 15a PB-C1 — 4th-hop
  defer to Phase 33-35; first read consumer materialises there).
* ADR-0134 Proposed → Accepted flip (Phase 15a PB-B1; wait for
  real schema bump).
* Full mid-process importer idempotency (Phase 15a B-15a-T3
  follow-up; current single-shot contract preserved unless 15b
  has consumer need).
* Validator surface (Phase 36 owns per ADR-0139).
* Promotion machinery (Phase 16 owns; pre-located at
  `mindsos_admin/promotion.py` per Phase 15a PB-3-i Round 4).
* CLI state-file access for KL surface (Phase 26).

PROCESS DISCIPLINE:

* **Tag on confirm:** `phase-15b-confirmed`. Branch point is
  **main-tip after Phase 15a merged**. Verify with
  `git log --oneline origin/main | head -5` before branching.
* **Sandbox vs Mac git** — file edits in sandbox; git ops on Mac
  per `feedback_sandbox_vs_mac_git_separation.md`.
* **Pull-rebase before every Mac commit** — Phase 15a hit "remote
  contains work that you do not have locally" twice (Linux pushed
  hotfix commits between Mac sessions). Default to
  `git pull --rebase` before each Mac-side commit step.
* Pre-build the test image; timeout 1800s.
* `notes-phase-15b.md` at REPO ROOT per
  `feedback_confirm_phase_file_paths.md`.
* `mindsos confirm-phase --init-notes 15b` ONLY ONCE (initializes
  blank template); then `mindsos confirm-phase --phase 15b
  --notes-file notes-phase-15b.md` for confirmation-doc generation
  per `feedback_confirm_phase_init_notes_overwrites.md`.
* Cumulative literal audit per
  `feedback_phase_baseline_literal_audit.md` — grep ALL tests for
  `+phase15a` / `phase 15a` / `Phase 15a` literals before patching.
  Special site: `mindsos_admin/bootstrap.py:_GLOBAL_ROLE_ORDER`
  parity assert against `mindsos_knowledge.bootstrap._GLOBAL_NAMED_ROLES`
  — doesn't change in 15b but worth noting.
* Tag AFTER squash-merge per
  `feedback_release_tag_after_squash_merge_only.md`.
* Phase 15b carries no version-bump exemption — bump to `+phase15b`
  across **all 5 packages** (`mindsos_core` / `mindsos_cli` /
  `mindsos_instances` / `mindsos_knowledge` / `mindsos_admin`);
  `manifest.toml [mindsos] phase = "15b"`; image tags
  `mindsos:phase15b-{prod,test}`.
* **NO 7-site new-top-level-package checklist** — `mindsos_admin/`
  already top-level (Phase 15a shipped). `mindsos_admin/importers/`
  is an existing sub-package; just append `alignments.py`.
* **Letter sub-phase regex** — Phase 15a B-15a-T1 patched Phase 08's
  pure-`\d{2}` literal. Audit Phase 09+ for any other lurking
  `phase.isdigit()` / `len(phase) == 2` literals via grep before
  hitting the cumulative sweep.
* **Lock step** — if AlignmentsImporter pulls a new runtime dep
  (unlikely; reuses rdflib/lxml/stdlib), update BOTH `pyproject.toml`
  AND `requirements.in` per
  `feedback_lock_sh_reads_requirements_in.md`.
* Per `feedback_batch_fix_dont_iterate.md`: enumerate ALL failures
  via static grep BEFORE patching.

CARRY-FORWARD ITEMS (Phase 15a → Phase 15b):

* **AlignmentsImporter** — first concrete consumer.
* **MetagraphSchema scanner L1 module** + `mindsos admin scan-schema`
  CLI verb (Phase 15a PB-5 / PB-9 lock — admin CLI verb, not
  write-hook).
* **`docs/dev/migration-playbook.md` full content** (Phase 13/14/15a
  re-carry).
* **ADR-0134 §amendment-3** (Phase 13/14/15a re-carry) — §closing
  flip criterion NOT met at Phase 15b either; defer flip again.
* **Full importer idempotency** (Phase 15a B-15a-T3 follow-up) —
  Phase 15b should decide: fix in 15b alongside Alignments
  consideration, or carry forward to whichever phase first needs
  mid-process re-import (probably none until release-bump tooling).
* **Per-edge alignment-anchor IRI builder** — 5th-hop carry to
  Phase 33-35 per Phase 15a PB-C1.

FIRST RESPONSE IN THE NEW CHAT SHOULD:

1. Confirm cited files read; report missing.
2. Verify `git log --oneline origin/main | head -3` shows Phase 15a's
   squash-merge SHA at tip.
3. Surface 1-3 pre-design pushbacks. Likely candidates:
   * AlignmentsImporter input format (CSV vs JSON Lines vs other).
   * Alignment dataset sourcing per pair — FN-WN is well-studied;
     DOLCE-OEWN and DOLCE-FN less so. Berkeley FrameNet ships
     WN-mappings; what about ontology-pairs? Worth probing whether
     v3 design doc §4 mentions alignment data sources.
   * Scanner CLI backend home: `mindsos_admin/scan.py` vs
     `mindsos_cli/commands/admin.py`.
   * Layer-mixing per Phase 15a PB-3a — 15b row in PHASE_MAP
     explicitly notes "Layer: L1+L2(admin)+CLI". Worth confirming.
   * B-15a-T3 follow-up: ship full importer idempotency in 15b or
     carry forward?
4. Ask the single highest-value missing-constraint question.

DO NOT start writing code in the first response. Design first,
sign-off, then implement.

When complete, Phase 15b squash-merges to main; `phase-15b-confirmed`
tag pushed AFTER merge per
`feedback_release_tag_after_squash_merge_only.md`. Downstream Phase
16 (Promotion machinery at `mindsos_admin/promotion.py` per Phase
15a §amendment-1) opens from
`confirmation_docs/PHASE_16_NEXT_CHAT_PROMPT.md` (Phase 15b writes it).
══════════════════════════════════════════════════════════════════════
```
