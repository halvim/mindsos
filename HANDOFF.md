# MindsOS — HANDOFF

> **Last updated:** 2026-06-09 (**Phase 49 SHIPPED — Integration C, the LAST numbered phase; ALL Phases 39–49 SHIPPED, the post-Phase-38 plan is COMPLETE.** Composes L0–L5 into one end-to-end trivial-task scenario (`tests/phase_49/`) + `usage/cookbook/end-to-end.md` + ADR-0181 Falkor index strategy (PB-HHH; **zero index code** → routed to WSD retrieval) + 10-surface bump 48→49; no new feature surface. Probe: `text.tokenize`→`text.space_split`; v0 lifecycle dispatches no real L3 capacity → **two stitched slices** (PB-1a). **PB-RT**: node `value` is stored primitive but the L5 Episode `value` is a dict → episode-flush-to-Falkor would error; **descoped** (Phase-44 machinery exercised via the Global-pair round-trip; Episode asserted in-memory) → durable-episode gap to **L0-26**. Live integration ran+passed; 3868/11/0; squash `149fb26`, confirm `cc8a7f8`, tag `phase-49-confirmed`; see §3.1.22. **Next chats = the downstream sequence (SKILL_ACQUISITION_PROCESS → WSD / FOL / code-skill / adapter; L4-v2; MAINTENANCE; DWF parallel) per `POST_PHASE_38_PHASE_MAP.md §6`.** Prior: **Phase 48 SHIPPED** — L5 v1: MM consolidation → Episode + Memory + `MEMORY_CONTAINS_EPISODE` edge (retain-by-default on all terminal paths); S12 write-half **closed** (ADR-0180 pre-authorized scope-aware `writeable` capability — PB-23 authorization half done); dream-cycle driver (`dream_cycle.py`); D'1 retention + inline-on-retire (`kl.read_at_version`/`retire_version` + `retention.py`); crash recovery (`crash_recovery.py` tombstone markers + startup scan); retention monitoring (`monitoring.py`); 3 concept docs; ADRs 0176-0180 + amendments 0146/0161/0170/0175. Squash `af331e8`, confirm `1952260`, tag `phase-48-confirmed`; cumulative **3863/10/0**; 10-surface bump 47→48; see §3.1.21. **Phase 47 SHIPPED** (L4 orchestrator over v0 catalogs; six-phase lifecycle + chain-artifact emit + L4 dispatch + S12 read-half; squash `cd8abb0`/Linux-canonical `6f49524`, confirm `db1a562`, tag `phase-47-confirmed`; 3832/9/0; ADRs 0171-0175; §3.1.20). Prior: Phase 46 **SHIPPED** — L4 substrate `mindsos_intelligence` (first L4 code) + ADRs 0163-0170; squash `47c3568`, confirm `18ba793`, tag `phase-46-confirmed`; cumulative 3793/9/0; 9-surface bump 45→46; single PR (PB-0 collapsed); S12 + dream-driver + signal-classifier deferred to Phase 47/48; **next chat = Phase 47 L4 orchestrator**; see §3.1.19. Prior: Phase 45 **SHIPPED**; Rail D — L3 dream family ratification — **closes the last pre-convergence rail.** Combined design+ship (option-C) under DREAM_FAMILY_CHAT. ADR-0162: 3 directive-emitter dream capacities (`dream.maintenance`=`replay_recorded`, `dream.exploration`=`re_execute_capacities`, `dream.retry`=`re_execute_capacities`+replan-injection) + new `DreamCapacity(_CapacityBase)` declaration kind (`execution_policy`+`entry_point`); `CATEGORY_DREAM` lazy-installed (NOT in `FUNCTIONAL_CATEGORIES`, text.* precedent); `builtins/dream.py` (`DreamExecutionPolicy` 2-value + `DreamDirective` + `ReplanInjectionDirective` + 2 DataStates + idempotent installer); `__all__` 117→118. **Consumer discipline:** dream bodies have no v1 L3 consumer — L4 dream-cycle timer + MM deep-copy + live re-execution + ALS firing deferred to Phase 46/47/48. Pre-provisioned `FAMILY_RULES['dream']`/`REALM_DREAM` needed zero edits. **First slot > high-water 44 → real 9-surface version bump 44→45.** 3694 passed cumulative gate; tag `phase-45-confirmed` at confirm-artifacts `e76a1a3` (ship squash `ab32e3d`). See §3.1.18 for ship closure. **All four rails (A/B/C/D) now closed — Phase 46 (L4 substrate convergence) can open R0.** Prior: Phase 42 SHIPPED 2026-06-07, §3.1.17; Phase 41 §3.1.16; Phase 40 §3.1.15; Phase 44 §3.1.14.)
> **Audience:** Any chat, contributor, or reviewer entering MindsOS. This is the canonical entry point — read it first.
> **Self-contained:** This document does not require loading external memory entries to make sense. Inline content is authoritative. Memory entries referenced as `[[name]]` are speed-ups for chats that have memory access; the canonical text lives here.

═══════════════════════════════════════════════════════════════════════
## 0. How to use this document

This handoff is the single source of truth for **what is true about MindsOS as of 2026-05-28**. It supersedes all earlier handoff documents (`mindsos_intelligence_handoff_current.md`, `mindsos_intelligence_handoff.md`, `mindsos_future_plans.md`, `system_overview_2026-04-26.md`, `l4_session_handoff_2026-04-25.md`). Those originals are archived in `_archive_Layered_Intelligence/_source_backup/root/` if needed for forensics.

The companion documents that future chats should also read are named in §10.

**Robot Demo workstream (parallel to the numbered phases).** Status + entry points live in `confirmation_docs/ROBOT_DEMO_STATUS.md`.

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
- **Phase 42 SHIPPED 2026-06-07 — Rail B X3, completes Rail B (X1→X2→X3).** ADR-0156 bipartite topology + ADR-0159 registration contract v2 + Phase 27 dont-know audit (L3-57) + Model C remediation. `__all__` 112→117; 3669 passed cumulative gate; tag `phase-42-confirmed` at confirm-artifacts `e0a1453` (ship squash `39a312c`); no version bump (slot 42 ≤ 44). Capacity-body migration + `invoke`→CapacityContext plumbing + instance `materialise` deferred to Phase 46 (PB-23/PB-24). See §3.1.17 for ship closure + `confirmation_docs/PHASE_42_DESIGN_LOG.md` for the full design record.
- **Phase 43 pre-R0 design pass CLOSED 2026-06-02 end-of-day.** Settlement at `confirmation_docs/PHASE_43_R0_PICKS_SEED.md` (locked picks; drops C-γ, P1, P-meta, A6 from Phase 43 scope; N4 L2Schema subclass safe per probe; task_patterns.confidence kept) + `confirmation_docs/PHASE_43_R0B_DERIVATIONS.md` (R0b artifacts: `applies_after` edges from D-L2-19, ADR-0150 §am-5 draft text, L2Schema(Schema) sketch with discipline+storage_mode transcription table). See §3.1.9.
- **Phase 43 FULL design pass CLOSED 2026-06-03.** R1 impl-locks + R2 amendment texts + R3 cross-check completed across 18 saturation rounds. Reconciles R0 picks seed + R0b derivations + PHASE_MAP §4 row drift against Accepted ADRs on disk. Critical reversals: storage_mode is per-NodeType (not per-role-graph); L2Schema(Schema) subclass placement (not L1 Schema amendment); bootstrap.py field-only at Phase 43 (Kahn scheduler defers to Phase 44 per L2-37 split); consolidate.py retargets at Phase 43 per R0 PB-43-9 (not Phase 48); detector form not migrator; PHASE_44 seed (not PHASE_46). 5 amendment text drafts ratified ready-to-paste. Full record at `confirmation_docs/PHASE_43_DESIGN_LOG.md`. See §3.1.12.
- **Next chat is the Phase 43 SHIP execution chat** (Rail A slot 2, schema-v2). Hand it `confirmation_docs/PHASE_43_SHIP_CHAT_PROMPT.md` — the prompt points to `PHASE_43_DESIGN_LOG.md` as the spec. Phase 43 branches off `phase-39-confirmed` tag (post Phase 39 ship).
- **Chat A (L4 design-resolution) CLOSED 2026-05-28.** Settlement at `confirmation_docs/CHAT_A_DECISIONS.md` (migrated from `_workbench/`).
- **Chat B (L5 design-resolution + note-fork decision) CLOSED 2026-05-31.** Settlement at `confirmation_docs/CHAT_B_DECISIONS.md`. Revised L5 design notes at `docs/dev/l5_mental_model_design_notes.md`.
- **L2 chat (L2 schema-v2 + role-graph expansion + `episodic_memories` rename) CLOSED 2026-06-01.** Settlement at `confirmation_docs/L2_CHAT_DECISIONS.md`. New ADRs 0151-0154; amendments to ADR-0044 §3, ADR-0094 §1, ADR-0150 §4 (split to §am-4 + §am-5 per Chat C IL-3).
- **L1/L3 reframe chat CLOSED 2026-06-01.** Settlement at `confirmation_docs/L1_L3_REFRAME_DECISIONS.md`. New ADRs 0155-0159 (Monitor lifecycle relocation; L3 bipartite topology; family-specific dont-know; DataState naming convention; capacity registration contract v2).
- **Chat C plan-authoring CLOSED 2026-06-02.** Settlement at `confirmation_docs/POST_PHASE_38_PHASE_MAP.md`. 4-rail DAG (A: rename → schema-v2; B: X1 → X2 → X3; C: L0 substrate; D: dream family) converging at Phase 46 (L4 substrate) → Phase 47 (L4 orchestrator) → Phase 48 (L5 v1) → Phase 49 (Integration C). See §3.1.7.
- **Two downstream design chats were named as Stream B rail prerequisites — both now CLOSED:** `L0_SUBSTRATE_CHAT` (absorbed into Phase 44 R0, SHIPPED 2026-06-04), `DREAM_FAMILY_CHAT` (absorbed into Phase 45 R0, SHIPPED 2026-06-07). **All four rails closed; the next chat is Phase 46 (L4 substrate convergence) — see `confirmation_docs/PHASE_45_NEXT_CHAT_PROMPT.md`.**
- **IS** in maintenance mode for tracked carry-forwards (see §6).

═══════════════════════════════════════════════════════════════════════
## 2. Shipped state (L0–L3) — what's true today

The L0-L3 numbered-phase rollout shipped Phase 00 → Phase 38 from 2026-05-03 to 2026-05-28. Phase 17, 23, 37 were retired. Phase 04 was superseded by 04-v2. Phase 05 split into 05a/b/c/d. Phase 26 split into 26a/b. **Phase 38 closed the L0-L3 rollout** with 3,379 passed / 57 skipped / 0 failed at squash `edb25df`.

### 2.1 L1 Core — shipped surfaces

- **Identity** (Phase 02): IRI primitives, IdentityRegistry, IdStrategy.
- **Graph elements** (Phase 03): Graph, Node, Edge, HyperEdge.
- **Schema** (Phase 04-v2): NodeType, EdgeType, HyperEdgeType; opt-in strict mode.
- **Metagraph** (Phase 05a-d): Metagraph, MetaEdge, MetaHyperEdge, IntergraphEdge (binary; Phase 05b), IntergraphHyperEdge (n-ary; Phase 05c), MetaEdgeType + MetaHyperEdgeType + MetagraphSchema. **Note on naming:** the primitive is `IntergraphEdge` (lowercase `g` in "graph"); the WSD project proposes `InterGraphEdge` (capital G). These are the same concept; **reconciliation CLOSED** — L1-6 (2026-06-01) kept the shipped `IntergraphEdge`; ratified at SKILL_ACQUISITION R0 (S13, 2026-06-09); WSD docs adopt the shipped spelling at authoring time.
- **Instancing** (Phase 06): sibling `mindsos_instances` package; 8 instance subclasses + ElementRegistry.
- **Persistence** (Phase 07): Client / FalkorClient / InMemoryClient / AsyncClient + Repositories + WAL + indexes + OCC.
- **Reconstruction** (Phase 08): MetagraphLoader + streaming + recover-on-load.
- **XRef** (Phase 09): cross-metagraph refs primitive.
- **Snapshot + soft-delete** (Phase 10): MetagraphSnapshot + tombstones + RemovalImpact.
- **Loader policy + schema migration** (Phase 11): Cypher integrity scanner + ADR-0134 schema migration.

### 2.2 L2 Knowledge — shipped surfaces

- **Identifiers + role IRIs + REF_TYPES** (Phase 12). **Note (L2 chat closure):** `memories` role rename → `episodic_memories` queued; atomic migration phase to ship per Chat C plan-authoring (ADR-0044 §amendment-3 + L2_CHAT_DECISIONS D-L2-16). Carry-forward L2-34.
- **8 role-graph schemas** (Phase 13): `ontology`, `lexicon`, `concepts`, plus the parametric `alignment:<role-a>:<role-b>` template, plus upper-layer schemas (~~`memories`~~ → pending rename to `episodic_memories`, `promoted-pipelines`, `task-patterns`, `problem-trace`, `capacity-state`). **L2 chat closure (2026-06-01):** schema v2 + role-graph expansion locked at ADR-0150 §amendment-4 + ADR-0152; closed role-set expands from 8 to 12 named + alignment-prefix (later 13 with installed-skills Phase 50, 14 with subminds, 15 with learned-pipelines (ADR-0203), 16 with installed-capacities (ADR-0150 §am-10); current = 16); `alignment` canonical form locked at `alignment:<a>:<b>` (ADR-0154; `identifiers.py:303` reconciliation tracked at L2-35).
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

### 3.1.11 Phase 39 ship closure (2026-06-02 end-of-day) — Rail A slot 1 SHIPPED

Phase 39 (`memories` → `episodic_memories` atomic rename + L2-35 alignment reconciliation + ADR-0146 §am-3 multi-NodeType dispatch) shipped as squash-merge commit `7a8bf10` on `main`; tag `phase-39-confirmed` cut from that SHA. The ship metadata + tester notes commit `6c73108` sits immediately before the squash-merge on main (semantically backwards but functionally correct — recovery anomaly recorded at `PHASE_39_DESIGN_LOG.md §9.5`).

**Final main commit order** (top → bottom):
- `7a8bf10` (tag: `phase-39-confirmed`) — Phase 39 squash-merge (the actual ship: 87 files, 1585 ins / 569 del).
- `6c73108` — `PHASE_39_CONFIRMED.md` + `notes-phase-39.md` via `mindsos confirm-phase`.
- `ec16443` (tag: `a0-corpus-landed`) — A0-5 doc closure.
- `f33db02` — A1 retention rule.

**Cumulative gate:** 3501 passed / 8 skipped / 0 failed. **mkdocs build clean** (only pre-existing carry-forward broken-link warnings; zero new from Phase 39 docs renames).

**Impl-chat artifacts on disk:**
- `confirmation_docs/PHASE_39_DESIGN_LOG.md §9` — impl-time amendments (R1/R2 picks beyond design pass, gate-driven follow-up commits 5b/5c, ship closure anomaly, Phase 43 carry-forwards).
- `confirmation_docs/PHASE_39_CONFIRMED.md` — `mindsos confirm-phase` auto-generated ship metadata.
- `confirmation_docs/notes/notes-phase-39.md` — tester notes (load-bearing per `PHASE_MAP §0`).

**Carry-forwards to Phase 43:**
- Stale `ROLE_MEMORIES` / `memory_iri` example code cleanup in non-amend-target ADRs (ADR-0045 / 0139 / 0143 / 0146 main body / 0147 / 0154 example IRI) — design log §9.6.
- Per-phase manifest-bump 9-surface checklist as cross-cutting decision (now in `POST_PHASE_38_PHASE_MAP.md §1`); doctor self-test gates this.
- Pre-confirm-phase squash-merge discipline (now in `POST_PHASE_38_PHASE_MAP.md §1`).

L2-34 + L2-35 backlog items closed at `docs/_workbench/L2_FUTURE_WORK.md` + `docs/_workbench/STREAM_A_BACKLOG.md`. Phase 43 chat opens against `phase-39-confirmed`.

### 3.1.12 Phase 43 full design pass closure (2026-06-03) — Rail A slot 2 design locked; ship pending

Phase 43 full design pass closed 2026-06-03 across **18 saturation rounds** (R1 rounds 1-16 reaching 3/3; R2 rounds 17-18 reaching 3/3; R3 cross-check round closing). Settlement at `confirmation_docs/PHASE_43_DESIGN_LOG.md` — ~600-line record covering R0/R0b drift reconciliation, ADR transcription parity findings, PR1/PR2 module-touch + test surface + commit boundaries, process locks, 5 R2 amendment-text drafts ready-to-paste, lessons for future phases, risk notes for tester ship pass.

**Picks locked beyond pre-R0 design pass (overrides `PHASE_43_R0_PICKS_SEED.md` / `PHASE_43_R0B_DERIVATIONS.md` / `POST_PHASE_38_PHASE_MAP.md §4 Phase 43 row` where drift surfaced):**

- **L2Schema(Schema) subclass placement at L2** (not L1 amendment to `mindsos_core.Schema`). ADR-0153 §amendment-1 supersedes §6's "mindsos_core.Schema gains" language. Required-at-construction (no backward-compat default). R0 N4 probe rationale + ADR-0010 import-direction symmetry.
- **storage_mode is per-NodeType property** (not per-role-graph L2Schema class field). Per ADR-0151 §Decision + ADR-0152 §6 explicit model. Only `LearnedParameter.value` carries large-payload in Phase 43 scope. R0b §3.3 sketch dropped storage_mode from L2Schema entirely.
- **Storage tier string `"falkor_blob"`** per ADR-0151 line 58 (not `"falkor_large_property"` from R0b §3.2). R0b draft transcription error.
- **bootstrap.py field-only at Phase 43** per L2-37 split routing. Kahn topological-sort consumer/scheduler defers to Phase 44 (L0 substrate). Phase 43 ships `applies_after: frozenset[str]` declarations on 13 `ensure_*_role_graph` functions; no scheduler.
- **consolidate.py retargets at Phase 43** per R0 PB-43-9 (`type_="Memory"` → `type_="Episode"`; `memory_composite_iri` → `episode_iri`). Chat opener's "OUT OF SCOPE: Phase 48 owns retarget" was a stale read of pre-R0 default; R0 picks seed reversed and chat opener didn't absorb the reversal.
- **Detector form not migrator** per R0 PB-43-10: `tools/check_phase_43_confidence_state.py` (v1 production empty per probe; Phase 39 PB-8 precedent). ADR-0094 §am-1 line 77-80 in-place edit: "maintenance migrator" → "detector form."
- **3 new ADRs already Accepted on disk** per R0a-3; Phase 43 IMPLEMENTS contracts, doesn't ratify. ADR-0094 §am-1 already on disk per R0b §4 (only detector ships). Phase 43 authors **2 amendments + 4 in-place edits + 6 ADR stale-example cleanups + 3 decisions-doc cleanups**.
- **Two-PR + single-squash + single-tag** per R0 PB-43-1: both PRs target `phase-43` branch; PR1 = framework + 9-surface manifest bump + amendments; PR2 = 4 new schemas + episodic_memories body + consumers + tests + docs. Branch squashes to main at confirm-phase.
- **9-surface manifest bump lands in PR1** (not PR2 per R0 §4 module-touch). Phase 39 §9.4 atomic-9-surface discipline forbids splitting; PR1 ownership keeps cumulative gates green across both PRs.
- **PHASE_44_NEXT_CHAT_PROMPT seed at PR2 commit 6** per chat opener literal; Phase 44 inherits L2-37 consumer + L2-39 + L2-41 deferrals. NOT Phase 46 seed (Phase 46 gated on all 4 rails per DAG; multi-rail consolidation isn't Phase 43's job).

**Drift-accumulation lesson (NPB11-META, PHASE_43_DESIGN_LOG §10.1):** rounds 6-12 surfaced incremental drift between design-pass drafts (R0 picks seed, R0b derivations, chat opener, PHASE_MAP §4 row) and Accepted ADRs on disk. Future-phase chats should run **ADR transcription parity check as R1 step 0** — grep each draft's transcription tables against source ADR-on-disk; surface drift; correct draft, not ADR.

**Phase 43 ship is the next chat.** PR1 contents, PR2 contents, commit boundaries, test surface, R2 amendment text drafts, tester runbook, and risk notes are all in `PHASE_43_DESIGN_LOG.md`. The ship chat's input prompt is `confirmation_docs/PHASE_43_SHIP_CHAT_PROMPT.md`.

**Cascade to other phases (PB-Z reading-list updates):**
- **Phase 44 R0** reads Phase 43 `bootstrap.py` diff (L2-37 split — Phase 44 implements the Kahn scheduler that consumes `applies_after` declarations Phase 43 ships) + `episodic_memories.py` diff (Phase 44's `kl.read_at_version` + `kl.retire_version` touch episode storage) + `mindsos_server/audit.py` (Phase 44 adds `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` constant).
- **Phase 46 R0** reads Phase 43 `_base.py` (L2Schema subclass) + `knowledge_layer.py` (bootstrap dispatch table) + `write_handle.py` (discipline enforcement body) — Phase 46 L4 substrate consumes the L2 invariant.
- **Phase 48 R0** reads Phase 43 `consolidate.py` retarget + `episodic_memories.py` body (Episode + Memory + memory_contains_episode) — Phase 48 L5 v1 builds on the retargeted MM consolidation path.

### 3.1.13 Phase 43 ship closure (2026-06-03) — Rail A slot 2 SHIPPED

Phase 43 (L2 schema-v2; 4 new role-graphs; mutation_discipline runtime invariant; per-NodeType storage_mode; bootstrap `applies_after` field; ADR-0094 §am-1 detector; consolidate retarget Memory → Episode; episodic_memories body finalize) shipped as squash-merge commit on `main`; tag `phase-43-confirmed` cut from that SHA.

**Ship contents.**

- **8 commits PR1** + **2 follow-ups (5b + 5c)** — design closure landing + ADR amendments + `_base.py` (Discipline / StorageMode / L2Schema) + `MutationDisciplineError` + `validate_mutation_discipline` + `validate_partition_invariant` + 9 schema audits (`Schema(...)` → `L2Schema(mutation_discipline=...)`; Pipeline + TaskPattern + ProblemTraceEntry partition frozensets) + 9-surface manifest bump + 4 sentinel test files + ADR cleanup (6 stale-example ADRs + ADR-0151 frontmatter + ADR-0094 §am-1 + ADR-0143 cross-ref) + L2_CHAT_DECISIONS D-L2-3/4/10 cleanup.
- **6 commits PR2** — 4 new schema files (parameter_staging + pending_promotions + capacity_gaps + learned_parameters) + episodic_memories body finalize (Episode + Memory partitions + `MEMORY_CONTAINS_EPISODE` EdgeType per R6 nomenclature reconciliation) + identifiers.py (4 new ROLE_* + 4 IRI builders + 4 prefix entries + 4 `_KINDS_PER_ROLE` + 4 `_IRI_BUILDERS` tuple-key registrations) + bootstrap.py (`_GLOBAL_NAMED_ROLES` 6→9, `_LOCAL_NAMED_ROLES` 2→5, `_APPLIES_AFTER_BY_ROLE` 12 declarations with soft edge `episodic_memories ← {task-patterns}`, `applies_after` kwarg field-only) + KnowledgeLayer.discipline_for + KLWriteHandle admin_authored enforcement + consolidate Episode retarget + detector + 9 tests/phase_43 files + tests/phase_13 + tests/phase_33 updates.

**Cumulative gate:**

- PR1: **3544 passed / 0 failed / 8 skipped** (31:43).
- PR2: (filled at confirm-phase post-squash).
- **mkdocs build clean** (17 WARN pre-existing carry-forward; 0 ERROR + 0 new).

**Impl-chat artifacts on disk:**

- `confirmation_docs/PHASE_43_DESIGN_LOG.md §9` — impl-time amendments (P1-P5 pre-impl, Q1-Q5 + R1-R5 round 2-3, R6 architectural memory_contains_episode, R7-R10 in-flight discoveries, R11-R12 pair-execution + confirm-phase workflows, 5b + 5c gate-driven follow-up records).
- `confirmation_docs/PHASE_43_CONFIRMED.md` — `mindsos confirm-phase` auto-generated ship metadata.
- `confirmation_docs/notes/notes-phase-43.md` — tester notes (load-bearing per `PHASE_MAP §0`).

**Carry-forwards to Phase 44:**

- **L2-37 consumer/scheduler.** Phase 43 ships `applies_after` field declarations; Phase 44 implements the Kahn topological-sort scheduler that consumes them (per L2_FUTURE_WORK §11 + L2-37 split + NPB11-1).
- **L2-39 audit constant.** `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` + capability per D-L2-23; routed to L0_SUBSTRATE_CHAT scope.
- **L2-41 KL retention surface.** `kl.read_at_version` + `kl.retire_version` per D-L2-18; routed to L0_SUBSTRATE_CHAT scope.
- **Pair-execution discipline.** Cowork (sandbox) prepares file content via Edit/Write tools; user runs git on Mac; Linux runs cumulative gates via docker. Established as default for all future Phase ship chats (R11; reasoning: Cowork sandbox `.git/` is read-only). See §9.
- **6-step confirm-phase workflow.** Cowork drafts notes-phase-N.md content + layer title + tester_notes copy-blocks; tester runs `mindsos confirm-phase --init-notes N` (Mac) to mint the notes file from template; tester edits notes file on Linux; tester runs `mindsos confirm-phase --phase N --notes-file notes-phase-N.md` on Linux from post-squash main; tester commits PHASE_N_CONFIRMED.md + notes-phase-N.md + pushes (R12). See §9.

**Process discipline learnings (carry to Phase 44+ design closures):**

- ADR transcription parity check as R1 step 0 default (per design log §10.1).
- PHASE_MAP §4 row scope-rewrite at PR2 last commit, not just SHIPPED status flip (per design log §10.2).
- Design-pass closures must commit closure artifacts before ending (P1 surfaced; carry-forward established).
- Buildability-scan over locked commit boundaries before ratification (P2 + Q1 surfaced; carry-forward established).
- Docker test image is NOT bind-mounted source; must rebuild after each push (R10).

### 3.1.14 Phase 44 ship closure (2026-06-04) — Rail C L0 substrate SHIPPED

Phase 44 (combined design+ship under option C — `L0_SUBSTRATE_CHAT` absorbed into R0) shipped on `main` via FF; tag `phase-44-confirmed` at the ship commit.

**Ship contents (as-shipped — narrower than the original plan; see below):**

- **PR1** — `FalkorDBLocalPersister` (native round-trip via `MetagraphRepository.persist` / `MetagraphLoader.load`; scoped `metagraph_id`-keyed delete since Locals co-reside with Global in one FalkorDB graph; per-user mutex). ADR-0160 (Falkor-only persister + shared-graph/scoped-delete substrate contract), ADR-0161 (KL version surface — unconsumed, Phase 48), ADR-0011 §am-3. `tests/phase_44/` (sentinels + persister units, `InMemoryClient`).
- **PR3** — `kahn_sort` + `BootstrapCycleError` (L2-37 consumer; consumes the Phase-43 `_APPLIES_AFTER_BY_ROLE` field; wired into `KnowledgeLayer.bootstrap()` × 3 sites — zero behavioral change since the one edge is cross-scope). `CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY` + `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` (L2-39; `ADMIN_CAPS`/`ALL_CAPABILITIES` 9→10; parity sentinel). + 14-surface version bump 43→44.
- **PR2 dropped** (CR-3 deferred).

**Cumulative gates:** PR1 = **3619 / 8 skipped / 0 failed**; PR3 = **3630 / 8 skipped / 0 failed**.

**Grounding-driven scope reversals (consumer discipline — ship only what has a v1 consumer):**

- **CR-2:** "ship both persisters" → **Falkor-only**. The `mindsos_cli` state-file serializer is disk-coupled/multi-file; `SQLiteLocalPersister` had no v1 consumer. SQLite + `MetagraphDump` + the `mindsos_cli`→`mindsos_core` serializer promotion deferred → first local-first/portable-export consumer.
- **CR-3:** "MindsOSServer class refactor now" → **deferred**. `login`/`logout` don't write Locals at v1 (PB-37); the hooks had no consumer. Orchestrator stays free-function per PB-38. Class + hooks → L4/L5 Local-write phase.
- **S6** (`read_at_version`/`retire_version`) → Phase 48 / L3-L4 (ADR-0161 froze the `_retired_inline_pending` marker name). **L2-10** (`validate_local_to_global_ref` wiring) → first Local→Global ref-write flow.

**Maintenance carry-forwards (L0_FUTURE_WORK §7):** L0-24 pre-existing `admin↔persistence↔mindsos_admin` import cycle (lazy-import fix in `promotion.py`; remove `tests/phase_44/conftest.py` band-aid — full diagnosis `PHASE_44_DESIGN_LOG.md §12`); L0-25 live-FalkorDB persister round-trip + scoped-delete coverage test.

**Full record:** `confirmation_docs/PHASE_44_DESIGN_LOG.md` (§1 R0 saturation S1-S8, §5-§10 the four reversals, §11 ship state, §12 import-cycle) + `PHASE_44_CONFIRMED.md` + `notes/notes-phase-44.md`.

### 3.1.15 Phase 40 ship closure (2026-06-05) — Rail B X1 SHIPPED

Phase 40 (L3 X1: ADR-0157 family-specific dont-know contracts + ADR-0158 DataState realm naming) shipped as squash-merge `5aee00f` on `main`; confirm artifacts cherry-picked at `cf3faeb`; tag `phase-40-confirmed` at `cf3faeb`. First Rail B slot; opens Phase 41 (X2).

**Ship contents:**

- **`mindsos_capacity/family_rules.py`** (new) — `FamilyDontKnowShape` (5-shape catalog: DATASTATE_MARKER / OPTIONAL_RETURN / VERDICT / VALIDATION_RESULT / NO_DONT_KNOW) + `FAMILY_RULES` dict (verbatim ADR-0157) + `family_rule_for(capacity_iri)` two-level prefix lookup (via `parse_capacity_iri`; malformed → `ValueError`) + `DS_UNHANDLED_INPUT = "datastate:marker.unhandled_input"`.
- **`mindsos_capacity/identifiers.py`** — 9 `REALM_*` constants + `RESERVED_REALMS` frozenset (ADR-0158). **Home corrected from the PHASE_MAP row's `mindsos_knowledge`** (D1; layer-correct + dissolved the Phase-39/43/44 `identifiers.py` collision concern — that file is L2; the L3 one was untouched since Phase 33).
- **`mindsos_capacity/capacity_layer.py`** — `register_datastate` strict realm validation (single-dot + reserved-realm) + `allow_new_realm` opt-in.
- **`mindsos_cli/commands/confirm_phase.py`** — PB-2 `_phase_exceeds_manifest` (high-water-mark: accepts a slot ≤ manifest, rejects only ahead) + `image_tag` derived from the manifest phase.
- `docs/concepts/capacity-families.md` + mkdocs nav; `tests/phase_40/` (5 files); export-slate sentinels 110→114 (phase_29/31/33/34).

**Cumulative gate:** 3670 passed / 8 skipped / 0 failed.

**Grounding-driven scope decisions (Phase 44 consumer discipline applied):**

- **PB-1:** `DontKnowReason.UNHANDLED_INPUT` **deferred to L4** (Phase 46/47) — the enum does not exist; its siblings are L4 MappingResult semantics; no v1 consumer. `test_dont_know_reason_enum.py` dropped.
- **PB-6:** `DS_UNHANDLED_INPUT` **constant-only** — no bootstrap node; no builtin DataState (text.*/mm.*/problem_trace.*) is product-bootstrap-registered, so a single-marker bootstrap with no v1 reader = consumer-less forward-shape.
- **PB-8 (latent, routed):** ADR-0157 `FAMILY_RULES` keys (`derive`, `signal`) don't match shipped `FUNCTIONAL_CATEGORIES` (`derivation`, `signalling`) and omit 7 shipped categories → they resolve via the permissive `DATASTATE_MARKER` default. Latent at v1 (all 3 shipped capacities classify correctly). Transcribed verbatim per NPB11-META; reconciliation routed to **Phase 42 (X3) Phase-27 audit** + WSD/FOL installation chats.
- **PB-2:** confirm-phase **high-water-mark** under the rail DAG — slot 40 ≤ high-water 44 ships with **no version bump**; PHASE_MAP §1 manifest row amended. Patches the PB-S assumption that missed out-of-order confirms.

**Gate-driven follow-up (1 cycle):** strict realm validation broke 38 pre-existing fixtures using non-reserved test realms (phase_29 `analysis`, phase_30 `test`). Fixed: phase_29 `analysis.sentiment`→`nlu.sentiment` (builder-local rename); phase_30 `allow_new_realm=True` at all 12 register sites (preserves the deliberate `test.` isolation namespace + IRI-literal assertions). **Lesson:** the S2 shipped-DataState sweep must include all test-fixture register sites, not just production + one probe file.

**Ceremony anomalies (non-blocking):** confirm-phase ran on `phase-40`-tip `d0d8201` (content-identical to the squash; CONFIRMED.md `git_sha` ≠ tag SHA — Phase 39-class); the cherry-picked confirm-artifacts commit carries the Linux box's placeholder author identity (stale Linux `git config`).

**Full record:** `confirmation_docs/PHASE_40_DESIGN_LOG.md` + `PHASE_40_CONFIRMED.md` + `notes/notes-phase-40.md`.

### 3.1.16 Phase 41 ship closure (2026-06-05) — Rail B X2 SHIPPED

Phase 41 (L3 X2: ADR-0155 Monitor-lifecycle retirement from L3) shipped as squash-merge `9330550` on `main`; confirm artifacts at `ba7c469`; tag `phase-41-confirmed` at `ba7c469`. Second Rail B slot; opens Phase 42 (X3). Impl of a settled design (L1_L3_REFRAME §D36, saturated R3; ADR-0155 Accepted on disk — no status flip).

**Ship contents:**

- **`mindsos_capacity/capacity_layer.py`** — removed `start_resident` / `stop_resident` / `active_subscriptions` methods + the `_subscriptions` field; added `iter_monitors() -> List[Monitor]` (filters the shared IRI-keyed `_declarations`; Local-wins inherited; no v1 consumer — the L4 `MonitorSubscriptionRegistry` lands Phase 46, acceptable per DAG).
- **`mindsos_capacity/runtime.py`** — removed `ResidentSubscription` dataclass (kept Phase-30 `invoke`/`ProblemTraceSink`/`ProblemTraceRecord`); trimmed now-unused imports.
- **`mindsos_capacity/exceptions.py`** — removed `ResidentError` (kept the other 7 classes).
- **`mindsos_capacity/identifiers.py`** + `capacity.py` — `KIND_RESIDENT` (`"resident"`) → `KIND_MONITOR` (`"monitor"`) + `NODE_KINDS`; `Monitor.node_kind` follows. node_kind triad now REACTIVE/MONITOR/ADAPTER.
- **`mindsos_capacity/__init__.py`** — `__all__` 114→112 (−`ResidentSubscription`, −`ResidentError`, −`KIND_RESIDENT`, +`KIND_MONITOR`).
- Tests: 9 phase_31 resident test files deleted whole; `tests/phase_31/_fixtures.py` pruned to its text-builtin helpers (shared by surviving text tests — NOT deleted); `tests/phase_27` node_kind rename; export-slate flipped 114→112 across phase_29/31/33/34 + membership flipped present→absent in phase_31/phase_33; `tests/phase_41/` (4 files: resident_infrastructure_retired, iter_monitors, kind_monitor_rename, adr_amendment_sentinels).
- Docs: ADR-0073 (+§amendment-1) → Superseded by ADR-0155; ADR-0155 §Implementation (Phase 41) marker; glossary "Resident" entry + summary/capacity.md ADR-0073 row + dev/internals/capacity.md annotated. **§3.1 (this file) was already amended by Chat C** — no further edit.

**Cumulative gate:** 3660 passed / 8 skipped / 0 failed.

**Grounding-driven corrections (Phase 44 consumer discipline applied):**

- **"Phase 31 module deletes whole" is test-only.** Production was **surgical** (the three modules host Phase-30 occupants); only the 9 resident *test* files delete whole. PHASE_MAP/ADR estimated "~6-8 files".
- **`_fixtures.py` is shared** by 5 surviving text tests → pruned, not deleted (the S2 test-fixture sweep, caught at R0; no gate-1 cascade).
- **`docs/concepts/monitors.md` is a phantom** — PHASE_MAP "Modules touched"/"confirms" lists a file that does not exist; doc amendments redirected to glossary/summary/internals.
- **grep-zero pass criterion is unsatisfiable repo-wide** (ADR-0155 + superseded ADR-0073 + the sentinel test legitimately contain the strings) → the retirement sentinel `tests/phase_41/test_resident_infrastructure_retired.py` is **scoped to the shipped package**: importability assertion + grep over `mindsos_capacity/**/*.py`.
- **`KIND_RESIDENT`→`KIND_MONITOR` is a VALUE change** (`"resident"`→`"monitor"`), not just a symbol rename — node_kind migration empty at v1 (no persisted Monitor instances).
- **No version bump** (slot 41 ≤ high-water 44; PB-2 convention from Phase 40).
- CHANGELOG left untouched (stops at Phase 38; 39/40/43/44 added no entry — consistency).

**Carry-forward to Phase 46 (L4 substrate):** implement `MonitorSubscriptionRegistry` (session-scope `Dict[DataState IRI, List[Monitor IRI]]`) consuming `cl.iter_monitors()` + per-task lazy Monitor `CapacityInstance` instantiation + orchestrator-thread-only register/unregister. PB-8 `FAMILY_RULES` vocabulary reconciliation (routed from Phase 40) is owned by **Phase 42 (X3)** Phase-27 audit (L3-57).

**Full record:** `confirmation_docs/PHASE_41_DESIGN_LOG.md` + `PHASE_41_CONFIRMED.md` + `notes/notes-phase-41.md`.

### 3.1.17 Phase 42 ship closure (2026-06-07) — Rail B X3 SHIPPED (completes Rail B)

Phase 42 (L3 X3) shipped as squash-merge `39a312c` on `main`; confirm artifacts at `e0a1453`; tag `phase-42-confirmed` at the confirm-artifacts commit `e0a1453` (the release workflow requires `PHASE_NN_CONFIRMED.md` present at the tagged commit — see Ceremony notes). Third + final Rail B slot — **Rail B (X1→X2→X3) is complete.** Implements the Accepted ADR-0156 (bipartite topology) + ADR-0159 (registration contract v2) + the Phase 27 dont-know audit (L3-57) + Model C remediation.

**Ship contents:**

- **`mindsos_capacity/capacity_layer.py`** — `register_capacity` emits `PRODUCES` (capacity→DataState) + `CONSUMES` (DataState→capacity) IntergraphEdges from the declaration's outputs/inputs; `if_exists: Literal["raise","upsert"]` (upsert = idempotent re-emit via `_has_intergraph_edge`); `_validate_contract_fields` (inline⇒max_latency_ms; structural precondition/effect IRIs, predicate-resolution soft). Retired `register_datastate` discovery hook + `rediscover` method + the discovery/`DiscoveryFailedError` imports.
- **`mindsos_capacity/capacity.py`** — `_CapacityBase` +6 fields (`concurrent`, `inline`, `max_latency_ms`, `precondition_iri`, `effect_iri`, `reads_mm`); `to_properties()` stops serialising `inputs`/`outputs`.
- **`mindsos_capacity/views.py`** — edge-sourced `producers_of`/`consumers_of` + new `inputs_of`/`outputs_of`; two-hop `successors_of`→`List[str]`; `SuccessorHop` retired (zero production consumers — ADR-0156 probe #8 was empty).
- **`mindsos_capacity/pipeline.py`** — `find_pipeline` BFS reads `view.outputs_of`/`inputs_of` (bipartite). Semantic-preserving vs Phase 30 + Integration B.
- **`mindsos_capacity/discovery.py`** — **deleted whole** (~330 LOC). `EDGE_TYPE_COMPAT` retired from `identifiers.py`/`schemas.py`/`exceptions.py`(`DiscoveryFailedError`).
- **`mindsos_capacity/context.py`** (NEW) — frozen 10-field `CapacityContext` (read-only `MappingProxyType` snapshots) + 4 `@runtime_checkable` Protocols (`MMHandle`/`KLHandle`/`CapacityLayerHandle`/`CancelToken`) + `CancelTokenView` + 5 verdict dataclasses (inline). Import-isolated.
- **`mindsos_instances/`** — `IntergraphEdgeInstance` + `IntergraphHyperEdgeInstance` (catalog 8→10; reconstruction `_KIND_TO_CLASS` + repository dispatch wired; `materialise` deferred to Phase 46).
- **`tools/check_phase_42_bipartite_state.py`** (NEW) — detector (PB-7; a migrator would be dead code — in-memory-first CapacityLayer, no persisted Global capacity state).
- **L3-57 (PB-8 Opt 3):** `family_rules.FAMILY_RULES` rename `derive`→`derivation` / `signal`→`signalling` + add `consolidate`/`trace`; `DEFERRED_DEFAULT_CATEGORIES` (5, test-pinned); `confirmation_docs/PHASE_27_DONT_KNOW_AUDIT.md` + ADR-0157 §amendment-1.
- **Docs:** ADR-0069/0086 → Superseded by ADR-0156; ADR-0156/0159 §Implementation footers; 8 amendment ADRs (0070/0071/0132; 0072/0078/0143/0146/0147); live capacity docs scrubbed to bipartite (Model C, PB-16 Opt B).
- **Exports:** `mindsos_capacity.__all__` 112→117; export-slate flipped across phase_29/30/31/33/34; phase_29 discovery suite retired (13 files; slate kept + flipped to retirement checks); `tests/phase_42/` 8-file suite.

**Cumulative gate:** 3669 passed / 9 skipped / 0 failed.

**Grounding-driven decisions (full record `PHASE_42_DESIGN_LOG.md` §5–§8):**

- **PB-7 — migrator → detector** (no persisted Global capacity state; Phase 39/43 reversal repeats).
- **PB-23 — capacity-body `context["kl"]`→`context.kl` + `invoke`→CapacityContext plumbing DEFERRED to Phase 46.** ADR-0159's `CapacityContext` carries no `session`-object field for ADR-0146 write-body capability gating; the ADR-0146/0159 boundary is L4-substrate (Phase 46) territory. `CapacityContext` ships as a forward contract (exported, isolated-tested).
- **PB-24 — instance `materialise` deferred to Phase 46** (capacity-MM instantiation is its first consumer).
- **PB-22 — edge-type values UPPERCASE** (`"PRODUCES"`/`"CONSUMES"`, already shipped) per ADR-0021 regex; ADR-0156 body lowercase = instance-layer label convention.
- **PB-16 — `mkdocs --strict` clean RE-SCOPED (Option B):** 17 pre-existing server-pivot-era broken-link warnings (zero Phase-42-related) tracked to a docs-maintenance item; criterion = non-strict build succeeds + no Phase-42 regression.
- **Parity:** "5 new fields" is 6; "9-field CapacityContext" is 10 (corrected in `context.py` + tests + PHASE_MAP).
- **grep-zero sentinel scoped to `mindsos_capacity/**`** (PB-3; repo-wide unsatisfiable).
- **Gate-1 follow-up (test-only):** phase_27/phase_28 `to_properties` no longer carries inputs/outputs (assert absent + verify edges); phase_29 slate flipped present-checks → retirement checks. 8 fails → 0; no source change.

**Carry-forward to Phase 46 (L4 substrate):** wire `invoke`→`CapacityContext`, migrate the 3 capacity bodies (`consolidate`/`trace`/text) to `context.kl`, resolve the ADR-0146/0159 session-gating boundary, implement `KLHandle.read_at_version` (Phase 48), and `materialise` the two intergraph instance subclasses (capacity-MM instantiation).

**Ceremony notes:** confirm-phase ran on the branch tip then was cherry-picked onto `main` (Phase 40 anomaly recurred); the confirm-artifacts commit `e0a1453` carries a placeholder author (`git config` copy-paste) — cosmetic, tag unaffected. **Fix the Linux `git config` identity before the next ship.** **Release CI was initially RED:** the tag was first placed at the squash `39a312c`, which predates `PHASE_42_CONFIRMED.md` (added in `e0a1453`); `release.yml` checks out the tag and requires the confirmation doc *at the tagged commit*, so the tag was moved to `e0a1453`. **Lesson: tag `phase-NN-confirmed` at the confirm-artifacts commit, not the squash** (the Phase 41 precedent — `ba7c469` — was correct; HANDOFF §9's generic "squash-merge commit" wording is wrong for the release gate and should be read as "the commit containing `PHASE_NN_CONFIRMED.md`"). No version bump (slot 42 ≤ high-water 44). CHANGELOG untouched (stops at Phase 38).

**Full record:** `confirmation_docs/PHASE_42_DESIGN_LOG.md` + `PHASE_42_CONFIRMED.md` + `notes/notes-phase-42.md`.

### 3.1.18 Phase 45 ship closure (2026-06-07) — Rail D L3 dream family SHIPPED (closes the last rail)

Phase 45 (Rail D; combined design+ship under option-C via DREAM_FAMILY_CHAT) shipped as squash-merge `ab32e3d` on `main`; confirm artifacts at `e76a1a3`; tag `phase-45-confirmed` at the confirm-artifacts commit `e76a1a3`. **Rail D was the only remaining slot before Phase 46 convergence — all four rails (A 39/43, B 40/41/42, C 44, D 45) are now closed.** Implements ADR-0162 (newly authored here) + Chat B D-B5..B9 + the L3-51 family contract.

**Design saturation:** DREAM_FAMILY_CHAT ran R0→R3 (4 rounds). R0 settled the central fork (S1 directive-emitter, user-confirmed); R1 transcription-parity probe clean + buildability locks; R2 confirmations; R3 probed live code and corrected one sentinel chain-parent error (Phase 38 has `test_phase_38_doc_sentinels.py`, not a `test_adr_amendment_sentinels.py` — Rail D mirrors Phase 44's independent-rail root instead). Full record: `confirmation_docs/PHASE_45_DESIGN_LOG.md`.

**Ship contents:**

- **`mindsos_capacity/builtins/dream.py`** (NEW) — `DreamExecutionPolicy` (2-value enum: `replay_recorded` / `re_execute_capacities`; `hybrid` is an ADR-0162 §v2 reservation, no v1 member); `ReplanInjectionDirective` + `DreamDirective` (consumer-local dataclasses, NOT top-level exported); `DS_DREAM_TASK_REF` + `DS_DREAM_DIRECTIVE`; 3 directive-emitter bodies; 3 `build_dream_*` factories; idempotent `install_dream_capacities` (DataStates-first, partial-state detection — consolidate/text precedent).
- **`mindsos_capacity/capacity.py`** — `DreamCapacity(_CapacityBase)` subclass (`execution_policy` + `entry_point` fields; `to_properties()` override; `node_kind=REACTIVE`), alongside Monitor/Adapter; `__all__` +1.
- **`mindsos_capacity/__init__.py`** — re-export `DreamCapacity`; top-level `__all__` **117→118**.
- **`mindsos_capacity/identifiers.py`** — `CATEGORY_DREAM = "dream"` (+ `__all__`). Deliberately **NOT** in `FUNCTIONAL_CATEGORIES`: the dream category graph is created lazily by `ensure_category_graph` at first register (text.* precedent), so `create_global` is unchanged.
- **ADR-0162** (Accepted; `§Implementation (Phase 45)` footer) + `docs/concepts/dream.md` + mkdocs nav.
- **9-surface version bump 44→45** (first slot to exceed the high-water mark → a real bump, contrast 40/41/42): manifest phase+version, pyproject, 7 `__version__`, docker-compose phase45 tags. Export-slate sentinel flips: count **117→118** (phase_29/31/33/34), version **phase44→phase45** (phase_30/31/34).
- **`tests/phase_45/`** (5 files): maintenance / exploration / retry / signal_provenance / adr_amendment_sentinels (Rail D chain root, mirrors Phase 44).

**Cumulative gate:** 3694 passed / 9 skipped / 0 failed (Linux docker, 31:56). Manual smokes: `doctor --self-test` green at phase45; dream install + introspect + retry replan-injection invoke verified.

**Grounding-driven decisions (consumer discipline — ship the L3 contract ahead of its consumer):**

- **S1 — directive-emitter bodies.** Dream capacities have **no v1 L3 consumer** (the L4 dream loop is Phase 46/47; the L5 hookup Phase 48). Bodies emit a `DreamDirective`; the MM deep-copy + live re-execution + ALS signal firing are L4/L5, out of scope. Same pattern as iter_monitors (Phase 41) / bipartite walk + CapacityContext (Phase 42).
- **S4 — replan-injection as a directive field.** `dream.retry` on a failed episode emits a populated `ReplanInjectionDirective` (`replan_level=taskrun`); the L4 loop performs the actual replan. Non-failed / missing episode → `None` (OPTIONAL_RETURN dont-know).
- **Pre-provisioned surfaces needed ZERO edits:** `FAMILY_RULES['dream']` (OPTIONAL_RETURN, Phase 42 — resolves via the `family_rule_for` category fall-through), `REALM_DREAM` (Phase 40). No `family_rules.py`, no `bootstrap`/`FUNCTIONAL_CATEGORIES`, no realm edits.
- **`dream_source_episode_iri`** ships as a `DreamDirective` field (provenance); live signal tagging is Phase 48.

**Ceremony notes (Phase 40/42 anomaly recurred — non-blocking):** confirm-phase ran on the `phase-45` branch tip (commit `1e0fbf1`, parented at the pre-squash branch commit), so the confirm artifacts were **cherry-picked onto `main`** (`e76a1a3`); `PHASE_45_CONFIRMED.md` content is identical to the squash (only its recorded git_sha differs from the tag — the documented Phase 39/40/42-class cosmetic anomaly). Tag placed at the confirm-artifacts commit `e76a1a3` (NOT the squash) per the Phase 42 release-gate lesson — `release.yml` requires `PHASE_45_CONFIRMED.md` at the tagged commit. CHANGELOG untouched (stops at Phase 38).

**Carry-forward to Phase 46 (L4 substrate):** the L4 dream-cycle timer interface (reads `execution_policy`/`entry_point` off the registered dream nodes + invokes the bodies for directives), MM deep-copy + live re-execution + ALS signal firing under each directive, and `invoke`→`CapacityContext` plumbing for dream bodies (PB-23). `hybrid` policy + cross-level entry-points are v2.

**Full record:** `confirmation_docs/PHASE_45_DESIGN_LOG.md` + `PHASE_45_CONFIRMED.md` + `notes/notes-phase-45.md`.

### 3.1.19 Phase 46 ship closure (2026-06-08) — L4 substrate SHIPPED (convergence point)

Phase 46 (the L4-substrate convergence) shipped as squash-merge `47c3568` on `main`; confirm artifacts at `18ba793`; tag `phase-46-confirmed` at the confirm-artifacts commit `18ba793` (per the Phase 42 release-gate lesson — `release.yml` requires `PHASE_46_CONFIRMED.md` at the tagged commit). **First L4 code ever written.** Implements Chat A R1 D32 substrate + Chat B D-B10/B11/B13/B14 MM substrate + ADRs 0163-0170 (8, authored at R0).

**Ship contents:**

- **`mindsos_intelligence/`** (NEW top-level package, first L4): `intelligence_layer.py` (IntelligenceLayer lifecycle `start`/`enqueue`/`stop("abort")`; `stop("pause")`→`NotImplementedError` per Push 5; `DreamCycleTimer` + `fork_dream_mm` deep-copy primitive), `executor.py` (priority-tier Executor over `(tier,-attention_score,submit_time)` + worker pool + single `write_priority` primitive + cooperative auto-preempt), `rwlock.py` (writer-preferred RWLock), `mm.py` (three-sub-MM container + thin root + `deep_copy`), `mm_resolver.py` (concrete `MMHandle`: lazy single-node + monotone-grow + pin-at-instantiation), `cancellation.py` (concrete `threading.Event` `CancelToken` satisfying the L3 Protocol + re-exported `CancelTokenView`), `signal_triage.py` (always-on thread + tier-passthrough stub classifier), `als_registry.py` (D9.1 dataclass + empty v0 catalog), `monitor_subscription.py` (`subscribes_to`-inverted registry consuming `cl.iter_monitors()`).
- **L3 prerequisites:** `mindsos_capacity/tiers.py` (`TierEnum` + per-tier default scores + `DEFAULT_HYSTERESIS`); `context.TierVerdict.tier` narrowed `Optional[Any]`→`Optional[TierEnum]`.
- **`mindsos_instances`:** `materialise` for `IntergraphEdgeInstance` + `IntergraphHyperEdgeInstance` (closes Phase 42 PB-24; consumer = capacity-MM instantiation).
- **ADRs 0163-0170** (Accepted; §Implementation Phase 46 footers); 2 concept docs (`intelligence-layer.md`, `mm-substrate.md`) + mkdocs nav.
- **9-surface version bump 45→46** + manifest `[mindsos] packages` 8th entry (`mindsos_intelligence`) + new-top-level-package checklist (Dockerfile COPY both stages, pyproject include, sentinel_paths, tests_server domain-layer roster, host pip refresh).

**Cumulative gate:** 3793 passed / 9 skipped / 0 failed (Linux docker, 31:55). `doctor --self-test` green at phase46 (8-package parity). Manual `python3` smokes: lifecycle roundtrip=42; pause→NotImplementedError; deep-copy independence; tier order `['c','b','d']`.

**Shipped as a SINGLE PR.** PB-0 Opt B (two PRs) collapsed once S12 + the S9 L3 classifier deferred to Phase 47 — no PR-B content remained.

**Grounding-driven decisions (probe-first):** **PB-8** TierEnum home = L3 not L4 (layer isolation is test-enforced; the shipped `TierVerdict.tier` placeholder — *"the downstream TierEnum pending its owning family"* — confirmed the intent). Only `consolidate.py`/`trace.py` use `context.get("kl")` (no `text.*` migration). `CancelToken` mutator is `request_cancel()`. `CapacityContext` carries `session_id`/`user_id` but no capability handle → the write-body gate lives in L4 dispatch (ADR-0170 contract; enforcement Phase 47). **S12 (`invoke`→CapacityContext + body migration + write-gate) deferred wholesale to Phase 47** (user-ratified) — flipping `invoke`'s shipped signature is a corpus-wide change with no Phase-46 caller; **PB-23 closes at Phase 47, not 46.**

**Carry-forward to Phase 47 (L4 orchestrator):** consume the substrate — six-phase task lifecycle + `planning.*` v0 + the deferred surfaces (`invoke`→CapacityContext + body migration + write-gate enforcement; L3 `decision.signal_to_tier` replacing the passthrough stub; L3 `scoring.attention_score` + `update_priority` wrapper; the dream driver). **Phase 48:** dream live re-execution + ALS firing + replan-injection consumption; MM `attention_score` write-through to TaskRun; MM inline-on-retire (D'1).

**Ceremony note:** confirm-phase ran on **post-squash `main`** (no branch-tip cherry-pick anomaly this time — the Phase 40/42/45 pattern was avoided by squashing before confirming); tag placed at the confirm-artifacts commit. New-package host pip refresh (`pip install -e .`) was required before the host CLI/doctor saw `mindsos_intelligence`. CHANGELOG untouched (stops at Phase 38).

**Full record:** `confirmation_docs/PHASE_46_DESIGN_LOG.md` + `PHASE_46_CONFIRMED.md` + `notes/notes-phase-46.md`.

### 3.1.20 Phase 47 ship closure (2026-06-08) — L4 orchestrator SHIPPED

Phase 47 (the six-phase task-lifecycle orchestrator over the placeholder v0
catalogs) shipped on `main`. **Note on the squash:** the ship squash exists as
two equivalent commits — Mac `cd8abb0` and the canonical Linux squash `6f49524`
that `origin/main` carries; the confirm commit `db1a562` (`PHASE_47_CONFIRMED.md`)
holds the tag `phase-47-confirmed`. Phase 47's ship-closure was completed at the
start of the Phase-48 chat (the tag + confirm doc had not been committed when
Phase 47 ended).

**What shipped:** `orchestrator.py` (LifecyclePhase 1–6 + bounded-replan loop +
`update_priority` with `attention_score` write-through) + `phase_1.py` /
`plan_construction.py` / `execution.py` / `phase_6.py` / `replan_check.py` /
`sufficient_predicate.py` / `dispatch.py` (L4Dispatcher) / `chain_artifacts.py`
(8 chain types) / `signal_sources.py` (10 skeletons) / `als_subsystems.py` (11
skeletons); v0 L3 catalogs `builtins/{planning_v0,phase1_v0,orchestration_v0}.py`
(`placeholder=True`); ADRs 0171-0175; 9-surface bump 46→47; cumulative
**3832/9/0**. **S12 split read/write (ADR-0175 §am-1):** the read-half (typed
`CapacityContext` dispatch for v0 reads + the L4 write-gate scaffold) shipped at
47; the write-half (consolidate/trace migration + the authorization
reconciliation) was deferred to 48. Dream driver deferred wholesale to 48
(no episode corpus existed). Worker-per-task lifecycle (ADR-0171, no separate
orchestrator thread). **Full record:** `confirmation_docs/PHASE_47_DESIGN_LOG.md`
+ `PHASE_47_CONFIRMED.md`.

### 3.1.21 Phase 48 ship closure (2026-06-09) — L5 v1 SHIPPED (final convergence)

Phase 48 makes the Phase-47 chain artifacts **persist as Episodes** and wires
dream as live re-execution — the final convergence phase. Squash `af331e8` on
`main`; confirm artifacts `1952260` (`PHASE_48_CONFIRMED.md`); tag
`phase-48-confirmed` at `1952260` (release.yml requires the doc at the tagged
commit); cumulative **3863 passed / 10 skipped / 0 failed**; 10-surface version
bump 47→48 (no new package). Shipped as an R0 design pass (3 rounds + grounding;
`PHASE_48_DESIGN_LOG.md`) + 5 commit groups + 2 gate-fix commits.

**What shipped (surface → ADR):**
- **MM consolidation write path** (S1, ADR-0176) — `mindsos_intelligence/
  consolidation.py` freezes the MM + assembles the 6-field D-B47 Episode record
  + dispatches `consolidate:mm`; wired into all three orchestrator terminal
  paths (success/dont-know/abort = retain-by-default); guarded (skips in
  simplified mode / when no consolidate capacity + KL). `mm_root_ref` is a v1
  reference (heavy full-MM snapshot deferred).
- **Episode + Memory authoring** (S2/S3, ADR-0176) — `consolidate:mm` writes the
  6-field Episode `value` + materialises Memory on first episode per task-pattern
  (content-hash `memory_id`) + the `MEMORY_CONTAINS_EPISODE` edge.
- **S12 write-half closed** (S4, ADR-0180) — a pre-authorized, session-bound
  `writeable` capability injected onto `CapacityContext` (11th field) by a shared
  `make_writeable(kl, session)`; scope-aware gate **at write-time inside the
  capability** (Local → none, Global → `CAN_WRITE_GLOBAL`); built by the
  session-holder (L4 dispatch for tasks, `CapacityLayer.invoke` write-branch for
  the CLI). ADR-0146 + ADR-0170 both preserved (L3 holds no principal). **PB-23
  authorization half closes.** **A1′ deferral:** the read-path dict + the
  transitional union annotation are kept one more phase (no read-corpus churn);
  the cosmetic union-drop is deferred.
- **D'1 KL stack** (S6, ADR-0177 + ADR-0161 §am-1) — `kl.read_at_version` +
  `kl.retire_version` + `_retired_inline_pending` marker + `RESERVED_PROPERTY_KEYS`
  entry. ADR-0161's forward-contract shipped **none** of this at Phase 44; Phase
  48 lands the full stack. Opt-C signature keeps the shipped `(iri, version)`
  Protocol; multi-version-per-node latent.
- **D'1 inline-on-retire read consumer** (S7, ADR-0177) — `retention.py`
  `resolve_ref`/`resolve_refs`. **Unit-test-only at v1 (PB-9)** — no live consumer
  (dream re-runs from `task_input`, not full reconstruction); real consumers =
  WSD reconstruction/retrieval.
- **Dream-cycle driver** (S5, ADR-0178) — `dream_cycle.py` wires the Phase-46
  `DreamCycleTimer` callback → the 3 Phase-45 `dream.*` capacities → directives
  (with `source_episode_iri` provenance; `dream.retry` carries the
  ReplanInjectionDirective) → re-exec hook. **v1 re-runs from the episode
  `task_input` (PB-9);** faithful episode→MM reconstruction +
  `replay_recorded`-vs-`re_execute_capacities` differentiation + real ALS firing
  are **WSD-gated**.
- **Crash recovery** (S8, ADR-0179) — `crash_recovery.py` tombstone checkpoint
  markers at the D-B50 triggers + `IntelligenceLayer.start` startup scan →
  `crash_marker` Episode (idempotent on task id). Partial-MM content recovery →
  v1.5.
- **Retention monitoring** (S9) — `monitoring.py` `export_retention_metrics`
  (episode/Memory count + size histogram + Falkor-row count). Instrumentation
  only; retention **policy** → v1.5 (PB-QQ).
- **Docs** (S12) — `concepts/layers.md` + `concepts/society-of-mind.md` +
  `getting-started/facts-and-figures.md` (new) + `concepts/dream.md` Phase-48
  hookup section + nav.

**Grounding-driven decisions** (full record `PHASE_48_DESIGN_LOG.md §5` +
`PHASE_48_CONFIRMED.md` tester_notes): D'1 hooks absent at Phase 44 → land full
stack; the CLI is a write path → shared gate factory + `capacity_layer.invoke`
write-branch (A1′); PB-10 Local-write fix (the Phase-47 blanket pre-gate would
have denied a normal user's Local consolidate); 2 gate-fix commits (the
`consolidate.py` local `memory_iri` tripped the Phase-39 retired-name sentinel →
`mem_iri`; the docs-nav test skips when `mkdocs.yml` is absent from the test
image).

**Deferred to Phase 49 / WSD / v1.5:** union-annotation drop +
`capacity_layer.invoke` read-path → CapacityContext; faithful episode→MM
reconstruction + `replay_recorded` differentiation + real ALS firing (WSD);
partial-MM crash-content recovery (v1.5); retention policy (v1.5); durable
Falkor-backed checkpoint store.

**Full record:** `confirmation_docs/PHASE_48_DESIGN_LOG.md` + `PHASE_48_CONFIRMED.md`.

### 3.1.22 Phase 49 ship closure (2026-06-09) — Integration C SHIPPED (LAST numbered phase; plan complete)

Integration C is the **closing integration phase** of the post-Phase-38 plan. **No new feature surface** — it composes the shipped L0–L5 pieces into one end-to-end trivial-task scenario, ships the cookbook, and closes PB-HHH. Single squash `149fb26` on `main` off `phase-48-confirmed`; confirm `cc8a7f8`; tag `phase-49-confirmed`. Gate **3868 passed / 11 skipped / 0 failed** (the +1 skip vs Phase-48 is the cookbook **nav-wiring** test, which skips by design because `mkdocs.yml` isn't copied into the test image).

**Shipped (by surface):**
- **S1 — scenario harness + tests** (`tests/phase_49/`): `integration_c.py` (step helpers over one KL with all v0 + text + consolidate + dream catalogs); `test_integration_c_scenario.py` = deterministic in-memory companion (`test_chain_inmemory`) + `@pytest.mark.integration` live-Falkor headline (CLI login + Phase-44 native round-trip via `bootstrap_global_pair_from_falkordb` + `MetagraphRepository.persist` + the chain); cookbook-renders + ADR-sentinel tests. **Composition only — no production code changed** beyond the version bump.
- **S2 — cookbook** `docs/usage/cookbook/end-to-end.md` (+ mkdocs nav); `text-realm.md` format + honest "Does NOT" (v0 placeholders; the two-slice seam; dream synchronous; no physical indexes; the episode-flush gap).
- **S3 — PB-HHH / ADR-0181** Falkor index strategy **decide-and-document, zero index code**; named indexes (`Episode.task_pattern_iri`, `Memory.memory_id`, `IntergraphHyperEdge` membership) routed to **WSD retrieval** (first query consumer); `L5_FUTURE_WORK.md` L5-NEW-13 updated.
- **S5 — version bump 48→49** (10 surfaces): 8 package `__version__` + `pyproject` + `manifest.toml` `version`+`phase` + 2 docker-compose tags + export-slate (phase_30/31/34).

**Grounding-driven findings (probe-first):**
- `text.tokenize` is drift → the shipped capacity is `text.space_split` (applied throughout).
- The v0 lifecycle dispatches **no real L3 capacity** (`execution.py` emits a notional StepExecutionRecord), so the scenario is **two stitched slices** sharing one session+KL (PB-1a), not a single tokenize→consolidate chain.
- **PB-RT (R2 reanalysis; scope-changing):** the L0 node persister stores node `value` as a **primitive** (`cypher/builders.py::build_unwind_create_nodes` → `n.value = row.value`; ADR-0130 `_props_json` is metagraph-level only), but the L5 Episode `value` is a structured dict → flushing a consolidated Episode to FalkorDB would error. **Descoped** the live episode flush (the integration test exercises the Phase-44 machinery via the Integration-A/B-proven Global-pair round-trip; the Episode is asserted in-memory). **Durable episode persistence routed to `L0_FUTURE_WORK.md` L0-26** (couples with the Phase-48-deferred durable Falkor checkpoint store). Integration C did its job — the first end-to-end exercise surfaced a real L0↔L5 seam; **routed, not fixed here.**

**Gate-host forensic note (process):** the Linux gate box is a **separate checkout** from the Mac authoring tree; the first cumulative run executed against a **stale `phase-48` checkout** lacking `tests/phase_49` and returned the unchanged baseline. Always confirm the gate box's HEAD sha + `ls tests/phase_NN` before trusting a cumulative count.

**Plan status:** **ALL Phases 39–49 SHIPPED — the post-Phase-38 plan is COMPLETE.** Next chats = the downstream sequence per `POST_PHASE_38_PHASE_MAP.md §6` (SKILL_ACQUISITION_PROCESS → WSD / FOL / code-skill / adapter; L4-v2 follow-up; MAINTENANCE; DWF parallelizable). New MAINTENANCE/v1.5 carry-forwards from this phase: **L0-26** (node-value serialization for durable episodes) + **L0-25** (live FalkorDBLocalPersister round-trip coverage).

**Full record:** `confirmation_docs/PHASE_49_DESIGN_LOG.md` + `PHASE_49_CONFIRMED.md`.

### 3.1.23 Phase 50 ship closure (2026-06-10) — SA-1 skill-install lifecycle SHIPPED (first downstream phase)

First slot (and only slot) of `SKILL_ACQUISITION_PROCESS_PHASE_MAP.md`; design settled 2026-06-09, this ship chat ran R0 impl-locks only. Two PRs on `phase-50` off `main` `5177e34`; cumulative gate **3970 passed / 11 skipped / 0 failed / 1 xpassed** (standing L0-25 orphan xfail). Tag `phase-50-confirmed`.

**Shipped (by surface):**
- **ADR-0182 implementation** (L0): `mindsos_core/persistence/value_codec.py` (`encode_node_value`/`decode_node_value`) + `build_unwind_create_nodes` `_value_json` SET branch + `graph_repository` row split + `graph_loader` decode + `_CORE_KEYS`/`RESERVED_PROPERTY_KEYS` reserved-key adds; M3 sentinel **deleted**, replaced by `tests/phase_50/test_adr_0182_value_codec.py` + a structured-value case in the L0-25 live test. Closes L0-26's impl half (durable Episode persistence still rides v1.5 retention).
- **`installed-skills` role-graph** (ADR-0150 §am-6; closed set **12 → 13**): schema (`Discipline.APPEND_ONLY`, Global-only, `SkillInstallRecord` with STORAGE_MODE_FIELDS inline) + IRI builder/minter/parser + bootstrap rosters (`_GLOBAL_NAMED_ROLES`, `_APPLIES_AFTER_BY_ROLE`, `_GLOBAL_ROLE_ORDER`) + ~13 corpus roster-pin updates.
- **Caps/audit** (Phase-44 S8 pattern): `CAN_INSTALL_SKILL`/`CAN_UNINSTALL_SKILL` (ADMIN_CAPS 10→12) + `EVT_SKILL_INSTALLED`/`EVT_SKILL_UNINSTALLED`/`EVT_SKILL_INSTALL_REJECTED`; **latent Phase-44 drift fixed** — `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` appended to `ALL_AUDIT_EVENTS`.
- **Install lifecycle** (ADR-0183; `mindsos_server/skills/`): TOML manifest parser + digest; collect-all preflight (`PreflightReport`); install/uninstall driver (all writes via ADR-0180 `make_writeable`; append-only records; S8 idempotency triple incl. failed-run repair + reject-on-digest-mismatch/upgrade); de-install = reverse-dep refuse + **marker-only deprecation** (G1) + record flip; `apply_installed_skills(cl, kl)` free-function activation; `mindsos skill install/uninstall/list/activate` CLI (session-less Global-only per capacity-CLI precedent).
- **Reference bundle** `tests/fixtures/skill_bundle_ref/` (1 DataState + 1 CapacityContext-native `text.ref_shout` + 3 L2 nodes) + `tests/phase_50/` lifecycle tests (install → no-op → de-install → re-install → fresh-process activation) + live Falkor record round-trip (the ADR-0182 first-consumer proof).
- **10-surface bump 49→50.**

**Grounding-driven findings:** **G1** — design-log R2-1's "node-level deprecation already exists" was falsified at file level (the citation is the ADR-0133 *edge* filter; `deprecate_version` is a phantom); v1 de-install is marker-only, node read-filtering added to the v2 ledger. **I4/I5 bundle-author rules (binding on WSD):** content props must avoid `RESERVED_PROPERTY_KEYS`; schema type-membership is enforced even at strict=False — content must use the role's declared NodeTypes. **I6:** S4's same-bundle ownership waiver is load-bearing (no deregistration ⇒ in-process reinstall self-collides without it). Full list (I1-I9): `PHASE_50_DESIGN_LOG.md §4`.

**Next chat = WSD_INSTALLATION_CHAT** (`projects/wsd/FUTURE_CHAT_PROMPT.md`, banner updated; inheritance contract `SKILL_ACQUISITION_PROCESS_PHASE_MAP.md §5`). DWF parallelizable (L2-only).

> **UPDATE 2026-06-10 — WSD_INSTALLATION design CLOSED; slots reserved.** `WSD_INSTALLATION_DESIGN_LOG.md` (R0–R3) + `WSD_INSTALLATION_PHASE_MAP.md` on disk. **Phases 51–56 are WSD-*scheduled* (not WSD-*owned*)** (51 riders+empirical-layer → 52 corpus bootstrap → 53 capacity+`wsd-core` bundle → 54 lifecycle+v0-flip → 55 learning loop → 56 DWF-gated enrichment). **Ownership ≠ scheduling:** core mechanics built inside these slots (empirical-layer machinery, promotion-loop, L4 slot-shapes, the v0→real flip, `hint/predicate/decision` families, ADR-0181 indexes, L3-59(b)/L0-25 cleanup) are MindsOS-owned and reusable by FOL/DWF; WSD owns only `wsd-*` bundle content. Do not record WSD as owner of any core mechanic — authoritative per-item split = **phase-map §2.1 Owner column + design log §7** (`projects/wsd/`). DWF_INSTALLATION_CHAT opened in parallel 2026-06-10 — it takes Phase 57+ and owes WSD the alignment-density number (gates slot 56; coordination contract: `WSD_INSTALLATION_DESIGN_LOG.md §3`). Notable plan deltas vs the POST_PHASE_38 §6 WSD row (scope amendments in phase-map §4): importers 6→2 (SemCor+GlossTag); ALS = consumed subsystems only; `world-axioms` deferred (no ADR-0150 amendment anywhere in the plan); PB-T trimmed. Next ship chat seed: `WSD_PHASE_51_NEXT_CHAT_PROMPT.md`.

**Full record:** `confirmation_docs/PHASE_50_DESIGN_LOG.md` + `PHASE_50_CONFIRMED.md`.

### 3.1.24 Phase-1 interpretation seam + `needs_input` clarification — DESIGN ONLY (2026-07-02; NOT shipped, no code)

A **generic core** feature converged in the core-design chat; **ADRs 0195 + 0196 written as Proposed, design-only — nothing built.** Core-owned per RULES §8; **arc-solver (mOS-AS) is the first consumer** (interpretation-only) and owns no core component. Two **decoupled, independently-shippable** features: **(A, ADR-0195)** a pluggable Phase-1 interpretation seam — a construction-bound `Phase1Profile` (per-step slots, v0 fallback) + a standalone `interpret()` decoupled from `run_lifecycle`, `resolve`-in-interpretation, opaque-dict hints + `reference_kind`; **(B, ADR-0196)** a `needs_input` capacity verdict (sibling to `dont_know`, caller-controlled trigger, non-terminal `pending_confirmation` on `TaskOutcome`, stateless re-submit at v1; MM-owns-pending + in-memory continuation designed-not-built). arc confirmed adoption with **two hard constraints**: (a) dispatcher-level body binding, no metagraph scope-mix; (b) `needs_input` trigger caller-controlled. **Next = implementation chat** (STATE.json `pending_designs` → `phase1-seam-and-needs-input`).

**Full record:** `docs/decisions/adr/0195-phase1-interpretation-seam.md` + `0196-needs-input-clarification.md` + `docs/_workbench/L4_FUTURE_WORK.md` §6/§6.2 + `L5_FUTURE_WORK.md` L5-NEW-19.

### 3.1.25 Resident-brain REPL — flagged command surface + `execute` (Slices 1–2 SHIPPED 2026-07-05)

Reworked `mindsos brain` into a Linux-style flagged REPL (Slice 1, main `14efafc`) and added skill-entry `execute` (Slice 2, main `e1b10d6`; closeout `2baa956` + docs `2c18a94`). Gate 4175 passed / 0 fail, containerized.

**Slice 1:** parser foundation `mindsos_cli/commands/_replparse.py` (shlex tokenize + REPL-safe flag parser + `-h` pre-scan; never raises/exits) + per-verb man pages `_manpages.py` (`<verb> -h`). Verbs `ls` (everything overview) / `search` (glob reverse-lookup, `-i`) / `ds` (rename of `datastate`; `--code`=schema) / `caps` (`--code`=decl+module) / `pl` (list promoted+learned / find / `--transitions`) / `skills` / `episodes` / `verify` (absorbs `status`). `invoke` ergonomics: suffix + single-input positional + `key=value` + single-quoted JSON. Scope `-l/-g` via a one-line `Stack.local_view()` over the existing `CapacityLayer.local_view`. New L0 readers `mindsos_server/episodes.py` + `pipelines.py`. `--new/--seq/--sub/--prototype` are SAP placeholders. Breaking CLI: `datastate`→`ds`, `ls`→everything, `status`→`verify`.

**Slice 2:** `execute <input>` runs a skill's declared entry pipeline — seeds `entry_start_datastate`, composes start→target via `ConjunctionFinder` over the **Global** view (`session=None`), runs it through the new standalone `mindsos_server/pipeline_runner.py` (no MM/writer/TaskRun; shared with `invoke <promoted-pipeline>`). New optional flat props `entry_start_datastate`/`entry_target_datastate` on `SkillInstallRecord` (ADR-0183 §am-1, additive/`strict=False`). `task` retained; `execute` inert until a skill declares an entry (ARC-packaging = first consumer, coordinated via the transient `.scratch/ARC_ENTRY_DECLARATION.md`).

**No version bump** — non-phase feats; `core_version` stays `phase50`. A `phase50a` bump was implemented and **reverted**: the version scheme is integer-phase-locked (manifest `phase` field + digit-only `preflight` regex + ~5 doctor parity tests; ≥51 reserved for WSD). Design record: `confirmation_docs/RESIDENT_BRAIN_REPL_COMMANDS_DESIGN.md`; dev internals: `docs/dev/internals/runtime.md`. Deferred: `verify --diff` + a prior-state snapshot store.

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
3. ~~**Skill-acquisition process chat**~~ — **CLOSED 2026-06-09** (tag `skill-acquisition-2026-06-09`). Contract: `confirmation_docs/SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md`; sequencing: `confirmation_docs/SKILL_ACQUISITION_PROCESS_PHASE_MAP.md` (single ship slot **SA-1 = Phase 50**; seed `confirmation_docs/SA_1_NEXT_CHAT_PROMPT.md`).
4. **WSD installation chat** (opens after SA-1 = Phase 50 confirms; inherits `SKILL_ACQUISITION_PROCESS_PHASE_MAP.md` §5).
5. **FOL installation chat** (inherits WSD's resolutions on shared propositions).
6. **Knowledge-acquisition process chat + DWF installation** (independent; can run in parallel with 2–5 because DWF is L2-only).

### 5.3 Cross-project shared blockers

| Blocker | DWF | WSD | FOL | Status |
|---|---|---|---|---|
| 7 L4 critique pushes | — | yes | yes | **RESOLVED — Chat A 2026-05-28** |
| Coherence Loop fate | — | yes | yes | **RESOLVED — Chat A R2 Push 3 (cut from v1; ALS substitutes)** |
| `sense-correlations` + `learned-parameters` unshipped | — | yes | yes | **RESOLVED — Chat A R3 (ship both v1)** |
| L5 retention model + note-fork | — | yes | yes | **RESOLVED — Chat B D-B1 (D'1 + lazy inline-on-retire; note-fork retired)** |
| L1 InterGraph naming reconciliation | yes (3 conventions in MindsOS code+docs+tests) | yes (proposes `InterGraphEdge`) | — | **RESOLVED — L1-6 (2026-06-01) kept shipped `IntergraphEdge`; ratified SKILL_ACQUISITION R0 S13 (2026-06-09)** |
| `AlignmentsImporter` body unshipped | yes (PRIORITY) | — | — | Knowledge acquisition |

═══════════════════════════════════════════════════════════════════════
## 6. Carry-forwards + open R0 questions

### 6.0 Designs awaiting implementation (newest first)

- **SubMind (Mindlet) — Slice 2 SHIPPED to `main` 2026-06-25** (squash `66315f3`; tag
  `feat-subminds-s2-confirmed`; gate **4090 passed / 11 skipped / 1 xpassed / 0 failed**, Linux +
  live FalkorDB). Consumes the Slice-1 stub resolver: the resolver is **goal-directed** (a Pipeline
  built at dispatch via `find_pipeline`), run by the new **core** Pipeline-step executor
  (`mindsos_intelligence/pipeline_execution.py` — RULES §8: this is core, NOT WSD). New
  `resources.py` (`ResourceLedger`/`ResourceHold`/`Contention` — the shared model Slice-3 Reflex
  reuses) + `submind_arbiter.py`. Preempt/reconcile is **derived from resource contention** (free →
  concurrent dispatch; contended → park + cooperative-cancel-if-outranked → event-driven resume on
  release); unsatisfiable need = tier-never-decays + capped backoff + never-give-up; goal-unreachable
  = honest dont-know → fires the SubMind's direct **ask-human** `fallback_resolver`. Additive
  executor change (`submit(preempt=True)` default unchanged + optional `resource_ledger`). **No
  role-set change** → parity sentinels untouched. ADR-0189 §2/§3 now shipped; ADR-0188 amendment-trail
  notes the shared seizure model. Full record: `confirmation_docs/SUBMIND_DESIGN_LOG.md` §20.
  **Pending: Slice 3** (Reflex path — reuses `ResourceLedger`), **Slice 4** (Local/teaching/tuning).
  Split-out follow-up: `pipelinenotfound-to-dontknow` (see STATE `pending_designs`).
- **SubMind (Mindlet) — Slice 1 SHIPPED to `feat/subminds` 2026-06-24** (gate green: 4069 passed /
  11 skipped / 1 xpassed / 0 failed, Linux + live FalkorDB; tag `feat-subminds-slice1-confirmed` at
  `cebd6ef`). Formalizes Minsky's "society of small minds" tier: an autonomous, no-reasoning
  **reflex** over one self-state vital (thirst/battery/balance) that monitors via an L4-scheduled
  adaptive loop and emits a **Signal** (queued, deliberated) or a **Reflex** (queue-bypassing,
  pre-wired, for non-reconcilable threats). L4 = the single Mind that arbitrates. Reverses
  **ADR-0155** (resident loops return, L4-owned not L3 — Slice 1 ships the L4 `SubMindScheduler`);
  amends **ADR-0150 §am-7** (role-set 13→14, new `subminds` L2 role-graph, Global form bootstrapped);
  added via **endowment** (distinct from skill-acquisition). **WSD owns none of it.** Slice 1 =
  definition + autonomous sensing (adaptive cadence + storm suppression) + Signal→triage→executor
  heap with a stub resolver. **Pending: Slice 2** (resource model + preempt/reconcile + unsat policy —
  largest surface), **Slice 3** (Reflex path + write-hook/arbiter seizure), **Slice 4** (Local scope +
  taught endowment + de-endowment + tuning). ADRs **0188/0189/0190** now `Accepted`. Full record:
  `confirmation_docs/SUBMIND_DESIGN_LOG.md` (§18 decision ledger, §19 impl plan + build/gate log).
- **Composition lifecycle — Slice 1 SHIPPED to `main` 2026-06-21** (`b56e0ac`; gate 3991/11/1xpass/0
  live FalkorDB). Fixed the verified `find_pipeline` multi-input unsoundness: pluggable `Finder`
  seam (`Finder`/`BFSFinder`/`ConjunctionFinder`) + `PipelineDAG` replacing linear `Pipeline` +
  typed `_CapacityBase.input_group` + composite persistence (ADR-0071 §am-2 + ADR-0159 §am-1).
  Record: `confirmation_docs/COMPOSITION_LIFECYCLE_DESIGN_LOG.md` (§8 build/gate log, §3/§6
  scope/dispositions) + STATE `recent`. Project-independent; WSD/bongard not a dependency.
- **Composition lifecycle — Slice 2 SCOPED, impl pending** (own chat). Two items Slice 1 left out,
  surfaced by ARC's D3 spike: invoke INPUT-contract validation (Part 6, standalone correctness) +
  DataState operand-arity/role axis (Part 5, consumer-gated). Scope + concerns + recommended split:
  **design log §9** + STATE `pending_designs` (`composition-lifecycle-s2`). Reopens ADR-0156 edge
  model + ADR-0159/0071 §am + ADR-0072/0146.

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
- **Pair-execution discipline (Phase 43 R11 — default for all numbered-phase ship chats).** Cowork sandbox cannot write to `.git/` — `git add` / `git commit` / `git push` / `git checkout` all fail from inside Cowork. The 3-actor pattern: **Cowork** prepares file content via Edit/Write tools (these reach the host directly); **user** runs git commands on Mac; **Linux** runs cumulative gates via docker. Cowork issues one command-group at a time with expected output; the user pastes back the actual output if it differs ("if my output differs I'll paste; otherwise tell you to proceed"), or just says "proceed" on match. Group simple obvious sequences (`cd && rm X && git status`) in one box; split when an output is needed before the next step can be safely composed. Tag Mac vs Linux explicitly on each command box. See `PHASE_43_DESIGN_LOG.md §9.1` R11 + `POST_PHASE_38_PHASE_MAP.md §1` pair-execution row.
- **6-step confirm-phase workflow (Phase 43 R12).** The two canonical CLI commands: `mindsos confirm-phase --init-notes N` mints `confirmation_docs/notes/notes-phase-N.md` from the project's template; `mindsos confirm-phase --phase N --notes-file notes-phase-N.md` writes `PHASE_N_CONFIRMED.md` from post-squash main (`--notes-file` takes the basename, not a path prefix). The 6 steps: (1) Cowork instructs `mindsos confirm-phase --init-notes N` (Mac) to mint the notes file; (2) Cowork provides layer title in a copy-block; (3) Cowork provides complete tester_notes body in a copy-block; (4) tester edits the notes file on Linux; (5) tester runs `mindsos confirm-phase --phase N --notes-file notes-phase-N.md` on Linux from post-squash main; (6) tester commits PHASE_N_CONFIRMED.md + notes-phase-N.md + pushes. Mac tags `phase-N-confirmed` at the squash-merge commit + pushes the tag. See `PHASE_43_DESIGN_LOG.md §9.1` R12 + `POST_PHASE_38_PHASE_MAP.md §1` 6-step row.
- **Linux host Python is `python3`, not `python` (env invariant — Phase 46).** On the tester's Linux gate/host machine bare `python` is not on PATH; manual smoke scripts and any host-run Python during the ship ceremony must be invoked as `python3 - <<'PY' ... PY`. Tests run inside docker (`docker compose run --rm mindsos-test pytest ...`) are unaffected — that's the container interpreter. Future ship chats: write host smokes with `python3` up front (recurs every phase otherwise).
- **Docker test image rebuild after each Mac push (Phase 43 R10).** `mindsos-test` service in `docker-compose.yml` has no source bind-mount; image bakes source at build time. Every Linux cumulative gate run MUST `docker compose build mindsos-test` before `docker compose run --rm mindsos-test pytest tests/`. Skipping the rebuild runs tests against stale source — surfaces as "fix not applied" puzzlement at the gate. See `PHASE_43_DESIGN_LOG.md §9.1` R10 + `POST_PHASE_38_PHASE_MAP.md §1` docker rebuild row.
- **Pre-impl pushback saturation discipline (Phase 43 §10.4 carry-forward).** When a ship chat opens, the user may ask "reanalyze the plan and list your pushbacks with options.... show me your choice" multiple times before authorising execution. Run a skeptical review round each time: surface concerns, list pros/cons + alternatives + your choice for any blocker, mark minor items for §9.1 tracking. The pattern typically saturates after **3 rounds** ("diminishing returns; impl-time will surface anything else and §9.1 absorbs it"). Say so explicitly when reached; user accepts saturation reasoning as the closure point. Phase 43: 3 rounds surfaced 1 blocker (P1), 2 real (P2 + Q1), the rest minor/track. Carry-forward: budget 2-3 pre-impl pushback rounds + a buildability scan over locked commit boundaries before branching.
- **Gate-driven follow-up budget (Phase 43 §10.5 carry-forward).** Phase 39 needed 2 follow-up commits (5b, 5c). Phase 43 needed 6 (PR1 5b + 5c; PR2 1b + 2b + 3b + 4b). Higher follow-up count tracks the larger scope-rewrite surface (9 schema audits + 4 new schemas + KnowledgeLayer.discipline_for + bootstrap dual-scope semantics + 12+ existing test-corpus expectation updates). Future-phase ship chats: budget follow-ups proportional to scope-rewrite surface; cascade errors at first gate often have a single root cause (Phase 43 PR2 commit 1: 79 collection errors from one `_GLOBAL_ROLE_ORDER` tuple parity miss; PR2 commit 2: ~250 cascade failures from one binary scope-rejection that didn't account for dual-scope roles). Diagnose root cause first; fix often single-line.

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
| SKILL_ACQUISITION_PROCESS_CHAT | **CLOSED 2026-06-09** (tag `skill-acquisition-2026-06-09`). Settlement: `confirmation_docs/SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md` + `SKILL_ACQUISITION_PROCESS_PHASE_MAP.md`. |
| SA-1 ship chat (Phase 50) | **SHIPPED 2026-06-10** (tag `phase-50-confirmed`). Record: `confirmation_docs/PHASE_50_DESIGN_LOG.md` + `PHASE_50_CONFIRMED.md`; this §3.1.23. |
| WSD installation chat | **Inherits SKILL_ACQUISITION_PROCESS_CHAT (closed) + Phase 50 (SHIPPED — the install driver exists at `mindsos_server/skills/`): read `SKILL_ACQUISITION_PROCESS_PHASE_MAP.md §5` (inheritance contract) + design log S9/S10 + `PHASE_50_DESIGN_LOG.md` (G1 + I4/I5 bundle-author rules).** Then `projects/ANALYSIS_DELTA_2026-06.md` FIRST, then `projects/wsd/ANALYSIS.md` (stale-bannered); `projects/wsd/FUTURE_CHAT_PROMPT.md`; `_workbench/cookbook_routing.md` (owns `nlu-slice.md`); FOL chat coordinates (cross-ref `projects/fol/`); this §3 + §5 |
| FOL installation chat | **Inherits WSD installation.** `projects/fol/ANALYSIS.md`; `projects/fol/FUTURE_CHAT_PROMPT.md`; this §3 + §5; WSD-resolutions inherited |
| DWF / knowledge-acquisition chat | `projects/dwf_mapping/ANALYSIS.md`; `projects/dwf_mapping/FUTURE_CHAT_PROMPT.md`; ADR-0150 + ADR-0154 (canonical `alignment:<a>:<b>` form, ratified Chat C Phase 39 cascade); this §5.1 |
| Code-skill installation chat | `_workbench/cookbook_routing.md` (owns `code-slice.md`); `_workbench/L3_FUTURE_WORK.md` (L3-28/L3-30/L3-31); inherits WSD installation |
| Adapter family chat | `_workbench/L3_FUTURE_WORK.md` (L3-49); inherits WSD installation |
| Maintenance chat | `_workbench/STREAM_A_BACKLOG.md`; relevant `_workbench/L*_FUTURE_WORK.md`; `confirmation_docs/PHASE_MAP.md` for the layer's row |
| L4-v2 follow-up chat | **Opens after Phase 49 confirmed.** `_workbench/L4_FUTURE_WORK.md`; this §3.1 + §3.1.5 |
| Bug-fix / maintenance chat | `confirmation_docs/PHASE_MAP.md` for the layer's row; `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §4` for the corresponding Phase 39-49 row; this §2 + §3.1.7 |
| Perception chat (atoms / grounding / learned leaves) | **Doctrine landed 2026-06-27 (docs-only, no code).** Read `docs/concepts/perception-principles.md` (P1–P17, the governing doctrine); ADRs **0191–0194** (Proposed: confidence seam, atom layer, grounding control loop, recognizers+promotion); evidence `docs/_workbench/PERCEPTION_LEARNING_NOTES.md` + `PERCEPTION_LEARNING_PREREG.md` (AM-1…AM-8 + §12 results) + `PERCEPTION_DISCOVERY_TEST_SPEC.md` + `discovery_test.py`. Key results: P14 validated (→ADR-0191); P15 grounding novelty-distance-relative; P16 reuse-driven *propagation* shown, unsupervised *discovery* **tested negative**; P17 near-miss = architectural (descent+finer-atom). ADRs flip Proposed→Accepted when a perception/vision subsystem consumes them. **Update 2026-06-28 (docs-only):** (1) cross-family confidence study `docs/_workbench/PERCEPTION_CROSSFAMILY_PREREG.md` — two-axis confidence + calibration generalizes across scoring/retrieval/derivation AND to real data (FrameNet, §11), but *which axis carries correctness is family-dependent*, independence requires proposer≠critic, calibration is conditional, blind-spot is continuous-only (all audited). (2) **LEAF-NOVELTY study CONCLUDED 2026-06-29** (`PERCEPTION_LEAF_NOVELTY_PREREG.md` §9 FINAL VERDICT + §8 AM-1..AM-10; runs 1–5 on Linux, audited): P0 parity holds (CNN 0.967 vs MindsOS 0.961) but the STRONG novelty claim does NOT — headline retention gap was a unit mismatch, the real gap is sample-efficiency + crisp-categorical routing (fresh modular CNN AUROC 0.995), no-fabrication conceded. Lesson: v1's MindsOS was a hand-coded corner-counter, not genuine leaf-learning. **Update 2026-06-29 — SUPERSEDED by STUDY 2 (design settled, NOT built):** paper-grade validation `docs/_workbench/PERCEPTION_LEAF_VALIDATION_PREREG.md` — bidirectional joint inference over named atoms, hypotheses H1–H6 (**H6 rescue-without-hallucination = headline/riskiest**), atoms-learned/composition-given, 4 baselines incl a feedback/part-whole mechanism control; per-sample metrics; build order in its §10. Build in a fresh focused chat (memory `perception-leaf-validation-study2`). |

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
*End of HANDOFF.md. Last reviewed 2026-06-10 (Phase 50 ship closure — SA-1 skill-install lifecycle; first downstream phase after the completed 39-49 plan). Update when WSD installation confirms, or when any §6 carry-forward closes. **Next chat: WSD_INSTALLATION_CHAT** — see `projects/wsd/FUTURE_CHAT_PROMPT.md` + `SKILL_ACQUISITION_PROCESS_PHASE_MAP.md §5`. DWF parallelizable (L2-only).*
