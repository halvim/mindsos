---
title: Bootstrap carve-out - session=None Global writes still allowed
status: Accepted
date: 2026-04-22
layer: L3
aliases: [capacity-ADR-021]
---

# ADR-0080: Bootstrap carve-out: session=None Global writes still allowed

**Status:** Accepted

**Date:** 2026-04-22

## Context

The bootstrap and admin-CLI paths register Global capacities before the Server Layer is online (there is no session to carry `CAN_WRITE_GLOBAL`). A strict "every Global write needs a session with the capability" rule would require the server to be running during bootstrap, which is a chicken-and-egg problem.

## Decision

`_enforce_global_write(session, op=...)` is a no-op when `session is None` and only raises `PermissionError` when a session is present but lacks the capability. Once production flows are all session-bearing, tighten the carve-out (switch from "only enforce when session present" to "always require a session").

## Consequences

**Good:**
- Current bootstrap scripts continue to work unchanged.
- Real session holders without the capability are rejected.

**Cost:**
- Lingering risk: a bug path where code drops the session and falls into the carve-out silently (mitigated by code review and eventual tightening).

## Alternatives considered

1. **Synthesise an internal bootstrap session** — rejected (more magic than necessary for the slice).
2. **Defer bootstrap to post-server** — rejected (L3 must be testable without the server).

## §Implementation (Phase 28 — 2026-05-24)

Shipped Phase 28 in `mindsos_capacity.CapacityLayer._enforce_global_write(session, *, op)`:

* `session is None` → no-op (carve-out preserves bootstrap path).
* `session is not None and not session.has(CAN_WRITE_GLOBAL)` → `raise PermissionError(f"{op}: session {session.session_id!r} (user={session.user_id!r}) lacks {CAN_WRITE_GLOBAL!r}")`.
* `session is not None and session.has(CAN_WRITE_GLOBAL)` → silent pass.

Called from `register_datastate`, `register_capacity`, `add_constraint`, `rediscover` (last deferred per Phase 29) when the resolved target user_id is `None` (i.e., the write targets the Global metagraph).

Tests at `tests/phase_28/test_capability_gate.py` (5 tests): refuses user session; allows admin session; carve-out passes `session=None`; PermissionError carries op + user_id; uses `Session.for_testing("alice", is_admin=True/False)` to materialize sessions.

Status remains Accepted; the eventual tightening (drop the carve-out when production flows all session-bearing) deferred to whichever phase audits the L3 callsites and certifies session-bearingness.
