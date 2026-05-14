# Phase 08 — Next Chat Handoff Prompt (design refinement)

> Authored 2026-05-13 at the close of the Phase 07 implementation chat.
> Paste the **PROMPT BODY** section into a fresh Claude chat (MindsOS
> project) when ready to refine the Phase 08 row.
>
> **Design philosophy:** navigation guide, not content dump. Scope, ADR
> texts, prior pushback ledgers, hotfix patterns — all of that lives in
> files. The prompt below lists those files in load order; the chat
> reads them, runs Step 0 on-disk audits, then opens design rounds.

---

## PROMPT BODY (copy from here)

Project: MindsOS (folder `halvim_mindsos/` under `Layered Intelligence`).

**Your role:** refine the Phase 08 row in
`confirmation_docs/PHASE_MAP.md` §5 from the existing stub
(`### Phase 08 — L1 Reconstruction (loaders, streaming, refresh)`)
into a fully-locked row, using the design-refinement pattern from
Phases 05a / 05b / 05c / 05d / 06 / 07 (3-6 rounds, M-picks +
P-picks, user agreement per round).

**DO NOT implement.** This is the design-refinement chat. The
implementation chat comes after lock + handoff prompt.

**CASC-1 cascade position:** Phase 07 SHIPPED 2026-05-13 (tag
`phase-07-confirmed` on `origin/main`). Phase 08 is unblocked.

### What Phase 08 ships (per the stub)

Read the canonical stub — do not rely on a summary in this prompt:

> `confirmation_docs/PHASE_MAP.md` §5 Phase 08 row stub
> (`### Phase 08 — L1 Reconstruction (loaders, streaming, refresh)`).

Stub identifies: load graph + load metagraph (full + streaming per
ADR-0124) + refresh; lazy-Local-hydration interaction (ADR-0125)
`refresh` must respect LRU eviction.

### Mandatory reads (in this order)

1. **`confirmation_docs/PHASE_MAP.md` §1** — settled cross-cutting
   decisions; per-phase workflow steps (a)–(l); supersession policy.
2. **`confirmation_docs/PHASE_MAP.md` §5 Phase 08 row stub** — the
   target.
3. **`confirmation_docs/PHASE_MAP.md` §5 Phase 07 row** — the
   shipped-Phase-07 contract Phase 08 builds on. Phase 07 deferred to
   Phase 08 (per M14 + P12 D + P98 A):
   - Metagraph `sync` CLI verb (Phase 07 ships `MetagraphRepository.persist`
     programmatic-only per P60 A).
   - Metagraph `load` CLI verb.
   - Full `mindsos persistence verify --source=db --metagraph M` (Phase 07
     ships graph-scoped `verify_invariants_graph` partial per P98 A;
     Phase 08's metagraph_loader unblocks the full scanner against
     FalkorDB).
   - `:WALEntry` recovery consumer integration (Phase 07 ships mechanism
     + replayer registry; no L1 consumer).
4. **`confirmation_docs/PHASE_07_CONFIRMED.md`** — tester baseline 1269
   passed + 2 skipped in-container; tester_notes section captures the
   4 hotfixes + 2 Step 0 probe outcomes (FalkorDB v4.18.3 quirks).
5. **`confirmation_docs/PHASE_07_DESIGN_LOG.md`** + **`PHASE_07_ROUND_6_ADDENDUM.md`**
   — design history; relevant for Phase 08 only insofar as Phase 07
   deferred items.
6. **ADRs at project-root `/Layered Intelligence/docs/decisions/adr/`
   (Model C hybrid per P30 A; outside halvim_mindsos git):**
   - `0124-streaming-loader-iter-load-and-refresh.md` (Proposed; Phase
     08 ships consumer → flip Accepted per M3 A precedent).
   - `0125-lazy-local-hydration-with-lru-eviction.md` (Proposed; same
     pattern; Phase 08 may also flip).
   - `0030-client-protocol-minimal-sync.md` (Accepted; Client surface
     unchanged).
   - `0121-substrate-falkordb-for-graphs-sqlite-for-non-graph.md`
     (substrate umbrella).
   - `0122-wal-graph-for-multi-statement-write-safety.md` (Accepted in
     Phase 07; consumer integration via Phase 08 metagraph persist
     CLI verb).
   - `0123-indexes-and-verify-integrity.md` (Accepted in Phase 07).
   - `0126-async-client-via-thread-pool-wrapper.md` (Accepted in
     Phase 07; metagraph_loader may consume).
   - `0127-optimistic-concurrency-on-global-writes.md` (Accepted in
     Phase 07).
