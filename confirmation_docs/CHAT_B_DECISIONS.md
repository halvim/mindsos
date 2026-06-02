# Chat B — Decisions Log

**Purpose.** Per-decision settlement record for L5 + note-fork resolution. Chat C plan-authoring inherits from here. Same shape as `CHAT_A_DECISIONS.md`.
**Status.** Chat B closed 2026-05-31. R-rounds saturated at impl-locks-only.
**Inputs inherited.** `CHAT_A_DECISIONS.md` (L4 contract) + L5 design notes (2026-04-21 baseline) + L5_FUTURE_WORK + L4_FUTURE_WORK.

---

## Round summary

| Round | Theme | Substantive picks | Reversals |
|---|---|---|---|
| R1 | Retention model + naming | Episode/Memory; D'1 pin-at-instantiation; no Global L5 | 0 |
| R2 | MM composition + L4 read discipline | Three sub-MMs; thin root; L4 reads MM-only; MM-only-instantiation rule | 0 |
| R3 | Worker pool clarification + Chat A vocab fix | "L3 worker pool" → "worker pool"; rule-3 L3 read scope; version_snapshot in CapacityContext | 0 |
| R4 | Hint nodes schema + chain reframe | HintNode schema lock; 4-level chain (later 6-level with TaskRun) | 0 (PB-N/O revised under new model) |
| R5 | Hierarchical Plan + Milestone vocab | Plan-as-tree; Milestone vs LifecyclePhase; lazy decomposition; planning.* L3 family; TaskRun wrapper | 0 |
| R6 | Schema cleanup + cross-sub-MM edges | DataState placement in capacity-MM; IntergraphHyperEdge composition; edge catalog | 0 |

Total substantive picks: ~50 across 6 rounds. Zero reversals across the saturation chain.

---

## R1 — Retention model + naming

### D-B1 — Retention model: D'1 (version-IRI freeze with pin-at-instantiation)

**Pick.** References stored as `(iri, version_int)` tuples. Pinning happens incrementally at instantiation time, not at consolidation.

**Rejected alternatives:**
- A (note-fork forward to v1) — design materials missing; pressures L0 v2 scope.
- B (sequence L5 v1 after server-pivot v2) — ruled out by "ship in v1."
- C (inline content copy) — storage explosion (rejected in 2026-04-26).
- D (no v1 retention) — ruled out by "memories ship v1" user pick.
- D'2 (scoped snapshot at consolidation) — dominated by D'1 on storage cost.
- D'3 (content-hash addressing) — extra infrastructure (hashes, history walk) for no net benefit.

**Rationale.** Lightest mechanism that preserves snapshot semantics. Reuses Phase 11 side-by-side versioning. Eliminates L0 note-fork dependency entirely.

**Cascade.** Note-fork retired from L0 v2 scope (see L0_FUTURE_WORK L0-10 amendment).

### D-B2 — Inline-on-retire trigger (PB-J)

**Picks:**
- Sub-pick (a) **lazy**: fires on first episode read after KL retires a referenced version.
- Sub-pick **(ii) keep-as-tuples** for transitive refs: inlined node's outgoing refs stay as `(iri, version)` tuples and inline themselves on next read.
- Sub-pick **(γ) retire-version event** only: fires when KL actually releases content (not on version bump that leaves prior version side-by-side).

**Rejected alternatives:**
- Eager batched scan at promotion — write amplification on retire (could touch 10k+ episodes per node).
- Transitive inline — unbounded inflation cascade.
- Every-release trigger — over-scan.

**Rationale.** Most episodes are never re-read; eager scan wastes work. Lazy aligns retention with actual usage. Transitive-tuple keeps per-event inflation bounded.

### D-B3 — Naming pair: episode / memory

**Pick.** Per-task persisted MM = **episode**. Cluster of episodes by task-pattern = **memory**.

**Rejected alternatives:** trace (collides with problem-trace), case (CBR baggage), snapshot (MM-snapshot collision), session (L0 collision), engram (obscure).

**Rationale.** Maps onto episodic-memory cognitive register. Matches L5's existing "short-term→long-term consolidation" framing.

### D-B4 — No Global L5

**Pick.** Memories are always Local + circumstantial. No Global L5 tenancy. Global learning travels via ALS only; cross-user knowledge transfer is admin-mediated manual Local search.

**Rejected.** Original L5 §1.3 "Global L5 + Local L5 mirroring L2/L3."

**Rationale.** Memories are highly personal (carry user inputs, decisions). Privacy + anonymization rubric is heavyweight (L5-6/R3 was deferred). ALS already carries the global-learning load via `parameter-staging` → `learned-parameters` flow.

