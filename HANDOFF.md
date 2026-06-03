# MindsOS — HANDOFF

> **Last updated:** 2026-06-02 end-of-day (Phase 43 pre-R0 design pass closed; locked picks at `confirmation_docs/PHASE_43_R0_PICKS_SEED.md`; R0b derivations at `confirmation_docs/PHASE_43_R0B_DERIVATIONS.md`; **S9 blocker surfaced** — post-Phase-38 corpus is uncommitted on `main`; A0 housekeeping commit checklist at `confirmation_docs/A0_HOUSEKEEPING_COMMIT_CHECKLIST.md` must land before Phase 39 impl branches. Earlier same day: Phase 39 design pass closed; Chat C plan-authoring closed. See §3.1.9.)
> **Audience:** Any chat, contributor, or reviewer entering MindsOS. This is the canonical entry point — read it first.
> **Self-contained:** This document does not require loading external memory entries to make sense. Inline content is authoritative. Memory entries referenced as `[[name]]` are speed-ups for chats that have memory access; the canonical text lives here.

═══════════════════════════════════════════════════════════════════════
## 0. How to use this document

This handoff is the single source of truth for **what is true about MindsOS as of 2026-05-28**. It supersedes all earlier handoff documents (`mindsos_intelligence_handoff_current.md`, `mindsos_intelligence_handoff.md`, `mindsos_future_plans.md`, `system_overview_2026-04-26.md`, `l4_session_handoff_2026-04-25.md`). Those originals are archived in `_archive_Layered_Intelligence/_source_backup/root/` if needed for forensics.

The companion documents that future chats should also read are named in §10.

═══════════════════════════════════════════════════════════════════════
## 1. Quick orientation — what is MindsOS, and what state is it in?

**MindsOS** is a 5-layer intelligence system built on FalkorDB metagraphs. The 5 layers:

- **L0 — Server.** Auth, sessions, capability-based authorization, audit, persistence orchestration. Orthogonal to the L1-L5 composition axis. **Shipped.**
- **L1 — Core (`mindsos_core`).** Graphs, metagraphs, nodes, edges, hyperedges, schemas, persistence primitives. No reasoning. **Shipped.**
- **L2 — Knowledge (`mindsos_knowledge`).** A metagraph where each contained graph is a role: `ontology`, `lexicon`, `concepts`, `alignment:*`, `memories` (pending rename → `episodic_memories` per Chat B D-B48), `promoted-pipelines`, `task-patterns`, `problem-trace`, `capacity-state`. Global + per-user Local. **Shipped.**
- **L3 — Intellectual Capacity (`mindsos_capacity`).** Fixed-not-learned algorithms organized into functional categories. **Shipped.**
- **L4 — Intelligence.** Per-session orchestrator, learner, attention queue, dreaming, replan, promotion proposing. **In design — contested.**
- **L5 — Mental Model.** Per-task metagraph instances; the system's working memory. **Settled — Chat B closed 2026-05-31.** No longer gated on note-fork (retired); ships independent of server-pivot v2.

**Plus:**
- `mindsos_admin` — admin importers (DOLCE, OEWN, FrameNet), promotion machinery, audit gate.
- `mindsos_instances` — instance vocabulary (`ElementInstance`, `CompositeInstance`).
- `mindsos_cli` — Typer CLI surface.
- `mindsos_server` — server layer (auth, sessions, audit, persister).

**Current operating mode (2026-06-02 end-of-day):**
- **PHASE-NUMBERED CODE-SHIPPING ACTIVE.** 11 phase slots reserved Phases 39-49 per `confirmation_docs/POST_PHASE_38_PHASE_MAP.md`.
- **S9 BLOCKER RESOLVED 2026-06-02.** A0 housekeeping (4 commits A0-1…A0-4) + Stream A items A9 + A1 all landed on `main`. `main`-tip = `f33db02`; tagged `a0-corpus-landed`. Pre-A0 baseline retained at tag `pre-a0-backup` (`5236857`). Cumulative gate result: 3429 passed / 8 skipped / 0 failed (Linux docker pytest); `mkdocs build` clean (~15 broken-link warnings, no errors). See §3.1.10 for the landing chat's incidental surface findings (Dockerfile drift, missing `docs/dev/internals/knowledge.md` vendor, stale `tests_server/` layer-isolation roster — all resolved). **Phase 39 hard prereqs from `PHASE_39_NEXT_CHAT_PROMPT.md` are now satisfied; `phase-39` can branch off `main`-tip.**
- **Phase 39 SHIPPED 2026-06-02.** Rail A slot 1. ADR-0044 §amendment-3 + ADR-0150 §amendment-4 (narrowed rename-only) + ADR-0146 §amendment-3 (multi-NodeType dispatch + `_IRI_BUILDERS` tuple-key + `mint_iri(type_, **content)` signature) shipped on disk. L2 `memories` → `episodic_memories` atomic rename across 38 source + test + docs files. L2-35 alignment reconciliation (`<->` → `:`). `tools/check_rename_state.py` Falkor detector. `tests/phase_39/` 7-file suite (sentinel chain root, no SKIP). Cumulative gate: 3501 passed / 8 skipped / 0 failed. See `confirmation_docs/PHASE_39_DESIGN_LOG.md` for the design closure and `confirmation_docs/PHASE_39_CONFIRMED.md` for ship metadata.
- **Phase 43 pre-R0 design pass CLOSED 2026-06-02 end-of-day.** Settlement at `confirmation_docs/PHASE_43_R0_PICKS_SEED.md` (locked picks; drops C-γ, P1, P-meta, A6 from Phase 43 scope; N4 L2Schema subclass safe per probe; task_patterns.confidence kept) + `confirmation_docs/PHASE_43_R0B_DERIVATIONS.md` (R0b artifacts: `applies_after` edges from D-L2-19, ADR-0150 §am-5 draft text, L2Schema(Schema) sketch with discipline+storage_mode transcription table). Future Phase 43 chat opens post `phase-39-confirmed`; loads seed + derivations as primary R0 input; runs R1 impl-locks → tester loop. See §3.1.9.
- **Next chat is the Phase 43 impl chat** (Rail A slot 2, schema-v2). Hand it `confirmation_docs/PHASE_43_NEXT_CHAT_PROMPT.md` + `confirmation_docs/PHASE_43_R0_PICKS_SEED.md` + `confirmation_docs/PHASE_43_R0B_DERIVATIONS.md`. Phase 43 branches off `phase-39-confirmed` tag (post Phase 39 ship).
- **Chat A (L4 design-resolution) CLOSED 2026-05-28.** Settlement at `confirmation_docs/CHAT_A_DECISIONS.md` (migrated from `_workbench/`).
- **Chat B (L5 design-resolution + note-fork decision) CLOSED 2026-05-31.** Settlement at `confirmation_docs/CHAT_B_DECISIONS.md`. Revised L5 design notes at `docs/dev/l5_mental_model_design_notes.md`.
- **L2 chat (L2 schema-v2 + role-graph expansion + `episodic_memories` rename) CLOSED 2026-06-01.** Settlement at `confirmation_docs/L2_CHAT_DECISIONS.md`. New ADRs 0151-0154; amendments to ADR-0044 §3, ADR-0094 §1, ADR-0150 §4 (split to §am-4 + §am-5 per Chat C IL-3).
- **L1/L3 reframe chat CLOSED 2026-06-01.** Settlement at `confirmation_docs/L1_L3_REFRAME_DECISIONS.md`. New ADRs 0155-0159 (Monitor lifecycle relocation; L3 bipartite topology; family-specific dont-know; DataState naming convention; capacity registration contract v2).
- **Chat C plan-authoring CLOSED 2026-06-02.** Settlement at `confirmation_docs/POST_PHASE_38_PHASE_MAP.md`. 4-rail DAG (A: rename → schema-v2; B: X1 → X2 → X3; C: L0 substrate; D: dream family) converging at Phase 46 (L4 substrate) → Phase 47 (L4 orchestrator) → Phase 48 (L5 v1) → Phase 49 (Integration C). See §3.1.7.
- **Two downstream design chats named as Stream B rail prerequisites:** `L0_SUBSTRATE_CHAT` (gates Phase 44), `DREAM_FAMILY_CHAT` (gates Phase 45).
- **IS** in maintenance mode for tracked carry-forwards (see §6).

═══════════════════════════════════════════════════════════════════════
## 2. Shipped state (L0–L3) — what's true today

The L0-L3 numbered-phase rollout shipped Phase 00 → Phase 38 from 2026-05-03 to 2026-05-28. Phase 17, 23, 37 were retired. Phase 04 was superseded by 04-v2. Phase 05 split into 05a/b/c/d. Phase 26 split into 26a/b. **Phase 38 closed the L0-L3 rollout** with 3,379 passed / 57 skipped / 0 failed at squash `edb25df`.

### 2.1 L1 Core — shipped surfaces

- **Identity** (Phase 02): IRI primitives, IdentityRegistry, IdStrategy.
- **Graph elements** (Phase 03): Graph, Node, Edge, HyperEdge.
- **Schema** (Phase 04-v2): NodeType, EdgeType, HyperEdgeType; opt-in strict mode.
- **Metagraph** (Phase 05a-d): Metagraph, MetaEdge, MetaHyperEdge, IntergraphEdge (binary; Phase 05b), IntergraphHyperEdge (n-ary; Phase 05c), MetaEdgeType + MetaHyperEdgeType + MetagraphSchema. **Note on naming:** the primitive is `IntergraphEdge` (lowercase `g` in "graph"); the WSD project proposes `InterGraphEdge` (capital G). These are the same concept; reconciliation pending in skill-acquisition chat.
- **Instancing** (Phase 06): sibling `mindsos_instances` package; 8 instance subclasses + ElementRegistry.
- **Persistence** (Phase 07): Client / FalkorClient / InMemoryClient / AsyncClient + Repositories + WAL + indexes + OCC.
- **Reconstruction** (Phase 08): MetagraphLoader + streaming + recover-on-load.
- **XRef** (Phase 09): cross-metagraph refs primitive.
- **Snapshot + soft-delete** (Phase 10): MetagraphSnapshot + tombstones + RemovalImpact.
- **Loader policy + schema migration** (Phase 11): Cypher integrity scanner + ADR-0134 schema migration.

