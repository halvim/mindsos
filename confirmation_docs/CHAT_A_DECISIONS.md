# Chat A — Decisions Log

**Purpose.** Per-decision settlement record. Chat C plan-authoring inherits from here.
**Format per decision:** ID, status, pick, rationale, alternatives considered, downstream cascades.
**Live document.** Appended round-by-round as Chat A progresses.

---

## R1 — D32 Concurrency Model

**Decision ID:** D32
**Round:** R1
**Status:** Pre-resolved per user 2026-05-28; R1 confirms architectural shape + resolves sub-decisions.

### Architectural shape (confirmed)

**Pick: B — Single-process, multi-threaded.** One Python process per `IntelligenceLayer` session (matching settled §1.1 lifecycle). Three thread classes:

- **Orchestrator thread (main).** Owns attention queue, plan-run state, replan-check dispatch, sufficient-predicate evaluation, phase transitions.
- **L3 worker pool.** N worker threads execute L3 capacity invocations. Returns `Future`-like handles to orchestrator.
- **Signal-triage worker (dedicated).** Polls L3 resident-capacity emit queues; classifies signals into priority tiers; surfaces CRITICAL signals to orchestrator's next-yield point.

**No subprocess pool in v1.** Per-capacity escape hatch via `ProcessPoolExecutor` is v2 opt-in (see D32.7).

### D32.2 — Signal-triage worker presence

**Pick: A — always-on dedicated thread.**

Rationale: Cost of one always-resident thread is negligible (<1MB stack); behavior is deterministic; debugging is trivial. Solves Push 8 unconditionally — CRITICAL signals never become invisible during long L3 calls.

Alternatives considered: (B) on-demand spawn — spawn latency hides early CRITICAL signals; (C) integrate triage into orchestrator main-loop poll — couples triage cadence to L4 task shape, fragile.

### D32.3 — MM locking granularity

**Pick: C — reader-writer lock.**

Rationale: Replan-check + sufficient-predicate run on orchestrator thread, are read-heavy, and run between every step. L3 capacity writes (DataState appends, decision-point pins) are bursty but less frequent. Reader-writer matches access pattern.

Alternatives considered: (A) whole-MM mutex — serializes all writes, throughput cap; (B) per-instance lock — deadlock risk with multi-instance writes; (D) copy-on-write — readers see stale state, flush scheduling complexity.

Implementation note: lock-fairness mode (writer-preferred when waiting > N ms) prevents writer starvation. Implementation-level, not architectural.

### D32.4 — L3 capacity threading contract

**Pick: B — opt-in concurrency via `concurrent=False` registration flag.**

Default for new capacities = `concurrent=True` (must be thread-safe). Phase 27–33 shipped capacities get audited; non-thread-safe ones get `concurrent=False` annotation.

**Resident clarification (added post-reanalysis 2026-05-28).** Residents don't take a `concurrent` flag — they always have inherently serialized state. Threading constraints on residents:
- `start_resident()` and `stop_resident()` MUST be called from orchestrator thread. Never from a worker. (Phase 31 already implicitly serializes; this makes the constraint explicit.)
- Resident `invoke()` submits to worker pool like any L3 call, but resident-internal state mutations serialize on a resident-internal lock (not the L3 invocation lock).
- Per L4 contract: one resident per capacity-IRI per session, so concurrent invocations on the same resident-instance are impossible.

Alternatives considered: (A) all must be thread-safe — burden on capacity authors + breaks shipped capacities; (C) global L3-invocation lock — defeats the worker pool; (D) all must be stateless — incompatible with residents (UC-WSD-2 Monitors).

Cascade: changes L3 registration contract. Coordinated with L1/L3 reframe chat (per Q2 routing). Capacity-registration contract change adds `concurrent: bool = True` field. Resident registration API documents orchestrator-thread-only constraint.

### D32.5 — Cancellation model

**Pick: A — cooperative cancellation via `cancel_token` kwarg.**

L4 contract: every L3 capacity that may run >100ms accepts an optional `cancel_token` kwarg and checks `.is_set()` at natural yield points. LLM and prover capacities wrap backend calls with cancellation hooks.

