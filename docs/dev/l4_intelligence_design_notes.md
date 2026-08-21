# MindsOS Layer 4 — Intelligence Layer: Design Notes

**Purpose.** Ideas and decisions surfaced during Layer 3 design that belong to Layer 4. This is not a specification — it is a running catalog of things the L4 design session should treat as load-bearing. Append as further decisions land.

---

## The principle that separates L3 from L4

A capability is in **L3** if it is *fixed* — a discrete algorithm, monitor, technique, or scorer that behaves deterministically and can be represented as a graph node. Either the system has it, or it doesn't.

A capability is in **L4** if it *depends on confidence learned from experience* — applying, composing, choosing among, or optimising L3 capacities. Its performance improves with use.

Shorthand: **L3 is fixed things you can do; L4 is the learned use of them.**

Every L4 responsibility below is a consequence of this principle.

---

## Responsibilities identified for L4

**Pipeline-finding as an applied process.** L3 holds path-finding algorithms (Dijkstra, BFS, A\*, pattern-matching, neural-guided search, brute-force enumeration) as fixed capacity nodes. L4 is the applied pipeline-finder: picks an algorithm suitable for the task, runs it against the current L3 metagraph, observes success/failure, and improves its choice via learned confidence.

**Task-to-pipeline flow (three-step default, 2026-04-23).** On receiving any task, L4 follows a fixed sequence before building or running a pipeline:

1. **Consult `L2.task-patterns`** to identify the task's kind — classify against known patterns learned from experience. Output: a task-shape descriptor that drives the next two steps. Every task goes through this step, including FOL queries, dream cycles, and training runs; there is no bypass in the default flow.
2. **Consult `L2.promoted-pipelines`** for pipelines previously successful on this task shape. Returns zero or more candidate pipelines with their per-pipeline confidence.
3. **Adapt or generate.** If a returned candidate matches closely enough (match criterion is itself learned), adapt it to the current task's specifics. Otherwise, invoke pipeline-generation (L3 capacity — see proposed ADR-023) to synthesize a new pipeline from first principles; on success, the new pipeline becomes a candidate for future promotion.

Only synthetic micro-tasks (e.g., "invoke this single capacity with these inputs") bypass this flow — and even there, step 1 is trivially fast because the pattern is fixed. This flow was surfaced during the FOL Layer design (Example 3 walk) and is the canonical L4 orchestration entry point.

**Strategy and technique selection.** At each step of a pipeline, choosing which L3 technique to invoke. Depends on learned confidence per (task-shape, technique, context) tuple.

**Orchestration / attention management.** The runtime that keeps resident L3 capacities alive, routes inputs to subscribers, composes priority signals, and decides what gets compute next when resources are constrained. L3 contains the scorers (urgency, salience, goal-alignment, cost); L4 composes them into an actual decision and runs the scheduler.

**Signal response.** A resident L3 capacity (e.g. a water-level-monitor) emits a signal. L4 decides what to do with it — translate to goal, enqueue as task, interrupt the current activity, or discard. The translation from signal to action is L4.

**Learning from traces.** L3 records traces (a fixed capacity) and inspects single traces (a fixed capacity). L4 aggregates traces across time, finds recurring sub-sequences, proposes promotions, tracks per-capacity confidence, updates preferred strategies. This is the learning faculty proper.

**Compound-path management.** Successful discovered paths are promoted to *named paths* — references into the existing L3 graph, not new nodes. L4 owns the library (stored in L2 as a `promoted-pipelines` role-graph), decides what to promote, when to deprecate, and when to re-validate.

**Pipeline editing / optimisation.** Taking a known pipeline and improving it — replacing steps, reordering, inserting adapters, parallelising sequential steps. A meta-learning operation over existing pipelines.

**Human-in-the-loop decisions.** L3 has the *mechanism* to ask a human (the ask-user capacity). L4 decides *when* to ask, based on confidence thresholds. As confidence in a pipeline grows, the frequency of human consultation should fall.

**Mental Model (L5) construction.** When a task is solved, L4 populates L5 with instance snapshots of the chosen pipeline, the DataStates that passed through it, and a reference to the trace. L5 is not written to by L3 directly.

**Task-conditioned subgraph selection.** Pruning the L3 metagraph to a relevant subset for a given task. L3 contains relevance-scoring capacities; L4 applies them with learned confidence and learns which pruning patterns serve which task types.

**Multi-objective path selection.** L3 produces Pareto-frontier candidates; L4 picks one based on task-level constraints (budget, latency, accuracy, confidence) and learns which trade-offs serve which task types.

