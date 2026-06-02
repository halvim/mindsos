---
title: constraint_kind is the property key, not kind
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-009]
---

# ADR-0068: constraint_kind is the property key, not kind

**Status:** Accepted

**Date:** 2026-04-21

## Context

Core reserves `kind` as an internal property on every Node and Edge. A CONSTRAINT edge that tries to store its category under `kind` silently loses the value.

## Decision

The namespaced key `constraint_kind` holds the category (`mutually_exclusive`, `mandatory_before`, `rate_limit`, `requires_approval`, `requires_l2_version`). `kind` is never written from L3.

## Consequences

**Good:**
- A subtle one-line gotcha is now explicit.

**Bad:**
- None observed.

## Alternatives considered

Lobby Core to free the `kind` key — rejected; Core's invariant is load-bearing across all layers.
