# Coordinated Change Handoff — L4 Intelligence: ALS, MSUR, SCMS Lifecycle, Six-Phase Task Lifecycle

**Date:** 2026-04-29
**Origin:** WSD subsystem design conversation (Word Sense Disambiguation project, Henrique Alvim).
**Purpose:** Surface L4 Intelligence Layer extensions required by the WSD subsystem architecture. L4 owns the most surface area of any layer in this work.
**Status:** Pre-implementation. Architectural specification only.
**Depends on:** L1, L2, L3 coordinated-change handoffs (this handoff specifies the consumer; those handoffs specify the dependencies).

---

## 0. How to use this document

Upload to the L4 design chat. Self-contained — does not require WSD-design-chat context. The L4 chat should:

1. Read §1 (motivation) and §2 (summary) to orient.
2. Read §3 (resolution of contested L4 decisions) for what's been settled.
3. Read §4–§9 for each new pipeline / mechanism / orchestration component.
4. Read §10 (coordinated implications) for ripple effects.
5. Read §11 (open questions) before designing internals.
6. Read §12 (phasing) for sequencing.
7. Read §13 (what this does NOT change) to bound scope.
8. Reference `WSD_ARCHITECTURE.md` (canonical architecture spec) for the full design context.

L4 owns the most decisions affected by this handoff — orchestration, lifecycle, training, audit, six-phase task execution.

---

## 1. Why this handoff exists

The WSD subsystem design surfaces large L4 changes. Specifically:

  - **Resolution of multiple contested L4 decisions** (per L4 current handoff §4 — Pushes 1-7). The WSD design accepts specific positions on these.
  - **ALS — Audited Learning Subsystem** as the replacement for the coherence loop (Push 3 accepted with substitute mechanism).
  - **MSUR pipeline** — multi-source update resolver, L4-orchestrated composition of L3 capacities.
  - **SCMS BSP turn pipeline** — L4-orchestrated continuous monitoring subsystem.
  - **Six-phase task lifecycle** including new Phase 6 failure diagnosis.
  - **Replan-check dual-role spec** (forward goal-orientation + reflective pipeline-validity).
  - **New ALS signal source S8** (replan-divergence).
  - **Pipeline-finding registered as ALS-trainable subsystem.**
  - **`capacity-gaps` admin queue** integrated into orchestration flow.
  - **Three audit policies** with user-can-override-more-conservative semantics.

---

## 2. Summary of changes

| # | Change | Section | Status in L4 current handoff |
|---|---|---|---|
| 1 | Push 3 accepted: cut coherence loop from v1; ALS substitutes | §3.1 | Was contested |
| 2 | Push 2 accepted: action contracts on L3 (preconditions/effects) | §3.2 | Was contested |
| 3 | Push 5 accepted: defer pause-and-resume to post-v1 | §3.3 | Was contested |
| 4 | Push 6 accepted: drop learnable preemption coefficients | §3.4 | Was contested |
| 5 | Push 1 — meta-pipeline-everywhere — partial (MSUR is L4 pipeline; SCMS turn is L4 pipeline; many decisions hardcoded) | §3.5 | Was contested |
| 6 | Push 7 dropped: predicate distillation deferred (effectively cut) | §3.6 | Was contested |
| 7 | ALS architecture | §4 | New |
| 8 | MSUR pipeline | §5 | New |
| 9 | SCMS BSP turn pipeline | §6 | New |
| 10 | Six-phase task lifecycle | §7 | Refines existing |
| 11 | Phase 6 — failure diagnosis | §7.6 | New |
| 12 | Replan-check dual-role | §8 | Refines Push 2 |
| 13 | New ALS signal source S8 (replan-divergence) | §9 | New |
| 14 | Pipeline-finding as ALS-trainable subsystem | §9.4 | New |
| 15 | `capacity-gaps` admin queue integration | §9.5 | New |
| 16 | Three audit policies | §4.7 | New |
| 17 | Sufficient-predicate evaluation per task-pattern | §7.4 | Refines existing |

---

## 3. Resolution of contested L4 decisions

The L4 current-state handoff (`mindsos_intelligence_handoff_current.md` §4) lists seven contested decisions ("Pushes"). The WSD design conversation has effectively settled five of them and partially settled the other two. Stating the resolutions explicitly:

### 3.1 Push 3 — Coherence dream loop: ACCEPT (cut from v1; ALS substitutes)

