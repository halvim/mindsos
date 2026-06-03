# MindsOS POST_PHASE_38_PHASE_MAP

**Authoritative phased rollout plan for L4/L5 + L1/L3 reframe ships + L2 schema-v2 + L0 substrate + dream family.** Frozen 2026-06-02 at Chat C plan-authoring closure.

This map covers **Phases 39 through 49** — the eleven slots reserved for the post-Phase-38 stream. The L0-L3 plan (`PHASE_MAP.md`) is closed-class; this is its successor for the work-streams that Chat A (L4) + Chat B (L5) + L1/L3 reframe chat + L2 chat settled, plus the L0 substrate work the Phase-38 carry-forward audit surfaced.

**Not in scope for this map:** WSD installation, FOL installation, DWF installation, skill-acquisition process, code-skill installation, adapter family, maintenance chats. Each owns its own phase-map authored after its design-resolution chat closes. §6 reserves their slots without authoring them.

---

## 0. How a phase chat reads this file (load-bearing rule)

Same pattern as `PHASE_MAP.md §0`, with one new clause (per PB-Z reading-list discipline). Every phase chat reads:

1. **§1** (settled cross-cutting decisions).
2. **Its own row** in §3 / §4.
3. **The two prior phase rows** in the same rail (DAG-aware; see §1 "DAG execution").
4. **The most recent `confirmation_docs/PHASE_<N-1>_CONFIRMED.md`** for the same rail.
5. **Only the docs paths named in its own row.**
6. **NEW (PB-Z): diffs of any prior phase touching files in this phase's `Modules touched` enumeration.** Anticipates merge collisions under DAG execution.

Phase chats also read `HANDOFF.md` first (canonical entry point) and the workbench-migrated foundation docs as needed: `confirmation_docs/CHAT_A_DECISIONS.md` (L4 settlement), `confirmation_docs/CHAT_B_DECISIONS.md` (L5 settlement), `confirmation_docs/L1_L3_REFRAME_DECISIONS.md` (5 ADRs 0155-0159 + X1/X2/X3 sequencing), `confirmation_docs/L2_CHAT_DECISIONS.md` (4 new ADRs + 3 amendments).

---

## 1. Settled cross-cutting decisions

| Topic | Decision |
|---|---|
| Inherited from `PHASE_MAP.md §1` | All §1 decisions from the L0-L3 plan carry forward unchanged unless explicitly amended below: repackage-vs-rewrite, tester driver (`mindsos_cli`), distribution (Docker Compose), repo+registry, CI, branching (`phase-NN` off main), per-phase workflow (Mac + Linux two-machine), `doctor --self-test` checks, confirmation doc as artifact + schema, failure path, tests in-container, CLI backward compat, test layout, reproducibility, logs/data volumes, Linux+Compose v2, conflict resolution in source docs, foundations-first grouping, integration-phase exception, design-only-phase exception, mkdocs page evolution. |
| **DAG execution (PB-K + PB-Y)** | Stream B is a **4-rail DAG converging at Phase 46**, not a strict-serial chain. Rail A = (Phase 39 rename → Phase 43 L2 schema-v2). Rail B = (Phase 40 X1 → Phase 41 X2 → Phase 42 X3). Rail C = (L0_SUBSTRATE_CHAT closure → Phase 44 L0 substrate). Rail D = (DREAM_FAMILY_CHAT closure → Phase 45 dream family ship). All four rails complete before Phase 46 (L4 substrate) opens R0. Rails describe **design + impl parallelism**; **tester verification serializes** through the single tester per `PHASE_MAP.md §1` per-phase workflow. Phase-number = slot reservation, not execution order. |
| **`release.yml` retention amendment (PB-R)** | `release.yml` retention rule is amended from "5 most-recent confirmed phases by tag-time" to "5 most-recent confirmed phases by `[mindsos] phase` integer." Under DAG execution, tag order ≠ phase-number order; tag-time-based eviction would prune a higher-phase tarball that was tagged earlier. **Ships as a Stream A maintenance PR BEFORE Phase 39 branches.** One-line `release.yml` edit + acknowledgment line in `mindsos confirm-phase` wrapper. |
| **Reading-list discipline (PB-Z)** | Each phase R0 reading-list MUST include diffs of any prior phase touching files this phase's `Modules touched` enumerates. Anticipates DAG merge collisions. Known collision surfaces: `consolidate.py` (Phase 39/42/48), `identifiers.py` (Phase 39/40), `mindsos_core/schema.py` (Phase 43, possibly Phase 46). |
| **Branching under DAG** | Each rail's phase branches off `origin/main` per `PHASE_MAP.md §1` rule; under DAG, parallel branches each off main may surface predictable conflicts (per reading-list discipline above). Rebase off main after each peer-rail ship to stay current. |
| **Manifest `[mindsos] phase` field** | Unchanged. Per PB-S, no new `[mindsos_plan]` namespace field — Phases 39-49 stay monotonic across rails, no collisions arise. `doctor --self-test` check #5 unchanged. |
| **Sentinel chain disposition (PB-6)** | The L0-L3-closing chain `14a → 15a → 15b → 35 → 36 → 38` is **closed-class**. A new chain rooted at Phase 39 begins. Phase 39's chain-anchor file follows the closest-ancestor-matching-content rule: Phase 39 ships ADR-0044 §amendment-3 → use Phase 35 precedent `tests/phase_39/test_adr_amendment_sentinels.py`. Cross-plan regression coverage relies on the cumulative test suite, not on the sentinel chain. |
| **Ship-shape default disposition (PB-11 / IL-8)** | **Dropped from active discipline.** Zero phases in this map have zero-net-new-src-LOC; ship-shape PB has zero triggers. Phase 38 R6 lesson preserved in `PHASE_38_DESIGN_LOG.md §5` as inherited-lesson home. Future maps re-derive if a docs-only-shaped phase surfaces. |
| **ADR drafting load (PB-BB)** | Per-phase R0 drafts new ADRs ratifying Chat A + Chat B + L1/L3 reframe + L2 chat picks that hadn't reached ADR form yet. Estimate: ~10-15 new ADRs across Phases 46/47/48 (L4 substrate primitives, L4 orchestrator surfaces, L5 invariants). Same precedent as L0-L3 rollout (each code-shipping phase authored its ADRs at R0). ADR-0155 through ADR-0159 (reframe chat) and ADR-0151 through ADR-0154 (L2 chat) are already drafted; remaining numbers reserved 0160+. |
| **ADR-0150 amendment split (IL-3)** | L2_CHAT_DECISIONS D-L2-26 picked single bulk §amendment-4 for both rename + 4 new role-graphs. Refined here per Phase 39/Phase 43 split: **§amendment-4 (rename row only) ships Phase 39 with rename code; §amendment-5 (4 new role-graphs) ships Phase 43 with schema code.** Matches §am-1/§am-2/§am-3 precedent (one event per amendment). |
| **Phase numbering** | Continue from `phase-39-confirmed`. No reset. No decimal. No `[mindsos_plan]` field. Slots 39-49 reserved monotonic. |
| **Per-phase manifest-bump 9-surface checklist (Phase 39 §9.4 carry-forward)** | Every numbered-phase ship must advance, in lockstep with `mindsos_cli/manifest.toml` `[mindsos] phase` + `version`: (a) 7 package `__version__` strings (`mindsos_core` / `mindsos_cli` / `mindsos_capacity` / `mindsos_server` / `mindsos_instances` / `mindsos_admin` / `mindsos_knowledge`); (b) `pyproject.toml` `[project] version`; (c) `docker-compose.yml` `mindsos:phase{N}-prod` + `mindsos:phase{N}-test` image tags; (d) Phase 30/31/34 export-slate sentinel-flip files (`tests/phase_30/test_phase_30_export_slate.py` + `tests/phase_31/test_phase_31_export_slate.py` + `tests/phase_34/test_phase_34_export_slate.py` `test_version_bumped_to_phase_34` literal value bumps per the sentinel-flip-at-target-phase convention; file name stays `phase_34`). Doctor self-test + version-parity tests gate this. See `confirmation_docs/PHASE_39_DESIGN_LOG.md §9.4`. |
| **Pre-confirm-phase squash-merge discipline (Phase 39 §9.5 carry-forward)** | `mindsos confirm-phase --phase N` MUST run on a `main` that already contains the squash-merge of `phase-N` — confirm-phase writes `confirmation_docs/PHASE_N_CONFIRMED.md` against the local main state. Skipping the squash-merge step on Mac before running confirm-phase on Linux yields a CONFIRMED.md committed BEFORE the squash-merge it describes (Phase 39 ship anomaly; recovered via reflog restore + force-retag — see `PHASE_39_DESIGN_LOG.md §9.5`). |
| **Dockerfile `tools/` test-stage COPY (Phase 39 §9.3 carry-forward)** | Phase 39 added `COPY tools ./tools` to the test stage when shipping the first runtime script under `tools/`. Future phases shipping tools must verify this COPY exists; updating its trailing comment to name the new consumer is conventional. |
| **Pair-execution discipline (Phase 43 R11 carry-forward — Cowork ↔ Mac ↔ Linux)** | Cowork (sandbox) prepares file content via Edit/Write tools; the user runs git commands on Mac; Linux runs cumulative gates via docker. Cowork sandbox `.git/` is read-only — sandbox CANNOT run `git add` / `git commit` / `git push` / `git checkout -b`. Cowork CAN: read repo state (`git status`/`git log`/`git diff`), edit working-tree files via Edit/Write. Per ship chat: Cowork issues one command-group at a time with expected output; the user pastes back the actual output if it differs ("if my output differs I'll paste; otherwise tell you to proceed"). Group simple obvious sequences in one box; tag Mac vs Linux explicitly. Established as default for all future numbered-phase ship chats. See `PHASE_43_DESIGN_LOG.md §9.1` R11. |
| **6-step confirm-phase workflow (Phase 43 R12 carry-forward)** | Established pattern for the `mindsos confirm-phase` cycle: (1) Cowork gives Mac command to generate `notes-phase-N.md` from the template (or `touch` if no template exists); (2) Cowork provides the layer title in a copy-block (e.g., "L2 schema-v2 ship"); (3) Cowork provides the complete `tester_notes` body in a copy-block (drawn from cumulative gate output + design log §9 content); (4) tester edits the notes file on Linux; (5) tester runs `mindsos confirm-phase --phase N --notes-file confirmation_docs/notes/notes-phase-N.md` on Linux from post-squash main; (6) tester commits `PHASE_N_CONFIRMED.md` + notes-phase-N.md + pushes. See `PHASE_43_DESIGN_LOG.md §9.1` R12. |
| **Docker test image rebuild discipline (Phase 43 R10 carry-forward)** | `docker-compose.yml` `mindsos-test` service has no source bind-mount; image bakes source at build time. Each Linux cumulative gate run after a Mac push MUST `docker compose build mindsos-test` before `docker compose run --rm mindsos-test pytest tests/`. Skipping the rebuild runs tests against stale source — surfaces as "fix not applied" puzzlement at the gate. See `PHASE_43_DESIGN_LOG.md §9.1` R10. |
| **Cookbook authoring scope (PB-7 + PB-W)** | nlu-slice + code-slice stay out of scope; routed to WSD installation + code-skill installation chats per `_workbench/cookbook_routing.md`. Phase 49 (Integration C) ships `usage/cookbook/end-to-end.md` as accompanying cookbook page (Phase 32→text-realm precedent). |
| **Model C remediation (PB-8)** | Strict-lift + 8-12 TYPE_COMPAT terminology docs + ~50-warning filename normalization bundled into Phase 42 (X3). Drop `mkdocs-redirects` plugin work entirely (housekeeping copied parent-tree ADRs into MindsOS; cross-link warnings collapse to filename drift). |
| **Workbench migration (PB-F + IL-9)** | Closed-class decision logs migrate to `confirmation_docs/` at Chat C closure: CHAT_A_DECISIONS, CHAT_B_DECISIONS, L1_L3_REFRAME_DECISIONS, L2_CHAT_DECISIONS, CHAT_A_L4_BASELINE, CHAT_PLAN_L4_L5. `NEXT_CHAT_PROMPTS.md` → `_archive_Layered_Intelligence/` (forensic-only; superseded). All `L*_FUTURE_WORK.md` stay in `_workbench/` while their open items remain. |
| **Stream A tracking** | In-repo `_workbench/STREAM_A_BACKLOG.md` mini-index. One line per item: owner + slot + status. Out-of-band of any phase number. |
| **Stream C disposition (PB-V)** | Reduced to 2 docs items (`concepts/layers.md` + `society-of-mind.md` + `getting-started/facts-and-figures.md`); absorbed into Phase 48 ship as accompanying docs. PHASE_38 §4 item #15 dropped (parent-tree forensic only). |
| **L4 v0 catalog discipline (PB-L)** | Phase 47 (L4 orchestrator) ships **minimal `planning.*` v0 placeholder catalog** (4 trivial impls: `derive_initial_plan` returns single-Milestone Plan; `decompose` returns []; `aggregate_outputs` returns last-child-output; `is_leaf` returns True). ALS subsystem registry ships with zero registered subsystems. WSD installation chat replaces v0 atomically with real catalogs. Same pattern as Phase 45 dream family ships 3 v1 capacities; downstream installation chats extend. |
| **L4/L5 v1 demo scope** | L4/L5 v1 ship is **substrate + orchestrator + chain mechanics + v0 placeholder catalogs**, not a feature-complete reasoning system. First feature-complete demo lands when WSD installation chat ships planning.* + ALS catalogs. Phase 49 (Integration C) exercises the substrate end-to-end with trivial-task scope. |
| Out of scope (carries forward) | WSD installation phases, FOL installation phases, DWF installation phases, skill-acquisition process design, code-skill installation, adapter family installation, L0 admin-surface items (absorbed into WSD installation per PB-T), L0-17 simplified-execution-mode CLI flag (maintenance chat). See §6 for downstream-chat sequencing. |

