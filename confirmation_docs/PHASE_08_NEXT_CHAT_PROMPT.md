# Phase 08 Implementation — Next-Chat Handoff Prompt

> Authored 2026-05-13 at the close of the Phase 08 row-refinement chat (4 design rounds; row locked at `PHASE_MAP.md` §5; design log at `PHASE_08_DESIGN_LOG.md`). Paste the **PROMPT BODY** section below into a fresh Claude chat (in the MindsOS project) when ready to implement Phase 08.
>
> **Design philosophy of this prompt:** navigation guide, not content dump. Scope, locks, ADR amendments, validation orders, CLI surfaces, future-work entries — none of that is repeated here. The implementation chat reads the files listed below to recover that context. If you find yourself wanting a fact that isn't in this prompt, the answer is in one of the listed files.

---

## PROMPT BODY (copy from here)

Project: MindsOS (folder `halvim_mindsos/` under `Layered Intelligence`).

Your role: implement Phase 08 on a `phase-08` branch off `origin/main`. **Design is fully locked** in the prior chat (2026-05-13, 4 design rounds, 59 numbered picks: 15 meta-plan picks (M0-M15) + 14 Round-1 pushbacks (PB-1..14) + 14 Round-2 (RPB-1..14) + 15 Round-3 (RR-1..15) + 16 Round-4 (R4-1..16); 1 user override at lock time on RPB-7 — test budget uncapped). The full pick log + rationale per pick lives in `confirmation_docs/PHASE_08_DESIGN_LOG.md` — that is the canonical record of what was decided and why.

