---
title: Teaching - humans add capacities; system grows repertoire via promotion and membership
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q7]
---

# ADR-0090: Teaching and repertoire growth model

**Status:** Accepted

**Date:** 2026-04-21

## Context

The system's repertoire of capacities must grow over time. The question is what mechanisms are used: do humans teach atomic capacities, or does the system synthesize its own?

## Decision

Humans teach the system new atomic capacities via a registration API. The effective repertoire grows through three mechanisms: (1) L2 promoted-paths (named sub-pipelines stored as reference-chains into existing L3 nodes), (2) multi-graph membership (capacities registering as members of additional categories), and (3) L4 learning confidences from experience (picking which capacities to use when). The system does not synthesize new DataStates or new atomic capacities on its own.

## Consequences

**Good:**
- Atomic capacity addition remains a deliberate, controlled act (human or admin-gated).
- The system's effective intelligence grows without requiring new atomic primitives.
- Path promotion is inspectable and auditable.

**Cost:**
- New atomic capacities require an explicit teaching step; the system cannot invent entirely new capabilities.

## Alternatives considered

1. **System synthesizes capacities** — rejected (requires code generation; hard to audit and validate).
2. **Only humans can add anything** — rejected (doesn't account for promoted paths as a growth mechanism).
