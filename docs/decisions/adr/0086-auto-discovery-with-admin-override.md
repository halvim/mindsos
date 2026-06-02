---
title: Auto-discovery of type-compat edges with admin manual override
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q3]
---

# ADR-0086: Auto-discovery of type-compat edges with admin override

**Status:** Accepted

**Date:** 2026-04-21

## Context

Manually declaring which capacities can feed which is tedious and error-prone. But if auto-discovery is the default, admins need a way to remove spurious edges and add ones auto-discovery missed.

## Decision

Auto-discovery runs on every `register_*` and writes `:TYPE_COMPAT` edges with a `discovered_automatically=True` flag. Admins can author TYPE_COMPAT edges without the flag; `rediscover_all` drops every flagged edge and recomputes, leaving manual edges alone. Manual edges persist through rediscovery.

## Consequences

**Good:**
- Default behaviour is fully automated; admins are not burdened with manual wiring for large graphs.
- Admin overrides are preserved and respected.
- Rediscovery is non-destructive for intentional manual work.

**Cost:**
- Admins must understand the distinction between auto and manual edges; the stamping mechanism must be documented clearly.

## Alternatives considered

1. **Require all TYPE_COMPAT to be manual** — rejected (too tedious at scale).
2. **No way to distinguish auto from manual** — rejected (loses the ability to safely rediscover).

## §Implementation (Phase 29 — 2026-05-25)

Auto-discovery + `rediscover_all` shipped per ADR-0069 §Implementation. Manual TYPE_COMPAT edges (no `discovered_automatically=True` flag, or flag explicitly `False`) survive `rediscover_all` because `_drop_auto_edges` filters on `discovered_automatically is True` only.

**Admin-authoring path at Phase 29 is documentation-only.** No `CapacityLayer.add_type_compat(...)` method ships — admins author manual edges via direct `Graph.add_edge(source_node, target_node, EDGE_TYPE_COMPAT, properties={"via_datastate": ..., ...})` (omitting the `discovered_automatically` property). Consequence: manual edges bypass `CAN_WRITE_GLOBAL` (the capability gate fires only on `CapacityLayer.register_*` paths). Filing as Phase 30+ carry-forward: ship `CapacityLayer.add_type_compat` mirroring `add_constraint` shape (capability-gated; auto-omits `discovered_automatically` flag) when first concrete admin caller surfaces.

**Open gap (deferred).** ADR-0086 does NOT specify behaviour when an admin DELETES an auto-discovered edge. Under the Phase 29 implementation, the next `rediscover_all` re-emits the deleted edge because `_edge_already_exists` checks current storage (not a deletion record); the admin's "remove this spurious edge" decision is silently overwritten. Resolution deferred to first reported foot-gun. Proposed mechanisms: (a) anti-edge marker the admin writes to suppress; (b) `blocked=True` flag on a manual edge that prevents auto re-emission for the same source/target/datastate triple; (c) admin-deletion tombstone tracked on the metagraph. Filed as Phase 30+ carry-forward.

Walk-side: `successors_of` (on `CapacityLayerView`) iterates both intra-graph Edges + cross-graph MetaEdges with `type_name == EDGE_TYPE_COMPAT` — parent-verbatim, no soft-delete filter at v1 per Phase 29 R5 PB-37.
