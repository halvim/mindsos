---
title: Capacities can belong to multiple graphs; one home graph and additional memberships
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q2]
---

# ADR-0085: Multi-graph membership for capacities

**Status:** Accepted

**Date:** 2026-04-21

## Context

Every capacity has a primary functional category (its "home" graph). But some capacities prove useful across multiple categories. The question is whether capacities are locked to a single graph or allowed additional memberships.

## Decision

Each capacity belongs to one home graph and can be registered as a member of zero or more additional category graphs. On lookup collision between graphs, Local wins (specialisation). Additional memberships are added when a capacity is discovered to serve another category — either by admin action or by L4 proposal with admin approval.

## Consequences

**Good:**
- Flexible organisation; capacities aren't artificially locked to a single category.
- One registration path (home graph required), multiple membership options (explicit opt-in).

**Cost:**
- Adds a layer of indirection; must document the home/additional distinction clearly.

## Alternatives considered

1. **Lock capacities to a single graph** — rejected (too rigid; some capacities genuinely serve multiple categories).
2. **Make all graphs equal (no home)** — rejected (every capacity needs a primary neighbourhood for discovery efficiency).

## §Implementation (Phase 28 — 2026-05-24)

Shipped Phase 28: **home-graph registration only.** `CapacityLayer.register_capacity(decl, ...)` writes the declaration's Node into exactly one category graph — `decl.category`'s role-graph in the target metagraph. No additional-membership API ships at Phase 28.

Rationale: no Phase 28-31 caller needs additional memberships. The vertical-slice text builtins (Phase 31) all live in a single home category (`perception`). Cross-category memberships would require either (a) admin action authoring an explicit "also belongs to X" call, or (b) L4 proposing memberships with admin approval — both deferred until a real consumer surfaces.

When an additional-membership API does ship, expected signature: `CapacityLayer.add_membership(capacity_iri, additional_category, *, session)`. The TYPE_COMPAT auto-discovery (Phase 29) will need to walk both home + additional category graphs at that point.

Status remains Accepted; no contract change. The "additional memberships" surface is design-locked-but-not-shipped.
