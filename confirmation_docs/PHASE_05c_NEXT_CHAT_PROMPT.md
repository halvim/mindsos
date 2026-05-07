# Phase 05c Implementation — Next-Chat Handoff Prompt

> Authored 2026-05-06 in the 05c row-refinement chat. Paste the **PROMPT BODY** section below into a fresh Claude chat (in the MindsOS project) when ready to implement Phase 05c.

---

## PROMPT BODY (copy from here)

Project: MindsOS (folder `halvim_mindsos/` under `Layered Intelligence`).

Your role: implement Phase 05c on a `phase-05c` branch off `origin/main`. **Design is fully locked** in the prior chat (2026-05-06, 4 reanalysis rounds, 20 numbered pushbacks, 3 sign-off items). Do not re-litigate locked decisions; if implementation surfaces a contradiction, flag it explicitly with a numbered pushback before continuing — but the bar is "I cannot implement what was locked," not "I'd have picked differently."

Phase 05c ships the n-ary `IntergraphHyperEdge` primitive + `IntergraphHyperEdgeType` schema vocab + a single replace-only `update_intergraph_hyperedge` factory + 4 CLI verbs on `mindsos metagraph` subapp + 1 CLI verb on `mindsos metagraph-schema` subapp + 5-way set-prop mutex + metagraph state-file v=2→v=3 + metagraph-schema state-file v=1→v=2 + ADR-0148 amendment + ADR-0014 second amendment. **Meta-vocabs (`MetaEdgeType` + `MetaHyperEdgeType`) were further deferred to NEW Phase 05d** via 05c P1-B split — do NOT pull them forward. Phase 05d's row stub is authored alongside 05c's row; 05d gets its own row-refinement chat AFTER 05c ships.

CASC-1 lock: cascade is now `05a → 05b → 05c → 05d → 06`. 05b SHIPPED 2026-05-05/06 (tester-confirmed 740/2 in-container; tag `phase-05b-confirmed`). You are unblocked.

### Mandatory reads (in this order; do NOT re-read older confirmation docs unless debugging a regression):

1. **`confirmation_docs/PHASE_MAP.md` §1** (settled cross-cutting decisions incl. SUPER-§1-EXT letter sub-phase amendment + supersession policy + per-phase workflow).
2. **`confirmation_docs/PHASE_MAP.md` §5 Phase 05c row** (lines ~1465-1797 — the canonical row LOCKED 2026-05-06; 20 pushbacks; §A 16-step validation order; §B ADR-0148 amendment text; §C ADR-0014 second amendment; §D 05d dry-run appendix).
3. **`confirmation_docs/PHASE_MAP.md` §5 Phase 05b row** (the prior phase precedent — patterns 05c inherits: `__setattr__` override mechanism, attach_schema atomicity, metagraph state-file migration chain, schema-mutation footgun warning, validation-order documentation pattern).
4. **`confirmation_docs/PHASE_MAP.md` §5 Phase 05a row** (two-prior context per §0 read rule).
5. **`confirmation_docs/PHASE_MAP.md` §5 Phase 05d row stub** (immediately after the 05c row — read so you know what NOT to ship in 05c; 05d carries MetaEdgeType + MetaHyperEdgeType).
6. **`confirmation_docs/PHASE_05b_CONFIRMED.md` `tester_notes`** (most recent confirmation; 6-hotfix ledger + 3 manual-recipe deviations + the canonical 740/2 baseline + lessons that 05c inherits).
7. **`confirmation_docs/PHASE_05b_IMPLEMENTATION_LOG.md`** (full bug ledger + the 34 pushback locks + the migration-chain pattern that 05c extends + forward-compat §8 already pre-resolves much of 05c for you).
8. **`confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`** — canonical for the intergraph edge family. **Read the "2026-05-06 amendment block" at the top FIRST** — it overrides body text where they conflict (ordered default flipped to True, compositional+ordered=False refusal, __setattr__ scope clarification, update API, symmetric-IntergraphEdge rejection, paired flags, 16-step order, phase placement w/ 05d, state-file shape table). Then read the rest of the doc as background context.

### Mandatory memory consultations (your auto-memory directory):

