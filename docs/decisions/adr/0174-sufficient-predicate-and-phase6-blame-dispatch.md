---
title: Sufficient-predicate evaluator + Phase-6 BlameVerdict dispatch
status: Accepted
date: 2026-06-08
accepted_date: 2026-06-08
layer: L4
related: [0171, 0172, 0173]
---

# ADR-0174: Sufficient-predicate + Phase-6 failure diagnosis dispatch

**Status:** Accepted

**Date:** 2026-06-08

**Related:** ADR-0171 (six-phase lifecycle), ADR-0172 (v0 catalog), ADR-0173 (replan).

## Context

Two L4 dispatch points complete the lifecycle's decision surface: the **sufficient-predicate** (Chat A D41 — has the task produced enough to succeed?) and **Phase 6 failure diagnosis** (Chat A D13 — when a task fails, attribute blame to a chain level/step). Both are L3 decisions dispatched by L4; their production bodies ship in WSD installation.

## Decision

### 1. Sufficient-predicate (D41)

L4 dispatches `predicate.sufficient(state, task_pattern) -> bool` at goal-verification points. The predicate IRI is declared per task-pattern (`sufficient_predicate_iri`); per-pattern flexibility (e.g. accepting multi-candidate output as success, UC-WSD-3) is automatic because each pattern references its own L3 predicate capacity. Predicates **are** capacities (Chat A Push 2 strict-line consistency).

### 2. Phase 6 — BlameVerdict (D13)

On the failure path L4 dispatches `phase6.attribute_blame(outcome, path) -> BlameVerdict`:

```
BlameVerdict:
  chain_level:      Literal["hint","map","plan","plan_subtree","pipeline"]
  milestone_ref:    Optional[XRef]
  capacity_step_ref: Optional[XRef]
  blame_score:      float
  rationale:        str
```

Full Phase 6 v1 (D13) includes cross-validation by sub-path substitution with an admin-tunable `phase6_cross_validation_budget` (default K=2, validates top-K-blame segments). At Phase 47 `attribute_blame` is a **skeleton dispatch** (BlameVerdict shape + invocation pipeline); the concrete body + cross-validation substitution land in WSD installation.

## Rationale

- **Both are L3 decisions** dispatched by L4 — consistent with the strict line; the orchestrator owns only the dispatch + the resulting control-flow branch.
- **Per-pattern predicate IRIs** give success-criterion flexibility without L4 machinery.
- **BlameVerdict carries the chain level** so Phase 6 output feeds replan (ADR-0173) and the capacity-gaps admin queue.

## Consequences

- At Phase 47 both bodies are test-configurable v0 stubs (ADR-0172); the sufficient-stub forceable to `false` exercises the dont-know branch.
- WSD installation ships the concrete predicate catalog + the cross-validation Phase-6 body.

## Alternatives considered

1. **L4-internal sufficient check (not an L3 predicate).** Rejected — violates the strict line; loses per-pattern learnability.
2. **No Phase 6 at v1 (fail-and-record only).** Rejected — D13 chose full Phase 6 v1; UC-WSD-6/9/14/15 require blame attribution.

## §v2-reservations

- Cross-validation budget K tuning + multi-segment substitution strategies.

## §Implementation (Phase 47; pending ship)

`sufficient_predicate.py` + `phase_6.py` (skeleton dispatch → BlameVerdict) + `tests/phase_47/test_phase_6_hookup.py`.