### 2.2 L2 Knowledge — shipped surfaces

- **Identifiers + role IRIs + REF_TYPES** (Phase 12). **Note (L2 chat closure):** `memories` role rename → `episodic_memories` queued; atomic migration phase to ship per Chat C plan-authoring (ADR-0044 §amendment-3 + L2_CHAT_DECISIONS D-L2-16). Carry-forward L2-34.
- **8 role-graph schemas** (Phase 13): `ontology`, `lexicon`, `concepts`, plus the parametric `alignment:<role-a>:<role-b>` template, plus upper-layer schemas (~~`memories`~~ → pending rename to `episodic_memories`, `promoted-pipelines`, `task-patterns`, `problem-trace`, `capacity-state`). **L2 chat closure (2026-06-01):** schema v2 + role-graph expansion locked at ADR-0150 §amendment-4 + ADR-0152; closed role-set expands from 8 to 12 named + alignment-prefix on impl phase; `alignment` canonical form locked at `alignment:<a>:<b>` (ADR-0154; `identifiers.py:303` reconciliation tracked at L2-35).
- **KnowledgeLayer + role-graph bootstrap** (Phase 14): KL class, MetagraphView read-only, install/extract hooks, two-method bootstrap. **No write API per ADR-0138.**
- **Admin importers** (Phase 15a): DolceImporter (pins DOLCE-DUL 4.1), OewnImporter (pins OEWN 2024), FrameNetImporter (pins FrameNet 1.7) under `mindsos_admin/importers/` per ADR-0140 §am-1.
- **Knowledge lifecycle ratification** (Phase 14a + 15b): design-only design-pass ships establishing the lifecycle vocabulary.
- **Admin similarity surface** (Phase 16): `mindsos_admin/similarity.py` read-only narrow per PB-1c reframe.
- **L2 hybrid validators home** (Phase 36): `mindsos_knowledge/validators.py` per ADR-0139; 5 pure-function validators + ValidationResult; wired to L3 consolidate/trace capacities.
- **Versioning enumerator** (Phase 17 retirement): `versions_in_role` + `mindsos knowledge versions` CLI verb (the rest of Phase 17 was retired per ADR-0150 §amendment-3).

### 2.3 L0 Server — shipped surfaces

- **User store + auth** (Phase 18): argon2id user store + 7-cap roster + Session + audit substrate.
- **Sessions** (Phase 19): login / logout / session_from_token; SessionTTL injection; InvalidSessionError unified.
- **Admin reset + bootstrap CLI** (Phase 20): `mindsos server bootstrap` + `reset-admin`.
- **Audit log reader** (Phase 21): query-audit + 14 audit-event constants.
- **Admin ops** (Phase 22): 6 admin verbs under `mindsos server admin` Typer subgroup.
- **Per-user transactional promotion** (Phase 24): admin-direct ATOM only per ADR-0118; `release_update` + `release_ship_lock` + audit gate + two-pass similarity. Schema v3→v4. ADMIN_CAPS 7→9.
- **Cross-user-read substrate** (Phase 25): `read_other_local` + `InstallRecord` refcount + `UserMutexRegistry` first consumer + SessionProtocol first ship (ADR-0040) + LocalPersister Protocol + InMemoryLocalPersister. **Important:** only `InMemoryLocalPersister` shipped; `SQLiteLocalPersister` + `FalkorDBLocalPersister` are deferred (see §6 carry-forward).

### 2.4 L3 Capacity — shipped surfaces

- **DataStates + capacity primitives** (Phase 27): 12 functional categories, 5-file slim port.
- **CapacityLayer + bootstrap + capability gate** (Phase 28): `CapacityLayer` class with CAN_WRITE_GLOBAL gate per ADR-0078.
- **Discovery + Walks** (Phase 29): TYPE_COMPAT auto-discovery + SuccessorHop + walks + rediscover + DiscoveryFailedError.
- **Pipeline finder + invoke runtime + ProblemTraceRecord** (Phase 30): `find` + `invoke` + ProblemTraceRecord + InvocationResult + CLI `mindsos capacity find` / `problem-trace tail`.
- **Residents + built-in text capacities** (Phase 31): ResidentSubscription + per-layer `_subscriptions` dict + 3 CapacityLayer resident methods + `mindsos capacity invoke` CLI verb + builtins/text.py.
- **Write capacities — `consolidate:mm` + `trace:problem`** (Phase 33): first L3 write surface; KLWriteHandle stub at L2 per ADRs 0145+0146+0147.
- **Per-flow build pattern + symmetric write contract** (Phase 34+35): ADR-0146 + ADR-0147 ship.

### 2.5 Integration phases

- **Integration A** (Phase 26a + 26b): FalkorDB persistence wiring + L0+L1+L2 read-side scenario.
- **Integration B** (Phase 32): L0+L1+L2+L3 read-side end-to-end scenario.

### 2.6 The closing phase

- **Phase 38** (2026-05-28): Closing-phase ship. Text-realm cookbook (read-side, transcribes Phase 32). PHASE_MAP §38 4-clause §inline-amendment. PHASE_38_PAGE_INVENTORY.md audits 74 docs pages. 3,379 passed / 57 skipped / 0 failed cumulative.

═══════════════════════════════════════════════════════════════════════
## 3. L4 Intelligence design state — settled vs contested

L4 is **in design**. No L4 code has been written. The design has accumulated 7 active critique pushes since the original 2026-04-22 design session; **all 7 are pending acceptance**. Other layers should design defensively around them.

### 3.1 Settled — other layers can rely on these

- **Lifecycle and tenancy.** One `IntelligenceLayer` instance per live user session. Owned by server's per-user context. Constructor: `IntelligenceLayer(session, knowledge=kl, capacity=cl)`. Methods: `start()`, `stop(mode="pause"|"abort")`, `enqueue(task)`. No Global L4.
- **Layer isolation.** No upward imports. L4 is sole writer to L5 and to the five upper-layer L2 role-graphs (`episodic_memories` [renamed from `memories` by Chat B D-B48], `promoted-pipelines`, `task-patterns`, `problem-trace`, `capacity-state`).
- **Confidence topology.** Pipeline-level on `promoted-pipelines` keyed by `(pipeline, task_type)`. Per-run output on TaskRun composite. **No per-capacity confidence anywhere** (violates L3 fixed-not-learned).
- **Pipeline-runs first-class.** `PipelineRun` (renamed by Chat B D-B32 from Chat A's `PlanRun`) is a `CompositeInstance` in intelligence-MM with `status`, timestamps, refs to its parent `TaskRun` (Chat B D-B33). Multiple per task (one per leaf Milestone executed). Replan per Chat B D-B30 = invalidate chain at and below replan level, spawn new artifacts; TaskRun stays put.
- **Capacities are fixed.** No internal versioning. IRI presence in active Global L3 is the entire dependency check.
- **Promotion topology.** Local pipeline using Local capacities cannot be Global-promoted until deps are also promoted. `PromotionProposal` builder shape settled.
- **L3 surface L4 consumes.** `cl.invoke()`, `cl.iter_monitors()` (per ADR-0155), `cl.problem_trace`, `cl.iter_constraints()`. **NOTE: `cl.start_resident()` / `cl.stop_resident()` / `cl.active_subscriptions()` retired by ADR-0155 (L1/L3 reframe chat 2026-06-01); Monitor lifecycle moves to L4 substrate.** CONSTRAINT edges to respect at dispatch: `MUTUALLY_EXCLUSIVE`, `MANDATORY_BEFORE`, `REQUIRES_APPROVAL`, `RATE_LIMIT`, `REQUIRES_L2_VERSION`.

### 3.1.5 Chat A closure (2026-05-28) — supersedes §3.2 contested list

Chat A (L4 design-resolution) closed 2026-05-28 with all 7 critique pushes ratified + ~70 substantive picks. The contested list in §3.2 below is **superseded** by Chat A outcomes. Full settlement at `docs/_workbench/CHAT_A_DECISIONS.md`. Quick summary:

- **Push 1** → PARTIAL-ACCEPT-4 (L4 = substrate + control flow only; all decisions are L3 capabilities).
- **Push 2** → ACCEPT-A (action contracts via L3 predicate-capacity IRIs).
- **Push 3** → ACCEPT cut + ALS substitutes (WSD architecture adopted).
- **Push 4** → DROP (subsumed by Push 2).
- **Push 5** → DEFER post-v1 (signature shipped; v1 only `mode="abort"`).
- **Push 6** → PARTIAL-ACCEPT-2 (keep tiers + within-tier score-based ordering with L3-mutable score via ALS).
- **Push 7** → DROP entirely.
- **Push 8** → Structurally solved (always-on signal-triage worker + workers handle L3).

Plus major new architecture: WSD's ALS adopted with 10 v1 subsystems; MSUR + SCMS as L3 orchestration capacities; six-phase task lifecycle with Phase 6; pipelines as binary deterministic solvers with 5-state lifecycle; Phase 1 5-step refactor with hint extraction; system-trust contract (honest don't-know + calibrated confidence).

### 3.1.6 L1/L3 reframe chat closure (2026-06-01) — ratifies Chat A R6 + capacity registration contract v2

The L1/L3 reframe chat closed 2026-06-01 ratifying the four routed-to-reframe items + the L3 family additions Chat A authored that need formal contract + the L3-36 → L3-51 family contract batch. Full settlement at `docs/_workbench/L1_L3_REFRAME_DECISIONS.md`. Five ADRs:

