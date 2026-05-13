# Phase 07 Implementation — Next-Chat Handoff Prompt

> Authored 2026-05-12 at the close of the Phase 07 row-refinement chat (3 design rounds + 4 meta-pick passes; row locked at `PHASE_MAP.md` §5; design log at `PHASE_07_DESIGN_LOG.md`). Paste the **PROMPT BODY** section below into a fresh Claude chat (in the MindsOS project) when ready to implement Phase 07.
>
> **Design philosophy of this prompt:** navigation guide, not content dump. Scope, locks, ADR amendments, validation orders, CLI surfaces, persistence layouts, future-work entries — none of that is repeated here. The implementation chat reads the files listed below to recover that context. If you find yourself wanting a fact that isn't in this prompt, the answer is in one of the listed files.

---

## PROMPT BODY (copy from here)

Project: MindsOS (folder `halvim_mindsos/` under `Layered Intelligence`).

Your role: implement Phase 07 on a `phase-07` branch off `origin/main`. **Design is fully locked** in the prior chat (2026-05-12, 3 design rounds + 4 meta-pick passes, 16 meta-plan picks (M0-M15 + P16-pre) + 25 numbered design pushbacks (P1-P25), 0 user overrides at lock time. 1 user instruction overrode Phase 06 P45 B precedent for ADR file edits in 07). The full pick log + rationale per pick lives in `confirmation_docs/PHASE_07_DESIGN_LOG.md` — that is the canonical record of what was decided and why.

Do not re-litigate locked decisions. If implementation surfaces a contradiction with the locked row, surface it as a numbered pushback (continuing P26+) before continuing — the bar is "I cannot implement what was locked," not "I'd have picked differently."

