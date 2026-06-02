---
title: No multi-writer concurrency control at Core level
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-023]
---

# ADR-0036: No multi-writer concurrency control at Core level

**Status:** Accepted

**Date:** 2026-04-22

## Context

Core assumes a single writer per metagraph. Two concurrent writes race with no detection; last-write-wins on every field.

## Decision

Serialise externally. The Server Layer owns the serialisation contract via a `GLOBAL_PROMOTE_LOCK` held for the duration of promotion. Intra-user writes happen inside a single session, which is inherently serial.

## Consequences

**Good:**
- Core carries no lock rows, no `modified_at` columns, no optimistic-concurrency branch in the write path.

**Bad:**
- Any future deployment with true concurrent writers needs Layer-above-Core enforcement.

## Alternatives considered

1. **Optimistic concurrency via per-element `modified_at`** — deferred.
2. **Pessimistic locking at the Graph level** — deferred. Both can be added as wrapper clients without breaking Core's contract.
