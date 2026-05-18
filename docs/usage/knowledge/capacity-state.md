---
last_confirmed_phase: 13
---

# Capacity-state role schema

Per-user resident-capacity snapshot store. **1 NodeType, 0 EdgeTypes**
at `strict=False`. **Local** metagraph per user (ADR-0044).

## NodeType

- `CapacitySnapshot` — advisory: `capacity_iri`, `user_id`, `taken_at`,
  `state_blob`.

`capacity_snapshot_iri` (Phase 12 PB-8) bakes in all three
identifying facets (`user_id`, `capacity_iri`, `taken_at`) into the
stable IRI. Field-level inverse parsing is deferred to Phase 28 per
PB-8.

## Why no edges in v1

A snapshot is a leaf record — no in-graph relationships. Cross-references
live inside the IRI's opaque body (Phase 12 PB-8).

## Where it's used

L4 lifecycle drains L3 capacity state into this role on logout / dream
phases. Phase 28 (L3 12 categories) is the first consumer.

## Strict-tighten status

`strict=False` (ADR-0149).