CASC-1 cascade: `05a → 05b → 05c → 05d → 06 → 07`. Phase 06 SHIPPED 2026-05-11 (tester-confirmed 1127 + 2 skipped in-container; tag `phase-06-confirmed` on main; PR #12 squash-merge; Release CI green). You are unblocked.

**Branch:** `phase-07` off `origin/main` (NEVER off `phase-06`).
**Tag on confirm:** `phase-07-confirmed`.
**Confirmation doc target:** `confirmation_docs/PHASE_07_CONFIRMED.md`.
**Implementation log target:** `confirmation_docs/PHASE_07_IMPLEMENTATION_LOG.md`.

### What 07 ships

Read the canonical row text. Do not rely on a summary in this prompt; the row is the source of truth for scope, modules touched, persistence layout, CLI surface, tests, pass criterion, risks, and rollback hazards:

> **`confirmation_docs/PHASE_MAP.md` §5 Phase 07 row** (look for `### Phase 07 — L1 Persistence`).

The row has sub-sections for Locked decisions, Features in scope, Modules touched, Persistence layout, Automated tests, Confirmation command, Pass criterion, Risks, Rollback hazards, Doc sections, Breaking changes, and Final amendments. Read all of it.

### Mandatory reads (in this order; do NOT re-read older confirmation docs unless debugging a regression)

1. **`confirmation_docs/PHASE_07_DESIGN_LOG.md`** — full pick log (M0-M15 + P16-pre + P1-P25) with rationale per pick, factual corrections to the prior prompt's premises, convergence note. **Read this first** if you need to understand *why* a decision was made.
2. **`confirmation_docs/PHASE_MAP.md` §5 Phase 07 row** — canonical scope. The implementation target.
3. **`confirmation_docs/PHASE_MAP.md` §1** — settled cross-cutting decisions; per-phase workflow; supersession policy.
4. **`confirmation_docs/PHASE_MAP.md` §5 Phase 06 row** — prior-phase precedent. Phase 07 inherits: `register_remove_observer` plumbing pattern (mirror for `register_persist_observer`); `attach_registry(mg)` idempotent helper (extends to subscribe persist observer); Core/instances boundary (P49 B).
5. **`confirmation_docs/PHASE_MAP.md` §5 Phase 04 / Phase 04-v2 rows** — `_version` field deferral note + `update_*_properties` precedent (no `_version` bump until Phase 07).
6. **`confirmation_docs/PHASE_06_CONFIRMED.md` `tester_notes` + Hotfix ledger** — most recent tester confirmation; canonical 1127/2 baseline; B-06-T1/T2/T3 patterns; recipe-deviation lessons 07 inherits.
7. **`confirmation_docs/PHASE_05d_CONFIRMED.md` `tester_notes`** — two-prior context per §0 read rule.
8. **`docs/decisions/adr/0030-client-protocol-minimal-sync.md`** — Client Protocol contract (stays Accepted; no flip).
9. **`docs/decisions/adr/0121-substrate-falkordb-for-graphs-sqlite-for-non-graph.md`** — substrate commitment (umbrella ADR; W1-W6 mitigation index).
10. **`docs/decisions/adr/0122-wal-graph-for-multi-statement-write-safety.md`** — WAL design (status: Proposed → flip to Accepted in 07 per M3 A).
11. **`docs/decisions/adr/0123-indexes-and-verify-integrity.md`** — 15-index + 5-bucket scanner design (Proposed → Accepted).
12. **`docs/decisions/adr/0126-async-client-via-thread-pool-wrapper.md`** — AsyncClient design (Proposed → Accepted).
13. **`docs/decisions/adr/0127-optimistic-concurrency-on-global-writes.md`** — OCC design (Proposed → Accepted; policy stays L0/L2).

**v3 baseline source files (slim-port source material, NOT runtime code):**

14. **`/Users/henriquealvim/Documents/Claude/Projects/Layered Intelligence/mindsos_core/persistence/`** (project-root v3 baseline) — Client / FalkorClient / InMemoryClient / AsyncClient / bootstrap / GraphRepository / MetagraphRepository / WAL / integrity. Port source.
15. **`/Users/henriquealvim/Documents/Claude/Projects/Layered Intelligence/mindsos_core/reconstruction/graph_loader.py`** (v3 baseline) — port source for M14 single-Graph load.
16. **`/Users/henriquealvim/Documents/Claude/Projects/Layered Intelligence/mindsos_core/cypher/builders.py`** (v3 baseline) — port source for round-3 P15 cypher builders module.
17. **`/Users/henriquealvim/Documents/Claude/Projects/Layered Intelligence/mindsos_instances/persistence/instance_repository.py`** (v3 baseline) — port source for P11 A sibling-package InstanceRepository.

### Mandatory memory consultations (your auto-memory directory; read in this order)

1. **`project_mindsos_phase_07_design.md`** — full lock state for 07 (mirror of `PHASE_07_DESIGN_LOG.md` in memory format). Primary reload pack.
2. **`project_mindsos_phase_06_implemented.md`** — what Phase 06 shipped + carry-forward patterns 07 inherits. Observer plumbing reference.
3. **`project_mindsos_l1_redesign.md`** — 11+6 redesign locks; W1-W6 mitigation index; ADR status across the cascade.
4. **`reference_mindsos_four_edge_primitives.md`** — primitive distinction (load-bearing for persisting all 4 edge primitives + `_version` on each).
5. **`feedback_new_top_level_package.md`** — 5-site checklist. Phase 07 does NOT add a new top-level package (`mindsos_instances/persistence` is a sub-package). Audit sentinel-paths + Dockerfile + pyproject + doctor + host-install regardless.
6. **`feedback_confirm_phase_timeout.md`** — pre-build before `confirm-phase`. Phase 06 ran 578s; Phase 07 + integration tests projects 700-900s; M12 bumps timeout to 900s in 07.
7. **`feedback_state_dir_env_var.md`** — recipe-authoring rule (`~/.mindsos/`, never `$MINDSOS_STATE_DIR`).
8. **`feedback_release_workflow_ordering.md`** — squash-merge before tagging.
9. **`feedback_state_version_audit_scope.md`** — Phase 07 does NOT bump state files (M0 B); audit confirms absence rather than rebases literals.
10. **`feedback_tag_regex_audit.md`** — 5-site checklist (probably not triggered in 07; image tag `phase07-prod` matches existing regex; read so you know it exists).
11. **`feedback_test_budget_unlimited.md`** — test budget rule.
12. **`feedback_terse_step_recipes.md`** — execution communication style.
13. **`feedback_docker_compose_invocation.md`** — Phase 02+ entrypoint behavior; rebuild image after pulling test-side fixes; `mindsos-test` profile already has FalkorDB sidecar reachable.
14. **`feedback_docs_source_of_truth.md`** — Model C hybrid docs precedent.
15. **`user_two_machine_setup.md`** — Mac/Linux split + canonical per-phase workflow steps (a)-(l).
16. **`reference_mindsos_layer_handoffs.md`** — per-layer handoff path index.

### Carry-forward locks + out-of-scope items

Both lists live in the row (`PHASE_MAP.md` §5 Phase 07) and the design log (`PHASE_07_DESIGN_LOG.md`). Do NOT pull anything forward that isn't in the row's scope. If unsure whether a feature is in scope, the design log's pick log is authoritative.

**Explicitly OUT of Phase 07 scope:**
- Metagraph `load` (Phase 08 ships metagraph_loader + streaming + refresh per ADR-0124).
- Metagraph `sync` (per P12 D; symmetric with above).
- Soft-delete read-path filter (Phase 10 per P16-pre).
- `persistence reset --force` (Phase 11; richer integrity scanner verifies before wipe).
- Graph `.properties` writer (PHASE_MAP §7 Q4 deferral; P9 C).
- XRef CRUD (Phase 09).
- Cypher schema migration (Phase 11).
- Global/Local OCC policy enforcement (L2/L0 territory; M7).
- ADR semantic edits beyond status flips (Phase 38; M3 A scope limit).

### Communication style

Implementation chat uses execution voice per `feedback_terse_step_recipes.md`. Step recipes tagged `[Mac]` / `[Linux]`. Pushbacks (if any surface) in one block at end. Analysis voice ONLY if a row-text contradiction surfaces that genuinely cannot be implemented as locked — surface as numbered pushback (P26+) with options + your pick; wait for user response before continuing.

### Project instructions

Canonical per the project `CLAUDE.md`. Skeptical default; concise; no filler; no emojis; no restating user messages.

### First action

1. Read the 13 docs + 16 memory files above (in parallel where possible). **Read `confirmation_docs/PHASE_07_DESIGN_LOG.md` and the Phase 07 row first** — the rest is precedent and context.
2. **Step 0 pre-implementation audit pass:**
   - Verify v3 baseline persistence modules exist at the project-root paths cited above (items 14-17). Confirm slim-port source material is available.
   - Verify `mindsos_core/models/node.py` has `_version: int = 1` field (Phase 04 deferral; expected to already be present).
   - Verify halvim_mindsos `mindsos_core/persistence/` directory does NOT yet exist (confirms net-new slim port).
   - Verify halvim_mindsos `mindsos_instances/persistence/` directory does NOT yet exist (confirms sibling-package new subpackage).
   - Verify `mindsos_cli/manifest.toml` has no `[falkordb]` section yet (Phase 07 adds).
   - Verify `requirements.in` does NOT contain `falkordb` (Phase 07 adds + relock).
   - Verify Compose `mindsos-test` profile has FalkorDB sidecar reachable (Phase 00 shipped; Phase 07 reuses).
   - Verify `docs/dev/internals/core.md` exists and is target for new "Persistence layer" section (P24 B).
   - Review every `tests/phase_*/test_state*.py` for accidental state-file dependencies; no Phase 07 bump means audit confirms absence (per `feedback_state_version_audit_scope.md`).
3. Report findings as a brief audit summary (file + line citations + any anomalies). Do NOT write any new code yet.
4. Wait for user sign-off before proceeding to Step 1.

### Workflow after Step 0 sign-off

The full per-phase workflow (steps a-l: branch, implement, test, recipe, confirm, tag, release) lives in `user_two_machine_setup.md`. Follow it verbatim. Three operational reminders to surface explicitly:

- **`feedback_state_dir_env_var.md`** — when authoring `notes-phase-07.md` tester recipes, use `~/.mindsos/<kind>-<name>.json` literally; NEVER `$MINDSOS_STATE_DIR/...`. Hit twice (05b + 05c).
- **`feedback_release_workflow_ordering.md`** — squash-merge MUST land before tagging from main. PR → `gh pr merge --squash --delete-branch` → pull main → verify `confirmation_docs/PHASE_07_CONFIRMED.md` exists → re-tag → push.
- **`feedback_confirm_phase_timeout.md`** — Phase 07 bumps the timeout itself (M12). **Verify `_CONFIRM_PHASE_TIMEOUT_SECONDS == 900` lands BEFORE `confirm-phase` runs** (chicken-and-egg: the timeout bump must ship as code before the verification run consumes it).

### Implementation order recommendation (not locked; pick at impl time)

The row leaves implementation order to the chat per PHASE_MAP §2 schema. Suggested dependency-flow order:

1. `mindsos_core/cypher/builders.py` slim port (no deps; needed by repositories).
2. `mindsos_core/exceptions.py` — add 5 new exceptions (P21 A).
3. `mindsos_core/persistence/client.py` (Protocol + InMemoryClient first; FalkorClient lazy import).
4. `mindsos_core/persistence/bootstrap.py` + `DEFAULT_INDEXES` (consumed by FalkorClient init).
5. `mindsos_core/config.py` (FalkorConfig).
6. `mindsos_core/persistence/async_client.py` (independent ~50 LOC).
7. `mindsos_core/persistence/integrity.py` (5-bucket scanner; consumes Metagraph; Client-independent).
8. `mindsos_core/models/{edge,hyperedge,metaedge,metahyperedge,intergraph_edge,intergraph_hyperedge}.py` — add `_version: int = 1` field (P10 A).
9. `mindsos_core/models/metagraph.py` — add `register_persist_observer` + `_persist_observers`.
10. `mindsos_core/persistence/graph_repository.py` (consumes builders + Client + exceptions).
11. `mindsos_core/persistence/metagraph_repository.py` (consumes GraphRepository + observer hook; strips v3's direct InstanceRepository call).
12. `mindsos_core/persistence/wal.py` (consumes Client).
13. `mindsos_core/reconstruction/graph_loader.py` (consumes Client + Graph model).
14. `mindsos_instances/models/{element_instance,composite_instance}.py` — add `_version: int = 1` field (P11 A).
15. `mindsos_instances/persistence/instance_repository.py` (consumes Client + instance models).
16. `mindsos_instances/registry.py` (or `__init__.py`) — extend `attach_registry(mg)` to register `after_persist` observer.
17. `mindsos_cli/commands/persistence.py` — 5-verb subapp.
18. `mindsos_cli/commands/doctor.py` — extend `--self-test` with `[falkordb]` ping.
19. `mindsos_cli/commands/confirm_phase.py` — bump timeout 600 → 900.
20. `mindsos_cli/manifest.toml` — add `[falkordb]` section; bump phase + version.
21. `requirements.in` — add `falkordb`; run `tools/lock.sh` once on Linux host.
22. `tests/phase_07/` — write tests as each module lands.
23. `tests/_shared/{falkordb_fixture,graph_equality,raises_on_nth_call}.py` — fixtures.
24. `tests/_shared/sentinel_paths.py` — 14 additions (P25 A).
25. `docs/usage/core/persistence.md` + `docs/dev/internals/core.md` + 4 API pages — write per row §Doc sections.
26. ADR status flips: edit ADRs 0122 / 0123 / 0126 / 0127 frontmatter `status: Proposed` → `status: Accepted` (M3 A inline file edit).

### Hotfix expectations

Phase 06 surfaced 3 hotfixes during tester run (B-06-T1: Dockerfile + sentinel; B-06-T2: CLI fixture flags; B-06-T3: exit-code wrapper). Phase 07 likely surfaces similar patterns:

- **B-07-T-likely-1:** `_CONFIRM_PHASE_TIMEOUT_SECONDS = 900` ships in code, but CI invocation may use bundled binary's prior value. Verify bump landed before relying on it.
- **B-07-T-likely-2:** `[falkordb]` manifest section may surface doctor self-test mismatch if Compose env vars aren't all present. Verify each env var Compose sets is consumed.
- **B-07-T-likely-3:** First `falkordb` package install requires `tools/lock.sh` regen of `requirements.txt` with hashes; manifest `requirements_txt_sha256` mismatch fails doctor self-test until tester reruns lock.
- **B-07-T-likely-4:** `pytest.mark.integration` marker not registered in `conftest.py` → unknown-mark warning. Ship registration in `tests/conftest.py`.

These are anticipated; not pre-locked. Implementation chat handles per Phase 06 hotfix ledger pattern.

### Memory updates at chat-end (after tester confirmation)

Create `project_mindsos_phase_07_implemented.md` mirroring `project_mindsos_phase_06_implemented.md` structure. Update MEMORY.md index entry. If new feedback patterns surface (e.g., FalkorDB-side rollback gotchas, integration-test marker recipes, manifest extension footgun), file as new `feedback_*.md` memory files.

## END PROMPT BODY (copy ends here)

---

## Notes for Henrique (NOT part of the prompt)

- Save this file before opening the new chat. Memory files load automatically when the new chat starts in the same project workspace.
- Reload cost in the next chat is 13 doc reads + 16 memory file reads. Bounded; expected to fit comfortably (the design log + row text are the largest single reads; both are bounded).
- Phase 08 follows 07. Open a separate chat for the 08 row-refinement when 07 ships. Phase 08's row addresses metagraph_loader + streaming (ADR-0124) + refresh + lazy local hydration (ADR-0125 consumer reaches L1).
- **First-time hit:** Phase 07 is the first phase to require a live FalkorDB connection from the test suite. Tester should verify `docker compose --profile test up -d falkordb` reaches healthy BEFORE the in-container pytest run; otherwise `@pytest.mark.integration` tests will fail with connection refused.
- **ADR file edits:** Phase 07 flips 4 ADRs Proposed → Accepted (per M3 A, overriding Phase 06 P45 B). This is the FIRST phase to amend ADR file content directly. Sets precedent that subsequent phases can flip their respective ADRs inline; semantic edits still defer to Phase 38.
