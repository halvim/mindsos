---
title: Orchestrator attention mechanism - priority queue keyed by live attention score
status: Proposed
date: 2026-04-22
layer: L4
aliases: [L4-attention]
---

# ADR-0103: Attention mechanism - priority queue and preemption

**Status:** Proposed

**Date:** 2026-04-22

## Context

L4 must manage multiple concurrent goals and tasks. When resources are bounded, it must decide what gets compute next. The question is how the orchestrator prioritizes work.

## Decision

The orchestrator's main data structure is a **priority queue keyed by a live attention score**, rescored as events arrive. Attention score is an L3-capacity-composed function of salience, relevance, urgency, cost, and interruption-cost.

Rescoring is dirty-flagged: items become `needs_rescore=True` when inputs change (new signal, goal shift, cost estimator invalidation). Only dirty items are rescored per tick.

**Four priority tiers:** CRITICAL > FOREGROUND > BACKGROUND > DREAM. Across-tier preemption is hard; within-tier uses effective-score.

Preemption rule: within a tier, a new item preempts the running one only if `attention_score > running_item.raw + sunk_cost_bonus + interruption_cost`. Sunk-cost and interruption-cost are learnable scoring-capacity parameters. Hysteresis locks further preemption for one step (prevents ping-pong).

## Consequences

**Good:**
- Single spotlight model maps cleanly to single-threaded runtime.
- Tiers prevent dreams from preempting user work.
- All scoring factors are learnable.

**Cost:**
- Tie-breaking within a tier requires careful tuning of attention composition.
- No true parallelism (v1 scope; ThreadPoolExecutor deferred to v1.5).

## Alternatives considered

1. **Simple FIFO queue** — rejected (no learned prioritization; no response to signals).
2. **Strict tier enforcement** — rejected (too rigid; needs some fluidity within tiers).

## Related decisions

Locked decisions #6, #7, #8 in the L4 handoff.
