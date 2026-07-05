# Task lifecycle (six phases)

Layer 4 drives every task through a **six-phase lifecycle** (Chat A D12). The
orchestrator ships at Phase 47 as `mindsos_intelligence/orchestrator.py`; it is
control flow only — every decision is an L3 capacity it dispatches through the
L4 `L4Dispatcher`, and every reasoning step emits an immutable chain artifact
into intelligence-MM under the MM writer lock.

## Where the lifecycle runs

The Phase-46 substrate is **worker-per-task**: `IntelligenceLayer.enqueue`
submits a task closure to the priority-tier worker pool, and the whole
lifecycle runs on the worker thread that dequeues it. There is no separate
orchestrator thread (a deliberate divergence from Chat A D32's wording —
ADR-0171). Capacity invocations run inline on that worker; cancellation and
replan are local to its per-task `cancel_token`.

## The six phases

**LifecyclePhase 1 — task interpretation.** A five-step flow (ADR-0172):
receive → `process.*` → `hint.*` extract → `decision.derive_goal` →
`map_to_task_pattern`. It emits a **HintSet** (step 3) and a **MappingResult**
(step 5) into intelligence-MM.

The flow is factored into a standalone `interpret()` decoupled from the
lifecycle (ADR-0195): the orchestrator is one caller, an interpretation-only
consumer (e.g. arc-solver) is another. Which body runs each step is a
**`Phase1Profile`** — a construction-bound, per-consumer selection of capacity
IRIs held on the `L4Dispatcher`; an unset slot falls back to the shipped v0
placeholder, so the all-v0 path needs no profile. Reference `resolve` is not a
fixed slot: when a hint reports an indirect `reference_kind`, it is composed by
the bipartite `find_pipeline` (ADR-0156) from the reference's DataState type to
the profile's `resolve_target_datastate`.

Input is **modality-typed at ingress** (ADR-0197). An `InputEnvelope` carries
the raw value, a **modality** (the identity of the ingress DataState —
`text.raw`, `image.raw`, …; there is no separate modality enum) and a **source**
(provenance, never read for selection). The boundary stamps the modality,
*declared by the source*; the dispatcher's `{modality → Phase1Profile}` table
then selects the interpretation bodies per input. The interpretation spine is
**environment-threaded** — each step keys its inputs/outputs off the selected
capacity's declared DataStates rather than a fixed spine — so a text input runs
through the real `text.space_split` (`text.raw → text.tokens`) as its `process`
step. `image` / `action` are contract-only extension points (register a
catalog); the all-v0 path is byte-identical.

**LifecyclePhase 2 — Plan + Pipeline construction.** `planning.derive_initial_
plan` seeds a **Plan**; the Plan is a recursive **Milestone** tree decomposed
lazily (`planning.decompose`) with a leaf predicate (`planning.is_leaf`) and a
cold-start max-depth of 3. A v0 pipeline-finder emits one **Pipeline** per leaf
Milestone. The whole-task **TaskRun** (Level 6 of the chain) wraps the run.

**LifecyclePhase 3–5 — execution.** Leaf Milestones run in DFS order
(sibling-sequential v1, child-failure fail-fast v1). Each leaf emits a
**PipelineRun** and a **StepExecutionRecord** per L3 invocation. MSUR and SCMS
are L3 orchestration capacities whose bodies ship in WSD installation; their
hooks are absent at Phase 47 and the loop tolerates that.

**LifecyclePhase 6 — failure diagnosis.** On the dont-know path, L4 dispatches
`phase6.attribute_blame`, which returns a **BlameVerdict** locating blame at a
chain level (hint / map / plan / plan_subtree / pipeline) and step. The concrete
cross-validation body ships in WSD installation.

## Goal verification, replan, and outcome

Between execution and completion the orchestrator dispatches
`predicate.sufficient` (has the task produced enough?) and `decision.should_
replan` (see [Replan](replan.md)). A `continue` verdict with a satisfied
sufficient-predicate completes the task; an unsatisfied predicate routes to
Phase 6 and returns a `dont_know` outcome; an `abort` verdict ends the task.

## Simplified mode

A `simplified` flag on `run_lifecycle` bypasses goal-verification,
consolidation, and ALS emission (Chat A D12 dev/test mode). The CLI surface
(`--bypass-lifecycle`) is deferred until an interactive consumer exists; Phase
47 is library-only.

## v0 catalog and consolidation seam

Phase 47 runs over **placeholder v0 catalogs** (`planning_v0` / `phase1_v0` /
`orchestration_v0`); WSD installation atomically replaces them with the real
families. The Phase-5→completion **consolidation** hook is a stub seam here; the
real MM-freeze + Episode write lands at Phase 48.
