---
title: Richness annotation in DataState type system is implicit, not explicit
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q4]
---

# ADR-0087: Richness annotation in DataState type system is implicit

**Status:** Accepted

**Date:** 2026-04-21

## Context

DataStates represent inputs and outputs with different semantic depths: raw strings (syntactic), tokenized texts (semi-syntactic), parsed meaning (semantic), etc. The question is whether to tag semantic richness explicitly in the type descriptor or leave it implicit in the capacity operators that produce/consume each DataState.

## Decision

Richness is implicit, not typed. The DataState type descriptor carries only `kind`, `elem`, `fields`, and `opaque_tag` — structural information sufficient for auto-discovery. Semantic depth is encoded in the *operator* — the capacity node's name and behaviour carry the intention about what depth of semantic work is being done. Reasoning about semantic richness happens when L4 picks capacities, not when it checks types.

## Consequences

**Good:**
- DataStates stay structurally simple; auto-discovery remains deterministic and cheap.
- Semantic decisions live in L4 (the learned layer), not in the type system.

**Cost:**
- Developers must infer richness from capacity names and documentation, not from type annotations.

## Alternatives considered

1. **Add explicit richness tags** — rejected (would double the compatibility machinery and move decision-making into the type system where it doesn't belong).
2. **Make richness a separate constraint edge** — rejected (same issue; moves reasoning to the wrong layer).