- **ADR-0155** (D36) — Monitor lifecycle relocated from L3 to L4 substrate. Supersedes ADR-0073 + §amendment-1. Phase 31 module retires whole.
- **ADR-0156** (D38) — L3 capacity-to-DataState topology reframed as explicit bipartite. Supersedes ADR-0069 + ADR-0086. Amends ADR-0070 + ADR-0071 + ADR-0132 (Phase 06 amendment adds `IntergraphEdgeInstance` + `IntergraphHyperEdgeInstance`).
- **ADR-0157** (D46) — L3 capacity dont-know contracts are family-specific (reverses Chat A R6 "universal" direction). 5-shape catalog; family rule implicit from prefix; new `family_rules.py` module; `DS_UNHANDLED_INPUT` ships.
- **ADR-0158** (D48) — DataState naming convention with realm sub-namespace. IRI form `datastate:<realm>.<name>` (matches shipped Phase 27-33 form verbatim; zero retroactive migration). 9 reserved v1 realms; strict-by-default validation + admin opt-in.
- **ADR-0159** (capacity registration contract v2) — bundles L3-3 + L3-34 + L3-47. Five new `_CapacityBase` fields (`concurrent`, `inline`, `max_latency_ms`, `precondition_iri`, `effect_iri`, `reads_mm`) + new `context.py` module with typed CapacityContext + 4 Protocols + 5 verdict types. Amends ADR-0072 / ADR-0078 / ADR-0143 / ADR-0146 / ADR-0147.

**16 L3 family contracts ratified** (L3-36 through L3-51 batch; L3-47 absorbed into ADR-0159; L3-32 thread-safety audit absorbed into ADR-0156 Phase 27 audit deliverable; L3-35 non-DataState returns absorbed into ADR-0157).

**3 ship phases sequenced** for Chat C plan-authoring:

- **Phase X1** = ADR-0157 + ADR-0158 bundled (shared `identifiers.py` realm constants + `family_rules.py` module).
- **Phase X2** = ADR-0155 (monitor lifecycle relocation).
- **Phase X3** = ADR-0156 + ADR-0159 + Phase 27 audit deliverable (atomic `_CapacityBase` migration).

**Phase 38 carry-forward updates:**

- #4 (`add_type_compat` admin API) — **RETIRED** per ADR-0156 supersession of ADR-0086.
- #5 (`include_deprecated` discipline, L3-19) — folded into ADR-0156 scope.
- #10 (mkdocs `--strict` lift) — grows by 8-12 docs surfaces touching TYPE_COMPAT terminology; bundled into ADR-0156 ship phase X3.

**Chat A R6 reconciliation:** ADR-0157 reverses the "universal no-opt-out" direction explicitly; the other three D36/D38/D48 directions ratified as stated with refinements.

**Chat B cascade gap absorbed:** `IntergraphHyperEdgeInstance` (required by Chat B D-B41 Pipeline composition) was not in Chat B's L3 cascades enumeration. ADR-0156 absorbs the gap into the Phase 06 amendment alongside `IntergraphEdgeInstance`.

### 3.1.8 Phase 39 design-pass closure (2026-06-02) — rename + L2-35 + ADR-0146 §am-N locked

Phase 39 design pass closed 2026-06-02 (same calendar day as Chat C
plan-authoring; design-pass time ~half day post-Chat-C). Three
consecutive reversal-free rounds (R1, R2, R3) satisfied HANDOFF §9
saturation criterion. Full settlement at
`confirmation_docs/PHASE_39_DESIGN_LOG.md`.

**Picks locked beyond the Phase 39 row spec in POST_PHASE_38_PHASE_MAP:**

- **`_IRI_BUILDERS` tuple-key registry** — `Dict[(role, NodeType_name), Callable]`; replaces shipped `Dict[role, Callable]`. Forced by D-L2-17 two-NodeType `episodic_memories` role (Episode + Memory). New **ADR-0146 §amendment-N** ratifies the shape change + `mint_iri(type_, **content)` signature.
- **`consolidate.py` semantic retarget DEFERRED to Phase 43.** Phase 39 ships identifier-surface rename only on `consolidate:mm` (ROLE_EPISODIC_MEMORIES import + writeable() role). `type_="Memory"` stays — capacity continues writing Memory-composite-shape IRIs (semantically wrong per D-L2-17 but mechanically valid). Collapses triple-touch (Phase 39/42/48) to double-touch (42/48).
- **Phase 13 schema-shape drops at Phase 39:** `USED_CAPACITY` + `PART_OF_PIPELINE` EdgeTypes + `MEMORY_PROPS` advisory frozenset dropped. Phase 13 single-Memory semantics superseded. Episode + Memory NodeType skeletons ship; full D-L2-17 content + `memory_contains_episode` IntergraphEdge + `mutation_discipline` apparatus deferred to Phase 43.
- **ADR-0150 §am-4 surgery: verbatim overwrite to rename-only.** Pre-ship in-place edits legitimate per ADR house style. Exclusion list (`sense-correlations` / `world-axioms` / `training-runs` / `fol-rules` / `fol-ledger`) migrates to §am-5 (Phase 43).
- **ADR-0044 §am-3 + ADR-0150 §am-4 verified, not drafted.** Both already on disk from L2 chat closure 2026-06-01.
- **ADR-0146 §am-N narrow scope.** Ratifies registry shape + mint_iri signature only. Per-flow-build discipline (ADR-0146 §am-1 clauses 4+5) unchanged.
- **ADR-0143 gets one-line cross-ref.** No separate amendment.
- **Migration script reframed as `tools/check_rename_state.py` detector.** Honest about being a wipe-and-rebootstrap stub, not a migrator. v1 production has no pre-rename state; dev environments only.
- **`docs/usage/knowledge/memories.md` → `episodic-memories.md`** with stub + forward-ref to Phase 48.
- **Test function names containing "memories" / "memory_iri" renamed atomically.** Extends D-L2-16 atomic principle to identifier-bearing function names.
- **Sentinel chain anchor strips Phase 35 Model C SKIP logic.** Post-housekeeping ADRs are in-repo; no SKIP needed.

**Pre-impl prereq:** Stream A item A1 (`release.yml` retention amendment per PB-R) must land before `phase-39` branches off main. Status at design-pass close: pending.

