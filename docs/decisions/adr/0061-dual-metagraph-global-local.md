---
title: Dual metagraph - Global + per-user Local mirrors KL
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-002]
---

# ADR-0061: Dual metagraph - Global + per-user Local mirrors KL

**Status:** Accepted

**Date:** 2026-04-21

## Context

Some capacities are system-wide (`text.space_split`), others are user-authored specialisations (`alice.space_split_with_custom_tokeniser`). KL already solved the multi-tenant shape.

## Decision

`CapacityLayer` owns one Global Metagraph and lazily creates a Local Metagraph per `user_id`. Local capacities may carry `ref:global_capacity` + `ref_type` pointing into Global. On lookup collision, Local wins.

## Consequences

**Good:**
- L3's public API and mental model match KL's.
- Cross-user contamination is impossible at the storage level.

**Bad:**
- Admin-authored Global content is effectively a separate authoring surface from user-authored Local content.

## Alternatives considered

1. **Single shared metagraph with an `owner` property** — rejected because it forces every read to filter.
2. **Shadow Local as a diff against Global** — rejected because diff semantics are harder to reason about.

## §Implementation (Phase 28 — 2026-05-24)

Shipped Phase 28 in `mindsos_capacity.CapacityLayer`:

* `__init__` constructs a Global `Metagraph` via `mindsos_capacity.bootstrap.create_global(...)` (12 category role-graphs + the shared `capacity:datastates` role-graph; ADR-0064 + ADR-0065 close the same ship).
* `local_metagraph(user_id)` lazily creates a per-user Local `Metagraph` on first call; cached in `self._locals: Dict[str, Metagraph]`. Per-Local `_capacity_index` entry is initialized atomically alongside the metagraph (R3 PB-23 invariant tested at `tests/phase_28/test_capacity_layer_init.py`).
* Local-wins lookup ships via `_resolve_declaration(capacity_iri, *, user_id)`: searches `_capacity_index[local_mg.metagraph_id]` first when `user_id is not None`, falls back to Global. Tested at `tests/phase_28/test_capacity_layer_local_wins.py`.
* `_declarations: Dict[str, _CapacityBase]` is single-dict (parent layout); Local registration of an IRI that collides with Global OVERWRITES the entry — semantically "Local specialises Global." Documented + tested at the same file.

Status remains Accepted; no contract change.
