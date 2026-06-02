# MindsOS Layer 5 — Mental Model Layer: Design Notes

**Purpose.** Design notes for Layer 5 (Mental Model Layer).
**Status.** Substantially rewritten 2026-05-31 to reflect Chat B closure (`docs/_workbench/CHAT_B_DECISIONS.md`). Supersedes the 2026-04-21 baseline + 2026-04-26 §3.4 amendment.
**Companion documents:** `l4_intelligence_design_notes.md`, `use_cases_text_realm.md`, `_workbench/CHAT_A_DECISIONS.md` (L4 contract), `_workbench/CHAT_B_DECISIONS.md` (this layer's settlement).
**Frame.** A Mental Model is **the live working memory of a task in progress** — the minimum coherent instance-graph the system needs to think about a specific task. Retention as an **episode** at task completion is a downstream consequence, not the defining feature.

---

## 1. What a Mental Model is

A Mental Model (MM) is a `Metagraph` (L1 primitive) **composed of three sub-metagraphs**:

- **knowledge-MM** — instances of L2 nodes/edges in attention (lexicon entries, ontology terms, task-patterns, etc.).
- **capacity-MM** — instances of L3 capacities (`CapacityInstance`) plus DataStates flowing through pipelines (`DataStateInstance`), connected by `produces` / `consumes` edges.
- **intelligence-MM** — L4-authored runtime state: chain artifacts (HintSet, MappingResult, Plan, Milestone, Pipeline, PipelineRun, TaskRun, TaskInput), provenance composites (ReplanRecord, StepExecutionRecord, CrossValSegmentVariant), orchestration runtime (MSURLedger, SCMSState), hint values (HintNode), Memory-association indexes.

**MM root** is a thin container holding pointers to the three sub-MMs plus minimal scalars:

```
MM root:
  knowledge_mm_ref:    XRef → knowledge-MM
  capacity_mm_ref:     XRef → capacity-MM
  intelligence_mm_ref: XRef → intelligence-MM
  task_run_ref:        XRef → the single TaskRun for this task
  ref:problem_trace:   Optional[XRef] → L2 problem-trace entry (per ADR-0096)
  outcome_ref:         Optional[XRef] → TaskOutcome composite
```

### 1.1 Properties

- **Working memory, not a memoir.** The MM is written during reasoning, as a side effect of execution. Not an archival artifact composed after the fact.
- **Minimum, expandable.** Starts with the task input. Grows by *instantiation* as reasoning demands.
- **Attention mask, enforced by code.** L4 reads only from MM. On cache-miss, L4 searches L2/L3, instantiates into MM, then reads from MM. There is no path by which L4 can read past attention.
- **L4 is the only writer** of intelligence-MM state. L4 owns the *write logic* for all three sub-MMs; worker threads can call L4-code helpers but cannot bypass the write path.
- **Episode-retained by default.** On task completion the MM is consolidated into L2's `episodic_memories` role-graph as an **episode**. Non-retention is an opt-out.

### 1.2 Sub-MM placement rules

**By chain role, not by L3 origin.** Two L3-capacity outputs may live in different sub-MMs:

| Output kind | Sub-MM | Chain role |
|---|---|---|
| Hint value (`hint.modality` etc.) | intelligence-MM | Pre-pipeline task-interpretation feature |
| DataState (pipeline-flow value) | capacity-MM | Pipeline-execution data |
| Mapping result | intelligence-MM | Task → task-pattern decision |
| Plan / Milestone | intelligence-MM | Strategic decomposition |
| Pipeline | intelligence-MM | DAG composition over capacity-MM members |

State explicitly: hints and DataStates are both produced by L3 capacities, but their **chain role** differs (task-interpretation vs pipeline-flow), and chain role determines sub-MM placement.

### 1.3 Tenancy

- **Local L5 only.** No Global L5.
- **Memories are always Local + circumstantial.** Cross-user learning travels via ALS (`parameter-staging` → `learned-parameters`), not via memory promotion.
- Admin who wants global training material may manually search Local episodes across users and curate. Tooling deferred to v2.

(The 2026-04-21 framing — "Global L5 + Local L5 mirroring L2/L3" — is overruled by Chat B D-B4.)

### 1.4 Who reads / writes what

- **L4 (orchestrator thread):** reads only from MM. Writes only to MM. Cache-miss → search L2/L3 → instantiate into MM → read.
- **L3 capacities (worker pool threads):** prefer MM reads via `mm_handle`; fallback to direct L2/L3 reads using `version_snapshot` from CapacityContext for pinning. Cannot write to MM directly; instantiation goes through `mm.get_or_instantiate(node_iri)` which is L4 code running on the worker thread.
- **L2 / L3 / users:** do not write MM.

**L4 invariant: no shadow state outside MM.** All L4 state lives in intelligence-MM. Audit, replay, and dream-as-live re-execution depend on this.

---

## 2. The chain — 6 levels of artifacts inside intelligence-MM

A task's reasoning is captured as a **chain of immutable artifacts**:

```
[Level 1] HintSet         — output of LifecyclePhase 1 step 3
   ↓
[Level 2] MappingResult   — output of LifecyclePhase 1 step 5
   ↓
[Level 3] Plan (tree)     — output of LifecyclePhase 2 root decomposition
   ↓ fan-out per leaf
[Level 4] Pipeline        — N per task (one per leaf Milestone)
   ↓ per-leaf execution
[Level 5] PipelineRun     — ≥N (more on Level-4 replan retries)
   ↓ wrapped by
[Level 6] TaskRun         — single per task; container for the whole execution
```

Each artifact references its upstream level via XRef. Replan invalidates artifacts at and below the replan level; upstream artifacts are reused.

### 2.1 Level 1 — HintSet + HintNode

Hints are pre-pipeline task-interpretation features. The global always-on subset (Phase 1 step 3, per Chat A R3 Method δ) populates **HintSet**:

```
HintSet (intelligence-MM CompositeInstance):
  hints: list[XRef] → HintNode entries
  phase: Literal["1_task_interpretation"]
  extracted_at_start: timestamp
  extracted_at_end:   timestamp

HintNode (intelligence-MM CompositeInstance):
  hint_iri:         IRI                                       # type, e.g. hint.modality
  value:            JSON-encoded
  value_type:       str                                       # denormalized for safe replay
  extracted_at:     timestamp
  extraction_status: Literal["success","null_graceful",
                              "error_logged","timeout_exceeded"]
  error_info:       Optional[str]
  confidence:       Optional[float]                           # from ALS subsystem #10
  source_capacity_iri: XRef → capacity-MM CapacityInstance    # version-pinned tuple
```

HintSet is **per Level-1-replan event** — typically one per task. Per-candidate-pattern hint evaluations (Phase 1 step 5b) belong to MappingResult, not HintSet.

### 2.2 Level 2 — MappingResult

```
MappingResult (intelligence-MM CompositeInstance):
  hint_set_ref:              XRef → HintSet
  per_candidate_evals:       list[CandidateEval]              # per-pattern hint evals + scores
  selected_task_pattern_iri: IRI                              # version-pinned
  mapping_confidence:        float
  mapping_capacity_iri:      XRef → capacity-MM CapacityInstance
  decided_at:                timestamp
```

### 2.3 Level 3 — Plan + Milestone (recursive tree)

The Plan is a **tree** (single-parent v1; DAG deferred). Tree nodes are **Milestones**.

> **Vocabulary discipline.** Chat A's "Phase 1-6" lifecycle is preserved unchanged. Plan-tree nodes are *Milestones*, never "phases." Discipline matters because the user-facing example "Phase 1: read text; Phase 2: identify subject" describes Milestones, while "LifecyclePhase 1: task interpretation" is a Chat A concept.

```
Plan (intelligence-MM CompositeInstance):
  root_milestone_ref:        XRef → Milestone
  mapping_result_ref:        XRef → MappingResult
  decomposed_by_capacity_ref: XRef → capacity-MM CapacityInstance # planning.derive_initial_plan
  created_at:                timestamp

Milestone (intelligence-MM CompositeInstance):
  parent_ref:                Optional[XRef]                    # None for root
  sequence_index:            int                               # order among siblings
  name:                      str
  description:               Optional[str]
  decomposed_by_capacity_ref: Optional[XRef]                   # planning.decompose invocation
  children_refs:             list[XRef]                        # populated lazily
  is_leaf:                   bool                              # decided by planning.is_leaf
  pipeline_ref:              Optional[XRef]                    # set on leaf milestones
  aggregator_capacity_invocation_ref: Optional[XRef]           # optional non-leaf aggregator
  status:                    Literal["pending","decomposing","active",
                                     "completed","failed","skipped_for_replan"]
  expected_output_data_state_type: IRI
  output_data_state_ref:     Optional[XRef] → capacity-MM DataStateInstance
  replans_used:              int                               # per-milestone replan budget counter
  decomposed_at:             Optional[timestamp]
  executed_at_start:         Optional[timestamp]
  executed_at_end:           Optional[timestamp]
```

**Decomposition is lazy.** Each Milestone's children are derived only when that Milestone becomes active. Sub-decomposition can use prior milestone outputs as context.

**Sibling execution is sequential v1.** DFS order via `sequence_index`. Parallel siblings v2+.

**Child failure → fail-fast v1.** First child failure → parent immediately fails. (Per-Milestone declared `on_child_failure` policy is v1.5.)

**Aggregator default = last-child-output-is-parent-output** when no aggregator declared. Optional declared `planning.aggregate_outputs(milestone, children_outputs) → DataState` capacity for cases that genuinely combine.

**Cold-start max-depth = 3.** Admin-tunable per task-pattern. v2 lifts the cap if needed.

### 2.4 Level 4 — Pipeline

Each leaf Milestone gets a Pipeline. Pipelines are pre-authored as L2.`promoted-pipelines` entries (5-state status per Chat A R3); `pipeline_finder.from_milestone(milestone, ctx)` selects among them.

```
Pipeline (intelligence-MM CompositeInstance):
  plan_ref:                XRef → Plan
  milestone_ref:           XRef → Milestone                   # the leaf this serves
  composition_ref:         XRef → IntergraphHyperEdge         # cross-sub-MM membership
  entry_data_state_ref:    XRef → capacity-MM DataStateInstance
  exit_data_state_ref:     XRef → capacity-MM DataStateInstance
  pipeline_finder_capacity_invocation_ref: XRef → capacity-MM CapacityInstance
  constructed_at:          timestamp
```

The Pipeline's DAG topology lives in **capacity-MM** (via `produces` / `consumes` edges between CapacityInstances and DataStateInstances). The Pipeline composite identifies which subgraph of capacity-MM IS this Pipeline via an IntergraphHyperEdge (Phase 05c primitive).

**No-Pipeline-for-leaf escalation:** if `pipeline_finder` finds no Pipeline for a leaf Milestone, first attempt is a Level-3 (plan_subtree) replan with budget; falling through to `DontKnowReason.PIPELINE_UNAVAILABLE` only after budget exhaustion. Budgets: `per_milestone_replan_budget = 2`, `per_task_total_replan_budget = 5`. Both admin-tunable.

### 2.5 Level 5 — PipelineRun

Slim execution-instance composite. Multiple per task (one per leaf Milestone executed, plus retries on Level-4 replan).

```
PipelineRun (intelligence-MM CompositeInstance):
  pipeline_ref:               XRef → Pipeline
  milestone_ref:              XRef → Milestone
  task_run_ref:               XRef → TaskRun
  status:                     Literal["running","completed","failed",
                                       "aborted_for_replan_at_level_L"]
  started_at:                 timestamp
  ended_at:                   Optional[timestamp]
  cross_validation_results:   list[XRef] → CrossValSegmentVariant
  step_execution_records:     list[XRef] → StepExecutionRecord
```

### 2.6 Level 6 — TaskRun

The whole-task execution wrapper. **One per task.** Stays put across replans.

```
TaskRun (intelligence-MM CompositeInstance):
  task_input_ref:             XRef → TaskInput
  plan_ref:                   XRef → Plan
  pipeline_runs:              list[XRef]                    # DFS-ordered
  active_milestone_ref:       Optional[XRef]
  replan_history:             list[XRef] → ReplanRecord
  total_replans_used:         int
  status:                     Literal["running","replanning","completed",
                                       "failed","aborted"]
  attention_score:            int                            # per Chat A D32.5c.4
  started_at:                 timestamp
  ended_at:                   Optional[timestamp]
  outcome_ref:                Optional[XRef] → TaskOutcome
```

> **Naming note.** Chat A's "PlanRun" is renamed to **PipelineRun** in Chat B because "Plan" now denotes the chain Level-3 tree artifact. TaskRun is the new whole-task wrapper. `attention_score` (Chat A D32.5c.4) lives on TaskRun (attention is per-task, not per-leaf-execution).

### 2.7 TaskInput + DataState placement (the hybrid)

```
TaskInput (intelligence-MM CompositeInstance):
  payload_ref:           XRef OR inline JSON-encoded value
  received_at:           timestamp
  received_from_user_id: IRI
  session_id:            IRI
  interactive:           bool
  size_bytes:            int

DataStateInstance (capacity-MM NodeInstance):
  data_state_type_iri:   IRI                                  # version-pinned
  value:                 JSON-encoded            (when storage_mode = inline)
  blob_ref:              Optional[XRef]          (when storage_mode = blob_ref)
  storage_mode:          Literal["inline","falkor_property","blob_ref"]
  produced_at:           timestamp
  size_bytes:            int
  # edges separate: `produces` from CapacityInstance; `consumes` to consuming CapacityInstances
```

**Storage tiers v1:** inline ≤ ~4 KB → JSON-encoded value; ~4 KB to ~1 MB → Falkor large property; > ~1 MB → v2 only, via external blob store (FOL chat decision per Chat A R5 D30 deferral).

The task's initial flow value is a DataStateInstance in capacity-MM, XRef'd to the TaskInput composite in intelligence-MM. TaskInput carries L4 receipt metadata; the DataStateInstance carries the value flowing into Pipeline_P00.

### 2.8 Other intelligence-MM composites

- **ReplanRecord** — per replan event; bidirectional XRefs to TaskRun (`replan_history`) and to chain artifacts (`invalidated_refs` + `spawned_refs`). Sparse: only on `replan` or `abort` verdicts. Extends Chat A D14 schema with `replan_level: Literal["hint","map","plan","plan_subtree","pipeline"]` + `replan_milestone_ref: Optional[XRef]`.
- **StepExecutionRecord** — per L3 capacity invocation. Carries confidence, divergence, blame_score, invocation timestamps, cross-validation_results. XRefs into capacity-MM CapacityInstance + PipelineRun + Milestone. (Per-invocation provenance is separated from capacity-MM structural identity.)
- **CrossValSegmentVariant** — per Phase 6 cross-validation substitution; carries original step, substituted capacity, re-execution outcome.
- **MSURLedger** — per TaskRun. Captures signal-resolution events during execution. Consolidated as part of episode at task completion (no live cross-task continuity v1).
- **SCMSState** — per task. Tracks BSP turn / quiescence per Chat A R4 D11.

---

## 3. Lifecycle phases (Chat A's six-phase lifecycle, preserved)

**Vocabulary note.** "LifecyclePhase 1-6" here is Chat A's task-execution lifecycle (`docs/_workbench/CHAT_A_DECISIONS.md` D12). Distinct from Plan-tree Milestones.

- **LifecyclePhase 1:** Task interpretation (5-step refactor per Chat A R3 — receive → process → extract_hints → derive_goal → map_to_task_pattern). Produces HintSet + MappingResult.
- **LifecyclePhase 2:** Plan + Pipeline construction. Produces Plan (root + lazy children) and per-leaf Pipelines as they materialize.
- **LifecyclePhase 3-5:** Execution. PipelineRuns spawn in DFS Milestone order. MSUR + SCMS run as L3 orchestration capacities.
- **LifecyclePhase 6:** Failure diagnosis (per Chat A R4 D13). `phase6.attribute_blame` produces a **BlameVerdict** carrying `chain_level: Literal["hint","map","plan","plan_subtree","pipeline"]` + `milestone_ref` + `capacity_step_ref` + `blame_score` + `rationale`.

---

## 4. Retention and consolidation

### 4.1 Retention default

On task completion (success, failure, abort — all complete a task), the MM is retained by default as an **episode** in L2.`episodic_memories`. Opt-out per task.

### 4.2 Consolidation

- **During the task:** the MM lives as live working-memory. L4 writes continuously.
- **At task completion:** L4 freezes the MM (final outcome metadata, end-time, late bindings). The frozen MM is written as an Episode entry in L2.`episodic_memories`, following KL's versioned role-graph pattern.
- **After consolidation:** the L5 live instance is released (process memory freed). The Episode in L2 is available to dream, retrieval, and inspection.

### 4.3 What's in an Episode

```
Episode (L2.`episodic_memories` entry):
  task_input_ref:           XRef → frozen TaskInput
  mm_root_ref:              XRef → frozen MM root (three sub-MMs + outcome)
  task_pattern_iri:         IRI                  # primary cluster key (last-active mapping)
  outcome_classification:   Literal["succeeded","failed","low_confidence",
                                     "asked_user","dont_know"]
  crash_marker:             Optional[CrashInfo]  # set if consolidation followed a crash
  consolidated_at:          timestamp
```

The Episode is a **frozen full MM** — three sub-MMs plus all chain artifacts, provenance, MSUR ledger, SCMS state, and chain history (including replanned artifacts marked `aborted_for_replan_at_level_L`).

**Crash recovery (per Chat B D-B50).** Checkpoint trigger set: LifecyclePhase transitions + per-Milestone completion + per-replan event. On L4 startup, scan for unconsolidated MMs; consolidate them with `crash_marker` set. Physical checkpoint mechanism routed to L4-implementation.

### 4.4 Version-ref resolution (D'1 + lazy inline-on-retire)

Episodes reference L2/L3 nodes by **version-pinned tuples** `(node_iri, version_int)`. Pinning happens at *instantiation time* during execution, not at consolidation.

The earlier 2026-04-26 amendment picked "note-fork" (server-pivot v2 mechanism) for version pinning. **Chat B retired this** in favor of:

1. **D'1 — version-IRI freeze.** Refs are tuples. KL keeps versions side-by-side per Phase 11.
2. **Lazy inline-on-retire.** When KL retires a version (the `retire-version` event — distinct from `deprecate-version` flagging), affected episodes inline the deprecated content **lazily on first read after retire**. The replacing inline content stays as a full snapshot of the retired node. Outgoing refs from the inlined content stay as version-pinned tuples and inline themselves on next read (bounded transitive inflation).

This is the cognitive parallel of short-term → long-term memory consolidation: the working construct (MM) becomes a retained piece of knowledge (Episode), with version-pinned references that absorb retired content as the L2/L3 world evolves.

### 4.5 Episode immutability invariant

Episode content is **append-only externally**. The only internal mutation permitted is lazy inline-on-retire (§4.4). Admin verify-queue actions modify the **Memory** composite (§4.6), never the underlying Episodes.

### 4.6 Memory — pattern-mining unit over episodes

**Memory** is a composite that clusters episodes by task-pattern. Lives in L2.`episodic_memories`.

```
Memory (L2.`episodic_memories` entry):
  task_pattern_iri:         IRI                                # primary cluster key
  created_at:               timestamp
  admin_notes:              Optional[str]
  rejected_promotions:      list[XRef]                         # denormalized index;
                                                               # audit log is authoritative
  # episode association via `memory_contains_episode` IntergraphEdge, not embedded list
```

**Materialization timing.** Memory materializes on **first episode** of a task-pattern. Subsequent episodes attach via `memory_contains_episode` edge. Materializing-on-first-episode keeps the invariant simple ("Memory exists ↔ task-pattern has at least one episode").

**Promotion granularity is per-episode, not per-memory** (PB-3 in Chat B). Local→Global promotion (when added) acts on individual episodes; memories are organizational scaffolding for pattern-mining.

**Cluster key on replan.** `task_pattern_iri = mappings[-1].selected_task_pattern_iri` (last-active MappingResult after any Level-1/Level-2 replan). Secondary findability ("episodes originally mapped to X") is via Mapping retrieval capacity walking task_pattern history; not pre-indexed.

### 4.7 Bootstrap importer

`episodic_memories` ships with a **schema-only bootstrap importer**: schema definition for Episode + Memory + composite shapes, zero entries. Per-user Local references the schema at first task; entries grow from task execution. No Global L5 seed content (per §1.3 + D-B4).

---

## 5. Retrieval, dream, and learning

### 5.1 Retrieval is L3, not L5

Retrieval of episodes/memories is provided by the `capacity:retrieval` family in L3 (per L4 contract). L5 itself just stores; it does not search.

Retrieval capacities are parameterized by search context (by task type, capacity used, result, input shape, pipeline shape, etc.) — see Chat A R5 D44 (`retrieval.by_admin_decision_similarity`) for an example.

### 5.2 Dream as live-execution + ALS as sole learning track

Dream is **load an episode → materialize a fresh MM by deep-copy → re-execute as if live**. ALS signals fire during re-execution per normal Chat A mechanics. There is **no separate dream-learning track**; dream is a corpus-replay mechanism that feeds the same ALS pipeline.

The 2026-04-21 baseline framing of dream as a *separate* learning loop is overruled by Chat B D-B5.

#### v1 dream pipelines

| Pipeline | Execution policy | Purpose |
|---|---|---|
| `dream.maintenance` | `replay_recorded` | Regression check; verify equivalence under pinned state |
| `dream.exploration` | `re_execute_capacities` | Drift detection vs current L2/L3; alt-strategy probe |
| `dream.retry` | `re_execute_capacities` (with replan-injection) | Re-execute failed episodes against current state |

All v1 dream pipelines operate at the **TaskRun level** — re-execute the whole task from the latest-active chain entry. Cross-level dream variants (re-run from sub-Milestone, re-extract hints, etc.) v2+.

**Signal payload provenance.** Signals emitted during dream re-execution carry `dream_source_episode_iri` for trace.

**Privacy.** Dream runs under the **owning user's session**. ALS signals tag Local-only. Global ALS aggregation continues via admin-mediated `parameter-staging` flow.

### 5.3 Dream-found promotion candidates

When dream identifies a promotion candidate (e.g., a Pipeline that generalizes across N episodes' Pipelines, or a new task-pattern that fits an unmapped class of inputs), the candidate is surfaced to the **capacity-gaps admin queue** (`promotion-candidates` sub-queue per L0-13 amendment).

Admin verdicts:
- **Approve** → candidate promoted (becomes an active L3 capacity or L2 pipeline entry).
- **Reject** → recorded on the source Memory (`rejected_promotions`) so future dreams skip re-proposing.

Audit log is the authoritative record; Memory composite denormalizes rejected_promotions for fast dream-time consultation.

### 5.4 ALS interaction

ALS (Audited Learning Subsystem) per Chat A R3 has 11 v1 subsystems after Chat B's addition of #11 (planning decomposition calibration) — see CHAT_B_DECISIONS D-B52. Signal catalog: 10 sources after addition of `signal.plan_decomposition_outcome` (D-B51). S7 still reserved.

Signal payloads under hierarchy carry `milestone_ref` (where applicable) per D-B51.

---

## 6. What L5 supports

- **Live reasoning.** L4's primary use of the live MM — reads it for in-flight decisions; writes via the on-demand instantiation discipline.
- **Retrospective inspection.** "What did the system do for task X?" — retrieve the Episode for X.
- **Comparison across tasks.** Retrieval by pipeline-shape or task-type surfaces episodes that solved similar problems similarly; comparison is over the retrieved set.
- **Provenance for learning.** Dream consumes episodes as training corpus, replayed live, feeding ALS via standard signal sources.
- **Re-execution / regression checking.** An episode is a re-runnable recipe against L3 at its pinned versions; `dream.maintenance` runs them against pinned state for regression.
- **Human review.** An episode is the human-legible artifact for "why did the system do that?" — more useful than a raw trace because chain structure is already picked out.

---

## 7. Open questions (Chat B did not resolve)

Most original §7 questions dissolved under Chat B. Remaining items:

- **R1. Retention policy fine-tuning** — aging strategies (keep last N per task-type; top-K by confidence; keep all failures; compress aging). Chat B note PB-QQ: episode storage cost may force this earlier than v2. Monitoring instrumentation v1; retention policy v1.5 if growth observed.
- **R2. Consolidation frequency** — every-completion default; revisit if write-volume problem.
- **R4. Teaching: user authors an episode/memory directly without execution** — defer to v3+.

Retired:
- ~~R3. Cross-user Global promotion criteria~~ — no Global L5 (Chat B D-B4).
- ~~R5. Partial-MM consolidation on crash~~ — resolved by Chat B D-B50 (consolidate-with-crash-flag + checkpoint trigger set).

---

## 8. Integration points

- **Core (L1).** L5 uses `Metagraph`, `NodeInstance`, `EdgeInstance`, `CompositeInstance`, `IntergraphEdge`, `IntergraphHyperEdge` (Phase 05c — used for cross-sub-MM Pipeline composition), `instantiate_*`, `compose`. No new Core primitives required.
- **Knowledge (L2).** L5 instances reference L2 nodes via version-pinned tuples. Consolidation writes Episodes + Memories to the new `episodic_memories` role-graph using KL's standard `register_version_graph` + `activate_version` pattern. Schema-only bootstrap importer ships at install.
- **Capacity (L3).** L5 instances reference L3 capacities via version-pinned tuples. Retrieval over `episodic_memories` is performed by L3's `capacity:retrieval` family. New L3 families introduced by Chat B: `planning.*` (4 capacities v1) and `dream.*` (3 capacities v1).
- **Intelligence (L4).** L4 is the only writer to L5, the only reader during task execution, and the coordinator of consolidation. The MM resolution+instantiation layer (Chat B D-B13) is new L4 substrate (~100-200 LOC on Chat A's 800-1200 estimate).
- **KL public surface.** New API: `kl.read_at_version(iri, version)` (Phase 11 side-by-side graphs surface). New operation hook: `kl.retire_version()` triggers lazy-inline marker; marker consulted on episode read.

---

## 9. Edge type catalog (v1 lock)

**capacity-MM internal:**
- `produces` (CapacityInstance → DataStateInstance)
- `consumes` (DataStateInstance → CapacityInstance)

**intelligence-MM internal:**
- `parent_milestone` / `child_milestone` (Milestone tree)
- `pipeline_ref` (Milestone → Pipeline; leaf milestones only)
- `mapping_ref`, `plan_ref` (chain links)
- `next_pipeline_run` (DFS execution order)
- `replan_history` (TaskRun → ReplanRecord)
- `rejected_promotions` (Memory → rejected promotion candidates)

**Cross-sub-MM (IntergraphEdge / IntergraphHyperEdge):**
- `composition` (intelligence-MM Pipeline → capacity-MM CapacityInstances + DataStateInstances; HyperEdge)
- `execution_step` (intelligence-MM StepExecutionRecord → capacity-MM CapacityInstance + PipelineRun + Milestone)
- `instance_of_l2` / `instance_of_l3` — version-pinned tuple references (the standard `(iri, version)` form)

**L2-level (across `episodic_memories` role-graph):**
- `memory_contains_episode` (Memory → Episode entries)

---

## Historical note

Earlier drafts (2026-04-21) framed the MM as "frozen snapshot of cognitive trajectory" with retention-as-default added later. The 2026-04-26 amendment picked Option A (note-fork) for version pinning, gating L5 on a not-yet-designed L0 mechanism.

Chat B (2026-05-31) substantially restructured the layer:

- **Note-fork retired.** D'1 (version-IRI freeze + pin-at-instantiation + lazy inline-on-retire) ships v1 without L0 coupling.
- **Three-sub-MM composition** (knowledge / capacity / intelligence) with thin root + IntergraphHyperEdge cross-sub-MM composition.
- **6-level chain** of artifacts inside intelligence-MM (HintSet → MappingResult → Plan → Pipeline → PipelineRun → TaskRun).
- **Plan as recursive tree of Milestones** with lazy decomposition + capacity-driven `is_leaf` predicate. New `planning.*` L3 family.
- **No Global L5** — memories Local + circumstantial; cross-user learning via ALS only.
- **Dream-as-live + ALS as sole learning track** — dream is corpus replay, not a parallel learning loop.
- **Vocabulary cleanup** — episode / memory / episodic_memories; Milestone (not "phase"); TaskRun (new) / PipelineRun (rename of Chat A's PlanRun); worker pool (L4 substrate, not L3).

Full settlement: `docs/_workbench/CHAT_B_DECISIONS.md`.

---

**End of notes.** Design locked at Chat B closure 2026-05-31; append as implementation surfaces new questions.
