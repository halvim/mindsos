---
title: Replan trigger - always-on at every step boundary with fast-path for high confidence
status: Superseded
superseded_by: ADR-0173
date: 2026-04-22
layer: L4
aliases: [L4-replan]
---

# ADR-0104: Replan trigger - always-on at step boundaries

**Status:** Superseded by [ADR-0173](0173-replan-check-dispatch-and-invalidation.md) — design-phase decision; the shipped L4/L5 architecture (Phases 46–48) implements it. Reconciled in the 2026-07 doc-vs-code audit.

**Date:** 2026-04-22

## Context

During pipeline execution, information changes (new signals arrive, confidence updates). The question is when to stop execution and regenerate the remaining plan: at every step, on certain triggers, or never?

## Decision

**Always-on at every step boundary.** Fast-pass-through on high-confidence cases (replan-check meta-pipeline emits `continue` for high-confidence cases; returns immediately without regenerating). This ensures fresh information is always considered while avoiding the cost of replanning on every step when confidence is high.

The replan-check meta-pipeline inputs: current MM state, remaining plan, per-run and pipeline-level confidence. Verdicts: `continue` (execute next step of current plan), `replan` (discard remaining plan, regenerate from current state), or `abort` (stop and consolidate).

## Consequences

**Good:**
- Uniform; simpler to reason about than gated-by-trigger.
- New information (signals, confidence updates) is always considered.
- Fast-path for high-confidence cases avoids overhead in stable executions.

**Cost:**
- More compute than lazy replanning; cost recouped by reduced failures from stale plans.

## Alternatives considered

1. **Lazy replanning on explicit triggers** — rejected (easy to miss signal-arrival windows; plans go stale).
2. **Never replan** — rejected (can't adapt to new information mid-run).

## Related decisions

Locked decision #14 in the L4 handoff.