**Fallback-branch decisions.** When a technique fails at runtime, L4 decides which alternative to try — using learned history of which alternatives have worked in similar contexts.

**Confidence tracking.** Confidence is **pipeline-level**, not node-level. The system does not keep a store of per-capacity reliability scores — a capacity that is unreliable at solving problems does not belong in L3 in the first place. Instead, L4 maintains, per `promoted-pipelines` record (one pipeline + one task type), a confidence value derived from observed success across runs. Per-run output confidence is computed fresh during each task (and written to the live Mental Model), not stored as a node attribute. This replaces the earlier sketch of a dedicated `capacity-confidence` role-graph.

---

## L2 / L3 / L4 / L5 contract

- **L3 capacities READ L2 freely.** Knowledge lookup is a cornerstone of most capacities.
- **L3 capacities never WRITE L2 directly.** Only L4 writes L2 — specifically when the learning intelligence produces new knowledge or new learned state.
- **L3 capacities never modify L3.** No self-modification at the capacity level; the repertoire is only changed by L4's learning intelligence (which may add or deprecate nodes) or by the user teaching the system.
- **L4 modifies its own state** (learned confidences, strategy preferences, promoted-path library) and writes to L2.
- **L5 is populated exclusively by L4.**

---

## New L2 role-graphs implied by L4's responsibilities

- `promoted-pipelines` — library of named compound techniques, stored as reference-chains into L3 node ids. **Carries pipeline-level confidence per task type** (the only confidence store in the system).
- `request-patterns` — what the system knows about a *kind* of request. ⚠ This line said
  `task-patterns` (a name the code has not used since Phase 43) and *"decomposition
  templates learned from experience"*, which is wrong twice: the role has **zero writers**,
  so nothing has ever been learned into it, and its `SubgoalTemplate` / `DECOMPOSES_INTO`
  schema is **not** the decomposition mechanism. Decomposition is
  [ADR-0206](../decisions/adr/0206-planning-decomposition-confidence.md) §4 and is unbuilt
  (CORE-C4R3); ADR-0206 §7 renames the role `request_knowledge` (CORE-C2R7).