7. **v3 baseline reconstruction source files** (slim-port material;
   live at project root, NOT in halvim_mindsos):
   - `/Layered Intelligence/mindsos_core/reconstruction/graph_loader.py`
     (Phase 07 already ported single-Graph slim version; check what's
     in v3 for streaming + iter_load + refresh).
   - `/Layered Intelligence/mindsos_core/reconstruction/metagraph_loader.py`
     (the metagraph reconstruction surface Phase 08 ports).

### Mandatory memory consultations (auto-memory; read in this order)

1. **`project_mindsos_phase_07_implemented.md`** — Phase 07 state +
   what's deferred to Phase 08. **Primary reload pack.**
2. **`project_mindsos_l1_redesign.md`** — 11+6 redesign locks; ADR
   status across the cascade (Phase 07 flipped 0122/0123/0126/0127;
   0124+0125 still Proposed).
3. **`reference_mindsos_layer_handoffs.md`** — per-layer handoff
   paths; Phase 07 tester-baseline 1269/2 noted.
4. **`feedback_falkordb_index_ddl_quirks.md`** (NEW 2026-05-13) —
   FalkorDB v4.18.3 substrate quirks. Phase 08 reads will hit
   `db.indexes()` if `diagnose` is extended; mind the per-label
   grouping.
5. **`feedback_cli_config_manifest_fallback.md`** (NEW 2026-05-13) —
   env-then-manifest-then-default pattern for any new CLI env var.
6. **`feedback_dockerfile_test_stage_file_reads.md`** (NEW 2026-05-13)
   — 6-site checklist for any new host file a test reads.
7. **`feedback_new_top_level_package.md`** — 5-site checklist. Phase
   08 likely does NOT add a new top-level package (extends
   `reconstruction/` subpackage).
8. **`feedback_confirm_phase_timeout.md`** — 900s timeout shipped in
   Phase 07; pre-build recipe carries forward.
9. **`feedback_state_dir_env_var.md`** — recipe-authoring rule
   (`~/.mindsos/` literal, never `$MINDSOS_STATE_DIR`).
10. **`feedback_release_workflow_ordering.md`** — squash-merge before
    tagging.
11. **`feedback_state_version_audit_scope.md`** — if Phase 08 bumps a
    state file, grep ALL test files for the literal.
12. **`feedback_tag_regex_audit.md`** — 5-site checklist (probably not
    triggered in 08).
13. **`feedback_test_budget_unlimited.md`** — no test-count cap.
14. **`feedback_terse_step_recipes.md`** — execution communication
    style.
15. **`feedback_docker_compose_invocation.md`** — Phase 02+ entrypoint
    behavior.
16. **`feedback_docs_source_of_truth.md`** — Model C hybrid; ADRs at
    project root.
17. **`user_two_machine_setup.md`** — Mac/Linux split + canonical
    per-phase workflow steps (a)–(l).
18. **`reference_mindsos_four_edge_primitives.md`** — relevant when
    metagraph_loader needs to round-trip all 4 edge primitives.

### Design refinement structure (pattern from Phases 05a–07)

Run the design chat as a sequence of reanalysis rounds (target 3–6
rounds, open-ended). Each round surfaces concerns + locks picks.
Numbered picks M0, M1, … for meta-plan-level choices (round count,
test split, ADR-flip policy, etc.); P1, P2, … for design-level
picks. User confirms each round explicitly.

**Likely Phase 08 design-question seeds** (NOT pre-locked — surface
+ pushback in design rounds):

1. **Streaming vs full-load API split.** ADR-0124 specifies
   `iter_load(role, batch_size)`. Should Phase 08 ship BOTH `load()`
   (full) and `iter_load()` (streaming), or just one? V3 baseline
   has both — does the slim port preserve the split?
