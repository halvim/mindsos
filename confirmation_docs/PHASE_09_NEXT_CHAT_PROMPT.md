# Phase 09 Implementation — Next-Chat Handoff Prompt

> Authored 2026-05-14 at the close of the Phase 09 row-refinement chat (3 design rounds; row locked at `PHASE_MAP.md` §5 lines ~2716+; design log at `PHASE_09_DESIGN_LOG.md`). Paste the **PROMPT BODY** section below into a fresh Claude chat (in the MindsOS project) when ready to implement Phase 09.
>
> **Design philosophy of this prompt:** navigation guide, not content dump. Scope, locks, ADR amendments, CLI surfaces, validation orders — none of that is repeated here. The implementation chat reads the files listed below to recover that context.
>
> Design-side prompt preserved at `PHASE_09_DESIGN_CHAT_PROMPT.md` (renamed from this file's prior content).

---

## PROMPT BODY (copy from here)

Project: MindsOS (folder `halvim_mindsos/` under `Layered Intelligence`).

Your role: implement Phase 09 on a `phase-09` branch off `origin/main`. **Design is fully locked** in the prior chat (2026-05-14, 3 design rounds, 53 active picks: 19 meta-plan picks (M0-M18) + 9 Round-1 pushbacks (PB-1..9) + 8 Round-2 (RPB-1..8) + 18 Round-3 (RR-1..18); RR-2 superseded by RR-16). The full pick log + rationale per pick lives in `confirmation_docs/PHASE_09_DESIGN_LOG.md` — that is the canonical record of what was decided and why.

Do not re-litigate locked decisions. If implementation surfaces a contradiction with the locked row, surface it as a numbered pushback (P50+) before continuing — the bar is "I cannot implement what was locked," not "I'd have picked differently."

CASC-1 cascade: `05a → 05b → 05c → 05d → 06 → 07 → 08 → 09`. Phase 08 SHIPPED 2026-05-14 (tester-confirmed 1374 + 2 skipped in-container; tag `phase-08-confirmed` on main; PR #15 squash-merge at `d5b6e98`; post-tag hotfix `cc4d37f` B-08-T9 release.yml octal trap; Release CI green). You are unblocked.

**Branch:** `phase-09` off `origin/main` (NEVER off `phase-08`).
**Tag on confirm:** `phase-09-confirmed`.
**Confirmation doc target:** `confirmation_docs/PHASE_09_CONFIRMED.md`.
**Implementation log target:** `confirmation_docs/PHASE_09_IMPLEMENTATION_LOG.md`.

### What 09 ships

Read the canonical row text. Do not rely on a summary in this prompt; the row is the source of truth for scope, modules touched, CLI surface, tests, pass criterion, risks, and rollback hazards:

> **`confirmation_docs/PHASE_MAP.md` §5 Phase 09 row** (look for `### Phase 09 — L1 XRef (cross-metagraph refs)`).

The row has sub-sections for Locked decisions, Features in scope, Modules touched, Persistence layout impact, Automated tests, Confirmation command, Pass criterion, Risks, Rollback hazards, Doc sections, Breaking changes, and Final amendments. Read all of it.

### Mandatory reads (in this order; do NOT re-read older confirmation docs unless debugging a regression)

1. **`confirmation_docs/PHASE_09_DESIGN_LOG.md`** — full pick log (M0-M18 + PB-1..9 + RPB-1..8 + RR-1..18) with rationale per pick, Step 0 audit results, cross-chat dependencies. **Read this first.**
2. **`confirmation_docs/PHASE_MAP.md` §5 Phase 09 row** — canonical scope. The implementation target.
3. **`confirmation_docs/PHASE_MAP.md` §1** — settled cross-cutting decisions; per-phase workflow; supersession policy.
4. **`confirmation_docs/PHASE_MAP.md` §5 Phase 08 row** — prior-phase precedent. Phase 09 builds on Phase 08's `register_after_load_observer` (M18 inherits) + `_dispatch_after_load` per-observer isolation + `MetagraphLoader.load`/`refresh` `mg._persist_client` transient setting + `load --metagraph M` 9-line summary (extended to 10 per M17) + `_metagraph_has_dependent_state` defensive query (patched per M11).
5. **`confirmation_docs/PHASE_MAP.md` §5 Phase 07 row** — Phase 09 inherits: `Client` Protocol + `FalkorClient` + `WriteAheadLog` + `register_replayer` global API + bootstrap-with-indexes + 4 exception classes + `MetagraphRepository.persist` (M16 RR-17 extends).
6. **`confirmation_docs/PHASE_08_CONFIRMED.md` `tester_notes` + Hotfix ledger** — most recent tester confirmation; canonical 1374/2 baseline; B-08-T1..T9 ledger (esp. B-08-T1 dynamic-manifest-read pattern carry; B-08-T2 conftest.py re-export pattern; B-08-T9 release.yml octal trap permanent fix).
7. **`confirmation_docs/PHASE_07_CONFIRMED.md` `tester_notes`** — two-prior context per §0 read rule.
8. **`docs/decisions/adr/0128-hybrid-xref-cross-metagraph-refs.md`** — XRef primitive design (status: Proposed → flip to Accepted in 09 per M0; §Revisions section appended with 5 amendments per RR-9; chunk-N commit at project-root per RPB-8).
9. **`docs/decisions/adr/0142-xref-cutover-for-ref-global.md`** — XRef cutover (stays Proposed per M1; acceptance-criteria amended with 3-commitment partition L1/L2/Server; only L1 commitment ships in 09).
10. **`docs/decisions/adr/0130-property-bag-on-metagraph-graph.md`** — property bag (status: Proposed → flip to Accepted in 09 per M7; closes §7 Q4).
11. **`docs/decisions/adr/0034-core-never-validates-refs.md`** — Accepted; amended by 0128 §Validation for XRefs (write-time validation when target_metagraph resolvable). No edit in 09; 0128 §Revisions already declares the amendment.
12. **`docs/decisions/adr/0016-cross-graph-references-via-property-prefix.md`** — Accepted; ADR-0128 retains for intra-metagraph refs. Read for context.
13. **`docs/decisions/adr/0122-wal-graph-for-multi-statement-write-safety.md`** — WAL (Accepted Phase 07; Phase 09 = first phase to register actual replayers per M16 + RR-16).
14. **`docs/decisions/adr/0123-indexes-and-verify-integrity.md`** — indexes (Accepted Phase 07; Phase 09 adds 4 new `:XRef` indexes per M15).
15. **`docs/decisions/adr/0124-streaming-loader-iter-load-and-refresh.md`** — Accepted Phase 08. Phase 09 inherits the after-load observer mechanism; no edit.
16. **`docs/decisions/adr/0030-client-protocol-minimal-sync.md`** — Client Protocol (Accepted; Phase 09 doesn't change).

**v3 baseline source files (slim-port source material, NOT runtime code):**

17. **`/Layered Intelligence/mindsos_core/models/xref.py`** (v3 baseline; ~74 LoC) — XRef dataclass port source. Keep 10 fields including `target_stale` + `deprecated_at` inert (M3).
18. **`/Layered Intelligence/mindsos_core/persistence/xref_repository.py`** (v3; ~52 LoC) — `XRefRepository.persist` + `.remove` port source. WAL wrap added in halvim port per M16.
19. **`/Layered Intelligence/mindsos_core/persistence/xref_migration.py`** (v3; ~87 LoC) — `migrate_in_memory(mg, ...)` port source. Rename flag constant `server:xref_migrated_at` → `xref:migrated_at` per M9.
20. **`/Layered Intelligence/mindsos_core/reconstruction/xref_loader.py`** (v3; ~83 LoC) — `XRefLoader.load_into` port source. Add clear-first semantics per PB-9 + `attach_xref_loader(mg)` helper per M18.
21. **`/Layered Intelligence/mindsos_core/cypher/builders.py::build_create_xref`** (v3) — Cypher builder port source. Creates `:XRef` node + `:XREF_OF` edge to source Metagraph anchor.

### Mandatory memory consultations (your auto-memory directory; read in this order)

1. **`project_mindsos_phase_09_design.md`** — full lock state for 09 (mirror of `PHASE_09_DESIGN_LOG.md` in memory format). Primary reload pack. *Authored by the design chat; if absent in your memory, fall back to `PHASE_09_DESIGN_LOG.md` directly.*
2. **`project_mindsos_phase_08_implemented.md`** — what Phase 08 shipped + carry-forward patterns 09 inherits. Observer plumbing + 9-line summary + `_metagraph_has_dependent_state` defensive query + B-08-T1..T9 ledger.
3. **`project_mindsos_phase_07_implemented.md`** — Phase 07 substrate (Client + repositories + WAL + integrity + 14-index bootstrap + 5-verb CLI). Phase 09 grows the index count to 18 + adds 2 WAL replayer kinds.
4. **`project_mindsos_phase_06_implemented.md`** — Phase 06 observer plumbing (`register_remove_observer` + `register_graph_added_observer` + `attach_registry` idempotent helper). Phase 09 mirrors for `attach_xref_loader(mg)` per M18.
5. **`project_mindsos_l1_redesign.md`** — 11+6 redesign locks; M2 Hybrid XRef is the canonical L1 design lock; W1-W6 mitigation index; ADR status across the cascade (Phase 09 flips 0128 + 0130; 0142 stays Proposed).
6. **`reference_mindsos_four_edge_primitives.md`** — primitive distinction. XRef is a **5th primitive** (cross-metagraph; not in the 4-primitive table). Mind the distinction in vocab decisions.
7. **`reference_mindsos_layer_handoffs.md`** — per-layer handoff path index.
8. **`feedback_falkordb_index_ddl_quirks.md`** — Phase 07 substrate quirks. Phase 09 adds 4 `:XRef` indexes; CREATE INDEX FOR (no IF NOT EXISTS); `db.indexes()` groups multi-property indexes per label; substring-check test per B-07-T4 carry.
9. **`feedback_cli_config_manifest_fallback.md`** — env-then-manifest-then-default pattern. Phase 09 doesn't add new env vars but inherits the pattern.
10. **`feedback_dockerfile_test_stage_file_reads.md`** — 6-site checklist for any new host file a test reads. Phase 09's new `tests/_shared/cross_metagraph_fixture.py` is shared module; audit Dockerfile test stage COPY (existing wildcard `tests/_shared/` should cover).
11. **`feedback_new_top_level_package.md`** — 5-site checklist. Phase 09 does NOT add a new top-level package (XRef code is `mindsos_core` submodules). Confirm at Step 0.
12. **`feedback_confirm_phase_timeout.md`** — pre-build before `confirm-phase`. Phase 09 retains 900s timeout. Pre-build recipe required: `docker compose --profile test build mindsos-test` BEFORE `mindsos confirm-phase`.
13. **`feedback_state_dir_env_var.md`** — recipe-authoring rule (`~/.mindsos/`, never `$MINDSOS_STATE_DIR`).
14. **`feedback_release_workflow_ordering.md`** — squash-merge before tagging.
15. **`feedback_state_version_audit_scope.md`** — **Phase 09 bumps metagraph state-file v=3 → v=4 (M10)**. Grep ALL `tests/` for `_state_version == 3` + `METAGRAPH_STATE_VERSION == 3` literals. Audit at Step 0. B-05d-T1 + B-08-T1 patterns carry.
16. **`feedback_tag_regex_audit.md`** — 6-site checklist (B-08-T9 added octal-trap fix; Phase 09 `phase09-*` matches existing regex unchanged).
17. **`feedback_workflow_bash_octal_trap.md`** — release.yml `$((10#$NN_NUM))` permanent fix from B-08-T9. Phase 09 `NN=09` is octal-safe.
18. **`feedback_test_budget_unlimited.md`** — test budget rule (Phase 08 RPB-7 user override; uncapped).
19. **`feedback_terse_step_recipes.md`** — execution communication style.
20. **`feedback_docker_compose_invocation.md`** — Phase 02+ entrypoint behavior.
21. **`feedback_docs_source_of_truth.md`** — Model C hybrid; ADR file edits land at project-root, single chunk-N commit per RPB-8.
22. **`user_two_machine_setup.md`** — Mac/Linux split + canonical per-phase workflow steps (a)-(l).

### Carry-forward locks + out-of-scope items

Both lists live in the row (`PHASE_MAP.md` §5 Phase 09) and the design log (`PHASE_09_DESIGN_LOG.md`). Do NOT pull anything forward that isn't in the row's scope. If unsure whether a feature is in scope, the design log's pick log is authoritative.

**Explicitly OUT of Phase 09 scope:**

- Snapshot + soft-delete + RemovalImpact (Phase 10). Phase 09 ships `target_stale` + `deprecated_at` fields as inert per M3; setters land in Phase 10.
- Reverse-dangling XRef cleanup on Metagraph removal (Phase 10 work per RPB-3; forward-cascade via `:XREF_OF` is in scope).
- `persistence reset --force` (Phase 11).
- `xref-add` / `xref-remove` CLI verbs (M6 — `xref-list` read-only verb only).
- L2 `MetagraphView.follow_ref` read-fallback with `LegacyRefWarning` (Phase 14; ADR-0142 commitment 2).
- Server first-start migration hook (Phase 18+; ADR-0142 commitment 3).
- L3 write capacities producing XRefs (Phase 33+; ADR-0142 commitment 1; ADR-0145).
- `XRefIntegrityError` registry-hook injection (Phase 18+ Server registers resolver; M4 ships class + `target_metagraph` kwarg only).
- ADR-0142 status flip (M1 — stays Proposed until all 3 commitments shipped).
- ADR-0132 status flip (M8 — orthogonal; no opportunistic flip in 09).
- Per-role mutation-flag enforcement (`RefreshUnsafeError` class-only carry from Phase 08 PB-5 B).
- Cypher schema migration utility (Phase 11).
- Heavy stress-test variants beyond 1K-XRef opt-in slow tier (RPB-6).
- Memory-pressure-based budget tests (Phase 08 PB-12 C carry).
- L4 / L5 layer work.

### Communication style

Implementation chat uses execution voice per `feedback_terse_step_recipes.md`. Step recipes tagged `[Mac]` / `[Linux]`. Pushbacks (if any surface) in one block at end. Analysis voice ONLY if a row-text contradiction surfaces that genuinely cannot be implemented as locked — surface as numbered pushback (P50+) with options + your pick; wait for user response before continuing.

### Project instructions

Canonical per the project `CLAUDE.md`. Skeptical default; concise; no filler; no emojis; no restating user messages.

### First action

1. Read the 22 docs + 22 memory files above (in parallel where possible). **Read `confirmation_docs/PHASE_09_DESIGN_LOG.md` and the Phase 09 row first** — the rest is precedent and context.
2. **Step 0 pre-implementation audit pass:**
   - Verify Phase 08 squash-merge on main: `git log origin/main --oneline -3` includes `d5b6e98 Phase 08 — L1 Reconstruction (#15)` + `cc4d37f Phase 08 — B-08-T9: release.yml bash octal trap on NN=08`. Tag `phase-08-confirmed` exists.
   - Verify v3 baseline XRef sources exist at project-root (items 17-21 above). Confirm slim-port material available; LoC counts ~74 + ~52 + ~87 + ~83 + ~30 = ~326 LoC.
   - Verify halvim_mindsos `mindsos_core/models/xref.py` does NOT yet exist (Phase 09 introduces).
   - Verify halvim_mindsos `mindsos_core/persistence/xref_repository.py` + `xref_migration.py` do NOT yet exist (Phase 09 introduces).
   - Verify halvim_mindsos `mindsos_core/reconstruction/xref_loader.py` does NOT yet exist (Phase 09 introduces).
   - Verify halvim_mindsos `mindsos_core/cypher/builders.py` does NOT yet have `build_create_xref` function (grep `def build_create_xref` returns 0 matches in halvim).
   - Verify `mindsos_core/models/metagraph.py` does NOT yet have `add_xref` / `iter_xrefs` / `remove_xref` methods or `xrefs` / `_xrefs_by_source` / `_xrefs_by_target` instance fields (Phase 09 adds).
   - Verify `mindsos_core/exceptions.py` does NOT yet have `XRefIntegrityError` (Phase 09 adds).
   - Verify `mindsos_core/persistence/bootstrap.py` has 14 indexes today (Phase 09 grows to 18).
   - Verify `mindsos_core/persistence/wal.py::register_replayer` is module-level + `_REPLAYERS` dict is module-level singleton (Phase 07; Phase 09 registers `xref_add` + `xref_remove` via per-kind module ownership pattern per RR-16).
   - Verify `mindsos_core/persistence/metagraph_repository.py::MetagraphRepository.persist` exists; Phase 09 extends inline to iterate `mg.xrefs` per RR-17.
   - Verify `MetagraphLoader.refresh` sets `mg._persist_client = self._client` before firing `_dispatch_after_load` (line 324 of `metagraph_loader.py`); Phase 09's `attach_xref_loader` observer reads it at fire time.
   - Verify `mindsos_cli/commands/persistence.py:296` has defensive `:XRef {metagraph_id: $mid}` query under try/except; Phase 09 patches to `source_metagraph_id` per M11.
   - Verify `mindsos_cli/commands/persistence.py` `load --metagraph M` summary is 9 lines (`Metagraph`/`Metagraph id`/`Graphs`/`MetaEdges`/`MetaHyperEdges`/`IntergraphEdges`/`IntergraphHyperEdges`/`ElementInstances`/`CompositeInstances`); Phase 09 extends to 10 with `XRefs:` insertion per M17.
   - Verify ADR-0128 frontmatter `status: Proposed` (Phase 09 flips Accepted).
   - Verify ADR-0130 frontmatter `status: Proposed` (Phase 09 flips Accepted).
   - Verify ADR-0142 frontmatter `status: Proposed`, `layer: L2` (Phase 09 leaves status; amends acceptance-criteria with 3-commitment partition).
   - Verify ADR-0132 frontmatter `status: Proposed` (Phase 09 leaves unchanged per M8).
   - Verify `mindsos_cli/manifest.toml` has `[mindsos] phase = "08"` (Phase 09 bumps to "09").
   - Verify `mindsos_cli/migrations/metagraph.py::CURRENT_VERSION == 3` (Phase 09 bumps to 4 per M10 + RR-12).
   - **State-file v=3 → v=4 audit (per `feedback_state_version_audit_scope.md`):** Grep ALL `tests/` for `_state_version == 3` + `METAGRAPH_STATE_VERSION == 3` + `_state_version: 3` + `_state_version:.*3`. Report all hits; each becomes a dynamic-read patch site (mirror B-08-T1 + B-05d-T1 pattern).
   - Verify `mindsos_core/_observers.py::_dispatch_after_load` exists per Phase 08 RR-9 A (Phase 09 doesn't change; XRefLoader fires through this dispatcher).
   - Verify `Metagraph.register_after_load_observer` exists at `mindsos_core/models/metagraph.py:420` (Phase 09 subscribes via `attach_xref_loader`).
   - Verify `Metagraph.properties: Dict[str, Any]` exists at `metagraph.py:307` (Phase 09's migration reads + writes `mg.properties["xref:migrated_at"]` flag; M7 flips ADR-0130 Accepted).
   - Verify `tests/_shared/metagraph_equality.py::assert_metagraphs_equal` exists per Phase 08 RR-13 A (Phase 09 extends per PB-3 + RR-4).
   - Verify `tests/_shared/falkordb_fixture.py::falkor_client` exists per Phase 07 P55 A (Phase 09 `tests/phase_09/conftest.py` re-exports per RR-11).
   - Verify FalkorDB v4.18.3 substrate quirks still apply (B-07-T1 + B-07-T4): bare `CREATE INDEX FOR` syntax; `db.indexes()` per-label grouping; substring-check test pattern.
3. Report findings as a brief audit summary (file + line citations + any anomalies). Do NOT write any new code yet.
4. Wait for user sign-off before proceeding to Step 1.

### Workflow after Step 0 sign-off

The full per-phase workflow (steps a-l: branch, implement, test, recipe, confirm, tag, release) lives in `user_two_machine_setup.md`. Follow it verbatim. Three operational reminders to surface explicitly:

- **`feedback_state_dir_env_var.md`** — when authoring `notes-phase-09.md` tester recipes, use `~/.mindsos/<kind>-<name>.json` literally; NEVER `$MINDSOS_STATE_DIR/...`. Hit twice in 05b/05c.
- **`feedback_release_workflow_ordering.md`** — squash-merge MUST land before tagging from main. PR → `gh pr merge --squash --delete-branch` → pull main → verify `confirmation_docs/PHASE_09_CONFIRMED.md` exists → re-tag → push.
- **`feedback_confirm_phase_timeout.md`** — timeout already at 900s. Pre-build recipe required: `docker compose --profile test build mindsos-test` BEFORE `mindsos confirm-phase`.

### Implementation order recommendation (not locked; pick at impl time)

Suggested dependency-flow order:

1. `mindsos_core/exceptions.py` — add `XRefIntegrityError(PersistenceError)` per RR-3.
2. `mindsos_core/models/xref.py` — **NEW**. Slim port from v3 (`/Layered Intelligence/mindsos_core/models/xref.py`). Dataclass with 10 fields including `target_stale` + `deprecated_at` inert (M3).
3. `mindsos_core/models/metagraph.py` — **MODIFY**. Add `xrefs: Dict[str, XRef]` + `_xrefs_by_source` + `_xrefs_by_target` instance fields in `__init__`. Add `add_xref(*, source_id, target_metagraph_id, target_role, target_id, ref_type, properties=None, target_metagraph=None)` method (M4 validation when `target_metagraph` passed). Add `iter_xrefs(*, source_id=None, target_metagraph_id=None, target_id=None, ref_type=None)` AND-composed filter (PB-2). Add `remove_xref(xref_id)`.
4. `mindsos_core/cypher/builders.py` — **MODIFY**. Add `build_create_xref(...)` per v3 baseline (MERGE `:XRef` + MERGE `:XREF_OF` to source Metagraph anchor per M2).
5. `mindsos_core/persistence/xref_repository.py` — **NEW**. Slim port. `XRefRepository.persist(xref)` + `.remove(xref_id)` with WAL wrap per M16 (`with wal.entry(kind="xref_add", payload=<10-field dict>) as op_id: ...`). Add `register_xref_replayers(client)` per RR-16: registers `xref_add` (MERGE-based) + `xref_remove` (DETACH DELETE) replayers via `mindsos_core.persistence.wal.register_replayer(kind, callback)`. Replayer bodies capture `client` via closure.
6. `mindsos_core/persistence/xref_migration.py` — **NEW**. Slim port from v3. Rename flag constant `server:xref_migrated_at` → `xref:migrated_at` per M9. `migrate_in_memory(mg, *, target_metagraph_id, default_ref_type="SPECIALISES") -> int`. Idempotent via `mg.properties["xref:migrated_at"]` flag. Per-XRef `already` skip via `mg.iter_xrefs(source_id=node.node_id)` content-tuple check. Uses `mg.add_xref` (each call WAL-wrapped per M16 + RPB-2).
7. `mindsos_core/persistence/bootstrap.py` — **MODIFY**. Add 4 new `:XRef` indexes per M15: `(id)`, `(source_metagraph_id)`, `(source_id)`, `(target_metagraph_id, target_id)` compound. Bare `CREATE INDEX FOR (n:XRef) ON (n.<prop>)` syntax (B-07-T1 carry). Add `register_all_l1_replayers(client)` wrapper per RR-16: calls `register_xref_replayers(client)`. `FalkorClient.__init__` calls `bootstrap(self) + register_all_l1_replayers(self)`.
8. `mindsos_core/persistence/metagraph_repository.py` — **MODIFY**. `MetagraphRepository.persist(mg)` extends inline-iteration per RR-17: after anchor + dependent state, `for xref in mg.xrefs.values(): XRefRepository(self._client).persist(xref)`.
9. `mindsos_core/reconstruction/xref_loader.py` — **NEW**. Slim port. `XRefLoader.load_into(mg)` clears `mg.xrefs` + `_xrefs_by_source` + `_xrefs_by_target` + unregisters XRef IDs from `mg.identity` BEFORE re-populating per PB-9. Query: `MATCH (x:XRef {source_metagraph_id: $mid}) RETURN x.id AS id, ...`. Add `attach_xref_loader(mg)` helper per M18: subscribes after-load observer via `mg.register_after_load_observer(callback)`; observer reads `mg._persist_client` at fire time + instantiates `XRefLoader(client) + load_into(mg)`. Idempotent re-attach.
10. `mindsos_core/reconstruction/__init__.py` — export `XRefLoader` + `attach_xref_loader`.
11. `mindsos_core/__init__.py` — `__version__ = "0.0.0+phase09"`.
12. `mindsos_cli/commands/persistence.py` — **MODIFY**. Add `xref-list` verb per PB-5 + RR-5: `--metagraph M [--source-id SID] [--target-metagraph TMID] [--target-id TID] [--ref-type RT] [--json]`. Rich table default + `--json` opt-in per RR-6 (columns: truncated IDs + ref_type + inert fields when set). Exit codes 0/1/2 per Phase 07 P64 A. **Patch `_metagraph_has_dependent_state` query** per M11: change `:XRef {metagraph_id: $mid}` to `:XRef {source_metagraph_id: $mid}` (keep try/except for label-not-found pre-P09). **Extend `load --metagraph M` summary to 10 lines** per M17: insert `XRefs: <N>` between `IntergraphHyperEdges` and `ElementInstances`. Phase 08 tests asserting literal 9-line shape patched dynamically (mirror B-08-T1 pattern).
13. `mindsos_cli/migrations/metagraph.py` — **MODIFY** per RR-12. Add `_v3_to_v4(state)` function: `state["xrefs"] = state.get("xrefs") or []; return state`. Append to `MIGRATIONS` list. Bump `CURRENT_VERSION = 4`. State-file deserializer in sync path: read `xrefs[]`; construct `XRef` objects from 10-field dicts (M9 + RR-8); assign to `mg.xrefs` directly + manually rebuild `mg._xrefs_by_source` + `mg._xrefs_by_target` per RR-18. Bypass `mg.add_xref` (no DB write at deserialization time).
14. `mindsos_cli/manifest.toml` — `[mindsos] phase = "09"`; `version = "0.0.0+phase09"`. 3-package version-string parity.
15. `mindsos_cli/__init__.py` + `mindsos_instances/__init__.py` — `__version__ = "0.0.0+phase09"`.
16. `pyproject.toml` — version + description bumped.
17. `docker-compose.yml` — image tags `mindsos:phase09-prod` / `mindsos:phase09-test`.
18. `Dockerfile` — comment lines bumped Phase 08 → Phase 09. Existing wildcard `COPY mindsos_core/` covers new submodule files; verify at Step 0.
19. `tests/_shared/metagraph_equality.py` — **MODIFY**. Extend `assert_metagraphs_equal` for XRef id-set + field-by-field on matched IDs per PB-3 + RR-4. Add sibling `assert_xref_contents_equal(xrefs1, xrefs2)` for content-tuple comparison (migration tests).
20. `tests/_shared/cross_metagraph_fixture.py` — **NEW** per RR-13. `make_source_and_target_metagraphs() -> tuple[Metagraph, Metagraph]` function-scoped helper.
21. `tests/_shared/sentinel_paths.py` — add 4 entries per RR-10: 4 new XRef files.
22. `tests/phase_09/conftest.py` — **NEW** per RR-11. Re-export `falkor_client` from `tests._shared.falkordb_fixture` (B-08-T2 pattern).
23. `tests/phase_09/` — write ~25-38 test files per row §Automated tests as each module lands. Use `clear_replayers()` between WAL tests per RR-16 (Phase 07 precedent).
24. **State-file v=3 → v=4 audit cleanup** per RR-12 + `feedback_state_version_audit_scope.md`: patch all `tests/` files surfaced at Step 0 audit (replace `METAGRAPH_STATE_VERSION == 3` literals with dynamic `metagraph_migrations.CURRENT_VERSION` reads).
25. **ADR file edits** (project-root chunk-N commit per RPB-8): flip ADR-0128 Proposed → Accepted + append §Revisions section with 5 amendments dated 2026-05-14 per RR-9; flip ADR-0130 Proposed → Accepted (closes §7 Q4); amend ADR-0142 §Decision / acceptance-criteria with 3-commitment partition note (L1 done in 09; L2 P14; Server P18+). One commit at `/Layered Intelligence/docs/decisions/adr/`.
26. `docs/concepts/references.md` — **REWRITE** per M14. Hybrid model documentation: intra-metagraph `ref:<role>` strings (ADR-0016 retained); cross-metagraph `:XRef` rows + indexed lookup; legacy `ref:global_*` deprecation + migration recipe.
27. `docs/api/core/xref.md` — **NEW**. Full API reference: `XRef` dataclass + Metagraph methods + Repository + Loader + `attach_xref_loader` + `migrate_in_memory` + `XRefIntegrityError`.
28. `docs/dev/internals/core.md` — **AMEND**. NEW "XRef" section under reconstruction. Cross-reference ADRs 0128/0130/0142. Observer subscription pattern; WAL replayer registration via per-kind module ownership.
29. `docs/changelog/CHANGELOG.md` — Phase 09 entry appended.
30. `mkdocs.yml` — nav entry for `docs/api/core/xref.md`.

### Hotfix expectations

Phase 06 surfaced 3 hotfixes; Phase 07 surfaced 4; Phase 08 surfaced 9. Phase 09 likely surfaces similar patterns:

- **B-09-T-likely-1:** State-file v=3 → v=4 audit miss. A Phase 02-08 test asserting `METAGRAPH_STATE_VERSION == 3` or `_state_version == 3` literal that the Step 0 grep didn't catch (typo, comment-only mention, indirect literal). Mirror B-05d-T1 + B-08-T1 dynamic-read patch.
- **B-09-T-likely-2:** `register_replayer` global state pollution between tests. A test that registers a fake replayer but doesn't `clear_replayers()` in teardown leaks into the next test. Add `clear_replayers()` to relevant fixtures.
- **B-09-T-likely-3:** WAL replay test ordering bug. `xref_add` + `xref_remove` sequence under recovery should be FIFO per RPB-1; if a test mocks `created_at` non-monotonically, replay order inverts.
- **B-09-T-likely-4:** `:XRef` index DDL syntax — FalkorDB v4.18.3 may reject the compound `(target_metagraph_id, target_id)` index syntax differently than expected. Re-probe per `feedback_falkordb_index_ddl_quirks.md`.
- **B-09-T-likely-5:** `xref-list --json` output shape regression. Rich-table-vs-JSON divergence (RR-6) may show field-order drift on the JSON side; test should assert key set + value types, not literal byte equality.
- **B-09-T-likely-6:** Cross-metagraph fixture cleanup. Two `:Metagraph` anchors per integration test → if function-scoped fixture leaks DB state between tests, results contaminate. Verify `falkor_client` fixture clears all `:Metagraph` rows on teardown.
- **B-09-T-likely-7:** Migration idempotency edge case. `mg.properties["xref:migrated_at"]` set at migration end; if migration crashes mid-loop, flag not set but partial XRefs exist. Re-run uses per-XRef `already` check to skip; verify on partial-crash fixture.
- **B-09-T-likely-8:** `MetagraphRepository.persist` redundancy detection. If `mg.xrefs` already in DB from programmatic adds, `persist` re-MERGEs them. MERGE idempotent so no data corruption, but test asserting "N writes" may double-count.
- **B-09-T-likely-9:** XRefLoader observer-fire on `attach_xref_loader` twice → duplicate subscriptions if idempotency not enforced. Verify Phase 06 P49 B idempotent-helper pattern carries.

These are anticipated; not pre-locked. Implementation chat handles per Phase 06/07/08 hotfix ledger pattern.

### Memory updates at chat-end (after tester confirmation)

Create `project_mindsos_phase_09_implemented.md` mirroring `project_mindsos_phase_08_implemented.md` structure. Update MEMORY.md index entry. If new feedback patterns surface (e.g., WAL replayer global-state-pollution recipes, FalkorDB compound-index quirks, cross-metagraph fixture teardown patterns), file as new `feedback_*.md` memory files. The Phase 07/08 feedback memories (`feedback_falkordb_index_ddl_quirks` / `feedback_cli_config_manifest_fallback` / `feedback_dockerfile_test_stage_file_reads` / `feedback_workflow_bash_octal_trap` / `feedback_state_version_audit_scope`) carry forward unchanged.

## END PROMPT BODY (copy ends here)

---

## Notes for Henrique (NOT part of the prompt)

- Save this file before opening the new chat. Memory files load automatically when the new chat starts in the same project workspace.
- Reload cost in the next chat is 22 doc reads + 22 memory file reads. Bounded; expected to fit comfortably (the design log + row text are the largest single reads).
- Phase 10 follows 09. Open a separate chat for the 10 row-refinement when 09 ships. Phase 10's row addresses snapshot + soft-delete + RemovalImpact. Phase 09's `target_stale` + `deprecated_at` inert fields (M3) are the forward-compat slots Phase 10's setters fill.
- **First-time hit:** Phase 09 introduces the first WAL replayer registration (Phase 08 shipped `recover()` as silent no-op; M16 + RR-16 register actual `xref_add` + `xref_remove` replayers). Tests for WAL recovery now test real replay behavior, not no-op behavior.
- **ADR file edits:** Phase 09 flips 2 ADRs Proposed → Accepted (ADR-0128 + ADR-0130 per M0 + M7) inheriting Phase 07/08 chunk-N project-root commit pattern. ADR-0142 stays Proposed (M1; only 1 of 3 commitments shipped).
- **State-file v=4 audit cost** — RR-12 grep across ALL `tests/` is mandatory; B-05d-T1 + B-08-T1 patterns prove the cost of missing this audit (CI failure on Phase 04 hard-coded literals).
- **Slim-port + 4 deltas** — Phase 09 is NOT a pure slim port. Deltas: M3 inert-fields kept; M4 target_metagraph kwarg + XRefIntegrityError; M9 flag rename; M11 Phase 08 dependent-state patch; M16 WAL wrap; M17 summary extension; PB-9 clear-first XRefLoader; RR-16 per-kind replayer pattern; RR-17 MetagraphRepository extension. Each delta is justified in the design log and traces back to a specific ADR commitment or substrate constraint.
- **Test budget uncapped** (RPB-7 user override 2026-05-13 inherited). Do as many tests as needed. Tester records actual count in `PHASE_09_CONFIRMED.md`; pre-existing `automated_test_summary` parser gap carries forward — canonical counts in tester_notes.
