---
title: Session persistence for residents via three-tier memory model managed by L4
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q6]
---

# ADR-0089: Three-tier memory model for resident observation persistence

**Status:** Accepted

**Date:** 2026-04-21

## Context

Residents produce observation streams over time. These observations need to be retained somewhere, but different observations have different retention needs. The question is where and for how long.

## Decision

A three-tier model managed by L4 lifecycle processes:

1. **L4 process memory** (ephemeral): rolling observation windows, in-flight state the resident uses. Dies with the process.
2. **L5 working memory** (task-scoped): observations pinned to the Mental Model of a currently-executing task. Retained as long as the Mental Model is retained.
3. **L2 long-term memory** (persistent): observations deemed worth remembering across sessions — written to `capacity-state` role-graph by the L4 lifecycle monitor's triage logic.

The triage rule ("which tier does this observation go to?") is itself an L4 intelligence, not an L3 concern. L3 residents simply produce observations; L4 places them.

## Consequences

**Good:**
- Retention policy is learnable — L4 can improve its triage over time.
- Each tier has appropriate guarantees and costs.
- L3 residents remain stateless and side-effect-free.

**Cost:**
- L3 doesn't directly control where observations go; L4 must implement the triage discipline.

## Alternatives considered

1. **All-or-nothing in-memory** — rejected (unbounded growth; no long-term retention).
2. **Always write to L2** — rejected (expensive; not every observation is worth persisting).
3. **Let residents decide** — rejected (violates L3's purity; L3 has no notion of task vs process lifetime).
