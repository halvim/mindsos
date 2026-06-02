---
title: Reconstruction uses private _restore_* factories
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-018]
---

# ADR-0031: Reconstruction uses private _restore_* factories

**Status:** Accepted

**Date:** 2026-04-22

## Context

Loading a Metagraph from FalkorDB needs to rebuild `MetaEdge`/`MetaHyperEdge`/`ElementInstance` objects *with their original ids* (not fresh UUIDs). The public `add_metaedge` / `instantiate_*` APIs mint fresh ids to guarantee uniqueness — reusing them for load would either lose the original id or silently collide.

## Decision

The loader calls `_restore_metaedge`, `_restore_metahyperedge`, `_attach_graph`, `_attach_instance`, `_attach_composite` (private methods on `Metagraph`) that take the id as a parameter and skip uniqueness checks. The IdentityRegistry is updated via `register()` (or `replace()` for the identifier swap during reconstruction).

## Consequences

**Good:**
- Reconstruction is a separate, explicit path.
- The public API cannot accidentally be used for load.

**Bad:**
- Two paths mean two places to keep in sync when a new element kind is added.

## Alternatives considered

1. **A single public `add_*` that accepts an optional `id` parameter** — rejected because it muddles the contract.
2. **A separate `Loader`-only façade on `Metagraph`** — deferred; marginal gain over the current underscore convention.
