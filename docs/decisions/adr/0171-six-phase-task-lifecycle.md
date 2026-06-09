---
title: Six-phase task lifecycle — orchestrator, worker-per-task, simplified mode
status: Accepted
date: 2026-06-08
accepted_date: 2026-06-08
layer: L4
related: [0163, 0164, 0165, 0166, 0167, 0169]
---

# ADR-0171: Six-phase task lifecycle — orchestrator structure

**Status:** Accepted

**Date:** 2026-06-08

**Related:** ADR-0163 (priority-tier Executor — the worker pool this runs on), ADR-0164 (MM RWLock — chain-artifact writes), ADR-0165 (three-sub-MM — intelligence-MM authoring), ADR-0166 (MM resolver — chain-artifact emit target), ADR-0169 (TierEnum / signal-triage).

## Context

Chat A D12 settled a **six-phase task lifecycle** (production) plus a simplified bypass mode for dev/test. Phase 46 shipped the L4 substrate (`mindsos_intelligence`) but no runnable lifecycle. Phase 47 implements the orchestrator that drives a task through LifecyclePhase 1→6.

Chat A D32 described an "orchestrator thread (main)" that owns phase transitions, with a worker pool for capacity invocations. **The Phase-46 substrate shipped a different concurrency shape** (grounding-confirmed): `IntelligenceLayer.enqueue(task: Callable[[], object])` submits the task closure directly to the priority-tier worker pool; `start()` launches the executor + signal-triage + dream timer but **no separate orchestrator main thread**.

## Decision

### 1. Lifecycle runs on the dequeuing worker thread (D32 divergence)

A task's entire six-phase lifecycle executes **on the worker thread that dequeues it** from the priority-tier executor. The orchestrator entry point is `run_lifecycle(task_input, context) -> TaskOutcome`, enqueued as a zero-arg closure via `IntelligenceLayer.enqueue`. Capacity invocations within the lifecycle run **inline** on that worker (sibling Milestones sequential v1 per Chat B); chain artifacts are written to intelligence-MM under the MM-root writer lock (ADR-0164); the per-task `cancel_token` held by that worker drives cooperative cancellation and preemption (ADR-0163).

This **supersedes Chat A D32's literal "orchestrator thread (main) owns phase transitions"** — the shipped Phase-46 substrate (worker-per-task) is authoritative. No cross-thread phase-transition coordination exists or is needed in v1; sub-task parallelism (parallel Milestones, cross-validation fan-out) is a v2 worker-pool use.

### 2. Six phases (D12)

`LifecyclePhase` enum (1–6) + a transition table on `orchestrator.py`; each phase delegates to its module:

- **Phase 1 — Task interpretation** (`phase_1.py`; 5-step, ADR-0172) → HintSet + MappingResult.
- **Phase 2 — Plan + Pipeline construction** (`plan_construction.py`) → Plan (recursive Milestone tree, lazy decomposition, cold-start max-depth 3) + per-leaf Pipelines.
- **Phase 3–5 — Execution** (`execution.py`) → PipelineRuns in DFS Milestone order. MSUR + SCMS are L3 orchestration capacities whose **bodies ship in WSD installation**; at Phase 47 their dispatch points are absent/skeleton hooks and the loop tolerates their absence.
- **Phase 6 — Failure diagnosis** (`phase_6.py`; ADR-0174) on the failure path.

Replan re-enters the state machine at the invalidate level (ADR-0173).

### 3. Simplified mode = API flag (PB-E)

D12's simplified mode ships as a `simplified: bool` flag on `run_lifecycle` that bypasses goal-verification, consolidation, and ALS signal emission. **The CLI verb (`mindsos capacity invoke --bypass-lifecycle`) is deferred** until an interactive consumer exists — Phase 47 is library-only; the trivial-task smoke and all tests drive the lifecycle via the API.

### 4. Consolidation seam

The Phase-5→completion consolidation hook ships as a **stub/no-op** at Phase 47. Real MM-freeze + Episode write lands at Phase 48 (L5 v1); the smoke uses stub-consolidate and covers control flow only.

## Rationale

- **Worker-per-task is simpler and is what shipped.** It removes cross-thread phase coordination; cancellation/replan are local to the running worker's token.
- **Per-phase modules** match the PHASE_MAP module list and keep each phase independently testable.
- **Simplified mode as a flag, not a CLI verb**, respects consumer discipline — no interactive consumer exists at 47.

## Consequences

- The orchestrator is a function enqueued as a closure; no new thread class beyond the Phase-46 substrate.
- Documents the Chat A D32 divergence so later chats do not re-introduce a separate orchestrator thread without cause.
- Phase 48 fills the consolidation stub; v2 may use the worker pool for parallel Milestones / cross-validation.

## Alternatives considered

1. **Dedicated orchestrator main thread (Chat A D32 literal).** Rejected — contradicts the shipped Phase-46 substrate; adds cross-thread coordination with no v1 benefit (siblings are sequential).
2. **Ship the `--bypass-lifecycle` CLI verb at 47.** Rejected — no interactive consumer; the flag covers the dev/test need.
3. **Monolithic orchestrator (no per-phase modules).** Rejected — harder to test phase-to-phase invariants; diverges from the PHASE_MAP module list.

## §v2-reservations

- Parallel sibling Milestones + cross-validation fan-out across the worker pool.
- `--bypass-lifecycle` CLI verb when an interactive consumer lands.

## §Implementation (Phase 47; pending ship)

`orchestrator.py` (LifecyclePhase enum + transition table + `run_lifecycle` closure) + `phase_1.py`/`plan_construction.py`/`execution.py`/`phase_6.py`/`replan_check.py`/`sufficient_predicate.py`. Lifecycle enqueued via `IntelligenceLayer.enqueue`; runs on the dequeuing worker. Tested by `tests/phase_47/test_six_phase_lifecycle.py` + `test_trivial_task_smoke.py`.
