---
title: Pause-and-resume support for voluntary logout
status: Deferred
date: 2026-04-22
layer: L4
aliases: [L4-pause]
---

# ADR-0112: Pause-and-resume for voluntary logout

**Status:** Deferred — acknowledged with a known path forward but not implemented in v1; revisit post-v1. Reconciled in the 2026-07 doc-vs-code audit.

**Date:** 2026-04-22

## Context

When a user logs out, the system may have an active task mid-execution. The question is whether the task is discarded, saved for later resumption, or handled differently for forced vs. voluntary logout.

## Decision

**In v1 scope.** On voluntary logout, the live Mental Model is paused: `stop(mode="pause")` preserves the MM as a normal memory; paused status lives on the **plan-run inside the MM**, not on the MM itself. On login, `retrieval.paused_plan_runs(session.user_id)` surfaces paused tasks; system validates and re-enqueues survivors or transitions to `invalidated_on_resume`.

Forced logout (admin kill, session expiry): `stop(mode="abort")` aborts-and-consolidates; no pause. Dreams are always aborted on logout, not paused (re-initiate next idle cycle).

## Consequences

**Good:**
- User experience payoff (walk away, come back); worth ~200 LOC + 100 LOC test.
- Paused runs are recoverable as normal memories if they're still valid.

**Cost:**
- Requires tracking which pipelines became invalid since logout (incompatible L2/L3 changes).
- Admin must handle edge case where paused task references deleted nodes.

## Alternatives considered

1. **Always discard on logout** — rejected (poor UX; loses work in progress).
2. **Always pause (forced and voluntary)** — rejected (forced termination shouldn't appear resumable).

## Related decisions

Locked decisions #27, #30, #31, #32 in the L4 handoff.
