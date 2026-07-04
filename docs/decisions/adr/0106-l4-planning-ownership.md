---
title: Planning ownership - L4 orchestrates; planning algorithms are L3 capacities
status: Superseded
superseded_by: ADR-0172
date: 2026-04-22
layer: L4
aliases: [L4-planning]
---

# ADR-0106: Planning ownership - L4 runs planning meta-pipeline

**Status:** Superseded by [ADR-0172](0172-phase-1-five-step-task-interpretation.md) — design-phase decision; the shipped L4/L5 architecture (Phases 46–48) implements it. Reconciled in the 2026-07 doc-vs-code audit.

**Date:** 2026-04-22

## Context

L3 defines path-finding algorithms (Dijkstra, BFS, A*, etc.) as capacity nodes. The question is who owns the overall planning process: should L4 call L3 functions directly, or should planning be orchestrated via a meta-pipeline?

## Decision

**Planning is L4's job; planning algorithms are L3 capacities.** L4 runs a meta-pipeline that classifies the task, picks an algorithm (via a chooser step), runs it, validates against CONSTRAINT edges, and returns a plan. This is the same as policy authorship (#3): planning procedures are learnable, not hard-coded.

## Consequences

**Good:**
- Planning is inspectable; different algorithms coexist as alternates behind `CONSTRAINT_MUTUALLY_EXCLUSIVE`.
- L4 can learn which algorithm works for which task shape.
- Planning policies improve over time via the learning loop.

**Cost:**
- L4's planning meta-pipeline must be bootstrapped; system ships defaults.

## Alternatives considered

1. **L4 hard-codes planner selection** — rejected (freezes the choice at system design time).
2. **L3 encapsulates planning** — rejected (planning is an intelligence concern, not a fixed capacity repertoire concern).

## Related decisions

Locked decision #16 in the L4 handoff.
