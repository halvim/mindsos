---
title: Composite overrides are bundle-level metadata and do not propagate
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-013]
---

# ADR-0026: Composite overrides are bundle-level metadata and do not propagate

**Status:** Accepted

**Date:** 2026-04-22

## Context

A `CompositeInstance` bundles member instances. A naive design would cascade the composite's `overrides` into each member on materialisation. This breaks materialisation determinism: the same member instance materialised inside two composites produces different objects.

## Decision

`CompositeInstance.overrides` is bundle-level metadata only. Members are materialised with *their own* overrides; the composite's overrides are preserved as annotations on the bundle itself, never merged into members.

## Consequences

**Good:**
- Materialisation is deterministic.

**Bad:**
- Users intuitively expect cascading.

## Alternatives considered

1. **Cascading overrides** — rejected because of determinism loss.
2. **Opt-in cascade via a `propagate=True` flag** — deferred; hasn't been needed yet.
