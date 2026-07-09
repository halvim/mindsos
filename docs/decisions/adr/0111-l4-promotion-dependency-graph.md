---
title: Promotion dependency graph - Local pipelines block Global promotion until deps are resolved
status: Deferred
date: 2026-04-22
layer: L4
aliases: [L4-promotion-deps]
---

# ADR-0111: Promotion dependency graph - local capacities block global promotion

**Status:** Deferred — acknowledged with a known path forward but not implemented in v1; revisit post-v1. Reconciled in the 2026-07 doc-vs-code audit.

**Date:** 2026-04-22

## Context

When L4 proposes a Local pipeline for promotion to Global, it might reference Local-only capacities (user-specific specialisations). If those are promoted without their Local dependencies, other users will encounter missing capacities. The question is how to prevent that.

## Decision

Pipeline promotion is guarded by a dependency check: the promotion tool walks the pipeline's capacity IRIs, partitions into Global and Local, and refuses promotion until every Local dependency is itself promoted (or explicitly substituted by a Global equivalent). The admin tool surfaces the dependency graph as part of the promotion UI — the admin sees which Local capacities must be promoted first or swapped out.

The dependency-walker is a read-only L3 function companion to `successors_of` / `producers_of`. The gate lives in the Server Layer's promotion orchestrator. The UI surface is the similar-node report extended to include the Local-capacity dependency list.

## Consequences

**Good:**
- Promotion is safe-by-default; no post-promotion "mystery missing capacity" errors.
- Admin sees the dependency graph and understands constraints.

**Cost:**
- Multi-step promotion for pipelines with Local steps (correct but adds friction).

## Alternatives considered

1. **Silently substitute Local with Global equivalents** — rejected (promoted pipeline behaves differently than the one that earned promotion).
2. **Allow dangling Local references** — rejected (surfaces errors at execution time, not safe).

## Related decisions

Locked decision #26 in the L4 handoff.
