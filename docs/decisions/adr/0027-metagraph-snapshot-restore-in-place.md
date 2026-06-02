---
title: MetagraphSnapshot.restore_into mutates in place
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-014]
---

# ADR-0027: MetagraphSnapshot.restore_into mutates in place

**Status:** Accepted

**Date:** 2026-04-22

## Context

The Server Layer wraps KL writes (promotion in particular) in a FalkorDB batch and needs an in-memory rollback path when the batch fails mid-commit. KL's `installed_locals` dict holds each user's Local Metagraph *by reference*: `installed_locals[user_id] = mg`. A rollback that returned a fresh Metagraph would leave every holder of the original reference pointing at a dead instance.

## Decision

`MetagraphSnapshot.of(mg)` deep-copies every mutable attribute. `restore_into(mg)` mutates the original object in place — `id(mg)`, `id(mg.identity)`, and `id(g)` for every surviving contained Graph are preserved.

## Consequences

**Good:**
- Rollback is transparent to every layer holding a reference.

**Bad:**
- A Graph that was *removed* between snapshot and restore is rebuilt as a new object — callers that cached the pre-removal reference hold a stale pointer.

## Alternatives considered

1. **Return a fresh Metagraph** — rejected because it orphans KL's `installed_locals` entry.
2. **Copy-on-write semantics** — rejected because it's too invasive for a narrow use case.

## Revisions

1. **2026-05-16 (Phase 10 — M3 + P84 corrected allow-list).** The covered-fields set is explicit per-attribute (not blanket `deepcopy(mg)`): `_metagraph_id`, `_metagraph_props`, `_graphs` (via `_GraphSnap` with `properties` + Graph-side `soft_delete_dirty`), `_metaedges`, `_metahyperedges`, `_intergraph_edges` (P84 add), `_intergraph_hyperedges` (P84 add), `_schema_name` + `_schema` (P84 add), `_xrefs`, `_xrefs_dirty` (RB1 add), `_soft_delete_dirty` (RPB-11 add), `_identity_ids`. Restore rebuilds identity via `IdentityRegistry.clear()+register()` so the shared-registry object identity survives (ADR-0020).