Alternatives considered: (B) thread-killing via `ctypes.PyThreadState_SetAsyncExc` — unreliable in Python, may leak resources; (C) no cancellation — weakens `stop(mode="abort")` semantics (abort doesn't immediately stop in-flight L3 call).

Discipline: at L3 capacity registration, declared-latency > threshold requires `cancel_token` in signature. Lint/test enforcement.

### D32.5b — Priority-tier executor (added post-reanalysis 2026-05-28)

**Pick: A — single custom Executor with priority queue.**

Standard `ThreadPoolExecutor` is FIFO across tiers — CRITICAL waits behind queued BACKGROUND tasks. Push 6 four-tier preemption (CRITICAL > FOREGROUND > BACKGROUND > DREAM) would be silently weakened.

**Custom `Executor` subclass** wraps a `PriorityQueue` keyed by `(tier, submit_time)`. ~50 LOC. Tier vocabulary shared with D32.2 signal-triage (same tier enum, same dispatch semantics).

Note: this gives queue-priority ordering, not preemption of running tasks. Combined with D32.5 = A cooperative cancellation, a running BACKGROUND task can be cancelled when CRITICAL arrives — orchestrator signals cancel; worker releases at next yield point; tier ordering ensures CRITICAL submits first.

Alternatives considered: (B) one executor per tier — 4N threads per session; (C) FIFO + tier check before submit — doesn't solve running-task case; (D) defer to v2 — Push 6 silently weakened at queue layer.

Cascade: tier-aware Executor is a new L4-internal primitive. Push 6 (D6) confirms tier vocabulary in R2.

### D32.5c — Within-tier score-based ordering + dynamic re-prioritization (added 2026-05-28)

**User pick:** Within-tier ordering is score-based, not FIFO. L4 owns a per-task score, mutable at any time. Combined with D32.5b tier-aware Executor, gives unified adrenaline mechanism.

**Queue key:** `(tier, -attention_score, submit_time)`. Tier dominates; within-tier ordered by descending attention_score; submit_time is final tiebreaker.

**New Executor APIs:**
- `set_score(task_id, new_score)` — mutate within-tier score; lazy-delete + re-insert.
- `elevate(task_id, new_tier=None, new_score=None)` — change tier and/or score; lazy-delete + re-insert.
- Both trigger auto-preempt-on-elevation per D32.5b semantics.

**Within-tier preempt rule:** `new_score > running_score + hysteresis_constant`. Hardcoded L4 logic. Prevents ping-pong.

#### Sub-pick D32.5c.1 — Score function origin

**Pick: D — Hybrid (constant default + optional L3 mutation hook).** v1 ships with constant per-tier default; L4 calls `set_score()` to mutate. v2 adds an L3 `scoring.initial_priority` capacity hook without breaking the API.

Alternatives considered: (A) constant only — no upgrade path; (B) admin per-task-pattern defaults — adds L2 schema field, premature; (C) L3 capacity always — adds invocation latency per submit, bootstrap complexity.

#### Sub-pick D32.5c.2 — Score type

**Pick: A — Integer 0–9999 within tier.** Predictable, easy to debug, cheap heap ops.

Default scores per tier:
- CRITICAL = 1000
- FOREGROUND = 500
- BACKGROUND = 100
- DREAM = 10

#### Sub-pick D32.5c.3 — Hysteresis constant

**Pick: B — Per-deployment configurable, default H=50.** Prevents ping-pong; tunable without code change.

#### Sub-pick D32.5c.4 — Score visibility on MM

**Pick: B — Score lives on queue AND on PlanRun composite in MM.** Queue holds live; MM carries last-written (write-through on `set_score`).

Replan-check + sufficient-predicate read MM's `attention_score` field for context. Sync: `set_score()` writes both atomically under MM writer lock (per D32.3 = C reader-writer lock).

Cascade: PlanRun composite gains `attention_score: int` field. Captured as L1/L2 schema addition in L1_FUTURE_WORK.md or L2_FUTURE_WORK.md (TBD which layer owns PlanRun composite schema).

#### Sub-pick D32.5c.5 — Default score on bare `elevate(tier=...)`

**Pick: C — Top of new tier.** When L4 calls `elevate(task_id, new_tier=CRITICAL)` without explicit score, task gets max-current-CRITICAL-score + 1 (or tier-max if empty). Full adrenaline = immediate top priority within new tier.

Explicit score wins if provided.

### Vocabulary discipline

Call the new concept `attention_score` or `priority_score`, never just `score`. Avoids confusion with existing `confidence` (pipeline-level on `promoted-pipelines` + per-run on MM root). Adopt `attention_score` for queue+MM.

### Push 6 cascade (R2)

WSD §3.4 ACCEPT-on-Push-6 picked FIFO within tier. D32.5c re-opens this partially:
- Keep: 4 tiers, cross-tier hard preempt, NO learnable preemption coefficients (sunk_cost_bonus, interruption_cost remain dropped).
- Change: within-tier ordering is score-based (not FIFO); score is L3-capacity-computed with learnable parameters via ALS; within-tier preempt rule is `new_score > running_score + hysteresis`.

R2 ratifies Push 6 under PARTIAL-ACCEPT-2 framing.

### D32.5c.6 — ALS subsystem registration for priority-scorer (added 2026-05-28)

Attention-score capacity registered as ALS subsystem. WSD §4.3 already lists 9 v1 subsystems; this becomes #10.

- **parameter_set_iri:** attention-score weights per task-pattern (within-tier scoring) + tier-default-override per task-pattern.
- **Signal sources:** S6 (task outcome), S9 NEW (mutation-frequency), admin-override events.
- **Mechanisms:** bayesian_update + ema.
- **Validation methods:** V1 (gold accuracy on user-task latency vs expected), V3 (drift on score distribution).
- **Audit policy:** batched-summary (matches WSD §4.3 pipeline-finding-parameters pattern).
- **Eligible scopes:** Local + Global.

### D32.5c.7 — New ALS signal source S9 (added 2026-05-28)

S9 mutation-frequency / score-change-rate per task-pattern. Captures user's meta-feedback insight: frequent re-scoring of a task-pattern class = initial scoring policy is mistuned.

- Emitted by L4 on every `set_score()` and `elevate()` event.
- Logged to `parameter-staging` as evidence for the priority-scorer ALS subsystem.
- v1 only consumer: priority-scorer subsystem. Other subsystems may subscribe later.

### D32.5c.1 (revised) — Score function origin

**Revised pick: L3 capacity with learnable parameters from v1** (not D constant + v2 hook).

L3 capacity `scoring.attention_score(task, context) -> int` registered v1. Parameters in `L2.learned-parameters` keyed by capacity IRI. Cold-start: constant per-tier defaults (CRITICAL=1000, FOREGROUND=500, BACKGROUND=100, DREAM=10) until ALS accumulates evidence.

Mutation policy stays hardcoded L4 in v1 (explicit events: CRITICAL signal arrival, admin abort, etc.). v2 may add `decision.preempt_target` L3 capacity. Mutation events feed ALS via S9 signal source to retrain initial-score policy.

Cascade: new L3 capacity family added to L3_FUTURE_WORK.md.

---

## L4-vs-L3 boundary (architectural target, added 2026-05-28)

**Strict line: L4 = substrate + control flow only. Everything else = L3.**

Per user pick 2026-05-28: all decisions and computations are L3 capabilities; L4 is a runtime that invokes L3 capacities and maintains state.

### L4 retains (substrate + control flow)

- IntelligenceLayer class lifecycle (`start`, `stop`, `enqueue`).
- Attention queue data structure + queue ops (push, pop, lazy-delete, peek).
- Custom priority-tier Executor (D32.5b).
- Worker pool + thread management.
- MM RWLock per active MM (D32.3).
- Plan-run state machine + status transitions on MM root.
- Phase-loop control flow (Phase 1 → 2 → 3 → 4 → 5 → 6 transitions). **v1 = one phase-loop in L4; v2 may reframe as L3 orchestration capacity if alt phase-loops emerge.**
- Signal-triage thread (the thread; the classifier it calls is L3).
- ALS dream-cycle timer.
- ALS subsystem registry + aggregate flow (control flow invoking L3 mechanism + validate + L0 audit).
- Cooperative cancellation plumbing (`cancel_token` framework).
- Cancel-target selection (v1 hardcoded "lowest-priority running"; v2 → L3 `decision.preempt_target`).
- Invocation dispatch (orchestrator → worker pool; orchestrator → inline L3).
- Tier enum vocabulary (shared with L3 classifier, lives in shared module).

### L3 (decisions and computations, all invoked by L4)

- `scoring.attention_score(task, context) -> int` — learnable.
- `decision.signal_to_tier(signal) -> tier` — signal-triage classifier.
- `decision.should_replan(state, divergence) -> verdict` — replan-check.
- `predicate.action_contract.precondition(state)` / `effect(state)` — Push 2.
- `predicate.sufficient(state, task_pattern) -> bool` — sufficient-predicate evaluator (predicate data in L2.task-patterns).
- `decision.promotion_rule(candidate) -> rule_iri` — WSD §A.1.
- `decision.task_to_pipeline(task_shape, lookup) -> pipeline` — pipeline-finder.
- `phase6.attribute_blame(outcome, path) -> blame_map` — WSD §A.5.
- `scoring.cost.*` — per ADR-0109.
- `mechanism.*`, `combination.*`, `comparator.*`, `evaluator.*`, `metric.*`, `validate.*` — WSD method libraries.
- `signal_source.S1` through `signal_source.S9` — ALS signal-source capacities.
- **MSUR (L3 orchestration capacity)**.
- **SCMS BSP turn (L3 orchestration capacity per WSD §A.6)**.
- Quiescence detection — internal to SCMS L3 capacity.
- Promotion-proposer dependency walking — already L3 per ADR-0111.

### Capacity registration contract (additions)

Two orthogonal flags on `register_capacity`:
- `concurrent: bool = True` — capacity tolerates concurrent invocations across threads.
- `inline: bool = False` — capacity skips worker pool dispatch, runs on caller's thread synchronously.

`inline=True` capacities MUST: declare max-latency budget; be CPU-bound (no I/O); not hold long write locks on MM.

L3 capacity contract allows non-DataState scalar/enum returns for `decision.*`, `scoring.*`, `metric.*`, `combination.*`, `comparator.*`, `evaluator.*`, `validate.*` families (per WSD §5.2 method-library precedent).

### Vocabulary fix

`set_score()` / `elevate()` as L4 public API names mask the L3-decision + L4-mutation split. Rename:
- `queue.write_priority(task_id, score, tier=None)` — pure L4 mutation.
- L4 wrapper `update_priority(task_id, context)` invokes L3 `scoring.attention_score` then `queue.write_priority`.

### Push 1 cascade (R2)

WSD §3.5 PARTIAL-ACCEPT listed 6 hardcoded items + 2 L4 pipelines (MSUR, SCMS). PARTIAL-ACCEPT-4 framing reshapes:
- 6 hardcoded items: 4 fully move to L3 (attention-score, signal-triage classifier, promotion-proposer-walk-which-was-already-L3, quiescence-which-lives-inside-SCMS); 2 split (replan-check, sufficient-predicate — dispatch L4, decision L3).
- 2 L4 pipelines: both → L3 orchestration capacities (MSUR by symmetry with SCMS §A.6).
- L4 hardcoded list reduces to: data-structure mutations, state-machine transitions, lock arbitration, queue ops, lifecycle methods, thread management.

L4 v1 LOC estimate: ~800–1200 (vs WSD's 4–6k under prior framing). ~70% redistributes to L3.

WSD installation chat will see PARTIAL-ACCEPT-4 as an amendment to WSD §3.5.

### Cascade items added to other docs

- `L3_FUTURE_WORK.md` L3-33: new L3 decision/scoring capacity family — ~15-20 new capacities (`scoring.attention_score`, `decision.signal_to_tier`, `decision.should_replan`, etc.).
- `L3_FUTURE_WORK.md` L3-34: capacity registration contract gains `concurrent: bool = True` and `inline: bool = False` flags (codifies D32.4 + L3 boundary contract).
- `L4_FUTURE_WORK.md` L4-6: phase-loop-as-L3 capability flagged as v2+ if alternative phase-loops emerge.

---

## R2 — Pushes 1–7 + Push 8 Ratification

**Round:** R2
**Status:** Ratified 2026-05-28.

### Push 1 — Meta-pipeline-everywhere

**Pick: PARTIAL-ACCEPT-4** (inherited from R1 L4-vs-L3 boundary).

L4 = substrate + control flow only. All decisions / computations are L3 capabilities. MSUR + SCMS are L3 orchestration capacities (per WSD §A.6 extended). Hardcoded L4 list reduces to data-structure mutations, state-machine transitions, lock arbitration, lifecycle, threading.

WSD §3.5 PARTIAL-ACCEPT amended.

### Push 2 — Replan-check predicate via action contracts

**Pick: ACCEPT-A with backward-compat + predicate-IRI sub-pick (b).**

- L3 capacity registration gains **optional** `precondition_iri` + `effect_iri` fields.
- `precondition_iri` + `effect_iri` are L3 predicate-capacity IRIs (predicates ARE capacities; consistent with strict-line architecture).
- Phase 27–33 shipped capacities default to no-contract; replan-check evaluates whatever contracts ARE present and marks the verdict `verified=False` for steps without contracts.
- WSD-era + future capacities declare contracts.

Predicate L3 capacity family added: `predicate.dataState_exists`, `predicate.dataState_value_eq`, `predicate.signal_present`, etc. Family is small + reusable.

**Verdict shape (revised post-PB-R2-2 explanation):**

```python
@dataclass
class ReplanVerdict:
    decision: Literal["continue", "replan", "abort"]
    verified: bool        # False when contracts absent
    divergence: float     # 0.0 when unverified
```

3 decisions (continue / replan / abort) + a `verified` flag + a `divergence` magnitude. Downstream consumers branch on `decision`; weight confidence by `verified`; ALS S8 signal observes `divergence` and `verified=False` events to surface contract-less capacities for contract authoring.

Captured in `decision.should_replan` capacity contract.

### Push 3 — Coherence dream loop

**Pick: ACCEPT cut + ALS substitutes (Q5 resolution).**

Coherence dream loop cut from v1. ALS Track A/B replaces parameter-learning function. FOL plural-strategies registered for FOL design chat (not Chat A scope).

Implication: dream intent count drops 4 → 3 (maintenance, exploration, retry). `stability` property in `promoted-pipelines` is unused; remove or repurpose.

### Push 4 — Per-plan assumption/expectation

**Pick: DROP. Subsumed by Push 2 action contracts.**

Per-plan assumption/expectation is expressible via action contracts on L3 capacities. No separate L4 machinery.

### Push 5 — Pause-and-resume

**Pick: DEFER to post-v1; ship signature.**

- `stop(mode="pause"|"abort")` signature shipped; v1 server only invokes `mode="abort"`.
- `stop(mode="pause")` raises `NotImplementedError` in v1.
- `retrieval.paused_plan_runs`, `PlanRunStatus.PAUSED`, `PlanRunStatus.INVALIDATED_ON_RESUME` removed from v1 scope.
- ~300 LOC + state validation saved.

UC-WSD-6 admin abort case covered by `mode="abort"`.

### Push 6 — Four-tier preemption

**Pick: PARTIAL-ACCEPT-2** (inherited from R1 D32.5c).

- Keep: 4 tiers (CRITICAL/FOREGROUND/BACKGROUND/DREAM); cross-tier hard preempt; drop learnable preemption coefficients (sunk_cost_bonus, interruption_cost).
- Add: within-tier ordering is score-based via L3 `scoring.attention_score` capacity; score is ALS-learnable; within-tier preempt rule `new_score > running_score + hysteresis`.

WSD §3.4 ACCEPT amended.

### Push 7 — Predicate distillation

**Pick: DROP entirely.**

No `predicate-corpus` role-graph; no distillation dream intent. LLM verdicts unstable enough that distillation produces noise. No UC depends on it.

FOL distillation-reconsider flagged as FOL-chat-watch item (FOL hasn't issued explicit drop verdict, only ACCEPT-recommend at HANDOFF_latest level).

### Push 8 — Signal-thread correctness

**Pick: STRUCTURAL resolution from R1.**

D32.2 = A always-on signal-triage worker + D32 = B workers handle L3 + D32.5 = A cooperative cancellation → CRITICAL signals never become invisible. Not "weakened to next-yield"; structurally always-visible.

Caveat: D32.5 cooperative cancellation depends on long CPU-bound L3 calls reaching yield points. FOL prover case may delay preempt (mitigated by D32.7 = C v2 subprocess escape hatch).

### Pushbacks against R2 picks

**PB-R2-1.** Predicate family adds 5–10 capacities to L3 catalog. Captured as L3-36 in L3_FUTURE_WORK.md.

**PB-R2-2 (resolved).** Initial framing was 4-valued verdict. User feedback: explain. Resolution: collapse to 3 decisions (continue / replan / abort) + `verified: bool` + `divergence: float`. Less API surface; same diagnostic power. ALS S8 reads `divergence` and `verified=False` events.

**PB-R2-3.** Push 3 cut loses unsupervised improvement avenue. Dream-exploration intent partly covers. Watch v2 if missing matters. Captured as L4-8 in L4_FUTURE_WORK.md.

**PB-R2-4.** Push 5 ships `stop(mode="pause")` as NotImplementedError. Tests must not exercise it. Discipline-level.

**PB-R2-5.** Push 7 drop is firm; FOL chat may re-litigate. Captured in FOL future_chat_prompt or L4_FUTURE_WORK.md L4-9.

**PB-R2-6.** Push 8 depends on cooperative cancellation reliability. v1 limitation documented; v2 escape hatch (D32.7 = C) addresses for known-tight-loop capacities.

### Cascade items added

- L3-36 (NEW): predicate L3 capacity family (5–10 reusable predicates).
- L4-8 (NEW): unsupervised-improvement v2 watch item.
- L4-9 (NEW): Push 7 distillation reconsider — FOL-chat-watch.
- `decision.should_replan` verdict shape: `ReplanVerdict(decision, verified, divergence)` — 3 decisions + 2 metadata fields. Captured in L3-33 family spec.

---

*R2 complete.*

---

## R3 — ALS Architecture + Calibration Target

**Round:** R3
**Status:** Ratified 2026-05-28.

### D9.1 Subsystem registration contract

**Pick: ACCEPT WSD §4.2 shape.**

```python
@dataclass
class ALSSubsystemRegistration:
    parameter_set_iri: IRI
    signal_sources: list[tuple[IRI, float]]
    update_mechanisms: dict[IRI, IRI]
    validation_methods: list[IRI]
    audit_policy: Literal["auto-apply", "batched-summary", "individual-review"]
    eligible_audit_scopes: frozenset[Literal["local", "global"]]
```

L4 owns the registry (dict). All IRIs point to L3 capabilities. Consistent with R1 strict line.

### D9.2 Track A vs Track B + v1 subsystem list (10 total)

**Pick: ACCEPT WSD §4.3 split + add priority-scorer (R1) to Track B batched-summary.**

| # | Subsystem | Track | Audit Policy |
|---|---|---|---|
| 1 | WSD candidate-scorer | B | individual-review |
| 2 | FOL rule confidences | B | individual-review |
| 3 | promoted-pipelines confidence | B | batched-summary |
| 4 | Pipeline-finding parameters | B | batched-summary |
| 5 | Task-shape recognition priors | B | individual-review |
| 6 | Goal verification thresholds | B | individual-review |
| 7 | Class generalization materialization policy | A | auto-apply |
| 8 | Per-hierarchy class-generalization weights | B | batched-summary |
| 9 | sense-correlations (Track A) | A | auto-apply |
| 10 | Priority-scorer / attention_score (R1) | B | batched-summary |

Concrete `parameter_set_iri`s + mechanism choices = WSD installation chat work.

### D9.3 Audit-policy override semantics

**Pick: ACCEPT WSD §4.7 more-conservative-only.**

Policies form total order: `auto-apply < batched-summary < individual-review`. User can override toward more-conservative; not toward less-conservative.

**Disable-subsystem is SEPARATE from audit-policy override.** Disable lives on L0 `user_settings` per WSD §4.6 + UC-WSD-8. Audit-policy override lives on per-session per-subsystem state. Two mechanisms.

### D9.4 Local→Global aggregation flow location

**Pick: A — Global cycle runs in L0 admin tools.**

Per R1 PB-E: no Global L4 → Global aggregation has no L4 home. Ships as a library that L0 admin tools import. Admin-triggered per WSD §4.5.

### D9.5 L2 role-graph shapes

**Pick: ACCEPT WSD §4.8 3-role-graph design (single `learned-parameters` for v1).**

- `parameter-staging` (Local only) — NEW.
- `pending-promotions` (Local + Global) — NEW.
- `learned-parameters` (Local + Global, ship-both per Q4) — existing/shipping.

Cascade: ADR-0150 §am-1 amendment for role-graph expansion.

**FOL #4 split flagged for R5.** `parameter_set_iri` is opaque IRI → v2-compatible if split lands later.

### D9.6 ALS dream-cycle threading (resolves D32.8)

**Pick: A — ALS aggregate as a task through normal phase-loop.**

Consistent with ADR-0091 (dream is a task) + R1 strict line. ALS aggregate becomes L3 orchestration capacity `als.aggregate_subsystem` invoked during DREAM-tier task's Phase 3.

L4 substrate timer enqueues `dream.maintenance.als_aggregate` task; task runs Phase 1–5; Phase 3 invokes aggregator capacity.

### D9.7 v1 registered subsystems

**Pick: RATIFY 10-subsystem list (D9.2 table).** Per-subsystem detail = WSD installation chat.

### D49 Calibration target as system-wide commitment

**Pick: A — System-wide non-functional commitment.**

- **V1 (gold accuracy)** — mandatory for every Track B subsystem.
- **V2 (calibration ECE/Brier)** — mandatory for every Track B subsystem.
- **V3 (distribution drift)** — mandatory for subsystems with `eligible_audit_scopes ⊇ {local, global}`.

Track A subsystems may declare lighter validators (statistical sanity).

Cold-start: "skip if no gold set" semantics; gold-set authoring required within N tasks after first evidence.

### Pushbacks against R3 picks

**PB-R3-1.** 10 ALS subsystems is large v1 scope. Mitigation: most start with constants; learning ramps over time. Cold-start period may be long (UC-WSD-7).

**PB-R3-2.** Single `learned-parameters` ships v1; FOL #4 split deferred to R5. `parameter_set_iri` opaque IRI → v2-forward-compatible.

**PB-R3-3.** DREAM-tier ALS task always preempted by user tasks. Under continuous load, ALS may not run. Mitigation: admin can elevate via R1 D32.5c `queue.elevate()`. v1 default DREAM-tier.

**PB-R3-4.** L0 admin-triggered Global cycle (D9.4) — no automatic cross-user aggregation in v1. v2 may want L0 scheduler. Captured L0-future.

**PB-R3-5.** V1+V2 mandatory means gold-set authoring required per subsystem. Cold-start gold-set unavailable. Mitigation: "skip if no gold set" + N-task deadline.

**PB-R3-6.** Disable vs audit-override distinction documented in WSD installation chat.

**PB-R3-7.** L0 user_settings (L0-4) is sequencing prereq for ALS Track B user-preference reading.

**PB-R3-8.** `als.aggregate_subsystem` is meta-capacity (invokes other capacities). Pattern consistent with SCMS/MSUR.

### Cascade items added

- L2-23 (NEW): `parameter-staging` + `pending-promotions` L2 role-graph schemas.
- L3-37 (NEW): `als.aggregate_subsystem` L3 orchestration capacity + ALS mechanism family + validator family (V1/V2/V3).
- L0-12 (NEW): L0 admin-tooling library export for Global ALS cycle.

---

*Initial R3 complete.*

---

## R3 extensions (multi-turn reanalysis 2026-05-28)

### Validator rename

`V1/V2/V3` → namespace IRIs: `validate.gold_accuracy`, `validate.calibration_ece`, `validate.distribution_drift`. Conversational shorthand: gold-validator, calibration-validator, drift-validator. Eliminates clash with version v1/v2/v3.

### Pipeline confidence migration

Pipelines are **binary deterministic solvers** (not probabilistic). Tested before approval. ADR-0094 revised:

- `promoted-pipelines` schema loses `confidence` field.
- Pipelines that fail get **quarantined** (admin review) → possibly retired.
- Confidence migrates to **task-to-task-type mapping** (subsystem #4).
- ALS v1 subsystem count: 9 (removed former "promoted-pipelines confidence").
- Renumbered: #3 = Pipeline selection parameters (efficiency-ranking among valid pipelines); #4 = Task-to-task-type mapping confidence (load-bearing).
- "Pipeline selection" learns efficiency ordering when multiple valid pipelines exist for the same task type.

### D51 — Capacity-pipeline-pattern pairing contract

Admin/user-authored L3 capacities MUST be paired with at least one seed pipeline. Task-pattern authoring MUST include at least one paired pipeline. Enforced at registration via tooling + L4 startup invariant. Generalized to: every task-pattern has ≥1 paired pipeline; every capacity is referenced by ≥1 pipeline.

### Teaching methods (open task-type space)

Task-type space is **infinite/open** — admins cannot pre-enumerate. Teaching interface is v1 deliverable. v1 ships:

- **Method 2 (structured declaration)** — primary admin authoring path; matches Phase 13 schema.
- **Method 4 (demonstration by execution)** — secondary; reuses Phase 30+ CLI with `--register-task-pattern`.
- v1.5: Method 5 (memory annotation).
- v2+: Methods 1, 3, 6, 7 deferred.

### "I don't know" as first-class output

Two kinds of uncertainty:
- **Mapping uncertainty** — am I solving the right problem?
- **Output uncertainty** — assuming I solved the right problem, how sure of the answer?

3-valued decision enum + 4 don't-know categories:

```python
@dataclass
class TaskOutcome:
    decision: Literal["answer", "dont_know", "uncertain_answer"]
    payload: Optional[Any]
    dont_know_reason: Optional[DontKnowReason]
    mapping_confidence: float
    output_confidence: Optional[float]
    suggested_action: Optional[str]

class DontKnowReason(Enum):
    NO_MATCHING_PATTERN = "no_matching_pattern"        # hard gap
    LOW_MAPPING_CONFIDENCE = "low_mapping_confidence"  # soft gap
    PIPELINE_UNAVAILABLE = "pipeline_unavailable"      # mapping ok, no path
    UNRESOLVED_AMBIGUITY = "unresolved_ambiguity"      # multiple patterns matched at comparable confidence
```

`dont_know` is Phase 1 / Phase 2 early-exit. `uncertain_answer` is Phase 4 outcome with calibrated confidence.

D20 expanded: `decision.classify_dont_know_reason` (4-way + ambiguity classifier).

### System-trust contract (alongside D49)

"Honest don't-know + calibrated confidence" = system-trust commitment. Trust contract:
1. System reports confidence calibrated to observed accuracy (D49).
2. System admits don't-know honestly when below threshold (4 categories).
3. Calibration-validator monitors both positive-output confidence AND dont-know threshold correctness.

### Per-task-pattern mapping-confidence threshold

Each task-pattern declares its own `mapping_confidence_threshold`. ALS subsystem #4 refines via observation. Global default exists as fallback for newly-authored patterns.

### Gap 4 refinement (cold-start defaults)

`learned-parameters` v0 written to **Global** at install via bootstrap importer. **Local** starts empty; reads fall through to Global per KL pattern.

- Fresh install: bootstrap importer.
- Software release adds subsystem: release migrator ships bootstrap importer for new subsystem.
- New user: Local empty → reads Global v0.
- Admin reset / DB restore: admin runs targeted importer.

`ALSSubsystemRegistration.bootstrap_importer_iri: IRI` field. L4 startup verifies Global v0 exists; invokes if absent (self-healing).

---

## R3 reanalysis pushbacks (final saturation pass)

### PB-R3-17 — ALS subsystem application dependency order

**Pick: A — `applies_after: frozenset[IRI]` field + topological sort at apply.** Captures real dependencies (mapping #4 before selection #3). v1 ships with known dependency edges.

### PB-R3-18 — Signal source semantics under binary pipelines

**Pick: A — enrich S6 payload to include efficiency metrics.** S6 payload becomes structured: `{outcome, latency_ms, cost_tokens, output_quality_score, dont_know_occurred, ...}`. Catalog stays at 9 signal sources.

### PB-R3-19 — Don't-know calibration validator

**Pick: C — calibration-validator handles both positive-output and dont-know calibration.** Semantic clarification: validator monitors that reported confidence (including dont-know threshold) matches observed accuracy.

### PB-R3-20 — Phase 1 multi-decision control flow

**No Chat A pick required.** WSD installation chat detail.

### PB-R3-21 — Pipeline-pattern many-to-many schema

**Pick: C — store both sides; task-pattern is source of truth.** `paired_pipelines` on task-pattern is authoritative; `serves_task_types` on pipeline is derived/cached. Integrity-check at startup.

### PB-R3-22 — Pipeline status enum expansion

**Pick: A — 5 states.** `draft → tested → active → quarantined → (active OR retired)`. Phase 13 `promoted-pipelines` schema v2 amendment.

---

## R3 cascade items (consolidated)

- L0-13: capacity-gaps admin tooling polished for v1 (under open task-type space, common case).
- L0-14: HITL clarification channel + interactive-mode detection.
- L0-15: new audit event constants (EVT_PIPELINE_QUARANTINED, EVT_PIPELINE_DELETED, EVT_TASK_PATTERN_AUTHORED, etc.).
- L2-23: `parameter-staging` + `pending-promotions` L2 role-graph schemas.
- L2-24: bootstrap-importer suite checklist (capacities + pipelines + task-patterns + learned-parameters v0).
- L2-25: `promoted-pipelines` schema v2 (5-state status enum + paired_pipelines + serves_task_types; ADR-0094 amended).
- L3-37: ALS L3 capacity family (`als.aggregate_subsystem` + mechanism family + validator family).
- L3-38: `pattern.extract_task_shape` capacity (Method 4 enabler).
- L3-39: `decision.classify_dont_know_reason` capacity (replaces D20 2-way classifier; 4-way + ambiguity).
- L3-40: shape-indexing for fast Phase 1 pattern matching (perf).
- L3-41: S6 enriched payload schema (outcome + efficiency metrics).
- L4-10: pattern-conflict admin alert mechanism (ALS dream-aggregate surface).
- L4-11: TaskOutcome schema with 3-valued decision enum + DontKnowReason.
- L4-12: per-task-pattern mapping-confidence threshold + ALS subsystem #4 refinement.
- L4-13: multi-pattern conflict policy per-task-pattern.
- L4-14: ALS subsystem `applies_after` field + topological apply ordering.

---

## R3 final v1 ALS subsystem list (9 total)

| # | Subsystem | Track | Audit Policy | applies_after |
|---|---|---|---|---|
| 1 | WSD candidate-scorer | B | individual-review | — |
| 2 | FOL rule confidences | B | individual-review | — |
| 3 | Pipeline selection parameters | B | batched-summary | #4 |
| 4 | Task-to-task-type mapping confidence | B | individual-review | — |
| 5 | Goal verification thresholds | B | individual-review | — |
| 6 | Class generalization materialization policy | A | auto-apply | — |
| 7 | Per-hierarchy class-generalization weights | B | batched-summary | — |
| 8 | sense-correlations (Track A) | A | auto-apply | — |
| 9 | Priority-scorer / attention_score | B | batched-summary | — |

Total v1 subsystems: 9. Track A: 2. Track B: 7.

---

*Initial R3 saturated.*

---

## R3 Phase 1 Refactor + Signal Rename + Hint System (2026-05-28)

### Signal rename

`S1`…`S9` → namespace IRIs matching the validator + mechanism naming pattern:

| Old | New IRI | Shorthand |
|---|---|---|
| S1 | `signal.self_distillation` | self-distill-signal |
| S2 | `signal.gold_anchor` | gold-signal |
| S3 | `signal.fol_disagreement` | FOL-disagree-signal |
| S4 | `signal.ensemble_agreement` | ensemble-signal |
| S5 | `signal.hitl` | HITL-signal |
| S6 | `signal.task_outcome` | outcome-signal |
| S7 | (reserved) | — |
| S8 | `signal.replan_divergence` | replan-divergence-signal |
| S9 | `signal.mutation_frequency` | mutation-frequency-signal |

Eliminates Sn vs version vn collision. Matches `validate.*` / `mechanism.*` / `signal.*` capacity family pattern.

### Phase 1 — Refactored 5-step flow

Hint/pattern extraction is now an explicit step before mapping. Makes mapping auditable + learnable.

```
Phase 1 — Task interpretation (5-step)

1. Receive task_input (raw).
2. process_input(raw) → structured_input
     - L3 family `process.*` (admin-authored per domain)
     - Tokenize/parse/normalize.
3. extract_hints(structured_input) → hint_set (global always-on subset)
     - L3 family `hint.*` — global subset runs on every Phase 1.
     - Returns dict[hint_iri, value].
4. derive_goal(structured_input, hint_set) → goal
     - L3 capacity `decision.derive_goal`.
5. map_to_task_pattern(structured_input, hint_set, goal) → (task_pattern, mapping_confidence)
     5a. Identify candidate patterns via shape-index lookup over hints.
     5b. For each candidate: run pattern's declared hints (per Method δ).
     5c. Compute mapping_confidence via mapping subsystem (#4).
     5d. If confidence < threshold OR no candidates → emit dont_know with appropriate DontKnowReason.
     5e. Otherwise return (task_pattern, mapping_confidence).
```

Phase 1 produces: `(structured_input, hint_set, goal, task_pattern, mapping_confidence)` OR `(structured_input, hint_set, dont_know_outcome)`.

Hint set captured on MM as `NodeInstance`s for audit + Phase 6 mapping-blame attribution.

### Method δ — Hybrid hint extraction (the v1 pick)

- **Global always-on hint subset** — runs on every Phase 1 invocation. ~20 baseline hints (modality, length, question-form, language, etc.).
- **Per-pattern hint declarations** — each `task-pattern` entry has `relevant_hints: list[IRI]` field. When Phase 1 evaluates a candidate pattern, it runs the declared hints.

Two-tier catalog. Admin authors hints as L3 `hint.*` capacities; per-pattern declarations select pattern-relevant subset.

Methods α (heuristic only), β (learned single extractor), γ (per-pattern only), ε (LLM-prompted) deferred.

### New ALS subsystem #10 — Hint extraction calibration

| # | Subsystem | Track | Audit | applies_after |
|---|---|---|---|---|
| 10 | Hint extraction calibration | B | batched-summary | — |

Mapping subsystem #4 `applies_after: {#10}` — mapping calibration depends on hint extraction calibration.

v1 ALS subsystem count: **10** (was 9 after R3 pipeline-confidence removal; +1 hint extraction = 10).

### L3 family additions

- `process.*` — domain-specific input processing (text, code, business-doc, multimodal-future). Step 2.
- `hint.*` — hint extractors. Step 3 + step 5b. 20+ baseline + N domain-specific.
- `decision.derive_goal` — goal-derivation capacity. Step 4.

All operate `inline=True` (sub-millisecond, CPU-bound, no I/O). Performance budget: Phase 1 < 50ms total.

### Vocabulary clarification

Four overlapping terms — different concepts:

| Term | Concept | Layer |
|---|---|---|
| **hint** | Phase 1 extracted input feature for task classification | L3 `hint.*` outputs |
| **signal** | ALS training event from L3 signal-source capacity | L3 `signal.*` outputs |
| **evidence** | Row staged in `parameter-staging` for ALS aggregate | L2 row |
| **feature** | (ML jargon, avoid in MindsOS docs) | — |

Use "hint" for Phase 1 input classification features. Use "signal" for ALS training events. Use "evidence" for staged rows. Avoid "feature" in MindsOS context.

---

## R3 final reanalysis (post-hint-system)

### PB-R3-23 — D51 scope refinement

D51 was capacity-pipeline-pattern pairing. Hint extractors aren't paired with pipelines. They're auxiliary. Need refined invariant:

**Pick: every L3 capacity must be REACHABLE from at least one entry point.** Entry points are:
- Pipelines (transform DataStates).
- Task-pattern declarations (hints + sufficient_predicate + relevant capacities).
- L4 direct invocations (substrate uses — `scoring.attention_score`, `decision.signal_to_tier`, etc.).
- Predicate-referenced action contracts (`precondition_iri` + `effect_iri`).
- ALS subsystem registrations (`signal_sources`, `update_mechanisms`, `validation_methods`).

L4 startup invariant: walk all L3 capacities; verify each is referenced by at least one entry point. Warn on orphans; block on startup if `--strict-reachability` flag set.

D51 generalized: **"L3 reachability invariant"** — covers pipelines + patterns + substrate + ALS.

### PB-R3-24 — `process.dispatch` unknown-domain case

Phase 1 step 2: input doesn't match any known domain processor → cannot proceed to step 3.

**Pick: New early-exit at Phase 1 step 2.** Returns `dont_know` with `DontKnowReason.NO_MATCHING_PATTERN` (collapsed under same reason — admin sees "system doesn't know how to handle this input type"). Alternative: new DontKnowReason `UNKNOWN_INPUT_DOMAIN` for clearer admin diagnosis.

**Decision:** `NO_MATCHING_PATTERN` collapses both "no task-pattern matched" and "no input processor matched." Admin tooling differentiates via audit log (which capacity returned which result). Avoids enum bloat.

### PB-R3-25 — Hint capacity inline=True discipline

Hints run on hot Phase 1 path. Performance budget tight.

**Pick: hint extractors MUST be `inline=True`** at registration. Declared latency budget ≤5ms each. No I/O. No long write locks on MM. Registration tooling enforces.

Cascade: `hint.*` family registration contract gains mandatory `inline=True` + `max_latency_ms ≤ 5`.

### PB-R3-26 — Hint extraction failure handling

Hint capacity fails (input malformed, etc.) → what?

**A. Graceful nulling** — hint returns null/None; mapping treats absence as missing-evidence.
  - Pros: Robust; partial information used; no cascade failure.
  - Cons: Silent failure may hide bugs.

**B. Exception → Phase 1 fails → dont_know.**
  - Pros: Loud failure; surfaces bugs.
  - Cons: Single hint failure crashes Phase 1; brittle.

**C. Graceful nulling + log error.**
  - Pros: A's robustness + B's debuggability.
  - Cons: None significant.

**Pick: C.** Graceful nulling + audit-log error. Phase 1 continues with absent hint; debugging surface via audit log.

### PB-R3-27 — Goal derivation single-pass vs per-candidate-refinement

Step 4 derives goal using global hints. Pattern-specific hints (step 5b) may reveal goal nuance.

**A. Single-pass** — derive once with global hints; mapping uses goal + all hints.
**B. Multi-pass** — rough goal first; refine per candidate with pattern-specific hints.

**Pick: A v1; B v2 if needed.** Single-pass keeps Phase 1 simpler. Pattern-specific goal refinement can happen in Phase 2 (pipeline determination) — pipeline-finder operates on the selected pattern + its declared hints. v2 may add explicit goal-refinement pass.

### PB-R3-28 — Vocabulary commit

Documented above (hint / signal / evidence / feature). Capture in baseline glossary. WSD installation chat references.

### PB-R3-29 — Hint catalog growth

20–100 hint capacities is admin-authoring burden. UC-WSD-1 success criterion 100ms total Phase 1 runtime requires hint extraction < 50ms. With 30 global hints × 1ms each = 30ms; budget tight but feasible.

Mitigation: shipped baseline v1 hint catalog covers common cases (~20 hints); admin extends per installation; perf testing at WSD installation time.

### PB-R3-30 — Hint extraction in MM schema

Hints written to MM as `NodeInstance`s. Each hint node has:
- `hint_iri`: which hint capacity produced it.
- `value`: the hint's value (bool, scalar, list, etc.).
- `extracted_at`: timestamp.
- `confidence`: extractor-reported confidence (if learned per #10).

MM schema for hint nodes: implementation-level. Captured for L1/L5 reframe chat.

---

## R3 consolidated outputs (final)

### v1 ALS subsystem list (10 total)

| # | Subsystem | Track | Audit Policy | applies_after |
|---|---|---|---|---|
| 1 | WSD candidate-scorer | B | individual-review | — |
| 2 | FOL rule confidences | B | individual-review | — |
| 3 | Pipeline selection parameters | B | batched-summary | #4 |
| 4 | Task-to-task-type mapping confidence | B | individual-review | #10 |
| 5 | Goal verification thresholds | B | individual-review | — |
| 6 | Class generalization materialization policy | A | auto-apply | — |
| 7 | Per-hierarchy class-generalization weights | B | batched-summary | — |
| 8 | sense-correlations | A | auto-apply | — |
| 9 | Priority-scorer / attention_score | B | batched-summary | — |
| 10 | Hint extraction calibration | B | batched-summary | — |

Track A: 2. Track B: 8.

### Cascade items (full consolidated list)

- **L0-13**: capacity-gaps admin tooling polished for v1.
- **L0-14**: HITL clarification channel + interactive-mode detection.
- **L0-15**: audit event constants (EVT_PIPELINE_QUARANTINED, EVT_PIPELINE_DELETED, EVT_TASK_PATTERN_AUTHORED, EVT_HINT_EXTRACTOR_FAILED, etc.).
- **L0-16**: hint catalog admin tooling (similar to capacity-gaps surface).
- **L2-23**: `parameter-staging` + `pending-promotions` schemas.
- **L2-24**: bootstrap-importer suite checklist.
- **L2-25**: `promoted-pipelines` schema v2 (5-state status + paired_pipelines + serves_task_types).
- **L2-26**: `task-patterns` schema gains `relevant_hints: list[IRI]` field.
- **L3-37**: ALS L3 family (aggregate + mechanism + validator).
- **L3-38**: `pattern.extract_task_shape` (Method 4 enabler).
- **L3-39**: `decision.classify_dont_know_reason` (4-way + ambiguity).
- **L3-40**: shape-indexing for fast Phase 1 pattern matching.
- **L3-41**: S6/`signal.task_outcome` enriched payload schema.
- **L3-42**: `hint.*` family (20+ baseline + N domain-specific; all `inline=True`).
- **L3-43**: `process.*` family (domain-specific input processing).
- **L3-44**: `decision.derive_goal` capacity.
- **L4-10**: pattern-conflict admin alert.
- **L4-11**: TaskOutcome schema with 3-valued decision + DontKnowReason.
- **L4-12**: per-task-pattern mapping-confidence threshold.
- **L4-13**: multi-pattern conflict policy.
- **L4-14**: ALS subsystem `applies_after` field + topological apply.
- **L4-15**: Phase 1 refactored 5-step control flow spec.
- **L4-16**: ALS subsystem #10 registration.

### Architectural commitments locked

- **L4-vs-L3 strict line:** L4 = substrate + control flow only.
- **9-IRI signal catalog** + S7 reserved.
- **10-subsystem ALS** with topological apply ordering.
- **Phase 1 5-step refactor** with explicit hint extraction.
- **3-valued TaskOutcome** + 4-category DontKnowReason.
- **Pipelines binary deterministic**; failure → quarantine → admin review.
- **System-trust contract** ("honest don't-know + calibrated confidence").
- **L3 reachability invariant** (D51 generalized).
- **Bootstrap importer pattern** for Global v0 + Local KL fall-through.
- **D32.5c attention_score** + R1 strict-line via ALS subsystem #9.

### Vocabulary glossary (R3-locked)

- **MM** = Mental Model (L5 working memory; per-task instance graph).
- **hint** = Phase 1 input-classification feature (`hint.*`).
- **signal** = ALS training event (`signal.*`).
- **evidence** = staged ALS row in `parameter-staging`.
- **task-pattern** = entry in L2 `task-patterns` role-graph.
- **mapping** = task → task-pattern classification (subsystem #4).
- **attention_score** = L4-mutable integer per-task priority within tier (R1 D32.5c).

---

*R3 fully saturated.*

---

## R3 final reanalysis (third pass) — substantive picks

### PB-R3-31 — Pipeline status transition authority

**Pick: B — System-triggered quarantine; admin-triggered everything else.**

- `draft → tested`: admin (after running tests).
- `tested → active`: admin (promotion).
- `active → quarantined`: **system** (on failure detection at high mapping confidence).
- `quarantined → active`: admin (reinstate).
- `quarantined → retired`: admin (delete).

Quarantine trigger: pipeline failed AND mapping_confidence at task arrival > pipeline's quarantine_threshold (per-pipeline admin-tunable, default 0.85).

### PB-R3-32 — DontKnowReason routing destination

**Pick: A — Static routing per reason + per-task-pattern optional override.**

| Reason | Destination |
|---|---|
| NO_MATCHING_PATTERN | capacity-gaps queue |
| LOW_MAPPING_CONFIDENCE | HITL if interactive, else capacity-gaps |
| PIPELINE_UNAVAILABLE | capacity-gaps queue |
| UNRESOLVED_AMBIGUITY | HITL if interactive, else capacity-gaps |

"Interactive" = consumer/session declares `interactive=True` at session start. L0 user_settings carries default.

v1 ships defaults; per-task-pattern routing override field optional (v1.5).

### PB-R3-33 — Default Global cycle schedule

**Pick: B — Default schedule + admin override.**

Ship default cadence = weekly off-hours. Admin can change cadence, disable, or manually trigger.

Cascade: **L0 scheduler infrastructure becomes v1 must-have** (was v2-future). Reclassified.

---

*R3 fully saturated 2026-05-28 — 33+ sub-decisions, 26+ cascade items, 10 ALS subsystems. Zero reversals across 7 reanalysis passes.*

---

## R4 — WSD Architecture + 9 Pending L4 ADRs

**Round:** R4
**Status:** Ratified 2026-05-28. Most picks are confirmations or applications of R1-R3 strict-line + ALS + pipeline-binary architecture.

### D10 — MSUR pipeline v1

**Pick: ship as L3 orchestration capacity** (per R1).

Internal composition per WSD §5.2: `als.signal_partition` → independent/reinforcing/contradictory → `combination.bayesian` for reinforcing → branch contradictory → `evaluator.*` per thread → `comparator.max` → emit hypothesised_emissions → return resolved_signal.

### D11 — SCMS BSP turn pipeline v1

**Pick: ship as L3 orchestration capacity** (WSD §A.6 + R1 confirmation).

Internal 4-phase BSP turn per WSD §6.2 + quiescence check.

### D12 — Six-phase task lifecycle

**Pick: B — Six-phase + simplified execution mode for admin testing.**

Production = six-phase. Simplified = `mindsos capacity invoke --bypass-lifecycle` for dev/test. Simplified bypasses goal verification + consolidation + ALS signal emission.

### D13 — Phase 6 failure diagnosis v1

**Pick: A — Full Phase 6 v1.**

Cross-validation by sub-path substitution; admin-tunable `phase6_cross_validation_budget` (default K=2, validates top-K-blame segments only).

Required by UC-WSD-6, UC-WSD-9, UC-WSD-14, UC-WSD-15.

### D14 — Replan-check dual-role + record schema

**Pick: adopt WSD §8.3 schema + R2 verdict integration.**

```python
@dataclass
class ReplanRecord:
    pre_state: ...
    expected_post_state: ...
    actual_post_state: ...
    divergence_magnitude: float
    divergence_threshold_at_decision_time: float
    verdict: ReplanVerdict  # R2: decision + verified + divergence
    affected_capacity_iris: list[IRI]
    triggering_step_iri: IRI
```

Sparse recording: only on actual replan events (continue verdicts don't generate records).

### D15 — `signal.replan_divergence`

Already renamed in R3. Registered as v1 signal source.

### D16 — `capacity-gaps` admin queue v1

**Pick: full v1.** Under R3 open task-type space, primary admin surface.

L4 writes from Phase 1 (NO_MATCHING_PATTERN, PIPELINE_UNAVAILABLE), Phase 2 (check_path_exists), Phase 3 (detect_mid_execution_gap), Phase 6 (classifier).

Schema includes occurrence_count + frequency for prioritization.

### D17 — Promotion-rule auto-selection (WSD §A.1)

**Pick: all 6 promotion-rule capacities v1 + L4 default heuristic + admin override.**

L3 ships: `promotion_rule.single_metric_threshold`, `.pareto_frontier`, `.composite`, `.statistical_significance`, `.shadow_deployment`, `.admin_discretionary`.

L4 default heuristic per WSD §A.1. Per-case admin override via minimal UI; override logged with rationale.

### D18 — Dream priority schema (WSD §A.2)

**Pick: adopt v1 as config-level (not L2 role-graph).**

Typed structured object: `kind ∈ {goal | metric | path-variant | cycle-weight}` + `target` + `priority_value` + `owner` + `expires_at`. Per-session + admin-set Global defaults. Audit-log tracks priority changes. UX is L0.

### D19 — Per-level independent dream scheduling (WSD §A.3)

**Pick: defer concrete spec to L2 chat.**

Direction confirmed: dream improvements don't auto-propagate across composition levels. Concrete schema depends on value-typed paths-of-paths decision in L2 chat.

### D20 — Data-gap vs capacity-gap classifier (WSD §A.4)

**Pick: retired — absorbed into R3 `decision.classify_dont_know_reason` (4-way + ambiguity).**

### D21 — Phase 6 path-segment blame (WSD §A.5)

**Pick: full v1.** Per-segment provenance on MM (per R3); blame heuristic `(1 - confidence) × (1 + divergence)`; cross-validation by sub-path substitution per L3-23.

Under R3 binary pipelines: failure at high mapping confidence → localize to capacity → ALS retrains capacity parameters → if retraining doesn't fix, pipeline quarantined.

### D22 — SCMS as L3 orchestration (WSD §A.6)

**Already done in R1.**

### D23 — Migration phase orchestration (WSD §A.7)

**Pick: B — Basic version pinning v1; full coexistence orchestration v2.**

Use existing `kl.activate_version` mechanism for v1. Full rollout policies + aggregate metrics + phase-transition proposals defer to v2 when first DS migration scenario surfaces.

No UC requires full migration orchestration.

### D24 — Six-phase retained (WSD §A.8)

Same as D12. Confirmed.

### D25 — ALS full pipeline orchestration (WSD §A.9)

Covered by R3 D9.6 + D9.1 + D9.7. Confirmed.

### Pushbacks against R4 picks

**PB-R4-1.** D13/D21 cross-validation doubles compute per failure. Admin-tunable budget. Acceptable.

**PB-R4-2.** D12 two paths (six-phase + simplified) is maintenance burden. Documentation discipline.

**PB-R4-3.** D17 6 promotion-rule capacities — each is ~50-100 LOC bounded scoring function. Could subset (A, B, F) v1 if scope pressure; ship all 6 default.

**PB-R4-4.** D18 config-level priority schema doesn't get KL versioning. Audit-log substitutes.

**PB-R4-5.** D23 basic version pinning may surface as gap in WSD installation. Acceptable risk.

**PB-R4-6.** D14 ReplanRecord verbose; sparse recording only on actual replans.

**PB-R4-7.** D16 capacity-gaps high admin load under R3 open task-type space. Frequency-based prioritization.

### Cascade items added in R4

- L3-45 (NEW): 6 promotion-rule L3 capacities.
- L0-17 (NEW): capacity-gaps admin queue UI/API (occurrence counting, prioritization, mark out-of-scope).
- L0-18 (NEW): simplified-execution-mode CLI flag (`--bypass-lifecycle`).
- L4-17 (NEW): Phase 6 cross-validation budget parameter.
- L4-18 (NEW): dream priority schema (config-level, audit-tracked).

---

*Initial R4 complete.*

---

## R4 reanalysis — PB-R4-8 + cascades (2026-05-28)

### PB-R4-8 — Promotion-rule selection should be L3, not hardcoded L4

D17 had "L4 default heuristic." Under R1 strict-line, selection is a decision → L3.

**Revised pick: B — new L3 capacity `decision.select_promotion_rule(context) -> rule_iri`.** Internal logic = WSD §A.1 heuristic. Admin override via standard capacity-override flow (UC-WSD-13 pattern). v2 may add ALS subsystem for learnable selection parameters.

Cascade: L3-46 (NEW) — `decision.select_promotion_rule` capacity.

### Clarifications (no architectural picks)

- **PB-R4-9.** Phase 6: sync v1 (Phase 4 returns false during execution); async deferred v2. L4-19 added.
- **PB-R4-10.** SCMS Monitor declaration schema includes `method_iris: dict[Literal["evaluator", "combination", "comparator"], IRI]`. Captured for L1/L3 reframe chat.
- **PB-R4-11.** ReplanRecord generated only on `replan` or `abort` verdicts; `continue` (any verified state) doesn't record.
- **PB-R4-12.** Phase 6 blame heuristic coefficients hardcoded v1; ALS subsystem v2 candidate. L4-20 added.
- **PB-R4-13.** capacity-gaps privacy (PII in stored inputs) — anonymization v2; L0 chat owns.
- **PB-R4-14.** Dream priorities: per-user → L0 user_settings; admin defaults → L0 admin config. L0-19 added.
- **PB-R4-15.** MSUR ledger persistence beyond task completion deferred v2 (already in WSD §5.4).

### Cascade items added

- **L3-46**: `decision.select_promotion_rule` capacity.
- **L4-19**: async Phase 6 v2 watch item.
- **L4-20**: Phase 6 blame ALS subsystem v2 candidate.
- **L0-19**: admin config field for Global dream priorities.

---

*R4 saturated 2026-05-28. 16 items resolved, 9 cascade items added, 1 architectural placement correction (PB-R4-8). Zero reversals.*

---

## R5 — FOL pushbacks + UC-surfaced + cross-realm

**Round:** R5
**Status:** Ratified 2026-05-28. Many items pre-resolved by R1-R4 settling; R5 picks the few that remain.

### D26 — FOL #1 live training (reinstate vs dreaming-only)

FOL: reinstate live + dreaming with provenance-tagged signals; live writes accumulate in L5, migrate after corroborating dream pass.

WSD's ALS already supports "live + dream" via different pattern: live signals → L2 `parameter-staging` (Local) during execution → dream-aggregate processes → admin audit → apply to `learned-parameters`.

**Pick: ACCEPT WSD pattern (already R3 D9.4). FOL #1 satisfied semantically.**

Note: FOL prefers L5→L2 migration (write to MM first, promote to L2 after dream). WSD writes to L2 directly during execution (Local staging). Same effect; different path. Watch item for FOL chat — if FOL has specific reason for L5-first path (e.g., neural model gradients accumulating in MM), revisit.

Cascade: L4-21 (NEW) — FOL #1 L5-first watch item for FOL chat.

### D27 — FOL #2 plural strategies

Already Q5 resolved: ALS adopted; FOL plural-strategies deferred to FOL chat. R5 confirms.

### D28 — FOL #4 `learned-parameters` split into 3

FOL: split into `learned-scalars` / `learned-policies` / `learned-models` for storage profile mismatch (12-byte scalar vs 100MB neural checkpoint).

WSD's 10 v1 subsystems write scalar/probabilistic parameters. Neural model artifacts emerge with FOL plural strategies (Q5 deferred).

**Pick: A — single `learned-parameters` role-graph v1. FOL #4 split deferred to FOL chat.** `parameter_set_iri` is opaque IRI; forward-compatible if FOL chat accepts split.

### D29 — FOL #5 `training-runs` role-graph

FOL: separate role-graph for checkpointed multi-task training runs.

Necessary for neural model training (hours-to-days). Not needed for scalar/probabilistic ALS updates (single dream cycle).

**Pick: DEFER to FOL chat.** v1 doesn't ship `training-runs`. ALS dream-cycle handles short training runs (per ADR-0091 dream-as-task).

### D30 — FOL #8 model-artifact blob store

FOL: external blob store + IRI manifest pattern (S3/MinIO + content-addressed hashes).

Neural model artifacts → FOL chat territory.

**Pick: DEFER to FOL chat.** No blob store ships v1. L0-8 reclassified: FOL chat picks design when needed.

### D31 — FOL #9 typed CapacityContext

FOL: define typed CapacityContext schema with named accessors per capacity family.

**A. Adopt typed v1.**
  - Pros: Clean contracts; matches engineering discipline.
  - Cons: ~100 LOC schema; per-family extensions.

**B. Stay untyped v1.**
  - Pros: Lower v1 scope.
  - Cons: Loose contracts; harder debugging.

**C. Per-family extension** — base `CapacityContext` with common fields; each capacity family extends.
  - Pros: Type safety + extensibility; matches WSD's family-based catalog.
  - Cons: More schema upfront.

**My pick: C.** Base `CapacityContext` has `session_id`, `user_id`, `learned_parameters_snapshot`, `mm_handle`, `cancel_token`, etc. Each L3 capacity family extends as needed (`WSDCapacityContext`, `SCMSCapacityContext`, etc.).

Cascade: L3-47 (NEW) — typed CapacityContext base + family extensions.

### D32 — FOL #12 concurrency

Already R1 = single-process multi-threaded. Confirmed.

### D33 — FOL #13 process item

"Coherence Loop scope drift" — Q5 resolved + Chat A IS the L4 design chat. Process item satisfied.

### D34 — sense-correlations + learned-parameters

Already R3 Q4 = ship both. Confirmed.

### D35 — R0-PB-10 single-tenant L4 v1

L4 v1 single-tenant; cross-layer rewrite handler v2.

**Pick: CONFIRM single-tenant v1; L4-v2 follow-up chat ships multi-tenant.** Already captured in L4-1 cascade.

### D39 — Method libraries vocabulary

Per WSD §5.2: 5 method libraries.

**Pick: adopt 5-library catalog v1:**
- `evaluator.*` — thread evaluation methods.
- `combination.*` — signal combination methods (`combination.bayesian`, `combination.max`, etc.).
- `comparator.*` — winner selection methods (`comparator.max`, `comparator.threshold`).
- `metric.*` — metric computation methods (latency, accuracy, ECE).
- `class.ancestors_*` — class hierarchy walks.

Per-method capacities authored by WSD installation chat.

### D40 — Signal sources v1 subset

Already R3 → 9-IRI `signal.*` catalog (8 active + S7 reserved). Confirmed.

### D41 — Sufficient-predicate flexibility (UC-WSD-3)

Sufficient-predicate per task-pattern accepts multi-candidate output as success.

**Pick: ALREADY HANDLED by R3 architecture.** Per-pattern flexibility is automatic — each task-pattern's `sufficient_predicate_iri` field references its own L3 predicate capacity. UC-WSD-3's `pp-attachment-ambiguity-detected` pattern references a predicate accepting multi-candidate output.

Cascade: L3-36 (predicate family) includes "ambiguity-preserved success" + "single-commitment success" + variants.

### D42 — Document-scope SCMS (UC-WSD-2/5)

What is "the document"? Monitor lifecycle scope.

**Pick: A — per-task input.** Document = entire task input (could be multi-sentence). SCMS Monitor lifecycle spans the task; restarts at next task.

WSD §6.3: "L4 owns Monitor lifecycle. Start when text-handling task begins, run until quiescence." Per-task aligns.

Cross-task context (e.g., conversation memory) defers to v2.

Cascade: L4-22 (NEW) — cross-task SCMS context v2.

### D43 — Multi-domain handling (UC-WSD-10)

**Pick: adopt UC-WSD-10 framework v1.**

- `domain_tag` on lexicon edges (L2-19 already captured).
- Per-hierarchy class-generalization weights (ALS subsystem #7 already covers).
- V3 drift alarm via drift-validator on mapping subsystem (#4 already).
- **v1: domain declared per task-pattern by admin.** Automatic domain detection defers v2.

Cascade: L4-23 (NEW) — automatic domain detection v2.

### D44 — Decision-precedent retrieval (UC-WSD-13)

Similarity function over admin decisions; admin-aid, not auto-decision.

**Pick: adopt v1.** New L3 capacity `retrieval.by_admin_decision_similarity(current_context) -> list[prior_decisions]`. Reads from audit log (admin decision rationale field). Returns similar prior decisions for admin review. Never auto-applies.

Cascade: L3-48 (NEW) — decision-precedent retrieval capacity.

### D45 — Per-segment provenance

Already R3 captured (L2-22, L4-15). Confirmed.

### D50 — Cross-realm DataState bridge (UC-X-1)

NLU + code unified.

**A. Single bridge DataState** (`DS_CROSS_REALM_QUERY`).
**B. Adapter capacity** per cross-realm transition.
**C. Per-pattern declared bridge.**

**My pick: B — adapter capacity family.** Each cross-realm task-pattern declares its bridge adapter as a step in the pipeline. UC-X-1's `nl_code_bridge` pattern uses `adapter.question_decompose_to_code_search_spec`. Other cross-realm cases author their own adapters.

Cascade: L3-49 (NEW) — `adapter.*` capacity family.

### Pushbacks against R5 picks

**PB-R5-1.** D26 FOL #1 pattern mismatch (WSD writes L2 during exec; FOL prefers L5→L2). Watch item for FOL chat. If FOL has specific reason (e.g., gradient accumulation in MM), reopen.

**PB-R5-2.** D31 typed CapacityContext per-family complexity. ~5-10 family extensions in v1. Acceptable.

**PB-R5-3.** D43 manual domain declaration v1 — admin must tag every task-pattern with domain. Authoring discipline. v2 automatic detection.

**PB-R5-4.** D50 adapter capacity catalog grows per cross-realm pattern. Per-pattern authoring; n cross-realm pairs = n adapters. Acceptable for n small.

**PB-R5-5.** D28 + D29 + D30 all deferred to FOL chat. FOL chat scope grows. Make explicit when FOL chat opens.

**PB-R5-6.** D34 + D35 + D40 + D45 confirmation-only — no R5 substantive work. Reflects R1-R4 maturity.

### Cascade items added in R5

- **L3-47** (NEW): typed CapacityContext base + family extensions.
- **L3-48** (NEW): decision-precedent retrieval capacity.
- **L3-49** (NEW): `adapter.*` cross-realm bridge family.
- **L4-21** (NEW): FOL #1 L5-first watch item.
- **L4-22** (NEW): cross-task SCMS context v2.
- **L4-23** (NEW): automatic domain detection v2.

### R5 summary

| ID | Item | Pick |
|---|---|---|
| D26 | FOL #1 live training | WSD pattern satisfies semantically; FOL chat watch |
| D27 | FOL #2 plural strategies | Q5 deferred to FOL chat |
| D28 | FOL #4 learned-params split | Single v1; FOL chat for split |
| D29 | FOL #5 training-runs | Defer to FOL chat |
| D30 | FOL #8 blob store | Defer to FOL chat |
| D31 | FOL #9 typed CapacityContext | Adopt v1 with per-family extension |
| D32 | FOL #12 concurrency | R1 confirmed |
| D33 | FOL #13 process item | Satisfied (Q5 + Chat A IS L4 chat) |
| D34 | sense-correlations + learned-params | R3 ship both confirmed |
| D35 | Single-tenant L4 v1 | Confirmed; v2 rewrite handler |
| D39 | Method libraries vocabulary | 5-library catalog v1 |
| D40 | Signal sources v1 subset | R3 9-IRI catalog confirmed |
| D41 | Sufficient-predicate flexibility | R3 architecture handles |
| D42 | Document-scope SCMS | Per-task input v1 |
| D43 | Multi-domain handling | UC-WSD-10 framework v1; manual domain declaration |
| D44 | Decision-precedent retrieval | Adopt v1 L3 capacity |
| D45 | Per-segment provenance | R3 confirmed |
| D50 | Cross-realm DataState bridge | Adapter capacity family v1 |

---

*Initial R5 complete.*

---

## R5 reanalysis — clarifications only (2026-05-28)

Zero substantive architectural picks. 5 clarifications:

- **PB-R5-7.** D31 typed CapacityContext — base has 7 fields (session_id, user_id, learned_parameters_snapshot, mm_handle, cancel_token, current_task_iri, current_pattern_iri); family extensions only add domain-specific fields. Lift-to-base rule: ≥2 unrelated families consume → base.
- **PB-R5-8.** D39 "5 method libraries" is a SUBSET (MSUR/SCMS-internal). Full Chat-A L3 capacity catalog spans ~15-20 families. Make distinction explicit in WSD installation docs.
- **PB-R5-9.** D43 "manual domain declaration" is actually hint-driven (domain hints via `hint.*` + per-pattern domain field + mapping subsystem #4 routing).
- **PB-R5-10.** D44 precedent retrieval reads audit log via L0 query API v1; L2 role-graph promotion deferred v2.
- **PB-R5-11.** D50 `adapter.*` is naming convention for cross-realm transformations, not structurally distinct family — follows standard L3 contract.

### Cascade added in reanalysis

- **L0-20** (NEW): L0 query API on audit log for L3 capacities.

---

*R5 saturated.*

---

## R6 — Routed-to-reframe confirm-only

**Round:** R6
**Status:** Direction-confirmed 2026-05-28. Chat A states preference; L1/L3 reframe chat + L2 chat ratify supersessions and schemas.

### D36 — Monitor lifecycle ownership (→ L1/L3 reframe chat)

**Direction: L4-owned Monitor lifecycle** per WSD §6.3.

Phase 31 supersession required. L3 `start_resident` / `stop_resident` retired (Chat A preference) or repurposed (alternative). L1/L3 reframe chat picks.

### D38 — Capacities-as-hyperedges (→ L1/L3 reframe chat)

**Direction: capacities-as-hyperedges with DataStates as nodes** per WSD architecture.

Phase 27 retired with migration plan for shipped capacities. Major architectural supersession; L1/L3 reframe chat scope substantial.

### D46 — `unhandled_inputs` contract universal (→ L1/L3 reframe chat)

**Direction: every L3 capacity MUST implement `unhandled_inputs` semantics.**

Phase 27–33 audit captured in L3-32. No opt-out per Chat A preference.

### D47 — Path-mutability (→ L2 chat)

**Direction: immutable-with-successor-IDs** (Chat A preference, advisory).

Aligns with R3 pipeline lifecycle (5-state enum); preserves "tested before approval" guarantee; matches ADR-0150 §am-1 versioning. L2 chat may pick differently if storage/query semantics drive otherwise.

### D48 — DataState taxonomy expansion (→ L1/L3 reframe chat)

**Direction: domain-specific DataState catalogs.**

NLU: `DS_FRAME_INSTANCES`, `DS_FOL_ATOMS`, `DS_NLU_FULL_ANNOTATION`.
Code: `DS_CODE_AST`, `DS_CALL_GRAPH`, `DS_INTENT`.
Cross-realm: `DS_PATTERN_FINGERPRINT` + adapter-specific bridges.

L1/L3 reframe chat catalogs + ships v1 baseline; admin extends per installation.

### Pushbacks against R6 confirmations

**PB-R6-1.** L1/L3 reframe chat scope balloons (4 items routed in). Sequencing: WSD installation cannot proceed until L1/L3 reframe completes. Recommend opening L1/L3 reframe chat early; can parallelize with Chat B.

**PB-R6-2.** Phase 27 + Phase 31 supersessions code-touching, not just design. Real engineering cost via L3-32 + L3-1 + L3-2.

**PB-R6-3.** D47 Chat A preference is advisory; L2 chat may override.

**PB-R6-4.** D48 DataState expansion has long tail per realm.

**PB-R6-5.** D46 universal `unhandled_inputs` retroactive Phase 27-33 audit cost captured.

### Cascade items added in R6

- **L4-24** (NEW): coordination — L1/L3 reframe chat is sequencing prereq for WSD installation.

---

## Chat A — CLOSURE

**Status:** Chat A complete 2026-05-28.

**Decisions resolved:** D1–D50 + sub-decisions (D32.x, D9.x, D32.5x, etc.) — ~70 substantive picks across R1-R6.

**Architectural commitments locked:**
- **L4 = substrate + control flow only** (R1 strict line, Push 1 PARTIAL-ACCEPT-4).
- **Single-process multi-threaded** (D32 = B) with always-on signal-triage worker + custom priority-tier Executor + cooperative cancellation.
- **Within-tier score-based attention queue** with L3 `scoring.attention_score` + ALS subsystem #9.
- **10 v1 ALS subsystems** with topological apply ordering + Track A/B split + 3 audit policies.
- **9-IRI signal catalog** (`signal.*` namespace, S7 reserved).
- **Pipelines binary deterministic** with 5-state lifecycle (draft/tested/active/quarantined/retired); quarantine system-triggered, lifecycle admin-owned.
- **Phase 1 5-step refactor** with explicit hint extraction; Method δ (hybrid global + per-pattern hints).
- **3-valued TaskOutcome + 4-category DontKnowReason**; system-trust contract.
- **Six-phase task lifecycle** with simplified mode for testing; full Phase 6 v1 with admin-tunable cross-validation budget.
- **MSUR + SCMS as L3 orchestration capacities**; admin-authored ships v1.
- **L3 reachability invariant** (D51 generalized) enforced at L4 startup.
- **Method libraries vocabulary** (5 WSD §5.2 + adapter family + ~15 other L3 families).
- **Bootstrap importer pattern** for Global v0 + Local KL fall-through; admin tooling supports.
- **Calibration target system-wide + honest don't-know** (D49 + system-trust contract).
- **Typed CapacityContext** (FOL #9) with per-family extension.

**Items routed elsewhere:**
- L1/L3 reframe chat: D36, D38, D46, D48 (architectural reframes).
- L2 chat: D47 (path-mutability), L2-* role-graph schema amendments.
- FOL chat: D27, D28, D29, D30 (plural strategies + neural model infrastructure).
- L4-v2 chat: D35 multi-tenant rewrite handler, L4-1 through L4-23 v2 watch items.
- Chat B (L5 design): note-fork decision + L5 retention model.
- Chat C (plan-authoring): phase-numbering + sentinel-chain + R0 mechanics + bootstrap importer suite checklist.

**Pre-Chat-B handoff:**

Chat B inherits this CHAT_A_DECISIONS.md as the L4 contract for L5 to satisfy. Specifically:
- L4 is sole writer to L5 (settled).
- MM is L4-owned with RWLock per active MM (D32.3).
- Hint set + ReplanRecord + provenance captured on MM during execution.
- ALS subsystems write to L2; do not require L5 changes.
- MSUR ledger lives in MM during execution; consolidated with MM on task completion.

**Pre-WSD-installation handoff:**

WSD installation chat inherits CHAT_A_DECISIONS.md + ratified WSD `coordinated_change_L4` items. Outstanding implementation work:
- L0-* admin tooling (capacity-gaps polished, audit log query API, dream priorities, etc.).
- L2 schema amendments (parameter-staging, pending-promotions, learned-parameters, task-patterns, promoted-pipelines v2).
- L3 capacity catalog authoring (~15-20 families, 50+ individual capacities).
- L4 substrate implementation (~800-1200 LOC).
- 10 ALS subsystem registrations with concrete IRIs + mechanisms + validators + audit policies.
- Bootstrap importer suite shipping Global v0 for all subsystems.

**Document outputs:**
- `_workbench/CHAT_A_L4_BASELINE.md` — Chat A inputs (this is what Chat A read).
- `_workbench/CHAT_A_DECISIONS.md` — Chat A outputs (this document; ~70 picks across 6 rounds).
- `_workbench/CHAT_PLAN_L4_L5.md` — chat sequencing.
- `_workbench/L0-L5_FUTURE_WORK.md` (6 docs) — cascade items routed to per-layer follow-up.

**Settlement-doc production:** This CHAT_A_DECISIONS.md serves as `CHAT_A_SETTLEMENT.md`. Chat B + Chat C inherit directly.

---

*Chat A closed 2026-05-28. Ready for Chat B (L5 + note-fork) or L1/L3 reframe chat (parallelizable with Chat B).*


### D32.7 — CPU-bound L3 escape hatch

**Pick: C — defer subprocess executor to v2 with upgrade-clean contract.**

v1 L4 uses a single `Executor` interface matching `concurrent.futures.Executor`. v2 can swap `ThreadPoolExecutor` for `ProcessPoolExecutor` for `concurrent=process` capacities without changing orchestrator. FOL installation chat triggers the v2 swap.

Acceptable v1 cost: FOL provers run GIL-blocked. UC-WSD-5 (deep FOL feedback) may have latency issues. Documented as known limitation.

Alternatives considered: (A) ignore CPU-bound — leaves FOL/prover users with bad latency; (B) ship `ProcessPoolExecutor` in v1 — IPC serialization overhead + doubled capacity-execution code paths.

### Push 8 resolution (D8 cascade)

Push 8 concern: CRITICAL signals invisible during long L3 calls.

**Resolution:** D32 = B + D32.2 = A structurally solves Push 8. L3 calls run on worker threads; orchestrator never blocks on L3; signal-triage worker observes residents independently. **Not "weakened to next-yield" — structurally always-visible.**

### Open sub-questions for later rounds

- **D32.1 worker pool size** — defer to implementation. Default: `min(8, cpu_count())`. Configurable per-deployment.
- **D32.6 already covered** by D32.2.
- **D32.8 ALS Local cycle threading** — ALS runs on worker? Dedicated background? Synchronous at dream-cycle entry? **Defer to R3 (D9 ALS).**
- **R4 D11 SCMS BSP parallelism** — Monitor invocations parallel within a phase, or serial? UC-WSD-5 implies serial-phase, parallel-monitor. **Defer to R4.**

### Pushbacks against R1 picks (skeptical pass)

**PB-R1-1.** D32.3 reader-writer lock can starve writers under heavy read load. L4 is read-heavy. Mitigation: writer-preferred fairness; implementation-level. Pick holds.

**PB-R1-2.** D32.4 `concurrent` flag introduces two contracts (default-safe + opt-out-unsafe). Coordination point for L1/L3 reframe chat — must respect the flag semantics.

**PB-R1-3.** D32.5 cooperative cancellation depends on capacity authors remembering to wire the token. Mitigation: register-time discipline. UC-WSD-6 admin abort relies on this.

**PB-R1-4.** D32.7 = C means FOL provers GIL-blocked in v1. UC-WSD-5 latency may suffer. Acceptable — FOL installation is downstream — but documented as a v2 upgrade trigger.

**PB-R1-5 (post-reanalysis).** Standard ThreadPoolExecutor is FIFO; would weaken Push 6 four-tier preemption at queue layer. Resolved by adding D32.5b — custom priority-tier Executor.

**PB-R1-6 (user request).** Within-tier ordering and dynamic re-prioritization. Resolved by adding D32.5c — score-based within-tier + tier-change/score-change APIs + auto-preempt-on-elevation. Re-opens Push 6 PARTIAL-ACCEPT-2 (within-tier scoring restored, learnable coefficients still dropped).

### Downstream cascades

- **L1/L3 reframe chat:** Capacity-registration contract gains `concurrent: bool = True` field.
- **L3 future-work:** Phase 27–33 shipped capacity audit for thread-safety — adds new item L3-32.
- **R3 D9 ALS:** ALS execution thread placement is open.
- **R4 D11 SCMS:** Monitor parallelism within BSP phase is open.

---

*R1 complete. Awaiting user sign-off before R2.*
