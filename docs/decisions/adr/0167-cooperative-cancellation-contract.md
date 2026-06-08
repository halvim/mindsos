---
title: Cooperative cancellation framework
status: Accepted
date: 2026-06-08
accepted_date: 2026-06-08
layer: L4
related: [0159, 0163]
---

# ADR-0167: Cooperative cancellation framework

**Status:** Accepted

**Date:** 2026-06-08

**Related:** ADR-0159 (capacity registration contract v2 — shipped the `CancelToken` Protocol + `CancelTokenView` in `mindsos_capacity/context.py`), ADR-0163 (Executor — cancellation turns queue ordering into running-task preemption).

## Context

Chat A D32.5 = A settled cancellation as **cooperative**: every L3 capacity that may run > 100 ms accepts an optional `cancel_token` and checks `.is_set()` at natural yield points. Thread-killing (`PyThreadState_SetAsyncExc`) was rejected as unreliable and resource-leaking; "no cancellation" was rejected because it weakens `stop(mode="abort")` (abort wouldn't stop an in-flight L3 call). Cancellation is also what gives ADR-0163's tier ordering real teeth — a running BACKGROUND task is released at its next yield when CRITICAL arrives.

The R0 grounding probe confirmed Phase 42 already shipped, in `mindsos_capacity/context.py`, the read-side surface: a `@runtime_checkable` `CancelToken` Protocol (with `is_set()`) and a `CancelTokenView` (read-only wrapper exposed to capacity bodies). What is missing is the **concrete, settable** token — that is L4 substrate.

## Decision

### 1. Concrete `CancelToken` in L4 (PB-4)

`mindsos_intelligence/cancellation.py` provides a concrete `threading.Event`-backed cancel token that **satisfies the Phase 42 `CancelToken` Protocol** — both `is_set()` and the mutator `request_cancel()` (the exact Protocol method names shipped in `context.py`). The Protocol stays where it shipped (L3 `context.py`), at the boundary capacity bodies import; the concrete implementation is L4. No symbol is duplicated.

### 2. `CancelTokenView` stays L3, re-exported

`CancelTokenView` (read-only) remains in `mindsos_capacity/context.py` — it is the body-side view and belongs at the L3 boundary. `cancellation.py` **re-exports** it for L4 ergonomics rather than redefining it. The view exposes only `is_set()`; bodies cannot cancel.

### 3. Plumbing + discipline

L4 dispatch passes a `cancel_token` (as a `CancelTokenView`) into each worker invocation. `stop(mode="abort")` calls `request_cancel()` on the tokens of all in-flight tasks; workers release at their next yield. Per ADR-0159, a capacity whose declared latency exceeds the threshold **must** accept `cancel_token` in its signature (lint/test-enforced). Cancel-target selection is hardcoded "lowest-priority running" at v1; an L3 `decision.preempt_target` capacity is v2.

## Rationale

- **Cooperative is the only safe model in CPython.** Async thread-kill leaks locks/resources; cooperative yields are explicit and testable.
- **Protocol at L3, concrete at L4.** The read contract belongs with the bodies that consume it (no upward import); the settable token is substrate. Re-exporting `CancelTokenView` avoids both duplication and an upward dependency.

## Consequences

- New `mindsos_intelligence/cancellation.py`; satisfies an already-shipped Protocol (zero L3 churn beyond a re-export).
- `stop(mode="abort")` (ADR's IntelligenceLayer) becomes effective against in-flight L3 calls that honour their tokens.
- Known limitation (Chat A PB-R2-6): a long CPU-bound L3 call that never yields delays preempt; the v2 subprocess escape hatch (D32.7) addresses known-tight-loop capacities.

## Alternatives considered

1. **Thread-killing (`ctypes.PyThreadState_SetAsyncExc`).** Rejected (D32.5-B) — unreliable; leaks resources.
2. **No cancellation.** Rejected (D32.5-C) — weakens `stop(mode="abort")`.
3. **Move `CancelTokenView` into `cancellation.py`.** Rejected — breaks Phase 42 `context.py` imports; churns a shipped module; the view is body-side (L3).
4. **Redefine a second `CancelToken` in L4.** Rejected — duplicate symbol; the Protocol exists to be satisfied, not re-declared.

## §v2-reservations

- `decision.preempt_target` L3 capacity (v1 = hardcoded "lowest-priority running").
- `ProcessPoolExecutor` escape hatch (D32.7) for known non-yielding capacities.

## §Implementation (Phase 46 — convergence; pending ship)

PR-A: `mindsos_intelligence/cancellation.py` (concrete `threading.Event` token + `cancel()` + re-export of `CancelTokenView`). Test `tests/phase_46/test_cancellation_framework.py` (cooperative cancellation + `CancelTokenView` read-only enforcement + Protocol satisfaction). Dispatch plumbing rides with the IntelligenceLayer lifecycle.
