# Phase 14 — Handoff Prompt (written by Phase 14a, 2026-05-18)

> Phase 14 branches off **main-tip** after Phase 14a's docs PR
> squash-merges. Phase 14a was design-only (no tag, no version bump,
> no `confirm-phase` invocation) per the §1 "design-only phases are an
> exception" clause Phase 13 added. There is **no `phase-14a-confirmed`
> tag** to branch off; the Phase 14 branch point is the main-tip
> commit that contains Phase 14a's PR. After Phase 14a merges, the
> 4-package version parity stays at `0.0.0+phase13` until Phase 14
> bumps to `+phase14`.
>
> Paste the **PROMPT BODY** below into a fresh Claude chat (MindsOS
> project) when ready to run Phase 14. The prompt is a **navigation
> guide** — every fact about scope, locks, prior phases, ADRs, and
> modules lives in files; the prompt routes you there.

---

## PROMPT BODY (copy from here)

```
══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 14 (L2 KnowledgeLayer + role-graph bootstrap)
══════════════════════════════════════════════════════════════════════

Project: MindsOS — folder `halvim_mindsos/` under `Layered
Intelligence`. **Branch off `main` tip** after running
`git fetch origin && git checkout origin/main`. Phase 14a was
design-only; there is NO `phase-14a-confirmed` tag to branch off.

ROLE: Critical design reviewer + implementer for the L2 KnowledgeLayer
bootstrap. Follow project-level CLAUDE.md skeptical-default + terse +
pros/cons + alternatives behavior. Phase 14 ships NEW CODE — the
shipping-feedback rules return (host pip refresh, dimension-table
cross-check, state-file key canonicalisation, tomllib stdlib fallback,
phase-baseline literal audit, batch-fix-don't-iterate, tag-AFTER-
squash-merge, etc.).

BEFORE DOING ANYTHING — REQUIRED READING (in order; READ THE FILES,
do not guess from training):

1. `MEMORY.md` (auto-loaded). Every `feedback_*` entry is a hard rule.
   Particularly load-bearing for Phase 14:
   * `feedback_batch_fix_dont_iterate.md`
   * `feedback_phase_baseline_literal_audit.md`
   * `feedback_state_file_key_canonicalization.md` (B-11-T2 lock —
     loaders MUST use `node_id` / `edge_id` keys; never `id`)
   * `feedback_state_file_serializer_deserializer_symmetry.md`
   * `feedback_dimension_table_cross_check.md`
   * `feedback_host_pip_refresh_on_new_package.md` (if Phase 14 adds
     a new top-level pkg — it shouldn't; KL stays in
     `mindsos_knowledge`)
   * `feedback_sandbox_vs_mac_git_separation.md`
   * `feedback_release_tag_after_squash_merge_only.md`

2. `project_mindsos_phase_13_implemented.md` (memory) — what Phase 13
   shipped (8 named-role + 1 parametric schema builders + dispatch +
   `UnknownRoleError` + CLI `mindsos knowledge schema {show,
   validate}`). Phase 14 is the FIRST consumer of
   `schema_for_role()` + `_ROLE_SCHEMA_BUILDERS` dispatch dict.

3. `halvim_mindsos/confirmation_docs/PHASE_13_CONFIRMED.md`
   tester_notes — load-bearing field per PHASE_MAP §0. Includes the
   11-smoke ledger, B-13-T1 hotfix class, and Phase 14a handoff.

4. `halvim_mindsos/confirmation_docs/PHASE_MAP.md` — read §0 (read
   rule) + §1 (settled cross-cutting decisions) + §Phase 14 row +
   §Phase 13 row + §Phase 14a row (the two-prior context per §0;
   note that 14a is design-only so PHASE_14a_CONFIRMED.md does NOT
   exist — read the §Phase 14a row in PHASE_MAP itself instead).

5. `halvim_mindsos/docs/concepts/knowledge-lifecycle.md` — Phase 14a's
   synthesis page. Phase 14's row reads `Status: planned`. Phase 14
   flips it to `shipped` in its own PR (one-cell edit).

6. `halvim_mindsos/docs/concepts/user-local-authoring.md` +
   `admin-global-shipping.md` + `promotion-bridge.md` — sibling
   concept docs cited by the synthesis. Phase 14 doesn't edit them
   but its bootstrap is the precondition they all assume.

7. `/Layered Intelligence/docs/decisions/adr/0150-l2-knowledge-lifecycle.md`
   — **Accepted; closed role-set.** Phase 14's `ensure_role_graph`
   MUST reject any role outside the 9-entry table by propagating
   `UnknownRoleError` (already shipped by Phase 13 PB-11; reuse,
   don't reimplement).

8. ADRs Phase 14 must honour without writing new code that violates:
   * [ADR-0010](../decisions/adr/0010-layer-isolation.md) — L2 must
     not import `mindsos_server` (existing Phase 12 PB-18 isolation
     test extends to Phase 14 surfaces).
   * [ADR-0044](../decisions/adr/0044-memories-move-to-local-per-user.md)
     — `memories` Local-per-user; bootstrap creates it in Local, not
     Global.
   * [ADR-0061](../decisions/adr/0061-dual-metagraph-global-local.md)
     — Global + Local metagraphs (L3 has the parallel pattern; KL
     follows).
   * [ADR-0138](../decisions/adr/0138-kl-drops-write-api.md)
     (Proposed) — `MetagraphView` ships read-only. No public write
     methods. If any v3 KL surface leaked writes, removing them is
     NEW CODE per PHASE_MAP §14.
   * [ADR-0141](../decisions/adr/0141-delete-shipped-promote.md)
     (Proposed) — Phase 14 does NOT ship the shipped `promote()`; it
     stays deleted. Promotion lands in Phase 16 + 24.
   * [ADR-0149](../decisions/adr/0149-l2-role-schemas-strict-false-and-tightening-rule.md)
     — schemas stay `strict=False`; bootstrap calls
     `schema_for_role(role, strict=False)`.

PHASE 14 SCOPE (per PHASE_MAP §Phase 14 row):

* `KnowledgeLayer` class (entry point); Global + Local metagraph
  bootstrap.
* `ensure_role_graph(metagraph, role)` — idempotent; calls Phase 13's
  `schema_for_role(role)`; propagates `UnknownRoleError` on unknown
  role (Phase 13 PB-11; do not reimplement).
* `MetagraphView` — read-only; no public write methods (anticipates
  ADR-0138 by NOT shipping writes).
* Per-edge alignment-anchor IRI builder (Phase 12 PB-4 carry-forward
  + Phase 13 PB-5 re-carry — first consumer makes the call. Decide:
  (a) wrapper IRI vs (b) entity-IRI-reuse).
* MetagraphSchema scanner (Phase 11 PB-7 C carry + Phase 12 PB-5 +
  Phase 13 PB-2 re-carry — first MetagraphSchema-bump candidate;
  Phase 14 owns the call on whether to bump or stay v=3).
* `docs/concepts/global-local.md` — Phase 14's NEW deliverable (the
  knowledge-lifecycle.md synthesis forward-cites it; placement in
  mkdocs nav under `Concepts > Knowledge lifecycle` group is Phase
  14's choice).
* `docs/concepts/knowledge-lifecycle.md` mapping-table row for Phase
  14: flip Status `planned → shipped` (one-cell edit; bump the
  `last_confirmed_phase` front-matter from `14a → 14`).
* `docs/usage/knowledge/overview.md` — amend to describe KL bootstrap
  flow (currently a Phase 13 stub).

NOT IN SCOPE (per Phase 14a design locks):

* New role-graphs beyond the 9 in ADR-0150. Closure is locked.
* KL write API (ADR-0138 Proposed — KL stays write-API-free in
  Phase 14; writes land via L3 capacities in Phase 33-35).
* `KLWriteHandle` (ADR-0143 Proposed — lands when L3 write capacities
  do).
* Promotion mechanics (Phase 16 + 23 + 24).
* Importer relocation (Phase 37 per ADR-0140).
* Real-user state-file access for `mindsos knowledge schema validate`
  (deferred to Phase 26 per Phase 14a round-3 minor lock).
* Hybrid validators (ADR-0139 Proposed — Phase 36 lands).

PROCESS DISCIPLINE:

* **Tag on confirm:** `phase-14-confirmed`. Branch point is **main-tip
  after Phase 14a merged** — Phase 14a's docs are in the chain.
  Verify with `git log --oneline origin/main | head -5` before
  branching; expect to see Phase 14a's squash-merge commit at the
  tip.
* Pre-build the test image; timeout 1800s (per
  `feedback_confirm_phase_timeout.md`).
* `notes-phase-14.md` at REPO ROOT per
  `feedback_confirm_phase_file_paths.md`.
* Cumulative literal audit per
  `feedback_phase_baseline_literal_audit.md` — grep ALL tests for
  `+phase13` / `phase 13` / `Phase 13` literals before patching.
* Tag AFTER squash-merge per
  `feedback_release_tag_after_squash_merge_only.md`.
* Phase 14 carries no version-bump exemption — bump to `+phase14`
  across all 4 packages (`mindsos_core`, `mindsos_cli`,
  `mindsos_instances`, `mindsos_knowledge`); `manifest.toml [mindsos]
  phase = "14"`; image tags `mindsos:phase14-{prod,test}`. NO new
  top-level package (KL stays in `mindsos_knowledge`).
* `feedback_batch_fix_dont_iterate.md` — when confirm-phase reports
  failures, enumerate ALL via static grep BEFORE patching; one
  commit, one push, one rebuild.

CARRY-FORWARD ITEMS (re-carried per Phase 13 PB-2/5; first-consumer
phase decides):

* **MetagraphSchema scanner** — Phase 11 PB-7 C / Phase 12 PB-5 /
  Phase 13 PB-2 re-carry. Phase 14 is the first MetagraphSchema-bump
  candidate (bootstrap creates the global + local MetagraphSchemas
  per Phase 05d's `MetaEdgeType` / `MetaHyperEdgeType` vocab).
* **Per-edge alignment-anchor IRI builder** — Phase 12 PB-4 / Phase
  13 PB-5 re-carry. Phase 14 wires the alignment-graph bootstrap and
  decides the IRI form for `AlignmentAnchor` nodes.
* **ADR-0134 Proposed → Accepted** — Phase 11 PB-7 / Phase 12 PB-5 /
  Phase 13 carry — defers to Phase 15 (Importers) per Phase 13
  carry-forward.

FIRST RESPONSE IN THE NEW CHAT SHOULD:

1. Confirm cited files read; report missing.
2. Surface 1-3 pre-design pushbacks. Likely candidates:
   * Where the MetagraphSchema scanner lives (`mindsos_core` test
     infra vs prod code in `mindsos_knowledge/bootstrap.py`).
   * Per-edge alignment-anchor IRI form: `(role-a, role-b,
     anchor-id)` ternary vs `(role-pair, anchor-id)` binary.
   * `MetagraphView` read-only enforcement: type-level (subclass
     without write methods) vs runtime (assertion on `__getattr__`).
   * `ensure_role_graph` parametric on (metagraph, role) — does the
     caller decide Global vs Local via the metagraph argument, or
     does the function dispatch on a `_LOCAL_ROLES` set per
     ADR-0044?
3. Ask the single highest-value missing-constraint question.

DO NOT start writing code in the first response. Design first,
sign-off, then implement.

When complete, Phase 14 squash-merges to main; `phase-14-confirmed`
tag pushed AFTER merge per
`feedback_release_tag_after_squash_merge_only.md`. Downstream Phase
15 (Importers) opens from `confirmation_docs/PHASE_15_NEXT_CHAT_PROMPT.md`
(Phase 14 writes it).
══════════════════════════════════════════════════════════════════════
```