**Cascades:**
- Original L5 §1.3 overruled.
- R3 (cross-user Global promotion criteria) retired from open-questions.
- Global L5 bootstrap pattern question (Chat A bootstrap importer cascade) becomes "schema-only Global bootstrap; Local starts empty" — see D-B25 (PB-TT).

### D-B5 — Dream as live-execution + ALS as sole learning track

**Pick.** Dream loads an episode, materializes a fresh MM by deep-copy, and **re-executes the pipeline as if live**. ALS signals fire during re-execution per normal Chat A mechanics. No separate dream-learning track.

**Rationale.** Avoids the coherence problem of two parallel learning pipelines (ALS + dream-over-memories). ALS handles parameter learning; dream is a corpus-replay mechanism that feeds the same ALS pipeline.

**Cascade.** L5 §5 (dreaming consumers) reframed: dream is *re-execution against current L2/L3 vs. pinned* with ALS signals capturing divergence — not a distinct learning subsystem.

### D-B6 — Dream pipeline catalog v1

**Pick.** v1 dream pipelines: `dream.maintenance`, `dream.exploration`, `dream.retry` (per L5 §5). All operate at the TaskRun level (re-execute whole task from selected chain entry). Cross-level dream variants (re-run from sub-Milestone, re-extract hints) v2+.

**Cascade.** L3-N new family `dream.*` orchestration capacities.

### D-B7 — Dream entry-point (PB-HH)

**Pick.** Each dream pipeline declares its entry-point spec at registration. v1 entry-points: "latest-active TaskRun state" (default for maintenance + exploration + retry). v2 adds: specific PipelineRun, specific Milestone, specific replan-point.

### D-B8 — Dream re-execution policy (PB-NN)

**Pick.** Per-dream-pipeline `execution_policy` field:
- `replay_recorded` — use recorded chain artifacts; no re-invocation of generative capacities.
- `re_execute_capacities` — re-invoke generative capacities against current L2/L3.
- `hybrid` — partial.

v1 assignment:
- `dream.maintenance` = `replay_recorded` (regression check).
- `dream.exploration` = `re_execute_capacities` (drift / alt strategies).
- `dream.retry` = `re_execute_capacities` with replan-injection.

### D-B9 — Dream privacy

**Pick.** Dream runs under the **owning user's session**. Local-staging-only. Global ALS aggregation continues from `parameter-staging` Local → admin-mediated cross-user aggregate (per Chat A R3 D9.4). No PII path to Global.

---

## R2 — MM composition + L4 read discipline

### D-B10 — Three sub-MMs (final assignment after R6 cleanup)

**Pick.** MM = metagraph composed of three sub-metagraphs:

- **knowledge-MM** — L2 instances in attention (lexicon entries, ontology terms, task-patterns, etc. that L4 instantiated from L2).
- **capacity-MM** — L3 instances in attention: **CapacityInstance** (one per L3 capacity per task) + **DataStateInstance** (values flowing through pipelines) + internal `produces` / `consumes` edges.
- **intelligence-MM** — L4-authored state composites: chain artifacts (HintSet, MappingResult, Plan, Milestone, Pipeline, PipelineRun, TaskRun, TaskInput), provenance composites (ReplanRecord, StepExecutionRecord, CrossValSegmentVariant), orchestration runtime state (MSURLedger, SCMSState), hint values (HintNode), Memory-association indexes.

**Cross-sub-MM connectivity:** IntergraphEdge / IntergraphHyperEdge (Phase 05b/c primitives). Pipeline → its member CapacityInstances + DataStateInstances via IntergraphHyperEdge (composition).

### D-B11 — Thin MM root

**Pick.** MM root is a container, not a state-holder. Holds:
- `knowledge_mm_ref`, `capacity_mm_ref`, `intelligence_mm_ref` (three sub-MM pointers)
- `task_run_ref` (the single TaskRun for this task)
- `ref:problem_trace` (if anything goes wrong; L2 problem-trace pointer per ADR-0096)
- `outcome_ref` (TaskOutcome composite, set at task completion)

PlanRun-style scalars (current_plan_run_id, attention_score, etc.) move into TaskRun + PipelineRun composites in intelligence-MM.

### D-B12 — L4-state asymmetry

**Pick.** Intelligence-MM is L4-authored directly (composites born in MM during execution). The "search and instantiate on cache-miss" rule applies only to knowledge-MM + capacity-MM (where L2/L3 sources pre-exist).

**Document explicitly.** The MM-only-read rule is uniform; the population mechanism differs.

### D-B13 — L4 read discipline (orchestrator thread)

**Pick.** L4 (orchestrator thread) reads only from MM. Writes only to MM. Cache-miss on knowledge-MM or capacity-MM → L4 searches the source (L2/L3) → instantiates → reads from MM.

