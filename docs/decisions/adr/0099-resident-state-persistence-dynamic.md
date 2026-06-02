---
title: Resident state persistence policy - activity-based dynamic snapshots as default
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q17]
---

# ADR-0099: Resident state persistence policy

**Status:** Accepted

**Date:** 2026-04-21

## Context

Resident capacities accumulate state over time (e.g., rolling statistics, seen patterns). The question is how often and under what conditions that state should be persisted to L2's `capacity-state` role-graph.

## Decision

**Activity-based dynamic snapshots** as default. Snapshot cadence is proportional to observed state-delta rate, with cooldown + a maximum-interval ceiling. Per-resident overrides available: `ephemeral` (never persist), `writethrough` (persist on every change), `snapshot(interval)` (fixed-interval snapshots). All four modes are expressible via the `capacity-state` role-graph without special code paths.

## Consequences

**Good:**
- Defaults are sensible — high-churn state snapshots frequently, quiet state less often.
- Policy is tunable per resident and per deployment.

**Cost:**
- Requires L4 to manage the snapshot lifecycle; adds operational complexity.

## Alternatives considered

1. **Always ephemeral** — rejected (resident state is lost on process restart; can't resume long-lived monitoring).
2. **Always writethrough** — rejected (too expensive; I/O on every state change).
3. **Fixed intervals** — rejected (doesn't adapt to actual resident churn).