- **`project_mindsos_phase_05c_design.md`** — what's locked, what's deferred, 20-pushback summary, 16-step validation order, persistence shapes, modules touched, pre-implementation audit task, tester-recipe pointers. Your primary reload pack.
- **`project_mindsos_phase_05d_design.md`** — what's NOT in 05c (so you don't accidentally pull 05d work forward).
- **`project_mindsos_phase_05b_implemented.md`** — what shipped in 05b + 6-hotfix ledger + recipe deviations + carry-forward patterns (esp. `__setattr__`, attach_schema, migration chain, CLI fixture pattern).
- **`project_mindsos_phase_05b_design.md`** — 34-pushback summary for context (esp. Push7-A eager-validation atomicity, Push17-A precheck pattern, Push22-A `__setattr__`, Push23-A schema-mutation footgun, Push29-A attach atomicity, Push32-A/D re-attach freshness — all carry-forward).
- **`project_mindsos_intergraph_edge_question.md`** — primitive split + canonical pointer + 05c locks summary + future-work registry.
- **`project_mindsos_phase_05a.md`** — base shape Metagraph + MetaEdge + MetaHyperEdge slim port (you DO NOT touch metaedges/metahyperedges in 05c; 05d does).
- **`project_mindsos_l1_redesign.md`** — 11+6 redesign locks; ADR status across the cascade.
- **`feedback_test_budget_unlimited.md`** — test budget rule (NEVER cap; project realistic coverage and ship it).
- **`feedback_terse_step_recipes.md`** — execution communication style (`[Mac]` / `[Linux]` tagged step recipes; analysis voice only during design discussions, NOT during implementation).
- **`feedback_tag_regex_audit.md`** — 5-site checklist if any new tag-form lock surfaces (probably not relevant for 05c since no new tag form, but read so you know the audit pattern exists).
- **`feedback_docker_compose_invocation.md`** — Phase 02+ entrypoint behavior; rebuild test image after pulling test-side fixes (B-05b-T2 lesson — stale Docker image hotfix in 05b).
- **`user_two_machine_setup.md`** — Mac edits, Linux tests, sync via git push/pull. **Canonical per-phase workflow (a)-(l) is in this file.** Note: confirm-phase ordering — edit `notes-phase-05c.md` FIRST, THEN run `mindsos confirm-phase --phase 05c --notes-file notes-phase-05c.md` (the wrapper reads from the notes file).
- **`reference_mindsos_layer_handoffs.md`** — per-layer handoff path index.

### Carry-forward locks from 05b (load-bearing — DO NOT redesign; 05c inherits unconditionally):

All carry-forward patterns are documented in the 05c row's "Locked decisions" section + the "Smaller items folded" subsection. Read those rather than asking. Key reuses: Push7-A eager-validation atomicity; Push14-A `mint_id`; Push17-A precheck pass extension to walk hyperedges; Push18-A `RESERVED_PROPERTY_KEYS` extension; Push22-A `__setattr__` mechanism (now scoped per P2-refined); Push23-A schema-mutation footgun; Push27-A mutex extension (4-way → 5-way); Push29-A attach atomicity; Push32-A/D re-attach freshness; Push33-A flat CLI surface accepted; Push34-A no `remove-*-type` verb.

### Out of scope for 05c (filed as future-work or deferred to later phases — DO NOT pull forward):

See the 05c row "Out of scope" subsection + the 05d row stub for what's deferred. Key non-shipping items: MetaEdgeType / MetaHyperEdgeType (Phase 05d); MetaEdge.type_name field audit (Phase 05d); symmetric `update_intergraph_edge_endpoints` on binary primitive (filed at `_source_backup/root/mindsos_future_plans.md` "Intergraph primitive structural mutation" / "Discoverable endpoint-update verb for IntergraphEdge"); in-place hyperedge→edge downgrade (same future-work section / "In-place hyperedge→edge downgrade with edge_id stability"); soft-delete substrate uniformly (Phase 10); `RemovalImpact` + `force=True` (Phase 10); FalkorDB persistence + Cypher Pattern B emit + n-lock canonical OCC implementation (Phase 07; 05c locks the contract per design §3.4 but does NOT implement); XRef cross-metagraph (Phase 09); Element instancing (Phase 06).

### 3 sign-off items confirmed at row commit (2026-05-06):

1. Phase 06 dep = `03, 05d` (CASC-1 strict-sequential through the entire 05 family). Already updated in PHASE_MAP §3 + Phase 06 row text.
2. **05b CHANGELOG amendment for P13-B retreat** ("Discoverable endpoint-update workaround") lands on `phase-05c` branch as a single commit alongside 05c implementation, NOT standalone on `main`.
3. MetagraphSchema state-file v=1→v=2 in 05c (intergraph_hyperedge_types only); v=2→v=3 in 05d (meta_edge_types + meta_hyperedge_types). Two separate bumps with strict-version contract on each.

### Recommended workflow for this chat (mirror the 05a/05b execution pattern):

