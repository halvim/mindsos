---
title: Per-session orchestrator owned by server; no Global L4
status: Superseded
superseded_by: ADR-0171
date: 2026-04-22
layer: L4
aliases: [L4-tenancy]
---

# ADR-0101: One IntelligenceLayer per live user session

**Status:** Superseded by [ADR-0171](0171-six-phase-task-lifecycle.md) — design-phase decision; the shipped L4/L5 architecture (Phases 46–48) implements it. Reconciled in the 2026-07 doc-vs-code audit.

**Date:** 2026-04-22

## Context

L4 is the applied intelligence that manages orchestration, learning, and Mental Model lifecycle. The question is whether L4 is per-user (mirroring KL's Local split) or global (one orchestrator for all users).

## Decision

**One `IntelligenceLayer` instance per live user session**, owned by the server's per-user context. **No Global L4.** L4 has no shared artifacts of its own — all learned state (confidences, memories, patterns) lives in L2 under the existing Global/Local split. A second split at L4 adds structure without buying anything.

Instantiated by the server's login flow after Local L2 and Local L3 are installed. Lives for the duration of the session; torn down at logout.

## Consequences

**Good:**
- Simple tenancy model; aligns with server session lifecycle.
- Session state is naturally scoped; no cross-user contamination.
- All learning state lives in L2; clean separation of concerns.

**Cost:**
- Each session has its own orchestrator; can't share warm state across users.

## Alternatives considered

1. **One Global L4 + per-user overlays** — rejected (two-tier split adds complexity without benefit).
2. **Layered (species-level + per-user)** — rejected (not needed for v1 scale).

## Related decisions

Locked decision #2 in the L4 handoff.
