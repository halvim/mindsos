---
title: invoke/start_resident thread session_user_id into context
status: Accepted
date: 2026-04-22
layer: L3
aliases: [capacity-ADR-022]
---

# ADR-0081: invoke/start_resident thread session_user_id into context

**Status:** Accepted

**Date:** 2026-04-22

## Context

The upcoming L3 memory-writing capacities need to stamp provenance on the *outputs* they produce. They can't read the session directly (the session is the caller's, not the capacity's), but they can read the `context` dict.

## Decision

When a session is supplied, `invoke` and `start_resident` inject `session_user_id = session.user_id` and `session_id = session.session_id` into `context` before handing it to the capacity's `impl`. Caller-supplied keys are never overwritten — `setdefault` is the semantic.

## Consequences

**Good:**
- Capacity implementations get a consistent provenance source without each of them parsing a session object.

**Cost:**
- Two extra keys in `context` that implementations must treat as reserved.

## Alternatives considered

1. **Pass the session object itself into `context`** — rejected (leaks the whole capability set to every capacity; security smell).
