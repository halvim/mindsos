---
title: L3 holds only fixed functions; learned state lives in L4
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-001]
---

# ADR-0060: L3 holds only fixed functions; learned state lives in L4

**Status:** Accepted

**Date:** 2026-04-21

## Context

The system has to distinguish between abilities that are *given* (the repertoire of things the machine can do) and abilities that *improve* (confidence, priors, preferences learned from experience). Conflating the two produced v3's hardest bugs: capacity nodes accumulated state that was actually learning, making them non-idempotent and breaking replay.

## Decision

A `Capacity` declaration is a pure function of `inputs` plus an immutable `context`. No property added by L3 to a capacity node grows, decays, or is updated after registration. Anything that mutates with observation — confidence, reward, prior probabilities, usage counts — belongs to L4 and is persisted via KL's `promoted-pipelines` / `memories` / `task-patterns` role-graphs.

## Consequences

**Good:**
- L3 nodes are stable enough to cache, hash, and ship as read-only artefacts.
- Tests are trivially replayable.

**Cost:**
- A rigid boundary: proposals that "just need a little learned state" in L3 must be rejected and redirected up a layer.

## Alternatives considered

1. **Let L3 hold learned scalars and namespace them** — rejected (namespacing doesn't make values idempotent).
2. **Push fixed capacities into L2 as data** — rejected (capacities are executable code, not knowledge).

## Enforced as

Invariant I1 in the L3 handoff.
