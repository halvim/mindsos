---
title: One shared capacity:datastates graph per metagraph
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-005]
---

# ADR-0064: One shared capacity:datastates graph per metagraph

**Status:** Accepted

**Date:** 2026-04-21

## Context

DataStates are referenced from every category graph. Either each category graph duplicates the DataState nodes, or one shared graph holds them.

## Decision

One shared `capacity:datastates` role-graph per metagraph. `EDGE_PRODUCES` / `EDGE_CONSUMES` become intra-graph `Edge` when capacity and DataState live in the same graph, and cross-graph `MetaEdge` otherwise.

## Consequences

**Good:**
- One authoritative DataState node per metagraph; zero duplication.
- TYPE_COMPAT is an `Edge` within a category and a `MetaEdge` across categories.

**Bad:**
- None observed.

## Alternatives considered

Inline DataStates into each category graph — rejected; forces a multi-node-update whenever a DataState's shape evolves.

## §Implementation (Phase 28 — 2026-05-24)

Shipped Phase 28:

* `mindsos_capacity.bootstrap.create_global` adds the shared `capacity:datastates` graph FIRST (before the 12 category graphs) so category graphs can reference DataStates by IRI from day one.
* `mindsos_capacity.bootstrap.ensure_datastate_graph(metagraph)` lazily creates the role-graph in Local metagraphs (Locals start empty per [[ADR-0061]] §Implementation; the DataState graph materializes on first `register_datastate` call).
* Schema for the DataState role-graph: `mindsos_capacity.schemas.build_datastates_schema` (1 NodeType: `DataState` with shape-descriptor property bag).
* `EDGE_PRODUCES` / `EDGE_CONSUMES` cross-graph MetaEdge variants are declared in the category-graph schema (`build_category_schema`) but **not populated** at Phase 28 — Phase 33 lights them up when write-API per-flow validators (ADR-0147) need them.

Status remains Accepted.
