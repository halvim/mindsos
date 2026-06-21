---
title: Reset boundary — role-scoped reset_run_state vs hard delete
status: Accepted
date: 2026-06-21
layer: Server
aliases: [F9-C]
---

# ADR-0187: Reset boundary

**Status:** Accepted

**Date:** 2026-06-21 (branch `feat/f9-durable-local`)

## Context

`FalkorDBLocalPersister.delete()` is a **hard-delete**: it drops every
graph AND the Metagraph node (full Local teardown). F9 needs a softer
"reset" that wipes a device's run-state while **retaining learned
skills**, so a user can clear in-flight/episodic state without losing
taught capabilities.

## Decision

Add **`reset_run_state(user_id) -> bool`** to `FalkorDBLocalPersister`. It
reuses only the per-graph **element `DETACH DELETE`** subset of `delete()`
(elements + their tombstones), scoped to the run-state role-graphs by
`g.role`. It does NOT drop the graph nodes, the durable role-graphs, the
satellites/XRefs, or the Metagraph node — the (now-empty) run-state graphs
stay in place, so the Local remains well-formed and re-loadable.

The run-state / durable split:

- **Wiped (run-state):** `episodic_memories` (per-task/run history),
  `parameter-staging` + `pending-promotions` (in-flight ALS
  evidence/proposals — **PB-A** pick: transient, not durable skill).
- **Retained (durable learning):** `learned-parameters` + `capacity-state`
  (**PB-C** pick: `capacity-state` is durable) — and every other graph.

Idempotent: returns `True` if the Local existed, `False` otherwise
(mirrors `delete`). Holds the per-user mutex (ADR-0006).

## Consequences

**Good:** reset retains taught skills (the F9 gate); the durable
`learned-parameters` descriptor (ADR-0185) survives, so capabilities
remain re-activatable after reset.

**Open (confirm with ALS owners):** PB-A — whether `parameter-staging` /
`pending-promotions` should ever be retained across reset. Current pick:
wipe (in-flight ALS state is not a durable skill).
