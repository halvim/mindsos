---
title: Piggyback metadata persists via MetagraphSettings JSON singletons
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-016]
---

# ADR-0029: Piggyback metadata persists via MetagraphSettings JSON singletons

**Status:** Accepted

**Date:** 2026-04-22

## Context

KL needs its active-version pointer map (`_kl_active_graph_ids`) to round-trip through FalkorDB. Hanging it as a Python attribute on `Metagraph` didn't persist. A full property-bag on `Metagraph` was deferred.

## Decision

One `:MetagraphSettings` node per key, MERGEd by `(metagraph_id, key)`, with a JSON-encoded `value`. The node is linked to its Metagraph by `:IN_METAGRAPH`. Currently one key is defined — `active_graph_ids` — which round-trips `_kl_active_graph_ids`. Additional keys can be added without a schema migration.

## Consequences

**Good:**
- KL's active-version map persists today.
- The pattern absorbs new piggyback keys with zero Core churn.

**Bad:**
- JSON-in-a-string is opaque to FalkorDB — queries can't filter on settings content.

## Alternatives considered

1. **Ship the full `Metagraph.properties` dict** — deferred; higher scope than the promotion rollback task justified.
2. **One node per setting key with scalar props** — rejected because settings shapes vary.