The coherence dream loop is **cut from v1** per the Push 3 recommendation. The originally-proposed coherence loop's job (parameter learning for trainable capacities — sense ranker weights, source-trust scores, etc.) is taken over by the **ALS (Audited Learning Subsystem)**, which is a fundamentally different mechanism (multi-source signal aggregation with admin-gated promotion, not GAN-analogous adversarial training).

The originally-proposed coherence loop's other job (pipeline-variant exploration) is handled within ALS + L4's existing pipeline-finding (per §9.4).

Implication: dream intent count drops from 4 to 3 (maintenance, exploration, retry — no coherence intent). The `stability` property in `promoted-pipelines` is unused; remove or repurpose.

### 3.2 Push 2 — Replan-check predicate: ACCEPT (action contracts on L3 capacities)

L3 capacity registrations gain optional `precondition_iri` and `effect_iri` fields per the Push 2 recommendation. Replan-check uses these to validate step expectations against actual state.

This is implemented in the L3 coordinated-change handoff (§10 of that doc) and consumed by L4's replan-check (§8 of this doc).

### 3.3 Push 5 — Pause-and-resume: ACCEPT (defer to post-v1)

Pause-and-resume is **deferred**. v1 ships abort-on-logout. The `stop(mode="pause"|"abort")` signature is settled either way; v1 server only invokes `mode="abort"`.

Removed from v1 scope:

  - `retrieval.paused_plan_runs` capacity.
  - `PlanRunStatus.PAUSED` and `PlanRunStatus.INVALIDATED_ON_RESUME` enum members.
  - Pause-and-resume validation logic.

### 3.4 Push 6 — Four-tier preemption with learnable coefficients: ACCEPT (keep tiers, drop coefficients)

Four priority tiers (CRITICAL > FOREGROUND > BACKGROUND > DREAM) retained. Within-tier preemption uses FIFO + hysteresis lockout (plain code), not learnable `sunk_cost_bonus + interruption_cost` coefficients.

Implication: `capacity:scoring` family does not need `sunk_cost_bonus` or `interruption_cost` capacities.

### 3.5 Push 1 — Meta-pipeline-everywhere: PARTIAL ACCEPT

The recommendation was to collapse from six default meta-pipelines to two (planning + per-run confidence composition). The WSD architecture endorses the principle (most decisions hardcoded; meta-pipelines only where genuinely useful) but defines specific L4 pipelines:

  - **MSUR pipeline** (§5) — L4 pipeline composing L3 capacities; admin-authored, ships v1.
  - **SCMS BSP turn pipeline** (§6) — L4 pipeline; admin-authored, ships v1.

