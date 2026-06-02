---
title: Promoting a pipeline transitively requires promoting its Local-capacity dependencies
status: Proposed
date: 2026-04-22
layer: L3
aliases: [capacity-ADR-024]
---

# ADR-0083: Promoting a pipeline transitively requires promoting its Local-capacity dependencies

**Status:** Proposed

**Date:** 2026-04-22

## Context

Pipelines produced by L4 commonly mix Global and Local capacities — a user-authored specialisation plugged into an otherwise standard pipeline. When the admin decides the pipeline has earned promotion from `memories` to `promoted-pipelines`, every step in it must be reachable from *every* user after promotion. A pipeline that references a Local-only capacity fails that test silently.

## Decision

Pipeline promotion is guarded by a dependency check: the admin-facing promotion tool walks the pipeline's capacity IRIs, partitions them into Global and Local, and refuses promotion until every Local dependency is itself promoted (or explicitly substituted by a Global equivalent). The admin tool surfaces the dependency graph as part of the promotion UI — the admin sees "this pipeline uses `capacity:perception:alice.custom_split` (Local to alice); promote that first, or swap it for `capacity:perception:text.space_split` (Global)".

## Consequences

**Good:**
- Promotion is safe-by-default: no post-promotion "mystery missing capacity" errors in other users' runs.
- The admin experience gains a dependency inspector.

**Cost:**
- Two-step promotion for any pipeline with Local steps, which is correct but adds friction.

## Implementation notes

- The *dependency-walker* is a read-only L3 function (`cl.pipeline_local_dependencies(pipeline) -> list[str]`) companion to `successors_of` / `producers_of`.
- The *gate* lives in the Server Layer's promotion orchestrator (already holds `GLOBAL_PROMOTE_LOCK`), which calls the L3 walker and refuses promotion if any Local dependency is unresolved.
- The *UI surface* is the similar-node report extended to include the Local-capacity dependency list.

## Alternatives considered

1. **Silently substitute Local capacities with Global equivalents** — rejected (auto-substitution would promote a pipeline that doesn't behave like the one that earned promotion).
2. **Allow promotion with dangling Local references** — rejected (surfaces breakage at execution time, not safe-by-default).

## Open items before flipping to Accepted

(a) Exact shape of the dependency-walker API. (b) How the walker treats `ref_to_global` Local capacities. (c) UX of the admin surface — likely a column in the similar-node report table.
