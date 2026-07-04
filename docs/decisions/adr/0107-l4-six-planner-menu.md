---
title: Planner menu - six loadable planning algorithms shipped as separate files
status: Deferred
date: 2026-04-22
layer: L4
aliases: [L4-planners]
---

# ADR-0107: Planner menu - six shipped, extensible

**Status:** Deferred — acknowledged with a known path forward but not implemented in v1; revisit post-v1. Reconciled in the 2026-07 doc-vs-code audit.

**Date:** 2026-04-22

## Context

L3 holds path-finding algorithms. The question is which algorithms ship with v1 and how they're made available to L4's planning orchestrator.

## Decision

Six planners ship as separate loadable files under `mindsos_capacity/builtins/planners/`:
1. BFS (existing)
2. Constraint-aware A*
3. Dijkstra
4. CSP backtracking
5. Beam search
6. Template-pattern-match

Drop-in pattern: L3's core code stays frozen; L4 picks whatever is registered. New planners are added as new files; the chooser learns which to use per task shape.

Deferred planners: MCTS, neural-guided, genetic (need training data or external libraries out of scope for v1).

## Consequences

**Good:**
- Diverse planning strategies available from day one.
- New planners can be added without modifying core L3 or L4.
- L4's chooser has interesting options to learn from.

**Cost:**
- Six capacity definitions to write and test.
- Choosing among six algorithms adds learning complexity.

## Alternatives considered

1. **One planner (BFS only)** — rejected (doesn't stress-test the learnable-choice architecture).
2. **All possible planners** — rejected (neural-guided/MCTS deferred; too much for v1).

## Related decisions

Locked decision #17 in the L4 handoff.
