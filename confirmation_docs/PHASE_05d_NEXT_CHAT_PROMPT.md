# Phase 05d Implementation — Next-Chat Handoff Prompt

> Authored 2026-05-07 in the 05d row-refinement chat. Paste the **PROMPT BODY** section below into a fresh Claude chat (in the MindsOS project) when ready to implement Phase 05d.
>
> **Design philosophy of this prompt:** it is a *navigation guide*, not a content dump. Scope, locks, ADR amendments, validation orders, ADR text, state-file shapes, fingerprint canonicalization formulas, future-work entries, primitive distinctions — none of that is repeated here. The implementation chat reads the files listed below to recover that context. If you find yourself wanting a fact that isn't in this prompt, the answer is in one of the listed files.

---

## PROMPT BODY (copy from here)

Project: MindsOS (folder `halvim_mindsos/` under `Layered Intelligence`).

Your role: implement Phase 05d on a `phase-05d` branch off `origin/main`. **Design is fully locked** in the prior chat (2026-05-07, 6 reanalysis rounds, 7 meta-plan picks (M1–M7) + 30 numbered design pushbacks (P1–P30), 5 user overrides). The full pick log + rationale per pick lives in `confirmation_docs/PHASE_05d_DESIGN_LOG.md` — that is the canonical record of what was decided and why.

Do not re-litigate locked decisions. If implementation surfaces a contradiction with the locked row, surface it as a numbered pushback (continuing P31+) before continuing — the bar is "I cannot implement what was locked," not "I'd have picked differently."

CASC-1 cascade: `05a → 05b → 05c → 05d → 06`. 05c SHIPPED 2026-05-06 (tester-confirmed 901 + 2 skipped in-container; tag `phase-05c-confirmed`). You are unblocked.

**Branch:** `phase-05d` off `origin/main` (NEVER off `phase-05c`).
**Tag on confirm:** `phase-05d-confirmed`.
**Confirmation doc target:** `confirmation_docs/PHASE_05d_CONFIRMED.md`.
**Implementation log target:** `confirmation_docs/PHASE_05d_IMPLEMENTATION_LOG.md`.

### What 05d ships

Read the canonical row text. Do not rely on a summary in this prompt; the row is the source of truth for scope, validation orders, ADR amendments, state-file bumps, CLI surface, and risks:

> **`confirmation_docs/PHASE_MAP.md` §5 Phase 05d row** (look for `### Phase 05d — L1 MetaEdgeType + MetaHyperEdgeType vocab + fingerprint-based explicit-consent re-attach`)

The row has 10 sub-sections (§A–§J) plus inline ADR-0014 third amendment text. Read all of it.

### Mandatory reads (in this order; do NOT re-read older confirmation docs unless debugging a regression)

1. **`confirmation_docs/PHASE_05d_DESIGN_LOG.md`** — full pick log (M1–M7 + P1–P30) with rationale per pick, user overrides flagged, audit-resolution finding, primitive-distinction call-out, final lock summary. **Read this first** if you need to understand *why* a particular decision was made.
2. **`confirmation_docs/PHASE_MAP.md` §5 Phase 05d row** — canonical scope, validation orders, ADR text, fingerprint mechanism, state-file bumps, CLI surface, risks, future-work pointers. The implementation target.
3. **`confirmation_docs/PHASE_MAP.md` §1** — settled cross-cutting decisions; per-phase workflow; supersession policy.
4. **`confirmation_docs/PHASE_MAP.md` §5 Phase 05c row** — prior-phase precedent. 05d inherits unconditionally: schema-mutation footgun, `_find_attached_metagraphs` helper, eager-attach atomicity, `__setattr__` strict scope. Treat 05c row as the source of carry-forward patterns rather than re-deriving them.
5. **`confirmation_docs/PHASE_MAP.md` §5 Phase 05b row** — two-prior context per §0 read rule; validation-order precedent (P5 from 05d mirrors 05b IntergraphEdge order).
6. **`confirmation_docs/PHASE_05c_CONFIRMED.md` `tester_notes`** — most recent tester confirmation; recipe-deviation lessons 05d inherits.
7. **`confirmation_docs/PHASE_05c_IMPLEMENTATION_LOG.md`** — 05c bug ledger + 7 implementation pushbacks (P26–P32) + forward-compat §8.
8. **`confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`** — background context for the 4-vocab Cypher namespace policy and `MetagraphSchema` shape. Read the 2026-05-06 amendment block at the top first; it overrides body text where they conflict.

### Mandatory memory consultations (your auto-memory directory; read in this order)