2. **`refresh(role)` semantics.** ADR-0125 + ADR-0124 — does refresh
   ALWAYS re-fetch from FalkorDB, or honour an LRU staleness window?
   ADR-0125's LRU eviction model applies to server-side (L0/L2);
   Phase 08 may ship the L1 mechanism with the policy at L0 / L2.
3. **Metagraph `sync --metagraph M` CLI verb.** Phase 07 deferred per
   P12 D. Does Phase 08 ship it now, or just the load side?
4. **`verify --source=db --metagraph M`** unblock. Phase 07's
   `verify_invariants_graph` partial scanner stays; Phase 08's
   metagraph_loader enables the full `verify_invariants(mg)` against
   FalkorDB. CLI flag refusal at P49 A → drop.
5. **WAL consumer integration.** ADR-0122's consumer-integration
   acceptance criterion (P27 C amendment) said "tracked separately."
   Does Phase 08 introduce the first real WAL consumer (e.g.,
   `MetagraphRepository.persist` wraps its multi-statement write in
   a WAL entry)?
6. **Test budget.** Per `feedback_test_budget_unlimited.md`, no cap.
   Phase 07 added 142 tests; Phase 08 streaming + refresh probably
   adds 50–100 more. Project realistic coverage.
7. **State-file bumps.** No state-file bumps expected (Phase 08 is
   FalkorDB-side reads; JSON state files stay v=4/v=2/v=1). Confirm
   via Step 0 grep across all `_state_version` literals
   (`feedback_state_version_audit_scope.md`).

### Step 0 pre-design audit pass

Before round 1, the chat runs a Step 0 audit per the Phase 07
precedent (see `PHASE_07_ROUND_6_ADDENDUM.md` §4 for shape):

- Resync verification: `git log origin/main --oneline -5` includes
  Phase 07 squash-merge. `phase-07-confirmed` tag exists.
- v3 baseline reconstruction source files exist at project root.
- `mindsos_core/reconstruction/graph_loader.py` (slim-port from Phase
  07) present in halvim_mindsos.
- `mindsos_core/reconstruction/metagraph_loader.py` does NOT yet
  exist in halvim_mindsos (Phase 08 introduces).
- ADRs 0124 + 0125 status read in full to confirm Proposed.

### Workflow on lock

Once design rounds converge:

1. Write `confirmation_docs/PHASE_08_DESIGN_LOG.md` — full pick log
   (M0-MN + P1-PN) with rationale per pick.
2. Replace the Phase 08 row stub in `PHASE_MAP.md` §5 with the
   locked row.
3. Write `confirmation_docs/PHASE_08_NEXT_CHAT_PROMPT.md` for the
   implementation chat (mirror this prompt's shape).
4. Commit on a `phase-08-design` branch (or directly on `phase-08`
   if the implementation chat is the same chat — Phase 06/07
   precedent: separate chats).
5. Open the implementation chat with the next-chat prompt as the
   first message.

### Communication style

Project `CLAUDE.md` rules apply: skeptical default; concise; no
filler; no emojis; no restating user messages.

Design rounds use analysis voice — pros/cons + alternatives format.
Each round closes with a numbered pushback ledger and explicit user
agreement. The pattern from Phases 05a–07 is the model.

### First action

Read the 7 docs + 18 memory files above in load order. Then run Step 0
audit. Then report Step 0 findings + open Round 1 with the
design-question seeds above (or stronger ones surfaced during the
read).

## END PROMPT BODY (copy ends here)

---

## Notes for Henrique (NOT part of the prompt)

- Phase 08 is design-refinement only. Implementation comes after lock
  + handoff prompt in a separate chat (Phase 06 / 07 precedent).
- Memory files load automatically when the new chat starts in the
  same project workspace. Reload cost: ~7 doc reads + 18 memory file
  reads. Bounded.
- The 4 new feedback memories from Phase 07 (`feedback_falkordb_index_ddl_quirks`,
  `feedback_cli_config_manifest_fallback`,
  `feedback_dockerfile_test_stage_file_reads`, plus the updated
  `project_mindsos_phase_07_implemented`) carry forward into Phase
  08. The chat will surface them during the read pass.
- After Phase 08 ships, Phase 09 (L1 XRef + cross-metagraph refs)
  follows per CASC-1.
