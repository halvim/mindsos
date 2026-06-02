---
title: Materialisation is lazy - instance.materialise() on demand
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-006]
---

# ADR-0019: Materialisation is lazy

**Status:** Accepted

**Date:** 2026-04-22

## Context

An instance with overrides describes *what the concrete object would look like*, not the object itself. Eagerly materialising every instance on creation would defeat the instancing model — every session would pay the full storage cost of its templates plus overrides.

## Decision

`ElementInstance.materialise()` returns a fresh Core object with overrides merged on top of the template. Core never auto-expands. Materialised objects are plain Python — unregistered, not attached to any graph. The caller decides attachment.

## Consequences

**Good:**
- An instance can be materialised many times cheaply.
- Core's write path is never surprised by auto-created nodes.

**Bad:**
- Callers must explicitly `materialise()` then attach; mistaking an instance for a materialised object is a common beginner bug.

## Alternatives considered

1. **Auto-materialise on access** — rejected because it's an invisible side-effect on a property read.
2. **Materialise-on-attach with a sentinel** — rejected because "is this instance or object?" branching becomes everywhere.
