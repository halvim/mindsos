---
title: Instancing vocabulary lives in Core
status: Superseded
superseded_by: ADR-0132
date: 2026-04-22
layer: L1
aliases: [core-ADR-024]
---

# ADR-0037: Instancing vocabulary lives in Core

**Status:** Superseded by [ADR-0132](0132-instancing-moved-to-mindsos-instances.md) — the instancing vocabulary moved to the `mindsos_instances` package (shipped). Reconciled in the 2026-07 doc-vs-code audit.

**Date:** 2026-04-22

## Context

`ElementInstance` and its seven subclasses, plus `CompositeInstance`, are Mental-Model-Layer (Layer 5) vocabulary by intent. Keeping them in Core means the Knowledge Layer (which doesn't touch instancing) pays import cost for vocabulary it doesn't use, and Layer 5 can't extend instancing without editing Core.

## Decision

Instancing stays in Core for now. The ADR-0015 model was drafted against Core primitives, and moving it to a sibling package would be architecture-shaped churn better timed to coincide with the Mental Model chat's own decisions.

## Consequences

**Good:**
- Core carries extra surface that KL doesn't use.

**Bad:**
- Layer 5 extensibility goes through Core PRs.
- The tradeoff is bounded — instancing is ~400 LOC of Core's ~2.5k.

## Alternatives considered

1. **Move to `mindsos_instances`** — deferred; revisit with Layer 5.
2. **Split Core into `_data` + `_persistence` with instancing as a third tier** — deferred; ADR-0018 covers why the package is not split today.
