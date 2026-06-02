---
title: Two-step writes - MERGE on id first, SET props second
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-010]
---

# ADR-0023: Two-step writes - MERGE on id first, SET props second

**Status:** Accepted

**Date:** 2026-04-22

## Context

In the v3 codebase, a combined `MERGE (n {...all-props...})` occasionally clobbered the `id` property when the property bag happened to contain an `id` key from upstream. The bug corrupted graph integrity silently.

## Decision

Every write is two statements: `MERGE (n:Label {id: $id})` first, then `SET n += $props` (plus additional core metadata properties). The `id` is always bound via `$id`; the `$props` bag cannot overwrite it.

## Consequences

**Good:**
- `id` is inviolate.

**Bad:**
- Core carries a small extra step per write; batching (ADR-0022) amortises the cost.

## Alternatives considered

1. **Strip `id` from the props bag before write** — rejected because it relies on every caller to remember.
2. **Fold back to single-statement after stripping** — rejected because of same fragility.
