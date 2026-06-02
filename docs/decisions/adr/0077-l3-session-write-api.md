---
title: Write API takes session: SessionProtocol
status: Accepted
date: 2026-04-22
layer: L3
aliases: [capacity-ADR-018]
---

# ADR-0077: Write API takes session: SessionProtocol

**Status:** Accepted

**Date:** 2026-04-22

## Context

The new `mindsos_server/` layer owns identity, session lifecycle, and capability enforcement. It hands a capability-bearing `Session` object down to every domain layer on every write so (a) provenance stamping is consistent, (b) capability checks have a single ground truth, (c) the layer below never has to re-look-up the user.

## Decision

Every write-facing method on `CapacityLayer` — `register_datastate`, `register_capacity`, `add_constraint`, `iter_constraints`, `invoke`, `start_resident`, the three successor-lookup methods, and `rediscover` — accepts a `session: SessionArg = None` keyword. `SessionProtocol` is defined structurally (`@runtime_checkable` Protocol with `session_id`, `user_id`, `actor_role`, `capabilities`, `has(capability)`) so L3 need not import the concrete `Session` class. Routing rule: session present → Local(`session.user_id`); absent → Global (bootstrap path).

## Consequences

**Good:**
- L3 aligns with L2 and the Server Layer; provenance (`created_by=session.user_id`) flows for free.
- `CAN_WRITE_GLOBAL` capability check has a place to live.

**Cost:**
- Every write-API caller in tests and L4 had to migrate.

## Alternatives considered

1. **Import `Session` as a concrete type** — rejected (breaks layer isolation; see ADR-0010).
2. **Pass the raw capability set as a separate argument** — rejected (plumbing two correlated arguments is worse than one).

## Lands in

`mindsos_capacity/types.py` (SessionProtocol, helpers) and `capacity_layer.py` (every write method).
