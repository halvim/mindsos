---
title: Backward-compat shim with DeprecationWarning during migration window
status: Accepted
date: 2026-04-22
layer: L3
aliases: [capacity-ADR-020]
---

# ADR-0079: Backward-compat shim with DeprecationWarning during migration

**Status:** Accepted

**Date:** 2026-04-22

## Context

The pre-2026-04-22 write-API took `user_id: str`. Thousands of call sites exist (docs, demos, tests, notebooks). A hard signature break would force a coordinated flag day across the repo.

## Decision

Each write method keeps `user_id: Optional[str] = None` as a deprecated alias in addition to the new `session: SessionArg = None`. Legacy inputs — `user_id=<str>`, `session=<bare str>`, and `session=<Mapping>` — are accepted, routed through `_resolve_session_arg`, wrapped in a `_LocalTestSession`, and emit a `DeprecationWarning`. Remove the non-`SessionProtocol` branches in the follow-up PR once Server Layer Phase 1 lands.

## Consequences

**Good:**
- Zero-downtime migration.
- Legacy tests run as-is (they emit warnings under `-W always`, which is informational).

**Cost:**
- The `_resolve_session_arg` helper is slightly larger than it needs to be long-term.

## Alternatives considered

1. **Hard break** — rejected (would require coordinated flag day across the repo).
2. **Silent coercion without warning** — rejected (we actively want to see every remaining legacy call site).
