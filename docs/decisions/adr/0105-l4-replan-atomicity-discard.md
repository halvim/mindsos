---
title: Replan atomicity - discard remaining plan; regenerate from current state
status: Superseded
superseded_by: ADR-0173
date: 2026-04-22
layer: L4
aliases: [L4-replan-atomicity]
---

# ADR-0105: Replan atomicity - full regeneration

**Status:** Superseded by [ADR-0173](0173-replan-check-dispatch-and-invalidation.md) — design-phase decision; the shipped L4/L5 architecture (Phases 46–48) implements it. Reconciled in the 2026-07 doc-vs-code audit.

**Date:** 2026-04-22

## Context

When replan triggers, the orchestrator must decide how much of the old plan to keep: can it reuse the remaining suffix (partial reuse), or must it discard and regenerate entirely (full atomicity)?

## Decision

**Full regeneration.** Discard the remaining plan; regenerate from the current state. Don't reuse the prefix. This creates a natural entry point for new information mid-run without the complexity of partial-reuse semantics.

## Consequences

**Good:**
- Simple logic; no partial-reuse state tracking.
- New information is incorporated into the entire remaining plan, not just appended.

**Cost:**
- More compute per replan (regenerate whole remaining plan vs. just suffix changes).
- Can be recouped by high confidence → fewer replans.

## Alternatives considered

1. **Partial reuse (keep prefix, regenerate suffix)** — rejected (complex semantics; must track which prefix steps are still valid).
2. **Adaptive (reuse when confidence high, regenerate when low)** — rejected (adds a layer of policy that's itself learnable; premature for v1).

## Related decisions

Locked decision #15 in the L4 handoff.
