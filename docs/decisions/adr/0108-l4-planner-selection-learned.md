---
title: Planner selection is learned per task shape
status: Deferred
date: 2026-04-22
layer: L4
aliases: [L4-planner-selection]
---

# ADR-0108: Planner selection - learned per task shape

**Status:** Deferred — acknowledged with a known path forward but not implemented in v1; revisit post-v1. Reconciled in the 2026-07 doc-vs-code audit.

**Date:** 2026-04-22

## Context

The planning meta-pipeline must choose which algorithm (BFS, A*, Dijkstra, etc.) to use for a given task. The question is whether the choice is hard-coded or learned from observation.

## Decision

**Learned.** L4's planning meta-pipeline includes a chooser step that picks which planner per task shape. The chooser has its own `promoted-pipelines` record, so its performance is tracked and improved via the same learning loop as any other pipeline.

## Consequences

**Good:**
- Planner preferences emerge from observation, not design-time guesses.
- System adapts as it learns task-to-algorithm affinities.
- Chooser improvements are automatic if a better planner is added later.

**Cost:**
- Boostrapping: must initialize chooser with sensible priors; cold-start performance may be suboptimal.

## Alternatives considered

1. **Hard-coded planner selection** — rejected (can't adapt to observed task patterns).
2. **Random selection** — rejected (throws away learning signals).

## Related decisions

Locked decision #18 in the L4 handoff.