Do not re-litigate locked decisions. If implementation surfaces a contradiction with the locked row, surface it as a numbered pushback (continuing P60+ to keep continuity with Phase 07's P26-P100 range) before continuing — the bar is "I cannot implement what was locked," not "I'd have picked differently."

CASC-1 cascade: `05a → 05b → 05c → 05d → 06 → 07 → 08`. Phase 07 SHIPPED 2026-05-13 (tester-confirmed 1269 + 2 skipped in-container; tag `phase-07-confirmed` on main; PR #14 squash-merge at `b07fdc6`; Release CI green). You are unblocked.

**Branch:** `phase-08` off `origin/main` (NEVER off `phase-07`).
**Tag on confirm:** `phase-08-confirmed`.
**Confirmation doc target:** `confirmation_docs/PHASE_08_CONFIRMED.md`.
**Implementation log target:** `confirmation_docs/PHASE_08_IMPLEMENTATION_LOG.md`.

### What 08 ships

Read the canonical row text. Do not rely on a summary in this prompt; the row is the source of truth for scope, modules touched, CLI surface, tests, pass criterion, risks, and rollback hazards:

> **`confirmation_docs/PHASE_MAP.md` §5 Phase 08 row** (look for `### Phase 08 — L1 Reconstruction (metagraph loader + streaming + refresh)`).

The row has sub-sections for Locked decisions, Features in scope, Modules touched, Automated tests, Confirmation command, Pass criterion, Risks, Rollback hazards, Doc sections, Breaking changes, and Final amendments. Read all of it.

### Mandatory reads (in this order; do NOT re-read older confirmation docs unless debugging a regression)

1. **`confirmation_docs/PHASE_08_DESIGN_LOG.md`** — full pick log (M0-M15 + PB-1..14 + RPB-1..14 + RR-1..15 + R4-1..16) with rationale per pick, Step 0 audit results, convergence note, cross-chat dependencies. **Read this first** if you need to understand *why* a decision was made.
2. **`confirmation_docs/PHASE_MAP.md` §5 Phase 08 row** — canonical scope. The implementation target.
3. **`confirmation_docs/PHASE_MAP.md` §1** — settled cross-cutting decisions; per-phase workflow; supersession policy.
4. **`confirmation_docs/PHASE_MAP.md` §5 Phase 07 row** — prior-phase precedent. Phase 08 builds directly on Phase 07's `MetagraphRepository.persist` (programmatic side) + `register_persist_observer` + `recover()` mechanism + 5-bucket scanner + WAL primitives. Phase 08 unblocks the deferred items (`sync --metagraph M` CLI, `load --metagraph M` CLI, `verify --source=db --metagraph M`).
5. **`confirmation_docs/PHASE_MAP.md` §5 Phase 06 row** — Phase 08 inherits: `register_remove_observer` cascade (`refresh` choreography per RPB-2 A); `register_graph_added_observer` (refresh's reload step fires per-graph observer subscription); `attach_registry(mg)` idempotent helper (extends to subscribe `after_load` observer per PB-4 A).
6. **`confirmation_docs/PHASE_07_CONFIRMED.md` `tester_notes` + Hotfix ledger** — most recent tester confirmation; canonical 1269/2 baseline; B-07-T1 (FalkorDB index DDL quirks) / B-07-T2 (CLI config manifest fallback) / B-07-T3 (Dockerfile test-stage COPY) / B-07-T4 (db.indexes() row-count assertion). Phase 08 inherits the substrate quirks; the 3 new feedback memories are mandatory reads.
7. **`confirmation_docs/PHASE_06_CONFIRMED.md` `tester_notes`** — two-prior context per §0 read rule.
8. **`docs/decisions/adr/0124-streaming-loader-iter-load-and-refresh.md`** — streaming loader + refresh design (status: Proposed → flip to Accepted in 08 per M3 A). **Phase 08 amends ADR body per PB-3 A (drop redundant `metagraph_id` slot from `iter_load`) + impl-refs per RR-6 A; acceptance criterion per PB-14 C (P27 C wording + impl-refs list).**
9. **`docs/decisions/adr/0125-lazy-local-hydration-with-lru-eviction.md`** — STAYS PROPOSED (PB-1 A; server-side; layer: Server). Phase 08 does NOT flip. Read for context only.
10. **`docs/decisions/adr/0030-client-protocol-minimal-sync.md`** — Client Protocol (Accepted; Phase 08 doesn't change).
11. **`docs/decisions/adr/0121-substrate-falkordb-for-graphs-sqlite-for-non-graph.md`** — substrate umbrella.
12. **`docs/decisions/adr/0122-wal-graph-for-multi-statement-write-safety.md`** — WAL design (Accepted in 07; Phase 08 wires first L1 consumer via `load_metagraph` recover-on-load per PB-6 B).
13. **`docs/decisions/adr/0123-indexes-and-verify-integrity.md`** — 14-index + 5-bucket scanner (Accepted in 07; Phase 08 unblocks `verify --source=db --metagraph M` per PB-7 A).
14. **`docs/decisions/adr/0127-optimistic-concurrency-on-global-writes.md`** — OCC (Accepted in 07; Phase 08 inherits).
15. **`docs/decisions/adr/0130-property-bag-on-metagraph-graph.md`** — `_props_json` on Metagraph (read by Phase 08 loader; Graph .properties writer still deferred per Phase 07 P9 C).
16. **`docs/decisions/adr/0132-instancing-sibling-package.md`** — boundary preserved by Phase 08 sibling-package instance_loader.

**v3 baseline source files (slim-port source material, NOT runtime code):**

17. **`/Users/henriquealvim/Documents/Claude/Projects/Layered Intelligence/mindsos_core/reconstruction/metagraph_loader.py`** (v3 baseline; 236 LOC) — port source. **Strip XRef sub-loader (Phase 09) + `_migrate_legacy_settings(mg)` (RPB-6 A; substrate is fresh).**
18. **`/Users/henriquealvim/Documents/Claude/Projects/Layered Intelligence/mindsos_core/reconstruction/graph_loader.py`** (v3 baseline; 348 LOC) — port source for `iter_load` method (now `iter_load_graph` function per PB-3 A + PB-2 C). Halvim's existing `mindsos_core/reconstruction/graph_loader.py` (Phase 07 slim) gets the iter_load_graph addition + refactor to call iter via assemble (RR-12 A).
19. **`/Users/henriquealvim/Documents/Claude/Projects/Layered Intelligence/mindsos_instances/reconstruction/instance_loader.py`** (v3 baseline) — port source for sibling-package `mindsos_instances/reconstruction/instance_loader.py`. Phase 06 P36 A allow-list validation added per RR-3 A; orphan handling per RR-4 B.

### Mandatory memory consultations (your auto-memory directory; read in this order)

1. **`project_mindsos_phase_08_design.md`** — full lock state for 08 (mirror of `PHASE_08_DESIGN_LOG.md` in memory format). Primary reload pack. *Authored by the design chat; if absent in your memory, fall back to `PHASE_08_DESIGN_LOG.md` directly.*
2. **`project_mindsos_phase_07_implemented.md`** — what Phase 07 shipped + carry-forward patterns 08 inherits. WAL + recover + persist-observer + 5-bucket scanner references.
3. **`project_mindsos_phase_06_implemented.md`** — Phase 06 observer plumbing (`register_remove_observer` + `register_graph_added_observer` + `attach_registry` idempotent helper). Phase 08 mirrors for `register_after_load_observer`.
4. **`project_mindsos_l1_redesign.md`** — 11+6 redesign locks; W1-W6 mitigation index; ADR status across the cascade (Phase 07 flipped 0122/0123/0126/0127; Phase 08 flips 0124; 0125 stays Proposed).
5. **`reference_mindsos_four_edge_primitives.md`** — primitive distinction (load-bearing for round-tripping all 4 edge primitives in MetagraphLoader.load per locked R4-1 sequence).
6. **`feedback_falkordb_index_ddl_quirks.md`** (Phase 07) — FalkorDB v4.18.3 substrate quirks. Phase 08 reads will hit `db.indexes()` if `diagnose` extended (it's NOT in Phase 08 scope); mind the per-label grouping anyway.
7. **`feedback_cli_config_manifest_fallback.md`** (Phase 07) — env-then-manifest-then-default pattern. Phase 08 doesn't add new env vars but inherits the pattern for any new CLI invocation.
8. **`feedback_dockerfile_test_stage_file_reads.md`** (Phase 07) — 6-site checklist for any new host file a test reads. Phase 08's new `tests/_shared/large_graph_factory.py` + `metagraph_equality.py` are test-shared modules; audit Dockerfile test stage COPY accordingly.
9. **`feedback_new_top_level_package.md`** — 5-site checklist. Phase 08 does NOT add a new top-level package (`mindsos_instances/reconstruction/` is a sub-package). Audit sentinel-paths + Dockerfile + pyproject + doctor + host-install regardless. Sub-package may need Dockerfile COPY in both stages depending on Phase 06 wildcard behavior.
10. **`feedback_confirm_phase_timeout.md`** — pre-build before `confirm-phase`. Phase 07 bumped to 900s; Phase 08 inherits. Pre-build recipe required: `docker compose --profile test build mindsos-test` BEFORE `mindsos confirm-phase`.
11. **`feedback_state_dir_env_var.md`** — recipe-authoring rule (`~/.mindsos/`, never `$MINDSOS_STATE_DIR`).
12. **`feedback_release_workflow_ordering.md`** — squash-merge before tagging.
13. **`feedback_state_version_audit_scope.md`** — Phase 08 does NOT bump state files (M0 carried); audit confirms absence rather than rebases literals. **Grep ALL `tests/` for `_state_version` literals to confirm.**
14. **`feedback_tag_regex_audit.md`** — 5-site checklist (probably not triggered in 08; image tag `phase08-prod` matches existing regex since Phase 05a). Read so you know it exists.
15. **`feedback_test_budget_unlimited.md`** — test budget rule. Phase 08 RPB-7 user override 2026-05-13: do as many tests as needed; no projection.
16. **`feedback_terse_step_recipes.md`** — execution communication style.
17. **`feedback_docker_compose_invocation.md`** — Phase 02+ entrypoint behavior; rebuild image after pulling test-side fixes; `mindsos-test` profile already has FalkorDB sidecar reachable.
18. **`feedback_docs_source_of_truth.md`** — Model C hybrid docs precedent.
19. **`user_two_machine_setup.md`** — Mac/Linux split + canonical per-phase workflow steps (a)-(l).
20. **`reference_mindsos_layer_handoffs.md`** — per-layer handoff path index.

### Carry-forward locks + out-of-scope items

Both lists live in the row (`PHASE_MAP.md` §5 Phase 08) and the design log (`PHASE_08_DESIGN_LOG.md`). Do NOT pull anything forward that isn't in the row's scope. If unsure whether a feature is in scope, the design log's pick log is authoritative.

**Explicitly OUT of Phase 08 scope:**

- XRef CRUD + cutover (Phase 09). Phase 08 establishes the after_load observer pattern Phase 09 inherits.
- Soft-delete read-path filter + RemovalImpact (Phase 10).
- `persistence reset --force` (Phase 11; richer integrity scanner verifies before wipe).
- Graph `.properties` writer (PHASE_MAP §7 Q4 deferral; Phase 07 P9 C carry-forward).
- ADR-0125 (lazy-Local hydration + LRU) — server-side; stays Proposed (PB-1 A); flip happens at Phase 18+.
- Per-role mutation-flag tracking + `RefreshUnsafeError` enforcement (PB-5 B; class only).
- Cypher schema migration (Phase 11).
- `inspect-state --metagraph M` per-metagraph drill-down (RR-11 B; Phase 11).
- `iter_load --stream` CLI surface (PB-10 A; programmatic-only).
- Metagraph-of-many-graphs streaming pagination (RR-2 D `batch_size` is per-contained-graph; whole-metagraph streaming Phase 11+).
- Memory-pressure-based budget tests (PB-12 C; structural only).
- Real memory-scale validation at 1M-node scale (future scale-test phase).
- `ReconstructionError` umbrella (R4-3 A; `PersistenceError` suffices).
- Legacy `:MetagraphSettings` migration (RPB-6 A; stripped from port).
- ADR semantic edits beyond status flip + impl-refs amendment (Phase 38; M3 A scope limit).

### Communication style

Implementation chat uses execution voice per `feedback_terse_step_recipes.md`. Step recipes tagged `[Mac]` / `[Linux]`. Pushbacks (if any surface) in one block at end. Analysis voice ONLY if a row-text contradiction surfaces that genuinely cannot be implemented as locked — surface as numbered pushback (P60+) with options + your pick; wait for user response before continuing.

### Project instructions

Canonical per the project `CLAUDE.md`. Skeptical default; concise; no filler; no emojis; no restating user messages.

### First action

1. Read the 16 docs + 20 memory files above (in parallel where possible). **Read `confirmation_docs/PHASE_08_DESIGN_LOG.md` and the Phase 08 row first** — the rest is precedent and context.
2. **Step 0 pre-implementation audit pass:**
   - Verify Phase 07 squash-merge on main: `git log origin/main --oneline -3` includes `b07fdc6 Phase 07 — L1 Persistence (#14)`. Tag `phase-07-confirmed` exists.
   - Verify v3 baseline reconstruction modules exist at the project-root paths (items 17-19 above). Confirm slim-port source material available.
   - Verify halvim_mindsos `mindsos_core/reconstruction/metagraph_loader.py` does NOT yet exist (Phase 08 introduces).
   - Verify halvim_mindsos `mindsos_instances/reconstruction/` directory does NOT yet exist (Phase 08 introduces).
   - Verify halvim_mindsos `mindsos_core/reconstruction/graph_loader.py` exists at Phase 07 slim form (function `load_graph`; no `iter_load`).
   - Verify `mindsos_core/models/metagraph.py` has `register_persist_observer` (Phase 07) + `register_remove_observer` + `register_graph_added_observer` (Phase 06); does NOT have `register_after_load_observer` (Phase 08 adds).
   - Verify `mindsos_core/exceptions.py` has 4 Phase-07 exception classes (`PersistenceError`, `IntegrityCheckError`, `OptimisticConcurrencyConflict`, `OptimisticConcurrencyExhausted`); does NOT have `RefreshUnsafeError` / `WALReplayerMissingError` / `RoleMismatchError` (Phase 08 adds 3).
   - **RR-1 A AUDIT:** Verify whether `IdentityRegistry.unregister(uid)` exists as public method in `mindsos_core/models/identity.py`. If present: no edit. If absent: Phase 08 adds additively (loud finding in audit report).
   - Verify ADR-0124 frontmatter `status: Proposed` (Phase 08 flips Accepted).
   - Verify ADR-0125 frontmatter `status: Proposed` + `layer: Server` (Phase 08 does NOT flip).
   - Verify `mindsos_cli/manifest.toml` has `[mindsos] phase = "07"` (Phase 08 bumps to "08").
   - Verify state files at v=4 / v=3 / v=1 unchanged (graph / metagraph / schema). No Phase 08 bump expected per M0.
   - Grep ALL `tests/` for `_state_version` literals; confirm no hard-coded values that would break under M0 invariant (per `feedback_state_version_audit_scope.md`).
   - Verify `mindsos_core/persistence/wal.py` exists with `recover(client, metagraph_id)` function + `register_replayer(kind, replayer)` API (Phase 08 PB-6 B + RPB-3 C consume).
   - Verify `mindsos_core/persistence/integrity.py` has `verify_invariants(mg) -> IntegrityReport` (Phase 08 PB-7 A consumes for `--source=db --metagraph M`).
   - Verify `tests/_shared/` has `graph_equality.py` + `falkordb_fixture.py` + `raises_on_nth_call.py` (Phase 07 fixtures; Phase 08 adds `metagraph_equality.py` + `large_graph_factory.py`).
3. Report findings as a brief audit summary (file + line citations + any anomalies). Do NOT write any new code yet.
4. Wait for user sign-off before proceeding to Step 1.

### Workflow after Step 0 sign-off

The full per-phase workflow (steps a-l: branch, implement, test, recipe, confirm, tag, release) lives in `user_two_machine_setup.md`. Follow it verbatim. Three operational reminders to surface explicitly:

- **`feedback_state_dir_env_var.md`** — when authoring `notes-phase-08.md` tester recipes, use `~/.mindsos/<kind>-<name>.json` literally; NEVER `$MINDSOS_STATE_DIR/...`. Hit twice in 05b/05c.
- **`feedback_release_workflow_ordering.md`** — squash-merge MUST land before tagging from main. PR → `gh pr merge --squash --delete-branch` → pull main → verify `confirmation_docs/PHASE_08_CONFIRMED.md` exists → re-tag → push.
- **`feedback_confirm_phase_timeout.md`** — timeout already at 900s (Phase 07 M12). Pre-build recipe required: `docker compose --profile test build mindsos-test` BEFORE `mindsos confirm-phase`.

### Implementation order recommendation (not locked; pick at impl time)

The row leaves implementation order to the chat per PHASE_MAP §2 schema. Suggested dependency-flow order:

1. `mindsos_core/exceptions.py` — add 3 new exceptions per R4-3 A (`RefreshUnsafeError`, `WALReplayerMissingError`, `RoleMismatchError`).
2. `mindsos_core/models/identity.py` — `unregister(uid)` method if Step-0 audit found missing (RR-1 A); skip if present.
3. `mindsos_core/_observers.py` — `_dispatch_after_load(observers, mg)` helper (RR-9 A).
4. `mindsos_core/models/metagraph.py` — `register_after_load_observer` + `_after_load_observers` list (mirror Phase 07 `register_persist_observer`).
5. `mindsos_core/reconstruction/graph_loader.py` — add `iter_load_graph(client, gid, *, identity, batch_size)` function (PB-3 A); refactor `load_graph` to call iter + assemble (RR-12 A); preserve Phase 07 surface.
6. `mindsos_core/reconstruction/metagraph_loader.py` — **NEW**. Class `MetagraphLoader(client)` + module function `load_metagraph(client, mid, *, batch_size, identity, schema)`. Implements locked R4-1 sequence with recover() first (R4-8 A). `.refresh(mg, role, *, schema)` uses proper `mg.remove_graph(gid)` API (RPB-2 A). Empty-role log-warn (R4-2 D); role-mismatch raise `RoleMismatchError` (R4-2 D).
7. `mindsos_core/reconstruction/__init__.py` — export 6 symbols per R4-12 A.
8. `mindsos_instances/reconstruction/__init__.py` + `instance_loader.py` — **NEW** sibling-package subpackage. Slim port from v3; override allow-list validation at load (RR-3 A); orphan template log+skip (RR-4 B); `_version` field decoded per instance.
9. `mindsos_instances/registry.py` — extend `attach_registry(mg)` to subscribe `after_load` observer (idempotent per Phase 06 P49 B helper). On observer fire, instantiate `InstanceLoader(client)` and call `load_into(mg)`.
10. `mindsos_instances/__init__.py` — does NOT re-export `InstanceLoader` (R4-13 B).
11. `mindsos_cli/commands/persistence.py` — extend with `sync --metagraph M [--replace]` (PB-8 A + RPB-4 C); `load --metagraph M [--to-json]` (PB-9 A + RR-7 A); drop Phase 07 P49 A refusal on `verify --source=db --metagraph M` (PB-7 A); add mutex enforcement `--graph G | --metagraph M` on `load` + `verify` (R4-6 A; exit 1 on combo); 9-line flat stdout summary per R4-5 A; `--json` opt-in.
12. `mindsos_cli/app.py` — help-text bump Phase 07 → Phase 08; mention metagraph round-trip (RR-14 A).
13. `mindsos_cli/manifest.toml` — `[mindsos] phase = "08"`; `version = "0.0.0+phase08"` (R4-15 A). 3-package version-string parity.
14. `mindsos_cli/__init__.py` + `mindsos_core/__init__.py` + `mindsos_instances/__init__.py` — `__version__` bumped.
15. `pyproject.toml` — version + description bumped.
16. `docker-compose.yml` — image tags `mindsos:phase08-prod` / `mindsos:phase08-test` (R4-16 A).
17. `Dockerfile` — comment lines bumped Phase 07 → Phase 08; verify `mindsos_instances/reconstruction/` lands in both prod + test stages (Phase 06 wildcard may already cover; explicit COPY if Step-0 audit shows gap).
18. `tests/_shared/metagraph_equality.py` — **NEW**. `assert_metagraphs_equal(mg1, mg2)` walker (RR-13 A).
19. `tests/_shared/large_graph_factory.py` — **NEW**. `make_large_graph_fixture(client, gid, n_nodes, *, edge_density)` builder (RR-13 A).
20. `tests/_shared/sentinel_paths.py` — ~15-20 additions (R4-14 A).
21. `tests/conftest.py` — register `pytest.mark.slow` marker (RPB-12 B+C).
22. `tests/phase_08/` — write tests per row §Automated tests as each module lands.
23. ADR-0124 file edit — frontmatter `status: Proposed` → `status: Accepted`; signature amendment per PB-3 A (drop `metagraph_id` from iter_load); impl-refs update per RR-6 A; acceptance criterion per PB-14 C.
24. `docs/usage/core/persistence.md` — amend per RR-15 A. New verbs + recipes + `RefreshUnsafeError` constraint + recover-on-load.
25. `docs/dev/internals/core.md` — NEW "Reconstruction layer" section with 5 subsections (RR-15 A).
26. `docs/api/core/loaders.md` — **NEW**. Full API reference per RR-15 A.
27. `docs/changelog/CHANGELOG.md` — Phase 08 entry appended.
28. `mkdocs.yml` — nav entry for `docs/api/core/loaders.md`.

### Hotfix expectations

Phase 06 surfaced 3 hotfixes; Phase 07 surfaced 4. Phase 08 likely surfaces similar patterns:

- **B-08-T-likely-1:** First test using `assert_metagraphs_equal` may fail with structural drift if the walker treats `IntergraphHyperEdge.ordered` lists vs sets inconsistently. Mirror Phase 05c canonicalize-before-comparison precedent.
- **B-08-T-likely-2:** `register_after_load_observer` not wired into doctor self-test parity check; may show as silent observer-not-firing on a misconfigured fixture. Verify subscription in `attach_registry` is idempotent across multiple loads.
- **B-08-T-likely-3:** Recover-on-load test may need fake replayer registered BEFORE `load_metagraph` call; test isolation gaps could yield false-positive "replayer not fired" assertions.
- **B-08-T-likely-4:** First `mindsos persistence sync --metagraph M --replace` against a metagraph with dependent state may bypass refusal if RPB-4 C check happens AFTER DETACH DELETE; verify check is BEFORE any destructive write.
- **B-08-T-likely-5:** `iter_load_graph` final-batch deferred-edges may miss hyperedges where one member is in batch N and another in batch N+2; verify cross-batch fidelity covers hyperedges too (RPB-1 A applies to hyperedges by symmetry).

These are anticipated; not pre-locked. Implementation chat handles per Phase 06/07 hotfix ledger pattern.

### Memory updates at chat-end (after tester confirmation)

Create `project_mindsos_phase_08_implemented.md` mirroring `project_mindsos_phase_07_implemented.md` structure. Update MEMORY.md index entry. If new feedback patterns surface (e.g., observer-fire-order gotchas, recover-on-load race conditions, mutex constraint UX), file as new `feedback_*.md` memory files. The 3 new Phase 07 feedback memories (`feedback_falkordb_index_ddl_quirks`, `feedback_cli_config_manifest_fallback`, `feedback_dockerfile_test_stage_file_reads`) carry forward unchanged.

## END PROMPT BODY (copy ends here)

---

## Notes for Henrique (NOT part of the prompt)

- Save this file before opening the new chat. Memory files load automatically when the new chat starts in the same project workspace.
- Reload cost in the next chat is 16 doc reads + 20 memory file reads. Bounded; expected to fit comfortably (the design log + row text are the largest single reads).
- Phase 09 follows 08. Open a separate chat for the 09 row-refinement when 08 ships. Phase 09's row addresses XRef CRUD + repository + loader + `ref:global` cutover migration. Phase 08's after_load observer pattern (RR-10 A) is the architectural slot XRefLoader fills.
- **First-time hit:** Phase 08 introduces the first `Metagraph.register_after_load_observer` consumer (`mindsos_instances.attach_registry`). Phase 09 will register a second consumer (XRefLoader). Verify observer-list ordering doesn't matter (per-observer exception isolation per RR-9 A; either order works).
- **ADR file edits:** Phase 08 flips 1 ADR Proposed → Accepted (ADR-0124, per M3 A inheriting Phase 07's precedent). ADR-0125 explicitly does NOT flip (PB-1 A; server-side). Subsequent phases follow Phase 07's "ADR file edits within consumer phase override Phase 06 P45 B" rule.
- **Mutex CLI constraint** (R4-6 A) — `--graph G | --metagraph M` mutex on `load` AND `verify` is the first time the persistence subapp uses Typer's mutex pattern. May need helper utility if the implementation surfaces verbosity; current row text leaves implementation detail to impl chat.
- **`MetagraphLoader.refresh` is the first L1 method that calls `mg.remove_graph(gid)` programmatically** (RPB-2 A). Verify the cascade-observer choreography is tested explicitly with element instances + composites + subgraph instances all attached pre-refresh.
- **Test budget uncapped** (RPB-7 user override 2026-05-13). Do as many tests as needed. Tester records actual count in `PHASE_08_CONFIRMED.md`; pre-existing `automated_test_summary` parser gap (Phase 07 hotfix B-07-T-summary) carries forward — canonical counts in tester_notes.
