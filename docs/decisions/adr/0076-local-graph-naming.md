---
title: One FalkorDB graph per Local metagraph; naming scheme mindsos_capacity_local_<slug>
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-017]
---

# ADR-0076: One FalkorDB graph per Local metagraph

**Status:** Accepted

**Date:** 2026-04-21

## Context

Per-user isolation needs to be enforced at the storage layer, not just the metagraph layer, so an accidental cross-user query cannot succeed.

## Decision

Each Local metagraph maps to a distinct FalkorDB graph named `mindsos_capacity_local_<slugify(user_id)>`. Cheap to drop; impossible to accidentally join across. The original `user_id` is preserved as a `Metagraph.user_id` attribute (slug mapping is lossy).

## Consequences

**Good:**
- Hard per-user isolation at the storage layer.

**Cost:**
- Slug collision risk ("`alice@x`" and "`alice_x`" collide); lossiness flagged in the handoff's gotchas.

## Alternatives considered

1. **One shared graph with an `owner` property** — rejected (see ADR-0061).

## Enforced as

Invariant I12 in the L3 handoff.