---

## 2. Per-phase row schema

Verbatim from `PHASE_MAP.md §2` (per IL-1). No new fields, no removed fields.

```
### Phase NN — <Title>

  **Status:** Pending | In progress | Confirmed | Superseded | Abandoned
  **Branch:** phase-NN
  **Tag on confirm:** phase-NN-confirmed
  **Rail:** A | B | C | D | convergence | integration       ← NEW informational field (PB-K)
  **Depends on:** <list of phase NNs that must be Confirmed first + named chat closures>
  **Layer(s):** <L0 / L1 / L2 / L3 / L4 / L5 / cross>
  **Net-new code?:** No (repackage only) | Yes (specify what)
  **Features in scope (capability-level — implementation chosen by phase chat):**
    - <terse capability list>
  **Modules touched (best-effort; phase chat finalises):**
    - <package/module list>
  **Automated tests (location + intent — names chosen by phase chat):**
    - tests/phase_NN/ — <what they verify>
  **Confirmation command:**
    `mindsos confirm-phase --phase NN --notes-file notes-phase-NN.md`
  **Pass criterion (what the tester verifies):**
    - <bulleted, terse>
  **Risks / known issues to watch:**
    - <bulleted>
  **Doc sections this phase confirms (mkdocs paths):**
    - docs/<...>.md — <one-line slice description>
  **Breaking changes from prior phase:**
    - <list, or "none">
```

The `Rail` field is informational only — it does not change tooling. `phase-NN` branch naming + tag naming remain integer-based.

---

## 3. Phase index

| # | Title | Rail | Layer | Deps |
|---|---|---|---|---|
| 39 | L2 — `memories` → `episodic_memories` atomic rename + L2-35 alignment reconciliation + ADR-0044 §am-3 + ADR-0150 §am-4 (rename row) | A | L2 | 38 |
| 40 | L3 — X1: ADR-0157 family-specific dont-know contracts + ADR-0158 DataState realm naming convention | B | L3 | 38 |
| 41 | L3 — X2: ADR-0155 Monitor lifecycle retirement from L3 | B | L3 | 40 |
| 42 | L3 — X3: ADR-0156 bipartite topology + ADR-0159 capacity registration contract v2 + Phase 27 audit deliverable + Model C remediation (strict-lift + filename normalization + TYPE_COMPAT docs) | B | L1+L3 | 41 |
| 43 | L2 — schema-v2: 4 new role-graphs + `mutation_discipline` runtime invariant + `storage_mode` + bootstrap topological order + ADR-0151 + ADR-0152 + ADR-0153 + ADR-0094 §am-1 + ADR-0150 §am-5 | A | L1+L2 | 39 |
| 44 | L0 — substrate: `FalkorDBLocalPersister` + `SQLiteLocalPersister` + Falkor-backed L3 bootstrap + state-file serialization + `kl.read_at_version` + `kl.retire_version` lazy-inline hook + `applies_after` bootstrap field + `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` + `READ_OTHER_LOCAL_EPISODIC_MEMORY` capability | C | L0+L2 | 38 + **L0_SUBSTRATE_CHAT** closure |
| 45 | L3 — `dream.*` family ratification: 3 v1 capacities (`dream.maintenance`, `dream.exploration`, `dream.retry`) + execution-policy contracts | D | L3 | 38 + **DREAM_FAMILY_CHAT** closure |
| 46 | L4 — substrate: IntelligenceLayer lifecycle + priority-tier Executor (D32.5b) + worker pool + MM RWLock + MM resolution+instantiation layer + cooperative cancellation framework + signal-triage worker + ALS subsystem registry | convergence | L4 | 42, 43, 44, 45 |
| 47 | L4 — orchestrator: six-phase task lifecycle + attention queue + replan-check dispatch + sufficient-predicate eval + minimal `planning.*` v0 catalog (PB-L) + ALS dream-cycle timer + 10 signal-source skeletons + 11 ALS subsystem skeletons | convergence | L4 | 46 |
| 48 | L5 — v1: MM consolidation write path + Episode/Memory schemas live + dream pipeline hookup + retention monitoring instrumentation (PB-AA PB-QQ) + concepts/layers.md + society-of-mind.md + facts-and-figures.md docs | convergence | L5 | 47 |
| 49 | Integration C — end-to-end L0→L5 trivial-task scenario + `usage/cookbook/end-to-end.md` + Falkor index decisions (PB-AA PB-HHH) | integration | cross | 48 |

