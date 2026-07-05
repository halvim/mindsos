---
title: Property bag on Metagraph / Graph - deferred
status: Superseded
superseded_by: ADR-0130
date: 2026-04-22
layer: L1
aliases: [core-ADR-020]
---

# ADR-0033: Property bag on Metagraph / Graph - deferred

**Status:** Superseded by [ADR-0130](0130-property-bag-on-metagraph-graph.md) — design-phase decision; the shipped L4/L5 architecture (Phases 46–48) implements it. Reconciled in the 2026-07 doc-vs-code audit.

**Date:** 2026-04-22

## Context

Every layer above Core wants to attach structured metadata at the graph or metagraph level ("this is OEWN 2024", "imported_at=…", "active-version pointer is X"). Today callers stash it as dynamic Python attributes (`mg._kl_active_graph_ids`, `graph.properties`), which are invisible to Core and do not round-trip through persistence.

## Decision (proposed)

Add a `properties: Dict[str, Any]` field to both `Metagraph` and `Graph`, with the same reserved-key rules as `Node.properties`. Persist as anchor-row properties.

## Consequences (expected)

Every layer gets a typed, persistent metadata slot. The ADR-0029 `:MetagraphSettings` singleton becomes the mechanism for *arbitrary-shape* metadata (JSON-blob), while the property bag covers scalar-typed metadata.

## Alternatives considered

Sanctioned "metadata graph" convention (a `role="_meta"` singleton graph); keep status quo plus a louder warning against dynamic attributes.
