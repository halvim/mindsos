---
title: Deletes leave tombstone-anchored REMOVED_* self-loops
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-011]
---

# ADR-0024: Deletes leave tombstone-anchored REMOVED_* self-loops

**Status:** Accepted

**Date:** 2026-04-22

## Context

Cypher cannot point a relationship at another relationship. Recording "edge X was deleted at time T" therefore has to reify the deletion as a *node-level* event. Without a record, a failed reconstruction looks identical to a successful one that never had the element.

## Decision

Each Graph owns a singleton `:Tombstone` anchor node. Deletions are recorded as `:REMOVED_NODE` / `:REMOVED_EDGE` / `:REMOVED_HYPEREDGE` self-loops on the tombstone, carrying the original id, rel-type, and timestamp in properties.

## Consequences

**Good:**
- Audit is preserved.
- Reconstruction can (in principle) present a tombstone view.

**Bad:**
- Tombstones grow unboundedly without compaction.

## Alternatives considered

1. **Soft delete via `deleted_at` property** — rejected because element rows linger in loader queries.
2. **Hard delete with no record** — rejected because of loss of audit.
3. **External audit log** — rejected because it couples Core to an external sink.