Decisions that remain **hardcoded** in L4 orchestration code (per Push 1 spirit):

  - Attention-score composition.
  - Signal triage.
  - Replan-check predicate dispatch.
  - Promotion-proposer dependency walking.
  - Quiescence detection.
  - Sufficient-predicate evaluation (calls the predicate; doesn't generate it).

Decisions **inside** the registered MSUR / SCMS pipelines are themselves pipeline-composed of L3 capacities (per the L4 design philosophy). So "meta-pipeline-everywhere" is partially true — the SCMS and MSUR are meta-pipelines — but their internals are conventional L4 orchestration logic.

### 3.6 Push 7 / Push 4 — Predicate distillation: ACCEPT (drop)

Predicate distillation is **dropped from v1** (and v2 unless re-justified). LLM-checker capacity may exist as a primitive if needed, but no distillation mechanism, no `predicate-corpus` role-graph, no distillation dream intent.

---

## 4. ALS — Audited Learning Subsystem

### 4.1 Purpose

ALS is the system-wide trainable-parameter learning infrastructure. Replaces the coherence loop. Any subsystem with parameters whose values affect probabilistic decisions registers with ALS.

### 4.2 Subsystem registration contract

Each subsystem registers by declaring:

  - `parameter_set_iri` — which records in `learned-parameters` it owns.
  - `signal_sources: list[(source_iri, weight)]` — which `signal:*` L3 capacities emit evidence for this subsystem.
  - `update_mechanisms: dict[parameter_iri, mechanism_iri]` — per-parameter mapping to the `mechanism.*` L3 capacity.
  - `validation_methods: list[validator_iri]` — V1 (gold accuracy), V2 (calibration ECE/Brier), V3 (drift). Per-validator config (gold-set IRI, drift threshold).
  - `audit_policy: str` — `auto-apply | batched-summary | individual-review`.
  - `eligible_audit_scopes: frozenset[str]` — subset of `{local, global}`.

### 4.3 v1 registered subsystems

  - **WSD candidate-scorer** — parameter set: WSD scorer weights and priors. Signal sources: S1, S2, S3, S4. Mechanisms: bayesian_update + ema + beta_posterior. Validators: V1 + V2 + V3. Audit: individual-review (high-risk).
  - **FOL rule confidences** — parameter set: synthetic-rule confidence scalars and assumption-resolution thresholds. Signal sources: S2, S3, S6. Mechanisms: beta_posterior + ema. Validators: V1 + V2. Audit: individual-review.
  - **`promoted-pipelines` confidence updates** — parameter set: per-(pipeline, task_type) confidence values. Signal sources: S6, S8. Mechanisms: beta_posterior. Validators: V1. Audit: batched-summary.
  - **Pipeline-finding parameters** — exploration policy (ε for ε-greedy), strategy preferences. Signal sources: S6, S8. Mechanisms: ema + beta_posterior. Validators: V1. Audit: batched-summary.
  - **Task-shape recognition priors** — Phase 1 of lifecycle. Signal sources: S2, S5, S6. Mechanisms: beta_posterior. Validators: V1. Audit: individual-review.
  - **Goal verification thresholds** — Phase 4. Signal sources: S2, S5, S6. Mechanisms: ema. Validators: V1 + V2. Audit: individual-review.
  - **Class generalization materialization policy** — per WSD architecture §5.5 Mechanism 4. Signal sources: S6 (query-pattern utility). Mechanisms: ema. Validators: V1. Audit: auto-apply (low-risk).
  - **Per-hierarchy class-generalization weights** — per WSD architecture §5.5 Mechanism 5. Signal sources: S6. Mechanisms: ema. Validators: V1. Audit: batched-summary.
  - **`sense-correlations` (lexicon empirical layer) — Track A** — auto-applied; signal sources: S6 (task-success-filtered); mechanisms: bayesian_update + ema; validators: statistical sanity only.

### 4.4 Two-track training model

**Track A — Low-risk.** Lexicon empirical layer (`sense-correlations` per WSD architecture §5.6 — auto-applied; admin sees aggregate stats only).

**Track B — High-risk.** Scorer parameters. Goes through full ALS pipeline:

  1. **Live-stage** — evidence rows written to `parameter-staging` (Local L2) as tasks complete.
  2. **Dream-aggregate** — maintenance dream pulls from staging, runs S4 ensemble-agreement filter, computes per-parameter losses, runs `mechanism.*` updates.
  3. **Validate** — V1 / V2 / V3 checks against gold subset.
  4. **Audit-queue** — proposed updates written to `pending-promotions` (Local).
  5. **Apply** — admin approves → versioned write to `learned-parameters`.

### 4.5 Local → Global promotion

Periodically (admin-triggered, not automatic), Global cycle aggregates approved Local updates across users:

  1. Read approved Local updates across all users.
  2. Compute consensus / ensemble update.
  3. Validate (same V1/V2/V3).
  4. Write to Global `pending-promotions`.
  5. Admin reviews and approves → versioned write to Global `learned-parameters`.

### 4.6 User-as-Local-admin

At Local scope, the user is the admin. Audit UI must be accessible to end users for Local approvals. At Global scope, system admin approves.

L4 reads per-user training preferences from L0's `user_settings` table at start of every dream cycle. Disabled subsystems get no signal collection from this user; high-priority subsystems get larger evidence batches.

### 4.7 Three audit policies

  - **`auto-apply`** — no admin review. Validation passes → write directly. v1 default for Track A. Used for low-risk parameter classes where wrong updates degrade gracefully.
  - **`batched-summary`** — admin sees aggregate diff per dream cycle, approves whole batch. Reasonable v1 default for medium-risk parameters where individual review is excessive.
  - **`individual-review`** — admin reviews each proposed update separately. v1 default for high-risk parameters affecting many users.

User can override the declared policy to **more-conservative** (e.g., subsystem says `batched-summary`; user wants `individual-review`). Cannot override to less-conservative.

### 4.8 Storage

  - **`parameter-staging`** (Local L2 role-graph; new per L2 handoff §6.1) — live evidence accumulation.
  - **`pending-promotions`** (Local + Global L2 role-graphs; new per L2 handoff §6.2) — audit queue.
  - **`learned-parameters`** (existing L2 role-graph; updated via `ParameterSnapshot` `SUPERSEDES` machinery for rollback per L2 §12 / FOL #4 — single role-graph in v1; possible split deferred).

---

## 5. MSUR pipeline — Multi-Source Update Resolver

### 5.1 Purpose

L4 pipeline that resolves multiple incoming signals into a single update, with branching for contradictions. Used by every refinement Monitor in the SCMS that has multiple signal sources (currently `wsd-update`; potentially `frame-match`, `retrieval`, `cross-word` when designed).

### 5.2 Pipeline composition (admin-authored, ships v1)

Inputs: `(current_state, pending_signals, evaluator_method_iri, combination_method_iri, comparator_method_iri)`. Outputs: `(resolved_signal, hypothesised_emissions)`.

Steps:

  1. **`signal_partition`** (L3 capacity from L3 handoff §4) → `(independent, reinforcing_groups, contradictory_groups)`.
  2. **Apply independent signals** (hardcoded in MSUR pipeline) → `base_state`.
  3. **Apply reinforcing groups via `combination_method_iri`** (L3 method library) → updated `base_state`.
  4. **Branch contradictory groups** (hardcoded) → `list[thread_state]`.
  5. **For each thread, invoke `evaluator_method_iri`** (L3 method library) → score per thread.
  6. **Apply `comparator_method_iri`** (L3 method library) → `(winning_thread, losing_threads)`.
  7. **Emit hypothesised_emissions** for losing threads' distinguishing assumptions (hardcoded; targets MSUR ledger).
  8. **Return resolved_signal** representing winning thread's update intent.

### 5.3 No branch budget in v1

Per WSD design conversation: contradictory branches don't grow exponentially in practice because FOL's discrete state-change criterion damps small WSD changes. No explicit branch budget. Threads that lose simply have their distinguishing assumptions tagged `hypothesised` and may re-enter via FOL's ledger if later evidence elevates them.

### 5.4 MSUR ledger

Per-task, lives in L5 MM during execution. Holds assumption threads with epistemic tags (`assumed | hypothesised | retracted` etc.). Separate from FOL ledger.

Persistence beyond task completion is v2.

### 5.5 Read patterns

MSUR pipeline reads:

  - L3 capacities (signal_partition + selected method-library capacities).
  - L2 lexicon empirical layer (when reinforcing/branching computations need correlation evidence).
  - L5 MM (current state).

MSUR pipeline writes:

  - L5 MM (MSUR ledger).
  - Returns resolved_signal to caller (Monitor's update_state).

---

## 6. SCMS BSP turn pipeline

### 6.1 Purpose

L4 pipeline that drives the continuous Sense Confidence Monitoring Subsystem. Runs whenever a text-handling task is in flight.

### 6.2 Pipeline composition

Inputs: `(active_monitors, current_mm)`. Outputs: turn outcome (broadcasts emitted, state changes applied, quiescence flag).

Steps per turn:

  - **Phase 1 — RESOLVE.** For each active Monitor with pending signals:
    - L4 reads Monitor's declaration (state_datastate_iri, update_state_iri, evaluator/combination/comparator method IRIs).
    - L4 invokes MSUR pipeline (§5) with Monitor's current state, pending signals, and method IRIs.
    - MSUR returns `(resolved_signal, hypothesised_emissions)`.
  - **Phase 2 — APPLY.** For each Monitor:
    - L4 invokes Monitor's `update_state` capacity with `(current_state, resolved_signal)` → `new_state`.
    - L4 writes `new_state` to MM.
  - **Phase 3 — BROADCAST.** For each Monitor whose state changed:
    - L4 routes new state to subscribers (per Monitor's `emits_to` declaration).
  - **Phase 4 — RECEIVE.** Each subscribed Monitor queues incoming signals for next turn.
  - **Quiescence check.** If zero broadcasts in this turn, set quiescence flag.

### 6.3 SCMS lifecycle

L4 owns Monitor lifecycle:

  - **Start** — when a text-handling task begins, L4 reads the task-pattern's required-capacities list, instantiates the relevant SCMS Monitors, runs `wsd-init` and `fol-init`, initializes Monitor state.
  - **Run** — L4 invokes SCMS BSP turn pipeline repeatedly until quiescence detected OR L4's task-end signal fires (sufficient-predicate evaluates true OR task aborts).
  - **Stop** — L4 either consolidates (success) or aborts (failure / external abort). MM consolidation per existing L4-L5 contract.

### 6.4 Convergence and re-engagement

  - **Pair-wise quiescence** detected as a turn with zero Phase-3 broadcasts.
  - **System-wide quiescence** when all Monitors' pair-wise conversations are silent.
  - L4 detects quiescence as a *signal*, not an instruction to halt — the SCMS itself doesn't decide to stop.

After quiescence, L4 evaluates the **sufficient-predicate** (per the active task-pattern, per L2 `task-patterns` schema). If insufficient:

  - L4 adds information to MM (invoke retrieval, request HITL, run alternative refiners).
  - SCMS re-engages from the updated state.
  - Loop continues until sufficient OR task aborts.

### 6.5 No SCMS compute budget

L4's task-lifecycle (timeouts, admin abort, session expiry) handles runaway. SCMS itself has no internal budget.

---

## 7. Six-phase task lifecycle

### 7.1 Phase 0 — Arrival

  - `task_input` (input DataState).
  - `session_context` (read from L0 — capabilities + user_settings).

### 7.2 Phase 1 — Task interpretation

L4 invokes:

  - `recognize_task_shape(task_input) → (task_shape, confidence)` — match against `L2.task-patterns` admin-authored sub-shape recognizers + emergent patterns.
  - `derive_task_goal(task_shape, task_input) → (task_goal, confidence)` — derive end state.

Both probabilistic; confidence values feed into provenance for later blame attribution (Phase 6).

### 7.3 Phase 2 — Pipeline determination

  - `translate_goal_to_datastates(task_goal) → (target_datastates, confidence)`.
  - `check_path_exists(start_state, target_datastates) → bool` — graph reachability (deterministic).
  - **If no path exists:** write to `capacity-gaps` (Global L2 role-graph; admin queue); return "I don't know" outcome to caller.
  - `lookup_known_pipeline(task_shape, target_datastates) → list[(pipeline, match_confidence)]` — query `promoted-pipelines`.
  - `generate_pipeline(start_state, target_datastates, generation_policy) → (pipeline, confidence)` — invoke L3 path-finding capacities.
  - `select_pipeline(known, generated, exploration_policy) → pipeline` — explore-vs-exploit per learned exploration_policy parameters.
  - `validate_pipeline(pipeline, target_datastates) → (plausible, confidence)` — uses L3 capacity preconditions/effects (per Push 2).

### 7.4 Phase 3 — Pipeline execution

For each step:

  - `execute_step(state, capacity, params) → new_state` — invoke L3 capacity.
  - `replan(current_state, target_datastates, remaining_pipeline) → (next_step, divergence, confidence)` — per §8 dual-role spec.
  - `record_replan(replan_event)` — log to MM's replan history (feeds S8 signal source).
  - `handle_step_failure(failed_step, current_state) → action` — probabilistic; returns retry / alternative / abort.
  - `detect_mid_execution_gap(current_state, remaining)` — if a step's preconditions don't hold given current state, capacity gap discovered mid-run; write to `capacity-gaps`.

SCMS runs continuously inside any text-handling step (per §6).

### 7.5 Phase 4 — Goal verification

  - `check_goal_state_match(current_state, target_datastates) → (matches, confidence)` — structural check.
  - `verify_goal_achievement(current_state, task_goal, replan_history) → (achieved, confidence, achievement_quality)` — beyond structural; considers replan history (high-divergence runs are lower-quality achievements).
  - `external_validation(achievement, task_input, current_state) → external_signal | none` — optional HITL/gold/downstream.

### 7.6 Phase 5 — Outcome processing

  - `consolidate_outcome(...) → outcome_record`.
  - `consolidate_mm_to_memory(...)` — write final MM to `L2.memories` per existing L4-L5 contract.
  - `flag_capacity_gap(...)` — if applicable.
  - `emit_signals_to_als(outcome) → list[signal_event]` — route to ALS staging via S1/S2/S3/S4/S6/S8 signal-source capacities.

### 7.7 Phase 6 — Failure diagnosis

Runs only when failure is detected (Phase 4 returns false, or external signal contradicts after consolidation).

  - `analyze_failure_provenance(outcome_record) → list[(parameter_set, blame_weight)]` — L3 capacity per L3 handoff §8.1; uses inverse-confidence + replan-divergence + hard-failure-isolation heuristic.
  - `cross_validate_failure(task_input, alternative_pipeline) → comparison` — optional; runs alternative pipeline if compute permits.
  - `request_human_diagnostic(failure_summary) → diagnostic_signal | none` — optional HITL.
  - `record_diagnostic_outcome(diagnostic_record)`.
  - `route_to_als(blame_weights) → ALS_update_signals` — emit per-parameter-set signals weighted by blame to ALS staging.

Phase 6 produces blame-weighted signals fed back into ALS, which then proceeds via standard pipeline.

---

## 8. Replan-check dual-role spec

### 8.1 Two roles

Per WSD architecture §6 Phase 3:

  - **Forward role — goal-orientation check.** Given the current state, what's the best next step toward the goal? L4 re-evaluates the remaining pipeline at every step boundary. This is the system *thinking*, not blindly executing.
  - **Reflective role — pipeline-quality validation.** Did the previous step produce what the pipeline expected? Use L3 capacity action contracts (precondition_iri, effect_iri per Push 2) to validate. Discrepancy between expected and actual state is a signal that pipeline-generation was flawed (or upstream interpretation was wrong). Feeds S8 signal source.

### 8.2 Replan-check pipeline (L4-orchestrated)

Steps:

  1. Read previous step's `effect_iri` (from L3 capacity registration).
  2. Evaluate effect predicate against current state. If satisfied → expected post-step state achieved.
  3. Read next step's `precondition_iri`. Evaluate against current state. If satisfied → next step is valid.
  4. Compute divergence = mismatch magnitude between expected and actual (defined per state shape; 0 means perfect match).
  5. If divergence > threshold (`replan_divergence_threshold` parameter, learnable via ALS):
     - Emit S8 signal (replan-divergence) for affected pipeline.
     - Re-generate remaining pipeline (call back to Phase 2 generation).
  6. Otherwise: continue with original remaining pipeline.

### 8.3 Replan record

Each replan event is recorded in MM's replan history:

  - `pre_state` — state before previous step.
  - `expected_post_state` — what pipeline expected.
  - `actual_post_state` — what current state is.
  - `divergence_magnitude`.
  - `divergence_threshold_at_decision_time`.
  - `decision` — continue | regenerate | abort.
  - `affected_capacity_iris`.

This record feeds S8 signal source (per L3 handoff §6).

### 8.4 Action contract failures

If step's `precondition_iri` evaluates false at next-step entry: hard failure, raised as `PreconditionViolation`. L4 invokes Phase 6 (failure diagnosis).

If step's `effect_iri` evaluates false post-execution: soft signal, large divergence, S8 signal emitted, replan triggered.

---

## 9. New L4 mechanisms

### 9.1 New ALS signal source S8 — replan-divergence

Per §8 of this handoff. Pipeline-related ALS subsystems (pipeline-finding parameters, `promoted-pipelines` confidence) subscribe to S8.

### 9.2 Pipeline-finding registered as ALS-trainable subsystem

Per WSD architecture §10 (`promoted-pipelines` updates flow through ALS) and the user's clarification that pipeline exploration is handled within ALS + existing pipeline-finding (not as a separate APES sibling).

Registered subsystem details:

  - **Parameter set:** exploration policy parameters (ε for ε-greedy, UCB confidence bound, etc.), search-algorithm preferences per task-shape, task-pattern-match thresholds.
  - **Signal sources:** S6 (task outcome) + S8 (replan-divergence).
  - **Mechanisms:** ema + beta_posterior.
  - **Audit policy:** batched-summary.
  - **Eligible scopes:** Local + Global.

### 9.3 `capacity-gaps` admin queue integration

Per L2 handoff §6.3, `capacity-gaps` is a Global admin-visible role-graph holding unsolvable task shapes.

L4 writes to `capacity-gaps` in two places:

  - **Phase 2** when `check_path_exists` returns false.
  - **Phase 3** when `detect_mid_execution_gap` fires.

L4 surfaces the queue to admin via standard admin tooling (read-only API + UI). Admin actions on a gap:

  - Teach a new capacity to fill the gap (admin-extends L3).
  - Add an adapter (admin-extends L3).
  - Mark out-of-scope (the system documents that this task class won't be solved).

These actions are L3 / admin-tooling concerns; L4 just surfaces the data.

### 9.4 Three audit policies — L4-orchestrated audit pipeline

Per §4.7. L4 orchestrates the audit phase:

  - **`auto-apply`** — validation passes → L4 directly invokes `audit.apply` capacity → versioned write to `learned-parameters`.
  - **`batched-summary`** — L4 aggregates per dream cycle into one batch entry in `pending-promotions`. Admin sees one diff covering the whole batch; approves whole batch or rejects.
  - **`individual-review`** — L4 writes one entry per proposed update. Admin reviews each.

Admin approval is gated by capability check at appropriate scope (Local: user has CAN_APPROVE_LOCAL; Global: admin has CAN_APPROVE_GLOBAL).

### 9.5 Sufficient-predicate evaluation

Per §6.4 and L2 handoff §6.4 (`task-patterns` schema). L4 reads the `sufficient_predicate` from the active task-pattern and evaluates it after SCMS quiescence:

  - If predicate true → consolidate; move on.
  - If predicate false → add information to MM; re-engage SCMS.

Sufficient-predicate evaluation is **hardcoded L4 logic**, not a meta-pipeline (per Push 1 partial acceptance — only complex decisions get meta-pipelined).

---

## 10. Coordinated implications across other layers

### L0 — Server

  - **`user_settings` table** read by L4 at start of every dream training cycle (per `coordinated_change_L0_user_settings.md`).

### L1 — Core

  - **InterGraphEdge** primitive used internally by L4's class-generalization fusion when traversing cross-system mappings.
  - **Schema layer mechanism** used when L4 reads lexicon graph (queries empirical layer specifically for sense scoring).
  - **`MetagraphSnapshot`** — L4 may use snapshots for failure rollback during Phase 6 cross-validation.

### L2 — Knowledge

  - All new role-graphs (`parameter-staging`, `pending-promotions`, `capacity-gaps`) are written by L4.
  - `learned-parameters` is L4's primary parameter-write target; goes through ALS audit pipeline.
  - `task-patterns` read by L4 during Phase 1.
  - `promoted-pipelines` read by L4 during Phase 2; written via ALS audit.
  - `memories` consolidation per existing L4-L5 contract.

### L3 — Capacity

  - All L4 pipelines (MSUR, SCMS turn) compose L3 capacities listed in `coordinated_change_L3_capacities_and_monitors.md`.
  - L4 reads Monitor declarations from L3 graph.
  - L4 invokes L3 capacities through standard `CapacityLayer.invoke()` API.

### L5 — Mental Model

  - MM holds replan history (per §8.3) and MSUR ledger (per §5.4) during task execution.
  - Consolidation pattern unchanged.

---

## 11. Open questions for L4 chat

  1. **Coordinator / scheduler shape for SCMS BSP turns.** Per WSD architecture, BSP is synchronous — slowest Monitor paces the turn. Implementation: single-threaded loop iterating Monitors per phase, or multi-threaded with synchronization barriers? Single-threaded is simpler and probably sufficient.

  2. **MSUR pipeline as graph-promoted-pipeline vs hardcoded.** Recommendation per Push 1 partial: graph-promoted-pipeline (admin-authored, ships v1 pre-promoted). Confirm? Or hardcode in L4 code?

  3. **SCMS BSP turn pipeline same question** as MSUR.

  4. **Replan-divergence magnitude formula** — divergence is "magnitude of mismatch between expected and actual state." Formula depends on state shape. v1 starts with simple binary (matches / doesn't match)? Or scalar magnitude per state-shape custom logic?

  5. **`replan_divergence_threshold` parameter granularity** — per task-pattern, per pipeline, per capacity, or global? Recommendation: per task-pattern (different tasks tolerate different divergence). ALS subsystem registration accommodates this.

  6. **HITL UX shape** — when `request_human_diagnostic` runs, what does the user see? UX design defers to a UX work session; L4 just needs the contract — predicate that returns diagnostic info or `None`.

  7. **ALS dream-cycle frequency** — how often does L4 run an ALS dream cycle? Continuous? Idle-detect? Configurable per deployment. Default: idle-detect with admin-tunable thresholds.

  8. **Cross-task ensemble agreement check (S4 signal)** — running ensemble (multiple candidate-scorer strategies) at task time is expensive. v1 strategy: run ensemble for sample tasks (e.g., 10%) for training data, single-strategy for production tasks. Confirm?

  9. **Phase 6 cross-validation policy** — when admin policy permits, what fraction of failures get cross-validated? Cost vs information gain tradeoff. Default: admin-tunable fraction.

  10. **Goal-misidentification detection** — Phase 4's `verify_goal_achievement` can't detect goal-misidentification from internal signals alone (per WSD architecture §7.5 Phase 4 discussion). External signals (S2 gold, S5 HITL) are the only protection. Document this limitation; surface to admin.

  11. **Lifecycle integration with server.** L4's `start()` / `stop(mode)` per existing L4 spec. v1 only `mode="abort"` per Push 5.

  12. **Module skeleton.** Per L4 current handoff, the original 7-module skeleton was sized for full-scope design. Under reduced scope (Pushes 3, 5, 6 accepted; Push 1 partial), several modules collapse. Re-estimate.

---

## 12. Phasing recommendation

  1. **Phase A — Pushes resolved + module skeleton.** Update L4 handoff status to reflect Pushes 2/3/5/6/7 accepted, Push 1 partial. Re-scope modules accordingly.
  2. **Phase B — ALS skeleton.** Subsystem registration contract + `parameter-staging` writes + `pending-promotions` queue + audit-policy dispatch. Most of ALS's surface; required by Phase D.
  3. **Phase C — Six-phase task lifecycle.** Phases 1-5 first; Phase 6 in Phase G. Replan-check dual-role from §8.
  4. **Phase D — SCMS BSP turn + MSUR.** Pipeline composition; depends on Phase B (ALS) for parameters.
  5. **Phase E — Audit policies + admin tooling.** Per §4.7 + §9.4. Admin UI / API for audit queue.
  6. **Phase F — Sufficient-predicate evaluation + capacity-gaps integration.** Per §6.4 + §9.5.
  7. **Phase G — Phase 6 failure diagnosis.** Per §7.7 + §9.1 (S8). Depends on Phase B (ALS) and Phase D (SCMS replan history).

Phases A / B can ship in parallel. Phase C depends on action contracts (L3) so coordinated with L3 Phase D. Phase D depends on B + L3 Phases A-C. Phase E depends on B. Phase G depends on B + C + D.

Realistic effort under this scope (Pushes resolved, module skeleton trimmed): 4-6k LOC, 4-6 months.

---

## 13. What this does NOT change

  - **Lifecycle and tenancy** per L4 current handoff §3.1 unchanged. One IntelligenceLayer per live user session.
  - **Layer isolation** per §3.2 unchanged. L4 imports nothing from server.
  - **Confidence topology** per §3.3 unchanged. Pipeline-level on `promoted-pipelines`; per-run on MM root.
  - **Plan-runs first-class** per §3.4 unchanged.
  - **Capacities are fixed** per §3.5 unchanged.
  - **Promotion topology** per §3.6 unchanged.
  - **L4 writes-to-L2 list** per §3.7 unchanged (just adds new role-graphs).
  - **L3 surface L4 consumes** per §3.8 unchanged (just adds new capacities).
  - **Three-step task-to-pipeline flow** (per layer4_intelligence_design_notes.md) unchanged. Phase 1 (task-shape recognition) + Phase 2 (pipeline lookup or generation) is the realization of this flow.

---

## 14. Summary checklist for the L4 chat

When this handoff is implemented, L4 should have:

  - [ ] L4 current handoff §4 updated: Pushes 2/3/5/6/7 marked accepted; Push 1 marked partial with the specific positions documented.
  - [ ] ALS architecture: subsystem registration contract; staging-pipeline-audit-apply flow; Local + Global cycles; user-as-Local-admin.
  - [ ] Three audit policies (auto-apply / batched-summary / individual-review) with override semantics.
  - [ ] MSUR pipeline (admin-authored, ships v1).
  - [ ] SCMS BSP turn pipeline (admin-authored, ships v1).
  - [ ] Six-phase task lifecycle (interpretation, determination, execution, verification, outcome, failure-diagnosis).
  - [ ] Replan-check dual-role implementation (forward + reflective).
  - [ ] S8 signal source (replan-divergence).
  - [ ] Pipeline-finding registered as ALS-trainable subsystem.
  - [ ] `capacity-gaps` write integration in Phase 2 + Phase 3.
  - [ ] Sufficient-predicate evaluation post-SCMS quiescence.
  - [ ] Coordinated removal of pause-and-resume infrastructure.
  - [ ] Coordinated removal of coherence dream intent.
  - [ ] Coordinated removal of learnable preemption coefficients.
  - [ ] Module skeleton re-estimated under reduced scope.

---

**End of handoff.**

When L4 design settles these changes, please update this document or write a follow-up handoff so the WSD design chat can absorb the final API.
