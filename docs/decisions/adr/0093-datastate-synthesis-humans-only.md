---
title: DataState synthesis by L4 - humans only for DataState creation
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q10]
---

# ADR-0093: DataState synthesis - humans only

**Status:** Accepted

**Date:** 2026-04-21

## Context

The system's DataState vocabulary represents the structured shapes that capacities consume and produce. The question is whether L4 can propose new DataStates when it observes near-compatibility, or whether new DataStates are human-authored only.

## Decision

**Humans only** for DataState creation. L4 does not propose new DataStates. However, **L4 proposes path-promotions** — named sub-pipelines stored as reference-chains into existing L3 nodes (recorded in L2's `promoted-pipelines` role-graph) with human approval. The system grows its effective repertoire by discovering and promoting paths between existing DataStates, not by inventing new DataStates.

## Consequences

**Good:**
- DataState vocabulary remains curated and human-reviewed.
- Growth is auditable — new promoted paths show up as L2 records.
- The system doesn't accidentally explode the DataState space with near-duplicates.

**Cost:**
- L4 cannot adapt the representation space to observed tasks — it works within the human-authored vocabulary.

## Alternatives considered

1. **L4 can propose DataStates** — rejected (would fragment the vocabulary; admins couldn't track what L4 has created).
2. **L4 proposes DataStates, humans gate promotion** — rejected (same issue; inventory management becomes a burden).
