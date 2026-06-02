---
title: Mental Model retention - retained by default into memories role-graph
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q16]
---

# ADR-0098: Mental Model retention - default retention to memories

**Status:** Accepted

**Date:** 2026-04-21

## Context

When a task completes, the Mental Model (the structured record of what was thought and done) could be discarded, retained indefinitely, or retained selectively. The question is what the default retention policy should be.

## Decision

**Retained by default** into L2's `memories` role-graph upon task completion. Opt-out available per task. Reading A of the consolidation pattern — working memory in L5 during execution, consolidated knowledge in L2 after. Old-version ref handling for retained memories is best-effort (archived Core versions remain readable; if the referenced node is gone, the memory is read-only).

## Consequences

**Good:**
- Default position maximizes learnability — the system has a corpus of past experiences to draw from.
- Opt-out is available when privacy or storage is a concern.

**Cost:**
- Storage accumulates unless the system has an archival/gc policy.
- Old references may become stale; must handle gracefully.

## Alternatives considered

1. **Never retain** — rejected (loses the substrate for learning and dreaming).
2. **Always retain (no opt-out)** — rejected (doesn't account for privacy or storage constraints).
