---
title: Instancing model - reference + overrides at any granularity
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-002]
---

# ADR-0015: Instancing model - reference + overrides at any granularity

**Status:** Accepted

**Date:** 2026-04-22

## Context

The Mental Model Layer needs to reuse Knowledge Layer templates across many sessions with small per-session tweaks ("Alice, but age=31 this time"). Cloning the full template would blow storage and break "what did the template actually say?" diffs.

## Decision

An `ElementInstance` references a template and carries an `overrides: dict`. Overrides can apply at any granularity: node, edge, hyperedge, subgraph, whole-graph, metaedge, metahyperedge. A `CompositeInstance` bundles instances and nests arbitrarily deep.

## Consequences

**Good:**
- Templates stay pristine; instances are cheap; composition is sparse.
- Materialisation deterministically produces a concrete Core object from `(template, overrides)`.

**Tradeoff:**
- The instancing vocabulary is itself a Core concern, not Layer 5 — see ADR-0037.

## Alternatives considered

1. **Full deep-copy clone per instance** — rejected (storage blow-up, lost provenance).
2. **"Diff patch" style overrides as a separate Patch object** — rejected (more indirection than benefit at Core's level).