**Sub-picks for the search-and-instantiate layer (PB-A.1/2/3):**
- **(a) Resolution via IRI namespace prefix** — reuses Phase 12 IRI scheme; no new registry.
- **(a) Monotone-grow MM** — no eviction during task lifetime; MM scope bounded by what task touches.
- **(a) Lazy single-node instantiation** — outgoing refs from instantiated nodes remain as `(iri, version)` tuples; resolve lazily.

**L4 invariant: no shadow state outside MM.** All L4 state lives in intelligence-MM. Audit, replay, dream-as-live depend on this.

### D-B14 — L3 read discipline (worker threads)

**Pick (PB-A' rule-3).** L3 capacities running on worker threads prefer MM reads via `mm_handle`; fallback to direct L2/L3 reads using `version_snapshot` from CapacityContext for pinning.

**Cascade:**
- D31 typed CapacityContext gains `version_snapshot: dict[IRI, version_int]` field (Chat A R5 D31 amendment via L3-47).
- New KL public API: `kl.read_at_version(iri, version)` (Phase 11 side-by-side graphs surface).
- `mm.get_or_instantiate(node_iri)` is the L4 helper exposed to worker threads; preserves "L4 owns the *write logic*, not the *write thread*" invariant.

### D-B15 — Vocabulary fix: "L3 worker pool" → "worker pool" (L4 substrate)

**Pick.** Chat A's "L3 worker pool" phrasing is loose. Threads are L4 substrate; L3 owns capacities only. Rename across Chat B docs + Chat C plan-authoring.

**Rule.** "L4 owns the worker pool; pool dispatches work; current dispatched work is L3 capacity invocations." L3 doesn't have threads.

---

## R3 — Pin semantics + cross-thread sync

### D-B16 — Pin-at-instantiation (PB-B)

**Pick.** Pinning happens incrementally during execution as L4 instantiates from L2/L3. Each MM instance carries `(node_iri, version_int)`.

**Rejected alternative:** pin-at-consolidation (single pin event at task completion). Risk: live MM mid-execution could see version shifts under L4's feet if L2/L3 release ships during a long task.

**Rationale.** Cleaner; episode = MM as-is; no live-shift hazard; enables D'1.

### D-B17 — Episode immutability invariant (C.7)

**Pick.** Episode content is **append-only externally.** The only internal mutation permitted is inline-on-retire (D-B2). Admin verify-queue actions modify the *Memory* composite, never the underlying episodes.

---

## R4 — Hint nodes schema (originally pre-chain-reframe)

### D-B18 — Hint nodes in intelligence-MM

**Pick.** HintSet (composite) + HintNode (composite) live in **intelligence-MM**.

**Rationale (post-R6 clarification under PB-CCC).** Hints are pre-pipeline task-interpretation artifacts (chain Level 1). DataStates are pipeline-flow artifacts (chain Levels 4-5). Different chain roles → different sub-MM placement, even though both are L3-capacity outputs.

**Schema lock — HintSet (CompositeInstance):**
- `hints: list[XRef]` → HintNode entries
- `phase: Literal["1_task_interpretation"]`
- `extracted_at_start: timestamp`
- `extracted_at_end: timestamp`

**Schema lock — HintNode (CompositeInstance):**
- `hint_iri: IRI` (the hint type, e.g., `hint.modality`)
- `value: JSON-encoded`
- `value_type: str` (denormalized from L3 hint capacity registry for safe replay)
- `extracted_at: timestamp`
- `extraction_status: Literal["success", "null_graceful", "error_logged", "timeout_exceeded"]`
- `error_info: Optional[str]`
- `confidence: Optional[float]` (from ALS subsystem #10)
- `source_capacity_iri: XRef` (version-pinned tuple into capacity-MM CapacityInstance)

### D-B19 — HintSet scope (PB-N revised)

**Pick.** HintSet is per **Level-1 replan event**, not per-task and not per-PlanRun.
- Initial Phase 1 produces HintSet[0].
- Levels 2-5 replans reuse HintSet[0].
- Level 1 replan produces HintSet[1]; downstream rebuilds from there.
- MM intelligence-MM holds `hint_sets: list[XRef]` (typically length 1).

### D-B20 — Per-candidate hints (PB-O revised)

**Pick.** HintSet holds **global always-on hints only**. **Per-candidate-pattern hint evaluations** (Phase 1 step 5b) belong to **MappingResult** (chain Level 2), not HintSet.

**Schema impact.** Drops `value_kind` + `pattern_context` discriminator from HintNode. MappingResult holds `per_candidate_evals: list[CandidateEval]` (each containing candidate task-pattern + evaluated hints + score).

### D-B21 — Phase 6 cross-val hint substitution dropped from v1

**Pick.** Cross-validation in v1 = **Level-4 (pipeline-segment) substitution only.** Hint substitution (Level-1 cross-val) deferred to v2.

**Cascade.** Drop `CrossValHintVariant` schema; lock `CrossValSegmentVariant` instead:
- `original_step_ref: XRef` (capacity-MM CapacityInstance step)
- `substituted_capacity_iri: XRef` (version-pinned)
- `re_execution_outcome: TaskOutcome`
- `re_execution_run_ref: XRef` (sub-PipelineRun for the partial re-exec)

---

## R5 — Hierarchical Plan + chain restructure

### D-B22 — 6-level chain in intelligence-MM

```
[L1] HintSet               (1 per task; +N per Level-1 replan)
  ↓
[L2] MappingResult         (1 per task; +N per Level-2 replan)
  ↓
[L3] Plan (tree)           (1 root; subtrees materialized lazily)
  ↓ fan-out per leaf
[L4] Pipeline              (N per task = leaf-Milestone count)
  ↓ per-leaf execution
[L5] PipelineRun           (≥N; +retries on Level-4 replan)
  ↓ wrapped by
[L6] TaskRun               (1 per task execution)
```

### D-B23 — Plan as recursive tree; Milestones as nodes (PB-Y, PB-EE)

**Pick.** **Plan is a tree** (single-parent v1; DAG deferred). Tree nodes = **Milestones**. Each Milestone has children (composite) or a Pipeline (leaf).

**Vocabulary lock.** **Milestone** (not "phase") for plan-tree nodes. Chat A's "Phase 1-6" lifecycle nomenclature is preserved unchanged.

**Plan tree generation (PB-X b).** Lazy per-Milestone decomposition — children derived only when parent Milestone becomes active. Allows sub-plans to react to upstream outputs.

### D-B24 — Aggregator capacity policy (PB-Z + PB-SS)

**Pick.** Parent's output from children's outputs:
- v1 **fail-fast** child-failure policy (PB-II).
- v1 **default** = last-child-output-is-parent-output if no aggregator declared.
- v1 **optional** declared aggregator capacity: `Milestone.aggregator_capacity_invocation_ref: Optional[XRef]`. If present, `planning.aggregate_outputs(milestone, children_outputs) → DataState` is invoked.

**Sub-pick.** v1 max plan-tree depth = 3 (cold-start default). Admin-tunable per task-pattern. v2 lifts cap if needed.

### D-B25 — New L3 capacity family `planning.*`

**Pick.** v1 ships:
- `planning.derive_initial_plan(mapping_result, context) → Plan` (root decomposition).
- `planning.decompose(milestone, context) → list[Milestone]` (sub-decomposition).
- `planning.aggregate_outputs(milestone, children_outputs) → DataState` (parent output composition; optional per Milestone).
- `planning.is_leaf(milestone, context) → bool` (decomposition-stop predicate; cold-start defaults: depth ≥ 3 OR primitive output type).

**Cascade:** L3-N new family `planning.*`. Capacity-internal implementation; no required L2 `milestone-patterns` role-graph v1 (catalog of milestone-patterns is v1.5 if admin-authoring proves load-bearing).

### D-B26 — Replan-level enum (PB-AA, PB-S)

**Pick.** ReplanRecord (Chat A D14) gains:
- `replan_level: Literal["hint", "map", "plan", "plan_subtree", "pipeline"]` (5 values).
- `replan_milestone_ref: Optional[XRef]` (required when level = `plan_subtree` or `pipeline`).

`decision.should_replan` capacity verdict outputs `replan_level` on `decision="replan"` verdicts.

`phase6.attribute_blame` returns BlameVerdict (PB-CC):
- `chain_level: Literal["hint", "map", "plan", "plan_subtree", "pipeline"]`
- `milestone_ref: Optional[XRef]`
- `capacity_step_ref: Optional[XRef]`
- `blame_score: float`
- `rationale: str`

### D-B27 — Decomposition-failure handling (PB-LL)

**Pick.** `planning.decompose` failure modes:
- Exception → Phase 6 blame at `plan` or `plan_subtree` → replan.
- Empty list with `planning.is_leaf` returning False → contradiction → replan with reason `decomposition_failed`.
- Runaway children → backstopped by `planning.is_leaf` + cold-start max-depth=3.

ReplanVerdict reason taxonomy adds `decomposition_failed`.

### D-B28 — No-Pipeline-for-leaf escalation (PB-UU)

**Pick.** Hybrid (β + α with budget):
- First attempt: Level-3 (plan_subtree) replan to find different leaf shape.
- Budgets: `per_milestone_replan_budget = 2`, `per_task_total_replan_budget = 5` (both admin-tunable).
- Both exhausted → fall through to `DontKnowReason.PIPELINE_UNAVAILABLE` → capacity-gaps queue.

**Cascade.** TaskRun gains `total_replans_used: int`; Milestone gains `replans_used: int`. Both increment on respective replan events.

### D-B29 — Sibling Milestone execution model (PB-PP)

**Pick.** **Sequential** v1. DFS execution order via `sequence_index`. Parallel siblings v2 (would add `parallel_group: Optional[int]` to Milestone schema).

### D-B30 — TaskRun lifecycle through replan (PB-GG)

**Pick.** TaskRun is **task-lifetime container**. All replans happen inside one TaskRun:
- Invalidated chain artifacts stay in MM as immutable (status `aborted_for_replan_at_level_L`).
- New artifacts spawn alongside at and below the replan level.
- TaskRun.status flips to `replanning` during replan, back to `running` after.

**Cascade.** Amends Chat A D14 — "Replan = new plan-run" reframed as "Replan = new chain-artifacts-at-and-below-replan-level inside same TaskRun." TaskRun.replan_history grows monotonically.

### D-B31 — Status enums under hierarchy (PB-JJ)

**TaskRun:** `running | replanning | completed | failed | aborted`
**PipelineRun:** `running | completed | failed | aborted_for_replan_at_level_L`
**Milestone:** `pending | decomposing | active | completed | failed | skipped_for_replan`

(Push 5 deferred per Chat A — no `paused` / `invalidated_on_resume` v1.)

### D-B32 — Vocabulary fix: PlanRun → PipelineRun

**Pick.** Chat A's "PlanRun" renamed to **PipelineRun**. Required because "Plan" now refers to the chain Level-3 tree artifact.

**Cascade.** Amends Chat A D14 + D32.5c.4 + all references. `attention_score` moves from PipelineRun → **TaskRun** (since attention is per-task, not per-leaf-execution).

### D-B33 — TaskRun composite schema (PB-DD)

**Pick.** New L4-state composite in intelligence-MM wrapping the whole task execution:
- `task_input_ref: XRef → TaskInput` (intelligence-MM)
- `plan_ref: XRef → Plan` (intelligence-MM)
- `pipeline_runs: list[XRef]` (ordered DFS traversal)
- `active_milestone_ref: Optional[XRef]`
- `replan_history: list[XRef]` → ReplanRecord composites
- `total_replans_used: int`
- `status: TaskRunStatus`
- `attention_score: int` (from D32.5c.4)
- `started_at: timestamp`
- `ended_at: Optional[timestamp]`
- `outcome_ref: Optional[XRef]` → TaskOutcome

### D-B34 — PipelineRun composite schema (slim, PB-U)

**Pick.** Per-leaf execution; structural identity moves to Pipeline composite + capacity-MM members:
- `pipeline_ref: XRef`
- `milestone_ref: XRef`
- `task_run_ref: XRef`
- `status: PipelineRunStatus`
- `started_at: timestamp`
- `ended_at: Optional[timestamp]`
- `cross_validation_results: list[XRef]` → CrossValSegmentVariant
- `step_execution_records: list[XRef]` → StepExecutionRecord

### D-B35 — StepExecutionRecord (PB-V)

**Pick.** Per-invocation provenance moves out of capacity-MM step NodeInstance and into intelligence-MM as `StepExecutionRecord` composite:
- `capacity_invocation_ref: XRef → capacity-MM CapacityInstance`
- `pipeline_run_ref: XRef → PipelineRun`
- `milestone_ref: XRef → Milestone`
- `confidence: float`
- `divergence: float`
- `blame_score: Optional[float]`
- `cross_validation_results: Optional[list[XRef]]`
- `invocation_started_at`, `invocation_ended_at`

**Rationale.** Capacity-MM CapacityInstance is one-per-capacity-per-task; multiple invocations may produce multiple records. Separating per-invocation provenance from per-capacity-instance keeps capacity-MM clean.

### D-B36 — ReplanRecord attachment (C.3)

**Pick.** ReplanRecord lives as separate composite in intelligence-MM with bidirectional XRefs:
- TaskRun holds `replan_history: list[XRef]` (forward index for iteration).
- ReplanRecord holds `invalidated_refs: list[XRef]` + `spawned_refs: list[XRef]` (chain artifacts touched).
- ReplanRecord holds `replan_level`, `replan_milestone_ref` per D-B26.

### D-B37 — Per-segment provenance attachment (C.4 + PB-V)

**Pick.** Per-segment provenance attaches to `StepExecutionRecord` composites in intelligence-MM (per D-B35). Capacity-MM CapacityInstance carries structural identity only; provenance is execution-scoped.

### D-B38 — MSUR ledger / SCMS state placement (PB-GGG)

**Pick.** Both live as composites in **intelligence-MM**:
- `MSURLedger` per TaskRun; consolidated with episode at task completion (PB-R4-15 satisfied: persistence beyond task = via episode, not live).
- `SCMSState` per task; lifecycle = per-task (Chat A D42 confirmed).

Their *capacity invocations* (the L3 orchestration capacities that drive MSUR / SCMS) live in capacity-MM as CapacityInstances. Pattern: orchestration *capacity invocations* → capacity-MM; orchestration *runtime state* → intelligence-MM.

### D-B39 — MSUR ledger inclusion at consolidation (C.2)

**Pick.** MSUR ledger is captured in the episode at consolidation (frozen as part of intelligence-MM). PB-R4-15's "persistence beyond task completion v2" reframed as "no *live* cross-task MSUR continuity v1" — episode-resident is historical provenance, not live state.

---

## R6 — Schema cleanup + cross-sub-MM edges

### D-B40 — DataState + Capacity placement in capacity-MM (PB-XX, final user pick)

**Pick.** Capacity-MM holds:
- **CapacityInstance** — one per L3 capacity per task. Version-pinned `(iri, version_int)`.
- **DataStateInstance** — values flowing through pipelines.
- Internal edges: `produces` (CapacityInstance → DataStateInstance), `consumes` (DataStateInstance → CapacityInstance). N-to-N (same CapacityInstance can be invoked multiple times across PipelineRuns, producing multiple DataStateInstances).

### D-B41 — Pipeline composition via IntergraphHyperEdge (PB-XX cascade)

**Pick.** Pipeline composite in intelligence-MM references its member CapacityInstances + DataStateInstances in capacity-MM via **IntergraphHyperEdge** (Phase 05c primitive).

**Pipeline schema:**
- `plan_ref: XRef → Plan` (intelligence-MM)
- `milestone_ref: XRef → Milestone` (intelligence-MM)
- `composition_ref: XRef → IntergraphHyperEdge` (the cross-sub-MM hyperedge identifying members)
- `entry_data_state_ref: XRef → capacity-MM DataStateInstance`
- `exit_data_state_ref: XRef → capacity-MM DataStateInstance`
- `pipeline_finder_capacity_invocation_ref: XRef → capacity-MM CapacityInstance`
- `constructed_at: timestamp`

### D-B42 — DataStateInstance schema

**Pick.**
- `data_state_type_iri: IRI` (version-pinned)
- `value` (when inline) OR `blob_ref`
- `storage_mode: Literal["inline", "falkor_property", "blob_ref"]`
- `produced_at: timestamp`
- `size_bytes: int`
- Edges separate: `produces` from a CapacityInstance; `consumes` to consuming CapacityInstances.

### D-B43 — TaskInput placement (PB-BBB)

**Pick (hybrid).**
- **TaskInput composite in intelligence-MM** — holds L4 metadata: `payload_ref`, `received_at`, `received_from_user_id`, `session_id`, `interactive: bool`, `size_bytes: int`.
- **Derived DataStateInstance in capacity-MM** — the initial flow value for Pipeline_P00; XRef'd to TaskInput composite.

### D-B44 — Inline-vs-blob storage tiers (PB-ZZ)

**Pick.** Three tiers v1; v2 escape hatch:
- Inline (≤ ~4 KB): JSON-encoded value field.
- Falkor large-property (~4 KB to ~1 MB): Falkor BLOB-style property.
- External blob_ref (> ~1 MB): v2 only, via FOL chat blob-store decision (Chat A R5 D30 deferral).

DataStateInstance + TaskInput schemas carry `storage_mode` field for forward compatibility.

### D-B45 — Hint/DataState schema asymmetry (PB-CCC)

**Pick.** Accept the asymmetry. Document explicitly in L5 design notes:

> L3-capacity outputs are placed by chain role, not by L3 origin. Task-interpretation outputs (hints, mapping result) live in intelligence-MM; pipeline-flow outputs (DataStates) live in capacity-MM.

### D-B46 — Edge type catalog (PB-DDD)

**Pick.** Locked v1 catalog:

**capacity-MM internal:**
- `produces`, `consumes`

**intelligence-MM internal:**
- `parent_milestone`, `child_milestone` (Milestone tree)
- `pipeline_ref` (Milestone → Pipeline; leaf only)
- `mapping_ref`, `plan_ref` (chain links)
- `next_pipeline_run` (DFS execution order)
- `replan_history` (TaskRun → ReplanRecord)
- `rejected_promotions` (Memory → rejected promotion candidates)

**Cross-sub-MM (IntergraphEdge / IntergraphHyperEdge):**
- `composition` (intelligence-MM Pipeline → capacity-MM CapacityInstances + DataStateInstances; HyperEdge)
- `execution_step` (intelligence-MM StepExecutionRecord → capacity-MM CapacityInstance + PipelineRun + Milestone)
- `instance_of_l2` / `instance_of_l3` (version-pinned tuples, ref form)

**L2-level (across `episodic_memories` role-graph):**
- `memory_contains_episode` (Memory → Episode entries; PB-VV edge-based association)

### D-B47 — Memory composite schema (PB-L stored + PB-VV edge-based + PB-WW tracking)

**Pick.** Memory is a **stored composite** in L2.`episodic_memories` role-graph. Episode-association via **edges** (`memory_contains_episode`), not embedded list.

**Schema:**
- `task_pattern_iri: IRI` (the cluster key; primary association)
- `created_at: timestamp`
- `admin_notes: Optional[str]`
- `rejected_promotions: list[XRef]` (denormalized index of admin-rejected dream-found promotion candidates; audit log is authoritative)

**Materialization timing (C.8 + PB-OO).** Memory materializes on **first episode** of a task-pattern. Subsequent episodes attach via `memory_contains_episode` edge. Memory cluster key = `mappings[-1].selected_task_pattern_iri` (last-active MappingResult's task_pattern after any replan).

---

## R7 — Operational + cross-cutting

### D-B48 — L2 role-graph name: `episodic_memories` (PB-M)

**Pick.** Container name = `episodic_memories`. Entry types: **Episode**, **Memory**.

**Rejected.** `memories` (entry-vs-container ambiguity); `episodic` (close but less precise); `episodes` (misleading because Memory also lives here).

### D-B49 — Bootstrap importer (PB-TT)

**Pick.** Schema-only bootstrap. Bootstrap importer ships schema definition for `episodic_memories` (entry types + composite shapes); zero entries. Per-user Local references schema at first task; entries grow from task execution.

**Cascade.** L2 bootstrap-importer suite (Chat A L2-24) gains `episodic_memories_bootstrap` entry shipping schema only.

### D-B50 — Crash recovery (C.6 + PB-KK)

**Pick.** Direction: **consolidate-with-crash-flag** on next L4 startup. Episode schema gains `crash_marker: Optional[CrashInfo]` field; L4 startup scans for unconsolidated MMs and consolidates them with the marker set.

**Checkpoint trigger set:**
- LifecyclePhase transitions (1→2, 2→3, ...).
- Per-Milestone completion within LifecyclePhase 3-5.
- Per-replan event.

Crash recovery uses latest checkpoint. Physical mechanism (continuous vs periodic Falkor writes) routed to L4-implementation.

### D-B51 — Signal payloads under hierarchy (PB-MM)

**Pick.** Signal catalog extended:
- `signal.task_outcome` payload gains `milestone_ref: Optional[XRef]`. Fires per Milestone completion + once per TaskRun completion.
- `signal.replan_divergence` payload gains `replan_level` + `replan_milestone_ref`.
- **New signal source: `signal.plan_decomposition_outcome`** — fires on each `planning.decompose` event for ALS subsystem #11.

**v1 signal catalog: 10 sources** (was 9 in Chat A; S7 still reserved).

### D-B52 — ALS subsystem #11 (planning decomposition calibration)

**Pick.** Add to Chat A's 10-subsystem list:

| # | Subsystem | Track | Audit Policy | applies_after |
|---|---|---|---|---|
| 11 | Planning decomposition calibration | B | batched-summary | — |

**v1 ALS subsystem count: 11.** Track A: 2. Track B: 9.

Cascade: L3-37 (ALS family) gains parameter set for `planning.*` family scoring.

### D-B53 — Phase 6 cross-validation scope v1 (PB-W revised)

**Pick.** v1 = Level-4 (pipeline-segment) substitution only. Cross-level cross-val (hint substitution, mapping substitution, plan substitution) v2+.

### D-B54 — Memory association on replan-chain task-pattern change (PB-OO)

**Pick.** Primary cluster = `mappings[-1].selected_task_pattern_iri` (last-active). Secondary findability (e.g., "find episodes originally mapped to task-pattern X") via Mapping retrieval capacity walking task_pattern history. No pre-built secondary index v1.

---

## Cascades to other layers

### L0 cascades

- **L0-10 (note-fork mechanism)** — **retired from L0 v2 scope.** L5 uses D'1 + lazy inline-on-retire; no L0 work required.
- **L0-13 (capacity-gaps admin tooling)** — extended with `promotion-candidates` sub-queue for dream-found candidates.
- **New L0-21 (KL public API)** — `kl.read_at_version(iri, version)` (Phase 11 side-by-side graphs surface).
- **New L0-22 (KL operation hook)** — `kl.retire_version()` triggers lazy-inline marker; marker consulted on episode read.

### L1 cascades

- **IntergraphHyperEdge (Phase 05c)** gains documented use case ("Pipeline composition over capacity-MM"). Documentation amendment only.

### L2 cascades

- **L2-23 amendment** — Add `episodic_memories` role-graph schema. Entry types: Episode, Memory.
- **L2-24 amendment** — Bootstrap-importer suite includes `episodic_memories_bootstrap` (schema-only).
- **L2 schema must support `memory_contains_episode` edge type** across `episodic_memories` role-graph.

### L3 cascades

- **L3-34 amendment** — Capacity registration gains semantic "reads MM"; harness exposes `mm.get_or_instantiate()` to worker threads.
- **L3-37 amendment** — ALS family + new subsystem #11 (planning decomposition calibration) + signal source `signal.plan_decomposition_outcome`.
- **L3-47 amendment** — Typed CapacityContext gains `version_snapshot: dict[IRI, version_int]`.
- **New L3-50 — `planning.*` capacity family** (4 capacities v1).
- **New L3-51 — `dream.*` orchestration capacity family** (3 capacities v1).
- **L3-N (pipeline-finder revision)** — `pipeline_finder.from_milestone(milestone, ctx) → Pipeline`. Per-leaf invocation under hierarchy.

### L4 cascades

- **New L4 substrate component** — MM resolution+instantiation layer (IRI-namespace dispatch; lazy single-node; monotone-grow; pin-at-instantiation). Estimated +100-200 LOC on Chat A's 800-1200 budget.
- **L4 invariant lock** — No shadow state outside MM.
- **MM RWLock (Chat A D32.3)** — protects all three sub-MMs uniformly.
- **D14 (ReplanRecord)** amended with `replan_level` + `replan_milestone_ref`.
- **D32.5c.4 (attention_score)** — moves from PipelineRun → TaskRun.

### L5 cascades

- L5 design notes substantially rewritten — see `docs/dev/l5_mental_model_design_notes.md`.
- L5_FUTURE_WORK updated — see `docs/_workbench/L5_FUTURE_WORK.md`.

---

## Notes / open follow-ups

- **PB-QQ episode storage cost** — episodes are materially larger than original L5 framing implied (~10 KB-10 MB range). Retention policy (L5-4 / L5 §7 R1) was deferred; **monitoring instrumentation v1; retention policy v1.5 if storage growth observed**. Not blocking v1 ship.
- **PB-HHH Falkor query indexes** — cross-sub-MM hyperedge queries may need indexes at scale. Defer to Chat C plan-authoring (persistence cookbook).
- **PB-AAA schema scope** — Chat B adds ~12 composite types. Logical schema is the contract; physical-layout optimization is L4-implementation. Flag for Chat C.

---

## Closure

**Chat B closed 2026-05-31.** Saturation criterion: R5+R6 produced impl-locks only; zero reversals across 6 rounds.

**Architectural commitments locked:**
- D'1 (version-IRI freeze + pin-at-instantiation) supersedes note-fork.
- Three sub-MMs (knowledge-MM, capacity-MM, intelligence-MM) with thin root + cross-sub-MM IntergraphHyperEdges.
- L4 reads only from MM + no shadow state outside MM.
- L3 worker threads run via L4's worker pool; "L3 worker pool" naming retired.
- 6-level chain in intelligence-MM (HintSet → MappingResult → Plan → Pipeline → PipelineRun → TaskRun).
- Plan is recursive tree of Milestones; lazy decomposition; sequential sibling execution v1.
- Capacities + DataStates → capacity-MM; chain artifacts → intelligence-MM.
- No Global L5; memories always Local + circumstantial; dream-as-live + ALS as sole learning track.
- Episode immutability + lazy inline-on-retire as only permitted mutation.
- 11 v1 ALS subsystems (added #11 planning decomposition calibration).
- 10 v1 signal sources (added `signal.plan_decomposition_outcome`).
- Vocabulary: episode / memory / episodic_memories / Milestone / TaskRun / PipelineRun / worker pool.

**Items routed elsewhere:**
- L1/L3 reframe chat: nothing new from Chat B (Chat A's D36/D38/D46/D48 still inherited).
- L2 chat: `episodic_memories` schema (D-B48 + D-B49); cross-sub-MM hyperedge use case.
- FOL chat: blob_ref storage tier for DataStateInstance (D-B44).
- Chat C plan-authoring: physical-layout optimization, storage retention policy, Falkor indexes.
- WSD installation chat: planning.* capacity family authoring; ALS subsystem #11 configuration.

**Pre-Chat-C handoff:** Chat C inherits this CHAT_B_DECISIONS + CHAT_A_DECISIONS as foundation for the L4_L5 phase-map authoring.

**Pre-WSD-installation handoff:** WSD chat inherits chain model + Milestone vocabulary + planning.* family + signal #10.

---

*End of CHAT_B_DECISIONS.md.*