**Cascade to other phases (PB-Z reading-list):**
- **Phase 40 R0** reads Phase 39 `identifiers.py` diff (overlap with REALM_* additions; near-zero literal-line collision risk).
- **Phase 42 R0** reads Phase 39 `consolidate.py` diff (Phase 42's `context["kl"]` → `context.kl` is the second touch).
- **Phase 43 R0** reads Phase 39 `episodic_memories.py` + `identifiers.py` diffs (Phase 43 ships D-L2-17 fully + 4 new role-graphs).
- **Phase 48 R0** reads Phase 39 + Phase 43 `consolidate.py` diffs (Phase 48 retargets `consolidate:mm` to write Episodes — the semantic change deferred from Phase 39).

**Impl + tester loop expected outputs (per §6 of design log):** `phase-39-confirmed` tag, `PHASE_39_CONFIRMED.md`, ADR amendments shipped, ~50 file touches, Phase 39 7-file test suite, manifest bump 38→39.

### 3.1.7 Chat C plan-authoring closure (2026-06-02) — 11 phase slots reserved Phases 39-49

Chat C plan-authoring closed 2026-06-02 after a 6-round saturation pass (R0 → R6). Three consecutive reversal-free rounds (R3 → R4 → R5 → R6 confirmation) satisfied HANDOFF §9 saturation criterion. Full settlement at `confirmation_docs/POST_PHASE_38_PHASE_MAP.md`.

**Stream B architecture: 4-rail DAG converging at Phase 46.**

- **Rail A (L2):** Phase 39 (`memories` → `episodic_memories` atomic rename + L2-35 alignment reconciliation + ADR-0044 §am-3 + ADR-0150 §am-4 rename row + `tools/rename_memories_to_episodic_memories.py` migration script) → Phase 43 (L2 schema-v2: 4 new role-graphs + `mutation_discipline` runtime invariant + `storage_mode` + bootstrap topological order + ADR-0151 + ADR-0152 + ADR-0153 + ADR-0094 §am-1 + ADR-0150 §am-5 4-new-role-graphs).
- **Rail B (L1/L3 reframe ships):** Phase 40 (X1: ADR-0157 family-specific dont-know + ADR-0158 DataState realm naming) → Phase 41 (X2: ADR-0155 Monitor lifecycle retirement from L3; hard-break public exports) → Phase 42 (X3: ADR-0156 bipartite topology + ADR-0159 capacity registration contract v2 + Phase 27 audit deliverable `PHASE_27_DONT_KNOW_AUDIT.md` + Model C remediation strict-lift + filename normalization + TYPE_COMPAT docs).
- **Rail C (L0 substrate):** `L0_SUBSTRATE_CHAT` closure → Phase 44 (`FalkorDBLocalPersister` + `SQLiteLocalPersister` + Falkor-backed L3 bootstrap + state-file serialization + `kl.read_at_version` + `kl.retire_version` lazy-inline hook + `applies_after` bootstrap field + `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` + `READ_OTHER_LOCAL_EPISODIC_MEMORY` capability).
- **Rail D (dream family):** `DREAM_FAMILY_CHAT` closure → Phase 45 (`dream.*` family ratification: 3 v1 capacities `dream.maintenance`, `dream.exploration`, `dream.retry` + execution-policy contracts).

**Convergence at Phase 46 (L4 substrate).** Requires all four rails closed. L4 substrate ships `IntelligenceLayer` lifecycle + priority-tier Executor (D32.5b) + worker pool + MM RWLock + MM resolution+instantiation layer + cooperative cancellation framework + signal-triage worker + ALS subsystem registry + MonitorSubscriptionRegistry. ~1000-1400 LOC + ~6-8 new ADRs at R0.

**Phase 47 (L4 orchestrator).** Six-phase task lifecycle + Phase 1 5-step refactor + Plan+Pipeline construction + DFS execution + Phase 6 failure-diagnosis hookup + replan-check dispatch + sufficient-predicate eval + minimal `planning.*` v0 placeholder catalog (4 trivial impls; WSD installation chat atomically replaces) + 10 signal-source skeletons + 11 ALS subsystem skeletons. ~3-5 new ADRs.

**Phase 48 (L5 v1).** MM consolidation write path + Episode/Memory authoring + dream pipeline hookup + D'1 retention model + lazy inline-on-retire + crash recovery + retention monitoring instrumentation. Absorbs PHASE_38 §4 docs items #12 (`facts-and-figures.md`) + #13 (`concepts/layers.md` + `society-of-mind.md`) per Chat C PB-V. ~3-5 new ADRs.

**Phase 49 (Integration C).** End-to-end L0→L5 trivial-task scenario + `usage/cookbook/end-to-end.md` cookbook page + Falkor index decisions per PB-HHH. First end-to-end exercise of L4 + L5 substrate; trivial-task scope (feature-complete demo waits for WSD installation).

**Cross-cutting commitments locked by Chat C:**

- **DAG execution** (PB-K + PB-Y) — rails describe design + impl parallelism; tester verification serializes through the single tester per PHASE_MAP §1.
- **`release.yml` retention amendment** (PB-R) — pre-Phase-39 Stream A prereq; rule changes from tag-time-based to phase-number-based eviction.
- **Per-phase R0 reading-list discipline** (PB-Z) — each phase R0 reads diffs of prior phases touching the same files. Predictable collision surfaces: `consolidate.py` (Phase 39/42/48), `identifiers.py` (Phase 39/40), `mindsos_core/schema.py` (Phase 43+46).
- **ADR-0150 amendment split** (IL-3) — §am-4 rename row at Phase 39; §am-5 4-new-role-graphs at Phase 43. Refines L2_CHAT_DECISIONS D-L2-26 single-bulk pick.
- **Sentinel chain** — closed-class at Phase 38; new chain rooted at Phase 39 (`test_adr_amendment_sentinels.py` per Phase 35 ancestor matching content).
- **PB-11 ship-shape default discipline dropped** (IL-8) — zero triggers in this map; lesson preserved in `confirmation_docs/PHASE_38_DESIGN_LOG.md §5`.
- **`[mindsos_plan]` manifest namespace field dropped** (PB-S) — no phase-number collisions arise; tooling unchanged.
- **Stream A** — in-repo bug-fix-PR index at `_workbench/STREAM_A_BACKLOG.md`; 7 items (1 pre-Phase-39 prereq + 6 interleavable).
- **Cookbook routing** — `_workbench/cookbook_routing.md` documents `text-realm.md` shipped, `end-to-end.md` ships Phase 49, `nlu-slice.md` → WSD installation, `code-slice.md` → code-skill installation.
- **Downstream chats** — `L0_SUBSTRATE_CHAT`, `DREAM_FAMILY_CHAT`, `SKILL_ACQUISITION_PROCESS_CHAT`, `WSD_INSTALLATION_CHAT`, `FOL_INSTALLATION_CHAT`, `DWF_INSTALLATION_CHAT`, `ADAPTER_FAMILY_CHAT`, `CODE_SKILL_INSTALLATION_CHAT`, `MAINTENANCE_CHAT`, `L4-v2 follow-up chat` — sequencing reserved at §6 of POST_PHASE_38_PHASE_MAP.

**Items routed elsewhere by Chat C:**

- L0 admin-surface items (audit constants for ALS events, scheduler infra, HITL channel, capacity-gaps tooling, hint catalog tooling) — absorbed into WSD_INSTALLATION_CHAT per PB-T (rejected a separate L0_ADMIN_SURFACE_CHAT).
- L0-17 simplified-execution-mode CLI flag — `MAINTENANCE_CHAT`.
- Cross-layer rewrite handler + pause-and-resume + coherence dream intent re-evaluation + phase-loop as L3 + `decision.preempt_target` + 15 other v2 watch items — L4-v2 follow-up chat (opens after Phase 49 confirmed).
- Storage retention policy (PB-QQ) — Phase 48 ships monitoring instrumentation only; retention policy v1.5 if growth observed.
- Falkor index strategy (PB-HHH) — Phase 49 R0 decision.
- Physical-layout optimization (PB-AAA) — Phase 46 R0 decision; default = Chat B schemas as-written.

### 3.1.9 Phase 43 pre-R0 design pass closure (2026-06-02 end-of-day) — S9 blocker surfaced + locked picks + R0b derivations

The Phase 43 pre-R0 design pass opened end-of-day 2026-06-02 immediately after Phase 39 design-pass close (`§3.1.8`) and Chat C plan-authoring close (`§3.1.7`). It ran four rounds of pre-R0 pushback iteration (C-α/β/γ/δ + PB-43-1…10 picks + N1-N6 + P1-P5+P-meta + per-round revisions) followed by an R0a probe loop, an N-now-C resolution, and an R0b derivation pass. Full settlement at:

- `confirmation_docs/PHASE_43_R0_PICKS_SEED.md` — locked R0 picks the next Phase 43 chat inherits; replaces the PB-43-1…10 default slate in `confirmation_docs/PHASE_43_NEXT_CHAT_PROMPT.md §3`.
- `confirmation_docs/PHASE_43_R0B_DERIVATIONS.md` — `applies_after` edge set + ADR-0150 §am-5 draft text + L2Schema(Schema) subclass sketch with full Discipline/StorageMode enums + 14-row transcription table + validator interface + exception. ADR-0094 §am-1 verified as already on disk.
- `confirmation_docs/A0_HOUSEKEEPING_COMMIT_CHECKLIST.md` — 4-commit grouping (A0-1 housekeeping + ADR tree vendor; A0-2 HANDOFF + sister projects; A0-3 chat closures + Chat C plan + workbench; A0-4 Phase 39 design close + Phase 43 prompt + seed + derivations + this checklist).

**S9 blocker** (load-bearing). R0a-12 probe (`git status`) surfaced that the entire post-Phase-38 corpus is uncommitted on `main`: 20 untracked entries + 16 modified files including this HANDOFF.md, the `docs/decisions/` ADR tree, the `docs/_workbench/` tree, sister projects, archive, all 4 chat closure decisions, the Phase 39 design log, the Phase 43 prompt + seed + derivations themselves. Last commit on `main` is `5236857` (Phase 38 next-chat prompt; 2026-05-28 ish). Phase 39 impl chat CANNOT branch `phase-39` from `main` until A0-1 through A0-4 land. Branching now would yield Phase 38 state with no closure context.

**Locked R0 picks** (carry into Phase 43 R1 — do not re-litigate):

- **PB-43-1** Two-PR split on `phase-43` branch + single squash to `main`.
- **PB-43-2** Transcribe ADR-0153 §1 discipline table into 8 existing schemas (mechanical; 6 disciplines on disk, not 5).
- **PB-43-3** Per-`*_PROPS` constants + partition invariant in `validate_mutation_discipline`.
- **PB-43-4** Explicit-required `applies_after`; edges per `PHASE_43_R0B_DERIVATIONS.md §1`.
- **PB-43-5** Drop `USED_CAPACITY` / `PART_OF_PIPELINE` permanently; schema reservation slot + ADR-0152 note.
- **PB-43-6** `L2Schema(Schema)` subclass in `mindsos_knowledge/schemas/_base.py` (R0a-10 probe clean — zero `isinstance(.., Schema)` / `_SCHEMA_REGISTRY` / `Schema.__name__` consumer cascade).
- **PB-43-7** Mechanical; PB-Z reading-list includes Phase 39 + 40 + 41 + 42 diffs.
- **PB-43-9** Retarget `consolidate.py` `type_="Memory"` → `type_="Episode"` at Phase 43; collapses Phase 39/42/48 triple-touch to Phase 43/48 double-touch.
- **PB-43-10** Detector form `tools/check_phase_43_confidence_state.py`; scope = `promoted-pipelines` only (`task-patterns.confidence` kept per ADR-0152 §2, resolved as N-now-C).
- **N1** Two PRs on branch; single squash to `main`; single phase tag.
- **N3** Both load-time (KL bootstrap dispatch) + write-time (KLWriteHandle write-path body) `mutation_discipline` enforcement at Phase 43.
- **N4** L2Schema subclass safe (R0a-10 zero hits).
- **C-β** Enforce at KL bootstrap, not L4 startup (closes the zombie-field gap pre-Phase-46).
- **C-δ** PB-Z reading-list includes Phase 41 in addition to 39/40/42.
- **P-A** R0 split into R0a + R0b (now closed in this design pass; Phase 43 chat starts at R1 impl-locks).
- **`storage_mode` placement** rides with `mutation_discipline` on `L2Schema`.

**Dropped picks** (do NOT re-litigate in Phase 43):

- **C-γ** (defer ADR-0152 ratification) — moot; ADRs 0151/52/53 already `status: Accepted` on disk per R0a-3.
- **P1** (probe ADR-0153 for 5 disciplines) — moot; ADR-0153 §1 enumerates 6 disciplines with role assignments per R0a-4.
- **P-meta** (open MAINTENANCE_CHAT L2 slot) — moot; L2_FUTURE_WORK §11 has every L2 carry-forward routed per R0a-12.
- **A6 from Phase 43 scope** — L2_FUTURE_WORK §11 routes A6 (`validate_local_to_global_ref`) to Stream A or Phase 44, NOT Phase 43.

**Cascade to other phases:**

- Phase 39 impl chat MUST verify A0 landed first (via `A0_HOUSEKEEPING_COMMIT_CHECKLIST.md §4`).
- Phase 39 impl owns the ADR-0150 §am-4 verbatim narrow-to-rename-only surgery + exclusion list deletion (per `§3.1.8`). Phase 43 then authors §am-5 (4 new role-graphs + exclusion list migrated) per the draft in `PHASE_43_R0B_DERIVATIONS.md §2`.
- Stream A item A8 added (`mindsos_instances` missing from `mindsos_cli/manifest.toml [mindsos] packages` list per R0a-8 probe).
- `PHASE_43_NEXT_CHAT_PROMPT.md` carries a banner pointing to seed + derivations as primary R0 input (added at this closure).

### 3.1.10 A0 + A9 + A1 landing chat closure (2026-06-02 post-design-passes) — S9 resolved

The A0 housekeeping commit checklist (`confirmation_docs/A0_HOUSEKEEPING_COMMIT_CHECKLIST.md`) was executed as 4 commits on `main` + 2 Stream A items (A9, A1) added to the same `wip/a0` branch before fast-forwarding `origin/main`. All 6 commits landed atomically at `f33db02`.

**Final commit stack** (`5236857` predecessor, all on `main` + tag `a0-corpus-landed`):
- `f33db02` — A1: clarify release.yml retention rule (PB-R) — documentation-only.
- `fe1c0d8` — A9: align `tests_server/integration/test_layer_isolation.py` with ADR-0010 §am-1.
- `c3a25fa` — A0-4: Phase 39 design close + Phase 43 seed + this checklist.
- `c66f3d4` — A0-3: chat closures + Chat C plan + workbench index.
- `7f8e932` — A0-2: HANDOFF + sister projects.
- `40fd643` — A0-1: notes relocation + ADR tree vendor + Dockerfile fix + `knowledge.md` vendor.

**Workflow** (documented for future Stream A + phase chats — see §9 "Tester two-machine sync"):

Mac stayed on `main` locally; each commit advanced `main` then pushed to a shared remote `wip/a0` branch for incremental Linux gating. Linux ran `docker compose build mindsos-test` + targeted pytest per commit. After A0-1 + A9 + A1 all verified, `origin/main` was fast-forwarded from `wip/a0`; `wip/a0` deleted from origin; annotated tag `a0-corpus-landed` pushed.

**Cumulative gate result** (post-A0+A9):
- Linux: `docker compose run --rm mindsos-test pytest -q --tb=no` → **3429 passed / 8 skipped / 0 failed** in ~31 min.
- Mac: `mkdocs build` → clean (`Documentation built in 2.68 seconds`); ~15 broken-link warnings + 4 broken-anchor INFOs, no ERRORs. Warnings are pre-existing carry-forwards (Phase 42 §1 filename-normalization scope).

**A1 targeted gate** (post-A1): `pytest tests/phase_01/` → 64 passed / 1 skipped / 0 failed in 29s.

**Three incidental surface findings** during A0 landing (all resolved in the same A0-1 amend + A9 commit; future chats may want to know these existed before):

1. **Dockerfile drift.** `COPY notes-phase-*.md ./` appeared in both prod (line 176) and test (line 250) stages, referring to root-level notes-phase files that A0-1 relocated to `confirmation_docs/notes/`. Rebuild would fail with `no such file or directory`. **Fix bundled into A0-1 amend:** both COPY lines removed (redundant — `COPY confirmation_docs ./confirmation_docs` already covers the new location). Comments updated to reference A0-1 reasoning.

2. **Missing `docs/dev/internals/knowledge.md` vendor.** A0 housekeeping vendored the parent-tree `docs/dev/internals/` dir, but `knowledge.md` was never tracked in repo history (`git log --all --diff-filter=D` returned zero hits). It lived only in `/Layered Intelligence/docs/dev/internals/knowledge.md` per Model C. Phase 36 sentinel `test_knowledge_md_validator_surface_section_present` failed when A0-1's path fix unmuted the parent-tree-skip pattern. **Fix bundled into A0-1 amend:** Henrique vendored the file from his Mac. Future housekeeping passes that retire parent-tree content must explicitly check for files referenced by halvim-tree sentinels but absent from halvim-tree git history.

3. **Stale `tests_server/integration/test_layer_isolation.py` `_DOMAIN_PACKAGES`.** Authored at Phase 18 with `mindsos_admin` + `mindsos_core` + `mindsos_knowledge` + `mindsos_instances` as the strict-§I-S1 roster. ADR-0010 §amendment-1 (Phase 24 ship 2026-05-22, Round 0 PB-Z22) reclassified `mindsos_admin` as a "server-side curation toolkit" that legitimately imports `mindsos_server` primitives. Sibling test `tests/phase_15a/test_import_isolation_phase15a.py` was updated at Phase 24 to honor the reclassification; this test was missed and has been latently failing since. Surfaced when A0-1's path fix unmuted the full pytest collection. **Fix shipped as Stream A item A9** (separate commit `fe1c0d8`): remove `mindsos_admin`, add `mindsos_capacity` (Phase 27 forward-reference catch-up). Roster post-A9: `mindsos_core / mindsos_knowledge / mindsos_capacity / mindsos_instances`. Probed all four for `mindsos_server` imports — zero violations.

**A1 audit finding** — `_retention.select_retention` (`mindsos_cli/_retention.py:134`) already sorts install_targets by the `(phase, letter)` slot tuple, i.e. by phase integer parsed from the tag name. `gh release list`'s tag-time ordering is the *input* but is discarded. A1 is therefore documentation-only: `release.yml` header + retention-step comments made the rule explicit, and `confirm_phase.py` text-mode output gained an acknowledgment line citing the rule. No code logic change.

**Process learnings** (newly written to §9 "Tester two-machine sync"): the Mac↔Linux split + WIP-branch incremental gate pattern is now documented for future Stream A + phase work.

### 3.2 Contested (HISTORICAL — superseded by Chat A closure above)

Each is in active review. **Resolution gates the L4/L5 plan** (see §4).

| # | Decision | Original (2026-04-22) | Critique (2026-04-25) |
|---|---|---|---|
| **Push 1** | Meta-pipeline-everywhere | 6 default meta-pipelines composed of L3 capacities | Collapse to 2 (planning + per-run confidence); hardcode the other 4 |
| **Push 2** | Replan-check predicate | Hand-wavy fast-path/deep-check | Use capacity-contract predicates (precondition + effect on L3 registration) |
| **Push 3** | Coherence dream loop | GAN-analogous 4th dream intent | Cut from v1; ship 3 intents only (maintenance, exploration, retry) |
| **Push 4** | Per-plan assumption/expectation | Filed as future-plan Entries 2+3 candidates for v1 | Reframe as action contracts on L3 capacities; drop per-plan generation |
| **Push 5** | Pause-and-resume | In v1 scope (~300 LOC) | Defer to post-v1; abort-on-logout in v1 |
| **Push 6** | Four-tier preemption | Learnable coefficients (sunk-cost, interruption-cost) | Keep tiers; hardcode preemption (FIFO + hysteresis) |
| **Push 7** | Predicate distillation | Proposed mechanism | Drop entirely; LLM verdicts not stable enough to distill |

Net effect if all 7 are accepted: roughly half the original-handoff scope. The original 2–3k LOC estimate becomes credible.

**Plus 1 unlisted concern (sometimes called Push 8):** signal-thread correctness hazard — single-threaded orchestrator + synchronous L3 invocations means CRITICAL signals are invisible during long-running L3 calls. Either weaken CRITICAL semantics ("high-priority at next yield") or add a signal-triage worker thread (~100 LOC + test).

### 3.3 WSD project has explicit ACCEPT picks on 6 of 7 (HISTORICAL — ratified at Chat A closure)

The WSD sister project (see §5) stated explicit ACCEPT picks on Pushes 1 (PARTIAL ACCEPT), 2, 3, 4, 5, 6, 7 in `projects/wsd/source/coordinated_change_L4_intelligence_and_als.md` §3. **All 7 ratified by Chat A 2026-05-28** (see §3.1.5 closure summary). WSD installation chat inherits Chat A picks verbatim.

═══════════════════════════════════════════════════════════════════════
## 4. L5 Mental Model design state — settled

L5 closed at Chat B (2026-05-31). Full settlement: `docs/_workbench/CHAT_B_DECISIONS.md`. Revised design notes: `docs/dev/l5_mental_model_design_notes.md`. Downstream chats inherit verbatim.

### 4.1 Settled architecture (post Chat B)

- **MM = metagraph of three sub-metagraphs.** `knowledge-MM` (L2 instances), `capacity-MM` (L3 CapacityInstance + DataStateInstance with produces/consumes edges), `intelligence-MM` (L4-authored chain artifacts + provenance + orchestration state + hint values). Thin MM root holds three pointers + `task_run_ref` + `ref:problem_trace` + `outcome_ref`.
- **L4 read discipline.** L4 reads only from MM; cache-miss → search L2/L3 → instantiate → read. L4 invariant: **no shadow state outside MM**. Worker pool threads run via L4 substrate; "L3 worker pool" naming retired ("L3 owns capacities only; threads are L4").
- **L3 read discipline.** L3 capacities prefer MM reads via `mm_handle`; fallback to direct L2/L3 reads using `version_snapshot` in CapacityContext. New KL API: `kl.read_at_version(iri, version)`.
- **6-level chain in intelligence-MM.** `HintSet → MappingResult → Plan → Pipeline → PipelineRun → TaskRun`. Each replan invalidates artifacts at and below the replan level; upstream artifacts reused.
- **Plan = recursive tree of Milestones.** Lazy decomposition; sequential siblings v1; cold-start max-depth=3. New L3 family `planning.*` (4 capacities: `derive_initial_plan`, `decompose`, `aggregate_outputs`, `is_leaf`).
- **Vocabulary discipline.** Chat A's "Phase 1-6" lifecycle preserved as `LifecyclePhase`. Plan-tree nodes are **Milestones** (never "phase"). Chat A's `PlanRun` renamed to **PipelineRun**. New wrapper composite: **TaskRun** (one per task; survives all replans).
- **Retention model — D'1.** References stored as `(iri, version_int)` tuples; pin-at-instantiation. Lazy inline-on-retire when KL releases a version (distinct from deprecate-flagging). Note-fork mechanism **retired** from L0 v2 scope.
- **No Global L5.** Memories Local + circumstantial. Cross-user learning via ALS only.
- **Dream-as-live.** Dream loads episode → fresh MM via deep-copy → re-execute. ALS signals fire normally. No separate dream-learning track. v1 dream pipelines: `dream.maintenance` (replay_recorded), `dream.exploration` (re_execute_capacities), `dream.retry`.
- **L5 role-graph: `episodic_memories`** with two entry types: **Episode** (per-task) and **Memory** (per-task-pattern cluster). Episode-memory association via `memory_contains_episode` IntergraphEdge (not embedded list). Promotion granularity is per-episode.
- **Failure recording.** Unchanged: `ref:problem_trace` on MM root.
- **Retrieval is L3, not L5.** Unchanged.

### 4.2 Cascades inherited from L5 settlement

- **L0:** L0-10 (note-fork) **retired**; new L0-21 (`kl.read_at_version`), L0-22 (`kl.retire_version` hook), L0-23 (`promotion-candidates` queue extension).
- **L1:** `IntergraphHyperEdge` (Phase 05c) gets documented Pipeline-composition use case.
- **L2:** New `episodic_memories` role-graph + schema-only bootstrap importer; new edge type `memory_contains_episode`.
- **L3:** New families `planning.*` + `dream.*`; CapacityContext gains `version_snapshot`; pipeline-finder gains `from_milestone` signature; new ALS subsystem #11 (planning decomposition calibration); new signal source `signal.plan_decomposition_outcome`. v1 ALS subsystem count: 11. v1 signal source catalog: 10 (S7 reserved).
- **L4:** New MM resolution+instantiation substrate (~100-200 LOC on Chat A's 800-1200 budget); D14 (ReplanRecord) amended with `replan_level` + `replan_milestone_ref`; D32.5c.4 `attention_score` moves to TaskRun.

═══════════════════════════════════════════════════════════════════════
## 5. Sister projects intake (DWF / WSD / FOL)

Three sister projects were taken in on 2026-05-28 for integration into MindsOS. Per-project triage docs at `projects/<name>/ANALYSIS.md`; design seeds at `projects/<name>/FUTURE_CHAT_PROMPT.md`; source materials at `projects/<name>/source/`.

| Project | Category | Status | Per-project doc |
|---|---|---|---|
| **DWF Mapping** | **Knowledge acquisition** (L2 install) | v6 substantially finished; v7 unexecuted | `projects/dwf_mapping/` |
| **WSD** | **Skill acquisition** (L1+L2+L3+L4+L5 bundle) | Goal-finalized; pre-code; 4 internal blockers (1 resolved by this housekeeping) | `projects/wsd/` |
| **FOL** | **Skill acquisition** (L1+L2+L3+L4 bundle) | Mid-design; 13 open pushbacks; 2 deferred decision sections | `projects/fol/` |

### 5.1 Acquisition vocabulary

- **Knowledge acquisition** = installing finished knowledge artifacts into MindsOS L2 as one or more role-graphs. DWF is the load-bearing first example.
- **Skill acquisition** = installing a multi-layer intelligent system (a "skill") into MindsOS, spanning L1+L2+L3+L4+L5 artifacts as a coherent unit. WSD + FOL are the two named instances. Both processes are themselves to be designed in future chats.

### 5.2 Recommended chat ordering (updated post Chat B)

Strict dependency order:

1. ~~**L4/L5 plan chat**~~ — **DONE.** Chat A (2026-05-28) closed L4 architecture; Chat B (2026-05-31) closed L5 architecture. Settlement at `_workbench/CHAT_A_DECISIONS.md` + `_workbench/CHAT_B_DECISIONS.md`.
2. **L1/L3 reframe chat** + **L2 chat** + **Chat C plan-authoring** — parallelizable next; reframe + L2 amendments must complete before Chat C finalizes the L4/L5 phase-map.
3. **Skill-acquisition process chat** (shared umbrella; owned by WSD initially).
4. **WSD installation chat.**
5. **FOL installation chat** (inherits WSD's resolutions on shared propositions).
6. **Knowledge-acquisition process chat + DWF installation** (independent; can run in parallel with 2–5 because DWF is L2-only).

### 5.3 Cross-project shared blockers

| Blocker | DWF | WSD | FOL | Status |
|---|---|---|---|---|
| 7 L4 critique pushes | — | yes | yes | **RESOLVED — Chat A 2026-05-28** |
| Coherence Loop fate | — | yes | yes | **RESOLVED — Chat A R2 Push 3 (cut from v1; ALS substitutes)** |
| `sense-correlations` + `learned-parameters` unshipped | — | yes | yes | **RESOLVED — Chat A R3 (ship both v1)** |
| L5 retention model + note-fork | — | yes | yes | **RESOLVED — Chat B D-B1 (D'1 + lazy inline-on-retire; note-fork retired)** |
| L1 InterGraph naming reconciliation | yes (3 conventions in MindsOS code+docs+tests) | yes (proposes `InterGraphEdge`) | — | **Open** — MindsOS internal; resolve before any consumer ships (DWF chat PB-7) |
| `AlignmentsImporter` body unshipped | yes (PRIORITY) | — | — | Knowledge acquisition |

═══════════════════════════════════════════════════════════════════════
## 6. Carry-forwards + open R0 questions

### 6.1 19-item Phase 38 carry-forward (full list in `confirmation_docs/PHASE_38_DESIGN_LOG.md §4`)

**Code surfaces (9):**
1. `mindsos capacity invoke --session-token` CLI flag (deferred from Phase 30 PB-30(a)).
2. Falkor-backed L3 bootstrap + state-file serialization (Phase 30 CF #3).
3. **`FalkorDBLocalPersister`** — load-bearing missing piece per Phase 38 R3-PB-A finding (`mindsos_server/persistence/local_persister.py:57-58`). Pairs with items 1+2.
4. `add_type_compat` admin API + bulk rediscover verb.
5. `include_deprecated` parameter discipline across L3 walks.
6. Per-user Local-scoped `ProblemTraceSink` dict.
7. `--install-builtins=<family,...>` CLI flag on `capacity invoke`.
8. `handle.validate_xref` body (ADR-0139 §am-1 clause 3).
9. 4 unconsumed L2 validators (`validate_local_to_global_ref`, `validate_alignment_role_naming`, `validate_ref_type`, `validate_promotion_candidate`).

**Docs surfaces (8):**
10. `mkdocs build --strict` lift (Model C remediation; **substantially smaller post-housekeeping** — see §6.3).
11. `docs/usage/cookbook/nlu-slice.md` + `code-slice.md`.
12. `docs/getting-started/facts-and-figures.md`.
13. `docs/concepts/layers.md` + `society-of-mind.md`.
14. Per-page ADR cross-reference cleanup.
15. PHASE_MAP §5 row appendices (parent-tree consolidation).
16. `usage/knowledge/memories.md` §6 drift.
17. `concepts/promotion-bridge.md` Phase 24 amendment verification.

**Phase-mechanics (2):**
18. `notes-phase-NN.md` per-phase parity standardization.
19. CHANGELOG `last_design_only_phase` convention generalization.

### 6.2 11 R0 PB candidates for the L4/L5 plan chat — ALL RESOLVED 2026-06-02 at Chat C closure

Captured at the same time as housekeeping; full list in `confirmation_docs/L4_L5_PLAN_NEXT_CHAT_PROMPT.md`. **Final resolution status as of 2026-06-02 (Chat C closure):**

1. ~~Plan vs design-resolution~~ — **RESOLVED.** Chat A closed L4; Chat B closed L5. Chat C plan-authoring closed 2026-06-02.
2. ~~Carry-forward scope absorption~~ — **RESOLVED Chat C** (3-stream split: Stream A bug-fix PRs / Stream B Phase 39-49 / Stream C absorbed into Phase 48). See POST_PHASE_38_PHASE_MAP §5.
3. ~~L4 vs L5 ordering~~ — **RESOLVED** (Chat B). Note-fork retired (D-B1); L5 ships independent of server-pivot v2.
4. ~~FOL placement~~ — **RESOLVED Chat C** (FOL phasing in its own `FOL_INSTALLATION_CHAT` downstream of WSD; reserved per POST_PHASE_38_PHASE_MAP §6).
5. ~~Phase numbering~~ — **RESOLVED Chat C** (continue Phase 39+; no manifest amendment per PB-S; slots 39-49 reserved).
6. ~~Sentinel chain disposition~~ — **RESOLVED Chat C** (new chain rooted at Phase 39 using Phase 35 `test_adr_amendment_sentinels.py` precedent).
7. ~~Cookbook gaps~~ — **RESOLVED Chat C** (`end-to-end.md` ships Phase 49; `nlu-slice.md` → WSD installation; `code-slice.md` → code-skill installation; see `_workbench/cookbook_routing.md`).
8. ~~Model C remediation timing~~ — **RESOLVED Chat C** (bundled into Phase 42 X3 ship as strict-lift + 8-12 TYPE_COMPAT docs + ~50 filename normalization rewrites; `mkdocs-redirects` plugin dropped).
9. ~~`sense-correlations` + `learned-parameters` disposition~~ — **RESOLVED** (Chat A R3 ship both v1; subsequently L2 chat 2026-06-01 withdrew `sense-correlations` as standalone role-graph per D-L2-2; data lives in lexicon empirical-layer; ALS subsystem #8 label preserved).
10. ~~Single-tenant vs multi-tenant L4 scope~~ — **RESOLVED** (Chat A R5 D35 single-tenant v1).
11. ~~Ship-shape default~~ — **RESOLVED Chat C** (PB-11 discipline DROPPED per IL-8; zero triggers in Phase 39-49 map; Phase 38 R6 lesson preserved in `PHASE_38_DESIGN_LOG.md §5`).

### 6.3 Internal-MindsOS drifts to reconcile

These are inconsistencies shipped in MindsOS code+docs+tests; not external project conflicts. They must be reconciled before downstream consumers can ship.

| Drift | Evidence | Resolution path |
|---|---|---|
| ~~**3 alignment role-graph naming conventions**~~ | `identifiers.py:303` `alignment_role()` returns `alignment:<a><->b>`; ADR-0150 §am-1 + `bootstrap.py` use `alignment:<a>:<b>`; Phase 36 validator tests `alignment:<a>-<b>` | **RESOLVED — L2 chat 2026-06-01 picked `alignment:<a>:<b>` canonical (ADR-0154 + L2_CHAT_DECISIONS D-L2-1)**. `identifiers.py:303` one-line body + docstring fix + Phase 36 test assertion update tracked as L2-35 maintenance carry-forward. |
| **50 mkdocs warnings** | Build probe 2026-05-28: 50 warnings, all summary pages linking to short-form ADR filenames (`0022-batched-writes.md`) vs actual descriptive names (`0022-batched-writes-via-unwind.md`). Affects 6 summary pages | Filename normalization; one mini-phase or in-housekeeping fix |

### 6.4 Phase 38 closed the L0-L3 plan. Chat C closure + Phase 39 design pass 2026-06-02.

L4 architecture settled at Chat A (2026-05-28). L5 architecture settled at Chat B (2026-05-31). L1/L3 reframe + L2 chats closed 2026-06-01. **Chat C plan-authoring CLOSED 2026-06-02.** Phase 39-49 slots reserved across 4-rail DAG at `confirmation_docs/POST_PHASE_38_PHASE_MAP.md`. See §3.1.7 for rail/phase summary.

Phase 39 (L2 `memories` → `episodic_memories` atomic rename) **design pass closed 2026-06-02** with locked picks at `confirmation_docs/PHASE_39_DESIGN_LOG.md`. Impl + tester loop is the next action; `phase-39` branches off main AFTER A0 housekeeping commits land (per `confirmation_docs/A0_HOUSEKEEPING_COMMIT_CHECKLIST.md`) AND Stream A item A1 (`release.yml` retention amendment per PB-R) lands.

Phase 43 (L2 schema-v2) **pre-R0 design pass closed 2026-06-02 end-of-day** with locked picks at `confirmation_docs/PHASE_43_R0_PICKS_SEED.md` + R0b derivation artifacts at `confirmation_docs/PHASE_43_R0B_DERIVATIONS.md`. Phase 43 chat opens after `phase-39-confirmed`; starts at R1 impl-locks (R0 + R0a + R0b complete). See §3.1.9.

═══════════════════════════════════════════════════════════════════════
## 7. Git state, provenance, file system

### 7.1 Git

- **Active branch:** `main`.
- **Latest ship tag:** `phase-38-confirmed` at squash commit `edb25df`.
- **GitHub remote:** `git@github.com:halvim/mindsos.git` (folder is named "MindsOS" locally; remote name is "halvim/mindsos" — discrepancy intentional; rename the GitHub repo later if you want full parity).
- **Historical local branches** (`phase-00`, `phase-01`, `phase-06`, `phase-21`, `phase-25`, `phase-26a`) are forensic-only. Safe to delete locally.

### 7.2 Provenance — what got extracted vs archived

**Extracted into MindsOS during 2026-05-28 housekeeping:**
- 144 ADRs from parent `docs/decisions/adr/` → `MindsOS/docs/decisions/adr/`.
- ADR machinery (`about.md`, `proposed.md`, `superseded.md`, `summary/*`) → `MindsOS/docs/decisions/`.
- L4 + L5 design notes → `MindsOS/docs/dev/l4_intelligence_design_notes.md`, `MindsOS/docs/dev/l5_mental_model_design_notes.md`.
- `use_cases_text_realm.md` → `MindsOS/docs/dev/use_cases_text_realm.md` (referenced by L4+L5 notes and FOL/WSD chats).
- 3 sister-project source materials → `MindsOS/projects/`.

**Stays in archive (`_archive_Layered_Intelligence/`):**
- `_source_backup/root/` — pre-rollout layer handoffs (`mindsos_core_handoff.md`, `mindsos_knowledge_handoff.md`, `mindsos_capacity_handoff.md`, `mindsos_server_handoff.md`, `mindsos_intelligence_handoff.md`, `mindsos_intelligence_handoff_current.md`, `mindsos_future_plans.md`, `layer3_system_design_plan.md`). Superseded by what shipped in L0-L3 or absorbed into this HANDOFF.md.
- Parent-tree `mindsos_*/` packages — pre-refactor sources.
- Parent `tests/`, `tests_kl/`, `tests_l3/`, `tests_server/` — pre-halvim test suites.
- `_memory_phase_34/`, `mindsos_capacity_handoff_current.md`, `mindsos_design_critique_handoff.md` — superseded.
- Original 3 sister-project zips (their contents are at `projects/*/source/`).
- Parent root metadata (`MAC_README.md`, `MINDSOS_DOCS_PLAN.md`, `PHASE_00_TESTER_CHECKLIST.md`, `HANDOFF.md` (2026-04-26 — superseded by this doc), parent `CLAUDE.md`).

### 7.3 Folder structure (post-housekeeping)

```
MindsOS/
├── HANDOFF.md                     ← this file
├── CLAUDE.md                      ← project instructions for Claude/Cowork
├── README.md
├── pyproject.toml, mkdocs.yml, docker-compose.yml, Dockerfile
├── requirements.in / .txt, entrypoint.sh
├── mindsos_admin/                 ← admin importers + promotion + audit gate
├── mindsos_capacity/              ← L3
├── mindsos_cli/                   ← Typer CLI
├── mindsos_core/                  ← L1
├── mindsos_instances/             ← instance vocab
├── mindsos_knowledge/             ← L2
├── mindsos_server/                ← L0
├── tests/                         ← phase-NN test suites
├── tests_server/                  ← server-specific tests
├── tools/                         ← lock.sh
├── scripts/                       ← dataset-fetch scripts
├── confirmation_docs/             ← PHASE_MAP + per-phase CONFIRMED + design logs + notes/ subfolder
│   └── notes/                     ← 39 historical notes-phase-NN.md files
├── docs/                          ← mkdocs source
│   ├── decisions/adr/             ← 144 ADRs (Model-C-collapsed in)
│   ├── decisions/summary/         ← 6 layer summaries
│   ├── dev/
│   │   ├── l4_intelligence_design_notes.md
│   │   ├── l5_mental_model_design_notes.md
│   │   └── use_cases_text_realm.md
│   ├── concepts/, usage/, api/, getting-started/, knowledge-sources/, changelog/
│   └── (other end-user docs)
└── projects/                      ← 3 sister-project intake
    ├── README.md
    ├── dwf_mapping/
    ├── wsd/
    └── fol/
```

═══════════════════════════════════════════════════════════════════════
## 8. Cowork project setup (when starting fresh)

When you open this folder in Claude desktop app for the first time:

1. Open Claude desktop app → Cowork mode.
2. Add a new project pointing at this MindsOS/ folder.
3. The CLAUDE.md at the root will load as the project instructions; the user-set project instructions (skeptical reviewer style, etc.) will apply.
4. **Read this HANDOFF.md FIRST** (you are reading it now).
5. For mkdocs: `cd MindsOS && pip install mkdocs mkdocs-material && mkdocs serve` → http://127.0.0.1:8000.

═══════════════════════════════════════════════════════════════════════
## 9. Process notes inherited from L0-L3 rollout

These conventions hold for any future code-shipping phase or chat:

- **Probe-first.** 4 of Phase 38's 5 reversals were traceable to probes R0 didn't run. Probe persistence-layer state + CLI verb roster + `mkdocs build` WARNING count + ADR file inventory before locking design picks.
- **Tester ship-shape preference may override design-time picks** (Phase 38 R6 lesson). At R0 of any docs-only-leaning phase, surface ship-shape as explicit PB.
- **Saturation pattern.** R5 produces impl-locks only, zero reversals — that's the signature of a ready-to-ship design pass. Less than that = not yet saturated.
- **Sentinel chain semantics are per-phase, not per-filename.** Filename follows the closest ancestor matching content.
- **Tester two-machine sync (Mac ↔ Linux).** Mac hosts git (commits, branches, tags, PRs), file edits, and quick `ls`/`grep` probes. Linux runs the canonical pytest gate via `docker compose run --rm mindsos-test pytest <args>`. **The only bridge is the git remote — Mac `git push`, Linux `git pull`. No shared filesystem, no rsync, no scp.** Consequence: "pre-commit verification" in any phase or A0 checklist is in practice *post-local-commit, pre-fast-forward-to-target*. Pattern: Mac commits locally → push to a WIP branch (e.g. `wip/<intent>`) → Linux pulls + gates → if green, Mac fast-forwards to target (`main` for Stream A, `phase-NN` for phase work); if red, Mac amends on WIP and re-pushes. Cumulative post-phase gates (A0 §4, phase-NN-confirmed cumulative pytest, `mkdocs build`) run on Linux against target-branch tip after all commits land — push all first, pull once, gate once. Chats walking the user through commits must tag every Linux task with a preceding Mac push and a leading Linux pull, never assume shared state.
- **Memory portability.** Cowork memory is per-project. Memory entries do not necessarily survive a project-root change. This HANDOFF.md is the durable, in-folder source of truth.

═══════════════════════════════════════════════════════════════════════
## 10. References + companion documents

**Required reading for any chat that picks up MindsOS:**

1. This HANDOFF.md (you are here).
2. `CLAUDE.md` at root — project instructions + Cowork setup.

**Required reading per chat type:**

| Chat type | Read also |
|---|---|
| Chat C plan-authoring | **CLOSED 2026-06-02.** Settlement at `confirmation_docs/POST_PHASE_38_PHASE_MAP.md`. 11 phase slots reserved Phases 39-49 (4-rail DAG + convergence + integration). See §3.1.7 closure block. |
| Phase 39 chat (L2 `memories` → `episodic_memories` rename; Rail A) | **DESIGN PASS CLOSED 2026-06-02; impl + tester pending.** **PREREQ:** `confirmation_docs/A0_HOUSEKEEPING_COMMIT_CHECKLIST.md` must land first (S9 — post-Phase-38 corpus uncommitted on `main` per §3.1.9). Settlement at `confirmation_docs/PHASE_39_DESIGN_LOG.md`. Impl + tester loop chat reads: A0 checklist first (verify landed); design log; `confirmation_docs/PHASE_39_NEXT_CHAT_PROMPT.md` (spec); `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1 + §4 Phase 39 row`; `confirmation_docs/L2_CHAT_DECISIONS.md` (D-L2-1/D-L2-16/D-L2-17/D-L2-25/D-L2-26); `docs/_workbench/STREAM_A_BACKLOG.md` (A1 must land first); ADR-0044 + ADR-0150 + ADR-0146 (§am-N drafted at this impl); this §2.2 + §3.1.7 + §3.1.8 + §3.1.9. |
| Phase 40-42 chats (L1/L3 reframe ships; Rail B) | `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1 + §4 Phase 40/41/42 rows`; `confirmation_docs/L1_L3_REFRAME_DECISIONS.md`; ADR drafts 0155-0159; this §3.1.6 + §3.1.7 |
| Phase 43 chat (L2 schema-v2; Rail A) | **PRE-R0 CLOSED 2026-06-02 end-of-day; chat opens at R1 impl-locks.** Primary R0 input: `confirmation_docs/PHASE_43_R0_PICKS_SEED.md` (locked picks + drops) + `confirmation_docs/PHASE_43_R0B_DERIVATIONS.md` (`applies_after` edges, ADR-0150 §am-5 draft, L2Schema sketch). Spec: `confirmation_docs/PHASE_43_NEXT_CHAT_PROMPT.md`. Also: `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1 + §4 Phase 43 row`; `confirmation_docs/PHASE_39_CONFIRMED.md` (when landed); `confirmation_docs/L2_CHAT_DECISIONS.md` D-L2-3/4/5/6/7/10/11/13/14/15/17/19/22/24/26; Phase 39 + 40 + 41 + 42 ship diffs (PB-Z reading-list); ADRs 0094 + 0150 + 0151 + 0152 + 0153 + 0154; this §2.2 + §3.1.7 + §3.1.8 + §3.1.9. |
| Phase 44 chat (L0 substrate; Rail C) | **Requires `L0_SUBSTRATE_CHAT` closure first.** Then `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1 + §4 Phase 44 row`; `_workbench/L0_FUTURE_WORK.md`; Chat B D-B14 + D-B16 + L2_CHAT_DECISIONS D-L2-23; this §2.3 + §3.1.7 |
| Phase 45 chat (dream family ship; Rail D) | **Requires `DREAM_FAMILY_CHAT` closure first.** Then `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1 + §4 Phase 45 row`; Chat B D-B5 + D-B6 + D-B7 + D-B8; ADR-0162 (drafted at DREAM_FAMILY_CHAT); this §3.1.7 + §4 |
| Phase 46 chat (L4 substrate; convergence) | `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1 + §4 Phase 46 row`; `confirmation_docs/CHAT_A_DECISIONS.md` (full R1 D32 + L4-vs-L3 boundary); `confirmation_docs/CHAT_B_DECISIONS.md` (D-B10/D-B11/D-B13/D-B14 MM substrate); `docs/dev/l4_intelligence_design_notes.md`; `docs/dev/l5_mental_model_design_notes.md` §1-§2; this §3.1.5 + §3.1.7 + §4 |
| Phase 47 chat (L4 orchestrator; convergence) | `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1 + §4 Phase 47 row`; `confirmation_docs/CHAT_A_DECISIONS.md` (R2 Pushes + R3 Phase 1 5-step + R4 D12 six-phase); `confirmation_docs/CHAT_B_DECISIONS.md` (D-B22 chain + D-B23 Plan-tree); this §3.1.5 + §3.1.7 + §4 |
| Phase 48 chat (L5 v1; convergence) | `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1 + §4 Phase 48 row`; `confirmation_docs/CHAT_B_DECISIONS.md` (full); `docs/dev/l5_mental_model_design_notes.md` (full); Phase 39 + 42 + 43 ship diffs for `consolidate.py` (PB-Z); this §3.1.7 + §4 |
| Phase 49 chat (Integration C) | `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1 + §4 Phase 49 row`; `confirmation_docs/PHASE_38_DESIGN_LOG.md` (text-realm cookbook precedent); `_workbench/cookbook_routing.md`; this §2.5 + §3.1.7 |
| L0_SUBSTRATE_CHAT (Phase 44 gate) | `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1 + §6`; `_workbench/L0_FUTURE_WORK.md`; `_workbench/L2_CHAT_DECISIONS.md` (D-L2-23); Chat B D-B2 + D-B14 + D-B16; this §2.3 + §3.1.7 |
| DREAM_FAMILY_CHAT (Phase 45 gate) | `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1 + §6`; `confirmation_docs/CHAT_B_DECISIONS.md` D-B5/D-B6/D-B7/D-B8/D-B9; `docs/dev/l5_mental_model_design_notes.md` §5.2-§5.3; this §3.1.7 + §4.1 |
| SKILL_ACQUISITION_PROCESS_CHAT | `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §6`; `projects/README.md`; `projects/wsd/FUTURE_CHAT_PROMPT.md`; `projects/fol/FUTURE_CHAT_PROMPT.md`; this §5 |
| WSD installation chat | **Inherits SKILL_ACQUISITION_PROCESS_CHAT.** Then `projects/wsd/ANALYSIS.md`; `projects/wsd/FUTURE_CHAT_PROMPT.md`; `_workbench/cookbook_routing.md` (owns `nlu-slice.md`); FOL chat coordinates (cross-ref `projects/fol/`); this §3 + §5 |
| FOL installation chat | **Inherits WSD installation.** `projects/fol/ANALYSIS.md`; `projects/fol/FUTURE_CHAT_PROMPT.md`; this §3 + §5; WSD-resolutions inherited |
| DWF / knowledge-acquisition chat | `projects/dwf_mapping/ANALYSIS.md`; `projects/dwf_mapping/FUTURE_CHAT_PROMPT.md`; ADR-0150 + ADR-0154 (canonical `alignment:<a>:<b>` form, ratified Chat C Phase 39 cascade); this §5.1 |
| Code-skill installation chat | `_workbench/cookbook_routing.md` (owns `code-slice.md`); `_workbench/L3_FUTURE_WORK.md` (L3-28/L3-30/L3-31); inherits WSD installation |
| Adapter family chat | `_workbench/L3_FUTURE_WORK.md` (L3-49); inherits WSD installation |
| Maintenance chat | `_workbench/STREAM_A_BACKLOG.md`; relevant `_workbench/L*_FUTURE_WORK.md`; `confirmation_docs/PHASE_MAP.md` for the layer's row |
| L4-v2 follow-up chat | **Opens after Phase 49 confirmed.** `_workbench/L4_FUTURE_WORK.md`; this §3.1 + §3.1.5 |
| Bug-fix / maintenance chat | `confirmation_docs/PHASE_MAP.md` for the layer's row; `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §4` for the corresponding Phase 39-49 row; this §2 + §3.1.7 |

**Optional reference / forensic only:**

- `confirmation_docs/PHASE_MAP.md` — the frozen L0-L3 plan (§1 cross-cutting decisions; §3 phase index; §4-5 per-phase rows).
- `confirmation_docs/POST_PHASE_38_PHASE_MAP.md` — the **active** L4/L5 plan + reframe ships + L2 schema-v2 + L0 substrate + dream family (Phases 39-49).
- `confirmation_docs/PHASE_<N>_CONFIRMED.md` per phase — ship metadata.
- `confirmation_docs/PHASE_<N>_DESIGN_LOG.md` per phase — design-pass picks.
- `confirmation_docs/CHAT_A_DECISIONS.md` — L4 architectural settlement (migrated from `_workbench/` at Chat C closure).
- `confirmation_docs/CHAT_B_DECISIONS.md` — L5 architectural settlement (migrated).
- `confirmation_docs/L1_L3_REFRAME_DECISIONS.md` — 5 ADRs 0155-0159 + X1/X2/X3 sequencing (migrated).
- `confirmation_docs/L2_CHAT_DECISIONS.md` — 4 new ADRs 0151-0154 + amendments (migrated).
- `confirmation_docs/CHAT_A_L4_BASELINE.md` — Chat A's R0 input baseline (migrated).
- `confirmation_docs/CHAT_PLAN_L4_L5.md` — chat-split decision record (migrated).
- `confirmation_docs/PHASE_43_R0_PICKS_SEED.md` — Phase 43 pre-R0 design pass closure: locked R0 picks + drops (2026-06-02 end-of-day; §3.1.9).
- `confirmation_docs/PHASE_43_R0B_DERIVATIONS.md` — Phase 43 R0b derivations: `applies_after` edge set + ADR-0150 §am-5 draft + L2Schema sketch (2026-06-02 end-of-day; §3.1.9).
- `confirmation_docs/A0_HOUSEKEEPING_COMMIT_CHECKLIST.md` — Pre-Phase-39 housekeeping commits (S9 blocker; §3.1.9).
- `confirmation_docs/notes/notes-phase-<N>.md` — tester notes.
- `docs/changelog/CHANGELOG.md` — release-style log.
- 159 ADRs at `docs/decisions/adr/` (144 from L0-L3 + 5 reframe + 4 L2 chat + 6 drafted-at-Chat-C-not-yet-shipped).
- 6 summary docs at `docs/decisions/summary/` per layer.
- Archive at `_archive_Layered_Intelligence/_source_backup/root/` for pre-housekeeping content.
- Archive at `_archive_Layered_Intelligence/_workbench_chat_c_closure/` for forensic-only superseded workbench docs (NEXT_CHAT_PROMPTS.md).

═══════════════════════════════════════════════════════════════════════
## 11. What this HANDOFF.md does not commit to

- It does not commit to v1 L4 ship calendar dates (Chat C reserves 11 slots Phases 39-49; tester throughput bounds calendar).
- It does not commit to L4-v2 multi-tenant rewrite handler shape (deferred to L4-v2 follow-up chat; opens after Phase 49 confirmed).
- It does not commit to WSD / FOL / DWF / code-skill / adapter shipping in any specific phase order (each is its own downstream chat per POST_PHASE_38_PHASE_MAP §6).
- It does not commit to a specific WSD installation phase-map shape (that map authored by WSD_INSTALLATION_CHAT downstream of SKILL_ACQUISITION_PROCESS_CHAT).

This handoff is the snapshot of where things stand entering Phase 39+. Per Phase 38 R6 lesson, tester ship-shape preferences may surface during execution and amend POST_PHASE_38_PHASE_MAP at the affected phase's R0.

*L4 architecture resolved at Chat A (2026-05-28). L5 architecture + retention model resolved at Chat B (2026-05-31). L1/L3 reframe ratified 2026-06-01. L2 schema-v2 ratified 2026-06-01. Phase map for Phases 39-49 authored at Chat C (2026-06-02).*

═══════════════════════════════════════════════════════════════════════
*End of HANDOFF.md. Last reviewed 2026-06-02 (Chat C plan-authoring closure). Update when Phase 39 ships, when L0_SUBSTRATE_CHAT or DREAM_FAMILY_CHAT opens, when any Phase 39-49 confirms, or when any §6 carry-forward closes.*