1. **`reference_mindsos_four_edge_primitives.md`** — **READ THIS BEFORE ANY VOCAB CODE.** Canonical distinction between MetaEdge / MetaHyperEdge / IntergraphEdge / IntergraphHyperEdge with the cat=c+a+t / "letter" example. Load-bearing for understanding why `MetaHyperEdgeType` has no `ordered` field.
2. **`project_mindsos_phase_05d_design.md`** — full lock state for 05d (mirror of `confirmation_docs/PHASE_05d_DESIGN_LOG.md` content, but in memory format). Primary reload pack.
3. **`project_mindsos_intergraph_edge_question.md`** — 4-primitive + 4-vocab cross-phase view, state-file shape table across 05a–05d, future-work pointer index.
4. **`project_mindsos_phase_05c_implemented.md`** — what shipped in 05c + carry-forward patterns 05d inherits.
5. **`project_mindsos_phase_05c_design.md`** — 05c 20-pushback summary for context (especially P12-A schema-mutation footgun pattern + P18-A ordered default rationale that does NOT carry to MetaHyperEdgeType).
6. **`project_mindsos_phase_05a.md`** — base shape Metagraph + MetaEdge + MetaHyperEdge slim port. You DO NOT touch the dataclasses; the row's "P3 audit RESOLVED" finding confirms this.
7. **`project_mindsos_l1_redesign.md`** — 11+6 redesign locks; ADR status across the cascade.
8. **`feedback_test_budget_unlimited.md`** — test budget rule.
9. **`feedback_terse_step_recipes.md`** — execution communication style.
10. **`feedback_state_dir_env_var.md`** — recipe-authoring rule (`~/.mindsos/`, never `$MINDSOS_STATE_DIR`).
11. **`feedback_release_workflow_ordering.md`** — squash-merge before tagging.
12. **`feedback_tag_regex_audit.md`** — 5-site checklist (probably not triggered in 05d, but read so you know it exists).
13. **`feedback_docker_compose_invocation.md`** — Phase 02+ entrypoint behavior; rebuild image after pulling test-side fixes.
14. **`user_two_machine_setup.md`** — Mac/Linux split + canonical per-phase workflow steps (a)-(l).
15. **`reference_mindsos_layer_handoffs.md`** — per-layer handoff path index.

### Carry-forward locks + out-of-scope items

Both lists live in the row (`PHASE_MAP.md` §5 Phase 05d) and the design log (`PHASE_05d_DESIGN_LOG.md`). Do NOT pull anything forward that isn't in the row's scope. If unsure whether a feature is in scope, the design log's pick log is authoritative — every "in" item has a P-number lock; every "deferred" item points to a future-work entry at `_source_backup/root/mindsos_future_plans.md`.

### Communication style

Implementation chat uses execution voice per `feedback_terse_step_recipes.md`. Step recipes tagged `[Mac]` / `[Linux]`. Pushbacks (if any surface) in one block at end. Analysis voice ONLY if a row-text contradiction surfaces that genuinely cannot be implemented as locked — surface as numbered pushback (P31+) with options + your pick; wait for user response before continuing.

### Project instructions

Canonical per the project `CLAUDE.md`. Skeptical default; concise; no filler; no emojis; no restating user messages.

### First action

1. Read the 8 docs + 15 memory files above (in parallel where possible). **Read `reference_mindsos_four_edge_primitives.md` and `confirmation_docs/PHASE_05d_DESIGN_LOG.md` first** — the rest is precedent and context.
2. **Step 0 pre-implementation audit pass:**
   - Verify `MetaEdge.type_name` at `mindsos_core/models/metagraph.py:136` and `MetaHyperEdge.type_name` at `:180` (P3 audit pre-resolution; expected: both fields present, required, regex-validated).
   - Verify `Graph.role: Optional[str]` at `mindsos_core/models/graph.py:94` (load-bearing for `allowed_*_graphs` constraints).
   - Verify `_find_attached_metagraphs` helper at `mindsos_cli/commands/metagraph_schema.py:171` (load-bearing for P8 A schema-mutation footgun reuse).
   - Review `tests/phase_05a/test_state*.py`, `tests/phase_05b/test_state*.py`, `tests/phase_05c/test_state*.py` for hard-coded `_state_version` constants; flag any for migration to dynamic constants. Mirrors 05a P14 / 04-v2 / 05b / 05c audit pattern.
3. Report findings as a brief audit summary (file + line citations + any flagged hard-coded constants). Do NOT write any new code yet.
4. Wait for user sign-off before proceeding to Step 1.

### Workflow after Step 0 sign-off

The full per-phase workflow (steps a–l: branch, implement, test, recipe, confirm, tag, release) lives in `user_two_machine_setup.md`. Follow it verbatim. Two operational reminders to surface explicitly because they have bitten prior phases:

- **`feedback_state_dir_env_var.md`** — when authoring `notes-phase-05d.md` tester recipes, use `~/.mindsos/<kind>-<name>.json` literally; NEVER `$MINDSOS_STATE_DIR/...`. Hit twice (05b + 05c).
- **`feedback_release_workflow_ordering.md`** — squash-merge MUST land before tagging from main. Hit once in 05c. PR → `gh pr merge --squash --delete-branch` → pull main → verify `confirmation_docs/PHASE_05d_CONFIRMED.md` exists → re-tag → push.

### Memory updates at chat-end (after tester confirmation)

Create `project_mindsos_phase_05d_implemented.md` mirroring `project_mindsos_phase_05c_implemented.md` structure. Update MEMORY.md index entry. If new feedback patterns surface (regex audit, recipe correction, hotfix pattern), file as new `feedback_*.md` memory files.

## END PROMPT BODY (copy ends here)

---

## Notes for Henrique (NOT part of the prompt)

- Save this file before opening the new chat. Memory files load automatically when the new chat starts in the same project workspace.
- Reload cost in the next chat is 8 doc reads + 15 memory file reads. Bounded; expected to fit comfortably.
- Phase 06 follows 05d. Open a separate chat for the 06 row-refinement when 05d ships. Phase 06's row will need to address the deferred "instance-graph role mutability" question (filed at `_source_backup/root/mindsos_future_plans.md` "Instancing semantics" section).
