---
title: Cost estimators are L3 capacities, not static node properties
status: Proposed
date: 2026-04-22
layer: L4
aliases: [L4-cost]
---

# ADR-0109: Cost estimators as L3 capacities

**Status:** Proposed

**Date:** 2026-04-22

## Context

Planners need estimates of capacity costs (latency, tokens, dollars) to make good decisions. The question is whether costs are static properties on capacity nodes or dynamic estimates computed by capacities.

## Decision

**Capacities, not properties.** New sub-family `capacity:scoring:cost.*` — one estimator per dimension (`cost.latency_ms`, `cost.tokens`, `cost.dollars`; extensible). Cost-aware planners invoke an estimator IRI per candidate edge. Estimators can use learned parameters (from `learned-parameters` role-graph) and are themselves improvable via observation.

This prevents L3 nodes from accumulating learned state (I1 violation) while still allowing cost estimates to improve over time.

## Consequences

**Good:**
- Costs improve with observation; system learns which estimates work.
- Estimators can be retrained without modifying capacity nodes.
- New cost dimensions can be added as new estimator capacities.

**Cost:**
- Planning is more expensive (must invoke estimators for each candidate edge).
- Bootstrapping: system ships default estimators (e.g., `_static` baseline).

## Alternatives considered

1. **Static properties on capacity nodes** — rejected (violates I1; can't improve from observation).
2. **One global cost model** — rejected (can't express per-capacity or per-shape cost differences).

## Related decisions

Locked decision #20 in the L4 handoff.
