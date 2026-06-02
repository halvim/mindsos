---
title: In-memory-first facade, Core-adapter agnostic persistence
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-016]
---

# ADR-0075: In-memory-first facade, Core-adapter agnostic persistence

**Status:** Accepted

**Date:** 2026-04-21

## Context

Unit tests must not require FalkorDB. The `CapacityLayer` facade is where every read and write flows; tying it to a persistence backend would force every test to stub one out.

## Decision

`CapacityLayer` operates on in-memory `Metagraph`/`Graph` instances. Persistence is layered on via Core's `Client` / repository / loader protocols, exactly as KL does. The facade never directly calls FalkorDB.

## Consequences

**Good:**
- Tests are fast and deterministic.
- The seam for persistence is the Core adapter, which we already trust for KL.

**Cost:**
- Loading a previously-persisted Metagraph is a construction-time step, not a facade capability.

## Alternatives considered

1. **Embed a tiny storage driver in L3** — rejected (duplication of Core's work).
