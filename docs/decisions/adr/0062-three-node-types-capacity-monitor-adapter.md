---
title: Three node types - Capacity, Monitor, Adapter over _CapacityBase
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-003]
---

# ADR-0062: Three node types - Capacity, Monitor, Adapter over _CapacityBase

**Status:** Accepted

**Date:** 2026-04-21

## Context

L3 needs reactive computation, subscription-driven monitoring, and shape-bridging glue. These share most of their structure but differ in invocation.

## Decision

One base class `_CapacityBase` carrying shared fields plus three concrete subclasses — `Capacity`, `Monitor`, `Adapter` — each with distinct `node_type` and extra fields (`subscribes_to`/`emits` on `Monitor`, `adapter_id` on `Adapter`).

## Consequences

**Good:**
- One registration path, three invocation verbs.
- Clean mental model; minimal code duplication.

**Bad:**
- Adding a fourth node type means another subclass.

## Alternatives considered

A single `Capacity` class with a `kind` enum — rejected because invocation paths diverge enough that dispatch-on-type is cleaner.
