---
title: L4 / L5 Intelligence decisions
tag: shipped
teaser: Decisions shaping the Intelligence Layer and Mental Model.
next: decisions/summary/server.md
---

# L4 / L5 Intelligence decisions

Layer 4 is the orchestrator and learner — the part of the system that improves with experience. Layer 5 is the per-task Mental Model. Both **shipped** in the Phase 46–48 convergence (`mindsos_intelligence` package).

!!! success "Shipped"
    L4 and L5 are live as of Phase 48. The shipped decisions are **ADRs 0163–0181** (table below). The earlier **ADRs 0101–0112** were the design-phase menu settled at the Chat A/B foundation chats; they are retained for historical context and were superseded/absorbed by the shipped set.

## Shipped decisions (ADRs 0163–0181)

| ADR # | Title | Summary |
|-------|-------|---------|
| [0163](../adr/0163-l4-priority-tier-executor.md) | L4 priority-tier Executor + `attention_score` | Four-tier priority executor; preemption by effective score within tier |
| [0164](../adr/0164-mm-rwlock-granularity.md) | MM RWLock — per-active-MM, root granularity, writer-preferred | Concurrency control for the Mental Model |
| [0165](../adr/0165-three-sub-mm-composition.md) | Three-sub-MM composition + thin root + no-shadow-state invariant | Knowledge / capacity / intelligence sub-MMs per task |
| [0166](../adr/0166-mm-resolution-and-instantiation.md) | MM resolution + instantiation layer | Concrete `MMHandle`; pin-at-instantiation |
| [0167](../adr/0167-cooperative-cancellation-contract.md) | Cooperative cancellation framework | Cooperative task cancellation contract |
| [0168](../adr/0168-monitor-subscription-registry.md) | MonitorSubscriptionRegistry — L4-side Monitor lifecycle | Consumes `cl.iter_monitors()`; L4 owns the loop (ADR-0155) |
| [0169](../adr/0169-tier-enum-home-and-signal-triage.md) | TierEnum home (L3) + signal-triage worker thread | Tier enum lives in L3; triage thread placement |
| [0170](../adr/0170-write-body-session-gating-boundary.md) | Write-body capability gating — boundary resolution | Reconciles ADR-0146 / ADR-0159 write gating |
| [0171](../adr/0171-six-phase-task-lifecycle.md) | Six-phase task lifecycle — orchestrator, worker-per-task | The core orchestrator control flow |
| [0172](../adr/0172-phase-1-five-step-task-interpretation.md) | Phase-1 five-step task interpretation + v0 catalog discipline | Task interpretation front-half. ⚠ **Amended by [0206](../adr/0206-planning-decomposition-confidence.md)** — `derive_goal` is deleted there and the v0 catalog is removed; read ADR-0172 §amendment-2 before treating it as current |
| [0173](../adr/0173-replan-check-dispatch-and-invalidation.md) | Replan-check dispatch + invalidate-at-and-below | Replan trigger + ReplanRecord sparsity |
| [0174](../adr/0174-sufficient-predicate-and-phase6-blame-dispatch.md) | Sufficient-predicate evaluator + Phase-6 BlameVerdict dispatch | Completion + blame assignment |
| [0175](../adr/0175-invoke-capacity-context-flip-and-write-gate.md) | `invoke`→CapacityContext flip + write-body gate enforcement | Capacity invocation contract v2 |
| [0176](../adr/0176-mm-consolidation-write-path.md) | MM consolidation write path — freeze+assemble, Episode write, Memory materialize | Task-completion consolidation into L2 |
| [0177](../adr/0177-d-prime-1-retention-lazy-inline-on-retire.md) | D'1 retention — version-pinned refs + lazy inline-on-retire | Full KL version read/retire stack |
| [0178](../adr/0178-dream-live-re-execution-driver.md) | Dream live re-execution driver | Timer hookup + episode `task_input` re-run |
| [0179](../adr/0179-crash-recovery-checkpoint-and-startup-scan.md) | Crash recovery — checkpoint trigger set + tombstone + startup scan | Durability on crash |
| [0180](../adr/0180-write-capability-on-context-scope-aware-gate.md) | Write-half close — pre-authorized `writeable` capability + scope-aware gate | S12 write-half closure |
| [0181](../adr/0181-falkor-index-strategy-cross-sub-mm-queries.md) | Falkor index strategy for cross-sub-MM hyperedge queries | Decide-and-document (physical creation → WSD) |