1. **Read the 8 docs + 12 memory files above.** Don't ask the user for content that's in the files.
2. **Pre-implementation audit pass** (locked task in 05c row "Automated tests" section): review every `tests/phase_05a/test_state*.py` and `tests/phase_05b/test_state*.py` for hard-coded `_state_version: 2` (metagraph) and `_state_version: 1` (metagraph-schema) constants; update to use `state_mod.METAGRAPH_STATE_VERSION` / `state_mod.METAGRAPH_SCHEMA_STATE_VERSION` dynamically. Symmetric with 05a P14 / 04-v2 / 05b audit. Lock as Step 0 before touching any new code.
3. **Read current state of touched files** before editing — at minimum: `mindsos_core/models/intergraph_edge.py` (the 05b sibling pattern your new file mirrors), `mindsos_core/models/metagraph.py` (your extension target), `mindsos_core/schema/metagraph_schema.py`, `mindsos_core/schema/types.py`, `mindsos_core/schema/validation.py`, `mindsos_cli/commands/metagraph.py`, `mindsos_cli/commands/metagraph_schema.py`, `mindsos_cli/state.py`, `mindsos_cli/migrations/metagraph.py`, `mindsos_cli/migrations/metagraph_schema.py`. Track read-state so subsequent Edit calls don't fail with "File has not been read yet."
4. **Implement on `phase-05c` branch off `origin/main`** (NEVER off `phase-05b`). Author the new file (`mindsos_core/models/intergraph_hyperedge.py`) first; extend the existing files in dependency order (model → schema → CLI → state → migrations); manifest + version bumps last.
5. **Write tests in `tests/phase_05c/`** following the test-file plan in the 05c row "Automated tests" subsection. Test budget unlimited per `feedback_test_budget_unlimited.md` — project realistic coverage and ship it. Final count whatever coverage requires; tester records actual at confirmation time.
6. **Author `confirmation_docs/PHASE_05c_IMPLEMENTATION_LOG.md`** mirroring 05a/05b structure (sections: pre-implementation audit findings, file ledger, bug ledger D-05c-N / B-05c-N during local iteration, deviations from row text if any).
7. **Author the 05b CHANGELOG amendment** for the P13-B retreat — single commit on `phase-05c` branch documenting the workaround pattern (remove + add with `--intergraph-edge-id <orig>` override). Reference the new future-work entry in `_source_backup/root/mindsos_future_plans.md` "Intergraph primitive structural mutation" section.
8. **Author tester recipe** with `[Mac]` / `[Linux]` tags per `feedback_terse_step_recipes.md`. Every step = `<command>` + `<expected outcome>`. No options, no reasoning. Pushbacks (if any surface during implementation) in one block at end. The full per-phase workflow checklist is in `user_two_machine_setup.md` (paths a-l). **Critical**: `notes-phase-05c.md` editing FIRST, THEN `mindsos confirm-phase --phase 05c --notes-file notes-phase-05c.md` (the wrapper reads from the notes file — user caught this reversed in 05b).
9. **Update memory at end of chat** (after tester confirmation): `project_mindsos_phase_05c_implemented.md` (NEW; mirror `project_mindsos_phase_05b_implemented.md` structure) + index entry in `MEMORY.md`. If new feedback patterns surface (e.g., another regex audit, recipe correction, hotfix pattern), file them as `feedback_*.md`.

### Communication style (memory `feedback_terse_step_recipes.md`):

- **Implementation chat = execution voice.** Terse step recipes (`<command>` → `<expected outcome>`, every step `[Mac]` or `[Linux]` tagged, pushbacks in one block at end).
- **Analysis voice ONLY if a row-text contradiction surfaces** that genuinely cannot be implemented as locked. In that case, surface as a numbered pushback (P26+ — continuing the 05c chat's numbering) with options + your pick; wait for user response before continuing.

### Project instructions (canonical per the project CLAUDE.md):

The user is a critical design reviewer. Default posture skeptical. Concise by default. No filler ("Great question", "That's an interesting approach", etc.). No emojis. No restating user messages.

### First action:

Read the 8 docs + 12 memory files above (in parallel where possible). Then start with **Step 0: pre-implementation audit pass** (read the 05a/05b state-version test files; identify hard-coded constants). Report findings as a brief audit summary (just the offending file paths + line numbers + the constants found). Wait for user sign-off before proceeding to Step 1 (new file authoring on `phase-05c` branch).

## END PROMPT BODY (copy ends here)

---

## Notes for Henrique (NOT part of the prompt)

- Save this file before opening the new chat. Memory files are inside the auto-memory directory and will load automatically when the new chat starts in the same project workspace.
- The reload cost in the next chat is the 8 doc reads + 12 memory file reads. Bounded; expected to fit comfortably in the implementation chat's budget.
- If the next chat surfaces a row-text correction, it should follow the supersession-policy pattern (small additive corrections) OR escalate as numbered pushback (large structural ones).
- Phase 05d follows 05c. Open a separate chat for the 05d row-refinement when 05c ships.