**Total: 11 phase slots.** Convergence at Phase 46 (Rails A+B+C+D all closed). Integration phase at Phase 49 (mirrors Phase 26 + Phase 32 precedent). Eight phases carry NEW CODE; three are layer-architecture-changing (40, 41, 42 retire shipped code under §1 design-only-phase exception's letter-sub-phase analog). Phase 49 is the integration convergence point.

---

## 4. Per-phase rows — full detail

(Implementation-specific decisions — exact CLI verbs, file paths, library choices — are deliberately **not** committed in this map. The phase chat picks them when it begins, refines its row, then implements.)

### Phase 39 — L2 `memories` → `episodic_memories` atomic rename

  **Status:** SHIPPED 2026-06-02
  **Branch:** phase-39 (squash-merged to main)
  **Tag on confirm:** phase-39-confirmed
  **Rail:** A
  **Depends on:** 38 (Phase 38 confirmed); pre-Phase-39 Stream A prereqs (`release.yml` retention amendment per PB-R landed). All satisfied at A0+A9+A1 closure 2026-06-02.
  **Layer(s):** L2 (rename touches L0/L1/L3 via consumers).
  **Net-new code?:** Yes — `tools/rename_memories_to_episodic_memories.py` migration script (~30 LOC; no-op on empty v1 state; ships per PB-X for dev-env safety).

  **Locked decisions (this chat — 2026-06-02):**
  - **Atomic rename.** No alias, no deprecation window (per L2_CHAT_DECISIONS D-L2-16 + PB-J ordering: rename ships first to minimize cumulative drift).
  - **`ROLE_MEMORIES` → `ROLE_EPISODIC_MEMORIES`** constant rename; all imports updated in the same PR.
  - **`memory_iri(version, user_id, memory_id)` retired**; replaced by `episode_iri(version, user_id, episode_id)` (per-task entry) + sibling `memory_composite_iri(version, user_id, memory_id)` (Chat B clustering composite).
  - **`_PREFIXES` entry `"memories-"` → `"episodic-memories-"`.**
  - **`_KINDS_PER_ROLE`** adds entries `"episode"` + `"memory"` under `ROLE_EPISODIC_MEMORIES`.
  - **`schemas/memories.py` → `schemas/episodic_memories.py`**; old single Memory node-type retired; new Episode + Memory node types per Chat B D-B47 + L5 design notes §4.3 + §4.6 (schema-only at this phase; full v1 storage discipline `append_only_with_lazy_inline` ratification lands Phase 43 via ADR-0153).
  - **`mindsos_capacity/builtins/consolidate.py`** (`consolidate:mm`) updated to target the renamed role + new Episode entry shape (Phase 33-shipped capacity body re-targets).
  - **Phase 25 audit constant `EVT_READ_OTHER_LOCAL_MEMORY` → `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY`** if present (full new capability + audit-event handling ships Phase 44 per D-L2-23).
  - **L2-35 alignment reconciliation bundled (IL-7).** `identifiers.py:303` `alignment_role()` body fixed to `f"alignment:{a}:{b}"` per L2_CHAT_DECISIONS D-L2-1 + ADR-0154 canonical; docstring rewritten; Phase 36 validator test updated.
  - **ADR-0044 §amendment-3 ships** (memories → episodic_memories rename + entry-type restructure per L2_CHAT_DECISIONS D-L2-25).
  - **ADR-0150 §amendment-4 ships (rename row only per IL-3 split).** 4-new-role-graph expansion splits to §amendment-5 (Phase 43).
  - **Migration script `tools/rename_memories_to_episodic_memories.py` ships** per PB-X (v1 production has no pre-rename state; script is safety-net for dev environments).

  **Features in scope (capability-level):**
  - Atomic identifier-surface rename across `mindsos_knowledge/identifiers.py` + bootstrap + schemas + admin importers + `consolidate:mm` capacity body + write_handle + validators + KnowledgeLayer + tests.
  - Migration script (no-op on empty state).
  - Two ADR amendments (ADR-0044 §am-3 + ADR-0150 §am-4-rename).
  - L2-35 alignment canonical-form reconciliation bundled.

  **Modules touched (best-effort):**
  - `mindsos_knowledge/identifiers.py` (`ROLE_*` rename + IRI builder rename + prefix table + kinds map + alignment_role fix).
  - `mindsos_knowledge/bootstrap.py` (rename `episodic_memories_bootstrap` entry).
  - `mindsos_knowledge/schemas/memories.py` → `schemas/episodic_memories.py` (renamed; schema body extended per D-L2-17 Episode + Memory node types).
  - `mindsos_knowledge/validators.py` (rename references).
  - `mindsos_knowledge/knowledge_layer.py` (rename references).
  - `mindsos_knowledge/write_handle.py` (rename references).
  - `mindsos_capacity/builtins/consolidate.py` (rename + new entry shape target).
  - `mindsos_server/audit.py` (audit constant rename if pre-existing).
  - `tools/rename_memories_to_episodic_memories.py` (new migration script).
  - `docs/decisions/adr/0044-memories-move-to-local-per-user.md` (§amendment-3).
  - `docs/decisions/adr/0150-l2-knowledge-lifecycle.md` (§amendment-4 rename row).

  **Automated tests:**
  - `tests/phase_39/test_rename_atomic.py` — verifies all import paths resolve to renamed names; no `ROLE_MEMORIES`, `memory_iri`, `memories-` prefix, or `schemas/memories` references remain.
  - `tests/phase_39/test_alignment_canonical.py` — verifies `alignment_role("concepts", "lexicon")` returns `"alignment:concepts:lexicon"` (canonical form); Phase 36 validator test updated to match.
  - `tests/phase_39/test_episode_memory_iri_builders.py` — verifies new IRI builders produce expected forms; reject malformed inputs.
  - `tests/phase_39/test_migration_script_idempotent.py` — runs migration script against empty state; asserts no-op + idempotent on re-run.
  - `tests/phase_39/test_adr_amendment_sentinels.py` — new chain root (PB-6); anchors §amendment-3 + §amendment-4 text.
  - Cumulative regression against all phase suites must remain green post-rename.

  **Confirmation command:**
  `mindsos confirm-phase --phase 39 --notes-file notes-phase-39.md`

  **Pass criterion:**
  - All cumulative tests pass (Phase 12/14/25/33/34/36 + new Phase 39 suite).
  - `grep -rn "ROLE_MEMORIES\|memory_iri\|memories-\|schemas/memories" mindsos_*/ tests/` returns zero hits.
  - Migration script runs idempotently against empty state.
  - ADR-0044 §amendment-3 + ADR-0150 §amendment-4 rendered correctly under `mkdocs build`.
  - L2-35 reconciliation confirmed: `alignment_role(a, b)` returns colon-canonical form; Phase 36 validator test green.

  **Risks / known issues to watch:**
  - **Predictable conflict with Phase 40 X1** on `identifiers.py` (X1 adds REALM_* constants; Phase 39 rename adds episode_iri + memory_composite_iri + edits alignment_role). Mitigated by reading-list discipline (PB-Z) — Phase 40 R0 reads Phase 39 diff.
  - **Triple-touch on `consolidate.py`** (Phase 39 rename + Phase 42 `context["kl"]` → `context.kl` + Phase 48 D-B47 + D-L2-17 schema target). Phase 42 + Phase 48 R0 reading-list anticipates.
  - Phase 33-shipped `consolidate:mm` capacity body must continue passing Phase 33 tests post-rename. Sentinel anchor in Phase 33 tests for any rename references.
  - Dev-environment users with accumulated `ROLE_MEMORIES` state need to run the migration script. v1 production has no such state.

  **Doc sections this phase confirms (mkdocs paths):**
  - `docs/decisions/adr/0044-memories-move-to-local-per-user.md` — §amendment-3.
  - `docs/decisions/adr/0150-l2-knowledge-lifecycle.md` — §amendment-4 (rename row only).
  - `docs/usage/knowledge/memories.md` — renamed to `episodic-memories.md` or deleted (resolves PHASE_38 §4 #16 drift). Phase chat picks.

  **Breaking changes from prior phase:**
  - **ABI-level rename.** `mindsos_knowledge.identifiers.ROLE_MEMORIES` removed; consumers must use `ROLE_EPISODIC_MEMORIES`. `memory_iri()` removed; consumers use `episode_iri()` or `memory_composite_iri()`. `_PREFIXES` `"memories-"` removed; `"episodic-memories-"` added. `schemas/memories.py` module path removed; consumers import from `schemas/episodic_memories.py`. Public API; users of `mindsos_knowledge` as a library must update imports.

---

### Phase 40 — L3 X1: family-specific dont-know contracts + DataState realm naming

  **Status:** Pending
  **Branch:** phase-40
  **Tag on confirm:** phase-40-confirmed
  **Rail:** B
  **Depends on:** 38 (Phase 38 confirmed). **NOT depends on Phase 39 directly** under DAG; Rail B is parallel to Rail A. (Reading-list discipline applies for `identifiers.py` collision.)
  **Layer(s):** L3.
  **Net-new code?:** Yes — new `mindsos_capacity/family_rules.py` module (~50 LOC); 9 `REALM_*` constants in `identifiers.py`; `DS_UNHANDLED_INPUT` marker registration; `DontKnowReason.UNHANDLED_INPUT` enum value; `register_datastate` validation expansion (~10 LOC).

  **Locked decisions (this chat — 2026-06-02):**
  - **ADR-0157 (D46) ships** — family-specific dont-know contracts per L1_L3_REFRAME_DECISIONS §D46. 5-shape catalog: DATASTATE_MARKER, OPTIONAL_RETURN, VERDICT, VALIDATION_RESULT, NO_DONT_KNOW. Family rule implicit from capacity IRI prefix; two-level lookup (name-prefix first → category fallback → DATASTATE_MARKER permissive default).
  - **ADR-0158 (D48) ships** — DataState naming convention `datastate:<realm>.<name>` per L1_L3_REFRAME_DECISIONS §D48. 9 reserved v1 realms: core, marker, bridge, text, mm, problem_trace, nlu, code, dream. Strict-by-default realm validation at `register_datastate`; `allow_new_realm=True` opt-in for admin extensions.
  - **Shared `identifiers.py` realm constants** between X1 + X3 (per L1/L3 reframe X3 cascade); 9 `REALM_*` frozen-string constants + frozenset.
  - **`DS_UNHANDLED_INPUT = "datastate:marker.unhandled_input"`** constant ships.
  - **`DontKnowReason.UNHANDLED_INPUT`** enum entry added.

  **Features in scope:**
  - `family_rules.py` module: FAMILY_RULES dict + `lookup_rule(capacity_iri)` function with 2-level prefix lookup.
  - DataState realm constants + frozenset in `identifiers.py`.
  - `register_datastate` validation: enforces `datastate:<realm>.<name>` form; rejects unknown realms unless `allow_new_realm=True`.
  - DS_UNHANDLED_INPUT registration as core marker DataState.
  - DontKnowReason enum extension.

  **Modules touched:**
  - `mindsos_capacity/family_rules.py` (NEW).
  - `mindsos_capacity/__init__.py` (export `family_rules` + `DS_UNHANDLED_INPUT` + DontKnowReason addition).
  - `mindsos_capacity/capacity_layer.py` (`register_datastate` validation).
  - `mindsos_knowledge/identifiers.py` (9 `REALM_*` constants + frozenset of reserved realms).
  - `docs/decisions/adr/0157-family-specific-dontknow-contracts.md` (ratified to Accepted on ship).
  - `docs/decisions/adr/0158-datastate-naming-convention-and-realms.md` (ratified to Accepted on ship).

  **Automated tests:**
  - `tests/phase_40/test_family_rules_lookup.py` — name-prefix-first then category-fallback then DATASTATE_MARKER default; 5 shapes coverage.
  - `tests/phase_40/test_realm_validation.py` — strict-by-default; `allow_new_realm=True` opt-in; rejects malformed IRI.
  - `tests/phase_40/test_ds_unhandled_input_registered.py` — verifies registration + default `dont_know_marker` IRI.
  - `tests/phase_40/test_dont_know_reason_enum.py` — UNHANDLED_INPUT value present + ordered correctly.
  - `tests/phase_40/test_adr_amendment_sentinels.py` — anchors ADR-0157 + ADR-0158 text; chain link from Phase 39.

  **Confirmation command:**
  `mindsos confirm-phase --phase 40 --notes-file notes-phase-40.md`

  **Pass criterion:**
  - All Phase 40 tests green + cumulative suites green.
  - ADR-0157 + ADR-0158 ratified text on disk (`docs/decisions/adr/`).
  - `register_datastate` rejects unknown realm without opt-in; accepts with opt-in.
  - `family_rules.lookup_rule("predicate.is_question")` returns NO_DONT_KNOW; `lookup_rule("scoring.confidence")` returns DATASTATE_MARKER permissive default; etc.

  **Risks / known issues to watch:**
  - **Phase 39 `identifiers.py` collision** under DAG. Phase 40 R0 reads Phase 39 diff per PB-Z; rebases off main after Phase 39 lands.
  - 9-realm reserved list may need additive realm if a v1 consumer (WSD installation) surfaces one not yet enumerated. Admin opt-in handles.
  - FAMILY_RULES dict correctness depends on accurate per-family return-type accounting (5 corrections required during R2 saturation; see L1_L3_REFRAME_DECISIONS §D46).

  **Doc sections this phase confirms (mkdocs paths):**
  - `docs/decisions/adr/0157-family-specific-dontknow-contracts.md`.
  - `docs/decisions/adr/0158-datastate-naming-convention-and-realms.md`.
  - `docs/concepts/capacity-families.md` (new or amended; documents 5-shape catalog).

  **Breaking changes from prior phase:**
  - None. ADR-0157 + ADR-0158 are additive at this phase (capacities ratifying via prefix + register-time validation); existing Phase 27-33 capacities default to DATASTATE_MARKER family rule with no code change.

---

### Phase 41 — L3 X2: Monitor lifecycle retirement from L3

  **Status:** Pending
  **Branch:** phase-41
  **Tag on confirm:** phase-41-confirmed
  **Rail:** B
  **Depends on:** 40 (Phase 40 confirmed).
  **Layer(s):** L3 (retirement; L4 substrate-side replacement ships Phase 46).
  **Net-new code?:** Yes — `cl.iter_monitors()` helper (~10 LOC); net-negative (retires ~150 LOC of resident infrastructure).

  **Locked decisions:**
  - **ADR-0155 (D36) ships** — Monitor lifecycle relocated from L3 to L4 substrate per L1_L3_REFRAME_DECISIONS §D36. **Hard-break public exports.** Phase 31 module retires whole.
  - **Retire from L3:** `start_resident()` / `stop_resident()` / `active_subscriptions()` methods on `CapacityLayer`; `_subscriptions` dict; `ResidentSubscription` dataclass; `ResidentError` exception; `KIND_RESIDENT` constant. **Phase 31 module deletes whole.**
  - **Keep at L3:** `Monitor` subclass + `subscribes_to: IRI` field with DataState IRI semantics.
  - **`KIND_RESIDENT` → `KIND_MONITOR`** rename (preserves REACTIVE/MONITOR/ADAPTER node_kind triad).
  - **`cl.iter_monitors()`** new helper enumerates registered Monitor capacities for L4-substrate consumption (L4 substrate consumes this at Phase 46).
  - **L4-side `MonitorSubscriptionRegistry`** ships Phase 46 with session-scope `Dict[DataState IRI, List[Monitor IRI]]` shape per L1_L3_REFRAME_DECISIONS §D36 constraint.

  **Features in scope:**
  - Retire Phase 31 resident infrastructure entirely (resident methods + state + subscription classes + tests).
  - Add `cl.iter_monitors()` helper.
  - Rename `KIND_RESIDENT` → `KIND_MONITOR` globally.
  - HANDOFF §3.1 amendment (strike retired methods from L3-surface-L4-consumes list; add `cl.iter_monitors()`).

  **Modules touched:**
  - `mindsos_capacity/capacity_layer.py` (delete `start_resident` / `stop_resident` / `active_subscriptions` / `_subscriptions`; add `iter_monitors`).
  - `mindsos_capacity/__init__.py` (delete `ResidentSubscription` / `ResidentError` / `KIND_RESIDENT` exports; add `KIND_MONITOR`).
  - Phase 31 module-set deletes whole (~6-8 files).
  - Phase 27 + Phase 28 dataclass/register tests get `node_kind` rename edits.
  - `docs/decisions/adr/0155-monitor-lifecycle-relocated-from-l3-to-l4.md` (ratified to Accepted on ship).
  - `docs/concepts/monitors.md` (amendment for relocation).
  - `HANDOFF.md` §3.1 amendment (Chat C closure already drafted this; Phase 41 finalizes).

  **Automated tests:**
  - `tests/phase_41/test_resident_infrastructure_retired.py` — verifies no shipped reference to retired surfaces; sentinel for the hard-break.
  - `tests/phase_41/test_iter_monitors.py` — verifies `cl.iter_monitors()` enumerates registered Monitors; empty on no-monitor sessions.
  - `tests/phase_41/test_kind_monitor_rename.py` — verifies KIND_MONITOR constant + node_kind value present.
  - `tests/phase_41/test_adr_amendment_sentinels.py` — anchors ADR-0155 text; chain link from Phase 40.

  **Confirmation command:**
  `mindsos confirm-phase --phase 41 --notes-file notes-phase-41.md`

  **Pass criterion:**
  - All Phase 41 tests green + cumulative suites green (Phase 31 tests retired; Phase 27/28 tests pass post-rename).
  - ADR-0155 ratified.
  - `grep -rn "start_resident\|stop_resident\|active_subscriptions\|ResidentSubscription\|ResidentError\|KIND_RESIDENT"` returns zero hits.
  - HANDOFF §3.1 reflects retired surface set.

  **Risks / known issues to watch:**
  - **Hard-break public API.** Any external consumer of `cl.start_resident` / `cl.stop_resident` breaks. Internal users only at v1; no production consumers; safe to hard-break.
  - **Phase 31 retirement test churn** ~6-8 files deleted; ensures no orphan import in tests/.
  - L4 substrate (Phase 46) is the consumer of `cl.iter_monitors()` + must implement `MonitorSubscriptionRegistry`; Phase 41 ships the L3-side retirement without the L4-side replacement live. Acceptable per DAG (no monitor consumers shipped pre-Phase-46).

  **Doc sections this phase confirms:**
  - `docs/decisions/adr/0155-monitor-lifecycle-relocated-from-l3-to-l4.md`.
  - `docs/concepts/monitors.md` (relocation amendment).

  **Breaking changes from prior phase:**
  - **Hard-break.** `cl.start_resident()` / `cl.stop_resident()` / `cl.active_subscriptions()` removed. `ResidentSubscription` / `ResidentError` / `KIND_RESIDENT` removed. `KIND_RESIDENT` renamed to `KIND_MONITOR`. Phase 31 module deleted whole.

---

### Phase 42 — L3 X3: bipartite topology + capacity registration contract v2 + Phase 27 audit + Model C remediation

  **Status:** Pending
  **Branch:** phase-42
  **Tag on confirm:** phase-42-confirmed
  **Rail:** B
  **Depends on:** 41 (Phase 41 confirmed).
  **Layer(s):** L1 + L3 (Phase 06 amendment in mindsos_instances; main L3 schema change).
  **Net-new code?:** Yes — `mindsos_capacity/context.py` (~150 LOC typed `CapacityContext` + 4 Protocols + `CancelTokenView`); 5 canonical verdict types (~30 LOC); `IntergraphEdgeInstance` + `IntergraphHyperEdgeInstance` (~80 LOC). Net-roughly-zero overall (retires ~330 LOC discovery.py + replaces with bipartite walk algorithm ~50 LOC; replaces `register_capacity` edge emission ~30 LOC).

  **Locked decisions:**
  - **ADR-0156 (D38) ships** — L3 bipartite topology per L1_L3_REFRAME_DECISIONS §D38. Capacities + DataStates remain nodes; explicit `produces` (capacity→DataState) + `consumes` (DataState→capacity) IntergraphEdges emitted at `register_capacity` time. TYPE_COMPAT retires. `discovery.py` deletes whole (~330 LOC). `views.successors_of` + `pipeline.find_pipeline` rewrite against bipartite walks.
  - **ADR-0159 ships** — capacity registration contract v2 per L1_L3_REFRAME_DECISIONS §Registration. 5 new `_CapacityBase` fields (`concurrent`, `inline`, `max_latency_ms`, `precondition_iri`, `effect_iri`, `reads_mm`); new `mindsos_capacity/context.py` module with typed `CapacityContext` (9 fields) + 4 Protocols (`MMHandle`, `KLHandle`, `CapacityLayerHandle`, `CancelToken`) + `CancelTokenView` wrapper + 5 canonical verdict types.
  - **`mindsos_instances` Phase 06 amendment ships** `IntergraphEdgeInstance` + `IntergraphHyperEdgeInstance` (Chat B D-B41 cascade gap absorbed).
  - **Phase 27 audit deliverable: `confirmation_docs/PHASE_27_DONT_KNOW_AUDIT.md`** lands as Phase 42 sub-deliverable (L1_L3_REFRAME_DECISIONS §D38 cascade).
  - **Phase 33-35 write capacity bodies migrate** `context["kl"]` → `context.kl` (mechanical; ~2-3 bodies; per L1_L3_REFRAME_DECISIONS §ADR-0159 §Fork 10).
  - **Model C remediation** (PB-8) bundled: `mkdocs build --strict` lift + ~50 filename normalization rewrites + 8-12 docs surfaces touching TYPE_COMPAT terminology.
  - **One-pass migrator** under ADR-0134 schema migration emits produces/consumes edges from existing Phase 27-33 `inputs`/`outputs` properties; strips properties; idempotent. Migration scope = Global only (Locals are in-memory pending Phase 44 persisters).

  **Features in scope:**
  - Bipartite topology + edge-emission `register_capacity` rewrite.
  - Typed CapacityContext + Protocols + verdict types.
  - 2 new instance subclasses (`IntergraphEdgeInstance` + `IntergraphHyperEdgeInstance`).
  - One-pass Global migrator.
  - Phase 27 audit deliverable doc.
  - Model C remediation (strict-lift + filename normalization + TYPE_COMPAT docs cleanup).
  - Phase 33-35 capacity body migration (mechanical).

  **Modules touched:**
  - `mindsos_capacity/context.py` (NEW; ~150 LOC).
  - `mindsos_capacity/verdicts.py` (NEW; ~30 LOC; 5 canonical verdict types).
  - `mindsos_capacity/_CapacityBase` (5 new fields).
  - `mindsos_capacity/capacity_layer.py` (`register_capacity` edge emission; retires TYPE_COMPAT).
  - `mindsos_capacity/discovery.py` (DELETE; ~330 LOC).
  - `mindsos_capacity/pipeline.py` (`find_pipeline` rewrite; bipartite BFS).
  - `mindsos_capacity/views.py` (rewrite `successors_of` + new `inputs_of` / `outputs_of` helpers).
  - `mindsos_capacity/builtins/consolidate.py` + Phase 33-35 write bodies (`context["kl"]` → `context.kl`).
  - `mindsos_instances/` (add `IntergraphEdgeInstance` + `IntergraphHyperEdgeInstance` subclasses; Phase 06 amendment ADR-0132 §amendment-N).
  - `mindsos_knowledge/identifiers.py` (shared `REALM_*` constants already present from Phase 40; no duplicate).
  - `tools/migrate_phase_42_bipartite.py` (NEW; one-pass migrator).
  - `confirmation_docs/PHASE_27_DONT_KNOW_AUDIT.md` (NEW; Phase 27 audit deliverable).
  - `mkdocs.yml` + ~50 docs files (Model C remediation; filename normalization).
  - 8-12 docs surfaces with TYPE_COMPAT references (cleanup).
  - `docs/decisions/adr/0156-l3-bipartite-topology-reframe.md` (ratified).
  - `docs/decisions/adr/0159-capacity-registration-contract-v2.md` (ratified).
  - ADR-0069 + ADR-0086 supersession notes; ADR-0070 + ADR-0071 + ADR-0072 + ADR-0078 + ADR-0132 + ADR-0143 + ADR-0146 + ADR-0147 amendment paragraphs.

  **Automated tests:**
  - `tests/phase_42/test_bipartite_register.py` — `register_capacity` emits produces/consumes edges; idempotent upsert.
  - `tests/phase_42/test_pipeline_find_bipartite.py` — `find_pipeline` rewrites BFS over bipartite walk; semantic-preserving against Phase 30 cases.
  - `tests/phase_42/test_typed_capacity_context.py` — 4 Protocols enforce + `CancelTokenView` + `MappingProxyType` for `version_snapshot`.
  - `tests/phase_42/test_intergraph_instances.py` — `IntergraphEdgeInstance` + `IntergraphHyperEdgeInstance` instantiation + persistence.
  - `tests/phase_42/test_migrator_idempotent.py` — Global migrator emits edges + strips properties + idempotent on re-run.
  - `tests/phase_42/test_phase_27_audit_doc.py` — sentinel on audit doc presence + content shape.
  - `tests/phase_42/test_mkdocs_strict_clean.py` — `mkdocs build --strict` exits 0.
  - `tests/phase_42/test_adr_amendment_sentinels.py` — anchors ADR-0156 + ADR-0159 + amendments; chain link from Phase 41.
  - Phase 29 test suite retires whole.
  - Phase 33 `test_outputs_terminator_discovery.py` retires or rewrites.

  **Confirmation command:**
  `mindsos confirm-phase --phase 42 --notes-file notes-phase-42.md`

  **Pass criterion:**
  - All Phase 42 tests + cumulative green; Phase 29 + selected Phase 33 tests retired cleanly.
  - `mkdocs build --strict` clean.
  - ADR-0156 + ADR-0159 ratified; 8 amendment ADRs landed.
  - Migrator runs once against shipped Global state; produces expected edge count.
  - Phase 27 audit deliverable present and readable.
  - `grep -rn "TYPE_COMPAT\|discover_for_capacity\|discover_for_datastate\|rediscover_all"` returns zero hits.

  **Risks / known issues to watch:**
  - **Largest phase in Stream B.** Spans L1 + L3 + docs + ADR amendments + migrator + audit. Tester load.
  - **`consolidate.py` second touch** (Phase 39 rename was first). PB-Q reading-list discipline anticipates.
  - One-pass migrator idempotence is load-bearing under DAG (Phase 44 Locals don't ship pre-Phase 44).
  - Model C remediation may surface unknown link-drift surfaces; strict-lift criterion forces resolution.

  **Doc sections this phase confirms:**
  - `docs/decisions/adr/0156-l3-bipartite-topology-reframe.md`.
  - `docs/decisions/adr/0159-capacity-registration-contract-v2.md`.
  - `confirmation_docs/PHASE_27_DONT_KNOW_AUDIT.md` (audit deliverable).
  - 8-12 amended docs pages touching TYPE_COMPAT terminology.
  - ~50 filename-normalized cross-link rewrites across `docs/decisions/summary/{core,knowledge,server,capacity,intelligence,cross-layer}.md`.

  **Breaking changes from prior phase:**
  - **`_CapacityBase` schema extension.** 5 new fields default-valued; backward-compatible at registration site but breaks any external consumer expecting old field set.
  - **`register_capacity` semantics:** edge emission at register time; consumers of TYPE_COMPAT-style discovery break (none in shipped code post-discovery.py deletion).
  - **`CapacityContext` shape:** Phase 33-35 bodies migrate `context["kl"]` → `context.kl`; any external capacity body in dev environments needs the same.
  - **`mindsos_instances` catalog:** 8 subclasses → 10 (additive).

---

### Phase 43 — L2 schema-v2: 4 new role-graphs + mutation_discipline runtime invariant + per-NodeType storage_mode + bootstrap applies_after field + ADR-0094 §am-1 detector + consolidate Episode retarget + episodic_memories body finalize

  **Status:** **SHIPPED 2026-06-03.** Rail A slot 2 complete. Full design log at `confirmation_docs/PHASE_43_DESIGN_LOG.md`; ship-time impl-amendments at §9. See HANDOFF.md §3.1.13 for full ship closure detail.
  **Branch:** phase-43 (squash-merged to main)
  **Tag on confirm:** phase-43-confirmed
  **Rail:** A
  **Depends on:** 39 (Phase 39 confirmed). **Parallel to Rail B** (no dependency on X1/X2/X3); reading-list discipline for `identifiers.py` overlap with Phase 40.
  **Layer(s):** L2 only (`L2Schema(Schema)` subclass placement per ADR-0153 §amendment-1 — L1 `mindsos_core.Schema` stays primitive; L1 amendment from pre-R0 framing was reversed).
  **Net-new code?:** Yes. 4 new schema files (`parameter_staging.py`, `pending_promotions.py`, `capacity_gaps.py`, `learned_parameters.py`); `_base.py` NEW (Discipline + StorageMode + L2Schema subclass); `validate_mutation_discipline` + `validate_partition_invariant`; `MutationDisciplineError`; 4 new IRI builders + ROLE_* constants; bootstrap `applies_after` field declarations; `KnowledgeLayer.discipline_for` + dispatch cache; `KLWriteHandle.write_and_validate` admin_authored enforcement; episodic_memories body finalize (Episode + Memory + `MEMORY_CONTAINS_EPISODE` EdgeType); `tools/check_phase_43_confidence_state.py` detector.

  **Locked decisions (as shipped):**
  - **ADR-0151 / 0152 / 0153 IMPLEMENTED (Accepted on disk pre-Phase-43 per R0a-3).** Phase 43 implements the contracts; does NOT re-ratify (NPB6-3).
  - **ADR-0153 §amendment-1 (NEW).** L2Schema(Schema) subclass placement at `mindsos_knowledge.schemas._base` supersedes §6 L1 `mindsos_core.Schema` framing (R0 N4 probe + PB-43-6 + R0a-10).
  - **ADR-0150 §amendment-5 (NEW).** 4 new role-graphs (parameter-staging Local; pending-promotions Local+Global; capacity-gaps Global; learned-parameters Local+Global) + 5-item exclusion list. Closed role-set: 8 → 12 named + alignment-prefix.
  - **ADR-0094 §amendment-1 in-place edit** — Migration of shipped state text: "maintenance migrator" → "detector form" (`tools/check_phase_43_confidence_state.py`) per R0 PB-43-10. V1 production has no confidence-carrying Pipeline records; detector form per Phase 39 PB-8 precedent.
  - **ADR-0151 frontmatter Related block** — promotes ADR-0152 + ADR-0153 from Proposed to Accepted (both already Accepted on disk per R0a-3).
  - **ADR-0143 §Implementation references** — appends ADR-0153 §2 cross-ref noting KLWriteHandle write-path body fills with mutation-discipline enforcement.
  - **6 disciplines per ADR-0153 §1** (not 5 — `append_only` added per R0a-4/S3 for problem-trace).
  - **`storage_mode` is per-NodeType property** (not per-role-graph). Only `LearnedParameter.value` carries large-payload declaration in Phase 43 scope per ADR-0152 §6 + NPB8-1.
  - **`bootstrap.py` field-only at Phase 43.** `applies_after: frozenset[str] = frozenset()` kwarg added on both `ensure_*_role_graph` functions; `_APPLIES_AFTER_BY_ROLE` dict declares 12 role dependencies (soft edge `episodic_memories ← {task-patterns}` per NPB6-6); Kahn topological-sort scheduler defers to Phase 44 per L2-37 split (NPB11-1).
  - **`consolidate.py` retarget at Phase 43** (R0 PB-43-9). `type_="Memory"` → `type_="Episode"`; `memory_id` → `episode_id`; NOTE(phase-48-retarget) comments removed. Memory NodeType remains in schema for future composite-consolidation flow (Phase 48+); `consolidate:mm` now writes Episodes per Chat B D-B47.
  - **`promoted-pipelines.confidence` DROPPED** from schema v2 per ADR-0094 §am-1; v1 production state is empty per PB-43-10. Migrates to ALS subsystems on `learned-parameters` (subsystem #3 selection + #4 mapping).
  - **`task-patterns` flat 13-field schema** (originally framed as "flat 9-field" at L2-chat closure; 13 = 11 listed + 2 timestamps per ADR-0152 §2). Phase 43 PR1 commit 7 reconciles D-L2-10 title.
  - **`episodic_memories` body finalized.** Episode (6 content + 0 metadata) + Memory (1 content + 3 metadata) + `MEMORY_CONTAINS_EPISODE` EdgeType (R6: shipped as regular EdgeType not IntergraphEdgeType — both NodeTypes in same role-graph per Chat B D-B47; ADR-0152 §7 IntergraphEdge nomenclature reconciled in design log §9.1).
  - **`memory_contains_episode` edge form** is regular EdgeType (Memory → Episode within `episodic_memories` Schema). MetagraphSchema-level IntergraphEdgeType reconsideration deferred to Phase 48+ if cross-role-graph use case surfaces.

  **Modules touched (as shipped):**
  - `mindsos_knowledge/schemas/_base.py` (NEW; Discipline + StorageMode + L2Schema(Schema) subclass).
  - `mindsos_knowledge/schemas/parameter_staging.py` (NEW; StagedEvidence; MUTABLE_WITH_RETENTION).
  - `mindsos_knowledge/schemas/pending_promotions.py` (NEW; PendingPromotion; AUDIT_ONLY_AFTER_SETTLED).
  - `mindsos_knowledge/schemas/capacity_gaps.py` (NEW; CapacityGap; MUTABLE_WITH_RETENTION).
  - `mindsos_knowledge/schemas/learned_parameters.py` (NEW; LearnedParameter; per-scope discipline split via `scope` kwarg; STORAGE_MODE_FIELDS map).
  - `mindsos_knowledge/schemas/{ontology,lexicon,concepts,alignment,capacity_state,problem_trace,promoted_pipelines,task_patterns,episodic_memories}.py` (9 schema audits; each `Schema(...)` → `L2Schema(mutation_discipline=Discipline.X, ...)`; promoted_pipelines + task_patterns + problem_trace get CONTENT_FIELDS + METADATA_FIELDS partition frozensets; promoted_pipelines drops `task_type` + `confidence`; task_patterns renames `task_type` → `pattern_name`; episodic_memories body finalized).
  - `mindsos_knowledge/schemas/__init__.py` (dispatch table grows 8→12; L2-private vocabulary re-exports).
  - `mindsos_knowledge/identifiers.py` (4 new ROLE_*; 4 new IRI builders; 4 new prefix entries; 4 new `_KINDS_PER_ROLE` rows; 4 new `_IRI_BUILDERS` tuple-key registrations).
  - `mindsos_knowledge/validators.py` (`validate_mutation_discipline` + `validate_partition_invariant` per ADR-0153 §3).
  - `mindsos_knowledge/exceptions.py` (`MutationDisciplineError` per ADR-0153 §5; multi-inherits KnowledgeError + ValueError).
  - `mindsos_knowledge/bootstrap.py` (`_GLOBAL_NAMED_ROLES` 6→9, `_LOCAL_NAMED_ROLES` 2→5, `_APPLIES_AFTER_BY_ROLE` 12 declarations, `applies_after` kwarg field-only).
  - `mindsos_knowledge/knowledge_layer.py` (`discipline_for` + lazy per-Metagraph dispatch cache per ADR-0153 §2).
  - `mindsos_knowledge/write_handle.py` (`write_and_validate` admin_authored discipline check + `_is_admin` bypass; raises `MutationDisciplineError` on admin_authored writes without flag).
  - `mindsos_knowledge/__init__.py` (re-exports 4 new ROLE_* + 4 new IRI builders + 4 new schema builders + Discipline + L2Schema + StorageMode + MutationDisciplineError).
  - `mindsos_capacity/builtins/consolidate.py` (retarget: type_="Memory" → "Episode"; memory_id → episode_id; NOTE(phase-48-retarget) comments removed; module docstring + DataState description updated).
  - `tools/check_phase_43_confidence_state.py` (NEW detector per R0 PB-43-10 + ADR-0094 §am-1).
  - `docs/decisions/adr/0150-l2-knowledge-lifecycle.md` (§amendment-5 NEW per IL-3 split).
  - `docs/decisions/adr/0153-l2-mutation-discipline.md` (§amendment-1 NEW; L2Schema(Schema) placement).
  - `docs/decisions/adr/0094-confidence-pipeline-level.md` (§am-1 in-place: migrator → detector).
  - `docs/decisions/adr/0151-l2-storage-tiers.md` (frontmatter Related block: 0152/0153 promoted Proposed → Accepted).
  - `docs/decisions/adr/0143-kl-write-handle-pattern.md` (§Implementation references appends ADR-0153 §2 cross-ref + stale ROLE_MEMORIES example cleanup).
  - `docs/decisions/adr/{0045,0139,0146,0147,0154}.md` (stale ROLE_MEMORIES / memory_iri / `memories-` example cleanup per Phase 39 PB-R1-A carry-forward).
  - `confirmation_docs/L2_CHAT_DECISIONS.md` (D-L2-3 cascade L1→L2 placement note + 6th discipline append_only row + capacity-gaps reassigned admin_authored→mutable_with_retention; D-L2-4 Pipeline partition paired_pipelines removed + pipeline_name + quarantine_threshold added; D-L2-10 title 9-field→13-field + canonical count note).
  - `tests/phase_13/test_dispatch.py` (`_ALL_NAMED_ROLES` 8→12; sentinel `len == 8` → `== 12`).
  - `tests/phase_13/test_advisory_property_constants.py` (Pipeline + TaskPattern v2 expected fields + negative regression guards).
  - `tests/phase_33/test_consolidate_mm_capacity.py` (5 line changes: `memory_id` → `episode_id` fixture keys + IRI literal `:memory:` → `:episode:`).
  - `tests/phase_43/` 9 NEW test files (test_4_role_graphs + test_mutation_discipline_runtime_invariant + test_storage_mode_field + test_bootstrap_applies_after + test_confidence_detector_script + test_episodic_memories_completion + test_promoted_pipelines_v2 + test_task_patterns_v2 + test_consolidate_retarget) + PR1 sentinel suite (test_l2schema_subclass + test_validate_mutation_discipline + test_partition_invariant + test_adr_amendment_sentinels + `__init__.py`).
  - `mindsos_cli/manifest.toml` + `pyproject.toml` + `docker-compose.yml` + 7 package `__init__.py` `__version__` + 3 export_slate test files (9-surface manifest bump per Phase 39 §9.4).

  **Confirmation command:**
  `mindsos confirm-phase --phase 43 --notes-file confirmation_docs/notes/notes-phase-43.md`

  **Pass criterion (achieved):**
  - All Phase 43 tests green + cumulative gate green (PR1: 3544 / 0 / 8; PR2: filled at confirm).
  - 2 ADR amendments shipped + 4 ADR in-place edits + 6 stale-example ADR cleanups + 3 L2_CHAT_DECISIONS sub-decision cleanups.
  - `KnowledgeLayer.discipline_for(metagraph, role)` returns expected discipline for 9 Global + 5 Local roles.
  - `KLWriteHandle.write_and_validate` raises `MutationDisciplineError` on `admin_authored` without `_is_admin=True`.
  - `tools/check_phase_43_confidence_state.py` runs idempotently (exit 0 on clean; exit 1 on findings; mocked detector tests pass).
  - `bootstrap.py` declarations cover all 12 named role-graphs; soft edge `episodic_memories ← {task-patterns}` per NPB6-6.

  **Doc sections this phase confirmed:**
  - 2 NEW ADR amendments + 4 ADR in-place edits + 6 stale-example ADR cleanups.
  - `docs/concepts/role-graphs.md` (4 new role-graph descriptions + cross-ref to mutation-discipline + storage-tiers).
  - `docs/concepts/mutation-discipline.md` (NEW; 6-discipline framework + L2Schema subclass + dispatch table).
  - `docs/concepts/storage-tiers.md` (NEW; 3 tiers + per-NodeType storage_mode + v1 consumers).

  **Breaking changes from prior phase:**
  - **`promoted-pipelines` schema:** `confidence` field removed; consumers reading it break.
  - **`task-patterns` schema:** 4 new fields (`sufficient_predicate_iri`, `domain`, `relevant_hints`, `mapping_confidence_threshold`, `provenance`, `routing_override`); additive; consumers writing v1 records pass new fields.
  - **`Schema` class:** gains `mutation_discipline` field; existing schemas need one-line declaration to opt out of the default.
  - **L4 startup invariant:** `KnowledgeLayer.bootstrap()` raises on schemas missing discipline declaration in strict mode.

---

### Phase 44 — L0 substrate: persisters + KL surface + bootstrap completion + audit

  **Status:** Pending
  **Branch:** phase-44
  **Tag on confirm:** phase-44-confirmed
  **Rail:** C
  **Depends on:** 38 (Phase 38 confirmed) + **L0_SUBSTRATE_CHAT** closure (settles KL surface design + persister Cypher contracts + audit constant roster). **Parallel to Rails A/B** under DAG.
  **Layer(s):** L0 + L2 (KL surface).
  **Net-new code?:** Yes — `FalkorDBLocalPersister` + `SQLiteLocalPersister` (~200-400 LOC + Cypher contracts + ADR); Falkor-backed L3 bootstrap (~80-120 LOC); `kl.read_at_version` + `kl.retire_version` (per L0_SUBSTRATE_CHAT scope); audit constant + capability; PHASE_38 §4 #2 + #3 absorbed here per R3 PB-U.

  **Locked decisions (this map):**
  - **`FalkorDBLocalPersister` + `SQLiteLocalPersister` ship** — completes Phase 25 partial ship (`InMemoryLocalPersister` only). Per L0_SUBSTRATE_CHAT design.
  - **Falkor-backed L3 bootstrap + state-file serialization** wires `bootstrap_kl_from_falkordb` (Phase 26a) into `_construct_invoke_layer` with reachability probe + in-memory fallback (PHASE_38 §4 #2; L3_FUTURE_WORK L3-17).
  - **`kl.read_at_version(iri, version)`** ships (Phase 11 side-by-side graphs surface) per Chat B D-B14 + L0_FUTURE_WORK L0-21.
  - **`kl.retire_version(role, version)`** operation hook triggers lazy-inline marker; distinct from `kl.deprecate_version()` flagging. Per Chat B D-B2 + L0_FUTURE_WORK L0-22.
  - **`applies_after: frozenset[IRI]`** field on bootstrap importer registration (Phase 43 ships the field; Phase 44 wires consumer + scheduler).
  - **`EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY`** audit constant + **`READ_OTHER_LOCAL_EPISODIC_MEMORY`** capability per L2_CHAT_DECISIONS D-L2-23 (Local-Persister-side wire-up).
  - **Per-user Local-scoped `ProblemTraceSink` dict** per PHASE_38 §4 #6.
  - **Phase 24-related FK-NOT-NULL audit constants** stay closed at Phase 25 ship; no new constants here.

  **Features in scope:**
  - `FalkorDBLocalPersister` + `SQLiteLocalPersister` impls per `LocalPersister` Protocol (Phase 25 ship).
  - Falkor-backed L3 bootstrap (state-file serialization + reachability probe + fallback).
  - KL surface extension: `kl.read_at_version` + `kl.retire_version`.
  - Audit constant + new capability roster (ADMIN_CAPS 9 → 10; default-user-role gets `READ_OTHER_LOCAL_EPISODIC_MEMORY` opt-in per admin policy).
  - Per-user `ProblemTraceSink` dict.
  - Lazy-inline-on-retire marker consultation on episode read.

  **Modules touched:**
  - `mindsos_server/persistence/local_persister.py` (FalkorDBLocalPersister + SQLiteLocalPersister classes).
  - `mindsos_server/persistence/bootstrap.py` (Falkor-backed L3 bootstrap wire-up).
  - `mindsos_cli/commands/capacity.py` (`_construct_invoke_layer` wires Falkor-backed bootstrap).
  - `mindsos_knowledge/knowledge_layer.py` (`read_at_version` + `retire_version` methods).
  - `mindsos_server/audit.py` (`EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` constant).
  - `mindsos_server/auth.py` (`READ_OTHER_LOCAL_EPISODIC_MEMORY` capability roster; ADMIN_CAPS bump).
  - `mindsos_capacity/problem_trace.py` (per-user Local-scoped sink dict).
  - `docs/decisions/adr/0160-l0-persister-impls.md` (NEW; ratified at L0_SUBSTRATE_CHAT closure or Phase 44 R0).
  - `docs/decisions/adr/0161-kl-version-read-and-retire.md` (NEW; ratified).
  - ADR-0040 §amendment-N + ADR-0011 §amendment-N (incremental persister contract amendments per L0_SUBSTRATE_CHAT).

  **Automated tests:**
  - `tests/phase_44/test_falkor_persister.py` — Falkor-backed Local read/write/migration cycle.
  - `tests/phase_44/test_sqlite_persister.py` — SQLite-backed Local read/write/migration cycle.
  - `tests/phase_44/test_falkor_bootstrap.py` — reachability probe + in-memory fallback.
  - `tests/phase_44/test_kl_read_at_version.py` — Phase 11 side-by-side graphs surface; version-pinned reads.
  - `tests/phase_44/test_kl_retire_version.py` — lazy-inline marker fires on retire; consumer-side consultation on read.
  - `tests/phase_44/test_episodic_audit_constant.py` — `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` emitted; distinct from `EVT_READ_OTHER_LOCAL`.
  - `tests/phase_44/test_capability_roster.py` — `READ_OTHER_LOCAL_EPISODIC_MEMORY` cap present; admin grant + default-deny.
  - `tests/phase_44/test_problem_trace_sink.py` — per-user Local-scoped dict; isolation across users.
  - `tests/phase_44/test_adr_amendment_sentinels.py` — anchors ADR-0160 + ADR-0161 + amendments; chain link from Phase 38 (Rail C chain root).

  **Confirmation command:**
  `mindsos confirm-phase --phase 44 --notes-file notes-phase-44.md`

  **Pass criterion:**
  - All Phase 44 tests green + cumulative.
  - Both persisters round-trip Local content through fresh sessions.
  - `kl.read_at_version` returns correct historical content; `kl.retire_version` triggers lazy-inline.
  - Audit log carries `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` for cross-user episode reads; not for capacity-state reads.
  - L0_SUBSTRATE_CHAT closure record on disk + ADRs ratified.

  **Risks / known issues to watch:**
  - **`L0_SUBSTRATE_CHAT` closure quality** is load-bearing; Phase 44 R0 verifies design saturation before impl.
  - **Falkor Cypher contract** correctness; Falkor multi-statement transactions don't atomicize.
  - **Schema-v3-to-v4 + v4-to-v5** migration if persister-side schema diverges from Phase 24 baseline.
  - **PB-T:** L0-admin-surface items (audit constants for ALS events, scheduler infra, HITL channel) do NOT ship here; they route to WSD installation chat scope.

  **Doc sections this phase confirms:**
  - 2 new ADRs (persister impls + KL version surface).
  - `docs/concepts/persistence.md` (amendment with L0 persister roster).
  - `docs/dev/kl-version-surface.md` (NEW; `read_at_version` + `retire_version` API).

  **Breaking changes from prior phase:**
  - **Capability roster:** ADMIN_CAPS 9 → 10; user-role default unchanged.
  - **Persister contract:** Phase 25 `InMemoryLocalPersister`-only assumption broken; consumers may now select persister; default-selection lives in `mindsos doctor` + bootstrap layer.

---

### Phase 45 — L3 dream family ratification: 3 v1 capacities

  **Status:** Pending
  **Branch:** phase-45
  **Tag on confirm:** phase-45-confirmed
  **Rail:** D
  **Depends on:** 38 (Phase 38 confirmed) + **DREAM_FAMILY_CHAT** closure (settles 3 capacity bodies + execution policies + replan-injection mechanism + dream entry-point hookup). **Parallel to Rails A/B/C** under DAG.
  **Layer(s):** L3.
  **Net-new code?:** Yes — 3 dream capacity bodies + execution-policy contracts (per DREAM_FAMILY_CHAT scope).

  **Locked decisions (this map):**
  - **3 v1 dream capacities ship:** `dream.maintenance` (execution policy `replay_recorded`), `dream.exploration` (policy `re_execute_capacities`), `dream.retry` (policy `re_execute_capacities` with replan-injection). Per Chat B D-B6.
  - **Family contract inherited from L3-51** (per L1_L3_REFRAME_DECISIONS family batch): OPTIONAL_RETURN dont-know contract; `concurrent=True` default.
  - **Replan-injection mechanism** specifics deferred to DREAM_FAMILY_CHAT scope.
  - **Dream entry-point hookup** to L4 substrate's dream-cycle timer (Phase 46-shipped).
  - **`signal.plan_decomposition_outcome`** signal source (per Chat B D-B51) lives in L3-37 ALS family scope, not Phase 45 — ships when WSD installation lands ALS catalog.
  - **L3-51 ownership chat is THIS chat** (DREAM_FAMILY_CHAT) per PB-G; not a placeholder.

  **Features in scope:**
  - 3 dream capacity bodies registered in `mindsos_capacity/builtins/dream.py`.
  - Execution-policy contracts (`replay_recorded` vs `re_execute_capacities`).
  - L4 dream-cycle timer interface (consumed by Phase 46 substrate).
  - `dream_source_episode_iri` signal-payload provenance field.

  **Modules touched:**
  - `mindsos_capacity/builtins/dream.py` (NEW).
  - `mindsos_capacity/__init__.py` (register new builtins family).
  - `docs/decisions/adr/0162-l3-dream-family.md` (NEW; ratified at DREAM_FAMILY_CHAT closure or Phase 45 R0).

  **Automated tests:**
  - `tests/phase_45/test_dream_maintenance.py` — `replay_recorded` policy; pinned-state regression.
  - `tests/phase_45/test_dream_exploration.py` — `re_execute_capacities` policy; drift detection.
  - `tests/phase_45/test_dream_retry.py` — replan-injection on failed-episode re-execution.
  - `tests/phase_45/test_dream_signal_provenance.py` — `dream_source_episode_iri` tag on signals.
  - `tests/phase_45/test_adr_amendment_sentinels.py` — anchors ADR-0162; chain link from Phase 38 (Rail D chain root).

  **Confirmation command:**
  `mindsos confirm-phase --phase 45 --notes-file notes-phase-45.md`

  **Pass criterion:**
  - All Phase 45 tests green + cumulative.
  - 3 dream capacities registered + invokable.
  - Replan-injection mechanism executes per DREAM_FAMILY_CHAT spec.
  - ADR-0162 ratified.

  **Risks / known issues to watch:**
  - **DREAM_FAMILY_CHAT closure quality** is load-bearing.
  - L4 dream-cycle timer hookup deferred to Phase 46 substrate.
  - Phase 48 L5 ships the consolidation path + dream-as-live mechanism; Phase 45 ships the capacities only.

  **Doc sections this phase confirms:**
  - ADR-0162.
  - `docs/concepts/dream.md` (NEW; 3-pipeline catalog).

  **Breaking changes from prior phase:**
  - None.

---

### Phase 46 — L4 substrate: convergence point

  **Status:** Pending
  **Branch:** phase-46
  **Tag on confirm:** phase-46-confirmed
  **Rail:** convergence
  **Depends on:** 42 + 43 + 44 + 45 (all four rails closed).
  **Layer(s):** L4.
  **Net-new code?:** Yes — ~800-1200 LOC L4 substrate per Chat A R1 + ~100-200 LOC MM resolution+instantiation layer per Chat B D-B13 cascade. Total ~1000-1400 LOC + ADRs.

  **Locked decisions (per Chat A + Chat B foundations):**
  - **IntelligenceLayer lifecycle.** One per session. `start(session, knowledge=kl, capacity=cl)`, `stop(mode="abort")`, `enqueue(task)`. v1 ships `mode="pause"` as `NotImplementedError` (Push 5 defer).
  - **Custom priority-tier Executor (D32.5b).** 4 tiers (CRITICAL/FOREGROUND/BACKGROUND/DREAM); `PriorityQueue` keyed by `(tier, -attention_score, submit_time)`; `set_score` + `elevate` APIs; auto-preempt-on-elevation per D32.5c.
  - **Worker pool.** Default size `min(8, cpu_count())`; configurable per-deployment.
  - **MM RWLock per active MM** (D32.3); writer-preferred fairness.
  - **MM resolution+instantiation layer** per Chat B D-B13: IRI-namespace dispatch; lazy single-node; monotone-grow; pin-at-instantiation. ~100-200 LOC.
  - **Cooperative cancellation framework** (D32.5): `cancel_token` plumbing; `CancelTokenView` enforces read-only at body side.
  - **Signal-triage worker (D32.2 = A)** — always-on dedicated thread; classifies signals into 4 tiers; calls L3 `decision.signal_to_tier` capacity (skeleton at Phase 47).
  - **ALS subsystem registry** (D9.1) — registry dict; v0 empty (concrete subsystem catalog lands when WSD installation ships).
  - **MonitorSubscriptionRegistry** (per L1_L3_REFRAME_DECISIONS §D36): session-scope `Dict[DataState IRI, List[Monitor IRI]]`; consumes `cl.iter_monitors()` (Phase 41).
  - **L4 invariant locked: no shadow state outside MM** (Chat B D-B13).
  - **Three sub-MMs** per Chat B D-B10: knowledge-MM + capacity-MM + intelligence-MM; thin root with refs + `task_run_ref` + `ref:problem_trace` + `outcome_ref`.
  - **PB-AA physical-layout decision** (per PB-AAA routing): default = Chat B schemas as-written; benchmarks trigger composite-collapse only post-Phase-49 if needed.
  - **~6-8 new ADRs drafted at R0** ratifying Chat A + Chat B substrate picks: priority-tier Executor primitive (D32.5b), MM RWLock semantics, MonitorSubscriptionRegistry contract, three-sub-MM composition, MM resolution+instantiation layer, cooperative cancellation contract, signal-triage worker thread placement, attention-score-on-TaskRun.

  **Features in scope:**
  - IntelligenceLayer class + lifecycle methods.
  - Priority-tier Executor + worker pool.
  - MM RWLock + three-sub-MM container.
  - MM resolution+instantiation layer.
  - Cooperative cancellation framework.
  - Signal-triage worker thread.
  - ALS subsystem registry + per-subsystem dispatch hooks (empty catalog).
  - MonitorSubscriptionRegistry.

  **Modules touched:**
  - `mindsos_intelligence/` (NEW package skeleton — first L4 code).
  - `mindsos_intelligence/__init__.py`.
  - `mindsos_intelligence/intelligence_layer.py` (IntelligenceLayer class).
  - `mindsos_intelligence/executor.py` (priority-tier Executor).
  - `mindsos_intelligence/mm_resolver.py` (resolution+instantiation layer).
  - `mindsos_intelligence/cancellation.py` (cancel token framework).
  - `mindsos_intelligence/signal_triage.py` (signal-triage worker).
  - `mindsos_intelligence/als_registry.py` (subsystem registry).
  - `mindsos_intelligence/monitor_subscription.py` (MonitorSubscriptionRegistry).
  - `pyproject.toml` (declares `mindsos_intelligence` as installable package).
  - `~6-8 new ADRs` at `docs/decisions/adr/0163-*.md` through `0170-*.md` (numbered at R0).

  **Automated tests:**
  - `tests/phase_46/test_intelligence_layer_lifecycle.py` — start/stop/enqueue + abort semantics + NotImplementedError on pause.
  - `tests/phase_46/test_priority_tier_executor.py` — 4-tier ordering + within-tier score + auto-preempt-on-elevation.
  - `tests/phase_46/test_mm_rwlock.py` — reader/writer + writer-preferred fairness.
  - `tests/phase_46/test_mm_resolver.py` — lazy single-node + monotone-grow + IRI-namespace dispatch + pin-at-instantiation.
  - `tests/phase_46/test_cancellation_framework.py` — cooperative cancellation + `CancelTokenView` read-only enforcement.
  - `tests/phase_46/test_signal_triage_worker.py` — always-on thread + classification path.
  - `tests/phase_46/test_three_sub_mm.py` — knowledge/capacity/intelligence sub-MM root + cross-MM XRefs.
  - `tests/phase_46/test_monitor_subscription_registry.py` — session-scope registry + `cl.iter_monitors()` consumption.
  - `tests/phase_46/test_adr_amendment_sentinels.py` — anchors 6-8 new ADRs; chain link to converged Rails A+B+C+D.

  **Confirmation command:**
  `mindsos confirm-phase --phase 46 --notes-file notes-phase-46.md`

  **Pass criterion:**
  - All Phase 46 tests green + cumulative.
  - `mindsos_intelligence` package importable + smoke-runnable.
  - 6-8 new ADRs ratified.
  - No shadow state outside MM (invariant test).
  - IntelligenceLayer.start() + enqueue() + stop("abort") roundtrip on empty task.

  **Risks / known issues to watch:**
  - **Largest R0 in the map** (PB-BB sizing). Expect 4-6 R-rounds. Drafting 6-8 ADRs in one R0 is high cognitive load.
  - Phase 41 retired Monitor lifecycle from L3; Phase 46 implements MonitorSubscriptionRegistry on L4 side. Verify session-scope registry shape matches L1_L3_REFRAME_DECISIONS §D36 constraints.
  - **Triple-touch reading-list** for `consolidate.py` (Phase 39 + 42) — though Phase 46 substrate doesn't edit consolidate.py directly, L5 v1 (Phase 48) will, and Phase 46 R0 must verify consolidate-side surface stays compatible with the substrate.
  - L4 substrate ships without runnable Plan-execution (Phase 47 ships `planning.*` v0 catalog + orchestrator).

  **Doc sections this phase confirms:**
  - 6-8 new ADRs.
  - `docs/concepts/intelligence-layer.md` (NEW).
  - `docs/concepts/mm-substrate.md` (NEW).
  - `docs/dev/l4_intelligence_design_notes.md` (amend with Phase 46 ship reflection).

  **Breaking changes from prior phase:**
  - **New package `mindsos_intelligence`.** Additive at L4 level; no prior code touches.
  - **`mindsos doctor`** gains L4-substrate health checks (e.g., `mindsos_intelligence` package importable).

---

### Phase 47 — L4 orchestrator: six-phase task lifecycle + planning.* v0 + skeletons

  **Status:** Pending
  **Branch:** phase-47
  **Tag on confirm:** phase-47-confirmed
  **Rail:** convergence
  **Depends on:** 46.
  **Layer(s):** L4 + L3 (v0 catalog).
  **Net-new code?:** Yes — six-phase task lifecycle + attention queue control flow + replan-check dispatch + sufficient-predicate eval + 4 `planning.*` v0 capacities + 10 signal-source skeletons + 11 ALS subsystem skeletons (~600-900 LOC).

  **Locked decisions (per Chat A R1 + Chat B chain):**
  - **Six-phase task lifecycle** (D12). Lifecycle phase 1-6 per Chat A; concrete impl ships here.
  - **Phase 1 5-step refactor** (D32.5c.1 revised + Chat A R3 Method δ): receive → process → extract_hints → derive_goal → map_to_task_pattern.
  - **Phase 2 Plan + Pipeline construction** (D-B22 chain + D-B23 recursive tree of Milestones; cold-start max-depth=3 admin-tunable).
  - **Phase 3-5 execution** (DFS Milestone order; MSUR + SCMS shipped as L3 orchestration capacities by WSD installation).
  - **Phase 6 failure diagnosis** (D13) — `phase6.attribute_blame` capacity skeleton ships here; concrete body lands in WSD installation.
  - **Replan-check dispatch** (D-B36 + D14) — `decision.should_replan` invocation + ReplanRecord emit.
  - **Sufficient-predicate evaluator** (D41) — invokes L3 `predicate.sufficient` capacity.
  - **`planning.*` v0 placeholder catalog (PB-L)** — `derive_initial_plan` returns single-Milestone Plan; `decompose` returns []; `aggregate_outputs` returns last-child-output; `is_leaf` returns True.
  - **10 signal-source skeletons** registered (S1-S10 per Chat A R3 D9.2 + Chat B D-B51); empty payloads.
  - **11 ALS subsystem skeletons** registered (Chat A 10 + Chat B #11); empty mechanism + validator pointers (filled by WSD installation).
  - **TaskRun + PipelineRun + Plan + Milestone + HintSet + MappingResult + ReplanRecord + StepExecutionRecord composite emit** per Chat B chain (D-B22 through D-B37); intelligence-MM authoring.
  - **Attention-score-on-TaskRun** (D32.5c.4 amended per Chat B cascade).
  - **~3-5 new ADRs drafted at R0** ratifying Chat A R3-R5 picks: six-phase lifecycle, Phase 1 5-step refactor, replan-check verdict shape, sufficient-predicate dispatch.

  **Features in scope:**
  - Six-phase task lifecycle state machine.
  - Phase 1 5-step refactor implementation.
  - Plan + Pipeline construction in Phase 2.
  - DFS execution Phase 3-5.
  - Phase 6 failure diagnosis hookup.
  - Replan-check dispatch + ReplanRecord emit.
  - Sufficient-predicate evaluator.
  - 4 `planning.*` v0 placeholder capacities.
  - 10 signal-source registration skeletons.
  - 11 ALS subsystem registration skeletons.
  - Chain artifact composite emit to intelligence-MM (TaskRun + Plan + Milestone + HintSet + MappingResult + PipelineRun + ReplanRecord + StepExecutionRecord).

  **Modules touched:**
  - `mindsos_intelligence/orchestrator.py` (six-phase state machine).
  - `mindsos_intelligence/phase_1.py` (5-step refactor).
  - `mindsos_intelligence/plan_construction.py` (Phase 2).
  - `mindsos_intelligence/execution.py` (Phase 3-5).
  - `mindsos_intelligence/phase_6.py` (failure diagnosis).
  - `mindsos_intelligence/replan_check.py` (dispatch + ReplanRecord emit).
  - `mindsos_intelligence/sufficient_predicate.py` (evaluator).
  - `mindsos_capacity/builtins/planning_v0.py` (NEW; 4 placeholder capacities).
  - `mindsos_intelligence/signal_sources.py` (10 skeletons).
  - `mindsos_intelligence/als_subsystems.py` (11 skeletons).
  - `mindsos_intelligence/chain_artifacts.py` (composite emit for 8 chain types).
  - `~3-5 new ADRs` at `docs/decisions/adr/0171-*.md` through `0175-*.md` (numbered at R0).

  **Automated tests:**
  - `tests/phase_47/test_six_phase_lifecycle.py` — state-machine transitions; phase-to-phase invariants.
  - `tests/phase_47/test_phase_1_5_step.py` — 5 steps executed in order; HintSet + MappingResult emitted.
  - `tests/phase_47/test_plan_construction.py` — single-Milestone Plan from v0 catalog; recursive-tree shape.
  - `tests/phase_47/test_execution_dfs.py` — DFS Milestone execution order.
  - `tests/phase_47/test_phase_6_hookup.py` — failure diagnosis invocation pipeline.
  - `tests/phase_47/test_replan_check_dispatch.py` — `decision.should_replan` invocation + ReplanRecord emit on `replan` / `abort` verdicts.
  - `tests/phase_47/test_planning_v0_catalog.py` — 4 v0 capacities ship + are invokable.
  - `tests/phase_47/test_signal_skeletons.py` — 10 signal sources registered; empty payload contracts.
  - `tests/phase_47/test_als_skeletons.py` — 11 subsystems registered; empty mechanism pointers.
  - `tests/phase_47/test_chain_artifact_emit.py` — 8 chain composite types emitted to intelligence-MM.
  - `tests/phase_47/test_trivial_task_smoke.py` — end-to-end trivial task: enqueue + Phase 1-5 + L5 stub-consolidate + return outcome. (Real consolidation lands Phase 48; v0 catalog produces empty Plan → smoke covers control-flow only.)
  - `tests/phase_47/test_adr_amendment_sentinels.py` — anchors 3-5 new ADRs; chain link from Phase 46.

  **Confirmation command:**
  `mindsos confirm-phase --phase 47 --notes-file notes-phase-47.md`

  **Pass criterion:**
  - All Phase 47 tests green + cumulative.
  - 3-5 new ADRs ratified.
  - Trivial-task smoke runs end-to-end through orchestrator + v0 catalog.
  - `planning.*` v0 catalog explicitly marked as placeholder in capacity registration metadata; WSD installation chat replaces.

  **Risks / known issues to watch:**
  - **v0 catalog placeholder discipline** — WSD installation chat must atomically replace v0 with real catalog; v0 capacities must be clearly marked + invocation guard against accidental v1-prod use.
  - **6-phase lifecycle is complex** — risk of subtle state-machine bugs surfacing under replan + cancellation interactions.
  - **Chain artifact emit volume** — 8 composite types per task; verify intelligence-MM write throughput meets `attention_score`-driven priorities.

  **Doc sections this phase confirms:**
  - 3-5 new ADRs.
  - `docs/concepts/task-lifecycle.md` (NEW; six-phase walkthrough).
  - `docs/concepts/replan.md` (NEW).
  - `docs/concepts/planning.md` (NEW; planning.* family + v0 catalog disclosure).

  **Breaking changes from prior phase:**
  - None internally. `planning.*` v0 catalog is additive.

---

### Phase 48 — L5 v1: consolidation + dream hookup + retention monitoring + concepts docs

  **Status:** Pending
  **Branch:** phase-48
  **Tag on confirm:** phase-48-confirmed
  **Rail:** convergence
  **Depends on:** 47.
  **Layer(s):** L5 + L4 + L2 (consolidation crosses layers).
  **Net-new code?:** Yes — MM consolidation write path + Episode/Memory authoring + dream pipeline hookup + retention monitoring instrumentation + crash recovery (~400-700 LOC).

  **Locked decisions (per Chat B + IL-5 + PB-AA):**
  - **MM consolidation write path** (Chat B §4.2): L4 freezes MM at task complete + writes Episode entry to L2.`episodic_memories`. Per-completion default.
  - **Episode + Memory live schema usage** (Chat B D-B47 + L2_CHAT_DECISIONS D-L2-17): `task_input_ref`, `mm_root_ref`, `task_pattern_iri`, `outcome_classification`, `crash_marker`, `consolidated_at`; Memory composite materializes on first episode per task-pattern.
  - **`memory_contains_episode` IntergraphEdge** wiring (per Chat B D-B47 PB-VV + Phase 43 schema).
  - **Dream pipeline hookup** (Chat B §5.2) — L4 dream-cycle timer invokes Phase 45-shipped `dream.maintenance` / `dream.exploration` / `dream.retry` capacities; ALS signals fire per normal Chat A mechanics; `dream_source_episode_iri` provenance tag.
  - **D'1 retention model + lazy inline-on-retire** (Chat B §4.4): episode references stored as `(iri, version_int)` tuples; pinning at instantiation; lazy inline triggers on `kl.retire_version()` (Phase 44-shipped hook); inline content reads on next episode read.
  - **Episode immutability invariant** (Chat B §4.5): append-only externally; only internal mutation = lazy inline-on-retire.
  - **Memory composite Schema D-L2-15 lock** — `task_pattern_iri` primary cluster key; per-task-pattern materialization; `rejected_promotions` denormalized list with L0 audit-log as authoritative.
  - **Crash recovery (D-B50)** — checkpoint trigger set on LifecyclePhase transitions + per-Milestone completion + per-replan event; L4-startup scan for unconsolidated MMs + consolidate with `crash_marker` set.
  - **PB-AA storage retention policy (PB-QQ routing)** — v1 ships **monitoring instrumentation only**: episode-count + episode-size histogram + Falkor-row count exporters. Retention policy = v1.5 if growth observed.
  - **PB-V Stream C absorb** — Phase 48 ships `docs/concepts/layers.md` (L4 + L5 conceptual content) + `docs/concepts/society-of-mind.md` (L4/L5 framing) + `docs/getting-started/facts-and-figures.md` (reference tables now that L4/L5 has substance to reference).
  - **~3-5 new ADRs drafted at R0** ratifying Chat B picks: D'1 retention model, three-sub-MM composition, Episode immutability invariant, lazy inline-on-retire mechanism, dream-as-live + ALS-as-sole-learning-track.

  **Features in scope:**
  - MM consolidation write path (frozen-MM → Episode write).
  - Episode + Memory entry authoring at task complete.
  - `memory_contains_episode` IntergraphEdge wiring.
  - Dream pipeline hookup (timer invokes Phase 45 capacities).
  - D'1 retention model (version-IRI freeze + lazy inline-on-retire).
  - Crash recovery (checkpoint trigger set + L4-startup scan).
  - Retention monitoring instrumentation.
  - 3 docs pages (concepts/layers.md + society-of-mind.md + facts-and-figures.md).
  - `consolidate:mm` Phase 33 capacity body finalized to write new Episode + Memory entry shape (third touch on consolidate.py per PB-Q; reading-list discipline).

  **Modules touched:**
  - `mindsos_intelligence/consolidation.py` (NEW; MM-freeze + Episode write path).
  - `mindsos_intelligence/dream_cycle.py` (NEW; timer + capacity dispatch).
  - `mindsos_intelligence/retention.py` (NEW; lazy-inline marker consultation on episode read).
  - `mindsos_intelligence/crash_recovery.py` (NEW; checkpoint trigger + startup scan).
  - `mindsos_intelligence/monitoring.py` (NEW; retention monitoring exporters).
  - `mindsos_capacity/builtins/consolidate.py` (third touch; writes new Episode + Memory entry shape).
  - `mindsos_knowledge/schemas/episodic_memories.py` (rectified consumer paths).
  - `docs/concepts/layers.md` (NEW).
  - `docs/concepts/society-of-mind.md` (NEW).
  - `docs/getting-started/facts-and-figures.md` (NEW).
  - `~3-5 new ADRs` at `docs/decisions/adr/0176-*.md` through `0180-*.md`.

  **Automated tests:**
  - `tests/phase_48/test_consolidation_write_path.py` — task complete → Episode written to `episodic_memories`.
  - `tests/phase_48/test_memory_composite_materialization.py` — Memory composite materializes on first episode per task-pattern.
  - `tests/phase_48/test_memory_contains_episode_edge.py` — IntergraphEdge wired correctly.
  - `tests/phase_48/test_dream_pipeline_hookup.py` — dream-cycle timer invokes 3 Phase 45 capacities; signal provenance correct.
  - `tests/phase_48/test_d_prime_1_retention.py` — version-pinned tuples + lazy inline-on-retire.
  - `tests/phase_48/test_episode_immutability_invariant.py` — append-only externally; only mutation = lazy inline.
  - `tests/phase_48/test_crash_recovery.py` — checkpoint trigger fires; startup scan consolidates with crash_marker.
  - `tests/phase_48/test_retention_monitoring.py` — episode count + size + Falkor-row exporters.
  - `tests/phase_48/test_consolidate_capacity_v2.py` — Phase 33 capacity body writes new Episode + Memory entry shape.
  - `tests/phase_48/test_docs_pages_ship.py` — 3 new concepts docs present + rendered.
  - `tests/phase_48/test_adr_amendment_sentinels.py` — anchors 3-5 new L5 ADRs.

  **Confirmation command:**
  `mindsos confirm-phase --phase 48 --notes-file notes-phase-48.md`

  **Pass criterion:**
  - All Phase 48 tests green + cumulative.
  - 3-5 new ADRs ratified.
  - Task completion → Episode appears in `episodic_memories` Local role-graph.
  - Dream cycle invokes all 3 Phase 45 capacities under appropriate conditions.
  - Crash recovery: simulated crash + restart produces consolidated Episode with crash_marker.
  - 3 docs pages render under `mkdocs build --strict`.

  **Risks / known issues to watch:**
  - **`consolidate.py` triple-touch resolution** under DAG; Phase 48 R0 reading-list reads Phase 39 + Phase 42 + Phase 43 diffs.
  - **D'1 lazy inline-on-retire** is subtle — verify outgoing refs from inlined content also inline themselves on next read (bounded transitive inflation).
  - **Retention monitoring instrumentation** ships; retention policy doesn't. PB-QQ growth concern monitored, not acted on at v1.
  - **Dream pipeline + ALS signal interaction** — Phase 45 ships capacities; Phase 47 ships subsystem skeletons; Phase 48 wires them. End-to-end signal-to-learning-update chain not exercised until WSD installation lands real ALS mechanisms.

  **Doc sections this phase confirms:**
  - 3-5 new ADRs.
  - `docs/concepts/layers.md`.
  - `docs/concepts/society-of-mind.md`.
  - `docs/getting-started/facts-and-figures.md`.
  - `docs/concepts/episodic-memories.md` (amendment; Phase 39 ship was schema-shape only).
  - `docs/concepts/dream.md` (amendment; Phase 45 ship was capacity-only).

  **Breaking changes from prior phase:**
  - **`consolidate:mm` capacity body changes** (Phase 33 third touch). External capacity-body consumers update.
  - **L4 startup now scans for crash residue.** Adds bootstrap-time overhead; configurable per-deployment.

---

### Phase 49 — Integration C: end-to-end L0→L5 trivial-task scenario + cookbook

  **Status:** Pending
  **Branch:** phase-49
  **Tag on confirm:** phase-49-confirmed
  **Rail:** integration
  **Depends on:** 48.
  **Layer(s):** cross.
  **Net-new code?:** No (composes shipped pieces) — test fixture authoring + cookbook page + Falkor index decisions per PB-HHH.

  **Locked decisions:**
  - **Integration scenario:** L0 login (Phase 19) → L4 enqueue (Phase 47) → L4 task lifecycle Phase 1 → 5 (Phase 47) using planning.* v0 (Phase 47) → L3 invoke `text.tokenize` builtin (Phase 31) → mutation_discipline runtime invariant respects writes (Phase 43) → L4 writes through MM (Phase 46) → L5 consolidation at task complete (Phase 48) → Episode written to `episodic_memories` (Phase 39/43/48) → Falkor-backed persister flushes (Phase 44) → dream pipeline ran in background (Phase 45/48).
  - **`usage/cookbook/end-to-end.md` cookbook page ships** (PB-W; Phase 32 → text-realm.md precedent). Documents the integration scenario walk-through.
  - **PB-AA Falkor indexes (PB-HHH routing)** decided at Phase 49 R0: which cross-sub-MM hyperedge queries need indexes at scale; index definitions land in the cookbook page + an ADR if substantial.

  **Features in scope:**
  - End-to-end integration test fixture authoring (~100-200 LOC test scaffolding).
  - Cookbook page `usage/cookbook/end-to-end.md`.
  - Falkor index decisions + impl (per PB-HHH).
  - Outstanding Phase 38 §4 doc-item closures (#13 society-of-mind already in Phase 48; #14 per-page ADR cleanup absorbed by Phase 42; #15 dropped).

  **Modules touched:**
  - `tests/phase_49/integration_c.py` (NEW; full scenario harness).
  - `docs/usage/cookbook/end-to-end.md` (NEW).
  - `mindsos_server/persistence/indexes.py` or Falkor schema migration scripts (per PB-HHH decisions).

  **Automated tests:**
  - `tests/phase_49/test_integration_c_scenario.py` — full L0→L5 scenario; deterministic outcome.
  - `tests/phase_49/test_cookbook_page_renders.py` — `mkdocs build --strict` includes end-to-end.md.
  - `tests/phase_49/test_falkor_index_present.py` — verified Falkor indexes per PB-HHH decisions.
  - `tests/phase_49/test_adr_amendment_sentinels.py` — anchors any new index ADR; chain link from Phase 48.

  **Confirmation command:**
  `mindsos confirm-phase --phase 49 --notes-file notes-phase-49.md`

  **Pass criterion:**
  - Integration scenario completes end-to-end deterministically.
  - Cookbook page renders.
  - Falkor indexes (if any) ship; ADR ratified (if any).
  - Cumulative regression green.
  - `mkdocs build --strict` clean.

  **Risks / known issues to watch:**
  - **First end-to-end exercise of L4 + L5 substrate** — surfaces any cross-phase regression not caught in unit tests.
  - **`planning.*` v0 catalog limits scenario realism** — single-Milestone Plan; no real decomposition. Acceptable for substrate verification; not for feature-complete demo (WSD installation provides that).
  - **PB-QQ retention growth** observable here; monitoring instrumentation (Phase 48) exports first numbers.

  **Doc sections this phase confirms:**
  - `docs/usage/cookbook/end-to-end.md`.
  - Any Falkor-index ADR per PB-HHH.

  **Breaking changes from prior phase:**
  - None.

---

## 5. Stream A — pre-Phase-39 prerequisites + interleaved bug-fix PRs

Tracked in `_workbench/STREAM_A_BACKLOG.md`. Each item ships as a maintenance PR to `main`, out-of-band of any phase number. No `phase-N-confirmed` tag; no `mindsos confirm-phase` invocation.

**Pre-Phase-39 prerequisites (must land before Phase 39 branches):**

1. **PB-R `release.yml` retention amendment.** Change rule from "5 most-recent by tag-time" to "5 most-recent by `[mindsos] phase` integer." One-line `release.yml` edit + acknowledgment line in `mindsos confirm-phase` wrapper.

**Interleaved with Stream B phases (land any time):**

2. **PHASE_38 §4 #1 — `mindsos capacity invoke --session-token` CLI flag.** ~10 LOC + 4 failure-mode tests.
3. **PHASE_38 §4 #6 — Per-user Local-scoped `ProblemTraceSink` dict.** Originally L4-pointing; could absorb into Phase 44 R0 if scope expands. Default = Stream A PR.
4. **PHASE_38 §4 #7 — `--install-builtins=<family,...>` CLI flag.** Waits for second builtins family; defer until WSD installation lands.
5. **PHASE_38 §4 #8 — `handle.validate_xref` body** wires per ADR-0139 §am-1 clause 3.
6. **PHASE_38 §4 #9 — 1 remaining unconsumed validator** (`validate_local_to_global_ref`). May absorb into Phase 44 (first per-flow consumer).
7. **PHASE_38 §4 #17 — `concepts/promotion-bridge.md` Phase 24 amendment verification + backfill.**

Items #2 was IL-7-moved into Phase 39 scope. PHASE_38 §4 #2 + #3 absorbed into Phase 44 per R3 PB-U.

---

## 6. Downstream chat sequencing reservations

Per PB-A: this map produces sequencing + slot reservations only. Each downstream chat authors its own `<CHAT_NAME>_PHASE_MAP.md` after its design-resolution closes.

| Chat | Opens after | Closes before | Owns | Notes |
|---|---|---|---|---|
| **L0_SUBSTRATE_CHAT** | Chat C closure | Phase 44 R0 | Phase 44 design (persisters + KL surface + audit constants + capabilities) | Per PB-B + PB-O. Scope: ~6 surfaces; Chat-A-R3-equivalent saturation expected. |
| **DREAM_FAMILY_CHAT** | Chat C closure | Phase 45 R0 | Phase 45 design (3 v1 dream capacities + execution policies + replan-injection + dream entry-point hookup) | Per PB-E + PB-G. Scope: 2-3 R-rounds expected. |
| **SKILL_ACQUISITION_PROCESS_CHAT** | Phase 47 confirmed (substrate must exist before skill-install lifecycle saturates) | WSD installation R0 | Per-layer install lifecycle (skill = L1+L2+L3+L4+L5 artifacts as bundle); bundle integrity; Local vs Global tiers; conflict resolution; audit + provenance; de-installation | Per `projects/README.md` ordering + PB-H. Shared umbrella for WSD + FOL installations. |
| **WSD_INSTALLATION_CHAT** | SKILL_ACQUISITION_PROCESS_CHAT closure | First WSD `<phase>-confirmed` tag | WSD skill installation phase-map; absorbs L0 admin-surface items per PB-T (audit constants for ALS events, scheduler infra, HITL channel, capacity-gaps tooling, hint catalog tooling); replaces Phase 47 `planning.*` v0 with real catalog; ships ALS subsystems #1-#11 mechanism + validator catalogs; ships `process.*`, `predicate.*`, `hint.*`, `decision.*` catalogs; ships `world-axioms` role-graph; ships 6 new L2 importers (SemCor, OntoNotes, VerbNet, SemLink, GlossTag, FrameNet-extended); ratifies WSD-specific ADRs from `projects/wsd/source/pending_adrs/` | Per `projects/wsd/FUTURE_CHAT_PROMPT.md`. Scope is large — likely multi-chat sub-series. |
| **FOL_INSTALLATION_CHAT** | WSD_INSTALLATION_CHAT closure (inherits ratifications on shared propositions) | First FOL `<phase>-confirmed` tag | FOL skill installation phase-map; pluggable prover backends; many-sorted FOL with DOLCE sorts; epistemic-tag ledger; `training-runs` role-graph (if FOL pushback #5 accepted); plural-strategies; external blob store for model artifacts (FOL pushback #8); typed `CapacityContext` family extensions; `learned-parameters` 3-way split (if FOL pushback #4 accepted) | Per `projects/fol/FUTURE_CHAT_PROMPT.md`. Inherits all WSD picks on shared blockers. |
| **DWF_INSTALLATION_CHAT** | Chat C closure (parallelizable with skill-acquisition since DWF is L2-only) | First DWF `<phase>-confirmed` tag | Knowledge-acquisition process design + DWF installation; `AlignmentsImporter` body + alignment role-graph ingestion (104,728 OEWN↔DOLCE rows + 38,998 OEWN↔FrameNet mappings); per-edge `confidence` + `method` + `provenance` properties on alignment edges; inherits `alignment:<a>:<b>` canonical from Phase 39 | Per `projects/dwf_mapping/FUTURE_CHAT_PROMPT.md`. Independent of L4/L5; can run parallel with Phase 39+. |
| **ADAPTER_FAMILY_CHAT** | Per-cross-realm pattern need (first consumer triggers) | First adapter-shipping phase | `adapter.*` family + concrete bridge DataState registrations; cross-realm transformations (e.g., `adapter.question_decompose_to_code_search_spec` for UC-X-1) | Per L1_L3_REFRAME_DECISIONS L3-49. Standard L3 contract; not structurally distinct. |
| **CODE_SKILL_INSTALLATION_CHAT** | WSD_INSTALLATION_CHAT closure | First code-skill `<phase>-confirmed` tag | `code` realm DataState catalog; `process.code.*` capacities; `code.ast_parse`, `code.identifier_split`, `code.call_graph_walk`, `code.side_effect_detect`, `code.module_find`, `code.symbol_resolve`; `generation.code_*` patch-generation; `nlu-slice.md` + `code-slice.md` cookbook pages | Per L3_FUTURE_WORK L3-28, L3-30, L3-31. Per `_workbench/cookbook_routing.md`. |
| **MAINTENANCE_CHAT** | Any | — | L0-17 simplified-execution-mode CLI flag; small L1/L2/L3 maintenance items not in Stream A | Per L0_FUTURE_WORK + L2_FUTURE_WORK + L3_FUTURE_WORK. |
| **L4-v2 follow-up chat** | Phase 49 confirmed (v1 baseline exists) | — | Cross-layer rewrite handler (L4-1); pause-and-resume (L4-2); coherence dream intent re-evaluation (L4-4); phase-loop as L3 orchestration (L4-6); `decision.preempt_target` learnable (L4-7); etc. | Per L4_FUTURE_WORK. |

**Recommended downstream ordering:**

```
Chat C (THIS chat) closure
   ├──► L0_SUBSTRATE_CHAT  ──► Phase 44 ship
   ├──► DREAM_FAMILY_CHAT ──► Phase 45 ship
   ├──► DWF_INSTALLATION_CHAT  (parallel; L2-only; independent of L4/L5)
   └──► Stream B converges at Phase 46
              │
              └──► Phase 49 confirmed
                       │
                       ├──► SKILL_ACQUISITION_PROCESS_CHAT
                       │       │
                       │       ├──► WSD_INSTALLATION_CHAT
                       │       │       │
                       │       │       ├──► FOL_INSTALLATION_CHAT
                       │       │       └──► CODE_SKILL_INSTALLATION_CHAT
                       │       │
                       │       └──► ADAPTER_FAMILY_CHAT (as triggered)
                       │
                       └──► L4-v2 follow-up chat
                       │
                       └──► MAINTENANCE_CHAT (any time)
```

---

## 7. Open questions

No architectural-level open questions exit Chat C. The following items remain — all routed:

| # | Question | Routed to |
|---|---|---|
| q1 | Worker pool size default (`min(8, cpu_count())`) — appropriate per deployment? | Phase 46 R0 (impl detail) |
| q2 | Falkor index strategy for cross-sub-MM hyperedge queries | Phase 49 R0 (PB-HHH) |
| q3 | Episode retention policy v1.5 triggers (PB-QQ) | Post-Phase-48 monitoring; v1.5 chat if observed growth |
| q4 | `planning.*` v0 → real catalog migration discipline | WSD_INSTALLATION_CHAT |
| q5 | ALS subsystem #1-#11 mechanism + validator catalogs | WSD_INSTALLATION_CHAT |
| q6 | L4-v2 multi-tenant rewrite handler shape | L4-v2 follow-up chat |
| q7 | `learned-parameters` 3-way split (FOL pushback #4) | FOL_INSTALLATION_CHAT |
| q8 | Note-fork mechanism revival? | Closed — Chat B D-B1 retired permanently; no future trigger anticipated |
| q9 | Skill-acquisition process: per-layer dependency ordering + audit + de-installation | SKILL_ACQUISITION_PROCESS_CHAT |

---

## 8. Closure summary

Chat C plan-authoring closes 2026-06-02. Saturation pattern: R5 produced impl-locks only; R6 confirmed (Phase 38 R6 precedent — post-design execution-time pass). Three consecutive reversal-free rounds = ship-ready per HANDOFF §9.

**Architectural commitments locked by this map:**
- **DAG execution** (4 rails + convergence + integration); 11 phase slots Phases 39-49.
- **Stream A** as in-repo bug-fix-PR index; 7 items (post-IL-7).
- **Stream C** absorbed into Phase 48 (concepts/layers + society-of-mind + facts-and-figures); PHASE_38 §4 #15 dropped.
- **`release.yml` retention amendment** as pre-Phase-39 prereq.
- **Per-phase R0 reading-list discipline** for predictable file-collision surfaces.
- **`planning.*` v0 placeholder catalog at Phase 47**; WSD installation atomically replaces.
- **3 docs pages absorb into Phase 48** (concepts/layers + society-of-mind + facts-and-figures).
- **Integration C at Phase 49** with `usage/cookbook/end-to-end.md`.
- **Phase 27 audit deliverable** at Phase 42 (X3 R0 bundled).
- **ADR-0150 amendment split** §am-4 (Phase 39 rename row) + §am-5 (Phase 43 4-new-role-graphs).
- **L0_SUBSTRATE_CHAT + DREAM_FAMILY_CHAT** named as Stream B rail prerequisites.
- **WSD/FOL/DWF/skill-acquisition/code-skill/adapter** chats sequenced; phase-maps authored downstream.

**Items dissolved at Chat C closure:**
- PB-11 ship-shape default discipline (zero triggers in map).
- `[mindsos_plan]` manifest namespace field (no collisions arise).
- Separate L0_ADMIN_SURFACE_CHAT (admin-surface items absorb into WSD installation per PB-T).

**Closure handoff:**
- This document is canonical.
- Each downstream chat reads HANDOFF.md + this map + its own FUTURE_CHAT_PROMPT.
- All `_workbench/L*_FUTURE_WORK.md` files remain live (open items routed; closure markers appended).
- Closed-class decision logs (CHAT_A_DECISIONS, CHAT_B_DECISIONS, L1_L3_REFRAME_DECISIONS, L2_CHAT_DECISIONS, CHAT_A_L4_BASELINE, CHAT_PLAN_L4_L5) migrate to `confirmation_docs/` at Chat C closure.
- `_workbench/NEXT_CHAT_PROMPTS.md` migrates to `_archive_Layered_Intelligence/` (forensic-only).

---

*End of POST_PHASE_38_PHASE_MAP.md. Last reviewed 2026-06-02 (Chat C closure). Update when any Phase 39-49 ships, when an open question resolves, or when a downstream chat opens.*