## The next design generation (ADRs 0205–0206) — NOT in the shipped set above

> ⚠ **The shipped table above is not the current design of planning or of task
> interpretation.** ADR-0206 amends ADR-0172: the interpretation steps become
> `request → hint → map → plan` (**`derive_goal` is deleted**), *plan* becomes a loop
> (`search → find → decompose → repeat`), `MAX_DEPTH` is retired in favour of a
> per-transition confidence threshold, and the thirteen `placeholder=True` v0 capacities
> are deleted rather than replaced. It is **Proposed and unbuilt** — CORE-C4 has not
> started — so the shipped set is what runs. This section exists because a reader who
> oriented from this page alone could not previously discover that ADR-0206 exists.

| ADR # | Title | Status | Summary |
|-------|-------|--------|---------|
| [0205](../adr/0205-abstraction-levels.md) | Abstraction levels — one graph at several resolutions | Accepted | The level ladder ADR-0206 sits on: capacity → pipeline → milestone → plan → request |
| [0206](../adr/0206-planning-decomposition-confidence.md) | Planning as a loop — milestones, decomposition, and confidence | Proposed | Amends [0172](../adr/0172-phase-1-five-step-task-interpretation.md). Confidence is the stopping rule; decomposition emits one layer at a time; `request_knowledge` replaces `request-patterns` |

## Design-phase menu (ADRs 0101–0112 — historical)

The original L4 design exploration, settled at the Chat A/B foundation chats and superseded/absorbed by the shipped set above. Retained for context.

| ADR # | Title | Summary |
|-------|-------|---------|
| [0101](../adr/0101-l4-per-session-orchestrator.md) | One IntelligenceLayer per live user session | No Global L4; learned state lives in L2; simple tenancy model |
| [0102](../adr/0102-l4-policy-as-meta-pipelines.md) | All decision-point policies composed from L3 capacities as meta-pipelines | Learnable; hard-coded Python doesn't freeze the meta-layer; inspectable |
| [0103](../adr/0103-l4-attention-priority-queue.md) | Orchestrator attention mechanism - priority queue keyed by live attention score | Four priority tiers (CRITICAL, FOREGROUND, BACKGROUND, DREAM); preemption by effective-score within tier |
| [0104](../adr/0104-l4-replan-always-on.md) | Replan trigger - always-on at every step boundary with fast-path | Fresh information always considered; fast-pass for high-confidence cases |
| [0105](../adr/0105-l4-replan-atomicity-discard.md) | Replan atomicity - discard remaining plan; regenerate from current state | Full regeneration on replan; simple logic; new information incorporated into entire remaining plan |
| [0106](../adr/0106-l4-planning-ownership.md) | Planning ownership - L4 orchestrates; planning algorithms are L3 capacities | Planning is a learnable meta-pipeline; algorithms are inspectable L3 nodes |
| [0107](../adr/0107-l4-six-planner-menu.md) | Planner menu - six loadable planning algorithms shipped as separate files | BFS, A*, Dijkstra, CSP, beam search, template-pattern-match; extensible drop-in pattern |
| [0108](../adr/0108-l4-planner-selection-learned.md) | Planner selection is learned per task shape | Chooser has its own promoted-pipelines record; improves via learning loop |
| [0109](../adr/0109-l4-cost-estimators-as-capacities.md) | Cost estimators are L3 capacities, not static node properties | Separate estimators per dimension (latency, tokens, dollars); learnable via observation |
| [0110](../adr/0110-l4-coherence-dream.md) | Coherence dream intent - GAN-like generator vs critic for training stability | Fourth dream intent alongside maintenance, exploration, retry; generator/critic for plan stability |
| [0111](../adr/0111-l4-promotion-dependency-graph.md) | Promotion dependency graph - Local capacities block Global promotion until resolved | Safe-by-default; admin sees dependency graph; two-step promotion when Local steps exist |
| [0112](../adr/0112-l4-pause-and-resume.md) | Pause-and-resume support for voluntary logout | Paused MM as normal memory; resume scans paused tasks on login; forced logout aborts |

---

**Next:** [Server decisions](server.md) — identity, sessions, and promotion orchestration.
