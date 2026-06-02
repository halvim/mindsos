---
title: Proxy pattern handles every Local->Global edge; no per-role carve-out
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-011]
---

# ADR-0048: Proxy pattern handles every Local->Global edge

**Status:** Accepted

**Date:** 2026-04-22

## Context

Upper-layer roles like `memories` live in Local but reference Global targets like `promoted-pipelines`. Question: does each new role need its own edge-creation primitive, or does the existing `add_local_edge(..., target_is_global=True, target_proxy_type=...)` cover it?

## Decision

The existing proxy pattern covers every case. `add_local_edge` with `target_is_global=True` lazily creates a proxy node in the Local role-graph on first reference, reuses it on subsequent references, and `_check_global_target_exists` enforces that the target lives in the active Global role-graph. No role-specific primitives.

## Consequences

**Good:**
- One code path, one test surface.
- New upper-layer roles inherit the proxy mechanics for free.

**Bad:**
- Callers must remember to pass `target_proxy_type`.

## Alternatives considered

None recorded; this was the consensus choice during the 2026-04-22 design session.
