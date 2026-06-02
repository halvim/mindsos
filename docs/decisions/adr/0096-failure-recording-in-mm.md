---
title: Failure recording inside an MM via ref:problem_trace pointer
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q14]
---

# ADR-0096: Failure recording inside an MM

**Status:** Accepted

**Date:** 2026-04-21

## Context

When a step in a pipeline fails, the Mental Model (which records the executed task) must capture that failure. The question is how — as a separate `FailureRecord` node, or as part of the normal task trace?

## Decision

The MM records the failed step as a normal `NodeInstance` and carries a `ref:problem_trace` pointer at the root pointing at the problem-trace entry with the error details. No separate `FailureRecord` composite; no duplication. The MM is a complete record of what was attempted; the problem-trace holds the diagnostic detail.

## Consequences

**Good:**
- One source of truth per MM: the structure records the attempted work, the problem-trace reference points to failure details.
- No duplication; less schema complexity.
- The MM remains a coherent narrative of the task.

**Cost:**
- Must ensure problem-trace entries are retained with their corresponding MM (coordinated retention policy).

## Alternatives considered

1. **Separate `FailureRecord` within the MM** — rejected (duplicates the failure fact; harder to reason about).
2. **Inline failure details in the NodeInstance** — rejected (bloats the MM with error payloads that don't belong in the main narrative).
