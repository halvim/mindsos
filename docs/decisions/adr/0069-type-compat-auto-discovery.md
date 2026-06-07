---
title: TYPE_COMPAT edges are auto-discovered and stamped with discovered_automatically flag
status: Superseded
superseded_by: ADR-0156
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-010]
---

# ADR-0069: TYPE_COMPAT edges are auto-discovered and stamped

**Status:** Superseded by [ADR-0156](0156-l3-bipartite-topology-reframe.md) (Phase 42 — bipartite PRODUCES/CONSUMES topology; TYPE_COMPAT auto-discovery + `discovery.py` retired).

**Date:** 2026-04-21

## Context

Manually declaring which capacities can feed which is tedious, error-prone, and defeats the point of structural shape matching. Yet if L3 auto-writes edges without marking them, admin overrides and rediscovery become impossible to distinguish from auto-discoveries.

## Decision

`discover_for_capacity` / `discover_for_datastate` run on every `register_*` and write `:TYPE_COMPAT` edges with a `discovered_automatically=True` flag and `via_datastate` pointing at the shared DataState. `rediscover_all` drops every edge carrying that stamp and recomputes from scratch. Admin overrides omit the stamp and survive rediscovery.

## Consequences

**Good:**
- Registration order does not matter; L3 is idempotent under replay.
- Admin overrides are preserved through rediscovery.

**Cost:**
- O(N×M) discovery cost flagged as C1 in open-concerns (out of scope for the slice).

## Alternatives considered

1. **Require admins to author TYPE_COMPAT explicitly** — rejected (non-starter above a dozen capacities).
2. **Auto-discover without the stamp** — rejected (losing the admin/auto distinction is unrecoverable).

## Enforced as

Invariant I8 in the L3 handoff.

## §Implementation (Phase 29 — 2026-05-25)

Auto-discovery shipped. `mindsos_capacity/discovery.py` (NEW) exposes `discover_for_capacity` + `discover_for_datastate` + `rediscover_all` free functions. `CapacityLayer.register_capacity` wires `discover_for_capacity` at end of the registration path (after the per-metagraph `_capacity_index` + `_declarations` are populated, so the discovery loop walks the full index and excludes self via `node_id` comparison). `CapacityLayer.register_datastate` wires `discover_for_datastate` symmetrically — though under the Phase 28-29 forward-ref restriction (`_CapacityBase.validate_for_registration` forbids inputs/outputs referencing unregistered DataStates) this trigger emits zero edges at v1; shipped for parent parity + future-scope.

Each auto-emitted edge / metaedge carries `discovered_automatically=True` + `via_datastate=<DataState IRI>` + `strictness="strict"`. Cross-graph TYPE_COMPAT writes a `MetaEdge` (halvim `Metagraph.add_metaedge` takes `source_graph_id` + `target_graph_id` — divergence from parent's Graph-object signature) carrying `source_capacity` + `target_capacity` properties; intra-graph TYPE_COMPAT writes a Core `Edge` per ADR-0086. `CapacityLayer.rediscover` (new at Phase 29) wraps `rediscover_all` which drops every flagged edge via `Graph.remove_edge` (hard delete; halvim probe confirmed no tombstone accumulation) + `Metagraph.remove_metaedge` (public method since Phase 05a — no private-state poke), then re-runs the discovery loop over the full pair-product.

Discovery failures (any `Exception` raised inside an `_add_edge`) surface as `DiscoveryFailedError` (sub of `CapacityRegistrationError`); the registration's node-add + index-mutation are NOT rolled back at v1 (partial-write state observable to callers per Phase 29 R2 PB-27).

Halvim divergences from parent: (1) `add_metaedge` takes graph IDs not Graph objects; (2) `remove_metaedge` is a public method, not a private-state poke; (3) walks (`successors_of` / `producers_of` / `consumers_of`) are parent-verbatim with NO `include_deprecated` parameter at v1 — `include_deprecated` discipline across L3 walks is a Phase 30+ carry-forward when soft-delete becomes a concrete L4 concern (per Phase 29 R5 PB-37).
