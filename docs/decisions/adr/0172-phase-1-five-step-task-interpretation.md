---
title: Phase-1 five-step task interpretation + Method δ + v0 catalog discipline
status: Accepted
date: 2026-06-08
accepted_date: 2026-06-08
layer: L4
related: [0171, 0159]
---

# ADR-0172: Phase-1 five-step task interpretation

**Status:** Accepted

**Date:** 2026-06-08

**Related:** ADR-0171 (six-phase lifecycle), ADR-0159 (capacity registration contract v2).

## Context

Chat A R3 refactored LifecyclePhase 1 (task interpretation) into an explicit 5-step flow so that mapping becomes auditable and learnable. The steps invoke L3 capacities (`process.*`, `hint.*`, `decision.derive_goal`, the mapping subsystem) whose **production bodies ship in WSD installation**. Phase 47 must run the control flow end-to-end with no real catalog.

## Decision

### 1. Five steps (Chat A R3, Method δ)

```
1. receive(task_input)                                   → raw
2. process_input(raw)            [L3 process.*]           → structured_input
3. extract_hints(structured_input) [L3 hint.* global]    → hint_set      → HintSet
4. derive_goal(structured_input, hint_set) [L3 decision.derive_goal] → goal
5. map_to_task_pattern(structured_input, hint_set, goal) → (task_pattern, mapping_confidence)
     5a shape-index candidate lookup
     5b per-candidate declared hints (Method δ)
     5c mapping subsystem #4 confidence
     5d dont-know on low confidence / no candidate
                                                          → MappingResult
```

Phase 1 emits **HintSet** (Level 1 chain artifact) at step 3 and **MappingResult** (Level 2) at step 5, both to intelligence-MM (Chat B chain).

### 2. Method δ — hybrid hint extraction

A global always-on hint subset runs every Phase 1 (step 3); per-pattern declared hints (`relevant_hints` on the task-pattern) run per candidate (step 5b). Methods α/β/γ/ε deferred.

### 3. v0 catalog discipline (PB-C / PB-7)

The orchestrator dispatches ~13 L3 points whose bodies are WSD-install. Phase 47 ships them as **placeholder-marked v0 capacities** in three modules under `mindsos_capacity/builtins/`:

- `planning_v0.py` — `planning.derive_initial_plan` (single-Milestone Plan), `planning.decompose` (`[]`), `planning.is_leaf` (`True`), `planning.aggregate_outputs` (last-child-output).
- `phase1_v0.py` — `process.identity` (raw→structured passthrough), `hint.*` global empty-set stub, `decision.derive_goal` (trivial goal), trivial mapping (fixed task-pattern).
- `orchestration_v0.py` — `decision.signal_to_tier`, `scoring.attention_score` (cold-start constants from `tiers.DEFAULT_TIER_SCORES`), `decision.should_replan`, `predicate.sufficient`, `phase6.attribute_blame`.

Every v0 capacity carries a `placeholder=True` registration marker and a guard that rejects production (non-test) invocation. **WSD installation atomically replaces the v0 catalog** with real capacities (Phase 45 dream-family precedent: ship v1 placeholders, downstream installation extends).

**Stub verdicts are test-configurable.** `decision.should_replan` and `predicate.sufficient` stubs accept an injected verdict so the **ReplanRecord + invalidate-at-and-below path (ADR-0173) and the dont-know path are exercised** — constant stubs would dead-ship those paths.

## Rationale

- **Explicit hint extraction before mapping** makes mapping auditable (HintSet on the MM) and gives ALS subsystem #10 / #4 a calibration target.
- **One coherent v0 catalog** (not scattered per-family) gives a uniform placeholder guard and a single replacement seam for WSD.
- **Test-configurable verdicts** close the coverage gap the constant-stub trap creates.

## Consequences

- Phase 47's trivial-task smoke runs the real 5-step path against v0 stubs.
- WSD installation replaces all three v0 modules atomically.
- HintSet + MappingResult chain artifacts are emitted at 47 (consumed by Phase 48 episodes).

## Alternatives considered

1. **Inject a pre-mapped task; skip Phase-1 L3 calls (PB-7 Opt B).** Rejected — Phase 1's success path stays untested at 47.
2. **Scatter stubs per family with constant verdicts (PB-C Opt B).** Rejected — dead-ships the replan/dont-know paths; no uniform guard.

## §v2-reservations

- Methods α/β/γ/ε hint-extraction strategies.

## §Implementation (Phase 47; pending ship)

`phase_1.py` (5-step) + the three v0 builtin modules + `tests/phase_47/test_phase_1_5_step.py` + `test_planning_v0_catalog.py`.
