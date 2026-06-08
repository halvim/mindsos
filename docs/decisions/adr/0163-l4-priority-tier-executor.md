---
title: L4 priority-tier Executor + attention_score
status: Accepted
date: 2026-06-08
accepted_date: 2026-06-08
layer: L4
related: [0169, 0167, 0164, 0159]
---

# ADR-0163: L4 priority-tier Executor + attention_score

**Status:** Accepted

**Date:** 2026-06-08

**Related:** ADR-0169 (TierEnum home — the tier vocabulary lives in L3, imported downward here), ADR-0167 (cooperative cancellation — the mechanism that turns queue ordering into running-task preemption), ADR-0164 (MM RWLock — guards the MM-side `attention_score` write-through deferred here), ADR-0159 (capacity registration contract v2 — `inline`/`concurrent` dispatch flags).

## Context

Chat A R1 (D32.5b + D32.5c) settled L4's scheduling primitive. A stock `ThreadPoolExecutor` is FIFO across tiers, so a CRITICAL task queues behind BACKGROUND work and Push 6 four-tier preemption is silently weakened. L4 needs a custom Executor whose queue is tier-aware and, within a tier, ordered by a mutable per-task `attention_score` (the "adrenaline" mechanism).

Phase 46 is the L4 substrate convergence point — the first L4 code. This ADR ratifies the Executor as a substrate primitive. Per the Chat A strict line (L4 = substrate + control flow; decisions are L3), the Executor holds only queue mechanics; the score *value* is computed by an L3 capacity that lands later.

**Consumer split.** At Phase 46 the Executor is exercised by its own tests on dummy callables and by the empty-task lifecycle roundtrip. Its real workload consumer is the Phase 47 orchestrator. Two pieces therefore defer to their consumers: the L3 `scoring.attention_score` capacity + the `update_priority` wrapper (Phase 47), and the MM-side `attention_score` write-through (Phase 48 — its target, the TaskRun composite, does not exist until L5 v1).

## Decision

### 1. Custom priority-tier Executor

`mindsos_intelligence/executor.py` provides a custom Executor over a `PriorityQueue` keyed `(tier, -attention_score, submit_time)`. Tier dominates; within-tier ordered by descending `attention_score`; `submit_time` is the final tiebreaker. The 4 tiers — CRITICAL / FOREGROUND / BACKGROUND / DREAM — come from the `TierEnum` defined in `mindsos_capacity` (ADR-0169) and imported downward.

This gives **queue-priority ordering, not preemption of running tasks**. Running-task preemption is achieved cooperatively: when a higher-priority task arrives, the orchestrator cancels a lower-priority running task via the `cancel_token` framework (ADR-0167); the worker releases at its next yield point; tier ordering ensures the higher task is dispatched next.

### 2. Single `write_priority` mutation primitive (PB-1)

Per the Chat A "Vocabulary fix" (decision/mutation split), the v1 public primitive is **one** method:

```
write_priority(task_id, score=None, tier=None)  # pure L4 mutation: lazy-delete + re-insert
```

- `score=None` → "top of new tier" default: `max(current scores in target tier) + 1`, or the tier default if empty (Chat A D32.5c.5). An explicit `score` wins.
- `tier=None` → score change within the current tier.
- Both forms trigger auto-preempt-on-elevation per §3.

The Chat A `set_score`/`elevate` names are **not** shipped as separate public methods — they masked the L3-decision/L4-mutation split. (The PHASE_MAP Phase 46 row still names `set_score`/`elevate`; superseded here — recorded as an as-shipped delta.) The L3-invoking wrapper `update_priority(task_id, context)` (invoke `scoring.attention_score` → `write_priority`) is **Phase 47** (needs the L3 capacity).

### 3. Within-tier preempt rule + hysteresis

A running task is preempted only when `new_score > running_score + H`. `H` is per-deployment configurable, default **50** (Chat A D32.5c.3). Prevents score ping-pong. Hardcoded L4 logic.

### 4. Constant attention_score defaults (PB-2)

`attention_score` is an integer 0–9999 within a tier. Cold-start per-tier defaults: CRITICAL = 1000, FOREGROUND = 500, BACKGROUND = 100, DREAM = 10 (Chat A D32.5c.2). The default table lives with the `TierEnum` in L3 (ADR-0169). At Phase 46 these constants are the *only* score source — the L3 `scoring.attention_score` capacity with `learned-parameters` + ALS S9 retraining is Phase 47.

### 5. attention_score is queue-only at v1 (PB-11)

Chat A D32.5c.4 specifies `attention_score` lives on the queue **and** is written through to the MM TaskRun composite under the MM writer lock. At Phase 46 **no TaskRun composite exists** (it is a Phase-48 L5 chain artifact). Therefore Phase 46 ships **queue-only** `attention_score`; the atomic MM write-through (under ADR-0164's lock) is deferred to Phase 48 when TaskRun exists. The ALS S9 mutation-frequency signal emission likewise defers to its Phase 47/48 consumer.

### 6. Worker pool

The Executor backs a worker pool of default size `min(8, cpu_count())`, per-deployment configurable (Chat A D32.1). Worker dispatch honours the `inline`/`concurrent` flags from ADR-0159 (`inline=True` runs on the caller thread).

## Rationale

- **One primitive, not two.** `write_priority(task_id, score, tier)` expresses both re-score and re-tier; the `score=None` path carries the elevate default. Fewer public symbols, matches the Vocabulary-fix strict line.
- **Queue ordering + cooperative cancel, not thread-killing.** Python thread-kill (`PyThreadState_SetAsyncExc`) is unreliable; cooperative cancel is the only safe preemption (ADR-0167).
- **Defer score-source and write-through to their consumers.** The L3 scorer and the TaskRun write target do not exist at 46; shipping them would be dead code (Phase 40/42/45 consumer-discipline precedent).

## Consequences

- New L4-internal primitive; additive (no prior code depends on it).
- `mindsos_intelligence/executor.py` imports `TierEnum` + defaults downward from `mindsos_capacity` (ADR-0169) — no upward import.
- Phase 47 adds `update_priority` + the L3 `scoring.attention_score` capacity; Phase 48 adds the MM `attention_score` write-through + ALS S9 emission.

## Alternatives considered

1. **Stock `ThreadPoolExecutor` + tier check before submit.** Rejected — doesn't order the queue; CRITICAL still waits behind running BACKGROUND.
2. **One executor per tier (4N threads/session).** Rejected — thread bloat; cross-tier preemption still manual.
3. **Ship `set_score`/`elevate` verbatim.** Rejected — masks the decision/mutation split; forces a Phase 47 rename.
4. **Write `attention_score` through to the MM root now (no TaskRun).** Rejected — root is not the spec'd target; would need re-homing when TaskRun lands at 48.

## §v2-reservations

- `decision.preempt_target` L3 capacity (v1 cancel-target = hardcoded "lowest-priority running").
- `scoring.initial_priority` hook beyond the Phase 47 `scoring.attention_score`.

## §Implementation (Phase 46 — convergence; pending ship)

PR-A: `mindsos_intelligence/executor.py` (Executor + `PriorityQueue` + `write_priority` + worker pool). Tests `tests/phase_46/test_priority_tier_executor.py` (4-tier ordering + within-tier score + auto-preempt-on-elevation + hysteresis). `update_priority` wrapper, L3 `scoring.attention_score`, MM write-through, and ALS S9 emission deferred to Phase 47/48.