- `memories` — consolidated Mental Models from completed tasks (see §"L5's role — live working memory and default retention" below, and `l5_mental_model_design_notes.md`). Retained by default; opt-out per task. Read by L3 `capacity:retrieval` capacities.
- `problem-trace` — thin structured entries emitted when a capacity invocation fails or raises an anomaly. Not a general trace log — only the problematic cases. Referenced from the MM root via `ref:problem_trace` when a task encounters problems.
- `capacity-state` — optional snapshots of resident-capacity internal state worth preserving across restarts (e.g. a long-lived monitor's rolling window).
- `sense-correlations` (added 2026-04-23, from FOL Layer design) — co-occurrence statistics between lemma senses, learned by L4 from consolidated `memories` during dreaming. **Two consumers:** (i) L3's WSD capacity reads it as *input* during sense candidate generation — correlations boost candidates consistent with the lemma-co-occurrence pattern of the current context, suppress those that aren't, and preserve multiple candidates when correlations don't decisively prefer one (so WSD can promote multiple sense-assumptions when truly ambiguous); (ii) L3's `fol.apply_sense_correlation` capacity reads it post-confirmation to propagate a confirmed sense to co-occurring lemmas' priors.
- `learned-parameters` (added 2026-04-23, from FOL Layer design) — single generic role-graph holding converged learned parameter snapshots for every L3 capacity with trainable state (e.g., WSD sense-ranker weights, gap-relevance scorer weights, source-trust scores, negative-closure completeness thresholds). Keyed by capacity IRI. Written by L4 on Coherence Loop convergence; read by L3 capacities via `context` threading (L4 pulls the active snapshot and passes it in). Replaces the earlier sketch of one role-graph per trainable generator.

These are new roles beyond KL's existing seed roles (`ontology`, `lexicon`, `concepts`, plus `alignment:*`). They extend KL's pattern cleanly — each is a versioned role-graph reached via `kl.activate_version(...)`.

**Dropped from earlier drafts:**

- `capacity-confidence` — subsumed by pipeline-level confidence on `promoted-pipelines` records.
- `trace-history` as a general capture — superseded by MM-as-success-trace (a consolidated memory in `memories` **is** the trace of a successful run) paired with the thin `problem-trace` for failure detail. There is no separate firehose of per-capacity invocations.

---

## Open design questions for L4 (collected as of L3 discussion)

1. **Tenancy.** Is L4 per-user (mirroring KL's Local Metagraphs), global (one orchestrator serving all users), or layered (a shared "species-level" L4 plus per-user overlays)?
2. ~~**Where confidence physically lives.**~~ **Settled 2026-04-21.** Pipeline-level confidence lives as a property on `promoted-pipelines` records in L2. Per-run output confidence lives on the MM root composite in L5 (and is consolidated into the `memories` record). No `capacity-confidence` role-graph exists.
3. ~~**Trace granularity.**~~ **Settled 2026-04-21.** The MM itself is the success trace — a consolidated memory in `memories` contains the full pipeline DAG, DataStates, strategy choices, and outcome. A separate `problem-trace` role-graph holds thin entries only for capacity invocations that failed or raised anomalies; MMs reference those via `ref:problem_trace`. No general trace-history firehose.
4. **Scheduler policy.** Strict priority, fair share, weighted auction, something else? Leaning: composed from L3 scorers, run by L4 runtime — confirm and define the composition.
5. **Competing goals.** How does L4 arbitrate when multiple resident L3 capacities emit goals simultaneously? Same as scheduler policy or different?
6. **Orchestrator policy authorship.** Is it an L4-internal program, or is it composed from L3 capacities? Leaning: composed from L3, run by L4 runtime — keeps the policy learnable.
7. **Goal-to-task transition.** The translation from signal (emitted by resident L3) to task (queued for reactive pipelines) — is this a single L4 step, or itself a composition of smaller learned behaviours?
8. **Concurrency model.** How many pipelines can run simultaneously? What is the isolation model between them? How do they share access to resident capacities?
9. **Long-term state persistence.** What gets persisted: pipeline confidence on `promoted-pipelines`, memories (default-retained), promoted paths, task patterns, problem-trace entries. What is ephemeral: L4 process state, live MMs (after consolidation). Re-validation cadence and retention aging remain open (see also D1, D3 in Dreaming).
10. **L4's own learning loop.** Self-improvement of the pipeline-finder itself — at what cadence, with what validation, to avoid regression?

---

## Concerns deferred from the L3 conversation

See `layer3_concerns.md`. Insight, analogy, and valence will all likely need L4 mechanisms even though the deeper design questions remain open.

---

## Integration with shipped layers

L4 will consume:
- **Core** (`mindsos_core`) — via the normal API (read through `MetagraphLoader`, write through repositories when extending L2).
- **Knowledge Layer** (`mindsos_knowledge`) — via `KnowledgeLayer` façade for reads and guarded writes, particularly for the new role-graphs listed above.
- **L3** (`mindsos_capacity` — name TBD) — via the capacity metagraph interface, once defined.

The persistence story for L4's state (confidences, promoted paths, trace history) piggybacks on KL's versioned role-graph pattern. No new persistence primitives required.

---

---

## Additions from the 2026-04-21 session

### Three-tier memory model (L2 / L4 / L5)

The system has three memory tiers, each at a different layer, each with a different write discipline. This is the canonical frame for *what gets remembered, where, and for how long*.

- **L2 — long-term memory.** Persistent, versioned, cross-session. What the system *knows* (ontology, lexicon, concepts, confidences, promoted pipelines, task patterns, capacity-state snapshots worth keeping). Global + Local split (already shipped). Writes go through KL's versioning machinery.
- **L4 — process memory.** Temporary state owned by running L4 processes. Not knowledge. Examples: scheduler priority compositions, resident monitor rolling observation windows, in-flight pipeline candidate evaluations. Dies with the process. May be snapshotted for resume (via `capacity-state`) but is never confused with knowledge.
- **L5 — working memory.** Task-scoped. The Mental Model of the currently-executing task holds the active pipeline, DataStates in flight, knowledge consulted, strategy choices, outcome metadata. Written by L4 throughout execution; consolidated into L2's `memories` role-graph on completion (retention is the default; opt-out per task).

**The L4 triage duty.** Every observation an L4 monitor produces — from a resident capacity, a trace, a scheduler decision — must be classified into one tier:

1. *Keep in L4 process state.* Ephemeral; relevant only while this process runs.
2. *Write to the current task's L5 Mental Model.* Pin to working memory. On task completion, the MM (including this entry) is consolidated into L2 `memories` by default, so "write to L5" is in practice the path to retained task-scoped knowledge.
3. *Promote to L2 directly.* Patterns worth remembering across tasks — confidence updates to `promoted-pipelines`, new `task-patterns`, new capacities in Local L3, etc. Distinct from the MM-consolidation path; this is for patterns that belong in long-term knowledge rather than a single task's memory.

Triage is itself an L4 intelligence — it depends on learned confidence ("is this pattern worth promoting?") and on retention policy (window size, privacy scope, Global-vs-Local placement). Triage policy becomes one of L4's own learnable behaviours over time.

**Forgetting is a triage consequence.** Not writing to L2 is one form of forgetting; aging L5 Mental Models out is another; clearing L4 process state on restart is a third. "Forgetting" is not a single mechanism but a layered one — each tier has its own retention story.

### Dreaming — idle-compute behaviour, implemented as a task

**Dreaming is a task like any other.** This is the load-bearing simplification from the 2026-04-21 design session. Dreaming does not need its own runtime, its own lifecycle, or its own special-case machinery. When the system is idle, L4 enqueues a *dream task* with a target intent (maintenance, exploration, or retry) and runs it through the normal pipeline-finding path.

**A dream pipeline always begins with a retrieval step.** The first capacity in every dream pipeline is drawn from L3's `capacity:retrieval` family, which reads from L2's `memories` role-graph. Retrieval capacities are parameterised by a *search context*:

- `retrieval.by_task_type(t)` — pull past memories for task type t.
- `retrieval.by_capacity_used(c)` — pull memories whose pipelines included capacity c.
- `retrieval.by_result(r)` — pull memories with outcome classification r (e.g., `failed`, `low-confidence`).
- `retrieval.by_input_shape(s)` — pull memories whose inputs match structural pattern s.
- `retrieval.by_pipeline_shape(p)` — pull memories whose pipelines match structural pattern p.

L4 picks among them with learned confidence just as it does for any other capacity family. The retrieved memories become the inputs to downstream capacities (re-run, compare, score, propose promotion, mine for patterns).

**Three dream intents and how they compose.** Each maps to a retrieval entry point followed by downstream capacities:

- **Maintenance.** `retrieval.by_task_type(*)` → re-score pipelines against current L2 → update `promoted-pipelines` confidence; compress aged memories; validate cached confidences; GC L4 process memory.
- **Exploration.** `retrieval.by_result(succeeded)` → propose alternative pipelines at each step → run against cached inputs → compare outcomes → queue promising adapters/pipelines as candidates.
- **Retry.** `retrieval.by_result(failed)` → pull the attached `ref:problem_trace` → construct alternative pipelines → re-execute → on success, update memory with `outcome: succeeded_on_retry` and propose the alternative for promotion.

Because a dream is itself a task, it **produces its own Mental Model**, which is consolidated as a memory in `memories` on completion. This means dreams can be dreamed about — retrieval over memories naturally surfaces dream-produced memories alongside user-task-produced ones. No second mechanism required.

Dreaming remains the mechanism by which the **Local L3 metagraph** grows: new adapters, new promoted paths, new pipeline-level confidence updates originate here. High-confidence discoveries queue for human approval before Global promotion.

**Open questions the dream loop raises:**

- **D1. Compute budget.** How is the dream budget set? A fixed fraction of idle cycles, a scheduler-enforced ceiling, or user-controllable?
- **D2. Explore-vs-exploit.** What is the trade-off between trying unfamiliar compositions (explore) and refining confidence on known-good pipelines (exploit)? Is the policy learned?
- **D3. Write-back gating.** Which dream outputs auto-apply (e.g., pipeline confidence updates on existing records) versus queue for human review (e.g., new Local capacity promotions)?
- **D4. Dream-initiated tasks.** Can a dream loop enqueue a "real" task (e.g., "I think I can now solve task X — attempt it")? If so, how is that distinguished from user-initiated work in the scheduler?
- **D5. Retrieval-context priors.** Which retrieval capacity does L4 pick to *start* a dream? The choice itself is learnable — maintenance dreams probably favour `by_task_type`, retry dreams favour `by_result(failed)`, exploration dreams favour `by_result(succeeded)` or `by_pipeline_shape`.

### Path promotion, not DataState synthesis

Reaffirmed: the system grows its effective repertoire by discovering **paths between existing DataStates** and promoting them as named compound techniques (references into L3, stored in L2's `promoted-pipelines` role-graph). **The system does not synthesise new DataStates.** New DataStates are human-authored.

L4's path-promotion workflow:

1. Pipeline-finder discovers a new path during dreaming or during live task-solving.
2. L4 observes repeated success of the path across varied inputs.
3. Confidence crosses a threshold.
4. L4 proposes the path for promotion — this may happen autonomously (writes to the user's Local `promoted-pipelines` graph) or queue for human approval (required for Global promotion).
5. Promoted paths are recorded as reference-chains, not as new graph nodes. No node explosion.

### Global and Local L3 metagraphs

L3 is not one metagraph — it is two, mirroring KL exactly:

- **Global L3 metagraph** ships with the system. Stable. Updated only with software releases.
- **Local L3 metagraph** accumulates user-taught capacities, L4-synthesised adapters, local overrides (cost priors, confidence priors tuned for this user's workload).
- **Promotion machinery** mirrors KL's — Local → Global via `register_version_graph` + `activate_version`, gated by validation and human approval.

L4 reads both. Pipelines step freely between Global and Local capacities; the `CapacityLayer` façade (analogous to `KnowledgeLayer`) offers unified views.

### Lifecycle monitoring for residents

Fine-grained residents (see L3 §5.2) produce observation streams. L4 runs a **lifecycle monitor** per resident (or per resident-class) that:

- Subscribes to the resident's emitted signals.
- Maintains rolling statistics in L4 process memory.
- Makes the triage decision (process/working/long-term) for each observation.
- Decides when the resident itself should be started, paused, or stopped based on task demand.
- Feeds back to the confidence layer: was this resident's signal useful, how often, under what conditions?

The lifecycle monitor is not a single capacity but a pattern — a small composition of L3 capacities (scoring, subscription, trace) run by L4 with policy.

### L5's role — live working memory and default retention

A Mental Model is the **live working memory** of a task in progress — a minimum coherent instance-graph over L2 / L3 / L4 representing what the system is currently thinking about. Retention as a memory is a secondary consequence, not the defining feature. See `l5_mental_model_design_notes.md` for the full treatment.

Two implications for L4:

- **L4 writes to L5 continuously during a task, not just at the end.** Every step of the pipeline advances the MM: the chosen L3 capacity is instantiated, the DataStates it consumes and produces are appended, the L2 nodes it consults are instantiated into the MM as `ref:global_<role>` references, decision points and strategy choices are pinned. The MM *is* how L4 knows what the current task is thinking about.
- **Retention is the default.** On task completion (success, failure, abort), L4 consolidates the MM into L2's `memories` role-graph unless the user or admin has opted out for this task. Consolidation is a small L4 responsibility: freeze outcome metadata, write the frozen MM as a record in `memories` following KL's versioning pattern, release the L5 live instance. After consolidation, the memory is reachable through `capacity:retrieval` capacities and becomes fuel for dreaming.

**Failure recording.** If any step during a task fails or raises an anomaly, L4 emits a thin `problem-trace` entry (via `capacity:trace`) and attaches a `ref:problem_trace` property to the MM root pointing at it. The failed step remains in the pipeline DAG as a normal `NodeInstance` — no separate `FailureRecord` composite, no duplicated error detail inside the MM. On consolidation, the memory carries the pointer; retrieval-by-result surfaces failed memories for dream-based retry.

**Confidence surfaces on the MM.** The per-run output confidence computed during task execution lives on the MM's root composite (as outcome metadata). The long-lived pipeline confidence lives on the `promoted-pipelines` record used by the run. Neither is a capacity-node property.

### Reference: use cases for verification

See `use_cases_text_realm.md`. Two realms — NLU and code understanding — with concrete cases that exercise L2 consultation, L3 capacity invocation, L4 pipeline-finding, and L5 Mental Model construction. These use cases are the test suite against which L4's design will be validated.

---

**End of notes.** Append as further decisions emerge during L3/L4 discussion.

---

## Changelog

- **2026-04-21 (final L3 session).** Pipeline-level confidence replaces per-capacity confidence: dropped the `capacity-confidence` role-graph. Added `memories`, `problem-trace`, `capacity-state` to the new-role-graphs list; removed `trace-history` (superseded by MM-as-success-trace + thin problem-trace). Rewrote the dreaming section around dreaming-as-task with a `capacity:retrieval` entry point. Rewrote L5's dual role around live-working-memory with retention-by-default consolidation into `memories`. Marked Q2 and Q3 settled.
- **2026-04-21 (earlier).** Appended three-tier memory (L2/L4/L5) and dreaming sections; locked L5 dual role.
- **2026-04-20 and earlier.** Initial cataloguing of L4 responsibilities surfaced during L3 discussion.
